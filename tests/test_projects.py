"""Tests for the project-folder factory (pipeline/projects.py) and the
generated-by-default asset route.

Covers: episode discovery, tracker write/parse round-trip, resume pointers,
stage validation, and the flipped asset_mode default. No render, no network.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline import projects as P


def _series(tmp_path: Path, name: str = "theranos", eps: int = 3) -> P.Project:
    return P.new_project(name, eps, root=tmp_path / "projects")


def test_new_project_scaffolds_briefs_and_tracker(tmp_path: Path) -> None:
    proj = _series(tmp_path)
    assert (tmp_path / "projects" / "theranos" / "Ep1.md").exists()
    assert (tmp_path / "projects" / "theranos" / "Ep3.md").exists()
    assert proj.tracker_path.exists()
    assert [e.name for e in proj.episodes] == ["Ep1", "Ep2", "Ep3"]
    # all pending -> resume at first stage
    assert all(e.next_stage() == "style" for e in proj.episodes)


def test_tracker_round_trip_and_resume(tmp_path: Path) -> None:
    proj = _series(tmp_path)
    P.set_stage(proj, "Ep1", "style", "done")
    P.set_stage(proj, "Ep1", "script", "done")
    P.set_stage(proj, "Ep1", "vo", "done")
    P.set_stage(proj, "Ep1", "scenes", "in_progress")
    P.set_stage(proj, "Ep2", "style", "done")
    P.write_tracker(proj)

    reloaded = P.load_project(tmp_path / "projects" / "theranos")
    assert reloaded.episodes[0].next_stage() == "scenes"  # resume mid-episode
    assert reloaded.episodes[1].next_stage() == "script"
    assert reloaded.episodes[2].next_stage() == "style"
    assert [e.name for e in reloaded.pending_episodes()] == ["Ep1", "Ep2", "Ep3"]


def test_complete_episode_excluded_from_pending(tmp_path: Path) -> None:
    proj = _series(tmp_path, eps=1)
    for s in P.STAGES:
        P.set_stage(proj, "Ep1", s, "done")
    P.write_tracker(proj)
    reloaded = P.load_project(tmp_path / "projects" / "theranos")
    assert reloaded.episodes[0].is_complete()
    assert reloaded.pending_episodes() == []


def test_set_stage_validates_names(tmp_path: Path) -> None:
    proj = _series(tmp_path)
    with pytest.raises(ValueError):
        P.set_stage(proj, "Ep1", "nonsense", "done")
    with pytest.raises(ValueError):
        P.set_stage(proj, "Ep1", "style", "nonsense")
    with pytest.raises(KeyError):
        P.set_stage(proj, "Ep99", "style", "done")


def test_discover_projects_finds_series_with_episodes(tmp_path: Path) -> None:
    _series(tmp_path, "a", 2)
    _series(tmp_path, "b", 1)
    (tmp_path / "projects" / "empty").mkdir()  # no Ep*.md -> skipped
    found = P.discover_projects(tmp_path / "projects")
    assert sorted(p.name for p in found) == ["a", "b"]


def test_asset_mode_default_is_auto() -> None:
    import json
    from pipeline import project_path

    schema = json.loads(
        (project_path("pipeline", "intelligence", "timeline_schema.json")).read_text(encoding="utf-8")
    )
    assert schema["properties"]["asset_mode"]["default"] == "auto"
    assert set(schema["properties"]["asset_mode"]["enum"]) == {"auto", "stock", "generated"}
