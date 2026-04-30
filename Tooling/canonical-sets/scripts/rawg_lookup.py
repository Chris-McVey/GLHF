#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests>=2.31",
#   "rapidfuzz>=3.0",
#   "lxml>=5.0",
#   "cssselect>=1.2",
# ]
# ///
"""Surface top-N RAWG candidates for the entries in the review report's
'RAWG resolution issues' section.

Reads from .cache/rawg-search/ when possible (already populated by curate.py
runs), falls back to a live API call when needed. Output is a markdown table
the reviewer can scan to pick the right RAWG ID.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CACHE_DIR, PLATFORMS
from sources import rawg as rawg_mod

NES = PLATFORMS["nes"]
PLATFORM_ID = NES.rawg_platform_id


def cache_path(name: str, platform_id: int | None) -> Path:
    key = f"{platform_id if platform_id is not None else 'any'}::{name}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / "rawg-search" / f"{digest}.json"


def load_top(name: str, api_key: str | None, *, n: int = 5):
    """Return up to N RAWG candidates for `name`. Use cache if present."""
    p = cache_path(name, PLATFORM_ID)
    if p.exists():
        results = json.loads(p.read_text()).get("results", [])
    elif api_key:
        results = rawg_mod._search(name, PLATFORM_ID, api_key).get("results", [])
    else:
        return []
    if not results and api_key:
        broad = rawg_mod._search(name, None, api_key).get("results", [])
        results = [c for c in broad if rawg_mod._has_platform(c, PLATFORM_ID)]
    return results[:n]


PROBLEM_TITLES = """\
Tag Team Match: MUSCLE
Eggerland
Exciting Baseball
Golf: Japan Course
Miracle Warriors: Seal of the Dark Lord
Titanic Mystery: Ao no Senritsu
Elite (video game)
Exciting Soccer: Konami Cup
Jeopardy!
720°
Hollywood Squares
Jesus
Metal Fighter
Mother
Short Order / Eggsplode!
Thunderbirds
Classic Concentration
Dragon Power
Fisher-Price: Perfect Fit
Galactic Crusader
Heavy Barrel
Jeopardy! 25th Anniversary Edition
Krazy Kreatures
Mission Cobra
Orb-3D
Parodius! From Myth to Laughter
Total Recall
Cowboy Kid
Monopoly
Dragon Warrior IV
Rod Land
Star Wars: The Empire Strikes Back
Rackets & Rivals
Stinger
Tiny Toon Adventures 6
Mario Bros. Classic Series
3-in-1 Super Mario Bros./Tetris/Nintendo World Cup
Wheel of Fortune: Featuring Vanna White
Jeopardy! Junior Edition
Super Jeopardy!
Fisher-Price: Firehouse Rescue
Fisher-Price: I Can Remember
Remote Control
The Legend of Prince Valiant
Archon
Castelian
KlashBall
Overlord
Thunder & Lightning
""".strip().splitlines()


def lookup_one(query: str, api_key: str | None, *, n: int = 5):
    """Direct RAWG lookup for a single query. Bypasses cache."""
    if not api_key:
        return []
    results = rawg_mod._search(query, PLATFORM_ID, api_key).get("results", [])
    if not results:
        broad = rawg_mod._search(query, None, api_key).get("results", [])
        results = [c for c in broad if rawg_mod._has_platform(c, PLATFORM_ID)]
    return results[:n]


def main():
    api_key = None
    if len(sys.argv) > 1 and sys.argv[1] == "--live":
        from curate import _load_rawg_api_key
        api_key = _load_rawg_api_key()
    elif len(sys.argv) > 2 and sys.argv[1] == "--query":
        from curate import _load_rawg_api_key
        api_key = _load_rawg_api_key()
        for query in sys.argv[2:]:
            print(f"## {query}")
            for c in lookup_one(query, api_key, n=5):
                cid = c.get("id")
                cname = c.get("name") or "(no name)"
                crel = (c.get("released") or "")[:4] or "—"
                print(f"  - `{cid}` {cname!r:50s} ({crel})")
            print()
        return

    print(f"# RAWG candidate lookup ({len(PROBLEM_TITLES)} titles)")
    print()
    for title in PROBLEM_TITLES:
        cands = load_top(title, api_key, n=5)
        print(f"## {title}")
        if not cands:
            print(f"  (no cached results — re-run with --live or accept rawgID:null)")
            print()
            continue
        for c in cands:
            cid = c.get("id")
            cname = c.get("name") or "(no name)"
            crel = (c.get("released") or "")[:4] or "—"
            crating = c.get("rating") or 0
            print(f"  - `{cid}` {cname!r:50s} ({crel}) rating={crating}")
        print()


if __name__ == "__main__":
    main()
