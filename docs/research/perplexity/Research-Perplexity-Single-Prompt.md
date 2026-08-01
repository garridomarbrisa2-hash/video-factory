# Perplexity Deep Research — Single Consolidated Prompt

**Date:** 2026-07-21
**Reasoning:** Of the ~100 gaps identified in Tavily research, most can be resolved through:
1. **Local experimentation** (run FFmpeg commands, measure results)
2. **Reading existing findings** (already documented in Research-Output/)
3. **Design decisions** (choose a safe default, iterate later)

Only a small set of gaps genuinely require multi-source external synthesis that we cannot produce locally. These are consolidated into ONE Perplexity deep-research prompt below.

---

## Gaps We Can Solve Ourselves (No Perplexity Needed)

| Gap | How to Solve |
|-----|-------------|
| Sidechain lookahead/pre-ducking | Experiment: add `adelay` to sidechain copy, A/B test with/without |
| AAC gapless joining | Design decision: use PCM intermediates → single final AAC encode (already decided in P0-Timeline) |
| zoompan jitter #4298 fix status | Experiment: run zoompan on FFmpeg 7.x with/without workarounds, visually compare |
| minterpolate throughput | Experiment: benchmark on target hardware with test clips |
| Audio-reactive pipelines | Experiment: pipe `astats` metadata into `sendcmd` or pre-computed expressions |
| NVENC cq↔crf mapping | Experiment: render test matrix, compute VMAF locally |
| QSV filter arguments | Read FFmpeg source headers + experiment |
| Color emoji in drawtext | Experiment: test with current FreeType build on Windows |
| xfade VFR behavior | Experiment: feed VFR input, observe failure mode |
| FFmpeg 7.0 color-range changes | Experiment: A/B test same command on 6.x vs 7.x |
| Windows build filter matrix | Run `ffmpeg -filters` on gyan.dev and BtbN builds, diff output |
| MCP outputSchema support | Read MCP client source code / docs directly |
| Checkpoint architectures | Design decision: scene-hash caching (already specified in P0-Timeline) |

---

## The ONE Perplexity Deep-Research Prompt

```
You are a senior video production systems architect researching for an FFmpeg-based MCP (Model Context Protocol) server that automates professional video editing. I need you to answer the following interconnected questions with verified, sourced information. Distinguish clearly between "documented fact", "community consensus", and "unknown".

---

QUESTION 1: Motion Graphics Selection Rules (CRITICAL — this drives our LLM trigger engine)

When professional video editors and motion designers choose between these visual treatments for a given script moment, what are the DECISION RULES?

Treatments: kinetic typography, animated data chart/graph, b-roll footage, split-screen comparison, lower-third overlay, highlight annotation (circle/arrow), generative animated background, picture-in-picture, transition effect

For each treatment, research:
- What script content patterns make editors choose this over alternatives? (e.g., "numbers → chart" is obvious, but when does a number become kinetic type vs a full chart vs just spoken?)
- What genre/context factors override the default choice? (e.g., documentary avoids kinetic type even for statistics?)
- What pacing/attention considerations drive the choice? (e.g., "use b-roll when viewer needs visual rest from text"?)
- Are there published studies, professional guidelines, or quantitative analyses of high-performing YouTube/broadcast content that measure which treatment performs better for which content type?

Search: professional video editing textbooks, broadcast graphics design guides, YouTube creator playbooks, academic papers on visual attention in educational video, motion graphics studio case studies, Vimeo Staff Picks breakdowns, Kurzgesagt-style edutainment production analyses.

---

QUESTION 2: ASS Subtitle Acceleration Formula (CRITICAL — this drives our animation easing system)

The libass `\t(t1,t2,accel,tags)` transformation uses an `accel` parameter that controls easing. The exact mathematical formula mapping `accel` values to easing curves is undocumented.

Research:
- Find the libass source code (GitHub: libass/libass) and identify the exact interpolation formula used for `\t` with `accel` parameter
- Map specific `accel` values to standard easing functions: what accel value = linear? = ease-in-quad? = ease-out-cubic? = ease-in-out? = ease-out-back?
- If the mapping is not 1:1 with Penner equations, provide the closest approximations
- Verify: does `\t` with `accel=1` produce linear interpolation?

Search: libass source code on GitHub (ass_render.c, ass_parse.c), libass documentation/wiki, Aegisub source code (which implements the same spec), VSFilter source code, ASS specification documents.

---

QUESTION 3: Production Checkpoint/Resume Architecture for FFmpeg Pipelines (HIGH — this drives our reliability design)

How do production video automation platforms (Canva, Kapwing, Clipchamp, cloud video editors) implement scene-level checkpointing and crash recovery for FFmpeg-based rendering?

Research:
- Do they render scenes to intermediate files and concatenate? (We believe yes, but need confirmation of the pattern)
- How do they handle transitions that span scene boundaries? (The transition needs frames from both scenes — do they render overlap regions separately?)
- How do they cache scene renders for reuse? (Content-addressable by scene JSON hash? By asset hash?)
- How do they handle partial failure: if scene 5 of 10 fails, do they re-render only scene 5, or re-render the whole timeline?
- Are there open-source implementations of this pattern we can study?

Search: open-source video editors (Shotcut, Kdenlive, OpenShot rendering pipelines), cloud video processing architectures (AWS Elemental, Mux, Cloudinary), video automation platforms (Shotstack, JSON2Video, Creatomate), conference talks on video rendering infrastructure, engineering blogs from video companies.

---

QUESTION 4: FFmpeg HEVC Alpha Channel Status 2026 (HIGH — this affects our overlay format choice)

FFmpeg ticket #9088 tracks HEVC alpha muxing support. What is the current status in FFmpeg 7.x/8.x (2026)?

Research:
- Can FFmpeg currently mux HEVC video with alpha channel into MP4 or MOV?
- Which encoders support HEVC alpha (libx265, hevc_nvenc, hevc_qsv, VideoToolbox)?
- What is the recommended workflow for HEVC-with-alpha overlays in 2026?
- If HEVC alpha is still unsupported, what is the best alternative: VP9 alpha in WebM, ProRes 4444 in MOV, or PNG sequence?

Search: FFmpeg trac ticket #9088 comments and status, FFmpeg git log for HEVC alpha commits, hevc_nvenc/hevc_qsv documentation, Apple VideoToolbox HEVC alpha support, professional video delivery format recommendations for alpha content.

---

QUESTION 5: MCP (Model Context Protocol) Production Tool Schemas for Video (HIGH — this drives our interface design)

Are there production MCP servers that expose video editing or FFmpeg functionality? If so, what are their actual tool schemas?

Research:
- Find ClipChat Engine, OpenCut MCP, or any other open-source FFmpeg MCP server on GitHub
- Extract their actual tool definitions (JSON schemas for tools/list responses)
- How do they structure composition: do they use a project/timeline handle pattern, or stateless per-call?
- What granularity did they choose: one tool per filter, one tool per recipe, or one tool per scene?
- How do they handle long-running renders: synchronous MCP calls, async job polling, or streaming progress?

Search: GitHub search for "ffmpeg mcp", "video editing mcp server", "clipchat engine", "opencut mcp", MCP server registries (mcpservers.org, glama.ai/mcp/servers), Anthropic MCP examples, Model Context Protocol GitHub discussions.

---

OUTPUT FORMAT:
For each question, provide:
## Question N: [Title]
### Answer
[Direct answer with evidence]
### Key Sources
[URLs and citations]
### Implementation Impact
[How this should influence the MCP design]
### Confidence
[High/Medium/Low with justification]
```

---

## Why These 5 Questions in 1 Prompt

1. **Motion graphics rules** — Cannot be solved locally; requires synthesizing professional editing knowledge across many sources
2. **ASS accel formula** — Requires reading libass C source code; we don't have it locally
3. **Checkpoint architecture** — Requires finding production system designs; not publicly documented well
4. **HEVC alpha status** — Requires tracking FFmpeg trac tickets and recent commits; changes frequently
5. **MCP tool schemas** — Requires finding and reading actual open-source implementations

All five are **lookup/synthesis tasks** that require web-scale research, not local experimentation. They're also **independent** — Perplexity can research them in parallel within one session.

---

## What to Do With the Answer

1. **Q1 (Motion graphics rules)** → Encode into LLM trigger engine decision rules
2. **Q2 (ASS accel)** → Build easing function lookup table for MCP text tools
3. **Q3 (Checkpoint)** → Design scene caching and partial re-render system
4. **Q4 (HEVC alpha)** → Choose overlay format (VP9 vs ProRes vs HEVC)
5. **Q5 (MCP schemas)** → Validate or adjust our tool granularity design

After Perplexity returns, we can begin MCP implementation with confidence.
