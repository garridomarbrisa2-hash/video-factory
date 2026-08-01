# Project Factory — Autonomous Episode Processing

How an agent turns a folder of episode research into finished videos, resumably,
with **generated assets as the default** (manual prompts) and stock only on request.

## Layout

```
projects/
  <series>/               # e.g. theranos, ww2, stoicism
    Ep1.md                # topic research / brief for episode 1
    Ep2.md
    tracker.md            # per-episode stage state (auto-maintained)
```

Each `Ep*.md` is the **brief + research** for one episode. The agent reads it and
runs the skills chain. `tracker.md` records where every episode stands so any
session can pick up mid-run.

## The contract

1. **Discover** — `pipeline.projects.discover_projects()` finds every series with
   `Ep*.md` files. For each, `load_project()` merges `tracker.md` state.
2. **Resume** — for each pending episode, `episode.next_stage()` returns the first
   stage not yet `done`/`skipped`. Start there, not from the top.
3. **Process stages in order** (see below), updating the tracker after each:
   `set_stage(proj, "Ep1", stage, "in_progress")` → work → `"done"` → `write_tracker(proj)`.
4. **Never abort a render on a missing asset** — Path B prints the prompt and falls
   back to a style plate, flagging `needs_manual_asset`.

## Stages (in order)

| Stage | What the agent does | Output |
|-------|--------------------|--------|
| `style` | Run `select_style` on the Ep brief → `global_style` | style id |
| `script` | Skill `01_script_writer` → retention script (style density/rhythm) | script text |
| `vo` | Run `python -m pipeline.vo_plan --script <script.md> --output <vo_plan.json>` → synthesize whole script and measure paragraph beats | VO plan with audio, durations, word times |
| `scenes` | Skill `02_director` consumes `vo_plan.json` → scenes fitted to measured beats, layout/energy/b-roll plan | scene list |
| `assets` | **Default `generated`**: emit `fallback_prompt` + `gen_kind` per scene; pipeline prints prompts for missing files, you drop them in `assets/in/`. **Only if the Ep says "use stock"**: emit `broll.keyword` instead. | timeline.json |
| `render` | `python -m pipeline.orchestrator --timeline <file>` | final mp4 |

Local render:

```bash
python -m pipeline.orchestrator --timeline <timeline.json>
```

GitHub Remotion clips + local FFmpeg assembly:

```bash
python -m pipeline.orchestrator --timeline <timeline.json> \
  --render-mode github --github-repo <owner/repo> --github-ref <branch>
```

GitHub mode stages `remotion/cloud-payload/`. Commit and push that payload plus
`.github/workflows/remotion-render.yml` to the requested ref before dispatch;
Actions cannot read uncommitted local files. Downloaded Remotion clips are
validated, then local FFmpeg performs footage compositing, xfade, audio, and NVENC.

## Asset route (default = generated)

- The timeline's `asset_mode` **defaults to `generated`** — no need to set it.
- The agent writes `fallback_prompt` + `gen_kind` (`image` / `image_video` / `video`)
  per scene. The user AI-generates those assets and drops them in
  `pipeline/assets/in/scene_XX.*`.
- **Exception:** if an Ep brief declares "use stock" (or similar), the agent sets
  `asset_mode: "stock"` for that timeline and writes `broll.keyword` per scene
  (Pexels → Pixabay). Everything else is unchanged.

## tracker.md format

A markdown table, one row per episode, icon per stage:

```
| Ep | style | script | vo | scenes | assets | render |
|----|-------|--------|--------|----|--------|--------|
| Ep1 | ✅ | ✅ | ✅ | 🔨 | ⬜ | ⬜ |
| Ep2 | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
```

`⬜ pending  🔨 in_progress  ✅ done  ⏭️ skipped  🟥 blocked`

`pipeline/projects.py` reads/writes this — the agent should use it (or edit the
table directly) rather than inventing a new format, so resume stays reliable.

## Multi-session autonomy

Because state lives in `tracker.md`, an agent can:
- process one stage across all episodes, then stop;
- crash / be interrupted mid-episode and resume at `next_stage()`;
- run episodes in any order (each is independent).

The agent's loop is simply: `for ep in proj.pending_episodes(): run from ep.next_stage()`.
