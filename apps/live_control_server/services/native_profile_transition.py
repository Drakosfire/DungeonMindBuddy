"""Explicit graph-only additive profile adoption with immutable receipt recovery."""

from datetime import UTC, datetime
import hmac

from dungeonmind.application.vnext.authority import (
    revision_from_command,
    verify_stored_revision,
)
from dungeonmind.application.vnext.errors import (
    KnowledgePublicationIdempotencyConflictError,
)
from dungeonmind.application.vnext.profile_transition import (
    transition_knowledge_semantic_profile,
)
from dungeonmind.application.vnext.publication import get_publication_receipt
from dungeonmind.application.vnext.admission import (
    domain_declaration_passes,
    semantic_profile_passes,
)
from dungeonmind.application.vnext.builder import build_parsed_knowledge_revision
from dungeonmind.application.vnext.materialization import (
    NATIVE_VNEXT_GRAPH_SCHEMA,
    decode_native_graph_payload,
)
from dungeonmind.contracts.semantic_profile import SemanticProfileRef
from dungeonmind.contracts.vnext.domain import DomainContractRef
from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand
from dungeonmind.contracts.vnext.profile_transition import KnowledgeProfileTransitionV1
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.domain.errors import PersistenceIntegrityError

from apps.live_control_server.integrations.dungeonmind import (
    native_registry_source as native,
)
from apps.live_control_server.models.native_profile_transition import (
    ProfileTransitionConfirm,
    ProfileTransitionContent,
    ProfileTransitionPrepare,
    SignedProfileTransition,
)
from apps.live_control_server.services.agent_graph_auth import require_native_graph_gm
from apps.live_control_server.services.graph_object_authoring_prepare import (
    PREPARE_TTL,
    sign_publication_intent,
    _prepare_binding_key,
)
from apps.live_control_server.services.hosted_native_graph_access import (
    require_explorer_access,
)
from graph_memory.vnext.domain_runtime import (
    DUNGEONBUDDY_DOMAIN_DIGEST,
    DUNGEONBUDDY_MANUAL_PROFILE_DIGEST,
    dungeonbuddy_world_domain_contract,
    dungeonbuddy_dnd5e_manual_profile,
    resolve_dungeonbuddy_descriptors,
)


class TransitionRefused(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require(condition, code):
    if not condition:
        raise TransitionRefused(code)


def _binding(principal, world, space, version):
    require_native_graph_gm(principal)
    require_explorer_access(principal, world)
    bound = native.binding(world)
    _require(
        bound["native_world_id"] == space and bound["binding_version"] == version,
        "profile_transition_binding_changed",
    )
    return bound


def _refs():
    domain = dungeonbuddy_world_domain_contract()
    target = dungeonbuddy_dnd5e_manual_profile()
    domain_ref = DomainContractRef(
        domain_id=domain.domain_id,
        domain_revision=domain.domain_revision,
        descriptor_sha256=DUNGEONBUDDY_DOMAIN_DIGEST,
    )
    target_ref = SemanticProfileRef(
        profile_id=target.profile_id,
        profile_revision=target.profile_revision,
        descriptor_sha256=DUNGEONBUDDY_MANUAL_PROFILE_DIGEST,
    )
    domain, target = resolve_dungeonbuddy_descriptors(
        domain_ref=domain_ref, profile_ref=target_ref
    )
    return domain, target, domain_ref, target_ref


def _descriptors(request):
    domain, target, domain_ref, target_ref = _refs()
    _require(
        request.domain_contract_ref == domain_ref
        and request.to_profile_ref == target_ref,
        "profile_transition_descriptor_mismatch",
    )
    _, current = resolve_dungeonbuddy_descriptors(
        domain_ref=request.domain_contract_ref, profile_ref=request.from_profile_ref
    )
    _require(
        current.profile_revision in {"2", "3"},
        "profile_transition_from_profile_unsupported",
    )
    return domain, current, target


def _parent(repo, request):
    parent = repo.get_revision(request.space_id, request.expected_parent_revision_id)
    if parent is None:
        raise PersistenceIntegrityError("profile transition original parent missing")
    verify_stored_revision(parent)
    revision = parent.revision
    if (
        revision.space_id != request.space_id
        or revision.revision_id != request.expected_parent_revision_id
        or revision.domain_contract_ref != request.domain_contract_ref
        or revision.semantic_profile_ref != request.from_profile_ref
        or revision.graph_schema != NATIVE_VNEXT_GRAPH_SCHEMA
    ):
        raise PersistenceIntegrityError(
            "profile transition original parent authority mismatch"
        )
    return parent


def _expected(repo, plan):
    request = plan.request
    parent = _parent(repo, request)
    if (
        parent.graph_payload_sha256 != plan.parent_payload_sha256
        or parent.revision.migration_origin_ref != plan.migration_origin_ref
    ):
        raise PersistenceIntegrityError(
            "profile transition original payload or origin mismatch"
        )
    return PublishKnowledgeRevisionCommand(
        space_id=request.space_id,
        parent_revision_id=request.expected_parent_revision_id,
        expected_parent_revision_id=request.expected_parent_revision_id,
        operation_ids=[request.publication_id],
        graph_schema=parent.revision.graph_schema,
        graph_payload=parent.graph_payload,
        domain_contract_ref=request.domain_contract_ref,
        semantic_profile_ref=request.to_profile_ref,
        migration_origin_ref=parent.revision.migration_origin_ref,
        created_at=request.created_at,
    )


def _verify_receipt(repo, plan, receipt, command):
    request = plan.request
    if receipt.command_sha256 != canonical_sha256(command.model_dump(mode="json")):
        raise KnowledgePublicationIdempotencyConflictError(
            space_id=request.space_id, publication_id=request.publication_id
        )
    expected = revision_from_command(command)
    child = repo.get_revision(request.space_id, receipt.published_revision_id)
    if child is None:
        raise PersistenceIntegrityError("profile transition committed child missing")
    verify_stored_revision(child)
    if (
        receipt.space_id != request.space_id
        or receipt.publication_id != request.publication_id
        or receipt.expected_parent_revision_id != request.expected_parent_revision_id
        or receipt.published_revision_id != expected.revision_id
        or receipt.graph_payload_sha256 != plan.parent_payload_sha256
        or child.graph_payload != command.graph_payload
        or canonical_sha256(child.revision.model_dump(mode="json"))
        != canonical_sha256(expected.model_dump(mode="json"))
    ):
        raise PersistenceIntegrityError(
            "profile transition committed command or child mismatch"
        )


def prepare(body, principal):
    body = ProfileTransitionPrepare.model_validate(body.model_dump(mode="json"))
    _binding(
        principal,
        body.managed_world_id,
        body.expected_native_world_id,
        body.expected_binding_version,
    )
    _prepare_binding_key()  # Availability before any expensive Core graph reads.
    repo = native.repository()
    head = repo.get_head(body.expected_native_world_id)
    _require(head is not None, "profile_transition_head_missing")
    _require(
        head.head_revision_id == body.expected_parent_revision_id,
        "profile_transition_parent_stale",
    )
    stored = repo.get_revision(
        body.expected_native_world_id, body.expected_parent_revision_id
    )
    if stored is None:
        raise PersistenceIntegrityError("profile transition selected revision missing")
    verify_stored_revision(stored)
    domain, target, domain_ref, target_ref = _refs()
    now = datetime.now(UTC)
    request = KnowledgeProfileTransitionV1(
        space_id=body.expected_native_world_id,
        publication_id=body.publication_id,
        expected_parent_revision_id=body.expected_parent_revision_id,
        domain_contract_ref=domain_ref,
        from_profile_ref=stored.revision.semantic_profile_ref,
        to_profile_ref=target_ref,
        created_at=now,
    )
    _descriptors(request)
    _parent(repo, request)
    parsed = build_parsed_knowledge_revision(
        stored.revision,
        decoded_content=decode_native_graph_payload(stored.graph_payload),
    )
    _require(
        all(
            domain_declaration_passes(a, domain_contract=domain) is None
            and semantic_profile_passes(a, semantic_profile=target) is None
            for a in parsed.assertions_by_id.values()
        ),
        "profile_transition_target_rejects_existing_assertion",
    )
    plan = ProfileTransitionContent(
        managed_world_id=body.managed_world_id,
        native_world_id=body.expected_native_world_id,
        binding_version=body.expected_binding_version,
        request=request,
        parent_payload_sha256=stored.graph_payload_sha256,
        migration_origin_ref=stored.revision.migration_origin_ref,
        prepared_by=principal.subject,
        expires_at=now + PREPARE_TTL,
    )
    final = repo.get_head(body.expected_native_world_id)
    _require(final == head, "profile_transition_parent_stale")
    _binding(
        principal,
        body.managed_world_id,
        body.expected_native_world_id,
        body.expected_binding_version,
    )
    return {
        "plan": SignedProfileTransition(
            **plan.model_dump(),
            token=sign_publication_intent(plan.model_dump(mode="json", by_alias=True)),
        ).model_dump(mode="json", by_alias=True)
    }


def confirm(body, principal):
    body = ProfileTransitionConfirm.model_validate(body.model_dump(mode="json"))
    plan = body.plan
    _binding(
        principal, plan.managed_world_id, plan.native_world_id, plan.binding_version
    )
    content = ProfileTransitionContent.model_validate(
        plan.model_dump(exclude={"token"})
    )
    _require(
        hmac.compare_digest(
            plan.token,
            sign_publication_intent(content.model_dump(mode="json", by_alias=True)),
        ),
        "profile_transition_signature_invalid",
    )
    _require(
        plan.prepared_by == principal.subject, "profile_transition_principal_changed"
    )
    domain, current, target = _descriptors(plan.request)
    repo = native.repository()
    receipt = get_publication_receipt(
        plan.native_world_id, plan.request.publication_id, repository=repo
    )
    command = _expected(repo, plan)
    if receipt is not None:
        _verify_receipt(repo, plan, receipt, command)
        _binding(
            principal, plan.managed_world_id, plan.native_world_id, plan.binding_version
        )
        return {
            "schema": "dmb_native_profile_transition_receipt_v1",
            "recovered": True,
            "receipt": receipt.model_dump(mode="json"),
        }
    _require(datetime.now(UTC) <= plan.expires_at, "profile_transition_review_expired")
    head = repo.get_head(plan.native_world_id)
    if (
        head is not None
        and head.head_revision_id != plan.request.expected_parent_revision_id
    ):
        stored = repo.get_revision(plan.native_world_id, head.head_revision_id)
        if (
            stored is not None
            and stored.revision.semantic_profile_ref == plan.request.to_profile_ref
        ):
            raise TransitionRefused(
                "profile_transition_already_adopted_without_receipt"
            )
        raise TransitionRefused("profile_transition_parent_stale")

    class GuardedRepository:
        denied = None

        def __getattr__(self, name):
            if self.denied is not None:
                raise self.denied
            return getattr(repo, name)

        def publish_publication(self, request, publication_id):
            try:
                _binding(
                    principal,
                    plan.managed_world_id,
                    plan.native_world_id,
                    plan.binding_version,
                )
            except Exception as exc:
                self.denied = exc
                raise
            return repo.publish_publication(request, publication_id)

    guarded = GuardedRepository()
    try:
        receipt = transition_knowledge_semantic_profile(
            repository=guarded,
            request=plan.request,
            domain_contract=domain,
            current_profile=current,
            target_profile=target,
        )
    except Exception:
        # Core's lost-ack probe must not turn host denial into an ambiguous write
        # or perform further receipt IO after permission/binding was revoked.
        if guarded.denied is not None:
            raise guarded.denied from None
        raise
    _verify_receipt(repo, plan, receipt, command)
    _binding(
        principal, plan.managed_world_id, plan.native_world_id, plan.binding_version
    )
    return {
        "schema": "dmb_native_profile_transition_receipt_v1",
        "recovered": False,
        "receipt": receipt.model_dump(mode="json"),
    }
