#!/usr/bin/env bash
# Copy the curated bundle into the iOS app target after running curate.py.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/Tooling/canonical-sets/output/nes.json"
DEST="$ROOT/GLHF/Resources/CanonicalSets/nes.json"
if [[ ! -f "$SRC" ]]; then
  echo "Missing $SRC — run: cd Tooling/canonical-sets && uv run curate.py --platform nes" >&2
  exit 1
fi
mkdir -p "$(dirname "$DEST")"
cp "$SRC" "$DEST"
python3 -c "
import json, sys
d = json.load(open('$DEST'))
print(f\"Exported {d['id']}: {d['gameCount']} games, {d['matchedGameCount']} with rawgID\")
"
