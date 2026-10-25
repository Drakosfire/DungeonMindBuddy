"""Real native candidate qualification within the connected-page saga."""
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


def test_mounted_saga_builds_real_native_candidate_for_both_distinct_edges(case,monkeypatch):  # noqa: F811
    original=case.authority.publish
    candidates=[]
    def native_boundary(request):
        contribution=request.contribution
        assert contribution.source_kind=='graph_review_authored_assertion'
        pairs={(a.source_artifact_id,a.source_revision_id):a.source_revision_id for a in contribution.accepted_assertions}
        candidate,_=_build_v2_candidate(contribution,context=WorldGraphMutationContext(
            world_id=case.record.world_id,revision_id='rev:d0',head_revision_id='rev:d0',objects={}),
            pair_to_dm=pairs,produced_at=datetime.now(UTC))
        candidates.append(candidate)
        return original(request)
    monkeypatch.setattr(case.authority,'publish',native_boundary)
    operation=prepare(case)
    result=confirm(case,operation)
    assert result.status_code==200,result.text
    assert len(candidates)==1
    edges=[a for a in candidates[0].assertions if a.assertion_kind=='edge']
    assert {a.predicate for a in edges}=={'owns','operates'}
    assert {json.loads(a.value)['dm_predicate'] for a in edges}=={'dnd5e:owns','dnd5e:operates'}
    assert len({(a.subject_object_id,a.object_object_id) for a in edges})==1
    assert confirm(case,operation).status_code==200
    assert len(candidates)==1
