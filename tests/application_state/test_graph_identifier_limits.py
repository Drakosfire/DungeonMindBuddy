"""Exact native-shaped identities through the bounded consumer representation."""
import hashlib

import pytest
from pydantic import ValidationError

from application_state.agent_conversation.identifier_limits import (
    GRAPH_CLAIM_ID_MAX_CHARS, GRAPH_EVIDENCE_REF_ID_MAX_CHARS,
)
from application_state.agent_conversation import types as t
from application_state.agent_conversation.context_trace import TraceSourcePassage
from apps.live_control_server.models.agent_turn import AgentEvidenceAnchorOpenTargetV1
from uuid import uuid4


def evidence_id(length):
    prefix = 'evidence:a:s:'
    return prefix + 'r' * (length - len(prefix))


def representations(reference):
    pin = dict(anchor_id='anchor-one', evidence_ref_id=reference,
        source_artifact_id='artifact-one', source_revision_id='source-revision-one')
    text = 'A goat carries goods across the lake.'
    receipt = dict(**pin, source_read_id='read-one', outcome='enough',
        content_sha256=hashlib.sha256(text.encode()).hexdigest(), line_start=1, line_end=1,
        returned_chars=len(text), truncated=False, evidence_sufficiency_status='sufficient')
    passage = {k:v for k,v in receipt.items() if k not in {'evidence_sufficiency_status', 'truncated'}} | dict(
        sequence=0, elapsed_ms=1, source_read_event_id=uuid4(), read_call_id=uuid4(),
        world_id='managed-world', graph_revision='graph-rev-one', text=text)
    target = dict(**pin, claim_id='graph-claim', managed_world_id='managed-world',
        native_world_id='native-world', binding_version=1, graph_revision='graph-rev-one')
    return [(t.GraphSourceScopeAnchorV2,pin),(t.SourceReadAnchorReceiptV2,receipt),
            (TraceSourcePassage,passage),(AgentEvidenceAnchorOpenTargetV1,target)]


@pytest.mark.parametrize('length', [30, 268, GRAPH_EVIDENCE_REF_ID_MAX_CHARS])
def test_exact_evidence_ids_survive_all_source_representations(length):
    reference = evidence_id(length)
    for model, payload in representations(reference):
        value = model.model_validate(payload)
        reopened = model.model_validate_json(value.model_dump_json(by_alias=True))
        assert reopened.evidence_ref_id == reference


def test_evidence_id_over_consumer_envelope_is_rejected_everywhere():
    for model, payload in representations(evidence_id(GRAPH_EVIDENCE_REF_ID_MAX_CHARS + 1)):
        with pytest.raises(ValidationError) as error:
            model.model_validate(payload)
        assert any(e['loc'] == ('evidence_ref_id',) and e['type'] == 'string_too_long' for e in error.value.errors())


@pytest.mark.parametrize('length', [128, 177, GRAPH_CLAIM_ID_MAX_CHARS])
def test_claim_labels_can_reuse_long_native_assertion_or_relationship_id(length):
    claim_id = 'assertion:' + 'a' * (length-len('assertion:'))
    claim = t.PlanWorldGraphClaimSegmentV1(kind='graph_claim', claim_id=claim_id,
        text='A goat carries goods.', target_kind='relationship', target_id='relationship-one',
        graph_revision='graph-rev-one', evidence_ref_ids=[evidence_id(268)])
    target = representations(evidence_id(268))[-1][1] | {'claim_id':claim_id}
    assert t.PlanWorldGraphClaimSegmentV1.model_validate_json(claim.model_dump_json(by_alias=True)).claim_id == claim_id
    assert AgentEvidenceAnchorOpenTargetV1.model_validate(target).claim_id == claim_id
    with pytest.raises(ValidationError):
        t.PlanWorldGraphClaimSegmentV1.model_validate(claim.model_dump(mode='json') | {'claim_id':'a'*(GRAPH_CLAIM_ID_MAX_CHARS+1)})


def test_wider_ids_do_not_change_scope_count_limit():
    anchors=[dict(anchor_id=f'anchor-{i}', evidence_ref_id=evidence_id(268),
        source_artifact_id='artifact-one', source_revision_id='source-revision-one') for i in range(513)]
    with pytest.raises(ValidationError) as error:
        t.GraphSourceReadScopeV2(retrieval_session_id='retrieval-one', initial_claim_packet_sha256='a'*64,
            world_id='world-one', campaign_id=None, graph_revision='graph-rev-one', admitted_anchors=anchors)
    assert any(e['loc'] == ('admitted_anchors',) and e['type'] == 'too_long' for e in error.value.errors())
