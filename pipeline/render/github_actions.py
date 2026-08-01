"""Submit CPU-only Remotion clip rendering to GitHub Actions."""

from __future__ import annotations

import subprocess
import time
import json

from pipeline.render.cloud import validate_cloud_clips
from pathlib import Path


def render_on_github(
    manifest: Path,
    output_dir: Path,
    repo: str,
    ref: str = "master",
    concurrency: int = 2,
    scene_pause: float = 1.0,
    timeout: int = 1800,
) -> Path:
    """Dispatch tracked manifest, wait, and download run-specific clip artifact."""
    manifest = manifest.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    root = Path(subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True
    ).stdout.strip()).resolve()
    try:
        manifest_rel = manifest.relative_to(root).as_posix()
    except ValueError as e:
        raise ValueError("GitHub manifest must be inside repository") from e
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", manifest_rel], capture_output=True, text=True
    )
    if tracked.returncode != 0:
        raise ValueError("GitHub manifest must be committed at requested ref")
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", manifest_rel, str(manifest.parent / "assets")],
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dirty:
        raise ValueError("GitHub payload has uncommitted changes; commit and push it before rendering")
    remote_has_ref = subprocess.run(
        ["git", "ls-remote", "--exit-code", "origin", ref], capture_output=True, text=True
    )
    if remote_has_ref.returncode != 0:
        raise ValueError(f"GitHub ref is not pushed to origin: {ref}")
    before = {
        item["databaseId"] for item in json.loads(subprocess.run(
            ["gh", "run", "list", "--repo", repo, "--workflow", "remotion-render.yml",
             "--limit", "20", "--json", "databaseId"],
            check=True, capture_output=True, text=True,
        ).stdout or "[]")
    }
    result = subprocess.run(
        ["gh", "workflow", "run", "remotion-render.yml", "--repo", repo, "--ref", ref,
         "-f", f"manifest={manifest_rel}",
         "-f", f"concurrency={concurrency}", "-f", f"scene_pause={scene_pause}"],
        check=True, capture_output=True, text=True,
    )
    run_id = ""
    discover_deadline = time.time() + 60
    while time.time() < discover_deadline and not run_id:
        runs = json.loads(subprocess.run(
            ["gh", "run", "list", "--repo", repo, "--workflow", "remotion-render.yml",
             "--limit", "20", "--json", "databaseId"],
            check=True, capture_output=True, text=True,
        ).stdout or "[]")
        new_ids = [str(item["databaseId"]) for item in runs if item["databaseId"] not in before]
        if len(new_ids) == 1:
            run_id = new_ids[0]
        elif len(new_ids) > 1:
            raise RuntimeError("Multiple workflow runs appeared; refusing ambiguous download")
        else:
            time.sleep(2)
    if not run_id:
        raise RuntimeError(f"Workflow dispatched but run ID missing: {result.stdout}")
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = subprocess.run(
            ["gh", "run", "view", run_id, "--repo", repo, "--json", "status,conclusion",
             "--jq", ".status + \" \" + (.conclusion // \"\")"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        if status.startswith("completed"):
            if not status.endswith("success"):
                raise RuntimeError(f"Remotion workflow failed: {run_id} ({status})")
            break
        time.sleep(10)
    else:
        raise TimeoutError(f"Remotion workflow timed out: {run_id}")
    subprocess.run(
        ["gh", "run", "download", run_id, "--repo", repo, "-n", f"remotion-clips-{run_id}",
         "-D", str(output_dir)], check=True,
    )
    validate_cloud_clips(output_dir / "clips.json", output_dir, manifest)
    return output_dir
