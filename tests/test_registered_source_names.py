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
