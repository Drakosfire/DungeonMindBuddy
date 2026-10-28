"""Layout matching preserves selected-source identity and every non-space character."""

import json
from copy import deepcopy
from types import SimpleNamespace

import httpx
import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation import source_quote_binding as quotes
from apps.live_control_server.services import build_jev_writer as writer
from tests.test_build_related_pages import build_case as _build_case


def packet(text, *, policy=quotes.CURRENT_POLICY):
    return {
        quotes.KEY: policy,
        "connected_page_review_policy": "typed_connected_page_review_v1",
        "opened_passages": [
            {"handle": "first", "text": text},
            {"handle": "other", "text": "A different witness."},
        ],
        "exposure": {"saved_sections": []},
    }


def answer(quote, handle="first"):
    return {
        "answer_segments": [
            {
                "kind": "source_passage_claim",
                "text": "A literal witness, not an entailment judgment.",
                "passage_handles": [handle],
                "supporting_quotes": [quote],
            }
        ]
    }


def test_pdf_hard_wrap_case_is_current_layout_only_not_historical_repair():
    source = "During the\nwinter, the keeper and her child tended\nlanterns, exchanging repairs for food and\nlodging."
    quote = "During the winter, the keeper and her child tended lanterns, exchanging repairs for food and lodging."
    value = answer(quote)
    before = deepcopy(value)
    accepted = quotes.validate_and_project(value, packet(source))
    assert "supporting_quotes" not in accepted["answer_segments"][0]
    assert value == before  # No model/source/citation mutation.
    historical = packet(source, policy=quotes.POLICY)
    with pytest.raises(ValueError, match="absent"):
        quotes.validate_and_project(value, historical)
    assert quotes.validate_and_project(answer(source), historical) == accepted


@pytest.mark.parametrize(
    "whitespace", ["\n", "\r\n", "\t", "\u00a0", "\u2003", " \n\t "]
)
def test_unicode_whitespace_layout_is_the_only_equivalence(whitespace):
    text = (
        whitespace + "The" + whitespace + "red" + whitespace + "lantern." + whitespace
    )
    assert quotes.validate_and_project(answer(" The red lantern. "), packet(text))


@pytest.mark.parametrize(
    "quote",
    [
        "the red lantern.",
        "The red lantern!",
        "The blue lantern.",
        "The red-lantern.",
        "The redlantern.",
        "The red \\nlantern.",
        "The red lantern. A different witness.",
        "The red lantérn.",
        "",
        " \t\n",
    ],
)
def test_word_case_punctuation_hyphen_escape_and_cross_source_changes_refused(quote):
    with pytest.raises(ValueError):
        quotes.validate_and_project(answer(quote), packet("The\nred lantern."))


@pytest.mark.parametrize("handle", ["other", "foreign"])
def test_layout_match_never_reselects_a_source(handle):
    with pytest.raises(ValueError, match="absent"):
        quotes.validate_and_project(
            answer("The red lantern.", handle), packet("The\nred lantern.")
        )


def test_no_unicode_compatibility_normalization_or_source_concatenation():
    with pytest.raises(ValueError):
        quotes.validate_and_project(answer("Café"), packet("Cafe\u0301"))
    value = packet("The red")
    value["opened_passages"][1]["text"] = "lantern."
    with pytest.raises(ValueError):
        quotes.validate_and_project(answer("The red lantern."), value)
    assert quotes.format_name("answer", packet("text")) == "answer_quotes_v3"
    historical = packet("text", policy=quotes.POLICY)
    assert quotes.format_name("answer", historical) == "answer"
    historical[quotes.WITNESS_KEY] = quotes.WITNESS_POLICY
    assert quotes.format_name("answer", historical) == "answer_quotes_v2"


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


@pytest.fixture
def completed_layout(build_case, monkeypatch, tmp_path):
    from tests.test_build_related_pages import completed, PagesWriter

    original = PagesWriter.handle_async_request

    async def wrapped(self, request):
        response = await original(self, request)
        body = response.json()
        output = json.loads(body["output"][0]["content"][0]["text"])
        for segment in output["answer_segments"]:
            if "supporting_quotes" in segment:
                segment["supporting_quotes"] = [
                    q.replace(" ", "\n") for q in segment["supporting_quotes"]
                ]
        raw = json.dumps(output)
        self.raw_output = raw
        body["output"][0]["content"][0]["text"] = raw
        return httpx.Response(200, request=request, json=body)

    monkeypatch.setattr(PagesWriter, "handle_async_request", wrapped)
    return completed.__wrapped__(
        build_case, monkeypatch, tmp_path, SimpleNamespace(param="answer_from_sources")
    )


def test_actual_sdk_app_layout_witness_reopens_exact_source_and_strict_format(
    completed_layout,
):
    turn, service, page, body, _, transport, _ = completed_layout
    execution = turn.graph_context_execution
    assert execution.policy.source_quote_binding_policy == quotes.CURRENT_POLICY
    assert len(transport.calls) == 1
    wire = json.loads(transport.calls[0].content)
    input_packet = json.loads(wire["input"])
    assert wire["text"]["format"]["name"].endswith("_quotes_v3")
    from application_state.agent_conversation.source_writer_output import (
        validate_writer_format,
    )

    validate_writer_format(wire["text"]["format"], input_packet)
    with pytest.raises(ValueError, match="quote policy"):
        validate_writer_format(
            {
                **wire["text"]["format"],
                "name": wire["text"]["format"]["name"].replace(
                    "_quotes_v3", "_quotes_v2"
                ),
            },
            input_packet,
        )
    historical = deepcopy(input_packet)
    historical[quotes.KEY] = quotes.POLICY
    with pytest.raises(ValueError, match="quote policy"):
        validate_writer_format(wire["text"]["format"], historical)
    from application_state.agent_conversation.build_related_pages import RelatedPageRead
    from apps.live_control_server.services.build_related_pages import open_page

    (read,) = [e for e in execution.events if isinstance(e, RelatedPageRead)]
    reopened = open_page(service, turn.world_id, turn.turn_id, read.read_id)
    assert reopened["markdown"] == body and reopened["page"]["document_id"] == str(
        page.document_id
    )
    assert "supporting_quotes" not in turn.model_dump_json(by_alias=True)
    assert t.Turn.model_validate_json(turn.model_dump_json(by_alias=True)) == turn
    old = execution.policy.model_dump(mode="json", by_alias=True)
    old["source_quote_binding_policy"] = quotes.POLICY
    assert (
        type(execution.policy)
        .model_validate(old)
        .model_dump(mode="json", by_alias=True)
        == old
    )


def test_current_writer_does_not_dispatch_historical_quote_profile(monkeypatch):
    from apps.live_control_server.services.agent_turn_service import (
        _PolicyExecutionAdapter,
    )
    from application_state.agent_conversation.build_primary_context import DRAFT_POLICY

    policy = SimpleNamespace(
        working_draft_context_policy="captured_build_working_draft_context_v1",
        primary_work_context_policy=DRAFT_POLICY,
        source_quote_binding_policy=quotes.POLICY,
    )
    adapter = SimpleNamespace(
        _is_build_turn=lambda: True,
        failure=None,
        fence=object(),
        _build_writer_projection=SimpleNamespace(
            event_sequence=0, prior_provider_attempt_id=None
        ),
        _broker_execution=lambda: SimpleNamespace(events=[], policy=policy),
        last_provider_attempt_id=None,
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("Historical quote profile reached current dispatch")

    monkeypatch.setattr(writer, "prepared_view", forbidden)
    assert not _PolicyExecutionAdapter.authorize_prepared_build_writer(
        adapter, object()
    )


def test_layout_fence_preserves_every_row(completed_layout, application_state_dsn):
    import psycopg
    from psycopg import sql
    from importlib import import_module

    def rows():
        with psycopg.connect(application_state_dsn) as conn:
            tables = conn.execute(
                "SELECT schemaname,tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY 1,2"
            ).fetchall()
            return {
                (schema, name): conn.execute(
                    sql.SQL(
                        "SELECT row_to_json(t)::text FROM {}.{} t ORDER BY row_to_json(t)::text"
                    ).format(sql.Identifier(schema), sql.Identifier(name))
                ).fetchall()
                for schema, name in tables
            }

    before = rows()
    migration = import_module(
        "application_state.migrations.versions.20261028_0085_build_layout_quote_witnesses"
    )
    migration.upgrade()
    with pytest.raises(RuntimeError, match="recovery forward"):
        migration.downgrade()
    assert rows() == before
