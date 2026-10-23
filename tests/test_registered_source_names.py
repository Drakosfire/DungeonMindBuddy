"""Source names are presentation from resolved provenance, not opaque IDs."""
from types import SimpleNamespace

import pytest

from apps.live_control_server.integrations.dungeonmind.world_graph_reads import _registered_source_name


@pytest.mark.parametrize('domain', ['session_recap', 'recap'])
def test_registered_session_names_ignore_artifact_and_normalized_filename(domain):
    artifact = SimpleNamespace(source_domain_key=domain, session_id='session-29',
        source_artifact_id='artifact:recap:v2:opaque-hash', uri='repo://seals/hash/normalized_source.md')
    assert _registered_source_name(artifact) == 'Session 29 recap'


@pytest.mark.parametrize('domain,session', [('worldbuilding','session-29'), ('recap',None),
    ('recap','not-a-session'), ('recap','session-0')])
def test_unknown_name_cannot_be_inferred_from_ids_or_uris(domain, session):
    artifact = SimpleNamespace(source_domain_key=domain, session_id=session,
        source_artifact_id='artifact:recap:session-29', uri='repo://Session 29 Recap.md')
    assert _registered_source_name(artifact) is None


@pytest.mark.parametrize('domain', ['session_recap', 'recap'])
@pytest.mark.parametrize('lineage', [{}, {'source_name': ''}, {'source_name': None}])
def test_native_proof_and_graph_passage_share_registered_recap_name(domain, lineage):
    from application_state.source.naming import registered_source_name
    artifact = dict(source_domain_key=domain, session_id='session-29', lineage=lineage)
    assert registered_source_name(artifact) == _registered_source_name(SimpleNamespace(**artifact)) == 'Session 29 recap'


@pytest.mark.parametrize('name', ['Of Conks & Cons', '  Authored source title  '])
def test_explicit_registered_name_precedes_session_presentation(name):
    from application_state.source.naming import registered_source_name
    artifact = dict(source_domain='session_recap', session_id='session-29', lineage={'source_name': name})
    assert registered_source_name(artifact) == name.strip()


@pytest.mark.parametrize('session', ['session-029', 'session--1', 'session-1/../../', 'session-1\n', 29, None])
def test_shared_policy_rejects_noncanonical_session_metadata(session):
    from application_state.source.naming import registered_source_name
    assert registered_source_name({'source_domain':'session_recap','session_id':session}) is None
