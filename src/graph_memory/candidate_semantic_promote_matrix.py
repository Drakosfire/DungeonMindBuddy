"""Fail-closed semantic-state → Kernel mapping for extract promotion.

Only played-canon, source-evidenced candidates may become Kernel canonical
state. Planning scaffolds, diagnostic-only, and LLM-extraction defaults are
rejected rather than silently rewritten to ``canonical``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from graph_memory.candidate_graph_preview import (
    COMMITTED_ACTIONS,
    CandidateEdge,
    CandidateNode,
    SemanticState,
)

_PROMOTE_CANON = frozenset({"played_canon"})
_PROMOTE_AUTHORITY = frozenset({"played_truth", "system_derived"})
_PROMOTE_EVIDENCE_ROLE = frozenset({"source_evidence"})
_PROMOTE_LIFECYCLE = frozenset({"candidate", "validated"})
_PROMOTE_VISIBILITY = frozenset({"gm_private", "player_visible", "spoiler_sensitive"})
_PROMOTE_ACTIONS = frozenset({"create", "anchor"})


class CandidateSemanticPromoteError(ValueError):
    """Raised when candidate semantics are not eligible for Kernel promotion."""


@dataclass(frozen=True)
class KernelSemanticMapping:
    canon_state: str
    visibility: str
    epistemic_kind: str
    approval_state: str


def _require_promote_eligible(
    *,
    object_id: str,
    semantic: SemanticState,
    proposed_action: str,
    confidence: str,
    warnings: tuple[str, ...],
) -> None:
    if semantic.canon_state not in _PROMOTE_CANON:
        raise CandidateSemanticPromoteError(
            f"{object_id}: canon_state={semantic.canon_state!r} is not promote-eligible "
            f"(require played_canon)"
        )
    if semantic.authority_state not in _PROMOTE_AUTHORITY:
        raise CandidateSemanticPromoteError(
            f"{object_id}: authority_state={semantic.authority_state!r} is not "
            f"promote-eligible (require played_truth|system_derived)"
        )
    if semantic.evidence_role not in _PROMOTE_EVIDENCE_ROLE:
        raise CandidateSemanticPromoteError(
            f"{object_id}: evidence_role={semantic.evidence_role!r} is not "
            f"promote-eligible (require source_evidence)"
        )
    if semantic.lifecycle_state not in _PROMOTE_LIFECYCLE:
        raise CandidateSemanticPromoteError(
            f"{object_id}: lifecycle_state={semantic.lifecycle_state!r} is not "
            f"promote-eligible (require candidate|validated)"
        )
    if semantic.visibility_state not in _PROMOTE_VISIBILITY:
        raise CandidateSemanticPromoteError(
            f"{object_id}: visibility_state={semantic.visibility_state!r} is not "
            f"promote-eligible"
        )
    if proposed_action in COMMITTED_ACTIONS:
        raise CandidateSemanticPromoteError(
            f"{object_id}: proposed_action={proposed_action!r} is already committed"
        )
    if proposed_action not in _PROMOTE_ACTIONS:
        raise CandidateSemanticPromoteError(
            f"{object_id}: proposed_action={proposed_action!r} is not promote-eligible "
            f"(require create|anchor)"
        )
    # confidence / warnings are recorded but do not block played_canon promote.
    _ = confidence, warnings


def kernel_visibility_for_candidate(visibility_state: str) -> str:
    if visibility_state == "player_visible":
        return "player"
    return "gm"


def map_candidate_semantics_to_kernel(
    *,
    object_id: str,
    semantic: SemanticState,
    proposed_action: str,
    confidence: str = "medium",
    warnings: tuple[str, ...] = (),
    acceptance_state: str = "candidate",
) -> KernelSemanticMapping:
    """Map promote-eligible candidate semantics to Kernel assertion fields."""
    _require_promote_eligible(
        object_id=object_id,
        semantic=semantic,
        proposed_action=proposed_action,
        confidence=confidence,
        warnings=warnings,
    )
    return KernelSemanticMapping(
        canon_state="canonical",
        visibility=kernel_visibility_for_candidate(semantic.visibility_state),
        epistemic_kind="source_derived_candidate",
        approval_state="accepted" if acceptance_state == "accepted" else "candidate",
    )


def assert_node_promote_eligible(node: CandidateNode) -> KernelSemanticMapping:
    return map_candidate_semantics_to_kernel(
        object_id=node.node_id,
        semantic=node.semantic_state,
        proposed_action=node.proposed_action,
        confidence=node.confidence,
        warnings=node.warnings,
    )


def assert_edge_promote_eligible(edge: CandidateEdge) -> KernelSemanticMapping:
    return map_candidate_semantics_to_kernel(
        object_id=edge.edge_id,
        semantic=edge.semantic_state,
        proposed_action=edge.proposed_action,
        confidence=edge.confidence,
        warnings=edge.warnings,
    )


def semantic_diagnostics(node_or_edge: CandidateNode | CandidateEdge) -> list[str]:
    """Carry candidate warnings into Kernel contribution diagnostics."""
    object_id = getattr(node_or_edge, "node_id", None) or getattr(
        node_or_edge, "edge_id", "?"
    )
    out = [f"confidence:{object_id}:{getattr(node_or_edge, 'confidence', 'unknown')}"]
    for warning in getattr(node_or_edge, "warnings", ()) or ():
        text = str(warning).strip()
        if text:
            out.append(f"warning:{object_id}:{text}")
    return out


def matrix_summary() -> dict[str, Any]:
    return {
        "canon_state": sorted(_PROMOTE_CANON),
        "authority_state": sorted(_PROMOTE_AUTHORITY),
        "evidence_role": sorted(_PROMOTE_EVIDENCE_ROLE),
        "lifecycle_state": sorted(_PROMOTE_LIFECYCLE),
        "visibility_state": sorted(_PROMOTE_VISIBILITY),
        "proposed_action": sorted(_PROMOTE_ACTIONS),
        "kernel_canon_state": "canonical",
        "kernel_epistemic_kind": "source_derived_candidate",
    }
