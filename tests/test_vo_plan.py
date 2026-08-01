from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline.vo_plan import build_vo_plan, script_paragraphs


def test_script_paragraphs_excludes_markdown_metadata() -> None:
    text = "# Title\n\nglobal_style: ledger\n\n## HOOK\n\nFirst line.\n\nSecond line.\n\nStyle: ledger\nTone: sober\n"
    assert script_paragraphs(text) == ["First line.", "Second line."]


def test_build_vo_plan_writes_measured_plan(tmp_path: Path) -> None:
    script = tmp_path / "script.md"
    output = tmp_path / "vo.json"
    script.write_text("# T\n\nNarration.\n", encoding="utf-8")
    plan = {"beats": [{"text": "Narration."}], "total_vo_sec": 500.0}
    with patch("pipeline.vo_plan.synthesize_script_plan", return_value=plan):
        assert build_vo_plan(script, output) == output
    assert '"total_vo_sec": 500.0' in output.read_text(encoding="utf-8")


def test_build_vo_plan_blocks_short_script(tmp_path: Path) -> None:
    script = tmp_path / "script.md"
    script.write_text("Narration.\n", encoding="utf-8")
    with patch("pipeline.vo_plan.synthesize_script_plan", return_value={"beats": [], "total_vo_sec": 479}):
        with pytest.raises(ValueError, match="8-20"):
            build_vo_plan(script, tmp_path / "vo.json")
