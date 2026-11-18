# Publishing to the dashboard

How benchmark results get onto <https://skillberry-runs.github.io/dashboard/>. cap-evolve's CI
publishes every run here by itself (each bench job's `Publish results to skillberry-runs` step: the row,
and the run's "Open UI" data in its benchmark's repo). This document is for everything else: runs
published by hand, write-ups, new benchmarks, tokens.

## What lives where

| What | Where | Visible on the site |
|---|---|---|
| **Run rows** (the table) | `records/<id>__<label>.json` in **this repo** | yes: every row |
| **Short notes** for hand-published runs | `notes/runs/<name>.md` in this repo | yes: `/notes/runs/<name>.html` |
| **Write-ups and report pages** per benchmark | the benchmark's repo, `skillberry-runs/<repo>` (public; the list is [`sections.json`](sections.json)) | `*.md` and `ui/*.html` only, at `/<benchmark>/…` |
| Raw data, `recipes/`, `artifacts/`, `presentations/` | the benchmark's repo | **no**: never published (they contain internal paths) |
| **"Open UI" data** per run | the benchmark's repo: `ci_ui/<run_id>__<tier>-<bench>/` | yes: `/<benchmark>/ci_ui/…`, opened in the shared viewer (`site/viewer/`) |
| "Watch live" data of a running CI job | [`skillberry-runs/live`](https://github.com/skillberry-runs/live), one branch per job, deleted when it ends | read live by the page |

## Which section do I need?

| I want to… | Go to |
|---|---|
| add a run to the table (a run that did not go through cap-evolve's CI) | **A** |
| add or update a write-up, heatmap or report page | **B** |
| attach a short note to a hand-published row | **C** |
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

**One run, one file.** The file name is a record's identity. If CI already published the run (a CI run
you are correcting, for example), reuse its file name rather than adding a second one; otherwise the run
shows up as two rows.

**3. Link a write-up** (optional). Put `summary_url` and/or `report_url` in the record, pointing at the
*published* page rather than at a file in a repo (see B and C for the URL form). `source` should say how the run
was produced and published; do not present a hand-finished run as a clean CI run.

**4. Add it with a pull request:**

```bash
git clone git@github.com:skillberry-runs/dashboard.git && cd dashboard
# example names; use your record's file name (pasting <...> placeholders fails: the shell reads < and > as redirects)
git switch -c add-pilot-spreadsheetbench
cp /tmp/pub/20261117001__pilot-spreadsheetbench.json records/
python3 scripts/check_records.py records/20261117001__pilot-spreadsheetbench.json     # must print 0 errors
git add records && git commit -m "records: add pilot-spreadsheetbench" && git push -u origin HEAD
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

SkillsBench's section moved here from cap-evolve's site on 2026-11-16 (cap-evolve's old addresses
redirect here).

## C. A short note for a hand-published row

For a few paragraphs about one run, add `notes/runs/<name>.md` to this repo (same pull-request flow as
A) and set the record's `summary_url` to
`https://skillberry-runs.github.io/dashboard/notes/runs/<name>.html`. Longer material belongs in the
benchmark's repo (B).

## D. Runs from cap-evolve's `benchmark-history` (retired)

Until 2026-11-18 cap-evolve's CI published to its own `benchmark-history` branch, and a sync workflow
copied those runs here. Everything on that branch was migrated (211 records, their notes and their
"Open UI" data; one run's data deliberately not, see `skip_ui` in `sections.json`), CI now publishes here
directly, and the sync workflow and migration scripts were removed (they are in this repo's git history).
The branch is being backed up to Box, and will be deleted after that.

## E. Publish a new benchmark (for example AppWorld)

Before the first run of a benchmark that has no repo here can be published, by CI or by hand, the
benchmark needs a repo, the CI token needs access to it, and `sections.json` needs to say which runs
go there. Do the steps in this order: a CI run that finishes before step 2 is done fails at its
publish step.

1. **Create the repo** `skillberry-runs/<benchmark>`, **public** (an org owner does this): everything in
   the org is public, and the deploy clones without credentials. Give it a `README.md`, which becomes
   the section's front page (or a `HOME.md`, which then takes precedence). Write-ups go in as `*.md`,
   report pages as `ui/*.html`. Only `.md` and `.html` files are rendered on the site; raw data (JSON
   and so on) and anything under `artifacts/`, `recipes/` or `presentations/` is not, but all of it is
   readable in the public repo, so keep secrets and internal-only material out of the repo altogether
   (the secret scanner checks every commit made from an IBM machine).
2. **Give the CI token access to the repo.** cap-evolve's CI writes each run's "Open UI" data into the
   benchmark's repo with the bot's **`skillberry-runs-results`** token (cap-evolve secret
   `SKILLBERRY_RUNS_RESULTS_TOKEN`). That token only reaches the repos listed on it. Log in as
   `skillberry-bot`, open <https://github.com/settings/personal-access-tokens>, edit
   `skillberry-runs-results`, and add the new repo under *Repository access* (permissions stay
   *Contents: Read and write*). Editing doesn't change the token's value, so no secret needs updating.
   Skip this and the CI run's `Publish results to skillberry-runs` step fails with a 403 when it pushes to
   the new repo.
   (Publishing by hand needs no token: you push with your own account.)
3. **Register the benchmark** in [`sections.json`](sections.json):
   ```json
   {"repo": "<benchmark>", "title": "<Display name>", "benches": ["<bench>", …]}
   ```
   `benches` lists the exact `bench` values its run records carry; that's how CI decides which repo a
   run's "Open UI" data goes to (default: the repo name). A `tau` repo, for example, lists `tau2`,
   `tau2_sierra`, `tau2_sierra_blackbox`, …. A bench that's in no entry still gets its row, with a
   CI warning that its "Open UI" data was not published.
   - While the repo has no write-ups yet, add `"site": false`: its "Open UI" data is still published,
     but there's no section page or menu entry. (`rfe` and `appworld` start this way.)
   - Once it has a section page, add a link next to the others in `site/index.html`'s menu (the menu on
     the section pages follows `sections.json` by itself).
4. **If CI should run it** (cap-evolve side): the benchmark must be in cap-evolve's
   `.github/workflows/benchmarks.yml` (`BENCHES`, and the dispatch options) with its
   `ci/benchmarks/<bench>/` folder; see cap-evolve's `ci/benchmarks/README.md`. The nightly
   [`check-site.yml`](.github/workflows/check-site.yml) confirms the "Running now" panel recognises it.
5. **Publish runs.** From here CI publishes every run of it automatically (its row here, its "Open UI"
   data in the repo). To publish by hand: the row with A, its "Open UI" data with F, write-ups with B.
6. **Deploy and check** (B): open `/<benchmark>/` (once it has a section) and the run's row, and its
   **Open UI** link.

## F. "Open UI" data (`ci_ui/`) and the shared viewer

Each run's "Open UI" is the CapEvolve dashboard for that run. The **data** lives in the benchmark's repo,
one folder per run, named exactly like the run's row:

```
<benchmark repo>/ci_ui/<run_id>__<tier>-<bench>/      e.g. spreadsheetbench/ci_ui/36887395788__full_verified_probe-spreadsheetbench/
```

The **viewer** is one shared copy in this repo, `site/viewer/`. At deploy time each repo's `ci_ui/` is
published to `/<benchmark>/ci_ui/` (internal paths and host names masked) and listed in `ui_index.json`;
a row whose run is listed opens `viewer/index.html?dataBase=…`. A row with `has_ui` whose data is not
here shows "UI archived".

CI writes each run's folder itself (masked first). For a run published by hand, see below.

**The secret scanner.** Commits to these repos go through IBM Vault Radar, which blocks text that looks
like a credential. Run data contains false positives (AI tool-call ids read as a Mailsac key, a website's
public OAuth client id, `pass=` in agent-written code). `scripts/mask_secrets.py <folder>` masks the known
ones (visible placeholders, tool-call ids mapped consistently so the viewer still pairs calls with
results). If a commit is still blocked, save the scanner's output to a file and run
`python3 scripts/mask_secrets.py <repo>/ci_ui --findings <file> --repo-root <repo>`, which masks exactly
those findings; then commit again. Never bypass the scanner. If a finding looks like a **real** secret,
stop and tell the team.

**Add a hand-run snapshot**: export it with cap-evolve's `export_static`
(cap-evolve's `ci/benchmarks/PUBLISHING.md`, "Open UI" section), copy its `data/` folder to
`<repo>/ci_ui/<run_id>__<tier>-<bench>/`, run `python3 scripts/mask_secrets.py <repo>/ci_ui`, commit, and
set `"has_ui": true` in the run's record.

**Update the viewer** to cap-evolve's latest dashboard: `scripts/update_viewer.sh` (needs node), then
commit `site/viewer/`. Newer viewers open older runs' data (tested back to July 2026).

---

## Tokens and secrets

Everything in the org is public, so **reading needs no token**: the dashboard's deploy clones without
credentials. Only cap-evolve's CI writes here, with two fine-grained tokens of the
bot account `skillberry-bot` (resource owner `skillberry-runs`, permission *Contents: Read and write*):

| Bot token | Repos it reaches | Secret in cap-evolve | Used by |
|---|---|---|---|
| `skillberry-runs-live` | `live` only | `SKILLBERRY_RUNS_LIVE_TOKEN` | the live poller during a run (`ci/benchmarks/lib/live_push.sh`) |
| `skillberry-runs-results` | `dashboard` and every benchmark repo | `SKILLBERRY_RUNS_RESULTS_TOKEN` | each bench job's end-of-run `Publish results to skillberry-runs` step (`ci/benchmarks/lib/publish_results.sh`, on the self-hosted runner): records here, "Open UI" data in the benchmark repo |

- **A new benchmark repo** must be added to `skillberry-runs-results` (E, step 2).
- **They expire on a fixed date** (November 2027). To renew one: as the bot, open it, *Regenerate* it with
  a new expiry, and run `gh secret set <SECRET NAME> -R skillberry-ai/cap-evolve` with the new value.
  An expired token shows up as a failed CI step (`Publish results to skillberry-runs` for results; for live, only a warning, since
  live updates are best-effort).
- If a section's repo is ever made **private**, the deploy will need a read token again: set
  `RESULTS_READ_TOKEN` in this repo (a bot token with *Contents: Read* on it); `pages.yml` uses it when set.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| A new row is not on the page | The filters. **Result** defaults to *success* (failed and cancelled runs are hidden) and **Time** to *All*. Also check that the deploy finished (Actions tab). |
| A row shows `—` for reward | `conclusion` is not `success`, or `suite` is empty because `record.py build` ran on an unfinished run. `check_records.py` warns about this. |
| Deploy is red when cloning a section's repo | The repo in `sections.json` doesn't exist or isn't public, or `RESULTS_READ_TOKEN` is set but expired (delete the secret: public repos don't need it). The log prints the token's owner and GitHub's reason. The last good site stays live. |
| Deploy is red at "Validate records" | A record failed `scripts/check_records.py`; the error names the file and the problem. |
| A link opens a 404 | A record or page links to a file that was renamed or never committed (GitHub Pages is case-sensitive: check the file name's letter case). |
| A CI run's row is missing | Look at that bench job's `Publish results to skillberry-runs` step in cap-evolve's Actions: a 403 means the results token lacks the repo (E, step 2) or expired; a record that fails `check_records.py` is not pushed. Republishing is safe (`ci/benchmarks/lib/publish_results.sh`, or A by hand). |
