# P0 Audio Mastery — FFmpeg Findings

**Research date:** 2026-07-21
**Research tool:** Tavily web search (12 queries, ffmpeg.org docs + community sources)
**Target consumer:** Video Automation MCP Server (FFmpeg tool design)

This document catalogs FFmpeg's audio filters relevant to sidechain compression, loudness normalization, audio ducking, TTS voice sweetening, mixing, automated QC analysis, and complex filter chaining. Each entry includes parameters with defaults/ranges, timeline-expression support, real commands, pitfalls, and validation methods.

---

## 1. Sidechain Compression & Auto-Ducking

### 1.1 `sidechaincompress` — Dynamics / Sidechain

Acts like a normal compressor, but gain reduction on the **first input** is driven by the signal of the **second input** (the sidechain). Two inputs in, one output out. Canonical use: duck music under a voiceover.

**Parameters (from ffmpeg.org docs):**

| Param | Default | Range | Notes |
|---|---|---|---|
| `level_in` | 1 | 0.015625 – 64 | Input gain (of the signal to be compressed) |
| `mode` | `downward` | `downward` / `upward` | Downward = duck; upward = expand |
| `threshold` | 0.125 | 0.00097563 – 1 | Sidechain level that triggers reduction |
| `ratio` | 2 | 1 – 20 | 1:2 means 4 dB over threshold → 2 dB after |
| `attack` | 20 ms | 0.01 – 2000 | Time above threshold before reduction starts |
| `release` | 250 ms | 0.01 – 9000 | Time below threshold before reduction eases |
| `makeup` | 1 | 1 – 64 | Post-processing amplification |
| `knee` | 2.82843 | 1 – 8 | Soft knee around threshold |
| `link` | `average` | `average` / `maximum` | Which sidechain channel drives reduction |
| `detection` | `rms` | `rms` / `peak` | RMS is smoother; peak reacts faster |
| `level_sc` | 1 | 0.015625 – 64 | Sidechain gain (boost quiet voice triggers) |
| `mix` | 1 | 0 – 1 | Blend compressed vs dry signal |

**Timeline support:** Yes — all above options are also runtime **commands** (can be changed live via `sendcmd`/ZMQ).

**Canonical ducking command (music + voiceover):**

```bash
ffmpeg -i music.mp3 -i voiceover.mp3 -filter_complex \
"[1:a]asplit=2[sc][mix];[0:a][sc]sidechaincompress=threshold=0.05:ratio=8:attack=50:release=500:makeup=2[bg];[bg][mix]amerge[final]" \
-map "[final]" -c:a aac -b:a 192k output.mp4
```

**Video + music bed + TTS voiceover (full pipeline shape):**

```bash
ffmpeg -i video.mp4 -i music.mp3 -i tts_voice.wav -filter_complex \
"[2:a]asplit=2[vo][sc]; \
 [1:a]volume=0.6,apad[bed]; \
 [bed][sc]sidechaincompress=threshold=0.03:ratio=10:attack=20:release=400:makeup=1.8[ducked]; \
 [ducked][vo]amix=inputs=2:duration=first:normalize=0[aout]" \
-map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k -shortest out.mp4
```

**Typical starting points for voiceover ducking:**
- `threshold=0.02–0.1` (lower = duck triggers on quieter voice)
- `ratio=5–12` (higher = deeper duck)
- `attack=10–100 ms` (longer = voice "pokes through" before duck engages)
- `release=300–1000 ms` (longer = smoother recovery, no pumping)
- Pro trick (from DAW practice): delay the **sidechain copy** slightly (`adelay`) or advance it so ducking starts a beat *before* the voice syllable — avoids the voice clipping the music's first transient.

**Pitfalls & fixes:**
- **Character-encoding error on filter labels.** Copy-pasted label text (e.g. `[final]`) can contain invisible Unicode; FFmpeg errors "No such filter". Fix: retype labels by hand, or omit the final label and let FFmpeg auto-map the single output.
- **amerge vs amix at the end.** `amerge` keeps channels separate (voice L/R + music L/R → 4 channels); use `amix` if you want a summed stereo. `amerge` always terminates on shortest input.
- **Pumping.** Attack too fast + release too short = audible "breathing" of the music bed. Raise release to 400–800 ms.
- **Duck never engages.** Sidechain voice too quiet → raise `level_sc` (e.g. `level_sc=4`) or lower `threshold`.
- **Sample-rate mismatch between inputs** silently resamples; normalize both to 48 kHz first with `aformat=sample_rates=48000` for predictable detection.

**Validation:**
- Re-run with `astats` on the ducked stem: confirm `RMS_peak` drops 8–15 dB when voice is active vs inactive.
- Visual: `-filter_complex "...[ducked]showwavespic=s=1280x240[v]" -map "[v]"` and inspect envelope.
- A/B loudness: `ebur128` momentary (M) trace should dip under voice segments.

---

### 1.2 `sidechaingate` — Dynamics / Sidechain (alternative)

Gate driven by a sidechain instead of self. Useful for harder on/off ducking (e.g., radio-style talk-over). Same parameter family as `sidechaincompress` plus `range` (default 0.06125, 0–1) — level of gain reduction when below threshold; setting `range=0` makes it a pure expander.

---

## 2. Loudness Normalization (`loudnorm`)

### 2.1 Filter overview — Loudness / EBU R128

Implements EBU R128 loudness normalization with integrated loudness (I), true peak (TP), and loudness range (LRA) targets.

**Parameters:**

| Param | Default | Range | Notes |
|---|---|---|---|
| `I` (integrated) | -24.0 LUFS | -70 – -5 | Target integrated loudness |
| `LRA` | 7.0 | 1 – 20 (some docs say 50) | Target loudness range |
| `TP` | -2.0 | -9 – +0 dBTP | Max true peak ceiling |
| `offset` | 0.0 | -99 – +99 | Gain applied before TP limiter |
| `linear` | false (dynamic) | bool | `true` = single linear gain (best quality) |
| `measured_I` / `measured_TP` / `measured_LRA` / `measured_thresh` | — | — | Feed-back values from pass 1 |
| `print_format` | `summary` | `summary` / `json` / `none` | JSON for machine parsing |
| `dual_mono` | false | bool | Treat dual-mono correctly (pan law -3.01 dB) |

**Platform targets (verified across multiple sources):**

| Platform / Context | I (LUFS) | TP (dBTP) | LRA (LU) |
|---|---|---|---|
| YouTube | -14 | -1.0 | 11 |
| Spotify / TikTok | -14 | -1.0 | 11 |
| Apple Podcasts / general podcasts | -16 | -1.0 to -1.5 | 11 |
| General "safe default" | -16 | -1.5 | 11 |
| EBU R128 broadcast | -23 | -1.0 | 7 |
| Loud music library | -12 | -1.0 | 14 |

### 2.2 One-pass vs two-pass — critical distinction

- **Single-pass (dynamic):** `ffmpeg -i in.mp4 -af loudnorm=I=-14:TP=-1.5:LRA=11 out.mp4`. Uses a look-ahead buffer and adjusts **dynamically moment-to-moment** — this is *dynamic compression*, and on music/dialogue it **pumps audibly**. Acceptable for live streaming; **do not use for VOD/files.**
- **Two-pass (linear):** Pass 1 measures, pass 2 applies one consistent gain with `linear=true`. Dynamics survive; this is the correct method for files. Measured difference vs single-pass is typically < 0.5 LU on I, but the *sound* is dramatically better.

**Pass 1 (measure — JSON goes to stderr):**

```bash
ffmpeg -hide_banner -i input.mp4 -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2> measure.log
```

Tail of `measure.log`:

```json
{
  "input_i" : "-27.61",
  "input_tp" : "-9.05",
  "input_lra" : "8.40",
  "input_thresh" : "-38.10",
  "output_i" : "-16.00",
  "output_tp" : "-1.50",
  "output_lra" : "11.00",
  "normalization_type" : "dynamic",
  "target_offset" : "0.49"
}
```

**Pass 2 (apply linear):**

```bash
ffmpeg -hide_banner -i input.mp4 \
 -af loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=-27.61:measured_TP=-9.05:measured_LRA=8.40:measured_thresh=-38.10:offset=0.49:linear=true \
 -c:v copy -c:a aac -b:a 192k -ar 48000 output.mp4
```

**Batch alternative:** `ffmpeg-normalize` (Python, `pip install ffmpeg-normalize`) wraps two-pass by default:

```bash
ffmpeg-normalize input.mp4 -nt ebu -t -14 -c:a aac -b:a 192k -ar 48000 -o output.mp4
ffmpeg-normalize *.mp4 -nt ebu -t -14 -ext mp4 -o normalized/
```

### 2.3 Pitfalls & fixes

- **192 kHz resample surprise.** `loudnorm` internally upsamples to 192 kHz for true-peak detection; if you don't pin `-ar 48000` (or 44100), the output may come out at 192 kHz. **Always set `-ar`.** For higher quality SRC use `aresample=resampler=soxr:out_sample_rate=48000:precision=28` (requires libsoxr build).
- **Short files (< 3 s) misbehave.** loudnorm uses overlapping 3 s windows; sub-3-second clips won't reach target. Fix: `apad,atrim=0:3` before loudnorm, then `atrim` back to original duration after.
- **Quiet file doesn't get louder in linear mode.** If required gain would push TP over the ceiling, linear normalization caps the gain (Output I lands above target). Fix: precede with compression (e.g. `acompressor` or `dynaudnorm`) to reduce crest, or accept dynamic mode.
- **Double-normalizing.** Running loudnorm on already-normalized audio further crushes dynamics. QC first: `ffmpeg -i in.mp4 -af loudnorm=print_format=summary -f null -` and skip if `input_i` is within ~0.5 LU of target.
- **Wrong target for platform.** -23 LUFS content uploaded to YouTube gets boosted ~9 LU and sounds unnatural; match the platform target instead (YouTube -14).
- **`offset` sign.** Use `target_offset` from pass-1 JSON as `offset` in pass 2; it compensates linear gain when the limiter engaged.

**Validation:**

```bash
ffmpeg -hide_banner -i output.mp4 -af ebur128 -f null - 2>&1 | tail -n 12
# Expect: Integrated loudness I: -14.0 LUFS (±0.5), True peak ≤ -1.0 dBTP
```

---

## 3. Audio Mixing: `amix`, `amerge`, `pan`, `volume` automation

### 3.1 `amix` — Mixing

Mixes N audio inputs into one output (sum). **Float samples only** — integer inputs get auto-`aresample` inserted.

| Param | Default | Notes |
|---|---|---|
| `inputs` | 2 | Number of input streams |
| `duration` | `longest` | `longest` / `shortest` / `first` |
| `dropout_transition` | 2 s | Renormalization ramp when an input ends |
| `weights` | 1 1 ... | Per-input weights, e.g. `weights="1 0.25"` |
| `normalize` | 1 (true) | **0 disables auto 1/N scaling** — critical, see pitfalls |

```bash
# Vocal full weight, music quarter weight, no auto-attenuation:
ffmpeg -i VOCALS -i MUSIC -filter_complex \
 "amix=inputs=2:duration=longest:dropout_transition=0:weights=\"1 0.25\":normalize=0" OUTPUT
```

**Pitfall (the #1 amix complaint):** by default amix scales each input by 1/N, so a 2-input mix comes out ~6 dB quieter than sources. Fix: `normalize=0` and control levels yourself with `volume` on each input, or use `weights`.

### 3.2 `amerge` — Channel merge

Merges streams into one multi-channel stream (no summing). Supports many sample formats (unlike amix). **Always terminates at shortest input.**

```bash
# Two mono files -> one stereo:
ffmpeg -i left.wav -i right.mp3 -filter_complex "[0:a][1:a]amerge=inputs=2" -ac 2 out.wav
```

### 3.3 `pan` — Channel routing / weighted mixing

Remaps and mixes channels with coefficients. More flexible than amix when you need exact level control, and supports many sample formats.

```bash
# Downmix-with-balance after amerge (2 stereo sources -> 1 stereo, music at 0.2):
[a0][a1]amerge,pan=stereo|c0<0.8*c0+0.2*c2|c1<0.8*c1+0.2*c3[out]

# 2.1 layout from 3 sources with explicit routing:
join=3:channel_layout=2.1:map='0.0-FR|1.0-LFE|2.0-FL'
```

**Pitfall:** spaces around the `|`/`;` separators in pan expressions are rejected in some shells — quote carefully.

### 3.4 `volume` — Gain & expression-driven automation

| Param | Default | Notes |
|---|---|---|
| `volume` | 1.0 | Linear (`0.5`), dB (`-6.0206dB`), or **expression** |
| `precision` | `float` | `fixed` / `float` / `double` |
| `eval` | `once` | `once` = evaluate at init; **`frame` = re-evaluate every frame** (enables automation) |
| `replaygain_noclip` | 1 | Prevent clipping on replaygain gain |

**Timeline support:** Full. Variables available in expressions: `t` (seconds), `n` (frame #), plus `enable='between(t,a,b)'` timeline gating (supported by volume, afade, and most filters — check `ffmpeg -filters` for the `T` flag).

**Expression ducking envelope (multi-segment automation without sidechain):**

```bash
ffmpeg -i in.wav -af "\
volume=enable='between(t,0,3)':volume='t/3.0':eval=frame,\
volume=enable='between(t,3,7)':volume='1':eval=frame,\
volume=enable='between(t,7,8)':volume='1-0.75*(t-7)':eval=frame,\
volume=enable='between(t,8,12)':volume='0.25':eval=frame,\
volume=enable='between(t,12,13)':volume='.25+0.75*(t-12)':eval=frame,\
volume=enable='between(t,15,18)':volume='1-(t-15)/3.0':eval=frame" out.wav
```

**Simple time-based fade-out via expression:**

```bash
volume='if(lt(t,10),1,max(1-(t-10)/5,0))':eval=frame
```

**Runtime command:** `volume` accepts a `volume` command at runtime (sendcmd/ZMQ) — usable for live automation in the MCP server.

### 3.5 `afade` / `acrossfade` — Fades

- `afade=t=in:st=5.5:d=0.5` / `afade=t=out:st=155:d=3` — time-based fades. `silence=` option sets the floor level instead of 0 (useful for duck-to-level effects).
- Fades always go to/from zero — for fade-to-25% tricks, combine `afade` with a scoped `volume` between two fades (see 3.4).
- `acrossfade=d=3:c1=tri:c2=tri` joins two audio files with crossfade curves (`exp`, `tri`, `qsin`, `esin`, `log`, etc.) — needed for music-bed looping and segment joins.

### 3.6 Pitfalls & fixes (mixing)

- **Levels drop after mix** → amix `normalize=0` + explicit `weights` or pre-`volume` per input.
- **Truncated output** → `amerge` always stops at shortest; `amix` defaults to longest. Use `apad` on short inputs or pick `duration=` deliberately.
- **Sync of overlays** → use `adelay=5000|5000` (per-channel ms) or input-level `-itsoffset 1.5 -i audio.mp3` to time-align music cues / stingers.
- **Background music looping under video:** `-stream_loop -1 -i music.mp3` + `-shortest`.
- **Avoid `pos`** in timeline expressions — deprecated.

---

## 4. TTS / Voice Sweetening Chain

Goal: make synthetic (or recorded) speech clear, present, de-essed, and consistent before mixing under video. Recommended chain order (each stage justified below):

```
highpass → (afftdn | anlmdn) → equalizer/anequalizer (presence) → deesser → acompressor/compand → alimiter → loudnorm (two-pass)
```

Filter order matters: clean noise before compression (or you compress the noise up), de-ess before final limiting, loudnorm last.

### 4.1 `highpass` / `lowpass` — Cleanup

- `highpass=f=80` (or `f=100` for thin TTS voices) removes rumble/handling/DC. Human speech fundamentals start ~85 Hz.
- `lowpass=f=8000`–`f=12000` trims hiss; TTS rarely has useful content above ~10 kHz.
- Poles: default 2 (12 dB/oct). `poles=1` for gentler slope.

### 4.2 Noise reduction: `afftdn` / `anlmdn` / `arnndn`

- `afftdn=nf=-25` — FFT denoiser, built-in, no model needed. Typical combo that tested well for speech-to-text prep: `highpass=f=80,afftdn=nf=-25,loudnorm,volume=2.0`. Beware: too aggressive (`nf=-30`+) eats consonants, "watery/muffled" artifacts.
- `anlmdn` — non-local means denoiser; good on stationary hiss.
- `arnndn=m=cb.rnnn` — RNN-based, best quality on speech, **but requires the .rnnn model file and a build with the filter enabled** — often missing in stock Windows builds. (Gap noted for deep research.)

### 4.3 Presence EQ: `equalizer` / `anequalizer` / `firequalizer`

Speech "presence/air" lives at 2–5 kHz; intelligibility consonants 3–6 kHz; boxiness 300–500 Hz.

```bash
# TTS presence sweetening:
equalizer=f=300:t=q:w=1:g=-2,equalizer=f=3000:t=q:w=2:g=3,equalizer=f=6000:t=q:w=2:g=1.5
```

`anequalizer` multi-band example (syntax: `c0 f=250 w=100 g=2 t=1|c0 f=700 w=500 g=-5 t=1|...` — per-channel, freq, width, gain dB, filter type).

### 4.4 `deesser` — Sibilance control

| Param | Default | Range | Notes |
|---|---|---|---|
| `i` (intensity) | 0 | 0 – 1 | Trigger intensity — **0 = off! Always set it** |
| `m` (amount) | 0.5 | 0 – 1 | Treble ducking depth |
| `f` | 0.5 | 0 – 1 | How much original freq content to keep |
| `s` | `o` | `i`/`o`/`e` | Output: input / de-essed / ess-only (use `e` to audition what's removed) |

```bash
# Moderate de-essing of TTS voice:
deesser=i=0.4:m=0.6:f=0.5
# Audition removed sibilance only:
deesser=i=0.4:m=0.6:s=e
```

**Pitfall:** `deesser=i=1` (max trigger) with default `m=0.5` is a common "it does nothing / it does too much" confusion — tune `i` first (0.2–0.5 typical for TTS, which is sibilant-heavy), then `m`.

### 4.5 `acompressor` / `compand` — Dynamics

`acompressor` (modern, per-param): `level_in`, `mode`, `threshold`, `ratio`, `attack`, `release`, `makeup`, `knee`, `link`, `detection`, `level_sc`, `mix` — same family as sidechaincompress (see §1.1 table).

Voice starting point:

```bash
acompressor=threshold=-20dB:ratio=3:attack=5:release=100:makeup=6dB
```

`compand` (legacy, points-based transfer function) — powerful for podcast/audiobook levelling:

```bash
# Boost quiet speech 3x, leave loud speech alone, kill noise floor:
compand=attacks=0:points=-80/-900|-45/-15|-27/-9|-5/-5|20/20:gain=5
```

Classic "noisy environment" preset (from FFmpeg docs): `compand=.3|.3:1|1:-90/-60|-60/-40|-40/-30|-20/-20:6:0:-90:0.2`

**Pitfall:** `attacks=0` means instantaneous (no averaging) — immediate clamping audible on yells. Use small non-zero attack (0.05–0.3 s) for natural sound.

### 4.6 `alimiter` — Safety ceiling

```bash
alimiter=limit=0.891:attack=5:release=50:level=false   # ≈ -1 dBFS brick wall
```

Place after compression, before loudnorm, to catch TTS peaks.

### 4.7 Full TTS sweetening command (ready for MCP tool)

```bash
ffmpeg -i tts_raw.wav -af "\
highpass=f=90,\
afftdn=nf=-25,\
equalizer=f=350:t=q:w=1:g=-2,equalizer=f=3200:t=q:w=2:g=3,\
deesser=i=0.35:m=0.55,\
acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=5dB,\
alimiter=limit=0.89:attack=5:release=60,\
loudnorm=I=-16:TP=-1.5:LRA=11" \
-ar 48000 tts_sweet.wav
```

(For production: replace the single-pass loudnorm tail with the two-pass flow from §2.2.)

**Validation:** compare `astats` before/after (RMS_level stability, Peak_level ≤ -1 dBFS), listen for lisp artifacts (deesser too deep) and pumping (compressor release too fast).

---

## 5. Audio Analysis & Automated QC

### 5.1 `ebur128` — Loudness scanner (the QC backbone)

Logs Momentary (M), Short-term (S), Integrated (I), LRA at 10 Hz; prints summary at end.

```bash
ffmpeg -nostats -i in.mp4 -filter:a ebur128=peak=true -f null -
```

- `peak=true` adds true-peak metering (sample / true / all).
- Injects metadata keys: `lavfi.r128.I`, `lavfi.r128.LRA`, `lavfi.r128.LRA.low/high`, `lavfi.r128.M`, `lavfi.r128.S` — parseable via `ametadata=print`.
- Also available as a **video meter** (`ebur128=video=1`) and `volumedetect` companion.

MCP use: run after every render; fail QC if |I − target| > 0.5 LU or true peak > -1 dBTP.

### 5.2 `volumedetect` — Quick mean/max

No parameters. 16-bit only (auto-converts). Prints `mean_volume` (RMS) and `max_volume` dB at end of stream. Fast pre-check before deciding whether normalization is needed.

```bash
ffmpeg -i in.wav -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"
```

### 5.3 `silencedetect` — Silence finder

| Param | Default | Notes |
|---|---|---|
| `noise, n` | -60 dB | Tolerance; `-50dB` typical for voice gaps, `-30dB` aggressive |
| `duration, d` | 2 s | Minimum silence length to report |
| `mono, m` | off | Per-channel detection |

```bash
ffmpeg -i in.wav -af silencedetect=noise=-50dB:d=0.5 -f null -
# stderr: silence_start: 12.34 / silence_end: 15.17 | silence_duration: 2.83
```

Export machine-readable:

```bash
ffmpeg -i in.mp4 -af "silencedetect=noise=-30dB:d=0.5,ametadata=mode=print:file=silence.txt" -f null -
```

MCP use cases: dead-air QC (fail if silence > N s inside content), auto-cut list generation, validating TTS gaps.

### 5.4 `silenceremove` — Silence trimming (companion action filter)

Key params: `start_periods`, `start_threshold`, `start_duration`, `start_silence`, `stop_periods` (**-1 = all periods**), `stop_duration`, `stop_threshold`, `stop_silence`, `window` (default 0.02 s), `detection` (`rms`/`peak`), `start_mode`/`stop_mode` (`any`/`all`).

```bash
# Remove ALL interior silences > 0.72 s below -50 dB (podcast tighten-up):
silenceremove=stop_periods=-1:stop_threshold=-50dB:stop_duration=0.72:window=0
# Keep max 0.5 s of each trimmed pause (natural pacing):
silenceremove=stop_periods=-1:stop_duration=1:stop_threshold=-45dB:stop_silence=0.5
```

**Pitfall:** with `window=0` (sample-accurate) boundaries match `silencedetect` exactly; with default windowing the cut points drift ~20 ms — detect and remove with the **same window/detection settings** for consistent results.

### 5.5 `astats` — Time-domain statistics

| Param | Default | Notes |
|---|---|---|
| `length` | 0.05 s | RMS peak/trough window [0–10] |
| `metadata` | off | Inject `lavfi.astats.*` frame metadata |
| `reset` | off | Recalculate every N frames |
| `measure_perchannel` / `measure_overall` | `all` | Flag-select which keys to compute |

Metadata keys (prefix `lavfi.astats.<ch#|Overall>.`): `DC_offset`, `Min_level`, `Max_level`, `Peak_level`, `RMS_level`, `RMS_peak`, `RMS_trough`, `Crest_factor`, `Flat_factor`, `Peak_count`, `Abs_Peak_count`, `Noise_floor`, `Noise_floor_count`, `Bit_depth`, `Dynamic_range`, `Zero_crossings(_rate)`, `Number_of_NaNs/Infs/denormals`, `Entropy`, `Min/Max/Mean/RMS_difference`.

**Per-frame RMS log (e.g. for ducking verification / waveform data):**

```bash
ffmpeg -i in.mp3 -af astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=log.txt -f null -
```

(Control granularity with `asetnsamples=44100` before astats for exact 1-second windows.)

**QC thresholds worth automating in MCP:**
- `Peak_level` > -1.0 dBFS → clipping risk (fail)
- `Flat_factor` high + `Peak_count` high → digital clipping (fail)
- `DC_offset` ≠ 0 → fix with `dcshift` or `highpass=f=10`
- `Crest_factor` < 4 → over-compressed
- `Dynamic_range` — DR ≥ 14 dynamic, DR 8–13 transitional, DR < 8 crushed (see also `drmeter`)

### 5.6 `dynaudnorm` — Alternative normalizer (single-pass, frame-windowed)

Adjusts gain per windowed frame (Gaussian smoothing). Key params: `framelen/f` (3–301, odd, default 31 — 31 frames ≈ 0.5 s at 60 fps audio frames... frame = 1/24 s by default), `gausssize/g` (odd, default 31), `peak/p` (default 0.95), `maxgain` (default 10), `targetrms/r`, `coupling/n`, `correctdc/c`, `altboundary/b`, `compress/s`, `threshold`.

```bash
ffmpeg -i in.mp4 -c:v copy -af dynaudnorm=f=150:g=13 out.mp4
```

**When to use which (consensus from sources):** `loudnorm` targets a standards LUFS level (use for delivery); `dynaudnorm` evens out levels moment-to-moment, sounds more "radio-processed", can pump (use for salvaging wildly uneven recordings, **before** loudnorm — not instead of).

---

## 6. Complex Filter Chains — Production Recipes

### 6.1 Podcast / talking-head video (voice-first)

Voice: clean → sweeten → compress → normalize. Music: bed at low level, sidechain-ducked, looped, faded at ends.

```bash
ffmpeg -i video.mp4 -i voice.wav -i music.mp3 -filter_complex "\
[1:a]highpass=f=90,afftdn=nf=-25,equalizer=f=3200:t=q:w=2:g=3,deesser=i=0.35:m=0.55,acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=5dB,asplit=2[vo][sc];\
[2:a]volume=0.35,afade=t=in:d=2,afade=t=out:st=58:d=2,apad[bed];\
[bed][sc]sidechaincompress=threshold=0.03:ratio=10:attack=30:release=500:makeup=1.6[ducked];\
[ducked][vo]amix=inputs=2:duration=first:normalize=0[mix];\
[mix]alimiter=limit=0.89,loudnorm=I=-16:TP=-1.5:LRA=11[aout]" \
-map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k -ar 48000 -t 60 out.mp4
```

### 6.2 Music video (music-first, occasional VO/stingers)

Music is primary: NO ducking by default; normalize music to platform target; stingers placed with `adelay`; brief ducks only under VO segments via expression volume or sidechain.

```bash
ffmpeg -i video.mp4 -i music.wav -i stinger.wav -i vo.wav -filter_complex "\
[3:a]asplit=2[vo][sc];\
[1:a][sc]sidechaincompress=threshold=0.05:ratio=6:attack=40:release=600[mus];\
[2:a]adelay=12000|12000,volume=0.8[stg];\
[mus][stg][vo]amix=inputs=3:duration=first:normalize=0:weights=\"1 0.8 1\"[mix];\
[mix]loudnorm=I=-14:TP=-1.0:LRA=11[aout]" \
-map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 256k -ar 48000 out.mp4
```

### 6.3 Documentary (multi-source: interview + nat sound + music)

Three stems with independent sweetening, interview drives ducking of BOTH nat sound and music:

```bash
ffmpeg -i interview.wav -i natsnd.wav -i music.wav -filter_complex "\
[0:a]highpass=f=80,afftdn=nf=-28,acompressor=threshold=-22dB:ratio=4:attack=4:release=150:makeup=6dB,asplit=2[int][sc];\
[1:a]volume=0.5[nat];[2:a]volume=0.4[bed];\
[nat][bed]amix=inputs=2:normalize=0[bg];\
[bg][sc]sidechaincompress=threshold=0.04:ratio=8:attack=60:release=700:makeup=1.7[bgd];\
[bgd][int]amix=inputs=2:normalize=0[mix];\
[mix]loudnorm=I=-16:TP=-1.5:LRA=11[aout]" \
-map "[aout]" -c:a pcm_s24le doc_master.wav
```

### 6.4 Chaining rules learned

1. **Order:** cleanup (HP/denoise) → tonal (EQ) → dynamics (de-ess, compress) → level (limit, normalize). Never denoise after compressing.
2. **loudnorm last** (it upsamples to 192 kHz internally), then `aresample=resampler=soxr:out_sample_rate=48000` and `-ar 48000` to pin output rate; `aformat` to pin channel layout/sample format before encoder; `apad` after everything if tail padding needed.
3. Use `asplit` liberally — one source feeding both a sidechain and the mix always needs an explicit split.
4. Prefer named labels `[like_this]`; invisible Unicode from copy-paste breaks graphs (retype by hand).
5. For MCP tool design: keep each stage a separate filter string segment and join with `,` / `;` programmatically — easier to toggle stages per-job.

---

## GAPS REQUIRING PERPLEXITY DEEP RESEARCH

1. **`arnndn` model availability & licensing.** Which `.rnnn` models ship with common Windows builds (gyan.dev, BtbN), where to download `cb.rnnn`/`bd.rnnn`/`sh.rnnn`, model file format, and quality comparison vs `afftdn` on TTS speech. Stock builds often lack it — need a definitive build/flag matrix.
2. **`deesser` internal algorithm details.** What detection band does it use (fixed? adaptive? split frequency)? Docs don't state the crossover — needed to predict interaction with `equalizer` presence boosts placed before it.
3. **`sidechaincompress` lookahead / latency compensation.** No documented way to make the duck engage *before* the trigger syllable (DAW-style negative delay on sidechain via `adelay` on the voice copy is community lore, not documented). Need verified recipes and any FFmpeg 7.x/8.x changes.
4. **`loudnorm` LRA behavior in dynamic mode.** Exactly how `LRA` target maps to the internal compressor settings when `linear=false`, and when/why `normalization_type` flips between `linear` and `dynamic` in pass-2 output. Edge cases where measured LRA < target LRA.
5. **`speechnorm` filter.** Appears in ffmpeg filter list (speech normalizer) but almost zero community usage data — parameters, quality vs `acompressor`+`loudnorm`, recommended settings for TTS.
6. **`dialoguenhance` real-world performance.** Docs say stereo→3.0 with enhanced center dialogue; no measured before/after data or guidance on downmixing the result back to stereo for web delivery.
7. **ZMQ/sendcmd runtime control for live automation.** Which audio filters accept runtime commands reliably (volume, sidechaincompress claim full command support), latency of command application, and a working `zmqsend`/`sendcmd` recipe for scheduled ducking in a single live encode.
8. **`mcompand` multiband sidechain use.** Can bands be independently sidechained (e.g., duck only music's 2–5 kHz under voice)? Filter docs imply per-band compand but sidechain routing within mcompand is undocumented.
9. **`whisper` filter (newer FFmpeg).** OpenAI Whisper transcription filter exists in recent FFmpeg — availability per version, model management, and JSON output format for driving silence/duck decisions from transcripts.
10. **Ducking quality benchmarks.** No published A/B measurements (LUFS dip depth, attack overshoot, THD) comparing `sidechaincompress` vs expression-`volume` ducking vs DAW-rendered reference. Needed to set MCP default presets with confidence.
11. **`loudnorm` + 5.1 / immersive layouts.** Confirmed issues around `dual_mono`, channel layout guessing, and whether per-channel normalization in 5.1 stays phase-coherent; guidance for MCP when input is 5.1 AC-3.
12. **`silenceremove` timestamp modes (`timestamp=copy|rewrite`)** — interaction with A/V sync when cutting silence from the audio track of a muxed video without cutting video (does `-vsync`/`-af apad` compensation hold sync, or must cuts be applied to both streams via select/aselect?).

---

## Source notes

Primary: ffmpeg.org/ffmpeg-filters.html (v8.x) — sidechaincompress, loudnorm, amix/amerge/pan, volume, afade, deesser, afftdn, ebur128, silencedetect, silenceremove, astats, dynaudnorm sections. Community: slhck/ffmpeg-normalize (GitHub), Gyan & Mulvya answers on Stack Overflow/Super User/Video Production SE, dev.to two-pass loudnorm guide, ffmpeg-micro.com normalization guides, r/ffmpeg threads, DSP StackExchange speech-enhancement pipeline, l-lin.github.io audio manipulation walkthrough. Where sources conflicted (e.g. loudnorm LRA range 20 vs 50, YouTube target -14 vs -16), the ffmpeg.org current-doc value was preferred and alternatives noted.
