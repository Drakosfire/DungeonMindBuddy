from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from extraction_lab.anchor_schema import load_entity_anchors, load_fact_anchors
from extraction_lab.campaign_memory_benchmark import (
    ROOT,
    CampaignMemoryBenchmark,
    validate_campaign_memory_benchmark,
)


SCHEMA = "dmb_campaign_memory_temporal_intent_v1"
REQUIRED_EXPECTATIONS = {
    "brin_cook_from_edge_background",
    "brin_refugee_leader_state",
    "orric_mayor_state",
    "brin_refugee_arrival_event",
    "karsemine_tripod_fire_weakness_knowledge",
    "mireward_siege_pressure_state",
    "mireward_north_gate_battle_state",
}
SOURCE_SESSIONS: dict[str, int | None] = {
    "Longmont Campaign/Campaign 2/Session Recaps/Session 23 - Mireward Gate.md": 23,
    "Longmont Campaign/Campaign 2/Session Recaps/Session 24 - Mireward Gate Battle.md": 24,
    "Longmont Campaign/Campaign 2/Session Recaps/Session 25 - Mireward Gate Battle II.md": 25,
    "Elderwyld/Cities and Towns/Mireward/Mireward_PLACE_BUILD_SCAFFOLD.md": None,
    "Elderwyld/Cities and Towns/Mireward/NPCs/brin_holloway/character_seed.md": None,
    "Elderwyld/Cities and Towns/Mireward/NPCs/orric_tane/character_seed.md": None,
    "Longmont Campaign/Campaign 2/PCs/karsemine/timeline.md": None,
}


class TruthWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_session: int | None
    end_session: int | None


class TemporalEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_file: str = Field(min_length=1)
    source_session: int | None
    source_text_marker: str = Field(min_length=1)
    role: Literal["supports", "confirms", "starts", "ends"]

    @field_validator("source_file", "source_text_marker")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class TemporalExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectation_id: str = Field(min_length=1)
    subject_anchor: str = Field(min_length=1)
    fact_anchor: str | None
    identity_expectation_refs: list[str]
    temporal_kind: Literal["background", "event", "state", "knowledge_acquisition"]
    persistence: Literal["historical", "enduring", "until_changed", "bounded"]
    truth_window: TruthWindow
    evidence: list[TemporalEvidence] = Field(min_length=1)
    intent: str = Field(min_length=1)

    @field_validator("expectation_id", "subject_anchor", "intent")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("fact_anchor")
    @classmethod
    def reject_blank_fact(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("fact_anchor must be null or non-blank")
        return value.strip() if value is not None else None

    @field_validator("identity_expectation_refs")
    @classmethod
    def unique_identity_refs(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("identity expectation refs must not be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("duplicate identity expectation ref")
        return normalized


class TemporalIntentOverlay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_name: Literal[SCHEMA] = Field(alias="schema", serialization_alias="schema")
    benchmark_id: str = Field(min_length=1)
    benchmark_corpus_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    benchmark_gold_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expectations: list[TemporalExpectation] = Field(min_length=7, max_length=7)


def _stable_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resolve_inside(root: Path, raw: str, *, label: str) -> Path:
    path = (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must resolve inside {root}") from exc
    return path


def _validate_truth(expectation: TemporalExpectation) -> None:
    start = expectation.truth_window.start_session
    end = expectation.truth_window.end_session
    if start is not None and end is not None and end < start:
        raise ValueError(f"end before start: {expectation.expectation_id}")
    evidence_sessions = {row.source_session for row in expectation.evidence}
    for label, boundary in (("start", start), ("end", end)):
        if boundary is not None and boundary not in evidence_sessions:
            raise ValueError(
                f"{label} boundary lacks evidence: {expectation.expectation_id}"
            )
    ending_rows = [row for row in expectation.evidence if row.role == "ends"]
    starting_rows = [row for row in expectation.evidence if row.role == "starts"]
    if starting_rows and start is None:
        raise ValueError(f"starts evidence requires start session: {expectation.expectation_id}")
    if any(row.source_session != start for row in starting_rows):
        raise ValueError(f"starts evidence session mismatch: {expectation.expectation_id}")
    if ending_rows and end is None:
        raise ValueError(f"ends evidence requires end session: {expectation.expectation_id}")
    if expectation.persistence == "bounded" and end is None:
        raise ValueError(f"bounded persistence requires end: {expectation.expectation_id}")
    if any(row.source_session != end for row in ending_rows):
        raise ValueError(f"ends evidence session mismatch: {expectation.expectation_id}")
    # A point event may use one supporting observation for its start=end occurrence.
    # Ending a state/interval requires explicit `ends` evidence.
    point_event = expectation.temporal_kind == "event" and start == end
    if start is not None and not point_event and not any(
        row.role == "starts" and row.source_session == start
        for row in expectation.evidence
    ):
        raise ValueError(f"start boundary lacks starts evidence: {expectation.expectation_id}")
    if end is not None and not point_event and not any(
        row.role == "ends" and row.source_session == end for row in expectation.evidence
    ):
        raise ValueError(f"end boundary lacks ends evidence: {expectation.expectation_id}")


def validate_campaign_memory_temporal_intent(
    *,
    benchmark_path: Path,
    temporal_intent_path: Path,
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    benchmark_summary = validate_campaign_memory_benchmark(
        benchmark_path, repo_root=repo_root
    )
    benchmark = CampaignMemoryBenchmark.model_validate_json(benchmark_path.read_bytes())
    overlay = TemporalIntentOverlay.model_validate_json(
        temporal_intent_path.read_bytes()
    )
    if overlay.benchmark_id != benchmark_summary["benchmark_id"]:
        raise ValueError("benchmark ID mismatch")
    if (
        overlay.benchmark_corpus_fingerprint
        != benchmark_summary["corpus_fingerprint"]
    ):
        raise ValueError("benchmark corpus fingerprint mismatch")
    if overlay.benchmark_gold_fingerprint != benchmark_summary["gold_fingerprint"]:
        raise ValueError("benchmark gold fingerprint mismatch")

    ids = [row.expectation_id for row in overlay.expectations]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate temporal expectation ID")
    if set(ids) != REQUIRED_EXPECTATIONS:
        raise ValueError("temporal expectation IDs must match exact v1 contract")

    benchmark_root = benchmark_path.resolve().parent
    entities = load_entity_anchors(benchmark_root / benchmark.entity_anchors)
    facts = load_fact_anchors(benchmark_root / benchmark.fact_anchors)
    entity_by_id = {row.anchor_id: row for row in entities}
    fact_by_id = {row.anchor_id: row for row in facts}
    identity_ids = {row.expectation_id for row in benchmark.identity_expectations}
    identity_by_id = {
        row.expectation_id: row for row in benchmark.identity_expectations
    }
    corpus_root = _resolve_inside(
        repo_root.resolve(), benchmark.corpus_root, label="corpus_root"
    )
    source_locators = {row.locator for row in benchmark.sources}

    evidence_count = 0
    for expectation in overlay.expectations:
        if expectation.subject_anchor not in entity_by_id:
            raise ValueError(f"unknown subject anchor: {expectation.expectation_id}")
        if expectation.fact_anchor is not None:
            fact = fact_by_id.get(expectation.fact_anchor)
            if fact is None:
                raise ValueError(f"unknown fact anchor: {expectation.expectation_id}")
            if fact.subject_anchor != expectation.subject_anchor:
                raise ValueError(f"fact subject mismatch: {expectation.expectation_id}")
        if any(ref not in identity_ids for ref in expectation.identity_expectation_refs):
            raise ValueError(
                f"unknown identity expectation ref: {expectation.expectation_id}"
            )
        for ref in expectation.identity_expectation_refs:
            if expectation.subject_anchor not in identity_by_id[ref].anchor_ids:
                raise ValueError(
                    f"identity expectation subject mismatch: {expectation.expectation_id}"
                )
        evidence_keys = [
            (row.source_file, row.source_session, row.source_text_marker, row.role)
            for row in expectation.evidence
        ]
        if len(evidence_keys) != len(set(evidence_keys)):
            raise ValueError(f"duplicate evidence row: {expectation.expectation_id}")
        for evidence in expectation.evidence:
            if evidence.source_file not in source_locators:
                raise ValueError(f"evidence source outside cohort: {expectation.expectation_id}")
            if SOURCE_SESSIONS[evidence.source_file] != evidence.source_session:
                raise ValueError(f"source session mismatch: {expectation.expectation_id}")
            source_path = _resolve_inside(
                corpus_root, evidence.source_file, label="evidence source"
            )
            if evidence.source_text_marker not in source_path.read_text(encoding="utf-8"):
                raise ValueError(f"evidence marker not found: {expectation.expectation_id}")
        evidence_count += len(expectation.evidence)
        _validate_truth(expectation)

    canonical = overlay.model_dump(mode="json", by_alias=True)
    for row in canonical["expectations"]:
        row["identity_expectation_refs"] = sorted(row["identity_expectation_refs"])
        row["evidence"] = sorted(
            row["evidence"],
            key=lambda evidence: (
                evidence["source_file"],
                evidence["source_session"]
                if evidence["source_session"] is not None
                else -1,
                evidence["source_text_marker"],
                evidence["role"],
            ),
        )
    canonical["expectations"] = sorted(
        canonical["expectations"], key=lambda row: row["expectation_id"]
    )
    return {
        "schema": SCHEMA,
        "benchmark_id": overlay.benchmark_id,
        "benchmark_corpus_fingerprint": overlay.benchmark_corpus_fingerprint,
        "benchmark_gold_fingerprint": overlay.benchmark_gold_fingerprint,
        "temporal_intent_fingerprint": _stable_sha256(canonical),
        "expectation_count": len(overlay.expectations),
        "linked_fact_expectation_count": sum(
            row.fact_anchor is not None for row in overlay.expectations
        ),
        "requirement_only_expectation_count": sum(
            row.fact_anchor is None for row in overlay.expectations
        ),
        "evidence_ref_count": evidence_count,
        "temporal_kind_counts": dict(
            sorted(Counter(row.temporal_kind for row in overlay.expectations).items())
        ),
        "persistence_counts": dict(
            sorted(Counter(row.persistence for row in overlay.expectations).items())
        ),
        "validated": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the model-free campaign-memory temporal intent overlay."
    )
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--temporal-intent", type=Path, required=True)
    args = parser.parse_args()
    try:
        summary = validate_campaign_memory_temporal_intent(
            benchmark_path=args.benchmark,
            temporal_intent_path=args.temporal_intent,
        )
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Temporal intent validation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
