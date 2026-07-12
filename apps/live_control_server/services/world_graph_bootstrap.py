"""Approved Eldyrwild bootstrap activation service (PR006D2)."""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

from pydantic import ValidationError

import graph_memory.kernel as kernel
from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.models.world_graph_bootstrap import (
    BootstrapAttributeReview,
    BootstrapContributionReview,
    BootstrapDiagnostic,
    BootstrapEvidenceSummary,
    BootstrapNodeReview,
    BootstrapReceipt,
    BootstrapRelationshipReview,
    BootstrapReview,
    BootstrapReviewSummary,
    BootstrapSourceArtifact,
    BootstrapState,
    BootstrapTrustBoundary,
    WorldGraphBootstrapConfirmRequest,
    WorldGraphBootstrapConfirmResponse,
    WorldGraphBootstrapEffects,
    WorldGraphBootstrapErrorResponse,
    WorldGraphBootstrapPrepareRequest,
    WorldGraphBootstrapPrepareResponse,
    WorldGraphBootstrapStatusResponse,
    CONTRACT_SCHEMA,
)
from graph_memory.contribution_bundles import (
    LoadedContributionBundle,
    load_contribution_bundle,
    validate_contribution_bundle,
)
from graph_memory.contribution_bundles.models import ContributionBundleValidationReport
from graph_memory.kernel.contribution_models import GraphContributionAssertion
from graph_memory.kernel.world_initialization_models import (
    WorldInitializationError,
    WorldInitializationPlan,
)
from graph_memory.world_supergraph.errors import WorldGraphNotFoundError

CONFIRM_TOKEN_KIND = "dmb_world_graph_bootstrap_confirm_v1"

APPROVED_BUNDLE_ID = "eldyrwild-longmont-c2-initial-v1"
APPROVED_BUNDLE_DIGEST = (
    "c8eb7e6ca7e735c40822cb1e6835f9949f2cd915b57f5704e7b4daeb72cf2fca"
)
APPROVED_BUNDLE_MERGE_SHA = "f69c69f271c427209860d902636347b70fea5920"
APPROVED_BUNDLE_RELPATH = (
    "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)
APPROVED_WORLD_ID = "eldyrwild"
APPROVED_CAMPAIGN_ID = "longmont-c2"
APPROVED_FOCUS_SESSION_ID = "session-23"
EXPECTED_FOCUS_SESSIONS = frozenset({"session-22", "session-23"})
EXPECTED_SOURCE_DOMAINS = frozenset(
    {"manual_seed", "recap", "statblock", "worldbuilding"}
)
FORBIDDEN_GRAPH_IDS = frozenset(
    {
        "sentinel:technical-alpha",
        "sentinel:technical-beta",
        "loc_mirathorn",
        "pc_caelynn",
        "event_session_23_mireward_gate",
    }
)

NO_MUTATION_GUARANTEES_PREPARE = [
    "Production World Supergraph state was not written.",
    "Production graph head was not created or advanced.",
    "The approved contribution bundle was not modified.",
    "Corpus sources were not modified.",
    "Preview or ingest-run artifacts were not modified.",
]
NO_MUTATION_GUARANTEES_CONFIRM = [
    "The approved contribution bundle was not modified.",
    "Corpus sources were not modified.",
    "Preview or ingest-run artifacts were not modified.",
]
CONFIRM_PUBLICATION_STATEMENT = (
    "Published the approved initialization through the PR006D1 Kernel operation."
)
CONFIRM_IDEMPOTENT_STATEMENTS = {
    "active": (
        "No new revision was published; the existing initialization matched the approved plan."
    ),
    "active_head_advanced": (
        "No new revision was published; the current head descends from the approved initialization."
    ),
}
TRUST_BOUNDARY_SERVICE_IDENTITY = [
    "The fixed Eldyrwild bootstrap service identity and endpoint contract.",
]
TRUST_BOUNDARY_CERTIFIED = [
    "The checked-in PR006C bundle checksum and manifest contract.",
    "The exact six ordered GraphContribution records.",
    "The content-bound PR006D1 initialization plan.",
    "The review projection derived from the certified bundle.",
]
TRUST_BOUNDARY_PUBLISHED = [
    "The Kernel receipt and reconstruction/integrity proof.",
]
TRUST_BOUNDARY_INVALID = [
    "The bundle contents, review projection, and content-bound initialization plan.",
    "Any production publication, receipt, or reconstruction/integrity proof.",
]
TRUST_BOUNDARY_NON_CLAIMS = [
    "No /ingest UI is delivered by PR006D2.",
    "No Projection Engine is delivered by PR006D2.",
    "No Plan or Play graph consumption is delivered by PR006D2.",
    "No arbitrary graph editing is delivered by PR006D2.",
]


class WorldGraphBootstrapError(ValueError):
    """Stable, safe service error for API and CLI boundaries."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int,
        bootstrap_state: BootstrapState = "error",
        diagnostics: list[BootstrapDiagnostic] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.bootstrap_state = bootstrap_state
        self.diagnostics = list(diagnostics or [])

    def response(self) -> WorldGraphBootstrapErrorResponse:
        return WorldGraphBootstrapErrorResponse(
            code=self.code,
            message=str(self),
            status_code=self.status_code,
            bootstrap_state=self.bootstrap_state,
            diagnostics=self.diagnostics,
        )


@dataclass(frozen=True)
class _CertifiedBundle:
    bundle: LoadedContributionBundle
    report: ContributionBundleValidationReport
    plan: WorldInitializationPlan
    review: BootstrapReview
    expected_counts: dict[str, int]


def _diagnostic(
    code: str,
    message: str,
    *,
    severity: str = "error",
) -> BootstrapDiagnostic:
    return BootstrapDiagnostic(code=code, message=message, severity=severity)


def _stable_digest(payload: object) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _approved_bundle_path() -> Path:
    return repo_root() / APPROVED_BUNDLE_RELPATH


def _resolved_root(root: Path | None) -> Path:
    return (root if root is not None else world_graph_root()).resolve()


def _fixed_attestation() -> kernel.WorldInitializationApprovalAttestation:
    return kernel.WorldInitializationApprovalAttestation(
        bundle_id=APPROVED_BUNDLE_ID,
        bundle_digest=APPROVED_BUNDLE_DIGEST,
        approved_bundle_merge_sha=APPROVED_BUNDLE_MERGE_SHA,
    )


def _classification_for_kinds(kinds: set[str]) -> str:
    if kinds == {"manual_import"}:
        return "sourceDerived"
    if kinds == {"graph_review_authored_assertion"}:
        return "gmAuthored"
    return "mixed"


def _edge_id(assertion: GraphContributionAssertion) -> str | None:
    if assertion.assertion_kind != "edge":
        return None
    value = dict(assertion.value)
    explicit = value.get("edge_id")
    if explicit:
        return str(explicit)
    source = assertion.subject_node_id or value.get("source_node_id")
    target = assertion.target_node_id or value.get("target_node_id")
    predicate = assertion.predicate or value.get("predicate")
    if source and target and predicate:
        return f"edge:{source}:{predicate}:{target}"
    return None


def _domains(assertion: GraphContributionAssertion) -> set[str]:
    value = dict(assertion.value)
    result = {str(item) for item in value.get("source_domains") or []}
    if value.get("source_domain"):
        result.add(str(value["source_domain"]))
    for item in value.get("evidence") or []:
        if isinstance(item, dict) and item.get("source_domain"):
            result.add(str(item["source_domain"]))
    return result


def _evidence_summaries(
    assertion: GraphContributionAssertion,
) -> list[BootstrapEvidenceSummary]:
    result: dict[str, BootstrapEvidenceSummary] = {}
    for item in dict(assertion.value).get("evidence") or []:
        if not isinstance(item, dict) or not item.get("evidence_ref_id"):
            continue
        source_domain = str(item.get("source_domain") or "")
        result[str(item["evidence_ref_id"])] = BootstrapEvidenceSummary(
            evidence_ref_id=str(item["evidence_ref_id"]),
            source_artifact_id=str(item.get("source_artifact_id") or ""),
            source_domain=source_domain,
            session_id=(
                str(item["session_id"]) if item.get("session_id") is not None else None
            ),
            locator=str(item["locator"]) if item.get("locator") is not None else None,
            source_span_ref_id=(
                str(item["source_span_ref_id"])
                if item.get("source_span_ref_id") is not None
                else None
            ),
            locator_status="unverified",
        )
    return [result[key] for key in sorted(result)]


def _build_review(bundle: LoadedContributionBundle) -> BootstrapReview:
    contributions = bundle.contributions
    contribution_reviews: list[BootstrapContributionReview] = []
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}
    attributes: list[BootstrapAttributeReview] = []
    sources: dict[str, BootstrapSourceArtifact] = {}
    evidence: dict[str, BootstrapEvidenceSummary] = {}

    for contribution in contributions:
        node_ids: set[str] = set()
        edge_ids: set[str] = set()
        attribute_ids: list[str] = []
        for assertion in contribution.accepted_assertions:
            for item in _evidence_summaries(assertion):
                evidence[item.evidence_ref_id] = item
            for raw_artifact in dict(assertion.value).get("source_artifacts") or []:
                if not isinstance(raw_artifact, dict):
                    continue
                artifact_id = str(raw_artifact.get("source_artifact_id") or "")
                if not artifact_id:
                    continue
                sources[artifact_id] = BootstrapSourceArtifact(
                    source_artifact_id=artifact_id,
                    source_domain=str(raw_artifact.get("source_domain") or ""),
                    uri=str(raw_artifact.get("uri") or ""),
                    campaign_id=str(raw_artifact.get("campaign_id") or ""),
                    session_id=(
                        str(raw_artifact["session_id"])
                        if raw_artifact.get("session_id") is not None
                        else None
                    ),
                    classification=(
                        "gmAuthored"
                        if contribution.source_kind
                        == "graph_review_authored_assertion"
                        else "sourceDerived"
                    ),
                )

            domains = _domains(assertion)
            assertion_evidence = _evidence_summaries(assertion)
            if assertion.assertion_kind == "node" and assertion.subject_node_id:
                node_id = assertion.subject_node_id
                node_ids.add(node_id)
                value = dict(assertion.value)
                current = nodes.setdefault(
                    node_id,
                    {
                        "label": assertion.label or str(value.get("label") or node_id),
                        "kind": str(value.get("kind") or "unknown"),
                        "role": str(value.get("role") or value.get("kind") or "unknown"),
                        "aliases": list(value.get("aliases") or []),
                        "source_domains": set(),
                        "contribution_ids": set(),
                        "evidence": {},
                        "kinds": set(),
                    },
                )
                current["source_domains"].update(domains)
                current["contribution_ids"].add(contribution.contribution_id)
                current["kinds"].add(contribution.source_kind)
                current["aliases"] = sorted(
                    set(current["aliases"]) | set(value.get("aliases") or [])
                )
                for item in assertion_evidence:
                    current["evidence"][item.evidence_ref_id] = item
            elif assertion.assertion_kind == "edge":
                edge_id = _edge_id(assertion)
                if edge_id is None:
                    continue
                edge_ids.add(edge_id)
                value = dict(assertion.value)
                current = edges.setdefault(
                    edge_id,
                    {
                        "source_node_id": assertion.subject_node_id
                        or str(value.get("source_node_id") or ""),
                        "target_node_id": assertion.target_node_id
                        or str(value.get("target_node_id") or ""),
                        "predicate": assertion.predicate
                        or str(value.get("predicate") or ""),
                        "label": assertion.label
                        or str(value.get("label") or value.get("predicate") or ""),
                        "session_ids": set(),
                        "source_domains": set(),
                        "contribution_ids": set(),
                        "evidence": {},
                        "kinds": set(),
                    },
                )
                current["session_ids"].update(
                    str(item) for item in value.get("session_ids") or []
                )
                current["source_domains"].update(domains)
                current["contribution_ids"].add(contribution.contribution_id)
                current["kinds"].add(contribution.source_kind)
                for item in assertion_evidence:
                    current["evidence"][item.evidence_ref_id] = item
            elif assertion.assertion_kind == "attribute":
                value = dict(assertion.value)
                attribute_ids.append(assertion.assertion_id)
                attributes.append(
                    BootstrapAttributeReview(
                        assertion_id=assertion.assertion_id,
                        subject_node_id=assertion.subject_node_id or "",
                        attribute=str(
                            value.get("attribute")
                            or assertion.predicate
                            or assertion.label
                            or ""
                        ),
                        text=str(value.get("text") or ""),
                        source_domains=sorted(domains),
                        contribution_id=contribution.contribution_id,
                        evidence=assertion_evidence,
                        classification=(
                            "gmAuthored"
                            if contribution.source_kind
                            == "graph_review_authored_assertion"
                            else "sourceDerived"
                        ),
                    )
                )

        contribution_reviews.append(
            BootstrapContributionReview(
                contribution_id=contribution.contribution_id,
                source_kind=contribution.source_kind,
                classification=(
                    "gmAuthored"
                    if contribution.source_kind == "graph_review_authored_assertion"
                    else "sourceDerived"
                ),
                authored_by=contribution.authored_by,
                source_artifact_id=contribution.source_artifact_id,
                source_revision_id=contribution.source_revision_id,
                accepted_assertion_count=len(contribution.accepted_assertions),
                node_ids=sorted(node_ids),
                edge_ids=sorted(edge_ids),
                attribute_assertion_ids=sorted(attribute_ids),
            )
        )

    node_reviews = [
        BootstrapNodeReview(
            node_id=node_id,
            label=data["label"],
            kind=data["kind"],
            role=data["role"],
            aliases=sorted(data["aliases"]),
            source_domains=sorted(data["source_domains"]),
            contribution_ids=sorted(data["contribution_ids"]),
            evidence=[data["evidence"][key] for key in sorted(data["evidence"])],
            classification=_classification_for_kinds(
                {
                    "manual_import"
                    if kind == "manual_import"
                    else "graph_review_authored_assertion"
                    for kind in data["kinds"]
                }
            ),
        )
        for node_id, data in sorted(nodes.items())
    ]
    relationship_reviews = [
        BootstrapRelationshipReview(
            edge_id=edge_id,
            source_node_id=data["source_node_id"],
            target_node_id=data["target_node_id"],
            predicate=data["predicate"],
            label=data["label"],
            session_ids=sorted(data["session_ids"]),
            source_domains=sorted(data["source_domains"]),
            contribution_ids=sorted(data["contribution_ids"]),
            evidence=[data["evidence"][key] for key in sorted(data["evidence"])],
            classification=_classification_for_kinds(
                {
                    "manual_import"
                    if kind == "manual_import"
                    else "graph_review_authored_assertion"
                    for kind in data["kinds"]
                }
            ),
        )
        for edge_id, data in sorted(edges.items())
    ]
    accepted_assertions = [
        assertion
        for contribution in contributions
        for assertion in contribution.accepted_assertions
    ]
    summary = BootstrapReviewSummary(
        contribution_count=len(contributions),
        node_count=len(node_reviews),
        relationship_count=len(relationship_reviews),
        attribute_count=len(attributes),
        accepted_assertion_count=len(accepted_assertions),
        support_count=len({item.assertion_id for item in accepted_assertions}),
        evidence_count=len(evidence),
        source_artifact_count=len(sources),
        source_domains=sorted(
            {
                domain
                for assertion in accepted_assertions
                for domain in _domains(assertion)
            }
        ),
        focus_sessions=list(bundle.manifest.focus_sessions),
    )
    return BootstrapReview(
        summary=summary,
        contributions=contribution_reviews,
        nodes=node_reviews,
        relationships=relationship_reviews,
        attributes=sorted(attributes, key=lambda item: item.assertion_id),
        sources=[sources[key] for key in sorted(sources)],
        evidence=[evidence[key] for key in sorted(evidence)],
        trust_boundary=[
            *bundle.manifest.non_claims,
            *TRUST_BOUNDARY_NON_CLAIMS,
        ],
    )


def _build_plan(bundle: LoadedContributionBundle) -> WorldInitializationPlan:
    return kernel.WorldInitializationPlan(
        schema="dmb_world_initialization_plan_v1",
        world_id=APPROVED_WORLD_ID,
        campaign_id=APPROVED_CAMPAIGN_ID,
        focus_session_id=APPROVED_FOCUS_SESSION_ID,
        ordered_contributions=[
            kernel.WorldInitializationContribution(
                contribution_id=contribution.contribution_id,
                payload_sha256=kernel.compute_contribution_payload_sha256(contribution),
            )
            for contribution in bundle.contributions
        ],
        approval_attestation=_fixed_attestation(),
    )


def _expected_counts(bundle: LoadedContributionBundle) -> dict[str, int]:
    accepted = [
        assertion
        for contribution in bundle.contributions
        for assertion in contribution.accepted_assertions
    ]
    evidence_ids = {
        str(item.get("evidence_ref_id"))
        for assertion in accepted
        for item in dict(assertion.value).get("evidence") or []
        if isinstance(item, dict) and item.get("evidence_ref_id")
    }
    artifact_ids = {
        str(item.get("source_artifact_id"))
        for assertion in accepted
        for item in dict(assertion.value).get("source_artifacts") or []
        if isinstance(item, dict) and item.get("source_artifact_id")
    }
    return {
        "node_count": len(
            {
                assertion.subject_node_id
                for assertion in accepted
                if assertion.assertion_kind == "node" and assertion.subject_node_id
            }
        ),
        "edge_count": len(
            {
                edge_id
                for assertion in accepted
                if (edge_id := _edge_id(assertion)) is not None
            }
        ),
        "accepted_assertion_count": len(accepted),
        "assertion_support_count": len({item.assertion_id for item in accepted}),
        "evidence_count": len(evidence_ids),
        "source_artifact_count": len(artifact_ids),
    }


def _policy_errors(
    bundle: LoadedContributionBundle,
    report: ContributionBundleValidationReport,
) -> list[str]:
    manifest = bundle.manifest
    errors: list[str] = []
    if manifest.bundle_id != APPROVED_BUNDLE_ID:
        errors.append("bundle_id does not match the locked Eldyrwild package")
    if manifest.bundle_digest != APPROVED_BUNDLE_DIGEST:
        errors.append("bundle_digest does not match the locked Eldyrwild package")
    if manifest.world_id != APPROVED_WORLD_ID:
        errors.append("world_id does not match the locked Eldyrwild package")
    if manifest.primary_campaign_scope != APPROVED_CAMPAIGN_ID:
        errors.append("primary campaign scope does not match the locked package")
    if set(manifest.focus_sessions) != EXPECTED_FOCUS_SESSIONS:
        errors.append("focus sessions do not match the locked package")
    if len(bundle.contributions) != 6:
        errors.append("ordered contribution count must be exactly 6")
    if report.accepted_assertion_count != 30:
        errors.append("accepted assertion count must be exactly 30")
    if report.rejected_assertion_count != 0:
        errors.append("rejected assertion count must be exactly 0")
    if report.unresolved_mention_count != 0:
        errors.append("unresolved mention count must be exactly 0")
    if report.identity_decision_count != 0:
        errors.append("identity decision count must be exactly 0")
    if set(report.source_domains) != EXPECTED_SOURCE_DOMAINS:
        errors.append("source domains do not match the locked package")
    observed_nodes = {
        assertion.subject_node_id
        for contribution in bundle.contributions
        for assertion in contribution.accepted_assertions
        if assertion.assertion_kind == "node" and assertion.subject_node_id
    }
    observed_edges = {
        edge_id
        for contribution in bundle.contributions
        for assertion in contribution.accepted_assertions
        if (edge_id := _edge_id(assertion)) is not None
    }
    if observed_nodes != set(manifest.required_node_ids):
        errors.append("required node set does not match the locked manifest")
    if observed_edges != set(manifest.required_edge_ids):
        errors.append("required edge set does not match the locked manifest")
    if FORBIDDEN_GRAPH_IDS & (observed_nodes | observed_edges):
        errors.append("forbidden graph IDs are present in the approved package")
    return errors


def _certify_bundle() -> _CertifiedBundle:
    try:
        bundle = load_contribution_bundle(_approved_bundle_path())
        report = validate_contribution_bundle(bundle)
    except (FileNotFoundError, OSError):
        raise WorldGraphBootstrapError(
            "The locked Eldyrwild contribution bundle is unavailable.",
            code="invalid_bundle",
            status_code=409,
            bootstrap_state="invalid_bundle",
            diagnostics=[_diagnostic("bundle_unavailable", "Locked bundle could not be loaded.")],
        ) from None
    except (ValueError, ValidationError, json.JSONDecodeError):
        raise WorldGraphBootstrapError(
            "The locked Eldyrwild contribution bundle is not certifiable.",
            code="invalid_bundle",
            status_code=409,
            bootstrap_state="invalid_bundle",
            diagnostics=[_diagnostic("bundle_uncertifiable", "Checksum or bundle validation failed.")],
        ) from None

    errors = list(report.validation_errors)
    errors.extend(_policy_errors(bundle, report))
    if errors:
        diagnostics = [
            _diagnostic("invalid_bundle", message) for message in errors
        ]
        raise WorldGraphBootstrapError(
            "The locked Eldyrwild contribution bundle failed acceptance policy.",
            code="invalid_bundle",
            status_code=409,
            bootstrap_state="invalid_bundle",
            diagnostics=diagnostics,
        )
    plan = _build_plan(bundle)
    return _CertifiedBundle(
        bundle=bundle,
        report=report,
        plan=plan,
        review=_build_review(bundle),
        expected_counts=_expected_counts(bundle),
    )


def _receipt_payload(receipt: Any) -> BootstrapReceipt | None:
    if receipt is None:
        return None
    return BootstrapReceipt.model_validate(
        receipt.model_dump(mode="json", by_alias=True)
    )


def _trust_boundary(
    bundle: LoadedContributionBundle | None,
    state: BootstrapState,
) -> BootstrapTrustBoundary:
    non_claims = list(bundle.manifest.non_claims) if bundle is not None else []
    if bundle is None:
        can_trust = list(TRUST_BOUNDARY_SERVICE_IDENTITY)
        cannot_trust = list(TRUST_BOUNDARY_INVALID)
    else:
        can_trust = list(TRUST_BOUNDARY_CERTIFIED)
        if state in {"active", "active_head_advanced"}:
            can_trust.extend(TRUST_BOUNDARY_PUBLISHED)
            cannot_trust = [
                "Future revisions or mutations not covered by the published initialization receipt."
            ]
        else:
            cannot_trust = [
                "Production publication, receipt, and reconstruction/integrity proof."
            ]
    return BootstrapTrustBoundary(
        can_trust=can_trust,
        cannot_trust=[*non_claims, *cannot_trust, *TRUST_BOUNDARY_NON_CLAIMS],
    )


def _production_state(
    root: Path,
    certified: _CertifiedBundle,
) -> tuple[BootstrapState, Any, str | None]:
    try:
        state = kernel.inspect_world_initialization_state(
            root,
            world_id=APPROVED_WORLD_ID,
            plan=certified.plan,
        )
        receipt = kernel.read_initialization_receipt(root, APPROVED_WORLD_ID)
        current_head = None
        if state in {"active", "active_head_advanced"}:
            current_head = kernel.open_world_graph_head(
                root, APPROVED_WORLD_ID
            ).head_revision_id
        return state, receipt, current_head
    except (json.JSONDecodeError, ValidationError, ValueError):
        raise WorldGraphBootstrapError(
            "The initialization receipt is corrupt or unreadable.",
            code="corrupt_initialization_receipt",
            status_code=409,
            bootstrap_state="error",
            diagnostics=[
                _diagnostic(
                    "corrupt_initialization_receipt",
                    "Initialization receipt could not be decoded or validated.",
                )
            ],
        ) from None
    except WorldInitializationError as exc:
        state = exc.state if exc.state in {"inconsistent_lineage", "error"} else "error"
        raise WorldGraphBootstrapError(
            "The production world lineage is inconsistent.",
            code="inconsistent_lineage",
            status_code=409,
            bootstrap_state=state,
            diagnostics=[
                _diagnostic("inconsistent_lineage", "Production revision lineage is not usable.")
            ],
        ) from None
    except (OSError, WorldGraphNotFoundError):
        raise WorldGraphBootstrapError(
            "The production world state could not be inspected.",
            code="bootstrap_internal_error",
            status_code=500,
            bootstrap_state="error",
            diagnostics=[_diagnostic("state_inspection_failed", "World state inspection failed.")],
        ) from None


def _run_preflight(
    certified: _CertifiedBundle,
    *,
    actor: str,
) -> tuple[str, str]:
    try:
        with TemporaryDirectory(prefix="dmb-world-bootstrap-preflight-") as temp_dir:
            result = kernel.initialize_world_from_contributions(
                Path(temp_dir),
                plan=certified.plan,
                contributions=list(certified.bundle.contributions),
                actor=actor,
            )
            receipt = result.receipt
            if not result.published or receipt is None:
                raise ValueError("preflight did not publish a receipt")
            expected = certified.expected_counts
            actual = {
                "node_count": receipt.node_count,
                "edge_count": receipt.edge_count,
                "accepted_assertion_count": receipt.accepted_assertion_count,
                "assertion_support_count": receipt.assertion_support_count,
                "evidence_count": receipt.evidence_count,
                "source_artifact_count": receipt.source_artifact_count,
            }
            if actual != expected:
                raise ValueError("preflight receipt counts do not match the bundle")
            if set(receipt.source_domains) != EXPECTED_SOURCE_DOMAINS:
                raise ValueError("preflight source domains do not match the bundle")
            if receipt.plan_digest != kernel.compute_initialization_plan_digest(
                certified.plan
            ):
                raise ValueError("preflight receipt plan digest does not match")
            _verify_preflight_graph(Path(temp_dir), certified)
            if (
                receipt.baseline_revision_id is None
                or receipt.initial_head_revision_id is None
            ):
                raise ValueError("preflight did not produce predicted revisions")
            return receipt.baseline_revision_id, receipt.initial_head_revision_id
    except WorldGraphBootstrapError:
        raise
    except Exception:
        raise WorldGraphBootstrapError(
            "The disposable Eldyrwild preflight failed.",
            code="bootstrap_internal_error",
            status_code=500,
            bootstrap_state="error",
            diagnostics=[_diagnostic("preflight_failed", "Disposable preflight verification failed.")],
        ) from None


def _verify_preflight_graph(root: Path, certified: _CertifiedBundle) -> None:
    _head, _revision, store = kernel.open_current_world_graph(
        root, APPROVED_WORLD_ID
    )
    required_nodes = set(certified.bundle.manifest.required_node_ids)
    required_edges = set(certified.bundle.manifest.required_edge_ids)
    if set(store.nodes) != required_nodes or set(store.edges) != required_edges:
        raise ValueError("preflight graph IDs do not match the locked manifest")
    if FORBIDDEN_GRAPH_IDS & (set(store.nodes) | set(store.edges)):
        raise ValueError("preflight graph contains a forbidden ID")
    for expectation in certified.bundle.manifest.expected_shared_support:
        expected_ids = {
            contribution.contribution_id
            for path in expectation.contribution_paths
            for index, entry in enumerate(
                certified.bundle.manifest.ordered_contributions
            )
            if entry.path == path
            for contribution in [certified.bundle.contributions[index]]
        }
        assertion_ids = {
            assertion.assertion_id
            for contribution in certified.bundle.contributions
            if contribution.contribution_id in expected_ids
            for assertion in contribution.accepted_assertions
            if assertion.assertion_kind == "node"
            and assertion.subject_node_id == expectation.node_id
        }
        if len(assertion_ids) != 1:
            raise ValueError("preflight shared support assertion identity mismatch")
        support = store.assertion_support.get(next(iter(assertion_ids)))
        if support is None:
            raise ValueError("preflight shared support record is missing")
        if set(support["active_contribution_ids"]) != expected_ids:
            raise ValueError("preflight shared support contributors do not match")
        observed_domains = {
            store.evidence[evidence_id].source_domain
            for evidence_id in support["evidence_ref_ids"]
            if evidence_id in store.evidence
        }
        if observed_domains != set(expectation.source_domains):
            raise ValueError("preflight shared support domains do not match")


def _proposal_id(
    *,
    actor: str,
    plan_digest: str,
    predicted_baseline_revision_id: str,
    predicted_initial_head_revision_id: str,
) -> str:
    return _stable_digest(
        {
            "kind": "dmb_world_graph_bootstrap_proposal_v1",
            "actor": actor,
            "plan_digest": plan_digest,
            "predicted_baseline_revision_id": predicted_baseline_revision_id,
            "predicted_initial_head_revision_id": predicted_initial_head_revision_id,
        }
    )


def _token_payload(
    *,
    actor: str,
    proposal_id: str,
    plan: WorldInitializationPlan,
    predicted_baseline_revision_id: str,
    predicted_initial_head_revision_id: str,
    expected_counts: dict[str, int],
) -> dict[str, Any]:
    return {
        "kind": CONFIRM_TOKEN_KIND,
        "actor": actor,
        "proposal_id": proposal_id,
        "plan_digest": kernel.compute_initialization_plan_digest(plan),
        "bundle_id": APPROVED_BUNDLE_ID,
        "bundle_digest": APPROVED_BUNDLE_DIGEST,
        "approved_bundle_merge_sha": APPROVED_BUNDLE_MERGE_SHA,
        "ordered_contributions": [
            item.model_dump(mode="json") for item in plan.ordered_contributions
        ],
        "predicted_baseline_revision_id": predicted_baseline_revision_id,
        "predicted_initial_head_revision_id": predicted_initial_head_revision_id,
        "expected_initial_production_state": "ready",
        "expected_counts": expected_counts,
    }


def build_confirm_token(
    *,
    actor: str,
    proposal_id: str,
    plan: WorldInitializationPlan,
    predicted_baseline_revision_id: str,
    predicted_initial_head_revision_id: str,
    expected_counts: dict[str, int],
) -> str:
    payload = _token_payload(
        actor=actor,
        proposal_id=proposal_id,
        plan=plan,
        predicted_baseline_revision_id=predicted_baseline_revision_id,
        predicted_initial_head_revision_id=predicted_initial_head_revision_id,
        expected_counts=expected_counts,
    )
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return f"{hashlib.sha256(raw).hexdigest()}.{encoded}"


def _decode_confirm_token(token: str) -> dict[str, Any]:
    try:
        digest, encoded = token.split(".", 1)
        raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("kind") != CONFIRM_TOKEN_KIND:
            raise ValueError
        return payload
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        raise WorldGraphBootstrapError(
            "The confirmation token is stale or malformed.",
            code="stale_confirmation",
            status_code=409,
            bootstrap_state="error",
            diagnostics=[_diagnostic("stale_confirmation", "Confirmation token validation failed.")],
        ) from None


def _confirm_guarantees(*, published: bool, state: BootstrapState) -> list[str]:
    if published:
        statement = CONFIRM_PUBLICATION_STATEMENT
    else:
        statement = CONFIRM_IDEMPOTENT_STATEMENTS.get(
            state,
            "No new revision was published; the approved initialization remains unchanged.",
        )
    return [statement, *NO_MUTATION_GUARANTEES_CONFIRM]


def _post_commit_confirm_response(
    *,
    request: WorldGraphBootstrapConfirmRequest,
    result: Any,
    plan_digest: str,
) -> WorldGraphBootstrapConfirmResponse:
    state = result.state if result.state in BootstrapState.__args__ else "error"
    diagnostics = [
        _diagnostic("kernel_result", "Kernel initialization result received.", severity="info")
    ]
    try:
        receipt = _receipt_payload(result.receipt)
    except Exception:
        receipt = None
        diagnostics.append(
            _diagnostic(
                "receipt_serialization_degraded",
                "Publication succeeded, but the initialization receipt could not be serialized.",
                severity="warning",
            )
        )

    response_values = {
        "actor": request.actor,
        "proposal_id": request.proposal_id,
        "plan_digest": plan_digest,
        "published": result.published,
        "state": state,
        "baseline_revision_id": result.baseline_revision_id,
        "initial_head_revision_id": result.initial_head_revision_id,
        "current_head_revision_id": result.current_head_revision_id,
        "receipt": receipt,
        "no_mutation_guarantees": _confirm_guarantees(
            published=result.published,
            state=state,
        ),
        "diagnostics": diagnostics,
    }
    try:
        return WorldGraphBootstrapConfirmResponse(**response_values)
    except Exception:
        diagnostics.append(
            _diagnostic(
                "response_assembly_degraded",
                "Publication succeeded, but response assembly used a validated fallback.",
                severity="warning",
            )
        )
        return WorldGraphBootstrapConfirmResponse.model_construct(**response_values)


def _status_from_certified(
    root: Path,
    certified: _CertifiedBundle,
) -> WorldGraphBootstrapStatusResponse:
    state, receipt, current_head = _production_state(root, certified)
    initial_head = receipt.initial_head_revision_id if receipt is not None else None
    return WorldGraphBootstrapStatusResponse(
        state=state,
        world_id=APPROVED_WORLD_ID,
        campaign_id=APPROVED_CAMPAIGN_ID,
        focus_session_id=APPROVED_FOCUS_SESSION_ID,
        bundle_id=APPROVED_BUNDLE_ID,
        bundle_digest=APPROVED_BUNDLE_DIGEST,
        approved_bundle_merge_sha=APPROVED_BUNDLE_MERGE_SHA,
        bundle_valid=True,
        current_head_revision_id=current_head,
        initial_head_revision_id=initial_head,
        head_advanced_since_initialization=state == "active_head_advanced",
        review=certified.review,
        trust_boundary=_trust_boundary(certified.bundle, state),
        diagnostics=[
            _diagnostic("bundle_certified", "Locked bundle passed checksum and acceptance policy.", severity="info")
        ],
        receipt=_receipt_payload(receipt),
    )


def get_world_graph_bootstrap_status(
    *,
    root: Path | None = None,
) -> WorldGraphBootstrapStatusResponse:
    graph_root = _resolved_root(root)
    try:
        certified = _certify_bundle()
    except WorldGraphBootstrapError as exc:
        return WorldGraphBootstrapStatusResponse(
            state=exc.bootstrap_state,
            world_id=APPROVED_WORLD_ID,
            campaign_id=APPROVED_CAMPAIGN_ID,
            focus_session_id=APPROVED_FOCUS_SESSION_ID,
            bundle_id=APPROVED_BUNDLE_ID,
            bundle_digest=APPROVED_BUNDLE_DIGEST,
            approved_bundle_merge_sha=APPROVED_BUNDLE_MERGE_SHA,
            bundle_valid=False,
            trust_boundary=_trust_boundary(None, exc.bootstrap_state),
            diagnostics=exc.diagnostics,
        )
    try:
        return _status_from_certified(graph_root, certified)
    except WorldGraphBootstrapError as exc:
        return WorldGraphBootstrapStatusResponse(
            state=exc.bootstrap_state,
            world_id=APPROVED_WORLD_ID,
            campaign_id=APPROVED_CAMPAIGN_ID,
            focus_session_id=APPROVED_FOCUS_SESSION_ID,
            bundle_id=APPROVED_BUNDLE_ID,
            bundle_digest=APPROVED_BUNDLE_DIGEST,
            approved_bundle_merge_sha=APPROVED_BUNDLE_MERGE_SHA,
            bundle_valid=True,
            review=certified.review,
            trust_boundary=_trust_boundary(certified.bundle, exc.bootstrap_state),
            diagnostics=exc.diagnostics,
        )


def _prepare_material(
    root: Path,
    *,
    actor: str,
    require_ready: bool = True,
) -> tuple[_CertifiedBundle, str, str, str, str]:
    certified = _certify_bundle()
    state, _receipt, _head = _production_state(root, certified)
    if require_ready and state != "ready":
        code = {
            "blocked_existing_world": "blocked_existing_world",
            "inconsistent_lineage": "inconsistent_lineage",
        }.get(state, "bootstrap_not_ready")
        raise WorldGraphBootstrapError(
            (
                "An existing production world is not the approved bootstrap."
                if code == "blocked_existing_world"
                else "Bootstrap preparation is allowed only while production state is ready."
            ),
            code=code,
            status_code=409,
            bootstrap_state=state,
            diagnostics=[
                _diagnostic(
                    code,
                    (
                        "Existing production world is not bound to the approved plan."
                        if code == "blocked_existing_world"
                        else f"Production bootstrap state is {state}."
                    ),
                )
            ],
        )
    predicted_baseline, predicted_head = _run_preflight(certified, actor=actor)
    plan_digest = kernel.compute_initialization_plan_digest(certified.plan)
    proposal_id = _proposal_id(
        actor=actor,
        plan_digest=plan_digest,
        predicted_baseline_revision_id=predicted_baseline,
        predicted_initial_head_revision_id=predicted_head,
    )
    token = build_confirm_token(
        actor=actor,
        proposal_id=proposal_id,
        plan=certified.plan,
        predicted_baseline_revision_id=predicted_baseline,
        predicted_initial_head_revision_id=predicted_head,
        expected_counts=certified.expected_counts,
    )
    return certified, proposal_id, token, predicted_baseline, predicted_head


def prepare_world_graph_bootstrap(
    request: WorldGraphBootstrapPrepareRequest,
    *,
    root: Path | None = None,
) -> WorldGraphBootstrapPrepareResponse:
    graph_root = _resolved_root(root)
    certified, proposal_id, token, predicted_baseline, predicted_head = _prepare_material(
        graph_root,
        actor=request.actor,
    )
    return WorldGraphBootstrapPrepareResponse(
        actor=request.actor,
        proposal_id=proposal_id,
        confirm_token=token,
        plan_digest=kernel.compute_initialization_plan_digest(certified.plan),
        predicted_baseline_revision_id=predicted_baseline,
        predicted_initial_head_revision_id=predicted_head,
        review=certified.review,
        effects=WorldGraphBootstrapEffects(
            contribution_count=len(certified.bundle.contributions),
            predicted_revision_count=len(certified.bundle.contributions) + 1,
            ordered_contribution_ids=[
                item.contribution_id for item in certified.plan.ordered_contributions
            ],
            predicted_baseline_revision_id=predicted_baseline,
            predicted_initial_head_revision_id=predicted_head,
        ),
        no_mutation_guarantees=list(NO_MUTATION_GUARANTEES_PREPARE),
    )


def confirm_world_graph_bootstrap(
    request: WorldGraphBootstrapConfirmRequest,
    *,
    root: Path | None = None,
) -> WorldGraphBootstrapConfirmResponse:
    graph_root = _resolved_root(root)
    certified, expected_proposal, _expected_token, predicted_baseline, predicted_head = (
        _prepare_material(graph_root, actor=request.actor, require_ready=False)
    )
    plan_digest = kernel.compute_initialization_plan_digest(certified.plan)
    actual_payload = _decode_confirm_token(request.confirm_token)
    expected_payload = _token_payload(
        actor=request.actor,
        proposal_id=expected_proposal,
        plan=certified.plan,
        predicted_baseline_revision_id=predicted_baseline,
        predicted_initial_head_revision_id=predicted_head,
        expected_counts=certified.expected_counts,
    )
    if actual_payload.get("actor") != request.actor:
        raise WorldGraphBootstrapError(
            "Confirmation actor does not match the prepared proposal.",
            code="actor_mismatch",
            status_code=409,
            bootstrap_state="error",
            diagnostics=[_diagnostic("actor_mismatch", "Prepared actor and confirming actor differ.")],
        )
    if request.proposal_id != expected_proposal or actual_payload.get("proposal_id") != request.proposal_id:
        raise WorldGraphBootstrapError(
            "Confirmation proposal ID does not match the prepared proposal.",
            code="proposal_mismatch",
            status_code=409,
            bootstrap_state="error",
            diagnostics=[_diagnostic("proposal_mismatch", "Proposal binding did not match.")],
        )
    if actual_payload != expected_payload:
        raise WorldGraphBootstrapError(
            "The confirmation token is stale for the current approved plan.",
            code="stale_confirmation",
            status_code=409,
            bootstrap_state="error",
            diagnostics=[_diagnostic("stale_confirmation", "Confirmation token binding did not match.")],
        )

    state, _receipt, _head = _production_state(graph_root, certified)
    if state == "blocked_existing_world":
        raise WorldGraphBootstrapError(
            "An existing world is not bound to the approved initialization plan.",
            code="blocked_existing_world",
            status_code=409,
            bootstrap_state=state,
            diagnostics=[_diagnostic("blocked_existing_world", "Existing production world is not the approved bootstrap.")],
        )
    if state == "inconsistent_lineage":
        raise WorldGraphBootstrapError(
            "The production world has inconsistent revision lineage.",
            code="inconsistent_lineage",
            status_code=409,
            bootstrap_state=state,
            diagnostics=[_diagnostic("inconsistent_lineage", "Production revision lineage is inconsistent.")],
        )
    try:
        result = kernel.initialize_world_from_contributions(
            graph_root,
            plan=certified.plan,
            contributions=list(certified.bundle.contributions),
            actor=request.actor,
        )
    except WorldInitializationError as exc:
        code = (
            exc.state
            if exc.state in {"blocked_existing_world", "inconsistent_lineage"}
            else "bootstrap_internal_error"
        )
        raise WorldGraphBootstrapError(
            "The Kernel could not complete Eldyrwild bootstrap activation.",
            code=code,
            status_code=409 if code != "bootstrap_internal_error" else 500,
            bootstrap_state=exc.state if exc.state in BootstrapState.__args__ else "error",
            diagnostics=[_diagnostic(code, "Kernel initialization did not complete.")],
        ) from None
    return _post_commit_confirm_response(
        request=request,
        result=result,
        plan_digest=plan_digest,
    )


def _normalize_contract_example(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "<created-at>"
            if key == "createdAt"
            else _normalize_contract_example(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_normalize_contract_example(item) for item in value]
    return value


def _contract_examples() -> dict[str, Any]:
    with TemporaryDirectory(prefix="dmb-world-bootstrap-contract-") as temp_dir:
        root = Path(temp_dir)
        ready = get_world_graph_bootstrap_status(root=root)
        prepared = prepare_world_graph_bootstrap(
            WorldGraphBootstrapPrepareRequest(actor="gm"),
            root=root,
        )
        published = confirm_world_graph_bootstrap(
            WorldGraphBootstrapConfirmRequest(
                actor="gm",
                proposal_id=prepared.proposal_id,
                confirm_token=prepared.confirm_token,
            ),
            root=root,
        )
        idempotent = confirm_world_graph_bootstrap(
            WorldGraphBootstrapConfirmRequest(
                actor="gm",
                proposal_id=prepared.proposal_id,
                confirm_token=prepared.confirm_token,
            ),
            root=root,
        )

        invalid_root = root / "invalid"
        with patch.object(
            sys.modules[__name__],
            "_approved_bundle_path",
            return_value=invalid_root / "missing-bundle",
        ):
            try:
                prepare_world_graph_bootstrap(
                    WorldGraphBootstrapPrepareRequest(actor="gm"),
                    root=invalid_root,
                )
            except WorldGraphBootstrapError as exc:
                invalid_bundle = exc.response()
            else:
                raise AssertionError("invalid bundle contract example did not fail")

        blocked_root = root / "blocked"
        baseline = kernel.build_empty_technical_baseline_store(
            APPROVED_CAMPAIGN_ID,
            APPROVED_FOCUS_SESSION_ID,
        )
        kernel.publish_world_revision(
            blocked_root,
            APPROVED_WORLD_ID,
            baseline,
            operation_ids=["contract-example-foreign-world"],
        )
        try:
            prepare_world_graph_bootstrap(
                WorldGraphBootstrapPrepareRequest(actor="gm"),
                root=blocked_root,
            )
        except WorldGraphBootstrapError as exc:
            blocked_world = exc.response()
        else:
            raise AssertionError("blocked world contract example did not fail")

    responses = {
        "readyStatus": ready,
        "preparedProposal": prepared,
        "publishedConfirmation": published,
        "idempotentConfirmation": idempotent,
        "invalidBundle": invalid_bundle,
        "blockedExistingWorld": blocked_world,
    }
    return {
        name: _normalize_contract_example(
            response.model_dump(mode="json", by_alias=True)
        )
        for name, response in responses.items()
    }


def build_api_contract() -> dict[str, Any]:
    """Return the API schemas and examples from real service operations."""
    schemas = {
        "statusResponse": WorldGraphBootstrapStatusResponse.model_json_schema(
            by_alias=True
        ),
        "prepareRequest": WorldGraphBootstrapPrepareRequest.model_json_schema(
            by_alias=True
        ),
        "prepareResponse": WorldGraphBootstrapPrepareResponse.model_json_schema(
            by_alias=True
        ),
        "confirmRequest": WorldGraphBootstrapConfirmRequest.model_json_schema(
            by_alias=True
        ),
        "confirmResponse": WorldGraphBootstrapConfirmResponse.model_json_schema(
            by_alias=True
        ),
        "errorResponse": WorldGraphBootstrapErrorResponse.model_json_schema(
            by_alias=True
        ),
    }
    examples = {
        **_contract_examples(),
    }
    return {
        "schema": CONTRACT_SCHEMA,
        "version": "1.0",
        "schemas": schemas,
        "examples": examples,
    }


__all__ = [
    "APPROVED_BUNDLE_DIGEST",
    "APPROVED_BUNDLE_ID",
    "APPROVED_BUNDLE_MERGE_SHA",
    "APPROVED_CAMPAIGN_ID",
    "APPROVED_FOCUS_SESSION_ID",
    "APPROVED_WORLD_ID",
    "WorldGraphBootstrapError",
    "build_api_contract",
    "build_confirm_token",
    "confirm_world_graph_bootstrap",
    "get_world_graph_bootstrap_status",
    "prepare_world_graph_bootstrap",
]
