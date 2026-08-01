# Research Prompt: LLM Integration Patterns for Script-to-Video Automation

## Role
You are an NLP engineer and video production workflow designer. The goal is to define how an LLM analyzes scripts, makes creative decisions, and orchestrates the FFmpeg MCP to produce coherent, professional videos without human intervention.

## Context
The pipeline:
1. LLM receives topic → researches → writes script (voiceover + visual directions)
2. LLM segments script into scenes with timing estimates
3. LLM selects/generates assets (b-roll, images, music)
4. LLM applies motion graphics via MCP tools
5. LLM renders, validates, and iterates

Challenge: The LLM must make hundreds of micro-decisions consistently.

---

## TASK 1 — Script Segmentation & Timing

Research how to convert raw script text into timed scenes:

### Segmentation Strategies
| Strategy | Method | Pros | Cons |
|----------|--------|------|------|
| Sentence-based | Split on `.`, `!`, `?` | Precise sync with TTS | Choppy, too many scenes |
| Paragraph-based | Split on `\n\n` | Natural topics | Paragraphs vary wildly |
| Semantic | LLM marks topic shifts | Content-aware | Requires LLM analysis |
| Hybrid | Paragraphs + sentence splitting for long paragraphs | Balanced | Complex logic |

### Duration Estimation
- TTS rate: ~150 words per minute (varies by voice, language, content)
- Pause insertion: commas, periods, paragraph breaks
- Emphasis: slower for key phrases, faster for lists
- Formula: `duration = (words / 150) * 60 + pause_time`

Research: How to estimate TTS duration before generation? Use character count, word count, or syllable count?

### Scene Duration Constraints
- Minimum: 2 seconds (viewer comprehension)
- Maximum: 15 seconds (attention span, unless complex demo)
- Ideal: 4-8 seconds per scene

---

## TASK 2 — Visual Direction Extraction

Design LLM prompt to extract visual requirements from script:

### Input
```
Script: "The iPhone 15 Pro features a titanium frame, making it 10% lighter than the previous model. This aerospace-grade material is also used in the Mars rover."
```

### Output Schema
```json
{
  "scenes": [
    {
      "text": "The iPhone 15 Pro features a titanium frame, making it 10% lighter than the previous model.",
      "visual_type": "product_shot",
      "subject": "iPhone 15 Pro",
      "action": "showcase",
      "emphasis": "titanium frame",
      "comparison": "previous model",
      "data_point": "10% lighter",
      "suggested_graphics": ["product_broll", "data_counter", "comparison_overlay"]
    },
    {
      "text": "This aerospace-grade material is also used in the Mars rover.",
      "visual_type": "broll",
      "subject": "Mars rover",
      "action": "context",
      "emotion": "credibility",
      "suggested_graphics": ["mars_footage", "text_overlay"]
    }
  ]
}
```

Research: How many visual types? How to handle ambiguous directions?

---

## TASK 3 — Asset Selection & Fallback Logic

Design decision tree for asset sourcing:

### Priority Order
1. **User-provided**: Explicit uploads for this video
2. **Stock library**: Search Pexels, Pixabay, Storyblocks
3. **AI generation**: DALL-E, Midjourney, Stable Diffusion
4. **Generative**: FFmpeg `geq`, `nullsrc`, `testsrc`
5. **Fallback**: Solid color + text overlay

### Search Query Generation
From scene description: "Mars rover on red planet surface"
→ Search: "mars rover", "red planet", "space exploration", "NASA"

Research: How many search results to evaluate? How to rank relevance?

### Asset Validation Before Use
- Duration sufficient for scene?
- Resolution adequate?
- Color/style consistent with video tone?
- License allows commercial use?

---

## TASK 4 — Motion Graphics Decision Engine

Design LLM prompt for triggering motion graphics:

### Context Provided to LLM
- Script text with timing
- Available assets with metadata
- Genre/tone of video
- Current scene content (what's on screen)
- Motion graphics already used in this video (avoid repetition)
- Genre density limits (from Timing research)

### Decision Framework
```
IF scene has comparison language AND two products mentioned
  AND genre != "documentary_serious"
  AND no comparison used in last 2 scenes
  THEN add split_screen_comparison

IF scene has number/statistic
  AND number is significant (>1000 or percentage or currency)
  AND no data_viz in current scene
  THEN add data_counter

IF scene text says "look at" or "notice" or "here"
  AND current visual has identifiable region
  THEN add highlight_annotation
```

Research: How to handle conflicting triggers? Priority system?

---

## TASK 5 — Consistency & Style Enforcement

Research how to maintain visual coherence:

### Brand Style Parameters
- Color palette (primary, secondary, accent)
- Font family and weights
- Animation style (smooth, bouncy, minimal)
- Transition style (fade, wipe, glitch)

### Consistency Checks
- Same lower third style throughout?
- Same transition type at similar boundaries?
- Color scheme maintained?
- Font sizes consistent?

### LLM Prompt for Style
```
You are editing a {genre} video for {brand}.
Style guide:
- Colors: {palette}
- Fonts: {fonts}
- Animation: {animation_style}
- Transitions: {transition_style}

Apply this style consistently. Do not introduce new styles without explicit instruction.
```

---

## TASK 6 — Iterative Refinement Loop

Design feedback loop for quality improvement:

### Render → Analyze → Refine Cycle
1. LLM renders preview
2. Automated QC checks (duration, loudness, black frames)
3. LLM reviews: "Is the lower third readable? Is the transition smooth?"
4. LLM adjusts parameters and re-renders

### Human-in-the-Loop Options
- Auto-approve after N successful renders
- Flag specific scenes for human review
- A/B test two versions

---

## TASK 7 — MCP Tool Sequencing

Design typical tool call sequences:

### Simple Talking Head
```
analyze_asset(vo.mp3)
analyze_asset(bg.mp4)
create_timeline(duration=vo.duration, resolution="1920x1080")
add_scene(source=bg.mp4, audio=vo.mp3, start=0)
lower_third(text="Speaker Name", timing={start: 1, duration: 3})
render_preview()
render_final()
```

### Product Comparison
```
analyze_asset(product_a.mp4)
analyze_asset(product_b.mp4)
analyze_asset(vo.mp3)
create_timeline(duration=vo.duration + 2, resolution="1920x1080")
add_scene(source=product_a.mp4, start=0, duration=5)
add_scene(source=product_b.mp4, start=5, duration=5)
split_screen(left=scene1, right=scene2, divider_animation="slide")
data_counter(value="10%", label="Lighter", timing={start: 2, duration: 3})
render_final()
```

---

## TASK 8 — Error Recovery & Fallback Strategies

Design for common failures:

| Failure | Detection | Recovery |
|---------|-----------|----------|
| TTS duration ≠ estimate | Compare actual vs estimated | Adjust scene timing, re-render |
| Asset not found | Search returns empty | Use generative background, or skip visual |
| Motion graphic overlaps | Timeline validation | Adjust timing or remove lower priority graphic |
| Render timeout | No progress for 60s | Simplify filters, reduce resolution, retry |
| QC failure | Loudness out of range | Re-normalize audio, re-render |

---

## Final Output Format

1. **Script segmentation specification** — strategies, timing formulas, constraints
2. **Visual direction schema** — JSON format, extraction prompts, validation
3. **Asset selection logic** — priority order, search generation, validation
4. **Motion graphics decision engine** — triggers, priorities, conflict resolution
5. **Style consistency system** — parameters, checks, enforcement
6. **Iterative refinement** — feedback loops, human-in-the-loop options
7. **Tool sequencing examples** — 5-10 complete workflows
8. **Error recovery** — detection, recovery, escalation strategies
