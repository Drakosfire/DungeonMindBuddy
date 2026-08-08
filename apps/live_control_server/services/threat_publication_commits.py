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
from collections.abc import Mapping
from typing import Any, Callable, Literal

import graph_memory.kernel as kernel
from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package
from graph_memory.kernel.contribution_models import ContributionMergeResult, GraphContribution
from graph_memory.kernel.contributions import normalize_assertion_provenance
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjectionFocus,
    WorldGraphProjectionRequest,
)
from graph_memory.union_supergraph.statblock_binding import (
    CONTRACT,
    CONTRACT_VERSION,
    ExternalResourceV1,
    FORBIDDEN_MECHANICS_KEYS,
    PROVIDER,
    ThreatStatblockBindingV1,
    compute_binding_id,
    edge_id_from_binding_id,
    external_statblock_node_id,
    parse_threat_statblock_binding_assertion,
    reject_mechanics_keys,
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
    commit_admitted: bool | None = None,
    infer_commit_admission: bool = True,
    retry_allowed: bool = False,
    message: str | None = None,
) -> ThreatPublicationCommitResponseV1:
    admitted = (
        commit is not None
        if infer_commit_admission and commit_admitted is None
        else commit_admitted
    )
    return ThreatPublicationCommitResponseV1(
        draft_id=draft_id,
        operation_id=operation_id,
        proposal_id=proposal_id,
        commit_id=commit_id,
        result_label=label,
        commit_admitted=admitted,
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
    *,
    commit: ThreatPublicationCommitV1 | None = None,
    admission_known: bool = True,
) -> CommitOutcome:
    kind = getattr(exc, "kind", "unavailable")
    label: ThreatPublicationCommitResultLabel = (
        "publication_commit_integrity_failure"
        if kind == "integrity"
        else "publication_commit_storage_unavailable"
    )
    return CommitOutcome(
        _response(
            draft_id,
            operation_id,
            proposal_id,
            commit_id,
            label,
            commit=commit,
            commit_admitted=(
                True
                if commit is not None
                else False
                if admission_known
                else None
            ),
            infer_commit_admission=False,
            message=str(exc),
        )
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
    """True when actual and expected are the same ordered assertion-id list."""
    return list(actual) == list(expected)


def _unmodified_contribution_matches_expected_ids(
    contribution: GraphContribution, expected_ids: list[str]
) -> bool:
    """Prove the unmodified reconstructed contribution already has exact order.

    Rearranging assertions before digest/merge is forbidden. Admission and
    authority checks must fail when reconstruction order disagrees with the
    c1 ledger list (which itself records reconstruction order).
    """
    return _assertion_ids_match(_extract_accepted_ids(contribution), expected_ids)


def _historical_seal_order_ids(
    sealed_proposal: Mapping[str, Any] | None,
) -> list[str] | None:
    """Exact pre-reconstruction seal-time assertion order from the sealed package.

    Old c1 persisted ``accepted_assertion_ids`` in the order of
    ``effect.accepted_proposals`` passed to ``seal_promote_proposal``. That list
    remains immutable inside the sealed package and is the only legitimate
    legacy-order discriminator — not arbitrary same-set permutations.
    """
    if not isinstance(sealed_proposal, Mapping):
        return None
    effect = sealed_proposal.get("effect")
    if not isinstance(effect, Mapping):
        return None
    accepted = effect.get("accepted_proposals")
    if not isinstance(accepted, list) or not accepted:
        return None
    ids: list[str] = []
    for item in accepted:
        if isinstance(item, Mapping):
            assertion_id = item.get("assertion_id")
        else:
            assertion_id = getattr(item, "assertion_id", None)
        if not isinstance(assertion_id, str) or not assertion_id.strip():
            return None
        ids.append(assertion_id)
    if len(ids) != len(set(ids)):
        return None
    return ids


def _contribution_order_disposition(
    contribution: GraphContribution,
    persisted_ids: list[str],
    *,
    sealed_proposal: Mapping[str, Any] | None = None,
) -> Literal["exact", "legacy_seal_order", "corrupt_permutation", "set_mismatch"]:
    """Classify persisted assertion order against reconstruction and historical seal.

    - reconstruction order == persisted → current exact proposal
    - known historical seal order == persisted → legacy; supersession only before
      a commit claim
    - any other same-set permutation → durable-authority corruption
    """
    reconstruction = _extract_accepted_ids(contribution)
    persisted = list(persisted_ids)
    if reconstruction == persisted:
        return "exact"
    if len(reconstruction) != len(persisted) or set(reconstruction) != set(persisted):
        return "set_mismatch"
    historical = _historical_seal_order_ids(sealed_proposal)
    if (
        historical is not None
        and persisted == historical
        and historical != reconstruction
    ):
        return "legacy_seal_order"
    return "corrupt_permutation"


_LEGACY_SEAL_ORDER_MESSAGE = (
    "proposal accepted_assertion_ids uses pre-reconstruction seal order; "
    "supersede the active proposal and re-prepare under current c1 "
    "(reconstruction order) before confirm"
)

_LEGACY_COMMIT_CLAIM_NO_REVISION_MESSAGE = (
    "commit claim uses pre-reconstruction seal-order assertion IDs and no "
    "recoverable revision was found; a new publication operation is required "
    "(proposal supersession remains blocked after a commit claim)"
)

_IDENTITY_UNAVAILABLE_LABELS = frozenset(
    {
        "publication_identity_storage_unavailable",
        "publication_identity_graph_unavailable",
        "publication_identity_busy",
    }
)
_IDENTITY_INTEGRITY_LABELS = frozenset({"publication_identity_integrity_failure"})
_IDENTITY_SUCCESS_LABELS = frozenset(
    {
        "publication_identity_connected_existing",
        "publication_identity_created_new",
    }
)
_PUBLICATION_UNAVAILABLE_LABELS = frozenset(
    {
        "publication_draft_unavailable",
        "publication_graph_unavailable",
        "publication_storage_unavailable",
        "publication_busy",
    }
)
_PUBLICATION_INTEGRITY_LABELS = frozenset({"publication_integrity_failure"})

IdentityAuthorityStatus = Literal["ok", "unavailable", "mismatch", "integrity"]
PublicationAuthorityStatus = Literal["ok", "unavailable", "mismatch", "integrity"]


def _classify_identity_authority(
    identity: Any,
    *,
    record: ThreatPublicationCommitV1,
    proposal: ThreatPublicationProposalV1 | None = None,
    require_active: bool = True,
) -> tuple[IdentityAuthorityStatus, Any | None, str | None]:
    """Classify a complete SBW09b resolution against the commit (and proposal).

    Binds more than ``selected_target``: publishable decision, exact
    request/candidate/source/parent identity, and decision-specific node identity.

    ``require_active=True`` (admission / retry): the named resolution must still
    be active and carry a publishable success label. Superseded or inactive
    resolutions are mismatches.

    ``require_active=False`` (post-commit verification): validate the exact named
    historical resolution content when readable, but do not require it to remain
    active. Later supersession must not permanently block verification of a known
    committed revision.

    ``read_identity_resolution`` represents missing/unavailable/integrity-failed
    dependencies as ``resolution is None`` plus a result label — it does not raise.
    """
    label = str(identity.response.result_label)
    resolution = identity.response.resolution
    if label in _IDENTITY_INTEGRITY_LABELS:
        return "integrity", None, f"identity dependency integrity failure: {label}"
    if resolution is None:
        if label in _IDENTITY_INTEGRITY_LABELS:
            return "integrity", None, f"identity dependency integrity failure: {label}"
        if label in _IDENTITY_UNAVAILABLE_LABELS:
            return "unavailable", None, f"identity dependency unavailable: {label}"
        if label == "publication_identity_not_found":
            if require_active:
                return "mismatch", None, f"identity dependency mismatch: {label}"
            return "unavailable", None, f"identity dependency unavailable: {label}"
        if label == "publication_identity_operation_not_ready":
            return "mismatch", None, f"identity dependency mismatch: {label}"
        if label in {"publication_identity_refused", "publication_identity_superseded"}:
            return "mismatch", None, f"identity dependency mismatch: {label}"
        return "integrity", None, f"identity resolution missing for label: {label}"

    resolution_state = getattr(resolution, "state", None)
    is_superseded = (
        label == "publication_identity_superseded" or resolution_state == "superseded"
    )
    if require_active:
        if is_superseded:
            return "mismatch", None, "identity resolution is superseded"
        if resolution_state != "active":
            return (
                "mismatch",
                None,
                f"identity resolution state is {resolution_state}",
            )
        if label == "publication_identity_refused" or getattr(resolution, "decision", None) == "refuse":
            return "mismatch", None, "identity resolution is not publishable"
        if label not in _IDENTITY_SUCCESS_LABELS:
            return "mismatch", None, f"identity result label unexpected: {label}"
    else:
        if label == "publication_identity_refused" or getattr(resolution, "decision", None) == "refuse":
            return "mismatch", None, "identity resolution is not publishable"
        if label not in _IDENTITY_SUCCESS_LABELS and not is_superseded:
            return "mismatch", None, f"identity result label unexpected: {label}"
        if resolution_state not in {"active", "superseded"}:
            return (
                "mismatch",
                None,
                f"identity resolution state is {resolution_state}",
            )

    if proposal is not None and (
        record.source_digest != proposal.source_digest
        or record.resolution_request_digest != proposal.resolution_request_digest
        or record.candidate_set_digest != proposal.candidate_set_digest
        or record.expected_parent_revision_id != proposal.expected_parent_revision_id
        or record.decision != proposal.decision
        or record.threat_node_id != proposal.threat_node_id
        or record.resolution_id != proposal.resolution_id
    ):
        return "integrity", None, "commit record identity fields disagree with proposal"

    expected_source = proposal.source_digest if proposal is not None else record.source_digest
    expected_request = (
        proposal.resolution_request_digest
        if proposal is not None
        else record.resolution_request_digest
    )
    expected_candidate = (
        proposal.candidate_set_digest if proposal is not None else record.candidate_set_digest
    )
    expected_parent = (
        proposal.expected_parent_revision_id
        if proposal is not None
        else record.expected_parent_revision_id
    )
    expected_decision = proposal.decision if proposal is not None else record.decision
    expected_threat = proposal.threat_node_id if proposal is not None else record.threat_node_id

    if getattr(resolution, "resolution_id", None) != record.resolution_id:
        return "mismatch", None, "identity resolution_id mismatch"
    if (
        getattr(resolution, "draft_id", None) != record.draft_id
        or getattr(resolution, "operation_id", None) != record.operation_id
    ):
        return "mismatch", None, "identity parent identity mismatch"
    if getattr(resolution, "source_digest", None) != expected_source:
        return "mismatch", None, "identity source_digest mismatch"
    if getattr(resolution, "request_digest", None) != expected_request:
        return "mismatch", None, "identity resolution request_digest mismatch"
    if getattr(resolution, "candidate_set_digest", None) != expected_candidate:
        return "mismatch", None, "identity candidate_set_digest mismatch"
    if getattr(resolution, "expected_parent_revision_id", None) != expected_parent:
        return "mismatch", None, "identity expected_parent_revision_id mismatch"
    if getattr(resolution, "decision", None) != expected_decision:
        return "mismatch", None, "identity decision mismatch"

    if expected_decision == "create_new":
        if getattr(resolution, "created_node_id", None) != expected_threat:
            return "mismatch", None, "identity created_node_id mismatch"
        if getattr(resolution, "selected_target", None) is not None:
            return "mismatch", None, "identity create_new has selected_target"
        if record.selected_target is not None:
            return "integrity", None, "commit record create_new has selected_target"
        if require_active and label != "publication_identity_created_new":
            return "mismatch", None, f"identity result label unexpected: {label}"
        if not require_active and label not in {
            "publication_identity_created_new",
            "publication_identity_superseded",
        }:
            return "mismatch", None, f"identity result label unexpected: {label}"
    elif expected_decision == "connect_existing":
        selected_target = getattr(resolution, "selected_target", None)
        if selected_target is None:
            return "mismatch", None, "identity resolution missing selected_target"
        if getattr(selected_target, "node_id", None) != expected_threat:
            return "mismatch", None, "identity selected_target node_id mismatch"
        if not _selected_targets_equal(record.selected_target, selected_target):
            return "mismatch", None, "identity selected_target mismatch"
        if require_active and label != "publication_identity_connected_existing":
            return "mismatch", None, f"identity result label unexpected: {label}"
        if not require_active and label not in {
            "publication_identity_connected_existing",
            "publication_identity_superseded",
        }:
            return "mismatch", None, f"identity result label unexpected: {label}"
    else:
        return "mismatch", None, "identity decision is not publishable"

    return "ok", resolution, None


def _classify_publication_operation_authority(
    refresh: Any,
    *,
    record: ThreatPublicationCommitV1,
) -> tuple[PublicationAuthorityStatus, Any | None, str | None]:
    """Classify SBW09a refresh authority for retry revalidation."""
    label = str(refresh.response.result_label)
    operation = refresh.response.operation
    if label in _PUBLICATION_INTEGRITY_LABELS:
        return "integrity", None, f"publication dependency integrity failure: {label}"
    if operation is None:
        if label in _PUBLICATION_UNAVAILABLE_LABELS:
            return "unavailable", None, f"publication dependency unavailable: {label}"
        if label == "publication_ready":
            return "integrity", None, "publication_ready missing operation"
        return "mismatch", None, f"publication operation not usable: {label}"
    if label != "publication_ready":
        if label in _PUBLICATION_UNAVAILABLE_LABELS:
            return "unavailable", None, f"publication dependency unavailable: {label}"
        return "mismatch", None, f"publication operation not ready: {label}"
    if operation.source_digest != record.source_digest:
        return "mismatch", None, "publication source_digest mismatch"
    if operation.expected_parent_revision_id != record.expected_parent_revision_id:
        return "mismatch", None, "publication expected_parent_revision_id mismatch"
    return "ok", operation, None


_ADMISSION_PROBE_COMMIT_ID = "00000000-0000-4000-8000-000000000001"


def _identity_unavailable_commit_label(identity_label: str) -> ThreatPublicationCommitResultLabel:
    if identity_label == "publication_identity_storage_unavailable":
        return "publication_commit_storage_unavailable"
    if identity_label == "publication_identity_graph_unavailable":
        return "publication_commit_graph_unavailable"
    return "publication_commit_recovery_pending"


def _publication_unavailable_commit_label(pub_label: str) -> ThreatPublicationCommitResultLabel:
    if pub_label in {"publication_draft_unavailable", "publication_storage_unavailable"}:
        return "publication_commit_storage_unavailable"
    if pub_label == "publication_graph_unavailable":
        return "publication_commit_graph_unavailable"
    return "publication_commit_recovery_pending"


def _admission_authority_probe_record(
    *,
    draft_id: str,
    operation_id: str,
    proposal: ThreatPublicationProposalV1,
    selected_target: Any | None = None,
) -> ThreatPublicationCommitV1:
    """Minimal proposal-bound record for admission authority classification only."""
    now = _utc_now_iso()
    raw_digest = "0" * 64
    return ThreatPublicationCommitV1.model_validate(
        {
            "commit_id": _ADMISSION_PROBE_COMMIT_ID,
            "request_digest": f"sha256:{raw_digest}",
            "draft_id": draft_id,
            "operation_id": operation_id,
            "proposal_id": proposal.proposal_id,
            "proposal_request_digest": proposal.request_digest,
            "sealed_proposal_digest": proposal.sealed_proposal_digest,
            "sealed_proposal_version": proposal.sealed_proposal_version,
            "resolution_id": proposal.resolution_id,
            "source_digest": proposal.source_digest,
            "resolution_request_digest": proposal.resolution_request_digest,
            "candidate_set_digest": proposal.candidate_set_digest,
            "world_id": _proposal_effect_world_id(proposal) or "world_1",
            "campaign_id": _proposal_effect_campaign_id(proposal) or "campaign_1",
            "expected_parent_revision_id": proposal.expected_parent_revision_id,
            "expected_contribution_id": proposal.expected_contribution_id,
            "expected_contribution_source_payload_sha256": raw_digest,
            "accepted_assertion_ids": list(proposal.accepted_assertion_ids),
            "decision": proposal.decision,
            "threat_node_id": proposal.threat_node_id,
            "selected_target": (
                selected_target.model_dump(mode="json", by_alias=True)
                if selected_target is not None
                else None
            ),
            "external_resource_node_id": proposal.effect_summary.external_resource_node_id,
            "binding_id": proposal.effect_summary.binding_edge_id,
            "binding_edge_id": proposal.effect_summary.binding_edge_id,
            "state": "committing",
            "merge_attempt_count": 1,
            "committed_revision_id": None,
            "created_by": "admission-probe",
            "created_at": now,
            "updated_at": now,
        }
    )


def _admission_outcome_for_identity(
    *,
    draft_id: str,
    operation_id: str,
    proposal_id: str,
    commit_id: str,
    identity: Any,
    status: IdentityAuthorityStatus,
    detail: str | None,
) -> CommitOutcome:
    label = str(identity.response.result_label)
    if status == "integrity":
        return CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                commit_id,
                "publication_commit_integrity_failure",
                message=detail,
            )
        )
    if status == "unavailable":
        return CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                commit_id,
                _identity_unavailable_commit_label(label),
                message=detail,
            )
        )
    conflict_label: ThreatPublicationCommitResultLabel = (
        "publication_commit_operation_not_ready"
        if label == "publication_identity_operation_not_ready"
        else "publication_commit_resolution_not_active"
    )
    return CommitOutcome(
        _response(
            draft_id,
            operation_id,
            proposal_id,
            commit_id,
            conflict_label,
            message=detail,
        )
    )


def _admission_outcome_for_publication(
    *,
    draft_id: str,
    operation_id: str,
    proposal_id: str,
    commit_id: str,
    refresh: Any,
    status: PublicationAuthorityStatus,
    detail: str | None,
) -> CommitOutcome:
    label = str(refresh.response.result_label)
    if status == "integrity":
        return CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                commit_id,
                "publication_commit_integrity_failure",
                message=detail,
            )
        )
    if status == "unavailable":
        return CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                commit_id,
                _publication_unavailable_commit_label(label),
                message=detail,
            )
        )
    return CommitOutcome(
        _response(
            draft_id,
            operation_id,
            proposal_id,
            commit_id,
            "publication_commit_operation_not_ready",
            message=detail or label,
        )
    )


def _persist_committed_unverified_receipt(
    root: Path,
    prior: ThreatPublicationCommitV1,
    updated: ThreatPublicationCommitV1,
) -> tuple[ThreatPublicationCommitV1, ThreatPublicationCommitResultLabel | None, str | None]:
    """Persist a known committed_unverified receipt.

    On receipt-save failure after a core-proven revision, durable-consume the
    governed retry (``merge_attempt_count=2``) so a later zero-match replay
    cannot enter ``_maybe_retry``. The prior committing claim remains until
    c2a recovery can persist the receipt (§10.6).
    """
    try:
        _save_commit(root, updated)
    except ThreatPublicationCommitStorageError as exc:
        label: ThreatPublicationCommitResultLabel = (
            "publication_commit_integrity_failure"
            if getattr(exc, "kind", "unavailable") == "integrity"
            else "publication_commit_storage_unavailable"
        )
        no_retry = prior
        if prior.state == "committing" and prior.merge_attempt_count == 1:
            no_retry = _with_updated(prior, merge_attempt_count=2)
            try:
                _save_commit(root, no_retry)
            except ThreatPublicationCommitStorageError:
                # Both receipt and no-retry saves failed — return durable disk truth.
                return prior, label, str(exc)
        return no_retry, label, str(exc)
    return updated, None, None


_AUTHORED_FIELD_PREDICATES = frozenset({"description", "threat_kind", "intended_role", "tag"})
_MECHANICS_SCAN_KEYS = FORBIDDEN_MECHANICS_KEYS | frozenset({"mechanics_body"})


def _scan_forbidden_mechanics_keys(value: Any, *, context: str) -> str | None:
    forbidden: set[str] = set()

    def collect(candidate: Any) -> None:
        if isinstance(candidate, Mapping):
            forbidden.update(_MECHANICS_SCAN_KEYS.intersection(candidate))
            for nested in candidate.values():
                collect(nested)
        elif isinstance(candidate, list):
            for nested in candidate:
                collect(nested)

    collect(value)
    if forbidden:
        return f"{context} must not contain mechanics fields: {sorted(forbidden)}"
    return None


def _proposal_effect_world_id(proposal: ThreatPublicationProposalV1) -> str:
    effect = proposal.sealed_proposal.get("effect") or {}
    return str(effect.get("world_id") or "").strip()


def _proposal_effect_campaign_id(proposal: ThreatPublicationProposalV1) -> str:
    effect = proposal.sealed_proposal.get("effect") or {}
    meta = effect.get("contribution_meta") or {}
    scope = meta.get("campaign_scope")
    if isinstance(scope, str) and scope.strip():
        return scope.strip()
    uri = str(effect.get("verified_source_uri") or "")
    # threat-publication://{world_id}/{campaign_id}/{draft_id}/{operation_id}
    prefix = "threat-publication://"
    if uri.startswith(prefix):
        parts = uri[len(prefix) :].split("/")
        if len(parts) >= 2 and parts[1].strip():
            return parts[1].strip()
    return ""


def _binding_id_from_contribution(
    contribution: GraphContribution, record: ThreatPublicationCommitV1
) -> str | None:
    binding_value = _binding_assertion_value(contribution, record)
    if binding_value is None:
        return None
    try:
        parsed = parse_threat_statblock_binding_assertion(
            subject_node_id=record.threat_node_id,
            target_node_id=record.external_resource_node_id,
            predicate="uses_statblock",
            value=dict(binding_value),
        )
    except ValueError:
        return None
    if parsed is None:
        return None
    return parsed.binding_id


def _selected_targets_equal(left: Any | None, right: Any | None) -> bool:
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    left_dump = (
        left.model_dump(mode="json", by_alias=True)
        if hasattr(left, "model_dump")
        else dict(left)
    )
    right_dump = (
        right.model_dump(mode="json", by_alias=True)
        if hasattr(right, "model_dump")
        else dict(right)
    )
    return left_dump == right_dump


def _record_matches_proposal_authority(
    record: ThreatPublicationCommitV1,
    proposal: ThreatPublicationProposalV1,
    *,
    contribution: GraphContribution | None = None,
    selected_target_authority: Any | None = None,
) -> str | None:
    checks: tuple[tuple[Any, Any, str], ...] = (
        (record.proposal_id, proposal.proposal_id, "proposal_id"),
        (record.proposal_request_digest, proposal.request_digest, "proposal_request_digest"),
        (record.sealed_proposal_digest, proposal.sealed_proposal_digest, "sealed_proposal_digest"),
        (record.sealed_proposal_version, proposal.sealed_proposal_version, "sealed_proposal_version"),
        (record.resolution_id, proposal.resolution_id, "resolution_id"),
        (record.source_digest, proposal.source_digest, "source_digest"),
        (record.resolution_request_digest, proposal.resolution_request_digest, "resolution_request_digest"),
        (record.candidate_set_digest, proposal.candidate_set_digest, "candidate_set_digest"),
        (record.expected_parent_revision_id, proposal.expected_parent_revision_id, "expected_parent_revision_id"),
        (record.expected_contribution_id, proposal.expected_contribution_id, "expected_contribution_id"),
        (list(record.accepted_assertion_ids), list(proposal.accepted_assertion_ids), "accepted_assertion_ids"),
        (record.decision, proposal.decision, "decision"),
        (record.threat_node_id, proposal.threat_node_id, "threat_node_id"),
        (
            record.external_resource_node_id,
            proposal.effect_summary.external_resource_node_id,
            "external_resource_node_id",
        ),
        (record.binding_edge_id, proposal.effect_summary.binding_edge_id, "binding_edge_id"),
        (record.world_id, _proposal_effect_world_id(proposal), "world_id"),
        (record.campaign_id, _proposal_effect_campaign_id(proposal), "campaign_id"),
    )
    for actual, expected, label in checks:
        if actual != expected:
            return f"{label}_mismatch"

    if contribution is not None:
        derived_binding = _binding_id_from_contribution(contribution, record)
        if derived_binding is None or derived_binding != record.binding_id:
            return "binding_id_mismatch"
        if edge_id_from_binding_id(record.binding_id) != record.binding_edge_id:
            return "binding_id_edge_mismatch"

    if record.decision == "create_new":
        if record.selected_target is not None:
            return "selected_target_mismatch"
    else:
        if not _selected_targets_equal(record.selected_target, selected_target_authority):
            return "selected_target_mismatch"
    return None


def _record_contribution_matches_authority(
    record: ThreatPublicationCommitV1,
    proposal: ThreatPublicationProposalV1,
    contribution: GraphContribution,
    *,
    selected_target_authority: Any | None = None,
) -> tuple[GraphContribution | None, str | None]:
    authority = _record_matches_proposal_authority(
        record,
        proposal,
        contribution=contribution,
        selected_target_authority=selected_target_authority,
    )
    if authority is not None:
        return None, authority
    if contribution.contribution_id != record.expected_contribution_id:
        return None, "contribution_id_mismatch"
    if not _unmodified_contribution_matches_expected_ids(
        contribution, list(record.accepted_assertion_ids)
    ):
        return None, "accepted_assertion_ids_mismatch"
    digest = kernel.compute_contribution_source_payload_sha256(contribution)
    if digest != record.expected_contribution_source_payload_sha256:
        return None, "contribution_source_digest_mismatch"
    return contribution, None


def _historical_contribution_source_digest(
    contribution: GraphContribution,
    sealed_proposal: Mapping[str, Any] | None,
) -> str | None:
    """Digest of the reconstructed contribution reordered to historical seal order.

    Old c1 persisted seal-time assertion order; the contribution source digest
    therefore differs from current reconstruction order even when the assertion
    set is identical. Derive the historical payload from immutable sealed
    ``effect.accepted_proposals`` order plus the reconstructed assertion objects.
    """
    historical_ids = _historical_seal_order_ids(sealed_proposal)
    if historical_ids is None:
        return None
    by_id = {item.assertion_id: item for item in contribution.accepted_assertions}
    if len(by_id) != len(historical_ids) or set(by_id) != set(historical_ids):
        return None
    try:
        ordered = contribution.model_copy(
            update={"accepted_assertions": [by_id[assertion_id] for assertion_id in historical_ids]}
        )
    except KeyError:
        return None
    return kernel.compute_contribution_source_payload_sha256(ordered)


def _record_matches_c2a_trust(
    record: ThreatPublicationCommitV1,
    proposal: ThreatPublicationProposalV1,
    contribution: GraphContribution,
    *,
    order_disposition: Literal[
        "exact", "legacy_seal_order", "corrupt_permutation", "set_mismatch"
    ],
) -> str | None:
    """Validate fields required to trust the c2a lookup key before reconciliation.

    Live identity selected_target authority is deferred until after a zero-match
    c2a result (committing replay must consult revision authority first).
    Legacy seal-order claims keep contribution_id trust and require the persisted
    source digest to equal the derived historical seal-order payload digest —
    not the current reconstruction digest.
    """
    if order_disposition in {"corrupt_permutation", "set_mismatch"}:
        return "accepted_assertion_ids_mismatch"

    # Snapshot self-consistency only — live identity is checked after zero match.
    selected_target_authority = (
        None if record.decision == "create_new" else record.selected_target
    )
    authority = _record_matches_proposal_authority(
        record,
        proposal,
        contribution=contribution,
        selected_target_authority=selected_target_authority,
    )
    if authority is not None:
        return authority
    if contribution.contribution_id != record.expected_contribution_id:
        return "contribution_id_mismatch"
    if order_disposition == "legacy_seal_order":
        historical_digest = _historical_contribution_source_digest(
            contribution, proposal.sealed_proposal
        )
        if (
            historical_digest is None
            or historical_digest != record.expected_contribution_source_payload_sha256
        ):
            return "contribution_source_digest_mismatch"
        return None
    if not _unmodified_contribution_matches_expected_ids(
        contribution, list(record.accepted_assertion_ids)
    ):
        return "accepted_assertion_ids_mismatch"
    digest = kernel.compute_contribution_source_payload_sha256(contribution)
    if digest != record.expected_contribution_source_payload_sha256:
        return "contribution_source_digest_mismatch"
    return None


def _advance_committed_verification(
    *,
    root: Path,
    world_root: Path,
    record: ThreatPublicationCommitV1,
    proposal: ThreatPublicationProposalV1,
    contribution: GraphContribution,
    lookup_fn: LookupFn,
) -> tuple[ThreatPublicationCommitV1, ThreatPublicationCommitResultLabel, str | None]:
    """Verify a persisted committed_unverified receipt; never hide it on verify-save failure.

    After a committed revision is known:

    - create_new: verification consumes record/proposal/contribution/revision only
      (no SBW09b read).
    - connect_existing: validate the exact named historical resolution content when
      needed, but do not require it to remain active. Unavailable keeps the receipt;
      contradictory content is integrity failure; exact historical content may verify.
    """
    if record.decision == "connect_existing":
        identity = read_identity_resolution(
            root, record.draft_id, record.operation_id, record.resolution_id
        )
        identity_status, _resolution, identity_detail = _classify_identity_authority(
            identity, record=record, proposal=proposal, require_active=False
        )
        if identity_status == "unavailable":
            return (
                record,
                "publication_commit_committed_unverified",
                identity_detail,
            )
        if identity_status in {"integrity", "mismatch"}:
            return (
                record,
                "publication_commit_integrity_failure",
                identity_detail,
            )

    verified = _verify_committed(
        root=root,
        world_root=world_root,
        record=record,
        proposal=proposal,
        contribution=contribution,
        lookup_fn=lookup_fn,
    )
    try:
        _save_commit(root, verified)
    except ThreatPublicationCommitStorageError:
        try:
            persisted = load_threat_publication_commit_ledger_unlocked(
                root, record.draft_id, record.operation_id
            )
            durable_record = persisted.commit if persisted is not None else record
        except ThreatPublicationCommitStorageError:
            durable_record = record
        return (
            durable_record,
            "publication_commit_committed_unverified",
            "verification could not persist",
        )
    return verified, _label_for_state(verified), None


def _statblock_id_from_resource_node_id(node_id: str) -> str | None:
    prefix = "external:dungeonmind:statblock:"
    if not node_id.startswith(prefix):
        return None
    statblock_id = node_id[len(prefix) :]
    return statblock_id or None


def _resource_statblock_id_from_contribution(
    contribution: GraphContribution, resource_node_id: str
) -> str | None:
    for assertion in contribution.accepted_assertions:
        if assertion.assertion_kind != "node":
            continue
        if assertion.subject_node_id != resource_node_id:
            continue
        payload = assertion.value.get("external_resource")
        if isinstance(payload, Mapping):
            resource_id = payload.get("resource_id")
            if isinstance(resource_id, str) and resource_id:
                return resource_id
    return _statblock_id_from_resource_node_id(resource_node_id)


def _provenance_domains_for_object(
    contribution: GraphContribution, node_id: str
) -> list[str]:
    """Return source domains declared by assertions connected to one graph object.

    Projection nodes aggregate provenance from their authored fields and
    connected binding edges, so verification compares this declared package
    contract as a subset of the projected domains rather than requiring the
    projection to discard legitimate connected-source domains.
    """
    domains: set[str] = set()
    for assertion in contribution.accepted_assertions:
        connected = (
            assertion.subject_node_id == node_id
            or (
                assertion.assertion_kind == "edge"
                and assertion.target_node_id == node_id
            )
        )
        if connected:
            domains.update(normalize_assertion_provenance(assertion).source_domains)
    return sorted(domains)


def _identity_fields_match(
    selected_target: Any,
    node: Any,
    *,
    store: Any | None = None,
    published_binding_id: str | None = None,
) -> bool:
    target_dump = selected_target.model_dump(mode="json", by_alias=True)
    node_dump = {
        "node_id": node.node_id,
        "label": node.label,
        "kind": node.kind,
        "role": node.role,
        "aliases": list(node.aliases),
        "campaign_scope": getattr(node, "campaign_scope", None),
        "summary": getattr(node, "summary", None),
        "source_domains": list(getattr(node, "source_domains", []) or []),
    }
    for key in (
        "node_id",
        "label",
        "kind",
        "role",
        "aliases",
        "campaign_scope",
        "summary",
        "source_domains",
    ):
        if key not in target_dump:
            continue
        expected = target_dump[key]
        actual = node_dump.get(key)
        if key == "kind":
            if str(expected).casefold() != str(actual).casefold():
                return False
        elif key in {"aliases", "source_domains"}:
            if sorted(expected or []) != sorted(actual or []):
                return False
        elif expected != actual:
            return False

    # Candidate binding_ids are the pre-publication parent snapshot. Connect-existing
    # publication adds record.binding_id, so the committed store must equal
    # selected_target.binding_ids ∪ {published binding}, not the pre-publication list alone.
    if "binding_ids" in target_dump and store is not None:
        expected_bindings = set(target_dump.get("binding_ids") or [])
        if published_binding_id:
            expected_bindings = expected_bindings | {published_binding_id}
        actual_bindings: set[str] = set()
        for edge in (store.edges or {}).values():
            binding = getattr(edge, "threat_statblock_binding", None)
            if binding is None:
                continue
            if edge.source_node_id != node.node_id and edge.target_node_id != node.node_id:
                continue
            binding_id = getattr(binding, "binding_id", None)
            if isinstance(binding_id, str) and binding_id:
                actual_bindings.add(binding_id)
        if actual_bindings != expected_bindings:
            return False
    return True


def _verify_external_resource_node(
    node: Any,
    *,
    statblock_id: str,
    expected_source_domains: list[str] | None = None,
) -> str | None:
    expected_node_id = external_statblock_node_id(statblock_id)
    expected_label = f"External statblock {statblock_id}"
    if node.node_id != expected_node_id:
        return "external_resource_node_id_mismatch"
    if str(node.kind).casefold() != "external_resource":
        return "external_resource_kind_mismatch"
    if node.role != "statblock":
        return "external_resource_role_mismatch"
    if node.label != expected_label:
        return "external_resource_label_mismatch"
    if sorted(node.aliases) != sorted([expected_label]):
        return "external_resource_aliases_mismatch"
    expected_domains = sorted(expected_source_domains or ["manual_seed"])
    if not set(expected_domains).issubset(set(node.source_domains)):
        return "external_resource_source_domain_mismatch"
    if node.external_resource is None:
        return "external_resource_payload_missing"
    try:
        expected = ExternalResourceV1.model_validate(
            {
                "schema": "dmb_external_resource_v1",
                "provider": PROVIDER,
                "resource_type": "statblock",
                "resource_id": statblock_id,
                "contract": CONTRACT,
                "contract_version": CONTRACT_VERSION,
            }
        )
        ExternalResourceV1.model_validate(
            node.external_resource.model_dump(mode="json", by_alias=True)
        )
    except Exception:
        return "external_resource_payload_invalid"
    if node.external_resource.model_dump(mode="json", by_alias=True) != expected.model_dump(
        mode="json", by_alias=True
    ):
        return "external_resource_payload_mismatch"
    return None


def _binding_assertion_value(contribution: GraphContribution, record: ThreatPublicationCommitV1) -> Mapping[str, Any] | None:
    for assertion in contribution.accepted_assertions:
        if assertion.assertion_kind != "edge":
            continue
        if assertion.subject_node_id != record.threat_node_id:
            continue
        if assertion.target_node_id != record.external_resource_node_id:
            continue
        if assertion.predicate != "uses_statblock":
            continue
        value = assertion.value
        if isinstance(value, Mapping):
            return value
    return None


def _verify_binding_edge(
    edge: Any,
    *,
    record: ThreatPublicationCommitV1,
    binding_value: Mapping[str, Any],
) -> str | None:
    if edge.edge_id != record.binding_edge_id:
        return "binding_edge_id_mismatch"
    if edge.source_node_id != record.threat_node_id:
        return "binding_source_mismatch"
    if edge.target_node_id != record.external_resource_node_id:
        return "binding_target_mismatch"
    if edge.predicate != "uses_statblock":
        return "binding_predicate_mismatch"
    if edge.direction != "outbound":
        return "binding_direction_mismatch"
    try:
        parsed = parse_threat_statblock_binding_assertion(
            subject_node_id=edge.source_node_id,
            target_node_id=edge.target_node_id,
            predicate=edge.predicate,
            value=dict(binding_value),
        )
    except ValueError:
        return "binding_assertion_parse_failed"
    if parsed is None:
        return "binding_assertion_missing"
    if edge.threat_statblock_binding is None:
        return "binding_payload_missing"
    try:
        ThreatStatblockBindingV1.model_validate(
            edge.threat_statblock_binding.model_dump(mode="json", by_alias=True)
        )
    except Exception:
        return "binding_payload_invalid"
    if parsed.binding_id != record.binding_id:
        return "binding_id_mismatch"
    if edge.threat_statblock_binding != parsed:
        return "binding_payload_mismatch"
    return None


def _threat_node_assertion(
    contribution: GraphContribution, threat_node_id: str
) -> Any | None:
    for assertion in contribution.accepted_assertions:
        if assertion.assertion_kind != "node":
            continue
        if assertion.subject_node_id != threat_node_id:
            continue
        kind = str((assertion.value or {}).get("kind", "")).casefold()
        if kind == "threat":
            return assertion
    return None


def _authored_field_assertions(
    contribution: GraphContribution, threat_node_id: str
) -> list[Any]:
    return [
        assertion
        for assertion in contribution.accepted_assertions
        if assertion.assertion_kind == "attribute"
        and assertion.subject_node_id == threat_node_id
        and assertion.predicate in _AUTHORED_FIELD_PREDICATES
    ]


def _verify_create_new_materialization(
    *,
    store: Any,
    contribution: GraphContribution,
    record: ThreatPublicationCommitV1,
) -> list[str]:
    codes: list[str] = []
    node_assertion = _threat_node_assertion(contribution, record.threat_node_id)
    if node_assertion is None:
        codes.append("missing_threat_node_assertion")
        return codes
    threat = store.nodes.get(record.threat_node_id)
    if threat is None:
        codes.append("missing_threat_node")
        return codes
    expected = node_assertion.value or {}
    if str(threat.kind).casefold() != str(expected.get("kind", "")).casefold():
        codes.append("threat_kind_materialization_mismatch")
    if threat.role != expected.get("role"):
        codes.append("threat_role_materialization_mismatch")
    if threat.label != node_assertion.label:
        codes.append("threat_label_materialization_mismatch")
    if sorted(threat.aliases) != sorted(list(expected.get("aliases") or [])):
        codes.append("threat_aliases_materialization_mismatch")
    if sorted(threat.source_domains) != sorted(list(expected.get("source_domains") or [])):
        codes.append("threat_source_domains_materialization_mismatch")

    authored_ids = {item.assertion_id for item in _authored_field_assertions(contribution, record.threat_node_id)}
    for assertion_id in record.accepted_assertion_ids:
        if assertion_id not in authored_ids:
            continue
        raw = (store.assertion_support or {}).get(assertion_id)
        if not isinstance(raw, dict):
            codes.append(f"missing_authored_support:{assertion_id}")
            continue
        if raw.get("support_state") != "supported":
            codes.append(f"unsupported_authored:{assertion_id}")
        active = list(raw.get("active_contribution_ids") or [])
        if record.expected_contribution_id not in active:
            codes.append(f"authored_support_contribution_mismatch:{assertion_id}")
    for assertion in _authored_field_assertions(contribution, record.threat_node_id):
        if assertion.assertion_id not in record.accepted_assertion_ids:
            codes.append(f"missing_authored_assertion:{assertion.assertion_id}")
    return codes


def _verify_connect_existing_constraints(
    *,
    store: Any,
    contribution: GraphContribution,
    record: ThreatPublicationCommitV1,
) -> list[str]:
    codes: list[str] = []
    for assertion in contribution.accepted_assertions:
        if assertion.assertion_kind == "node" and (
            assertion.subject_node_id == record.threat_node_id
            or str((assertion.value or {}).get("kind", "")).casefold() == "threat"
        ):
            codes.append("connect_existing_threat_rewrite")
            break
        if assertion.assertion_kind == "attribute" and assertion.subject_node_id == record.threat_node_id:
            codes.append("connect_existing_threat_attribute_rewrite")
            break
    if record.selected_target is not None:
        target = store.nodes.get(record.threat_node_id)
        if target is None:
            codes.append("connect_target_missing")
        elif not _identity_fields_match(
            record.selected_target,
            target,
            store=store,
            published_binding_id=record.binding_id,
        ):
            codes.append("connect_target_mismatch")
    return codes


def _parsed_contribution_binding(
    contribution: GraphContribution, record: ThreatPublicationCommitV1
) -> ThreatStatblockBindingV1 | None:
    binding_value = _binding_assertion_value(contribution, record)
    if binding_value is None:
        return None
    try:
        return parse_threat_statblock_binding_assertion(
            subject_node_id=record.threat_node_id,
            target_node_id=record.external_resource_node_id,
            predicate="uses_statblock",
            value=dict(binding_value),
        )
    except ValueError:
        return None


def _projection_threat_matches_selected_target(
    threat: Any, selected_target: Any
) -> list[str]:
    """Compare projected Threat immutable fields to the persisted selected-target snapshot."""
    codes: list[str] = []
    target_dump = selected_target.model_dump(mode="json", by_alias=True)
    comparisons: tuple[tuple[str, Any], ...] = (
        ("node_id", threat.node_id),
        ("label", threat.label),
        ("kind", threat.kind),
        ("role", threat.role),
        ("aliases", list(threat.aliases or [])),
        ("campaign_scope", getattr(threat, "campaign_scope", None)),
        ("summary", getattr(threat, "summary", None)),
        ("source_domains", list(getattr(threat, "source_domains", []) or [])),
    )
    for key, actual in comparisons:
        if key not in target_dump:
            continue
        expected = target_dump[key]
        if key == "kind":
            if str(expected).casefold() != str(actual).casefold():
                codes.append(f"projection_connect_threat_{key}_mismatch")
        elif key == "aliases":
            if sorted(expected or []) != sorted(actual or []):
                codes.append(f"projection_connect_threat_{key}_mismatch")
        elif key == "source_domains":
            if not set(expected or []).issubset(set(actual or [])):
                codes.append(f"projection_connect_threat_{key}_mismatch")
        elif expected != actual:
            codes.append(f"projection_connect_threat_{key}_mismatch")
    return codes


def _verify_projection_audit(
    projection: Any,
    *,
    record: ThreatPublicationCommitV1,
    contribution: GraphContribution,
    statblock_id: str,
) -> list[str]:
    codes: list[str] = []
    if projection.snapshot.revision_id != record.committed_revision_id:
        codes.append("projection_revision_mismatch")
        return codes

    nodes_by_id = {node.node_id: node for node in projection.nodes}
    threat = nodes_by_id.get(record.threat_node_id)
    if threat is None:
        codes.append("projection_missing_threat")
    else:
        node_assertion = _threat_node_assertion(contribution, record.threat_node_id)
        if node_assertion is not None:
            expected = node_assertion.value or {}
            if threat.label != node_assertion.label:
                codes.append("projection_threat_label_mismatch")
            if str(threat.kind).casefold() != str(expected.get("kind", "")).casefold():
                codes.append("projection_threat_kind_mismatch")
            if threat.role != expected.get("role"):
                codes.append("projection_threat_role_mismatch")
            if sorted(threat.aliases) != sorted(list(expected.get("aliases") or [])):
                codes.append("projection_threat_aliases_mismatch")
            # Projection may aggregate connected evidence/artifact domains (e.g. binding
            # brings ``statblock``) beyond the Threat node assertion's declared domains.
            # Require the package contract to be a subset of projected domains.
            expected_domains = _provenance_domains_for_object(
                contribution, record.threat_node_id
            )
            if not set(expected_domains).issubset(set(threat.source_domains)):
                codes.append("projection_threat_source_domains_mismatch")
        elif record.decision == "connect_existing" and record.selected_target is not None:
            # No Threat node assertion in connect_existing contributions — bind the
            # projected Threat to the immutable selected-target snapshot fields.
            codes.extend(
                _projection_threat_matches_selected_target(threat, record.selected_target)
            )
        projected_attrs = {
            attr.assertion_id: attr
            for attr in (projection.attributes or [])
            if attr.subject_node_id == record.threat_node_id
        }
        for assertion in _authored_field_assertions(contribution, record.threat_node_id):
            attr = projected_attrs.get(assertion.assertion_id)
            if attr is None:
                codes.append(f"projection_missing_authored_attribute:{assertion.assertion_id}")
                continue
            if attr.predicate != assertion.predicate:
                codes.append(
                    f"projection_authored_predicate_mismatch:{assertion.assertion_id}"
                )
            if dict(attr.value or {}) != dict(assertion.value or {}):
                codes.append(f"projection_authored_value_mismatch:{assertion.assertion_id}")

    resource = nodes_by_id.get(record.external_resource_node_id)
    if resource is None:
        codes.append("projection_missing_resource")
    else:
        resource_reason = _verify_external_resource_node(
            resource,
            statblock_id=statblock_id,
            expected_source_domains=_provenance_domains_for_object(
                contribution, record.external_resource_node_id
            ),
        )
        if resource_reason is not None:
            codes.append(f"projection_{resource_reason}")

    binding_matches = [
        rel
        for rel in projection.relationships
        if rel.edge_id == record.binding_edge_id
    ]
    if len(binding_matches) != 1:
        codes.append("projection_missing_binding")
    else:
        rel = binding_matches[0]
        if rel.source_node_id != record.threat_node_id:
            codes.append("projection_binding_source_mismatch")
        if rel.target_node_id != record.external_resource_node_id:
            codes.append("projection_binding_target_mismatch")
        if rel.predicate != "uses_statblock":
            codes.append("projection_binding_predicate_mismatch")
        # Projection normalizes store "outbound" → closed vocabulary "outgoing".
        if rel.direction != "outgoing":
            codes.append("projection_binding_direction_mismatch")
        if rel.threat_statblock_binding is None:
            codes.append("projection_binding_payload_missing")
        else:
            expected_binding = _parsed_contribution_binding(contribution, record)
            if expected_binding is None:
                codes.append("projection_binding_expected_parse_failed")
            else:
                try:
                    actual_binding = ThreatStatblockBindingV1.model_validate(
                        rel.threat_statblock_binding.model_dump(mode="json", by_alias=True)
                    )
                except Exception:
                    codes.append("projection_binding_payload_invalid")
                else:
                    recomputed = compute_binding_id(
                        threat_node_id=rel.source_node_id,
                        provider=actual_binding.provider,
                        statblock_id=actual_binding.statblock_id,
                        revision_id=actual_binding.revision_id,
                        contract=actual_binding.contract,
                        contract_version=actual_binding.contract_version,
                        definition_digest=actual_binding.definition_digest,
                        role=actual_binding.role,
                        phase_key=actual_binding.phase_key,
                        variant_label=actual_binding.variant_label,
                    )
                    if actual_binding.binding_id != recomputed:
                        codes.append("projection_binding_semantic_id_mismatch")
                    if actual_binding.binding_id != record.binding_id:
                        codes.append("projection_binding_id_mismatch")
                    if actual_binding != expected_binding:
                        codes.append("projection_binding_payload_mismatch")
    return codes


def _contribution_matches_proposal(
    contribution: GraphContribution, proposal: ThreatPublicationProposalV1
) -> bool:
    if contribution.contribution_id != proposal.expected_contribution_id:
        return False
    return _unmodified_contribution_matches_expected_ids(
        contribution, list(proposal.accepted_assertion_ids)
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

    if not _unmodified_contribution_matches_expected_ids(
        contribution, list(record.accepted_assertion_ids)
    ) or not _assertion_ids_match(
        list(record.accepted_assertion_ids), list(proposal.accepted_assertion_ids)
    ):
        return _with_updated(
            record,
            state="committed_unverified",
            verification_status="failed",
            verification_codes=["verification_assertion_order_mismatch"],
            warnings=warnings,
        )

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
    elif status != "failed":
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

    store = None
    statblock_id: str | None = None
    binding_value: Mapping[str, Any] | None = None

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
            statblock_id = _resource_statblock_id_from_contribution(
                contribution, record.external_resource_node_id
            )
            binding_value = _binding_assertion_value(contribution, record)

            assertion_by_id = {
                item.assertion_id: item for item in contribution.accepted_assertions
            }
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
                assertion = assertion_by_id.get(assertion_id)
                if assertion is not None:
                    cid = record.expected_contribution_id
                    expected_evidence = list(assertion.evidence_ref_ids or [])
                    expected_artifacts = (
                        [assertion.source_artifact_id]
                        if assertion.source_artifact_id
                        else []
                    )
                    per_evidence = dict(raw.get("per_contribution_evidence_ref_ids") or {})
                    per_artifacts = dict(
                        raw.get("per_contribution_source_artifact_ids") or {}
                    )
                    if expected_evidence or cid in per_evidence:
                        if list(per_evidence.get(cid) or []) != expected_evidence:
                            codes.append(f"support_evidence_lineage_mismatch:{assertion_id}")
                            status = "failed"
                    if expected_artifacts or cid in per_artifacts:
                        if list(per_artifacts.get(cid) or []) != expected_artifacts:
                            codes.append(
                                f"support_source_artifact_lineage_mismatch:{assertion_id}"
                            )
                            status = "failed"

            resource = store.nodes.get(record.external_resource_node_id)
            binding = store.edges.get(record.binding_edge_id)
            if resource is None:
                codes.append("missing_external_resource")
                status = "failed"
            elif statblock_id is None:
                codes.append("missing_statblock_id")
                status = "failed"
            else:
                resource_reason = _verify_external_resource_node(
                    resource,
                    statblock_id=statblock_id,
                    expected_source_domains=_provenance_domains_for_object(
                        contribution, record.external_resource_node_id
                    ),
                )
                if resource_reason is not None:
                    codes.append(resource_reason)
                    status = "failed"
                try:
                    reject_mechanics_keys(
                        resource.model_dump(mode="json", by_alias=True),
                        context="external resource node",
                    )
                except ValueError as exc:
                    codes.append("external_resource_mechanics_leak")
                    warnings.append(str(exc)[:180])
                    status = "failed"
                leak = _scan_forbidden_mechanics_keys(
                    resource.model_dump(mode="json", by_alias=True),
                    context="external resource node",
                )
                if leak is not None:
                    codes.append("external_resource_mechanics_body_leak")
                    warnings.append(leak[:180])
                    status = "failed"

            if binding is None:
                codes.append("missing_binding_edge")
                status = "failed"
            elif binding_value is None:
                codes.append("missing_binding_assertion")
                status = "failed"
            else:
                binding_reason = _verify_binding_edge(
                    binding,
                    record=record,
                    binding_value=binding_value,
                )
                if binding_reason is not None:
                    codes.append(binding_reason)
                    status = "failed"
                try:
                    reject_mechanics_keys(
                        binding.model_dump(mode="json", by_alias=True),
                        context="binding edge",
                    )
                except ValueError as exc:
                    codes.append("binding_mechanics_leak")
                    warnings.append(str(exc)[:180])
                    status = "failed"
                leak = _scan_forbidden_mechanics_keys(
                    binding.model_dump(mode="json", by_alias=True),
                    context="binding edge",
                )
                if leak is not None:
                    codes.append("binding_mechanics_body_leak")
                    warnings.append(leak[:180])
                    status = "failed"

            for assertion in contribution.accepted_assertions:
                value = assertion.value
                if isinstance(value, Mapping):
                    try:
                        reject_mechanics_keys(value, context="contribution assertion")
                    except ValueError as exc:
                        codes.append("mechanics_body_leak")
                        warnings.append(str(exc)[:180])
                        status = "failed"
                        break
                    leak = _scan_forbidden_mechanics_keys(
                        value, context="contribution assertion"
                    )
                    if leak is not None:
                        codes.append("mechanics_body_leak")
                        warnings.append(leak[:180])
                        status = "failed"
                        break

            if record.decision == "create_new":
                for code in _verify_create_new_materialization(
                    store=store,
                    contribution=contribution,
                    record=record,
                ):
                    codes.append(code)
                    status = "failed"
            else:
                for code in _verify_connect_existing_constraints(
                    store=store,
                    contribution=contribution,
                    record=record,
                ):
                    codes.append(code)
                    status = "failed"

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

        if store is not None and statblock_id is not None:
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
                for code in _verify_projection_audit(
                    projection,
                    record=record,
                    contribution=contribution,
                    statblock_id=statblock_id,
                ):
                    codes.append(code)
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


def _merge_failure_message(result: ContributionMergeResult | None) -> str | None:
    """Return the governed merge failure diagnostic for the UI.

    New merge results carry a structured ``failure_code`` / ``failure_message``
    pair. The prefixed diagnostic fallback is retained only for old injected
    results and persisted records created before that contract existed.
    """
    if result is None:
        return None
    failure_code = getattr(result, "failure_code", None)
    failure_message = getattr(result, "failure_message", None)
    if failure_code == "merge_failed" and failure_message:
        return (
            "World Graph merge rejected the proposal "
            f"({failure_message}). Cancel this publication and prepare again."
        )
    diagnostics = list(getattr(result, "diagnostics", None) or [])
    for item in diagnostics:
        if isinstance(item, str) and item.startswith("merge_failed:"):
            detail = item.removeprefix("merge_failed:").strip()
            if detail:
                return (
                    "World Graph merge rejected the proposal "
                    f"({detail}). Cancel this publication and prepare again."
                )
    if result.published is False:
        return (
            "World Graph merge did not publish a revision. "
            "Cancel this publication and prepare again."
        )
    return None


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
    published_false_message: str | None = None,
) -> tuple[
    ThreatPublicationCommitV1,
    int,
    ThreatPublicationCommitResultLabel,
    bool,
    str | None,
]:
    """Reconcile an uncertain outcome through c2a.

    The fourth return value is True only when the lookup completed and returned
    zero matches with attempt_count==1, so the caller may run the one governed
    recovery retry. Transient lookup unavailability and integrity-unloadable
    authority keep state=committing but must never merge again in this request.
    The fifth return value is an optional response message (e.g. identity gap
    after a recovered committed receipt).
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
            None,
        )
    except OSError:
        return (
            record,
            merge_calls,
            "publication_commit_recovery_pending",
            False,
            None,
        )
    except Exception:
        return (
            record,
            merge_calls,
            "publication_commit_integrity_failure",
            False,
            None,
        )

    if len(matches) > 1:
        updated = _with_updated(record, state="ambiguous")
        _save_commit(root, updated)
        return updated, merge_calls, "publication_commit_outcome_ambiguous", False, None

    if len(matches) == 1:
        try:
            ok, _reason = _core_proof_match(
                manifest=matches[0], record=record, world_root=world_root
            )
        except WorldGraphIntegrityError:
            return record, merge_calls, "publication_commit_integrity_failure", False, None
        if not ok:
            updated = _with_updated(record, state="ambiguous")
            _save_commit(root, updated)
            return updated, merge_calls, "publication_commit_outcome_ambiguous", False, None
        updated = _with_updated(
            record,
            state="committed_unverified",
            committed_revision_id=matches[0].revision_id,
            recovered_via_operation_lookup=True,
            verification_status="not_started",
        )
        persisted, save_label, save_message = _persist_committed_unverified_receipt(
            root, record, updated
        )
        if save_label is not None:
            return persisted, merge_calls, save_label, False, save_message
        updated = persisted
        if proposal is not None and contribution is not None:
            verified, label, message = _advance_committed_verification(
                root=root,
                world_root=world_root,
                record=updated,
                proposal=proposal,
                contribution=contribution,
                lookup_fn=lookup_fn,
            )
            return verified, merge_calls, label, False, message
        return updated, merge_calls, "publication_commit_committed_unverified", False, None

    # zero matches
    if published_false:
        updated = _with_updated(record, state="uncommitted")
        _save_commit(root, updated)
        return (
            updated,
            merge_calls,
            "publication_commit_uncommitted",
            False,
            published_false_message
            or (
                "World Graph merge did not publish a revision. "
                "Cancel this publication and prepare again."
            ),
        )

    if record.merge_attempt_count >= 2:
        updated = _with_updated(record, state="uncommitted")
        _save_commit(root, updated)
        return (
            updated,
            merge_calls,
            "publication_commit_uncommitted",
            False,
            "World Graph merge did not publish after recovery retry. "
            "Cancel this publication and prepare again.",
        )

    # Conditional single retry requires full revalidation by caller.
    return record, merge_calls, "publication_commit_recovery_pending", True, None


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
    probe_selected_target = (
        resolution.selected_target
        if resolution is not None and proposal.decision == "connect_existing"
        else None
    )
    probe = _admission_authority_probe_record(
        draft_id=draft_id,
        operation_id=operation_id,
        proposal=proposal,
        selected_target=probe_selected_target,
    )
    identity_status, resolution, identity_detail = _classify_identity_authority(
        identity, record=probe, proposal=proposal, require_active=True
    )
    if identity_status != "ok":
        return (
            None,
            _admission_outcome_for_identity(
                draft_id=draft_id,
                operation_id=operation_id,
                proposal_id=proposal_id,
                commit_id=request.commit_id,
                identity=identity,
                status=identity_status,
                detail=identity_detail,
            ),
            None,
            proposal,
        )
    assert resolution is not None

    refresh = refresh_publication_operation(root, draft_id, operation_id)
    pub_status, operation, pub_detail = _classify_publication_operation_authority(
        refresh, record=probe
    )
    if pub_status != "ok":
        return (
            None,
            _admission_outcome_for_publication(
                draft_id=draft_id,
                operation_id=operation_id,
                proposal_id=proposal_id,
                commit_id=request.commit_id,
                refresh=refresh,
                status=pub_status,
                detail=pub_detail,
            ),
            None,
            proposal,
        )
    assert operation is not None

    snapshot = operation.source_snapshot

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
        disposition = _contribution_order_disposition(
            contribution,
            list(proposal.accepted_assertion_ids),
            sealed_proposal=proposal.sealed_proposal,
        )
        if disposition == "legacy_seal_order":
            return None, CommitOutcome(
                _response(
                    draft_id,
                    operation_id,
                    proposal_id,
                    request.commit_id,
                    "publication_commit_proposal_incompatible",
                    message=_LEGACY_SEAL_ORDER_MESSAGE,
                )
            ), None, proposal
        return None, CommitOutcome(
            _response(
                draft_id,
                operation_id,
                proposal_id,
                request.commit_id,
                "publication_commit_integrity_failure",
                message=(
                    "reconstructed contribution does not match proposal"
                    if disposition == "set_mismatch"
                    else "proposal accepted_assertion_ids order is corrupt "
                    "(not reconstruction order and not historical seal order)"
                ),
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
) -> tuple[ThreatPublicationCommitV1, int, ThreatPublicationCommitResultLabel, str | None]:
    try:
        head, _rev, _store = kernel.open_current_world_graph(world_root, record.world_id)
    except Exception:
        return record, merge_calls, "publication_commit_graph_unavailable", None
    if head.head_revision_id != record.expected_parent_revision_id:
        updated = _with_updated(record, state="uncommitted")
        _save_commit(root, updated)
        return updated, merge_calls, "publication_commit_uncommitted", None

    identity = read_identity_resolution(
        root, record.draft_id, record.operation_id, record.resolution_id
    )
    identity_status, _resolution, identity_detail = _classify_identity_authority(
        identity, record=record, proposal=proposal
    )
    if identity_status == "unavailable":
        return record, merge_calls, "publication_commit_recovery_pending", identity_detail
    if identity_status == "integrity":
        return record, merge_calls, "publication_commit_integrity_failure", identity_detail
    if identity_status == "mismatch":
        updated = _with_updated(record, state="uncommitted")
        _save_commit(root, updated)
        return updated, merge_calls, "publication_commit_uncommitted", identity_detail

    refresh = refresh_publication_operation(root, record.draft_id, record.operation_id)
    pub_status, _operation, pub_detail = _classify_publication_operation_authority(
        refresh, record=record
    )
    if pub_status == "unavailable":
        return record, merge_calls, "publication_commit_recovery_pending", pub_detail
    if pub_status == "integrity":
        return record, merge_calls, "publication_commit_integrity_failure", pub_detail
    if pub_status == "mismatch":
        updated = _with_updated(record, state="uncommitted")
        _save_commit(root, updated)
        return updated, merge_calls, "publication_commit_uncommitted", pub_detail

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
    except OSError as exc:
        return (
            record,
            merge_calls,
            "publication_commit_recovery_pending",
            f"contribution reconstruction unavailable: {exc}",
        )
    except WorldGraphIntegrityError as exc:
        return (
            record,
            merge_calls,
            "publication_commit_integrity_failure",
            f"contribution reconstruction integrity failure: {exc}",
        )
    except Exception as exc:
        return (
            record,
            merge_calls,
            "publication_commit_integrity_failure",
            f"contribution reconstruction integrity failure: {exc}",
        )

    if (
        not _unmodified_contribution_matches_expected_ids(
            rebuilt, list(record.accepted_assertion_ids)
        )
        or rebuilt.contribution_id != record.expected_contribution_id
        or kernel.compute_contribution_source_payload_sha256(rebuilt)
        != record.expected_contribution_source_payload_sha256
    ):
        updated = _with_updated(record, state="uncommitted")
        _save_commit(root, updated)
        return updated, merge_calls, "publication_commit_uncommitted", None

    attempt2 = _with_updated(record, merge_attempt_count=2)
    try:
        _save_commit(root, attempt2)
    except ThreatPublicationCommitStorageError as exc:
        label: ThreatPublicationCommitResultLabel = (
            "publication_commit_integrity_failure"
            if getattr(exc, "kind", "unavailable") == "integrity"
            else "publication_commit_storage_unavailable"
        )
        return record, merge_calls, label, str(exc)
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
        updated, merge_calls, label, _allow_retry, message = _reconcile(
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
        return updated, merge_calls, label, message

    if _direct_publish_usable(result, attempt2):
        updated = _with_updated(
            attempt2,
            state="committed_unverified",
            committed_revision_id=result.revision_id,
            recovered_via_operation_lookup=False,
            verification_status="not_started",
        )
        persisted, save_label, save_message = _persist_committed_unverified_receipt(
            root, attempt2, updated
        )
        if save_label is not None:
            return persisted, merge_calls, save_label, save_message
        updated = persisted
        verified, label, message = _advance_committed_verification(
            root=root,
            world_root=world_root,
            record=updated,
            proposal=proposal,
            contribution=rebuilt,
            lookup_fn=lookup_fn,
        )
        return verified, merge_calls, label, message

    updated, merge_calls, label, _allow_retry, message = _reconcile(
        root=root,
        world_root=world_root,
        record=attempt2,
        proposal=proposal,
        contribution=rebuilt,
        lookup_fn=lookup_fn,
        merge_fn=merge_fn,
        published_false=(result.published is False),
        merge_calls=merge_calls,
        published_false_message=_merge_failure_message(result),
    )
    return updated, merge_calls, label, message


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
            return _outcome_storage(
                safe_draft,
                safe_op,
                safe_proposal,
                safe_commit,
                exc,
                admission_known=False,
            )

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

            # §8.1 — terminal / verified replay before dependency reads.
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

            try:
                proposal_ledger = load_threat_publication_proposal_ledger_unlocked(
                    root, safe_draft, safe_op
                )
            except ThreatPublicationProposalStorageError as exc:
                if record.state == "committed_unverified":
                    # Known committed receipt must not be hidden by dependency unavailability.
                    return CommitOutcome(
                        _response(
                            safe_draft,
                            safe_op,
                            safe_proposal,
                            safe_commit,
                            "publication_commit_committed_unverified",
                            commit=record,
                            retry_allowed=False,
                            message=f"verification dependency unavailable: {exc}",
                        )
                    )
                return _outcome_storage(
                    safe_draft,
                    safe_op,
                    safe_proposal,
                    safe_commit,
                    exc,
                    commit=record,
                )
            proposal = (
                find_threat_publication_proposal(proposal_ledger, record.proposal_id)
                if proposal_ledger is not None
                else None
            )
            if proposal is None:
                if record.state == "committed_unverified":
                    return CommitOutcome(
                        _response(
                            safe_draft,
                            safe_op,
                            safe_proposal,
                            safe_commit,
                            "publication_commit_committed_unverified",
                            commit=record,
                            retry_allowed=False,
                            message="verification dependency unavailable: proposal missing",
                        )
                    )
                return CommitOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_proposal,
                        safe_commit,
                        "publication_commit_integrity_failure",
                        commit=record,
                        message="proposal missing while commit record exists",
                    )
                )

            if record.state == "committing":
                authority_err = _record_matches_proposal_authority(
                    record,
                    proposal,
                    contribution=None,
                    selected_target_authority=(
                        None if record.decision == "create_new" else record.selected_target
                    ),
                )
                if authority_err is not None:
                    return CommitOutcome(
                        _response(
                            safe_draft,
                            safe_op,
                            safe_proposal,
                            safe_commit,
                            "publication_commit_integrity_failure",
                            commit=record,
                            message=f"commit record authority mismatch: {authority_err}",
                        )
                    )

                contribution: GraphContribution | None = None
                order_disposition: Literal[
                    "exact", "legacy_seal_order", "corrupt_permutation", "set_mismatch"
                ] | None = None
                reconstruction_blocker: str | None = None
                reconstruction_integrity = False

                def _order_after_reconstruction_failure() -> Literal[
                    "exact", "legacy_seal_order"
                ]:
                    seal_ids = _historical_seal_order_ids(proposal.sealed_proposal)
                    record_ids = list(record.accepted_assertion_ids)
                    proposal_ids = list(proposal.accepted_assertion_ids)
                    if (
                        seal_ids is not None
                        and record_ids == seal_ids
                        and record_ids != proposal_ids
                    ):
                        return "legacy_seal_order"
                    return "exact"

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
                    order_disposition = _contribution_order_disposition(
                        contribution,
                        list(record.accepted_assertion_ids),
                        sealed_proposal=proposal.sealed_proposal,
                    )
                except OSError as exc:
                    reconstruction_blocker = (
                        f"contribution reconstruction unavailable: {exc}"
                    )
                    contribution = None
                    order_disposition = _order_after_reconstruction_failure()
                except WorldGraphIntegrityError as exc:
                    reconstruction_blocker = (
                        f"contribution reconstruction integrity failure: {exc}"
                    )
                    reconstruction_integrity = True
                    contribution = None
                    order_disposition = _order_after_reconstruction_failure()
                except Exception as exc:  # noqa: BLE001
                    reconstruction_blocker = (
                        f"contribution reconstruction failed: {exc}"
                    )
                    reconstruction_integrity = True
                    contribution = None
                    order_disposition = _order_after_reconstruction_failure()

                assert order_disposition is not None
                if (
                    contribution is not None
                    and order_disposition in {"corrupt_permutation", "set_mismatch"}
                ):
                    return CommitOutcome(
                        _response(
                            safe_draft,
                            safe_op,
                            safe_proposal,
                            safe_commit,
                            "publication_commit_integrity_failure",
                            commit=record,
                            message=(
                                "commit record accepted_assertion_ids order is corrupt "
                                "(not reconstruction order and not historical seal order)"
                                if order_disposition == "corrupt_permutation"
                                else "commit record authority mismatch: "
                                "accepted_assertion_ids_mismatch"
                            ),
                        )
                    )

                if contribution is not None:
                    trust_err = _record_matches_c2a_trust(
                        record,
                        proposal,
                        contribution,
                        order_disposition=order_disposition,
                    )
                    if trust_err is not None:
                        return CommitOutcome(
                            _response(
                                safe_draft,
                                safe_op,
                                safe_proposal,
                                safe_commit,
                                "publication_commit_integrity_failure",
                                commit=record,
                                message=f"commit record authority mismatch: {trust_err}",
                            )
                        )

                # c2a runs once the durable record/proposal establish the lookup
                # key, regardless of reconstruction success. Reconstruction
                # integrity blocks retry/verification but must not hide a
                # core-proven committed revision.
                reconcile_contribution = (
                    contribution if order_disposition == "exact" else None
                )
                updated, merge_calls, label, allow_zero_match_retry, reconcile_message = (
                    _reconcile(
                        root=root,
                        world_root=configured_world,
                        record=record,
                        proposal=proposal,
                        contribution=reconcile_contribution,
                        lookup_fn=lookup,
                        merge_fn=merge,
                        published_false=False,
                        merge_calls=merge_calls,
                    )
                )

                if updated.state != "committing":
                    message = reconcile_message
                    if (
                        reconstruction_blocker is not None
                        and updated.state
                        in {"committed_unverified", "committed_verified"}
                    ):
                        message = (
                            f"{reconstruction_blocker}; committed revision recovered "
                            "via c2a; reconstruction integrity blocks verification"
                        )
                    return CommitOutcome(
                        _response(
                            safe_draft,
                            safe_op,
                            safe_proposal,
                            safe_commit,
                            label,
                            commit=updated,
                            retry_allowed=False,
                            message=message,
                        ),
                        merge_calls=merge_calls,
                    )

                # Unique c2a match proved a committed revision but receipt
                # persistence failed: durable record remains committing-shaped,
                # yet merge retry must never be advertised.
                if label == "publication_commit_storage_unavailable":
                    return CommitOutcome(
                        _response(
                            safe_draft,
                            safe_op,
                            safe_proposal,
                            safe_commit,
                            label,
                            commit=updated,
                            retry_allowed=False,
                            message=reconcile_message,
                        ),
                        merge_calls=merge_calls,
                    )

                if reconstruction_integrity:
                    # Zero/unavailable c2a after reconstruction integrity: keep
                    # committing, block retry, surface integrity. Do not enter
                    # governed merge retry without a successful reconstruction.
                    return CommitOutcome(
                        _response(
                            safe_draft,
                            safe_op,
                            safe_proposal,
                            safe_commit,
                            "publication_commit_integrity_failure",
                            commit=updated,
                            retry_allowed=False,
                            message=reconstruction_blocker,
                        ),
                        merge_calls=merge_calls,
                    )

                if order_disposition == "legacy_seal_order":
                    # Only terminalize after an authoritative completed zero-match
                    # lookup. Transient/integrity/receipt-save failures must return
                    # the untouched record with their original classification.
                    if not allow_zero_match_retry:
                        return CommitOutcome(
                            _response(
                                safe_draft,
                                safe_op,
                                safe_proposal,
                                safe_commit,
                                label,
                                commit=updated,
                                retry_allowed=_retry_allowed(updated),
                                message=reconcile_message,
                            ),
                            merge_calls=merge_calls,
                        )
                    terminal = _with_updated(updated, state="uncommitted")
                    _save_commit(root, terminal)
                    return CommitOutcome(
                        _response(
                            safe_draft,
                            safe_op,
                            safe_proposal,
                            safe_commit,
                            "publication_commit_uncommitted",
                            commit=terminal,
                            message=_LEGACY_COMMIT_CLAIM_NO_REVISION_MESSAGE,
                        ),
                        merge_calls=merge_calls,
                    )

                if (
                    allow_zero_match_retry
                    and updated.merge_attempt_count == 1
                ):
                    # Zero c2a match: require identity/operation authority before retry.
                    identity = read_identity_resolution(
                        root, safe_draft, safe_op, updated.resolution_id
                    )
                    identity_status, _resolution, identity_detail = (
                        _classify_identity_authority(
                            identity, record=updated, proposal=proposal
                        )
                    )
                    if identity_status == "unavailable":
                        return CommitOutcome(
                            _response(
                                safe_draft,
                                safe_op,
                                safe_proposal,
                                safe_commit,
                                "publication_commit_recovery_pending",
                                commit=updated,
                                retry_allowed=_retry_allowed(updated),
                                message=identity_detail,
                            ),
                            merge_calls=merge_calls,
                        )
                    if identity_status == "integrity":
                        # Corrupt identity storage: integrity without pretending
                        # the outcome is uncommitted.
                        return CommitOutcome(
                            _response(
                                safe_draft,
                                safe_op,
                                safe_proposal,
                                safe_commit,
                                "publication_commit_integrity_failure",
                                commit=updated,
                                message=identity_detail,
                            ),
                            merge_calls=merge_calls,
                        )
                    if identity_status == "mismatch":
                        terminal = _with_updated(updated, state="uncommitted")
                        _save_commit(root, terminal)
                        return CommitOutcome(
                            _response(
                                safe_draft,
                                safe_op,
                                safe_proposal,
                                safe_commit,
                                "publication_commit_uncommitted",
                                commit=terminal,
                                message=(
                                    f"{identity_detail}; a new publication "
                                    "operation is required"
                                ),
                            ),
                            merge_calls=merge_calls,
                        )
                    if contribution is None:
                        return CommitOutcome(
                            _response(
                                safe_draft,
                                safe_op,
                                safe_proposal,
                                safe_commit,
                                label,
                                commit=updated,
                                retry_allowed=_retry_allowed(updated),
                                message=reconcile_message,
                            ),
                            merge_calls=merge_calls,
                        )
                    updated, merge_calls, label, retry_message = _maybe_retry(
                        root=root,
                        world_root=configured_world,
                        record=updated,
                        proposal=proposal,
                        contribution=contribution,
                        merge_fn=merge,
                        lookup_fn=lookup,
                        merge_calls=merge_calls,
                    )
                else:
                    retry_message = None
                return CommitOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_proposal,
                        safe_commit,
                        label,
                        commit=updated,
                        retry_allowed=_retry_allowed(updated),
                        message=retry_message,
                    ),
                    merge_calls=merge_calls,
                )

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
            except Exception as exc:  # noqa: BLE001
                return CommitOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_proposal,
                        safe_commit,
                        "publication_commit_committed_unverified",
                        commit=record,
                        retry_allowed=False,
                        message=f"verification dependency unavailable: {exc}",
                    )
                )

            order_disposition = _contribution_order_disposition(
                contribution,
                list(record.accepted_assertion_ids),
                sealed_proposal=proposal.sealed_proposal,
            )
            if order_disposition in {"corrupt_permutation", "set_mismatch"}:
                return CommitOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_proposal,
                        safe_commit,
                        "publication_commit_integrity_failure",
                        commit=record,
                        message=(
                            "commit record accepted_assertion_ids order is corrupt "
                            "(not reconstruction order and not historical seal order)"
                            if order_disposition == "corrupt_permutation"
                            else "commit record authority mismatch: "
                            "accepted_assertion_ids_mismatch"
                        ),
                    )
                )

            # committed_unverified — preserve known receipt across dependency gaps.
            if order_disposition == "legacy_seal_order":
                return CommitOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_proposal,
                        safe_commit,
                        "publication_commit_committed_unverified",
                        commit=record,
                        retry_allowed=False,
                        message=(
                            "commit claim uses pre-reconstruction seal-order "
                            "assertion IDs; verification deferred"
                        ),
                    )
                )

            selected_target_authority = None
            if record.decision == "connect_existing":
                identity = read_identity_resolution(
                    root, safe_draft, safe_op, record.resolution_id
                )
                identity_status, resolution_authority, identity_detail = (
                    _classify_identity_authority(
                        identity,
                        record=record,
                        proposal=proposal,
                        require_active=False,
                    )
                )
                if identity_status == "unavailable":
                    return CommitOutcome(
                        _response(
                            safe_draft,
                            safe_op,
                            safe_proposal,
                            safe_commit,
                            "publication_commit_committed_unverified",
                            commit=record,
                            retry_allowed=False,
                            message=identity_detail,
                        )
                    )
                if identity_status in {"integrity", "mismatch"}:
                    return CommitOutcome(
                        _response(
                            safe_draft,
                            safe_op,
                            safe_proposal,
                            safe_commit,
                            "publication_commit_integrity_failure",
                            commit=record,
                            message=identity_detail,
                        )
                    )
                if resolution_authority is not None:
                    selected_target_authority = resolution_authority.selected_target

            matched_contribution, authority_err = _record_contribution_matches_authority(
                record,
                proposal,
                contribution,
                selected_target_authority=selected_target_authority,
            )
            if authority_err is not None or matched_contribution is None:
                return CommitOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_proposal,
                        safe_commit,
                        "publication_commit_integrity_failure",
                        commit=record,
                        message=f"commit record authority mismatch: {authority_err}",
                    )
                )
            contribution = matched_contribution

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
            except ThreatPublicationCommitStorageError:
                return CommitOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_proposal,
                        safe_commit,
                        "publication_commit_committed_unverified",
                        commit=record,
                        retry_allowed=False,
                        message="verification could not persist",
                    )
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
            persisted, save_label, save_message = _persist_committed_unverified_receipt(
                root, record, updated
            )
            if save_label is not None:
                return CommitOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_proposal,
                        safe_commit,
                        save_label,
                        commit=persisted,
                        retry_allowed=False,
                        message=save_message,
                    ),
                    created=True,
                    merge_calls=merge_calls,
                )
            updated = persisted
            verified, label, verify_message = _advance_committed_verification(
                root=root,
                world_root=configured_world,
                record=updated,
                proposal=proposal,
                contribution=contribution,
                lookup_fn=lookup,
            )
            return CommitOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    safe_proposal,
                    safe_commit,
                    label,
                    commit=verified,
                    retry_allowed=_retry_allowed(verified),
                    message=verify_message,
                ),
                created=True,
                merge_calls=merge_calls,
            )

        updated, merge_calls, label, allow_zero_match_retry, reconcile_message = (
            _reconcile(
                root=root,
                world_root=configured_world,
                record=record,
                proposal=proposal,
                contribution=contribution,
                lookup_fn=lookup,
                merge_fn=merge,
                published_false=published_false,
                merge_calls=merge_calls,
                published_false_message=_merge_failure_message(result),
            )
        )
        outcome_message = reconcile_message
        if (
            allow_zero_match_retry
            and updated.state == "committing"
            and updated.merge_attempt_count == 1
        ):
            updated, merge_calls, label, outcome_message = _maybe_retry(
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
                message=outcome_message,
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
            return _outcome_storage(
                safe_draft,
                safe_op,
                None,
                safe_commit,
                exc,
                admission_known=False,
            )
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
