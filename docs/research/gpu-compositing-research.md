# GPU-Accelerated Video Compositing: Deep Research

> Research date: 2026-07-21
> Target: Python/Node.js video automation pipeline on Windows with RTX 3060
> Status: Complete

---

## 1. How Professional Editors Use GPU

### Adobe Premiere Pro — Mercury Playback Engine

The Mercury Playback Engine is **not** a pure GPU renderer. It's a hybrid CPU+GPU architecture:

- **64-bit multithreaded CPU** handles timeline orchestration, codec I/O, audio, and non-GPU effects
- **GPU (CUDA on NVIDIA, OpenCL on AMD, Metal on Apple)** handles a specific subset of operations: color correction, blending modes, scaling, transitions, certain effects
- GPU processing is done in **32-bpc linear color space** — pixel values are converted from YUV to linear RGB float before GPU shader execution
- The GPU renders layers as **textures**, composites them via fragment shaders, and reads back for encoding
- Premiere does NOT do a "zero-copy" pipeline — frames shuttle between CPU and GPU constantly. The CPU decodes (usually via its own codec engine), uploads to GPU for effects, downloads for encoding (or passes to NVENC/AMF as a separate encode step)

**Key architecture pattern:** The CPU is the orchestrator. The GPU is a coprocessor for pixel-parallel operations. Each layer is a texture. Effects are shader passes over textures. Compositing happens in the fragment shader.

### DaVinci Resolve

- Uses **CUDA on NVIDIA**, OpenCL on AMD (deprecated in favor of Metal on macOS)
- More aggressively GPU-centric than Premiere — color grading, Fusion effects, and many transitions run entirely on GPU
- Resolve 17+ requires CUDA 11+; falls back to OpenCL if NVIDIA driver doesn't support it (with significant performance loss)
- Fusion (node compositor) renders each node's output as a GPU texture, chains them in VRAM
- Neural engine features use CUDA cores directly

**Key difference from Premiere:** Resolve tries to keep the entire image pipeline on GPU from decode to display, only falling back to CPU for unsupported codecs/operations.

### Filmora & CapCut

- **Filmora** (Wondershare): Uses OpenGL/D3D for GPU-accelerated preview rendering. Effects engine is shader-based. GPU acceleration for transitions, color, and compositing. Actual export encode typically uses Intel QSV/NVENC/AMF via OS media APIs.
- **CapCut** (ByteDance): Built on a custom cross-platform engine. Mobile uses GPU extensively (OpenGL ES/Metal/Vulkan). Desktop version uses ANGLE (OpenGL on D3D11) for compositing. Layers are textures, effects are shader passes, transitions are blend operations in fragment shaders.

**Common architecture pattern across all four:**
```
Timeline (CPU orchestrator)
    │
    ├─→ Layer 1: video frame → GPU texture (via hwdecode or CPU upload)
    ├─→ Layer 2: image → GPU texture
    ├─→ Layer 3: text → GPU texture (rasterized by FreeType/CPU, uploaded once)
    │
    ▼
Fragment Shader (per frame):
    for each layer:
        sample texture
        apply transform (position, scale, rotation, opacity)
        blend (normal, add, multiply, etc.)
    output to framebuffer
    │
    ▼
Encoder (NVENC / AMF / QSV / x264)
```

---

## 2. FFmpeg GPU Filters

### CUDA Filters (NVIDIA)

FFmpeg has **9 native CUDA filters** that operate entirely on GPU frames:

| Filter | Description | Tier |
|--------|------------|------|
| `scale_cuda` | Scale/resize + pixel format conversion | T1 |
| `overlay_cuda` | Overlay one video on another | T1 |
| `pad_cuda` | Add padding/borders | T1 |
| `chromakey_cuda` | Chroma keying (green screen) | T1 |
| `colorspace_cuda` | Color space conversion | T1 |
| `bilateral_cuda` | Edge-preserving smoothing | T2 |
| `bwdif_cuda` | Deinterlacing (bwdif algorithm) | T2 |
| `yadif_cuda` | Deinterlacing (yadif algorithm) | T2 |
| `thumbnail_cuda` | Select representative frame | T2 |

Plus **NPP-based filters** (require `--enable-libnpp`):
- `scale_npp` — scaling + format conversion
- `scale2ref_npp` — scale based on reference video
- `sharpen_npp` — image sharpening
- `transpose_npp` — transpose/rotate

**Requirements:** FFmpeg built with `--enable-cuda-nvcc` or `--enable-cuda-llvm` + NVIDIA CUDA Toolkit installed.

### OpenCL Filters (Cross-platform)

| Filter | Description |
|--------|------------|
| `overlay_opencl` | Overlay compositing |
| `xfade_opencl` | Cross-fade transitions |
| `tonemap_opencl` | HDR→SDR tone mapping |
| `avgblur_opencl` | Average blur |
| `boxblur_opencl` | Box blur |
| `colorkey_opencl` | Color keying |
| `convolution_opencl` | Custom convolution |
| `deshake_opencl` | Video stabilization |
| `dilation_opencl` | Morphological dilation |
| `erosion_opencl` | Morphological erosion |
| `nlmeans_opencl` | NL-means denoising |
| `pad_opencl` | Padding |
| `prewitt_opencl` | Prewitt edge detection |
| `program_opencl` | Custom OpenCL kernel |
| `remap_opencl` | Pixel remapping |
| `roberts_opencl` | Roberts edge detection |
| `sobel_opencl` | Sobel edge detection |
| `unsharp_opencl` | Unsharp masking |

**Requirements:** FFmpeg built with `--enable-opencl`.

### Vulkan/libplacebo Filters

| Filter | Description |
|--------|------------|
| `libplacebo` | Full GPU-accelerated processing (Vulkan/OpenGL/D3D11) |

`libplacebo` is the most powerful GPU filter in FFmpeg. It supports:
- High-quality scaling (Lanczos, EWA, spline36, etc.)
- HDR tone mapping (PQ/HLG → SDR)
- Color space conversion
- Debanding
- Film grain synthesis
- Custom shader injection
- Multi-input compositing (N inputs placed/blended in output frame)
- Frame interpolation (low FPS → smooth 60fps)

**Requirements:** FFmpeg built with `--enable-vulkan --enable-libshaderc --enable-libplacebo`.

### Can FFmpeg composite text/images using GPU filters without CPU download?

**For images: YES.** The full GPU pipeline works:

```bash
ffmpeg \
  -hwaccel cuda -hwaccel_output_format cuda -i main.mp4 \
  -hwaccel cuda -hwaccel_output_format cuda -i overlay.png \
  -filter_complex "
    [0:v]scale_cuda=1920:1080[main];
    [1:v]scale_cuda=640:360[ovr];
    [main][ovr]overlay_cuda=x=100:y=100
  " \
  -c:v h264_nvenc -preset p4 output.mp4
```

This decodes on GPU (NVDEC), scales on GPU, composites on GPU, and encodes on GPU (NVENC) — **zero CPU frame copies**.

**For text: NO (with a major caveat).** `drawtext` is CPU-only. There is no `drawtext_cuda` or `drawtext_opencl`. The workaround:

1. **Pre-render text to transparent PNG/WebM** on CPU (one-time cost), then upload as image overlay via `overlay_cuda` — this is the standard approach for automation pipelines
2. Use `hwdownload → drawtext → hwupload_cuda` — but this defeats the purpose (PCIe round-trip per frame)
3. Use `libplacebo` with custom shaders for procedural text (limited, no font rasterization)

**The recommended pattern for GPU text:**
```
Text (Python/PIL/FreeType) → RGBA PNG → hwupload_cuda → overlay_cuda → NVENC
```

Text rasterization happens **once per unique text**, not per frame. For animated text, pre-render key positions or use multiple overlays with `enable` expressions.

### Can you chain decode→scale→overlay→encode entirely on GPU?

**YES**, with caveats:

```bash
ffmpeg \
  -hwaccel cuda -hwaccel_output_format cuda -i input1.mp4 \
  -hwaccel cuda -hwaccel_output_format cuda -i input2.mp4 \
  -init_hw_device cuda \
  -filter_complex "
    [0:v]scale_cuda=1920:1080[main];
    [1:v]scale_cuda=480:270,pip[overlay];
    [main][overlay]overlay_cuda=x=W-w-20:y=H-h-20[out]
  " \
  -map "[out]" -c:v h264_nvenc -preset p4 -cq 20 output.mp4
```

**Caveats:**
- Both inputs must decode to CUDA frames (h264_cuvid, hevc_cuvid, etc.)
- Pixel formats must match for `overlay_cuda` (use `scale_cuda=format=yuv420p` or `scale_cuda=format=nv12` to normalize)
- Some codecs (VP9, AV1) may not have CUDA decoders on all GPUs
- Complex filter graphs may need `hwdownload`/`hwupload` bridges for CPU-only filters (like `drawtext`, `ass`, `xfade`)

---

## 3. MLT Framework (Shotcut, Kdenlive)

MLT's GPU support is **experimental and largely CPU-based**:

- MLT core processes frames in CPU memory (YUV422 internally)
- The `movit` module integrates [Movit](https://movit.sesse.net/) — a GLSL-based video processing library
- Movit applies effects via GLSL shaders on GPU: color grading, blur, glow, deinterlacing, rescaling
- The `glsl.manager` filter initializes the OpenGL subsystem
- **BUT:** frames are still decoded on CPU, uploaded to GPU for effects, downloaded back for compositing. There is no zero-copy GPU pipeline.
- Shotcut 24.x has improved GPU effects but still renders most compositing on CPU
- The `consumer_qglsl` module provides OpenGL display, not GPU-accelerated rendering

**Verdict:** MLT is **not** a viable GPU compositing engine. It's a CPU-based timeline with optional GPU shader effects bolted on. Do not use for high-throughput automation.

---

## 4. GStreamer GPU Compositing

GStreamer has the most mature GPU compositing ecosystem:

### `glvideomixer` (OpenGL)
- Composites N video streams using OpenGL
- Each input is a GL texture; compositing happens in fragment shader
- Supports position (xpos, ypos), size (width, height), z-order, alpha per input
- Works with `glupload` to upload CPU frames to GPU textures
- Cross-platform (Windows, Linux, macOS)

```bash
gst-launch-1.0 \
  glvideomixer name=mix sink_0::xpos=0 sink_0::ypos=0 sink_1::xpos=960 sink_1::ypos=540 ! \
  glimagesink \
  videotestsrc ! video/x-raw,format=RGBA ! glupload ! mix.sink_0 \
  videotestsrc pattern=12 ! video/x-raw,format=RGBA ! glupload ! mix.sink_1
```

### `nvcompositor` (NVIDIA Jetson)
- Jetson-specific, uses VIC (Video Image Compositor) hardware
- Fixed-function hardware compositor — not CUDA
- Extremely efficient on Jetson but **not available on desktop GPUs**

### `cudamix` / `nvenc` plugins (Desktop NVIDIA)
- GStreamer has `nvdec` and `nvenc` plugins for hardware decode/encode
- `cudaconvert` for CUDA-based format conversion
- `cudascale` for CUDA-based scaling
- But **no general-purpose CUDA compositor plugin** on desktop — you'd chain decode→convert→mix→encode using GL or CPU compositor

### `compositor` (CPU, default)
- The default `compositor` element is CPU-based
- Supports alpha blending, cropping, positioning
- Not GPU-accelerated

**Verdict for RTX 3060 + Windows:** GStreamer's `glvideomixer` is viable for real-time compositing. Python bindings via `gi` (PyGObject) work on Windows. But GStreamer's Windows GPU support is less mature than on Linux. Consider this a secondary option.

---

## 5. mpv/vlc Shader Approach

### mpv GLSL User Shaders

mpv has a powerful user shader system (`--glsl-shader`) that allows injecting custom GLSL fragment shaders at arbitrary points in the rendering pipeline:

```glsl
//!HOOK MAIN
//!BIND HOOKED
//!DESC Custom Overlay

vec4 hook() {
    vec4 base = HOOKED_tex(HOOKED_pos);
    // Custom compositing logic here
    return base;
}
```

**Capabilities:**
- Access to intermediate textures at any pipeline stage
- Custom fragment shader logic per frame
- Can sample multiple textures (via `//!BIND`)
- Can output to different sizes (via `//!WIDTH`/`//!HEIGHT`)
- Conditional execution (via `//!WHEN`)
- Save/load textures (via `//!SAVE`/`//!TEXTURE`)

**Limitations for video compositing:**
- mpv is a **player**, not a compositor. Shaders operate on the video being played, not on multiple independent layers
- No built-in support for loading external images as textures in shaders (possible via `//!TEXTURE` but awkward)
- No timeline concept — shaders are stateless per-frame
- No NVENC encoding integration — mpv renders to screen, not to file
- Text rendering would require pre-rasterized texture atlas + custom sampling logic

**Verdict:** mpv's shader system is powerful for per-frame pixel effects (sharpening, denoising, color grading, upscaling) but **not suitable** for multi-layer timeline compositing. It's a rendering pipeline for playback, not a compositing engine.

---

## 6. Custom OpenGL/Vulkan Compositor

This is essentially **what Filmora/Premiere/Resolve do internally**. Building one is very achievable.

### Architecture

```
┌─────────────────────────────────────────────┐
│            Python Application                │
│  (Timeline, Layer Management, Transitions)   │
├─────────────────────────────────────────────┤
│         ModernGL / Vulkan (Python)           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │Texture 1│ │Texture 2│ │Texture 3│ ...   │
│  │(video)  │ │(image)  │ │(text)   │       │
│  └────┬────┘ └────┬────┘ └────┬────┘       │
│       └────────────┼────────────┘            │
│                    ▼                         │
│           Fragment Shader                    │
│     (composite all layers with transforms)   │
│                    │                         │
│              FBO (offscreen)                 │
│                    │                         │
│            Read pixels → NVENC               │
│         (or zero-copy via CUDA-GL interop)   │
└─────────────────────────────────────────────┘
```

### Implementation with Python + ModernGL

**ModernGL** is a Pythonic OpenGL wrapper that supports headless rendering:

```python
import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Headless context (no window needed)
ctx = moderngl.create_context(standalone=True, backend='egl')  # or 'wgl' on Windows

# Create FBO for offscreen rendering
fbo = ctx.framebuffer(
    color_attachments=[ctx.texture((1920, 1080), 4)]  # RGBA
)
fbo.use()

# Compile compositing shader
prog = ctx.program(
    vertex_shader='''
        #version 330
        in vec2 in_vert;
        in vec2 in_uv;
        out vec2 uv;
        void main() {
            gl_Position = vec4(in_vert, 0.0, 1.0);
            uv = in_uv;
        }
    ''',
    fragment_shader='''
        #version 330
        uniform sampler2D base_layer;
        uniform sampler2D overlay_layer;
        uniform sampler2D text_layer;
        uniform float overlay_opacity;
        uniform vec2 overlay_pos;
        uniform vec2 overlay_scale;
        uniform float text_opacity;
        uniform vec2 text_pos;
        in vec2 uv;
        out vec4 fragColor;

        void main() {
            vec4 color = texture(base_layer, uv);

            // Overlay layer with transform
            vec2 ovr_uv = (uv - overlay_pos) / overlay_scale;
            if (ovr_uv.x >= 0.0 && ovr_uv.x <= 1.0 &&
                ovr_uv.y >= 0.0 && ovr_uv.y <= 1.0) {
                vec4 ovr = texture(overlay_layer, ovr_uv);
                color = mix(color, ovr, ovr.a * overlay_opacity);
            }

            // Text layer
            vec2 txt_uv = uv - text_pos;
            if (txt_uv.x >= 0.0 && txt_uv.x <= 1.0 &&
                txt_uv.y >= 0.0 && txt_uv.y <= 1.0) {
                vec4 txt = texture(text_layer, txt_uv);
                color = mix(color, txt, txt.a * text_opacity);
            }

            fragColor = color;
        }
    '''
)

# Full-screen quad
vertices = np.array([
    -1.0, -1.0, 0.0, 0.0,
     1.0, -1.0, 1.0, 0.0,
    -1.0,  1.0, 0.0, 1.0,
     1.0,  1.0, 1.0, 1.0,
], dtype='f4')

vbo = ctx.buffer(vertices)
vao = ctx.vertex_array(prog, [(vbo, '2f 2f', 'in_vert', 'in_uv')])

# Load textures
def load_texture_from_pil(img: Image.Image) -> moderngl.Texture:
    img = img.convert('RGBA')
    tex = ctx.texture(img.size, 4, img.tobytes())
    tex.build_mipmaps()
    return tex

# Render text to texture (one-time, or per text change)
def text_to_texture(text: str, font_size: int = 48) -> moderngl.Texture:
    font = ImageFont.truetype("arial.ttf", font_size)
    # Measure text
    bbox = font.getbbox(text)
    w, h = bbox[2] - bbox[0] + 20, bbox[3] - bbox[1] + 20
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), text, fill=(255, 255, 255, 255), font=font)
    return load_texture_from_pil(img)

# Per-frame render loop
def render_frame(video_frame_tex, overlay_tex, text_tex):
    fbo.use()
    ctx.clear(0.0, 0.0, 0.0, 1.0)

    video_frame_tex.use(0)
    overlay_tex.use(1)
    text_tex.use(2)

    prog['base_layer'].value = 0
    prog['overlay_layer'].value = 1
    prog['text_layer'].value = 2
    prog['overlay_opacity'].value = 0.9
    prog['overlay_pos'].value = (0.6, 0.6)
    prog['overlay_scale'].value = (0.35, 0.35)
    prog['text_opacity'].value = 1.0
    prog['text_pos'].value = (0.05, 0.85)

    vao.render(moderngl.TRIANGLE_STRIP)

    # Read back for encoding
    data = fbo.read(components=4, dtype='f1')
    return np.frombuffer(data, dtype=np.uint8).reshape(1080, 1920, 4)
```

### NVENC Integration

Two approaches:

**A) Read back to CPU → pipe to FFmpeg NVENC (simple, ~10-20ms overhead per frame):**
```python
import subprocess

ffmpeg = subprocess.Popen([
    'ffmpeg', '-y',
    '-f', 'rawvideo', '-pix_fmt', 'rgba',
    '-s', '1920x1080', '-r', '30',
    '-i', '-',  # stdin
    '-c:v', 'h264_nvenc', '-preset', 'p4', '-cq', '20',
    'output.mp4'
], stdin=subprocess.PIPE)

for frame_data in render_loop():
    ffmpeg.stdin.write(frame_data.tobytes())
```

**B) Zero-copy via CUDA-OpenGL interop → PyNvVideoCodec (advanced, fastest):**
- Register the OpenGL FBO texture as a CUDA external resource
- Map it to a CUDA array
- Pass directly to NVENC via `PyNvVideoCodec`
- **Zero PCIe round-trips**
- Requires: `pycuda` + `PyNvVideoCodec` + `cuda-gl-interop`

### Difficulty Assessment

| Component | Difficulty | Time Estimate |
|-----------|-----------|---------------|
| ModernGL headless setup | Easy | 1 hour |
| Basic compositing shader | Easy | 2 hours |
| Text rasterization (PIL → texture) | Easy | 1 hour |
| Video frame → texture (via PyNvVideoCodec decode) | Medium | 4 hours |
| Transform system (position/scale/rotation/opacity) | Medium | 4 hours |
| Transition system (crossfade, wipe, etc.) | Medium | 8 hours |
| NVENC encode (CPU readback) | Easy | 2 hours |
| NVENC encode (CUDA-GL interop zero-copy) | Hard | 16+ hours |
| **Total for working prototype** | | **~2-4 days** |

This is **very buildable** and gives you Filmora-class compositing performance.

---

## 7. OBS Studio / libobs Approach

### Architecture

OBS Studio is built on **libobs**, a C library with a modular plugin system:

- **Sources** (inputs): video capture, image, text (FreeType2), media (via FFmpeg), browser (CEF), color source
- **Scenes**: collections of sources with per-source transform (position, scale, rotation, crop, alignment)
- **Filters**: per-source effects (color correction, chroma key, sharpen, LUT, scroll, etc.)
- **Transitions**: between scenes (fade, cut, swipe, slide, stinger, luma wipe)
- **Outputs**: streaming (RTMP), recording (NVENC, AMF, QSV, x264), virtual camera, NDI
- **Rendering**: OpenGL on Linux/macOS, Direct3D 11 on Windows. All compositing happens on GPU.

### Can libobs be used headlessly?

**YES**, with caveats:

1. **libobs is a standalone C library** — you can link against it without the Qt UI
2. There are **Python bindings** via `obs-python` (scripting API) and community wrappers like `obsws-python` (WebSocket API)
3. **obs-websocket** provides a WebSocket API to control a running OBS instance — you can create scenes, add sources, set transforms, start/stop recording, all programmatically
4. OBS can run **minimized/offscreen** but requires a GPU context (cannot run truly headless without a display on Windows — but can run as a background process)
5. The **`--startrecording`** and **`--minimize-to-tray`** flags enable automated operation

**Practical approach for automation:**

```python
# Using obsws-python to control OBS remotely
import obsws_python as obs

cl = obs.ReqClient(host='localhost', port=4455, password='secret')

# Create a scene
cl.create_scene('AutoScene')

# Add media source
cl.create_input('AutoScene', 'video', 'ffmpeg_source', {
    'local_file': 'input.mp4',
    'is_hw_decoding': True
})

# Add text source
cl.create_input('AutoScene', 'title', 'text_ft2_source', {
    'text': 'Hello World',
    'font': {'face': 'Arial', 'size': 48}
})

# Position the text
cl.set_scene_item_transform('AutoScene', 'title', {
    'positionX': 100, 'positionY': 900
})

# Start recording
cl.start_record()
```

**Pros:**
- Battle-tested GPU compositing (used by millions)
- Rich source types (text, image, video, browser, capture)
- NVENC recording built-in
- WebSocket API for remote control

**Cons:**
- OBS must be running as a process (not a library you embed)
- Requires GPU context on Windows (no true headless mode)
- Overkill for simple automation pipelines
- Scene/source model is designed for live streaming, not frame-accurate timeline rendering

**Verdict:** Viable for automation if you accept running OBS as a background service. Not ideal for high-throughput batch rendering.

---

## 8. NVIDIA Video Codec SDK + CUDA

### PyNvVideoCodec (Recommended for Python)

NVIDIA's official Python library for hardware video encode/decode:

```python
import PyNvVideoCodec as nvc

# Decode
demuxer = nvc.CreateDemuxer(filename="input.mp4")
decoder = nvc.CreateDecoder(
    gpuid=0,
    codec=demuxer.GetNvCodecId(),
    usedevicememory=True  # Frames stay in GPU memory
)

for packet in demuxer:
    for frame in decoder.Decode(packet):
        # frame.cuda() exposes CUDA Array Interface
        # Can pass directly to PyTorch, CuPy, pycuda
        gpu_ptr = frame.cuda()

# Encode
encoder = nvc.CreateEncoder(
    width=1920, height=1080,
    format="NV12",
    usecpuinputbuffer=False,  # GPU buffer mode — zero copy
    config_params={"gpu_id": 0, "codec": "h264"}
)

# Pass CUDA buffers directly
encoder.Encode(gpu_frame)
encoder.EndEncode()
```

**Key features:**
- `pip install PyNvVideoCodec` — no compilation needed
- Supports H.264, HEVC, AV1 encode/decode
- GPU buffer mode: input objects implementing `cuda()` method (CUDA Array Interface) are encoded directly from GPU memory
- Works with PyTorch tensors, CuPy arrays, pycuda GPU arrays
- MIT license, officially supported by NVIDIA
- Decode performance: close to native C++ SDK

### CUDA Compositing + NVENC Pipeline

The ultimate zero-copy pipeline:

```
NVDEC (decode) → CUDA kernel (composite) → NVENC (encode)
     │                  │                      │
  GPU memory ←——————— zero-copy ————————→ GPU memory
```

**Implementation:**

```python
import pycuda.driver as cuda
import pycuda.autoinit
from pycuda.compiler import SourceModule
import PyNvVideoCodec as nvc
import numpy as np

# CUDA compositing kernel
composite_kernel = SourceModule("""
__global__ void composite(
    unsigned char* main_frame,   // NV12: Y plane followed by UV plane
    unsigned char* overlay_frame, // RGBA
    int main_width, int main_height,
    int ovr_width, int ovr_height,
    int ovr_x, int ovr_y,
    float opacity
) {
    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int y = blockIdx.y * blockDim.y + threadIdx.y;

    if (x >= main_width || y >= main_height) return;

    // Check if in overlay region
    int ox = x - ovr_x;
    int oy = y - ovr_y;
    if (ox >= 0 && ox < ovr_width && oy >= 0 && oy < ovr_height) {
        int ovr_idx = (oy * ovr_width + ox) * 4;
        float alpha = (overlay_frame[ovr_idx + 3] / 255.0f) * opacity;

        int y_idx = y * main_width + x;
        // Blend Y channel
        float y_main = main_frame[y_idx];
        float y_ovr = overlay_frame[ovr_idx] * 0.299f +
                      overlay_frame[ovr_idx+1] * 0.587f +
                      overlay_frame[ovr_idx+2] * 0.114f;
        main_frame[y_idx] = (unsigned char)(y_main * (1-alpha) + y_ovr * alpha);
    }
}
""").get_function("composite")

# Full pipeline
demuxer = nvc.CreateDemuxer(filename="input.mp4")
decoder = nvc.CreateDecoder(gpuid=0, codec=demuxer.GetNvCodecId(), usedevicememory=True)
encoder = nvc.CreateEncoder(
    width=1920, height=1080, format="NV12",
    usecpuinputbuffer=False, config_params={"gpu_id": 0, "codec": "h264"}
)

for packet in demuxer:
    for frame in decoder.Decode(packet):
        # Composite on GPU (frame.cuda() gives CUDA array)
        # composite_kernel(frame_ptr, overlay_ptr, ...)
        # Encode directly from GPU
        encoder.Encode(frame)

encoder.EndEncode()
```

**GPUDirect / Zero-copy:** NVENC accepts CUDA device pointers directly. No GPUDirect needed for single-GPU compositing — standard CUDA memory is sufficient. GPUDirect is for multi-GPU or NIC→GPU transfers (video over network).

---

## 9. WebGPU/WebGL in Headless Chrome

### Architecture

```
VideoDecoder (WebCodecs) → VideoFrame → GPUExternalTexture → WGSL Shader → OffscreenCanvas → VideoFrame → VideoEncoder (WebCodecs)
```

Chrome supports **headless mode with GPU** (`--headless=new --use-angle=vulkan`). This enables:

- **WebCodecs**: Hardware-accelerated video decode (H.264, HEVC, VP9, AV1) and encode (H.264)
- **WebGPU**: GPU compute and render via WGSL shaders on Vulkan/D3D12/Metal
- **VideoFrame**: Zero-copy GPU texture wrapper — decode output is already a GPU texture

### Practical Implementation (Node.js + Puppeteer)

```javascript
// This runs inside headless Chrome via Puppeteer
const decoder = new VideoDecoder({
    output: async (videoFrame) => {
        // videoFrame is a GPU texture — zero copy
        const device = await navigator.gpu.requestAdapter().then(a => a.requestDevice());

        // Create external texture from VideoFrame
        const externalTexture = device.importExternalTexture({ source: videoFrame });

        // Composite in WGSL shader
        const pipeline = device.createRenderPipeline({ /* ... */ });
        // ... render composite to offscreen canvas ...

        // Capture result as new VideoFrame
        const outputFrame = new VideoFrame(offscreenCanvas, {
            timestamp: videoFrame.timestamp
        });

        // Encode
        encoder.encode(outputFrame);
        outputFrame.close();
        videoFrame.close();
    },
    error: console.error
});

const encoder = new VideoEncoder({
    output: (chunk) => { /* mux to MP4 */ },
    error: console.error
});
encoder.configure({
    codec: 'avc1.640028',  // H.264 High 4.0
    width: 1920, height: 1080,
    hardwareAcceleration: 'prefer-hardware'
});
```

### Open-source projects using this approach

- **[KubeezCut](https://kubeez.com)**: Free browser video editor using WebGPU + WebCodecs. Composites layers in WGSL shaders, encodes via WebCodecs, muxes with MediaBunny. Fully client-side.
- **[Remotion](https://remotion.dev)**: React-based video creation framework. Renders via headless Chromium. GPU-accelerated for WebGL/CSS effects. Encodes via FFmpeg (not WebCodecs). The most mature programmatic video framework.

**Pros:**
- True zero-copy decode→shader→encode pipeline
- Cross-platform (any Chrome/Edge)
- JavaScript/TypeScript ecosystem
- Text rendering via Canvas 2D or DOM → texture

**Cons:**
- Requires headless Chrome (heavy dependency ~400MB)
- WebCodecs H.264 encode quality is browser-dependent
- Limited codec support for encode (H.264 only in most browsers)
- Complex to orchestrate from Python (needs Node.js or Puppeteer bridge)

---

## 10. Practical Existing Tools

### Libraries/Services for GPU Compositing

| Project | Language | GPU | Approach | Verdict for RTX 3060 |
|---------|----------|-----|----------|----------------------|
| **FFmpeg CUDA filters** | C (CLI) | CUDA | `scale_cuda`, `overlay_cuda` chain | ✅ Best for pure FFmpeg pipeline |
| **PyNvVideoCodec + pycuda** | Python | CUDA | Custom CUDA kernels + NVENC | ✅ Best for custom compositing |
| **ModernGL + FFmpeg** | Python | OpenGL | Shader compositing → pipe to NVENC | ✅ Best balance of flexibility + simplicity |
| **Remotion** | TypeScript | OpenGL/WebGL | Headless Chrome → canvas → FFmpeg | ✅ Best for complex animations/motion graphics |
| **GStreamer glvideomixer** | C/Python (gi) | OpenGL | GL texture compositing | ⚠️ Viable but Windows GL support is spotty |
| **OBS + obs-websocket** | C++ (service) | D3D11/GL | Scene compositing in OBS | ⚠️ Works but heavy and not frame-accurate |
| **MLT/movit** | C++ | OpenGL | GLSL effects, CPU compositing | ❌ Not truly GPU-accelerated |
| **mpv shaders** | GLSL | OpenGL/Vulkan | Per-frame playback shaders | ❌ Not a compositing engine |
| **libplacebo** | C | Vulkan/GL/D3D | High-quality render pipeline | ⚠️ Great for scaling/tonemapping, limited compositing |
| **WebGPU + WebCodecs** | JavaScript | Vulkan/D3D12 | Browser WGSL shader pipeline | ⚠️ Promising but complex to orchestrate |

### The Recommended Architecture for This Project

Given: **Python pipeline, Windows, RTX 3060, need text/image/video compositing, output to H.264**

**Tier 1 (Recommended): FFmpeg CUDA filter chain**
```
Decode (NVDEC) → scale_cuda → overlay_cuda (images) → NVENC
                      ↑
              Pre-rendered text PNGs
              (uploaded once, reused across frames)
```
- Use for: 90% of compositing tasks
- Performance: ~500-1000 fps for 1080p overlay on RTX 3060
- Complexity: Low (just FFmpeg commands)

**Tier 2 (Advanced): ModernGL compositor → NVENC pipe**
```
Decode (NVDEC via PyNvVideoCodec) → ModernGL shader composite → stdin → FFmpeg NVENC
```
- Use for: Complex multi-layer scenes, custom transitions, animated text
- Performance: ~200-400 fps for 1080p (limited by PCIe readback)
- Complexity: Medium

**Tier 3 (Maximum performance): CUDA kernel + NVENC zero-copy**
```
Decode (NVDEC) → CUDA kernel composite → NVENC encode
         (all in GPU memory, zero PCIe transfers)
```
- Use for: High-throughput batch rendering
- Performance: ~800-2000 fps for 1080p
- Complexity: High

---

## Appendix A: Complete FFmpeg CUDA Filter Reference

### CUDA Video Filters (require `--enable-cuda-nvcc` or `--enable-cuda-llvm`)

| Filter | Since | Inputs | GPU Memory | Description |
|--------|-------|--------|------------|-------------|
| `bilateral_cuda` | 4.4 | 1 | CUDA | Edge-preserving bilateral filter |
| `bwdif_cuda` | 5.0 | 1 | CUDA | Bwdif deinterlacing |
| `chromakey_cuda` | 4.4 | 1 | CUDA | Chroma keying (green screen) |
| `colorspace_cuda` | 5.0 | 1 | CUDA | Color space/primaries/transfer conversion |
| `overlay_cuda` | 4.4 | 2 | CUDA | Overlay one video on another |
| `pad_cuda` | 8.0 | 1 | CUDA | Add padding/borders |
| `scale_cuda` | 4.4 | 1 | CUDA | Scale/resize + format conversion |
| `thumbnail_cuda` | 4.4 | 1 | CUDA | Select representative frame |
| `yadif_cuda` | 4.4 | 1 | CUDA | Yadif deinterlacing |

### CUDA NPP Filters (require `--enable-libnpp`)

| Filter | Since | Inputs | Description |
|--------|-------|--------|-------------|
| `scale_npp` | 3.4 | 1 | Scale + format conversion via NPP |
| `scale2ref_npp` | 4.4 | 2 | Scale based on reference video |
| `sharpen_npp` | 4.4 | 1 | Image sharpening with border control |
| `transpose_npp` | 4.4 | 1 | Transpose/rotate via NPP |

### OpenCL Filters (require `--enable-opencl`)

| Filter | Description |
|--------|-------------|
| `avgblur_opencl` | Average blur |
| `boxblur_opencl` | Box blur |
| `colorkey_opencl` | Color keying |
| `convolution_opencl` | Custom convolution matrix |
| `deshake_opencl` | Video stabilization |
| `dilation_opencl` | Morphological dilation |
| `erosion_opencl` | Morphological erosion |
| `nlmeans_opencl` | NL-means denoising |
| `overlay_opencl` | Overlay compositing |
| `pad_opencl` | Padding |
| `prewitt_opencl` | Prewitt edge detection |
| `program_opencl` | Custom OpenCL kernel |
| `remap_opencl` | Pixel remapping |
| `roberts_opencl` | Roberts edge detection |
| `sobel_opencl` | Sobel edge detection |
| `tonemap_opencl` | HDR→SDR tone mapping |
| `unsharp_opencl` | Unsharp masking |
| `xfade_opencl` | Cross-fade transitions |

### Vulkan/libplacebo Filter (require `--enable-vulkan --enable-libplacebo`)

| Filter | Description |
|--------|-------------|
| `libplacebo` | Full GPU pipeline: scaling, tonemapping, debanding, grain, color management, custom shaders, multi-input compositing |

---

## Appendix B: Example FFmpeg Commands for RTX 3060

### Full GPU pipeline: decode → scale → overlay image → encode
```bash
ffmpeg -y \
  -hwaccel cuda -hwaccel_output_format cuda -i main.mp4 \
  -i logo.png \
  -filter_complex "
    [0:v]scale_cuda=1920:1080:format=yuv420p[main];
    [1:v]format=rgba,hwupload_cuda,scale_cuda=200:200[logo];
    [main][logo]overlay_cuda=x=W-w-20:y=20
  " \
  -c:v h264_nvenc -preset p4 -cq 20 output.mp4
```

### Picture-in-picture: two videos side by side
```bash
ffmpeg -y \
  -hwaccel cuda -hwaccel_output_format cuda -i video1.mp4 \
  -hwaccel cuda -hwaccel_output_format cuda -i video2.mp4 \
  -filter_complex "
    [0:v]scale_cuda=960:1080[left];
    [1:v]scale_cuda=960:1080[right];
    [left]pad_cuda=w=1920:h=1080:x=0:y=0[canvas];
    [canvas][right]overlay_cuda=x=960:y=0
  " \
  -c:v h264_nvenc -preset p4 output.mp4
```

### Chroma key compositing (green screen over background)
```bash
ffmpeg -y \
  -hwaccel cuda -hwaccel_output_format cuda -i greenscreen.mp4 \
  -hwaccel cuda -hwaccel_output_format cuda -i background.mp4 \
  -filter_complex "
    [0:v]chromakey_cuda=0x00FF00:0.1:0.05:1[keyed];
    [1:v]scale_cuda=1920:1080[bg];
    [bg][keyed]overlay_cuda
  " \
  -c:v h264_nvenc -preset p4 output.mp4
```

### libplacebo: high-quality scale + tone map (HDR→SDR)
```bash
ffmpeg -y \
  -init_hw_device vulkan=vk:0 \
  -init_hw_device cuda@cudadev \
  -hwaccel cuda -hwaccel_output_format cuda -i hdr_input.mp4 \
  -filter_complex "
    hwupload=derive_device=vulkan,
    libplacebo=
      w=1920:h=1080:
      tonemapping=spline:
      colorspace=bt709:
      color_primaries=bt709:
      color_trc=bt709,
    hwdownload,format=nv12
  " \
  -c:v h264_nvenc -preset p4 output.mp4
```

### Text overlay (hybrid: CPU text render → GPU composite)
```bash
# Step 1: Pre-render text to transparent PNG (Python/PIL)
# Step 2: Composite on GPU
ffmpeg -y \
  -hwaccel cuda -hwaccel_output_format cuda -i main.mp4 \
  -i text_overlay.png \
  -filter_complex "
    [0:v]scale_cuda=1920:1080:format=yuv420p[main];
    [1:v]format=rgba,hwupload_cuda[text];
    [main][text]overlay_cuda=x=(W-w)/2:y=H-h-50
  " \
  -c:v h264_nvenc -preset p4 output.mp4
```

---

## Appendix C: Python Package Quick Reference

| Package | Install | Purpose | GPU? |
|---------|---------|---------|------|
| `PyNvVideoCodec` | `pip install PyNvVideoCodec` | HW decode/encode via NVDEC/NVENC | ✅ CUDA |
| `pycuda` | `pip install pycuda` | CUDA kernel programming | ✅ CUDA |
| `moderngl` | `pip install moderngl` | OpenGL rendering/compositing | ✅ OpenGL |
| `moderngl[headless]` | `pip install moderngl[headless]` | Headless GL context (EGL) | ✅ OpenGL |
| `Pillow` | `pip install Pillow` | Text/image rasterization → PNG | ❌ CPU |
| `numpy` | `pip install numpy` | Array manipulation | ❌ CPU |
| `cupy` | `pip install cupy-cuda12x` | GPU arrays (CUDA Array Interface) | ✅ CUDA |
| `torch` | `pip install torch` | GPU tensors (can exchange with PyNvVideoCodec) | ✅ CUDA |
| `obsws-python` | `pip install obsws-python` | OBS remote control via WebSocket | ✅ (OBS GPU) |
| `gi` (PyGObject) | System package | GStreamer Python bindings | ⚠️ Partial |

---

*End of research document.*
