# Free Motion Graphics Assets for Remotion — Research Report

**Date:** 2026-07-22 · **Purpose:** Compositing sources for `<OffthreadVideo>`, `@remotion/lottie`, CSS `mix-blend-mode`, and native Remotion packages. All resources verified free + commercially usable unless flagged.

---

## 1. Free Motion Overlay Sources

General compositing rule for Remotion: overlays come in two forms — **(a) true alpha** (ProRes 4444 / VP9-with-alpha / MOV) → render directly with `<OffthreadVideo>`; **(b) black-background** (most free clips) → composite with `mix-blend-mode: screen` (light-based effects: leaks, bokeh, dust, smoke) or `overlay`/`soft-light` (grain/texture). Green-screen variants need keying (see §4).

| Source | URL | License | Formats / Alpha | Notes |
|---|---|---|---|---|
| **Pixabay Video** | https://pixabay.com/videos/search/grain%20overlay | Pixabay Content License — free commercial use, **no attribution** | MP4 (H.264), mostly **black background**; small "alpha channel" category (510+ clips) | ~1,870 grain overlays, 2,000+ film overlays, large smoke/ink/particle/bokeh/VHS sets. Best first stop: bulk CC-equivalent, API available (`PIXABAY_API_KEY`). |
| **Pexels Video** | https://www.pexels.com/search/videos/film%20grain | Pexels License — free commercial, no attribution | MP4, mostly black background | Good for smoke/fog/bokeh/light-leak plates. API available (`PEXELS_API_KEY`). |
| **Mixkit** (Envato) | https://mixkit.co/free-stock-video/light-leak | Mixkit Free License — free commercial, no attribution | MP4, black background | Curated light leaks, film burns, VHS, glitch, smoke, dust. One of the cleanest licenses. |
| **Videezy** | https://www.videezy.com/free-video/alpha-channel | Per-clip: many **CC BY** — attribution usually required | MP4/MOV, real **alpha-channel category (483 clips)** | Quality varies; check license badge per clip. Good for particles, ink bleeds, VHS. |
| **Videvo** (free tier) | https://www.videvo.net | **CC BY 3.0** or **Videvo Attribution License** — commercial OK w/ credit | MP4/MOV; some alpha | 18,000+ free clips. Fine if credits are acceptable. |
| **ProductionCrate / FootageCrate** | https://www.productioncrate.com | Royalty-free commercial **even on free tier**. **5 downloads/day free** | MP4 + many **true-alpha** clips; green-screen variants | Excellent for smoke/fog/fire/particles/debris. Daily cap is the only limit. |
| **Motion Array freebies** | https://motionarray.com/learn/video-effects/free-film-grain | Free w/ account; royalty-free commercial | MP4, black background | 19+ film grain overlays, 8mm grain pack, "Old Film Toolkit". |
| **Rocketstock (Shutterstock)** freebies | https://www.shutterstock.com/blog/free-overlays-for-product-shots | "100% free — use in any project" | MP4 4K, black background | 13 free 4K light leaks. Newsletter signup. |
| **PremiumBeat (Shutterstock)** freebies | https://www.premiumbeat.com/blog/7-places-find-free-light-leaks | Royalty-free commercial | MP4 | Curated free overlay packs. |
| **Enchanted Media** | https://www.enchanted.media/free-premiere-pro-light-leak-overlays | "Copyright free for broadcast, motion picture and online" | MP4 1080p, black bg, loop-ready | 20 bokeh light leaks + scratched-film/leaks loop. |
| **Color Grading Central** | https://www.colorgradingcentral.com/free-film-grain-overlay-4k | No attribution required | MP4 4K (real 35mm scans), 18%-gray bg → `overlay` blend | 5 authentic 35mm grain files. |
| **FX Elements** | https://www.fxelements.com/free | Free clip tier, royalty-free | **Alpha-channel VFX clips** (specialty) | True-alpha fire/smoke/energy. |

**Pipeline recommendation:** Pixabay + Pexels (API) primary; Mixkit + ProductionCrate for curated overlays; assume **black background → `mix-blend-mode: screen`** for light/dust/leak clips.

---

## 2. Lottie

### LottieFiles license
- **Lottie Simple License** (https://lottiefiles.com/page/license): free download, modification, distribution, public display — **including commercial, NO attribution required**.
- ⚠️ Modified files must carry same license (irrelevant for rendered video embedding).
- ⚠️ Animations *created in their editor under Free plan* are non-commercial — public library downloads under Simple License are commercial-safe.
- ⚠️ Some files are pirated re-uploads; prefer creators with track records.

### Useful categories
Search lottiefiles.com: **arrows, underline, scribble/doodle, hand drawn, checkmark, icons, transitions, social icons, loading, confetti, shapes morph**. Downloadable as **GIF/MP4/Lottie JSON** — MP4 export is a fallback for files that flicker in Remotion.

### Remotion integration
- Package: **`@remotion/lottie`** (+ peer `lottie-web`).
- `<Lottie animationData={data} />`; load JSON via `staticFile('anim.json')` + `delayRender`/`continueRender`, or remote URL.
- Helpers: `getLottieMetadata()`, `speed` prop, loop control.
- **Gotchas:** Remotion seeks with `goToAndStop()` → **limited expression support**; AE-expression-based animations can render non-deterministically → flicker. Test per file; fallback to MP4 export + `<OffthreadVideo>`. Never use plain `lottie-react` uncontrolled (won't sync to frame clock).
- Docs: https://www.remotion.dev/docs/lottie

### Other free Lottie sources
Iconscout Lottie (free tier, attribution), Flaticon animated icons (attribution), Lordicon (free subset), Drawer/UseAnimations (MIT-style), Rive community (`@remotion/rive` exists).

---

## 3. Remotion-Native Libraries / Packages

| Package | Install | What it provides |
|---|---|---|
| **@remotion/transitions** | `npm i @remotion/transitions` | `<TransitionSeries>` + presentations: `fade`, `slide`, `wipe` (8 dirs), `flip`, `clockWipe`, `iris`, `zoomBlur`, `dreamyZoom`, `filmBurn`, `linearBlur`, `bookFlip`, `zoomInOut`, `dissolve`, `ripple`, `crosswarp`, `crossZoom`, `swap`, `cube`, `none`. Timings: `linearTiming`, `springTiming`. Custom presentations supported. Both scenes render simultaneously during transition (heavier Chrome load — our FFmpeg xfade stays valid for batch). |
| **@remotion/light-leaks** (v4.0.415+) | `npm i @remotion/light-leaks` | `<LightLeak durationInFrames seed hueShift>` — **procedural WebGL light leak**, no asset download. Pairs with `<TransitionSeries.Overlay>` to mask cuts. |
| **@remotion/shapes** | `npm i @remotion/shapes` | SVG generators + components: `makeArrow`, `makeRect`, `makeCircle`, `makeEllipse`, `makeTriangle`, `makeStar`, `makeHeart`, `makePie`, `makeCallout`, `makeSpark`, `makePolygon`. |
| **@remotion/paths** | `npm i @remotion/paths` | SVG path math: measure length, get point at length, **`evolvePath`** → **line-draw / stroke-dashoffset animation** (map routes, underlines, signatures). Zero deps, MIT. |
| **@remotion/noise** | `npm i @remotion/noise` | **Deterministic simplex noise** (`noise2D/3D/4D`) — procedural film grain + handheld camera shake without assets. MIT. |
| **@remotion/three** | `npm i three @react-three/fiber @remotion/three @types/three` | `<ThreeCanvas>` wired to Remotion time; `useVideoTexture()`, `useOffthreadVideoTexture()`. Requires `--gl=angle`. |
| **@remotion/captions** (v4.0.216+) | `npm i @remotion/captions` | `Caption` type, `parseSrt()`, `createTikTokStyleCaptions()` → per-word timing tokens for kinetic captions. |
| **@remotion/google-fonts** | `npm i @remotion/google-fonts` | Typed loader: `loadFont()` per family/weight/subset; blocks render until loaded. |
| **@remotion/motion-blur** | `npm i @remotion/motion-blur` | `<Trail layers lagInFrames>` (ghost-frame trails) + `<CameraMotionBlur shutterAngle samples>` (film-camera blur). Expensive — keep subtrees small. |
| **@remotion/skia** | `npm i @remotion/skia @shopify/react-native-skia` | Skia 2D canvas — GPU shaders, paths, blur/blend. |

---

## 4. Chroma Key in Remotion

No official `<ChromaKey>` component, but known recipes:

1. **WebGL shader route** — draw `<Video>` frame into texture, fragment shader computes color distance from key color in YUV space (OBS chroma-key algorithm). Docs: remotion.dev/docs/shaders. Via `@remotion/three` `onBeforeCompile` on `useVideoTexture()`.
2. **Pre-convert offline (recommended for our pipeline):** key at the **FFmpeg stage** (`chromakey=0x00FF00:0.15:0.08`) when pre-normalizing overlay assets, output webm-with-alpha (libvpx-vp9 `-pix_fmt yuva420p`), skip in-browser keying. In-browser WebGL keying is the fallback.

---

## 5. Free Fonts for Motion Graphics (via @remotion/google-fonts)

Trendy 2025 picks, all Google Fonts (OFL, free commercial):

**Condensed grotesques / kinetic-type workhorses**
- **Archivo / Archivo Expanded & Black** — variable weight+width, kinetic-typography staple
- **Oswald**, **Barlow Condensed**, **Anton** — bold condensed headline punches
- **Bricolage Grotesque** — trendy variable grotesque
- **Special Gothic Expanded One** — industrial/brutalist

**Mono (documentary/data/dossier look — crime/history styles)**
- **Space Mono**, **IBM Plex Mono**, **JetBrains Mono**, **Roboto Mono**
- **Special Elite** (typewriter, for crime docs — use sparingly)

**Serif display (editorial/documentary authority)**
- **Instrument Serif** — trendy 2024-25 italic-forward display serif
- **Newsreader** — variable serif for documentary pull-quotes
- **Playfair Display**, **Libre Caslon**, **DM Serif Display**

**Neutral sans body/lower-thirds**
- **Inter**, **DM Sans**, **Figtree**, **Outfit**, **Work Sans**

Load pattern: `import {loadFont} from '@remotion/google-fonts/Archivo';` → `const {fontFamily} = loadFont('normal', {weights: ['700','900'], subsets: ['latin']});`

---

## 6. Free SFX Sources

| Source | URL | License | Best for |
|---|---|---|---|
| **Pixabay SFX** | https://pixabay.com/sound-effects/ | Free commercial, **no attribution** | Whoosh/riser (3,300+), glitch hits, film burn. **First choice** — matches existing Pixabay integration. |
| **Mixkit SFX** | https://mixkit.co/free-sound-effects/whoosh | Free commercial, no attribution | Curated whooshes, cinematic impacts, stingers, glitch. |
| **Freesound** | https://freesound.org | Per-sound: **CC0**, **CC BY**, **CC BY-NC (avoid)**. Filter license=CC0 or CC BY. | Deepest library: risers, tape stops, film burns, VHS noise. |
| **ProductionCrate SoundsCrate** | https://www.productioncrate.com | Royalty-free, free tier 5/day | Cinematic hits/whooshes/risers. |
| **Zapsplat** | https://www.zapsplat.com | Free tier commercial **with attribution** | Huge transitional SFX library. |

**Recommendation:** Pixabay SFX + Mixkit primary (attribution-free); Freesound CC0-filtered for exotic (film burn crackle, VHS tracking).

---

## Quick-implementation cheat sheet
1. Grain → **@remotion/noise** (procedural) or Pixabay black-bg grain + `mix-blend-mode: overlay`.
2. Light leaks at cuts → **@remotion/light-leaks** (procedural, no asset download).
3. Doodles/arrows/checkmarks → LottieFiles JSON + `@remotion/lottie` (test for expression flicker; MP4 fallback).
4. Line-draw underlines/maps → `@remotion/paths` + stroke-dashoffset.
5. Green-screen-only overlays → FFmpeg `chromakey` → VP9-alpha webm → `<OffthreadVideo>`.
6. Transition SFX → Pixabay/Mixkit whoosh, synced at FFmpeg xfade points.
