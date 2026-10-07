"""A bounded candidate edit makes a new held recap child, never a World write."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import httpx
from fastapi import FastAPI

from application_state.ingest.service import (
    RecapSemanticBasisV2, RecapSemanticBasisV3, RecapSemanticBasisV4,
    RecapSemanticBasisV5, RecapSemanticBasisV6, _assert_recap_semantic_basis,
)
from application_state.errors import ApplicationStateConflictError
from apps.live_control_server.models.extract_promote import (
    RecapCandidateCorrectionRequest,
    RecapCandidateCorrectionRequestV2,
    RecapCandidateCorrectionRequestV3,
    RecapCandidateCorrectionRequestV4,
    RecapCandidateCorrectionRequestV5,
    RecapCandidateEvidenceReplacementV5,
    RecapCandidateEvidenceSpanReplacement,
    RecapCandidateEdgeTuple,
    RecapCandidateEdgeTupleReplacement,
    RecapNodeDescriptionReplacement,
    RecapSessionActionReplacement,
    RecapSemanticDecisionRequest,
)
from apps.live_control_server.services import recap_semantic_candidate_correction as service
from apps.live_control_server.services import extract_promote, graph_run_registry
from apps.live_control_server.models.extract_promote import ExtractPromotePrepareRequest
from apps.live_control_server.services.recap_semantic_disposition import (
    EFFECT_KEY, accepted_effect_binding,
)
from apps.live_control_server.routes import extract_promote as routes
from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal, native_graph_gm_dependency
from apps.live_control_server.services.graph_run_registry import GraphRunRegistryError
from apps.live_control_server.services.recap_semantic_disposition import assess_recap_semantics
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fixture(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    *,
    actions: bool = False,
    source_text: str = "Mira found the key under the bridge.\n",
):
    source = root / "source.md"
    source.write_text(source_text, encoding="utf-8")
    spans = root / "spans.json"
    spans.write_text('{"spans":[]}', encoding="utf-8")
    artifact_id = "artifact:recap:c:s:source"
    span_id = f"{artifact_id}:span:abc:1-1"
    node = {
        "node_id": "mira", "node_type": "character", "label": "Mira",
        "description": "Mira carried an uncertain object.", "importance": "medium",
        "semantic_state": {
            "canon_state": "played_canon", "lifecycle_state": "candidate",
            "evidence_role": "source_evidence", "authority_state": "system_derived",
            "visibility_state": "gm_private",
        },
        "proposed_action": "create", "confidence": "medium",
        "evidence_refs": [{
            "source_ref_id": "ref:mira", "source_artifact_id": artifact_id,
            "source_span_ref_id": span_id, "can_open_source": True,
            "can_highlight_span": True,
            "anchor_quotes": [source_text.strip()],
        }],
    }
    if actions:
        node["session_actions"] = ["Mira crossed the bridge.", "Mira dodged the key.", "Mira went home."]
    payload = {
        "schema": "dmb_candidate_graph_preview_v0", "version": "0.1",
        "preview_id": "preview:recap-semantic-test", "campaign_id": "c",
        "session_id": "s", "source_artifact_ids": [artifact_id],
        "status": "preview", "nodes": [node], "edges": [], "beats": [],
        "proposed_writes": [], "ignored_items": [], "deferred_items": [],
        "diagnostics": {
            "preview_only": True, "extraction_performed": False,
            "llm_used": False, "runtime_connected": False,
            "plan_connected": False, "agent_interaction_connected": False,
            "corpus_scanned": False, "corpus_mutated": False,
            "facts_promoted": False, "canon_promoted": False,
            "unresolved_evidence_refs": 0, "missing_evidence_objects": 0,
            "warning_count": 0,
        },
    }
    parent_file = root / "parent.json"
    parent_bytes = json.dumps(payload).encode()
    parent_file.write_bytes(parent_bytes)
    components = {
        kind.value: ExtractionRunComponentRef(
            kind=kind, uri=uri, sha256=_sha((root / uri).read_bytes()), exists=True,
        )
        for kind, uri in (
            (ExtractionRunComponentKind.SOURCE_ARTIFACT, "source.md"),
            (ExtractionRunComponentKind.SOURCE_SPAN_INDEX, "spans.json"),
            (ExtractionRunComponentKind.CANDIDATE_GRAPH, "parent.json"),
        )
    }
    parent = ExtractionRun(
        run_id="parent", source_artifact_id=artifact_id,
        source_domain="recap", campaign_id="c", session_id="s",
        profile_id=service.PROFILE, status=ExtractionRunStatus.REVIEWABLE,
        components=components,
    )
    runs = {"parent": parent}

    def resolve(run_id, **_kwargs):
        run = runs[run_id]
        return SimpleNamespace(
            run_id=run_id, source_domain="recap", extraction_profile=service.PROFILE,
            campaign_id="c", session_id="s", source_artifact_id=artifact_id,
            candidate_graph_path=root / run.components["candidate_graph"].uri,
            normalized_recap_path=source, source_span_index_path=spans,
            source_revision_id=_sha(source.read_bytes()),
        )

    def get_run(_root, run_id):
        try:
            return runs[run_id]
        except KeyError as exc:
            raise GraphRunRegistryError("missing", status_code=404) from exc

    def create_run(_root, **kwargs):
        run = ExtractionRun(**kwargs)
        runs[run.run_id] = run
        return run

    def update_run(_root, run_id, *, status, expected_revision):
        run = runs[run_id]
        assert run.revision == expected_revision
        updated = run.model_copy(update={"status": status, "revision": expected_revision + 1})
        runs[run_id] = updated
        return updated

    monkeypatch.setattr(service, "repo_root", lambda: root)
    monkeypatch.setattr(service, "resolve_promotable_ingest_run", resolve)
    monkeypatch.setattr(service, "get_extraction_run", get_run)
    monkeypatch.setattr(service, "create_extraction_run", create_run)
    monkeypatch.setattr(service, "update_extraction_run_status", update_run)
    monkeypatch.setattr(
        service, "_load_frozen_span_index_for_resolved_run",
        lambda _resolved: SimpleNamespace(spans=[SimpleNamespace(
            source_span_id=span_id, start_line=1, end_line=1,
        )]),
    )
    return parent, parent_bytes, runs


def _tuple_fixture(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    *,
    include_unmapped_edge: bool = False,
):
    source_text = "Mira found the key under the bridge. The tunnel opens into a chamber.\n"
    parent, _parent_bytes, runs = _fixture(monkeypatch, root, source_text=source_text)
    parent_path = root / parent.components["candidate_graph"].uri
    payload = json.loads(parent_path.read_bytes())
    evidence = payload["nodes"][0]["evidence_refs"]
    quote = source_text.strip()
    state = payload["nodes"][0]["semantic_state"]

    def node(node_id: str, node_type: str, label: str) -> dict:
        return {
            "node_id": node_id, "node_type": node_type, "label": label,
            "description": f"{label} from the session.", "importance": "medium",
            "semantic_state": state, "proposed_action": "create", "confidence": "medium",
            "evidence_refs": [{**evidence[0], "anchor_quotes": [quote]}],
        }

    payload["nodes"] = [
        node("mira", "character", "Mira"),
        node("key", "item", "Key"),
        node("tunnel", "location", "Tunnel"),
        node("chamber", "location", "Chamber"),
    ]
    payload["edges"] = [
        {
            "edge_id": "edge-possession", "from_node_id": "key", "relationship_type": "located_in",
            "to_node_id": "mira", "label": "found by",
            "semantic_state": state, "proposed_action": "create", "confidence": "medium",
            "evidence_refs": [{**evidence[0], "anchor_quotes": [quote]}],
        },
        {
            "edge_id": "edge-tunnel", "from_node_id": "chamber", "relationship_type": "located_in",
            "to_node_id": "tunnel", "label": "opens from",
            "semantic_state": state, "proposed_action": "create", "confidence": "medium",
            "evidence_refs": [{**evidence[0], "anchor_quotes": [quote]}],
        },
    ]
    if include_unmapped_edge:
        payload["edges"].append({
            "edge_id": "edge-membership", "from_node_id": "mira",
            "relationship_type": "located_in", "to_node_id": "key",
            "label": "associated with", "semantic_state": state,
            "proposed_action": "create", "confidence": "medium",
            "evidence_refs": [{**evidence[0], "anchor_quotes": [quote]}],
        })
    parent_bytes = json.dumps(payload).encode()
    parent_path.write_bytes(parent_bytes)
    components = dict(parent.components)
    components["candidate_graph"] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
        uri=parent.components["candidate_graph"].uri,
        sha256=_sha(parent_bytes),
        exists=True,
    )
    parent = parent.model_copy(update={"components": components})
    runs["parent"] = parent
    return parent, parent_bytes, runs


def _span_relocation_fixture(monkeypatch: pytest.MonkeyPatch, root: Path):
    source_text = "Mira found a key.\nThe tunnel opens into a chamber.\n"
    parent, parent_bytes, runs = _fixture(monkeypatch, root, source_text=source_text)
    spans_path = root / parent.components["source_span_index"].uri
    spans_path.write_text('{"spans":[{"source_span_id":"old","start_line":1,"end_line":1},{"source_span_id":"new","start_line":2,"end_line":2}]}', encoding="utf-8")
    span_id = f"{parent.source_artifact_id}:span:old:1-1"
    target_span_id = f"{parent.source_artifact_id}:span:new:2-2"
    payload = json.loads(parent_bytes)
    evidence = payload["nodes"][0]["evidence_refs"][0]
    evidence["source_span_ref_id"] = span_id
    evidence["anchor_quotes"] = ["Mira found a key."]
    parent_bytes = json.dumps(payload).encode()
    parent_path = root / parent.components["candidate_graph"].uri
    parent_path.write_bytes(parent_bytes)
    components = dict(parent.components)
    components["candidate_graph"] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
        uri=parent.components["candidate_graph"].uri,
        sha256=_sha(parent_bytes), exists=True,
    )
    components["source_span_index"] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
        uri=parent.components["source_span_index"].uri,
        sha256=_sha(spans_path.read_bytes()), exists=True,
    )
    parent = parent.model_copy(update={"components": components})
    runs["parent"] = parent
    monkeypatch.setattr(
        service, "_load_frozen_span_index_for_resolved_run",
        lambda _resolved: SimpleNamespace(spans=[
            SimpleNamespace(source_span_id=span_id, start_line=1, end_line=1),
            SimpleNamespace(source_span_id=target_span_id, start_line=2, end_line=2),
        ]),
    )
    request = RecapCandidateCorrectionRequestV4(
        schema="dmb_recap_candidate_correction_request_v4",
        parent_run_id="parent", parent_candidate_sha256=_sha(parent_bytes),
        evidence_span_replacements=[RecapCandidateEvidenceSpanReplacement(
            record_kind="node", record_id="mira", evidence_index=0,
            expected_source_ref_id="ref:mira",
            expected_source_artifact_id=parent.source_artifact_id,
            expected_source_span_ref_id=span_id,
            replacement_source_span_ref_id=target_span_id,
            expected_anchor_quotes=["Mira found a key."],
            replacement_anchor_quotes=["The tunnel opens into a chamber."],
        )],
    )
    return parent, parent_bytes, runs, request, target_span_id


def _evidence_batch_fixture(monkeypatch: pytest.MonkeyPatch, root: Path):
    parent, parent_bytes, runs = _tuple_fixture(monkeypatch, root)
    payload = json.loads(parent_bytes)
    source_ref = payload["nodes"][0]["evidence_refs"][0]
    expected_quotes = source_ref["anchor_quotes"]
    span_id = source_ref["source_span_ref_id"]
    source_ref_id = source_ref["source_ref_id"]
    artifact_id = parent.source_artifact_id
    operations = [
        ("node", "mira", 0, ["Mira found the key under the bridge."]),
        ("node", "key", 0, ["The tunnel opens into a chamber."]),
        ("node", "tunnel", 0, ["The tunnel opens into a chamber."]),
        ("edge", "edge-tunnel", 0, ["The tunnel opens into a chamber."]),
    ]
    request = RecapCandidateCorrectionRequestV5(
        schema="dmb_recap_candidate_correction_request_v5",
        parent_run_id="parent", parent_candidate_sha256=_sha(parent_bytes),
        evidence_replacements=[
            RecapCandidateEvidenceReplacementV5(
                record_kind=kind, record_id=record_id, evidence_index=index,
                expected_source_ref_id=source_ref_id,
                expected_source_artifact_id=artifact_id,
                expected_source_span_ref_id=span_id,
                replacement_source_span_ref_id=span_id,
                expected_anchor_quotes=expected_quotes,
                replacement_anchor_quotes=quotes,
            )
            for kind, record_id, index, quotes in operations
        ],
    )
    return parent, parent_bytes, runs, request


def _request(parent_bytes: bytes) -> RecapCandidateCorrectionRequest:
    return RecapCandidateCorrectionRequest(
        parent_run_id="parent", parent_candidate_sha256=_sha(parent_bytes),
        node_description_replacements=[RecapNodeDescriptionReplacement(
            node_id="mira", original_description="Mira carried an uncertain object.",
            replacement_description="Mira found the key under the bridge.",
        )],
    )


def _action_request(parent_bytes: bytes) -> RecapCandidateCorrectionRequestV2:
    return RecapCandidateCorrectionRequestV2(
        schema="dmb_recap_candidate_correction_request_v2",
        parent_run_id="parent", parent_candidate_sha256=_sha(parent_bytes),
        session_action_replacements=[RecapSessionActionReplacement(
            node_id="mira", action_index=1,
            expected_old_text="Mira dodged the key.",
            replacement_text="Mira found the key under the bridge.",
        )],
    )


def _tuple_request(parent_bytes: bytes) -> RecapCandidateCorrectionRequestV3:
    return RecapCandidateCorrectionRequestV3(
        schema="dmb_recap_candidate_correction_request_v3",
        parent_run_id="parent", parent_candidate_sha256=_sha(parent_bytes),
        edge_tuple_replacements=[
            RecapCandidateEdgeTupleReplacement(
                edge_id="edge-possession",
                expected_tuple=RecapCandidateEdgeTuple(
                    from_node_id="key", relationship_type="located_in",
                    to_node_id="mira", label="found by",
                ),
                replacement_tuple=RecapCandidateEdgeTuple(
                    from_node_id="mira", relationship_type="possesses",
                    to_node_id="key", label="has",
                ),
            ),
            RecapCandidateEdgeTupleReplacement(
                edge_id="edge-tunnel",
                expected_tuple=RecapCandidateEdgeTuple(
                    from_node_id="chamber", relationship_type="located_in",
                    to_node_id="tunnel", label="opens from",
                ),
                replacement_tuple=RecapCandidateEdgeTuple(
                    from_node_id="tunnel", relationship_type="leads_to",
                    to_node_id="chamber", label="opens up into",
                ),
            ),
        ],
    )


def _unmapped_membership_replacement() -> RecapCandidateEdgeTupleReplacement:
    return RecapCandidateEdgeTupleReplacement(
        edge_id="edge-membership",
        expected_tuple=RecapCandidateEdgeTuple(
            from_node_id="mira", relationship_type="located_in",
            to_node_id="key", label="associated with",
        ),
        replacement_tuple=RecapCandidateEdgeTuple(
            from_node_id="mira", relationship_type="part_of_group",
            to_node_id="key", label="member of",
        ),
    )


def test_edge_tuple_child_replays_atomically_and_stays_held(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs = _tuple_fixture(monkeypatch, tmp_path)
    original = json.loads(parent_bytes)
    request = _tuple_request(parent_bytes)
    response = service.correct_recap_candidate(request)
    child = runs[response.run_id]

    assert response.schema_ == "dmb_recap_candidate_correction_response_v3"
    assert child.lineage["derivation"] == service.DERIVATION_V3
    assert child.lineage["semantic_candidate_manifest"]["schema"] == service.MANIFEST_SCHEMA_V3
    assert child.lineage["semantic_disposition"]["state"] == "held"
    assert service.correct_recap_candidate(request) == response
    assert service.verify_child_replay(child, parent, tmp_path)
    assert (tmp_path / parent.components["candidate_graph"].uri).read_bytes() == parent_bytes

    candidate = json.loads((tmp_path / child.components["candidate_graph"].uri).read_bytes())
    expected = copy.deepcopy(original)
    expected_by_id = {edge["edge_id"]: edge for edge in expected["edges"]}
    expected_by_id["edge-possession"].update({
        "from_node_id": "mira", "relationship_type": "possesses",
        "to_node_id": "key", "label": "has",
    })
    expected_by_id["edge-tunnel"].update({
        "from_node_id": "tunnel", "relationship_type": "leads_to",
        "to_node_id": "chamber", "label": "opens up into",
    })
    assert candidate == expected
    for edge_id in ("edge-possession", "edge-tunnel"):
        before = next(edge for edge in original["edges"] if edge["edge_id"] == edge_id)
        after = next(edge for edge in candidate["edges"] if edge["edge_id"] == edge_id)
        assert after["edge_id"] == before["edge_id"]
        assert after["evidence_refs"] == before["evidence_refs"]

    assessment = assess_recap_semantics(
        child, parent=parent, source_revision_id=_sha((tmp_path / "source.md").read_bytes()), root=tmp_path,
    )
    assert assessment.marked and not assessment.accepted
    basis = RecapSemanticBasisV4.model_validate(assessment.basis)
    assert basis.digest() == response.semantic_basis_sha256
    from application_state.errors import ApplicationStateConflictError
    from application_state.ingest.service import _assert_recap_semantic_basis

    _assert_recap_semantic_basis(child, parent, basis)
    bad_manifest = copy.deepcopy(child.lineage["semantic_candidate_manifest"])
    bad_manifest["edge_tuple_replacements"][0]["arbitrary_patch"] = {"label": "forged"}
    bad_manifest_sha = _sha(service._canonical_bytes(bad_manifest))
    bad_child = child.model_copy(update={
        "lineage": {
            **child.lineage, "manifest_sha256": bad_manifest_sha,
            "semantic_candidate_manifest": bad_manifest,
        },
    })
    bad_assessment = assess_recap_semantics(
        bad_child, parent=parent,
        source_revision_id=_sha((tmp_path / "source.md").read_bytes()), root=tmp_path,
    )
    assert bad_assessment.marked and not bad_assessment.accepted
    with pytest.raises(ApplicationStateConflictError, match="edge tuple manifest is malformed"):
        _assert_recap_semantic_basis(
            bad_child, parent, basis.model_copy(update={"manifest_sha256": bad_manifest_sha}),
        )
    overlong_manifest = copy.deepcopy(child.lineage["semantic_candidate_manifest"])
    overlong_manifest["edge_tuple_replacements"] *= 4
    overlong_sha = _sha(service._canonical_bytes(overlong_manifest))
    overlong_child = child.model_copy(update={
        "lineage": {
            **child.lineage, "manifest_sha256": overlong_sha,
            "semantic_candidate_manifest": overlong_manifest,
        },
    })
    with pytest.raises(ApplicationStateConflictError, match="candidate manifest is missing"):
        _assert_recap_semantic_basis(
            overlong_child, parent, basis.model_copy(update={"manifest_sha256": overlong_sha}),
        )

    accepted_lineage = copy.deepcopy(child.lineage)
    accepted_lineage["semantic_disposition"] = {
        "version": 1, "state": "accepted", "basis_sha256": basis.digest(),
        "review_decision_ref": "review:tuple", "reviewer_id": "reviewer",
        "decided_at": "2026-10-07T00:00:00Z",
    }
    accepted_child = child.model_copy(update={"lineage": accepted_lineage})
    accepted_assessment = assess_recap_semantics(
        accepted_child, parent=parent,
        source_revision_id=_sha((tmp_path / "source.md").read_bytes()), root=tmp_path,
    )
    assert accepted_assessment.accepted
    binding = accepted_effect_binding(accepted_child, accepted_assessment)
    assert binding["manifest_sha256"] == child.lineage["manifest_sha256"]
    assert binding["derivation"] == service.DERIVATION_V3
    assert binding["manifest_schema"] == service.MANIFEST_SCHEMA_V3


def test_edge_tuple_batch_rejects_unmapped_entry_without_partial_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs = _tuple_fixture(monkeypatch, tmp_path, include_unmapped_edge=True)
    request = _tuple_request(parent_bytes).model_copy(update={
        "edge_tuple_replacements": [*_tuple_request(parent_bytes).edge_tuple_replacements, _unmapped_membership_replacement()],
    })

    with pytest.raises(extract_promote.ExtractPromoteError) as caught:
        service.correct_recap_candidate(request)
    assert caught.value.status_code == 422
    assert any(
        diagnostic.code == "edge_tuple_unmapped_predicate"
        and "edgeTupleReplacements[2]" in diagnostic.message
        for diagnostic in caught.value.diagnostics
    )
    assert set(runs) == {"parent"}
    assert (tmp_path / parent.components["candidate_graph"].uri).read_bytes() == parent_bytes
    assert not (tmp_path / "out" / "graph_memory" / "derived_candidates").exists()


def test_edge_tuple_replay_rejects_stale_unknown_and_duplicate_targets() -> None:
    parent = {
        "nodes": [
            {"node_id": "tunnel", "node_type": "location"},
            {"node_id": "chamber", "node_type": "location"},
        ],
        "edges": [{
            "edge_id": "edge-1", "from_node_id": "chamber", "relationship_type": "located_in",
            "to_node_id": "tunnel", "label": "inside", "evidence_refs": [{"anchor_quotes": ["the tunnel opens into a chamber"]}],
        }],
        "beats": [{"beat_id": "keep"}],
    }
    operation = {
        "edge_id": "edge-1",
        "expected_tuple": {
            "from_node_id": "chamber", "relationship_type": "located_in",
            "to_node_id": "tunnel", "label": "inside",
        },
        "replacement_tuple": {
            "from_node_id": "tunnel", "relationship_type": "leads_to",
            "to_node_id": "chamber", "label": "opens into",
        },
    }
    manifest = {"schema": service.MANIFEST_SCHEMA_V3, "edge_tuple_replacements": [operation]}
    replayed = service.replay_candidate(parent, manifest)
    assert replayed["beats"] == parent["beats"]
    assert replayed["edges"][0]["evidence_refs"] == parent["edges"][0]["evidence_refs"]
    assert parent["edges"][0]["relationship_type"] == "located_in"

    with pytest.raises(extract_promote.ExtractPromoteError) as stale:
        service.replay_candidate(parent, {**manifest, "edge_tuple_replacements": [{
            **operation, "expected_tuple": {**operation["expected_tuple"], "label": "stale"},
        }]})
    assert any(item.code == "edge_tuple_stale_preimage" for item in stale.value.diagnostics)
    with pytest.raises(extract_promote.ExtractPromoteError) as missing_endpoint:
        service.replay_candidate(parent, {**manifest, "edge_tuple_replacements": [{
            **operation, "replacement_tuple": {**operation["replacement_tuple"], "to_node_id": "missing"},
        }]})
    assert any(item.code == "edge_tuple_endpoint_missing_or_ambiguous" for item in missing_endpoint.value.diagnostics)
    with pytest.raises(extract_promote.ExtractPromoteError) as unknown_predicate:
        service.replay_candidate(parent, {**manifest, "edge_tuple_replacements": [{
            **operation, "replacement_tuple": {**operation["replacement_tuple"], "relationship_type": "invented_relation"},
        }]})
    assert any(item.code == "edge_tuple_unknown_predicate" for item in unknown_predicate.value.diagnostics)
    with pytest.raises(extract_promote.ExtractPromoteError) as inadmissible_kinds:
        service.replay_candidate(parent, {**manifest, "edge_tuple_replacements": [{
            **operation, "replacement_tuple": {
                **operation["replacement_tuple"],
                "from_node_id": "tunnel", "relationship_type": "possesses",
                "to_node_id": "chamber",
            },
        }]})
    assert any(item.code == "edge_tuple_endpoint_kind_not_admitted" for item in inadmissible_kinds.value.diagnostics)
    with pytest.raises(extract_promote.ExtractPromoteError) as duplicate_id:
        service.replay_candidate(parent, {**manifest, "edge_tuple_replacements": [operation, operation]})
    assert any(item.code == "edge_tuple_duplicate_edge_id" for item in duplicate_id.value.diagnostics)
    duplicate_parent = copy.deepcopy(parent)
    duplicate_parent["edges"].append({**copy.deepcopy(parent["edges"][0]), "edge_id": "edge-2"})
    with pytest.raises(extract_promote.ExtractPromoteError) as duplicate_target:
        service.replay_candidate(duplicate_parent, {**manifest, "edge_tuple_replacements": [operation, {
            **operation, "edge_id": "edge-2",
        }]})
    assert any(item.code == "edge_tuple_duplicate_target" for item in duplicate_target.value.diagnostics)
    with pytest.raises(ValueError):
        RecapCandidateCorrectionRequestV3(
            schema="dmb_recap_candidate_correction_request_v3",
            parent_run_id="parent", parent_candidate_sha256="a" * 64,
            edge_tuple_replacements=[_tuple_request(b"{}").edge_tuple_replacements[0]] * 8,
        )
    with pytest.raises(ValueError):
        RecapCandidateEdgeTuple(
            from_node_id="tunnel\n", relationship_type="leads_to",
            to_node_id="chamber", label="opens into",
        )


def test_evidence_span_child_replays_same_source_and_stays_held(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs, request, target_span_id = _span_relocation_fixture(monkeypatch, tmp_path)
    parent_payload = json.loads(parent_bytes)
    response = service.correct_recap_candidate(request)
    child = runs[response.run_id]

    assert response.schema_ == "dmb_recap_candidate_correction_response_v4"
    assert child.lineage["derivation"] == service.DERIVATION_V4
    assert child.lineage["semantic_candidate_manifest"]["schema"] == service.MANIFEST_SCHEMA_V4
    assert child.lineage["semantic_disposition"]["state"] == "held"
    assert service.correct_recap_candidate(request) == response
    assert service.verify_child_replay(child, parent, tmp_path)
    assert (tmp_path / parent.components["candidate_graph"].uri).read_bytes() == parent_bytes
    assert child.components["source_artifact"] == parent.components["source_artifact"]
    assert child.components["source_span_index"] == parent.components["source_span_index"]

    candidate = json.loads((tmp_path / child.components["candidate_graph"].uri).read_bytes())
    expected = copy.deepcopy(parent_payload)
    expected_ref = expected["nodes"][0]["evidence_refs"][0]
    expected_ref["source_span_ref_id"] = target_span_id
    expected_ref["anchor_quotes"] = ["The tunnel opens into a chamber."]
    assert candidate == expected
    assert candidate["nodes"][0]["node_id"] == parent_payload["nodes"][0]["node_id"]
    assert candidate["nodes"][0]["evidence_refs"][0]["source_ref_id"] == "ref:mira"

    assessment = assess_recap_semantics(
        child, parent=parent, source_revision_id=_sha((tmp_path / "source.md").read_bytes()), root=tmp_path,
    )
    assert assessment.marked and not assessment.accepted
    basis = RecapSemanticBasisV5.model_validate(assessment.basis)
    assert basis.digest() == response.semantic_basis_sha256
    _assert_recap_semantic_basis(child, parent, basis)
    accepted_lineage = copy.deepcopy(child.lineage)
    accepted_lineage["semantic_disposition"] = {
        "version": 1, "state": "accepted", "basis_sha256": basis.digest(),
        "review_decision_ref": "review:span", "reviewer_id": "reviewer",
        "decided_at": "2026-10-07T00:00:00Z",
    }
    accepted_child = child.model_copy(update={"lineage": accepted_lineage})
    accepted_assessment = assess_recap_semantics(
        accepted_child, parent=parent,
        source_revision_id=_sha((tmp_path / "source.md").read_bytes()), root=tmp_path,
    )
    binding = accepted_effect_binding(accepted_child, accepted_assessment)
    assert binding["derivation"] == service.DERIVATION_V4
    assert binding["manifest_schema"] == service.MANIFEST_SCHEMA_V4


@pytest.mark.parametrize(
    "failure",
    ["stale-parent", "stale-preimage", "foreign-span", "nonliteral-quote", "source-hash", "index-hash"],
)
def test_evidence_span_reanchor_rejects_before_any_child_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str
) -> None:
    parent, parent_bytes, runs, request, _target_span_id = _span_relocation_fixture(monkeypatch, tmp_path)
    operation = request.evidence_span_replacements[0]
    if failure == "stale-parent":
        request = request.model_copy(update={"parent_candidate_sha256": "0" * 64})
    elif failure == "stale-preimage":
        operation = operation.model_copy(update={"expected_source_span_ref_id": "stale-span"})
        request = request.model_copy(update={"evidence_span_replacements": [operation]})
    elif failure == "foreign-span":
        operation = operation.model_copy(update={
            "replacement_source_span_ref_id": "artifact:other:span:foreign:2-2",
        })
        request = request.model_copy(update={"evidence_span_replacements": [operation]})
    elif failure == "nonliteral-quote":
        operation = operation.model_copy(update={"replacement_anchor_quotes": ["not in the source"]})
        request = request.model_copy(update={"evidence_span_replacements": [operation]})
    elif failure in {"source-hash", "index-hash"}:
        key = "source_artifact" if failure == "source-hash" else "source_span_index"
        components = dict(parent.components)
        original_ref = components[key]
        components[key] = original_ref.model_copy(update={"sha256": "f" * 64})
        parent = parent.model_copy(update={"components": components})
        runs["parent"] = parent

    with pytest.raises(extract_promote.ExtractPromoteError):
        service.correct_recap_candidate(request)
    assert set(runs) == {"parent"}
    assert (tmp_path / "parent.json").read_bytes() == parent_bytes
    assert not (tmp_path / "out" / "graph_memory" / "derived_candidates").exists()


def test_v5_evidence_replacement_batch_replays_as_one_held_full_valid_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs, request = _evidence_batch_fixture(monkeypatch, tmp_path)
    response = service.correct_recap_candidate(request)
    child = runs[response.run_id]

    assert response.schema_ == "dmb_recap_candidate_correction_response_v5"
    assert child.lineage["derivation"] == service.DERIVATION_V5
    manifest = child.lineage["semantic_candidate_manifest"]
    assert manifest["schema"] == service.MANIFEST_SCHEMA_V5
    assert len(manifest["evidence_span_replacements"]) == 4
    assert child.lineage["semantic_disposition"]["state"] == "held"
    assert service.verify_child_replay(child, parent, tmp_path)
    assert (tmp_path / "parent.json").read_bytes() == parent_bytes

    candidate = json.loads((tmp_path / child.components["candidate_graph"].uri).read_bytes())
    assert candidate["nodes"][0]["evidence_refs"][0]["anchor_quotes"] == [
        "Mira found the key under the bridge."
    ]
    assert candidate["edges"][1]["evidence_refs"][0]["anchor_quotes"] == [
        "The tunnel opens into a chamber."
    ]
    assessment = assess_recap_semantics(
        child, parent=parent, source_revision_id=_sha((tmp_path / "source.md").read_bytes()),
        root=tmp_path,
    )
    assert assessment.marked and not assessment.accepted
    basis = RecapSemanticBasisV6.model_validate(assessment.basis)
    assert basis.derivation == service.DERIVATION_V5
    assert basis.manifest_schema == service.MANIFEST_SCHEMA_V5
    assert basis.digest() == response.semantic_basis_sha256
    _assert_recap_semantic_basis(child, parent, basis)
    duplicated_lineage = copy.deepcopy(child.lineage)
    duplicated_lineage["semantic_candidate_manifest"]["evidence_span_replacements"].append(
        copy.deepcopy(manifest["evidence_span_replacements"][0])
    )
    with pytest.raises(ApplicationStateConflictError):
        _assert_recap_semantic_basis(
            child.model_copy(update={"lineage": duplicated_lineage}), parent, basis,
        )
    accepted_lineage = copy.deepcopy(child.lineage)
    accepted_lineage["semantic_disposition"] = {
        "version": 1, "state": "accepted", "basis_sha256": basis.digest(),
        "review_decision_ref": "review:batch", "reviewer_id": "reviewer",
        "decided_at": "2026-10-07T00:00:00Z",
    }
    accepted_child = child.model_copy(update={"lineage": accepted_lineage})
    accepted_assessment = assess_recap_semantics(
        accepted_child, parent=parent,
        source_revision_id=_sha((tmp_path / "source.md").read_bytes()), root=tmp_path,
    )
    assert accepted_assessment.accepted
    assert accepted_effect_binding(accepted_child, accepted_assessment)["manifest_schema"] == (
        service.MANIFEST_SCHEMA_V5
    )


def test_v5_evidence_replacement_batch_rejects_bad_operation_before_any_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _parent, parent_bytes, runs, request = _evidence_batch_fixture(monkeypatch, tmp_path)
    operations = list(request.evidence_replacements)
    operations[1] = operations[1].model_copy(update={"expected_anchor_quotes": ["stale preimage"]})
    request = request.model_copy(update={"evidence_replacements": operations})

    with pytest.raises(extract_promote.ExtractPromoteError):
        service.correct_recap_candidate(request)
    assert set(runs) == {"parent"}
    assert (tmp_path / "parent.json").read_bytes() == parent_bytes
    assert not (tmp_path / "out" / "graph_memory" / "derived_candidates").exists()


def test_v5_request_rejects_duplicate_evidence_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _parent, _parent_bytes, _runs, request = _evidence_batch_fixture(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="duplicate evidence replacement target"):
        RecapCandidateCorrectionRequestV5(
            schema="dmb_recap_candidate_correction_request_v5",
            parent_run_id=request.parent_run_id,
            parent_candidate_sha256=request.parent_candidate_sha256,
            evidence_replacements=[request.evidence_replacements[0], request.evidence_replacements[0]],
        )


def test_v5_valid_batch_cannot_hide_an_inherited_invalid_anchor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs, request = _evidence_batch_fixture(monkeypatch, tmp_path)
    payload = json.loads(parent_bytes)
    chamber = next(node for node in payload["nodes"] if node["node_id"] == "chamber")
    chamber["evidence_refs"][0]["anchor_quotes"] = ["inherited unsupported phrase"]
    changed_parent_bytes = json.dumps(payload).encode()
    (tmp_path / "parent.json").write_bytes(changed_parent_bytes)
    components = dict(parent.components)
    components["candidate_graph"] = components["candidate_graph"].model_copy(
        update={"sha256": _sha(changed_parent_bytes)}
    )
    parent = parent.model_copy(update={"components": components})
    runs["parent"] = parent
    request = request.model_copy(update={"parent_candidate_sha256": _sha(changed_parent_bytes)})

    with pytest.raises(extract_promote.ExtractPromoteError):
        service.correct_recap_candidate(request)
    assert set(runs) == {"parent"}
    assert (tmp_path / "parent.json").read_bytes() == changed_parent_bytes
    assert not (tmp_path / "out" / "graph_memory" / "derived_candidates").exists()


def test_v3_session_action_child_replays_and_stays_held(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs = _fixture(monkeypatch, tmp_path, actions=True)
    original = json.loads(parent_bytes)
    response = service.correct_recap_candidate(_action_request(parent_bytes))
    child = runs[response.run_id]
    assert response.schema_ == "dmb_recap_candidate_correction_response_v2"
    assert child.lineage["derivation"] == service.DERIVATION_V2
    assert child.lineage["semantic_disposition"]["state"] == "held"
    assert service.verify_child_replay(child, parent, tmp_path)
    assert (tmp_path / "parent.json").read_bytes() == parent_bytes
    assessment = assess_recap_semantics(
        child, parent=parent, source_revision_id=_sha((tmp_path / "source.md").read_bytes()), root=tmp_path,
    )
    assert assessment.marked and not assessment.accepted
    assert RecapSemanticBasisV3.model_validate(assessment.basis).digest() == response.semantic_basis_sha256
    candidate = json.loads((tmp_path / child.components["candidate_graph"].uri).read_text())
    assert candidate["nodes"][0]["session_actions"] == [
        "Mira crossed the bridge.", "Mira found the key under the bridge.", "Mira went home.",
    ]
    assert candidate["nodes"][0]["description"] == original["nodes"][0]["description"]


def test_v3_replay_rejects_stale_cross_node_and_unbounded_actions() -> None:
    parent = {"nodes": [{"node_id": "mira", "description": "old", "session_actions": ["first", "second"]}]}
    action = {"node_id": "mira", "action_index": 1, "expected_old_text": "second", "replacement_text": "new"}
    manifest = {"schema": service.MANIFEST_SCHEMA_V2, "node_description_replacements": [], "omitted_edge_ids": [], "session_action_replacements": [action]}
    assert service.replay_candidate(parent, manifest)["nodes"][0]["session_actions"] == ["first", "new"]
    assert parent["nodes"][0]["session_actions"] == ["first", "second"]
    combined = {**manifest, "node_description_replacements": [{
        "node_id": "mira", "original_description": "old", "replacement_description": "new description",
    }]}
    assert service.replay_candidate(parent, combined)["nodes"][0] == {
        "node_id": "mira", "description": "new description", "session_actions": ["first", "new"],
    }
    for bad in ({**action, "expected_old_text": "wrong"}, {**action, "action_index": 2}, {**action, "action_index": True}):
        with pytest.raises(ValueError):
            service.replay_candidate(parent, {**manifest, "session_action_replacements": [bad]})
    with pytest.raises(ValueError):
        service.replay_candidate(parent, {**manifest, "session_action_replacements": [action, action]})
    with pytest.raises(ValueError):
        service.replay_candidate(parent, {**manifest, "node_description_replacements": [{"node_id": "other", "original_description": "old", "replacement_description": "new"}]})
    with pytest.raises(ValueError):
        service.replay_candidate(parent, {**manifest, "schema": service.MANIFEST_SCHEMA})


def test_malformed_stored_v2_manifest_remains_held(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs = _fixture(monkeypatch, tmp_path, actions=True)
    response = service.correct_recap_candidate(_action_request(parent_bytes))
    child = runs[response.run_id]
    manifest = child.lineage["semantic_candidate_manifest"]
    manifest["node_description_replacements"] = [None]
    child.lineage["manifest_sha256"] = _sha(service._canonical_bytes(manifest))

    with pytest.raises(extract_promote.ExtractPromoteError, match="node replacement manifest is malformed"):
        service.replay_candidate(json.loads(parent_bytes), manifest)
    assert not service.verify_child_replay(child, parent, tmp_path)
    assessment = assess_recap_semantics(
        child, parent=parent,
        source_revision_id=_sha((tmp_path / "source.md").read_bytes()), root=tmp_path,
    )
    assert assessment.marked and not assessment.accepted
    assert assessment.disposition is None

    valid_manifest = {**manifest, "node_description_replacements": []}
    for malformed_parent in (None, {"nodes": [None]}, {"nodes": "not a list"}, {"nodes": [], "edges": [None]}):
        with pytest.raises(extract_promote.ExtractPromoteError, match="malformed"):
            service.replay_candidate(malformed_parent, valid_manifest)


def test_immutable_child_replays_and_stays_held(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs = _fixture(monkeypatch, tmp_path)
    response = service.correct_recap_candidate(_request(parent_bytes))
    assert service.correct_recap_candidate(_request(parent_bytes)) == response
    assert parent_bytes == (tmp_path / "parent.json").read_bytes()
    child = runs[response.run_id]
    assert child.status == ExtractionRunStatus.REVIEWABLE
    assert child.lineage["semantic_disposition"]["state"] == "held"
    assert service.verify_child_replay(child, parent, tmp_path)
    assessment = assess_recap_semantics(
        child, parent=parent, source_revision_id=_sha((tmp_path / "source.md").read_bytes()),
        root=tmp_path,
    )
    assert assessment.marked and not assessment.accepted
    assert assessment.basis_sha256 == response.semantic_basis_sha256
    assert RecapSemanticBasisV2.model_validate(assessment.basis).digest() == response.semantic_basis_sha256
    candidate = json.loads((tmp_path / child.components["candidate_graph"].uri).read_text())
    assert candidate["nodes"][0]["description"] == "Mira found the key under the bridge."
    assert candidate["nodes"][0]["evidence_refs"] == json.loads(parent_bytes)["nodes"][0]["evidence_refs"]
    candidate["nodes"][0]["label"] = "forged"
    (tmp_path / child.components["candidate_graph"].uri).write_text(json.dumps(candidate))
    assert not service.verify_child_replay(child, parent, tmp_path)
    assert not assess_recap_semantics(
        child, parent=parent, source_revision_id=_sha((tmp_path / "source.md").read_bytes()),
        root=tmp_path,
    ).accepted
    candidate_path = tmp_path / child.components["candidate_graph"].uri
    candidate_path.write_bytes(service._canonical_bytes(service.replay_candidate(json.loads(parent_bytes), child.lineage["semantic_candidate_manifest"])))
    (tmp_path / "spans.json").write_text('{"spans":[],"tampered":true}')
    assert not service.verify_child_replay(child, parent, tmp_path)


def test_replay_refuses_stale_description_and_edge_dependency() -> None:
    parent = {
        "nodes": [{"node_id": "n", "description": "old"}],
        "edges": [{"edge_id": "e"}],
        "proposed_writes": [{"target_id": "e"}],
    }
    manifest = {
        "schema": service.MANIFEST_SCHEMA,
        "node_description_replacements": [{
            "node_id": "n", "original_description": "wrong",
            "replacement_description": "new",
        }],
        "omitted_edge_ids": [],
    }
    with pytest.raises(ValueError, match="stale"):
        service.replay_candidate(parent, manifest)
    manifest["node_description_replacements"] = []
    manifest["omitted_edge_ids"] = ["e"]
    with pytest.raises(ValueError, match="dependent"):
        service.replay_candidate(parent, manifest)
    parent["proposed_writes"] = []
    assert service.replay_candidate(parent, manifest)["edges"] == []
    assert parent["edges"] == [{"edge_id": "e"}]


def test_request_enforces_one_plus_one_bounded_shape() -> None:
    with pytest.raises(ValueError):
        RecapCandidateCorrectionRequest(parent_run_id="p", parent_candidate_sha256="a" * 64)
    with pytest.raises(ValueError):
        RecapCandidateCorrectionRequest(
            parent_run_id="p", parent_candidate_sha256="a" * 64,
            omitted_edge_ids=["e1", "e2"],
        )


def test_http_route_creates_held_child_and_rejects_wrong_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs = _fixture(monkeypatch, tmp_path)
    route = next(route for route in routes.router.routes if route.path.endswith("/recap-candidate-corrections"))
    assert any(dependency.call is native_graph_gm_dependency for dependency in route.dependant.dependencies)
    import fastapi.dependencies.utils as dependency_utils
    import fastapi.routing as fastapi_routing

    async def inline_sync(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(fastapi_routing, "run_in_threadpool", inline_sync)
    monkeypatch.setattr(dependency_utils, "run_in_threadpool", inline_sync)
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[native_graph_gm_dependency] = lambda: NativeGraphPrincipal(
        subject="test_gm", role="gm", auth_method="local_session",
    )
    body = _request(parent_bytes).model_dump(mode="json", by_alias=True)
    url = "/api/live/extract-promote/runs/parent/recap-candidate-corrections"

    async def exercise():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            mismatch = await client.post(url, json={**body, "parentRunId": "other"})
            assert mismatch.status_code == 422
            unknown = await client.post(url, json={**body, "arbitraryPatch": {"x": 1}})
            assert unknown.status_code == 422
            created = await client.post(url, json=body)
            assert created.status_code == 200, created.text
            assert created.json()["semanticState"] == "held"
            assert created.json()["runId"] in runs

    asyncio.run(exercise())
    assert parent_bytes == (tmp_path / parent.components["candidate_graph"].uri).read_bytes()


def test_http_v2_route_preserves_auth_and_rejects_cross_node_and_extra_patch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs = _fixture(monkeypatch, tmp_path, actions=True)
    import fastapi.dependencies.utils as dependency_utils
    import fastapi.routing as fastapi_routing

    async def inline_sync(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(fastapi_routing, "run_in_threadpool", inline_sync)
    monkeypatch.setattr(dependency_utils, "run_in_threadpool", inline_sync)
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[native_graph_gm_dependency] = lambda: NativeGraphPrincipal(
        subject="test_gm", role="gm", auth_method="local_session",
    )
    body = _action_request(parent_bytes).model_dump(mode="json", by_alias=True)
    url = "/api/live/extract-promote/runs/parent/recap-candidate-corrections"

    async def exercise() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            for invalid in (
                {**body, "arbitraryPatch": {"label": "forged"}},
                {**body, "sessionActionReplacements": [*body["sessionActionReplacements"], *body["sessionActionReplacements"]]},
                {**body, "nodeDescriptionReplacements": [{"nodeId": "other", "originalDescription": "old", "replacementDescription": "new"}]},
                {key: value for key, value in body.items() if key != "schema"},
            ):
                response = await client.post(url, json=invalid)
                assert response.status_code == 422, response.text
            created = await client.post(url, json=body)
            assert created.status_code == 200, created.text
            assert created.json()["schema"] == "dmb_recap_candidate_correction_response_v2"
            assert created.json()["semanticState"] == "held"
            assert created.json()["runId"] in runs

    asyncio.run(exercise())
    assert parent_bytes == (tmp_path / parent.components["candidate_graph"].uri).read_bytes()


def test_http_v3_route_creates_held_edge_tuple_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs = _tuple_fixture(monkeypatch, tmp_path)
    route = next(route for route in routes.router.routes if route.path.endswith("/recap-candidate-corrections"))
    assert any(dependency.call is native_graph_gm_dependency for dependency in route.dependant.dependencies)
    import fastapi.dependencies.utils as dependency_utils
    import fastapi.routing as fastapi_routing

    async def inline_sync(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(fastapi_routing, "run_in_threadpool", inline_sync)
    monkeypatch.setattr(dependency_utils, "run_in_threadpool", inline_sync)
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[native_graph_gm_dependency] = lambda: NativeGraphPrincipal(
        subject="test_gm", role="gm", auth_method="local_session",
    )
    body = _tuple_request(parent_bytes).model_dump(mode="json", by_alias=True)
    url = "/api/live/extract-promote/runs/parent/recap-candidate-corrections"

    async def exercise() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            mismatch = await client.post(url, json={**body, "parentRunId": "other"})
            assert mismatch.status_code == 422
            unsupported = await client.post(url, json={**body, "patch": {"predicate": "uses"}})
            assert unsupported.status_code == 422
            created = await client.post(url, json=body)
            assert created.status_code == 200, created.text
            assert created.json()["schema"] == "dmb_recap_candidate_correction_response_v3"
            assert created.json()["semanticState"] == "held"
            assert created.json()["runId"] in runs

    asyncio.run(exercise())
    assert parent_bytes == (tmp_path / parent.components["candidate_graph"].uri).read_bytes()


def test_http_v4_route_creates_held_evidence_span_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _parent, parent_bytes, runs, request, _target_span_id = _span_relocation_fixture(monkeypatch, tmp_path)
    route = next(route for route in routes.router.routes if route.path.endswith("/recap-candidate-corrections"))
    assert any(dependency.call is native_graph_gm_dependency for dependency in route.dependant.dependencies)
    import fastapi.dependencies.utils as dependency_utils
    import fastapi.routing as fastapi_routing

    async def inline_sync(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(fastapi_routing, "run_in_threadpool", inline_sync)
    monkeypatch.setattr(dependency_utils, "run_in_threadpool", inline_sync)
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[native_graph_gm_dependency] = lambda: NativeGraphPrincipal(
        subject="test_gm", role="gm", auth_method="local_session",
    )
    body = request.model_dump(mode="json", by_alias=True)
    url = "/api/live/extract-promote/runs/parent/recap-candidate-corrections"

    async def exercise() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            mismatch = await client.post(url, json={**body, "parentRunId": "other"})
            assert mismatch.status_code == 422
            created = await client.post(url, json=body)
            assert created.status_code == 200, created.text
            assert created.json()["schema"] == "dmb_recap_candidate_correction_response_v4"
            assert created.json()["semanticState"] == "held"
            assert created.json()["runId"] in runs

    asyncio.run(exercise())
    assert parent_bytes == (tmp_path / "parent.json").read_bytes()


def test_http_v5_route_creates_held_evidence_replacement_batch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _parent, parent_bytes, runs, request = _evidence_batch_fixture(monkeypatch, tmp_path)
    route = next(route for route in routes.router.routes if route.path.endswith("/recap-candidate-corrections"))
    assert any(dependency.call is native_graph_gm_dependency for dependency in route.dependant.dependencies)
    import fastapi.dependencies.utils as dependency_utils
    import fastapi.routing as fastapi_routing

    async def inline_sync(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(fastapi_routing, "run_in_threadpool", inline_sync)
    monkeypatch.setattr(dependency_utils, "run_in_threadpool", inline_sync)
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[native_graph_gm_dependency] = lambda: NativeGraphPrincipal(
        subject="test_gm", role="gm", auth_method="local_session",
    )
    body = request.model_dump(mode="json", by_alias=True)
    url = "/api/live/extract-promote/runs/parent/recap-candidate-corrections"

    async def exercise() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            mismatch = await client.post(url, json={**body, "parentRunId": "other"})
            assert mismatch.status_code == 422
            duplicate = {**body, "evidenceReplacements": [body["evidenceReplacements"][0]] * 2}
            duplicate_response = await client.post(url, json=duplicate)
            assert duplicate_response.status_code == 422
            created = await client.post(url, json=body)
            assert created.status_code == 200, created.text
            assert created.json()["schema"] == "dmb_recap_candidate_correction_response_v5"
            assert created.json()["semanticState"] == "held"
            assert created.json()["runId"] in runs

    asyncio.run(exercise())
    assert parent_bytes == (tmp_path / "parent.json").read_bytes()


def test_full_app_v2_route_requires_gm_and_csrf(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import fastapi.dependencies.utils as dependency_utils
    import fastapi.routing as fastapi_routing
    from apps.live_control_server.main import create_app
    from apps.live_control_server.services.agent_graph_auth import authenticate_native_graph_principal
    from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionResponseV2

    async def inline_sync(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(fastapi_routing, "run_in_threadpool", inline_sync)
    monkeypatch.setattr(dependency_utils, "run_in_threadpool", inline_sync)
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "development")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", "synthetic-local-operator-capability-32-characters")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_UI_ORIGIN", "http://127.0.0.1:5202")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_API_HOST", "127.0.0.1:8000")
    monkeypatch.setenv("DMB_AGENT_GRAPH_SESSION_STORE", str(tmp_path / "sessions.json"))
    seen = []

    def correct(request):
        seen.append(request)
        return RecapCandidateCorrectionResponseV2(
            run_id="child", parent_run_id="parent", parent_candidate_sha256="a" * 64,
            candidate_sha256="b" * 64, manifest_sha256="c" * 64,
            semantic_basis_sha256="d" * 64, semantic_state="held",
        )

    monkeypatch.setattr(routes, "correct_recap_candidate", correct)
    app = create_app()
    body = RecapCandidateCorrectionRequestV2(
        schema="dmb_recap_candidate_correction_request_v2",
        parent_run_id="parent", parent_candidate_sha256="a" * 64,
        session_action_replacements=[RecapSessionActionReplacement(
            node_id="mira", action_index=0, expected_old_text="wrong", replacement_text="right",
        )],
    ).model_dump(mode="json", by_alias=True)
    url = "/api/live/extract-promote/runs/parent/recap-candidate-corrections"

    async def exercise() -> None:
        transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
            assert (await client.post(url, json=body)).status_code == 401
            app.dependency_overrides[authenticate_native_graph_principal] = lambda: NativeGraphPrincipal(
                subject="player", role="player", auth_method="local_operator",
            )
            assert (await client.post(url, json=body)).status_code == 403
            app.dependency_overrides.clear()
            boot = await client.post(
                "/api/live/agent/local-session",
                headers={"Origin": "http://127.0.0.1:5202", "Sec-Fetch-Site": "same-origin"},
            )
            assert boot.status_code == 200, boot.text
            origin = {"Origin": "http://127.0.0.1:5202"}
            assert (await client.post(url, json=body, headers=origin)).status_code == 403
            headers = {**origin, "X-DMB-Graph-CSRF": boot.json()["csrf_token"]}
            assert (await client.post(url, json={**body, "schema": "dmb_recap_candidate_correction_request_v1"}, headers=headers)).status_code == 422
            accepted = await client.post(url, json=body, headers=headers)
            assert accepted.status_code == 200, accepted.text
            assert accepted.json()["schema"] == "dmb_recap_candidate_correction_response_v2"
            assert accepted.json()["semanticState"] == "held"

    asyncio.run(exercise())
    assert len(seen) == 1 and isinstance(seen[0], RecapCandidateCorrectionRequestV2)


def test_v3_decision_dispatches_exact_basis_to_appstate_cas(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from application_state.ingest import service as ingest_service
    from apps.live_control_server.services import source_artifact_registry

    parent, parent_bytes, runs = _fixture(monkeypatch, tmp_path, actions=True)
    response = service.correct_recap_candidate(_action_request(parent_bytes))
    child = runs[response.run_id]
    monkeypatch.setattr(extract_promote, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(graph_run_registry, "get_reviewable_extraction_run", lambda _root, _id: child)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, _id: parent)
    monkeypatch.setattr(source_artifact_registry, "get_source_artifact", lambda _root, _id: SimpleNamespace(content_sha256=_sha((tmp_path / "source.md").read_bytes())))
    seen = []

    def record(run_id, *, expected_revision, basis, decision):
        assert isinstance(basis, RecapSemanticBasisV3)
        assert basis.digest() == response.semantic_basis_sha256
        seen.append((run_id, expected_revision, decision.reviewer_id))
        decided = child.model_copy(deep=True, update={"revision": expected_revision + 1})
        decided.lineage["semantic_disposition"] = {
            "version": 1, "state": decision.state, "basis_sha256": basis.digest(),
            "review_decision_ref": decision.review_decision_ref,
            "reviewer_id": decision.reviewer_id,
            "decided_at": "2026-10-06T00:00:00Z", "from_revision": expected_revision,
        }
        return decided

    monkeypatch.setattr(ingest_service, "record_recap_semantic_disposition", record)
    receipt = extract_promote.decide_recap_semantic_disposition(
        child.run_id,
        RecapSemanticDecisionRequest(
            expected_revision=child.revision, candidate_sha256=response.candidate_sha256,
            decision="accepted", review_decision_ref="review:v3",
        ),
        reviewer_id="gm",
    )
    assert receipt.state == "accepted" and receipt.basis_sha256 == response.semantic_basis_sha256
    assert seen == [(child.run_id, child.revision, "gm")]


def test_v4_decision_dispatches_exact_basis_to_appstate_cas(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from application_state.ingest import service as ingest_service
    from apps.live_control_server.services import source_artifact_registry

    parent, parent_bytes, runs = _tuple_fixture(monkeypatch, tmp_path)
    response = service.correct_recap_candidate(_tuple_request(parent_bytes))
    child = runs[response.run_id]
    monkeypatch.setattr(extract_promote, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(graph_run_registry, "get_reviewable_extraction_run", lambda _root, _id: child)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, _id: parent)
    monkeypatch.setattr(
        source_artifact_registry, "get_source_artifact",
        lambda _root, _id: SimpleNamespace(content_sha256=_sha((tmp_path / "source.md").read_bytes())),
    )
    seen = []

    def record(run_id, *, expected_revision, basis, decision):
        assert isinstance(basis, RecapSemanticBasisV4)
        assert basis.digest() == response.semantic_basis_sha256
        assert basis.derivation == service.DERIVATION_V3
        assert basis.manifest_schema == service.MANIFEST_SCHEMA_V3
        seen.append((run_id, expected_revision, decision.reviewer_id))
        decided = child.model_copy(deep=True, update={"revision": expected_revision + 1})
        decided.lineage["semantic_disposition"] = {
            "version": 1, "state": decision.state, "basis_sha256": basis.digest(),
            "review_decision_ref": decision.review_decision_ref,
            "reviewer_id": decision.reviewer_id,
            "decided_at": "2026-10-07T00:00:00Z", "from_revision": expected_revision,
        }
        return decided

    monkeypatch.setattr(ingest_service, "record_recap_semantic_disposition", record)
    receipt = extract_promote.decide_recap_semantic_disposition(
        child.run_id,
        RecapSemanticDecisionRequest(
            expected_revision=child.revision, candidate_sha256=response.candidate_sha256,
            decision="accepted", review_decision_ref="review:tuple-v4",
        ),
        reviewer_id="gm",
    )
    assert receipt.state == "accepted" and receipt.basis_sha256 == response.semantic_basis_sha256
    assert seen == [(child.run_id, child.revision, "gm")]


def test_v5_decision_dispatches_span_basis_to_appstate_cas(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from application_state.ingest import service as ingest_service
    from apps.live_control_server.services import source_artifact_registry

    parent, _parent_bytes, runs, request, _target_span_id = _span_relocation_fixture(monkeypatch, tmp_path)
    response = service.correct_recap_candidate(request)
    child = runs[response.run_id]
    monkeypatch.setattr(extract_promote, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(graph_run_registry, "get_reviewable_extraction_run", lambda _root, _id: child)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, _id: parent)
    monkeypatch.setattr(
        source_artifact_registry, "get_source_artifact",
        lambda _root, _id: SimpleNamespace(content_sha256=_sha((tmp_path / "source.md").read_bytes())),
    )
    seen = []

    def record(run_id, *, expected_revision, basis, decision):
        assert isinstance(basis, RecapSemanticBasisV5)
        assert basis.digest() == response.semantic_basis_sha256
        assert basis.derivation == service.DERIVATION_V4
        assert basis.manifest_schema == service.MANIFEST_SCHEMA_V4
        seen.append((run_id, expected_revision, decision.reviewer_id))
        decided = child.model_copy(deep=True, update={"revision": expected_revision + 1})
        decided.lineage["semantic_disposition"] = {
            "version": 1, "state": decision.state, "basis_sha256": basis.digest(),
            "review_decision_ref": decision.review_decision_ref,
            "reviewer_id": decision.reviewer_id,
            "decided_at": "2026-10-07T00:00:00Z", "from_revision": expected_revision,
        }
        return decided

    monkeypatch.setattr(ingest_service, "record_recap_semantic_disposition", record)
    receipt = extract_promote.decide_recap_semantic_disposition(
        child.run_id,
        RecapSemanticDecisionRequest(
            expected_revision=child.revision, candidate_sha256=response.candidate_sha256,
            decision="accepted", review_decision_ref="review:span-v5",
        ),
        reviewer_id="gm",
    )
    assert receipt.state == "accepted" and receipt.basis_sha256 == response.semantic_basis_sha256
    assert seen == [(child.run_id, child.revision, "gm")]


def test_v6_decision_dispatches_evidence_batch_basis_to_appstate_cas(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from application_state.ingest import service as ingest_service
    from apps.live_control_server.services import source_artifact_registry

    parent, _parent_bytes, runs, request = _evidence_batch_fixture(monkeypatch, tmp_path)
    response = service.correct_recap_candidate(request)
    child = runs[response.run_id]
    monkeypatch.setattr(extract_promote, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(graph_run_registry, "get_reviewable_extraction_run", lambda _root, _id: child)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, _id: parent)
    monkeypatch.setattr(
        source_artifact_registry, "get_source_artifact",
        lambda _root, _id: SimpleNamespace(content_sha256=_sha((tmp_path / "source.md").read_bytes())),
    )
    seen = []

    def record(run_id, *, expected_revision, basis, decision):
        assert isinstance(basis, RecapSemanticBasisV6)
        assert basis.digest() == response.semantic_basis_sha256
        assert basis.derivation == service.DERIVATION_V5
        assert basis.manifest_schema == service.MANIFEST_SCHEMA_V5
        seen.append((run_id, expected_revision, decision.reviewer_id))
        decided = child.model_copy(deep=True, update={"revision": expected_revision + 1})
        decided.lineage["semantic_disposition"] = {
            "version": 1, "state": decision.state, "basis_sha256": basis.digest(),
            "review_decision_ref": decision.review_decision_ref,
            "reviewer_id": decision.reviewer_id,
            "decided_at": "2026-10-07T00:00:00Z", "from_revision": expected_revision,
        }
        return decided

    monkeypatch.setattr(ingest_service, "record_recap_semantic_disposition", record)
    receipt = extract_promote.decide_recap_semantic_disposition(
        child.run_id,
        RecapSemanticDecisionRequest(
            expected_revision=child.revision, candidate_sha256=response.candidate_sha256,
            decision="accepted", review_decision_ref="review:batch-v6",
        ),
        reviewer_id="gm",
    )
    assert receipt.state == "accepted" and receipt.basis_sha256 == response.semantic_basis_sha256
    assert seen == [(child.run_id, child.revision, "gm")]


def test_edge_tuple_child_cannot_prepare_while_semantic_hold_is_pending(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs = _tuple_fixture(monkeypatch, tmp_path)
    response = service.correct_recap_candidate(_tuple_request(parent_bytes))
    child = runs[response.run_id]
    monkeypatch.setattr(extract_promote, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", service.resolve_promotable_ingest_run)
    from apps.live_control_server.services.managed_world_graph_projection import VerifiedManagedWorldBinding
    monkeypatch.setattr(
        extract_promote, "_resolve_publication_target",
        lambda _id: VerifiedManagedWorldBinding(
            managed_world_id="managed-world", native_world_id="eldyrwild",
            binding_version=1, source_root_relpath="corpus/managed-world-markdown",
        ),
    )
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, run_id: runs[run_id])
    monkeypatch.setattr(extract_promote, "_candidate_owner_for_locator", lambda _loc: child)
    with pytest.raises(extract_promote.ExtractPromoteError, match="semantic review") as held:
        extract_promote.prepare(
            ExtractPromotePrepareRequest(run_id=child.run_id, managed_world_id="managed-world")
        )
    assert held.value.code == "recap_semantic_hold"


@pytest.mark.parametrize("action_v2", [False, True])
def test_v2_hold_and_confirm_binding_guard_world_writer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, action_v2: bool
) -> None:
    parent, parent_bytes, runs = _fixture(monkeypatch, tmp_path, actions=action_v2)
    request = _action_request(parent_bytes) if action_v2 else _request(parent_bytes)
    response = service.correct_recap_candidate(request)
    child = runs[response.run_id]
    monkeypatch.setattr(extract_promote, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", service.resolve_promotable_ingest_run)
    from apps.live_control_server.services.managed_world_graph_projection import VerifiedManagedWorldBinding
    monkeypatch.setattr(
        extract_promote, "_resolve_publication_target",
        lambda _id: VerifiedManagedWorldBinding(
            managed_world_id="managed-world", native_world_id="eldyrwild",
            binding_version=1, source_root_relpath="corpus/managed-world-markdown",
        ),
    )
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, run_id: runs[run_id])
    monkeypatch.setattr(extract_promote, "_candidate_owner_for_locator", lambda _loc: runs[response.run_id])
    with pytest.raises(extract_promote.ExtractPromoteError, match="semantic review") as held:
        extract_promote.prepare(ExtractPromotePrepareRequest(run_id=child.run_id, managed_world_id="managed-world"))
    assert held.value.code == "recap_semantic_hold"
    source_sha = _sha((tmp_path / "source.md").read_bytes())
    child.lineage["semantic_disposition"] = {
        "version": 1, "state": "rejected", "basis_sha256": response.semantic_basis_sha256,
        "review_decision_ref": "review:reject", "reviewer_id": "gm",
        "decided_at": "2026-10-06T00:00:00Z", "from_revision": child.revision,
    }
    child.revision += 1
    with pytest.raises(extract_promote.ExtractPromoteError) as rejected:
        extract_promote.prepare(ExtractPromotePrepareRequest(run_id=child.run_id, managed_world_id="managed-world"))
    assert rejected.value.code == "recap_semantic_hold"
    child.lineage["semantic_disposition"]["state"] = "accepted"
    assessment = assess_recap_semantics(
        child, parent=parent, source_revision_id=source_sha, root=tmp_path,
    )
    assert assessment.accepted
    binding = accepted_effect_binding(child, assessment)
    if action_v2:
        assert binding["derivation"] == service.DERIVATION_V2
        assert binding["manifest_schema"] == service.MANIFEST_SCHEMA_V2
    locator = str(tmp_path / child.components["candidate_graph"].uri)
    extract_promote._assert_recap_semantics_at_confirm(locator, {"effect": {EFFECT_KEY: binding}})
    with pytest.raises(extract_promote.ExtractPromoteError):
        extract_promote._assert_recap_semantics_at_confirm(locator, {"effect": {EFFECT_KEY: {**binding, "manifest_sha256": "f" * 64}}})
    candidate = tmp_path / child.components["candidate_graph"].uri
    candidate.write_bytes(candidate.read_bytes() + b" ")
    with pytest.raises(extract_promote.ExtractPromoteError) as drifted:
        extract_promote._assert_recap_semantics_at_confirm(locator, {"effect": {EFFECT_KEY: binding}})
    assert drifted.value.code == "recap_semantic_hold"
