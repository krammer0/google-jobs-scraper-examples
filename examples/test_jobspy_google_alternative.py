"""Offline tests: no network, no token."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jobspy_google_alternative import COLUMNS, hours_old_to_date_posted, to_jobspy_row


class HoursOld(unittest.TestCase):
    def test_boundaries(self):
        cases = [(None, None), (24, "24h"), (25, "3d"), (72, "3d"), (73, "7d"), (168, "7d"), (169, "30d")]
        for hours, expected in cases:
            with self.subTest(hours=hours):
                self.assertEqual(hours_old_to_date_posted(hours), expected)


class Row(unittest.TestCase):
    def test_full_item(self):
        item = {
            "job_id": "abc==", "title": "Dev", "company": "Example", "location": "NY",
            "description": "text", "postedDate": "2026-11-05",
            "apply_options": [{"title": "A", "link": "https://a.example"}, {"title": "B", "link": "https://b.example"}],
            "salaryMin": 100, "salaryMax": 200, "salaryCurrency": "USD", "salaryPeriod": "year",
            "jobTypes": ["FULLTIME", "CONTRACTOR"], "workMode": "remote",
        }
        row = to_jobspy_row(item)
        self.assertEqual(list(row), COLUMNS)
        self.assertEqual(row["id"], "go-abc==")
        self.assertEqual(row["site"], "google")
        self.assertEqual(row["job_url"], "https://a.example")
        self.assertEqual(row["date_posted"], "2026-11-05")
        self.assertEqual(row["job_type"], "fulltime,contract")
        self.assertEqual(row["interval"], "yearly")
        self.assertEqual((row["min_amount"], row["max_amount"], row["currency"]), (100, 200, "USD"))
        self.assertTrue(row["is_remote"])

    def test_empty_item(self):
        row = to_jobspy_row({})
        self.assertIsNone(row["id"])
        self.assertEqual(row["site"], "google")
        for key in COLUMNS:
            if key not in ("site", "is_remote"):
                self.assertIsNone(row[key], key)
        self.assertFalse(row["is_remote"])

    def test_null_lists(self):
        row = to_jobspy_row({"apply_options": None, "jobTypes": None})
        self.assertIsNone(row["job_url"])
        self.assertIsNone(row["job_type"])

    def test_salary_period(self):
        for src, dst in [("hour", "hourly"), ("day", "daily"), ("week", "weekly"), ("month", "monthly"), ("year", "yearly")]:
            self.assertEqual(to_jobspy_row({"salaryPeriod": src})["interval"], dst)
        self.assertIsNone(to_jobspy_row({"salaryPeriod": "decade"})["interval"])

    def test_job_type(self):
        for src, dst in [("FULLTIME", "fulltime"), ("PARTTIME", "parttime"), ("CONTRACTOR", "contract"), ("INTERN", "internship")]:
            self.assertEqual(to_jobspy_row({"jobTypes": [src]})["job_type"], dst)

    def test_is_remote(self):
        self.assertTrue(to_jobspy_row({"workMode": "remote"})["is_remote"])
        self.assertFalse(to_jobspy_row({"workMode": "hybrid"})["is_remote"])
        self.assertFalse(to_jobspy_row({"workMode": None})["is_remote"])


if __name__ == "__main__":
    unittest.main()
