# Research Prompt: FFmpeg Performance Optimization & Scalability

## Role
You are a video infrastructure engineer tasked with maximizing FFmpeg throughput for a video automation factory. The goal is to define hardware acceleration strategies, parallelization patterns, and resource management for rendering hundreds of videos per day.

## Context
Target metrics:
- 5-minute 1080p video renders in <2 minutes on consumer hardware
- 4K video renders in <10 minutes
- Support for concurrent rendering of 4+ videos
- Graceful degradation when hardware acceleration unavailable
- Predictable memory usage (<8GB for 1080p, <16GB for 4K)

---

## TASK 1 — Hardware Acceleration Matrix

Research and document hardware acceleration support across platforms:

### NVIDIA (NVENC/NVDEC/CUDA)
- `h264_nvenc`, `hevc_nvenc`, `av1_nvenc` — quality vs speed presets
- `scale_cuda`, `overlay_cuda`, `yadif_cuda`, `thumbnail_cuda` — which filters have CUDA variants?
- `hwaccel cuda` + `hwaccel_output_format cuda` — zero-copy pipeline
- Multi-GPU: `-gpu` selection, load balancing
- Driver/FFmpeg version compatibility matrix

### Intel Quick Sync (QSV)
- `h264_qsv`, `hevc_qsv`, `av1_qsv` — quality comparison vs NVENC
- `scale_qsv`, `overlay_qsv`, `deinterlace_qsv`
- OneVPL vs legacy MSDK — FFmpeg version requirements
- Integrated vs Arc discrete GPU differences

### AMD (AMF/VAAPI)
- `h264_amf`, `hevc_amf`, `av1_amf`
- VAAPI on Linux: `h264_vaapi`, filter support
- Quality gaps vs x264/x265 software encoding

### Apple (VideoToolbox)
- `h264_videotoolbox`, `hevc_videotoolbox`
- `scale_vt`, `transpose_vt` — limited filter support
- M1/M2/M3 Pro/Max/Ultra performance characteristics

### Software Fallback
- x264, x265, SVT-AV1 preset tuning for speed/quality balance
- When to use `-preset ultrafast` vs `-preset veryfast` vs `-preset fast`

---

## TASK 2 — Zero-Copy Pipeline Architecture

Research how to keep frames on GPU throughout the pipeline:

```
Input (GPU decode) → GPU filters → GPU encode → Output
```

Challenges:
- Mixing CPU and GPU filters — when does copy occur?
- `hwdownload` and `hwupload` — explicit transfers
- Filter compatibility: can `drawtext` (CPU) work between `scale_cuda` and `h264_nvenc`?
- Pixel format constraints: CUDA frames are NV12/P010, drawtext needs RGBA

Design patterns:
- Decode to GPU → GPU scale → download → CPU text overlay → upload → GPU encode
- Minimize transfers by grouping CPU operations
- When is full CPU pipeline actually faster than hybrid?

---

## TASK 3 — Parallelization Strategies

Research how to parallelize FFmpeg workloads:

### Within Single Video
- `-threads` for encoding — optimal thread count vs diminishing returns
- Filter threading: some filters are single-threaded, some multi-threaded
- Slice-based encoding for H.264/HEVC

### Across Multiple Videos
- Process pool: N FFmpeg instances rendering N videos
- Resource limits: CPU affinity, memory caps, GPU memory partitioning
- Queue management: priority, retry, failure isolation

### Distributed Rendering
- Segment video → render chunks on multiple machines → concatenate
- Consistent encoding parameters across nodes
- Network transfer optimization (compressed intermediates?)

---

## TASK 4 — Memory & I/O Optimization

Research memory bottlenecks and mitigation:

### Memory Usage Patterns
- `filter_complex` memory scaling with node count
- Image sequence input: memory-mapped files vs explicit loading
- 4K frame buffers: YUV420p = 12MB/frame, RGBA = 33MB/frame

### Disk I/O
- Intermediate file formats: FFV1 (fast, large) vs H.264 (slow, small) vs ProRes (balanced)
- NVMe vs SSD vs HDD for temp files
- RAM disk for small intermediates
- `-c copy` for stream copying when possible

### Network Sources
- HTTP/S3 input: buffering, retry, bandwidth limits
- `-reconnect`, `-reconnect_streamed`, `-timeout` options

---

## TASK 5 — Quality vs Speed Decision Framework

Create decision tree for LLM:

```
IF deadline < 5 min AND resolution <= 1080p
  THEN use h264_nvenc -preset p1 -tune ll
ELSE IF deadline < 15 min AND quality = "high"
  THEN use h264_nvenc -preset p4 -tune hq -rc vbr -cq 19
ELSE IF hardware unavailable
  THEN use libx264 -preset veryfast -crf 23
```

Research:
- Actual render times for standard test videos across presets/hardware
- VMAF/SSIM quality scores for each preset
- File size differences
- When hardware encoding is WORSE than software (low bitrate, complex content)

---

## TASK 6 — Resource Monitoring & Auto-Tuning

Design telemetry for MCP server:

- `ffprobe` before render: duration, resolution, codec, complexity estimate
- During render: progress, fps, bitrate, ETA, CPU/GPU/memory usage
- After render: actual time, file size, quality metrics (if computed)

Auto-tuning rules:
- If GPU memory >80% → reduce concurrent renders or fall back to software
- If disk I/O wait >50% → switch to faster intermediate codec
- If render time >2x estimate → kill and retry with faster preset

---

## TASK 7 — Benchmark Suite Specification

Define standard benchmarks to run on any new deployment:

1. **Standard test video**: 5min 1080p, mixed content (talking head, b-roll, text, motion graphics)
2. **Stress test**: 4K, 60fps, heavy filter_complex (50+ nodes)
3. **Codec test**: H.264, HEVC, AV1, VP9 encode/decode
4. **Filter test**: CPU-intensive (geq, minterpolate) vs GPU-intensive (scale, overlay)

Output: JSON report with timings, quality scores, resource usage

---

## Final Output Format

1. **Hardware acceleration matrix** — platform, codec, filter support, quality rating
2. **Zero-copy pipeline patterns** — validated filter chains, transfer points
3. **Parallelization architecture** — process model, resource limits, queue design
4. **Memory/I/O optimization guide** — buffer management, intermediate formats
5. **Quality/speed decision tree** — LLM-usable logic with benchmark data
6. **Monitoring specification** — telemetry points, auto-tuning rules
7. **Benchmark suite** — test cases, execution commands, expected outputs
