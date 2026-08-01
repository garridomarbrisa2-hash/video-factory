import pytest

from pipeline.orchestrator import validate_total_vo_duration


def test_total_vo_duration_accepts_production_range() -> None:
    assert validate_total_vo_duration({"scenes": [{"vo_duration": 481}, {"vo_duration": 10}]}) == 491


@pytest.mark.parametrize("seconds", [479, 1201])
def test_total_vo_duration_requires_script_adjustment(seconds: float) -> None:
    with pytest.raises(ValueError, match="script must be adjusted"):
        validate_total_vo_duration({"scenes": [{"vo_duration": seconds}]})
