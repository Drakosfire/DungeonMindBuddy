"""Bind an admitted native Graph evidence span to an exact release excerpt."""
from __future__ import annotations

import hashlib

from dungeonmind.application.vnext import list_admitted_native_text_sources, open_admitted_native_text


class GuestReleaseEvidenceError(ValueError):
    """Native evidence does not prove the selected release citation."""


def verify_relationship_citation(*, edge, evidence_id: str, access, excerpt: dict, source_binding: tuple,
                                 expected_native_world_id: str, expected_graph_revision: str) -> str:
    """Return a release-local excerpt ID only for the exact admitted evidence.

    The caller supplies a player-scoped access context from the same exact Graph
    revision as the edge, and the private binding produced during page selection.
    No host identity or native evidence identifier is returned to the guest.
    """
    if (access.space_id != expected_native_world_id or access.revision_id != expected_graph_revision
        or evidence_id not in edge.evidence_ref_ids):
        raise GuestReleaseEvidenceError("Evidence does not support the relationship")
    native_evidence = access.parsed.get_evidence(evidence_id)
    if native_evidence is None or native_evidence.evidence_role != "support":
        raise GuestReleaseEvidenceError("Native evidence is not supporting evidence")
    excerpt_id, document_id, _, _, _, digest, start, end, registry_revision = source_binding
    text = excerpt.get("text")
    if excerpt.get("id") != str(excerpt_id) or not isinstance(text, str):
        raise GuestReleaseEvidenceError("Release excerpt binding differs")
    catalog = list_admitted_native_text_sources(access, evidence_ref_ids=[evidence_id])
    candidates = [item for item in catalog.sources if evidence_id in item.evidence_ref_ids]
    if not catalog.complete or len(candidates) != 1:
        raise GuestReleaseEvidenceError("Native evidence is unavailable or ambiguous")
    source = candidates[0]
    origin = source.origin
    if (origin is None or origin.namespace != "dungeonbuddy.workspace-document-registry"
        or origin.object_id != str(document_id)
        or origin.revision_id != f"registry-revision:{registry_revision}"
        or source.source_revision.content_sha256 != digest):
        raise GuestReleaseEvidenceError("Native evidence is bound to a different source")
    opened = open_admitted_native_text(access, evidence_id)
    if opened.status != "available" or opened.body_sha256 != digest:
        raise GuestReleaseEvidenceError("Native evidence body is unavailable")
    body = opened.body_text
    if (not isinstance(body, str) or hashlib.sha256(body.encode("utf-8")).hexdigest() != digest
        or type(start) is not int or type(end) is not int or start < 0 or end <= start
        or end > len(body) or body[start:end] != text):
        raise GuestReleaseEvidenceError("Release excerpt differs from native source")
    byte_start = len(body[:start].encode("utf-8"))
    byte_end = len(body[:end].encode("utf-8"))
    if (opened.span_start_byte != byte_start or opened.span_end_byte != byte_end
        or opened.span_sha256 != hashlib.sha256(text.encode("utf-8")).hexdigest()):
        raise GuestReleaseEvidenceError("Release excerpt differs from admitted evidence span")
    return str(excerpt_id)
