"""Navigation adopts real Core catalogs; ordinary Plan tests cover APP/SDK authority."""
from types import SimpleNamespace
from uuid import uuid4

import pytest

from application_state.agent_conversation import native_corpus as bodies
from apps.live_control_server.services.corpus_source_navigation import NativeBodyNavigation
from tests.test_native_corpus_source_access import lane as lane, admit, capture

BODY = "# Opening\nA source-local opening.\n# Episode\nThe selected source-local episode. 🌿\n"


def navigation(lane, *, full=False, human=True, search=True, failure=False, pending=False, two_sources=False):
    admit(lane, 'first', body=BODY)
    if two_sources:
        admit(lane, 'second', body=BODY)
    snapshot = capture(lane)
    catalogs = tuple(bodies.build_native_body_catalog(snapshot.authority, member, BODY)
        for member in snapshot.members)
    catalog = catalogs[0]
    excerpt = (bodies.select_native_full_document(catalog, BODY) if full else
        bodies.select_native_body_excerpt(catalog, BODY, catalog.sections[1].section_id))
    events = []
    if human:
        events.append(bodies.NativeAuthoredSourceReadV1(event_id=uuid4(), sequence=0,
            capture_event_id=uuid4(), reference_index=0, catalog=catalog, excerpt=excerpt))
    if search:
        grant = bodies.NativeBodySearchAuthorizedV1(event_id=uuid4(), sequence=len(events),
            provider_attempt_id=uuid4(), context_receipt_sha256='a'*64,
            execution_policy_sha256='b'*64, authority=snapshot.authority, query_sha256='c'*64)
        events.extend((grant, bodies.NativeBodySearchObservedV1(event_id=uuid4(), sequence=len(events)+1,
            authorization_event_id=grant.event_id, catalogs=catalogs,
            matches=tuple(bodies.NativeBodySectionMatchV1(catalog_sha256=c.catalog_sha256,
                section_id=s.section_id, matched_terms=('source',)) for c in catalogs for s in c.sections),
            unavailable_source_count=0)))
        if not human:
            auth = bodies.NativeBodyReadAuthorizedV1(event_id=uuid4(), sequence=len(events),
                provider_attempt_id=grant.provider_attempt_id, search_event_id=events[-1].event_id,
                catalog_sha256=catalog.catalog_sha256,
                retrieval_kind='full_document' if full else 'section',
                section_id=None if full else excerpt.section.section_id)
            events.append(auth)
            if not pending:
                events.append(bodies.NativeBodyReadObservedV1(event_id=uuid4(), sequence=len(events),
                    authorization_event_id=auth.event_id, excerpt=None if failure else excerpt,
                    failure_code='native_body_unavailable' if failure else None))
    turn = SimpleNamespace(user_text='What does the selected episode establish?',
        graph_context_receipt=SimpleNamespace(source_authority=snapshot.authority),
        graph_context_execution=SimpleNamespace(events=events))
    nav = object.__new__(NativeBodyNavigation)
    nav.adapter = SimpleNamespace(fence=SimpleNamespace(turn=turn))
    return nav, catalog, catalogs


@pytest.mark.parametrize('human', [False, True])
def test_successful_section_is_examined_and_not_offered_again_but_other_context_remains(lane, human):
    nav, catalog, _ = navigation(lane, human=human)
    offered = {row.handle for row in nav.offered()}
    assert bodies.native_body_handle(catalog.catalog_sha256, catalog.sections[1].section_id) not in offered
    assert bodies.native_body_handle(catalog.catalog_sha256, catalog.sections[0].section_id) in offered
    assert bodies.native_full_document_handle(catalog.catalog_sha256) in offered
    examined = [row for row in nav.examined() if 'Acquired' in row.kind]
    assert len(examined) == 1 and 'Episode' in examined[0].label and 'lines 3–4' in examined[0].label
    assert ('mandatory writer input' in examined[0].kind) == human
    assert 'selected source-local episode' not in examined[0].label


@pytest.mark.parametrize('human', [False, True])
def test_full_acquisition_covers_its_sections_without_hiding_identical_other_source(lane, human):
    nav, catalog, catalogs = navigation(lane, full=True, human=human, two_sources=True)
    offered = {row.handle for row in nav.offered()}
    assert bodies.native_full_document_handle(catalog.catalog_sha256) not in offered
    assert all(bodies.native_body_handle(catalog.catalog_sha256, s.section_id) not in offered for s in catalog.sections)
    other = next(c for c in catalogs if c.catalog_sha256 != catalog.catalog_sha256)
    assert bodies.native_full_document_handle(other.catalog_sha256) in offered
    assert all(bodies.native_body_handle(other.catalog_sha256, s.section_id) in offered for s in other.sections)


def test_human_passage_is_visible_before_optional_search_without_claiming_global_coverage(lane):
    nav, _, _ = navigation(lane, search=False)
    assert len(nav.offered()) == 1 and nav.offered()[0].kind.startswith('Source lexical navigation')
    examined = nav.examined()
    assert len(examined) == 1 and examined[0].kind.startswith('Acquired user-selected source text')
    assert 'not an answer-sufficiency verdict' in examined[0].kind


@pytest.mark.parametrize('pending', [False, True])
def test_unavailable_and_unresolved_reads_never_become_acquired_navigation(lane, pending):
    nav, _, _ = navigation(lane, human=False, failure=True, pending=pending)
    assert not any('Acquired' in row.kind for row in nav.examined())
    assert any(row.kind == ('Unresolved source read' if pending else 'Unavailable source read') for row in nav.examined())
    if pending:
        with pytest.raises(ValueError, match='unresolved durable grant'):
            nav.offered()


def test_navigation_rehydrates_from_the_existing_retained_event_inventory(lane):
    nav, _, _ = navigation(lane)
    original = nav.offered(), nav.examined()
    turn = nav.adapter.fence.turn
    authority = turn.graph_context_receipt.source_authority
    events = [type(event).model_validate_json(event.model_dump_json())
        for event in turn.graph_context_execution.events]
    recovered = SimpleNamespace(user_text=turn.user_text,
        graph_context_receipt=SimpleNamespace(source_authority=type(authority).model_validate_json(authority.model_dump_json())),
        graph_context_execution=SimpleNamespace(events=events))
    reopened = object.__new__(NativeBodyNavigation)
    reopened.adapter = SimpleNamespace(fence=SimpleNamespace(turn=recovered))
    assert (reopened.offered(), reopened.examined()) == original
