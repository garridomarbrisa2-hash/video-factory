import json
from pathlib import Path

import pytest

from studio import director


def test_visual_beats_split_long_narration_and_preserve_duration() -> None:
    plan = {
        "beats": [
            {
                "index": 0,
                "text": "Primeira ideia importante. Segunda ideia importante. Terceira ideia importante.",
                "vo_start": 2.0,
                "duration_sec": 30.0,
            }
        ]
    }
    beats = director.visual_beats(plan)
    assert len(beats) == 3
    assert beats[0]["vo_start"] == 2.0
    assert round(sum(item["duration"] for item in beats), 3) == 30.0


def test_generate_direction_writes_timed_plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "projects" / "bitcoin"
    project.mkdir(parents=True)
    (project / "Ep1.md").write_text(
        "language: pt-BR\ntarget_duration_min: 8\nglobal_style: history\nasset_mode: auto\n\n"
        "## Assunto\n\nA história do Bitcoin\n",
        encoding="utf-8",
    )
    (project / "Ep1_voice_plan.json").write_text(
        json.dumps(
            {
                "status": "approved",
                "total_vo_sec": 10.0,
                "beats": [
                    {
                        "index": 0,
                        "text": "O Bitcoin começou como uma proposta.",
                        "vo_start": 0,
                        "duration_sec": 10.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(director, "test_connection", lambda key: {"models": ["claude-sonnet-5"]})
    monkeypatch.setattr(
        director,
        "_request_message",
        lambda *args, **kwargs: {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "scenes": [
                                {
                                    "id": 1,
                                    "type": "intro",
                                    "layout": "keyword",
                                    "energy": "high",
                                    "text": "Bitcoin",
                                    "emphasis": "proposta",
                                    "source_route": "web_image",
                                    "keyword": "bitcoin whitepaper document",
                                    "fallback_prompt": "Close-up documental do whitepaper do Bitcoin.",
                                    "because": "Apresenta visualmente a origem citada.",
                                }
                            ]
                        }
                    ),
                }
            ],
            "usage": {"input_tokens": 10, "output_tokens": 20},
        },
    )

    result = director.generate_direction(tmp_path, "bitcoin", 1, "secret")
    saved = json.loads((project / "Ep1_director.json").read_text(encoding="utf-8"))
    assert result["scene_count"] == 1
    assert saved["notes"][0]["source_route"] == "web_image"
    assert (project / "Ep1_timeline.json").is_file()
