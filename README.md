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
  push that touches the above.

`benchmarks.json`/`meta.json` are **not committed**. They're regenerated on every deploy.

## Benchmark report sections

`/parsec/` and `/spreadsheetbench/` publish the write-ups (`*.md`, rendered) and report pages
(`ui/*.html`) of [`skillberry-runs/parsec`](https://github.com/skillberry-runs/parsec) and
[`skillberry-runs/spreadsheetbench`](https://github.com/skillberry-runs/spreadsheetbench).
`scripts/build_reports.py` renders them on every deploy. It does **not** publish raw results
data, `recipes/`, `artifacts/` or `presentations/`; links to those go to the private repo on
GitHub. It also masks internal cluster paths and host names in what it does publish. `/notes/`
renders `notes/`: hand-written notes for locally-run records, linked from their Source column.

Those repos are private, so the deploy reads them with `RESULTS_READ_TOKEN`, a `skillberry-bot`
fine-grained token with *Contents: read* on both. Until that secret is set, it falls back to the
identical legacy branches on public `skillberry-ai/cap-evolve`.

## Preview locally

```bash
python3 scripts/record.py aggregate records --now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --out site
python3 -m http.server -d site 8000   # open http://localhost:8000/
# or http://localhost:8000/?fixture to use the small committed sample feed
```

## Provenance and current limits

This repo was created on 2026-11-10 as a fresh snapshot of cap-evolve's `benchmark-history`
branch (records only, at `0875ae5`) plus the page from cap-evolve's `site/` (at `4e93f41`).
The branch's git history (~2,700 commits) and its large per-run artifacts were deliberately
**not** copied:

- **"Open UI" links** go to the per-run CapEvolve UI snapshots, which are still served from the
  cap-evolve site (`benchmark-history`'s `runs/**`, ~3 GB).
- **"Running now" / "Watch live"** still read cap-evolve's Actions API and `benchmark-history`'s
  `live/`, because cap-evolve's CI is still where runs execute.
- **New runs are not here yet.** cap-evolve's CI still writes new records to its own
  `benchmark-history` branch. Until it's pointed at this repo (planned; it will run as
  `skillberry-bot`), this dashboard is a snapshot as of the date above.
