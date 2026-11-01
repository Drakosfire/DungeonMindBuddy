"""Saved Recap review/confirmation via existing WK/Core; no source admission writes."""

import hashlib
import hmac
import json
from datetime import UTC, datetime
from uuid import uuid4

import worldkeeper.application as wk
from dungeonmind.application.vnext import open_admitted_native_text
from fastapi.encoders import jsonable_encoder

from application_state.source import service as sources
from apps.live_control_server import config
from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
from apps.live_control_server.integrations.worldkeeper import registry_standing_consumer as transport
from apps.live_control_server.integrations.worldkeeper.graph_authoring_consumer import _predicate
from apps.live_control_server.services import native_recap_source_admission as admission
from apps.live_control_server.models.native_recap_preparation import NativeRecapReviewEnvelope
from apps.live_control_server.services.graph_object_authoring_prepare import (
    PREPARE_TTL, sign_publication_intent, decode_publication_intent,
)
from apps.live_control_server.services.agent_graph_auth import require_native_graph_gm
from apps.live_control_server.services.extract_promote import project_candidate_record_evidence
from apps.live_control_server.services.graph_run_registry import load_reviewable_extraction_data
from graph_memory.anchor_quotes import find_anchor_quote_matches
from graph_memory.candidate_document_integrity import classify_candidate_document_integrity
from graph_memory.candidate_graph_preview import NODE_TYPES
from graph_memory.vnext.domain_runtime import CAMPAIGN_SCOPE_AXIS

# Product representation only. Classification does not establish role or source truth.
_KINDS = {kind: f"dungeonbuddy:{kind}" for kind in NODE_TYPES}
_KINDS["location"] = "dnd5e:location"
PRODUCER = "dungeonbuddy:reviewed-recap"


class ReviewRefused(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require(condition, code):
    if not condition:
        raise ReviewRefused(code)


def _metadata(review, campaign, evidence):
    return wk.AssertionMetadata(
        scope=(wk.ScopeBinding(CAMPAIGN_SCOPE_AXIS, campaign),),
        visibility=review.visibility,
        epistemic_basis=review.epistemic_basis,
        claim_mode=review.claim_mode,
        standing=review.standing,
        evidence_ref_ids=tuple(evidence),
        temporal_scope=review.temporal_scope.native(),
        domain_metadata=tuple(item.native() for item in review.domain_metadata),
    )


def _support_refs(review, witnesses, access, admitted):
    """Join explicit review choices to Core evidence, not a truth/entailment test."""
    for identifier in review.evidence_ref_ids:
        evidence = access.parsed.get_evidence(identifier)
        _require(evidence is not None and evidence.evidence_role == "support",
                 "candidate_support_required")
        opened = open_admitted_native_text(access, identifier)
        _require(opened.status == "available", "candidate_support_unavailable")
        _require(
            opened.source_artifact_id == admitted.source_artifact_id
            and opened.source_revision_id == admitted.source_revision_id
            and opened.body_sha256 == admitted.app_body_sha256,
            "candidate_support_source_mismatch",
        )
        # Core verified the bytes/visibility. Buddy only checks that this selected
        # native passage belongs to the saved candidate's actual source witness.
        lines = opened.body_text.splitlines(keepends=True)
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line.encode("utf-8")))
        selected = opened.body_text.encode("utf-8")[opened.span_start_byte:opened.span_end_byte].decode("utf-8")
        _require(any(
            1 <= witness.start_line <= witness.end_line <= len(lines)
            and offsets[witness.start_line - 1] <= opened.span_start_byte
            < opened.span_end_byte <= offsets[witness.end_line]
            and find_anchor_quote_matches(selected, witness.anchor_quotes)
            for witness in witnesses
        ), "candidate_support_outside_witness")
    return tuple(review.evidence_ref_ids)


def _fields(kind, record):
    if kind == "node":
        values = {"label": record.label, "node_type": record.node_type}
        if record.description is not None:
            values["description"] = record.description
        values.update({f"session_actions:{i}": value for i, value in enumerate(record.session_actions)})
        return values
    return {"title": record.title, "node_type": "session_beat", "summary": record.summary}


def _intent(preview, selections, space, campaign, admitted, data, access):
    records = {
        **{("node", row.node_id): row for row in preview.nodes},
        **{("edge", row.edge_id): row for row in preview.edges},
        **{("beat", row.beat_id): row for row in preview.beats},
    }
    by_key = {(s.kind, s.record_id): s for s in selections}
    _require(set(by_key) <= set(records), "unknown_candidate_selection")
    operations, inventory, endpoints, edge_witnesses = [], [], {}, {}
    for index, (key, record) in enumerate(records.items()):
        kind, identifier = key
        selection = by_key.get(key)
        action = selection.action if selection else "held"
        values = _fields(kind, record) if kind != "edge" else {}
        selected = []
        if selection and action in {"create", "use_existing"}:
            # One shared projector verifies exact APP source/span/quote references.
            witness = project_candidate_record_evidence(
                assertion_id=identifier, kind="relationship" if kind == "edge" else "object",
                label=getattr(record, "label", None) or getattr(record, "title", identifier),
                summary="", evidence_refs=record.evidence_refs,
                source_prose=data.source_bytes.decode("utf-8"),
                source_artifact_id=data.source_artifact.source_artifact_id,
                span_index=data.span_index,
            )
            if kind == "edge":
                edge_witnesses[identifier] = witness.evidence
            else:
                facts = []
                for field_index, fact in enumerate(selection.facts):
                    field = fact.field if fact.index is None else f"{fact.field}:{fact.index}"
                    _require(field in values, "unknown_candidate_field")
                    value = values[field]
                    _require(isinstance(value, str) and bool(value.strip()), "blank_candidate_field")
                    if fact.field == "node_type":
                        _require(value in _KINDS, "unsupported_candidate_kind")
                        predicate, encoded = "dnd5e:classification", wk.TermRefFactValue(_KINDS[value])
                    else:
                        predicate = "dnd5e:name" if fact.field in {"label", "title"} else "dnd5e:summary"
                        encoded = wk.LiteralFactValue.from_json(value)
                    facts.append(wk.CreateFact(
                        f"record:{index}.field:{field_index}", predicate, encoded,
                        _metadata(fact.metadata, campaign,
                                  _support_refs(fact.metadata, witness.evidence, access, admitted)),
                    ))
                    selected.append(field)
                if action == "create":
                    operation = f"record:{index}"
                    operations.append(wk.CreateObject(operation, tuple(facts)))
                    endpoint = wk.ResultOf(operation)
                else:
                    operations.append(wk.UseExisting(selection.entity_id, tuple(facts)))
                    endpoint = wk.DurableObjectRef(selection.entity_id)
                if kind == "node":
                    endpoints[identifier] = endpoint
        inventory.append({
            "kind": kind, "record_id": identifier, "disposition": action,
            "selected_fields": selected, "unselected_fields": sorted(set(values) - set(selected)),
            "held_aliases": list(getattr(record, "aliases", ())),
            "non_executable_hints": [field for field in ("corpus_ref", "enriched_by", "order", "involved_node_ids", "unresolved_thread_node_ids", "source_beat_id") if getattr(record, field, None) is not None],
        })
    for index, edge in enumerate(preview.edges):
        selection = by_key.get(("edge", edge.edge_id))
        if selection and selection.action == "create":
            _require(edge.from_node_id in endpoints and edge.to_node_id in endpoints, "selected_edge_endpoint_held")
            operations.append(wk.CreateRelationship(
                f"edge:{index}", endpoints[edge.from_node_id], _predicate(edge.relationship_type),
                endpoints[edge.to_node_id], _metadata(selection.metadata, campaign,
                    _support_refs(selection.metadata, edge_witnesses[edge.edge_id], access, admitted)),
            ))
    for kind, collection in (("ignored", preview.ignored_items), ("deferred", preview.deferred_items),
                             ("proposed_write", preview.proposed_writes),
                             ("source_observation", preview.source_observations)):
        for row in collection:
            identifier = getattr(row, "item_id", None) or getattr(row, "write_id", None) or row.observation_id
            inventory.append({"kind": kind, "record_id": identifier,
                              "disposition": "held", "reason": "not_an_executable_review_selection"})
    return wk.WorldChangeIntent(space, PRODUCER, tuple(operations)), inventory


def prepare(request, principal):
    require_native_graph_gm(principal)
    root = config.artifact_data_root()
    bound = native.binding(request.managed_world_id)
    space = bound["native_world_id"]
    data = load_reviewable_extraction_data(root, request.run_id)
    run, artifact = data.run, data.source_artifact
    _require(run.revision == request.expected_run_revision, "candidate_run_changed")
    _require(hashlib.sha256(data.candidate_bytes).hexdigest() == request.candidate_sha256, "candidate_bytes_changed")
    _require(run.source_domain == "recap" and run.campaign_id == request.campaign_id, "candidate_scope_mismatch")
    # Extraction context is generation history. Present publication authority
    # comes from the current source ownership/admission and reviewed WK change.
    source = sources.get_source_markdown(
        source_artifact_id=artifact.source_artifact_id, content_sha256=artifact.content_sha256,
    )
    _require(source is not None, "candidate_source_unavailable")
    _require(
        source.markdown.encode("utf-8") == data.source_bytes
        and source.content_sha256 == artifact.content_sha256
        and source.world_id == artifact.world_id == space
        and source.source_domain == artifact.source_domain == "recap"
        and source.campaign_id == artifact.campaign_id == request.campaign_id
        and source.session_id == artifact.session_id == run.session_id
        and source.media_type == "text/markdown" and source.encoding == "utf-8",
        "candidate_source_mismatch",
    )
    session = run.session_id or ""
    _require(session.startswith("session-") and session[8:].isdigit(), "candidate_session_invalid")
    admitted = admission.inspect(root, request.source_admission_run_id, request.managed_world_id,
                                 request.campaign_id, int(session[8:]))
    _require(admitted.state == "admitted" and admitted.opening.state == "verified", "candidate_source_not_admitted")
    _require(
        admitted.app_source_artifact_id == source.source_artifact_id
        and admitted.app_source_revision_id == source.source_revision_id
        and admitted.app_body_sha256 == source.content_sha256
        and admitted.native_world_id == space and admitted.binding_version == bound["binding_version"]
        and bool(admitted.evidence_ref_id), "candidate_admission_mismatch",
    )
    classification = classify_candidate_document_integrity(json.loads(data.candidate_bytes))
    _require(not classification.is_document_integrity_failure, "candidate_document_invalid")
    preview = classification.preview
    _require(preview.campaign_id == run.campaign_id and preview.session_id == run.session_id
             and tuple(preview.source_artifact_ids) == (artifact.source_artifact_id,), "candidate_document_scope_mismatch")
    repo = native.repository()
    context, access = native.access_context(repo, space)
    _require(context["revision_id"] == request.expected_parent_revision_id, "candidate_parent_stale")
    _require(context["source_epoch"] == request.expected_source_authority_epoch,
             "candidate_source_authority_stale")
    intent, inventory = _intent(preview, request.selections, space, request.campaign_id,
                                admitted, data, access)
    prepared = None
    if intent.operations:
        domain, profile = native.descriptors(repo, space, context["revision_id"])
        prepared = transport.runtime(repo, domain, profile, now=datetime.now(UTC),
                                     operation_id=f"recap-review:{uuid4()}").prepare_change(intent)
        transport.verify_prepared_parent(prepared, context)
        _require(prepared.prepared_operations == intent.operations, "candidate_preparation_changed")
    _require(native.binding(request.managed_world_id) == bound, "candidate_binding_changed")
    head = repo.get_head(space)
    _require(head is not None and head.head_revision_id == request.expected_parent_revision_id, "candidate_parent_stale")
    _require(repo.open_native_source_view(space).epoch == context["source_epoch"],
             "candidate_source_authority_changed")
    packet = transport.encode_prepared(prepared) if prepared else None
    envelope = NativeRecapReviewEnvelope(
        purpose="dmb_native_recap_confirm_v1", producer=PRODUCER,
        principal=principal.subject, binding=bound, parent_context=context,
        review=request, prepared_change_id=prepared.prepared_change_id,
        prepared_digest=transport.digest(packet), expires_at=prepared.prepared_at + PREPARE_TTL,
    ).model_dump(mode="json") if prepared else None
    return {
        "status": "prepared" if prepared else "held", "publication": "not_performed",
        "run_id": run.run_id, "run_revision": run.revision,
        "candidate_sha256": request.candidate_sha256,
        "source_revision_id": str(source.source_revision_id),
        "native_source_admission_id": admitted.admission_id,
        "expected_parent_revision_id": request.expected_parent_revision_id,
        "expected_source_authority_epoch": request.expected_source_authority_epoch,
        "prepared": packet, "envelope": envelope,
        "token": sign_publication_intent(envelope) if envelope else None,
        "records": inventory,
    }


def confirm(request, principal):
    """Authenticate one review; WK/Core own commit, replay and exact-child proof."""
    require_native_graph_gm(principal)
    envelope = request.envelope
    signed = decode_publication_intent(request.token, allow_expired_recovery=True)
    _require(
        hmac.compare_digest(transport.canonical(signed),
                            transport.canonical(envelope.model_dump(mode="json")))
        and envelope.principal == principal.subject
        and envelope.prepared_digest == transport.digest(request.prepared),
        "candidate_review_invalid",
    )
    bound = native.binding(envelope.review.managed_world_id)
    _require(bound == envelope.binding, "candidate_binding_changed")
    space = bound["native_world_id"]
    prepared = transport.decode_prepared(request.prepared)
    _require(
        prepared.space_id == space and prepared.producer == PRODUCER
        and prepared.prepared_change_id == prepared.dungeonmind_publication_id
        == envelope.prepared_change_id
        and prepared.expected_parent_revision_id == envelope.review.expected_parent_revision_id
        and envelope.parent_context.get("source_epoch")
        == envelope.review.expected_source_authority_epoch,
        "candidate_review_invalid",
    )
    try:
        transport.verify_prepared_parent(prepared, envelope.parent_context)
    except (KeyError, TypeError, ValueError) as exc:
        raise ReviewRefused("candidate_review_invalid") from exc
    repo = native.repository()
    # Presence only selects recovery; it never establishes success. WK verifies
    # the original exact child even after expiry or a newer source/head exists.
    recovering = repo.get_publication_receipt(space, prepared.dungeonmind_publication_id) is not None
    if not recovering:
        _require(envelope.expires_at >= datetime.now(UTC), "candidate_review_expired")
        context, access = native.access_context(repo, space)
        _require(context["revision_id"] == prepared.expected_parent_revision_id,
                 "candidate_parent_stale")
        _require(context["source_epoch"] == envelope.review.expected_source_authority_epoch,
                 "candidate_source_authority_stale")
        transport.verify_prepared_parent(prepared, context)
        # One current Core opening, no APP/candidate reload or second source validator.
        for witness in prepared.evidence_witnesses:
            _require(open_admitted_native_text(access, witness.evidence_ref_id).status == "available",
                     "candidate_support_unavailable")
        _require(repo.open_native_source_view(space).epoch == context["source_epoch"],
                 "candidate_source_authority_changed")
    _require(native.binding(envelope.review.managed_world_id) == bound, "candidate_binding_changed")
    domain, profile = native.descriptors(repo, space, prepared.expected_parent_revision_id)
    result = transport.runtime(repo, domain, profile, now=prepared.prepared_at,
                               operation_id=prepared.prepared_change_id).commit_prepared_change(
                                   prepared, confirmed_by=principal.subject)
    return {"status": "committed", "recovered": recovering, "result": jsonable_encoder(result)}
