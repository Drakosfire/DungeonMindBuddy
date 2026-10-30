"""A bounded candidate edit makes a new held recap child, never a World write."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

import pytest
import httpx
from fastapi import FastAPI

from application_state.ingest.service import (
    RecapSemanticBasisV12, _assert_recap_semantic_basis,
)
from application_state.errors import ApplicationStateConflictError
from apps.live_control_server.models.extract_promote import (
    RecapCandidateCorrectionRequest,
    RecapCandidateNodeOmission,
    RecapCandidateCorrectionRequestV2,
    RecapCandidateCorrectionRequestV3,
    RecapCandidateCorrectionRequestV4,
    RecapCandidateCorrectionRequestV5,
    RecapCandidateCorrectionRequestV6,
    RecapCandidateEvidenceReplacementV5,
    RecapCandidateEvidenceSpanReplacement,
    RecapCandidateEdgeTuple,
    RecapCandidateEdgeTupleReplacement,
    RecapCandidateNodeTypeReplacement,
    RecapNodeDescriptionReplacement,
    RecapNodeLabelReplacement,
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


def _candidate_path(root: Path, run) -> Path:
    return root / run.components["candidate_graph"].uri.removeprefix("repo://")


def _component_path(root: Path, run, component: str) -> Path:
    return root / run.components[component].uri.removeprefix("repo://")


def _assert_child_source_snapshot(root: Path, parent, child) -> None:
    parent_source = parent.components["source_artifact"]
    child_source = child.components["source_artifact"]
    child_candidate = _candidate_path(root, child)
    expected_uri = f"repo://{child_candidate.parent.relative_to(root).as_posix()}/source.md"
    assert child_source.uri == expected_uri
    assert child_source.sha256 == parent_source.sha256
    assert _component_path(root, child, "source_artifact").read_bytes() == (
        _component_path(root, parent, "source_artifact").read_bytes()
    )
    assert child.components["source_span_index"] == parent.components["source_span_index"]


def _update_source_artifact_record(root: Path, artifact_id: str, **changes) -> None:
    registry = root / "out" / "registries" / "source_artifacts.json"
    document = json.loads(registry.read_text(encoding="utf-8"))
    record = next(
        row for row in document["records"]
        if row["source_artifact_id"] == artifact_id
    )
    record.update(changes)
    registry.write_text(json.dumps(document), encoding="utf-8")


def _fixture(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    *,
    actions: bool = False,
    source_text: str = "Mira found the key under the bridge.\n",
    node_id: str = "mira",
    node_label: str = "Mira",
):
    source = root / "source.md"
    source.write_text(source_text, encoding="utf-8")
    spans = root / "spans.json"
    spans.write_text('{"spans":[]}', encoding="utf-8")
    artifact_id = "artifact:recap:c:s:source"
    artifact_digest = _sha(source.read_bytes())
    artifact_registry = root / "out" / "registries" / "source_artifacts.json"
    artifact_registry.parent.mkdir(parents=True, exist_ok=True)
    artifact_registry.write_text(json.dumps({
        "schema_version": "dmb_source_artifact_registry_v1",
        "records": [{
            "source_artifact_id": artifact_id,
            "source_domain": "recap", "campaign_id": "c", "session_id": "s",
            "world_id": None, "uri": "repo://source.md",
            "content_sha256": artifact_digest, "artifact_kind": "recap_markdown",
            "document_class": "recap", "status": "active",
        }],
    }), encoding="utf-8")
    span_id = f"{artifact_id}:span:abc:1-1"
    node = {
        "node_id": node_id, "node_type": "character", "label": node_label,
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
            run_id=run_id, status=run.status.value,
            source_domain="recap", extraction_profile=service.PROFILE,
            campaign_id="c", session_id="s", source_artifact_id=artifact_id,
            source_revision_id=_sha(source.read_bytes()),
            world_id=None, ingest_context=None,
            normalized_recap_path=source,
            source_span_index_path=spans,
            candidate_graph_path=_candidate_path(root, run),
            preview_union_store_path=root,
            manifest_path=root / "extraction_run.json",
            run_dir=root, registry_root=root,
            sealed_source_uri=str(source), registry_context_graph_path=None,
            diagnostics=[],
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

    # Unit-only output owner double. The disposable-PG integration restores
    # the real owner; ordinary API/file-denial coverage lives in database review.
    from application_state.ingest import components as output_store
    outputs = {}

    def persist_output(*, run_id, expected_revision, kind, payload):
        assert runs[run_id].revision == expected_revision
        digest = _sha(payload)
        assert digest == runs[run_id].components[str(kind)].sha256.removeprefix("sha256:")
        outputs[(run_id, str(kind))] = payload
        return digest

    def review_data(_root, run_id):
        resolved = extract_promote.resolve_promotable_ingest_run(run_id, root=root)
        return SimpleNamespace(run=runs[run_id],
            source_artifact=SimpleNamespace(world_id=resolved.world_id, content_sha256=resolved.source_revision_id),
            source_bytes=resolved.normalized_recap_path.read_bytes(),
            candidate_bytes=outputs.get((run_id, "candidate_graph"), resolved.candidate_graph_path.read_bytes()),
            span_bytes=resolved.source_span_index_path.read_bytes(),
            span_index=extract_promote._load_frozen_span_index_for_resolved_run(resolved))

    monkeypatch.setattr(output_store, "persist_component_payload", persist_output)
    monkeypatch.setattr(graph_run_registry, "load_reviewable_extraction_data", review_data)

    monkeypatch.setattr(service, "repo_root", lambda: root)
    monkeypatch.setattr(service, "resolve_promotable_ingest_run", resolve)
    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", resolve)
    monkeypatch.setattr(extract_promote, "_load_frozen_span_index_for_resolved_run", lambda resolved: service._load_frozen_span_index_for_resolved_run(resolved))
    monkeypatch.setattr(service, "get_extraction_run", get_run)
    monkeypatch.setattr(service, "create_extraction_run", create_run)
    monkeypatch.setattr(service, "update_extraction_run_status", update_run)
    from application_state.source import service as source_service
    # This pure correction fixture stubs product metadata storage. Actual DB
    # descriptor lookup and file denial are covered by test_source_input_metadata_database.
    monkeypatch.setattr(source_service, "get_source_input_descriptors", lambda *, source_artifact_ids: {
        row["source_artifact_id"]: row
        for row in json.loads(artifact_registry.read_text())["records"]
        if row["source_artifact_id"] in source_artifact_ids
    })
    monkeypatch.setattr(
        source_service, "persist_source_markdown",
        lambda **_kwargs: SimpleNamespace(source_artifact_id=artifact_id),
    )
    def database_source(**kwargs):
        # This unit fixture stubs storage boundaries; real PostgreSQL source
        # reads and missing-file behavior are exercised in test_source_body_database.
        from apps.live_control_server.services.source_artifact_registry import (
            get_source_artifact, _read_exact_repo_uri_bytes,
        )
        stored = get_source_artifact(root, kwargs["source_artifact_id"])
        return SimpleNamespace(
            source_artifact_id=stored.source_artifact_id,
            content_sha256=stored.content_sha256,
            source_domain=str(stored.source_domain), world_id=stored.world_id,
            campaign_id=stored.campaign_id, session_id=stored.session_id,
            media_type="text/markdown", encoding="utf-8",
            markdown=_read_exact_repo_uri_bytes(root, stored.uri).decode("utf-8"),
        )
    monkeypatch.setattr(source_service, "get_source_markdown", database_source)
    monkeypatch.setattr(
        service, "_load_frozen_span_index_for_resolved_run",
        lambda _resolved: SimpleNamespace(spans=[SimpleNamespace(
            source_span_id=span_id, start_line=1, end_line=1,
        )]),
    )
    return parent, parent_bytes, runs


def _world_ingest_context(*, world_id: str = "elderwyld") -> dict[str, object]:
    return {
        "schema": "dm_world_campaign_ingest_context_v1",
        "managed_world_id": "managed-elderwyld",
        "native_world_id": world_id,
        "binding_version": 1,
        "campaign_id": "c",
        "head_revision_id": "revision-7",
        "graph_schema": "world_graph_v1",
        "graph_payload_sha256": "a" * 64,
    }


def _scoped_fixture(
    monkeypatch, root, *, context=None, lineage=None, source_world_id="elderwyld",
):
    parent, parent_bytes, runs = _fixture(monkeypatch, root)
    context = _world_ingest_context() if context is None else context
    frozen_lineage = {"world_campaign_ingest_context": context} if lineage is None else lineage
    parent = parent.model_copy(update={"lineage": frozen_lineage})
    _update_source_artifact_record(
        root, parent.source_artifact_id, world_id=source_world_id,
    )
    runs["parent"] = parent
    original_resolve = service.resolve_promotable_ingest_run

    def resolve(run_id, **kwargs):
        result = original_resolve(run_id, **kwargs)
        values = dict(vars(result))
        values["world_id"] = source_world_id
        return SimpleNamespace(**values)

    monkeypatch.setattr(service, "resolve_promotable_ingest_run", resolve)
    return parent, parent_bytes, runs


def _tuple_fixture(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    *,
    include_unmapped_edge: bool = False,
):
    source_text = "Mira found the key under the bridge. The tunnel opens into a chamber.\n"
    parent, _parent_bytes, runs = _fixture(monkeypatch, root, source_text=source_text)
    parent_path = _candidate_path(root, parent)
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


def _sprite_fixture(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    *,
    include_untouched_possession: bool = False,
):
    source_text = "Ephanna’s Sprite takes the lead and looks for traps, scouting with Ephanna to warn the party.\n"
    parent, _parent_bytes, runs = _fixture(monkeypatch, root, source_text=source_text)
    parent_path = _candidate_path(root, parent)
    payload = json.loads(parent_path.read_bytes())
    mira = payload["nodes"][0]
    state = mira["semantic_state"]
    evidence = mira["evidence_refs"][0]

    def node(node_id: str, node_type: str, label: str, description: str) -> dict:
        return {
            "node_id": node_id, "node_type": node_type, "label": label,
            "description": description, "importance": "medium",
            "semantic_state": state, "proposed_action": "create", "confidence": "medium",
            "evidence_refs": [copy.deepcopy(evidence)],
        }

    payload["nodes"] = [
        node("node:item:session14:sprite", "item", "Sprite", "Ephanna’s Sprite companion used to scout for traps and warn the party."),
        node("node:ephanna", "character", "Ephanna", "Ephanna scouts with her Sprite companion."),
    ]
    if include_untouched_possession:
        payload["nodes"].append(
            node("node:character:karsemine", "character", "Karsemine", "Karsemine travels with Ephanna and her Sprite.")
        )
    payload["edges"] = [{
        "edge_id": "edge:session14:023", "from_node_id": "node:ephanna",
        "relationship_type": "possesses", "to_node_id": "node:item:session14:sprite",
        "label": "has companion", "semantic_state": state,
        "proposed_action": "create", "confidence": "medium",
        "evidence_refs": [copy.deepcopy(evidence)],
    }]
    if include_untouched_possession:
        payload["edges"].append({
            "edge_id": "edge:session14:024", "from_node_id": "node:character:karsemine",
            "relationship_type": "possesses", "to_node_id": "node:item:session14:sprite",
            "label": "holds", "semantic_state": state,
            "proposed_action": "create", "confidence": "medium",
            "evidence_refs": [copy.deepcopy(evidence)],
        })
    parent_bytes = json.dumps(payload).encode()
    parent_path.write_bytes(parent_bytes)
    components = dict(parent.components)
    components["candidate_graph"] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
        uri=parent.components["candidate_graph"].uri,
        sha256=_sha(parent_bytes), exists=True,
    )
    parent = parent.model_copy(update={"components": components})
    runs["parent"] = parent
    request = RecapCandidateCorrectionRequestV3(
        schema="dmb_recap_candidate_correction_request_v3",
        parent_run_id="parent", parent_candidate_sha256=_sha(parent_bytes),
        node_type_replacements=[RecapCandidateNodeTypeReplacement(
            node_id="node:item:session14:sprite",
            expected_node_type="item", replacement_node_type="character",
        )],
        edge_tuple_replacements=[RecapCandidateEdgeTupleReplacement(
            edge_id="edge:session14:023",
            expected_tuple=RecapCandidateEdgeTuple(
                from_node_id="node:ephanna", relationship_type="possesses",
                to_node_id="node:item:session14:sprite", label="has companion",
            ),
            replacement_tuple=RecapCandidateEdgeTuple(
                from_node_id="node:item:session14:sprite", relationship_type="cooperates_with",
                to_node_id="node:ephanna", label="warns/scouts for",
            ),
        )],
    )
    return parent, parent_bytes, runs, request


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
    parent_path = _candidate_path(root, parent)
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


def test_source_binding_rechecks_snapshot_after_child_lock_wait(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    parent, parent_bytes, runs = _fixture(monkeypatch, tmp_path)
    request = _request(parent_bytes)
    source_path = _component_path(tmp_path, parent, "source_artifact")
    source_before = source_path.read_bytes()
    original_lock = service._source_binding_child_lock
    acquired: list[str] = []

    @contextmanager
    def change_source_after_lock(root: Path, child_id: str):
        with original_lock(root, child_id):
            acquired.append(child_id)
            source_path.write_bytes(source_before + b"changed while waiting")
            yield

    monkeypatch.setattr(service, "_source_binding_child_lock", change_source_after_lock)
    with pytest.raises(service.ExtractPromoteError, match="parent run authority changed"):
        service.correct_recap_candidate(request)

    assert len(acquired) == 1
    assert set(runs) == {parent.run_id}
    package_root = tmp_path / "out" / "graph_memory" / "derived_candidates"
    assert not (package_root / acquired[0]).exists()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO paths require POSIX")
def test_source_binding_child_reader_rejects_fifo_without_blocking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    fifo = tmp_path / "component.fifo"
    os.mkfifo(fifo)
    directory_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    original_open = os.open

    def require_nonblocking(path, flags, *args, **kwargs):
        if path == fifo.name:
            assert flags & os.O_NONBLOCK
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(service.os, "open", require_nonblocking)
    try:
        with pytest.raises(service.ExtractPromoteError, match="not a regular file"):
            service._read_child_file(directory_fd, fifo.name)
    finally:
        os.close(directory_fd)


@pytest.mark.parametrize(
    "fault",
    [
        "after_draft",
        "source_only",
        "candidate_only",
        "owner_staging",
        "after_prepared",
        "after_extracted",
        "after_validated",
        "after_reviewable",
    ],
)
def test_source_binding_exact_retry_recovers_owned_partial_and_sealed_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str,
) -> None:
    parent, parent_bytes, runs = _fixture(monkeypatch, tmp_path)
    source_before = _component_path(tmp_path, parent, "source_artifact").read_bytes()
    spans_before = _component_path(tmp_path, parent, "source_span_index").read_bytes()
    request = _request(parent_bytes)
    original_create = service.create_extraction_run
    original_update = service.update_extraction_run_status
    original_publish = service._publish_child_package_files
    interrupted = False
    owner_staging_path: Path | None = None

    def create_then_interrupt(root, **kwargs):
        nonlocal interrupted
        child = original_create(root, **kwargs)
        if fault == "after_draft" and not interrupted:
            interrupted = True
            raise RuntimeError("injected interruption after DRAFT row creation")
        return child

    def update_then_interrupt(root, run_id, *, status, expected_revision):
        nonlocal interrupted
        child = original_update(
            root, run_id, status=status, expected_revision=expected_revision,
        )
        if fault == f"after_{status.value}" and not interrupted:
            interrupted = True
            raise RuntimeError(f"injected interruption after {status.value}")
        return child

    def publish_then_interrupt(root, child_id, *, source_bytes, candidate_bytes, allow_existing):
        nonlocal interrupted, owner_staging_path
        if fault in {"source_only", "candidate_only"} and not interrupted:
            package = root / "out" / "graph_memory" / "derived_candidates" / child_id
            package.mkdir(parents=True, exist_ok=True)
            if fault == "source_only":
                (package / "source.md").write_bytes(source_bytes)
            else:
                (package / "candidate_graph.json").write_bytes(candidate_bytes)
            interrupted = True
            raise RuntimeError(f"injected interruption with {fault} package")
        if fault == "owner_staging" and not interrupted:
            staging = root / "out" / "graph_memory" / "derived_candidates" / ".staging"
            staging.mkdir(parents=True, exist_ok=True)
            owner_staging_path = staging / f"{child_id}.prior-owner.tmp"
            owner_staging_path.write_bytes(b"preserve prior owner's staging artifact")
            interrupted = True
            raise RuntimeError("injected interruption with prior-owner staging file")
        return original_publish(
            root, child_id, source_bytes=source_bytes,
            candidate_bytes=candidate_bytes, allow_existing=allow_existing,
        )

    monkeypatch.setattr(service, "create_extraction_run", create_then_interrupt)
    monkeypatch.setattr(service, "update_extraction_run_status", update_then_interrupt)
    monkeypatch.setattr(service, "_publish_child_package_files", publish_then_interrupt)

    with pytest.raises(RuntimeError, match="injected interruption"):
        service.correct_recap_candidate(request)

    assert interrupted
    child_ids = set(runs) - {parent.run_id}
    assert len(child_ids) == 1
    child_id = child_ids.pop()
    child = runs[child_id]
    if fault in {"after_draft", "source_only", "candidate_only", "owner_staging"}:
        assert child.status == ExtractionRunStatus.DRAFT
    else:
        expected_status = {
            "after_prepared": ExtractionRunStatus.PREPARED,
            "after_extracted": ExtractionRunStatus.EXTRACTED,
            "after_validated": ExtractionRunStatus.VALIDATED,
            "after_reviewable": ExtractionRunStatus.REVIEWABLE,
        }[fault]
        assert child.status == expected_status

    monkeypatch.setattr(service, "create_extraction_run", original_create)
    monkeypatch.setattr(service, "update_extraction_run_status", original_update)
    monkeypatch.setattr(service, "_publish_child_package_files", original_publish)
    response = service.correct_recap_candidate(request)

    assert response.run_id == child_id
    assert set(runs) - {parent.run_id} == {child_id}
    child = runs[child_id]
    assert child.status == ExtractionRunStatus.REVIEWABLE
    assert service.verify_child_replay(child, parent, tmp_path)
    assert _component_path(tmp_path, parent, "source_artifact").read_bytes() == source_before
    assert _component_path(tmp_path, parent, "source_span_index").read_bytes() == spans_before
    _, package_files = service._source_binding_package_state(tmp_path, child_id)
    assert set(package_files) == {"source.md", "candidate_graph.json"}
    assert package_files["source.md"] == source_before
    assert package_files["candidate_graph.json"] == _candidate_path(tmp_path, child).read_bytes()
    if owner_staging_path is not None:
        assert owner_staging_path.read_bytes() == b"preserve prior owner's staging artifact"


@pytest.mark.parametrize("historical_state", ["exact", "stranded_draft", "mismatched", "orphan"])
def test_source_binding_never_duplicates_or_adopts_legacy_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, historical_state: str,
) -> None:
    parent, parent_bytes, runs = _fixture(monkeypatch, tmp_path)
    request = _request(parent_bytes)
    bound_response = service.correct_recap_candidate(request)
    bound = runs.pop(bound_response.run_id)
    candidate_bytes = _candidate_path(tmp_path, bound).read_bytes()
    bound_package = _candidate_path(tmp_path, bound).parent
    for name in ("source.md", "candidate_graph.json"):
        (bound_package / name).unlink()
    bound_package.rmdir()

    legacy_id = str(uuid5(
        NAMESPACE_URL,
        f"dmb:{service.DERIVATION}:{parent.run_id}:{_sha(parent_bytes)}:{bound_response.manifest_sha256}",
    ))
    legacy_relative = f"out/graph_memory/derived_candidates/{legacy_id}/candidate_graph.json"
    legacy_dir = tmp_path / "out" / "graph_memory" / "derived_candidates" / legacy_id
    legacy_lineage = copy.deepcopy(bound.lineage)
    for key in ("operation_derivation", "operation_manifest_schema", "semantic_source_binding_basis_v12"):
        legacy_lineage.pop(key, None)
    legacy_lineage["derivation"] = service.DERIVATION
    legacy_components = dict(bound.components)
    legacy_components["candidate_graph"] = legacy_components["candidate_graph"].model_copy(
        update={"uri": legacy_relative},
    )
    legacy_components["source_artifact"] = parent.components["source_artifact"]
    legacy_components["source_span_index"] = parent.components["source_span_index"]
    legacy = bound.model_copy(update={
        "run_id": legacy_id,
        "status": ExtractionRunStatus.REVIEWABLE,
        "revision": 1,
        "components": legacy_components,
        "lineage": legacy_lineage,
    })

    legacy_dir.mkdir(parents=True, exist_ok=True)
    if historical_state != "orphan":
        (legacy_dir / "candidate_graph.json").write_bytes(candidate_bytes)
        assessment = assess_recap_semantics(
            legacy,
            parent=parent,
            source_revision_id=_sha(_component_path(tmp_path, parent, "source_artifact").read_bytes()),
            root=tmp_path,
        )
        assert assessment.basis is not None and assessment.basis_sha256 is not None
        legacy.lineage["semantic_disposition"] = {
            "version": 1,
            "state": "held",
            "basis_sha256": assessment.basis_sha256,
        }
        if historical_state == "stranded_draft":
            legacy.status = ExtractionRunStatus.DRAFT
        elif historical_state == "mismatched":
            legacy.lineage["manifest_sha256"] = "0" * 64
        runs[legacy_id] = legacy
    else:
        (legacy_dir / "candidate_graph.json").write_bytes(candidate_bytes)
    bytes_before = (legacy_dir / "candidate_graph.json").read_bytes()
    rows_before = set(runs)

    if historical_state == "exact":
        response = service.correct_recap_candidate(request)
        assert response.run_id == legacy_id
        assert response.run_id != bound_response.run_id
    else:
        with pytest.raises(extract_promote.ExtractPromoteError, match=legacy_id):
            service.correct_recap_candidate(request)

    assert set(runs) == rows_before
    assert (legacy_dir / "candidate_graph.json").read_bytes() == bytes_before
    assert not (tmp_path / "out" / "graph_memory" / "derived_candidates" / bound_response.run_id).exists()


def _label_request(parent_bytes: bytes) -> RecapCandidateCorrectionRequest:
    return RecapCandidateCorrectionRequest(
        parent_run_id="parent", parent_candidate_sha256=_sha(parent_bytes),
        node_label_replacements=[RecapNodeLabelReplacement(
            node_id="node:location:locked-door-to-guard-room",
            original_label="locked door to the guard room",
            replacement_label="door used by guards",
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
    assert child.lineage["derivation"] == service.SOURCE_BINDING_DERIVATION_V11
    assert child.lineage["operation_derivation"] == service.DERIVATION_V3
    assert child.lineage["semantic_candidate_manifest"]["schema"] == service.MANIFEST_SCHEMA_V3
    assert child.lineage["semantic_disposition"]["state"] == "held"
    assert service.correct_recap_candidate(request) == response
    assert service.verify_child_replay(child, parent, tmp_path)
    assert (_candidate_path(tmp_path, parent)).read_bytes() == parent_bytes

    candidate = json.loads((_candidate_path(tmp_path, child)).read_bytes())
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
    assert assessment.marked and not assessment.accepted, assessment
    basis = RecapSemanticBasisV12.model_validate(assessment.basis, strict=True)
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
    with pytest.raises(ApplicationStateConflictError, match="source-binding basis changed"):
        _assert_recap_semantic_basis(
            bad_child, parent, basis.model_copy(update={
                "operation_basis": basis.operation_basis.model_copy(
                    update={"manifest_sha256": bad_manifest_sha}
                ),
            }),
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
    with pytest.raises(ApplicationStateConflictError, match="source-binding basis changed"):
        _assert_recap_semantic_basis(
            overlong_child, parent, basis.model_copy(update={
                "operation_basis": basis.operation_basis.model_copy(
                    update={"manifest_sha256": overlong_sha}
                ),
            }),
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
    assert binding["derivation"] == service.SOURCE_BINDING_DERIVATION_V11
    assert binding["operation_derivation"] == service.DERIVATION_V3
    assert binding["operation_manifest_schema"] == service.MANIFEST_SCHEMA_V3
    assert child.lineage["manifest_sha256"] == "118f051572259d43b205e0f249b32e539c51619172e75f1dd3c2fe5240a8545c"
    assert child.run_id == str(uuid5(
        NAMESPACE_URL,
        f"dmb:{service.SOURCE_BINDING_DERIVATION_V11}:parent:{_sha(parent_bytes)}:{child.lineage['manifest_sha256']}",
    ))


def test_sprite_type_and_edge_tuple_change_replay_atomically_and_stay_held(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs, request = _sprite_fixture(monkeypatch, tmp_path)
    original = json.loads(parent_bytes)
    response = service.correct_recap_candidate(request)
    child = runs[response.run_id]

    assert child.lineage["semantic_disposition"]["state"] == "held"
    assert service.verify_child_replay(child, parent, tmp_path)
    manifest = child.lineage["semantic_candidate_manifest"]
    assert set(manifest) == {"schema", "edge_tuple_replacements", "node_type_replacements"}
    candidate = json.loads((_candidate_path(tmp_path, child)).read_bytes())
    expected = copy.deepcopy(original)
    expected["nodes"][0]["node_type"] = "character"
    expected["edges"][0].update({
        "from_node_id": "node:item:session14:sprite",
        "relationship_type": "cooperates_with",
        "to_node_id": "node:ephanna",
        "label": "warns/scouts for",
    })
    assert candidate == expected
    before_sprite, after_sprite = original["nodes"][0], candidate["nodes"][0]
    assert after_sprite["node_id"] == before_sprite["node_id"]
    assert after_sprite["description"] == before_sprite["description"]
    assert after_sprite["evidence_refs"] == before_sprite["evidence_refs"]
    assert candidate["edges"][0]["edge_id"] == original["edges"][0]["edge_id"]
    assert candidate["edges"][0]["evidence_refs"] == original["edges"][0]["evidence_refs"]
    assert (_candidate_path(tmp_path, parent)).read_bytes() == parent_bytes

    assessment = assess_recap_semantics(
        child, parent=parent, source_revision_id=_sha((tmp_path / "source.md").read_bytes()), root=tmp_path,
    )
    basis = RecapSemanticBasisV12.model_validate(assessment.basis, strict=True)
    assert assessment.marked and not assessment.accepted
    _assert_recap_semantic_basis(child, parent, basis)


@pytest.mark.parametrize(
    ("expected_type", "replacement_type"),
    [("npc", "character"), ("item", "dnd5e:item")],
)
def test_sprite_type_correction_rejects_stale_or_unsupported_type_before_child(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    expected_type: str,
    replacement_type: str,
) -> None:
    parent, parent_bytes, runs, request = _sprite_fixture(monkeypatch, tmp_path)
    replacement = request.node_type_replacements[0].model_copy(update={
        "expected_node_type": expected_type,
        "replacement_node_type": replacement_type,
    })
    bad_request = request.model_copy(update={"node_type_replacements": [replacement]})

    with pytest.raises(extract_promote.ExtractPromoteError):
        service.correct_recap_candidate(bad_request)
    assert set(runs) == {"parent"}
    assert (_candidate_path(tmp_path, parent)).read_bytes() == parent_bytes
    assert not (tmp_path / "out" / "graph_memory" / "derived_candidates").exists()


def test_sprite_type_request_requires_paired_edge_and_supported_type() -> None:
    edge = RecapCandidateEdgeTupleReplacement(
        edge_id="edge:session14:023",
        expected_tuple=RecapCandidateEdgeTuple(
            from_node_id="node:ephanna", relationship_type="possesses",
            to_node_id="node:item:session14:sprite", label="has companion",
        ),
        replacement_tuple=RecapCandidateEdgeTuple(
            from_node_id="node:item:session14:sprite", relationship_type="cooperates_with",
            to_node_id="node:ephanna", label="warns/scouts for",
        ),
    )
    type_replacement = RecapCandidateNodeTypeReplacement(
        node_id="node:item:session14:sprite",
        expected_node_type="item", replacement_node_type="character",
    )
    with pytest.raises(ValueError, match="paired"):
        RecapCandidateCorrectionRequestV3(
            schema="dmb_recap_candidate_correction_request_v3",
            parent_run_id="parent", parent_candidate_sha256="a" * 64,
            edge_tuple_replacements=[edge.model_copy(update={
                "expected_tuple": RecapCandidateEdgeTuple(
                    from_node_id="ephanna", relationship_type="possesses",
                    to_node_id="sprite", label="has companion",
                ),
                "replacement_tuple": RecapCandidateEdgeTuple(
                    from_node_id="sprite", relationship_type="cooperates_with",
                    to_node_id="ephanna", label="warns/scouts for",
                ),
            })],
            node_type_replacements=[type_replacement],
        )
    with pytest.raises(extract_promote.ExtractPromoteError, match="malformed"):
        service.replay_candidate(
            {"nodes": [{"node_id": "sprite", "node_type": "item"}], "edges": []},
            {
                "schema": service.MANIFEST_SCHEMA_V3,
                "edge_tuple_replacements": [{
                    "edge_id": "edge", "expected_tuple": {
                        "from_node_id": "sprite", "relationship_type": "located_in",
                        "to_node_id": "sprite", "label": "same",
                    }, "replacement_tuple": {
                        "from_node_id": "sprite", "relationship_type": "located_in",
                        "to_node_id": "sprite", "label": "different",
                    },
                }],
                "node_type_replacements": [{
                    "node_id": "sprite", "expected_node_type": "item",
                    "replacement_node_type": "dnd5e:item",
                }],
            },
        )


def test_sprite_type_change_rejects_untouched_item_only_edge_before_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs, request = _sprite_fixture(
        monkeypatch, tmp_path, include_untouched_possession=True,
    )

    with pytest.raises(extract_promote.ExtractPromoteError) as caught:
        service.correct_recap_candidate(request)

    assert caught.value.status_code == 422
    assert "unchanged incident edge" in str(caught.value)
    assert set(runs) == {"parent"}
    assert (_candidate_path(tmp_path, parent)).read_bytes() == parent_bytes
    assert not (tmp_path / "out" / "graph_memory" / "derived_candidates").exists()


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
    assert (_candidate_path(tmp_path, parent)).read_bytes() == parent_bytes
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
    assert child.lineage["derivation"] == service.SOURCE_BINDING_DERIVATION_V11
    assert child.lineage["operation_derivation"] == service.DERIVATION_V4
    assert child.lineage["semantic_candidate_manifest"]["schema"] == service.MANIFEST_SCHEMA_V4
    assert child.lineage["semantic_disposition"]["state"] == "held"
    assert service.correct_recap_candidate(request) == response
    assert service.verify_child_replay(child, parent, tmp_path)
    assert (_candidate_path(tmp_path, parent)).read_bytes() == parent_bytes
    _assert_child_source_snapshot(tmp_path, parent, child)

    candidate = json.loads((_candidate_path(tmp_path, child)).read_bytes())
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
    basis = RecapSemanticBasisV12.model_validate(assessment.basis, strict=True)
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
    assert binding["derivation"] == service.SOURCE_BINDING_DERIVATION_V11
    assert binding["operation_derivation"] == service.DERIVATION_V4
    assert binding["operation_manifest_schema"] == service.MANIFEST_SCHEMA_V4


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
    assert child.lineage["derivation"] == service.SOURCE_BINDING_DERIVATION_V11
    assert child.lineage["operation_derivation"] == service.DERIVATION_V5
    manifest = child.lineage["semantic_candidate_manifest"]
    assert manifest["schema"] == service.MANIFEST_SCHEMA_V5
    assert len(manifest["evidence_span_replacements"]) == 4
    assert child.lineage["semantic_disposition"]["state"] == "held"
    assert service.verify_child_replay(child, parent, tmp_path)
    assert (tmp_path / "parent.json").read_bytes() == parent_bytes

    candidate = json.loads((_candidate_path(tmp_path, child)).read_bytes())
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
    basis = RecapSemanticBasisV12.model_validate(assessment.basis, strict=True)
    assert basis.operation_basis.derivation == service.DERIVATION_V5
    assert basis.operation_basis.manifest_schema == service.MANIFEST_SCHEMA_V5
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
    assert accepted_effect_binding(accepted_child, accepted_assessment)["operation_manifest_schema"] == (
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


def test_v5_valid_batch_preserves_inherited_invalid_anchor_as_held(
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

    response = service.correct_recap_candidate(request)
    child = runs[response.run_id]
    assert response.semantic_state == "held"
    projected = json.loads((_candidate_path(tmp_path, child)).read_bytes())
    assert next(n for n in projected["nodes"] if n["node_id"] == "chamber")["evidence_refs"] == chamber["evidence_refs"]
    assert (tmp_path / "parent.json").read_bytes() == changed_parent_bytes


def test_v3_session_action_child_replays_and_stays_held(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs = _fixture(monkeypatch, tmp_path, actions=True)
    original = json.loads(parent_bytes)
    response = service.correct_recap_candidate(_action_request(parent_bytes))
    child = runs[response.run_id]
    assert response.schema_ == "dmb_recap_candidate_correction_response_v2"
    assert child.lineage["derivation"] == service.SOURCE_BINDING_DERIVATION_V11
    assert child.lineage["operation_derivation"] == service.DERIVATION_V2
    assert child.lineage["semantic_disposition"]["state"] == "held"
    assert service.verify_child_replay(child, parent, tmp_path)
    assert (tmp_path / "parent.json").read_bytes() == parent_bytes
    assessment = assess_recap_semantics(
        child, parent=parent, source_revision_id=_sha((tmp_path / "source.md").read_bytes()), root=tmp_path,
    )
    assert assessment.marked and not assessment.accepted
    assert RecapSemanticBasisV12.model_validate(assessment.basis, strict=True).digest() == response.semantic_basis_sha256
    candidate = json.loads((_candidate_path(tmp_path, child)).read_text())
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
    manifest = child.lineage["semantic_candidate_manifest"]
    assert manifest == {
        "schema": service.MANIFEST_SCHEMA,
        "node_description_replacements": [{
            "node_id": "mira",
            "original_description": "Mira carried an uncertain object.",
            "replacement_description": "Mira found the key under the bridge.",
        }],
        "omitted_edge_ids": [],
    }
    expected_manifest_sha = _sha(service._canonical_bytes(manifest))
    assert response.manifest_sha256 == expected_manifest_sha
    assert response.run_id == str(uuid5(
        NAMESPACE_URL,
        f"dmb:{service.SOURCE_BINDING_DERIVATION_V11}:parent:{_sha(parent_bytes)}:{expected_manifest_sha}",
    ))
    assert child.status == ExtractionRunStatus.REVIEWABLE
    assert child.lineage["semantic_disposition"]["state"] == "held"
    assert service.verify_child_replay(child, parent, tmp_path)
    assessment = assess_recap_semantics(
        child, parent=parent, source_revision_id=_sha((tmp_path / "source.md").read_bytes()),
        root=tmp_path,
    )
    assert assessment.marked and not assessment.accepted
    assert assessment.basis_sha256 == response.semantic_basis_sha256
    assert RecapSemanticBasisV12.model_validate(assessment.basis, strict=True).digest() == response.semantic_basis_sha256
    candidate = json.loads((_candidate_path(tmp_path, child)).read_text())
    assert candidate["nodes"][0]["description"] == "Mira found the key under the bridge."
    assert candidate["nodes"][0]["evidence_refs"] == json.loads(parent_bytes)["nodes"][0]["evidence_refs"]
    candidate["nodes"][0]["label"] = "forged"
    (_candidate_path(tmp_path, child)).write_text(json.dumps(candidate))
    assert not service.verify_child_replay(child, parent, tmp_path)
    assert not assess_recap_semantics(
        child, parent=parent, source_revision_id=_sha((tmp_path / "source.md").read_bytes()),
        root=tmp_path,
    ).accepted
    candidate_path = _candidate_path(tmp_path, child)
    candidate_path.write_bytes(service._canonical_bytes(service.replay_candidate(json.loads(parent_bytes), child.lineage["semantic_candidate_manifest"])))
    (tmp_path / "spans.json").write_text('{"spans":[],"tampered":true}')
    assert not service.verify_child_replay(child, parent, tmp_path)


def test_semantic_child_preserves_frozen_world_scope_and_replay_binds_it(monkeypatch, tmp_path):
    parent, parent_bytes, runs = _scoped_fixture(monkeypatch, tmp_path)
    response = service.correct_recap_candidate(_request(parent_bytes))
    child = runs[response.run_id]

    assert child.lineage["world_campaign_ingest_context"] == parent.lineage["world_campaign_ingest_context"]
    assert service.correct_recap_candidate(_request(parent_bytes)) == response
    assert service.verify_child_replay(child, parent, tmp_path)

    stripped = child.model_copy(deep=True)
    stripped.lineage.pop("world_campaign_ingest_context")
    assert not service.verify_child_replay(stripped, parent, tmp_path)

    forged = child.model_copy(deep=True)
    forged.lineage["world_campaign_ingest_context"]["native_world_id"] = "another-world"
    assert not service.verify_child_replay(forged, parent, tmp_path)


def test_semantic_child_preserves_explicit_legacy_world_scope(monkeypatch, tmp_path):
    legacy_scope = {"native_world_id": "elderwyld", "campaign_id": "c"}
    parent, parent_bytes, runs = _scoped_fixture(
        monkeypatch, tmp_path, lineage=legacy_scope,
    )
    response = service.correct_recap_candidate(_request(parent_bytes))
    child = runs[response.run_id]

    assert {key: child.lineage[key] for key in legacy_scope} == legacy_scope
    assert service.verify_child_replay(child, parent, tmp_path)


@pytest.mark.parametrize("failure", ["malformed_context", "missing_source_world", "source_world_mismatch"])
def test_semantic_child_world_scope_fails_before_persistence(monkeypatch, tmp_path, failure):
    context = _world_ingest_context()
    source_world_id = "elderwyld"
    if failure == "malformed_context":
        context.pop("graph_payload_sha256")
    elif failure == "missing_source_world":
        source_world_id = None
    else:
        source_world_id = "other-world"
    parent, parent_bytes, runs = _scoped_fixture(
        monkeypatch, tmp_path, context=context, source_world_id=source_world_id,
    )
    writes = []
    monkeypatch.setattr(service, "_publish_child_package_files", lambda *args, **kwargs: writes.append("candidate"))
    monkeypatch.setattr(service, "create_extraction_run", lambda *args, **kwargs: writes.append("run"))

    with pytest.raises(service.ExtractPromoteError):
        service.correct_recap_candidate(_request(parent_bytes))

    assert writes == []
    assert runs == {"parent": parent}
    assert not (tmp_path / "out/graph_memory/derived_candidates").exists()


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


def test_v1_label_correction_changes_only_label_and_stays_held(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source_text = "A locked door at the opposite end of the bridge is used by two guards.\n"
    parent, parent_bytes, runs = _fixture(
        monkeypatch, tmp_path, source_text=source_text,
        node_id="node:location:locked-door-to-guard-room",
        node_label="locked door to the guard room",
    )
    original = json.loads(parent_bytes)
    request = _label_request(parent_bytes)
    response = service.correct_recap_candidate(request)
    child = runs[response.run_id]

    manifest = child.lineage["semantic_candidate_manifest"]
    assert set(manifest) == {"schema", "node_description_replacements", "omitted_edge_ids", "node_label_replacements"}
    assert manifest["node_label_replacements"] == [{
        "node_id": "node:location:locked-door-to-guard-room",
        "original_label": "locked door to the guard room",
        "replacement_label": "door used by guards",
    }]
    assert child.lineage["semantic_disposition"]["state"] == "held"
    assert service.verify_child_replay(child, parent, tmp_path)
    assert response == service.correct_recap_candidate(request)
    assert (_candidate_path(tmp_path, parent)).read_bytes() == parent_bytes

    candidate = json.loads((_candidate_path(tmp_path, child)).read_bytes())
    expected = copy.deepcopy(original)
    expected["nodes"][0]["label"] = "door used by guards"
    assert candidate == expected
    assert candidate["nodes"][0]["node_id"] == "node:location:locked-door-to-guard-room"
    assert candidate["nodes"][0]["description"] == original["nodes"][0]["description"]
    assert candidate["nodes"][0]["evidence_refs"] == original["nodes"][0]["evidence_refs"]
    assert candidate["edges"] == original["edges"]
    assessment = assess_recap_semantics(
        child, parent=parent,
        source_revision_id=_sha((tmp_path / "source.md").read_bytes()), root=tmp_path,
    )
    assert assessment.marked and not assessment.accepted
    basis = RecapSemanticBasisV12.model_validate(assessment.basis, strict=True)
    _assert_recap_semantic_basis(child, parent, basis)
    malformed_manifest = copy.deepcopy(manifest)
    malformed_manifest["node_label_replacements"][0]["extra"] = "unbounded patch"
    malformed_sha = _sha(service._canonical_bytes(malformed_manifest))
    malformed_child = child.model_copy(update={
        "lineage": {
            **child.lineage,
            "manifest_sha256": malformed_sha,
            "semantic_candidate_manifest": malformed_manifest,
        },
    })
    with pytest.raises(ApplicationStateConflictError, match="semantic basis components changed"):
        _assert_recap_semantic_basis(malformed_child, parent, basis)


def test_label_replay_rejects_stale_or_malformed_preimage_without_mutation() -> None:
    parent = {"nodes": [{"node_id": "n", "label": "old", "description": "kept"}], "edges": []}
    manifest = {
        "schema": service.MANIFEST_SCHEMA,
        "node_description_replacements": [],
        "omitted_edge_ids": [],
        "node_label_replacements": [{
            "node_id": "n", "original_label": "old", "replacement_label": "new",
        }],
    }
    replayed = service.replay_candidate(parent, manifest)
    assert replayed == {"nodes": [{"node_id": "n", "label": "new", "description": "kept"}], "edges": []}
    assert parent["nodes"][0]["label"] == "old"

    stale = copy.deepcopy(manifest)
    stale["node_label_replacements"][0]["original_label"] = "stale"
    with pytest.raises(ValueError, match="stale"):
        service.replay_candidate(parent, stale)
    malformed = copy.deepcopy(manifest)
    malformed["node_label_replacements"][0]["extra"] = "patch"
    with pytest.raises(ValueError, match="malformed"):
        service.replay_candidate(parent, malformed)
    assert parent["nodes"][0]["label"] == "old"


def test_stale_label_request_is_rejected_before_child_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs = _fixture(
        monkeypatch, tmp_path,
        source_text="A locked door at the opposite end of the bridge is used by two guards.\n",
        node_id="node:location:locked-door-to-guard-room",
        node_label="locked door to the guard room",
    )
    request = _label_request(parent_bytes).model_copy(update={
        "node_label_replacements": [RecapNodeLabelReplacement(
            node_id="node:location:locked-door-to-guard-room",
            original_label="different stale label",
            replacement_label="door used by guards",
        )],
    })

    with pytest.raises(extract_promote.ExtractPromoteError, match="stale"):
        service.correct_recap_candidate(request)
    assert set(runs) == {"parent"}
    assert (_candidate_path(tmp_path, parent)).read_bytes() == parent_bytes
    assert not (tmp_path / "out" / "graph_memory" / "derived_candidates").exists()


def test_request_enforces_one_plus_one_bounded_shape() -> None:
    with pytest.raises(ValueError):
        RecapCandidateCorrectionRequest(parent_run_id="p", parent_candidate_sha256="a" * 64)
    with pytest.raises(ValueError):
        RecapCandidateCorrectionRequest(
            parent_run_id="p", parent_candidate_sha256="a" * 64,
            omitted_edge_ids=["e1", "e2"],
        )
    with pytest.raises(ValueError):
        RecapCandidateCorrectionRequest(
            parent_run_id="p", parent_candidate_sha256="a" * 64,
            node_label_replacements=[
                RecapNodeLabelReplacement(node_id="n1", original_label="old", replacement_label="new"),
                RecapNodeLabelReplacement(node_id="n2", original_label="old", replacement_label="new"),
            ],
        )
    with pytest.raises(ValueError):
        RecapNodeLabelReplacement(node_id="n", original_label="same", replacement_label="same")


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
    assert parent_bytes == (_candidate_path(tmp_path, parent)).read_bytes()


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
    assert parent_bytes == (_candidate_path(tmp_path, parent)).read_bytes()


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
    assert parent_bytes == (_candidate_path(tmp_path, parent)).read_bytes()


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

    parent, parent_bytes, runs = _fixture(monkeypatch, tmp_path, actions=True)
    response = service.correct_recap_candidate(_action_request(parent_bytes))
    child = runs[response.run_id]
    monkeypatch.setattr(extract_promote, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(graph_run_registry, "get_reviewable_extraction_run", lambda _root, _id: child)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, _id: parent)
    seen = []

    def record(run_id, *, expected_revision, basis, decision):
        assert isinstance(basis, RecapSemanticBasisV12)
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

    parent, parent_bytes, runs = _tuple_fixture(monkeypatch, tmp_path)
    response = service.correct_recap_candidate(_tuple_request(parent_bytes))
    child = runs[response.run_id]
    monkeypatch.setattr(extract_promote, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(graph_run_registry, "get_reviewable_extraction_run", lambda _root, _id: child)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, _id: parent)
    seen = []

    def record(run_id, *, expected_revision, basis, decision):
        assert isinstance(basis, RecapSemanticBasisV12)
        assert basis.digest() == response.semantic_basis_sha256
        assert basis.operation_basis.derivation == service.DERIVATION_V3
        assert basis.operation_basis.manifest_schema == service.MANIFEST_SCHEMA_V3
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

    parent, _parent_bytes, runs, request, _target_span_id = _span_relocation_fixture(monkeypatch, tmp_path)
    response = service.correct_recap_candidate(request)
    child = runs[response.run_id]
    monkeypatch.setattr(extract_promote, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(graph_run_registry, "get_reviewable_extraction_run", lambda _root, _id: child)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, _id: parent)
    seen = []

    def record(run_id, *, expected_revision, basis, decision):
        assert isinstance(basis, RecapSemanticBasisV12)
        assert basis.digest() == response.semantic_basis_sha256
        assert basis.operation_basis.derivation == service.DERIVATION_V4
        assert basis.operation_basis.manifest_schema == service.MANIFEST_SCHEMA_V4
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

    parent, _parent_bytes, runs, request = _evidence_batch_fixture(monkeypatch, tmp_path)
    response = service.correct_recap_candidate(request)
    child = runs[response.run_id]
    monkeypatch.setattr(extract_promote, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(graph_run_registry, "get_reviewable_extraction_run", lambda _root, _id: child)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, _id: parent)
    seen = []

    def record(run_id, *, expected_revision, basis, decision):
        assert isinstance(basis, RecapSemanticBasisV12)
        assert basis.digest() == response.semantic_basis_sha256
        assert basis.operation_basis.derivation == service.DERIVATION_V5
        assert basis.operation_basis.manifest_schema == service.MANIFEST_SCHEMA_V5
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
        assert binding["derivation"] == service.SOURCE_BINDING_DERIVATION_V11
        assert binding["operation_derivation"] == service.DERIVATION_V2
        assert binding["operation_manifest_schema"] == service.MANIFEST_SCHEMA_V2
    locator = str(_candidate_path(tmp_path, child))
    extract_promote._assert_recap_semantics_at_confirm(locator, {"effect": {EFFECT_KEY: binding}})
    with pytest.raises(extract_promote.ExtractPromoteError):
        extract_promote._assert_recap_semantics_at_confirm(locator, {"effect": {EFFECT_KEY: {**binding, "manifest_sha256": "f" * 64}}})
    candidate = _candidate_path(tmp_path, child)
    candidate.write_bytes(candidate.read_bytes() + b" ")
    with pytest.raises(extract_promote.ExtractPromoteError) as drifted:
        extract_promote._assert_recap_semantics_at_confirm(locator, {"effect": {EFFECT_KEY: binding}})
    assert drifted.value.code == "recap_semantic_hold"


def _split_fixture(monkeypatch, root, *, duplicate_quotes=False, foreign_span=False, holder_kind="node"):
    lines = [""] * 22
    lines[15] = "Mira rests in the room."
    lines[19] = "Mira breaks a tunnel and plants a shield. Echo."
    lines[21] = "Mira activates a synthetic aura. Echo."
    source_text = "\n".join(lines) + "\n"
    parent, raw, runs = _fixture(monkeypatch, root, source_text=source_text)
    payload = json.loads(raw)
    source_sha = _sha(source_text.encode())
    artifact = parent.source_artifact_id
    spans = [{
        "source_span_id": f"{artifact}:span:{source_sha[:12]}:{line}-{line}",
        "source_ref_id": "ref:mira", "source_artifact_id": artifact,
        "content_sha256": source_sha, "start_line": line, "end_line": line,
    } for line in (16, 20, 22)]
    if foreign_span:
        spans[2]["source_artifact_id"] = "foreign-artifact"
    index = {"schema": "dmb_source_span_index_v1", "version": "1.0", "source_artifact_id": artifact, "source_ref_id": "ref:mira", "content_sha256": source_sha, "spans": spans}
    index_bytes = service._canonical_bytes(index)
    (root / "spans.json").write_bytes(index_bytes)
    original_ref = payload["nodes"][0]["evidence_refs"][0]
    original_ref["source_span_ref_id"] = spans[0]["source_span_id"]
    original_ref["anchor_quotes"] = [lines[15]]
    target = copy.deepcopy(original_ref)
    target.update({
        "source_span_ref_id": spans[1]["source_span_id"],
        "source_anchor_id": f"anchor:{spans[1]['source_span_id']}",
        "label": spans[1]["source_span_id"],
        "anchor_quotes": ["Echo."] * 3 if duplicate_quotes else ["breaks a tunnel", "plants a shield", "activates a synthetic aura"],
    })
    after = copy.deepcopy(original_ref)
    after["source_span_ref_id"] = spans[2]["source_span_id"]
    after["anchor_quotes"] = ["Echo."]
    payload["nodes"][0]["evidence_refs"] = [original_ref, target, after]
    retained = copy.deepcopy(payload["nodes"][0])
    retained.update({"node_id": "room", "node_type": "location", "label": "Room", "evidence_refs": [copy.deepcopy(original_ref)]})
    payload["nodes"].append(retained)
    payload["edges"] = [{
        "edge_id": "e", "from_node_id": "mira", "to_node_id": "room", "relationship_type": "located_in", "label": "rests in", "evidence_refs": [copy.deepcopy(original_ref)], "semantic_state": copy.deepcopy(payload["nodes"][0]["semantic_state"]), "proposed_action": "create", "confidence": "medium",
    }]
    if holder_kind == "edge":
        payload["edges"][0]["evidence_refs"] = copy.deepcopy(payload["nodes"][0]["evidence_refs"])
        payload["nodes"][0]["evidence_refs"] = [original_ref, after]
    raw = service._canonical_bytes(payload)
    (root / "parent.json").write_bytes(raw)
    components = dict(parent.components)
    for key, value in (("candidate_graph", raw), ("source_span_index", index_bytes)):
        components[key] = components[key].model_copy(update={"sha256": _sha(value)})
    parent = parent.model_copy(update={"components": components})
    runs["parent"] = parent
    monkeypatch.setattr(service, "_load_frozen_span_index_for_resolved_run", lambda _resolved: SimpleNamespace(spans=[SimpleNamespace(**span) for span in spans]))
    body = {
        "schema": "dmb_recap_candidate_correction_request_v6", "parent_run_id": "parent", "parent_candidate_sha256": _sha(raw),
        "source_revision_sha256": source_sha, "span_index_sha256": _sha(index_bytes),
        "evidence_ref_splits": [{
            "record_kind": holder_kind, "record_id": "mira" if holder_kind == "node" else "e", "evidence_index": 1,
            "expected_evidence_ref_sha256": _sha(service._canonical_bytes(target)),
            "parts": [{"source_span_ref_id": spans[1]["source_span_id"], "quote_indices": [0, 1]}, {"source_span_ref_id": spans[2]["source_span_id"], "quote_indices": [2]}],
        }],
    }
    return parent, raw, runs, body


def _split_http_app(monkeypatch):
    import fastapi.dependencies.utils as dependency_utils
    import fastapi.routing as fastapi_routing

    async def inline_sync(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(fastapi_routing, "run_in_threadpool", inline_sync)
    monkeypatch.setattr(dependency_utils, "run_in_threadpool", inline_sync)
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[native_graph_gm_dependency] = lambda: NativeGraphPrincipal(subject="test_gm", role="gm", auth_method="local_session")
    return app


@pytest.mark.parametrize("duplicate_quotes", [False, True])
@pytest.mark.parametrize("holder_kind", ["node", "edge"])
def test_http_evidence_ref_split_exact_child_is_marked_held(monkeypatch, tmp_path, duplicate_quotes, holder_kind):
    parent, raw, runs, body = _split_fixture(monkeypatch, tmp_path, duplicate_quotes=duplicate_quotes, holder_kind=holder_kind)
    source_before = (tmp_path / "source.md").read_bytes()
    spans_before = (tmp_path / "spans.json").read_bytes()
    app = _split_http_app(monkeypatch)

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            url = "/api/live/extract-promote/runs/parent/recap-candidate-corrections"
            response = await client.post(url, json=body)
            assert response.status_code == 200, response.text
            assert response.json()["schema"] == "dmb_recap_candidate_correction_response_v6"
            assert response.json()["semanticState"] == "held"
            assert (await client.post(url, json=body)).json() == response.json()
            return response.json()

    response = asyncio.run(exercise())
    child = runs[response["runId"]]
    original = json.loads(raw)
    expected = copy.deepcopy(original)
    holder_collection = "nodes" if holder_kind == "node" else "edges"
    before, target, after = original[holder_collection][0]["evidence_refs"]
    outputs = []
    for part in body["evidence_ref_splits"][0]["parts"]:
        ref = copy.deepcopy(target)
        ref.update({"source_span_ref_id": part["source_span_ref_id"], "source_anchor_id": f"anchor:{part['source_span_ref_id']}", "label": part["source_span_ref_id"], "anchor_quotes": [target["anchor_quotes"][i] for i in part["quote_indices"]]})
        outputs.append(ref)
    expected[holder_collection][0]["evidence_refs"] = [before, *outputs, after]
    assert (_candidate_path(tmp_path, child)).read_bytes() == service._canonical_bytes(expected)
    assert (tmp_path / "parent.json").read_bytes() == raw
    assert (tmp_path / "source.md").read_bytes() == source_before
    assert (tmp_path / "spans.json").read_bytes() == spans_before
    _assert_child_source_snapshot(tmp_path, parent, child)
    assert [quote for ref in outputs for quote in ref["anchor_quotes"]] == target["anchor_quotes"]
    assert service.verify_child_replay(child, parent, tmp_path)
    assessment = assess_recap_semantics(child, parent=parent, source_revision_id=_sha(source_before), root=tmp_path)
    assert assessment.marked and not assessment.accepted
    assert child.lineage["semantic_disposition"]["state"] == "held"
    basis = RecapSemanticBasisV12.model_validate(assessment.basis, strict=True)
    assert basis.digest() == response["semanticBasisSha256"]
    assert basis.operation_basis.manifest_sha256 == child.lineage["manifest_sha256"] == response["manifestSha256"]
    _assert_recap_semantic_basis(child, parent, basis)
    with pytest.raises(ValueError, match="not accepted"):
        accepted_effect_binding(child, assessment)
    accepted_lineage = copy.deepcopy(child.lineage)
    accepted_lineage["semantic_disposition"] = {"version": 1, "state": "accepted", "basis_sha256": basis.digest(), "review_decision_ref": "review:split", "reviewer_id": "reviewer", "decided_at": "2026-10-07T00:00:00Z"}
    accepted_child = child.model_copy(update={"lineage": accepted_lineage})
    accepted = assess_recap_semantics(accepted_child, parent=parent, source_revision_id=_sha(source_before), root=tmp_path)
    binding = accepted_effect_binding(accepted_child, accepted)
    assert binding["derivation"] == service.SOURCE_BINDING_DERIVATION_V11
    assert binding["operation_derivation"] == service.DERIVATION_V6
    assert binding["operation_manifest_schema"] == service.MANIFEST_SCHEMA_V6
    assert binding["manifest_sha256"] == basis.operation_basis.manifest_sha256
    # A rehashed malformed stored manifest must fail replay and APP-STATE shape checks.
    bad_manifest = copy.deepcopy(child.lineage["semantic_candidate_manifest"])
    bad_manifest["evidence_ref_splits"][0]["parts"][0]["quote_indices"] = [1, 0]
    bad_sha = _sha(service._canonical_bytes(bad_manifest))
    bad_child = child.model_copy(update={"lineage": {**child.lineage, "semantic_candidate_manifest": bad_manifest, "manifest_sha256": bad_sha}})
    assert not service.verify_child_replay(bad_child, parent, tmp_path)
    with pytest.raises(ApplicationStateConflictError, match="semantic basis components changed"):
        _assert_recap_semantic_basis(bad_child, parent, basis)
    assert not assess_recap_semantics(bad_child, parent=parent, source_revision_id=_sha(source_before), root=tmp_path).accepted


@pytest.mark.parametrize("fault", ["stale_parent", "stale_ref", "source_pin", "index_pin", "lost", "added", "duplicate", "reordered", "same_span", "unindexed", "foreign", "bad_literal", "extra_json", "mixed", "too_many", "bool_index"])
def test_http_evidence_ref_split_rejects_before_any_write(monkeypatch, tmp_path, fault):
    parent, raw, runs, body = _split_fixture(monkeypatch, tmp_path, foreign_span=fault == "foreign")
    operation = body["evidence_ref_splits"][0]
    if fault == "stale_parent":
        body["parent_candidate_sha256"] = "0" * 64
    elif fault == "stale_ref":
        operation["expected_evidence_ref_sha256"] = "0" * 64
    elif fault == "source_pin":
        body["source_revision_sha256"] = "0" * 64
    elif fault == "index_pin":
        body["span_index_sha256"] = "0" * 64
    elif fault in ("lost", "added", "duplicate", "reordered"):
        operation["parts"][0]["quote_indices"] = {"lost": [0], "added": [0, 1, 2], "duplicate": [0, 0], "reordered": [1, 0]}[fault]
        if fault == "lost":
            operation["parts"][1]["quote_indices"] = [1]
        if fault == "added":
            operation["parts"][1]["quote_indices"] = [3]
    elif fault == "same_span":
        operation["parts"][1]["source_span_ref_id"] = operation["parts"][0]["source_span_ref_id"]
    elif fault == "unindexed":
        operation["parts"][1]["source_span_ref_id"] = "span:missing"
    elif fault == "bad_literal":
        operation["parts"].reverse()
        operation["parts"][0]["quote_indices"] = [0, 1]
        operation["parts"][1]["quote_indices"] = [2]
    elif fault == "extra_json":
        operation["replacement_ref"] = {"anchor_quotes": ["fabricated"]}
    elif fault == "mixed":
        body["omitted_edge_ids"] = ["e"]
    elif fault == "too_many":
        body["evidence_ref_splits"] *= 2
    elif fault == "bool_index":
        operation["parts"][0]["quote_indices"] = [False, 1]

    def forbidden_write(*args, **kwargs):
        pytest.fail("invalid split reached a child write")

    monkeypatch.setattr(service, "_publish_child_package_files", forbidden_write)
    monkeypatch.setattr(service, "create_extraction_run", forbidden_write)
    app = _split_http_app(monkeypatch)

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/live/extract-promote/runs/parent/recap-candidate-corrections", json=body)
            assert response.status_code in (409, 422), response.text

    asyncio.run(exercise())
    assert set(runs) == {"parent"}
    assert (tmp_path / "parent.json").read_bytes() == raw
    assert not (tmp_path / "out" / "graph_memory" / "derived_candidates").exists()


def test_split_decision_dispatches_exact_basis_to_appstate_cas(monkeypatch, tmp_path):
    from application_state.ingest import service as ingest_service

    parent, _, runs, body = _split_fixture(monkeypatch, tmp_path)
    response = service.correct_recap_candidate(RecapCandidateCorrectionRequestV6.model_validate(body))
    child = runs[response.run_id]
    monkeypatch.setattr(extract_promote, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(graph_run_registry, "get_reviewable_extraction_run", lambda _root, _id: child)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, _id: parent)
    seen = []

    def record(run_id, *, expected_revision, basis, decision):
        assert isinstance(basis, RecapSemanticBasisV12)
        assert basis.digest() == response.semantic_basis_sha256
        assert basis.operation_basis.derivation == service.DERIVATION_V6
        assert basis.operation_basis.manifest_schema == service.MANIFEST_SCHEMA_V6
        _assert_recap_semantic_basis(child, parent, basis)
        seen.append((run_id, expected_revision))
        decided = child.model_copy(deep=True, update={"revision": expected_revision + 1})
        decided.lineage["semantic_disposition"] = {"version": 1, "state": decision.state, "basis_sha256": basis.digest(), "review_decision_ref": decision.review_decision_ref, "reviewer_id": decision.reviewer_id, "decided_at": "2026-10-07T00:00:00Z", "from_revision": expected_revision}
        return decided

    monkeypatch.setattr(ingest_service, "record_recap_semantic_disposition", record)
    receipt = extract_promote.decide_recap_semantic_disposition(child.run_id, RecapSemanticDecisionRequest(expected_revision=child.revision, candidate_sha256=response.candidate_sha256, decision="accepted", review_decision_ref="review:split"), reviewer_id="gm")
    assert receipt.state == "accepted" and receipt.basis_sha256 == response.semantic_basis_sha256
    assert seen == [(child.run_id, child.revision)]


@pytest.mark.parametrize("version,manifest_sha,child_id", [
    (1, "53c547b5bee2ba5de80c04c17134c9f4d5a8d47fb7651b6c17f7878596b400a4", "61a59049-3686-5680-b569-5b8816497b19"),
    (2, "7736364055515ab421783121fa7e7f76c8d42fd723393ad52e08475f8a3b6b24", "d268e534-22c9-5e3e-af92-6f8ef73d2117"),
    (3, "118f051572259d43b205e0f249b32e539c51619172e75f1dd3c2fe5240a8545c", "3ab3a671-f8b5-5b42-b68d-f8c4d0d7b688"),
    (4, "7816fd4a2bc04fb534c55cad4fc78a108dfd4dc7d5bdb6c4d67074632c562922", "2abce1ad-9326-5d4e-b39f-8e9e73963a9b"),
    (5, "a8eba477c9e072d012d8660347abb56d13da0a0690b499cadc10581dfc8b7bca", "011fb4e0-6d73-583f-9754-757eb9e0ed61"),
])
def test_split_keeps_main_v1_through_v5_manifest_and_child_identity(monkeypatch, tmp_path, version, manifest_sha, child_id):
    # Golden witnesses measured on the unchanged pinned main, not the held lanes.
    if version == 1:
        parent, raw, runs = _fixture(monkeypatch, tmp_path)
        request = _request(raw)
    elif version == 2:
        parent, raw, runs = _fixture(monkeypatch, tmp_path, actions=True)
        request = _action_request(raw)
    elif version == 3:
        parent, raw, runs = _tuple_fixture(monkeypatch, tmp_path)
        request = _tuple_request(raw)
    elif version == 4:
        parent, raw, runs, request, _ = _span_relocation_fixture(monkeypatch, tmp_path)
    else:
        parent, raw, runs, request = _evidence_batch_fixture(monkeypatch, tmp_path)
    response = service.correct_recap_candidate(request)
    assert response.manifest_sha256 == manifest_sha
    operation_derivation = {
        1: service.DERIVATION, 2: service.DERIVATION_V2,
        3: service.DERIVATION_V3, 4: service.DERIVATION_V4,
        5: service.DERIVATION_V5,
    }[version]
    expected_legacy_id = str(uuid5(
        NAMESPACE_URL,
        f"dmb:{operation_derivation}:{parent.run_id}:{_sha(raw)}:{manifest_sha}",
    ))
    assert child_id == expected_legacy_id
    expected_bound_id = str(uuid5(
        NAMESPACE_URL,
        f"dmb:{service.SOURCE_BINDING_DERIVATION_V11}:{parent.run_id}:{_sha(raw)}:{manifest_sha}",
    ))
    assert response.run_id == expected_bound_id
    assert service.verify_child_replay(runs[response.run_id], parent, tmp_path)
    assert (tmp_path / "parent.json").read_bytes() == raw


def _omission_fixture(monkeypatch, root, fault=None):
    parent, _, runs = _fixture(monkeypatch, root)
    payload = json.loads((root / "parent.json").read_bytes())
    retained = copy.deepcopy(payload["nodes"][0])
    retained["node_id"] = "retained"
    payload["nodes"].append(retained)
    if fault == "ambiguous":
        payload["nodes"].append(copy.deepcopy(payload["nodes"][0]))
    if fault == "missing":
        payload["nodes"] = [retained]
    if fault in ("incoming", "outgoing", "self_loop"):
        payload["edges"] = [{
            "edge_id": "incident",
            "from_node_id": "retained" if fault == "incoming" else "mira",
            "to_node_id": "retained" if fault == "outgoing" else "mira",
        }]
    if fault in ("beats", "proposed_writes", "ignored_items", "deferred_items"):
        payload[fault] = [{"nested": [{"target": "mira"}]}]
    raw = service._canonical_bytes(payload)
    (root / "parent.json").write_bytes(raw)
    components = dict(parent.components)
    components["candidate_graph"] = components["candidate_graph"].model_copy(update={"sha256": _sha(raw)})
    parent = parent.model_copy(update={"components": components})
    runs["parent"] = parent
    request = RecapCandidateCorrectionRequest(
        parent_run_id="parent", parent_candidate_sha256=_sha(raw),
        node_omissions=[RecapCandidateNodeOmission(
            node_id="mira", expected_node_sha256=_sha(service._canonical_bytes(payload["nodes"][0])),
        )],
    )
    if fault == "stale":
        request.node_omissions[0].expected_node_sha256 = "0" * 64
    return parent, raw, runs, request


def test_http_node_omission_creates_exact_held_child(monkeypatch, tmp_path):
    parent, raw, runs, request = _omission_fixture(monkeypatch, tmp_path)
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

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            mismatch = await client.post(url, json={**body, "parentRunId": "other"})
            assert mismatch.status_code == 422
            wrong_parent = await client.post(url, json={**body, "parentCandidateSha256": "0" * 64})
            assert wrong_parent.status_code == 409
            assert set(runs) == {"parent"}
            response = await client.post(url, json=body)
            assert response.status_code == 200, response.text
            assert response.json()["semanticState"] == "held"
            assert (await client.post(url, json=body)).json() == response.json()
            return response.json()["runId"]

    child = runs[asyncio.run(exercise())]
    original = json.loads(raw)
    expected = copy.deepcopy(original)
    expected["nodes"] = [original["nodes"][1]]
    assert (_candidate_path(tmp_path, child)).read_bytes() == service._canonical_bytes(expected)
    assert (tmp_path / "parent.json").read_bytes() == raw
    _assert_child_source_snapshot(tmp_path, parent, child)
    assert service.verify_child_replay(child, parent, tmp_path)
    assessment = assess_recap_semantics(child, parent=parent, source_revision_id=_sha((tmp_path / "source.md").read_bytes()), root=tmp_path)
    assert assessment.marked and not assessment.accepted
    basis = RecapSemanticBasisV12.model_validate(assessment.basis, strict=True)
    _assert_recap_semantic_basis(child, parent, basis)
    # Stored manifests must enforce the same operation shape as the route/replay.
    manifest = copy.deepcopy(child.lineage["semantic_candidate_manifest"])
    manifest["node_omissions"][0]["cascade"] = True
    digest = _sha(service._canonical_bytes(manifest))
    malformed = child.model_copy(update={"lineage": {**child.lineage, "semantic_candidate_manifest": manifest, "manifest_sha256": digest}})
    with pytest.raises(ApplicationStateConflictError, match="semantic basis components changed"):
        _assert_recap_semantic_basis(malformed, parent, basis)
    assert not service.verify_child_replay(malformed, parent, tmp_path)


@pytest.mark.parametrize("fault", ["ambiguous", "missing", "stale", "incoming", "outgoing", "self_loop", "beats", "proposed_writes", "ignored_items", "deferred_items"])
def test_node_omission_rejects_before_any_write(monkeypatch, tmp_path, fault):
    parent, raw, runs, request = _omission_fixture(monkeypatch, tmp_path, fault)
    from apps.live_control_server.services.extract_promote import ExtractPromoteError

    def forbidden_write(*args, **kwargs):
        pytest.fail("invalid omission reached a child write")

    monkeypatch.setattr(service, "_publish_child_package_files", forbidden_write)
    monkeypatch.setattr(service, "create_extraction_run", forbidden_write)
    with pytest.raises(ExtractPromoteError) as error:
        service.correct_recap_candidate(request)
    assert error.value.status_code == 409
    assert set(runs) == {"parent"}
    assert not (tmp_path / "out" / "graph_memory" / "derived_candidates").exists()
    assert (tmp_path / "parent.json").read_bytes() == raw


def test_node_omission_contract_is_bounded_and_exact():
    operation = {"node_id": "n", "expected_node_sha256": "a" * 64}
    body = {"parent_run_id": "p", "parent_candidate_sha256": "b" * 64, "node_omissions": [operation]}
    for changes in (
        {"node_omissions": [operation, operation]},
        {"node_omissions": [{**operation, "expected_node_sha256": "wrong"}]},
        {"node_omissions": [{**operation, "cascade": True}]},
        {"omitted_edge_ids": ["e"]},
    ):
        with pytest.raises(ValueError):
            RecapCandidateCorrectionRequest.model_validate({**body, **changes})
    parent = {"nodes": [{"node_id": "n"}], "edges": []}
    manifest = {"schema": service.MANIFEST_SCHEMA, "node_description_replacements": [], "omitted_edge_ids": [], "node_omissions": [operation]}
    for operations in ([], [operation, operation], [{**operation, "cascade": True}]):
        with pytest.raises(ValueError):
            service.replay_candidate(parent, {**manifest, "node_omissions": operations})


def test_legacy_manifest_identity_ignores_unused_node_omission(monkeypatch, tmp_path):
    from uuid import NAMESPACE_URL, uuid5
    parent, raw, runs = _fixture(monkeypatch, tmp_path)
    request = _request(raw)
    response = service.correct_recap_candidate(request)
    manifest = {
        "schema": "dmb_recap_semantic_candidate_manifest_v1",
        "node_description_replacements": [{"node_id": "mira", "original_description": "Mira carried an uncertain object.", "replacement_description": "Mira found the key under the bridge."}],
        "omitted_edge_ids": [],
    }
    digest = _sha(service._canonical_bytes(manifest))
    assert runs[response.run_id].lineage["semantic_candidate_manifest"] == manifest
    assert digest == "53c547b5bee2ba5de80c04c17134c9f4d5a8d47fb7651b6c17f7878596b400a4"
    assert response.manifest_sha256 == digest
    legacy_run_id = str(uuid5(
        NAMESPACE_URL,
        f"dmb:{service.DERIVATION}:parent:{_sha(raw)}:{digest}",
    ))
    assert legacy_run_id == "61a59049-3686-5680-b569-5b8816497b19"
    assert response.run_id != legacy_run_id
    assert response.run_id == str(uuid5(
        NAMESPACE_URL,
        f"dmb:{service.SOURCE_BINDING_DERIVATION_V11}:parent:{_sha(raw)}:{digest}",
    ))
    assert service.verify_child_replay(runs[response.run_id], parent, tmp_path)


def _multiple_bad_quote_fixture(monkeypatch, root):
    parent, raw, runs, split = _split_fixture(monkeypatch, root)
    payload = json.loads(raw)
    payload["nodes"][0]["evidence_refs"][0]["anchor_quotes"] = ["unchanged bad first quote"]
    payload["nodes"][1]["evidence_refs"][0]["anchor_quotes"] = ["unchanged bad second quote"]
    raw = service._canonical_bytes(payload)
    (root / "parent.json").write_bytes(raw)
    components = dict(parent.components)
    components["candidate_graph"] = components["candidate_graph"].model_copy(update={"sha256": _sha(raw)})
    parent = parent.model_copy(update={"components": components})
    runs["parent"] = parent
    split["parent_candidate_sha256"] = _sha(raw)
    return parent, raw, runs, split


def test_http_incremental_description_split_and_strict_acceptance(monkeypatch, tmp_path):
    from application_state.ingest import service as ingest_service
    parent, raw, runs, split = _multiple_bad_quote_fixture(monkeypatch, tmp_path)
    frozen = parent.model_dump(mode="json")
    app = _split_http_app(monkeypatch)
    monkeypatch.setattr(extract_promote, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(graph_run_registry, "get_reviewable_extraction_run", lambda _root, key: runs[key])
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, key: runs[key])
    monkeypatch.setattr(extract_promote, "resolve_first_world_capability", lambda **_kwargs: SimpleNamespace(world_id="w", world_state="initialized", eligible=True, reason=None))
    # Add only review metadata to the frozen-component resolver; quote validation stays real.
    original_resolver = service.resolve_promotable_ingest_run
    def resolve(key, **kwargs):
        result = original_resolver(key, **kwargs)
        result.status = runs[key].status.value
        result.diagnostics = []
        return result
    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", resolve)
    calls = []
    def record(key, *, expected_revision, basis, decision):
        run = runs[key]
        assert run.revision == expected_revision
        _assert_recap_semantic_basis(run, runs[run.lineage["parent_run_id"]], basis)
        calls.append(key)
        updated = run.model_copy(deep=True, update={"revision": expected_revision + 1})
        updated.lineage["semantic_disposition"] = {"version": 1, "state": decision.state,
            "basis_sha256": basis.digest(), "review_decision_ref": decision.review_decision_ref,
            "reviewer_id": decision.reviewer_id, "decided_at": "2026-10-07T00:00:00Z"}
        runs[key] = updated
        return updated
    monkeypatch.setattr(ingest_service, "record_recap_semantic_disposition", record)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            url = "/api/live/extract-promote/runs/parent/recap-candidate-corrections"
            description = RecapCandidateCorrectionRequest(parent_run_id="parent", parent_candidate_sha256=_sha(raw),
                node_description_replacements=[RecapNodeDescriptionReplacement(node_id="mira",
                    original_description=json.loads(raw)["nodes"][0]["description"], replacement_description="Mira rests in the room.")])
            desc = await client.post(url, json=description.model_dump(mode="json", by_alias=True))
            assert desc.status_code == 200, desc.text
            assert desc.json()["semanticState"] == "held"
            assert (await client.post(url, json=description.model_dump(mode="json", by_alias=True))).json() == desc.json()
            separated = await client.post(url, json=split)
            assert separated.status_code == 200, separated.text
            key = separated.json()["runId"]
            child = runs[key]
            assert service.verify_child_replay(child, parent, tmp_path)
            _assert_child_source_snapshot(tmp_path, parent, child)
            view = await client.get(f"/api/live/extract-promote/runs/{key}/review-package")
            assert view.status_code == 200, view.text
            assert view.json()["invalidEvidenceCount"] == 2
            binding = json.loads(next(d.split(":",1)[1] for d in view.json()["diagnostics"] if d.startswith("unresolved_quote_binding:")))
            assert binding["candidate_sha256"] == separated.json()["candidateSha256"]
            assert binding["source_sha256"] == parent.components["source_artifact"].sha256
            assert binding["span_index_sha256"] == parent.components["source_span_index"].sha256
            assert len(binding["occurrences"]) == 2
            decision = {"expectedRevision": child.revision, "candidateSha256": separated.json()["candidateSha256"],
                "decision": "accepted", "reviewDecisionRef": "review:test"}
            refused = await client.post(f"/api/live/extract-promote/runs/{key}/semantic-disposition", json=decision)
            assert refused.status_code == 422, refused.text
            assert calls == []
            payload = json.loads((_candidate_path(tmp_path, child)).read_bytes())
            replacements = []
            for kind, identifier in [("node", "mira"), ("node", "room")]:
                ref = next(n for n in payload["nodes"] if n["node_id"] == identifier)["evidence_refs"][0]
                replacements.append(RecapCandidateEvidenceReplacementV5(record_kind=kind, record_id=identifier, evidence_index=0,
                    expected_source_ref_id=ref["source_ref_id"], expected_source_artifact_id=ref["source_artifact_id"],
                    expected_source_span_ref_id=ref["source_span_ref_id"], replacement_source_span_ref_id=ref["source_span_ref_id"],
                    expected_anchor_quotes=ref["anchor_quotes"], replacement_anchor_quotes=["Mira rests in the room."]))
            repaired = RecapCandidateCorrectionRequestV5(schema="dmb_recap_candidate_correction_request_v5",
                parent_run_id=key, parent_candidate_sha256=separated.json()["candidateSha256"], evidence_replacements=replacements)
            result = await client.post(f"/api/live/extract-promote/runs/{key}/recap-candidate-corrections", json=repaired.model_dump(mode="json",by_alias=True))
            assert result.status_code == 200, result.text
            ready_id = result.json()["runId"]
            ready = runs[ready_id]
            accepted = await client.post(f"/api/live/extract-promote/runs/{ready_id}/semantic-disposition",
                json={**decision, "expectedRevision": ready.revision, "candidateSha256": result.json()["candidateSha256"]})
            assert accepted.status_code == 200, accepted.text
            assert calls == [ready_id]
            assert parent.model_dump(mode="json") == frozen
            assert (tmp_path / "parent.json").read_bytes() == raw
    asyncio.run(exercise())


def test_changed_invalid_reference_rejected_before_child_write(monkeypatch, tmp_path):
    parent, raw, runs, split = _multiple_bad_quote_fixture(monkeypatch, tmp_path)
    ref = json.loads(raw)["nodes"][0]["evidence_refs"][0]
    request = RecapCandidateCorrectionRequestV5(schema="dmb_recap_candidate_correction_request_v5",
        parent_run_id="parent", parent_candidate_sha256=_sha(raw), evidence_replacements=[RecapCandidateEvidenceReplacementV5(
            record_kind="node", record_id="mira", evidence_index=0,
            expected_source_ref_id=ref["source_ref_id"], expected_source_artifact_id=ref["source_artifact_id"],
            expected_source_span_ref_id=ref["source_span_ref_id"], expected_anchor_quotes=ref["anchor_quotes"],
            replacement_source_span_ref_id=split["evidence_ref_splits"][0]["parts"][0]["source_span_ref_id"],
            replacement_anchor_quotes=ref["anchor_quotes"])])
    app = _split_http_app(monkeypatch)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
            response = await client.post("/api/live/extract-promote/runs/parent/recap-candidate-corrections",json=request.model_dump(mode="json",by_alias=True))
            assert response.status_code == 422
    asyncio.run(exercise())
    assert set(runs) == {"parent"}
    assert not (tmp_path / "out" / "graph_memory" / "derived_candidates").exists()
    assert (tmp_path / "parent.json").read_bytes() == raw


@pytest.mark.parametrize("label_target", ["mira", "retained"])
def test_node_omission_cannot_mix_with_label_correction(monkeypatch, tmp_path, label_target):
    parent, raw, runs, omission = _omission_fixture(monkeypatch, tmp_path)
    label = RecapNodeLabelReplacement(node_id=label_target, original_label="Mira", replacement_label="Corrected Mira")
    body = omission.model_dump(mode="json", by_alias=True)
    body["nodeLabelReplacements"] = [label.model_dump(mode="json", by_alias=True)]
    with pytest.raises(ValueError, match="node omission must be the only"):
        RecapCandidateCorrectionRequest.model_validate(body)
    app = _split_http_app(monkeypatch)

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/live/extract-promote/runs/parent/recap-candidate-corrections", json=body)
            assert response.status_code == 422, response.text

    def forbidden_write(*args, **kwargs):
        pytest.fail("mixed omission/label reached a child write")

    with monkeypatch.context() as guarded:
        guarded.setattr(service, "_publish_child_package_files", forbidden_write)
        guarded.setattr(service, "create_extraction_run", forbidden_write)
        asyncio.run(exercise())
        # Replay must enforce the same restriction even when model validation is bypassed.
        with pytest.raises(ValueError, match="node omission must be the only"):
            service.correct_recap_candidate(omission.model_copy(update={"node_label_replacements": [label]}))
    assert set(runs) == {"parent"}
    assert not (tmp_path / "out" / "graph_memory" / "derived_candidates").exists()
    assert (tmp_path / "parent.json").read_bytes() == raw

    response = service.correct_recap_candidate(omission)
    child = runs[response.run_id]
    assessment = assess_recap_semantics(child, parent=parent, source_revision_id=_sha((tmp_path / "source.md").read_bytes()), root=tmp_path)
    basis = RecapSemanticBasisV12.model_validate(assessment.basis, strict=True)
    _assert_recap_semantic_basis(child, parent, basis)
    manifest = copy.deepcopy(child.lineage["semantic_candidate_manifest"])
    manifest["node_label_replacements"] = [label.model_dump(mode="json")]
    digest = _sha(service._canonical_bytes(manifest))
    mixed_child = child.model_copy(update={"lineage": {**child.lineage, "semantic_candidate_manifest": manifest, "manifest_sha256": digest}})
    assert not service.verify_child_replay(mixed_child, parent, tmp_path)
    with pytest.raises(ApplicationStateConflictError, match="semantic basis components changed"):
        _assert_recap_semantic_basis(mixed_child, parent, basis)


def _atomic_fixture(monkeypatch, root):
    parent, _, runs, _ = _split_fixture(monkeypatch, root)
    index = json.loads((root / "spans.json").read_bytes())
    index["source_ref_id"] = parent.source_artifact_id + ":text"
    for span in index["spans"]:
        span["source_ref_id"] = index["source_ref_id"]
    index_bytes = service._canonical_bytes(index)
    (root / "spans.json").write_bytes(index_bytes)
    payload = json.loads((root / "parent.json").read_bytes())
    for ref in payload["nodes"][0]["evidence_refs"]:
        ref["source_ref_id"] = index["source_ref_id"]
    item = copy.deepcopy(payload["nodes"][0])
    item.update(node_id="key", node_type="item", label="Key", description="The key.")
    item["evidence_refs"] = [copy.deepcopy(payload["nodes"][0]["evidence_refs"][0])]
    payload["nodes"].append(item)
    base = {"edge_id": "reversed", "from_node_id": "key", "relationship_type": "possesses",
            "to_node_id": "mira", "label": "key owns Mira", "proposed_action": "create",
            "confidence": "medium", "semantic_state": item["semantic_state"],
            "evidence_refs": copy.deepcopy(item["evidence_refs"])}
    payload["edges"] = [base, {**copy.deepcopy(base), "edge_id": "unsupported", "label": "unsupported claim"}]
    raw = service._canonical_bytes(payload)
    (root / "parent.json").write_bytes(raw)
    components = dict(parent.components)
    components["candidate_graph"] = components["candidate_graph"].model_copy(update={"sha256": _sha(raw)})
    components["source_span_index"] = components["source_span_index"].model_copy(update={"sha256": _sha(index_bytes)})
    parent = parent.model_copy(update={"components": components}); runs["parent"] = parent
    monkeypatch.setattr(service, "_load_frozen_span_index_for_resolved_run", lambda _: SimpleNamespace(spans=[SimpleNamespace(**span) for span in index["spans"]]))
    body = {
        "schema": "dmb_recap_candidate_correction_request_v7", "parent_run_id": "parent",
        "parent_candidate_sha256": _sha(raw), "source_revision_sha256": _sha((root / "source.md").read_bytes()),
        "span_index_sha256": _sha(index_bytes), "profile_id": service.PROFILE,
        "node_description_replacements": [{"node_id": "mira", "original_description": payload["nodes"][0]["description"], "replacement_description": "Mira rests, breaks a tunnel and activates an aura."}],
        "node_label_replacements": [{"node_id": "mira", "original_label": "Mira", "replacement_label": "Mira (session)"}],
        "edge_tuple_replacements": [{"edge_id": "reversed", "expected_tuple": {k: base[k] for k in service.EDGE_TUPLE_FIELDS},
                                    "replacement_tuple": {"from_node_id": "mira", "relationship_type": "holds", "to_node_id": "key", "label": "holds key"}}],
        "edge_omissions": [{"edge_id": "unsupported", "expected_edge_sha256": _sha(service._canonical_bytes(payload["edges"][1]))}],
        "evidence_replacements": [
            {"record_kind": "node", "record_id": "mira", "evidence_index": i,
             "expected_evidence_ref_sha256": _sha(service._canonical_bytes(payload["nodes"][0]["evidence_refs"][i])),
             "source_span_ref_id": index["spans"][span_i]["source_span_id"], "anchor_quotes": [quote]}
            for i, span_i, quote in [(0, 2, "Mira activates a synthetic aura."), (1, 1, "Mira breaks a tunnel and plants a shield.")]
        ],
    }
    return parent, raw, runs, body


def test_http_atomic_batch_one_held_child_idempotent_replay_and_basis(monkeypatch, tmp_path):
    parent, raw, runs, body = _atomic_fixture(monkeypatch, tmp_path)
    source_before = (tmp_path / "source.md").read_bytes()
    spans_before = (tmp_path / "spans.json").read_bytes()
    app = _split_http_app(monkeypatch)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            url = "/api/live/extract-promote/runs/parent/recap-candidate-corrections"
            first = await client.post(url, json=body)
            assert first.status_code == 200, first.text
            assert first.json()["schema"] == "dmb_recap_candidate_correction_response_v7"
            assert (await client.post(url, json=body)).json() == first.json()
            return first.json()
    response = asyncio.run(exercise())
    assert len(runs) == 2
    child = runs[response["runId"]]
    assert child.status == ExtractionRunStatus.REVIEWABLE and response["semanticState"] == "held"
    assert service.verify_child_replay(child, parent, tmp_path)
    assessment = assess_recap_semantics(child, parent=parent, source_revision_id=_sha(source_before), root=tmp_path)
    assert assessment.marked and not assessment.accepted
    basis = RecapSemanticBasisV12.model_validate(assessment.basis, strict=True)
    _assert_recap_semantic_basis(child, parent, basis)
    assert basis.digest() == response["semanticBasisSha256"]
    candidate = json.loads((_candidate_path(tmp_path, child)).read_bytes())
    assert candidate["nodes"][0]["label"] == "Mira (session)"
    assert candidate["edges"][0]["from_node_id"] == "mira" and len(candidate["edges"]) == 1
    for ref in candidate["nodes"][0]["evidence_refs"][:2]:
        assert ref["source_anchor_id"] == "anchor:" + ref["source_span_ref_id"]
        assert ref["label"] == ref["source_span_ref_id"]
        assert ref["source_ref_id"] == parent.source_artifact_id + ":text"
    assert (tmp_path / "parent.json").read_bytes() == raw
    assert (tmp_path / "source.md").read_bytes() == source_before
    assert (tmp_path / "spans.json").read_bytes() == spans_before
    drifted = child.model_copy(deep=True)
    drifted.lineage["semantic_candidate_manifest"]["edge_omissions"][0]["expected_edge_sha256"] = "f" * 64
    with pytest.raises(ApplicationStateConflictError):
        _assert_recap_semantic_basis(drifted, parent, basis)
    assert not service.verify_child_replay(drifted, parent, tmp_path)


@pytest.mark.parametrize("failure", ["description", "label", "tuple", "evidence", "omission", "source", "span", "profile", "quote", "overlap", "duplicate", "foreign_span", "native_kind", "bad_anchor_field"])
def test_http_atomic_batch_rejects_entire_request_without_persistence(monkeypatch, tmp_path, failure):
    parent, raw, runs, body = _atomic_fixture(monkeypatch, tmp_path)
    if failure == "description": body["node_description_replacements"][0]["original_description"] = "stale"
    elif failure == "label": body["node_label_replacements"][0]["original_label"] = "stale"
    elif failure == "tuple": body["edge_tuple_replacements"][0]["expected_tuple"]["label"] = "stale"
    elif failure == "evidence": body["evidence_replacements"][0]["expected_evidence_ref_sha256"] = "f" * 64
    elif failure == "omission": body["edge_omissions"][0]["expected_edge_sha256"] = "f" * 64
    elif failure == "source": body["source_revision_sha256"] = "f" * 64
    elif failure == "span": body["span_index_sha256"] = "f" * 64
    elif failure == "profile": body["profile_id"] = "foreign"
    elif failure == "quote": body["evidence_replacements"][0]["anchor_quotes"] = ["fabricated words"]
    elif failure == "overlap": body["edge_omissions"][0]["edge_id"] = "reversed"
    elif failure == "duplicate": body["node_label_replacements"] *= 2
    elif failure == "foreign_span": body["evidence_replacements"][0]["source_span_ref_id"] = "foreign"
    elif failure == "native_kind": body["edge_tuple_replacements"][0]["replacement_tuple"]["relationship_type"] = "defends_weakened_location"
    else: body["evidence_replacements"][0]["source_anchor_id"] = "caller-anchor"
    app = _split_http_app(monkeypatch)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            result = await client.post("/api/live/extract-promote/runs/parent/recap-candidate-corrections", json=body)
            assert result.status_code in {409, 422}, result.text
    asyncio.run(exercise())
    assert runs == {"parent": parent}
    assert (tmp_path / "parent.json").read_bytes() == raw
    assert not (tmp_path / "out/graph_memory/derived_candidates").exists()


def test_atomic_request_per_kind_and_total_bounds(monkeypatch, tmp_path):
    from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV7
    from pydantic import ValidationError
    _, _, _, body = _atomic_fixture(monkeypatch, tmp_path)
    for key, limit in [("node_description_replacements", 8), ("node_label_replacements", 4), ("edge_tuple_replacements", 2), ("evidence_replacements", 2), ("edge_omissions", 3)]:
        oversized = copy.deepcopy(body); oversized[key] = oversized[key][:1] * (limit + 1)
        with pytest.raises(ValidationError): RecapCandidateCorrectionRequestV7.model_validate(oversized)


def test_http_atomic_full_19_recipe_order_independent(monkeypatch, tmp_path):
    parent, _, runs, body = _atomic_fixture(monkeypatch, tmp_path)
    payload = json.loads((tmp_path / "parent.json").read_bytes())
    for i in range(5):
        actor = copy.deepcopy(payload["nodes"][1]); actor.update(node_id=f"actor{i}", node_type="character", label=f"Actor {i}")
        payload["nodes"].append(actor)
    second = copy.deepcopy(payload["edges"][0]); second.update(edge_id="reversed2", to_node_id="actor0", label="owns actor0")
    payload["edges"].append(second)
    for i in range(2):
        edge = copy.deepcopy(payload["edges"][1]); edge.update(edge_id=f"omit{i}", label=f"unsupported{i}")
        payload["edges"].append(edge)
    raw = service._canonical_bytes(payload); (tmp_path / "parent.json").write_bytes(raw)
    components = dict(parent.components); components["candidate_graph"] = components["candidate_graph"].model_copy(update={"sha256": _sha(raw)})
    parent = parent.model_copy(update={"components": components}); runs["parent"] = parent
    body["parent_candidate_sha256"] = _sha(raw)
    body["node_description_replacements"] = [{"node_id": n["node_id"], "original_description": n["description"], "replacement_description": "Observed " + n["description"]} for n in payload["nodes"]]
    body["node_label_replacements"] = [{"node_id": n["node_id"], "original_label": n["label"], "replacement_label": n["label"] + " (session)"} for n in payload["nodes"][:4]]
    body["edge_tuple_replacements"].append({"edge_id": second["edge_id"], "expected_tuple": {k: second[k] for k in service.EDGE_TUPLE_FIELDS}, "replacement_tuple": {"from_node_id": "actor0", "relationship_type": "holds", "to_node_id": "key", "label": "holds key"}})
    body["edge_omissions"] = [{"edge_id": e["edge_id"], "expected_edge_sha256": _sha(service._canonical_bytes(e))} for e in payload["edges"] if e["edge_id"] in {"unsupported", "omit0", "omit1"}]
    from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV7
    RecapCandidateCorrectionRequestV7.model_validate(body)
    app = _split_http_app(monkeypatch)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            url = "/api/live/extract-promote/runs/parent/recap-candidate-corrections"
            response = await client.post(url, json=body); assert response.status_code == 200, response.text
            reordered = copy.deepcopy(body)
            for key in ("node_description_replacements", "node_label_replacements", "edge_tuple_replacements", "evidence_replacements", "edge_omissions"): reordered[key].reverse()
            assert (await client.post(url, json=reordered)).json() == response.json()
            return response.json()
    result = asyncio.run(exercise()); child = runs[result["runId"]]
    assert len(runs) == 2 and result["semanticState"] == "held"
    candidate = json.loads((_candidate_path(tmp_path, child)).read_bytes())
    assert len(candidate["nodes"]) == 8 and len(candidate["edges"]) == 2
    assert service.verify_child_replay(child, parent, tmp_path)
    assert (tmp_path / "parent.json").read_bytes() == raw


@pytest.mark.parametrize("collection", ["beats", "proposed_writes", "ignored_items", "deferred_items"])
def test_http_atomic_omission_rejects_retained_dependencies_before_writes(monkeypatch, tmp_path, collection):
    parent, _, runs, body = _atomic_fixture(monkeypatch, tmp_path)
    payload = json.loads((tmp_path / "parent.json").read_bytes())
    payload[collection] = [{"nested": {"retained_edge_ids": ["unsupported"]}}]
    raw = service._canonical_bytes(payload); (tmp_path / "parent.json").write_bytes(raw)
    components = dict(parent.components)
    components["candidate_graph"] = components["candidate_graph"].model_copy(update={"sha256": _sha(raw)})
    parent = parent.model_copy(update={"components": components}); runs["parent"] = parent
    body["parent_candidate_sha256"] = _sha(raw)
    writes = []
    monkeypatch.setattr(service, "_publish_child_package_files", lambda *args, **kwargs: writes.append("file"))
    monkeypatch.setattr(service, "create_extraction_run", lambda *args, **kwargs: writes.append("run"))
    app = _split_http_app(monkeypatch)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/live/extract-promote/runs/parent/recap-candidate-corrections", json=body)
            assert response.status_code == 409, response.text
            assert "dependent candidate record" in response.json()["message"]
    asyncio.run(exercise())
    assert writes == [] and runs == {"parent": parent}
    assert (tmp_path / "parent.json").read_bytes() == raw
    assert not (tmp_path / "out/graph_memory/derived_candidates").exists()


def test_http_atomic_bad_last_operation_does_not_persist_earlier_edits(monkeypatch, tmp_path):
    parent, raw, runs, body = _atomic_fixture(monkeypatch, tmp_path)
    # Earlier descriptions, labels, tuple, omission and first evidence edit are valid.
    body["evidence_replacements"][-1]["anchor_quotes"] = ["not in the frozen source"]
    writes = []
    monkeypatch.setattr(service, "_publish_child_package_files", lambda *args, **kwargs: writes.append("file"))
    monkeypatch.setattr(service, "create_extraction_run", lambda *args, **kwargs: writes.append("run"))
    app = _split_http_app(monkeypatch)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/live/extract-promote/runs/parent/recap-candidate-corrections", json=body)
            assert response.status_code == 422, response.text
            assert "not literal" in response.json()["message"]
    asyncio.run(exercise())
    assert writes == [] and runs == {"parent": parent}
    assert (tmp_path / "parent.json").read_bytes() == raw
    assert not (tmp_path / "out/graph_memory/derived_candidates").exists()


def _final35_fixture(monkeypatch, root):
    parent, _, runs, prior = _atomic_fixture(monkeypatch, root)
    payload = json.loads((root / "parent.json").read_bytes())
    prototype = copy.deepcopy(next(n for n in payload["nodes"] if n["node_id"] == "key"))
    additions = [(f"effect{i}", "item") for i in range(4)] + [("guard", "organization"), ("lookouts", "organization"), ("redundant-wall", "item")]
    additions += [(f"retained{i}", "item") for i in range(29)]
    for identifier, kind in additions:
        node = copy.deepcopy(prototype); node.update(node_id=identifier, node_type=kind, label=identifier, description="Observed " + identifier)
        payload["nodes"].append(node)
    assert len(payload["nodes"]) == 39
    edge_proto = payload["edges"][0]
    def edge(identifier, frm, pred, to):
        return {**copy.deepcopy(edge_proto), "edge_id": identifier, "from_node_id": frm, "relationship_type": pred, "to_node_id": to, "label": identifier}
    payload["edges"] = [edge("held-key", "key", "possesses", "mira"),
        edge("cause0", "effect0", "possesses", "mira"), edge("cause1", "effect1", "possesses", "mira"),
        edge("protection", "mira", "defends_weakened_location", "guard"),
        edge("omit-owned", "effect2", "possesses", "mira"), edge("omit-contains", "effect0", "contains", "key"),
        edge("omit-above", "effect1", "located_in", "mira"), edge("omit-motive", "mira", "defends_weakened_location", "lookouts")]
    payload["edges"] += [edge(f"keep{i}", "mira", "holds", f"retained{i}") for i in range(11)]
    raw = service._canonical_bytes(payload); (root / "parent.json").write_bytes(raw)
    components = dict(parent.components); components["candidate_graph"] = components["candidate_graph"].model_copy(update={"sha256": _sha(raw)})
    parent = parent.model_copy(update={"components": components, "revision": 5}); runs["parent"] = parent
    retained = [n for n in payload["nodes"] if n["node_id"] != "redundant-wall"]
    node_index = {n["node_id"]: n for n in payload["nodes"]}
    kind_targets = [(f"effect{i}", "event") for i in range(4)] + [("guard", "character"), ("lookouts", "group")]
    targets = {"held-key": ("mira", "holds", "key"), "cause0": ("mira", "causes", "effect0"),
               "cause1": ("mira", "causes", "effect1"), "protection": ("mira", "protects", "guard")}
    body = {"schema": "dmb_recap_candidate_correction_request_v8", "parent_run_id": "parent", "expected_parent_revision": 5,
        "parent_candidate_sha256": _sha(raw), "source_revision_sha256": prior["source_revision_sha256"],
        "span_index_sha256": prior["span_index_sha256"], "profile_id": service.PROFILE,
        "node_description_replacements": [{"node_id": n["node_id"], "original_description": n["description"], "replacement_description": "Scene occurrence: " + n["description"]} for n in retained[:10]],
        "node_label_replacements": [{"node_id": n["node_id"], "original_label": n["label"], "replacement_label": n["label"] + " (scene)"} for n in retained[:8]],
        "evidence_replacements": prior["evidence_replacements"],
        "node_type_replacements": [{"node_id": nid, "expected_node_type": node_index[nid]["node_type"], "replacement_node_type": kind} for nid, kind in kind_targets],
        "node_omissions": [{"node_id": "redundant-wall", "expected_node_sha256": _sha(service._canonical_bytes(node_index["redundant-wall"]))}],
        "edge_tuple_replacements": [{"edge_id": e["edge_id"], "expected_tuple": {k: e[k] for k in service.EDGE_TUPLE_FIELDS},
            "replacement_tuple": {"from_node_id": targets[e["edge_id"]][0], "relationship_type": targets[e["edge_id"]][1], "to_node_id": targets[e["edge_id"]][2], "label": "corrected " + e["edge_id"]}} for e in payload["edges"] if e["edge_id"] in targets],
        "edge_omissions": [{"edge_id": e["edge_id"], "expected_edge_sha256": _sha(service._canonical_bytes(e))} for e in payload["edges"] if e["edge_id"].startswith("omit-")]}
    return parent, raw, runs, body


def test_http_final35_one_held53_child_reordered_replay_and_parent_revision(monkeypatch, tmp_path):
    parent, raw, runs, body = _final35_fixture(monkeypatch, tmp_path)
    before_source = (tmp_path / "source.md").read_bytes(); before_index = (tmp_path / "spans.json").read_bytes()
    app = _split_http_app(monkeypatch)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            url = "/api/live/extract-promote/runs/parent/recap-candidate-corrections"
            result = await client.post(url, json=body); assert result.status_code == 200, result.text
            reordered = copy.deepcopy(body)
            for key, value in reordered.items():
                if isinstance(value, list): value.reverse()
            assert (await client.post(url, json=reordered)).json() == result.json()
            return result.json()
    response = asyncio.run(exercise()); child = runs[response["runId"]]
    assert response["schema"] == "dmb_recap_candidate_correction_response_v8" and response["semanticState"] == "held"
    assert len(runs) == 2 and child.revision == 5
    payload = json.loads((_candidate_path(tmp_path, child)).read_bytes())
    assert len(payload["nodes"]) == 38 and len(payload["edges"]) == 15
    assert {n["node_id"]: n["node_type"] for n in payload["nodes"]}["guard"] == "character"
    assert all(n["node_type"] == "event" for n in payload["nodes"] if n["node_id"].startswith("effect"))
    assert service.verify_child_replay(child, parent, tmp_path)
    assessment = assess_recap_semantics(child, parent=parent, source_revision_id=_sha(before_source), root=tmp_path)
    basis = RecapSemanticBasisV12.model_validate(assessment.basis, strict=True)
    assert basis.digest() == response["semanticBasisSha256"] and not assessment.accepted
    _assert_recap_semantic_basis(child, parent, basis)
    with pytest.raises(ApplicationStateConflictError, match="parent revision"):
        _assert_recap_semantic_basis(child, parent.model_copy(update={"revision": 6}), basis)
    assert (tmp_path / "parent.json").read_bytes() == raw and (tmp_path / "source.md").read_bytes() == before_source
    assert (tmp_path / "spans.json").read_bytes() == before_index


@pytest.mark.parametrize("failure", ["parent_revision", "kind_stale", "kind_npc", "node_hash", "node_edited_omitted", "node_dependency", "edge_dependency", "last_evidence", "last_tuple", "unchanged_bad_tuple", "last_description", "last_label"])
def test_http_final35_failure_has_zero_file_or_row_effects(monkeypatch, tmp_path, failure):
    parent, raw, runs, body = _final35_fixture(monkeypatch, tmp_path)
    if failure == "parent_revision": body["expected_parent_revision"] = 6
    elif failure == "kind_stale": body["node_type_replacements"][-1]["expected_node_type"] = "item"
    elif failure == "kind_npc": body["node_type_replacements"][-2]["replacement_node_type"] = "npc"
    elif failure == "node_hash": body["node_omissions"][0]["expected_node_sha256"] = "f" * 64
    elif failure == "node_edited_omitted": body["node_omissions"][0]["node_id"] = "mira"
    elif failure in {"node_dependency", "edge_dependency", "unchanged_bad_tuple"}:
        payload = json.loads(raw)
        if failure == "node_dependency": payload["deferred_items"] = [{"ref": "redundant-wall"}]
        elif failure == "edge_dependency": payload["beats"] = [{"ref": "omit-contains"}]
        else: payload["edges"][-1]["from_node_id"] = "effect3"  # After event conversion, untouched holds is invalid.
        raw = service._canonical_bytes(payload); (tmp_path / "parent.json").write_bytes(raw)
        components = dict(parent.components); components["candidate_graph"] = components["candidate_graph"].model_copy(update={"sha256": _sha(raw)})
        parent = parent.model_copy(update={"components": components}); runs["parent"] = parent; body["parent_candidate_sha256"] = _sha(raw)
    elif failure == "last_evidence": body["evidence_replacements"][-1]["anchor_quotes"] = ["fabricated"]
    elif failure == "last_tuple": body["edge_tuple_replacements"][-1]["replacement_tuple"]["relationship_type"] = "contains"
    elif failure == "last_description": body["node_description_replacements"][-1]["original_description"] = "stale"
    else: body["node_label_replacements"][-1]["original_label"] = "stale"
    writes = []
    monkeypatch.setattr(service, "_publish_child_package_files", lambda *args, **kwargs: writes.append("file"))
    monkeypatch.setattr(service, "create_extraction_run", lambda *args, **kwargs: writes.append("row"))
    app = _split_http_app(monkeypatch)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            result = await client.post("/api/live/extract-promote/runs/parent/recap-candidate-corrections", json=body)
            assert result.status_code in {409, 422}, result.text
    asyncio.run(exercise())
    assert writes == [] and runs == {"parent": parent} and (tmp_path / "parent.json").read_bytes() == raw
    assert not (tmp_path / "out/graph_memory/derived_candidates").exists()


def test_final35_per_kind_caps_are_distinct_from_v7(monkeypatch, tmp_path):
    from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV7, RecapCandidateCorrectionRequestV8
    from pydantic import ValidationError
    _, _, _, body = _final35_fixture(monkeypatch, tmp_path)
    RecapCandidateCorrectionRequestV8.model_validate(body)
    for key, count in [("node_description_replacements", 10), ("node_label_replacements", 8), ("evidence_replacements", 2), ("node_type_replacements", 6), ("node_omissions", 1), ("edge_tuple_replacements", 4), ("edge_omissions", 4)]:
        malformed = copy.deepcopy(body); malformed[key] = malformed[key][:1] * (count + 1)
        with pytest.raises(ValidationError): RecapCandidateCorrectionRequestV8.model_validate(malformed)
    with pytest.raises(ValidationError): RecapCandidateCorrectionRequestV7.model_validate({**body, "schema": "dmb_recap_candidate_correction_request_v7"})


def _pc_reference_fixture(monkeypatch, root, *, source_text="Mira found the key under the bridge.\n"):
    from apps.live_control_server.models.world_graph_mutation_context import (
        MutationObject, WorldGraphMutationContext,
    )
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes
    from graph_memory import party_context
    from graph_memory.source_span import build_stable_source_span_id, document_source_ref_id

    parent, _, runs = _fixture(monkeypatch, root, source_text=source_text)
    payload = json.loads((root / "parent.json").read_bytes())
    payload["session_id"] = "session-28"
    payload["nodes"][0]["corpus_ref"] = None
    source_ref_id = document_source_ref_id(parent.source_artifact_id)
    payload["nodes"][0]["evidence_refs"][0]["source_ref_id"] = source_ref_id
    source_sha = _sha((root / "source.md").read_bytes())
    stable_span_id = build_stable_source_span_id(
        source_artifact_id=parent.source_artifact_id,
        content_sha256=source_sha, start_line=1, end_line=1,
    )
    payload["nodes"][0]["evidence_refs"][0]["source_span_ref_id"] = stable_span_id
    raw = service._canonical_bytes(payload)
    (root / "parent.json").write_bytes(raw)
    source = (root / "source.md").read_bytes()
    source_sha = _sha(source)
    span_id = payload["nodes"][0]["evidence_refs"][0]["source_span_ref_id"]
    index = {
        "schema": "dmb_source_span_index_v1", "version": "1.0",
        "source_artifact_id": parent.source_artifact_id, "source_ref_id": source_ref_id,
        "content_sha256": source_sha,
        "spans": [{"source_span_id": span_id, "source_artifact_id": parent.source_artifact_id,
                   "source_ref_id": source_ref_id, "content_sha256": source_sha,
                   "start_line": 1, "end_line": 1}],
    }
    index_bytes = service._canonical_bytes(index)
    (root / "spans.json").write_bytes(index_bytes)
    components = dict(parent.components)
    components["candidate_graph"] = components["candidate_graph"].model_copy(update={"sha256": _sha(raw)})
    components["source_span_index"] = components["source_span_index"].model_copy(update={"sha256": _sha(index_bytes)})
    parent = parent.model_copy(update={"components": components, "session_id": "session-28", "revision": 5})
    _update_source_artifact_record(
        root, parent.source_artifact_id, session_id="session-28",
    )
    runs["parent"] = parent
    original_resolve = service.resolve_promotable_ingest_run
    def resolve(run_id, **kwargs):
        value = original_resolve(run_id, **kwargs)
        value.session_id = "session-28"
        return value
    monkeypatch.setattr(service, "resolve_promotable_ingest_run", resolve)
    monkeypatch.setattr(service, "_load_frozen_span_index_for_resolved_run",
                        lambda _: SimpleNamespace(spans=[SimpleNamespace(**index["spans"][0])]))
    registry_path = root / "corpus/invented/_party_registry.json"
    monkeypatch.setitem(party_context.CAMPAIGN_CORPUS, "c", (Path("corpus"), "invented"))
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(json.dumps({"schema": "party_registry_v1", "campaign_id": "c",
                                         "session_pc_rosters": {"23": ["mira"]}}))
    context = WorldGraphMutationContext(
        world_id="invented-world", revision_id="rev:head", head_revision_id="rev:head",
        objects={"pc:mira": MutationObject(object_id="pc:mira", label="Mira",
                                            kind="player_character", canon_state="canonical",
                                            memory_state="active")},
    )
    monkeypatch.setattr(world_graph_writes, "load_production_mutation_context", lambda _: context)
    body = {
        "schema": "dmb_recap_candidate_correction_request_v9", "parent_run_id": "parent",
        "parent_candidate_sha256": _sha(raw), "expected_parent_revision": 5,
        "source_revision_sha256": source_sha, "span_index_sha256": _sha(index_bytes),
        "profile_id": service.PROFILE, "registry_path": "corpus/invented/_party_registry.json",
        "registry_sha256": _sha(registry_path.read_bytes()), "roster_session": 28,
        "roster_key": "23", "world_id": "invented-world",
        "expected_head_revision_id": "rev:head", "reviewer_id": "reviewer",
        "review_decision_ref": "decision:invented",
        "attachments": [{"node_id": "mira", "expected_corpus_ref": None,
                         "corpus_ref": {"type": "pc", "ref_id": "mira", "resolution": "resolved"},
                         "source_span_ref_id": span_id,
                         "anchor_quote": source.decode().strip(),
                         "pc_mention": "Mira",
                         "native_object_id": "pc:mira"}],
    }
    return parent, raw, runs, body, context


def test_inherited_pc_proof_survives_legacy_v9_into_source_bound_v7(monkeypatch, tmp_path):
    from apps.live_control_server.models.extract_promote import (
        RecapCandidateCorrectionRequestV7, RecapCandidateCorrectionRequestV9,
    )
    from apps.live_control_server.services.recap_semantic_candidate_correction import (
        inherited_pc_proof_digest, inherited_pc_reference_proof,
    )

    parent, _parent_bytes, runs, body, _context = _pc_reference_fixture(monkeypatch, tmp_path)
    created = service.correct_recap_candidate(RecapCandidateCorrectionRequestV9.model_validate(body))
    source_bound = runs.pop(created.run_id)
    source_bound_directory = _candidate_path(tmp_path, source_bound).parent
    candidate_bytes = _candidate_path(tmp_path, source_bound).read_bytes()
    for name in ("source.md", "candidate_graph.json"):
        (source_bound_directory / name).unlink()
    source_bound_directory.rmdir()

    manifest_sha = source_bound.lineage["manifest_sha256"]
    legacy_id = str(uuid5(
        NAMESPACE_URL,
        f"dmb:{service.DERIVATION_V9}:{parent.run_id}:"
        f"{source_bound.lineage['parent_candidate_sha256']}:{manifest_sha}",
    ))
    legacy_relative = f"out/graph_memory/derived_candidates/{legacy_id}/candidate_graph.json"
    legacy_directory = tmp_path / "out/graph_memory/derived_candidates" / legacy_id
    legacy_directory.mkdir(parents=True)
    legacy_candidate = legacy_directory / "candidate_graph.json"
    legacy_candidate.write_bytes(candidate_bytes)

    legacy_lineage = copy.deepcopy(source_bound.lineage)
    for key in (
        "operation_derivation", "operation_manifest_schema",
        "semantic_source_binding_basis_v12",
    ):
        legacy_lineage.pop(key)
    legacy_lineage["derivation"] = service.DERIVATION_V9
    legacy_components = dict(source_bound.components)
    legacy_components["candidate_graph"] = legacy_components["candidate_graph"].model_copy(
        update={"uri": legacy_relative},
    )
    legacy_components["source_artifact"] = parent.components["source_artifact"]
    legacy_components["source_span_index"] = parent.components["source_span_index"]
    legacy = source_bound.model_copy(update={
        "run_id": legacy_id,
        "status": ExtractionRunStatus.REVIEWABLE,
        "components": legacy_components,
        "lineage": legacy_lineage,
    })
    assert service.verify_child_replay(legacy, parent, tmp_path)
    legacy_assessment = assess_recap_semantics(
        legacy, parent=parent, source_revision_id=body["source_revision_sha256"], root=tmp_path,
    )
    assert legacy_assessment.basis_sha256 is not None
    legacy.lineage["semantic_disposition"] = {
        "version": 1, "state": "held", "basis_sha256": legacy_assessment.basis_sha256,
    }
    runs[legacy_id] = legacy

    request = RecapCandidateCorrectionRequestV7.model_validate({
        "schema": "dmb_recap_candidate_correction_request_v7",
        "parent_run_id": legacy_id,
        "parent_candidate_sha256": legacy.components["candidate_graph"].sha256.removeprefix("sha256:"),
        "source_revision_sha256": body["source_revision_sha256"],
        "span_index_sha256": body["span_index_sha256"],
        "profile_id": service.PROFILE,
        "node_description_replacements": [{
            "node_id": "mira",
            "original_description": "Mira carried an uncertain object.",
            "replacement_description": "Mira carried a key through the older legacy route.",
        }],
    })
    response = service.correct_recap_candidate(request)
    child = runs[response.run_id]
    proof = inherited_pc_reference_proof(child, tmp_path)
    assert proof is not None and proof["rows"][0]["origin_run_id"] == legacy_id
    assessment = assess_recap_semantics(
        child, parent=legacy, source_revision_id=body["source_revision_sha256"], root=tmp_path,
    )
    basis = RecapSemanticBasisV12.model_validate(assessment.basis, strict=True)
    assert basis.operation_basis.inherited_pc_proof_sha256 == inherited_pc_proof_digest(proof)
    assert service.verify_child_replay(child, legacy, tmp_path)
    _assert_recap_semantic_basis(child, legacy, basis, get_ancestor=runs.get)


def test_inherited_pc_proof_survives_held_v9_v7_v8_chain(monkeypatch, tmp_path):
    from application_state.ingest.service import RecapSemanticBasisV8
    from apps.live_control_server.models.extract_promote import (
        RecapCandidateCorrectionRequestV7, RecapCandidateCorrectionRequestV8,
        RecapCandidateCorrectionRequestV9,
    )
    from apps.live_control_server.services.recap_semantic_candidate_correction import (
        inherited_pc_proof_digest, inherited_pc_reference_proof,
        verify_inherited_pc_native_basis,
    )

    parent, _, runs, body, context = _pc_reference_fixture(monkeypatch, tmp_path)
    first = service.correct_recap_candidate(RecapCandidateCorrectionRequestV9.model_validate(body))
    v9 = runs[first.run_id]
    assert v9.lineage["semantic_disposition"]["state"] == "held"
    common = {"parent_run_id": v9.run_id,
              "parent_candidate_sha256": v9.components["candidate_graph"].sha256.removeprefix("sha256:"),
              "source_revision_sha256": body["source_revision_sha256"],
              "span_index_sha256": body["span_index_sha256"],
              "profile_id": body["profile_id"]}
    v7_body = {"schema": "dmb_recap_candidate_correction_request_v7", **common,
               "node_description_replacements": [{"node_id": "mira",
                   "original_description": "Mira carried an uncertain object.",
                   "replacement_description": "Mira carried a key."}]}
    second = service.correct_recap_candidate(RecapCandidateCorrectionRequestV7.model_validate(v7_body))
    v7 = runs[second.run_id]
    proof7 = inherited_pc_reference_proof(v7, tmp_path)
    assert proof7 == v7.lineage["inherited_pc_proof"]
    assert proof7["rows"][0]["origin_run_id"] == v9.run_id
    assessment7 = assess_recap_semantics(v7, parent=v9, source_revision_id=body["source_revision_sha256"], root=tmp_path)
    basis7 = RecapSemanticBasisV12.model_validate(assessment7.basis, strict=True)
    assert basis7.operation_basis.inherited_pc_proof_sha256 == inherited_pc_proof_digest(proof7)
    legacy_fields = basis7.operation_basis.model_dump(mode="json", by_alias=True)
    legacy_fields["inherited_pc_proof_sha256"] = None
    legacy_basis = RecapSemanticBasisV8.model_validate(legacy_fields)
    legacy_bytes = json.dumps({key: value for key, value in legacy_fields.items() if value is not None},
                              sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    assert legacy_basis.digest() == hashlib.sha256(legacy_bytes).hexdigest()
    _assert_recap_semantic_basis(v7, v9, basis7, get_ancestor=runs.get)
    v8_body = {"schema": "dmb_recap_candidate_correction_request_v8",
               **{**common, "parent_run_id": v7.run_id,
                  "parent_candidate_sha256": v7.components["candidate_graph"].sha256.removeprefix("sha256:")},
               "expected_parent_revision": v7.revision,
               "node_description_replacements": [{"node_id": "mira",
                   "original_description": "Mira carried a key.",
                   "replacement_description": "Mira carried the bridge key."}]}
    third = service.correct_recap_candidate(RecapCandidateCorrectionRequestV8.model_validate(v8_body))
    v8 = runs[third.run_id]
    proof8 = inherited_pc_reference_proof(v8, tmp_path)
    assert proof8 == v8.lineage["inherited_pc_proof"]
    assessment8 = assess_recap_semantics(v8, parent=v7, source_revision_id=body["source_revision_sha256"], root=tmp_path)
    basis8 = RecapSemanticBasisV12.model_validate(assessment8.basis, strict=True)
    assert basis8.operation_basis.inherited_pc_proof_sha256 == inherited_pc_proof_digest(proof8)
    _assert_recap_semantic_basis(v8, v7, basis8, get_ancestor=runs.get)
    monkeypatch.setattr(extract_promote, "_artifact_root", lambda: tmp_path)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, run_id: runs[run_id])
    original_resolve = extract_promote.resolve_promotable_ingest_run
    def review_resolve(run_id, **kwargs):
        value = original_resolve(run_id, **kwargs)
        value.session_id = "session-28"
        value.status = "reviewable"
        value.diagnostics = []
        return value
    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", review_resolve)
    package = extract_promote.get_exact_run_review_package(v8.run_id)
    assert package.inherited_pc_references is not None
    assert package.inherited_pc_references.rows[0].origin_run_id == v9.run_id
    assert package.inherited_pc_references.proof_sha256 == inherited_pc_proof_digest(proof8)
    assert package.inherited_pc_references.final_candidate_sha256 == basis8.operation_basis.candidate_sha256
    assert package.inherited_pc_references.run_revision == v8.revision
    assert package.inherited_pc_references.semantic_basis_sha256 == assessment8.basis_sha256
    final = json.loads((_candidate_path(tmp_path, v8)).read_bytes())
    assert verify_inherited_pc_native_basis(final, proof8, context)
    from dataclasses import replace
    from apps.live_control_server.models.world_graph_mutation_context import MutationObject
    assert not verify_inherited_pc_native_basis(
        final, proof8, replace(context, world_id="another-world"))
    assert not verify_inherited_pc_native_basis(
        final, proof8, replace(context, objects={"pc:mira": MutationObject(
            object_id="pc:mira", label="Mira", kind="npc",
            canon_state="canonical", memory_state="active")}))
    changed = copy.deepcopy(v8.lineage)
    changed["inherited_pc_proof"]["rows"][0]["anchor_quote"] = "forged"
    altered = v8.model_copy(update={"lineage": changed})
    assert assess_recap_semantics(altered, parent=v7,
                                  source_revision_id=body["source_revision_sha256"], root=tmp_path).basis is None
    with pytest.raises(ApplicationStateConflictError, match="inherited PC proof"):
        _assert_recap_semantic_basis(altered, v7, basis8, get_ancestor=runs.get)
    old = v8.model_copy(update={"lineage": {key: value for key, value in v8.lineage.items()
                                               if key != "inherited_pc_proof"}})
    assert assess_recap_semantics(old, parent=v7,
                                  source_revision_id=body["source_revision_sha256"], root=tmp_path).basis is None
    with pytest.raises(ApplicationStateConflictError, match="inherited PC proof"):
        _assert_recap_semantic_basis(old, v7, basis8, get_ancestor=runs.get)

    # Exercise the real decision function and APP-STATE CAS over synthetic rows.
    from contextlib import contextmanager
    from application_state.ingest import service as ingest_service
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes
    from apps.live_control_server.services.managed_world_graph_projection import VerifiedManagedWorldBinding
    from apps.live_control_server.services import candidate_graph_admission
    from graph_memory.extract_promote_ops import ExtractPromotePrepareResult

    monkeypatch.setattr(graph_run_registry, "get_reviewable_extraction_run",
                        lambda _root, run_id: runs[run_id])
    monkeypatch.setattr(ingest_service, "load_runtime_dsn", lambda: "synthetic")
    monkeypatch.setattr(ingest_service, "assert_at_head", lambda **_: None)
    @contextmanager
    def fake_uow(_dsn):
        yield object()
    monkeypatch.setattr(ingest_service, "unit_of_work", fake_uow)
    monkeypatch.setattr(ingest_service.repo, "lock_run", lambda _conn, run_id: runs.get(run_id))
    monkeypatch.setattr(ingest_service.repo, "get_run", lambda _conn, run_id: runs.get(run_id))
    def cas(_conn, *, run_id, expected_revision, lineage):
        current = runs[run_id]
        if current.revision != expected_revision:
            return None
        updated = current.model_copy(update={"revision": expected_revision + 1, "lineage": lineage})
        runs[run_id] = updated
        return updated
    monkeypatch.setattr(ingest_service.repo, "cas_update_run_lineage", cas)
    receipt = extract_promote.decide_recap_semantic_disposition(
        v8.run_id,
        RecapSemanticDecisionRequest(expected_revision=v8.revision,
            candidate_sha256=basis8.operation_basis.candidate_sha256, decision="accepted",
            review_decision_ref="decision:final-v8"),
        reviewer_id="gm",
    )
    assert receipt.state == "accepted" and receipt.basis_sha256 == assessment8.basis_sha256
    post_decision_assessment = assess_recap_semantics(
        runs[v8.run_id], parent=v7, source_revision_id=body["source_revision_sha256"],
        root=tmp_path,
    )
    assert post_decision_assessment.accepted, (
        post_decision_assessment.reason, post_decision_assessment.basis,
    )
    with pytest.raises(extract_promote.ExtractPromoteError, match="conflicts"):
        extract_promote.decide_recap_semantic_disposition(
            v8.run_id,
            RecapSemanticDecisionRequest(expected_revision=v8.revision,
                candidate_sha256=basis8.operation_basis.candidate_sha256, decision="accepted",
                review_decision_ref="decision:stale-conflict"),
            reviewer_id="gm",
        )
    assert runs[v9.run_id].lineage["semantic_disposition"]["state"] == "held"
    assert runs[v7.run_id].lineage["semantic_disposition"]["state"] == "held"
    accepted = runs[v8.run_id]
    accepted_assessment = assess_recap_semantics(
        accepted, parent=v7, source_revision_id=body["source_revision_sha256"], root=tmp_path)
    assert accepted_assessment.accepted
    binding = accepted_effect_binding(accepted, accepted_assessment)
    assert binding["inherited_pc_proof_sha256"] == inherited_pc_proof_digest(proof8)

    target = VerifiedManagedWorldBinding(
        managed_world_id="managed", native_world_id="invented-world",
        binding_version=1, source_root_relpath="corpus/invented")
    monkeypatch.setattr(extract_promote, "_resolve_publication_target", lambda _: target)
    monkeypatch.setattr(extract_promote, "_candidate_owner_for_locator", lambda _: runs[v8.run_id])
    monkeypatch.setattr(extract_promote, "_require_canonical_source_artifact",
                        lambda _: SimpleNamespace(world_id="invented-world"))
    monkeypatch.setattr(extract_promote, "assert_sealed_source_uri_allowed", lambda _: None)
    original_review_resolve = extract_promote.resolve_promotable_ingest_run
    def publication_resolve(run_id, **kwargs):
        value = original_review_resolve(run_id, **kwargs)
        value.sealed_source_uri = str(tmp_path / "source.md")
        value.registry_context_graph_path = None
        value.world_id = "invented-world"
        value.ingest_context = None
        return value
    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", publication_resolve)
    monkeypatch.setattr(world_graph_writes, "bind_identity_ledger_to_package", lambda package, _: package)
    def admission(**kwargs):
        effect = {"world_id": "invented-world", "parent_revision_id": "rev:head"}
        return ExtractPromotePrepareResult(
            review_package={"effect": effect, "proposal_digest": "initial"},
            proposal_id="synthetic", proposal_digest="initial",
            parent_revision_id="rev:head", world_id="invented-world",
            accepted_proposals_count=0, unresolved_mentions_count=0,
            rejected_assertions_count=0, confirmable=False,
        )
    monkeypatch.setattr(candidate_graph_admission, "prepare_candidate_graph_admission", admission)
    prepared = extract_promote.prepare(ExtractPromotePrepareRequest(
        run_id=v8.run_id, managed_world_id="managed"))
    assert prepared.review_package["effect"][EFFECT_KEY] == binding
    locator = str(_candidate_path(tmp_path, accepted))
    extract_promote._assert_recap_semantics_at_confirm(locator, prepared.review_package)
    from dataclasses import replace
    from apps.live_control_server.models.world_graph_mutation_context import MutationObject
    stale_target = replace(context, objects={"pc:mira": MutationObject(
        object_id="pc:mira", label="Mira", kind="npc",
        canon_state="canonical", memory_state="active")})
    monkeypatch.setattr(world_graph_writes, "load_production_mutation_context",
                        lambda _: stale_target)
    with pytest.raises(extract_promote.ExtractPromoteError, match="native target"):
        extract_promote.prepare(ExtractPromotePrepareRequest(
            run_id=v8.run_id, managed_world_id="managed"))
    with pytest.raises(extract_promote.ExtractPromoteError, match="native target"):
        extract_promote._assert_recap_semantics_at_confirm(locator, prepared.review_package)
    monkeypatch.setattr(world_graph_writes, "load_production_mutation_context", lambda _: context)

    # Each forged frozen link must fail at the accepted-effect confirm boundary.
    origin = runs[v9.run_id]
    for mutation in ("tuple", "quote", "manifest", "missing_intro", "forged_intro", "source", "index", "cycle"):
        altered_origin = origin.model_copy(deep=True)
        if mutation == "tuple":
            altered_origin.lineage["semantic_candidate_manifest"]["attachments"][0]["corpus_ref"]["ref_id"] = "other"
        elif mutation == "quote":
            altered_origin.lineage["semantic_candidate_manifest"]["attachments"][0]["anchor_quote"] = "forged quote"
        elif mutation == "manifest":
            altered_origin.lineage["semantic_candidate_manifest"]["world_id"] = "foreign-world"
        elif mutation == "missing_intro":
            altered_origin.lineage["semantic_candidate_manifest"]["attachments"] = []
        elif mutation == "forged_intro":
            altered_origin.lineage["semantic_candidate_manifest"]["attachments"][0]["node_id"] = "forged-node"
        elif mutation in {"source", "index"}:
            key = "source_artifact" if mutation == "source" else "source_span_index"
            altered_origin.components[key] = altered_origin.components[key].model_copy(
                update={"sha256": "0" * 64})
        else:
            altered_origin.lineage["parent_run_id"] = origin.run_id
        runs[origin.run_id] = altered_origin
        with pytest.raises(extract_promote.ExtractPromoteError):
            extract_promote._assert_recap_semantics_at_confirm(locator, prepared.review_package)
        runs[origin.run_id] = origin

    original_bytes = (_candidate_path(tmp_path, accepted)).read_bytes()
    altered_candidate = json.loads(original_bytes)
    altered_candidate["nodes"][0]["corpus_ref"]["ref_id"] = "other"
    (_candidate_path(tmp_path, accepted)).write_bytes(
        service._canonical_bytes(altered_candidate))
    with pytest.raises(extract_promote.ExtractPromoteError):
        extract_promote._assert_recap_semantics_at_confirm(locator, prepared.review_package)
    (_candidate_path(tmp_path, accepted)).write_bytes(original_bytes)


def test_pc_reference_child_is_held_replayable_and_only_changes_refs(monkeypatch, tmp_path):
    from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV9

    parent, raw, runs, body, _ = _pc_reference_fixture(monkeypatch, tmp_path)
    result = service.correct_recap_candidate(RecapCandidateCorrectionRequestV9.model_validate(body))
    child = runs[result.run_id]
    assert result.schema_ == "dmb_recap_candidate_correction_response_v9"
    assert result.semantic_state == "held" and len(runs) == 2
    candidate = json.loads((_candidate_path(tmp_path, child)).read_bytes())
    original = json.loads(raw)
    assert candidate["nodes"][0].pop("corpus_ref") == body["attachments"][0]["corpus_ref"]
    assert original["nodes"][0].pop("corpus_ref") is None
    assert candidate == original
    assert service.verify_child_replay(child, parent, tmp_path)
    assessment = assess_recap_semantics(child, parent=parent,
                                        source_revision_id=body["source_revision_sha256"], root=tmp_path)
    basis = RecapSemanticBasisV12.model_validate(assessment.basis, strict=True)
    assert basis.digest() == result.semantic_basis_sha256 and not assessment.accepted
    _assert_recap_semantic_basis(child, parent, basis)
    with pytest.raises(ApplicationStateConflictError, match="parent revision"):
        _assert_recap_semantic_basis(child, parent.model_copy(update={"revision": 6}), basis)
    tampered = child.model_copy(update={"lineage": copy.deepcopy(child.lineage)})
    tampered.lineage["semantic_candidate_manifest"]["attachments"][0]["anchor_quote"] = "invented"
    with pytest.raises(ApplicationStateConflictError, match="PC reference manifest changed"):
        _assert_recap_semantic_basis(tampered, parent, basis)


def test_pc_reference_http_route_accepts_only_typed_held_child(monkeypatch, tmp_path):
    _, _, runs, body, _ = _pc_reference_fixture(monkeypatch, tmp_path)
    app = _split_http_app(monkeypatch)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url="http://test") as client:
            url = "/api/live/extract-promote/runs/parent/recap-candidate-corrections"
            response = await client.post(url, json=body)
            assert response.status_code == 200, response.text
            assert response.json()["schema"] == "dmb_recap_candidate_correction_response_v9"
            assert response.json()["semanticState"] == "held"
            retry = await client.post(url, json=body)
            assert retry.json() == response.json()
            return response.json()
    response = asyncio.run(exercise())
    assert len(runs) == 2 and response["runId"] in runs


@pytest.mark.parametrize("bad", ["registry", "alternate_registry", "roster", "source", "parent",
                                 "world", "head", "kind", "redirect", "duplicate", "ref",
                                 "actor", "wrong_pc_quote", "wrong_pc_mention", "preimage"])
def test_pc_reference_invalid_basis_creates_no_child(monkeypatch, tmp_path, bad):
    from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV9
    from apps.live_control_server.models.world_graph_mutation_context import MutationObject
    from dataclasses import replace
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes

    parent, raw, runs, body, context = _pc_reference_fixture(
        monkeypatch, tmp_path,
        source_text=("Ari found the key under the bridge.\n" if bad == "wrong_pc_quote"
                     else "Ari met Mira at the bridge.\n" if bad == "wrong_pc_mention"
                     else "Mira found the key under the bridge.\n"))
    if bad == "registry":
        body["registry_sha256"] = "0" * 64
    elif bad == "alternate_registry":
        alternate = tmp_path / "corpus/other/_party_registry.json"
        alternate.parent.mkdir(parents=True)
        alternate.write_bytes((tmp_path / body["registry_path"]).read_bytes())
        body["registry_path"] = "corpus/other/_party_registry.json"
    elif bad == "roster":
        body["roster_key"] = "22"
    elif bad == "source":
        body["source_revision_sha256"] = "0" * 64
    elif bad == "parent":
        body["expected_parent_revision"] = 6
    elif bad == "world":
        body["world_id"] = "foreign-world"
    elif bad == "head":
        body["expected_head_revision_id"] = "rev:stale"
    elif bad == "kind":
        context = replace(context, objects={"pc:mira": replace(context.objects["pc:mira"], kind="npc")})
    elif bad == "redirect":
        context = replace(context, identity_redirects={"pc:mira": "pc:other"})
    elif bad == "duplicate":
        context = replace(context, objects={**context.objects,
            "node:mira": MutationObject(object_id="node:mira", label="Mira",
                                        kind="player_character", canon_state="canonical")})
    elif bad == "ref":
        body["attachments"][0]["corpus_ref"]["ref_id"] = "other"
    elif bad == "actor":
        body["attachments"][0]["anchor_quote"] = "Unsupported actor quote"
    elif bad == "wrong_pc_mention":
        body["attachments"][0]["pc_mention"] = "Ari"
    elif bad == "preimage":
        original = json.loads(raw)
        original["nodes"][0]["corpus_ref"] = {"type": "pc", "ref_id": "mira", "resolution": "resolved"}
        raw = service._canonical_bytes(original)
        (tmp_path / "parent.json").write_bytes(raw)
        components = dict(parent.components)
        components["candidate_graph"] = components["candidate_graph"].model_copy(update={"sha256": _sha(raw)})
        parent = parent.model_copy(update={"components": components})
        runs["parent"] = parent
        body["parent_candidate_sha256"] = _sha(raw)
    monkeypatch.setattr(world_graph_writes, "load_production_mutation_context", lambda _: context)
    request = RecapCandidateCorrectionRequestV9.model_validate(body) if bad != "ref" else None
    before = list(runs)
    if request is None:
        with pytest.raises(ValueError):
            RecapCandidateCorrectionRequestV9.model_validate(body)
    else:
        with pytest.raises(extract_promote.ExtractPromoteError):
            service.correct_recap_candidate(request)
    assert list(runs) == before
    assert not (tmp_path / "out/graph_memory/derived_candidates").exists()


def test_pc_reference_prepare_and_confirm_reprove_current_basis(monkeypatch, tmp_path):
    from dataclasses import replace
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes
    from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV9
    from apps.live_control_server.services.managed_world_graph_projection import VerifiedManagedWorldBinding

    parent, _, runs, body, context = _pc_reference_fixture(monkeypatch, tmp_path)
    response = service.correct_recap_candidate(RecapCandidateCorrectionRequestV9.model_validate(body))
    child = runs[response.run_id]
    lineage = copy.deepcopy(child.lineage)
    lineage["semantic_disposition"] = {
        "version": 1, "state": "accepted", "basis_sha256": response.semantic_basis_sha256,
        "review_decision_ref": "decision:invented", "reviewer_id": "reviewer",
        "decided_at": "2026-10-11T00:00:00Z",
    }
    child = child.model_copy(update={"lineage": lineage})
    runs[child.run_id] = child
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, run_id: runs[run_id])
    monkeypatch.setattr(extract_promote, "repo_root", lambda: tmp_path)
    original_resolve = service.resolve_promotable_ingest_run
    def prepare_resolve(run_id, **kwargs):
        value = original_resolve(run_id, **kwargs)
        value.sealed_source_uri = str(tmp_path / "source.md")
        value.world_id = "invented-world"
        value.ingest_context = None
        value.registry_context_graph_path = None
        value.diagnostics = ["resolved via canonical ExtractionRun registry"]
        return value
    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", prepare_resolve)
    monkeypatch.setattr(extract_promote, "assert_sealed_source_uri_allowed", lambda _: None)
    monkeypatch.setattr(extract_promote, "_candidate_owner_for_locator", lambda _: child)
    monkeypatch.setattr(extract_promote, "_resolve_publication_target", lambda _: VerifiedManagedWorldBinding(
        managed_world_id="managed", native_world_id="invented-world", binding_version=1,
        source_root_relpath="corpus/invented"))
    assessment = assess_recap_semantics(child, parent=parent,
                                        source_revision_id=body["source_revision_sha256"], root=tmp_path)
    assert assessment.accepted
    mismatched = child.model_copy(update={"lineage": copy.deepcopy(child.lineage)})
    mismatched.lineage["semantic_disposition"]["reviewer_id"] = "other-reviewer"
    assert not assess_recap_semantics(
        mismatched, parent=parent, source_revision_id=body["source_revision_sha256"],
        root=tmp_path).accepted
    mismatched.lineage["semantic_disposition"]["reviewer_id"] = "reviewer"
    mismatched.lineage["semantic_disposition"]["review_decision_ref"] = "other-decision"
    assert not assess_recap_semantics(
        mismatched, parent=parent, source_revision_id=body["source_revision_sha256"],
        root=tmp_path).accepted
    binding = accepted_effect_binding(child, assessment)
    assert binding["world_id"] == "invented-world"
    assert binding["expected_head_revision_id"] == "rev:head"
    locator = str(_candidate_path(tmp_path, child))
    effect = {EFFECT_KEY: binding, "world_id": "invented-world", "parent_revision_id": "rev:head"}
    extract_promote._assert_recap_semantics_at_confirm(locator, {"effect": effect})
    with pytest.raises(extract_promote.ExtractPromoteError, match="World or parent head"):
        extract_promote._assert_recap_semantics_at_confirm(
            locator, {"effect": {**effect, "world_id": "foreign-world"}})
    with pytest.raises(extract_promote.ExtractPromoteError, match="World or parent head"):
        extract_promote._assert_recap_semantics_at_confirm(
            locator, {"effect": {**effect, "parent_revision_id": "rev:stale"}})
    stale = replace(context, revision_id="rev:new", head_revision_id="rev:new")
    monkeypatch.setattr(world_graph_writes, "load_production_mutation_context", lambda _: stale)
    with pytest.raises(extract_promote.ExtractPromoteError, match="semantic review"):
        extract_promote.prepare(ExtractPromotePrepareRequest(run_id=child.run_id,
                                                             managed_world_id="managed"))
    with pytest.raises(extract_promote.ExtractPromoteError, match="held"):
        extract_promote._assert_recap_semantics_at_confirm(locator, {"effect": effect})
    monkeypatch.setattr(world_graph_writes, "load_production_mutation_context", lambda _: context)
    registry = tmp_path / body["registry_path"]
    registry.write_text(registry.read_text() + "\n")
    with pytest.raises(extract_promote.ExtractPromoteError, match="held"):
        extract_promote._assert_recap_semantics_at_confirm(locator, {"effect": effect})


def _append_fixture(monkeypatch, root, *, actor_recovery=False, actor_prefix="", line_ending="\n"):
    """Frozen three-span recap plus a PC introduction and an existing edge."""
    from graph_memory.source_span import build_stable_source_span_id
    parent, _, runs, pc_body, context = _pc_reference_fixture(monkeypatch, root)
    first_line = (
        f"{actor_prefix}Lysandro found the key under the bridge while Mira watched."
        if actor_recovery else "Mira found the key under the bridge."
    )
    source = line_ending.join((first_line, "Mira rescued a traveler.", "Mira felt frightened.")).encode("utf-8") + line_ending.encode("utf-8")
    (root / "source.md").write_bytes(source)
    digest = _sha(source)
    _update_source_artifact_record(
        root, parent.source_artifact_id, content_sha256=digest,
    )
    old = json.loads((root / "parent.json").read_bytes())
    index = json.loads((root / "spans.json").read_bytes())
    index["content_sha256"] = digest
    index["spans"] = [{
        "source_span_id": build_stable_source_span_id(source_artifact_id=parent.source_artifact_id,
            content_sha256=digest, start_line=i, end_line=i),
        "source_artifact_id": parent.source_artifact_id, "source_ref_id": index["source_ref_id"],
        "content_sha256": digest, "start_line": i, "end_line": i,
    } for i in (1, 2, 3)]
    ref = old["nodes"][0]["evidence_refs"][0]
    ref["source_span_ref_id"] = index["spans"][0]["source_span_id"]
    if actor_recovery:
        ref["anchor_quotes"] = [first_line]
    location = copy.deepcopy(old["nodes"][0])
    location.update(node_id="bridge", node_type="location", label="Bridge")
    old["nodes"].append(location)
    old["edges"] = [{"edge_id": "edge-bridge", "from_node_id": "mira", "to_node_id": "bridge",
        "relationship_type": "located_in", "label": "found key under bridge",
        "evidence_refs": [copy.deepcopy(ref)], "semantic_state": copy.deepcopy(old["nodes"][0]["semantic_state"]),
        "confidence": "medium", "proposed_action": "create"}]
    raw = service._canonical_bytes(old)
    span_bytes = service._canonical_bytes(index)
    (root / "parent.json").write_bytes(raw)
    (root / "spans.json").write_bytes(span_bytes)
    components = dict(parent.components)
    for key, content in (("source_artifact", source), ("source_span_index", span_bytes), ("candidate_graph", raw)):
        components[key] = components[key].model_copy(update={"sha256": _sha(content)})
    parent = parent.model_copy(update={"components": components})
    runs[parent.run_id] = parent
    pc_body.update(parent_candidate_sha256=_sha(raw), source_revision_sha256=digest,
                   span_index_sha256=_sha(span_bytes))
    pc_body["attachments"][0]["source_span_ref_id"] = index["spans"][0]["source_span_id"]
    monkeypatch.setattr(service, "_load_frozen_span_index_for_resolved_run",
        lambda _: SimpleNamespace(spans=[SimpleNamespace(**s) for s in index["spans"]]))
    return parent, raw, runs, pc_body, context, index


def _append_request(parent, payload, index, *, kind="node", identifier="mira", line=2):
    collection, key = ("nodes", "node_id") if kind == "node" else ("edges", "edge_id")
    record = next(x for x in payload[collection] if x[key] == identifier)
    return {"schema": "dmb_recap_candidate_correction_request_v10", "parent_run_id": parent.run_id,
        "expected_parent_revision": parent.revision,
        "parent_candidate_sha256": parent.components["candidate_graph"].sha256.removeprefix("sha256:"),
        "source_revision_sha256": parent.components["source_artifact"].sha256.removeprefix("sha256:"),
        "span_index_sha256": parent.components["source_span_index"].sha256.removeprefix("sha256:"),
        "profile_id": service.PROFILE,
        "evidence_appends": [{"record_kind": kind, "record_id": identifier,
            "expected_evidence_refs_sha256": _sha(service._canonical_bytes(record["evidence_refs"])),
            "source_span_ref_id": index["spans"][line - 1]["source_span_id"],
            "anchor_quotes": ["Mira rescued a traveler." if line == 2 else "Mira felt frightened."]}]}


def test_append_replay_preserves_existing_citations_and_rejects_forged_authority(monkeypatch, tmp_path):
    from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV10
    from pydantic import ValidationError
    parent, raw, _, _, _, index = _append_fixture(monkeypatch, tmp_path)
    payload = json.loads(raw)
    body = _append_request(parent, payload, index)
    req = RecapCandidateCorrectionRequestV10.model_validate(body)
    manifest = req.model_dump(mode="json", exclude={"schema_", "parent_run_id", "parent_candidate_sha256"})
    manifest["schema"] = service.MANIFEST_SCHEMA_V10
    child = service.replay_candidate(payload, manifest, source_bytes=(tmp_path / "source.md").read_bytes(),
                                     span_bytes=(tmp_path / "spans.json").read_bytes())
    assert child["nodes"][0]["evidence_refs"][:-1] == payload["nodes"][0]["evidence_refs"]
    assert service._canonical_bytes(child["nodes"][0]["evidence_refs"][:-1]) == service._canonical_bytes(payload["nodes"][0]["evidence_refs"])
    assert child["nodes"][1:] == payload["nodes"][1:] and child["edges"] == payload["edges"]
    appended = child["nodes"][0]["evidence_refs"][-1]
    assert appended["source_anchor_id"] == "anchor:" + body["evidence_appends"][0]["source_span_ref_id"]
    forged = copy.deepcopy(body)
    forged["evidence_appends"][0]["source_artifact_id"] = "client-authority"
    with pytest.raises(ValidationError):
        RecapCandidateCorrectionRequestV10.model_validate(forged)
    duplicated = copy.deepcopy(body)
    duplicated["evidence_appends"] *= 2
    with pytest.raises(ValidationError):
        RecapCandidateCorrectionRequestV10.model_validate(duplicated)


def test_http_append_child_preserves_pc_proof_and_retry_identity(monkeypatch, tmp_path):
    from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV9
    parent, raw, runs, pc_body, _, index = _append_fixture(monkeypatch, tmp_path)
    introduced = service.correct_recap_candidate(RecapCandidateCorrectionRequestV9.model_validate(pc_body))
    pc_parent = runs[introduced.run_id]
    pc_bytes = (_candidate_path(tmp_path, pc_parent)).read_bytes()
    pc_payload = json.loads(pc_bytes)
    body = _append_request(pc_parent, pc_payload, index)
    edge_body = _append_request(pc_parent, pc_payload, index, kind="edge", identifier="edge-bridge", line=3)
    body["evidence_appends"].extend(edge_body["evidence_appends"])
    body["node_description_replacements"] = [{"node_id": "mira",
        "original_description": pc_payload["nodes"][0]["description"],
        "replacement_description": "Mira found a key and rescued a traveler."}]
    app = _split_http_app(monkeypatch)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            first = await client.post(f"/api/live/extract-promote/runs/{pc_parent.run_id}/recap-candidate-corrections", json=body)
            assert first.status_code == 200, first.text
            reverse = copy.deepcopy(body)
            reverse["evidence_appends"].reverse()
            second = await client.post(f"/api/live/extract-promote/runs/{pc_parent.run_id}/recap-candidate-corrections", json=reverse)
            assert second.status_code == 200 and second.json() == first.json()
            return first.json()
    response = asyncio.run(exercise())
    assert response["schema"] == "dmb_recap_candidate_correction_response_v10"
    assert response["semanticState"] == "held" and len(runs) == 3
    child = runs[response["runId"]]
    value = json.loads((_candidate_path(tmp_path, child)).read_bytes())
    for collection in ("nodes", "edges"):
        assert value[collection][0]["evidence_refs"][:-1] == pc_payload[collection][0]["evidence_refs"]
    assert value["nodes"][0]["corpus_ref"] == pc_payload["nodes"][0]["corpus_ref"]
    proof = service.inherited_pc_reference_proof(child, tmp_path)
    assert proof == child.lineage["inherited_pc_proof"]
    assert proof["rows"][0]["origin_run_id"] == pc_parent.run_id
    assert service.verify_child_replay(child, pc_parent, tmp_path)
    assessment = assess_recap_semantics(child, parent=pc_parent,
        source_revision_id=body["source_revision_sha256"], root=tmp_path)
    assert assessment.marked and not assessment.accepted
    basis = RecapSemanticBasisV12.model_validate(assessment.basis, strict=True)
    assert basis.digest() == response["semanticBasisSha256"]
    _assert_recap_semantic_basis(child, pc_parent, basis, get_ancestor=runs.get)
    monkeypatch.setattr(extract_promote, "_artifact_root", lambda: tmp_path)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, run_id: runs[run_id])
    original_resolve = service.resolve_promotable_ingest_run
    def review_resolve(run_id, **kwargs):
        value = original_resolve(run_id, **kwargs)
        value.status = "reviewable"
        value.diagnostics = []
        return value
    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", review_resolve)
    package = extract_promote.get_exact_run_review_package(child.run_id)
    assert package.inherited_pc_references is not None
    assert package.inherited_pc_references.rows[0].origin_run_id == pc_parent.run_id
    assert package.inherited_pc_references.proof_sha256 == basis.operation_basis.inherited_pc_proof_sha256
    assert (_candidate_path(tmp_path, pc_parent)).read_bytes() == pc_bytes
    assert (tmp_path / "parent.json").read_bytes() == raw
    drifted = child.model_copy(deep=True)
    drifted.lineage["inherited_pc_proof"]["rows"][0]["corpus_ref"]["ref_id"] = "foreign"
    with pytest.raises(ApplicationStateConflictError):
        _assert_recap_semantic_basis(drifted, pc_parent, basis, get_ancestor=runs.get)


@pytest.mark.parametrize("fault", ["parent_revision", "parent_digest", "source", "span", "quote", "unknown_target", "existing_span", "array_preimage", "bad_last_append"])
def test_append_service_rejects_atomically_before_child(monkeypatch, tmp_path, fault):
    from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV10
    parent, raw, runs, _, _, index = _append_fixture(monkeypatch, tmp_path)
    body = _append_request(parent, json.loads(raw), index)
    if fault == "parent_revision":
        body["expected_parent_revision"] += 1
    elif fault == "parent_digest":
        body["parent_candidate_sha256"] = "0" * 64
    elif fault == "source":
        body["source_revision_sha256"] = "0" * 64
    elif fault == "span":
        body["span_index_sha256"] = "0" * 64
    elif fault == "quote":
        body["evidence_appends"][0]["anchor_quotes"] = ["Mira rescued a dragon."]
    elif fault == "unknown_target":
        body["evidence_appends"][0]["record_id"] = "unknown"
    elif fault == "existing_span":
        body["evidence_appends"][0].update(source_span_ref_id=index["spans"][0]["source_span_id"], anchor_quotes=["Mira found the key under the bridge."])
    elif fault == "array_preimage":
        body["evidence_appends"][0]["expected_evidence_refs_sha256"] = "0" * 64
    elif fault == "bad_last_append":
        second = copy.deepcopy(body["evidence_appends"][0])
        second.update(source_span_ref_id=index["spans"][2]["source_span_id"], anchor_quotes=["not literal"])
        body["evidence_appends"].append(second)
    with pytest.raises(service.ExtractPromoteError):
        service.correct_recap_candidate(RecapCandidateCorrectionRequestV10.model_validate(body))
    assert len(runs) == 1 and not (tmp_path / "out/graph_memory/derived_candidates").exists()
    assert (tmp_path / "parent.json").read_bytes() == raw


def test_append_decision_dispatch_uses_distinct_basis_and_stays_guarded(monkeypatch, tmp_path):
    from application_state.ingest import service as ingest_service
    from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV10
    parent, raw, runs, _, _, index = _append_fixture(monkeypatch, tmp_path)
    body = _append_request(parent, json.loads(raw), index)
    response = service.correct_recap_candidate(RecapCandidateCorrectionRequestV10.model_validate(body))
    child = runs[response.run_id]
    monkeypatch.setattr(extract_promote, "_artifact_root", lambda: tmp_path)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, run_id: runs[run_id])
    monkeypatch.setattr(graph_run_registry, "get_reviewable_extraction_run", lambda _root, run_id: runs[run_id])
    seen = []
    def record(run_id, *, expected_revision, basis, decision):
        assert isinstance(basis, ingest_service.RecapSemanticBasisV12)
        assert isinstance(basis.operation_basis, ingest_service.RecapSemanticBasisV11)
        _assert_recap_semantic_basis(child, parent, basis, get_ancestor=runs.get)
        seen.append((run_id, expected_revision, basis.digest()))
        decided = child.model_copy(deep=True, update={"revision": expected_revision + 1})
        decided.lineage["semantic_disposition"] = {"version": 1, "state": decision.state,
            "basis_sha256": basis.digest(), "review_decision_ref": decision.review_decision_ref,
            "reviewer_id": decision.reviewer_id, "decided_at": "2026-10-12T00:00:00Z",
            "from_revision": expected_revision}
        return decided
    monkeypatch.setattr(ingest_service, "record_recap_semantic_disposition", record)
    receipt = extract_promote.decide_recap_semantic_disposition(child.run_id,
        RecapSemanticDecisionRequest(expected_revision=child.revision,
            candidate_sha256=response.candidate_sha256, decision="rejected",
            review_decision_ref="synthetic:append-review"), reviewer_id="gm")
    assert receipt.state == "rejected"
    assert seen == [(child.run_id, child.revision, response.semantic_basis_sha256)]
    assert child.lineage["semantic_disposition"]["state"] == "held"
    from pydantic import ValidationError
    for count in (0, 3):
        bounded = copy.deepcopy(body)
        bounded["evidence_appends"] *= count
        with pytest.raises(ValidationError):
            RecapCandidateCorrectionRequestV10.model_validate(bounded)


def _actor_recovery_request(
    parent, payload, index, source_text, *, action="retarget", edge_id="edge-bridge",
):
    from apps.live_control_server.services.recap_semantic_candidate_correction import _canonical_bytes

    edge = next(row for row in payload["edges"] if row["edge_id"] == edge_id)
    span_id = index["spans"][0]["source_span_id"]
    name = "Lysandro"
    name_start = source_text.index(name)
    return {
        "schema": "dmb_recap_candidate_correction_request_v11",
        "parent_run_id": parent.run_id,
        "expected_parent_revision": parent.revision,
        "parent_candidate_sha256": parent.components["candidate_graph"].sha256.removeprefix("sha256:"),
        "source_revision_sha256": parent.components["source_artifact"].sha256.removeprefix("sha256:"),
        "span_index_sha256": parent.components["source_span_index"].sha256.removeprefix("sha256:"),
        "profile_id": service.PROFILE,
        "misbound_actor_id": "mira",
        "actor_introduction": {
            "literal_name": name,
            "source_span_ref_id": span_id,
            "name_start": name_start,
            "name_end": name_start + len(name),
            "replacement_description": "Lysandro found the key under the bridge.",
            "description_anchor_quotes": ["Lysandro found the key under the bridge"],
        },
        "affected_edges": [{
            "action": action,
            "edge_id": edge["edge_id"],
            "expected_edge_sha256": _sha(_canonical_bytes(edge)),
            "expected_evidence_refs_sha256": _sha(_canonical_bytes(edge["evidence_refs"])),
            "original_from_id": edge["from_node_id"],
            "original_to_id": edge["to_node_id"],
            "original_predicate": edge["relationship_type"],
            "misbound_endpoint": "from_id",
            "source_span_ref_id": span_id,
            "actor_anchor_quotes": [source_text.splitlines()[0]],
        }],
    }


def test_source_supported_actor_recovery_creates_held_child_and_replays(monkeypatch, tmp_path):
    from apps.live_control_server.models.extract_promote import (
        RecapCandidateCorrectionRequestV11, RecapCandidateCorrectionResponseV11,
    )
    from application_state.ingest import service as ingest_service

    parent, raw, runs, _, _, index = _append_fixture(monkeypatch, tmp_path, actor_recovery=True)
    source_text = (tmp_path / "source.md").read_text(encoding="utf-8")
    request_body = _actor_recovery_request(parent, json.loads(raw), index, source_text)
    request = RecapCandidateCorrectionRequestV11.model_validate(request_body, strict=True)
    app = _split_http_app(monkeypatch)

    async def submit():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test",
        ) as client:
            url = f"/api/live/extract-promote/runs/{parent.run_id}/recap-candidate-corrections"
            first = await client.post(url, json=request_body)
            assert first.status_code == 200, first.text
            second = await client.post(url, json=request_body)
            assert second.status_code == 200 and second.json() == first.json()
            return first.json()

    response = RecapCandidateCorrectionResponseV11.model_validate(asyncio.run(submit()))

    assert isinstance(response, RecapCandidateCorrectionResponseV11)
    assert (response.introduced_actor_count, response.retargeted_edge_count,
            response.omitted_edge_count) == (1, 1, 0)
    child = runs[response.run_id]
    payload = json.loads(_candidate_path(tmp_path, child).read_bytes())
    actor = payload["nodes"][-1]
    assert actor["node_id"].startswith("node:recovered-actor:")
    assert actor["label"] == "Lysandro" and actor["corpus_ref"] is None
    assert actor["semantic_state"]["visibility_state"] == "gm_private"
    assert payload["edges"][0]["from_node_id"] == actor["node_id"]
    assert payload["edges"][0]["to_node_id"] == "bridge"
    assert payload["edges"][0]["evidence_refs"] == json.loads(raw)["edges"][0]["evidence_refs"]
    assert child.lineage["semantic_disposition"]["state"] == "held"
    assert service.verify_child_replay(child, parent, tmp_path)
    assessment = assess_recap_semantics(
        child, parent=parent, source_revision_id=request.source_revision_sha256, root=tmp_path,
    )
    assert assessment.marked and not assessment.accepted, assessment
    assert assessment.basis is not None, assessment
    basis = ingest_service.RecapSemanticBasisV12.model_validate(assessment.basis, strict=True)
    assert basis.request_version == 11
    assert isinstance(basis.operation_basis, ingest_service.RecapSemanticBasisV13)
    assert basis.digest() == response.semantic_basis_sha256

    monkeypatch.setattr(extract_promote, "_artifact_root", lambda: tmp_path)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, run_id: runs[run_id])
    original_resolve = service.resolve_promotable_ingest_run

    def review_resolve(run_id, **kwargs):
        resolved = original_resolve(run_id, **kwargs)
        resolved.status = "reviewable"
        resolved.diagnostics = []
        return resolved

    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", review_resolve)
    package = extract_promote.get_exact_run_review_package(child.run_id)
    assert any(assertion.label == "Lysandro" for assertion in package.assertions)
    assert package.semantic_disposition and package.semantic_disposition["state"] == "held"


@pytest.mark.parametrize("fault", [
    "unknown_quote", "stale_edge", "duplicate_actor_name", "partial_name",
    "omitted_dependent",
])
def test_source_supported_actor_recovery_rejects_invalid_edits_atomically(
    monkeypatch, tmp_path, fault,
):
    from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV11

    parent, raw, runs, _, _, index = _append_fixture(monkeypatch, tmp_path, actor_recovery=True)
    source_text = (tmp_path / "source.md").read_text(encoding="utf-8")
    body = _actor_recovery_request(parent, json.loads(raw), index, source_text)
    if fault == "unknown_quote":
        body["actor_introduction"]["description_anchor_quotes"] = ["Lysandro rescued everyone"]
    elif fault == "stale_edge":
        body["affected_edges"][0]["expected_edge_sha256"] = "0" * 64
    elif fault == "duplicate_actor_name":
        payload = json.loads(raw)
        duplicate = copy.deepcopy(payload["nodes"][0])
        duplicate.update(node_id="lysandro-old", label="Lysandro")
        payload["nodes"].append(duplicate)
        (tmp_path / "parent.json").write_bytes(service._canonical_bytes(payload))
        revised = _sha(service._canonical_bytes(payload))
        components = dict(parent.components)
        components["candidate_graph"] = components["candidate_graph"].model_copy(update={"sha256": revised})
        parent = parent.model_copy(update={"components": components})
        runs["parent"] = parent
        body["parent_candidate_sha256"] = revised
    elif fault == "partial_name":
        body["actor_introduction"]["name_start"] += 1
        body["actor_introduction"]["name_end"] += 1
    elif fault == "omitted_dependent":
        payload = json.loads(raw)
        payload["beats"] = [{"related_edge_id": "edge-bridge"}]
        revised_bytes = service._canonical_bytes(payload)
        (tmp_path / "parent.json").write_bytes(revised_bytes)
        revised = _sha(revised_bytes)
        components = dict(parent.components)
        components["candidate_graph"] = components["candidate_graph"].model_copy(
            update={"sha256": revised},
        )
        parent = parent.model_copy(update={"components": components})
        runs["parent"] = parent
        body["parent_candidate_sha256"] = revised
        body["affected_edges"][0]["action"] = "omit"
    request = RecapCandidateCorrectionRequestV11.model_validate(body, strict=True)
    with pytest.raises(service.ExtractPromoteError):
        service.correct_recap_candidate(request)
    assert len(runs) == 1
    assert not (tmp_path / "out/graph_memory/derived_candidates").exists()


def test_source_supported_actor_offsets_use_codepoints_with_crlf(monkeypatch, tmp_path):
    from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV11

    parent, raw, runs, _, _, index = _append_fixture(
        monkeypatch, tmp_path, actor_recovery=True, actor_prefix="🐉 ", line_ending="\r\n",
    )
    source_bytes = (tmp_path / "source.md").read_bytes()
    source_text = source_bytes.decode("utf-8")
    body = _actor_recovery_request(parent, json.loads(raw), index, source_text)
    start = body["actor_introduction"]["name_start"]
    assert source_text[start:start + len("Lysandro")] == "Lysandro"
    assert len(source_text[:start].encode("utf-8")) > start
    request = RecapCandidateCorrectionRequestV11.model_validate(body, strict=True)
    response = service.correct_recap_candidate(request)
    child = runs[response.run_id]
    assert service.verify_child_replay(child, parent, tmp_path)
    assert json.loads(_candidate_path(tmp_path, child).read_bytes())["nodes"][-1]["label"] == "Lysandro"


def test_actor_source_span_bounds_multiline_crlf_index():
    from graph_memory.source_span import (
        SourceSpanIndex, SourceSpanIndexEntry, build_stable_source_span_id,
        document_source_ref_id,
    )

    source_text = "Opening\r\nLysandro appears here.\r\nClosing"
    source_bytes = source_text.encode("utf-8")
    artifact_id = "artifact:recap:multi-line-span"
    content_sha = _sha(source_bytes)
    source_ref_id = document_source_ref_id(artifact_id)
    span_id = build_stable_source_span_id(
        source_artifact_id=artifact_id, content_sha256=content_sha,
        start_line=1, end_line=2,
    )
    index = SourceSpanIndex(
        source_artifact_id=artifact_id, content_sha256=content_sha,
        source_ref_id=source_ref_id,
        spans=(SourceSpanIndexEntry(
            source_span_id=span_id, source_ref_id=source_ref_id,
            source_artifact_id=artifact_id, content_sha256=content_sha,
            start_line=1, end_line=2,
        ),),
    )
    start, end, text = service._actor_source_span(source_text, index, span_id)
    assert start == 0
    assert text == "Opening\r\nLysandro appears here."
    assert end == len(text)


def test_source_supported_actor_rejects_host_id_collision_and_caller_identity(monkeypatch, tmp_path):
    from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV11
    from pydantic import ValidationError

    parent, raw, runs, _, _, index = _append_fixture(monkeypatch, tmp_path, actor_recovery=True)
    source_text = (tmp_path / "source.md").read_text(encoding="utf-8")
    body = _actor_recovery_request(parent, json.loads(raw), index, source_text)
    request = RecapCandidateCorrectionRequestV11.model_validate(body, strict=True)
    monkeypatch.setattr(service, "_recovered_actor_node_id", lambda _request: "mira")
    with pytest.raises(service.ExtractPromoteError, match="collides"):
        service.correct_recap_candidate(request)
    assert len(runs) == 1

    injected = copy.deepcopy(body)
    injected["actor_introduction"]["corpus_ref"] = {"type": "npc", "ref_id": "native:actor"}
    with pytest.raises(ValidationError):
        RecapCandidateCorrectionRequestV11.model_validate(injected, strict=True)
