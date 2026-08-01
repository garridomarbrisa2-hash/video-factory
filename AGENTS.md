# AGENTS.md

## Project Overview

**Vidrush-Style Local Pipeline** — a local vidrush.ai clone for a video automation factory. Brief in → finished long-form video out.

**Pipeline:** brief → **global style selection** → skill-chained script → custom TTS voiceover → stock/manual B-roll → Remotion batch render (motion graphics in the style's grammar) → FFmpeg xfade + NVENC final.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Intelligence | Python 3.11+ (style selection, skills chain, orchestrator) |
| Scene rendering | Remotion 4.x (React + TypeScript), Chrome raster via `@remotion/renderer` |
| Assembly + encode | FFmpeg 7.x CLI (xfade, sidechaincompress, loudnorm) |
| GPU encode | NVENC (RTX 3060): p6/hq final, ~12 Mbps 1080p30 |
| VO | Qwen3-TTS on Modal (`modal_qwen`, default — endpoint in `docs/API/modal-qwen3tts.md`) / `gradio_qwen` / `custom_http`/`custom_cli` adapters (`pipeline/config/vo.json`) |
| Stock video | Pexels (primary, `/v1/videos/search`) / Pixabay (backup + animation), user API keys via env |
| Image gen | ModelScope — Z-Image (default photoreal/bilingual) / Krea-2-Turbo (stylized), `MODELSCOPE_API_KEY` |
| Style system | JSON style templates in `pipeline/intelligence/styles/` (5 platform themes + per-project styles such as `ledger`) |

## Project Structure

```
ffmpeg-mcp/
├── AGENTS.md                    # this file
├── Implementation-Plan.md       # v3 execution plan (research-backed)
├── Implementation-Tracker.md    # phase tracker
├── docs/
│   ├── GLOBAL_STYLE_RESEARCH.md # EVIDENCE BASE — VidRush/Remotion official docs
│   ├── VIDRUSH_CLONE_PLAN.md    # architecture v3
│   ├── PROJECT_FACTORY.md       # projects/<series>/Ep*.md autonomous runbook
│   ├── PRO_EDIT_STYLE.md        # editorial motion rules (AE/Premiere, not web)
│   └── STYLE_GUIDE.md           # user-facing: pick/tune/extend styles
├── pipeline/
│   ├── intelligence/
│   │   ├── styles/              # crime/history/modern/minimalist/standard JSONs
│   │   ├── select_style.py      # brief → global_style (scoring, aliases)
│   │   ├── brief_template.py    # VidRush-format prompt (Style:/Tone: last)
│   │   ├── lint_skill_output.py # banned-editing-words linter
│   │   ├── skills/              # 01_script_writer … 05_video_prompt (style-aware)
│   │   └── timeline_schema.json # global_style field
│   ├── assets/                  # vo.py, stock.py, imagegen.py, cache
│   ├── audio/                   # mix, loudnorm
│   ├── config/                  # vo.json (custom TTS), pipeline.json
│   ├── examples/
│   ├── projects.py              # Ep*.md discovery + tracker.md state (resumable factory)
│   └── orchestrator.py          # --brief / --timeline / --style
├── projects/                    # one folder per series: Ep1.md, Ep2.md… + tracker.md
├── remotion/src/
│   ├── components/              # styleSystem.ts, SceneShell, AeType, editMotion, tokens, choreo
│   ├── components/effects/      # fonts, grade, Grain, camera, transitions, typography, drawOn, mediaSlots
│   ├── scenes/                  # intro/content/stat/quote/list/comparison/person/outro
│   └── render.js                # batch renderMedia + xfade + NVENC
└── output/
```

## FX & Motion System (components/effects/)

Per-style identity is built from these layers (all research-backed — see `docs/AE_TRENDS_CATALOG.md`, `docs/REMOTION_AE_TECHNIQUES.md`, `docs/FREE_MOTION_ASSETS.md`):

| Module | What it provides |
|--------|-----------------|
| `fonts.ts` | Per-style type: crime=Anton+PlexMono, history=Newsreader+SpaceMono, modern=Archivo+Inter, minimalist=WorkSans, standard=Archivo+Inter (via `@remotion/google-fonts`) |
| `textSkin.ts` | **Per-style text grammar** (replaces the one shared black plate): crime=dossier plate+mono stamp, history=archival parchment plate+double-rule+serif smallcaps, modern=chip/no plate+accent highlight, minimalist=bare (no plate), standard=soft translucent plate. `LowerThirdPlate`/`Label` read it via `textSkinFor`/`plateStyle`/`kickerStyle` |
| `grade.ts` | Per-style color look: crime silver-desat, history warm sepia, modern teal punch, minimalist neutral bright (CSS filter chains — no canvas cost) |
| `Grain.tsx` | **Animated** procedural grain (feTurbulence re-seeded per frame, deterministic) — replaces the old static tile |
| `camera.ts` | `cameraDrift` (noise3D handheld), `cameraShake` (decaying impulse), `punchZoom` (whole-frame beat accent) — all seeded/deterministic |
| `transitions.tsx` | `CutLeak` (`@remotion/light-leaks` WebGL leak masking scene cuts, under the FFmpeg xfade) + `whipIn` |
| `typography.tsx` | `MaskLineReveal` (per-line rise, THE documentary entrance), `WordPop` (per-word VO beats), `TrackingTitle` (letter-spacing settle) |
| `drawOn.tsx` | `DrawOnUnderline`, `DrawOnCircle` via `@remotion/paths` `evolvePath` (stroke-dashoffset draw-on) |
| `mediaSlots.tsx` | **Role-based multi-asset layering:** `midground[]` (parallax cutouts), `foreground[]` (polaroid cards), `overlay` (blend-mode texture). Depth convention: mid 0.4/0.7, fg 1.0. |

**Per-style motion vocab** lives in `tokens.ts` (`motionVocab`): tempo, drift, max_shake (ceiling), punch, grain, cutLeak, titleMode, accentMode. Scenes read vocab — they never set easings directly. AE easing curves (`AE_EASE`, `AE_SNAP`, `AE_SETTLE`) are tokens; `Easing.linear` stays default for editorial wipes.

## Layout & Genre Engine (Phase 6)

| Module | What it provides |
|--------|-----------------|
| `components/layout.ts` | **Single placement authority.** Rule-of-thirds grid + 5% text-safe zone. `resolvePlacement(intent)` → hero/editorial/sidebar/float anchors; `distributeAssets()` computes slot positions so assets never collide with text. |
| `components/genreArcs.ts` | **Story grammar per script format** (separate from visual style). `arcFor(format)` → documentary/news/essay/listicle/explainer; each arc = ordered beats (context→evidence→reveal…), energy curve, text density. `beatForScene()` paces the director. |
| `effects/typography.tsx` | `breakLines()` auto word-wrap (no manual `\n`), `fontSizeFor()` responsive size, placement intents on all type components. |

**Shake is opt-in per scene** (`shake` prop, capped by style `max_shake`) — never a style default. **Background drift/shake on stills is OFF** (user rejected — headache); a `bg_image` still instead gets ONE smooth deliberate move via **`still_motion`** (`push` default / `pan` / `parallax` / `light` / `hold`-artifact-only), rendered as a visible eased Ken Burns (`vocab.stillKen`) or a living-light layer — never jittery `cameraDrift`. `validate_still_motion` warns on an unjustified `hold`. **Text presence is the director's judgment** (`bare` layout when VO carries the beat). Placement/asset positions are **computed by the layout engine**, never hardcoded.

**VO-first timing (Ep1 pilot fix):** after script, run `python -m pipeline.vo_plan --script <script.md> --output <vo_plan.json>`. This separate stage synthesizes the whole script up front → measured per-paragraph durations + cached audio + word_times. Director consumes that plan and writes those fields into scenes. Orchestrator never synthesizes VO; it only validates external metadata and applies `stage_retime_to_vo`. **Footage-only (silent) beats** — omit `vo_text`, set `intent:"footage"`, a real video bg (`bg_video`/`gen_kind video`), director-set `duration`; the music bed swells in the gap (sidechain recovers). `validate_footage_beats` warns on a silent still or over-use (~1 in 5 cap).

**Runtime gate:** measured total VO must be 8:00–20:00 (`480–1200s`) before asset resolution. Outside range means rewrite and re-synthesize script; never pad picture to fake runtime. **Generated-image ceiling:** at most six comma-separated parts and 55 words: one subject, action/pose, setting, period, simple light, one medium. No complex crowds, conflicting media, or generated text/documents; Remotion owns labels and data.

**Visual-variety gate:** one still/plate may not carry more than 12 seconds of measured VO by itself. Split long narration into new motivated scenes with distinct assets; after an establishing still, prefer real footage where available. A layered still with meaningful `midground`/`foreground` or an explicit `asset_sequence` may span longer. Never duplicate one image across splits. `validate_long_stills` reports violations after assets resolve.

**Execution boundary:** GitHub Actions is CPU-only Remotion clip rendering. It never runs NVENC, local footage processing, transitions, audio, or final assembly. Local RTX 3060 owns supported CUDA normalization/compositing experiments and NVENC output; CPU `xfade` remains fallback until a measured Vulkan path is faster. Optimize wall time, not GPU percentage; compatible hard cuts use stream copy.

**Motivated editing** — the director follows `docs/EDITING_DECISIONS.md` (Murch's Rule of Six: emotion 51% / story 23% / rhythm 10%; cut-vs-hold, eye-trace, transition logic, text reading-time). Every scene must justify itself. Orchestrator validates text reading time (`validate_reading_time`).

**Multi-asset scenes:** skills pass `midground`/`foreground`/`overlay` arrays in scene props; `SceneShell` renders the layer stack. `render.js` injects `scene_seed` per scene so noise differs scene-to-scene.

## Core Principles

1. **Per-project custom style** — when a project's audit doc (e.g. `projects/<series>-vidiq.md`) specifies a visual formula, create `pipeline/intelligence/styles/<project>.json` next to the five platform themes, register its id in `select_style.STYLE_IDS`, `timeline_schema.json` enums, `remotion/.../styleSystem.ts` (`GlobalStyleId`, `STYLES`), `fonts.ts`, `tokens.ts`, `effects/textSkin.ts`, `effects/grade.ts`. Set `source` to the audit path. The platform five never move; per-project styles inherit editorial constraints (linear easings, `spring_allowed:false` outside modern).
2. **Prompt = WHAT, Theme = HOW** — skills emit content/structure/words, never editing instructions; the style JSON owns all motion and visuals (VidRush prompting guide)
3. **Global style drives everything** — one choice (`crime|history|ledger|modern|minimalist|standard`) flows to script density/rhythm, VO tone, palette/typography, transitions, B-roll mood (VidRush themes doc + per-project audits)
4. **Research-traceable values** — every style parameter traces to `docs/GLOBAL_STYLE_RESEARCH.md`, the project's audit doc (e.g. `vidiq_audit:projects/american-ledger-vidiq.md`), or is explicitly flagged as a design decision
5. **Editorial motion only** — `Easing.linear`, mask wipes, opacity cuts, plate lower-thirds; banned: word stagger, scale pop, glow pills, glass cards, UI beziers (`docs/PRO_EDIT_STYLE.md`)
6. **GPU-first local assembly** — GitHub renders Remotion clips; local FFmpeg handles footage, xfade, audio, and NVENC final. No single long Chrome render
7. **~0.5 talking points per minute** — script density rule from VidRush prompt guide
8. **Project style + packaging contract** — per-project custom styles live alongside the platform five; episode briefs declare `global_style:` and a packaging block (title formula with concrete number, hook with figures in first 10s, one focal object thumbnail rule). Channel niche stays put; audits tune packaging only.

## Key Design Decisions

- **Global styles** = VidRush's 5 themes mirrored as JSON (`pipeline/intelligence/styles/`) **plus per-project styles** (e.g. `ledger.json` for american-ledger, tracing to `vidiq_audit:projects/american-ledger-vidiq.md`); tie/unclear briefs → `standard`
- **Legacy style names** (`documentary`, `storytelling`, `listicle`, `explainer`, `commentary`) = aliases → the five canonical styles
- **Transitions** = FFmpeg xfade in batch mode; **one xfade type per style** (type + frames from style JSON); `<TransitionSeries>` deferred (needs one long Chrome render)
- **Springs** = only in `modern` stat reveals, `overshootClamping: true`; everything else linear
- **VO** = per-line synthesis, SHA256 cache (`text+voice+provider+model`), user-configured custom provider only
- **B-roll** = three routes, set once via top-level `asset_mode` in the timeline (per-scene `broll.source` overrides); **default is `auto`**: **Path C `auto` (default)** = the pipeline auto-fills — image beats → ModelScope (`choose_image_model`: Z-Image default photoreal/bilingual @1536×864, Krea-2-Turbo for stylized/LoRA @1280×720, async submit+poll, SHA cache), video beats → the Path A stock search; **Path A `stock`** = director keyword → Pexels → Pixabay top match ≥1080p → normalize (scale_cuda 1920x1080, trim); **Path B `generated`** = user AI-generates assets and drops them in `assets/in/scene_XX.*` (`broll.gen_kind`: `image` still→loop, `image_video` still+motion, `video` clip). Either route, on a miss → **never abort**: print the 04/05 prompt, fall back to a style-colour plate, flag `needs_manual_asset`. `--skip-stock` skips only the *online stock search* — local/generated/auto stills + plate fallback still run
- **Project factory** = `projects/<series>/Ep*.md` briefs + `tracker.md` state; agents process episodes autonomously and resume at `next_stage()`. See `docs/PROJECT_FACTORY.md`
- **Audio** = `sidechaincompress` duck + two-pass `loudnorm`; YouTube target -14 LUFS / -1 dBTP
- **Style values marked `design_decision`** (frame counts, darken, ken-zoom) are ours from `PRO_EDIT_STYLE.md`, not platform-documented — never cite them as VidRush values

## Commands

```bash
# Full pipeline (auto style)
python -m pipeline.orchestrator --brief "The rise and fall of Theranos"

# Override style
python -m pipeline.orchestrator --brief "..." --style crime

# From existing timeline
python -m pipeline.orchestrator --timeline pipeline/examples/timeline_local_assets.json

# Thermal relief: pause between scene renders (CPU breath) + cap parallel Chrome bursts
python -m pipeline.orchestrator --timeline <file> --scene-pause 3 --concurrency 2

# Remotion batch render directly
cd remotion && node src/render.js --batch manifest.json --scene-pause 3 --concurrency 2

# Python unit tests (style selection, template, linter, orchestrator)
pytest tests/ -v

# Style lookup / debug
python -m pipeline.intelligence.select_style --brief "..." --json
```

## Coding Conventions

- Python: type hints on public functions, `async` for I/O, FFmpeg commands as `list[str]` (never shell strings)
- Remotion/TS: all motion via `editMotion.ts` / `styleSystem.ts` — **no ad-hoc springs or easings in scene files**
- Time values in seconds (float) at pipeline level; frames only inside Remotion components
- Style JSON changes require a source citation or `design_decisions` flag update
- Cache keys: SHA256 of canonical JSON (sorted keys), 16 hex chars display
- Env secrets (`VO_API_KEY`, `PEXELS_API_KEY`, `PIXABAY_API_KEY`, `MODELSCOPE_API_KEY`) — never committed
- **Persistent API keys live in `docs/API/*.md`** (gitignored): `pexel.md`, `pixabay.md`, `modelscope.md`. These are the canonical key store across the whole project — `pipeline/__init__.py` reads them on import (`_key_from_md` extracts the token), injects them into `os.environ`, and rewrites `.env` to match. A real exported env var still wins. To rotate a key, edit the `docs/API/*.md` file only.

## Platform Loudness Targets

- YouTube: -14 LUFS, -1 dBTP
- Podcast: -16 LUFS, -1.5 dBTP
- Broadcast: -23 LUFS, -2 dBTP
