"""Pluggable voiceover synthesis. User configures provider in pipeline/config/vo.json."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Protocol

import httpx

from pipeline import ensure_dir, load_json, project_path, resolve_env
from pipeline.assets.word_timing import resolve_word_times


class VOProvider(Protocol):
    def synthesize(self, text: str, voice: str | None = None) -> Path:
        """Return path to cached audio file for this text+voice."""
        ...

    def synthesize_with_meta(self, text: str, voice: str | None = None) -> tuple[Path, Any]:
        """Return (audio path, raw provider payload for word-timing) — optional.
        Default falls back to synthesize() + None payload (audio-only)."""
        return self.synthesize(text, voice), None


def _cache_key(text: str, voice: str, provider: str, model: str = "") -> str:
    raw = f"{provider}|{model}|{voice}|{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def _expand_template(obj: Any, mapping: dict[str, str]) -> Any:
    if isinstance(obj, str):
        out = resolve_env(obj)
        for k, v in mapping.items():
            out = out.replace(f"{{{k}}}", v)
        return out
    if isinstance(obj, dict):
        return {k: _expand_template(v, mapping) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_template(v, mapping) for v in obj]
    return obj


class CustomHttpProvider:
    def __init__(self, cfg: dict[str, Any], cache_dir: Path) -> None:
        self.cfg = cfg
        self.cache_dir = ensure_dir(cache_dir)
        self.ext = cfg.get("output_ext", "mp3")

    def synthesize(self, text: str, voice: str | None = None) -> Path:
        path, _ = self.synthesize_with_meta(text, voice)
        return path

    def synthesize_with_meta(self, text: str, voice: str | None = None) -> tuple[Path, Any]:
        """Synthesize + return the raw JSON payload so word-timing can be parsed
        natively when the TTS API returns it (response_type=json_with_timings).
        Falls back to (audio, None) for plain audio responses."""
        voice = voice or self.cfg.get("voice", "default")
        key = _cache_key(text, voice, "custom_http", self.cfg.get("endpoint", ""))
        out = self.cache_dir / f"{key}.{self.ext}"
        if out.exists() and out.stat().st_size > 0:
            return out, None

        mapping = {"text": text, "voice": voice}
        endpoint = _expand_template(self.cfg["endpoint"], mapping)
        method = self.cfg.get("method", "POST").upper()
        headers = _expand_template(self.cfg.get("headers", {}), mapping)
        body = _expand_template(self.cfg.get("body", {"text": text}), mapping)

        api_key_env = self.cfg.get("api_key_env")
        if api_key_env and api_key_env in os.environ:
            # already expanded via resolve_env in headers
            pass

        with httpx.Client(timeout=120.0) as client:
            if method == "GET":
                resp = client.get(endpoint, headers=headers, params=body if isinstance(body, dict) else None)
            else:
                resp = client.request(method, endpoint, headers=headers, json=body)
            resp.raise_for_status()

        response_type = self.cfg.get("response_type", "audio_binary")
        if response_type == "audio_binary":
            out.write_bytes(resp.content)
            return out, None
        if response_type == "json_url":
            data = resp.json()
            path_key = self.cfg.get("audio_path_in_response", "url")
            url = data
            for part in path_key.split("."):
                url = url[part]
            audio = httpx.get(url, timeout=120.0)
            audio.raise_for_status()
            out.write_bytes(audio.content)
            # The JSON envelope may carry word timings alongside the URL.
            return out, data
        if response_type == "json_with_timings":
            # JSON body holds both the audio (URL or base64) and word timings.
            data = resp.json()
            url = data
            for part in self.cfg.get("audio_path_in_response", "audio_url").split("."):
                url = url[part]
            audio = httpx.get(url, timeout=120.0)
            audio.raise_for_status()
            out.write_bytes(audio.content)
            return out, data
        raise ValueError(f"Unknown response_type: {response_type}")


class GradioQwenProvider:
    """Qwen3-TTS served from a Gradio app (e.g. a Google Colab deployment).

    Colab `*.gradio.live` base URLs are EPHEMERAL — a new one is issued every
    session — so the base URL is read from config (`base_url`) and may carry an
    env placeholder (resolved via resolve_env, e.g. "${VO_ENDPOINT}"). Update
    vo.json (or set VO_ENDPOINT) each time the Colab tunnel restarts; nothing
    else changes.

    Flow (Gradio async API):
      1. POST {base}/gradio_api/call/{fn}           -> {"event_id": ...}
      2. GET  {base}/gradio_api/call/{fn}/{event_id} (SSE) -> 'data: [{...FileData...}]'
      3. download FileData.url (or base + /gradio_api/file={path}) -> audio bytes
    """

    def __init__(self, cfg: dict[str, Any], cache_dir: Path) -> None:
        self.cfg = cfg
        self.cache_dir = ensure_dir(cache_dir)
        self.ext = cfg.get("output_ext", "wav")
        self.fn = cfg.get("api_name", "v2/voice_design")
        self.timeout = float(cfg.get("timeout", 300.0))
        self.poll_interval = float(cfg.get("poll_interval", 1.5))

    def _base(self) -> str:
        raw = self.cfg.get("base_url") or os.environ.get("VO_ENDPOINT") or ""
        base = resolve_env(str(raw)).rstrip("/")
        if not base:
            raise ValueError(
                "gradio_qwen.base_url not set. Point vo.json providers.gradio_qwen.base_url "
                "at your Colab Gradio URL (https://<hash>.gradio.live) or set VO_ENDPOINT."
            )
        return base

    def _payload(self, text: str, voice: str | None) -> dict[str, Any]:
        fn = self.fn
        if fn.endswith("voice_design"):
            # voice design: the 'voice' slot carries the free-text voice description.
            desc = voice or self.cfg.get("voice_description") or "natural, clear narrator"
            return {"data": [text, desc]}
        if fn.endswith("custom_voice"):
            name = (voice or self.cfg.get("voice_name") or "serena").lower()
            return {"data": [text, name, self.cfg.get("instruction", "")]}
        if fn.endswith("voice_clone"):
            raise ValueError(
                "voice_clone needs a reference_audio upload — not supported by this provider. "
                "Use api_name v2/voice_design (default) or v2/custom_voice."
            )
        # Fallback: send the whole configured body template expanded.
        mapping = {"text": text, "voice": voice or ""}
        return _expand_template(self.cfg.get("body", {"text": text}), mapping)

    def synthesize(self, text: str, voice: str | None = None) -> Path:
        path, _ = self.synthesize_with_meta(text, voice)
        return path

    def synthesize_with_meta(self, text: str, voice: str | None = None) -> tuple[Path, Any]:
        voice_key = voice or self.cfg.get("voice_description") or self.cfg.get("voice_name") or "default"
        key = _cache_key(text, voice_key, "gradio_qwen", self.fn + "|" + self._base())
        out = self.cache_dir / f"{key}.{self.ext}"
        if out.exists() and out.stat().st_size > 0:
            return out, None

        base = self._base()
        payload = self._payload(text, voice)
        with httpx.Client(timeout=self.timeout) as client:
            # 1) submit
            r = client.post(f"{base}/gradio_api/call/{self.fn}", json=payload)
            r.raise_for_status()
            event_id = r.json()["event_id"]
            # 2) poll SSE until 'event: complete' (or error)
            filedata = self._poll(client, f"{base}/gradio_api/call/{self.fn}/{event_id}")
            # 3) download audio
            url = filedata.get("url") or f"{base}/gradio_api/file={filedata['path']}"
            audio = client.get(url)
            audio.raise_for_status()
            out.write_bytes(audio.content)
        return out, None

    def _poll(self, client: httpx.Client, url: str) -> dict[str, Any]:
        import time

        deadline = time.time() + self.timeout
        while time.time() < deadline:
            with client.stream("GET", url) as resp:
                resp.raise_for_status()
                event = ""
                for line in resp.iter_lines():
                    line = line.strip()
                    if line.startswith("event:"):
                        event = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        data = line.split(":", 1)[1].strip()
                        if event in ("complete", "error") and data and data != "null":
                            if event == "error":
                                raise RuntimeError(f"gradio_qwen error: {data}")
                            arr = json.loads(data)
                            filedata = arr[0] if isinstance(arr, list) else arr
                            if isinstance(filedata, dict) and (filedata.get("url") or filedata.get("path")):
                                return filedata
                            raise RuntimeError(f"gradio_qwen: unexpected result payload: {data}")
            time.sleep(self.poll_interval)
        raise TimeoutError(f"gradio_qwen: no result within {self.timeout}s from {url}")


class ModalQwenProvider:
    """Qwen3-TTS served as a direct-download Modal web endpoint.

    Config lives in vo.json providers.modal_qwen; the endpoint URL is read from
    the gitignored key store docs/API/modal-qwen3tts.md (first https URL in the
    file), which may be overridden by the VO_ENDPOINT env var or a config
    "endpoint" value. Request body: {"text": ..., "voice_id": ..., "language": ...}
    — the response is the raw audio file (audio/wav).
    """

    def __init__(self, cfg: dict[str, Any], cache_dir: Path) -> None:
        self.cfg = cfg
        self.cache_dir = ensure_dir(cache_dir)
        self.ext = cfg.get("output_ext", "wav")
        self.timeout = float(cfg.get("timeout", 300.0))

    def _endpoint(self) -> str:
        url = os.environ.get("VO_ENDPOINT") or str(self.cfg.get("endpoint") or "")
        if not url:
            note = project_path("docs", "API", "modal-qwen3tts.md")
            if note.exists():
                import re

                m = re.search(r"https://\S+", note.read_text(encoding="utf-8", errors="ignore"))
                if m:
                    url = m.group(0).rstrip(".,;)")
        url = resolve_env(url).strip()
        if not url:
            raise ValueError(
                "modal_qwen endpoint not set. Put the Modal URL in "
                "docs/API/modal-qwen3tts.md (or set VO_ENDPOINT / providers.modal_qwen.endpoint)."
            )
        return url

    def synthesize(self, text: str, voice: str | None = None) -> Path:
        path, _ = self.synthesize_with_meta(text, voice)
        return path

    def synthesize_with_meta(self, text: str, voice: str | None = None) -> tuple[Path, Any]:
        voice_id = voice or self.cfg.get("voice_id", "male-narrator1")
        language = self.cfg.get("language", "english")
        endpoint = self._endpoint()
        key = _cache_key(text, voice_id, "modal_qwen", endpoint)
        out = self.cache_dir / f"{key}.{self.ext}"
        if out.exists() and out.stat().st_size > 0:
            return out, None

        body = {"text": text, "voice_id": voice_id, "language": language}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(endpoint, json=body)
            resp.raise_for_status()
        if not resp.content:
            raise RuntimeError("modal_qwen returned an empty audio body")
        out.write_bytes(resp.content)
        return out, None


class CustomCliProvider:
    def __init__(self, cfg: dict[str, Any], cache_dir: Path) -> None:
        self.cfg = cfg
        self.cache_dir = ensure_dir(cache_dir)
        self.ext = cfg.get("output_ext", "wav")

    def synthesize(self, text: str, voice: str | None = None) -> Path:
        voice = voice or self.cfg.get("voice", "default")
        key = _cache_key(text, voice, "custom_cli", " ".join(self.cfg.get("command", [])))
        out = self.cache_dir / f"{key}.{self.ext}"
        if out.exists() and out.stat().st_size > 0:
            return out

        mapping = {"text": text, "voice": voice, "output_path": str(out)}
        cmd = _expand_template(self.cfg["command"], mapping)
        if not isinstance(cmd, list):
            raise ValueError("custom_cli.command must be a list of strings")

        stdin_mode = self.cfg.get("stdin")
        if stdin_mode == "text":
            proc = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                check=False,
            )
        else:
            proc = subprocess.run(cmd, capture_output=True, check=False)

        if proc.returncode != 0:
            raise RuntimeError(
                f"VO CLI failed ({proc.returncode}): {proc.stderr.decode('utf-8', errors='replace')}"
            )
        if not out.exists() or out.stat().st_size == 0:
            # Some CLIs write to stdout
            if proc.stdout:
                out.write_bytes(proc.stdout)
            else:
                raise RuntimeError(f"VO CLI produced no output at {out}")
        return out


def load_vo_provider(config_path: str | Path | None = None) -> VOProvider:
    path = Path(config_path) if config_path else project_path("pipeline", "config", "vo.json")
    cfg = load_json(path)
    provider_name = cfg.get("provider", "custom_http")
    providers = cfg.get("providers", {})
    if provider_name not in providers:
        raise KeyError(
            f"VO provider '{provider_name}' not in config.providers. "
            f"Available: {list(providers.keys())}. Edit pipeline/config/vo.json."
        )
    pcfg = providers[provider_name]
    cache_dir = ensure_dir(cfg.get("cache_dir", "pipeline/assets/cache/vo"))
    ptype = pcfg.get("type", provider_name)

    if ptype == "custom_http":
        return CustomHttpProvider(pcfg, cache_dir)
    if ptype == "custom_cli":
        return CustomCliProvider(pcfg, cache_dir)
    if ptype == "gradio_qwen":
        return GradioQwenProvider(pcfg, cache_dir)
    if ptype == "modal_qwen":
        return ModalQwenProvider(pcfg, cache_dir)
    raise ValueError(
        f"Unsupported VO provider type '{ptype}'. "
        "Only custom_http, custom_cli, gradio_qwen and modal_qwen are supported. "
        "Configure your TTS endpoint/CLI in pipeline/config/vo.json."
    )


def synthesize_lines(
    lines: list[dict[str, Any]],
    provider: VOProvider | None = None,
    default_voice: str | None = None,
) -> list[dict[str, Any]]:
    """
    lines: [{id, text, voice?}]
    returns: [{id, text, voice, audio_path, duration_sec, word_times}]

    word_times is [[word, t_seconds], ...] relative to the START OF THIS LINE —
    native from the provider when available, else prosody-estimated. The
    orchestrator maps each line to its scene, so these are already scene-relative.
    """
    provider = provider or load_vo_provider()
    provider_cfg = getattr(provider, "cfg", None)
    results: list[dict[str, Any]] = []
    for line in lines:
        text = line["text"]
        voice = line.get("voice") or default_voice
        if hasattr(provider, "synthesize_with_meta"):
            audio_path, payload = provider.synthesize_with_meta(text, voice)
        else:
            audio_path, payload = provider.synthesize(text, voice), None
        duration = probe_duration(audio_path)
        word_times = resolve_word_times(
            text, audio_path, duration, native_payload=payload, provider_cfg=provider_cfg
        )
        results.append(
            {
                "id": line.get("id"),
                "text": text,
                "voice": voice,
                "audio_path": str(audio_path),
                "duration_sec": duration,
                "word_times": word_times,
            }
        )
    return results


def synthesize_script_plan(
    paragraphs: list[str],
    provider: VOProvider | None = None,
    default_voice: str | None = None,
    min_beat_sec: float = 2.0,
    max_beat_sec: float = 14.0,
) -> dict[str, Any]:
    """VO-FIRST planning (Ep1 pilot fix): synthesize the WHOLE script up front —
    before scenes are authored — so the video's timing is driven by the measured
    VO, not by a pre-guessed 140wpm estimate.

    paragraphs: the script split into narration paragraphs (one thought each).
    Returns a plan the director uses to build scenes that FIT the VO:
      {
        "beats": [{index, text, vo_start, vo_end, duration_sec, audio_path,
                   word_times, suggested_split}],
        "total_vo_sec": float,
      }
    Each beat carries its audio so the downstream per-scene stage can reuse the
    file (no re-synthesis) and pull exact word_times for VO→visual sync.

    suggested_split flags a paragraph whose spoken length exceeds max_beat_sec —
    a cue for the director to break it into two scenes (a cut keeps retention)."""
    provider = provider or load_vo_provider()
    provider_cfg = getattr(provider, "cfg", None)
    beats: list[dict[str, Any]] = []
    t = 0.0
    for i, text in enumerate(paragraphs):
        text = (text or "").strip()
        if not text:
            continue
        if hasattr(provider, "synthesize_with_meta"):
            audio_path, payload = provider.synthesize_with_meta(text, default_voice)
        else:
            audio_path, payload = provider.synthesize(text, default_voice), None
        duration = probe_duration(audio_path)
        word_times = resolve_word_times(
            text, audio_path, duration, native_payload=payload, provider_cfg=provider_cfg
        )
        beats.append(
            {
                "index": i,
                "text": text,
                "vo_start": round(t, 3),
                "vo_end": round(t + duration, 3),
                "duration_sec": duration,
                "audio_path": str(audio_path),
                "word_times": word_times,
                "suggested_split": duration > max_beat_sec,
            }
        )
        t += duration
    return {"beats": beats, "total_vo_sec": round(t, 3)}


def probe_duration(path: Path | str) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return float(out)
