#!/usr/bin/env python3
"""Copy per-run "Open UI" data from cap-evolve's benchmark-history into the benchmark repos.

    python3 scripts/migrate_ui_snapshots.py --repos-dir .. --dry-run    # what would be copied
    python3 scripts/migrate_ui_snapshots.py --repos-dir ..              # copy into the checkouts
    python3 scripts/migrate_ui_snapshots.py --repos-dir .. --commit     # ...and commit in each repo

For every record in records/ with `has_ui: true`, the run's snapshot on cap-evolve's
`benchmark-history` branch is runs/<slug>/ui/: a copy of the viewer app plus data/. Only data/
is copied, to <repos-dir>/<repo>/ci_ui/<slug>/ in the checkout of the repo that owns that
benchmark (sections.json: a section's "benches", default [its repo name]). The viewer itself
is shared, in this repo's site/viewer/. <slug> is `<run_id>__<tier>-<bench>`.

Before committing, the copied data is masked with scripts/mask_secrets.py's standing rules
(tool-call ids, public OAuth client ids), which the repos' secret scanner otherwise blocks. If
a commit is still blocked, save the scanner output and run
`python3 scripts/mask_secrets.py <repo>/ci_ui --findings scan.txt --repo-root <repo>`, then commit.

Records whose bench has no repo yet are listed and left alone; their "Open UI" keeps opening
cap-evolve's copy. Runs already copied are skipped, so this is safe to rerun for new runs.
Pushing each repo is left to you (`git -C <repos-dir>/<repo> push`).

Only the needed folders are downloaded (sparse, blob-less clone of the branch).
"""
from __future__ import annotations

import argparse
import collections
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mask_secrets import standing_rules  # noqa: E402

SOURCE = "https://github.com/skillberry-ai/cap-evolve.git"
BRANCH = "benchmark-history"
ROOT = Path(__file__).resolve().parent.parent


def slug_of(r: dict) -> str:
    return f"{r['run_id']}__{r.get('tier') or 'smoke'}-{r['bench']}"


def git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repos-dir", type=Path, required=True, help="folder holding checkouts of the benchmark repos")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true", help="git add + commit ci_ui/ in each changed repo")
    a = ap.parse_args()

    sections = json.loads((ROOT / "sections.json").read_text())
    owner = {b: s["repo"] for s in sections for b in s.get("benches", [s["repo"]])}
    # runs deliberately left on cap-evolve, with the reason (sections.json "skip_ui": {slug: reason})
    skip = {slug: why for s in sections for slug, why in s.get("skip_ui", {}).items()}

    want: dict[str, list[str]] = collections.defaultdict(list)   # repo -> slugs to copy
    no_repo: collections.Counter = collections.Counter()
    for p in sorted((ROOT / "records").glob("*.json")):
        r = json.loads(p.read_text())
        if not r.get("has_ui"):
            continue
        repo = owner.get(r["bench"])
        if repo is None:
            no_repo[r["bench"]] += 1
            continue
        if slug_of(r) in skip:
            print(f"skipping {slug_of(r)}: {skip[slug_of(r)]}")
            continue
        if not (a.repos_dir / repo / "ci_ui" / slug_of(r)).exists():
            want[repo].append(slug_of(r))

    for repo in want:
        if not (a.repos_dir / repo / ".git").exists():
            print(f"ERROR: no checkout of {repo} at {a.repos_dir / repo}", file=sys.stderr)
            return 1

    total = sum(len(v) for v in want.values())
    print(f"to copy: {total} run(s) " + ", ".join(f"{r}: {len(v)}" for r, v in sorted(want.items())))
    if no_repo:
        print("left on cap-evolve (bench has no repo yet): " + ", ".join(f"{b} ({n})" for b, n in no_repo.most_common()))
    if a.dry_run or not total:
        return 0

    tmp = Path(tempfile.mkdtemp(prefix="ui-migrate-"))
    src = tmp / "bh"
    print(f"fetching {total} snapshot data folder(s) from {BRANCH}…")
    git("clone", "--quiet", "--depth", "1", "--filter=blob:none", "--sparse", "--branch", BRANCH, SOURCE, str(src))
    git("sparse-checkout", "set", *[f"runs/{s}/ui/data" for v in want.values() for s in v], cwd=src)

    missing = []
    for repo, slugs in sorted(want.items()):
        n_files = size = 0
        for slug in slugs:
            data = src / "runs" / slug / "ui" / "data"
            if not data.is_dir():
                missing.append(slug)
                continue
            dst = a.repos_dir / repo / "ci_ui" / slug
            shutil.copytree(data, dst)
            files = [f for f in dst.rglob("*") if f.is_file()]
            for f in files:  # mask what the secret scanner would block (see mask_secrets.py)
                text = f.read_text(encoding="utf-8", errors="surrogateescape")
                new, k = standing_rules(text)
                if k:
                    f.write_text(new, encoding="utf-8", errors="surrogateescape")
            n_files += len(files)
            size += sum(f.stat().st_size for f in files)
        print(f"  {repo}: {len(slugs) - sum(1 for s in missing if s in slugs)} run(s), {n_files} files, {size / 1e6:.0f} MB")
        if a.commit:
            git("add", "ci_ui", cwd=a.repos_dir / repo)
            r = subprocess.run(["git", "commit", "-q", "-m",
                f"ci_ui: add the Open UI data of {len(slugs)} run(s) from cap-evolve benchmark-history\n\n"
                "One folder per run, ci_ui/<run_id>__<tier>-<bench>/, holding the run's exported dashboard data\n"
                "(runs/<slug>/ui/data/ on the branch). Published on the dashboard and opened in its shared viewer.\n"
                "Masked with scripts/mask_secrets.py (secret-scanner false positives)."],
                cwd=a.repos_dir / repo, capture_output=True, text=True)
            if r.returncode:
                scan = a.repos_dir / repo / ".scan-blocked.txt"
                scan.write_text(r.stdout + r.stderr)
                print(f"  {repo}: commit BLOCKED (scanner output in {scan}). Mask with:\n"
                      f"    python3 scripts/mask_secrets.py {a.repos_dir / repo}/ci_ui --findings {scan} "
                      f"--repo-root {a.repos_dir / repo}\n  then commit ci_ui/ by hand (delete {scan.name} first).")
    shutil.rmtree(tmp, ignore_errors=True)
    for s in missing:
        print(f"WARNING: record says has_ui but benchmark-history has no runs/{s}/ui/data/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
