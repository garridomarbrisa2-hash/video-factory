"""Delete reproducible render data after final video approval."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def cleanup(root: Path, keep_output: str | None = None) -> list[Path]:
    removed: list[Path] = []
    output = root / "output"
    keep = (output / keep_output).resolve() if keep_output else None
    if output.exists():
        for path in output.iterdir():
            if keep and path.resolve() == keep:
                continue
            shutil.rmtree(path) if path.is_dir() else path.unlink()
            removed.append(path)

    cache = root / "pipeline" / "assets" / "cache"
    if cache.exists():
        shutil.rmtree(cache)
        removed.append(cache)

    public = root / "remotion" / "public"
    for pattern in ("gen_*.png", "scene_*.mp4", "plate_*.mp4"):
        for path in public.glob(pattern):
            path.unlink()
            removed.append(path)
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved", action="store_true", help="Confirm final video approval")
    parser.add_argument("--keep-output", help="Output filename to preserve")
    args = parser.parse_args()
    if not args.approved:
        parser.error("--approved is required because cleanup is irreversible")
    root = Path(__file__).resolve().parents[1]
    for path in cleanup(root, args.keep_output):
        print(f"deleted {path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
