# Phase 7 — Presence Engine: from "slideshow" to "edited video"

**Goal.** Kill the "professional slideshow" feel. Make stills read like an AE editor
brought them alive. Feedback: current output is news-channel paced but flat — one
rigid full-frame transform per still, no depth, no living light, shallow grade.

## The 6 slideshow tells → the fix

| # | Tell (root cause) | Fix |
|---|-------------------|-----|
| 1 | **Whole-frame transform** — one CSS transform on a full-bleed `<Img>`; fg/bg move as one flat card | **Multi-plane split.** Bake 3 soft depth planes (far / mid / near) per image via luminance-keyed feathered alpha masks (PIL). Each plane drifts/scales at a different rate → real parallax *within* the scene. |
| 2 | **Linear dead motion** — `kenBurns` is an un-eased constant-velocity ramp | **Eased camera grammar.** Ease-out settle (fast in, decel) + low-frequency drift tail + micro-rotate. No constant-velocity slides. |
| 3 | **No physical light** — only a flat gradient wash + leak at cuts | **Living light.** Animated volumetric light sweep + drifting dust particles + beat-reactive flare, seeded per style, *inside* the frame. |
| 4 | **Shallow muddy grade** — `history = contrast(1.05) sepia(.28)` flattens | **Sculpted grade.** Split-tone (lift shadows per style), filmic S-curve contrast, focal separation (center crisp / edges softer). |
| 5 | **Motion confined to edges** — grain + micro-drift sub-perceptual | Living light + parallax put motion in the *middle* of the frame. |
| 6 | **No DOF** — everything equally sharp | Far plane gets a slight blur; near plane stays crisp. Sells depth. |

## Architecture

- **Python (bake, one-time per image):** `pipeline/assets/depth_planes.py` — luminance
  segmentation into 3 soft planes via Otsu-style thresholds + heavy gaussian feather.
  Outputs `_far.png`, `_mid.png`, `_near.png` (RGBA) + `_bg.png` (base, no near/mid).
  PIL only — no torch/rembg (fragile, slow). Manifest lists plane paths.
- **Remotion:** new `components/effects/depthParallax.tsx` renders the 3 planes with
  per-plane drift/scale/rotate; `components/effects/lightLife.tsx` renders sweep +
  dust + flare; `camera.ts` gains `easedCamera()`; `grade.ts` gains split-tone +
  filmic curve + focal DOF. `SceneShell` composes them when a `depth` prop is present,
  falling back to the current single-image path when not.
- **Per-style tuning** lives in `tokens.ts` (parallax amount, light intensity, grade
  split) — scenes never hardcode.

## Constraints
- PIL/numpy only in the bake step (already installed). No new heavy ML deps.
- All motion deterministic/seeded. `staticFile` paths under `remotion/public/`.
- Scenes with no depth manifest keep working unchanged (fallback path).
- Typecheck clean + render the history test + extract frames for user review.

---

# Phase 7b — HYBRID ARCHITECTURE (the real fix)

**Why.** Remotion rasterizes every frame in Chrome and CPU-encodes → ~45–70s per
5s clip. Unacceptable for a 32s video (5–15 min). The effects aren't the cost —
Chrome raster + CPU encode is. Remotion is the wrong tool for animating stills.

**User's principle (authoritative):**
- **FFmpeg (GPU/NVENC)** → still images needing only NON-animation work: ken-burns
  zoom-pan, 2-plane parallax, grade, light, duration, xfade. GPU → sub-second, cool CPU.
- **Remotion** → ONLY the precision ANIMATION layer: text entrances, kinetic type,
  stat counters, draw-on accents — where exact frame when/where/how matters.
  Rendered as TRANSPARENT (alpha) overlay clips, then composited by FFmpeg.

**Per scene:** FFmpeg builds the photo base (GPU) → Remotion renders a transparent
text overlay → FFmpeg `overlay` composites → xfade concat → NVENC final.

## Build order
1. `SceneShell` gains `transparent` mode — skips background, keeps only the
   animation/children layer (text, accents, counters). No bg requirement.
2. `render.js` — for each scene, render TWO artifacts:
   a. Remotion transparent overlay (WebM VP9 alpha, or PNG seq if alpha unreliable).
   b. FFmpeg photo base (from bg_image + planes): zoompan + grade + parallax.
   Then FFmpeg `overlay` to composite, xfade concat, NVENC.
3. FFmpeg photo-base builder (`pipeline/video/photo_base.py` or inline in render.js
   via spawned ffmpeg): zoompan eased move + overlay near-plane parallax + eq/curves
   grade + light sweep overlay.
4. Keep Remotion-only path as fallback (no alpha / pure-graphics scenes).

## Target
32s video in ~30–60s total. Remotion clips become light (no 1080p photo raster).

