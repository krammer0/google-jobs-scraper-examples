"""Print only the jobs you have not seen before. Run it once a day (cron, or an Apify schedule).

It asks for jobs from the last 7 days, not 24 hours: Google returns its most relevant jobs
first, and often only a few are from the last 24 hours. The seen-file below removes repeats.

The Actor removes duplicates inside one run only, so this script keeps the job_id values
it has already shown in a JSON file and skips them next time.

Example:
    python examples/daily_alerts.py "python developer" --location "London" --country gb
"""
import argparse
import json
import os

from common import search_jobs


def new_jobs(jobs, seen):
    return [job for job in jobs if job["job_id"] not in seen]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("queries", nargs="+")
    ap.add_argument("--location", action="append", default=[], help="can be given more than once")
    ap.add_argument("--country", default="us")
    ap.add_argument("--seen-file", default="seen_job_ids.json")
    a = ap.parse_args()

    seen = set()
    if os.path.exists(a.seen_file):
        with open(a.seen_file) as f:
            seen = set(json.load(f))

    jobs = search_jobs(a.queries, a.location, country=a.country, datePosted="7d")
    fresh = new_jobs(jobs, seen)
    print(f"{len(fresh)} new jobs ({len(jobs) - len(fresh)} already seen)\n")
    for job in fresh:
        link = (job.get("apply_options") or [{}])[0].get("link") or ""
        print(f"- {job['title']} | {job['company']} | {job.get('location') or ''}\n  {link}")

    with open(a.seen_file, "w") as f:
        json.dump(sorted(seen | {job["job_id"] for job in jobs}), f)


if __name__ == "__main__":
    main()
