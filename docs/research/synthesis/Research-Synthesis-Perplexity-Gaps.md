# Research Synthesis & Perplexity Deep-Research Requirements

**Date:** 2026-07-21
**Status:** 10/10 Tavily research tasks complete
**Total findings:** ~280KB across 10 documents in `Research-Output/`

---

## Executive Summary

All 10 research tracks were executed via parallel Tavily subagents. Coverage was strong across the board — most foundational questions were answered with verified commands and community-sourced recipes. However, **~100 specific gaps** were identified that require Perplexity's deeper multi-source synthesis. This document consolidates and prioritizes those gaps.

### Coverage Assessment by Track

| Track | Coverage | Confidence | Gap Count |
|-------|----------|-----------|-----------|
| P0-Audio-Mastery | 85% | High | 12 |
| P0-Timeline-Architecture | 90% | High | 11 |
| P1-Performance-Optimization | 80% | High | 12 |
| P1-Text-Typography | 85% | High | 10 |
| P1-Asset-Pipeline | 75% | Medium-High | 12 |
| P2-Error-Handling | 85% | High | 10 |
| P2-MCP-Interface | 80% | High | 9 |
| P2-Filter-Validation | 75% | Medium-High | 10 |
| P3-LLM-Integration | 80% | Medium-High | 10 |
| P3-Advanced-Techniques | 70% | Medium | 9 |

---

## TIER 1 — BLOCKERS (Must research before building)

These gaps directly block correct implementation of core MCP features.

### 1. Sidechain Lookahead / Pre-Ducking (Audio)
**Gap:** No verified recipe for delaying the sidechain key signal to achieve pre-emptive ducking (DAW-standard technique).
**Why it matters:** Without lookahead, ducking reacts *after* voice starts — audible music swell at every sentence start.
**Perplexity prompt:** "FFmpeg sidechaincompress lookahead delay sidechain signal pre-ducking recipe — verify whether adelay on the key input achieves DAW-style lookahead compression, and document the exact filter_complex with measured latency."

### 2. AAC Encoder-Delay / Gapless Joining (Timeline)
**Gap:** Authoritative handling of AAC priming samples when concatenating encoded audio segments.
**Why it matters:** The research recommends "PCM intermediates → single final AAC encode" — but if we ever join pre-encoded AAC, ~30ms clicks/pops appear at every scene boundary.
**Perplexity prompt:** "FFmpeg AAC gapless concatenation encoder delay priming samples — document whether FFmpeg handles iTunSMPB/edit-list metadata on concat, and the authoritative method for click-free AAC joins in 2026."

### 3. zoompan Jitter Bug #4298 — Definitive Fix Status (Filters)
**Gap:** Which FFmpeg version/commit actually fixed (or didn't) the infamous integer-rounding jitter. Trac ticket status unclear.
**Why it matters:** Ken Burns is the #1 most-used effect in automated video. We need to know if we must ship the upscale-8K workaround or if a native fix exists in 7.x/8.x.
**Perplexity prompt:** "FFmpeg zoompan ticket 4298 jitter fix status 2026 — which FFmpeg version resolved the integer rounding bug, is the trac ticket closed, and do current releases still require the trunc() or upscale workarounds?"

### 4. minterpolate Throughput Benchmarks (Filters + Performance)
**Gap:** Zero published fps/resolution/CPU throughput numbers anywhere.
**Why it matters:** minterpolate is single-threaded and the recommended strategy is chunking + parallel instances — but we can't size chunks without knowing base throughput.
**Perplexity prompt:** "FFmpeg minterpolate benchmark fps throughput 1080p 4K — measured rendering speed in frames-per-second for mi_mode=mci on modern CPUs (i7/i9/Ryzen), needed to calculate chunk sizes for parallel processing."

### 5. Motion-Graphics Decision Rules from Real Usage (LLM Integration)
**Gap:** When to use kinetic typography vs charts vs B-roll — only anecdotal evidence. Tavily quota died on this query.
**Why it matters:** This is the CORE of the trigger engine — the LLM's decision quality depends on real usage data, not theory.
**Perplexity prompt:** "Motion graphics selection rules kinetic typography vs charts vs b-roll — professional video editor guidelines and academic/industry research on which visual treatment to choose for which content type, with quantitative evidence from high-performing YouTube channels and broadcast graphics."

### 6. Audio-Reactive Video Pipelines (Advanced)
**Gap:** No verified method for driving video filter parameters from audio levels per-frame (e.g., bass energy → scale pulse).
**Why it matters:** Music-driven visuals are a high-value differentiator. The building blocks exist (astats metadata, sendcmd) but nobody has documented the full pipeline.
**Perplexity prompt:** "FFmpeg audio-reactive video visualization drive filter parameters from audio level — verified methods to extract per-frame amplitude/loudness and feed into drawbox/scale/geq expressions, including astats metadata reuse, sendcmd piping, and ebur128 momentary levels as animation drivers."

---

## TIER 2 — HIGH VALUE (Research before production launch)

### 7. QSV Filter Argument Documentation (Performance)
**Gap:** `vpp_qsv`, `scale_qsv` full argument specs are a known documentation disaster.
**Perplexity prompt:** "FFmpeg QSV vpp_qsv scale_qsv complete parameter documentation — all options, defaults, and examples for Intel Quick Sync video processing filters, including oneVPL vs legacy MSDK differences."

### 8. NVENC -cq ↔ x264 -crf Mapping Curves (Performance)
**Gap:** No published equivalence data between NVENC constant-quality and x264 CRF values.
**Perplexity prompt:** "NVENC cq parameter vs x264 crf equivalence mapping — measured VMAF/SSIM comparisons across cq values 15-35 to establish bitrate-quality equivalence curves for H.264 and HEVC."

### 9. Color Emoji in drawtext (Text)
**Gap:** Contradictory reports on which FreeType versions/ft_load_flags render CBDT/COLR emoji.
**Perplexity prompt:** "FFmpeg drawtext color emoji CBDT COLR FreeType support — definitive answer on which FFmpeg/FreeType versions render color emoji, required build flags, and working configurations on Windows."

### 10. ASS `\t` Accel → Penner Mathematical Mapping (Text)
**Gap:** The libass acceleration formula is undocumented — requires source analysis.
**Perplexity prompt:** "libass transform accel parameter mathematical formula — source code analysis of how the acceleration value in \\t(t1,t2,accel,tags) maps to easing curves, with the exact interpolation equation and Penner equivalents."

### 11. HEVC Alpha Muxing Status 2026 (Assets)
**Gap:** FFmpeg ticket #9088 current status — is HEVC-with-alpha muxable yet?
**Perplexity prompt:** "FFmpeg HEVC alpha channel muxing ticket 9088 status 2026 — current support for HEVC with alpha layer in MP4/MOV, which encoders support it, and the recommended workflow for HEVC alpha delivery."

### 12. xfade Behavior with VFR/Mixed Timebases (Timeline)
**Gap:** Strict timebase matching is documented, but VFR input behavior is not.
**Perplexity prompt:** "FFmpeg xfade variable frame rate VFR mixed timebase behavior — what happens when xfade inputs have different timebases or VFR, the exact conversion/normalization required, and validation methods."

### 13. FFmpeg 7.0 Color-Range Rework — Which Filters Changed (Filters + Assets)
**Gap:** Silent visual differences vs 6.x, but affected filters not enumerated anywhere.
**Perplexity prompt:** "FFmpeg 7.0 color range negotiation rework affected filters list — which specific filters changed output behavior in the 7.0 color-range rework, with before/after comparisons and migration guide."

### 14. Production Error-Recovery/Checkpoint Architectures (Error Handling)
**Gap:** Near-zero documentation on production-grade checkpoint/resume systems for video pipelines.
**Perplexity prompt:** "Production video rendering pipeline checkpoint resume architecture — how companies like Canva, Kapwing, or cloud video editors implement scene-level checkpointing, crash recovery, and partial re-rendering in FFmpeg-based systems."

### 15. Per-Tool JSON Schemas from ClipChat/OpenCut (MCP Interface)
**Gap:** Actual production tool schemas from existing FFmpeg MCP servers.
**Perplexity prompt:** "ClipChat Engine OpenCut MCP FFmpeg tool JSON schema definitions — extract the actual tool definitions, parameter schemas, and composition patterns from open-source FFmpeg MCP servers on GitHub."

---

## TIER 3 — MEDIUM VALUE (Research during development)

### 16. `speechnorm` Filter Community Usage (Audio)
**Gap:** Almost zero usage data on this speech-normalization filter.
**Perplexity prompt:** "FFmpeg speechnorm filter real-world usage examples — parameter tuning for voiceover normalization, comparison vs loudnorm+compand chains, and when speechnorm is the better choice."

### 17. `dialoguenhance` Measured Performance (Audio)
**Gap:** No measured data on effectiveness or stereo downmix guidance.
**Perplexity prompt:** "FFmpeg dialoguenhance filter measured performance benchmarks — effectiveness tests on movie/TV content, parameter recommendations, and interaction with stereo downmixing."

### 18. `arnndn` RNN Denoiser Model Matrix (Audio)
**Gap:** Model availability, licensing, and build requirements unclear.
**Perplexity prompt:** "FFmpeg arnndn filter model availability licensing — which RNN denoiser models are compatible, where to download them, license terms for commercial use, and quality comparison vs afftdn."

### 19. Dolby Vision Encoding Support (Assets)
**Gap:** Current FFmpeg Dolby Vision encoding and metadata preservation status.
**Perplexity prompt:** "FFmpeg Dolby Vision encoding support 2026 — can FFmpeg encode Dolby Vision, preserve DoVi metadata through transcodes, and what is the current state of dolby_vision bitstream filter?"

### 20. ACES Workflow / OpenColorIO Integration (Assets)
**Gap:** Native RRT/ODT support and OCIO integration status.
**Perplexity prompt:** "FFmpeg ACES workflow OpenColorIO OCIO integration — native support for ACES RRT/ODT transforms, OCIO config loading, and professional color management pipelines in FFmpeg 2026."

### 21. Perspective Sub-Pixel Accuracy Quantification (Filters)
**Gap:** No published corner-pin error measurements.
**Perplexity prompt:** "FFmpeg perspective filter sub-pixel accuracy corner pin error measurement — quantified geometric accuracy of the perspective filter, anti-aliasing quality assessment, and comparison vs dedicated corner-pin tools."

### 22. xfade Objective Quality Data (Filters)
**Gap:** No PSNR/VMAF comparisons; "broadcast-quality" rating is consensus inference.
**Perplexity prompt:** "FFmpeg xfade transition quality objective measurement PSNR VMAF — quality comparison of xfade transition types, which introduce artifacts, and measured data on transition smoothness."

### 23. Windows Build Filter Availability Matrix (Filters)
**Gap:** gyan.dev vs BtbN build differences — critical since this project targets Windows.
**Perplexity prompt:** "FFmpeg Windows builds gyan.dev vs BtbN filter availability comparison — which filters are included/excluded in each Windows build, GPL vs non-free flags, and libass/librsvg/fontconfig availability."

### 24. MCP outputSchema/Structured-Content Client Support (MCP Interface)
**Gap:** Which MCP clients actually support structured output.
**Perplexity prompt:** "MCP Model Context Protocol outputSchema structured content client support — which MCP clients (Claude, Cursor, etc.) support outputSchema, elicitation, and notifications/progress in 2026."

### 25. InVideo 12-Parameter Scene Evaluation Internals (LLM Integration)
**Gap:** Details of the most sophisticated commercial scene-routing system.
**Perplexity prompt:** "InVideo AI scene generation 12 parameter system architecture — detailed breakdown of InVideo's per-scene evaluation parameters, model routing logic, and shot design system."

---

## TIER 4 — DEFER (Nice to have, post-launch)

<details>
<summary>26 additional lower-priority gaps (click to expand)</summary>

**Audio:**
- `mcompand` per-band sidechaining possibility
- `whisper` filter transcription-driven automation details
- Ducking quality benchmarks vs DAW reference
- loudnorm 5.1/immersive phase coherence
- silenceremove timestamp modes and A/V sync on muxed video
- ZMQ/sendcmd runtime control for live ducking

**Timeline:**
- Frame-exact boundary verification at scale
- Hardware-accelerated xfade (xfade_opencl) reliability
- YouTube embedded chapter ingestion 2026 status
- Parallel segment rendering with shared transition ownership
- Rate-control boundary effects in chunked encoding

**Performance:**
- AMF AV1 benchmarks
- M3/M4 VideoToolbox multi-engine scaling
- Split-Frame-Encoding FFmpeg flag semantics
- NVENC dual-session scaling root cause
- FFmpeg 7.x threading benchmarks
- Cross-platform energy-per-bit data
- HDR metadata through HW pipelines
- VAAPI vs QSV same-silicon comparison
- Windows cross-device zero-copy interop

**Text:**
- Per-glyph drawtext animation via 2023 Harfbuzz rewrite
- Vertical CJK (tategaki) real behavior
- Animated vector \clip morphing edge cases
- drawtext-chain vs libass benchmarks at 100+ events
- Variable font axes (wght animation) exposure
- text_source side-data bboxes documentation
- LayoutResX/Y vs PlayResX/Y scaling interplay
- RTL karaoke with \k/\t + fribidi bidi reordering

**Assets:**
- AV1 native alpha roadmap
- EXR deep data/Cryptomatte support
- BT.2020 to P3-D65 zscale/libplacebo syntax
- IMF/MXF AS-11 broadcast validation
- Animated WebP alpha support
- 12-bit ProRes 4444 XQ roadmap
- HDR10+ dynamic metadata injection
- VVC/H.266 encoder availability
- Vulkan compute filters alpha/HDR status

**Error Handling:**
- -timeout per-protocol semantics matrix
- -xerror exit-code guarantees
- freezedetect tuning for intentional stills
- 10-bit HDR signalstats thresholds
- ebur128 momentary/short-term gating
- Windows-specific hang behavior
- stderr string stability across versions
- progress-output completeness matrix
- HW-accelerated error signatures (NVENC/QSV)

**MCP Interface:**
- Real `sampling` implementations
- Token-cost benchmarks per granularity level
- FFmpeg filter_complex DAGs as validated JSON
- Production OTIO→FFmpeg renderers
- MCP elicitation examples
- Tool-schema versioning strategies

**LLM Integration:**
- Lumen5 NLP segmentation algorithm
- Modern (2024+) pause prediction SOTA
- Per-provider TTS duration variance data
- Color-palette distance metrics (ΔE) for automated QC
- xfade memory behavior at 50+ scene scale
- HITL review-gate placement literature

**Advanced:**
- Canonical VHS recipes (search was rate-limited)
- Lottie headless tooling specifics and benchmarks
- perspective runtime command support in FFmpeg 7.x/8.x
- find_rect successors (dnn_detect filter)
- 2.5D parallax tutorials
- zmq latency benchmarks
- 4K performance data for advanced techniques
- Native planar-tracking proposals

</details>

---

## Recommended Perplexity Execution Plan

### Batch 1 (Do First — 6 prompts)
Tier 1 items #1-6. These block core implementation decisions.

### Batch 2 (Before Production — 9 prompts)
Tier 2 items #7-15. These affect production quality and platform compatibility.

### Batch 3 (During Development — 10 prompts)
Tier 3 items #16-25. These refine quality and unlock advanced features.

### Batch 4 (Post-Launch — remaining)
Tier 4 items as needed for specific feature development.

---

## Perplexity Prompt Template

For each gap, use this execution template:

```
You are researching a specific technical gap for an FFmpeg MCP server project.

CONTEXT: [paste relevant section from the Findings document]

GAP: [paste the specific gap description]

RESEARCH REQUIREMENTS:
1. Search official FFmpeg documentation, trac tickets, and git commits
2. Search production usage reports (blogs, forums, conference talks)
3. Search academic papers if applicable
4. Provide VERIFIED information with source citations
5. Distinguish between "documented fact", "community consensus", and "uncertain"
6. If the answer is "unknown/undocumented", say so explicitly

OUTPUT FORMAT:
## [Gap Title]
### Answer
[Direct answer to the question]
### Evidence
[Source citations and verification]
### Implementation Impact
[How this affects the MCP server design]
### Confidence
[High/Medium/Low with justification]
```

---

## Files Generated

| File | Size | Track |
|------|------|-------|
| `Research-Output/P0-Audio-Mastery-Findings.md` | 29KB | Audio |
| `Research-Output/P0-Timeline-Architecture-Findings.md` | 28KB | Timeline |
| `Research-Output/P1-Performance-Optimization-Findings.md` | 34KB | Performance |
| `Research-Output/P1-Text-Typography-Findings.md` | 21KB | Text |
| `Research-Output/P1-Asset-Pipeline-Findings.md` | 26KB | Assets |
| `Research-Output/P2-Error-Handling-Findings.md` | 29KB | Error Handling |
| `Research-Output/P2-MCP-Interface-Findings.md` | 28KB | MCP Interface |
| `Research-Output/P2-Filter-Validation-Findings.md` | 27KB | Filter Validation |
| `Research-Output/P3-LLM-Integration-Findings.md` | 33KB | LLM Integration |
| `Research-Output/P3-Advanced-Techniques-Findings.md` | 31KB | Advanced Techniques |

**Total research corpus: ~286KB of structured findings ready for MCP implementation.**
