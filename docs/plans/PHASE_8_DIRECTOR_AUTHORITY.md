# Phase 8 — Director Authority + Genre Creativity Engine

**Status:** planned · **Depends on:** Phase 6 (genre engine), Phase 7 (presence engine, now opt-in)

> ## Audit first (Sections A–D) — what the pipeline does from script creation → final
> render, and where it falls short of a professional Adobe-AE edit. The improvement
> plan (Section E onward) fixes the gaps. The governing principle for every fix:
>
> **The DIRECTOR directs. No editing decision is hardcoded inside a scene.**
> Code provides *capabilities* (camera moves, text entrances, shake, punch, parallax);
> the director provides *intent* (which, when, how much, why). Style still owns *values*
> (colors, fonts, grain, easing curves). Anything a human editor would choose on the
> day belongs to the director — anything that is the brand belongs to the style.

---

## A. The full pipeline today (script → render)

```
brief ──► select_style.py  (brief → global_style: crime|history|modern|minimalist|standard)
        │
        ▼
01_script_writer  ── script.md (HOOK/BODY/CTA, ~140wpm, style rhythm + format)
02_director       ── scenes: type/duration/layout/placement/energy/shake/emphasis/broll
03_voiceover      ── per-scene vo_text + pause markers + voice hint
04_image_prompt   ── (optional) stock-miss fallback prompts
05_video_prompt   ── (optional) motion-needed prompts
        │
        ▼
orchestrator.py
  1 validate_timeline / validate_style_consistency / validate_reading_time
  2 stage_resolve_broll  → Pexels/Pixabay ≥1080p, copy into remotion/public
  3 stage_vo             → custom TTS per line, SHA256 cache, fill vo_start, extend duration
  4 stage_build_manifest → timeline → remotion manifest.json (global_style carried)
  5 stage_render         → node src/render.js --batch manifest.json
  6 stage_audio_mix      → adelay + amix + single-pass loudnorm (-14 LUFS YT)
        │
        ▼
remotion render.js --batch
  per scene → selectComposition (type → comp id) → renderMedia (Chrome raster, h264)
             duration = scene.duration × fps  (override, content-driven ✓)
  concatWithXfade → FFmpeg xfade chain (ONE transition type per style) + NVENC
```

---

## B. Gap audit — why it is NOT yet "AE-professional"

### B1. The big one: editing is hardcoded inside the scenes  ⛔ *core complaint*
Every scene computes its own beat timing from fixed tokens. The director can pick a
scene *type* and a handful of flags, but **cannot move a single beat**:

| What an AE editor controls | Where it's hardcoded today |
|---|---|
| When text lands (sync to VO beat) | `Content.tsx tText = t0 + dur(fast)`, `tSub = tText + dur(base)+2` |
| Text entrance choice per line | scene picks `MaskLineReveal` / `WordPop` — director can't override |
| When the stat punch fires | `Stat.tsx tAccent = tNum + 0.7·countFrames` |
| When a shake hits, how long | `SceneShell cameraShake(...)` always from `shake_at`, fixed 24f decay |
| Camera move / its timing / ease | `ken_burns` direction only; `easedCameraProgress(0.42, 0.1)` baked |
| Document highlight→punch timing | `Document.tsx tPunch = tHighlight + highlightFrames + dur(fast)` |
| Raw literal beats | `PersonCard startFrame={2}/{6}/{12}/{18}` — not even tokens |

`PersonCard` is the smoking gun — literal frame numbers. The whole point of the
token system ("one editorial hand") accidentally locked the *timing* too.

**Fix:** a **beat-choreography contract**. The scene ships *defaults*, but every beat
is a named prop the director may set (`beats={title: 0.2, text: 0.5, accent: 0.9}` in
seconds, or absolute frames). Director can also scale all of a scene's rhythm
(`tempo=1.2`) without touching the style. Linter allows timing numbers because they are
*intent*, rendered into motion by the style.

### B2. No VO→visual sync (the single biggest "pro" tell)
`WordPop` claims "sync beats to VO when the pipeline passes per-word offsets" — **nothing
ever passes them.** VO is synthesized per-line; word timings are discarded. Text pops on
even 3-frame spacing regardless of narration. An AE editor keyframes text to the spoken
word; here they drift apart, and the eye notices.

**Fix:** `vo.py` already returns per-line duration — extend the provider to also return
word timestamps (most TTS APIs give them; else force-align). Orchestrator writes
`word_times[]` into the scene; `WordPop`/`MaskLineReveal`/`Stat` punch use real offsets.
Beat to `B2`: shake/punch land *on the spoken emphasis word*, not on a fixed frame.

### B3. Transition grammar is one type per video, always at the same length
`render.js` uses ONE xfade type from the style JSON for every cut, at one duration.
An editor varies it: hard cut for 95% of cuts, a whip or match cut at act breaks, a dip
to black for era change. We got the *type* discipline right (style owns HOW) but lost the
*placement* judgment (director owns WHERE).

**Fix:** per-scene `transition_out` intent — `hard | style_default | dissolve | whip |
dip` (never a raw xfade name). Director marks the 2–4 act breaks; everything else defaults
to the style's hard cut. `concatWithXfade` reads the per-cut intent. This is the director's
"one signature move per video" rule, enforced.

### B4. Camera grammar is a rotation, not a decision
`KB_ROTATION[seed % 6]` cycles in/right/out/left/up/down. Real operators choose the move
to serve the subject: push-in on a reveal, pull-back on context, lateral pan across a
lineup. Rotation = "template."

**Fix (already partially specced):** director's `photo_move` / `ken_burns` per scene is
already a prop — but nothing in the director skill says *when* to push vs pull vs pan.
Add camera-intent guidance to `02_director.md` keyed to the beat (reveal→`in`,
context→`out`, person→`in-left`, evidence→`none` + parallax).

### B5. Audio is a single loudness pass with no mix architecture
- `amix ... normalize=0` then one `loudnorm`. No **sidechaincompress duck** under VO
  (AGENTS.md §Audio *says* sidechain duck — `stage_audio_mix` doesn't do it).
- No music bed level automation (swells at the reveal, drops under dialogue).
- No SFX at all (`FREE_MOTION_ASSETS.md` §6 lists sources; nothing is wired).
- `loudnorm` single-pass is flagged "two-pass later" — still single.

**Fix:** proper sidechain duck (music −12dB under VO, returns on bare scenes), two-pass
loudnorm, optional SFX hook on transition beats (paper-shuffle on document, whoosh on whip).

### B6. Grain/leak/grade are per-style constants, not per-scene choices
`grain`, `cutLeak`, `darken`, `vignette` come from the style and apply to every scene.
An editor *grades scenes* — archival footage gets scratches + sepia, present-day talking
gets clean. The VHS/scratch (§11) and halftone (§12) treatments exist in the catalog but
have no per-scene trigger.

**Fix:** optional per-scene `grade_override` intent: `archival | clean | noir | sepia |
halftone` — maps onto the style's palette, adjusts grain/leak/scratch for that scene only.
Director uses it to signpost era ("this is the 1974 tape").

### B7. Genre creativity is shallow — styles differ by color, not by *moves*
This is the user's "_fx_creative_crime.mp4" request. Today `crime` vs `history` vs
`modern` mostly change palette + grain + one transition type. The **signature moves that
make a genre read instantly** are catalogued (AE_TRENDS §5–22) but mostly unbuilt:

| Genre | Signature moves present? | Missing |
|---|---|---|
| crime | grain, fadeblack, underline | glitch beat (§9), crime-board collage (§18), halftone docs (§12), evidence punch-zoom, interrogation spotlight |
| history | sepia grade, drift, underline | VHS/scratch (§11), map route ✓ (built), photo-archival sepia pulse, era wipe |
| modern | punch (§6), highlight, springs | whip-pan (§5), count-up ✓, kinetic tracking, chart draw-on (§20) |
| minimalist | (by design) restrained | fine — restraint IS the move |
| standard | safe middle | — |

**Fix (Section E, P5):** build the missing signature moves as opt-in components, gated by
`presenceVocab`-style per-style caps, fired **only** when the director calls them. The
user's note — *"shaky solved / still use it but just in some case"* — means: shake must be
fixed to feel like an impact (not a cheap jitter) and reserved for genuine impact beats.

### B8. Shake needs a quality fix + rarity enforcement
`cameraShake` rotates ±0.5° and translates up to 5px with fast noise — reads as "jelly,"
not "impact." Real impact shake: a fast directional **kick** (translate mostly one axis,
2–4px, 8–12 frames) with a single decay, *plus* a 1–2px motion-blur-ish smear, landing on
a beat. And it must be capped per video, not just per scene.

**Fix (Section E, P4):** rewrite shake as a directional kick (not isotropic noise), decay
over 10f, add a 1-frame horizontal smear, cap uses via the director skill ("most videos
have ZERO; never two adjacent").

### B9. Minor / hygiene
- `PersonCard`/`Comparison`/`ListReveal` use literal frames (not even tokens).
- `validate_reading_time` floor 0.85s but director doc says text needs `(words/4)+1.0`;
  enforce the same number in both.
- No retry on Pexels miss → orchestrator `raise`s; a resilient pipeline should try Pixabay
  then emit the AI prompt and continue with a neutral plate rather than abort the whole video.
- `--brief` mode only *prints* a prompt; there is no automated script→timeline call, so the
  "factory" is still manual between skills. (May be intentional — flag for decision.)

---

## C. What is already right (do not regress)
- Duration is content-driven (scene.duration × fps overrides comp default). ✓
- One transition *type* per style; FFmpeg xfade in batch. ✓
- Token system for easing/duration values (one hand). ✓ — keep values, free the *timing*.
- Layout engine = single placement authority; no hardcoded asset coords. ✓
- Genre arcs (story spine) separated from visual style. ✓
- Style owns values; director owns intent — the boundary is correct, just under-built. ✓
- Batch render + NVENC + clean process exit. ✓

---

## D. The "not AE-professional" summary (ranked)
1. **Beat timing is frozen in components** — director can't direct. (B1)
2. **No VO→text/punch sync** — the dead giveaway of automation. (B2)
3. **Transition placement has no act structure** — one type, uniform, no judgment. (B3)
4. **Camera moves rotate instead of serve the subject.** (B4)
5. **Genre identity is color-deep, not move-deep** — crime/history/modern read alike. (B7)
6. **Shake reads as jelly, not impact; not rarity-enforced.** (B8)
7. **Audio has no duck/architecture, no SFX.** (B5)
8. **Grading is global, not per-scene era-signposting.** (B6)

---

# E. Improvement plan

> Ordered by impact. P0/P1 unblock "the director directs"; P4/P5 deliver the
> `_fx_creative_<style>.mp4` genre showreels the user asked for.

## P0 — Director Beat-Choreography Contract (frees editing from components)
**Goal: every beat in every scene is overridable by the director; defaults keep working.**

- Add to each scene an optional `beats` prop: named beat → **seconds from scene start**
  (float; orchestrator already thinks in seconds). E.g. `Content`: `{plate, text, accent, subtext}`;
  `Stat`: `{unit, number, punch, context}`; `Document`: `{doc, highlight, punch, caption}`.
- Resolution rule inside components: `t = beats.x ?? defaultTokenChain`. Director timing wins;
  absent → today's default (no regression).
- Add `tempo` (scene-level rhythm multiplier, default 1) and `hold_last` (freeze last beat to
  scene end) as director intents.
- Convert `PersonCard`/`Comparison`/`ListReveal` literal frames → token defaults under the same
  contract.
- `render.js` already passes arbitrary props through — no change needed beyond scene signatures.
- Linter update: allow numeric `beats`/`tempo` (they are intent; style renders values).
- **Files:** all `scenes/*.tsx`, `components/tokens.ts` (contract type), `02_director.md`
  (how to time beats), `lint_skill_output.py` (whitelist intent numbers).
- **Acceptance:** a timeline that sets `Content.beats.text=1.2` renders the line landing at 1.2s;
  omitting it renders today's timing. `PersonCard` has no literal frame constants.

## P1 — VO→Visual Sync (kills the "automated" tell)
- Extend `vo.py` providers to capture **word timestamps** (TTS API word timings, or
  `aeneas`/whisper force-alignment as fallback). Cache key already covers text+voice.
- Orchestrator writes `word_times: [[word, t], ...]` (scene-relative seconds) into each scene.
- `WordPop`/`MaskLineReveal` accept optional `word_times`; `Stat.punch` + `shake_at` default to
  the emphasis-word timestamp when present.
- `SceneShell` shake default `shake_at` → emphasis beat, not 0.
- **Files:** `assets/vo.py`, `orchestrator.py` (stage_vo), `typography.tsx`, `Stat.tsx`,
  `SceneShell.tsx`, `03_voiceover.md`.
- **Acceptance:** in a 2-line scene the words pop on the spoken syllables (±60ms), and the stat
  punch lands on the spoken number.

## P2 — Act-aware transitions ✅ SHIPPED
- Director emits optional per-scene `transition_out: hard|style|dissolve|whip|dip` +
  `transition_note` (the one-sentence justification). Default = style xfade.
- `render.js concatWithXfade` builds a **per-cut** xfade (mix allowed only via director intent);
  `hard` = 2-frame fade (xfade's practical floor — 1 frame corrupts chain timing), `dip` =
  fadeblack regardless of style, `whip` = hblur @ ~0.27s (act-break snap).
- Enforced in `validate_transition_rarity`: each non-default type ≤1×/video, ≤15%
  non-default budget, `transition_note` required. Director skill has the act-break table.
- **Files:** `render.js`, `orchestrator.py` (validator), `02_director.md`, `timeline_schema.json`.
- **Acceptance:** a crime timeline with a `whip` at the act break renders one whip + rest fadeblack
  hard cuts; validator warns if a second whip is added.

## P3 — Camera intent grammar ✅ SHIPPED
- `02_director.md`: beat → `photo_move`/`energy` table (reveal→`in`, context→`out`,
  person→`in-left`/`in-right`, lineup→pan, evidence→`none`+parallax, quiet→`none`).
- `SceneShell` `resolveCameraMove`: precedence **photo_move > energy-derived > ken_burns
  (scene-type structural default) > seed-rotation**. When the director passes `energy`,
  the move derives from it (low=hold, mid/high=push-in) instead of the dice roll.
- All 9 scenes forward `energy`/`photo_move`; orchestrator + render.js pass them through.
- `validate_camera_variety`: three identical moves in a row warns (template tell).
- **Verified:** console trace confirms resolution (out→out, photo_move overrides ken_burns,
  none→static scale 1.0, in→push 1.04); validator + tests green.

## P4 — Impact-shake fix + rarity (the "shaky solved / use in some case" item)
- Rewrite `cameraShake` as a **directional kick**: single dominant axis (director can pass
  `shake_dir`), 2–4px, 10f decay, plus a 1-frame 1–2px X smear for blur. Kill the isotropic
  ±0.5° rotation jelly.
- Cap usage: director skill — "≥90% of videos have ZERO shake scenes; never two adjacent; never
  on text or bare beats." Validator warns on >1 shake scene per 60s.
- Shake fires on the emphasis/impact beat (from P1 word timing), not frame 0.
- **Files:** `effects/camera.ts`, `SceneShell.tsx`, `02_director.md`, `orchestrator.py`.
- **Acceptance:** a crime reveal shake reads as a single hard hit that settles, not a wobble;
  a quiet scene with shake is flagged.

## P5 — Genre signature moves (the `_fx_creative_<style>.mp4` showreels)
Build the catalogued-but-missing moves as **opt-in components**, each capped per style and fired
only on director intent. Deliver one creative showreel per style as proof.

- **crime** → `_fx_creative_crime.mp4`
  - `GlitchBeat` (§9 RGB-split + slice shear, 5–15f) — one per video, at the twist.
  - `CrimeBoard` (§18 pinned cutouts + string draw-on) — collage evidence beats.
  - `HalftoneDoc` (§12) on `Document` when `grade_override=halftone`.
  - evidence `punch-zoom` (§6) on the exhibit.
  - fixed impact `shake` (P4) at the arrest/reveal — *the "some case."*
- **history** → `_fx_creative_history.mp4`
  - `ArchivalPulse` (§11 scratch/dust overlay, era signpost) when `grade_override=archival`.
  - map route dive ✓ (built) + era wipe (dip-to-black) at decade changes.
  - sepia photo drift with paper-grain.
- **modern** → `_fx_creative_modern.mp4`
  - `WhipPan` (§5 directional-blur cut) at energy bumps.
  - `CountUp` ✓ + `ChartDrawOn` (§20 bar/line) for data.
  - kinetic `TrackingTitle` punch entrances.
- **minimalist / standard** → restraint is the genre; no new moves (document why).
- Each move reads its intensity from `presenceVocab`-style per-style caps (add
  `signatureCaps` to `tokens.ts`); **none** are style defaults — the director calls them.
- **Files:** new `components/effects/signature/{GlitchBeat,CrimeBoard,WhipPan,ChartDrawOn,ArchivalPulse}.tsx`,
  `tokens.ts` (caps), `SceneShell.tsx`/scenes (opt-in wiring), `02_director.md` (when to call each),
  5 showreel manifests + renders.
- **Acceptance:** each `_fx_creative_<style>.mp4` plays and is visually distinct; every signature
  move is opt-in and capped; a video with the move called 3× gets a validator warning.

## P6 — Audio architecture ✅ SHIPPED
- `stage_audio_mix` rewritten: `sidechaincompress` ducks the music bed under VO (~`music_duck_db`
  = −12 dB) and **recovers after narration** — the AGENTS.md promise. The old code flattened music
  volume for the whole video.
- **Recovery fix (the hard-won lesson):** `sidechaincompress` terminates at the *shorter* input, so
  the VO sidechain is padded with trailing silence to the full video length (`apad,atrim`). Without
  it the music bed cuts off when VO ends. Verified: −21 dB under VO → −33 dB (bed at −12 dB base)
  after VO, bed runs the full duration.
- Two-pass loudnorm (linear, `measured_*` from pass 1) → hits **−14.0 LUFS exactly**, TP −5.0 dBTP.
  Falls back to single-pass dynamic if measurement unavailable.
- Per-scene `sfx` (paper/whoosh/hit) — opt-in, placed at scene start via `adelay`, mixed at
  `sfx_volume` (scene → timeline default 0.6), missing files skipped (never fatal).
- Removed `-shortest` (it truncated output to the shortest audio, not the video).
- `validate_sfx_rarity`: >2 SFX per video or same SFX back-to-back warns (decoration, not punctuation).
- **Files:** `orchestrator.py` (`stage_audio_mix`, `_build_audio_filter`, `_run_two_pass_loudnorm`,
  `_collect_sfx`, `validate_sfx_rarity`), `timeline_schema.json` (`sfx`, `sfx_volume`),
  `02_director.md` (Sound section), `pipeline/assets/sfx/README.md`, `tests/test_audio_mix.py`.
- **Acceptance met:** bed dips under VO and recovers; −14 LUFS ±0.5, TP ≤ −1; SFX lands on its beat.

## P7 — Per-scene grade intent ✅ SHIPPED
- Optional `grade_override: archival|clean|noir|sepia|halftone` per scene; `resolveGrade(style, override)`
  in `grade.ts` maps the *meaning* onto the style palette (a per-style `OVERRIDE_WEIGHT` caps how far
  the override can push — crime/history lean in, minimalist stays restrained at 0.4×).
- `SceneShell` accepts `grade_override` and applies the resolved **filter** (wins over flat + sculpt),
  **wash**, and **grain** multiplier. `archival` auto-fires the `ArchivalPulse` scratch/dust overlay
  (style-capped via `signatureCaps.archival`), so the director needs no separate `signature.archival`.
  `halftone` desaturates toward print; the dot screen itself stays with the document scene (`HalftoneDoc`).
- All 9 scenes forward `grade_override` (render.js already passed it through the manifest).
- **Verified:** numeric resolution (each override distinct, style weight caps archival 0.5 → minimalist
  0.2, no-override returns base look); rendered `_fx_p7_grade.mp4` (base/archival/clean) — SATAVG
  confirms desat ordering archival 7.85 < base 9.29 < clean 13.08, cross-scene diffs 3.6–4.1.
- **Files:** `grade.ts` (resolveGrade + OVERRIDE_WEIGHT), `SceneShell.tsx`, all 9 scenes, `02_director.md`.

## P8 — Resilience & hygiene ✅ SHIPPED
- Stock miss: try Pixabay → emit AI prompt → fall back to a neutral style plate; **do not abort**
  the whole render. Flag the scene for manual asset. *(done — `_style_plate` + `needs_manual_asset`)*
- Align `validate_reading_time` floor with the director doc's `(words/4)+1.0`. *(already aligned;
  fixed `test_consistency_resolves_legacy_alias` fixture that tripped the new validator)*
- Decide whether `--brief` should optionally chain straight into script→timeline (factory mode) —
  user decision. *(deferred — open question below)*
- **Files:** `assets/stock.py`, `orchestrator.py`, `tests/test_stock_resilience.py`.

---

## F. Suggested build order
1. **P0** beat contract (frees the director — the core complaint).
2. **P1** VO sync (biggest visible "pro" jump).
3. **P4** shake fix + rarity (unblocks the creative reels cleanly).
4. **P5** crime showreel first (`_fx_creative_crime.mp4` — user's named target), then history, modern.
5. **P2** transitions, **P3** camera grammar.
6. **P6** audio, **P7** grade intent, **P8** hygiene.

Each P is independently shippable and behind a flag or opt-in, so the clean Phase-6 baseline
never regresses.
