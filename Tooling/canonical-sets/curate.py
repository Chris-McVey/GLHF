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
"""
Canonical-Set Curation Pipeline (multi-source v2).

For a target platform:

  1. Pull a candidate list from Wikidata (SPARQL, region-filtered).
  2. Cross-reference against Wikipedia's "List of <platform> games" article.
  3. Cross-reference against the No-Intro DAT for the platform.
  4. Resolve a stable RAWG ID for each surviving candidate.
  5. Tier each entry by source agreement (authoritative/likely/review).
  6. Write a JSON bundle (default: tier in {authoritative, likely}) and a
     markdown editorial review report.

Outputs:
  output/<slug>.json              - Bundle file (the deliverable)
  output/review/<slug>-review.md  - Editorial review report

Run:
  RAWG_API_KEY=... uv run curate.py --platform nes

Idempotent: caches Wikidata + Wikipedia + RAWG responses under .cache/. The
No-Intro DAT must be supplied manually (see README) at
data/no-intro/<filename>.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

import overrides as overrides_mod
from bundle import Validation, build, cross_reference, is_western, resolve_release_year
from config import OUTPUT_DIR, REVIEW_DIR, SCRIPT_DIR, PLATFORMS
from review import write_report
from sources import nointro, rawg, wikidata, wikipedia

# The Swift app stores the RAWG key in GLHF/Services/Secrets.swift (gitignored).
# Reuse it so the curator doesn't need a separate env var on this machine.
_SECRETS_SWIFT_PATH = SCRIPT_DIR.parent.parent / "GLHF" / "Services" / "Secrets.swift"
_SECRETS_RAWG_KEY_RE = re.compile(r'rawgAPIKey\s*=\s*"([^"]+)"')


def _load_rawg_api_key() -> str | None:
    """Resolve the RAWG API key from env var first, Secrets.swift fallback."""
    if env := os.environ.get("RAWG_API_KEY"):
        return env
    if not _SECRETS_SWIFT_PATH.exists():
        return None
    text = _SECRETS_SWIFT_PATH.read_text(encoding="utf-8")
    if m := _SECRETS_RAWG_KEY_RE.search(text):
        return m.group(1)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Curate canonical platform-library bundles for GLHF.",
    )
    parser.add_argument(
        "--platform",
        choices=sorted(PLATFORMS.keys()),
        default="nes",
        help="Which platform to curate.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on Wikidata entries (smoke testing).",
    )
    parser.add_argument(
        "--include-review-tier",
        action="store_true",
        help="Include 1-source-only games in the bundle (default: review-only).",
    )
    parser.add_argument(
        "--skip-rawg",
        action="store_true",
        help="Skip the RAWG fuzzy-match step. Useful for fast iteration on the "
             "Wikidata/Wikipedia/No-Intro pipeline; produces a bundle with all "
             "rawgID fields null.",
    )
    args = parser.parse_args()

    platform = PLATFORMS[args.platform]
    api_key = None if args.skip_rawg else _load_rawg_api_key()
    if not api_key and not args.skip_rawg:
        print(
            f"ERROR: no RAWG API key found.\n"
            f"  Set $RAWG_API_KEY, or add `static let rawgAPIKey = \"...\"` to "
            f"{_SECRETS_SWIFT_PATH.relative_to(SCRIPT_DIR.parent.parent)}, "
            f"or pass --skip-rawg.",
            file=sys.stderr,
        )
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[start] Platform: {platform.display_name} ({platform.region})")

    overrides = overrides_mod.load(platform.slug)
    if not overrides.is_empty:
        print(f"[overrides] Loaded {overrides.summary()}")

    bindings = wikidata.fetch(platform)
    candidates = wikidata.coalesce(bindings, platform)

    if args.limit:
        candidates = candidates[: args.limit]
        print(f"[wikidata] Limited to first {len(candidates)} entries for smoke test.")

    overrides_mod.report_unused(
        overrides, candidate_qids={c["wikidata_qid"] for c in candidates},
    )

    wikipedia_index = wikipedia.fetch(platform)
    nointro_index = nointro.load(platform)

    # Phase 1: cross-reference + Western-vote (cheap, no API calls).
    # We compute the Western decision before RAWG so we don't burn quota on
    # Famicom-only games that won't make the bundle. Editorial [include]
    # overrides force a candidate past the vote; [exclude] forces a drop.
    voted: list[dict[str, Any]] = []
    region_drops: list[dict[str, Any]] = []
    matched_wp_keys: set[str] = set()
    matched_ni_keys: set[str] = set()
    for wd in candidates:
        qid = wd["wikidata_qid"]
        # Apply [name] override BEFORE cross-reference so renamed games
        # find their Wikipedia/No-Intro counterparts (e.g. Wikidata
        # 'Salamander' renamed to 'Life Force' matches the Wikipedia
        # 'Life Force' row, closing the spurious gap-analysis entry).
        if name_override := overrides.name.get(qid):
            wd["name"] = name_override
        validation, wp, ni, wp_key, ni_key = cross_reference(
            wd, wikipedia_index, nointro_index,
        )
        if wp_key is not None:
            matched_wp_keys.add(wp_key)
        if ni_key is not None:
            matched_ni_keys.add(ni_key)

        override_reason = None
        if qid in overrides.exclude:
            region_drops.append(wd)
            continue
        if qid in overrides.include:
            override_reason = overrides.include[qid]
        elif not is_western(wd, wp, ni, platform):
            region_drops.append(wd)
            continue
        voted.append({
            "wikidata": wd, "wikipedia": wp, "nointro": ni,
            "validation": validation,
            "override_reason": override_reason,
        })
    print(
        f"[region] Western vote: {len(voted)} kept, {len(region_drops)} dropped as "
        f"non-Western."
    )

    # Phase 2: RAWG resolution + year precedence on the kept set.
    if args.skip_rawg:
        print("[rawg] --skip-rawg: skipping RAWG resolution; rawgID will be null.")
    else:
        print(
            f"[rawg] Resolving RAWG IDs for {len(voted)} kept candidates "
            f"(rate-limited; cached on disk)..."
        )

    enriched: list[dict[str, Any]] = []
    applied_overrides: list[dict[str, Any]] = []  # for review report
    for i, item in enumerate(voted, start=1):
        wd = item["wikidata"]
        wp = item["wikipedia"]
        qid = wd["wikidata_qid"]
        applied: list[str] = []

        if name_override := overrides.name.get(qid):
            applied.append(f"name -> {name_override!r}")

        if args.skip_rawg:
            rawg_match = {"status": "skipped", "high_confidence": False, "candidates": []}
        else:
            rawg_match = rawg.match(wd, platform, api_key)

        if rawg_id_override := overrides.rawg.get(qid):
            rawg_match = {
                **rawg_match,
                "rawg_id": rawg_id_override,
                "status": "override",
                "high_confidence": True,
            }
            applied.append(f"rawg -> {rawg_id_override}")

        year, year_source = resolve_release_year(wd, rawg_match, wp)
        if year_override := overrides.year.get(qid):
            year = year_override
            year_source = "override"
            applied.append(f"year -> {year_override}")

        if item["override_reason"]:
            applied.append(f"include: {item['override_reason']}")

        license_override = overrides.license.get(qid)
        if license_override is not None:
            applied.append(
                f"license -> {'licensed' if license_override else 'unlicensed'}"
            )

        enriched.append({
            "wikidata": wd,
            "wikipedia": wp,
            "nointro": item["nointro"],
            "rawg_match": rawg_match,
            "validation": item["validation"],
            "release_year": year,
            "release_year_source": year_source,
            "override_reason": item["override_reason"],
            "license_override": license_override,
        })
        if applied:
            applied_overrides.append({"qid": qid, "name": wd["name"], "applied": applied})
        if i % 25 == 0 or i == len(voted):
            matched = sum(
                1 for e in enriched if e["rawg_match"].get("status") in {"matched", "override"}
            )
            print(f"[rawg] {i}/{len(voted)} \u2014 matched {matched}")

    # Phase 3: synthesize Wikipedia-supplement entries that have no Wikidata
    # entity but are confirmed Western releases per editorial decision.
    for supp in overrides.supplements:
        synth_wd = {
            "wikidata_qid": f"override-{supp.slug}",
            "wikidata_uri": None,
            "name": supp.name,
            "wikipedia_title": supp.name,
            "mobygames_id": None,
            "igdb_id": None,
            "publishers": list(supp.publishers),
            "developers": list(supp.developers),
            "regions": [],
            "all_release_years": [supp.year] if supp.year else [],
            "release_year_wikidata_earliest": supp.year,
            "release_year_wikidata_platform": None,
        }
        if supp.rawg_id is not None:
            rawg_match = {
                "rawg_id": supp.rawg_id,
                "rawg_name": supp.name,
                "status": "override",
                "high_confidence": True,
                "candidates": [],
            }
        elif supp.skip_rawg:
            rawg_match = {
                "status": "skipped",
                "high_confidence": False,
                "rawg_id": None,
                "candidates": [],
            }
        elif args.skip_rawg:
            rawg_match = {"status": "skipped", "high_confidence": False, "candidates": []}
        else:
            rawg_match = rawg.match(synth_wd, platform, api_key)

        synth_validation = Validation(
            in_wikidata=False, in_wikipedia=True, in_no_intro=False,
        )
        enriched.append({
            "wikidata": synth_wd,
            "wikipedia": None,
            "nointro": None,
            "rawg_match": rawg_match,
            "validation": synth_validation,
            "release_year": supp.year,
            "release_year_source": "override" if supp.year else "none",
            "override_reason": supp.note or "wikipedia supplement",
            "license_override": supp.licensed,
        })
        applied_overrides.append({
            "qid": synth_wd["wikidata_qid"],
            "name": supp.name,
            "applied": [
                "supplement: Wikipedia-only entry",
                f"year -> {supp.year}" if supp.year else None,
                f"rawg -> {supp.rawg_id}" if supp.rawg_id else None,
            ],
        })

    if overrides.supplements:
        print(f"[overrides] Synthesized {len(overrides.supplements)} Wikipedia-supplement entries.")
        from matching import normalize as _norm
        for supp in overrides.supplements:
            wp_key = _norm(supp.name)
            if wp_key in wikipedia_index:
                matched_wp_keys.add(wp_key)

    bundle = build(platform, enriched, include_review_tier=args.include_review_tier)
    bundle_path = OUTPUT_DIR / f"{platform.slug}.json"
    bundle_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n")
    print(f"[output] Bundle written: {bundle_path.relative_to(OUTPUT_DIR.parent)}")

    review_path = write_report(
        platform, enriched, region_drops, wikipedia_index, nointro_index, bundle,
        matched_wp_keys=matched_wp_keys,
        matched_ni_keys=matched_ni_keys,
        applied_overrides=applied_overrides,
    )
    print(f"[output] Review report: {review_path.relative_to(OUTPUT_DIR.parent)}")

    counts = bundle["sourceCounts"]
    total = bundle["gameCount"]
    matched_count = bundle["matchedGameCount"]
    print(
        f"[done] {total} games in bundle "
        f"({counts['authoritative']} authoritative, {counts['likely']} likely, "
        f"{counts['review']} review-tier held back); "
        f"{matched_count} ({matched_count/total:.0%}) "
        f"matched to RAWG IDs."
        if total else "[done] 0 games in bundle."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
