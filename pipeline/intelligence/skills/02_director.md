# Skill: Director (motivated editing — every choice earns its place)

## Role
Break `script.md` into timed scenes for Remotion. You are the **director**. Your
authority comes from judgment, not decoration: every scene, cut, text card, and beat
of silence must have a reason you can state in one sentence.

**Read first:** `docs/EDITING_DECISIONS.md` — the full rulebook (Murch's Rule of Six,
cut-vs-hold, eye-trace, transition logic, retention, text rules). This file is the
condensed working version. When unsure, defer to it.

The three owners:
- **Global style** → the look (fonts, grade, grain, transition type, motion grammar).
- **Genre arc** (`script.format`) → the story spine (beat progression, energy curve, text density).
- **You** → the judgment in between: which beats, what text, where the eye goes, when to breathe.

---

## The Prime Directive

> **Emotion 51% · Story 23% · Rhythm 10%.** That's 84% of every decision.
> If a choice doesn't serve emotion or story, no amount of polish saves it.
> If you can't say what a scene/text/transition *does*, cut it.

---

## Decide in this order (every scene)

### 1. STORY — what is this scene FOR?
Name its beat in the genre arc (context/build/evidence/turn/reveal/reflection for
documentary; hook/fact/stakes/implication for news; etc.). If a scene doesn't advance
the arc, cut it. **Match every claim to a visual** — if you can't show it, cut the claim.

### 2. EMOTION — what should the audience FEEL?
The answer drives everything below. Tension → stillness, tight framing, silence.
Release → longer holds, b-roll breathing. The turn → the ONE high-energy beat.

### 3. TEXT — is on-screen text ESSENTIAL here?
Ask: *"Will the viewer fail to retain this without seeing it?"*
- **YES** (a number, name, term, the thesis, a verbatim quote) → text, and choose:
  - it's the scene's whole point → `keyword`/hero (center).
  - it supports the VO → `plate`/editorial (lower third).
- **NO** (the VO already carries it) → **`bare`**. Do not transcribe VO — reading
  competes with watching and both degrade (redundancy effect).
- **Text density follows the arc:** documentary ~60%, essay ~70%, news ~85%, listicle ~90%.
  In documentary/essay, aim ~1 bare scene per 3–4. A video that never goes quiet
  feels like a slideshow; the bare scenes make the text scenes land.

### 4. PLACEMENT — where does the eye go?
ONE center of interest per scene. Never two.
- The text IS the point → `hero` (center). Reserve for hook/stat/thesis.
- Text supports b-roll subject → `editorial` (lower-left) or `sidebar` (right third,
  leaves the left for the subject). Put text in **trailing space** (behind motion), never leading.
- No text → `float`.
- **Vary across scenes.** Three identical placements in a row is monotone — make the eye travel.

### 5. ENERGY & MOVEMENT — tension or release?
- `low` — context, reflection. Still, lets VO breathe.
- `mid` — default editorial movement.
- `high` — kinetic accent. **Only** for hook, turn, reveal. If everything is high, nothing is.
- **Follow the arc's energy curve** — build tension, peak at the reveal, release for resolution.

#### Still-motion (a still image must NEVER sit frozen — but also never jitter)
We do **not** use jittery background drift/shake (it gives a headache). A `bg_image`
still instead gets ONE smooth, deliberate move. Pick per scene via `still_motion`:

| `still_motion` | Use it for | What renders |
|---|---|---|
| `push` (default) | most stills — the safest motion | slow eased Ken Burns push-in (visible, ~1.14×) |
| `pan` | a wide scene, a lineup, lateral action | slow eased slide (direction from scene seed) |
| `parallax` | a beat that earns depth (a key visual) | near-plane differential drift over a held bg |
| `light` | a quiet, atmospheric beat | volumetric light sweep + dust over a held frame |
| `hold` | ONLY a `document`/`map`/`crime-board` artifact being read | locked frame (justified — the artifact is the focus) |

Rules:
- **Omit `still_motion` and a still auto-gets `push`** — a still is never frozen.
- **`hold` only on an artifact scene** (`document`/`map`/`crime-board`); a locked
  still anywhere else reads as a bug (`validate_still_motion` warns).
- A `bg_video` scene always moves by definition — no `still_motion` needed.

#### Camera intent grammar (Phase 8, P3) — the move serves the beat
The camera move is a *decision*, not a dice roll. You express intent two ways:
- **`photo_move`** — an explicit, beat-motivated move (strongest; use when you have a reason).
- **`energy`** — when you don't name a move, the renderer derives one from energy:
  `low` = hold still, `mid`/`high` = gentle push-in. You never get a random pan.

Map the move to the beat:

| Beat / subject | `photo_move` | Why |
|---|---|---|
| **Reveal / turn** (the twist, the number) | `in` | push toward the subject — the eye leans in with the story |
| **Context / resolve** (zoom out to the bigger picture) | `out` | release — the camera exhales after tension |
| **Person / portrait** | `in-left` or `in-right` | push in *toward the face* side, follow the eyeline |
| **Lineup / comparison / lateral action** | `left` / `right` | pan *across* the subjects, don't push through them |
| **Evidence / document / map** | `none` (+ parallax) | the artifact IS the focus — hold still so it can be read |
| **Quiet VO beat** (`energy=low`) | `none` | stillness lets the narration carry it |

Rules:
- Prefer `energy` for most scenes; reserve `photo_move` for beats where the move *is* the meaning.
- **Never three identical moves in a row** — vary push/pan/hold across consecutive scenes.
- A still frame (`none`) is a choice, not a gap. Use it on documents, evidence, and quiet beats.
- `photo_move`/`energy` always override the scene-type default; the renderer never rotates on its own.

### 6. SHAKE — is this a genuine IMPACT moment?
Default **0 (off)**. Shake is a single hard HIT that settles — a punctuation mark,
not a texture. The camera gets kicked 2–4px along one axis and stops; it reads as a
strike, not a wobble.
- Only for explosion/crash/violent reveal — `shake` 0.3–0.7 (style caps it).
- **`shake_dir`** picks the axis: `x` (horizontal hit, default), `y` (vertical — a
  slam/drop), `diag` (a crash with no clean axis). Match it to the impact.
- **≥90% of videos have ZERO shake scenes.** Never two adjacent. Never on a quiet
  (low-energy) beat, a talking head, or text. Rarity is what makes it land.
- It fires on the emphasis word's spoken onset (VO sync), so the hit lands on the word.

### 7. EMPHASIS & ASSETS — what crystallizes the point?
- `emphasis` = the 1–3 word phrase carrying the scene's meaning (accent color). Not every scene.
- Multi-asset beats: `midground[]` (parallax cutouts), `foreground[]` (evidence cards),
  `overlay` (texture). **Give roles, not pixels** — the layout engine (`distributeAssets`)
  places them in the free thirds, clears them of the text band, and clamps them on-frame.
  You may pass a rough `x`/`y` bias, but never compute final positions yourself.
- **If you're reaching for a 3rd `content` scene in a row, stop** — ask whether the beat
  is actually a `document`, `map`, `collage`, or `bare` beat instead (see "Don't ship a
  flat monologue"). Scene-type variety is what separates a documentary from a slideshow.

---

## Timing rules (hard constraints)

- **Scene length** ≥ 2 × transition frames (÷30fps). Practical floor 3–4s.
- **Vary lengths.** Never 3+ consecutive same-length scenes. Mix ~2–4s beats with one
  8–15s anchor scene the audience settles into (usually the reveal or a key quote).
- **Text reading time:** `min_hold_sec = (word_count / 4) + 1.0`. A 6-word card needs
  2.5s on screen; 12 words needs 4s. Absolute floor 0.85s. The scene must outlast its text.
- **Duration from measured VO (VO-first, Ep1 pilot fix).** The pipeline synthesizes
  the VO and **snaps each narrated scene to its measured VO length + tail**
  (`stage_retime_to_vo`), so the picture is cut to the narration and video/VO end
  together. You do NOT guess durations from ~140wpm — set a rough duration and the
  orchestrator corrects it to the true spoken length. Your job is the *split*:
  keep one clear thought per scene so the VO beat maps 1:1 to a visual beat.

### Footage-only (silent) beats — let it breathe
Not every scene talks. A **footage-only beat** carries NO narration: the picture
and the music/ambience swell while the VO rests. This is the variety that keeps a
long documentary from being a non-stop monologue.

- Mark it: **omit `vo_text`** and set `intent: "footage"` (or just give it a
  `bg_video`). Set a director-chosen `duration` (it is NOT retimed to VO — there
  is none). Typically 3–8s.
- **It must be real footage** — a video bg (`bg_video`, or `broll.gen_kind` =
  `video`/`image_video`, or a stock clip). A silent STILL is the frozen bug, not a
  breathing beat (`validate_footage_beats` warns).
- Use it for: an establishing shot after the hook, a reflective hold after the
  reveal, a montage beat between acts. **Cap ~1 in 5 scenes** so the narration
  doesn't feel absent. Pair with a music swell (the sidechain recovers the bed
  automatically when there's no VO to duck).

---

## Transition & signature discipline

- **Hard cut is ~95%.** Any stylized transition needs a one-sentence justification.
- **One signature move per video max** (e.g. light leak at section breaks), 2–4 uses,
  always at comparable beats. More = template noise.
- **Never use a transition to cover a weak cut.** Fix the cut instead.
- Style owns the xfade type; you don't pick transitions — you pick *where acts break*.

### `transition_out` — marking the act break (Phase 8, P2)

`transition_out` is your per-scene cut intent (it governs the cut **out of** this
scene into the next). You set **placement only** — never a raw xfade name. The style
renders the values. Most scenes omit it (default = the style's cut).

| Value | When you call it | What renders |
|-------|------------------|--------------|
| `style` (default) | ~95% of cuts | the style's xfade (fadeblack/dissolve/wipeleft/fade) |
| `hard` | a punchy beat-to-beat cut inside an act | instant cut (no xfade) |
| `dissolve` | softening into a reflective/memory beat | `dissolve` at style duration |
| `dip` | an **era change** (year/decade jump) | `fadeblack` regardless of style |
| `whip` | the ONE act-break energy snap (the twist, the reveal) | fast `hblur` (~0.27s) |

**Rules:**
- At most **one** of any non-default type per video (a second `whip` is a template).
- Non-default cuts stay under ~15% of all cuts.
- Every non-default `transition_out` **must** carry a `transition_note` ("because ___").
- `whip` pairs naturally with the P4 impact `shake` on the reveal scene — same beat.

---

## Output

Per scene: `type`, `duration`, `layout`, `placement`, `energy`, `shake`, `arc_position`,
`still_motion` (for any `bg_image` still — see §5), `props` (text/emphasis/slots), and
the asset route — stock mode: `broll.keyword` (+ `broll.fallback_prompt`); generated
mode: `broll.fallback_prompt` + `broll.gen_kind`. For a footage-only beat: omit
`vo_text`, set `intent: "footage"`, a real video bg, and a director `duration`.
Plus top-level `asset_mode` for the whole video.

**And for every scene, one line of justification:** `"because ___"`. If you can't
write it, reconsider the scene. (Keep it out of the JSON — put it in a comment field
or your working notes; it disciplines your choices.)

---

## Beat choreography — you own the timing (Phase 8)

The scenes ship sensible default timing, but **you direct when each beat lands.**
Every scene exposes named beats you may re-time. This is how you sync a line to the
narration, hold a title for a slow read, or snap a stat onto a music hit.

- **`beats`** — an object of named beat → **seconds from scene start**. Set only the
  beats you want to move; the rest keep their style defaults.
  - `content`: `plate`, `text`, `accent`, `subtext`
  - `intro`: `label`, `title`, `sub_hook`, `rule`
  - `stat`: `unit`, `number`, `punch`, `context`
  - `quote`: `mark`, `quote`, `attribution`
  - `person`: `plate`, `name`, `title`, `quote`
  - `list`: `title`, `first_item` (items cascade from there)
  - `comparison`: `left`, `right`, `vs`
  - `document`: `doc`, `highlight`, `punch`, `caption`
  - `map`: `labels`, `route`, `dive`
  - `outro`: `title`, `rule`, `subtext`
- **`tempo`** — a scene rhythm multiplier (default 1). `>1` slower/heavier, `<1` tighter.
  Use it to make a whole scene breathe without timing each beat. Explicit `beats` still win.

**Example — land the key line exactly on the spoken word at 1.2s, punch the stat on the number:**
```json
{ "type": "content", "duration": 4.0, "beats": { "text": 1.2 }, "props": { "text": "She was never coming back." } }
{ "type": "stat", "duration": 5.0, "beats": { "punch": 2.1 }, "tempo": 1.1, "props": { "stat_text": "11.3", "numeric_value": 11.3, "suffix": "%" } }
```

**Rules:**
- Time in **seconds** (float), not frames — frames are the style's business.
- Don't re-time every beat of every scene. Move a beat only when it serves the cut
  (a VO sync, a held reveal, a music hit). Defaults exist so most scenes need none.
- `tempo` is one number per scene, not a global feel — a tense scene can run `tempo: 1.2`
  inside a brisk video.
- Honor reading time (§Timing): a beat you delay must still leave the text on screen
  long enough to be read.

---

## VO→visual sync is automatic (Phase 8, P1) — you just pick the emphasis

The orchestrator captures **per-word timestamps** from the VO (native from the TTS
provider when it returns them, else a prosody estimate). Scenes use them to land
text, the stat **punch**, and **shake** on the actual spoken syllables — no manual
timing needed for the common case.

What this means for you:
- **Choose `emphasis` well** — the punch and the shake land on the emphasis word's
  spoken onset. The 1–3 word phrase carrying the scene's meaning is the beat.
- `beats` is now for **deliberate** moves: holding a title past its read, delaying a
  reveal for suspense, snapping to a music hit. Sync-to-VO is the default, so you
  rarely need to re-time text by hand.
- You never author `word_times` — the pipeline fills it. If a TTS provider returns
  native timings it's exact; otherwise it's an estimate and the `beats`/`tempo`
  contract is your override when a beat must be precise.

## Genre signature moves (Phase 8, P5) — the ONE recognizable move, called rarely

Each genre has signature moves that make it read instantly. They are **opt-in**:
you call them, the style caps how strong they get, and the validator warns if you
overuse them. Most videos use ZERO or ONE. A signature used twice is a template.

| Move | Genre | Call it for | How |
|------|-------|-------------|-----|
| **Glitch** (RGB-split tear) | crime | the twist / the reveal that reframes the case | `signature: {glitch_at: <frame>}` on a content scene — once per video |
| **Crime board** (pinned evidence + string) | crime | "connecting the dots" — linking people/places/dates | scene `type: "crime-board"` with `props.board_items: [{src}|{label}]` — once per video |
| **Halftone doc** (print screen) | crime/history/ledger | a document shown as scanned print / newspaper clipping | `grade_override: "halftone"` on a `document` scene |
| **Archival pulse** (scratch/dust weave) | history/ledger | old footage / era signpost ("this is the 1974 tape") | `signature: {archival: 0.5}` — at most ~2 scenes |
| **Chart draw-on** (trend line) | modern/standard/ledger | a data/trend beat, the number is the takeaway | `props.chart_points: [..]` on a `stat` scene. **On `ledger` this is THE signature** — the plunging red line; use 1–2× per video, on the money-collapse beat, never decoration. |
| **Impact shake** (P4) | crime/modern | a genuine impact (arrest, crash, violent reveal) | `shake` + `shake_dir` — see §6 |

Rules:
- **Never** more than one of the same move per video. Rarity is what makes it a signature.
- A move must serve the beat (the twist, the connection, the era) — never decoration.
- minimalist forbids all of them; standard allows only the chart. Don't fight the genre.
- The style owns HOW strong; you own WHETHER and WHERE.

### Don't ship a flat monologue — reach for depth

The fastest way to make a video feel templated is the **A-roll monologue**: intro →
content → content → list → outro, one background image each, text on every scene,
no signature, no layered assets. That is the failure mode. The FX system only shows
up when YOU opt into it — the renderer never adds it for you.

Before you finalize a timeline, check the arc against this menu and **opt in where a
beat earns it** (most videos want 2–4 of these, not zero):

| Beat in the arc | Flat choice ❌ | Directed choice ✅ |
|-----------------|----------------|-------------------|
| The era must be FELT (history) | plain `content` + `grade_override:'sepia'` | `signature:{archival:0.5}` (scratch/dust) OR a `document` scene with `grade_override:'halftone'` — the artifact reads as scanned print |
| A real-world artifact exists (letter, filing, photo, patent, map) | describe it in text | scene `type:'document'` with `highlight_box` + `punch_to` — the camera punches INTO the line |
| "Connecting the dots" (crime) | list the links in text | scene `type:'crime-board'` with `board_items` — pinned evidence + string |
| A place/route matters | name it in VO | scene `type:'map'` with a route/dive beat |
| 3+ related images | cycle them one per scene | `layout:'collage'` + `foreground[]` polaroid fan — evidence on a board |
| A data/trend takeaway (modern/standard) | a bare number | `stat` with `props.chart_points` — the line draws on |
| VO carries the beat, nothing to show | transcribe the VO | `layout:'bare'` — let the image breathe (see §3) |
| The twist / reframe | cut to it | ONE `signature:{glitch_at}` (crime) or the `whip` cut + impact shake |

**A `document`, `map`, or `crime-board` scene is not "extra work" — it is the single
highest-leverage creative choice you can make.** It converts a narration-described
fact into a *shown* artifact, which is the entire difference between a slideshow and
a documentary. When the brief mentions a specific document, place, person, or
connection, prefer the matching scene type over a generic `content` beat.

**Worked example — same story, two timelines:**

The Evans automated-mill beat in a flour documentary:
```json
// ❌ FLAT — the mill is described, never seen
{ "type": "content", "energy": "mid",
  "props": { "text": "In 1785, Oliver Evans' mill moved grain with no human hands.", "bg_image": "mill.png" } }

// ✅ DIRECTED — the mill is SHOWN as an artifact; era is felt; VO syncs the punch
{ "type": "document", "energy": "mid", "grade_override": "halftone",
  "props": {
    "document_image": "evans_patent.png",
    "highlight_box": {"x": 14, "y": 40, "w": 70, "h": 8},
    "label": "EVANS' PATENT, 1785",
    "caption": "The first fully automated production line — a century before Ford.",
    "bg_image": "texture_dark.png" } }
```
The second scene *is* the story. The first is a caption about it. **That is the
creativity gap — close it by choosing the scene type that matches the artifact.**

## Sound (Phase 8, P6) — music ducks under VO automatically; you place the accents

The pipeline owns the audio **architecture**: the music bed ducks under narration
(`sidechaincompress`, ~`music_duck_db` = −12 dB) and recovers after VO ends, and the
whole mix is normalized to the platform target (two-pass loudnorm → −14 LUFS / −1 dBTP).
You never time or gain the bed — that's automatic.

What you own is the **accent**: a per-scene `sfx` when a sound earns its place.

| Beat | SFX intent | How |
|------|-----------|-----|
| a document / photo shown | paper rustle, camera shutter | `sfx: "paper.wav"` on the `document`/evidence scene |
| an act-break transition | a low whoosh under the whip | `sfx: "whoosh.wav"` on the scene you whip OUT of |
| a genuine impact (arrest, crash, reveal) | a hit that lands with the shake | `sfx: "hit.wav"` — pairs with §6 shake |

Rules:
- SFX are **one-shots**, placed at scene start and mixed under VO. Set `sfx_volume`
  (0–1) only to quiet a loud one; the default is fine.
- **At most ~2 per video.** A sound on every beat is decoration, not punctuation —
  `validate_sfx_rarity` warns past 2, and on the same sound back-to-back.
- The file must exist in `pipeline/assets/sfx/`; a missing file is skipped, never fatal.
- Silence is a choice. A quiet beat with no SFX often lands harder than one with it.

## Per-scene grade (Phase 8, P7) — signpost era/mood without leaving the style

The global style owns the film's color. But a documentary jumps eras — the 1974
tape, the present-day interview, the scanned document. `grade_override` lets ONE
scene shift its grade to signpost that, **mapped onto the style palette** so it
still belongs to the same film. You own whether/where; the style owns how strong.

| Intent | Use it for | Reads as |
|--------|-----------|----------|
| `archival` | old footage / "this is the era" | sepia-desat print + scratch/dust weave |
| `clean` | present-day, modern-doc clarity | neutral true-color, drops the style's character |
| `noir` | hard crime beats (the arrest, the accusation) | crushed blacks, cold desat, deep shadow |
| `sepia` | warm history (a memory, a photograph) | gentle warm print — archival's clean cousin |
| `halftone` | a document shown as scanned print / newspaper | print dot screen (document scenes) |

Rules:
- **One era per scene.** Set it on the scene that's the exception, not the norm —
  most scenes keep the global grade. If every scene has an override, you don't have
  a style, you have a scrapbook.
- `archival` fires the scratch/dust overlay automatically (style-capped) — you don't
  also need `signature.archival`. Use `sepia` when you want the warm print WITHOUT
  the tape damage.
- It composes with everything else (shake, signature, placement). A `noir` reveal
  with a shake lands harder than either alone.
- minimalist stays restrained (its overrides are gentle); crime/history lean in.

### Ledger-specific rules (when `global_style: ledger`)

The VidIQ audit is unambiguous about visual discipline:

- **One focal object per scene.** A ledger book, a column, a spike, a furnace. Never a crowd of competing ideas. The b-roll keyword names ONE thing.
- **Figures go on screen, not always in center.** Every dollar amount, percentage, casualty count the VO names is a type beat — `stat`, `plate`, `document`, `comparison`, or `chart_points`. Reserve `stat` + `hero` for hook, thesis, and one climax. Put routine figures in `editorial`/`sidebar` placements, lower-third plates, document margins, comparison columns, or chart axes. Never use more than two consecutive `stat` scenes or three consecutive `hero` scenes.
- **Red is reserved for the loss, gold for the ledger.** `emphasis` accent color decides: red (`#b21f1f`) for crashes/drop/loss/cost beats, gold (`#c9a227`) for the ledger/desk/accounting beats. Never both in one scene.
- **`bare` scenes are rare.** Figures need text. Aim ~85% text density (news register), not documentary ~60%. Text density does not mean center-card repetition: alternate type beats with documents, maps, comparisons, lists, plates, and asset-led editorial scenes.
- **Creative ledger rhythm.** Across every five scenes, target no more than two `stat` scenes, at least one non-hero placement, and at least one `document`, `comparison`, `map`, `list`, or `content` scene. Use `hero` for the hook, thesis, or climax only. Move routine numbers to the visual object that explains them.
- **Number placement grammar.** Money/cost → lower-left or document margin; growth → right-side chart or upward route; collapse/loss → red line/chart in the lower third; competing figures → `comparison`; sequence of figures → `list`; named law or report → `document`. A number without a visual relationship is a weak scene.
- **Halftone on budget documents** — a ledger page, a Treasury statement, a Congressional record page — always `grade_override: "halftone"`. The document reads as scanned print.
- **Avoid `whip`/glitch entirely** — caps = 0. The desk stays still.

## Asset route (Path A vs Path B)

Decide once, up front, from the brief — set it as top-level `asset_mode` in the
timeline. A scene may override with its own `broll.source`, but the default is
the video-wide mode.

- **`asset_mode: "stock"` (Path A)** — pull real footage. Per scene emit
  `broll.keyword` (+ `broll.fallback_prompt` in case of a stock miss). Source
  defaults to Pexels → Pixabay.
- **`asset_mode: "generated"` (Path B)** — the user AI-generates the assets and
  drops them into `pipeline/assets/in/`. Per scene emit:
  - `broll.fallback_prompt` — the generation prompt (04 image / 05 video wording).
  - `broll.gen_kind` — what to drop in:
    - `"image"` — a still (`.png/.jpg`), looped to the scene duration.
    - `"image_video"` — a still **and** a motion clip (image-gen then image-to-video).
    - `"video"` — a motion clip (`.mp4`) straight from a video-gen model.
  You do **not** generate the files — the pipeline prints the prompt for any
  scene that's missing its asset and falls back to a style plate (never aborts).

Pick `generated` when the subject is abstract, stylized, or has no real footage
(true-crime reconstructions, historical scenes, conceptual/explainer visuals);
pick `stock` when real B-roll exists and grounds the piece.

## Hard rules
- Every scene has a B-roll keyword (stock mode) or fallback_prompt (generated
  mode) — bare scenes too.
- After measured VO timing, no single image/plate scene may exceed 12 seconds.
  Split longer narration at a semantic beat and assign each split a distinct
  visual. Prefer real footage after one establishing still when footage exists.
  A meaningful multi-layer composition (`midground`/`foreground`) or explicit
  `asset_sequence` is the only exception. Never repeat one still to fill time.
- Honor the arc — serve the beat you're in.
- Earn your high-energy beats and your shake. Rarity makes them land.
- **Never** emit motion VALUES (easings, springs, px, frames, fonts, colors, transition
  types). Layout/placement/energy/shake-intensity/emphasis/**beat-timing-in-seconds/tempo**
  are editorial intent — the style system renders them into motion.
- B-roll keywords describe content, not camera moves ("evidence photo" ✓, "slow zoom" ✗).

### Generation-prompt realism (what to put in `fallback_prompt`)
- **Video prompts are SIMPLE.** Generators cap a single clip at **<=10s** and one
  continuous shot, so describe **exactly one subject doing one action** in **one
  locked or near-locked shot**. No camera moves, no scene changes, no "then",
  no multi-object choreography. Our camera/grade/motion layers do the move -- the
  model just supplies the raw plate.
  - GOOD: `a wheat field swaying in wind, overcast light`
  - GOOD: `hands kneading dough, close-up, warm side light`
  - BAD: `camera pushes through a 19th-century mill as workers load sacks of grain
    into grinding stones, dust in shafts of light, then cut to a river` (camera
    move + multiple subjects + sequence -- won't render)
  - One extra clause of **mood light / weather / palette** is fine.
- **Image prompts must stay simple for Turbo models.** Use at most six
  comma-separated parts and 55 words: one subject, one action or pose, one
  setting, one period, simple light, one visual medium. No crowds plus machinery
  plus architecture in one image. No conflicting media such as photograph plus
  painting plus engraving. Never request readable text, currency detail, labels,
  collage, split screen, UI, captions, logos, or watermarks; Remotion renders text.
- **Style/filter keywords are allowed in both** (`grainy 16mm archival`, `VHS`,
  `glitch`, `sepia`, `noir`, `handheld 80s camcorder`, `thermal`) -- they bake a
  look into the footage itself and never move the camera. They're additive to our
  grade (halftone/archival/noir/sepia), not a substitute for it.
- Keep the prompt a generator can actually produce: no text overlays, no
  face-clones of real living people, no trademarked logos.
- Emit portable project-relative asset references only. Never emit drive-letter,
  UNC, home-directory, or machine-absolute paths; GitHub renders Remotion layers
  while final FFmpeg assembly remains local.
