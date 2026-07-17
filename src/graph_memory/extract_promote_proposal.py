"""Sealed promote proposals: identity, digest, and confirm-time verification.

Prepare seals the complete durable effect an operator reviewed. Confirm
reconstructs the merge contribution only from sealed fields and refuses to
merge if the package, parent pin, source URI/revision, contribution metadata,
or identity outcomes drifted.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Mapping, Sequence

from graph_memory.kernel.contribution_models import (
    ContributionIdentityMention,
    GraphContribution,
    GraphContributionAssertion,
)
from graph_memory.kernel.contributions import canonical_payload_sha256

PROMOTE_PROPOSAL_SCHEMA = "dmb_extract_promote_proposal_v1"
PROMOTE_PROPOSAL_VERSION = 2


class PromoteProposalError(ValueError):
    """Raised when a promote proposal cannot be sealed or verified."""


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_proposal_digest(effect_body: Mapping[str, Any]) -> str:
    """SHA-256 over the sealed effect body (no mutable envelope fields)."""
    return hashlib.sha256(_canonical_json(effect_body).encode("utf-8")).hexdigest()


def compute_selection_digest(assertion_ids: Sequence[str]) -> str:
    """SHA-256 over the canonical selected-assertion-id set."""
    canonical = sorted({str(a).strip() for a in assertion_ids if str(a).strip()})
    return hashlib.sha256(_canonical_json(canonical).encode("utf-8")).hexdigest()


def contribution_meta_from_contribution(
    contribution: GraphContribution,
) -> dict[str, Any]:
    """Extract durable contribution metadata that must be sealed."""
    return {
        "source_kind": contribution.source_kind,
        "source_artifact_id": contribution.source_artifact_id,
        "source_revision_id": contribution.source_revision_id,
        "extraction_profile": contribution.extraction_profile,
        "campaign_scope": contribution.campaign_scope,
        "authored_by": contribution.authored_by,
    }


def build_effect_body(
    *,
    world_id: str,
    parent_revision_id: str,
    source_revision_id: str,
    source_artifact_id: str,
    verified_source_uri: str,
    candidate_preview_id: str,
    candidate_schema: str,
    candidate_version: str,
    contribution_meta: Mapping[str, Any],
    accepted_proposals: Sequence[GraphContributionAssertion],
    rejected_assertions: Sequence[GraphContributionAssertion],
    unresolved_mentions: Sequence[ContributionIdentityMention],
    node_id_map: Mapping[str, str],
    identity_outcome_snapshot: Mapping[str, str],
) -> dict[str, Any]:
    uri = (verified_source_uri or "").strip()
    if not uri:
        raise PromoteProposalError("verified_source_uri is required in sealed effect")
    meta = dict(contribution_meta)
    for required in (
        "source_kind",
        "source_artifact_id",
        "source_revision_id",
        "extraction_profile",
        "authored_by",
    ):
        if not str(meta.get(required) or "").strip():
            raise PromoteProposalError(
                f"contribution_meta.{required} is required in sealed effect"
            )
    return {
        "world_id": world_id,
        "parent_revision_id": parent_revision_id,
        "source_revision_id": source_revision_id,
        "source_artifact_id": source_artifact_id,
        "verified_source_uri": uri,
        "candidate_preview_id": candidate_preview_id,
        "candidate_schema": candidate_schema,
        "candidate_version": candidate_version,
        "contribution_meta": {
            "source_kind": str(meta["source_kind"]),
            "source_artifact_id": str(meta["source_artifact_id"]),
            "source_revision_id": str(meta["source_revision_id"]),
            "extraction_profile": str(meta["extraction_profile"]),
            "campaign_scope": meta.get("campaign_scope"),
            "authored_by": str(meta["authored_by"]),
        },
        "accepted_proposals": [
            a.model_dump(mode="json") for a in accepted_proposals
        ],
        "rejected_assertions": [
            a.model_dump(mode="json") for a in rejected_assertions
        ],
        "unresolved_mentions": [
            m.model_dump(mode="json") for m in unresolved_mentions
        ],
        "node_id_map": dict(sorted((str(k), str(v)) for k, v in node_id_map.items())),
        "identity_outcome_snapshot": dict(
            sorted((str(k), str(v)) for k, v in identity_outcome_snapshot.items())
        ),
    }


def seal_promote_proposal(
    *,
    world_id: str,
    parent_revision_id: str,
    source_revision_id: str,
    source_artifact_id: str,
    verified_source_uri: str,
    candidate_preview_id: str,
    candidate_schema: str,
    candidate_version: str,
    contribution_meta: Mapping[str, Any],
    accepted_proposals: Sequence[GraphContributionAssertion],
    rejected_assertions: Sequence[GraphContributionAssertion],
    unresolved_mentions: Sequence[ContributionIdentityMention],
    node_id_map: Mapping[str, str],
    identity_outcome_snapshot: Mapping[str, str],
    prepared_by: str,
    scorer_report: Mapping[str, Any] | None = None,
    diagnostics: Sequence[str] | None = None,
    world_root: str | None = None,
    candidate_graph_path: str | None = None,
    proposal_id: str | None = None,
    proposal_version: int = PROMOTE_PROPOSAL_VERSION,
) -> dict[str, Any]:
    prepared = (prepared_by or "").strip()
    if not prepared:
        raise PromoteProposalError("prepared_by is required to seal a proposal")

    effect = build_effect_body(
        world_id=world_id,
        parent_revision_id=parent_revision_id,
        source_revision_id=source_revision_id,
        source_artifact_id=source_artifact_id,
        verified_source_uri=verified_source_uri,
        candidate_preview_id=candidate_preview_id,
        candidate_schema=candidate_schema,
        candidate_version=candidate_version,
        contribution_meta=contribution_meta,
        accepted_proposals=accepted_proposals,
        rejected_assertions=rejected_assertions,
        unresolved_mentions=unresolved_mentions,
        node_id_map=node_id_map,
        identity_outcome_snapshot=identity_outcome_snapshot,
    )
    digest = compute_proposal_digest(effect)
    pid = (proposal_id or "").strip() or f"proposal:{uuid.uuid4().hex}"

    package: dict[str, Any] = {
        "schema": PROMOTE_PROPOSAL_SCHEMA,
        "proposal_id": pid,
        "proposal_version": int(proposal_version),
        "proposal_digest": digest,
        "prepared_by": prepared,
        "effect": effect,
        # Advisory only — never used to construct the durable contribution.
        "scorer_report": dict(scorer_report or {}),
        "diagnostics": list(diagnostics or []),
    }
    if world_root:
        package["world_root"] = world_root
    if candidate_graph_path:
        package["candidate_graph_path"] = candidate_graph_path
    return package


def _parse_assertions(
    items: Sequence[Mapping[str, Any]] | None,
) -> list[GraphContributionAssertion]:
    return [
        GraphContributionAssertion.model_validate(item) for item in (items or [])
    ]


def _parse_mentions(
    items: Sequence[Mapping[str, Any]] | None,
) -> list[ContributionIdentityMention]:
    return [
        ContributionIdentityMention.model_validate(item) for item in (items or [])
    ]


def recompute_digest_from_package(package: Mapping[str, Any]) -> str:
    effect = package.get("effect")
    if not isinstance(effect, dict):
        raise PromoteProposalError("review package missing effect body")
    return compute_proposal_digest(effect)


def verify_promote_proposal(
    package: Mapping[str, Any],
    *,
    confirming_principal: str,
    expected_parent_revision_id: str | None = None,
    selected_assertion_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Verify seal integrity and return the parsed sealed effect.

    Raises PromoteProposalError on any mismatch. Does not mutate the world.
    """
    principal = (confirming_principal or "").strip()
    if not principal:
        raise PromoteProposalError("confirming_principal is required")

    if package.get("schema") != PROMOTE_PROPOSAL_SCHEMA:
        raise PromoteProposalError(
            f"unsupported review package schema: {package.get('schema')!r}"
        )
    if int(package.get("proposal_version") or 0) != PROMOTE_PROPOSAL_VERSION:
        raise PromoteProposalError(
            f"unsupported proposal_version: {package.get('proposal_version')!r}"
        )
    if not str(package.get("proposal_id") or "").strip():
        raise PromoteProposalError("proposal_id is required")
    if not str(package.get("prepared_by") or "").strip():
        raise PromoteProposalError("prepared_by is required on sealed proposal")

    sealed_digest = str(package.get("proposal_digest") or "").strip()
    if not sealed_digest:
        raise PromoteProposalError("proposal_digest is required")

    recomputed = recompute_digest_from_package(package)
    if recomputed != sealed_digest:
        raise PromoteProposalError(
            "proposal_digest mismatch: package effect was modified after prepare"
        )

    effect = dict(package["effect"])
    parent = str(effect.get("parent_revision_id") or "").strip()
    if expected_parent_revision_id is not None:
        expected = str(expected_parent_revision_id).strip()
        if parent != expected:
            raise PromoteProposalError(
                f"parent_revision_id mismatch: sealed={parent!r} head={expected!r}"
            )

    verified_source_uri = str(effect.get("verified_source_uri") or "").strip()
    if not verified_source_uri:
        raise PromoteProposalError("sealed effect missing verified_source_uri")

    contribution_meta = dict(effect.get("contribution_meta") or {})
    for required in (
        "source_kind",
        "source_artifact_id",
        "source_revision_id",
        "extraction_profile",
        "authored_by",
    ):
        if not str(contribution_meta.get(required) or "").strip():
            raise PromoteProposalError(
                f"sealed effect missing contribution_meta.{required}"
            )

    # Reject unsealed envelope fields that historically leaked into durable
    # construction — confirm must never trust them.
    if "contribution_candidate" in package:
        raise PromoteProposalError(
            "review package must not carry contribution_candidate; "
            "durable contribution is reconstructed only from sealed effect"
        )
    if package.get("verified_source_uri") is not None:
        envelope_uri = str(package.get("verified_source_uri") or "").strip()
        if envelope_uri and envelope_uri != verified_source_uri:
            raise PromoteProposalError(
                "envelope verified_source_uri disagrees with sealed effect"
            )

    accepted = _parse_assertions(effect.get("accepted_proposals"))
    by_id = {a.assertion_id: a for a in accepted}
    if selected_assertion_ids is not None:
        for assertion_id in selected_assertion_ids:
            if assertion_id not in by_id:
                raise PromoteProposalError(
                    f"selected assertion {assertion_id!r} is not in sealed accepted_proposals"
                )

    # Identity outcomes in sealed assertions must match the snapshot.
    snapshot = {
        str(k): str(v)
        for k, v in dict(effect.get("identity_outcome_snapshot") or {}).items()
    }
    for assertion in accepted:
        if assertion.assertion_kind != "node":
            continue
        outcome = assertion.identity_resolution_outcome
        if not outcome:
            raise PromoteProposalError(
                f"sealed assertion {assertion.assertion_id} missing identity_resolution_outcome"
            )
        for extract_id, durable_id in dict(effect.get("node_id_map") or {}).items():
            if durable_id == assertion.subject_node_id:
                snap = snapshot.get(str(extract_id))
                if snap is not None and snap != outcome:
                    raise PromoteProposalError(
                        f"identity outcome drift for {extract_id}: "
                        f"sealed_assertion={outcome!r} snapshot={snap!r}"
                    )

    # Guard against assertion payload tampering: re-hash sealed accepted set.
    sealed_accepted_digest = canonical_payload_sha256(
        [a.model_dump(mode="json") for a in accepted]
    )
    effect_accepted_digest = canonical_payload_sha256(
        effect.get("accepted_proposals") or []
    )
    if sealed_accepted_digest != effect_accepted_digest:
        raise PromoteProposalError("accepted_proposals payload integrity failure")

    return {
        "proposal_id": str(package["proposal_id"]),
        "proposal_version": int(package["proposal_version"]),
        "proposal_digest": sealed_digest,
        "prepared_by": str(package["prepared_by"]),
        "confirming_principal": principal,
        "effect": effect,
        "accepted_proposals": accepted,
        "rejected_assertions": _parse_assertions(effect.get("rejected_assertions")),
        "unresolved_mentions": _parse_mentions(effect.get("unresolved_mentions")),
        "node_id_map": {
            str(k): str(v) for k, v in dict(effect.get("node_id_map") or {}).items()
        },
        "identity_outcome_snapshot": snapshot,
        "parent_revision_id": parent,
        "source_revision_id": str(effect.get("source_revision_id") or ""),
        "source_artifact_id": str(effect.get("source_artifact_id") or ""),
        "verified_source_uri": verified_source_uri,
        "contribution_meta": contribution_meta,
        "world_id": str(effect.get("world_id") or ""),
        "candidate_preview_id": str(effect.get("candidate_preview_id") or ""),
        "candidate_schema": str(effect.get("candidate_schema") or ""),
        "candidate_version": str(effect.get("candidate_version") or ""),
    }
