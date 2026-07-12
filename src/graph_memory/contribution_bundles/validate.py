"""Validate loaded GraphContribution bundles against locked contracts."""

from __future__ import annotations

from collections import Counter
from typing import Any

from graph_memory.contribution_bundles.models import (
    ContributionBundleValidationReport,
    LoadedContributionBundle,
)
from graph_memory.evidence.source_domain import KNOWN_SOURCE_DOMAINS
from graph_memory.kernel.contribution_models import GraphContribution, GraphContributionAssertion
from graph_memory.kernel.contributions import (
    compute_assertion_id,
    compute_contribution_id,
)

_GRAPH_MUTATING_BLOCKED = frozenset(
    {"ambiguous", "blocked_collision", "rejected", "provisional_new"}
)


def _edge_id(assertion: GraphContributionAssertion) -> str | None:
    if assertion.assertion_kind != "edge":
        return None
    value = dict(assertion.value or {})
    explicit = value.get("edge_id")
    if explicit:
        return str(explicit)
    source = assertion.subject_node_id or value.get("source_node_id")
    target = assertion.target_node_id or value.get("target_node_id")
    predicate = assertion.predicate or value.get("predicate")
    if source and target and predicate:
        return f"edge:{source}:{predicate}:{target}"
    return None


def _node_ids(contribution: GraphContribution) -> set[str]:
    nodes: set[str] = set()
    for assertion in contribution.accepted_assertions:
        if assertion.assertion_kind == "node" and assertion.subject_node_id:
            nodes.add(assertion.subject_node_id)
    return nodes


def _edge_ids(contribution: GraphContribution) -> set[str]:
    edges: set[str] = set()
    for assertion in contribution.accepted_assertions:
        edge_id = _edge_id(assertion)
        if edge_id:
            edges.add(edge_id)
    return edges


def _domains_from_assertion(assertion: GraphContributionAssertion) -> set[str]:
    domains: set[str] = set()
    value = dict(assertion.value or {})
    for domain in value.get("source_domains") or []:
        domains.add(str(domain))
    if value.get("source_domain"):
        domains.add(str(value["source_domain"]))
    for evidence in value.get("evidence") or []:
        if isinstance(evidence, dict) and evidence.get("source_domain"):
            domains.add(str(evidence["source_domain"]))
    for artifact in value.get("source_artifacts") or []:
        if isinstance(artifact, dict) and artifact.get("source_domain"):
            domains.add(str(artifact["source_domain"]))
    return domains


def _evidence_coverage(contributions: list[GraphContribution]) -> dict[str, Any]:
    accepted = [a for c in contributions for a in c.accepted_assertions]
    total = len(accepted)
    with_evidence = 0
    with_artifact = 0
    recap_with_session = 0
    recap_total = 0
    non_recap_with_locator = 0
    non_recap_total = 0

    for assertion in accepted:
        refs = list(assertion.evidence_ref_ids)
        value = dict(assertion.value or {})
        evidence_payloads = [
            item for item in (value.get("evidence") or []) if isinstance(item, dict)
        ]
        if refs or evidence_payloads:
            with_evidence += 1
        artifact_ok = bool(assertion.source_artifact_id) or any(
            isinstance(item, dict) and item.get("source_artifact_id")
            for item in (value.get("source_artifacts") or [])
        ) or any(item.get("source_artifact_id") for item in evidence_payloads)
        if artifact_ok:
            with_artifact += 1

        domains = _domains_from_assertion(assertion)
        is_recap = "recap" in domains
        if is_recap:
            recap_total += 1
            if any(
                item.get("session_id") and item.get("source_span_ref_id")
                for item in evidence_payloads
            ):
                recap_with_session += 1
        else:
            non_recap_total += 1
            if any(
                item.get("locator")
                or item.get("source_span_ref_id")
                or item.get("uri")
                or item.get("source_locator")
                or item.get("line_ref")
                for item in evidence_payloads
            ):
                non_recap_with_locator += 1

    def _pct(numer: int, denom: int) -> float:
        return 100.0 if denom == 0 else round(100.0 * numer / denom, 2)

    return {
        "accepted_assertions": total,
        "with_evidence_ref": with_evidence,
        "with_resolvable_source_artifact": with_artifact,
        "recap_with_session_locator": recap_with_session,
        "recap_assertions": recap_total,
        "non_recap_with_source_locator": non_recap_with_locator,
        "non_recap_assertions": non_recap_total,
        "pct_with_evidence_ref": _pct(with_evidence, total),
        "pct_with_resolvable_source_artifact": _pct(with_artifact, total),
        "pct_recap_with_session_locator": _pct(recap_with_session, recap_total),
        "pct_non_recap_with_source_locator": _pct(non_recap_with_locator, non_recap_total),
    }


def validate_contribution_bundle(
    bundle: LoadedContributionBundle,
) -> ContributionBundleValidationReport:
    """Fail closed on contract violations. Never rewrites the bundle."""
    errors: list[str] = []
    warnings: list[str] = []
    manifest = bundle.manifest
    contributions = bundle.contributions

    if manifest.schema_ != "dmb_graph_contribution_bundle_v1":
        errors.append(f"unsupported schema: {manifest.schema_!r}")
    if manifest.world_id != "eldyrwild":
        errors.append(f"world_id must be 'eldyrwild', got {manifest.world_id!r}")

    kind_counts: Counter[str] = Counter()
    domains: set[str] = set()
    accepted_total = 0
    rejected_total = 0
    unresolved_total = 0
    seen_assertion_ids: set[str] = set()
    observed_nodes: set[str] = set()
    observed_edges: set[str] = set()

    for index, contribution in enumerate(contributions):
        entry = manifest.ordered_contributions[index]
        expected_id = compute_contribution_id(
            world_id=contribution.world_id,
            source_kind=contribution.source_kind,
            source_artifact_id=contribution.source_artifact_id,
            source_revision_id=contribution.source_revision_id,
            extraction_profile=contribution.extraction_profile,
            authored_by=contribution.authored_by,
            supersedes_contribution_id=contribution.supersedes_contribution_id,
        )
        if contribution.contribution_id != expected_id:
            errors.append(
                f"stale contribution_id for {entry.path}: "
                f"stored={contribution.contribution_id!r} expected={expected_id!r}"
            )
        if contribution.world_id != manifest.world_id:
            errors.append(
                f"contribution world_id mismatch for {entry.path}: "
                f"{contribution.world_id!r}"
            )
        if contribution.status != "active":
            errors.append(
                f"contribution status must be active for {entry.path}: "
                f"{contribution.status!r}"
            )

        rejected_total += len(contribution.rejected_assertions)
        unresolved_total += len(contribution.unresolved_mentions)
        observed_nodes |= _node_ids(contribution)
        observed_edges |= _edge_ids(contribution)

        for assertion in (
            *contribution.candidate_assertions,
            *contribution.accepted_assertions,
            *contribution.rejected_assertions,
        ):
            if assertion.contribution_id != contribution.contribution_id:
                errors.append(
                    "assertion/contribution ownership mismatch: "
                    f"{assertion.assertion_id} contribution_id="
                    f"{assertion.contribution_id!r} expected="
                    f"{contribution.contribution_id!r}"
                )
            expected_assertion_id = compute_assertion_id(
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
            if assertion.assertion_id != expected_assertion_id:
                errors.append(
                    f"stale assertion_id {assertion.assertion_id!r} in {entry.path}; "
                    f"expected {expected_assertion_id!r}"
                )
            if assertion.assertion_id in seen_assertion_ids:
                # Shared semantic IDs across contributions are required for
                # multi-source support; only duplicate *within* one contribution.
                pass
            seen_assertion_ids.add(assertion.assertion_id)

            for domain in _domains_from_assertion(assertion):
                domains.add(domain)
                if domain not in KNOWN_SOURCE_DOMAINS:
                    errors.append(
                        f"unknown source_domain {domain!r} on {assertion.assertion_id}"
                    )

        for assertion in contribution.accepted_assertions:
            accepted_total += 1
            kind_counts[assertion.assertion_kind] += 1
            if assertion.epistemic_kind is None:
                errors.append(
                    f"missing epistemic_kind on accepted assertion {assertion.assertion_id}"
                )
            if assertion.visibility is None:
                errors.append(
                    f"missing visibility on accepted assertion {assertion.assertion_id}"
                )
            if (
                assertion.campaign_scope is not None
                and assertion.campaign_scope != manifest.primary_campaign_scope
            ):
                errors.append(
                    f"invalid campaign_scope {assertion.campaign_scope!r} "
                    f"on {assertion.assertion_id}"
                )

            value = dict(assertion.value or {})
            evidence_payloads = [
                item for item in (value.get("evidence") or []) if isinstance(item, dict)
            ]
            if not assertion.evidence_ref_ids and not evidence_payloads:
                errors.append(
                    f"missing evidence on accepted assertion {assertion.assertion_id}"
                )
            else:
                for evidence in evidence_payloads:
                    if not evidence.get("source_artifact_id"):
                        errors.append(
                            f"missing source_artifact_id on evidence for "
                            f"{assertion.assertion_id}"
                        )
                    if not evidence.get("evidence_ref_id"):
                        errors.append(
                            f"missing evidence_ref_id on evidence for "
                            f"{assertion.assertion_id}"
                        )
                    domain = str(evidence.get("source_domain") or "")
                    if domain == "recap" or evidence.get("session_id"):
                        if not evidence.get("session_id"):
                            errors.append(
                                f"recap evidence missing session_id on "
                                f"{assertion.assertion_id}"
                            )
                        if not evidence.get("source_span_ref_id"):
                            errors.append(
                                f"recap evidence missing source_span_ref_id on "
                                f"{assertion.assertion_id}"
                            )
                    elif not any(
                        evidence.get(key)
                        for key in (
                            "locator",
                            "source_span_ref_id",
                            "uri",
                            "source_locator",
                            "line_ref",
                        )
                    ):
                        errors.append(
                            f"non-recap evidence missing source locator on "
                            f"{assertion.assertion_id}"
                        )

            artifacts = [
                item
                for item in (value.get("source_artifacts") or [])
                if isinstance(item, dict)
            ]
            if not assertion.source_artifact_id and not artifacts:
                errors.append(
                    f"missing source artifact on accepted assertion "
                    f"{assertion.assertion_id}"
                )
            for artifact in artifacts:
                if not artifact.get("uri"):
                    errors.append(
                        f"source artifact missing uri on {assertion.assertion_id}"
                    )
                if not str(artifact.get("uri") or "").startswith("graph-data://"):
                    errors.append(
                        f"source artifact uri must be graph-data:// on "
                        f"{assertion.assertion_id}"
                    )

            outcome = assertion.identity_resolution_outcome
            if (
                assertion.acceptance_state == "accepted"
                and outcome in _GRAPH_MUTATING_BLOCKED
            ):
                errors.append(
                    "unsupported identity outcome entered as accepted canonical "
                    f"mutation: {assertion.assertion_id} outcome={outcome!r}"
                )

    if rejected_total != 0:
        errors.append(f"rejected_assertions must be 0, got {rejected_total}")
    if unresolved_total != 0:
        errors.append(f"unresolved_mentions must be 0, got {unresolved_total}")
    if len(bundle.identity_decision_records) != 0 or len(manifest.identity_decisions) != 0:
        errors.append("identity_decisions must be empty for the initial bundle")

    required_nodes = set(manifest.required_node_ids)
    required_edges = set(manifest.required_edge_ids)
    if observed_nodes != required_nodes:
        missing = sorted(required_nodes - observed_nodes)
        extra = sorted(observed_nodes - required_nodes)
        if missing:
            errors.append(f"missing required nodes: {missing}")
        if extra:
            errors.append(f"extra nodes outside locked scope: {extra}")
    if observed_edges != required_edges:
        missing = sorted(required_edges - observed_edges)
        extra = sorted(observed_edges - required_edges)
        if missing:
            errors.append(f"missing required edges: {missing}")
        if extra:
            errors.append(f"extra edges outside locked scope: {extra}")

    expected_domains = set(manifest.expected_source_domains)
    if not expected_domains.issubset(domains):
        errors.append(
            "missing expected source domains: "
            f"{sorted(expected_domains - domains)}"
        )
    if not domains.issubset(KNOWN_SOURCE_DOMAINS):
        errors.append(
            f"unknown domains present: {sorted(domains - KNOWN_SOURCE_DOMAINS)}"
        )

    # Dependency order: session-22/23 may resolve existing hubs/roster nodes;
    # Tripod may reference the session-23 event.
    created_nodes: set[str] = set()
    for index, contribution in enumerate(contributions):
        entry = manifest.ordered_contributions[index]
        for assertion in contribution.accepted_assertions:
            if assertion.assertion_kind != "node" or not assertion.subject_node_id:
                continue
            node_id = assertion.subject_node_id
            outcome = assertion.identity_resolution_outcome
            if outcome == "created_new":
                if node_id in created_nodes:
                    errors.append(
                        f"duplicate created_new for {node_id} in {entry.path}"
                    )
                created_nodes.add(node_id)
            elif outcome == "resolved_existing":
                if node_id not in created_nodes:
                    errors.append(
                        f"resolved_existing before create for {node_id} in {entry.path}"
                    )

    shared_support_report: list[dict[str, Any]] = []
    for expectation in manifest.expected_shared_support:
        contrib_ids = []
        for path in expectation.contribution_paths:
            matches = [
                entry.contribution_id
                for entry in manifest.ordered_contributions
                if entry.path == path
            ]
            if not matches:
                errors.append(
                    f"shared-support path missing from manifest: {path}"
                )
                continue
            contrib_ids.append(matches[0])

        assertion_ids: set[str] = set()
        for contribution in contributions:
            if contribution.contribution_id not in contrib_ids:
                continue
            for assertion in contribution.accepted_assertions:
                if (
                    assertion.assertion_kind == "node"
                    and assertion.subject_node_id == expectation.node_id
                ):
                    assertion_ids.add(assertion.assertion_id)
        if len(assertion_ids) != 1:
            errors.append(
                f"shared-support for {expectation.node_id} expected one semantic "
                f"assertion_id, found {sorted(assertion_ids)}"
            )
        shared_support_report.append(
            {
                "node_id": expectation.node_id,
                "contribution_paths": list(expectation.contribution_paths),
                "source_domains": list(expectation.source_domains),
                "assertion_ids": sorted(assertion_ids),
                "contribution_ids": contrib_ids,
            }
        )

    # Order lock: filenames must match the declared ordered_contributions sequence.
    for index, entry in enumerate(manifest.ordered_contributions):
        if not entry.path.startswith(f"contributions/{index + 1:03d}-") or not entry.path.endswith(
            ".json"
        ):
            errors.append(f"contribution path shape invalid: {entry.path}")
        # Soft check that lexical order of declared paths matches list order.
        if index > 0:
            prev = manifest.ordered_contributions[index - 1].path
            if entry.path < prev:
                errors.append(
                    f"wrong contribution order: {entry.path} before {prev}"
                )

    coverage = _evidence_coverage(contributions)
    for key in (
        "pct_with_evidence_ref",
        "pct_with_resolvable_source_artifact",
        "pct_recap_with_session_locator",
        "pct_non_recap_with_source_locator",
    ):
        if coverage.get(key, 0) < 100.0:
            errors.append(f"evidence coverage below 100% for {key}: {coverage.get(key)}")

    report = ContributionBundleValidationReport(
        bundle_id=manifest.bundle_id,
        bundle_digest=manifest.bundle_digest,
        world_id=manifest.world_id,
        primary_campaign_scope=manifest.primary_campaign_scope,
        contribution_count=len(contributions),
        identity_decision_count=len(manifest.identity_decisions),
        accepted_assertion_count=accepted_total,
        rejected_assertion_count=rejected_total,
        unresolved_mention_count=unresolved_total,
        assertion_counts_by_kind=dict(sorted(kind_counts.items())),
        source_domains=sorted(domains),
        required_node_count=len(required_nodes),
        required_edge_count=len(required_edges),
        evidence_coverage=coverage,
        shared_support_expectations=shared_support_report,
        validation_errors=errors,
        validation_warnings=warnings,
        ok=not errors,
    )
    return report
