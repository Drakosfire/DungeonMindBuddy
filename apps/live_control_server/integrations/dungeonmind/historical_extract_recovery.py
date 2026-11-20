"""Receipt-only ordinary extract recovery; package digests are NOT signatures.

Reconstruct original ordinary V2 publication correspondence from retained inputs
and exact immutable companions; never renew source admission or publish on a miss.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from apps.live_control_server.services.extract_promote import ExtractPromoteError


def _unsupported(reason: str) -> ExtractPromoteError:
    return ExtractPromoteError(
        f"Historical extract recipe is unsupported; retain the original request: {reason}.",
        code="publication_history_unsupported", status_code=409,
    )


def _invalid(reason: str) -> ExtractPromoteError:
    return ExtractPromoteError(
        f"Original extract packet failed integrity verification: {reason}.",
        code="plan_verification_failed", status_code=409,
    )


def validate_original_packet(package: Mapping[str, Any], selection: Sequence[str]) -> dict[str, Any]:
    """Prove carried consistency, never historical authenticity or permission.

    A caller can recompute this unkeyed digest. Only complete correspondence with
    the verified original terminal review can establish the requested history.
    This routine performs no authority, filesystem, source or database reads.
    """
    from graph_memory.extract_promote_proposal import (
        PromoteProposalError, PROMOTE_PROPOSAL_SCHEMA, verify_promote_proposal, verify_source_local_identity_basis,
    )
    from apps.live_control_server.models.extract_promote import SERVER_CONFIRMING_PRINCIPAL
    from apps.live_control_server.models.candidate_graph_admission import CandidateAdmissionBinding
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        _derive_confirm_operation_id, _require_sealed_identity_ledger, WorldGraphWriteError,
    )
    from apps.live_control_server.services.extract_promote import _PUBLICATION_TARGET_SCHEMA, _PUBLICATION_TARGET_KEY

    if not isinstance(package, Mapping):
        raise _invalid("package shape")
    if (not selection or any(not isinstance(item, str) or not item or item.strip() != item for item in selection)
            or len(set(selection)) != len(selection)):
        raise _invalid("explicit nonempty unique selection")
    try:
        version = int(package.get("proposal_version") or 0)
    except (TypeError, ValueError) as exc:
        raise _unsupported("proposal generation") from exc
    if package.get("schema") != PROMOTE_PROPOSAL_SCHEMA or version not in {2, 3}:
        raise _unsupported("proposal generation")
    frozen = deepcopy(dict(package))
    try:
        verified = verify_promote_proposal(frozen, confirming_principal=SERVER_CONFIRMING_PRINCIPAL,
                                           selected_assertion_ids=list(selection))
    except (PromoteProposalError, TypeError, ValueError, KeyError) as exc:
        raise _invalid("proposal/selection consistency") from exc
    effect = verified["effect"]
    slices = verified["contribution_slices"]
    if len(slices) != 1:
        raise _unsupported("multiple contribution slices")
    part = slices[0]
    meta = part.get("contribution_meta") or {}
    if meta.get("source_kind") != "source_extraction":
        raise _unsupported("non-extraction source")
    for field in ("source_proven_endpoint_basis", "recap_source_observation_basis", "recap_semantic_disposition"):
        if effect.get(field) is not None:
            raise _unsupported(field)
    target = effect.get(_PUBLICATION_TARGET_KEY)
    if (not isinstance(target, Mapping) or target.get("schema") != _PUBLICATION_TARGET_SCHEMA
            or target.get("native_world_id") != verified["world_id"]
            or not isinstance(target.get("managed_world_id"), str) or not target["managed_world_id"].strip()
            or type(target.get("binding_version")) is not int or target["binding_version"] < 1):
        raise _invalid("managed/native target identity")
    historical_context = effect.get("world_campaign_ingest_context")
    if historical_context is not None:
        # These are terminal-bound historical coordinates, not renewed proof
        # of current campaign membership or semantic acceptance.
        if (not isinstance(historical_context, Mapping)
                or historical_context.get("schema") != "dm_world_campaign_ingest_context_v1"
                or any(historical_context.get(key) != target.get(key) for key in
                       ("managed_world_id", "native_world_id", "binding_version"))
                or historical_context.get("head_revision_id") != verified["parent_revision_id"]
                or historical_context.get("campaign_id") != meta.get("campaign_scope")
                or not isinstance(historical_context.get("graph_payload_sha256"), str)
                or len(historical_context["graph_payload_sha256"]) != 64
                or any(char not in "0123456789abcdef" for char in historical_context["graph_payload_sha256"])):
            raise _invalid("historical Recap campaign coordinates")
    source = effect.get("source_admission")
    if not isinstance(source, Mapping):
        raise _unsupported("missing original source admission")
    for field in ("source_artifact_id", "source_revision_id", "buddy_source_revision_id", "content_sha256"):
        if not isinstance(source.get(field), str) or not source[field].strip():
            raise _unsupported("incomplete original source admission")
    pair = (source["source_artifact_id"], source["buddy_source_revision_id"])
    if pair != (verified["source_artifact_id"], verified["source_revision_id"]):
        raise _invalid("source admission coordinates")
    try:
        admission = CandidateAdmissionBinding.model_validate(effect.get("candidate_admission"))
        if (not admission.confirmable or admission.world_id != verified["world_id"]
                or admission.parent_revision_id != verified["parent_revision_id"]
                or (admission.source_artifact_id, admission.source_revision_id) != pair
                or admission.candidate_preview_id != verified["candidate_preview_id"]):
            raise ValueError("candidate coordinates")
        ledger = effect.get("identity_ledger")
        if (not isinstance(ledger, Mapping) or not isinstance(ledger.get("decisions"), list)
                or any(not isinstance(item, Mapping) for item in ledger["decisions"])):
            raise ValueError("identity ledger shape")
        _require_sealed_identity_ledger(frozen)
        verify_source_local_identity_basis(effect, require=True)
    except (TypeError, ValueError, KeyError, WorldGraphWriteError) as exc:
        raise _invalid("candidate/source-local/ledger correspondence") from exc
    basis = part.get("identity_basis") or {}
    nodes = basis.get("nodes") or {}
    if any(record.get("classification") != "source_local" for record in nodes.values()):
        raise _unsupported("non-source-local identity")
    for raw in [*(part.get("accepted_proposals") or []), *(part.get("rejected_assertions") or [])]:
        if (raw.get("source_artifact_id"), raw.get("source_revision_id")) != pair:
            raise _unsupported("multiple source pairs")
    return {
        "package": frozen, "verified": verified, "selection": tuple(selection),
        "source_admission": dict(source),
        "operation_id": _derive_confirm_operation_id(world_id=verified["world_id"], package=frozen,
                                                     assertion_ids=tuple(selection)),
    }


def _integrity(reason: str) -> ExtractPromoteError:
    return ExtractPromoteError(
        f"Historical extract persistence integrity failed: {reason}.",
        code="publication_integrity_failure", status_code=409,
    )


def reconstruct_original_candidate(
    carried: dict[str, Any], *, parent: Any, source_revision: Any | None = None,
) -> tuple[Any, Any, dict[str, Any], Any]:
    """Reproduce the ordinary producer using carried data and exact immutable inputs.

    No terminal candidate is accepted as an input. A metadata revision, when
    needed for older admission carriers, must be the one exact retained source
    revision; this is not permission to open its body or current catalog artifact.
    """
    from types import SimpleNamespace
    from dungeonmind.domain.canonical import canonical_sha256
    from apps.live_control_server.models.extract_promote import SERVER_CONFIRMING_PRINCIPAL
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes as writes
    from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package

    verified = carried["verified"]
    source = carried["source_admission"]
    world, parent_id = verified["world_id"], verified["parent_revision_id"]
    if parent is None:
        raise _integrity("missing immutable parent")
    envelope = parent.revision
    if (envelope.world_id != world or envelope.revision_id != parent_id
            or getattr(envelope.status, "value", envelope.status) != "published"
            or envelope.graph_schema != "dm_union_graph_v6"
            or not isinstance(parent.graph_payload, Mapping)
            or canonical_sha256(parent.graph_payload) != envelope.graph_payload_sha256):
        raise _integrity("immutable parent identity/payload")
    historical_context = verified["effect"].get("world_campaign_ingest_context")
    if historical_context is not None and (
            historical_context.get("graph_schema") != envelope.graph_schema
            or historical_context.get("graph_payload_sha256") != envelope.graph_payload_sha256):
        raise _integrity("historical Recap parent correspondence")
    locator = source.get("source_locator")
    if source_revision is not None:
        if (source_revision.source_revision_id != source["source_revision_id"]
                or source_revision.source_artifact_id != source["source_artifact_id"]
                or source_revision.content_sha256 != source["content_sha256"]):
            raise _integrity("immutable source revision identity")
        if locator is not None and locator != source_revision.locator:
            raise _integrity("immutable source revision locator")
        locator = source_revision.locator
    if not isinstance(locator, str) or not locator.strip():
        raise _unsupported("original admitted source locator unavailable")
    try:
        context = writes._mutation_context_from_sealed_package(
            stored=parent, package=carried["package"], world_id=world, head_revision_id=parent_id,
        )
    except (TypeError, ValueError, KeyError, writes.WorldGraphWriteError) as exc:
        raise _integrity("immutable parent context decoding") from exc
    _, original = resolve_merged_contribution_from_package(
        review_package=carried["package"], confirming_principal=SERVER_CONFIRMING_PRINCIPAL,
        world_id_hint=world, expected_parent_revision_id=parent_id,
        assertion_ids=carried["selection"], mutation_context=context,
    )
    pair = (source["source_artifact_id"], source["buddy_source_revision_id"])
    rows_by_id: dict[str, Any] = {}
    assertions = [*original.accepted_assertions, *original.candidate_assertions, *original.rejected_assertions]
    for assertion in assertions:
        if (assertion.source_artifact_id, assertion.source_revision_id) != pair:
            raise _unsupported("unbound source pair after original selection")
        value = assertion.value
        rows = value.get("evidence") if isinstance(value, dict) else None
        if not isinstance(rows, list):
            raise _unsupported("original Recap evidence rows unavailable")
        evidence = {}
        for row in rows:
            if (not isinstance(row, dict) or row.get("source_domain") not in {"recap", "session_recap"}
                    or row.get("source_artifact_id") != pair[0]
                    or not isinstance(row.get("evidence_ref_id"), str)):
                raise _unsupported("unproved Recap evidence domain/source")
            key = row["evidence_ref_id"]
            if key in evidence:
                raise _invalid("duplicate original evidence row")
            evidence[key] = row
            # Only fields used by the original evidence mapper participate in
            # operation-wide binding identity. Complete values remain in payload.
            binding = (pair, row.get("source_span_ref_id"))
            if key in rows_by_id and rows_by_id[key] != binding:
                raise _invalid("conflicting operation-wide evidence identity")
            rows_by_id[key] = binding
        if set(evidence) != set(assertion.evidence_ref_ids):
            raise _invalid("original evidence ID/row bijection")
    def artifact(artifact_id: str) -> Any:
        if artifact_id != pair[0]:
            raise _invalid("unexpected artifact lookup")
        return SimpleNamespace(source_domain="session_recap")
    def revision(revision_id: str) -> Any:
        if revision_id != source["source_revision_id"]:
            raise _invalid("unexpected revision lookup")
        return SimpleNamespace(locator=locator)
    candidate, states = writes._build_v2_candidate(
        original, context=context, pair_to_dm={pair: source["source_revision_id"]},
        produced_at=envelope.created_at,
        sources=SimpleNamespace(get_artifact=artifact, get_revision=revision),
    )
    if candidate.schema_version != "dm_graph_contribution_v2":
        raise _unsupported("non-ordinary contribution generation")
    return original, candidate, states, context


def expected_original_review(carried: dict[str, Any], *, parent: Any, source_revision: Any | None = None) -> tuple[Any, Any]:
    """Derive the complete ordinary V2 review, not an extract from recorded state."""
    from dungeonmind.application.contribution_review_v2 import _build_review_state
    from dungeonmind.contracts.contribution_review import (
        ContributionAssertionVerdict, ContributionPlanRef, derive_confirmation_id,
    )
    from dungeonmind.contracts.contribution_review_v2 import (
        CommitConfirmationReceiptV2, ContributionReviewIntentV2, ContributionReviewSubmissionV2,
        FINALIZE_REVIEW_V2_TOOL, contribution_v2_payload_sha256, derive_review_intent_sha256_v2,
    )
    from dungeonmind.contracts.semantic_profile import SemanticProfileRef
    from dungeonmind.domain.canonical import canonical_sha256
    from apps.live_control_server.models.extract_promote import SERVER_CONFIRMING_PRINCIPAL
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import _build_identity_dispositions

    original, candidate, states, _ = reconstruct_original_candidate(carried, parent=parent, source_revision=source_revision)
    package = carried["package"]
    proposals, verdicts = _build_identity_dispositions(candidate, states)
    assertions = [ContributionAssertionVerdict(assertion_id=item.assertion_id, acceptance_state=states[item.assertion_id])
                  for item in sorted(candidate.assertions, key=lambda item: item.assertion_id)]
    profile = parent.graph_payload.get("semantic_profile")
    if profile is None:
        raise _integrity("immutable parent profile missing")
    try:
        profile = SemanticProfileRef.model_validate(profile)
    except ValueError as exc:
        raise _integrity("immutable parent profile decoding") from exc
    plan = ContributionPlanRef(
        source_plan_schema=package["schema"], source_plan_id=package["proposal_id"],
        source_plan_sha256=package["proposal_digest"], source_input_sha256=canonical_sha256(package["effect"]),
        preview_content_sha256=canonical_sha256(package.get("preview") or {}),
        candidate_contribution_sha256=contribution_v2_payload_sha256(candidate),
        expected_parent_revision_id=parent.revision.revision_id, base_graph_schema=parent.revision.graph_schema,
        base_graph_payload_sha256=parent.revision.graph_payload_sha256,
        semantic_profile=profile,
    )
    at = parent.revision.created_at
    fields = dict(operation_id=carried["operation_id"], world_id=carried["verified"]["world_id"],
        campaign_id=original.campaign_scope or None, plan_ref=plan, candidate_contribution=candidate,
        identity_proposals=proposals, identity_verdicts=verdicts, assertion_verdicts=assertions,
        reviewer_id=SERVER_CONFIRMING_PRINCIPAL, reviewed_at=at)
    digest = derive_review_intent_sha256_v2(**fields, reviewed_identity_preconditions=None)
    intent = ContributionReviewIntentV2(**fields, review_intent_sha256=digest)
    confirmation = CommitConfirmationReceiptV2(
        confirmation_id=derive_confirmation_id(operation_id=carried["operation_id"], review_intent_sha256=digest,
            actor=SERVER_CONFIRMING_PRINCIPAL, confirmed_at=at),
        operation_id=carried["operation_id"], review_intent_sha256=digest, actor=SERVER_CONFIRMING_PRINCIPAL,
        tool_name=FINALIZE_REVIEW_V2_TOOL, effect="commit", world_id=fields["world_id"],
        campaign_id=fields["campaign_id"], expected_parent_revision_id=parent.revision.revision_id, confirmed_at=at,
    )
    return original, _build_review_state(ContributionReviewSubmissionV2(intent=intent, confirmation=confirmation))


def verify_original_review(carried: dict[str, Any], *, history: Any, parent: Any,
                           source_revision: Any | None = None) -> Any:
    """Prove every original effect/preview/selection/review commitment in full."""
    _require_normal_review(history)
    original, expected = expected_original_review(carried, parent=parent, source_revision=source_revision)
    if history.review.model_dump(mode="json") != expected.model_dump(mode="json"):
        raise _integrity("complete original review correspondence")
    publication = history.publication
    if (publication.expected_parent_revision_id != parent.revision.revision_id
            or publication.parent_graph_payload_sha256 != parent.revision.graph_payload_sha256
            or publication.graph_schema != parent.revision.graph_schema
            or publication.published_at != parent.revision.created_at
            or history.revision.created_at != parent.revision.created_at):
        raise _integrity("original publication parent/time correspondence")
    return original



def _require_normal_review(history: Any) -> None:
    from dungeonmind.contracts.contribution_review_v2 import ContributionReviewStateV2, ContributionReviewRecordV2
    if type(history.review) is not ContributionReviewStateV2 or type(history.review.record) is not ContributionReviewRecordV2:
        raise _unsupported("terminal review generation or guarded review")
    if (history.review.candidate_contribution.diagnostics or {}).get("reviewed_extract_confirmation") is not None:
        raise _unsupported("independent reviewed-extract confirmation")

def authorize_current_target(carried: dict[str, Any]) -> tuple[str, str, int]:
    """Current local-operator World binding fence, independent of source/head."""
    from apps.live_control_server.services import extract_promote as service
    target = carried["verified"]["effect"][service._PUBLICATION_TARGET_KEY]
    try:
        current = service._resolve_publication_target(target["managed_world_id"])
    except ExtractPromoteError as exc:
        if exc.status_code >= 500:
            raise ExtractPromoteError("Original publication target storage is unavailable; retain the request.",
                code="authority_unavailable", status_code=503) from exc
        raise ExtractPromoteError("Original publication target is unavailable; retain the request.",
            code="publication_target_changed", status_code=409) from exc
    if service._target_basis(current) != target:
        raise ExtractPromoteError("Original publication target binding changed; retain the request.",
            code="publication_target_changed", status_code=409)
    return current.managed_world_id, current.native_world_id, current.binding_version


def _bare_readers() -> tuple[Any, Any, Any]:
    from dungeonmind.infrastructure.postgres import PostgresDatabase, PostgresWorldGraphRepository, PostgresSourceRepository
    from dungeonmind.infrastructure.postgres.review_publication import PostgresFinalizedReviewPublicationRepository
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import _require_database_url
    database = PostgresDatabase(_require_database_url(None))
    return (PostgresFinalizedReviewPublicationRepository(database),
            PostgresWorldGraphRepository(database), PostgresSourceRepository(database))


def recover_original_confirmation(request: Any) -> Any:
    """Return only a completely verified original receipt; absence cannot write.

    Existing hosting policy authorizes local operator calls and denies these
    classic endpoints in hosted mode. This function grants no new hosted access.
    """
    from dungeonmind.application.compatibility import read_historical_finalized_publication
    from graph_memory.extract_promote_proposal import PromoteProposalError
    from graph_memory.candidate_graph_to_contribution import CandidateGraphMappingError
    from pydantic import ValidationError
    from dungeonmind.domain.errors import CapabilityDeniedError, PersistenceIntegrityError, PersistenceUnavailableError
    from apps.live_control_server.models.extract_promote import ExtractPromoteConfirmReceipt
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import _affected_ids_from_contribution, WorldGraphWriteError

    carried = validate_original_packet(request.review_package, request.assertion_ids)
    binding = authorize_current_target(carried)
    world = carried["verified"]["world_id"]
    try:
        reader, graph, sources = _bare_readers()
        history = read_historical_finalized_publication(world, carried["operation_id"], reader=reader)
        if history is None:
            raise ExtractPromoteError("No original publication receipt exists; retain the request.",
                code="publication_receipt_unavailable", status_code=409)
        _require_normal_review(history)
        try:
            parent = graph.get_revision(world, carried["verified"]["parent_revision_id"])
            source = sources.get_revision(carried["source_admission"]["source_revision_id"])
        except (TypeError, ValueError, KeyError) as exc:
            raise _integrity("immutable companion decoding") from exc
        if source is None:
            raise _integrity("missing immutable source revision")
        verify_original_review(carried, history=history, parent=parent, source_revision=source)
    except PersistenceUnavailableError as exc:
        raise ExtractPromoteError("Historical extract storage is unavailable; retain the request.",
            code="authority_unavailable", status_code=503) from exc
    except PersistenceIntegrityError as exc:
        raise _integrity("stored terminal aggregate") from exc
    except CapabilityDeniedError as exc:
        raise _unsupported("terminal aggregate generation") from exc
    except WorldGraphWriteError as exc:
        if exc.code == "authority_unavailable":
            raise ExtractPromoteError("Historical extract storage is unavailable; retain the request.",
                code="authority_unavailable", status_code=503) from exc
        raise _invalid("original producer correspondence") from exc
    except (PromoteProposalError, CandidateGraphMappingError, ValidationError) as exc:
        raise _invalid("original producer contract") from exc
    if authorize_current_target(carried) != binding:
        raise ExtractPromoteError("Original publication target binding changed; retain the request.",
            code="publication_target_changed", status_code=409)
    accepted, affected = _affected_ids_from_contribution(history.review.reviewed_contribution)
    return ExtractPromoteConfirmReceipt(
        outcome="already_applied", world_id=world,
        proposal_id=carried["package"]["proposal_id"], proposal_digest=carried["package"]["proposal_digest"],
        parent_revision_id=carried["verified"]["parent_revision_id"],
        committed_revision_id=history.publication.published_revision_id,
        head_advanced=False, selected_assertion_ids=list(carried["selection"]),
        accepted_assertion_ids=accepted, affected_object_ids=affected, applied_assertion_count=len(accepted),
        audit_status="ok", warnings=[],
    )
