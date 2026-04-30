"""Title-normalization helpers shared by every source's cross-reference step."""
from __future__ import annotations

import re

_PARENTHETICAL_YEAR = re.compile(r"\s*\(\d{4}\)\s*")
_NONALNUM = re.compile(r"[^a-z0-9]+")


def strip_parenthetical_year(s: str) -> str:
    """Remove a trailing/embedded `(YYYY)` disambiguator.

    RAWG often suffixes duplicate titles with a year (`Galaga (1981)`) which
    rapidfuzz penalizes; stripping it before comparison restores the match.
    """
    return _PARENTHETICAL_YEAR.sub(" ", s).strip()


def normalize(s: str) -> str:
    """Canonical lowercase alphanumeric form for comparing titles across sources."""
    s = strip_parenthetical_year(s)
    s = s.lower()
    s = _NONALNUM.sub(" ", s)
    return s.strip()
