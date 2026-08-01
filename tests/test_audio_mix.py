"""Tests for Phase 8, P6 — audio architecture.

Covers the pure/graph-building pieces (no ffmpeg render): the sidechain duck
filter graph, two-pass loudnorm arg assembly, SFX collection + rarity. The real
mix is exercised by the E2E run (needs audio files + ffmpeg).
"""

from __future__ import annotations

from pipeline.orchestrator import (
    _build_audio_filter,
    validate_sfx_rarity,
)


# --- filter graph construction ---------------------------------------------

def test_filter_vo_only_no_music_has_no_duck() -> None:
    g = _build_audio_filter(2, [0.0, 4.0], None, -12, [], [], video_dur=8.0)
    # no music -> no sidechain, no dangling vo_key
    assert "sidechaincompress" not in g
    assert "vo_key" not in g
    assert "[vo_mix]" in g


def test_filter_music_adds_sidechain_duck() -> None:
    g = _build_audio_filter(1, [0.0], 2, -12, [], [], video_dur=5.0)
    assert "sidechaincompress" in g
    # music ducked under the VO sidechain
    assert "[mpre][vo_key]sidechaincompress" in g
    # duck gain for -12 dB ~ 0.2512
    assert "volume=0.2512" in g


def test_filter_pads_sidechain_to_video_length() -> None:
    # the recovery fix: pad the VO sidechain so music isn't cut at VO end
    g = _build_audio_filter(1, [0.0], 2, -12, [], [], video_dur=5.0)
    assert "[vo_key_raw]apad,atrim=0:5.000[vo_key]" in g
    assert "apad,atrim=0:5.000[mpre]" in g


def test_filter_sfx_positioned_at_scene_start() -> None:
    sfx = [(2.5, "paper.wav", 0.6)]
    g = _build_audio_filter(1, [0.0], None, -12, sfx, [2], video_dur=5.0)
    assert "adelay=2500|2500" in g
    assert "volume=0.6000" in g
    assert "[sfx0]" in g


def test_filter_sfx_without_music_still_mixes() -> None:
    sfx = [(0.0, "hit.wav", 0.8)]
    g = _build_audio_filter(1, [0.0], None, -12, sfx, [2], video_dur=5.0)
    # no music -> vo_mix + sfx only
    assert "amix=inputs=2" in g
    assert "sidechaincompress" not in g


def test_filter_music_and_sfx_together() -> None:
    sfx = [(3.0, "hit.wav", 0.8)]
    g = _build_audio_filter(1, [0.0], 2, -12, sfx, [3], video_dur=8.0)
    assert "sidechaincompress" in g
    assert "[sfx0]" in g
    assert "amix=inputs=3" in g  # vo_mix + mus + sfx0


# --- SFX rarity validator ---------------------------------------------------

def _tl(sfx_list: list[str | None]) -> dict:
    return {
        "title": "T",
        "scenes": [
            {
                "id": i,
                "type": "content",
                "duration": 4.0,
                "sfx": s,
                "props": {"bg_image": "1.png"},
            }
            for i, s in enumerate(sfx_list)
        ],
    }


def test_sfx_rarity_clean_when_sparse() -> None:
    assert validate_sfx_rarity(_tl([None, "paper.wav", None])) == []
    assert validate_sfx_rarity(_tl(["a.wav", None, "b.wav"])) == []


def test_sfx_rarity_warns_over_two() -> None:
    w = validate_sfx_rarity(_tl(["a.wav", "b.wav", "c.wav"]))
    assert any("3 SFX" in x for x in w)


def test_sfx_rarity_warns_adjacent_repeat() -> None:
    w = validate_sfx_rarity(_tl(["a.wav", "a.wav"]))
    assert any("back-to-back" in x for x in w)


def test_sfx_rarity_ignores_non_adjacent_same() -> None:
    # same sfx separated by a silent scene is fine
    w = validate_sfx_rarity(_tl(["a.wav", None, "a.wav"]))
    assert not any("back-to-back" in x for x in w)
