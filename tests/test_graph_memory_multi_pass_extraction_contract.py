from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

from evals.graph_memory_layer import multi_pass_extraction_contract as c
from evals.graph_memory_layer.validate_session_23_recap_ingest_fixture import main as validate_recap
from evals.graph_memory_layer.validate_session_23_candidate_graph_gold_fixture import main as validate_gold


def text(obj): return json.dumps(obj, sort_keys=True).lower()
def pass_by(fid): return {p['pass_id']: p for p in c.load_session_23_contract_fixture()['passes']}[fid]


def test_manifest():
    m=c.load_contract(); c.validate_contract_manifest(m)
    assert m['schema']==c.CONTRACT_SCHEMA and m['version']==c.CONTRACT_VERSION
    assert m['contract_id']==c.CONTRACT_ID and m['campaign_id']=='longmont-c2' and m['target_session']==23
    assert m['execution_mode']=='contract_only' and m['pass_order']==c.PASS_ORDER
    assert all(v is False for k,v in m['diagnostics'].items() if k!='contract_only')


def test_dependencies():
    validate_recap(); validate_gold(); c.validate_dependencies()
    root=c.repo_root()
    f=c.load_session_23_contract_fixture()
    assert (root/f['gold_fixture']['candidate_graph_gold_path']).exists()
    assert (root/f['source_fixture']['source_span_seed_refs_path']).exists()


def test_pass_contracts():
    f=c.load_session_23_contract_fixture(); c.validate_pass_contracts(f)
    assert len(f['passes'])==9
    assert [p['pass_id'] for p in f['passes']]==c.PASS_ORDER
    assert len({p['pass_id'] for p in f['passes']})==9
    for p in f['passes']:
        assert p['purpose'] and p['input_contract'] is not None and p['output_contract']
        assert p['hard_gates'] and 'forbidden_outputs' in p and 'allowed_dependencies' in p
        assert p['schema'] in c.ALLOWED_OUTPUT_SCHEMAS
        deps = p['input_contract']['depends_on_previous_passes']
        assert deps == c.EXPECTED_PASS_DEPENDENCIES[p['pass_id']]
        index = c.PASS_ORDER.index(p['pass_id'])
        assert set(deps) <= set(c.PASS_ORDER[:index])
        assert (index == 0 and deps == []) or (index > 0 and deps)
        assert 'actual_extractor_output' not in text(p)


def test_source_span_selection_contract():
    t=text(pass_by('source_span_selection'))
    assert 'known source_span_seed_refs' in t and 'no invented source_anchor_id' in t
    assert 'openable' in t and 'highlightable' in t and 'no raw source text body' in t


def test_named_entity_contract():
    p=pass_by('named_entity_candidate_extraction'); policies=set(p['output_contract']['identity_policies'])
    assert {'directly_named','role_only','separate_span_binding','deferred_identity','canonical_alias_deferred'} <= policies
    t=text(p); assert 'lysandro' in t and 'canonical party-name binding' in t


def test_unnamed_important_contract():
    p=pass_by('unnamed_important_concept_extraction'); concepts=' '.join(p['output_contract']['required_session_23_concepts']).lower()
    for needle in ['first meat wave','tripod meat monsters','flying meatwings','remaining approaching horde']:
        assert needle in concepts
    assert 'second-wave wording' in text(p) and 'statblock inference' in text(p)


def test_relationship_contract():
    p=pass_by('relationship_edge_proposal'); rel=set(p['output_contract']['allowed_relationship_types'])
    assert {'recognizes','warns_of','commands_attack','identifies_weakness','threatens'} <= rel
    t=text(p); assert 'edge endpoints must exist' in t and 'edge evidence required' in t and 'unsupported relation inference' in t


def test_ignored_deferred_contract():
    p=pass_by('ignored_deferred_detection'); t=text(p)
    for needle in ['exact shadow count','unnamed experienced adventurer identities','exact mechanical statblocks','help edge or defend mireward','first-wave outcome','mireward overrun risk','canonical party-name binding','cliffhanger resolution']:
        assert needle in t


def test_evidence_alignment_contract():
    p=pass_by('evidence_alignment'); t=text(p)
    assert 'high_risk_evidence_audit' in t and 'lysandro name + father relationship' in t
    for needle in ['every candidate object must have evidence refs','no unknown source_anchor_id','every source evidence ref must resolve','highlight','no heading-only snippets']:
        assert needle in t


def test_candidate_graph_assembly_contract():
    t=text(pass_by('candidate_graph_assembly'))
    for needle in ['candidategraphpreview','status must be preview','diagnostics.preview_only must be true','no promoted lifecycle','approved writes','ignored/deferred items preserved']:
        assert needle in t


def test_gold_comparison_contract():
    g=c.load_session_23_gold_comparison_contract(); c.validate_gold_comparison_contract(g)
    assert g['gold_fixture_id']=='graph-memory:session-23-candidate-graph-gold:v0'
    assert g['matching_policy'] and g['soft_scores'] and g['issue_categories']
    assert set(c.HARD_FAILURE_CATEGORIES) <= set(g['hard_failure_categories'])
    assert set(c.SOFT_MISS_CATEGORIES) <= set(g['soft_miss_categories'])


def test_safety_boundaries():
    objs=[c.load_contract(),c.load_session_23_contract_fixture(),c.load_session_23_expected_pass_outline(),c.load_session_23_gold_comparison_contract()]
    c.validate_safety_boundaries(*objs)
    t=text(objs)
    for needle in ['llm_response','extraction_output','graph_write_result','runtime_payload','plan_payload','agent_interaction_payload','corpus_mutation_payload']:
        assert needle not in t
    assert '/workspace/' not in t


def test_cli_validator_and_report():
    for mod in ['evals.graph_memory_layer.validate_multi_pass_extraction_contract','evals.graph_memory_layer.report_multi_pass_extraction_contract']:
        r=subprocess.run([sys.executable,'-m',mod], cwd=c.repo_root(), text=True, capture_output=True, check=True)
        assert r.returncode==0
        if mod.endswith('report_multi_pass_extraction_contract'):
            assert '## Pass Order' in r.stdout and '## Hard Failure Categories' in r.stdout and '## Boundary Statement' in r.stdout
