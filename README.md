# dashboard

The benchmark-runs dashboard for [cap-evolve](https://github.com/skillberry-ai/cap-evolve):
every `ci/benchmarks` execution (PR and manual runs), as a sortable, filterable log of
reward, eval/optimizer cost, latency and models, each measured against that run's own
freshly-computed baseline.

**Live:** <https://skillberry-runs.github.io/dashboard/>

Part of the [skillberry-runs](https://github.com/skillberry-runs) org, which holds
cap-evolve's benchmark results, one repo per benchmark.

## Layout

- `records/<id>.json`: one record per (run × benchmark). This is the source of truth.
- `site/`: the static page (`index.html`, `benchmarks.js`, `style.css`, `js/`, `assets/`).
- `scripts/record.py`: renders `benchmarks.json` + `meta.json` from `records/`. It's a copy of
  cap-evolve's `ci/benchmarks/lib/record.py`, and the record schema is owned there.
- `.github/workflows/pages.yml`: renders the feed and deploys `site/` to Pages on every
  push that touches the above, and nightly (to pick up the benchmark repos' write-ups).
  `check-records.yml` validates records on pull requests; `check-site.yml` checks the page against
  cap-evolve's tiers and benches.

`benchmarks.json`/`meta.json` are **not committed**. They're regenerated on every deploy.

## Publishing

**[PUBLISHING.md](PUBLISHING.md)** is the how-to: add a run row by hand, update a benchmark's write-ups,
add a new benchmark, renew tokens, and troubleshoot. Tools: `scripts/check_records.py` (validates records;
runs on pull requests and before every deploy), `scripts/mask_secrets.py` (secret-scanner false positives in
run data; cap-evolve's CI runs it too), `scripts/publish_ci_ui.py` + `site/viewer/` (serving runs' "Open
UI" data), and `sections.json` (the list of benchmark sections, and which repo holds which bench).

New runs arrive by themselves: cap-evolve's CI publishes each one here (its record) and to its
benchmark's repo (its "Open UI" data), as `skillberry-bot`.

## Benchmark report sections

Each benchmark listed in [`sections.json`](sections.json) gets a section, `/<repo>/`, publishing the
write-ups (`*.md`, rendered) and report pages (`ui/*.html`) of `skillberry-runs/<repo>`, plus its runs'
"Open UI" data (`ci_ui/`).
`scripts/build_reports.py` renders them on every deploy. It does **not** publish raw results
data, `recipes/`, `artifacts/` or `presentations/`; links to those open the files in the repo on
GitHub. It also masks internal cluster paths and host names in what it does publish. `/notes/`
renders `notes/`: hand-written notes for locally-run records, linked from their Source column.

The benchmark repos are public (since 2026-11-17), so the deploy clones them without credentials.
If `RESULTS_READ_TOKEN` is set it is used instead (needed only if a section's repo is ever private).

## Preview locally

```bash
python3 scripts/record.py aggregate records --now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --out site
python3 -m http.server -d site 8000   # open http://localhost:8000/
# or http://localhost:8000/?fixture to use the small committed sample feed
```

## Provenance

This repo was created on 2026-11-10 as a fresh snapshot of cap-evolve's `benchmark-history`
branch (records only, at `0875ae5`) plus the page from cap-evolve's `site/` (at `4e93f41`). The
branch's git history (~2,700 commits) and its large per-run artifacts were deliberately **not**
copied. Its per-run "Open UI" data was moved into the benchmark repos' `ci_ui/` folders
(2026-11-16/17), and since 2026-11-18 cap-evolve's CI writes here directly (cap-evolve#993), with
"Watch live" data in [`skillberry-runs/live`](https://github.com/skillberry-runs/live).
"Running now" still reads cap-evolve's Actions API, since that's where runs execute (unauthenticated:
60 requests an hour per IP address, which a shared office network can use up).
