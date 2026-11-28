"""Plan authoring request capture belongs to its exact ordinary Agent intent."""

from uuid import uuid4
import json
import httpx2

import pytest
from pydantic import ValidationError

from tests.application_state.test_plan_authoring import capture_payload
from tests.test_plan_jev_harness import unavailable_native_sources  # noqa: F401
from tests.test_plan_jev_dispatch import plan_adapter as plan_adapter
from apps.live_control_server.models.agent_turn import AgentTurnRequest
from apps.live_control_server.services.agent_turn_service import _submitted_turn_intent
from application_state.agent_conversation.types import (
    submitted_turn_intent_fingerprint_v2,
)


def request_payload():
    return dict(
        schema="dmb_agent_turn_request_v1",
        client_thread_id=str(uuid4()),
        turn_id=str(uuid4()),
        surface=dict(surface_id="plan", instance_id="surface:plan:a"),
        owner_scope=dict(kind="world", world_id="world:a"),
        primary_work=dict(
            kind="plan",
            object_id="page:a",
            expected_revision=3,
            expected_revision_n=3,
            expected_content_sha256="a" * 64,
        ),
        client_work_state="saved_dirty",
        graph_request={"mode": "none"},
        graph_selection=None,
        plan_context_policy={"policy": "auto_plan_world"},
        plan_authoring_capture=capture_payload(),
        message="Now draft this Plan and preserve the current working note.",
    )


def test_plan_live_capture_participates_in_the_exact_turn_identity():
    payload = request_payload()
    first = AgentTurnRequest.model_validate(payload)
    intent = _submitted_turn_intent(first, world_id="world:a")
    assert intent.plan_authoring_capture_sha256 == first.plan_authoring_capture.sha256
    initial = submitted_turn_intent_fingerprint_v2(intent)
    payload["plan_authoring_capture"]["draft_generation"] += 1
    second = _submitted_turn_intent(
        AgentTurnRequest.model_validate(payload), world_id="world:a"
    )
    assert initial != submitted_turn_intent_fingerprint_v2(second)


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p["plan_authoring_capture"].update(world_id="world:foreign"),
        lambda p: p["plan_authoring_capture"].update(document_id="page:foreign"),
        lambda p: p["plan_authoring_capture"].update(base_revision=2),
        lambda p: p["plan_authoring_capture"].update(base_content_sha256="b" * 64),
        lambda p: p["surface"].update(surface_id="play"),
        lambda p: p.update(plan_context_policy=None),
    ],
)
def test_foreign_or_stale_plan_capture_is_rejected_before_provider_dispatch(change):
    payload = request_payload()
    change(payload)
    with pytest.raises(ValidationError):
        AgentTurnRequest.model_validate(payload)


# Exercise the real GenerationEngine dispatch gate and disposable APP database;
# synthetic transport supplies only the provider response, never an APP receipt.


class SemanticWire(httpx2.AsyncBaseTransport):
    def __init__(self, adapter, choice, compatible_selectors=None, *, expect_examined=True):
        self.adapter, self.choice = adapter, choice
        self.compatible_selectors = compatible_selectors
        self.expect_examined = expect_examined

    async def handle_async_request(self, request):
        body = json.loads(request.content)
        current = self.adapter.service.list_turns(
            "world:one", self.adapter.turn.conversation_id
        )[0]
        from application_state.agent_conversation.native_context import NativePlanRequestAdmissionV1
        opening = type(current.graph_context_receipt.assembled_input) is NativePlanRequestAdmissionV1
        expected_state = {
            "user_request",
            "current_page_title",
            "dialogue_reference",
            "edit_target_available",
            "intent_policy",
            "offered_page_locations",
            "placement_policy",
        }
        if opening:
            expected_state |= {"candidates", "relevance_guidance", "conditional_read_plan_policy"}
            if self.expect_examined:
                expected_state.add("examined_subjects")
        if self.adapter.request.authored_references is not None:
            expected_state.add("author_selected_references")
        if self.adapter.request.plan_requested_operation is not None:
            expected_state.add('plan_requested_operation')
        contextual = 'placement_relation' in body['questions']
        locator = None
        if contextual:
            from application_state.agent_conversation.plan_author_location import explicit_paragraph_locator
            from application_state.agent_conversation.native_plan_opening import NativePlanAuthorScopeObservedV1
            scopes = [event.scope_observation for event in current.graph_context_execution.events
                if type(event) is NativePlanAuthorScopeObservedV1]
            if scopes:
                locator = explicit_paragraph_locator(self.adapter.request.message, scopes[-1].relation)
            expected_state.difference_update({'offered_page_locations', 'intent_policy', 'placement_policy'})
            expected_state.update({'focused_edit_target', 'interpretation_policy',
                'offered_page_anchors', 'placement_relations', 'paragraph_passages',
                'paragraph_sections', 'paragraph_scope_modes', 'section_ancestor_paths', 'scope_qualifier_modes'})
            if locator is not None:
                expected_state.add('existing_paragraph_locator')
                assert body['state']['existing_paragraph_locator'] == locator
            if any(scope.page_edit_intent or scope.requested_work in {"discuss", "clarify"} for scope in scopes):
                expected_state.add('author_page_edit_intent')
                assert body['state']['author_page_edit_intent'] in {'page_edit', 'discussion', 'unresolved'}
        if any(candidate["kind"] == "Explicit admitted full-source read; metadata choice, not evidence"
               for candidate in body["state"].get("candidates", ())):
            expected_state.update({"full_document_selection_guidance", "source_catalogue_guidance"})
        assert set(body["state"]) == expected_state
        assert body["state"]["user_request"] == self.adapter.request.message
        assert body["state"]["edit_target_available"] == (
            self.adapter.request.plan_authoring_capture is not None
        )
        from application_state.agent_conversation import types as t
        from application_state.agent_conversation.plan_authoring import QUESTION_FIRST_INTENT_POLICY,CONNECTED_PAGE_INTENT_POLICY
        expected=CONNECTED_PAGE_INTENT_POLICY if isinstance(self.adapter.request.plan_context_policy,t.PlanContextPolicyV2) else QUESTION_FIRST_INTENT_POLICY
        if not contextual:
            assert body["state"]["intent_policy"] == expected
        expected_questions = {"requested_work"}
        if opening:
            expected_questions |= {"operation", "post_read_plan", *(f"candidate_{i}" for i in range(len(body["state"]["candidates"])))}
        if contextual:
            expected_questions |= {'placement_relation', 'paragraph_scope', 'scope_qualifier', *(f'anchor_{i}'
                for i in range(len(body['state']['offered_page_anchors']))),
                *(f'passage_{i}' for i in range(len(body['state']['paragraph_passages']))),
                *(f'section_{i}' for i in range(len(body['state']['paragraph_sections']))),
                *(f'ancestor_{i}' for i in range(len(body['state']['section_ancestor_paths'])))}
            if locator is not None:
                expected_questions.update(f'locator_passage_{i}' for i in range(len(body['state']['paragraph_passages'])))
        assert set(body["questions"]) == expected_questions
        assert current.graph_context_execution.events[-1].outcome == "sdk_entered"
        choice = self.choice
        if choice == "write_current_page":
            choice = "write:captured" if self.adapter.request.plan_authoring_capture is not None else "write_unavailable"
        target = choice.removeprefix("write:") if choice.startswith("write:") else None
        if contextual and choice.startswith("write:"):
            choice = "write_current_page"
        groups, relation, component_votes = [], 'unresolved', {}
        paragraph_scope = 'not_applicable'
        nominated = self.compatible_selectors if self.compatible_selectors is not None else (target,)
        if contextual:
            from application_state.agent_conversation.plan_contextual_targets import component_inventory
            inventory = component_inventory(self.adapter.request.plan_authoring_capture,
                self.adapter.request.plan_placement_catalog)
            groups = inventory['all']
            selected_entries = [entry for _, entries in groups for entry in entries if entry.selector in nominated]
            if selected_entries:
                kinds = {'captured' if entry.kind == 'captured_target' else entry.kind for entry in selected_entries}
                assert len(kinds) == 1
                relation = kinds.pop()
            selected_anchors = {row['selector'] for row, entries in groups
                if any(entry.selector in nominated for entry in entries)}
            paragraph = relation in {'before_paragraph', 'after_paragraph'}
            if paragraph:
                paragraph_scope = 'unscoped'
            for prefix, entries in [('anchor', inventory['direct']), ('passage', inventory['passages']), ('section', inventory['sections'])]:
                for i, entry in enumerate(entries):
                    applicable = paragraph and prefix == 'passage' or not paragraph and prefix == 'anchor'
                    component_votes[f'{prefix}_{i}'] = ('include' if applicable
                        and selected_anchors.intersection(entry['anchors']) else 'exclude')
            if locator is not None:
                for i in range(len(inventory['passages'])):
                    component_votes[f'locator_passage_{i}'] = component_votes[f'passage_{i}']
        answers = {}
        for name, question in body["questions"].items():
            selected = (component_votes[name] if name in component_votes
                else 'none' if name == 'scope_qualifier'
                else paragraph_scope if name == 'paragraph_scope' else relation if name == 'placement_relation'
                else choice if name == "requested_work" else
                "finish_retrieval" if name == "operation" else
                "review_after_reads" if name == "post_read_plan" else "exclude")
            assert selected in question["criteria"]
            answers[name] = dict(type="choice", choice=selected, confidence=1.0,
                probabilities={option: float(option == selected) for option in question["criteria"]})
        return httpx2.Response(200, request=request, json={
            "model": "jev-1.14.0", "answers": answers,
            "usage": {"input_tokens": 31, "output_tokens": 7},
        })


@pytest.mark.parametrize(
    "choice", ["discuss", "clarify", "write_current_page", "different_destination"]
)
def test_semantic_destination_is_durable_without_granting_edit_authority(
    plan_adapter, choice
):
    import asyncio
    from application_state.agent_conversation import types as t
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch

    dispatch = PlanJevDispatch.requested_work(plan_adapter, page_title="Preparation")
    assert dispatch.parent.schema_ == "dmb_plan_requested_work_input_v7"
    selected, _ = asyncio.run(
        dispatch.run(
            transport=SemanticWire(plan_adapter, choice), api_key="synthetic-not-secret"
        )
    )
    assert selected == choice
    current = plan_adapter.service.list_turns(
        "world:one", plan_adapter.turn.conversation_id
    )[0]
    assert isinstance(current.graph_context_execution.policy, t.PlanAuthoringPolicyV1)
    events = current.graph_context_execution.events
    assert [e.kind for e in events] == [
        "plan_requested_work_authorized_v2",
        "provider_outcome",
        "provider_outcome",
        "plan_requested_work_selected_v2",
    ]
    assert (
        events[-1].requested_work == choice and events[-1].target_capture_sha256 is None
    )
    assert events[-1].actual_input_tokens == 31 and events[-1].actual_output_tokens == 7
    # Missing edit authority is retained as missing; it cannot change write intent
    # to discussion or independently permit a generated placement.
    assert current.status == "running" and current.completion is None
    from tests.test_plan_jev_dispatch import controller, Wire as RetrievalWire

    retrieval = controller(plan_adapter)
    acquired, _ = asyncio.run(
        retrieval.run(
            transport=RetrievalWire(plan_adapter), api_key="synthetic-not-secret"
        )
    )
    assert acquired.operation == "finish_retrieval"
    execution = plan_adapter.fence.turn.graph_context_execution
    if choice == "write_current_page":
        # Even a settled retrieval cannot authorize a writer for a missing target.
        writer = execution.policy.provider_roles.writer
        auth = retrieval.authorization.model_dump(mode="json", by_alias=True)
        for key in ("decision_request_id", "parent_request_sha256"):
            auth.pop(key)
        auth.update(
            kind="plan_jev_writer_authorized_v1",
            sequence=len(execution.events),
            event_id=str(uuid4()),
            provider_attempt_id=str(uuid4()),
            provider=writer.provider,
            model=writer.model,
            api_mode=writer.api_mode,
            frame_sha256="a" * 64,
        )
        payload = execution.model_dump(mode="json", by_alias=True)
        payload["events"].append(auth)
        with pytest.raises(ValueError, match="captured edit target"):
            type(execution).model_validate(payload)
    with pytest.raises(ValueError, match="unique"):
        dispatch.acknowledge(None)


def test_semantic_destination_unknown_outcome_never_resends(plan_adapter):
    import asyncio
    from generationengine import GenerationEngineError
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch

    class Wire(httpx2.AsyncBaseTransport):
        calls = 0

        async def handle_async_request(self, request):
            self.calls += 1
            raise httpx2.ReadTimeout("synthetic unknown outcome", request=request)

    wire = Wire()
    with pytest.raises(GenerationEngineError):
        asyncio.run(
            PlanJevDispatch.requested_work(plan_adapter, page_title="Plan").run(
                transport=wire, api_key="synthetic-not-secret"
            )
        )
    with pytest.raises(GenerationEngineError):
        asyncio.run(
            PlanJevDispatch.requested_work(plan_adapter, page_title="Plan").run(
                transport=wire, api_key="synthetic-not-secret"
            )
        )
    assert wire.calls == 1
    assert (
        plan_adapter.fence.turn.graph_context_execution.events[-1].outcome
        == "outcome_unknown"
    )


def admitted_authoring(plan_adapter, *, admit=True, placement="captured", selected=False):
    """Use actual Content, conversation and provider owners for a live target."""
    import asyncio
    from dataclasses import replace
    from application_state.content.service import create_world_plan, commit_plan
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.plan_authoring import (
        PlanAuthoringCaptureV1, text_digest,
    )
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch

    obj = create_world_plan(title="Preparation", world_id="world:one")
    obj, revision = commit_plan(
        str(obj.work_object_id),
        plan_adapter.work.plan_markdown,
        expected_revision=obj.object_revision,
        expected_world_id="world:one",
    )
    service = plan_adapter.service
    service.new_conversation(
        t.ConversationCommand(
            world_id="world:one",
            command_id=uuid4(),
            expected_pointer_revision=0,
            expected_active_conversation_id=None,
        )
    )
    pointer = service.get_world_pointer("world:one")
    payload = capture_payload()
    payload.update(
        world_id="world:one",
        document_id=str(obj.work_object_id),
        base_revision=obj.object_revision,
        base_content_sha256=revision.content_sha256,
        conversation_id=str(pointer.active_conversation_id),
        expected_pointer_revision=pointer.revision,
    )
    if placement == "under:0":
        editor = json.dumps({"type": "doc", "content": [
            {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Preparation"}]},
            {"type": "paragraph", "content": [{"type": "text", "text": "Existing notes."}]},
        ]}, separators=(",", ":"))
        draft = "## Preparation\n\nExisting notes."
        payload.update(editor_json=editor, editor_sha256=text_digest(editor),
            draft_markdown=draft, draft_sha256=text_digest(draft))
    if selected:

        selection = '{"type":"text","anchor":1,"head":14}'
        payload.update(selection_json=selection, selection_sha256=text_digest(selection),
            target_kind="replace_selection", selected_text="A live draft.", **{"from": 1, "to": 14})
    capture = PlanAuthoringCaptureV1.model_validate(payload)
    basis = plan_adapter.work.content_basis.model_copy(
        update={
            "document_id": str(obj.work_object_id),
            "object_revision": obj.object_revision,
            "work_revision_id": str(revision.work_revision_id),
            "revision_n": revision.revision_n,
            "content_sha256": revision.content_sha256,
        }
    )
    plan_adapter.work = replace(
        plan_adapter.work,
        object_id=str(obj.work_object_id),
        revision=obj.object_revision,
        content_basis=basis,
    )
    primary = plan_adapter.request.primary_work.model_copy(
        update={
            "object_id": str(obj.work_object_id),
            "expected_revision": obj.object_revision,
            "expected_revision_n": revision.revision_n,
            "expected_content_sha256": revision.content_sha256,
        }
    )
    from application_state.agent_conversation.plan_placement import PlanPlacementCatalogV1, PlanPlacementOptionV1
    end = PlanPlacementOptionV1(selector="end",kind="end_page",label="At page end",root_boundary=1,position=15,target_capture_sha256="0"*64)
    if placement == "under:0":
        end = PlanPlacementOptionV1(selector="under:0", kind="after_heading",
            label="Directly below the heading Preparation, before its existing body",
            root_boundary=1, position=13, target_capture_sha256="0"*64)
    captured = PlanPlacementOptionV1(selector="captured", kind="captured_target",
        label="Replace selected text" if selected else "At captured caret",
        root_boundary=None, position=None, target_capture_sha256=capture.sha256)
    entries = (captured,)
    if not selected:
        entries += (end.model_copy(update={"target_capture_sha256": end.derived_target(capture).sha256}),)
    catalog = PlanPlacementCatalogV1(original_capture_sha256=capture.sha256, editor_sha256=capture.editor_sha256,
        entries=entries)
    plan_adapter.request = plan_adapter.request.model_copy(
        update={"primary_work": primary, "plan_authoring_capture": capture, "plan_placement_catalog":catalog}
    )
    plan_adapter.submitted_intent = _submitted_turn_intent(
        plan_adapter.request, world_id="world:one"
    )
    if not admit:
        return capture, None
    dispatch = PlanJevDispatch.requested_work(plan_adapter, page_title="Preparation")
    asyncio.run(
        dispatch.run(
            transport=SemanticWire(plan_adapter, "write:" + placement),
            api_key="synthetic-not-secret",
        )
    )
    return catalog.resolve(capture, placement), plan_adapter.fence.turn


def test_agent_reservation_marks_both_owners_before_commit_and_replays_exactly(
    plan_adapter,
):
    from application_state.plan_action_dialogue.service import PlanActionDialogueService
    from application_state.errors import ApplicationStateValidationError

    capture, turn = admitted_authoring(plan_adapter)
    action, fresh = plan_adapter.service.reserve_plan_authoring_action(
        capture=capture, turn_id=turn.turn_id, expected_revision=turn.revision
    )
    assert fresh and action.status == "pending"
    assert action.authoring_origin.turn_id == turn.turn_id
    assert action.authoring_origin.capture_sha256 == capture.sha256
    assert action.authoring_origin.conversation_id == capture.conversation_id
    duplicate, second_fresh = plan_adapter.service.reserve_plan_authoring_action(
        capture=capture, turn_id=turn.turn_id, expected_revision=turn.revision
    )
    assert not second_fresh and duplicate == action
    with pytest.raises(
        ApplicationStateValidationError, match="atomic turn finalization"
    ):
        PlanActionDialogueService().finish(
            action_id=action.action_id,
            token=action.dispatch_token,
            fence=action.fence,
            status="completed",
            summary="Wrong owner",
        )
    assert (
        plan_adapter.service.list_turns("world:one", turn.conversation_id)[0].status
        == "running"
    )


def _claim_contextual_scope_turn(plan_adapter, *, selected=False):
    from application_state.agent_conversation.native_plan_statements import NativePlanQueryUnavailableV1
    from application_state.agent_conversation.plan_placement import PlanPlacementCatalogV2, PlanPlacementOptionV2
    from application_state.agent_conversation.types import NativeCorpusUnavailableV1, PlanContextPolicyV2

    capture, _ = admitted_authoring(plan_adapter, admit=False, selected=selected)
    catalog = PlanPlacementCatalogV2(original_capture_sha256=capture.sha256,
        editor_sha256=capture.editor_sha256, entries=(PlanPlacementOptionV2(
            selector='captured', kind='captured_target',
            label='Replace only the captured selection' if selected else 'At the captured text caret',
            source_root_index=None, root_boundary=None, position=None, target_capture_sha256=capture.sha256),))
    plan_adapter.request = plan_adapter.request.model_copy(update={'plan_placement_catalog': catalog,
        'plan_context_policy': PlanContextPolicyV2(policy='auto_plan_world', graph_source='reviewed_native_graph')})
    plan_adapter.submitted_intent = _submitted_turn_intent(plan_adapter.request, world_id='world:one')
    plan_adapter.bootstrap = None
    plan_adapter.native_source_authority = NativeCorpusUnavailableV1(
        managed_world_id='world:one', failure_code='native_source_head_unavailable')
    plan_adapter.native_query = NativePlanQueryUnavailableV1(
        managed_world_id='world:one', reason='native_graph_binding_unavailable')
    return capture, plan_adapter.claim_native_plan_request(dialogue=())


def test_author_scope_input_admission_joins_exact_native_turn_without_granting_work(plan_adapter):
    from hashlib import sha256

    from application_state.agent_conversation.native_plan_opening import (
        NativePlanAuthorScopeParentV1, prepare_author_scope_decision,
    )
    from application_state.agent_conversation.native_retrieval import NativePlanAuthorScopeAuthorizedV1
    from application_state.agent_conversation.native_writer import json_container_count
    from application_state.agent_conversation.plan_jev_decision import scope_digest
    from application_state.agent_conversation.types import ProviderOutcomeEventV1
    from application_state.errors import ApplicationStateValidationError

    capture, turn = _claim_contextual_scope_turn(plan_adapter)
    admission = turn.graph_context_receipt.assembled_input
    parent = NativePlanAuthorScopeParentV1(question=turn.user_text, dialogue=(),
        max_span_attempts=2048, quote_context=False, request_id=uuid4(), parent_attempt_id=uuid4(),
        scope_sha256=scope_digest(turn), request_manifest_sha256=admission.manifest_sha256)
    decision = prepare_author_scope_decision(parent)
    payload = {'model': decision.model, 'state': decision.state,
        'questions': {q.name: {'type': 'choice', 'instructions': q.question,
            'criteria': q.option_descriptions} for q in decision.questions}}
    wire = json.dumps(payload, separators=(',', ':'))
    authorization = NativePlanAuthorScopeAuthorizedV1(event_id=uuid4(),
        sequence=len(turn.graph_context_execution.events), decision_request_id=parent.request_id,
        parent_request_sha256=parent.digest, provider_attempt_id=parent.parent_attempt_id,
        provider=decision.provider, model=decision.model, api_mode='decision',
        envelope_sha256=sha256(wire.encode()).hexdigest(), serializer_version='typesafe-sdk-json-v1',
        tool_schema_sha256=sha256(b'[]').hexdigest(), input_accounting_kind='conservative_upper_bound',
        input_estimator=admission.tokenizer_name, input_tokens=len(wire.encode())+64*(1+json_container_count(payload)),
        output_token_reserve=plan_adapter.budget['outputReserveTokens'], included_assertion_ids=[],
        included_relationship_ids=[], included_evidence_ref_ids=[], included_graph_event_ids=[],
        included_source_read_event_ids=[])

    def admit(value):
        return plan_adapter.service.authorize_plan_jev_provider(
            turn.world_id, turn.conversation_id, turn.turn_id, expected_revision=turn.revision,
            expected_attempt=turn.attempt,
            authorization=authorization.model_copy(update={'parent_request_sha256': value.digest}),
            producer_proof={'parent_request_json': value.model_dump_json(by_alias=True), 'request_json': wire})

    foreign = parent.model_copy(update={'request_manifest_sha256': '0' * 64})
    with pytest.raises(ApplicationStateValidationError, match='admitted Plan request or dialogue'):
        admit(foreign)
    forged_focus = parent.model_copy(update={'editor_focus': 'text_selection'})
    with pytest.raises(ApplicationStateValidationError, match='admitted Plan request or dialogue'):
        admit(forged_focus)
    stored, fresh = admit(parent)
    assert fresh
    assert stored.graph_context_execution.events == [*turn.graph_context_execution.events, authorization]
    assert len(stored.graph_context_execution.events) == 1
    assert stored.graph_context_execution.policy.action.intent.plan_authoring_capture_sha256 == capture.sha256
    entered = ProviderOutcomeEventV1(kind='provider_outcome', event_id=uuid4(),
        sequence=1, provider_attempt_id=authorization.provider_attempt_id, outcome='sdk_entered')
    with pytest.raises(ApplicationStateValidationError, match='exact admitted prepared authorization'):
        plan_adapter.service.record_provider_outcome(
            stored.world_id, stored.conversation_id, stored.turn_id,
            expected_revision=stored.revision, expected_attempt=stored.attempt, outcome=entered)


@pytest.mark.parametrize("message, relation, intent, scope_calls", [
    ("Could we add a warning?", "unresolved", "unresolved", 1),
    ("What did the party learn?", "unstated_insertion_location", "discussion", 1),
    ("Insert a warning before that note.", "unstated_insertion_location", "discussion", 2),
])
def test_unscoped_plan_discussion_preserves_recheck_for_concrete_directions(
    plan_adapter, application_state_dsn, message, relation, intent, scope_calls,
):
    import asyncio

    import psycopg

    from application_state.errors import ApplicationStateValidationError
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch
    from apps.live_control_server.services.plan_jev_harness import PlanJevHarness

    plan_adapter.request = plan_adapter.request.model_copy(
        update={"message": message}
    )
    capture, turn = _claim_contextual_scope_turn(plan_adapter)
    requests = []

    async def respond(request):
        wire = json.loads(request.content)
        requests.append(wire)
        assert not wire["state"]["scope_hypotheses"]
        choices = {
            "location_relation": relation,
            "existing_scope": "none",
            "page_edit_intent": intent,
        }
        answers = {
            name: {
                "type": "choice",
                "choice": choice,
                "confidence": 1.0,
                "probabilities": {
                    key: float(key == choice)
                    for key in wire["questions"][name]["criteria"]
                },
            }
            for name, choice in choices.items()
        }
        return httpx2.Response(200, json={
            "model": wire["model"], "answers": answers,
            "usage": {"input_tokens": 40, "output_tokens": 9},
        })

    harness = PlanJevHarness(
        decision_transport=httpx2.MockTransport(respond),
        decision_api_key="synthetic-not-secret",
    )
    first = harness._interpret_author_scope(plan_adapter, (), [])
    assert len(requests) == scope_calls
    assert first.scope_observation.relation == relation
    opening = PlanJevDispatch.requested_work(
        plan_adapter, page_title="Preparation", author_scope=first,
    )
    work, _ = asyncio.run(opening.run(
        transport=SemanticWire(plan_adapter, "write:captured", expect_examined=False),
        api_key="synthetic-not-secret",
    ))
    confirmed = plan_adapter.service.list_turns(turn.world_id, turn.conversation_id)[0]
    selection = confirmed.graph_context_execution.events[-1]
    assert work == ("discuss" if intent == "discussion" else "clarify")
    assert selection.author_scope_binding.observation_event_id == first.event_id
    assert selection.author_scope_binding.page_edit_intent == intent
    assert selection.placement_selector is None and selection.target_capture_sha256 is None
    with pytest.raises(ApplicationStateValidationError, match="frozen destination or target"):
        plan_adapter.service.reserve_plan_authoring_action(
            capture=capture, turn_id=turn.turn_id, expected_revision=confirmed.revision,
        )
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM plan_action.action").fetchone()[0] == 0


@pytest.mark.parametrize('provider_case', [
    'success', 'disagreeing_recheck', 'capture_rewrite_recheck', 'substituted_observation', 'unknown_outcome',
    'discussion_veto', 'edit_permission_disagreement', 'explicit_editor_operation',
    'implicit_caret_request', 'deictic_selection_request',
])
def test_source_blind_sdk_records_only_its_actual_native_scope_observation(
        plan_adapter, monkeypatch, application_state_dsn, provider_case):
    import asyncio

    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch
    from application_state.agent_conversation.native_plan_opening import (
        NativePlanAuthorScopeObservedV1, require_retained_author_scope,
    )
    from application_state.agent_conversation.plan_author_location import UnscopedLocation
    from application_state.agent_conversation.plan_jev_decision import current_selection
    from application_state.errors import ApplicationStateValidationError
    from generationengine import GenerationEngineError

    if provider_case in {'discussion_veto', 'edit_permission_disagreement'}:
        message = 'Would a warning at the caret be too direct? I am asking for feedback first.'
    elif provider_case == 'capture_rewrite_recheck':
        message = 'Rewrite only the selected sentence to retain its meaning and add a precaution.'
    else:
        message = 'Add a note at the caret and mention the Equipment section.'
    if provider_case == 'implicit_caret_request':
        message = ('Add what the players see and hear at the boardwalk. '
                   'Give me a private reminder to leave the tower sealed unless the players investigate.')
    selected = provider_case == 'deictic_selection_request'
    if selected:
        message = 'Rewrite this to emphasize the three lanterns.'
    ordinary_relation = {
        'deictic_selection_request': 'replace_explicit_selection',
        'implicit_caret_request': 'unstated_insertion_location',
    }.get(provider_case, 'insert_at_explicit_caret')
    operation = 'write_current_page' if provider_case == 'explicit_editor_operation' else None
    request_fields = {'message': message, 'plan_requested_operation': operation}
    if operation is not None:
        from application_state.agent_conversation.types import PlanContextPolicyV2

        request_fields['plan_context_policy'] = PlanContextPolicyV2(
            policy='auto_plan_world', graph_source='reviewed_native_graph')
    plan_adapter.request = plan_adapter.request.model_copy(update=request_fields)
    capture, turn = _claim_contextual_scope_turn(plan_adapter, selected=selected)
    if provider_case in {'disagreeing_recheck', 'capture_rewrite_recheck'}:
        plan_adapter.fence.begin_plan_opening()
        assert plan_adapter.fence.renewer._session is not None
    dispatch = PlanJevDispatch.author_scope(plan_adapter)
    requests = []
    if provider_case == 'substituted_observation':
        append = plan_adapter.fence.append

        def substitute(method, label, event, **extras):
            if type(event) is NativePlanAuthorScopeObservedV1:
                changed = event.scope_observation.model_copy(update={'relation': 'after_heading'})
                event = event.model_copy(update={'scope_observation': changed})
            return append(method, label, event, **extras)

        monkeypatch.setattr(plan_adapter.fence, 'append', substitute)

    async def respond(request):
        requests.append(request)
        current = plan_adapter.service.list_turns(turn.world_id, turn.conversation_id)[0]
        assert current.graph_context_execution.events[-1].outcome == 'sdk_entered'
        wire = json.loads(request.content)
        expected = {'current_request', 'dialogue', 'scope_hypotheses', 'current_editor_focus'}
        focus = wire['state']['current_editor_focus']
        assert ('selected existing text' if selected else 'has a text caret') in focus
        if not selected:
            assert "First determine the requested work" in focus
        assert "caret_guidance_version" not in request.content.decode()
        if selected:
            assert capture.selected_text not in request.content.decode()
        assert capture.document_id not in request.content.decode()
        if operation is not None:
            expected.add('explicit_editor_operation')
            assert wire['state']['explicit_editor_operation'] == operation
        assert set(wire['state']) == expected
        assert turn.world_id not in request.content.decode()
        if provider_case == 'unknown_outcome':
            raise httpx2.ReadTimeout('synthetic unknown outcome', request=request)
        assert all(('text_before' in row['author_quote']) == (len(requests) == 2)
            for row in wire['state']['scope_hypotheses'].values())
        relation = ('after_paragraph' if provider_case == 'capture_rewrite_recheck' else
            'after_heading' if len(requests) == 2 and provider_case == 'disagreeing_recheck'
            else ordinary_relation)
        permission = ('discussion' if provider_case == 'discussion_veto'
            or (provider_case == 'edit_permission_disagreement' and len(requests) == 2) else 'page_edit')
        selections = {'location_relation': relation, 'existing_scope': 'none', 'page_edit_intent': permission}
        answers = {name: {'type': 'choice', 'choice': selected, 'confidence': 1.0,
            'probabilities': {key: float(key == selected) for key in wire['questions'][name]['criteria']}}
            for name, selected in selections.items()}
        return httpx2.Response(200, request=request, json={'model': wire['model'], 'answers': answers,
            'usage': {'input_tokens': 40, 'output_tokens': 9}})

    def run():
        return asyncio.run(dispatch.run(
            transport=httpx2.MockTransport(respond), api_key='synthetic-not-secret'))

    if provider_case == 'unknown_outcome':
        with pytest.raises(GenerationEngineError):
            run()
    elif provider_case == 'substituted_observation':
        with pytest.raises(ApplicationStateValidationError, match='differs from its exact SDK result'):
            run()
    else:
        observation, result = run()
    current = plan_adapter.service.list_turns(turn.world_id, turn.conversation_id)[0]
    events = current.graph_context_execution.events
    assert len(requests) == 1
    if provider_case in {'unknown_outcome', 'substituted_observation'}:
        assert len(events) == 3
        assert events[-1].outcome == ('outcome_unknown' if provider_case == 'unknown_outcome' else 'response_received')
        return
    assert [e.kind for e in events] == ['native_plan_author_scope_authorized_v1',
        'provider_outcome', 'provider_outcome', 'native_plan_author_scope_observed_v1']
    assert type(events[-1]) is NativePlanAuthorScopeObservedV1
    assert events[-1].scope_observation == observation
    assert observation.relation == ('after_paragraph' if provider_case == 'capture_rewrite_recheck'
        else ordinary_relation)
    assert observation.scope == UnscopedLocation()
    assert events[-1].actual_output_tokens == result.observation.output_tokens == 9
    assert require_retained_author_scope(current.graph_context_execution, events[-1].event_id, observation) == events[-1]
    with pytest.raises(ValueError, match='exact retained author observation'):
        require_retained_author_scope(current.graph_context_execution, uuid4(), observation)
    with pytest.raises(ValueError, match='exact retained author observation'):
        require_retained_author_scope(current.graph_context_execution, events[-1].event_id,
            observation.model_copy(update={'relation': 'after_heading'}))
    with pytest.raises(ValueError, match='no longer current'):
        current_selection(current)
    second = PlanJevDispatch.author_scope(plan_adapter, prior_scope=events[-1])
    asyncio.run(second.run(transport=httpx2.MockTransport(respond), api_key='synthetic-not-secret'))
    assert len(requests) == 2
    assert second.authorization.prior_scope_event_id == events[-1].event_id
    opening_scope = second.selection_event
    opening = PlanJevDispatch.requested_work(plan_adapter, page_title='Preparation',
        author_scope=opening_scope)
    if provider_case in {'disagreeing_recheck', 'capture_rewrite_recheck'}:
        async def no_opening(_):
            pytest.fail('Disagreeing author observations cannot enter the opening transport')

        with pytest.raises(GenerationEngineError):
            asyncio.run(opening.run(transport=httpx2.MockTransport(no_opening), api_key='synthetic-not-secret'))
        denied = plan_adapter.service.list_turns(turn.world_id, turn.conversation_id)[0]
        assert denied.graph_context_execution.events[-1] == second.selection_event
        assert plan_adapter.fence.renewer._session is None
        review = PlanJevDispatch.author_scope(plan_adapter, review_scope=(events[-1], second.selection_event))

        async def adjudicate(request):
            wire = json.loads(request.content)
            assert set(wire['state']) == {'current_request', 'dialogue', 'current_editor_focus'}
            assert str(events[-1].event_id) not in request.content.decode()
            criteria = wire['questions']['adjudicated_scope']['criteria']
            desired = 'Replace the selected text' if provider_case == 'capture_rewrite_recheck' else 'Insert at the caret'
            choice = next(key for key, value in criteria.items()
                if key != 'unresolved' and json.loads(value)['relation'].startswith(desired))
            return httpx2.Response(200, request=request, json={'model': wire['model'], 'answers': {
                'adjudicated_scope': {'type': 'choice', 'choice': choice, 'confidence': 1.0,
                    'probabilities': {key: float(key == choice) for key in criteria}}},
                'usage': {'input_tokens': 25, 'output_tokens': 6}})

        scope, _ = asyncio.run(review.run(transport=httpx2.MockTransport(adjudicate),
            api_key='synthetic-not-secret'))
        assert scope.relation == ('replace_explicit_selection' if provider_case == 'capture_rewrite_recheck'
            else 'insert_at_explicit_caret')
        assert review.authorization.scope_review_event_ids == (events[-1].event_id, second.selection_event.event_id)
        opening_scope = review.selection_event
        opening = PlanJevDispatch.requested_work(plan_adapter, page_title='Preparation', author_scope=opening_scope)
    work, _ = asyncio.run(opening.run(
        transport=SemanticWire(plan_adapter, 'write:captured', expect_examined=False),
        api_key='synthetic-not-secret'))
    confirmed = plan_adapter.service.list_turns(turn.world_id, turn.conversation_id)[0]
    selection = confirmed.graph_context_execution.events[-1]
    assert selection.author_scope_binding.observation_event_id == opening_scope.event_id
    if provider_case in {'discussion_veto', 'edit_permission_disagreement'}:
        import psycopg

        discuss = provider_case == 'discussion_veto'
        assert selection.author_scope_binding.page_edit_intent == ('discussion' if discuss else 'unresolved')
        assert selection.requested_intent == 'write_current_page'
        assert work == ('discuss' if discuss else 'clarify')
        assert selection.placement_selector is None and selection.target_capture_sha256 is None
        capture = confirmed.graph_context_execution.policy.action.authoring_capture
        with pytest.raises(ApplicationStateValidationError, match='frozen destination or target'):
            plan_adapter.service.reserve_plan_authoring_action(
                capture=capture, turn_id=confirmed.turn_id, expected_revision=confirmed.revision)
        with psycopg.connect(application_state_dsn) as conn:
            assert conn.execute('SELECT count(*) FROM plan_action.action').fetchone()[0] == 0
        return
    assert selection.author_scope_binding.page_edit_intent == 'page_edit'
    if provider_case == 'capture_rewrite_recheck':
        assert confirmed.graph_context_execution.policy.action.authoring_capture.target_kind == 'insert_at_caret'
        assert work == 'clarify'
        assert selection.placement_selector is None
        assert selection.target_capture_sha256 is None
        return
    assert work == 'write_current_page'
    assert selection.placement_selector == 'captured'
    assert selection.target_capture_sha256 == current.graph_context_execution.policy.action.authoring_capture.sha256


@pytest.mark.parametrize("mutation", ["content", "turn_revision", "capture", "pointer"])
def test_rejected_authoring_reservation_rolls_back_its_pending_action(
    plan_adapter, application_state_dsn, mutation
):
    import psycopg
    from application_state.errors import (
        ApplicationStateConflictError,
        ApplicationStateValidationError,
    )
    from application_state.agent_conversation import types as t
    from application_state.content.service import commit_plan

    capture, turn = admitted_authoring(plan_adapter)
    expected = turn.revision
    if mutation == "content":
        commit_plan(
            capture.document_id,
            "A newer saved Plan.",
            expected_revision=capture.base_revision,
            expected_world_id=capture.world_id,
        )
    elif mutation == "turn_revision":
        expected -= 1
    elif mutation == "capture":
        capture = capture.model_copy(
            update={"draft_generation": capture.draft_generation + 1}
        )
    else:
        plan_adapter.service.new_conversation(
            t.ConversationCommand(
                world_id=capture.world_id,
                command_id=uuid4(),
                expected_pointer_revision=capture.expected_pointer_revision,
                expected_active_conversation_id=capture.conversation_id,
            )
        )
    with pytest.raises(
        (ApplicationStateConflictError, ApplicationStateValidationError)
    ):
        plan_adapter.service.reserve_plan_authoring_action(
            capture=capture, turn_id=turn.turn_id, expected_revision=expected
        )
    with psycopg.connect(application_state_dsn) as conn:
        assert (
            conn.execute("SELECT count(*) FROM plan_action.action").fetchone()[0] == 0
        )


def test_competing_authoring_reservations_share_one_immutable_action(plan_adapter):
    from concurrent.futures import ThreadPoolExecutor

    capture, turn = admitted_authoring(plan_adapter)

    def reserve(_):
        return plan_adapter.service.reserve_plan_authoring_action(
            capture=capture, turn_id=turn.turn_id, expected_revision=turn.revision
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, range(2)))
    assert sum(fresh for _, fresh in results) == 1
    assert results[0][0].action_id == results[1][0].action_id
    assert results[0][0].authoring_origin == results[1][0].authoring_origin


@pytest.mark.parametrize(
    "change",
    [
        {"requested_work": "write_current_page"},
        {"target_capture_sha256": "a" * 64},
        {"actual_input_tokens": 32},
        {"original_capture_sha256": "c" * 64},
        {"placement_catalog_sha256": "d" * 64},
        {"placement_selector": "end"},
    ],
)
def test_semantic_projection_cannot_change_the_captured_provider_answer(
    plan_adapter, change
):
    import asyncio
    from application_state.errors import ApplicationStateValidationError
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch

    dispatch = PlanJevDispatch.requested_work(plan_adapter, page_title="Preparation")
    _, result = asyncio.run(
        dispatch.run(
            transport=SemanticWire(plan_adapter, "discuss"),
            api_key="synthetic-not-secret",
        )
    )
    turn = plan_adapter.fence.turn
    event = turn.graph_context_execution.events[-1].model_copy(
        update=change
        | {"event_id": uuid4(), "sequence": len(turn.graph_context_execution.events)}
    )
    with pytest.raises(ApplicationStateValidationError, match="Plan"):
        plan_adapter.service.record_plan_requested_work_selection(
            turn.world_id,
            turn.conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
            expected_attempt=turn.attempt,
            selection=event,
            producer_proof={
                "parent_request_json": dispatch.parent.model_dump_json(by_alias=True),
                "request_json": dispatch.prepared.body.decode(),
                "response_json": result.model_dump_json(),
            },
        )
    assert (
        plan_adapter.service.list_turns(turn.world_id, turn.conversation_id)[0].revision
        == turn.revision
    )


def authoring_writer(plan_adapter, *, rules_used=False, graph_used=True, placement="captured"):
    import asyncio
    from application_state.agent_conversation.rules_authority_policy import (
        rules_capability,
    )
    from graph_memory.interaction.session import GraphReferent
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    from apps.live_control_server.services.plan_jev_rules_runtime import (
        PlanRulesRuntime,
    )
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from tests.test_plan_jev_driver import Decisions, fixture_reads

    if rules_used:
        from tests.test_rules_lookup_broker import args

        plan_adapter.request = plan_adapter.request.model_copy(
            update={"message": args().question}
        )
    capture, turn = admitted_authoring(plan_adapter, placement=placement)
    action, _ = plan_adapter.service.reserve_plan_authoring_action(
        capture=capture, turn_id=turn.turn_id, expected_revision=turn.revision
    )
    if graph_used:
        plan_adapter.bootstrap.retrieval_session.referents = [
            GraphReferent(id="pond", label="Park pond")
        ]
        fixture_reads(plan_adapter)
    rules = PlanRulesRuntime(plan_adapter, rules_capability(graph=True))
    rules.authoring = (action, capture)
    driver = PlanJevDriver(plan_adapter, rules=rules if rules_used else None)
    proof = asyncio.run(
        driver.run(transport=Decisions(), api_key="synthetic-not-secret")
    )
    return PlanJevWriter(plan_adapter, proof, rules), action, capture


@pytest.mark.parametrize("source_root", [False, True])
@pytest.mark.parametrize("mode", ["base", "rules_only", "mixed"])
def test_one_writer_atomically_stores_plan_result_and_exact_replay(
    plan_adapter, mode, monkeypatch, source_root
):
    import asyncio
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.rules_authority_reads import (
        MixedCompletedTurnV1,
    )
    from application_state.plan_action_dialogue.service import PlanActionDialogueService
    from application_state.agent_conversation.plan_authoring import (
        PlanActionAuthoringResultV1,
    )
    from application_state.content.service import commit_plan
    from tests.test_plan_jev_writer import WriterWire, graph_answer

    if source_root:
        plan_adapter.native_source_authority=t.NativeCorpusUnavailableV1(
            managed_world_id=plan_adapter.world_id,failure_code='native_source_head_unavailable')
    writer, action, capture = authoring_writer(
        plan_adapter, rules_used=mode != "base", graph_used=mode != "rules_only"
    )
    answer = graph_answer()
    answer["schema"] = writer.projection.frame["answer_policy"]
    answer["answer_segments"].append(
        {
            "kind": "proposal",
            "label": "invented_idea",
            "text": "## Possible approach\n\n| Lead | Follow-up |\n| --- | --- |\n| Pond | Ask about access. |",
        }
    )
    if mode != "base":
        support = json.loads(writer.messages[1]["content"])["supports"][0]
        assert writer.output_format['schema']['properties']['kind']['const'] == 'rules_answer'
        answer = {
            "kind": "rules_answer",
            "base_output": None if mode == "rules_only" else answer,
            "rules_segments": [
                {
                    "kind": "rules_claim",
                    "text": support['excerpt_text'],
                    "support_ids": [support['support_id']],
                }
            ],
            "ordered_refs": (
                [{"domain": "base", "segment_index": None}] if mode == "mixed" else []
            )
            + [{"domain": "rules", "segment_index": 0}],
        }
    method = (
        "complete_plan_authoring_turn"
        if mode == "base"
        else "complete_plan_authoring_mixed_turn"
    )
    original = getattr(plan_adapter.service, method)
    accepted = []

    def complete(result, **kwargs):
        accepted.append((result, kwargs))
        return original(result, **kwargs)

    monkeypatch.setattr(plan_adapter.service, method, complete)
    wire = WriterWire(plan_adapter, json.dumps(answer))
    completed = asyncio.run(writer.run(transport=wire, api_key="synthetic-not-secret"))
    assert len(wire.calls) == 1 and len(accepted) == 1
    actual_request = json.loads(wire.calls[0].content)
    frame = json.loads(actual_request["input"][0]["content"])
    assert frame["current_page_draft"] == {
        "state": "unsaved_working_draft",
        "primary_authoring_context": True,
        "markdown": capture.draft_markdown,
    }
    assert frame["focused_edit_target"] == {"kind": "insert_at_caret", "location":"At captured caret"}
    assert actual_request["input"][0]["content"].count(capture.draft_markdown) == 1
    assert (
        "Prepare only the requested editable Plan fragment"
        in actual_request["instructions"]
    )
    assert "No edit or generation happened." not in actual_request["instructions"]
    envelope = (
        completed.envelope if isinstance(completed, MixedCompletedTurnV1) else completed
    )
    assert envelope.status == "completed"
    stored = PlanActionDialogueService().get_by_key(
        capture.world_id, capture.idempotency_key
    )
    assert stored.status == "completed" and isinstance(
        stored.authoring_origin, PlanActionAuthoringResultV1
    )
    assert stored.authoring_origin.expected_turn_revision + 1 == envelope.revision
    proposal = plan_adapter.service.get_plan_authoring_proposal(
        capture.world_id, action.action_id
    )
    from apps.live_control_server.services.agent_turn_service import (
        project_plan_authoring_proposal,
    )

    assert (
        project_plan_authoring_proposal(completed, service=plan_adapter.service)
        == proposal
    )
    assert proposal == accepted[0][1]["proposal"]
    assert proposal.capture == capture
    from apps.live_control_server.routes import agent as agent_route

    monkeypatch.setattr(agent_route, "enforce_native_graph_gm", lambda request: None)
    monkeypatch.setattr(agent_route, "_verified_world_id", lambda world: world)
    monkeypatch.setattr(
        agent_route, "_conversation_service", lambda request: plan_adapter.service
    )
    history = agent_route.get_world_conversation_history(
        capture.world_id,
        None,
        limit=10,
        before_sequence=None,
        include_turn_correlation=True,
    )
    assert history.turns[0].plan_proposal == proposal
    assert history.turns[0].turn_id == envelope.turn_id
    if mode == "rules_only":
        assert (
            isinstance(completed, MixedCompletedTurnV1)
            and completed.base_projection.kind == "unclaimed"
        )
        assert proposal.replacement_markdown == support['excerpt_text']
    else:
        assert "| Lead | Follow-up |" in proposal.replacement_markdown
        assert "\n\n## Possible approach" in proposal.replacement_markdown
    # Exact result replay remains available after the author moves on. It is not
    # another dispatch, an edit to the newer Plan, or a requirement to reactivate
    # the archived conversation.
    plan_adapter.service.new_conversation(
        t.ConversationCommand(
            world_id=capture.world_id,
            command_id=uuid4(),
            expected_pointer_revision=capture.expected_pointer_revision,
            expected_active_conversation_id=capture.conversation_id,
        )
    )
    commit_plan(
        capture.document_id,
        "A newer saved Plan.",
        expected_revision=capture.base_revision,
        expected_world_id=capture.world_id,
    )
    assert original(accepted[0][0], **accepted[0][1]) == completed
    assert (
        project_plan_authoring_proposal(completed, service=plan_adapter.service)
        == proposal
    )
    assert (
        plan_adapter.service.get_plan_authoring_proposal(
            capture.world_id, action.action_id
        )
        == proposal
    )
    assert len(wire.calls) == 1


@pytest.mark.parametrize(
    "case",
    [
        "terminal_cas",
        "generic_finish",
        "later_save",
        "switch_chat",
        "stale_before_send",
    ],
)
def test_authoring_failure_and_navigation_boundaries_keep_ownership(
    plan_adapter, application_state_dsn, monkeypatch, case
):
    import asyncio
    import psycopg
    from application_state.agent_conversation import types as t
    from application_state.content.service import commit_plan, snapshot_content
    from application_state.errors import (
        ApplicationStateConflictError,
        ApplicationStateValidationError,
    )
    from application_state.plan_action_dialogue import repository as actions
    from application_state.plan_action_dialogue.service import PlanActionDialogueService
    from tests.test_plan_jev_writer import WriterWire, graph_answer

    writer, action, capture = authoring_writer(plan_adapter)
    if case == "terminal_cas":
        original = actions.finish_authoring_result

        def lose_fence(conn, *args):
            conn.execute(
                "UPDATE plan_action.action SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE action_id=%s",
                (action.action_id,),
            )
            return original(conn, *args)

        monkeypatch.setattr(actions, "finish_authoring_result", lose_fence)
    elif case == "generic_finish":

        def wrong_owner(result, *, proposal, output_proof, expected_rules_revision):
            return plan_adapter.service.complete_native_base_turn(
                result,
                output_proof=output_proof,
                expected_rules_revision=expected_rules_revision,
            )

        monkeypatch.setattr(
            plan_adapter.service, "complete_plan_authoring_turn", wrong_owner
        )

    def newer_plan():
        commit_plan(
            capture.document_id,
            "A newer author edit.",
            expected_revision=capture.base_revision,
            expected_world_id=capture.world_id,
        )

    if case == "stale_before_send":
        newer_plan()

    class Wire(WriterWire):
        async def handle_async_request(self, request):
            if case == "later_save":
                newer_plan()
            elif case == "switch_chat":
                plan_adapter.service.new_conversation(
                    t.ConversationCommand(
                        world_id=capture.world_id,
                        command_id=uuid4(),
                        expected_pointer_revision=capture.expected_pointer_revision,
                        expected_active_conversation_id=capture.conversation_id,
                    )
                )
            return await super().handle_async_request(request)

    wire = Wire(plan_adapter, json.dumps(graph_answer()))
    if case in {"terminal_cas", "generic_finish", "stale_before_send"}:
        # The real GenEngine gate wraps pre-send authorization errors; post-send
        # atomic failures retain their actual APP error.
        if case == "stale_before_send":
            from generationengine import GenerationEngineError

            expected = (GenerationEngineError, ApplicationStateConflictError)
        else:
            expected = (ApplicationStateConflictError, ApplicationStateValidationError)
        with pytest.raises(expected):
            asyncio.run(writer.run(transport=wire, api_key="synthetic-not-secret"))
        assert len(wire.calls) == (0 if case == "stale_before_send" else 1)
        assert (
            plan_adapter.service.list_turns(capture.world_id, capture.conversation_id)[
                0
            ].status
            == "running"
        )
        assert (
            plan_adapter.service.get_plan_authoring_proposal(
                capture.world_id, action.action_id
            )
            is None
        )
        with psycopg.connect(application_state_dsn) as conn:
            # A terminal-CAS failure must roll back the earlier Agent completion
            # and closing of its Rules ledger on this same connection.
            assert (
                conn.execute(
                    "SELECT count(*) FROM agent.turn WHERE status='completed'"
                ).fetchone()[0]
                == 0
            )
            assert (
                conn.execute(
                    "SELECT count(*) FROM agent.turn_rules_execution WHERE payload->>'state'='active'"
                ).fetchone()[0]
                == 1
            )
    else:
        completed = asyncio.run(
            writer.run(transport=wire, api_key="synthetic-not-secret")
        )
        assert completed.status == "completed" and len(wire.calls) == 1
        proposal = plan_adapter.service.get_plan_authoring_proposal(
            capture.world_id, action.action_id
        )
        assert proposal.capture == capture
        assert (
            proposal.replacement_markdown
            == graph_answer()["answer_segments"][0]["text"]
        )
    stored = PlanActionDialogueService().get_by_key(
        capture.world_id, capture.idempotency_key
    )
    assert stored.status == (
        "completed" if case in {"later_save", "switch_chat"} else "pending"
    )
    if case in {"later_save", "stale_before_send"}:
        assert snapshot_content(capture.document_id).markdown == "A newer author edit."


def test_unvalidated_fragment_cannot_be_attached_after_grounding(
    plan_adapter, monkeypatch
):
    import asyncio
    from application_state.agent_conversation.plan_authoring import (
        PlanAuthoredProposalV1,
        text_digest,
    )
    from application_state.errors import ApplicationStateValidationError
    from tests.test_plan_jev_writer import WriterWire, graph_answer

    writer, action, capture = authoring_writer(plan_adapter)
    original = plan_adapter.service.complete_plan_authoring_turn

    def inject(result, *, proposal, **kwargs):
        payload = proposal.model_dump(mode="json", by_alias=True)
        payload["replacement_markdown"] += "\n\nAn unrelated unvalidated assertion."
        payload["origin"]["replacement_markdown_sha256"] = text_digest(
            payload["replacement_markdown"]
        )
        return original(
            result, proposal=PlanAuthoredProposalV1.model_validate(payload), **kwargs
        )

    monkeypatch.setattr(plan_adapter.service, "complete_plan_authoring_turn", inject)
    wire = WriterWire(plan_adapter, json.dumps(graph_answer()))
    with pytest.raises(ApplicationStateValidationError, match="literal output"):
        asyncio.run(writer.run(transport=wire, api_key="synthetic-not-secret"))
    assert len(wire.calls) == 1
    assert (
        plan_adapter.service.list_turns(capture.world_id, capture.conversation_id)[
            0
        ].status
        == "running"
    )
    assert (
        plan_adapter.service.get_plan_authoring_proposal(
            capture.world_id, action.action_id
        )
        is None
    )


def test_mixed_rules_acceptance_rolls_back_with_plan_terminal_cas(
    plan_adapter, application_state_dsn, monkeypatch
):
    import asyncio
    import psycopg
    from application_state.errors import ApplicationStateConflictError
    from application_state.plan_action_dialogue import repository as actions
    from tests.test_plan_jev_writer import WriterWire

    writer, action, capture = authoring_writer(
        plan_adapter, rules_used=True, graph_used=False
    )
    support = json.loads(writer.messages[1]["content"])["supports"][0]
    assert writer.output_format['schema']['properties']['kind']['const'] == 'rules_answer'
    answer = {
        "kind": "rules_answer",
        "base_output": None,
        "rules_segments": [
            {
                "kind": "rules_claim",
                "text": support['excerpt_text'],
                "support_ids": [support['support_id']],
            }
        ],
        "ordered_refs": [{"domain": "rules", "segment_index": 0}],
    }
    original = actions.finish_authoring_result

    def lose_fence(conn, *args):
        conn.execute(
            "UPDATE plan_action.action SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE action_id=%s",
            (action.action_id,),
        )
        return original(conn, *args)

    monkeypatch.setattr(actions, "finish_authoring_result", lose_fence)
    wire = WriterWire(plan_adapter, json.dumps(answer))
    with pytest.raises(ApplicationStateConflictError, match="atomic result completion"):
        asyncio.run(writer.run(transport=wire, api_key="synthetic-not-secret"))
    with psycopg.connect(application_state_dsn) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM agent.turn WHERE status='completed'"
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM agent.turn_rules_execution WHERE payload->>'state'='active' AND accepted_binding IS NULL AND accepted_binding_sha256 IS NULL"
            ).fetchone()[0]
            == 1
        )
    assert len(wire.calls) == 1
    assert (
        plan_adapter.service.get_plan_authoring_proposal(
            capture.world_id, action.action_id
        )
        is None
    )


def test_plan_result_readback_rejects_a_mismatched_completed_owner(
    plan_adapter, application_state_dsn
):
    import asyncio
    import psycopg
    from application_state.errors import ApplicationStateIntegrityError
    from tests.test_plan_jev_writer import WriterWire, graph_answer

    writer, action, capture = authoring_writer(plan_adapter)
    wire = WriterWire(plan_adapter, json.dumps(graph_answer()))
    asyncio.run(writer.run(transport=wire, api_key="synthetic-not-secret"))
    # A syntactically valid seal cannot stand in for the actual paired result.
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE plan_action.action SET authoring_origin=jsonb_set(authoring_origin,'{agent_result_sha256}',to_jsonb(%s::text)) WHERE action_id=%s",
            ("0" * 64, action.action_id),
        )
    with pytest.raises(ApplicationStateIntegrityError, match="do not match"):
        plan_adapter.service.get_plan_authoring_proposal(
            capture.world_id, action.action_id
        )
    assert len(wire.calls) == 1


def test_live_agent_claim_keeps_authoring_action_fence_past_fixed_lease(
    plan_adapter, application_state_dsn
):
    import asyncio
    import psycopg
    from application_state.plan_action_dialogue.service import PlanActionDialogueService
    from tests.test_plan_jev_writer import WriterWire, graph_answer

    writer, action, capture = authoring_writer(plan_adapter)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE plan_action.action SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE action_id=%s",
            (action.action_id,),
        )
    reconciled = PlanActionDialogueService().get_by_key(
        capture.world_id, capture.idempotency_key
    )
    assert reconciled.status == "pending" and reconciled.fence == action.fence
    assert reconciled.dispatch_token == action.dispatch_token
    wire = WriterWire(plan_adapter, json.dumps(graph_answer()))
    completed = asyncio.run(writer.run(transport=wire, api_key="synthetic-not-secret"))
    assert completed.status == "completed" and len(wire.calls) == 1
    assert (
        plan_adapter.service.get_plan_authoring_proposal(
            capture.world_id, action.action_id
        )
        is not None
    )


@pytest.mark.parametrize("loss", ["expired", "interrupted", "different_attempt"])
def test_authoring_action_never_renews_a_lost_agent_claim(
    plan_adapter, application_state_dsn, loss
):
    import psycopg
    from application_state.agent_conversation.types import TurnFailure
    from application_state.plan_action_dialogue.service import PlanActionDialogueService

    writer, action, capture = authoring_writer(plan_adapter)
    turn = plan_adapter.fence.turn
    if loss == "interrupted":
        plan_adapter.service.fail_turn(
            TurnFailure(
                world_id=turn.world_id,
                conversation_id=turn.conversation_id,
                turn_id=turn.turn_id,
                expected_revision=turn.revision,
                failure_code="synthetic_interruption",
            ),
            interrupted=True,
        )
    else:
        with psycopg.connect(application_state_dsn) as conn:
            if loss == "expired":
                conn.execute(
                    "UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
                    (turn.turn_id,),
                )
            else:
                conn.execute(
                    "UPDATE agent.turn SET attempt=attempt+1 WHERE turn_id=%s",
                    (turn.turn_id,),
                )
    reconciled = PlanActionDialogueService().get_by_key(
        capture.world_id, capture.idempotency_key
    )
    assert reconciled.status == "indeterminate" and reconciled.fence == action.fence + 1
    assert reconciled.dispatch_token is None and reconciled.lease_expires_at is None


def test_action_expiry_waits_for_concurrent_agent_claim_renewal(
    plan_adapter, application_state_dsn
):
    import psycopg
    from concurrent.futures import ThreadPoolExecutor, TimeoutError
    from threading import Event
    from application_state.plan_action_dialogue.service import PlanActionDialogueService

    _, action, capture = authoring_writer(plan_adapter)
    turn = plan_adapter.fence.turn
    plan_adapter.fence.renewer.stop_and_join()
    with psycopg.connect(application_state_dsn) as expiry:
        expiry.execute(
            "UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
            (turn.turn_id,),
        )
        expiry.execute(
            "UPDATE plan_action.action SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE action_id=%s",
            (action.action_id,),
        )
    started = Event()
    with psycopg.connect(application_state_dsn) as renewal:
        renewal.execute("SET LOCAL lock_timeout='5s'")
        renewal.execute(
            "UPDATE agent.turn SET claim_expires_at=clock_timestamp()+interval '120 seconds' WHERE turn_id=%s",
            (turn.turn_id,),
        )

        def reconcile():
            started.set()
            return PlanActionDialogueService().get_by_key(
                capture.world_id, capture.idempotency_key
            )

        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(reconcile)
            try:
                assert started.wait(5)
                # A nonlocking read would see the committed expired deadline and
                # fence valid work. Reconciliation must wait for renewal here.
                with pytest.raises(TimeoutError):
                    pending.result(timeout=0.2)
                renewal.commit()
            finally:
                renewal.rollback()
            result = pending.result(timeout=10)
    assert result.status == "pending" and result.fence == action.fence
    assert result.dispatch_token == action.dispatch_token






def test_completed_writing_cannot_silently_lose_its_plan_result(
    plan_adapter, application_state_dsn
):
    import asyncio
    import psycopg
    from application_state.errors import ApplicationStateIntegrityError
    from apps.live_control_server.services.agent_turn_service import (
        project_plan_authoring_proposal,
    )
    from tests.test_plan_jev_writer import WriterWire, graph_answer

    writer, action, _ = authoring_writer(plan_adapter)
    completed = asyncio.run(
        writer.run(
            transport=WriterWire(plan_adapter, json.dumps(graph_answer())),
            api_key="synthetic",
        )
    )
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "DELETE FROM plan_action.action WHERE action_id=%s", (action.action_id,)
        )
    with pytest.raises(ApplicationStateIntegrityError, match="paired Plan proposal"):
        project_plan_authoring_proposal(completed, service=plan_adapter.service)




@pytest.mark.parametrize('status,expected', [(400,'invalid_request'),(429,'rate_limited'),(503,'provider_unavailable'),(None,'provider_timeout')])
def test_plan_decision_failure_retains_normalized_cause_without_sdk_text(plan_adapter,status,expected):
    import asyncio
    from generationengine import GenerationEngineError
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch

    class FailedWire(httpx2.AsyncBaseTransport):
        calls=0
        async def handle_async_request(self,request):
            self.calls+=1
            if status is None:
                raise httpx2.ReadTimeout('DO_NOT_CAPTURE_PRIVATE_TRANSPORT_DETAIL',request=request)
            return httpx2.Response(status,request=request,json={'error':{'message':'DO_NOT_CAPTURE_PRIVATE_TRANSPORT_DETAIL'}})

    wire=FailedWire()
    with pytest.raises(GenerationEngineError):
        asyncio.run(PlanJevDispatch.requested_work(plan_adapter,page_title='Plan').run(transport=wire,api_key='synthetic-not-secret'))
    assert wire.calls==1
    trace=plan_adapter.context_capture.trace
    failures=[event for event in trace.observations if event.kind=='failure']
    assert failures[-1].code=='plan_jev_'+expected and failures[-1].phase=='provider'
    assert 'DO_NOT_CAPTURE_PRIVATE_TRANSPORT_DETAIL' not in trace.model_dump_json()
    execution=plan_adapter.fence.turn.graph_context_execution
    assert any(event.kind=='plan_requested_work_authorized_v2' for event in execution.events)
    assert not any(event.kind=='plan_requested_work_selected_v2' for event in execution.events)


@pytest.mark.parametrize("schema", ["dmb_plan_requested_work_input_v2", "unregistered_parent"])
def test_current_authorization_rejects_parent_contract_substitution(plan_adapter, schema):
    import asyncio
    from application_state.agent_conversation.plan_jev_decision import verify_input
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch

    dispatch = PlanJevDispatch.requested_work(plan_adapter, page_title="Preparation")
    asyncio.run(dispatch.run(transport=SemanticWire(plan_adapter, "discuss"), api_key="synthetic-not-secret"))
    turn = plan_adapter.fence.turn
    parent = dispatch.parent.model_dump(mode="json", by_alias=True) | {"schema": schema}
    with pytest.raises(ValueError):
        verify_input(turn, dispatch.authorization, {
            "parent_request_json": json.dumps(parent),
            "request_json": dispatch.prepared.body.decode(),
        })




def _shared_plan_authoring_case(
    plan_adapter, tmp_path, monkeypatch, placement, mode, failure=None, *, routing=None, dsn=None,
    placement_factory=None, semantic_intent=None, semantic_compatible=None,
    ordinary_caret=False, author_scope_calls=None, first_intent=None,
):
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_plan_statements import (
        NativePlanQueryUnavailableV1,
    )
    from application_state.plan_action_dialogue.service import PlanActionDialogueService
    from tests.test_plan_jev_harness import route_case, Finish
    from tests.test_plan_jev_writer import WriterWire
    from apps.live_control_server.services.agent_turn_service import execute_agent_turn

    if mode != "base":
        from tests.test_rules_lookup_broker import args

        plan_adapter.request = plan_adapter.request.model_copy(
            update={"message": args().question}
        )
    capture, _ = admitted_authoring(plan_adapter, admit=False)
    if placement_factory is not None:
        capture, catalog = placement_factory(capture)
        plan_adapter.request = plan_adapter.request.model_copy(update={
            "plan_authoring_capture": capture, "plan_placement_catalog": catalog})
    plan_adapter.request = plan_adapter.request.model_copy(
        update={
            "plan_context_policy": t.PlanContextPolicyV2(
                policy="auto_plan_world", graph_source="reviewed_native_graph"
            )
        }
    )
    if routing == "write_without_capture":
        plan_adapter.request = plan_adapter.request.model_copy(update={
            "plan_authoring_capture": None, "plan_placement_catalog": None})
    harness, _, wire, kwargs = route_case(plan_adapter, tmp_path)
    kwargs["plan_graph_resolver"] = lambda *_args: pytest.fail(
        "No classic Graph path for current Plan"
    )
    kwargs["native_graph_query_resolver"] = lambda *_args: (
        None,
        NativePlanQueryUnavailableV1(
            managed_world_id=plan_adapter.world_id,
            reason="native_graph_head_unavailable",
        ),
    )
    from application_state.content.service import commit_plan, snapshot_content

    def newer_plan():
        commit_plan(
            capture.document_id,
            "A newer author edit.",
            expected_revision=capture.base_revision,
            expected_world_id=capture.world_id,
        )

    if failure in {"changed_capture", "changed_page", "changed_conversation"}:
        reserve = kwargs["conversation_service"].reserve_plan_authoring_action

        def change_at_reservation(**values):
            if failure == "changed_capture":
                values["capture"] = values["capture"].model_copy(
                    update={"draft_generation": values["capture"].draft_generation + 1}
                )
            action = reserve(**values)
            if failure == "changed_page":
                newer_plan()
            if failure == "changed_conversation":
                kwargs["conversation_service"].new_conversation(
                    t.ConversationCommand(
                        world_id=capture.world_id,
                        command_id=uuid4(),
                        expected_pointer_revision=capture.expected_pointer_revision,
                        expected_active_conversation_id=capture.conversation_id,
                    )
                )
            return action

        monkeypatch.setattr(
            kwargs["conversation_service"],
            "reserve_plan_authoring_action",
            change_at_reservation,
        )
    if failure == "terminal_cas":
        from application_state.plan_action_dialogue import repository as actions

        finish = actions.finish_authoring_result

        def expired(conn, action, *values):
            conn.execute(
                "UPDATE plan_action.action SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE action_id=%s",
                (action.action_id,),
            )
            return finish(conn, action, *values)

        monkeypatch.setattr(actions, "finish_authoring_result", expired)

    class Choices(Finish):
        async def handle_async_request(self, request):
            body = json.loads(request.content)
            if body["state"].get("surface") == "plan":
                from application_state.agent_conversation.surface_action_catalog import opening_action_menu

                assert not self.calls
                self.calls.append(request)
                assert set(body["questions"]) == {"requested_work"}
                criteria = body["questions"]["requested_work"]["criteria"]
                assert criteria == opening_action_menu("plan", plan_operation=plan_adapter.request.plan_requested_operation)
                assert set(body["state"]) <= {"surface", "user_utterance", "page_title", "selected_text",
                                             "prior_dialogue", "explicit_editor_operation"}
                choice = first_intent or semantic_intent or (
                    routing if routing in {"discuss", "clarify", "different_destination"} else "write_current_page"
                )
                return httpx2.Response(200, request=request, json={
                    "model": body["model"], "usage": {"input_tokens": 31, "output_tokens": 7},
                    "answers": {"requested_work": {"type": "choice", "choice": choice, "confidence": 1,
                        "probabilities": {value: float(value == choice) for value in criteria}}},
                })
            if 'existing_scope' in body['questions']:
                assert set(body["questions"]) == {"page_edit_intent", "location_relation", "existing_scope"}
                assert set(body["questions"]["page_edit_intent"]["criteria"]) == {
                    "page_edit", "discussion", "unresolved",
                }
                assert "candidates" not in body["state"]
                self.calls.append(request)
                catalog = plan_adapter.request.plan_placement_catalog
                nominated = semantic_compatible or (placement,)
                entry = next((e for e in catalog.entries if e.selector in nominated), None)
                relation = 'unresolved'
                if entry is not None and (routing not in {'discuss', 'clarify'}
                        or semantic_intent == 'write_current_page'):
                    relation = 'insert_at_explicit_caret' if entry.kind == 'captured_target' else entry.kind
                    if ordinary_caret:
                        assert relation == 'insert_at_explicit_caret'
                        relation = 'unstated_insertion_location'
                scope = 'none'
                if relation in {'before_paragraph', 'after_paragraph'} and 'the Preparation paragraph about' in body['state']['current_request']:
                    scope = next(alias for alias, candidate in body['state']['scope_hypotheses'].items()
                        if candidate['author_quote']['text'] == 'Preparation')
                choices = {'location_relation': relation, 'existing_scope': scope,
                    'page_edit_intent': 'discussion' if routing == 'discuss' else 'page_edit'}
                answers = {name: dict(type='choice', choice=value, confidence=1,
                    probabilities={key: float(key == value) for key in body['questions'][name]['criteria']})
                    for name, value in choices.items()}
                return httpx2.Response(200, request=request, json=dict(model=body['model'], answers=answers,
                    usage=dict(input_tokens=31, output_tokens=7)))
            if "requested_work" in body["questions"]:
                if "conditional_read_plan_policy" in body["state"] and "author_page_edit_intent" in body["state"]:
                    from application_state.agent_conversation.surface_action_catalog import opening_action_menu

                    assert body["questions"]["requested_work"]["criteria"] == opening_action_menu(
                        "plan", plan_operation=plan_adapter.request.plan_requested_operation,
                    )
                    assert "operation" in body["questions"]
                self.calls.append(request)
                return await SemanticWire(
                    wire.adapter, semantic_intent or (("write_current_page" if routing == "write_without_capture" else routing)
                    if routing else "write:" + placement), compatible_selectors=semantic_compatible,
                ).handle_async_request(request)
            if mode != "base":
                self.calls.append(request)
                selected = {
                    i
                    for i, c in enumerate(body.get("state", {}).get("candidates", []))
                    if c["kind"] == "public_rules_lookup"
                }
                answers = {}
                for name, q in body["questions"].items():
                    choice = (
                        "include"
                        if name.startswith("candidate_")
                        and int(name.split("_")[-1]) in selected
                        else "finish_retrieval"
                        if name == "operation"
                        else "exclude"
                    )
                    answers[name] = dict(
                        type="choice",
                        choice=choice,
                        confidence=1,
                        probabilities={o: float(o == choice) for o in q["criteria"]},
                    )
                return httpx2.Response(
                    200,
                    request=request,
                    json=dict(
                        model="jev-1.14.0",
                        answers=answers,
                        usage=dict(input_tokens=31, output_tokens=7),
                    ),
                )
            return await super().handle_async_request(request)

    class Proposed(WriterWire):
        async def handle_async_request(self, request):
            payload = json.loads(request.content)
            rows = payload["input"]
            if routing in {"discuss", "clarify"}:
                from application_state.agent_conversation.plan_placement import PlanPlacementCatalogV2
                from application_state.agent_conversation.response_prompt import compose_response_prompt
                question_field = payload["text"]["format"]["schema"]["properties"].get("question", {})
                task = (("contextual_target_question" if 'enum' in question_field else "contextual_content_question")
                        if payload["text"]["format"]["name"] == "plan_contextual_question_v1"
                        else "plan_placement_clarify" if routing == "clarify"
                        and type(plan_adapter.request.plan_placement_catalog) is PlanPlacementCatalogV2
                        else "clarify" if routing == "clarify"
                        else "plan_contextual_discussion" if routing == "discuss"
                        and type(plan_adapter.request.plan_placement_catalog) is PlanPlacementCatalogV2
                        else "answer")
                assert payload["instructions"] == compose_response_prompt(task=task).instructions
                schema = payload["text"]["format"]["schema"]
                base = schema.get("$defs", {}).get("Base", schema)
                if task in {"contextual_content_question", "contextual_target_question"}:
                    assert base["properties"]["question"]["minLength"] == 1
                else:
                    assert base["properties"]["answer_segments"].get("minItems", 0) == (
                        1 if task == "plan_placement_clarify" else 0)
            if routing in {"discuss", "clarify"}:
                [packet] = rows
                prose = packet["content"]
                assert prose.startswith("# Plan evidence\n\n")
                assert capture.draft_markdown in prose
                assert "## Current page draft" in prose
                assert "## Focused edit target" in prose
                expected_placement = capture.target_kind
                assert expected_placement in prose
                assert "run_id" not in prose
            else:
                frames = [json.loads(row["content"]) for row in rows
                          if row["content"] != "Return JSON."]
                native = next(row for row in frames if set(row) == {
                    "input_status", "user_question", "native_body_evidence",
                    "native_statements", "native_assertions",
                })
                from application_state.agent_conversation.native_plan_work_view import is_semantic_frame
                work = next(row for row in frames if is_semantic_frame(row))
                assert 'schema' not in work
                assert 'run_id' not in json.dumps(work)
                assert len(frames) == 3
                assert frames[-1 if routing in {"discuss", "clarify"} else 0] == native
                assert work["current_page_draft"]["markdown"] == capture.draft_markdown
                assert work["focused_edit_target"]["kind"] == (
                    "insert_at_caret" if placement == "captured" else "insert_at_boundary"
                )
                if placement_factory is not None:
                    from application_state.agent_conversation.plan_placement import PlanPlacementCatalogV2
                    catalog = plan_adapter.request.plan_placement_catalog
                    entry = next((entry for entry in catalog.entries if entry.selector == placement), None)
                    if type(catalog) is PlanPlacementCatalogV2 and entry is not None and entry.kind.endswith('_paragraph'):
                        scope = work["focused_edit_target"]["fragment_scope"]
                        node = json.loads(capture.editor_json)["content"][entry.source_root_index]
                        assert scope["existing_paragraph_text"] == "".join(
                            "\n" if part["type"] == "hardBreak" else part["text"] for part in node["content"])
            self.adapter = wire.adapter
            if placement_factory is not None:
                serialized = json.dumps(rows)
                for host_field in ("source_root_index", "root_boundary", "editor_sha256", "target_capture_sha256"):
                    assert host_field not in serialized
                assert capture.document_id not in serialized and capture.world_id not in serialized
            if failure == "writer_timeout":
                import httpx

                self.calls.append(request)
                raise httpx.ReadTimeout(
                    "Synthetic shared Plan writer timeout", request=request
                )
            if failure == "save_after_send":
                newer_plan()
            if failure == "chat_after_send":
                kwargs["conversation_service"].new_conversation(
                    t.ConversationCommand(
                        world_id=capture.world_id,
                        command_id=uuid4(),
                        expected_pointer_revision=capture.expected_pointer_revision,
                        expected_active_conversation_id=capture.conversation_id,
                    )
                )
            from application_state.agent_conversation.native_plan_assertions import POLICY
            candidate = dict(
                schema=POLICY,
                answer_segments=[
                    dict(
                        kind="proposal",
                        label="invented_idea",
                        text="A proposed arrival, ready for the author to review.",
                    )
                ],
                limitations=[],
                requested_detail_gaps=[],
            )
            if payload['text']['format']['name'] == 'plan_contextual_question_v1':
                candidate = dict(question=payload['text']['format']['schema']['properties']['question'].get(
                    'enum', ['Which part of the request should I clarify?'])[0])
            if mode != "base":
                rules = json.loads(rows[1]["content"])
                support = rules["supports"][0]
                assert json.loads(request.content)['text']['format']['schema']['properties']['kind']['const'] == 'rules_answer'
                candidate = dict(
                    kind="rules_answer",
                    base_output=None if mode == "rules_only" else candidate,
                    rules_segments=[
                        dict(
                            kind="rules_claim",
                            text=support["excerpt_text"],
                            support_ids=[support["support_id"]],
                        )
                    ],
                    ordered_refs=(
                        [dict(domain="base", segment_index=None)]
                        if mode == "mixed"
                        else []
                    )
                    + [dict(domain="rules", segment_index=0)],
                )
            self.text = json.dumps(candidate)
            return await super().handle_async_request(request)

    decisions = Choices()
    writer = Proposed(None, "")
    harness.decision_transport = decisions
    harness.writer_transport = writer
    from application_state.agent_conversation.plan_placement import PlanPlacementCatalogV2
    if author_scope_calls is None:
        author_scope_calls = 2 if type(plan_adapter.request.plan_placement_catalog) is PlanPlacementCatalogV2 else 0
    contextual = bool(author_scope_calls)
    requested_first = first_intent or semantic_intent or routing
    author_scope_calls = 1 if requested_first in {"discuss", "clarify"} else author_scope_calls + 1
    if routing is not None:
        from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
        from application_state.plan_action_dialogue.repository import get_authoring_for_turn
        import psycopg
        refused = {"different_destination": "plan_authoring_destination_unavailable",
            "write_without_capture": "plan_authoring_target_unavailable"}
        if routing in refused:
            saved_before = snapshot_content(capture.document_id).markdown
            with pytest.raises(AgentTurnServiceError) as failed:
                execute_agent_turn(plan_adapter.request, **kwargs)
            assert failed.value.code == refused[routing]
            if routing == "different_destination" and author_scope_calls:
                from application_state.agent_conversation.native_plan_opening import NativePlanAuthorScopeObservedV1

                assert len(decisions.calls) == 1 and not writer.calls
                turn = kwargs["conversation_service"].inspect_turn(
                    world_id=capture.world_id, turn_id=wire.adapter.turn.turn_id,
                )
                observations = [event.scope_observation for event in turn.graph_context_execution.events
                                if type(event) is NativePlanAuthorScopeObservedV1]
                assert [observation.requested_work for observation in observations] == ["different_destination"]
                assert turn.completion is None
                assert PlanActionDialogueService().get_by_key(capture.world_id, capture.idempotency_key) is None
                assert not any(event.kind in {"native_plan_request_search_authorized_v1", "native_authored_source_read_v1"}
                               for event in turn.graph_context_execution.events)
                assert snapshot_content(capture.document_id).markdown == saved_before
                return None
            assert not writer.calls and len(decisions.calls) == 1 + author_scope_calls
            response = None
        else:
            from time import perf_counter

            started = perf_counter()
            response = execute_agent_turn(plan_adapter.request, **kwargs)
            capture_ms = (perf_counter() - started) * 1000
            assert response.answer.status == "ok" and response.plan_proposal is None
            assert "plan_proposal" not in response.model_dump(mode="json")
            assert len(writer.calls) == 1 and len(decisions.calls) == 1 + author_scope_calls
        if routing == "clarify" and author_scope_calls:
            import os
            from pathlib import Path

            if destination := os.environ.get("DMB_PLAN_OPENING_WIRE"):
                Path(destination).write_text(json.dumps([
                    json.loads(call.content) for call in decisions.calls
                ], indent=2) + "\n")
        turn = kwargs["conversation_service"].inspect_turn(
            world_id=capture.world_id, turn_id=wire.adapter.turn.turn_id)
        assert turn.graph_context_receipt.schema_ == "dmb_surface_native_context_receipt_v1"
        assert turn.user_text == plan_adapter.request.message
        selected = [event for event in turn.graph_context_execution.events
            if isinstance(event, t.PlanRequestedWorkSelectedV2)]
        assert len(selected) == 1
        if author_scope_calls:
            from application_state.agent_conversation.native_plan_opening import NativePlanAuthorScopeObservedV1
            scopes = [event for event in turn.graph_context_execution.events
                if type(event) is NativePlanAuthorScopeObservedV1]
            assert len(scopes) == author_scope_calls
            assert scopes[0].scope_observation.requested_work is not None
            if contextual:
                assert selected[0].author_scope_binding.observation_event_id == scopes[-1].event_id
        assert selected[0].requested_work == ("write_current_page" if routing == "write_without_capture" else routing)
        assert selected[0].original_capture_sha256 == (None if routing == "write_without_capture" else capture.sha256)
        action = PlanActionDialogueService().get_by_key(
            capture.world_id, capture.idempotency_key
        )
        with psycopg.connect(dsn) as conn:
            reservation = get_authoring_for_turn(
                conn, world_id=turn.world_id, turn_id=turn.turn_id, attempt=turn.attempt
            )
        before = (capture.base_revision, plan_adapter.work.plan_markdown)
        snapshot = snapshot_content(capture.document_id)
        after = (snapshot.work_object.object_revision, snapshot.markdown)
        if response is None:
            assert action is None and reservation is None and before == after
        else:
            from hashlib import sha256
            from evals.buddy_benchmark.artifacts import immutable_save
            from evals.buddy_benchmark.workflow import action_report

            effects = []
            if reservation is not None or action is not None:
                effects.append("write_reserved")
            if response.plan_proposal is not None:
                effects.append("proposal_created")
            report_dir = tmp_path / "aw-report"
            immutable_save(report_dir, "observation", {
                "events": effects,
                "journal_complete": False,
                "before": list(before),
                "after": list(after),
                "fulfilled": response.answer.status == "ok",
            })
            observation = report_dir / "observation.json"
            immutable_save(report_dir, "manifest", {
                "schema": "dmb_aw_assessment_v1",
                "cases": [{
                    "id": str(turn.turn_id),
                    "observation": {
                        "path": observation.name,
                        "sha256": sha256(observation.read_bytes()).hexdigest(),
                    },
                }],
            })
            started = perf_counter()
            assessment = action_report(report_dir / "manifest.json")["cases"][0]
            report_ms = (perf_counter() - started) * 1000
            immutable_save(report_dir, "timing", {
                "ordinary_dispatch_ms": capture_ms,
                "offline_assessment_ms": report_ms,
                "provider_mode": "mock_transport",
            })
            assert assessment["status"] == "unproven", assessment
        calls = len(decisions.calls), len(writer.calls)
        if response is None:
            assert turn.failure_code == refused[routing] and turn.completion is None
            attempts = kwargs["conversation_service"].list_context_trace_attempts(
                world_id=turn.world_id, turn_id=turn.turn_id)
            failures = [event for event in attempts[-1].observations if event.kind == "failure"]
            assert failures[-1].code == turn.failure_code
            assert failures[-1].phase == "delivery"
            assert attempts[-1].terminal_status == "interrupted"
            with pytest.raises(AgentTurnServiceError):
                execute_agent_turn(plan_adapter.request, **kwargs)
        else:
            assert turn.completion.schema_ == "dmb_surface_native_completion_v1"
            replay = execute_agent_turn(plan_adapter.request, **kwargs)
            assert replay.plan_proposal is None and replay.plan_context.completion == response.plan_context.completion
        assert calls == (len(decisions.calls), len(writer.calls))
        return
    if failure is not None and failure not in {"save_after_send", "chat_after_send"}:
        from apps.live_control_server.services.agent_turn_service import (
            AgentTurnServiceError,
        )

        with pytest.raises(AgentTurnServiceError):
            execute_agent_turn(plan_adapter.request, **kwargs)
        assert len(writer.calls) == (
            1 if failure in {"writer_timeout", "save_after_send", "terminal_cas"} else 0
        )
        retained = kwargs["conversation_service"].inspect_turn(
            world_id=capture.world_id, turn_id=wire.adapter.turn.turn_id
        )
        assert (
            retained.status == "interrupted"
            and retained.completion is None
            and retained.user_text == plan_adapter.request.message
        )
        action = PlanActionDialogueService().get_by_key(
            capture.world_id, capture.idempotency_key
        )
        assert (
            action is None
            if failure in {"changed_capture", "changed_opening_intent"}
            else action.status == "indeterminate"
        )
        assert (
            kwargs["conversation_service"].get_plan_authoring_proposal(
                capture.world_id, action.action_id
            )
            is None
            if action
            else True
        )
        if failure == "changed_opening_intent":
            assert len(decisions.calls) == 2
            assert not any(isinstance(event, t.PlanRequestedWorkSelectedV2)
                           for event in retained.graph_context_execution.events)
        calls = (len(decisions.calls), len(writer.calls))
        with pytest.raises(AgentTurnServiceError):
            execute_agent_turn(plan_adapter.request, **kwargs)
        assert calls == (len(decisions.calls), len(writer.calls))
        return
    response = execute_agent_turn(plan_adapter.request, **kwargs)
    context = (
        response.plan_context
        if mode == "base"
        else response.rules_context.base_context
        or response.rules_context.unclaimed_context
    )
    assert context.receipt.schema_ == "dmb_surface_native_context_receipt_v1"
    assert response.plan_proposal is not None
    expected = plan_adapter.request.plan_placement_catalog.resolve(capture, placement)
    assert response.plan_proposal.capture == expected
    if mode == "base":
        from application_state.agent_conversation.plan_placement import PlanPlacementCatalogV2
        footer = "This answer uses partial retrieval and does not establish corpus completeness."
        assert footer in response.answer.text
        if type(plan_adapter.request.plan_placement_catalog) is PlanPlacementCatalogV2:
            assert footer not in response.plan_proposal.replacement_markdown
        else:
            assert footer in response.plan_proposal.replacement_markdown
    if mode != "rules_only":
        assert response.plan_proposal.replacement_markdown.startswith(
            "A proposed arrival, ready for the author to review."
        )
    else:
        assert response.plan_proposal.replacement_markdown
    action = PlanActionDialogueService().get_by_key(
        capture.world_id, capture.idempotency_key
    )
    assert (
        action.status == "completed"
        and action.authoring_origin.proposal == response.plan_proposal
    )
    # Once sent, the immutable proposal can finish while a newer draft/chat is preserved. It never saves the page.
    snapshot = snapshot_content(capture.document_id)
    assert snapshot.markdown == (
        "A newer author edit."
        if failure == "save_after_send"
        else plan_adapter.work.plan_markdown
    )
    assert snapshot.work_object.object_revision == capture.base_revision + (
        1 if failure == "save_after_send" else 0
    )
    assert (
        len(decisions.calls) == (2 if mode == "base" else 3) + author_scope_calls and len(writer.calls) == 1
    )
    replay = execute_agent_turn(plan_adapter.request, **kwargs)
    assert (
        replay.plan_proposal == response.plan_proposal
        and len(writer.calls) == 1
        and len(decisions.calls) == (2 if mode == "base" else 3) + author_scope_calls
    )
    return response


def test_ordinary_plan_caret_reopens_its_exact_captured_proposal(
    plan_adapter, tmp_path, monkeypatch, application_state_dsn,
):
    from tests.application_state.test_plan_placement import native_paragraph_placement_fixture

    plan_adapter.request = plan_adapter.request.model_copy(update={
        "message": "Add what the players see and hear at the boardwalk. "
                   "Give me a private reminder to leave the tower sealed unless the players investigate.",
    })
    result = _shared_plan_authoring_case(
        plan_adapter, tmp_path, monkeypatch, "captured", "base",
        dsn=application_state_dsn, placement_factory=native_paragraph_placement_fixture,
        ordinary_caret=True,
    )
    assert result.plan_proposal.capture.target_kind == "insert_at_caret"
    assert result.plan_proposal.capture.from_ == result.plan_proposal.capture.to


@pytest.mark.parametrize("mode", ["base", "mixed", "rules_only"])
@pytest.mark.parametrize("placement", ["captured", "end"])
def test_current_shared_plan_caller_reserves_and_delivers_its_actual_edit(
    plan_adapter, tmp_path, monkeypatch, placement, mode
):
    _shared_plan_authoring_case(plan_adapter, tmp_path, monkeypatch, placement, mode)


def test_plain_plan_cannot_write_after_discussion_intent(plan_adapter, tmp_path, monkeypatch):
    _shared_plan_authoring_case(
        plan_adapter, tmp_path, monkeypatch, "captured", "base",
        failure="changed_opening_intent", first_intent="discuss",
    )


@pytest.mark.parametrize(
    "failure",
    [
        "changed_capture",
        "changed_page",
        "changed_conversation",
        "writer_timeout",
        "terminal_cas",
    ],
)
def test_current_shared_plan_caller_never_completes_or_resends_changed_authoring(
    plan_adapter, tmp_path, monkeypatch, failure
):
    _shared_plan_authoring_case(
        plan_adapter, tmp_path, monkeypatch, "captured", "base", failure
    )


@pytest.mark.parametrize("change", ["save_after_send", "chat_after_send"])
def test_current_shared_plan_caller_preserves_the_proposal_when_work_moves_after_send(
    plan_adapter, tmp_path, monkeypatch, change
):
    _shared_plan_authoring_case(
        plan_adapter, tmp_path, monkeypatch, "captured", "base", change
    )


@pytest.mark.parametrize("routing", ["discuss", "clarify", "different_destination", "write_without_capture"])
def test_current_shared_plan_caller_keeps_routing_and_action_ownership(
    plan_adapter, tmp_path, monkeypatch, application_state_dsn, routing
):
    _shared_plan_authoring_case(plan_adapter, tmp_path, monkeypatch, "captured", "base",
        routing=routing, dsn=application_state_dsn)


def test_under_heading_selection_survives_actual_dispatch_reservation_and_retained_replay(plan_adapter):
    capture, turn = admitted_authoring(plan_adapter, placement="under:0")
    event = turn.graph_context_execution.events[-1]
    assert event.placement_selector == "under:0"
    assert event.target_capture_sha256 == capture.sha256
    assert capture.root_boundary == 1 and capture.from_ == capture.to == 13
    action, fresh = plan_adapter.service.reserve_plan_authoring_action(
        capture=capture, turn_id=turn.turn_id, expected_revision=turn.revision)
    assert fresh and action.authoring_origin.capture_sha256 == capture.sha256
    retained = plan_adapter.service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id)
    replayed = type(retained).model_validate_json(retained.model_dump_json(by_alias=True))
    assert replayed.graph_context_execution.events[-1].placement_selector == "under:0"
    again, fresh_again = plan_adapter.service.reserve_plan_authoring_action(
        capture=capture, turn_id=turn.turn_id, expected_revision=turn.revision)
    assert not fresh_again and again.action_id == action.action_id


@pytest.mark.parametrize("outcome", ["selected", "ambiguous", "relation_conflict", "stale_layout", "foreign",
    "ordinary_caret", "mid_paragraph_caret", "conflicting_caret"])
def test_composed_native_turn_retains_checked_slot_or_clarifies(plan_adapter, tmp_path, outcome):
    from dataclasses import replace

    from application_state.agent_conversation.native_execution import NativePlanOpeningSelectedV3
    from application_state.agent_conversation.native_plan_assertions import POLICY
    from application_state.agent_conversation.plan_authoring import text_digest
    from application_state.content.service import commit_plan, snapshot_plan
    from application_state.plan_action_dialogue.service import PlanActionDialogueService
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError, execute_agent_turn
    from tests.application_state.test_plan_authoring_review import composed_plan, LEFT, RIGHT, ENDING
    from tests.test_plan_jev_harness import Finish, route_case
    from tests.test_plan_jev_writer import WriterWire

    original, _ = admitted_authoring(plan_adapter, admit=False)
    markdown, layout, editor = composed_plan([LEFT], [RIGHT], ENDING)
    obj, revision = commit_plan(
        original.document_id, markdown, expected_revision=original.base_revision,
        expected_world_id=original.world_id, page_presentation=layout,
    )
    work = plan_adapter.work
    plan_adapter.work = replace(
        work, revision=obj.object_revision, plan_markdown=markdown,
        content_basis=work.content_basis.model_copy(update=dict(
            object_revision=obj.object_revision, work_revision_id=str(revision.work_revision_id),
            revision_n=revision.revision_n, content_sha256=revision.content_sha256,
        )),
    )
    raw = plan_adapter.request.model_dump(mode="json", by_alias=True)
    raw["primary_work"].update(
        expected_revision=obj.object_revision, expected_revision_n=revision.revision_n,
        expected_content_sha256=revision.content_sha256,
    )
    raw["plan_placement_catalog"] = None
    raw["plan_context_policy"] = {"policy": "auto_plan_world", "graph_source": "reviewed_native_graph"}
    qualified = outcome in {"selected", "relation_conflict"}
    raw["message"] = ("Insert a lantern warning after the locked gate in the right column."
                      if qualified else "Insert a lantern warning after the locked gate.")
    raw["plan_authoring_capture"].update(
        schema="dmb_plan_authoring_composed_snapshot_v1", target_kind="offer_slot_placement",
        base_revision=obj.object_revision, base_content_sha256=revision.content_sha256,
        editor_json=editor, editor_sha256=text_digest(editor), draft_markdown=markdown,
        draft_sha256=text_digest(markdown), base_page_presentation_sha256=layout.fingerprint(),
        draft_page_presentation=layout.model_dump(mode="json", by_alias=True),
        draft_page_presentation_sha256=layout.fingerprint(),
    )
    caret_case = outcome in {"ordinary_caret", "mid_paragraph_caret", "conflicting_caret"}
    if caret_case:
        raw["message"] = ("Add what the players see and hear at the boardwalk. "
                          "Give me a private reminder to leave the tower sealed unless the players investigate.")
        position = len(LEFT[1]) + 7 + len(RIGHT[1]) - int(outcome == "mid_paragraph_caret")
        selection_json = json.dumps({"type": "text", "anchor": position, "head": position})
        raw["plan_authoring_capture"].update({"from": position, "to": position,
            "selection_json": selection_json, "selection_sha256": text_digest(selection_json)})
    if outcome == "foreign":
        raw["plan_authoring_capture"]["world_id"] = "world:foreign"
        with pytest.raises(ValidationError):
            AgentTurnRequest.model_validate(raw)
        assert snapshot_plan(original.document_id).page_presentation == layout
        return
    if outcome == "stale_layout":
        raw["plan_authoring_capture"]["base_page_presentation_sha256"] = "a" * 64
    request = AgentTurnRequest.model_validate(raw)
    capture = request.plan_authoring_capture
    harness, _, wire, kwargs = route_case(plan_adapter, tmp_path)
    kwargs["plan_graph_resolver"] = lambda *_: pytest.fail("Unexpected classic Graph fallback")
    from application_state.agent_conversation.native_plan_statements import NativePlanQueryUnavailableV1
    kwargs["native_graph_query_resolver"] = lambda *_: (
        None, NativePlanQueryUnavailableV1(
            managed_world_id=capture.world_id, reason="native_graph_head_unavailable"),
    )

    class ComposedChoices(Finish):
        async def handle_async_request(self, request):
            body = json.loads(request.content)
            questions = body["questions"]
            if body["state"].get("surface") == "plan":
                from application_state.agent_conversation.surface_action_catalog import opening_action_menu

                assert not self.calls
                assert set(questions) == {"requested_work"}
                assert questions["requested_work"]["criteria"] == opening_action_menu("plan")
                assert set(body["state"]) == {"surface", "user_utterance", "page_title"}
                choices = {"requested_work": "write_current_page"}
            elif "existing_scope" in questions:
                choices = dict(
                    location_relation=("unstated_insertion_location" if caret_case
                        else "before_paragraph" if outcome == "relation_conflict" else "after_paragraph"),
                    existing_scope="none", page_edit_intent="page_edit",
                )
            elif "confirmed_work" in questions:
                locations = {row["alias"]: row["description"] for row in body["state"]["locations"]}
                choices = dict(confirmed_work="write_current_page", relation="after", row_choice="any_row",
                               scope="qualified" if qualified else "unscoped")
                if caret_case:
                    offered = body["state"].get("offered_caret_boundary")
                    assert offered == (None if outcome == "mid_paragraph_caret" else "after")
                    choices["scope"] = "caret_boundary" if offered else "unresolved"
                    if outcome == "conflicting_caret":
                        choices["relation"] = "before"
                choices.update({name: "exclude" if caret_case else "include"
                    for name in questions if name.startswith("passage")})
                choices.update({
                    alias: "include" if qualified and "right column" in label else "exclude"
                    for alias, label in locations.items()
                })
                choices.update({name: "exclude" for name in questions if name.startswith("candidate_")})
                choices.update(operation="finish_retrieval", post_read_plan="review_after_reads")
            else:
                return await super().handle_async_request(request)
            assert capture.document_id not in request.content.decode()
            assert capture.draft_page_presentation_sha256 not in request.content.decode()
            self.calls.append(request)
            answers = {name: dict(type="choice", choice=choice, confidence=1,
                probabilities={key: float(key == choice) for key in questions[name]["criteria"]})
                for name, choice in choices.items()}
            return httpx2.Response(200, request=request, json=dict(
                model=body["model"], answers=answers, usage=dict(input_tokens=31, output_tokens=7)))

    class ComposedWriter(WriterWire):
        async def handle_async_request(self, request):
            body = json.loads(request.content)
            self.adapter = wire.adapter
            assert capture.draft_page_presentation_sha256 not in request.content.decode()
            if outcome in {"ambiguous", "relation_conflict", "mid_paragraph_caret", "conflicting_caret"}:
                response = {"question": body["text"]["format"]["schema"]["properties"]["question"]["enum"][0]}
            else:
                response = dict(schema=POLICY, answer_segments=[dict(
                    kind="proposal", label="invented_idea", text="Keep a lantern ready.",
                )], limitations=[], requested_detail_gaps=[])
            self.text = json.dumps(response)
            return await super().handle_async_request(request)

    decisions, writer = ComposedChoices(), ComposedWriter(None, "")
    harness.decision_transport, harness.writer_transport = decisions, writer
    if outcome == "stale_layout":
        with pytest.raises(AgentTurnServiceError):
            execute_agent_turn(request, **kwargs)
        assert not decisions.calls and not writer.calls
        assert PlanActionDialogueService().get_by_key(capture.world_id, capture.idempotency_key) is None
        assert snapshot_plan(capture.document_id).page_presentation == layout
        return
    response = execute_agent_turn(request, **kwargs)
    assert response.answer.status == "ok"
    turn = kwargs["conversation_service"].inspect_turn(
        world_id=capture.world_id, turn_id=wire.adapter.turn.turn_id,
    )
    from application_state.agent_conversation.native_plan_opening import NativePlanAuthorScopeObservedV1

    intent = next(event for event in turn.graph_context_execution.events
                  if type(event) is NativePlanAuthorScopeObservedV1)
    assert intent.scope_observation.requested_work == "write_current_page"
    [selection] = [event for event in turn.graph_context_execution.events
                   if type(event) is NativePlanOpeningSelectedV3]
    assert intent.sequence < selection.sequence
    calls = len(decisions.calls), len(writer.calls)
    replay = execute_agent_turn(request, **kwargs)
    assert (len(decisions.calls), len(writer.calls)) == calls
    assert replay.plan_context.delivery_replay
    snapshot = snapshot_plan(capture.document_id)
    assert snapshot.markdown == markdown and snapshot.page_presentation == layout
    action = PlanActionDialogueService().get_by_key(capture.world_id, capture.idempotency_key)
    if outcome == "ordinary_caret":
        assert selection.implicit_caret_version == "v1"
        assert selection.target_resolution == "unique"
        assert response.plan_proposal.capture.slot_address.slot_id == "right"
        assert response.plan_proposal.capture.slot_address.relation == "after"
        assert replay.plan_proposal == response.plan_proposal
        assert action is not None and action.target_kind == "insert_at_slot_boundary"
        with pytest.raises(ValueError, match="complete target resolution"):
            NativePlanOpeningSelectedV3.model_validate(selection.model_dump() | {"implicit_caret_version": None})
    elif outcome == "selected":
        assert selection.target_resolution == "unique"
        assert response.plan_proposal is not None
        assert response.plan_proposal.capture.slot_address.slot_id == "right"
        assert replay.plan_proposal == response.plan_proposal
        assert action is not None and action.target_kind == "insert_at_slot_boundary"
        from types import SimpleNamespace
        from application_state.agent_conversation.native_plan_opening import composed_author_column, resolve_composed_opening
        from application_state.agent_conversation.plan_author_location import LiteralScopeName, NamedScopePath

        binding = selection.author_scope_binding
        missing_scope = NamedScopePath(names=(LiteralScopeName(text="Missing heading"),))
        for conflict in ({"scope": missing_scope}, {"relation": "replace_explicit_selection"}):
            constrained = binding.model_copy(update={
                "observation": binding.observation.model_copy(update=conflict),
            })
            assert resolve_composed_opening(
                capture, request.plan_placement_catalog, constrained, selection.composed_nomination,
                selection.author_operation,
            ) == dict(requested_work="clarify", target_resolution="unresolved",
                      placement_selector=None, target_capture_sha256=None)
        column_scope = NamedScopePath(names=(LiteralScopeName(text="the right column"),))
        composed_binding = binding.model_copy(update={
            "observation": binding.observation.model_copy(update={"scope": column_scope}),
        })
        def column_in(question):
            return composed_author_column(SimpleNamespace(
                column_scope_version="v1", author_scope_binding=composed_binding, question=question, dialogue=(),
            ))

        assert column_in("Add a warning after the gate in the right column.") == "right column"
        assert resolve_composed_opening(
            capture, request.plan_placement_catalog, composed_binding, selection.composed_nomination,
            selection.author_operation, author_column=column_in("Add a warning after the gate in the right column."),
        )["placement_selector"] == selection.placement_selector
        for question in (
            'Add a warning after the gate in the heading "Right Column".',
            'Add a warning after the gate in the Right Column heading.',
            'Add a warning after the gate in the Right Column subsection.',
            'Add a warning after the gate in the Right Column subheading.',
            'Add a warning after the quoted line "in the right column".',
        ):
            assert column_in(question) is None
            assert resolve_composed_opening(
                capture, request.plan_placement_catalog, composed_binding, selection.composed_nomination,
                selection.author_operation, author_column=column_in(question),
            )["target_resolution"] == "unresolved"
    else:
        assert selection.target_resolution == ("ambiguous" if outcome == "ambiguous" else "unresolved")
        assert response.plan_proposal is None and action is None


def test_caret_guidance_version_preserves_historical_scope_wire():
    from application_state.agent_conversation.native_plan_opening import (
        NativePlanAuthorScopeInputV1, prepare_author_scope_decision, validate_author_scope_wire,
    )

    historical = NativePlanAuthorScopeInputV1(
        question="Trace what the party learned.", dialogue=(), max_span_attempts=2048,
        quote_context=False, assess_page_edit=True, editor_focus="caret", implicit_caret_version="v1",
    )
    assert "caret_guidance_version" not in historical.model_dump()
    current = historical.model_copy(update={"caret_guidance_version": "v2"})
    old_request = prepare_author_scope_decision(historical)
    new_request = prepare_author_scope_decision(current)
    assert "When the author asks to add writing" in old_request.state["current_editor_focus"]
    assert "First determine the requested work" in new_request.state["current_editor_focus"]
    assert old_request.questions == new_request.questions
    assert {key: value for key, value in old_request.state.items() if key != "current_editor_focus"} == {
        key: value for key, value in new_request.state.items() if key != "current_editor_focus"
    }
    old_wire = json.dumps({
        "model": old_request.model,
        "state": old_request.state,
        "questions": {q.name: {"type": "choice", "instructions": q.question,
                                "criteria": q.option_descriptions} for q in old_request.questions},
    }).encode()
    validate_author_scope_wire(historical, old_wire)
    with pytest.raises(ValueError, match="reconstructed local choices"):
        validate_author_scope_wire(current, old_wire)
