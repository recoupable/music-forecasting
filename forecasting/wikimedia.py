"""Acquire a fixed cohort of public Wikimedia Analytics pageview series."""
import argparse
import csv
from datetime import date, timedelta
import gzip
import hashlib
from io import StringIO
import json
from pathlib import Path
import subprocess
from urllib.parse import quote

BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user"
AGENT = "RecoupMusicForecasting/0.1 (https://github.com/recoupable/music-forecasting)"


def fetch(url):
    return subprocess.run(
        ["curl", "--fail", "--silent", "--show-error", "--retry", "3", "--retry-max-time", "90",
         "--max-time", "60", "--user-agent", AGENT, url],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def acquire(config, output, cache):
    config_bytes = config.read_bytes()
    settings = json.loads(config_bytes)
    start = date.fromisoformat(settings["source_start"])
    end = date.fromisoformat(settings["source_end"])
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    expected = set(days)
    series = {}
    sources = {}
    cache.mkdir(parents=True, exist_ok=True)
    for page in settings["pages"]:
        url = f"{BASE}/{quote(page, safe='')}/daily/{start:%Y%m%d}/{end:%Y%m%d}"
        cached = cache / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        data = cached.read_bytes() if cached.is_file() else fetch(url)
        points = {}
        for item in json.loads(data)["items"]:
            day = date.fromisoformat(item["timestamp"][:8])
            views = item["views"]
            if day in points or not isinstance(views, int) or views < 0:
                raise ValueError(f"{page}: invalid or duplicate observation on {day}")
            points[day] = views
        if points.keys() != expected:
            missing = sorted(expected - points.keys())
            raise ValueError(f"{page}: incomplete source coverage ({len(missing)} dates missing, first {missing[:2]})")
        if not cached.is_file():
            cached.write_bytes(data)
        series[page] = points
        sources[page] = {"url": url, "response_sha256": hashlib.sha256(data).hexdigest()}
        print(f"{page}: {len(points)} daily observations", flush=True)

    csv_data = StringIO(newline="")
    writer = csv.writer(csv_data, lineterminator="\n")
    writer.writerow(["date", *series])
    writer.writerows([day.isoformat(), *(points[day] for points in series.values())] for day in days)
    payload = csv_data.getvalue().encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(gzip.compress(payload, mtime=0))
    manifest = {
        "benchmark": settings["benchmark"],
        "source_license": "CC0-1.0",
        "csv_sha256": hashlib.sha256(payload).hexdigest(),
        "cohort_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "source_series": sources,
    }
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("experiments/attention-cohort.json"))
    parser.add_argument("--output", type=Path, default=Path("experiments/pageviews.csv.gz"))
    parser.add_argument("--cache", type=Path, default=Path(".forecast/wikimedia"))
    args = parser.parse_args()
    acquire(args.config, args.output, args.cache)
