#!/usr/bin/env bash
# Fetch a No-Intro-derived NES DAT (ClrMamePro format) from libretro-database.
# DAT-o-MATIC XML requires manual captcha login; this mirror uses the same
# No-Intro naming convention (see file header: "comment no-intro").
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/data/no-intro/nes.dat"
mkdir -p "$(dirname "$DEST")"
URL="https://raw.githubusercontent.com/libretro/libretro-database/master/dat/Nintendo%20-%20Nintendo%20Entertainment%20System.dat"
echo "Downloading libretro No-Intro-derived NES DAT..."
curl -fsSL "$URL" -o "$DEST"
BYTES=$(wc -c < "$DEST" | tr -d ' ')
echo "Saved $DEST ($BYTES bytes)"
head -n 11 "$DEST"
