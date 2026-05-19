# Canonical set policy (GLHF)

## Scope

Western **licensed** and **unlicensed retail** releases for each supported platform.

| In scope | Out of scope |
|----------|----------------|
| Wikipedia “Licensed games” rows with a NA and/or PAL release year | Japan-only / Famicom-only rows (no NA/PAL year) |
| Wikipedia “Unlicensed games” rows with Western release (e.g. Tengen, Color Dreams, Wisdom Tree) | “Unreleased games” table |
| Editorial `[supplement]` entries (multicarts, etc.) documented in `overrides/` | Homebrew / aftermarket hobbyist carts |
| | “After lifespan” / homebrew Wikipedia subsections |
| | Post-2005 unlicensed titles (modern homebrew heuristic) |

## Primary authority

**Wikipedia** — [List of Nintendo Entertainment System games](https://en.wikipedia.org/wiki/List_of_Nintendo_Entertainment_System_games) (and the equivalent list article per platform).

Membership is: *appears on that list with a NA or PAL release date, in a licensed or unlicensed retail section, and passes homebrew exclusion.*

## Secondary sources (enrichment only)

| Source | Role |
|--------|------|
| **Wikidata** | Optional QID, MobyGames/IGDB IDs when name-matched |
| **No-Intro DAT** | Validation / gap report; not membership |
| **RAWG** | Cover art and detail pages (`rawgID`) |

## Bundle identity

- `primarySource`: `wikipedia`
- `policy`: `western-licensed-and-unlicensed-retail`
- `version`: date stamp (`YYYYMMDD`) of the Wikipedia scrape + override file

## Editorial overrides

Human decisions live in `overrides/<platform>.toml` (`[exclude]`, `[name]`, `[rawg]`, `[[supplement]]`, …). Re-run `uv run curate.py` after edits.

## Attribution

Wikipedia content is [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). Ship attribution in app settings or collection metadata when we surface “Complete NES (Wikipedia)” presets.
