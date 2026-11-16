#!/usr/bin/env bash
# Rebuild the shared "Open UI" viewer (site/viewer/) from cap-evolve's dashboard frontend.
#
#   scripts/update_viewer.sh            # build from cap-evolve's main
#   scripts/update_viewer.sh <ref>      # or from a branch/tag/sha
#
# One viewer serves every run: a row's "Open UI" opens site/viewer/index.html?dataBase=<run data>,
# where the data is <bench>/ci_ui/<run_id>__<tier>-<bench>/ (see scripts/publish_ci_ui.py).
# Old runs' data opens fine in a newer viewer (tested back to July 2026 snapshots).
# Needs git, node and npm. Commit site/viewer/ afterwards.
set -euo pipefail
REF="${1:-main}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
git clone --quiet --depth 1 --filter=blob:none --sparse --branch "$REF" \
  https://github.com/skillberry-ai/cap-evolve.git "$TMP/ce" 2>/dev/null \
  || { git clone --quiet --filter=blob:none --sparse https://github.com/skillberry-ai/cap-evolve.git "$TMP/ce"; git -C "$TMP/ce" checkout --quiet "$REF"; }
git -C "$TMP/ce" sparse-checkout set dashboard/frontend
SHA="$(git -C "$TMP/ce" rev-parse HEAD)"
( cd "$TMP/ce/dashboard/frontend" && npm ci --silent --no-audit --no-fund && VITE_STATIC=1 npx vite build --outDir "$TMP/out" --emptyOutDir >/dev/null )
rm -rf "$ROOT/site/viewer" && cp -R "$TMP/out" "$ROOT/site/viewer"
printf 'CapEvolve dashboard viewer, static build (VITE_STATIC=1) of\nskillberry-ai/cap-evolve dashboard/frontend @ %s\nbuilt %s by scripts/update_viewer.sh\n' "$SHA" "$(date -u +%Y-%m-%d)" > "$ROOT/site/viewer/VERSION.txt"
echo "site/viewer/ rebuilt from cap-evolve @ ${SHA:0:9} ($(du -sh "$ROOT/site/viewer" | cut -f1))"
