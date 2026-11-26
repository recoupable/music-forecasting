from datetime import date
import unittest

from forecasting.hit100_cohort import build_weeks, join_cohort


class Hit100CohortTests(unittest.TestCase):
    def test_exact_collaborator_match_and_ambiguous_version(self):
        recordings = [
            {"title": "Song", "artist": "Artist feat. Guest", "isrcs": ["one"], "release_on": "2024-01-05"},
            {"title": "Song (Remix)", "artist": "Artist", "isrcs": ["two"], "release_on": "2024-01-05"},
            {"title": "Other", "artist": "Artist", "isrcs": ["dup"], "release_on": "2024-01-05"},
            {"title": "Other edit", "artist": "Artist", "isrcs": ["dup"], "release_on": "2024-01-05"},
        ]
        editions = [
            {"date": "2024-02-03", "data": [{"song": "Song", "artist": "Artist Featuring Guest"}]},
            {"date": "2024-02-10", "data": [{"song": "Song", "artist": "Artist & Guest"}]},
        ]
        joined, _ = join_cohort(recordings, editions)
        self.assertEqual(joined[0]["status"], "exact_text_match")
        self.assertEqual(joined[0]["first_chart_issue_on"], "2024-02-03")
        self.assertEqual(joined[1]["status"], "possible_title_or_credit_variant")
        self.assertEqual(joined[2]["status"], "ambiguous_recording")
        self.assertEqual(joined[3]["status"], "ambiguous_recording")

    def test_label_boundary_uncertainty_is_excluded(self):
        candidates = [
            {"release_on": "2024-01-01", "first_chart_issue_on": issue,
             "status": "exact_text_match" if issue else "no_text_match", "lead_artist_key": "artist"}
            for issue in ("2024-01-13", "2024-02-03", "2024-04-13", None)
        ]
        settings = {"k": 1, "candidate_age_days": 180, "first_cutoff": "2024-01-08", "last_cutoff": "2024-01-08"}
        week, = build_weeks(settings, candidates, {"artist": [date(2024, 1, 6), date(2024, 1, 13)]}, 7)
        self.assertEqual(week.labels, (1, 0))
        self.assertEqual(week.resolves, date(2024, 4, 14))
        self.assertEqual(week.candidates[0][1], week.candidates[1][1])
