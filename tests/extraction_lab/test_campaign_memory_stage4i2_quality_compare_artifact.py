import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "extraction_lab" / "campaign_memory_stage4i2_three_arm_quality_compare.json"
REPORT = ROOT / "extraction_lab" / "campaign_memory_stage4i2_three_arm_quality_compare.md"


def test_three_arm_quality_compare_artifact_is_committed_and_unevaluated() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert payload["schema"] == "dmb_stage4i2_three_arm_quality_compare_v1"
    assert payload["evaluator_llm"] is False
    assert set(payload["arms"]) == {
        "deepseek-none",
        "deepseek-low",
        "luna-flex-low",
    }
    assert [row["id"] for row in payload["objects"]] == [
        "brin",
        "orik",
        "karsemine",
        "mireward",
        "hesta",
        "thrin",
        "tripod",
        "refugees",
    ]
    report = REPORT.read_text(encoding="utf-8")
    assert "NOT_EVALUATED" in report
    assert "Do not freeze" in report or "do not freeze" in report.lower()
