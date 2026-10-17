"""Batch scheduling uses one acknowledged judgment; synthetic decisions are not semantic accuracy."""

import json

import httpx2
import pytest

from application_state.agent_conversation import (
    AgentConversationService,
    types as ledger,
)
from apps.live_control_server.services.build_jev_dispatch import PHASE_POLICY
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from apps.live_control_server.services.build_jev_transitions import (
    BuildJevTransitions,
    AcquisitionIntent,
    FRONTIER_POLICY,
    JOINT_SUPPORT_POLICY,
    READ_BATCH_POLICY,
)
from tests.test_build_jev_transitions import SCOPE, actions, answer, unit
from tests.test_build_jev_frontier import coverage_reply, negative
from tests.test_build_jev_estimated_continuations import counter
from tests.test_agent_build_jev_ordinary_harness import (
    DecisionWire,
    WriterWire,
    ordinary_case,
    build_case as _build_case,
)
from tests.test_agent_build_governed_graph import execute


def machine(*labels, batching=True):
    return BuildJevTransitions(
        "How do these places connect?",
        SCOPE,
        actions(*labels),
        frontier_policy=FRONTIER_POLICY,
        phase_input_policy=PHASE_POLICY,
        support_policy=JOINT_SUPPORT_POLICY,
        acquisition_policy=READ_BATCH_POLICY if batching else None,
    )


def judged_batch(m):
    answer(m, next_id="none")
    return coverage_reply(m, ["unknown", "useful", negative(0.7), negative(0.95)])


def test_one_judgment_batches_useful_then_unknown_and_reassesses_complete_basis():
    m = machine("Ambiguous link", "Known link", "Deferred", "Excluded")
    batch = judged_batch(m)
    assert isinstance(batch, AcquisitionIntent)
    assert [a.id for a in batch.actions] == ["a1", "a0"]
    assert m._deferred == {"a2"} and m._excluded == {"a3"}
    old_basis = m._basis()
    m.accept_acquisition(
        {
            "a1": (unit("u1", "Assembly governs Harbor."),),
            "a0": (
                unit(
                    "u0",
                    "Aster leads the assembly.",
                    epistemic_kind="belief",
                    temporal_scope={"as_of": "earlier"},
                ),
            ),
        }
    )
    assert m.step.phase == "assess" and len(m.step.state["evidence"]) == 2
    assert m.step.state["acquisition_policy"] == READ_BATCH_POLICY
    assert m._visited == {"a0", "a1"} and m._coverage_basis is None
    assert not m._excluded and not m._deferred and m._basis() != old_basis
    assert len(m._coverage_judgments) == 1
    assert m._units["u0"].epistemic_kind == "belief"
    assert m._units["u0"].temporal_scope == {"as_of": "earlier"}
    answer(m, label="conflict", relevance={"joint_support": 1.0})
    assert m.step.state["assessment_binding"]["conflict"]
    assert set(m.step.state["legal_next_actions"]) == {"a2", "a3"}


@pytest.mark.parametrize("fault", ["missing", "foreign", "hash", "duplicate"])
def test_bad_batch_refuses_without_partially_committing_evidence(fault):
    m = machine("Ambiguous", "Useful", "Deferred", "Excluded")
    judged_batch(m)
    deliveries = {
        "a1": (unit("u1", "Assembly governs Harbor."),),
        "a0": (unit("u0", "Aster leads assembly."),),
    }
    if fault == "missing":
        deliveries.pop("a0")
    elif fault == "foreign":
        deliveries["a0"] = (
            deliveries["a0"][0].model_copy(
                update={"scope": SCOPE.model_copy(update={"world_id": "foreign"})}
            ),
        )
    elif fault == "hash":
        deliveries["a0"] = (
            deliveries["a0"][0].model_copy(update={"content_sha256": "0" * 64}),
        )
    else:
        deliveries["a0"] = (deliveries["a1"][0],)
    with pytest.raises(ValueError):
        m.accept_acquisition(deliveries)
    assert m.step.status == "refused" and not m._units and not m._visited


def test_old_fieldsets_single_acquisition_and_basis_remain_distinct():
    m = machine("Ambiguous", "Useful", "Deferred", "Excluded", batching=False)
    assert [a.id for a in judged_batch(m).actions] == ["a1"]
    assert "acquisition_policy" not in m._decision("coverage").state
    assert (
        "acquisition_policy"
        not in ledger.BuildWriterBudgetActionControllerWriterPolicyV1.model_fields
    )
    assert m._basis() != machine("Ambiguous", "Useful", "Deferred", "Excluded")._basis()
    with pytest.raises(ValueError, match="read batching"):
        BuildJevTransitions(
            "Question", SCOPE, actions("A"), acquisition_policy=READ_BATCH_POLICY
        )
    with pytest.raises(ValueError, match="read batching"):
        BuildJevTransitions(
            "Question", SCOPE, actions("A"), acquisition_policy="unknown"
        )


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


class BatchDecisions(DecisionWire):
    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        payload = json.loads(response.content)
        for key, q in json.loads(request.content)["questions"].items():
            selected = (
                "none"
                if key == "next"
                else "unknown"
                if key.startswith("use_")
                else None
            )
            if selected is not None:
                payload["answers"][key] = dict(
                    type="choice",
                    choice=selected,
                    confidence=1,
                    probabilities={k: float(k == selected) for k in q["criteria"]},
                )
        return httpx2.Response(200, request=request, json=payload)


def test_real_sdk_mixed_batch_persists_all_bindings_and_one_writer(
    build_case, monkeypatch, tmp_path
):
    case, reads = ordinary_case(build_case, monkeypatch)
    decisions, writer = BatchDecisions(), WriterWire()
    result = execute(
        case,
        tmp_path,
        BuildJevHarness(
            decision_transport=decisions, writer_transport=writer, accounting=counter()
        ),
    )
    assert result.answer.text == "Frank believes the western gate is haunted."
    assert reads == {"graph": 1, "source": 1} and len(writer.calls) == 1
    phases = [
        json.loads(call.content)["state"]["decision"]["phase"]
        for call in decisions.calls
    ]
    assert phases == ["select", "navigate", "coverage", "assess"]
    packet = json.loads(json.loads(writer.calls[0].content)["input"])
    assert packet["exposure"]["saved_sections"]
    service = AgentConversationService()
    turn = service.list_turns(
        "elderwyld", service.get_world_pointer("elderwyld").active_conversation_id
    )[0]
    assert turn.status == "completed"
    assert isinstance(
        turn.graph_context_execution.policy,
        ledger.BuildReadBatchActionControllerWriterPolicyV1,
    )
    assert turn.graph_context_execution.policy.acquisition_policy == READ_BATCH_POLICY
    assert (
        turn.graph_context_execution.policy.writer_context_budget.context_limit_tokens
        == 128000
    )
    restored = ledger.PlanWorldGraphExecutionV3.model_validate_json(
        turn.graph_context_execution.model_dump_json(by_alias=True)
    )
    assert restored == turn.graph_context_execution


def test_changed_runtime_acquisition_policy_refuses_before_next_send(
    build_case, monkeypatch, tmp_path
):
    class DriftHarness(BuildJevHarness):
        async def _decide(self, adapter, driver):
            await super()._decide(adapter, driver)
            if len(self.calls) == 1:
                adapter.budget["buildJevActions"]["acquisition_policy"] = None

    case, _ = ordinary_case(build_case, monkeypatch)
    decisions, writer = BatchDecisions(), WriterWire()
    with pytest.raises(Exception, match="could not complete safely"):
        execute(
            case,
            tmp_path,
            DriftHarness(
                decision_transport=decisions,
                writer_transport=writer,
                accounting=counter(),
            ),
        )
    assert len(decisions.calls) == 1 and not writer.calls
