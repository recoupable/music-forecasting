"""Project a bounded release cohort from a local MusicBrainz core table dump."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile
from tempfile import TemporaryDirectory

# Zero-based columns from MusicBrainz schema 31. PostgreSQL COPY leaves text escaped.
TABLES = {
    "area": {0: "id", 2: "name"},
    "artist": {0: "id", 1: "gid"},
    "artist_credit": {0: "id", 1: "name"},
    "artist_credit_name": {0: "credit", 1: "position", 2: "artist"},
    "iso_3166_1": {0: "area", 1: "code"},
    "isrc": {1: "recording", 2: "code"},
    "label": {0: "id", 2: "name"},
    "medium": {0: "id", 1: "release_id", 3: "format"},
    "medium_format": {0: "id", 1: "name"},
    "recording": {0: "id", 1: "gid", 2: "title", 3: "credit", 8: "video"},
    "release": {0: "id", 1: "gid", 5: "status"},
    "release_country": {0: "release_id", 1: "country", 2: "y", 3: "m", 4: "d"},
    "release_unknown_country": {0: "release_id", 1: "y", 2: "m", 3: "d"},
    "release_label": {1: "release_id", 2: "label"},
    "release_status": {0: "id", 1: "name"},
    "track": {2: "recording", 3: "medium", 11: "is_data"},
}

COHORT_QUERY = """
WITH events AS (
    SELECT release_id, country, try_cast(y || '-' || lpad(m,2,'0') || '-' || lpad(d,2,'0') AS DATE) AS day,
        try_cast(y || '-' || lpad(coalesce(m,'1'),2,'0') || '-' || lpad(coalesce(d,'1'),2,'0') AS DATE) AS earliest
    FROM release_country
    UNION ALL
    SELECT release_id, NULL, try_cast(y || '-' || lpad(m,2,'0') || '-' || lpad(d,2,'0') AS DATE),
        try_cast(y || '-' || lpad(coalesce(m,'1'),2,'0') || '-' || lpad(coalesce(d,'1'),2,'0') AS DATE)
    FROM release_unknown_country
), selected_editions AS (
    SELECT DISTINCT e.release_id, r.gid AS release_gid, e.day,
        CASE WHEN country_code.code = 'US' THEN 'US' ELSE 'XW' END AS market
    FROM events e
    JOIN release r ON e.release_id = r.id
    JOIN release_status s ON r.status = s.id AND s.name = 'Official'
    LEFT JOIN release_label rl ON r.id = rl.release_id
    LEFT JOIN label l ON rl.label = l.id
    JOIN area a ON a.id = e.country
    LEFT JOIN iso_3166_1 country_code ON a.id = country_code.area AND country_code.code = 'US'
    WHERE (country_code.code = 'US' OR a.name = '[Worldwide]' OR a.name = 'Worldwide')
      AND e.day >= $start::DATE AND e.day < $stop::DATE
      AND (len($labels) = 0 OR list_contains($labels, l.name))
), selected_slots AS (
    SELECT DISTINCT t.recording, edition.release_gid, edition.day, edition.market
    FROM selected_editions edition
    JOIN medium m ON m.release_id = edition.release_id
    JOIN medium_format fmt ON m.format = fmt.id AND fmt.name = 'Digital Media'
    JOIN track t ON m.id = t.medium AND t.is_data IN ('0', 'f')
    JOIN recording rec ON rec.id = t.recording AND rec.video IN ('0', 'f')
), candidate_ids AS (
    SELECT DISTINCT recording FROM selected_slots
), first_day AS (
    SELECT c.recording, min(e.earliest) AS day
    FROM candidate_ids c
    JOIN track t ON c.recording = t.recording AND t.is_data IN ('0', 'f')
    JOIN medium m ON t.medium = m.id
    JOIN release r ON m.release_id = r.id
    JOIN release_status s ON r.status = s.id AND s.name = 'Official'
    JOIN events e ON r.id = e.release_id
    GROUP BY c.recording
), grouped AS (
    SELECT DISTINCT slots.recording, slots.day,
        list(DISTINCT slots.market ORDER BY slots.market) AS markets,
        list(DISTINCT slots.release_gid ORDER BY slots.release_gid) AS releases
    FROM selected_slots slots JOIN first_day first ON first.recording = slots.recording AND first.day = slots.day
    GROUP BY slots.recording, slots.day
), isrcs AS (
    SELECT i.recording, list(DISTINCT i.code ORDER BY i.code) AS codes
    FROM isrc i JOIN candidate_ids c ON i.recording = c.recording GROUP BY i.recording
)
SELECT r.gid, r.title, ac.name, a.gid, grouped.day::VARCHAR, markets, releases, coalesce(isrcs.codes, [])
FROM grouped
JOIN recording r ON r.id = grouped.recording
JOIN artist_credit ac ON r.credit = ac.id
JOIN artist_credit_name n ON ac.id = n.credit AND n.position = '0'
JOIN artist a ON n.artist = a.id
LEFT JOIN isrcs ON r.id = isrcs.recording
ORDER BY r.gid
"""


def extract_tables(archive, destination):
    seen = set()
    schema = None
    with tarfile.open(archive, "r|xz") as dump:
        for member in dump:
            if not member.isfile():
                continue
            if member.name == "SCHEMA_SEQUENCE":
                schema = dump.extractfile(member).read().strip()
            if member.name.startswith("mbdump/"):
                name = member.name.removeprefix("mbdump/")
                if name in TABLES and name not in seen:
                    with dump.extractfile(member) as source, (destination / name).open("wb") as target:
                        shutil.copyfileobj(source, target, 1024 * 1024)
                    seen.add(name)
    if set(TABLES) != seen or schema != b"31":
        raise ValueError(f"Expected MusicBrainz schema 31 and core tables; schema={schema!r}, missing={set(TABLES) - seen}")


def unescape(value):
    escapes = {"b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v", "\\": "\\"}
    return re.sub(r"\\(.)", lambda match: escapes.get(match[1], match[1]), value)


def project(settings, archive, output):
    import duckdb

    first = settings["first_release_month"] + "-01"
    year, month = map(int, settings["last_release_month"].split("-"))
    stop = f"{year + (month == 12):04d}-{1 if month == 12 else month + 1:02d}-01"
    with TemporaryDirectory(prefix="mb-cohort-", dir=output.parent) as folder, duckdb.connect() as connection:
        destination = Path(folder)
        extract_tables(archive, destination)
        for table, fields in TABLES.items():
            source = str(destination / table).replace("'", "''")
            relation = connection.sql(
                rf"SELECT * FROM read_csv('{source}', delim='\t', header=false, all_varchar=true, "
                r"quote='', escape='', nullstr='\N')"
            )
            columns = relation.columns
            projection = ", ".join(f'{columns[index]} AS "{name}"' for index, name in fields.items())
            relation.project(projection).create_view(table)
        result = connection.execute(COHORT_QUERY, {"labels": settings["labels"], "start": first, "stop": stop})
        recordings = [
            {"id": gid, "title": unescape(title), "artist": unescape(credit), "artist_id": artist_id,
             "release_on": day, "market_evidence": markets, "release_ids": releases, "isrcs": codes}
            for gid, title, credit, artist_id, day, markets, releases, codes in result.fetchall()
        ]
    with archive.open("rb") as raw:
        source_sha256 = hashlib.file_digest(raw, "sha256").hexdigest()
    output.write_text(json.dumps({
        "source": "musicbrainz-core-dump",
        "source_sha256": source_sha256,
        "release_editions": len({rid for item in recordings for rid in item["release_ids"]}),
        "recordings": recordings,
    }, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--config", type=Path, default=Path("experiments/hit100-musicbrainz.json"))
    parser.add_argument("--output", type=Path, default=Path(".forecast/musicbrainz-cohort.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    project(json.loads(args.config.read_bytes()), args.archive, args.output)
