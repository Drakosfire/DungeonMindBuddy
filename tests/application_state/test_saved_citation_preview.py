"""Presentation cannot acquire source bodies or grant execution authority."""

from copy import deepcopy
from hashlib import sha256
from uuid import uuid4
import pytest
from application_state.agent_conversation.saved_citation_preview import project
from tests.test_native_plan_assertions import lane as lane


def native_row(surface="build"):
    text = "The source describes the ruined bridge."
    h = "a" * 64
    citation = dict(
        segment_index=0,
        text_sha256=sha256(text.encode()).hexdigest(),
        provider_attempt_id=str(uuid4()),
        envelope_sha256=h,
        read_event_id=str(uuid4()),
        catalog_sha256=h,
        source_artifact_id="source",
        native_source_revision_id="revision",
        content_sha256=h,
        excerpt_sha256=h,
        section_id=h,
        selector_policy="native_full_document_v1",
        source_name="Recap",
        section_title="Full document",
        line_start=1,
        line_end=5,
    )
    completion = dict(
        schema="dmb_surface_native_completion_v1",
        surface_id=surface,
        context_receipt_sha256=h,
        producing_provider_attempt_id=citation["provider_attempt_id"],
        answer_basis="mixed_evidence",
        answer_context_status="source_grounded",
        answer_segments=[dict(kind="source_passage_claim", text=text)],
        collaboration=None,
        saved_source_citations=[],
        native_body_citations=[citation],
        native_clause_citations=[],
        native_assertion_citations=[],
    )
    return dict(
        world_id="world-one",
        surface_id=surface,
        status="completed",
        assistant_text=text,
        completion=completion,
        answer_composition_kind="base",
        rules_summary=None,
        citation_source_basis=None,
    )


@pytest.mark.parametrize("surface", ["build", "plan", "play"])
def test_native_preview_keeps_order_and_drops_authority_and_actions(surface):
    row = native_row(surface)
    row["completion"]["native_body_citations"].append(
        dict(row["completion"]["native_body_citations"][0], read_event_id=str(uuid4()))
    )
    original = deepcopy(row)
    result = project(row)
    assert result["status"] == "ready"
    assert result["native_body_citations"] == row["completion"]["native_body_citations"]
    assert result["answer_segments"] == row["completion"]["answer_segments"]
    assert (
        not {
            "collaboration",
            "execution",
            "context_receipt_sha256",
            "answer_basis",
            "answer_context_status",
        }
        & result.keys()
    )
    assert row == original


@pytest.mark.parametrize("version", [3, 4, 5, 6, 7])
def test_existing_native_citation_families_adopt_their_original_indexes(version):
    row = native_row("plan")
    native = row["completion"]
    c = native["native_body_citations"][0]
    section = {
        k: v for k, v in c.items() if k not in {"catalog_sha256", "selector_policy"}
    }
    section.update(
        catalog_event_id=str(uuid4()),
        app_source_revision_id=str(uuid4()),
        selector_policy="markdown_sections_v1",
    )
    completion = {
        k: native[k]
        for k in [
            "surface_id",
            "context_receipt_sha256",
            "answer_basis",
            "answer_context_status",
            "answer_segments",
        ]
    }
    completion.update(
        schema=f"dmb_surface_evidence_completion_v{version}",
        citation_map=None,
        source_citations=[],
        native_source_citations=[section],
    )
    if version >= 5:
        completion["native_body_citations"] = []
    if version >= 6:
        completion["native_clause_citations"] = []
    if version >= 7:
        completion["native_assertion_citations"] = []
    row["completion"] = completion
    result = project(row)
    assert result["status"] == "ready", result
    assert result["native_source_citations"] == [section]


@pytest.mark.parametrize("marker", ["rules_mixed_v1", "unknown", None])
def test_non_base_compositions_do_not_gain_base_markers(marker):
    row = native_row()
    row["answer_composition_kind"] = marker
    assert project(row)["status"] == "details_required"


@pytest.mark.parametrize("state", ["active", "unused", "failed"])
def test_unaccepted_rules_record_does_not_suppress_base_citations(state):
    row = native_row()
    row["rules_summary"] = dict(state=state, oversized=False, binding=None, seal=None)
    assert project(row)["status"] == "ready"


@pytest.mark.parametrize(
    "summary",
    [
        {},
        True,
        dict(state="accepted", oversized=False, binding=None, seal=None),
        dict(state="active", oversized=True, binding=None, seal=None),
        dict(state="unused", oversized=False, binding={}, seal=None),
        dict(state="failed", oversized=False, binding=None, seal="a" * 64),
    ],
)
def test_invalid_base_rules_authority_keeps_details_fallback(summary):
    row = native_row()
    row["rules_summary"] = summary
    assert project(row)["status"] == "details_required"


@pytest.mark.parametrize(
    "change", ["text", "surface", "citation", "extra", "unopened_legacy", "null"]
)
def test_invalid_or_unsupported_completion_keeps_text_with_details_fallback(change):
    row = native_row()
    if change == "text":
        row["assistant_text"] = "Different answer"
    elif change == "surface":
        row["surface_id"] = "plan"
    elif change == "citation":
        row["completion"]["native_body_citations"][0]["segment_index"] = 4
    elif change == "extra":
        row["completion"]["execute"] = True
    elif change == "unopened_legacy":
        row["completion"] = dict(
            schema="dmb_build_graph_completion_v1", source_opened=False
        )
    else:
        row["completion"] = None
    assert project(row)["status"] == "details_required"


@pytest.mark.parametrize("status", ["accepted", "running", "interrupted", "failed"])
def test_incomplete_attempts_have_no_preview(status):
    row = native_row()
    row["status"] = status
    assert project(row) is None


def test_saved_claim_uses_only_the_actual_source_stamp():
    row = native_row()
    h = "b" * 64
    row["completion"]["answer_segments"] = [
        dict(kind="saved_source_claim", text=row["assistant_text"], content_sha256=h)
    ]
    row["completion"].update(
        native_body_citations=[],
        saved_source_citations=[
            dict(
                segment_index=0,
                text_sha256=sha256(row["assistant_text"].encode()).hexdigest(),
                section_event_ids=[str(uuid4())],
            )
        ],
    )
    row["citation_source_basis"] = dict(
        world_id="world-one",
        document_id="page",
        registry_revision=7,
        content_sha256=h,
        visibility="internal",
    )
    assert project(row)["source_basis"] == row["citation_source_basis"]
    row["citation_source_basis"]["world_id"] = "foreign"
    assert project(row)["status"] == "details_required"


def test_active_snapshot_projects_stored_native_metadata_without_full_turn_reads(
    lane, tmp_path, monkeypatch, application_state_dsn
):
    from application_state.agent_conversation import library, repository
    from tests.test_surface_native_build_ordinary import _fresh_case

    case = _fresh_case(
        lane,
        tmp_path,
        monkeypatch,
        None,
        False,
        False,
        False,
        native_body="direct_support",
        authored_source="full_document",
    )
    pointer = case.service.get_world_pointer(case.world)

    def forbidden(*args, **kwargs):
        raise AssertionError("Full receipt/execution loaded for citation presentation")

    with monkeypatch.context() as patch:
        patch.setattr(repository, "_turn_from_row", forbidden)
        page = library.read_active_messages(case.world)
    assert page["schema"] == "dmb_active_conversation_messages_v2"
    message = page["messages"][0]
    import psycopg

    with psycopg.connect(
        application_state_dsn, options="-c default_transaction_read_only=on"
    ) as conn:
        shape = conn.execute(
            "SELECT answer_composition_kind, EXISTS(SELECT 1 FROM agent.turn_rules_execution r WHERE r.turn_id=t.turn_id) FROM agent.turn t WHERE turn_id=%s",
            (case.turn.turn_id,),
        ).fetchone()
    assert message["citation_preview"]["status"] == "ready", (
        message["citation_preview"],
        shape,
    )
    assert message["citation_preview"]["native_body_citations"] == [
        c.model_dump(mode="json") for c in case.turn.completion.native_body_citations
    ]
    assert message["assistant_text"] == case.turn.assistant_text
    assert case.service.get_world_pointer(case.world) == pointer
    opened = case.client.get(
        f"/api/live/agent/worlds/{case.world}/conversation/turns/{case.turn.turn_id}/native-body-excerpts/0"
    )
    assert (
        opened.status_code == 200
        and opened.json()["citation"]
        == message["citation_preview"]["native_body_citations"][0]
    )
