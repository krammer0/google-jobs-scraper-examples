"""List the companies that are hiring for a role in a city, most postings first.

Example:
    python examples/hiring_companies.py "registered nurse" "Chicago, IL" --csv nurses_chicago.csv
"""
import argparse
import csv
from collections import Counter

from common import search_jobs


def top_companies(jobs, n=20):
    return Counter(job["company"] for job in jobs).most_common(n)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("role")
    ap.add_argument("location")
    ap.add_argument("--country", default="us")
    ap.add_argument("--max", type=int, default=100, help="max jobs (default 100)")
    ap.add_argument("--csv", help="also save all jobs to this CSV file")
    a = ap.parse_args()

    jobs = search_jobs([a.role], [a.location], country=a.country, maxResultsPerSearch=a.max)
    print(f"{len(jobs)} postings for '{a.role}' in {a.location}\n")
    for company, count in top_companies(jobs):
        print(f"{count:>4}  {company}")

    if a.csv:
        fields = ["company", "title", "location", "salary", "postedDate", "workMode"]
        with open(a.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(fields + ["apply_link"])
            for job in jobs:
                link = (job.get("apply_options") or [{}])[0].get("link")
                w.writerow([job.get(k) for k in fields] + [link])
        print(f"\nSaved {len(jobs)} jobs to {a.csv}")


if __name__ == "__main__":
    main()
