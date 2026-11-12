"""Offline tests for the job-hunt scripts. Run: python -m unittest test_job_hunt (no network)."""
import json
import os
import tempfile
import unittest

import fetch_jobs
import report


def job(jid, title="Backend Engineer", company="Acme", **kw):
    return {"job_id": jid, "title": title, "company": company, "description": "x" * 5000,
            "apply_options": [{"title": "Site", "link": None}, {"title": "Acme", "link": f"https://acme.example/{jid}"}], **kw}


def score(jid, s, applied="no", **kw):
    return {"job_id": jid, "score": s, "reasons": ["fits"], "applied": applied, **kw}


CFG = {"queries": ["q"], "minScore": 7, "maxGmailChecks": 2, "topHighlights": 1}


class SelectNew(unittest.TestCase):
    def test_skips_seen_id_and_seen_title_company(self):
        seen = fetch_jobs.seen_keys(job("a")) | fetch_jobs.seen_keys(job("b", title="Data Engineer", company="Beta"))
        jobs = [job("a"), job("c", title="Data  engineer", company="BETA"), job("d", title="SRE")]
        self.assertEqual([j["job_id"] for j in fetch_jobs.select_new(jobs, seen)], ["d"])

    def test_dedupes_inside_batch_and_excludes_companies(self):
        jobs = [job("a"), job("b"), job("c", company="Evil Corp"), job("d", title="SRE")]
        got = fetch_jobs.select_new(jobs, set(), exclude_companies=["evil corp"])
        self.assertEqual([j["job_id"] for j in got], ["a", "d"])

    def test_slim_takes_first_real_link_and_cuts_description(self):
        s = fetch_jobs.slim(job("a"))
        self.assertEqual(s["link"], "https://acme.example/a")
        self.assertEqual(len(s["description"]), fetch_jobs.DESCRIPTION_LIMIT)


class BestLinks(unittest.TestCase):
    """Cases from a real run (2026-11-12): reposting sites often come first in apply_options."""

    def opts(self, *pairs):
        return [{"title": t, "link": l} for t, l in pairs]

    def test_ats_beats_earlier_boards(self):
        j = {"company": "Expeditors", "apply_options": self.opts(
            ("Apply directly on Indeed", "https://www.indeed.com/viewjob?jk=1"),
            ("Apply on JobLeads", "https://www.jobleads.com/us/job/x"),
            ("Apply on Smart Recruiters Jobs", "https://jobs.smartrecruiters.com/Expeditors/7"))}
        self.assertEqual(fetch_jobs.best_links(j), ["https://jobs.smartrecruiters.com/Expeditors/7",
                                                    "https://www.indeed.com/viewjob?jk=1", "https://www.jobleads.com/us/job/x"])

    def test_company_careers_title_first_and_big_board_before_repost(self):
        j = {"company": "WEXWEXUS", "apply_options": self.opts(
            ("Apply on JobLeads", "https://www.jobleads.com/us/job/y"),
            ("Apply on LinkedIn", "https://www.linkedin.com/jobs/view/z"),
            ("Apply on WEX Careers", "https://careers.wexinc.com/us/en/job/R1"))}
        self.assertEqual(fetch_jobs.best_links(j)[:2], ["https://careers.wexinc.com/us/en/job/R1", "https://www.linkedin.com/jobs/view/z"])

    def test_only_reposts_keeps_google_order(self):
        j = {"company": "Coinbase, Inc.", "apply_options": self.opts(("Apply on Trabajo.org", "https://us.trabajo.org/a"))}
        s = fetch_jobs.slim(dict(job("a"), **j))
        self.assertEqual((s["link"], s["link_kind"]), ("https://us.trabajo.org/a", "repost"))


class Validate(unittest.TestCase):
    jobs = [job("a"), job("b"), job("c")]

    def test_ok(self):
        scores = [score("a", 9, highlights=["Kafka"]), score("b", 8), score("c", 3, applied="unchecked")]
        self.assertEqual(report.validate(self.jobs, scores, CFG), [])

    def test_missing_extra_duplicate(self):
        scores = [score("a", 2), score("a", 2), score("z", 2)]
        errs = report.validate(self.jobs, scores, CFG)
        self.assertTrue(any("b: no score" in e for e in errs))
        self.assertTrue(any("z: not in the jobs file" in e for e in errs))
        self.assertTrue(any("a: scored more than once" in e for e in errs))

    def test_bad_fields(self):
        scores = [score("a", 11), score("b", 5, reasons=[]), score("c", 5, applied="yes")]
        errs = report.validate(self.jobs, scores, CFG)
        self.assertEqual(len(errs), 3, errs)

    def test_top_must_be_gmail_checked_and_top_apply_needs_highlights(self):
        scores = [score("a", 9, applied="unchecked"), score("b", 8, applied="yes", applied_evidence="Thanks for applying, 2026-11-01"),
                  score("c", 7, applied="unchecked")]
        errs = report.validate(self.jobs, scores, CFG)
        self.assertEqual(sorted(e.split(":")[0] for e in errs), ["a", "a"], errs)  # c is 3rd; only top 2 need Gmail

    def test_unchecked_below_gmail_limit_is_allowed(self):
        cfg = dict(CFG, maxGmailChecks=1)
        scores = [score("a", 9, highlights=["x"]), score("b", 8, applied="unchecked"), score("c", 1, applied="unchecked")]
        self.assertEqual(report.validate(self.jobs, scores, cfg), [])


class EndToEnd(unittest.TestCase):
    def test_fetch_score_report_then_seen_blocks_rerun(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "job-hunt.json"), "w") as f:
                json.dump(CFG, f)
            data = os.path.join(d, "dataset.json")
            with open(data, "w") as f:
                json.dump([job("a"), job("b", title="SRE"), job("c", title="Intern")], f)

            fetch_jobs.main(["--workdir", d, "--from-file", data, "--date", "2026-11-12"])
            day = os.path.join(d, "days", "2026-11-12")
            with open(day + ".jobs.json") as f:
                self.assertEqual(len(json.load(f)), 3)

            with open(day + ".scores.json", "w") as f:
                json.dump([score("a", 9, highlights=["Go"]), score("b", 7, applied="yes", applied_evidence="Your application, 2026-11-02"),
                           score("c", 2, applied="unchecked", reasons=["intern | role"])], f)
            self.assertEqual(report.main(["--workdir", d, "--date", "2026-11-12"]), 0)
            with open(day + ".md") as f:
                md = f.read()
            self.assertIn("### 1. Backend Engineer at Acme (9/10)", md)
            self.assertIn("## Already applied (skipped)", md)
            self.assertNotIn("only reposting sites", md)  # acme.example link has "Acme" in its title
            self.assertIn("| 2 | Intern | Acme | intern / role |", md)

            fetch_jobs.main(["--workdir", d, "--from-file", data, "--date", "2026-11-13"])
            with open(os.path.join(d, "days", "2026-11-13.jobs.json")) as f:
                self.assertEqual(json.load(f), [])

    def test_bad_scores_exit_1_and_seen_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "job-hunt.json"), "w") as f:
                json.dump(CFG, f)
            os.makedirs(os.path.join(d, "days"))
            day = os.path.join(d, "days", "2026-11-12")
            with open(day + ".jobs.json", "w") as f:
                json.dump([fetch_jobs.slim(job("a"))], f)
            with open(day + ".scores.json", "w") as f:
                json.dump([], f)
            self.assertEqual(report.main(["--workdir", d, "--date", "2026-11-12"]), 1)
            self.assertFalse(os.path.exists(os.path.join(d, "seen.json")))


if __name__ == "__main__":
    unittest.main()
