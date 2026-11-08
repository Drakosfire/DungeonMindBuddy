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
    ('no session 8', None),
    ("don't include session 8", None),
    ('don’t include session 8', None),
    ('session8', {'a'}),
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


def test_session16_shorthand_is_a_positive_navigation_hint():
    assert preferred_source_pairs('What happened in session16?', {
        'a':display(session='session-16'), 'b':display(session='session-17')}) == frozenset({'a'})


@pytest.mark.parametrize('question,expected', [
    ('What does the selected recap establish?', {'selected','unknown'}),
    ('What repairs that central mass after it is burned? Cite the selected recap. Discuss only; do not edit or save.', {'selected','unknown'}),
    ('Compare it with C2S20. Do not save.', {'other','unknown'}),
    ('Outside C2S20. Do not edit or save.', None),
    ('Compare it with C2S20', {'other','unknown'}),
    ('Look outside the selected recap', None),
    ('Do not limit this to the selected recap', None),
    ('What does Winter recap add?', None),
    ('I do not publish.', None),
    ("We don't save.", None),
    ('The source says: do not publish.', None),
    ("What does the selected recap establish? Don't save.", {'selected','unknown'}),
])
def test_opened_reference_hint_preserves_explicit_scope_and_broad_requests(question,expected):
    rows={'selected':display(session='session-16'),
        'other':display('longmont-c2','session-20'),
        'unknown':dict(display(),status='unavailable')}
    rows['other']['label']='Winter recap'
    actual=preferred_source_pairs(question,rows,opened_reference_pairs={('absent','revision'),'selected'})
    assert actual==(None if expected is None else frozenset(expected))


@pytest.mark.parametrize('reference', [set(),{'missing'}, {'unknown'}])
def test_missing_or_unavailable_reference_metadata_does_not_narrow(reference):
    rows={'other':display(), 'unknown':dict(display(),status='unavailable')}
    assert preferred_source_pairs('What happened?',rows,opened_reference_pairs=reference) is None


@pytest.mark.parametrize('question', [
    'before Session 4', 'AFTER session4', 'by Session 4', 'through Session4',
    'until Session 4', 'since Session4', 'as of Session 4',
    '(by the end of Session 4), what was known?',
    'at the start of Session4', 'at the beginning of Session 4',
    'between Session 1 and Session 8', 'from Session 1 to Session 8',
    'Session 1 through Session 8', 'Session 1–8', 'Sessions 1-8',
    'before C2S4', 'C2S1—C2S8', 'by the end of C2 S4',
    'At the end of Session4, what is known from Winter recap?',
])
@pytest.mark.parametrize('opened', [(), ('boundary',)])
def test_temporal_boundaries_and_ranges_do_not_select_only_the_endpoint(question, opened):
    rows = {'earlier': display(session='session-1'),
            'boundary': dict(display(session='session-4'), label='Winter recap'),
            'later': display(session='session-8'),
            'other': display('fixture-c2', 'session-4')}
    assert preferred_source_pairs(question, rows, opened_reference_pairs=opened) is None


@pytest.mark.parametrize('question', [
    'In Session4, end with a concise answer.',
    'From Session4 recap, extract the names.',
    'What happened in Session4 after the fight?',
    'Since we last met, tell me what happened in Session4.',
])
def test_temporal_words_elsewhere_do_not_disable_an_exact_session_hint(question):
    rows = {'exact': display(session='session-4'), 'other': display(session='session-8')}
    assert preferred_source_pairs(question, rows) == frozenset({'exact'})


@pytest.mark.parametrize('question', [
    'Campaign 2, by the end of Session4',
    'Campaign 2 through C2S4',
    'fixture-c2 before C2S4',
])
def test_temporal_hint_retains_independent_compatible_campaign_scope(question):
    rows = {'earlier': display('fixture-c2', 'session-1'),
            'boundary': display('fixture-c2', 'session-4'),
            'later': display('fixture-c2', 'session-8'),
            'other': display('fixture-c1', 'session-4'),
            'unknown': dict(display(), status='unavailable'),
            'stale': dict(display(), origin_matches_current_metadata=False)}
    assert preferred_source_pairs(question, rows, opened_reference_pairs={'boundary'}) == frozenset(
        {'earlier', 'boundary', 'later', 'unknown', 'stale'})


@pytest.mark.parametrize('question', [
    'campaign 1 through C2S4',
    'fixture-c1 by the end of C2S4',
    'campaign 1 by Session4, compared with C2S8',
    'opaque-campaign through C2S4',
])
def test_temporal_hint_cannot_hide_conflicting_or_unreconciled_compact_campaign(question):
    rows = {'one': display('fixture-c1', 'session-1'),
            'two': display('fixture-c2', 'session-4'),
            'opaque': display('opaque-campaign', 'session-4')}
    assert preferred_source_pairs(question, rows, opened_reference_pairs={'one'}) is None
