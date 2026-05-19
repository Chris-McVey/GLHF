"""Wikipedia-primary membership for canonical sets.

Builds the candidate list from Wikipedia's platform list article (licensed +
unlicensed retail with a Western release). Wikidata is optional enrichment.
"""
from __future__ import annotations

import re
from typing import Any

from rapidfuzz import fuzz, process

from bundle import _fuzzy_xref_allowed
from config import PlatformConfig
from homebrew import is_homebrew_candidate
from matching import normalize
from sources import wikipedia

_VIDEO_GAME_SUFFIX = re.compile(r"\s*\(video game\)\s*$", re.I)


def western_retail_records(
    wikipedia_index: dict[str, dict[str, Any]],
) -> list[tuple[str, dict[str, Any]]]:
    """Return (normalized_key, record) rows that belong in the canonical set."""
    out: list[tuple[str, dict[str, Any]]] = []
    for key, rec in wikipedia_index.items():
        if not rec.get("has_western_release"):
            continue
        subsection = (rec.get("source_subsection") or "").lower()
        if not rec.get("is_licensed") and "famicom" in subsection:
            continue
        license_status = "licensed" if rec.get("is_licensed") else "unlicensed"
        year = rec.get("na_year") or rec.get("eu_year")
        is_hb, _reason = is_homebrew_candidate(
            nointro_record=None,
            wikipedia_record=rec,
            release_year=year,
            license_status=license_status,
        )
        if is_hb:
            continue
        out.append((key, rec))
    return sorted(out, key=lambda item: item[1]["title"].lower())


def _normalize_wikidata_label(name: str) -> str:
    return normalize(_VIDEO_GAME_SUFFIX.sub("", name))


def attach_wikidata(
    wikipedia_index: dict[str, dict[str, Any]],
    wikidata_candidates: list[dict[str, Any]],
) -> dict[str, dict[str, Any] | None]:
    """Map Wikipedia normalized keys to the best Wikidata coalesced row, if any."""
    wd_keys: list[str] = []
    wd_by_norm: dict[str, dict[str, Any]] = {}
    for wd in wikidata_candidates:
        norm = _normalize_wikidata_label(wd["name"])
        if not norm:
            continue
        wd_keys.append(norm)
        if norm not in wd_by_norm:
            wd_by_norm[norm] = wd

    attached: dict[str, dict[str, Any] | None] = {}
    for wp_key in wikipedia_index:
        if wp_key in wd_by_norm:
            attached[wp_key] = wd_by_norm[wp_key]
            continue
        match = process.extractOne(
            wp_key,
            wd_keys,
            scorer=fuzz.WRatio,
            score_cutoff=88,
        )
        if match is None:
            attached[wp_key] = None
            continue
        matched_norm = match[0]
        if not _fuzzy_xref_allowed(wp_key, matched_norm):
            attached[wp_key] = None
            continue
        attached[wp_key] = wd_by_norm[matched_norm]
    return attached


def record_to_candidate(
    wp_key: str,
    rec: dict[str, Any],
    wikidata_row: dict[str, Any] | None,
) -> dict[str, Any]:
    """Shape a Wikidata-like candidate dict for the shared curate/bundle path."""
    regions: list[str] = []
    if rec.get("na_year"):
        regions.append("North America")
    if rec.get("eu_year"):
        regions.append("Europe")

    publishers: list[str] = []
    if pub := rec.get("publisher"):
        publishers.append(pub)
    developers: list[str] = []
    if dev := rec.get("developer"):
        developers.append(dev)

    if wikidata_row:
        qid = wikidata_row["wikidata_qid"]
        name = rec["title"]
        return {
            **wikidata_row,
            "name": name,
            "wikidata_qid": qid,
            "publishers": wikidata_row.get("publishers") or publishers,
            "developers": wikidata_row.get("developers") or developers,
            "regions": wikidata_row.get("regions") or regions,
            "wikipedia_title": rec["title"],
        }

    return {
        "wikidata_qid": f"wp:{wp_key}",
        "wikidata_uri": None,
        "name": rec["title"],
        "wikipedia_title": rec["title"],
        "mobygames_id": None,
        "igdb_id": None,
        "publishers": publishers,
        "developers": developers,
        "regions": regions,
        "all_release_years": [y for y in (rec.get("na_year"), rec.get("eu_year")) if y],
        "release_year_wikidata_earliest": rec.get("na_year") or rec.get("eu_year"),
        "release_year_wikidata_platform": None,
    }


def build_candidates(
    platform: PlatformConfig,
    wikipedia_index: dict[str, dict[str, Any]],
    wikidata_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Full Wikipedia-primary candidate list with optional Wikidata enrichment."""
    western = western_retail_records(wikipedia_index)
    wd_map = attach_wikidata(wikipedia_index, wikidata_candidates)
    licensed_n = 0
    unlicensed_n = 0
    wd_hit = 0
    candidates: list[dict[str, Any]] = []
    for wp_key, rec in western:
        wd_row = wd_map.get(wp_key)
        if wd_row:
            wd_hit += 1
        candidates.append(record_to_candidate(wp_key, rec, wd_row))
        if rec.get("is_licensed"):
            licensed_n += 1
        else:
            unlicensed_n += 1
    print(
        f"[wikipedia-primary] {len(candidates)} Western retail rows "
        f"({licensed_n} licensed, {unlicensed_n} unlicensed; "
        f"{wd_hit} matched to Wikidata)."
    )
    return candidates
