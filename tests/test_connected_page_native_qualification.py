"""Legacy shared Graph Review qualification and current native connected-page proof."""
from datetime import UTC, datetime
import json

import pytest
from dungeonmind.contracts.contribution import GraphContributionAssertionV2
from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
    _qualified_edge_update, _build_v2_candidate, WorldGraphWriteError,
)
from apps.live_control_server.models.world_graph_mutation_context import WorldGraphMutationContext
from tests.test_connected_page_authoring import case, prepare, confirm  # noqa: F401
from tests.test_graph_document_source import case as source_case  # noqa: F401


def edge(value='{}'):
    return GraphContributionAssertionV2(assertion_id='edge:operation',assertion_kind='edge',
        subject_object_id='person',object_object_id='place',predicate='operates',label='Operates',value=value)


def test_explicit_operation_qualifies_without_ownership_or_direction_change():
    update=_qualified_edge_update(edge(),endpoint_kinds={'person':'npc','place':'location'},place_operation=True)
    assert json.loads(update['value'])=={'dm_predicate':'dnd5e:operates'}
    assert 'subject_object_id' not in update and 'object_object_id' not in update
    with pytest.raises(WorldGraphWriteError,match='explicit graph-review'):
        _qualified_edge_update(edge(),endpoint_kinds={'person':'npc','place':'location'})
    with pytest.raises(WorldGraphWriteError,match='explicit graph-review'):
        _qualified_edge_update(edge('{"dm_predicate":"dnd5e:operates"}'),endpoint_kinds={'person':'npc','place':'location'})


@pytest.mark.parametrize('kinds',[{'person':'location','place':'npc'}, {'person':'faction','place':'location'}, {'person':'npc','place':'item'}])
def test_wrong_or_reversed_operation_endpoints_refuse(kinds):
    with pytest.raises(WorldGraphWriteError,match='endpoint kinds'):
        _qualified_edge_update(edge(),endpoint_kinds=kinds,place_operation=True)
    # A caller qualification must not bypass endpoint validation.
    with pytest.raises(WorldGraphWriteError,match='endpoint kinds'):
        _qualified_edge_update(edge('{"dm_predicate":"dnd5e:operates"}'),endpoint_kinds=kinds,place_operation=True)


def test_wrong_prequalified_term_refuses():
    with pytest.raises(WorldGraphWriteError,match='differs'):
        _qualified_edge_update(edge('{"dm_predicate":"dnd5e:owns"}'),endpoint_kinds={'person':'npc','place':'location'},place_operation=True)


def test_mounted_saga_publishes_current_native_edges_with_exact_authored_support(case):  # noqa: F811
    from dungeonmind.application.vnext import EntityReadService, EvidenceReadService, open_admitted_native_text
    from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
    operation=prepare(case)
    assert operation['schema']=='dmb_connected_page_operation_v3'
    assert case.authority.publish_calls==0
    response=confirm(case,operation)
    assert response.status_code==200,response.text
    receipt=response.json()['receipt']
    person=receipt['created_node_ids']['person'];place=receipt['created_node_ids']['place']
    assert person.startswith('ent:') and place.startswith('ent:')
    read,access,*_=native.read_context(case.repo,case.binding.native_world_id,receipt['published_revision_id'],None,'gm',scope_mode='world')
    entity=EntityReadService().get_complete_entity(read,person)
    edges=[a for a in entity.assertions if a.value.kind=='entity_ref' and a.value.entity_id==place]
    assert {a.predicate for a in edges}=={'dungeonbuddy.custom:owns','dungeonbuddy.custom:operates'}
    assert len({a.assertion_id for a in edges})==2
    for edge in edges:
        assert edge.metadata.scope==()
        assert edge.metadata.epistemic_basis=='asserted'
        assert edge.metadata.temporal_scope.kind=='unknown'
        proof=EvidenceReadService().get_assertion_evidence(read,edge.assertion_id)
        assert proof.available and proof.completeness.status=='complete'
        support=[e for e in proof.evidence if e.evidence_role=='support']
        assert len(support)==1
        opened=open_admitted_native_text(access,support[0].evidence_ref_id)
        assert opened.status=='available'
        quote=opened.body_text.encode()[opened.span_start_byte:opened.span_end_byte].decode()
        predicate=edge.predicate.split(':')[-1]
        assert quote==f'Brin {predicate} Brin’s Blacksmithy.'
    assert confirm(case,operation).status_code==200
    assert case.authority.publish_calls==1
