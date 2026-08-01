# Research Prompt: FFmpeg Audio Mastery for Professional Video Automation

## Role
You are an audio engineer and FFmpeg expert tasked with building a complete audio processing specification for an MCP (Model Context Protocol) server. The goal is to enable an LLM to produce broadcast-quality audio mixing, ducking, and sweetening purely through FFmpeg commands — no external DAW.

## Context
This is for a video automation factory where:
- LLM generates voiceover via TTS (needs consistent loudness, silence trimming)
- Background music must auto-duck under voiceover (radio-style sidechain compression)
- Sound effects need precise placement and layering
- Final output must meet platform loudness standards (YouTube: -14 LUFS, Spotify: -14 LUFS, broadcast: -23 LUFS)
- All processing must be automatable via FFmpeg filter_complex

---

## TASK 1 — Complete Audio Filter Audit

List EVERY FFmpeg audio filter with mixing, dynamics, spatial, or analytical potential. For each:
- Full parameter list with defaults and ranges
- Which parameters support timeline expressions (`enable`, `t`, `n`)
- Real-world use case in video production

Group by category:

### Mixing & Routing
- amix, amerge, pan, channelsplit, channelmap, join, anull

### Dynamics & Leveling
- volume, loudnorm, dynaudnorm, compand, sidechaincompress, sidechaingate, alimiter, acompressor, aexpand, agate

### Time & Pitch
- atempo, asetrate, atrim, adelay, aecho, aphaser, achorus, acompressor

### EQ & Tone
- equalizer, firequalizer, highshelf, lowshelf, bass, treble, tiltshelf, anequalizer

### Analysis & Visualization
- showwaves, showspectrum, avectorscope, showcqt, astats, aspectralstats, loudnorm (print_format), ebur128, volumedetect, silencedetect

### Effects & Spatial
- aecho, aphaser, achorus, aflanger, aresample, aformat, surround, headphone, stereo3d, crossfeed

### Noise & Restoration
- anlmdn, afftdn, arnndn, highpass, lowpass, bandpass, notch

### Synthesis & Generation
- anoisesrc, sine, aevalsrc, anoisesrc, flite (TTS)

---

## TASK 2 — Professional Audio Recipes

For EACH recipe below, provide:
- Complete FFmpeg command with explanation
- Parameter tuning guide (what to adjust for different content)
- Common pitfalls and fixes
- Quality validation method (what ffprobe/volumedetect output to check)

### Recipe A: Auto-Ducking (Sidechain Compression)
Voiceover automatically reduces music volume by 6-12dB when speaking.

Requirements:
- Use `sidechaincompress` with voiceover as key input
- Music should duck quickly (attack: 50-200ms) and release smoothly (500-1500ms)
- Must work with stereo music and mono voiceover
- Provide 3 intensity levels: subtle (podcast), moderate (YouTube), aggressive (broadcast)

### Recipe B: Loudness Normalization to Platform Standards
- YouTube: -14 LUFS integrated, -1 dBTP true peak
- Podcast: -16 LUFS integrated
- Broadcast: -23 LUFS integrated, -2 dBTP

Use `loudnorm` with `print_format=json` for measurement, then apply correction.
Two-pass vs one-pass tradeoffs.

### Recipe C: TTS Voice Sweetening
Make synthetic speech sound natural:
- High-pass filter to remove rumble (80-100Hz)
- Presence boost (2-5kHz, +2-4dB)
- De-esser (5-8kHz reduction, if sibilant)
- Light compression (2:1 ratio, -18dB threshold)
- Room tone addition (very low level noise to mask digital artifacts)

### Recipe D: Multi-Track Mixing
Combine voiceover, music, and 2-3 SFX with:
- Individual level control
- Panning (if stereo output)
- Crossfades between music segments
- Final master limiting

### Recipe E: Silence Detection & Removal
Auto-trim silence from TTS voiceover:
- `silencedetect` to find silence below threshold
- Generate edit list or use `silenceremove`
- Preserve natural pauses (don't remove <300ms gaps)

### Recipe F: Audio-Visual Sync Verification
Methods to verify audio matches video duration:
- `ffprobe` duration comparison
- Waveform overlay for visual QC
- Beat detection for music sync (`astats`, `ebur128` momentary)

---

## TASK 3 — Audio Analysis for LLM Decision-Making

Design ffprobe/ffmpeg analysis commands that output structured JSON for:

1. **Loudness profile** — integrated, short-term, momentary LUFS, true peak
2. **Silence map** — timestamps of all silences >500ms
3. **Spectral balance** — bass/mid/treble energy distribution
4. **Dynamic range** — crest factor, RMS variance
5. **Clipping detection** — samples at 0dBFS

Format as MCP tool responses an LLM can parse to make mixing decisions.

---

## TASK 4 — Audio Filter Chaining for Complex Scenarios

Show how to chain filters for:

1. **Podcast-style**: Voice → de-esser → compressor → EQ → loudnorm → limiter
2. **Music video**: Music → sidechain (key: voice) → EQ carve for voice → master limiter
3. **Documentary**: Multiple interview clips → individual leveling → crossfade → ambient bed → final loudnorm
4. **SFX design**: Layer 3 impacts + whoosh → EQ each layer → compress group → mix with music ducking

---

## TASK 5 — Platform-Specific Presets

Create preset parameter sets for:
- YouTube (stereo, 48kHz, -14 LUFS)
- TikTok/Reels (mono or stereo, 48kHz, aggressive loudness for mobile)
- Podcast (stereo, 44.1kHz, -16 LUFS, dynamic range preserved)
- Broadcast (stereo, 48kHz, -23 LUFS, strict true peak)

Include codec settings: AAC bitrate, sample rate, channel layout.

---

## TASK 6 — Gap Analysis

What audio tasks CANNOT be done in FFmpeg and require external tools?
- Multi-band compression with visual feedback
- De-reverb (limited)
- Pitch correction/formant shifting
- Advanced noise reduction (iZotope RX-level)
- Surround sound mixing beyond basic panning

For each gap, recommend: external tool, or acceptable workaround, or accept limitation.

---

## Final Output Format

Structured document with:
1. Filter catalog table (name, category, key params, animatable params)
2. Recipe library with commands and tuning guides
3. Analysis tool specifications (JSON output format)
4. Chaining diagrams for complex scenarios
5. Platform preset reference cards
6. Gap analysis with workarounds

Ready for direct conversion to MCP tool definitions and LLM prompt logic.
