# Phase 6 Plan — Genre Engine & Dynamic Direction

**Date:** 2026-07-22 · **Status:** approved · **Trigger:** user feedback on v1 FX upgrade
**Research base:** `docs/AE_TRENDS_CATALOG.md`, `docs/REMOTION_AE_TECHNIQUES.md`

---

## Problem diagnosis (from user feedback)

| # | Complaint | Root cause (verified in code) |
|---|-----------|-------------------------------|
| 1 | Every scene has shake | `SceneShell` calls `cameraShake(..., vocab.shake, 0, ...)` **unconditionally at frame 0** — style-global, no per-scene opt-in |
| 2 | Text stiff, same everywhere | `MaskLineReveal` needs manual `\n` breaks (never provided → one long line); all text locked to bottom-left, hardcoded sizes, one entrance type |
| 3 | Scenes don't always need text | Director had no `bare`/text-presence judgment guidance — every scene defaulted to text |
| 4 | Document scene: orange middle + text bottom-left, confusing | Document centered at 56% w/ accent highlight mid-frame, caption plate detached bottom-left — two competing focal anchors; punch doesn't bring the line to the viewer |
| 5 | Object placement poor | No layout grid — foreground cards hardcode `x:24`, midground dead-center, text bottom-left; elements collide, no rule-of-thirds, no text-safe zones |
| 6 | Doesn't tell a story per genre | 5 styles change only colors/fonts — no **story grammar** (documentary builds, news hits, essay argues, listicle counts) |

**Core philosophy (user-stated, now the design goal):**
> The system assembles a collection of assets into a story that fits the script,
> with genre-specific grammar — documentary, storytelling, news — not just
> re-skinned templates.

---

## Design

### A. Shake → per-scene opt-in (issue 1) ✅ decided
- Remove `shake` from style `motionVocab` as a default.
- `SceneShell` gains optional `shake?: number` + `shake_at?: number` props.
- Director opts in per scene **only for genuine impact beats** (explosion, reveal, drop).
- Style keeps a *ceiling* (`max_shake`) so crime can allow heavier hits than minimalist.

### B. Layout engine (issues 2, 5) — `components/layout.ts`
A single placement authority all scenes read from:

```
Rule-of-thirds grid (1920×1080):
  vertical lines at x = 640, 1280   → anchors 'left' | 'center' | 'right'
  horizontal lines at y = 360, 720  → anchors 'top' | 'middle' | 'bottom'
Text-safe zone: 5% margins (title-safe) — nothing important outside.
Focal anchor: each scene declares ONE focal point; all elements align to it.
```

- `resolvePlacement(role, intent, style)` → `{left, top, transform, maxWidth, textAlign}`.
- Roles: `title`, `body`, `plate`, `subject` (midground), `evidence` (foreground), `caption`.
- Intents: `hero` (center), `editorial` (lower-left third), `sidebar` (right third), `float` (no text).
- Slot placement becomes **computed**, not hardcoded: evidence cards distribute across the non-text two-thirds; midground cutouts anchor to the empty third.

### C. Flexible type system (issue 2) — upgrade `effects/typography.tsx`
- **Auto line-break:** `breakLines(text, maxCharsPerLine)` — greedy word-wrap so titles never need manual `\n`. Keeps lines balanced (avoids orphan last line).
- **Responsive size:** `fontSizeFor(text, role)` — longer text → smaller size, so a 6-word title doesn't overflow.
- **Placement intents:** title/body accept `placement` prop → resolved by layout engine (not always bottom-left).
- Entrance variety stays style-owned (`titleMode` in vocab) but the *same* entrance now lands at the *right* position.

### D. Document scene redesign (issue 4) — single focal hierarchy
- The highlighted line IS the focal point. Camera punches **toward the highlight_box center**, bringing it to frame center (not leaving it mid-frame).
- Caption **anchors under the document**, aligned to the punch destination — not floating bottom-left.
- One focal anchor: document first, then (post-punch) the caption replaces it. No two anchors competing.
- Label moves to top-left text-safe zone.

### E. Genre story arcs (issue 6) — `director` skill v3 + `genreArcs.ts`
Styles keep visual identity; **arcs add scene-progression grammar**. Arc is *derived from script format* (already in style JSON `script.format`), not the visual style id.

| Arc (from script.format) | Progression | Scene grammar |
|---|---|---|
| **documentary** (history, crime-mystery) | context → evidence → turn → reveal → reflection | slow open, document/map beats, stat at the turn, quiet quote to close |
| **news / crisis** (modern) | breaking → fact → stat → implication → outlook | hard intro, fast stat, comparison for stakes, minimal quiet |
| **essay / storytelling** (standard, storytelling) | hook → build → deepen → payoff → takeaway | keyword beats, person cards, one bare reflection scene |
| **listicle** (standard-list) | tease → #N… → #1 → recap | repeated content/list beats, stat punctuation, countdown rhythm |
| **explainer** (minimalist) | promise → step 1…n → result | clean plates, list reveals, no texture |

`genreArcs.ts` exposes `arcFor(format)` → `{sceneFlow: string[], energyCurve: number[], textDensity: number}`.
Director skill reads it to pace scene types + energy + when to go `bare`.

### F. Director skill v3 (issues 1, 3, 6) — rewrite `02_director.md`
New explicit judgments per scene:
1. **Text presence:** does this beat need on-screen text? (`bare` if VO carries it — director decides, per user choice)
2. **Shake:** is this a genuine impact beat? (default no)
3. **Layout intent:** hero / editorial / sidebar / float (feeds layout engine)
4. **Energy:** low / mid / high (already present)
5. **Genre arc position:** where in the arc is this scene (context/evidence/reveal/…)?

---

## Files touched

**New:**
- `remotion/src/components/layout.ts` — grid + placement engine
- `remotion/src/components/genreArcs.ts` — format → story arc grammar

**Modified:**
- `remotion/src/components/SceneShell.tsx` — shake opt-in, layout-aware slots
- `remotion/src/components/effects/typography.tsx` — auto-break, responsive size, placement intents
- `remotion/src/components/effects/mediaSlots.tsx` — computed placement (no hardcoded x)
- `remotion/src/components/tokens.ts` — drop shake default, add max_shake ceiling
- `remotion/src/scenes/Document.tsx` — focal-hierarchy redesign
- `remotion/src/scenes/*.tsx` — read placement from layout engine
- `pipeline/intelligence/skills/02_director.md` — v3 (text judgment, shake opt-in, arc)
- `pipeline/intelligence/timeline_schema.json` — `shake`, `shake_at`, `placement`, `arc_position`
- `AGENTS.md`, `Implementation-Tracker.md` — phase 6 entry

---

## Acceptance criteria

1. Shake appears **only** on scenes where the director set `shake > 0`.
2. A 6-word title auto-breaks into balanced lines and lands at the declared placement (not always bottom-left).
3. Document scene: highlight punches to frame center, caption sits under document — single focal path.
4. Evidence/midground assets never collide with text (computed placement respects text-safe thirds).
5. Same script through two genre arcs (e.g. documentary vs news) produces **different scene progressions**, not just different colors.
6. Typecheck clean; one genre rendered end-to-end.

---

## Out of scope (deferred)
- Per-word VO-synced captions (`@remotion/captions`) — needs VO timestamp plumbing; phase 7.
- TransitionSeries between scenes (kept FFmpeg xfade batch architecture).
- AI cutout generation for midground (assets must already be PNG w/ alpha).
