"""Replay weekly song-attention forecasts from a pinned daily pageview snapshot."""
import argparse
import csv
from dataclasses import dataclass
from datetime import date, timedelta
import gzip
import hashlib
from io import StringIO
import json
from math import log1p, sin, cos, tau
from pathlib import Path
from random import Random
from statistics import mean

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class Week:
    cutoff: date
    resolves: date
    candidates: tuple
    labels: tuple


def load_dataset(config, dataset):
    manifest = json.loads(dataset.with_suffix(".manifest.json").read_text())
    config_bytes = config.read_bytes()
    settings = json.loads(config_bytes)
    payload = gzip.decompress(dataset.read_bytes())
    for prefix, content in [("csv", payload), ("cohort", config_bytes)]:
        if manifest[f"{prefix}_sha256"] != hashlib.sha256(content).hexdigest():
            raise ValueError(f"{prefix} hash does not match manifest")
    start = date.fromisoformat(settings["source_start"])
    end = date.fromisoformat(settings["source_end"])
    rows = csv.reader(StringIO(payload.decode()))
    if next(rows) != ["date", *settings["pages"]]:
        raise ValueError("Dataset columns do not match the cohort")
    series = []
    for index, (day, *counts) in enumerate(rows):
        if date.fromisoformat(day) != start + timedelta(days=index):
            raise ValueError(f"Unexpected date or gap at {day}")
        points = [int(count) for count in counts]
        if len(points) != len(settings["pages"]) or min(points) < 0:
            raise ValueError(f"Invalid observation on {day}")
        series.append(points)
    if len(series) != (end - start).days + 1:
        raise ValueError("Dataset does not cover the configured range")
    return settings, start, series, manifest["csv_sha256"]


def top(scores, k):
    return sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:k]


def build_weeks(settings, start, series):
    cohort = settings["pages"]
    k, rank = settings["k"], settings["attention_rank"]
    lag, horizon = settings["availability_lag_days"], settings["horizon_days"]
    first = date.fromisoformat(settings["first_cutoff"])
    last = date.fromisoformat(settings["last_cutoff"])
    if len(set(cohort)) != len(cohort) or not 0 < k <= len(cohort) - rank or not 0 < rank < len(cohort):
        raise ValueError("Invalid cohort or rank")
    if not 0 <= lag or not 1 <= horizon <= 364 - lag or first > last:
        raise ValueError("Invalid benchmark dates")
    cumulative = np.vstack([np.zeros(len(cohort), dtype=np.int64), np.cumsum(series, axis=0)])

    weeks = []
    for shift in range(0, (last - first).days + 1, 7):
        cutoff = first + timedelta(days=shift)
        day = (cutoff - start).days
        available = day - lag
        if min(available - 84, day - 364) < 0 or day + horizon + lag > len(series):
            raise ValueError(f"Insufficient temporal coverage at {cutoff}")

        recent = cumulative[available] - cumulative[available - 28]
        prior = cumulative[available - 28] - cumulative[available - 56]
        week = cumulative[available] - cumulative[available - 7]
        quarter = cumulative[available] - cumulative[available - 84]
        seasonal = cumulative[day - 364 + horizon] - cumulative[day - 364]
        excluded = set(top(recent, rank))
        future = cumulative[day + horizon] - cumulative[day]
        entered = set(top(future, rank))
        angle = tau * (cutoff.timetuple().tm_yday - 1) / 365.25

        candidates, labels = [], []
        for i in range(len(cohort)):
            if i in excluded:
                continue
            candidates.append((
                log1p(int(recent[i])),
                log1p(int(quarter[i])),
                log1p(int(recent[i])) - log1p(int(prior[i])),
                log1p(int(week[i]) * 4) - log1p(int(recent[i])),
                log1p(int(seasonal[i])),
                sin(angle),
                cos(angle),
            ))
            labels.append(int(i in entered))
        weeks.append(Week(cutoff, cutoff + timedelta(days=horizon + lag), tuple(candidates), tuple(labels)))
    return weeks


def training_before(weeks, day):
    return [week for week in weeks if week.cutoff < day and week.resolves <= day]


def score(labels, predictions, k):
    hits = sum(labels[index] for index in top(predictions, k))
    positives = sum(labels)
    return hits / k, hits / positives if positives else None


def evaluate(weeks, predict, k, probabilities=False):
    details = []
    for week in weeks:
        predictions = predict(week)
        precision, recall = score(week.labels, predictions, k)
        brier = mean((float(value) - label) ** 2 for value, label in zip(predictions, week.labels))
        details.append((precision, recall, brier))
    recalls = [row[1] for row in details if row[1] is not None]
    summary = {
        "precision_at_k": mean(row[0] for row in details),
        "recall_at_k": mean(recalls) if recalls else None,
        "brier": mean(row[2] for row in details) if probabilities else None,
    }
    return summary, [row[0] for row in details]


def paired_interval(deltas, block, samples=4000):
    """Seeded circular moving-block bootstrap over paired weekly differences."""
    rng = Random(20261125)
    size = len(deltas)
    if not 1 <= block <= size:
        raise ValueError("Paired interval requires at least one full block")
    means = []
    for _ in range(samples):
        sample = []
        while len(sample) < size:
            start = rng.randrange(size)
            sample.extend(deltas[(start + i) % size] for i in range(block))
        means.append(mean(sample[:size]))
    return [float(value) for value in np.quantile(means, [0.025, 0.975])]


BASELINES = {
    "random": None,
    "popularity_28d": 0,
    "popularity_84d": 1,
    "momentum": 2,
    "prior_year_attention": 4,
}
CHALLENGERS = {
    "logistic_popularity": (0, 1),
    "logistic_momentum": (0, 1, 2, 3),
    "logistic_seasonality": (0, 1, 4, 5, 6),
    "logistic_all": (0, 1, 2, 3, 4, 5, 6),
}


def baseline(week, index):
    if index is not None:
        return [row[index] for row in week.candidates]
    rng = Random(week.cutoff.toordinal())
    return [rng.random() for _ in week.candidates]


def fit(weeks, indexes):
    features = np.asarray([row for week in weeks for row in week.candidates])[:, indexes]
    labels = [label for week in weeks for label in week.labels]
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
    model.fit(features, labels)
    return model


def run(config, dataset):
    settings, start, series, digest = load_dataset(config, dataset)
    weeks = build_weeks(settings, start, series)
    k = settings["k"]
    validation_start = date.fromisoformat(settings["validation_start"])
    test_start = date.fromisoformat(settings["test_start"])
    development = training_before(weeks, validation_start)
    validation = [week for week in training_before(weeks, test_start) if week.cutoff >= validation_start]
    holdout = [week for week in weeks if week.cutoff >= test_start]
    if not all([development, validation, holdout]):
        raise ValueError("Expected nonempty development, validation, and holdout periods")

    leaderboard = {}
    for name, index in BASELINES.items():
        leaderboard[name], _ = evaluate(validation, lambda week: baseline(week, index), k)
    for name, indexes in CHALLENGERS.items():
        model = fit(development, indexes)
        leaderboard[name], _ = evaluate(
            validation, lambda week: model.predict_proba(np.asarray(week.candidates)[:, indexes])[:, 1], k, True
        )

    def key(name):
        return leaderboard[name]["precision_at_k"]

    winner = max(CHALLENGERS, key=key)
    control = max(BASELINES, key=key)
    indexes = CHALLENGERS[winner]
    training = training_before(weeks, test_start)
    model = fit(training, indexes)
    winner_scores, winner_weekly = evaluate(
        holdout, lambda week: model.predict_proba(np.asarray(week.candidates)[:, indexes])[:, 1], k, True
    )
    control_scores, control_weekly = evaluate(holdout, lambda week: baseline(week, BASELINES[control]), k)
    deltas = [w - c for w, c in zip(winner_weekly, control_weekly)]
    block = (settings["horizon_days"] + settings["availability_lag_days"] + 6) // 7
    interval = paired_interval(deltas, block)
    return {
        "benchmark": settings["benchmark"],
        "dataset_sha256": digest,
        "precision_k": k,
        "validation": {
            "training_weeks": len(development),
            "weeks": len(validation),
            "strategies": leaderboard,
        },
        "holdout": {
            "fit_weeks": len(training),
            "weeks": len(holdout),
            "first_cutoff": str(holdout[0].cutoff),
            "last_cutoff": str(holdout[-1].cutoff),
            "candidates_per_week": len(holdout[0].labels),
            "zero_positive_weeks": sum(not any(week.labels) for week in holdout),
            "challenger": {"strategy": winner, **winner_scores},
            "baseline": {"strategy": control, **control_scores},
            "paired_precision_delta": mean(deltas),
            "paired_95_interval": interval,
            "moving_block_weeks": block,
            "hillclimb_observed": interval[0] > 0,
            "paired_weekly": [
                {"cutoff": str(week.cutoff), "challenger_precision": w, "baseline_precision": c}
                for week, w, c in zip(holdout, winner_weekly, control_weekly)
            ],
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("experiments/attention-cohort.json"))
    parser.add_argument("--dataset", type=Path, default=Path("experiments/pageviews.csv.gz"))
    args = parser.parse_args()
    print(json.dumps(run(args.config, args.dataset), indent=2, allow_nan=False))
