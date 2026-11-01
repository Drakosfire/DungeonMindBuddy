"""Fixture-backed pipeline proof for the bounded worldbuilding profile."""

from __future__ import annotations
from tests.page_fixtures import create_page_fixture, save_page
from apps.live_control_server.services.workspace_document_registry import get_workspace_document

import json
from pathlib import Path
from typing import Any

import pytest

from apps.live_control_server.services.source_artifact_registry import (
    create_source_artifact_from_workspace_document,
    load_source_span_index,
)
from graph_memory.source_span import source_span_index_to_dict
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    FixtureCategoryGraphPassClient,
)
from src.graph_memory.extraction.graph_preview_runner import (
    ProductionExtractionRequest,
    run_production_extraction,
)
from src.graph_memory.extraction.source_adapter import NormalizedExtractionSource
from src.graph_memory.extraction.worldbuilding_extraction_profile import (
    WORLDBUILDING_PROFILE_ID,
    WORLDBUILDING_PROFILE_VERSION,
    validate_worldbuilding_candidate_bounds,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "evals"
    / "graph_memory_layer"
    / "fixtures"
    / "worldbuilding_profile_fixture.json"
)


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _admit_fixture_source(tmp_path: Path) -> tuple[NormalizedExtractionSource, str]:
    """Register fixture prose as a SourceArtifact and return normalized source + paragraph span."""
    fixture = _load_fixture()
    record = create_page_fixture(
        tmp_path,
        title="Shepherd's Flock fixture",
        campaign_id=fixture["campaign_id"],
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class=fixture["document_class"],
        authority_state="draft",
        visibility_state="internal",
    )
    committed = get_workspace_document(tmp_path, record.document_id)
    content = str(fixture["source_text"]).rstrip("\n") + "\n"
    committed = save_page(tmp_path, committed.document_id, content)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=committed.document_id,
        expected_revision=committed.revision,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        load_registered_source_artifact_text,
    )

    registered, text = load_registered_source_artifact_text(
        tmp_path, artifact.source_artifact_id
    )
    index = load_source_span_index(tmp_path, artifact.source_artifact_id)
    index_payload = source_span_index_to_dict(index)
    first_span = (index_payload.get("spans") or [None])[0]
    if not isinstance(first_span, dict):
        raise AssertionError("registered source span index has no spans")
    span_id = str(
        first_span.get("source_span_id") or first_span.get("source_span_ref_id") or ""
    )
    if not span_id:
        raise AssertionError("registered span missing source_span_id")
    source = NormalizedExtractionSource(
        source_artifact_id=registered.source_artifact_id,
        source_domain=str(registered.source_domain),
        source_text=text,
        source_sha256=registered.content_sha256 or "",
        source_uri=registered.uri,
        campaign_id=registered.campaign_id,
        session_id=registered.session_id,
        document_class=registered.document_class,
        source_span_index=index_payload,
    )
    return source, span_id


def _pass_outputs_for_span(fixture: dict, span_id: str) -> dict:
    outputs = json.loads(json.dumps(fixture["pass_outputs"]))
    for pass_payload in outputs.values():
        for key in ("observation_nodes", "observation_edges"):
            for row in pass_payload.get(key) or []:
                for ref in row.get("evidence_refs") or []:
                    if ref.get("source_span_ref_id") == "PLACEHOLDER_SPAN":
                        ref["source_span_ref_id"] = span_id
    return outputs


def _run_with_pass_outputs(
    tmp_path: Path,
    *,
    source: NormalizedExtractionSource,
    pass_outputs: dict[str, Any],
) -> Any:
    return run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=WORLDBUILDING_PROFILE_ID,
            profile_version=WORLDBUILDING_PROFILE_VERSION,
            allow_llm=True,
            category_client=FixtureCategoryGraphPassClient(pass_outputs),
        )
    )


def test_fixture_pipeline_produces_reviewable_null_session_run(tmp_path: Path) -> None:
    fixture = _load_fixture()
    source, span_id = _admit_fixture_source(tmp_path)
    result = _run_with_pass_outputs(
        tmp_path,
        source=source,
        pass_outputs=_pass_outputs_for_span(fixture, span_id),
    )

    assert result.failure_kind is None
    assert result.run.status.value == "reviewable"
    assert result.run.session_id is None
    assert result.run.profile_id == f"{WORLDBUILDING_PROFILE_ID}@{WORLDBUILDING_PROFILE_VERSION}"
    assert result.candidate_graph is not None
    assert result.candidate_graph.get("session_id") in (None, "")
    assert validate_worldbuilding_candidate_bounds(result.candidate_graph) == []
    labels = {node["label"] for node in result.candidate_graph["nodes"]}
    assert "Commander Vell" in labels
    assert "Shepherd's Flock" in labels
    assert "Flockhouse" in labels
    for node in result.candidate_graph["nodes"]:
        assert node["evidence_refs"]
        assert all("source_span_ref_id" in ref for ref in node["evidence_refs"])


def test_fixture_pipeline_rejects_recap_profile_for_worldbuilding_source(
    tmp_path: Path,
) -> None:
    source, _span_id = _admit_fixture_source(tmp_path)
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id="recap_category_v2",
            profile_version="2.0",
            allow_llm=False,
        )
    )
    assert result.failure_kind == "profile"
    assert result.run.status.value == "failed"


def test_pipeline_rejects_excluded_item_node_as_non_reviewable(tmp_path: Path) -> None:
    """item is globally valid IR but excluded by the worldbuilding profile."""
    fixture = _load_fixture()
    source, span_id = _admit_fixture_source(tmp_path)
    pass_outputs = _pass_outputs_for_span(fixture, span_id)
    pass_outputs["actor_pass"]["observation_nodes"].append(
        {
            "node_id": "item:trail-rations",
            "label": "trail rations",
            "node_type": "item",
            "description": "Excluded commodity.",
            "importance": "low",
            "evidence_refs": [
                {
                    "source_span_ref_id": span_id,
                    "anchor_quotes": ["Shepherd's Flock"],
                }
            ],
        }
    )
    result = _run_with_pass_outputs(
        tmp_path,
        source=source,
        pass_outputs=pass_outputs,
    )
    assert result.failure_kind == "validation"
    assert result.run.status.value != "reviewable"
    assert any("excluded type" in d for d in result.diagnostics)


def test_pipeline_rejects_undeclared_node_type_as_non_reviewable(tmp_path: Path) -> None:
    """landmark is valid IR vocabulary but undeclared for this profile."""
    fixture = _load_fixture()
    source, span_id = _admit_fixture_source(tmp_path)
    pass_outputs = _pass_outputs_for_span(fixture, span_id)
    pass_outputs["location_pass"]["observation_nodes"].append(
        {
            "node_id": "landmark:ridge-marker",
            "label": "ridge marker",
            "node_type": "landmark",
            "description": "Undeclared for worldbuilding profile.",
            "importance": "low",
            "evidence_refs": [
                {
                    "source_span_ref_id": span_id,
                    "anchor_quotes": ["high ridge"],
                }
            ],
        }
    )
    result = _run_with_pass_outputs(
        tmp_path,
        source=source,
        pass_outputs=pass_outputs,
    )
    assert result.failure_kind == "validation"
    assert result.run.status.value != "reviewable"
    assert any("undeclared type" in d for d in result.diagnostics)


def test_pipeline_rejects_missing_evidence_as_non_reviewable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty-evidence nodes that survive extraction must not become reviewable.

    The category extractor normally omits empty-evidence nodes. This adversarial
    path preserves a resolved corpus_ref node with empty evidence_refs and
    disables the promote projection drop so the production controller's
    missing-evidence gate (and profile validator) are exercised.
    """
    from src.graph_memory.extraction import category_candidate_graph_extractor as extractor

    def _project_keep_empty_evidence(graph: dict, warning_count: int | None = None, **_kwargs: Any) -> dict:
        for edge in graph.get("edges") or []:
            if isinstance(edge, dict):
                for key in extractor._EDGE_PROMOTE_DROP_KEYS:
                    edge.pop(key, None)
        for node in graph.get("nodes") or []:
            if isinstance(node, dict):
                for key in extractor._NODE_PROMOTE_DROP_KEYS:
                    node.pop(key, None)
        return graph

    monkeypatch.setattr(
        extractor,
        "project_candidate_graph_for_promote",
        _project_keep_empty_evidence,
    )

    fixture = _load_fixture()
    source, span_id = _admit_fixture_source(tmp_path)
    pass_outputs = _pass_outputs_for_span(fixture, span_id)
    pass_outputs["actor_pass"]["observation_nodes"].append(
        {
            "node_id": "npc:ghost",
            "label": "Ghost Scout",
            "node_type": "character",
            "description": "Missing evidence.",
            "importance": "low",
            "evidence_refs": [],
            "corpus_ref": {
                "type": "npc",
                "ref_id": "ghost",
                "resolution": "resolved",
            },
        }
    )
    result = _run_with_pass_outputs(
        tmp_path,
        source=source,
        pass_outputs=pass_outputs,
    )
    assert result.failure_kind == "validation"
    assert result.run.status.value != "reviewable"
    assert any("evidence" in d.lower() for d in result.diagnostics)


def test_pipeline_rejects_empty_edge_evidence_without_endpoint_inheritance(
    tmp_path: Path,
) -> None:
    """Empty edge evidence_refs must not inherit endpoint citations under BLD-08."""
    fixture = _load_fixture()
    source, span_id = _admit_fixture_source(tmp_path)
    pass_outputs = _pass_outputs_for_span(fixture, span_id)
    # Keep valid evidenced endpoints; strip relationship-native evidence only.
    pass_outputs["edge_pass"] = {
        "observation_edges": [
            {
                "edge_id": "edge:vell-commands-flock",
                "from_node_id": "npc:vell",
                "to_node_id": "faction:shepherds-flock",
                "relationship_type": "commands",
                "predicate_family": "authority",
                "label": "commands",
                "evidence_refs": [],
            }
        ]
    }
    result = _run_with_pass_outputs(
        tmp_path,
        source=source,
        pass_outputs=pass_outputs,
    )
    assert result.failure_kind == "validation"
    assert result.run.status.value != "reviewable"
    assert any("evidence" in d.lower() for d in result.diagnostics)
    # Edge must still be present for validation (not silently dropped/repaired).
    assert result.candidate_graph is not None
    edges = result.candidate_graph.get("edges") or []
    assert any(e.get("edge_id") == "edge:vell-commands-flock" for e in edges)
    empty = next(e for e in edges if e.get("edge_id") == "edge:vell-commands-flock")
    assert not (empty.get("evidence_refs") or [])


def test_profile_wires_executable_post_extraction_validator() -> None:
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile

    profile = get_extraction_profile(
        WORLDBUILDING_PROFILE_ID, WORLDBUILDING_PROFILE_VERSION
    )
    assert profile.post_extraction_validator is validate_worldbuilding_candidate_bounds
    assert "institution" not in profile.vocabulary_policy["included_node_types"]
    assert all(
        pass_spec.allowed_node_types is not None for pass_spec in profile.node_passes
    )


def test_pipeline_fails_closed_when_post_extraction_validator_raises(
    tmp_path: Path,
) -> None:
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile

    def _boom(_graph: dict[str, Any]) -> list[str]:
        raise RuntimeError("validator bug")

    fixture = _load_fixture()
    source, span_id = _admit_fixture_source(tmp_path)
    profile = get_extraction_profile(
        WORLDBUILDING_PROFILE_ID, WORLDBUILDING_PROFILE_VERSION
    )
    original = profile.post_extraction_validator
    object.__setattr__(profile, "post_extraction_validator", _boom)
    try:
        result = _run_with_pass_outputs(
            tmp_path,
            source=source,
            pass_outputs=_pass_outputs_for_span(fixture, span_id),
        )
    finally:
        object.__setattr__(profile, "post_extraction_validator", original)

    assert result.failure_kind == "validation"
    assert result.run.status.value == "failed"
    assert any("validator raised" in d for d in result.diagnostics)
