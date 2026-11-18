#!/usr/bin/env python3
"""Check that the benchmark-runs page still matches cap-evolve's Benchmarks workflow.

    python3 scripts/check_site.py                     # fetch cap-evolve's benchmarks.yml from main
    python3 scripts/check_site.py --workflow <file>   # or use a local copy

Moved here from cap-evolve's core/tests/test_site_live_panel_tiers.py (2026-11) along with the
page. The "Running now" panel matches CI job names ("<tier> / <bench>") with JOB_RE; a tier or
bench it cannot match is a running job that is silently invisible (this happened when the
`pilot` tier landed). The tier and bench lists live in cap-evolve, so this compares against
them. Exit 1 on any failure.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = ROOT / "site" / "benchmarks.js"
HTML = ROOT / "site" / "index.html"
WORKFLOW_URL = "https://raw.githubusercontent.com/skillberry-ai/cap-evolve/main/.github/workflows/benchmarks.yml"


def _list(src: str, name: str) -> list[str]:
    m = re.search(rf"^\s*{name}\s*=\s*\[([^\]]*)\]", src, re.M | re.S)
    if not m:
        raise SystemExit(f"{name} not found in benchmarks.yml")
    return re.findall(r'"([^"]+)"', m.group(1))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workflow", type=Path, help="local copy of cap-evolve's benchmarks.yml")
    a = ap.parse_args()
    wf = a.workflow.read_text() if a.workflow else urllib.request.urlopen(WORKFLOW_URL, timeout=30).read().decode()
    js, html = JS.read_text(encoding="utf-8"), HTML.read_text(encoding="utf-8")
    tiers, benches = _list(wf, "TIERS"), _list(wf, "BENCHES")
    fails: list[str] = []

    m = re.search(r"JOB_RE\s*=\s*/(.+?)/[gimsuy]*\s*;", js)
    if not m:
        fails.append("JOB_RE not found in site/benchmarks.js")
    else:
        rx = re.compile(m.group(1).replace("\\/", "/"))
        missing = [f"{t} / {b}" for t in tiers for b in benches if not rx.match(f"{t} / {b}")]
        if missing:
            fails.append(f"JOB_RE does not match these CI job names, so they'd be invisible in 'Running now': {missing}")
        g = rx.match("pilot / spreadsheetbench")
        if not (g and g.group(1) == "pilot" and g.group(2) == "spreadsheetbench"):
            fails.append("JOB_RE must capture tier as group 1 and bench as group 2 (the live links use them)")
        for name in ("plan legs", "aggregate history", "collect-pr-context", "Test Python (core)"):
            if rx.match(name):
                fails.append(f"JOB_RE matches the non-leg job {name!r}")

    if not re.search(r'<select[^>]*id="f-tier"', html):
        fails.append("the f-tier select is missing from site/index.html")
    if not re.search(r'fillSelect\(\s*\$\("#f-tier"\)\s*,\s*tierOptions\(', js):
        fails.append('benchmarks.js must fill the tier filter from records: fillSelect($("#f-tier"), tierOptions(...))')

    if not re.search(r'<th data-k="algorithm">', html):
        fails.append("the table has no Algorithm column (a hill-climb and an agent-optimize number would look comparable)")
    if "r.algorithm" not in js:
        fails.append("benchmarks.js never renders the record's algorithm field")
    head = html[html.index("<thead><tr>"):html.index("</thead>")] if "<thead><tr>" in html else ""
    n_cols = len(re.findall(r"<th\b", head))
    span = re.search(r'colspan="(\d+)"', js)
    if not span or int(span.group(1)) != n_cols:
        fails.append(f"the detail row's colspan ({span.group(1) if span else None}) != header columns ({n_cols})")

    print(f"checked against {len(tiers)} tier(s) x {len(benches)} bench(es): "
          + ("OK" if not fails else f"{len(fails)} failure(s)"))
    for f in fails:
        print("FAIL", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
