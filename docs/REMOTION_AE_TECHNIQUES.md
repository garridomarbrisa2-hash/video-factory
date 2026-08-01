# Remotion 4.x: After Effects–Style Motion Techniques — Implementation Research

**Scope:** Verified against remotion.dev docs as of July 2026 (Remotion 4.x; several APIs noted with exact versions). The pipeline pins one xfade per style with `Easing.linear` — findings below are ordered to be directly consumable by `editMotion.ts` / `styleSystem.ts`. **Installed version: 4.0.495 → every feature below is available.**

---

## 1. Film grain / noise overlay

`@remotion/noise` exists (v3.2.32+, MIT): `noise2D()`, `noise3D()`, `noise4D()` — deterministic simplex noise, seedable, returns `[-1, 1]`.

Approaches (in order):
- **(a) Looping video overlay** — pre-generate 1–2s grain loop, `<OffthreadVideo muted style={{mixBlendMode: 'overlay', opacity: 0.15}} />` wrapped in `<Loop>`. Most render-friendly (FFmpeg extracts off-thread).
- **(b) Procedural canvas grain** — small 128×128 `ImageData` tile from `noise3D('grain', x, y, frame*speed)`, CSS `image-rendering: pixelated; transform: scale()` upscale + `mixBlendMode: 'overlay'`. Deterministic because seeded.
- **(c) SVG `feTurbulence`** — animate `seed` per frame. CPU-rasterized, slow at 1080p fullscreen.

**Perf:** per-frame `ImageData` at 1080p is slow — generate small tile + upscale via CSS.

Docs: https://www.remotion.dev/docs/noise

---

## 2. Light leaks / film burns / dust overlays

**Big find:** `@remotion/light-leaks` (v4.0.415+) — WebGL `<LightLeak durationInFrames seed hueShift>`; reveals over first half, retracts over second. With `<TransitionSeries.Overlay>` you get light-leak transitions without timeline shortening. Also `filmBurn()` built-in transition presentation (v4.0.467+).

**Video-based leaks/dust:** `<OffthreadVideo>` + `mix-blend-mode: 'screen'` (screen for black-bg leaks/dust, `overlay` for texture). No rendering gotchas — it's pure Chrome compositing. Prefer black-background plates + `screen` blend (BMP extraction, no alpha cost).

**Perf:** `<LightLeak>` is WebGL — render with `chromiumOptions: {gl: 'angle'}` (we already do).

Docs: https://www.remotion.dev/docs/light-leaks

---

## 3. Whip-pan / punch-zoom transitions

- **Punch-zoom:** `interpolate(frame, [0,8,16],[1,1.15,1], {easing: Easing.bezier(0.85,0,0.15,1)})` snap-in; whip-pan adds `translateX` covering >100% width in 6–12 frames.
- **Directional motion blur:** CSS `blur()` is isotropic. Options:
  - **Ghost frames:** 3–5 offset copies with decreasing opacity — exactly what `<Trail>` does. Cheapest robust option.
  - **SVG `feGaussianBlur stdDeviation="X 0"`** — true single-axis blur via `filter: url(#dirblur)`.
  - **`linearBlur()` presentation** (v4.0.466+) — ready-made whip-blur shader transition; `zoomBlur()` for radial blur zoom.

**Perf:** large/animated CSS blur radii are expensive — keep ≤20px, prefer `<Trail>` for moves, reserve shader blurs for 15–30-frame transition windows.

---

## 4. Motion blur — `@remotion/motion-blur`

Verified (v3.2.31+). Two HOCs:
- **`<Trail layers={50} lagInFrames={0.1} trailOpacity={1}>`** — time-offset duplicates → trail/ghost blur. Children **must be absolutely positioned** (wrap in `<AbsoluteFill>`).
- **`<CameraMotionBlur shutterAngle={180} samples={10}>`** — film-camera-style blur averaging time-offset renders. Destructive to colors — keep samples 5–10.

**Perf:** `<CameraMotionBlur samples={10}>` renders subtree 10× per frame; `<Trail layers={50}>` 50×. Keep wrapped subtree small, never nest around `<OffthreadVideo>` (N× decode cost).

Docs: https://www.remotion.dev/docs/motion-blur

---

## 5. 2.5D parallax photo animation

No special package needed. Layer 2–4 planes (`<Img>`/`<AbsoluteFill>`), drive each with the same normalized camera progress at different rates:

```ts
const cam = interpolate(frame, [0, dur], [0, 1], {easing: Easing.inOut(Easing.cubic)});
// per layer: scale = 1 + cam * depth[i] * 0.08; translateX = cam * depth[i] * 40
```

Foreground moves more than background → dolly illusion. Add global `scale(1.05→1.12)` to sell camera motion. Static small `blur()` on bg/fg planes fakes depth-of-field.

**Perf:** transforms are compositor-cheap. Pre-cut subjects offline — no live per-frame masking.

---

## 6. Kinetic typography

- **`@remotion/captions`** (v4.0.216+): `Caption` type. `createTikTokStyleCaptions({captions, combineTokensWithinMilliseconds})` → pages with per-word `fromMs`/`toMs` tokens. **Whitespace-sensitive** — spaces must lead each token; render with `white-space: pre`. For our custom-TTS pipeline, construct `Caption[]` from per-line VO timestamps.
- **Mask line reveals:** `overflow: hidden` wrapper + inner `translateY(100% → 0)` with spring or `Easing.out(Easing.cubic)` — pure CSS, GPU-cheap.
- **Variable font weight animation:** `@remotion/google-fonts` `loadFont()` (narrow `weights`/`subsets`!). Animate `fontVariationSettings: '"wght" 400 → 900'` per frame.
- **Text measurement:** `@remotion/layout-utils` `measureText()`/`fitTextOnNLines()`; `@remotion/rounded-text-box` for TikTok-style backing plates.

Docs: https://www.remotion.dev/docs/captions/api · https://www.remotion.dev/docs/google-fonts

---

## 7. Glitch effect

No built-in glitch API. Approaches:
- **RGB channel split:** three stacked copies, `mix-blend-mode: screen`, channel isolation via SVG `feColorMatrix` (zeroing two channels), offset ±2–8px with `random()` gating (active only some frames: `random(seed) > 0.7`).
- **Slice displacement:** N strips with `clip-path: inset(Y1 0 Y2 0)` + independent `translateX` jitter — clip-path is compositor-friendly.
- Restrict glitches to short bursts (5–15 frames).

Docs: https://www.remotion.dev/docs/random

---

## 8. Speed ramp / time remapping

Verified recipe: **Do NOT** do `playbackRate={interpolate(...)}` — frames evaluate independently. Correct pattern **accumulates** past rates:

```tsx
const remapSpeed = (frame: number, speed: (f: number) => number) => {
  let framesPassed = 0;
  for (let i = 0; i <= frame; i++) framesPassed += speed(i);
  return framesPassed;
};
// <Sequence from={frame}><OffthreadVideo trimBefore={Math.round(remapped)} playbackRate={speed(frame)} src="...#disable" /></Sequence>
```

Append **`#disable`** to URL to kill media-fragment hints. Reverse playback **not supported**. Doesn't work with newer `<Video>` from `@remotion/media` — use `<OffthreadVideo>`.

Docs: https://www.remotion.dev/docs/videos/accelerated-video

---

## 9. Documentary map zooms + route drawing

- **Map zoom:** hi-res static map `<Img>`, animate `scale` + `translate` toward focal point with `transform-origin` at that point, `Easing.inOut(Easing.cubic)`. Source ≥2× output resolution.
- **Route draw-on — `@remotion/paths`:** `getLength(path)`, `getPointAtLength(path, len)`, **`evolvePath(progress, path)`** (returns `strokeDasharray`/`strokeDashoffset`), `getTangentAtLength()`. Route line via `evolvePath`, pulsing marker at tip via `getPointAtLength`. Put `<svg>` inside the zooming layer so the route scales with the map.

Docs: https://www.remotion.dev/docs/paths/evolve-path

---

## 10. Animated counters and chart draw-ons

No official chart lib — canonical hand-rolled SVG:
- **Bars:** `spring({frame: frame - i*12, fps, config})` per bar with stagger, scaling from baseline.
- **Line draw-on:** `evolvePath(lineProgress, linePath)`; tip marker via `getPointAtLength`.
- **Counters:** `Math.round(interpolate(frame, [a,b], [0, target], {easing: Easing.out(Easing.cubic)}))` — interpolate for the count (deterministic landing), spring only for entrance pop; `overshootClamping: true` if springing values; `fontVariantNumeric: 'tabular-nums'` to prevent jitter.
- **D3 example** exists on remotion.dev resources — D3 for math/scales, Remotion for time.

Docs: https://www.remotion.dev/docs/spring

---

## 11. 3D — `@remotion/three` + React Three Fiber

Officially maintained. `<ThreeCanvas>` wired to Remotion time (animate off `useCurrentFrame()`, not `useFrame()`); `useVideoTexture()`/`useOffthreadVideoTexture()`. Requires `chromiumOptions: {gl: 'angle'}`.

**When worth it:** real 3D camera moves, extruded logos/text, product mockups with live video textures. **Not worth it** for flat editorial motion — CSS 3D (`perspective` + `rotateY`) covers card tilts at a fraction of the cost.

---

## 12. Real GLSL shaders

Official ways (all verified):
1. **Raw WebGL canvas** — remotion.dev/docs/shaders, update uniforms from `useCurrentFrame()`, render `--gl=angle`.
2. **`<HtmlInCanvas>`** (v4.0.455+) — draws live DOM into canvas, post-process with WebGL2/WebGPU shaders.
3. **`createEffect()` + `@remotion/effects`** (v4.0.464+) — reusable shader effects with Studio-editable controls.
4. **Shader transitions:** `makeHtmlInCanvasPresentation()` — docs walk through porting gl-transitions.com shaders. Several built-in (`filmBurn`, `linearBlur`, `zoomBlur`, `dissolve`, `ripple`…).

---

## 13. Easing curves that mimic AE speed graphs

`Easing` module (ported from React Native): `linear`, `quad`, `cubic`, `poly(n)`, `sin`, `circle`, `exp`, `back(s)`, `bounce`, `elastic`, **`bezier(x1,y1,x2,y2)`**, modifiers `in/out/inOut`, and **`Easing.spring(config)`** (v4.0.476+).

| AE keyframe assistant | Remotion |
|---|---|
| Easy Ease (33% influence) | `Easing.bezier(0.33, 0, 0.67, 1)` ≈ `Easing.inOut(Easing.cubic)` |
| Easy Ease strong (65–75%) | `Easing.bezier(0.65, 0, 0.35, 1)` |
| Snap/whip (fast in, hard out) | `Easing.bezier(0.85, 0, 0.15, 1)`; `Easing.out(Easing.exp)` for punch-zoom landings |
| Inertial bounce / overshoot landing | `spring({config:{stiffness: 120–200, damping: 12–20, mass: 0.5–1}})`; no-bounce: `damping: 200`; playful: `Easing.out(Easing.back(1.7))` |
| **overshootClamping** | spring config flag (default false): when true, value never passes target — use for opacity/scale-to-100%. |

Physics intuition: **stiffness↑ = snappier, damping↑ = less oscillation (200 ≈ critically damped), mass↑ = heavier.** `spring({durationInFrames})` stretches to exact duration for VO beat sync; `durationRestThreshold: 0.001` for transitions.

Docs: https://www.remotion.dev/docs/easing · https://www.remotion.dev/docs/spring

---

## 14. Mask wipes / luma mattes / TransitionSeries

`@remotion/transitions` (v4.0.53+): `<TransitionSeries>` = `<Series>` + `<TransitionSeries.Transition>` (both scenes overlap — 2× render cost during transition) + `<TransitionSeries.Overlay>` (v4.0.415+, no shortening).

**Built-in presentations:** `fade`, `slide`, `wipe` (8 dirs), `flip`, `clockWipe`, `iris`, `zoomBlur`, `dreamyZoom`, `filmBurn`, `linearBlur`, `bookFlip`, `zoomInOut`, `dissolve`, `ripple`, `crosswarp`, `crossZoom`, `swap`, `cube`, `none`.

**Custom presentation API:** function returning `{component, props}`; component receives `children`, `presentationDirection`, `presentationProgress`, `passedProps`. The official docs example is literally a mask-wipe (star clipPath grown with progress via `@remotion/shapes` + `@remotion/paths`).

**Intra-scene mask wipes:** CSS `mask-image: linear-gradient()` animating `mask-position`, or `clip-path: inset()/polygon()` interpolation — GPU-accelerated. SVG `<mask>` with grayscale content = true luma matte, rasterizes fine.

---

## 15. Camera shake / handheld feel (deterministic)

**`random(seed)` from `remotion`** — deterministic pseudorandom `[0,1)`; same seed → same value across render threads (why `Math.random()` breaks multithreaded rendering).

Smooth shake needs **continuous** noise — `noise3D()` with frame as time axis:

```ts
const x = noise3D('shake-x', 0, 0, frame * 0.15) * amp;
const y = noise3D('shake-y', 0, 0, frame * 0.15) * amp;
const r = noise3D('shake-r', 0, 0, frame * 0.1) * 0.4;
// transform: translate(x, y) rotate(r) scale(1.03)  ← overscan prevents edge reveal
```

Time multiplier 0.05–0.15 = handheld drift; >0.3 = earthquake. Modulate amp over time (build then settle). Stepped/action-cam: quantize `Math.floor(frame/2)`.

Docs: https://www.remotion.dev/docs/random · https://www.remotion.dev/docs/noise

---

## 16. Text stroke/outline, text on path, handwritten draw-ons

- **Text stroke:** CSS `-webkit-text-stroke: 2px #fff` + `-webkit-text-fill-color: transparent` for hollow text. Crisp, animatable, cheap. Alternative: SVG `<text>` with `paint-order: stroke`.
- **Text on path:** SVG `<textPath href="#path" startOffset={...}>` — animate startOffset per frame.
- **Handwritten underline / draw-on:** `evolvePath(progress, path)` → spread `strokeDasharray`/`strokeDashoffset` on `<path>` with `strokeLinecap="round"`. THE draw-on primitive; marker dot at tip via `getPointAtLength`.

---

## Appendix — version gates (installed: 4.0.495 → ALL available)

| Feature | Min version |
|---|---|
| `@remotion/noise`, `@remotion/motion-blur` | 3.2.x |
| `<TransitionSeries>` / presentations | 4.0.53 |
| `@remotion/captions` | 4.0.216 |
| `<TransitionSeries.Overlay>`, `@remotion/light-leaks` | 4.0.415 |
| `<HtmlInCanvas>`, `@remotion/effects` | 4.0.455–464 |
| `linearBlur()`, `filmBurn()` presentations | 4.0.466–467 |
| `Easing.spring()` | 4.0.476 |

**Most impactful upgrades (ranked):**
1. `@remotion/light-leaks` + Overlay at cut points — replaces per-style single-xfade monotony
2. `Easing.bezier` AE-style curves + `Easing.spring` in `editMotion.ts` (relax "linear-only" for landings)
3. `random()`/`noise3D` handheld shake + video/procedural grain for texture
4. `<Trail>` for whip/punch accents
5. `@remotion/paths` `evolvePath` for map routes + underline draw-ons
6. HTML-in-canvas shader transitions (`filmBurn`, `linearBlur`) — available now on 4.0.495
