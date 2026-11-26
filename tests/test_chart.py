from datetime import date, timedelta
import unittest

from forecasting.chart import build_chart_weeks


class ChartTests(unittest.TestCase):
    cutoff = date(2021, 1, 4)

    def bundle(self):
        c = self.cutoff
        return {
            "benchmark": "hit-100",
            "first_cutoff": str(c),
            "last_cutoff": str(c),
            "validation_start": "2022-01-03",
            "test_start": "2023-01-02",
            "coverage": {
                "approval_ref": "TEST-ONLY",
                "prior_chart_history_complete": True,
                "first_release_cutoff_covered": str(c),
                "last_release_cutoff_covered": str(c),
                "labels_complete_through": str(c + timedelta(days=90)),
            },
            "recordings": [
                {"id": f"{i:03d}", "release_on": "2020-01-01", "release_available_on": "2020-01-02",
                 "first_chart_on": "2021-01-05" if i == 0 else ("2020-12-28" if i == 100 else None)}
                for i in range(101)
            ],
            "observations": [
                {"id": "000", "occurred_on": "2020-12-25", "available_on": "2021-01-01", "value": 30},
                {"id": "000", "occurred_on": "2020-12-25", "available_on": "2021-01-05", "value": 3000},
            ],
        }

    def test_keeps_noncharters_excludes_chart_history_and_uses_vintage(self):
        bundle = self.bundle()
        _, weeks = build_chart_weeks(bundle)
        week = weeks[0]
        self.assertEqual(len(week.labels), 100)
        self.assertEqual(sum(week.labels), 1)
        bundle["observations"].pop()
        self.assertEqual(week, build_chart_weeks(bundle)[1][0])

    def test_fails_closed_for_unresolved_horizon(self):
        bundle = self.bundle()
        bundle["coverage"]["labels_complete_through"] = "2021-02-01"
        with self.assertRaisesRegex(ValueError, "coverage"):
            build_chart_weeks(bundle)

    def test_late_release_availability_does_not_enter_cohort(self):
        bundle = self.bundle()
        bundle["recordings"][1]["release_available_on"] = "2021-01-05"
        with self.assertRaisesRegex(ValueError, "eligible"):
            build_chart_weeks(bundle)

    def test_requires_authoritative_prior_history(self):
        bundle = self.bundle()
        bundle["coverage"]["prior_chart_history_complete"] = False
        with self.assertRaisesRegex(ValueError, "prior chart history"):
            build_chart_weeks(bundle)
