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

Below is a compact but detailed reference you can wire directly into MCP logic: each motion graphic type is mapped to script patterns, timing, genres, narrative function, real‑world examples, and explicit IF–THEN rules, plus anti‑patterns and genre density guidelines. Motion‑graphics usage patterns are drawn from motion‑graphics guides, lower‑third usage articles, and creator best‑practice tutorials.[^1][^2][^3][^4][^5][^6]

***

## Motion graphic types \& contextual triggers (Tasks 1–2)

### Split‑screen comparisons / comparison overlays

**Language patterns (script cues)**

- Comparative terms: “versus”, “vs”, “compared to”, “on one hand… on the other hand”, “pros and cons”, “before vs after”, “Option A vs Option B”.
- Contrastive structures: “while X does…, Y instead…”, “the big difference is…”, “in contrast”.[^1][^7]

**Typical timing**

- Mid‑content when introducing *two* competing products/ideas.
- In listicles when showing two items side‑by‑side.
- In reviews during feature comparison segments.[^2]

**Genres using it**

- Product reviews, tech/comparison videos, explainers, corporate demos, news analysis (two sources/regions), sports comparison, educational side‑by‑side experiments.[^1][^7]

**Narrative function**

- Clarify complex differences visually.
- Maintain attention by showing two options simultaneously.
- Guide the viewer’s eye to “A vs B” framing instead of linear exposition.[^1]

**Real examples**

- YouTube explainer channels and agencies (YumYumVideos, What a Story) show multiple options in motion‑graphics explainers with side‑by‑side layouts to compare features or flows.[^7][^8]
- Broadcast news double box layouts (ABC owned‑station graphics package) use split‑screen with lower‑third banners to compare live feeds or show anchor + remote guest simultaneously.[^5]

***

### Circle / box highlights \& spotlight zoom

**Language patterns**

- Attention cues: “look at this”, “notice here”, “pay attention to”, “focus on this part”, “as you can see right here…”.
- Error/issue pointing: “this is where it breaks”, “here’s the problem”, “see this small detail”.[^1][^9]

**Timing**

- During screen‑recordings or UI walkthroughs when highlighting a button/region.
- During B‑roll or diagrams when drawing attention to one area.
- Often mid‑explanation, not at intro/outro.[^2]

**Genres**

- Tutorials and software demos, educational explainer videos, UI/UX breakdowns, business presentations, social‑media how‑to content.[^1][^2][^9]

**Narrative function**

- Guide the viewer’s eye to the relevant part of a busy frame.
- Reduce cognitive load by visually marking the “subject”.
- Clarify steps in procedural content (where to click, what to inspect).[^1][^2]

**Real examples**

- Motion‑graphics arrow and highlight packs are marketed specifically for tutorials, explainer videos, and social‑media content to “point things out and keep your audience focused where it matters most”.[^1][^10][^9]
- YouTube tutorials on “Animated Motion Graphics for YouTube” recommend arrows, rectangles, and simple highlight shapes on top of screen recordings to emphasize UI elements.[^2]

***

### Arrow pointers \& callout labels

**Language patterns**

- Directives: “go here”, “click this button”, “this part is important”, “this is where the magic happens”.
- Call‑to‑action references: “hit the subscribe button”, “check the link below”, “tap here to learn more”.[^2][^9]

**Timing**

- When showing UI or visual layouts with multiple elements.
- During CTAs (subscribe, like, buy, sign up).
- During product shots to point at features or specifications.[^2][^9]

**Genres**

- Tutorials (software, design, coding), YouTube educational channels, product explainers, marketing/promotional videos, social ads.[^1][^2][^9]

**Narrative function**

- Guide the viewer’s eye precisely.
- Reinforce CTAs by literally pointing at interactive elements.
- Make static images feel more dynamic without full animation sequences.[^1][^9]

**Real examples**

- Envato and similar marketplaces sell arrow/callout packs specifically described as “perfect for social media content, YouTube tutorials, explainer videos, or business presentations” to highlight key messages or CTAs.[^9]
- Dedicated arrow‑icon motion‑graphics collections on YouTube promote use for “highlighting important elements, guiding viewers’ attention, and improving visual storytelling” in tutorials and motion‑graphics projects.[^10]

***

### Kinetic typography (animated emphasis text)

**Language patterns**

- Key phrases or slogans: “the key takeaway is…”, “the bottom line”, “in summary”, “the problem is…”, “solution”, “step one / step two”.
- Emotional emphasis: “critical”, “huge mistake”, “massive opportunity”, “the secret is…”.[^7]

**Timing**

- During important summary lines or punchy statements.
- In intros to present title/episode theme.
- In mid‑section emphasis moments (e.g., listing steps or key facts).[^7][^2]

**Genres**

- Explainer videos, SaaS/product marketing, social clips, educational videos, inspirational talks, Kurzgesagt‑style infographic content.[^7][^11]

**Narrative function**

- Emphasize spoken words by synchronised text on screen.
- Maintain pacing and visual interest in talking‑head or voiceover‑driven content.
- Reinforce brand tone via typography and color.[^1][^7]

**Real examples**

- Explainer studios highlight kinetic typography as a distinct style for explainer videos where “moving text” is central to conveying ideas and producing visual impact.[^7]
- Compilation videos of explainer styles show multiple examples where key phrases, numbers, and titles pop in kinetic type to keep complex explanations engaging.[^11]

***

### Data counters, stats overlays, charts

**Language patterns**

- Numeric statements: “we grew by 25%”, “over 2 million users”, “3 out of 5 people”, “the market is worth \$10 billion”.
- Comparisons with numbers: “twice as fast”, “half the cost”, “1 in 10”.
- Step/time references: “after 30 days”, “in 3 simple steps”.[^1][^2]

**Timing**

- When introducing key metrics in product/corporate explainers.
- In educational content explaining datasets or trends.
- In documentary segments that shift into statistical narration.[^1][^4]

**Genres**

- Corporate explainers and brand videos, business/finance channels, educational content (science/data), news graphics (economic indicators), infographics/edutainment.[^1][^3][^4]

**Narrative function**

- Clarify and quantify abstract claims.
- Improve retention of numbers via visual representation.
- Signal “this is an important figure” that supports the argument.[^1][^2]

**Real examples**

- Motion‑graphics guides recommend using charts, graphs, and infographics to “simplify complex data in educational or tutorial videos.”[^2]
- Broadcast lower thirds frequently include stocks, scores, dates, weather and other numeric data in banners or tickers for clarity and context.[^3]

***

### Transitions (wipes, slides, glitches, chapter cards)

**Language patterns**

- Topic changes: “now let’s move on to…”, “next we’ll look at…”, “on to the next step”, “in chapter two…”.
- Structural markers: “first… second… third…”, “now for the pros”, “now for the cons”.[^2][^7]

**Timing**

- Between distinct sections, chapters, or list items.
- Between locations/time jumps in documentaries or vlogs.
- At “style shifts” (e.g., from talking head to screen recording).[^5][^2]

**Genres**

- Listicles/Top 10, tutorials with multiple steps, news packages, documentaries with chapter structure, corporate explainers.[^7][^5]

**Narrative function**

- Signal clear structural boundaries.
- Maintain pacing by smoothing visual jumps.
- Support brand style via consistent transition look.[^1][^5]

**Real examples**

- ABC owned‑station graphics package uses short 3D sequences as “transitional wipe elements” between segments and for bumpers into breaks.[^5]
- Explainer templates at motion‑graphics marketplaces and tutorial guides consistently bundle customizable transitions for chapter changes and segment shifts.[^2][^12]

***

### Lower‑thirds (IDs, topics, branded info bars)

**Language patterns**

- Introductions: “I’m [Name] and today…”, “Joining us is [Guest Name]”.
- Topic announcements: “Today we’ll talk about…”, “This segment is about…”.
- Location/time descriptors: “Meanwhile in New York…”.[^3][^4][^13]

**Timing**

- When a new speaker appears.
- When changing topic within a continuous shot.
- At start of interview, panel segment, or important B‑roll.[^3][^4]

**Genres**

- Broadcast news, documentaries, interviews, corporate videos, webinars and livestreams, explainer channels that identify speakers/roles.[^3][^4][^13]

**Narrative function**

- Clarify who is speaking and their role.
- Label topic/context without interrupting footage.
- Reinforce branding via consistent bar style.[^3][^4][^13]

**Real examples**

- Adobe’s guide notes lower thirds in broadcast TV that display network logos, scores, breaking news, date/time, and weather in the lower region to communicate context without pulling focus from the frame.[^3]
- Documentary guide shows The Social Dilemma using stylized lower thirds to introduce interviewees and highlight affiliations; Becoming uses minimal white lower thirds to label a speaker once.[^4]
- News graphics breakdowns (ABC) describe multiple lower‑third layouts for headlines, teases, talent IDs, and double‑anchor identifiers, all with purposeful entrance animations.[^5]

***

### Intros (logo/title, openers) \& Outros/CTAs

**Language patterns (intros)**

- Opening hook: questions, bold statements (“What if there were…”, “In this video we’ll…”).
- Title statements: “[Brand] presents”, “Welcome to [Channel]”.[^7][^11][^2]

**Language patterns (outros/CTAs)**

- CTAs: “subscribe for more”, “like and share”, “download the guide”, “visit our website”, “check the link below”.
- Closing phrases: “thanks for watching”, “see you in the next video”, “that’s it for today”.[^2][^7]

**Timing**

- Intros at 0–10 seconds, often with logo/title motion graphics.
- Outros at last 10–20 seconds, often with subscribe buttons and end‑screen prompts.[^2][^7]

**Genres**

- Almost all YouTube formats: explainers, vlogs, reviews, tutorials, corporate videos, documentaries with branded openers.[^1][^2][^7]

**Narrative function**

- Establish brand identity and tone at the start.
- Create emotional closure and drive specific viewer actions at the end.
- Provide structural “wrapper” around core content.[^1][^2]

**Real examples**

- Motion‑graphics tutorials recommend intro/outro templates containing channel name, logo, and social handles to “create a strong first impression” and “encourage viewers to like, subscribe, or leave a comment.”[^2]
- Explainer compilations highlight studio‑quality title sequences and branded intros/outros as core elements of professional explainer style.[^7][^11]

***

### Picture‑in‑picture (PiP), over‑shoulder frames

**Language patterns**

- Demonstrations: “let me show you”, “on my screen you’ll see”, “here’s how the interface looks”.
- Multi‑view references: “while this is happening, over here…”.[^1][^2]

**Timing**

- During walkthrough portions where you need both presenter and screen.
- When showing comparison between live camera and B‑roll or slides.[^2]

**Genres**

- Tutorials (presenter + screen), webinars, live training, news double‑box layouts.[^2][^5]

**Narrative function**

- Allow simultaneous focus on person and demonstration.
- Maintain human connection while teaching technical content.[^1][^4]

**Real examples**

- Broadcast multi‑box layouts described in ABC’s graphics package (double‑box, banner + talent inserts) serve as PiP‑style multi‑view for anchors and visuals.[^5]
- Tutorial guides for YouTube editing recommend PiP for screencasts combined with talking‑head footage to keep content engaging.[^2]

***

### Gallery grids / multi‑snippet layouts

**Language patterns**

- List structures: “Top 10…”, “here are 5 examples…”, “three case studies”.
- Mentions of “multiple options” or “several examples at once”.[^7][^11]

**Timing**

- During “roundup” segments.
- When summarizing multiple items side‑by‑side (e.g., logos, thumbnails, product variants).

**Genres**

- Listicle videos, compilation reels, product showcase, news recap highlight reels.[^7][^14]

**Narrative function**

- Efficiently show many items at once.
- Convey “breadth” and variety visually.

**Real examples**

- Stock and template libraries specifically label “explainer animation” packs and gallery layouts for top‑10 or multi‑item presentations.[^14]
- Explainer compilations show multi‑tile sequences for “best examples” or “feature overview.”[^11]

***

### Generative / animated backgrounds

**Language patterns**

- Abstract segments: definitions, conceptual explanations, brand messages not tied to specific footage.
- “Floating” narration: voiceover without reference to specific live shots.[^1][^7]

**Timing**

- Behind titles, bullet points, and infographics.
- During abstract explanations where B‑roll is generic or unavailable.[^1][^2]

**Genres**

- Motion‑graphics explainer videos, brand promos, conceptual science explainers, corporate decks translated into video.[^7][^11][^1]

**Narrative function**

- Provide visual texture and brand style without distracting from overlay text and icons.
- Avoid static black screens; maintain subtle movement to hold attention.[^1][^2]

**Real examples**

- Explainer studios frequently use abstract, animated backgrounds behind iconography and typography to make complex conceptual explanations more engaging.[^7][^11]
- Motion‑graphics tutorials recommend animated backgrounds as “background enhancements” for depth and texture.[^2]

***

### Stylized effects (edge/comic look, slow‑motion, motion trails)

**Language patterns**

- Emphasis on emotional or dramatic moments: “this is crazy”, “watch what happens”, “in slow motion…”.
- “Highlight reels”: “here’s the best part”, “instant replay”.

**Timing**

- At climactic or “wow” moments.
- During recaps or highlight reels.

**Genres**

- Sports, action highlights, vlogs, documentary sequences with stylistic flair, fashion/brand promos.[^1][^15]

**Narrative function**

- Create emotional impact and aesthetic differentiation.
- Signal that a moment is special or worth replaying.

**Real examples**

- Sports and high‑paced films use slow motion and high‑dynamism scenes sparingly; research finds that high‑paced, high‑color aspects directly contribute to visual fatigue, underscoring the need for controlled usage.[^15]
- Brand visual identity research notes using motion graphics design to dynamically reinforce brand meaning, but stresses balance and intentionality.[^16]

***

## IF–THEN decision rules for automatic triggering (Task 3)

You can encode the following rules into MCP logic. Each motion graphic type may have additional parameters derived from context (e.g., nouns, numbers, names).

### Comparison overlays / split‑screen

- IF a script sentence contains comparative language (“versus”, “vs”, “compared to”, “on one hand… on the other hand”, “before vs after”, “pros and cons”) AND mentions two distinct entities (products, concepts, options)
THEN trigger [Split‑Screen Comparison Overlay] during that line or the next 1–2 sentences.[^1][^7]


### Circle/box highlight / spotlight zoom

- IF a sentence includes attention cues (“look at this”, “notice here”, “pay attention to”, “as you can see”, “this part right here”) AND the underlying video frame has a discernible UI element or region
THEN trigger [Circle/Box Highlight or Spotlight Zoom] centered on the relevant region.[^1][^9]


### Arrow pointer / callout

- IF a sentence contains directional or CTA language (“click this”, “tap here”, “go to this button”, “hit subscribe”, “check the link below”)
THEN trigger [Arrow Pointer] pointing at the UI element, subscribe button, or onscreen CTA graphic.[^2][^9]


### Kinetic typography

- IF a sentence contains a short, punchy phrase that summarizes a key idea (“the key takeaway is…”, “the secret is…”, “the bottom line…”, numbered steps “Step 1… Step 2…”)
THEN trigger [Kinetic Typography Overlay] for that phrase, synchronised with speech.[^7][^11]


### Data counters / charts

- IF a sentence states specific numeric values (percentages, counts, monetary amounts, ratios) OR references metrics (“growth”, “conversion rate”, “market size”, “statistics show”)
THEN trigger [Data Counter or Chart Overlay] visualising the key number(s) near the speaker or in a dedicated data zone.[^1][^2][^3]


### Transitions \& chapter title cards

- IF the script indicates a topic shift (“now let’s move on to…”, “next up”, “in chapter two”, new numbered list item) OR the editor marks a chapter boundary
THEN trigger [Transition + Chapter Title Card] between the segments.[^7][^5]


### Lower‑thirds (speaker/topic IDs)

- IF a new speaker name appears (“I’m [Name]”, “Joining us is [Name]”) OR the script transitions to a clearly defined segment title (“Segment: [Topic]”)
THEN trigger [Lower‑Third ID Graphic] with name/title or topic; hold for 3–5 seconds.[^3][^13][^4]


### Intros

- IF script position is at very start (first 1–2 sentences) AND includes title, brand name or introduction (“Welcome to [Channel]”, “Today we’re talking about…”)
THEN trigger [Intro Title Sequence] with logo, episode title, and optional brief kinetic typography.[^2][^7][^11]


### Outros \& CTAs

- IF script reaches closing phrases (“thanks for watching”, “see you next time”, “before you go, subscribe…”, “check the description for links”)
THEN trigger [Outro Animation + Subscribe CTA Overlay + End‑screen elements].[^2][^3]


### Picture‑in‑picture

- IF a sentence references screen content explicitly (“on my screen you can see…”, “this interface looks like…”) AND there is live presenter footage
THEN trigger [PiP Layout] (presenter + screen), maintaining it until the explanation of that screen ends.[^2][^5]


### Gallery grid

- IF script enumerates multiple items for simultaneous overview (“Top 5 tools”, “3 examples you should know”, “several case studies”) AND footage exists for each item
THEN trigger [Gallery Grid Layout] during that enumeration segment.[^7][^14][^11]


### Generative / animated backgrounds

- IF script segment is purely conceptual or voiceover (definitions, brand statements) with no specific B‑roll or footage anchors
THEN trigger [Animated Background] plus text/icons rather than raw talking‑head.[^1][^2][^7]


### Stylized effects (slow‑mo, motion trails, comic look)

- IF script flags a dramatic or visually interesting action moment (“watch this carefully”, “in slow motion”, “here’s the highlight”) AND footage contains motion or action
THEN trigger [Slow‑Motion / Stylized Effect] on that specific clip, not globally.[^15][^16]

***

## Anti‑patterns: when NOT to trigger motion graphics (Task 4)

Evidence from UX and motion‑graphics best‑practice articles shows clear downsides of overusing animation.[^6][^2][^17][^15]

### Overuse \& visual fatigue

- Too many simultaneous animated elements (multiple graphics, backgrounds, text all moving at once) → kills visual hierarchy; “when everything moves, nothing stands out”.[^6]
- High‑paced and high‑color scenes directly increase visual fatigue; studies on film scene dynamism show that rapid motion and intense color combinations strain viewers.[^15]

**Signals to avoid triggering**

- If the current scene already has strong motion (fast cuts, handheld camera, action) → avoid extra busy motion graphics; prefer subtle lower thirds.
- If the topic is serious/somber (news about tragedy, sensitive interviews) → avoid flashy glitches or playful kinetic type; use minimal, calm graphics.[^4][^6]
- If a graphic would obscure critical visual information (e.g., charts covering evidence footage) → avoid; use smaller or deferred overlays.
- If multiple triggers fire within the same sentence (comparison words, numbers, CTA) → choose *one* dominant motion graphic (e.g., comparison overlay OR chart), not all at once.[^6][^17]


### Clutter and inconsistency

- Motion‑graphics tutorials warn against cluttered screens and inconsistent styles, recommending that all graphics align with brand identity and appear at appropriate times.[^2]
- UX guidance emphasizes that using too many animation styles in one interface creates chaos and undermines trust.[^6]

**Anti‑rules**

- IF three or more motion‑graphic types would overlap (e.g., lower third + kinetic typography + arrows + animated background)
THEN suppress at least one, prioritising clarity: keep ID + one emphasis element only.[^6][^2]
- IF the animation does not clearly clarify, guide, or delight (per UX checklist)
THEN do not trigger it: motion must “earn its place”.[^6][^1]
- IF the genre and scene tone are formal/serious (documentary interview, corporate statement on sensitive topic)
THEN avoid flashy transitions/glitches; use restrained motion or static graphics.[^4][^3]

***

## Genre‑specific frequency \& density guidelines (Task 5)

Grounded in motion‑graphics best‑practice guides, documentary advice on lower thirds, UX fatigue research, and explainer‑video commentary, the table below gives *approximate* recommended densities per minute.[^1][^2][^3][^4][^6][^15]


| Genre | Typical Motion Graphics per Minute (approx.) | Common Types | Notes |
| :-- | :-- | :-- | :-- |
| Documentary (interview‑driven) | 0.5–2 graphics/minute | Lower thirds, minimal transitions, occasional highlight or data overlay | Use lower thirds at first appearance of each speaker, and sparingly for topic/location IDs; motion should be subtle and unobtrusive.[^4][^13] |
| Documentary (stylized/poetic) | 1–3 graphics/minute | Title cards, restrained kinetic type, occasional animated infographics | Graphics support mood and information; avoid heavy effects in emotional scenes.[^4][^15] |
| Explainer / educational (motion‑graphics style) | 3–6 graphics/minute | Kinetic typography, icons, animated backgrounds, data visuals, transitions | Explainers often rely heavily on motion graphics; still, best‑practice advice stresses clarity, brand consistency, and purposeful animation.[^1][^7][^11] |
| Tutorial / screencast | 2–5 graphics/minute | Arrows/highlights, PiP layouts, lower thirds for steps, occasional transitions | Use highlight shapes and arrows frequently for UI guidance; keep style simple to avoid clutter.[^2][^9] |
| Listicle / Top‑10 | 3–7 graphics/minute | Chapter title cards, list counters, transitions, comparison overlays | Each item typically has a title card and transition; avoid stacking multiple effects per item.[^7][^14] |
| News / broadcast | 3–8 graphics/minute (continuous banners/tickers) | Lower thirds, banners, tickers, transitions, split‑screens | News graphics can be dense but highly structured; use consistent lower‑third style and purposeful motion, as in ABC packages.[^3][^5] |
| Corporate explainer / brand promo | 2–4 graphics/minute | Branded intros/outros, lower thirds, data overlays, light kinetic type | Motion supports brand and messaging; guides stress aligning style with brand identity and avoiding clutter.[^1][^16][^2] |
| Vlog / lifestyle | 0–3 graphics/minute | Minimal lower thirds, occasional pop‑up text, intro/outro animations | Viewers expect authenticity; heavy graphics feel overproduced unless genre is highly stylized.[^1][^2] |
| Social ads / short‑form (Reels/Shorts) | 4–8 graphics/minute (short runtime) | Fast kinetic typography, CTAs, animated backgrounds, arrows | Short videos often use dense motion; still, UX guidance warns against excessive motion that overwhelms users.[^18][^6] |

**Operational guideline for MCP**

- Use the genre label (from metadata or LLM inference) to *scale* trigger thresholds.
- For high‑density genres (explainer, listicle, news, social ads), allow multiple motion‑graphic triggers per minute but enforce anti‑pattern rules (no overlapping chaos).
- For low‑density genres (documentary, vlog), restrict to essential triggers (lower thirds, occasional emphasis) and suppress flashy transitions unless explicitly requested by script or brand style.[^1][^4][^6][^15]

***

You can now translate this document directly into MCP rules:

- **Per type:** a trigger function with script pattern detection, context (genre, section), and narrative weight.
- **Global:** per‑genre frequency caps and anti‑pattern checks to decide when *not* to trigger a graphic.

This gives the LLM enough structured logic to choose *what* motion graphic to use, *when* to fire it, and *when to hold back* to preserve clarity and pacing, all grounded in how real creators and broadcasters actually use motion graphics.[^1][^2][^3][^4][^5][^6][^15]
<span style="display:none">[^19][^20][^21][^22][^23][^24][^25][^26][^27][^28][^29][^30][^31][^32][^33][^34][^35][^36][^37][^38][^39][^40][^41][^42]</span>

<div align="center">⁂</div>

[^1]: https://www.clueso.io/glossary/motion-graphics

[^2]: https://www.miracamp.com/learn/youtube/creating-animated-graphics-your-content

[^3]: https://www.adobe.com/id_en/creativecloud/video/discover/lower-third-graphics.html

[^4]: https://www.soundstripe.com/blogs/a-documentarians-guide-to-lower-thirds

[^5]: https://www.newscaststudio.com/2023/10/02/abc-owned-graphics-package-2023/2/

[^6]: https://lordicon.com/blog/too-much-motion-hurts-ux-heres-why

[^7]: https://www.youtube.com/watch?v=F96q9CiOtq8

[^8]: https://www.youtube.com/watch?v=pdfArI9H16E

[^9]: https://elements.envato.com/arrow-highlight-elements-motion-graphics-7QZHZW8

[^10]: https://www.youtube.com/watch?v=Uql_wqM9g5s

[^11]: https://www.youtube.com/watch?v=8eKZnmOy5Tw

[^12]: https://uppbeat.io/motion-graphics/category/explainer

[^13]: https://modeldiplomat.com/learn/glossary/lower-third

[^14]: https://www.storyblocks.com/all-video/search/explainer-animation

[^15]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11535479/

[^16]: https://www.jisem-journal.com/article/a-research-on-the-dynamization-effect-of-brand-visual-identity-design-mediated-by-digital-14078

[^17]: https://www.spielcreative.com/blog/how-much-animation-is-too-much/

[^18]: https://dl.acm.org/doi/pdf/10.1145/3613904.3642839

[^19]: https://dl.acm.org/doi/pdf/10.1145/3640543.3645164

[^20]: https://arxiv.org/html/2501.07983v1

[^21]: http://arxiv.org/pdf/2207.05872.pdf

[^22]: https://elements.envato.com/news-lower-thirds-GQWDG8N

[^23]: https://www.istockphoto.com/photos/news-lower-third

[^24]: https://www.behance.net/search/projects/news lower third

[^25]: https://www.behance.net/search/projects/news lower third after effects?locale=en_US

[^26]: https://www.istockphoto.com/illustrations/lower-third-shape

[^27]: https://www.shutterstock.com/search/editable-news-lower-thirds

[^28]: https://www.youtube.com/watch?v=Xnp_GxtyHfw

[^29]: https://www.freepik.com/free-photos-vectors/lower-third-news-broadcast-motion-graphics-template

[^30]: https://www.shutterstock.com/video/search/news-lower-third

[^31]: https://www.youtube.com/watch?v=-no8A0l_HqA

[^32]: https://stock.adobe.com/search?k=news+lower+third

[^33]: https://pubmed.ncbi.nlm.nih.gov/26444805/

[^34]: https://www.semanticscholar.org/paper/8281e9a66473c74c6c756502eb56993fea9b671f

[^35]: https://www.semanticscholar.org/paper/085fefc62ec231adb362cffd08836e312eab4c9b

[^36]: https://journals.sagepub.com/doi/full/10.3233/VES-2004-14603

[^37]: https://www.semanticscholar.org/paper/4a8f7d284c53da64d18fe8718b2bb2606477ff8e

[^38]: https://www.semanticscholar.org/paper/5413c2f109e5381f054756e477e5f78dc32c29bf

[^39]: https://www.semanticscholar.org/paper/491201f6872990255d6ce688598fe7644bf4e3a6

[^40]: https://www.semanticscholar.org/paper/e799eb05c1b368cc090b7b80533a7db2377f7f23

[^41]: https://www.shutterstock.com/video/search/creative-arrow

[^42]: https://www.shutterstock.com/id/video/search/highlight-arrows

