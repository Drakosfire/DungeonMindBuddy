"""The final native request must contain the exact admitted target record."""
import json
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import pytest

from application_state.agent_conversation.native_graph_input import producing_graph_closures
from application_state.agent_conversation.rules_authority_types import canonical_bytes
from application_state.agent_conversation.types import ValidatedGraphOperationEventV1


def case(*, wire="responses", presentation="full"):
    identity = uuid4()
    rows = [{"assertionId": "a1", "value": "first 🦉", "evidenceRefIds": ["ev1"]},
            {"assertionId": "a2", "value": "second", "evidenceRefIds": ["ev2"]}]
    packet = {"attributes": rows, "sourceAnchors": [
        {"anchorId": "s1", "evidenceRefId": "ev1"},
        {"anchorId": "s2", "evidenceRefId": "ev2"}]}
    event = ValidatedGraphOperationEventV1.model_construct(
        event_id=identity, result_packet_sha256=sha256(canonical_bytes(packet)).hexdigest(),
        graph_revision="revision", assertion_ids=["a1", "a2"],
        relationship_ids=[], evidence_ref_ids=["ev1", "ev2"])
    if presentation == "full":
        payload = {**packet, "claimLedger": [], "retrievalSessionId": "r", "addedClaimIds": []}
    elif presentation == "page":
        payload = {"schema": "dmb_graph_tool_page_v1", "resultId": "one", "records": [
            {"path": ["attributes", 0], "value": rows[0]}]}
    elif presentation == "fragment":
        raw = json.dumps(rows[0], ensure_ascii=False)
        cut = len(raw) // 2
        payload = {"schema": "dmb_graph_tool_page_v1", "resultId": "one", "records": [
            {"path": ["attributes", 0], "requiresReassembly": True,
             "start": start, "end": end, "length": len(raw),
             "sha256": sha256(raw.encode()).hexdigest(), "fragmentEncoding": "json",
             "fragment": raw[start:end]} for start, end in [(0, cut), (cut, len(raw))]]}
    else:
        payload = {"schema": "dmb_graph_evidence_packet_v1", "bundleId": str(identity),
            "records": [{"kind": "attributes", "record": {
                "assertionId": "a1", "value": "first 🦉", "evidence": ["e1"]}}]}
    raw = json.dumps(payload, ensure_ascii=False)
    if wire == "responses":
        body = {"input": [
            {"type": "function_call", "call_id": "c", "name": "expand_graph_retrieval"},
            {"type": "function_call_output", "call_id": "c", "output": raw}]}
    else:
        body = {"messages": [
            {"role": "assistant", "tool_calls": [{"id": "c", "function": {"name": "expand_graph_retrieval"}}]},
            {"role": "tool", "tool_call_id": "c", "content": raw}]}
    turn = SimpleNamespace(graph_context_execution=SimpleNamespace(events=[event]),
        graph_context_receipt=SimpleNamespace(assembled_input=SimpleNamespace(dispatched_packet_sha256=None),
            graph_authority=SimpleNamespace(graph_revision="revision")))
    auth = SimpleNamespace(included_graph_event_ids=[identity], included_assertion_ids=["a1", "a2"],
        included_relationship_ids=[], included_evidence_ref_ids=["ev1", "ev2"])
    proof = SimpleNamespace(graph_packets={identity: json.dumps(packet)}, prepared_request_json=json.dumps(body))
    return turn, auth, proof, body, payload


@pytest.mark.parametrize("wire", ["responses", "chat"])
@pytest.mark.parametrize("presentation", ["full", "page", "fragment", "bundle"])
def test_native_target_evidence_comes_from_actual_complete_record(wire, presentation):
    turn, auth, proof, _, _ = case(wire=wire, presentation=presentation)
    result = producing_graph_closures(turn, auth, proof)
    assert ("assertion", "a1", ("ev1",)) in result
    assert ("assertion", "a1", ("ev1", "ev2")) not in result
    assert (("assertion", "a2", ("ev2",)) in result) == (presentation == "full")


@pytest.mark.parametrize("mutation", ["packet", "withheld", "quoted", "changed_record", "partial", "oversized"])
def test_native_graph_proof_rejects_or_withholds_unproved_evidence(mutation):
    turn, auth, proof, body, payload = case(presentation="page")
    if mutation == "packet":
        identity = next(iter(proof.graph_packets))
        proof.graph_packets[identity] = proof.graph_packets[identity].replace("first", "forged")
    elif mutation == "withheld":
        auth.included_graph_event_ids = []
    elif mutation == "quoted":
        body = {"input": [{"role": "user", "content": json.dumps(payload)}]}
    elif mutation == "changed_record":
        payload["records"][0]["value"]["evidenceRefIds"] = ["ev2"]
        body["input"][1]["output"] = json.dumps(payload)
    elif mutation == "partial":
        turn, auth, proof, body, payload = case(presentation="fragment")
        payload["records"].pop()
        body["input"][1]["output"] = json.dumps(payload)
    else:
        proof.graph_packets[next(iter(proof.graph_packets))] = "x" * 1050001
    proof.prepared_request_json = json.dumps(body)
    if mutation in {"packet", "withheld", "oversized"}:
        with pytest.raises(ValueError):
            producing_graph_closures(turn, auth, proof)
    else:
        assert producing_graph_closures(turn, auth, proof) == ()


@pytest.mark.parametrize("conflict", [False, True])
def test_repeated_fragment_pages_reuse_exact_content_and_reject_conflicts(conflict):
    turn, auth, proof, body, payload = case(presentation="fragment")
    repeated = json.loads(json.dumps(payload))
    if conflict:
        repeated["records"][0]["fragment"] = "changed"
    body["input"].extend([
        {"type": "function_call", "call_id": "repeat", "name": "expand_graph_retrieval"},
        {"type": "function_call_output", "call_id": "repeat", "output": json.dumps(repeated)}])
    proof.prepared_request_json = json.dumps(body)
    if conflict:
        with pytest.raises(ValueError, match="conflicting fragments"):
            producing_graph_closures(turn, auth, proof)
    else:
        assert producing_graph_closures(turn, auth, proof) == (("assertion", "a1", ("ev1",)),)


@pytest.mark.parametrize("mutation", [None, "receipt", "scope", "quoted"])
def test_initial_target_requires_exact_frozen_system_packet(mutation):
    turn, auth, proof, body, _ = case()
    packet = {"claimLedger": [{"claim_id": "initial", "revision_id": "revision",
                               "evidence_ref_ids": ["ev1"]}]}
    turn.graph_context_receipt.assembled_input = SimpleNamespace(
        dispatched_packet_sha256=sha256(canonical_bytes(packet)).hexdigest(),
        dispatched_assertion_ids=["initial"], dispatched_relationship_ids=[],
        dispatched_evidence_ref_ids=["ev1"])
    auth.included_assertion_ids.append("initial")
    content = "Turn capability policy (runtime-enforced; also required on tool calls):\n" + json.dumps({"initialClaimPacket": packet})
    body["input"].insert(0, {"role": "system", "content": content})
    if mutation == "receipt":
        turn.graph_context_receipt.assembled_input.dispatched_packet_sha256 = "0" * 64
    elif mutation == "scope":
        auth.included_assertion_ids.remove("initial")
    elif mutation == "quoted":
        body["input"][0]["role"] = "user"
    proof.prepared_request_json = json.dumps(body)
    if mutation == "receipt":
        with pytest.raises(ValueError, match="frozen receipt"):
            producing_graph_closures(turn, auth, proof)
    else:
        result = producing_graph_closures(turn, auth, proof)
        assert (("assertion", "initial", ("ev1",)) in result) == (mutation is None)


def test_actual_compact_neighborhood_delivery_supplies_exact_native_target_closure():
    from apps.live_control_server.services.graph_tool_presentation import GraphToolPresentation
    from tests.test_graph_tool_presentation import compact_neighborhood_case, TOOL, SCOPE
    graph,args=compact_neighborhood_case();identity=uuid4();raw=json.dumps(graph)
    packet=GraphToolPresentation(SCOPE).present(TOOL,args,raw,identity)
    evidence=graph['sourceAnchors'][0]['evidenceRefId'];target=graph['relationships'][0]['edgeId']
    event=ValidatedGraphOperationEventV1.model_construct(event_id=identity,
        result_packet_sha256=sha256(canonical_bytes(graph)).hexdigest(),graph_revision=SCOPE.revision_id,
        assertion_ids=[],relationship_ids=[target],evidence_ref_ids=[evidence])
    turn=SimpleNamespace(graph_context_execution=SimpleNamespace(events=[event]),
        graph_context_receipt=SimpleNamespace(assembled_input=SimpleNamespace(dispatched_packet_sha256=None),
            graph_authority=SimpleNamespace(graph_revision=SCOPE.revision_id)))
    auth=SimpleNamespace(included_graph_event_ids=[identity],included_assertion_ids=[],included_relationship_ids=[target],included_evidence_ref_ids=[evidence])
    body={'input':[{'type':'function_call','call_id':'c','name':TOOL},
        {'type':'function_call_output','call_id':'c','output':packet}]}
    proof=SimpleNamespace(graph_packets={identity:raw},prepared_request_json=json.dumps(body))
    assert producing_graph_closures(turn,auth,proof)==(('relationship',target,(evidence,)),)
    body['input'][1]['output']=json.dumps({**json.loads(packet),'records':[]});proof.prepared_request_json=json.dumps(body)
    assert producing_graph_closures(turn,auth,proof)==()
