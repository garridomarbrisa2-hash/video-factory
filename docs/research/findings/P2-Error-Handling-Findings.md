# P2 — FFmpeg Error Handling, Validation & Debugging Findings
## Research Phase 2: Error Handling & Validation for Automated Video Processing
**Date:** 2026-07-21
**Method:** Tavily web searches (8 successful queries) + direct FFmpeg documentation + Wikipedia file-signature reference
**Status:** Complete (with gaps noted at end)

---

## 1. INPUT VALIDATION

### 1.1 ffprobe JSON Output — Primary Validation Tool

ffprobe is the canonical pre-flight validator. It reads container metadata without decoding the full stream, making it fast for automated pipelines.

**Automation commands:**

```bash
# Quick integrity check (exit code 0 = parseable, non-zero = error)
ffprobe -v error "input.mp4" && echo "OK" || echo "ERROR"

# Full structured probe → JSON for programmatic parsing
ffprobe -v quiet -print_format json -show_format -show_streams input.mp4

# Probe only specific fields (fast field extraction)
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,r_frame_rate,duration \
  -of json input.mp4

# Batch validation loop (bash)
for i in *.mp4; do
  ffprobe -v error "$i" 2>/dev/null && echo "OK => $i" || echo "ERROR => $i"
done
```

**Key JSON fields to validate in automation:**

| JSON path | Validates | Failure mode if absent/invalid |
|---|---|---|
| `streams[].codec_name` | Decoder available | `Decoder not found` |
| `streams[].codec_type` | Expected stream present | Missing video/audio stream |
| `streams[].width`/`height` | Sane resolution | 0×0 = broken header |
| `streams[].r_frame_rate` | Valid framerate | `0/0` or `1000/1` garbage |
| `format.duration` | Duration parseable | `N/A` = missing moov atom |
| `format.probe_score` | Detection confidence | Low score (<25) = unreliable |

**Detection method — JSON parse + field presence test.** If `format.duration` is missing or `N/A`, the file is likely truncated (classic: `moov atom not found`).

**Classification:** METADATA-CORRUPT (permanent, do not retry same file).

---

### 1.2 Magic Number / File Signature Verification

Check the first bytes before invoking FFmpeg at all — cheap pre-filter that catches misnamed/empty files.

| Container | Magic bytes (hex) | Offset | Text form |
|---|---|---|---|
| MP4/M4V/MOV | `66 74 79 70 69 73 6F 6D` | 4 | `ftypisom` |
| MP4 (MSNV) | `66 74 79 70 4D 53 4E 56` | 4 | `ftypMSNV` |
| 3GP/3G2 | `66 74 79 70 33 67` | 4 | `ftyp3g` |
| MKV/WebM | `1A 45 DF A3` | 0 | (EBML header) |
| AVI | `52 49 46 46 ?? ?? ?? ?? 41 56 49 20` | 0 | `RIFF????AVI ` |
| WAV | `52 49 46 46 ?? ?? ?? ?? 57 41 56 45` | 0 | `RIFF????WAVE` |
| MPEG-TS | `47` (repeats every 188 bytes) | 0, 188, 376… | sync byte `G` |
| MPEG-PS | `00 00 01 BA` | 0 | — |
| OGG | `4F 67 67 53` | 0 | `OggS` |
| FLAC | `66 4C 61 43` | 0 | `fLaC` |
| MP3 (no ID3) | `FF FB` / `FF F3` / `FF F2` | 0 | — |
| MP3 (ID3v2) | `49 44 33` | 0 | `ID3` |
| ASF/WMV/WMA | `30 26 B2 75 8E 66 CF 11 …` | 0 | (GUID) |

**Automation (PowerShell):**

```powershell
function Test-MagicBytes {
    param([string]$Path)
    $fs = [System.IO.File]::OpenRead($Path)
    $buf = New-Object byte[] 12
    $fs.Read($buf, 0, 12) | Out-Null
    $fs.Close()
    $hex = ($buf | ForEach-Object { $_.ToString("X2") }) -join ' '
    switch -Regex ($hex) {
        '1A 45 DF A3'          { return 'MKV/WEBM' }
        '52 49 46 46'          { return 'RIFF (AVI/WAV)' }
        '4F 67 67 53'          { return 'OGG' }
        '66 4C 61 43'          { return 'FLAC' }
        '^47'                  { return 'MPEG-TS' }
        '00 00 01 BA'          { return 'MPEG-PS' }
        'FF (FB|F3|F2)'        { return 'MP3' }
        '49 44 33'             { return 'MP3+ID3' }
    }
    # MP4: bytes 4-7 = 'ftyp'
    if ($hex.Substring(12,11) -match '66 74 79 70') { return 'MP4/ISOM' }
    return 'UNKNOWN'
}
```

**Classification:** FORMAT-MISMATCH (permanent — extension lies about content; re-probe with correct demuxer or reject).

---

### 1.3 Corruption Detection — Beyond Metadata

ffprobe alone only validates headers. Deep corruption inside the stream requires decode-based validation.

**Automation commands:**

```bash
# Aggressive error detection during decode (no output written)
ffmpeg -v error -err_detect explode -i input.mp4 -f null -

# Verify every frame decodes; count errors
ffmpeg -v error -xerror -i input.mp4 -f null - 2>decode_errors.log
#   -xerror = exit non-zero on ANY decode error

# CRC + bitstream compliance check
ffmpeg -err_detect crccheck+bitstream+buffer -i input.mp4 -f null -
```

**`-err_detect` flags (from ffprobe/ffmpeg docs):**

| Flag | Detects |
|---|---|
| `crccheck` | Embedded CRC mismatches |
| `bitstream` | Bitstream spec deviations |
| `buffer` | Improper bitstream length |
| `explode` | Abort on even minor errors (strictest) |
| `careful` / `compliant` / `aggressive` | Legacy gradations |

**Recovery strategy:** If `-xerror` fails, attempt salvage transcode with `-err_detect ignore` + `-fflags +discardcorrupt`, or re-request source. Tag file as DECODE-CORRUPT.

---

## 2. DRY-RUN & SYNTAX VALIDATION

### 2.1 The Null Muxer — Universal Dry-Run

```bash
# Full decode test without writing output (fastest validation)
ffmpeg -i input.mp4 -f null -

# Benchmark-style (reports wall time)
ffmpeg -benchmark -i input.mp4 -f null -

# Windows equivalent (use NUL or -)
ffmpeg -i input.mp4 -f null NUL
```

**Detection:** Exit 0 = stream fully decodable. Non-zero + stderr = decode path failure. `-` is preferred over `NUL`/`/dev/null` because it never touches the filesystem.

**Classification:** DECODE-VALIDATION — catches corrupt frames, unsupported codec params, timestamp errors before real encode.

---

### 2.2 Filter Graph Validation

Filter graphs are validated at parse time — errors appear *before* any frames are processed, making them safe to test cheaply.

```bash
# Validate a filtergraph with a 1-frame synthetic input
ffmpeg -f lavfi -i testsrc=duration=1:size=1920x1080:rate=1 \
  -vf "scale=1280:720,setsar=1" -f null -

# Visualize the parsed graph (ASCII)
ffmpeg -dumpgraph 1 -f lavfi -i "testsrc,split[L1],hflip[L2];[L1][L2]hstack" -f null -

# Graphviz dot-file representation (requires tools/graph2dot)
echo "nullsrc,scale=640:360,nullsink" | graph2dot -o graph.dot
```

**Common filter-graph parse errors:**

| stderr pattern | Cause | Class |
|---|---|---|
| `No such filter: 'xyz'` | Typo / filter not compiled in | CONFIG (permanent) |
| `Invalid filtergraph` | Syntax error (unbalanced `[`/`]`) | CONFIG |
| `Cannot find a matching stream for unlabeled input pad` | Missing link label | CONFIG |
| `Filter ... has an unconnected output` | Graph not terminated in sink | CONFIG |
| `Option 'x' not found` | Wrong parameter name | CONFIG |

**Recovery:** All filter-graph errors are PERMANENT/CONFIG — fix the command, do not retry.

---

### 2.3 Expression Parsing / Metadata Dry-Run

```bash
# Validate expressions in isolation with aevalsrc / testsrc
ffmpeg -f lavfi -i "aevalsrc='sin(440*2*PI*t)':d=0.1" -f null -

# idet interlace-flag audit (example from official docs)
ffmpeg -i INPUT -filter:v idet,metadata=mode=print -frames:v 360 -an -f null -
```

**Note from docs:** When a filter accepts runtime *commands* (e.g., `drawtext` re-init), "If the specified expression is not valid, it is kept at its current value" — runtime expression failures are NON-FATAL and only logged. Validate expressions at graph-parse time instead.

---

## 3. ERROR CODES & STDERR PATTERNS

### 3.1 Exit Codes (CLI)

Per FFmpeg devs (Carl Eugen Hoyos, ffmpeg-user 2013): **exit codes are not a reliable taxonomy.**

| Exit code | Meaning (observed, not contractual) |
|---|---|
| `0` | Success |
| `1` | Generic error (the vast majority of failures) |
| `123` | Signal caught (e.g., SIGINT) |
| `234` / `254` | Related to accumulated error count in some paths |
| `137` (128+9) | SIGKILL (OOM / external kill — common in containers) |

**Recommendation (mpegflow.com production guidance):** *"Inspect FFmpeg's exit + stderr before deciding whether to retry. Build a small classifier; have it return one of three buckets."* Do NOT branch on exit code alone.

---

### 3.2 Internal AVERROR Codes (library level)

From `libavutil/error.h` — useful when calling libav* APIs directly, and the basis for stderr strings:

| Code | FourCC | Meaning | Transient? |
|---|---|---|---|
| `AVERROR_INVALIDDATA` | `INDA` | Invalid data found when processing input | No (permanent) |
| `AVERROR_DECODER_NOT_FOUND` | `DEC` | Decoder not found | No (config) |
| `AVERROR_ENCODER_NOT_FOUND` | `ENC` | Encoder not found | No (config) |
| `AVERROR_DEMUXER_NOT_FOUND` | `DEM` | Demuxer not found | No (config) |
| `AVERROR_MUXER_NOT_FOUND` | `MUX` | Muxer not found | No (config) |
| `AVERROR_FILTER_NOT_FOUND` | `FIL` | Filter not found | No (config) |
| `AVERROR_PROTOCOL_NOT_FOUND` | `PRO` | Protocol not found | No (config) |
| `AVERROR_STREAM_NOT_FOUND` | `STR` | Stream not found | No |
| `AVERROR_OPTION_NOT_FOUND` | `OPT` | Option not found | No (config) |
| `AVERROR_EOF` | `EOF ` | End of file | Expected |
| `AVERROR_EXIT` | `EXIT` | Immediate exit requested | n/a |
| `AVERROR_EXTERNAL` | `EXT ` | External library error | Maybe |
| `AVERROR_PATCHWELCOME` | `PAWE` | Not implemented | No |
| `AVERROR_BUG` / `AVERROR_BUG2` | `BUG!`/`BUG ` | Internal bug | No (report) |
| `AVERROR_UNKNOWN` | `UNKN` | Unknown | Maybe |
| `AVERROR_HTTP_BAD_REQUEST` | `400` | HTTP 400 | No (request fix) |
| `AVERROR_HTTP_UNAUTHORIZED` | `401` | HTTP 401 | No (auth) |
| `AVERROR_HTTP_FORBIDDEN` | `403` | HTTP 403 | No (auth) |
| `AVERROR_HTTP_NOT_FOUND` | `404` | HTTP 404 | No |
| `AVERROR(ENOMEM)` | — | Out of memory | Maybe (retry smaller) |
| `AVERROR(EAGAIN)` | — | Try again | Yes |

---

### 3.3 stderr Pattern Taxonomy (Classifier for Automation)

Bucket stderr into three actionable classes (pattern → action):

**PERMANENT (fail-fast, do not retry):**

```
Invalid data found when processing input        → corrupt/unsupported input
moov atom not found                             → truncated MP4
Decoder not found / Encoder not found           → build/config issue
No such filter                                  → filtergraph typo
Unable to find a suitable output format         → bad extension/-f
Error opening input file: No such file or directory
Permission denied
Conversion failed!                              → catch-all after other errors
```

**TRANSIENT (retry with backoff):**

```
Connection timed out                            → network
Connection refused                              → network
Server returned 5XX                             → upstream
I/O error                                       → disk/network blip
Resource temporarily unavailable                → EAGAIN
```

**RESOURCE (retry with reduced parameters):**

```
Cannot allocate memory                          → reduce threads/resolution
No space left on device                         → clean disk, retry
Too many open files                             → ulimit
```

**NON-FATAL (log and continue — do NOT classify as failure):**

```
Past duration 0.X too large                     → timestamp jitter
invalid, clipping / invalid dropping st:N       → PTS/DTS repair (Frigate-style floods)
Non-monotonous DTS                              → timestamp warning
Deprecated pixel format used                    → cosmetic
```

---

## 4. RETRY STRATEGIES

### 4.1 Transient vs Permanent Decision Matrix

From mpegflow production guidance — *"inspect FFmpeg's exit + stderr before deciding whether to retry. Build a small classifier; have it return one of three buckets. Each bucket gets its own policy."*

| Bucket | Examples | Policy |
|---|---|---|
| **Deterministic-permanent** | Invalid data, missing codec, filter typo, bad option | Fail immediately; alert human; do NOT retry same args |
| **Transient** | Network timeout, 5xx, EAGAIN, I/O blip | Retry ≤3× with exponential backoff + jitter |
| **Resource** | OOM, disk full, threads | Retry once with reduced `-threads`, lower res, or after cleanup |

**Anti-patterns to avoid (mpegflow):**
- Shipping FFmpeg stderr line-by-line to centralized logs (high velocity, costly). **Buffer per job, flush as one artifact.**
- Blindly retrying any non-zero exit — burns worker time on deterministic failures.
- Not treating delivery (CDN purge) as part of the job — encode succeeds but client waits 30 min.

---

### 4.2 FFmpeg Built-In Reconnect Options (network inputs)

From `ffmpeg-protocols` docs — prefer these *before* shell-level retry:

```bash
ffmpeg -i "https://example.com/stream.m3u8" \
  -reconnect 1 \
  -reconnect_at_eof 1 \
  -reconnect_streamed 1 \
  -reconnect_on_network_error 1 \
  -reconnect_on_http_error 4xx,5xx \
  -reconnect_delay_max 30 \
  -reconnect_max_retries 5 \
  -reconnect_delay_total_max 120 \
  output.mp4
```

| Option | Effect |
|---|---|
| `reconnect` | Auto-reconnect when disconnected before EOF |
| `reconnect_at_eof` | Treat EOF as error (live streams) |
| `reconnect_on_network_error` | Reconnect on TCP/TLS connect errors |
| `reconnect_on_http_error` | CSV of HTTP codes or `4xx`/`5xx` to retry |
| `reconnect_streamed` | Reconnect even on non-seekable streams |
| `reconnect_delay_max` | Cap on per-retry delay (s) |
| `reconnect_max_retries` | Hard retry count |
| `reconnect_delay_total_max` | Total time budget (s) |

**Also:** `retry_errors` (default true) — transient read errors ignored and retried at cache layer.

---

### 4.3 Fallback Pipelines (External Orchestration)

```bash
# Pattern: systemd auto-restart with -timeout for clean failure (RTSP example)
ffmpeg -hide_banner -loglevel error \
  -timeout 1000000 \
  -use_wallclock_as_timestamps 1 \
  -rtsp_transport tcp \
  -i rtsp://cam/stream1 \
  -c copy -f segment -segment_time 30 -reset_timestamps 1 \
  out_%Y%m%d_%H%M%S.mkv
#   systemd: Restart=always, RestartSec=5, TimeoutSec=1s
```

**Fallback ladder pattern (automation):**

```
Attempt 1: ffmpeg -i in.mp4 -c:v libx264 -preset fast out.mp4
  ↓ exit≠0 + stderr classified as DECODE-CORRUPT
Attempt 2: ffmpeg -err_detect ignore -fflags +discardcorrupt -i in.mp4 …
  ↓ still failing
Attempt 3: ffmpeg -vsync drop -async 1 -i in.mp4 … (timestamp repair)
  ↓ still failing
REJECT: quarantine file, alert operator
```

---

## 5. QC AUTOMATION FILTERS

### 5.1 blackdetect — Black Frame Detection

```bash
# Detect black intervals ≥2s, strictest blackness threshold
ffmpeg -i input.mp4 -vf "blackdetect=d=2:pix_th=0.00" -an -f null -

# Looser (0.10 is default pixel-black threshold)
ffmpeg -i input.mp4 -vf "blackdetect=d=0.5:pix_th=0.10:pic_th=0.98" -an -f null -
```

**Parameters:**

| Param | Meaning | Default |
|---|---|---|
| `d` / `duration` | Min black duration to report (s) | 2.0 |
| `pix_th` / `pixel_black_th` | Luma threshold for "black" (scaled to range) | 0.10 |
| `pic_th` / `picture_black_ratio_th` | Fraction of frame that must be black | 0.98 |

**Output pattern (parse stderr):**
```
[blackdetect @ ...] black_start:660.927 black_end:661.194 black_duration:0.266933
```

**Threshold formula (docs):** `absolute_threshold = luma_minimum + pixel_black_th × luma_range_size` where range is [0–255] full, [16–235] limited.

**Also available:** `blackframe` filter (per-frame, exports `lavfi.blackframe.pblack` metadata, requires loglevel ≥ INFO).

**QC rule example:** FAIL if any `black_duration > 2.0` s (broadcast) or `> 5.0` s (web content).

---

### 5.2 freezedetect — Frozen Frame Detection

```bash
# Detect freezes ≥2s with -60dB noise floor
ffmpeg -i input.mp4 -vf "freezedetect=n=-60dB:d=2" -map 0:v:0 -f null -
```

**Parameters:**

| Param | Meaning | Default |
|---|---|---|
| `n` / `noise` | Noise tolerance (dB if suffixed, else ratio 0–1) | -60dB (0.001) |
| `d` / `duration` | Freeze duration until notification (s) | 2.0 |

**Metadata exported (parse via `metadata=mode=print` or stderr):**
- `lavfi.freezedetect.freeze_start`
- `lavfi.freezedetect.freeze_duration`
- `lavfi.freezedetect.freeze_end`

**Availability:** Since FFmpeg 4.2. Algorithm: mean absolute difference of all components vs noise floor.

**QC rule:** FAIL if `freeze_duration > 3.0` s (unless intentional still-frame content — whitelist via metadata).

---

### 5.3 silencedetect — Audio Silence Detection

```bash
# Detect silence below -30dB for ≥2s
ffmpeg -i input.mp4 -af "silencedetect=noise=-30dB:d=2" -vn -f null -

# Very strict broadcast check
ffmpeg -i input.mp4 -af "silencedetect=n=-50dB:d=0.5" -f null -
```

**Parameters:**

| Param | Meaning | Default |
|---|---|---|
| `n` / `noise` | Silence threshold (dB or amplitude) | -60dB |
| `d` / `duration` | Min silence duration to report (s) | 2.0 |

**stderr output pattern:**
```
[silencedetect @ ...] silence_start: 12.345
[silencedetect @ ...] silence_end: 15.678 | silence_duration: 3.333
```

**Metadata:** `lavfi.silencedetect.silence_start`, `silence_end`, `silence_duration`.

**QC rules:**
- FAIL if silence at head > 1.0 s (unpadded content expected)
- FAIL if total silence > 30% of duration
- FAIL if `silence_duration` spans entire file (dead audio track)

**Companion:** `volumedetect` for overall level sanity:
```bash
ffmpeg -i input.mp4 -af volumedetect -vn -f null -
# → mean_volume / max_volume (fail if max_volume = -91.0 dB = digital zero)
```

---

### 5.4 signalstats — Broadcast Legal Levels & Video Stats

```bash
# Extract per-frame YMIN/YMAX via ffprobe
ffprobe -f lavfi movie=input.mp4,signalstats \
  -show_entries frame_tags=lavfi.signalstats.YMAX,lavfi.signalstats.YMIN

# Full metric dump (tout+vrep+brng)
ffprobe -f lavfi movie=input.mp4,signalstats="stat=tout+vrep+brng" -show_frames

# Visual QC (highlight out-of-range pixels)
ffplay input.mp4 -vf signalstats="out=brng:color=red"
```

**Metadata keys logged per frame:** `YMIN`, `YLOW`, `YAVG`, `YHIGH`, `YMAX`, plus U/V equivalents, `SATMIN/AVG/MAX`, `HUEAVG/HUEMED`, `YDIF/UDIF/VDIF`, `YBITDEPTH`.

**Analysis flags (`stat=`):**

| Flag | Detects |
|---|---|
| `tout` | Temporal outliers (frame-to-frame Y plane jumps — tape dropouts) |
| `vrep` | Vertical line repetition (dropout concealment in digitized analog) |
| `brng` | Pixels outside broadcast legal range |

**QC rule (8-bit limited range):** FAIL if `YMIN < 16` or `YMAX > 235` on >0.1% of frames (brng). For full-range content adjust to 0–255.

**Repair (broadcast legalizer):**
```bash
ffmpeg -i in.mp4 -filter:v "lut,setparams=range=tv" -color_range:v tv out.mp4
# Or proper range conversion:
ffmpeg -i in.mp4 -filter:v \
  "scale=in_range=pc:out_range=tv:flags=bilinear+accurate_rnd+error_diffusion,format=yuv420p" \
  out.mp4
```

---

### 5.5 ebur128 & loudnorm — Loudness QC & Repair

**ebur128 (measurement only):**

```bash
# Measure integrated loudness (read summary at end)
ffmpeg -hide_banner -i input.mp4 -af ebur128 -f null - 2>&1 | tail -n 12

# With true peak
ffmpeg -i input.mp4 -af ebur128=peak=true -f null -
```

**Summary output to parse:**
```
Integrated loudness:
    I:         -16.0 LUFS
    Threshold: -26.3 LUFS
True peak:
    Peak:       -1.5 dBFS
```

**Two-pass loudnorm (the *correct* way for VOD):**

```bash
# Pass 1: measure → JSON on stderr
ffmpeg -i input.mp4 -af loudnorm=print_format=json -f null - 2> measure.log

# JSON tail to parse:
# {"input_i":"-27.61","input_tp":"-9.05","input_lra":"8.40","input_thresh":"-38.10",...}

# Pass 2: apply with measured values (linear=true avoids pumping)
ffmpeg -i input.mp4 -c:v copy \
  -af "loudnorm=I=-23:TP=-1:LRA=7:measured_I=-27.61:measured_TP=-9.05:measured_LRA=8.40:measured_thresh=-38.10:linear=true" \
  -ar 48000 output.mp4
```

**Targets by context:**

| Context | I (LUFS) | TP (dBTP) | LRA (LU) |
|---|---|---|---|
| EBU R128 broadcast | -23 | -1 | 7 |
| Streaming (Spotify/YouTube) | -14 | -1 | 11 |
| General/podcast | -16 | -1.5 | 11 |

**QC rule:** FAIL if measured `I` deviates from target by > ±0.5 LU after normalization. Verify with a *second* ebur128 pass on output.

**Warning (docs/community):** single-pass loudnorm ("dynamic") pumps — never use for VOD QC.

**Batch alternative:** `ffmpeg-normalize` wrapper (pip) — wraps two-pass by default:
```bash
ffmpeg-normalize input.mp4 -nt ebu -t -16 -c:a aac -b:a 192k -ar 48000 -o output.mp4
```

---

## 6. LOGGING & DEBUGGING

### 6.1 Log Levels

```bash
ffmpeg -v LEVEL …       # -v is synonym for -loglevel
```

| Level | Numeric | Shows |
|---|---|---|
| `quiet` | -8 | Nothing |
| `panic` | 0 | Fatal only |
| `fatal` | 8 | Fatal errors |
| `error` | 16 | All errors |
| `warning` | 24 | Warnings + errors |
| `info` | 32 | **Default.** Normal progress |
| `verbose` | 40 | More detail |
| `debug` | 48 | Everything incl. debug |
| `trace` | 56 | Max (huge output) |

**Prefix flags (combinable):** `repeat` (don't compress repeats), `level` (prefix each line with severity):
```bash
ffmpeg -loglevel repeat+level+verbose -i input output
```

---

### 6.2 The -report Flag & FFREPORT Environment Variable

```bash
# Simple: dump everything to ffmpeg-YYYYMMDD-HHMMSS.log (implies -loglevel debug)
ffmpeg -report -i input.mp4 output.mp4

# Controlled: custom filename + level via env var (RECOMMENDED for automation)
# Bash:
FFREPORT="file=out.log:level=32" ffmpeg -v verbose -i in.mp4 out.mp4

# Windows cmd:
cmd.exe /K set FFREPORT=file='C:\logs\job.log':level=32 && ffmpeg.exe -i in.mp4 out.mp4

# PowerShell:
$env:FFREPORT = "file=C:\logs\job.log:level=32"
ffmpeg -i in.mp4 out.mp4
Remove-Item Env:\FFREPORT
```

**FFREPORT keys:** `file` (supports `%p` program name, `%t` timestamp, `%%` literal), `level` (numeric).

**`-hide_banner`:** suppress version/config banner — combine with `-v error` for clean automation logs:
```bash
ffmpeg -hide_banner -v error -i in.mp4 out.mp4
```

---

### 6.3 Progress Output for Automation

```bash
# Machine-readable progress to stdout/file/pipe (key=value lines)
ffmpeg -i in.mp4 -progress /tmp/progress.log -nostats out.mp4
ffmpeg -i in.mp4 -progress pipe:1 -nostats out.mp4 | parse_progress

# Control stats update rate
ffmpeg -i in.mp4 -stats_period 0.5 out.mp4

# Structured stats file (legacy, per-frame)
ffmpeg -i in.mp4 -vstats_file stats.txt out.mp4
```

**`-progress` keys emitted:** `frame`, `fps`, `stream_0_0_q`, `bitrate`, `total_size`, `out_time_us`, `out_time_ms`, `out_time`, `dup_frames`, `drop_frames`, `speed`, `progress` (`continue`/`end`).

**Hang detection:** monitor `out_time_us` — if it hasn't advanced in N seconds while process alive, kill and classify HUNG.

---

## 7. HANG DETECTION & TIMEOUT HANDLING

### 7.1 The -timeout Option (Input-side)

**Unit: microseconds.** Applies to network protocols (RTSP, HTTP, TCP).

```bash
# 1 second timeout (RTSP camera example from production)
ffmpeg -timeout 1000000 -rtsp_transport tcp -i rtsp://cam/stream -c copy out.mkv

# 10 second timeout (more typical)
ffmpeg -timeout 10000000 -i https://example.com/video.mp4 out.mp4
```

**Behavior:** When timeout fires, FFmpeg terminates *gracefully* — closes output file properly (critical for valid MP4s). From production example: "when camera disappears ffmpeg will terminate gracefully after one second (it will stop recording and close the file)."

**Note:** `-timeout` is input-protocol-specific. For HTTP also see `-timeout` on the protocol; for RTSP it sets both TCP and UDP timeout.

---

### 7.2 External Timeout Wrappers (Process-level)

```bash
# Linux: hard kill after 5 minutes
timeout 300 ffmpeg -i in.mp4 out.mp4
timeout -k 10 300 ffmpeg -i in.mp4 out.mp4   # SIGTERM then SIGKILL after 10s grace

# PowerShell: job-based timeout
$job = Start-Job { ffmpeg -i $using:in -c:v libx264 $using:out }
if (Wait-Job $job -Timeout 300) { Receive-Job $job } else { Stop-Job $job; Remove-Job $job; throw "TIMEOUT" }
```

**Exit code on `timeout` kill:** 124 (GNU timeout convention) — distinguishable from FFmpeg's own failures.

---

### 7.3 Progress-Stall Hang Detection (Recommended Pattern)

```python
# Pseudocode — robust hang detector
import subprocess, time, re

proc = subprocess.Popen(
    ['ffmpeg', '-i', src, '-progress', 'pipe:1', '-nostats', dst],
    stdout=subprocess.PIPE, text=True)

last_time_us = 0
last_change = time.time()
STALL_LIMIT = 30  # seconds

for line in proc.stdout:
    m = re.match(r'out_time_us=(\d+)', line)
    if m:
        t = int(m.group(1))
        if t != last_time_us:
            last_time_us = t
            last_change = time.time()
    if time.time() - last_change > STALL_LIMIT:
        proc.kill()
        raise HungProcessError("no progress in 30s")
    if 'progress=end' in line:
        break
```

**Rationale:** FFmpeg can legitimately pause output during buffering — `out_time_us` (media time processed) is the ground truth of forward progress, not wall-clock CPU.

---

## 8. CONSOLIDATED AUTOMATION SNIPPET — Pre-Flight Validation Gate

```bash
#!/usr/bin/env bash
# validate_input.sh — gate before any processing
set -u
FILE="$1"

# Gate 1: existence + non-empty
[ -s "$FILE" ] || { echo "FAIL: missing/empty"; exit 1; }

# Gate 2: magic bytes (bash version — extend as needed)
head -c 4 "$FILE" | grep -qE $'^\x1aE\xdf\xa3|ftyp|RIFF|OggS|fLaC' \
  || echo "WARN: unrecognized magic"

# Gate 3: ffprobe header parse
JSON=$(ffprobe -v error -print_format json -show_format -show_streams "$FILE" 2>&1) \
  || { echo "FAIL: ffprobe: $JSON"; exit 2; }

# Gate 4: required fields present
echo "$JSON" | grep -q '"codec_type": "video"' || { echo "FAIL: no video stream"; exit 3; }
echo "$JSON" | grep -q '"duration"'            || { echo "FAIL: no duration (truncated?)"; exit 3; }

# Gate 5: full decode dry-run (strict)
ffmpeg -v error -xerror -i "$FILE" -f null - 2>decode_err.log \
  || { echo "FAIL: decode errors (see decode_err.log)"; exit 4; }

echo "PASS: $FILE"
exit 0
```

---

## GAPS REQUIRING PERPLEXITY DEEP RESEARCH

The following areas were **not sufficiently covered** by Tavily searches (rate limit hit on final 2 queries; some topics underrepresented in results) and warrant Perplexity deep research:

1. **Exact `-timeout` option semantics per protocol** — Tavily confirmed RTSP usage and µs units, but the behavior matrix across HTTP/HTTPS/RTMP/SRT/RIST (which protocols honor it, which use `rw_timeout` instead, interaction with `-listen`) needs authoritative confirmation from current ffmpeg-protocols docs.

2. **`-xerror` vs `-err_detect explode` exit-code guarantees** — whether `-xerror` produces a *distinguishable* exit code from generic failure, and its interaction with `-v error` (does the stderr still carry the specific error?). Production-grade classifier needs this.

3. **`rw_timeout` vs `-timeout` vs `-stimeout` deprecation history** — RTSP's `-stimeout` was deprecated in favor of `-timeout`; exact version cutover and behavioral differences for socket-level vs application-level timeout need version-specific research.

4. **Freezedetect false-positive tuning on intentional stills** — no data found on recommended `n=` thresholds for slideshow/lecture content vs broadcast; community tuning data needed.

5. **signalstats broadcast-legal thresholds for 10-bit HDR (PQ/HLG)** — all found examples assume 8-bit SDR limited range; 10-bit legal values (Y: 64–940) and HDR-specific QC rules (MaxCLL/MaxFALL validation against container metadata) were not covered by any search result.

6. **ebur128 momentary/short-term loudness QC windows** — searches covered integrated loudness and loudnorm well, but automated gating on M (400ms) and S (3s) window peaks (e.g., "fail if M > -16 LUFS for >5% of runtime") needs patterns not found in results.

7. **Windows-specific FFmpeg hang behavior** — job objects vs `timeout` equivalents, `WaitForSingleObject` patterns, and known cases where FFmpeg on Windows ignores console Ctrl+C during network stalls (documented FFmpeg trac tickets) were not surfaced.

8. **stderr format stability guarantees across versions** — the classifier regexes in §3.3 depend on English stderr strings; whether FFmpeg considers these strings a stable interface (and known rewordings between 5.x/6.x/7.x) needs trac/changelog research.

9. **`-progress` vs `-vstats_file` vs `-stats_period` completeness matrix** — which fields each emits, and whether `pipe:2` (stderr progress) differs from `pipe:1`, needs a controlled comparison not found in sources.

10. **Hardware-accelerated decode error patterns** (NVENC/QSV/AMF-specific stderr signatures and whether `-xerror` propagates HW errors identically) — zero coverage in search results.

---

*End of P2 findings.*
