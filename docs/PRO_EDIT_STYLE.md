# Pro Edit Style Rules (AE / Premiere language)

**Goal:** Look like After Effects + Premiere documentary/story edit — **not** Framer, Webflow, or CSS UI motion.

---

## Style is script-driven

| Owns | Does not own |
|------|----------------|
| **Script** → `edit_style` (documentary / storytelling / listicle / …) | Skills (only words + structure) |
| **This file** → how pixels move | Website animation patterns |

---

## Banned (website / frontend tells)

| Pattern | Why it reads “dev” |
|---------|-------------------|
| `opacity + translateY` on every title | CSS `fadeInUp` |
| `scaleX` growing accent bars | SVG/CSS progress line |
| `scale()` pop-in on numbers | App icon bounce |
| Word-by-word stagger | Landing hero |
| `box-shadow` glow, pill radius 999 | SaaS chrome |
| `flex` + `gap` “card stacks” as the design | React layout |
| `backdrop-filter: blur` glass cards | Web UI |
| Overshoot bezier `(0.16, 1, 0.3, 1)` | Product motion default |
| Continuous pulse | CSS keyframes |

---

## Required (AE / broadcast)

### Text
- **Linear** or near-linear opacity (2–6 frames), or **hard cut** (0–1 frame).
- Prefer **mask wipe** (clip-path / overflow width) left→right for titles — classic AE linear wipe.
- **No Y-slide** on body type unless lower-third slide (one solid plate, 8–12f linear).
- Type: clean, high contrast, soft drop shadow only: `0 2px 6px rgba(0,0,0,0.7)`.
- Stats: **cut or 3f fade** — never scale from 0.4.

### Lower thirds
- Solid (or 85% black) **rectangle plate**, not glass.
- Accent = **3px left edge** or thin rule **already full width** (draw once; no scaleX grow).
- Slide in from left/bottom as **one plate**, linear, ~10f.

### B-roll / camera
- Motion = footage + **slow** Ken Burns (3–6% over full scene).
- Grade: bottom-weighted darken for LT readability, light vignette, grain ≤ 3%.

### Cuts
- Scene joins: hard cut or short dissolve (8–15f). Energy from script, not UI transitions.

---

## Motion primitives (implementation)

| Primitive | Use |
|-----------|-----|
| `OpacityCut` | 0–3f linear opacity |
| `MaskWipe` | AE linear wipe via clip-path |
| `LowerThirdPlate` | Solid plate + edge, linear slide |
| `StaticType` | No motion — text sits on plate |

Do **not** use FadeUp / scaleX AccentBar / KineticWords stagger.

---

## Checklist

- [ ] No translateY text intros
- [ ] No scaleX bars
- [ ] No glow pills
- [ ] Titles wipe or cut
- [ ] LT is a plate, not a card
- [ ] `edit_style` from script only
