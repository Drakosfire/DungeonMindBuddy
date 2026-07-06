"""Overlap detection for graph object authoring prepare warnings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.live_control_server.models.graph_authoring_overlay import (
    AuthoredGraphAssertion,
    AuthoredGraphLinkExistingAssertion,
    AuthoredGraphObjectAssertion,
    AuthoredGraphOverlay,
)

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


def _assertion_identity_tokens(assertion: AuthoredGraphAssertion) -> tuple[set[str], set[str], set[str]]:
    labels: set[str] = set()
    aliases: set[str] = set()
    source_anchors: set[str] = set()

    if assertion.status != "authored":
        return labels, aliases, source_anchors

    if assertion.assertion_kind == "object":
        object_assertion: AuthoredGraphObjectAssertion = assertion
        _add_token(labels, object_assertion.object_ref.label)
        for alias in object_assertion.aliases:
            _add_token(aliases, alias)
    elif assertion.assertion_kind == "link_existing":
        link_assertion: AuthoredGraphLinkExistingAssertion = assertion
        _add_token(source_anchors, link_assertion.normalized_selected_text)
        _add_token(source_anchors, link_assertion.selected_text)
        _add_token(aliases, link_assertion.alias_text)
        _add_token(labels, link_assertion.existing_object_ref.label)

    if assertion.source_anchor:
        _add_token(source_anchors, assertion.source_anchor.normalized_selected_text)
        _add_token(source_anchors, assertion.source_anchor.selected_text)

    return labels, aliases, source_anchors


def _overlay_identity_index(
    overlay: AuthoredGraphOverlay,
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Maps normalized token -> display label for labels, aliases, source anchors."""
    labels: dict[str, str] = {}
    aliases: dict[str, str] = {}
    source_anchors: dict[str, str] = {}

    for assertion in overlay.assertions:
        assertion_labels, assertion_aliases, assertion_anchors = _assertion_identity_tokens(assertion)
        display = (
            assertion.object_ref.label
            if assertion.assertion_kind == "object"
            else assertion.existing_object_ref.label
            if assertion.assertion_kind == "link_existing"
            else assertion.assertion_id
        )
        for token in assertion_labels:
            labels.setdefault(token, display)
        for token in assertion_aliases:
            aliases.setdefault(token, display)
        for token in assertion_anchors:
            source_anchors.setdefault(token, token)

    return labels, aliases, source_anchors


def detect_prepare_overlap_warnings(
    request: GraphObjectAuthoringPrepareRequest,
    *,
    existing_overlay: AuthoredGraphOverlay,
) -> list[GraphAuthoringDiagnostic]:
    diagnostics: list[GraphAuthoringDiagnostic] = []
    overlay_labels, overlay_aliases, overlay_source_anchors = _overlay_identity_index(existing_overlay)

    seen_batch_tokens: dict[str, str] = {}

    for proposal in request.proposals:
        tokens = _proposal_identity_tokens(proposal)
        proposal_label = ""
        if proposal.proposal_kind == "object" and proposal.object_ref:
            raw_label = proposal.object_ref.get("label")
            proposal_label = raw_label if isinstance(raw_label, str) else ""
        normalized_proposal_label = normalize_overlap_text(proposal_label)

        if normalized_proposal_label and normalized_proposal_label in overlay_labels:
            diagnostics.append(
                _warning_diag(
                    "authored_overlay_possible_duplicate_label",
                    (
                        f'Possible duplicate: label "{overlay_labels[normalized_proposal_label]}" '
                        "already exists in authored graph memory."
                    ),
                    local_proposal_id=proposal.local_proposal_id,
                )
            )

        for token in tokens:
            if token in overlay_aliases:
                diagnostics.append(
                    _warning_diag(
                        "authored_overlay_possible_duplicate_alias",
                        (
                            f'Possible duplicate: "{token}" is already an alias of authored object '
                            f'"{overlay_aliases[token]}".'
                        ),
                        local_proposal_id=proposal.local_proposal_id,
                    )
                )
            elif (
                token in overlay_labels
                and token != normalized_proposal_label
            ):
                diagnostics.append(
                    _warning_diag(
                        "authored_overlay_possible_duplicate_label",
                        (
                            f'Possible duplicate: "{token}" matches authored object label '
                            f'"{overlay_labels[token]}".'
                        ),
                        local_proposal_id=proposal.local_proposal_id,
                    )
                )
            elif token in overlay_source_anchors:
                diagnostics.append(
                    _warning_diag(
                        "authored_overlay_possible_duplicate_source_anchor",
                        (
                            f'Possible duplicate: source anchor "{overlay_source_anchors[token]}" '
                            "is already linked in authored graph memory."
                        ),
                        local_proposal_id=proposal.local_proposal_id,
                    )
                )

            if token in seen_batch_tokens and seen_batch_tokens[token] != proposal.local_proposal_id:
                diagnostics.append(
                    _warning_diag(
                        "staged_proposal_possible_duplicate",
                        (
                            f'Possible duplicate: "{token}" also appears in staged proposal '
                            f"{seen_batch_tokens[token]}."
                        ),
                        local_proposal_id=proposal.local_proposal_id,
                    )
                )
            else:
                seen_batch_tokens.setdefault(token, proposal.local_proposal_id)

    return diagnostics
