"""Owner-only inventory of exact fields and evidence eligible for selection.

This inventory is not an approval, a publication, or a guest-facing payload.
Preparation reopens and independently verifies every selected item.
"""
from __future__ import annotations

from uuid import UUID

from dungeonmind.application.vnext import (
    ParsedEntityRefValue, ParsedLiteralValue, ParsedTermRefValue,
    list_admitted_native_text_sources, open_admitted_native_text,
)

from application_state.content.pages import committed_page
from application_state.errors import ApplicationStateError
from apps.live_control_server.integrations.dungeonmind import native_registry_source
from apps.live_control_server.services.guest_release_assertions import GuestReleaseAssertionError, _assertion, _text
from apps.live_control_server.services.guest_release_evidence import GuestReleaseEvidenceError, verify_source_citation
from apps.live_control_server.services.guest_release_native_graph import GuestNativeGraphError, read_owner_graph
from apps.live_control_server.services.guest_release_sources import GuestReleaseSourceError, selected_page_excerpt
from apps.live_control_server.services.managed_world_graph_projection import resolve_managed_world_binding


def selection_options(*, world_id: str) -> dict:
    """Inspect the current owner Graph and return selectable exact values."""
    binding = resolve_managed_world_binding(world_id)
    repo = native_registry_source.read_repository()
    head = repo.get_head(binding.native_world_id)
    if head is None:
        raise GuestNativeGraphError("Native Graph head is unavailable")
    revision_id = head.head_revision_id
    current_binding, context, support, access = read_owner_graph(managed_world_id=world_id, revision_id=revision_id)
    if current_binding != binding:
        raise GuestNativeGraphError("Native Graph binding changed")
    ids = set(support.listing.admitted_assertion_ids)
    if len(ids) > 5000:
        raise GuestNativeGraphError("Graph is too large for release selection")
    assertions = []
    evidence_ids = set()
    for assertion_id in sorted(ids):
        assertion = context.parsed.get_assertion(assertion_id)
        if assertion is None:
            raise GuestNativeGraphError("Admitted assertion disappeared")
        try:
            _assertion(context, ids, assertion_id, subject=assertion.subject_entity_id, predicate=assertion.predicate)
            if assertion.predicate == "dnd5e:name" and isinstance(assertion.value, ParsedLiteralValue):
                value = _text(assertion.value.value)
                kind = "name"
            elif assertion.predicate == "dnd5e:classification" and isinstance(assertion.value, ParsedTermRefValue):
                value = _text(assertion.value.term.removeprefix("dnd5e:"))
                kind = "classification"
            elif isinstance(assertion.value, ParsedEntityRefValue):
                value = _text(assertion.predicate.removeprefix("dnd5e:").replace("_", " "))
                kind = "relationship"
            else:
                continue
        except GuestReleaseAssertionError:
            continue
        assertions.append((assertion, kind, value))
        evidence_ids.update(assertion.metadata.evidence_ref_ids)
    if len(evidence_ids) > 1000:
        raise GuestNativeGraphError("Graph has too much evidence for release selection")
    sources = {}
    for evidence_id in sorted(evidence_ids):
        evidence = access.parsed.get_evidence(evidence_id)
        if evidence is None or evidence.evidence_role != "support":
            continue
        catalog = list_admitted_native_text_sources(access, evidence_ref_ids=[evidence_id])
        matches = [item for item in catalog.sources if evidence_id in item.evidence_ref_ids]
        if not catalog.complete or len(matches) != 1:
            continue
        source = matches[0]
        origin = source.origin
        if origin is None or origin.namespace != "dungeonbuddy.workspace-document-registry":
            continue
        try:
            document_id = str(UUID(origin.object_id))
            page = committed_page(document_id, world_id=world_id)
            if (page.revision is None or page.page.status != "active"
                or page.metadata.visibility_state not in {"internal", "player_safe"}
                or origin.revision_id != f"registry-revision:{page.page.object_revision}"
                or page.revision.content_sha256 != source.source_revision.content_sha256):
                continue
            opened = open_admitted_native_text(access, evidence_id)
            if opened.status != "available" or opened.body_text != page.revision.markdown:
                continue
            raw = opened.body_text.encode("utf-8")
            start = len(raw[:opened.span_start_byte].decode("utf-8"))
            end = len(raw[:opened.span_end_byte].decode("utf-8"))
            text = opened.body_text[start:end]
            excerpt, proof = selected_page_excerpt(world_id=world_id, document_id=document_id,
                revision_n=page.revision.revision_n, expected_sha256=page.revision.content_sha256,
                start=start, end=end, expected_excerpt=text)
            verify_source_citation(evidence_id=evidence_id, access=access, excerpt=excerpt,
                source_binding=proof[:9], expected_native_world_id=binding.native_world_id,
                expected_graph_revision=revision_id)
        except (ValueError, UnicodeDecodeError, ApplicationStateError, GuestReleaseSourceError, GuestReleaseEvidenceError):
            continue
        sources[evidence_id] = {"document_id": document_id, "document_title": page.page.title,
            "visibility": page.metadata.visibility_state, "revision_n": page.revision.revision_n,
            "sha256": page.revision.content_sha256, "start": start, "end": end,
            "excerpt": text, "evidence_id": evidence_id}
    fields = []
    for assertion, kind, value in assertions:
        eligible = [item for item in assertion.metadata.evidence_ref_ids if item in sources]
        if not eligible:
            continue
        fields.append({"assertion_id": assertion.assertion_id, "entity_id": assertion.subject_entity_id,
            "kind": kind, "value": value, "predicate": assertion.predicate,
            "target_id": assertion.value.entity_id if kind == "relationship" else None,
            "temporal": assertion.metadata.temporal_scope.kind, "evidence_ids": eligible})
    return {"graph_revision": revision_id, "fields": fields, "sources": list(sources.values())}
