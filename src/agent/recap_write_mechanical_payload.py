"""Deterministic pieces of ``recap_write_v1`` for the ``build_recap_write_payload`` tool.

Pure helpers (no IO except what callers pass in). The planner tool composes these
with :func:`recap_ingest_helpers.assemble_recap` output so the model only authors
``npc_audit`` (judgment), ``plot_artifacts``, ``notes_for_gm``, and pastes
``recap_preview.confirm_token`` after ``write_corpus_file`` dry_run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.agent.recap_context import RecapContext
from src.agent.recap_ingest_helpers import IngestReport
from src.agent.recap_write_output_schema import RECAP_WRITE_SCHEMA_VERSION

_PARA_PREVIEW_MAX = 200


def canonical_recap_path(ctx: RecapContext) -> str:
    """Corpus-relative path for the new recap file (``Session N - Recap.md``)."""
    base = ctx.session_recaps_dir.rstrip("/")
    return f"{base}/Session {ctx.target_session} - Recap.md"


def duplicate_paragraphs_from_ingest(report: IngestReport) -> list[dict[str, Any]]:
    """Build ``duplicate_paragraphs[]`` entries from mechanical duplicate removal."""
    out: list[dict[str, Any]] = []
    for m in report.duplicates_removed:
        prev = (m.b.text or m.a.text).strip()
        if len(prev) > _PARA_PREVIEW_MAX:
            prev = prev[: _PARA_PREVIEW_MAX - 1] + "…"
        out.append(
            {
                "source_lines": [m.a.source_line_start, m.b.source_line_start],
                "paragraph_preview": prev,
                "recommended_action": "remove_later",
            }
        )
    return out


def prep_pointer_proposal_from_context(ctx: RecapContext) -> dict[str, str] | None:
    """Bidirectional prep/recap pointer lines when a prep doc exists; else ``None``."""
    if not ctx.prep_doc_path:
        return None
    prep_basename = Path(ctx.prep_doc_path).name
    n = ctx.target_session
    recap_path = canonical_recap_path(ctx)
    return {
        "prep_path": ctx.prep_doc_path,
        "recap_path": recap_path,
        "prep_append_line": (
            f"> **Prep:** See `Session Prep/{prep_basename}`. "
            "(Expand with session-specific prep-vs-play notes in `notes_for_gm`.)"
        ),
        "recap_append_line": (
            f"> **Played:** See `Session Recaps/Session {n} - Recap.md`. "
            "(Expand with play-vs-prep deltas in `notes_for_gm`.)"
        ),
    }


def build_recap_write_payload_from_ingest(
    ctx: RecapContext,
    report: IngestReport,
) -> dict[str, Any]:
    """Full ``recap_write_v1``-shaped object with mechanical fields + empty placeholders.

    ``recap_preview.confirm_token`` is ``""`` until the model runs ``write_corpus_file``
    with ``dry_run=true`` and copies the token into the final JSON.
    """
    prep = prep_pointer_proposal_from_context(ctx)
    return {
        "schema_version": RECAP_WRITE_SCHEMA_VERSION,
        "recap_preview": {
            "path": canonical_recap_path(ctx),
            "mode": "create",
            "confirm_token": "",
        },
        "duplicate_paragraphs": duplicate_paragraphs_from_ingest(report),
        "npc_audit": {
            "timeline_append_candidates": [],
            "new_hub_proposals": [],
            "dismissed": [],
        },
        "plot_artifacts": [],
        "prep_pointer_proposal": prep,
        "notes_for_gm": "",
    }
