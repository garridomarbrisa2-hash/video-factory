"""Regenerate the searchable HyperFrames effect/component catalog.

HyperFrames (github.com/heygen-com/hyperframes) is a separate, non-Remotion
project (HTML/CSS/GSAP composed and rendered via Puppeteer/FFmpeg). It is not
a runtime dependency of Video Factory — this script reads a local clone once
and writes a flat, versioned JSON snapshot into pipeline/config/ so the
catalog can be searched (see pipeline/intelligence/hyperframes_catalog.py)
without needing the HyperFrames repo present.

Usage:
    python -m scripts.build_hyperframes_catalog [path-to-hyperframes-clone]

Defaults to ~/Documents/hyperframes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path("~/Documents/hyperframes").expanduser()
OUT_PATH = PROJECT_ROOT / "pipeline" / "config" / "hyperframes_catalog.json"


def build_catalog(hyperframes_root: Path) -> dict:
    items = []
    for group in ("components", "blocks", "examples"):
        group_dir = hyperframes_root / "registry" / group
        if not group_dir.is_dir():
            continue
        for item_dir in sorted(group_dir.iterdir()):
            meta_path = item_dir / "registry-item.json"
            if not meta_path.is_file():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            html_files = [
                f["path"] for f in meta.get("files", []) if f.get("type") == "hyperframes:snippet"
            ]
            items.append(
                {
                    "name": meta.get("name"),
                    "group": group,
                    "type": meta.get("type"),
                    "title": meta.get("title"),
                    "description": meta.get("description"),
                    "tags": meta.get("tags", []),
                    "variables": meta.get("variables", []),
                    "source_dir": str(item_dir.relative_to(hyperframes_root)),
                    "html_files": html_files,
                }
            )
    return {
        "generated_from": str(hyperframes_root),
        "count": len(items),
        "items": items,
    }


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    source = Path(args[0]).expanduser() if args else DEFAULT_SOURCE
    if not (source / "registry" / "registry.json").is_file():
        print(f"Not a HyperFrames checkout (no registry/registry.json): {source}", file=sys.stderr)
        return 1
    catalog = build_catalog(source)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {catalog['count']} items -> {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
