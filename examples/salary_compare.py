"""Compare the yearly salary range of one role in several cities.

Example:
    python examples/salary_compare.py "data engineer" "New York, NY" "Austin, TX" "Seattle, WA"
"""
import argparse
from statistics import median

from common import search_jobs


def summarize(jobs, currency="USD"):
    """Return {location: (count, median_min, median_max)} for yearly salaries in one currency."""
    by_city = {}
    for job in jobs:
        if job.get("salaryPeriod") != "year" or job.get("salaryCurrency") != currency:
            continue
        if job.get("salaryMin") is None or job.get("salaryMax") is None:
            continue
        by_city.setdefault(job["searchLocation"], []).append(job)
    return {
        city: (len(js), median(j["salaryMin"] for j in js), median(j["salaryMax"] for j in js))
        for city, js in by_city.items()
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("role")
    ap.add_argument("cities", nargs="+")
    ap.add_argument("--country", default="us")
    ap.add_argument("--currency", default="USD")
    ap.add_argument("--max", type=int, default=50, help="max jobs per city (default 50)")
    a = ap.parse_args()

    jobs = search_jobs([a.role], a.cities, country=a.country, maxResultsPerSearch=a.max)
    rows = summarize(jobs, a.currency)
    print(f"{a.role}: yearly salary in {a.currency} (median of postings that show a salary)\n")
    print(f"{'City':<25}{'Postings':>9}{'Min':>12}{'Max':>12}")
    for city in a.cities:
        if city in rows:
            n, lo, hi = rows[city]
            print(f"{city:<25}{n:>9}{lo:>12,.0f}{hi:>12,.0f}")
        else:
            print(f"{city:<25}{0:>9}{'-':>12}{'-':>12}")


if __name__ == "__main__":
    main()
