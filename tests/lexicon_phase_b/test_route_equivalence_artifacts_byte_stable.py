from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.lexicon_phase_b.route_equivalence_manifest import (
    build_route_equivalence_manifest,
    write_route_equivalence_manifest,
)

CASES = [
    (
        "longmont-c1",
        Path("corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_npc_registry.json"),
        Path("evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl"),
    ),
    (
        "longmont-c2",
        Path("corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_npc_registry.json"),
        Path("evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl"),
    ),
]


@pytest.mark.parametrize(("campaign_id", "registry_path", "expected_artifact_path"), CASES)
def test_build_matches_committed_artifact_bytes(
    campaign_id: str,
    registry_path: Path,
    expected_artifact_path: Path,
    tmp_path: Path,
) -> None:
    del campaign_id
    records = build_route_equivalence_manifest(registry_path)
    out_path = tmp_path / "out.jsonl"
    write_route_equivalence_manifest(records, out_path)
    assert out_path.read_bytes() == expected_artifact_path.read_bytes()


@pytest.mark.parametrize(("campaign_id", "registry_path", "expected_artifact_path"), CASES)
def test_determinism_within_process(
    campaign_id: str,
    registry_path: Path,
    expected_artifact_path: Path,
    tmp_path: Path,
) -> None:
    del campaign_id, expected_artifact_path
    records_a = build_route_equivalence_manifest(registry_path)
    records_b = build_route_equivalence_manifest(registry_path)
    out_a = tmp_path / "a.jsonl"
    out_b = tmp_path / "b.jsonl"
    write_route_equivalence_manifest(records_a, out_a)
    write_route_equivalence_manifest(records_b, out_b)
    assert out_a.read_bytes() == out_b.read_bytes()


@pytest.mark.parametrize(("campaign_id", "registry_path", "expected_artifact_path"), CASES)
def test_schema_version_and_authority_effect_pinned(
    campaign_id: str,
    registry_path: Path,
    expected_artifact_path: Path,
) -> None:
    del campaign_id, registry_path
    first_non_empty = next(
        line for line in expected_artifact_path.read_text(encoding="utf-8").splitlines() if line.strip()
    )
    obj = json.loads(first_non_empty)
    assert obj["schema_version"] == "0.3.0"
    assert obj["authority_effect"] == "routing_only"


@pytest.mark.parametrize(("campaign_id", "registry_path", "expected_artifact_path"), CASES)
def test_real_registry_relative_paths_map_campaign_to_world_fallback(
    campaign_id: str,
    registry_path: Path,
    expected_artifact_path: Path,
) -> None:
    del expected_artifact_path
    records = build_route_equivalence_manifest(registry_path)
    assert records
    for record in records:
        assert record.from_route_id.startswith(f"route:{campaign_id}:")
        assert record.to_route_id.startswith("route:elderwyld:")


@pytest.mark.parametrize(("campaign_id", "registry_path", "expected_artifact_path"), CASES)
def test_manifest_hash_constant_per_file(campaign_id: str, registry_path: Path, expected_artifact_path: Path) -> None:
    del campaign_id, registry_path
    rows = [json.loads(line) for line in expected_artifact_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len({row["route_equivalence_manifest_hash"] for row in rows}) == 1
