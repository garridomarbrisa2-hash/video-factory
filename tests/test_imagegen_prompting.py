"""Model-aware still-prompt guardrails; no network or image generation."""

from __future__ import annotations

import pytest

from pipeline.assets.imagegen import _NO_ARTIFACTS, image_prompt


def test_image_prompt_requests_one_clean_editorial_frame() -> None:
    prompt = image_prompt("  factory workers  loading   sacks at dawn ")

    assert prompt.startswith("factory workers loading sacks at dawn.")
    assert "Single 16:9 scene" in prompt
    assert "one clear subject" in prompt
    assert "No text, watermark, logo, collage, or duplicate subjects" in prompt


def test_z_image_negative_prompt_excludes_layout_artifacts() -> None:
    assert "watermark" in _NO_ARTIFACTS
    assert "collage" in _NO_ARTIFACTS
    assert "malformed anatomy" in _NO_ARTIFACTS


def test_image_prompt_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        image_prompt("  ")


def test_image_prompt_caps_turbo_model_complexity() -> None:
    prompt = image_prompt(
        "subject, action, place, period, light, medium, extra prop, second crowd, third event"
    )

    assert "medium." in prompt
    assert "extra prop" not in prompt
