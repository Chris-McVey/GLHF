"""No-Intro DAT parser (XML from DAT-o-MATIC or ClrMamePro from libretro mirror).

Used as a *tertiary validator* for the Wikidata candidate list and as a
hard reference for completeness gaps. No-Intro encodes region in a
parenthetical suffix on each game name:

    Super Mario Bros. (USA)
    Mother (Japan)
    10-Yard Fight (USA, Europe)

For strict-Western policy we keep only games whose region tag is one of
USA / Europe / World / USA, Europe (multi-region carts).

Official source: https://datomatic.no-intro.org/ (XML, captcha login).
Dev/bootstrap mirror: libretro-database ClrMamePro DAT (same naming, cites
no-intro) — see `scripts/fetch_nes_dat.sh`.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from config import NOINTRO_DIR, PlatformConfig
from matching import normalize

_TAG_GROUP = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]\s*")
_REGION_GROUP = re.compile(r"\(([^)]*)\)")

_WESTERN_REGION_TOKENS = ("usa", "europe", "world", "australia")

_EXCLUDE_TAGS = frozenset({
    "proto", "prototype", "beta", "sample", "demo",
    "test program", "debug", "kiosk",
})

_UNLICENSED_TAGS = frozenset({
    "unl", "unlicensed", "aftermarket", "homebrew",
})

_CLRMAME_NAME_RE = re.compile(r'^\s+name "([^"]+)"\s*$', re.MULTILINE)


def load(platform: PlatformConfig) -> dict[str, dict[str, Any]]:
    """Return a dict keyed on normalized title for the platform's DAT."""
    dat_path = NOINTRO_DIR / platform.nointro_dat_filename
    if not dat_path.exists():
        print(
            f"[no-intro] DAT not found at {dat_path.relative_to(NOINTRO_DIR.parent.parent)}.\n"
            f"          Run: ./scripts/fetch_nes_dat.sh\n"
            f"          Or download XML from https://datomatic.no-intro.org/ "
            f"(System → 'Nintendo - Nintendo Entertainment System (Headered) "
            f"(Parent-Clone)'). Skipping No-Intro validation."
        )
        return {}

    print(f"[no-intro] Parsing {dat_path.name} ({_detect_format(dat_path)})")
    raw_names = _read_raw_names(dat_path)
    return _build_western_index(raw_names)


def _detect_format(dat_path: Path) -> str:
    head = dat_path.read_text(encoding="utf-8", errors="replace")[:200].lstrip()
    if head.startswith("<?xml") or head.startswith("<"):
        return "XML"
    if head.lower().startswith("clrmamepro"):
        return "ClrMamePro"
    return "unknown"


def _read_raw_names(dat_path: Path) -> list[str]:
    text = dat_path.read_text(encoding="utf-8", errors="replace")
    fmt = _detect_format(dat_path)
    if fmt == "XML":
        root = ET.fromstring(text)
        return [
            name for game in root.iter("game")
            if (name := (game.get("name") or "").strip())
        ]
    if fmt == "ClrMamePro":
        return _CLRMAME_NAME_RE.findall(text)
    raise ValueError(f"Unsupported DAT format in {dat_path}")


def _build_western_index(raw_names: list[str]) -> dict[str, dict[str, Any]]:
    games: dict[str, dict[str, Any]] = {}
    skipped_excluded = 0

    for raw_name in raw_names:
        tags = [t.strip().lower() for t in _REGION_GROUP.findall(raw_name)]
        if any(t in _EXCLUDE_TAGS or any(x in t for x in _EXCLUDE_TAGS) for t in tags):
            skipped_excluded += 1
            continue

        is_unlicensed = any(
            t in _UNLICENSED_TAGS or any(x in t for x in _UNLICENSED_TAGS)
            for t in tags
        )

        region_tag = next(
            (t for t in tags if any(r in t for r in (
                "usa", "europe", "world", "japan", "australia", "spain",
                "france", "germany", "italy", "netherlands", "sweden",
                "korea", "taiwan", "china", "asia", "brazil",
            ))),
            None,
        )

        title_clean = _TAG_GROUP.sub("", raw_name).strip()
        if not title_clean:
            continue
        key = normalize(title_clean)
        if not key:
            continue

        if key not in games:
            games[key] = {
                "title": title_clean,
                "regions": set(),
                "raw_names": [],
                "is_unlicensed": True,
            }
        games[key]["regions"].add(region_tag or "unknown")
        games[key]["raw_names"].append(raw_name)
        if not is_unlicensed:
            games[key]["is_unlicensed"] = False

    western_only: dict[str, dict[str, Any]] = {}
    for key, record in games.items():
        regions = record["regions"]
        record["regions"] = sorted(regions)
        record["has_western_release"] = any(
            any(w in r for w in _WESTERN_REGION_TOKENS)
            for r in regions
        )
        record["is_unlicensed"] = record.get("is_unlicensed", False)
        if record["has_western_release"]:
            western_only[key] = record

    if skipped_excluded:
        print(
            f"[no-intro] Skipped {skipped_excluded} entries tagged "
            f"Proto/Beta/Sample/Demo/Kiosk."
        )
    print(
        f"[no-intro] Parsed {len(games)} unique titles ({len(western_only)} with a "
        f"Western region tag)."
    )
    return western_only
