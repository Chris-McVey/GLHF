"""Wikidata SPARQL extraction.

Pulls the *primary* candidate list, but does not decide regional inclusion —
that's the orchestrator's job after Wikipedia + No-Intro have been consulted.
This source still records:

  - All P577 publication dates per game, with their P400 platform qualifier
    (so the orchestrator can prefer a date stamped with the platform we
    actually care about).
  - All P291 region qualifiers across all dates (the orchestrator uses
    these as one of three Western-evidence sources).

The platform `wikidata_qids` is a tuple because Wikidata splits hardware
families inconsistently (NES `Q172742` vs Famicom `Q11288`); we query both
and let cross-source consensus pick a region.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

import requests

from cache import cached_json
from config import PlatformConfig, USER_AGENT

WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

WIKIDATA_QUERY_TEMPLATE = """
SELECT DISTINCT
  ?game ?gameLabel ?wpEnTitle ?releaseDate ?stmtPlatform ?regionLabel
  ?publisherLabel ?developerLabel
  ?mobygamesId ?igdbId
WHERE {
  VALUES ?platform { %PLATFORM_VALUES% }
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P400 ?platform .
  OPTIONAL {
    ?game p:P577 ?stmt .
    ?stmt ps:P577 ?releaseDate .
    OPTIONAL { ?stmt pq:P291 ?region . }
    OPTIONAL { ?stmt pq:P400 ?stmtPlatform . }
  }
  OPTIONAL { ?game wdt:P123 ?publisher . }
  OPTIONAL { ?game wdt:P178 ?developer . }
  OPTIONAL { ?game wdt:P1933 ?mobygamesId . }
  OPTIONAL { ?game wdt:P5794 ?igdbId . }
  OPTIONAL {
    ?wpArticle schema:about ?game ;
               schema:isPartOf <https://en.wikipedia.org/> ;
               schema:name ?wpEnTitle .
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""

_QID_LIKE_LABEL = re.compile(r"^Q\d+$")
_YEAR = re.compile(r"^(\d{4})")


def fetch(platform: PlatformConfig) -> list[dict[str, Any]]:
    values = " ".join(f"wd:{qid}" for qid in platform.wikidata_qids)
    query = WIKIDATA_QUERY_TEMPLATE.replace("%PLATFORM_VALUES%", values)

    def _fetch() -> dict[str, Any]:
        print(f"[wikidata] Querying SPARQL for platforms {platform.wikidata_qids}...")
        response = requests.get(
            WIKIDATA_SPARQL_ENDPOINT,
            params={"query": query, "format": "json"},
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/sparql-results+json",
            },
            timeout=180,
        )
        response.raise_for_status()
        return response.json()

    cache_key = "+".join(sorted(platform.wikidata_qids))
    raw = cached_json("wikidata", cache_key, _fetch)
    bindings = raw["results"]["bindings"]
    print(f"[wikidata] {len(bindings)} raw bindings.")
    return bindings


def coalesce(
    bindings: list[dict[str, Any]],
    platform: PlatformConfig,
) -> list[dict[str, Any]]:
    """Group rows by ?game URI; return the candidate list (unfiltered).

    Each game record carries:
      - `release_year_wikidata_platform`: earliest year from a P577 statement
        whose P400 qualifier matches one of this platform's Q-ids. Useful
        for sorting; not authoritative for the *Western* port year because
        Wikidata contributors apply the NES Q-id to Famicom releases too.
      - `release_year_wikidata_earliest`: earliest year across all P577.
      - `regions`: union of P291 region qualifiers across all release dates.

    Region filtering is intentionally NOT done here. The orchestrator's
    `is_western` vote considers Wikipedia and No-Intro evidence too.
    """
    grouped: dict[str, dict[str, Any]] = {}
    multi: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "publishers": set(),
            "developers": set(),
            "regions": set(),
            "all_release_years": set(),
            "platform_release_years": set(),
        }
    )
    skipped_unlabeled = 0
    rescued_via_wikipedia = 0

    platform_qid_uris = {
        f"http://www.wikidata.org/entity/{qid}" for qid in platform.wikidata_qids
    }

    for row in bindings:
        qid_uri = row["game"]["value"]
        label = row.get("gameLabel", {}).get("value", "")
        wp_title = row.get("wpEnTitle", {}).get("value", "")
        # When `gameLabel` is missing, the SERVICE wikibase:label fallback
        # returns the bare QID. Many famous games (Duck Hunt = Q764069, etc.)
        # have no English rdfs:label but DO have an English Wikipedia article;
        # use the Wikipedia page title as the rescue name.
        if _QID_LIKE_LABEL.match(label):
            if wp_title:
                label = wp_title
                rescued_via_wikipedia += 1
            else:
                skipped_unlabeled += 1
                continue
        if qid_uri not in grouped:
            grouped[qid_uri] = {
                "wikidata_qid": qid_uri.rsplit("/", 1)[-1],
                "wikidata_uri": qid_uri,
                "name": label,
                "wikipedia_title": wp_title or None,
                "mobygames_id": row.get("mobygamesId", {}).get("value"),
                "igdb_id": row.get("igdbId", {}).get("value"),
            }

        date_value = row.get("releaseDate", {}).get("value")
        stmt_platform = row.get("stmtPlatform", {}).get("value")
        if date_value:
            year_match = _YEAR.match(date_value)
            if year_match:
                year = int(year_match.group(1))
                multi[qid_uri]["all_release_years"].add(year)
                if stmt_platform in platform_qid_uris:
                    multi[qid_uri]["platform_release_years"].add(year)
        if pub := row.get("publisherLabel", {}).get("value"):
            multi[qid_uri]["publishers"].add(pub)
        if dev := row.get("developerLabel", {}).get("value"):
            multi[qid_uri]["developers"].add(dev)
        if region := row.get("regionLabel", {}).get("value"):
            multi[qid_uri]["regions"].add(region)

    out: list[dict[str, Any]] = []
    for qid_uri, base in grouped.items():
        meta = multi[qid_uri]
        all_years = sorted(meta["all_release_years"])
        platform_years = sorted(meta["platform_release_years"])
        base["release_year_wikidata_earliest"] = all_years[0] if all_years else None
        base["release_year_wikidata_platform"] = (
            platform_years[0] if platform_years else None
        )
        base["all_release_years"] = all_years
        base["publishers"] = sorted(meta["publishers"])
        base["developers"] = sorted(meta["developers"])
        base["regions"] = sorted(meta["regions"])
        out.append(base)

    out.sort(key=lambda g: (
        g.get("release_year_wikidata_platform")
        or g.get("release_year_wikidata_earliest")
        or 9999,
        g["name"].lower(),
    ))

    if rescued_via_wikipedia:
        print(
            f"[wikidata] Rescued {rescued_via_wikipedia} unlabeled rows via "
            f"English Wikipedia sitelink."
        )
    if skipped_unlabeled:
        print(
            f"[wikidata] Skipped {skipped_unlabeled} rows with no English "
            f"label or Wikipedia sitelink."
        )
    print(f"[wikidata] {len(out)} unique games after coalescing.")
    return out
