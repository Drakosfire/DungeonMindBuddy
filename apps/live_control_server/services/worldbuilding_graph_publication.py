"""Existing-world worldbuilding prepare → confirm (CUTOVER D.2B).

Owns the mounted worldbuilding authority boundary. First-world/bootstrap stays
in ``extract_promote.py``. Product code talks only to ``WorldGraphAuthority``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
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

_IDENTITY_CHECKPOINT_REL = "out/registries/worldbuilding_identity_checkpoints.json"
_IDENTITY_CHECKPOINT_SCHEMA = "dmb_worldbuilding_identity_checkpoint_v1"


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


def _identity_checkpoint_path() -> Path:
    return live_config.repo_root() / _IDENTITY_CHECKPOINT_REL


def _load_identity_checkpoints() -> dict[str, Any]:
    path = _identity_checkpoint_path()
    if not path.is_file():
        return {"schema": _IDENTITY_CHECKPOINT_SCHEMA, "checkpoints": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": _IDENTITY_CHECKPOINT_SCHEMA, "checkpoints": []}
    if not isinstance(payload, dict):
        return {"schema": _IDENTITY_CHECKPOINT_SCHEMA, "checkpoints": []}
    records = payload.get("checkpoints")
    if not isinstance(records, list):
        payload["checkpoints"] = []
    return payload


def _checkpoint_key(record: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(record.get("world_id") or ""),
        str(record.get("parent_revision_id") or ""),
        str(record.get("digest") or ""),
    )


def _record_identity_checkpoint(
    *, world_id: str, parent_revision_id: str, digest: str
) -> None:
    path = _identity_checkpoint_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _load_identity_checkpoints()
    records = [dict(item) for item in list(payload.get("checkpoints") or []) if isinstance(item, dict)]
    entry = {
        "world_id": world_id,
        "parent_revision_id": parent_revision_id,
        "digest": digest,
    }
    if _checkpoint_key(entry) not in {_checkpoint_key(item) for item in records}:
        records.append(entry)
    payload["schema"] = _IDENTITY_CHECKPOINT_SCHEMA
    payload["checkpoints"] = records
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _require_identity_checkpoint(
    *, world_id: str, parent_revision_id: str, digest: str
) -> None:
    payload = _load_identity_checkpoints()
    wanted = (world_id, parent_revision_id, digest)
    records = [item for item in list(payload.get("checkpoints") or []) if isinstance(item, dict)]
    if wanted not in {_checkpoint_key(item) for item in records}:
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
    from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
        resolve_buddy_predicate_mapping_v4,
    )

    mapping = resolve_buddy_predicate_mapping_v4(expected)
    if mapping is None or not mapping[0]:
        return False
    dm_predicate = mapping[0]
    return published == dm_predicate or published_tail == dm_predicate.rsplit(":", 1)[-1]


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
                obj = objects[subject]
                terms = tuple(getattr(obj, "property_terms", ()) or ())
                # DungeonMind v6 materializes attribute assertions as
                # evidence/provenance only, not object.properties. When the
                # child does expose property terms, they must include the
                # accepted predicate. Empty terms are not a dropped assertion
                # so long as the subject exists and accepted IDs matched.
                if predicate and terms and not any(
                    _relationship_predicate_matches(term, predicate) for term in terms
                ):
                    codes.append(f"missing_attribute:{subject}:{predicate}")
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
    _record_identity_checkpoint(
        world_id=DEFAULT_WORLD_ID,
        parent_revision_id=request.expected_parent_revision_id,
        digest=_identity_snapshot_digest(snapshot),
    )
    return response


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
    _require_identity_checkpoint(
        world_id=DEFAULT_WORLD_ID,
        parent_revision_id=plan.parent_revision_id,
        digest=_identity_snapshot_digest(snapshot),
    )
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
