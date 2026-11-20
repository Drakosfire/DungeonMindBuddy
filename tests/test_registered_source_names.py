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


@pytest.mark.parametrize('key', ['dungeonbuddy.recap', 'fixture.recaps', 'recap'])
@pytest.mark.parametrize('session', ['session-16', 'session-20'])
def test_valid_native_artifact_uses_generic_family_not_producer_key(key, session):
    from dungeonmind.contracts.evidence import SourceArtifactV2
    artifact = SourceArtifactV2(source_artifact_id='opaque', source_domain_key=key,
        source_domain='session_recap', world_id='world', campaign_id='campaign', session_id=session,
        uri=None, current_revision_id=None, authority=None, visibility=None, artifact_kind=None,
        document_class=None, review_state=None, source_visibility_state=None, workspace_document_ref=None,
        lineage={}, status='active', created_at=None, updated_at=None)
    from application_state.source.naming import registered_source_name
    expected = f"Session {session.split('-')[1]} recap"
    assert registered_source_name(artifact.model_dump(mode='json')) == _registered_source_name(artifact) == expected


@pytest.mark.parametrize('domain', ['worldbuilding', 'other', 'unknown', ''])
def test_producer_key_never_overrides_explicit_non_recap_family(domain):
    from application_state.source.naming import registered_source_name
    assert registered_source_name({'source_domain_key':'recap','source_domain':domain,'session_id':'session-29'}) is None
