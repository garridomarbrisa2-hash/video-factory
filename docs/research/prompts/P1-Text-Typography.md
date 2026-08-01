# Research Prompt: Text & Typography Deep Dive for Professional Video Graphics

## Role
You are a broadcast graphics designer and FFmpeg text rendering expert. The goal is to define a complete text/typography system for the FFmpeg MCP that produces broadcast-quality titles, lower thirds, kinetic typography, and data visualizations — overcoming `drawtext` limitations through advanced techniques.

## Context
Video automation requires:
- Lower thirds with speaker names/titles (animated in/out)
- Kinetic typography synchronized to voiceover
- Data counters and animated statistics
- Multi-language support (Latin, CJK, Arabic, RTL)
- Brand-consistent styling (fonts, colors, animations)
- Dynamic content (text length varies, must auto-layout)

---

## TASK 1 — `drawtext` Complete Capability Audit

Document every `drawtext` option with:
- Parameter name, type, default, range
- Timeline expression support (`t`, `n`, `x`, `y`, `w`, `h`)
- Text expansion functions: `%{...}` syntax, `eif`, `pts`, `n`, `metadata`
- Font loading: fontfile vs fontconfig vs system fonts
- Box and border options: `box`, `boxcolor`, `boxborderw`, `boxw`, `boxh`

### Critical Limitations to Document
- No per-character animation (kerning, rotation, color per character)
- No text on path/curve
- No multi-style text (bold + italic + color spans in one line)
- No automatic text wrapping with hyphenation
- Limited text measurement (no width query for dynamic layout)

---

## TASK 2 — ASS Subtitle Engine as Advanced Text Renderer

Research ASS (Advanced SubStation Alpha) as a text rendering engine:

### ASS Feature Set
- `\pos(x,y)`, `\move(x1,y1,x2,y2,t1,t2)` — positioning and animation
- `\an` alignment, `\frx\fry\frz` rotation, `\fscx\fscy` scaling
- `\bord`, `\shad`, `\be`, `\blur` — outline and shadow
- `\c&Hbbggrr&`, `\1c`, `\3c`, `\4c` — color control
- `\t(...)` — transformation over time (animate any property)
- `\k`, `\kf`, `\ko` — karaoke timing per character
- `\p` drawing mode — vector primitives within text
- `\clip`, `\iclip` — rectangular and vector clipping

### FFmpeg Integration
- `subtitles=filename.ass` filter
- `ass=filename.ass` filter (libass required)
- `ass` filter options: `fontsdir`, `alpha`, `shaping`, `original_size`
- Rendering quality vs `drawtext` — antialiasing, hinting, subpixel

### Workflow: Generate ASS from LLM
Design a template system where LLM generates ASS content:
```ass
[Script Info]
Title: Dynamic Lower Third
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: LowerThird,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.50,0:00:03.00,LowerThird,,0,0,0,,{\move(100,100,100,100,0,500)\fad(200,200)}Speaker Name
```

Research:
- ASS time format (centiseconds) vs FFmpeg time (seconds)
- Escaping special characters in ASS text
- Font embedding vs system font dependency
- Performance: ASS rendering vs multiple drawtext instances

---

## TASK 3 — Kinetic Typography Implementation

Define 10 kinetic typography patterns implementable via ASS or `drawtext`:

### Pattern 1: Word-by-Word Highlight
Each word appears/highlighted as spoken.
- Implementation: ASS with `\k` karaoke tags, or multiple `drawtext` with `enable='between(t,start,end)'`

### Pattern 2: Typewriter Effect
Characters appear sequentially.
- Implementation: ASS `\ko` (karaoke outline) or drawtext with `text` expansion and `n` frame counting

### Pattern 3: Scale Pop-In
Text scales from 0% to 100% with overshoot.
- Implementation: ASS `\t(\fscx100\fscy100)` with acceleration curve

### Pattern 4: Slide + Fade
Text slides from edge while fading in.
- Implementation: ASS `\move` + `\fad` or drawtext with `x='w-(w+text_w)*min(t/0.5,1)'`

### Pattern 5: Character Jitter/Glitch
Per-character random offset for "hand-made" or glitch effect.
- Implementation: Multiple ASS dialogue lines per character with random `\pos` offsets, or geq-generated displacement

### Pattern 6: 3D Rotation (Simulated)
Rotation around X or Y axis simulated with scale + skew.
- Implementation: ASS `\frx\fry` with `\t` animation

### Pattern 7: Text on Path
Text follows a curve (circle, wave).
- Implementation: **NOT POSSIBLE** in native FFmpeg — requires pre-rendered PNG sequence or external tool

### Pattern 8: Counter/Number Animation
Number increments from A to B over time.
- Implementation: `drawtext` with `%{eif\:...}` expression, or ASS with `\t` on `\pos` for vertical scroll

### Pattern 9: Multi-Line Stagger
Lines appear with 100ms stagger.
- Implementation: Multiple ASS dialogue lines with offset start times

### Pattern 10: Emphasis Shake
Text shakes to emphasize impact.
- Implementation: ASS `\pos` with `\t` and random or sinusoidal offsets

For each pattern, provide:
- Complete ASS code or drawtext command
- Parameter customization points (speed, amplitude, timing)
- Performance cost estimate

---

## TASK 4 — Dynamic Text Layout & Measurement

Research solutions for "text of unknown length":

### Problem: Centering Dynamic Text
`drawtext` has `x=(w-text_w)/2`, but `text_w` is only known at render time.

Solutions to research:
1. **FFmpeg 6.0+ `text_w`/`text_h` variables** — available in some contexts?
2. **Pre-measurement pass** — render to null, extract dimensions, re-render
3. **ASS with auto-sizing** — `\an` alignment handles positioning, but box size?
4. **Font metrics estimation** — pre-compute per-character widths for common fonts

### Problem: Multi-Line with Dynamic Wrapping
- ASS handles wrapping automatically with margins
- `drawtext` requires manual line breaking
- Hybrid: generate ASS from LLM with pre-computed line breaks

### Problem: Font Fallback for Missing Glyphs
- CJK characters when only Latin font specified
- Emoji rendering (color font support in libass?)
- Fontconfig substitution rules

---

## TASK 5 — Font Management System

Research font handling across platforms:

### Font Discovery
- `fc-list` (fontconfig) — Linux/macOS
- Windows Registry font enumeration
- FFmpeg `fontconfig` vs explicit `fontfile`

### Font Embedding
- Can FFmpeg embed fonts in output? (No, but can render to image)
- Pre-render text to PNG with transparent background via `drawtext` to `color=none`

### Recommended Font Stack
Define fallback chain for MCP:
1. Primary: Brand font (user-provided)
2. Secondary: System sans-serif (Arial, Helvetica, Noto Sans)
3. Fallback: Liberation Sans, DejaVu Sans (open metrics-compatible)

---

## TASK 6 — Text Animation Timing Functions

Document easing functions implementable in FFmpeg expressions:

| Easing | Formula | FFmpeg Expression |
|--------|---------|-----------------|
| Linear | t | t |
| Ease In Quad | t² | t*t |
| Ease Out Quad | t(2-t) | t*(2-t) |
| Ease In Out Quad | t<0.5 ? 2t² : -1+(4-2t)t | if(lt(t,0.5), 2*t*t, -1+(4-2*t)*t) |
| Ease Out Back | 1 + c3(t-1)³ + c1(t-1)² + c1 | 1 + 2.70158*pow(t-1,3) + 1.70158*pow(t-1,2) |
| Ease Out Elastic | 2^(-10t) * sin((t*10-0.75)(2π/3)) + 1 | pow(2,-10*t) * sin((t*10-0.75)*(2*PI/3)) + 1 |

Provide:
- General expression template for any easing
- ASS `\t` equivalent with acceleration parameter
- Performance comparison: expression vs ASS

---

## TASK 7 — MCP Text Tool Schema

Design JSON schema for text rendering tools:

```json
{
  "tool": "render_text",
  "parameters": {
    "text": "Speaker Name",
    "style": {
      "font": "Arial",
      "size": 48,
      "color": "#FFFFFF",
      "outline": {"color": "#000000", "width": 2},
      "shadow": {"color": "#00000080", "offset": [2, 2], "blur": 4}
    },
    "position": {"x": "center", "y": "bottom", "margin": 50},
    "animation": {
      "in": {"type": "slide", "direction": "up", "duration": 0.5, "easing": "ease_out_back"},
      "out": {"type": "fade", "duration": 0.3},
      "loop": null
    },
    "timing": {"start": 0.5, "duration": 3.0}
  }
}
```

Research: How to compile this to ASS or drawtext?

---

## Final Output Format

1. **`drawtext` complete reference** — all options, limitations, workarounds
2. **ASS engine specification** — features, FFmpeg integration, template system
3. **Kinetic typography library** — 10 patterns with code and parameters
4. **Dynamic layout solutions** — measurement, wrapping, fallback strategies
5. **Font management guide** — discovery, embedding, fallback chains
6. **Easing function reference** — expressions and ASS equivalents
7. **MCP tool schema** — JSON specification with compilation examples
