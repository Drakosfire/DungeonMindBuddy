"""Owner-only inventory of exact fields and evidence eligible for selection.

This inventory is not an approval, a publication, or a guest-facing payload.
Preparation reopens and independently verifies every selected item.
"""
from __future__ import annotations

import re
from uuid import UUID, uuid4

from dungeonmind.application.vnext import (
    ParsedEntityRefValue, ParsedLiteralValue, ParsedTermRefValue,
    list_admitted_native_text_sources, open_admitted_native_text,
)

from application_state.content.pages import committed_page
from application_state.errors import ApplicationStateError
from apps.live_control_server.integrations.dungeonmind import native_registry_source
from apps.live_control_server.services.guest_release_assertions import GuestReleaseAssertionError, _assertion, _term_label, _text
from apps.live_control_server.services.guest_release_evidence import GuestReleaseEvidenceError, verify_source_citation
from apps.live_control_server.services.guest_release_native_graph import GuestNativeGraphError, read_owner_graph
from apps.live_control_server.services.guest_release_sources import GuestReleaseSourceError, selected_page_excerpt
from apps.live_control_server.services.managed_world_graph_projection import resolve_managed_world_binding


def _context_ranges(body: str, start: int, end: int):
    """Offer individually selected nonempty lines inside the native span."""
    for match in re.finditer(r"[^\r\n]+", body[start:end]):
        value = match.group()
        left = len(value) - len(value.lstrip())
        right = len(value.rstrip())
        if right > left:
            yield start + match.start() + left, start + match.start() + right


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
                value = _term_label(assertion.value.term)
                kind = "classification"
            elif isinstance(assertion.value, ParsedEntityRefValue):
                value = _term_label(assertion.predicate)
                kind = "relationship"
            else:
                continue
        except GuestReleaseAssertionError:
            continue
        assertions.append((assertion, kind, value))
        evidence_ids.update(assertion.metadata.evidence_ref_ids)
    # Keep assertion evidence first: a long context document must not consume
    # the bounded inventory before its Graph fields can be selected.
    catalog = list_admitted_native_text_sources(access)
    independent_ids = {identity for source in catalog.sources for identity in source.evidence_ref_ids
                       if identity not in evidence_ids
                       and (evidence := access.parsed.get_evidence(identity)) is not None
                       and evidence.evidence_role == "context"}
    if len(evidence_ids | independent_ids) > 1000:
        raise GuestNativeGraphError("Graph has too much evidence for release selection")
    sources = []
    by_evidence = {}
    truncated = False
    scanned = 0
    for evidence_id in [*sorted(evidence_ids), *sorted(independent_ids)]:
        evidence = access.parsed.get_evidence(evidence_id)
        if evidence is None or evidence.evidence_role not in {"support", "context"}:
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
        except (ValueError, UnicodeDecodeError, ApplicationStateError, GuestReleaseSourceError, GuestReleaseEvidenceError):
            continue
        if evidence.evidence_role == "context":
            candidates = _context_ranges(opened.body_text, start, end)
        else:
            candidates = [(start, end)]
        for selected_start, selected_end in candidates:
            scanned += 1
            if scanned > 2000:
                truncated = True
                break
            text = opened.body_text[selected_start:selected_end]
            try:
                excerpt, proof = selected_page_excerpt(world_id=world_id, document_id=document_id,
                    revision_n=page.revision.revision_n, expected_sha256=page.revision.content_sha256,
                    start=selected_start, end=selected_end, expected_excerpt=text)
                excerpt["evidence_role"] = evidence.evidence_role
                verify_source_citation(evidence_id=evidence_id, access=access, excerpt=excerpt,
                    source_binding=proof[:9], expected_native_world_id=binding.native_world_id,
                    expected_graph_revision=revision_id)
            except (ValueError, ApplicationStateError, GuestReleaseSourceError, GuestReleaseEvidenceError):
                continue
            if len(sources) >= 500:
                truncated = True
                break
            option_id = str(uuid4())
            by_evidence.setdefault(evidence_id, []).append(option_id)
            sources.append({"option_id": option_id, "document_id": document_id, "document_title": page.page.title,
                "visibility": page.metadata.visibility_state, "revision_n": page.revision.revision_n,
                "sha256": page.revision.content_sha256, "start": selected_start, "end": selected_end,
                "excerpt": text, "evidence_id": evidence_id, "evidence_role": evidence.evidence_role})
        if truncated:
            break
    fields = []
    for assertion, kind, value in assertions:
        eligible = [option for item in assertion.metadata.evidence_ref_ids for option in by_evidence.get(item, [])]
        if not eligible:
            continue
        fields.append({"assertion_id": assertion.assertion_id, "entity_id": assertion.subject_entity_id,
            "kind": kind, "value": value, "predicate": assertion.predicate,
            "target_id": assertion.value.entity_id if kind == "relationship" else None,
            "temporal": assertion.metadata.temporal_scope.kind, "basis": assertion.metadata.epistemic_basis,
            "source_option_ids": eligible})
    return {"graph_revision": revision_id, "fields": fields, "sources": sources, "source_options_truncated": truncated or not catalog.complete}
