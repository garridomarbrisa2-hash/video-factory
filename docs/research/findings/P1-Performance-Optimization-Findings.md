# P1 Research Findings: FFmpeg Performance Optimization & Hardware Acceleration

**Research Date:** 2026-07-21
**Research Method:** Tavily web search (14 queries across 7 topic areas)
**Scope:** NVENC, QSV, AMF, VideoToolbox, zero-copy pipelines, parallelization, memory/I/O, quality/speed tradeoffs

---

## 1. NVIDIA NVENC (h264_nvenc, hevc_nvenc, av1_nvenc)

### 1.1 Hardware & Codec Support

| GPU Generation | NVENC Chips | AV1 Encode | Notes |
|---|---|---|---|
| Maxwell (GTX 900) | 1 | No | H.264/HEVC only |
| Pascal (GTX 10) | 1 | No | HEVC 10-bit added |
| Turing (RTX 20) | 1 | No | HEVC B-frames added |
| Ampere (RTX 30) | 1 | No | Quality ~Turing |
| Ada Lovelace (RTX 40) | 1-2 | Yes | AV1 NVENC, SFE support |
| Blackwell (RTX 50) | 2 | Yes | Improved AV1 UHQ |

**RTX 4070 Ti SUPER, 4080, 4090** have 2 NVENC chips enabling Split-Frame Encoding (SFE).

### 1.2 Preset System (Video Codec SDK 10+)

Modern presets: **p1 (fastest) → p7 (slowest/highest quality)**
Legacy presets (slow/medium/fast/hq/bd/ll) are **deprecated** — FFmpeg warns: "The selected preset is deprecated. Use p1 to p7 + -tune or fast/medium/slow."

Tuning options:
- `-tune hq` — high quality
- `-tune uhq` — ultra high quality (FFmpeg 12.2+; dramatically improves hevc_nvenc)
- `-tune ll` / `-tune ull` — low / ultra-low latency

Multipass: `-multipass fullres` (two-pass at full resolution; replaces deprecated `-2pass 1`)

### 1.3 Quality vs x264/x265 — Benchmark Data

From scottstuff.net H.265 benchmarking (VMAF=95 target, 10-bit 4:2:0):

| Encoder | File size @ VMAF 95 | Encode time |
|---|---|---|
| libx265 -preset slow | 4,232 kB | 38.64–45.34s |
| hevc_nvenc p7 + `-tune uhq` | 4,384 kB (~3.6% larger) | 14.36s (~3x faster) |

Key findings:
- **`-tune uhq` is essential**: VMAF 95 reached at `-cq 33.7` with uhq vs `-cq 26.2` without. Worst preset with uhq beats best preset without it.
- `-rc vbr` appears to be default when `-cq:v` is used (identical results with/without).
- NVENC `-cq` is **NOT the same scale** as x264 `-crf` — must calibrate via VMAF on own footage.

Consensus quality ranking (per Reddit/Stack Overflow/testing):
- **x265 > hevc_nvenc** for archiving (psychovisual options, grain preservation)
- **hevc_nvenc ≥ x264 medium** at medium bitrates with p6/p7 + uhq
- Hardware encoders excel at: "decent quality at medium bitrates very fast without burdening CPU"

### 1.4 AV1 NVENC vs SVT-AV1 (RTX 50 series, Reddit benchmark)

| Encoder | Output size | FPS | VMAF |
|---|---|---|---|
| av1_nvenc p7 -tune uhq -cq 35 | 4.02 MB (1922 kb/s) | 117 | 94.53 |
| libsvtav1 -preset 6 -crf 26 | 3.86 MB (1844 kb/s) | 128 | 94.45 |

NVENC AV1 is now nearly at parity with SVT-AV1 preset 6 in quality-per-bit (~4% larger), with up to 3x faster FPS in other tests. SVT-AV1 presets slower than 6 still win on efficiency at exponential time cost.

Independent test (giannirosato.com): "SVT-AV1 is in a class by itself. Preset 8 dominates the hardware encoders across the board... NVENC AV1 is more efficient than QSV AV1 on Arc, even if the advantage is slight."

### 1.5 Split-Frame Encoding (SFE) — Ada+ GPUs

- Splits one UHD frame into horizontal slices encoded in parallel on multiple NVENC chips, then stitched at bitstream level.
- Throughput gains: **+82.6% (4K HEVC P1), +86.4% (8K HEVC P1), up to +96.2% (4K HEVC P7)**
- 4K HEVC: 285 → 520 FPS; 8K HEVC: 72 → 135 FPS
- RD penalty is negligible: ~0.042 dB PSNR / 0.053 VMAF at 4K (max observed 0.41 dB in UHQ 2-pass)
- Enables P7 preset for real-time 4K60p HEVC (not feasible on single NVENC chip)
- Enable with `-split_encode_mode 2` (auto) — introduced SDK 12.0, Ada GPUs, HEVC/AV1 only
- Power: 1-chip HEVC 38.5W → 2-chip 43.0W; roughly **1/10th the energy** of CPU software encoding (~150W)

### 1.6 NVENC Command Examples

**Check support:**
```bash
ffmpeg -encoders | grep nvenc
ffmpeg -h encoder=hevc_nvenc   # actual list of presets for your build
```

**Quality VOD (recommended starting point):**
```bash
ffmpeg -y -hwaccel cuda -i source.mp4 -c:v hevc_nvenc -preset p7 -tune uhq \
  -multipass fullres -rc vbr -cq 30 -spatial_aq 1 -temporal_aq 1 \
  -rc-lookahead 20 -bf 3 -pix_fmt p010le -c:a copy out.mp4
```

**ABR ladder rung (quality target + hard ceiling):**
```bash
ffmpeg -y -hwaccel cuda -i source.mp4 -c:v h264_nvenc -preset p6 -tune hq \
  -rc vbr -cq 23 -maxrate 4M -bufsize 8M -an rung_1080.mp4
```

**Low-latency live:**
```bash
ffmpeg -i input -c:v h264_nvenc -preset p4 -tune ull -rc cbr -b:v 6M \
  -maxrate 6M -bufsize 12M -zerolatency 1 -g 60 out.mp4
```

**AV1 NVENC (RTX 40+):**
```bash
ffmpeg -y -hwaccel cuda -i source.mp4 -c:v av1_nvenc -preset p7 -tune uhq \
  -rc vbr -cq 35 -b:v 0 out_av1.mp4
```

**Multi-output 1:N transcode (GPU scale):**
```bash
ffmpeg -y -vsync 0 -hwaccel cuda -hwaccel_output_format cuda -i input.mp4 \
  -filter_complex "[0:v]hwupload_cuda,split=4[o1][o2][o3][o4]" \
  -map "[o1]" -c:v h264_nvenc -b:v 8M out1.mp4 \
  -map "[o2]" -c:v h264_nvenc -b:v 10M out2.mp4
```

**Rate control mode reference:**

| Mode | NVENC flags | Use when |
|---|---|---|
| Constant quality | `-rc vbr -cq N` | VOD, stable quality |
| Capped CRF-like | `-rc vbr -cq N -maxrate M -bufsize 2M` | ABR rungs |
| CBR | `-rc cbr -b:v M` | Live, fixed bandwidth |

### 1.7 Resource Requirements & Fallback

- Requires NVIDIA GPU + `--enable-nvenc` build (non-free for GPL3 builds); NVENC/NVDEC are dedicated ASICs separate from CUDA cores → near-zero CPU/3D-engine load.
- Consumer GeForce historically limited to ~3 (now 8 on 40-series) concurrent NVENC sessions; datacenter GPUs unrestricted.
- Fallback: if encoder init fails with "invalid param (8): Presets P1 to P7 are not supported with older 2 Pass RC Modes" → remove `-2pass 1`, use `-multipass fullres` instead.

---

## 2. Intel QSV (h264_qsv, hevc_qsv, av1_qsv)

### 2.1 oneVPL vs MSDK

- **oneVPL (oneAPI Video Processing Library)** is the successor to Intel Media SDK (MSDK). MSDK is EOL — "new features for new Intel Gen platforms will be supported in oneVPL only."
- FFmpeg 5.x+ supports both: `--enable-libvpl` (oneVPL) vs `--enable-libmfx` (MSDK). **Cannot enable both simultaneously.**
- VPL dispatcher loads: `VPL-intel-gpu` for Xe architecture (Arc, 11th gen+ iGPU); falls back to Media SDK implementation for legacy hardware.
- Codec support via _qsv (oneVPL):
  - **Decoders:** av1_qsv, h264_qsv, hevc_qsv, mpeg2_qsv, mjpeg_qsv, vc1_qsv, vp8_qsv, vp9_qsv
  - **Encoders:** h264_qsv, hevc_qsv, mpeg2_qsv, mjpeg_qsv, vp9_qsv, av1_qsv (Arc/newer)

### 2.2 Quality: Arc vs Integrated GPU

From Tom's Hardware testing (VMAF):
- **Intel Arc is the HEVC quality winner among hardware encoders**: VMAF 92.1 @ 8Mbps 4K, beating NVIDIA Turing/Ampere/Ada (which tie) and well ahead of CPU libx265 medium.
- UHD 770 (12th/13th gen iGPU) H.264: between NVIDIA Pascal and Turing/Ampere/Ada in VMAF.
- UHD 770 HEVC: only 1–2 VMAF points behind Arc and NVIDIA.
- Arc's redesigned media engine gives **>5 VMAF points** improvement over previous Intel generations (arXiv 2511.18686).
- Puget Systems: For Premiere encoding, RTX 4060 beats Arc A770 slightly on H.264; HEVC is "on par or a bit faster" on Arc → **a wash overall** between Arc and NVIDIA.
- Reddit (2026): at VMAF 95-matched settings, Arc A750 encode was 10–20% slower and files larger than NVENC (RTX 5060 Ti) — "nvenc would have 10% of original size while qsv(arc) would be 15%". Conflicting with Tom's HEVC result → content/codec dependent; Arc AV1 QSV is slightly behind NVENC AV1.

### 2.3 QSV Rate Control

- `global_quality` (1–51, ~21 recommended) acts like CRF; with 3 algorithm options, `-look_ahead 1` fanciest.
- **ICQ** (Intelligent Constant Quality) works with h264_qsv; historically problematic with hevc_qsv on some builds. On Arc, control with `-global_quality` (15–19 tested range; lower = better).
- `-preset veryslow` → `slow` is the sensible quality tradeoff; presets 1–7 map roughly: preset 4 ≈ 239 FPS @ VMAF 73.29, preset 1 ≈ 128 FPS @ VMAF 73.75 (Intel-supplied 1080p test).
- `-async_depth` (default 2) — raising may improve throughput on some systems.

### 2.4 QSV Command Examples

**Basic HEVC transcode (Arc / iGPU):**
```bash
ffmpeg -init_hw_device qsv=hw -i input.mp4 -c:v hevc_qsv -sn output.mp4
```

**Full hardware pipeline (decode→filter→encode):**
```bash
ffmpeg -y -init_hw_device qsv=hw,child_device_type=dxva2 -hwaccel qsv \
  -hwaccel_output_format qsv -c:v h264_qsv -i input.mp4 \
  -vf "vpp_qsv=framerate=60,scale_qsv=w=1920:h=1080" \
  -c:v h264_qsv -global_quality 21 -preset slow output.mp4
```

**ICQ rate control (Arc):**
```bash
ffmpeg -init_hw_device qsv=hw -i input.mp4 -c:v hevc_qsv \
  -global_quality 16 -preset veryslow output.mp4
```

**Intel-recommended broadcast ladder (with hwupload):**
```bash
ffmpeg -y -init_hw_device qsv=hw -filter_hw_device hw -i football_1080p.mp4 \
  -vf hwupload=extra_hw_frames=64,format=qsv -c:v h264_qsv \
  -b:v 4M -maxrate 4M -bufsize 4M -g 120 -idr_interval 4 \
  -async_depth 5 -preset 4 -c:a aac -b:a 128k out.mp4
```

**Hybrid: QSV decode → software x265 encode:**
```bash
ffmpeg -hwaccel qsv -c:v h264_qsv -i input.264 \
  -vf hwdownload,format=nv12 -c:v libx265 out.265
```

**Multi-GPU selection (Linux):**
```bash
ffmpeg -init_hw_device vaapi=va:/dev/dri/renderD129 -init_hw_device qsv=hw@va \
  -filter_hw_device hw -f rawvideo -pix_fmt yuv420p -s:v 176x144 -i in.yuv \
  -vf hwupload=extra_hw_frames=64,format=qsv -c:v h264_qsv -y out.h264
```

### 2.5 QSV Filter Support

Known QSV-accelerated filters (documentation is notoriously poor):
- `scale_qsv` — scaling/format conversion
- `vpp_qsv` — video post-processing: crop (`cw/cx/w/h`), deinterlace (`deinterlace=2`), framerate
- `deinterlace_qsv`
- `hwupload=extra_hw_frames=64,format=qsv` — upload CPU frames to QSV surfaces

Working example from experimentation:
```bash
ffmpeg -init_hw_device qsv=qsv -hwaccel qsv -i input.mts \
  -c:v h264_qsv -preset veryslow \
  -vf "vpp_qsv=deinterlace=2:cw=628:cx=0:w=640:h=480" -q:v 30 output.mp4
```

Note: `scale_qsv` must not be used with `w=`/`h=` kwargs in some builds — `vpp_qsv=w=1920:h=1080` is more reliable. **This is an active pain point: no authoritative argument list exists.**

### 2.6 Resource Requirements & Fallback

- Requires Intel CPU with iGPU (6th gen+ for HEVC) or Arc discrete GPU; on Linux needs media-driver, gmmlib, onevpl-intel-gpu packages, HuC firmware loaded.
- Xeon/EPYC systems without iGPU need Arc card.
- Fallback strategy: try oneVPL → libmfx → VAAPI (`h264_vaapi`/`hevc_vaapi`) → software x264/x265. ICQ unsupported on hevc_qsv → fall back to VBR with `-b:v`.

---

## 3. AMD AMF (h264_amf, hevc_amf, av1_amf)

### 3.1 Capabilities & Quality Gap

- Supported on Windows natively; Linux historically VAAPI-only (Vulkan interop for AMF is WIP).
- Encoders: h264_amf, hevc_amf, av1_amf (RX 7000+ for AV1).
- **Quality consensus: AMD lags NVIDIA and Intel.** Tom's Hardware: AMD RDNA 2/3 got 44 VMAF @ 8Mbps 4K H.264 vs Intel Arc 65, NVIDIA 57; older AMD GPUs "abysmal" at 33. AMD h264 encoder "just that slow... they don't bother improving it."
- AMF documentation is chaotic; OBS implementation differs from raw FFmpeg.

### 3.2 AMF Settings

Presets: `-usage transcoding` + `-quality quality|balanced|speed` (AV1 adds `high quality`).

Key parameters: `-vbaq true`, `-preencode true`, `-preanalysis true`, `-high_motion_quality_boost_enable true`, `-pa_lookahead_buffer_depth 40`, `-pa_taq_mode 2`, `-pa_adaptive_mini_gop true`, `-rc cqp|cbr|vbr_peak|vbr_latency`.

### 3.3 AMF Command Examples (official AMD recommendations)

**Archive H.264:**
```bash
ffmpeg -i input.mp4 -c:v h264_amf -preset quality -rc vbr_peak \
  -b:v 4000000 -maxrate 16000000 -bufsize 16000000 -vbaq true \
  -preencode true -g 600 -high_motion_quality_boost_enable true \
  -preanalysis true -max_b_frames 3 -pa_adaptive_mini_gop true \
  -pa_lookahead_buffer_depth 40 -pa_taq_mode 2 output.mp4
```

**Archive HEVC:**
```bash
ffmpeg -i input.mp4 -c:v hevc_amf -preset quality -rc vbr_peak \
  -b:v 4000000 -maxrate 16000000 -bufsize 16000000 -vbaq true \
  -preencode true -g 600 -high_motion_quality_boost_enable true \
  -preanalysis true -pa_lookahead_buffer_depth 40 -pa_taq_mode 2 output.mp4
```

**Broadcast H.264 (CBR, 60fps GOP):**
```bash
ffmpeg -i input.mp4 -c:v h264_amf -preset quality -rc cbr \
  -b:v 4000000 -bufsize 8000000 -vbaq true -preencode true -g 60 \
  -high_motion_quality_boost_enable true -preanalysis true \
  -max_b_frames 2 -bf 2 -pa_lookahead_buffer_depth 40 -pa_taq_mode 2 output.mp4
```

**Linux fallback (VAAPI on AMD):**
```bash
ffmpeg -hwaccel vaapi -hwaccel_output_format vaapi -i input.mp4 \
  -vf 'format=vaapi,hwupload' -c:v hevc_vaapi -qp 32 output.mp4
```

### 3.4 Resource Requirements & Fallback

- Windows: recent AMD Adrenalin driver; AMF runtime bundled with driver.
- Verify with `ffmpeg -h encoder=h264_amf`.
- Check capabilities on Linux: `vainfo | grep Slice` (VAEntrypointEncSlice = encode support).
- Fallback: AMF → VAAPI (Linux) → software. For low-bitrate streaming, set `AMF_PA_CAQ_STRENGTH` high.

---

## 4. Apple VideoToolbox (h264_videotoolbox, hevc_videotoolbox)

### 4.1 Capabilities

| Mac | Supported codecs |
|---|---|
| Intel Mac 2011+ | H.264 |
| Intel Mac 2017+ | H.264, H.265 |
| Apple Silicon (M1/M2/M3/M4) | H.264, H.265, ProRes (partial via prores_videotoolbox) |

- **No CRF support** — bitrate (`-b:v`) is the primary control; `-q:v` (0–100) works on Apple Silicon for fixed-quality mode (added in ffmpeg commit efece44).
- Can leverage eGPU resources via VTEncoderXPCService.
- Pro/Max chips have multiple media engines → higher throughput.

### 4.2 Performance & Quality Data

- M1 Pro 4K test (yre.jp): hevc_videotoolbox at 1.72x realtime vs libx265 (-crf 28 -preset fast) at 0.116x → **~15x faster**, CPU at 30–50% instead of pegged.
- Martin Riedl: videotoolbox **4x faster than x264** (H.264), **3x faster than x265** (HEVC); only 20% CPU vs 100%.
- **Quality gap:** default hevc_videotoolbox produced "hazy" output at ~22 MB; with `-q:v 50` quality was good but file ballooned to ~171 MB. libx265 delivered "excellent" quality at ~24 MB. VideoToolbox needs significantly higher bitrate to match libx265 VMAF.
- Homebrew ffmpeg enables VideoToolbox by default.

### 4.3 Command Examples

**Basic:**
```bash
ffmpeg -i input.mp4 -c:v h264_videotoolbox -b:v 4M -c:a aac -b:a 128k out.mp4
```

**HEVC fixed quality (Apple Silicon):**
```bash
ffmpeg -i input.mp4 -c:v hevc_videotoolbox -q:v 50 -c:a copy out.mp4
```

**Full HW pipeline (decode + encode):**
```bash
ffmpeg -hwaccel videotoolbox -i input.mp4 -c:v hevc_videotoolbox \
  -b:v 6000k -c:a copy out.mp4
```

**Check options:**
```bash
ffmpeg -encoders | grep videotoolbox
ffmpeg -h encoder=h264_videotoolbox
```

### 4.4 Resource Requirements & Fallback

- No drivers needed (built into macOS); ffmpeg must be built `--enable-videotoolbox`.
- Some flags silently ignored — check FFmpeg console output.
- Fallback: videotoolbox → libx264/libx265. If `-q:v` unsupported (older Intel Macs), use `-b:v` with generous bitrate (add ~30–50% over x264 target).

---

## 5. Zero-Copy Pipeline (hwaccel, hwdownload/hwupload, mixing CPU/GPU filters)

### 5.1 Concepts

- **Zero-copy**: frames stay in GPU memory from decode → filter → encode. Avoids expensive PCIe transfers (a 1080p NV12 frame ≈ 3 MB; at 60fps ≈ 180 MB/s per direction).
- `-hwaccel cuda -hwaccel_output_format cuda` keeps decoded frames in VRAM.
- GPU filters: `scale_cuda` (newer, replaces `scale_npp`), `scale_npp`, `yadif_cuda`, `transpose_npp`, `overlay_cuda`, `nlmeans_opencl` (via OpenCL), `scale_qsv`/`vpp_qsv`, `scale_vaapi`.
- `hwdownload` pulls frames to system RAM; `hwupload` pushes back up; `format=nv12|p010le` conversions often needed at boundaries.

### 5.2 Command Examples

**Full GPU pipeline (NVIDIA decode→scale→encode, zero-copy):**
```bash
ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -i input.mkv \
  -vf "scale_cuda=1280:-2" -c:v h264_nvenc -preset p6 -c:a copy out.mkv
```

**10-bit HEVC source → GPU scale → download for CPU filter → NVENC:**
```bash
ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -i input.mkv \
  -filter_complex "scale_cuda=1280:-2,hwdownload,format=p010le,format=nv12,hwupload" \
  -c:v h264_nvenc -preset p7 -tune hq -rc vbr -cq 30 out.mkv
```

**NVIDIA-documented CPU+GPU mixing (CPU decode → GPU filter → NVENC):**
```bash
ffmpeg -vsync 0 -c:v h264_cuvid -i input.264 \
  -vf "fade,hwupload_cuda,scale_npp=1280:720" -c:v h264_nvenc output.264
```

**GPU decode + GPU denoise (OpenCL) + NVENC:**
```bash
ffmpeg -hide_banner -init_hw_device opencl=gpu:0.0 -filter_hw_device gpu \
  -hwaccel nvdec -hwaccel_output_format yuv420p -i in.mkv \
  -vf hwupload,nlmeans_opencl=s=1.0:p=7:pc=5:r=3:rc=3,hwdownload \
  -c:v hevc_nvenc -preset p7 -tune hq -rc vbr -cq 30 out.mkv
```

**VAAPI zero-copy:**
```bash
ffmpeg -hwaccel vaapi -hwaccel_output_format vaapi -vaapi_device /dev/dri/renderD128 \
  -i input.mp4 -vf 'scale_vaapi=1280:720' -c:v h264_vaapi -qp 19 out.mp4
```

### 5.3 Pitfalls & Rules

- **"Input frame is not in the configured hwframe context"** error: mixing hwaccel output format with mismatched filter chain. Fix by adding explicit `hwdownload,format=...` before CPU filters and `hwupload` after, or use `-init_hw_device ... -filter_hw_device`.
- Old decode (`-c:v h264_cuvid`) vs new (`-hwaccel cuda`): cuvid decoders auto-download unless `-hwaccel_output_format cuda` set; prefer the modern `-hwaccel cuda` syntax.
- Not all filters have GPU variants — anything CPU-bound (e.g., `pad`, `drawtext`, most `zscale` chains) forces a download; chain GPU filters together before downloading once.
- `scale_npp` deprecated in favor of `scale_cuda` in recent builds.
- QSV hybrid: `-hwaccel qsv -c:v hevc_qsv -i in.mkv -vf "hwdownload,format=p010le" ...` then CPU filters, then any encoder.

### 5.4 Resource Requirements

- ffmpeg built with `--enable-cuda-nvcc --enable-libnpp` (for scale_cuda/scale_npp) and `--enable-nvenc`.
- VRAM: 1080p pipeline typically < 500 MB; 4K multi-output with lookahead buffers can exceed 2 GB.
- `extra_hw_frames=64` commonly needed in hwupload for QSV filter chains.

---

## 6. Parallelization

### 6.1 Within FFmpeg (threads)

- `-threads N` controls per-codec thread pools; `-threads 0` = auto.
- Thread types: `FF_THREAD_FRAME` (frame-level) and `FF_THREAD_SLICE` (slice-level); VP9/AV1/VVC add tile-level parallelism.
- **High thread counts hurt**: >16 threads triggers nvdec warnings; VBV-sensitive encoders (libx264) can undershoot/overflow target bitrate with very high thread counts. Recommended manual cap: **≤8 threads when running multiple sessions**.
- Quality is non-deterministic across thread counts: same input + different `-threads` → slightly different file sizes (few KB). For bit-exact archival reproducibility, pin thread count.

### 6.2 FFmpeg 7.0+ Multi-Threaded Conversion

- CLI architecture refactor ("most complex refactoring in decades"): demuxing, decoding, filtering, encoding, muxing now run on separate threads **within one process**.
- Only helps when there are multiple inputs/outputs/filters — single-file 1:1 transcodes see little change.
- Outputs now mux in parallel rather than sequentially (older FFmpeg created output files one after another).

### 6.3 Multi-Instance / Process Pools

- Multiple outputs in one FFmpeg process "slow down to the slowest encoder"; serial encoders (e.g., audio) become the bottleneck → **separate FFmpeg processes per output run more in parallel**.
- GNU `parallel` + FFmpeg works but each instance pre-allocates thread pools → oversubscription. Cap `-threads` per instance: `parallel -j4 ffmpeg -threads 4 ...`.
- NVENC: RTX 4090 has 2 NVENC units, 8 concurrent sessions allowed. Dual-instance encoding *sometimes* scales 25→50 fps, often only 25–40 fps (driver scheduling inconsistency; Nsight shows encoders busy — known flaky behavior). SFE is the sanctioned way to use both chips for one stream.
- Optimal jobs/hour example (1080p60s clips): `-preset medium` 85s → 42 jobs/hr; `-preset fast` 55s → 65 jobs/hr (**+55% capacity**).

### 6.4 Distributed / Chunked Encoding

Pattern (rustyguts.dev, AWS Step Functions style):
1. **Split** source into chunks at GOP boundaries (or fixed duration):
   ```bash
   ffmpeg -i source.mkv -c copy -map 0 -segment_time 60 -f segment segments/%03d.mkv
   ```
2. **Transcode chunks in parallel** across workers:
   ```bash
   ffmpeg -i segments/001.mkv -c:v libsvtav1 -crf 30 -preset 5 transcoded/001.mkv
   ```
3. **Concatenate** losslessly:
   ```bash
   ffmpeg -f concat -safe 0 -i concat.txt -i audio.wav -c copy output.mp4
   ```
- I/O becomes the bottleneck: "instead of processing a 100 GB file on a single machine, we may process 100 × 1 GB files on 10 machines" — needs beefy network/storage.
- Pitfalls: `-reset_timestamps 1` required for clean segments; audio sync drift at cut points with `-c copy` → re-encode audio at boundaries; encode each chunk with fixed GOP/closed-GOP so concatenation is seamless.
- Alternative intra-process split: keyframe-segment parallelism proposal (each thread encodes a full GOP segment) — discussed in FFmpeg community, not implemented; would avoid per-frame region splitting's quality cost.

### 6.5 Orchestration Guidance

- Use a job queue + containerized workers; match container CPU limits to FFmpeg `-threads`.
- GPU nodes: keep driver/SDK aligned; build failover path to software encoders when GPU nodes go offline.
- Measure per-machine throughput before scaling out.

---

## 7. Memory & I/O Optimization

### 7.1 Memory Footprint

- Frame buffer math: FFmpeg holds 10–20 frames in flight (decoder + lookahead + B-frames + filter queues). 8K 4:2:0 10-bit frame ≈ 47 MB → **470–940 MB per job just for buffers**. Real-world 8K HEVC→x264 job consumed ~9 GB virtual memory.
- Mitigations (AddPipe case study):
  - Cap resolution early (8K→4K cut memory 4x: 9 GB → 2.25 GB).
  - Reduce thread pool sizes, decoder picture buffers, filter frame queues.
  - Embedded builds: `--disable-threading`, `--enable-small`, explicit buffer limits.
- NVENC lookahead (`-rc-lookahead`) and `-multipass fullres` increase VRAM/system RAM usage modestly.

### 7.2 RAM Disk / tmpfs

- tmpfs on Ryzen 1700: 2.8–3.5 GB/s sequential, 492K–2.2M IOPS — **vastly exceeds any NVMe** (Intel P4610) and even Optane P4801X.
- **But transcoding is rarely I/O-bound**: Plex/Jellyfin testing shows identical transcode start times (5s) on RAM disk vs SSD — "storage medium is not a bottleneck; the limitation is the processors."
- Real benefit of RAM transcode folder: **eliminating SSD wear** from continuous small-file writes (Plex/Unmanic workloads), not speed.
- tmpfs consumes RAM directly — size it as (job count × peak intermediate size) with headroom; volatile (data lost on reboot).

### 7.3 NVMe vs SSD vs HDD

- If disk usage hits 100% during render while CPU/RAM sit at 50% → I/O-bound; moving **input and output files** (not the ffmpeg binary) to SSD helps most.
- Use separate physical disks for source and destination to avoid head-seek contention on HDDs.
- RAID0 striping > single disk; RAID1/5 don't help write speed.
- I/O scheduler (Linux): `none` often optimal for NVMe (hardware controller manages scheduling); `mq-deadline`/`kyber` alternatives for SATA.
- Enable write-behind caching on removable drives.
- Buffer/cache warming: preloading frequently-accessed inputs into OS page cache reduces decode-stage I/O stalls.

### 7.4 Intermediate Codecs

- For multi-stage pipelines (edit → grade → encode), use fast intermediates to avoid repeated lossy re-encode and slow seeks:
  - **ProRes** (prores_ks / prores_videotoolbox on Mac) — fast decode, large files (~10x H.264).
  - **DNxHD/DNxHR** (dnxhd) — similar role, cross-platform.
  - **FFV1** (`-c:v ffv1 -level 3`) — lossless, ~2x source, archival-safe.
  - **Lossless x264** (`-crf 0`) or lossless HEVC — smaller but slower to decode.
- Intermediates belong on the fastest storage available (NVMe/RAM disk) since they're read/written repeatedly.
- Two-pass encoding note: modern guidance favors single-pass CRF/CQ + VMAF verification; dropping the second pass saved 30–45 min per project with no measurable quality loss at matched settings.

### 7.5 Command Examples

**RAM disk transcode (Linux):**
```bash
sudo mkdir /mnt/ramdisk && sudo mount -t tmpfs -o size=16G tmpfs /mnt/ramdisk
ffmpeg -i /mnt/ramdisk/input.mkv -c:v libx264 -preset fast /mnt/ramdisk/out.mp4
```

**Windows RAM disk:** use ImDisk/SoftPerfect, then point FFmpeg paths at the volume.

**Intermediate render then final encode:**
```bash
ffmpeg -i edit_timeline.mov -c:v prores_ks -profile:v 3 -c:a pcm_s16le master.mov
ffmpeg -i master.mov -c:v hevc_nvenc -preset p7 -tune uhq -rc vbr -cq 30 \
  -c:a aac -b:a 192k final.mp4
```

---

## 8. Quality/Speed Decision Framework

### 8.1 x264 Preset BD-Rate Table (4K UHD, vs veryslow reference)

| Preset | BD-Rate (%) | Encoding time multiplier |
|---|---|---|
| ultrafast | 51.2 | — |
| superfast | 39.0 | — |
| veryfast | 53.5 | — |
| faster | 53.3 | — |
| fast | 50.3 | — |
| medium | 37.5 | — |
| slow | 5.3 | — |
| slower | 0.8 | — |
| veryslow | 0.0 (reference) | — |

Each preset step ≈ 1.3–2.0x the encoding time of the preceding one. **Sweet spot: `slow`** — within ~5% of best achievable bitrate at a fraction of veryslow time.

### 8.2 Decision Matrix (by workload)

| Workload | Recommended | Why |
|---|---|---|
| Live / real-time capture | NVENC p4–p6 / QSV / AMF speed | Throughput dominates; near-zero CPU |
| High-volume VOD batch | NVENC p6–p7 + uhq / QSV slow | Cost-per-minute wins; ~3% larger than x265 |
| YouTube upload transcode | NVENC p5–p6 / QSV slow | Platform re-encodes anyway |
| Archival / mastering | libx265 slow / SVT-AV1 preset 4–6 | Quality-per-bit compounds forever |
| Blu-ray rip compression | x265 veryslow / SVT-AV1 | Maximum efficiency |
| AV1 storage savings | SVT-AV1 (software) | Beats av1_nvenc on efficiency (gap shrinking) |
| Spiky low-volume jobs | Software | Idle GPU = wasted money |
| macOS quick transcode | VideoToolbox | 4–15x faster; pad bitrate +30–50% |
| AMD-only Windows | AMF with full PA tuning | Accept quality gap vs NVENC |

### 8.3 Hardware Encoder Quality Ranking (per current benchmarks)

**H.264:** Intel Arc > NVIDIA Turing/Ampere/Ada > UHD 770 > NVIDIA Pascal > CPU (fast presets) > AMD RDNA 2/3
**HEVC:** Intel Arc ≥ NVIDIA Ada/Ampere/Turing ≈ UHD 770 > NVIDIA Pascal > libx265 medium (at low bitrates; x265 wins at matched time) > AMD
**AV1:** SVT-AV1 (any preset ≤8) > NVENC AV1 ≥ QSV AV1 (Arc)

### 8.4 Calibrating CQ/CRF with VMAF (the correct method)

**Never copy CRF values across encoders.** Calibrate per encoder per content class:

```bash
# Encode samples at several quality points
for q in 24 27 30 33 36; do
  ffmpeg -y -hwaccel cuda -i sample.mp4 -c:v hevc_nvenc -preset p7 -tune uhq \
    -rc vbr -cq $q -c:a copy test_cq$q.mp4
done

# Measure VMAF against source
ffmpeg -i test_cq30.mp4 -i sample.mp4 \
  -lavfi "[0:v]setpts=PTS-STARTPTS[dist];[1:v]setpts=PTS-STARTPTS[ref];\
[dist][ref]libvmaf=feature='name=psnr|name=float_ssim':log_fmt=json:log_path=vmaf.json" \
  -f null -
```

Target: **VMAF 93–96** is visually transparent for most content; VMAF 95 is the common "archival-ish" bar.

Full multi-metric command:
```bash
ffmpeg -i encoded.mp4 -i master.mp4 \
  -lavfi "[0:v]setpts=PTS-STARTPTS[dist];[1:v]setpts=PTS-STARTPTS[ref];\
[dist][ref]libvmaf=feature='name=psnr|name=float_ssim|name=float_ms_ssim':\
log_fmt=json:log_path=metrics.json" -f null -
```

VMAF gotchas:
- Default model trained on 1080p — **upscale lower-res footage to 1920 wide before scoring** or scores inflate.
- Use the 4K model for >1080p content.
- Distorted input goes FIRST, reference second.
- PSNR (dB, ∞ = identical), SSIM/MS-SSIM (0–1), VMAF (0–100) are different scales — never compare across metrics.
- Sub-1080p example with round-trip scaling:
```bash
ffmpeg -r 24 -i encoded_720p.mp4 -r 24 -i ref_1080p.mp4 -lavfi \
"[0:v]setpts=PTS-STARTPTS,scale=1920:-2[dist];\
[1:v]setpts=PTS-STARTPTS[ref];[dist][ref]libvmaf=n_threads=16" -f null -
```

### 8.5 Practical Preset Selection Rules

1. **Software x264/x265**: default `medium` is fine; `slow` gets within ~10% of best (x265) / ~5% BD-rate (x264); avoid ultrafast/superfast/veryfast entirely (worse BD-rate than medium at higher speed — yes, really, per the table above).
2. **NVENC**: always `-tune uhq` (or `hq` minimum) + p6/p7 for anything quality-sensitive; p1–p3 only for raw throughput. Adjust `-cq` after enabling uhq (it shifts the scale by ~7 points).
3. **QSV**: `-preset veryslow`/`slow` + `-global_quality` 16–21 (ICQ); look_ahead on where supported.
4. **AMF**: `-quality quality` + full pre-analysis chain (see §3.3); accept ~10–15% bitrate penalty vs NVENC at matched quality.
5. **VideoToolbox**: `-q:v 50–65` or bitrate +30–50% over x264 target; HEVC over H.264 for size.
6. **Two-pass**: only for hard bitrate targets (disc, streaming caps); otherwise single-pass CQ/CRF + VMAF check.

---

## 9. Cross-Cutting Fallback Strategy (Universal)

```
1. Try GPU zero-copy:  -hwaccel cuda|qsv|vaapi|videotoolbox -hwaccel_output_format <same>
2. If filter unsupported on GPU: insert hwdownload,format=nv12 → CPU filter → hwupload
3. If HW encoder missing/fails: fall back per platform:
   Windows+NVIDIA: h264_nvenc → h264_qsv (iGPU) → h264_amf → libx264
   Windows+AMD:    h264_amf → h264_qsv (iGPU) → libx264
   Linux+Intel:    h264_qsv → h264_vaapi → libx264
   macOS:          h264_videotoolbox → libx264
4. If init fails with preset errors: modernize flags (p1–p7 + -tune + -multipass, drop -2pass/-rc vbr_hq)
5. Verify actual HW usage mid-run: nvidia-smi / intel_gpu_top / amdgpu_top / macOS Activity Monitor (VTDecoderXPCService, VTEncoderXPCService)
```

**Verification commands:**
```bash
ffmpeg -encoders | grep -E "nvenc|qsv|amf|videotoolbox|vaapi"
ffmpeg -hwaccels
ffmpeg -h encoder=hevc_nvenc    # per-encoder option list (source of truth for your build)
```

---

## GAPS REQUIRING PERPLEXITY DEEP RESEARCH

1. **Complete QSV filter argument documentation** — No authoritative list of `vpp_qsv`/`scale_qsv` arguments and their semantics exists anywhere Tavily could find. Intel forums explicitly complain about this. Need deep dive into FFmpeg source (libavfilter/vf_vpp_qsv.c) and oneVPL spec to enumerate every parameter, valid ranges, and Arc-vs-iGPU differences.

2. **NVENC `-cq` ↔ x264 `-crf` mapping curves** — Community consensus says "don't copy values across," but no published data maps equivalent VMAF points across the two scales for multiple content classes/resolutions. Requires original benchmarking.

3. **AMF AV1 (av1_amf) quality benchmarks** — RX 7000-series AV1 encode quality vs NVENC AV1 and SVT-AV1 is essentially undocumented (Tom's Hardware tested H.264/HEVC only at the time). No VMAF data found.

4. **VideoToolbox on M3/M4 (and Pro/Max multi-media-engine scaling)** — All benchmarks found are M1/M2-era. No data on whether FFmpeg can saturate multiple media engines on M-series Pro/Max chips (e.g., via parallel sessions), nor M4 AV1-encode status (Apple added AV1 decode; hardware AV1 encode status unclear).

5. **SFE (Split-Frame Encoding) FFmpeg-level flag behavior** — Papers document `-split_encode_mode` at SDK level and arXiv used "2 or 15" values, but exact FFmpeg option semantics (which values map to 2-way/auto, interaction with `-multipass`, whether it's exposed as encoder AVOption in current FFmpeg releases) needs verification against current FFmpeg source/docs.

6. **Concurrent NVENC session scaling inconsistency** — The 4090 dual-instance 25–50 fps fluctuation is a known forum complaint with no root cause or fix documented. Needs investigation into driver scheduling, session limits per GeForce vs datacenter, and whether SFE or MIG-style partitioning resolves it.

7. **Chunked/distributed encoding stitching quality** — No quantitative data on VMAF/PSNR discontinuities at chunk boundaries when concatenating independently encoded segments (open vs closed GOP, lookahead reset effects). Academic and practical treatment both thin.

8. **FFmpeg 7.x/8.x threading scheduler internals** — The "most complex refactoring in decades" lacks published benchmarks quantifying the pipeline-parallelism gains for realistic filter graphs (e.g., 1-in-4-out ABR ladders) and guidance for tuning the new per-stage thread pools.

9. **Power/energy-per-bit cross-platform comparison** — Only NVENC SFE paper gave energy figures (~1/10th of CPU). No equivalent joules-per-frame data for QSV, AMF, VideoToolbox, or Apple Silicon media engines.

10. **HDR (HDR10/HLG/Dolby Vision) through hardware pipelines** — Scattered anecdotes (one QSV HDR blog) but no systematic coverage of metadata preservation (Mastering Display, CLL) across NVENC/QSV/AMF/VideoToolbox encode paths, tonemapping filter GPU support (tonemap_opencl, zscale on GPU), or 10-bit zero-copy format constraints per platform.

11. **VAAPI vs QSV quality/performance on identical Intel hardware** — Intel teased a comparison article ("Future articles will cover comparisons of VPL vs VA-API") but it was not found. Same silicon, two API paths — which wins and why is undocumented.

12. **Windows-specific zero-copy interop** — d3d11va ↔ CUDA ↔ QSV surface sharing on Windows (mixed-vendor laptops: Intel iGPU + NVIDIA dGPU) has only fragmentary forum coverage; no working command references for cross-device hwmap/hwdownload pipelines.
