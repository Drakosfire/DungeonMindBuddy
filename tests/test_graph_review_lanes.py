import pytest
from pydantic import ValidationError

from apps.live_control_server.services.graph_review_lanes import (
    GraphReviewLane,
    GraphReviewLaneCounts,
    GraphReviewLaneMetadata,
    GraphReviewLaneRole,
    GraphReviewLaneSourceKind,
    GraphReviewLaneStatus,
    GraphReviewVocabularyMode,
)


def _lane(**overrides: object) -> GraphReviewLane:
    values = {
        "lane_id": "lane-gold",
        "role": GraphReviewLaneRole.GOLD,
        "source_kind": GraphReviewLaneSourceKind.GOLD_FIXTURE,
        "label": "Gold fixture",
        "campaign_id": "longmont-c2",
        "session_id": "session-23",
        "counts": GraphReviewLaneCounts(),
        "metadata": GraphReviewLaneMetadata(),
    }
    values.update(overrides)
    return GraphReviewLane(**values)


def test_minimal_gold_lane_defaults_are_conservative() -> None:
    lane = _lane()

    assert lane.role == "gold"
    assert lane.source_kind == "gold_fixture"
    assert lane.status == "unknown"
    assert lane.counts.nodes == 0
    assert lane.counts.edges == 0
    assert lane.metadata.vocabulary_mode == "unknown"


def test_live_graph_ingest_lane_can_be_created() -> None:
    lane = _lane(
        lane_id="lane-live",
        role="live",
        source_kind="graph_ingest_run",
        label="Latest live run",
        manifest_path="out/graph_memory/runs/run-1/graph_ingest_run_manifest.json",
        preview_union_path="out/graph_memory/runs/run-1/preview_union.json",
        status="available",
        counts=GraphReviewLaneCounts(nodes=3, edges=2, evidence_refs=5),
        metadata=GraphReviewLaneMetadata(run_id="run-1", vocabulary_mode="none"),
    )

    assert lane.role == "live"
    assert lane.source_kind == "graph_ingest_run"
    assert lane.status == "available"
    assert lane.counts.evidence_refs == 5
    assert lane.metadata.run_id == "run-1"


def test_manual_review_variant_lane_can_be_represented() -> None:
    lane = _lane(
        lane_id="lane-manual-variant",
        role="variant",
        source_kind="manual_review_variant",
        label="Manual vocabulary variant",
        artifact_path="evals/graph_memory_layer/artifacts/manual_review.json",
        metadata=GraphReviewLaneMetadata(vocabulary_mode="node_and_edge"),
    )

    assert lane.role == "variant"
    assert lane.source_kind == "manual_review_variant"
    assert lane.metadata.vocabulary_mode == "node_and_edge"


def test_projection_payload_lane_can_be_represented() -> None:
    lane = _lane(
        lane_id="lane-reference-projection",
        role="reference",
        source_kind="projection_payload",
        label="Reference projection payload",
        artifact_path="evals/graph_memory_layer/examples/projection_payload.json",
    )

    assert lane.role == "reference"
    assert lane.source_kind == "projection_payload"


def test_mutable_metadata_defaults_are_not_shared_between_instances() -> None:
    first = GraphReviewLaneMetadata()
    second = GraphReviewLaneMetadata()

    first.runner_options["profile"] = "candidate"
    first.diagnostics["warning"] = True

    assert second.runner_options == {}
    assert second.diagnostics == {}


def test_serialization_uses_camel_case_wire_names() -> None:
    lane = _lane(
        lane_id="lane-live",
        role="live",
        source_kind="graph_ingest_run",
        manifest_path="manifest.json",
        preview_union_path="preview-union.json",
        counts=GraphReviewLaneCounts(evidence_refs=7),
        metadata=GraphReviewLaneMetadata(
            run_id="run-1",
            generated_at="2026-07-01T00:00:00Z",
            model_id="gpt-example",
            extraction_profile="anchor_quote_n3",
            extraction_mode="category",
            vocabulary_mode="dynamic",
            runner_options={"maxPasses": 7},
            diagnostics={"warnings": []},
        ),
    )

    payload = lane.model_dump(mode="json", by_alias=True)

    assert payload["laneId"] == "lane-live"
    assert payload["sourceKind"] == "graph_ingest_run"
    assert payload["campaignId"] == "longmont-c2"
    assert payload["sessionId"] == "session-23"
    assert payload["manifestPath"] == "manifest.json"
    assert payload["previewUnionPath"] == "preview-union.json"
    assert payload["counts"]["evidenceRefs"] == 7
    assert payload["metadata"]["runId"] == "run-1"
    assert payload["metadata"]["generatedAt"] == "2026-07-01T00:00:00Z"
    assert payload["metadata"]["modelId"] == "gpt-example"
    assert payload["metadata"]["extractionProfile"] == "anchor_quote_n3"
    assert payload["metadata"]["extractionMode"] == "category"
    assert payload["metadata"]["vocabularyMode"] == "dynamic"
    assert payload["metadata"]["runnerOptions"] == {"maxPasses": 7}
    assert payload["metadata"]["diagnostics"] == {"warnings": []}


def test_camel_case_wire_names_can_be_used_for_validation() -> None:
    lane = GraphReviewLane.model_validate(
        {
            "laneId": "lane-live",
            "role": "live",
            "sourceKind": "graph_ingest_run",
            "label": "Live run",
            "campaignId": "longmont-c2",
            "sessionId": "session-23",
            "counts": {"nodes": 1, "edges": 2, "evidenceRefs": 3},
            "metadata": {"runId": "run-1", "vocabularyMode": "unknown"},
        }
    )

    assert lane.lane_id == "lane-live"
    assert lane.counts.evidence_refs == 3
    assert lane.metadata.run_id == "run-1"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("role", "baseline"),
        ("source_kind", "vocabulary_run"),
        ("status", "ready"),
    ],
)
def test_invalid_lane_enum_values_are_rejected(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        _lane(**{field: value})


def test_invalid_vocabulary_mode_is_rejected() -> None:
    with pytest.raises(ValidationError):
        GraphReviewLaneMetadata(vocabulary_mode="assisted")


def test_all_public_enum_vocabularies_are_closed_to_expected_values() -> None:
    assert {item.value for item in GraphReviewLaneRole} == {
        "gold",
        "live",
        "variant",
        "reference",
    }
    assert {item.value for item in GraphReviewLaneSourceKind} == {
        "gold_fixture",
        "graph_ingest_run",
        "manual_review_variant",
        "projection_payload",
    }
    assert {item.value for item in GraphReviewLaneStatus} == {
        "available",
        "missing_projection",
        "failed",
        "stale",
        "unknown",
    }
    assert {item.value for item in GraphReviewVocabularyMode} == {
        "none",
        "node",
        "edge",
        "node_and_edge",
        "dynamic",
        "unknown",
    }
