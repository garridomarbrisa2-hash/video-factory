# Research Prompt: MCP Interface Contract & Tool Schema Design

## Role
You are an API architect designing the Model Context Protocol (MCP) interface for FFmpeg video automation. The goal is to define a clean, composable, LLM-friendly tool schema that abstracts FFmpeg complexity while preserving full creative control.

## Context
The MCP server must:
- Accept high-level creative intent ("add a lower third with speaker name")
- Compile to precise FFmpeg commands
- Support composition (multiple tools combine into one video)
- Provide feedback for LLM learning (what worked, what failed)
- Handle both simple one-off renders and complex multi-scene projects

---

## TASK 1 — Tool Granularity Analysis

Compare three granularity levels:

### Level 1: Atomic Filters (Too Low)
Tools: `draw_box`, `draw_text`, `overlay`, `scale`, `crop`

Pros: Maximum flexibility
Cons: LLM must understand FFmpeg deeply; composition is verbose; error-prone

### Level 2: Motion Graphics Recipes (Recommended)
Tools: `lower_third`, `kinetic_title`, `split_screen`, `data_counter`, `highlight_box`

Pros: LLM-friendly naming; encapsulates complexity; validated parameters
Cons: Less flexible for novel effects; more tools to maintain

### Level 3: Scene Templates (Too High)
Tools: `intro_sequence`, `product_showcase`, `testimonial_segment`

Pros: Extremely fast for common patterns
Cons: Inflexible; hard to customize; combinatorial explosion

Research: Which level do successful MCP servers use? (GitHub, Slack, etc.)

---

## TASK 2 — Core Tool Set Definition

Define the minimum viable tool set:

### Asset Management
- `upload_asset` — Register video/image/audio with metadata
- `analyze_asset` — Get duration, resolution, color space, loudness
- `normalize_asset` — Convert to standard format

### Composition
- `create_timeline` — Initialize project with fps, resolution, duration
- `add_scene` — Add segment with video source, audio source, timing
- `add_overlay` — Attach motion graphic to scene
- `add_transition` — Define in/out transitions for scene
- `render_preview` — Render low-res proxy for review
- `render_final` — Render full quality with all QC

### Motion Graphics (Recipe Level)
- `lower_third` — Name/title bar with animated entry/exit
- `kinetic_text` — Animated text with multiple style options
- `highlight_annotation` — Circle/box/arrow on region of interest
- `split_screen` — Side-by-side comparison with animated divider
- `data_visualization` — Counter, bar, progress, chart
- `transition_effect` — Wipe, fade, glitch, zoom between scenes
- `pip_window` — Picture-in-picture with border/shadow
- `gallery_grid` — Multi-item grid layout

### Audio
- `mix_audio` — Combine voice, music, SFX with levels and ducking
- `normalize_loudness` — Target LUFS with true peak limiting
- `trim_silence` — Auto-remove silence from voiceover

---

## TASK 3 — Tool Schema Specification

Design JSON schemas for each tool:

### Example: `lower_third`

```json
{
  "name": "lower_third",
  "description": "Add an animated lower third with name and optional title",
  "parameters": {
    "type": "object",
    "properties": {
      "scene_id": {"type": "string", "description": "Target scene"},
      "text": {"type": "string", "description": "Primary text (name)"},
      "subtext": {"type": "string", "description": "Secondary text (title/role)"},
      "style": {
        "type": "object",
        "properties": {
          "font": {"type": "string", "default": "Arial"},
          "font_size": {"type": "integer", "default": 48},
          "color": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"},
          "background_color": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}[0-9A-Fa-f]{2}$"},
          "bar_height": {"type": "integer", "default": 80}
        }
      },
      "position": {
        "type": "string",
        "enum": ["bottom_left", "bottom_center", "bottom_right", "top_left", "top_center", "top_right"]
      },
      "animation": {
        "type": "object",
        "properties": {
          "in_type": {"enum": ["slide_up", "slide_left", "fade", "scale_pop"]},
          "in_duration": {"type": "number", "default": 0.5},
          "out_type": {"enum": ["slide_down", "slide_right", "fade", "scale_shrink"]},
          "out_duration": {"type": "number", "default": 0.3},
          "hold_duration": {"type": "number", "default": 3.0}
        }
      },
      "timing": {
        "type": "object",
        "properties": {
          "start": {"type": "number", "description": "Start time in scene"},
          "duration": {"type": "number", "description": "Total display time"}
        }
      }
    },
    "required": ["scene_id", "text", "timing"]
  }
}
```

Research:
- How to represent "either X or Y" (mutually exclusive parameters)?
- How to represent conditional requirements (if animation.in_type = "custom", require custom_expression)?
- How to represent arrays of varying length (multiple text lines)?

---

## TASK 4 — Composition Model

Design how tools combine:

### Stateless Model (Recommended for Simplicity)
Each tool call is independent; server maintains timeline state.

```
LLM: create_timeline(fps=30, resolution="1920x1080")
LLM: add_scene(scene_id="s1", source="broll.mp4", start=0, duration=7)
LLM: lower_third(scene_id="s1", text="Speaker", timing={start: 1, duration: 3})
LLM: render_final(output="final.mp4")
```

### Stateful Model
Tools return handles for further manipulation.

```
LLM: timeline = create_timeline(...)
LLM: scene = timeline.add_scene(...)
LLM: lt = scene.add_lower_third(...)
LLM: lt.set_style(color="#FF0000")
LLM: timeline.render()
```

### Declarative Model
LLM describes full video; server compiles and renders.

```
LLM: render_video({
  "timeline": {
    "scenes": [...],
    "overlays": [...],
    "transitions": [...]
  }
})
```

Research: Tradeoffs of each model for LLM usability, error recovery, partial rendering.

---

## TASK 5 — Response Schema Design

Design success and error responses:

### Success Response
```json
{
  "status": "success",
  "data": {
    "asset_id": "asset_abc123",
    "duration": 7.5,
    "resolution": [1920, 1080],
    "preview_url": "/previews/abc123.jpg",
    "qc": {
      "loudness_lufs": -23.1,
      "true_peak_dbtp": -2.1,
      "black_frames": 0
    }
  },
  "metadata": {
    "render_time_ms": 12500,
    "ffmpeg_version": "6.0",
    "warnings": []
  }
}
```

### Error Response
```json
{
  "status": "error",
  "error": {
    "code": "ASSET_NOT_FOUND",
    "message": "Asset 'broll.mp4' not found in registry",
    "suggestion": "Upload asset first with upload_asset, or use analyze_asset to verify path",
    "retry_possible": false
  }
}
```

### Partial Success
```json
{
  "status": "partial",
  "completed": ["scene_1", "scene_2"],
  "failed": [{"scene": "scene_3", "error": "..."}],
  "next_steps": ["Retry scene_3 with simpler effects", "Check asset integrity"]
}
```

---

## TASK 6 — LLM Prompt Engineering for Tool Use

Design system prompts and examples:

### System Prompt Template
```
You are a video editor AI using FFmpeg MCP tools.

Available tools:
{tool_definitions}

Rules:
1. Always analyze assets before use (duration, resolution, format)
2. Validate timing: overlays must fit within scene duration
3. Check audio: voiceover duration determines scene length
4. Use genre-appropriate motion graphics density
5. Preview before final render when possible

Current project state:
{timeline_state}
```

### Few-Shot Examples
Provide 5-10 complete examples of:
- Simple talking head video
- Product comparison video
- Tutorial with highlights
- Listicle with transitions
- Data-driven explainer

---

## TASK 7 — Extensibility & Versioning

Design for future growth:

### Tool Versioning
- Schema version in each tool call
- Server supports multiple versions during migration
- Deprecation warnings for old schemas

### Custom Tool Registration
- Allow users to define custom motion graphics (Jinja2 templates?)
- Sandbox validation of custom tools
- Sharing/monetization of community tools

### Plugin Architecture
- Core: FFmpeg compilation and execution
- Plugin: Additional analysis (face detection, scene detection)
- Plugin: External renderers (Lottie, SVG, 3D)

---

## Final Output Format

1. **Granularity recommendation** — analysis and justification
2. **Core tool set** — 15-20 essential tools with full schemas
3. **Composition model** — stateless vs stateful vs declarative with examples
4. **Response schemas** — success, error, partial with all fields
5. **LLM prompt templates** — system prompt, few-shot examples
6. **Extensibility design** — versioning, custom tools, plugins
