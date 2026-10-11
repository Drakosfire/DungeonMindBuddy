"""Producer proposals are distinct, default-off and require their selected subject."""
from dataclasses import replace
import pytest

from tests.test_candidate_graph_to_contribution import _minimal_graph
from graph_memory.candidate_graph_to_contribution import load_typed_candidate_graph, CandidateGraphMappingError
from graph_memory.extract_identity_gate import (
    gate_candidate_graph_against_head, build_accepted_contribution_from_proposals,
    build_accepted_contribution_from_multi_slice_proposals,
)
from graph_memory.extract_promote_review_projection import project_promote_review
from apps.live_control_server.models.world_graph_mutation_context import WorldGraphMutationContext


def case(*, blank=False, source_domain="recap"):
    payload=_minimal_graph()
    payload["edges"]=[]
    if blank:
        for node in payload["nodes"]:
            node["description"]=" "
    preview=load_typed_candidate_graph(payload)
    context=WorldGraphMutationContext(
        world_id="world:test",revision_id="rev:parent",head_revision_id="rev:parent",objects={},
    )
    gate=gate_candidate_graph_against_head(
        preview,world_id=context.world_id,source_revision_id="sha256:"+"a"*64,
        campaign_scope=preview.campaign_id,mutation_context=context,
        source_uri="repo://source.md",source_domain=source_domain,include_edges=False,
    )
    return preview,context,gate


def test_create_new_companions_are_separate_default_off_and_source_exact():
    preview,context,gate=case()
    nodes=[a for a in gate.accepted_proposals if a.assertion_kind=="node"]
    observations=[a for a in gate.accepted_proposals if a.assertion_kind=="attribute"]
    assert len(nodes)==len(observations)==2
    items,summary=project_promote_review(gate,contribution_slice_id="0:source")
    assert summary.new_object_count==2
    for node,observation in zip(nodes,observations):
        assert observation.assertion_id!=node.assertion_id
        assert observation.subject_node_id==node.subject_node_id
        assert observation.source_artifact_id==node.source_artifact_id
        assert observation.source_revision_id==node.source_revision_id
        assert observation.evidence_ref_ids==node.evidence_ref_ids
        assert observation.value["summary"]==node.value["summary"]
        assert observation.value["session_ids"]==["session-22"]
        assert observation.value["kind"]==node.value["kind"]
        assert observation.visibility==node.visibility
        item=next(i for i in items if i.assertion_id==observation.assertion_id)
        assert item.selectable and not item.selected_by_default
        assert observation.value["summary"] in item.summary
        assert item.depends_on_slice_qualified_ids==["0:source::"+node.assertion_id]
    default=build_accepted_contribution_from_proposals(gate,mutation_context=context)
    assert all(a.assertion_kind=="node" for a in default.accepted_assertions)
    multi=build_accepted_contribution_from_multi_slice_proposals(
        [(gate,None,"0:source")],mutation_context=context,
    )
    assert all(a.assertion_kind=="node" for a in multi.accepted_assertions)


def test_attribute_subject_selection_is_enforced_single_and_multi_slice():
    _,context,gate=case()
    observation=next(a for a in gate.accepted_proposals if a.assertion_kind=="attribute")
    node=next(a for a in gate.accepted_proposals if a.assertion_kind=="node"
        and a.subject_node_id==observation.subject_node_id)
    with pytest.raises(CandidateGraphMappingError,match="attribute subject"):
        build_accepted_contribution_from_proposals(
            gate,mutation_context=context,accepted_assertion_ids=[observation.assertion_id])
    with pytest.raises(CandidateGraphMappingError,match="attribute subject"):
        build_accepted_contribution_from_multi_slice_proposals(
            [(gate,[observation.assertion_id],"source")],mutation_context=context)
    selected=build_accepted_contribution_from_proposals(
        gate,mutation_context=context,accepted_assertion_ids=[node.assertion_id,observation.assertion_id])
    assert {a.assertion_kind for a in selected.accepted_assertions}=={"node","attribute"}
    node_gate=replace(gate,accepted_proposals=[node])
    observation_gate=replace(gate,accepted_proposals=[observation])
    atomic=build_accepted_contribution_from_multi_slice_proposals(
        [(node_gate,[node.assertion_id],"nodes"),(observation_gate,[observation.assertion_id],"observations")],
        mutation_context=context,
    )
    assert len(atomic.accepted_assertions)==2


@pytest.mark.parametrize("blank,domain",[(True,"recap"),(False,"worldbuilding")])
def test_no_companion_for_empty_description_or_non_recap(blank,domain):
    _,_,gate=case(blank=blank,source_domain=domain)
    assert not any(a.assertion_kind=="attribute" for a in gate.accepted_proposals)
