# Research Prompt: Advanced FFmpeg Techniques for Professional Motion Graphics

## Role
You are a senior motion graphics artist and FFmpeg power user. The goal is to document advanced, non-obvious techniques that bridge the gap between "basic FFmpeg" and "professional broadcast graphics" — pushing native filters to their limits and integrating external tools where necessary.

## Context
The MCP server needs techniques that go beyond the basic catalog:
- Screen replacement and corner pinning
- Object tracking and auto-follow graphics
- Audio-reactive visualizations
- Advanced masking and rotoscoping
- 3D-like camera moves on 2D assets
- Integration with external renderers (Lottie, SVG, Blender)

---

## TASK 1 — Screen Replacement & Corner Pinning

Research `perspective` filter for practical screen replacement:

### Static Screen Replacement
- Source: video of phone/laptop screen
- Target: replacement content
- Challenge: 4 corner coordinates must be precise

Research:
- Coordinate detection: manual, `find_rect`, or CV-assisted
- Sub-pixel precision and anti-aliasing quality
- Motion blur handling for moving screens
- Reflection preservation (add fake reflection after replacement?)

### Dynamic Screen Replacement
- Screen moves in source video
- Options:
  1. Track corners frame-by-frame, generate perspective animation
  2. Stabilize source, replace, re-apply motion
  3. Use external tracker (OpenCV), feed coordinates to FFmpeg

Deliverable: Complete workflow for static and dynamic screen replacement

---

## TASK 2 — Object Tracking & Auto-Follow Graphics

Research methods to make graphics follow moving objects:

### Method 1: `find_rect` Filter
- Detects rectangular objects (faces, screens, logos)
- Outputs metadata with coordinates
- Use metadata in `drawbox`, `overlay` expressions

Research:
- Accuracy and reliability of `find_rect`
- Performance cost
- Minimum object size, contrast requirements

### Method 2: External Tracking → FFmpeg
- Use OpenCV (CSRT, KCF, MOSSE trackers) or ML (YOLO, Detectron)
- Export coordinates as JSON or CSV
- FFmpeg reads via `sendcmd`/`zmq` or pre-computed expressions

Research:
- Real-time vs offline tracking
- Coordinate format and injection method
- Handling track loss (object leaves frame)

### Method 3: Template Matching with `ffmpeg`
- `templatematch` filter (if available in build)
- Limited to rigid, high-contrast templates

Deliverable: Comparison matrix of tracking methods, implementation guide for each

---

## TASK 3 — Audio-Reactive Visualizations

Research visualizations driven by audio analysis:

### Built-in Audio Visualization
- `showwaves`: waveform, envelope, point, line, p2p, cline
- `showspectrum`: frequency spectrum, sliding, full-frame
- `showcqt`: constant-Q transform (musical notes)
- `avectorscope`: stereo phase/vectorscope
- `showvolume`: volume meter

### Advanced Techniques
- Extract audio features with `astats`, `aspectralstats`, `ebur128`
- Use metadata in `drawtext`, `drawbox` expressions
- Example: bass energy → scale of background pulse

### Beat Detection
- `ebur128` momentary loudness peaks
- `silencedetect` inverse (onset detection)
- External: `aubio`, `librosa` → beat timestamps → FFmpeg expressions

Deliverable: Audio-reactive recipe library with parameter mappings

---

## TASK 4 — Advanced Masking & Rotoscoping

Research masking beyond simple rectangles:

### Animated Masks
- `drawbox` with animated position/size — rectangular only
- `geq` for arbitrary shapes — circles, ellipses, polygons via math
- Image sequence masks — pre-rendered complex shapes
- `alphamerge` with video mask — luminance as alpha

### Rotoscoping (Manual)
- No native rotoscoping tool
- Workflow: export frames → rotoscope in external tool (After Effects, Nuke, Silhouette) → import as image sequence → `alphamerge`

### Auto-Masking
- `chromakey`, `colorkey`, `lumakey` — color-based
- `backgroundkey` — static background removal
- `edgedetect` + `morphology` — edge-based mask refinement
- ML-based: external (Runway, Remove.bg) → import alpha

Deliverable: Masking technique catalog with complexity ratings

---

## TASK 5 — 3D Camera Moves on 2D Assets (Ken Burns++)

Research beyond basic `zoompan`:

### Perspective Ken Burns
- `perspective` + `zoompan` combination
- Simulate dolly + pan + tilt on still image
- Parallax: separate foreground/midground/background layers

### Rotation + Scale
- `rotate` with animated angle + `scale` with animated size
- Pivot point control (rotate around arbitrary center)

### Shake and Handheld
- `crop` with random or sinusoidal offset
- `tblend` for motion blur simulation
- `noise` for micro-jitter

Deliverable: 3D-like move recipe library with parameters

---

## TASK 6 — External Tool Integration

Research when and how to integrate:

### Lottie/Bodymovin Animations
- `lottie` filter in FFmpeg? (No, but possible via `rlottie` or `lottie-web` → PNG sequence)
- Workflow: Lottie JSON → render to PNG sequence (Node.js, Python) → FFmpeg image sequence input
- Performance: rendering time vs native FFmpeg

### SVG Animation
- No native SVG animation support
- Workflow: SVG → rasterize frames (librsvg, resvg, Inkscape) → FFmpeg
- CSS animations → headless browser → screen capture → FFmpeg

### Blender/3D Integration
- Blender renders → FFmpeg compositing
- Camera tracking data from Blender → FFmpeg `perspective`?
- Alembic/FBX → FFmpeg? (No, render in Blender)

### HTML/CSS Animation
- Headless Chrome → screen capture → FFmpeg
- CSS animations more powerful than FFmpeg text
- Performance: real-time capture vs offline render

Deliverable: Integration guide with workflow diagrams, performance comparison

---

## TASK 7 — Creative Filter Combinations

Research non-obvious combinations for unique looks:

### Glitch Art
- `shufflepixels` + `rgbashift` + `tblend` + `displace`
- Data moshing: `select` + `setpts` for temporal smearing

### Dreamy/Ethereal
- `minterpolate` (blend mode) + `gblur` + `curves` + `vignette`
- `tmix` with high frame count for motion trails

### Retro/VHS
- `noise` + `rgbashift` + `curves` (crushed blacks) + `drawtext` (timestamp)
- `fieldmatch` + `yadif` for deinterlacing simulation

### Thermal/X-Ray
- `pseudocolor` with custom LUT
- `edgedetect` + `negate` + `pseudocolor`

### Infrared/Heat Map
- `lut` with red-yellow-blue gradient
- `selectivecolor` for skin tone emphasis

Deliverable: 10 creative look recipes with full filter chains

---

## TASK 8 — Performance vs Quality Tradeoffs in Advanced Techniques

Document cost of each technique:

| Technique | Render Time Factor | Quality Impact | When to Use |
|-----------|-------------------|----------------|-------------|
| `minterpolate` | 3-5x slower | Artifacts possible | Slow motion only |
| `geq` complex | 2-10x slower | Unlimited creativity | Generative backgrounds |
| External tracking | Pre-processing + 1x | High accuracy | Object follow graphics |
| Lottie integration | 2x (render + composite) | Vector quality | Brand animations |
| 4K geq | 4-8x slower | Stunning but slow | Hero shots only |

Deliverable: Decision matrix for technique selection based on deadline and quality requirements

---

## Final Output Format

1. **Screen replacement guide** — static and dynamic workflows
2. **Object tracking comparison** — 3 methods with implementation details
3. **Audio-reactive library** — visualizations with parameter mappings
4. **Masking technique catalog** — from simple to complex
5. **3D-like move recipes** — Ken Burns++, rotation, shake
6. **External integration guide** — Lottie, SVG, Blender, HTML/CSS
7. **Creative look recipes** — 10 unique styles with filter chains
8. **Performance/quality matrix** — technique selection framework
