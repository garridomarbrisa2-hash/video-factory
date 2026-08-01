# Phase 9: Generated-Asset Pipeline — Plan

**Date:** 2026-07-23 · **Status:** implemented; prompt-quality hardening validated · **Research:** `docs/API/modelscope.md` (API shape) + official model prompt guides + two sourced research reports (ModelScope image models; Pexels/Pixabay video APIs) synthesized below.

## Goal
Add a third asset route so the pipeline can **auto-generate stills** (and pull stock video more intelligently) instead of only flagging `needs_manual_asset`:

- **Images** → ModelScope inference API: **Z-Image** (default, photoreal/bilingual) or **Krea-2-Turbo** (stylized/concept) chosen by topic.
- **Video** → **Pexels** (primary, real footage) / **Pixabay** (backup + animation/abstract), with the API fixes the research surfaced.

## Asset routes (after this phase)

| Route | `asset_mode` | Image source | Video source | Use when |
|---|---|---|---|---|
| A stock | `stock` | — | Pexels → Pixabay | real B-roll exists |
| B generated | `generated` | user drops files in `assets/in/` | user drops clips | manual control (current) |
| **C auto-gen** | `auto` *(new)* | **ModelScope Z-Image / Krea-2-Turbo** | **Pexels → Pixabay** (or none → plate) | hands-off; API keys set |

Route C is opt-in. Misses still never abort (style plate fallback, Phase-8 P8 contract).

## Research synthesis (the "why")

### ModelScope image models — topic → model
| | **Z-Image** (`Tongyi-MAI/Z-Image`) | **Krea-2-Turbo** (`krea-community/Krea-2-Turbo`) |
|---|---|---|
| Strength | photoreal documentary, in-image text, **bilingual (EN+中文)** | aesthetic-first, stylized/illustrative/cinematic grain, anti-"AI-generic" |
| Prompt style | detailed, 80–250 words, structured | concise + style/palette/composition notes |
| Size (16:9) | **1536×864** (or 1280×720) | **1280×720** (multiple of 16) |
| Steps / guidance | 9 / 0.0 (Turbo behaviour) | 8 / 0.0 (CFG off) |
| Negative prompt | omit (Turbo ignores) | omit |
| LoRA | no (distilled) | yes (train-on-RAW → run-on-Turbo) |

**Rule:** default → **Z-Image @1536×864**. Route to **Krea-2-Turbo @1280×720** when the beat is stylized/concept/illustrative/cinematic-grain or wants a LoRA look. Any in-image text or Chinese brief → always Z-Image. Upscale to 1920×1080 in FFmpeg normalize.

### Prompt-quality contract (2026-07-30)

Testing exposed visible generated-image artifacts from using raw fallback/VO text as
an image prompt. Asset generation now owns a small, model-aware cleanup pass:

1. Director emits one frozen editorial moment: subject, pose/action, setting,
   framing, lighting, and only useful period/material/style details.
2. Pipeline appends a universal still constraint: one coherent 16:9 frame; no
   embedded text, logos, watermarks, UI, borders, split screen, or collage.
3. **Z-Image only:** send `negative_prompt` excluding layout/text artifacts. Its
   official README strongly recommends negative prompts for stronger control.
4. **Krea-2-Turbo:** send detailed natural-language positive prompt only. Its
   official guide says detailed prompts yield best results and does not document
   negative-prompt controls. Quote exact words only when text is intentionally
   required.
5. Prompt cleanup is part of generated-image cache key. Earlier artifact-prone
   cache results cannot be reused after this policy change.

Sources:

- Z-Image README: https://github.com/Tongyi-MAI/Z-Image
- Krea-2 prompting guide: https://github.com/krea-ai/krea-2/blob/main/docs/prompting.md

Ceiling: prompt constraints reduce layout/text artifacts but cannot guarantee
anatomy or factual accuracy. Add generated-image review/retry scoring only when
real runs show a repeatable failure class and approved quality signal exists.

**API (already in `docs/API/modelscope.md`):** async-only. `POST /v1/images/generations` (`X-ModelScope-Async-Mode: true`) → poll `GET /v1/tasks/{id}` (`X-ModelScope-Task-Type: image_generation`) every 5s until `SUCCEED` → download `output_images[0]`. Quota: ~2000 calls/day/user, 429 on over-limit → treat as miss (plate fallback).

### Stock video — corrections to current code
| Fix | Current | Correct |
|---|---|---|
| Pexels endpoint | `api.pexels.com/videos/search` (**deprecated**) | `api.pexels.com/v1/videos/search` + `size=medium` server pre-filter |
| Pixabay tier | "prefer large" → **downloads 4K** | prefer **`medium`** (usually exactly 1920×1080); `large` (4K) only if medium <1080p; read real `width`/`height` |
| Pixabay cache | none | **≥24h response cache (ToS requirement)** |
| Routing | source-pinned only | animation/abstract/loop keywords → **Pixabay `video_type=animation` first**; else Pexels first |
| Quality escalation | none | weak Pixabay set → retry `editors_choice=true` |
| Rate limits | none | honor `X-RateLimit-*` headers + 429 backoff |

**Order:** Pexels primary → Pixabay backup, except animation/abstract/background/loop keywords → Pixabay animation first. Both free, no attribution required (a "Videos provided by Pexels/Pixabay" credit is contractually requested).

## Work items
1. **W1** — Split `--skip-stock`: only skip the *stock search*; still run flatten + plate for local/generated/auto. (Fixes the footgun that hid the Phase-8 bug.)
2. **W2** — `pipeline/assets/imagegen.py`: ModelScope async client (submit/poll/download, SHA-cache), `choose_image_model(prompt, style/topic)`, per-model param dicts, LoRA passthrough, 429 → `ImageGenMiss`.
3. **W3** — `pipeline/assets/stock.py`: `/v1/` migration + `size=medium`; Pixabay medium-first tier + real-dimension check + 24h cache + `video_type=animation` routing + `editors_choice` escalation + rate-limit headers.
4. **W4** — orchestrator: `asset_mode: "auto"` route — image beats → imagegen (topic→model), video beats → stock (Pexels→Pixabay); on miss → plate. `generate` config block + `MODELSCOPE_API_KEY` env. `--skip-stock` split (W1).
5. **W5** — E2E test on worms timeline; docs (`AGENTS.md`, `docs/API/README` credit note); tracker update; commit.
6. **W6** — Prompt-quality hardening: model-aware still cleanup, Z-Image-only
   negative prompt, skill rules, and pure unit checks. **Complete 2026-07-30.**

## Env / config (keys never committed)
```
MODELSCOPE_API_KEY   # ModelScope token (ms-...)
PEXELS_API_KEY
PIXABAY_API_KEY
```
`pipeline.json` gains a `generate` block (model ids, sizes, steps, per-model default) mirroring the existing `stock` block.

## Attribution / ToS note
Pixabay ToS requires ≥24h caching of API responses (our SHA asset cache satisfies this) and prohibits mass scraping (we download per-scene only). Both providers request a source credit; surface "Videos provided by Pexels/Pixabay" + "Images via ModelScope" in the output metadata / credits.
