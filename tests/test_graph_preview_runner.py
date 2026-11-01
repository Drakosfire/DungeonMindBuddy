from __future__ import annotations
from tests.page_fixtures import create_page_fixture, save_page
from apps.live_control_server.services.workspace_document_registry import get_workspace_document

import copy
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from apps.live_control_server.services.graph_run_registry import get_extraction_run
from apps.live_control_server.services.source_artifact_registry import (
    create_recap_source_artifact,
    create_source_artifact_from_workspace_document,
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


@pytest.fixture(autouse=True)
def _ingest_application_state(application_state_dsn: str) -> str:
    return application_state_dsn


class _ContractFakeSourceAdmission:
    def prove_or_admit(self, request):
        from apps.live_control_server.ports.world_graph_source_admission import (
            AdmittedSourceIdentity,
        )

        artifact = request.source_artifact
        token = str(request.source_revision_token)
        digest = str(
            getattr(artifact, "content_sha256", "") or token.removeprefix("sha256:")
        )
        return AdmittedSourceIdentity(
            source_artifact_id=str(artifact.source_artifact_id),
            source_revision_id=token,
            content_sha256=digest,
            buddy_source_revision_id=token,
        )

    def prove(self, *, world_id, source_artifact_id, source_revision_id, source_revision_token=None):
        from apps.live_control_server.ports.world_graph_source_admission import (
            AdmittedSourceIdentity,
        )

        token = str(source_revision_token or source_revision_id)
        return AdmittedSourceIdentity(
            source_artifact_id=source_artifact_id,
            source_revision_id=source_revision_id,
            content_sha256=token.removeprefix("sha256:"),
            buddy_source_revision_id=token,
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
        world_id="world:elderwyld",
        campaign_id="longmont-c2",
        session_id="session-24",
        recap_path=recap_path,
    )
    return _normalized_from_artifact(tmp_path, artifact.source_artifact_id)


def _admit_worldbuilding(tmp_path: Path, text: str = "Mirathorn is a river city.\n"):
    record = create_page_fixture(
        tmp_path,
        title="Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    committed = get_workspace_document(tmp_path, record.document_id)
    content = text.rstrip("\n") + "\n"
    committed = save_page(tmp_path, committed.document_id, content)
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
        nodes = [node]
        if self.mode == "unsupported_sublocation" and pass_name == "location_pass":
            nodes.append(
                {
                    "node_id": "candidate:medical-wing",
                    "label": "Medical Wing",
                    "node_type": "sublocation",
                    "description": "fixture unsupported sublocation",
                    "importance": "medium",
                    "evidence_refs": [
                        {
                            "source_span_ref_id": evidence_ref,
                            "anchor_quotes": ["Mirathorn"],
                        }
                    ],
                }
            )
        return {
            "parsed": {"observation_nodes": nodes},
            "cost_usd": 0.0,
            "usage": {},
            "elapsed_ms": 1,
            "response_id": pass_name,
        }


def _first_paragraph_span_id(source: NormalizedExtractionSource) -> str:
    for span in source.source_span_index.get("spans") or []:
        return str(span.get("source_span_id") or span.get("source_span_ref_id"))
    raise AssertionError("expected at least one span")


def _recap_run_lineage(source: NormalizedExtractionSource) -> dict[str, str]:
    """Synthetic extraction callers state the source's fixture World explicitly."""
    return {
        "native_world_id": "world:elderwyld",
        "campaign_id": source.campaign_id or "",
    }


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
            initial_lineage=_recap_run_lineage(source),
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
            initial_lineage=_recap_run_lineage(source),
        )
    )
    loaded = get_extraction_run(tmp_path, result.run.run_id)
    assert result.failure_kind is None
    assert loaded.status == ExtractionRunStatus.REVIEWABLE
    assert loaded.session_id == "session-24"
    assert loaded.profile_id == f"{RECAP_PROFILE_ID}@{RECAP_PROFILE_VERSION}"
    assert loaded.lineage.get("model_id")
    assert result.candidate_graph is not None
    from application_state.ingest.components import get_component_bytes
    first_candidate = loaded.components["candidate_graph"]
    original_bytes = get_component_bytes(run_id=loaded.run_id, kind=first_candidate.kind,
        content_sha256=first_candidate.sha256)
    # Re-run must not overwrite the prior exact stored candidate.
    second = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            allow_llm=True,
            category_client=FixtureClient(span_ref=span_ref),
            initial_lineage=_recap_run_lineage(source),
        )
    )
    assert second.run.run_id != loaded.run_id
    still_first = get_extraction_run(tmp_path, loaded.run_id)
    assert still_first.status == ExtractionRunStatus.REVIEWABLE
    assert still_first == loaded
    assert get_component_bytes(run_id=loaded.run_id, kind=first_candidate.kind,
        content_sha256=first_candidate.sha256) == original_bytes


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
        )
    )
    loaded = get_extraction_run(tmp_path, result.run.run_id)
    assert loaded.session_id is None
    assert loaded.status == ExtractionRunStatus.REVIEWABLE
    assert loaded.lineage.get("profile_id") == WORLDBUILDING_PLUMBING_PROFILE_ID


def test_gazetteer_deferred_proposals_are_persisted_and_source_resolvable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hashlib
    from dataclasses import replace as dataclass_replace

    from apps.live_control_server.services.graph_run_registry import (
        assert_immutable_component_refs,
    )
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        FixtureCategoryGraphPassClient,
        extract_category_candidate_graph,
    )
    from src.graph_memory.extraction.bounded_recap_execution import (
        BoundedRecapPassClient,
        DEEPSEEK_MODEL,
    )
    from src.graph_memory.extraction.worldbuilding_gazetteer_scenario_scope import (
        GAZETTEER_PREPARED_SCENARIO_PROFILE,
    )
    from types import SimpleNamespace

    source_text = "\n\n".join([
        "#### Fantastic Livestock for the Exampleland",
        "#### 1. Float Goats",
        "Float Goats walk on water and carry goods across lakes.",
        "## Cultural Significance",
        "Float Goats symbolize joy and lightness in local culture.",
        "## Later section",
        "This unrelated detail stays outside the livestock owner section.",
        "## Approach to Mirathorn",
        "An approach-only prepared scene.",
    ])
    source = _admit_worldbuilding(tmp_path, text=source_text)
    source_lines = source.source_text.splitlines()

    def ref_for(line_text: str) -> dict[str, Any]:
        line_number = next(
            index for index, value in enumerate(source_lines, start=1)
            if value == line_text
        )
        span = next(
            item for item in source.source_span_index["spans"]
            if item["start_line"] <= line_number <= item["end_line"]
        )
        return {
            "source_span_ref_id": span["source_span_id"],
            "anchor_quotes": [line_text],
        }

    outputs = {
        "location_pass": {"observation_nodes": [{
            "node_id": "place:exampleland", "label": "The Exampleland",
            "node_type": "location", "description": "A source-backed place.",
            "importance": "medium",
            "evidence_refs": [ref_for("#### Fantastic Livestock for the Exampleland")],
        }, {
            "node_id": "scene:gate", "label": "Main Gate Scene",
            "node_type": "location", "description": "A source-backed prepared scene.",
            "importance": "medium",
            "evidence_refs": [ref_for("An approach-only prepared scene.")],
        }]},
        "definition_pass": {"observation_nodes": [{
            "node_id": "event:goats", "label": "Float Goats Livestock Definition",
            "node_type": "event", "description": "The original species proposal.",
            "importance": "medium",
            "evidence_refs": [ref_for("Float Goats walk on water and carry goods across lakes.")],
        }]},
        "edge_pass": {"observation_edges": [{
            "edge_id": "edge:goats", "from_node_id": "event:goats",
            "to_node_id": "place:exampleland", "relationship_type": "located_in",
            "predicate_family": "spatial", "label": "",
            "evidence_refs": [ref_for("Float Goats walk on water and carry goods across lakes.")],
        }]},
    }
    class BoundedFixtureClient(BoundedRecapPassClient):
        def __init__(self):
            self.limits = SimpleNamespace(
                provider="openrouter", model=DEEPSEEK_MODEL, max_calls=8,
            )
            self.fixture = FixtureCategoryGraphPassClient(outputs)
            self.calls = []

        def run_pass(self, pass_name, **kwargs):
            result = self.fixture.run_pass(pass_name, **kwargs)
            self.calls.append({
                "pass_name": pass_name,
                "observation": None,
                "external_outcome": "completed",
            })
            return result

    fixture_client = BoundedFixtureClient()

    def extract_with_extra_review_qualifier(options, *, client=None, progress_callback=None):
        result = extract_category_candidate_graph(
            options, client=client, progress_callback=progress_callback,
        )
        diagnostics = copy.deepcopy(result.consolidation_diagnostics)
        proposal = diagnostics["source_section_retention"][
            "livestock_semantic_hygiene"]["deferred_proposals"][
                "deferred:livestock-section:edge:edge:goats"]["proposal"]
        proposal["qualifiers"] = {"certainty": "qualified", "scope": "Exampleland"}
        return dataclass_replace(result, consolidation_diagnostics=diagnostics)

    monkeypatch.setattr(
        "src.graph_memory.extraction.graph_preview_runner.extract_category_candidate_graph",
        extract_with_extra_review_qualifier,
    )
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=GAZETTEER_PREPARED_SCENARIO_PROFILE.profile_id,
            profile_version=GAZETTEER_PREPARED_SCENARIO_PROFILE.profile_version,
            model_id=DEEPSEEK_MODEL,
            allow_llm=True,
            category_client=fixture_client,
        )
    )

    assert result.failure_kind is None
    assert result.run.status == ExtractionRunStatus.REVIEWABLE
    loaded = get_extraction_run(tmp_path, result.run.run_id)
    diagnostics_ref = loaded.components["consolidation_diagnostics"]
    from application_state.ingest.components import get_component_bytes
    diagnostics_bytes = get_component_bytes(run_id=loaded.run_id, kind=diagnostics_ref.kind,
        content_sha256=diagnostics_ref.sha256)
    assert diagnostics_ref.sha256 == hashlib.sha256(diagnostics_bytes).hexdigest()
    assert diagnostics_ref.exists
    assert not list(tmp_path.rglob("consolidation_diagnostics.json"))
    diagnostics = json.loads(diagnostics_bytes)
    proposals = diagnostics["source_section_retention"][
        "livestock_semantic_hygiene"]["deferred_proposals"]
    edge_proposal = proposals[
        "deferred:livestock-section:edge:edge:goats"]["proposal"]
    assert edge_proposal["label"] == ""
    assert edge_proposal["from_node_id"] == "event:goats"
    assert edge_proposal["to_node_id"] == "place:exampleland"
    assert edge_proposal["relationship_type"] == "located_in"
    assert edge_proposal["qualifiers"] == {
        "certainty": "qualified", "scope": "Exampleland",
    }
    assert edge_proposal["evidence_refs"][0]["source_artifact_id"] == source.source_artifact_id
    assert edge_proposal["evidence_refs"][0]["source_ref_id"] == f"{source.source_artifact_id}:text"
    scenario_proposal = diagnostics["source_section_retention"][
        "prepared_scenario_scope"]["deferred_proposals"][
            "deferred:prepared-scenario:node:scene:gate"]["proposal"]
    assert scenario_proposal["evidence_refs"][0]["source_artifact_id"] == source.source_artifact_id
    assert scenario_proposal["evidence_refs"][0]["source_ref_id"] == f"{source.source_artifact_id}:text"

    span_ref = loaded.components["source_span_index"]
    span_index = json.loads(get_component_bytes(run_id=loaded.run_id, kind=span_ref.kind,
        content_sha256=span_ref.sha256))
    span_ids = {item["source_span_id"] for item in span_index["spans"]}
    assert edge_proposal["evidence_refs"][0]["source_span_ref_id"] in span_ids
    candidate_ref = loaded.components["candidate_graph"]
    candidate = json.loads(get_component_bytes(run_id=loaded.run_id, kind=candidate_ref.kind,
        content_sha256=candidate_ref.sha256))
    candidate_node_ids = {item["node_id"] for item in candidate["nodes"]}
    assert "event:goats" not in candidate_node_ids
    assert "scene:gate" not in candidate_node_ids
    assert scenario_proposal["evidence_refs"][0]["source_span_ref_id"] in span_ids
    assert all(
        edge["from_node_id"] in candidate_node_ids
        and edge["to_node_id"] in candidate_node_ids
        for edge in candidate["edges"]
    )
    assert_immutable_component_refs(tmp_path, loaded, expected_revision=loaded.revision)


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
            initial_lineage=_recap_run_lineage(source),
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
            initial_lineage=_recap_run_lineage(source),
        )
    )
    loaded = get_extraction_run(tmp_path, result.run.run_id)
    assert loaded.status == ExtractionRunStatus.REVIEWABLE
    assert loaded.source_artifact_id == source.source_artifact_id
    assert ":" in source.source_artifact_id.split("session-24")[-1]

    from application_state.ingest.components import get_component_bytes
    graph_ref = loaded.components["candidate_graph"]
    graph = json.loads(get_component_bytes(run_id=loaded.run_id, kind=graph_ref.kind,
        content_sha256=graph_ref.sha256))
    span_ref = loaded.components["source_span_index"]
    span_index = json.loads(get_component_bytes(run_id=loaded.run_id, kind=span_ref.kind,
        content_sha256=span_ref.sha256))
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
        world_id="world:elderwyld",
        campaign_id="longmont-c2",
        session_id="session-24",
        recap_path=recap_path,
    )
    assert recap_path.read_text(encoding="utf-8") == original
    assert first.uri == f"object://{first.source_artifact_id}"
    import hashlib
    assert first.content_sha256 == hashlib.sha256(original.encode()).hexdigest()

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
            initial_lineage=_recap_run_lineage(
                _normalized_from_artifact(tmp_path, first.source_artifact_id)
            ),
        )
    )
    assert first_run.run.status == ExtractionRunStatus.REVIEWABLE

    recap_path.write_text(edited, encoding="utf-8")
    second = create_recap_source_artifact(
        tmp_path,
        world_id="world:elderwyld",
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
    from apps.live_control_server.services.graph_run_registry import load_run_source_input
    assert load_run_source_input(tmp_path, reloaded)[1].decode().startswith("Alpha")


def test_production_source_actor_uses_hydrated_spans_without_registry_suppression(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = "TestHero walks into Mirathorn.\n\nGuards watch the gate.\n"
    source = _admit_recap(tmp_path, text)
    span_ref = _first_paragraph_span_id(source)

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
            initial_lineage=_recap_run_lineage(source),
        )
    )
    labels = {n.get("label") for n in (result.candidate_graph or {}).get("nodes") or []}
    assert "TestHero" in labels
    assert "provenance_index" not in result.run.components


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

    from apps.live_control_server.services.graph_run_registry import get_reviewable_extraction_run
    mutable_source = tmp_path / source.source_uri.removeprefix("repo://")
    from apps.live_control_server.services.graph_run_registry import load_run_source_input
    frozen_bytes = load_run_source_input(tmp_path, loaded)[1]
    from apps.live_control_server.services.source_artifact_registry import get_source_artifact
    from apps.live_control_server.services.workspace_document_registry import get_workspace_document_snapshot
    from apps.live_control_server.services.tiptap_markdown_write import (
        prepare_tiptap_markdown_write, commit_tiptap_markdown_write,
        TiptapMarkdownWritePrepareRequest, TiptapMarkdownWriteCommitRequest,
    )
    artifact = get_source_artifact(tmp_path, loaded.source_artifact_id)
    before = get_workspace_document_snapshot(tmp_path, artifact.workspace_document_id)
    updated_text = "Mirathorn changed after extraction.\n"
    prepared_write = prepare_tiptap_markdown_write(root=tmp_path, request=TiptapMarkdownWritePrepareRequest(
        document_id=before.record.document_id, markdown=updated_text,
        expected_revision=before.loaded_revision, write_mode="authoring"))
    commit_tiptap_markdown_write(root=tmp_path, request=TiptapMarkdownWriteCommitRequest(
        document_id=before.record.document_id, markdown=updated_text,
        expected_revision=before.loaded_revision, write_mode="authoring",
        writer_confirm_token=prepared_write.writer_confirm_token))

    reopened = get_reviewable_extraction_run(tmp_path, loaded.run_id)
    assert reopened.components["source_artifact"].sha256 == loaded.components["source_artifact"].sha256
    assert load_run_source_input(tmp_path, reopened)[1] == frozen_bytes
    import subprocess
    import sys
    script = """import sys
from pathlib import Path
from apps.live_control_server.services.graph_run_registry import load_reviewable_extraction_data
review=load_reviewable_extraction_data(Path(sys.argv[1]),sys.argv[2])
assert review.run.run_id==sys.argv[2] and review.source_bytes and review.candidate_bytes and review.span_bytes
print('fresh-process registered components verified')
"""
    proof = subprocess.run([sys.executable, "-c", script, str(tmp_path), loaded.run_id],
                           check=True, capture_output=True, text=True)
    assert "registered components verified" in proof.stdout
    from apps.live_control_server.services.graph_run_registry import (
        assert_run_reviewable_evidence,
    )
    alternate = tmp_path / "alternate-source.md"
    alternate.write_bytes(frozen_bytes)
    bad_components = dict(loaded.components)
    bad_components["source_artifact"] = loaded.components["source_artifact"].model_copy(
        update={"uri": "repo://alternate-source.md"})
    assert_run_reviewable_evidence(tmp_path, loaded.model_copy(update={"components": bad_components}))
    mutable_source.parent.mkdir(parents=True, exist_ok=True)
    mutable_source.write_text("Corrupt operational source copy\n")
    assert get_reviewable_extraction_run(tmp_path, loaded.run_id) == loaded


def _run_recap_extraction(
    tmp_path: Path,
    *,
    client: FixtureClient,
):
    source = _admit_recap(tmp_path)
    if client.span_ref is None:
        client.span_ref = _first_paragraph_span_id(source)
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            allow_llm=True,
            category_client=client,
            initial_lineage=_recap_run_lineage(source),
        )
    )
    return source, result


def _mutate_extracted_candidate(
    monkeypatch: pytest.MonkeyPatch, mutator: Any
) -> None:
    from src.graph_memory.extraction import graph_preview_runner as runner

    real = runner.extract_category_candidate_graph

    def _wrapped(options: Any, client: Any = None) -> Any:
        extracted = real(options, client=client)
        mutated = mutator(copy.deepcopy(extracted.candidate_graph))
        return replace(extracted, candidate_graph=mutated)

    monkeypatch.setattr(runner, "extract_category_candidate_graph", _wrapped)


def _duplicate_first_node(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = list(graph.get("nodes") or [])
    assert nodes, "expected assembled nodes before duplicate injection"
    graph["nodes"] = [*nodes, copy.deepcopy(nodes[0])]
    return graph


def _duplicate_first_edge(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = list(graph.get("nodes") or [])
    assert nodes, "expected assembled nodes before duplicate-edge injection"
    seed = nodes[0]
    endpoint = str(seed.get("node_id") or "")
    edge = {
        "edge_id": "candidate:edge:dup",
        "from_node_id": endpoint,
        "to_node_id": endpoint,
        "relationship_type": "located_at",
        "label": "located at",
        "semantic_state": copy.deepcopy(seed.get("semantic_state") or {}),
        "evidence_refs": copy.deepcopy(seed.get("evidence_refs") or []),
        "proposed_action": "create",
        "confidence": "medium",
        "warnings": [],
    }
    graph["edges"] = [copy.deepcopy(edge), copy.deepcopy(edge)]
    return graph


def _duplicate_first_node_and_add_sublocation(graph: dict[str, Any]) -> dict[str, Any]:
    graph = _duplicate_first_node(graph)
    seed = graph["nodes"][0]
    extra = copy.deepcopy(seed)
    extra["node_id"] = "candidate:medical-wing"
    extra["label"] = "Medical Wing"
    extra["node_type"] = "sublocation"
    extra["description"] = "injected unsupported sublocation"
    graph["nodes"].append(extra)
    return graph


@pytest.mark.parametrize(
    ("mutator", "issue_code", "id_key", "collection"),
    [
        (_duplicate_first_node, "duplicate_node_id", "node_id", "nodes"),
        (_duplicate_first_edge, "duplicate_edge_id", "edge_id", "edges"),
    ],
)
def test_duplicate_ids_fail_generation_as_integrity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutator: Any,
    issue_code: str,
    id_key: str,
    collection: str,
) -> None:
    source = _admit_recap(tmp_path)
    span_ref = _first_paragraph_span_id(source)
    _mutate_extracted_candidate(monkeypatch, mutator)
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            allow_llm=True,
            category_client=FixtureClient(span_ref=span_ref),
            initial_lineage=_recap_run_lineage(source),
        )
    )
    loaded = get_extraction_run(tmp_path, result.run.run_id)
    item_ids = [
        item.get(id_key)
        for item in (result.candidate_graph or {}).get(collection) or []
        if isinstance(item, dict)
    ]
    assert result.failure_kind == "validation"
    assert loaded.status == ExtractionRunStatus.FAILED
    assert loaded.lineage.get("reviewable") is False
    assert issue_code in " ".join(result.diagnostics)
    assert item_ids
    assert len(item_ids) != len(set(item_ids))


def test_unexpected_typed_parse_exception_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(_data: Any) -> Any:
        raise RuntimeError("unexpected typed parse")

    monkeypatch.setattr(
        "src.graph_memory.candidate_document_integrity.candidate_graph_preview_from_dict",
        _boom,
    )
    _source, result = _run_recap_extraction(
        tmp_path,
        client=FixtureClient(),
    )
    loaded = get_extraction_run(tmp_path, result.run.run_id)
    assert result.failure_kind == "validation"
    assert loaded.status == ExtractionRunStatus.FAILED
    assert loaded.lineage.get("reviewable") is False
    assert any("preview parse failed" in item for item in result.diagnostics)
    assert any("unexpected typed parse" in item for item in result.diagnostics)


def test_unsupported_sublocation_reaches_reviewable_unchanged(tmp_path: Path) -> None:
    _source, result = _run_recap_extraction(
        tmp_path,
        client=FixtureClient(mode="unsupported_sublocation"),
    )
    loaded = get_extraction_run(tmp_path, result.run.run_id)
    frozen = copy.deepcopy(result.candidate_graph)
    assert result.failure_kind is None
    assert loaded.status == ExtractionRunStatus.REVIEWABLE
    nodes = list((result.candidate_graph or {}).get("nodes") or [])
    unsupported = [
        node
        for node in nodes
        if isinstance(node, dict) and node.get("node_id") == "candidate:medical-wing"
    ]
    assert len(unsupported) == 1
    assert unsupported[0]["node_type"] == "sublocation"
    assert result.candidate_graph == frozen


def test_reviewable_unsupported_candidate_is_exact_admission_input(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.models.world_graph_mutation_context import (
        WorldGraphMutationContext,
    )
    from apps.live_control_server.services.candidate_graph_admission import (
        canonical_candidate_digest,
        prepare_candidate_graph_admission,
    )

    source, result = _run_recap_extraction(
        tmp_path,
        client=FixtureClient(mode="unsupported_sublocation"),
    )
    loaded = get_extraction_run(tmp_path, result.run.run_id)
    assert loaded.status == ExtractionRunStatus.REVIEWABLE
    candidate = result.candidate_graph or {}
    frozen = copy.deepcopy(candidate)
    exact_digest = canonical_candidate_digest(candidate)

    revision = source.source_sha256
    if not revision.startswith("sha256:"):
        revision = f"sha256:{revision}"
    from apps.live_control_server.services.source_artifact_registry import (
        get_source_artifact, load_registered_source_artifact_bytes,
    )

    prepared = prepare_candidate_graph_admission(
        source_body=load_registered_source_artifact_bytes(tmp_path, source.source_artifact_id)[1],
        candidate_graph=candidate,
        source_uri=source.source_uri,
        source_revision_id=revision,
        prepared_by="gm@test",
        world_id="world:elderwyld",
        source_artifact_id=source.source_artifact_id,
        source_artifact=get_source_artifact(tmp_path, source.source_artifact_id),
        campaign_scope="longmont-c2",
        candidate_graph_path=str(tmp_path / "candidate_graph.json"),
        repo_root=tmp_path,
        mutation_context=WorldGraphMutationContext(
            world_id="world:elderwyld",
            revision_id="rev:d0",
            head_revision_id="rev:d0",
            objects={},
        ),
        source_admission=_ContractFakeSourceAdmission(),
    )
    binding = prepared.review_package["effect"]["candidate_admission"]
    assert candidate == frozen
    assert binding["candidate_digest"] == exact_digest
    assert {
        (item["item_id"], item["reason"])
        for item in binding["dispositions"]
        if item["reason"] == "unsupported_node_type"
    } == {("candidate:medical-wing", "unsupported_node_type")}


def test_integrity_failure_outranks_unsupported_eligibility(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _admit_recap(tmp_path)
    span_ref = _first_paragraph_span_id(source)
    _mutate_extracted_candidate(monkeypatch, _duplicate_first_node_and_add_sublocation)
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            allow_llm=True,
            category_client=FixtureClient(span_ref=span_ref),
            initial_lineage=_recap_run_lineage(source),
        )
    )
    loaded = get_extraction_run(tmp_path, result.run.run_id)
    graph = result.candidate_graph or {}
    node_ids = [node.get("node_id") for node in graph.get("nodes") or []]
    assert result.failure_kind == "validation"
    assert loaded.status == ExtractionRunStatus.FAILED
    assert "duplicate_node_id" in " ".join(result.diagnostics)
    assert "candidate:medical-wing" in node_ids
    assert len(node_ids) != len(set(node_ids))


def test_valid_candidate_semantics_are_unchanged_by_integrity_classification(
    tmp_path: Path,
) -> None:
    from src.graph_memory.candidate_document_integrity import (
        classify_candidate_document_integrity,
    )

    _source, result = _run_recap_extraction(
        tmp_path,
        client=FixtureClient(),
    )
    loaded = get_extraction_run(tmp_path, result.run.run_id)
    candidate = result.candidate_graph or {}
    frozen = copy.deepcopy(candidate)
    classification = classify_candidate_document_integrity(candidate)
    assert loaded.status == ExtractionRunStatus.REVIEWABLE
    assert classification.is_document_integrity_failure is False
    assert classification.eligibility_issues == ()
    assert candidate == frozen


def test_profile_post_extraction_validator_still_fails_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.graph_memory.extraction.extraction_profile import require_admitted_profile

    real = require_admitted_profile

    def _with_validator(*args: Any, **kwargs: Any) -> Any:
        profile = real(*args, **kwargs)
        return replace(
            profile,
            post_extraction_validator=lambda _graph: ["synthetic profile bound"],
        )

    monkeypatch.setattr(
        "src.graph_memory.extraction.graph_preview_runner.require_admitted_profile",
        _with_validator,
    )
    _source, result = _run_recap_extraction(
        tmp_path,
        client=FixtureClient(),
    )
    loaded = get_extraction_run(tmp_path, result.run.run_id)
    assert result.failure_kind == "validation"
    assert loaded.status == ExtractionRunStatus.FAILED
    assert any("profile post-extraction validation failed" in item for item in result.diagnostics)


def test_recap_snapshot_rejects_path_escape(tmp_path: Path) -> None:
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
    )

    with pytest.raises(SourceArtifactRegistryError, match="safe path segment"):
        create_recap_source_artifact(
            tmp_path,
            world_id="fixture-world",
            campaign_id="../..",
            session_id="session-24",
            recap_text="escape attempt\n",
        )
    with pytest.raises(SourceArtifactRegistryError, match="safe path segment"):
        create_recap_source_artifact(
            tmp_path,
            world_id="fixture-world",
            campaign_id="longmont-c2",
            session_id="session-24/../evil",
            recap_text="escape attempt\n",
        )


def test_production_outputs_survive_deleted_files_in_ingest_store(tmp_path, monkeypatch):
    import hashlib
    from application_state.ingest.components import get_component_bytes
    source = _admit_worldbuilding(tmp_path)
    result = run_production_extraction(ProductionExtractionRequest(
        repo_root=tmp_path, source=source,
        profile_id=WORLDBUILDING_PLUMBING_PROFILE_ID,
        profile_version=WORLDBUILDING_PLUMBING_PROFILE_VERSION,
        allow_llm=True, category_client=FixtureClient(span_ref=_first_paragraph_span_id(source)),
    ))
    assert result.run.status == ExtractionRunStatus.REVIEWABLE
    expected = {}
    for name, ref in result.run.components.items():
        if name == "source_artifact":
            continue
        path = tmp_path / ref.uri.removeprefix("repo://")
        expected[name] = get_component_bytes(run_id=result.run.run_id, kind=ref.kind,
            content_sha256=ref.sha256)
        if path.is_file():
            assert path.read_bytes() == expected[name]
            path.unlink()
    monkeypatch.setattr(Path, "read_bytes", lambda *a, **k: pytest.fail("output read file"))
    monkeypatch.setattr(Path, "read_text", lambda *a, **k: pytest.fail("output read file"))
    for name, raw in expected.items():
        ref = result.run.components[name]
        actual = get_component_bytes(run_id=result.run.run_id, kind=ref.kind, content_sha256=ref.sha256)
        assert actual == raw
        assert hashlib.sha256(actual).hexdigest() == ref.sha256
    assert json.loads(expected["candidate_graph"]) == result.candidate_graph
    assert json.loads(expected["source_span_index"]) == result.source_span_index


def test_production_json_outputs_do_not_require_file_storage(tmp_path, monkeypatch):
    from application_state.ingest.components import get_component_bytes
    source = _admit_recap(tmp_path)
    def json_files():
        return {str(p.relative_to(tmp_path)): p.read_bytes()
                for p in tmp_path.rglob("*.json")}
    before = json_files()
    original = Path.write_bytes
    def no_json_mirror(path, data):
        if path.name in {"source_span_index.json", "candidate_graph.json", "known_entity_mentions.json"}:
            raise OSError("synthetic JSON mirror unavailable")
        return original(path, data)
    monkeypatch.setattr(Path, "write_bytes", no_json_mirror)
    result = run_production_extraction(ProductionExtractionRequest(
        repo_root=tmp_path, source=source, profile_id=RECAP_PROFILE_ID,
        profile_version=RECAP_PROFILE_VERSION, allow_llm=True,
        category_client=FixtureClient(span_ref=_first_paragraph_span_id(source)),
        initial_lineage=_recap_run_lineage(source)))
    assert result.run.status == ExtractionRunStatus.REVIEWABLE
    expected = {"candidate_graph":result.candidate_graph, "source_span_index":result.source_span_index}
    assert "provenance_index" not in result.run.components
    for kind, payload in expected.items():
        ref = result.run.components[kind]
        actual = get_component_bytes(run_id=result.run.run_id, kind=kind, content_sha256=ref.sha256)
        assert actual == (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    assert json_files() == before


@pytest.mark.parametrize("kind,expected_status", [
    ("source_span_index", "draft"), ("candidate_graph", "prepared"),
])
def test_database_json_output_failure_does_not_advertise_missing_output(tmp_path, monkeypatch, kind, expected_status):
    from application_state.ingest import components, service
    original = components.persist_component_payload
    def unavailable(**kwargs):
        if kwargs["kind"].value == kind:
            raise OSError("synthetic output store unavailable")
        return original(**kwargs)
    monkeypatch.setattr(components, "persist_component_payload", unavailable)
    with pytest.raises(OSError, match="synthetic output store unavailable"):
        _run_recap_extraction(tmp_path, client=FixtureClient())
    [saved] = service.list_extraction_runs()
    assert saved.status.value == expected_status
    assert kind not in saved.components
    assert not list(tmp_path.rglob("candidate_graph.json"))


def test_controller_needs_no_source_snapshot_or_output_files(tmp_path, monkeypatch):
    from apps.live_control_server.services.graph_run_registry import load_run_source_input
    source = _admit_worldbuilding(tmp_path)
    def snapshot():
        return {str(p.relative_to(tmp_path)):p.read_bytes() if p.is_file() else None
                for p in tmp_path.rglob("*")}
    before = snapshot()
    original = Path.open
    def no_snapshot(path, mode="r", *args, **kwargs):
        if path.name == "source.md" and mode == "xb":
            raise OSError("synthetic source mirror unavailable")
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", no_snapshot)
    result = run_production_extraction(ProductionExtractionRequest(repo_root=tmp_path, source=source,
        profile_id=WORLDBUILDING_PLUMBING_PROFILE_ID, profile_version=WORLDBUILDING_PLUMBING_PROFILE_VERSION,
        allow_llm=True, category_client=FixtureClient(span_ref=_first_paragraph_span_id(source))))
    assert result.run.status == ExtractionRunStatus.REVIEWABLE
    assert load_run_source_input(tmp_path, result.run)[1] == source.source_text.encode()
    assert snapshot() == before


@pytest.mark.parametrize("damage", ["normalized_digest", "registered_bytes"])
def test_source_input_mismatch_fails_before_inference(tmp_path, damage):
    import hashlib
    from apps.live_control_server.services.graph_run_registry import GraphRunRegistryError
    source = _admit_worldbuilding(tmp_path)
    if damage == "normalized_digest":
        source = replace(source, source_sha256="0" * 64)
    else:
        text = "Unregistered replacement source.\n"
        source = replace(source, source_text=text, source_sha256=hashlib.sha256(text.encode()).hexdigest())
    class NoInference:
        def run_pass(self, *args, **kwargs):
            pytest.fail("inference before source input validation")
    with pytest.raises((ValueError, GraphRunRegistryError), match="digest mismatch|component digest|registered input"):
        run_production_extraction(ProductionExtractionRequest(repo_root=tmp_path, source=source,
            profile_id=WORLDBUILDING_PLUMBING_PROFILE_ID, profile_version=WORLDBUILDING_PLUMBING_PROFILE_VERSION,
            allow_llm=True, category_client=NoInference()))
