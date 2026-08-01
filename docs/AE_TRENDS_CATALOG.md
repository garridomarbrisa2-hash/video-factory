# Motion Graphics Techniques Catalog 2024–2026
## After Effects Trends for YouTube Long-Form (Documentary / Explainer / Video Essay / Finance-Crime-History) & Commercial Ads

**Purpose:** Catalog of the trendiest motion graphics techniques of 2024–2026 with enough technical detail to recreate programmatically in Remotion. Compiled from 2024–2026 trend reports (School of Motion, Motion Array, Envato), creator teardowns (Johnny Harris, Fern, Magnates Media, LEMMiNO, Vox), and AE tutorial canon.

---

## Kinetic Typography

### 1. Mask Line Reveal (per-line text rise)
**What it looks like:** Each line of text rises into view from behind an invisible mask — the line appears to slide up out of a horizontal slot, with a slight ease-out deceleration. Lines stagger 3–6 frames apart.
**Where used:** Title cards, lower thirds, pull quotes, chapter markers.
**Why trendy:** It is THE default text entrance of every major documentary channel (Vox, Johnny Harris, Fern). Reads as "broadcast editorial" because it mimics AE's text animators with range selectors.
**Technical breakdown:** `overflow: hidden` wrapper per line + inner `translateY(100% → 0)` on an ease-out curve (AE Easy Ease ≈ cubic-bezier(0.33, 0, 0.67, 1)). Optional 4–8px blur settling to 0. No rotation, no scale — movement is pure Y. Stagger comes from per-line `startFrame + i*4`.

### 2. Word-by-Word Pop / Highlight Sync (caption kinetic type)
**What it looks like:** Words appear one at a time in sync with VO; the active word is highlighted (color swap or background plate) while spoken. MrBeast / TikTok-caption style, now standard in finance/explainer YouTube.
**Where used:** Hook lines, emphasis beats, fast-paced explainers.
**Why trendy:** Retention editing — every word is an event. Driven by auto-captions (Whisper).
**Technical breakdown:** Per-word timing tokens (from caption data). Each word: opacity 0→1 in 2 frames + optional 3–6% scale pop with `overshootClamping` spring. Active word gets accent color; inactive words sit at 0.55 opacity. Container `white-space: pre` because tokens carry leading spaces.

### 3. Variable Font Weight Animation
**What it looks like:** Text "loads" — strokes thicken from thin (wght 300) to black (wght 900) over ~20 frames, often word-by-word left to right. Reads as if the type is being printed in real time.
**Where used:** Modern/tech intros, stat callouts.
**Why trendy:** Variable fonts (Archivo, Bricolage Grotesque) made this trivial in AE 2024+; it reads as premium motion design.
**Technical breakdown:** Animate `fontVariationSettings: '"wght" 300 → 900'` per frame via interpolate. Requires a variable font actually loaded with the weight axis. Pairs with mask reveal for a two-axis entrance.

### 4. Tracking-In (letter-spacing contraction)
**What it looks like:** Wide-tracked caps (0.3em) contract to normal (0.02em) while fading in — a cinematic "title settling" feel.
**Where used:** Chapter titles, section markers, outro CTAs.
**Why trendy:** Zero-translate entrance; reads as confident and expensive. Standard in Netflix-style doc titles.
**Technical breakdown:** `letter-spacing: 0.28em → 0.02em` + opacity on ease-out. Pure CSS property animation — no transforms.

---

## Transitions

### 5. Whip Pan (directional blur swipe)
**What it looks like:** The frame swipes horizontally at extreme speed with heavy directional motion blur — the cut is hidden inside the blur. 4–10 frames total.
**Where used:** Between B-roll beats, scene energy bumps, match-on-action cuts.
**Why trendy:** Fern / Magnates Media staple. Adds kinetic energy without graphics.
**Technical breakdown:** Exiting scene `translateX(0 → -110%)` on an expo-in curve; entering scene `translateX(110% → 0)` expo-out. Motion blur simulated by 3–5 ghost copies at fractional offsets with decreasing opacity (what `<Trail>` does) or SVG `feGaussianBlur stdDeviation="X 0"` (true single-axis blur). True AE whip uses directional blur + echo.

### 6. Punch Zoom (snap-in scale)
**What it looks like:** Camera "punches" into the subject 8–15% over 6–10 frames with a hard expo landing — often on a music beat or emphasis word.
**Where used:** Stat reveals, reaction beats, comedic timing.
**Why trendy:** Replaces the slow Ken Burns drift when energy is needed; signature of fast-cut YouTube docs.
**Technical breakdown:** `scale(1 → 1.12 → 1.09)` with `Easing.bezier(0.85, 0, 0.15, 1)` (fast in, hard out). Land slightly over 1.0 (1.08–1.10) so the punch doesn't feel like a bounce. Optional micro camera shake (2–4px) for 8 frames after landing.

### 7. Match Cut / Zoom Punch Through
**What it looks like:** A circle/shape in scene A expands to fill frame and becomes scene B (iris), or a detail in A is matched by a same-position detail in B with a hard cut.
**Where used:** Doc transitions between locations/eras.
**Why trendy:** The "Johnny Harris map zoom" grammar — camera dives from globe → country → city.
**Technical breakdown:** Scale toward focal point with `transform-origin` at the focal coordinate; next scene starts at scale 2–3× zoomed into its own focal point and settles to 1.0. The eye reads it as one continuous camera move across the cut.

### 8. Light Leak / Film Burn at Cuts
**What it looks like:** Warm orange/red light bleeds across the frame exactly at the cut point, peaking mid-transition and retracting — the leak "carries" the viewer across the edit.
**Where used:** History/crime docs, montage sequences, era changes.
**Why trendy:** Instant filmic texture; masks hard cuts without a dissolve. Procedural (no asset needed).
**Technical breakdown:** WebGL light-leak overlay seeded per cut, `durationInFrames` ≈ 2× transition length, composited with screen blend. Or black-background leak video + `mix-blend-mode: screen`.

### 9. Glitch Cut (RGB split + slice displacement)
**What it looks like:** For 5–15 frames the image tears: RGB channels split 2–8px apart, horizontal slices shear left/right, then it snaps clean. Used at violent/shocking reveal moments.
**Where used:** Crime docs, tech channels, twist reveals.
**Why trendy:** One glitch beat per video = production value spike. Overuse kills it.
**Technical breakdown:** Three stacked copies with SVG `feColorMatrix` channel isolation + `mix-blend-mode: screen`, offset ±px via seeded random gating (active only on frames where `random(seed) > 0.7`). Slice displacement via `clip-path: inset()` strips with independent `translateX` jitter.

---

## Texture Treatments

### 10. Animated Film Grain
**What it looks like:** Fine luminance noise that *moves* every frame — the image breathes. Static grain reads as a filter; animated grain reads as film.
**Where used:** Entire history/crime styles, archival footage treatment.
**Why trendy:** The single biggest "generic → cinematic" upgrade. 35mm grain scans are the gold standard.
**Technical breakdown:** Video grain loop (1–2s) via `<OffthreadVideo>` + `mix-blend-mode: overlay`, opacity 0.10–0.20. Procedural alternative: small seeded noise tile (128px) upscaled with `image-rendering: pixelated`, re-seeded per frame via `random()` or `noise3D`.

### 11. Dust & Scratches / VHS Tracking
**What it looks like:** White hairline scratches, dust specks, and (for VHS) horizontal tracking tears with chromatic aberration at frame edges.
**Where used:** Archival segments within history/crime videos — signals "this is old footage."
**Why trendy:** Era signposting without a title card.
**Technical breakdown:** Black-background overlay video + `mix-blend-mode: screen`, or procedural: random thin white lines (1px, opacity 0.3) appearing for 1–3 frames at random X via seeded random. VHS adds 2–4px RGB split at edges + occasional full-width horizontal displacement band.

### 12. Halftone / Print Texture (document collage)
**What it looks like:** Newspaper/print dot pattern over images, with slight paper off-white and ink-blue duotone.
**Where used:** Document reveals, newspaper headlines in crime/history videos.
**Why trendy:** The "court evidence" aesthetic — pairs with cutout collage.
**Technical breakdown:** Radial-gradient dot pattern (CSS `background-image: radial-gradient(circle, #000 1px, transparent 1px)`, size 4–6px) as a screen/overlay layer; duotone via `filter: grayscale(1) sepia(0.3) hue-rotate(180deg)`-style chain or SVG feColorMatrix.

---

## Depth & Camera

### 13. 2.5D Parallax Photo Animation
**What it looks like:** A still photo comes alive — foreground subject drifts slightly more than background, with soft DOF blur separating planes. The "documentary photo treatment."
**Where used:** Every history/crime doc when only stills exist.
**Why trendy:** Makes archives feel shot on camera. LEMMiNO/Fern signature.
**Technical breakdown:** 2–4 layered planes (bg plate, subject cutout, fg element) driven by the same normalized camera progress at different rates: `scale = 1 + cam*depth*0.08`, `translateX = cam*depth*40px`. Foreground moves most. Static small `blur()` on non-focus planes. Cutouts prepared offline (remove.bg).

### 14. Handheld Camera Shake / Drift
**What it looks like:** Frame floats — 2–8px organic wander with micro-rotation (±0.3°). Never still, never jittery.
**Where used:** Verité/documentary b-roll, tension beats.
**Why trendy:** Kills the "slideshow" feel of static compositions.
**Technical breakdown:** Continuous simplex noise (`noise3D` with frame*time-factor 0.05–0.15) driving translate + rotate, with 3–5% overscan scale so edges never reveal. Decaying shake variant: amplitude envelope `1 → 0` over N frames after an impact beat.

### 15. Speed Ramp (time remapping)
**What it looks like:** Footage flows at 100% → drops to 30% slow-mo on the key moment → ramps back to 100%+, all in one continuous shot.
**Where used:** Product reveals, action b-roll, music-video beats.
**Why trendy:** Editors' favorite "make stock footage feel directed" move.
**Technical breakdown:** **Accumulated** playbackRate (never interpolate rate directly): per frame, source position = sum of all previous rates. In Remotion: `<Sequence from={frame}><OffthreadVideo trimBefore={accumulated} playbackRate={rate(frame)} src="...#disable"/></Sequence>`.

---

## Documentary Graphics

### 16. Map Zoom with Animated Route
**What it looks like:** Camera dives globe → region → city while a route line draws itself between points, with a pulsing dot at the tip.
**Where used:** Geography/context segments. Johnny Harris's signature.
**Why trendy:** Turns exposition into a journey; viewers expect it now.
**Technical breakdown:** Hi-res map image, `transform: scale(s) translate(...)` with `transform-origin` at focal point, `Easing.inOut(Easing.cubic)`. Route via SVG path + `evolvePath(progress, path)` (stroke-dashoffset draw-on); marker at `getPointAtLength(path, len*progress)`. Map source ≥2× output resolution.

### 17. Document/Newspaper Highlight Reveal
**What it looks like:** A document fills frame; a yellow marker highlight sweeps across the key line, then the camera punches into that line.
**Where used:** Evidence beats in crime/finance docs.
**Why trendy:** The "receipts" moment — audiences pause on these.
**Technical breakdown:** Document image with slow ken-burns; highlight = accent-color rect (opacity 0.35, multiply blend) whose width interpolates 0→100% over 15–20 frames on a linear wipe; then punch-zoom toward the highlighted region.

### 18. Photo Cutout Collage (crime board)
**What it looks like:** Cut-out photos pinned/taped on a textured board, dropped in one by one with soft shadows and slight rotations, connected by string/marker lines.
**Where used:** Crime documentaries, conspiracy explainers, relationship maps.
**Why trendy:** Instantly communicates "investigation."
**Technical breakdown:** Each photo: white border (padding 8–12px), `box-shadow` large/soft, `rotate(±2–4°)`, entrance = opacity + scale 1.1→1.0 settle (clamped spring). Connecting lines via SVG path draw-on. Board = paper/cork texture image at low brightness.

---

## Data & Stats

### 19. Count-Up Number Reveal
**What it looks like:** Big number counts 0 → target over ~1s with ease-out deceleration; unit/context lands after.
**Where used:** Stat scenes everywhere.
**Why trendy:** Motion gives the number weight; a static number reads as a slide.
**Technical breakdown:** `Math.round(interpolate(frame, [a, b], [0, target], {easing: Easing.out(Easing.cubic)}))` — interpolate (not spring) for the count so it lands exactly; spring only for the entrance pop. `fontVariantNumeric: 'tabular-nums'` prevents width jitter.

### 20. Bar/Line Chart Draw-On
**What it looks like:** Axes wipe in, bars grow from baseline with per-bar stagger (12-frame overlap), line charts draw left-to-right with a glowing tip.
**Where used:** Finance/data segments.
**Why trendy:** Animated data reads as analysis; static charts read as homework.
**Technical breakdown:** Bars: `spring({frame: frame - i*12})` scaleY from baseline. Line: `evolvePath(progress, linePath)` stroke-dashoffset; tip marker via `getPointAtLength`. D3 for scales/math, Remotion for time.

---

## Lower Thirds & Titles (2025)

### 21. Minimal Plate Lower Third
**What it looks like:** Solid dark plate (0.8–0.85 opacity black) with a 3px accent edge on the left, name + role inside; wipes in from the accent edge.
**Where used:** Speaker IDs, location stamps.
**Why trendy:** The broadcast standard — everything else (glass, gradients, glow) now reads as dated.
**Technical breakdown:** `clip-path: inset(0 100% 0 0 → 0 0% 0 0)` linear wipe 12–18 frames; text inside cuts in 4 frames after the plate starts.

### 22. Brushed/Handwritten Underline Draw-On
**What it looks like:** A rough brush-stroke underline draws itself under the keyword, 8–15 frames, with a tapered end.
**Where used:** Keyword emphasis in educational/essay content.
**Why trendy:** Humanizes digital type; LottieFiles has thousands of free stroke assets.
**Technical breakdown:** SVG path + `evolvePath` (dash draw-on), `strokeLinecap: round`, or Lottie JSON of a brush stroke via `@remotion/lottie`.

---

## Trend-Report Consensus (2024–2026)

Across School of Motion / Motion Array / Envato trend reports, the recurring macro-trends:
1. **Texture over polish** — grain, dust, print, paper (anti-corporate)
2. **Kinetic typography as narration** — text moves with VO, not beside it
3. **2.5D everything** — flat is dead for documentary; depth planes everywhere
4. **Camera moves, not object moves** — the frame is a camera; graphics hold still inside it
5. **One hero effect per video** — a single signature moment (glitch, whip, match cut) beats constant decoration
6. **Editorial restraint** — transitions are cuts/fades/whips; bouncy UI easing is the mark of templates

**Design implication for this pipeline:** per-style identity = (grade look + grain + camera behavior + ONE signature move). Not more effects — better-chosen few.
