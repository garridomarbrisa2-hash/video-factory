# Research Prompt: FFmpeg Filter Validation Matrix — Production-Ready vs Experimental

## Role
You are a video quality assurance engineer tasked with validating every FFmpeg filter mentioned in the motion graphics catalog. The goal is to create a definitive matrix: which filters are production-ready for automated use, which require careful parameter tuning, and which are experimental/artifact-prone.

## Context
The MCP server will expose motion graphics recipes to an LLM. Each recipe must be:
- Reliable: produces predictable output across FFmpeg versions
- Performant: renders in reasonable time
- Quality-acceptable: no visible artifacts for broadcast use
- Parameter-safe: LLM cannot easily create invalid configurations

---

## TASK 1 — Filter Stability Classification

Classify each filter into tiers:

### Tier 1: Production-Ready (Rock Solid)
Filters that are:
- Stable across FFmpeg 5.x, 6.x, 7.x
- Well-documented with predictable behavior
- Performant on commodity hardware
- No known artifacts or edge cases

Candidates: `drawbox`, `drawtext`, `scale`, `crop`, `overlay`, `fade`, `xfade` (basic types), `format`, `fps`, `setpts`, `trim`, `concat`

Validation: Verify with test renders, document version differences

### Tier 2: Production-Ready with Constraints
Filters that work well but require:
- Specific parameter ranges to avoid artifacts
- Performance considerations (may need reduced resolution)
- Careful combination with other filters
- Version-specific behavior

Candidates: `zoompan`, `minterpolate`, `geq`, `perspective`, `displace`, `lenscorrection`, `tblend`, `tmix`, `edgedetect`, `vignette`, `curves`, `lut3d`, `chromakey`, `colorkey`, `alphamerge`, `premultiply`, `unpremultiply`, `maskedmerge`

Validation: Define safe parameter ranges, document artifacts, provide fallback

### Tier 3: Experimental / Use with Caution
Filters that are:
- New or recently changed
- Known to have bugs or artifacts
- Performance-prohibitive for real-time use
- Poorly documented or unpredictable

Candidates: `v360`, `remap`, `tiltandshift`, `feedback`, `lagfun`, `life`, `cellauto`, `mandelbrot`, `sierpinski`, `zoneplate`, `gradients`, `perlin`, `qrencode`, `datascope`, `signalstats`, `find_rect`, `cover_rect`, `backgroundkey`

Validation: Extensive testing required, mark as "beta" in MCP

### Tier 4: Not Recommended for Automation
Filters that are:
- Deprecated or removed in recent versions
- Known security issues (buffer overflows, etc.)
- Non-deterministic output
- Require external files that may not exist

Candidates: Any filter requiring external LUT files, `frei0r` plugins (build-dependent), `opencv` filters (build-dependent)

---

## TASK 2 — Per-Filter Validation Protocol

For each filter in Tiers 1-3, document:

### Basic Functionality Test
- Minimal working command with all defaults
- Expected output description
- Common failure modes

### Parameter Validation
| Parameter | Type | Min | Max | Safe Range | Danger Zone | Artifact Risk |
|-----------|------|-----|-----|------------|-------------|---------------|
| `zoompan:z` | expr | 0 | 10 | 1.0-3.0 | >5.0 | Extreme pixelation |
| `minterpolate:mi_mode` | enum | - | - | mci, blend | dup | mci=artifacts, dup=judder |

### Performance Benchmark
- Render time for 10s 1080p30 with default settings
- Memory usage
- GPU acceleration available? (cuda, qsv, videotoolbox)
- Multithreading support?

### Artifact Documentation
- Description of visual artifacts at extremes
- Parameter combinations that cause problems
- Mitigation strategies

### Combination Compatibility
- Filters that MUST precede this filter
- Filters that MUST follow this filter
- Filters that conflict or produce undefined behavior

---

## TASK 3 — High-Priority Filter Deep Dives

### `zoompan` — Ken Burns Effect
**Status**: Tier 2 (jitter issues)

Research:
- Sub-pixel movement causes jitter: `z='1+0.001*n'` vs `z='1+0.01*n'`
- `s` parameter (output size) interaction with scale filter
- `d` parameter (duration in frames) vs `fps` setting
- Recommended alternative: `scale` + `crop` with animated expressions

Deliverable: Safe parameter ranges, jitter-free recipes

### `minterpolate` — Motion Interpolation
**Status**: Tier 2 (artifact-prone)

Research:
- `mi_mode=mci` (motion-compensated) vs `mi_mode=blend`
- `mc_mode` and `me_mode` tuning for different content
- Scene change detection: `scd` parameter
- When is it acceptable? (Slow motion of smooth motion, NOT for fast action)

Deliverable: Content-type decision tree, artifact examples

### `geq` — Generic Equation
**Status**: Tier 2 (performance, complexity)

Research:
- Expression complexity limits (parse time, evaluation time)
- Performance at 1080p, 4K — is real-time possible?
- Common patterns: gradients, shapes, noise
- Debugging: how to visualize what geq is generating

Deliverable: Recipe library with performance ratings, complexity limits

### `xfade` — Transitions
**Status**: Tier 1 for basic, Tier 2 for complex

Research:
- All 40+ transition types: which are broadcast-quality vs gimmicky?
- Offset/duration math for precise timing
- Audio synchronization with `acrossfade`
- Performance: single-pass vs two-pass

Deliverable: Transition catalog with quality ratings

### `perspective` — Corner Pinning
**Status**: Tier 2 (coordinate confusion)

Research:
- Coordinate system: source vs destination corners
- Sub-pixel precision and anti-aliasing
- Combination with `scale` and `pad` for screen replacement
- Interactive corner specification — can LLM compute correct values?

Deliverable: Coordinate calculation guide, screen replacement recipe

### `displace` — Displacement Mapping
**Status**: Tier 2 (requires displacement map)

Research:
- Displacement map generation (geq, external)
- Scale parameter: how much displacement per pixel value?
- Edge behavior: smearing, wrapping
- Performance: much slower than static transforms

Deliverable: Displacement map generation recipes, use case catalog

---

## TASK 4 — Filter Combination Validation

Test and document common combinations:

### Text + Background
`drawtext` with `box=1` vs separate `drawbox` + `drawtext`
- Which is more flexible for animation?
- Which performs better?

### Multiple Overlays
`overlay` chained 5+ times vs `xstack` vs `tile`
- Performance comparison
- Alpha handling differences
- Memory usage

### Color Chain
`curves` + `colorbalance` + `lut3d` vs single `lut3d`
- Quality comparison
- Performance comparison
- When to use each approach

### Scale + Rotate + Perspective
Order matters: `scale` → `rotate` → `perspective` vs reverse
- Quality differences (intermediate scaling losses)
- Performance differences

---

## TASK 5 — Version Compatibility Matrix

Document behavior changes across FFmpeg versions:

| Filter | FFmpeg 4.4 | FFmpeg 5.1 | FFmpeg 6.0 | FFmpeg 7.0 | Notes |
|--------|-----------|-----------|-----------|-----------|-------|
| `drawtext` | baseline | +`boxw`, `boxh` | +`line_spacing` | +`text_align` | Font rendering improved |
| `xfade` | 30 transitions | +5 transitions | +`circleopen` | +`radial` | All stable |
| `geq` | baseline | +`interp` | +`a` alpha expr | +`rect` | More variables |
| `minterpolate` | baseline | +`scd` | +`mi_mode=blend` | Performance | Major improvements |

Research: How to detect FFmpeg version at runtime and adapt?

---

## TASK 6 — MCP Filter Exposure Strategy

Based on validation, design exposure tiers:

### Fully Exposed (LLM can use freely)
- `drawbox`, `drawtext`, `scale`, `crop`, `overlay`, `fade`, `format`, `fps`, `setpts`, `trim`, `concat`, `xfade` (10 basic types)

### Constrained Exposure (LLM uses with validated parameters)
- `zoompan`: only with pre-validated recipes
- `minterpolate`: only for slow-motion, with content detection
- `geq`: only with pre-built recipes, no free-form expressions
- `perspective`: only with computed corner coordinates
- `tblend`, `tmix`: only with frame count limits

### Recipe-Only Exposure (LLM selects recipe, no parameter access)
- `displace`: only with pre-built displacement maps
- `lenscorrection`: only with preset k1/k2 values
- `v360`: only for specific projection conversions

### Not Exposed (Internal use only)
- `remap`, `feedback`, `life`, `cellauto`, `mandelbrot`, `sierpinski`

---

## Final Output Format

1. **Tier classification** — all filters with justification
2. **Per-filter validation sheets** — parameters, performance, artifacts, compatibility
3. **High-priority deep dives** — zoompan, minterpolate, geq, xfade, perspective, displace
4. **Combination validation** — tested chains with recommendations
5. **Version compatibility matrix** — behavior changes across FFmpeg versions
6. **MCP exposure strategy** — tiered access with safety constraints
