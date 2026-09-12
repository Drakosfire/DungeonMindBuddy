import json
from pathlib import Path

import pytest

from extraction_lab.campaign_memory_baseline_manifest import load_baseline_manifest


ROOT = Path(__file__).resolve().parents[2]


def manifest_payload() -> dict:
    return {
        "schema": "dmb_campaign_memory_baseline_characterization_v1",
        "experiment_id": "stage4h-live",
        "repository_sha": "0" * 40,
        "benchmark": "evals/campaign_memory_development/benchmark.json",
        "temporal_intent": "evals/campaign_memory_development/temporal_expectations.json",
        "pins": {
            "benchmark_id": "c2-mireward-campaign-memory-dev-v1",
            "corpus_fingerprint": "925ad24a54d888e2f1d3673919d126767b39cdeaf885c07057bfb5da346ba8c1",
            "gold_fingerprint": "de072c175cc00a1dc7ed672cdaca317ee0f8cb381a8186e9cfc53a5885a4cd23",
            "temporal_intent_fingerprint": "ed3596e4fd7d75029534c19e5017f4905840347356bf5323b30c365f906c56c4",
        },
        "execution": {
            "mode": "realtime",
            "cache_policy": "isolated",
            "repetitions": 3,
            "batch_size": 5,
        },
    }


def test_loads_exact_frozen_authorities(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest_payload()), encoding="utf-8")
    loaded = load_baseline_manifest(path, repo_root=ROOT)
    assert len(loaded.source_paths) == 7
    assert loaded.manifest.execution.repetitions == 3


def test_rejects_unknown_or_wrong_pin(tmp_path: Path) -> None:
    payload = manifest_payload()
    payload["pins"]["gold_fingerprint"] = "0" * 64
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="pins"):
        load_baseline_manifest(path, repo_root=ROOT)
