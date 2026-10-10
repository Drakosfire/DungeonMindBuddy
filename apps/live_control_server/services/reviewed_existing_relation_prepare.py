"""Trusted, read-only preparation of reviewed edges between canonical nodes.

The caller must already hold a GM execution context and a pinned independent
semantic review. This module only prepares a Core v2 intent; it never confirms,
finalizes, publishes, creates nodes, or changes the source extraction.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from dungeonmind.application.graph_snapshot import GRAPH_SCHEMA_V6
from dungeonmind.application.graph_snapshot_v6 import UnionGraphV6Payload
from dungeonmind.application.repositories import SourceRepository, WorldGraphRepository
from dungeonmind.application.semantic_profiles import (
    SemanticProfileRegistry,
    resolve_and_verify_profile,
    validate_qualified_term,
)
from dungeonmind.contracts.capability import CapabilityEffect, CapabilityPolicy
from dungeonmind.contracts.contribution import (
    AcceptanceState,
    ContributionSourceKind,
    GraphContributionAssertionV2,
    GraphContributionV2,
)
from dungeonmind.contracts.contribution_review import (
    ContributionAssertionVerdict,
    ContributionPlanRef,
)
from dungeonmind.contracts.contribution_review_v2 import (
    ContributionReviewIntentV2,
    contribution_v2_payload_sha256,
    derive_review_intent_sha256_v2,
)
from dungeonmind.contracts.evidence import EvidenceRef, EvidenceRole, SourceStatus
from dungeonmind.contracts.projection import Admissibility
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.domain.capability import evaluate_capability
from dungeonmind_dnd.application.world_object_vocabulary import (
    load_builtin_world_object_v5_vocabulary,
)

from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
    predicate_allowed_endpoints,
)
from apps.live_control_server.models.reviewed_existing_relation_prepare import (
    PinnedExistingRelationReview,
    TrustedGMRelationContext,
)
from graph_memory.source_span import (
    source_span_index_from_dict,
    validate_source_span_index,
)

_PLAN_SCHEMA = "dmb_reviewed_existing_relation_prepare_v1"
PREPARE_TOOL_NAME = "dungeonbuddy.prepare_reviewed_existing_relations"


class ReviewedExistingRelationPrepareError(ValueError):
    """A failed exact closure; no review intent was prepared."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise ReviewedExistingRelationPrepareError(code, message)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _record_digest(value: PinnedExistingRelationReview) -> str:
    return canonical_sha256(value.model_dump(mode="json", exclude={"review_sha256"}))


def _resolve_source_run(repo_root: Path, run_id: str) -> tuple[Any, Any]:
    from apps.live_control_server.services.graph_run_registry import get_extraction_run
    from apps.live_control_server.services.promotable_ingest_run import (
        resolve_promotable_ingest_run,
    )

    return get_extraction_run(repo_root, run_id), resolve_promotable_ingest_run(
        run_id, root=repo_root
    )


def _get_managed_world(repo_root: Path, world_id: str) -> Any:
    from apps.live_control_server.services.world_container_registry import (
        get_world_container,
    )

    return get_world_container(repo_root, world_id)


def _load_pinned_source(
    review: PinnedExistingRelationReview,
    *,
    repo_root: Path,
) -> tuple[dict[str, Any], dict[str, str], str]:
    """Use the canonical run resolver, then check its exact bytes and spans."""
    try:
        run, resolved = _resolve_source_run(repo_root, review.source_run_id)
        if (
            resolved.run_id != review.source_run_id
            or resolved.world_id != review.buddy_world_id
            or resolved.campaign_id != review.campaign_id
            or resolved.source_artifact_id != review.source_artifact_id
            or resolved.source_revision_id.removeprefix("sha256:")
            != review.source_body_sha256
            or resolved.source_span_index_path is None
        ):
            _fail(
                "source_binding_mismatch",
                "run, World, campaign, or source identity changed",
            )
        components = run.components
        source_component = components["source_artifact"]
        candidate_component = components["candidate_graph"]
        span_component = components["source_span_index"]
        source_bytes = resolved.normalized_recap_path.read_bytes()
        candidate_bytes = resolved.candidate_graph_path.read_bytes()
        span_bytes = resolved.source_span_index_path.read_bytes()
        if (
            _sha(source_bytes) != review.source_body_sha256
            or _sha(source_bytes) != source_component.sha256.removeprefix("sha256:")
            or _sha(candidate_bytes) != review.candidate_graph_sha256
            or _sha(candidate_bytes)
            != candidate_component.sha256.removeprefix("sha256:")
            or _sha(span_bytes) != review.source_span_index_sha256
            or _sha(span_bytes) != span_component.sha256.removeprefix("sha256:")
        ):
            _fail(
                "source_digest_drift",
                "run-pinned source, candidate, or span bytes changed",
            )
        source_text = source_bytes.decode("utf-8", errors="strict")
        index = source_span_index_from_dict(json.loads(span_bytes))
        validate_source_span_index(
            index,
            source_artifact_id=review.source_artifact_id,
            content_sha256=review.source_body_sha256,
        )
        lines = source_text.splitlines()
        paragraphs = {
            span.source_span_id: "\n".join(lines[span.start_line - 1 : span.end_line])
            for span in index.spans
            if 1 <= span.start_line <= span.end_line <= len(lines)
        }
        if len(paragraphs) != len(index.spans) or any(
            not text.strip() for text in paragraphs.values()
        ):
            _fail(
                "source_span_drift", "run-pinned source spans do not resolve to prose"
            )
        candidate = json.loads(candidate_bytes)
        if not isinstance(candidate, dict) or not isinstance(
            candidate.get("edges"), list
        ):
            _fail("candidate_invalid", "run-pinned candidate graph is malformed")
        return candidate, paragraphs, resolved.source_domain
    except ReviewedExistingRelationPrepareError:
        raise
    except Exception as exc:  # noqa: BLE001 - all source read failures deny preparation
        _fail("source_unavailable", f"exact source proof failed: {type(exc).__name__}")


def prepare_reviewed_existing_relations(
    context: TrustedGMRelationContext,
    review: PinnedExistingRelationReview,
    *,
    repo_root: Path,
    gm_capability_policy: CapabilityPolicy,
    world_graph_repository: WorldGraphRepository,
    source_repository: SourceRepository,
    semantic_profile_registry: SemanticProfileRegistry,
) -> ContributionReviewIntentV2:
    """Prepare one digested edge-only v2 intent from a trusted semantic review."""
    if _record_digest(review) != review.review_sha256:
        _fail("review_digest_drift", "semantic review artifact digest changed")
    try:
        evaluate_capability(
            gm_capability_policy,
            tool_name=PREPARE_TOOL_NAME,
            effect=CapabilityEffect.PREVIEW_WRITE,
        )
    except Exception as exc:  # noqa: BLE001 - any policy denial blocks preparation
        _fail(
            "prepare_capability_denied",
            f"trusted preparation capability denied: {type(exc).__name__}",
        )
    scope = gm_capability_policy.graph_scope
    if (
        scope is None
        or scope.admissibility is not Admissibility.GM
        or scope.world_id != context.native_world_id
        or scope.campaign_id != context.campaign_id
        or scope.revision_pin != context.expected_parent_revision_id
    ):
        _fail(
            "gm_scope_required",
            "preparation requires the selected pinned GM graph scope",
        )
    if (
        review.buddy_world_id != context.buddy_world_id
        or review.native_world_id != context.native_world_id
        or review.campaign_id != context.campaign_id
        or review.expected_parent_revision_id != context.expected_parent_revision_id
        or review.expected_parent_payload_sha256
        != context.expected_parent_payload_sha256
    ):
        _fail(
            "context_mismatch",
            "semantic review is not bound to the selected GM context",
        )
    try:
        container = _get_managed_world(repo_root, context.buddy_world_id)
    except Exception as exc:  # noqa: BLE001 - managed World read failures deny preparation
        _fail(
            "world_unavailable",
            f"managed World binding is unavailable: {type(exc).__name__}",
        )
    binding = container.native_graph_binding
    if (
        binding is None
        or binding.status != "active"
        or binding.native_world_id != context.native_world_id
    ):
        _fail(
            "world_binding_mismatch",
            "selected World has no matching active native graph",
        )

    head = world_graph_repository.get_head(context.native_world_id)
    if head is None or head.head_revision_id != context.expected_parent_revision_id:
        _fail("parent_drift", "native World head differs from reviewed parent")
    parent = world_graph_repository.get_revision(
        context.native_world_id, context.expected_parent_revision_id
    )
    if parent is None or (
        parent.revision.world_id != context.native_world_id
        or parent.revision.graph_schema != GRAPH_SCHEMA_V6
        or parent.revision.graph_payload_sha256
        != context.expected_parent_payload_sha256
        or canonical_sha256(parent.graph_payload)
        != context.expected_parent_payload_sha256
    ):
        _fail("parent_drift", "native World parent schema or payload digest changed")
    try:
        graph = UnionGraphV6Payload.model_validate(parent.graph_payload)
        if (
            graph.model_dump(mode="json") != parent.graph_payload
            or graph.world_id != context.native_world_id
        ):
            _fail("parent_invalid", "native World parent does not round-trip exactly")
        profile = resolve_and_verify_profile(
            graph.semantic_profile, semantic_profile_registry
        )
    except ReviewedExistingRelationPrepareError:
        raise
    except Exception as exc:  # noqa: BLE001 - parent/profile integrity failures deny preparation
        _fail(
            "parent_invalid",
            f"native World parent or profile is invalid: {type(exc).__name__}",
        )

    artifact = source_repository.get_artifact(review.source_artifact_id)
    revision = source_repository.get_revision(review.source_revision_id)
    if (
        artifact is None
        or revision is None
        or artifact.world_id != context.native_world_id
        or artifact.campaign_id != context.campaign_id
        or artifact.status != SourceStatus.ACTIVE
        or artifact.current_revision_id != review.source_revision_id
        or revision.source_artifact_id != review.source_artifact_id
        or revision.content_sha256.removeprefix("sha256:") != review.source_body_sha256
        or artifact.source_domain is None
    ):
        _fail(
            "source_not_admitted",
            "exact source revision is not active in the selected native World",
        )
    candidate, paragraphs, source_domain = _load_pinned_source(
        review, repo_root=repo_root
    )
    expected_domain = "session_recap" if source_domain == "recap" else source_domain
    if (
        expected_domain not in {"session_recap", "worldbuilding"}
        or artifact.source_domain.value != expected_domain
    ):
        _fail(
            "source_domain_mismatch",
            "run source domain differs from admitted native source",
        )
    if candidate.get("campaign_id") != context.campaign_id:
        _fail(
            "candidate_scope_mismatch",
            "candidate campaign differs from selected campaign",
        )
    edges = candidate["edges"]
    objects = {item.object_id: item for item in graph.objects}
    existing_ids = {item.relationship_id for item in graph.relationships}
    existing_triples = {
        (item.source_object_id, item.predicate, item.target_object_id)
        for item in graph.relationships
    }
    existing_evidence_ids = {item.evidence_ref_id for item in graph.evidence_refs}
    vocabulary = load_builtin_world_object_v5_vocabulary()
    assertions: list[GraphContributionAssertionV2] = []
    verdicts: list[ContributionAssertionVerdict] = []
    new_evidence_ids: set[str] = set()
    new_triples: set[tuple[str, str, str]] = set()
    for relation in sorted(review.relations, key=lambda item: item.relationship_id):
        matches = [
            item
            for item in edges
            if isinstance(item, dict)
            and item.get("edge_id") == relation.candidate_edge_id
        ]
        if len(matches) != 1:
            _fail(
                "candidate_edge_missing",
                "reviewed candidate edge is absent or ambiguous",
            )
        refs = matches[0].get("evidence_refs")
        if not isinstance(refs, list):
            _fail("candidate_evidence_missing", "candidate edge lacks source evidence")
        candidate_spans = {
            item.get("source_span_ref_id")
            for item in refs
            if isinstance(item, dict)
            and item.get("source_artifact_id") == review.source_artifact_id
        }
        matching_refs = [
            item
            for item in refs
            if isinstance(item, dict)
            and item.get("source_artifact_id") == review.source_artifact_id
        ]
        if (
            len(matching_refs) != len(candidate_spans)
            or set(relation.source_span_ids) != candidate_spans
        ):
            _fail(
                "candidate_evidence_drift",
                "reviewed spans differ from the exact candidate edge",
            )
        if any(span not in paragraphs for span in relation.source_span_ids):
            _fail(
                "source_span_drift",
                "reviewed source span is absent from the pinned body",
            )
        from graph_memory.anchor_quotes import find_anchor_quote_matches

        for ref in matching_refs:
            quotes = ref.get("anchor_quotes")
            if quotes is None:
                continue
            if (
                not isinstance(quotes, list)
                or not quotes
                or any(
                    not isinstance(quote, str)
                    or not quote.strip()
                    or not find_anchor_quote_matches(
                        paragraphs[ref["source_span_ref_id"]], [quote]
                    )
                    for quote in quotes
                )
            ):
                _fail(
                    "source_quote_drift",
                    "candidate quote is not literal in the pinned source span",
                )
        subject = objects.get(relation.subject_object_id)
        target = objects.get(relation.object_object_id)
        if subject is None or target is None:
            _fail(
                "endpoint_missing",
                "reviewed relation endpoint is not canonical in the parent",
            )
        if subject.kind != relation.subject_kind or target.kind != relation.object_kind:
            _fail(
                "endpoint_kind_drift", "reviewed endpoint kind differs from the parent"
            )
        try:
            validate_qualified_term(
                relation.qualified_predicate, profile, field_name="predicate"
            )
        except Exception as exc:  # noqa: BLE001 - profile validation failures deny preparation
            _fail(
                "predicate_invalid",
                f"predicate is not admitted by the parent profile: {type(exc).__name__}",
            )
        allowed = predicate_allowed_endpoints(relation.qualified_predicate, vocabulary)
        if (
            allowed is None
            or subject.kind not in allowed[0]
            or target.kind not in allowed[1]
        ):
            _fail(
                "predicate_kind_invalid",
                "predicate does not admit these exact endpoint kinds",
            )
        triple = (subject.object_id, relation.qualified_predicate, target.object_id)
        if (
            relation.relationship_id in existing_ids
            or triple in existing_triples
            or triple in new_triples
        ):
            _fail(
                "relationship_collision",
                "reviewed relationship collides with parent or batch",
            )
        new_triples.add(triple)
        evidence: list[EvidenceRef] = []
        for span_id in sorted(relation.source_span_ids):
            evidence_id = "evidence:reviewed:" + _sha(
                f"{review.review_sha256}\0{relation.relationship_id}\0{span_id}".encode()
            )
            if evidence_id in existing_evidence_ids or evidence_id in new_evidence_ids:
                _fail(
                    "evidence_collision",
                    "reviewed evidence ID collides with parent or batch",
                )
            new_evidence_ids.add(evidence_id)
            evidence.append(
                EvidenceRef(
                    evidence_ref_id=evidence_id,
                    source_artifact_id=review.source_artifact_id,
                    source_revision_id=review.source_revision_id,
                    source_domain=artifact.source_domain,
                    evidence_role=EvidenceRole.SUPPORT,
                    can_open_source=True,
                    can_highlight_span=True,
                    locator=span_id,
                    uri=artifact.uri,
                )
            )
        assertion_id = "assertion:reviewed:" + _sha(
            f"{review.review_sha256}\0{relation.relationship_id}".encode()
        )
        assertions.append(
            GraphContributionAssertionV2(
                assertion_id=assertion_id,
                assertion_kind="edge",
                subject_object_id=subject.object_id,
                object_object_id=target.object_id,
                predicate=relation.qualified_predicate,
                value=json.dumps(
                    {
                        "dm_predicate": relation.qualified_predicate,
                        "edge_id": relation.relationship_id,
                        "session_refs": [],
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                evidence_refs=evidence,
                source_artifact_id=review.source_artifact_id,
                source_revision_id=review.source_revision_id,
                campaign_scope=context.campaign_id,
                temporal_scope={"kind": "unknown"},
            )
        )
        verdicts.append(
            ContributionAssertionVerdict(
                assertion_id=assertion_id,
                acceptance_state=AcceptanceState.ACCEPTED,
            )
        )

    contribution = GraphContributionV2(
        contribution_id="contrib:reviewed:" + review.review_sha256,
        world_id=context.native_world_id,
        source_kind=ContributionSourceKind.GRAPH_REVIEW,
        source_artifact_id=review.source_artifact_id,
        source_revision_id=review.source_revision_id,
        produced_at=review.reviewed_at,
        campaign_scope=context.campaign_id,
        authored_by=context.service_principal,
        assertions=assertions,
        diagnostics={
            "semantic_review_sha256": review.review_sha256,
            "semantic_reviewer_kind": review.semantic_reviewer_kind,
            "semantic_reviewer_id": review.semantic_reviewer_id,
            "preparation": _PLAN_SCHEMA,
        },
    )
    candidate_sha = contribution_v2_payload_sha256(contribution)
    plan_ref = ContributionPlanRef(
        source_plan_schema=_PLAN_SCHEMA,
        source_plan_id="reviewed-existing-relations:" + review.review_sha256,
        source_plan_sha256=review.review_sha256,
        source_input_sha256=review.candidate_graph_sha256,
        preview_content_sha256=candidate_sha,
        candidate_contribution_sha256=candidate_sha,
        expected_parent_revision_id=context.expected_parent_revision_id,
        base_graph_schema=GRAPH_SCHEMA_V6,
        base_graph_payload_sha256=context.expected_parent_payload_sha256,
        semantic_profile=graph.semantic_profile,
    )
    operation_id = (
        "reviewop:"
        + _sha(f"{context.native_world_id}\0{review.review_sha256}".encode())[:32]
    )
    intent_sha = derive_review_intent_sha256_v2(
        operation_id=operation_id,
        world_id=context.native_world_id,
        campaign_id=context.campaign_id,
        plan_ref=plan_ref,
        candidate_contribution=contribution,
        identity_proposals=[],
        identity_verdicts=[],
        assertion_verdicts=verdicts,
        reviewer_id=context.service_principal,
        reviewed_at=review.reviewed_at,
    )
    return ContributionReviewIntentV2(
        operation_id=operation_id,
        world_id=context.native_world_id,
        campaign_id=context.campaign_id,
        plan_ref=plan_ref,
        candidate_contribution=contribution,
        identity_proposals=[],
        identity_verdicts=[],
        assertion_verdicts=verdicts,
        reviewer_id=context.service_principal,
        reviewed_at=review.reviewed_at,
        review_intent_sha256=intent_sha,
    )
