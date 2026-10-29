"""Governed source-statement publication and complete qualified subject readback."""

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

from dungeonmind.application.vnext import (
    EntityReadService,
    open_admitted_native_text,
    open_native_text_source_access_context,
    publish_native_source_evidence_extension,
)
from dungeonmind.application.vnext.prospective import get_prospective_publication
from dungeonmind.contracts.vnext.native_source import NativeSourceEvidenceExtensionV1
from dungeonmind.domain.canonical import canonical_sha256
from fastapi.encoders import jsonable_encoder

from apps.live_control_server.integrations.dungeonmind import (
    native_registry_source as native,
)
from apps.live_control_server.integrations.worldkeeper import (
    registry_standing_consumer as transport,
)
from apps.live_control_server.integrations.worldkeeper import (
    source_statements as mapping,
)
from apps.live_control_server.models.source_statements import StatementSelection
from apps.live_control_server.services.agent_graph_auth import require_native_graph_gm
from apps.live_control_server.services.graph_object_authoring_prepare import (
    decode_publication_intent,
    sign_publication_intent,
)
from graph_memory.vnext.domain_runtime import (
    CAMPAIGN_SCOPE_AXIS,
    GM_LABEL,
    PLAYER_LABEL,
    DungeonBuddyVNextProjectionInput,
    build_dungeonbuddy_read_context,
)

PURPOSE = "dmb_source_statement_confirm_v1"
PAYLOAD_FIELDS = {
    "schema",
    "clause",
    "quote",
    "meaning",
    "mode",
    "reporter",
    "referents",
    "uncertainty",
    "qualifications",
    "episode",
    "source_order",
    "embedded_content_factive",
    "assertion_target",
    "visibility",
    "proof",
}
CLAUSE_FIELDS = {
    "world",
    "campaign",
    "logical_source",
    "source_sha256",
    "start_byte",
    "end_byte",
    "clause_sha256",
}


class StatementError(ValueError):
    def __init__(self, code, message, *, retry_original_packet=False):
        self.code = code
        self.retry_original_packet = retry_original_packet
        super().__init__(message)


def _refuse(code, message):
    raise StatementError(code, message)


def semantic_digest(payload):
    # Native proof allocations are authenticated but are not interpreted meaning.
    return transport.digest({k: v for k, v in payload.items() if k != "proof"})


def _context(repo, space, revision, campaign, role="gm"):
    domain, profile = native.descriptors(repo, space, revision)
    access = open_native_text_source_access_context(
        repository=repo,
        space_id=space,
        revision_id=revision,
        domain_contract=domain,
        audience_labels=(GM_LABEL, PLAYER_LABEL) if role == "gm" else (PLAYER_LABEL,),
    )
    read = build_dungeonbuddy_read_context(
        parsed_revision=access.parsed,
        projection_input=DungeonBuddyVNextProjectionInput(
            world_id=space,
            revision_id=revision,
            scope_mode="campaign",
            campaign_id=campaign,
            role=role,
        ),
        source_reader=access.source_view,
    )
    return read, access, domain, profile


def _source(repo, space, access, proof, source_sha256, start, end, clause_sha256):
    if type(proof) is not dict:
        _refuse("statement_source_invalid", "Complete admitted source proof required")
    if set(proof) == {"source_admission_id", "evidence_ref_id"}:
        receipt = repo.get_native_source_admission_receipt(space, proof["source_admission_id"])
        bindings = receipt.bindings if receipt is not None else ()
    elif set(proof) == {"source_evidence_extension_id", "evidence_ref_id"}:
        extension = repo.get_native_source_evidence_extension_receipt(
            space, proof["source_evidence_extension_id"]
        )
        receipt = (
            repo.get_native_source_admission_receipt(space, extension.original_admission_id)
            if extension is not None else None
        )
        if (
            extension is None or receipt is None
            or extension.space_id != space
            or extension.extension_id != proof["source_evidence_extension_id"]
            or extension.original_admission_sha256 != canonical_sha256(receipt.model_dump(mode="json"))
            or extension.source_artifact_id != receipt.source_artifact_id
            or extension.source_revision_id != receipt.source_revision_id
            or extension.origin != receipt.origin
            or repo.get_publication_receipt(space, extension.extension_id) != extension.publication_receipt
        ):
            _refuse("statement_source_invalid", "Extension does not match its original admitted source")
        bindings = extension.bindings
    else:
        _refuse("statement_source_invalid", "Choose exactly one admitted source proof")
    opened = open_admitted_native_text(access, proof["evidence_ref_id"])
    if (
        receipt is None
        or receipt.space_id != space
        or receipt.origin is None
        or repo.get_publication_receipt(space, receipt.admission_id)
        != receipt.publication_receipt
        or opened.status != "available"
        or opened.body_text is None
        or opened.body_sha256 != source_sha256
        or opened.source_artifact_id != receipt.source_artifact_id
        or opened.source_revision_id != receipt.source_revision_id
        or not any(
            b.evidence_ref_id == proof["evidence_ref_id"] for b in bindings
        )
    ):
        _refuse(
            "statement_source_invalid",
            "Source proof does not match the selected admitted revision",
        )
    if not opened.span_start_byte <= start < end <= opened.span_end_byte:
        _refuse(
            "statement_span_invalid",
            "Selected clause is outside its admitted evidence span",
        )
    clause = opened.body_text.encode("utf-8")[start:end]
    try:
        quote = clause.decode("utf-8")
    except UnicodeDecodeError:
        _refuse("statement_span_invalid", "Selected clause splits UTF8 text")
    if hashlib.sha256(clause).hexdigest() != clause_sha256:
        _refuse("statement_span_invalid", "Selected clause digest changed")
    logical = {
        "namespace": receipt.origin.namespace,
        "object_id": receipt.origin.object_id,
    }
    return logical, quote


def _payload(request, repo, space, access):
    if (request.source_admission_id is None) == (request.source_evidence_extension_id is None):
        _refuse("statement_source_invalid", "Choose exactly one admitted source proof")
    proof = {"evidence_ref_id": request.evidence_ref_id}
    if request.source_admission_id is not None:
        proof["source_admission_id"] = request.source_admission_id
    else:
        proof["source_evidence_extension_id"] = request.source_evidence_extension_id
    logical, quote = _source(
        repo,
        space,
        access,
        proof,
        request.source_sha256,
        request.start_byte,
        request.end_byte,
        request.clause_sha256,
    )
    for order in request.source_order:
        for side in ("before", "after"):
            _source(
                repo,
                space,
                access,
                proof,
                request.source_sha256,
                getattr(order, side + "_start"),
                getattr(order, side + "_end"),
                getattr(order, side + "_sha256"),
            )
    return {
        "schema": mapping.SCHEMA,
        "clause": {
            "world": space,
            "campaign": request.campaign_id,
            "logical_source": logical,
            "source_sha256": request.source_sha256,
            "start_byte": request.start_byte,
            "end_byte": request.end_byte,
            "clause_sha256": request.clause_sha256,
        },
        "quote": quote,
        "meaning": request.meaning,
        "mode": request.mode,
        "reporter": request.reporter,
        "referents": sorted(request.referents),
        "uncertainty": request.uncertainty,
        "qualifications": request.qualifications,
        "episode": request.episode,
        "source_order": [o.model_dump() for o in request.source_order],
        "embedded_content_factive": False,
        "assertion_target": "source_statement",
        "visibility": "gm",
        "proof": proof,
    }


def _validate_payload(payload):
    if (
        type(payload) is not dict
        or set(payload) != PAYLOAD_FIELDS
        or payload["schema"] != mapping.SCHEMA
        or payload["embedded_content_factive"] is not False
        or payload["visibility"] != "gm"
        or type(payload["clause"]) is not dict
        or set(payload["clause"]) != CLAUSE_FIELDS
    ):
        _refuse("statement_payload_invalid", "Incomplete qualified source statement")
    clause = payload["clause"]
    logical = clause["logical_source"]
    if (
        type(logical) is not dict
        or set(logical) != {"namespace", "object_id"}
        or any(type(v) is not str or not v.strip() for v in logical.values())
        or type(payload["quote"]) is not str
        or not payload["quote"]
    ):
        _refuse("statement_payload_invalid", "Invalid source correspondence")
    StatementSelection(
        managed_world_id=clause["world"],
        campaign_id=clause["campaign"],
        expected_parent_revision_id="validated-separately",
        **payload["proof"],
        source_sha256=clause["source_sha256"],
        start_byte=clause["start_byte"],
        end_byte=clause["end_byte"],
        clause_sha256=clause["clause_sha256"],
        **{
            k: payload[k]
            for k in (
                "meaning",
                "mode",
                "reporter",
                "referents",
                "uncertainty",
                "qualifications",
                "episode",
                "source_order",
                "embedded_content_factive",
                "assertion_target",
            )
        },
    )
    if payload["referents"] != sorted(payload["referents"]):
        _refuse("statement_payload_invalid", "Noncanonical reviewed endpoints")
    if (
        hashlib.sha256(payload["quote"].encode()).hexdigest() != clause["clause_sha256"]
        or len(payload["quote"].encode()) != clause["end_byte"] - clause["start_byte"]
    ):
        _refuse("statement_payload_invalid", "Stored clause correspondence changed")
    transport.canonical(payload)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate payload key")
        result[key] = value
    return result


def _bundle(repo, space, revision, campaign, statement_id, role="gm", pinned=None):
    read, access, _, _ = (
        pinned
        if pinned is not None
        else _context(repo, space, revision, campaign, role)
    )
    statement = EntityReadService().get_complete_entity(read, statement_id)
    if not statement.found or statement.completeness.status != "complete":
        _refuse("statement_bundle_unavailable", "Complete statement is unavailable")
    summaries = [
        a
        for a in statement.assertions
        if a.subject_entity_id == statement_id and a.predicate == "dnd5e:summary"
    ]
    if len(summaries) != 1:
        _refuse(
            "statement_bundle_unavailable", "Qualified statement payload is unavailable"
        )
    try:
        payload = json.loads(summaries[0].value.value, object_pairs_hook=_unique)
        _validate_payload(payload)
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        raise StatementError(
            "statement_payload_invalid", "Malformed qualified statement"
        ) from exc
    clause = payload["clause"]
    if (clause["world"], clause["campaign"]) != (space, campaign):
        _refuse(
            "statement_bundle_unavailable",
            "Statement scope differs from selected context",
        )
    own = [a for a in statement.assertions if a.subject_entity_id == statement_id]
    about = [a for a in own if a.predicate == mapping.ABOUT]
    reporters = [a for a in own if a.predicate == mapping.REPORTED_BY]
    if (
        len(own) != 1 + len(payload["referents"]) + bool(payload["reporter"])
        or sorted(getattr(a.value, "entity_id", "") for a in about)
        != payload["referents"]
        or [getattr(a.value, "entity_id", "") for a in reporters]
        != ([payload["reporter"]] if payload["reporter"] else [])
    ):
        _refuse(
            "statement_bundle_unavailable",
            "Statement attribution or discovery bundle is incomplete",
        )
    for a in own:
        m = a.metadata
        if (
            tuple((b.axis, b.value) for b in m.scope)
            != ((CAMPAIGN_SCOPE_AXIS, campaign),)
            or m.visibility.kind != "labels_any"
            or tuple(m.visibility.labels) != (GM_LABEL,)
            or m.claim_mode != "dungeonbuddy.claim:fact"
            or m.epistemic_basis != "asserted"
            or m.standing.value != "established"
            or m.temporal_scope.kind != "unknown"
            or tuple(m.evidence_ref_ids) != (payload["proof"]["evidence_ref_id"],)
            or m.domain_metadata
        ):
            _refuse(
                "statement_bundle_unavailable",
                "Statement qualification metadata differs",
            )
    logical, quote = _source(
        repo,
        space,
        access,
        payload["proof"],
        clause["source_sha256"],
        clause["start_byte"],
        clause["end_byte"],
        clause["clause_sha256"],
    )
    if logical != clause["logical_source"] or quote != payload["quote"]:
        _refuse("statement_bundle_unavailable", "Stored source correspondence differs")
    for order in payload["source_order"]:
        for side in ("before", "after"):
            _source(
                repo,
                space,
                access,
                payload["proof"],
                clause["source_sha256"],
                order[side + "_start"],
                order[side + "_end"],
                order[side + "_sha256"],
            )
    return {
        "statement_id": statement_id,
        "payload": payload,
        "semantic_digest": semantic_digest(payload),
        "assertion_ids": sorted(a.assertion_id for a in own),
        "revision_id": revision,
    }


def _recover(repo, space, payload):
    operation = mapping.publication_id(payload["clause"])
    aggregate = get_prospective_publication(space, operation, repository=repo)
    if aggregate is None:
        return None
    bindings = aggregate.prospective_result.results
    objects = [
        b
        for b in bindings
        if b.client_op_id == "statement" and b.result_kind == "entity"
    ]
    if len(objects) != 1:
        _refuse(
            "statement_receipt_invalid", "Original statement mapping is unavailable"
        )
    bundle = _bundle(
        repo,
        space,
        aggregate.publication_receipt.published_revision_id,
        payload["clause"]["campaign"],
        objects[0].durable_id,
    )
    if bundle["semantic_digest"] != semantic_digest(payload):
        _refuse(
            "statement_semantic_conflict",
            "This source clause already has different reviewed meaning; correction review required",
        )
    expected = {
        "statement",
        "qualified-payload",
        *("about:" + str(i) for i in range(len(payload["referents"]))),
    }
    if payload["reporter"]:
        expected.add("reporter")
    if (
        len(bindings) != len(expected)
        or {b.client_op_id for b in bindings} != expected
        or sorted(b.durable_id for b in bindings if b.result_kind == "assertion")
        != bundle["assertion_ids"]
    ):
        _refuse(
            "statement_receipt_invalid", "Original statement result mappings differ"
        )
    return {
        "receipt": jsonable_encoder(aggregate.publication_receipt),
        "bindings": jsonable_encoder(bindings),
        "bundle": bundle,
    }


def _head_matches(repo, space, revision):
    head = repo.get_head(space)
    if head is None or head.head_revision_id != revision:
        _refuse(
            "statement_parent_stale", "Selected World revision changed; refresh review"
        )


def prepare(request, principal):
    require_native_graph_gm(principal)
    bound = native.binding(request.managed_world_id)
    space = bound["native_world_id"]
    repo = native.repository()
    read, access, domain, profile = _context(
        repo, space, request.expected_parent_revision_id, request.campaign_id
    )
    payload = _payload(request, repo, space, access)
    _validate_payload(payload)
    recovered = _recover(repo, space, payload)
    if recovered is not None:
        return {"status": "committed", "recovered": True, "result": recovered}
    _head_matches(repo, space, request.expected_parent_revision_id)
    for endpoint in {
        *request.referents,
        *([request.reporter] if request.reporter else []),
    }:
        entity = EntityReadService().get_entity(read, endpoint)
        if (
            not entity.found
            or entity.completeness.status != "complete"
            or not entity.assertions
            or not any(a.predicate == "dnd5e:name" for a in entity.assertions)
        ):
            _refuse(
                "statement_endpoint_unreviewable",
                "Reviewed endpoint has no visible supported identity",
            )
    operation = mapping.publication_id(payload["clause"])
    now = datetime.now(UTC)
    runtime = transport.runtime(repo, domain, profile, now=now, operation_id=operation)
    prepared = runtime.prepare_change(
        mapping.intent(space, payload, request.evidence_ref_id)
    )
    # WK must preserve the reviewed exact parent and all selected operations.
    if (
        prepared.expected_parent_revision_id != request.expected_parent_revision_id
        or prepared.prepared_operations
        != mapping.intent(space, payload, request.evidence_ref_id).operations
    ):
        _refuse(
            "statement_parent_stale",
            "Preparation changed the reviewed statement or parent",
        )
    parent = repo.get_revision(space, request.expected_parent_revision_id)

    def authority(ref, kind):
        return {
            "authority_id": getattr(ref, kind + "_id"),
            "revision": getattr(ref, kind + "_revision"),
            "descriptor_sha256": ref.descriptor_sha256,
        }

    parent_context = {
        "space_id": space,
        "revision_id": request.expected_parent_revision_id,
        "graph_sha256": parent.graph_payload_sha256,
        "domain_ref": authority(parent.revision.domain_contract_ref, "domain"),
        "profile_ref": authority(parent.revision.semantic_profile_ref, "profile"),
    }
    transport.verify_prepared_parent(prepared, parent_context)
    encoded = transport.encode_prepared(prepared)
    envelope = {
        "schema": PURPOSE,
        "purpose": PURPOSE,
        "principal": principal.subject,
        "binding": bound,
        "payload": payload,
        "parent_context": parent_context,
        "prepared_digest": transport.digest(encoded),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
    }
    if native.binding(request.managed_world_id) != bound:
        _refuse("statement_binding_changed", "World binding changed during review")
    return {
        "status": "prepared",
        "envelope": envelope,
        "prepared": encoded,
        "token": sign_publication_intent(envelope),
    }


def confirm(request, principal):
    require_native_graph_gm(principal)
    envelope = request.envelope
    signed = decode_publication_intent(request.token, allow_expired_recovery=True)
    if (
        not hmac.compare_digest(
            transport.canonical(signed), transport.canonical(envelope)
        )
        or envelope.get("schema") != PURPOSE
        or envelope.get("purpose") != PURPOSE
        or envelope.get("principal") != principal.subject
        or envelope.get("prepared_digest") != transport.digest(request.prepared)
    ):
        _refuse("statement_review_invalid", "Statement review authentication differs")
    payload = envelope["payload"]
    _validate_payload(payload)
    bound = envelope["binding"]
    if native.binding(bound["managed_world_id"]) != bound:
        _refuse("statement_binding_changed", "Reviewed World binding changed")
    space = bound["native_world_id"]
    if payload["clause"]["world"] != space:
        _refuse("statement_review_invalid", "Statement World differs from review")
    prepared = transport.decode_prepared(request.prepared)
    operation = mapping.publication_id(payload["clause"])
    if (
        prepared.prepared_change_id != operation
        or prepared.dungeonmind_publication_id != operation
        or prepared.space_id != space
        or prepared.producer != mapping.PRODUCER
        or prepared.prepared_operations
        != mapping.intent(
            space, payload, payload["proof"]["evidence_ref_id"]
        ).operations
    ):
        _refuse(
            "statement_review_invalid", "Prepared statement meaning differs from review"
        )
    transport.verify_prepared_parent(prepared, envelope["parent_context"])
    repo = native.repository()
    recovered = _recover(repo, space, payload)
    if recovered is not None:
        return {"status": "committed", "recovered": True, "result": recovered}
    if datetime.fromisoformat(envelope["expires_at"]) < datetime.now(UTC):
        _refuse("statement_review_expired", "Refresh expired uncommitted review")
    _head_matches(repo, space, prepared.expected_parent_revision_id)
    _, access, domain, profile = _context(
        repo, space, prepared.expected_parent_revision_id, payload["clause"]["campaign"]
    )
    clause = payload["clause"]
    logical, quote = _source(
        repo,
        space,
        access,
        payload["proof"],
        clause["source_sha256"],
        clause["start_byte"],
        clause["end_byte"],
        clause["clause_sha256"],
    )
    if logical != clause["logical_source"] or quote != payload["quote"]:
        _refuse("statement_source_invalid", "Reviewed clause changed")
    transport.runtime(
        repo, domain, profile, now=prepared.prepared_at, operation_id=operation
    ).commit_prepared_change(prepared, confirmed_by=principal.subject)
    result = _recover(repo, space, payload)
    if result is None:
        raise StatementError(
            "statement_outcome_unknown",
            "Keep and retry the original prepared packet",
            retry_original_packet=True,
        )
    return {"status": "committed", "recovered": False, "result": result}


def read_subject(*, managed_world_id, campaign_id, revision_id, entity_id, principal):
    if principal.role not in {"gm", "player"}:
        _refuse("statement_role_invalid", "Authenticated reader role required")
    bound = native.binding(managed_world_id)
    space = bound["native_world_id"]
    repo = native.repository()
    pinned = _context(repo, space, revision_id, campaign_id, principal.role)
    read = pinned[0]
    subject = EntityReadService().get_complete_entity(read, entity_id)
    gaps = [] if subject.completeness.status == "complete" else ["subject_read_partial"]
    links = [
        a
        for a in subject.assertions
        if a.predicate == mapping.ABOUT
        and getattr(a.value, "entity_id", None) == entity_id
        and a.subject_entity_id != entity_id
    ]
    bundles = []
    for statement_id in sorted({a.subject_entity_id for a in links}):
        try:
            bundle = _bundle(
                repo,
                space,
                revision_id,
                campaign_id,
                statement_id,
                principal.role,
                pinned=pinned,
            )
            expected_links = [
                a.assertion_id for a in links if a.subject_entity_id == statement_id
            ]
            if not set(expected_links).issubset(bundle["assertion_ids"]):
                _refuse(
                    "statement_bundle_unavailable",
                    "Discovery link differs from complete bundle",
                )
            bundles.append(bundle)
        except (ValueError, TypeError, AttributeError, KeyError):
            gaps.append("statement_bundle_unavailable")
    return {
        "status": "partial"
        if gaps
        else ("complete" if bundles else "no_visible_statements"),
        "space_id": space,
        "campaign_id": campaign_id,
        "revision_id": revision_id,
        "entity_id": entity_id,
        "statements": bundles,
        "gap_codes": sorted(set(gaps)),
        "universal_absence_claimed": False,
    }


def extend_source_evidence(request, principal):
    """GM requests evidence only; Core owns immutable identity and atomic recovery."""
    require_native_graph_gm(principal)
    bound = native.binding(request.managed_world_id)
    space = bound["native_world_id"]
    repo = native.repository()
    domain, profile = native.descriptors(repo, space, request.expected_parent_revision_id)
    receipt = publish_native_source_evidence_extension(
        repository=repo,
        request=NativeSourceEvidenceExtensionV1(
            space_id=space,
            **request.model_dump(exclude={"managed_world_id"}),
        ),
        domain_contract=domain,
        semantic_profile=profile,
        audience_labels=(GM_LABEL, PLAYER_LABEL),
    )
    return {"status": "committed", "receipt": receipt.model_dump(mode="json")}
