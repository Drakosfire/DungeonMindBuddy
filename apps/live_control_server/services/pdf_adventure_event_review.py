"""Reviewed adventure Events backed by immutable Build PDF evidence."""
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from dungeonmind.application.vnext import get_prospective_publication
from dungeonmind.application.vnext.native_pdf_access import bind_native_pdf_evidence
from dungeonmind.contracts.vnext.pdf_region import NativePdfRegionV1
from pydantic import BaseModel, ConfigDict, Field
from worldkeeper.application import contracts as wk

from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateUnavailableError,
)
from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
from apps.live_control_server.integrations.worldkeeper import registry_standing_consumer as transport
from apps.live_control_server.services.graph_object_authoring_prepare import (
    _prepare_binding_key,
    decode_publication_intent,
    sign_publication_intent,
)
from apps.live_control_server.services.native_pdf_evidence import register_pdf_regions
from apps.live_control_server.services.managed_world_graph_projection import resolve_managed_source_identity
from apps.live_control_server.services.world_container_registry import get_world_container
from apps.live_control_server.services.world_graph_binding import (
    WorldGraphBindingError, activate_native_source_graph,
)
from graph_memory.vnext.domain_runtime import GM_LABEL

PRODUCER = "dungeonbuddy:pdf-adventure-event-v1"


class EventPublicationRecoveryRequired(ApplicationStateUnavailableError):
    code = "event_publication_outcome_unknown"

    def __init__(self):
        super().__init__("Retry the exact confirmation to recover publication.")


class EventDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_id: UUID
    region: NativePdfRegionV1
    name: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=16000)


class EventConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    draft: EventDraft
    prepared: dict[str, Any]


def _publication_id(draft):
    return f"{PRODUCER}:{draft.operation_id}"


def _intent(space_id, draft, evidence_id):
    meta = wk.AssertionMetadata(
        scope=(),
        visibility=wk.Visibility("labels_any", (GM_LABEL,)),
        epistemic_basis="asserted",
        claim_mode="dungeonbuddy.claim:plan",
        standing="provisional",
        temporal_scope=wk.TemporalScope(kind="unknown"),
        evidence_ref_ids=(evidence_id,),
    )
    return wk.WorldChangeIntent(space_id, PRODUCER, (
        wk.CreateObject("event", (
            wk.CreateFact("event.name", "dnd5e:name", wk.LiteralFactValue(draft.name), meta),
            wk.CreateFact("event.kind", "dnd5e:classification", wk.TermRefFactValue("dnd5e:event"), meta),
            wk.CreateFact("event.description", "dnd5e:summary", wk.LiteralFactValue(draft.description), meta),
        )),
    ))


def prepare(world_id, draft, principal, *, authorize_write):
    if not draft.name.strip() or not draft.description.strip():
        raise ApplicationStateConflictError("Provide the Event name and reviewed text.")
    _prepare_binding_key()
    identity = resolve_managed_source_identity(world_id)
    bound = asdict(identity)
    space = identity.native_world_id
    repo = native.repository()
    publication_id = _publication_id(draft)
    if get_prospective_publication(space, publication_id, repository=repo) is not None:
        raise ApplicationStateConflictError("This Event operation is already published. Retry its confirmation.")
    now = datetime.now(UTC)
    context, access = native.access_context(repo, space)
    authorize_write()
    context, _, evidence_ids, _ = register_pdf_regions(
        repo, space, (draft.region,), context, access, now, authorize_write=authorize_write,
    )
    if resolve_managed_source_identity(world_id) != identity:
        raise ApplicationStateConflictError("The World binding changed during review.")
    domain, profile = native.descriptors(repo, space, context["revision_id"])
    prepared = transport.runtime(
        repo, domain, profile, now=now, operation_id=publication_id,
    ).prepare_change(_intent(space, draft, evidence_ids[0]))
    transport.verify_prepared_parent(prepared, context)
    encoded = transport.encode_prepared(prepared)
    envelope = {
        "purpose": PRODUCER,
        "binding": bound,
        "principal": principal.subject,
        "draft": draft.model_dump(mode="json"),
        "evidence_id": evidence_ids[0],
        "prepared_digest": transport.digest(encoded),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
    }
    return {"draft": envelope["draft"], "prepared": encoded, "token": sign_publication_intent(envelope)}


def confirm(world_id, request, principal, *, authorize_write):
    envelope = decode_publication_intent(request.token, allow_expired_recovery=True)
    identity = resolve_managed_source_identity(world_id)
    bound = asdict(identity)
    draft = request.draft
    if (
        envelope.get("purpose") != PRODUCER
        or envelope.get("binding") != bound
        or envelope.get("principal") != principal.subject
        or envelope.get("draft") != draft.model_dump(mode="json")
        or envelope.get("prepared_digest") != transport.digest(request.prepared)
    ):
        raise ApplicationStateConflictError("The confirmation differs from the reviewed Event.")
    space = bound["native_world_id"]
    repo = native.repository()
    publication_id = _publication_id(draft)
    prepared = transport.decode_prepared(request.prepared)
    evidence_id = envelope["evidence_id"]
    if (
        prepared.space_id != space
        or prepared.producer != PRODUCER
        or prepared.prepared_change_id != publication_id
        or prepared.dungeonmind_publication_id != publication_id
        or prepared.prepared_operations != _intent(space, draft, evidence_id).operations
    ):
        raise ApplicationStateConflictError("The prepared change differs from the reviewed Event.")
    prior = get_prospective_publication(space, publication_id, repository=repo)
    if prior is None:
        decode_publication_intent(request.token)
        context, access = native.access_context(repo, space)
        transport.verify_prepared_parent(prepared, context)
        evidence = bind_native_pdf_evidence(
            draft.region, authorized_space_id=space, audience=frozenset(),
            declared_labels=frozenset(), load=repo.get_native_pdf_source,
        )
        if evidence is None or evidence.evidence_ref_id != evidence_id or access.parsed.get_evidence(evidence_id) is None:
            raise ApplicationStateConflictError("The reviewed PDF region is unavailable.")
        if resolve_managed_source_identity(world_id) != identity:
            raise ApplicationStateConflictError("The World binding changed during confirmation.")
    domain, profile = native.descriptors(repo, space, prepared.expected_parent_revision_id)
    runtime = transport.runtime(
        repo, domain, profile, now=prepared.prepared_at, operation_id=publication_id,
    )
    authorize_write()
    runtime.commit_prepared_change(prepared, confirmed_by=principal.subject)
    aggregate = get_prospective_publication(space, publication_id, repository=repo)
    if aggregate is None or resolve_managed_source_identity(world_id) != identity:
        raise EventPublicationRecoveryRequired()
    result = aggregate.prospective_result
    if get_world_container(world_id).native_graph_binding.status == "provisioning":
        authorize_write()
        try:
            activate_native_source_graph(
                world_id, identity=identity, repository=repo,
                published_revision_id=result.published_revision_id,
            )
        except WorldGraphBindingError as exc:
            raise EventPublicationRecoveryRequired() from exc
    if resolve_managed_source_identity(world_id) != identity:
        raise EventPublicationRecoveryRequired()
    native.binding(world_id)
    entities = [entry for entry in result.results if entry.result_kind == "entity"]
    if len(entities) != 1 or entities[0].client_op_id != "event":
        raise ApplicationStateIntegrityError("The reviewed Event publication returned an unexpected result.")
    return {
        "node_id": entities[0].durable_id,
        "publication_id": publication_id,
        "published_revision_id": result.published_revision_id,
        "evidence_ref_id": evidence_id,
        "replayed": prior is not None,
    }
