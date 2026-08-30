"""Existing-world worldbuilding prepare → confirm (CUTOVER D.2B).

Owns the mounted worldbuilding authority boundary. First-world/bootstrap lives
in ``first_world_graph_publication.py``. Product code talks only to
``WorldGraphAuthority``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from typing import Any, Mapping

from apps.live_control_server import config as live_config
from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
    worldbuilding_authority_operation_id,
)
from apps.live_control_server.models.extract_promote import (
    PRODUCT_CONFIRM_ALLOW_LIVE_WORLD,
    PRODUCT_CONFIRM_DRY_RUN,
    WORLD_BUILDING_WRITE_PLAN_SCHEMA,
    WORLD_BUILDING_WRITE_PLAN_SCHEMA_V1,
    ConfirmAuditStatus,
    WorldbuildingWritePlanConfirmReceipt,
    WorldbuildingWritePlanConfirmRequest,
    WorldbuildingWritePlanPrepareRequest,
    WorldbuildingWritePlanResponse,
)
from apps.live_control_server.ports.world_graph_authority import (
    WorldGraphAuthority,
    WorldGraphAuthorityError,
    WorldGraphPublicationReceipt,
    WorldGraphPublishRequest,
)
from apps.live_control_server.ports.world_graph_authority_access import (
    get_world_graph_authority,
)
from apps.live_control_server.services.extract_promote import (
    ExtractPromoteError,
    _diagnostic,
    _load_typed_worldbuilding_preview_for_run,
)
from apps.live_control_server.services.promotable_ingest_run import (
    PromotableIngestRunError,
    resolve_promotable_ingest_run,
)
from graph_memory.extract_promote_ops import DEFAULT_WORLD_ID
from graph_memory.worldbuilding_write_plan import (
    WorldbuildingDispositionInput,
    WorldbuildingWritePlanError,
    WorldbuildingWritePlanVerificationContext,
    build_worldbuilding_write_plan,
    materialize_worldbuilding_contribution,
    verify_worldbuilding_write_plan,
)

_PORT_ERROR_MAP: dict[str, tuple[str, int]] = {
    "authority_unavailable": ("authority_unavailable", 503),
    "revision_unavailable": ("world_not_initialized", 409),
    "stale_parent": ("stale_parent_revision", 409),
    "integrity_failure": ("publication_integrity_failure", 409),
    "inexpressible": ("dungeonmind_inexpressible", 409),
    "publication_failed": ("merge_did_not_publish", 409),
}

_PREPARE_BINDING_SCHEMA = "dmb_worldbuilding_prepare_binding_v1"
_PREPARE_BINDING_KEY_ENV = "DMB_WORLDBUILDING_PREPARE_BINDING_KEY"
_PROCESS_PREPARE_BINDING_KEY = secrets.token_bytes(32)


def _promotable_run_error(exc: PromotableIngestRunError) -> ExtractPromoteError:
    from apps.live_control_server.services.extract_promote import (
        _promotable_run_error as mapped,
    )

    return mapped(exc)


def _authority_error(exc: WorldGraphAuthorityError) -> ExtractPromoteError:
    code, status = _PORT_ERROR_MAP.get(exc.code, ("authority_unavailable", 503))
    if exc.code == "stale_parent":
        message = "expected parent revision is not the current World Graph head"
    elif exc.code == "revision_unavailable":
        message = "The World Graph is not initialized."
    else:
        message = str(exc)
    return ExtractPromoteError(
        message,
        code=code,
        status_code=status,
        diagnostics=[_diagnostic(code, message)],
    )


def _write_plan_error(exc: WorldbuildingWritePlanError) -> ExtractPromoteError:
    return ExtractPromoteError(
        str(exc),
        code=exc.code,
        status_code=exc.status_code,
        diagnostics=[_diagnostic(exc.code, str(exc))],
    )


def _legacy_reprepare_error() -> ExtractPromoteError:
    return ExtractPromoteError(
        "worldbuilding v1 plans have no sealed identity authority; re-prepare",
        code="legacy_plan_reprepare_required",
        status_code=409,
        diagnostics=[
            _diagnostic(
                "legacy_plan_reprepare_required",
                "worldbuilding v1 plans have no sealed identity authority; re-prepare",
            )
        ],
    )


def _identity_snapshot_digest(snapshot: Mapping[str, Any]) -> str:
    payload = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _prepare_binding_key() -> bytes:
    explicit = os.environ.get(_PREPARE_BINDING_KEY_ENV, "").strip()
    if explicit:
        return hashlib.sha256(
            f"{_PREPARE_BINDING_SCHEMA}:{explicit}".encode("utf-8")
        ).digest()
    return _PROCESS_PREPARE_BINDING_KEY


def _prepare_binding_message(
    *,
    world_id: str,
    parent_revision_id: str,
    plan_id: str,
    plan_digest: str,
    identity_snapshot_digest: str,
) -> bytes:
    payload = json.dumps(
        {
            "schema": _PREPARE_BINDING_SCHEMA,
            "world_id": world_id,
            "parent_revision_id": parent_revision_id,
            "plan_id": plan_id,
            "plan_digest": plan_digest,
            "identity_snapshot_digest": identity_snapshot_digest,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return payload.encode("utf-8")


def _sign_prepare_binding(
    *,
    world_id: str,
    parent_revision_id: str,
    plan_id: str,
    plan_digest: str,
    identity_snapshot_digest: str,
) -> str:
    digest = hmac.new(
        _prepare_binding_key(),
        _prepare_binding_message(
            world_id=world_id,
            parent_revision_id=parent_revision_id,
            plan_id=plan_id,
            plan_digest=plan_digest,
            identity_snapshot_digest=identity_snapshot_digest,
        ),
        hashlib.sha256,
    ).hexdigest()
    return f"v1.{digest}"


def _require_prepare_binding(
    plan: WorldbuildingWritePlanResponse,
    snapshot: Mapping[str, Any],
) -> None:
    expected = _sign_prepare_binding(
        world_id=str(plan.world_id),
        parent_revision_id=str(plan.parent_revision_id),
        plan_id=str(plan.plan_id),
        plan_digest=str(plan.plan_digest),
        identity_snapshot_digest=_identity_snapshot_digest(snapshot),
    )
    provided = str(getattr(plan, "prepare_binding", None) or "").strip()
    if not provided or not hmac.compare_digest(provided, expected):
        raise ExtractPromoteError(
            "identity snapshot was not sealed by prepare on this server",
            code="identity_snapshot_inexpressible",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "identity_snapshot_inexpressible",
                    "identity snapshot was not sealed by prepare on this server",
                )
            ],
        )


def _relationship_predicate_matches(published: str, expected: str) -> bool:
    """True when the native child edge is the accepted Buddy fact.

    DungeonMind may store a mapped vocabulary term (``linked_to`` →
    ``associated_with``). That is expression, not a dropped assertion.
    """
    if published == expected:
        return True
    published_tail = published.rsplit(":", 1)[-1]
    expected_tail = expected.rsplit(":", 1)[-1]
    if published_tail == expected or published_tail == expected_tail:
        return True
    from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
        resolve_buddy_predicate_mapping_v4,
    )

    mapping = resolve_buddy_predicate_mapping_v4(expected)
    if mapping is None or not mapping[0]:
        return False
    dm_predicate = mapping[0]
    return published == dm_predicate or published_tail == dm_predicate.rsplit(":", 1)[-1]


def _attribute_evidence_ids(assertion: Any, reviewed_contribution_id: str) -> list[str]:
    ids: list[str] = []
    for item in list(getattr(assertion, "evidence_ref_ids", None) or []):
        text = str(item).strip()
        if text:
            ids.append(text)
    subject = str(getattr(assertion, "subject_node_id", "") or "")
    contribution_id = str(reviewed_contribution_id or "").strip()
    if contribution_id and subject:
        fallback = f"evidence:{contribution_id}:{subject}"
        if fallback not in ids:
            ids.append(fallback)
    return ids


def _evidence_id_on_child(present: set[str], expected_id: str) -> bool:
    """True when the child carries the expected evidence id or its DM v1 rewrite.

    DungeonMind adoption/publication may suffix Buddy evidence ids with
    ``:dmv1:<binding sha256>`` (export identity). Exact id match remains valid.
    """
    if expected_id in present:
        return True
    marker = f"{expected_id}:dmv1:"
    return any(item.startswith(marker) for item in present)


def _identity_snapshot_payload(plan: WorldbuildingWritePlanResponse) -> dict[str, Any]:
    authority = plan.effect.identity_authority
    if authority is None:
        raise _legacy_reprepare_error()
    payload = authority.model_dump(mode="json", by_alias=False)
    schema = payload.pop("schema_", None) or payload.get("schema")
    if schema:
        payload["schema"] = schema
    return payload


def _confirm_receipt(
    *,
    outcome: str,
    verified: Mapping[str, Any],
    contribution: Any,
    parent_revision_id: str,
    committed_revision_id: str,
    head_advanced: bool,
    accepted_assertion_ids: list[str],
    rejected_assertion_ids: list[str],
    audit_status: ConfirmAuditStatus,
    warnings: list[str],
) -> WorldbuildingWritePlanConfirmReceipt:
    unresolved_mention_ids = [
        mention.mention_id for mention in contribution.unresolved_mentions
    ]
    return WorldbuildingWritePlanConfirmReceipt(
        outcome=outcome,  # type: ignore[arg-type]
        world_id=str(verified["world_id"]),
        plan_id=str(verified["plan_id"]),
        plan_digest=str(verified["plan_digest"]),
        decision_digest=str(verified["decision_digest"]),
        parent_revision_id=parent_revision_id,
        committed_revision_id=committed_revision_id,
        head_advanced=head_advanced,
        contribution_id=contribution.contribution_id,
        applied_assertion_count=len(accepted_assertion_ids),
        accepted_assertion_ids=list(accepted_assertion_ids),
        rejected_assertion_ids=list(rejected_assertion_ids),
        unresolved_mention_ids=unresolved_mention_ids,
        audit_status=audit_status,
        warnings=list(warnings),
    )


def _verify_worldbuilding_child(
    authority: WorldGraphAuthority,
    *,
    receipt: WorldGraphPublicationReceipt,
    contribution: Any,
    verified: Mapping[str, Any],
    parent: str,
    materialized_accepted: list[str],
) -> tuple[str, list[str]]:
    """Prove accepted worldbuilding facts and receipt bindings on the child."""
    codes: list[str] = []
    if receipt.world_id != str(verified["world_id"]):
        codes.append("receipt_world_mismatch")
    if receipt.parent_revision_id != parent:
        codes.append("receipt_parent_mismatch")
    if tuple(receipt.accepted_assertion_ids) != tuple(materialized_accepted):
        codes.append("accepted_assertion_ids_mismatch")
    if not str(receipt.reviewed_contribution_id or "").strip():
        codes.append("reviewed_contribution_unbound")
    try:
        child = authority.read_revision(receipt.world_id, receipt.published_revision_id)
    except WorldGraphAuthorityError as exc:
        if exc.code == "authority_unavailable":
            if codes:
                return "failed", codes
            return "degraded", [f"child_verification_unavailable:{exc.code}"]
        raise
    if (
        child.parent_revision_id
        and child.parent_revision_id != receipt.parent_revision_id
    ):
        codes.append("child_parent_mismatch")
    objects = child.objects
    relationships = list(child.relationships.values())
    for assertion in list(getattr(contribution, "accepted_assertions", None) or []):
        kind = str(getattr(assertion, "assertion_kind", "") or "")
        subject = str(getattr(assertion, "subject_node_id", "") or "")
        target = str(getattr(assertion, "target_node_id", "") or "")
        predicate = str(getattr(assertion, "predicate", "") or "")
        value = getattr(assertion, "value", None) or {}
        if not isinstance(value, dict):
            value = {}
        if kind == "node" and subject and subject not in objects:
            codes.append(f"missing_object:{subject}")
        elif kind == "attribute":
            if subject and subject not in objects:
                codes.append(f"missing_attribute_subject:{subject}")
            elif subject:
                expected = _attribute_evidence_ids(
                    assertion, str(receipt.reviewed_contribution_id or "")
                )
                present_evidence = set(getattr(child, "evidence_refs", {}) or {})
                supported = getattr(child, "supported_assertion_ids", frozenset()) or frozenset()
                assertion_id = str(getattr(assertion, "assertion_id", "") or "")
                terms = tuple(getattr(objects[subject], "property_terms", ()) or ())
                evidence_ok = any(
                    _evidence_id_on_child(present_evidence, item) for item in expected
                ) or (assertion_id in supported)
                terms_ok = bool(
                    predicate
                    and terms
                    and any(
                        _relationship_predicate_matches(term, predicate) for term in terms
                    )
                )
                if predicate and terms and not terms_ok:
                    codes.append(f"missing_attribute:{subject}:{predicate}")
                elif not evidence_ok and not terms_ok:
                    codes.append(
                        f"missing_attribute_evidence:{subject}:{predicate or assertion_id}"
                    )
        elif kind == "alias":
            if subject and subject not in objects:
                codes.append(f"missing_alias_subject:{subject}")
            elif subject:
                alias = str(value.get("alias") or getattr(assertion, "label", "") or "")
                aliases = tuple(getattr(objects[subject], "aliases", ()) or ())
                if alias and alias not in aliases:
                    codes.append(f"missing_alias:{subject}:{alias}")
        elif kind == "edge":
            if subject and subject not in objects:
                codes.append(f"missing_edge_subject:{subject}")
            if target and target not in objects:
                codes.append(f"missing_edge_target:{target}")
            if subject and target and predicate:
                matched = any(
                    rel.subject_object_id == subject
                    and rel.target_object_id == target
                    and _relationship_predicate_matches(rel.predicate, predicate)
                    for rel in relationships
                )
                if not matched:
                    codes.append(f"missing_relationship:{subject}:{predicate}:{target}")
    if codes:
        return "failed", codes
    return "passed", []


def prepare_worldbuilding(
    request: WorldbuildingWritePlanPrepareRequest,
) -> WorldbuildingWritePlanResponse:
    """Prepare one exact BLD-08 worldbuilding run into an inert v2 write plan."""
    try:
        resolved = resolve_promotable_ingest_run(request.run_id, root=live_config.repo_root())
    except PromotableIngestRunError as exc:
        raise _promotable_run_error(exc) from exc

    typed_preview, expected_profile = _load_typed_worldbuilding_preview_for_run(
        resolved
    )
    authority = get_world_graph_authority()
    try:
        mutation_context = authority.mutation_context(
            DEFAULT_WORLD_ID, request.expected_parent_revision_id
        )
    except WorldGraphAuthorityError as exc:
        if exc.code == "revision_unavailable":
            try:
                head = authority.current_head(DEFAULT_WORLD_ID)
            except WorldGraphAuthorityError:
                raise _authority_error(exc) from exc
            if head.revision_id != request.expected_parent_revision_id:
                raise ExtractPromoteError(
                    "expected parent revision is not the current World Graph head",
                    code="stale_parent_revision",
                    status_code=409,
                    diagnostics=[
                        _diagnostic(
                            "stale_parent_revision",
                            "expected parent revision is not the current World Graph head",
                        )
                    ],
                ) from exc
        raise _authority_error(exc) from exc

    try:
        plan = build_worldbuilding_write_plan(
            preview=typed_preview,
            mutation_context=mutation_context,
            world_id=DEFAULT_WORLD_ID,
            expected_parent_revision_id=request.expected_parent_revision_id,
            run_id=resolved.run_id,
            source_artifact_id=resolved.source_artifact_id,
            source_revision_id=resolved.source_revision_id,
            source_uri=resolved.sealed_source_uri,
            extraction_profile=expected_profile,
            campaign_scope=resolved.campaign_id or None,
            dispositions=[
                WorldbuildingDispositionInput(
                    assertion_id=item.assertion_id,
                    decision=item.decision,
                    target_node_id=item.target_node_id,
                )
                for item in request.dispositions
            ],
        )
    except WorldbuildingWritePlanError as exc:
        raise _write_plan_error(exc) from exc

    try:
        head = authority.current_head(DEFAULT_WORLD_ID)
    except WorldGraphAuthorityError as exc:
        raise _authority_error(exc) from exc
    if head.revision_id != request.expected_parent_revision_id:
        raise ExtractPromoteError(
            "expected parent revision is not the current World Graph head",
            code="stale_parent_revision",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "stale_parent_revision",
                    "expected parent revision is not the current World Graph head",
                )
            ],
        )

    response = WorldbuildingWritePlanResponse(
        schema=WORLD_BUILDING_WRITE_PLAN_SCHEMA,
        version=2,
        plan_id=plan.plan_id,
        plan_digest=plan.plan_digest,
        decision_digest=plan.decision_digest,
        world_id=plan.world_id,
        parent_revision_id=plan.parent_revision_id,
        run_id=plan.run_id,
        source_artifact_id=plan.source_artifact_id,
        source_revision_id=plan.source_revision_id,
        extraction_profile=plan.extraction_profile,  # type: ignore[arg-type]
        candidate_preview_id=plan.candidate_preview_id,
        candidate_schema=plan.candidate_schema,
        candidate_version=plan.candidate_version,
        effect=plan.effect,
        summary=plan.summary,
        diagnostics=plan.diagnostics,
    )
    try:
        verify_worldbuilding_write_plan(
            response.model_dump(mode="json", by_alias=True),
            preview=typed_preview,
            mutation_context=mutation_context,
            context=WorldbuildingWritePlanVerificationContext(
                world_id=DEFAULT_WORLD_ID,
                parent_revision_id=request.expected_parent_revision_id,
                run_id=resolved.run_id,
                source_artifact_id=resolved.source_artifact_id,
                source_revision_id=resolved.source_revision_id,
                source_uri=resolved.sealed_source_uri,
                extraction_profile=expected_profile,
                campaign_scope=resolved.campaign_id or None,
            ),
            require_current_head=False,
        )
    except WorldbuildingWritePlanError as exc:
        if exc.code == "stale_parent_revision":
            raise _write_plan_error(exc) from exc
        raise ExtractPromoteError(
            "worldbuilding write plan failed self-verification",
            code="plan_verification_failed",
            status_code=500,
            diagnostics=[_diagnostic("plan_verification_failed", str(exc))],
        ) from exc
    snapshot = _identity_snapshot_payload(response)
    return response.model_copy(
        update={
            "prepare_binding": _sign_prepare_binding(
                world_id=DEFAULT_WORLD_ID,
                parent_revision_id=response.parent_revision_id,
                plan_id=response.plan_id,
                plan_digest=response.plan_digest,
                identity_snapshot_digest=_identity_snapshot_digest(snapshot),
            )
        }
    )


def confirm_worldbuilding(
    request: WorldbuildingWritePlanConfirmRequest,
) -> WorldbuildingWritePlanConfirmReceipt:
    """Rebuild-verify a v2 plan and publish or recover one DungeonMind child."""
    plan = request.plan
    if (
        plan.schema_ == WORLD_BUILDING_WRITE_PLAN_SCHEMA_V1
        or plan.version == 1
        or plan.effect.identity_authority is None
    ):
        raise _legacy_reprepare_error()

    world_root = live_config.world_graph_root()
    if (
        world_root.resolve() == live_config.live_world_graph_root().resolve()
        and not PRODUCT_CONFIRM_ALLOW_LIVE_WORLD
    ):
        raise ExtractPromoteError(
            "refusing to mutate live world root without allow_live_world",
            code="live_world_refused",
            status_code=403,
            diagnostics=[_diagnostic("live_world_refused", "live world refused")],
        )

    try:
        resolved = resolve_promotable_ingest_run(plan.run_id, root=live_config.repo_root())
    except PromotableIngestRunError as exc:
        raise _promotable_run_error(exc) from exc

    typed_preview, expected_profile = _load_typed_worldbuilding_preview_for_run(
        resolved
    )
    verify_context = WorldbuildingWritePlanVerificationContext(
        world_id=DEFAULT_WORLD_ID,
        parent_revision_id=plan.parent_revision_id,
        run_id=resolved.run_id,
        source_artifact_id=resolved.source_artifact_id,
        source_revision_id=resolved.source_revision_id,
        source_uri=resolved.sealed_source_uri,
        extraction_profile=expected_profile,
        campaign_scope=resolved.campaign_id or None,
    )
    authority = get_world_graph_authority()
    snapshot = _identity_snapshot_payload(plan)
    _require_prepare_binding(plan, snapshot)
    try:
        mutation_context = authority.mutation_context(
            DEFAULT_WORLD_ID,
            plan.parent_revision_id,
            sealed_identity_snapshot=snapshot,
        )
    except WorldGraphAuthorityError as exc:
        raise _authority_error(exc) from exc

    try:
        verified = verify_worldbuilding_write_plan(
            plan.model_dump(mode="json", by_alias=True),
            preview=typed_preview,
            mutation_context=mutation_context,
            context=verify_context,
            require_current_head=False,
        )
        contribution = materialize_worldbuilding_contribution(
            world_id=verified["world_id"],
            plan_digest=verified["plan_digest"],
            effect=verified["effect"],
        )
    except WorldbuildingWritePlanError as exc:
        raise _write_plan_error(exc) from exc

    if PRODUCT_CONFIRM_DRY_RUN:
        raise ExtractPromoteError(
            "worldbuilding confirm dry_run is not supported",
            code="invalid_request",
            status_code=422,
            diagnostics=[_diagnostic("invalid_request", "dry_run not supported")],
        )

    materialized_accepted = [
        assertion.assertion_id for assertion in contribution.accepted_assertions
    ]
    materialized_rejected = [
        assertion.assertion_id for assertion in contribution.rejected_assertions
    ]
    parent = str(verified["parent_revision_id"])
    operation_id = worldbuilding_authority_operation_id(
        world_id=str(verified["world_id"]),
        plan_id=str(verified["plan_id"]),
        plan_digest=str(verified["plan_digest"]),
    )
    actor = str(plan.run_id)
    recovered: WorldGraphPublicationReceipt | None
    try:
        recovered = authority.recover(
            str(verified["world_id"]),
            operation_id,
            expected_parent_revision_id=parent,
            contribution=contribution,
            actor=actor,
            operation_namespace="worldbuilding",
        )
    except WorldGraphAuthorityError as exc:
        raise _authority_error(exc) from exc

    if recovered is not None:
        return _receipt_from_publication(
            receipt=recovered,
            verified=verified,
            contribution=contribution,
            parent=parent,
            materialized_accepted=materialized_accepted,
            materialized_rejected=materialized_rejected,
            authority=authority,
            outcome="already_applied",
        )

    try:
        head = authority.current_head(str(verified["world_id"]))
    except WorldGraphAuthorityError as exc:
        raise _authority_error(exc) from exc
    if head.revision_id != parent:
        raise ExtractPromoteError(
            "expected parent revision is not the current World Graph head",
            code="stale_parent_revision",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "stale_parent_revision",
                    "expected parent revision is not the current World Graph head",
                )
            ],
        )

    publish_request = WorldGraphPublishRequest(
        world_id=str(verified["world_id"]),
        expected_parent_revision_id=parent,
        authority_operation_id=operation_id,
        actor=actor,
        contribution=contribution,
        accepted_assertion_ids=tuple(materialized_accepted),
        operation_namespace="worldbuilding",
    )
    try:
        receipt = authority.publish(publish_request)
    except WorldGraphAuthorityError as exc:
        if exc.code == "stale_parent":
            raise _authority_error(exc) from exc
        try:
            recovered = authority.recover(
                str(verified["world_id"]),
                operation_id,
                expected_parent_revision_id=parent,
                contribution=contribution,
                actor=actor,
                operation_namespace="worldbuilding",
            )
        except WorldGraphAuthorityError as recover_exc:
            raise _authority_error(recover_exc) from recover_exc
        if recovered is not None:
            return _receipt_from_publication(
                receipt=recovered,
                verified=verified,
                contribution=contribution,
                parent=parent,
                materialized_accepted=materialized_accepted,
                materialized_rejected=materialized_rejected,
                authority=authority,
                outcome="already_applied",
                extra_warnings=[f"publish_uncertain:{exc.code}"],
            )
        raise _authority_error(exc) from exc

    return _receipt_from_publication(
        receipt=receipt,
        verified=verified,
        contribution=contribution,
        parent=parent,
        materialized_accepted=materialized_accepted,
        materialized_rejected=materialized_rejected,
        authority=authority,
        outcome="already_applied" if receipt.outcome == "already_applied" else "committed",
    )


def _receipt_from_publication(
    *,
    receipt: WorldGraphPublicationReceipt,
    verified: Mapping[str, Any],
    contribution: Any,
    parent: str,
    materialized_accepted: list[str],
    materialized_rejected: list[str],
    authority: WorldGraphAuthority,
    outcome: str,
    extra_warnings: list[str] | None = None,
) -> WorldbuildingWritePlanConfirmReceipt:
    warnings = list(extra_warnings or [])
    status, codes = _verify_worldbuilding_child(
        authority,
        receipt=receipt,
        contribution=contribution,
        verified=verified,
        parent=parent,
        materialized_accepted=materialized_accepted,
    )
    if status == "failed":
        raise ExtractPromoteError(
            "published worldbuilding child failed native verification",
            code="publication_integrity_failure",
            status_code=409,
            diagnostics=[_diagnostic("publication_integrity_failure", ",".join(codes))],
        )
    audit_status: ConfirmAuditStatus = "ok"
    if status == "degraded":
        audit_status = "degraded"
        outcome = "published_audit_degraded"
        warnings.extend(codes)
    accepted = list(materialized_accepted)
    return _confirm_receipt(
        outcome=outcome,
        verified=verified,
        contribution=contribution,
        parent_revision_id=parent,
        committed_revision_id=receipt.published_revision_id,
        head_advanced=receipt.published_revision_id != parent,
        accepted_assertion_ids=accepted,
        rejected_assertion_ids=materialized_rejected,
        audit_status=audit_status,
        warnings=warnings,
    )


__all__ = ["confirm_worldbuilding", "prepare_worldbuilding"]
