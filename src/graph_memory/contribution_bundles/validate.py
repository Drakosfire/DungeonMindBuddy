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
_CORPUS_IMPORT_KINDS = frozenset({"manual_import"})
_AUTHORED_KINDS = frozenset({"graph_review_authored_assertion"})
_ALLOWED_URI_PREFIXES = ("graph-data://", "repo://corpus/")
_SHA256_HEX_LEN = 64
_LOCATOR_FIELDS = (
    "locator",
    "source_span_ref_id",
    "uri",
    "source_locator",
    "line_ref",
)


def _is_sha256_hex(value: str) -> bool:
    if len(value) != _SHA256_HEX_LEN:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _assertion_provenance_domains(assertion: GraphContributionAssertion) -> set[str]:
    """Domains declared on the assertion value (not evidence/artifact spill)."""
    value = dict(assertion.value or {})
    domains: set[str] = set()
    for domain in value.get("source_domains") or []:
        domains.add(str(domain))
    if value.get("source_domain"):
        domains.add(str(value["source_domain"]))
    return domains


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


def _uri_allowed(uri: str, domains: set[str], *, source_kind: str) -> bool:
    if not any(uri.startswith(prefix) for prefix in _ALLOWED_URI_PREFIXES):
        return False
    if source_kind in _AUTHORED_KINDS:
        return uri.startswith("graph-data://")
    if source_kind in _CORPUS_IMPORT_KINDS or domains & _EXTERNAL_SOURCE_DOMAINS:
        return uri.startswith("repo://corpus/")
    return True


def _contribution_has_recap(contribution: GraphContribution) -> bool:
    for assertion in contribution.accepted_assertions:
        if "recap" in _domains_from_assertion(assertion):
            return True
    return False


def _temporal_session_id(assertion: GraphContributionAssertion) -> str | None:
    temporal = assertion.temporal_scope
    if not isinstance(temporal, dict):
        return None
    session_id = temporal.get("session_id")
    return str(session_id) if session_id else None


def _validate_contribution_campaign_scope(
    contribution: GraphContribution,
    entry_path: str,
    primary_campaign: str,
    errors: list[str],
) -> None:
    """Recap/authored contributions must carry the primary campaign; hubs may be null."""
    requires_campaign = (
        contribution.source_kind in _AUTHORED_KINDS
        or _contribution_has_recap(contribution)
    )
    scope = contribution.campaign_scope
    if requires_campaign:
        if scope != primary_campaign:
            errors.append(
                f"contribution campaign_scope must equal primary "
                f"{primary_campaign!r} for {entry_path}, got {scope!r}"
            )
    elif scope is not None:
        # World-global hubs keep null; any other value must still match primary.
        if scope != primary_campaign:
            errors.append(
                f"contribution campaign_scope {scope!r} disagrees with primary "
                f"{primary_campaign!r} for {entry_path}"
            )


def _validate_scope_chronology(
    assertion: GraphContributionAssertion,
    artifacts: dict[str, dict[str, Any]],
    evidence_payloads: list[dict[str, Any]],
    *,
    primary_campaign: str,
    focus_sessions: set[str],
    observed_recap_sessions: set[str],
    errors: list[str],
) -> None:
    """Fail closed when campaign/session provenance disagrees."""
    assertion_id = assertion.assertion_id
    provenance_domains = _assertion_provenance_domains(assertion)
    is_recap = "recap" in provenance_domains or "recap" in _domains_from_assertion(
        assertion
    )
    temporal_session = _temporal_session_id(assertion)

    for artifact_id, artifact in artifacts.items():
        campaign_id = artifact.get("campaign_id")
        if campaign_id is None or str(campaign_id).strip() == "":
            errors.append(
                f"source artifact {artifact_id!r} missing campaign_id on "
                f"{assertion_id}"
            )
        elif str(campaign_id) != primary_campaign:
            errors.append(
                f"source artifact {artifact_id!r} campaign_id {campaign_id!r} "
                f"disagrees with primary {primary_campaign!r} on {assertion_id}"
            )

    recap_evidence_sessions: set[str] = set()
    for evidence in evidence_payloads:
        evidence_domain = str(evidence.get("source_domain") or "")
        evidence_session = evidence.get("session_id")
        artifact_id = str(evidence.get("source_artifact_id") or "")
        artifact = artifacts.get(artifact_id, {})
        artifact_session = artifact.get("session_id")

        if evidence_domain == "recap" or evidence_session:
            if not evidence_session:
                continue  # missing session already reported elsewhere
            session = str(evidence_session)
            recap_evidence_sessions.add(session)
            observed_recap_sessions.add(session)
            if session not in focus_sessions:
                errors.append(
                    f"recap session_id {session!r} outside manifest.focus_sessions "
                    f"on {assertion_id}"
                )
            if artifact_session is None or str(artifact_session).strip() == "":
                errors.append(
                    f"recap artifact {artifact_id!r} missing session_id on "
                    f"{assertion_id}"
                )
            elif str(artifact_session) != session:
                errors.append(
                    f"evidence/artifact session mismatch on {assertion_id}: "
                    f"evidence={session!r} artifact={artifact_session!r}"
                )

    if is_recap and temporal_session:
        if not recap_evidence_sessions:
            errors.append(
                f"temporal_scope.session_id {temporal_session!r} without recap "
                f"evidence session on {assertion_id}"
            )
        elif recap_evidence_sessions != {temporal_session}:
            errors.append(
                f"temporal/evidence session mismatch on {assertion_id}: "
                f"temporal={temporal_session!r} "
                f"evidence={sorted(recap_evidence_sessions)}"
            )
        if temporal_session not in focus_sessions:
            errors.append(
                f"temporal_scope.session_id {temporal_session!r} outside "
                f"manifest.focus_sessions on {assertion_id}"
            )

    if assertion.assertion_kind == "edge":
        value = dict(assertion.value or {})
        edge_sessions = value.get("session_ids")
        if edge_sessions is not None:
            normalized = {str(item) for item in edge_sessions}
            if temporal_session is None:
                errors.append(
                    f"edge session_ids present without temporal_scope.session_id "
                    f"on {assertion_id}"
                )
            elif normalized != {temporal_session}:
                errors.append(
                    f"edge session_ids/temporal mismatch on {assertion_id}: "
                    f"session_ids={sorted(normalized)} "
                    f"temporal={temporal_session!r}"
                )
        elif is_recap and temporal_session:
            errors.append(
                f"recap edge missing session_ids for temporal "
                f"{temporal_session!r} on {assertion_id}"
            )


def _validate_authority_model(
    contribution: GraphContribution,
    entry_path: str,
    errors: list[str],
) -> None:
    kind = contribution.source_kind
    author = (contribution.authored_by or "").strip()
    if kind in _CORPUS_IMPORT_KINDS:
        if author:
            errors.append(
                f"manual_import must not set authored_by for {entry_path}: {author!r}"
            )
    elif kind in _AUTHORED_KINDS:
        if not author:
            errors.append(
                f"authored contribution missing authored_by for {entry_path}"
            )
    else:
        errors.append(
            f"unsupported source_kind {kind!r} for {entry_path}; "
            f"expected manual_import or authored kinds"
        )


def _validate_provenance_coherence(
    contribution: GraphContribution,
    assertion: GraphContributionAssertion,
    artifacts: dict[str, dict[str, Any]],
    evidence_payloads: list[dict[str, Any]],
    errors: list[str],
) -> None:
    assertion_id = assertion.assertion_id
    kind = contribution.source_kind
    provenance_domains = _assertion_provenance_domains(assertion)
    if not provenance_domains:
        errors.append(f"missing assertion provenance domain on {assertion_id}")

    if assertion.source_artifact_id != contribution.source_artifact_id:
        errors.append(
            f"assertion source_artifact_id {assertion.source_artifact_id!r} "
            f"differs from contribution source_artifact_id "
            f"{contribution.source_artifact_id!r} on {assertion_id}"
        )
    if assertion.source_revision_id != contribution.source_revision_id:
        errors.append(
            f"assertion source_revision_id {assertion.source_revision_id!r} "
            f"differs from contribution source_revision_id "
            f"{contribution.source_revision_id!r} on {assertion_id}"
        )

    if kind in _CORPUS_IMPORT_KINDS:
        if len(artifacts) != 1:
            errors.append(
                f"manual_import assertion must embed exactly one source artifact "
                f"on {assertion_id}, found {sorted(artifacts)}"
            )
        primary = artifacts.get(str(contribution.source_artifact_id or ""))
        if primary is None:
            errors.append(
                f"contribution source_artifact_id "
                f"{contribution.source_artifact_id!r} missing from embedded "
                f"source_artifacts on {assertion_id}"
            )
        else:
            content_sha = str(primary.get("content_sha256") or "")
            if not content_sha:
                errors.append(
                    f"missing content_sha256 on embedded source artifact "
                    f"{contribution.source_artifact_id!r} for {assertion_id}"
                )
            elif not _is_sha256_hex(content_sha):
                errors.append(
                    f"malformed content_sha256 on embedded source artifact "
                    f"{contribution.source_artifact_id!r} for {assertion_id}"
                )
            expected_revision = f"sha256:{content_sha}" if content_sha else ""
            if content_sha and contribution.source_revision_id != expected_revision:
                errors.append(
                    f"source_revision_id {contribution.source_revision_id!r} "
                    f"does not match content_sha256 on {assertion_id}"
                )
            if assertion.source_revision_id and content_sha:
                if assertion.source_revision_id != expected_revision:
                    errors.append(
                        f"assertion source_revision_id "
                        f"{assertion.source_revision_id!r} does not match "
                        f"content_sha256 on {assertion_id}"
                    )

    for artifact_id, artifact in artifacts.items():
        uri = str(artifact.get("uri") or "")
        artifact_domain = str(artifact.get("source_domain") or "")
        if not artifact_domain:
            errors.append(
                f"source artifact {artifact_id!r} missing source_domain on "
                f"{assertion_id}"
            )
        elif provenance_domains and artifact_domain not in provenance_domains:
            errors.append(
                f"source artifact {artifact_id!r} source_domain "
                f"{artifact_domain!r} disagrees with assertion domains "
                f"{sorted(provenance_domains)} on {assertion_id}"
            )
        if not uri:
            errors.append(
                f"source artifact {artifact_id!r} missing uri on {assertion_id}"
            )
        elif not _uri_allowed(uri, provenance_domains or {artifact_domain}, source_kind=kind):
            errors.append(
                f"source artifact {artifact_id!r} has disallowed uri {uri!r} "
                f"for source_kind={kind!r} domains={sorted(provenance_domains)} "
                f"on {assertion_id}"
            )
        if kind in _AUTHORED_KINDS and not uri.startswith("graph-data://"):
            errors.append(
                f"authored artifact {artifact_id!r} must use graph-data:// uri "
                f"on {assertion_id}"
            )
        if kind in _CORPUS_IMPORT_KINDS and not uri.startswith("repo://corpus/"):
            errors.append(
                f"manual_import artifact {artifact_id!r} must use repo://corpus/ "
                f"uri on {assertion_id}"
            )

    for evidence in evidence_payloads:
        evidence_id = str(evidence.get("evidence_ref_id") or "")
        artifact_id = str(evidence.get("source_artifact_id") or "")
        evidence_domain = str(evidence.get("source_domain") or "")
        if artifact_id and artifact_id not in artifacts:
            continue  # dangling artifact already reported elsewhere
        artifact = artifacts.get(artifact_id, {})
        artifact_domain = str(artifact.get("source_domain") or "")
        if not evidence_domain:
            errors.append(
                f"missing evidence source_domain on {assertion_id} "
                f"(evidence={evidence_id!r})"
            )
            continue
        if artifact_domain and evidence_domain != artifact_domain:
            errors.append(
                f"evidence/artifact source_domain mismatch on {assertion_id}: "
                f"evidence={evidence_domain!r} artifact={artifact_domain!r}"
            )
        if provenance_domains and evidence_domain not in provenance_domains:
            errors.append(
                f"evidence source_domain {evidence_domain!r} disagrees with "
                f"assertion domains {sorted(provenance_domains)} on {assertion_id}"
            )
        if kind in _CORPUS_IMPORT_KINDS:
            if artifact_id != contribution.source_artifact_id:
                errors.append(
                    f"evidence source_artifact_id {artifact_id!r} differs from "
                    f"contribution source_artifact_id "
                    f"{contribution.source_artifact_id!r} on {assertion_id}"
                )


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
    observed_recap_sessions: set[str] = set()
    focus_sessions = set(manifest.focus_sessions)
    primary_campaign = manifest.primary_campaign_scope

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
        _validate_authority_model(contribution, entry.path, errors)
        _validate_contribution_campaign_scope(
            contribution,
            entry.path,
            manifest.primary_campaign_scope,
            errors,
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

            _validate_provenance_coherence(
                contribution,
                assertion,
                artifacts,
                evidence_payloads,
                errors,
            )
            _validate_scope_chronology(
                assertion,
                artifacts,
                evidence_payloads,
                primary_campaign=primary_campaign,
                focus_sessions=focus_sessions,
                observed_recap_sessions=observed_recap_sessions,
                errors=errors,
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
    if observed_recap_sessions != focus_sessions:
        errors.append(
            "recap session set must equal manifest.focus_sessions: "
            f"observed={sorted(observed_recap_sessions)} "
            f"expected={sorted(focus_sessions)}"
        )
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
