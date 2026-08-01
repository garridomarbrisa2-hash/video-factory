<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# You are a video editor and content strategist tasked with building a

"trigger logic" reference for an MCP (Model Context Protocol) motion
graphics library. For each motion graphic type in the catalog (comparison
overlays, circle/highlight annotations, arrow pointers, kinetic typography,
data counters, transitions, lower-thirds, intros/outros, etc.), research
and document the SPECIFIC contexts, moments, and content patterns where it
is actually used in real videos — so an LLM can later decide automatically
when to trigger each one from a script.

TASK 1 — Contextual Trigger Mapping
For EACH motion graphic type, answer:

- What SPOKEN/WRITTEN language pattern in a script typically precedes or
accompanies this motion graphic? (e.g., comparison words like "versus,"
"compared to," "on one hand... on the other hand" trigger split-screen
    + arrow graphics)
- What TIMING within a video does it typically appear (intro, mid-content
topic shift, climax/reveal, outro, CTA moment)?
- What VIDEO GENRE or FORMAT commonly uses it (documentary, explainer,
tutorial, listicle/Top 10, news recap, vlog, product review, corporate/
marketing, educational/edutainment like Kurzgesagt-style)?
- What NARRATIVE FUNCTION does it serve (clarify complex info, emphasize
a key point, create emotional impact, maintain pacing/attention, brand
reinforcement, guide viewer's eye, transition between subtopics)?

TASK 2 — Case-by-Case Real Examples
For each motion graphic type, find and describe REAL, documented examples
from actual YouTube channels, films, TV shows, or brand videos where it
was used — cite the channel/brand/show name, the specific scene or video,
and exactly why that motion graphic was chosen over a static visual or
plain B-roll. Include both large studio-quality use (film title sequences,
network news graphics) and creator-level use (YouTube explainer channels,
faceless documentary channels).

TASK 3 — Decision Rules for Automatic Triggering
Based on Tasks 1-2, write explicit IF-THEN decision rules an LLM could
follow when reading a script line-by-line, such as:

- IF script contains comparative language between two items/concepts
THEN trigger [Split-Screen Comparison + Arrow]
- IF script states a statistic or number THEN trigger [Animated Counter/
Chart Overlay]
- IF script says "look at this" / "notice this" / "pay attention to"
THEN trigger [Circle Highlight / Spotlight Zoom]
- IF script transitions to a new subtopic/chapter THEN trigger [Dynamic
Wipe Transition + Chapter Title Card]
- IF script reaches sign-off/closing statement THEN trigger [Subscribe
CTA Overlay / Outro Animation]
Cover ALL motion graphic types from the library, not just the common ones.

TASK 4 — Anti-Pattern Research (When NOT to Use Motion Graphics)
Research and document cases where motion graphics are OVERUSED or
misapplied, based on creator/community feedback, editing critiques, or
industry best-practice guides. Identify signals that indicate a motion
graphic would hurt pacing or clarity rather than help (e.g., too frequent
use causing visual fatigue, using flashy effects on serious/somber content,
overlapping multiple motion graphics at once).

TASK 5 — Genre-Specific Frequency \& Density Guidelines
For each major video genre (documentary, listicle, tutorial, news-style,
vlog, corporate explainer), estimate typical FREQUENCY of motion graphic
usage per minute of content, based on industry examples and creator
commentary. This will help calibrate how "trigger-happy" the automatic
system should be per genre.

Final output: a structured reference document mapping every motion
graphic type to its trigger conditions, real-world examples, decision
rules, and genre-specific usage density — ready to be converted into
LLM prompt logic or a rules engine for the MCP server.

Below is a structured “trigger logic” reference you can drop straight into MCP prompt logic or a rules engine. It maps each motion‑graphic type to (1) script patterns, (2) timing in the video, (3) genres, (4) narrative function, (5) real examples, and (6) explicit IF–THEN rules, plus anti‑patterns and genre‑specific density guidelines.[^1][^2]

***

## Comparison overlays / split‑screen

### Trigger mapping

- **Language patterns**
    - Comparative wording: “versus”, “vs”, “compared to”, “on one hand… on the other hand”, “before vs after”, “pros and cons”, “in contrast”, “the big difference is…”.[^2]
    - Often accompanied by explicit mention of two items, e.g., “the iPhone 15 vs the Galaxy S24” or “traditional marketing versus performance marketing”.[^2]
- **Typical timing**
    - Mid‑content when introducing a comparison segment, usually after both items have been introduced verbally.[^2]
    - In listicles when comparing two entries directly (e.g., \#3 vs \#4) or in review chapters labeled “Comparison” or “Specs showdown”.[^2]
- **Genres**
    - Product reviews, tech/comparison videos, explainers, corporate demos, news analysis (“Candidate A vs Candidate B”), sports analysis.[^2][^3]
- **Narrative function**
    - Clarify differences by showing items side‑by‑side.
    - Reduce cognitive load in complex comparisons (spec sheets, feature lists).
    - Maintain attention by framing the moment as a “head‑to‑head showdown”.[^1][^2]


### Real examples

- **Studio‑level**
    - Broadcast news routinely uses double‑box layouts (two live feeds or anchor + guest) with branded lower‑thirds and transitions to visually frame comparisons or debates.[^4][^5]
- **Creator‑level**
    - Explainer studios like YumYumVideos and What a Story show side‑by‑side comparisons in their explainer style breakdowns (e.g., motion‑graphics vs 2D character animation) to illustrate pros and cons visually.[^6][^7]


### IF–THEN rules

- IF line contains explicit comparative language (“vs”, “compared to”, “on the other hand”) AND mentions two entities
THEN trigger **[Split‑Screen Comparison Overlay]** for the next 1–2 sentences.
- IF the script heading/section label includes “Comparison”, “Pros and cons”, or “Before / After”
THEN wrap that section with **[Split‑Screen]** plus optional **[Highlight arrows]** indicating key differences.

***

## Circle / box highlights \& spotlight zooms

### Trigger mapping

- **Language patterns**
    - Attention cues: “look at this”, “notice here”, “pay attention to”, “as you can see right here”, “this part is important”.[^8]
    - Error/bug focus: “this is where the bug happens”, “see this small detail”, “this tiny icon is easy to miss”.[^8]
- **Timing**
    - During UI walkthroughs, diagrams, or B‑roll with multiple visual elements.
    - Mid‑explanation, not at intro/outro; often at the moment the narrator calls out one region of the frame.[^8]
- **Genres**
    - Tutorials, screencasts, educational explainers, design/UX breakdowns, product demos.[^8][^2]
- **Narrative function**
    - Guide the viewer’s eye to the subject region.
    - Clarify procedural steps (“click here”) and small details that might be missed in complex interfaces.[^1][^8]


### Real examples

- YouTube tutorials and motion‑graphics packs advertise circles/boxes as tools to “highlight important UI elements or key objects in your footage” for tutorials and explainer content.[^8][^9]
- Template sites offer “callout” and “highlight” animations marketed for screen recordings and product demos, used to mark buttons, metrics, or regions.[^9][^10]


### IF–THEN rules

- IF line includes attention phrases (“look at this”, “notice here”, “pay attention”) AND underlying shot has a clear target region
THEN trigger **[Circle/Box Highlight]** around that region.
- IF narrator references “this small detail”, “this specific button”, or “this region in the chart”
THEN trigger **[Spotlight Zoom]** centered on that element.

***

## Arrow pointers \& callout labels

### Trigger mapping

- **Language patterns**
    - Directive CTAs: “click this button”, “tap here”, “go to this menu”, “hit subscribe”, “check this link”.[^8][^2]
    - Spatial references: “over here in the top‑right”, “this slider on the left”, “look at this panel”.[^8]
- **Timing**
    - Exactly when the narrator gives an action instruction or points out a UI element.
    - During CTAs on YouTube (subscribe button, notification bell, link in description).[^8]
- **Genres**
    - Software tutorials, design tools demos, website walkthroughs, social media edits, YouTube education channels.[^8][^2]
- **Narrative function**
    - Guide viewer’s eye and reduce search time for UI elements.
    - Reinforce CTAs (subscribe, buy, sign up) by visually pointing to interactive elements.[^1][^8]


### Real examples

- Arrow/callout packs from marketplaces are described as “perfect for tutorials, educational videos, motion‑graphics projects, and social media videos” to highlight important elements and improve visual storytelling.[^9][^11]


### IF–THEN rules

- IF line contains an action verb + UI element (“click the save icon”, “tap the profile picture”, “hit subscribe”)
THEN trigger **[Arrow Pointer]** pointing at the referenced UI element or button.
- IF line contains a CTA referencing on‑screen elements (“click the button below”, “tap here on screen”)
THEN trigger **[Arrow Pointer + subtle label]** near the element.

***

## Kinetic typography (animated text)

### Trigger mapping

- **Language patterns**
    - Short, punchy statements: “the key takeaway is…”, “the bottom line”, “the problem is…”, “here’s the solution”, “Step 1 / Step 2 / Step 3”.[^6][^12]
    - Emotional emphasis: “huge mistake”, “massive opportunity”, “critical”, “secret”.[^1]
- **Timing**
    - During key summary lines or section headers.
    - In intros for episode titles; mid‑content to emphasise key phrases; occasionally in outros for taglines.[^6][^2]
- **Genres**
    - Explainer videos, SaaS/product promos, Kurzgesagt‑style edutainment, social ads.[^6][^12][^2]
- **Narrative function**
    - Emphasise crucial wording, improve retention of key phrases.
    - Maintain engagement in voiceover‑heavy or talking‑head segments.
    - Reinforce brand voice via typography and color.[^1][^2]


### Real examples

- Explainer style breakdowns explicitly list “kinetic typography” as a distinct style where moving text is the main carrier of meaning.[^6]
- Designer Daily analyses explainer videos where animated text and icons are timed to script beats to “use motion as storytelling device” and emphasize key points.[^1]


### IF–THEN rules

- IF a line matches a pattern like “the key takeaway is…”, “the bottom line…”, or a clearly labeled step (“Step 1: …”)
THEN trigger **[Kinetic Typography]** rendering that phrase with emphasis.
- IF line is short (≤10 words), highly emotive or summarising, and sits at start/end of a section
THEN use **[Kinetic Typography]** synced precisely to voiceover.

***

## Data counters, statistic overlays, charts

### Trigger mapping

- **Language patterns**
    - Explicit numbers: percentages, counts, monetary values (“25% growth”, “2 million users”, “\$10 billion market”).[^2][^12]
    - Statistical phrases: “data shows”, “on average”, “3 out of 5”, “1 in 10”.[^2]
- **Timing**
    - Whenever the narrator introduces a key metric that supports the argument (product stats, social proof, scientific numbers).
    - Often early in corporate explainers and mid‑segment in educational content.[^2][^12]
- **Genres**
    - Corporate explainers, tech/business channels, educational/science videos, news/business segments.[^2][^4]
- **Narrative function**
    - Clarify numbers visually; make them memorable through counters or simple graph shapes.
    - Signal “this is a crucial figure” and support persuasion or explanation.[^1][^2]


### Real examples

- Explainer guides highlight animated charts and infographics as standard tools for simplifying complex data; examples from Amazon and other brands use animated numbers and bars to convey metrics.[^13][^2]


### IF–THEN rules

- IF a sentence includes a numeric expression (percentage, count, money, ratio) and that value is central (not a throwaway detail)
THEN trigger **[Numeric Counter or Bar/Chart Overlay]** next to the speaker or in a dedicated data zone.
- IF multiple statistics are introduced in a short cluster (e.g., “we serve 2M users across 40 countries with 99.9% uptime”)
THEN trigger **[Mini Infographic]** summarising them in a clustered layout.

***

## Transitions (wipes, slides, glitches) \& chapter title cards

### Trigger mapping

- **Language patterns**
    - Topic shifts: “now let’s move on to…”, “next we’ll look at…”, “on to the next step”, “in chapter two…”, “now for the pros… now for the cons…”.[^12]
    - Listicle structure: “Number three on our list is…”, “coming in at number one…”.[^2][^12]
- **Timing**
    - Between clear sections, chapters, or list items; when moving between different visual contexts (talking head → screen recording → B‑roll).[^2]
    - At montage sequences or recaps.[^14]
- **Genres**
    - Listicles/Top‑X, structured tutorials, news packages, documentaries with chapter titles, corporate explainers.[^2][^14]
- **Narrative function**
    - Mark structural boundaries and maintain pacing.
    - Provide visual reset between topics and help viewers mentally segment content.[^1][^14]


### Real examples

- ABC’s 3D graphics package uses short animated sequences as transitional wipes between segments and into/out of commercials, designed to feel purposeful rather than decorative.[^14]
- Explainer templates on stock sites bundle animated chapter cards and transitions to visually separate steps or list items.[^10][^2]


### IF–THEN rules

- IF line begins with “Next…”, “Now let’s talk about…”, “Number X”, “Chapter X” OR editor marks a section boundary
THEN trigger **[Transition + Chapter Title Card]** between segments.
- IF script indicates a stylistic change (e.g., “Let’s jump into the demo”)
THEN trigger a **[Transition]** coinciding with the cut to a new visual context.

***

## Lower‑thirds (IDs, roles, topics)

### Trigger mapping

- **Language patterns**
    - Introductions: “I’m [Name]”, “Joining us is [Name]”, “Today I’m talking with [Name], [Title].”[^15][^16][^4]
    - Implicit intros (no spoken intro): new person starts talking without verbal self‑introduction.[^17]
- **Timing**
    - First time a speaker appears.
    - At start of an interview segment or when role/location changes.[^15][^4][^17]
- **Genres**
    - Broadcast news, documentaries, interviews, webinars, podcasts, vlogs, corporate videos.[^15][^16][^17]
- **Narrative function**
    - Identify who is speaking and their role.
    - Provide contextual info (location, organisation, topic) without breaking flow.
    - Reinforce brand via consistent graphic style.[^15][^16][^4]


### Real examples

- Documentary guides note that lower thirds appear when a new subject is introduced, communicating identity and credentials without needing a voiceover; The Social Dilemma and Becoming use lower thirds strategically for clarity.[^15]
- Adobe and OpenClip explain that broadcast television fills lower thirds with names, titles, headlines, scores and logos, using them as a staple of news and documentary storytelling.[^16][^4][^5]
- Creator guides emphasise that animated lower thirds should be brief (≈3–6 seconds) and non‑distracting, especially for talking‑head content.[^17][^4]


### IF–THEN rules

- IF a new speaker appears AND their name/title is known (from script or metadata)
THEN trigger **[Lower‑Third ID]** for 3–6 seconds at first appearance.
- IF script labels a new segment (“Segment: Market Overview”)
THEN trigger **[Lower‑Third Topic Bar]** at the start of that segment.

***

## Intros \& outros (including Subscribe/CTA overlays)

### Trigger mapping

- **Language patterns (intro)**
    - Opening hook: question or problem statement (“What if there were 1 trillion more trees?”, “In this video you’ll learn…”).[^13][^18]
    - Title announcements: “Welcome to [Channel]”, “Today we’re talking about…”.[^2]
- **Language patterns (outro/CTA)**
    - CTAs: “subscribe for more”, “like this video”, “share with a friend”, “download the guide in the description”, “visit our website”.[^2][^19]
    - Closing phrases: “thanks for watching”, “see you next time”, “that’s all for today”.[^17]
- **Timing**
    - Intros: first 5–10 seconds.
    - Outros: final 10–20 seconds, often overlapping with end‑screen elements.[^2][^17]
- **Genres**
    - Nearly all YouTube formats: explainer, vlog, review, tutorial, corporate marketing, documentary with branded openers.[^2][^17]
- **Narrative function**
    - Intros: establish brand identity and set expectations.
    - Outros: drive concrete viewer actions and close the narrative arc.[^2][^17]


### Real examples

- Explainer video guides frame intros/outros as core components of professional motion‑graphics explainers, with branded titles and closing CTAs.[^2][^12][^13]
- Creator tutorials show adding animated logo intros and subscribe overlays to make channels feel more polished and to systematically prompt engagement.[^19][^17]


### IF–THEN rules

- IF script position < N seconds AND lines include channel name, video topic, or brand tagline
THEN trigger **[Intro Title/Logo Animation]**.
- IF lines include CTA phrases (“subscribe”, “like”, “visit”, “download”, “check the description”) AND appear in final section
THEN trigger **[Subscribe/CTA Overlay + Outro Animation]** aligned to those lines.

***

## Picture‑in‑picture (PiP) \& multi‑box layouts

### Trigger mapping

- **Language patterns**
    - Screen reference: “on my screen you’ll see…”, “take a look at this interface”, “here’s how it looks in the app”.[^8][^2]
    - Parallel action: “while this is happening here, over on the dashboard…”.[^2]
- **Timing**
    - During demonstrations where presenter commentary and screen content need to be visible together.
    - During interviews where multiple participants or feeds are active (news double‑box).[^4][^5]
- **Genres**
    - Tutorials, webinars, software demos, news panels, interviews.[^2][^4]
- **Narrative function**
    - Maintain human connection while showing detailed UI or visuals.
    - Provide multi‑view context (anchor + guest, before + after).[^4][^5]


### Real examples

- Broadcast graphics templates include double‑box and over‑shoulder layouts for news anchors and guests, used with consistent lower‑thirds and transitions.[^5][^4]
- Creator‑level screencast tutorials commonly use PiP of presenter + screen, recommended in editing guides as a way to keep viewers engaged.[^8][^2]


### IF–THEN rules

- IF script references “on screen”, “in the app”, or “as you can see here” AND underlying footage includes both presenter and screen or can be composed that way
THEN trigger **[PiP Layout]** for that segment.

***

## Gallery grids / multi‑snippet layouts

### Trigger mapping

- **Language patterns**
    - List structures: “Top 5 tools”, “here are three examples”, “these are our case studies”.[^2][^12]
    - Summary clusters: “we work with brands like X, Y, and Z”.[^2]
- **Timing**
    - During list segments; at recap moments showing many options or examples at once.
- **Genres**
    - Listicles/Top‑X videos, compilation reels, product highlight reels, portfolio showcases.[^2][^20]
- **Narrative function**
    - Convey breadth and variety quickly.
    - Efficiently show multiple items without long sequential cuts.[^1][^2]


### Real examples

- Stock providers offer explainer animation and gallery templates designed for “Top 10” or “explainer highlight” formats.[^20][^10][^2]


### IF–THEN rules

- IF script enumerates items (“Top 5”, “3 case studies”, “these 4 features”) AND assets exist for each
THEN trigger **[Gallery Grid Layout]** when listing them, with each panel mapped to an item.

***

## Generative / animated backgrounds

### Trigger mapping

- **Language patterns**
    - Abstract/conceptual explanations: definitions, frameworks, brand values, with no reference to specific live footage (“our platform simplifies complexity”, “here’s how the process works conceptually”).[^1][^2]
    - Voiceover scripts not tied to a particular location.[^2]
- **Timing**
    - Behind titles, bullet points, infographics.
    - During conceptual segments where B‑roll is generic or not available.[^2][^12]
- **Genres**
    - Motion‑graphics explainers, product promos, conceptual science/tech explainers.[^2][^12][^13]
- **Narrative function**
    - Provide visual texture while keeping focus on text/icons.
    - Maintain subtle motion to hold attention without distracting from information.[^1][^8]


### Real examples

- Explainer studios use abstract animated backgrounds (shapes, gradients) behind iconography and typography in videos like Accelerant, Samsung Biologics explainers, etc.[^13][^1][^2]


### IF–THEN rules

- IF script segment is pure voiceover about concepts with no strong visual reference AND genre is “motion‑graphics explainer” or “corporate promo”
THEN use **[Animated Background]** plus text/icons instead of raw talking‑head.

***

## Stylized effects (slow‑mo, trails, comic/edge look)

### Trigger mapping

- **Language patterns**
    - Emphasis on dramatic action: “watch this carefully”, “here’s the highlight”, “in slow motion you can see…”.[^2][^18]
    - “Instant replay”, “let’s rewind that moment”.
- **Timing**
    - At peak moments (climax, big reveal, physical action).
    - In recap sequences or highlight reels.[^1][^21]
- **Genres**
    - Sports, action vlogs, cinematic documentaries, fashion/brand spots.[^21][^2]
- **Narrative function**
    - Heighten emotional impact and aesthetic interest.
    - Reveal details not visible at normal speed (slow‑mo).


### Real examples

- Research on film scene dynamism shows high‑paced, high‑color scenes contribute directly to visual fatigue, highlighting that stylised effects should be used sparingly.[^21]
- Explainer and design guides stress using expressive animation only where the composition is simple enough and the moment meaningful.[^1][^8]


### IF–THEN rules

- IF line explicitly requests focus (“watch in slow motion”, “here’s the highlight”) AND the clip is visually rich (action, motion)
THEN apply **[Slow‑Motion or Stylized Effect]** to that specific clip.
- IF genre is “sports highlight” or “music/fashion promo” AND the script marks a “drop” or “moment”
THEN selectively allow stylised transitions or trails at those beats.

***

## Anti‑patterns: when NOT to use motion graphics

### Overuse \& visual fatigue

- UX and animation research emphasise that too much motion causes distraction, visual chaos, and fatigue; delight is not infinite.[^22][^1]
- Film studies find high‑paced, high‑colour scenes in films directly increase visual fatigue, implying that adding more motion graphics on top of already dynamic footage can worsen the experience.[^21]

**Signals to suppress triggers**

- Scene already has fast cuts or strong camera motion → avoid extra flashy graphics; prefer subtle lower‑thirds.[^21][^1]
- Serious/sombre content (tragedy, sensitive interviews, serious documentaries) → avoid glitches, playful kinetic type, hyper‑color backgrounds; use minimal graphics.[^15][^4]
- Multiple triggers in same sentence (comparison + stats + CTA) → choose one primary graphic (e.g., split‑screen OR chart), not all at once.[^1][^22]
- Dense compositions with many elements → IBM‑style guidance suggests simple motion or static graphics to avoid overload.[^1]


### Clutter and inconsistency

- Guides for motion‑graphics explainer videos stress visual consistency (colors, typography, transition types) and clear hierarchy; random styles per scene feel amateur and confusing.[^1][^12][^2]
- Lower‑third guides warn that overly animated or busy lower‑thirds distract from the story and advise simple, brief animations.[^17][^4]

**Anti‑rules**

- IF current frame already has a lower third + captions + animated background AND logic wants to add kinetic typography or arrows
THEN suppress the new motion graphic unless it has clear added value for clarity.
- IF animation would cover critical footage region (evidence shot, interview subject)
THEN either reposition or skip it.
- IF genre is documentary or corporate statement on sensitive topic AND effect is flashy (glitch, extreme zoom, heavy trails)
THEN downgrade to minimal or static treatment.

***

## Genre‑specific frequency \& density guidelines

Based on documentary lower‑third guidance, explainer/video production guides, UX animation research, and creator commentary:[^15][^16][^4][^1][^22][^2]


| Genre | Recommended Motion Graphics Density | Common Types | Usage Notes |
| :-- | :-- | :-- | :-- |
| Documentary (interview‑driven) | ~0.5–2 graphics/min | Lower‑third IDs, simple topic bars, occasional data overlays | Use lower thirds at first appearance of each speaker and sparingly for new topics; keep motion subtle and non‑flashy.[^15][^16][^4] |
| Documentary (stylized/essay) | ~1–3 graphics/min | Title cards, restrained kinetic type, infographics | Graphics support mood and explanation; avoid heavy effects in emotional scenes and follow clarity‑first principles.[^15][^1] |
| Explainer / educational (motion‑graphics) | ~3–6 graphics/min | Kinetic typography, icons, animated backgrounds, transitions, data visuals | Motion is core to the format; every animated element should “serve the message, not decoration”, with consistent style.[^1][^2][^12] |
| Tutorial / screencast | ~2–5 graphics/min | Highlights, arrows, PiP, step labels | Use highlights/arrows frequently for UI guidance; keep designs simple to avoid clutter on dense interfaces.[^8][^9][^2] |
| Listicle / Top‑X | ~3–7 graphics/min | Item title cards, numeric counters, transitions, occasional comparisons | Each item usually gets a title/lower third and transition; avoid stacking multiple effects inside a single short beat.[^2][^12] |
| News / broadcast | Continuous banners + 3–8 animated events/min | Lower thirds, tickers, scorebars, transitions, split‑screens | Graphics are dense but highly structured; follow network‑style consistency and keep motion purposeful, not flashy.[^4][^5][^23] |
| Corporate explainer / brand promo | ~2–4 graphics/min | Branded intros/outros, data overlays, lower thirds, kinetic type | Motion reinforces brand identity and clarifies benefits; article and guides emphasise avoiding “decorative noise”.[^24][^1][^2] |
| Vlog / lifestyle | ~0–3 graphics/min | Minimal lower thirds, simple pop‑up text, intro/outro | Audience expects authenticity; heavy motion graphics can feel overproduced unless intentionally stylised.[^17][^2] |
| Short‑form social ads (Reels/Shorts) | ~4–8 graphics/min (short runtime) | Fast kinetic type, CTAs, animated backgrounds, arrows | Short videos tolerate higher motion density, but UX guidance warns against overuse that overwhelms viewers.[^25][^22][^2] |

**How to use these thresholds in MCP**

- Infer or read **genre** from metadata/script.
- Apply genre‑specific caps (e.g., max 2 graphics/min for documentaries, higher for explainers).
- When multiple triggers fire, choose the most informative type under the cap, and apply anti‑pattern rules to avoid clutter.

***

This reference gives you:

- Trigger cues (script patterns, timing, genre, narrative function) for each motion graphic type.
- Real usage patterns from broadcast, documentary, explainer studios, and creator‑level content.
- IF–THEN logic you can implement for automatic, script‑driven motion‑graphics decisions.
- Anti‑pattern guardrails and genre‑specific density settings so the system is smart, not “trigger‑happy”.[^1][^22][^15][^4][^2]
<span style="display:none">[^26][^27][^28][^29][^30][^31][^32][^33][^34][^35]</span>

<div align="center">⁂</div>

[^1]: https://www.designer-daily.com/motion-graphics-that-actually-communicate-lessons-from-explainer-videos-213110

[^2]: https://www.moonb.io/blog/motion-graphics-explainer-videos

[^3]: https://www.storyblocks.com/resources/blog/lower-thirds-for-video

[^4]: https://www.adobe.com/creativecloud/video/discover/lower-third-graphics.html

[^5]: https://videocue.io/looks/lower-third-broadcast-graphics-classic

[^6]: https://www.youtube.com/watch?v=F96q9CiOtq8

[^7]: https://www.youtube.com/watch?v=pdfArI9H16E

[^8]: https://www.aicoursify.com/blog/using-motion-graphics-to-enhance-videos

[^9]: https://elements.envato.com/arrow-highlight-elements-motion-graphics-7QZHZW8

[^10]: https://uppbeat.io/motion-graphics/category/explainer

[^11]: https://www.youtube.com/watch?v=Uql_wqM9g5s

[^12]: https://www.eggplain.com/how-to-make-a-motion-graphics-explainer-video/

[^13]: https://www.youtube.com/watch?v=8eKZnmOy5Tw

[^14]: https://www.newscaststudio.com/2023/10/02/abc-owned-graphics-package-2023/2/

[^15]: https://www.soundstripe.com/blogs/a-documentarians-guide-to-lower-thirds

[^16]: https://openclip.app/learn/lower-third

[^17]: https://www.epidemicsound.com/blog/lower-thirds/

[^18]: https://www.youtube.com/watch?v=DmI7_SNJCBs

[^19]: https://www.miracamp.com/learn/youtube/creating-animated-graphics-your-content

[^20]: https://www.storyblocks.com/all-video/search/explainer-animation

[^21]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11535479/

[^22]: https://lordicon.com/blog/from-delight-to-annoyance-when-too-much-animation-hurts-ux

[^23]: https://hstalks.com/doi/10.69554/YZOX6190/

[^24]: https://www.jisem-journal.com/article/a-research-on-the-dynamization-effect-of-brand-visual-identity-design-mediated-by-digital-14078

[^25]: https://dl.acm.org/doi/pdf/10.1145/3613904.3642839

[^26]: https://link.springer.com/10.1007/978-1-4302-6698-3_9

[^27]: https://www.semanticscholar.org/paper/7d13cac88b693407467bd4b89d2904eeeedb69c2

[^28]: http://link.springer.com/10.1007/3-540-36108-1_2

[^29]: https://www.semanticscholar.org/paper/9b7d833e6d7d0b9e91abc9057c257715717b03c5

[^30]: https://www.semanticscholar.org/paper/782c20b016fe02a2e5ca3345dbe9523ef4671845

[^31]: https://digitalcommons.unomaha.edu/jrf/vol20/iss2/26/

[^32]: https://www.semanticscholar.org/paper/dd46c31131b85e1b1c71d816859734b76fd590bf

[^33]: https://modeldiplomat.com/learn/glossary/lower-third

[^34]: https://www.theauxiliaryco.com/articles/using-motion-graphics-in-explainer-videos-the-complete-guide-for-2025

[^35]: https://riverside.com/blog/lower-thirds

