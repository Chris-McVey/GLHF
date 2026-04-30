"""No-Intro DAT XML parser.

Used as a *tertiary validator* for the Wikidata candidate list and as a
hard reference for completeness gaps. No-Intro encodes region in a
parenthetical suffix on each `<game name="...">` entry:

    Super Mario Bros. (USA)
    Mother (Japan)
    Akumajou Densetsu (Japan)        ← e.g. "Castlevania III" Famicom version
    Bram Stoker's Dracula (Europe)

For strict-Western policy we keep only games whose region tag is one of
USA / Europe / World / USA, Europe (multi-region carts).

Datomatic requires a captcha login so we don't auto-download. The DAT must
be obtained manually and placed at `data/no-intro/<filename>` per the
platform config; the curator script will print clear instructions if it's
missing.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

from config import NOINTRO_DIR, PlatformConfig
from matching import normalize

# Strip everything inside parentheses or brackets from a No-Intro filename
# (region, language, revision, prototype tags, etc.) to recover the canonical
# title. Walk left-to-right so we keep `Mega Man 2` from `Mega Man 2 (USA)`
# and from `Mega Man 2 (USA) (Rev 1)`.
_TAG_GROUP = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]\s*")
_REGION_GROUP = re.compile(r"\(([^)]*)\)")

_WESTERN_REGION_TAGS = frozenset({
    "usa", "europe", "world", "usa, europe", "usa, australia",
    "europe, usa", "europe, australia", "australia",
})

# Pre-release / non-retail artifacts we always drop (these never shipped at
# retail in any form and aren't in scope for a canonical set).
_EXCLUDE_TAGS = frozenset({
    "proto", "prototype", "beta", "sample", "demo",
    "test program", "debug", "kiosk",
})

# Tags that indicate the cartridge shipped at retail BUT without official
# platform-holder licensing (Tengen, Color Dreams, Camerica, Wisdom Tree,
# Panesian, etc.). We keep these in the canonical set and surface the
# license status as a structured field.
_UNLICENSED_TAGS = frozenset({
    "unl", "unlicensed", "aftermarket", "homebrew",
})


def load(platform: PlatformConfig) -> dict[str, dict[str, Any]]:
    """Return a dict keyed on normalized title for the platform's DAT.

    Each record carries `{title, regions, has_western_release, raw_names}`.
    `regions` is the union of region tags across all entries (a multi-cart
    might appear once as Europe-only and once as USA-only).
    """
    dat_path = NOINTRO_DIR / platform.nointro_dat_filename
    if not dat_path.exists():
        print(
            f"[no-intro] DAT not found at {dat_path.relative_to(NOINTRO_DIR.parent.parent)}.\n"
            f"          Download from https://datomatic.no-intro.org/ "
            f"(System → 'Nintendo - Nintendo Entertainment System (Headered) "
            f"(Parent-Clone)') and save to that path. Skipping No-Intro "
            f"validation for this run."
        )
        return {}

    print(f"[no-intro] Parsing {dat_path.name}")
    tree = ET.parse(dat_path)
    root = tree.getroot()

    games: dict[str, dict[str, Any]] = {}
    skipped_excluded = 0
    skipped_non_western = 0

    for game in root.iter("game"):
        raw_name = game.get("name") or ""
        if not raw_name:
            continue

        tags = [t.strip().lower() for t in _REGION_GROUP.findall(raw_name)]
        if any(t in _EXCLUDE_TAGS or any(x in t for x in _EXCLUDE_TAGS) for t in tags):
            skipped_excluded += 1
            continue
        # Unlicensed retail releases stay in the pool; record the flag.
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

        is_western = region_tag is not None and any(
            w in region_tag for w in ("usa", "europe", "world", "australia")
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
                # `True` only if every variant we've seen is unlicensed; once
                # we see a licensed variant we flip back to False (e.g. an
                # unlicensed re-release of a licensed game).
                "is_unlicensed": True,
            }
        games[key]["regions"].add(region_tag or "unknown")
        games[key]["raw_names"].append(raw_name)
        if not is_unlicensed:
            games[key]["is_unlicensed"] = False

        if region_tag is not None and not is_western:
            skipped_non_western += 1  # tracked but not skipped here; tier downstream

    western_only: dict[str, dict[str, Any]] = {}
    for key, record in games.items():
        regions = record["regions"]
        record["regions"] = sorted(regions)
        record["has_western_release"] = any(
            any(w in r for w in ("usa", "europe", "world", "australia"))
            for r in regions
        )
        if record["has_western_release"]:
            western_only[key] = record

    if skipped_excluded:
        print(
            f"[no-intro] Skipped {skipped_excluded} entries tagged "
            f"Proto/Beta/Sample/Demo/Unlicensed."
        )
    print(
        f"[no-intro] Parsed {len(games)} unique titles ({len(western_only)} with a "
        f"Western region tag)."
    )
    return western_only
