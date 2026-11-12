"""Shared helper: run the Google Jobs Scraper Actor and return the jobs.

Needs the APIFY_TOKEN environment variable (Apify Console > Settings > API & Integrations).
"""
import os
import sys

from apify_client import ApifyClient

ACTOR = "krammer/google-jobs-scraper"


def search_jobs(queries, locations=None, **options):
    """Run one Actor run and return the list of job items.

    options are other input fields, for example country="gb", datePosted="7d",
    maxResultsPerSearch=50, jobTypes=["FULLTIME"].
    """
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("Set APIFY_TOKEN first: export APIFY_TOKEN=<your token>")
    client = ApifyClient(token)
    run_input = {"queries": list(queries), "locations": list(locations or []), **options}
    run = client.actor(ACTOR).call(run_input=run_input)
    if run is None or run.get("status") != "SUCCEEDED":
        status = run.get("status") if run else "unknown"
        sys.exit(f"Run did not succeed (status: {status}). Check the run log in Apify Console.")
    return list(client.dataset(run["defaultDatasetId"]).iterate_items())
