"""Pure candidate-document integrity versus admission-eligibility classification.

Typed preview validation remains the source of candidate issues. This module
only partitions those issues so production generation and Candidate Graph
Admission share one integrity definition. It does not repair, drop, or rewrite
candidate semantics.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from graph_memory.candidate_graph_preview import (
    CandidateGraphPreview,
    CandidateGraphPreviewIssue,
    candidate_graph_preview_from_dict,
    validate_candidate_graph_preview,
)


def is_admission_eligibility_issue(issue: CandidateGraphPreviewIssue) -> bool:
    """Return True for coherent unsupported node kinds, not document corruption."""
    return issue.field == "node_type" and issue.message == "invalid node_type"


@dataclass(frozen=True)
class CandidateDocumentIntegrityClassification:
    """Typed preview plus the integrity/eligibility partition of its issues."""

    preview: CandidateGraphPreview | None
    parse_error: str | None
    integrity_issues: tuple[CandidateGraphPreviewIssue, ...]
    eligibility_issues: tuple[CandidateGraphPreviewIssue, ...]

    @property
    def is_document_integrity_failure(self) -> bool:
        return self.parse_error is not None or bool(self.integrity_issues)


def classify_candidate_document_integrity(
    candidate_graph: Mapping[str, Any],
) -> CandidateDocumentIntegrityClassification:
    """Classify a fully assembled candidate without mutating the caller's mapping."""
    raw = copy.deepcopy(dict(candidate_graph))
    try:
        preview = candidate_graph_preview_from_dict(raw)
    except (KeyError, TypeError, ValueError) as exc:
        return CandidateDocumentIntegrityClassification(
            preview=None,
            parse_error=str(exc),
            integrity_issues=(),
            eligibility_issues=(),
        )

    report = validate_candidate_graph_preview(preview)
    eligibility_issues = tuple(
        issue for issue in report.issues if is_admission_eligibility_issue(issue)
    )
    integrity_issues = tuple(
        issue for issue in report.issues if not is_admission_eligibility_issue(issue)
    )
    return CandidateDocumentIntegrityClassification(
        preview=preview,
        parse_error=None,
        integrity_issues=integrity_issues,
        eligibility_issues=eligibility_issues,
    )
