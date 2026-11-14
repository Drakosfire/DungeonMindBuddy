from types import SimpleNamespace

import pytest

from application_state.agent_conversation.native_corpus import bounded_body_section


def test_bounded_body_section_preserves_source_coordinates():
    source = "é\r\n😀\nend"
    catalog = SimpleNamespace(catalog_sha256="a" * 64, body_bytes=len(source.encode()))
    excerpt = SimpleNamespace(
        catalog_sha256=catalog.catalog_sha256,
        section=SimpleNamespace(
            line_start=1, line_end=3, char_start=0, byte_start=0, label="Recap",
        ),
        text=source,
    )

    section, passage = bounded_body_section(catalog, excerpt, line_start=2, line_end=2)
    assert passage == "😀\n"
    assert source[section.char_start:section.char_end] == passage
    assert source.encode()[section.byte_start:section.byte_end] == passage.encode()

    with pytest.raises(ValueError, match="shorter than the full source"):
        bounded_body_section(catalog, excerpt, line_start=1, line_end=3)
    with pytest.raises(ValueError, match="outside"):
        bounded_body_section(catalog, excerpt, line_start=2, line_end=4)


def test_citations_distinguish_passages_from_same_read(monkeypatch):
    from uuid import uuid4
    from application_state.agent_conversation import native_corpus

    from application_state.agent_conversation.native_corpus import (
        body_citation,
        model_body_frame_rows,
        validate_body_support_citations,
    )

    read_id = uuid4()
    producer = uuid4()
    envelope = "a" * 64
    catalog = SimpleNamespace(
        catalog_sha256="b" * 64,
        source=SimpleNamespace(
            artifact=SimpleNamespace(source_artifact_id="source"),
            presentation_name="Recap", campaign_scope="Campaign", session_scope="Session",
            revision=SimpleNamespace(source_artifact_id="source", source_revision_id="revision", content_sha256="c" * 64),
        ),
    )
    text = "alpha\nbeta\n"
    catalog.body_bytes = len(text.encode())
    read = SimpleNamespace(
        event_id=read_id, sequence=1,
        excerpt=SimpleNamespace(
            catalog_sha256=catalog.catalog_sha256, text=text,
            selector_policy="native_full_document_v1",
            planning_ranges=SimpleNamespace(lines=((1, 2),)),
            section=SimpleNamespace(label="Recap", line_start=1, line_end=2,
                                    char_start=0, byte_start=0, byte_end=len(text.encode())),
        ),
    )
    execution = SimpleNamespace(events=())
    monkeypatch.setattr(native_corpus, "acquired_body_reads", lambda _: (read,))
    monkeypatch.setattr(native_corpus, "acquired_body_catalogs", lambda _: {catalog.catalog_sha256: catalog})
    assert native_corpus.body_passage_selection_context(execution) == {
        "r0": {"source": "Recap", "session": "Session", "first_line": 1, "lines": ["alpha\n", "beta\n"]},
    }
    with pytest.raises(ValueError, match="must omit material"):
        native_corpus.resolve_body_passages(execution, [("r0", 1, 1), ("r0", 2, 2)])
    read.excerpt.text += "gamma\n"
    read.excerpt.section.line_end = 3
    read.excerpt.section.byte_end = len(read.excerpt.text.encode())
    catalog.body_bytes = read.excerpt.section.byte_end
    supports = native_corpus.resolve_body_passages(execution, [("r0", 1, 1), ("r0", 2, 2), ("r0", 1, 1)])
    assert [support.passage()[1] for support in supports] == ["alpha\n", "beta\n"]
    with pytest.raises(ValueError, match="unavailable source read"):
        native_corpus.resolve_body_passages(execution, [("r1", 1, 1)])
    frame = model_body_frame_rows(None, (), None, passage_supports=supports[1:])
    [row] = frame["excerpts"]
    assert row["text"] == "beta\n"
    assert row["extent_kind"] == "section"
    assert row["planning_line_ranges"] == [[2, 2]]
    answer = "Both moments matter."
    citations = [
        body_citation(support, index=0, text=answer, producer=producer, envelope_sha256=envelope)
        for support in supports
    ]
    completion = SimpleNamespace(
        native_body_citations=citations, answer_segments=[SimpleNamespace(text=answer)],
    )
    validate_body_support_citations(
        completion, reversed(supports), producer=producer, envelope_sha256=envelope, before_sequence=2,
    )
    citations[0] = citations[0].model_copy(update={"section_id": citations[1].section_id})
    with pytest.raises(ValueError, match="changed its exact source"):
        validate_body_support_citations(
            completion, supports, producer=producer, envelope_sha256=envelope, before_sequence=2,
        )


def test_ranked_passage_recovered_from_covering_read():
    from uuid import uuid4

    from application_state.agent_conversation import native_corpus as bodies
    from application_state.agent_conversation.native_execution import NativePlanOpeningSelectedV1

    text = "outside\nranked evidence\noutside again\n"
    section = SimpleNamespace(
        section_id="ranked", line_start=2, line_end=2, byte_start=8, byte_end=24,
    )
    artifact = SimpleNamespace(source_artifact_id="source")
    revision = SimpleNamespace(
        source_artifact_id="source", source_revision_id="revision", content_sha256="b" * 64,
    )
    catalog = SimpleNamespace(
        catalog_sha256="a" * 64, body_bytes=len(text.encode()), sections=(section,),
        source=SimpleNamespace(artifact=artifact, revision=revision),
    )
    search = bodies.NativeBodySearchObservedV1.model_construct(catalogs=(catalog,))
    opening = NativePlanOpeningSelectedV1.model_construct(
        sequence=1, operation="select_candidates",
        selected_handles=(bodies.native_body_handle(catalog.catalog_sha256, section.section_id),),
    )
    full_read = bodies.NativeBodyReadObservedV1.model_construct(
        event_id=uuid4(), sequence=2,
        excerpt=SimpleNamespace(
            catalog_sha256=catalog.catalog_sha256, text=text,
            section=SimpleNamespace(
                label="Recap", line_start=1, line_end=3, char_start=0,
                byte_start=0, byte_end=len(text.encode()),
            ),
        ),
    )
    execution = SimpleNamespace(events=(search, opening, full_read))
    [support] = bodies.selected_ranked_body_passages(execution)
    assert support.read is full_read
    extent, passage = support.passage()
    assert passage == "ranked evidence\n"
    assert (extent.byte_start, extent.byte_end) == (section.byte_start, section.byte_end)

    from application_state.agent_conversation.native_retrieval import NativeRetrievalSelectedV3

    full_read.excerpt.selector_policy = "native_full_document_v1"
    catalog.source.presentation_name = "Recap"
    catalog.source.campaign_scope = "Campaign"
    catalog.source.session_scope = "Session 1"
    decision = NativeRetrievalSelectedV3.model_construct(
        sequence=3, operation="finish_retrieval", selected_handles=(),
        selected_lines=(("r0", 2), ("r0", 3)),
    )
    execution.events += (decision,)
    selected = bodies.retained_plan_body_passages(execution)
    assert [(item.handle, item.selected_lines, item.passage()[1]) for item in selected] == [
        ("p0", (2, 2), "ranked evidence\n"),
        ("p1", (3, 3), "outside again\n"),
    ]


def test_plan_writer_stops_before_projecting_unselected_full_recap(monkeypatch):
    from application_state.agent_conversation import native_corpus, native_writer, types
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter

    execution = SimpleNamespace(events=(), policy=SimpleNamespace(writer_context_budget=None))
    receipt = types.SurfaceNativeContextReceiptV1.model_construct()
    turn = SimpleNamespace(graph_context_execution=execution, graph_context_receipt=receipt)
    adapter = SimpleNamespace(
        fence=SimpleNamespace(turn=turn),
        budget={"outputReserveTokens": 100, "contextLimitTokens": 1000},
    )
    monkeypatch.setattr(native_corpus, "initial_source_discovery_enabled", lambda _: True)
    monkeypatch.setattr(native_corpus, "body_passage_selection_context", lambda _: {"r0": {}})
    from application_state.agent_conversation import rules_authority_plan_packet
    monkeypatch.setattr(rules_authority_plan_packet, "model_rules_frame", lambda _: {})

    def unexpected_projection(*args, **kwargs):
        pytest.fail("Writer projected an unselected full recap")

    monkeypatch.setattr(native_writer, "model_frame", unexpected_projection)
    with pytest.raises(ValueError, match="requires bounded passages"):
        PlanJevWriter(adapter, {}, SimpleNamespace(frame=lambda: {}))


def test_writer_passage_alias_must_keep_exact_text_and_extent(monkeypatch):
    from application_state.agent_conversation import native_writer

    execution = SimpleNamespace(events=())
    monkeypatch.setattr(native_writer.statements, "selected_read_records", lambda _: ())
    monkeypatch.setattr(native_writer.assertions, "selected_read_records", lambda _: ())
    from application_state.agent_conversation.native_corpus import NativeBodySupport

    text = "first\nsecond\n"
    catalog = SimpleNamespace(catalog_sha256="a" * 64, body_bytes=len(text))
    excerpt = SimpleNamespace(
        catalog_sha256=catalog.catalog_sha256, text=text,
        section=SimpleNamespace(line_start=1, line_end=2, char_start=0, byte_start=0, label="Recap"),
    )
    support = NativeBodySupport("p0", SimpleNamespace(excerpt=excerpt), catalog, (2, 2))
    row = {"excerpt_handle": "body0", "line_start": 2, "line_end": 2, "text": "second\n"}
    frame = {"native_body_evidence": {"excerpts": [row]},
             "native_statements": {"statements": []}, "native_assertions": None}
    [bound] = native_writer.read_evidence_records(execution, frame, passage_supports=(support,))["body_excerpts"]
    assert bound.handle == "body0"
    assert bound.passage() == support.passage()

    row["line_start"] = 1
    with pytest.raises(ValueError, match="exact source evidence"):
        native_writer.read_evidence_records(execution, frame, passage_supports=(support,))


def test_passages_follow_session_and_source_order():
    from application_state.agent_conversation.native_corpus import NativeBodySupport, assemble_body_passages

    def passage(session, start, end):
        text = "first\nsecond\nthird\n"
        catalog = SimpleNamespace(
            catalog_sha256=f"{session:064x}", body_bytes=len(text),
            source=SimpleNamespace(
                campaign_scope="Campaign", session_scope=session,
                revision=SimpleNamespace(source_artifact_id=f"session-{session}",
                                         source_revision_id="rev", content_sha256="a" * 64),
            ),
        )
        excerpt = SimpleNamespace(
            catalog_sha256=catalog.catalog_sha256, text=text,
            section=SimpleNamespace(line_start=1, line_end=3, char_start=0, byte_start=0, label="Recap"),
        )
        return NativeBodySupport("temporary", SimpleNamespace(excerpt=excerpt), catalog, (start, end))

    supports = assemble_body_passages(
        (passage(10, 1, 1), passage(2, 2, 2)),
        (passage(2, 1, 2),),
    )
    assert [(item.handle, item.catalog.source.session_scope, item.passage()[1]) for item in supports] == [
        ("p0", 2, "first\n"),
        ("p1", 2, "second\n"),
        ("p2", 10, "first\n"),
    ]


def test_ranked_coverage_request_uses_json_array():
    from uuid import uuid4

    from application_state.agent_conversation.jev_retrieval_contract import (
        NativePlanPassageDecisionInputV4, prepare_decision,
    )

    parent = NativePlanPassageDecisionInputV4(
        request_id=uuid4(), parent_attempt_id=uuid4(), scope_sha256="0" * 64,
        question="What happened?", candidates=(),
        allowed_operations=("discover_more", "finish_retrieval"),
        source_authority_status="unavailable", source_revision=None, graph_revision=None,
        ranked_passages=("A ranked passage.\n",),
    )
    request = prepare_decision(parent)
    assert request.state["ranked_passages"] == ["A ranked passage.\n"]
    assert [question.name for question in request.questions] == ["operation", "post_read_plan"]


def test_graph_admission_preserves_selected_read_identity():
    from application_state.agent_conversation.native_plan_assertions import (
        NativePlanAssertionReadObservedV1, selected_read_records, writer_admission_indexes,
    )
    from application_state.agent_conversation.native_retrieval import NativeRetrievalSelectedV3

    records = tuple(object() for _ in range(3))
    read = NativePlanAssertionReadObservedV1.model_construct(reads=records)
    decision = NativeRetrievalSelectedV3.model_construct(selected_assertion_indexes=(1,), reviewed_assertion_count=3)
    execution = SimpleNamespace(events=(read, decision))
    assert selected_read_records(execution, admitted_indexes=writer_admission_indexes(execution)) == (
        (read, records[1]),
    )
    assert selected_read_records(execution, admitted_indexes=()) == ()
    with pytest.raises(ValueError, match="acquired assertion rows"):
        selected_read_records(execution, admitted_indexes=(3,))
