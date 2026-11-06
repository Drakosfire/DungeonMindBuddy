"""Issued native requests remain inspectable before IO; no new evidence path."""
from types import SimpleNamespace

import pytest
from pydantic import TypeAdapter
from application_state.agent_conversation.context_trace import ContextTraceObservation
from apps.live_control_server.services.native_retrieval_activity import observe_native_retrieval
from tests.test_native_plan_assertions import lane as lane  # noqa: F401
from tests.application_state.test_native_plan_statements import native_read_admission_probes as native_read_admission_probes  # noqa: F401


def test_existing_trace_codec_preserves_unavailable_without_claiming_retrieval():
    rows=[]
    adapter=SimpleNamespace(context_capture=SimpleNamespace(observe=rows.append))
    observe_native_retrieval(adapter,'source_section_read','native-body:selected',completed=True,unavailable=True)
    row=TypeAdapter(ContextTraceObservation).validate_python({**rows[0],'sequence':0,'elapsed_ms':1})
    assert row.action=='retained' and row.reason_code=='unavailable'
    assert row.item_ids==['native-body:selected']
    assert row.kind=='context_decision'  # Existing stored-event codec, no new reader contract.
    observe_native_retrieval(SimpleNamespace(),'source_search','native-corpus-search:selected')


def test_ordinary_native_progress_is_durable_before_core_io_and_outside_claim_lock(lane,tmp_path,monkeypatch):
    from apps.live_control_server.services.agent_context_trace_collector import ContextTraceCollector
    from apps.live_control_server.integrations.dungeonmind import native_corpus_source as core
    from tests.test_surface_native_build_ordinary import _fresh_case
    captures=[]; before_io=[]
    original_observe=ContextTraceCollector.observe
    def observe(self,fields):
        if fields.get('policy_version','').endswith('_progress_v1'):
            assert self.fence.renewer._lock.acquire(blocking=False), 'Progress re-entered the claim lock'
            self.fence.renewer._lock.release()
            captures.append(self)
        return original_observe(self,fields)
    monkeypatch.setattr(ContextTraceCollector,'observe',observe)
    def inspect_before_io():
        capture=captures[-1]
        turn=capture.fence.renewer._turn
        rows=capture.fence.service.list_context_trace_attempts(world_id=turn.world_id,turn_id=turn.turn_id)[-1].observations
        progress=[row for row in rows if row.kind=='context_decision' and row.policy_version.endswith('_progress_v1')]
        assert progress[-1].action=='expanded'
        before_io.append((progress[-1].policy_version,progress[-1].item_ids[0]))
    original_search=core.capture_native_sources
    def search(**kwargs):
        inspect_before_io()
        return original_search(**kwargs)
    original_read=core.read_native_corpus_member
    def read(**kwargs):
        inspect_before_io()
        return original_read(**kwargs)
    monkeypatch.setattr(core,'capture_native_sources',search)
    monkeypatch.setattr(core,'read_native_corpus_member',read)
    case=_fresh_case(lane,tmp_path,monkeypatch,None,False,False,False,native_body='direct_support')
    rows=case.service.list_context_trace_attempts(world_id=case.world,turn_id=case.turn.turn_id)[-1].observations
    progress=[r for r in rows if r.kind=='context_decision' and r.policy_version.endswith('_progress_v1')]
    assert {policy for policy, _ in before_io} == {
        'native_source_search_progress_v1', 'native_source_document_read_progress_v1'}
    assert len(progress) == 2 * len(before_io)
    for policy,target in before_io:
        pair=[row for row in progress if row.policy_version==policy and row.item_ids==[target]]
        assert [row.action for row in pair]==['expanded','retrieved']
    assert case.turn.status=='completed' and case.turn.completion.native_body_citations
    # _fresh_case also verifies exact ordinary replay makes no additional provider call,
    # and opens the accepted support through its existing citation owner.


@pytest.mark.parametrize('unavailable', [False, True])
def test_ordinary_graph_read_progress_brackets_native_owner(lane, tmp_path, monkeypatch, unavailable, native_read_admission_probes):
    from apps.live_control_server.services.agent_context_trace_collector import ContextTraceCollector
    from apps.live_control_server.services import native_graph_reads
    from tests.test_native_plan_assertions import _ordinary_native_case
    captures = []
    original_observe = ContextTraceCollector.observe
    def observe(self, fields):
        if fields.get('policy_version') == 'native_assertion_read_progress_v1':
            assert self.fence.renewer._lock.acquire(blocking=False)
            self.fence.renewer._lock.release()
            captures.append(self)
        return original_observe(self, fields)
    monkeypatch.setattr(ContextTraceCollector, 'observe', observe)
    before_io = []
    original_read = native_graph_reads.read_selected
    def read(context, grant, principal):
        capture = captures[-1]
        turn = capture.fence.renewer._turn
        rows = capture.fence.service.list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)[-1].observations
        progress = [r for r in rows if r.kind == 'context_decision' and r.policy_version == 'native_assertion_read_progress_v1']
        assert progress[-1].item_ids == [f'native-assertion-read:{grant.event_id}']
        if before_io:  # The ordinary fixture later reopens the accepted citation.
            assert progress[-1].action == 'retrieved'
        else:
            assert progress[-1].action == 'expanded'
            before_io.append(grant.event_id)
        return original_read(context, grant, principal)
    monkeypatch.setattr(native_graph_reads, 'read_selected', read)
    _ordinary_native_case(lane, tmp_path, monkeypatch, False, unavailable, None, None, False, native_read_admission_probes)
    assert len(before_io) == 1  # The fixture also verifies replay does not dispatch again.
    capture = captures[-1]
    turn = capture.fence.renewer._turn
    rows = capture.fence.service.list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)[-1].observations
    progress = [r for r in rows if r.kind == 'context_decision' and r.policy_version == 'native_assertion_read_progress_v1']
    assert [r.action for r in progress] == ['expanded', 'retained' if unavailable else 'retrieved']
    assert progress[-1].reason_code == ('unavailable' if unavailable else 'question_relevance')
