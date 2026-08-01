# Per-scene SFX go here (Phase 8, P6).

A scene opts in with `sfx: "<filename>"` in the timeline. The orchestrator
places it at the scene start, scales it to `sfx_volume` (scene override →
timeline `sfx_volume` default 0.6), and mixes it under the VO.

SFX are **one-shot accents**, not a bed — a document rustle, a transition
whoosh, an impact hit. They earn their place only when they serve the beat.
Rarity is enforced (`validate_sfx_rarity`): >2 per video warns.

Suggested free sources: Pixabay SFX, Freesound, YouTube Audio Library.
Name files clearly, e.g. `paper.wav`, `whoosh.wav`, `hit.wav` — reference
from a scene's `sfx` field (filename only, resolved against this dir).
Short mono/stereo WAV or MP3, ~0.2–2s.
