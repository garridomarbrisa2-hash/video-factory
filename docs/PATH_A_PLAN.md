# Path A — Footage-Type Router with VO as Master Clock

**Version:** 2.2 (implemented and media-validated)
**Date:** 2026-07-30
**Status:** Implemented; mixed-route smoke validated
**Research basis:** `docs/VIDRUSH_ENGINE_RESEARCH.md`, `docs/REMOTION_REPLACEMENT_RESEARCH.md`, `docs/GLOBAL_STYLE_RESEARCH.md`, `docs/PRO_EDIT_STYLE.md`.
**Supersedes:** `docs/PATH_A_PLAN.md` v2.0.

> **Decision (locked):** Keep Remotion + FFmpeg + NVENC. Route each scene by explicit resolved asset provenance. Image and plate scenes render in Remotion. Real video footage is handled by FFmpeg with minimal editing: trim, scale, fixed per-style grade, and simple transitions. FFmpeg never renders text or motion graphics. Text on footage uses a transparent Remotion overlay composited by FFmpeg (Option A). VO is the program clock: synthesize and measure VO before searching or generating assets.

---

## 1. Renderer Contract

| Resolved asset kind | Renderer | Allowed work |
|---|---|---|
| `image` | Remotion | Full theme: typography, scene graphics, `still_motion`, grade, grain, vignette |
| `plate` | Remotion | Full theme over a static style plate; never treat a plate MP4 as footage |
| `video` | FFmpeg | Trim-to-fit, hard-cut multiple source clips, scale/normalize, fixed per-style grade |
| `video` with authored text | Remotion alpha overlay + FFmpeg | Remotion renders authored foreground typography/graphics only; FFmpeg composites it over clean footage |
| Final program | FFmpeg + NVENC | Boundary transitions, concat, audio mix, loudnorm, encode |

### Guardrails

1. Routing uses `resolved_asset_kind`, never file extension, `bg_video`, or container format.
2. FFmpeg never creates typography or motion graphics.
3. Remotion never trims, cuts, grades, or composites real footage.
4. FFmpeg footage transitions are true hard cuts or one simple xfade.
5. Option A covers authored foreground typography and scene-local graphics only. It does not include `SceneShell` grade wash, grain, vignette, media layers, archival effects, or cut leaks.
6. Routing remains purely asset-driven. VO duration controls asset quantity and trim targets, not renderer choice.
7. Initial router works per scene. Consecutive image-run grouping is deferred until profiling proves worthwhile and transition timing is tested.

---

## 2. Program Clock and Transition Math

VO-master timing works only if transition overlap is part of timeline math.

### 2.1 Clock rules

- Narrated scene target duration = measured `vo_duration + vo_tail` (`vo_tail` default 0.5s).
- Silent footage beats retain director-authored duration.
- **Hard cut = true concat with zero overlap.** Do not emulate a hard cut with a two-frame xfade.
- An xfade overlaps adjacent picture clips. Its duration must be represented in the program clock.
- `vo_start` values and final expected runtime derive from the same boundary table used by FFmpeg assembly.

### 2.2 Chosen transition timing policy: handles preserve scene starts

Render transition handles outside each scene's program interval:

- Each scene owns its full VO-aligned program duration.
- At an animated boundary, neighboring picture clips include enough visual handle material for the overlap.
- FFmpeg overlaps only handles, so authored scene starts, `vo_start`, and total program duration remain unchanged.
- Image scenes can extend still animation into handles.
- Video scenes request extra source media for handles. If unavailable, freeze/loop only handle frames; never shorten the program interval.

This policy keeps narration timing simple and prevents cumulative drift. If handles prove impractical for a specific source, downgrade that boundary to a hard cut rather than changing VO timing.

### 2.3 Required assertions

Before audio mix:

1. Compute expected final frames from scene program durations and transition policy.
2. Probe each routed scene clip and require duration within one frame of its target plus declared handles.
3. Probe assembled silent video and require duration within one frame of expected program duration.
4. Verify final VO endpoint does not exceed picture duration.

---

## 3. Pipeline Order

```text
brief → select style → skills chain (script + scene/asset intent; no fetch)
      → synthesize VO per scene
      → measure VO + word timings
      → retime scenes from measured VO
      → build boundary/handle table and recompute vo_start
      → search/select/generate assets using measured durations + handles
      → persist resolved timeline
      → route by resolved_asset_kind
          image/plate → Remotion scene clip
          video → FFmpeg trim/scale/grade scene clip
          authored text on video → Remotion alpha overlay → FFmpeg composite
      → assemble routed clips with true hard cuts / selected xfades
      → verify program duration
      → mix VO/music/SFX + loudnorm
      → NVENC final encode
```

### VO failure policy

- If any narrated scene lacks measured VO in normal VO-master mode, stop **before asset network requests**.
- Estimated timing is allowed only through an explicit caller choice such as `--skip-vo`; it must not silently masquerade as VO-master mode.
- `stage_retime_to_vo` is the single owner of scene retiming. `stage_vo` records audio, duration, and word timings but does not independently extend scene duration.

### Checkpoints

- Persist timeline after VO measurement/retiming.
- Persist again after asset resolution.
- Keep valid routed scene clips keyed by canonical render-input hash; do not delete them after every successful run.

---

## 4. Resolved Timeline Model

Authored intent and resolved render data must remain distinct. Do not infer resolved state from `props.bg_video`.

Minimum resolved fields:

```json
{
  "resolved_asset_kind": "image|video|plate",
  "resolved_segments": [
    {
      "path": "pipeline/assets/cache/stock/source.mp4",
      "source_start": 0.0,
      "target_duration": 5.0
    }
  ],
  "render_route": "remotion|ffmpeg",
  "needs_manual_asset": false
}
```

Rules:

- `image`: retain original still path. A looped MP4 derivative does not change its kind.
- `plate`: use a static color/image input and route through Remotion.
- `video`: `resolved_segments` contains ordered real-footage segments selected to cover scene program duration plus handles.
- `render_route` is derived from `resolved_asset_kind`; it is persisted for diagnostics, not authored by the director.
- Update `timeline_schema.json` to represent resolved fields already written by the pipeline (`vo_audio`, `vo_duration`, `vo_tail`, `word_times`, `total_sec`, `needs_manual_asset`) plus router fields. Prefer separate authored/resolved definitions if that remains a small diff.

---

## 5. Asset Resolution After VO

### 5.1 Image and plate scenes

- Fetch/generate one still. Duration does not affect source quantity.
- Remotion renders it for exact program duration plus required visual handles.
- Missing image becomes `resolved_asset_kind: "plate"`, sets `needs_manual_asset`, and still routes through Remotion.

### 5.2 Video scenes: fetch-to-cover, trim-to-fit

Use measured scene duration plus transition handles to calculate required footage coverage.

1. Search once and retain candidate metadata.
2. Probe or use trustworthy source duration metadata.
3. Select ordered clips until total usable coverage reaches target.
4. Trim each selected clip to assigned `target_duration`.
5. Hard-cut segments inside one scene output. Internal source changes are not scene transitions and do not alter VO timing.
6. If coverage remains short, use a second related clip first, then loop or freeze the final clip as fallback.
7. Never stretch below 0.8× speed. Default implementation performs no speed change.
8. Output one validated scene clip with exact target duration plus handles.

### 5.3 Availability preflight

`LOW_FOOTAGE_AVAILABILITY` uses the same retained search candidates consumed by resolution. It must not perform a second search. Availability means enough downloadable, decodable footage duration to cover the measured target, not merely a non-empty result list.

### 5.4 Error boundary

Expected per-scene failures (missing key, HTTP failure, download error, decode/probe failure, normalization failure) convert that scene to an image/plate fallback and set `needs_manual_asset`.

Final assembly, duration mismatch, corrupt audio, or mux failure are not scene fallbacks. Fail clearly to prevent silent data loss.

---

## 6. Duration-Safe Caching

Every derived media cache key includes:

```text
source content hash
+ source trim/start
+ target frames
+ fps and dimensions
+ renderer/filter/grade profile
+ codec/pixel-format profile when relevant
```

Before reuse, probe cached output and require duration/profile within tolerance. This applies to:

- normalized footage
- scene-level multi-clip outputs
- image/plate Remotion renders
- transparent overlays
- overlay composites
- transition-handle variants

No cache key may depend only on scene ID, URL, or filename.

---

## 7. FFmpeg Footage Path

### 7.1 Minimal editing only

- Trim selected segments.
- Normalize to 1920×1080 at timeline FPS.
- Preserve aspect ratio with crop/pad policy defined once.
- Apply one fixed FFmpeg grade filter string per canonical style.
- Hard-cut source segments inside a scene.
- Encode a validated scene clip.

### 7.2 Grade parity

- Define one boring filter chain per style; do not build a general CSS-to-FFmpeg grade compiler.
- Mark uncited values as `design_decision`.
- Compare a representative source frame through Remotion and FFmpeg for each style. Tune until boundaries do not show obvious grade jumps.

### 7.3 GPU wording and compatibility

- Initial path uses known-good **CPU filters + NVENC encode**.
- Do not claim overlay, xfade, crop, or grade are GPU-accelerated.
- Add CUDA filter graphs only after end-to-end hardware-frame compatibility passes on target FFmpeg build.
- Provide software encoder fallback when NVENC is unavailable; do not silently change quality settings.

---

## 8. Option A: Text on Video Footage

### Scope

Transparent Remotion output supports explicitly authored foreground elements:

- lower-thirds
- names and dates
- authored captions or callouts
- scene-local stat/quote typography proven to survive alpha mode

It does not automatically include shell-level grade, grain, vignette, cut leaks, foreground/midground media, or archival textures.

### Trigger

Do not infer overlay need from `vo_text`. Otherwise every footage scene becomes captioned. Overlay is triggered by explicit authored scene text/graphics fields.

If accessibility captions are later required, add timed caption cues derived from `word_times`; keep them separate from decorative scene text.

### Render/composite

1. Remotion renders ProRes 4444 (`.mov`, `codec: prores`, `proResProfile: '4444'`, PNG frames, alpha pixel format) for exact scene duration.
2. Probe output and require alpha-capable pixel format (`yuva444p*`); container alpha metadata alone is insufficient.
3. FFmpeg composites the overlay over clean graded footage with `overlay=0:0:shortest=1`.
4. Reject VP8/VP9 overlays when FFmpeg decodes them as opaque `yuv420p`, even if stream metadata reports `alpha_mode=1`; opaque black canvas will cover footage.
5. Validate representative lower-third, date, caption, and stat smoke cases before enabling Option A generally.

---

## 9. Boundary Transitions

- Preserve explicit director `transition_out` values.
- `hard` means real concat.
- Explicit `style`, `dissolve`, `dip`, and `whip` remain director-owned, but FFmpeg footage boundaries may downgrade unsupported complex choices to the style's simple xfade with a warning.
- The VidRush ~70/30 hard:animated target applies only where `transition_out` is absent. It never overrides authored intent.
- Selection is deterministic from timeline seed.
- Every animated boundary uses the handle policy in §2.2.

---

## 10. Audio

- Run audio assembly whenever **VO, music, or SFX** exists; VO is not required.
- Build audio graph with optional VO bus.
- Silent footage beats return music to bed level through compressor release. Do not call this a "swell" unless an explicit gain envelope is added.
- Audio placement uses the same program-clock boundary table as picture assembly.
- Keep `sidechaincompress` and two-pass `loudnorm` targets; VidRush's slider model is not an upgrade.

---

## 11. Implementation Sequence

| Order | Work | Exit check |
|---|---|---|
| 1 | Fix program clock: true hard concat, transition handles, expected-duration calculation | Mixed hard/xfade fixture stays within one frame; VO endpoints align |
| 2 | Add explicit resolved asset provenance and schema support | Image, video, and plate fixtures route correctly despite all having MP4 derivatives |
| 3 | Move VO measurement/retime before asset search; make failure explicit | Asset resolver receives measured durations; failed VO performs no network fetch |
| 4 | Fix duration-sensitive cache keys and validation | Changing VO duration cannot reuse stale media |
| 5 | Route per scene: image/plate → Remotion, video → FFmpeg | Mixed three-scene fixture renders exact duration |
| 6 | Add multi-clip video coverage and trim-to-fit | Short source clips fill one long VO scene without dead air |
| 7 | Add fixed per-style footage grades | Visual comparison shows no obvious boundary grade jump |
| 8 | Add Option A alpha overlays | ProRes 4444 `yuva444p*` smoke fixture preserves alpha, visible footage, and timing |
| 9 | Fix audio for VO/music/SFX combinations | Silent-only music fixture and mixed silent-beat fixture pass |
| 10 | Add retained scene cache/checkpoints | Interrupted render resumes without rerendering valid clips |
| 11 | Add archive source + shared availability preflight | History/crime fixture finds adequate public-domain coverage or cleanly falls back |
| 12 | Add 70/30 default transition budget | Explicit director transitions remain unchanged |
| 13 | Profile image-run grouping | Implement only if measured savings justify complexity |

---

## 12. Required Checks

Leave focused tests/checks for:

- VO-before-assets stage ordering
- VO failure stopping before asset requests
- `image|video|plate` routing
- duration-sensitive cache invalidation
- multi-clip coverage and fallback fill
- true hard concat duration
- mixed hard/xfade handle math
- `vo_start` and final VO endpoint alignment
- alpha overlay retention and composite duration
- alpha probe requires decoded `yuva444p*`, not only `alpha_mode` metadata
- footage-plus-overlay frame remains non-black during visual smoke check
- silent-only music/SFX
- expected final duration vs ffprobe within one frame
- explicit director transition preservation

Use pure unit tests for routing and duration calculations plus one small runnable FFmpeg/Remotion smoke fixture for media behavior.

---

## 13. Deferred Workstreams

### Public-domain/archive source

Add Wikimedia Commons + archive.org after router correctness. History/crime uses archive-first; other styles remain stock-first. Reuse existing cache/fallback contracts.

### Mini/Pro visual tier

Add only after router ships:

- `mini`: image/plate routes only
- `pro`: image + real video routes

### Script direction validator

Add `HYPER_SPECIFIC_VISUALS_IN_SCRIPT` for bracketed stage directions. Keep separate from renderer work.

### Theme grammar

Continue tuning Remotion theme grammar. Every value remains research-traced or marked `design_decision`.

---

## 14. Exit Criteria and Path B Trigger

Path A succeeds when:

- mixed image/video programs stay synchronized within one frame;
- video scenes skip Chrome and retain clean, style-compatible grade;
- authored text overlays preserve Remotion typography on footage;
- plate fallbacks remain full Remotion scenes;
- asset misses do not abort unrelated scenes;
- interrupted renders reuse valid scene outputs;
- history/crime footage availability improves after archive sourcing.

Revisit Path B (`docs/REMOTION_REPLACEMENT_RESEARCH.md`) only for a demonstrated requirement the router cannot meet: frame-accurate multitrack A/V editing, pitch-aware speed ramps, or complex real-footage compositing beyond a foreground alpha overlay.
