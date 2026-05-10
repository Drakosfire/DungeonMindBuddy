from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.lexicon_phase_b.route_equivalence_loader import (
    load_route_equivalence_manifest,
    load_route_equivalence_manifests,
)
from src.lexicon_phase_b.schemas import RouteEquivalenceRecord
from tests.lexicon_phase_b.test_route_equivalence_artifacts_byte_stable import CASES


@pytest.mark.parametrize(("campaign_id", "registry_path", "artifact_path"), CASES)
def test_loader_returns_canonical_record_id_order_for_committed_artifact(
    campaign_id: str,
    registry_path: Path,
    artifact_path: Path,
) -> None:
    del campaign_id, registry_path
    records = load_route_equivalence_manifest(artifact_path)
    record_ids = [r.record_id for r in records]
    assert record_ids == sorted(record_ids)


def test_loader_concat_dedupes_and_sorts_by_record_id() -> None:
    c1_path = CASES[0][2]
    c2_path = CASES[1][2]
    records = load_route_equivalence_manifests([c1_path, c2_path, c1_path])
    expected = load_route_equivalence_manifests([c1_path, c2_path])
    assert records == expected
    assert [r.record_id for r in records] == sorted(r.record_id for r in records)


def test_loader_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    base_record = RouteEquivalenceRecord(
        record_id="route-equivalence:test:ok",
        campaign_id="longmont-c1",
        display_name="Captain Tamsin Vale",
        from_route_id="route:longmont-c1:tamsin-vale",
        to_route_id="route:elderwyld:captain-tamsin-vale",
    ).model_dump(mode="json")
    bad_record = dict(base_record)
    bad_record["record_id"] = "route-equivalence:test:bad"
    bad_record["schema_version"] = "9.9.9"
    payload = "\n".join(json.dumps(x) for x in (base_record, bad_record))
    artifact = tmp_path / "synthetic.jsonl"
    artifact.write_text(payload + "\n", encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        load_route_equivalence_manifest(artifact)
    message = str(excinfo.value)
    assert "9.9.9" in message
    assert str(artifact) in message


def test_loader_skips_blank_lines(tmp_path: Path) -> None:
    first = RouteEquivalenceRecord(
        record_id="route-equivalence:test:one",
        campaign_id="longmont-c1",
        display_name="One",
        from_route_id="route:longmont-c1:one",
        to_route_id="route:elderwyld:one",
    ).model_dump(mode="json")
    second = RouteEquivalenceRecord(
        record_id="route-equivalence:test:two",
        campaign_id="longmont-c2",
        display_name="Two",
        from_route_id="route:longmont-c2:two",
        to_route_id="route:elderwyld:two",
    ).model_dump(mode="json")
    artifact = tmp_path / "with-blanks.jsonl"
    artifact.write_text(
        f"{json.dumps(first)}\n\n{json.dumps(second)}\n\n",
        encoding="utf-8",
    )
    records = load_route_equivalence_manifest(artifact)
    assert len(records) == 2


def test_loader_raises_for_missing_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_route_equivalence_manifest(tmp_path / "nope.jsonl")
