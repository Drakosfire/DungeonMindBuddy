"""SBW09c1: Threat publication-proposal orchestration.

Storage:
    out/threat_publication_proposals/<draft_id>/<operation_id>/ledger.json
    out/threat_publication_proposals/<draft_id>/<operation_id>/.proposal.lock

Lock order:
    proposal ledger lock -> SBW09b identity read -> SBW09a publication refresh/read
    -> exact expected-parent World Graph read

No graph, ThreatDraft, accepted-mechanics, or predecessor mutation occurs here.
"""
from __future__ import annotations

import fcntl
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator, Literal

import graph_memory.kernel as kernel

from apps.live_control_server.config import world_graph_root
from apps.live_control_server.models.statblock_mechanics_acceptance import AcceptedMechanicsRefV1
from apps.live_control_server.models.threat_draft import require_draft_id
from apps.live_control_server.models.threat_publication import (
    ThreatPublicationOperationV1,
    ThreatPublicationResultLabel,
    validate_publication_operation_id,
)
from apps.live_control_server.models.threat_publication_identity import (
    RESOLUTION_SCHEMA,
    ThreatPublicationIdentityResolutionV1,
    ThreatPublicationIdentityResultLabel,
    source_name_from_snapshot,
    validate_resolution_id,
)
from apps.live_control_server.models.threat_publication_proposal import (
    LEDGER_SCHEMA,
    MAX_PROPOSALS_PER_OPERATION,
    PrepareThreatPublicationProposalRequestV1,
    ProposalDecision,
    ThreatPublicationEffectSummaryV1,
    ThreatPublicationProposalLedgerV1,
    ThreatPublicationProposalResponseV1,
    ThreatPublicationProposalResultLabel,
    ThreatPublicationProposalV1,
    canonical_string_list,
    deterministic_evidence_id,
    operation_source_artifact_id,
    operation_verified_source_uri,
    prepare_request_digest,
    resolution_source_artifact_id,
    validate_proposal_id,
)
from apps.live_control_server.services.threat_publication_commit_store import (
    ThreatPublicationCommitStorageError,
    load_threat_publication_commit_ledger_unlocked,
    threat_publication_commit_ledger_exists,
)
from apps.live_control_server.models.threat_publication_commit import (
    ThreatPublicationCommitLedgerV1,
)
from apps.live_control_server.services.threat_publication_identity import (
    IdentityResolutionOutcome,
    read_identity_resolution,
)
from apps.live_control_server.services.threat_publication_operations import (
    PublicationOperationOutcome,
    refresh_publication_operation,
)
from graph_memory.extract_promote_proposal import seal_promote_proposal, verify_promote_proposal
from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package
from graph_memory.kernel.contribution_models import GraphContributionAssertion
from graph_memory.union_supergraph.model import UnionSupergraphEdge, UnionSupergraphNode
from graph_memory.union_supergraph.statblock_binding import (
    CONTRACT,
    CONTRACT_VERSION,
    PROVIDER,
    ExternalResourceV1,
    ThreatStatblockBindingV1,
    compute_binding_id,
    edge_id_from_binding_id,
    external_statblock_node_id,
    parse_threat_statblock_binding_assertion,
)
from src.live_play.live_store import load_json, write_json

DEFAULT_PROPOSAL_REL = "out/threat_publication_proposals"
LEDGER_NAME = "ledger.json"
LOCK_NAME = ".proposal.lock"
EXTRACTION_PROFILE = "dmb_threat_publication_v1"
IDENTITY_DECISION_SOURCE_KIND = "identity_decision"


@dataclass(frozen=True)
class ProposalOutcome:
    response: ThreatPublicationProposalResponseV1
    created: bool = False


class ThreatPublicationProposalStorageError(Exception):
    def __init__(self, message: str, *, kind: Literal["unavailable", "integrity"]) -> None:
        super().__init__(message)
        self.kind = kind


_RESOLUTION_LABEL_MAP: dict[
    ThreatPublicationIdentityResultLabel, ThreatPublicationProposalResultLabel
] = {
    "publication_identity_refused": "publication_proposal_identity_refused",
    "publication_identity_not_found": "publication_proposal_resolution_not_active",
    "publication_identity_superseded": "publication_proposal_resolution_not_active",
    "publication_identity_integrity_failure": "publication_proposal_integrity_failure",
    "publication_identity_storage_unavailable": "publication_proposal_storage_unavailable",
    "publication_identity_graph_unavailable": "publication_proposal_graph_unavailable",
}

_PUBLICATION_LABEL_MAP: dict[
    ThreatPublicationResultLabel, ThreatPublicationProposalResultLabel
] = {
    "publication_not_found": "publication_proposal_operation_not_ready",
    "publication_stale": "publication_proposal_operation_not_ready",
    "publication_cancelled": "publication_proposal_operation_not_ready",
    "publication_superseded": "publication_proposal_operation_not_ready",
    "publication_parent_mismatch": "publication_proposal_parent_mismatch",
    "publication_source_mismatch": "publication_proposal_predecessor_mismatch",
    "publication_integrity_failure": "publication_proposal_integrity_failure",
    "publication_storage_unavailable": "publication_proposal_storage_unavailable",
    "publication_graph_unavailable": "publication_proposal_graph_unavailable",
    "publication_draft_unavailable": "publication_proposal_storage_unavailable",
}


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def proposal_root(repo_root: Path) -> Path:
    return repo_root / DEFAULT_PROPOSAL_REL


def _storage_unavailable() -> ThreatPublicationProposalStorageError:
    return ThreatPublicationProposalStorageError(
        "publication proposal ledger storage unavailable", kind="unavailable"
    )


def _integrity_failure(message: str) -> ThreatPublicationProposalStorageError:
    return ThreatPublicationProposalStorageError(message, kind="integrity")


def _operation_directory(root: Path, draft_id: str, operation_id: str) -> Path:
    safe_draft = require_draft_id(draft_id)
    safe_op = validate_publication_operation_id(operation_id)
    store_root = proposal_root(root).resolve()
    directory = (store_root / safe_draft / safe_op).resolve()
    expected_parent = (store_root / safe_draft).resolve()
    if directory.parent != expected_parent or not str(directory).startswith(str(store_root)):
        raise _integrity_failure("proposal path escape")
    return directory


def _ledger_path(root: Path, draft_id: str, operation_id: str) -> Path:
    return _operation_directory(root, draft_id, operation_id) / LEDGER_NAME


@contextmanager
def _proposal_lock(root: Path, draft_id: str, operation_id: str) -> Iterator[None]:
    directory = _operation_directory(root, draft_id, operation_id)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        lock_path = directory / LOCK_NAME
        lock_file = open(lock_path, "a+", encoding="utf-8")
    except OSError:
        raise _storage_unavailable() from None
    try:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        except OSError:
            raise _storage_unavailable() from None
        try:
            yield
        finally:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
    finally:
        lock_file.close()


@contextmanager
def threat_publication_lifecycle_lock(
    root: Path, draft_id: str, operation_id: str
) -> Iterator[None]:
    """Shared proposal/commit lifecycle lock (existing `.proposal.lock` path)."""
    with _proposal_lock(root, draft_id, operation_id):
        yield


def load_threat_publication_proposal_ledger_unlocked(
    root: Path, draft_id: str, operation_id: str
) -> ThreatPublicationProposalLedgerV1 | None:
    return _load_ledger_unlocked(root, draft_id, operation_id)


def find_threat_publication_proposal(
    ledger: ThreatPublicationProposalLedgerV1, proposal_id: str
) -> ThreatPublicationProposalV1 | None:
    return _find_proposal(ledger, proposal_id)


def _empty_ledger(draft_id: str, operation_id: str) -> ThreatPublicationProposalLedgerV1:
    return ThreatPublicationProposalLedgerV1(
        draft_id=draft_id,
        operation_id=operation_id,
        active_proposal_id=None,
        proposals=[],
    )


def _load_ledger_unlocked(
    root: Path, draft_id: str, operation_id: str
) -> ThreatPublicationProposalLedgerV1 | None:
    path = _ledger_path(root, draft_id, operation_id)
    if not path.is_file():
        return None
    try:
        payload = load_json(path)
    except OSError:
        raise _storage_unavailable() from None
    except Exception:
        raise _integrity_failure("corrupt publication proposal ledger") from None
    if not isinstance(payload, dict):
        raise _integrity_failure("corrupt publication proposal ledger")
    if payload.get("schema") != LEDGER_SCHEMA:
        raise _integrity_failure("corrupt publication proposal ledger")
    try:
        ledger = ThreatPublicationProposalLedgerV1.model_validate(payload)
    except Exception:
        raise _integrity_failure("corrupt publication proposal ledger") from None
    if ledger.draft_id != require_draft_id(draft_id):
        raise _integrity_failure("proposal ledger identity mismatch")
    if ledger.operation_id != validate_publication_operation_id(operation_id):
        raise _integrity_failure("proposal ledger identity mismatch")
    return ledger


def _save_ledger_unlocked(root: Path, ledger: ThreatPublicationProposalLedgerV1) -> None:
    path = _ledger_path(root, ledger.draft_id, ledger.operation_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, ledger.model_dump(mode="json", by_alias=True))
    except OSError:
        raise _storage_unavailable() from None


def _response(
    draft_id: str,
    operation_id: str,
    resolution_id: str | None,
    label: ThreatPublicationProposalResultLabel,
    *,
    proposal: ThreatPublicationProposalV1 | None = None,
    message: str | None = None,
) -> ThreatPublicationProposalResponseV1:
    return ThreatPublicationProposalResponseV1(
        draft_id=draft_id,
        operation_id=operation_id,
        resolution_id=resolution_id,
        result_label=label,
        proposal=proposal,
        message=message,
    )


def _outcome_from_storage_error(
    draft_id: str,
    operation_id: str,
    resolution_id: str | None,
    exc: ThreatPublicationProposalStorageError,
) -> ProposalOutcome:
    if exc.kind == "integrity":
        return ProposalOutcome(
            _response(
                draft_id,
                operation_id,
                resolution_id,
                "publication_proposal_integrity_failure",
                message=str(exc),
            )
        )
    return ProposalOutcome(
        _response(
            draft_id,
            operation_id,
            resolution_id,
            "publication_proposal_storage_unavailable",
            message=str(exc),
        )
    )


def _find_proposal(
    ledger: ThreatPublicationProposalLedgerV1, proposal_id: str
) -> ThreatPublicationProposalV1 | None:
    for proposal in ledger.proposals:
        if proposal.proposal_id == proposal_id:
            return proposal
    return None


def _replace_proposal(
    ledger: ThreatPublicationProposalLedgerV1, updated: ThreatPublicationProposalV1
) -> list[ThreatPublicationProposalV1]:
    return [
        updated if item.proposal_id == updated.proposal_id else item
        for item in ledger.proposals
    ]


def _proposal_label(proposal: ThreatPublicationProposalV1) -> ThreatPublicationProposalResultLabel:
    if proposal.state == "superseded":
        return "publication_proposal_superseded"
    return "publication_proposal_ready"


def _identity_label(label: ThreatPublicationIdentityResultLabel) -> ThreatPublicationProposalResultLabel:
    mapped = _RESOLUTION_LABEL_MAP.get(label)
    if mapped is not None:
        return mapped
    if label == "publication_identity_operation_not_ready":
        return "publication_proposal_operation_not_ready"
    return "publication_proposal_resolution_not_active"


def _publication_label(label: ThreatPublicationResultLabel) -> ThreatPublicationProposalResultLabel:
    mapped = _PUBLICATION_LABEL_MAP.get(label)
    if mapped is not None:
        return mapped
    return "publication_proposal_operation_not_ready"


def _outcome_from_identity_failure(
    draft_id: str,
    operation_id: str,
    resolution_id: str,
    predecessor: IdentityResolutionOutcome,
) -> ProposalOutcome:
    label = _identity_label(predecessor.response.result_label)
    return ProposalOutcome(
        _response(
            draft_id,
            operation_id,
            resolution_id,
            label,
            message=predecessor.response.message or predecessor.response.result_label,
        )
    )


def _outcome_from_publication_failure(
    draft_id: str,
    operation_id: str,
    resolution_id: str,
    predecessor: PublicationOperationOutcome,
) -> ProposalOutcome:
    label = _publication_label(predecessor.response.result_label)
    return ProposalOutcome(
        _response(
            draft_id,
            operation_id,
            resolution_id,
            label,
            message=predecessor.response.message or predecessor.response.result_label,
        )
    )


def _load_exact_parent_store(
    operation: ThreatPublicationOperationV1,
    *,
    world_root: Path | None,
):
    graph_root = (world_root if world_root is not None else world_graph_root()).resolve()
    try:
        return kernel.load_world_graph_revision_with_integrity(
            graph_root,
            operation.source_snapshot.world_id,
            operation.expected_parent_revision_id,
        )
    except kernel.WorldGraphProjectionError as exc:
        if exc.code == "projection_integrity_error":
            raise _integrity_failure(
                "exact expected-parent World Graph revision failed integrity validation"
            ) from exc
        raise _storage_unavailable() from None


def _resource_payload(statblock_id: str) -> dict[str, object]:
    resource = ExternalResourceV1.model_validate(
        {
            "schema": "dmb_external_resource_v1",
            "provider": PROVIDER,
            "resource_type": "statblock",
            "resource_id": statblock_id,
            "contract": CONTRACT,
            "contract_version": CONTRACT_VERSION,
        }
    )
    return {
        "kind": "external_resource",
        "role": "statblock",
        "external_resource": resource.model_dump(mode="json", by_alias=True),
    }


def _binding_payload(
    *,
    threat_node_id: str,
    accepted_ref: AcceptedMechanicsRefV1,
) -> tuple[dict[str, object], str, str]:
    binding = ThreatStatblockBindingV1.model_validate(
        {
            "schema": "dmb_threat_statblock_binding_v1",
            "binding_id": compute_binding_id(
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
            ),
            "provider": accepted_ref.provider,
            "statblock_id": accepted_ref.statblock_id,
            "revision_id": accepted_ref.revision_id,
            "contract": accepted_ref.contract,
            "contract_version": accepted_ref.contract_version,
            "definition_digest": accepted_ref.definition_digest,
            "role": "primary",
            "phase_key": None,
            "variant_label": None,
        }
    )
    edge_id = edge_id_from_binding_id(binding.binding_id)
    value = {
        "edge_id": edge_id,
        "direction": "outbound",
        "threat_statblock_binding": binding.model_dump(mode="json", by_alias=True),
    }
    return value, edge_id, binding.binding_id


def _assertion_common(
    *,
    operation: ThreatPublicationOperationV1,
    resolution: ThreatPublicationIdentityResolutionV1,
    source_domain: str,
    identity_outcome: str,
) -> dict[str, object]:
    snapshot = operation.source_snapshot
    return {
        "acceptance_state": "accepted",
        "evidence_ref_ids": [
            deterministic_evidence_id(
                operation.operation_id,
                resolution.resolution_id,
                source_domain,
                "primary",
            )
        ],
        "source_artifact_id": operation_source_artifact_id(operation.operation_id),
        "source_revision_id": operation.source_digest,
        "campaign_scope": snapshot.campaign_id,
        "visibility": "gm",
        "epistemic_kind": "fact",
        "identity_resolution_outcome": identity_outcome,
    }


def _attribute_assertion(
    *,
    operation: ThreatPublicationOperationV1,
    resolution: ThreatPublicationIdentityResolutionV1,
    subject_node_id: str,
    predicate: str,
    text: str,
    identity_outcome: str,
) -> GraphContributionAssertion:
    common = _assertion_common(
        operation=operation,
        resolution=resolution,
        source_domain="worldbuilding",
        identity_outcome=identity_outcome,
    )
    return kernel.build_assertion(
        assertion_kind="attribute",
        subject_node_id=subject_node_id,
        predicate=predicate,
        label=text,
        value={"text": text, "source_domains": ["worldbuilding"]},
        **common,
    )


def _build_create_new_assertions(
    operation: ThreatPublicationOperationV1,
    resolution: ThreatPublicationIdentityResolutionV1,
) -> list[GraphContributionAssertion]:
    snapshot = operation.source_snapshot
    assert resolution.created_node_id is not None
    threat_node_id = resolution.created_node_id
    source_name = source_name_from_snapshot(snapshot)
    roles = canonical_string_list(snapshot.intended_roles)
    tags = canonical_string_list(snapshot.tags)
    role = roles[0] if roles else snapshot.threat_kind.strip() or "threat"
    identity_outcome = "created_new"

    assertions: list[GraphContributionAssertion] = []
    common = _assertion_common(
        operation=operation,
        resolution=resolution,
        source_domain="worldbuilding",
        identity_outcome=identity_outcome,
    )
    assertions.append(
        kernel.build_assertion(
            assertion_kind="node",
            subject_node_id=threat_node_id,
            label=source_name,
            value={
                "kind": "threat",
                "role": role,
                "aliases": [source_name],
                "source_domains": ["worldbuilding"],
            },
            **common,
        )
    )

    description = snapshot.description.strip()
    if description:
        assertions.append(
            _attribute_assertion(
                operation=operation,
                resolution=resolution,
                subject_node_id=threat_node_id,
                predicate="description",
                text=description,
                identity_outcome=identity_outcome,
            )
        )
    threat_kind = snapshot.threat_kind.strip()
    if threat_kind:
        assertions.append(
            _attribute_assertion(
                operation=operation,
                resolution=resolution,
                subject_node_id=threat_node_id,
                predicate="threat_kind",
                text=threat_kind,
                identity_outcome=identity_outcome,
            )
        )
    for item in roles:
        assertions.append(
            _attribute_assertion(
                operation=operation,
                resolution=resolution,
                subject_node_id=threat_node_id,
                predicate="intended_role",
                text=item,
                identity_outcome=identity_outcome,
            )
        )
    for item in tags:
        assertions.append(
            _attribute_assertion(
                operation=operation,
                resolution=resolution,
                subject_node_id=threat_node_id,
                predicate="tag",
                text=item,
                identity_outcome=identity_outcome,
            )
        )

    accepted_ref = snapshot.accepted_mechanics_ref
    resource_node_id = external_statblock_node_id(accepted_ref.statblock_id)
    assertions.append(
        kernel.build_assertion(
            assertion_kind="node",
            acceptance_state="accepted",
            subject_node_id=resource_node_id,
            label=f"External statblock {accepted_ref.statblock_id}",
            value=_resource_payload(accepted_ref.statblock_id),
            source_artifact_id=resolution_source_artifact_id(resolution.resolution_id),
            evidence_ref_ids=[
                deterministic_evidence_id(
                    operation.operation_id,
                    resolution.resolution_id,
                    "statblock",
                    "resource",
                )
            ],
            source_revision_id=operation.source_digest,
            campaign_scope=snapshot.campaign_id,
            visibility="gm",
            epistemic_kind="fact",
            identity_resolution_outcome=identity_outcome,
        )
    )

    binding_value, _edge_id, _binding_id = _binding_payload(
        threat_node_id=threat_node_id,
        accepted_ref=accepted_ref,
    )
    assertions.append(
        kernel.build_assertion(
            assertion_kind="edge",
            acceptance_state="accepted",
            subject_node_id=threat_node_id,
            target_node_id=resource_node_id,
            predicate="uses_statblock",
            label="uses_statblock",
            value=binding_value,
            source_artifact_id=resolution_source_artifact_id(resolution.resolution_id),
            evidence_ref_ids=[
                deterministic_evidence_id(
                    operation.operation_id,
                    resolution.resolution_id,
                    "statblock",
                    "binding",
                )
            ],
            source_revision_id=operation.source_digest,
            campaign_scope=snapshot.campaign_id,
            visibility="gm",
            epistemic_kind="fact",
            identity_resolution_outcome=identity_outcome,
        )
    )
    return assertions


def _build_connect_existing_assertions(
    operation: ThreatPublicationOperationV1,
    resolution: ThreatPublicationIdentityResolutionV1,
) -> list[GraphContributionAssertion]:
    assert resolution.selected_target is not None
    threat_node_id = resolution.selected_target.node_id
    identity_outcome = "matched_existing"
    snapshot = operation.source_snapshot
    accepted_ref = snapshot.accepted_mechanics_ref
    resource_node_id = external_statblock_node_id(accepted_ref.statblock_id)

    assertions: list[GraphContributionAssertion] = []
    assertions.append(
        kernel.build_assertion(
            assertion_kind="node",
            acceptance_state="accepted",
            subject_node_id=resource_node_id,
            label=f"External statblock {accepted_ref.statblock_id}",
            value=_resource_payload(accepted_ref.statblock_id),
            evidence_ref_ids=[
                deterministic_evidence_id(
                    operation.operation_id,
                    resolution.resolution_id,
                    "statblock",
                    "resource",
                )
            ],
            source_artifact_id=resolution_source_artifact_id(resolution.resolution_id),
            source_revision_id=operation.source_digest,
            campaign_scope=snapshot.campaign_id,
            visibility="gm",
            epistemic_kind="fact",
            identity_resolution_outcome=identity_outcome,
        )
    )

    binding_value, _edge_id, _binding_id = _binding_payload(
        threat_node_id=threat_node_id,
        accepted_ref=accepted_ref,
    )
    assertions.append(
        kernel.build_assertion(
            assertion_kind="edge",
            acceptance_state="accepted",
            subject_node_id=threat_node_id,
            target_node_id=resource_node_id,
            predicate="uses_statblock",
            label="uses_statblock",
            value=binding_value,
            evidence_ref_ids=[
                deterministic_evidence_id(
                    operation.operation_id,
                    resolution.resolution_id,
                    "statblock",
                    "binding",
                )
            ],
            source_artifact_id=resolution_source_artifact_id(resolution.resolution_id),
            source_revision_id=operation.source_digest,
            campaign_scope=snapshot.campaign_id,
            visibility="gm",
            epistemic_kind="fact",
            identity_resolution_outcome=identity_outcome,
        )
    )
    return assertions


def _identity_snapshot_for_decision(decision: ProposalDecision) -> str:
    return "created_new" if decision == "create_new" else "matched_existing"


def _build_sealed_package(
    *,
    operation: ThreatPublicationOperationV1,
    resolution: ThreatPublicationIdentityResolutionV1,
    proposal_id: str,
    actor: str,
    accepted_assertions: list[GraphContributionAssertion],
    decision: ProposalDecision,
    threat_node_id: str,
) -> dict[str, object]:
    snapshot = operation.source_snapshot
    identity_key = f"publication:{resolution.resolution_id}"
    identity_outcome = _identity_snapshot_for_decision(decision)
    verified_uri = operation_verified_source_uri(
        world_id=snapshot.world_id,
        campaign_id=snapshot.campaign_id,
        draft_id=snapshot.draft_id,
        operation_id=operation.operation_id,
    )
    contribution_meta = {
        "source_kind": IDENTITY_DECISION_SOURCE_KIND,
        "source_artifact_id": operation_source_artifact_id(operation.operation_id),
        "source_revision_id": operation.source_digest,
        "extraction_profile": EXTRACTION_PROFILE,
        "campaign_scope": snapshot.campaign_id,
        "authored_by": resolution.actor,
    }
    package = seal_promote_proposal(
        world_id=snapshot.world_id,
        parent_revision_id=operation.expected_parent_revision_id,
        source_revision_id=operation.source_digest,
        source_artifact_id=operation_source_artifact_id(operation.operation_id),
        verified_source_uri=verified_uri,
        candidate_preview_id=resolution.resolution_id,
        candidate_schema=RESOLUTION_SCHEMA,
        candidate_version="1",
        contribution_meta=contribution_meta,
        accepted_proposals=accepted_assertions,
        rejected_assertions=[],
        unresolved_mentions=[],
        node_id_map={identity_key: threat_node_id},
        identity_outcome_snapshot={identity_key: identity_outcome},
        prepared_by=actor,
        proposal_id=proposal_id,
    )
    verify_promote_proposal(
        package,
        confirming_principal=actor,
        expected_parent_revision_id=operation.expected_parent_revision_id,
    )
    return package


def _expected_contribution_id(
    *,
    package: dict[str, object],
    operation: ThreatPublicationOperationV1,
    actor: str,
    world_root: Path,
) -> str:
    _verified, contribution = resolve_merged_contribution_from_package(
        review_package=package,
        confirming_principal=actor,
        world_id_hint=operation.source_snapshot.world_id,
        root=world_root,
        expected_parent_revision_id=operation.expected_parent_revision_id,
        assertion_ids=None,
        verify_source=False,
    )
    return contribution.contribution_id


def _node_matches_candidate(
    node: UnionSupergraphNode, candidate: ThreatPublicationIdentityResolutionV1
) -> bool:
    assert candidate.selected_target is not None
    target = candidate.selected_target
    return (
        node.node_id == target.node_id
        and node.label == target.label
        and node.kind.casefold() == target.kind.casefold()
        and node.role == target.role
        and sorted(node.aliases) == sorted(target.aliases)
        and sorted(node.source_domains) == sorted(target.source_domains)
    )


def _existing_resource_matches(
    node: UnionSupergraphNode, statblock_id: str
) -> bool:
    expected_node_id = external_statblock_node_id(statblock_id)
    expected_label = f"External statblock {statblock_id}"
    if node.node_id != expected_node_id:
        return False
    if node.kind.casefold() != "external_resource":
        return False
    if node.role != "statblock":
        return False
    if node.label != expected_label:
        return False
    if sorted(node.aliases) != sorted([expected_label]):
        return False
    if sorted(node.source_domains) != ["manual_seed"]:
        return False
    if node.external_resource is None:
        return False
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
    return node.external_resource.model_dump(mode="json", by_alias=True) == expected.model_dump(
        mode="json", by_alias=True
    )


def _existing_binding_matches(
    edge: UnionSupergraphEdge,
    *,
    threat_node_id: str,
    accepted_ref: AcceptedMechanicsRefV1,
) -> bool:
    expected_value, expected_edge_id, _ = _binding_payload(
        threat_node_id=threat_node_id,
        accepted_ref=accepted_ref,
    )
    if edge.edge_id != expected_edge_id:
        return False
    if edge.source_node_id != threat_node_id:
        return False
    if edge.target_node_id != external_statblock_node_id(accepted_ref.statblock_id):
        return False
    if edge.predicate != "uses_statblock":
        return False
    try:
        parsed = parse_threat_statblock_binding_assertion(
            subject_node_id=edge.source_node_id,
            target_node_id=edge.target_node_id,
            predicate=edge.predicate,
            value=expected_value,
        )
    except ValueError:
        return False
    return parsed is not None and edge.threat_statblock_binding == parsed


def _run_exact_parent_preflight(
    store,
    *,
    operation: ThreatPublicationOperationV1,
    resolution: ThreatPublicationIdentityResolutionV1,
    decision: ProposalDecision,
) -> str | None:
    accepted_ref = operation.source_snapshot.accepted_mechanics_ref
    resource_node_id = external_statblock_node_id(accepted_ref.statblock_id)
    if decision == "create_new":
        assert resolution.created_node_id is not None
        threat_node_id = resolution.created_node_id
        if threat_node_id in store.nodes:
            return "create-new Threat ID already exists at expected parent"
    else:
        assert resolution.selected_target is not None
        threat_node_id = resolution.selected_target.node_id
        existing = store.nodes.get(threat_node_id)
        if existing is None:
            return "connect target missing at expected parent"
        if existing.kind.casefold() != "threat":
            return "connect target is not a Threat at expected parent"
        if not _node_matches_candidate(existing, resolution):
            return "connect target does not match snapshotted candidate"

    existing_resource = store.nodes.get(resource_node_id)
    if existing_resource is not None:
        if not _existing_resource_matches(existing_resource, accepted_ref.statblock_id):
            return "incompatible external resource already present"

    _expected_binding_value, expected_edge_id, _ = _binding_payload(
        threat_node_id=threat_node_id,
        accepted_ref=accepted_ref,
    )
    existing_edge = store.edges.get(expected_edge_id)
    if existing_edge is not None:
        if not _existing_binding_matches(
            existing_edge,
            threat_node_id=threat_node_id,
            accepted_ref=accepted_ref,
        ):
            return "incompatible statblock binding already present"
    else:
        for edge in store.edges.values():
            if (
                edge.source_node_id == threat_node_id
                and edge.predicate == "uses_statblock"
                and edge.target_node_id == resource_node_id
            ):
                return "incompatible statblock binding already present"
    return None


def _authored_field_count(decision: ProposalDecision, assertions: list[GraphContributionAssertion]) -> int:
    if decision != "create_new":
        return 0
    return sum(1 for item in assertions if item.assertion_kind == "attribute")


def _effect_summary(
    *,
    decision: ProposalDecision,
    threat_node_id: str,
    accepted_ref: AcceptedMechanicsRefV1,
    assertions: list[GraphContributionAssertion],
) -> ThreatPublicationEffectSummaryV1:
    resource_node_id = external_statblock_node_id(accepted_ref.statblock_id)
    _, edge_id, _ = _binding_payload(
        threat_node_id=threat_node_id,
        accepted_ref=accepted_ref,
    )
    return ThreatPublicationEffectSummaryV1(
        decision=decision,
        threat_node_id=threat_node_id,
        external_resource_node_id=resource_node_id,
        binding_edge_id=edge_id,
        accepted_assertion_count=len(assertions),
        authored_field_assertion_count=_authored_field_count(decision, assertions),
    )


def _commit_claim_message() -> str:
    return "publication commit record claims this operation; no new proposal or supersession"


def _orphan_commit_integrity_outcome(
    draft_id: str, operation_id: str, resolution_id: str | None
) -> ProposalOutcome:
    return ProposalOutcome(
        _response(
            draft_id,
            operation_id,
            resolution_id,
            "publication_proposal_integrity_failure",
            message="commit ledger present without matching proposal authority",
        )
    )


def _commit_claim_busy_outcome(
    draft_id: str, operation_id: str, resolution_id: str
) -> ProposalOutcome:
    return ProposalOutcome(
        _response(
            draft_id,
            operation_id,
            resolution_id,
            "publication_proposal_busy",
            message=_commit_claim_message(),
        ),
        created=False,
    )


def _load_commit_ledger_if_present(
    root: Path, draft_id: str, operation_id: str
) -> ThreatPublicationCommitLedgerV1 | None:
    if not threat_publication_commit_ledger_exists(root, draft_id, operation_id):
        return None
    return load_threat_publication_commit_ledger_unlocked(root, draft_id, operation_id)


def prepare_threat_publication_proposal(
    root: Path,
    draft_id: str,
    operation_id: str,
    resolution_id: str,
    request: PrepareThreatPublicationProposalRequestV1,
    *,
    world_root: Path | None = None,
) -> ProposalOutcome:
    safe_draft = require_draft_id(draft_id)
    safe_op = validate_publication_operation_id(operation_id)
    safe_resolution = validate_resolution_id(resolution_id)
    safe_proposal = validate_proposal_id(request.proposal_id)

    ledger_file = _ledger_path(root, safe_draft, safe_op)
    try:
        commit_claimed = threat_publication_commit_ledger_exists(root, safe_draft, safe_op)
    except ThreatPublicationCommitStorageError as exc:
        return _outcome_from_storage_error(
            safe_draft,
            safe_op,
            safe_resolution,
            ThreatPublicationProposalStorageError(str(exc), kind=exc.kind),
        )

    # Honest no-artifact fast path only when BOTH proposal and commit authority absent.
    if not ledger_file.is_file() and not commit_claimed:
        if request.supersedes_proposal_id is not None:
            return ProposalOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    safe_resolution,
                    "publication_proposal_input_conflict",
                    message="supersedes_proposal_id requires an active proposal",
                ),
                created=False,
            )

        identity_outcome = read_identity_resolution(root, safe_draft, safe_op, safe_resolution)
        resolution = identity_outcome.response.resolution
        if resolution is None:
            return _outcome_from_identity_failure(
                safe_draft, safe_op, safe_resolution, identity_outcome
            )
        if resolution.state != "active":
            return ProposalOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    safe_resolution,
                    "publication_proposal_resolution_not_active",
                    message="identity resolution is not active",
                )
            )
        if resolution.decision == "refuse":
            return ProposalOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    safe_resolution,
                    "publication_proposal_identity_refused",
                    message="identity resolution refused publication",
                )
            )
        if resolution.decision not in ("create_new", "connect_existing"):
            return ProposalOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    safe_resolution,
                    "publication_proposal_resolution_not_active",
                    message="identity resolution is not publishable",
                )
            )

    with threat_publication_lifecycle_lock(root, safe_draft, safe_op):
        try:
            existing_ledger = _load_ledger_unlocked(root, safe_draft, safe_op)
        except ThreatPublicationProposalStorageError as exc:
            return _outcome_from_storage_error(safe_draft, safe_op, safe_resolution, exc)

        try:
            commit_ledger = load_threat_publication_commit_ledger_unlocked(
                root, safe_draft, safe_op
            )
        except ThreatPublicationCommitStorageError as exc:
            return _outcome_from_storage_error(
                safe_draft,
                safe_op,
                safe_resolution,
                ThreatPublicationProposalStorageError(str(exc), kind=exc.kind),
            )

        if commit_ledger is not None and existing_ledger is None:
            return ProposalOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    safe_resolution,
                    "publication_proposal_integrity_failure",
                    message="commit claim exists without matching proposal ledger",
                ),
                created=False,
            )

        if existing_ledger is not None:
            existing_proposal = _find_proposal(existing_ledger, safe_proposal)
            if existing_proposal is not None:
                incoming_digest = prepare_request_digest(
                    safe_draft, safe_op, safe_resolution, request
                )
                if incoming_digest == existing_proposal.request_digest:
                    return ProposalOutcome(
                        _response(
                            safe_draft,
                            safe_op,
                            safe_resolution,
                            _proposal_label(existing_proposal),
                            proposal=existing_proposal,
                        ),
                        created=False,
                    )
                return ProposalOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_resolution,
                        "publication_proposal_input_conflict",
                        proposal=existing_proposal,
                        message="proposal_id reused with a changed request",
                    ),
                    created=False,
                )

            if commit_ledger is not None:
                claimed = commit_ledger.commit.proposal_id
                if _find_proposal(existing_ledger, claimed) is None:
                    return ProposalOutcome(
                        _response(
                            safe_draft,
                            safe_op,
                            safe_resolution,
                            "publication_proposal_integrity_failure",
                            message="commit claim exists without matching proposal",
                        ),
                        created=False,
                    )
                return ProposalOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_resolution,
                        "publication_proposal_busy",
                        message=(
                            "publication commit claim exists for this operation; "
                            "new proposals and supersession are refused"
                        ),
                    ),
                    created=False,
                )

            if (
                existing_ledger.active_proposal_id is not None
                and request.supersedes_proposal_id is None
            ):
                return ProposalOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_resolution,
                        "publication_proposal_busy",
                        message="active proposal exists; explicit supersession required",
                    ),
                    created=False,
                )
            if request.supersedes_proposal_id is not None:
                if commit_ledger is not None:
                    return _commit_claim_busy_outcome(safe_draft, safe_op, safe_resolution)
                if request.supersedes_proposal_id != existing_ledger.active_proposal_id:
                    return ProposalOutcome(
                        _response(
                            safe_draft,
                            safe_op,
                            safe_resolution,
                            "publication_proposal_input_conflict",
                            message="supersedes_proposal_id must name the current active proposal",
                        ),
                        created=False,
                    )
        elif request.supersedes_proposal_id is not None:
            return ProposalOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    safe_resolution,
                    "publication_proposal_input_conflict",
                    message="supersedes_proposal_id requires an active proposal",
                ),
                created=False,
            )
        elif commit_ledger is not None:
            return _commit_claim_busy_outcome(safe_draft, safe_op, safe_resolution)

        identity_outcome = read_identity_resolution(root, safe_draft, safe_op, safe_resolution)
        resolution = identity_outcome.response.resolution
        if resolution is None:
            return _outcome_from_identity_failure(
                safe_draft, safe_op, safe_resolution, identity_outcome
            )
        if resolution.state != "active":
            return ProposalOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    safe_resolution,
                    "publication_proposal_resolution_not_active",
                    message="identity resolution is not active",
                )
            )
        if resolution.decision == "refuse":
            return ProposalOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    safe_resolution,
                    "publication_proposal_identity_refused",
                    message="identity resolution refused publication",
                )
            )
        if resolution.decision not in ("create_new", "connect_existing"):
            return ProposalOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    safe_resolution,
                    "publication_proposal_resolution_not_active",
                    message="identity resolution is not publishable",
                )
            )

        refresh = refresh_publication_operation(root, safe_draft, safe_op)
        if refresh.response.result_label != "publication_ready" or refresh.response.operation is None:
            return _outcome_from_publication_failure(
                safe_draft, safe_op, safe_resolution, refresh
            )
        operation = refresh.response.operation

        if (
            resolution.draft_id != safe_draft
            or resolution.operation_id != safe_op
            or resolution.resolution_id != safe_resolution
            or resolution.source_digest != operation.source_digest
            or resolution.expected_parent_revision_id != operation.expected_parent_revision_id
        ):
            return ProposalOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    safe_resolution,
                    "publication_proposal_predecessor_mismatch",
                    message="SBW09a/SBW09b predecessor identity mismatch",
                )
            )

        decision: ProposalDecision = resolution.decision
        if decision == "create_new":
            assert resolution.created_node_id is not None
            threat_node_id = resolution.created_node_id
            accepted_assertions = _build_create_new_assertions(operation, resolution)
        else:
            assert resolution.selected_target is not None
            threat_node_id = resolution.selected_target.node_id
            accepted_assertions = _build_connect_existing_assertions(operation, resolution)

        graph_root = (world_root if world_root is not None else world_graph_root()).resolve()
        try:
            parent_store = _load_exact_parent_store(operation, world_root=graph_root)
        except ThreatPublicationProposalStorageError as exc:
            return _outcome_from_storage_error(safe_draft, safe_op, safe_resolution, exc)

        preflight_error = _run_exact_parent_preflight(
            parent_store,
            operation=operation,
            resolution=resolution,
            decision=decision,
        )
        if preflight_error is not None:
            label: ThreatPublicationProposalResultLabel = (
                "publication_proposal_typed_collision"
                if "collision" in preflight_error.casefold() or "incompatible" in preflight_error.casefold()
                else "publication_proposal_typed_collision"
            )
            return ProposalOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    safe_resolution,
                    label,
                    message=preflight_error,
                )
            )

        sealed_package = _build_sealed_package(
            operation=operation,
            resolution=resolution,
            proposal_id=safe_proposal,
            actor=request.actor,
            accepted_assertions=accepted_assertions,
            decision=decision,
            threat_node_id=threat_node_id,
        )
        try:
            expected_contribution_id = _expected_contribution_id(
                package=sealed_package,
                operation=operation,
                actor=request.actor,
                world_root=graph_root,
            )
        except Exception as exc:
            return ProposalOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    safe_resolution,
                    "publication_proposal_integrity_failure",
                    message=str(exc),
                )
            )

        now = _utc_now_iso()
        proposal_digest_hex = str(sealed_package["proposal_digest"])
        proposal_record = ThreatPublicationProposalV1.model_validate(
            {
                "proposal_id": safe_proposal,
                "request_digest": prepare_request_digest(
                    safe_draft, safe_op, safe_resolution, request
                ),
                "draft_id": safe_draft,
                "operation_id": safe_op,
                "resolution_id": safe_resolution,
                "source_digest": operation.source_digest,
                "resolution_request_digest": resolution.request_digest,
                "candidate_set_digest": resolution.candidate_set_digest,
                "expected_parent_revision_id": operation.expected_parent_revision_id,
                "decision": decision,
                "threat_node_id": threat_node_id,
                "sealed_proposal_id": safe_proposal,
                "sealed_proposal_digest": f"sha256:{proposal_digest_hex}",
                "sealed_proposal_version": int(sealed_package["proposal_version"]),
                "sealed_proposal": sealed_package,
                "expected_contribution_id": expected_contribution_id,
                "accepted_assertion_ids": [item.assertion_id for item in accepted_assertions],
                "effect_summary": _effect_summary(
                    decision=decision,
                    threat_node_id=threat_node_id,
                    accepted_ref=operation.source_snapshot.accepted_mechanics_ref,
                    assertions=accepted_assertions,
                ).model_dump(mode="json"),
                "state": "active",
                "supersedes_proposal_id": request.supersedes_proposal_id,
                "superseded_by_proposal_id": None,
                "created_by": request.actor,
                "operator_note": request.operator_note,
                "created_at": now,
                "updated_at": now,
            }
        )

        ledger = existing_ledger or _empty_ledger(safe_draft, safe_op)
        if len(ledger.proposals) >= MAX_PROPOSALS_PER_OPERATION:
            return ProposalOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    safe_resolution,
                    "publication_proposal_history_full",
                    message="publication proposal history bound reached",
                )
            )

        updated_proposals = list(ledger.proposals)
        if request.supersedes_proposal_id is not None:
            predecessor = _find_proposal(ledger, request.supersedes_proposal_id)
            if predecessor is None:
                return ProposalOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        safe_resolution,
                        "publication_proposal_input_conflict",
                        message="supersedes_proposal_id must reference a ledger proposal",
                    )
                )
            superseded_predecessor = predecessor.model_copy(
                update={
                    "state": "superseded",
                    "superseded_by_proposal_id": safe_proposal,
                    "updated_at": now,
                }
            )
            updated_proposals = _replace_proposal(
                ThreatPublicationProposalLedgerV1(
                    draft_id=safe_draft,
                    operation_id=safe_op,
                    active_proposal_id=ledger.active_proposal_id,
                    proposals=updated_proposals,
                ),
                superseded_predecessor,
            )
        updated_proposals = [*updated_proposals, proposal_record]

        new_ledger = ThreatPublicationProposalLedgerV1.model_validate(
            {
                "draft_id": safe_draft,
                "operation_id": safe_op,
                "active_proposal_id": safe_proposal,
                "proposals": updated_proposals,
            }
        )
        try:
            _save_ledger_unlocked(root, new_ledger)
        except ThreatPublicationProposalStorageError as exc:
            return _outcome_from_storage_error(safe_draft, safe_op, safe_resolution, exc)

        return ProposalOutcome(
            _response(
                safe_draft,
                safe_op,
                safe_resolution,
                "publication_proposal_ready",
                proposal=proposal_record,
            ),
            created=True,
        )


def read_threat_publication_proposal(
    root: Path,
    draft_id: str,
    operation_id: str,
    proposal_id: str,
) -> ProposalOutcome:
    safe_draft = require_draft_id(draft_id)
    safe_op = validate_publication_operation_id(operation_id)
    safe_proposal = validate_proposal_id(proposal_id)

    ledger_file = _ledger_path(root, safe_draft, safe_op)
    proposal_ledger_exists = ledger_file.is_file()
    commit_ledger_exists = threat_publication_commit_ledger_exists(root, safe_draft, safe_op)

    if not proposal_ledger_exists and commit_ledger_exists:
        with threat_publication_lifecycle_lock(root, safe_draft, safe_op):
            try:
                commit_ledger = load_threat_publication_commit_ledger_unlocked(
                    root, safe_draft, safe_op
                )
                proposal_ledger = _load_ledger_unlocked(root, safe_draft, safe_op)
            except ThreatPublicationProposalStorageError as exc:
                return _outcome_from_storage_error(safe_draft, safe_op, None, exc)
            except ThreatPublicationCommitStorageError as exc:
                return _outcome_from_storage_error(
                    safe_draft,
                    safe_op,
                    None,
                    ThreatPublicationProposalStorageError(str(exc), kind=exc.kind),
                )
            if commit_ledger is not None and proposal_ledger is None:
                return _orphan_commit_integrity_outcome(safe_draft, safe_op, None)

    if not proposal_ledger_exists and not commit_ledger_exists:
        return ProposalOutcome(
            _response(
                safe_draft,
                safe_op,
                None,
                "publication_proposal_not_found",
                message="publication proposal ledger not found",
            )
        )

    with threat_publication_lifecycle_lock(root, safe_draft, safe_op):
        try:
            ledger = _load_ledger_unlocked(root, safe_draft, safe_op)
            commit_ledger = _load_commit_ledger_if_present(root, safe_draft, safe_op)
        except ThreatPublicationProposalStorageError as exc:
            return _outcome_from_storage_error(safe_draft, safe_op, None, exc)
        except ThreatPublicationCommitStorageError as exc:
            return _outcome_from_storage_error(
                safe_draft,
                safe_op,
                None,
                ThreatPublicationProposalStorageError(str(exc), kind=exc.kind),
            )

        if commit_ledger is not None and ledger is None:
            return _orphan_commit_integrity_outcome(safe_draft, safe_op, None)

        if ledger is None:
            return ProposalOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    None,
                    "publication_proposal_not_found",
                    message="publication proposal ledger not found",
                )
            )

        proposal = _find_proposal(ledger, safe_proposal)
        if proposal is None:
            return ProposalOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    None,
                    "publication_proposal_not_found",
                    message="publication proposal not found",
                )
            )

        return ProposalOutcome(
            _response(
                safe_draft,
                safe_op,
                proposal.resolution_id,
                _proposal_label(proposal),
                proposal=proposal,
            ),
            created=False,
        )
