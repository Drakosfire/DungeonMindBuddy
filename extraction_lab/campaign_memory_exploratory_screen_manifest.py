from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from extraction_lab.campaign_memory_benchmark import validate_campaign_memory_benchmark
from extraction_lab.campaign_memory_temporal_intent import (
    validate_campaign_memory_temporal_intent,
)


SCHEMA = "dmb_campaign_memory_exploratory_screen_v1"
MODELS = ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"]
BENCHMARK = "evals/campaign_memory_development/benchmark.json"
TEMPORAL = "evals/campaign_memory_development/temporal_expectations.json"
FORBIDDEN_GENERATION_MARKERS = (
    "PREREGISTRATION-DOGFOOD-CONTINUITY-stage4i",
    "gold/entity_anchors.json",
    "gold/fact_anchors.json",
    "temporal_expectations.json",
    "fact_anchors.json",
    "entity_anchors.json",
)


class Pins(BaseModel):
    model_config = ConfigDict(extra="forbid")
    benchmark_id: str
    corpus_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    gold_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    temporal_intent_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class Execution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["flex"]
    cache_policy: Literal["isolated"]
    repetitions: Literal[1]
    batch_size: Literal[5]
    reasoning_effort: Literal["medium"]
    fact_contract: Literal["payload_lean_v1"]
    models: list[str]

    @model_validator(mode="after")
    def exact_models(self) -> "Execution":
        if self.models != MODELS:
            raise ValueError(f"models must be exactly {MODELS} in Luna → Terra → Sol order")
        return self


class ScreenManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_name: Literal[SCHEMA] = Field(alias="schema")
    experiment_id: str = Field(min_length=1)
    repository_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    benchmark: str
    temporal_intent: str
    pins: Pins
    execution: Execution


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observed_authority_pins(*, repo_root: Path) -> dict[str, str]:
    benchmark_path = repo_root / BENCHMARK
    temporal_path = repo_root / TEMPORAL
    benchmark = validate_campaign_memory_benchmark(benchmark_path, repo_root=repo_root)
    temporal = validate_campaign_memory_temporal_intent(
        benchmark_path=benchmark_path,
        temporal_intent_path=temporal_path,
        repo_root=repo_root,
    )
    return {
        "benchmark_id": benchmark["benchmark_id"],
        "corpus_fingerprint": benchmark["corpus_fingerprint"],
        "gold_fingerprint": benchmark["gold_fingerprint"],
        "temporal_intent_fingerprint": temporal["temporal_intent_fingerprint"],
    }


def build_screen_manifest_payload(
    *, repo_root: Path, repository_sha: str
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "experiment_id": "stage4i-exploratory-model-screen",
        "repository_sha": repository_sha,
        "benchmark": BENCHMARK,
        "temporal_intent": TEMPORAL,
        "pins": observed_authority_pins(repo_root=repo_root),
        "execution": {
            "mode": "flex",
            "cache_policy": "isolated",
            "repetitions": 1,
            "batch_size": 5,
            "reasoning_effort": "medium",
            "fact_contract": "payload_lean_v1",
            "models": list(MODELS),
        },
    }


def load_screen_manifest(path: Path, *, repo_root: Path) -> tuple[ScreenManifest, dict[str, Any]]:
    manifest = ScreenManifest.model_validate_json(path.read_text(encoding="utf-8"))
    observed = observed_authority_pins(repo_root=repo_root)
    if observed != manifest.pins.model_dump():
        raise ValueError("manifest authority pins do not match validated benchmark")
    benchmark_path = repo_root / manifest.benchmark
    temporal_path = repo_root / manifest.temporal_intent
    payload = json.loads(benchmark_path.read_text(encoding="utf-8"))
    corpus_root = (repo_root / payload["corpus_root"]).resolve()
    sources = [corpus_root / item["locator"] for item in payload["sources"]]
    return manifest, {
        "manifest_path": path.resolve(),
        "manifest_sha256": sha(path),
        "benchmark_path": benchmark_path,
        "temporal_path": temporal_path,
        "corpus_root": corpus_root,
        "sources": sources,
        "source_locators": [item["locator"] for item in payload["sources"]],
        "entity_gold": (benchmark_path.parent / payload["entity_anchors"]).resolve(),
        "fact_gold": (benchmark_path.parent / payload["fact_anchors"]).resolve(),
    }


def argv_leaks_evaluator_authority(argv: list[str]) -> list[str]:
    joined = " ".join(argv)
    return [marker for marker in FORBIDDEN_GENERATION_MARKERS if marker in joined]
