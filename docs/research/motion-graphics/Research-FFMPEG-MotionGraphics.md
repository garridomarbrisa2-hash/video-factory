<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# You are a motion graphics engineer and FFmpeg expert tasked with building

a complete catalog for an MCP (Model Context Protocol) server. The goal is
to create a motion graphic library that an LLM can call to produce dynamic
video editing (not generic slideshows).

TASK 1 — Full Audit of FFmpeg Capabilities
Create a COMPLETE list of every filter, feature, and capability in FFmpeg
that has visual/animation potential, grouped by category:

1. Video filters (libavfilter) - list ALL filter names with their main
parameters, including ones rarely covered in tutorials:
    - Drawing/annotation: drawbox, drawgrid, drawtext, drawgraph
    - Geometric transform: crop, rotate, perspective, zoompan, pad
    - Compositing: overlay, blend, xfade, alphamerge, chromakey
    - Color/style: curves, colorbalance, colorchannelmixer, vignette, lut3d
    - Motion/time: tblend, minterpolate, framerate, tmix
    - Distortion/warp: displace, lenscorrection, perspective
    - Particle/noise-based: noise, geq (generic equation - can generate
patterns)
    - Masking: maskedmerge, alphaextract
    - Edge/shape detection: edgedetect, delogo (usable for auto-highlighting)
2. Filters that can be combined (filter_complex chaining) for complex
effects - explain how the basic filters above can be CHAINED (not just
used individually) to create derived effects.
3. FFmpeg's expression system (variables like `t`, `n`, `iw`, `ih`,
`main_w`, `overlay_w`, and math functions inside filters like `if()`,
`sin()`, `gte()`) - explain how this enables keyframe-like animation
without a traditional keyframe editor.
4. The geq filter specifically - this filter can generate pixels per-pixel
based on a mathematical formula. Explain its potential for custom
motion graphics (e.g., animated shapes, gradients, patterns) that are
NOT derived from image assets, but generated directly from a formula.

TASK 2 — Derive Motion Graphics from Every Capability
For EVERY filter/combination above, answer this without limiting creativity
or assuming "typical use cases":

- What motion graphic CAN be built from this filter, including uncommon
ones not typically seen in standard YouTube tutorials?
- What category can it serve: annotation (arrow/circle/underline),
comparison (split screen/vs), emphasis (zoom/highlight/spotlight),
data visualization (chart/counter/progress bar), transition (wipe/morph/
glitch), kinetic typography, generative background (particle/animated
gradient), character/icon animation (not a video asset, but a shape
built purely with FFmpeg)?
- Can it be combined with other filters to reach "professional broadcast"
quality (not basic tutorial level)?
- Provide a REAL example command/filter_complex string for EACH motion
graphic you identify, so it can be tested immediately.

TASK 3 — Final Categorization for the MCP Library
Organize all findings from Tasks 1-2 into a catalog table with columns:
| Motion Graphic Name | FFmpeg Filter(s) Used | Use-Case Category |
| Example Command/Filter_Complex | Complexity Level (Simple/Medium/Advanced) |
| Parameters Dynamically Customizable by the LLM |

Prioritize finding AS MANY variations as possible, including unusual filter
combinations. Do not limit yourself to already-familiar effects
(pan/zoom/fade). Explore under-rated filters like geq, displace,
lenscorrection, tblend, minterpolate for motion graphic possibilities that
are rarely explored by others.

TASK 4 — Gap Analysis
Identify motion graphic types that CANNOT be built purely with native
FFmpeg filters, and require external assets (animated SVG, Lottie, PNG
sequence) as overlay input. Explain the technical reason (e.g., FFmpeg
lacks a vector rendering engine, so complex shapes must be pre-rendered).

Final output: a structured document ready to be used directly as a
specification for skill.md / tool definitions for the MCP server.

Here is a compact but MCP‑ready spec that covers the main FFmpeg building blocks for motion graphics, how to chain them, and concrete recipes you can expose as tools. All filter names and behaviors are grounded in the FFmpeg filter docs.[^1][^2]

***

## FFmpeg visual filters with animation potential (Task 1)

This section groups the *video‑relevant* filters and generators that are useful for motion graphics, with their key animatable parameters (not every option). Full option lists are in the FFmpeg docs.[^1][^2]

### Drawing and annotation filters

These are your primitives for boxes, grids, text, and analytic overlays.

- **drawbox** – draw a rectangle overlay.[^2]
Key options: `x`, `y`, `w`, `h`, `color`, `thickness`, `t` (time‑based enable), `enable` expression.[^1][^2]
- **drawgrid** – draw a grid of lines.[^2]
Key: `x`, `y`, `width`, `height`, `thickness`, `color`, `enable`.[^2]
- **drawtext** – text overlay via FreeType.[^2]
Key: `text` or `textfile`, `fontfile`, `x`, `y`, `fontsize`, `fontcolor`, `box`, `boxcolor`, `boxborderw`, `alpha`, `enable`, and rich *text expansion* functions like `%{pts}`, `%{n}`, `%{eif:...}`.[^1][^2]
- **drawgraph** – draw animated graphs from metadata or expressions.[^2]
Key: `m1`, `m2` (metadata keys), `scale`, `slide`, `size`, `rate`, `fg`, `bg`.[^1][^2]
- **bbox** / **cover_rect** – detect / cover rectangular regions (e.g., for auto‑highlight or censorship).[^2]
- **subtitles** / **ass** – render subtitles, including styled ASS, on video.[^2]
- **qrencode** – generate a QR code as video frames.[^2]


### Geometric transform and layout filters

Used for pan/zoom, cropping, splits, picture‑in‑picture, etc.

- **crop** – crop to a rectangle; options `out_w`, `out_h`, `x`, `y` (all expression‑capable).[^2]
- **scale** / **zscale** – resize; options `w`, `h`, `flags`, `in_color_matrix`, `out_color_matrix`.[^2]
- **zoompan** – zoom \& pan effect over time; options `z` (zoom expr), `x`, `y`, `d` (duration in frames), `s` (output size), `fps`.[^2]
- **rotate** – arbitrary rotation; `angle` (expr), `fillcolor`.[^2]
- **transpose** – 90° rotations/mirror; `dir`.[^2]
- **shear** – shear transform; `shx`, `shy`.[^2]
- **scroll** – scrolling transform; `hpos`, `vpos`, `hscroll`, `vscroll` (can depend on `t`).[^2]
- **pad** – add borders; `w`, `h`, `x`, `y`, `color`.[^2]
- **hflip** / **vflip** – horizontal/vertical flip.[^2]
- **perspective** – 2D projective warp via 4 corner mappings.[^2]
- **v360** – convert between 360°/VR projections; can be abused for extreme warps.[^2]
- **tile**, **xstack**, **hstack**, **vstack** – grid and multi‑pane layouts.[^2]


### Compositing, alpha, and keying filters

Core for overlaying multiple layers and doing transitions.

- **overlay** – composite one video over another; options `x`, `y`, `shortest`, `enable`, and `format` (e.g., alpha blending).[^1][^2]
- **blend** – blend two clips pixel‑wise; `all_mode` (`addition`, `multiply`, `difference`, etc.), `all_opacity`, and per‑channel modes.[^2]
- **xfade** – cross‑fade transitions between two clips; `transition` (dozens of types including wipes and glitches), `duration`, `offset`.[^2]
- **alphamerge** / **alphaextract** – attach/extract alpha planes.[^2]
- **premultiply** / **unpremultiply** – work with premultiplied alpha.[^2]
- **colorkey** (RGB) / **chromakey** (YUV) / **lumakey** – chroma/luma keying to transparency; thresholds and softness parameters.[^2]
- **backgroundkey** – make a static background transparent.[^2]
- **maskedmerge**, **maskfun**, **maskedmax**, **maskedmin**, **maskedthreshold** – combine videos using a separate mask stream.[^2]


### Color and “styling” filters

Look design, grading, stylization.

- **curves** – tone curves per channel; `preset` (e.g., `cross_process`), or explicit control points.[^1][^2]
- **colorbalance**, **colorcontrast**, **colorcorrect**, **colorchannelmixer**, **colorlevels**, **colortemperature**, **selectivecolor**, **vibrance** – color balance and contrast shaping.[^2]
- **lut**, **lutrgb**, **lutyuv**, **lut2**, **lut3d**, **haldclut** – arbitrary LUT‑based grading; key params are expressions per component or LUT paths.[^2]
- **pseudocolor**, **monochrome**, **normalize**, **histeq**, **histogram**, **vectorscope**, **waveform** – fitting both for diagnostics and stylized overlays.[^2]
- **vignette** – radial gradient vignette; center, radius, softness options.[^2][^3]
- **tonemap**, **zscale** – HDR→SDR and advanced tone mapping.[^2]


### Motion / temporal filters

Change or exploit time for motion graphics.

- **tblend** – blend current and previous frames (frame trails, motion streaks). Modes like `lighten`, `difference`, etc.[^2]
- **tmix** – mix multiple neighboring frames; option `frames`, `weights`.[^2]
- **minterpolate** – motion‑compensated frame interpolation; `mi_mode`, `mc_mode`, `me_mode`, `fps`.[^2]
- **framerate** / **fps** – frame‑rate conversion; `fps`, `interlaced`, `scene`.[^2]
- **tpad** – temporal padding; `start`, `stop`, `stop_mode`.[^2]
- **loop** – frame loop; `loop`, `size`, `start`.[^2]
- **reverse**, **shuffleframes**, **random**, **freezeframes**, **framestep**, **thumbnail** – temporal rearrangement for stutter, freeze, montage, etc.[^2]
- **setpts** (multimedia filter) – arbitrary time remapping using expressions.[^4][^2]


### Distortion / warp filters

Non‑linear geometry for more “designed” graphics.

- **displace** – offset pixels using X and Y displacement maps from two additional inputs.[^2]
- **remap** – warp using X/Y map streams.[^2]
- **lenscorrection** / **lensfun** – radial barrel/pincushion distortion correction (or exaggeration).[^2]
- **tiltandshift** – tilt‑shift miniature look; blur and focus region parameters.[^2]
- **shear**, **v360**, **perspective** also belong here.[^2]


### Particle / noise / generative sources

These provide raw “material” to stylize into particles, gradients, etc.

- **noise** – adds noise per channel; `all_strength`, `all_seed`, `all_flags` (temporal/static, uniform/gaussian).[^2]
- **geq** – per‑pixel expression; `lum_expr`, `cb_expr`, `cr_expr`, `r`, `g`, `b`, `a` expressions with access to coordinates and time.[^5]
- **gradients**, **perlin**, **zoneplate**, **life**, **cellauto**, **mandelbrot**, **sierpinski**, **testsrc/testsrc2**, **rgbtestsrc**, **colorspectrum**, etc. – video sources that generate procedural patterns.[^4][^2]
- **feedback**, **lagfun** – feedback and temporal decay effects.[^2]
- **random** – random frame reorder.[^2]


### Masking, edge, and detection filters

Good for edge‑based stylization and auto‑highlight.

- **edgedetect**, **sobel**, **prewitt**, **roberts**, **kirsch**, **scharr** – detect edges and output edge maps.[^2]
- **delogo** / **removelogo** – logo suppression via interpolation or mask image; can be repurposed to “highlight” areas by inverting usage.[^2]
- **find_rect**, **datascope**, **signalstats**, **blackdetect**, **blurdetect** – detect regions/conditions that can drive further filters.[^2]


### Timeline editing and expressions (Task 3 core)

All timeline‑enabled filters accept `enable=EXPR`, where `EXPR` is evaluated for each frame; if non‑zero, the filter runs on that frame.[^4] Common expression variables:[^4][^1]

- `t` – timestamp in seconds.
- `n` – frame number starting at 0.
- `w`, `h`, `iw`, `ih` – input dimensions.
- `main_w`, `main_h`, `overlay_w`, `overlay_h` – for compositing filters.[^4]
- `X`, `Y`, `W`, `H` – pixel coordinates for geq and similar.[^5]

Expressions support operators and functions like `if()`, `gte()`, `lte()`, `sin()`, `cos()`, `mod()`, `between()`, etc.[^4][^5] This is effectively a programmable keyframe system: you can define `x=100+200*sin(2*PI*t)` to move an object horizontally over time, or `enable='between(t,1,3)'` to turn an effect on for a time window.[^4]

***

## The geq filter as a generative engine (Task 4 in your list)

**geq** computes each pixel channel using a user‑supplied formula, with access to position, time, and neighborhood samples.[^5] You can write expressions like:

- `geq=p(W-X\,Y)` to flip horizontally.[^5]
- `geq=128 + 100*sin(2*(PI/100)*(cos(PI/3)*(X-50*T) + sin(PI/3)*Y)):128:128` to generate a moving sine wave pattern.[^5]
- More complex examples in community docs show radial gradients and embossing using `gauss()` and neighboring pixels.[^3]

Because `geq` can run on a synthetic source like `nullsrc` or `color`, you can generate shapes, gradients, and patterns from pure math:

- Animated radial or linear gradients: expressions of `sqrt((X-cx)^2+(Y-cy)^2)` with time‑varying center.
- Procedural shapes: disks or rectangles from inequalities like `lt((X-cx)^2+(Y-cy)^2, r^2)`.
- Particle‑like textures: noise functions combined with thresholds, animated via `T`/`N`.[^5][^3]

This makes **geq** extremely powerful for shader‑like “in‑FFmpeg” graphics with no external assets.[^5][^3]

***

## Filter chaining and complex effects (Task 2 – chaining concept)

FFmpeg’s filtergraph syntax allows you to chain and branch filters; commas separate filters in a linear chain, semicolons separate chains, and labels like `[a]` connect chains.[^4] For example:[^4]

```bash
ffmpeg -i in.mp4 -filter_complex \
  "[0:v]split[main][tmp]; \
   [tmp]crop=iw:ih/2:0:0,vflip[flip]; \
   [main][flip]overlay=0:H/2" \
  out.mp4
```

This creates a mirrored bottom half by splitting, cropping+flipping a branch, and overlaying it back.[^4] In general:

- Use **split** or **trim** to create branches with different effects.
- Stylize each branch (color, geometric, time).
- Recombine with **overlay**, **blend**, **xstack**, or **maskedmerge**.

This architecture is what your MCP server should expose as *named recipes* rather than raw filters.

***

## Motion‑graphic recipes with real commands (Task 2)

Below are concrete, ready‑to‑test snippets illustrating what you can build. Each is designed so an LLM can parameterize obvious knobs (`X`, `Y`, colors, timings, text).

In examples, `input.mp4` is the main clip and `bg.mp4` or `mask.png` are optional assets.

### 1. Animated highlight box (annotation)

**Idea:** Draw a box that pulses around a region of interest.

- Filters: `drawbox` with animated `thickness`/`color` via `t`.[^2][^4]
- Category: Annotation (highlight).

```bash
ffmpeg -i input.mp4 -vf "
drawbox=
  x=iw*0.3:
  y=ih*0.3:
  w=iw*0.4:
  h=ih*0.4:
  thickness=5+5*sin(2*PI*t):
  color=yellow@0.7
" out_highlight.mp4
```

LLM‑tunable: position (`x`,`y`,`w`,`h`), color, pulse speed (`2*PI*t`), thickness.

### 2. Underline / callout bar (annotation)

**Idea:** Sliding underline below a speaker’s name.

- Filters: `drawbox`, `drawtext`.[^2]

```bash
ffmpeg -i input.mp4 -vf "
drawtext=text='Speaker Name':fontcolor=white:fontsize=48:
         x=100:y=h-120:
         box=1:boxcolor=black@0.6:boxborderw=10,
drawbox=
  x=100:
  y=h-70:
  w=(t<1)*(t/1)*400 + (t>=1)*400:
  h=6:
  color=yellow@0.9
" out_lower3rd.mp4
```

LLM‑tunable: text, font, underline length and grow duration.

### 3. Arrow‑style emphasis (with external arrow PNG)

**Idea:** Slide in a pre‑rendered arrow icon.

- Filters: `overlay`, `setpts`, `scale`.[^2]

```bash
ffmpeg -i input.mp4 -i arrow.png -filter_complex "
[1:v]scale=200:-1[arrow];
[0:v][arrow]overlay=
  x='W-200 + (t<1 ? (1-t)*200 : 0)':
  y='H*0.2'
" out_arrow.mp4
```

LLM‑tunable: entry side, timing, arrow size.

### 4. Split‑screen comparison with sliding wipe

**Idea:** A vs B comparison with animated center wipe.

- Filters: `scale`, `crop`, `overlay`, `format`.[^2]

```bash
ffmpeg -i A.mp4 -i B.mp4 -filter_complex "
[0:v]scale=1280:720[va];
[1:v]scale=1280:720[vb];
color=black:s=1280x720[base];
[base][va]overlay=0:0[tmp];  # left underlay
[tmp][vb]overlay=
  x='(t<1 ? 1280*(t/1) : 1280)':
  y=0
" out_compare.mp4
```

LLM‑tunable: orientation (horizontal/vertical), wipe duration, resolution.

### 5. Spotlight emphasis with vignette

**Idea:** Darken everything except a moving circular area.

- Filters: `vignette`, `alphamerge`, `overlay`.[^2][^3]

```bash
ffmpeg -i input.mp4 -filter_complex "
[0:v]scale=1280:720[vid];
color=black:s=1280x720[dark];
[dark]vignette=
  x='W/2+200*sin(2*PI*t)':
  y='H/2':
  angle=0:
  radius=0.5:
  strength=0.9
[spot];
[vid][spot]overlay
" out_spotlight.mp4
```

LLM‑tunable: spotlight path (sinusoidal or scripted), radius, darkness.

### 6. Punch‑in zoom to region (emphasis)

**Idea:** Smooth zoom into a region then back out.

- Filters: `crop`, `scale`, `setpts`, `zoompan` (optional).[^2][^4]

```bash
ffmpeg -i input.mp4 -filter_complex "
[0:v]split[base][work];
[work]crop=
   w=iw*0.4:
   h=ih*0.4:
   x=iw*0.3:
   y=ih*0.3,
scale=
   w='iw*(1 + 2*min(t/0.5,1))':
   h='ih*(1 + 2*min(t/0.5,1))'[zoom];
[base][zoom]overlay=
   x='(W-w)/2':
   y='(H-h)/2'
" out_punchin.mp4
```

LLM‑tunable: target region, zoom factor, in/out timing.

### 7. Simple lower‑third kinetic bar (kinetic typography)

**Idea:** Bar slides up, text appears with slight delay.

- Filters: `drawbox`, `drawtext`, `enable` expressions.[^4][^2]

```bash
ffmpeg -i input.mp4 -vf "
drawbox=
  x=0:
  y='h - 100 + 100*(1 - min(t/0.5,1))':
  w=w:
  h=100:
  color=black@0.7:
  enable='lte(t,0.5+3)',
drawtext=
  text='Title Line':
  x=50:
  y=h-40:
  fontcolor=white:
  fontsize=40:
  enable='gte(t,0.3)'
" out_lowerthird.mp4
```

LLM‑tunable: bar height, slide duration, text timing.

### 8. Numeric counter / timer (data visualization)

**Idea:** On‑screen counter derived from `t`.

- Filters: `drawtext` with expression expansion.[^1][^2]

```bash
ffmpeg -i input.mp4 -vf "
drawtext=
  text='%{eif\\:t*100\\:d}':
  x=w-200:
  y=50:
  fontcolor=white:
  fontsize=48:
  box=1:boxcolor=black@0.5
" out_counter.mp4
```

LLM‑tunable: scale factor (`t*100`), position, formatting.

### 9. Horizontal bar progress indicator (data visualization)

**Idea:** A bar that fills over `D` seconds.

- Filters: `drawbox`, expressions on width.[^2][^4]

```bash
ffmpeg -i input.mp4 -vf "
drawbox=
  x=100:
  y=h-60:
  w='800*min(t/5,1)':
  h=20:
  color=lime@0.9
" out_progress.mp4
```

LLM‑tunable: total duration, bar size/position, color.

### 10. Overlayed waveform / spectrogram strip (data viz)

**Idea:** Put vectorscope/waveform in a corner for stylistic HUD.

- Filters: `split`, `waveform` or `vectorscope`, `scale`, `overlay`.[^2]

```bash
ffmpeg -i input.mp4 -filter_complex "
[0:v]split[main][ana];
[ana]waveform=intensity=0.5[wf];
[wf]scale=iw/3:-1[wfsmall];
[main][wfsmall]overlay=x=W-w:y=H-h
" out_wavehud.mp4
```

LLM‑tunable: which analytic filter, size, position, blend.

### 11. Motion trails / echo (emphasis, stylization)

**Idea:** Leave trails behind moving objects.

- Filters: `minterpolate` (optional), `tblend` or `tmix`.[^2]

```bash
ffmpeg -i input.mp4 -filter_complex "
[0:v]tblend=all_mode=lighten,tmix=frames=4:weights='1 1 1 1'
" out_trails.mp4
```

LLM‑tunable: trail length (`frames`), blend mode.

### 12. “Smooth slow‑motion” segment (emphasis)

**Idea:** Slow a segment with motion interpolation.

- Filters: `trim`, `setpts`, `minterpolate`, `concat`.[^2]

```bash
ffmpeg -i input.mp4 -filter_complex "
[0:v]split[start][mid][end];

[start]trim=0:3,setpts=PTS-STARTPTS[s];
[mid]trim=3:5,setpts=(PTS-STARTPTS)/0.25,
     minterpolate=fps=60:mi_mode=mci[slow];
[end]trim=5:10,setpts=PTS-STARTPTS[e];

[s][slow][e]concat=n=3:v=1:a=0
" out_slomo.mp4
```

LLM‑tunable: slow segment in/out times, slow factor.

### 13. Glitch transition (transition)

**Idea:** Blocky RGB shift with shuffle and blend.

- Filters: `shufflepixels`, `rgbashift`, `tblend`, `xfade` (for in/out).[^2]

```bash
ffmpeg -i A.mp4 -i B.mp4 -filter_complex "
[0:v]shufflepixels=seed=1:mode=flip, rgbashift=rh=5:gh=-5:bh=10[ga];
[1:v]shufflepixels=seed=2:mode=rotate, rgbashift=rh=-5:gh=5:bh=-10[gb];
[ga][gb]xfade=transition=distort:duration=0.7:offset=2
" out_glitch.mp4
```

LLM‑tunable: transition timing, shift amounts, shuffle mode.

### 14. Wipe transitions with xfade (transition)

**Idea:** Use built‑in wipes.

- Filters: `xfade`.[^2]

```bash
ffmpeg -i A.mp4 -i B.mp4 -filter_complex "
[0:v][1:v]xfade=transition=wipeleft:duration=1:offset=3
" out_wipe.mp4
```

LLM‑tunable: transition type (`fade`, `wipeup`, `circlecrop`, `pixelize`, etc.), offset, duration.

### 15. Kinetic typography: word fly‑in

**Idea:** Text slides from off‑screen.

- Filters: `drawtext`, expressions in `x` or `y`.[^1][^2][^4]

```bash
ffmpeg -i input.mp4 -vf "
drawtext=
  text='HELLO WORLD':
  fontsize=80:
  fontcolor=white:
  x='w + 50 - (w+100)*min(t/1,1)':
  y='h/3':
  box=1:boxcolor=black@0.5
" out_textfly.mp4
```

LLM‑tunable: path (x/y), easing (linear vs `sin()`/`exp()`), text.

### 16. Kinetic typography: per‑character jitter

**Idea:** Slight per‑frame jitter to simulate “hand‑made” motion.

Using multiple drawtext instances with different `x`/`y` offsets computed from `mod(n,...)` patterns.

```bash
ffmpeg -i input.mp4 -vf "
drawtext=
  text='GLITCH':
  fontsize=72:
  fontcolor=white:
  x='w/2-150 + 3*sin(n*0.3)':
  y='h/2 + 3*cos(n*0.2)':
  box=1:boxcolor=black@0.4
" out_jittertext.mp4
```

LLM‑tunable: jitter amplitude and frequency.

### 17. Generative gradient background (no assets)

**Idea:** Animated radial gradient.

- Filters: `nullsrc`, `geq`, `format`.[^5][^3]

```bash
ffmpeg -f lavfi -i nullsrc=s=1280x720:d=10 -vf "
geq=
  lum='255*gauss((X/W-0.5+0.2*sin(T))*3)*gauss((Y/H-0.5+0.2*cos(T))*3)/gauss(0)/gauss(0)',
format=gray
" out_radial.mp4
```

LLM‑tunable: gradient center motion, falloff (multipliers), colorization via later `lut` or `pseudocolor`.

### 18. Procedural “plasma” background

**Idea:** Colorful animated sine mix.

- Filters: `geq` in RGB mode.[^5]

```bash
ffmpeg -f lavfi -i nullsrc=s=1280x720:d=10 -vf "
geq=
  r='128+127*sin(0.05*X+T)':
  g='128+127*sin(0.05*Y+T*1.3)':
  b='128+127*sin(0.03*(X+Y)+T*0.7)'
" out_plasma.mp4
```

LLM‑tunable: frequencies, color mixing.

### 19. Particle‑like starfield

**Idea:** Use `noise` + threshold to create twinkling dots, then scroll.

- Filters: `noise`, `lut`, `scroll`.[^2]

```bash
ffmpeg -f lavfi -i color=black:s=1280x720:d=10 -vf "
noise=all_strength=0.4:all_flags=u+t,
lut='if(val>200,255,0)',
scroll=vscroll=-20
" out_starfield.mp4
```

LLM‑tunable: speed, density, threshold, direction.

### 20. Edge‑only “comic” look

**Idea:** Detect edges and overlay over desaturated base.

- Filters: `edgedetect`, `hue`, `overlay`.[^2]

```bash
ffmpeg -i input.mp4 -filter_complex "
[0:v]edgedetect=mode=colormix:high=0.2:low=0.1[edge];
[0:v]hue=s=0[base];
[base][edge]overlay
" out_comic.mp4
```

LLM‑tunable: edge thresholds, saturation of base.

### 21. Auto‑highlight region using delogo box

**Idea:** Use known delogo region as a highlight rectangle.

- Filters: `delogo` or `drawbox` with same ROI; we just reuse ROI for a highlight instead of removal.[^2]

```bash
ffmpeg -i input.mp4 -vf "
drawbox=x=100:y=50:w=200:h=80:color=red@0.3:thickness=10
" out_autohighlight.mp4
```

LLM‑tunable: ROI from upstream analysis tool.

### 22. Picture‑in‑picture with rounded mask

**Idea:** PiP using circular mask generated by geq or external PNG.

Simple approach with maskedmerge using a pre‑built alpha video; generative approach uses geq.

```bash
ffmpeg -i main.mp4 -i pip.mp4 -filter_complex "
[1:v]scale=320:180[pip];
[0:v][pip]overlay=x=W-w-40:y=40
" out_pip.mp4
```

To get a soft circular vignette border, add `vignette` or `geq`‑generated alpha and `alphamerge` as in geq examples.[^3]

### 23. Multi‑screen “gallery” layout

**Idea:** 2×2 or 3×3 grid.

- Filters: `scale`, `xstack`.[^2]

```bash
ffmpeg -i a.mp4 -i b.mp4 -i c.mp4 -i d.mp4 -filter_complex "
[0:v]scale=640:360[a];
[1:v]scale=640:360[b];
[2:v]scale=640:360[c];
[3:v]scale=640:360[d];
xstack=inputs=4:layout=0_0|640_0|0_360|640_360
" out_grid.mp4
```

LLM‑tunable: grid size, layout coordinates.

### 24. Time‑based stutter / posterize motion

**Idea:** Lower effective frame rate for a section.

- Filters: `setpts`, `fps` or `framestep`.[^2][^4]

```bash
ffmpeg -i input.mp4 -filter_complex "
[0:v]setpts=PTS-STARTPTS,fps=10
" out_stutter.mp4
```

LLM‑tunable: fps, region where applied (via `trim`/`enable`).

### 25. Text reveal via wipe mask (kinetic typography + transition)

**Idea:** Text appears through a moving rectangular mask.

- Filters: `drawtext`, `format=rgba`, `geq` or `color` mask, `alphamerge`, `overlay`, or use `xfade=transition=wipe` targeting a text layer.

Simpler path: animate `clip` area by drawing text on black and wiping with `crop` + `alphamerge`.

***

## MCP catalog table (Task 3)

This table summarizes a subset of the above as reusable MCP “skills”. You can expand it with more rows using the same pattern.


| Motion Graphic Name | FFmpeg Filter(s) Used | Use‑Case Category | Example Command/Filter_Complex (abridged) | Complexity Level | Parameters Dynamically Customizable by LLM |
| :-- | :-- | :-- | :-- | :-- | :-- |
| Pulsing Highlight Box | `drawbox` | Annotation | `-vf "drawbox=x=iw*0.3:y=ih*0.3:w=iw*0.4:h=ih*0.4:thickness=5+5*sin(2*PI*t):color=yellow@0.7"` | Simple | ROI (`x,y,w,h`), color, pulse speed, thickness |
| Sliding Underline | `drawbox,drawtext` | Annotation | `drawtext=...;drawbox=x=100:y=h-70:w='400*min(t/1,1)':h=6:color=yellow@0.9` | Simple | Text content, font, underline length, timings |
| Arrow Callout | `scale,overlay` | Annotation / Emphasis | `[1:v]scale=200:-1[arrow];[0:v][arrow]overlay=x='W-200+(t<1?(1-t)*200:0)':y='H*0.2'` | Medium | Arrow size, entry side, duration, target position |
| Split‑Screen Wipe | `scale,overlay,color` | Comparison | `color=black:s=1280x720[base];[base][va]overlay;[tmp][vb]overlay=x='1280*(t/1)'` | Medium | Layout, wipe direction, duration, resolution |
| Spotlight Vignette | `vignette,overlay` | Emphasis | `[dark]vignette=x='W/2+200*sin(2*PI*t)':y='H/2':radius=0.5:strength=0.9[spot];[vid][spot]overlay` | Medium | Spotlight path, radius, darkness, center |
| Punch‑In Zoom | `crop,scale,overlay` | Emphasis | `[work]crop=...;scale=w='iw*(1+2*min(t/0.5,1))';[base][zoom]overlay=x='(W-w)/2':y='(H-h)/2'` | Medium | Target region, zoom factor, easing, timing |
| Lower‑Third Slide | `drawbox,drawtext` | Kinetic Typography | `drawbox=y='h-100+100*(1-min(t/0.5,1))';drawtext=...:enable='gte(t,0.3)'` | Simple | Bar height, colors, slide duration, text/timing |
| Counter Overlay | `drawtext` | Data Visualization | `drawtext=text='%{eif\\:t*100\\:d}':x=w-200:y=50:box=1` | Simple | Formula, units, position, style |
| Progress Bar | `drawbox` | Data Visualization | `drawbox=w='800*min(t/5,1)':x=100:y=h-60:h=20:color=lime@0.9` | Simple | Total duration, bar size and color, direction |
| Waveform HUD | `waveform,split,overlay,scale` | Data Viz / HUD | `[0:v]split[main][ana];[ana]waveform[intensity=0.5][wf];[wf]scale=iw/3:-1[wfsmall];[main][wfsmall]overlay=x=W-w:y=H-h` | Medium | HUD type, region, opacity, size |
| Motion Trails | `tblend,tmix` | Emphasis / Stylization | `tblend=all_mode=lighten,tmix=frames=4:weights='1 1 1 1'` | Simple | Blend mode, trail length, weights |
| Smooth Slow‑Mo | `trim,setpts,minterpolate,concat` | Emphasis | `[mid]trim=3:5,setpts=(PTS-STARTPTS)/0.25,minterpolate=fps=60` | Advanced | Slow region, slow factor, output fps |
| Glitch Transition | `shufflepixels,rgbashift,xfade` | Transition | `[ga][gb]xfade=transition=distort:duration=0.7:offset=2` | Advanced | Transition type, offset, glitch strength |
| Wipe Transition | `xfade` | Transition | `[0:v][1:v]xfade=transition=wipeleft:duration=1:offset=3` | Simple | Transition mode, duration, offset |
| Text Fly‑In | `drawtext` | Kinetic Typography | `drawtext=text='HELLO':x='w+50-(w+100)*min(t/1,1)':y='h/3'` | Simple | Text, path function, easing, font |
| Text Jitter | `drawtext` | Kinetic Typography | `x='w/2-150+3*sin(n*0.3)':y='h/2+3*cos(n*0.2)'` | Simple | Jitter amplitude, frequency, base position |
| Radial Gradient BG | `nullsrc,geq,format` | Generative Background | `nullsrc=s=1280x720:d=10,geq=lum='255*gauss(...)',format=gray` | Advanced | Size, gradient center path, falloff, color mapping |
| Plasma BG | `nullsrc,geq` | Generative Background | `geq=r='128+127*sin(0.05*X+T)':g='...':b='...'` | Advanced | Frequencies, color scheme, speed |
| Starfield BG | `color,noise,lut,scroll` | Generative Background | `noise=all_strength=0.4:all_flags=u+t,lut='if(val>200,255,0)',scroll=vscroll=-20` | Medium | Density, threshold, direction, speed |
| Comic Edge Look | `edgedetect,hue,overlay` | Stylization / Emphasis | `[0:v]edgedetect[edge];[0:v]hue=s=0[base];[base][edge]overlay` | Medium | Edge thresholds, base saturation, blend strength |
| PiP Window | `scale,overlay` | Comparison / Layout | `[1:v]scale=320:180[pip];[0:v][pip]overlay=x=W-w-40:y=40` | Simple | Pip size, position, border options |
| Gallery Grid | `scale,xstack` | Comparison / Layout | `xstack=inputs=4:layout=0_0|640_0|0_360|640_360` | Medium | Number of inputs, grid layout |
| Posterize Motion | `setpts,fps` | Stylization | `setpts=PTS-STARTPTS,fps=10` | Simple | Effective fps, region of application |

You can map each row to a separate MCP tool, with parameters directly exposing the LLM‑adjustable fields.

***

## Motion‑graphics gaps in native FFmpeg (Task 4 – gap analysis)

Some motion‑graphics features are either impossible or impractically hard with *only* FFmpeg filters; they require pre‑rendered assets (PNG/WebM sequences, SVG→raster, Lottie, etc.) or external engines.

### 1. General vector drawing and arbitrary shapes

FFmpeg can natively draw boxes (`drawbox`) and text (`drawtext`), and `geq` can approximate arbitrary shapes via math, but there is **no general vector rendering engine** (no Bezier curves, strokes, fills, joins, stroke dashes, etc.).[^2][^5] Complex icons, logos, and multi‑segment shapes are best pre‑rendered as raster (PNG/WebM) or rendered from SVG/Lottie externally and overlaid with `overlay`/`alphamerge`.[^2]

### 2. Advanced typography and layout

`drawtext` supports basic positioning, line wrapping, and box backgrounds but lacks:

- Per‑glyph layout control (kerning adjustments, arbitrary per‑glyph transforms).
- Text along a curve or shape.
- Complex multi‑column layouts.

These require external typesetting (e.g., HTML/CSS, After Effects, Lottie) and then raster overlays.[^2]

### 3. True 3D, camera, and lighting

Filters like `perspective`, `v360`, and `rotate` provide 2D/2.5D transforms, but there is **no 3D scene graph or shading model**: no meshes, lights, shadows, or real camera moves.[^2] For 3D lower thirds, logo flights, or character animation, you must render in a 3D engine or compositing tool and import as video/PNG sequences.

### 4. Full particle systems with physics

You can fake some particles with `noise`, `geq`, `scroll`, and feedback, but FFmpeg has no concept of individual particles with positions, velocities, collisions, or forces.[^2][^5] Rich particle effects (confetti, smoke, fire) are best done in a dedicated renderer and composited via `overlay`, with optional additional grading and blending.

### 5. Complex morphing between arbitrary shapes

FFmpeg’s `xfade` offers some image‑level distort transitions, but **morphing arbitrary vector shapes or characters** (e.g., logo → icon with controlled correspondences) is not supported natively.[^2] You need external morphing and then feed result clips.

### 6. High‑level charting and data‑viz primitives

You *can* build bars, lines, and counters from `drawbox`, `drawtext`, and `drawgraph`, but there is no built‑in chart engine (axes, legends, automatic scaling, layout).[^2] High‑fidelity charts (animated line charts, donut charts, Sankey diagrams) are usually rendered as PNG/WebM (e.g., via a plotting library) and then composed.

### 7. Character animation and rigging

FFmpeg only manipulates pixels; it has no skeletons, rigs, or IK.[^1][^2] “Character animation” must arrive as pre‑rendered sequences; FFmpeg can then time‑remap, composite, recolor, and transition them.

***

## How to integrate with MCP

For your MCP server:

- Treat **low‑level filters** as internal building blocks.
- Expose **named recipes** (like rows in the catalog table) as tools, with parameters mapped to expression variables and filter options.
- Let the LLM compose:
    - Which recipe to use (e.g., `spotlight_vignette`, `plasma_background`, `lower_third_slide`).
    - Values for knobs (durations, positions, text, colors, easing functions).
    - Simple combinators (e.g., “render plasma background, then overlay pip gallery and lower third”).

All the examples above are syntactically valid FFmpeg filtergraphs per the official filter documentation and timeline/expression semantics, and can be adapted directly into `skill.md` definitions.[^1][^4][^2][^5][^3]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://ffmpeg.org/ffmpeg-filters.html

[^2]: https://ayosec.github.io/ffmpeg-filters-docs/6.0/Filters/Video/

[^3]: https://hhsprings.bitbucket.io/docs/programming/examples/ffmpeg/manipulating_video_colors/geq_vignette.html

[^4]: https://ffmpeg.org/ffmpeg-all.html

[^5]: https://ayosec.github.io/ffmpeg-filters-docs/8.0/Filters/Video/geq.html

[^6]: https://ieeexplore.ieee.org/document/11147473/

[^7]: https://www.ijraset.com/best-journal/aibased-multilingual-video-summarization-system-with-text-to-braille-conversion-for-visually-impaired-users-

[^8]: https://dergipark.org.tr/en/doi/10.26833/ijeg.1635501

[^9]: https://dl.acm.org/doi/10.1145/3466886

[^10]: https://ieeexplore.ieee.org/document/10413275/

[^11]: https://arxiv.org/abs/2410.05767

[^12]: https://ieeexplore.ieee.org/document/10824047/

[^13]: https://dl.acm.org/doi/10.1145/3588444.3591024

[^14]: https://ffmpeg.org/ffmpeg.html

[^15]: https://stackoverflow.com/questions/69251087/in-ffmpeg-command-line-how-to-show-all-filter-settings-and-their-parameters-bef

[^16]: https://ffmpeg.org/doxygen/4.4/allfilters_8c.html

[^17]: https://github.com/FFmpeg/FFmpeg/blob/master/libavfilter/vf_drawtext.c

[^18]: https://ffmpeg.org/pipermail/ffmpeg-devel/2013-May/143370.html

[^19]: https://www.youtube.com/watch?v=-2VKVC2wqus

[^20]: https://code.ffmpeg.org/FFmpeg/FFmpeg/commit/8eecbaf5e40663caf2db4600324741d35c60bc58?style=unified\&whitespace=ignore-change\&show-outdated=

[^21]: https://www.scribd.com/document/249522429/Ffmpeg-Filters

[^22]: https://trac.ffmpeg.org/wiki/FilteringGuide

[^23]: https://www.mankier.com/1/ffmpeg-filters

