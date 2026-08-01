"""Depth-plane baker — split a still into soft far/mid/near parallax planes.

Why this exists (Phase 7): the "slideshow" tell is one rigid full-frame transform.
AE editors create depth by moving planes at different rates. For *scene* imagery
(wheat fields, mills) there is no clean subject to cut out, so we segment by
**luminance** into three soft, heavily-feathered planes — bright regions (typically
lit subject / nearer) vs dark (shadow / farther). Each plane is an RGBA layer that
Remotion drifts at a different rate → genuine parallax without ML.

Dependency-light by design: PIL + numpy only (no torch, no rembg). The masks are
soft (gaussian-feathered) so there are no hard cutout edges — the eye reads depth
from differential motion, not from silhouette boundaries.

Output per image `foo.png` ->  `<out_dir>/foo_far.png`, `foo_mid.png`, `foo_near.png`
plus a manifest entry the renderer reads. Deterministic (seeded), cacheable by SHA.

Design decision: 3 planes, luminance-keyed, feather radius scales with image size.
Not a true depth map (no MiDaS) — good-enough parallax at zero ML cost.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageFilter

# Plane keys in depth order: far (background) -> mid -> near (foreground).
PLANES = ("far", "mid", "near")


@dataclass
class DepthManifest:
    """Per-image record the Remotion renderer consumes via `depth` prop."""

    base: str  # full-frame base image (weakest motion)
    far: str
    mid: str
    near: str
    width: int
    height: int

    def to_dict(self) -> dict:
        return asdict(self)


def _luminance(rgb: np.ndarray) -> np.ndarray:
    """Rec. 709 luma, 0..1 float."""
    return (
        0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    ) / 255.0


def _soft_plane(
    luma: np.ndarray, lo: float, hi: float, feather: int, size: tuple[int, int]
) -> np.ndarray:
    """A soft mask for luma in [lo, hi], feathered. Returns 0..1 float alpha.

    Soft band: rises 0->1 across the lower third of the band, holds, falls 1->0
    across the upper third, so planes overlap smoothly and never hard-cut.
    """
    span = max(1e-6, hi - lo)
    t = (luma - lo) / span  # 0..1 position within band
    rise = np.clip(t / 0.33, 0, 1)
    fall = np.clip((1 - t) / 0.33, 0, 1)
    mask = np.minimum(rise, fall)
    # Feather in image space for organic edges.
    m = Image.fromarray((mask * 255).astype("uint8")).filter(
        ImageFilter.GaussianBlur(feather)
    )
    return np.asarray(m).astype("float32") / 255.0


def bake_depth_planes(
    image_path: str | Path,
    out_dir: str | Path,
    feather_frac: float = 0.02,
    render_size: tuple[int, int] = (1920, 1080),
) -> DepthManifest:
    """Split one image into far/mid/near RGBA planes. Returns the manifest.

    `feather_frac` — gaussian radius as a fraction of the longest edge (softness).
    `render_size` — planes are baked at the render resolution (NOT the source
    resolution) so Chrome composites ~2MP layers, not 4MP ones. This is the
    difference between a realtime-feel render and a slideshow-slow one.
    """
    image_path = Path(image_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    im = Image.open(image_path).convert("RGB")
    # Downscale to render res FIRST — planes are never needed at source res.
    im = im.resize(render_size, Image.LANCZOS)
    w, h = im.size
    rgb = np.asarray(im).astype("float32")
    luma = _luminance(rgb)
    feather = max(8, int(max(w, h) * feather_frac))

    # Luminance bands (overlapping soft bands). Dark = far, bright = near.
    bands = {
        "far": (0.0, 0.45),
        "mid": (0.3, 0.7),
        "near": (0.55, 1.0),
    }

    stem = image_path.stem
    paths: dict[str, str] = {}
    for key in PLANES:
        lo, hi = bands[key]
        alpha = _soft_plane(luma, lo, hi, feather, (w, h))
        rgba = np.dstack([rgb.astype("uint8"), (alpha * 255).astype("uint8")])
        out_path = out_dir / f"{stem}_{key}.png"
        Image.fromarray(rgba, "RGBA").save(out_path)
        paths[key] = out_path.name

    return DepthManifest(
        base=image_path.name, far=paths["far"], mid=paths["mid"], near=paths["near"],
        width=w, height=h,
    )


def bake_many(
    images: list[str | Path], out_dir: str | Path, manifest_path: str | Path
) -> dict[str, dict]:
    """Bake a batch, write a JSON manifest keyed by original filename."""
    manifest: dict[str, dict] = {}
    for img in images:
        dm = bake_depth_planes(img, out_dir)
        manifest[Path(img).name] = dm.to_dict()
    Path(manifest_path).write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    if len(args) < 2:
        print("usage: python -m pipeline.assets.depth_planes <out_dir> <img...>")
        raise SystemExit(1)
    out = args[0]
    m = bake_many(args[1:], out, Path(out) / "depth_manifest.json")
    for k, v in m.items():
        print(f"{k}: far/mid/near planes baked ({v['width']}x{v['height']})")
