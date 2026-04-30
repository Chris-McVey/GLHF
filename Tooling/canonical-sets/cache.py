"""On-disk JSON/text cache used by every source module."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from config import CACHE_DIR


def _path_for(namespace: str, key: str, suffix: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / namespace / f"{digest}{suffix}"


def cached_json(namespace: str, key: str, fetch_fn: Callable[[], Any]) -> Any:
    """Memoize JSON results to disk under .cache/<namespace>/<sha>.json."""
    path = _path_for(namespace, key, ".json")
    if path.exists():
        with path.open() as f:
            return json.load(f)
    path.parent.mkdir(parents=True, exist_ok=True)
    value = fetch_fn()
    with path.open("w") as f:
        json.dump(value, f, indent=2, sort_keys=True)
    return value


def cached_text(namespace: str, key: str, fetch_fn: Callable[[], str]) -> str:
    """Memoize an HTML/text response under .cache/<namespace>/<sha>.html."""
    path = _path_for(namespace, key, ".html")
    if path.exists():
        return path.read_text(encoding="utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    value = fetch_fn()
    path.write_text(value, encoding="utf-8")
    return value
