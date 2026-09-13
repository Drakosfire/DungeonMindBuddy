from __future__ import annotations

from types import SimpleNamespace

from extraction_lab.campaign_memory_output_contract_audit import build_output_contract_audit
from src.ingestion.entity_extractor import (
    _experiment_request_kwargs,
    _usage_dict_from_openai_response,
)
from src.ingestion.fact_extractor import (
    ExtractedFact,
    FactValueOutput,
    PayloadLeanExtractedFact,
    _build_fact_record,
    _build_fact_system_prompt,
    _compute_fact_id,
    _standardize_fact_payload,
)


PREREGISTERED_TARGET_LANGUAGE = (
    "weak to fire",
    "resistant to poison",
    "Ironveil Warehouse",
    "Hesta Bramblewood",
    "Hunter's Mark",
    "Mireward",
    "Karsemine",
    "Orik",
    "Orric",
    "Thrin",
)


def test_payload_lean_prompt_preserves_decisive_answers_without_gold_language() -> None:
    prompt = _build_fact_system_prompt("payload_lean_v1")
    assert "preserve the answer itself" in prompt
    assert "mere fact that learning" in prompt
    for phrase in PREREGISTERED_TARGET_LANGUAGE:
        assert phrase not in prompt
    default = _build_fact_system_prompt("default")
    assert "DECISIVE PAYLOAD RULE" not in default
    assert "fact_id" in default
    assert "DECISIVE PAYLOAD RULE" in prompt
    assert "fact_id" not in prompt


def test_payload_lean_schema_removes_only_fact_id_and_runtime_restores_deterministic_id(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DMB_FACT_EXTRACTION_CONTRACT", "payload_lean_v1")
    payload = {
        "facts": [
            {
                "subject_entity_id": "karsemine",
                "attribute": "event_outcome",
                "value": {"kind": "scalar", "label": "Concrete answer", "normalized": None},
            }
        ]
    }
    standardized = _standardize_fact_payload(payload, batched=False)
    expected = _compute_fact_id("karsemine", "event_outcome", "Concrete answer")
    assert standardized["facts"][0]["fact_id"] == expected
    again = _standardize_fact_payload(payload, batched=False)
    assert again["facts"][0]["fact_id"] == expected
    record = _build_fact_record(
        ExtractedFact(
            fact_id="model-emitted-ignored",
            subject_entity_id="karsemine",
            attribute="event_outcome",
            value=FactValueOutput(kind="scalar", label="Concrete answer"),
        ),
        evidence_unit={"evidence_id": "ev1"},
        truth_state="OBSERVED",
        source_authority="observed_recap",
        entity_id_set={"karsemine"},
    )
    assert record is not None
    assert record["fact_id"] == expected
    audit = build_output_contract_audit()
    assert audit["removed_model_fields"] == ["fact_id"]
    assert "fact_id" not in PayloadLeanExtractedFact.model_json_schema()["properties"]
    assert next(row for row in audit["fact_fields"] if row["field"] == "fact_id")[
        "classification"
    ] == "DERIVED_DETERMINISTIC"


def test_default_fact_contract_still_requires_model_fact_id(monkeypatch) -> None:
    monkeypatch.delenv("DMB_FACT_EXTRACTION_CONTRACT", raising=False)
    prompt = _build_fact_system_prompt()
    assert "DECISIVE PAYLOAD RULE" not in prompt
    assert "fact_id" in ExtractedFact.model_json_schema()["properties"]


def test_usage_telemetry_preserves_reasoning_detail_and_truthful_absence() -> None:
    present = SimpleNamespace(
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=8,
            input_tokens_details=SimpleNamespace(cached_tokens=3),
            output_tokens_details=SimpleNamespace(reasoning_tokens=5),
        )
    )
    usage = _usage_dict_from_openai_response(present)
    assert usage["reasoning_tokens"] == 5
    absent = SimpleNamespace(
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=8,
            input_tokens_details=None,
            output_tokens_details=None,
        )
    )
    assert _usage_dict_from_openai_response(absent)["reasoning_tokens"] is None
    zero = SimpleNamespace(
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=8,
            input_tokens_details=None,
            output_tokens_details=SimpleNamespace(reasoning_tokens=0),
        )
    )
    assert _usage_dict_from_openai_response(zero)["reasoning_tokens"] == 0


def test_experiment_request_kwargs_set_equivalent_flex_and_medium_reasoning(monkeypatch) -> None:
    monkeypatch.setenv("DMB_OPENAI_SERVICE_TIER", "flex")
    monkeypatch.setenv("DMB_OPENAI_REASONING_EFFORT", "medium")
    assert _experiment_request_kwargs() == {
        "service_tier": "flex",
        "reasoning": {"effort": "medium"},
    }
    monkeypatch.delenv("DMB_OPENAI_SERVICE_TIER", raising=False)
    monkeypatch.delenv("DMB_OPENAI_REASONING_EFFORT", raising=False)
    assert _experiment_request_kwargs() == {}
