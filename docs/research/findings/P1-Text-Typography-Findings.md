# P1 — Text & Typography Research Findings
## FFmpeg Text Rendering for Professional Video Graphics

**Research date:** 2026-07-21
**Method:** Tavily web search (10 queries) + direct documentation extraction
**Scope:** drawtext, ASS/libass, kinetic typography, dynamic layout, font management, easing expressions

---

## TOPIC 1 — FFmpeg `drawtext` Complete Options

### 1.1 Technique: Core drawtext rendering pipeline
- **Implementation:** drawtext filter (requires `--enable-libfreetype`, `--enable-libharfbuzz`; font fallback needs `--enable-libfontconfig`; RTL shaping needs `--enable-libfribidi`)
- **Complete parameter surface** (from vf_drawtext.c source & FFmpeg 8.0 docs):
  - `fontfile` / `font` (fontconfig name), `text` / `textfile`, `reload` (frame-interval re-read), `fontsize` (expression), `fontcolor` / `fontcolor_expr`, `alpha` (expression)
  - `box` (0/1), `boxcolor`, `boxborderw` (1–4 edge values `T|R|B|L`), `boxw`, `boxh`, `line_spacing`
  - `borderw`, `bordercolor`, `shadowcolor`, `shadowx`, `shadowy`
  - `x`, `y` (expressions), `text_align` (T/M/B + L/C/R), `y_align` (text/baseline/font)
  - `tabsize`, `basetime`, `fix_bounds`, `expansion` (none/strftime/normal)
  - `ft_load_flags` (default, no_hinting, render, monochrome, etc.)
  - `text_shaping` (1/0, fribidi), `text_source` (side-data detection bboxes)
  - `timecode` + `rate`/`r` + `tc24hmax` for timecode burn-in
- **Runtime commands (sendcmd):** x, y, alpha, fontsize, fontcolor, boxcolor, bordercolor, shadowcolor, box, boxw, boxh, boxborderw, line_spacing, text_align, shadowx, shadowy, borderw — all hot-swappable via `sendcmd`/`zmq`.
- **Code example — full-featured burn-in:**
  ```
  drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Hello %{n}':
    fontsize=h/20:fontcolor=white@0.9:borderw=2:bordercolor=black@0.6:
    shadowcolor=black@0.5:shadowx=2:shadowy=2:
    box=1:boxcolor=black@0.4:boxborderw=12|20:
    x=(w-text_w)/2:y=h-text_h-40:enable='between(t,1,5)'
  ```
- **Customization points:** every geometry/color/alpha value accepts per-frame expressions.
- **Performance:** moderate — glyph rasterization is cached per glyph; cost scales with unique characters × font size changes. Animating `fontsize` defeats the glyph cache (expensive). `reload=1` re-reads file every frame (disk I/O).
- **Limitations & workarounds:**
  - **No automatic word wrap.** Newlines must be literal `\n` in text or textfile. Workaround: pre-wrap externally (Python/shell) or use ASS.
  - **`fontsize` animation is costly** (cache misses) — use ASS `\fscx/\fscy` or overlay+scale instead.
  - **Windows font paths need escaped colon:** `fontfile='C\:/Windows/Fonts/arial.ttf'`.
  - **`%` must be escaped** in text unless `expansion=none`.

### 1.2 Technique: Text expansion functions
- **Implementation:** drawtext `%{...}` expansion (normal mode)
- **Available functions:**
  - `%{n}` / `%{frame_num}` — frame counter from 0
  - `%{pts[:flt|hms|gmtime|localtime[:offset[:24HH|strftime-fmt]]]}` — frame PTS
  - `%{localtime[:strftime-fmt]}` / `%{gmtime[:strftime-fmt]}` — wall clock; extended `%[1-6]N` gives fractional seconds
  - `%{metadata:key[:default]}` — frame metadata (e.g., `%{metadata\:lavf.image2dec.source_basename\:NA}`)
  - `%{expr\:EXPR}` / `%{e\:EXPR}` — evaluate numeric expression
  - `%{expr_int_format\:EXPR\:x|X|d|u[:padding]}` / `%{eif\:...}` — formatted integer output
  - `%{pict_type}` — I/P/B frame type
- **Code example — ms-precision timestamp:**
  ```
  drawtext=text='%{localtime\:%X}.%{eif\:1M*t-1K*trunc(t*1K)\:d\:3}'
  ```
  or simpler with extended strftime: `text='%{localtime\:%X.%N}'`
- **Limitation:** `%{expr}` can only return **numbers**, not strings — `if(gt(t,1.5),'ab','a')` FAILS. Workaround: chain multiple drawtext with `enable='between(t,...)'` windows, or the crop-reveal trick (fixed-width fonts only).

---

## TOPIC 2 — ASS Subtitle Format & libass

### 2.1 Technique: ASS override tags for typography
- **Implementation:** ASS file burned via `ass=file.ass` or `subtitles=file.ass` filter (libass). Use `ass` filter for complex ASS (dedicated init path); `subtitles` also handles SRT→ASS conversion.
- **PlayRes contract:** Always set `PlayResX`/`PlayResY` in `[Script Info]`. If missing, libass assumes **384×288** — coordinates silently wrong. Set them to design resolution (e.g., 1080/1920 for vertical video).
- **Positioning tags:**
  - `\pos(x,y)` — absolute position of line anchor
  - `\move(x1,y1,x2,y2[,t1,t2])` — linear move; t1/t2 in ms relative to line start
  - `\an1`–`\an9` — numpad alignment (1=bottom-left, 5=middle-center, 8=top-center)
  - `\org(x,y)` — rotation origin
  - `\fad(t1,t2)` / `\fade(a1,a2,a3,t1,t2,t3,t4)` — fade in/out
- **Style/transform tags:**
  - `\fs` (size), `\fscx`/`\fscy` (scale % — **prefer over `\fs` for animation**, avoids hinting jumps)
  - `\frx`/`\fry`/`\frz` (3-axis rotation, degrees; `\frz-30` ≡ `\frz330`; `\t(\frz3600)` = 10 revolutions)
  - `\fax`/`\fay` (shear), `\fsp` (letter spacing), `\bord`, `\shad`, `\xbord`/`\ybord`, `\xshad`/`\yshad`
  - `\blur`, `\be` (blur edges), `\c&HBBGGRR&`, `\1a`–`\4a` (alpha per layer), `\alpha&H00–FF&`
  - `\fe` (encoding), `\fn` (font name), `\b`/`\i`/`\u`/`\s` (weight/style toggles)
- **Code example — positioned, faded, rotated:**
  ```
  Dialogue: 0,0:00:01.00,0:00:05.00,Default,,0,0,0,,{\an5\pos(960,540)\fscx150\fscy150\frz-15\blur0.8\fad(300,300)\1c&H00FFFF&\3c&H000000&\bord3}KINETIC
  ```

### 2.2 Technique: `\t` transformations (the animation engine)
- **Syntax:** `{\t(t1,t2,accel,tags)}` — t1/t2 in ms, accel (0.5=fast-slow, 1=linear, 2=slow-fast). Omit times = whole line duration.
- **Animatable tags:** colors, alphas, `\bord \shad \xbord \ybord \xshad \yshad`, `\fs \fsp \fscx \fscy`, `\blur \be`, `\fax \fay \frx \fry \frz`, `\clip` (rect only interpolates linearly).
- **Multiple `\t`s chain:** `{\t(0,500,\fscx200)\t(500,1000,\fscx100)}` = pop then settle.
- **accel trick:** accel >1 = ease-in (slow start), <1 = ease-out. Not full Penner curves, but enough for most kinetic type.
- **Performance:** cheap — libass evaluates per-event, rasterizes once per frame change. Far cheaper than per-char drawtext chains.

### 2.3 Technique: Karaoke `\k` family
- **Tags:** `\k` (instant fill), `\K`/`\kf` (sweep fill L→R), `\ko` (outline sweep), `\kt` (set absolute time). Duration in **centiseconds**.
- **Mechanism:** before syllable time → `SecondaryColour`; after → `PrimaryColour`. Set `SecondaryColour` transparent for word-reveal:
  ```
  Dialogue: 0,0:00:00.00,0:00:03.46,Default,,0,0,0,,{\2a&HFF\k100}I'm {\k50}a {\k196}subtitle
  ```
- **Word-by-word reveal with border (needs `\t`):**
  ```
  Dialogue: 0,0:00:00.00,0:00:03.46,Default,,0,0,0,,I'm {\alpha&HFF\t(1000,1000,\alpha0)}a {\alpha&HFF\t(1500,1500,\alpha0)}subtitle
  ```
  (instant `\t` at t1=t2 acts as a delayed state change)
- **libass ≥0.16.0 note:** old libass used different word/glyph order with tags inside lines; modern builds follow ASS spec. Use Unicode bidi controls if targeting old renderers.

### 2.4 Technique: Vector drawing mode
- **Implementation:** `{\p1}` … `{\p0}` — text becomes a drawing canvas. `\pbo(y)` baseline offset.
- **Commands:** `m x y` (move), `n x y` (move no-close), `l x y` (line), `b x1 y1 x2 y2 x3 y3` (cubic Bézier), `s …` (b-spline, ≥3 points), `p` (extend spline), `c` (close).
- **All style tags apply** (fill=PrimaryColour, outline=OutlineColour, `\bord`, transforms, `\clip`).
- **Use cases:** underline boxes, highlight sweeps, progress bars, callout shapes, animated masks via `\clip(…drawing…)`.
- **Code example — rounded-rect highlight:**
  ```
  Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,{\p1\pos(200,200)\1c&H80000000&\bord0}m 0 0 l 300 0 300 60 0 60{\p0}
  ```
- **Limitation:** drawings are per-event; complex art = long strings. Generate programmatically (Python templating).

### 2.5 Burning ASS in FFmpeg
```
ffmpeg -i in.mp4 -vf "ass=kinetic.ass:fontsdir=./fonts" -c:a copy out.mp4
```
- `force_style='FontName=Inter,FontSize=28,Outline=2'` overrides styles (subtitles filter).
- `alpha=1` processes alpha channel (for transparent-background ProRes 4444 outputs).
- `wrap_unicode` (default on, libass ≥0.17 + libunibreak) — Unicode line breaking.
- **Build requirement:** `--enable-libass`; check with `ffmpeg -filters | grep -E "subtitles|ass"`.

---

## TOPIC 3 — Kinetic Typography Techniques

### 3.1 Word-by-word reveal
- **drawtext approach:** one drawtext per word, `enable='gte(t,N)'` + cumulative x offsets. Painful for long text; requires pre-measured word widths (use Python/Pillow or `ffprobe`-style pre-pass). Reddit practitioners pair it with Whisper/Azure TTS word timings.
- **ASS approach (recommended):** `\k` with transparent SecondaryColour, or per-word `{\alpha&HFF\t(t,t,\alpha&H00&)}`. Single event, trivially timed.
- **Verdict:** ASS wins decisively. drawtext only if generating filtergraph programmatically anyway.

### 3.2 Typewriter effect
- **drawtext (real):** crop-reveal trick — render full line on rgba layer, animate `crop=w=char_w*trunc(t*rate)`, colorkey, overlay:
  ```
  color=white:1280x120,fps=30[c];
  [c]format=rgba,drawtext=fontfile=cour.ttf:fontsize=60:text='HELLO WORLD':x=0:y=0,
  crop=trunc(12*t)*60:120:0:0,colorkey=FFFFFF:0.01:1[tx];
  [0:v][tx]overlay=100:600
  ```
  **Only works cleanly with monospace fonts** (known ffmpeg bug distorts proportional reveals).
- **ASS (fake):** per-character `\k` tags or `{\alpha&HFF\t(t,t,\alpha0)}` per char — works with any font, no crop bug.
- **Cursor blink:** drawtext `enable='lt(mod(t,1),0.5)'` on a `|` drawtext; or ASS `{\blink}` doesn't exist — emulate with two events alternating.

### 3.3 Scale pop
- **drawtext:** `fontsize=BASE*(0.7+0.3*ease)` — but glyph-cache thrash. Better: render static drawtext layer → `scale=w=iw*(1+0.2*u):h=-1` on the layer → overlay (interpolated scaling, cache-friendly).
- **ASS:** `{\fscx70\fscy70\t(0,150,0.5,\fscx110\fscy110)\t(150,300,0.5,\fscx100\fscy100)}` — overshoot pop with two chained transforms. Cheap, hinting-free (that's why `\fscx` not `\fs`).

### 3.4 Slide + fade
- **drawtext:**
  ```
  drawtext=text='SLIDE IN':x='lerp(-text_w,100,min((t-1)/0.5,1))':alpha='min((t-1)/0.5,1)':enable='gte(t,1)'
  ```
- **ASS:** `{\move(-300,540,960,540,0,500)\fad(200,0)}` — but note `\move` is **linear only**; combine with `\t(\fscx)` for emphasis or accept linear.

### 3.5 Character jitter / wiggle
- **drawtext:** `x=100+5*sin(t*17)`: `y=200+3*cos(t*23)` — whole-text shake only (no per-char control).
- **ASS:** per-char events with random offsets per frame is impractical; standard approach is generating N variants with `\pos` jitter across short (2–3 frame) events via script. Or `\frz` oscillation: `{\t(0,100,10,\frz2)\t(100,200,10,\frz-2)}` looped by event duplication.
- **Better:** render text to transparent video (ASS on alpha), then apply FFmpeg `rotate`/`crop`+`overlay` wobble or `tblend` noise downstream — hybrid pipeline.

### 3.6 Hybrid architecture (recommended for professional output)
Author all kinetic type in ASS (positions, `\t`, `\k`), burn onto transparent intermediate (`-c:v qtrle` or `png` image sequence with alpha), then composite with `overlay` — this separates typography from base-grade, allows re-use, and dodges drawtext's layout limits entirely.

---

## TOPIC 4 — Dynamic Text Layout

### 4.1 Text measurement constants
- Available in x/y/alpha expressions: `text_w`/`tw`, `text_h`/`th`, `line_h`/`lh`, `max_glyph_w`, `max_glyph_h`, `max_glyph_a` (ascent), `max_glyph_d` (descent), `ascent`, `sar`, `dar`, `hsub`, `vsub`, `w`/`h`/`n`/`t`.
- **Centering:** `x=(w-text_w)/2:y=(h-text_h)/2`
- **Baseline placement:** `y=h/2-ascent` or `y_align=baseline` (FFmpeg ≥7).
- **Multi-line vertical stack:** line i of N: `y=((h-text_h)/2) ± (i-(N-1)/2)*(text_h*1.25)` — empirical; use `line_spacing` for intra-block spacing instead.

### 4.2 Auto-centering with text_align (FFmpeg 7.1+)
- `text_align=MC` (middle-center) aligns text **within the box** (boxw/boxh). Combined with `boxw=W:boxh=H:x=0:y=0` gives true frame centering without `text_w` math — and works with `sendcmd` text updates where `text_w` would lag.

### 4.3 Multi-line wrapping
- **drawtext: NO automatic wrap.** `\n` (literal) breaks lines; tabs supported only with left alignment (`tabsize`).
- **Workarounds:**
  1. External pre-wrap (Python textwrap → textfile, `reload=1` picks up changes).
  2. `text_align=C` for center-justified multi-line blocks.
  3. **Use ASS** — libass wraps automatically to margins (`MarginL`/`MarginR`) with `wrap_unicode` and `q2` smart wrapping. This is the single biggest layout reason to choose ASS.

### 4.4 Font fallback
- drawtext: single fontfile only; missing glyphs render as `.notdef` boxes. Fallback only via fontconfig (`font=Sans` with fonts.conf fallback chain).
- libass: full fontconfig/fallback chain (fontprovider), per-glyph fallback works on Linux/macOS; Windows builds use fontconfig if configured or GDI-like fallback via fontsdir.

---

## TOPIC 5 — Font Management

### 5.1 fontconfig on Windows
- Windows FFmpeg builds ship `--enable-libfontconfig` but **no fonts.conf**. Fix:
  1. Create `fonts\` dir next to ffmpeg.exe
  2. Place minimal `fonts.conf` inside pointing at `WINDOWSFONTDIR`
  3. Set env vars `FONTCONFIG_FILE` / `FONTCONFIG_PATH` (blog "pure and applied" documents exact steps)
- Then `drawtext=font='Arial'` works without fontfile paths.

### 5.2 Embedded/per-project fonts
- `ass=...:fontsdir=./fonts` — libass loads extra fonts per-filter. Best practice: bundle fonts with project, use fontsdir, avoid system font dependency.
- ASS has **no font-embedding** in the file (unlike MKV attachments); mux fonts as MKV attachments for portable soft-subs: `-attach font.ttf -metadata:s:t mimetype=application/x-truetype-font`.

### 5.3 CJK / RTL / complex scripts
- drawtext: `text_shaping=1` (default when fribidi present) handles Arabic joining + bidi reversal; harfbuzz handles Devanagari/Indic shaping (confirmed working with Khula.ttf Hindi example).
- CJK: works with any CJK fontfile; vertical layout via `ft_load_flags=vertical_layout` (limited).
- libass: shaping engine `auto` (best available: FriBidi SIMPLE / HarfBuzz COMPLEX) — log line `Shaper: FriBidi 1.0.10 (SIMPLE) HarfBuzz-ng (COMPLEX)` confirms.

### 5.4 Emoji rendering
- **Color emoji is the weak point for both paths.** FreeType can render CBDT/COLR bitmap glyphs, but drawtext often yields monochrome emoji unless the color emoji font is directly fontfile'd and FreeType is new enough (FT_LOAD_COLOR).
- fontconfig fallback to Noto Color Emoji is notoriously fragile (NixOS/Arch threads): DejaVu ships B&W emoji that pre-empts color fonts; fixes involve blacklist configs or `<edit name="embeddedbitmap">`.
- **Reliable workaround:** pre-render emoji to PNGs (via Pillow/twemoji) and `overlay` them — bypasses font stack entirely. For emoji-heavy graphics this is the production-safe route.
- libass 0.17+ handles color emoji better than drawtext but still renderer-dependent.

---

## TOPIC 6 — Easing Functions in FFmpeg Expressions

### 6.1 Foundation pattern
Normalize time: `u = clip((t - t0)/d, 0, 1)`, apply easing to `u`, then `lerp(A, B, eased)` (FFmpeg ≥5 has native `lerp(x,y,z)`).

### 6.2 Linear
```
x='lerp(-200, 960, clip((t-1)/0.8, 0, 1))'
```

### 6.3 Sine-out (cheap, great default)
```
fontsize='S*(0.7 + 0.3*sin(PI/2*clip((t-1)/0.4,0,1)))'
```
Full sine in-out: `u' = (1 - cos(PI*u))/2`

### 6.4 Quadratic
- In: `u*u` — In-out: `if(lt(u,0.5), 2*u*u, 1-2*(1-u)*(1-u))`

### 6.5 Cubic
- In: `u*u*u`
- In-out (from xfade-easing repo, verified FFmpeg syntax):
  ```
  st(0, clip((t-1)/3, 0, 1)); st(0, if(lt(ld(0),0.5), 4*ld(0)^3, 1-4*(1-ld(0))^3)); lerp(A, B, ld(0))
  ```
  Note: `^` is exponent in FFmpeg expr; `st/ld` give local variables (requires `-filter_complex_threads 1` for thread safety).

### 6.6 Back (overshoot ~10%)
From xfade-easing (in-out):
```
st(0, clip((t-1)/0.6, 0, 1));
st(0, if(lt(ld(0),0.5),
   (ld(0)*7.18982-2.59491)*ld(0)*ld(0)*2,
   (ld(0)*7.18982-4.59491)*(1-ld(0))^2*2+1));
lerp(A, B, ld(0))
```
(c1 = 1.70158; coefficients 7.18982 = 4*c1+... per Michael Pohoreski single-arg Penner port.)

### 6.7 Elastic
Out (leaves result in st(0)):
```
st(0, clip((t-1)/0.8, 0, 1));
st(0, 1 - cos(ld(0)*20.944)/2^(10*ld(0)));
lerp(A, B, ld(0))
```
In: `st(0, cos((1-u)*20.944)/2^(10*(1-u)))`. **Overshoot clips values outside [0,1]** — clamp or use for scale where slight overshoot is desired; for positions ensure target bounds tolerate overshoot.

### 6.8 Practical drawtext example — elastic pop-in scale via layer scaling
```
[txt]scale=w='iw*(0.5+0.5*(1-cos(clip((t-1)/0.6\,0\,1)*20.944)/pow(2\,10*clip((t-1)/0.6\,0\,1))))':h=-1:eval=frame[txts];
[base][txts]overlay=(W-w)/2:(H-h)/2
```
(Layer-scale avoids drawtext glyph-cache thrash.)

### 6.9 ASS easing equivalent
- `\t` accel parameter: `accel<1` ease-out, `>1` ease-in — single-knob approximation. For Penner-accurate curves in ASS: script-generated per-frame `\t` slices (Aegisub automation like HYDRA) or apply easing via FFmpeg post-transform (zoompan/scale on subtitle layer).

### 6.10 Performance
- Pure-expression easings: negligible (per-frame float math).
- `st()/ld()` state: forces single-threaded filter slices → real slowdown on heavy filters (xfade, geq). For drawtext-only chains the impact is minor.
- xfade-easing repo (github.com/scriptituk/xfade-easing) is the canonical source of copy-paste Penner expressions for FFmpeg: quadratic, cubic, quartic, quintic, sinusoidal, exponential, circular, elastic, back, bounce + squareroot/cuberoot/flipelastic/flipback variants.

---

## QUICK DECISION MATRIX

| Need | Use |
|---|---|
| Static label, watermark, timecode | drawtext |
| Per-frame counter/metadata | drawtext (`%{n}`, `%{metadata}`) |
| Word-by-word / karaoke | ASS `\k` |
| Scale/rotate/shear animation | ASS `\t` + `\fscx/\frz` |
| Auto word-wrap | ASS (only option) |
| Multi-language/CJK/RTL at scale | ASS + fontsdir |
| Emoji-heavy graphics | Pre-rendered PNG overlay |
| Typewriter (monospace OK) | drawtext crop trick |
| Penner easing on position/size | drawtext expr with st/ld or ASS accel |
| Live-updating text | drawtext textfile + reload=1, or sendcmd |

---

## GAPS REQUIRING PERPLEXITY DEEP RESEARCH

1. **Color emoji in drawtext — definitive matrix.** Which FreeType versions + `ft_load_flags` combinations actually render CBDT/COLR/SBIX color emoji in current FFmpeg (8.x)? Contradictory anecdotal reports; no authoritative working command found. Need deep test-verified research.

2. **`\t` accel → Penner equivalence.** Exact mathematical mapping between ASS `\t` accel values and standard easing curves (is accel a cubic-hermite exponent? piecewise?). Aegisub docs don't specify the interpolation formula; libass source reading required.

3. **drawtext per-glyph animation.** Any patch/fork/technique for staggered per-character animation in drawtext (e.g., wave effects) without N separate filters? The 2023 drawtext rewrite (Harfbuzz cluster data) may have opened internals — need research on whether any build exposes glyph positions.

4. **Vertical text (CJK tategaki).** Real-world results of `ft_load_flags=vertical_layout`: does it produce correct vertical CJK with proper glyph substitution (vert/vrt2 features)? Almost zero documentation/examples found.

5. **ASS `\clip` animated vector mask interpolation.** libass behavior when `\clip` rectangles/paths are transformed via `\t` — rect interpolates, but do vector-path clips morph point-by-point? Edge cases with differing point counts undocumented.

6. **Performance benchmarks: drawtext-chain vs libass for 100+ animated text events.** No published fps/ms-per-frame comparisons. Needed for pipeline sizing decisions (when does drawtext chaining become slower than ASS authoring?).

7. **Variable fonts (fvar axes).** Can drawtext/libass address variable font weight/width axes (e.g., animate wght 100→900)? FreeType supports it; unclear if FFmpeg exposes any control. Possibly requires harfbuzz variation APIs — unverified.

8. **HarfBuzz cluster data in text_source / detection bboxes.** The new `text_source` option (side-data bboxes from detection filters) is essentially undocumented — use cases, interaction with OCR/ObjDet pipelines, and whether it enables auto-caption placement.

9. **libass `LayoutResX/Y` vs `PlayResX/Y` interplay** in modern libass (0.17.x) for responsive subtitle scaling — sparse docs.

10. **Right-to-left kinetic typography.** Whether `\k` karaoke and `\t` transforms behave correctly with RTL (Arabic/Hebrew) scripts under fribidi — bidi reordering vs syllable timing order is a known minefield with no consolidated guidance.
