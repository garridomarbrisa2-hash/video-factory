# P1 Asset Pipeline Findings

## 1. Video Codec Support — H.264, HEVC, VP9, AV1, ProRes, DNxHD

### 1.1 Codec Alpha Support Matrix

| Codec | Alpha Support | Max Bit Depth | Chroma Subsampling | FFmpeg Encoder | Pixel Format |
|-------|--------------|---------------|-------------------|----------------|--------------|
| H.264 | No | 8-bit (10-bit via High10) | 4:2:0, 4:2:2, 4:4:4 | libx264 | yuv420p, yuv422p, yuv444p |
| HEVC / H.265 | Limited (Alpha layer in spec, poor FFmpeg support) | 10-bit | 4:2:0, 4:2:2, 4:4:4 | libx265 | yuv420p10le, yuv422p10le, yuv444p10le |
| VP9 | Yes | 12-bit | 4:2:0, 4:2:2, 4:4:0, 4:4:4 | libvpx-vp9 | yuva420p, yuv420p10le, yuv420p12le |
| AV1 | No native alpha (workaround via vstack/alphaextract) | 12-bit | 4:2:0, 4:2:2, 4:4:4 | libaom-av1 | yuv420p, yuv420p10le, yuv420p12le |
| ProRes 4444 | Yes | 12-bit (FFmpeg encodes 10-bit) | 4:4:4:4 | prores_ks | yuva444p10le |
| ProRes 422 | No | 10-bit | 4:2:2 | prores_ks, prores_aw | yuv422p10le |
| DNxHD | No | 8-bit | 4:2:2 | dnxhd | yuv422p |
| DNxHR HQX | No | 10-bit / 12-bit | 4:2:2 | dnxhd | yuv422p10le, yuv422p12le |
| DNxHR 444 | No | 10-bit / 12-bit | 4:4:4 | dnxhd | yuv444p10le, yuv444p12le |

### 1.2 H.264 Encoding

```bash
# Standard H.264 encode
ffmpeg -i input.mp4 -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p output.mp4

# Fast encode with high quality
ffmpeg -i input.mp4 -c:v libx264 -preset superfast -tune fastdecode -g 1 -crf 17 output.mp4

# 10-bit H.264 (High10 profile)
ffmpeg -i input.mp4 -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p10le output.mp4
```

### 1.3 HEVC / H.265 Encoding

```bash
# Standard HEVC encode
ffmpeg -i input.mp4 -c:v libx265 -preset slow -crf 20 -pix_fmt yuv420p10le output.mp4

# HEVC with HDR metadata (BT.2020 / PQ)
ffmpeg -i input.mp4 -c:v libx265 -preset slow -crf 20 \
  -x265-params "colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:max-cll=1000,400:master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,0.0050)" \
  -pix_fmt yuv420p10le output.mp4
```

**Note:** HEVC alpha layer support exists in the specification (via auxiliary pictures), but FFmpeg muxing support is incomplete. Apple VideoToolbox encoder supports HEVC with alpha on macOS.

### 1.4 VP9 Encoding with Alpha

```bash
# VP9 with alpha channel (WebM)
ffmpeg -i input.mov -c:v libvpx-vp9 -pix_fmt yuva420p -crf 32 -b:v 0 output.webm

# VP9 two-pass encoding with alpha
ffmpeg -y -i input.mov -pix_fmt yuva420p -an -c:v libvpx-vp9 -crf 45 -b:v 0 \
  -deadline good -threads 4 -lag-in-frames 25 -row-mt 1 -pass 1 -f null /dev/null && \
ffmpeg -y -i input.mov -pix_fmt yuva420p -an -c:v libvpx-vp9 -crf 45 -b:v 0 \
  -deadline good -threads 4 -lag-in-frames 25 -row-mt 1 -pass 2 output.webm

# VP9 10-bit with color metadata
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.png -frames:v 200 -c:v libvpx-vp9 \
  -pix_fmt yuv420p10le -crf 22 -cpu-used 2 -row-mt 1 -quality good -b:v 0 \
  -sws_flags spline+accurate_rnd+full_chroma_int \
  -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" \
  -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
  -y outputfile.mp4
```

### 1.5 AV1 Encoding

```bash
# Standard AV1 encode
ffmpeg -i input.mp4 -c:v libaom-av1 -crf 30 -b:v 0 -cpu-used 4 output.mp4

# AV1 with alpha workaround (vstack alphaextract method)
ffmpeg -y -i input.mov \
  -filter_complex "[0:v]format=pix_fmts=yuva444p[main]; [main]split[main][alpha]; [alpha]alphaextract[alpha]; [main][alpha]vstack" \
  -pix_fmt yuv420p -an -c:v libaom-av1 -cpu-used 3 -crf 45 -pass 1 -f null /dev/null && \
ffmpeg -y -i input.mov \
  -filter_complex "[0:v]format=pix_fmts=yuva444p[main]; [main]split[main][alpha]; [alpha]alphaextract[alpha]; [main][alpha]vstack" \
  -pix_fmt yuv420p -an -c:v libaom-av1 -cpu-used 3 -crf 45 -pass 2 -movflags +faststart output.mp4
```

### 1.6 ProRes Encoding

```bash
# ProRes 422 HQ (no alpha)
ffmpeg -i input.mp4 -c:v prores_ks -profile:v 3 -vendor apl0 -bits_per_mb 8000 \
  -pix_fmt yuv422p10le output.mov

# ProRes 4444 with alpha
ffmpeg -i input.mp4 -c:v prores_ks -profile:v 4 -vendor apl0 -bits_per_mb 8000 \
  -pix_fmt yuva444p10le output.mov

# ProRes 4444 XQ
ffmpeg -i input.mp4 -c:v prores_ks -profile:v 5 -vendor apl0 \
  -pix_fmt yuva444p10le output.mov

# ProRes from image sequence with color management
ffmpeg -r 24 -start_number 100 -i inputfile.%04d.png \
  -pix_fmt yuv422p10le -vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" \
  -frames:v 100 -c:v prores_ks -profile:v 3 -vendor apl0 \
  -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
  -y output.mov
```

### 1.7 DNxHD / DNxHR Encoding

```bash
# DNxHD 1080p 110Mbps
ffmpeg -i input.mp4 -c:v dnxhd -b:v 110M -pix_fmt yuv422p -c:a pcm_s16le output.mxf

# DNxHR HQ 8-bit
ffmpeg -i input.mp4 -c:v dnxhd -profile:v dnxhr_hq -pix_fmt yuv422p output.mxf

# DNxHR HQX 10-bit
ffmpeg -i input.mp4 -c:v dnxhd -profile:v dnxhr_hqx -pix_fmt yuv422p10le output.mxf

# DNxHR 444 10-bit
ffmpeg -i input.mp4 -c:v dnxhd -profile:v dnxhr_444 -pix_fmt yuv444p10le output.mxf
```

### 1.8 Lossless / Intermediate Codecs with Alpha

```bash
# FFV1 lossless with alpha (best for intermediates)
ffmpeg -framerate 60 -i out%04d.png -c:v ffv1 out.mkv

# QuickTime Animation (RLE) with alpha
ffmpeg -framerate 60 -i out%04d.png -c:v qtrle out.mov
```

FFV1 supported alpha pixel formats: yuva420p, yuva422p, yuva444p, yuva420p10le, yuva422p10le, yuva444p10le, yuva444p16le, rgba64le, etc.

---

## 2. Image Format Handling — PNG, JPEG, WebP, TIFF, EXR, DPI/Resolution

### 2.1 Format Capabilities

| Format | Alpha | Max Bit Depth | HDR Support | DPI Metadata | FFmpeg Decoder | FFmpeg Encoder |
|--------|-------|---------------|-------------|--------------|----------------|----------------|
| PNG | Yes | 16-bit | No | No | png | png |
| JPEG | No | 8-bit | No | Yes (JFIF) | mjpeg | mjpeg |
| WebP | Yes | 8-bit | No | No | libwebp | libwebp |
| TIFF | Yes | 32-bit float | Yes | Yes | tiff | tiff |
| EXR | Yes | 32-bit float | Yes | No | exr | exr |
| BMP | Yes (32-bit) | 8-bit | No | Yes | bmp | bmp |
| DPX | Yes | 16-bit | Yes | No | dpx | dpx |

### 2.2 DPI / Resolution Metadata

FFmpeg does not universally read or write DPI metadata for all formats. For TIFF output, use the `-dpi` option:

```bash
# TIFF with DPI setting (must be placed before output file)
ffmpeg -i input.tif -vf "scale=6974:4919:force_original_aspect_ratio=decrease,pad=7016:4961:(ow-iw)/2:(oh-ih)/2:color=white,format=rgb24" -dpi 300 output.tif
```

**Common problem:** FFmpeg-generated TIFFs default to 72 DPI regardless of source. Always explicitly set `-dpi` for print workflows.

### 2.3 Image Conversion Examples

```bash
# PNG to WebP
ffmpeg -i input.png -c:v libwebp -quality 90 output.webp

# Video frame to high-quality PNG
ffmpeg -ss 00:01:10 -i input.mp4 -vframes 1 -vf "format=rgb24" output.png

# EXR to PNG (tone-mapped)
ffmpeg -i input.exr -vf "zscale=transfer=linear,tonemap=hable,zscale=transfer=bt709,format=rgb24" output.png

# TIFF to PNG with DPI preservation
ffmpeg -i input.tif -vf "format=rgb24" output.png
```

---

## 3. Color Management — BT.601 vs BT.709 vs BT.2020, colormatrix, zscale, tonemap

### 3.1 Color Space Standards

| Standard | Use Case | Gamut | Transfer Function | Bit Depth |
|----------|----------|-------|-------------------|-----------|
| BT.601 | SD video (480i, 576i) | Limited | Gamma (~2.4) | 8-bit |
| BT.709 | HD video (720p, 1080p) | Limited | Gamma (~2.4) | 8-bit / 10-bit |
| BT.2020 | UHD / HDR | Wide | PQ (ST 2084) or HLG | 10-bit / 12-bit |

**Key distinction:** BT.2020 is a color *gamut* (primaries), while PQ/HLG are *transfer functions*. HDR content typically uses BT.2020 gamut + PQ transfer. SDR content can use BT.2020 gamut with gamma transfer (WCG without HDR).

### 3.2 Color Metadata Signaling

Always explicitly tag color metadata to avoid player misinterpretation:

```bash
# Tag output as BT.709 SDR
ffmpeg -i input.mp4 -c:v libx264 -crf 18 \
  -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
  output.mp4

# Tag output as BT.2020 HDR10
ffmpeg -i input.mp4 -c:v libx265 -crf 20 \
  -color_range tv -colorspace bt2020nc -color_primaries bt2020 -color_trc smpte2084 \
  output.mp4
```

### 3.3 colormatrix Filter (Legacy / Simple Conversions)

```bash
# BT.709 to BT.601 conversion
ffmpeg -i input.mp4 -vf "colormatrix=bt709:bt601" output.mp4

# BT.601 to BT.709
ffmpeg -i input.mp4 -vf "colormatrix=bt601:bt709" output.mp4
```

**Limitation:** colormatrix only handles 8-bit and does not support BT.2020 or linear light.

### 3.4 colorspace Filter (More Advanced)

```bash
# BT.709 to BT.601 with colorspace filter
ffmpeg -i input.mp4 -vf "colorspace=bt601:itur709:iall=bt709:fast=1" output.mp4
```

### 3.5 zscale Filter (Recommended for HDR / High Bit Depth)

Requires FFmpeg compiled with `--enable-libzimg`.

```bash
# Convert to linear light
zscale=transfer=linear:npl=100

# Convert primaries to BT.709
zscale=primaries=bt709

# Convert back to BT.709 gamma, limited range
zscale=transfer=bt709:matrix=bt709:range=tv
```

### 3.6 HDR to SDR Tone Mapping

#### CPU Path (zscale + tonemap)

```bash
# Full HDR to SDR conversion chain
ffmpeg -i hdr_input.mp4 -vf \
  "zscale=transfer=linear:npl=100,format=gbrpf32le,zscale=primaries=bt709,tonemap=tonemap=hable:desat=0,zscale=transfer=bt709:matrix=bt709:range=tv,format=yuv420p" \
  -c:v libx264 -crf 18 sdr_output.mp4
```

**Tone mapping operators:**
- `hable` — Filmic curve, good shadow/highlight retention
- `reinhard` — Brighter output, may lose highlight detail
- `mobius` — Smooth highlight roll-off
- `clip` — Hard clip (fastest, worst quality)
- `linear` — Simple linear scaling
- `gamma` — Logarithmic fit

**Recommended:** `hable` with `desat=0` for most content.

#### GPU Path (OpenCL)

```bash
# OpenCL accelerated tone mapping
ffmpeg -hwaccel nvdec -init_hw_device opencl=ocl -filter_hw_device ocl \
  -i input.mkv -vf \
  "format=p010,hwupload,tonemap_opencl=t=bt709:r=tv:p=bt709:m=bt709:tonemap=hable:format=p010,hwdownload,format=p010" \
  output.mp4
```

#### GPU Path (libplacebo / Vulkan)

```bash
# libplacebo with BT.2390 tone mapping
ffmpeg -i input.mp4 -vf \
  "libplacebo=tonemapping=bt.2390:colorspace=bt709:color_primaries=bt709:color_trc=bt709:format=yuv420p" \
  -c:v libx264 -crf 18 output.mp4
```

### 3.7 Common Color Problems and Solutions

| Problem | Cause | Solution |
|---------|-------|----------|
| Washed out colors | HDR content played as SDR without tone mapping | Use zscale + tonemap chain |
| Color shift / green tint | Wrong color matrix assumption | Explicitly set `-colorspace` and use `scale=in_color_matrix=bt709:out_color_matrix=bt709` |
| Banding in gradients | 8-bit output with wide gamut | Use 10-bit output (`yuv420p10le`) |
| Too dark after conversion | Forcing PQ curve into gamma without remapping | Proper linearization + tone mapping |
| ProRes colors wrong in NLE | FFmpeg not writing correct color matrix | Add `-vf scale=in_color_matrix=bt709:out_color_matrix=bt709` |

---

## 4. Alpha Channel Workflows

### 4.1 alphaextract / alphamerge

Extract alpha to separate grayscale video, or merge grayscale back as alpha:

```bash
# Extract alpha channel to grayscale video
ffmpeg -i input.mov -vf "alphaextract" alpha_only.mp4

# Merge separate alpha video back
ffmpeg -i video.mp4 -i alpha.mp4 -filter_complex "[0:v][1:v]alphamerge" output.mov

# Full pipeline: separate, process, merge
ffmpeg -i input.mov -filter_complex \
  "[0:v]alphaextract[alpha]; [0:v]format=yuv420p[main]; [main][alpha]alphamerge" \
  -c:v qtrle output.mov
```

**Important:** `alphamerge` operates on frame sequences without timestamps and terminates when either input ends. Use `overlay` for image overlays instead.

### 4.2 Premultiply / Unpremultiply

```bash
# Unpremultiply (straighten) using second input as alpha
ffmpeg -i foreground.mov -i alpha.mp4 -filter_complex "[0:v][1:v]unpremultiply" output.mov

# Premultiply using alpha from same stream
ffmpeg -i input.mov -vf "premultiply=inplace=1" output.mov
```

**Note:** Both streams must have same dimensions and pixel format for `unpremultiply`.

### 4.3 Chromakey / Colorkey

```bash
# Basic green screen removal
ffmpeg -i input.mp4 -vf "chromakey=green:0.1:0.2" output.mov

# Colorkey with similarity and blend
ffmpeg -i background.mp4 -i greenscreen.mp4 -filter_complex \
  "[1:v]colorkey=0x3BBD1E:0.3:0.2[ckout];[0:v][ckout]overlay[out]" \
  -map "[out]" output.mp4

# CUDA accelerated chromakey
ffmpeg -hwaccel cuda -hwaccel_output_format cuda -i input_green.mp4 \
  -hwaccel cuda -hwaccel_output_format cuda -i base_video.mp4 \
  -init_hw_device cuda -filter_complex \
  "[0:v]chromakey_cuda=0x25302D:0.1:0.12:1[overlay_video]; [1:v]scale_cuda=format=yuv420p[base]; [base][overlay_video]overlay_cuda" \
  -an -sn -c:v h264_nvenc -cq 20 output.mp4
```

**Parameters:**
- `colorkey=color:similarity:blend` — similarity 0.01-1.0, blend 0.0-1.0
- `chromakey=color:similarity:blend:yuv=1` — process in YUV space

### 4.4 Geq (Generic Equation) for Custom Alpha

```bash
# Create circular mask
ffmpeg -f lavfi -i "color=red:size=228x228,format=yuva420p,geq=lum='p(X,Y)':a='if(lte(hypot(X-(W/2),Y-(H/2)),100),255,0)'" \
  -i map.mp4 -filter_complex "alphaextract[a];[a]alphamerge" -c:v libvpx-vp9 masked.webm
```

### 4.5 Alpha Preservation Best Practices

1. **Always verify alpha exists:** `ffprobe -v quiet -print_format json -show_streams input.mov` — look for `pix_fmt` containing `a` (e.g., `rgba`, `yuva420p`, `yuva444p10le`)
2. **Use explicit format filters:** `format=rgba` or `format=yuva420p` before alpha-sensitive operations
3. **Avoid implicit conversions:** Many filters drop alpha; insert `format` explicitly
4. **Choose correct codec/container:** ProRes 4444 (.mov), VP9 (.webm), FFV1 (.mkv), QTRLE (.mov), PNG sequence

---

## 5. Image Sequences

### 5.1 Pattern Syntax

```bash
# %03d = 3-digit zero-padded (000, 001, 002...)
ffmpeg -i image-%03d.png output.mp4

# %04d = 4-digit zero-padded (0000, 0001...)
ffmpeg -i image-%04d.png output.mp4

# %d = no padding (1, 2, 3...)
ffmpeg -i image-%d.png output.mp4

# Glob pattern (non-sequential)
ffmpeg -framerate 10 -pattern_type glob -i "*.jpg" -c:v libx264 -pix_fmt yuv420p output.mp4
```

### 5.2 Start Number and Numbering

```bash
# Start from frame 100
ffmpeg -start_number 100 -i image-%03d.png output.mp4

# Start from frame 501, read 60 seconds worth
ffmpeg -start_number 501 -framerate 30 -t 60.0 -i input1.%04d.jpg output.mp4
```

**Rule:** FFmpeg expects consecutive numbering. If files are `img-000.png, img-001.png, img-005.png`, it stops at the gap.

### 5.3 Framerate Interpretation

```bash
# Input framerate (how fast to read images)
ffmpeg -framerate 24 -i img%03d.png output.mp4

# Different input and output rates (duplicates/drops frames)
ffmpeg -framerate 1/5 -i img%03d.png -c:v libx264 -r 30 -pix_fmt yuv420p out.mp4

# Default is 25 fps if omitted
ffmpeg -i img%03d.png output.mp4
```

**Best practice:** Use `-framerate` before `-i` for input rate, `-r` after for output rate.

### 5.4 Looping

```bash
# Loop single image for 30 minutes
ffmpeg -loop 1 -i image.png -c:v libx264 -t 00:30:00 -pix_fmt yuv420p output.mp4

# Loop image sequence infinitely with duration limit
ffmpeg -loop 1 -i "input_%04d.jpg" -c:v libx264 -t 00:30:00 -r 25 -pix_fmt yuv420p out.mp4

# Loop first frame of sequence for 5 seconds
ffmpeg -start_number 501 -framerate 30 -t 60.0 -i input1.%04d.jpg \
  -filter_complex "loop=149:1:0[bgheld5]" out.mp4
```

### 5.5 Time Remapping / Select Frames

```bash
# Use every 3rd image, retime to 30fps
ffmpeg -framerate 30 -i img%03d.png -vf "select='not(mod(n,3))',setpts=N/30/TB" -crf 23 output.mp4

# Skip first 2000 frames
ffmpeg -framerate 40 -i img%03d.png -vf "select='gt(n,2000)',setpts=N/30/TB" -crf 23 -pix_fmt yuv420p output.mp4

# Reverse sequence
ffmpeg -framerate 30 -i img%03d.png -vf "reverse" output.mp4
```

### 5.6 Video to Image Sequence

```bash
# Extract all frames
ffmpeg -i video.webm image-%03d.png

# Extract 1 frame per second
ffmpeg -i video.mp4 -r 1 -s 1920x1080 -f image2 foo-%03d.jpeg

# Extract specific frame count
ffmpeg -i video.mp4 -frames:v 100 image-%03d.png

# Extract with scaling and padding
ffmpeg -i video.mp4 -vf "fps=20,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p" out%d.png
```

---

## 6. Asset Validation and QC

### 6.1 ffprobe JSON Output

```bash
# Full metadata dump
ffprobe -v quiet -print_format json -show_format -show_streams input.mp4

# Compact output for scripting
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,pix_fmt,color_space,color_transfer,color_primaries -of csv=p=0 input.mp4

# Specific fields
ffprobe -v error -show_entries format=duration,size,bit_rate -of default=noprint_wrappers=1 input.mp4

# Frame-level analysis (first 10 frames)
ffprobe -v error -select_streams v:0 -show_entries frame=pkt_pts_time,pict_type -of csv=p=0 -read_intervals "%+10" input.mp4
```

### 6.2 Corruption Detection

```bash
# Decode entire file, report errors
ffmpeg -v error -i input.mp4 -f null - 2>error.log

# Check for non-monotonic timestamps
ffprobe -v error -show_entries frame=pkt_dts_time,pkt_pts_time -of csv=p=0 input.mp4 | sort -n

# Verify bitstream with h264_metadata (if H.264)
ffmpeg -i input.mp4 -c copy -bsf:v h264_metadata=tick_rate=50 -f null -
```

### 6.3 QC Filters

#### blackdetect

```bash
# Detect black frames >2 seconds
ffmpeg -i input.mp4 -vf "blackdetect=d=2:pix_th=0.00" -an -f null -

# Output to file via metadata
ffmpeg -i input.mp4 -vf "blackdetect=d=2:pix_th=0.00,metadata=mode=print:file=black.txt" -an -f null -
```

**Output format:** `blackdetect: black_start:0 black_end:2.5 black_duration:2.5`

#### freezedetect

```bash
# Detect frozen video >2 seconds
ffmpeg -i input.mp4 -vf "freezedetect=n=-60dB:d=2" -an -f null -

# Output to file
ffmpeg -i input.mp4 -vf "freezedetect=n=-60dB:d=2,metadata=mode=print:file=freeze.txt" -an -f null -
```

**Metadata keys:** `lavfi.freezedetect.freeze_start`, `lavfi.freezedetect.freeze_duration`, `lavfi.freezedetect.freeze_end`

#### silencedetect

```bash
# Detect silence below -50dB for >0.5 seconds
ffmpeg -i input.mp4 -af "silencedetect=noise=-50dB:d=0.5" -f null -

# Output to file
ffmpeg -i input.mp4 -af "silencedetect=noise=-20dB:d=0.5,ametadata=mode=print:file=silence.txt" -f null -
```

**Metadata keys:** `lavfi.silence_start`, `lavfi.silence_end`, `lavfi.silence_duration`

#### Combined QC Scan

```bash
# Scan for black, freeze, and silence simultaneously
ffmpeg -i input.mp4 \
  -vf "blackdetect=d=1:pix_th=0.10,freezedetect=n=-50dB:d=1" \
  -af "silencedetect=noise=-40dB:d=1" \
  -f null - 2>qc_report.txt
```

### 6.4 Advanced QC with signalstats

```bash
# Check for out-of-gamut colors (broadcast safe)
ffprobe -f lavfi -i "movie=input.mp4,signalstats=tout" -show_frames

# Read only first 1% of file for quick check
ffprobe -f lavfi -i "movie=input.mp4,signalstats=tout" -read_intervals %00:01 -show_frames
```

**Key metadata:** `lavfi.signalstats.TOUT` (temporal outliers), `lavfi.signalstats.SATMAX`, `lavfi.signalstats.YMAX`

### 6.5 Automation Script Pattern

```python
import subprocess
import json
import re

def qc_scan(filepath):
    # Basic metadata
    probe = subprocess.run([
        'ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_format', '-show_streams', filepath
    ], capture_output=True, text=True)
    meta = json.loads(probe.stdout)
    
    # QC filters
    qc = subprocess.run([
        'ffmpeg', '-i', filepath,
        '-vf', 'blackdetect=d=1:pix_th=0.10,freezedetect=n=-50dB:d=1',
        '-af', 'silencedetect=noise=-40dB:d=1',
        '-f', 'null', '-'
    ], capture_output=True, text=True)
    
    # Parse QC results
    black = re.findall(r'blackdetect:.*?black_start:(\S+).*?black_end:(\S+)', qc.stderr)
    freeze = re.findall(r'lavfi.freezedetect.freeze_start=(\S+)', qc.stderr)
    silence = re.findall(r'silence_start:(\S+)', qc.stderr)
    
    return {
        'metadata': meta,
        'black_segments': black,
        'freeze_timestamps': freeze,
        'silence_timestamps': silence
    }
```

---

## 7. Normalization Filter Chains

### 7.1 Universal Normalization Chain

```bash
# Normalize any input to 1080p30, BT.709, yuv420p, faststart
ffmpeg -i input.mov -vf \
  "fps=30,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,format=yuv420p" \
  -c:v libx264 -preset slow -crf 18 \
  -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
  -movflags +faststart output.mp4
```

### 7.2 Scale and Pad (Letterbox)

```bash
# Fit inside 1280x720 with black bars
ffmpeg -i input -vf \
  "scale=w=1280:h=720:force_original_aspect_ratio=1,pad=1280:720:(ow-iw)/2:(oh-ih)/2" \
  output.mp4
```

### 7.3 Scale and Crop (Fill)

```bash
# Fill 1280x720, crop excess
ffmpeg -i input -vf \
  "scale=w=1280:h=720:force_original_aspect_ratio=2,crop=1280:720" \
  output.mp4
```

### 7.4 SAR / DAR Correction

```bash
# Force square pixels (SAR 1:1)
ffmpeg -i input -vf "setsar=1" output.mp4

# Set display aspect ratio to 16:9
ffmpeg -i input -vf "setdar=16/9" output.mp4
```

---

## 8. Common Problems and Solutions

| Problem | Symptom | Solution |
|---------|---------|----------|
| Alpha lost after filter | Output has no transparency | Insert `format=rgba` or `format=yuva420p` before/after filter |
| Wrong colors in ProRes | Colors shifted in NLE | Add `-vf scale=in_color_matrix=bt709:out_color_matrix=bt709` |
| TIFF DPI wrong | Print shop rejects file | Use `-dpi 300` before output filename |
| Image sequence stops early | Missing frames in output | Check for numbering gaps; use `-start_number` or glob |
| HDR looks washed out | Colors dull after conversion | Use full zscale + tonemap chain, not just `format=yuv420p` |
| Black bars too large | Aspect ratio wrong | Use `force_original_aspect_ratio` and verify `setsar=1` |
| VP9 alpha not working in Safari | Transparency missing | Safari supports VP9 alpha only in WebM, not MP4; use HEVC for Safari |
| FFmpeg can't read EXR | Decoder error | Ensure FFmpeg compiled with `--enable-libopenexr` or use TIFF/PNG intermediate |
| DNxHD bitrate error | Encoder rejects settings | Must specify exact bitrate for resolution/framerate combo |
| zscale not found | Filter missing | Install FFmpeg build with `--enable-libzimg` |

---

## GAPS REQUIRING PERPLEXITY DEEP RESEARCH

1. **HEVC Alpha Layer Muxing:** FFmpeg ticket #9088 indicates incomplete support for HEVC bitstreams with alpha layers in MP4. Need current status (2026), whether videotoolbox HEVC alpha can be remuxed to MP4, and if any third-party tools (mp4box, gpac) handle this correctly.

2. **AV1 Alpha Channel Specification:** AV1 spec supports alpha via auxiliary streams, but FFmpeg implementation status is unclear. Need deep research on whether libaom-av1 or librav1e will support native alpha, and current workarounds beyond vstack.

3. **EXR Deep Data / Cryptomatte:** FFmpeg EXR decoder supports basic RGBA, but deep data (deep compositing) and Cryptomatte metadata support is undocumented. Need research on whether FFmpeg can read/write deep EXR or if external tools (OpenImageIO, Nuke) are required.

4. **Dolby Vision Profile 5 / 8 / 9:** FFmpeg can decode some Dolby Vision profiles, but encoding support is non-existent. Need current status of open-source Dolby Vision encoding (e.g., dovi_tool integration), and whether FFmpeg can preserve DV metadata in HEVC remux.

5. **BT.2020 to P3-D65 Conversion:** Common for HDR deliverables, but zscale does not natively support P3 primaries. Need research on whether libplacebo or custom 3D LUTs are the only path, and exact zscale/libplacebo syntax for P3 output.

6. **ACES Workflow Integration:** FFmpeg can read ACES-encoded EXR, but native ACES RRT/ODT support is missing. Need research on whether OpenColorIO integration is planned, and current best practices for ACES proxy generation with FFmpeg.

7. **IMF / MXF AS-11 Validation:** FFmpeg has basic MXF support, but broadcast IMF validation (SMPTE ST 2067) requires specialized tools. Need research on whether FFmpeg can validate IMF packages or if tools like Photon/Netflix IMF validator are mandatory.

8. **WebP Animation with Alpha:** FFmpeg supports WebP encoding, but animated WebP with alpha channel support is undocumented. Need research on whether `libwebp` encoder in FFmpeg supports animated WebP with alpha, and browser compatibility.

9. **12-bit ProRes 4444 XQ:** FFmpeg's prores_ks encoder is limited to 10-bit. Need research on whether 12-bit encoding is on the roadmap, or if alternative encoders (e.g., Apple Compressor, Adobe Media Encoder) are the only option.

10. **HDR10+ / Dynamic Metadata:** FFmpeg can pass through HDR10+ metadata in some containers, but dynamic metadata generation (ST 2094-40) is unsupported. Need research on whether hdr10plus_tool or similar can inject metadata into FFmpeg-encoded HEVC streams.

11. **VVC / H.266 Support:** FFmpeg has experimental VVC decoder (vvdec) but no encoder. Need research on encoder availability timeline and whether VVC will support alpha in the same way as HEVC.

12. **FFmpeg Vulkan Compute Filters:** New Vulkan filters (scale_vulkan, chromaber_vulkan, overlay_vulkan) are emerging. Need research on whether these support alpha channel processing and HDR tone mapping with better performance than OpenCL paths.

---

*Research compiled via Tavily search. Sources include FFmpeg official documentation, Stack Overflow, Video Production Stack Exchange, Super User, ORI Encoding Guidelines, and various technical blogs. All commands verified against FFmpeg 6.x/7.x documentation where possible.*
