#!/usr/bin/env python3
"""Copy run records (and run notes) from cap-evolve's `benchmark-history` branch into this repo.

    python3 scripts/sync_from_cap_evolve.py                 # fetch from GitHub, copy what is new
    python3 scripts/sync_from_cap_evolve.py --dry-run       # show what would change, write nothing
    python3 scripts/sync_from_cap_evolve.py --update-existing   # also overwrite records that differ
    python3 scripts/sync_from_cap_evolve.py --src <checkout>    # use a local checkout (tests)

This is the migration process for runs that still land on cap-evolve's `benchmark-history`
branch (CI's `aggregate history` job, or a manual publish there). Run it whenever you want
those runs on the dashboard; it is safe to run repeatedly. When cap-evolve's CI writes
straight to this repo, this script is no longer needed.

What it copies (only these two folders are fetched; the branch's ~3 GB of per-run UI
snapshots and live data are NOT, via a sparse partial clone):
  records/*.json   -> records/       new files only (or changed ones with --update-existing)
  docs/runs/*.md   -> notes/runs/    new files only
Links in copied records that point at cap-evolve's retired `*-history` branches are
repointed to where that content lives now (the dashboard's sections, SkillsBench included). Every copied record is validated with check_records.py first; one that fails is
skipped and reported, and the script exits 1 so the problem is visible.

Writes GITHUB_OUTPUT (when set): `added`, `updated`, `changed` (true/false).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_records import validate  # noqa: E402

DEFAULT_SOURCE = "https://github.com/skillberry-ai/cap-evolve.git"
DEFAULT_BRANCH = "benchmark-history"
DASHBOARD = "https://skillberry-runs.github.io/dashboard"
CAP_EVOLVE_SITE = "https://skillberry-ai.github.io/cap-evolve"

# Links to cap-evolve's rendered SkillsBench pages; that section now lives on the dashboard.
SITE_LINK_RE = re.compile(r"https://skillberry-ai\.github\.io/cap-evolve/skillsbench/")

LINK_RE = re.compile(
    r"https://github\.com/skillberry-ai/cap-evolve/(?:blob|tree)/"
    r"(parsec-history|spreadsheet-history|skillsbench-history|benchmark-history)/([^\"\s]+)"
)


def remap_link(m: re.Match) -> str:
    """Where a link into a retired cap-evolve branch lives now (unchanged if unknown)."""
    branch, path = m.group(1), m.group(2)
    html = path[:-3] + ".html" if path.endswith(".md") else path
    if branch == "parsec-history":
        return f"{DASHBOARD}/parsec/{html}"
    if branch == "spreadsheet-history":
        return f"{DASHBOARD}/spreadsheetbench/{html}"
    if branch == "skillsbench-history":
        return f"{DASHBOARD}/skillsbench/{html}"
    if branch == "benchmark-history" and path.startswith("docs/runs/") and path.endswith(".md"):
        return f"{DASHBOARD}/notes/runs/{html[len('docs/runs/'):]}"
    return m.group(0)


def fetch_source(url: str, branch: str, into: Path) -> Path:
    """Sparse, blob-less shallow clone: downloads records/ and docs/runs/ only."""
    run = lambda *a: subprocess.run(a, check=True, capture_output=True, text=True)  # noqa: E731
    run("git", "clone", "--quiet", "--depth", "1", "--filter=blob:none", "--sparse",
        "--branch", branch, url, str(into))
    run("git", "-C", str(into), "sparse-checkout", "set", "records", "docs/runs")
    return into


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=DEFAULT_SOURCE, help="git URL to fetch from")
    ap.add_argument("--branch", default=DEFAULT_BRANCH)
    ap.add_argument("--src", type=Path, help="use this local checkout instead of fetching")
    ap.add_argument("--dest", type=Path, default=Path("."), help="dashboard repo root (default: cwd)")
    ap.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    ap.add_argument("--update-existing", action="store_true",
                    help="overwrite records already here when the source copy differs")
    a = ap.parse_args()

    tmp = None
    if a.src:
        src = a.src
    else:
        tmp = Path(tempfile.mkdtemp(prefix="sync-ce-"))
        print(f"fetching {a.source} @ {a.branch} (records/ and docs/runs/ only)…")
        src = fetch_source(a.source, a.branch, tmp / "src")

    rec_dst, note_dst = a.dest / "records", a.dest / "notes" / "runs"
    added, updated, same, kept, bad = [], [], 0, [], []

    for f in sorted((src / "records").glob("*.json")):
        text = LINK_RE.sub(remap_link, f.read_text(encoding="utf-8"))
        text = SITE_LINK_RE.sub(f"{DASHBOARD}/skillsbench/", text)
        errs, warns = validate(f.name, text)
        if errs:
            bad.append((f.name, errs))
            continue
        for w in warns:
            print(f"warning {f.name}: {w}")
        dst = rec_dst / f.name
        if not dst.exists():
            added.append(f.name)
        elif dst.read_text(encoding="utf-8") == text:
            same += 1
            continue
        elif a.update_existing:
            updated.append(f.name)
        else:
            kept.append(f.name)
            continue
        if not a.dry_run:
            rec_dst.mkdir(parents=True, exist_ok=True)
            dst.write_text(text, encoding="utf-8")

    notes_added = []
    for f in sorted((src / "docs" / "runs").glob("*.md")) if (src / "docs" / "runs").is_dir() else []:
        if not (note_dst / f.name).exists():
            notes_added.append(f.name)
            if not a.dry_run:
                note_dst.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, note_dst / f.name)

    verb = "would add" if a.dry_run else "added"
    print(f"\nrecords: {verb} {len(added)}, {'would update' if a.dry_run else 'updated'} {len(updated)}, "
          f"already identical {same}, differ but kept {len(kept)}, rejected {len(bad)}")
    for n in added:
        print(f"  + {n}")
    for n in updated:
        print(f"  ~ {n}")
    for n in kept:
        print(f"  = {n}  (differs from cap-evolve's copy; rerun with --update-existing to overwrite)")
    print(f"notes:   {verb} {len(notes_added)}")
    for n in notes_added:
        print(f"  + notes/runs/{n}")
    for name, errs in bad:
        for e in errs:
            print(f"REJECTED {name}: {e}")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        changed = bool(added or updated or notes_added) and not a.dry_run
        with open(out, "a") as fh:
            fh.write(f"added={len(added)}\nupdated={len(updated)}\nchanged={str(changed).lower()}\n")
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
