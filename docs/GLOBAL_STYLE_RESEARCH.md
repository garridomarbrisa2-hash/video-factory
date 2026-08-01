# Global Style System — Research Basis

**Date:** 2026-07-22
**Sources:** VidRush official docs (docs.vidrush.ai), Remotion official docs (remotion.dev), competitor platform docs (InVideo, Pictory, Lumen5, OpusClip).

This file is the **evidence base** for the global style system. Every style parameter in `pipeline/intelligence/styles/` must trace back to something documented here. Do not invent style values ad hoc.

---

## 1. What VidRush actually does (official docs)

### 1.1 Themes = the "look and feel" layer

From `docs.vidrush.ai/docs/themes`:

> "Themes control the visual identity of your video: **fonts, colors, animations, text overlays, graphics, and transitions**. Think of it as the 'look and feel' layer that sits on top of your content."

VidRush offers exactly **five themes**:

| Theme | Official description | Target content (official) |
|-------|---------------------|---------------------------|
| **Crime** | "A dark and intense theme… dramatic visual elements" | True crime, conspiracy, mystery |
| **History** | "A classic and timeless theme" | Historical documentaries, educational, period pieces |
| **Modern** | "Sleek and contemporary… clean lines and vibrant colors" | Tech, business, lifestyle, news |
| **Minimalist** | "Clean and simple… subtle animations" | Corporate, product, clean educational |
| **Standard** | "Versatile, well-balanced, neutral styling" | General purpose / unsure → start here |

Plus a **Background image** layer the user picks separately (swap-able post-render without re-render).

### 1.2 Prompt ↔ theme split of responsibility

From `docs.vidrush.ai/docs/prompt`:

- **Prompt controls:** format ("documentary", "top 10"), length, title, talking points, exact hook lines, CTA, **Style:** and **Tone:** declarations (e.g. `Style: Serious investigative journalism`, `Tone: Neutral but highlighting tensions`).
- **Theme controls:** everything visual — fonts, colors, animations, overlays, transitions.
- Explicitly banned in prompts: editing instructions ("Use dramatic transitions", "Put text on screen saying…"). *"Focus on WHAT to talk about, not HOW to show it."*

From `docs.vidrush.ai/docs/reference-video` (feature now removed, but the principle remains):

> Reference video influenced **writing style, sentence flow, vocabulary, pacing, narrative tone. It did NOT influence visuals, B-roll, editing style, transitions.**

**Conclusion for our clone:** the *script layer* owns style/tone words; the *theme layer* owns all motion/visual decisions. Our `global_style` must therefore be chosen from topic/brief at script time and then **drive both** (a) script pacing guidance and (b) the visual theme deterministically.

### 1.3 VidRush content formats (prompt templates)

Official prompt templates define four recurring formats:

1. **Documentary Style** (10–12 min) — Historical Context / Current Situation / Expert Perspectives / Future Implications. Tone: serious, analytical.
2. **Top 10 / Listicle** (12–15 min) — countdown, item → key fact → why it matters. Tone: informative but entertaining.
3. **Mystery/Investigation** (15–18 min) — mystery → investigation → revealing details → truth. Tone: mysterious, compelling.
4. **Crisis/News** (8–10 min) — breaking point → numbers → ground zero → causes → human cost → what's next. Tone: urgent, fact-driven.

**Golden rule of density:** ~0.5 talking points per minute (6–8 min → 4–5 points; 10–12 min → 7–8 points; 30–40 min → 20–30 points).

**Theme selection impact (official):** "Crime/History theme: darker maps, dramatic fonts. Standard theme: satellite imagery, clean graphics. Choose based on content tone, not personal preference."

### 1.4 Competitor evidence (secondary)

| Platform | Style mechanism | Relevant detail |
|----------|----------------|-----------------|
| **Pictory** | Styles Library | Each style bundles **font combination + color palette + text animation type + scene transition design**. Layouts: Default, Title, Emphasis, Quote, List, Number. |
| **InVideo** | Motion-graphics blocks | Hook cards ~2s, hooks of 3–5 words, structure hook→problem→proof→CTA; template/art-style "locking". |
| **OpusClip** | Brand templates | Named presets (Karaoke, Popline, Simple) = typography + highlight colors + caption behavior. |
| **Lumen5** | Scene-type guidance | Break long text into sub-scenes; dedicated templates for intros/quotes/data highlights. |

Cross-platform convergence: a style = **{typography set, palette, text animation, transition design, pacing rules}**. This validates our style-JSON schema.

**Evidence gaps (documented):** no platform publishes exact transition durations, easing curves, or LUT/grade values. Those numbers are our own design decisions, guided by `docs/PRO_EDIT_STYLE.md` — and must be marked as such.

---

## 2. Remotion capability inventory (official docs)

### 2.1 Transitions — `@remotion/transitions` (v4.0.53+)

Installed in `remotion/node_modules/@remotion/transitions`. Two-part model:

**Presentation** (what it looks like) — 17 built-ins:

| Presentation | Editorial feel | Style fit |
|--------------|----------------|-----------|
| `fade()` | Soft crossfade | Standard, Minimalist |
| `dissolve()` | Film dissolve | History, Crime |
| `wipe()` | Directional linear wipe | Modern, news |
| `slide()` | Push/slide | Modern, energetic |
| `flip()` | 3D flip | (sparingly) |
| `clockWipe()` | Clock radial wipe | History (period feel) |
| `filmBurn()` | Film burn | Crime, History |
| `crossZoom()` | Zoom through | Modern, energetic |
| `dreamyZoom()` | Soft zoom blur | Storytelling |
| `linearBlur()` | Motion blur push | News, urgent |
| `ripple()` | Ripple | (rare) |
| `swap()` | Swap places | (rare) |
| `zoomBlur()` | Zoom + blur | Energetic |
| `zoomInOut()` | Punch in/out | Energetic |
| `bookFlip()` | Page turn | History (book/period) |
| `crosswarp()` | Warp | (rare) |
| `none()` | Hard cut | Documentary, news |

**Timing** (how long + curve):

| Timing | Use |
|--------|-----|
| `linearTiming({durationInFrames})` | Editorial, broadcast feel (linear = pro) |
| `springTiming({config})` | Bouncy product feel — use with `damping` high to kill bounce |

**Hard rules (from docs):**
1. Transition must not be longer than either adjacent sequence.
2. Two transitions cannot be adjacent.
3. Two overlays cannot be adjacent.
4. A transition and an overlay cannot be adjacent.
5. Total duration = Σ sequences − Σ transitions (transitions overlap).

`<TransitionSeries.Overlay>` (v4.0.415+) renders over a cut point without shortening the timeline — useful for film-burn flashes, light leaks on Crime/History styles.

### 2.2 Animation primitives

- `spring({frame, fps, config:{mass, damping, stiffness, overshootClamping}, durationInFrames, delay})` — physics-based; overshoots unless clamped. Per `PRO_EDIT_STYLE.md`, springs are **banned for editorial text** (product-motion tell) except where a style explicitly wants energy (Modern stat pops with `overshootClamping`).
- `interpolate()` + `Easing` — our `editMotion.ts` already enforces `Easing.linear` for opacity/wipes.
- Current batch renderer uses **FFmpeg `xfade` between separately rendered scene clips** (not `<TransitionSeries>`). Rationale: keeps Chrome raster bursts short, NVENC per clip. *Decision: keep FFmpeg xfade as the assembly mechanism; style JSON picks the xfade transition type. `<TransitionSeries>` is reserved for future single-render mode.*

### 2.3 FFmpeg xfade mapping (what we render with today)

Our assembly layer maps style → xfade type:

| Remotion presentation equivalent | FFmpeg xfade | Notes |
|----------------------------------|--------------|-------|
| `none()` | concat (no xfade) | Hard cut — documentary/news default |
| `fade()` | `fade` | Crossfade |
| `dissolve()` | `dissolve` | |
| `wipe()` | `wipeleft` / `wiperight` | Directional |
| `slide()` | `slideleft` / `slideright` | |
| `clockWipe()` | `circleopen` | Closest xfade equivalent |
| `filmBurn()` | `fadeblack` / `fadewhite` | Approximation |

---

## 3. Style mapping matrix (research → parameters)

Style IDs mirror VidRush's five themes, extended with content-format knowledge from the prompt templates. `edit_style` enum in `timeline_schema.json` changes from `documentary|storytelling|listicle|explainer|commentary` to **`crime|history|modern|minimalist|standard`** (VidRush parity), keeping our old names as aliases.

### 3.1 Crime (`crime`)
- **VidRush:** dark, intense, dramatic visual elements; darker maps, dramatic fonts. Formats: Mystery/Investigation (15–18 min).
- **Palette:** near-black backgrounds, desaturated red accent, high-contrast white type.
- **Typography:** condensed/dramatic serif or heavy grotesque; slow mask-wipe reveals.
- **Transitions:** `fadeblack` (film-burn analog) or hard cut; 10–15f.
- **B-roll:** dark keywords (night, interrogation, evidence, archive); heavy darken (0.6), strong vignette, film grain.
- **VO:** suspenseful, measured, long pauses (`—`, `...`).
- **Talking points density:** 0.5/min; mystery structure (mystery → investigation → details → truth).

### 3.2 History (`history`)
- **VidRush:** classic, timeless; documentaries, period pieces. Documentary prompt format (10–12 min).
- **Palette:** sepia-leaning neutrals, parchment/paper tones, muted gold accent.
- **Typography:** classic serif; `clockWipe`/`bookFlip`-feel transitions for chapter changes.
- **Transitions:** `dissolve` 12–15f or `circleopen` (clock-wipe analog).
- **B-roll:** archive, maps, paintings, monuments; slow Ken Burns 3–5%; grain.
- **VO:** authoritative, measured, documentary-narrator (Fern/Lemmino reference per VidRush library).

### 3.3 Modern (`modern`)
- **VidRush:** sleek, contemporary, clean lines, vibrant colors; tech/business/lifestyle/news.
- **Palette:** dark slate + vibrant accent (electric blue/green), clean whites.
- **Typography:** geometric sans, tight tracking; fast mask-wipes; occasional clamped spring on stats.
- **Transitions:** `wipeleft`/`slideleft` 8–10f; `crossZoom`-feel on section changes.
- **B-roll:** city, technology, people working, product; moderate grade, crisp contrast.
- **VO:** energetic, confident, shorter sentences, punchier pacing (Vox-style reference per VidRush library).

### 3.4 Minimalist (`minimalist`)
- **VidRush:** clean, simple, subtle animations; corporate, product, clean educational.
- **Palette:** white/light-gray backgrounds or heavily darkened b-roll, single restrained accent.
- **Typography:** light-weight sans, generous whitespace; **subtle** 2–4f opacity cuts only.
- **Transitions:** `fade` 8–12f or hard cut; nothing directional.
- **B-roll:** minimal, product, office, abstract; low grain, gentle grade.
- **VO:** calm, formal, measured; short declarative lines.

### 3.5 Standard (`standard`)
- **VidRush:** versatile, well-balanced, neutral; "if unsure, start here"; satellite imagery, clean graphics. Default for listicles/top-10 too.
- **Palette:** neutral dark + standard accent (#ff6b35 default in current schema).
- **Typography:** balanced sans; mask-wipe titles, plate lower-thirds.
- **Transitions:** `fade`/`dissolve` 10f; hard cut acceptable.
- **B-roll:** broad keywords; documentary-neutral grade.
- **VO:** adaptable; listicle format = countdown energy within neutral visuals.

---

## 4. Script-generation rules per style (synergy layer)

What skills must respect (from VidRush prompt guide + reference-video docs):

| Rule | Source | Implementation |
|------|--------|----------------|
| ~0.5 talking points per minute | VidRush prompt guide | `01_script_writer.md` computes point count from target duration |
| Style/Tone declared at end of brief | VidRush prompt guide | Orchestrator brief template ends with `Style:`/`Tone:` lines mapped from global_style |
| Prompt = WHAT, theme = HOW | VidRush prompt guide | Skills never emit editing instructions; style JSON owns motion |
| Reference-video rhythm informs writing only | VidRush reference docs | `03_voiceover.md` gets per-style rhythm descriptor (sentence length, pause markers) |
| Footage availability check | VidRush prompt guide | `02_director.md` prefers concrete nouns (locations, people, events, objects) per style b-roll mood |
| Hooks: exact lines preserved | VidRush prompt guide | `hook_text` passes through verbatim |
| Abstract → concrete framing | VidRush prompt guide | Director rewrites abstract points into visualizable b-roll keywords |

---

## 5. Open design values (our decisions, not platform-documented)

These are **not** published by any platform — we set them from `PRO_EDIT_STYLE.md` and broadcast convention. Flagged here so nobody cites them as "VidRush values":

- Exact frame counts: wipeFrames 8–12, plateFrames 8–12, transition 8–15f.
- Darken 0.48–0.60, Ken Burns zoom 1.05–1.08.
- Loudness: YouTube -14 LUFS / -1 dBTP.
- NVENC p6/hq ~12 Mbps final encode.

---

## 6. Citations

1. VidRush — Themes & Visual Style: https://docs.vidrush.ai/docs/themes
2. VidRush — Prompting Guide: https://docs.vidrush.ai/docs/prompt
3. VidRush — Reference Video: https://docs.vidrush.ai/docs/reference-video
4. Remotion — Transitions overview: https://www.remotion.dev/docs/transitions
5. Remotion — `<TransitionSeries>`: https://www.remotion.dev/docs/transitions/transitionseries
6. Remotion — `spring()`: https://www.remotion.dev/docs/spring
7. Pictory — Styles Library: https://pictory.ai/academy/how-to-use-styles-library-pictory-ai
8. InVideo — motion graphics guidance: https://invideo.io/blog/best-motion-graphics-templates
9. OpusClip — brand templates: https://help.opus.pro/api-reference/brand-template
10. Lumen5 — better videos guide: https://lumen5.com/learn/how-to-create-better-lumen5-videos
