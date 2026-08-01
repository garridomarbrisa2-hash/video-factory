"""Project-folder factory: discover episode briefs (Ep*.md) and track per-episode
pipeline state so an agent can process a series autonomously and resume mid-run.

Layout (user-defined):

    projects/
      <series>/
        Ep1.md            # topic research / brief for episode 1
        Ep2.md
        tracker.md        # per-episode stage state (see TRACKER_TEMPLATE)

An episode flows through STAGES in order. The tracker records each stage's state
(pending / in_progress / done / skipped) so a fresh agent session can pick up
exactly where the last one stopped. This module is the deterministic read/write
layer; the agent (LLM) does the actual script/direct/VO authoring per stage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pipeline import ensure_dir, project_path

# Pipeline stages, in order. `assets` covers Path B (generated drop-ins / printed
# prompts) and Path A (stock); `render` is the Remotion+FFmpeg final.
STAGES = ["style", "script", "vo", "scenes", "assets", "render"]

STATE_ICONS = {
    "pending": "⬜",
    "in_progress": "🔨",
    "done": "✅",
    "skipped": "⏭️",
    "blocked": "🟥",
}
ICON_STATE = {v: k for k, v in STATE_ICONS.items()}

_EP_RE = re.compile(r"^Ep(\d+)\.md$", re.IGNORECASE)
_ROW_RE = re.compile(r"^\|\s*(Ep\d+)\s*\|(.+?)\|\s*$")


@dataclass
class Episode:
    """One episode brief + its per-stage states."""

    name: str  # e.g. "Ep1"
    number: int
    brief_path: Path
    states: dict[str, str] = field(default_factory=lambda: {s: "pending" for s in STAGES})

    def next_stage(self) -> str | None:
        """First stage not yet done/skipped — where the agent resumes."""
        for s in STAGES:
            if self.states.get(s, "pending") not in ("done", "skipped"):
                return s
        return None

    def is_complete(self) -> bool:
        return self.next_stage() is None


@dataclass
class Project:
    name: str
    root: Path
    tracker_path: Path
    episodes: list[Episode]

    def pending_episodes(self) -> list[Episode]:
        return [e for e in self.episodes if not e.is_complete()]


def _episode_name(path: Path) -> tuple[str, int] | None:
    m = _EP_RE.match(path.name)
    if not m:
        return None
    n = int(m.group(1))
    return f"Ep{n}", n


def discover_projects(root: Path | str = "projects") -> list[Project]:
    """Find all series folders containing at least one Ep*.md."""
    base = project_path(str(root))
    if not base.exists():
        return []
    projects: list[Project] = []
    for series_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        proj = load_project(series_dir)
        if proj.episodes:
            projects.append(proj)
    return projects


def load_project(series_dir: Path | str) -> Project:
    """Load one series folder: its Ep*.md briefs + tracker state (if present)."""
    d = Path(series_dir)
    if not d.is_absolute():
        d = project_path(str(d))
    episodes: list[Episode] = []
    for md in sorted(d.glob("Ep*.md")):
        parsed = _episode_name(md)
        if parsed:
            name, num = parsed
            episodes.append(Episode(name=name, number=num, brief_path=md))
    episodes.sort(key=lambda e: e.number)
    tracker_path = d / "tracker.md"
    proj = Project(name=d.name, root=d, tracker_path=tracker_path, episodes=episodes)
    if tracker_path.exists():
        _apply_tracker(proj, tracker_path.read_text(encoding="utf-8"))
    return proj


def _apply_tracker(proj: Project, text: str) -> None:
    """Parse tracker.md rows and merge recorded states into episodes."""
    by_name = {e.name.lower(): e for e in proj.episodes}
    for line in text.splitlines():
        m = _ROW_RE.match(line.strip())
        if not m:
            continue
        ep = by_name.get(m.group(1).strip().lower())
        if not ep:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        for stage, cell in zip(STAGES, cells):
            state = ICON_STATE.get(cell) or (cell if cell in STATE_ICONS else None)
            if state:
                ep.states[stage] = state


def render_tracker(proj: Project) -> str:
    """Serialize the project's tracker.md (header + one row per episode)."""
    header = "| Ep | " + " | ".join(STAGES) + " |\n"
    sep = "|" + "---|" * (len(STAGES) + 1) + "\n"
    rows = []
    for e in proj.episodes:
        cells = " | ".join(STATE_ICONS.get(e.states.get(s, "pending"), "⬜") for s in STAGES)
        rows.append(f"| {e.name} | {cells} |")
    legend = (
        "\n\nLegend: "
        + "  ".join(f"{icon}={state}" for state, icon in STATE_ICONS.items())
        + "\nStages: " + " → ".join(STAGES) + "\n"
    )
    return f"# Tracker — {proj.name}\n\n{header}{sep}" + "\n".join(rows) + legend


def write_tracker(proj: Project) -> Path:
    proj.tracker_path.write_text(render_tracker(proj), encoding="utf-8")
    return proj.tracker_path


def set_stage(proj: Project, episode: str, stage: str, state: str) -> None:
    """Update one episode's stage state (in memory; call write_tracker to persist)."""
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}; expected one of {STAGES}")
    if state not in STATE_ICONS:
        raise ValueError(f"unknown state {state!r}; expected one of {list(STATE_ICONS)}")
    ep = next((e for e in proj.episodes if e.name.lower() == episode.lower()), None)
    if ep is None:
        raise KeyError(f"episode {episode!r} not in project {proj.name!r}")
    ep.states[stage] = state


def new_project(series: str, episodes: int, root: Path | str = "projects") -> Project:
    """Scaffold a new series folder with empty Ep*.md briefs + a fresh tracker."""
    d = ensure_dir(Path(root) / series)
    for n in range(1, episodes + 1):
        ep = d / f"Ep{n}.md"
        if not ep.exists():
            ep.write_text(
                f"# Ep{n} — {series}\n\n## Topic research\n\n(paste research here)\n",
                encoding="utf-8",
            )
    proj = load_project(d)
    write_tracker(proj)
    return proj
