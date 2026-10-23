"""Overlap detection for graph object authoring prepare warnings."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.live_control_server.services.graph_object_authoring_prepare import (
        GraphAuthoringDiagnostic,
        GraphObjectAuthoringPrepareRequest,
        GraphObjectAuthoringProposalPayload,
    )


def _warning_diag(
    code: str,
    message: str,
    *,
    local_proposal_id: str | None = None,
) -> GraphAuthoringDiagnostic:
    from apps.live_control_server.services.graph_object_authoring_prepare import GraphAuthoringDiagnostic

    return GraphAuthoringDiagnostic(
        code=code,
        message=message,
        local_proposal_id=local_proposal_id,
        severity="warning",
    )


def normalize_overlap_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _add_token(tokens: set[str], text: str | None) -> None:
    if not text:
        return
    normalized = normalize_overlap_text(text)
    if normalized:
        tokens.add(normalized)


def _proposal_identity_tokens(proposal: GraphObjectAuthoringProposalPayload) -> set[str]:
    tokens: set[str] = set()
    if proposal.proposal_kind == "object" and proposal.object_ref:
        label = proposal.object_ref.get("label")
        _add_token(tokens, label if isinstance(label, str) else None)
        aliases = proposal.object_ref.get("aliases")
        if isinstance(aliases, list):
            for alias in aliases:
                if isinstance(alias, str):
                    _add_token(tokens, alias)
    elif proposal.proposal_kind == "link_existing":
        _add_token(tokens, proposal.selected_text)
        _add_token(tokens, proposal.normalized_selected_text)
        _add_token(tokens, proposal.alias_text)
    if proposal.selection:
        selected = proposal.selection.get("selectedText")
        normalized = proposal.selection.get("normalizedSelectedText")
        _add_token(tokens, selected if isinstance(selected, str) else None)
        _add_token(tokens, normalized if isinstance(normalized, str) else None)
    return tokens


def detect_prepare_overlap_warnings(request: GraphObjectAuthoringPrepareRequest) -> list[GraphAuthoringDiagnostic]:
    """Batch-only guidance; unpublished local overlays are not native authority."""
    diagnostics = []
    seen: dict[str, str] = {}
    for proposal in request.proposals:
        for token in sorted(_proposal_identity_tokens(proposal)):
            if token in seen and seen[token] != proposal.local_proposal_id:
                diagnostics.append(_warning_diag(
                    "staged_proposal_possible_duplicate",
                    f'Possible duplicate: "{token}" appears in more than one staged proposal.',
                    local_proposal_id=proposal.local_proposal_id,
                ))
            else:
                seen[token] = proposal.local_proposal_id
    return diagnostics
