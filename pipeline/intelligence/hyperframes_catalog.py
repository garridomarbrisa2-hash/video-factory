"""Searchable index over the HyperFrames effect/component catalog.

The catalog itself (382 components/blocks/examples from
github.com/heygen-com/hyperframes) is a static snapshot at
pipeline/config/hyperframes_catalog.json, produced by
scripts/build_hyperframes_catalog.py from a local HyperFrames clone.
HyperFrames is not a runtime dependency — this module only reads the JSON
snapshot, so it works whether or not the HyperFrames repo is present.

Usage:
    python -m pipeline.intelligence.hyperframes_catalog --search "camera push"
    python -m pipeline.intelligence.hyperframes_catalog --tag transition-primitive
    python -m pipeline.intelligence.hyperframes_catalog --name count-up
"""

from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).resolve().parents[1] / "config" / "hyperframes_catalog.json"


@lru_cache(maxsize=1)
def _load() -> list[dict[str, Any]]:
    if not CATALOG_PATH.is_file():
        raise FileNotFoundError(
            f"{CATALOG_PATH} not found. Run scripts/build_hyperframes_catalog.py "
            "against a local HyperFrames clone first."
        )
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8")).get("items", [])


def _matches_text(item: dict[str, Any], query: str) -> bool:
    q = query.casefold()
    haystack = " ".join(
        [
            str(item.get("name") or ""),
            str(item.get("title") or ""),
            str(item.get("description") or ""),
            " ".join(item.get("tags", [])),
        ]
    ).casefold()
    return all(term in haystack for term in q.split())


def search(
    query: str | None = None,
    *,
    tag: str | None = None,
    group: str | None = None,
    item_type: str | None = None,
    limit: int | None = 25,
) -> list[dict[str, Any]]:
    """Search the catalog. All filters are ANDed together."""
    results = _load()
    if group:
        results = [i for i in results if i.get("group") == group]
    if item_type:
        results = [i for i in results if i.get("type") == item_type]
    if tag:
        results = [i for i in results if tag in i.get("tags", [])]
    if query:
        results = [i for i in results if _matches_text(i, query)]
    return results[:limit] if limit else results


def get(name: str) -> dict[str, Any] | None:
    """Look up one catalog item by exact name."""
    for item in _load():
        if item.get("name") == name:
            return item
    return None


def tag_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in _load():
        for tag in item.get("tags", []):
            counts[tag] = counts.get(tag, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Search the HyperFrames catalog")
    parser.add_argument("--search", dest="query", default=None)
    parser.add_argument("--tag", default=None)
    parser.add_argument("--group", choices=["components", "blocks", "examples"], default=None)
    parser.add_argument("--name", default=None)
    parser.add_argument("--tags", action="store_true", help="print tag frequency and exit")
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args(argv)

    if args.tags:
        for tag, count in tag_counts().items():
            print(f"{count:4d}  {tag}")
        return 0

    if args.name:
        item = get(args.name)
        print(json.dumps(item, indent=2, ensure_ascii=False) if item else f"Not found: {args.name}")
        return 0 if item else 1

    results = search(args.query, tag=args.tag, group=args.group, limit=args.limit)
    for item in results:
        print(f"{item['name']:32s} [{item['group']:10s}] {', '.join(item['tags'][:5])}")
    print(f"\n{len(results)} result(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
