"""Campaign scope projection without a database or provider."""
from copy import deepcopy
import json

import pytest
from application_state.agent_conversation.native_evidence_view import (
    expected_semantic_frame, semantic_frame,
)


def host_frame():
    metadata = dict(scope=[], visibility='gm', epistemic_basis='observed',
                    claim_mode='fact', standing='current', evidence_ref_ids=[],
                    temporal_scope=None, domain_metadata=[])
    def assertion(campaign):
        value = deepcopy(metadata)
        value['scope'] = [{'axis': 'dungeonbuddy.scope:campaign', 'value': campaign}]
        return {'assertion': {'subject_entity_id': 'host-entity', 'predicate': 'knows',
                              'value': {'kind': 'literal', 'value': 'a meaningful name'},
                              'metadata': value}}
    payload = dict(schema='statement', clause={'campaign': 'host-campaign-a'},
                   quote='a meaningful name', meaning='literal evidence', mode='fact',
                   reporter=None, referents=[], uncertainty=[], qualifications={},
                   episode=None, source_order=[], embedded_content_factive=True,
                   assertion_target=None, visibility='gm', proof={})
    return dict(schema='dmb_surface_native_writer_evidence_v2', input_status='complete',
                user_question='Explain', native_body_evidence={'source_authority_status': 'available', 'excerpts': []},
                native_statements={'status': 'available', 'statements': [{'payload': payload}]},
                native_assertions={'status': 'available', 'assertions': [
                    assertion('host-campaign-a'), assertion('host-campaign-b'), assertion('host-campaign-a')]})


def test_campaign_aliases_preserve_join_and_historical_reconstruction():
    host = host_frame()
    before = deepcopy(host)
    current = semantic_frame(host, alias_campaign_scope=True)
    rows = current['native_assertions']['assertions']
    qualifications = current['native_assertions']['qualifications']
    scope = lambda row: qualifications[row['assertion']['qualification']]['scope'][0]['value']
    assert scope(rows[0]) == scope(rows[2]) == current['native_statements']['statements'][0]['payload']['campaign']
    assert scope(rows[0]) != scope(rows[1])
    wire = json.dumps(current)
    assert 'host-campaign-a' not in wire and 'host-campaign-b' not in wire
    assert 'a meaningful name' in wire
    assert expected_semantic_frame(host, current, alias_campaign_scope=True) == current
    historical = semantic_frame(host)
    assert expected_semantic_frame(host, historical) == historical
    assert host == before


def test_campaign_alias_does_not_accept_unclassified_binding():
    host = host_frame()
    host['native_assertions']['assertions'][0]['assertion']['metadata']['scope'][0]['extra'] = 'unknown'
    with pytest.raises(ValueError, match='Unclassified campaign scope identity'):
        semantic_frame(host, alias_campaign_scope=True)
