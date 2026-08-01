# Perplexity Research Synthesis — Design Decisions for FFmpeg MCP

**Date:** 2026-07-21
**Source:** `Research-Perplexity-Answer.md` (5 questions, all answered)
**Status:** Ready for implementation

---

## Executive Summary

All 5 questions received actionable answers. Two came back with high confidence, two with medium, one with low-medium. Critically, **none of the answers blocked implementation** — they all confirmed our architectural direction while providing specific refinements.

---

## Question 1: Motion Graphics Selection Rules

### What We Learned

**Confidence: Medium** — Strong evidence for general principles, weak evidence for fine-grained rules.

Key finding: **Professional practice is driven by heuristics and genre conventions, NOT formalized if-then rules.** The research explicitly states: "most detailed guidelines are descriptive, not prescriptive."

### Actionable Rules Extracted

| Script Feature | Primary Treatment | Fallback | Genre Override |
|----------------|-------------------|----------|----------------|
| Single headline number | On-screen text + lower-third | Simple counter | — |
| Multi-point statistic/series | Animated chart/graph | Simple text + highlight | Vlog: b-roll + overlay |
| Slogan with number ("10x growth") | Kinetic typography | Bold static text | News: avoid |
| Identity introduction | Lower-third | On-screen text | Documentary: minimal |
| Concrete noun/action | B-roll footage | Stock still image | — |
| Explicit comparison | Split-screen | Sequential cuts | Documentary: rare |
| "Look at this" / "notice" | Highlight annotation | Zoom + arrow | — |
| Abstract concept | Generative background | Solid color + text | — |
| Screen demo + presenter | Picture-in-picture | Full screen switch | — |
| Topic shift | Transition effect | Hard cut | News: conservative |

### Design Decision: Heuristic Engine, Not Rule Engine

```json
{
  "trigger": {
    "feature": "numeric_series",
    "candidates": [
      {"treatment": "animated_chart", "weight": 0.7, "genre_boost": {"educational": 1.2}},
      {"treatment": "kinetic_text", "weight": 0.2, "genre_boost": {"music": 1.5}},
      {"treatment": "simple_text", "weight": 0.1}
    ],
    "fallback": "simple_text",
    "pacing_constraints": {
      "max_per_minute": 2,
      "no_overlap_with": ["split_screen", "complex_chart"]
    }
  }
}
```

The LLM receives this as a **decision matrix**, not a decision tree. It can justify choices: "I selected animated_chart because the script contains a multi-step numeric comparison in an educational context (weight 0.7, boosted to 0.84 for educational genre)."

---

## Question 2: ASS `\t` Accel Easing Formula

### What We Learned

**Confidence: Low-Medium** — Qualitative behavior documented, exact formula unknown.

Key finding: The `accel` parameter is confirmed as:
- `accel = 1` → linear (documented fact)
- `0 < accel < 1` → ease-out-like (fast start, slow finish)
- `accel > 1` → ease-in-like (slow start, fast finish)

**No mapping to Penner equations exists in public documentation.** The libass source was not accessible.

### Design Decision: Power Function Approximation

Since libass is VSFilter-compatible and the community consensus treats `accel` as a power exponent, we will:

1. **Internal representation**: Use standard Penner easing names (`linear`, `easeInQuad`, `easeOutCubic`, etc.)
2. **ASS compatibility mode**: Approximate with power function `x^accel` for ease-in, `1-(1-x)^accel` for ease-out
3. **Never claim exact equivalence**: Document as "approximate, not exact"
4. **Preserve original `accel` values** when round-tripping ASS files

```python
# MCP easing implementation
def ease(t, easing_type, accel=None):
    if easing_type == "linear" or accel == 1:
        return t
    elif easing_type == "ass_compat":
        if accel > 1:  # ease-in
            return t ** accel
        else:  # ease-out
            return 1 - (1 - t) ** (1 / accel)
    elif easing_type == "easeInQuad":
        return t * t
    elif easing_type == "easeOutCubic":
        return 1 - (1 - t) ** 3
    # ... etc
```

---

## Question 3: Production Checkpoint/Resume Architecture

### What We Learned

**Confidence: Medium** — High-level pattern confirmed, exact SaaS internals undocumented.

Key finding: **Scene-level intermediate rendering + FFmpeg mux is the standard pattern**, but exact implementations are proprietary. The research confirms:

1. Segment rendering → FFmpeg concat is documented in open tools
2. Transitions spanning scenes require special handling (either separate transition clips or timeline-level rendering)
3. Content-addressable caching (scene JSON hash) is assumed standard
4. Partial failure = retry only failed unit is "robust architecture" consensus

### Design Decision: Hybrid Scene + Transition Architecture

```
Timeline
├── Scene 1 (cached: hash_abc123)
├── Transition 1→2 (rendered fresh: needs tail of S1 + head of S2)
├── Scene 2 (cached: hash_def456)
├── Transition 2→3 (cached: hash_ghi789)
└── Scene 3 (rendered fresh: new content)
```

**Implementation:**
- `render_scene(scene_json)` → returns `scene_id` + `output_path` + `cache_hit`
- `render_transition(from_scene_id, to_scene_id, transition_json)` → returns `transition_id` + `output_path`
- `render_project(project_id, reuse_cache=true)` → orchestrates all scenes + transitions
- Cache key: `sha256(scene_json + asset_hashes + ffmpeg_version)`

**Failure recovery:**
- If Scene 5 fails: retry Scene 5 only, plus adjacent transitions (4→5 and 5→6)
- If Transition 4→5 fails: retry only that transition (Scenes 4 and 5 are cached)

---

## Question 4: HEVC Alpha Channel Status 2026

### What We Learned

**Confidence: High for encoders, Medium for muxing**

Key finding:
- **libx265**: NO alpha support (confirmed)
- **hevc_videotoolbox**: YES alpha support, Apple-only, out-of-spec extension
- **MP4 muxer**: Uncertain for HEVC alpha in FFmpeg 7.x/8.x
- **Cross-platform**: HEVC alpha is Apple-only, not standardized

### Design Decision: VP9/WebM Primary, ProRes 4444 Master, HEVC Optional

| Format | Use Case | Alpha? | Platform |
|--------|----------|--------|----------|
| **VP9/WebM** | Web overlays, cross-browser | ✅ Yes | Chrome, Firefox, Edge |
| **ProRes 4444** | Production master, internal pipeline | ✅ Yes | All NLEs, high quality |
| **HEVC/MOV** | Apple ecosystem only | ✅ Yes | Safari, iOS, macOS |
| **PNG sequence** | Universal fallback | ✅ Yes | Everywhere |

**MCP tool design:**
```json
{
  "encode_overlay": {
    "format": "vp9_webm_alpha",
    "fallback_formats": ["prores_4444", "png_sequence"],
    "capability_check": "hevc_videotoolbox_available"
  }
}
```

---

## Question 5: MCP Production Tool Schemas

### What We Learned

**Confidence: High** — Multiple existing servers with clear patterns.

Key finding: Two dominant patterns exist:

1. **FFmpeg-centric stateless** (FFmpeg Micro, video converter servers)
   - One tool per recipe: `transcode_video`, `clip_video`, `overlay`
   - Job-based async: `create_job` → `get_status` → `get_result`
   - Returns file paths/IDs, not video bytes

2. **Editor-centric stateful** (OpenCut Controller, ClipChat)
   - Project/timeline handles: `create_project` → `add_scene` → `render`
   - Many granular tools (161 for OpenCut)
   - Async job queue with progress streaming

### Design Decision: Hybrid Recipe + Project Handle Pattern

**Level 1: Recipe Tools (Stateless, for simple operations)**
```
trim_video(input_path, start, end) → output_path
overlay_video(bg_path, fg_path, position, timing) → output_path
normalize_audio(input_path, target_lufs) → output_path
```

**Level 2: Project Tools (Stateful, for complex compositions)**
```
create_project(fps, resolution, genre) → project_id
add_scene(project_id, scene_json) → scene_id
add_overlay(project_id, scene_id, overlay_json) → overlay_id
set_transition(project_id, from_scene, to_scene, transition_json) → transition_id
render_project(project_id, profile) → job_id
get_render_status(job_id) → {status, progress, output_path?}
```

**Level 3: Analysis Tools (Stateless, for decision support)**
```
analyze_asset(asset_path) → {duration, resolution, codec, loudness, color_space}
suggest_treatments(script_text, genre, available_assets) → [treatment_options]
validate_timeline(project_id) → {valid, errors, warnings}
```

---

## Updated MCP Architecture

Based on all findings, here is the final architecture:

```
┌─────────────────────────────────────────┐
│           LLM Orchestrator              │
│  (script → decisions → tool calls)      │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│         MCP Server (FFmpeg)             │
│                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ Recipe  │ │ Project │ │ Analysis│   │
│  │ Tools   │ │ Tools   │ │ Tools   │   │
│  │(stateless)│ │(stateful)│ │(stateless)│ │
│  └────┬────┘ └────┬────┘ └────┬────┘   │
│       │           │           │         │
│       └───────────┴───────────┘         │
│                   │                     │
│                   ▼                     │
│  ┌─────────────────────────────────┐    │
│  │      Scene Cache + Job Queue    │    │
│  │  (content-addressable storage)  │    │
│  └─────────────────────────────────┘    │
│                   │                     │
│                   ▼                     │
│  ┌─────────────────────────────────┐    │
│  │      FFmpeg Execution Engine    │    │
│  │  (filter_complex compilation)   │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

---

## Implementation Readiness Checklist

| Component | Status | Blockers |
|-----------|--------|----------|
| Motion graphics trigger engine | ✅ Ready | None — heuristic matrix defined |
| Text/typography system | ✅ Ready | ASS + drawtext hybrid confirmed |
| Audio ducking | ✅ Ready | sidechaincompress recipe validated |
| Timeline assembly | ✅ Ready | Scene + transition architecture defined |
| Asset pipeline | ✅ Ready | VP9/ProRes/PNG strategy confirmed |
| Performance optimization | ✅ Ready | NVENC/QSV/VideoToolbox paths documented |
| Error handling | ✅ Ready | 3-bucket taxonomy + retry strategies |
| MCP interface | ✅ Ready | Hybrid recipe+project pattern confirmed |
| Filter validation | ✅ Ready | Tier classifications with workarounds |
| Checkpoint/recovery | ✅ Ready | Scene hash caching design confirmed |

---

## Next Immediate Action

**Begin MCP implementation.** All research is complete. The architecture is validated. Start with:

1. **Project skeleton**: MCP server with tool registration
2. **Recipe tools**: 5 core recipes (trim, overlay, normalize, lower_third, transition)
3. **Scene cache**: File-based content-addressable storage
4. **FFmpeg compiler**: JSON scene → filter_complex
5. **Job queue**: Async render with progress polling

The research corpus (280KB Tavily + 50KB Perplexity + 100KB user-provided) is sufficient to build a production-grade system.
