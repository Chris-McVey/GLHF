"""RAWG fuzzy-match resolution.

Preserves the v1 matcher: per-platform `/games?search=` first, fall back to
unscoped `/games?search=` filtered by `platforms[]`, then score each candidate
with rapidfuzz on the normalized title with a year-disagreement penalty,
relaxed when the name match is essentially perfect (arcade-port year mismatch
pitfall — see the linked Athena learning).
"""
from __future__ import annotations

import re
from typing import Any

import requests
from rapidfuzz import fuzz

from cache import cached_json
from config import PlatformConfig, USER_AGENT
from matching import normalize

RAWG_BASE_URL = "https://api.rawg.io/api"

NAME_MATCH_THRESHOLD = 85
YEAR_TOLERANCE = 2
NAME_OVERRIDES_YEAR = 95
HIGH_CONFIDENCE_THRESHOLD = 92


def _search(name: str, platform_id: int | None, api_key: str) -> dict[str, Any]:
    def _fetch() -> dict[str, Any]:
        params = {"search": name, "page_size": "5", "key": api_key}
        if platform_id is not None:
            params["platforms"] = str(platform_id)
        response = requests.get(
            f"{RAWG_BASE_URL}/games",
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    cache_key = f"{platform_id if platform_id is not None else 'any'}::{name}"
    return cached_json("rawg-search", cache_key, _fetch)


def _has_platform(rawg_game: dict[str, Any], platform_id: int) -> bool:
    """Some RAWG entries don't surface in scoped /games?platforms=N searches but
    their detail records do list the platform. Verify explicitly when falling back."""
    platforms = rawg_game.get("platforms") or []
    for wrapper in platforms:
        platform = wrapper.get("platform") or {}
        if platform.get("id") == platform_id:
            return True
    return False


def match(
    candidate: dict[str, Any],
    platform: PlatformConfig,
    api_key: str,
) -> dict[str, Any]:
    """Return a match record with the best RAWG candidate (or None) and confidence."""
    name = candidate["name"]
    wd_year = (
        candidate.get("release_year_wikidata_platform")
        or candidate.get("release_year_wikidata_earliest")
    )

    try:
        results = _search(name, platform.rawg_platform_id, api_key)
    except requests.HTTPError as e:
        return {"status": "rawg_error", "error": str(e), "candidates": []}

    candidates = results.get("results", [])

    fallback_used = False
    if not candidates:
        try:
            broad = _search(name, None, api_key)
        except requests.HTTPError as e:
            return {"status": "rawg_error", "error": str(e), "candidates": []}
        broad_results = broad.get("results", [])
        candidates = [c for c in broad_results if _has_platform(c, platform.rawg_platform_id)]
        fallback_used = True
        if not candidates:
            return {"status": "no_results", "candidates": []}

    norm_query = normalize(name)
    scored: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
    for cand in candidates:
        cand_name = cand.get("name") or ""
        norm_cand = normalize(cand_name)
        name_score = fuzz.WRatio(norm_query, norm_cand)
        cand_year = None
        if released := cand.get("released"):
            cand_year = int(released[:4]) if re.match(r"^\d{4}", released) else None
        year_diff = abs((wd_year or 0) - (cand_year or 0)) if (wd_year and cand_year) else None
        year_penalty = 0
        if year_diff is not None and year_diff > YEAR_TOLERANCE:
            year_penalty = min(20, (year_diff - YEAR_TOLERANCE) * 5)
        composite = name_score - year_penalty
        scored.append((composite, cand, {
            "name_score": name_score,
            "year_diff": year_diff,
            "year_penalty": year_penalty,
            "cand_year": cand_year,
        }))

    scored.sort(key=lambda t: t[0], reverse=True)
    best_score, best_cand, best_meta = scored[0]

    name_score = best_meta["name_score"]
    year_diff = best_meta["year_diff"]

    if name_score >= NAME_OVERRIDES_YEAR:
        accepted = True
    else:
        accepted = name_score >= NAME_MATCH_THRESHOLD and (
            year_diff is None or year_diff <= YEAR_TOLERANCE
        )
    high_confidence = accepted and name_score >= HIGH_CONFIDENCE_THRESHOLD

    return {
        "status": "matched" if accepted else "low_confidence",
        "high_confidence": high_confidence,
        "fallback_used": fallback_used,
        "rawg_id": best_cand.get("id") if accepted else None,
        "rawg_name": best_cand.get("name"),
        "rawg_released": best_cand.get("released"),
        "rawg_year": best_meta["cand_year"] if accepted else None,
        "name_score": name_score,
        "year_diff": year_diff,
        "candidates": [
            {"id": c.get("id"), "name": c.get("name"), "released": c.get("released")}
            for _, c, _ in scored[:3]
        ],
    }
