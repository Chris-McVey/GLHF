"""Editorial overrides loaded from `overrides/<slug>.toml`.

The automated pipeline produces a strong default bundle, but every platform
has a long tail of editorial calls: localization renames Wikipedia tracks
under a different name than Wikidata, Wikidata entries that ship in
Western markets despite empty `regions` fields, prototypes that survived
SPARQL on a stray P400 tag, etc.

The overrides file is the single source of truth for those decisions.
Edits land in git, survive pipeline re-runs, and surface in the review
report so the next reviewer can see why a game was force-included or
relabeled.

# Schema (see also `overrides/nes.toml.example`)

```toml
[include]
# Force-include a Wikidata candidate that the Western-vote dropped or that
# only Wikidata vouches for (review tier). Key = Wikidata QID.
"Q123" = "1991 NA Konami release Wikipedia missed"

[exclude]
# Force-drop a candidate that survived the vote. Key = Wikidata QID.
"Q456" = "prototype, never shipped commercially"

[name]
# Override the bundle display name for a candidate. Useful when Wikidata
# uses an alternate-region title (`Galaga: Demons of Death`) but the
# Western-canonical title is something else.
"Q789" = "Galaga"

[year]
# Pin a release year when no source has the right one. Sets
# `releaseYearSource` to `override`.
"Q789" = 1985

[rawg]
# Force a specific RAWG ID even when the auto-match was low-confidence.
# Useful when manual disambiguation found the right RAWG entry.
"Q789" = 24881

[license]
# Override the auto-detected license status (Wikipedia subtable / No-Intro
# `(Unl)` tag). Useful when the auto-detection has the wrong answer:
# e.g. Tengen's NES Tetris is famously unlicensed despite Wikipedia
# sometimes listing it under the licensed table; modern licensed
# re-releases of unlicensed Color Dreams games may need the inverse.
# Accepts true/false or "licensed"/"unlicensed" for readability.
"Q789" = "unlicensed"

[[supplement]]
# Wikipedia-only entries — games confirmed in Wikipedia's NA/PAL columns
# but for which no Wikidata entity exists (or Wikidata's entity is too
# far afield to fuzzy-match). Each supplement gets a synthetic record in
# the bundle and goes through RAWG resolution by name.
slug          = "mike-tysons-punch-out"
name          = "Mike Tyson's Punch-Out!!"
year          = 1987
rawg_id       = 25081           # optional; if absent we fuzzy-match by name.
                                # Set to 0 to FORCE rawgID:null (suppress
                                # auto-match when it produces a known wrong
                                # result, e.g. 'Sesame Street A-B-C' fuzzy-
                                # matching to 'Street Cop').
publishers    = ["Nintendo"]
developers    = ["Nintendo R&D3"]
note          = "Famous renamed sequel; Wikidata's Punch-Out!! is the SNES port"
```

A QID may appear in `[name]`, `[year]`, and `[rawg]` simultaneously. A QID
in `[include]` may also appear in `[name]` / `[year]` / `[rawg]`. A QID
appearing in both `[include]` and `[exclude]` is a hard error.
"""
from __future__ import annotations

import dataclasses
import sys
import tomllib
from pathlib import Path
from typing import Any

from config import OVERRIDES_DIR


@dataclasses.dataclass(frozen=True)
class Supplement:
    slug: str
    name: str
    year: int | None = None
    rawg_id: int | None = None
    skip_rawg: bool = False              # True when rawg_id=0 in TOML; suppress auto-match
    licensed: bool = True                # default; set false for unlicensed supplements
    publishers: tuple[str, ...] = ()
    developers: tuple[str, ...] = ()
    note: str | None = None


@dataclasses.dataclass(frozen=True)
class Overrides:
    include: dict[str, str]            # qid -> reason
    exclude: dict[str, str]            # qid -> reason
    name: dict[str, str]               # qid -> override name
    year: dict[str, int]               # qid -> override year
    rawg: dict[str, int]               # qid -> override RAWG id
    license: dict[str, bool]           # qid -> True (licensed) | False (unlicensed)
    supplements: tuple[Supplement, ...]

    @property
    def is_empty(self) -> bool:
        return not (
            self.include or self.exclude or self.name or self.year or self.rawg
            or self.license or self.supplements
        )

    def summary(self) -> str:
        return (
            f"include={len(self.include)} exclude={len(self.exclude)} "
            f"name={len(self.name)} year={len(self.year)} rawg={len(self.rawg)} "
            f"license={len(self.license)} supplement={len(self.supplements)}"
        )


_EMPTY = Overrides(
    include={}, exclude={}, name={}, year={}, rawg={}, license={}, supplements=(),
)


def _validate_qid(qid: str, *, section: str) -> None:
    if not (qid.startswith("Q") and qid[1:].isdigit()):
        raise ValueError(
            f"[{section}] keys must be Wikidata QIDs like 'Q12345'; got {qid!r}"
        )


def load(slug: str) -> Overrides:
    """Load `overrides/<slug>.toml`. Returns empty Overrides if the file is absent."""
    path = OVERRIDES_DIR / f"{slug}.toml"
    if not path.exists():
        return _EMPTY
    with path.open("rb") as f:
        raw = tomllib.load(f)

    include = {k: str(v) for k, v in raw.get("include", {}).items()}
    exclude = {k: str(v) for k, v in raw.get("exclude", {}).items()}
    name = {k: str(v) for k, v in raw.get("name", {}).items()}
    year_raw = raw.get("year", {})
    year = {k: int(v) for k, v in year_raw.items()}
    rawg_raw = raw.get("rawg", {})
    rawg = {k: int(v) for k, v in rawg_raw.items()}
    license_raw = raw.get("license", {})
    # `[license]` accepts either a bool (true=licensed, false=unlicensed) or
    # the strings "licensed"/"unlicensed" for readability. Validate strictly.
    license_overrides: dict[str, bool] = {}
    for k, v in license_raw.items():
        if isinstance(v, bool):
            license_overrides[k] = v
        elif isinstance(v, str) and v.lower() in {"licensed", "unlicensed"}:
            license_overrides[k] = v.lower() == "licensed"
        else:
            raise ValueError(
                f"[license] {k!r} must be true/false or 'licensed'/'unlicensed'; got {v!r}"
            )
    for section, d in (("include", include), ("exclude", exclude),
                       ("name", name), ("year", year_raw), ("rawg", rawg_raw),
                       ("license", license_raw)):
        for qid in d:
            _validate_qid(qid, section=section)

    overlap = set(include) & set(exclude)
    if overlap:
        raise ValueError(
            f"QIDs cannot appear in both [include] and [exclude]: {sorted(overlap)}"
        )

    supplements: list[Supplement] = []
    seen_slugs: set[str] = set()
    for entry in raw.get("supplement", []):
        if "slug" not in entry or "name" not in entry:
            raise ValueError(
                f"[[supplement]] entries require 'slug' and 'name'; got {entry!r}"
            )
        if entry["slug"] in seen_slugs:
            raise ValueError(
                f"Duplicate supplement slug: {entry['slug']!r}"
            )
        seen_slugs.add(entry["slug"])
        # rawg_id=0 is a sentinel for "force rawgID:null" — useful when the
        # auto-fuzzy-matcher returns a confidently-wrong RAWG entry (e.g.
        # 'Sesame Street A-B-C' fuzzy-matching to 'Street Cop'). Setting
        # rawg_id=0 suppresses the auto-match without forcing a real ID.
        rawg_id_raw = entry.get("rawg_id")
        if rawg_id_raw is None:
            rawg_id = None
            skip_rawg = False
        elif int(rawg_id_raw) == 0:
            rawg_id = None
            skip_rawg = True
        else:
            rawg_id = int(rawg_id_raw)
            skip_rawg = False
        supplements.append(Supplement(
            slug=str(entry["slug"]),
            name=str(entry["name"]),
            year=int(entry["year"]) if "year" in entry else None,
            rawg_id=rawg_id,
            skip_rawg=skip_rawg,
            licensed=bool(entry.get("licensed", True)),
            publishers=tuple(entry.get("publishers", [])),
            developers=tuple(entry.get("developers", [])),
            note=str(entry["note"]) if "note" in entry else None,
        ))

    return Overrides(
        include=include, exclude=exclude,
        name=name, year=year, rawg=rawg, license=license_overrides,
        supplements=tuple(supplements),
    )


def report_unused(
    overrides: Overrides,
    candidate_qids: set[str],
    *,
    out=sys.stderr,
) -> list[str]:
    """Warn about override entries whose QID never matched a Wikidata candidate.

    Returns the list of unused QIDs. Doesn't raise — overrides may
    legitimately persist across pipeline runs even when the underlying
    Wikidata entity has been deleted/merged.
    """
    unused: list[str] = []
    for section_name, section in (
        ("include", overrides.include),
        ("exclude", overrides.exclude),
        ("name", overrides.name),
        ("year", overrides.year),
        ("rawg", overrides.rawg),
        ("license", overrides.license),
    ):
        for qid in section:
            if qid not in candidate_qids:
                unused.append(f"[{section_name}] {qid}")
    if unused:
        print(
            f"[overrides] WARNING: {len(unused)} override entries reference "
            f"QIDs that don't appear in the Wikidata candidate pool. They are "
            f"silently ignored. Inspect:\n  " + "\n  ".join(unused),
            file=out,
        )
    return unused


def example_toml(platform_slug: str, platform_display: str) -> str:
    """Return a `<slug>.toml.example` template body."""
    return f"""# Editorial overrides for the {platform_display} canonical set.
#
# Each section is optional and starts empty. Add entries as you walk
# `output/review/{platform_slug}-review.md`. The pipeline reads this file
# every run; edits survive re-curation. Reasons are required (a string),
# both for your future self and so the review report explains why.

[include]
# Force-include candidates from the Region-vote drops or Review tier.
# QID -> reason
# "Q123456" = "PAL-only Konami release; Wikipedia confirms Sept 1990"

[exclude]
# Force-drop candidates that survived the Western-vote but shouldn't ship.
# QID -> reason
# "Q789012" = "competition cartridge, never sold at retail"

[name]
# Override the bundle display name for a candidate.
# QID -> override name
# "Q345678" = "Galaga"

[year]
# Pin a release year when no source has the right one.
# QID -> year
# "Q345678" = 1985

[rawg]
# Force a specific RAWG ID for low-confidence / no-results matches.
# QID -> RAWG ID
# "Q345678" = 24881

[license]
# Override auto-detected license status when Wikipedia's subtable
# placement or the No-Intro (Unl) tag are wrong.
# QID -> "licensed" | "unlicensed" (or true / false)
# "Q789012" = "unlicensed"

# [[supplement]]
# # Wikipedia-only entries (Wikidata has no entity for them).
# # rawg_id is optional; if absent the pipeline fuzzy-matches by name.
# slug       = "mike-tysons-punch-out"
# name       = "Mike Tyson's Punch-Out!!"
# year       = 1987
# rawg_id    = 25081
# publishers = ["Nintendo"]
# developers = ["Nintendo R&D3"]
# note       = "Wikipedia tracks the original 1987 release; Wikidata's Punch-Out!! is the 1990 SNES port"
"""
