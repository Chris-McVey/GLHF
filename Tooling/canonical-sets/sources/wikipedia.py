"""Wikipedia "List of ... games" scraper.

Used as a *secondary validator* for the Wikidata-derived candidate list.
Wikipedia editors curate region-of-release explicitly, so a game that appears
in Wikipedia with non-empty NA or PAL release dates is high-confidence
Western. The same game absent from Wikipedia is a flag for editorial review.

The article structure for the NES list (and most other platform list articles)
is a single big sortable wikitable per "Licensed games" section, with columns:

    Title | Developer | Publisher | First released | JP date | NA date | PAL date

Sub-page article URLs vary; the scraper walks every wikitable on the page in
document order, attaches the most-recent preceding h2 heading to each row,
and uses that heading to derive `is_licensed` (True for "Licensed games",
"Compilations", "Championship games", platform-adapter sub-tables; False for
anything under "Unlicensed games"). The "Unreleased games" subtable is
skipped entirely — those games were never commercially released.
"""
from __future__ import annotations

import re
from typing import Any

import requests
from lxml import html as lxml_html

from cache import cached_text
from config import PlatformConfig, USER_AGENT
from matching import normalize

_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_FOOTNOTE_MARKER = re.compile(r"\[\s*[a-z]?\d+\s*\]")


def fetch(platform: PlatformConfig) -> dict[str, dict[str, Any]]:
    """Return a dict keyed on normalized title.

    Each record is `{title, na_year, eu_year, jp_year, developer, publisher,
    has_western_release, is_licensed, source_section}`. Only entries from
    tables that look like the standard "Licensed games" schema are included.
    """
    def _fetch() -> str:
        print(f"[wikipedia] Fetching {platform.wikipedia_list_url}")
        response = requests.get(
            platform.wikipedia_list_url,
            headers={"User-Agent": USER_AGENT},
            timeout=60,
        )
        response.raise_for_status()
        return response.text

    html_text = cached_text("wikipedia", platform.slug, _fetch)
    tree = lxml_html.fromstring(html_text)

    games: dict[str, dict[str, Any]] = {}
    skipped_unreleased = 0
    licensed_count = 0
    unlicensed_count = 0
    for table, section, subsection in _tables_with_sections(tree):
        # Wikipedia tags sections explicitly. Only "Unlicensed games" subtables
        # carry that h2 — everything else (Licensed games, Compilations,
        # Championship games, Konami QTa, Bandai Datach) is licensed.
        section_lower = section.lower()
        if "unreleased" in section_lower:
            skipped_unreleased += sum(1 for _ in table.cssselect("tr")[1:])
            continue
        is_licensed = "unlicensed" not in section_lower

        col_index = _identify_columns(table)
        if "title" not in col_index:
            continue
        # Accept two table shapes:
        #   - Licensed/main: at least one of na/eu/jp release-year columns.
        #   - Unlicensed: a single generic 'year' column (Wikipedia editors
        #     don't track per-region for unlicensed/homebrew releases).
        if not any(k in col_index for k in ("na", "eu", "jp", "year")):
            continue

        # Map the unlicensed-table 'year' column to the right region based on
        # h3 subsection context. "Famicom games" subsection is JP-only;
        # everything else under "Unlicensed games" h2 (NES's lifespan, After
        # lifespan) is NA-canonical.
        single_year_to = None
        if "year" in col_index and not is_licensed:
            single_year_to = "jp" if "famicom" in subsection.lower() else "na"

        for row in table.cssselect("tr")[1:]:
            cells = row.cssselect("td, th")
            if not cells:
                continue
            title_idx = col_index["title"]
            if title_idx >= len(cells):
                continue
            title = _extract_title(cells[title_idx])
            if not title:
                continue
            year = _extract_year(cells, col_index.get("year"))
            record = {
                "title": title,
                "na_year": _extract_year(cells, col_index.get("na")) or
                    (year if single_year_to == "na" else None),
                "eu_year": _extract_year(cells, col_index.get("eu")),
                "jp_year": _extract_year(cells, col_index.get("jp")) or
                    (year if single_year_to == "jp" else None),
                "developer": _extract_text(cells, col_index.get("developer")),
                "publisher": _extract_text(cells, col_index.get("publisher")),
                "is_licensed": is_licensed,
                "source_section": section,
                "source_subsection": subsection,
            }
            record["has_western_release"] = bool(
                record["na_year"] or record["eu_year"]
            )
            key = normalize(title)
            if not key or key in games:
                continue
            games[key] = record
            if is_licensed:
                licensed_count += 1
            else:
                unlicensed_count += 1

    print(
        f"[wikipedia] Parsed {len(games)} games from list article "
        f"({licensed_count} licensed, {unlicensed_count} unlicensed; "
        f"skipped {skipped_unreleased} 'unreleased' rows)."
    )
    return games


def _tables_with_sections(tree) -> list[tuple[Any, str, str]]:
    """Yield (table, h2_section, h3_subsection) for every wikitable in document order.

    Walking in document order lets us cheaply attach the most recent
    preceding `<h2>` AND `<h3>` headings to each table. h2 distinguishes
    Licensed vs Unlicensed; h3 distinguishes Unlicensed sub-categories
    (NES's lifespan / Famicom games / After lifespan) — needed to map
    the single 'Year' column in unlicensed tables to a NA or JP slot.
    """
    out: list[tuple[Any, str, str]] = []
    current_h2 = ""
    current_h3 = ""
    for el in tree.iter():
        if el.tag == "h2":
            hl = el.cssselect(".mw-headline")
            text = (hl[0].text_content() if hl else el.text_content()).strip()
            current_h2 = " ".join(text.split())
            current_h3 = ""              # h3 resets when we hit a new h2
        elif el.tag == "h3":
            hl = el.cssselect(".mw-headline")
            text = (hl[0].text_content() if hl else el.text_content()).strip()
            current_h3 = " ".join(text.split())
        elif el.tag == "table" and "wikitable" in (el.get("class") or ""):
            out.append((el, current_h2, current_h3))
    return out


def _identify_columns(table) -> dict[str, int]:
    """Walk the first 2-3 rows of `<th>` cells to map header label → column index.

    NES-style headers stack two rows (top row colspans `Release date` over
    JP/NA/PAL sub-headers in the second row). We flatten by counting visual
    columns: the top row's colspans contribute their span to the total, and
    the second row's labels overwrite into the columns the colspan covered.
    """
    col_labels: dict[int, str] = {}

    rows = table.cssselect("tr")
    if not rows:
        return {}

    top_cells = rows[0].cssselect("th, td")
    col_pos = 0
    spans_to_fill: list[tuple[int, int]] = []  # (start_col, span_count)
    for cell in top_cells:
        colspan = int(cell.get("colspan") or 1)
        label = _clean_header(cell)
        if colspan > 1 and (
            "release" in label or "date" in label or "first" in label
        ):
            spans_to_fill.append((col_pos, colspan))
        else:
            col_labels[col_pos] = label
        col_pos += colspan

    if len(rows) > 1 and spans_to_fill:
        second_cells = rows[1].cssselect("th, td")
        idx = 0
        for start_col, span in spans_to_fill:
            for offset in range(span):
                if idx < len(second_cells):
                    col_labels[start_col + offset] = _clean_header(second_cells[idx])
                    idx += 1

    out: dict[str, int] = {}
    for i, label in col_labels.items():
        if "title" in label or label == "name" or label == "game":
            out.setdefault("title", i)
        elif "developer" in label:
            out.setdefault("developer", i)
        elif "publisher" in label:
            out.setdefault("publisher", i)
        elif (
            label == "na" or "north america" in label or "n. america" in label
            or "u.s." in label or "usa" in label
        ):
            out.setdefault("na", i)
        elif (
            label == "eu" or "europe" in label or label == "pal"
            or "pal " in label
        ):
            out.setdefault("eu", i)
        elif label == "jp" or "japan" in label:
            out.setdefault("jp", i)
        elif label == "year" or "year" in label:
            # Unlicensed-table fallback: single 'Year' column without
            # NA/EU/JP split. We treat it generically; the caller decides
            # whether to treat the year as NA or JP based on subtable
            # context (NES's lifespan -> NA, Famicom games -> JP).
            out.setdefault("year", i)
    return out


def _text(node) -> str:
    return " ".join(node.text_content().split()).strip()


def _clean_header(node) -> str:
    """Header text minus Wikipedia footnote markers (`NA[16][18]` -> `na`)."""
    return _FOOTNOTE_MARKER.sub("", _text(node)).strip().lower()


def _extract_title(cell) -> str:
    """Pull the canonical title from a title cell.

    Wikipedia structures NES list cells as
    `<i><a>NA Title</a></i><br><i>JP Title</i><sup>JP</sup>`. The canonical
    Western title is reliably the FIRST `<i>` element (whether or not it
    wraps a wikilink). Earlier we only looked at `<a>` and fell back to the
    full cell text when no link existed, which produced concatenated
    artifacts like `Thunder & LightningFamily BlockJP` for unlinked games.
    Pulling the first `<i>` handles linked, unlinked, and red-linked rows
    uniformly. Fall back to the plain cell text only when no `<i>` exists.
    """
    italics = cell.cssselect("i")
    if italics:
        text = _text(italics[0])
        if text:
            return text
    return _text(cell)


def _extract_year(cells, idx: int | None) -> int | None:
    if idx is None or idx >= len(cells):
        return None
    text = _text(cells[idx])
    if not text or "unreleased" in text.lower():
        return None
    m = _YEAR.search(text)
    return int(m.group(0)) if m else None


def _extract_text(cells, idx: int | None) -> str | None:
    if idx is None or idx >= len(cells):
        return None
    text = _text(cells[idx])
    return text or None
