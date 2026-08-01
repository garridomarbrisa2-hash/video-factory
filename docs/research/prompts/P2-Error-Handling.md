# Research Prompt: Error Handling, Validation & Debugging for FFmpeg Automation

## Role
You are a reliability engineer designing fault-tolerant video processing systems. The goal is to define error handling, validation, and debugging strategies for an FFmpeg MCP server that processes untrusted LLM-generated commands and diverse input assets.

## Context
Failure modes to handle:
- LLM generates syntactically invalid filter_complex
- LLM generates semantically invalid commands (referencing non-existent inputs)
- Input assets are corrupted, wrong format, or missing
- FFmpeg crashes or hangs on specific inputs
- Output fails QC (black frames, wrong duration, loudness out of spec)
- Resource exhaustion (memory, disk, GPU)

---

## TASK 1 — Input Validation Layer

Design validation before any FFmpeg execution:

### Asset Validation
- File existence and readability
- File size sanity (not 0 bytes, not >10GB)
- Magic number verification (actual format vs extension)
- `ffprobe` validation: decodable, has video/audio streams, duration >0
- Resolution/fps/codec allowlist

### Command Validation
- Syntax checking: balanced brackets, valid filter names, quoted strings
- Semantic checking: input/output label consistency, filter exists in FFmpeg build
- Parameter validation: ranges, enums, expression syntax
- Security validation: no shell injection, no file system escape, no network access

### Expression Validation
- Parse expressions with FFmpeg's expression evaluator (dry-run)
- Check for undefined variables
- Validate function names and arity
- Detect division by zero, log of negative, etc.

---

## TASK 2 — Dry-Run & Sandboxed Validation

Research validation without full render:

### Syntax Validation
- `ffmpeg -h filter=drawtext` — verify filter exists and get options
- `ffmpeg -filters` — list all available filters in build
- `ffmpeg -formats`, `ffmpeg -codecs` — verify format/codec support

### Graph Validation
- `ffmpeg -f lavfi -i "nullsrc=s=1920x1080" -filter_complex_script graph.txt -f null -` — validate graph without encoding
- `ffmpeg -v verbose` — parse filter graph construction messages

### Frame Sampling Validation
- Render 1 frame from start, middle, end — verify no crashes
- Compare frame count to expected duration

---

## TASK 3 — Error Detection & Classification

Design error taxonomy:

### FFmpeg Exit Codes
- 0: Success
- 1: Generic error
- 251: Conversion failed (FFmpeg specific)

### stderr Pattern Matching
| Pattern | Error Type | Recovery Action |
|---------|-----------|-----------------|
| `No such filter` | Invalid filter name | Suggest similar filter, check FFmpeg version |
| `Invalid argument` | Parameter out of range | Clamp to valid range, retry |
| `Cannot find a matching stream` | Label mismatch in filter_complex | Rebuild graph with correct labels |
| `Conversion failed` | Generic | Capture full log, escalate |
| `Device or resource busy` | Resource conflict | Retry with backoff |
| `Output file is empty` | Encoding produced nothing | Check input validity, retry with simpler settings |
| `moov atom not found` | Corrupted MP4 input | Attempt repair with `-movflags +faststart` or re-encode |

### Hang Detection
- No progress for >30 seconds
- Memory usage grows unboundedly
- CPU usage drops to 0

Recovery: kill process, retry with `-timeout` option or simpler pipeline

---

## TASK 4 — Output Quality Validation

Define automated QC checks:

### Video QC
- Duration matches expected (±0.1s)
- Resolution matches target
- Frame count = duration × fps (±1 frame)
- No black frames >1 second (configurable threshold)
- No frozen frames >2 seconds (except intentional stills)
- Signal statistics within range (luma, chroma, saturation)

### Audio QC
- Duration matches video
- Loudness within target (±0.5 LUFS)
- True peak below -1 dBTP
- No clipping (samples at 0dBFS = 0)
- No silence >5 seconds (except intentional pauses)

### Implementation
- `ffprobe -v quiet -print_format json -show_format -show_streams`
- `ffmpeg -i output.mp4 -vf "blackdetect,freezedetect,signalstats" -af "silencedetect,ebur128" -f null -`

---

## TASK 5 — Retry & Recovery Strategies

Design fault tolerance:

### Retry Logic
| Failure Type | Retry Strategy | Max Retries |
|-------------|---------------|-------------|
| Transient (network, resource) | Immediate retry with exponential backoff | 3 |
| Invalid parameter | Auto-correct parameter, retry | 1 |
| Corrupted input | Attempt repair, else fail | 1 |
| Hang/crash | Simplify pipeline, retry | 2 |

### Fallback Pipeline
If full quality render fails:
1. Retry with hardware acceleration disabled
2. Retry with simpler filter graph (remove optional effects)
3. Retry with software encoding, faster preset
4. Render at lower resolution, upscale after
5. Render without audio, mux separately

### Partial Result Preservation
- Save intermediate renders before final assembly
- Cache scene renders for reuse in similar videos
- Preserve logs and failed outputs for debugging

---

## TASK 6 — Logging & Observability

Design logging for debugging and audit:

### Log Levels
- DEBUG: Full FFmpeg stderr, filter graph dumps, expression evaluations
- INFO: Command executed, input/output specs, timing, QC results
- WARN: Non-fatal issues (retries, fallbacks, QC warnings)
- ERROR: Fatal failures, invalid inputs, resource exhaustion

### Structured Logging Format
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "job_id": "video_12345",
  "stage": "scene_3_render",
  "ffmpeg_command": "ffmpeg -i ...",
  "input_assets": ["broll1.mp4", "vo1.mp3"],
  "output": "scene_3.mp4",
  "duration_ms": 4500,
  "exit_code": 0,
  "qc_results": {
    "duration": 4.52,
    "resolution": "1920x1080",
    "loudness_lufs": -23.1,
    "true_peak_dbtp": -2.3
  }
}
```

### Debug Mode
- Dump filter_complex to file
- Save intermediate frames as PNG
- Generate waveform/spectrogram of audio
- Create side-by-side comparison of input/output

---

## TASK 7 — MCP Error Response Schema

Design error reporting to LLM:

```json
{
  "status": "error",
  "error": {
    "code": "INVALID_FILTER",
    "message": "Filter 'drawtext2' not found. Did you mean 'drawtext'?",
    "stage": "validation",
    "suggestion": {
      "action": "replace_filter",
      "from": "drawtext2",
      "to": "drawtext"
    },
    "retry_possible": true,
    "fallback_available": true
  },
  "partial_results": [
    {"scene": 1, "status": "completed", "path": "/tmp/scene1.mp4"},
    {"scene": 2, "status": "failed", "error": "..."}
  ]
}
```

Research: How much detail to expose to LLM vs internal logging?

---

## Final Output Format

1. **Input validation specification** — asset checks, command checks, expression checks
2. **Dry-run validation pipeline** — syntax, graph, sampling validation
3. **Error taxonomy** — patterns, classification, recovery actions
4. **QC automation** — video/audio checks with thresholds
5. **Retry & recovery architecture** — strategies, fallbacks, preservation
6. **Logging & observability** — levels, formats, debug tools
7. **MCP error schema** — structured error responses with suggestions
