#!/usr/bin/env python3
"""Mask secret-scanner matches in run data before it is committed to a results repo.

    python3 scripts/mask_secrets.py <dir>...                     # apply the standing rules
    python3 scripts/mask_secrets.py <dir> --findings scan.txt    # also mask what a scan flagged

Why: committing to skillberry-runs goes through IBM Vault Radar ("Block Secrets"), which
stops a commit when run data contains text that looks like a credential. In the migrated
"Open UI" data every match so far was a false positive, but the policy is not ours to
override, so the matching text is replaced with a visible placeholder instead:

  rule                 example                                   becomes
  tool-call ids        toolu_bdrk_01AbC…  (read as a Mailsac key) toolu_masked_<16 hex>
  OAuth client ids     1234-abcd….apps.googleusercontent.com      <public-oauth-client-id>.apps.googleusercontent.com
  --findings matches   pass={expected_value …} (read as a password) pass={<masked> …}

Tool-call ids are mapped deterministically (same id -> same stand-in, in every file), so the
viewer still pairs each tool call with its result. Replacements never contain quotes or
backslashes, and every .json file must still parse afterwards, or this exits 1. Originals
remain on cap-evolve's benchmark-history branch.

--findings takes the scanner's text output (the "error: <file>:<line>:<col>: detected <kind>"
lines of a blocked commit) and masks the value at each reported position. Run the commit again
afterwards; repeat until it passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

TOOL_ID = re.compile(r"toolu_(?:bdrk_|vrtx_)?[A-Za-z0-9]{16,}")
OAUTH = re.compile(r"\b\d{6,}-[a-z0-9]{16,}\.apps\.googleusercontent\.com\b")
FINDING = re.compile(r"error:\s+(\S+?):(\d+):(\d+):\s+detected (.+?): severity")
# the value after an assignment-like keyword, as Vault Radar's "Password assignment" sees it
ASSIGNED_VALUE = re.compile(rb"(?i)(pass(?:word|wd)?|pwd|secret|token|api_?key)(\W{0,8}?[:=]\W{0,8}?)([A-Za-z0-9_.!@#$%^&*+\-]{3,})")


def standing_rules(text: str) -> tuple[str, int]:
    n = 0

    def tid(m: re.Match) -> str:
        return "toolu_masked_" + hashlib.sha256(m.group(0).encode()).hexdigest()[:16]

    text, k = TOOL_ID.subn(tid, text)
    n += k
    text, k = OAUTH.subn("<public-oauth-client-id>.apps.googleusercontent.com", text)
    n += k
    return text, n


def mask_at(raw: bytes, line: int, col: int) -> tuple[bytes, bool]:
    """Mask the assigned value nearest to (line, col) — col is a byte offset in that line."""
    lines = raw.split(b"\n")
    if not 1 <= line <= len(lines):
        return raw, False
    s = lines[line - 1]
    best = None
    for m in ASSIGNED_VALUE.finditer(s, max(0, col - 64), min(len(s), col + 256)):
        d = abs(m.start() - col)
        if best is None or d < best[0]:
            best = (d, m)
    if best is None:
        return raw, False
    m = best[1]
    lines[line - 1] = s[: m.start(3)] + b"<masked>" + s[m.end(3):]
    return b"\n".join(lines), True


def check_json(p: Path) -> str | None:
    if p.suffix.lower() != ".json":
        return None
    try:
        json.loads(p.read_text(encoding="utf-8", errors="surrogateescape"))
    except json.JSONDecodeError as e:
        return f"{p}: invalid JSON after masking ({e})"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+", type=Path, help="folders to mask in place (e.g. <repo>/ci_ui)")
    ap.add_argument("--findings", type=Path, help="Vault Radar output from a blocked commit")
    ap.add_argument("--repo-root", type=Path, default=Path("."), help="paths in --findings are relative to this")
    a = ap.parse_args()

    bad: list[str] = []
    n_files = n_rules = 0
    for d in a.dirs:
        for p in sorted(x for x in d.rglob("*") if x.is_file()):
            text = p.read_text(encoding="utf-8", errors="surrogateescape")
            new, k = standing_rules(text)
            if k:
                p.write_text(new, encoding="utf-8", errors="surrogateescape")
                n_files += 1
                n_rules += k
                if (e := check_json(p)):
                    bad.append(e)
    print(f"standing rules: {n_rules} replacement(s) in {n_files} file(s)")

    if a.findings:
        found = FINDING.findall(a.findings.read_text())
        done = 0
        for rel, line, col, kind in found:
            p = a.repo_root / rel
            if not p.is_file():
                print(f"  skip (no such file): {rel}")
                continue
            if kind in ("Mailsac API key", "Google OAuth client ID"):
                continue  # handled by the standing rules above
            raw, ok = mask_at(p.read_bytes(), int(line), int(col))
            if ok:
                p.write_bytes(raw)
                done += 1
                if (e := check_json(p)):
                    bad.append(e)
            else:
                print(f"  could not locate the value for: {rel}:{line}:{col} ({kind}) — mask it by hand")
        print(f"findings: {len(found)} reported, {done} masked by position")

    for b in bad:
        print(f"ERROR {b}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
