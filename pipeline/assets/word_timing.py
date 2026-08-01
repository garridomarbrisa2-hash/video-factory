"""Word-level timing for VO→visual sync (Phase 8, P1).

Why: the dead giveaway of an automated edit is text that pops on even spacing
while the narration drifts. A human editor keyframes text to the spoken word.
This module gives every VO line a per-word timestamp so scenes can land text,
punch, and shake on the actual syllables.

Two sources, in priority order:
  1. Native provider timestamps — many TTS APIs return word/phoneme timings.
     When the configured provider supplies them (see `word_timing` config), we
     parse them straight from the synthesis response. Most accurate; zero cost.
  2. Prosody-aware estimation — when the provider is audio-only, distribute the
     measured line duration across words by speaking weight (syllables, with a
     pause after punctuation). Not true alignment, but far closer to human
     cadence than even spacing, and it needs no ML deps or GPU.

The result is always scene-relative seconds: [[word, t_seconds], ...], cached
beside the audio so re-runs are free.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

# Rough syllable estimator — good enough to weight word speaking time.
_VOWEL_GROUP = re.compile(r"[aeiouyáéíóúàèìòùâêîôûäëïöü]+", re.IGNORECASE)


def _syllables(word: str) -> int:
    w = re.sub(r"[^a-záéíóúàèìòùâêîôûäëïöü]", "", word.lower())
    if not w:
        return 0
    groups = _VOWEL_GROUP.findall(w)
    n = max(1, len(groups))
    # silent trailing 'e'
    if w.endswith("e") and n > 1 and not w.endswith(("le", "ee", "ye")):
        n -= 1
    return max(1, n)


def _split_words(text: str) -> list[str]:
    return [w for w in re.split(r"\s+", text.strip()) if w]


def _pause_after(word: str) -> float:
    """Extra dwell (seconds) after a word, from its trailing punctuation.

    Mirrors the style's pause-markers: em-dash / ellipsis breathe longest,
    sentence end next, clause punctuation least.
    """
    if word.endswith(("...", "…")):
        return 0.55
    if word.endswith(("—", "--", "–")):
        return 0.45
    if word.endswith((".", "!", "?")):
        return 0.32
    if word.endswith((",", ";", ":")):
        return 0.18
    return 0.0


def estimate_word_times(text: str, duration_sec: float) -> list[list[Any]]:
    """Distribute `duration_sec` across words by speaking weight.

    Returns [[word, t_seconds], ...] where t is each word's onset, relative to
    the start of THIS line (scene-relative once the scene owns the line).
    Weights = syllables; punctuation adds a trailing pause. Scaled so the last
    word ends exactly at duration_sec.
    """
    words = _split_words(text)
    if not words:
        return []
    weights = []
    for w in words:
        syl = _syllables(w)
        weights.append(syl + _pause_after(w) * 3.0)  # pause ≈ 3 syllables of time
    total = sum(weights) or 1.0
    # Reserve a tiny tail so the last word doesn't end flush on the cut.
    usable = max(0.05, duration_sec * 0.985)
    per = usable / total
    out: list[list[Any]] = []
    t = 0.0
    for w, wt in zip(words, weights):
        out.append([w, round(t, 3)])
        t += wt * per
    return out


def _word_cache_path(audio_path: Path) -> Path:
    return audio_path.with_suffix(audio_path.suffix + ".words.json")


def load_cached_word_times(audio_path: Path) -> list[list[Any]] | None:
    p = _word_cache_path(audio_path)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, list) and data and isinstance(data[0], list):
                return data
        except Exception:
            return None
    return None


def save_word_times(audio_path: Path, word_times: list[list[Any]]) -> None:
    p = _word_cache_path(audio_path)
    p.write_text(json.dumps(word_times), encoding="utf-8")


def parse_native_word_times(payload: Any, cfg: dict[str, Any]) -> list[list[Any]] | None:
    """Extract [[word, t], ...] from a provider's JSON response, using the
    `word_timing` config block:

      "word_timing": {
        "path": "words",                 # dot path to the word list
        "word_key": "word",              # key holding the word text
        "start_key": "start",            # key holding onset seconds
        "time_unit": "s"                 # "s" | "ms" (default s)
      }

    Returns None when not configured or the payload doesn't match — callers
    then fall back to estimation.
    """
    spec = cfg.get("word_timing")
    if not spec or not isinstance(payload, (dict, list)):
        return None
    node: Any = payload
    for part in str(spec.get("path", "")).split("."):
        if not part:
            continue
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    if not isinstance(node, list):
        return None
    wkey = spec.get("word_key", "word")
    skey = spec.get("start_key", "start")
    unit = spec.get("time_unit", "s")
    scale = 0.001 if unit == "ms" else 1.0
    out: list[list[Any]] = []
    for item in node:
        if not isinstance(item, dict) or wkey not in item or skey not in item:
            return None
        out.append([str(item[wkey]), round(float(item[skey]) * scale, 3)])
    return out or None


def resolve_word_times(
    text: str,
    audio_path: Path,
    duration_sec: float,
    native_payload: Any = None,
    provider_cfg: dict[str, Any] | None = None,
) -> list[list[Any]]:
    """The single entry point. Cache → native → estimate."""
    cached = load_cached_word_times(audio_path)
    if cached is not None:
        return cached
    if native_payload is not None and provider_cfg is not None:
        native = parse_native_word_times(native_payload, provider_cfg)
        if native:
            save_word_times(audio_path, native)
            return native
    est = estimate_word_times(text, duration_sec)
    save_word_times(audio_path, est)
    return est


def emphasis_word_time(
    word_times: list[list[Any]],
    emphasis: str | None,
) -> float | None:
    """Onset (seconds) of the emphasis word/phrase within the line — the beat a
    punch or shake should land on. Matches the first word of the phrase,
    case-insensitive, ignoring punctuation. None when not found."""
    if not emphasis or not word_times:
        return None
    target = _split_words(emphasis)
    if not target:
        return None

    def norm(w: str) -> str:
        return re.sub(r"[^a-z0-9]", "", w.lower())

    first = norm(target[0])
    for w, t in word_times:
        if norm(str(w)) == first:
            return float(t)
    return None
