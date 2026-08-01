# Research Prompt: Asset Pipeline Specification for Video Automation

## Role
You are a digital asset management (DAM) architect and FFmpeg format expert. The goal is to define a complete asset pipeline for the video automation factory: how images, videos, audio, and generated content flow from source to final composition with correct color, timing, and quality.

## Context
Assets come from:
- User uploads (various formats, qualities, color spaces)
- Stock sites (Pexels, Pixabay, Unsplash — different licenses, formats)
- AI generation (DALL-E, Midjourney, Stable Diffusion — PNG/JPG, various sizes)
- TTS engines (MP3, WAV, various sample rates)
- Internal generation (FFmpeg `geq`, `nullsrc`, `testsrc`)

All must normalize to a consistent internal format for reliable composition.

---

## TASK 1 — Input Format Compatibility Matrix

Document every asset type FFmpeg can ingest:

### Video Codecs
| Codec | Container | Alpha? | HDR? | Notes |
|-------|-----------|--------|------|-------|
| H.264 | MP4, MKV, MOV | No | No (8-bit) | Universal, fast decode |
| HEVC | MP4, MKV, MOV | No | Yes (10-bit) | Licensing, slower |
| VP9 | WebM, MKV | Yes (alpha) | Yes | Web standard |
| AV1 | MP4, MKV, WebM | Yes (alpha) | Yes | Slow decode, future |
| ProRes | MOV | Yes (4444) | Yes | Large files, fast decode |
| DNxHD | MXF, MOV | No | No | Broadcast standard |
| FFV1 | MKV | Yes | Yes | Lossless, huge files |
| Hap | MOV | Yes | No | GPU decode, fast |

### Image Formats
| Format | Alpha? | Bit Depth | Color Space | Notes |
|--------|--------|-----------|-------------|-------|
| PNG | Yes | 8/16 | RGB/RGBA | Best for graphics |
| JPEG | No | 8 | YCbCr | Photos only |
| WebP | Yes | 8 | RGB/RGBA | Good compression |
| TIFF | Yes | 8/16 | RGB/CMYK | Print legacy |
| EXR | Yes | 16/32 float | Linear | HDR/VFX |
| SVG | N/A | Vector | N/A | Not supported by FFmpeg |

### Audio Formats
| Format | Sample Rates | Bit Depth | Channels | Notes |
|--------|-------------|-----------|----------|-------|
| WAV | All | 16/24/32 | All | Uncompressed, large |
| MP3 | 8-48kHz | 16 | Stereo | Lossy, universal |
| AAC | All | 16 | All | Best lossy quality |
| FLAC | All | 16/24 | All | Lossless, large |
| Opus | 8-48kHz | 16 | All | Best for speech |

---

## TASK 2 — Normalization Pipeline Design

Define standard internal formats:

### Video Normalization Target
- Codec: H.264 (compatibility) or FFV1 (quality preservation)
- Resolution: 1920x1080 (or 3840x2160 for 4K pipeline)
- FPS: 30 (or match source, conformed)
- Color: BT.709 SDR, 8-bit YUV420p
- Pixel format: yuv420p (compatibility) or yuv444p (quality)

Research:
- `scale`, `fps`, `format`, `colormatrix` filter chain for normalization
- Handling of anamorphic/non-square pixels (`setsar`, `setdar`)
- Rotation metadata (iPhone videos) — autorotation vs manual

### Image Normalization Target
- Format: PNG with alpha
- Size: Match video resolution or power-of-2 for GPU
- Color: sRGB, straight alpha (not premultiplied)

Research:
- `format=rgba`, `premultiply`/`unpremultiply` for alpha handling
- DPI/resolution metadata — ignored by FFmpeg?
- Color profile stripping (`-color_primaries`, `-color_trc`)

### Audio Normalization Target
- Format: WAV or AAC
- Sample rate: 48000 Hz
- Channels: Stereo (or mono for voiceover)
- Bit depth: 16-bit (AAC) or 24-bit (WAV)

Research:
- `aresample`, `aformat` filter chain
- Loudness normalization during ingest (loudnorm to -23 LUFS?)

---

## TASK 3 — Color Management Deep Dive

Research color space handling to prevent shifts:

### Source Color Spaces
- BT.601 (SD legacy)
- BT.709 (HD standard)
- BT.2020 (UHD/HDR)
- sRGB (computer graphics)
- Linear (VFX/EXR)

### FFmpeg Color Tools
- `colormatrix` — BT.601 ↔ BT.709 conversion
- `zscale` — full color management (primaries, transfer, matrix)
- `tonemap` — HDR to SDR (hable, mobius, reinhard)
- `lut3d` — creative and technical LUTs

### Common Problems & Solutions
| Problem | Cause | Solution |
|---------|-------|----------|
| Washed out colors | BT.601 interpreted as BT.709 | `colormatrix=bt601:bt709` |
| Too dark/bright | Gamma mismatch (2.2 vs 2.4 vs BT.1886) | `zscale` with `transfer` |
| Green tint | Chroma siting or matrix error | `zscale` with correct `matrix` |
| Banding in gradients | 8-bit limit, insufficient dither | `zscale` with `dither=error_diffusion` |

---

## TASK 4 — Alpha Channel Handling

Research alpha workflows:

### Video with Alpha
- ProRes 4444, VP9 alpha, HEVC alpha (limited support)
- WebM with alpha for web overlays
- `format=yuva420p`, `format=yuva444p` pixel formats

### Alpha Operations
- `alphamerge` — combine RGB + separate alpha
- `alphaextract` — extract alpha to grayscale
- `premultiply`/`unpremultiply` — straight vs premultiplied
- `colorkey`, `chromakey` — generate alpha from color

### Common Workflows
1. **PNG sequence → video with alpha**: `ffmpeg -i %03d.png -c:v prores_ks -profile:v 4444`
2. **Video alpha → PNG sequence**: Extract for external processing
3. **Chroma key to alpha**: `chromakey=green:0.1:0.2` → overlay on background
4. **Matte generation**: Use `geq` or `drawbox` to create animated alpha mask

---

## TASK 5 — Image Sequence & Loop Handling

Research patterns for animated assets:

### Image Sequence Input
- Pattern: `%03d.png`, `%04d.tiff`, etc.
- Framerate: `-framerate 30` before `-i`
- Start number: `-start_number 100`

### Looping Short Assets
- `loop` filter for video: `loop=loop=90:size=1` (loop 90 frames)
- `-stream_loop` for input looping (less precise)
- `tile` filter for spatial looping (backgrounds)

### Time Remapping of Assets
- `setpts` for speed ramping
- `reverse` for ping-pong loops
- `trim` + `concat` for custom loops

---

## TASK 6 — Asset Validation & QC

Design automated checks:

### Pre-Render Validation
- `ffprobe` JSON output for: duration, resolution, codec, color space, audio channels
- File size limits (reject >500MB intermediates?)
- Corruption detection: decode first and last frame

### Post-Render QC
- `ffmpeg -i output.mp4 -vf "signalstats,metadata=print" -f null -`
- Black frame detection: `blackdetect`
- Freeze frame detection: `freezedetect`
- Audio silence detection: `silencedetect`
- Loudness verification: `ebur128`

---

## TASK 7 — MCP Asset Schema

Design JSON schema for asset description:

```json
{
  "asset": {
    "id": "broll_sunset_001",
    "type": "video",
    "source": {
      "path": "/assets/stock/sunset_beach.mp4",
      "url": "https://example.com/backup.mp4",
      "checksum": "sha256:abc123..."
    },
    "properties": {
      "duration": 15.5,
      "resolution": [1920, 1080],
      "fps": 30,
      "codec": "h264",
      "color_space": "bt709",
      "has_alpha": false
    },
    "processing": {
      "trim": [2.0, 12.0],
      "speed": 1.0,
      "normalize": true,
      "target_format": "prores_422"
    },
    "license": {
      "source": "pexels",
      "id": "12345",
      "attribution": "Video by John Doe"
    }
  }
}
```

Research: How to validate schema before processing?

---

## Final Output Format

1. **Format compatibility matrix** — all ingestible formats with capabilities
2. **Normalization pipeline** — filter chains for video, image, audio
3. **Color management guide** — color spaces, tools, problem/solution table
4. **Alpha handling specification** — workflows, formats, operations
5. **Image sequence & looping** — patterns, timing, remapping
6. **Asset validation system** — pre/post QC with automated checks
7. **MCP asset schema** — JSON specification with validation rules
