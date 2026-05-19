"""Detect modern / hobbyist NES homebrew vs unlicensed retail (Tengen, Color Dreams).

Unlicensed retail stays in the canonical set; homebrew is dropped unless
explicitly `[include]`'d in overrides with a documented reason.
"""
from __future__ import annotations

import re
from typing import Any

_REGION_GROUP = re.compile(r"\(([^)]*)\)")

# No-Intro parenthetical tags that indicate hobbyist / post-era releases.
_HOMEBREW_TAGS = frozenset({"homebrew", "aftermarket"})

# Substrings in DAT names that are effectively always homebrew on NES.
_HOMEBREW_NAME_MARKERS = (
    "nesdev",
    "byte-off",
    "greetingcart",
    "8-bit xmas",
    "240p test suite",
)

# Licensed-unlikely: post-NES-era unlicensed releases are almost always homebrew
# carts (Micro Mages, Battle Kid, etc.). Retail unlicensed on NES peaked ~1989-1995.
_HOMEBREW_YEAR_CUTOFF = 2005


def tags_from_raw_name(raw_name: str) -> list[str]:
    return [t.strip().lower() for t in _REGION_GROUP.findall(raw_name)]


def is_homebrew_nointro_raw_name(raw_name: str) -> bool:
    """True when No-Intro tags this ROM row as aftermarket/homebrew."""
    tags = tags_from_raw_name(raw_name)
    if any(
        t in _HOMEBREW_TAGS or any(part in t for part in _HOMEBREW_TAGS)
        for t in tags
    ):
        return True
    lower = raw_name.lower()
    return any(marker in lower for marker in _HOMEBREW_NAME_MARKERS)


def is_homebrew_wikipedia_record(wp: dict[str, Any] | None) -> bool:
    if not wp:
        return False
    subsection = (wp.get("source_subsection") or "").lower()
    section = (wp.get("source_section") or "").lower()
    # Wikipedia hobbyist tables (NES list: "After lifespan" under Unlicensed).
    if "aftermarket" in subsection or "aftermarket" in section:
        return True
    if "homebrew" in subsection or "homebrew" in section:
        return True
    if "after lifespan" in subsection:
        return True
    return False


def is_homebrew_candidate(
    *,
    nointro_record: dict[str, Any] | None,
    wikipedia_record: dict[str, Any] | None,
    release_year: int | None,
    license_status: str | None,
) -> tuple[bool, str]:
    """Return (is_homebrew, reason_label)."""
    if nointro_record and nointro_record.get("is_homebrew"):
        raw = next(
            (
                r
                for r in nointro_record.get("raw_names", [])
                if is_homebrew_nointro_raw_name(r)
            ),
            nointro_record.get("title", ""),
        )
        return True, f"no-intro:{str(raw)[:60]}"

    if nointro_record:
        for raw in nointro_record.get("raw_names", []):
            if is_homebrew_nointro_raw_name(raw):
                return True, f"no-intro:{raw[:60]}"

    if is_homebrew_wikipedia_record(wikipedia_record):
        sub = wikipedia_record.get("source_subsection") or wikipedia_record.get("source_section")
        return True, f"wikipedia:{sub}"

    if (
        release_year is not None
        and release_year >= _HOMEBREW_YEAR_CUTOFF
        and license_status == "unlicensed"
    ):
        return True, f"year>={_HOMEBREW_YEAR_CUTOFF}+unlicensed"

    return False, ""
