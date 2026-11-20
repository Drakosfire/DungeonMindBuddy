"""Explicit same-source quote partitions produce immutable reviewable children."""
import hashlib
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from apps.live_control_server.models.extract_promote import WorldbuildingEvidencePart, WorldbuildingEvidenceQuoteAssignment
from apps.live_control_server.services import exact_run_evidence_correction as owner
from tests.test_demo_derived_candidate_evidence_correction import _fixture, _request


def stage(monkeypatch,tmp_path):
    parent,_,_,span,children=_fixture(monkeypatch,tmp_path)
    path=tmp_path/'parent.json';payload=json.loads(path.read_bytes())
    ref=payload['nodes'][0]['evidence_refs'][0]
    ref['anchor_quotes']=['Torbin bought the strange seed','Mara keeps a lantern.']
    path.write_text(json.dumps(payload));before=path.read_bytes()
    source=tmp_path/'source.md';source.write_text('Torbin, who bought the strange seed, repaired the roof.\nMara keeps a lantern.\n')
    index=SimpleNamespace(spans=[SimpleNamespace(source_span_id=span,start_line=1,end_line=1),
        SimpleNamespace(source_span_id='second-paragraph',start_line=2,end_line=2)])
    parent._test_span_index=index
    q=_request(hashlib.sha256(before).hexdigest(),span)
    q.source_sha256=hashlib.sha256(source.read_bytes()).hexdigest()
    q.corrections[0].expected_ref_sha256=owner._sha(owner._canonical_bytes(ref))
    q.corrections[0].parts.append(WorldbuildingEvidencePart(source_span_ref_id='second-paragraph',quote_assignments=[
        WorldbuildingEvidenceQuoteAssignment(original_quote_index=1,replacement_quote='Mara keeps a lantern.')]))
    return parent,children,q,before,payload,index


def test_complete_multi_paragraph_partition_preserves_semantics_parent_and_retry(monkeypatch,tmp_path):
    parent,children,q,before,payload,_=stage(monkeypatch,tmp_path)
    receipt=owner.correct_exact_run_evidence(q)
    assert owner.correct_exact_run_evidence(q)==receipt
    assert len(children)==1 and parent.revision==7
    child=children[receipt.run_id]
    assert child.status.value=='reviewable' and child.lineage['derivation']=='operator_frozen_evidence_partition_v2'
    actual=json.loads((tmp_path/child.components['candidate_graph'].uri).read_bytes())
    refs=actual['nodes'][0]['evidence_refs']
    assert [r['source_span_ref_id'] for r in refs]==[q.corrections[0].parts[0].source_span_ref_id,'second-paragraph']
    assert [r['anchor_quotes'] for r in refs]==[['who bought the strange seed'],['Mara keeps a lantern.']]
    actual['nodes'][0]['evidence_refs']=payload['nodes'][0]['evidence_refs']
    assert actual==payload and (tmp_path/'parent.json').read_bytes()==before


@pytest.mark.parametrize('bad',['missing_index','duplicate_index','unknown_index','unknown_span','duplicate_span','nonliteral',
    'ref_preimage','candidate_preimage','source_preimage','index_preimage','world','artifact','run_revision','run_status','ambiguous_span','unrelated_invalid'])
def test_invalid_partition_cannot_create_child(monkeypatch,tmp_path,bad):
    parent,children,q,before,payload,index=stage(monkeypatch,tmp_path)
    parts=q.corrections[0].parts
    if bad=='missing_index':parts.pop()
    elif bad=='duplicate_index':parts[1].quote_assignments[0].original_quote_index=0
    elif bad=='unknown_index':parts[1].quote_assignments[0].original_quote_index=3
    elif bad=='unknown_span':parts[1].source_span_ref_id='foreign-span'
    elif bad=='duplicate_span':parts[1].source_span_ref_id=parts[0].source_span_ref_id
    elif bad=='nonliteral':parts[1].quote_assignments[0].replacement_quote='invented prose'
    elif bad=='ref_preimage':q.corrections[0].expected_ref_sha256='0'*64
    elif bad=='candidate_preimage':q.parent_candidate_sha256='0'*64
    elif bad=='source_preimage':q.source_sha256='0'*64
    elif bad=='index_preimage':q.span_index_sha256='0'*64
    elif bad=='world':q.world_id='foreign'
    elif bad=='artifact':q.source_artifact_id='foreign'
    elif bad=='run_revision':q.expected_parent_revision=6
    elif bad=='run_status':parent.status=owner.ExtractionRunStatus.VALIDATED
    elif bad=='ambiguous_span':index.spans.append(deepcopy(index.spans[0]))
    elif bad=='unrelated_invalid':
        other=deepcopy(payload['nodes'][0]);other['node_id']='other'
        other['evidence_refs'][0]['anchor_quotes']=['not in the source']
        payload['nodes'].append(other);path=tmp_path/'parent.json';path.write_text(json.dumps(payload))
        q.parent_candidate_sha256=hashlib.sha256(path.read_bytes()).hexdigest();before=path.read_bytes()
    with pytest.raises(owner.ExtractPromoteError):owner.correct_exact_run_evidence(q)
    assert not children and (tmp_path/'parent.json').read_bytes()==before


def test_catalog_contains_exact_frozen_spans_and_full_ref_preimages(monkeypatch,tmp_path):
    _,_,q,_,payload,_=stage(monkeypatch,tmp_path)
    c=owner.get_worldbuilding_frozen_spans('parent')
    assert c.parent_revision==7 and c.parent_candidate_sha256==q.parent_candidate_sha256
    assert c.source_sha256==q.source_sha256 and c.span_index_sha256==q.span_index_sha256
    assert c.spans[1].source_span_ref_id=='second-paragraph'
    assert c.spans[1].paragraph_text=='Mara keeps a lantern.'
    assert c.evidence_refs[0].ref_sha256==owner._sha(owner._canonical_bytes(payload['nodes'][0]['evidence_refs'][0]))


def test_worldbuilding_transport_has_no_v1_quote_request_fallback(monkeypatch,tmp_path):
    _,_,q,_,_,_=stage(monkeypatch,tmp_path)
    raw=q.model_dump();raw['schema_']='dmb_exact_run_evidence_correction_request_v1'
    with pytest.raises(ValidationError):type(q).model_validate(raw)


def test_route_catalog_rejects_extra_selectors_and_old_world_quote_wire(monkeypatch,tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.live_control_server.routes import extract_promote as route
    _,_,q,_,_,_=stage(monkeypatch,tmp_path)
    calls=[]
    monkeypatch.setattr(route,'get_worldbuilding_frozen_spans',lambda run: (calls.append(run),owner.get_worldbuilding_frozen_spans(run))[1])
    app=FastAPI();app.include_router(route.router)
    with TestClient(app) as client:
        base='/api/live/extract-promote/runs/parent'
        assert client.get(base+'/frozen-source-spans?source=foreign').status_code==422
        assert not calls
        response=client.get(base+'/frozen-source-spans')
        assert response.status_code==200 and response.json()['parentRevision']==7
        bad=q.model_dump(mode='json',by_alias=True);bad['schema']='dmb_exact_run_evidence_correction_request_v1'
        assert client.post(base+'/evidence-corrections',json=bad).status_code==422
        valid=client.post(base+'/evidence-corrections',json=q.model_dump(mode='json',by_alias=True))
        assert valid.status_code==200 and valid.json()['status']=='reviewable'


@pytest.mark.parametrize('interleaved',[False,True])
def test_original_global_quote_order_is_preserved_or_rejected(monkeypatch,tmp_path,interleaved):
    _,children,q,_,payload,index=stage(monkeypatch,tmp_path)
    source=tmp_path/'source.md';source.write_text('Zero.\nOne.\nTwo.\n')
    index.spans[0].end_line=3
    old=payload['nodes'][0]['evidence_refs'][0];old['anchor_quotes']=['Zero.','One.','Two.']
    path=tmp_path/'parent.json';path.write_text(json.dumps(payload));before=path.read_bytes()
    q.source_sha256=hashlib.sha256(source.read_bytes()).hexdigest();q.parent_candidate_sha256=hashlib.sha256(before).hexdigest()
    q.corrections[0].expected_ref_sha256=owner._sha(owner._canonical_bytes(old))
    def part(span,indices):return WorldbuildingEvidencePart(source_span_ref_id=span,quote_assignments=[
        WorldbuildingEvidenceQuoteAssignment(original_quote_index=i,replacement_quote=old['anchor_quotes'][i]) for i in indices])
    first=index.spans[0].source_span_id
    q.corrections[0].parts=([part(first,[0,2]),part('second-paragraph',[1])] if interleaved
        else [part(first,[0]),part('second-paragraph',[1]),part(first,[2])])
    if interleaved:
        with pytest.raises(owner.ExtractPromoteError,match='original quote order'):owner.correct_exact_run_evidence(q)
        assert not children
    else:
        receipt=owner.correct_exact_run_evidence(q);child=children[receipt.run_id]
        result=json.loads((tmp_path/child.components['candidate_graph'].uri).read_bytes())
        assert [q for ref in result['nodes'][0]['evidence_refs'] for q in ref['anchor_quotes']]==old['anchor_quotes']
    assert path.read_bytes()==before
