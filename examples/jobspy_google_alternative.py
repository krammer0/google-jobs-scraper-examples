"""A replacement for JobSpy's Google source.

JobSpy's `scrape_jobs(site_name=["google"], ...)` currently returns 0 jobs
(GitHub issue #284: https://github.com/speedyapply/JobSpy/issues/284).
This script gets Google Jobs results from the Google Jobs Scraper Actor and
returns them with JobSpy's column names.

Needs the APIFY_TOKEN environment variable.

Example:
    python examples/jobspy_google_alternative.py "software engineer" --location "San Francisco, CA" --hours-old 72 --results 20
"""
import argparse
import csv

COLUMNS = [
    "id", "site", "job_url", "title", "company", "location", "date_posted",
    "job_type", "interval", "min_amount", "max_amount", "currency",
    "is_remote", "description",
]

JOB_TYPES = {"FULLTIME": "fulltime", "PARTTIME": "parttime", "CONTRACTOR": "contract", "INTERN": "internship"}
INTERVALS = {"hour": "hourly", "day": "daily", "week": "weekly", "month": "monthly", "year": "yearly"}


def hours_old_to_date_posted(hours_old):
    """Map JobSpy's hours_old to the Actor's datePosted value."""
    if hours_old is None:
        return None
    if hours_old <= 24:
        return "24h"
    if hours_old <= 72:
        return "3d"
    if hours_old <= 168:
        return "7d"
    return "30d"


def to_jobspy_row(item):
    """Map one Actor dataset item to a dict with JobSpy column names. Never raises."""
    item = item or {}
    job_id = item.get("job_id")
    links = [o.get("link") for o in (item.get("apply_options") or []) if isinstance(o, dict) and o.get("link")]
    types = [JOB_TYPES[t] for t in (item.get("jobTypes") or []) if t in JOB_TYPES]
    return {
        "id": "go-" + job_id if job_id else None,
        "site": "google",
        "job_url": links[0] if links else None,
        "title": item.get("title"),
        "company": item.get("company"),
        "location": item.get("location"),
        "date_posted": item.get("postedDate"),
        "job_type": ",".join(types) if types else None,
        "interval": INTERVALS.get(item.get("salaryPeriod")),
        "min_amount": item.get("salaryMin"),
        "max_amount": item.get("salaryMax"),
        "currency": item.get("salaryCurrency"),
        "is_remote": item.get("workMode") == "remote",
        "description": item.get("description"),
    }


def scrape_google_jobs(search_term, location=None, results_wanted=20, hours_old=None,
                       country="us", as_dataframe=False):
    """Return Google Jobs results as a list of dicts (or a pandas DataFrame)."""
    from common import search_jobs  # imported here so the pure functions work without apify-client

    options = {"country": country, "maxResultsPerSearch": results_wanted}
    date_posted = hours_old_to_date_posted(hours_old)
    if date_posted is not None:
        options["datePosted"] = date_posted
    items = search_jobs([search_term], [location] if location else None, **options)
    rows = [to_jobspy_row(i) for i in items]
    if as_dataframe:
        import pandas as pd  # optional dependency
        return pd.DataFrame(rows, columns=COLUMNS)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("search_term")
    ap.add_argument("--location")
    ap.add_argument("--country", default="us")
    ap.add_argument("--hours-old", type=int)
    ap.add_argument("--results", type=int, default=20)
    ap.add_argument("--csv", help="also save the rows to this CSV file")
    a = ap.parse_args()

    rows = scrape_google_jobs(a.search_term, a.location, a.results, a.hours_old, a.country)
    print(f"{len(rows)} jobs\n")
    for r in rows:
        print(" | ".join(str(r[k] or "") for k in ("title", "company", "location", "date_posted")))
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            w.writerows(rows)
        print(f"\nSaved to {a.csv}")


if __name__ == "__main__":
    main()
