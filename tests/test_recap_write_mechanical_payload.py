"""Tests for deterministic recap_write_v1 field builders."""

from __future__ import annotations

from src.agent.recap_context import RecapContext, RecapEntry
from src.agent.recap_ingest_helpers import DuplicateMatch, IngestReport, Paragraph
from src.agent.recap_write_mechanical_payload import (
    build_recap_write_payload_from_ingest,
    canonical_recap_path,
    duplicate_paragraphs_from_ingest,
    prep_pointer_proposal_from_context,
)
from src.agent.recap_write_output_schema import (
    RECAP_WRITE_SCHEMA_VERSION,
    validate_recap_write_payload,
)


def _ctx() -> RecapContext:
    return RecapContext(
        campaign_id="longmont-c2",
        campaign_hub="Longmont Campaign/Campaign 2",
        session_recaps_dir="Longmont Campaign/Campaign 2/Session Recaps",
        session_prep_dir="Longmont Campaign/Campaign 2/Session Prep",
        npcs_dir="Longmont Campaign/Campaign 2/NPCs",
        target_session=20,
        next_session_after_target=21,
        recent_recaps=[
            RecapEntry(
                path="Longmont Campaign/Campaign 2/Session Recaps/Session 19 - Recap.md",
                session=19,
                title="x",
                campaign_id="longmont-c2",
            )
        ],
        prep_doc_path="Longmont Campaign/Campaign 2/Session Prep/session_20_prep.md",
        notes=[],
    )


def test_canonical_recap_path() -> None:
    assert (
        canonical_recap_path(_ctx())
        == "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"
    )


def test_prep_pointer_proposal_from_context() -> None:
    pp = prep_pointer_proposal_from_context(_ctx())
    assert pp is not None
    assert pp["prep_path"] == "Longmont Campaign/Campaign 2/Session Prep/session_20_prep.md"
    assert "Session Prep/session_20_prep.md" in pp["prep_append_line"]
    assert "Session Recaps/Session 20 - Recap.md" in pp["recap_append_line"]


def test_prep_pointer_none_without_prep_doc() -> None:
    c = _ctx()
    c2 = RecapContext(
        campaign_id=c.campaign_id,
        campaign_hub=c.campaign_hub,
        session_recaps_dir=c.session_recaps_dir,
        session_prep_dir=c.session_prep_dir,
        npcs_dir=c.npcs_dir,
        target_session=c.target_session,
        next_session_after_target=c.next_session_after_target,
        recent_recaps=c.recent_recaps,
        prep_doc_path=None,
        notes=c.notes,
    )
    assert prep_pointer_proposal_from_context(c2) is None


def test_duplicate_paragraphs_from_removed_pairs() -> None:
    a = Paragraph(text="Hello world.", source_line_start=6, source_line_end=6)
    b = Paragraph(text="Hello world.", source_line_start=10, source_line_end=10)
    report = IngestReport(
        title_line_stripped=False,
        duplicates_detected=[DuplicateMatch(a=a, b=b)],
        duplicates_removed=[DuplicateMatch(a=a, b=b)],
        paragraph_count_in=2,
        paragraph_count_out=1,
    )
    dups = duplicate_paragraphs_from_ingest(report)
    assert len(dups) == 1
    assert dups[0]["source_lines"] == [6, 10]
    assert dups[0]["recommended_action"] == "remove_later"
    assert "Hello world" in dups[0]["paragraph_preview"]


def test_build_recap_write_payload_validates() -> None:
    a = Paragraph(text="x", source_line_start=1, source_line_end=1)
    b = Paragraph(text="x", source_line_start=2, source_line_end=2)
    report = IngestReport(
        title_line_stripped=False,
        duplicates_detected=[],
        duplicates_removed=[DuplicateMatch(a=a, b=b)],
        paragraph_count_in=2,
        paragraph_count_out=1,
    )
    payload = build_recap_write_payload_from_ingest(_ctx(), report)
    assert payload["schema_version"] == RECAP_WRITE_SCHEMA_VERSION
    assert payload["recap_preview"]["confirm_token"] == ""
    assert payload["recap_preview"]["mode"] == "create"
    assert validate_recap_write_payload(payload) == []


def test_empty_confirm_token_passes_validator() -> None:
    payload = build_recap_write_payload_from_ingest(
        _ctx(),
        IngestReport(
            title_line_stripped=False,
            duplicates_detected=[],
            duplicates_removed=[],
            paragraph_count_in=0,
            paragraph_count_out=0,
        ),
    )
    assert validate_recap_write_payload(payload) == []
