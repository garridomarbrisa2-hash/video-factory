# Vidrush Clone — Build Plan v3

**v3.0 — 2026-07-22.** Global style system, research-backed.
**Evidence base:** `docs/GLOBAL_STYLE_RESEARCH.md` (VidRush + Remotion official docs, competitors).
**Execution plan:** `Implementation-Plan.md` v3 | **Progress:** `Implementation-Tracker.md`.

Local-first vidrush.ai clone. Heavy GPU, minimal CPU. Style-driven: **brief → global style → script → VO → footage → render.**

---

## 1. Goal

Pipeline takes a **brief/topic** and produces a finished long-form video (60s–10min) with:
- AI-written script whose **pacing and rhythm follow the selected global style**
- AI voiceover (TTS via user-configured API) whose **tone follows the style**
- Stock or manual B-roll (full-bleed, every scene) in the **style's visual mood**
- Kinetic typography + motion graphics in the **style's motion grammar** (Remotion)
- GPU-encoded final (NVENC, 12+ Mbps, 1080p30)

No empty backgrounds. No AI-slop stills. No CPU-bound final encode. No web-UI motion.

---

## 2. The Global Style System (new in v3)

### What VidRush does (official)

VidRush separates two layers — and so do we:

| Layer | Owns | VidRush source |
|-------|------|----------------|
| **Prompt/script** | WHAT: talking points, structure, tone words, hook lines | Prompting guide |
| **Theme** | HOW: fonts, colors, animations, text overlays, graphics, transitions | Themes doc |

VidRush ships 5 themes: **Crime, History, Modern, Minimalist, Standard**. We mirror them 1:1 as global styles (`crime`, `history`, `modern`, `minimalist`, `standard`), each a JSON file in `pipeline/intelligence/styles/` defining: script pacing rules, VO tone, visual palette/typography, motion grammar (transition type + frames), B-roll mood, and allowed/banned Remotion components.

### Style selection

LLM reads the brief → scores against each style's `topic_keywords` + format words → picks one. Tie or unclear → `standard` (VidRush: "if you're unsure, start here"). User override: `--style`.

### Style flows through everything

```
global_style ──► 01_script_writer (density ~0.5 pts/min, rhythm, hook form)
             ──► 02_director      (b-roll keywords, scene mix, min scene length)
             ──► 03_voiceover     (pace, pause markers, voice hint)
             ──► timeline.json    (global_style field)
             ──► styleSystem.ts   (motion params → components)
             ──► render.js        (xfade transition type + frames)
```

Full mapping tables (per-style transitions, palettes, VO energy, component matrix) are in `docs/GLOBAL_STYLE_RESEARCH.md` §3–4. **All style values must trace to that file or be flagged as design decisions.**

---

## 3. Architecture (3 Layers)

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1 — INTELLIGENCE (Claude + Skills + Styles)          │
│  Input:  brief/topic                                        │
│  Output: timeline.json (script + scenes + global_style)     │
│                                                             │
│  0. select_style  → global_style + styles/<id>.json         │
│  1. script-writer → script.md (style density + rhythm)      │
│  2. director      → scenes, B-roll keywords (style mood)    │
│  3. voiceover     → vo_text, style pause markers            │
│  4. (opt) image/video-prompt on stock miss                  │
│                                                             │
│  Skills emit WHAT, never HOW (no editing instructions).     │
└──────────────────┬──────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2 — ASSET PIPE (async, GPU)                          │
│  a) VO gen  → custom TTS (adapter), per-line, SHA-cached    │
│  b) B-roll  → Pexels/Pixabay, top match ≥1080p MP4          │
│  c) Miss    → print prompt, user drops assets/in/scene_XX   │
│  d) Normalize → FFmpeg scale 1920x1080, trim, cache by hash │
└──────────────────┬──────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3 — RENDER (GPU, batch, style-aware)                 │
│  - styleSystem.ts reads styles/<id>.json                    │
│  - Per-scene renderMedia (short Chrome bursts)              │
│  - SceneShell: full-bleed B-roll + style grade              │
│  - NVENC per clip; FFmpeg xfade chain (type from style)     │
│  - Audio: VO + music, sidechain duck, 2-pass loudnorm       │
│  - Final NVENC p6/hq ~12 Mbps                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Voiceover — Pluggable API Adapter

**Custom only.** `pipeline/config/vo.json` — `custom_http` / `custom_cli` with `VO_API_KEY`. No baked-in provider default. Per-line synthesis → precise `vo_start`; cache by `SHA256(text+voice+provider+model)`; user-defined fallback chain. Style JSON supplies `voice_hint` + pause markers; the VO skill applies them.

---

## 5. Handoff Format — `timeline.json`

```json
{
  "title": "Why 3I/ATLAS Isn't What NASA Says",
  "global_style": "crime",
  "vo_config": "config/vo.json",
  "music": "dark_tension.mp3",
  "music_duck_db": -12,
  "loudness_target_lufs": -14,
  "scenes": [
    {
      "id": 0,
      "type": "intro",
      "duration": 4.0,
      "vo_text": "The official story doesn't add up.",
      "vo_start": 0.2,
      "voice": "deep_calm",
      "broll": {"keyword": "night telescope observatory", "source": "pexels"},
      "props": {"hook_text": "The Official Story", "bg_video": "pexels_12345.mp4"}
    }
  ]
}
```

`global_style` enum: `crime | history | modern | minimalist | standard`. Legacy values (`documentary`, `storytelling`, `listicle`, `explainer`, `commentary`) accepted as aliases → mapped to the five.

---

## 6. Stock Footage

| Source | Key | Notes |
|--------|-----|-------|
| Pexels Video | `PEXELS_API_KEY` (user) | Primary, 1080p MP4 |
| Pixabay Video | `PIXABAY_API_KEY` (user, optional) | Backup |

Director emits keywords **in the style's b-roll mood** (e.g. crime → "night city", "evidence", "archive footage"). 0 results → `fallback_prompt` printed for MJ/SDXL/Runway → user drops into `assets/in/scene_{id}.{ext}`.

---

## 7. Render: Transition Mapping (Remotion research)

Batch mode = per-scene clips + **FFmpeg xfade** (not `<TransitionSeries>` — that needs one long Chrome render, the CPU bottleneck we avoid). Style JSON picks from the mapped set:

| Style | xfade | Frames |
|-------|-------|--------|
| crime | `fadeblack` | 12 |
| history | `dissolve` / `circleopen` (chapters) | 12–15 |
| modern | `wipeleft` / `slideleft` | 8–10 |
| minimalist | `fade` or hard cut | 8–12 |
| standard | `fade` / `dissolve` | 10 |

In-scene: `Easing.linear` everywhere; `spring()` only in `modern` stats with `overshootClamping`. Banned: word stagger, scale pop, glow pills, glass cards (see `docs/PRO_EDIT_STYLE.md`).

---

## 8. GPU Budget (RTX 3060 12GB, 60s video)

| Task | GPU | Time |
|------|-----|------|
| Asset normalize | CUDA | ~5s |
| Remotion batch (per scene) | CPU raster (short bursts) | ~60–90s |
| xfade concat | CPU xfade + NVENC | ~10s |
| Audio mix + loudnorm | CPU | ~15s |
| Final NVENC p6/hq | NVENC | ~7s |
| **Total** | | **~2 min** |

---

## 9. Repo Structure

```
├── pipeline/
│   ├── intelligence/
│   │   ├── styles/              # crime/history/modern/minimalist/standard .json
│   │   ├── select_style.py
│   │   ├── skills/ (01–05)      # style-aware
│   │   └── timeline_schema.json # global_style
│   ├── assets/ (vo.py, stock.py, vo_providers/, cache/)
│   ├── audio/ (mix.py, loudnorm.py)
│   ├── render/ → calls remotion/src/render.js --batch
│   ├── config/ (vo.json, pipeline.json)
│   └── orchestrator.py          # --brief / --timeline / --style
├── remotion/src/
│   ├── components/styleSystem.ts
│   ├── components/{SceneShell, AeType, editMotion}
│   ├── scenes/ (8 scene types)
│   └── render.js                # batch + xfade + NVENC
├── docs/
│   ├── GLOBAL_STYLE_RESEARCH.md # evidence base
│   ├── VIDRUSH_CLONE_PLAN.md    # this file
│   └── PRO_EDIT_STYLE.md        # editorial rules
└── output/
```

---

## 10. Build Order (YAGNI)

1. Style JSONs ×5 + `select_style.py` + schema `global_style`
2. Skills updated to read style constraints
3. `styleSystem.ts` + `editMotion` + `SceneShell` grade + render.js xfade map
4. Orchestrator `--brief`/`--style` + validation
5. Real keys + full run + STYLE_GUIDE.md

### Skip for v1
- Runway/Sora API video gen, Coverr scrape, multi-language VO, thumbnail gen, `<TransitionSeries>` single-render mode, WebGL renderer.

---

## 11. Comparison to VidRush

| Feature | VidRush | This clone |
|---------|---------|------------|
| Themes | 5 (Crime/History/Modern/Minimalist/Standard) | Same 5, JSON-defined, extensible |
| Script | AI (style/tone from prompt) | AI (style JSON drives density + rhythm) |
| VO | Their TTS | User-configured (any TTS) |
| B-roll | Stock + AI | Stock + AI prompts + manual |
| Render | Cloud | Local Remotion + NVENC |
| Cost/video | Subscription | $0 + TTS cost |
| Speed | ~3–5 min | ~2 min (60s) |
| Quality | 1080p 8–12 Mbps | 1080p 12–16 Mbps |

---

## 12. Decisions (locked)

| Question | Decision |
|----------|----------|
| Global styles | VidRush's 5 themes, mirrored: `crime`, `history`, `modern`, `minimalist`, `standard` |
| Style ownership | Script layer picks style (from brief); style JSON owns all visual/motion decisions |
| Old style names | Legacy aliases → 5 canonical styles |
| Transitions | FFmpeg xfade in batch mode; `<TransitionSeries>` deferred |
| Default TTS | Custom only (`custom_http`/`custom_cli`), user fills `pipeline/config/vo.json` |
| Stock keys | User env: `PEXELS_API_KEY`, optional `PIXABAY_API_KEY` |
| Music | Bundle royalty-free under `pipeline/assets/music/` |
| Skill files | AI Labs script-writer + Luke Robins 7-Skill, combined, style-aware |
| Style values | Must trace to `docs/GLOBAL_STYLE_RESEARCH.md` or be flagged as design decisions |
