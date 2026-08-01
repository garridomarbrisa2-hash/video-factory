# Vidrush-Style Local Pipeline — Implementation Plan

**Version:** 3.0 (research-backed rewrite)
**Date:** 2026-07-22
**Status:** Ready for implementation
**Research basis:** `docs/GLOBAL_STYLE_RESEARCH.md` — VidRush official docs, Remotion official docs, 4 competitor platforms. Every style decision must trace to that file or be flagged as an open design value.

> **Supersedes:** the old FFmpeg-MCP server plan (v1) and the v2 draft written before research. Old `src/`, `tests/`, `scripts/`, `pyproject.toml` have been deleted.

---

## 1. What We're Building

A local vidrush.ai-style factory: **brief → global style selection → skill-chained script → custom VO → stock/manual B-roll → Remotion batch render → NVENC final.**

The core new system: **Global Style Templates** that mirror VidRush's five official themes (Crime, History, Modern, Minimalist, Standard — [docs.vidrush.ai/docs/themes](https://docs.vidrush.ai/docs/themes)). The LLM picks one style from the topic/brief; that single choice deterministically drives:

1. **Script pacing** (talking-points density, sentence rhythm, hook form) — per VidRush prompt guide
2. **VO tone** (pace, pause markers, voice energy) — per VidRush reference-video docs
3. **Visual theme** (palette, typography, text animation, transitions) — the theme's job per VidRush themes doc
4. **B-roll mood** (keyword framing, grade) — per VidRush footage-matching guidance

### Core principles (from research)

| # | Principle | Source |
|---|-----------|--------|
| 1 | **Prompt = WHAT, theme = HOW.** Skills never emit editing instructions; style JSON owns all motion | VidRush prompt guide |
| 2 | **~0.5 talking points per minute** of target video | VidRush prompt guide |
| 3 | **Style/Tone declared at brief end**, then propagated to every layer | VidRush prompt guide |
| 4 | **Script rhythm is a writing decision; visuals are a theme decision.** Keep them in separate layers | VidRush reference-video docs |
| 5 | A style = **{typography set, palette, text animation, transition design, pacing rules}** | Cross-platform convergence (Pictory/InVideo/OpusClip) |
| 6 | **Editorial motion = linear.** Springs/overshoot banned except clamped stats in `modern` | `docs/PRO_EDIT_STYLE.md` |
| 7 | **GPU-first assembly**: per-scene Remotion clips + FFmpeg xfade + NVENC | Existing render.js (kept) |

---

## 2. Architecture

```
┌────────────────────────────────────────────────────────────────┐
│ LAYER 1 — INTELLIGENCE                                         │
│                                                                │
│ brief ──► select_style.py ──► global_style (crime|history|     │
│                               modern|minimalist|standard)      │
│                               loads styles/<id>.json           │
│                                                                │
│ Skills chain (style-aware):                                    │
│   01_script_writer → talking points at style density + rhythm  │
│   02_director      → scenes + b-roll keywords in style mood    │
│   03_voiceover     → vo_text with style pause markers          │
│   04/05 prompts    → only on stock miss                        │
│                                                                │
│ OUTPUT: timeline.json (global_style + scenes)                  │
└──────────────────────────┬─────────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────────┐
│ LAYER 2 — ASSET PIPE                                           │
│   VO     → custom TTS adapter (config/vo.json), per-line,      │
│            SHA-cached                                          │
│   B-roll → Pexels/Pixabay keyword search → 1080p download →    │
│            FFmpeg normalize (scale 1920x1080, trim)            │
│   Miss   → assets/in/scene_XX.* manual drop or printed prompt  │
└──────────────────────────┬─────────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────────┐
│ LAYER 3 — RENDER (GPU batch)                                   │
│   styleSystem.ts reads styles/<id>.json → motion params        │
│   Per-scene renderMedia (short Chrome bursts) + NVENC clip     │
│   FFmpeg xfade chain (transition type FROM style JSON)         │
│   Audio: VO + music, sidechaincompress duck, 2-pass loudnorm   │
│   Final: NVENC p6/hq ~12 Mbps 1080p30                          │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. Global Style Template System

### 3.1 Style JSON schema (`pipeline/intelligence/styles/<id>.json`)

Every field traces to research (`docs/GLOBAL_STYLE_RESEARCH.md` §3) or is marked `design_decision: true`:

```json
{
  "style_id": "crime",
  "name": "Crime",
  "source": "vidrush_theme:Crime",
  "topic_keywords": ["true crime", "mystery", "investigation", "conspiracy", "cold case"],
  "script": {
    "talking_points_per_min": 0.5,
    "format": "mystery_investigation",
    "sentence_rhythm": "measured, long pauses, em-dash breaks",
    "hook_form": "question or cold-open statement",
    "tone_words": ["suspenseful", "mysterious", "compelling"]
  },
  "vo": {
    "pace": "measured",
    "energy": "low_intense",
    "pause_markers": ["—", "..."],
    "voice_hint": "deep, calm, serious"
  },
  "visual": {
    "palette": {"bg": "#0a0a0c", "text": "#f2f2f2", "accent": "#c0392b"},
    "typography": {"family": "condensed grotesque or dramatic serif", "weight": 700, "tracking": "tight"},
    "title_animation": "mask_wipe_slow",
    "lower_third": "plate_slide_linear",
    "stat_reveal": "opacity_cut_3f",
    "grade": {"darken": 0.6, "vignette": "strong", "grain": 0.04}
  },
  "motion": {
    "transition": {"xfade": "fadeblack", "frames": 12},
    "ken_burns_zoom": 1.05,
    "wipe_frames": 12,
    "plate_frames": 12,
    "hard_titles": false,
    "allowed_easings": ["linear"],
    "spring_allowed": false
  },
  "broll": {
    "keywords": ["night city", "evidence", "archive footage", "interrogation", "crime scene"],
    "avoid": ["bright daylight lifestyle", "cheering crowds"],
    "preferred_sources": ["pexels"]
  },
  "design_decisions": ["transition.frames", "grade.darken", "ken_burns_zoom", "wipe_frames", "plate_frames"]
}
```

### 3.2 The five styles (research-mapped)

| Style ID | VidRush theme | Formats (prompt templates) | Transition (xfade) | Palette mood | VO energy |
|----------|---------------|---------------------------|--------------------|--------------|-----------|
| `crime` | Crime | Mystery/Investigation | `fadeblack` 12f | near-black + red accent | low, intense, long pauses |
| `history` | History | Documentary | `dissolve` 12–15f, `circleopen` for chapters | sepia/parchment + muted gold | authoritative, measured |
| `modern` | Modern | Crisis/News, tech | `wipeleft`/`slideleft` 8–10f | dark slate + vibrant accent | energetic, confident, Vox-style |
| `minimalist` | Minimalist | Corporate/educational | `fade` 8–12f or hard cut | light/neutral + one accent | calm, formal |
| `standard` | Standard | Top-10/Listicle, general | `fade`/`dissolve` 10f | neutral dark + #ff6b35 | adaptable; countdown energy for listicles |

Legacy aliases: `documentary→history`, `storytelling→standard`, `listicle→standard`, `explainer→minimalist`, `commentary→modern`. Old timelines keep working.

### 3.3 Style selection (`pipeline/intelligence/select_style.py`)

1. Score brief against each style's `topic_keywords` (+ format words: "top 10"→standard, "investigation"→crime, "history of"→history, "how to"→minimalist).
2. Highest score wins; tie → `standard` (VidRush: "if unsure, start here").
3. `--style` flag always overrides.

---

## 4. Remotion Capability Mapping (official docs)

From `@remotion/transitions` (installed, v4) and `remotion` core — see research doc §2 for the full 17-presentation table and `<TransitionSeries>` rules.

**Assembly decision (kept from current build):** scenes render as individual clips via `renderMedia`, joined by **FFmpeg xfade** whose type/duration come from `style.motion.transition`. `<TransitionSeries>` is NOT used in batch mode (it requires a single long Chrome render — the CPU bottleneck we're avoiding). This is an explicit trade-off: xfade covers our five needed transition feels (none/fade/dissolve/wipe/slide/fadeblack/circleopen).

**In-scene animation:** `spring()` only in `modern` stat reveals with `overshootClamping: true`; everything else `interpolate()` + `Easing.linear` per `PRO_EDIT_STYLE.md`.

**Style → component constraints:**

| Component | crime | history | modern | minimalist | standard |
|-----------|-------|---------|--------|------------|----------|
| `SceneShell` (Ken Burns b-roll) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `MaskWipe` titles | ✅ slow | ✅ slow | ✅ fast | ✅ subtle | ✅ |
| `OpacityCut` (2–6f) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `LowerThirdPlate` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `StaticType` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Clamped-spring stat pop | ❌ | ❌ | ✅ | ❌ | ❌ |
| KineticWords / FadeUp / GlowPill | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 5. Skills Synergy (style-aware)

| Skill | Reads from style JSON | Produces |
|-------|----------------------|----------|
| `01_script_writer` | `script.talking_points_per_min`, `format`, `sentence_rhythm`, `hook_form`, `tone_words` | script.md with correct density/rhythm; ends with `Style:`/`Tone:` lines |
| `02_director` | `broll.keywords`, `broll.avoid`, `visual.title_animation` (scene-type mix), `motion.transition.frames` (min scene length) | scenes.json + per-scene b-roll keyword |
| `03_voiceover` | `vo.pace`, `vo.energy`, `vo.pause_markers`, `vo.voice_hint` | vo_script.json with markers + voice pick |
| `04/05 prompts` | `broll.keywords` framing rules | MJ/SDXL/Runway prompts on stock miss |

**Hard rule (VidRush):** skills emit WHAT (content, structure, words); never HOW (transitions, animations). Any editing instruction found in skill output is a bug.

---

## 6. Implementation Phases

### Phase 1 — Style foundation
- [ ] `pipeline/intelligence/styles/` + 5 style JSONs per §3 schema
- [ ] `select_style.py` (keyword scoring + override)
- [ ] `timeline_schema.json`: `global_style` enum → `crime|history|modern|minimalist|standard` (+ legacy aliases)
- [ ] Unit test: 10 briefs → expected styles

**Milestone:** style selection works, style JSONs validate.

### Phase 2 — Skills integration
- [ ] Update 3 core skill files to read style constraints (sections in §5)
- [ ] Orchestrator brief template appends `Style:`/`Tone:` from style JSON
- [ ] Integration test: brief → style → script → scenes → timeline.json

**Milestone:** skills produce style-consistent timelines.

### Phase 3 — Remotion style system
- [ ] `remotion/src/components/styleSystem.ts` — load style JSON (bundled at build), expose `getGlobalStyle()`
- [ ] `editMotion.ts` → style-driven params (replaces hardcoded `styleParams()` switch)
- [ ] `SceneShell` grade params (darken/vignette/grain) from style
- [ ] `render.js` reads `global_style` from manifest → picks xfade type + per-scene props
- [ ] Visual A/B: same script in `crime` vs `modern` renders visibly different

**Milestone:** one timeline, two styles, two visibly different videos.

### Phase 4 — Orchestrator end-to-end
- [ ] `orchestrator.py --brief "..."` auto-selects style; `--style` overrides
- [ ] Style consistency validation (scene min-length ≥ transition frames × 2; allowed components only)
- [ ] E2E test on `pipeline/examples/`

**Milestone:** brief → final MP4 with correct style, one command.

### Phase 5 — Polish + docs
- [ ] VO/stock with real keys, full non-skipped run
- [ ] `docs/STYLE_GUIDE.md` (user-facing: how to pick/extend styles)
- [ ] Update AGENTS.md, Implementation-Tracker.md

**Milestone:** production-ready.

---

## 7. File Structure

```
ffmpeg-mcp/
├── AGENTS.md                        # rewritten (pipeline overview)
├── Implementation-Plan.md           # this file
├── Implementation-Tracker.md        # new phase tracker
├── docs/
│   ├── GLOBAL_STYLE_RESEARCH.md     # evidence base (done)
│   ├── VIDRUSH_CLONE_PLAN.md        # upgraded to v3
│   └── PRO_EDIT_STYLE.md            # editorial rules (kept)
├── pipeline/
│   ├── intelligence/
│   │   ├── styles/                  # NEW: 5 style JSONs
│   │   ├── select_style.py          # NEW
│   │   ├── skills/                  # UPDATED: style-aware
│   │   └── timeline_schema.json     # UPDATED: global_style
│   ├── assets/ (vo.py, stock.py)    # kept
│   ├── audio/                       # kept
│   ├── config/ (vo.json, pipeline.json)
│   ├── examples/
│   └── orchestrator.py              # UPDATED: --brief/--style
└── remotion/src/
    ├── components/styleSystem.ts    # NEW
    ├── components/editMotion.ts     # UPDATED
    ├── components/SceneShell.tsx    # UPDATED: style grade
    ├── scenes/                      # UPDATED: style props
    └── render.js                    # UPDATED: style → xfade
```

---

## 8. Risks

| Risk | Mitigation |
|------|-----------|
| Style JSONs drift from research | Every field needs `source` or `design_decisions` flag (enforced in review) |
| xfade can't express a transition a style wants | Constrain styles to the 7 mapped xfade types; revisit single-render mode only if user demands |
| LLM mis-selects style | `--style` override; log scores; tune keywords with real briefs |
| Skills leak editing instructions | Validation step: reject skill output containing banned motion words |
| Old timelines break | Legacy alias mapping in schema + styleSystem |

---

## 9. Success Criteria

- [ ] 5 styles defined, each field traced to research or flagged
- [ ] Style selection ≥90% agreement with human pick on 10 test briefs
- [ ] Same script × 2 styles = visibly different pacing/transitions/grade
- [ ] One-command E2E: `python -m pipeline.orchestrator --brief "..." → output/*.mp4`
- [ ] Zero editing instructions in any skill output (linter)

---

## 10. Citations

See `docs/GLOBAL_STYLE_RESEARCH.md` §6 (10 sources: VidRush ×3, Remotion ×3, Pictory, InVideo, OpusClip, Lumen5).
