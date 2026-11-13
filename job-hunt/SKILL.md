---
name: job-hunt
description: Daily job hunt from Google Jobs. Finds new jobs (posted in the last 7 days by default), scores each one against the user's resume, checks Gmail for jobs already applied to, and writes a short list of jobs to apply to today with resume points to highlight. Use when the user says "job hunt", "find jobs for me", "run my daily job search", or "/job-hunt". It never submits applications.
---

# job-hunt

Turns new Google Jobs listings into a short daily list: what to apply to, why, and
what to highlight on the resume. The user still clicks "Apply". This skill never
submits anything, because auto-applying breaks the terms of most job sites and
puts the user's accounts at risk.

Scripts are in the same folder as this file (`fetch_jobs.py`, `report.py`).
The user's data is in a work folder (default `~/job-hunt`):

```text
~/job-hunt/
  job-hunt.json      search settings (copy job-hunt.example.json)
  resume.md          the user's resume as plain text or Markdown
  seen.json          jobs already shown (written by report.py)
  days/<date>.jobs.json    new jobs (written by fetch_jobs.py)
  days/<date>.scores.json  your scores (written by you)
  days/<date>.md           the daily list (written by report.py)
```

## Step 0: check the setup

```sh
W=~/job-hunt; S=<this skill folder>
test -f $W/job-hunt.json && test -f $W/resume.md && echo setup-ok
test -n "$APIFY_TOKEN" && echo token-ok
```

```text
if setup-ok is missing:
    copy $S/job-hunt.example.json to $W/job-hunt.json
    ask the user for their resume file, copy it to $W/resume.md
    ask the user to edit queries, locations and country in job-hunt.json
    STOP until the user says it is done
elif token-ok is missing:
    tell the user: export APIFY_TOKEN=<token from Apify Console > Settings > API & Integrations>
    STOP
else:
    go to Step 1
```

## Step 1: get new jobs

```sh
python3 $S/fetch_jobs.py --workdir $W
```

```text
if exit code != 0:
    show the error to the user
    STOP
elif the output says "0 new":
    tell the user "no new jobs today"
    STOP
else:
    go to Step 2
```

The Actor charges per Google results page (about 10 jobs), $0.028 to $0.09 per page
by Apify plan. Keep `datePosted` at `7d`, not `24h`: the date filter runs on the
results Google returns, so `24h` pays for the same pages and keeps far fewer jobs
(one real run: 30 found, 1 kept). `seen.json` already hides jobs you saw before.

## Step 2: score each job against the resume

Read `$W/resume.md` and `$W/days/<date>.jobs.json`. Give every job one score:

```text
0-3   wrong role or a hard blocker: seniority off by 2+ levels, location or work
      permit the resume cannot meet, required skill family missing
4-6   same role family, but 1-2 core requirements are missing
7-8   meets the core requirements, with at most 1 nice-to-have missing
9-10  meets core and most nice-to-have requirements, and the level fits
```

Rules:

- Each reason quotes or names a concrete requirement from the description.
- Score only on what the description says. Do not guess the salary or the team.
- If `job-hunt.json` has `notes`, apply them (for example "no on-site 5 days").

## Step 3: check Gmail for jobs already applied to

Only for the top `maxGmailChecks` jobs with score >= `minScore`. Skip this step if
`maxGmailChecks` is 0 or no Gmail tool is connected.

```text
for job in top jobs:
    employer = the company the description names as the employer
               (the "company" field is sometimes a reposting site, e.g. "MeeBoss"
                for a TestSprite job, so use the real employer)
    search Gmail: "<employer>" subject:(application OR applying OR applied) newer_than:180d
    if a message from the employer or its job system (Greenhouse, Lever, Workday,
       LinkedIn/Indeed "application sent") confirms an application for a similar role:
        applied = "yes"
        applied_evidence = "<subject>, <date>"
    else:
        applied = "no"
other jobs: applied = "unchecked"
```

Job alerts, "a job you may like" emails, salary reports, and newsletters do not
count as an application.

Read only. Do not open attachments, send, label, or delete anything.

## Step 4: resume highlights

For the top `topHighlights` jobs with applied = "no", list 2-4 items that already
exist in the resume and that the job asks for, most important first.
Do not invent experience.

If a job's `link_kind` is `repost`, the report tells the user to look for the job
on the company careers page. Do not search the web for it yourself. If the job needs something the resume does not have,
put it in `gaps`, not in `highlights`.

## Step 5: write the scores file and the report

Write `$W/days/<date>.scores.json`, one object per job in the jobs file:

```json
[{"job_id": "…", "score": 8,
  "reasons": ["Asks for Go and Kafka; resume has 4 years of both"],
  "gaps": ["Wants Kubernetes operator experience"],
  "applied": "no", "applied_evidence": "",
  "highlights": ["Kafka pipeline at 2M events/s", "Go services on AWS"]}]
```

```sh
python3 $S/report.py --workdir $W
```

```text
if exit code == 1:
    fix every problem it prints in the scores file
    run report.py again
else:
    show the user the "Apply today" part of $W/days/<date>.md
```

`report.py` adds today's jobs to `seen.json` only when the report is written, so a
failed run can be repeated.
