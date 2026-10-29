"""One authenticated C1 dossier-standing lifecycle; Core/WK own persistence/replay."""

from __future__ import annotations

from dungeonmind.contracts.vnext import DomainContractRef
from dungeonmind.contracts.semantic_profile import SemanticProfileRef
from graph_memory.vnext.domain_runtime import resolve_dungeonbuddy_descriptors

from datetime import UTC, datetime, timedelta
import hmac

from apps.live_control_server.models.registry_standing import SourceRequest
from apps.live_control_server.services.agent_graph_auth import require_native_graph_gm
from apps.live_control_server.services.graph_object_authoring_prepare import (
    decode_publication_intent,
    sign_publication_intent,
    verify_publication_intent,
)
from apps.live_control_server.integrations.dungeonmind import (
    native_registry_source as native,
)
from apps.live_control_server.integrations.worldkeeper import (
    registry_standing_consumer as wk,
)

SOURCE_PURPOSE = "dmb_native_pc_standing_source_v1"
CONFIRM_PURPOSE = "dmb_native_pc_standing_confirm_v1"


def _now():
    return datetime.now(UTC)


def _expiry():
    return (_now() + timedelta(hours=1)).isoformat()


def _signed_equal(token, packet, principal, purpose):
    decoded = decode_publication_intent(token, allow_expired_recovery=True)
    if (
        not hmac.compare_digest(wk.canonical(decoded), wk.canonical(packet))
        or packet.get("purpose") != purpose
        or packet.get("schema") != purpose
        or packet.get("principal") != principal.subject
    ):
        raise ValueError("prepared authentication scope mismatch")
    return datetime.fromisoformat(packet["expires_at"]) < _now()


def _operation(principal, bound, operation_id):
    return "dmb-standing:" + wk.digest(
        {
            "purpose": CONFIRM_PURPOSE,
            "principal": principal.subject,
            "world": bound["native_world_id"],
            "operation": str(operation_id),
        }
    )


def source(request, principal):
    require_native_graph_gm(principal)
    bound = native.binding(request.managed_world_id)
    rows = native.load_sources(request, bound)
    repo = native.repository()
    admitted = native.admit_sources(repo, request, bound, rows, principal.subject)
    context, access = native.access_context(repo, bound["native_world_id"])
    native.verify_sources(access, admitted)
    found = native.alternatives(repo, context, access, admitted)
    if (
        repo.get_head(bound["native_world_id"]).head_revision_id
        != context["revision_id"]
    ):
        raise ValueError("native head changed during source review")
    if native.binding(request.managed_world_id) != bound:
        raise ValueError("managed binding changed during source review")
    packet = {
        "schema": SOURCE_PURPOSE,
        "purpose": SOURCE_PURPOSE,
        "principal": principal.subject,
        "binding": bound,
        "request": request.model_dump(mode="json"),
        "rows": admitted,
        "context": context,
        "alternatives": found,
        "expires_at": _expiry(),
    }
    return {"source_packet": packet, "source_token": sign_publication_intent(packet)}


def _validate_current(repo, packet):
    request = SourceRequest.model_validate(packet["request"])
    bound = native.binding(request.managed_world_id)
    if bound != packet["binding"]:
        raise ValueError("managed binding changed")
    current = native.load_sources(request, bound)
    if [{k: v for k, v in r.items() if k != "body_text"} for r in current] != [
        {k: v for k, v in r.items() if k not in {"receipt", "evidence_ref_id"}}
        for r in packet["rows"]
    ]:
        raise ValueError("reviewed dossier closure changed")
    context, access = native.access_context(repo, bound["native_world_id"])
    if context != packet["context"]:
        raise ValueError("reviewed native context changed")
    native.verify_sources(access, packet["rows"])
    # Verify receipt authority, not only source opening or a caller-supplied ID.
    for row in packet["rows"]:
        receipt = repo.get_native_source_admission_receipt(
            bound["native_world_id"], row["receipt"]["admission_id"]
        )
        if receipt is None or receipt.model_dump(mode="json") != row["receipt"]:
            raise ValueError("source admission receipt changed")
    return bound


def _validate_reuse(packet, choices):
    for choice in choices:
        if choice.action != "use_existing":
            continue
        row = next(r for r in packet["rows"] if r["slug"] == choice.slug)
        found = packet["alternatives"][choice.slug]["targets"]
        target = next((t for t in found if t["entity_id"] == choice.entity_id), None)
        if target is None or not target["supported"]:
            raise ValueError(
                "reuse target lacks admitted support in reviewed alternatives"
            )
        assertions = target["entity"]["assertions"]
        has_name = any(
            a["predicate"] == "dnd5e:name" and a["value"].get("value") == row["name"]
            for a in assertions
        )
        has_pc = any(
            a["predicate"] == "dnd5e:classification"
            and a["value"].get("term") == "dnd5e:pc"
            for a in assertions
        )
        contradictory = any(
            a["predicate"] == "dnd5e:classification"
            and a["value"].get("term") == "dnd5e:npc"
            and any(s["value"] == "longmont-c1" for s in a["metadata"]["scope"])
            for a in assertions
        )
        if not has_name or not has_pc or contradictory:
            raise ValueError("reuse target lacks compatible name/PC-role support")


def prepare(request, principal):
    require_native_graph_gm(principal)
    packet = request.source_packet
    if _signed_equal(request.source_token, packet, principal, SOURCE_PURPOSE):
        raise ValueError("source review expired; refresh source review")
    verify_publication_intent(request.source_token, packet)
    repo = native.repository()
    operation = _operation(principal, packet["binding"], request.operation_id)
    if (
        repo.get_publication_receipt(packet["binding"]["native_world_id"], operation)
        is not None
    ):
        raise ValueError(
            "operation already committed; recover with original prepared packet"
        )
    bound = _validate_current(repo, packet)
    intent = wk.standing_intent(
        bound["native_world_id"], packet["rows"], request.choices
    )
    _validate_reuse(packet, request.choices)
    domain, profile = native.descriptors(
        repo, bound["native_world_id"], packet["context"]["revision_id"]
    )
    runtime = wk.runtime(repo, domain, profile, now=_now(), operation_id=operation)
    prepared = runtime.prepare_change(intent)
    # WK reads authority internally: compare its returned parent before signing.
    wk.verify_prepared_parent(prepared, packet["context"])
    if (
        prepared.prepared_operations != intent.operations
        or prepared.producer != intent.producer
    ):
        raise ValueError("WK returned a different standing intent")
    if native.binding(bound["managed_world_id"]) != bound:
        raise ValueError("managed binding changed during preparation")
    encoded = wk.encode_prepared(prepared)
    if wk.decode_prepared(encoded) != prepared:
        raise ValueError("prepared transport is not lossless")
    envelope = {
        "schema": CONFIRM_PURPOSE,
        "purpose": CONFIRM_PURPOSE,
        "principal": principal.subject,
        "source": packet,
        "choices": [c.model_dump(mode="json") for c in request.choices],
        "operation_id": str(request.operation_id),
        "prepared_id": operation,
        "prepared_codec": wk.CODEC,
        "prepared_digest": wk.digest(encoded),
        "expires_at": _expiry(),
    }
    return {
        "envelope": envelope,
        "prepared": encoded,
        "token": sign_publication_intent(envelope),
    }


def confirm(request, principal):
    require_native_graph_gm(principal)
    envelope = request.envelope
    expired = _signed_equal(request.token, envelope, principal, CONFIRM_PURPOSE)
    if envelope.get("prepared_codec") != wk.CODEC or envelope.get(
        "prepared_digest"
    ) != wk.digest(request.prepared):
        raise ValueError("prepared value authentication mismatch")
    prepared = wk.decode_prepared(request.prepared)
    source_packet = envelope["source"]
    if (
        source_packet["principal"] != principal.subject
        or source_packet["schema"] != SOURCE_PURPOSE
    ):
        raise ValueError("source principal/schema mismatch")
    bound = source_packet["binding"]
    if (
        prepared.prepared_change_id != envelope["prepared_id"]
        or prepared.dungeonmind_publication_id != envelope["prepared_id"]
        or prepared.space_id != bound["native_world_id"]
        or prepared.prepared_change_id
        != _operation(principal, bound, envelope["operation_id"])
    ):
        raise ValueError("prepared operation identity mismatch")
    wk.verify_prepared_parent(prepared, source_packet["context"])
    repo = native.repository()
    # Existing Core receipt/result authority is consulted BEFORE current source/head.
    completed = repo.get_prospective_publication(
        prepared.space_id, prepared.prepared_change_id
    )
    if expired and completed is None:
        raise ValueError("expired preparation has no committed receipt to recover")
    if completed is None:
        verify_publication_intent(request.token, envelope)
        _validate_current(repo, source_packet)
    domain, profile = resolve_dungeonbuddy_descriptors(
        domain_ref=DomainContractRef(
            domain_id=prepared.domain_contract_ref.authority_id,
            domain_revision=prepared.domain_contract_ref.revision,
            descriptor_sha256=prepared.domain_contract_ref.descriptor_sha256,
        ),
        profile_ref=SemanticProfileRef(
            profile_id=prepared.semantic_profile_ref.authority_id,
            profile_revision=prepared.semantic_profile_ref.revision,
            descriptor_sha256=prepared.semantic_profile_ref.descriptor_sha256,
        ),
    )
    runtime = wk.runtime(
        repo,
        domain,
        profile,
        now=prepared.prepared_at,
        operation_id=prepared.prepared_change_id,
    )
    result = runtime.commit_prepared_change(prepared, confirmed_by=principal.subject)
    from fastapi.encoders import jsonable_encoder

    return {
        "schema": "dmb_pc_standing_committed_v1",
        "recovered": completed is not None,
        "result": jsonable_encoder(result),
    }
