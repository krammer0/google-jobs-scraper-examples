# Google Jobs API examples (Python)

Google Jobs (the job panel in Google Search) has no official API. These examples get Google Jobs listings as JSON with the [Google Jobs Scraper](https://apify.com/krammer/google-jobs-scraper?utm_source=github&utm_medium=examples) Actor on Apify, then do something useful with them.

| Script | What it does |
|---|---|
| [`salary_compare.py`](examples/salary_compare.py) | Compares the yearly salary range of one role in several cities. |
| [`hiring_companies.py`](examples/hiring_companies.py) | Lists the companies that hire for a role in a city, and saves the jobs to CSV. |
| [`daily_alerts.py`](examples/daily_alerts.py) | Prints only the jobs posted in the last 24 hours that you have not seen before. |

## Quick start

1. Create a free [Apify account](https://console.apify.com/sign-up) and copy your API token from **Settings > API & Integrations**.
2. Install and run:

```bash
git clone https://github.com/krammer0/google-jobs-scraper-examples.git
cd google-jobs-scraper-examples
pip install -r requirements.txt
export APIFY_TOKEN=<your token>

python examples/salary_compare.py "data engineer" "New York, NY" "Austin, TX" "Seattle, WA"
python examples/hiring_companies.py "registered nurse" "Chicago, IL" --csv nurses.csv
python examples/daily_alerts.py "python developer" --location "London" --country gb
```

## The core call

All examples use the same 10 lines (see [`common.py`](examples/common.py)):

```python
from apify_client import ApifyClient

client = ApifyClient("<YOUR_APIFY_TOKEN>")
run = client.actor("krammer/google-jobs-scraper").call(run_input={
    "queries": ["software engineer"],
    "locations": ["New York, NY"],
    "country": "us",           # us, gb, in, de
    "datePosted": "7d",        # any, 24h, 3d, 7d, 30d
    "maxResultsPerSearch": 50, # 1 to 200
})
for job in client.dataset(run["defaultDatasetId"]).iterate_items():
    print(job["title"], "|", job["company"], "|", job["salaryMin"], job["salaryMax"])
```

## What one job looks like

Abridged; the company name is replaced.

```json
{
  "job_id": "RtLv7vlPTbn2E40SAAAAAA==",
  "title": "Staff Software Engineer - Card Technology",
  "company": "Example Corp",
  "location": "New York, NY (+3 others)",
  "description": "Example Corp is hiring a Staff Software Engineer for its card technology team. ...",
  "apply_options": [{ "title": "Example Corp Careers", "link": "https://careers.example.com/jobs/12345" }],
  "salary": "$150K–$200K a year",
  "posted": "3 days ago",
  "salaryMin": 150000,
  "salaryMax": 200000,
  "salaryCurrency": "USD",
  "salaryPeriod": "year",
  "postedDate": "2026-11-05",
  "jobTypes": ["FULLTIME"],
  "workMode": null
}
```

The full field list is on the [Actor page](https://apify.com/krammer/google-jobs-scraper?utm_source=github&utm_medium=examples).

## Cost

The Actor charges per Google results page (up to 10 jobs): $0.028 to $0.09 per page, depending on your Apify plan. Searches that return nothing are free. For example, 50 jobs is about 5 pages, so $0.45 or less on the Free plan.

## Countries

United States (`us`), United Kingdom (`gb`), India (`in`), Germany (`de`).

## License

MIT
