"""Production boundary from immutable candidate graph to governed publication.

Candidate integrity and admission eligibility are intentionally separate.  The
complete input is digested before qualification.  A derived eligibility view
may omit unsupported items only after every omission has an explicit sealed
disposition; the caller's candidate is never changed.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any, TypeVar

from apps.live_control_server.models.candidate_graph_admission import (
    CandidateAdmissionBinding,
    CandidateAdmissionDisposition,
    CandidateAdmissionIntegrityError,
    CandidateIntegrityDiagnostic,
)
from graph_memory.candidate_graph_preview import (
    NODE_TYPES,
    candidate_graph_preview_from_dict,
    validate_candidate_graph_preview,
)
from graph_memory.extract_promote_ops import (
    ExtractPromotePrepareResult,
    prepare_extract_promote,
)
from graph_memory.candidate_graph_to_contribution import kernel_kind_for_node_type
from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
    CURRENT_V5_TARGET,
    resolve_buddy_predicate_mapping_v4,
)
from graph_memory.extract_promote_proposal import (
    bind_candidate_admission_to_proposal,
    verify_promote_proposal,
)

_T = TypeVar("_T")


def canonical_candidate_digest(candidate_graph: Mapping[str, Any]) -> str:
    """Hash the complete semantic candidate before any qualification."""
    encoded = json.dumps(
        candidate_graph,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_candidate_document_integrity(candidate_graph: Mapping[str, Any]):
    """Return the exact typed preview while treating unsupported kinds as eligibility."""
    digest = canonical_candidate_digest(candidate_graph)
    raw = copy.deepcopy(dict(candidate_graph))
    try:
        preview = candidate_graph_preview_from_dict(raw)
    except (KeyError, TypeError, ValueError) as exc:
        raise CandidateAdmissionIntegrityError(
            [CandidateIntegrityDiagnostic(code="typed_parse_failed", message=str(exc))],
            candidate_digest=digest,
        ) from exc

    report = validate_candidate_graph_preview(preview)
    eligibility_issues = [
        issue
        for issue in report.issues
        if issue.field == "node_type" and issue.message == "invalid node_type"
    ]
    integrity_issues = [
        issue for issue in report.issues if issue not in eligibility_issues
    ]
    if integrity_issues:
        raise CandidateAdmissionIntegrityError(
            [
                CandidateIntegrityDiagnostic(
                    code=issue.code,
                    object_id=issue.object_id,
                    field=issue.field,
                    message=issue.message,
                )
                for issue in integrity_issues
            ],
            candidate_digest=digest,
        )
    return preview


def _integrity_and_eligibility(
    candidate_graph: Mapping[str, Any],
) -> tuple[dict[str, Any], list[CandidateAdmissionDisposition], str]:
    digest = canonical_candidate_digest(candidate_graph)
    raw = copy.deepcopy(dict(candidate_graph))
    validate_candidate_document_integrity(raw)

    unsupported_ids = {
        str(node.get("node_id") or "")
        for node in raw.get("nodes", [])
        if isinstance(node, Mapping)
        and (
            str(node.get("node_type") or "") not in NODE_TYPES
            or kernel_kind_for_node_type(str(node.get("node_type") or ""))
            not in CURRENT_V5_TARGET.buddy_to_dm_kind
        )
    }
    dispositions = [
        CandidateAdmissionDisposition(
            item_id=str(node.get("node_id") or ""),
            item_kind="node",
            outcome="rejected",
            reason="unsupported_node_type",
        )
        for node in raw.get("nodes", [])
        if isinstance(node, Mapping)
        and str(node.get("node_id") or "") in unsupported_ids
    ]

    admitted_edges: list[Any] = []
    not_admitted_ids = set(unsupported_ids)
    for edge in raw.get("edges", []):
        if not isinstance(edge, Mapping):
            admitted_edges.append(edge)
            continue
        blocked = [
            endpoint
            for endpoint in (
                str(edge.get("from_node_id") or ""),
                str(edge.get("to_node_id") or ""),
            )
            if endpoint in unsupported_ids
        ]
        predicate = str(edge.get("relationship_type") or "").strip()
        if blocked:
            edge_id = str(edge.get("edge_id") or "")
            not_admitted_ids.add(edge_id)
            dispositions.append(
                CandidateAdmissionDisposition(
                    item_id=edge_id,
                    item_kind="edge",
                    outcome="rejected",
                    reason="endpoint_not_admitted",
                    depends_on=blocked,
                )
            )
        elif resolve_buddy_predicate_mapping_v4(predicate) is None:
            edge_id = str(edge.get("edge_id") or "")
            not_admitted_ids.add(edge_id)
            dispositions.append(
                CandidateAdmissionDisposition(
                    item_id=edge_id,
                    item_kind="edge",
                    outcome="rejected",
                    reason="unmapped_predicate",
                )
            )
        else:
            admitted_edges.append(edge)

    # This is an eligibility projection, not repaired candidate authority: the
    # complete original remains bound by digest and every excluded item receives
    # a sealed disposition.
    projected = copy.deepcopy(raw)
    projected["nodes"] = [
        node
        for node in raw.get("nodes", [])
        if not isinstance(node, Mapping)
        or str(node.get("node_id") or "") not in unsupported_ids
    ]
    projected["edges"] = admitted_edges
    admitted_beats: list[Any] = []
    for beat in raw.get("beats", []):
        if not isinstance(beat, Mapping):
            admitted_beats.append(beat)
            continue
        blocked = sorted(
            (
                set(map(str, beat.get("involved_node_ids", [])))
                | set(map(str, beat.get("unresolved_thread_node_ids", [])))
            )
            & unsupported_ids
        )
        if blocked:
            beat_id = str(beat.get("beat_id") or "")
            not_admitted_ids.add(beat_id)
            dispositions.append(
                CandidateAdmissionDisposition(
                    item_id=beat_id,
                    item_kind="beat",
                    outcome="rejected",
                    reason="dependency_not_admitted",
                    depends_on=blocked,
                )
            )
        else:
            admitted_beats.append(beat)
    projected["beats"] = admitted_beats
    retained_targets = {
        str(node.get("node_id") or "")
        for node in projected.get("nodes", [])
        if isinstance(node, Mapping)
    } | {
        str(edge.get("edge_id") or "")
        for edge in projected.get("edges", [])
        if isinstance(edge, Mapping)
    } | {
        str(beat.get("beat_id") or "")
        for beat in projected.get("beats", [])
        if isinstance(beat, Mapping)
    }
    admitted_writes: list[Any] = []
    for write in raw.get("proposed_writes", []):
        if not isinstance(write, Mapping):
            admitted_writes.append(write)
            continue
        target_id = str(write.get("target_id") or "")
        if target_id not in retained_targets or target_id in not_admitted_ids:
            dispositions.append(
                CandidateAdmissionDisposition(
                    item_id=str(write.get("write_id") or ""),
                    item_kind="proposed_write",
                    outcome="rejected",
                    reason="target_not_admitted",
                    depends_on=[target_id] if target_id else [],
                )
            )
        else:
            admitted_writes.append(write)
    projected["proposed_writes"] = admitted_writes
    return projected, dispositions, digest


def prepare_candidate_graph_admission(
    *, candidate_graph: Mapping[str, Any], **prepare_kwargs: Any
) -> ExtractPromotePrepareResult:
    """Prepare and seal one exact candidate against one pinned parent."""
    projected, dispositions, digest = _integrity_and_eligibility(candidate_graph)
    result = prepare_extract_promote(candidate_graph=projected, **prepare_kwargs)
    effect = dict(result.review_package.get("effect") or {})
    binding = CandidateAdmissionBinding(
        candidate_digest=digest,
        candidate_locator=prepare_kwargs.get("candidate_graph_path"),
        candidate_preview_id=str(candidate_graph.get("preview_id") or ""),
        source_artifact_id=str(effect.get("source_artifact_id") or ""),
        source_revision_id=str(effect.get("source_revision_id") or ""),
        world_id=result.world_id,
        parent_revision_id=result.parent_revision_id,
        dispositions=dispositions,
        exact_candidate_counts={
            key: len(candidate_graph.get(key) or [])
            for key in ("nodes", "edges", "beats", "proposed_writes")
        },
    )
    package = bind_candidate_admission_to_proposal(
        result.review_package, binding.as_effect_payload()
    )
    return replace(
        result,
        review_package=package,
        proposal_digest=str(package["proposal_digest"]),
        rejected_assertions_count=result.rejected_assertions_count
        + sum(item.outcome == "rejected" for item in dispositions),
    )


def verify_candidate_graph_admission_confirmation(
    *, review_package: Mapping[str, Any], candidate_graph: Mapping[str, Any]
) -> CandidateAdmissionBinding:
    """Re-prove exact candidate binding before governed confirmation."""
    effect = dict(review_package.get("effect") or {})
    raw_binding = effect.get("candidate_admission")
    if not isinstance(raw_binding, Mapping):
        raise CandidateAdmissionIntegrityError(
            [CandidateIntegrityDiagnostic(code="admission_binding_missing", message="sealed proposal has no candidate admission binding")],
            candidate_digest=canonical_candidate_digest(candidate_graph),
        )
    binding = CandidateAdmissionBinding.model_validate(raw_binding)
    sealed_pairs = {
        "world_id": str(effect.get("world_id") or ""),
        "parent_revision_id": str(effect.get("parent_revision_id") or ""),
        "source_artifact_id": str(effect.get("source_artifact_id") or ""),
        "source_revision_id": str(effect.get("source_revision_id") or ""),
        "candidate_preview_id": str(effect.get("candidate_preview_id") or ""),
    }
    drifted = [
        field
        for field, sealed in sealed_pairs.items()
        if str(getattr(binding, field)) != sealed
    ]
    if drifted:
        raise CandidateAdmissionIntegrityError(
            [
                CandidateIntegrityDiagnostic(
                    code="admission_binding_mismatch",
                    field=field,
                    message=f"candidate admission {field} disagrees with sealed effect",
                )
                for field in drifted
            ],
            candidate_digest=canonical_candidate_digest(candidate_graph),
        )
    actual = canonical_candidate_digest(candidate_graph)
    if actual != binding.candidate_digest:
        raise CandidateAdmissionIntegrityError(
            [CandidateIntegrityDiagnostic(code="candidate_digest_mismatch", message="candidate changed after prepare")],
            candidate_digest=actual,
        )
    # Also prove the ordinary sealed effect before any caller invokes mutation.
    verify_promote_proposal(review_package, confirming_principal="candidate-admission")
    return binding


def confirm_candidate_graph_admission(
    *,
    review_package: Mapping[str, Any],
    candidate_graph: Mapping[str, Any],
    governed_confirm: Callable[[], _T],
) -> _T:
    """Verify admission, then invoke the existing governed write exactly once."""
    verify_candidate_graph_admission_confirmation(
        review_package=review_package, candidate_graph=candidate_graph
    )
    return governed_confirm()
