from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from extraction_lab.anchor_schema import (
    EntityGoldAnchor,
    FactGoldAnchor,
    load_entity_anchors,
    load_fact_anchors,
)
from extraction_lab.benchmark_contract import compute_benchmark_contract


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "dmb_campaign_memory_development_benchmark_v1"
SURFACE = "campaign_memory_development"
REQUIRED_SOURCES = {
    "Longmont Campaign/Campaign 2/Session Recaps/Session 23 - Mireward Gate.md",
    "Longmont Campaign/Campaign 2/Session Recaps/Session 24 - Mireward Gate Battle.md",
    "Longmont Campaign/Campaign 2/Session Recaps/Session 25 - Mireward Gate Battle II.md",
    "Elderwyld/Cities and Towns/Mireward/Mireward_PLACE_BUILD_SCAFFOLD.md",
    "Elderwyld/Cities and Towns/Mireward/NPCs/brin_holloway/character_seed.md",
    "Elderwyld/Cities and Towns/Mireward/NPCs/orric_tane/character_seed.md",
    "Longmont Campaign/Campaign 2/PCs/karsemine/timeline.md",
}
FORBIDDEN_PARTS = {"_archive", "_normalized", "_breadcrumbed", "_session_memory"}


class BenchmarkSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    locator: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    role: Literal[
        "played_recap",
        "world_reference",
        "character_reference",
        "continuity_reference",
    ]
    reason: str = Field(min_length=1)

    @field_validator("locator", "reason")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class IdentityExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectation_id: str = Field(min_length=1)
    anchor_ids: list[str] = Field(min_length=2)
    intent: str = Field(min_length=1)

    @field_validator("expectation_id", "intent")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("anchor_ids")
    @classmethod
    def unique_anchor_ids(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("identity anchor IDs must not be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("identity anchor IDs must be unique")
        return normalized


class CampaignMemoryBenchmark(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_name: Literal[SCHEMA] = Field(alias="schema", serialization_alias="schema")
    benchmark_id: str = Field(min_length=1)
    surface: Literal[SURFACE]
    corpus_root: str = Field(min_length=1)
    sources: list[BenchmarkSource] = Field(min_length=7, max_length=7)
    entity_anchors: str = Field(min_length=1)
    fact_anchors: str = Field(min_length=1)
    identity_expectations: list[IdentityExpectation] = Field(min_length=1)


def _resolve_inside(root: Path, raw: str, *, label: str) -> Path:
    path = (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must resolve inside {root}") from exc
    return path


def _unique(values: list[str], *, label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {label}")


def _validate_anchors(
    *,
    entities: list[EntityGoldAnchor],
    facts: list[FactGoldAnchor],
    source_text: dict[str, str],
    expectations: list[IdentityExpectation],
) -> None:
    if not entities or not facts:
        raise ValueError("development surface requires entity and fact anchors")
    _unique([row.anchor_id for row in entities], label="entity anchor ID")
    _unique([row.anchor_id for row in facts], label="fact anchor ID")
    entity_by_id = {row.anchor_id: row for row in entities}
    for kind, anchors in (("entity", entities), ("fact", facts)):
        for anchor in anchors:
            if anchor.surface != SURFACE:
                raise ValueError(f"{kind} anchor surface mismatch: {anchor.anchor_id}")
            if not anchor.source_file or anchor.source_file not in source_text:
                raise ValueError(f"anchor source outside cohort: {anchor.anchor_id}")
            if not anchor.source_text_marker:
                raise ValueError(f"anchor marker missing: {anchor.anchor_id}")
            if anchor.source_text_marker not in source_text[anchor.source_file]:
                raise ValueError(f"anchor marker not found: {anchor.anchor_id}")
    for fact in facts:
        if fact.subject_anchor not in entity_by_id:
            raise ValueError(f"fact subject anchor missing: {fact.anchor_id}")
    _unique([row.expectation_id for row in expectations], label="identity expectation ID")
    for expectation in expectations:
        try:
            members = [entity_by_id[anchor_id] for anchor_id in expectation.anchor_ids]
        except KeyError as exc:
            raise ValueError(
                f"identity expectation anchor missing: {expectation.expectation_id}"
            ) from exc
        if len({row.expected_class for row in members}) != 1:
            raise ValueError(
                f"identity expectation class mismatch: {expectation.expectation_id}"
            )


def validate_campaign_memory_benchmark(
    manifest_path: Path, *, repo_root: Path = ROOT
) -> dict[str, Any]:
    manifest = CampaignMemoryBenchmark.model_validate_json(manifest_path.read_bytes())
    repo_root = repo_root.resolve()
    corpus_root = _resolve_inside(repo_root, manifest.corpus_root, label="corpus_root")
    if not corpus_root.is_dir():
        raise ValueError(f"corpus_root missing: {corpus_root}")
    locators = [source.locator for source in manifest.sources]
    _unique(locators, label="source locator")
    if set(locators) != REQUIRED_SOURCES:
        raise ValueError("source cohort must match the exact seven-source v1 contract")
    source_paths: list[Path] = []
    source_text: dict[str, str] = {}
    for source in manifest.sources:
        path = _resolve_inside(corpus_root, source.locator, label="source")
        if path.suffix.lower() != ".md":
            raise ValueError(f"source must be Markdown: {source.locator}")
        if FORBIDDEN_PARTS.intersection(path.relative_to(corpus_root).parts):
            raise ValueError(f"forbidden derived source: {source.locator}")
        if not path.is_file():
            raise ValueError(f"source missing: {source.locator}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != source.sha256:
            raise ValueError(f"source SHA mismatch: {source.locator}")
        source_paths.append(path)
        source_text[source.locator] = path.read_text(encoding="utf-8")

    benchmark_root = manifest_path.resolve().parent
    entity_path = _resolve_inside(
        benchmark_root, manifest.entity_anchors, label="entity_anchors"
    )
    fact_path = _resolve_inside(
        benchmark_root, manifest.fact_anchors, label="fact_anchors"
    )
    if not entity_path.is_file() or not fact_path.is_file():
        raise ValueError("anchor file missing")
    entities = load_entity_anchors(entity_path)
    facts = load_fact_anchors(fact_path)
    _validate_anchors(
        entities=entities,
        facts=facts,
        source_text=source_text,
        expectations=manifest.identity_expectations,
    )
    contract = compute_benchmark_contract(
        surface=SURFACE,
        source_paths=source_paths,
        corpus_source_root=corpus_root,
        entity_anchors=entities,
        fact_anchors=facts,
    )
    if not contract["corpus"]["available"]:
        raise ValueError("benchmark corpus identity unavailable")
    return {
        "schema": SCHEMA,
        "benchmark_id": manifest.benchmark_id,
        "surface": SURFACE,
        "source_count": len(source_paths),
        "entity_anchor_count": len(entities),
        "fact_anchor_count": len(facts),
        "identity_expectation_count": len(manifest.identity_expectations),
        "corpus_fingerprint": contract["corpus"]["fingerprint"],
        "gold_fingerprint": contract["gold"]["fingerprint"],
        "entity_fingerprint": contract["gold"]["entity_fingerprint"],
        "fact_fingerprint": contract["gold"]["fact_fingerprint"],
        "validated": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the model-free campaign-memory development benchmark."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate_campaign_memory_benchmark(args.manifest)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Benchmark validation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
