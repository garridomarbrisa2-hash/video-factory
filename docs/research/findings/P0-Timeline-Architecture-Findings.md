# P0 — Timeline Architecture Findings

**Research scope:** FFmpeg timeline orchestration for multi-scene video assembly — concatenation strategies, transition chaining, frame-accurate timing, multi-track audio, chapter markers, error recovery, and timeline-JSON compilation.
**Date:** 2026-07-21
**Method:** Tavily web research (10+ targeted queries), primary sources: ffmpeg.org official docs, FFmpeg Trac wiki, Stack Overflow / Super User / Video Production SE (notably answers by Gyan, llogan, slhck), Mux/Cloudinary/Shotstack engineering blogs, GitHub projects.

---

## 1. Concatenation Strategies — Demuxer vs Filter vs Protocol

FFmpeg has **three** distinct concat mechanisms. Choosing wrong produces corrupted output, frozen frames at stitch points, or silent failure.

### 1a. Concat Demuxer (`-f concat`) — stream-level, no re-encode

```
# list.txt
file 'scene1.mp4'
file 'scene2.mp4'
file 'scene3.mp4'

ffmpeg -f concat -safe 0 -i list.txt -c copy -fflags +genpts output.mp4
```

- **How it works:** Reads packets from each file sequentially at the *stream* level and copies them. `-c copy` = zero re-encode; a 10-minute video joins in seconds.
- **Requirements:** ALL inputs must share codec, resolution, pixel format, frame rate, timebase, and audio parameters (sample rate, channel layout). `-safe 0` allows absolute paths. `-fflags +genpts` regenerates timestamps for smoother playback on some players.
- **Pros:** Fastest; lossless; CPU-trivial.
- **Cons:** Mismatched params → frozen frames at transition points, desync, or unplayable file — **often with no error message**. No filtering/transitions possible.
- **Script directives** (ffconcat format): `ffconcat version 1.0` header, `file`, `inpoint`, `outpoint`, `duration`.
  - **`inpoint`/`outpoint`:** select a sub-range of a file without re-encoding. Works best with intra-frame codecs (ProRes, all-I H.264); with long-GOP codecs you get extra packets before the inpoint. Use the `concatdec_select` metadata var to skip out-of-interval frames when filtering.
  - **`duration` gotcha (documented by Gyan on Super User):** `duration` does NOT limit how much of the clip is output — it only sets the timestamp offset used for the *next* clip. To actually truncate a clip use `outpoint = inpoint + wanted_duration`.
  - **AAC priming-sample gap fix** (video.stackexchange #22203): seamless audio concatenation requires encoding 2 extra AAC frames at both ends of each segment (AAC frame = 1024 samples; at 44.1 kHz one frame = 0.02322 s), then trimming them via inpoint/outpoint. All segments must be an exact multiple of AAC frame duration or you get ~30 ms gaps/clicks at stitch points.
  - A concat list file can **reference itself** as the last entry to create an infinite loop (useful with `-shortest`).

### 1b. Concat Filter (`concat=n=N:v=1:a=1`) — re-encode, mixed inputs

```
ffmpeg -i a.mp4 -i b.webm -i c.mp4 \
  -filter_complex "[0:v:0][0:a:0][1:v:0][1:a:0][2:v:0][2:a:0]concat=n=3:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 20 -c:a aac output.mp4
```

- **How it works:** Decodes every input fully and re-encodes into one continuous stream.
- **Robust normalization pattern** (from Stack Overflow production code): reset timestamps per segment before concat to avoid PTS discontinuities:
  ```
  [0:v]setpts=PTS-STARTPTS[v0];[0:a]asetpts=PTS-STARTPTS[a0]; ... [v0][a0][v1][a1]concat=n=N:v=1:a=1[v][a]
  ```
- **Official docs caveats:** all segments must start at timestamp 0; resolution must be normalized explicitly (scale/pad per input) though pixel format/sample rate/layout are auto-negotiated; differing frame rates produce VFR output; the filter pads shorter audio streams with silence to match the longest stream per segment.
- **Pros:** Handles mismatched inputs; required base for transitions; single-command.
- **Cons:** Full re-encode (slow, generation loss); all inputs decoded in one process — memory grows with N; syntax error-prone.
- **Hybrid strategy:** re-encode only the non-conforming inputs to match, then use the demuxer with `-c copy` for the final join.

### 1c. Concat Protocol (`concat:`) — file-level byte join

```
ffmpeg -i "concat:input1.ts|input2.ts|input3.ts" -c copy output.ts
```

- Byte-level concatenation (like `cat`/`copy`). Only valid for formats that support it: MPEG-TS, MPEG-PS, raw streams, and a few others. **Not valid for MP4/MOV/WebM.**
- **Best use:** intermediate-file workflow — encode scenes to `.ts` then join instantly, or join HLS segments. Named pipes (FIFO) can avoid intermediate disk files entirely.

### Decision matrix

| Scenario | Method | Why |
|---|---|---|
| Same codec/res/fps/params, no transitions | concat demuxer | Lossless, seconds-fast |
| Mixed codecs/resolutions | concat filter | Auto-normalizes A/V basics |
| Transitions between scenes | xfade chain (filter) | Only filters can blend frames |
| MPEG-TS/HLS segments | concat protocol | Simplest, instant |
| Per-scene render cache, then join | demuxer (if identical encodes) | Caching-friendly |
| Sub-range of each scene, no re-encode | demuxer + inpoint/outpoint | Intra-frame codecs only |

---

## 2. xfade Filter Chaining — N-Clip Transition Mathematics

### Single transition

```
ffmpeg -i v1.mp4 -i v2.mp4 -filter_complex \
 "[0:v][1:v]xfade=transition=fade:duration=1:offset=7,format=yuv420p[v]; \
  [0:a][1:a]acrossfade=d=1[a]" \
 -map "[v]" -map "[a]" output.mp4
```

- `offset` = time **in the first input** at which the transition begins.
- Constraint (Trac wiki): `offset <= duration(v1) - transition_duration`, and `duration(v2) >= transition_duration`.
- **`format=yuv420p` after each xfade** is required in most real-world chains (color-space negotiation), and xfade requires both inputs at identical resolution/fps/pixfmt.

### Offset mathematics for N clips

Total output duration = `Σ(durations) − Σ(transition_durations)` — transitions consume time.

Cumulative offset for the k-th xfade (1-based transitions, clips d₁..dN, fades f₁..fN−1):

```
offset_k = (Σ d₁..dk) − (Σ f₁..fk)
```

Worked example (5 clips: 20, 6, 5, 9 s; 1 s fades):
- xfade1 offset = 20 − 1 = **19**
- xfade2 offset = (20+6) − 2 = **24**
- xfade3 offset = (20+6+5) − 3 = **28**
- xfade4 offset = (20+6+5+9) − 4 = **36**

### Chained command (3 clips)

```
ffmpeg -i v0.mp4 -i v1.mp4 -i v2.mp4 -filter_complex \
 "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=41.567[v01]; \
  [v01][2:v]xfade=transition=fade:duration=0.5:offset=55.534,format=yuv420p[video]; \
  [0:a][1:a]acrossfade=d=0.5:c1=tri:c2=tri[a01]; \
  [a01][2:a]acrossfade=d=0.5:c1=tri:c2=tri[audio]" \
 -map "[video]" -map "[audio]" -movflags +faststart output.mp4
```

### Audio-side pitfall (documented on Super User #1739162)

`acrossfade` has **no offset parameter** — it always fades the *end* of the first (already-accumulated) audio into the next. For chain position this happens to work when offsets are cumulative. But when trimming a head segment, you must `atrim` the first audio to `offset + duration` before the acrossfade, or the fade happens at the wrong place:
```
[0:a]atrim=0:14[a0];[a0][1:a]acrossfade=d=4:c1=tri:c2=tri[audio]
```
Common curves: `c1=tri:c2=tri` (linear-ish), or `fade`/`qsin` etc.

### Practical generation loop (from SO #63553906, bash; Python equivalent widely used)

```python
offset = 0.0
for i in range(1, len(clips)):
    offset += duration[i-1] - fade      # cumulative
    v_chain += f"[{prev}][{i}:v]xfade=transition={t}:duration={fade}:offset={offset:.3f}[v{i}];"
    a_chain += f"[{aprev}][{i}:a]acrossfade=d={fade}[a{i}];"
```

### Preserving total runtime ("lost seconds" problem)

Each xfade removes `fade` seconds from the sum. Mitigations:
1. **Plan for it:** compute scene cut points so on-screen content assumes overlap (preferred for generated content).
2. **`tpad=stop=1:stop_mode=clone`** — append a 1 s freeze-frame to each clip to be "sacrificed" to the fade (looks static).
3. **Reverse-tail trick:** duplicate the last second of clip A reversed and prepend a reversed first second of clip B, so the crossfade blends motion instead of stills.

### Performance

- Every clip is decoded for the entire render; one giant filter_complex = single process, memory grows with clip count, and **one bad input aborts the whole render**.
- `xfade_opencl` exists for GPU-accelerated transitions (subset of transition names; requires OpenCL build).
- For long timelines, render scene pairs/segments in parallel (identical encode settings) and join with concat demuxer — but **a transition spans two segments**, so transition frames must be rendered inside one segment (boundary convention: segment owns its outgoing transition).

### Frame-accuracy verification

- `ffprobe -v error -show_entries format=duration -of csv=p=0 out.mp4` → compare against `Σd − Σf`.
- `ffprobe -select_streams v -show_entries frame=pts_time -of csv out.mp4` around each expected transition boundary; confirm monotonic PTS and expected frame count (`fps × expected_duration ±1`).
- Visual: `ffplay`/mpv with `--osd-fractions` scrub to boundary; or extract `select='between(t,off,off+d)'` frames.

---

## 3. Frame-Accurate Seeking

### The two modes (official ffmpeg docs)

- **Input seeking** — `-ss` before `-i`:
  ```
  ffmpeg -ss 00:23:00 -i input.mkv -frames:v 1 out.jpg
  ```
  Seeks to the closest seek point (keyframe) *before* the position. Since FFmpeg 2.1, when **transcoding**, `-accurate_seek` is **on by default**: the surplus segment between keyframe and target is decoded and discarded → frame-accurate AND fast. Disable with `-noaccurate_seek`.
- **Output seeking** — `-ss` after `-i`:
  ```
  ffmpeg -i input.mkv -ss 23:00 -frames:v 1 out.jpg
  ```
  Decodes and discards frame-by-frame up to the position. Frame-accurate but slow for deep seeks. Advantage: timestamps are NOT reset before filtering (useful e.g. burning subtitles at original timestamps).

### Stream copy caveat (`-c copy`)

With `-c copy`, input `-ss` snaps to keyframes — **not frame accurate**. FFmpeg compensates by writing a negative start-time offset (edit list), which some players honor and others render as frozen/garbage lead-in frames. Output `-ss` with copy produces a truncated stream missing reference data → artifacts. **Rule: re-encode when frame accuracy matters.**

### Timestamp handling

- Input `-ss` resets timestamps to zero for the output. To preserve original PTS add `-copyts`.
- `-t` (duration) vs `-to` (end position): mutually exclusive, `-t` wins. With input seeking, `-to` is measured from the *seek point* (since timestamps reset) — a classic off-by-seek bug:
  ```
  # Cut 1:00 → 2:00 of the ORIGINAL using fast seek:
  ffmpeg -ss 00:01:00 -i in.mp4 -to 00:01:00 -c copy cut.mp4   # -to now relative!
  ```
- `-seek_timestamp`: treats `-ss` as an absolute timestamp (files not starting at 0, e.g. TS).
- `-seek2any` (demuxer opt): allow non-keyframe seek at demuxer level.

### Timebase / GOP considerations for assembly

- Default libx264 GOP = 250 frames (10 s @ 25 fps). For cut-friendly intermediates, force keyframes: `-g 1` (all-I, big files), or small `-g` / `-keyint_min`, or `-force_key_frames "expr:gte(t,n_forced)"`.
- For frame-exact math, express times as frame counts: `t = frame / fps`; prefer rational fps sources; check `tbn` (timebase) in ffprobe — concat of files with different `tbn` is a classic desync source.
- Verification: `ffprobe -show_entries frame=pts_time,pict_type -of csv -read_intervals 10%+#100 out.mp4` confirms the first output frame PTS = 0 and is an I-frame.

---

## 4. Multi-Track Audio Timeline

### 4a. Voiceover concatenation

Chain voiceover segments exactly like video — `concat` filter for mixed sources, or acrossfade for slight overlaps:
```
[0:a][1:a]acrossfade=d=0.05:c1=tri:c2=tri[vo]
```
For gap-free TTS stitching, mind the AAC priming issue (§1a) or work in WAV intermediates and encode AAC once at the end (**recommended pipeline: PCM intermediates → single final AAC encode**).

### 4b. Music looping

Three methods:
1. **`-stream_loop -1` (input option) + `-shortest`** — simplest:
   ```
   ffmpeg -i video.mp4 -stream_loop -1 -i music.mp3 -shortest -map 0:v -map 1:a -c:v copy out.mp4
   ```
   ⚠ Known bug (documented r/ffmpeg): with `-c copy` on MP3, a ~30 ms gap is inserted per loop (encoder delay / `start: 0.025057` offset). Fix: loop in PCM domain or re-encode.
2. **filter `amovie=music.mp3:loop=0`** — loop inside filtergraph:
   ```
   -filter_complex "amovie=bgm.mp3:loop=0,volume=0.15[bgm];[0:a][bgm]amix=inputs=2[a]"
   ```
3. **Self-referencing concat list** for endless playlists (`file 'audio.txt'` as last line of audio.txt).
Also `aloop` filter for decoded-domain looping. End music cleanly with `afade=t=out:st=D-3:d=3` before mix.

### 4c. SFX placement with adelay

`adelay` takes per-channel delays in **milliseconds** separated by `|` (append `s` for seconds, `S` for samples; `all=1` applies last value to all channels):
```
ffmpeg -i video.mp4 -i whoosh.wav -i ding.wav -filter_complex \
 "[1:a]adelay=2100|2100[s1]; \
  [2:a]adelay=5s:all=1[s2]; \
  [0:a][s1][s2]amix=inputs=3:duration=first:dropout_transition=0:normalize=0[a]" \
 -map 0:v -map "[a]" -c:v copy out.mp4
```
- Delayed channels are padded with silence — placement is sample-accurate.
- **`amix` key options:** `duration=first|longest|shortest`; `normalize=0` + explicit `volume` per input to avoid unexpected gain reduction (default normalize scales by 1/N); `dropout_transition=0` to avoid level pumping when a short SFX ends; `weights="1 0.25"` for balance. amix works in float — aresample is auto-inserted.

### 4d. Voiceover + music + ducking (sidechaincompress)

```
ffmpeg -i music.mp3 -i voice.mp3 -filter_complex \
 "[1:a]adelay=5000|5000,volume=1.5,apad[vo]; \
  [0:a]volume=0.7[mus]; \
  [vo]asplit=2[sc][mix]; \
  [mus][sc]sidechaincompress=threshold=0.05:ratio=20:level_sc=1:attack=1:release=500[compr]; \
  [compr][mix]amerge[a]" \
 -map "[a]" out.mp3
```
- `apad` extends the voiceover so the sidechain key survives to the end.
- Alternative to amerge: `[compr][mix]amix=inputs=2:normalize=0`.
- Reports note sidechaincompress can silently misbehave with mismatched channel layouts (mono VO vs stereo music) — normalize with `aformat`/pan first.

### 4e. Conditional original-audio muting (scene windows)

```
[0:a]volume=0:enable='between(t,600,1200)'[a0]
```
Timeline-driven: generate enable expressions from the JSON scene map.

**Assembly recommendation:** build the audio timeline fully in the filtergraph (adelay + amix, PCM), then encode AAC once. `-shortest` needs `-shortest_buf_duration` tuning with sparse streams.

---

## 5. Chapter Markers (ffmetadata)

### Workflow

1. Extract existing metadata: `ffmpeg -i in.mp4 -f ffmetadata meta.txt`
2. Edit/append chapters:
   ```
   ;FFMETADATA1
   title=My Video
   [CHAPTER]
   TIMEBASE=1/1000
   START=0
   END=448000
   title=The Pledge
   [CHAPTER]
   TIMEBASE=1/1000
   START=448001
   END=3883999
   title=The Turn
   ```
3. Mux back (no re-encode):
   ```
   ffmpeg -i in.mp4 -i meta.txt -map_metadata 1 -map_chapters 1 -codec copy out.mp4
   ```

### Container notes

- **TIMEBASE** must be explicit; `1/1000` (ms) is the sane choice (examples using `1/1000000000` come from ffprobe defaults). Compute START/END from scene boundaries in ms.
- **MP4/ISOBMFF quirk (Super User #1877167):** FFmpeg writes BOTH QuickTime `CHAP` and Nero `CHPL` chapters; chapter *titles* are carried by `-map_metadata`, so you need both `-map_metadata 1` **and** `-map_chapters 1`. Optionally `-movflags disable_chpl` to skip Nero chapters (QuickTime style has wider support).
- **Windows pitfall:** save the metadata file as ANSI/UTF-8-without-BOM — a BOM on `;FFMETADATA1` breaks parsing. The magic first line must be exactly `;FFMETADATA1`.
- VLC only shows chapter UI when ≥2 chapters exist.
- Merging multiple chaptered videos: extract each (`-f ffmetadata`), offset each file's START/END by cumulative duration (script: tildes "join-chapters.py" approach), then mux into concatenated output.
- yt-dlp `--embed-chapters` uses this same mechanism.

### YouTube recognition

YouTube's canonical chapter source is the **description timestamp list**, not embedded metadata:
- First timestamp must be `00:00`
- ≥3 timestamps, ascending
- Each chapter ≥10 seconds
- Format: `0:00 Title` (colon separator, space before title)
Up to ~72 h processing; active strikes can disable. **Pipeline action: emit both** — embedded ffmetadata chapters (for MKV/MP4 players) and a generated description block (for YouTube). Chapter boundaries must therefore be clamped to ≥10 s scenes in the timeline schema if YouTube is a target.

---

## 6. Error Recovery — Partial Rendering, Scene Caching, Fallbacks

**Note:** this area is sparsely documented as a formal discipline; the following is synthesized from segmentation workflows and production reports.

### Segment-based rendering (the core pattern)

Render scenes as independent files, then join:
```
# per scene i (parallelizable, retryable):
ffmpeg -i assets... -filter_complex "<scene graph>" \
  -c:v libx264 -crf 18 -preset slow -c:a aac -ar 48000 -ac 2 \
  -r 30 -g 60 -pix_fmt yuv420p scene_i.mp4
# join (identical encode params → demuxer-safe):
ffmpeg -f concat -safe 0 -i scenes.txt -c copy final.mp4
```
Requirements for copy-join: **identical** codec, resolution, fps, pix_fmt, sample rate, channel layout, timebase across all scenes. Lock these as pipeline constants. TS intermediates (`scene_i.ts`) are the broadcast-standard spliceable container and tolerate protocol concat; MP4 intermediates are fine for the demuxer.

### Caching strategy

- Key scenes by hash of (scene JSON + asset versions + encode profile); skip render if cached file exists and validates.
- Validate cache entries before join: `ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,sample_rate,channels -of json scene_i.mp4` compared against the pipeline profile; plus duration check `±1 frame`.
- Audio-gap defense: make scene durations exact multiples of AAC frame duration (1024/48000 s) or add the 2-frame head/tail padding trick (§1a) with inpoint/outpoint at join; or keep intermediates PCM/MKV and encode AAC at final mux.

### Failure handling & fallbacks

- **Per-scene retry:** a scene failure only re-renders that scene; N-1 scenes stay cached. (`ffmpeg` exit code + `-xerror` to fail on any decoding error; `-v error -report` for diagnostics.)
- **Corrupt output detection:** `ffmpeg -v error -i scene.mp4 -f null -` — full decode pass that surfaces errors on stderr with exit≠0.
- **Timeout guard:** wrap process; if a filtergraph stalls (deadlock from `-shortest` buffering, EOF-less lavfi sources), kill and retry with simplified graph.
- **Transition boundary ownership:** transitions must be rendered *inside* a segment (e.g., segment owns its out-transition), otherwise the concat demuxer join (hard cut) replaces the intended crossfade.
- **Graceful degradation ladder:** (1) retry scene as-is → (2) retry with lighter preset/different encoder (libx264 → nvenc) → (3) drop fancy transition to hard cut at that boundary → (4) substitute placeholder (color/slate with text) → never abort the whole video for one scene.
- **Timestamp hygiene on retry:** always `setpts/asetpts=PTS-STARTPTS` per scene; verify with ffprobe that first frame pts=0 — non-zero start times break demuxer concat duration math.
- No native ffmpeg checkpoint/resume — orchestration layer (MCP) must own scene-state tracking.

---

## 7. Timeline JSON Schema Design — Compiling to filter_complex

Two reference implementations surfaced:

### A. pilotpirxie/json-to-ffmpeg (open source, MIT, TypeScript) — closest to our need

Schema concepts:
- **`inputs`**: named sources `{type: video|audio|image, file, hasAudio, hasVideo, duration}`
- **`tracks[]`**: `{type: video|audio, clips[]}` — non-linear, multiple tracks
- **clip**: `{name, source, timelineTrackStart, duration, sourceStartOffset, clipType, transform:{x,y,width,height,rotation,opacity}}`, audio clips add `volume`
- **`transitions[]`**: `{type: fade|smoothup|smoothdown|circlecrop|squeezev|squeezeh..., duration, from, to}` — `from:null` = transition-in from black, `to:null` = transition-out to black
- **`output`**: `{file, videoCodec, audioCodec, width, height, preset, crf, framerate, flags, startPosition, endPosition, scaleRatio}`

Observed compilation strategies worth copying:
1. **Black base canvas:** `color=c=black:s=WxH:d=TOTAL[base]`, tracks overlaid on top.
2. **Per-clip preprocessing:** scale → format=rgba → colorchannelmixer=aa=opacity → overlay onto a per-clip black base (enables PiP/rotation) → `rotate` → `fps`.
3. **Gap filling:** explicit `color=black@0.0:d=gapDur[gap_x]` clips between clips on a track; audio gaps via `anullsrc=channel_layout=stereo:sample_rate=44100:d=gap`.
4. **Transitions from/to nothing** compiled as xfade against a short black "void" clip (`duration` snapped to frame grid: e.g. 0.5 s @ 30 fps → 0.43333 s — note: this appears to be their frame-quantization; verify independently).
5. **Sequential assembly per track:** concat chain with fps normalization after every stage (`concat=n=2:v=1:a=0,fps=30`), interleaved with xfade stages for between-clip transitions.
6. **Audio track:** per-clip `atrim=0:dur,asetpts=PTS-STARTPTS,volume=x`, gaps via anullsrc, single concat chain `concat=n=5:v=0:a=1`.
7. **Track compositing:** `[base][track1]overlay[t]; [t][track2]overlay[video_output]`; audio track → volume → `[audio_output]`; `-map '[video_output]' -map '[audio_output]'`.
8. Random label suffixes (`[gap_xbPT0R2D]`) to avoid filtergraph name collisions.

### B. Shotstack Edit API (commercial) — schema UX reference

```json
{ "timeline": {
    "soundtrack": {"src": "...", "effect": "fadeInFadeOut", "volume": 0.5},
    "background": "#000000",
    "tracks": [ {"clips": [
      {"asset": {"type": "video|image|audio|title|html", "src": "...",
                 "trim": 2, "volume": 0.5, "speed": 1,
                 "crop": {...}, "chromaKey": {...}},
       "start": 0, "length": 5, "fit": "cover",
       "position": "top", "scale": 0.5,
       "transition": {"in": "fade", "out": "fade"},
       "effect": "zoomIn"} ]} ] },
  "output": {"format": "mp4", "size": {"width": 1280, "height": 720}} }
```
Model: clips are sequential per track; `length:"auto"`; transitions attached to clip edges rather than separate objects; global soundtrack with ducking-level volume; `effect` = canned motion presets (zoomIn/slideUp → compiled to zoompan/overlay expressions).

### Recommended schema for the FFMPEG MCP (synthesis)

```json
{
  "version": 1,
  "output": {"width":1920,"height":1080,"fps":30,"videoCodec":"libx264","crf":18,"preset":"slow","audioCodec":"aac","audioRate":48000,"channels":2},
  "scenes": [
    {"id":"s1","asset":"scene1.mp4","in":0,"duration":5.0,
     "transition_out":{"type":"fade","duration":0.5},
     "audio":{"volume":1.0}},
    {"id":"s2","asset":"scene2.mp4","in":2,"duration":4.0,"transition_out":null}
  ],
  "audio_tracks": [
    {"type":"voiceover","clips":[{"src":"vo1.wav","at":0.0},{"src":"vo2.wav","at":5.2}]},
    {"type":"music","src":"bgm.mp3","loop":true,"volume":0.15,"duck":{"threshold":0.05,"ratio":12},"fade_out":3},
    {"type":"sfx","clips":[{"src":"whoosh.wav","at":4.5,"volume":0.8}]}
  ],
  "chapters":[{"time":0,"title":"Intro"},{"time":5,"title":"Main"}]
}
```

**Compiler rules:**
1. Fetch all durations via ffprobe up front (`format=duration`); fail fast on missing assets.
2. Quantize every time value to the frame grid: `round(t*fps)/fps`.
3. If any `transition_out` → build xfade chain with cumulative offsets `offset_k = Σd₁..k − Σf₁..k`; matching `acrossfade` chain; else → concat filter (or demuxer path if scenes are pre-rendered files).
4. Normalize per scene before chain: `scale=W:H,fps,format=yuv420p,setpts=PTS-STARTPTS`; audio: `aresample=48000,pan stereo,asetpts=PTS-STARTPTS`.
5. Audio: voiceover clips → `adelay={ms}|{ms}` each; music → `-stream_loop -1` (re-encode path) or amovie loop + `afade` tail; duck via sidechaincompress with asplit key; final `amix=normalize=0:dropout_transition=0`, `alimiter` safety.
6. Emit ffmetadata file from `chapters` (ms timebase; clamp/merge to ≥10 s if `target:youtube`), mux with `-map_metadata 1 -map_chapters 1 -c copy` as a post-pass.
7. Two execution modes: **one-shot** (single filter_complex, small N) and **scene-cached** (per-scene renders + demuxer join + chapter post-pass) chosen by scene count/duration thresholds.

---

## GAPS REQUIRING PERPLEXITY DEEP RESEARCH

1. **Error-recovery discipline:** No authoritative sources on scene-level checkpoint/retry architectures for FFmpeg pipelines (cache invalidation, hash schemes, resume-after-crash). Only fragmented anecdotes. Needs deep research into production systems (Remotion, Revideo, Editly, Shotstack internals).
2. **Frame-exact boundary verification at scale:** Beyond ffprobe spot-checks — automated methods to assert transition boundaries land on exact frame numbers across an N-scene render (e.g., comparing PTS series against expected schedule, perceptual hash checks at boundaries).
3. **xfade + variable fps / mixed timebases:** Behavior of xfade chains when inputs are VFR or have different `tbn`; best-practice normalization order (`fps` vs `settb` vs `setpts`) is not documented in one place.
4. **acrossfade chain drift:** Whether cumulative acrossfade chains accumulate timing/level drift vs xfade's offset model; documented asymmetric behaviors (xfade consumes time from both inputs; acrossfade tail-only) need authoritative reconciliation for chain math.
5. **AAC priming/encoder-delay correctness across containers:** The 2-extra-frames workaround is community folklore (single SE answer + one repo). Precise encoder-delay/trimming metadata handling (iTunSMPB/edit lists) for gapless scene joins in MP4 needs deeper sourcing; whether Opus-in-MKV is the cleaner intermediate.
6. **Hardware-accelerated timeline rendering:** Real-world reliability/perf of `xfade_opencl` and NVENC/CUDA decode in multi-input filtergraphs (surface counts, filter interop, when graphs silently fall back to software).
7. **Parallel segment rendering with shared transitions:** Formal segment-boundary conventions (who owns the transition), keyframe forcing (`-force_key_frames` at segment edges), and whether chunked encodes joined by demuxer are bit-identical to single-pass at boundaries (rate-control discontinuity effects on quality).
8. **Timeline JSON → filtergraph compilation literature:** Beyond json-to-ffmpeg (experimental) — Editly's compiler, Remotion's FFmpeg assembly, FFmpeg's own `ffmpeg CLI` graph limits (max inputs, filterchain length limits, escaping hell on Windows) and when to switch to `filter_complex_script` file.
9. **YouTube embedded-chapter ingestion:** Whether YouTube reads embedded ffmetadata/CHAP chapters at upload (vs description-only), current 2026 behavior — search results only covered description timestamps.
10. **`-shortest` + sparse-stream buffering:** Memory behavior and deadlock conditions with `-shortest_buf_duration` on long timelines with sparse SFX tracks — only a doc paragraph found.
11. **VFR-normalization decision tree:** When to `fps=30` vs `setpts` vs `vsync cfr` per scene for mixed-source (screen capture + camera + generated) timelines; dropped/duped frame accounting.

---

### Key sources
- ffmpeg.org official documentation (ffmpeg.html, ffmpeg-filters.html, ffmpeg-formats.html — concat demuxer, xfade, amix, adelay, -ss/-accurate_seek)
- trac.ffmpeg.org/wiki/Xfade (offset/duration constraints)
- Stack Overflow #7333232, #63553906; Super User #778762, #1671254, #1739162, #1615982, #1847624, #1877167, #1887799; video.stackexchange #22203, #23373, #18247
- ffmpeg-micro.com concat guide; mux.com stitch guide; cloudinary.com concat & audio guides; json2video.com audio guide; ottverse.com xfade catalog
- github.com/pilotpirxie/json-to-ffmpeg (schema + generated graph); shotstack.io docs/examples (schema UX)
- support.google.com/youtube/answer/9884579 (chapter rules)
