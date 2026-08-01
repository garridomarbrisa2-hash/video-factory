# Research Prompt: Timeline Architecture Patterns for Multi-Scene Video Assembly

## Role
You are a video systems architect and FFmpeg expert designing the timeline orchestration layer for an MCP server. The goal is to define how to assemble dozens of video segments, images, audio tracks, and motion graphics into a cohesive final video with frame-accurate timing, transitions, and chapter markers.

## Context
A video automation factory produces videos with this structure:
```
0:00-0:05  Intro: Logo animation + title card + music sting
0:05-0:12  Scene 1: B-roll + voiceover + lower third
0:12-0:20  Scene 2: B-roll + voiceover + kinetic typography
0:20-0:28  Scene 3: Split-screen comparison + data overlay
...
0:55-1:00  Outro: CTA + subscribe animation + music fade
```

Each scene has:
- Video source (file, image sequence, or generated)
- Audio source (voiceover segment, music, SFX)
- 0-5 motion graphics overlays with independent timing
- In/out transitions (crossfade, wipe, glitch, etc.)
- Optional chapter marker

---

## TASK 1 — Assembly Strategy Comparison

Compare these approaches for multi-scene assembly:

### Strategy A: Single filter_complex
All scenes, transitions, and overlays in one massive filter graph.

Research:
- Maximum practical filter_complex size (nodes, memory, parse time)
- Debugging strategies when graph fails
- Performance implications vs segmented rendering
- Frame accuracy of transitions between scenes

### Strategy B: Scene Rendering + Concatenation
Render each scene to intermediate file, then concatenate.

Research:
- Concat demuxer vs concat filter vs concat protocol — when each is correct
- Codec consistency requirements (same codec, parameters, timebase)
- Audio-video sync preservation across concatenation
- Chapter marker embedding at scene boundaries

### Strategy C: Hybrid — Segment Groups
Group related scenes (e.g., intro+scene1, scene2+scene3) into segments, render separately, concatenate.

Research:
- Optimal segment size for parallelism vs overhead
- How to handle transitions spanning segment boundaries
- State management between segments

### Strategy D: External Timeline Format
Use FFmpeg with external timeline description (EDL, XML, custom JSON).

Research:
- Can FFmpeg read EDL/CMX3600? (Limited, but possible)
- XML timeline formats (Final Cut Pro XML, AAF, OTIO)
- Custom JSON → filter_complex generation pipeline

---

## TASK 2 — Transition Chaining Mathematics

`xfade` only connects two clips. Derive formulas for N-clip chains:

### Chain of 3 clips with crossfades
```
[0][1]xfade=offset=D1:dur=T1[ab];
[ab][2]xfade=offset=D1+D2-T1:dur=T2[abc]
```

Generalize for N clips:
- Offset calculation for clip i in the output timeline
- Audio equivalent using `acrossfade` — same math?
- Mixed transition types (fade, wipe, glitch) in one chain

### Non-linear transitions
- Fade through black: A → fadeout → black → fadein → B
- Dip to white, dip to color
- Zoom transition: scale A up while scaling B down

Provide filter_complex templates for 2-10 clip chains.

---

## TASK 3 — Frame-Accurate Timing Control

Research precise timing mechanisms:

### Input seeking vs output seeking
- `-ss` before `-i`: fast, keyframe-aligned, inaccurate
- `-ss` after `-i`: slow, frame-accurate
- `-ss` with `-accurate_seek`: behavior matrix by codec

### Timebase consistency
- `settb`, `setpts`, `asetpts` for synchronizing streams
- Variable frame rate (VFR) to constant frame rate (CFR) conversion
- Timebase conflicts in filter_complex — detection and resolution

### Duration control
- `-t`, `-to`, `-fs` — which is frame-accurate?
- `trim`/`atrim` vs `-ss`/`-t` — precision comparison
- `select` filter for frame-exact extraction

---

## TASK 4 — Multi-Track Audio Timeline

Design audio assembly for:

### Voiceover segments
- Concatenate 10 TTS clips with 200ms crossfades
- Auto-duck music under each segment
- Handle variable TTS durations (script says 5s, TTS says 4.2s)

### Music continuity
- Single music track under multiple scenes
- Loop music if video exceeds track length
- Crossfade between music tracks at scene boundaries

### SFX placement
- Frame-accurate SFX sync to visual events (whoosh on transition, ding on counter)
- Sample-accurate delay with `adelay`
- SFX ducking under voiceover (lower priority than music ducking)

---

## TASK 5 — Chapter Marker & Metadata

Research FFmpeg chapter support:

- `ffmetadata` format for chapters
- Chapter embedding in MP4, MKV, MOV
- YouTube chapter recognition requirements
- Chapter title, start, end — can chapters have thumbnails?

Provide commands to:
- Extract chapters from existing video
- Insert chapters at scene boundaries
- Validate chapter timing against actual content

---

## TASK 6 — Error Recovery & Partial Rendering

Design for failure resilience:

- Scene 5 of 10 fails → re-render only scene 5, concatenate with cached scenes
- Validation checkpoints: probe each scene before final assembly
- Fallback strategies: if transition fails, use hard cut; if overlay fails, render without
- Logging and debugging: how to inspect which filter_complex node failed

---

## TASK 7 — MCP Timeline Schema Design

Design a JSON schema for timeline description that compiles to FFmpeg commands:

```json
{
  "timeline": {
    "fps": 30,
    "resolution": "1920x1080",
    "scenes": [
      {
        "id": "scene_1",
        "duration": 7.0,
        "sources": {
          "video": {"type": "file", "path": "broll1.mp4", "trim": [2.0, 9.0]},
          "audio": {"type": "file", "path": "vo1.mp3", "gain": 1.0}
        },
        "overlays": [
          {"type": "lower_third", "text": "Speaker Name", "start": 0.5, "duration": 3.0}
        ],
        "transition_in": {"type": "fade", "duration": 0.5},
        "transition_out": {"type": "wipe_left", "duration": 0.5},
        "chapter": "Introduction"
      }
    ]
  }
}
```

Research:
- How to represent arbitrary filter chains in JSON?
- Expression embedding in JSON strings — escaping issues
- Validation of JSON schema before FFmpeg compilation
- Compilation to single filter_complex vs segmented rendering

---

## Final Output Format

1. **Strategy comparison matrix** — A vs B vs C vs D with pros/cons
2. **Transition chaining formulas** — mathematical foundation + templates
3. **Timing control reference** — seeking, timebase, duration precision guide
4. **Audio timeline specification** — voiceover, music, SFX orchestration
5. **Chapter/metadata implementation** — commands and validation
6. **Error recovery architecture** — checkpoints, fallbacks, debugging
7. **MCP timeline schema** — JSON specification with compilation examples
