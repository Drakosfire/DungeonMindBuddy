"""SBW09c2b: proposal-bound Threat publication commit, recovery, and verification.

Storage:
    out/threat_publication_commits/<draft_id>/<operation_id>/ledger.json

Lock order (shared c1 lifecycle lock):
    lifecycle lock -> proposal ledger -> commit ledger
    -> SBW09b identity read -> SBW09a refresh/read -> Kernel APIs
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Literal

import graph_memory.kernel as kernel
from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package
from graph_memory.kernel.contribution_models import ContributionMergeResult, GraphContribution
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjectionFocus,
    WorldGraphProjectionRequest,
)
from graph_memory.union_supergraph.statblock_binding import (
    compute_binding_id,
    edge_id_from_binding_id,
)
from graph_memory.world_supergraph.errors import WorldGraphIntegrityError
from graph_memory.world_supergraph.model import WorldGraphRevision

from apps.live_control_server.config import world_graph_root
from apps.live_control_server.models.threat_draft import require_draft_id
from apps.live_control_server.models.threat_publication import (
    validate_publication_operation_id,
)
from apps.live_control_server.models.threat_publication_commit import (
    ConfirmThreatPublicationRequestV1,
    ThreatPublicationCommitLedgerV1,
    ThreatPublicationCommitResponseV1,
    ThreatPublicationCommitResultLabel,
    ThreatPublicationCommitV1,
    confirm_request_digest,
    validate_commit_id,
)
from apps.live_control_server.models.threat_publication_proposal import (
    ThreatPublicationProposalV1,
    validate_proposal_id,
)
from apps.live_control_server.services.threat_publication_commit_store import (
    ThreatPublicationCommitStorageError,
    load_threat_publication_commit_ledger_unlocked,
    save_threat_publication_commit_ledger_unlocked,
)
from apps.live_control_server.services.threat_publication_identity import (
    read_identity_resolution,
)
from apps.live_control_server.services.threat_publication_operations import (
    refresh_publication_operation,
)
from apps.live_control_server.services.threat_publication_proposals import (
    ThreatPublicationProposalStorageError,
    find_threat_publication_proposal,
    load_threat_publication_proposal_ledger_unlocked,
    threat_publication_lifecycle_lock,
)

MergeFn = Callable[..., ContributionMergeResult]
LookupFn = Callable[..., tuple[WorldGraphRevision, ...]]


@dataclass(frozen=True)
class CommitOutcome:
    response: ThreatPublicationCommitResponseV1
    created: bool = False
    merge_calls: int = 0


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _response(
    draft_id: str,
    operation_id: str,
    proposal_id: str | None,
    commit_id: str,
    label: ThreatPublicationCommitResultLabel,
    *,
    commit: ThreatPublicationCommitV1 | None = None,
    retry_allowed: bool = False,
    message: str | None = None,
) -> ThreatPublicationCommitResponseV1:
    return ThreatPublicationCommitResponseV1(
        draft_id=draft_id,
        operation_id=operation_id,
        proposal_id=proposal_id,
        commit_id=commit_id,
        result_label=label,
        commit=commit,
        retry_allowed=retry_allowed,
        message=message,
    )


def _label_for_state(commit: ThreatPublicationCommitV1) -> ThreatPublicationCommitResultLabel:
    if commit.state == "committed_verified":
        return "publication_commit_verified"
    if commit.state == "committed_unverified":
        return "publication_commit_committed_unverified"
    if commit.state == "committing":
        return "publication_commit_recovery_pending"
    if commit.state == "uncommitted":
        return "publication_commit_uncommitted"
    return "publication_commit_outcome_ambiguous"


def _retry_allowed(commit: ThreatPublicationCommitV1) -> bool:
    return commit.state == "committing" and commit.merge_attempt_count == 1


def _outcome_storage(
    draft_id: str,
    operation_id: str,
    proposal_id: str | None,
    commit_id: str,
    exc: ThreatPublicationCommitStorageError | ThreatPublicationProposalStorageError,
) -> CommitOutcome:
    kind = getattr(exc, "kind", "unavailable")
    label: ThreatPublicationCommitResultLabel = (
        "publication_commit_integrity_failure"
        if kind == "integrity"
        else "publication_commit_storage_unavailable"
    )
    return CommitOutcome(
        _response(draft_id, operation_id, proposal_id, commit_id, label, message=str(exc))
    )


def _derive_binding_id(
    *,
    threat_node_id: str,
    accepted_ref: Any,
    binding_edge_id: str,
) -> str:
    binding_id = compute_binding_id(
        threat_node_id=threat_node_id,
        provider=accepted_ref.provider,
        statblock_id=accepted_ref.statblock_id,
        revision_id=accepted_ref.revision_id,
        contract=accepted_ref.contract,
        contract_version=accepted_ref.contract_version,
        definition_digest=accepted_ref.definition_digest,
        role="primary",
        phase_key=None,
        variant_label=None,
    )
    if edge_id_from_binding_id(binding_id) != binding_edge_id:
        raise ValueError("derived binding_id does not match proposal binding_edge_id")
    return binding_id


def _extract_accepted_ids(contribution: GraphContribution) -> list[str]:
    return [item.assertion_id for item in contribution.accepted_assertions]


def _assertion_ids_match(actual: list[str], expected: list[str]) -> bool:
    """True when actual and expected are the same unique membership.

    Reconstruction from the sealed package may permute assertion order relative to
    the c1 proposal ledger. The commit record still persists the exact ordered c1
    list; admission only requires identical membership and cardinality.
    """
    if len(actual) != len(expected):
        return False
    if len(set(actual)) != len(actual):
        return False
    return set(actual) == set(expected)


def _contribution_matches_proposal(
    contribution: GraphContribution, proposal: ThreatPublicationProposalV1
) -> bool:
    if contribution.contribution_id != proposal.expected_contribution_id:
        return False
    return _assertion_ids_match(
        _extract_accepted_ids(contribution), list(proposal.accepted_assertion_ids)
    )


def _direct_publish_usable(
    result: ContributionMergeResult, record: ThreatPublicationCommitV1
) -> bool:
    if not result.published:
        return False
    if result.world_id != record.world_id:
        return False
    if result.parent_revision_id != record.expected_parent_revision_id:
        return False
    if not result.revision_id:
        return False
    if list(result.contribution_ids) != [record.expected_contribution_id]:
        return False
    return _assertion_ids_match(
        list(result.accepted_assertion_ids), list(record.accepted_assertion_ids)
    )


def _core_proof_match(
    *,
    manifest: WorldGraphRevision,
    record: ThreatPublicationCommitV1,
    world_root: Path,
) -> tuple[bool, str | None]:
    if manifest.world_id != record.world_id:
        return False, "manifest_world_mismatch"
    if manifest.parent_revision_id != record.expected_parent_revision_id:
        return False, "manifest_parent_mismatch"
    if record.expected_contribution_id not in manifest.operation_ids:
        return False, "manifest_operation_membership"
    if manifest.status != "published":
        return False, "manifest_status"
    try:
        store = kernel.load_world_graph_revision_with_integrity(
            world_root, record.world_id, manifest.revision_id
        )
    except WorldGraphIntegrityError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise WorldGraphIntegrityError(str(exc)) from exc

    digests = store.contribution_source_payload_sha256 or {}
    actual = digests.get(record.expected_contribution_id)
    if actual != record.expected_contribution_source_payload_sha256:
        return False, "contribution_source_digest_mismatch"

    active = [
        entry
        for entry in (store.contribution_replay_manifest or [])
        if entry.contribution_id == record.expected_contribution_id and entry.status == "active"
    ]
    if len(active) != 1:
        return False, "replay_manifest_mismatch"
    if active[0].source_payload_sha256 != record.expected_contribution_source_payload_sha256:
        return False, "replay_manifest_digest_mismatch"
    return True, None


def _save_commit(root: Path, commit: ThreatPublicationCommitV1) -> None:
    ledger = ThreatPublicationCommitLedgerV1(
        draft_id=commit.draft_id,
        operation_id=commit.operation_id,
        commit=commit,
    )
    save_threat_publication_commit_ledger_unlocked(root, ledger)


def _with_updated(commit: ThreatPublicationCommitV1, **updates: Any) -> ThreatPublicationCommitV1:
    payload = commit.model_dump(mode="json", by_alias=True)
    payload.update(updates)
    payload["updated_at"] = _utc_now_iso()
    return ThreatPublicationCommitV1.model_validate(payload)


def _verify_committed(
    *,
    root: Path,
    world_root: Path,
    record: ThreatPublicationCommitV1,
    proposal: ThreatPublicationProposalV1,
    contribution: GraphContribution,
    lookup_fn: LookupFn,
) -> ThreatPublicationCommitV1:
    codes: list[str] = []
    warnings: list[str] = []
    status: Literal["passed", "degraded", "failed", "not_started"] = "passed"

    try:
        matches = lookup_fn(
            world_root, record.world_id, record.expected_contribution_id
        )
    except WorldGraphIntegrityError as exc:
        return _with_updated(
            record,
            state="committed_unverified",
            verification_status="failed",
            verification_codes=["verification_lookup_integrity", str(exc)[:180]],
            warnings=warnings,
        )
    except OSError as exc:
        return _with_updated(
            record,
            state="committed_unverified",
            verification_status="degraded",
            verification_codes=["verification_lookup_unavailable"],
            warnings=[str(exc)[:180]],
        )

    if len(matches) != 1 or matches[0].revision_id != record.committed_revision_id:
        codes.append("verification_c2a_revision_mismatch")
        status = "failed"
    else:
        try:
            ok, reason = _core_proof_match(
                manifest=matches[0], record=record, world_root=world_root
            )
            if not ok:
                codes.append(reason or "verification_core_mismatch")
                status = "failed"
        except WorldGraphIntegrityError as exc:
            codes.append("verification_integrity_load")
            warnings.append(str(exc)[:180])
            status = "failed"

    if status != "failed":
        try:
            store = kernel.load_world_graph_revision_with_integrity(
                world_root, record.world_id, str(record.committed_revision_id)
            )
        except Exception as exc:  # noqa: BLE001
            codes.append("verification_store_load")
            warnings.append(str(exc)[:180])
            status = "failed"
            store = None

        if store is not None:
            for assertion_id in record.accepted_assertion_ids:
                raw = (store.assertion_support or {}).get(assertion_id)
                if not isinstance(raw, dict):
                    codes.append(f"missing_support:{assertion_id}")
                    status = "failed"
                    continue
                if raw.get("support_state") != "supported":
                    codes.append(f"unsupported:{assertion_id}")
                    status = "failed"
                active = list(raw.get("active_contribution_ids") or [])
                if record.expected_contribution_id not in active:
                    codes.append(f"support_contribution_mismatch:{assertion_id}")
                    status = "failed"

            resource = store.nodes.get(record.external_resource_node_id)
            binding = store.edges.get(record.binding_edge_id)
            if resource is None:
                codes.append("missing_external_resource")
                status = "failed"
            if binding is None:
                codes.append("missing_binding_edge")
                status = "failed"
            elif (
                binding.source_node_id != record.threat_node_id
                or binding.target_node_id != record.external_resource_node_id
                or binding.predicate != "uses_statblock"
            ):
                codes.append("binding_endpoints_mismatch")
                status = "failed"

            if record.decision == "create_new":
                threat = store.nodes.get(record.threat_node_id)
                if threat is None:
                    codes.append("missing_threat_node")
                    status = "failed"
            else:
                for assertion in contribution.accepted_assertions:
                    kind = str((assertion.value or {}).get("kind", "")).casefold()
                    if assertion.assertion_kind == "node_upsert" and (
                        assertion.subject_node_id == record.threat_node_id or kind == "threat"
                    ):
                        codes.append("connect_existing_threat_rewrite")
                        status = "failed"
                        break
                if record.selected_target is not None:
                    target = store.nodes.get(record.threat_node_id)
                    if target is None or target.node_id != record.selected_target.node_id:
                        codes.append("connect_target_mismatch")
                        status = "failed"

            # Mechanics body must not appear in contribution values.
            banned = ("mechanics_body", "rendered_markdown", "rules_elements", "assets")
            for assertion in contribution.accepted_assertions:
                blob = str(assertion.value)
                if any(token in blob for token in banned):
                    codes.append("mechanics_body_leak")
                    status = "failed"
                    break

    if status != "failed":
        try:
            rebuild = kernel.rebuild_from_contributions(
                world_root,
                world_id=record.world_id,
                compare_revision_id=record.committed_revision_id,
                publish=False,
            )
            if "rebuild_equivalent_to_pinned_revision" not in (rebuild.diagnostics or []):
                codes.append("rebuild_not_equivalent")
                status = "degraded" if status == "passed" else status
        except Exception as exc:  # noqa: BLE001
            codes.append("rebuild_unavailable")
            warnings.append(str(exc)[:180])
            status = "degraded" if status == "passed" else status

        try:
            projection = kernel.project_world_graph(
                world_root,
                WorldGraphProjectionRequest(
                    schema=PROJECTION_REQUEST_SCHEMA,
                    world_id=record.world_id,
                    campaign_id=record.campaign_id,
                    focus=WorldGraphProjectionFocus(kind="none"),
                    admissibility="gm",
                    scope_mode="campaign",
                    revision_pin=record.committed_revision_id,
                    query_text=record.threat_node_id,
                ),
            )
            if projection.snapshot.revision_id != record.committed_revision_id:
                codes.append("projection_revision_mismatch")
                status = "failed"
        except Exception as exc:  # noqa: BLE001
            codes.append("projection_unavailable")
            warnings.append(str(exc)[:180])
            status = "degraded" if status == "passed" else status

    if status == "passed":
        return _with_updated(
            record,
            state="committed_verified",
            verification_status="passed",
            verification_codes=codes,
            warnings=warnings,
        )
    return _with_updated(
        record,
        state="committed_unverified",
        verification_status=status if status != "not_started" else "failed",
        verification_codes=codes,
        warnings=warnings,
    )


def _reconcile(
    *,
    root: Path,
    world_root: Path,
    record: ThreatPublicationCommitV1,
    proposal: ThreatPublicationProposalV1 | None,
    contribution: GraphContribution | None,
    lookup_fn: LookupFn,
    merge_fn: MergeFn,
    published_false: bool,
    merge_calls: int,
) -> tuple[ThreatPublicationCommitV1, int, ThreatPublicationCommitResultLabel, bool]:
    """Reconcile an uncertain outcome through c2a.

    The fourth return value is True only when the lookup completed and returned
    zero matches with attempt_count==1, so the caller may run the one governed
    recovery retry. Transient lookup unavailability and integrity-unloadable
    authority keep state=committing but must never merge again in this request.
    """
    try:
        matches = lookup_fn(
            world_root, record.world_id, record.expected_contribution_id
        )
    except WorldGraphIntegrityError:
        return (
            record,
            merge_calls,
            "publication_commit_integrity_failure",
            False,
        )
    except OSError:
        return (
            record,
            merge_calls,
            "publication_commit_recovery_pending",
            False,
        )
    except Exception:
        return (
            record,
            merge_calls,
            "publication_commit_integrity_failure",
            False,
        )

    if len(matches) > 1:
        updated = _with_updated(record, state="ambiguous")
        _save_commit(root, updated)
        return updated, merge_calls, "publication_commit_outcome_ambiguous", False

    if len(matches) == 1:
        try:
            ok, _reason = _core_proof_match(
                manifest=matches[0], record=record, world_root=world_root
            )
        except WorldGraphIntegrityError:
            return record, merge_calls, "publication_commit_integrity_failure", False
        if not ok:
            updated = _with_updated(record, state="ambiguous")
            _save_commit(root, updated)
            return updated, merge_calls, "publication_commit_outcome_ambiguous", False
        updated = _with_updated(
            record,
            state="committed_unverified",
            committed_revision_id=matches[0].revision_id,
            recovered_via_operation_lookup=True,
            verification_status="not_started",
        )
        _save_commit(root, updated)
        if proposal is not None and contribution is not None:
            verified = _verify_committed(
                root=root,
                world_root=world_root,
                record=updated,
                proposal=proposal,
                contribution=contribution,
                lookup_fn=lookup_fn,
            )
            _save_commit(root, verified)
            return verified, merge_calls, _label_for_state(verified), False
        return updated, merge_calls, "publication_commit_committed_unverified", False

    # zero matches
    if published_false:
        updated = _with_updated(record, state="uncommitted")
        _save_commit(root, updated)
        return updated, merge_calls, "publication_commit_uncommitted", False

    if record.merge_attempt_count >= 2:
        updated = _with_updated(record, state="uncommitted")
        _save_commit(root, updated)
        return updated, merge_calls, "publication_commit_uncommitted", False

    # Conditional single retry requires full revalidation by caller.
    return record, merge_calls, "publication_commit_recovery_pending", True


def _admit_and_build_record(
    *,
    root: Path,
    world_root: Path,
    draft_id: str,
    operation_id: str,
    proposal_id: str,
    request: ConfirmThreatPublicationRequestV1,
) -> tuple[ThreatPublicationCommitV1 | None, CommitOutcome | None, GraphContribution | None, ThreatPublicationProposalV1 | None]:
    proposal_ledger = load_threat_publication_proposal_ledger_unlocked(
        root, draft_id, operation_id
    )
    if proposal_ledger is None:
        return None, CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                request.commit_id,
                "publication_commit_proposal_not_active",
                message="proposal ledger not found",
            )
        ), None, None

    proposal = find_threat_publication_proposal(proposal_ledger, proposal_id)
    if (
        proposal is None
        or proposal.state != "active"
        or proposal_ledger.active_proposal_id != proposal_id
    ):
        return None, CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                request.commit_id,
                "publication_commit_proposal_not_active",
                message="proposal is not active",
            )
        ), None, None

    if request.sealed_proposal_digest != proposal.sealed_proposal_digest:
        return None, CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                request.commit_id,
                "publication_commit_input_conflict",
                message="sealed_proposal_digest mismatch",
            )
        ), None, proposal
    if request.expected_parent_revision_id != proposal.expected_parent_revision_id:
        return None, CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                request.commit_id,
                "publication_commit_parent_mismatch",
                message="expected_parent_revision_id mismatch",
            )
        ), None, proposal

    identity = read_identity_resolution(root, draft_id, operation_id, proposal.resolution_id)
    resolution = identity.response.resolution
    if resolution is None or resolution.state != "active":
        return None, CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                request.commit_id,
                "publication_commit_resolution_not_active",
                message="identity resolution is not active",
            )
        ), None, proposal
    if resolution.decision not in ("create_new", "connect_existing"):
        return None, CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                request.commit_id,
                "publication_commit_resolution_not_active",
                message="identity resolution is not publishable",
            )
        ), None, proposal

    refresh = refresh_publication_operation(root, draft_id, operation_id)
    operation = refresh.response.operation
    if refresh.response.result_label != "publication_ready" or operation is None:
        return None, CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                request.commit_id,
                "publication_commit_operation_not_ready",
                message=refresh.response.result_label,
            )
        ), None, proposal

    snapshot = operation.source_snapshot
    if (
        resolution.source_digest != proposal.source_digest
        or resolution.request_digest != proposal.resolution_request_digest
        or resolution.candidate_set_digest != proposal.candidate_set_digest
        or resolution.expected_parent_revision_id != proposal.expected_parent_revision_id
        or resolution.decision != proposal.decision
        or (
            resolution.decision == "create_new"
            and resolution.created_node_id != proposal.threat_node_id
        )
        or (
            resolution.decision == "connect_existing"
            and (
                resolution.selected_target is None
                or resolution.selected_target.node_id != proposal.threat_node_id
            )
        )
        or operation.source_digest != proposal.source_digest
        or operation.expected_parent_revision_id != proposal.expected_parent_revision_id
    ):
        return None, CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                request.commit_id,
                "publication_commit_predecessor_mismatch",
                message="publication predecessors no longer match proposal authority",
            )
        ), None, proposal

    try:
        _verified, contribution = resolve_merged_contribution_from_package(
            review_package=proposal.sealed_proposal,
            confirming_principal=proposal.created_by,
            world_id_hint=snapshot.world_id,
            root=world_root,
            expected_parent_revision_id=proposal.expected_parent_revision_id,
            assertion_ids=None,
            verify_source=False,
        )
    except Exception as exc:  # noqa: BLE001
        return None, CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                request.commit_id,
                "publication_commit_integrity_failure",
                message=f"contribution reconstruction failed: {exc}",
            )
        ), None, proposal

    if not _contribution_matches_proposal(contribution, proposal):
        return None, CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                request.commit_id,
                "publication_commit_integrity_failure",
                message="reconstructed contribution does not match proposal",
            )
        ), None, proposal

    source_digest = kernel.compute_contribution_source_payload_sha256(contribution)
    try:
        binding_id = _derive_binding_id(
            threat_node_id=proposal.threat_node_id,
            accepted_ref=snapshot.accepted_mechanics_ref,
            binding_edge_id=proposal.effect_summary.binding_edge_id,
        )
    except Exception as exc:  # noqa: BLE001
        return None, CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                request.commit_id,
                "publication_commit_integrity_failure",
                message=f"binding identity derivation failed: {exc}",
            )
        ), None, proposal

    try:
        head, _rev, _store = kernel.open_current_world_graph(world_root, snapshot.world_id)
    except Exception as exc:  # noqa: BLE001
        return None, CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                request.commit_id,
                "publication_commit_graph_unavailable",
                message=str(exc),
            )
        ), None, proposal
    if head.head_revision_id != proposal.expected_parent_revision_id:
        return None, CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                request.commit_id,
                "publication_commit_parent_mismatch",
                message="current head does not equal proposal parent",
            )
        ), None, proposal

    selected_target = (
        None
        if proposal.decision == "create_new"
        else resolution.selected_target
    )
    if proposal.decision == "connect_existing" and selected_target is None:
        return None, CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                request.commit_id,
                "publication_commit_resolution_not_active",
                message="connect_existing requires selected_target snapshot",
            )
        ), None, proposal

    now = _utc_now_iso()
    record = ThreatPublicationCommitV1.model_validate(
        {
            "commit_id": request.commit_id,
            "request_digest": confirm_request_digest(
                draft_id, operation_id, proposal_id, request
            ),
            "draft_id": draft_id,
            "operation_id": operation_id,
            "proposal_id": proposal_id,
            "proposal_request_digest": proposal.request_digest,
            "sealed_proposal_digest": proposal.sealed_proposal_digest,
            "sealed_proposal_version": proposal.sealed_proposal_version,
            "resolution_id": proposal.resolution_id,
            "source_digest": proposal.source_digest,
            "resolution_request_digest": proposal.resolution_request_digest,
            "candidate_set_digest": proposal.candidate_set_digest,
            "world_id": snapshot.world_id,
            "campaign_id": snapshot.campaign_id,
            "expected_parent_revision_id": proposal.expected_parent_revision_id,
            "expected_contribution_id": proposal.expected_contribution_id,
            "expected_contribution_source_payload_sha256": source_digest,
            "accepted_assertion_ids": list(proposal.accepted_assertion_ids),
            "decision": proposal.decision,
            "threat_node_id": proposal.threat_node_id,
            "selected_target": (
                selected_target.model_dump(mode="json", by_alias=True)
                if selected_target is not None
                else None
            ),
            "external_resource_node_id": proposal.effect_summary.external_resource_node_id,
            "binding_id": binding_id,
            "binding_edge_id": proposal.effect_summary.binding_edge_id,
            "state": "committing",
            "merge_attempt_count": 1,
            "committed_revision_id": None,
            "recovered_via_operation_lookup": False,
            "verification_status": "not_started",
            "verification_codes": [],
            "warnings": [],
            "created_by": request.actor,
            "operator_note": request.operator_note,
            "created_at": now,
            "updated_at": now,
        }
    )
    return record, None, contribution, proposal


def _maybe_retry(
    *,
    root: Path,
    world_root: Path,
    record: ThreatPublicationCommitV1,
    proposal: ThreatPublicationProposalV1,
    contribution: GraphContribution,
    merge_fn: MergeFn,
    lookup_fn: LookupFn,
    merge_calls: int,
) -> tuple[ThreatPublicationCommitV1, int, ThreatPublicationCommitResultLabel]:
    try:
        head, _rev, _store = kernel.open_current_world_graph(world_root, record.world_id)
    except Exception:
        return record, merge_calls, "publication_commit_graph_unavailable"
    if head.head_revision_id != record.expected_parent_revision_id:
        updated = _with_updated(record, state="uncommitted")
        _save_commit(root, updated)
        return updated, merge_calls, "publication_commit_uncommitted"

    identity = read_identity_resolution(
        root, record.draft_id, record.operation_id, record.resolution_id
    )
    resolution = identity.response.resolution
    if (
        resolution is None
        or resolution.state != "active"
        or resolution.source_digest != record.source_digest
        or resolution.request_digest != record.resolution_request_digest
        or resolution.candidate_set_digest != record.candidate_set_digest
    ):
        updated = _with_updated(record, state="uncommitted")
        _save_commit(root, updated)
        return updated, merge_calls, "publication_commit_uncommitted"

    refresh = refresh_publication_operation(root, record.draft_id, record.operation_id)
    operation = refresh.response.operation
    if (
        refresh.response.result_label != "publication_ready"
        or operation is None
        or operation.source_digest != record.source_digest
        or operation.expected_parent_revision_id != record.expected_parent_revision_id
    ):
        updated = _with_updated(record, state="uncommitted")
        _save_commit(root, updated)
        return updated, merge_calls, "publication_commit_uncommitted"

    try:
        _verified, rebuilt = resolve_merged_contribution_from_package(
            review_package=proposal.sealed_proposal,
            confirming_principal=proposal.created_by,
            world_id_hint=record.world_id,
            root=world_root,
            expected_parent_revision_id=record.expected_parent_revision_id,
            assertion_ids=None,
            verify_source=False,
        )
    except Exception:
        updated = _with_updated(record, state="uncommitted")
        _save_commit(root, updated)
        return updated, merge_calls, "publication_commit_uncommitted"

    if (
        rebuilt.contribution_id != record.expected_contribution_id
        or kernel.compute_contribution_source_payload_sha256(rebuilt)
        != record.expected_contribution_source_payload_sha256
        or not _assertion_ids_match(
            _extract_accepted_ids(rebuilt), list(record.accepted_assertion_ids)
        )
    ):
        updated = _with_updated(record, state="uncommitted")
        _save_commit(root, updated)
        return updated, merge_calls, "publication_commit_uncommitted"

    attempt2 = _with_updated(record, merge_attempt_count=2)
    _save_commit(root, attempt2)
    try:
        result = merge_fn(
            world_root,
            world_id=attempt2.world_id,
            contribution=rebuilt,
            expected_parent_revision_id=attempt2.expected_parent_revision_id,
        )
        merge_calls += 1
    except Exception:
        merge_calls += 1
        updated, merge_calls, label, _allow_retry = _reconcile(
            root=root,
            world_root=world_root,
            record=attempt2,
            proposal=proposal,
            contribution=rebuilt,
            lookup_fn=lookup_fn,
            merge_fn=merge_fn,
            published_false=False,
            merge_calls=merge_calls,
        )
        return updated, merge_calls, label

    if _direct_publish_usable(result, attempt2):
        updated = _with_updated(
            attempt2,
            state="committed_unverified",
            committed_revision_id=result.revision_id,
            recovered_via_operation_lookup=False,
            verification_status="not_started",
        )
        _save_commit(root, updated)
        verified = _verify_committed(
            root=root,
            world_root=world_root,
            record=updated,
            proposal=proposal,
            contribution=rebuilt,
            lookup_fn=lookup_fn,
        )
        _save_commit(root, verified)
        return verified, merge_calls, _label_for_state(verified)

    updated, merge_calls, label, _allow_retry = _reconcile(
        root=root,
        world_root=world_root,
        record=attempt2,
        proposal=proposal,
        contribution=rebuilt,
        lookup_fn=lookup_fn,
        merge_fn=merge_fn,
        published_false=(result.published is False),
        merge_calls=merge_calls,
    )
    return updated, merge_calls, label


def confirm_threat_publication(
    root: Path,
    draft_id: str,
    operation_id: str,
    proposal_id: str,
    request: ConfirmThreatPublicationRequestV1,
    *,
    world_root: Path | None = None,
    merge_fn: MergeFn | None = None,
    lookup_fn: LookupFn | None = None,
) -> CommitOutcome:
    safe_draft = require_draft_id(draft_id)
    safe_op = validate_publication_operation_id(operation_id)
    safe_proposal = validate_proposal_id(proposal_id)
    safe_commit = validate_commit_id(request.commit_id)
    configured_world = world_root if world_root is not None else world_graph_root()
    merge = merge_fn or kernel.merge_contribution_to_revision
    lookup = lookup_fn or kernel.find_world_graph_revisions_by_operation_id
    merge_calls = 0

    with threat_publication_lifecycle_lock(root, safe_draft, safe_op):
        try:
            existing = load_threat_publication_commit_ledger_unlocked(
                root, safe_draft, safe_op
            )
        except ThreatPublicationCommitStorageError as exc:
            return _outcome_storage(safe_draft, safe_op, safe_proposal, safe_commit, exc)

        if existing is not None:
            record = existing.commit
            incoming = confirm_request_digest(
                safe_draft, safe_op, safe_proposal, request
            )
            if record.commit_id != safe_commit:
                return CommitOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_proposal,
                        safe_commit,
                        "publication_commit_busy",
                        commit=record,
                        message="operation already claimed by a different commit_id",
                    )
                )
            if record.request_digest != incoming:
                return CommitOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_proposal,
                        safe_commit,
                        "publication_commit_input_conflict",
                        commit=record,
                        message="commit_id reused with a changed request",
                    )
                )
            if record.proposal_id != safe_proposal:
                return CommitOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_proposal,
                        safe_commit,
                        "publication_commit_integrity_failure",
                        commit=record,
                        message="commit record proposal_id disagrees with route",
                    )
                )

            if record.state == "committed_verified":
                return CommitOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_proposal,
                        safe_commit,
                        "publication_commit_verified",
                        commit=record,
                    )
                )
            if record.state in {"uncommitted", "ambiguous"}:
                return CommitOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_proposal,
                        safe_commit,
                        _label_for_state(record),
                        commit=record,
                    )
                )

            # Need proposal + contribution for verification / recovery paths.
            try:
                proposal_ledger = load_threat_publication_proposal_ledger_unlocked(
                    root, safe_draft, safe_op
                )
            except ThreatPublicationProposalStorageError as exc:
                return _outcome_storage(
                    safe_draft, safe_op, safe_proposal, safe_commit, exc
                )
            proposal = (
                find_threat_publication_proposal(proposal_ledger, record.proposal_id)
                if proposal_ledger is not None
                else None
            )
            contribution = None
            if proposal is not None:
                try:
                    _v, contribution = resolve_merged_contribution_from_package(
                        review_package=proposal.sealed_proposal,
                        confirming_principal=proposal.created_by,
                        world_id_hint=record.world_id,
                        root=configured_world,
                        expected_parent_revision_id=record.expected_parent_revision_id,
                        assertion_ids=None,
                        verify_source=False,
                    )
                except Exception:
                    contribution = None

            if record.state == "committed_unverified":
                if proposal is None or contribution is None:
                    return CommitOutcome(
                        _response(
                            safe_draft,
                            safe_op,
                            safe_proposal,
                            safe_commit,
                            "publication_commit_committed_unverified",
                            commit=record,
                        )
                    )
                verified = _verify_committed(
                    root=root,
                    world_root=configured_world,
                    record=record,
                    proposal=proposal,
                    contribution=contribution,
                    lookup_fn=lookup,
                )
                try:
                    _save_commit(root, verified)
                except ThreatPublicationCommitStorageError as exc:
                    return _outcome_storage(
                        safe_draft, safe_op, safe_proposal, safe_commit, exc
                    )
                return CommitOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_proposal,
                        safe_commit,
                        _label_for_state(verified),
                        commit=verified,
                    )
                )

            # committing — reconcile first
            updated, merge_calls, label, allow_zero_match_retry = _reconcile(
                root=root,
                world_root=configured_world,
                record=record,
                proposal=proposal,
                contribution=contribution,
                lookup_fn=lookup,
                merge_fn=merge,
                published_false=False,
                merge_calls=merge_calls,
            )
            if (
                allow_zero_match_retry
                and updated.state == "committing"
                and updated.merge_attempt_count == 1
                and proposal is not None
                and contribution is not None
            ):
                updated, merge_calls, label = _maybe_retry(
                    root=root,
                    world_root=configured_world,
                    record=updated,
                    proposal=proposal,
                    contribution=contribution,
                    merge_fn=merge,
                    lookup_fn=lookup,
                    merge_calls=merge_calls,
                )
            return CommitOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    safe_proposal,
                    safe_commit,
                    label,
                    commit=updated,
                    retry_allowed=_retry_allowed(updated),
                ),
                merge_calls=merge_calls,
            )

        # New admission
        try:
            record, early, contribution, proposal = _admit_and_build_record(
                root=root,
                world_root=configured_world,
                draft_id=safe_draft,
                operation_id=safe_op,
                proposal_id=safe_proposal,
                request=request,
            )
        except ThreatPublicationProposalStorageError as exc:
            return _outcome_storage(safe_draft, safe_op, safe_proposal, safe_commit, exc)
        except ThreatPublicationCommitStorageError as exc:
            return _outcome_storage(safe_draft, safe_op, safe_proposal, safe_commit, exc)

        if early is not None:
            return early
        assert record is not None and contribution is not None and proposal is not None

        try:
            _save_commit(root, record)
        except ThreatPublicationCommitStorageError as exc:
            return _outcome_storage(safe_draft, safe_op, safe_proposal, safe_commit, exc)

        published_false = False
        result: ContributionMergeResult | None = None
        try:
            result = merge(
                configured_world,
                world_id=record.world_id,
                contribution=contribution,
                expected_parent_revision_id=record.expected_parent_revision_id,
            )
            merge_calls += 1
            published_false = result.published is False
        except Exception:
            merge_calls += 1
            result = None

        if result is not None and _direct_publish_usable(result, record):
            updated = _with_updated(
                record,
                state="committed_unverified",
                committed_revision_id=result.revision_id,
                recovered_via_operation_lookup=False,
                verification_status="not_started",
            )
            try:
                _save_commit(root, updated)
            except ThreatPublicationCommitStorageError:
                # Receipt save failed; remain committing for c2a recovery on replay.
                return CommitOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_proposal,
                        safe_commit,
                        "publication_commit_recovery_pending",
                        commit=record,
                        retry_allowed=True,
                        message="committed revision may exist; receipt persistence failed",
                    ),
                    created=True,
                    merge_calls=merge_calls,
                )
            verified = _verify_committed(
                root=root,
                world_root=configured_world,
                record=updated,
                proposal=proposal,
                contribution=contribution,
                lookup_fn=lookup,
            )
            try:
                _save_commit(root, verified)
            except ThreatPublicationCommitStorageError:
                return CommitOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_proposal,
                        safe_commit,
                        "publication_commit_committed_unverified",
                        commit=updated,
                    ),
                    created=True,
                    merge_calls=merge_calls,
                )
            return CommitOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    safe_proposal,
                    safe_commit,
                    _label_for_state(verified),
                    commit=verified,
                ),
                created=True,
                merge_calls=merge_calls,
            )

        updated, merge_calls, label, allow_zero_match_retry = _reconcile(
            root=root,
            world_root=configured_world,
            record=record,
            proposal=proposal,
            contribution=contribution,
            lookup_fn=lookup,
            merge_fn=merge,
            published_false=published_false,
            merge_calls=merge_calls,
        )
        if (
            allow_zero_match_retry
            and updated.state == "committing"
            and updated.merge_attempt_count == 1
        ):
            updated, merge_calls, label = _maybe_retry(
                root=root,
                world_root=configured_world,
                record=updated,
                proposal=proposal,
                contribution=contribution,
                merge_fn=merge,
                lookup_fn=lookup,
                merge_calls=merge_calls,
            )
        return CommitOutcome(
            _response(
                safe_draft,
                safe_op,
                safe_proposal,
                safe_commit,
                label,
                commit=updated,
                retry_allowed=_retry_allowed(updated),
            ),
            created=True,
            merge_calls=merge_calls,
        )


def read_threat_publication_commit(
    root: Path,
    draft_id: str,
    operation_id: str,
    commit_id: str,
) -> CommitOutcome:
    safe_draft = require_draft_id(draft_id)
    safe_op = validate_publication_operation_id(operation_id)
    safe_commit = validate_commit_id(commit_id)

    # Missing GET must not create directories or locks.
    from apps.live_control_server.services.threat_publication_commit_store import (
        threat_publication_commit_ledger_exists,
    )

    if not threat_publication_commit_ledger_exists(root, safe_draft, safe_op):
        return CommitOutcome(
            _response(
                safe_draft,
                safe_op,
                None,
                safe_commit,
                "publication_commit_not_found",
                message="publication commit ledger not found",
            )
        )

    with threat_publication_lifecycle_lock(root, safe_draft, safe_op):
        try:
            ledger = load_threat_publication_commit_ledger_unlocked(
                root, safe_draft, safe_op
            )
        except ThreatPublicationCommitStorageError as exc:
            return _outcome_storage(safe_draft, safe_op, None, safe_commit, exc)
        if ledger is None or ledger.commit.commit_id != safe_commit:
            return CommitOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    None,
                    safe_commit,
                    "publication_commit_not_found",
                    message="publication commit not found",
                )
            )
        record = ledger.commit
        return CommitOutcome(
            _response(
                safe_draft,
                safe_op,
                record.proposal_id,
                safe_commit,
                _label_for_state(record),
                commit=record,
                retry_allowed=_retry_allowed(record),
            )
        )
