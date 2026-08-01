# Skill: Image Prompt (optional)

## Role
Produce ModelScope still prompts for `Tongyi-MAI/Z-Image` or
`krea-community/Krea-2-Turbo`.

## Output
- `fallback_prompt` per scene in timeline.broll
- Use at most six comma-separated parts and 55 words: one subject, one
  action/pose, one setting, one historical period, simple lighting, one visual
  medium. Shorter wins.
- Never describe a sequence, before/after comparison, collage, split screen,
  UI, captions, logos, watermarks, readable text, detailed money, or detailed
  documents. Remotion adds every label, date, quote, and statistic.
- Avoid complex crowds, multiple simultaneous actions, and conflicting media
  words. Use Z-Image for simple realistic subjects/environments. Use Krea-2 only
  for one explicitly stylized subject or a requested LoRA.
- Good: `Alexander Hamilton seated at a wooden desk, Philadelphia in 1790, soft
  window light, realistic historical oil painting`
- Bad: `Hamilton portrait, bank, crowd, currency, documents, map, cinematic
  photograph, engraving, painting, dramatic collage`

## Ledger-specific additions (when `global_style: ledger`)

Source audit: `projects/american-ledger-vidiq.md` — top performers share near-black backgrounds, deep red + gold palette, ONE focal object. Keep prompts aligned so the render grade doesn't fight the source plate.

- **One focal object, named first.** "A leather-bound ledger on a desk …" never "a desk with books, papers, a quill, a lamp, and a window". Single subject; everything else is shadow.
- **Light stays low and warm.** "dim candle-light", "single tungsten desk lamp", "late dusk through tall windows". Never "bright daylight", "cheerful", "vibrant colors".
- **Period materials over abstraction.** Real wood, brass, ink, paper. No "futuristic", "neon", "glowing UI", "hologram".
- Good: `a leather ledger open on a wooden desk, Washington D.C. in 1790, single candle light, photorealistic historical still`
- Good: `an empty abandoned steel mill interior, rust belt in 1980, dim overcast light through broken windows, desaturated photograph`
- Bad: `downtown wall street with traders phones ticker screens graphs money dramatic cinematic`
