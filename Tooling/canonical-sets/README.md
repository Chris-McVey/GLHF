# Canonical-Set Curation

One-off tooling that produces the bundled "Complete Platform Library" JSONs
GLHF ships at runtime. Not part of the iOS app; runs on a developer machine
when a platform's catalog needs (re)building.

The output JSONs are vendored into the app at
`GLHF/Resources/CanonicalSets/<slug>.json` after curation. Generated
artifacts under `output/` stay gitignored here; copy with:

```bash
./export_to_app.sh
# or: cp output/nes.json ../../GLHF/Resources/CanonicalSets/nes.json
```

## What it does (v2 multi-source)

For a target platform (e.g. NES):

1. **Wikidata** — SPARQL primary candidate list across all hardware-family
   Q-ids for the platform. (The NES family is split across `Q172742` (NES
   Western), `Q11288` (Famicom JP), and `Q135321` (Famicom Disk System) —
   contributors apply them inconsistently, so we query all three and let
   the Western-vote step decide region.) Entries with no English label are
   rescued via their English Wikipedia article title.
2. **Wikipedia** — scrapes the platform's "List of games" article as the
   primary region authority. The NA / PAL / JP columns are editorially
   curated per game; presence of a NA or PAL year is the strongest signal
   of a Western release.
3. **No-Intro DAT** — parses the official cartridge-level DAT for the
   platform as a tertiary validator. The DAT must be obtained manually
   (Datomatic gates downloads behind a captcha login) — see "Required
   external data" below.
4. **RAWG** — fuzzy-matches each surviving candidate to a stable RAWG ID so
   the iOS app's existing detail / cover-art code paths keep working.

**Default membership (`--source wikipedia`, see `CANONICAL_POLICY.md`):** every
Wikipedia licensed or unlicensed row with a NA or PAL release year, minus
homebrew. Wikidata and No-Intro enrich only; all rows ship in the bundle.

**Legacy (`--source wikidata`) — region inclusion is a multi-source vote**, not a Wikidata-only filter:
a candidate ships in the bundle if Wikipedia confirms a NA/PAL release, OR
No-Intro tags it with a **retail** Western cartridge (`USA` / `Europe` /
`Australia`, or standalone `(World)` — not Virtual Console / Museum /
Collection bundles), OR Wikidata's per-release region qualifiers include a
Western region. Wikidata **Japan-only** rows drop unless Wikipedia or retail
No-Intro overrides. Fuzzy cross-reference rejects strict prefix extensions
(`Tetris 2 + Bombliss` must not match `Tetris 2`).

**Release year follows a Western-first precedence**: Wikipedia NA → Wikipedia
EU → RAWG → Wikidata-platform-qualified → Wikidata earliest. Wikidata's
`pq:P400 wd:Q172742` qualifier conflates the Famicom and NES because
contributors apply it loosely, so it's only a fallback.

Each candidate ends up tagged with which sources vouch for it, and assigned
a confidence tier:

| Tier | Sources agree | Goes in bundle? | Goes in review report? |
|---|---|---|---|
| `authoritative` | 3/3 | yes | no |
| `likely` | 2/3 | yes (default) | spot-check section |
| `review` | 1/3 (Wikidata only) | no (default) | yes — held back for editorial decision |

`--include-review-tier` overrides the default and ships the 1-source-only
games in the bundle.

## Quick start

The RAWG API key is read automatically from `GLHF/Services/Secrets.swift`
(the same file the iOS app uses), so no env var is needed on a developer
machine that's already set up to build the app:

```bash
uv run curate.py --platform nes
```

Override with `$RAWG_API_KEY` if you want to use a different key, or pass
`--skip-rawg` to run the Wikidata/Wikipedia/No-Intro pipeline without
resolving RAWG IDs (useful when iterating on the curation logic):

```bash
RAWG_API_KEY=different_key uv run curate.py --platform nes
uv run curate.py --platform nes --limit 50 --skip-rawg
```

The first run takes a few minutes (one RAWG call per Wikidata candidate, plus
the Wikipedia HTML fetch). Responses are cached under `.cache/`, so re-runs
are near-instant. Delete `.cache/` to force a fresh pull.

## Required external data

The Wikidata SPARQL endpoint and the Wikipedia article are auto-fetched.

**Quick path (NES):** `./scripts/fetch_nes_dat.sh` downloads the
[libretro-database](https://github.com/libretro/libretro-database) ClrMamePro
DAT (header cites `no-intro`). Same parenthetical naming as DAT-o-MATIC.

**Official path:** DAT-o-MATIC XML (captcha login) → save as
`data/no-intro/nes.dat`. XML and ClrMamePro are both supported.

`data/no-intro/*.dat` is gitignored (~1.4MB). Without it, curation uses
Wikidata + Wikipedia only (no `authoritative` 3/3 tier).

After adding No-Intro, save `output/nes-before-nointro.json` then run
`uv run scripts/nointro_impact_report.py` for a before/after summary.

## Outputs

```
output/
├── nes.json                    ← the deliverable bundle (schemaVersion: 2)
└── review/
    └── nes-review.md           ← editorial review report

overrides/
├── nes.toml                    ← editorial decisions (committed to git)
└── nes.toml.example            ← worked example with real cases
```

### `nes.json` schema

```json
{
  "id": "nes-20260429",
  "displayName": "Complete Nintendo Entertainment System Library",
  "platformName": "Nintendo Entertainment System",
  "platformSlug": "nes",
  "region": "Western",
  "version": "20260429",
  "schemaVersion": 2,
  "sources": ["wikidata", "wikipedia", "no-intro", "rawg"],
  "sourceCounts": {
    "authoritative": 612,
    "likely": 98,
    "review": 41
  },
  "gameCount": 710,
  "matchedGameCount": 698,
  "games": [
    {
      "name": "Galaga",
      "releaseYear": 1985,
      "releaseYearSource": "rawg",
      "wikidataReleaseYear": 1981,
      "publishers": ["Namco"],
      "developers": ["Namco"],
      "regions": ["Europe", "Japan", "North America"],
      "rawgID": 53830,
      "rawgName": "Galaga (1981)",
      "wikidataQID": "Q1043534",
      "mobygamesID": "galaga",
      "igdbID": "arcade-game-series-galaga",
      "matchStatus": "matched",
      "matchHighConfidence": true,
      "validation": {
        "inWikidata": true,
        "inWikipedia": true,
        "inNoIntro": true,
        "sourceCount": 3,
        "confidenceTier": "authoritative"
      }
    }
  ]
}
```

Field notes from the iOS app's perspective:

- `releaseYear` is now the NES-port year, not the franchise's earliest year.
  `wikidataReleaseYear` preserves Wikidata's earliest for audit (and for the
  rare case where a downstream feature wants to show "originally an arcade
  game from 1981").
- `validation.confidenceTier` lets the UI show a tier badge or filter.
- `rawgID` remains the most important field — it lets the existing
  `RAWGService.getGameDetail` code populate cover art, descriptions, and
  screenshots without re-doing the match at runtime.

### `review/nes-review.md`

Markdown report with these sections:

- **Match summary** — RAWG match rate.
- **Source-tier summary** — count per tier + region-filter drops.
- **Review tier** — every game where only Wikidata vouches; held back from
  the bundle, manual call required.
- **Likely tier** — every game with 2/3 source agreement; ships in the
  bundle, eyeball-only.
- **Overrides applied** — every editorial decision sourced from
  `overrides/<slug>.toml`, with QID + change summary + reason.
- **Wikipedia gaps** — Wikipedia-listed Western games that didn't match any
  Wikidata candidate. Add as `[[supplement]]` or accept the gap.
- **No-Intro gaps** — DAT-listed Western games that didn't match any
  Wikidata candidate. Manual call.
- **Region-vote drops** — games whose multi-source Western-vote came back
  negative. Skim for false positives.
- **RAWG resolution issues** — fuzzy-match failures and low-confidence
  matches. The bundle still includes these games (with `rawgID: null`); the
  iOS app falls back to a runtime search for cover art / detail.

The review report is the editorial step — expect 1-3 hours of manual review
per platform after the automated run.

## Editorial overrides

`overrides/<slug>.toml` is the single source of truth for editorial
decisions. The pipeline reads the file every run; edits land in git,
survive cache invalidation, and surface in the review report's "Overrides
applied" section so the next reviewer sees what was changed and why.

### Workflow

1. Run `uv run curate.py --platform <slug>` once. Open the review report.
2. Walk it top-to-bottom. The four sections that need decisions, in priority
   order:
   - **Review tier** (~40 games) — single-source candidates. Use `[include]`
     to ship one, optionally with `[name]` / `[year]` overrides if Wikidata's
     metadata isn't Western-canonical.
   - **Wikipedia gap analysis** (~60 games) — Wikipedia confirms a Western
     release but no Wikidata entity matched. Either accept the gap or add a
     `[[supplement]]` entry with the Wikipedia-canonical name.
   - **RAWG resolution issues** (~36 games) — game already ships, just
     missing a stable RAWG ID. Use `[rawg]` to pin the right ID.
   - **Region-vote drops** (~550 games) — skim, don't read row-by-row. Most
     are correct JP-only drops. Look for famous JP titles you remember
     having a Western release.
3. Re-run the pipeline. The "Overrides applied" report section confirms
   each decision landed.
4. Commit `overrides/<slug>.toml` to git. Done.

### Schema

Each section is optional. Reasons are required strings (so future-you knows
why):

```toml
[include]
"Q123" = "1991 NA Konami release Wikipedia missed"

[exclude]
"Q456" = "prototype, never shipped commercially"

[name]
"Q789" = "Galaga"             # rename Wikidata 'Galaga: Demons of Death'

[year]
"Q789" = 1985                 # pin year when no source has it right

[rawg]
"Q789" = 24881                # force RAWG ID for low-confidence matches

[[supplement]]                # for Wikipedia entries with no Wikidata match
slug       = "mike-tysons-punch-out"
name       = "Mike Tyson's Punch-Out!!"
year       = 1987
rawg_id    = 25081            # optional; absent = fuzzy-match by name
publishers = ["Nintendo"]
note       = "1987 NA original; Wikidata's Punch-Out!! is the SNES port"
```

See `overrides/<slug>.toml.example` for a worked example using real Dragon
Warrior series + Mike Tyson's Punch-Out cases.

### Behavior notes

- A QID in `[include]` ships in the bundle regardless of confidence tier.
- A QID in `[exclude]` is dropped before the Western-vote runs.
- An `[include]` QID may also appear in `[name]` / `[year]` / `[rawg]`.
- A QID appearing in both `[include]` and `[exclude]` is a hard error.
- Overrides referencing QIDs not in the current Wikidata candidate pool
  are silently ignored (with a `[overrides]` warning to stderr) so the
  file can persist across schema migrations.
- The `releaseYearSource` for an override-applied year is `override`.
- The `matchStatus` for an override-pinned RAWG ID is `override`.
- Bundle entries force-included by `[include]` carry an `overrideReason`
  field with the value from the TOML.

## Tuning

Defaults are conservative; override in the source if a platform has unusually
clean or unusually messy data:

| Constant | File | Default | What it controls |
|---|---|---|---|
| `NAME_MATCH_THRESHOLD` | `sources/rawg.py` | 85 | Minimum rapidfuzz `WRatio` for an auto-accept |
| `YEAR_TOLERANCE` | `sources/rawg.py` | 2 | Years apart Wikidata vs. RAWG can be |
| `NAME_OVERRIDES_YEAR` | `sources/rawg.py` | 95 | At this name score, ignore year mismatch |
| `HIGH_CONFIDENCE_THRESHOLD` | `sources/rawg.py` | 92 | Below this, match shows up in spot-check |
| `WESTERN_REGION_TOKENS` | `config.py` | (see file) | Tokens that mark a region as Western |

## Adding a new platform

Add an entry to `PLATFORMS` in `config.py`:

```python
"snes": PlatformConfig(
    slug="snes",
    display_name="Super Nintendo Entertainment System",
    region="Western",
    wikidata_qid="Q183259",
    rawg_platform_id=79,
    rawg_platform_label="SNES",
    wikipedia_list_url=(
        "https://en.wikipedia.org/wiki/"
        "List_of_Super_Nintendo_Entertainment_System_games"
    ),
    nointro_dat_filename="snes.dat",
),
```

Wikidata Q-ids for common platforms:

| Platform | Q-id |
|---|---|
| Nintendo Entertainment System (Western) | Q172742 |
| Family Computer (Famicom, JP) | Q11288 |
| Super Nintendo Entertainment System | Q183259 |
| Game Boy | Q186437 |
| Nintendo 64 | Q184839 |
| Sega Genesis (US) | Q10676 |
| PlayStation | Q10677 |

RAWG platform IDs: pull the live list with `GLHF/RAWGService.getPlatforms()`
or `GET /api/platforms` directly.

## Caveats

- **Wikidata coverage varies by platform.** NES, SNES, PSX, GameCube are
  excellent. Obscure platforms (NEC PC-FX, FM Towns Marty, Bandai WonderSwan)
  are sparse — the No-Intro/Wikipedia cross-reference matters most for them.
- **Strict-Western is opinionated.** Famicom-only games (and Famicom Disk
  System exclusives that Wikidata sometimes tags as `Q172742`) are dropped
  by design. To produce a Famicom bundle, add a separate `PlatformConfig`
  with `wikidata_qid="Q11288"` and `region="Japan"`.
- **Wikipedia/No-Intro normalization is exact-string against `matching.normalize`.**
  Subtle name differences (`Adventures of Lolo` vs. `Adventures of Lolo I`,
  `Castlevania III: Dracula's Curse` vs. `Akumajou Densetsu`) will show up as
  cross-reference misses. The review report's "gap analysis" sections are
  the editorial surface for resolving these.
- **Multicarts, championship cartridges, peripheral titles** are handled by
  Wikidata's editorial decisions; document GLHF-specific overrides in this
  README when you make them.
- **Set sizes change over time** (newly-discovered prototypes, unlicensed
  releases that get reclassified). Re-run the pipeline; the version stamp
  in the bundle ID lets the iOS app reconcile against existing user data.

## Legal

- **Wikidata** — CC0 public domain; no attribution required.
- **Wikipedia** — CC-BY-SA; we extract *facts* from the article (title,
  developer, publisher, release dates), not the article text.
- **No-Intro DAT** — DAT files themselves have a murky license; the *facts*
  inside (game names, regions) are factual and not copyrightable per
  *Feist v. Rural*. We don't redistribute the DAT.
- **RAWG** — terms of service apply to API responses; the resolved IDs are
  used to drive runtime calls under the same agreement, not redistributed.
- **PriceCharting** (planned future integration) — paid CSV is licensed
  for the subscriber's use; only the facts (UPC codes, factual game names)
  would be embedded into the bundle, never the proprietary price data.
