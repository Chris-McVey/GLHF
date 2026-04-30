"""Editorial review report generation.

Sections:
  1. Match summary (RAWG match rate, source-tier breakdown).
  2. Source disagreements — every game where the three sources don't agree.
  3. Wikipedia gaps — titles in Wikipedia not present in Wikidata candidates.
  4. No-Intro gaps — titles in No-Intro not present in Wikidata candidates.
  5. Region-filter casualties — games dropped because regions array contained
     no Western region (these are the Famicom-mistagging suspects).
  6. RAWG-resolution issues — fuzzy-match failures, low-confidence + spot-check.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from config import PlatformConfig, REVIEW_DIR
from sources.rawg import HIGH_CONFIDENCE_THRESHOLD, NAME_MATCH_THRESHOLD


def write_report(
    platform: PlatformConfig,
    enriched: list[dict[str, Any]],
    region_drops: list[dict[str, Any]],
    wikipedia_index: dict[str, dict[str, Any]],
    nointro_index: dict[str, dict[str, Any]],
    bundle: dict[str, Any],
    *,
    matched_wp_keys: set[str] | None = None,
    matched_ni_keys: set[str] | None = None,
    applied_overrides: list[dict[str, Any]] | None = None,
) -> Path:
    matched_wp_keys = matched_wp_keys or set()
    matched_ni_keys = matched_ni_keys or set()
    applied_overrides = applied_overrides or []
    out_path = REVIEW_DIR / f"{platform.slug}-review.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = len(enriched)
    rawg_matched = sum(1 for e in enriched if e["rawg_match"].get("status") == "matched")
    rawg_high = sum(1 for e in enriched if e["rawg_match"].get("high_confidence"))
    rawg_low = sum(1 for e in enriched if e["rawg_match"].get("status") == "low_confidence")
    rawg_none = sum(1 for e in enriched if e["rawg_match"].get("status") == "no_results")
    rawg_err = sum(1 for e in enriched if e["rawg_match"].get("status") == "rawg_error")
    counts = bundle["sourceCounts"]

    lines: list[str] = []
    lines.append(f"# Editorial Review — {platform.display_name} ({platform.region})")
    lines.append("")
    lines.append(f"_Generated {time.strftime('%Y-%m-%d %H:%M:%S')} from `curate.py`._")
    lines.append("")

    lines.append("## Match summary")
    lines.append("")
    lines.append(f"- Wikidata candidates (post region-filter): **{total}**")
    if total:
        lines.append(f"- Auto-matched to RAWG: **{rawg_matched}** ({rawg_matched/total:.0%})")
    lines.append(f"- High-confidence RAWG (\u2265{HIGH_CONFIDENCE_THRESHOLD}): **{rawg_high}**")
    lines.append(f"- Low-confidence RAWG (<{NAME_MATCH_THRESHOLD} or year mismatch): **{rawg_low}**")
    lines.append(f"- No RAWG results at all: **{rawg_none}**")
    if rawg_err:
        lines.append(f"- RAWG errors: **{rawg_err}**")
    lines.append("")

    lines.append("## Source-tier summary")
    lines.append("")
    lines.append(f"- Authoritative (3/3 sources): **{counts['authoritative']}** \u2014 ship in bundle")
    lines.append(f"- Likely (2/3 sources): **{counts['likely']}** \u2014 ship in bundle, spot-check below")
    lines.append(f"- Review (1/3 sources): **{counts['review']}** \u2014 held back from bundle")
    lines.append(f"- Region-vote drops (no Western evidence): **{len(region_drops)}** \u2014 see below")
    lines.append("")

    lines.append("## Bundle metadata")
    lines.append("")
    lines.append(f"- Bundle ID: `{bundle['id']}`")
    lines.append(f"- Schema version: **{bundle['schemaVersion']}**")
    lines.append(f"- Game count (in bundle): **{bundle['gameCount']}**")
    lines.append(f"- RAWG IDs resolved: **{bundle['matchedGameCount']}**")
    lines.append(f"- Editorial overrides applied: **{bundle.get('overrideCount', 0)}**")
    if license_counts := bundle.get("licenseCounts"):
        lines.append(
            f"- License status: **{license_counts['licensed']}** licensed, "
            f"**{license_counts['unlicensed']}** unlicensed, "
            f"**{license_counts['unknown']}** unknown"
        )
    lines.append("")

    # Surface the unlicensed roster — collectors care about this and we
    # want a quick eyeball on whether auto-detection is doing the right
    # thing (e.g. did Tengen Tetris get tagged correctly?).
    unlicensed_games = [
        g for g in bundle.get("games", []) if g.get("licenseStatus") == "unlicensed"
    ]
    if unlicensed_games:
        lines.append(f"## Unlicensed games \u2014 {len(unlicensed_games)} entries")
        lines.append("")
        lines.append(
            "Games whose license status was detected as 'unlicensed' "
            "(via Wikipedia subtable placement, No-Intro `(Unl)` tag, or "
            "an editorial `[license]` override). Spot-check for false "
            "positives \u2014 add to `[license]` overrides as `\"licensed\"` "
            "if wrong."
        )
        lines.append("")
        lines.append("| Title | Year | Publishers | Source | QID |")
        lines.append("|---|---|---|---|---|")
        for g in sorted(unlicensed_games, key=lambda x: (x.get("releaseYear") or 9999, x["name"])):
            qid = g["wikidataQID"]
            qid_link = (
                f"[{qid}](https://www.wikidata.org/wiki/{qid})"
                if not qid.startswith("override-") else f"`{qid}`"
            )
            pubs = ", ".join(g.get("publishers", [])[:2]) or "\u2014"
            lines.append(
                f"| {g['name']} | {g.get('releaseYear') or '\u2014'} "
                f"| {pubs} | {g.get('licenseSource', 'unknown')} | {qid_link} |"
            )
        lines.append("")

    if applied_overrides:
        lines.append(f"## Overrides applied \u2014 {len(applied_overrides)} entries")
        lines.append("")
        lines.append(
            f"Editorial decisions sourced from `overrides/{platform.slug}.toml`. "
            "Edit that file to add, remove, or change overrides; re-run the "
            "pipeline to apply."
        )
        lines.append("")
        lines.append("| QID | Title | Changes |")
        lines.append("|---|---|---|")
        for ov in applied_overrides:
            applied_str = "; ".join(s for s in ov["applied"] if s)
            qid_link = ov["qid"]
            if qid_link.startswith("Q") and qid_link[1:].isdigit():
                qid_link = f"[{qid_link}](https://www.wikidata.org/wiki/{qid_link})"
            lines.append(f"| {qid_link} | {ov['name']} | {applied_str} |")
        lines.append("")

    review_tier = [e for e in enriched if e["validation"].confidence_tier == "review"]
    likely_tier = [e for e in enriched if e["validation"].confidence_tier == "likely"]

    if review_tier:
        lines.append(f"## Review tier \u2014 only Wikidata vouches for these ({len(review_tier)} entries)")
        lines.append("")
        lines.append(
            "Held back from the bundle by default. Either accept (manually whitelist) "
            "or remove from the canonical set. Common reasons: legitimate JP-leaning "
            "Western releases Wikipedia missed, prototypes Wikidata mistakenly tagged "
            "as released, or genuinely Famicom-only games whose Wikidata regions "
            "field is empty."
        )
        lines.append("")
        lines.append("| QID | Title | Year | Regions | RAWG match? |")
        lines.append("|---|---|---|---|---|")
        for e in review_tier[:200]:
            wd = e["wikidata"]
            regions = ", ".join(wd.get("regions", [])) or "\u2014"
            rawg = e["rawg_match"]
            rawg_summary = (
                rawg.get("rawg_name") if rawg.get("status") == "matched"
                else rawg.get("status", "\u2014")
            )
            lines.append(
                f"| `{wd['wikidata_qid']}` "
                f"| {wd['name']} "
                f"| {wd.get('release_year_wikidata_platform') or wd.get('release_year_wikidata_earliest') or '\u2014'} "
                f"| {regions} "
                f"| {rawg_summary} |"
            )
        if len(review_tier) > 200:
            lines.append(f"| \u2026 and {len(review_tier) - 200} more \u2026 | | | | |")
        lines.append("")

    if likely_tier:
        lines.append(f"## Likely tier \u2014 2/3 sources agree ({len(likely_tier)} entries)")
        lines.append("")
        lines.append(
            "These ship in the bundle. Eyeball the ones missing from a primary "
            "source (often a name-spelling discrepancy that breaks normalization)."
        )
        lines.append("")
        lines.append("| Title | Year | In Wikipedia? | In No-Intro? | RAWG ID |")
        lines.append("|---|---|---|---|---|")
        for e in likely_tier[:200]:
            wd = e["wikidata"]
            v = e["validation"]
            rawg_id = e["rawg_match"].get("rawg_id") or "\u2014"
            lines.append(
                f"| {wd['name']} "
                f"| {e['release_year'] or '\u2014'} "
                f"| {'\u2713' if v.in_wikipedia else '\u2717'} "
                f"| {'\u2713' if v.in_no_intro else '\u2717'} "
                f"| {rawg_id} |"
            )
        if len(likely_tier) > 200:
            lines.append(f"| \u2026 and {len(likely_tier) - 200} more \u2026 | | | | |")
        lines.append("")

    wp_gaps = [
        rec for key, rec in wikipedia_index.items()
        if key not in matched_wp_keys and rec.get("has_western_release")
    ]
    if wp_gaps:
        lines.append(f"## Wikipedia gap analysis \u2014 {len(wp_gaps)} titles missing from Wikidata")
        lines.append("")
        lines.append(
            "Titles Wikipedia lists with a NA or PAL release date that didn't match "
            "any Wikidata candidate. Manual call: add to bundle as overrides, or "
            "accept the gap."
        )
        lines.append("")
        lines.append("| Wikipedia Title | NA Year | PAL Year | Publisher |")
        lines.append("|---|---|---|---|")
        for rec in wp_gaps[:200]:
            lines.append(
                f"| {rec['title']} "
                f"| {rec.get('na_year') or '\u2014'} "
                f"| {rec.get('eu_year') or '\u2014'} "
                f"| {rec.get('publisher') or '\u2014'} |"
            )
        if len(wp_gaps) > 200:
            lines.append(f"| \u2026 and {len(wp_gaps) - 200} more \u2026 | | | |")
        lines.append("")

    ni_gaps = [
        rec for key, rec in nointro_index.items()
        if key not in matched_ni_keys
    ]
    if ni_gaps:
        lines.append(f"## No-Intro gap analysis \u2014 {len(ni_gaps)} titles missing from Wikidata")
        lines.append("")
        lines.append(
            "Titles the No-Intro DAT lists in a Western region tag that didn't match "
            "any Wikidata candidate. Manual call as above."
        )
        lines.append("")
        lines.append("| No-Intro Title | Regions |")
        lines.append("|---|---|")
        for rec in ni_gaps[:200]:
            lines.append(f"| {rec['title']} | {', '.join(rec.get('regions', []))} |")
        if len(ni_gaps) > 200:
            lines.append(f"| \u2026 and {len(ni_gaps) - 200} more \u2026 | |")
        lines.append("")

    if region_drops:
        lines.append(f"## Region-vote drops \u2014 {len(region_drops)} entries dropped")
        lines.append("")
        lines.append(
            "Multi-source vote concluded these are not Western releases. None of "
            "Wikidata regions, Wikipedia NA/PAL columns, or No-Intro region tags "
            "supplied positive evidence of a Western release. Mostly Famicom-only "
            "games whose only NES tagging in Wikidata is a stray P400 qualifier. "
            "Spot-check that none are false positives."
        )
        lines.append("")
        lines.append("| QID | Title | Year | Regions |")
        lines.append("|---|---|---|---|")
        for wd in region_drops[:200]:
            regions = ", ".join(wd.get("regions", [])) or "\u2014"
            lines.append(
                f"| `{wd['wikidata_qid']}` "
                f"| {wd['name']} "
                f"| {wd.get('release_year_wikidata_platform') or wd.get('release_year_wikidata_earliest') or '\u2014'} "
                f"| {regions} |"
            )
        if len(region_drops) > 200:
            lines.append(f"| \u2026 and {len(region_drops) - 200} more \u2026 | | | |")
        lines.append("")

    rawg_problems = [
        e for e in enriched
        if e["rawg_match"].get("status") in ("low_confidence", "no_results", "rawg_error")
    ]
    if rawg_problems:
        lines.append(f"## RAWG resolution issues \u2014 {len(rawg_problems)} entries")
        lines.append("")
        lines.append(
            "These cleared the source-tier check but couldn't be auto-resolved to "
            "a stable RAWG ID. The bundle entry has `rawgID: null`; cover-art "
            "and detail fetches will fall back to a runtime search until manually "
            "fixed up."
        )
        lines.append("")
        lines.append("| Title | Year | Status | Best RAWG candidate | Score |")
        lines.append("|---|---|---|---|---|")
        for e in rawg_problems[:200]:
            wd = e["wikidata"]
            m = e["rawg_match"]
            cands = m.get("candidates") or []
            best = cands[0] if cands else {}
            lines.append(
                f"| {wd['name']} "
                f"| {e['release_year'] or '\u2014'} "
                f"| {m.get('status')} "
                f"| {best.get('name', '\u2014')} "
                f"| {m.get('name_score', '\u2014')} |"
            )
        if len(rawg_problems) > 200:
            lines.append(f"| \u2026 and {len(rawg_problems) - 200} more \u2026 | | | | |")
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append(
        "- Western-vote policy: a candidate ships if Wikipedia confirms a "
        "NA/PAL release, OR No-Intro tags it with a Western region, OR "
        "Wikidata's per-release region qualifiers include a Western token. "
        "Only when none of those signals fire is the candidate dropped."
    )
    lines.append(
        "- Release-year precedence: Wikipedia NA \u2192 Wikipedia EU "
        "\u2192 RAWG \u2192 Wikidata-platform-qualified \u2192 Wikidata "
        "earliest. Original Wikidata earliest is preserved in "
        "`wikidataReleaseYear` for audit."
    )
    lines.append(
        "- Bundle excludes the \u201creview\u201d tier by default. Pass "
        "`--include-review-tier` to ship them anyway, or add the QID to "
        f"`overrides/{platform.slug}.toml` `[include]` to ship just that one."
    )
    lines.append(
        f"- Editorial decisions live in `overrides/{platform.slug}.toml`. "
        "See the file header for schema; entries survive pipeline re-runs."
    )
    lines.append("")

    out_path.write_text("\n".join(lines))
    return out_path
