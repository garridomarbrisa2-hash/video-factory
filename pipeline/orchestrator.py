"""
End-to-end video pipeline orchestrator.

Usage:
  python -m pipeline.orchestrator --timeline path/to/timeline.json
  python -m pipeline.orchestrator --timeline path/to/timeline.json --skip-vo --skip-stock
  python -m pipeline.orchestrator --brief "The rise and fall of Theranos"
  python -m pipeline.orchestrator --brief "..." --style crime

Styles:
  global_style (crime|history|modern|minimalist|standard) drives palette,
  transitions, grade, and motion via the style JSONs. Legacy edit_style
  names resolve through the alias map. --style always overrides.

Stages:
  1. Load + validate timeline.json
  2. Resolve B-roll (stock / local / manual)
  3. Synthesize VO (user-configured custom TTS)
  4. Build Remotion batch manifest
  5. Render scenes (node remotion/src/render.js --batch)
  6. Mix audio + loudnorm (if VO present)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from pipeline import ensure_dir, load_json, project_path
from pipeline.assets.stock import StockMissError, resolve_broll, resolve_broll_segments
from pipeline.assets.vo import probe_duration
from pipeline.intelligence.select_style import (
    load_style,
    normalize_style_id,
    select_style,
)


def validate_timeline(timeline: dict[str, Any]) -> None:
    if not timeline.get("title"):
        raise ValueError("timeline.title required")
    scenes = timeline.get("scenes")
    if not scenes or not isinstance(scenes, list):
        raise ValueError("timeline.scenes must be a non-empty list")
    for i, s in enumerate(scenes):
        if "type" not in s or "duration" not in s or "props" not in s:
            raise ValueError(f"scene[{i}] missing type/duration/props")
        props = s["props"]
        if s["type"] != "comparison":
            if not props.get("bg_image") and not props.get("bg_video"):
                # Will be filled by stock resolve if broll present
                if not s.get("broll"):
                    raise ValueError(
                        f"scene[{i}] ({s['type']}) needs bg_image/bg_video or broll"
                    )


def validate_style_consistency(timeline: dict[str, Any]) -> list[str]:
    """Remotion transition rule 1 equivalent: a scene must outlast the
    transitions on both sides. Warns (never blocks) so short scenes can be
    fixed upstream in the skills chain."""
    style_id = normalize_style_id(
        timeline.get("global_style") or timeline.get("edit_style")
    ) or "standard"
    style = load_style(style_id)
    transition_sec = style["motion"]["transition"]["frames"] / 30.0
    min_scene = transition_sec * 2
    warnings: list[str] = []
    for s in timeline["scenes"]:
        dur = float(s.get("duration", 0))
        if dur < min_scene:
            warnings.append(
                f"scene[{s.get('id')}] ({s['type']}) duration {dur:.2f}s < "
                f"2x transition ({min_scene:.2f}s) for style '{style_id}'"
            )
    warnings.extend(validate_reading_time(timeline))
    warnings.extend(validate_shake_rarity(timeline))
    warnings.extend(validate_signature_rarity(timeline))
    warnings.extend(validate_transition_rarity(timeline))
    warnings.extend(validate_camera_variety(timeline))
    warnings.extend(validate_sfx_rarity(timeline))
    warnings.extend(validate_still_motion(timeline))
    warnings.extend(validate_long_stills(timeline))
    warnings.extend(validate_footage_beats(timeline))
    return warnings


def validate_long_stills(timeline: dict[str, Any]) -> list[str]:
    """Warn when a resolved still carries a long beat without visual layering."""
    warnings: list[str] = []
    for scene in timeline["scenes"]:
        if scene.get("resolved_asset_kind") not in ("image", "plate"):
            continue
        props = scene.get("props", {})
        duration = float(scene.get("vo_duration") or props.get("vo_duration") or scene.get("duration", 0))
        layered = (
            props.get("midground")
            or props.get("foreground")
            or props.get("asset_sequence")
            or scene.get("asset_sequence")
            or (scene.get("type") == "comparison" and (
                (props.get("left_image") and props.get("right_image"))
                or (props.get("left_prompt") and props.get("right_prompt"))
            ))
        )
        if duration > 12 and not layered:
            warnings.append(
                f"scene[{scene.get('id')}] resolved {scene['resolved_asset_kind']} holds {duration:.2f}s "
                "without midground, foreground, or asset_sequence"
            )
    return warnings


def validate_still_motion(timeline: dict[str, Any]) -> list[str]:
    """No frozen stills (Ep1 pilot bug): a scene backed by a still image must
    MOVE — smoothly and deliberately, never with jittery drift/shake (the user
    rejected background drift). The director picks `still_motion`:
      push | pan | parallax | light | hold
    Absent still_motion, the renderer defaults a still to a visible eased 'push',
    so a still is never truly frozen. This validator only fires on an explicit
    'hold' with no justification — a locked frame is a choice that must be earned
    (a document/map artifact being read), not a gap. Video bgs always move."""
    warnings: list[str] = []
    ARTIFACT_TYPES = {"document", "map", "crime-board"}
    for s in timeline["scenes"]:
        props = s.get("props", {})
        # Only still-image backgrounds can freeze; video moves by definition.
        if props.get("bg_video"):
            continue
        if not (props.get("bg_image") or s.get("broll")):
            continue  # nothing resolved yet — resolve stage handles it
        sm = (s.get("still_motion") or props.get("still_motion") or "").lower()
        if sm == "hold" and s.get("type") not in ARTIFACT_TYPES:
            warnings.append(
                f"scene[{s.get('id')}] ({s['type']}) uses still_motion 'hold' on a "
                "non-artifact scene — a locked still reads frozen. Use 'push'/'pan'/"
                "'parallax'/'light', or reserve 'hold' for a document/map being read."
            )
    return warnings


def validate_sfx_rarity(timeline: dict[str, Any]) -> list[str]:
    """SFX is seasoning, not a bed (Phase 8, P6). A sound effect earns its place
    only when it serves the beat (a document rustle, an impact hit); sprinkled on
    every scene it reads as a template. Warns only — the director fixes upstream.

    Rule: more than 2 SFX in a video, or the same SFX on adjacent scenes, reads
    as decoration."""
    warnings: list[str] = []
    scenes = timeline["scenes"]
    sfx_idx = [i for i, s in enumerate(scenes) if s.get("sfx")]
    if len(sfx_idx) > 2:
        warnings.append(
            f"{len(sfx_idx)} SFX cues (scenes {[scenes[i].get('id') for i in sfx_idx]}) — "
            "cap ~2 per video. A sound on every beat is decoration, not punctuation."
        )
    for a, b in zip(sfx_idx, sfx_idx[1:]):
        if b == a + 1 and scenes[a].get("sfx") == scenes[b].get("sfx"):
            warnings.append(
                f"scenes {scenes[a].get('id')} and {scenes[b].get('id')} repeat sfx "
                f"'{scenes[a].get('sfx')}' back-to-back — vary it or drop one."
            )
    return warnings


def validate_camera_variety(timeline: dict[str, Any]) -> list[str]:
    """Camera intent grammar (Phase 8, P3): the move serves the beat, so three
    identical camera moves in a row reads as a template, not direction. The
    effective move is resolved the same way SceneShell does:
      photo_move (explicit) > energy-derived (low=none, mid/high=in) > scene-type
      default. Warns only — the director varies push/pan/hold upstream.
    """
    warnings: list[str] = []
    scenes = timeline["scenes"]

    def effective_move(s: dict[str, Any]) -> str:
        if s.get("photo_move"):
            return str(s["photo_move"])
        e = s.get("energy")
        if e == "low":
            return "none"
        if e in ("mid", "high"):
            return "in"
        # No intent expressed — the scene-type default applies; not the
        # director's call, so we don't police it. Treat as unknown (skip).
        return "?"

    moves = [effective_move(s) for s in scenes]
    run = 1
    for i in range(1, len(moves)):
        cur, prev = moves[i], moves[i - 1]
        if cur != "?" and cur == prev:
            run += 1
            if run == 3:
                warnings.append(
                    f"scenes {scenes[i-2].get('id')},{scenes[i-1].get('id')},{scenes[i].get('id')} "
                    f"all use camera move '{cur}' — three identical moves in a row reads "
                    "as a template. Vary push-in / pan / hold across consecutive beats."
                )
        else:
            run = 1
    return warnings


def validate_transition_rarity(timeline: dict[str, Any]) -> list[str]:
    """Act-aware transitions are the director's ONE signature move per video
    (Phase 8, P2). 95% of cuts stay the style default; a non-default cut
    (whip/dip/dissolve) marks an act break and must stay rare or it reads as a
    template. Warns only — the director fixes upstream.

    Rules (docs/plans/PHASE_8_DIRECTOR_AUTHORITY.md §P2):
      - any non-default transition type appearing >1× reads as a template;
      - non-hard/non-default cuts should not exceed ~15% of all cuts.
    """
    warnings: list[str] = []
    scenes = timeline["scenes"]
    # transition_out on scene i governs cut i→i+1; the last scene has no out-cut.
    intents = [
        (s.get("id"), (s.get("transition_out") or "style").lower())
        for s in scenes[:-1]
    ]
    cuts = [t for _, t in intents]
    n_cuts = len(cuts)
    if n_cuts == 0:
        return warnings

    non_default = [(sid, t) for sid, t in intents if t not in ("style", "hard")]
    # Per-type rarity: each signature type at most once.
    by_type: dict[str, list[Any]] = {}
    for sid, t in non_default:
        by_type.setdefault(t, []).append(sid)
    for t, ids in by_type.items():
        if len(ids) > 1:
            warnings.append(
                f"transition '{t}' on {len(ids)} cuts (scenes {ids}) — one signature "
                f"move per video; a second {t} reads as a template, not an act break."
            )
    # Overall share of non-default cuts. On short videos a single act-break is
    # legitimately a large fraction (1/4 = 25%), so the ~15% budget only bites
    # once it's meaningful — i.e. when 15% of the cuts is at least two cuts.
    if len(non_default) >= 2 and len(non_default) / n_cuts > 0.15:
        warnings.append(
            f"{len(non_default)}/{n_cuts} non-default transitions "
            f"({100.0 * len(non_default) / n_cuts:.0f}%) — over the ~15% act-break "
            "budget; most cuts should be the style default."
        )
    # A non-default transition without a justification note is an unexplained cut.
    for s in scenes[:-1]:
        t = (s.get("transition_out") or "style").lower()
        if t not in ("style", "hard") and not (s.get("transition_note") or "").strip():
            warnings.append(
                f"scene {s.get('id')} uses transition '{t}' with no transition_note — "
                "every act-break cut needs its one-line 'because ___'."
            )
    return warnings


def validate_signature_rarity(timeline: dict[str, Any]) -> list[str]:
    """Signature moves are the genre's ONE recognizable move — rare by definition
    (Phase 8, P5). A glitch/crime-board/whip used more than once reads as a
    template, not a signature. Warns only."""
    warnings: list[str] = []
    scenes = timeline["scenes"]
    glitch = [s.get("id") for s in scenes if (s.get("signature") or {}).get("glitch_at") is not None]
    boards = [s.get("id") for s in scenes if s.get("type") == "crime-board"]
    archival = [s.get("id") for s in scenes if (s.get("signature") or {}).get("archival")]
    if len(glitch) > 1:
        warnings.append(f"glitch signature on {len(glitch)} scenes {glitch} — one per video, at the twist.")
    if len(boards) > 1:
        warnings.append(f"crime-board on {len(boards)} scenes {boards} — one evidence wall per video.")
    if len(archival) > 2:
        warnings.append(f"archival pulse on {len(archival)} scenes {archival} — era overlay loses meaning past ~2 uses.")
    return warnings


def validate_shake_rarity(timeline: dict[str, Any]) -> list[str]:
    """Impact shake is a punctuation mark, not a texture (Phase 8, P4).

    Rules (docs/EDITING_DECISIONS.md + skills/02_director.md §6):
      - most videos have ZERO shake scenes;
      - never two adjacent shake scenes;
      - never shake a quiet/low-energy beat;
      - cap: ~1 shake scene per 60s of video.
    Warns only — the director fixes upstream."""
    warnings: list[str] = []
    scenes = timeline["scenes"]
    total = sum(float(s.get("duration", 0)) for s in scenes) or 1.0
    shake_idx = [
        i for i, s in enumerate(scenes) if float(s.get("shake", 0) or 0) > 0
    ]
    if not shake_idx:
        return warnings

    # Density cap: at most ~1 shake per 60s.
    allowed = max(1, round(total / 60.0))
    if len(shake_idx) > allowed:
        warnings.append(
            f"{len(shake_idx)} shake scenes in {total:.0f}s video — cap is ~1 per 60s "
            f"({allowed}). Shake lands only when rare; drop the rest."
        )
    # Adjacency.
    for a, b in zip(shake_idx, shake_idx[1:]):
        if b == a + 1:
            warnings.append(
                f"scenes {scenes[a].get('id')} and {scenes[b].get('id')} are adjacent "
                "shake scenes — never two in a row; the second hit can't land."
            )
    # Quiet beats should not shake.
    for i in shake_idx:
        s = scenes[i]
        if s.get("energy") == "low":
            warnings.append(
                f"scene {s.get('id')} is a low-energy beat but has shake "
                f"{s.get('shake')} — shake belongs on impact/reveal, not quiet moments."
            )
    return warnings


def validate_reading_time(timeline: dict[str, Any]) -> list[str]:
    """Text must stay on screen long enough to be read.

    Rule (docs/EDITING_DECISIONS.md §8): min_hold_sec = (word_count / 4) + 1.0,
    absolute floor 0.85s. The scene must outlast its longest text block.
    Warns only — the director fixes upstream."""
    warnings: list[str] = []
    TEXT_KEYS = ("text", "hook_text", "quote_text", "subtext", "sub_hook", "context_text", "caption", "cta_text")
    for s in timeline["scenes"]:
        dur = float(s.get("duration", 0))
        props = s.get("props", {})
        longest = 0
        for k in TEXT_KEYS:
            v = props.get(k)
            if isinstance(v, str) and v.strip():
                longest = max(longest, len(v.split()))
        if longest == 0:
            continue
        min_hold = (longest / 4.0) + 1.0
        if dur < min_hold:
            warnings.append(
                f"scene[{s.get('id')}] ({s['type']}) duration {dur:.2f}s too short for "
                f"{longest}-word text (needs {min_hold:.2f}s reading time)"
            )
    return warnings


def _style_plate(style: str, scene_id: int, duration: float, cache_dir: Path) -> Path:
    """Neutral style plate: solid style-colour clip used as the resilient fallback
    when stock/manual b-roll misses. Scenes layer text/grade on top, so the beat
    stays on-style even with no footage. Never aborts the render.

    Cache key includes the target frame count so a retimed scene (VO changed the
    duration) never reuses a stale plate cut to the old length."""
    from pipeline.intelligence.select_style import load_style
    look = load_style(style).get("palette", {})
    colour = str(look.get("bg", "#141414")).lstrip("#")
    colour = colour if len(colour) == 6 else "141414"
    frames = max(1, int(round(duration * 30)))
    dest = ensure_dir(cache_dir) / f"plate_{style}_{scene_id:02d}_{frames}f.mp4"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    proc = subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c=0x{colour}:size=1920x1080:rate=30",
            "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(dest),
        ],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"style plate ffmpeg failed:\n{proc.stderr[-1000:]}")
    return dest


def stage_resolve_broll(timeline: dict[str, Any], pipeline_cfg: dict[str, Any], allow_stock: bool = True) -> dict[str, Any]:
    """Attach resolved bg assets to each scene props. Copies into remotion/public/.

    Three asset routes (timeline.asset_mode, per-scene broll.source overrides):
      - auto      (Path C, DEFAULT): auto-generate stills via ModelScope
                            (Z-Image/Krea by topic); video beats go to the stock search.
      - stock     (Path A): search Pexels/Pixabay by keyword.
      - generated (Path B): you drop AI-generated stills/clips into assets/in/;
                            image gen, image+video gen, or motion clip (gen_kind).
    `allow_stock=False` (--skip-stock) skips only the online stock search; local
    files, generated stills, and the style-plate fallback still run.
    Either route, on a miss, never aborts — style plate + needs_manual_asset flag."""
    public_dir = ensure_dir(project_path("remotion", "public"))
    # Default route is `auto` (Path C: ModelScope image-gen + Pexels/Pixabay stock
    # video) unless the timeline explicitly declares stock/generated. Per-scene
    # broll.source overrides either way.
    asset_mode = timeline.get("asset_mode", "auto")

    def _plate_fallback(scene: dict[str, Any], props: dict[str, Any], pipeline_cfg: dict[str, Any], public_dir: Path) -> None:
        """Swap the bg for a neutral style plate and flag the scene. Never aborts."""
        sid = int(scene.get("id", 0))
        scene["needs_manual_asset"] = True
        plate = _style_plate(
            timeline.get("global_style", "standard"),
            sid,
            float(scene["duration"]),
            ensure_dir(project_path(pipeline_cfg.get("assets_cache_dir", "pipeline/assets/cache")) / "plates"),
        )
        name = f"scene_{sid:02d}_{plate.stem}{plate.suffix}"
        dest = public_dir / name
        if not dest.exists() or dest.stat().st_size != plate.stat().st_size:
            shutil.copy2(plate, dest)
        props.pop("bg_image", None)
        props["bg_video"] = name
        # Provenance: a plate must route through the full Remotion theme even
        # though it is stored as an MP4 — never send it down the FFmpeg footage path.
        scene["resolved_asset_kind"] = "plate"
        print(f"[broll-fallback] scene {sid} -> style plate {name} (flagged for manual asset)")

    def _is_footage_beat(scene: dict[str, Any], broll: dict[str, Any] | None) -> bool:
        """True when the director wants REAL footage (→ stock video), not a still.
        Signals (any one):
          - scene intent 'footage' (a footage-only / silent beat is real video);
          - explicit broll.source of a stock provider (pexels/pixabay/stock);
          - a broll.keyword with NO gen_kind and NO source — the director asked for
            a real shot (steel mill, locomotive, breadline). Stock footage exists
            for it. (An explicit gen_kind 'image'/'image_video' is what forces a
            generated still, e.g. pre-photography eras with no real footage.)"""
        if (scene.get("intent") or "").lower() == "footage":
            return True
        b = broll or {}
        if (b.get("source") or "").lower() in ("pexels", "pixabay", "stock"):
            return True
        if b.get("keyword") and not b.get("gen_kind") and not b.get("source"):
            return True
        return False

    def _autogen_image(scene: dict[str, Any], props: dict[str, Any], broll: dict[str, Any] | None, public_dir: Path) -> bool:
        """Route C: generate a still via ModelScope (Z-Image / Krea-2-Turbo by topic).

        Only fires when asset_mode=='auto', the scene has no bg yet, and the beat is
        a still (gen_kind image/image_video, or no gen_kind). On success copies the
        PNG flat into public/ and sets bg_image. Returns True when an image was set.
        """
        if asset_mode != "auto":
            return False
        if props.get("bg_image") or props.get("bg_video"):
            return False
        gen_kind = (broll or {}).get("gen_kind")
        if gen_kind in ("video",):
            return False  # explicit video beats go to the stock path, not image-gen
        # Footage intent (Ep1 pilot bug): in auto mode a scene the director wants
        # as REAL footage must hit Pexels/Pixabay, not be flattened to a still.
        # Signals: intent 'footage', an explicit broll.source of a stock provider,
        # or a broll.keyword with gen_kind unset (the director asked for a shot,
        # not a generated image — real B-roll exists for it). Only an explicit
        # gen_kind 'image'/'image_video' forces a generated still.
        if _is_footage_beat(scene, broll):
            return False  # route to stock search below
        prompt = (broll or {}).get("fallback_prompt") or scene.get("vo_text") or timeline.get("title", "")
        sid = int(scene.get("id", 0))
        try:
            from pipeline.assets.imagegen import ImageGenMiss, generate_image_for_scene
            png = generate_image_for_scene(
                prompt, sid, pipeline_cfg,
                seed=int(scene.get("scene_seed", sid)),
                model=(broll or {}).get("gen_model"),
                loras=(broll or {}).get("loras"),
            )
        except ImageGenMiss as e:
            print(f"[autogen-miss] scene {sid}: {e}")
            return False
        except Exception as e:  # never abort on a generator hiccup
            print(f"[autogen-miss] scene {sid}: unexpected {e}")
            return False
        dest = public_dir / png.name
        if not dest.exists() or dest.stat().st_size != png.stat().st_size:
            shutil.copy2(png, dest)
        props["bg_image"] = png.name
        # Scene-specific image props: Document needs document_image, Map needs
        # map_image — these are the content, not just the background. Without
        # them Document.tsx calls staticFile(undefined) and Chrome 404s.
        stype = scene.get("type", "")
        if stype == "document" and not props.get("document_image"):
            props["document_image"] = png.name
        elif stype == "map" and not props.get("map_image"):
            props["map_image"] = png.name
        elif stype == "comparison" and not props.get("left_image"):
            from pipeline.assets.imagegen import generate_image_for_scene
            left_prompt = props.pop("left_prompt", None)
            right_prompt = props.pop("right_prompt", None)
            if not left_prompt or not right_prompt:
                raise ValueError(f"comparison scene {sid} requires left_prompt and right_prompt")
            left = generate_image_for_scene(
                left_prompt, sid * 2, pipeline_cfg, seed=sid * 2
            )
            right = generate_image_for_scene(
                right_prompt, sid * 2 + 1, pipeline_cfg, seed=sid * 2 + 1
            )
            for generated in (left, right):
                target = public_dir / generated.name
                if not target.exists() or target.stat().st_size != generated.stat().st_size:
                    shutil.copy2(generated, target)
            props["left_image"] = left.name
            props["right_image"] = right.name
        scene["resolved_asset_kind"] = "image"
        print(f"[autogen] scene {sid} -> generated still {png.name}")
        return True

    for scene in timeline["scenes"]:
        broll = scene.get("broll")
        props = scene["props"]
        if props.get("bg_video") or props.get("bg_image"):
            # Already set (local assets). Resolve against the project root, copy the
            # file FLAT into remotion/public/, and point the prop at the flat name.
            def _flatten(val: Any) -> str | None:
                """Resolve a project-relative asset, copy it flat into public/, return
                the flat basename. Returns None when the file can't be resolved (warns)."""
                if not val or not isinstance(val, str):
                    return None
                src = project_path(val)
                if not src.exists():
                    # tolerate a bare filename already sitting in public/
                    if (public_dir / Path(val).name).exists():
                        return Path(val).name
                    print(f"[asset-warn] scene {scene.get('id')}: {val} not found")
                    return None
                dest = public_dir / src.name
                if not dest.exists() or dest.stat().st_size != src.stat().st_size:
                    shutil.copy2(src, dest)
                return src.name

            for key in ("bg_video", "bg_image", "left_image", "right_image", "document_image", "overlay_image"):
                val = props.get(key)
                if not val:
                    continue
                new = _flatten(val)
                if new:
                    props[key] = new
                else:
                    # Drop the dead path so Remotion never sees a 404 src (which
                    # crashes Chrome with EncodingError and kills the whole batch).
                    props.pop(key, None)
            # Provenance from the surviving background media (after dead paths are
            # dropped). A local clip is real footage; a still is an image scene.
            if props.get("bg_video"):
                scene["resolved_asset_kind"] = "video"
            elif props.get("bg_image"):
                scene["resolved_asset_kind"] = "image"
            # Role-based asset slots also carry local srcs that must be flattened.
            for slot_key in ("foreground", "midground"):
                slots = props.get(slot_key)
                if isinstance(slots, list):
                    kept = []
                    for slot in slots:
                        if isinstance(slot, dict) and slot.get("src"):
                            new = _flatten(slot["src"])
                            if new:
                                slot["src"] = new
                                kept.append(slot)
                            # unresolvable slot: drop it (layer is decorative)
                        else:
                            kept.append(slot)
                    props[slot_key] = kept
            overlay = props.get("overlay")
            if isinstance(overlay, dict) and overlay.get("src"):
                new = _flatten(overlay["src"])
                if new:
                    overlay["src"] = new
                else:
                    props.pop("overlay", None)
            # If the background never resolved, the scene has no media to show.
            # Route C: try to auto-generate a still first; only then plate-fallback.
            if not props.get("bg_video") and not props.get("bg_image"):
                if not _autogen_image(scene, props, broll, public_dir):
                    _plate_fallback(scene, props, pipeline_cfg, public_dir)
            continue
        if not broll:
            continue
        # Route C: for an image beat with no local asset, auto-generate the still
        # before falling through to the stock/manual search.
        if asset_mode == "auto" and _autogen_image(scene, props, broll, public_dir):
            continue
        # Apply the video-wide route unless the scene pins its own source.
        if "source" not in broll and asset_mode == "generated":
            broll = {**broll, "source": "manual"}  # generated assets arrive as manual drop-ins
        # --skip-stock: skip only the *online stock search*; manual/generated/auto
        # drop-ins and the plate fallback still run. A stock-sourced scene becomes a
        # plate + manual-asset flag rather than hitting the network.
        src_route = (broll or {}).get("source", "manual" if asset_mode in ("generated",) else "pexels")
        if not allow_stock and src_route in ("pexels", "pixabay", "stock"):
            print(f"[skip-stock] scene {scene.get('id')}: stock search skipped -> style plate")
            _plate_fallback(scene, props, pipeline_cfg, public_dir)
            continue
        gen_kind = (broll or {}).get("gen_kind")
        is_still_beat = gen_kind in ("image", "image_video")
        try:
            if is_still_beat:
                # Still beat: loop a generated/manual still to a clip for Remotion.
                clip = resolve_broll(
                    broll,
                    scene_id=int(scene.get("id", 0)),
                    duration=float(scene["duration"]),
                    pipeline_cfg=pipeline_cfg,
                )
            else:
                # Genuine video beat: fetch-to-cover, trim-to-fit into raw source
                # segments. These are edited by FFmpeg at render time (footage path),
                # never baked into a Remotion-bound MP4 here.
                segments = resolve_broll_segments(
                    broll,
                    scene_id=int(scene.get("id", 0)),
                    duration=float(scene["duration"]),
                    pipeline_cfg=pipeline_cfg,
                )
        except StockMissError as e:
            route = "generated" if (broll or {}).get("source") in ("manual", "local", "generated") or gen_kind else "stock"
            print(f"[asset-miss:{route}] scene {scene.get('id')}: {e}")
            if e.fallback_prompt:
                which = {"image": "04_image_prompt", "image_video": "04_image_prompt + 05_video_prompt", "video": "05_video_prompt"}.get(gen_kind, "04_image_prompt")
                print(f"  Generate with ({which}):\n  {e.fallback_prompt}")
            exts = ".png/.jpg (image) or .mp4 (video)" if gen_kind in (None, "image", "image_video") else ".mp4 (video)"
            print(
                f"  Drop file at: pipeline/assets/in/scene_{int(scene.get('id', 0)):02d}{exts}"
            )
            # P8 resilience: do NOT abort. Flag for a manual asset and fall back to a
            # neutral style plate so the render completes on-style.
            _plate_fallback(scene, props, pipeline_cfg, public_dir)
            continue

        if is_still_beat:
            name = f"scene_{int(scene.get('id', 0)):02d}_{clip.stem}{clip.suffix}"
            dest = public_dir / name
            if not dest.exists() or dest.stat().st_size != clip.stat().st_size:
                shutil.copy2(clip, dest)
            props["bg_video"] = name
            # A generated/manual STILL looped to an MP4 is an image scene, not footage.
            scene["resolved_asset_kind"] = "image"
            print(f"[broll] scene {scene.get('id')} -> {name}")
        else:
            scene["resolved_segments"] = segments
            scene["resolved_asset_kind"] = "video"
            print(f"[broll] scene {scene.get('id')} -> video segments x{len(segments)} (footage path)")
    # Artifact scenes render their focal media through a type-specific prop.
    # Reuse the resolved background rather than falling through to Root.tsx's
    # demo `1.png`, which does not exist in production bundles.
    for scene in timeline["scenes"]:
        props = scene.get("props", {})
        if scene.get("type") == "document" and not props.get("document_image"):
            props["document_image"] = props.get("bg_image")
        if scene.get("type") == "map" and not props.get("map_image"):
            props["map_image"] = props.get("bg_image")
    return timeline


def validate_total_vo_duration(
    timeline: dict[str, Any], min_sec: float = 8 * 60, max_sec: float = 20 * 60
) -> float:
    """Reject scripts outside production runtime before assets or rendering."""
    total = sum(float(scene.get("vo_duration", 0.0)) for scene in timeline["scenes"])
    if total < min_sec or total > max_sec:
        raise ValueError(
            f"total VO is {total / 60:.2f} minutes; script must be adjusted to "
            f"produce between {min_sec / 60:g} and {max_sec / 60:g} minutes of VO"
        )
    print(f"[vo] total: {total / 60:.2f} minutes (required 8-20)")
    return total


# --- Program-clock helpers (Path A, §2) ---------------------------------------
#
# The render layer (remotion/src/render.js) shortens the final picture at every
# animated cut: an xfade overlaps `sec` seconds of two clips, so the joined
# output is shorter than the sum of scene durations. Hard cuts are TRUE concat
# (zero overlap). The program clock below mirrors that exact arithmetic so
# `vo_start` and the expected final duration track the *assembled* picture, not
# the naive sum of scene durations. Keep `resolve_cut_transition_sec` in sync
# with resolveCutTransition() in render.js.

_WHIP_SEC = 8 / 30  # mirror of render.js WHIP_SEC


def resolve_cut_transition_sec(
    intent: str | None,
    transition_sec: float,
) -> float:
    """Seconds of picture overlap at a cut, given the director's transition_out
    intent. Mirrors render.js resolveCutTransition: hard → 0 (true concat, no
    overlap); whip → fixed snap; style/dissolve/dip → the style transition_sec."""
    kind = (intent or "style").lower()
    if kind == "hard":
        return 0.0
    if kind == "whip":
        return _WHIP_SEC
    # style / dissolve / dip all run at the style's transition_sec.
    return float(transition_sec)


def expected_program_sec(timeline: dict[str, Any], transition_sec: float | None = None) -> float:
    """Expected final picture duration = sum(scene durations) − sum(xfade overlaps).
    Hard cuts subtract nothing. This is the single source of truth for both
    `vo_start` placement and the post-render duration assertion."""
    scenes = timeline["scenes"]
    if not scenes:
        return 0.0
    if transition_sec is None:
        transition_sec = float(timeline.get("transition_sec", 0.6))
    total = sum(float(s.get("duration", 0.0)) for s in scenes)
    overlap = 0.0
    for s in scenes[:-1]:  # scene i's transition_out governs cut i → i+1
        intent = s.get("transition_out") or s.get("props", {}).get("transition_out")
        overlap += resolve_cut_transition_sec(intent, transition_sec)
    return round(total - overlap, 3)


def stage_retime_to_vo(timeline: dict[str, Any]) -> dict[str, Any]:
    """VO-driven timing (Ep1 pilot fix): after VO is synthesized, make each
    narrated scene's duration FOLLOW its measured VO exactly — VO length + a
    small tail — instead of the pre-VO ~140wpm guess. Footage-only beats (no
    vo_text, footage intent) keep their director-set duration.

    vo_start walks the ASSEMBLED program clock: each cut consumes the outgoing
    scene's transition overlap, so narration lands on the picture as joined by
    FFmpeg (hard cuts advance the full scene duration; xfades advance duration
    minus the overlap)."""
    for scene in timeline["scenes"]:
        if scene.get("vo_duration") is not None:
            tail = float(scene.get("vo_tail", 0.5))
            scene["duration"] = round(float(scene["vo_duration"]) + tail, 3)
    transition_sec = float(timeline.get("transition_sec", 0.6))
    # Re-walk vo_start on the assembled-picture clock so beats stay contiguous
    # after retiming AND after xfade overlap is accounted for.
    t = 0.0
    scenes = timeline["scenes"]
    for i, scene in enumerate(scenes):
        scene["vo_start"] = round(t, 3)
        dur = float(scene["duration"])
        if i < len(scenes) - 1:
            intent = scene.get("transition_out") or scene.get("props", {}).get("transition_out")
            dur -= resolve_cut_transition_sec(intent, transition_sec)
        t += dur
    timeline["total_sec"] = round(t, 3)
    return timeline


def validate_footage_beats(timeline: dict[str, Any]) -> list[str]:
    """Footage-only (silent) beats — the variety the pilot lacked. A scene with
    footage intent and no vo_text lets the picture and music breathe (no talking).
    Rules so it reads as a deliberate beat, not a gap:
      - it must have a real video bg (bg_video) or broll that resolves to video —
        a silent STILL is the frozen-slideshow bug, not a breathing beat;
      - cap ~1 in 5 scenes (too many and the narration feels absent)."""
    warnings: list[str] = []
    scenes = timeline["scenes"]
    footage_idx = [
        i for i, s in enumerate(scenes)
        if not s.get("vo_text") and (
            (s.get("intent") == "footage") or (s.get("props", {}).get("bg_video"))
        )
    ]
    for i in footage_idx:
        s = scenes[i]
        props = s.get("props", {})
        has_video = bool(props.get("bg_video")) or (
            (s.get("broll") or {}).get("gen_kind") in ("video", "image_video")
        )
        if not has_video and not props.get("bg_video"):
            warnings.append(
                f"scene[{s.get('id')}] is a footage-only beat (no VO) but has no "
                "video bg — a silent still is the frozen bug. Give it real footage "
                "(broll.gen_kind 'video'/'image_video' or a stock clip)."
            )
    if len(scenes) >= 5 and len(footage_idx) > max(1, len(scenes) // 5):
        warnings.append(
            f"{len(footage_idx)} footage-only beats in {len(scenes)} scenes — cap "
            "~1 in 5 so the narration doesn't feel absent."
        )
    return warnings


def _scene_needs_overlay(scene: dict[str, Any]) -> bool:
    """True when a footage scene carries authored foreground text/graphics that
    must ride over the clean footage via a Remotion alpha overlay (Option A).
    Only explicit text keys trigger it — vo_text alone does NOT caption a scene."""
    props = scene.get("props", {})
    TEXT_KEYS = ("text", "hook_text", "quote_text", "subtext", "sub_hook", "context_text", "caption", "cta_text")
    return any(isinstance(props.get(k), str) and props[k].strip() for k in TEXT_KEYS)


def stage_build_manifest(timeline: dict[str, Any], output_mp4: Path) -> Path:
    """Convert timeline → remotion batch manifest (carries global_style).

    Footage-type router (Path A): scenes are classified by resolved_asset_kind.
    image/plate scenes render the full Remotion theme; video scenes are edited by
    FFmpeg (trim/grade) and only get a Remotion alpha overlay when they carry
    authored text. The manifest carries the routed scene list with absolute
    footage clip paths for the render layer to splice in."""
    out_dir = ensure_dir(output_mp4.parent)
    global_style = normalize_style_id(
        timeline.get("global_style") or timeline.get("edit_style")
    ) or "standard"
    footage_cache = ensure_dir(
        project_path("pipeline", "assets", "cache") / "footage"
    )
    routed = route_scenes(timeline, footage_cache)
    scenes_out = []
    for entry in routed:
        scene = entry["scene"]
        # Editorial/director fields live at scene level in the timeline; the
        # manifest must forward them so render.js can pass them to Remotion.
        mscene: dict[str, Any] = {
            "type": scene["type"],
            "duration": scene["duration"],
            # Router fields (read by render.js, not by Remotion comps).
            "render_route": entry["route"],
            "footage_path": entry.get("footage_path"),
            "needs_overlay": entry.get("needs_overlay", False),
            "props": {
                **scene["props"],
                "accent_color": timeline.get("accent_color", "#ff6b35"),
                "text_color": timeline.get("text_color", "#ffffff"),
            },
        }
        for key in (
            "layout",
            "placement",
            "energy",
            "shake",
            "shake_at",
            "shake_dir",
            "beats",
            "tempo",
            "transition_out",
            "transition_note",
            "grade_override",
            "signature",
            "photo_move",
            "still_motion",
            "parallax",
            "arc_position",
            "sfx",
            "word_times",
        ):
            if key in scene and scene[key] is not None:
                mscene[key] = scene[key]
        scenes_out.append(mscene)
    manifest = {
        "composition": "full-video",
        "output": str(output_mp4).replace("\\", "/"),
        "accent_color": timeline.get("accent_color", "#ff6b35"),
        "text_color": timeline.get("text_color", "#ffffff"),
        "transition_sec": timeline.get("transition_sec", 0.6),
        # Global style drives palette, transitions, grade, motion in Remotion.
        "global_style": global_style,
        # Deprecated alias kept for older render.js / manifests.
        "edit_style": global_style,
        "scenes": scenes_out,
    }
    path = out_dir / f"{output_mp4.stem}_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[manifest] {path}")
    return path


def route_scenes(timeline: dict[str, Any], footage_cache: Path) -> list[dict[str, Any]]:
    """Classify each scene and pre-render footage clips via FFmpeg.

    Returns a list (same order as timeline scenes) of {scene, route,
    footage_path, needs_overlay}. image/plate → 'remotion'; video → 'ffmpeg'
    (footage clip rendered here, spliced by the render layer).
    """
    from pipeline.render.footage import render_footage_scene

    global_style = normalize_style_id(
        timeline.get("global_style") or timeline.get("edit_style")
    ) or "standard"
    out: list[dict[str, Any]] = []
    for scene in timeline["scenes"]:
        kind = scene.get("resolved_asset_kind")
        # Back-compat: scenes without provenance (older timelines) default to the
        # Remotion path — they were rendered by Remotion before the router existed.
        if kind == "video" and scene.get("resolved_segments"):
            clip = render_footage_scene(
                scene["resolved_segments"],
                global_style,
                float(scene["duration"]),
                footage_cache,
            )
            out.append(
                {
                    "scene": scene,
                    "route": "ffmpeg",
                    "footage_path": str(clip),
                    "needs_overlay": _scene_needs_overlay(scene),
                }
            )
        else:
            out.append(
                {
                    "scene": scene,
                    "route": "remotion",
                    "footage_path": None,
                    "needs_overlay": False,
                }
            )
    return out


def stage_render(manifest_path: Path, scene_pause: float | None = None, concurrency: int | None = None) -> None:
    remotion = project_path("remotion")
    cmd = ["node", "src/render.js", "--batch", str(manifest_path)]
    # Thermal relief between scene renders (CPU breath) — forwarded to render.js,
    # which sleeps scenePauseSec after each scene clip. Concurrency caps parallel
    # Chrome bursts.
    if scene_pause is not None:
        cmd += ["--scene-pause", str(scene_pause)]
    if concurrency is not None:
        cmd += ["--concurrency", str(concurrency)]
    print(f"[render] {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(remotion), check=True)


def stage_assemble_cloud(manifest_path: Path, clips_dir: Path) -> None:
    remotion = project_path("remotion")
    cmd = ["node", "src/render.js", "--batch", str(manifest_path), "--assemble-only", str(clips_dir)]
    print(f"[assemble] {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(remotion), check=True)


def safe_output_stem(title: str, limit: int = 40) -> str:
    """Portable filename stem; forbids Windows ADS/reserved punctuation."""
    stem = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("._")[:limit].rstrip("._")
    return stem or "video"


def validate_external_vo(timeline: dict[str, Any]) -> None:
    """Require director timelines to carry VO produced by pipeline.vo_plan."""
    missing = [
        scene.get("id") for scene in timeline["scenes"]
        if scene.get("vo_text") and (
            not scene.get("vo_audio")
            or scene.get("vo_duration") is None
            or scene.get("word_times") is None
        )
    ]
    if missing:
        raise ValueError(
            "timeline has narration without external VO metadata for scenes "
            f"{missing}; run `python -m pipeline.vo_plan` before director, then "
            "copy each beat's audio_path/duration_sec/word_times into its scene"
        )


def _resolve_sfx_path(name: str) -> Path | None:
    """Resolve a director-named SFX to pipeline/assets/sfx/<name>. Missing → None
    (we skip, never abort — audio garnish must not break a render)."""
    p = project_path("pipeline", "assets", "sfx", name)
    return p if p.exists() else None


def _collect_sfx(timeline: dict[str, Any]) -> list[tuple[float, Path, float]]:
    """Return [(start_sec, sfx_path, volume), ...] for scenes that opt into SFX.
    Volume = scene override → timeline default → 0.6. Missing files are skipped."""
    default_vol = float(timeline.get("sfx_volume", 0.6))
    out: list[tuple[float, Path, float]] = []
    for s in timeline["scenes"]:
        name = s.get("sfx")
        if not name:
            continue
        path = _resolve_sfx_path(str(name))
        if path is None:
            print(f"[audio] sfx not found: {name} — skip (scene {s.get('id')})")
            continue
        vol = float(s.get("sfx_volume", default_vol))
        out.append((float(s.get("vo_start", 0.0)), path, vol))
    return out


def _build_audio_filter(
    n_vo: int,
    vo_starts: list[float],
    music_index: int | None,
    duck_db: float,
    sfx: list[tuple[float, Path, float]],
    sfx_indices: list[int],
    video_dur: float | None = None,
) -> str:
    """Compose the filter_complex graph (audio only, pre-loudnorm).

    Layout: VO lines are individually adelay'd then amix'd into a single [vo]
    bus, which is BOTH a mix input and the sidechain that ducks the music bed
    (sidechaincompress) — the duck engages only while VO plays, unlike the old
    whole-video volume flatten. The music bed is padded with silence to the full
    video length so the sidechain is a gain envelope (music recovers after VO)
    rather than a hard cut at the end of narration. SFX are one-shot accents:
    adelay'd to their scene and mixed at their set level directly.
    """
    parts: list[str] = []
    vo_labels: list[str] = []
    for i, start in enumerate(vo_starts):
        delay_ms = int(round(start * 1000))
        parts.append(f"[{i + 1}:a]adelay={delay_ms}|{delay_ms}[v{i}]")
        vo_labels.append(f"[v{i}]")

    mix_inputs: list[str] = []

    # Single VO bus (only when narration exists). When music is present, asplit
    # also feeds the duck sidechain; otherwise the bus goes straight to the mix
    # (no dangling label). The sidechain copy is padded with trailing silence to
    # the full video length so the music compressor stays alive after narration
    # ends (sidechaincompress otherwise terminates with the shorter sidechain
    # input, cutting the music bed early). With no VO, there is no sidechain —
    # music plays unducked.
    if n_vo:
        if music_index is not None:
            parts.append(
                f"{''.join(vo_labels)}amix=inputs={n_vo}:duration=longest:normalize=0,"
                f"asplit=2[vo_mix][vo_key_raw]"
            )
            if video_dur is not None:
                parts.append(f"[vo_key_raw]apad,atrim=0:{video_dur:.3f}[vo_key]")
            else:
                parts.append("[vo_key_raw]anull[vo_key]")
        else:
            parts.append(
                f"{''.join(vo_labels)}amix=inputs={n_vo}:duration=longest:normalize=0[vo_mix]"
            )
        mix_inputs.append("[vo_mix]")

    # Music bed: ducked under VO via sidechaincompress (only when VO exists),
    # then trimmed to duck_db below unity so the bed sits under narration. Pad
    # with trailing silence to the full video length first so the bed keeps
    # playing (at recovered level) after the last VO line ends — sidechaincompress
    # otherwise ends the music with the sidechain. With no VO, the bed plays at
    # the ducked level for the whole video (no narration to duck against).
    if music_index is not None:
        duck_gain = 10 ** (duck_db / 20.0)
        if video_dur is not None:
            parts.append(
                f"[{music_index}:a]apad,atrim=0:{video_dur:.3f}[mpre]"
            )
        else:
            parts.append(f"[{music_index}:a]anull[mpre]")
        if n_vo:
            parts.append(
                f"[mpre][vo_key]sidechaincompress=threshold=0.02:ratio=8:"
                f"attack=20:release=400:makeup=1,volume={duck_gain:.4f}[mus]"
            )
        else:
            parts.append(f"[mpre]volume={duck_gain:.4f}[mus]")
        mix_inputs.append("[mus]")

    # SFX one-shots: position each at its scene start, scale to its level, mix in.
    for k, ((start, _path, vol), idx) in enumerate(zip(sfx, sfx_indices)):
        delay_ms = int(round(start * 1000))
        parts.append(
            f"[{idx}:a]adelay={delay_ms}|{delay_ms},volume={vol:.4f}[sfx{k}]"
        )
        mix_inputs.append(f"[sfx{k}]")

    parts.append(
        f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:"
        f"duration=longest:normalize=0[a_raw]"
    )
    return ";".join(parts)


def _run_two_pass_loudnorm(
    args_prefix: list[str],
    a_raw_label: str,
    target_lufs: float,
    output_args: list[str],
) -> list[str]:
    """Two-pass loudnorm → returns the full ffmpeg arg list for pass 2.

    Pass 1 runs loudnorm with print_format=json to measure the mixed signal;
    pass 2 applies linear normalization with the measured_* values so we hit the
    platform target (−14 LUFS / −1 dBTP) precisely instead of the single-pass
    dynamic approximation.
    """
    import re

    # a_raw_label is the full mix graph ending in the [a_raw] pad; chain loudnorm
    # onto that pad with a chain separator.
    measure_fc = (
        f"{a_raw_label};[a_raw]loudnorm=I={target_lufs}:TP=-1.0:LRA=11:print_format=json"
    )
    measure_cmd = args_prefix + ["-filter_complex", measure_fc, "-f", "null", "-"]
    proc = subprocess.run(measure_cmd, capture_output=True, text=True)
    measured: dict[str, str] = {}
    # loudnorm prints the measurement as a pretty-printed JSON block to stderr.
    m = re.search(r"\{.*?\}", proc.stderr, re.DOTALL)
    if m:
        try:
            measured = json.loads(m.group(0))
        except json.JSONDecodeError:
            measured = {}

    keys = ("input_i", "input_tp", "input_lra", "input_thresh")
    if all(k in measured for k in keys):
        norm = (
            f"loudnorm=I={target_lufs}:TP=-1.0:LRA=11:"
            f"measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:"
            f"measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}:"
            f"linear=true"
        )
        print(f"[audio] loudnorm two-pass (measured I={measured['input_i']} LUFS)")
    else:
        # Fallback: single-pass dynamic loudnorm if measurement failed.
        norm = f"loudnorm=I={target_lufs}:TP=-1.0:LRA=11"
        print("[audio] loudnorm single-pass (measurement unavailable)")

    apply_fc = f"{a_raw_label};[a_raw]{norm}[aout]"
    return args_prefix + ["-filter_complex", apply_fc] + output_args


def stage_audio_mix(
    timeline: dict[str, Any],
    video_path: Path,
    output_path: Path,
    pipeline_cfg: dict[str, Any],
) -> Path:
    """Mux VO lines (+ optional music/SFX) onto silent video.

    Runs whenever there is VO, music, or SFX — narration is not required (a
    silent picture with only music/SFX still gets an audio pass). Music & SFX
    are ducked under VO via sidechaincompress when VO exists, and loudness is
    normalized with a true two-pass loudnorm to the platform target (YouTube
    −14 LUFS / −1 dBTP)."""
    vo_entries = [
        (float(s.get("vo_start", 0)), s["vo_audio"])
        for s in timeline["scenes"]
        if s.get("vo_audio")
    ]
    sfx = _collect_sfx(timeline)
    music_ref = timeline.get("music")
    # Nothing to add at all → copy the silent picture through.
    if not vo_entries and not music_ref and not sfx:
        shutil.copy2(video_path, output_path)
        return output_path

    vo_starts = [st for st, _ in vo_entries]

    # inputs: 0=video, 1..N=vo files, then music, then sfx files
    args_prefix = ["ffmpeg", "-y", "-i", str(video_path)]
    for _, path in vo_entries:
        args_prefix += ["-i", path]
    next_index = 1 + len(vo_entries)

    music_path: Path | None = None
    music_index: int | None = None
    music = timeline.get("music")
    if music:
        candidate = project_path("pipeline", "assets", "music", music)
        if not candidate.exists():
            candidate = project_path(music)
        if candidate.exists():
            music_path = candidate
            music_index = next_index
            args_prefix += ["-i", str(music_path)]
            next_index += 1
        else:
            print(f"[audio] music not found: {music} — skip")

    sfx_indices: list[int] = []
    seen: set[str] = set()
    for _, path, _ in sfx:
        key = str(path)
        if key in seen:
            # Reuse the same input index for a repeated sfx file.
            sfx_indices.append(_index_of_input(args_prefix, key))
            continue
        seen.add(key)
        sfx_indices.append(next_index)
        args_prefix += ["-i", str(path)]
        next_index += 1

    duck_db = float(timeline.get("music_duck_db", -12))
    video_dur = probe_duration(video_path)
    a_raw = _build_audio_filter(
        n_vo=len(vo_entries),
        vo_starts=vo_starts,
        music_index=music_index,
        duck_db=duck_db,
        sfx=sfx,
        sfx_indices=sfx_indices,
        video_dur=video_dur,
    )

    target = float(
        timeline.get(
            "loudness_target_lufs",
            pipeline_cfg.get("loudness", {}).get("target_lufs", -14),
        )
    )
    output_args = [
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-ar", "48000",
        "-b:a", "192k",
        str(output_path),
    ]
    n_ducked = (1 if music_index is not None else 0) + len(sfx)
    print(
        f"[audio] mixing {len(vo_entries)} VO + {n_ducked} ducked beds "
        f"(music={'yes' if music_index is not None else 'no'}, sfx={len(sfx)}), two-pass loudnorm"
    )
    full_args = _run_two_pass_loudnorm(args_prefix, a_raw, target, output_args)
    subprocess.run(full_args, check=True)
    return output_path


def _index_of_input(args_prefix: list[str], path: str) -> int:
    """Find the input index of an already-added -i path (0-based, video=0)."""
    inputs = [i for i, a in enumerate(args_prefix) if a == "-i"]
    for n, pos in enumerate(inputs):
        if args_prefix[pos + 1] == path:
            return n
    raise ValueError(f"input not found: {path}")


def run(
    timeline_path: Path,
    output: Path | None = None,
    skip_vo: bool = False,
    skip_stock: bool = False,
    skip_audio: bool = False,
    style_override: str | None = None,
    scene_pause: float | None = None,
    concurrency: int | None = None,
    render_mode: str = "github",
    github_repo: str | None = "srb991/video-factory",
    github_ref: str = "master",
) -> Path:
    timeline = load_json(timeline_path)
    if style_override:
        timeline["global_style"] = normalize_style_id(style_override)
        print(f"[style] override -> {timeline['global_style']}")
    validate_timeline(timeline)
    for w in validate_style_consistency(timeline):
        print(f"[style-warn] {w}")
    pipeline_cfg = load_json(project_path("pipeline", "config", "pipeline.json"))

    out_dir = ensure_dir(pipeline_cfg.get("output_dir", "output"))
    stem = safe_output_stem(timeline["title"])
    silent_mp4 = out_dir / f"{stem}_silent.mp4"
    final_mp4 = output or (out_dir / f"{stem}_final.mp4")
    resolved_path = out_dir / f"{stem}_timeline_resolved.json"

    # VO is a separate pre-director stage (`python -m pipeline.vo_plan`). The
    # orchestrator only validates and applies its measured timing; it never calls TTS.
    has_narration = any(s.get("vo_text") for s in timeline["scenes"])
    if not skip_vo:
        if has_narration:
            validate_external_vo(timeline)
            validate_total_vo_duration(timeline)
            timeline = stage_retime_to_vo(timeline)
        # Checkpoint: persist the VO-timed timeline before touching the network.
        resolved_path.write_text(json.dumps(timeline, indent=2), encoding="utf-8")

    # Resolve assets AFTER VO retime so stock/manual/generated searches and
    # normalizations target measured scene durations. --skip-stock only skips the
    # *stock search*; local files, generated stills, and plate fallback still run.
    timeline = stage_resolve_broll(timeline, pipeline_cfg, allow_stock=not skip_stock)
    for warning in validate_long_stills(timeline):
        print(f"[visual-variety-warn] {warning}")

    # Checkpoint: persist the fully-resolved timeline (assets attached).
    resolved_path.write_text(json.dumps(timeline, indent=2), encoding="utf-8")

    manifest = stage_build_manifest(timeline, silent_mp4)
    if render_mode == "github":
        if not github_repo:
            raise ValueError("--github-repo is required with --render-mode github")
        from pipeline.render.cloud import stage_cloud_payload
        from pipeline.render.github_actions import render_on_github

        payload = project_path("remotion", "cloud-payload")
        cloud_manifest = stage_cloud_payload(manifest, payload, project_path("remotion", "public"))
        clips_dir = render_on_github(
            cloud_manifest,
            out_dir / "remotion-clips",
            github_repo,
            ref=github_ref,
            concurrency=concurrency or 2,
            scene_pause=scene_pause if scene_pause is not None else 0,
            timeout=3 * 60 * 60,
        )
        stage_assemble_cloud(manifest, clips_dir)
    else:
        stage_render(manifest, scene_pause=scene_pause, concurrency=concurrency)

    # Program-clock assertion (Path A §2.3): the assembled silent picture must
    # match expected_program_sec (scene durations minus xfade overlaps) within a
    # frame — otherwise narration would drift out of sync. Warn (not abort) so a
    # borderline render still completes, but surface it loudly for investigation.
    try:
        expected = expected_program_sec(timeline)
        actual = probe_duration(silent_mp4)
        tolerance = (1.0 / 30) + 0.05
        if abs(actual - expected) > tolerance:
            print(
                f"[clock-warn] assembled duration {actual:.3f}s != expected "
                f"{expected:.3f}s (drift {actual - expected:+.3f}s) — VO may be out "
                "of sync; check transition/concat math."
            )
    except Exception as e:
        print(f"[clock-warn] could not verify assembled duration: {e}")

    # Mix whenever there is VO, music, or SFX — a silent picture with only music
    # or SFX still needs the audio pass (not just a copy).
    has_audio = (
        any(s.get("vo_audio") for s in timeline["scenes"])
        or bool(timeline.get("music"))
        or any(s.get("sfx") for s in timeline["scenes"])
    )
    if not skip_audio and has_audio:
        stage_audio_mix(timeline, silent_mp4, final_mp4, pipeline_cfg)
    else:
        shutil.copy2(silent_mp4, final_mp4)

    print(f"\nDone -> {final_mp4}")
    return final_mp4


def run_brief(
    brief: str,
    duration_min: float = 8.0,
    style_override: str | None = None,
) -> None:
    """Auto-select style + print the VidRush-format brief.

    Full-auto mode: the agent runs the skills chain (01→05) on this brief to
    produce a timeline.json, then renders it via ``run()``. This function's job
    is the deterministic front-end — style selection + the style-locked brief
    the chain consumes. The chain itself is agent/LLM work, not Python."""
    style_id, scores = select_style(brief, override=style_override, return_scores=True)
    if scores:
        print(f"[scores] {json.dumps(scores, sort_keys=True)}")
    print(f"[style] {style_id}" + (" (override)" if style_override else ""))
    from pipeline.intelligence.brief_template import build_brief

    print()
    print(build_brief(brief, style_id, duration_min))
    print()
    print(
        "Next: run the skills chain with this prompt, write timeline.json with "
        f"global_style=\"{style_id}\", then:\n"
        "  python -m pipeline.orchestrator --timeline <timeline.json>"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Vidrush-style local video pipeline")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--timeline", help="Path to timeline.json")
    src.add_argument("--brief", help="Video brief — auto-selects style, prints skills prompt")
    p.add_argument("--style", default=None, help="Force global style (id or legacy alias)")
    p.add_argument("--duration", type=float, default=8.0, help="Target minutes (--brief mode)")
    p.add_argument("--output", default=None, help="Final MP4 path")
    p.add_argument("--skip-vo", action="store_true")
    p.add_argument("--skip-stock", action="store_true")
    p.add_argument("--skip-audio", action="store_true")
    p.add_argument("--scene-pause", type=float, default=None,
                   help="Seconds to pause between scene renders (CPU thermal relief). Default 2 in render.js.")
    p.add_argument("--concurrency", type=int, default=None,
                   help="Parallel scene renders (default 3 remotion-only / 4 hybrid). Lower = cooler CPU.")
    p.add_argument("--render-mode", choices=("local", "github"), default="github",
                    help="Render Remotion clips locally or on GitHub Actions; assembly stays local.")
    p.add_argument("--github-repo", default="srb991/video-factory",
                   help="GitHub owner/repo for --render-mode github")
    p.add_argument("--github-ref", default="master", help="Committed ref containing cloud payload")
    args = p.parse_args(argv)

    try:
        if args.brief:
            run_brief(args.brief, duration_min=args.duration, style_override=args.style)
            return 0
        run(
            Path(args.timeline),
            Path(args.output) if args.output else None,
            skip_vo=args.skip_vo,
            skip_stock=args.skip_stock,
            skip_audio=args.skip_audio,
            style_override=args.style,
            scene_pause=args.scene_pause,
            concurrency=args.concurrency,
            render_mode=args.render_mode,
            github_repo=args.github_repo,
            github_ref=args.github_ref,
        )
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
