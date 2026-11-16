#!/usr/bin/env python3
"""Publish a results repo's per-run "Open UI" data (ci_ui/) onto the dashboard site.

    python3 scripts/publish_ci_ui.py --src <checkout> --repo <name> --site site

Layout, in each results repo (skillberry-runs/<repo>):

    ci_ui/<run_id>__<tier>-<bench>/      one folder per run: the run's exported dashboard data
        index.json, runs.json, ...       (the files the viewer fetches; no viewer copy)

Output:
    site/<repo>/ci_ui/<slug>/...         the same files, with internal paths/hosts masked
    site/ui_index.json                   {"<slug>": "<repo>/ci_ui/<slug>", ...}, merged across
                                         repos; site/benchmarks.js uses it to open a row's
                                         "Open UI" in the shared viewer (site/viewer/)

The folder name is the same `<run_id>__<tier>-<bench>` slug the records and the page use, so a
row finds its data without a lookup table. Masking is the same as for write-ups (see
build_reports.REDACTIONS); every JSON file must still parse afterwards, or this exits 1.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_reports import redact  # noqa: E402

TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".log", ".html", ".csv", ".yaml", ".yml", ".diff", ".patch"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, type=Path, help="checkout of the results repo")
    ap.add_argument("--repo", required=True, help="repo name, e.g. spreadsheetbench (the site subfolder)")
    ap.add_argument("--site", type=Path, default=Path("site"), help="dashboard site dir (default: site)")
    a = ap.parse_args()

    root = a.src / "ci_ui"
    index_path = a.site / "ui_index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    if not root.is_dir():
        print(f"{a.repo}: no ci_ui/ folder, nothing to publish")
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(json.dumps(index, indent=1, sort_keys=True))
        return 0

    out_root = a.site / a.repo / "ci_ui"
    if out_root.exists():
        shutil.rmtree(out_root)
    n_runs = n_files = n_masked = 0
    bad: list[str] = []
    for run_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        slug = run_dir.name
        for f in sorted(p for p in run_dir.rglob("*") if p.is_file()):
            dst = out_root / f.relative_to(root)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if f.suffix.lower() in TEXT_SUFFIXES:
                text, k = redact(f.read_text(encoding="utf-8", errors="surrogateescape"))
                n_masked += k
                if k and f.suffix.lower() == ".json":
                    try:
                        json.loads(text)
                    except json.JSONDecodeError as e:
                        bad.append(f"{f.relative_to(a.src)}: invalid JSON after masking ({e})")
                dst.write_text(text, encoding="utf-8", errors="surrogateescape")
            else:
                shutil.copy2(f, dst)
            n_files += 1
        index[slug] = f"{a.repo}/ci_ui/{slug}"
        n_runs += 1

    index_path.write_text(json.dumps(index, indent=1, sort_keys=True))
    print(f"{a.repo}: published {n_runs} run(s), {n_files} files, masked {n_masked} internal paths/hosts")
    for b in bad:
        print(f"ERROR {b}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
