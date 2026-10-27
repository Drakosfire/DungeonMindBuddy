"""Actual provider-free writer admission, history and host page-reference projection."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from urllib.parse import urlparse, parse_qs
from uuid import uuid4

import pytest
from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.agent_conversation.plan_authoring import authored_markdown
from application_state.agent_conversation.rules_authority_policy import rules_capability
from application_state.agent_conversation.rules_authority_types import canonical_sha256
from application_state.agent_conversation.surface_evidence_answer import PLAN_POLICY
from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
from tests.test_plan_jev_dispatch import plan_adapter  # noqa: F401
from tests.test_plan_jev_driver import Decisions
from tests.test_plan_jev_writer import WriterWire


def stage_summary(a, *, authoring=False, rules_used=False):
    packet = dict(schema_version="dmb_session_evidence_v1", title="Synthetic gate rehearsal",
        world_id=a.world_id, run_id=str(uuid4()), review_revision=4,
        checkpoint_run_revision=8, session_content_sha256="c"*64,
        sources=[dict(kind="scene_note",element_id="scene:gate",
                      text="Technical rehearsal: the gate stayed closed. No fight occurred. 🐸\r\n"),
                 dict(kind="closing_reflections",text="The next route remains undecided; ask before initiative.")])
    for source in packet["sources"]: source["sha256"]=sha256(source["text"].encode()).hexdigest()
    packet["sha256"]=canonical_sha256(packet)
    a.work=replace(a.work,session_evidence={"sessions":[packet]})
    if authoring:
        from tests.test_plan_jev_authoring import authoring_writer
        writer,_,_=authoring_writer(a,rules_used=rules_used,placement="end")
    else:
        rules=PlanRulesRuntime(a,rules_capability(graph=True))
        proof=asyncio.run(PlanJevDriver(a).run(transport=Decisions(),api_key="synthetic"))
        writer=PlanJevWriter(a,proof,rules)
    ids=[entry["text_blocks"][0]["selection_id"] for entry in writer.projection.frame["session_evidence"][0]["sources"]]
    payload=dict(schema=PLAN_POLICY,limitations=[],requested_detail_gaps=[],answer_segments=[
        dict(kind="session_summary",text="The saved rehearsal kept the gate closed without a fight; the next route is still open.",selection_ids=ids),
        dict(kind="proposal",text="We could ask the players which route they prefer before initiative.",label="invented_idea")])
    return writer, packet, payload


def test_summary_preserves_exact_two_entry_support_history_and_page_links(plan_adapter):
    writer,packet,payload=stage_summary(plan_adapter)
    result=asyncio.run(writer.run(transport=WriterWire(plan_adapter,json.dumps(payload)),api_key="synthetic"))
    assert isinstance(result.completion,t.SurfaceEvidenceCompletionV4)
    summary=result.completion.answer_segments[0]
    assert isinstance(summary,t.SessionSummaryV1)
    assert summary.text not in " ".join(source["text"] for source in packet["sources"])
    assert [s.text for s in summary.supports]==[s["text"] for s in packet["sources"]]
    assert [s.source_ordinal for s in summary.supports]==[0,1]
    assert all(s.owner_sha256==packet["sha256"] and s.checkpoint_content_sha256=="c"*64 for s in summary.supports)
    assert summary.supports[0].body_sha256!=summary.supports[1].body_sha256
    reopened=AgentConversationService().inspect_turn(world_id=result.world_id,turn_id=result.turn_id)
    assert reopened.completion==result.completion
    history=AgentConversationService().list_completed_plan_ask_context(result.world_id,result.graph_context_receipt.plan_basis)
    assert isinstance(history[-1].history_attribution,t.PlanEvidenceHistoryAttributionV4)
    assert history[-1].history_attribution.answer_segments==result.completion.answer_segments
    fragment=authored_markdown(result)
    from application_state.agent_conversation.session_summary_projection import citation_target
    for support in summary.supports:
        target=citation_target(result.world_id,support)
        assert target in fragment
        parsed=urlparse(target)
        assert parse_qs(parsed.query)=={"world":[result.world_id],"run":[packet["run_id"]],"evidence_revision":["4"]}
        assert support.entry_identity in parsed.fragment and support.body_sha256 in parsed.fragment
        assert support.owner_sha256 in parsed.fragment and support.checkpoint_content_sha256 in parsed.fragment
    assert ' · Scene notes"' in fragment and ' · Closing reflections"' in fragment
    assert packet["sources"][0]["text"] not in fragment  # No forced repeated literal excerpt.
    t.validate_session_evidence_claims(result.completion.answer_segments,result.provenance)
    forged=deepcopy(result.completion.answer_segments)
    forged[0].supports[0]=forged[0].supports[0].model_copy(update={"owner_sha256":"f"*64})
    with pytest.raises(ValueError,match="frozen turn provenance"):
        t.validate_session_evidence_claims(forged,result.provenance)


@pytest.mark.parametrize("bad",["unknown","plan","duplicate","metadata"])
def test_summary_refuses_non_session_unexposed_or_model_authored_support(plan_adapter,bad):
    writer,packet,payload=stage_summary(plan_adapter)
    row=payload["answer_segments"][0]
    if bad=="unknown": row["selection_ids"]=["not-exposed"]
    elif bad=="plan": row["selection_ids"]=[writer.projection.frame["committed_plan_blocks"][0]["selection_id"]]
    elif bad=="duplicate": row["selection_ids"]*=2
    else: row["citation_url"]="/play?run=forged"
    with pytest.raises(Exception):
        asyncio.run(writer.run(transport=WriterWire(plan_adapter,json.dumps(payload)),api_key="synthetic"))
    result=AgentConversationService().inspect_turn(world_id=plan_adapter.world_id,turn_id=plan_adapter.turn.turn_id)
    assert result.status!="completed" and result.completion is None


@pytest.mark.parametrize("rules_used",[False,True])
def test_cited_summary_survives_actual_proposal_review_edit_save_and_reload(plan_adapter,rules_used):
    from tests.application_state.test_plan_authoring_review import opened,execute,command,prepare
    from application_state.content.service import current_committed_revision
    writer,packet,payload=stage_summary(plan_adapter,authoring=True,rules_used=rules_used)
    if rules_used:
        support=writer.rules.frame().supports[0]
        payload=dict(schema="dmb_rules_mixed_answer_v1",base_output=payload,
            rules_segments=[dict(kind="rules_claim",text=support.excerpt_text,support_ids=[str(support.support_id)])],
            ordered_refs=[dict(domain="base",segment_index=None),dict(domain="rules",segment_index=0)])
    asyncio.run(writer.run(transport=WriterWire(plan_adapter,json.dumps(payload)),api_key="synthetic"))
    action,capture=writer.rules.authoring
    proposal=plan_adapter.service.get_plan_authoring_proposal(capture.world_id,action.action_id)
    original=proposal.replacement_markdown
    assert '#source-0-' in original and '#source-1-' in original
    review=opened(proposal)
    edited=original+"\n\nAuthor reminder: ask before initiative."
    review=execute(proposal,command(proposal,review,"save",markdown=edited))
    pending=prepare(proposal,review)
    application=pending.applications[-1]
    confirm=command(proposal,pending,"confirm",application_id=application.application_id)
    saved=execute(proposal,confirm)
    assert saved.state=="applied" and execute(proposal,confirm)==saved
    current=current_committed_revision(capture.document_id,kind="plan")
    assert edited in current.work_revision.markdown
    assert current.work_revision.markdown.startswith(capture.draft_markdown)
    assert plan_adapter.service.get_plan_authoring_proposal(capture.world_id,action.action_id).replacement_markdown==original
