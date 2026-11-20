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
