#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Compare bundle before/after No-Intro validation and summarize gaps."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from config import PLATFORMS
from matching import normalize
from sources import nointro


def main() -> int:
    before_path = SCRIPT_DIR / "output" / "nes-before-nointro.json"
    after_path = SCRIPT_DIR / "output" / "nes.json"
    report_path = SCRIPT_DIR / "output" / "review" / "nes-nointro-impact.md"

    if not after_path.exists():
        print("Missing output/nes.json — run curate.py first.", file=sys.stderr)
        return 1

    after = json.loads(after_path.read_text())
    before = json.loads(before_path.read_text()) if before_path.exists() else None

    platform = PLATFORMS["nes"]
    ni_index = nointro.load(platform)

    after_by_qid = {g["wikidataQID"]: g for g in after["games"]}
    before_by_qid = {g["wikidataQID"]: g for g in before["games"]} if before else {}

    promoted = []
    demoted_tier = []
    new_in_bundle = []
    removed_from_bundle = []

    if before:
        before_qids = set(before_by_qid)
        after_qids = set(after_by_qid)
        new_in_bundle = sorted(after_qids - before_qids)
        removed_from_bundle = sorted(before_qids - after_qids)
        for qid in before_qids & after_qids:
            bt = before_by_qid[qid]["validation"]["confidenceTier"]
            at = after_by_qid[qid]["validation"]["confidenceTier"]
            if bt != "authoritative" and at == "authoritative":
                promoted.append(after_by_qid[qid])
            if bt == "authoritative" and at != "authoritative":
                demoted_tier.append((before_by_qid[qid], after_by_qid[qid]))

    in_bundle_no_ni = [
        g for g in after["games"]
        if not g["validation"]["inNoIntro"]
    ]
    ni_only_western = []
    bundle_keys = {normalize(g["name"]) for g in after["games"]}
    for key, rec in ni_index.items():
        if key not in bundle_keys:
            ni_only_western.append(rec)

    lines: list[str] = [
        "# No-Intro impact report — NES Western canonical set",
        "",
        f"**After bundle:** `{after['id']}` — {after['gameCount']} games, "
        f"{after['matchedGameCount']} with RAWG IDs",
        "",
        f"**Source counts:** {after.get('sourceCounts', {})}",
        "",
    ]
    if before:
        lines.extend([
            f"**Before bundle:** `{before['id']}` — {before['gameCount']} games",
            "",
            "## Bundle delta (before → after No-Intro)",
            "",
            f"- Games added: **{len(new_in_bundle)}**",
            f"- Games removed: **{len(removed_from_bundle)}**",
            f"- Promoted to authoritative (2/3 → 3/3): **{len(promoted)}**",
            "",
        ])
        if new_in_bundle[:30]:
            lines.append("### Added (sample)")
            lines.append("")
            for qid in new_in_bundle[:30]:
                g = after_by_qid[qid]
                lines.append(f"- {g['name']} (`{qid}`)")
            if len(new_in_bundle) > 30:
                lines.append(f"- … and {len(new_in_bundle) - 30} more")
            lines.append("")
        if removed_from_bundle[:30]:
            lines.append("### Removed (sample)")
            lines.append("")
            for qid in removed_from_bundle[:30]:
                g = before_by_qid[qid]
                lines.append(f"- {g['name']} (`{qid}`)")
            if len(removed_from_bundle) > 30:
                lines.append(f"- … and {len(removed_from_bundle) - 30} more")
            lines.append("")

    lines.extend([
        "## In bundle but not matched to No-Intro",
        "",
        f"**{len(in_bundle_no_ni)}** games ship in the bundle with `inNoIntro: false`. "
        "These rely on Wikidata + Wikipedia only (2/3 tier). Worth spot-checking.",
        "",
    ])
    if in_bundle_no_ni[:40]:
        lines.append("| Title | Tier | Wikipedia | QID |")
        lines.append("|---|---|---|---|")
        for g in in_bundle_no_ni[:40]:
            v = g["validation"]
            lines.append(
                f"| {g['name']} | {v['confidenceTier']} | "
                f"{'yes' if v['inWikipedia'] else 'no'} | {g['wikidataQID']} |"
            )
        if len(in_bundle_no_ni) > 40:
            lines.append(f"| … | | | {len(in_bundle_no_ni) - 40} more |")
        lines.append("")

    lines.extend([
        "## No-Intro Western titles not in bundle",
        "",
        f"**{len(ni_only_western)}** unique Western-tagged No-Intro titles did not "
        "match any bundled game. See `nes-review.md` § No-Intro gap analysis for the "
        "full list — candidates for `[include]` or `[[supplement]]`.",
        "",
    ])
    if ni_only_western[:40]:
        lines.append("| No-Intro title | Regions |")
        lines.append("|---|---|")
        for rec in ni_only_western[:40]:
            lines.append(f"| {rec['title']} | {', '.join(rec.get('regions', []))} |")
        if len(ni_only_western) > 40:
            lines.append(f"| … | {len(ni_only_western) - 40} more |")
        lines.append("")

    auth = sum(1 for g in after["games"] if g["validation"]["confidenceTier"] == "authoritative")
    likely = sum(1 for g in after["games"] if g["validation"]["confidenceTier"] == "likely")
    lines.extend([
        "## Tier breakdown (in bundle)",
        "",
        f"- **authoritative** (3/3): {auth}",
        f"- **likely** (2/3): {likely}",
        "",
        f"No-Intro index: **{len(ni_index)}** Western unique titles parsed from DAT.",
        "",
    ])

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines))
    print(f"Wrote {report_path.relative_to(SCRIPT_DIR.parent)}")
    print(f"  authoritative: {auth}, likely: {likely}, in bundle without NI: {len(in_bundle_no_ni)}")
    print(f"  NI Western not in bundle: {len(ni_only_western)}")
    if before:
        print(f"  bundle delta: +{len(new_in_bundle)} -{len(removed_from_bundle)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
