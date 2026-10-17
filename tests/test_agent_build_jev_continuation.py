"""Receipt-bound continuation through real SDK/APP; synthetic, no network."""
import json
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256

import pytest

from apps.live_control_server.services import build_jev_dispatch as policy
from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
from apps.live_control_server.services.build_jev_driver import BuildJevDriver
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from tests.test_agent_build_jev_ordinary_harness import (
    DecisionWire, WriterWire, ordinary_case, build_case as _build_case,
)
from tests.test_agent_build_governed_graph import execute


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def test_actual_sdk_continuations_have_historical_commitment_not_initial_packet(
    build_case, monkeypatch, tmp_path
):
    decisions, writer = DecisionWire(), WriterWire()
    class TwoDecisions(BuildJevHarness):
        async def _decide(self, adapter, driver):
            await super()._decide(adapter, driver)
            if len(decisions.calls) == 2:
                raise SystemExit("initial/continuation exposure proof before acquisition")
    runtime = TwoDecisions(decision_transport=decisions, writer_transport=writer)
    case, _ = ordinary_case(build_case, monkeypatch)
    from graph_memory.interaction.authority_classifier import claims_from_retrieval_result
    from graph_memory.interaction.session import GraphRetrievalSession, CoverageState, SourceAnchorState
    source, request, bootstrap = case
    claims = claims_from_retrieval_result({
        "relationships": [{"edgeId": "rel:seed", "sourceNodeId": "node:one", "targetNodeId": "node:two", "predicate": "guards", "evidenceRefIds": ["ev:one"]}],
        "sourceAnchors": [{"anchorId": "anchor:one", "revisionId": "native-rev-3", "evidenceRefId": "ev:one", "readable": True, "supportingGraphObjectIds": []}],
    }, revision_id="native-rev-3")
    bootstrap = replace(bootstrap, retrieval_session=GraphRetrievalSession(
        snapshot=bootstrap.retrieval_session.snapshot, question=request.message,
        coverage=CoverageState(state="ready"), claims=claims,
        source_anchors=[SourceAnchorState(anchor_id="anchor:one", readable=True)]),
        candidate_relationship_ids=("rel:seed",), candidate_evidence_ref_ids=("ev:one",),
        evidence_by_anchor_id={"anchor:one": "ev:one"},
        source_scope_anchors=({"anchor_id": "anchor:one", "evidence_ref_id": "ev:one", "source_artifact_id": "artifact:one", "source_revision_id": "source-rev:one"},))
    with pytest.raises(SystemExit):
        execute((source, request, bootstrap), tmp_path, runtime)
    events = runtime.adapter.turn.graph_context_execution.events
    from application_state.agent_conversation.types import ProviderAttemptAuthorizedEventV3
    authorizations = [e for e in events if isinstance(e, ProviderAttemptAuthorizedEventV3)]
    assert authorizations[0].included_relationship_ids == ["rel:seed"]
    assert all("rel:seed" not in e.included_relationship_ids and "ev:one" not in e.included_evidence_ref_ids for e in authorizations[1:])
    bodies = [json.loads(call.content) for call in decisions.calls]
    assert "initialClaimPacket" in bodies[0]["state"]
    assert len(bodies) == 2 and writer.calls == []
    receipt = runtime.adapter.turn.graph_context_receipt
    for body in bodies[1:]:
        state = body["state"]
        assert state["schema"] == policy.PHASE_SCHEMA
        assert state["input_policy"] == policy.PHASE_POLICY
        assert "initialClaimPacket" not in state
        assert state["historical_initial"]["context_receipt_sha256"] == receipt.context_receipt_sha256
        assert state["historical_initial"]["initial_envelope_sha256"] == receipt.assembled_input.assembled_input_sha256
        assert "questions" not in state["decision"]
        logical = state["decision"]["state"]
        assert "legal_next_actions" not in logical
        if "action_catalog" in logical:
            table = logical["action_catalog"]
            assert table["columns"] == ["id", "kind", "hint", "hint_truncated"]
            assert len({r[0] for r in table["rows"]}) == len(table["rows"])


@pytest.mark.parametrize("mutation", ["missing", "foreign_receipt", "foreign_envelope", "policy", "sequence", "prior_attempt", "turn", "tampered_parent_receipt"])
def test_mutated_continuation_is_refused_before_second_send(
    build_case, monkeypatch, tmp_path, mutation
):
    original = BuildJevDriver.authorize
    rejected = []

    def authorize(driver, prepared):
        body = json.loads(prepared.body)
        if body["state"]["schema"] != policy.PHASE_SCHEMA:
            return original(driver, prepared)
        binding = body["state"]["historical_initial"]
        if mutation == "tampered_parent_receipt":
            binding["context_receipt_sha256"] = "f" * 64
            driver._pending = replace(driver._pending, state_json=policy.canonical(body["state"]))
        elif mutation == "missing":
            body["state"].pop("historical_initial")
        else:
            key, value = {
                "foreign_receipt": ("context_receipt_sha256", "f" * 64),
                "foreign_envelope": ("initial_envelope_sha256", "f" * 64),
                "policy": ("execution_policy_sha256", "f" * 64),
                "sequence": ("event_sequence", binding["event_sequence"] + 1),
                "prior_attempt": ("prior_provider_attempt_id", "foreign"),
                "turn": ("turn_id", "foreign"),
            }[mutation]
            binding[key] = value
        raw = json.dumps(body).encode()
        accepted = original(driver, replace(prepared, body=raw, body_size=len(raw), body_sha256=sha256(raw).hexdigest()))
        rejected.append(accepted)
        return accepted

    monkeypatch.setattr(BuildJevDriver, "authorize", authorize)
    decisions, writer = DecisionWire(), WriterWire()
    runtime = BuildJevHarness(decision_transport=decisions, writer_transport=writer)
    case, _ = ordinary_case(build_case, monkeypatch)
    with pytest.raises(AgentTurnServiceError):
        execute(case, tmp_path, runtime)
    assert rejected == [False]
    assert len(decisions.calls) == 1 and writer.calls == []


def test_factored_catalog_reconstructs_exact_parent_intent(build_case, monkeypatch):
    from tests.test_agent_build_jev_driver_decisions import driver_case
    _, driver, _, _ = driver_case(build_case, monkeypatch)
    intent = driver.step
    original = intent.model_dump(mode="json")
    factored = deepcopy(policy.factored_decision(intent))
    state = factored["state"]
    table = state.pop("action_catalog")
    rows = table["rows"]
    state["legal_next_actions"] = {aid: hint for aid, kind, hint, truncated in rows}
    state["legal_action_kinds"] = {kind: [row[0] for row in rows if row[1] == kind] for kind in table["kinds"]}
    state["truncated_discovery_hints"] = [row[0] for row in rows if row[3]]
    factored["questions"] = original["questions"]
    assert policy.canonical(factored) == policy.canonical(original)


@pytest.mark.parametrize("mutation", ["none", "qualification", "bool_type", "missing_anchor", "foreign_anchor", "missing_ref", "unrelated_support", "complete_fragments", "missing_fragment"])
def test_selected_record_closure_ignores_only_unrelated_envelope_metadata(mutation):
    from apps.live_control_server.services.build_jev_driver import verify_selected_presentation
    row = dict(assertionId="observation-one", subjectNodeId="frank", text="Frank believes the gate is haunted.",
               evidenceRefIds=["ev:one"], epistemicKind="belief", temporalScope="past", campaignId="c1", visible=True)
    anchor = dict(anchorId="anchor:one", evidenceRefId="ev:one", supportingAssertionIds=["observation-one"],
                  sourceArtifactId="artifact:one", sourceRevisionId="source-rev:one")
    raw = dict(reviewedSourceObservations=[row], sourceAnchors=[anchor], claimLedger=[{"not_exposed": True}],
               unrelated_metadata={"not_exposed": True})
    records = [dict(path=["reviewedSourceObservations", 0], value=deepcopy(row)),
               dict(path=["sourceAnchors", 0], value=deepcopy(anchor))]
    if mutation == "qualification":
        records[0]["value"].pop("epistemicKind")
    elif mutation == "bool_type":
        records[0]["value"]["visible"] = 1
    elif mutation == "missing_anchor":
        records.pop()
    elif mutation == "foreign_anchor":
        records[1]["value"]["sourceRevisionId"] = "foreign"
    elif mutation == "missing_ref":
        records[0]["value"]["evidenceRefIds"] = []
    elif mutation == "unrelated_support":
        records[1]["path"] = ["sourceAnchors", 1]
        records[1]["value"]["supportingAssertionIds"] = ["other"]
    elif mutation in {"complete_fragments", "missing_fragment"}:
        text = policy.canonical(row)
        middle = len(text) // 2
        records.pop(0)
        for start,end in [(0,middle),(middle,len(text))]:
            records.append(dict(path=["reviewedSourceObservations",0], start=start, end=end,
                                length=len(text), sha256=sha256(text.encode()).hexdigest(),
                                fragmentEncoding="json", fragment=text[start:end]))
        if mutation == "missing_fragment":
            records.pop()
    payloads = (json.dumps(dict(schema="dmb_graph_tool_page_v1", records=records)),)
    if mutation in {"none", "complete_fragments"}:
        verify_selected_presentation(raw, payloads, "observation-one")
    else:
        with pytest.raises(ValueError):
            verify_selected_presentation(raw, payloads, "observation-one")


def test_source_batch_planning_reserves_only_remaining_character_allowance(monkeypatch):
    from types import SimpleNamespace
    from uuid import uuid4
    from application_state.agent_conversation import types as ledger

    used, requests, accepted = [1615], [], []
    event_id = uuid4()
    execution = SimpleNamespace(policy=SimpleNamespace(
        max_source_read_chars=96000, max_chars_per_source_read=12000), events=[])
    raw = json.dumps({"sourceAnchors": [{"anchorId": f"anchor:{n}"} for n in range(9)]})
    monkeypatch.setattr(ledger, "source_read_character_usage", lambda policy, events: used[0])

    def read(call):
        args = call["arguments"]
        # This owning admission precondition used to reject the first fixed batch of8.
        assert used[0] + len(args["anchorIds"]) * args["maxChars"] <= 96000
        requests.append(args)
        used[0] += 100 * len(args["anchorIds"])
        return {"resultJson": json.dumps({"schema": "dmb_read_graph_source_batch_v1"})}

    adapter = SimpleNamespace(
        failure=None, operation_payloads={event_id: raw},
        bootstrap=SimpleNamespace(retrieval_session=SimpleNamespace(id="session:one")),
        _broker_execution=lambda: execution,
        _tool_presentation=lambda: SimpleNamespace(inclusion=lambda tool, payloads: [SimpleNamespace(event_id=event_id)]),
        broker_graph_operation=lambda call: {"resultJson": raw}, broker_source_read=read,
    )
    driver = SimpleNamespace(
        step=SimpleNamespace(actions=[SimpleNamespace(id="graph:one", kind="graph_observations")]),
        action_arguments=lambda action_id: {}, accept_acquisition=accepted.append,
    )
    BuildJevHarness._acquire(adapter, driver)
    assert [len(args["anchorIds"]) for args in requests] == [7, 2]
    assert {aid for args in requests for aid in args["anchorIds"]} == {f"anchor:{n}" for n in range(9)}
    assert len(accepted) == 1
