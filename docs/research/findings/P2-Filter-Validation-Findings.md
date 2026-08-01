# P2 — FFmpeg Filter Validation Findings

Research date: 2026-07-21
Research method: Tavily web searches (10 queries) across FFmpeg trac/wiki, ffmpeg.org docs, Stack Overflow/Super User, Phoronix, FFmpeg-devel mailing list, and practitioner blogs.
Scope: production-readiness of key filters used in automated video pipelines, with emphasis on the filters requested: zoompan, minterpolate, geq, xfade, perspective, plus version-compatibility and deprecation landscape.

Tier legend:
- **T1 — Production-ready**: stable, well-tested, safe for unattended automation with documented constraints.
- **T2 — Production-ready with guardrails**: works reliably only inside documented parameter ranges / preconditions; needs input normalization or validation.
- **T3 — Use with caution**: known artifacts/performance traps; requires per-clip QA or fallback logic.
- **T4 — Experimental / avoid for automation**: known bugs, unmaintained paths, or unpredictable output.

---

## 1. zoompan — T3 (known jitter bug; usable only with workarounds)

### Known issues and artifacts
- **Long-standing jitter/jiggle bug (FFmpeg trac ticket #4298, filed ~2016)**: zoompan rounds the evaluated `x`/`y` expressions to whole pixels internally. Any non-integer pan velocity produces uneven direction changes — visible as zig-zag / shaking, especially at slow pan speeds on low-resolution inputs. Multiple Stack Overflow / Super User / Video Production SE threads confirm the bug persists in user experience across many versions (3.1 through 4.x era reports; still referenced as "the known bug" in 2024-era guides).
- **A fix patch exists but landed late**: ffmpeg-devel 2020-02 thread "[PATCH v4] avfilter/vf_zoompan: fix shaking when zooming" shows the fix approach — internally overscaling the input and doing sub-pixel-aware crop position math (`ceil(av_clipd(...))` then chroma-aligned masking). This class of fix is in modern releases (5.x+), but community reports indicate residual jitter remains with arbitrary x/y expressions; the "upscale first" workaround is still the standard advice even in recent guides (ffmpeglab Ken Burns guide, 2025).
- **Default fps trap**: zoompan's private `fps` option defaults to **25**, independent of input. Forgetting `fps=` causes frame-rate mismatch, "zoom resets at 9.5s" artifacts, slowed-down output, and 23.7 fps reports (Super User #1094743, SO #53691231).
- **Image inputs default to 25 fps** unless `-framerate` is set on the input — interacts with the above.

### Safe parameter ranges / recipes
- `z` (zoom) expression range is **1–10**; default 1. `d` (duration per input frame) default 90. `s` default hd720.
- **Reliable anti-jitter recipe (community consensus)**:
  1. Upscale the source 2–8x first (`scale=8000x4000` or similar) so pixel-rounding is proportionally smaller, OR
  2. Wrap x/y expressions in `trunc()` to make the rounding deterministic, OR
  3. Compute zoom with integer-safe math, e.g. `z='trunc(iw*10*(1+0.0015*in)/2)*2/(iw*10)'` (forces zoom steps that land on even pixel boundaries).
  Downscale after zoompan to the delivery size.
- Always set zoompan's own `s=` and `fps=` inside the filter rather than relying on outer `-s`/`-r` to avoid double scaling and rate mismatches.
- Clamp pan expressions to avoid black borders: `x='max(0,min(iw-iw/zoom, <expr>))'`.

### Version compatibility
- Present since 2.x; behavior of expressions (`pzoom`, `px`, `py`, `duration`, `pduration` variables) stable across 4.x–8.x docs.
- The anti-shake overscale fix is present in 5.x+; treat 4.x and earlier as definitively jittery without the upscale workaround.

### Performance
- The 8x-upscale workaround multiplies pixel work ~64x at the zoompan stage; significant for batch jobs. Prefer trunc-based expressions or moderate 2–4x upscale when throughput matters.

### Recommended alternatives
- For video (not stills): `scale` + animated `crop` with per-frame expressions often gives smoother motion than zoompan.
- For Ken Burns slideshows: render motion via `zoompan` at high resolution once, or use gl-transition / custom OpenGL paths for GPU-smooth pans.

---

## 2. minterpolate — T2/T3 (excellent output quality; severe performance and scene-change caveats)

### Known issues and artifacts
- **Artifact classes observed in practice** (hellocatfood glitch-aesthetics series, systematic parameter sweep):
  - Morphing/warping smears around fast-moving object boundaries when `search_param` too low (default 32 produces "not much movement" then mush).
  - Over-smearing with extreme `search_param` (2000) — diminishing returns beyond ~400.
  - Wrong interpolation across cuts unless scene-change detection is tuned: `scd=fdiff` (default) replaces interpolated frames at cuts; `scd=none` produces cross-cut morph artifacts.
- **Works well**: moderate motion, 24/25→50/60 fps conversion of film/TV content with `mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1` (this exact recipe is the community-standard "quality" preset, Super User #178503 top answer).
- **Fails / looks bad**: very fast motion, heavy occlusion, screen content, animation with strobing, low-detail footage (motion vectors random → warping).
- **Single-threaded filter** (Programster blog): cannot use multiple threads; standard workaround is splitting the source into chunks, processing in parallel ffmpeg instances, and stitching. This is the #1 operational constraint for automation.
- `esa` (exhaustive search) `me` algorithm: ~4 hours for short clips in one test — effectively unusable.

### Safe parameter ranges
- Recommended baseline: `minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1`
- `search_param`: 32 (default) → often too small; **64–400 is the useful band**; >400 rarely helps.
- `mb_size`: default 16; keep 8–16.
- `me` algorithm: default `epzs` is the right speed/quality trade; avoid `esa` (exhaustive) and treat `tss`/`tdls` as speed fallbacks.
- Keep `scd` at default (`fdiff`) for general content; only use `scd=none` for intentional morph effects.
- `vsbmc=1` reduces boundary blur but costs more time.

### Version compatibility
- Introduced in libavfilter November 2016 (FFmpeg 3.2 era). Options set (`mi_mode`, `mc_mode`, `me_mode`, `me`, `mb_size`, `search_param`, `vsbmc`, `scd`) stable through 8.0 docs.
- Must use `-filter:v`/`-vf` stream specifier; bare `-filter` fails when non-video streams exist.

### Performance benchmarks
- Single-threaded; order-of-magnitude slower than realtime for 1080p mci/aobmc. Chunked-parallel workflow is mandatory for batch automation.
- `mi_mode=blend` (frame averaging) and `tblend` are 10–100x faster fallbacks when motion-compensated quality isn't required.

### Recommended alternatives
- `framerate` filter (simpler interpolation, faster, lower quality).
- `tblend`+`-r` for motion-blur-style speedup.
- External: RIFE / SVP / Butterflow-class tools (Butterflow effectively abandoned; RIFE is the modern ML choice) when minterpolate quality is insufficient.

---

## 3. geq (generic equation) — T2 (powerful and correct, but slow by design)

### Known issues and limits
- **Officially documented as slow**: "Note: this filter is slow. For faster processing you should use a dedicated filter." (ffmpeg-filters manual, repeated across all versions). Per-pixel expression evaluation with no SIMD; performance scales with (pixels × expression complexity).
- **Expression complexity**: full `eval` expression language per pixel; nested function calls, `hypot`, `sin`, `random`, `st/ld` state all work but multiply cost. Real-world complex examples (moving-light demo) run at small sizes (256×256) for a reason.
- **Threading caveat**: geq uses slice threading, but **each slice gets its own expression state** — expressions depending on persistent state (`st`/`ld` across pixels) require `-filter_threads 1` (documented), eliminating parallelism.
- **RGB vs YUV mode trap**: to operate in RGB you must set at least one of `r/g/b` expressions (even as identity `g='g(X,Y)'`); luma-only expressions imply YUV mode. Silent wrong-colorspace operation is a common beginner bug (Super User #1789950).
- Out-of-range `p(X,Y)` accesses are clipped to edge (documented) — safe but can produce edge-smear artifacts in custom convolution expressions.

### Safe parameter ranges / usage guidance
- Use for: per-pixel alpha manipulation (`a='0.3*alpha(X,Y)'`), gradients, emboss, custom color remapping, procedural generation on `nullsrc`.
- Avoid for: anything achievable by a dedicated filter (eq, colorchannelmixer, curves, vignette, lut/lut3d, convolution) — those are SIMD-optimized and 10–1000x faster.
- Keep frames small or expressions simple when used procedurally; benchmark before batch deployment.

### Version compatibility
- Ported from libmpcodecs in the 2.x era (Changelog: "geq filter ported from libmpcodecs"); stable option names (`lum_expr/lum`, `cb_expr/cb`, `cr_expr/cr`, `alpha_expr/a`, `red_expr/r`, `green_expr/g`, `blue_expr/b`, plus `interpolation`) through 8.0.
- `lerp()` and `randomi()` expression functions were added in later lavu/eval versions (randomi in 7.0) — expression portability to older FFmpeg must be checked.

### Performance benchmarks
- No official benchmarks; practitioner consensus: unusable for full-res video effects in throughput-sensitive pipelines; acceptable for overlays/icons, LUT-like one-time generation, or low-res procedural sources.

### Recommended alternatives
- `lut`, `lutyuv`, `lutrgb`, `lut3d`, `curves`, `colorchannelmixer`, `eq` for color math; `convolution` for kernel ops; `vignette`, `drawgrid/drawbox`+`overlay` for spatial effects; `gradients`/`mandelbrot`/`life` sources for procedural content.

---

## 4. xfade — T1/T2 (production-ready; strict input preconditions)

### Known issues and constraints
- **Hard preconditions** (documented): both inputs must be constant frame-rate and share resolution, pixel format, frame rate, **and timebase**. Violations produce the classic errors:
  - "First input link main timebase (1/15360) do not match the corresponding second input link xfade timebase (1/11988)"
  - frame-rate mismatch variants (30/1 vs 30000/1001).
  - Fix: normalize each input with `fps`, `settb=AVTB` (or matching `settb`), `scale`, `setsar=1`, `format` before xfade.
- **Black flash** between clips: usually fps/timebase mismatch — force constant fps on both inputs (ffmpeglab guide).
- **Wrong offset**: offset is relative to the *combined* timeline of prior xfade stages; cumulative-offset arithmetic errors are the most common automation bug. Too large → second clip never appears; too small → premature overlap.
- **Duplicated frames / A-V desync** in long multi-xfade chains (SO #64038132, #63553906): reported when mixing apad/atrim audio paths with xfade video; mitigated by `aresample=async=1:first_pts=0` per audio input and careful `acrossfade` pairing.
- Linear progress only: built-in transitions have no easing — motion transitions (slide*, wipe*) start/stop abruptly. The third-party **xfade-easing** project (scriptituk/xfade-easing) exists precisely to fix this, offering eased expressions for standard ffmpeg or a custom build with `easing`/`reverse` options.
- `distance` and `hblur` transitions aggregate pixels and can't be replicated via per-pixel custom expressions (xfade-easing docs); they're also the most computationally heavy built-ins.

### Transition inventory & broadcast-quality assessment
- ~44 built-in transitions (ffmpeg 4.3+): fades (fade, fadeblack, fadewhite, fadegrays), wipes (8 directions + 4 corner wipes), slides (4), smooth* (4), circlecrop/rectcrop/circleopen/circleclose, horz/vert open/close, diag* (4), hlslice/hrslice/vuslice/vdslice, dissolve, pixelize, radial, hblur, distance, squeezeh/squeezev, zoomin (5.0+), hlwind/hrwind/vuwind/vdwind (added ~2023, 6.x era).
- **Broadcast-safe tier** (conservative, clean at any duration): fade, fadeblack, fadewhite, dissolve, wipeleft/right/up/down, circleopen/circleclose, radial.
- **Stylized but reliable**: smooth*, slide*, diag*, pixelize (pixelize reads as intentional effect), zoomin.
- **Novelty tier** (fine for social, risky for broadcast): squeezeh/squeezev (aspect distortion), hblur (heavy, visible banding at low bitrates), distance (organic but unpredictable on dissimilar content), wind variants.
- Custom transition expressions are supported (`transition=custom` + `expr`), enabling GLSL-ported effects; quality then depends on the expression author.

### Safe parameter ranges
- `duration`: keep ≥0.25s and ≤ half the shorter clip; 0.5–1.0s typical.
- `offset`: compute as (cumulative duration of preceding content) − duration; validate against probed input durations, not assumed ones.
- Always pair video xfade with audio `acrossfade=duration=<same>`.

### Version compatibility
- Added in **FFmpeg 4.3** (2020). zoomin added ~5.0; wind variants (hlwind etc.) added ~6.x era. `xfade_opencl` exists as a GPU variant for a subset of transitions.
- Expression-evaluated `custom` transitions and the `expr` option require 4.4+; check availability with `ffmpeg -h filter=xfade`.

### Performance
- CPU cost is modest (per-pixel blend) except `hblur`/`distance` (aggregation). `xfade_opencl` offloads but requires OpenCL build and matching hw frames.

### Recommended alternatives
- ffmpeg-gl-transition (GLSL, external build) for higher-end effects.
- xfade-easing wrapper for eased (non-linear) transitions without a custom build.

---

## 5. perspective — T2 (correct math, but footguns in sense/interpolation)

### Coordinate system (documented, frequently misunderstood)
- Options `x0 y0 … x3 y3` are the four corners in order: **top-left, top-right, bottom-left, bottom-right**. Default `0:0:W:0:0:H:W:H` = identity.
- `sense=source` (default): "the specified points in the SOURCE are sent to the corners of the destination" — i.e., you name where the corners come *from*; used to **flatten/correct** a trapezoid (keystone correction, screen extraction).
- `sense=destination`: "the corners of the source are sent to the specified coordinates" — i.e., you name where the corners go *to*; used to **insert/warp** content onto a trapezoid (screen replacement).
- **These two modes are inverse mappings; picking the wrong one is the #1 user error.** For corner-pin screen replacement of new content onto a filmed screen: use `sense=destination` with the filmed screen's corner coordinates.
- `eval=init` (default) vs `eval=frame`: per-frame evaluation enables animated corner-pinning (tracked screen replacement) via expressions using `in`, `on`, `n`, `t` — but you must supply tracking data yourself; FFmpeg has no built-in point tracker (deshake/vidstab are global-motion only).

### Known issues / accuracy notes
- **Interpolation**: `linear` (default) vs `cubic`. Real-world report (SO #61028674): cubic "bloats the output with NO apparent improvement"; linear output "viewable but rough quality due to sampling error". Perspective is a point-sampler — no anti-aliasing/anisotropic filtering — so minified regions shimmer and aliases. Mitigation: pre-scale the content up, or accept soft output.
- **Out-of-frame coordinates are legal** (e.g. `x2=-60:y2=469`) and needed for extrapolated trapezoids — but easy to clip content accidentally.
- Corner-pinning accuracy is limited by: (a) your corner coordinates (integer-pixel input), (b) point sampling, (c) no lens-distortion modeling — curved screens/phone displays won't pin cleanly.
- Expression variables are limited (`W`, `H`, `in`, `on`) — no arbitrary per-frame data injection without regenerating the filtergraph (e.g. via sendcmd or scripted command files).

### Safe parameter ranges
- Coordinates may be negative or >W/H (extrapolation) — valid but verify visually.
- Prefer `interpolation=linear`; cubic rarely justifies cost.
- For screen replacement: pin with `sense=destination`, then composite with `overlay` (perspective output frame size = input frame size; black/empty outside the quad).

### Version compatibility
- Stable option set across 4.x–8.x (`x0..y3`, `interpolation`, `sense`, `eval`). No renames observed.

### Recommended alternatives
- For tracked screen replacement at production quality: planar trackers (Mocha-style) feeding corner data into per-frame `perspective` via generated filter scripts — FFmpeg alone has no tracker.
- `v360` (perspective projection mode) for FOV-style remaps; `lenscorrection`/`fisheye` for optical distortion; OpenCV homography warp when sub-pixel AA matters.

---

## 6. Version differences — FFmpeg 5.x vs 6.x vs 7.x (filter-relevant)

### Release policy change (6.0+)
- From 6.0 "Von Neumann" (2023-02-28): new major release every year; **ABI bumped every major release**; **deprecated APIs removed after 3 releases at the next major bump**. Practically: filters/options marked deprecated in 5.x could be gone by 7.0/8.0. 7.0 "Dijkstra" is explicitly **NOT backward compatible** (debugpoint/Phoronix): long-deprecated CLI options and APIs removed.

### 5.x (5.0 "Lorentz" 2022-01, 5.1 2022-07 — last LTS-style line)
- xfade present with ~40 transitions (zoomin added in this era).
- filtergraph file-passing (`/option` prefix) added in 5.1-era master → appears in 6.0.
- swscale still the default scaler path; `scale` filter flags largely stable.
- Notable 5.x filter additions include tiltandshift precursors... (see changelog: corr, ssim360, showcwt, adrc, afdelaysrc, hstack/vstack/xstack _vaapi and _qsv hardware stack filters are **6.0** additions).

### 6.0 "Von Neumann" (2023-02)
- New/reworked internals: libavutil/tx replaces FFT/MDCT/DCT/DST used by codecs **and filters** (faster; also smaller binaries); large reduction in per-frame allocations in video decoders; improved timestamp/frame-duration accuracy for VFR content (affects filter graphs that rely on PTS math — mostly fixes, but edge-case timestamp behavior changed).
- New filters: showcwt, corr, adrc, afdelaysrc, ssim360, backgroundkey; hstack_vaapi/vstack_vaapi/xstack_vaapi and _qsv variants.
- ffmpeg CLI: stats options, option values from file (`-/opt`, filtergraph `/name` prefix).
- Threading now **required** to build ffmpeg (relevant for minimal builds).
- xfade wind transitions (hlwind/hrwind/vuwind/vdwind) appear in this era.

### 7.0 "Dijkstra" (2024-04)
- **Multi-threaded ffmpeg CLI** — biggest refactor in years: demux/decode/filter/encode/mux run in parallel. Filter-graph throughput on multi-core improves; also changes latency/ordering characteristics of some graphs and logging interleaving. Scripts parsing ffmpeg stderr output may break.
- **Removals**: deprecated CLI options `-psnr`, `-map_channel` gone; `-top` deprecated earlier in favor of `setfield` filter. C11 compiler required (C17 coming).
- **Color-range rework** (big one for filters): full-range/limited-range negotiation was rebuilt; color range is now forwarded correctly and consistently to filters, encoders, muxers. Filters that previously received unreliable range flags may produce *different* (more correct) output vs 5.x/6.x — a silent visual difference when A/B comparing versions.
- QSV encoders: default bitrate control changed VBR→CQP.
- New filters: tiltandshift, quirc, qrencode/qrencodesrc, fsync, aap, dnn libtorch backend; `randomi()` in expressions (affects geq/drawtext expression portability).
- VVC decoder (experimental), IAMF, DVD-Video demuxer, ffplay Vulkan renderer.

### 8.0 (2025) — context for "current"
- `pp` filter **removed** (libpostproc dropped May 2025, maintenance burden; replacement uncertain — Super User #1929982). Any pipeline using `pp=al|f` (autolevels) breaks on 8.0 with "No option name near 'al|f'".
- YUVJ pixel formats obsoleted by proper YUV colorspace negotiation (7.x–8.x arc) — scripts using `-pix_fmt yuvj420p` should switch to `yuv420p` + range signaling.
- CrystalHD decoders deprecated (6.x), DEC Alpha DSP removed, sdl1 device removed earlier (3.x) — pattern: little-used hardware paths keep getting pruned.

### Practical version-pinning guidance for automation
- Pin a major version per pipeline; treat major upgrades as requiring a visual regression pass, especially: color-range handling (7.0), CLI threading (7.0 stderr/ordering), removed CLI opts (7.0), pp removal (8.0).
- 5.1 and 6.1 are the "safe old stable" lines; 7.1 is the first line with the new CLI threading + range negotiation fully settled.

---

## 7. Deprecation & removal landscape (filters and parameters)

### Removed filters (confirmed)
- **`pp` (postproc)** — removed in 8.0 (libpostproc deleted May 2025). Was widely used for `pp=al` autolevels and `pp=lb` deblocking. **No direct replacement**; nearest equivalents: `eq`/`normalize` for levels, `deblock` filter (4.1+) for deblocking. This is the most impactful recent filter removal.
- `ocv` (OpenCV wrapper), `frei0r` (still present but build-gated) — availability depends on build flags; not removed but commonly "missing" in distro builds (cf. Video Production SE "filters missing after upgrade to 4.0": usually a build-config difference, not an upstream removal).

### Renamed filters (historical, still biting old scripts)
- `aspect` → `setdar`, `pixelaspect` → `setsar` (2.x era).
- `movie`/`amovie` `stream_index/si` option: **deprecated** (docs: "Deprecated. If the filter is called amovie...").
- `aeval` and expression filters: `POS` variable deprecated ("do not use"); `RTCTIME` deprecated → use `time(0)`.
- scale filter `sws_flags` usage **deprecated** in favor of `scaler` option; individual sws algorithm flags (`fast_bilinear`, `bilinear`, `bicubic`, `experimental`, `neighbor`, `area`, `bicublin`, `gauss`, `sinc`, `lanczos`, `spline`) marked "(Deprecated)" in that context.
- CLI `-top` deprecated → `setfield` filter.

### Breaking-change patterns to design around
1. **3-release deprecation clock** (6.0+): any "deprecated" tag in docs is a commitment to remove. Treat deprecated options as technical debt with a known expiry.
2. **YUVJ pixel formats obsoleted** by colorspace negotiation (7.x/8.x).
3. **Build-flag fragility**: filters requiring external libs (frei0r, ocv, libzimg for zscale, OpenCL for xfade_opencl, vidstab) silently absent in some builds — always probe with `ffmpeg -filters` at runtime in automation.
4. **CLI removals in 7.0**: `-psnr`, `-map_channel` removed; more deprecated CLI opts expected to drop at each major bump.

---

## Consolidated Filter Validation Matrix (requested filters)

| Filter | Tier | Headline risk | Safe recipe | Automation verdict |
|---|---|---|---|---|
| zoompan | T3 | Integer-rounding jitter (#4298) | Upscale 4–8x first or trunc() expressions; always set fps= and s= | Usable only with the workaround pipeline |
| minterpolate | T2/T3 | Single-threaded; warping on fast/occluded motion | fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1, search_param 64–400, keep scd=fdiff; chunk+parallelize | Batch-viable with chunked parallelism and QA sampling |
| geq | T2 | Per-pixel eval cost; RGB/YUV mode trap; thread-state caveat | Prefer dedicated filters; identity-express unused channels; filter_threads=1 if stateful | Fine for small/procedural jobs; avoid for full-res fx |
| xfade | T1/T2 | fps/timebase/resolution mismatch errors; cumulative offset math; linear-only motion | Normalize inputs (fps, settb, scale, setsar, format); compute offsets from probed durations; pair with acrossfade | Production-ready with input normalization gate |
| perspective | T2 | sense mode confusion; point-sampling aliasing; no tracker | sense=destination for screen replacement; interpolation=linear; pre-upscale content | Reliable for static pins; tracked pins need external tracking data |

---

## GAPS REQUIRING PERPLEXITY DEEP RESEARCH

The following could not be established from Tavily-indexed sources and warrant deep research (FFmpeg trac/git archaeology, mailing-list history, or primary benchmarks):

1. **zoompan #4298 definitive resolution status** — The 2020 PATCH v4 thread implies a fix was merged, but I could not confirm from primary sources (a) the exact commit/version the anti-shake overscale logic landed in, (b) whether trac #4298 is formally closed, (c) whether residual jitter reports on 6.x/7.x reflect a different root cause or incomplete fix. Needs trac.ffmpeg.org ticket history + git log of vf_zoompan.c.
2. **minterpolate throughput benchmarks** — No hard numbers (fps processed vs resolution vs me algorithm vs CPU) exist in indexed sources; only anecdotes ("4 hours per clip" for esa). Needed to size chunking for automation. Also: whether any threading work landed in 7.x/8.x for minterpolate specifically.
3. **geq expression-complexity cost model** — No data on cost scaling per function call, or comparative benchmarks geq vs lut/curves for equivalent operations. Also whether the 7.0 CLI threading changed geq slice behavior measurably.
4. **xfade broadcast-quality objective data** — No PSNR/SSIM/VMAF comparisons of transitions vs. ideal crossfade, no bitrate-sensitivity analysis (hblur banding thresholds), no broadcaster acceptance references. "Broadcast-quality" assessment above is practitioner-consensus inference, not measured.
5. **perspective sub-pixel accuracy quantification** — No published measurements of corner-pin error vs. ground truth, no comparison of linear vs cubic interpolation error surfaces, no documentation of rounding behavior at extreme extrapolation. Also: whether any AA/anisotropic improvements are planned (needs ffmpeg-devel search).
6. **Complete removed-filter list 4.x→8.x** — The Changelog is additive-oriented; removals (like pp in 8.0) are documented per-release but I could not produce a verified exhaustive list of filter removals across 5.x/6.x/7.x without git-level diffing of vf_* registration tables. Also unverified: rumored future removals (e.g., filters superseded by Vulkan/libplacebo paths).
7. **Per-version behavioral diffs for the five target filters** — e.g., did xfade's timebase check tighten in a specific release? Did minterpolate defaults change (me default epzs across all versions?)? Did perspective gain `eval=frame` in a specific version? Requires doc archaeology across release snapshots.
8. **xfade_opencl transition subset and parity status** — Which transitions the OpenCL variant actually supports in each version, and whether output is bit-identical to CPU xfade, is not documented in indexed sources.
9. **Windows-build-specific filter availability** — gyan.dev vs BtbN builds differ in bundled libs (libzimg, frei0r, vidstab, OpenCL); no authoritative matrix found. Relevant since this project targets Windows automation.
10. **7.0 color-range negotiation: filter-level impact list** — Which specific filters changed output due to the range-forwarding rework (7.0), and whether any produce visibly different results vs 6.x for identical command lines, is not enumerated anywhere indexed.
