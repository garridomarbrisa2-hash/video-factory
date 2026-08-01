# Skill: Video Prompt (optional)

## Role
When stock misses and the beat needs motion: write a prompt for a video generator
(Runway / Sora / Kling / Veo). This produces a finished motion plate that local
FFmpeg normalizes and grades before final assembly.

## Constraints
- **≤10 seconds** per clip. One continuous shot only — no cuts, no scene changes.
- **One subject, one action, one (near-)locked camera.** The simpler the shot,
  the better it renders; complex multi-subject choreography falls apart.
- **No camera moves in the prompt.** Local footage routing treats generated video
  as finished motion, then applies grade and cut transitions. Ask for a **locked**
  or subtly-held frame so generated motion does not fight editorial assembly.
- **No text overlays, no real-face clones, no logos.**

## What IS allowed
- One mood clause: light / weather / palette / time-of-day.
- A **style/filter keyword** that bakes a look into the footage: `grainy 16mm
  archival`, `VHS`, `glitch`, `noir`, `sepia`, `handheld 80s camcorder`,
  `thermal`. These affect the image, never the camera — additive to our grade.

## Output
A single line: the shot description. Camera move, grade, and duration are decided
by the director + style, not by this prompt.

### Good
- `a wheat field swaying in wind, overcast light`
- `hands kneading dough on a wooden board, close-up, warm side light`
- `grainy 16mm archival: a factory conveyor moving loaves, locked frame`

### Bad (don't emit)
- `camera pushes through a 19th-century mill as workers load sacks into grinding
  stones, dust in shafts of light, then cut to a river` — camera move + multiple
  subjects + a sequence. Split it or reduce to one locked shot.
