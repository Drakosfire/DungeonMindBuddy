from __future__ import annotations

import hashlib
import json
from typing import Any

from src.ingestion.fact_extractor import (
    PayloadLeanBatchedFactExtractionResult,
    PayloadLeanExtractedFact,
    _build_fact_system_prompt,
)


FACT_FIELD_AUDIT: list[dict[str, Any]] = [
    {
        "field": "fact_id",
        "schema_location": "facts[].fact_id",
        "classification": "DERIVED_DETERMINISTIC",
        "consumer": "fact persistence",
        "destination": "facts[].fact_id",
        "replacement": "_compute_fact_id(subject_entity_id, attribute, value.label)",
        "proof": "tests/extraction_lab/test_campaign_memory_exploratory_output.py",
    },
    {
        "field": "subject_entity_id",
        "schema_location": "facts[].subject_entity_id",
        "classification": "SEMANTIC_REQUIRED",
        "consumer": "resolver/persistence",
        "destination": "facts[].subject_entity_id",
        "replacement": None,
        "proof": "provided entity identity selects fact owner",
    },
    {
        "field": "attribute",
        "schema_location": "facts[].attribute",
        "classification": "SEMANTIC_REQUIRED",
        "consumer": "fact projection/scorer",
        "destination": "facts[].attribute",
        "replacement": None,
        "proof": "attribute is not derivable from free text",
    },
    {
        "field": "value.kind",
        "schema_location": "facts[].value.kind",
        "classification": "SEMANTIC_REQUIRED",
        "consumer": "fact schema/projection",
        "destination": "facts[].value.kind",
        "replacement": None,
        "proof": "controls scalar/state/ref/set/interpretive semantics",
    },
    {
        "field": "value.label",
        "schema_location": "facts[].value.label",
        "classification": "SEMANTIC_REQUIRED",
        "consumer": "human/scorer/persistence",
        "destination": "facts[].value.label",
        "replacement": None,
        "proof": "carries decisive source-grounded payload",
    },
    {
        "field": "value.normalized",
        "schema_location": "facts[].value.normalized",
        "classification": "SEMANTIC_REQUIRED",
        "consumer": "dedup/retrieval",
        "destination": "facts[].value.normalized",
        "replacement": None,
        "proof": "current normalization is semantic and not mechanically equivalent",
    },
    {
        "field": "value.entity_id",
        "schema_location": "facts[].value.entity_id",
        "classification": "SEMANTIC_REQUIRED",
        "consumer": "entity-reference projection",
        "destination": "facts[].value.entity_id",
        "replacement": None,
        "proof": "selects referenced entity",
    },
    {
        "field": "value.values",
        "schema_location": "facts[].value.values",
        "classification": "SEMANTIC_REQUIRED",
        "consumer": "set-value projection",
        "destination": "facts[].value.values",
        "replacement": None,
        "proof": "enumerated members cannot be reconstructed from normalized slug",
    },
    {
        "field": "value.interpretation_level",
        "schema_location": "facts[].value.interpretation_level",
        "classification": "AUTHORITY_SENSITIVE",
        "consumer": "interpretive fact projection",
        "destination": "facts[].value.interpretation_level",
        "replacement": None,
        "proof": "distinguishes assertion from inference",
    },
    {
        "field": "value.strength",
        "schema_location": "facts[].value.strength",
        "classification": "AUTHORITY_SENSITIVE",
        "consumer": "interpretive fact projection",
        "destination": "facts[].value.strength",
        "replacement": None,
        "proof": "expresses inference strength",
    },
]


def build_output_contract_audit() -> dict[str, Any]:
    schema = PayloadLeanBatchedFactExtractionResult.model_json_schema()
    lean_fact = PayloadLeanExtractedFact.model_json_schema()
    prompt = _build_fact_system_prompt("payload_lean_v1")
    default_prompt = _build_fact_system_prompt("default")
    return {
        "schema": "dmb_campaign_memory_output_contract_audit_v1",
        "contract": "payload_lean_v1",
        "fact_fields": FACT_FIELD_AUDIT,
        "removed_model_fields": ["fact_id"],
        "entity_contract_changed": False,
        "lean_model_fact_properties": sorted(lean_fact.get("properties", {}).keys()),
        "structured_output_schema_sha256": hashlib.sha256(
            json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "default_prompt_sha256": hashlib.sha256(default_prompt.encode()).hexdigest(),
    }
