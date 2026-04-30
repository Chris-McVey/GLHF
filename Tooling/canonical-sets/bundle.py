"""Bundle assembly + cross-source confidence tiering.

Schema v2 additions over v1:
  - `releaseYear` is now NES-port-specific (precedence: Wikidata-NES-qualified
    → RAWG year → Wikipedia NA year → Wikidata earliest).
  - `wikidataReleaseYear` preserves the Wikidata earliest for audit.
  - `validation` block per game with per-source presence + confidence tier.
  - Top-level `sourceCounts` summary + `sources` provenance list.
"""
from __future__ import annotations

import dataclasses
import time
from typing import Any, Literal

from rapidfuzz import fuzz, process

from config import PlatformConfig, WESTERN_REGION_TOKENS

BUNDLE_VERSION_FORMAT = "%Y%m%d"

ConfidenceTier = Literal["authoritative", "likely", "review"]

# Cross-reference fuzzy threshold. Below this we treat the source as
# disagreeing. 88 catches title-format drift (`Stack-Up` vs `Stack Up`,
# punctuation differences) without admitting genuinely different games.
XREF_FUZZY_THRESHOLD = 88


def is_western(
    candidate: dict[str, Any],
    wp: dict[str, Any] | None,
    ni: dict[str, Any] | None,
    platform: PlatformConfig,
) -> bool:
    """Multi-source vote for Western inclusion.

    For non-Western platforms (e.g. Famicom), pass through. For Western
    platforms, accept if ANY of:
      - Wikipedia lists a NA or PAL release year, OR
      - No-Intro tags an entry with a Western region (USA/Europe/World), OR
      - Wikidata's per-release P291 qualifiers include a Western region.
    Reject only when there's positive evidence of JP-only release.
    """
    if platform.region.lower() not in {"western", "us", "na"}:
        return True

    if wp and wp.get("has_western_release"):
        return True
    if ni and ni.get("has_western_release"):
        return True

    wd_regions = candidate.get("regions") or []
    if wd_regions:
        if any(r.lower() in WESTERN_REGION_TOKENS for r in wd_regions):
            return True
        # Wikidata says JP-only; Wikipedia/No-Intro didn't override.
        # If Wikipedia explicitly knows about this game and confirms JP-only,
        # that's strong evidence.
        if wp and not wp.get("has_western_release"):
            return False
        # No Wikipedia entry at all + Wikidata regions are non-Western:
        # most likely a Famicom-only game Wikidata mistagged.
        return False

    # No Wikidata regions, no Wikipedia, no No-Intro: insufficient evidence.
    # Default to drop — these are typically prototypes or never-released
    # entries that survived the SPARQL filter via a stray P400 tag.
    if not wp and not ni:
        return False

    # No Wikidata regions but a source mentioned the game (above checks
    # didn't catch it): fall back to a conservative keep.
    return True


@dataclasses.dataclass
class Validation:
    in_wikidata: bool = True            # primary by definition
    in_wikipedia: bool = False
    in_no_intro: bool = False

    @property
    def source_count(self) -> int:
        return sum([self.in_wikidata, self.in_wikipedia, self.in_no_intro])

    @property
    def confidence_tier(self) -> ConfidenceTier:
        n = self.source_count
        if n >= 3:
            return "authoritative"
        if n == 2:
            return "likely"
        return "review"


def _fuzzy_lookup(
    key: str,
    index: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any] | None, str | None]:
    """Exact-key first; on miss, rapidfuzz against all keys above the threshold.

    Returns (record, matched_key) so callers can track which entries were
    consumed (for gap analysis).
    """
    if hit := index.get(key):
        return hit, key
    if not index:
        return None, None
    match = process.extractOne(
        key,
        index.keys(),
        scorer=fuzz.WRatio,
        score_cutoff=XREF_FUZZY_THRESHOLD,
    )
    if match is None:
        return None, None
    matched_key = match[0]
    return index.get(matched_key), matched_key


def cross_reference(
    candidate: dict[str, Any],
    wikipedia_index: dict[str, dict[str, Any]],
    nointro_index: dict[str, dict[str, Any]],
) -> tuple[Validation, dict[str, Any] | None, dict[str, Any] | None,
           str | None, str | None]:
    """Walk Wikipedia + No-Intro using the candidate's normalized title.

    Exact key match first; on miss, rapidfuzz match >= XREF_FUZZY_THRESHOLD.
    The fuzzy fallback catches the long tail of title-format drift between
    sources (`Stack-Up` vs `Stack Up`, `Q*bert` vs `Q-bert`, NA vs JP names).
    Returns (validation, wp_record, ni_record, wp_matched_key, ni_matched_key).
    """
    from matching import normalize

    key = normalize(candidate["name"])
    wp, wp_key = _fuzzy_lookup(key, wikipedia_index)
    ni, ni_key = _fuzzy_lookup(key, nointro_index)
    return (
        Validation(
            in_wikipedia=wp is not None,
            in_no_intro=ni is not None,
        ),
        wp,
        ni,
        wp_key,
        ni_key,
    )


def resolve_release_year(
    candidate: dict[str, Any],
    rawg_match: dict[str, Any],
    wikipedia_record: dict[str, Any] | None,
) -> tuple[int | None, str]:
    """Pick the most Western-specific release year available.

    Precedence (Wikipedia first because it's per-region editorially curated;
    Wikidata's `pq:P400 wd:Q172742` qualifier conflates Famicom and NES, so
    it's only useful as a last-resort sort key):

      1. Wikipedia's NA release year
      2. Wikipedia's EU release year
      3. RAWG's `released` for the matched platform-scoped game
      4. Wikidata's P577 with P400 qualifier (Famicom-conflated, last resort)
      5. Wikidata's earliest unqualified P577

    Returns (year, source_label).
    """
    if wikipedia_record:
        if y := wikipedia_record.get("na_year"):
            return y, "wikipedia-na"
        if y := wikipedia_record.get("eu_year"):
            return y, "wikipedia-eu"
    if rawg_match.get("status") == "matched" and (y := rawg_match.get("rawg_year")):
        return y, "rawg"
    if y := candidate.get("release_year_wikidata_platform"):
        return y, "wikidata-platform-qualified"
    if y := candidate.get("release_year_wikidata_earliest"):
        return y, "wikidata-earliest"
    return None, "none"


def build(
    platform: PlatformConfig,
    enriched: list[dict[str, Any]],
    *,
    include_review_tier: bool = False,
) -> dict[str, Any]:
    """Assemble the output bundle.

    `enriched` is a list of dicts produced by the orchestrator, each carrying
    `wikidata`, `rawg_match`, `wikipedia`, `nointro`, `validation`,
    `release_year`, `release_year_source`.

    By default, only `authoritative` and `likely` games ship in the bundle;
    `review` tier goes to the editorial report only. Pass
    `include_review_tier=True` to surface them in the JSON.
    """
    version = time.strftime(BUNDLE_VERSION_FORMAT)

    games_payload: list[dict[str, Any]] = []
    counts = {"authoritative": 0, "likely": 0, "review": 0}
    override_count = 0
    for entry in enriched:
        validation: Validation = entry["validation"]
        counts[validation.confidence_tier] += 1
        override_reason = entry.get("override_reason")
        # Override-included games bypass the default tier filter, so an
        # editorial decision to ship a 1-source-only game survives without
        # needing --include-review-tier on every run.
        if (
            not include_review_tier
            and validation.confidence_tier == "review"
            and not override_reason
        ):
            continue
        if override_reason:
            override_count += 1

        wd = entry["wikidata"]
        rawg_match = entry["rawg_match"]
        license_status, license_source = _resolve_license_status(entry)
        games_payload.append({
            "name": wd["name"],
            "releaseYear": entry["release_year"],
            "releaseYearSource": entry["release_year_source"],
            "wikidataReleaseYear": wd.get("release_year_wikidata_earliest"),
            "publishers": wd.get("publishers", []),
            "developers": wd.get("developers", []),
            "regions": wd.get("regions", []),
            "licenseStatus": license_status,
            "licenseSource": license_source,
            "rawgID": rawg_match.get("rawg_id"),
            "rawgName": rawg_match.get("rawg_name"),
            "wikidataQID": wd["wikidata_qid"],
            "mobygamesID": wd.get("mobygames_id"),
            "igdbID": wd.get("igdb_id"),
            "matchStatus": rawg_match.get("status"),
            "matchHighConfidence": rawg_match.get("high_confidence", False),
            "overrideReason": override_reason,
            "validation": {
                "inWikidata": validation.in_wikidata,
                "inWikipedia": validation.in_wikipedia,
                "inNoIntro": validation.in_no_intro,
                "sourceCount": validation.source_count,
                "confidenceTier": validation.confidence_tier,
            },
        })

    license_counts = {"licensed": 0, "unlicensed": 0, "unknown": 0}
    for g in games_payload:
        license_counts[g["licenseStatus"]] += 1

    return {
        "id": f"{platform.slug}-{version}",
        "displayName": f"Complete {platform.display_name} Library",
        "platformName": platform.display_name,
        "platformSlug": platform.slug,
        "region": platform.region,
        "version": version,
        "schemaVersion": 3,
        "sources": ["wikidata", "wikipedia", "no-intro", "rawg"],
        "sourceCounts": counts,
        "licenseCounts": license_counts,
        "overrideCount": override_count,
        "gameCount": len(games_payload),
        "matchedGameCount": sum(1 for g in games_payload if g["rawgID"] is not None),
        "games": games_payload,
    }


# License-status precedence: editorial override > Wikipedia subtable >
# No-Intro `(Unl)` tag > unknown. Wikipedia is preferred over No-Intro
# because a Tengen game might be missing from No-Intro's `(Unl)` filter
# (some Tengen carts are tagged USA without the unlicensed marker) but
# Wikipedia editors reliably curate them in the "Unlicensed games"
# subtable. Editorial overrides win because the auto-detection has
# false positives (e.g. modern licensed re-releases of unlicensed games).
def _resolve_license_status(entry: dict[str, Any]) -> tuple[str, str]:
    """Return (status, source) where status is 'licensed' / 'unlicensed' / 'unknown'."""
    if (override := entry.get("license_override")) is not None:
        return ("licensed" if override else "unlicensed"), "override"
    wp = entry.get("wikipedia")
    if wp is not None and "is_licensed" in wp:
        return ("licensed" if wp["is_licensed"] else "unlicensed"), "wikipedia"
    ni = entry.get("nointro")
    if ni is not None and "is_unlicensed" in ni:
        return ("unlicensed" if ni["is_unlicensed"] else "licensed"), "no-intro"
    return "unknown", "none"
