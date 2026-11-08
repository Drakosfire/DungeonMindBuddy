"""Native creature proposals via existing draft, Core admission and WK owners.

Core's deterministic publication receipt is the creation journal. No file-backed
publication ledger, alternative Graph store or new mechanics authority is added.
"""
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from dungeonmind.application.vnext import (
    get_prospective_publication, open_admitted_native_text,
    publish_native_text_source_evidence,
)
from dungeonmind.contracts.vnext.common import LabelsAllVisibility
from dungeonmind.contracts.vnext.native_source import (
    NativeTextEvidenceSpanRequestV1, NativeTextSourceAdmissionV1, NativeTextSourceOriginV1,
)
from worldkeeper.application import contracts as wk

from application_state.errors import ApplicationStateConflictError, ApplicationStateIntegrityError
from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
from apps.live_control_server.integrations.worldkeeper import registry_standing_consumer as transport
from apps.live_control_server.models.native_threat_creation import NativeThreatReview
from apps.live_control_server.services.agent_graph_auth import require_native_graph_gm
from apps.live_control_server.services.graph_object_authoring_prepare import (
    decode_publication_intent, sign_publication_intent,
)
from apps.live_control_server.services.threat_draft_store import get_threat_draft, locked_threat_draft
from graph_memory.vnext.domain_runtime import GM_LABEL

PRODUCER = "dungeonbuddy:native-threat-draft-v1"
ORIGIN = "dungeonbuddy.threat-draft"


def require(condition, message):
    if not condition:
        raise ApplicationStateConflictError(message)


def publication_id(draft_id):
    return "dmb-native-threat:v1:" + str(draft_id)


def body(draft):
    return f"# {draft.name}\n\nProposed creature; not an established played event.\n\n{draft.description}"


def owned_draft(root, draft_id, world_id):
    draft = get_threat_draft(root, str(draft_id))
    require(draft.schema_name == "dmb_threat_draft_v2" and draft.world_id == world_id,
            "Select a saved creature draft from this World")
    require(draft.workflow_state == "mechanics_saved" and draft.threat_kind == "creature",
            "Save creature mechanics before creating its native identity")
    return draft


def existing(repo, bound, draft_id):
    return get_prospective_publication(bound["native_world_id"], publication_id(draft_id), repository=repo)


def published(bound, draft_id, aggregate, *, replayed):
    # Core verifies receipt/result bindings. This consumer selects its one output;
    # it does not re-admit records or infer an identity from names.
    result = aggregate.prospective_result
    objects = [row for row in result.results if row.result_kind == "entity"]
    if len(objects) != 1 or objects[0].client_op_id != "creature":
        raise ApplicationStateIntegrityError("Native creature publication has an unexpected result")
    return dict(state="published", world_id=bound["managed_world_id"], draft_id=str(draft_id),
                native_world_id=bound["native_world_id"], binding_version=bound["binding_version"],
                node_id=objects[0].durable_id, publication_id=publication_id(draft_id),
                published_revision_id=result.published_revision_id, replayed=replayed)


def status(root, draft_id, world_id, principal):
    require_native_graph_gm(principal)
    owned_draft(root, draft_id, world_id)
    bound = native.binding(world_id)
    prior = existing(native.read_repository(), bound, draft_id)
    require(native.binding(world_id) == bound, "The World binding changed")
    return published(bound, draft_id, prior, replayed=True) if prior else None


def intent(review):
    metadata = wk.AssertionMetadata(
        scope=(), visibility=wk.Visibility("labels_any", (GM_LABEL,)),
        epistemic_basis="asserted", claim_mode="dungeonbuddy.claim:plan", standing="provisional",
        temporal_scope=wk.TemporalScope(kind="unknown"), evidence_ref_ids=(review.source_evidence_id,))
    return wk.WorldChangeIntent(review.binding["native_world_id"], PRODUCER, (
        wk.CreateObject("creature", (
            wk.CreateFact("creature.name", "dnd5e:name", wk.LiteralFactValue(review.label), metadata),
            wk.CreateFact("creature.kind", "dnd5e:classification",
                          wk.TermRefFactValue("dungeonbuddy:creature"), metadata),)),))


def source_matches(access, review):
    opened = open_admitted_native_text(access, review.source_evidence_id)
    require(opened.status == "available" and opened.body_sha256 == review.body_sha256
            and opened.source_artifact_id == review.source_artifact_id
            and opened.source_revision_id == review.source_revision_id
            and opened.span_start_byte == 0 and opened.span_sha256 == review.body_sha256
            and opened.span_end_byte == len(opened.body_text.encode()),
            "The exact proposed creature source is unavailable")


def prepare(root, draft_id, request, principal):
    require_native_graph_gm(principal)
    draft = owned_draft(root, draft_id, request.world_id)
    bound = native.binding(request.world_id)
    repo = native.repository()
    prior = existing(repo, bound, draft_id)
    if prior:
        require(native.binding(request.world_id) == bound, "The World binding changed")
        return published(bound, draft_id, prior, replayed=True)
    require(draft.version == request.expected_draft_version, "The creature draft changed; reopen it")
    text = body(draft)
    digest = sha256(text.encode()).hexdigest()
    admission_id = f"dmb-threat-source:{draft_id}:{draft.version}:{digest}"
    origin = NativeTextSourceOriginV1(namespace=ORIGIN, object_id=str(draft_id),
                                    revision_id=f"draft-version:{draft.version}")
    with locked_threat_draft(root, str(draft_id)) as current:
        require(current == draft, "The creature draft changed during review")
        context, _ = native.access_context(repo, bound["native_world_id"])
        domain, profile = native.descriptors(repo, bound["native_world_id"], context["revision_id"])
        admitted = repo.get_native_source_admission_receipt(bound["native_world_id"], admission_id)
        if admitted is None:
            require(native.binding(request.world_id) == bound, "The World binding changed")
            admitted = publish_native_text_source_evidence(repository=repo, domain_contract=domain,
                semantic_profile=profile, request=NativeTextSourceAdmissionV1(
                    space_id=bound["native_world_id"], admission_id=admission_id,
                    expected_parent_revision_id=context["revision_id"],
                    created_at=datetime.fromisoformat(draft.updated_at), body_text=text,
                    expected_body_sha256=digest, source_classification="dungeonbuddy.source:worldbuilding",
                    authority="primary", visibility=LabelsAllVisibility(labels=[GM_LABEL]), origin=origin,
                    spans=[NativeTextEvidenceSpanRequestV1(client_ref="whole-draft", evidence_role="support",
                        start_byte=0, end_byte=len(text.encode()), expected_slice_sha256=digest)]))
        require(admitted.origin == origin and admitted.space_id == bound["native_world_id"]
                and admitted.admission_id == admission_id and len(admitted.bindings) == 1
                and admitted.bindings[0].client_ref == "whole-draft", "The retained source receipt changed")
        context, access = native.access_context(repo, bound["native_world_id"])
        domain, profile = native.descriptors(repo, bound["native_world_id"], context["revision_id"])
        now = datetime.now(UTC)
        review = NativeThreatReview(world_id=draft.world_id, draft_id=draft_id, draft_version=draft.version,
            label=draft.name, body_sha256=digest, binding=bound, publication_id=publication_id(draft_id),
            source_evidence_id=admitted.bindings[0].evidence_ref_id,
            source_artifact_id=admitted.source_artifact_id, source_revision_id=admitted.source_revision_id,
            prepared_digest="0" * 64, principal=principal.subject, expires_at=now + timedelta(hours=1))
        source_matches(access, review)
        prepared = transport.runtime(repo, domain, profile, now=now,
            operation_id=publication_id(draft_id)).prepare_change(intent(review))
        transport.verify_prepared_parent(prepared, context)
        require(prepared.prepared_operations == intent(review).operations, "Prepared creature intent changed")
        require(native.binding(request.world_id) == bound, "The World binding changed during review")
        encoded = transport.encode_prepared(prepared)
        review = review.model_copy(update={"prepared_digest": transport.digest(encoded)})
        envelope = review.model_dump(mode="json", by_alias=True)
        return dict(state="prepared", source_text=text, review=envelope, prepared=encoded, token=sign_publication_intent(envelope))


def confirm(root, draft_id, request, principal):
    require_native_graph_gm(principal)
    review = request.review
    signed = decode_publication_intent(request.token, allow_expired_recovery=True)
    require(signed == review.model_dump(mode="json", by_alias=True)
            and review.principal == principal.subject and str(review.draft_id) == str(draft_id)
            and review.publication_id == publication_id(draft_id)
            and review.prepared_digest == transport.digest(request.prepared),
            "The creature confirmation differs from its exact review")
    bound = native.binding(review.world_id)
    require(bound == review.binding, "The reviewed World binding changed")
    repo = native.repository()
    prepared = transport.decode_prepared(request.prepared)
    require(prepared.space_id == bound["native_world_id"] and prepared.producer == PRODUCER
            and prepared.prepared_change_id == prepared.dungeonmind_publication_id == publication_id(draft_id)
            and prepared.prepared_operations == intent(review).operations,
            "The prepared creature differs from the reviewed intent")
    prior = existing(repo, bound, draft_id)
    if prior is None:
        decode_publication_intent(request.token)
        draft = owned_draft(root, draft_id, review.world_id)
        require(draft.version == review.draft_version and sha256(body(draft).encode()).hexdigest() == review.body_sha256,
                "The creature draft changed; prepare a new review")
        with locked_threat_draft(root, str(draft_id)) as current:
            require(current == draft, "The creature draft changed during confirmation")
            context, access = native.access_context(repo, bound["native_world_id"])
            transport.verify_prepared_parent(prepared, context)
            source_matches(access, review)
            require(native.binding(review.world_id) == bound, "The World binding changed")
            domain, profile = native.descriptors(repo, bound["native_world_id"], prepared.expected_parent_revision_id)
            transport.runtime(repo, domain, profile, now=prepared.prepared_at,
                operation_id=publication_id(draft_id)).commit_prepared_change(prepared, confirmed_by=principal.subject)
    else:
        domain, profile = native.descriptors(repo, bound["native_world_id"], prepared.expected_parent_revision_id)
        transport.runtime(repo, domain, profile, now=prepared.prepared_at,
            operation_id=publication_id(draft_id)).commit_prepared_change(prepared, confirmed_by=principal.subject)
    result = existing(repo, bound, draft_id)
    require(result is not None and native.binding(review.world_id) == bound,
            "Creature publication outcome needs recovery; keep the same review")
    return published(bound, draft_id, result, replayed=prior is not None)
