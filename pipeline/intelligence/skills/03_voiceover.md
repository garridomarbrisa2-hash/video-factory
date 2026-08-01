# Skill: Voiceover (style-aware)

## Role
Polish script for TTS; add pause markers; pick voice per section — all **in the rhythm the global style demands**.

## Input
- script.md + scenes (with `global_style`)
- The matching style JSON in `pipeline/intelligence/styles/<id>.json`

## Style constraints (read from style JSON `vo` block)

| Field | What you must do |
|-------|------------------|
| `pace` | Sentence length target: `measured` → allow longer, flowing sentences; `brisk` → chop to short punchy lines; `conversational` → natural mix. |
| `energy` | Word emphasis and line intensity: `low_intense` (crime) = understated, weighty; `energetic_confident` (modern) = driven, Vox-style; `authoritative` (history) = documentary-narrator gravity. |
| `pause_markers` | Use **only** these markers where a beat is needed — e.g. crime: `—` and `...`; history: `.` and `—`; modern/minimalist/standard: `.` only. Never invent others. |
| `voice_hint` | Map to the closest voice in `pipeline/config/vo.json` — e.g. "deep, calm, serious" (crime), "documentary narrator" (history), "confident explainer" (modern). |

## Output
- per-scene `vo_text` (spoken form, not on-screen text)
- pause markers from the style's allowed set only
- voice name for the custom TTS config

## Rules
- Shorter sentences for TTS clarity (within the style's pace)
- Numbers spoken as words when natural
- On-screen text ≠ VO text (VO can expand)
- VO rhythm is a **writing** decision (VidRush reference-video principle); visuals stay with the style JSON. Never write delivery-as-edit instructions ("echo effect", "fade out the voice").
