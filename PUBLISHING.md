# Publishing to the dashboard

How new benchmark results get onto <https://skillberry-runs.github.io/dashboard/>, by hand.
(cap-evolve's CI still publishes to cap-evolve's own `benchmark-history` branch; section D
brings those runs over. Making CI write here directly is a later step.)

## What lives where

| What | Where | Visible on the site |
|---|---|---|
| **Run rows** (the table) | `records/<id>__<label>.json` in **this repo** | yes: every row |
| **Short notes** for hand-published runs | `notes/runs/<name>.md` in this repo | yes: `/notes/runs/<name>.html` |
| **Write-ups and report pages** per benchmark | the benchmark's repo, `skillberry-runs/<repo>` (public; the list is [`sections.json`](sections.json)) | `*.md` and `ui/*.html` only, at `/<benchmark>/…` |
| Raw data, `recipes/`, `artifacts/`, `presentations/` | the benchmark's repo | **no**: never published (they contain internal paths) |
| **"Open UI" data** per run | the benchmark's repo: `ci_ui/<run_id>__<tier>-<bench>/` | yes: `/<benchmark>/ci_ui/…`, opened in the shared viewer (`site/viewer/`) |
| "Open UI" data of runs not yet moved (see F), "Watch live" data | cap-evolve's `benchmark-history` branch | served by cap-evolve's site |

## Which section do I need?

| I want to… | Go to |
|---|---|
| add a run to the table (a run that did not go through cap-evolve's CI) | **A** |
| add or update a write-up, heatmap or report page | **B** |
| attach a short note to a hand-published row | **C** |
| bring over runs that cap-evolve's CI recorded on `benchmark-history` | **D** |
| publish a benchmark that has no section yet (e.g. AppWorld) | **E** |
| add or move a run's "Open UI" data | **F** |

---

## A. Add a run row by hand

**1. Build the record.** Follow steps 1–4 of cap-evolve's
[`ci/benchmarks/PUBLISHING.md`](https://github.com/skillberry-ai/cap-evolve/blob/main/ci/benchmarks/PUBLISHING.md):
collect the run dir, run `metrics.py`, write `runmeta.json`, run `record.py build`. You end up with one
JSON file. Stop there: its step 5 is where the record is published, and this section replaces it.

**2. Name it** `<id>__<label>.json`: an id that sorts by time, two underscores, a short label.
CI uses the Actions run id as the id; hand-published runs use `YYYYMMDDNNN` (for example
`20261019001__v6-parsec.json`). The name is the record's identity: adding a file with an existing
name replaces that record, which is how you correct one.

**3. Link a write-up** (optional). Put `summary_url` and/or `report_url` in the record, pointing at the
*published* page rather than at a file in a repo (see B and C for the URL form). `source` should say how the run
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

**The site rebuilds nightly** (03:17 UTC), so pushes to these repos show up by the next morning. To see
them sooner, run **Actions → Deploy dashboard → Run workflow** in this repo, or:

```bash
gh workflow run pages.yml -R skillberry-runs/dashboard
```

A page's address is its path with `.md` → `.html`: `results/v6/v6_t4_e1/summary.md` in `parsec` is
<https://skillberry-runs.github.io/dashboard/parsec/results/v6/v6_t4_e1/summary.html>.
Links *from* one published page to another are rewritten for you. Links to files that are not
rendered (`artifacts/…`, raw JSON) open the file in the repo on GitHub.

A section's front page is its `HOME.md` if the repo has one (SkillsBench does: the experiment cards),
otherwise its `README.md`.

SkillsBench's section moved here from cap-evolve's site on 2026-11-16. Until cap-evolve drops its copy,
pushing to `skillberry-runs/skillsbench` still rebuilds cap-evolve's site too (its
`notify-cap-evolve-pages.yml`); this site needs the manual deploy above, like the others.

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
- **"Open UI" links** in copied rows open cap-evolve's copy of the snapshot until that run's data is
  moved into its benchmark repo (F); then they open this site's shared viewer.

## E. Publish a new benchmark (for example AppWorld)

1. **Create the repo** `skillberry-runs/<benchmark>`, **public** (everything in the org is public, and the
   deploy clones without credentials). Put a `README.md` (it becomes the front page; or a `HOME.md`),
   write-ups as `*.md`, and report pages as `ui/*.html`. Only `.md` and `.html` files are rendered on the
   site; raw data (JSON and so on) and anything under `artifacts/`, `recipes/` or `presentations/` are
   not, but they are still readable in the public repo, so keep secrets and internal-only material out
   of the repo altogether (the secret scanner checks every commit).
2. **Register the section.** Add an entry to [`sections.json`](sections.json):
   `{"repo": "<benchmark>", "title": "<Display name>", "benches": ["<bench>", …]}`. `benches` lists the
   `bench` values of the records whose "Open UI" data belongs in this repo (default: the repo name; a
   `tau` repo lists `tau2`, `tau2_sierra`, `tau2_custom_direct`, …). Add a link next to the others in `site/index.html`'s menu; the menu on
   the section pages follows `sections.json` by itself.
3. **Move its runs' "Open UI" data** into the repo (F).
4. **Deploy** (B) and open `/<benchmark>/`. Add its run rows with A.

## F. "Open UI" data (`ci_ui/`) and the shared viewer

Each run's "Open UI" is the CapEvolve dashboard for that run. The **data** lives in the benchmark's repo,
one folder per run, named exactly like the run's row:

```
<benchmark repo>/ci_ui/<run_id>__<tier>-<bench>/      e.g. spreadsheetbench/ci_ui/36887395788__full_verified_probe-spreadsheetbench/
```

The **viewer** is one shared copy in this repo, `site/viewer/`. At deploy time each repo's `ci_ui/` is
published to `/<benchmark>/ci_ui/` (internal paths and host names masked) and listed in `ui_index.json`;
a row whose run is listed opens `viewer/index.html?dataBase=…`, any other row opens cap-evolve's copy.

**Move runs from cap-evolve** (every record with `has_ui` whose `bench` belongs to a repo in
`sections.json`; already-moved runs are skipped):

```bash
# with checkouts of the benchmark repos next to this one (../parsec, ../spreadsheetbench, …)
python3 scripts/migrate_ui_snapshots.py --repos-dir .. --dry-run     # what would move
python3 scripts/migrate_ui_snapshots.py --repos-dir .. --commit      # copy + commit in each repo
git -C ../<repo> push                                                # then deploy (B)
```

Only each run's `ui/data/` is copied (not its copy of the viewer, nor raw run folders).

**The secret scanner.** Commits to these repos go through IBM Vault Radar, which blocks text that looks
like a credential. Run data contains false positives (AI tool-call ids read as a Mailsac key, a website's
public OAuth client id, `pass=` in agent-written code). `migrate_ui_snapshots.py` masks the known ones
before committing (`scripts/mask_secrets.py`: visible placeholders, tool-call ids mapped consistently so
the viewer still pairs calls with results). If a commit is still blocked, the script saves the scanner's
output and prints the command that masks exactly those findings; run it, then commit again. Never bypass
the scanner. If a finding looks like a **real** secret, stop and tell the team: it is also public on
cap-evolve's `benchmark-history`.

**Add a hand-run snapshot** (not on cap-evolve): export it with cap-evolve's `export_static`
(cap-evolve's `ci/benchmarks/PUBLISHING.md`, "Open UI" section), copy its `data/` folder to
`<repo>/ci_ui/<run_id>__<tier>-<bench>/`, run `python3 scripts/mask_secrets.py <repo>/ci_ui`, commit, and
set `"has_ui": true` in the run's record.

**Update the viewer** to cap-evolve's latest dashboard: `scripts/update_viewer.sh` (needs node), then
commit `site/viewer/`. Newer viewers open older runs' data (tested back to July 2026).

---

## Tokens and secrets

| Secret | Lives in | Used for |
|---|---|---|
| `RESULTS_READ_TOKEN` | this repo | optional since the repos went public: if set, the deploy clones with it |
| `SKILLSBENCH_READ_TOKEN` | cap-evolve | cap-evolve's deploy reads `skillsbench` (same token as above; retired once cap-evolve drops its SkillsBench section) |
| `CAP_EVOLVE_DISPATCH_TOKEN` | `skillberry-runs/skillsbench` | starts cap-evolve's deploy when `skillsbench` changes (same: retired with that section) |

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
| Deploy is red when cloning a section's repo | The repo in `sections.json` doesn't exist or isn't public, or `RESULTS_READ_TOKEN` is set but expired (delete the secret: public repos don't need it). The log prints the token's owner and GitHub's reason. The last good site stays live. |
| Deploy is red at "Validate records" | A record failed `scripts/check_records.py`; the error names the file and the problem. |
| A link opens a 404 | A record or page links to a file that was renamed or never committed (GitHub Pages is case-sensitive: check the file name's letter case). |
| Sync run is red | A source record failed validation (listed as `REJECTED` in the log). Fix it at the source, or copy it by hand through A. |
