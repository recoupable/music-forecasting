"""Crosswalk and score a bounded MusicBrainz cohort against Hot 100 issue dates."""

import argparse
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from datetime import date, timedelta
import hashlib
import json
from math import log1p
from pathlib import Path
import re
import unicodedata

from .benchmark import Week, compare, training_before
from .chart_audit import audit

HORIZON = timedelta(days=90)


def normalized(value):
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    words = "".join(c for c in decomposed if not unicodedata.combining(c))
    words = words.replace("&", " and ").replace("’", "").replace("'", "")
    return " ".join(re.findall(r"[^\W_]+", words))


def normalized_credit(credit):
    return re.sub(r"\b(?:featuring|feat|ft|with|and)\b\s*", "", normalized(credit)).strip()


def lead_artist(credit):
    return normalized(re.split(r"\s+(?:featuring|feat\.?|ft\.?|with|&|x)\s+|,\s*", credit,
                               maxsplit=1, flags=re.IGNORECASE)[0])


def base_title(title):
    return normalized(re.sub(r"\s*[\[(].*?[\])]", "", title))


def join_cohort(recordings, editions):
    exact = {}
    loose = set()
    artist_history = defaultdict(list)
    for issue in sorted(editions, key=lambda item: item["date"]):
        day = date.fromisoformat(issue["date"])
        for row in issue["data"]:
            key = (normalized(row["song"]), normalized_credit(row["artist"]))
            exact.setdefault(key, day)
            lead = lead_artist(row["artist"])
            loose.add((base_title(row["song"]), lead))
            artist_history[lead].append(day)

    key_counts = Counter((normalized(row["title"]), normalized_credit(row["artist"])) for row in recordings)
    version_counts = Counter(isrc for row in recordings for isrc in row["isrcs"])
    crosswalk = []
    for row in recordings:
        key = (normalized(row["title"]), normalized_credit(row["artist"]))
        lead = lead_artist(row["artist"])
        day = exact.get(key)
        if not all(key) or key_counts[key] > 1 or any(version_counts[isrc] > 1 for isrc in row["isrcs"]):
            status = "ambiguous_recording"
        elif day and day < date.fromisoformat(row["release_on"]):
            status = "chart_before_indexed_release"
        elif day:
            status = "exact_text_match"
        elif (base_title(row["title"]), lead) in loose:
            status = "possible_title_or_credit_variant"
        else:
            status = "no_text_match"
        crosswalk.append({
            **row,
            "status": status,
            "first_chart_issue_on": str(day) if day else None,
            "lead_artist_key": lead,
        })
    return crosswalk, artist_history


def build_weeks(settings, crosswalk, chart_history, label_lead):
    first = date.fromisoformat(settings["first_cutoff"])
    last = date.fromisoformat(settings["last_cutoff"])
    max_age = timedelta(days=settings["candidate_age_days"])
    lead = timedelta(days=label_lead)
    eligible = []
    artist_releases = defaultdict(list)
    for row in crosswalk:
        release = date.fromisoformat(row["release_on"])
        artist_releases[row["lead_artist_key"]].append(release)
        if row["status"] not in {"exact_text_match", "no_text_match"}:
            continue
        issue = row["first_chart_issue_on"]
        eligible.append((release, date.fromisoformat(issue) if issue else None, row["lead_artist_key"]))
    for days in artist_releases.values():
        days.sort()

    weeks = []
    for shift in range(0, (last - first).days + 1, 7):
        cutoff = first + timedelta(days=shift)
        resolves = cutoff + HORIZON
        candidates, labels = [], []
        for release, issue, artist in eligible:
            # Allow a UTC boundary after the indexed release day.
            if not cutoff - max_age <= release < cutoff:
                continue
            if issue and (issue - lead <= cutoff or issue - lead <= resolves < issue):
                continue
            chart_days = chart_history.get(artist, [])
            prior_chart = bisect_right(chart_days, cutoff) - bisect_left(chart_days, cutoff - timedelta(days=365))
            prior_releases = bisect_left(artist_releases[artist], release)
            age = (cutoff - release).days
            candidates.append((-log1p(age), log1p(prior_chart), log1p(prior_releases)))
            labels.append(int(issue is not None and issue <= resolves))
        if len(labels) < settings["k"]:
            raise ValueError(f"{cutoff} has {len(labels)} eligible recordings, requires {settings['k']}")
        # Purge the full horizon plus a conservative issue-date lead from later training splits.
        weeks.append(Week(cutoff, resolves + lead, tuple(candidates), tuple(labels)))
    return weeks


def run(config, archive, cohort, output):
    config_bytes, chart_bytes, cohort_bytes = (file.read_bytes() for file in (config, archive, cohort))
    settings = {**json.loads(config_bytes), "k": 100, "horizon_days": 90, "availability_lag_days": 7}
    source = json.loads(cohort_bytes)
    chart_end = date.fromisoformat(settings["last_cutoff"]) + HORIZON + timedelta(days=14)
    chart_start = date.fromisoformat(settings["first_release_month"] + "-01")
    check = audit(chart_bytes, chart_start, chart_end)
    if (check["nonweekly_intervals"] or check["incomplete_or_duplicate_rank_editions"]
            or date.fromisoformat(check["first_issue"]) - chart_start > timedelta(days=6)
            or chart_end - date.fromisoformat(check["last_issue"]) > timedelta(days=6)):
        raise ValueError("The archive does not completely cover the trial label period")
    # Freeze the archive boundary for a repeatable historical trial across future refreshes.
    editions = [x for x in json.loads(chart_bytes) if date.fromisoformat(x["date"]) <= chart_end]
    crosswalk, chart_history = join_cohort(source["recordings"], editions)
    output.mkdir(parents=True, exist_ok=True)
    (output / "hot100-crosswalk.json").write_text(json.dumps(crosswalk, indent=2) + "\n")

    comparison = {}
    for lead_days in (settings["chart_issue_lead_days"], 0):
        settings["availability_lag_days"] = lead_days
        weeks = build_weeks(settings, crosswalk, chart_history, lead_days)
        baselines = {"random": None, "release_recency": 0, "artist_prior_chart_activity": 1}
        challengers = {"logistic_age_catalog": (0, 2), "logistic_age_catalog_chart": (0, 1, 2)}
        result = compare(weeks, settings, hashlib.sha256(cohort_bytes).hexdigest(), baselines, challengers)
        split = date.fromisoformat(settings["test_start"])
        fits = training_before(weeks, split)
        holdout = [week for week in weeks if week.cutoff >= split]
        result["fit_positive_recording_weeks"] = sum(sum(week.labels) for week in fits)
        result["holdout_positive_recording_weeks"] = sum(sum(week.labels) for week in holdout)
        comparison[str(lead_days)] = result

    return {
        "status": "exploratory_issue_date_backtest",
        "chart_sha256": check["source_sha256"],
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "release_editions": source["release_editions"],
        "indexed_recordings_seen": source["indexed_recordings_seen"],
        "recordings": len(crosswalk),
        "recordings_with_isrc": sum(bool(row["isrcs"]) for row in crosswalk),
        "join_counts": dict(sorted(Counter(row["status"] for row in crosswalk).items())),
        "comparisons_by_issue_lead_days": comparison,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("cohort", type=Path)
    parser.add_argument("--config", type=Path, default=Path("experiments/hit100-musicbrainz.json"))
    parser.add_argument("--output", type=Path, default=Path(".forecast"))
    args = parser.parse_args()
    print(json.dumps(run(args.config, args.archive, args.cohort, args.output), indent=2, allow_nan=False))
