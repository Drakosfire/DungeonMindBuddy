"""Agent and human navigation adopt one producer display join, not new authority."""
from types import SimpleNamespace

import pytest
from psycopg import OperationalError
from application_state.source import service as sources
from application_state.errors import ApplicationStateError
from apps.live_control_server.services import native_source_inspection as inspector
from apps.live_control_server.services.corpus_source_navigation import NativeBodyNavigation
from apps.live_control_server.models.native_graph_inspection import InspectionScope
from apps.live_control_server.integrations.dungeonmind.native_corpus_source import capture_native_sources
from application_state.agent_conversation.native_corpus import build_native_body_catalog
from tests.test_native_source_inspection import (
    inspection as inspection, source_lane as source_lane, registered, recap_metadata, SCOPE,  # noqa: F401
)
from tests.test_native_corpus_source_access import GM, lane as lane  # noqa: F401
from tests.test_agent_native_corpus_sources import source_adapter as source_adapter  # noqa: F401


def navigation(case):
    context, _ = inspector._pinned(InspectionScope(**SCOPE), GM)
    capture = capture_native_sources(managed_world_id='managed', principal=GM, prepared=context)
    member = capture.members[0]
    body = capture.bodies[(member.artifact.source_artifact_id, member.revision.source_revision_id)]
    catalog = build_native_body_catalog(context.authority, member, body)
    turn = SimpleNamespace(user_text='What happened?', graph_context_receipt=SimpleNamespace(
        source_authority=context.authority), graph_context_execution=SimpleNamespace(events=[]))
    adapter = SimpleNamespace(native_corpus_context=context, fence=SimpleNamespace(turn=turn))
    return NativeBodyNavigation(adapter), catalog


def test_exact_recap_display_join_is_shared_and_cached_only_within_navigation(inspection, monkeypatch):
    registered(inspection)
    calls = []
    def metadata(**kwargs):
        calls.append(kwargs)
        return [recap_metadata()]
    monkeypatch.setattr(sources, 'get_source_revision_metadata', metadata)
    nav, catalog = navigation(inspection)
    assert nav.offered() and not calls  # Historical navigation remains search-first.
    before = catalog.model_dump_json()
    label = nav._source_name(catalog)
    assert label == 'Session 8 recap · campaign: c1 · session: session-8'
    assert nav._source_name(catalog) == label and len(calls) == 1
    assert catalog.model_dump_json() == before
    assert catalog.source.campaign_scope == catalog.source.session_scope == 'unestablished'
    # A label cache cannot relabel a different source revision.
    changed = catalog.model_copy(update={'source':catalog.source.model_copy(update={
        'revision_json': catalog.source.revision_json.replace(catalog.source.revision.source_revision_id, 'other')})})
    assert nav._source_name(changed).endswith('(source name unavailable)')


@pytest.mark.parametrize('changes', [
    {'world_id':'foreign'}, {'source_artifact_id':'foreign'},
    {'source_revision_id':'22222222-2222-4222-8222-222222222222'},
    {'content_sha256':'0'*64},
])
def test_foreign_metadata_neither_names_nor_changes_native_source(inspection, monkeypatch, changes):
    registered(inspection)
    monkeypatch.setattr(sources, 'get_source_revision_metadata', lambda **_: [recap_metadata(**changes)])
    nav, catalog = navigation(inspection)
    before = catalog.model_dump_json()
    assert nav._source_name(catalog).endswith('(source name unavailable)')
    assert catalog.model_dump_json() == before


@pytest.mark.parametrize('error_type', [ApplicationStateError, OperationalError])
def test_display_database_failure_preserves_native_body_and_unavailable_label(inspection, monkeypatch, error_type):
    registered(inspection)
    def unavailable(**_):
        raise error_type('metadata unavailable')
    monkeypatch.setattr(sources, 'get_source_revision_metadata', unavailable)
    nav, catalog = navigation(inspection)
    assert nav._source_name(catalog).endswith('(source name unavailable)')
    assert catalog.body_bytes > 0


def test_newer_page_name_is_marked_as_navigation_not_selected_revision(inspection, monkeypatch):
    from application_state.content import pages
    from tests.test_native_source_inspection import APP_REVISION
    registered(inspection, page=True)
    page = SimpleNamespace(work_object_id=APP_REVISION, world_id='managed', title='Current page name',
                           object_revision=3, campaign_id=None)
    monkeypatch.setattr(pages, 'page_inventory', lambda **_: [SimpleNamespace(page=page)])
    nav, catalog = navigation(inspection)
    assert nav._source_name(catalog) == 'Current page name · current page label; selected source is an older revision'
    assert catalog.source.revision.source_revision_id


@pytest.fixture
def labelled_adapter(request, monkeypatch):
    from tests import test_native_corpus_source_access as fixture_owner
    from tests.test_native_corpus_source_access import BODY
    from hashlib import sha256
    from tests.test_native_source_inspection import APP_REVISION
    original = fixture_owner.publish_native_text_source_evidence
    def publish(**kwargs):
        request = kwargs['request']
        raw = request.model_dump(mode='json')
        raw['origin'] = dict(namespace='dungeonbuddy.app-recap-source.v1', object_id='recap', revision_id=APP_REVISION)
        return original(**(kwargs | {'request':type(request).model_validate(raw)}))
    monkeypatch.setattr(fixture_owner, 'publish_native_text_source_evidence', publish)
    monkeypatch.setattr(sources, 'get_source_revision_metadata', lambda **_: [recap_metadata(
        world_id='world:one', content_sha256=sha256(BODY.encode()).hexdigest())])
    return request.getfixturevalue('source_adapter')


def test_actual_retrieval_wire_uses_joined_names_without_changing_read_identity(labelled_adapter):
    import asyncio
    from tests.test_agent_native_corpus_sources import DecisionWire, SourceChoices
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    from apps.live_control_server.services.agent_turn_service import _submitted_turn_intent
    from application_state.agent_conversation.native_corpus import selected_body_reads
    a = labelled_adapter
    a.request = a.request.model_copy(update={'message':'What did Éphanna hear?'})
    a.submitted_intent = _submitted_turn_intent(a.request, world_id=a.world_id)
    semantic = PlanJevDispatch.requested_work(a, page_title='Synthetic park Plan')
    asyncio.run(semantic.run(transport=DecisionWire(a), api_key='synthetic-not-secret'))
    wire = SourceChoices()
    asyncio.run(PlanJevDriver(a).run(transport=wire, api_key='synthetic-not-secret'))
    documents = [c for call in wire.calls for c in call['state']['candidates']
                 if c['kind']=='Explicit full-document read']
    assert len(documents)==1
    assert documents[0]['label'].startswith('Read full document: Session 8 recap · campaign: c1 · session: session-8')
    reads = selected_body_reads(a.fence.turn.graph_context_execution)
    assert len(reads)==1 and reads[0].excerpt.selector_policy=='native_full_document_v1'
    from application_state.agent_conversation.native_corpus import NativeBodyReadAuthorizedV1
    grants = [e for e in a.fence.turn.graph_context_execution.events if isinstance(e, NativeBodyReadAuthorizedV1)]
    assert len(grants)==1 and grants[0].catalog_sha256==reads[0].excerpt.catalog_sha256


def test_raw_page_database_error_does_not_block_native_navigation_or_human_read(inspection, monkeypatch):
    from application_state.content import pages
    from tests.test_native_source_inspection import PATH, selection
    from tests.test_native_corpus_source_access import BODY
    registered(inspection, page=True)
    def unavailable(**_):
        raise OperationalError('synthetic display query unavailable')
    monkeypatch.setattr(pages, 'page_inventory', unavailable)
    nav, catalog = navigation(inspection)
    assert nav._source_name(catalog).endswith('(source name unavailable)')
    opened = inspection.client.post(PATH+'/read', json=selection(inspection))
    assert opened.status_code==200 and opened.json()['source']['body_text']==BODY


def test_activity_section_label_uses_existing_display_join_and_exact_catalog_extent(inspection,monkeypatch):
    registered(inspection)
    monkeypatch.setattr(sources,'get_source_revision_metadata',lambda **_: [recap_metadata()])
    nav,catalog=navigation(inspection)
    section=catalog.sections[-1]
    before=catalog.model_dump_json()
    assert nav._read_label(catalog,section.section_id)==(
        f'Session 8 recap · campaign: c1 · session: session-8 · {section.label} · lines {section.line_start}–{section.line_end}')
    assert nav._read_label(catalog)=='Session 8 recap · campaign: c1 · session: session-8'
    assert catalog.model_dump_json()==before
