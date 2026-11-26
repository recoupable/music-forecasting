"""Replay HIT-100 from an operator-qualified private chart benchmark bundle."""

import argparse
from collections import defaultdict
from datetime import date, timedelta
import hashlib
import json
from math import isfinite, log1p
from pathlib import Path

from .benchmark import Week, compare


def build_chart_weeks(bundle):
    """Use date-grain provider vintages. A day means verified available by 00:00 UTC."""
    coverage = bundle["coverage"]
    if not coverage["approval_ref"] or coverage["prior_chart_history_complete"] is not True:
        raise ValueError("An approval reference and complete prior chart history are required")
    first = date.fromisoformat(bundle["first_cutoff"])
    last = date.fromisoformat(bundle["last_cutoff"])
    horizon = timedelta(days=90)
    if not (
        date.fromisoformat(coverage["first_release_cutoff_covered"]) <= first <= last
        <= date.fromisoformat(coverage["last_release_cutoff_covered"])
        and last + horizon <= date.fromisoformat(coverage["labels_complete_through"])
    ):
        raise ValueError("Insufficient candidate or label coverage")

    recordings = {}
    for item in bundle["recordings"]:
        rid = item["id"]
        released = date.fromisoformat(item["release_on"])
        available = date.fromisoformat(item["release_available_on"])
        charted = date.fromisoformat(item["first_chart_on"]) if item["first_chart_on"] else None
        if not rid or rid in recordings or (charted and charted < released):
            raise ValueError(f"Invalid or duplicate recording {rid}")
        recordings[rid] = (released, available, charted)

    observations = defaultdict(list)
    vintages = set()
    for item in bundle["observations"]:
        rid = item["id"]
        occurred = date.fromisoformat(item["occurred_on"])
        available = date.fromisoformat(item["available_on"])
        value = item["value"]
        vintage = (rid, occurred, available)
        if rid not in recordings or occurred > available or not isfinite(value) or value < 0 or vintage in vintages:
            raise ValueError(f"Invalid or duplicate observation {vintage}")
        vintages.add(vintage)
        observations[rid].append((available, occurred, value))
    for events in observations.values():
        events.sort()

    weeks = []
    for offset in range(0, (last - first).days + 1, 7):
        cutoff = first + timedelta(days=offset)
        resolves = cutoff + horizon
        windows = [cutoff - timedelta(days=days) for days in (7, 28, 56, 84)]
        candidates, labels = [], []
        for rid, (release, available, charted) in sorted(recordings.items()):
            if max(release, available) > cutoff or (charted and charted <= cutoff):
                continue
            visible = {}
            for vintage, occurred, value in observations[rid]:
                if vintage > cutoff:
                    break
                if windows[3] <= occurred < cutoff:
                    visible[occurred] = value
            week = sum(v for day, v in visible.items() if day >= windows[0])
            recent = sum(v for day, v in visible.items() if day >= windows[1])
            prior = sum(v for day, v in visible.items() if windows[2] <= day < windows[1])
            candidates.append((
                log1p(recent),
                log1p(sum(visible.values())),
                log1p(recent) - log1p(prior),
                log1p(week * 4) - log1p(recent),
                len(visible) / 84,
            ))
            labels.append(int(charted is not None and charted <= resolves))
        if len(labels) < 100:
            raise ValueError(f"{cutoff}: fewer than 100 eligible candidates")
        weeks.append(Week(cutoff, resolves, tuple(candidates), tuple(labels)))
    settings = {
        "benchmark": bundle["benchmark"], "k": 100, "horizon_days": 90, "availability_lag_days": 0,
        "validation_start": bundle["validation_start"], "test_start": bundle["test_start"],
    }
    return settings, weeks


def run_chart(path):
    payload = path.read_bytes()
    settings, weeks = build_chart_weeks(json.loads(payload))
    baselines = {"random": None, "popularity_28d": 0, "popularity_84d": 1, "momentum": 2}
    challengers = {"logistic_popularity": (0, 1), "logistic_momentum": (0, 1, 2, 3),
                   "logistic_with_coverage": (0, 1, 2, 3, 4)}
    return compare(weeks, settings, hashlib.sha256(payload).hexdigest(), baselines, challengers)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    print(json.dumps(run_chart(args.bundle), indent=2, allow_nan=False))
