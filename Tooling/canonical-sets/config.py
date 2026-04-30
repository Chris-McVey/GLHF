"""Platform configurations and shared paths for the canonical-set pipeline."""
from __future__ import annotations

import dataclasses
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CACHE_DIR = SCRIPT_DIR / ".cache"
DATA_DIR = SCRIPT_DIR / "data"
NOINTRO_DIR = DATA_DIR / "no-intro"
OVERRIDES_DIR = SCRIPT_DIR / "overrides"
OUTPUT_DIR = SCRIPT_DIR / "output"
REVIEW_DIR = OUTPUT_DIR / "review"

USER_AGENT = (
    "GLHF-CanonicalSetCurator/0.2 "
    "(https://github.com/chrismcvey/GLHF; one-off curation tool)"
)

# Tokens any of which, when present in a region label, marks it as Western.
# Used both to filter Wikidata's per-release region qualifiers and to recognize
# region tags in No-Intro DAT filenames.
WESTERN_REGION_TOKENS = frozenset({
    "north america", "united states", "usa", "u.s.", "u.s.a.", "canada",
    "europe", "european union", "united kingdom", "uk",
    "germany", "france", "spain", "italy", "scandinavia", "sweden",
    "australia", "world",
})


@dataclasses.dataclass(frozen=True)
class PlatformConfig:
    slug: str                       # output filename slug ("nes")
    display_name: str               # canonical display name
    region: str                     # "Western", "Japan", etc.
    wikidata_qids: tuple[str, ...]  # all Q-ids treated as this platform
    rawg_platform_id: int           # numeric RAWG platform id
    rawg_platform_label: str        # human label for review reports
    wikipedia_list_url: str         # URL of the Wikipedia "List of ... games" article
    nointro_dat_filename: str       # canonical filename under data/no-intro/


# Wikidata splits the NES hardware family across at least three Q-ids and
# applies the tags inconsistently:
#   - Q172742: NES (Western) — Castlevania III, Mario Bros., etc.
#   - Q11288:  Famicom (JP) — Pac-Man, Donkey Kong, most early titles
#   - Q135321: Famicom Disk System — Castlevania I & II, Zelda I, Metroid,
#              Kid Icarus (originally FDS, ported to NES cartridge for NA)
# Querying all three and letting the Western-vote step (Wikipedia NA +
# No-Intro region tag) decide regional inclusion is the only way to build
# a complete Western NES candidate pool.
PLATFORMS: dict[str, PlatformConfig] = {
    "nes": PlatformConfig(
        slug="nes",
        display_name="Nintendo Entertainment System",
        region="Western",
        wikidata_qids=("Q172742", "Q11288", "Q135321"),
        rawg_platform_id=49,
        rawg_platform_label="NES",
        wikipedia_list_url=(
            "https://en.wikipedia.org/wiki/"
            "List_of_Nintendo_Entertainment_System_games"
        ),
        nointro_dat_filename="nes.dat",
    ),
}
