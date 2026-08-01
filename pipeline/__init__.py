"""Shared path helpers and config loading for the video pipeline."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

PIPELINE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PIPELINE_ROOT.parent


def _load_dotenv(path: Path | None = None) -> None:
    """Load KEY=value lines from a gitignored .env into os.environ.

    Existing env vars win (a real export always overrides the file). Secrets stay
    out of source: .env is gitignored. This lets the pipeline + agents pick up
    API keys (MODELSCOPE_API_KEY, PEXELS_API_KEY, PIXABAY_API_KEY, VO_API_KEY)
    without any shell setup.
    """
    env_path = path or (PROJECT_ROOT / ".env")
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except OSError:
        pass


def _key_from_md(path: Path) -> str | None:
    """Extract a bare API key/token from a docs/API markdown note.

    These files are freeform ('pexel api key: XXX', a code sample with
    api_key = "ms-...", etc.). We scan for the first plausible token:
    an ms-... ModelScope token, a Pixabay uuid-ish key, or any long
    high-entropy run of key characters after a colon/equals/quote.
    """
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    import re

    # ModelScope token (ms-...) — most specific first.
    m = re.search(r"\bms-[0-9a-zA-Z-]{8,}\b", text)
    if m:
        return m.group(0)
    # Pixabay-style "<digits>-<hex>".
    m = re.search(r"\b\d{6,}-[0-9a-f]{16,}\b", text)
    if m:
        return m.group(0)
    # Generic "key: VALUE" / api_key = "VALUE" / 'key' : VALUE — a long token.
    m = re.search(r"[keyKEY]{3,}[^A-Za-z0-9]{0,6}[:=]?\s*[\"']?([A-Za-z0-9]{20,})", text)
    if m:
        return m.group(1)
    return None


def _load_api_docs_keys() -> dict[str, str]:
    """Read persistent keys from the gitignored docs/API/ folder (the user's
    canonical key store) → {ENV_VAR: key}. These are the source of truth across
    the project; .env is synced from them below so a stale .env can't shadow a
    rotated key."""
    mapping = {
        "PEXELS_API_KEY": ("pexels.md", "pexel.md"),
        "PIXABAY_API_KEY": ("pixabay.md",),
        "MODELSCOPE_API_KEY": ("modelscope.md",),
    }
    api_dir = PROJECT_ROOT / "docs" / "API"
    found: dict[str, str] = {}
    for env_var, names in mapping.items():
        for name in names:
            key = _key_from_md(api_dir / name)
            if key:
                found[env_var] = key
                break
    return found


def _sync_api_keys_to_env() -> None:
    """Make docs/API/*.md the persistent key source: load those keys into
    os.environ (overriding any stale .env value) and rewrite .env so it matches.
    Never commits — docs/API and .env are both gitignored."""
    keys = _load_api_docs_keys()
    if not keys:
        _load_dotenv()
        return
    # Real exported env vars always win; otherwise the docs/API key is canonical
    # (it overrides a stale .env).
    for var, key in keys.items():
        os.environ[var] = key
    # Rewrite .env to mirror the canonical keys (preserve any non-key lines).
    env_path = PROJECT_ROOT / ".env"
    header = "# Local API keys — gitignored, never commit. Synced from docs/API/ by pipeline/__init__.py.\n"
    lines = [f"{var}={key}" for var, key in keys.items()]
    try:
        env_path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass


_sync_api_keys_to_env()


def load_json(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def resolve_env(value: str) -> str:
    """Expand ${VAR} and {VAR} style env refs in config strings."""
    out = value
    for key, val in os.environ.items():
        out = out.replace(f"${{{key}}}", val).replace(f"{{{key}}}", val)
    return out


def ensure_dir(path: Path | str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def project_path(*parts: str) -> Path:
    return PROJECT_ROOT.joinpath(*parts)
