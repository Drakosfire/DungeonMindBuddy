import hashlib
from types import SimpleNamespace
from uuid import uuid4

import pytest

from apps.live_control_server.services import guest_release_evidence as evidence


def test_relationship_citation_requires_exact_native_span_and_origin(monkeypatch):
    body = "Before 🐉 clue after"
    text = "🐉 clue"
    start, end = body.index(text), body.index(text) + len(text)
    digest = hashlib.sha256(body.encode()).hexdigest()
    excerpt_id, document_id = uuid4(), uuid4()
    origin = SimpleNamespace(namespace="dungeonbuddy.workspace-document-registry", object_id=str(document_id), revision_id="registry-revision:8")
    source = SimpleNamespace(evidence_ref_ids=("ev",), origin=origin,
                             source_revision=SimpleNamespace(content_sha256=digest))
    monkeypatch.setattr(evidence, "list_admitted_native_text_sources", lambda *a, **k: SimpleNamespace(complete=True, sources=[source]))
    opened = SimpleNamespace(status="available", body_sha256=digest, body_text=body,
        span_start_byte=len(body[:start].encode()), span_end_byte=len(body[:end].encode()),
        span_sha256=hashlib.sha256(text.encode()).hexdigest())
    monkeypatch.setattr(evidence, "open_admitted_native_text", lambda *a, **k: opened)
    args = dict(edge=SimpleNamespace(evidence_ref_ids=["ev"]), evidence_id="ev",
        access=SimpleNamespace(space_id="native", revision_id="rev",
            parsed=SimpleNamespace(get_evidence=lambda _: SimpleNamespace(evidence_role="support"))),
        excerpt={"id": str(excerpt_id), "text": text},
        source_binding=(excerpt_id, document_id, 0, 0, 1, digest, start, end, 8),
        expected_native_world_id="native", expected_graph_revision="rev")
    assert evidence.verify_relationship_citation(**args) == str(excerpt_id)
    with pytest.raises(evidence.GuestReleaseEvidenceError):
        evidence.verify_relationship_citation(**{**args, "evidence_id": "other"})
    with pytest.raises(evidence.GuestReleaseEvidenceError):
        evidence.verify_relationship_citation(**{**args, "expected_graph_revision": "other"})
    origin.revision_id = "registry-revision:1"
    with pytest.raises(evidence.GuestReleaseEvidenceError):
        evidence.verify_relationship_citation(**args)
    origin.revision_id = "registry-revision:8"
    origin.object_id = str(uuid4())
    with pytest.raises(evidence.GuestReleaseEvidenceError):
        evidence.verify_relationship_citation(**args)


def test_standalone_proof_uses_fresh_core_view_and_rejects_withdrawal():
    from datetime import UTC, datetime
    from dungeonmind.application.vnext import initialize_empty_knowledge_space, publish_native_text_source_evidence
    from dungeonmind.contracts.vnext.native_source import NativeTextSourceAdmissionV1
    from dungeonmind.infrastructure.memory.vnext_sources import InMemoryNativeSourceEvidenceRepository
    from graph_memory.vnext.domain_runtime import dungeonbuddy_world_domain_contract, dungeonbuddy_dnd5e_manual_profile
    from apps.live_control_server.integrations.dungeonmind.native_registry_source import read_context

    repo = InMemoryNativeSourceEvidenceRepository()
    domain, profile = dungeonbuddy_world_domain_contract(), dungeonbuddy_dnd5e_manual_profile()
    space, doc_id = "space:release-proof", uuid4()
    now = datetime(2026, 11, 20, tzinfo=UTC)
    genesis = initialize_empty_knowledge_space(repository=repo, space_id=space, initialization_id="genesis:release-proof",
        created_at=now, domain_contract=domain, semantic_profile=profile)
    body = "A 🐉 safe clue."
    text = "🐉 safe"
    digest = hashlib.sha256(body.encode()).hexdigest()
    start, end = body.index(text), body.index(text) + len(text)
    admission = publish_native_text_source_evidence(repository=repo, domain_contract=domain, semantic_profile=profile,
        request=NativeTextSourceAdmissionV1(space_id=space, admission_id="admission:release-proof",
            expected_parent_revision_id=genesis.published_revision_id, created_at=now, body_text=body,
            expected_body_sha256=digest, source_classification="dungeonbuddy.source:worldbuilding",
            authority="primary", visibility={"kind": "public"},
            origin={"namespace": "dungeonbuddy.workspace-document-registry", "object_id": str(doc_id),
                    "revision_id": "registry-revision:4"},
            spans=[{"client_ref": "selected", "evidence_role": "support", "start_byte": len(body[:start].encode()),
                    "end_byte": len(body[:end].encode()), "expected_slice_sha256": hashlib.sha256(text.encode()).hexdigest()}]))
    graph_revision = admission.publication_receipt.published_revision_id
    evidence_id = admission.bindings[0].evidence_ref_id
    _, access, _, _ = read_context(repo, space, graph_revision, None, role="player", scope_mode="world")
    excerpt_id = uuid4()
    args = dict(evidence_id=evidence_id, excerpt={"id": str(excerpt_id), "text": text},
        source_binding=(excerpt_id, doc_id, 0, 0, 1, digest, start, end, 4),
        expected_native_world_id=space, expected_graph_revision=graph_revision)
    assert evidence.verify_source_citation(access=access, **args) == str(excerpt_id)
    repo.withdraw_native_source(space_id=space, source_artifact_id=admission.source_artifact_id,
                                source_revision_id=admission.source_revision_id)
    # A pinned view is the explicitly documented cutoff: later withdrawal is
    # observed by a newly opened view, not retroactively by the earlier view.
    assert evidence.verify_source_citation(access=access, **args) == str(excerpt_id)
    _, fresh, _, _ = read_context(repo, space, graph_revision, None, role="player", scope_mode="world")
    with pytest.raises(evidence.GuestReleaseEvidenceError):
        evidence.verify_source_citation(access=fresh, **args)
