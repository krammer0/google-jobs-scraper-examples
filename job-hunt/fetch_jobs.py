"""Step 1 of the job-hunt skill: get today's new Google Jobs listings.

Reads the search settings from job-hunt.json, runs the Google Jobs Scraper Actor
(or reads a saved dataset with --from-file), removes jobs you have already seen,
and writes a short JSON file for Claude to score.

Example:
    python fetch_jobs.py --workdir ~/job-hunt
    python fetch_jobs.py --workdir ~/job-hunt --from-file dataset.json   # no Apify call
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

ACTOR = "krammer/google-jobs-scraper"
DESCRIPTION_LIMIT = 4000  # characters; keeps the file small enough for Claude to read


def load_config(path):
    with open(path) as f:
        cfg = json.load(f)
    if not cfg.get("queries"):
        sys.exit(f"{path}: 'queries' must be a non-empty list")
    return cfg


def run_actor(cfg):
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("Set APIFY_TOKEN first: export APIFY_TOKEN=<your token>")
    from apify_client import ApifyClient

    client = ApifyClient(token)
    run_input = {
        "queries": cfg["queries"],
        "locations": cfg.get("locations", []),
        "country": cfg.get("country", "us"),
        "datePosted": cfg.get("datePosted", "24h"),
        "maxResultsPerSearch": cfg.get("maxResultsPerSearch", 30),
    }
    run = client.actor(ACTOR).call(run_input=run_input)
    if run is None or run.get("status") != "SUCCEEDED":
        status = run.get("status") if run else "unknown"
        sys.exit(f"Run did not succeed (status: {status}). Check the run log in Apify Console.")
    return list(client.dataset(run["defaultDatasetId"]).iterate_items())


def norm(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def seen_keys(job):
    """A job can come back with a new job_id, so title + company is a second key."""
    return {"id:" + job["job_id"], "tc:" + norm(job.get("title")) + "|" + norm(job.get("company"))}


ATS_HOSTS = ("greenhouse.io", "lever.co", "ashbyhq.com", "myworkdayjobs.com", "smartrecruiters.com",
             "workable.com", "icims.com", "jobvite.com")
BIG_BOARDS = ("linkedin.com", "indeed.com", "glassdoor.com", "ziprecruiter.com", "builtin", "dice.com",
              "levels.fyi", "wellfound.com")


def link_rank(option, company):
    """0 = company careers page or ATS, 1 = big job board, 2 = other reposting site."""
    link, title = (option.get("link") or "").lower(), (option.get("title") or "").lower()
    first_word = norm(company).split(" ")[0] if norm(company) else ""
    if any(h in link for h in ATS_HOSTS) or "careers" in title or (first_word and first_word in norm(title)):
        return 0
    if any(b in link for b in BIG_BOARDS):
        return 1
    return 2


def best_links(job, n=3):
    options = [o for o in job.get("apply_options") or [] if o.get("link")]
    options.sort(key=lambda o: link_rank(o, job.get("company")))  # stable: keeps Google's order inside a rank
    return [o["link"] for o in options[:n]]


def slim(job):
    links = best_links(job)
    link = links[0] if links else None
    first = next((o for o in job.get("apply_options") or [] if o.get("link") == link), {})
    return {
        "job_id": job["job_id"],
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "salary": job.get("salary"),
        "posted": job.get("postedDate") or job.get("posted"),
        "link": link,
        "other_links": links[1:],
        "link_kind": ["company", "job board", "repost"][link_rank(first, job.get("company"))] if link else None,
        "description": (job.get("description") or "")[:DESCRIPTION_LIMIT],
    }


def select_new(jobs, seen, exclude_companies=()):
    """Return new jobs: not seen before, not from an excluded company, no duplicates in this batch."""
    excluded = {norm(c) for c in exclude_companies}
    out, batch = [], set()
    for job in jobs:
        if not job.get("job_id") or norm(job.get("company")) in excluded:
            continue
        keys = seen_keys(job)
        if keys & seen or keys & batch:
            continue
        batch |= keys
        out.append(slim(job))
    return out


def load_seen(path):
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return set(json.load(f))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workdir", default=".", help="folder with job-hunt.json and resume.md")
    ap.add_argument("--from-file", help="use a saved dataset JSON (list of jobs) instead of calling Apify")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args(argv)

    cfg = load_config(os.path.join(a.workdir, "job-hunt.json"))
    if a.from_file:
        with open(a.from_file) as f:
            jobs = json.load(f)
    else:
        jobs = run_actor(cfg)

    seen = load_seen(os.path.join(a.workdir, "seen.json"))
    fresh = select_new(jobs, seen, cfg.get("excludeCompanies", []))

    os.makedirs(os.path.join(a.workdir, "days"), exist_ok=True)
    out = os.path.join(a.workdir, "days", f"{a.date}.jobs.json")
    with open(out, "w") as f:
        json.dump(fresh, f, indent=1, ensure_ascii=False)
    print(f"{len(jobs)} jobs found, {len(fresh)} new -> {out}")


if __name__ == "__main__":
    main()
