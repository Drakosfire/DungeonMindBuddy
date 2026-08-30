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

from apps.live_control_server.models.world_graph_contribution_models import (
    ContributionIdentityMention,
    GraphContribution,
    GraphContributionAssertion,
)
from apps.live_control_server.models.world_graph_contributions import canonical_payload_sha256

PROMOTE_PROPOSAL_SCHEMA = "dmb_extract_promote_proposal_v1"
PROMOTE_PROPOSAL_VERSION = 3
PROMOTE_PROPOSAL_VERSION_V2 = 2

# Delimiter for slice-qualified selection keys: f"{contribution_slice_id}{DELIM}{assertion_id}".
# Chosen because assertion/contribution ids never contain a double colon.
SLICE_SELECTOR_DELIMITER = "::"


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


def build_contribution_effect_slice(
    *,
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
    """One sealed contribution slice inside a v3 multi-contribution effect."""
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
    """Build a v2-shaped single-contribution effect (also used as primary mirror)."""
    slice_body = build_contribution_effect_slice(
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
    return {
        "world_id": world_id,
        "parent_revision_id": parent_revision_id,
        **slice_body,
    }


def contribution_slice_id_for(index: int, slice_body: Mapping[str, Any]) -> str:
    """Stable slice identity derived from position + source_kind (not stored).

    Recomputed identically at prepare-review-projection time and at
    confirm time from the same ordered ``slices`` list, so it never needs to
    ride inside the sealed digest. Selection keys are
    ``f"{contribution_slice_id}{SLICE_SELECTOR_DELIMITER}{assertion_id}"``.
    """
    meta = dict(slice_body.get("contribution_meta") or {})
    source_kind = str(meta.get("source_kind") or "unknown").strip() or "unknown"
    return f"{index}:{source_kind}"


def primary_contribution_meta_from_slices(
    slices: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Pick the mirrored top-level contribution_meta for a multi-slice effect.

    Prefers ``source_extraction`` (the recap slice is the human-facing
    primary); falls back to the last slice when no source_extraction slice
    is present.
    """
    if not slices:
        raise PromoteProposalError("contributions must be non-empty")
    primary = slices[-1]
    for item in slices:
        meta = dict(item.get("contribution_meta") or {})
        if str(meta.get("source_kind") or "") == "source_extraction":
            primary = item
            break
    return dict(primary.get("contribution_meta") or {})


def parse_slice_qualified_selector(selector: str) -> tuple[str | None, str]:
    """Split a selection key into ``(contribution_slice_id, assertion_id)``.

    Bare selectors (no delimiter) return ``(None, selector)`` — the caller
    must resolve them against sealed slices and refuse ambiguous matches.
    """
    text = str(selector or "").strip()
    if SLICE_SELECTOR_DELIMITER in text:
        slice_id, _, assertion_id = text.partition(SLICE_SELECTOR_DELIMITER)
        slice_id = slice_id.strip()
        assertion_id = assertion_id.strip()
        if not slice_id or not assertion_id:
            raise PromoteProposalError(
                f"malformed slice-qualified selector: {selector!r}"
            )
        return slice_id, assertion_id
    return None, text


def resolve_slice_qualified_selection(
    slices: Sequence[Mapping[str, Any]],
    selectors: Sequence[str],
) -> dict[str, set[str]]:
    """Resolve selection selectors into ``{contribution_slice_id: {assertion_id}}``.

    Selectors may be slice-qualified (``sliceId::assertionId``) or a bare
    ``assertionId`` when it identifies exactly one sealed slice's accepted
    proposal. A bare id present in more than one slice is refused — this is
    the fix for P1 (assertion ids are content-hashed and can legitimately
    collide across independently-sourced slices, e.g. a standing_context
    registry fact re-asserted by the recap extraction with different
    evidence). Raises ``PromoteProposalError`` for unknown or ambiguous ids.
    """
    slice_ids = [contribution_slice_id_for(i, s) for i, s in enumerate(slices)]
    assertions_by_slice: dict[str, set[str]] = {}
    assertion_locations: dict[str, list[str]] = {}
    for slice_id, slice_body in zip(slice_ids, slices):
        ids = {
            str(a.get("assertion_id") or "").strip()
            for a in (slice_body.get("accepted_proposals") or [])
            if str(a.get("assertion_id") or "").strip()
        }
        assertions_by_slice[slice_id] = ids
        for assertion_id in ids:
            assertion_locations.setdefault(assertion_id, []).append(slice_id)

    resolved: dict[str, set[str]] = {}
    for raw in selectors:
        slice_id, assertion_id = parse_slice_qualified_selector(raw)
        if slice_id is not None:
            if slice_id not in assertions_by_slice:
                raise PromoteProposalError(
                    f"selected slice {slice_id!r} is not in sealed contribution slices"
                )
            if assertion_id not in assertions_by_slice[slice_id]:
                raise PromoteProposalError(
                    f"selected assertion {assertion_id!r} is not in sealed "
                    f"contribution slice {slice_id!r}"
                )
            resolved.setdefault(slice_id, set()).add(assertion_id)
            continue
        locations = assertion_locations.get(assertion_id) or []
        if not locations:
            raise PromoteProposalError(
                f"selected assertion {assertion_id!r} is not in sealed accepted_proposals"
            )
        if len(locations) > 1:
            raise PromoteProposalError(
                f"selected assertion {assertion_id!r} is ambiguous across "
                f"contribution slices {locations!r}; use a slice-qualified "
                f"selector '{{contributionSliceId}}{SLICE_SELECTOR_DELIMITER}{{assertionId}}'"
            )
        resolved.setdefault(locations[0], set()).add(assertion_id)
    return resolved


def build_multi_contribution_effect_body(
    *,
    world_id: str,
    parent_revision_id: str,
    contributions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """v3 effect: ordered contribution slices + flat accepted union for selection."""
    if not contributions:
        raise PromoteProposalError("contributions must be non-empty")
    slices = [dict(c) for c in contributions]
    primary_meta = primary_contribution_meta_from_slices(slices)
    primary = next(
        (
            item
            for item in slices
            if dict(item.get("contribution_meta") or {}) == primary_meta
        ),
        slices[-1],
    )
    accepted: list[Any] = []
    rejected: list[Any] = []
    unresolved: list[Any] = []
    node_id_map: dict[str, str] = {}
    identity_outcome_snapshot: dict[str, str] = {}
    for item in slices:
        accepted.extend(list(item.get("accepted_proposals") or []))
        rejected.extend(list(item.get("rejected_assertions") or []))
        unresolved.extend(list(item.get("unresolved_mentions") or []))
        node_id_map.update(
            {str(k): str(v) for k, v in dict(item.get("node_id_map") or {}).items()}
        )
        identity_outcome_snapshot.update(
            {
                str(k): str(v)
                for k, v in dict(item.get("identity_outcome_snapshot") or {}).items()
            }
        )
    return {
        "world_id": world_id,
        "parent_revision_id": parent_revision_id,
        "contributions": slices,
        "source_revision_id": primary["source_revision_id"],
        "source_artifact_id": primary["source_artifact_id"],
        "verified_source_uri": primary["verified_source_uri"],
        "candidate_preview_id": primary["candidate_preview_id"],
        "candidate_schema": primary["candidate_schema"],
        "candidate_version": primary["candidate_version"],
        "contribution_meta": dict(primary["contribution_meta"]),
        "accepted_proposals": accepted,
        "rejected_assertions": rejected,
        "unresolved_mentions": unresolved,
        "node_id_map": dict(sorted(node_id_map.items())),
        "identity_outcome_snapshot": dict(sorted(identity_outcome_snapshot.items())),
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
    proposal_version: int | None = None,
) -> dict[str, Any]:
    prepared = (prepared_by or "").strip()
    if not prepared:
        raise PromoteProposalError("prepared_by is required to seal a proposal")

    version = (
        PROMOTE_PROPOSAL_VERSION_V2
        if proposal_version is None
        else int(proposal_version)
    )
    # Single-contribution seals stay on the v2 flat effect shape for back-compat
    # unless the caller explicitly requests v3.
    if version >= PROMOTE_PROPOSAL_VERSION:
        slice_body = build_contribution_effect_slice(
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
        effect = build_multi_contribution_effect_body(
            world_id=world_id,
            parent_revision_id=parent_revision_id,
            contributions=[slice_body],
        )
        version = PROMOTE_PROPOSAL_VERSION
    else:
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
        version = PROMOTE_PROPOSAL_VERSION_V2

    digest = compute_proposal_digest(effect)
    pid = (proposal_id or "").strip() or f"proposal:{uuid.uuid4().hex}"

    package: dict[str, Any] = {
        "schema": PROMOTE_PROPOSAL_SCHEMA,
        "proposal_id": pid,
        "proposal_version": int(version),
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


def seal_multi_contribution_promote_proposal(
    *,
    world_id: str,
    parent_revision_id: str,
    contribution_slices: Sequence[Mapping[str, Any]],
    prepared_by: str,
    scorer_report: Mapping[str, Any] | None = None,
    diagnostics: Sequence[str] | None = None,
    world_root: str | None = None,
    candidate_graph_path: str | None = None,
    proposal_id: str | None = None,
) -> dict[str, Any]:
    """Seal a v3 package with ordered contribution slices (standing then recap)."""
    prepared = (prepared_by or "").strip()
    if not prepared:
        raise PromoteProposalError("prepared_by is required to seal a proposal")
    effect = build_multi_contribution_effect_body(
        world_id=world_id,
        parent_revision_id=parent_revision_id,
        contributions=contribution_slices,
    )
    digest = compute_proposal_digest(effect)
    pid = (proposal_id or "").strip() or f"proposal:{uuid.uuid4().hex}"
    package: dict[str, Any] = {
        "schema": PROMOTE_PROPOSAL_SCHEMA,
        "proposal_id": pid,
        "proposal_version": PROMOTE_PROPOSAL_VERSION,
        "proposal_digest": digest,
        "prepared_by": prepared,
        "effect": effect,
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


def contribution_slices_from_effect(effect: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Normalize v2 flat effect or v3 contributions list into ordered slices."""
    raw = effect.get("contributions")
    if isinstance(raw, list) and raw:
        return [dict(item) for item in raw if isinstance(item, Mapping)]
    return [
        {
            "source_revision_id": effect.get("source_revision_id"),
            "source_artifact_id": effect.get("source_artifact_id"),
            "verified_source_uri": effect.get("verified_source_uri"),
            "candidate_preview_id": effect.get("candidate_preview_id"),
            "candidate_schema": effect.get("candidate_schema"),
            "candidate_version": effect.get("candidate_version"),
            "contribution_meta": dict(effect.get("contribution_meta") or {}),
            "accepted_proposals": list(effect.get("accepted_proposals") or []),
            "rejected_assertions": list(effect.get("rejected_assertions") or []),
            "unresolved_mentions": list(effect.get("unresolved_mentions") or []),
            "node_id_map": dict(effect.get("node_id_map") or {}),
            "identity_outcome_snapshot": dict(
                effect.get("identity_outcome_snapshot") or {}
            ),
        }
    ]


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
    version = int(package.get("proposal_version") or 0)
    if version not in {PROMOTE_PROPOSAL_VERSION_V2, PROMOTE_PROPOSAL_VERSION}:
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

    slices = contribution_slices_from_effect(effect)
    if not slices:
        raise PromoteProposalError("sealed effect has no contributions")

    verified_source_uri = str(effect.get("verified_source_uri") or "").strip()
    if not verified_source_uri:
        for item in slices:
            meta = dict(item.get("contribution_meta") or {})
            if str(meta.get("source_kind") or "") == "source_extraction":
                verified_source_uri = str(item.get("verified_source_uri") or "").strip()
                break
        if not verified_source_uri:
            verified_source_uri = str(slices[-1].get("verified_source_uri") or "").strip()
    if not verified_source_uri:
        raise PromoteProposalError("sealed effect missing verified_source_uri")

    contribution_meta = dict(effect.get("contribution_meta") or {})
    if not contribution_meta:
        contribution_meta = dict(slices[-1].get("contribution_meta") or {})
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

    for item in slices:
        meta = dict(item.get("contribution_meta") or {})
        for required in (
            "source_kind",
            "source_artifact_id",
            "source_revision_id",
            "extraction_profile",
            "authored_by",
        ):
            if not str(meta.get(required) or "").strip():
                raise PromoteProposalError(
                    f"contribution slice missing contribution_meta.{required}"
                )
        if not str(item.get("verified_source_uri") or "").strip():
            raise PromoteProposalError(
                "contribution slice missing verified_source_uri"
            )

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
    resolved_selection: dict[str, set[str]] | None = None
    if selected_assertion_ids is not None:
        resolved_selection = resolve_slice_qualified_selection(
            slices, selected_assertion_ids
        )

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
        "proposal_version": version,
        "proposal_digest": sealed_digest,
        "prepared_by": str(package["prepared_by"]),
        "confirming_principal": principal,
        "effect": effect,
        "contribution_slices": slices,
        "resolved_selection": resolved_selection,
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
