import {render,screen,fireEvent} from '@testing-library/react';
import {it,expect,vi} from 'vitest';
import {webcrypto,createHash} from 'node:crypto';
import {getAgentSourcePassage,getAgentNativeSourceClause} from '../../api/liveApi';
vi.mock('../../api/liveApi',()=>({getAgentSourcePassage:vi.fn(),getAgentNativeSourceClause:vi.fn()}));
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

it('renders host-materialized excerpts with saved-source attribution',()=>{
  const old=evidence(),quote=old.answer_segments[0]!;
  if(quote.kind!=='authored_quote')throw new Error('fixture');
  const completion:import('../../api/types').SurfaceEvidenceCompletionV2={...old,schema:'dmb_surface_evidence_completion_v2',
    answer_segments:[{...quote,kind:'authored_excerpt',text:'A saved 🐸 observation.\r\n',
      block_handle:'b'+'d'.repeat(64),partition_version:'markdown_source_blocks_v1',byte_start:0,
      byte_end:new TextEncoder().encode('A saved 🐸 observation.\r\n').length,block_sha256:'e'.repeat(64),entry_identity:null}]};
  render(<SurfaceEvidenceAnswer completion={completion}/>);
  expect(screen.getByText('A saved 🐸 observation.').closest('blockquote')).not.toBeNull();
  expect(screen.getByText('Committed Plan · quoted excerpt')).toBeTruthy();
});

it('links a session excerpt to its exact World, Run and immutable review checkpoint',()=>{
  const c=evidence(),quote=c.answer_segments[0]!;
  if(quote.kind!=='authored_quote')throw new Error('fixture');
  c.answer_segments=[{...quote,source_kind:'session',source_name:'Synthetic park outing — notes and reflections',
    object_id:'11111111-1111-4111-8111-111111111111',revision:'54'}];
  render(<SurfaceEvidenceAnswer completion={c} worldId="park / &"/>);
  const link=screen.getByRole('link',{name:'Synthetic park outing — notes and reflections'});
  const target=new URL(link.getAttribute('href')!, 'http://localhost');
  expect(target.pathname).toBe('/play');
  expect(Object.fromEntries(target.searchParams)).toEqual({world:'park / &',run:'11111111-1111-4111-8111-111111111111',evidence_revision:'54'});
  expect(target.searchParams.has('review')).toBe(false);
  expect(screen.getByText('A proposed outing.').closest('blockquote')).not.toBeNull();
});

it.each([{kind:'plan' as const,world:'park'},{kind:'session' as const,world:null}])(
  'does not invent a session destination for $kind with World $world',({kind,world})=>{
    const c=evidence(),quote=c.answer_segments[0]!;
    if(quote.kind!=='authored_quote')throw new Error('fixture');
    c.answer_segments=[{...quote,source_kind:kind}];
    render(<SurfaceEvidenceAnswer completion={c} worldId={world}/>);
    expect(screen.queryByRole('link')).toBeNull();
    expect(screen.getByText('A proposed outing.').closest('blockquote')).not.toBeNull();
  });


it.each(['exact','changed-bytes','changed-revision','changed-campaign'])('opens only the original native statement clause: %s',async change=>{
  vi.stubGlobal('crypto',webcrypto);
  const content='A reports that B fled; uncertain.\n';
  const hash=(s:string)=>createHash('sha256').update(s).digest('hex');
  const citation:import('../../api/types').NativeStatementClauseCitationV1={segment_index:0,
    statement_id:'ent:statement',provider_attempt_id:'attempt',envelope_sha256:'b'.repeat(64),context_receipt_sha256:'a'.repeat(64),
    managed_world_id:'native-world',native_world_id:'native',campaign_id:'c1',read_revision_id:'rev:R',publication_revision_id:'rev:C',
    source_artifact_id:'source',source_revision_id:'source:1',body_sha256:'c'.repeat(64),start_byte:0,
    end_byte:new TextEncoder().encode(content).length,clause_sha256:hash(content),semantic_digest:'d'.repeat(64)};
  const completion:import('../../api/types').SurfaceEvidenceCompletionV6={schema:'dmb_surface_evidence_completion_v6',surface_id:'plan',
    context_receipt_sha256:'a'.repeat(64),answer_basis:'mixed_evidence',answer_context_status:'source_grounded',citation_map:null,
    source_citations:[],native_source_citations:[],native_body_citations:[],native_clause_citations:[citation],
    answer_segments:[{kind:'source_passage_claim',text:'Source reports: an uncertain escape.'}]};
  const response={schema:'dmb_native_statement_clause_read_v1' as const,world_id:'native-world',turn_id:'turn',citation_index:0,citation:{...citation},content};
  if(change==='changed-bytes')response.content='Nearby unsupported prose.';
  if(change==='changed-revision')response.citation.source_revision_id='source:new-head';
  if(change==='changed-campaign')response.citation.campaign_id='foreign';
  vi.mocked(getAgentNativeSourceClause).mockResolvedValue(response);
  render(<SurfaceEvidenceAnswer completion={completion} worldId="native-world" turnId="turn"/>);
  fireEvent.click(screen.getByRole('button',{name:'Read source statement · c1'}));
  if(change==='exact')await screen.findByText('A reports that B fled; uncertain.');
  else await screen.findByText('The exact cited section is unavailable. No newer text has been substituted.');
  expect(getAgentNativeSourceClause).toHaveBeenCalledWith('native-world','turn',0);
});
