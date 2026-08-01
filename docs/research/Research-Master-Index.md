# FFmpeg MCP Research Master Index

Complete research program for building a production-grade FFmpeg MCP server for video automation.

**All research complete.** All 10 prompts executed → 10 findings docs produced. Synthesis + Perplexity aggregation consolidated.

**Repository layout:**
- `prompts/` — 10 research prompts (P0-P3)
- `findings/` — 10 findings docs (P0-P3)
- `motion-graphics/` — 3 user-provided motion graphics research docs
- `synthesis/` — design decisions + gap analysis
- `perplexity/` — single-prompt aggregation + raw answer

---

## Research Documents Completed

### Existing Research (User-Provided)

| Document | Path | Focus | Status |
|----------|------|-------|--------|
| `Research-FFMPEG-MotionGraphics.md` | `motion-graphics/` | Filter catalog, motion graphics recipes, gap analysis | ✅ Complete |
| `Research-MotionGraphics-Timing1.md` | `motion-graphics/` | Trigger logic, genre guidelines, anti-patterns | ✅ Complete |
| `Research-MotionGraphics-Timing2.md` | `motion-graphics/` | Extended trigger logic with examples | ✅ Complete |

---

## New Research Documents (All Executed ✅)

### P0 — Critical Path (Blockers for MVP)

| Priority | Document | Research Prompt | Findings | Key Deliverables |
|----------|----------|---------------|---------|----------------|
| **P0** | **Audio Mastery** | `prompts/P0-Audio-Mastery.md` | `findings/P0-Audio-Mastery-Findings.md` | Auto-ducking, loudness normalization, TTS sweetening, audio analysis tools |
| **P0** | **Timeline Architecture** | `prompts/P0-Timeline-Architecture.md` | `findings/P0-Timeline-Architecture-Findings.md` | Multi-scene assembly, transition chaining, frame-accurate timing, MCP timeline schema |

**Why P0**: Without audio and timeline, you have motion graphics demos, not videos.

---

### P1 — High Priority (Required for Production)

| Priority | Document | Research Prompt | Findings | Key Deliverables |
|----------|----------|---------------|---------|----------------|
| **P1** | **Performance Optimization** | `prompts/P1-Performance-Optimization.md` | `findings/P1-Performance-Optimization-Findings.md` | Hardware acceleration matrix, parallelization, quality/speed decision tree |
| **P1** | **Text & Typography** | `prompts/P1-Text-Typography.md` | `findings/P1-Text-Typography-Findings.md` | ASS subtitle engine, kinetic typography library, dynamic layout, font management |
| **P1** | **Asset Pipeline** | `prompts/P1-Asset-Pipeline.md` | `findings/P1-Asset-Pipeline-Findings.md` | Format compatibility, normalization, color management, alpha handling, QC automation |

**Why P1**: Without these, you'll have slow renders, ugly text, and asset compatibility issues.

---

### P2 — Medium Priority (Required for Reliability)

| Priority | Document | Research Prompt | Findings | Key Deliverables |
|----------|----------|---------------|---------|----------------|
| **P2** | **Error Handling & Validation** | `prompts/P2-Error-Handling.md` | `findings/P2-Error-Handling-Findings.md` | Input validation, dry-run testing, error taxonomy, retry logic, QC automation |
| **P2** | **MCP Interface Contract** | `prompts/P2-MCP-Interface.md` | `findings/P2-MCP-Interface-Findings.md` | Tool granularity, JSON schemas, composition model, LLM prompt templates |
| **P2** | **Filter Validation Matrix** | `prompts/P2-Filter-Validation.md` | `findings/P2-Filter-Validation-Findings.md` | Tier classification, per-filter validation, version compatibility, exposure strategy |

**Why P2**: Without these, your MCP will crash on edge cases and expose dangerous filters to the LLM.

---

### P3 — Enhancement (Competitive Advantage)

| Priority | Document | Research Prompt | Findings | Key Deliverables |
|----------|----------|---------------|---------|----------------|
| **P3** | **LLM Integration Patterns** | `prompts/P3-LLM-Integration.md` | `findings/P3-LLM-Integration-Findings.md` | Script segmentation, asset selection, decision engine, style consistency, error recovery |
| **P3** | **Advanced Techniques** | `prompts/P3-Advanced-Techniques.md` | `findings/P3-Advanced-Techniques-Findings.md` | Screen replacement, object tracking, audio-reactive visuals, external tool integration |

**Why P3**: These differentiate your factory from basic automation and enable premium content quality.

---

## Synthesis & Aggregated Research

| Document | Path | Focus |
|----------|------|-------|
| `Research-Synthesis-Design-Decisions.md` | `synthesis/` | Consolidated design decisions derived from all findings |
| `Research-Synthesis-Perplexity-Gaps.md` | `synthesis/` | Gap analysis across Perplexity aggregation |
| `Research-Perplexity-Single-Prompt.md` | `perplexity/` | Single combined prompt for full-pipeline research |
| `Research-Perplexity-Answer.md` | `perplexity/` | Raw Perplexity answer (61KB corpus, multi-topic) |

---

## Research Execution Order

### Phase 1: Foundation (Week 1-2)
1. Execute **P0-Audio-Mastery** — can you duck music under voiceover?
2. Execute **P0-Timeline-Architecture** — can you assemble 3 scenes with transitions?
3. Execute **P1-Text-Typography** — can you render broadcast-quality lower thirds?

**Milestone**: Render a 30-second video with voiceover, music, 3 scenes, transitions, and lower thirds.

### Phase 2: Production Readiness (Week 3-4)
4. Execute **P1-Performance-Optimization** — how fast can you render?
5. Execute **P1-Asset-Pipeline** — can you handle any input format?
6. Execute **P2-Filter-Validation** — which filters are safe to expose?

**Milestone**: Render a 5-minute video with 10 scenes, mixed assets, and <5 minute render time.

### Phase 3: Reliability & Polish (Week 5-6)
7. Execute **P2-Error-Handling** — does it recover from failures?
8. Execute **P2-MCP-Interface** — is the LLM interface clean and composable?

**Milestone**: MCP server handles 100 renders with 99% success rate, auto-recovery from common failures.

### Phase 4: Intelligence (Week 7-8)
9. Execute **P3-LLM-Integration** — does the LLM make good creative decisions?
10. Execute **P3-Advanced-Techniques** — can you do screen replacement and object tracking?

**Milestone**: Full pipeline from topic → script → assets → render with minimal human intervention.

---

## How to Use These Research Prompts

Each prompt is designed for execution by a research-capable LLM (Perplexity, GPT-4, Claude, etc.) with web access.

### Execution Template
```
You are executing a research task for an FFmpeg MCP server project.

Read the attached research prompt carefully. Execute all tasks thoroughly.
Use official FFmpeg documentation (ffmpeg.org) as primary source.
Cross-reference with community knowledge (Stack Overflow, Reddit r/ffmpeg, video production forums).
Validate all commands with actual FFmpeg execution where possible.

Output a structured document following the format specified in the prompt.
Include working commands, parameter tables, decision trees, and code examples.
Mark any uncertain information with [VERIFY] for manual validation.

Research Prompt:
[attach P0-Audio-Mastery.md or other]
```

### Validation Checklist
After receiving research output:
- [ ] All commands execute without error on FFmpeg 6.0+
- [ ] JSON schemas are valid and parseable
- [ ] Performance claims have benchmark data
- [ ] Gap analysis acknowledges limitations honestly
- [ ] MCP tool definitions are implementable

---

## Integration with Existing Research

Your existing motion graphics and timing research feeds into:

| New Research | Uses Your Existing Research For |
|-------------|--------------------------------|
| P0-Timeline | Motion graphics catalog → scene overlay placement |
| P1-Text | Kinetic typography patterns → ASS implementation |
| P2-MCP-Interface | Trigger logic → tool design and LLM prompts |
| P3-LLM-Integration | Genre density guidelines → decision engine rules |
| P3-Advanced | Gap analysis → external tool integration priorities |

---

## Success Criteria for Complete MCP

After all research is executed and integrated, your MCP should:

1. **Accept** a script or topic from an LLM
2. **Analyze** and segment into scenes with timing
3. **Source** or generate appropriate assets
4. **Compose** scenes with motion graphics, transitions, and audio
5. **Render** in reasonable time with hardware acceleration
6. **Validate** output quality automatically
7. **Recover** from failures gracefully
8. **Learn** from feedback to improve future renders

---

## Next Immediate Actions

1. **Execute P0-Audio-Mastery** — highest blocker
2. **Execute P0-Timeline-Architecture** — second blocker
3. **Prototype**: Build a 3-scene video with voiceover, music, and lower thirds using your existing research + new audio/timeline research
4. **Validate**: Does the prototype render correctly? Is it maintainable?
5. **Iterate**: Refine research based on prototype learnings

Start with P0. The audio and timeline research will immediately expose gaps in your current approach and drive the rest of the architecture.
