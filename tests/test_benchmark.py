import unittest
from datetime import date, timedelta

from forecasting.benchmark import build_weeks, paired_interval, score, training_before


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.cutoff = date(2022, 1, 3)
        self.start = self.cutoff - timedelta(days=450)
        self.series = [[100, 40, 10] for _ in range(490)]
        self.settings = {
            "pages": ["a", "b", "c"],
            "first_cutoff": str(self.cutoff),
            "last_cutoff": str(self.cutoff),
            "horizon_days": 28,
            "availability_lag_days": 7,
            "attention_rank": 1,
            "k": 1,
        }

    def test_recent_unavailable_counts_do_not_enter_features(self):
        before = build_weeks(self.settings, self.start, self.series)[0]
        offset = (self.cutoff - self.start).days
        self.series[offset - 1] = [0, 1_000_000, 20]
        after = build_weeks(self.settings, self.start, self.series)[0]
        self.assertEqual(before.candidates, after.candidates)

    def test_future_values_change_labels_only(self):
        before = build_weeks(self.settings, self.start, self.series)[0]
        offset = (self.cutoff - self.start).days
        for i in range(offset, offset + 28):
            self.series[i] = [1, 5, 50]
        after = build_weeks(self.settings, self.start, self.series)[0]
        self.assertEqual(before.candidates, after.candidates)
        self.assertEqual(after.labels, (0, 1))
        self.assertEqual(after.resolves, self.cutoff + timedelta(days=35))

    def test_training_excludes_unresolved_outcomes(self):
        week = build_weeks(self.settings, self.start, self.series)[0]
        self.assertEqual(training_before([week], week.resolves - timedelta(days=1)), [])
        self.assertEqual(training_before([week], week.resolves), [week])

    def test_incomplete_lookback_fails(self):
        with self.assertRaisesRegex(ValueError, "coverage"):
            build_weeks(self.settings, self.start + timedelta(days=150), self.series)

    def test_paired_interval_for_no_difference(self):
        self.assertEqual(paired_interval([0.0] * 20, 5), [0.0, 0.0])

    def test_top_k_metrics_and_zero_positive_cutoff(self):
        self.assertEqual(score((0, 1, 1), [0.8, 0.5, 0.4], 2), (0.5, 0.5))
        self.assertEqual(score((0, 0), [0.8, 0.5], 1), (0.0, None))
