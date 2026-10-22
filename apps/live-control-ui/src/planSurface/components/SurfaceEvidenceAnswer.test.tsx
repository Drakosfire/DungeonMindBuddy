import {render,screen,fireEvent} from '@testing-library/react';
import {it,expect,vi} from 'vitest';
import {webcrypto,createHash} from 'node:crypto';
import {getAgentSourcePassage} from '../../api/liveApi';
vi.mock('../../api/liveApi',()=>({getAgentSourcePassage:vi.fn()}));
import {SurfaceEvidenceAnswer} from './SurfaceEvidenceAnswer';
import type {SurfaceEvidenceCompletionV1} from '../../api/types';
function evidence():SurfaceEvidenceCompletionV1 {
 return {schema:'dmb_surface_evidence_completion_v1',surface_id:'plan',context_receipt_sha256:'a'.repeat(64),
 answer_basis:'mixed_evidence',answer_context_status:'authored_grounded',citation_map:null,source_citations:[],answer_segments:[
 {kind:'authored_quote',text:'A proposed outing.',source_kind:'plan',source_name:'Committed Plan',source_handle:'q1',object_id:'p',revision:'1',body_sha256:'b'.repeat(64),owner_sha256:'b'.repeat(64)},
 {kind:'source_passage_claim',text:'The journal describes a walkway.'}]};
}
it('keeps quoted Plan material visibly separate from source-supported prose',()=>{
  render(<SurfaceEvidenceAnswer completion={evidence()}/>);
  expect(screen.getByText('Committed Plan · quoted excerpt')).toBeTruthy();
  expect(screen.getByText('A proposed outing.').closest('blockquote')).not.toBeNull();
  expect(screen.getByLabelText('Source-supported statement').textContent).toContain('journal describes');
});

it('shows unopened Graph authority and opens the selected named source at its original citation index',async()=>{
  vi.stubGlobal('crypto',webcrypto);
  const c=evidence(),id='11111111-1111-4111-8111-111111111111';
  const passage='An exact synthetic source passage.';
  const hash=(s:string)=>createHash('sha256').update(s).digest('hex');
  c.answer_segments.unshift({kind:'graph_claim',text:'A Graph fact with unopened source.',claim_id:'g',target_kind:'assertion',target_id:'a',graph_revision:'r',evidence_ref_ids:['e']});
  c.answer_segments.splice(1,0,{kind:'source_passage_claim',text:'Another independently cited source fact.'});
  const citation={segment_index:3,text_sha256:hash(c.answer_segments[3]!.text),provider_attempt_id:id,envelope_sha256:'d'.repeat(64),read_event_id:id,
    source_name:'Synthetic park journal',receipt:{source_read_id:'read1',anchor_id:'anchor',evidence_ref_id:'e',source_artifact_id:'source',source_revision_id:'rev',
      outcome:'enough' as const,content_sha256:hash(passage),line_start:5,line_end:5,returned_chars:passage.length,truncated:false as const,evidence_sufficiency_status:'sufficient' as const}};
  c.source_citations=[{...citation,segment_index:1,source_name:'Other journal'},citation];
  c.answer_context_status='graph_grounded';c.citation_map={schema:'dmb_graph_citation_map_v2',context_receipt_sha256:c.context_receipt_sha256,entries:[{claim_id:'g',target_kind:'assertion',target_id:'a',graph_revision:'r',evidence_ref_ids:['e'],source_opened:false,source_read_ids:[]}]};
  vi.mocked(getAgentSourcePassage).mockResolvedValue({schema:'dmb_agent_source_passage_read_v1',target:{schema:'dmb_agent_source_passage_open_target_v1',kind:'source_passage',world_id:'w',turn_id:id,citation_index:1},citation,content:passage});
  render(<SurfaceEvidenceAnswer completion={c} worldId="w" turnId={id}/>);
  expect(screen.getByText('World Graph · source passage not opened')).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Read Synthetic park journal · lines 5–5'}));
  await screen.findByText(passage);
  expect(getAgentSourcePassage).toHaveBeenCalledWith('w',id,1);
});
