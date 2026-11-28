"""Actual APP contract boundaries; no network or retained user data."""

import json
from uuid import uuid4
import pytest
from jsonschema import Draft202012Validator
from application_state.agent_conversation import build_intentional_response as c
from application_state.agent_conversation import types as t
from application_state.agent_conversation.source_writer_output import (
    POLICY,
    GAP_POLICY,
    validate_writer_format,
)


def packet(work="discuss"):
    return {
        "source_writer_output_policy": POLICY,
        "requested_detail_gap_policy": GAP_POLICY,
        "user_question": "Hello; shall we begin?",
        "opened_passages": [],
        "exposure": {"saved_sections": []},
        "retrieval_disposition": {
            "status": "insufficient_evidence",
            "coverage_status": "catalog_exhausted",
        },
        "response_contract": json.loads(
            c.canonical(
                c.resolve(
                    work,
                    c.Capabilities(("answer_from_sources",), ("questions",), False),
                )
            )
        ),
    }


def neutral():
    return {
        "answer_context_status": "discussion",
        "answer_segments": [{"kind": "discussion", "text": "Ready when you are."}],
        "limitations": [],
        "requested_detail_gaps": [],
        "collaboration": None,
    }


def test_actual_new_writer_schema_and_normalizer_support_neutral_without_any_draft():
    p, raw = packet(), neutral()
    assert "working_draft_context" not in p
    schema = c.output_schema(p)
    Draft202012Validator(schema).validate(raw)
    validate_writer_format(
        {"type": "json_schema", "name": c.FORMAT, "schema": schema, "strict": True}, p
    )
    result = c.normalize(json.dumps(raw), p)
    assert result["answer_context_status"] == "discussion"
    assert result["answer_segments"] == [
        {"kind": "connective", "text": "Ready when you are."}
    ]
    assert "DraftReferenceClaimV1" not in schema["$defs"]


def test_valid_questions_are_the_whole_response_and_empty_total_response_is_rejected():
    p, raw = packet("clarify_request"), neutral()
    raw["answer_segments"] = []
    raw["collaboration"] = {
        "kind": "questions",
        "questions": [{"text": "Which person should we develop?"}],
    }
    Draft202012Validator(c.output_schema(p)).validate(raw)
    result = c.normalize(json.dumps(raw), p)
    assert (
        result["answer_segments"] == []
        and result["collaboration"] == raw["collaboration"]
    )
    completion = t.BuildIntentionalResponseCompletionV1(
        context_receipt_sha256="a" * 64,
        answer_basis="conversation",
        source_citations=[],
        **result,
    )
    command = t.TurnResult(
        world_id="world",
        conversation_id=uuid4(),
        turn_id=uuid4(),
        expected_revision=1,
        assistant_text="",
        completion=completion,
        producing_provider_attempt_id=uuid4(),
        claim_graph_event_ids={},
    )
    assert command.assistant_text == ""
    raw["collaboration"] = None
    with pytest.raises(ValueError):
        c.normalize(json.dumps(raw), p)


def test_duplicate_inline_questions_and_foreign_review_objects_fail():
    p, raw = packet("clarify_request"), neutral()
    raw["collaboration"] = {
        "kind": "questions",
        "questions": [{"text": raw["answer_segments"][0]["text"]}],
    }
    with pytest.raises(ValueError, match="duplicated"):
        c.normalize(json.dumps(raw), p)
    raw["answer_segments"] = []
    raw["collaboration"] = {
        "kind": "plan",
        "steps": [{"text": "Write.", "kind": "prepare_insertion"}],
    }
    with pytest.raises(ValueError, match="differs"):
        c.normalize(json.dumps(raw), p)


def test_old_format_cannot_gain_new_marker_or_neutral_status():
    p = packet()
    with pytest.raises(ValueError, match="format differs"):
        validate_writer_format({"name": "build_working_draft_answer_v5"}, p)
    with pytest.raises(ValueError):
        t.BuildDraftContextCompletionV1(
            context_receipt_sha256="a" * 64,
            answer_context_status="discussion",
            answer_segments=[{"kind": "connective", "text": "Ready."}],
            source_citations=[],
        )


@pytest.mark.parametrize("work", sorted(c.UNAVAILABLE))
def test_unsupported_actions_remain_creation_without_a_substitute_page_operation(work):
    result = c.resolve(work, c.Capabilities(c.OPERATIONS, c.REVIEWS, True, True))
    assert (
        result["intent_family"] == "create"
        and result["operation"] == "answer_from_sources"
    )
    assert result["purpose"] == "explain_capability"
    assert "prepare_current_page_writing" not in {
        f["id"] for f in result["available_followups"]
    }


def test_changed_resolution_and_uncaptured_draft_claim_fail():
    p = packet()
    p["response_contract"]["operation"] = "propose_build_insertion"
    with pytest.raises(ValueError, match="changed"):
        c.normalize(json.dumps(neutral()), p)
    p, raw = packet(), neutral()
    raw["answer_segments"] = [
        {
            "kind": "draft_reference_claim",
            "text": "A fact.",
            "draft_record_id": str(uuid4()),
        }
    ]
    with pytest.raises(ValueError, match="uncaptured"):
        c.normalize(json.dumps(raw), p)


def run_no_editor(tmp_path, monkeypatch, application_state_dsn, work):
    """Actual packet has no draft; generated text is neither a suggestion nor a gap."""
    from dataclasses import replace
    import httpx
    from tests.test_build_related_pages import build_case, PagesDecision
    from tests.test_build_world_context import world_case
    from tests.test_agent_build_governed_graph import execute
    from tests.test_build_jev_estimated_continuations import counter
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    from application_state.agent_conversation import AgentConversationService
    from tests.application_state.test_agent_conversation_postgres import _new

    case = build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)
    (source, request, bootstrap), _ = world_case(case, monkeypatch)
    service = AgentConversationService()
    conversation = _new(service, "elderwyld")
    question = (
        "Hello; shall we begin?"
        if work == "discuss"
        else "Ask which shop I want to develop."
    )
    request = AgentTurnRequest.model_validate(
        {
            **request.model_dump(mode="json", by_alias=True),
            "turn_id": str(uuid4()),
            "message": question,
            "build_write_capability": None,
            "build_draft_context": None,
        }
    )
    bootstrap = replace(bootstrap, completed_discovery_query=question)

    class NeutralWire(httpx.AsyncBaseTransport):
        def __init__(self):
            self.calls = []

        async def handle_async_request(self, request):
            self.calls.append(request)
            body = json.loads(request.content)
            p = json.loads(body["input"])
            assert "working_draft_context" not in p
            assert body["text"]["format"]["name"] == c.FORMAT
            content = neutral()
            if work == "clarify_request":
                content.update(
                    answer_segments=[],
                    collaboration={
                        "kind": "questions",
                        "questions": [{"text": "Which shop should we develop?"}],
                    },
                )
            raw = json.dumps(content)
            return httpx.Response(
                200,
                request=request,
                json={
                    "id": "resp_neutral",
                    "object": "response",
                    "created_at": 1,
                    "status": "completed",
                    "model": body["model"],
                    "output": [
                        {
                            "type": "message",
                            "id": "msg",
                            "role": "assistant",
                            "status": "completed",
                            "content": [
                                {"type": "output_text", "text": raw, "annotations": []}
                            ],
                        }
                    ],
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 40,
                        "total_tokens": 140,
                    },
                },
            )

    wire, decisions = NeutralWire(), PagesDecision()
    decisions.requested_work = work
    harness = BuildJevHarness(
        world_context=True,
        named_citations=True,
        related_pages=True,
        decision_transport=decisions,
        writer_transport=wire,
        accounting=counter(),
    )
    response = execute(
        (source, request, bootstrap),
        tmp_path,
        harness,
        operator_subject="local_operator",
    )
    assert response.knowledge_context.completion.schema_ == c.COMPLETION
    (turn,) = service.list_turns("elderwyld", conversation.conversation_id)
    assert (
        turn.status == "completed"
        and turn.completion.answer_context_status == "discussion"
    )
    assert turn.assistant_text == ("Ready when you are." if work == "discuss" else "")
    assert turn.completion.answer_basis == "conversation"
    choices = [
        e
        for e in turn.graph_context_execution.events
        if isinstance(e, t.BuildRequestedWorkResolutionV1)
    ]
    assert len(choices) == 1 and choices[0].requested_work == work
    first = json.loads(decisions.calls[0].content)
    interaction=first["state"]["decision"]["state"]["interaction"]
    assert interaction["current_page"]=={"document_id":source.record.document_id,"title":source.record.title}
    assert interaction["current_page_role"]=="descriptive_untrusted_navigation_metadata_not_evidence_or_write_authority"
    assert interaction["working_draft"] is None and interaction["capability_sha256"] is None
    assert len(first["questions"]["requested_work"]["criteria"]) == 14
    assert (
        "operation" not in first["questions"]
        and "cannot_select" not in first["questions"]["requested_work"]["criteria"]
    )
    assert len(wire.calls) == 1

    return turn, service, decisions, wire


@pytest.mark.parametrize("work", ["discuss", "clarify_request"])
def test_no_editor_neutral_reply_survives_real_sdk_app_and_database(
    tmp_path, monkeypatch, application_state_dsn, work
):
    run_no_editor(tmp_path, monkeypatch, application_state_dsn, work)


@pytest.mark.parametrize('base', [False, True])
def test_real_semantic_call_preserves_independent_rules_choice_and_mixed_completion(tmp_path, monkeypatch, application_state_dsn, base):
    import httpx
    import httpx2
    from tests.test_rules_build_parent import build_case, RulesDecisionWire, RulesWriterWire, run_parent
    from apps.live_control_server.services.rules_build_runtime import QUERY_CHOICE
    case = build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)
    class SemanticRulesDecision(RulesDecisionWire):
        async def handle_async_request(self, request):
            response = await super().handle_async_request(request)
            body, data = json.loads(request.content), response.json()
            if 'requested_work' in body['questions']:
                data['answers']['requested_work'].update(choice='discuss', probabilities={key: float(key=='discuss') for key in body['questions']['requested_work']['criteria']})
            return httpx2.Response(200, request=request, json=data)
    class SemanticRulesWriter(RulesWriterWire):
        async def handle_async_request(self, request):
            response = await super().handle_async_request(request)
            body = response.json()
            raw = json.loads(body['output'][0]['content'][0]['text'])
            if raw['base_output'] is not None:
                raw['base_output']['collaboration'] = None
            body['output'][0]['content'][0]['text'] = json.dumps(raw)
            return httpx.Response(200, request=request, json=body)
    completed, adapter, decisions, wire, _ = run_parent(case, tmp_path, monkeypatch,
        decision=SemanticRulesDecision(dsn=application_state_dsn), writer=SemanticRulesWriter(base=base, dsn=application_state_dsn), api_response=True)
    first = json.loads(decisions.calls[0].content)
    assert 'requested_work' in first['questions'] and QUERY_CHOICE in first['questions']
    assert completed.rules_context.accepted_binding.support_table
    assert len(wire.calls) == 1
    if base:
        assert completed.rules_context.base_context.completion.schema_ == c.COMPLETION


def test_current_page_navigation_metadata_is_frozen_without_editor_and_not_provider_mutable(tmp_path,monkeypatch,application_state_dsn):
    from copy import deepcopy
    from apps.live_control_server.services.build_jev_dispatch import validate_body
    turn,service,decisions,_=run_no_editor(tmp_path,monkeypatch,application_state_dsn,"discuss")
    first=json.loads(decisions.calls[0].content)
    changed=deepcopy(first)
    changed["state"]["decision"]["state"]["interaction"]["current_page"]["title"]="Another destination"
    with pytest.raises(ValueError,match="differs"):
        validate_body(json.dumps(changed),first["state"])
    assert service.inspect_turn(world_id=turn.world_id,turn_id=turn.turn_id)==turn


def test_current_page_navigation_refresh_preserves_identity_without_capability():
    from types import SimpleNamespace as S
    from apps.live_control_server.services.build_jev_driver import freeze_interaction
    pointer=S(active_conversation_id=None,revision=0)
    adapter=S(world_id="synthetic",turn=None,budget={},
        request=S(build_write_capability=None,build_draft_context=None,build_authored_references=None),
        service=S(get_world_pointer=lambda _:pointer),work=S(build_source=S(document_id="first",title="Workshop")))
    first=freeze_interaction(adapter)
    adapter.work=S(build_source=S(document_id="second",title="Workshop"))
    second=freeze_interaction(adapter)
    assert first["current_page"]=={"document_id":"first","title":"Workshop"}
    assert second["current_page"]=={"document_id":"second","title":"Workshop"}
    assert first["allowed_operations"]==second["allowed_operations"]==["answer_from_sources"]
    assert first["capability_sha256"] is second["capability_sha256"] is None
    adapter.work=S(build_source=S(document_id="third",title="Newly created workshop"))
    assert freeze_interaction(adapter)["current_page"]=={"document_id":"third","title":"Newly created workshop"}


def test_retained_selection_keeps_exact_probability_inventory():
    retained_menu = c.digest(c.question(guidance=c._RETAINED_GUIDANCE, work_options=c._RETAINED_WORK))
    probabilities = {name: float(name == "discuss") for name in c._RETAINED_WORK}
    response = {"answers": {"requested_work": {"selected": "discuss", "probabilities": probabilities}}}
    assert c.known_semantics(retained_menu, c._resolver_digest(c._RETAINED_WORK))
    assert c.selected(response, menu=retained_menu) == "discuss"
    with pytest.raises(ValueError, match="Invalid actual semantic selection"):
        c.selected(response, menu=c.MENU_DIGEST)
    probabilities["draft_in_conversation"] = 0.0
    with pytest.raises(ValueError, match="Invalid actual semantic selection"):
        c.selected(response, menu=retained_menu)


def test_variant_approval_requires_the_explicit_choice_in_the_new_menu():
    previous = c.digest(c.question(guidance=c._PRE_APPROVAL_GUIDANCE, work_options=c._PRE_APPROVAL_WORK))
    assert c.known_semantics(previous, c._resolver_digest(c._PRE_APPROVAL_WORK))
    assert "review_variant_approval" not in c.decision_instructions(previous)
    assert "review_variant_approval" in c.decision_instructions()

    label = "review_variant_approval"
    response = {"answers": {"requested_work": {
        "selected": label,
        "probabilities": {key: float(key == label) for key in c.WORK},
    }}}
    assert c.selected(response, menu=c.MENU_DIGEST) == label
    with pytest.raises(ValueError):
        c.selected(response, menu=previous)


def test_retained_resolution_uses_the_frozen_work_inventory():
    from dataclasses import asdict
    from types import SimpleNamespace

    operations = ("answer_from_sources",)
    caps = c.Capabilities(operations, ("questions",), False)
    retained_menu = c.digest(c.question(
        guidance=c._RETAINED_GUIDANCE, work_options=c._RETAINED_WORK
    ))
    policy = SimpleNamespace(
        intentional_response_policy=c.POLICY,
        allowed_surface_operations=operations,
        plan_surface_available=False,
        action_capability_sha256=None,
        response_capabilities_sha256=c.digest(asdict(caps)),
        requested_work_menu_sha256=retained_menu,
        response_resolver_sha256=c._resolver_digest(c._RETAINED_WORK),
    )
    digest = c.digest({
        "policy": c.POLICY,
        "work": {label: asdict(work) for label, work in c._RETAINED_WORK.items()},
        "capabilities": asdict(caps),
    })
    saved_resolution = json.loads(c.canonical(c.resolve("discuss", caps)))
    saved_resolution["contract_sha256"] = digest
    event = SimpleNamespace(
        requested_work="discuss",
        intent_family=saved_resolution["intent_family"],
        operation="answer_from_sources",
        capability_sha256=None,
        response_capabilities_sha256=policy.response_capabilities_sha256,
        menu_sha256=retained_menu,
        resolver_sha256=c._resolver_digest(c._RETAINED_WORK),
        resolution=saved_resolution,
    )

    c.validate_resolution_metadata(event, policy)
    assert c.resolve("discuss", caps)["contract_sha256"] != digest
    event.resolution = {**saved_resolution, "contract_sha256": "0" * 64}
    with pytest.raises(ValueError, match="differs from its frozen response contract"):
        c.validate_resolution_metadata(event, policy)


@pytest.mark.parametrize("work", ["review_lore_page", "review_lore_page_from_conversation"])
def test_lore_page_request_cannot_fall_through_to_connected_location_review(work):
    caps = c.Capabilities(("answer_from_sources",), ("connected_page",), False)
    route = c.resolve(work, caps)
    assert route["requested_work"] == work
    assert c.resolve(work, c.Capabilities(("answer_from_sources",), ("lore_page",), False))["barrier"] is None
    assert route["purpose"] == "explain_capability"
    assert route["barrier"] == "requested_review_not_offered"
    assert all(item["id"] != "review_connected_page" for item in route["available_followups"])
    assert c.resolve("review_connected_page", caps)["barrier"] is None

    previous_lore_menu = c.digest(c.question(guidance=c._PRE_CONVERSATION_LORE_GUIDANCE,
                                             work_options=c._PRE_CONVERSATION_LORE_WORK))
    assert c.known_semantics(previous_lore_menu, c._resolver_digest(c._PRE_CONVERSATION_LORE_WORK))

    prior = c.digest(c.question(guidance=c._PRE_LORE_PAGE_GUIDANCE,
                                work_options=c._PRE_LORE_PAGE_WORK))
    assert c.known_semantics(prior, c._resolver_digest(c._PRE_LORE_PAGE_WORK))
    response = {"answers": {"requested_work": {
        "selected": "review_connected_page",
        "probabilities": {key: float(key == "review_connected_page") for key in c._PRE_LORE_PAGE_WORK},
    }}}
    assert c.selected(response, menu=prior) == "review_connected_page"
    with pytest.raises(ValueError, match="Invalid actual semantic selection"):
        c.selected(response, menu=c.MENU_DIGEST)



def test_tied_source_need_does_not_override_build_clarification(monkeypatch):
    monkeypatch.setattr(c, "_captured_semantics", lambda _: (None, None, c.SCOPED_BUILD_MENU_DIGEST, None))
    menu = c.opening_work_question(c.SCOPED_BUILD_MENU_DIGEST)["criteria"]
    request = {"questions": {"source_need": c.source_need_question()}}
    source_vote = {"selected": "uncertain", "probabilities": {
        "anchored": .24, "source_lookup": .38, "uncertain": .38,
    }}

    def response(label):
        return {"answers": {
            "requested_work": {"selected": label, "probabilities": {k: float(k == label) for k in menu}},
            "source_need": source_vote,
        }}

    assert c.opening_work(None, request, response("clarify_request"), None) == (
        "clarify_request", "anchored",
    )
    with pytest.raises(c.UnresolvedDiscussionSource):
        c.opening_work(None, request, response("discuss"), None)
    del source_vote["probabilities"]["anchored"]
    with pytest.raises(ValueError, match="Invalid actual semantic selection"):
        c.opening_work(None, request, response("clarify_request"), None)


def test_opening_intent_requires_the_acknowledged_response(monkeypatch):
    from types import SimpleNamespace

    identity = ("typesafe", "jev-1.14.0", "typesafe_decision")
    policy = SimpleNamespace(provider_roles=SimpleNamespace(
        controller=SimpleNamespace(identity=lambda: identity),
        writer=SimpleNamespace(identity=lambda: ("openai", "writer", "responses")),
    ))
    monkeypatch.setattr(c, "_captured_semantics", lambda _: (None, None, c.SCOPED_BUILD_MENU_DIGEST, None))
    attempt = t.ProviderAttemptAuthorizedEventV5.model_construct(
        context_phase="select", provider_attempt_id=uuid4(), envelope_sha256="a" * 64,
        provider=identity[0], model=identity[1], api_mode=identity[2],
    )
    response = t.ProviderOutcomeEventV1(
        kind="provider_outcome", event_id=uuid4(), sequence=1, provider_attempt_id=attempt.provider_attempt_id,
        outcome="response_received", response_sha256="b" * 64,
    )
    intent = t.BuildOpeningIntentSelectedV1(
        kind="build_opening_intent_selected_v1", event_id=uuid4(), sequence=2,
        controller_attempt_id=attempt.provider_attempt_id, controller_envelope_sha256=attempt.envelope_sha256,
        controller_response_sha256=response.response_sha256, requested_work="discuss",
    )
    c.validate_native_action_events(SimpleNamespace(policy=policy, events=[attempt, response, intent]))

    for events in (
        [attempt, intent],
        [attempt, response, intent.model_copy(update={"controller_envelope_sha256": "c" * 64})],
        [attempt, response, intent, intent],
        [attempt, response, intent.model_copy(update={"requested_work": "not_offered"})],
    ):
        with pytest.raises(ValueError, match="acknowledged controller"):
            c.validate_native_action_events(SimpleNamespace(policy=policy, events=events))


def test_build_followup_offers_paragraph_placement_only_for_page_edit(monkeypatch):
    from types import SimpleNamespace

    from application_state.build_proposal import prose_catalog, prose_decision

    capability = SimpleNamespace(basis=SimpleNamespace(caret=4))
    catalog = object()
    monkeypatch.setattr(prose_catalog, "catalog_for_build_capability", lambda cap: catalog if cap is capability else None)

    def opening(question, title, captured, *, caret):
        assert (question, title, captured, caret) == ("Add a line.", "Edge", catalog, 4)
        return {}, (SimpleNamespace(name="paragraph_work", question="Place text?", options=("place", "skip")),)

    monkeypatch.setattr(prose_decision, "build_boundary_opening", opening)
    state = {"user_question": "Add a line.", "interaction": {"current_page_title": "Edge"}}
    kwargs = {"menu_digest": c.SCOPED_BUILD_MENU_DIGEST, "write_capability": capability}
    discussion = c.build_source_followup_wire(state, "discuss", **kwargs)
    edit = c.build_source_followup_wire(state, "write_current_page", **kwargs)
    assert set(discussion["questions"]) == {"source_need"}
    assert edit["questions"]["paragraph_work"]["criteria"] == {"place": None, "skip": None}
