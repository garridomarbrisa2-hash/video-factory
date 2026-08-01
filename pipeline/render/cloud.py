"""Cloud-render clip artifact validation."""

from __future__ import annotations

import json
import ntpath
import shutil
import subprocess
import argparse
from pathlib import Path
from typing import Any


def _load_json(value: Path | dict[str, Any]) -> Any:
    return json.loads(value.read_text(encoding="utf-8")) if isinstance(value, Path) else value


def _reject_windows_paths(value: Any, location: str = "payload") -> None:
    if isinstance(value, str) and ntpath.isabs(value):
        raise ValueError(f"Windows absolute path forbidden in cloud {location}: {value}")
    if isinstance(value, dict):
        for child in value.values():
            _reject_windows_paths(child, location)
    elif isinstance(value, list):
        for child in value:
            _reject_windows_paths(child, location)


def cloud_render_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Copy manifest while removing local-only footage paths from cloud payload."""
    clean = json.loads(json.dumps(manifest))
    clean.pop("output", None)
    for scene in clean.get("scenes", []):
        scene.pop("footage_path", None)
    _reject_windows_paths(clean, "manifest")
    return clean


def stage_cloud_payload(manifest_path: Path, destination: Path, public_dir: Path) -> Path:
    """Stage portable manifest and only Remotion-referenced public assets."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    clean = cloud_render_manifest(manifest)
    destination.mkdir(parents=True, exist_ok=True)
    assets = destination / "assets"
    keys = {"bg_image", "bg_video", "left_image", "right_image", "document_image", "overlay_image"}
    for scene in clean.get("scenes", []):
        if scene.get("render_route") == "ffmpeg" and not scene.get("needs_overlay"):
            continue
        props = scene.get("props", {})
        for key in keys:
            value = props.get(key)
            if not isinstance(value, str) or not value:
                continue
            source = public_dir / Path(value).name
            if not source.is_file():
                raise FileNotFoundError(f"Cloud render asset missing: {source}")
            assets.mkdir(exist_ok=True)
            target = assets / source.name
            shutil.copy2(source, target)
            props[key] = f"assets/{source.name}"
    output = destination / "manifest.json"
    output.write_text(json.dumps(clean, indent=2) + "\n", encoding="utf-8")
    return output


def _filenames(data: Any) -> list[str]:
    clips = data if isinstance(data, list) else data.get("clips")
    if not isinstance(clips, list):
        raise ValueError("Cloud clip metadata/manifest requires a clips list")
    names = [item if isinstance(item, str) else item.get("filename") for item in clips]
    if any(not isinstance(name, str) or not name or Path(name).name != name for name in names):
        raise ValueError("Cloud clip filenames must be plain relative filenames")
    return names


def validate_cloud_clips(
    metadata_path: Path,
    clips_dir: Path,
    expected_manifest: Path | dict[str, Any],
) -> list[Path]:
    """Validate exact metadata, manifest, and downloaded clip filename agreement."""
    metadata = _load_json(metadata_path)
    expected = _load_json(expected_manifest)
    _reject_windows_paths(metadata, "metadata")
    metadata_names = _filenames(metadata)
    metadata_items = metadata if isinstance(metadata, list) else metadata.get("clips", [])
    if "clips" in expected:
        expected_names = _filenames(expected)
    else:
        expected_names = []
        for index, scene in enumerate(expected.get("scenes", [])):
            pad = f"{index:02d}"
            if scene.get("render_route") != "ffmpeg":
                expected_names.append(f"clip_{pad}_{scene['type']}.mp4")
            elif scene.get("needs_overlay"):
                expected_names.append(f"overlay_{pad}_{scene['type']}.mov")
    if len(metadata_names) != len(set(metadata_names)) or len(expected_names) != len(set(expected_names)):
        raise ValueError("Duplicate cloud clip filename")
    if metadata_names != expected_names:
        raise ValueError("Cloud clip metadata does not match expected manifest")
    actual_names = sorted(path.name for path in clips_dir.iterdir() if path.is_file() and path.name != "clips.json")
    if actual_names != sorted(expected_names):
        raise ValueError("Cloud clip directory has missing or unexpected filenames")
    paths = [clips_dir / name for name in expected_names]
    metadata_by_name = {
        item["filename"]: item for item in metadata_items if isinstance(item, dict)
    }
    for path in paths:
        if path.stat().st_size == 0:
            raise ValueError(f"Cloud clip is empty: {path.name}")
        item = metadata_by_name.get(path.name)
        if item is None or "kind" not in item:
            # Filename-only contracts validate exact membership and non-empty files.
            continue
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
             "-show_entries", "stream=codec_name,width,height,pix_fmt,nb_read_frames,r_frame_rate",
             "-of", "json", str(path)], capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise ValueError(f"Cloud clip cannot be decoded: {path.name}")
        stream = (json.loads(proc.stdout).get("streams") or [{}])[0]
        if stream.get("width") != 1920 or stream.get("height") != 1080 or stream.get("r_frame_rate") != "30/1":
            raise ValueError(f"Cloud clip has wrong format: {path.name}")
        if item.get("kind") == "scene" and (stream.get("codec_name") != "h264" or stream.get("pix_fmt") != "yuv420p"):
            raise ValueError(f"Cloud scene clip has wrong codec/pixel format: {path.name}")
        if item.get("kind") == "overlay" and not str(stream.get("pix_fmt", "")).startswith("yuva"):
            raise ValueError(f"Cloud overlay lost alpha: {path.name}")
        frames = stream.get("nb_read_frames")
        if frames not in (None, "N/A") and abs(int(frames) - int(item["expected_frames"])) > 1:
            raise ValueError(f"Cloud clip has wrong frame count: {path.name}")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage portable GitHub Remotion payload")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--destination", type=Path, default=Path("remotion/cloud-payload"))
    parser.add_argument("--public-dir", type=Path, default=Path("remotion/public"))
    args = parser.parse_args()
    print(stage_cloud_payload(args.manifest, args.destination, args.public_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
