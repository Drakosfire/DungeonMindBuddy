from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from extraction_lab.pair_experiment_manifest import (
    NormalizedPairExperiment,
    load_pair_experiment_manifest,
)


REPEAT_EXPERIMENT_SCHEMA = "dmb_extraction_repeat_experiment_v1"


class RepeatExperimentManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_name: Literal[REPEAT_EXPERIMENT_SCHEMA] = Field(
        alias="schema", serialization_alias="schema"
    )
    experiment_id: str = Field(min_length=1)
    pair_manifest: str = Field(min_length=1)
    repetitions: int = Field(ge=2, le=3)

    @field_validator("experiment_id", "pair_manifest")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("repetitions", mode="before")
    @classmethod
    def reject_boolean(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("repetitions must be an integer")
        return value


class NormalizedRepeatExperiment(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    manifest: RepeatExperimentManifest
    manifest_path: Path
    manifest_sha256: str
    pair_manifest_path: Path
    pair_manifest_sha256: str
    pair: NormalizedPairExperiment


def load_repeat_experiment_manifest(
    manifest_path: Path, *, repo_root: Path
) -> NormalizedRepeatExperiment:
    raw_bytes = manifest_path.read_bytes()
    manifest = RepeatExperimentManifest.model_validate_json(raw_bytes)
    pair_path = (manifest_path.resolve().parent / manifest.pair_manifest).resolve()
    if not pair_path.is_file():
        raise ValueError(f"pair_manifest does not exist: {pair_path}")
    pair_bytes = pair_path.read_bytes()
    pair = load_pair_experiment_manifest(pair_path, repo_root=repo_root)
    return NormalizedRepeatExperiment(
        manifest=manifest,
        manifest_path=manifest_path.resolve(),
        manifest_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        pair_manifest_path=pair_path,
        pair_manifest_sha256=hashlib.sha256(pair_bytes).hexdigest(),
        pair=pair,
    )
