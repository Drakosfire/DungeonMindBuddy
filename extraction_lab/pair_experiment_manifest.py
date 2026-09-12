from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from extraction_lab.anchor_schema import load_entity_anchors, load_fact_anchors


PAIR_EXPERIMENT_SCHEMA = "dmb_extraction_pair_experiment_v1"


class PairExecutionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["realtime"]
    cache_policy: Literal["isolated"]
    repetitions: Literal[1]


class PairVariantConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_size: int = Field(ge=1, le=32)


class PairVariants(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline: PairVariantConfig
    candidate: PairVariantConfig


class PairExperimentManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_name: Literal[PAIR_EXPERIMENT_SCHEMA] = Field(
        alias="schema", serialization_alias="schema"
    )
    experiment_id: str = Field(min_length=1)
    repository_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    surface: str = Field(min_length=1)
    corpus_root: str = Field(min_length=1)
    sources: list[str] = Field(min_length=1, max_length=3)
    entity_anchors: str = Field(min_length=1)
    fact_anchors: str = Field(min_length=1)
    execution: PairExecutionConfig
    variants: PairVariants

    @field_validator(
        "experiment_id", "surface", "corpus_root", "entity_anchors", "fact_anchors"
    )
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("sources")
    @classmethod
    def validate_source_locators(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("source locators must not be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("source locators must be unique")
        return normalized

    @model_validator(mode="after")
    def require_exact_variants(self) -> PairExperimentManifest:
        # PairVariants forbids extras; retaining this validator makes the public
        # two-variant invariant explicit at the owning schema boundary.
        if set(self.variants.model_fields_set) != {"baseline", "candidate"}:
            raise ValueError("variants must contain exactly baseline and candidate")
        return self


class NormalizedPairExperiment(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    manifest: PairExperimentManifest
    manifest_path: Path
    manifest_sha256: str
    repo_root: Path
    corpus_root: Path
    source_paths: tuple[Path, ...]
    source_locators: tuple[str, ...]
    entity_anchor_path: Path
    fact_anchor_path: Path


def _resolve_inside(root: Path, raw_path: str, *, label: str) -> Path:
    candidate = (root / raw_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must resolve inside {root}") from exc
    return candidate


def load_pair_experiment_manifest(
    manifest_path: Path, *, repo_root: Path
) -> NormalizedPairExperiment:
    raw_bytes = manifest_path.read_bytes()
    manifest = PairExperimentManifest.model_validate_json(raw_bytes)
    repo_root = repo_root.resolve()
    corpus_root = _resolve_inside(repo_root, manifest.corpus_root, label="corpus_root")
    if not corpus_root.is_dir():
        raise ValueError(f"corpus_root does not exist: {corpus_root}")

    source_paths: list[Path] = []
    source_locators: list[str] = []
    for locator in manifest.sources:
        path = _resolve_inside(corpus_root, locator, label="source")
        if path.suffix.lower() != ".md":
            raise ValueError(f"source must be Markdown: {locator}")
        relative_parts = path.relative_to(corpus_root).parts
        if "_dungeonbuddy" in relative_parts:
            raise ValueError(f"managed _dungeonbuddy source is forbidden: {locator}")
        if not path.is_file():
            raise ValueError(f"source does not exist: {locator}")
        source_paths.append(path)
        source_locators.append(path.relative_to(corpus_root).as_posix())
    if len(source_locators) != len(set(source_locators)):
        raise ValueError("source locators must resolve to unique files")

    entity_anchor_path = _resolve_inside(
        repo_root, manifest.entity_anchors, label="entity_anchors"
    )
    fact_anchor_path = _resolve_inside(
        repo_root, manifest.fact_anchors, label="fact_anchors"
    )
    if not entity_anchor_path.is_file() or not fact_anchor_path.is_file():
        raise ValueError("entity and fact gold files must exist")
    load_entity_anchors(entity_anchor_path)
    load_fact_anchors(fact_anchor_path)

    return NormalizedPairExperiment(
        manifest=manifest,
        manifest_path=manifest_path.resolve(),
        manifest_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        repo_root=repo_root,
        corpus_root=corpus_root,
        source_paths=tuple(source_paths),
        source_locators=tuple(source_locators),
        entity_anchor_path=entity_anchor_path,
        fact_anchor_path=fact_anchor_path,
    )
