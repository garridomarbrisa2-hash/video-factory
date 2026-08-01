# P3 — LLM Integration Findings
## Script Segmentation, Visual Direction Extraction, Asset Selection, Motion Graphics Decisions, Style Consistency

**Research date:** 2026-07-21
**Method:** Tavily web search + targeted content extraction (7 search clusters, 2 full-page extractions)
**Status:** Tavily quota exhausted partway through the final query cluster (motion-graphics decision rules). All other topics covered; residual unknowns listed in GAPS section.

---

## 1. SCRIPT-TO-VIDEO AI TOOLS — HOW EXISTING PRODUCTS SEGMENT SCRIPTS

### 1.1 Pictory (Script-to-Video)

**How it works (architecture):**
- Core feature: "Script to Video" — user pastes text or imports a document; Pictory's AI analyzes the script, "identifies visual cues," and builds scenes with matching visuals, captions, and audio.
- **Scene segmentation is user-configurable, not purely automatic:** the right-hand settings panel exposes an explicit "Scene Segmentation" option: **split scenes by sentence OR by line breaks**. This is the single most concrete, transferable finding — commercial tooling reduces segmentation to a deterministic delimiter rule with an AI layer on top.
- **Keyword Highlighting:** user (or AI) marks key terms to emphasize; highlighted terms can force a term onto "its own scene" and drive footage selection for that scene.
- **Visual Auto-Selection:** AI picks stock footage per scene based on scene text.
- **Brand Kit:** saved logo/fonts/colors applied across scenes for consistency.
- Output model: a **storyboard** of discrete scenes, each with estimated duration and visual context; scenes are drag-and-drop reorderable; transitions (wipe left/down, fades) are applied *between* scenes as a per-scene-pair attribute.
- Editing loop: scene-level preview → full-video preview render (async, takes time proportional to scene/clip count) → download/export per platform (16:9 / 9:16 / 1:1).

**Authoring guidance surfaced by Pictory's own docs/tutorials (i.e., the rules the segmentation engine rewards):**
- Break scripts into short sentences for better scene matching.
- Add punctuation for natural voiceovers.
- Use bold headlines to guide scene segmentation.
- One idea per line.

**Decision logic (observed):** one sentence (or one line) ≈ one scene ≈ one visual. Highlighted keyword = dedicated scene + targeted asset query.

### 1.2 Lumen5

- **Storyboard approach:** breaks content into scenes but leaves the user to decide what text and visuals appear in each — "semi-manual." More upfront control, slower production. Contrast with Pictory's fully-automated extraction.
- Blog-to-video: AI summarizes/extracts key sentences from a URL and drafts scenes; user confirms each.
- Implication for our pipeline: there is a proven product split between **fully-automatic segmentation** (Pictory) and **AI-proposes/human-confirms segmentation** (Lumen5). Lumen5's model is the human-in-the-loop pattern commercialized.

### 1.3 InVideo (agentic script breakdown)

**Most detailed decision-engine finding in this research.** InVideo's agentic breakdown evaluates **every scene request against 12 parameters before generating anything**:

1. Film reference
2. Shot design
3. Length
4. Style interpretation
5. Emotional register
6. Lens
7. Lighting plan
8. Color script
9. Atmosphere layers
10. Blocking
11. Final prompt
12. Negative prompt

- **Model routing:** scenes are *tagged*, and the agent routes each shot to the model whose strengths fit: Kling for multi-shot dialogue/coverage, Seedance reference-to-video for continuity-critical sequences, Veo/Runway for realism/motion. **Per-scene model routing is the decision-engine pattern.**
- **Script ingestion order matters:** upload the FULL script first for global context (character arcs, themes, motifs), then generate act-by-act. "The full script loads whole for context, then the generation work chunks act by act. Those are two different operations, and conflating them is how context gets lost."
- Multi-agent pattern: initialize a **creative-producer agent** holding full script + shot breakdown + character details as the "central vision-holder" that grounds every downstream specialist agent.

### 1.4 Synthesia & HeyGen (avatar-led)

- Both follow the same loop: **script in → avatar + scenes assembled → export out**. Both expect a finished script; neither turns messy source material into a script.
- **Synthesia:** slide-deck metaphor (like PowerPoint/Google Slides) — the video is built **scene by scene**, each scene = text boxes + images + avatar; script-based editor with timeline view; templates + brand kit enforce structure. Enterprise focus (SOC 2, LMS/SCORM, review/governance). Strong fit for "hundreds of consistent modules."
- **HeyGen:** chatbot-driven planning (prompt → drafted video plan → approval → production); scene-based editor with larger template/asset library; "system maps visuals to the script so every line has a clear on-screen moment"; auto-generates scenes, transitions, voiceover, captions. API access for programmatic/CRM-triggered generation.
- **Key shared limitation (directly relevant to our design):** a talking avatar is "a person reading a script in front of a flat background." If the video needs screen recordings, callouts, B-roll, and motion graphics, **neither tool assembles all of that** — that gap is exactly where a custom FFmpeg pipeline wins.

**HeyGen power-user prompt example (verbatim, from a tutorial — a real production prompt for motion/B-roll direction):**
> "Create B-roll to match this section of my script. Create a long form video up to 10 minutes. Use motion driven B-roll, cut scenes every five to seven seconds. Use motion graphics and animation. Leverage motion graphics as overlays to explain key concepts. Use motion graphics for checklists and key points. Incorporate abstract scientific illustrations as B-roll. Use diagrams and visualizations for neuroscience explanations. Use fade through transitions for B-roll. Combine talking avatar with multiple frames and dynamic visuals. Add charts and illustrations. Include motion graphics for statistics. Use slow elegant transitions. Add chapter breaks."

This is a **motion-graphics decision prompt in the wild**: motion graphics for (a) explaining key concepts, (b) checklists/key points, (c) statistics; B-roll for narrative; 5–7s cut cadence; fade transitions on B-roll.

---

## 2. LLM PROMPT ENGINEERING FOR CREATIVE DECISIONS

### 2.1 Academic: "From Shots to Stories" (arXiv 2505.12237) — LLM-assisted editing

**Complete Next Shot Selection prompt (verbatim, production-grade):**
> "You are an experienced film editing analyst. You will read a storyboard table containing the following information for each shot: ID, shot size, camera angle, camera movement, shot content, and subtitles.
> Your tasks are:
> 1. Read the 'Sequential Shots' information to understand the scene, rhythm, and plot logic;
> 2. Read the 'Candidate Shots' information;
> 3. Based on the following criteria, determine which candidate shot is most likely to be the next shot:
>   - Spatial continuity: whether the scene or background is consistent or naturally connected;
>   - Continuity of character actions and eye lines;
>   - Logical coherence of plot and dialogue;
>   - Reasonableness of shot language rhythm;
>   - Stylistic consistency (coordination of shot size and movement style)."

**Transferable schema:** storyboard table columns = `ID | shot size | camera angle | camera movement | shot content | subtitles`. The 5 scoring criteria are directly reusable as an LLM rubric for our asset-selection/ordering decisions.

### 2.2 Academic: "Prompt-Driven Agentic Video Editing System" (arXiv 2509.16811) — full extraction

**Architecture:** specialized agents, each owning a bounded subtask (narration planning, clip selection, beat alignment, rendering), each invoking either an LLM (Gemini) or a domain tool (**FFmpeg, ElevenLabs, custom alignment heuristics**).

**Two critical prompt-engineering findings:**
1. **"When LLMs are asked to both reason and produce structured output simultaneously, performance often degrades. Therefore, for complex tasks, we introduce intermediate freeform reasoning steps before issuing a second prompt to structure the result."** → Two-pass pattern: Pass 1 = freeform reasoning; Pass 2 = structure into JSON.
2. **Retrieval agent prompt design:** "prompted with the narration segment and instructed to concentrate its reasoning attention on the detailed, timestamped scene descriptions. The prompt is crafted to **maximize token allocation on the indexed content**, reducing cognitive overhead elsewhere." → Put the bulk of prompt tokens into candidate-asset descriptions, not instructions.

**Why multi-agent beats single-pass (their stated principles):** separation of concerns (low cognitive load per invocation); redundancy + self-correction across agents mitigates error cascades; structured, persistent intermediate outputs enable reuse.

### 2.3 Practitioner: structured generation prompts (Reddit r/PromptEngineering, CCAIPS workflow)

**Structured shot-generation prompt template (verbatim):**
> Shot type: [Wide/Medium/Close-up/POV]
> Movement: [Static/Slow pan left/Dolly forward/Tracking shot]
> Subject: [Detailed description with specific attributes]
> Environment: [Lighting conditions, time of day, weather]
> Style: [Cinematic/Documentary/Commercial]
> Technical: [4K, 24fps, shallow depth of field]
> Duration: [3/5/10 seconds]

**Structured editing-parameters prompt (verbatim):**
> Edit parameters:
> - Remove: filler words, long pauses (>2 sec), false starts
> - Pacing: Keep segments under [X] seconds, transition every [Y] seconds
> - Audio: Normalize to -14 LUFS, remove background noise below -40dB
> - Music: [Mood], start at 10% volume, duck under dialogue, fade out last 5 seconds
> - Graphics: Lower thirds at 0:15, 2:30, 5:45 following [brand guidelines]
> - Captions: Yellow highlight on key phrases, white base

**Key practitioner rules:**
- Generic prompts produce one-off results; **structured prompts with technical specifications produce repeatable results**.
- Contextual grounding: state audience + setting ("board of directors… confident, data-focused, not casual") so the LLM makes pacing/tone decisions correctly.
- Always specify **exclusions** ("Exclude the section where the customer discusses competitors around 12:00; avoid camera B in segment 1 due to audio issues").
- Semantic footage search: describe footage like you would to a colleague — visually specific + audio context ("interview segments where the marketing director discusses social media strategy and mentions Instagram metrics").
- Build a **prompt library**: mine old videos for what worked, reuse compound prompts. Reported: script time cut 6h → 2h; hybrid AI shoot $4,500/day → $600/4h.

### 2.4 Text-to-camera-shot parsing (ordinaryanimator.com)

- Base prompt + shot description appended; asks LLM for a **simple-to-parse output format** (`Subject: / Height: / From: / Distance:`).
- Lessons: small local models (Llama 7B) get angles wrong (front vs. profile); models volunteer better abstractions than instructed (ChatGPT returned "Closeup" instead of meters — semantically more useful); models add framing info that breaks machine parsing → **constrain output schema explicitly and validate**.
- Workflow tip: generate results with the prompt, manually correct them → bootstrap a fine-tuning dataset.

### 2.5 Text style transfer (arXiv 2301.11997 / EMNLP 2023 Findings)

- Prompt-based editing ("P&R" — Prompt-and-Revise) beats vanilla and distant-exemplar few-shot prompting for style transfer with small models (GPT-J-6B). Relevant pattern for rewriting on-screen text/captions into a consistent brand voice: **prompt the model to revise its own output against an explicit style rule set rather than one-shotting**.

---

## 3. TTS DURATION ESTIMATION

### 3.1 Words-per-minute baselines (multiple converging sources)

| Context | WPM |
|---|---|
| Presentations (general) | 125–145 |
| Technical / high-stakes material | 110–125 |
| Conversational content | 145–160 |
| Calculator defaults found in the wild | 130, 140, 150, 183 ("average adult," research-cited) |
| Silent reading (for comparison) | 238 |

**Canonical formula (vclar speech-time estimator):**
```
speech_time_seconds = (word_count / WPM) × 60
final_time = speech_time + pause_buffer        # pause_buffer ≈ 10–20%
```
Example: 700 words @ 140 WPM = 5:00; +10% pause buffer → ~5:30.

**Practical conversion anchors:** ~70 words per 30s @140 WPM; ~150 words/minute of finished voiceover as a safe planning figure; 65–80 words per 30s slot.

### 3.2 Pause prediction (ISCA Interspeech 2016 — "Pause Prediction from Text")

- Words followed by pauses are only **5–15% of a standard TTS corpus** → skewed class problem; evaluate with F-measure, not accuracy.
- Baseline method ("Punc"): insert pauses at punctuation (comma, colon, semicolon, hyphen, quotes). Learned models beat punctuation-only but punctuation is a strong baseline.
- Features for pause prediction per word: presence/absence of following punctuation; content-word vs. function-word; trained on phone-level aligned corpora (silences vs. pauses distinguished).
- **Practical rule for our pipeline:** punctuation-driven pause insertion + 10–20% global buffer gets within useful tolerance; per-word ML pause models are a refinement, not a prerequisite.

### 3.3 Duration modeling for dubbing/sync (Amazon Science — neural TTS duration modeling)

- Proxy method used in production dubbing pipelines: run TTS on the full sequence with no pauses → **force-align audio to text** → compute per-word durations from timestamps ("TTS + FA").
- Trained duration models (frame-level/Gaussian, BiLSTM) speed prosodic-alignment training/inference ~100× vs. the TTS+FA proxy.
- **Directly actionable:** the most reliable duration estimate is *generate the audio first, then measure it* (force-align or just read container duration), rather than predicting from text. This matches the pipeline finding in §5 ("Real media-duration detection" as a required reliability feature). Use WPM math for *planning/scene budgeting*; use measured audio duration for *render timing*.

---

## 4. STOCK VIDEO/IMAGE SEARCH APIs

| API | Auth | Default limits | Media | Key constraints |
|---|---|---|---|---|
| **Pexels** | `Authorization` header w/ API key (instant) | 200 req/hour, 20,000 req/month (raisable to unlimited free w/ attribution) | Photos **+ videos** | Prominent linkback expectation; max 80 items/page |
| **Pixabay** | `key` query param (signup + approval friction) | 100 req/60s | Images + videos + music | **Must cache responses 24h; no permanent hotlinking — download & self-host**; max 500 videos/query; full-res URLs only after full-access approval |
| **Unsplash** | `Client-ID` | 50/hour demo → 1,000–5,000/hour after production approval | **Photos only** | Hotlinking + attribution workflow required |

**Pexels video search specifics (from OpenAPI spec):** `/videos/search` with `query`, `orientation` (landscape/portrait/square), `size` (large/medium/small), `locale`, pagination; `/videos/popular` with `min_width`, `min_height`, `min_duration` — **server-side duration filtering exists**, valuable for matching assets to scene budgets.

**Integration patterns for automated pipelines (from Themeisle's multi-provider implementation — a production fallback design):**
- **Provider fallback chain:** Primary stock search → Fallback 1: first content image → Fallback 2: title-generated image → Fallback 3: default image. "Never leave posts without images."
- **Rate-limit handling:** on 429 → switch provider (priority order), wait for reset, use cached results, enable request throttling. Distribute requests across multiple APIs; schedule heavy jobs off-peak.
- **Quota monitoring:** alert at 80% of limit; cache search results (multi-day cache duration) to cut API calls.
- **Common failure cause:** query too specific / filters too restrictive → **query-broadening retry** is a needed behavior (see §7).

**FFmpeg integration point:** Pixabay's no-hotlinking rule and Pexels' attribution model both push toward the same architecture our pipeline already implies: **download selected assets to local/scene-level storage first, normalize with FFmpeg, then render** — never stream remote assets into a render graph at concat time.

---

## 5. AI VIDEO GENERATION PIPELINES — SCRIPT → SCENE → ASSET → RENDER

### 5.1 Reference architecture (DEV Community, full extraction)

Canonical stage list (each stage can fail independently):
```
Document Upload → Text Extraction → Document Classification →
Information Structuring → Script Generation → Scene Planning →
Visual Prompt Generation → Image/Background Generation → Voice Generation →
Avatar/Motion Generation → Scene Rendering → Video Composition →
Final Encoding → Publishing
```
Minimal viable pipeline: `Document → Structured JSON → Scene Script → Generated Images → Generated Narration → FFmpeg Motion → Final Video`.

**Per-stage failure examples (their list):** PDF parsing fails on scanned images; **LLM returns invalid JSON**; image API rejects a prompt; voice provider times out; **generated video has a different duration than expected**; FFmpeg runs out of memory; final upload fails after render succeeds.

**Reliability requirements (their checklist):** structured document extraction · explicit workflow states · provider-independent interfaces · background job processing · bounded concurrency · **idempotent operations** · **scene-level asset storage** · **real media-duration detection** · **consistent FFmpeg normalization** · accurate progress reporting · cost tracking · privacy/security · **recovery from partial failure**.

**UX principle:** separate planning from rendering; never hide every decision behind AI — users review extracted info → scene outline → narration → style → preview → **regenerate individual scenes** → export.

### 5.2 n8n "Ads Factory" pipeline (production workflow template)

Four stages: (1) Image generation (prompt agent → image model → Drive); (2) **Scene scripting — a vision model analyzes the generated image for visual consistency, then Claude Opus converts the user script into structured 8-second scenes with consistent visuals and environment-aware motion prompts**; (3) Clip generation per scene (Veo3, poll until complete, per-scene status in Google Sheets); (4) Stitching via **fal.ai FFmpeg** after all clips complete.

**Error handling pattern:** two-sheet state model — `Videos` (campaign status: Create→Processing→Completed/Failed) and `Video Data` (one row per scene: scene JSON, scene #, image URL, clip links, per-scene status). **Retry = set scene status to `Redo`**; scheduled triggers reprocess Redo rows every 15 min. Scene-level granularity is what makes retries cheap.

### 5.3 Multi-agent pipeline (MindStudio) + GitHub reference implementation

Five agents in sequence, each consuming the previous agent's output: **Script Agent** (GPT-4o/Claude, structured script) → **Storyboard Agent** (scene-by-scene visual directions) → **Image/Video Generation Agent** (FLUX etc., outputs auto-stored) → **Voice Agent** (ElevenLabs/OpenAI TTS per section) → **Assembly Agent** (video rendering API). 10–20 min for a 3–5 min video. Cost estimate for 5-min explainer: script $0.05–0.20, 10 images $0.50–2.00, voice $0.50–1.50, render $1.00–3.00.

GitHub `ai-video-generation-pipeline` adds: script generation with **camera directions and emotion/emphasis markers in dialogue**; voice synthesis with **audio-duration matching to scene length**; **automatic consistency validation between scenes + audio-video sync verification**; resumable checkpoints; 95%+ character-consistency score via an "Asset-First" approach.

### 5.4 Character-consistency pipeline (arXiv 2512.16954, "Lights, Camera, Consistency")

- LLM (Gemini 2.5) prompted as screenwriter+director outputs a **structured JSON blueprint** with strict scene constraints.
- **"Asset-First" mechanism:** decouple character design from scene generation; character references condition every scene's initial frame — zero-shot consistency without LoRA/fine-tuning.
- **Iterative scene synthesis:** for each scene, an LLM decides whether to incorporate the **final frame of the preceding scene** as continuity conditioning; Image-to-Image generates the initial frame conditioned on scene description + character references + prior frame.
- Philosophy: "structured deterministic control via JSON blueprints" rather than probabilistic agent simulation.

### 5.5 Vidu practitioner rules (short-form reality check)

- **Write scene-by-scene, not story-by-story. One subject, one action, one camera position per clip. If the scene has a transition, split it.**
- "What script-to-video AI is actually good at: producing scene-level assets that a creator then sequences. The script determines the shot list; the model executes each shot individually."
- Consistency requires **reference anchors** (saved asset library) — models don't hold narrative across long prompts.

### 5.6 FFmpeg/JSON render-layer integration

- **JSON2Video:** JSON scene manifest → cloud render. Scenes contain typed elements (text, image, video, voiceover, captions) with durations; template placeholders enable personalization at scale. This is the "scene manifest" pattern our MCP can emit/consume.
- **Shotstack:** entire edit described as JSON timeline; API renders in cloud — positioned explicitly as "FFmpeg without the syntax/infra pain."
- **FFmpeg concat decision table (ffmpeg-micro):**
  - Same codec/resolution/framerate → **concat demuxer** (no re-encode, fastest)
  - Mismatched specs → **concat filter** (re-encode)
  - Need transitions (fade/slide) → **concat filter + xfade**
  - Transport streams → concat protocol
- **Crossfade filtergraph pattern (working example):**
  ```
  [0:v]fade=t=out:st=19.5:d=0.5[v0];
  [1:v]fade=t=in:st=0:d=0.5,fade=t=out:st=9.5:d=0.5[v1];
  [v0][0:a][v1][1:a]concat=n=2:v=1:a=1[outv][outa]
  ```
  Rule: `fade-out start = clip_length − fade_duration`.
- **Prerequisite for concat:** per-input filtering must complete before concat (e.g., subtitles burned per-segment first); inputs must be normalized (resolution, fps, SAR, audio rate) — hence "consistent FFmpeg normalization" as a pipeline stage.

---

## 6. VISUAL CONSISTENCY ENFORCEMENT

### 6.1 Brand-kit pattern (commercial consensus)

- **Pictory / VEED / Canva / HeyGen brand kits:** centralized store of logos, fonts, color palettes, media assets, intro/outro templates; applied automatically to every scene; review/lock features so stakeholders can approve without editing access. "Lock down visual identity while giving creators room to innovate."
- **Typeface (5-step brand training):** collect 15–20 images representing ideal aesthetic → upload as Brand Kit training set → **tag each with style attributes (lighting, palette, composition)** → generate test images → refine the training set based on outputs.

### 6.2 Style-extraction tooling

- **OpenCreator Branding Visual Style Extractor:** upload brand assets (logos, ads, screenshots) → AI extracts **color palettes, design motifs, composition patterns, aesthetic characteristics** → generates derivatives matching the extracted "visual DNA." This is palette/motif extraction as a service — the same extraction can be done locally (e.g., colorthief-style palette extraction on brand assets) and injected into LLM prompts and FFmpeg color parameters.
- **Midjourney-style pattern (r/graphic_design):** style-reference codes (`--sref`) lock lighting/color/composition across generations; maintain a **style library = color palettes + reference codes + prompt templates**; test styles side-by-side; document the process for repeatability.

### 6.3 SOP / governance layer (Venngage, Speak Agency)

- **Translate brand guidelines into explicit AI-followable rules** — vague rules ("use friendly icons") fail because models interpret them differently than designers.
- Guidelines must specify: logo variations & safe zones; primary/secondary/accent palettes; approved fonts/weights; acceptable imagery styles.
- **One-page QC checklist (their template):** (1) Colors within official palette? (2) Heading/body typography correct? (3) Logo present, sized, in safe zone? (4) Contrast/legibility pass? (5) Recognizable as our brand without the logo? Include visual pass/fail examples; run as a final pre-publish gate — a **deterministic validator step in the pipeline** (automatable: palette-distance check, font check, logo-overlay check).

### 6.4 Programmatic enforcement points for our pipeline

1. Palette extraction from brand assets → inject hex colors into scene JSON (background colors, caption colors, lower thirds).
2. FFmpeg color enforcement: overlay/logo placement filters, drawtext with brand fonts/colors, optional `eq`/`colorbalance` nudge toward palette.
3. LLM prompt scaffolding: carry a `style_guide` block (palette hexes, mood adjectives, forbidden elements = negative prompts) into every visual-direction prompt.
4. Consistency validation between scenes (per §5.3) as an automated QA stage before concat.

---

## 7. ERROR RECOVERY IN AUTOMATED VIDEO PRODUCTION

### 7.1 Agent-level recovery patterns (GoCodeo)

- **Checkpointing:** save state after each successful step; rewind plan to most recent checkpoint; store side effects reversibly.
- **Human-in-the-loop escalation:** escalate to human review when confidence is low or failure persists; integrate preview diffs/logs into UI; allow manual override at key checkpoints; **capture human corrections to improve prompts/fallback logic**.
- Design principles: **Observability first** (structured logs: retry counts, fallback paths, failure reasons); **Validation over trust** (schema + syntax + semantic validation of every LLM output before execution).

### 7.2 The critical fallback-corruption finding (Towards Data Science)

- **A completed pipeline ≠ a working pipeline.** Real case: Executor hit 429 → retry loop swapped to fallback model → pipeline reported 100% completion, no errors — but the fallback's output was schema-incompatible ("incomplete – schema mismatch during swap"), and the downstream Validator silently received broken data.
- **Rules:** treat a model/provider swap as a **data-integrity event, not an infrastructure retry** — snapshot before swap, adapt the payload to the fallback's schema, tell the fallback explicitly what state it landed in. Monitor goal achievement, not just HTTP 200s and clean exits.
- **Adaptive retries:** don't retry with the identical prompt — vary the prompt, the model, or the strategy.

### 7.3 LLM resilience toolkit (Uplatz production patterns)

- Retry strategies: exponential backoff; token-aware retry; **query transformation on retry**; context-window trimming on failure.
- **Self-repair loop:** when structured output has a small format error, feed the error back to the LLM ("you messed up the formatting here, fix it") instead of discarding the response.
- Graceful fallback hierarchy: backup model → cached answer to similar prior request → degraded-but-helpful response. "Never leave the user at a dead end."
- Output validation gates: safety + format + intent checks post-generation.
- Human handoff designed as a **core feature**, not a fallback.

### 7.4 Video-pipeline-specific recovery (from §5 sources, consolidated)

- **Scene-level retries** (n8n Ads Factory): per-scene status rows; `Redo` flag reprocessed on schedule. Failed scenes never block completed ones.
- **Idempotent operations + resumable checkpoints** (GitHub pipeline): pause/resume from checkpoints; re-running a stage must not duplicate side effects.
- **Regenerate individual scenes** in the UX (DEV architecture): preview → regenerate one scene → re-render only affected composition segment.
- **Provider fallback chain for assets** (Themeisle, §4): primary → content-derived → generated → default; query broadening on empty results; 429 → switch provider + cache.
- **Duration-mismatch handling:** generated media duration ≠ planned duration is an expected failure mode → measure actual durations (ffprobe/force-align) and re-time the scene manifest before render rather than trusting estimates.
- **Validation stages:** schema-validate LLM JSON before any tool call; verify audio-video sync post-render; format-validate per target platform; optional manual review gate before publish.

---

## CONSOLIDATED DESIGN IMPLICATIONS FOR THE FFMPEG MCP PROJECT

1. **Segmentation:** default rule = sentence/line-break splitting (Pictory model), upgraded by an LLM pass that merges/splits on semantic boundaries; expose the rule as a user setting, not hidden magic.
2. **Scene manifest:** JSON blueprint per video — scenes with `{id, narration, visual_prompt, negative_prompt, asset_query, duration_budget, transition, style_tags}`; two-pass LLM (reason → structure) to build it.
3. **Duration:** plan with WPM math (140 WPM default, +10–20% pause buffer); render with measured TTS duration (ffprobe); re-budget scenes from actuals.
4. **Asset selection:** LLM generates visually-specific queries → Pexels primary (video+duration filters) → Pixabay fallback (self-host) → generated/default terminal fallback; cache results; broaden query on empty.
5. **Consistency:** brand-kit block (palette hexes, fonts, logo path, style adjectives, negatives) injected into every prompt; palette/logo/font enforcement + QC checklist as a deterministic validation stage.
6. **Render:** normalize all assets first; concat demuxer when uniform, concat filter + xfade when transitions; subtitles/lower-thirds burned per-scene before concat.
7. **Recovery:** per-scene status + Redo semantics; checkpoint after each stage; schema-validate every LLM output; self-repair prompt on format errors; human review gate before publish; treat any provider/model swap as a data-integrity event.

---

## GAPS REQUIRING PERPLEXITY DEEP RESEARCH

The following could not be resolved with Tavily (final query cluster failed on quota; some topics only partially covered):

1. **Motion-graphics decision rules** — The explicit rule set for *when* an automated system should choose kinetic typography vs. animated charts vs. B-roll vs. talking head. Only anecdotal evidence found (the HeyGen prompt: motion graphics for concepts/checklists/statistics, B-roll for narrative, 5–7s cut cadence). Need: formal heuristics, explainer-video industry conventions, any published decision trees.
2. **InVideo's 12-parameter schema internals** — the parameters are named but their value spaces, weights, and how the agent resolves conflicts between them are undocumented publicly. Worth a deep research pass on InVideo's agent documentation/patents.
3. **Lumen5's summarization/segmentation algorithm** — only marketing-level descriptions found ("AI extracts key sentences"). No technical detail on their NLP approach (TextRank-style extraction vs. LLM).
4. **Pause prediction SOTA (2024–2026)** — found 2012–2016 literature (punctuation baselines, 5–15% skew, ToBI break models). Modern LLM-era prosody/pause prediction (e.g., how ElevenLabs/Azure/Google handle pause markup, SSML break-time tuning norms) not retrieved.
5. **TTS per-provider duration variance** — no data found on how much actual TTS duration deviates from WPM estimates per provider (ElevenLabs vs. OpenAI vs. Azure vs. Kokoro), which determines how large the re-budgeting correction loop needs to be.
6. **Color-palette distance metrics for automated QC** — the "colors within official palette?" check needs a concrete metric (ΔE in CIELAB? palette histogram distance?). No implementation-level guidance found.
7. **Benchmarks for LLM structured-output reliability in scene manifests** — general "validate LLM JSON" advice found, but no measured failure rates per model or best-in-class repair-loop implementations specific to video pipelines.
8. **Licensing/attribution automation** — how production systems track per-asset attribution requirements (Pexels linkback vs. Pixabay none-required) in rendered output metadata; only ToS-level info found.
9. **xfade/transition performance at scale** — re-encode cost and memory behavior of concat-filter + xfade graphs for 50+ scene videos (FFmpeg OOM was listed as a failure mode but without mitigation detail: chunking strategies, two-pass assembly, intermediate mezzanine files).
10. **Human-in-the-loop UI patterns specific to storyboard review** — Lumen5/Pictory expose review UIs, but no design-pattern literature on review-gate placement (post-script? post-storyboard? post-preview?) and its effect on throughput/quality trade-offs.
