from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from extraction_lab.campaign_memory_benchmark import (
    CampaignMemoryBenchmark,
    validate_campaign_memory_benchmark,
)
from extraction_lab.campaign_memory_temporal_intent import (
    validate_campaign_memory_temporal_intent,
)


SCHEMA = "dmb_campaign_memory_baseline_characterization_v1"


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
    repetitions: Literal[3]
    batch_size: Literal[5]


class BaselineManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_name: Literal[SCHEMA] = Field(alias="schema")
    experiment_id: str = Field(min_length=1)
    repository_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    model_id: Literal["gpt-5.6-sol"]
    benchmark: str
    temporal_intent: str
    pins: Pins
    execution: Execution


class NormalizedBaseline:
    def __init__(
        self, manifest_path: Path, manifest: BaselineManifest, repo_root: Path
    ):
        self.manifest_path = manifest_path.resolve()
        self.manifest = manifest
        self.repo_root = repo_root.resolve()
        self.manifest_sha256 = hashlib.sha256(
            self.manifest_path.read_bytes()
        ).hexdigest()
        self.benchmark_path = self._inside(manifest.benchmark)
        self.temporal_path = self._inside(manifest.temporal_intent)
        benchmark = CampaignMemoryBenchmark.model_validate_json(
            self.benchmark_path.read_bytes()
        )
        self.corpus_root = self._inside(benchmark.corpus_root)
        self.source_locators = [row.locator for row in benchmark.sources]
        self.source_paths = [
            (self.corpus_root / row).resolve() for row in self.source_locators
        ]
        self.entity_anchor_path = (
            self.benchmark_path.parent / benchmark.entity_anchors
        ).resolve()
        self.fact_anchor_path = (
            self.benchmark_path.parent / benchmark.fact_anchors
        ).resolve()

    def _inside(self, raw: str) -> Path:
        path = (self.repo_root / raw).resolve()
        path.relative_to(self.repo_root)
        return path


def load_baseline_manifest(path: Path, *, repo_root: Path) -> NormalizedBaseline:
    manifest = BaselineManifest.model_validate_json(path.read_bytes())
    normalized = NormalizedBaseline(path, manifest, repo_root)
    benchmark = validate_campaign_memory_benchmark(
        normalized.benchmark_path, repo_root=repo_root
    )
    temporal = validate_campaign_memory_temporal_intent(
        benchmark_path=normalized.benchmark_path,
        temporal_intent_path=normalized.temporal_path,
        repo_root=repo_root,
    )
    expected = manifest.pins
    actual = (
        benchmark["benchmark_id"],
        benchmark["corpus_fingerprint"],
        benchmark["gold_fingerprint"],
        temporal["temporal_intent_fingerprint"],
    )
    if actual != (
        expected.benchmark_id,
        expected.corpus_fingerprint,
        expected.gold_fingerprint,
        expected.temporal_intent_fingerprint,
    ):
        raise ValueError("manifest pins do not match validated benchmark authority")
    if len(set(normalized.source_locators)) != 7 or any(
        "_dungeonbuddy" in Path(row).parts for row in normalized.source_locators
    ):
        raise ValueError("source cohort must contain seven unique non-derived sources")
    return normalized
