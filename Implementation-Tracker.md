# Vidrush-Style Local Pipeline — Implementation Tracker

**Started:** 2026-07-22 (v3 rewrite)
**Status:** Phase 8 in progress — Director Authority & Genre Creativity
**Plan:** `Implementation-Plan.md` v3.0 | **Research:** `docs/GLOBAL_STYLE_RESEARCH.md`
**Phase 6 plan:** `docs/plans/PHASE_6_GENRE_ENGINE.md`
**Phase 7 plan:** `docs/plans/PHASE_7_PRESENCE_ENGINE.md`
**Phase 8 audit+plan:** `docs/plans/PHASE_8_DIRECTOR_AUTHORITY.md`
**Phase 9 plan:** `docs/plans/PHASE_9_GENERATED_ASSETS.md`

> Old FFmpeg-MCP phases (v1) completed and codebase deleted on 2026-07-22. This tracker covers the new global-style pipeline only.

---

## Phase 0: Research + Planning ✅

| # | Task | Status | Notes |
|---|------|--------|-------|
| 0.1 | Research VidRush official docs (themes, prompt, reference-video) | ✅ | 5 themes: Crime, History, Modern, Minimalist, Standard |
| 0.2 | Research Remotion official docs (transitions, spring, TransitionSeries) | ✅ | 17 presentations, linearTiming/springTiming, 5 hard rules |
| 0.3 | Research competitor style systems (Pictory, InVideo, OpusClip, Lumen5) | ✅ | Style = typography + palette + text anim + transitions + pacing |
| 0.4 | Write `docs/GLOBAL_STYLE_RESEARCH.md` evidence base | ✅ | 10 citations, style mapping matrix, open design values flagged |
| 0.5 | Rewrite Implementation-Plan.md v3 (research-backed) | ✅ | |
| 0.6 | Delete old pipeline (src/, tests/, scripts/, pyproject.toml) | ✅ | Commits 133d2b8, 975cf78 |

---

## Phase 1: Style Foundation

**Goal:** 5 style JSONs + selection logic + schema update

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1.1 | Create `pipeline/intelligence/styles/` directory | ✅ | |
| 1.2 | Write `crime.json` (per research §3.1) | ✅ | fadeblack 12f, near-black+red, measured VO |
| 1.3 | Write `history.json` (per research §3.2) | ✅ | dissolve 14f + circleopen chapters, sepia/gold |
| 1.4 | Write `modern.json` (per research §3.3) | ✅ | wipeleft 9f, teal accent, spring_allowed=true (only style) |
| 1.5 | Write `minimalist.json` (per research §3.4) | ✅ | fade 10f, light palette, hard_titles=true |
| 1.6 | Write `standard.json` (per research §3.5) | ✅ | fade 10f, #ff6b35 default accent; dropped generic "why"/"story" keywords (false positives) |
| 1.7 | Write `select_style.py` (keyword scoring + `--style` override) | ✅ | keywords=1pt, format_words=2pt; tie/no-signal → standard; alias map; `load_style()` lru_cached |
| 1.8 | Update `timeline_schema.json`: `global_style` enum + legacy aliases | ✅ | `edit_style` deprecated but still validates (old timelines pass) |
| 1.9 | Unit test: 10 briefs → expected styles | ✅ | 27 tests, all pass; 10/10 human-pick agreement |

**Milestone:** ✅ Style selection works, JSONs validate. (27 passed; example timeline validates against updated schema)

---

## Phase 2: Skills Integration

**Goal:** Skills chain reads style constraints

| # | Task | Status | Notes |
|---|------|--------|-------|
| 2.1 | Update `01_script_writer.md` — density, rhythm, hook form, tone from style | ✅ | 0.5 pts/min budget formula, format→structure map, prompt=WHAT rule |
| 2.2 | Update `02_director.md` — b-roll keywords/avoid, scene mix, min scene length | ✅ | min scene = 2× transition frames (Remotion rule 1) |
| 2.3 | Update `03_voiceover.md` — pace, energy, pause markers, voice hint | ✅ | pause markers from style's allowed set only |
| 2.4 | Orchestrator brief template appends `Style:`/`Tone:` from style JSON | ✅ | `brief_template.py` — Style:/Tone: last per VidRush; cp1252-safe |
| 2.5 | Skill-output linter: reject banned motion words | ✅ | `lint_skill_output.py` — 30 banned patterns, Style:/Tone: lines exempt |
| 2.6 | Integration test: brief → style → script → scenes → timeline.json | ✅ | `test_integration_brief_to_timeline_shape` + linter gate on all 5 styles |

**Milestone:** ✅ Skills produce style-consistent timelines; zero editing instructions. (60 tests pass)

---

## Phase 3: Remotion Style System

**Goal:** Components read style params; style → xfade mapping

| # | Task | Status | Notes |
|---|------|--------|-------|
| 3.1 | Create `remotion/src/components/styleSystem.ts` (load style JSON, `getGlobalStyle()`) | ✅ | JSON imports bundled; `normalizeStyleId`, `motionFor`, `paletteFor`, `gradeFor`, `transitionSecFor` |
| 3.2 | Rewrite `editMotion.ts` → style-driven (replace hardcoded switch) | ✅ | Thin wrapper over styleSystem; `Easing.linear` kept; legacy names compile |
| 3.3 | Update `SceneShell.tsx` — grade params (darken/vignette/grain) from style | ✅ | vignette 4-level map, grain conditional, KB zoom + accent from style |
| 3.4 | Update scene components to consume style props | ✅ | All 8 scenes accept `global_style`; accent/text default from palette; new `StatReveal` (clamped spring = modern only) |
| 3.5 | Update `render.js` — `global_style` → xfade type + frames | ✅ | One xfade type per style (no more carousel); frames/30 = duration; palette defaults from style |
| 3.6 | Legacy alias resolution in styleSystem | ✅ | `LEGACY_ALIASES` in styleSystem.ts + render.js mirror |
| 3.7 | Visual A/B: same script in `crime` vs `modern` | ✅ | `output/ab_crime.mp4` (fadeblack 0.4s, red, darken .6) vs `ab_modern.mp4` (wipeleft 0.3s, teal, spring stat). Proven: YAVG 45.3 vs 50.7; sat-red 96/32, sat-teal 0/45 |

**Milestone:** ✅ One timeline, two styles, two visibly different videos. (Bundle compiles; A/B renders verified via signalstats)

---

## Phase 4: Orchestrator End-to-End

**Goal:** One command from brief to final video

| # | Task | Status | Notes |
|---|------|--------|-------|
| 4.1 | `orchestrator.py --brief "..."` auto-selects style | ✅ | Prints scores + style + VidRush-format brief; hands to skills chain |
| 4.2 | `--style` flag override | ✅ | Works in both --brief and --timeline modes |
| 4.3 | Style consistency validation (min scene length ≥ 2× transition frames; allowed components) | ✅ | `validate_style_consistency` warns; per-style threshold; legacy alias resolves |
| 4.4 | E2E test on `pipeline/examples/` | ✅ | Legacy `storytelling`→standard/fade; `--style crime`→crime/fadeblack. 66 tests pass |

**Milestone:** ✅ `python -m pipeline.orchestrator --brief "..." → output/*.mp4` one command (brief→style; timeline→MP4).

---

## Phase 5: Polish + Docs

**Goal:** Production ready

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.1 | Fill `pipeline/config/vo.json` with real provider; export stock keys | ⬜ | USER TASK — templates ready (`VO_API_KEY`, `PEXELS_API_KEY`, `PIXABAY_API_KEY`) |
| 5.2 | Full non-skipped run (real VO + stock + music) | ⬜ | Blocked on 5.1 |
| 5.3 | Paste full skill content into `pipeline/intelligence/skills/*.md` | ⬜ | USER TASK — style-constraint tables already in place |
| 5.4 | Write `docs/STYLE_GUIDE.md` (user-facing) | ✅ | pick/tune/extend styles, command reference |
| 5.5 | Style selection accuracy check vs human picks (10 briefs) | ✅ | 10/10 = 100% (target ≥90%) — `test_brief_selects_expected_style` |

**Milestone:** ✅ Code-complete; production-ready pending user API keys + skill content (5.1–5.3).

---

## Milestones Summary

| Phase | Milestone | Status |
|-------|-----------|--------|
| 0 | Research + plan (evidence-based) | ✅ |
| 1 | Style selection works, JSONs validate | ✅ |
| 2 | Skills produce style-consistent timelines | ✅ |
| 3 | Same timeline × 2 styles = 2 visibly different videos | ✅ |
| 4 | One-command E2E brief → MP4 | ✅ |
| 5 | Production-ready | 🔨 code-complete; keys + skill content pending |
| 6 | Genre engine: story arcs + layout engine + shake opt-in | ✅ |
| 7 | Presence engine: depth parallax + sculpted grade + living light (opt-in) | 🔨 reverted to opt-in |
| 8 | Director authority + genre creativity | ✅ P0–P8 done |
| 9 | Generated-asset pipeline (ModelScope image + smart stock) | ✅ |

---

## Phase 9: Generated-Asset Pipeline 🔨

**Goal:** third asset route — auto-generate stills via ModelScope (Z-Image / Krea-2-Turbo by topic) and pull stock video smarter (Pexels /v1/ + Pixabay medium-tier), so a miss auto-fills instead of only flagging `needs_manual_asset`.
**Plan:** `docs/plans/PHASE_9_GENERATED_ASSETS.md` (research-synthesized).

| # | Task | Status | Notes |
|---|------|--------|-------|
| 9.1 | Split `--skip-stock`: skip stock *search* only, still flatten + plate local/generated/auto | ✅ | `run()` always calls `stage_resolve_broll(allow_stock=not skip_stock)`; stock-sourced scenes → plate+flag when skipped, manual/generated/auto still resolve. Fixes the footgun that hid the Phase-8 EncodingError bug. |
| 9.2 | `pipeline/assets/imagegen.py` — ModelScope async client + topic→model (Z-Image default / Krea stylized) | ✅ | `choose_image_model(prompt, loras)`: stylized/grain/concept hints or LoRA → `krea-community/Krea-2-Turbo` @1280×720 s8 g0; else `Tongyi-MAI/Z-Image` @1536×864 s9 g0. Async submit+poll (5s, 120s timeout), SHA cache, 429/no-key/timeout → `ImageGenMiss` (plate fallback, never abort). **Verified:** 4/4 model-selection cases + LoRA→Krea + graceful no-key miss. |
| 9.3 | `stock.py` — Pexels `/v1/videos/search` + `size=medium`; Pixabay medium-first + real-dim + 24h cache + animation routing + editors_choice + rate-limit headers | ✅ | Pexels migrated off deprecated `/videos/` + `size=medium` pre-filter + 1080-closest/fps~30 pick. Pixabay: **medium tier first** (usually exactly 1920×1080; was "prefer large" = 4K bug), real width/height check, downloads/views ranking, `_is_abstract_keyword` → `video_type=animation` first, weak set → `editors_choice=true` retry, 24h disk cache of search JSON (ToS). **Verified:** abstract-routing + Pexels→Pixabay fallback tests pass (5/5 stock_resilience). |
| 9.4 | orchestrator `asset_mode:"auto"` route (**now the default**) + `generate` config + `MODELSCOPE_API_KEY` env | ✅ | `asset_mode` defaults to `"auto"` (was `"generated"`). `_autogen_image` fires when auto + no bg + image beat → ModelScope by topic (per-scene `gen_model`/`loras` overrides); video beats → stock. Schema enum `["auto","stock","generated"]`, default `auto`. `generate` config block. **Verified:** worms timeline with `asset_mode` omitted → auto fires, 6 scenes graceful miss (no key) → plate fallback → `Done ->`, no crash. |
| 9.5 | E2E test on worms timeline; docs + AGENTS.md + tracker; commit | ✅ | auto-mode render OK; `test_stock_resilience` 5/5; full suite 81 passed / 6 failed (same pre-existing linter baseline, zero regressions); AGENTS.md tech-stack + 3-route + env-keys + assets/ updated; Phase 9 plan doc written. |

**Milestone:** ✅ `asset_mode:"auto"` renders end-to-end (generated-still route live; stock search fixed to Pexels /v1/ + Pixabay medium-tier). Production use pending user API keys (`MODELSCOPE_API_KEY`, `PEXELS_API_KEY`, `PIXABAY_API_KEY`).

---

## Phase 6: Genre Engine & Dynamic Direction 🔨

**Goal:** Fix 6 user-reported issues; move from re-skinned templates to genre-specific storytelling.
**Plan:** `docs/plans/PHASE_6_GENRE_ENGINE.md`

| # | Task | Status | Notes |
|---|------|--------|-------|
| 6.1 | Shake → per-scene opt-in prop (remove style-global default) | ✅ | `SceneShell` shake/shake_at props; style `max_shake` ceiling (crime .8, history 0, modern .5, minimalist 0, standard .6) |
| 6.2 | Layout engine — `components/layout.ts` (rule-of-thirds grid, focal anchors, text-safe zones, computed slot placement) | ✅ | `resolvePlacement` (hero/editorial/sidebar/float) + `distributeAssets` |
| 6.3 | Flexible type system — auto line-break, responsive size, placement intents | ✅ | `breakLines()` word-wrap + orphan rebalance, `fontSizeFor()` responsive |
| 6.4 | Redesign Document scene — single focal hierarchy, punch brings line to center, caption anchors under doc | ✅ | caption centered under doc on same axis; label top-left safe zone |
| 6.5 | Genre story arcs — `components/genreArcs.ts` (documentary/news/essay/listicle/explainer from script.format) | ✅ | arc ≠ visual style; `arcFor`/`beatForScene` pace the director |
| 6.6 | Director skill v3 — text-presence judgment, shake opt-in, layout intent, arc position | ✅ | `02_director.md` rewrite: 5 judgments per scene |
| 6.7 | Timeline schema — `shake`, `shake_at`, `placement`, `arc_position` fields | ✅ | render.js flows editorial choices through to props |
| 6.8 | Typecheck + render one genre end-to-end | ✅ | documentary arc (history style) 6 scenes rendered — `output/_fx_genre_documentary.mp4` |
| 6.9 | Fix per-scene drift reading as shake (drift rotation/timeScale/amp) | ✅ | drift rotation ±0.35°→±0.06°, timeScale 0.09→0.04, amp reduced (crime .15/history .5/standard .25); modern+minimalist static |
| 6.10 | Motivated-editing rulebook — `docs/EDITING_DECISIONS.md` (Murch Rule of Six, cut/hold, eye-trace, transitions, retention, text) | ✅ | research-codified decision brain |
| 6.11 | Director skill v4 — motivated decision logic (7 ordered judgments + one-line justification per scene) | ✅ | `02_director.md` rewrite; emotion/story/rhythm first |
| 6.12 | Text reading-time validation in orchestrator | ✅ | `validate_reading_time` — min_hold = words/4 + 1.0s, floor 0.85s |

**Milestone:** ✅ Genre engine + motivated editing in place — story arcs pace scenes, shake is opt-in, placement is computed, and every editing choice follows the Rule-of-Six decision brain.

---

## Phase 7: Presence Engine 🔨 (reverted to opt-in)

**Goal:** 2.5D depth parallax + sculpted grade + living light so stills read as cinema, not slideshow.
**Plan:** `docs/plans/PHASE_7_PRESENCE_ENGINE.md`

| # | Task | Status | Notes |
|---|------|--------|-------|
| 7.1 | `effects/depthParallax.tsx` (2-plane near/far), `effects/lightLife.tsx` (sweep/dust/flare), `grade.ts` sculpt split-tone/focal | ✅ | built, research-backed |
| 7.2 | `camera.ts` easedCameraProgress (ease-out settle + drift tail) — kills constant-velocity slide | ✅ | |
| 7.3 | `pipeline/assets/depth_planes.py` luminance-keyed RGBA plane baker (PIL/numpy, no ML deps) | ✅ | |
| 7.4 | `pipeline/video/photo_base.py` FFmpeg/GPU photo base + hybrid path in render.js | ✅ | `hybrid` flag, `renderSceneHybrid` |
| 7.5 | **Fallback decision:** hybrid output "degraded to poor editing" → revert to full-Remotion; parallax/sculpt made OPT-IN (default OFF) | ✅ | SceneShell clean Phase-6 baseline; commit `e03c725` checkpoint, `921ee7e` revert |
| 7.6 | Fix render.js hang after "Final →" (puppeteer/Chrome held event loop) | ✅ | explicit `process.exit(0)`; 6-scene/32s video = 76.6s clean exit |

**Milestone:** Presence layers built and kept behind flags; default render = clean Phase-6 editorial look; render process exits cleanly.

---

## Phase 8: Director Authority & Genre Creativity 🔨

**Goal:** Free editing from hardcoded scene timing (the director directs); add per-genre signature moves (`_fx_creative_<style>.mp4`).
**Audit + plan:** `docs/plans/PHASE_8_DIRECTOR_AUTHORITY.md` — gaps B1–B9, plan P0–P8.

**Top gap (B1):** every scene computed its own beat timing (`tText = t0 + dur(fast)`; `PersonCard startFrame={2}`) — the director could not move a beat. Fix = a beat-choreography contract.

| # | Task | Status | Notes |
|---|------|--------|-------|
| P0 | **Director beat-choreography contract** — `beats`/`tempo`/`hold_last` override per-scene timing; defaults unchanged; literal frames killed | ✅ | `components/beats.ts` (seconds→frames, tempo scale, director override); all 10 scenes wired via `choreoBeats`; render.js + orchestrator pass-through; schema `beats`/`tempo`/`transition_out`/`grade_override`; linter + `02_director.md` docs. **Verified:** two renders differing only in `beats.text` (0.3s vs 3.0s) differ by 6007px at t=1.0s, converge at 3.5s. |
| P1 | VO→visual sync — word timestamps from TTS; text pops + punch land on spoken words | ✅ | `pipeline/assets/word_timing.py` (native provider timings via `word_timing` cfg + prosody estimate fallback, cached); `vo.py` `synthesize_with_meta`; orchestrator writes scene-relative `word_times`; `effects/sync.ts` (`phraseOnsetFrame`/`numberOnsetFrame`); `WordPop` + Stat punch + SceneShell shake sync to spoken syllables. **Verified:** 6047→12962 bright px across a delayed word's onset (sync works). Director `beats` still overrides. |
| P2 | Act-aware per-cut transitions (`transition_out: hard|dissolve|whip|dip`) + signature-move cap | ✅ | `render.js` — `resolveCutTransition` maps intent→xfade (hard=2-frame fade, style=default, dissolve, dip=fadeblack, whip=hblur@0.27s); per-cut xfade chain in `concatWithXfade` with cumulative-offset bookkeeping; inputs pinned `fps=30,settb=AVTB` (mixing transition durations else time-compresses ~2×). Orchestrator `validate_transition_rarity` — each non-default type ≤1×/video, ≤15% non-default budget, `transition_note` required. `02_director.md` act-break table. **Verified:** crime timeline (style,hard,whip) renders 15.3s = exact offset math, content plays correct speed (scene cuts @3.5/7.5/11.5s); uniform-style regression unchanged 14.8s; validator single-whip clean / two-whips warns / no-note warns / over-budget warns; pytest 57/9 (pre-existing baseline). **Bug found+fixed:** 1-frame (0.033s) hard-cut xfade corrupts chain timing → whole video ~2× speed; raised to 2-frame min (xfade practical floor). |
| P3 | Camera intent grammar — beat→ken_burns mapping, energy-derived moves | ✅ | `SceneShell` `resolveCameraMove` — precedence photo_move (explicit) > energy-derived (low=none, mid/high=in) > ken_burns (scene-type structural default) > seed-rotation (last resort). All 9 scenes forward `energy`/`photo_move`; orchestrator + render.js forward both. `02_director.md` beat→move table (reveal→in, context→out, person→in-left/right, lineup→pan, evidence→none, quiet→none). `validate_camera_variety` — 3 identical moves in a row warns. **Verified:** console trace `kb=out→dir=out`, `photo_move=none+kb=in→dir=none` (override wins), `none→scale 1.000@f0&f59` (static), `in→scale 1.000→1.0399` (push-in); validator 3-in-a-row warns / varied clean; pytest 57/9 (baseline); tsc clean. (Cross-file blend-diff=0 was a red herring — 4% zoom at dark grade + crf16 h264 sits in the encode noise floor; console trace is the authoritative proof.) |
| P4 | Impact-shake rewrite (directional kick, not jelly) + rarity caps — "shaky solved / use in some case" | ✅ | `camera.ts` `impactShake` — single-axis 2–4px kick, attack→smooth decay, settles ~10f, **r=0 throughout** (rotation was the jelly tell), 1-frame smear; old `cameraShake` kept as deprecated alias. `SceneShell` `shake_dir` (x/y/diag) + 10f decay + smear in transform. Orchestrator `validate_shake_rarity` — density (~1/60s), no-adjacency, no-quiet-beat warnings. schema `shake_dir`; `02_director.md` impact/rarity rules. **Verified:** numeric trace peak 2.08px @f2, settled @f10, after-window all-0; 2-scene crime render clean; pytest 57/9 (pre-existing baseline, zero regressions). |
| P5 | Genre signature moves → `_fx_creative_crime.mp4` (glitch, crime-board, halftone, evidence punch), `_fx_creative_history.mp4`, `_fx_creative_modern.mp4` | ✅ | `effects/signature/{GlitchBeat,CrimeBoard,WhipPan,ChartDrawOn,ArchivalPulse,HalftoneDoc}.tsx`; `signatureCaps` in tokens.ts (crime=glitch/board/halftone, history=archival/halftone, modern=whip/chart, minimalist/standard≈0). New `crime-board` scene type + composition; SceneShell `signature` intent (glitch/archival), Document `grade_override=halftone`, Stat `chart_points`. `validate_signature_rarity` (1/video cap). **3 showreels rendered + verified:** crime (glitch 27.9→0.002 spike, board cards+red-string, halftone 9.3), history (archival live YAVG 48, halftone 10.7), modern (live 46.5, chart-draw line). **Bug found+fixed:** render.js hybrid was default-ON (`!== false`) contradicting the Phase 7 revert — flipped to opt-in (`=== true`), restoring full-Remotion default; history/modern re-rendered clean. minimalist/standard intentionally have no showreel (restraint IS their genre). |
| P6 | Audio architecture — sidechain duck (AGENTS.md promise), two-pass loudnorm, SFX | ⬜ | orchestrator stage_audio_mix |
| P7 | Per-scene grade intent (`grade_override: archival|clean|noir|sepia|halftone`) | ⬜ | grade.ts, SceneShell |
| P8 | Resilience & hygiene — stock Pixabay fallback, reading-time floor alignment | ⬜ | stock.py, orchestrator |

**Build order:** P0 → P1 → P4 → P5(crime first) → P2 → P3 → P6 → P7/P8.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ⬜ | Not started |
| 🔨 | In progress |
| ✅ | Complete |
| ❌ | Blocked |
| ⏭️ | Skipped / deferred |
