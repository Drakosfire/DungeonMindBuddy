"""Real SDK preparation → host machine → broker reads → APP/source writer; synthetic."""

import asyncio
import json
from dataclasses import replace
from hashlib import sha256
from uuid import uuid4

import httpx2
import pytest
from generationengine import GenerationClient, GenerationEngineError
from generationengine.types import (
    BinaryDecisionQuestion,
    ChoiceDecisionQuestion,
    DecisionRequest,
)
from generationengine.decision_dispatch import DecisionDispatchGate
from generationengine.providers.typesafe_decision import TypeSafeDecisionProvider
from application_state.agent_conversation import AgentConversationService
from apps.live_control_server.services import build_jev_dispatch as policy
from apps.live_control_server.services.build_jev_driver import (
    AcquisitionBinding,
    sdk_answers,
)
from apps.live_control_server.services.build_jev_transitions import (
    AcquisitionIntent,
    Disposition,
)
from tests.test_agent_build_jev_controller_exposure import _native_reads, _acquire
from tests.test_agent_build_jev_dispatch import _adapter, build_case as _build_case
from tests.test_agent_build_source_passage_writer import answer, WriterWire, invoke


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def driver_case(build_case, monkeypatch, *, second=False):
    adapter, _ = _adapter(build_case)
    from graph_memory.evidence.source_artifact import (
        build_worldbuilding_source_artifact_id,
    )

    source = adapter.work.build_source
    artifact_id = build_worldbuilding_source_artifact_id(
        workspace_document_id=source.document_id,
        workspace_document_revision=source.revision,
        content_sha256=source.content_sha256,
    )
    discovery = {
        "schema": "dmb_build_source_discovery_v1",
        "discovery_only": True,
        "world_id": "native-build-world",
        "graph_revision": "native-rev-3",
        "source_artifact_id": artifact_id,
        "source_revision_id": "source-rev-one",
        "status": "complete",
        "eligible_count": 1,
        "next_page_token": None,
        "entries": [
            {
                "assertion_id": "observation-one",
                "subject_object_id": "frank",
                "subject_label": "Frank",
                "excerpt": "Frank believes a gate is haunted.",
            }
        ],
    }
    if second:
        discovery["entries"].append(
            {**discovery["entries"][0], "assertion_id": "observation-two"}
        )
        discovery["eligible_count"] = 2
    adapter.work = replace(adapter.work, build_source_discovery=discovery)
    adapter.bootstrap = replace(adapter.bootstrap, build_source_discovery=discovery)
    calls, text = _native_reads(adapter, monkeypatch)
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as native,
    )
    from graph_memory.interaction import expansion_executor
    from types import SimpleNamespace

    original_graph = native.get_object_with_reviewed_sources_direct_v3

    def graph(*args, **kwargs):
        value = original_graph(*args, **kwargs)
        return replace(
            value,
            result=value.result.model_copy(
                update={
                    "source_anchors": [
                        anchor.model_copy(update={"source_artifact_id": artifact_id})
                        for anchor in value.result.source_anchors
                    ]
                }
            ),
            source_pins=tuple(
                SimpleNamespace(**{**vars(pin), "source_artifact_id": artifact_id})
                for pin in value.source_pins
            ),
            reviewed_source_observations=tuple(
                row.model_copy(update={"source_artifact_id": artifact_id})
                for row in value.reviewed_source_observations
            ),
        )

    monkeypatch.setattr(native, "get_object_with_reviewed_sources_direct_v3", graph)
    original_source = expansion_executor.execute_read_graph_source

    def read(*args, **kwargs):
        value = json.loads(
            json.dumps(original_source(*args, **kwargs)).replace(
                "artifact-one", artifact_id
            )
        )
        for item in value["reads"]:
            item["result"]["contentSha256"] = source.content_sha256
            item["receipt"]["read_content_sha256"] = source.content_sha256
        return value

    monkeypatch.setattr(expansion_executor, "execute_read_graph_source", read)
    return adapter, adapter.create_build_jev_driver(), calls, text


class Wire(httpx2.AsyncBaseTransport):
    def __init__(self, selected):
        self.selected, self.calls = selected, []

    async def handle_async_request(self, request):
        self.calls.append(request)
        body = json.loads(request.content)
        answers = {}
        for name, q in body["questions"].items():
            if q["type"] == "noul":
                answers[name] = {"type": "noul", "noul": 0.99}
            else:
                labels = q["criteria"]
                choice = self.selected.get(name, next(iter(labels)))
                answers[name] = {
                    "type": "choice",
                    "choice": choice,
                    "confidence": 1.0,
                    "probabilities": {
                        label: float(label == choice) for label in labels
                    },
                }
        return httpx2.Response(
            200,
            request=request,
            json={
                "model": policy.MODEL,
                "usage": {"input_tokens": 23, "output_tokens": 4},
                "answers": answers,
            },
        )

    async def aclose(self):
        pass


def sdk(driver, plan, selected, *, alter=None):
    wire = Wire(selected)
    seen = []

    async def run():
        async def authorize(prepared):
            seen.append(prepared)
            return driver.authorize(alter(prepared) if alter else prepared)

        async def record(event):
            return driver._adapter.record_prepared_build_decision(event)

        provider = TypeSafeDecisionProvider(
            api_key="synthetic-not-a-credential",
            dispatch_gate=DecisionDispatchGate(authorize, record),
            transport=wire,
        )
        client = GenerationClient(decision_providers={"typesafe": provider})
        questions = [
            (
                BinaryDecisionQuestion
                if q["kind"] == "binary"
                else ChoiceDecisionQuestion
            ).model_validate(q)
            for q in plan.state()["decision"]["questions"]
        ]
        try:
            return await client.decide(
                DecisionRequest(
                    provider=policy.PROVIDER,
                    model=policy.MODEL,
                    state=plan.state(),
                    questions=questions,
                    max_transport_retries=0,
                )
            )
        finally:
            await client.aclose()

    return asyncio.run(run()), wire, seen


def start(build_case, monkeypatch):
    adapter, driver, calls, text = driver_case(build_case, monkeypatch)
    plan = driver.stage()
    aid = next(
        aid
        for aid in driver.step.state["legal_next_actions"]
        if aid.startswith("graph:")
    )
    result, wire, seen = sdk(
        driver, plan, {"sufficiency": "more_evidence", "next": aid}
    )
    step = driver.accept_decision(
        policy.MODEL,
        sdk_answers(result),
    )
    assert isinstance(step, AcquisitionIntent)
    return adapter, driver, calls, text, aid, plan, wire, seen


def acquire(adapter, driver, aid):
    graph, _ = _acquire(adapter)
    ids = tuple(str(eid) for eid in adapter.source_payloads)
    binding = AcquisitionBinding(graph_payloads=(graph,), source_event_ids=ids)
    driver.accept_acquisition({aid: binding})
    return binding


def test_real_sdk_host_machine_compact_exposure_and_source_writer(
    build_case, monkeypatch
):
    adapter, driver, calls, text, aid, first, wire, _ = start(build_case, monkeypatch)
    assert json.loads(wire.calls[0].content)["state"] == first.state()
    args = driver.action_arguments(aid)
    assert args["operation"] == "observations" and args["observationIds"] == [
        "observation-one"
    ]
    binding = acquire(adapter, driver, aid)
    plan = driver.stage()
    view = plan.state()["decision"]["state"]
    assert view["evidence"][0]["epistemic_kind"] == "belief"
    assert text in json.dumps(view) and "requirements" not in view
    uid = driver.step.state["evidence"][0]["id"]
    result, wire, seen = sdk(
        driver, plan, {"sufficiency": "more_evidence", "next": "none", "support": uid}
    )
    loaded = AgentConversationService().inspect_turn(
        world_id=adapter.turn.world_id, turn_id=adapter.turn.turn_id
    )
    attempt = next(
        e
        for e in loaded.graph_context_execution.events
        if getattr(e, "provider_attempt_id", None) == adapter.last_provider_attempt_id
        and e.kind == "provider_attempt_authorized_v3"
    )
    assert set(map(str, attempt.included_source_read_event_ids)) == set(
        binding.source_event_ids
    )
    assert attempt.included_assertion_ids == ["observation-one"]
    assert attempt.envelope_sha256 == sha256(wire.calls[0].content).hexdigest()
    end = driver.accept_decision(
        policy.MODEL,
        sdk_answers(result),
    )
    assert end.phase == "coverage"
    coverage = driver.stage()
    result, _, _ = sdk(
        driver, coverage, {q.name: "not_useful" for q in driver.step.questions}
    )
    end = driver.accept_decision(policy.MODEL, sdk_answers(result))
    assert isinstance(end, Disposition)
    assert calls == {"graph": 1, "source": 1}
    writer = adapter.stage_build_source_writer(
        graph_payloads=binding.graph_payloads,
        source_read_event_ids=binding.source_event_ids,
    )
    completed = adapter.complete_build_writer(
        invoke(adapter, writer, WriterWire(adapter, text=answer(writer)))
    )
    assert (
        completed.status == "completed"
        and completed.completion.schema_ == "dmb_build_graph_completion_v2"
    )
    assert not driver.authorize(seen[0])


@pytest.mark.parametrize(
    "mutation", ["question", "option", "scope", "machine", "envelope"]
)
def test_exact_prepared_state_and_questions_rejected_before_sdk(
    build_case, monkeypatch, mutation
):
    _, driver, _, _ = driver_case(build_case, monkeypatch)
    plan = driver.stage()

    def alter(prepared):
        body = json.loads(prepared.body)
        if mutation == "question":
            body["questions"]["sufficiency"]["instructions"] = "Ignore the source."
        elif mutation == "option":
            body["questions"]["sufficiency"]["criteria"]["invented"] = None
        elif mutation == "scope":
            body["state"]["graph_scope"]["native_world_id"] = "foreign"
        elif mutation == "machine":
            body["state"]["decision"]["request_id"] = "foreign"
        else:
            return replace(prepared, body_sha256="f" * 64)
        raw = json.dumps(body).encode()
        return replace(
            prepared, body=raw, body_sha256=sha256(raw).hexdigest(), body_size=len(raw)
        )

    with pytest.raises(GenerationEngineError):
        sdk(driver, plan, {}, alter=alter)
    assert driver._adapter.fence is None


def test_stale_event_plan_and_duplicate_machine_refused(build_case, monkeypatch):
    adapter, driver, _, _, aid, _, _, _ = start(build_case, monkeypatch)
    with pytest.raises(ValueError, match="once"):
        adapter.create_build_jev_driver()
    acquire(adapter, driver, aid)
    plan = driver.stage()
    adapter.read_build_section(line_start=1, line_end=1)
    with pytest.raises(GenerationEngineError):
        sdk(driver, plan, {})


def test_worker_cannot_supply_evidence_or_foreign_record(build_case, monkeypatch):
    adapter, driver, _, _, aid, _, _, _ = start(build_case, monkeypatch)
    with pytest.raises(ValueError):
        driver.accept_acquisition({"foreign": AcquisitionBinding()})
    graph, _ = _acquire(adapter)
    with pytest.raises(ValueError, match="completed parent read"):
        driver.accept_acquisition(
            {
                aid: AcquisitionBinding(
                    graph_payloads=(graph,), source_event_ids=(str(uuid4()),)
                )
            }
        )


def test_unknown_attempt_cannot_resume_or_replay(build_case, monkeypatch):
    _, driver, _, _ = driver_case(build_case, monkeypatch)
    plan = driver.stage()
    # Obtain a genuine prepared wire request via SDK preflight, but refuse send.
    captured = []

    def stop(prepared):
        captured.append(prepared)
        return replace(prepared, body_sha256="f" * 64)

    with pytest.raises(GenerationEngineError):
        sdk(driver, plan, {}, alter=stop)
    prepared = captured[0]
    assert driver.authorize(prepared)
    from generationengine.decision_dispatch import DecisionDispatchEvent

    assert driver._adapter.record_prepared_build_decision(
        DecisionDispatchEvent(prepared, "sending")
    )
    assert driver._adapter.record_prepared_build_decision(
        DecisionDispatchEvent(prepared, "outcome_unknown")
    )
    assert not driver.authorize(prepared)
    with pytest.raises(ValueError, match="unresolved"):
        driver.accept_decision(policy.MODEL, {})
    with pytest.raises(ValueError, match="fresh"):
        driver.stage()


def test_saved_section_is_host_materialized_and_bound_to_provider(
    build_case, monkeypatch
):
    adapter, driver, _, _ = driver_case(build_case, monkeypatch)
    plan = driver.stage()
    aid = next(
        a for a in driver.step.state["legal_next_actions"] if a.startswith("saved:")
    )
    result, _, _ = sdk(driver, plan, {"sufficiency": "more_evidence", "next": aid})
    driver.accept_decision(policy.MODEL, sdk_answers(result))
    args = driver.action_arguments(aid)
    read = json.loads(adapter.read_build_section(**args))
    driver.accept_acquisition(
        {aid: AcquisitionBinding(section_read_id=read["read_id"])}
    )
    plan = driver.stage()
    result, _, _ = sdk(driver, plan, {"sufficiency": "more_evidence", "next": "none"})
    loaded = AgentConversationService().inspect_turn(
        world_id=adapter.turn.world_id, turn_id=adapter.turn.turn_id
    )
    included = [
        e
        for e in loaded.graph_context_execution.events
        if e.kind == "build_section_provider_inclusion_v1"
    ]
    assert (
        included
        and included[-1].provider_attempt_id == adapter.last_provider_attempt_id
    )
    assert "saved_build_world_reference" in json.dumps(plan.state())
    assert read["text"] in json.dumps(plan.state(), ensure_ascii=False).replace(
        "\\n", "\n"
    )


@pytest.mark.parametrize(
    "mutation", ["source_body", "source_range", "graph_qualification", "source_id"]
)
def test_tampered_host_material_never_becomes_driver_evidence(
    build_case, monkeypatch, mutation
):
    adapter, driver, _, _, aid, _, _, _ = start(build_case, monkeypatch)
    graph, _ = _acquire(adapter)
    source_id = next(iter(adapter.source_payloads))
    if mutation == "graph_qualification":
        event = next(iter(adapter.operation_payloads))
        raw = json.loads(adapter.operation_payloads[event])
        raw["reviewedSourceObservations"][0]["epistemicKind"] = "fact"
        adapter.operation_payloads[event] = json.dumps(raw)
    else:
        raw = json.loads(adapter.source_payloads[source_id])
        raw[
            {
                "source_body": "content",
                "source_range": "lineEnd",
                "source_id": "sourceArtifactId",
            }[mutation]
        ] = 99 if mutation == "source_range" else "forged"
        adapter.source_payloads[source_id] = json.dumps(raw)
    with pytest.raises(ValueError):
        driver.accept_acquisition(
            {
                aid: AcquisitionBinding(
                    graph_payloads=(graph,), source_event_ids=(str(source_id),)
                )
            }
        )


def test_acquired_bytes_are_reverified_before_a_later_dispatch(build_case, monkeypatch):
    adapter, driver, _, _, aid, _, _, _ = start(build_case, monkeypatch)
    acquire(adapter, driver, aid)
    source_id = next(iter(adapter.source_payloads))
    raw = json.loads(adapter.source_payloads[source_id])
    raw["content"] += "Changed"
    adapter.source_payloads[source_id] = json.dumps(raw)
    with pytest.raises(ValueError):
        driver.stage()


def test_two_observations_share_one_complete_source_batch_losslessly(
    build_case, monkeypatch
):
    from types import SimpleNamespace
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as native,
    )
    from graph_memory.interaction import expansion_executor

    adapter, driver, _, _ = driver_case(build_case, monkeypatch, second=True)
    original_graph = native.get_object_with_reviewed_sources_direct_v3

    def graph(services, request, **kwargs):
        result = original_graph(services, request, **kwargs)
        selected = request.observation_ids[0]
        second = selected == "observation-two"
        anchor = "anchor-two" if second else "anchor-one"
        evidence = "evidence-two" if second else "evidence-one"
        source_anchor = result.result.source_anchors[0].model_copy(
            update={
                "anchor_id": anchor,
                "evidence_ref_id": evidence,
                "supporting_assertion_ids": [selected],
            }
        )
        return replace(
            result,
            result=result.result.model_copy(
                update={
                    "operation": "observations",
                    "requested_node_id": None,
                    "matched_node_ids": ["frank"],
                    "source_anchors": [source_anchor],
                }
            ),
            source_pins=(
                SimpleNamespace(
                    **{
                        **vars(result.source_pins[0]),
                        "anchor_id": anchor,
                        "evidence_ref_id": evidence,
                    }
                ),
            ),
            reviewed_source_observations=(
                result.reviewed_source_observations[0].model_copy(
                    update={"assertion_id": selected, "evidence_ref_ids": [evidence]}
                ),
            ),
        )

    from apps.live_control_server.integrations.dungeonmind import (
        selected_observation_reads,
    )

    monkeypatch.setattr(selected_observation_reads, "select_observations_direct", graph)
    original_read = expansion_executor.execute_read_graph_source
    batches = []

    def read(arguments, **kwargs):
        batches.append(arguments["anchorIds"])
        results = []
        for anchor in arguments["anchorIds"]:
            value = original_read({**arguments, "anchorIds": ["anchor-one"]}, **kwargs)
            if anchor == "anchor-two":
                value = json.loads(
                    json.dumps(value)
                    .replace("anchor-one", "anchor-two")
                    .replace("evidence-one", "evidence-two")
                    .replace("source-read-one", "source-read-two")
                )
            results.extend(value["reads"])
        return {**value, "reads": results}

    monkeypatch.setattr(expansion_executor, "execute_read_graph_source", read)
    plan = driver.stage()
    result, _, _ = sdk(driver, plan, {"sufficiency": "more_evidence", "next": "none"})
    coverage = driver.accept_decision(policy.MODEL, sdk_answers(result))
    assert coverage.phase == "coverage"
    plan = driver.stage()
    selected = {
        q.name: ("not_useful" if "saved:" in q.question else "useful")
        for q in driver.step.questions
    }
    result, _, _ = sdk(driver, plan, selected)
    acquisition = driver.accept_decision(policy.MODEL, sdk_answers(result))
    assert isinstance(acquisition, AcquisitionIntent) and len(acquisition.actions) == 2
    payloads = {}
    for action in acquisition.actions:
        payloads[action.id] = adapter.broker_graph_operation(
            {
                "toolName": "expand_graph_retrieval",
                "arguments": driver.action_arguments(action.id),
            }
        )["resultJson"]
    assert adapter.failure is None, (str(adapter.failure), payloads)
    assert all("sourceAnchors" in json.loads(p) for p in payloads.values()), payloads
    source_reply = adapter.broker_source_read(
        {
            "toolName": "read_graph_source",
            "arguments": {
                "retrievalSessionId": adapter.bootstrap.retrieval_session.id,
                "anchorIds": ["anchor-one", "anchor-two"],
                "maxChars": 4000,
            },
        }
    )
    assert adapter.failure is None
    events = tuple(str(eid) for eid in adapter.source_payloads)
    assert len(events) == 1 and batches == [["anchor-one", "anchor-two"]], source_reply
    driver.accept_acquisition(
        {
            aid: AcquisitionBinding(graph_payloads=(payload,), source_event_ids=events)
            for aid, payload in payloads.items()
        }
    )
    plan = driver.stage()
    view = plan.state()["decision"]["state"]
    assert len(view["evidence"]) == 2 and len(view["passages"]) == 1
    assert len(plan.source_event_ids) == 1
    result, _, _ = sdk(
        driver,
        plan,
        {"sufficiency": "sufficient", "support": view["evidence"][0]["id"]},
    )
    loaded = AgentConversationService().inspect_turn(
        world_id=adapter.turn.world_id, turn_id=adapter.turn.turn_id
    )
    event = next(
        e
        for e in loaded.graph_context_execution.events
        if e.kind == "provider_attempt_authorized_v3"
        and e.provider_attempt_id == adapter.last_provider_attempt_id
    )
    assert len(event.included_source_read_event_ids) == 1
    assert set(event.included_assertion_ids) == {"observation-one", "observation-two"}
