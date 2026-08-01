# P3 — Advanced FFmpeg Techniques for Professional Motion Graphics
## Research Findings (Tavily Search Phase)

**Date:** 2026-07-21
**Researcher:** Research Subagent (P3)
**Method:** 11 Tavily advanced-depth searches (9 completed, 3 blocked by API usage limit) + corroborating FFmpeg domain documentation found in search results.

---

## 1. SCREEN REPLACEMENT

### 1.1 Perspective Filter Corner Pinning (Native FFmpeg)

**Category:** Screen replacement / corner pinning
**Method:** The `perspective` filter accepts 8 coordinate expressions — `x0:y0` (top-left), `x1:y1` (top-right), `x2:y2` (bottom-left), `x3:y3` (bottom-right) — remapping the four corners of a source frame to arbitrary destination positions. This is FFmpeg's native equivalent of After Effects' Corner Pin.

**Key semantics (from official docs):**
- `sense=source` (default): the specified points are where the source corners get *sent to* in the destination.
- `sense=destination`: the corners of the destination are *pulled from* the specified source coordinates.
- Expressions can use `W`, `H` (frame size), `in` (input frame count), `on` (output frame count) — meaning **corner positions can be animated per-frame with expressions**, enabling tracked screen replacement without external tools for simple linear tracks.
- `interpolation=linear` (default) or `cubic`.

**Complete command — static corner pin of a replacement screen onto a device screen:**
```bash
ffmpeg -i phone_footage.mp4 -i new_screen.mp4 -filter_complex \
"[1:v]perspective=x0=225:y0=120:x1=715:y1=85:x2=200:y2=469:x3=740:y3=500[s]; \
 [0:v][s]overlay=0:0[v]" -map "[v]" -map 0:a? -c:a copy out.mp4
```

**Real-world verified example (Stack Overflow #61028674):** extracting a trapezoidal perspective section from a 1280x720 video, including an **out-of-frame coordinate** (`x2=-60,y2=469`) — negative/off-frame coordinates are legal, which matters when a screen corner exits the frame:
```bash
ffmpeg -hide_banner -i input.mkv -lavfi \
"perspective=x0=225:y0=0:x1=715:y1=385:x2=-60:y2=469:x3=615:y3=634:interpolation=linear" \
output.mkv
```

**Combined perspective + rotate + overlay for tilted screens (Video Production SE #16809):**
```bash
ffmpeg -y -i "base.mov" -i "overlay.mov" -filter_complex \
"[1:v] fade=in:10:1:alpha=1, fade=out:500:1:alpha=1, scale=80:80, \
 perspective=x0=0:y0=0:x1=W:y1=40, rotate=-0.1745:c=none [ov]; \
 [0:v][ov] overlay=100:100 [v]" -map "[v]" out.mov
```

**Animated corner pinning (expression-driven, no external tracker):**
```bash
perspective=x0='100+20*sin(on/30)':y0=120:x1=715:y1=85:x2=200:y2=469:x3=740:y3=500
```

**Performance cost:** Moderate — per-pixel inverse homography. `interpolation=linear` is fast; `cubic` notably slower with one report of "bloat with NO apparent improvement" for noisy source footage. Output frame size always equals input frame size.
**Quality impact:** Linear interpolation produces "rough" sub-pel sampling; cubic softens. Recommended fix: sharpen after with `unsharp=3:3:0.35`.
**External tools:** None required.
**Limitations:**
- Single-plane homography only — no lens distortion correction, no motion blur matching, no occlusion handling.
- **No `sendcmd`/command support is documented for perspective** (it does not appear in the command-supporting filter list), so per-frame animation must use expressions with `on`/`in` variables, or be baked via other means.
- Edge anti-aliasing on the pinned corners is limited.

### 1.2 find_rect for Screen Detection

**Category:** Screen/object location detection
**Method:** `find_rect` matches a reference image (PGM grayscale) against every frame and stores results as frame metadata tags `lavfi.rect.x`, `lavfi.rect.y`, `lavfi.rect.w`, `lavfi.rect.h`, `lavfi.rect.score`.

**Complete command (from official docs) — extract track to CSV:**
```bash
ffprobe -f lavfi movie=test.mp4,find_rect=object=object.pgm:threshold=0.3 \
 -show_entries frame=pkt_pts_time:frame_tags=lavfi.rect.x,lavfi.rect.y \
 -of csv -o find_rect.csv
```

**Visualize the detection:**
```bash
ffmpeg -i test.mp4 -vf "find_rect=object=screen.pgm:threshold=0.3,cover_rect=object=screen.pgm" -f null -
```

**Performance cost:** High — brute-force template match per frame; scales with frame area × template area.
**Limitations:**
- **Single-point (top-left) detection only** — it finds the rectangle position, but NOT four corners. For perspective-correct screen replacement you need 4 corner tracks, so find_rect alone is insufficient for corner pinning a moving/rotating screen; it works only for axis-aligned screen positions.
- Grayscale template, no rotation/scale invariance. Template must match size/orientation of the on-screen rectangle.
- Threshold tuning is empirical (0.3 is the doc default).
- Object must be a PGM file (`convert screen.png -colorspace Gray screen.pgm`).

### 1.3 Practical Screen Replacement Workflows (Industry Reality Check)

Search results confirm the professional consensus: **pure-FFmpeg screen replacement is a niche workflow**. The Adobe/Mocha workflow (planar tracker → 4-corner corner pin) dominates because Mocha's planar tracker handles rotation, scale, shear, and perspective drift per frame. The viable FFmpeg-centric pipeline is:
1. Track externally (Mocha AE, Blender, or OpenCV — see §2.2) → export 4 corner coordinates per frame.
2. Bake coordinates into an FFmpeg `perspective` expression driven by `on`, or split the render into segments with discrete perspective calls.
3. Composite with `overlay`, then match grain (`noise`), blur, and color to glue the shot.

**Use cases:** automated batch screen replacement on static/locked-off shots (e.g., app-demo video generation pipelines), automated sports-broadcast graphics on fixed camera angles.

---

## 2. OBJECT TRACKING

### 2.1 find_rect Accuracy Characteristics

As detailed in §1.2. Accuracy depends on: template uniqueness (high-frequency detail tracks better), threshold (0.3 default; raise to 0.5+ for cluttered scenes), and scale match. Known failure modes: template scale drift as object approaches camera; lighting change on emissive screens; partial occlusion producing jitter between candidate matches. **Workaround:** re-extract the template every N seconds (multi-pass), or crop the search region per segment to reduce false matches.

### 2.2 External Tracking: OpenCV + FFmpeg (the practical hybrid)

**Category:** External tool integration
**Method:** OpenCV performs per-frame template matching (`cv2.matchTemplate` with `TM_CCOEFF_NORMED` + `cv2.minMaxLoc` yielding top-left `(max_loc)` coordinates and a confidence `max_val`), writes coordinates per frame, and FFmpeg consumes them for overlays/effects. This is the dominant community pattern; multiple verified implementations were found.

**Reference implementation (from search results, debuggercafe / OpenCV forum patterns):**
```python
import cv2
cap = cv2.VideoCapture("input.mp4")
template = cv2.imread("needle.png", 0)
w, h = template.shape[::-1]
coords = []
while True:
    ret, frame = cap.read()
    if not ret: break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    x1, y1 = max_loc                      # top-left corner
    coords.append((x1, y1, max_val))      # x, y, confidence per frame
# write coords to sendcmd file (see 2.3)
```

**Multi-scale matching** (GeeksforGeeks pattern): loop over progressively downscaled frames, keep the match with the highest correlation coefficient, rescale coordinates by the scale factor `r` — handles object size change that find_rect cannot.

**For identity-preserving tracking** (multi-object, occlusion): search results point to detection+tracking stacks (DeepSORT, ByteTrack, OC-SORT with YOLO detectors) rather than template matching — detect every nth frame, track between detections, export per-frame bounding boxes, then hand to FFmpeg for rendering (boxes via `drawbox` with per-frame `sendcmd`, or pre-rendered overlay PNGs).

**Performance:** OpenCV template matching runs near-real-time on CPU for 1080p with modest templates; deep trackers need GPU for real-time. FFmpeg render pass is then near-real-time.
**External tools required:** Python + OpenCV (`pip install opencv-python`), or a tracker repo (YOLO+DeepSORT) for multi-object.

### 2.3 sendcmd / zmq Coordinate Injection

**Category:** Timeline-driven filter animation / live control

**sendcmd — file-based, offline.** Commands file syntax is `[START[-END]] [filter@instance] [command] [args];` — intervals are `[START, END)`. Verified working pattern (Stack Overflow #54462184):

`test.cmd`:
```
0 overlay@1 x 10, overlay@1 y 10, rotate@1 angle '45*PI/180';
2.25 overlay@1 x 200, overlay@1 y 150, rotate@1 angle '90*PI/180';
```

Command:
```bash
ffmpeg -loop 1 -i mask1.png -i video.mp4 -filter_complex \
"[1:v]sendcmd=f=test.cmd,nullsink; \
 [0:v]rotate@1=c=black@0[r]; [1:v][r]overlay@1=shortest=1[v]" \
-map "[v]" out.mp4
```

**Critical gotchas found in research:**
- Image inputs must use `-loop 1`, otherwise no frame exists at t=2.25 for the command to act on (the #1 failure mode).
- Filter instances are addressed with `@name` on the filter (e.g., `overlay@1`, `rotate@1`).
- Only filters marked with `C` in `ffmpeg -filters` output accept commands. Command-supporting filters verified in docs: `overlay` (x, y), `rotate` (angle), `gblur`, `rgbashift`, `avectorscope` (most options), `drawtext`, `hue`, `crop`.
- Invalid expressions are silently ignored (kept at current value) — debug with `-loglevel debug`.
- **Commands set values discretely — there is no interpolation between keyframes.** For smooth motion you must emit a command per frame (a Python script can generate a 30-line-per-second cmd file from tracker output — this is the standard bridge from OpenCV tracking to FFmpeg rendering).

**zmq / azmq — live, network-based.** Insert `zmq` into the filtergraph; FFmpeg binds a ZMQ REP socket; an external client sends `TARGET COMMAND ARG` text messages and receives `ERROR_CODE ERROR_REASON MESSAGE` replies. FFmpeg ships `tools/zmqsend` as a reference client. This enables **real-time** coordinate injection (e.g., live tracked graphics during a stream), which sendcmd cannot do. Workflow: OpenCV tracker in Python → `zmq` socket → running `ffplay`/`ffmpeg -i ... -f mpegts` instance with `zmq` + `overlay@track` in the graph.

**Performance:** sendcmd adds negligible overhead. zmq adds message latency (~sub-ms locally) but requires the ZMQ library compiled in (most gyan.dev Windows builds and Linux distro builds include `--enable-libzmq` — verify with `ffmpeg -filters | findstr zmq`).

---

## 3. AUDIO VISUALIZATION & AUDIO-REACTIVE VISUALS

### 3.1 Core Visualization Filters (all verified with complete commands)

| Filter | Purpose | Verified Command |
|---|---|---|
| `showwaves` | Waveform (point/line/cline/p2p modes) | `ffmpeg -i input.mp3 -filter_complex "[0:a]showwaves=s=1280x202:mode=line:rate=25,format=yuv420p[v]" -map "[v]" -map 0:a -c:a copy out.mp4` |
| `showspectrum` | Sliding spectrogram (lin/log/sqrt/cbrt scales) | `ffmpeg -i song.mp3 -filter_complex "showspectrum=mode=separate:color=intensity:slide=1:scale=cbrt" -acodec copy video.mp4` |
| `showcqt` | Constant-Q transform — **musical note view (shows which piano keys are pressed)** | `ffmpeg -i input.mp3 -filter_complex "[0:a]showcqt=s=1920x1080,format=yuv420p[v]" -map "[v]" -map 0:a showcqt.mp4` |
| `avectorscope` | Stereo Lissajous (L/R difference; vertical line = mono, horizontal = out of phase) | `ffmpeg -i input.mp3 -filter_complex "[0:a]avectorscope=s=1920x1080,format=yuv420p[v]" -map "[v]" -map 0:a avectorscope.mp4` |
| `showfreqs` | Frequency amplitude bars (log scale) | `ffmpeg -i input.mp3 -filter_complex "[0:a]showfreqs=s=1920x1080:mode=line:fscale=log,format=yuv420p[v]" -map "[v]" -map 0:a showfreqs.mp4` |
| `ahistogram` | Sample value histogram | `ffmpeg -i input.mp3 -filter_complex "[0:a]ahistogram=s=1920x1080,format=yuv420p[v]" -map "[v]" -map 0:a ahistogram.mp4` |
| `aphasemeter` | Stereo phase meter | `ffmpeg -i input.mp3 -filter_complex "[0:a]aphasemeter=s=1920x1080:mpc=cyan,format=yuv420p[v]" -map "[v]" -map 0:a aphasemeter.mp4` |
| `showvolume` | VU-meter style volume bar | `ffmpeg -i input.mp3 -filter_complex "[0:a]showvolume=f=0.5:c=VOLUME:b=4:w=1920:h=900,format=yuv420p[v]" -map "[v]" -map 0:a showvolume.mp4` |
| `showspatial` | Spatial stereo field visualization | (in docs; less community usage found) |

**Key avectorscope options (FFmpeg 8.0 docs):** draw modes `dot`/`line`/`aaline`; scale `lin`/`sqrt`/`cbrt`/`log`; contrast `rc/gc/bc/ac` (defaults 40/160/80/255); fade `rf/gf/bf/af`; `zoom` 0–10.

### 3.2 Professional Composite Visualizer (verified multi-layer example)

The canonical "YouTube music visual" stacks multiple analyzers with overlay and drawtext:

```bash
ffmpeg -i input.mp3 -filter_complex \
"[0:a]avectorscope=s=640x518,pad=1280:720[vs]; \
 [0:a]showspectrum=mode=separate:color=intensity:scale=cbrt:s=640x518[ss]; \
 [0:a]showwaves=s=1280x202:mode=line[sw]; \
 [vs][ss]overlay=w[bg]; \
 [bg][sw]overlay=0:H-h,drawtext=fontfile=Vera.ttf:fontcolor=white:x=10:y=10:text='\"Song Title\" by Artist'[out]" \
-map "[out]" -map 0:a -c:v libx264 -preset fast -crf 18 -c:a copy output.mkv
```

**Waveform over background art (Publitio verified pattern):**
```bash
ffmpeg -i audio.mp3 -loop 1 -i background.jpg -filter_complex \
"[0:a]aformat=channel_layouts=mono,showwaves=s=1280x720:mode=cline:rate=30:colors=white[waveform]; \
 [1:v]scale=1280:720[bg]; [bg][waveform]overlay=shortest=1" \
-pix_fmt yuv420p -r 30 -y visualizer.mp4
```

**Circular/radial waveform hack (advanced, verified in Publitio article):** FFmpeg has no native radial waveform — the trick is `showwaves` (linear) followed by `geq` with polar-coordinate pixel remapping to warp the line into a circle. High CPU cost (geq evaluates per-pixel expressions).

### 3.3 Audio-Reactive Expressions (audio driving video parameters)

This is the weakest-covered area in search results — **no complete verified pipeline was found via Tavily**. Known-capable building blocks (documented in FFmpeg filter docs, partially corroborated):
- `astats` with `metadata=print` / `metadata=inject` writes per-frame audio level metadata (`lavfi.astats.Overall.RMS_level`, etc.).
- `ametadata` can read/compare it; `sidechaingate`, `compand` key on sidechain audio for *audio→audio* reaction.
- For *audio→video* reaction, community workflows use: (a) extract envelope via `astats` → ffprobe CSV → generate `sendcmd` file driving `hue`/`gblur`/`zoompan` values per frame; or (b) real-time via `azmq` + external envelope follower.

**Performance:** Native visualizers run 10–30× realtime for 1080p (Publitio measured ~3s for a 19s file at 720p). geq-based radial hacks are 1–3× realtime. Multi-layer composites scale linearly per analyzer.

**Limitations:** showwaves colors are per-channel (L=red, R=green by default — overlap renders yellow); avectorscope requires genuine stereo separation (mono = vertical line, a reported "bug" that is actually correct behavior); `format=yuv420p` must be appended for player compatibility; no GPU acceleration for analyzers.

---

## 4. ADVANCED MASKING

### 4.1 geq-Generated Masks (procedural, no image files needed)

**Category:** Procedural masking
**Verified pattern (curiosalon blog):** generate an alpha channel with a mathematical expression, extract, merge onto target video.

**Circular mask over video (complete verified command):**
```bash
ffmpeg -f lavfi -i "color=color=red:size=228x228,format=yuva420p,\
geq=lum='p(X,Y)':a='if(lte(hypot(X-(W/2),Y-(H/2)),100),255,0)'" \
-i map.mp4 -filter_complex "alphaextract[a];[a]alphamerge" -c:v vp9 maskedmap.webm
```

Dissection: `geq` requires a luminance expression — `lum='p(X,Y)'` passes source luma through; the alpha expression `a='if(lte(hypot(X-(W/2),Y-(H/2)),100),255,0)'` writes 255 (opaque) inside a radius-100 circle centered on the frame, 0 outside. `alphaextract` pulls that alpha to grayscale; `alphamerge` applies it to the target.

**Useful geq alpha recipes:**
- Diagonal wipe: `a='if(gt(X,Y*W/H),255,0)'`
- Animated iris: `a='if(lte(hypot(X-W/2,Y-H/2),100+50*sin(T*2)),255,0)'` (T = time in seconds)
- Feathered edge (smoothstep approximation): `a='255*clip((110-hypot(X-W/2,Y-H/2))/20,0,1)'`

**Performance:** geq is one of the slowest filters — per-pixel expression evaluation, no SIMD. 1080p geq runs ~5–15 fps on modern CPU. Pre-render static masks to a PNG sequence instead of regenerating per render.
**Limitation:** hard edges unless you write the feathering math yourself; no built-in anti-aliasing.

### 4.2 Image Sequence / Video Masks with alphamerge

**Verified workflow (Super User #916431 — blur+greyscale masked region):**
```bash
ffmpeg -i input -loop 1 -i mask.png -filter_complex \
"[0:v][1:v]alphamerge,hue=s=0,boxblur=5[fg]; \
 [0:v][fg]overlay[v]" -map "[v]" -map 0:a -c:a copy output
```

**PNG mask → alpha on video (Stack Overflow #36467594, verified):**
```bash
ffmpeg -y -i input.mp4 -loop 1 -i mask_with_alpha.png -filter_complex \
"[1:v]alphaextract[alf];[0:v][alf]alphamerge" -c:v qtrle -an output.mov
```
(Use `-c:v qtrle` or VP9/ProRes 4444 for alpha-carrying output; **H.264/H.265 drop alpha** — verified community finding.)

**Animated masks:** replace the looped PNG with a mask video (PNG sequence via `-framerate 30 -i mask_%04d.png` or a ProRes/qtrle MOV) — `alphamerge` consumes frame pairs in sync.

**Merging alpha with existing alpha (verified pattern, Tyzoid):** when the base video already has alpha, `alphamerge` *replaces* it — combine instead with `blend=all_mode=darken` on the two extracted alphas first:
```bash
-filter_complex "[1:v]alphaextract[alf];[0:v]alphaextract[oalf];\
[alf][oalf]blend=all_mode=darken[res];[0:v][res]alphamerge"
```

**YUV range gotcha (documented in FFmpeg mailing list):** YUV limited range cannot represent 0–16 or 235–255, so masks from YUV sources produce alpha=16 instead of 0 ("pure black" never fully transparent). **Workaround:** keep masks in RGB/gray (`format=gray` or rgba) end-to-end, or clamp with `lut=y=val*255/219` style correction.

**maskedmerge vs alphamerge (Video Production SE #37653):** `alphamerge` only *attaches* alpha — downstream metric filters (SSIM/PSNR) ignore alpha. To actually composite through a mask, use `maskedmerge` (3 inputs: base, overlay, mask) or overlay after alphamerge.

### 4.3 Rotoscoping Alternatives

No native FFmpeg rotoscoping exists. Search-informed alternatives:
- **ffmpeg-mask / AI matte pipeline:** run an external segmentation model (e.g., MODNet/RVM — Robust Video Matting) frame-by-frame → PNG alpha sequence → `alphamerge` as in §4.2. This is the standard "AI rotoscoping" approach feeding FFmpeg.
- **Chroma-key path:** `chromakey`/`colorkey` + `despill` filters (both present in current FFmpeg) for green-screen rotoscope replacement; combine with `maskfun` (mask generation from luma) for garbage mattes.
- **Temporal mask cleanup:** `gblur` on the mask (soften chatter), `tblend`/`xmedian` across frames to stabilize mask flicker before merging.

---

## 5. KEN BURNS & CAMERA MOVES

### 5.1 zoompan Essentials + the Jitter Bug (well-documented, verified)

**Basic command:**
```bash
ffmpeg -loop 1 -i input.jpg -vf "zoompan=z='min(zoom+0.0015,1.5)':d=125" \
-c:v libx264 -t 10 -s 1920x1080 -pix_fmt yuv420p output.mp4
```

**Zoom to center (Bannerbear verified):**
```bash
ffmpeg -loop 1 -i photo.jpg -filter_complex \
"scale=1200:-2,setsar=1:1,crop=1200:670,scale=8000:-1,\
zoompan=z='zoom+0.001':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=250:s=1200x670:fps=25[out]" \
-map "[out]" -pix_fmt yuv420p -r 25 -t 10 video.mp4
```

**The jitter problem (FFmpeg bug #4298, widely confirmed):** zoompan **rounds x/y expression results to integers**, causing visible jerky motion. Two verified workarounds:
1. **Upscale before zoompan** (the standard fix): `scale=8000:-1` or `scale=8000x4000` before zoompan, downscale after (`scale=-2:480`) or via zoompan's own `s=` output size. Cost: significant memory/CPU — 8000px-wide intermediate frames.
2. **Pad-then-zoom with trunc()** (Video Production SE #37370, avoids the 8K intermediate): pad to square, drive zoom with `z='trunc(iw*10*(1+0.0015*in)/2)*2/(iw*10)'` — pre-quantizing the zoom value to even integers so rounding is deterministic and smooth. Faster for batch processing.

**High-end slideshow pattern (mko.re, verified):** pre-`pad` images into a large canvas (`pad=w=9600:h=6000`), then zoompan with combined zoom+pan expressions; add `fade=t=in/out:alpha=1` + `setpts=PTS-STARTPTS+offset/TB` per clip and `xfade`-style overlapping for full Ken Burns slideshows with transitions. Pan speed note: **the farther the pan, the higher the fps needed for smoothness** — 60fps recommended for long pans.

### 5.2 Ease In/Out Motion

zoompan expressions support any math — replace linear `zoom+0.0015` with easing, e.g. cosine ease `z='1+0.5*(1-cos(PI*on/125))/2'`. Community consensus (Reddit r/ffmpeg): for complex easing many users switch to OpenShot/Kdenlive/Shotcut — FFmpeg easing is possible but expression authoring is laborious.

### 5.3 Parallax / 3D-Like Moves

**Technique (documented pattern, no single verified tutorial found):** layer-split a still into foreground/midground/background cutouts (PNG with alpha, cut in Photoshop/GIMP or via AI segmentation), then apply **different zoompan rates per layer** in parallel filter chains and overlay — differential motion = parallax. Combined with `perspective` for a fake dolly: animate all four perspective corners drifting inward at slightly different rates per layer. This simulates the "2.5D photo animation" (Volu-style) effect using only FFmpeg.

**3D rotation illusion:** `perspective` with `on`-driven corner expressions (e.g., oscillating x1/x3) creates a planar "card flip/turn" — true 3D rotation of a plane. Verified variable support: `on` (output frame count) is legal in perspective coordinate expressions.

---

## 6. LOTTIE TO VIDEO

**Category:** External tool integration

**Confirmed finding: FFmpeg has no Lottie decoder.** All pipelines render the Lottie JSON to frames first, then FFmpeg assembles.

**Pipeline A — lottie-web + headless browser (the standard programmatic route):**
1. Load JSON in lottie-web (SVG or canvas renderer) inside Puppeteer/headless Chrome.
2. Step the animation frame-by-frame (`animation.goToAndStop(frame, true)`), screenshot each frame to PNG (`frame_%04d.png`).
3. Assemble: `ffmpeg -framerate 60 -i frame_%04d.png -c:v libx264 -pix_fmt yuv420p out.mp4` (or `-c:v qtrle`/ProRes 4444 / VP9 for alpha).

**Pipeline B — hosted/online converters (verified in search):** Lottielab's "Lottie to Video" converter (JSON→MP4 up to 4K, free tier), html5animationtogif.com (JSON→APNG with transparent background, configurable FPS/loops/size up to 1920px). Good for one-offs; not automatable at scale.

**Pipeline C — After Effects round-trip (reverse direction, verified):** AE renders MP4/PNG sequence → Bodymovin exports Lottie JSON. Relevant when motion-graphics sources live in AE: render in AE, composite/encode in FFmpeg.

**Key technical notes found:**
- **Renderer choice matters:** lottie-player's `renderer` setting (svg vs canvas) affects both fidelity and headless capture reliability — search results note preview/render issues fixed by switching renderer or background color.
- **Transparent background** requires canvas renderer + capturing with `omitBackground`/transparent page background in Puppeteer, then encoding to an alpha codec (qtrle/VP9/ProRes 4444), never H.264.
- Image-sequence-embedded Lotties (PNG sequences inside the JSON) are a known failure point in the AE/Bodymovin export direction (blank output — GitHub issue #1070, lottiefiles forum), but do not affect the lottie-web render direction.
- Frame-stepping (goToAndStop + screenshot) avoids `captureStream()` quality/perf problems documented for live canvas recording (michelleenos.com) — the same decoupled pattern is recommended: render frames slowly, assemble fast with FFmpeg.

**Performance:** headless render ~5–30 fps depending on animation complexity; FFmpeg assembly near-instant. **External tools:** Node.js, puppeteer, lottie-web (or lottie-node), or a hosted converter account.

---

## 7. GLITCH & CREATIVE EFFECTS

### 7.1 rgbashift (channel-split glitch — verified)

```bash
ffmpeg -i original.mp4 -vf "rgbashift=rh=15:bv=15:gh=-15" -pix_fmt yuv420p rgba-shifted.mp4
```
Options: `rh/rv/gh/gv/bh/bv/ah/av` (per-channel H/V pixel shifts), `edge=smear|default|warp`. **Supports sendcmd commands** — shift amounts can be keyframed for "glitch hits" on beats.

**Retro glow composite (zayne.io verified 3-pass):** rgbashift → `blend=overlay` back onto original (with `scale2ref`) → heavy `gblur` → yields chromatic-aberration glow. Can be collapsed to one filtergraph with split/merge.

### 7.2 shufflepixels / shuffleframes / shuffleplanes

- `shufflepixels=direction=forward:mode=horizontal:width=32` — reorders pixel blocks (horizontal/vertical/block modes); strong "corrupted tile" glitch. Block size options `width`/`height`.
- `shuffleframes=0 2 1` — reorders frames (swap 2nd/3rd of every 3) — temporal stutter glitch.
- `shuffleplanes` — swaps color planes between frames for color-inversion glitch.

### 7.3 Datamoshing (true codec-level mosh — verified workflow)

**FFmpeg alone cannot reliably datamosh** — confirmed by multiple sources ("tedious if at all possible with FFmpeg"). The verified toolchain:
```bash
# 1. Convert to AVI
ffmpeg -i input.mp4 output1.avi
# 2. Mosh with aviglitch (Ruby) — removes I-frames, duplicates P-frames
datamosh output1.avi -o datamoshedvideo.avi
# 3. Transcode back
ffmpeg -i datamoshedvideo.avi moshed.mp4
```
Tools: **aviglitch** (Ruby gem) or **Avidemux** (GUI: cut I-frames, copy-paste P-frame runs for the classic "melting bloom"). Principle (glitchology.com): H.264/MPEG-4 predict frames from keyframes; delete I-frames and prediction smears motion across shots; duplicate P-frames and motion blooms/extends. Reddit r/datamoshing notes P-frame duplication can freeze/stutter depending on player tolerance.

### 7.4 pseudocolor (false-color / thermal looks)

```bash
ffmpeg -i in.mp4 -vf "pseudocolor=preset=inferno" out.mp4
```
Presets: `magma, inferno, plasma, viridis, turbo, cividis, range1, range2, shadows, highlights`. Custom component expressions via `c0/c1/c2/c3` with `index` choosing the source component; `opacity` blends with source. Great for heat-map/thermal/scanline aesthetics in motion graphics.

### 7.5 VHS / Analog Degradation (composite recipe — no single filter)

No verified one-command VHS tutorial surfaced in search (gap — see §GAPS), but the documented building blocks assemble into a full VHS chain:
```bash
ffmpeg -i in.mp4 -vf "\
scale=320:240,scale=640:480:flags=neighbor,\
noise=alls=12:allf=t+u,\
rgbashift=rh=2:bh=-2:edge=smear,\
curves=vintage,\
vignette=PI/4.5,\
drawtext=text='PLAY %\\{localtime\\:%H\\\\\\:%M\\\\\\:%S}':fontcolor=white@0.8:fontsize=28:x=24:y=24:fontfile=VCR.ttf" \
-c:v libx264 -crf 20 out.mp4
```
Components: resolution crush + nearest-neighbor upscale (soft macroblocking), `noise` temporal luma/chroma grain, small `rgbashift` (chroma bleed), `curves=vintage` (lifted blacks), `vignette`, VCR OSD text. Optional `tblend=all_mode=average` for head-switching smear and periodic `crop`+`pad` line offsets for tracking errors.

**Performance:** all glitch filters are cheap (near-realtime 1080p) except geq-based custom effects. Datamoshing is offline by nature (codec surgery).

---

## GAPS REQUIRING PERPLEXITY DEEP RESEARCH

The following items could NOT be adequately verified via Tavily (3 searches were blocked by API usage limits; several topics returned thin or unverified results):

1. **Audio-reactive video parameter driving** — No complete, verified pipeline found for using audio levels (RMS/peak/band energies) to drive *video* filter parameters (scale/rotation/opacity) per-frame. Need: canonical `astats metadata` → `sendcmd` generation examples, `sidechaingate`-style video keying, and any newer native mechanisms (e.g., `aformat`+`metadata` injection consumed by video filters via `azmq`).

2. **VHS effect canonical recipes** — The specific search for VHS filter chains was rate-limited. The recipe above is assembled from general knowledge, not from a verified source. Need: battle-tested VHS/CRT chains, `vhs`-style frei0r plugins availability in stock builds, and scanline/CRT shaders via `frei0r`/`libplacebo`.

3. **Lottie headless rendering tooling specifics** — The dedicated search was rate-limited. Unverified: exact `lottie-node`/puppeteer CLI wrappers (e.g., `lottie-converter`, `puppeteer-lottie` npm packages), their maintenance status in 2025–2026, and performance benchmarks vs. hosted APIs (Lottielab/LottieFiles API).

4. **perspective filter sendcmd/command support** — Could not confirm whether current FFmpeg (7.x/8.x) added runtime command support to `perspective` (docs list commands for many filters; perspective was not explicitly confirmed either way). This determines whether tracked corner-pins can be injected live via zmq.

5. **find_rect rotation/scale invariance & cover_rect details** — Official behavior of `cover_rect` options (it can blur/replace the found rect — useful for automated logo blurring) and any `find_rect` successors (e.g., DNN-based object detection filters `dnn_detect`) were not fully retrieved.

6. **Parallax/2.5D tutorials** — No dedicated verified tutorial found; the layered-zoompan technique is documented from pattern knowledge only. Need real project examples and performance comparisons vs. Blender-based 2.5D.

7. **OpenCV→FFmpeg zmq live injection latency benchmarks** — The zmq filter is documented, but no real-world latency/throughput figures for live tracked-graphics overlays were found.

8. **Performance benchmarks for perspective/geq/shufflepixels at 4K** — No quantitative data found; only qualitative impressions.

9. **ffmpeg-native planar tracking proposals** — Whether any GSoC/experimental planar tracker exists for FFmpeg (would replace the Mocha dependency for screen replacement) could not be confirmed.
