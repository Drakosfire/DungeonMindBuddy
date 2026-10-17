"""Selection must preserve whole-event exposure and refuse forged producer proof."""
import json
import os
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import httpx
import httpx2
import pytest

from application_state.agent_conversation import AgentConversationService, types as ledger
from application_state.agent_conversation import writer_evidence_selection as selection
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from apps.live_control_server.services.build_jev_runtime import load_offline_accounting
from tests.test_agent_build_jev_ordinary_harness import DecisionWire, WriterWire, ordinary_case
from tests.test_agent_build_jev_dispatch import build_case as _build_case
from tests.test_agent_build_governed_graph import execute


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    monkeypatch.setenv("TYPESAFE_JEV_API_KEY", "synthetic-only")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-only")
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


@pytest.fixture
def accounting():
    asset = os.environ.get("DMB_TEST_JEV_TOKENIZER_FILE")
    if not asset:
        pytest.skip("existing verified offline tokenizer asset required")
    return load_offline_accounting(Path(asset))


def test_whole_event_closure_retains_unselected_sibling_and_uncertainty():
    catalog = {
        "a": {"kind": "native_passage", "source_event_ids": ["event-one"]},
        "b": {"kind": "native_passage", "source_event_ids": ["event-one"]},
        "c": {"kind": "native_passage", "source_event_ids": ["event-two"]},
        "saved:x": {"kind": "saved_section", "section": {"read_id": "read-one"}},
    }
    closure = selection.close_selection(catalog, {
        "a": "qualification_or_conflict", "b": "irrelevant", "c": "irrelevant", "saved:x": "uncertain"})
    assert closure == {"requested_unit_ids": ["a", "saved:x"], "expanded_unit_ids": ["a", "b", "saved:x"],
                       "source_event_ids": ["event-one"], "section_read_ids": ["read-one"],
                       "omitted_unit_ids": ["c"]}
    with pytest.raises(ValueError, match="complete"):
        selection.close_selection(catalog, {"a": "direct_support"})
    with pytest.raises(ValueError, match="complete"):
        selection.close_selection(catalog, {key: "invented" for key in catalog})


class SelectionWire(DecisionWire):
    def __init__(self, mode="normal"):
        super().__init__()
        self.mode = mode

    async def handle_async_request(self, request):
        body = json.loads(request.content)
        selecting = body["state"].get("writer_selection_policy") == selection.POLICY
        if selecting and self.mode == "unknown_attempt":
            self.calls.append(request)
            raise httpx2.ReadTimeout("synthetic selection outcome unknown", request=request)
        response = await super().handle_async_request(request)
        data = response.json()
        for key, answer in data["answers"].items():
            labels = body["questions"][key].get("criteria", {})
            chosen = None
            if selecting and self.mode == "irrelevant":
                chosen = "irrelevant"
            elif selecting and self.mode == "incomplete":
                del data["answers"][key]
                break
            elif not selecting and key == "next" and self.mode == "saved_only":
                chosen = next((label for label in labels if label.startswith("saved:")), "none")
            elif not selecting and key == "next" and self.mode == "empty":
                chosen = "none"
            if chosen is not None:
                answer.update(choice=chosen, probabilities={label: float(label == chosen) for label in labels})
        return httpx2.Response(200, request=request, json=data)


class SavedWriter(WriterWire):
    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        packet = json.loads(json.loads(request.content)["input"])
        sections = packet["exposure"]["saved_sections"]
        if packet["opened_passages"] or not sections:
            return response
        data = response.json()
        data["output"][0]["content"][0]["text"] = json.dumps({
            "answer_context_status": "source_grounded_partial",
            "answer_segments": [{"kind": "saved_source_claim", "text": sections[0]["text"],
                                 "section_read_ids": [sections[0]["read_id"]]}],
            "limitations": ["partial_retrieval"],
        })
        return httpx.Response(200, request=request, json=data)


def run_case(build_case, monkeypatch, tmp_path, accounting, mode="normal"):
    case, reads = ordinary_case(build_case, monkeypatch)
    decisions, writer = SelectionWire(mode), SavedWriter()
    harness = BuildJevHarness(decision_transport=decisions, writer_transport=writer, accounting=accounting)
    return case, reads, decisions, writer, harness


@pytest.mark.parametrize("mode", ["normal", "saved_only", "irrelevant", "empty"])
def test_sdk_app_selection_and_exact_single_writer_reopen(build_case, monkeypatch, tmp_path, accounting, mode):
    case, reads, decisions, writer, harness = run_case(build_case, monkeypatch, tmp_path, accounting, mode)
    response = execute(case, tmp_path, harness)
    assert len(writer.calls) == 1
    service = AgentConversationService()
    pointer = service.get_world_pointer("elderwyld")
    turn, = service.list_turns("elderwyld", pointer.active_conversation_id)
    execution = turn.graph_context_execution
    settled, = [event for event in execution.events if isinstance(event, ledger.BuildWriterEvidenceSelectionV1)]
    selection_wires = [json.loads(request.content) for request in decisions.calls
                       if json.loads(request.content)["state"].get("writer_selection_policy")]
    assert len(selection_wires) == (0 if mode == "empty" else 1)
    assert settled.mode == ("empty_catalog" if mode == "empty" else "jev")
    if selection_wires:
        wire = selection_wires[0]
        assert wire["state"]["user_question"] == turn.user_text
        assert selection.digest(wire["state"]["sources"]) == settled.catalog_sha256
        captures = service.list_context_trace_attempts(world_id="elderwyld", turn_id=turn.turn_id)
        item_id = f"unvalidated-controller-decision:{settled.controller_attempt_id}:{turn.graph_context_receipt.context_receipt_sha256}"
        material, = [m for capture in captures for observation in capture.observations
                     if observation.kind == "context_snapshot" for m in observation.materials
                     if m.item_id == item_id]
        import hashlib
        assert hashlib.sha256(material.text.encode()).hexdigest() == settled.controller_response_sha256
    packet = json.loads(json.loads(writer.calls[0].content)["input"])
    assert sorted(section["read_id"] for section in packet["exposure"]["saved_sections"]) == sorted(str(x) for x in settled.section_read_ids)
    writer_auth, = [event for event in execution.events if isinstance(event, ledger.ProviderAttemptAuthorizedEventV3)
                    and event.provider == "openai"]
    assert set(writer_auth.included_source_read_event_ids) == set(settled.source_event_ids)
    if mode in {"irrelevant", "empty"}:
        assert not settled.expanded_unit_ids and not getattr(turn.completion, "source_citations", ())
        assert packet["retrieval_disposition"]["status"] == "insufficient_evidence"
    else:
        assert mode == "saved_only" or turn.completion.source_citations
    if mode == "saved_only":
        assert reads == {"graph": 0, "source": 0}
        assert packet["exposure"]["saved_sections"] and not packet["opened_passages"]
        bindings = [event for event in execution.events if isinstance(event, ledger.BuildSectionAnswerBindingV1)]
        assert bindings and bindings[0].bindings
    raw = execution.model_dump(mode="json", by_alias=True)
    before_writer = raw["events"][:writer_auth.sequence]
    # Reconstructing a changed execution must not permit another controller or
    # a second selection between the settled manifest and writer authorization.
    duplicate = deepcopy(settled.model_dump(mode="json"))
    duplicate.update(event_id=str(uuid4()), sequence=len(before_writer))
    with pytest.raises(ValueError, match="unique acknowledged"):
        ledger.PlanWorldGraphExecutionV3.model_validate({**raw, "events": [*before_writer, duplicate]})
    controller = deepcopy(next(event for event in reversed(raw["events"])
                               if event.get("kind") == "provider_attempt_authorized_v3"
                               and event.get("provider") == "typesafe"))
    controller.update(event_id=str(uuid4()), provider_attempt_id=str(uuid4()), sequence=len(before_writer))
    with pytest.raises(ValueError, match="controller cannot resume after writer evidence selection"):
        ledger.PlanWorldGraphExecutionV3.model_validate({**raw, "events": [*before_writer, controller]})
    count = len(decisions.calls)
    reopened = AgentConversationService().list_turns("elderwyld", pointer.active_conversation_id)[0]
    assert reopened.completion == turn.completion
    replay = execute(case, tmp_path, None)
    assert replay.answer.text == response.answer.text
    assert len(decisions.calls) == count and len(writer.calls) == 1


@pytest.mark.parametrize("mutation", ["request", "response", "closure", "judgments", "capture"])
def test_app_refuses_forged_selection_before_writer(build_case, monkeypatch, tmp_path, accounting, mutation):
    case, _, _, writer, harness = run_case(build_case, monkeypatch, tmp_path, accounting)
    original = AgentConversationService.record_build_writer_evidence_selection
    if mutation == "capture":
        from apps.live_control_server.services.agent_context_trace_collector import ContextTraceCollector
        monkeypatch.setattr(ContextTraceCollector, "controller_decision_response", lambda *a, **kw: None)

    def forged(self, *args, **kwargs):
        proof = deepcopy(kwargs.get("producer_proof"))
        event = kwargs["selection"]
        if mutation in {"request", "response"}:
            proof[mutation + "_json"] = "{}"
        elif mutation == "closure":
            kwargs["selection"] = event.model_copy(update={"source_event_ids": []})
        elif mutation == "judgments":
            kwargs["selection"] = event.model_copy(update={"judgments": {}})
        kwargs["producer_proof"] = proof
        return original(self, *args, **kwargs)

    monkeypatch.setattr(AgentConversationService, "record_build_writer_evidence_selection", forged)
    with pytest.raises(Exception):
        execute(case, tmp_path, harness)
    assert not writer.calls


@pytest.mark.parametrize("mode", ["unknown_attempt", "incomplete"])
def test_uncertain_or_incomplete_selection_never_replays_or_writes(build_case, monkeypatch, tmp_path, accounting, mode):
    case, _, decisions, writer, harness = run_case(build_case, monkeypatch, tmp_path, accounting, mode)
    with pytest.raises(Exception):
        execute(case, tmp_path, harness)
    assert not writer.calls
    assert sum(bool(json.loads(request.content)["state"].get("writer_selection_policy")) for request in decisions.calls) == 1


def test_catalog_requires_exact_captured_receipts_and_keeps_whole_shared_event():
    import hashlib
    event_id, call_id = uuid4(), uuid4()
    receipts, captures = [], []
    for index, text in enumerate(("The gate is closed after dusk.", "Town seals allow guarded entry.")):
        receipt = ledger.SourceReadAnchorReceiptV2(
            source_read_id=f"read-{index}", anchor_id=f"anchor-{index}", evidence_ref_id=f"evidence-{index}",
            source_artifact_id="artifact", source_revision_id="r1", outcome="enough",
            content_sha256=hashlib.sha256(text.encode()).hexdigest(), line_start=index + 1,
            line_end=index + 1, returned_chars=len(text), truncated=False,
            evidence_sufficiency_status="sufficient")
        receipts.append(receipt)
        captures.append({"kind": "source_passage", "source_read_event_id": str(event_id),
                         **receipt.model_dump(mode="json"), "text": text})
    execution = type("Execution", (), {"events": [ledger.ValidatedSourceReadEventV2(
        event_id=event_id, sequence=0, kind="validated_source_read_v2", read_call_id=call_id, receipts=receipts)]})()
    trace = {"capture_status": "recording", "observations": captures}
    catalog = selection.acquired_catalog(execution, trace)
    assert len(catalog) == 2
    a, b = catalog
    closure = selection.close_selection(catalog, {a: "direct_support", b: "irrelevant"})
    assert closure["expanded_unit_ids"] == [a, b] and closure["source_event_ids"] == [str(event_id)]
    changed = deepcopy(trace)
    changed["observations"][0]["text"] = "An unrelated current document."
    with pytest.raises(ValueError, match="differs"):
        selection.acquired_catalog(execution, changed)
    with pytest.raises(ValueError, match="exact captured"):
        selection.acquired_catalog(execution, {"capture_status": "recording", "observations": captures[:1]})
    with pytest.raises(ValueError, match="complete protected"):
        selection.acquired_catalog(execution, {**trace, "capture_status": "incomplete"})


def test_accounted_authoring_keeps_its_separate_path(build_case, monkeypatch, tmp_path, accounting):
    from application_state.build_proposal.service import BuildProposalService
    case, reads = ordinary_case(build_case, monkeypatch, authoring=True)
    decisions = DecisionWire(operation="propose_build_insertion")
    writer = WriterWire()
    response = execute(case, tmp_path, BuildJevHarness(
        decision_transport=decisions, writer_transport=writer, accounting=accounting))
    assert isinstance(response.knowledge_context.completion, ledger.BuildAuthoringCompletionV1)
    assert len(decisions.calls) == len(writer.calls) == 1
    assert reads == {"graph": 0, "source": 0}
    action = BuildProposalService().get("elderwyld", response.knowledge_context.completion.action_id)
    assert action.state == "proposed" and not action.inserted_in_draft
    service = AgentConversationService()
    turn, = service.list_turns("elderwyld", service.get_world_pointer("elderwyld").active_conversation_id)
    assert isinstance(turn.graph_context_execution.policy, ledger.BuildSelectedSourceActionControllerWriterPolicyV1)
    assert not any(isinstance(event, ledger.BuildWriterEvidenceSelectionV1) for event in turn.graph_context_execution.events)
