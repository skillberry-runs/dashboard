#!/usr/bin/env python3
"""Validate records/*.json before they reach the dashboard.

    python3 scripts/check_records.py                 # check every record in records/
    python3 scripts/check_records.py records/X.json  # check specific files

Exit 1 on any ERROR (the deploy and the sync workflow stop). WARNINGs are printed but
do not fail: they flag things worth a look, such as a row that will show "—" for reward.

What a record must satisfy is what the page and `record.py aggregate` rely on:
  - valid JSON object, named `<id>__<label>.json` (CI uses the Actions run id as <id>;
    hand-published runs use a sortable id such as 20261001001, so it need not equal run_id)
  - run_id (number, or a string for old manual runs), bench, date (ISO-8601 UTC, `…Z`)
  - conclusion in {success, failure, cancelled}
  - links (run_url / summary_url / report_url) are absolute https URLs and do not point at
    cap-evolve's retired `*-history` branches (those were migrated to skillberry-runs)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REQUIRED = ("run_id", "bench", "date", "conclusion")
CONCLUSIONS = {"success", "failure", "cancelled"}
NAME_RE = re.compile(r"^[A-Za-z0-9._-]+__[A-Za-z0-9._-]+\.json$")
DATE_RE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
LINK_FIELDS = ("run_url", "summary_url", "report_url")
RETIRED_BRANCHES = ("parsec-history", "spreadsheet-history", "skillsbench-history")


def validate(name: str, text: str) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for one record's file name and text."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        r = json.loads(text)
    except json.JSONDecodeError as e:
        return [f"not valid JSON: {e}"], []
    if not isinstance(r, dict):
        return ["top level must be a JSON object"], []

    for k in REQUIRED:
        if r.get(k) in (None, ""):
            errors.append(f"missing required field '{k}'")
    if errors:
        return errors, warnings

    if not NAME_RE.match(name):
        errors.append("file name must look like '<id>__<label>.json' (letters, digits, . _ - only)")
    if isinstance(r["run_id"], bool) or not isinstance(r["run_id"], (int, str)):
        errors.append("run_id must be a number (or a string for old manual runs)")
    if not DATE_RE.match(str(r["date"])):
        errors.append(f"date must be ISO-8601 UTC like 2026-08-05T12:00:00Z, got {r['date']!r}")
    if r["conclusion"] not in CONCLUSIONS:
        errors.append(f"conclusion must be one of {sorted(CONCLUSIONS)}, got {r['conclusion']!r}")

    for k in LINK_FIELDS:
        v = r.get(k)
        if not v:
            continue
        if not str(v).startswith("https://"):
            errors.append(f"{k} must be an absolute https URL, got {v!r}")
        elif any(f"/{b}/" in v for b in RETIRED_BRANCHES):
            errors.append(f"{k} points at a retired cap-evolve branch: {v}")

    if r["conclusion"] == "success" and not r.get("suite"):
        warnings.append("conclusion is 'success' but 'suite' is empty: the page will show — for reward "
                        "(was record.py build run on a finished run's metrics?)")
    if not r.get("source"):
        warnings.append("no 'source' text: say how this run was produced or published")
    return errors, warnings


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv[1:]] or sorted(Path("records").glob("*.json"))
    if not paths:
        print("no records found", file=sys.stderr)
        return 1
    n_err = n_warn = 0
    for p in paths:
        errs, warns = validate(p.name, p.read_text(encoding="utf-8"))
        for e in errs:
            print(f"ERROR   {p.name}: {e}")
        for w in warns:
            print(f"warning {p.name}: {w}")
        n_err += len(errs)
        n_warn += len(warns)
    print(f"checked {len(paths)} record(s): {n_err} error(s), {n_warn} warning(s)")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
