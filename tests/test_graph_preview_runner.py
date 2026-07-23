from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from apps.live_control_server.services.graph_run_registry import get_extraction_run
from apps.live_control_server.services.source_artifact_registry import (
    create_recap_source_artifact,
    create_source_artifact_from_workspace_document,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    mark_workspace_document_committed,
)
from graph_memory.ingestion.extraction_run import ExtractionRunStatus
from graph_memory.source_span import source_span_index_to_dict
from apps.live_control_server.services.source_artifact_registry import load_source_span_index
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionError,
)
from src.graph_memory.extraction.graph_preview_runner import (
    ProductionExtractionRequest,
    run_production_extraction,
)
from src.graph_memory.extraction.recap_extraction_profile import (
    RECAP_PROFILE_ID,
    RECAP_PROFILE_VERSION,
)
from src.graph_memory.extraction.source_adapter import NormalizedExtractionSource
from src.graph_memory.extraction.worldbuilding_plumbing_profile import (
    WORLDBUILDING_PLUMBING_PROFILE_ID,
    WORLDBUILDING_PLUMBING_PROFILE_VERSION,
)


def _normalized_from_artifact(root: Path, source_artifact_id: str) -> NormalizedExtractionSource:
    from apps.live_control_server.services.source_artifact_registry import (
        load_registered_source_artifact_text,
    )

    artifact, text = load_registered_source_artifact_text(root, source_artifact_id)
    index = load_source_span_index(root, source_artifact_id)
    return NormalizedExtractionSource(
        source_artifact_id=artifact.source_artifact_id,
        source_domain=str(artifact.source_domain),
        source_text=text,
        source_sha256=artifact.content_sha256 or "",
        source_uri=artifact.uri,
        campaign_id=artifact.campaign_id,
        session_id=artifact.session_id,
        document_class=artifact.document_class,
        source_span_index=source_span_index_to_dict(index),
    )


def _admit_recap(tmp_path: Path, text: str = "Mirathorn is a river city.\n\nGuards watch the gate.\n"):
    recap_path = tmp_path / "corpus" / "recap.md"
    recap_path.parent.mkdir(parents=True, exist_ok=True)
    recap_path.write_text(text, encoding="utf-8")
    artifact = create_recap_source_artifact(
        tmp_path,
        campaign_id="longmont-c2",
        session_id="session-24",
        recap_path=recap_path,
    )
    return _normalized_from_artifact(tmp_path, artifact.source_artifact_id)


def _admit_worldbuilding(tmp_path: Path, text: str = "Mirathorn is a river city.\n"):
    record = create_workspace_document(
        tmp_path,
        title="Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    committed = mark_workspace_document_committed(
        tmp_path, record.document_id, expected_revision=1
    )
    target = tmp_path / committed.target_relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    content = text.rstrip("\n") + "\n"
    target.write_text(content, encoding="utf-8")
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=committed.document_id,
        expected_revision=committed.revision,
    )
    return _normalized_from_artifact(tmp_path, artifact.source_artifact_id)


class FixtureClient:
    def __init__(self, *, mode: str = "ok", span_ref: str | None = None) -> None:
        self.mode = mode
        self.span_ref = span_ref

    def run_pass(
        self,
        pass_name: str,
        *,
        model_id: str,
        instructions: str,
        user_content: str,
        pass_spec: Any = None,
    ) -> dict[str, Any]:
        if self.mode == "refusal":
            raise CategoryGraphExtractionError(f"model refused {pass_name}: policy")
        if self.mode == "incomplete":
            raise CategoryGraphExtractionError(f"model response incomplete for {pass_name}")
        if self.mode == "schema":
            raise CategoryGraphExtractionError(f"schema failure for {pass_name}")
        if pass_name == "edge_pass":
            return {
                "parsed": {"observation_edges": []},
                "cost_usd": 0.0,
                "usage": {},
                "elapsed_ms": 1,
                "response_id": "edge",
            }
        if pass_name == "beat_pass":
            return {
                "parsed": {"observation_beats": []},
                "cost_usd": 0.0,
                "usage": {},
                "elapsed_ms": 1,
                "response_id": "beat",
            }
        evidence_ref = self.span_ref or "span-1"
        node = {
            "node_id": f"{pass_name}-1",
            "label": "Mirathorn",
            "node_type": "location",
            "description": "fixture",
            "importance": "medium",
            "evidence_refs": [
                {"source_span_ref_id": evidence_ref, "anchor_quotes": ["Mirathorn"]}
            ],
        }
        if self.mode == "missing_evidence":
            node["evidence_refs"] = []
        return {
            "parsed": {"observation_nodes": [node]},
            "cost_usd": 0.0,
            "usage": {},
            "elapsed_ms": 1,
            "response_id": pass_name,
        }


def _first_paragraph_span_id(source: NormalizedExtractionSource) -> str:
    for span in source.source_span_index.get("spans") or []:
        return str(span.get("source_span_id") or span.get("source_span_ref_id"))
    raise AssertionError("expected at least one span")


def test_unknown_profile_persists_failed_run(tmp_path: Path) -> None:
    source = _admit_recap(tmp_path)
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id="missing",
            profile_version="0.0",
            allow_llm=True,
            category_client=FixtureClient(),
        )
    )
    loaded = get_extraction_run(tmp_path, result.run.run_id)
    assert result.failure_kind == "profile"
    assert loaded.status == ExtractionRunStatus.FAILED
    assert loaded.lineage.get("failure_kind") == "profile"
    assert loaded.diagnostics.errors


def test_recap_fixture_extracts_reviewable_run(tmp_path: Path) -> None:
    source = _admit_recap(tmp_path)
    span_ref = _first_paragraph_span_id(source)
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            allow_llm=True,
            category_client=FixtureClient(span_ref=span_ref),
            output_dir=tmp_path / "runs",
        )
    )
    loaded = get_extraction_run(tmp_path, result.run.run_id)
    assert result.failure_kind is None
    assert loaded.status == ExtractionRunStatus.REVIEWABLE
    assert loaded.session_id == "session-24"
    assert loaded.profile_id == f"{RECAP_PROFILE_ID}@{RECAP_PROFILE_VERSION}"
    assert loaded.lineage.get("model_id")
    assert result.candidate_graph is not None
    for key in ("source_artifact", "source_span_index", "candidate_graph"):
        component = loaded.components[key]
        assert component.uri.startswith("repo://")
        assert component.sha256
    # Re-run must not overwrite prior evidence bundle.
    second = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            allow_llm=True,
            category_client=FixtureClient(span_ref=span_ref),
            output_dir=tmp_path / "runs",
        )
    )
    assert second.run.run_id != loaded.run_id
    still_first = get_extraction_run(tmp_path, loaded.run_id)
    assert still_first.status == ExtractionRunStatus.REVIEWABLE
    assert still_first.components["candidate_graph"].uri != second.run.components[
        "candidate_graph"
    ].uri


def test_worldbuilding_null_session_extracts(tmp_path: Path) -> None:
    source = _admit_worldbuilding(tmp_path)
    span_ref = _first_paragraph_span_id(source)
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=WORLDBUILDING_PLUMBING_PROFILE_ID,
            profile_version=WORLDBUILDING_PLUMBING_PROFILE_VERSION,
            allow_llm=True,
            category_client=FixtureClient(span_ref=span_ref),
            output_dir=tmp_path / "wb-runs",
        )
    )
    loaded = get_extraction_run(tmp_path, result.run.run_id)
    assert loaded.session_id is None
    assert loaded.status == ExtractionRunStatus.REVIEWABLE
    assert loaded.lineage.get("profile_id") == WORLDBUILDING_PLUMBING_PROFILE_ID


@pytest.mark.parametrize("mode,kind", [("refusal", "refusal"), ("incomplete", "incomplete"), ("schema", "schema")])
def test_failure_modes_persist(tmp_path: Path, mode: str, kind: str) -> None:
    source = _admit_recap(tmp_path, "Mirathorn.\n")
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            allow_llm=True,
            category_client=FixtureClient(mode=mode),
        )
    )
    loaded = get_extraction_run(tmp_path, result.run.run_id)
    assert result.failure_kind == kind
    assert loaded.status == ExtractionRunStatus.FAILED
    assert loaded.lineage.get("failure_kind") == kind
    assert loaded.diagnostics.errors
    assert loaded.lineage.get("model_id")


def test_reviewable_candidate_evidence_binds_registered_artifact(tmp_path: Path) -> None:
    from graph_memory.source_span import document_source_ref_id

    source = _admit_recap(tmp_path)
    span_ref = _first_paragraph_span_id(source)
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            allow_llm=True,
            category_client=FixtureClient(span_ref=span_ref),
            output_dir=tmp_path / "runs",
        )
    )
    loaded = get_extraction_run(tmp_path, result.run.run_id)
    assert loaded.status == ExtractionRunStatus.REVIEWABLE
    assert loaded.source_artifact_id == source.source_artifact_id
    assert ":" in source.source_artifact_id.split("session-24")[-1]

    candidate_uri = loaded.components["candidate_graph"].uri.removeprefix("repo://")
    graph = json.loads((tmp_path / candidate_uri).read_text(encoding="utf-8"))
    span_uri = loaded.components["source_span_index"].uri.removeprefix("repo://")
    span_index = json.loads((tmp_path / span_uri).read_text(encoding="utf-8"))
    expected_ref = document_source_ref_id(source.source_artifact_id)
    span_ids = {
        str(span.get("source_span_id") or span.get("source_span_ref_id"))
        for span in span_index.get("spans") or []
        if isinstance(span, dict)
    }

    assert graph["source_artifact_ids"] == [source.source_artifact_id]
    legacy = f"artifact:recap:{source.campaign_id}:{source.session_id}"
    assert source.source_artifact_id != legacy

    for collection in ("nodes", "edges", "beats"):
        for item in graph.get(collection) or []:
            for ref in item.get("evidence_refs") or []:
                assert ref["source_artifact_id"] == source.source_artifact_id
                assert ref["source_ref_id"] == expected_ref
                assert ref["source_span_ref_id"] in span_ids


def test_in_repo_recap_admission_is_immutable_across_edits(tmp_path: Path) -> None:
    from apps.live_control_server.services.source_artifact_registry import (
        load_registered_source_artifact_text,
    )

    original = "Alpha paragraph.\n\nBeta paragraph.\n"
    edited = "Edited paragraph.\n\nStill different.\n"
    recap_path = tmp_path / "corpus" / "Session 24 - Recap.md"
    recap_path.parent.mkdir(parents=True, exist_ok=True)
    recap_path.write_text(original, encoding="utf-8")

    first = create_recap_source_artifact(
        tmp_path,
        campaign_id="longmont-c2",
        session_id="session-24",
        recap_path=recap_path,
    )
    assert recap_path.read_text(encoding="utf-8") == original
    assert first.uri.startswith("repo://out/registries/source_content/recap/")
    assert first.content_sha256 and first.content_sha256 in first.uri

    span_ref = _first_paragraph_span_id(
        _normalized_from_artifact(tmp_path, first.source_artifact_id)
    )
    first_run = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=_normalized_from_artifact(tmp_path, first.source_artifact_id),
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            allow_llm=True,
            category_client=FixtureClient(span_ref=span_ref),
            output_dir=tmp_path / "runs",
        )
    )
    assert first_run.run.status == ExtractionRunStatus.REVIEWABLE

    recap_path.write_text(edited, encoding="utf-8")
    second = create_recap_source_artifact(
        tmp_path,
        campaign_id="longmont-c2",
        session_id="session-24",
        recap_path=recap_path,
    )
    assert second.source_artifact_id != first.source_artifact_id
    assert second.uri != first.uri
    assert recap_path.read_text(encoding="utf-8") == edited

    _, first_text = load_registered_source_artifact_text(tmp_path, first.source_artifact_id)
    assert first_text == original.rstrip("\n") + "\n" or first_text.startswith("Alpha")
    reloaded = get_extraction_run(tmp_path, first_run.run.run_id)
    assert reloaded.status == ExtractionRunStatus.REVIEWABLE
    source_uri = reloaded.components["source_artifact"].uri.removeprefix("repo://")
    assert (tmp_path / source_uri).read_text(encoding="utf-8").startswith("Alpha")


def test_production_known_entity_matching_uses_hydrated_spans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.graph_memory.extraction.known_entity_registry import (
        KnownEntity,
        KnownEntityRegistry,
    )

    text = "TestHero walks into Mirathorn.\n\nGuards watch the gate.\n"
    source = _admit_recap(tmp_path, text)
    span_ref = _first_paragraph_span_id(source)

    entity = KnownEntity(
        slug="test_hero",
        kind="pc",
        display_name="TestHero",
        canonical_entity_id="node:test-hero",
        aliases=(),
        hub_rel_path="PCs/test_hero/README.md",
        hub_resolved=True,
        corpus_ref={"type": "character", "ref_id": "test_hero", "resolution": "resolved"},
        match_terms=(("TestHero", "canonical"),),
    )
    registry = KnownEntityRegistry(
        campaign_id="longmont-c2",
        session_key="24",
        roster_session_key="24",
        roster_carry_forward=False,
        registry_relpath=None,
        entities=(entity,),
    )
    monkeypatch.setattr(
        "src.graph_memory.extraction.category_candidate_graph_extractor.build_known_entity_registry",
        lambda *args, **kwargs: registry,
    )

    class DuplicateHeroClient(FixtureClient):
        def run_pass(self, pass_name: str, **kwargs: Any) -> dict[str, Any]:
            if pass_name == "actor_pass":
                return {
                    "parsed": {
                        "observation_nodes": [
                            {
                                "node_id": "node:test-hero-dup",
                                "label": "TestHero",
                                "node_type": "character",
                                "description": "duplicate",
                                "importance": "medium",
                                "evidence_refs": [
                                    {
                                        "source_span_ref_id": span_ref,
                                        "anchor_quotes": ["TestHero"],
                                    }
                                ],
                            }
                        ]
                    },
                    "cost_usd": 0.0,
                    "usage": {},
                    "elapsed_ms": 1,
                    "response_id": "actor",
                }
            return super().run_pass(pass_name, **kwargs)

    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            allow_llm=True,
            category_client=DuplicateHeroClient(span_ref=span_ref),
            output_dir=tmp_path / "runs",
        )
    )
    assert result.known_entity_mentions is not None
    assert int(result.known_entity_mentions.get("diagnostics", {}).get("mention_count") or 0) >= 1
    assert result.known_entity_mentions.get("diagnostics", {}).get("spans_scanned", 0) >= 1
    labels = {n.get("label") for n in (result.candidate_graph or {}).get("nodes") or []}
    assert "TestHero" not in labels


def test_worldbuilding_graph_uses_profile_semantic_state(tmp_path: Path) -> None:
    from src.graph_memory.candidate_graph_preview import (
        candidate_graph_preview_from_dict,
        validate_candidate_graph_preview,
    )

    source = _admit_worldbuilding(tmp_path, "Mirathorn is a river city.\n")
    span_ref = _first_paragraph_span_id(source)
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=WORLDBUILDING_PLUMBING_PROFILE_ID,
            profile_version=WORLDBUILDING_PLUMBING_PROFILE_VERSION,
            allow_llm=True,
            category_client=FixtureClient(span_ref=span_ref),
            output_dir=tmp_path / "wb-runs",
        )
    )
    loaded = get_extraction_run(tmp_path, result.run.run_id)
    assert loaded.status == ExtractionRunStatus.REVIEWABLE
    nodes = (result.candidate_graph or {}).get("nodes") or []
    assert nodes
    for node in nodes:
        assert node["semantic_state"]["canon_state"] == "worldbuilding_draft"
        assert node["semantic_state"]["lifecycle_state"] == "candidate"
    preview = candidate_graph_preview_from_dict(result.candidate_graph or {})
    report = validate_candidate_graph_preview(preview)
    assert report.issue_counts.get("invalid_semantic_state", 0) == 0
    assert report.issues == ()


def test_recap_snapshot_rejects_path_escape(tmp_path: Path) -> None:
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
    )

    with pytest.raises(SourceArtifactRegistryError, match="safe path segment"):
        create_recap_source_artifact(
            tmp_path,
            campaign_id="../..",
            session_id="session-24",
            recap_text="escape attempt\n",
        )
    with pytest.raises(SourceArtifactRegistryError, match="safe path segment"):
        create_recap_source_artifact(
            tmp_path,
            campaign_id="longmont-c2",
            session_id="session-24/../evil",
            recap_text="escape attempt\n",
        )
