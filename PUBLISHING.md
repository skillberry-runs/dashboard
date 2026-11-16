# Publishing to the dashboard

How new benchmark results get onto <https://skillberry-runs.github.io/dashboard/>, by hand.
(cap-evolve's CI still publishes to cap-evolve's own `benchmark-history` branch; section D
brings those runs over. Making CI write here directly is a later step.)

## What lives where

| What | Where | Visible on the site |
|---|---|---|
| **Run rows** (the table) | `records/<id>__<label>.json` in **this repo** | yes: every row |
| **Short notes** for hand-published runs | `notes/runs/<name>.md` in this repo | yes: `/notes/runs/<name>.html` |
| **Write-ups and report pages** per benchmark | the benchmark's repo: `skillberry-runs/parsec`, `/spreadsheetbench` (private) | `*.md` and `ui/*.html` only, at `/<benchmark>/…` |
| Raw data, `recipes/`, `artifacts/`, `presentations/` | the benchmark's repo | **no**: never published (they contain internal paths) |
| SkillsBench | `skillberry-runs/skillsbench` (private) | rendered on **cap-evolve's** site, not here |
| "Open UI" snapshots, "Watch live" data | cap-evolve's `benchmark-history` branch | served by cap-evolve's site (not migrated yet) |

## Which section do I need?

| I want to… | Go to |
|---|---|
| add a run to the table (a run that did not go through cap-evolve's CI) | **A** |
| add or update a write-up, heatmap or report page | **B** |
| attach a short note to a hand-published row | **C** |
| bring over runs that cap-evolve's CI recorded on `benchmark-history` | **D** |
| publish a benchmark that has no section yet (e.g. AppWorld) | **E** |

---

## A. Add a run row by hand

**1. Build the record.** Follow steps 1–4 of cap-evolve's
[`ci/benchmarks/PUBLISHING.md`](https://github.com/skillberry-ai/cap-evolve/blob/main/ci/benchmarks/PUBLISHING.md):
collect the run dir, run `metrics.py`, write `runmeta.json`, run `record.py build`. You end up with one
JSON file. Stop before its "push to benchmark-history" step; the destination is this repo.

**2. Name it** `<id>__<label>.json`: an id that sorts by time, two underscores, a short label.
CI uses the Actions run id as the id; hand-published runs use `YYYYMMDDNNN` (for example
`20261019001__v6-parsec.json`). The name is the record's identity: adding a file with an existing
name replaces that record, which is how you correct one.

**3. Link a write-up** (optional). Put `summary_url` and/or `report_url` in the record, pointing at the
*published* page, not at a private repo (see B and C for the URL form). `source` should say how the run
was produced and published; do not present a hand-finished run as a clean CI run.

**4. Add it with a pull request:**

```bash
git clone git@github.com:skillberry-runs/dashboard.git && cd dashboard
git switch -c add-<label>
cp /tmp/pub/<id>__<label>.json records/
python3 scripts/check_records.py records/<id>__<label>.json     # must print 0 errors
git add records && git commit -m "records: add <label>" && git push -u origin HEAD
```

A CI check runs the same validation on the PR. **Merging deploys automatically** (about a minute).

**5. Verify.** Open the page, set the filters you need (see Troubleshooting), or:

```bash
curl -s https://skillberry-runs.github.io/dashboard/benchmarks.json \
  | python3 -c "import json,sys; print([(r['run_id'], r['bench'], r['conclusion']) for r in json.load(sys.stdin)][:3])"
```

## B. Add or update write-ups and reports

Commit them to the benchmark's own repo (`skillberry-runs/parsec`, `skillberry-runs/spreadsheetbench`).
What gets published on the site:

- every `*.md` outside `artifacts/`, `recipes/`, `presentations/`, rendered to a web page (the README
  becomes the section's front page);
- every `*.html` outside those folders, copied as is (this is how heatmaps and dashboards go out).

Internal cluster paths and host names in published text are replaced by `<internal path>` /
`<cluster host>`. The repo itself is not changed.

**The site does not update on its own when these repos change yet.** After pushing, run
**Actions → Deploy dashboard → Run workflow** in this repo, or:

```bash
gh workflow run pages.yml -R skillberry-runs/dashboard
```

A page's address is its path with `.md` → `.html`: `results/v6/v6_t4_e1/summary.md` in `parsec` is
<https://skillberry-runs.github.io/dashboard/parsec/results/v6/v6_t4_e1/summary.html>.
Links *from* one published page to another are rewritten for you. Links to files that are not
published (`artifacts/…`, raw JSON) are sent to the private repo on GitHub, so they open for org
members only.

SkillsBench works differently: pushing to `skillberry-runs/skillsbench` rebuilds **cap-evolve's** site
(its `notify-cap-evolve-pages.yml`), and its section lives there.

## C. A short note for a hand-published row

For a few paragraphs about one run, add `notes/runs/<name>.md` to this repo (same pull-request flow as
A) and set the record's `summary_url` to
`https://skillberry-runs.github.io/dashboard/notes/runs/<name>.html`. Longer material belongs in the
benchmark's repo (B).

## D. Bring over runs from cap-evolve

Runs that cap-evolve's CI records on its `benchmark-history` branch, or that someone published there by
hand, are copied here by the **Sync from cap-evolve** workflow. Run it whenever you want them on the
dashboard; it is safe to repeat.

**Actions → Sync from cap-evolve → Run workflow**, or:

```bash
gh workflow run sync-from-cap-evolve.yml -R skillberry-runs/dashboard                    # copy what is new
gh workflow run sync-from-cap-evolve.yml -R skillberry-runs/dashboard -f dry_run=true    # report only
gh run list -R skillberry-runs/dashboard --workflow sync-from-cap-evolve.yml --limit 1   # then: gh run view <id> --log
```

The report (what was added, what already matched, what was rejected) is also on the run's summary page.

It copies `records/*.json` and `docs/runs/*.md` that are not here yet (nothing else: the branch's
per-run UI snapshots and live data are not fetched), repoints links that still name cap-evolve's retired
`*-history` branches, validates each record, commits as `skillberry-bot`, and starts a deploy. A record
that fails validation is skipped and the run fails, so it cannot go unnoticed.

- `-f update_existing=true` also overwrites a record that already exists here but differs from
  cap-evolve's copy (use it after correcting a record at the source). By default such a record is kept
  and listed.
- Without GitHub: `python3 scripts/sync_from_cap_evolve.py --dry-run`, then run it without `--dry-run`
  and commit.
- **"Open UI" links** in copied rows point at cap-evolve's site, which serves those snapshots. They work
  once cap-evolve's own site has deployed after the run was recorded.

## E. Publish a new benchmark (for example AppWorld)

1. **Create the repo** `skillberry-runs/<benchmark>` (private). Put a `README.md` (it becomes the front
   page), write-ups as `*.md`, and report pages as `ui/*.html`. Only `.md` and `.html` files are
   published; raw data (JSON and so on) never is, and nothing under `artifacts/`, `recipes/` or
   `presentations/` is, so put anything that carries internal paths there.
2. **Let the deploy read it.** In skillberry-bot's token list
   (<https://github.com/settings/personal-access-tokens>, logged in as the bot), edit
   `skillberry-runs-read` and add the new repo under *Repository access*. Editing does not change the
   token's value, so no secret needs updating.
3. **Register the section.** Add an entry to [`sections.json`](sections.json)
   (`{"repo": "<benchmark>", "title": "<Display name>"}`; `legacy_branch` is only for the old cap-evolve
   branches) and add a link next to the others in `site/index.html`'s menu. The menu on the section
   pages follows `sections.json` by itself.
4. **Deploy** (B) and open `/<benchmark>/`. Add its run rows with A.

---

## Tokens and secrets

| Secret | Lives in | Used for |
|---|---|---|
| `RESULTS_READ_TOKEN` | this repo | the deploy reads the private benchmark repos |
| `SKILLSBENCH_READ_TOKEN` | cap-evolve | cap-evolve's deploy reads `skillsbench` (same token as above) |
| `CAP_EVOLVE_DISPATCH_TOKEN` | `skillberry-runs/skillsbench` | starts cap-evolve's deploy when `skillsbench` changes |

All three are fine-grained tokens of the bot account `skillberry-bot` and **expire on a fixed date**
(set to one year). Every deploy logs the expiry of `RESULTS_READ_TOKEN` and warns 30 days ahead. To renew:
as the bot, open the token, *Regenerate* it with a new expiry, and set the new value in each place the
token is used (`gh secret set RESULTS_READ_TOKEN -R skillberry-runs/dashboard`, and
`SKILLSBENCH_READ_TOKEN` in cap-evolve). The sync workflow needs no token of its own.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| A new row is not on the page | The filters. **Result** defaults to *success* (failed and cancelled runs are hidden) and **Time** to *All*. Also check that the deploy finished (Actions tab). |
| A row shows `—` for reward | `conclusion` is not `success`, or `suite` is empty because `record.py build` ran on an unfinished run. `check_records.py` warns about this. |
| Deploy is red with `403` in the report step | `RESULTS_READ_TOKEN` expired, lacks *Contents: read* on a repo, or the repo is missing from its list. The log prints the token's owner and GitHub's stated reason. The last good site stays live. |
| Deploy is red at "Validate records" | A record failed `scripts/check_records.py`; the error names the file and the problem. |
| A link opens a 404 for someone outside the org | It points into a private repo. Link the published page instead (B). |
| Sync run is red | A source record failed validation (listed as `REJECTED` in the log). Fix it at the source, or copy it by hand through A. |
