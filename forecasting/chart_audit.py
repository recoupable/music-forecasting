"""Summarize a Hot 100 JSON archive without exporting chart rows."""
import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path


def audit(payload, start, through):
    if through < start:
        raise ValueError("End date precedes start date")
    source = json.loads(payload)
    editions = []
    edition_fields = set()
    for edition in source:
        issue = date.fromisoformat(edition["date"])
        if start <= issue <= through:
            editions.append((issue, edition["data"]))
            edition_fields.update(edition)
    editions.sort(key=lambda entry: entry[0])
    if not editions:
        raise ValueError("No editions in the selected period")

    dates = [issue for issue, _ in editions]
    invalid = [
        issue.isoformat()
        for issue, entries in editions
        if Counter(entry["this_week"] for entry in entries) != Counter(range(1, 101))
    ]
    return {
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "first_issue": dates[0].isoformat(),
        "last_issue": dates[-1].isoformat(),
        "editions": len(editions),
        "rank_rows": sum(len(entries) for _, entries in editions),
        "duplicate_issue_dates": [issue.isoformat() for issue, count in Counter(dates).items() if count > 1],
        "incomplete_or_duplicate_rank_editions": invalid,
        "nonweekly_intervals": [
            {"from": str(left), "to": str(right), "days": (right - left).days}
            for left, right in zip(dates, dates[1:])
            if (right - left).days != 7
        ],
        "rank_fields": sorted({key for _, entries in editions for row in entries for key in row}),
        "edition_fields": sorted(edition_fields),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--through", required=True, type=date.fromisoformat)
    args = parser.parse_args()
    print(json.dumps(audit(args.archive.read_bytes(), args.start, args.through), indent=2))
