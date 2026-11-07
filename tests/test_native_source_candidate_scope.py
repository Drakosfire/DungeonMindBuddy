"""Scope navigation is reversible and independent of source/fact authority."""
import pytest
from apps.live_control_server.services.native_source_candidate_scope import preferred_source_pairs


def display(campaign='longmont-c1', session='session-8', **changes):
    return dict(kind='recap', status='available', origin_matches_current_metadata=True,
        campaign_id=campaign, session_id=session, label=f'{campaign} {session}', **changes)


@pytest.mark.parametrize('question,expected', [
    ('campaign 1 and C2S20', {'a', 'b'}),
    ('C2S20', {'b'}),
    ('session 20', {'b', 'c'}),
    ('longmont-c2', {'b', 'd'}),
    ('campaign 3', None),
    ('What happened to Edge?', None),
    ('not campaign 1', None),
    ('without session 8', None),
    ('exclude campaign 1', None),
    ('outside C2S20', None),
    ('session 20 except longmont-c2', None),
    ('session 8 and session 9', {'a', 'd'}),
])
def test_explicit_hint_union_and_no_match_remains_broad(question, expected):
    rows = {'a':display(), 'b':display('longmont-c2','session-20'),
        'c':display('other-c4','session-20'), 'd':display('longmont-c2','session-9')}
    assert preferred_source_pairs(question, rows) == (frozenset(expected) if expected else None)


@pytest.mark.parametrize('changes', [
    {'status':'unavailable'}, {'origin_matches_current_metadata':False},
    {'origin_matches_current_metadata':None}, {'campaign_id':'opaque'},
    {'campaign_id':None}, {'session_id':None}, {'session_id':'unknown'},
    {'kind':'worldbuilding'}, {'kind':'other'},
])
def test_unknown_stale_and_other_material_stays_reachable(changes):
    unknown = display('longmont-c2', 'session-9')
    unknown.update(changes)
    assert preferred_source_pairs('C2S20', {'match':display('longmont-c2','session-20'),
        'unknown':unknown}) == frozenset({'match','unknown'})


def test_names_only_add_and_identical_ordinals_do_not_guess_campaign_identity():
    first = display()
    first['label'] = 'Winter recap'
    rows = {'a':first, 'b':display('other-c1','session-8'), 'c':display('longmont-c2','session-20')}
    assert preferred_source_pairs('Winter recap', rows) is None
    assert preferred_source_pairs('C2S20 and Winter recap', rows) == frozenset({'a','c'})
    assert preferred_source_pairs('campaign 1', rows) == frozenset({'a','b'})
