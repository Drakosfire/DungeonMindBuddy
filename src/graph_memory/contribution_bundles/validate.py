"""Validate loaded GraphContribution bundles against locked contracts."""

from __future__ import annotations

from collections import Counter
from typing import Any, get_args

from graph_memory.contribution_bundles.models import (
    ContributionBundleValidationReport,
    LoadedContributionBundle,
)
from graph_memory.evidence.source_domain import KNOWN_SOURCE_DOMAINS
from graph_memory.kernel.contribution_models import (
    GraphContribution,
    GraphContributionAssertion,
)
from graph_memory.kernel.contributions import (
    compute_assertion_id,
    compute_contribution_id,
)
from graph_memory.kernel.identity_models import IdentityResolutionOutcome

_GRAPH_MUTATING_BLOCKED = frozenset(
    {"ambiguous", "blocked_collision", "rejected", "provisional_new"}
)
_KNOWN_IDENTITY_OUTCOMES = frozenset(get_args(IdentityResolutionOutcome))
_EXTERNAL_SOURCE_DOMAINS = frozenset({"worldbuilding", "recap"})
_ALLOWED_URI_PREFIXES = ("graph-data://", "repo://corpus/")
_LOCATOR_FIELDS = (
    "locator",
    "source_span_ref_id",
    "uri",
    "source_locator",
    "line_ref",
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


def _artifact_map(assertion: GraphContributionAssertion) -> dict[str, dict[str, Any]]:
    value = dict(assertion.value or {})
    artifacts: dict[str, dict[str, Any]] = {}
    for item in value.get("source_artifacts") or []:
        if isinstance(item, dict) and item.get("source_artifact_id"):
            artifacts[str(item["source_artifact_id"])] = item
    return artifacts


def _evidence_payloads(
    assertion: GraphContributionAssertion,
) -> list[dict[str, Any]]:
    value = dict(assertion.value or {})
    return [item for item in (value.get("evidence") or []) if isinstance(item, dict)]


def _uri_allowed(uri: str, domains: set[str]) -> bool:
    if not any(uri.startswith(prefix) for prefix in _ALLOWED_URI_PREFIXES):
        return False
    if domains & _EXTERNAL_SOURCE_DOMAINS:
        return uri.startswith("repo://corpus/")
    return True


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
        evidence_payloads = _evidence_payloads(assertion)
        artifacts = _artifact_map(assertion)
        embedded_ids = {
            str(item.get("evidence_ref_id"))
            for item in evidence_payloads
            if item.get("evidence_ref_id")
        }
        if refs and set(refs) == embedded_ids and evidence_payloads:
            with_evidence += 1

        artifact_ids = set(artifacts)
        evidence_artifacts = {
            str(item.get("source_artifact_id"))
            for item in evidence_payloads
            if item.get("source_artifact_id")
        }
        if (
            assertion.source_artifact_id
            and assertion.source_artifact_id in artifact_ids
            and evidence_artifacts
            and evidence_artifacts.issubset(artifact_ids)
        ):
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
            if any(any(item.get(field) for field in _LOCATOR_FIELDS) for item in evidence_payloads):
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
        "pct_non_recap_with_source_locator": _pct(
            non_recap_with_locator, non_recap_total
        ),
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
    if not manifest.bundle_digest.strip():
        errors.append("bundle_digest must be non-empty")

    kind_counts: Counter[str] = Counter()
    domains: set[str] = set()
    accepted_total = 0
    rejected_total = 0
    unresolved_total = 0
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

        seen_in_contribution: set[str] = set()
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
            if assertion.assertion_id in seen_in_contribution:
                errors.append(
                    f"duplicate assertion_id {assertion.assertion_id!r} within "
                    f"{entry.path}"
                )
            seen_in_contribution.add(assertion.assertion_id)

            for domain in _domains_from_assertion(assertion):
                domains.add(domain)
                if domain not in KNOWN_SOURCE_DOMAINS:
                    errors.append(
                        f"unknown source_domain {domain!r} on {assertion.assertion_id}"
                    )

        for assertion in contribution.accepted_assertions:
            accepted_total += 1
            kind_counts[assertion.assertion_kind] += 1
            if assertion.acceptance_state != "accepted":
                errors.append(
                    "accepted_assertions entry must have acceptance_state='accepted': "
                    f"{assertion.assertion_id} has {assertion.acceptance_state!r}"
                )
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

            outcome = assertion.identity_resolution_outcome
            if outcome is None:
                errors.append(
                    f"missing identity_resolution_outcome on {assertion.assertion_id}"
                )
            elif outcome not in _KNOWN_IDENTITY_OUTCOMES:
                errors.append(
                    f"unknown identity_resolution_outcome {outcome!r} on "
                    f"{assertion.assertion_id}"
                )
            elif (
                assertion.acceptance_state == "accepted"
                and outcome in _GRAPH_MUTATING_BLOCKED
            ):
                errors.append(
                    "unsupported identity outcome entered as accepted canonical "
                    f"mutation: {assertion.assertion_id} outcome={outcome!r}"
                )

            artifacts = _artifact_map(assertion)
            evidence_payloads = _evidence_payloads(assertion)
            top_level_refs = list(assertion.evidence_ref_ids)
            embedded_refs = [
                str(item.get("evidence_ref_id"))
                for item in evidence_payloads
                if item.get("evidence_ref_id")
            ]

            if not top_level_refs:
                errors.append(
                    f"missing evidence_ref_ids on accepted assertion "
                    f"{assertion.assertion_id}"
                )
            if not evidence_payloads:
                errors.append(
                    f"missing embedded evidence on accepted assertion "
                    f"{assertion.assertion_id}"
                )
            if top_level_refs and set(top_level_refs) != set(embedded_refs):
                errors.append(
                    f"evidence_ref_ids do not match embedded evidence on "
                    f"{assertion.assertion_id}: top={sorted(set(top_level_refs))} "
                    f"embedded={sorted(set(embedded_refs))}"
                )

            if not assertion.source_artifact_id:
                errors.append(
                    f"missing source_artifact_id on accepted assertion "
                    f"{assertion.assertion_id}"
                )
            elif assertion.source_artifact_id not in artifacts:
                errors.append(
                    f"assertion source_artifact_id "
                    f"{assertion.source_artifact_id!r} not present in embedded "
                    f"source_artifacts on {assertion.assertion_id}"
                )
            if not artifacts:
                errors.append(
                    f"missing embedded source_artifacts on accepted assertion "
                    f"{assertion.assertion_id}"
                )

            assertion_domains = _domains_from_assertion(assertion)
            for artifact_id, artifact in artifacts.items():
                uri = str(artifact.get("uri") or "")
                if not uri:
                    errors.append(
                        f"source artifact {artifact_id!r} missing uri on "
                        f"{assertion.assertion_id}"
                    )
                elif not _uri_allowed(uri, assertion_domains):
                    errors.append(
                        f"source artifact {artifact_id!r} has disallowed uri "
                        f"{uri!r} for domains {sorted(assertion_domains)} on "
                        f"{assertion.assertion_id}"
                    )

            for evidence in evidence_payloads:
                evidence_id = str(evidence.get("evidence_ref_id") or "")
                artifact_id = str(evidence.get("source_artifact_id") or "")
                if not evidence_id:
                    errors.append(
                        f"missing evidence_ref_id on evidence for "
                        f"{assertion.assertion_id}"
                    )
                if not artifact_id:
                    errors.append(
                        f"missing source_artifact_id on evidence for "
                        f"{assertion.assertion_id}"
                    )
                elif artifact_id not in artifacts:
                    errors.append(
                        f"evidence {evidence_id!r} points to nonexistent embedded "
                        f"source artifact {artifact_id!r} on {assertion.assertion_id}"
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
                elif not any(evidence.get(field) for field in _LOCATOR_FIELDS):
                    errors.append(
                        f"non-recap evidence missing source locator on "
                        f"{assertion.assertion_id}"
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
    if domains != expected_domains:
        errors.append(
            "source domains must exactly match expected_source_domains: "
            f"observed={sorted(domains)} expected={sorted(expected_domains)}"
        )
    if not domains.issubset(KNOWN_SOURCE_DOMAINS):
        errors.append(
            f"unknown domains present: {sorted(domains - KNOWN_SOURCE_DOMAINS)}"
        )

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
    contrib_by_path = {
        entry.path: contributions[index]
        for index, entry in enumerate(manifest.ordered_contributions)
    }
    for expectation in manifest.expected_shared_support:
        contrib_ids: list[str] = []
        assertion_ids: set[str] = set()
        observed_support_domains: set[str] = set()
        for path in expectation.contribution_paths:
            contribution = contrib_by_path.get(path)
            if contribution is None:
                errors.append(f"shared-support path missing from manifest: {path}")
                continue
            contrib_ids.append(contribution.contribution_id)
            matching = [
                assertion
                for assertion in contribution.accepted_assertions
                if assertion.assertion_kind == "node"
                and assertion.subject_node_id == expectation.node_id
            ]
            if not matching:
                errors.append(
                    f"shared-support contributor {path} missing node assertion for "
                    f"{expectation.node_id}"
                )
                continue
            for assertion in matching:
                assertion_ids.add(assertion.assertion_id)
                observed_support_domains |= _domains_from_assertion(assertion)
        if len(assertion_ids) != 1:
            errors.append(
                f"shared-support for {expectation.node_id} expected one semantic "
                f"assertion_id, found {sorted(assertion_ids)}"
            )
        expected_support_domains = set(expectation.source_domains)
        if observed_support_domains != expected_support_domains:
            errors.append(
                f"shared-support domains mismatch for {expectation.node_id}: "
                f"observed={sorted(observed_support_domains)} "
                f"expected={sorted(expected_support_domains)}"
            )
        shared_support_report.append(
            {
                "node_id": expectation.node_id,
                "contribution_paths": list(expectation.contribution_paths),
                "source_domains": list(expectation.source_domains),
                "observed_source_domains": sorted(observed_support_domains),
                "assertion_ids": sorted(assertion_ids),
                "contribution_ids": contrib_ids,
            }
        )

    for index, entry in enumerate(manifest.ordered_contributions):
        if not entry.path.startswith(f"contributions/{index + 1:03d}-") or not entry.path.endswith(
            ".json"
        ):
            errors.append(f"contribution path shape invalid: {entry.path}")
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

    return ContributionBundleValidationReport(
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
