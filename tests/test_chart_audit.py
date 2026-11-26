from datetime import date
import json
import unittest

from forecasting.chart_audit import audit


class ChartAuditTests(unittest.TestCase):
    def test_detects_missing_rank_and_week_without_reading_future_editions(self):
        ranks = [{"this_week": n} for n in range(1, 101)]
        payload = json.dumps([
            {"date": "2024-01-06", "data": ranks},
            {"date": "2024-01-20", "data": [*ranks[:-1], ranks[0]]},
            {"date": "2024-02-03", "data": [], "extra": True},
        ]).encode()
        results = audit(payload, date(2024, 1, 1), date(2024, 1, 31))
        self.assertEqual(results["editions"], 2)
        self.assertEqual(results["rank_rows"], 200)
        self.assertEqual(results["incomplete_or_duplicate_rank_editions"], ["2024-01-20"])
        self.assertEqual(results["nonweekly_intervals"], [{"from": "2024-01-06", "to": "2024-01-20", "days": 14}])
        self.assertEqual(results["edition_fields"], ["data", "date"])
