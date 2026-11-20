"""Explicit owner-selected native assertion projection for a private candidate.

No source, label, neighbor, summary or alias is implicitly selected. This module
does not authorize a request or publish its result.
"""
from __future__ import annotations

from uuid import UUID, uuid4

from dungeonmind.application.vnext import ParsedEntityRefValue, ParsedLiteralValue, ParsedTermRefValue

from apps.live_control_server.services.guest_release_evidence import verify_source_citation
from apps.live_control_server.services.guest_release_sources import contains_unsupported_destination


class GuestReleaseAssertionError(ValueError):
    """A requested exact assertion cannot be copied safely."""


def _assertion(context, admitted_ids: set[str], assertion_id: str, *, subject: str, predicate: str):
    assertion = context.parsed.get_assertion(assertion_id)
    if (assertion_id not in admitted_ids or assertion is None
        or assertion.subject_entity_id != subject or assertion.predicate != predicate):
        raise GuestReleaseAssertionError("Selected assertion is not admitted")
    # The initial wire can represent only established asserted facts without
    # losing modality. Other claims must not be silently flattened; a later
    # representation must preserve their full semantics.
    if (assertion.metadata.standing != "established"
        or assertion.metadata.epistemic_basis != "asserted"
        or assertion.metadata.claim_mode != "dungeonbuddy.claim:fact"
        or assertion.metadata.temporal_scope.kind not in {"timeless", "unknown"}):
        raise GuestReleaseAssertionError("Selected assertion semantics are unsupported")
    return assertion


def _text(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 500 or contains_unsupported_destination(value):
        raise GuestReleaseAssertionError("Selected display value is unsafe")
    return value


def _citation(assertion, selection: tuple, *, access, native_world_id: str, revision_id: str) -> str:
    evidence_id, excerpt, source_binding = selection
    if evidence_id not in assertion.metadata.evidence_ref_ids:
        raise GuestReleaseAssertionError("Selected evidence does not support assertion")
    return verify_source_citation(evidence_id=evidence_id, access=access, excerpt=excerpt,
        source_binding=source_binding, expected_native_world_id=native_world_id,
        expected_graph_revision=revision_id)


def select_node(*, context, admitted_ids: set[str], entity_id: str, name_assertion_id: str,
                kind_assertion_id: str, name_evidence: tuple, kind_evidence: tuple,
                access, native_world_id: str, revision_id: str, local_id: UUID | None = None) -> tuple[dict, tuple]:
    """Copy one exact name and classification, with separate evidence."""
    name = _assertion(context, admitted_ids, name_assertion_id, subject=entity_id, predicate="dnd5e:name")
    kind = _assertion(context, admitted_ids, kind_assertion_id, subject=entity_id, predicate="dnd5e:classification")
    if not isinstance(name.value, ParsedLiteralValue) or not isinstance(kind.value, ParsedTermRefValue):
        raise GuestReleaseAssertionError("Selected node assertions have unsupported values")
    label = _text(name.value.value)
    category = _text(kind.value.term.removeprefix("dnd5e:"))
    name_citation = _citation(name, name_evidence, access=access, native_world_id=native_world_id, revision_id=revision_id)
    kind_citation = _citation(kind, kind_evidence, access=access, native_world_id=native_world_id, revision_id=revision_id)
    node_id = local_id or uuid4()
    public = {"id": str(node_id), "label": label, "kind": category,
              "name_citations": [name_citation], "kind_citations": [kind_citation],
              "name_temporal": name.metadata.temporal_scope.kind,
              "kind_temporal": kind.metadata.temporal_scope.kind}
    return public, (node_id, entity_id, name_assertion_id, name_evidence[0], name_citation,
                    kind_assertion_id, kind_evidence[0], kind_citation)


def select_relationship(*, context, admitted_ids: set[str], assertion_id: str,
                        subject_id: str, predicate: str, node_ids: dict[str, str],
                        evidence: tuple, access, native_world_id: str, revision_id: str,
                        local_id: UUID | None = None) -> tuple[dict, tuple]:
    """Copy one exact relationship only when both endpoints were selected."""
    assertion = _assertion(context, admitted_ids, assertion_id, subject=subject_id, predicate=predicate)
    if not isinstance(assertion.value, ParsedEntityRefValue):
        raise GuestReleaseAssertionError("Selected assertion is not a relationship")
    target = assertion.value.entity_id
    if subject_id not in node_ids or target not in node_ids:
        raise GuestReleaseAssertionError("Relationship endpoints are not selected")
    # Preserve the actual qualified predicate rather than flattening it into an
    # inferred natural-language claim. The UI can render this as plain text.
    label = _text(predicate.removeprefix("dnd5e:").replace("_", " "))
    citation = _citation(assertion, evidence, access=access, native_world_id=native_world_id, revision_id=revision_id)
    edge_id = local_id or uuid4()
    public = {"id": str(edge_id), "source": node_ids[subject_id], "target": node_ids[target],
              "label": label, "citations": [citation], "temporal": assertion.metadata.temporal_scope.kind}
    return public, (edge_id, assertion_id, evidence[0], citation)
