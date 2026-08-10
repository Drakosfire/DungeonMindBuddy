"""GraphContribution factory and deterministic ID helpers (PR005)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from graph_memory.kernel.contribution_models import (
    ContributionIdentityMention,
    ContributionSourceKind,
    GraphContribution,
    GraphContributionAssertion,
    GraphContributionAssertionCorrection,
)

PROVENANCE_ONLY_ASSERTION_VALUE_KEYS = frozenset(
    {
        "source_domain",
        "source_domains",
        "source_artifact_id",
        "source_artifacts",
        "source_revision_id",
        "evidence",
        "evidence_ref_ids",
    }
)


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


# Lifecycle ledger fields that may change after a contribution is first written
# (supersession, retraction, diagnostics append). They are excluded from the
# revision-bound source-authority digest so historical revision pins remain
# readable after later lifecycle mutations of the mutable ledger record.
CONTRIBUTION_SOURCE_PAYLOAD_EXCLUDED_FIELDS = frozenset({"status", "diagnostics"})


def canonical_payload_sha256(payload: object) -> str:
    """Hash any JSON-serializable payload with the repo's canonical JSON rules."""
    return hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    ).hexdigest()


def compute_contribution_payload_sha256(contribution: GraphContribution) -> str:
    """Hash the complete canonical GraphContribution payload (including lifecycle)."""
    return canonical_payload_sha256(contribution.model_dump(mode="json", by_alias=True))


def contribution_source_payload(contribution: GraphContribution) -> dict[str, Any]:
    """Return the lifecycle-neutral source body used for revision-bound digests."""
    payload = contribution.model_dump(mode="json", by_alias=True)
    result = {
        key: value
        for key, value in payload.items()
        if key not in CONTRIBUTION_SOURCE_PAYLOAD_EXCLUDED_FIELDS
    }
    # Historical compatibility: empty correction lists must not change digests
    # for contributions authored before assertion-level correction existed.
    if not result.get("assertion_corrections"):
        result.pop("assertion_corrections", None)
    return result


def compute_contribution_source_payload_sha256(contribution: GraphContribution) -> str:
    """Hash the lifecycle-neutral contribution source payload.

    Stable across ledger ``status`` / ``diagnostics`` mutations. Changes when
    semantic contribution content changes.
    """
    return canonical_payload_sha256(contribution_source_payload(contribution))


def compute_correction_digest(
    assertion_corrections: list[GraphContributionAssertionCorrection] | None,
) -> str | None:
    """Canonical digest of durable assertion-correction links (or None if empty)."""
    corrections = list(assertion_corrections or [])
    if not corrections:
        return None
    payload = [
        correction.model_dump(mode="json", by_alias=True) for correction in corrections
    ]
    return hashlib.sha256(_canonical_json({"assertion_corrections": payload}).encode("utf-8")).hexdigest()


def compute_contribution_id(
    *,
    world_id: str,
    source_kind: ContributionSourceKind,
    source_artifact_id: str | None,
    source_revision_id: str | None,
    extraction_profile: str | None,
    authored_by: str | None,
    supersedes_contribution_id: str | None = None,
    proposal_digest: str | None = None,
    selection_digest: str | None = None,
    correction_digest: str | None = None,
) -> str:
    payload = {
        "world_id": world_id,
        "source_kind": source_kind,
        "source_artifact_id": source_artifact_id,
        "source_revision_id": source_revision_id,
        "extraction_profile": extraction_profile,
        "authored_by": authored_by,
        "supersedes_contribution_id": supersedes_contribution_id,
        "proposal_digest": proposal_digest,
        "selection_digest": selection_digest,
    }
    # Omit when absent so historical contribution IDs remain stable.
    if correction_digest is not None:
        payload["correction_digest"] = correction_digest
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:16]
    return f"contribution:{digest}"


def compute_assertion_id(
    *,
    assertion_kind: str,
    subject_node_id: str | None,
    target_node_id: str | None,
    predicate: str | None,
    label: str | None,
    value: dict[str, Any] | None,
    campaign_scope: str | None,
    temporal_scope: dict[str, Any] | None,
    epistemic_kind: str | None,
    visibility: str | None,
) -> str:
    payload = {
        "assertion_kind": assertion_kind,
        "subject_node_id": subject_node_id,
        "target_node_id": target_node_id,
        "predicate": predicate,
        "label": label,
        "value": semantic_assertion_value(value),
        "campaign_scope": campaign_scope,
        "temporal_scope": temporal_scope,
        "epistemic_kind": epistemic_kind,
        "visibility": visibility,
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:16]
    return f"assertion:{digest}"


def semantic_assertion_value(value: dict[str, Any] | None) -> dict[str, Any]:
    """Return the shallow semantic portion of an assertion value."""
    return {
        key: item
        for key, item in dict(value or {}).items()
        if key not in PROVENANCE_ONLY_ASSERTION_VALUE_KEYS
    }


@dataclass(frozen=True)
class AssertionProvenance:
    """Normalized explicit provenance declared by one assertion.

    This is deliberately independent of assertion identity: provenance-only
    fields may change without changing ``assertion_id``, so merge,
    validation, and projection must all derive their lineage from this same
    representation.
    """

    evidence_ref_ids: list[str]
    source_artifact_ids: list[str]
    source_domains: list[str]


def normalize_assertion_provenance(
    assertion: GraphContributionAssertion,
) -> AssertionProvenance:
    """Return every supported explicit provenance representation consistently."""
    value = dict(assertion.value or {})
    evidence_ref_ids: set[str] = set(assertion.evidence_ref_ids)
    nested_evidence_ref_ids = value.get("evidence_ref_ids")
    if isinstance(nested_evidence_ref_ids, list):
        evidence_ref_ids.update(
            str(item) for item in nested_evidence_ref_ids if str(item).strip()
        )

    source_artifact_ids: set[str] = set()
    source_domains: set[str] = set()
    source_domain = value.get("source_domain")
    if isinstance(source_domain, str) and source_domain.strip():
        source_domains.add(source_domain.strip())
    declared_source_domains = value.get("source_domains")
    if isinstance(declared_source_domains, list):
        source_domains.update(
            str(item).strip()
            for item in declared_source_domains
            if isinstance(item, str) and item.strip()
        )
    if assertion.source_artifact_id:
        source_artifact_ids.add(assertion.source_artifact_id)
    nested_source_artifact_id = value.get("source_artifact_id")
    if nested_source_artifact_id:
        source_artifact_ids.add(str(nested_source_artifact_id))

    for entry in value.get("evidence") or []:
        if not isinstance(entry, dict):
            continue
        evidence_ref_id = entry.get("evidence_ref_id")
        if evidence_ref_id:
            evidence_ref_ids.add(str(evidence_ref_id))
        source_artifact_id = entry.get("source_artifact_id")
        if source_artifact_id:
            source_artifact_ids.add(str(source_artifact_id))
        entry_source_domain = entry.get("source_domain")
        if isinstance(entry_source_domain, str) and entry_source_domain.strip():
            source_domains.add(entry_source_domain.strip())

    for entry in value.get("source_artifacts") or []:
        if isinstance(entry, dict):
            source_artifact_id = entry.get("source_artifact_id")
            if source_artifact_id:
                source_artifact_ids.add(str(source_artifact_id))
            entry_source_domain = entry.get("source_domain")
            if isinstance(entry_source_domain, str) and entry_source_domain.strip():
                source_domains.add(entry_source_domain.strip())

    return AssertionProvenance(
        evidence_ref_ids=sorted(evidence_ref_ids),
        source_artifact_ids=sorted(source_artifact_ids),
        source_domains=sorted(source_domains),
    )


def explicit_assertion_evidence_ref_ids(assertion: GraphContributionAssertion) -> list[str]:
    """Full explicit evidence lineage declared by one assertion.

    Includes ``evidence_ref_ids`` (top level and nested under ``value``) and
    ``evidence_ref_id`` entries embedded in ``value["evidence"]`` objects.
    Provenance-only fields are excluded from assertion identity, so this must
    be the single place both the merge (write) path and the projection (read)
    path derive "what evidence did this contribution actually assert" from —
    otherwise a mutation to provenance-only fields can silently change what
    the projection returns without changing ``assertion_id``.
    """
    return normalize_assertion_provenance(assertion).evidence_ref_ids


def explicit_assertion_source_artifact_ids(assertion: GraphContributionAssertion) -> list[str]:
    """Full explicit source-artifact lineage declared by one assertion.

    Includes ``source_artifact_id`` (top level and nested under ``value``)
    and ``source_artifact_id`` entries embedded in ``value["source_artifacts"]``
    objects. See ``explicit_assertion_evidence_ref_ids`` for why this must be
    shared between the merge and projection paths.
    """
    return normalize_assertion_provenance(assertion).source_artifact_ids


def _canonicalize_assertion_identity(
    assertion: GraphContributionAssertion,
) -> tuple[GraphContributionAssertion, tuple[str, str] | None]:
    current_id = compute_assertion_id(
        assertion_kind=assertion.assertion_kind,
        subject_node_id=assertion.subject_node_id,
        target_node_id=assertion.target_node_id,
        predicate=assertion.predicate,
        label=assertion.label,
        value=assertion.value,
        campaign_scope=assertion.campaign_scope,
        temporal_scope=assertion.temporal_scope,
        epistemic_kind=assertion.epistemic_kind,
        visibility=assertion.visibility,
    )
    if assertion.assertion_id == current_id:
        return assertion, None
    return assertion.model_copy(update={"assertion_id": current_id}), (
        assertion.assertion_id,
        current_id,
    )


def _canonicalize_graph_contribution_assertions(
    contribution: GraphContribution,
) -> tuple[GraphContribution, list[tuple[str, str]]]:
    """Return an immutable contribution copy using current assertion IDs."""
    rekeys: list[tuple[str, str]] = []

    def canonicalize(
        assertions: list[GraphContributionAssertion],
    ) -> list[GraphContributionAssertion]:
        canonical: list[GraphContributionAssertion] = []
        for assertion in assertions:
            updated, rekey = _canonicalize_assertion_identity(assertion)
            canonical.append(updated)
            if rekey is not None:
                rekeys.append(rekey)
        return canonical

    accepted_before = len(rekeys)
    accepted = canonicalize(contribution.accepted_assertions)
    accepted_rekey_map = {
        old_id: new_id for old_id, new_id in rekeys[accepted_before:]
    }
    corrections: list[GraphContributionAssertionCorrection] = []
    for correction in contribution.assertion_corrections:
        replacement_id = correction.replacement_assertion_id
        if (
            replacement_id is not None
            and replacement_id in accepted_rekey_map
        ):
            replacement_id = accepted_rekey_map[replacement_id]
        corrections.append(
            correction.model_copy(update={"replacement_assertion_id": replacement_id})
        )

    return (
        contribution.model_copy(
            update={
                "candidate_assertions": canonicalize(contribution.candidate_assertions),
                "accepted_assertions": accepted,
                "rejected_assertions": canonicalize(contribution.rejected_assertions),
                "assertion_corrections": corrections,
            }
        ),
        rekeys,
    )


def _with_contribution_id(
    assertions: list[GraphContributionAssertion],
    contribution_id: str,
) -> list[GraphContributionAssertion]:
    updated: list[GraphContributionAssertion] = []
    for assertion in assertions:
        if assertion.contribution_id and assertion.contribution_id != contribution_id:
            # Placeholder contribution_id is rewritten to the computed id.
            if not assertion.contribution_id.startswith("contribution:"):
                updated.append(
                    assertion.model_copy(update={"contribution_id": contribution_id})
                )
            else:
                updated.append(
                    assertion.model_copy(update={"contribution_id": contribution_id})
                )
        else:
            updated.append(
                assertion.model_copy(update={"contribution_id": contribution_id})
            )
    return updated


def create_graph_contribution(
    *,
    world_id: str,
    source_kind: ContributionSourceKind,
    source_artifact_id: str | None = None,
    source_revision_id: str | None = None,
    extraction_profile: str | None = None,
    campaign_scope: str | None = None,
    candidate_assertions: list[GraphContributionAssertion] | None = None,
    accepted_assertions: list[GraphContributionAssertion] | None = None,
    rejected_assertions: list[GraphContributionAssertion] | None = None,
    unresolved_mentions: list[ContributionIdentityMention] | None = None,
    identity_decision_ids: list[str] | None = None,
    assertion_corrections: list[GraphContributionAssertionCorrection] | None = None,
    authored_by: str | None = None,
    supersedes_contribution_id: str | None = None,
    proposal_digest: str | None = None,
    selection_digest: str | None = None,
    produced_at: str | None = None,
    diagnostics: list[str] | None = None,
) -> GraphContribution:
    """Build a GraphContribution with a deterministic contribution_id.

    ``produced_at`` is metadata only and does not affect identity.
    ``proposal_digest``, ``selection_digest``, and ``correction_digest`` (when
    set) enter durable contribution identity so distinct sealed proposals,
    accepted assertion subsets, and correction linkages cannot collide.
    """
    if not world_id.strip():
        raise ValueError("world_id must be non-empty")

    # Canonicalize accepted assertions before hashing so correction linkage and
    # contribution identity agree on replacement_assertion_id.
    prelim_accepted: list[GraphContributionAssertion] = []
    accepted_rekey_map: dict[str, str] = {}
    for assertion in list(accepted_assertions or []):
        updated, rekey = _canonicalize_assertion_identity(assertion)
        prelim_accepted.append(updated)
        if rekey is not None:
            accepted_rekey_map[rekey[0]] = rekey[1]

    corrections: list[GraphContributionAssertionCorrection] = []
    for correction in list(assertion_corrections or []):
        replacement_id = correction.replacement_assertion_id
        if (
            replacement_id is not None
            and replacement_id in accepted_rekey_map
        ):
            replacement_id = accepted_rekey_map[replacement_id]
        corrections.append(
            correction.model_copy(update={"replacement_assertion_id": replacement_id})
        )
    correction_digest = compute_correction_digest(corrections)

    contribution_id = compute_contribution_id(
        world_id=world_id,
        source_kind=source_kind,
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        extraction_profile=extraction_profile,
        authored_by=authored_by,
        supersedes_contribution_id=supersedes_contribution_id,
        proposal_digest=proposal_digest,
        selection_digest=selection_digest,
        correction_digest=correction_digest,
    )

    candidates = _with_contribution_id(
        list(candidate_assertions or []), contribution_id
    )
    accepted = _with_contribution_id(prelim_accepted, contribution_id)
    rejected = _with_contribution_id(list(rejected_assertions or []), contribution_id)

    contribution = GraphContribution(
        contribution_id=contribution_id,
        world_id=world_id,
        source_kind=source_kind,
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        extraction_profile=extraction_profile,
        produced_at=produced_at or _utc_now_iso(),
        campaign_scope=campaign_scope,
        status="active",
        supersedes_contribution_id=supersedes_contribution_id,
        candidate_assertions=candidates,
        accepted_assertions=accepted,
        rejected_assertions=rejected,
        unresolved_mentions=list(unresolved_mentions or []),
        identity_decision_ids=list(identity_decision_ids or []),
        assertion_corrections=corrections,
        authored_by=authored_by,
        diagnostics=list(diagnostics or []),
    )
    canonical, rekeys = _canonicalize_graph_contribution_assertions(contribution)
    # Accepted assertions were pre-canonicalized; remaining rekeys are
    # candidate/rejected only and must not rewrite correction linkage.
    if not rekeys:
        return canonical
    return canonical.model_copy(
        update={
            "diagnostics": [
                *canonical.diagnostics,
                *[
                    f"assertion_identity_rekeyed:{old_id}->{new_id}"
                    for old_id, new_id in rekeys
                ],
            ]
        }
    )


def create_edge_assertion_correction_contribution(
    *,
    world_id: str,
    authored_by: str,
    target_contribution_id: str,
    target_assertion_id: str,
    replacement_assertion: GraphContributionAssertion,
    source_artifact_id: str | None = None,
    source_revision_id: str | None = None,
    campaign_scope: str | None = None,
    produced_at: str | None = None,
    diagnostics: list[str] | None = None,
) -> GraphContribution:
    """Build a human-authored structural edge correction contribution.

    Binds exactly one ``contradicts_and_replaces`` link to the sole accepted
    replacement edge assertion. Does not publish; callers must use the Kernel
    correction operation with expected-parent CAS.
    """
    if not authored_by or not authored_by.strip():
        raise ValueError("authored_by must be non-blank for edge assertion correction")
    if replacement_assertion.assertion_kind != "edge":
        raise ValueError("replacement assertion must be assertion_kind='edge'")
    if replacement_assertion.acceptance_state != "accepted":
        raise ValueError("replacement assertion must be acceptance_state='accepted'")

    # Placeholder replacement id is rewritten after canonicalize.
    placeholder_replacement_id = replacement_assertion.assertion_id
    correction = GraphContributionAssertionCorrection(
        correction_kind="contradicts_and_replaces",
        target_contribution_id=target_contribution_id,
        target_assertion_id=target_assertion_id,
        replacement_assertion_id=placeholder_replacement_id,
    )
    return create_graph_contribution(
        world_id=world_id,
        source_kind="graph_review_authored_assertion",
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope=campaign_scope,
        accepted_assertions=[replacement_assertion],
        assertion_corrections=[correction],
        authored_by=authored_by.strip(),
        produced_at=produced_at,
        diagnostics=diagnostics,
    )


def create_edge_assertion_contradiction_contribution(
    *,
    world_id: str,
    authored_by: str,
    target_assertion_id: str,
    target_contribution_ids: list[str],
    source_artifact_id: str | None = None,
    source_revision_id: str | None = None,
    campaign_scope: str | None = None,
    produced_at: str | None = None,
    diagnostics: list[str] | None = None,
) -> GraphContribution:
    """Build a human-authored edge contradiction with no replacement.

    Emits one ``contradicts`` link per exact active supporting contribution for
    a single target assertion. Does not publish; callers must use
    ``contradict_edge_assertion_support`` with expected-parent CAS.
    """
    if not authored_by or not authored_by.strip():
        raise ValueError(
            "authored_by must be non-blank for edge assertion contradiction"
        )
    if not target_assertion_id or not str(target_assertion_id).strip():
        raise ValueError("target_assertion_id must be non-blank")
    if not target_contribution_ids:
        raise ValueError("target_contribution_ids must be non-empty")
    if len(target_contribution_ids) != len(set(target_contribution_ids)):
        raise ValueError("target_contribution_ids must be unique")

    corrections = [
        GraphContributionAssertionCorrection(
            correction_kind="contradicts",
            target_contribution_id=contribution_id,
            target_assertion_id=target_assertion_id,
            replacement_assertion_id=None,
        )
        for contribution_id in target_contribution_ids
    ]
    return create_graph_contribution(
        world_id=world_id,
        source_kind="graph_review_authored_assertion",
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope=campaign_scope,
        accepted_assertions=[],
        assertion_corrections=corrections,
        authored_by=authored_by.strip(),
        produced_at=produced_at,
        diagnostics=diagnostics,
    )


def build_assertion(
    *,
    assertion_kind: str,
    acceptance_state: str,
    contribution_id: str = "contribution:pending",
    subject_node_id: str | None = None,
    target_node_id: str | None = None,
    predicate: str | None = None,
    label: str | None = None,
    value: dict[str, Any] | None = None,
    evidence_ref_ids: list[str] | None = None,
    source_artifact_id: str | None = None,
    source_revision_id: str | None = None,
    campaign_scope: str | None = None,
    temporal_scope: dict[str, Any] | None = None,
    visibility: str | None = None,
    epistemic_kind: str | None = None,
    identity_resolution_outcome: str | None = None,
    assertion_id: str | None = None,
) -> GraphContributionAssertion:
    """Helper to build an assertion with a deterministic assertion_id."""
    value_map = dict(value or {})
    computed_id = assertion_id or compute_assertion_id(
        assertion_kind=assertion_kind,
        subject_node_id=subject_node_id,
        target_node_id=target_node_id,
        predicate=predicate,
        label=label,
        value=value_map,
        campaign_scope=campaign_scope,
        temporal_scope=temporal_scope,
        epistemic_kind=epistemic_kind,
        visibility=visibility,
    )
    return GraphContributionAssertion(
        assertion_id=computed_id,
        assertion_kind=assertion_kind,  # type: ignore[arg-type]
        subject_node_id=subject_node_id,
        target_node_id=target_node_id,
        predicate=predicate,
        label=label,
        value=value_map,
        evidence_ref_ids=list(evidence_ref_ids or []),
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope=campaign_scope,
        temporal_scope=temporal_scope,
        visibility=visibility,
        epistemic_kind=epistemic_kind,
        acceptance_state=acceptance_state,  # type: ignore[arg-type]
        identity_resolution_outcome=identity_resolution_outcome,
        contribution_id=contribution_id,
    )
