# Remotion Replacement — Open-Source Real-Footage Editors (Research)

**Date:** 2026-07-26
**Scope:** Find open-source tools that (a) edit REAL video footage (timeline, cuts, trims, transitions, overlays, grade, audio) and (b) can be driven automatically — ideally via MCP (Model Context Protocol) or a clean headless API — as a candidate replacement for Remotion in this pipeline.
**Companion doc:** `docs/VIDRUSH_ENGINE_RESEARCH.md` (changes the recommendation — see §6).

---

## 1. The flaw being solved

Remotion renders HTML/React to frames via Chrome — it **cannot natively edit real video footage**. In this pipeline the real-footage assembly (cutting/trimming clips, transitions between real clips, NVENC encode) is done by a **separate FFmpeg step**; Remotion only produces the motion-graphic overlay scenes. This research evaluates whether a single open-source tool could do both the real-footage editing AND be agent-driven via MCP.

---

## 2. Comparison table

| Tool | Repo | License | Activity | Edits REAL footage? | Driven via | Ready MCP? | Text/titles/motion | Windows | Headless | GPU encode |
|---|---|---|---|---|---|---|---|---|---|---|
| **MLT / melt** (+ **Kdenlive-mcp**) | `mltframework/mlt`, `AMMIROSOH/Kdenlive-mcp` | LGPL / Apache-2.0 | ~1k★ + 4★, active | ✅ full timeline: cuts, trims, ripple, transitions, keyframes, filters, captions | XML project → `melt` CLI; Python bindings; MCP server | ✅ Kdenlive-mcp (purpose-built, **public preview**) | ✅ `dynamictext`/`qtext`, watermarks, affine | ✅ melt.exe ships w/ Shotcut | ✅ fully headless | NVENC via avformat consumer |
| **Kinocut** | `KyaniteLabs/kinocut` | Apache-2.0 | 91★, very active (v1.11.1) | ✅ trim, merge w/ transitions, composite, overlays, subtitles, speed, chroma key, grade, duck/normalize | MCP (161 tools), Python `Client`, `kino` CLI | ✅ **most complete MCP** | ✅ animated text, ASS/SRT subtitles, blend modes | ✅ (Python + FFmpeg) | ✅ | FFmpeg / NVENC |
| **Blender VSE** | (Blender Foundation) | GPL | huge, very active | ✅ real NLE: strips, cuts, dissolves, wipes, speed, effects, text, transforms, compositor | Python `bpy`; headless `blender -b -P` | ⚠️ Blender MCPs exist (~15k★) but **none target VSE** | ✅ text strips + full Compositor | ✅ native | ✅ `-b` | ❌ **no NVENC** (CPU encode) |
| **OpenShot (libopenshot)** | `OpenShot/libopenshot` | LGPL-3.0 | 1.5k★, active | ✅ real timeline, transitions, keyframes, titles, audio mix | C++/Python API (SWIG) | ❌ build your own | ✅ SVG titles, keyframed effects | ⚠️ **painful MSYS2 Python bindings** | ⚠️ | partial CUDA |
| **Shotcut (MLT GUI)** | `mltframework/shotcut` | GPL-3.0 | ~11k★, active | ✅ full NLE | GUI; project = MLT XML → `melt` | ❌ (MCP "planned", not shipped) | ✅ rich filters/text/keyframes | ✅ | ⚠️ plain `melt` is headless | MLT consumer |
| **MoviePy** | `Zulko/moviepy` | MIT | 14.8k★, active | ✅ cuts/subclips/concat/composite/text/audio | pure Python | ❌ trivial to wrap | ✅ TextClip, numpy effects | ✅ (pip) | ✅ | ❌ CPU encode (slow numpy) |
| **Auto-Editor** | `WyattBlue/auto-editor` | MIT | 4.6k★, active | ⚠️ partial — silence/filler cutting, exports EDL | CLI | ❌ | ❌ no text/overlays | ✅ binary | ✅ | n/a (cut lists) |
| **GES (GStreamer Editing Services)** | (freedesktop) | LGPL | maintained | ✅ true NLE: timeline/layers/tracks/transitions/titles | C/Python (gi), `ges-launch` | ❌ | ✅ titles/overlays via plugins | ⚠️ **rough on Windows** | ✅ | NVENC plugins exist |
| **Flowblade / Pitivi / Olive / Avidemux** | various | GPL | active-ish | ✅ NLEs | GUI; **no usable headless API** | ❌ | GUI-only | ⚠️ Linux-first | ❌ | — |
| **Oh My Cassette** | `Cassette-Editor/oh-my-cassette` | MIT | 143★, new/active | ✅ (cloud-rendered montage) | MCP (14 tools) | ✅ | ✅ | ✅ | ✅ | ❌ **cloud backend — not local** |
| **video-audio-mcp** | `misbahsy/video-audio-mcp` | MIT | 83★, active | ✅ trim/concat/overlays/subtitles/B-roll/silence | MCP (FastMCP) | ✅ | ✅ text overlay, subtitles | ✅ | ✅ | FFmpeg (extend for NVENC) |
| misc **ffmpeg-mcp** forks | various | various | 3–141★ | ⚠️ basic trim/concat/overlay | MCP | ✅ | ⚠️ basic text only | ⚠️ some mac-only | ✅ | FFmpeg direct |

---

## 3. Top recommendations (for a true Remotion replacement)

### 🥇 #1 — MLT / melt XML (+ Kdenlive-mcp as control layer)
Only option that is simultaneously (a) a genuine NLE with frame-accurate timeline semantics, (b) fully headless, (c) driven by a declarative XML file an agent can generate directly, and (d) has a purpose-built MCP server (`AMMIROSOH/Kdenlive-mcp`) with revisioned projects, undo, previews, and render verification.

This pipeline already thinks in "timelines" (`timeline_schema.json`). **MLT XML *is* that timeline** — clips, in/out points, transitions (luma/mix/composite), filters (dynamictext, affine, brightness), multitrack audio. The `melt` binary bundled with Shotcut for Windows renders it headless. One step could replace both "Remotion per-scene render" and "FFmpeg xfade concat".

### 🥈 #2 — Kinocut (agent tool layer / fast first win)
`pip install kinocut` → 161 typed, guardrailed tools covering exactly what the assembly step does (trim, merge with transitions, add_text, composite_layers with blend modes, subtitles, audio duck/normalize, color grade) plus quality-check gates. Its Python `Client` lets `orchestrator.py` call it **directly in-process** without MCP overhead.

**Recommended architecture if replacing:** use **both** — MLT/Kdenlive-mcp as the *timeline engine* (the edit), Kinocut as the *pre/post utility layer* (asset prep, silence removal, quality gates). If forced to pick one: **MLT/Kdenlive-mcp** for correctness, **Kinocut** for speed-to-value.

---

## 4. Integration sketch — replacing "Remotion scene render → FFmpeg xfade"

### Current flow
```
timeline.json → render.js → N × Remotion Chrome renders (scene_01.mp4 … scene_NN.mp4)
              → FFmpeg xfade chain → NVENC encode → final.mp4
```

### MLT flow
```
timeline.json → pipeline/mlt_compiler.py → project.mlt  (XML)
             → melt project.mlt -consumer avformat:final.mp4 [NVENC props]
             → done  (one render: real footage + text + transitions + grade)
```

`pipeline/render/mlt_compiler.py` (~300–500 lines) maps each scene dict → MLT XML:

| Timeline scene element | MLT equivalent |
|---|---|
| `bg_video` (stock clip) | `<producer>` with `in`/`out` points |
| `still_motion: push` (Ken Burns) | `affine` filter with animated rect |
| scene text / lower-thirds | `dynamictext`/`qtext` filters + style palette/font from `styles/*.json` |
| transitions between scenes | `<tractor>` with `luma`/`mix` (one type per style — same rule as now) |
| VO track | audio `<playlist>` + volume; or keep FFmpeg audio pass |
| per-style grade | `brightness`/`contrast`/`saturation`/`avfilter.colorbalance` chain |

Render: `melt project.mlt -consumer avformat:final.mp4 vcodec=h264_nvenc preset=p6 b=12M …` — NVENC works because MLT's avformat consumer passes properties straight to FFmpeg. Windows `melt` ships with Shotcut (`C:\Program Files\Shotcut\melt.exe`).

### What replaces Remotion's motion graphics?
- Titles/lower-thirds/plates → MLT `qtext`/`dynamictext` + `shape`/`color` producers.
- Ken Burns / push / parallax → `affine` filter keyframes.
- **Word-pop / mask-line reveals — the genuinely hard part.** MLT has no per-word stagger. Options: (a) accept simpler per-line fade/slide (editorially fine per `PRO_EDIT_STYLE.md`, which already bans word stagger), or (b) keep a **small Remotion island** for the 2–3 typographic hero moments per video, imported as `<producer>` clips into the MLT timeline (Remotion as a *clip generator*, not the editor — its correct role). Option (b) is the low-risk hybrid.
- Grain/vignette/glow → MLT `noise`/`vignette`/`glow` or frei0r plugins.

### Effort & risk
| Item | Effort | Risk |
|---|---|---|
| `mlt_compiler.py` (timeline → XML) | 2–4 days | Low — validate by opening output in Shotcut GUI |
| Style JSON → MLT filter mapping | 2–3 days | Medium — MLT filter params differ from CSS |
| NVENC via melt consumer | hours | Low |
| Typographic hero moments (keep Remotion island) | 0 (existing) | Low |
| Kdenlive-mcp as MCP server | 1 day wiring | Medium — 4★ "public preview"; battle-test first |
| **Total (compiler path)** | **~1.5 weeks** | **Medium-low** |
| **Total (Kinocut-only path)** | **~2–3 days** | **Low** (no true multitrack timeline) |

**Biggest risk:** MLT on Windows is less battle-tested than Linux. Mitigate by pinning to Shotcut-bundled `melt` and validating `h264_nvenc` output early. Second: Kdenlive-mcp maturity — treat as optional; the XML compiler works with plain `melt` regardless.

---

## 5. MCP server status summary

| Tool | MCP exists? | Maturity |
|---|---|---|
| **Kinocut** | ✅ `pip install kinocut`, stdio | Production (v1.11.1, CI, PyPI/npm/MCP-registry) |
| **Kdenlive-mcp** | ✅ stdio/HTTP | Public preview (projects/timeline/render/verify work; OTIO round-trip + AI analysis missing) |
| **video-audio-mcp** | ✅ FastMCP stdio | Hobby-solid (83★, tested) |
| **ffmpeg-mcp (video-creator)** | ✅ stdio | macOS only — skip |
| **Oh My Cassette** | ✅ stdio | Cloud-dependent — fails "local" requirement |
| **Blender VSE** | ⚠️ Blender-MCP servers exist (3D-focused) | Need a VSE-specific tool set (~1 week) or call `blender -b -P` directly |
| **OpenShot / Shotcut / MoviePy / GES / Auto-Editor / Flowblade / Pitivi / Olive / Avidemux** | ❌ none | Would need building from scratch |

---

## 6. Bottom line (and the VidRush twist)

- **Fastest MCP-native path today:** **Kinocut** as the assembly/edit engine. Replaces the FFmpeg glue with guardrailed typed tools; Windows + NVENC via FFmpeg. You lose true frame-accurate multitrack timeline semantics — but the current two-step (Remotion clips → xfade) never had them either.
- **Correct long-term real-NLE architecture:** thin **`timeline.json → MLT XML` compiler** → headless **`melt`** (Shotcut-bundled, Windows, NVENC), optionally **`Kdenlive-mcp`** in front for agent sessions. Keep Remotion only as an optional *typographic clip generator* for hero text moments.
- **Avoid for this use case:** OpenShot (Windows Python bindings too painful, no MCP), Blender VSE (no NVENC, heavy, MCP not VSE-oriented), GES (weak Windows story), MoviePy (too slow for long-form), Auto-Editor (not an NLE), Oh My Cassette (cloud, not local), Premiere/DaVinci MCPs (not open-source).

> **⚠️ The VidRush twist (see `docs/VIDRUSH_ENGINE_RESEARCH.md`):** VidRush itself does NOT use a real NLE. It is a theme-driven HTML/canvas motion-graphics layer over trimmed source clips, server-rendered — i.e. **the same shape as our current Remotion + FFmpeg architecture.** This suggests the flaw is a *role* problem (Remotion should be the clip/motion-graphics generator, FFmpeg the assembler) rather than a *tool* problem. **Path A (refine current architecture) is the VidRush-validated route; this MLT/Kinocut research is Path B, held in reserve.** See `docs/PATH_A_PLAN.md`.
