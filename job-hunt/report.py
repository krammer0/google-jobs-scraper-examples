"""Last step of the job-hunt skill: check Claude's scores and write the daily list.

Reads days/<date>.jobs.json (from fetch_jobs.py) and days/<date>.scores.json (written
by Claude), checks that the scores file is complete, writes days/<date>.md, and adds
the jobs to seen.json so they do not come back tomorrow.

Exit code 0: report written. Exit code 1: the scores file has problems (printed); fix and run again.

Example:
    python report.py --workdir ~/job-hunt
"""
import argparse
import datetime as dt
import json
import os
import sys

from fetch_jobs import load_config, load_seen, seen_keys

APPLIED = {"yes", "no", "unchecked"}


def candidates(scores, min_score):
    """Jobs at or above min_score, best first."""
    return sorted((s for s in scores if s["score"] >= min_score), key=lambda s: -s["score"])


def validate(jobs, scores, cfg):
    min_score = cfg.get("minScore", 7)
    gmail_checks = cfg.get("maxGmailChecks", 10)
    top_highlights = cfg.get("topHighlights", 3)
    errors = []

    job_ids = [j["job_id"] for j in jobs]
    score_ids = [s.get("job_id") for s in scores]
    for jid in sorted(set(job_ids) - set(score_ids)):
        errors.append(f"{jid}: no score")
    for jid in sorted(set(score_ids) - set(job_ids)):
        errors.append(f"{jid}: not in the jobs file")
    for jid in sorted({x for x in score_ids if score_ids.count(x) > 1}):
        errors.append(f"{jid}: scored more than once")

    for s in scores:
        jid = s.get("job_id")
        if not isinstance(s.get("score"), int) or not 0 <= s["score"] <= 10:
            errors.append(f"{jid}: score must be an integer 0-10")
            s["score"] = -1
        if not s.get("reasons") or not all(isinstance(r, str) and r for r in s["reasons"]):
            errors.append(f"{jid}: reasons must be a non-empty list of strings")
        if s.get("applied", "unchecked") not in APPLIED:
            errors.append(f"{jid}: applied must be one of {sorted(APPLIED)}")
        if s.get("applied") == "yes" and not s.get("applied_evidence"):
            errors.append(f"{jid}: applied=yes needs applied_evidence (email subject and date)")
    if errors:
        return errors

    top = candidates(scores, min_score)
    for s in top[:gmail_checks]:
        if s.get("applied", "unchecked") == "unchecked":
            errors.append(f"{s['job_id']}: score {s['score']} is in the top {gmail_checks}; check Gmail (applied yes/no)")
    to_apply = [s for s in top if s.get("applied") != "yes"]
    for s in to_apply[:top_highlights]:
        if not s.get("highlights"):
            errors.append(f"{s['job_id']}: in the top {top_highlights} to apply; add resume highlights")
    return errors


def bullets(items):
    return "".join(f"  - {x}\n" for x in items or [])


def render(date, jobs, scores, cfg):
    min_score = cfg.get("minScore", 7)
    by_id = {j["job_id"]: j for j in jobs}
    top = candidates(scores, min_score)
    to_apply = [s for s in top if s.get("applied") != "yes"]
    applied = [s for s in top if s.get("applied") == "yes"]
    low = sorted((s for s in scores if s["score"] < min_score), key=lambda s: -s["score"])

    out = [f"# Job hunt: {date}\n\n"]
    out.append(f"{len(jobs)} new jobs. {len(to_apply)} to apply (score {min_score}+), "
               f"{len(applied)} already applied, {len(low)} below {min_score}.\n\n")
    out.append("## Apply today\n\n")
    if not to_apply:
        out.append("Nothing today.\n\n")
    for n, s in enumerate(to_apply, 1):
        j = by_id[s["job_id"]]
        out.append(f"### {n}. {j['title']} at {j['company']} ({s['score']}/10)\n\n")
        meta = " | ".join(x for x in (j.get("location"), j.get("salary"), j.get("posted")) if x)
        if meta:
            out.append(f"{meta}\n\n")
        out.append("- Why it fits:\n" + bullets(s["reasons"]))
        if s.get("gaps"):
            out.append("- Gaps:\n" + bullets(s["gaps"]))
        if s.get("highlights"):
            out.append("- Put first in your resume:\n" + bullets(s["highlights"]))
        if s.get("applied", "unchecked") == "unchecked":
            out.append("- Gmail: not checked\n")
        out.append(f"- Apply: {j.get('link') or 'no link; search the company careers page'}\n")
        if j.get("link_kind") == "repost":
            out.append("  - only reposting sites found; apply on the company careers page if you can\n")
        for other in j.get("other_links") or []:
            out.append(f"  - also: {other}\n")
        out.append("\n")
    if applied:
        out.append("## Already applied (skipped)\n\n")
        for s in applied:
            j = by_id[s["job_id"]]
            out.append(f"- {j['title']} at {j['company']}: {s['applied_evidence']}\n")
        out.append("\n")
    if low:
        out.append(f"## Below {min_score}\n\n| Score | Job | Company | Main reason |\n|---|---|---|---|\n")
        for s in low:
            j = by_id[s["job_id"]]
            reason = s["reasons"][0].replace("|", "/")
            out.append(f"| {s['score']} | {j['title']} | {j['company']} | {reason} |\n")
    return "".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workdir", default=".")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args(argv)

    cfg = load_config(os.path.join(a.workdir, "job-hunt.json"))
    day = os.path.join(a.workdir, "days", a.date)
    with open(day + ".jobs.json") as f:
        jobs = json.load(f)
    with open(day + ".scores.json") as f:
        scores = json.load(f)

    errors = validate(jobs, scores, cfg)
    if errors:
        print(f"{len(errors)} problems in {day}.scores.json:")
        print("\n".join("- " + e for e in errors))
        return 1

    with open(day + ".md", "w") as f:
        f.write(render(a.date, jobs, scores, cfg))

    seen_path = os.path.join(a.workdir, "seen.json")
    seen = load_seen(seen_path)
    for j in jobs:
        seen |= seen_keys(j)
    with open(seen_path, "w") as f:
        json.dump(sorted(seen), f, indent=0)
    print(f"report -> {day}.md ({len(seen)} keys in seen.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
