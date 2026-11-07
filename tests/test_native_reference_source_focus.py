"""Real ordinary Build references retain an explicit route to broader sources."""
from hashlib import sha256

import pytest

from tests.test_native_plan_assertions import lane as lane  # noqa: F401
from tests.test_surface_native_build_ordinary import _fresh_case
from apps.live_control_server.services.corpus_source_navigation import NativeBodyNavigation
from application_state.agent_conversation.native_corpus import (
    NativeAuthoredSourceReadV1, NativeBodySearchObservedV1,
)


@pytest.mark.parametrize('selection', ['section', 'full_document'])
@pytest.mark.parametrize('broaden', [False, True])
def test_ordinary_opened_reference_focus_preserves_search_and_writer_support(lane,tmp_path,monkeypatch,selection,broaden):
    from apps.live_control_server.services import native_source_display, native_source_candidate_scope
    real_hint=native_source_candidate_scope.preferred_source_pairs
    hints=[]
    def hint(question,displays,*,opened_reference_pairs=()):
        hints.append(frozenset(opened_reference_pairs))
        return real_hint(question,displays,opened_reference_pairs=opened_reference_pairs)
    monkeypatch.setattr(native_source_candidate_scope,'preferred_source_pairs',hint)
    # Producer display is metadata only; native membership, reads, receipts and
    # writer/citation acceptance still use the actual synthetic Core and APP.
    def display(items,world_id):
        return [dict(label=f'Source {index}',kind='recap',campaign_id='fixture-c1',
            session_id=f'session-{index}',status='available',metadata_revision='fixture',
            origin_matches_current_metadata=True) for index,_ in enumerate(items)]
    monkeypatch.setattr(native_source_display,'source_display_metadata',display)
    focused=[]
    def before_provider(adapter,provider):
        turn=adapter.fence.turn
        events=turn.graph_context_execution.events
        human=[e for e in events if isinstance(e,NativeAuthoredSourceReadV1)]
        if provider!='typesafe' or not human or any(isinstance(e,NativeBodySearchObservedV1) for e in events):
            return
        nav=NativeBodyNavigation(adapter)
        offers=nav.offered()
        selected={(e.catalog.source.artifact.source_artifact_id,e.catalog.source.revision.source_revision_id) for e in human}
        offered_pairs={nav._direct_sources[c.handle][0] for c in offers if c.handle in nav._direct_sources}
        assert offered_pairs<=selected
        assert any(pair not in selected for pair,_,_ in nav._source_choices().values())
        assert any(c.kind.startswith('Source lexical navigation') for c in offers)
        assert any(c.handle==nav.expansion_handle() for c in offers)
        focused.append(selected)
    case=_fresh_case(lane,tmp_path,monkeypatch,None,False,False,False,
        authored_source=selection,before_provider=before_provider,
        native_body='direct_support' if broaden else None,direct_source='mixed' if broaden else False)
    assert focused and any(hints)
    assert bool(any(isinstance(e,NativeBodySearchObservedV1) for e in case.turn.graph_context_execution.events))==broaden
    if broaden:
        assert frozenset() in hints  # An actual scan drops the initial reference hint.
    assert case.turn.completion.native_body_citations
    for index,citation in enumerate(case.turn.completion.native_body_citations):
        response=case.client.get(f'/api/live/agent/worlds/{case.world}/conversation/turns/{case.turn.turn_id}/native-body-excerpts/{index}')
        assert response.status_code==200,response.text
        opened=response.json()
        assert opened['citation']==citation.model_dump(mode='json',by_alias=True)
        assert sha256(opened['content'].encode()).hexdigest()==citation.excerpt_sha256
