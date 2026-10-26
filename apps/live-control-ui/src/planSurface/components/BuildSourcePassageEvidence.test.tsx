import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createHash, webcrypto } from 'node:crypto';
import { BuildSourcePassageEvidence, isBuildSourceCompletion, isSurfaceSourceCompletion } from './BuildSourcePassageEvidence';
import { ResponseEvidenceTabs } from './ResponseEvidenceTabs';
import { getAgentSourcePassage, getAgentRelatedPage } from '../../api/liveApi';
import type { AgentSourcePassageReadResponseV1, WorldBuildGraphCompletionV2, SurfaceSourceCompletionV1 } from '../../api/types';
vi.mock('../../api/liveApi', () => ({ getAgentSourcePassage: vi.fn(),getAgentRelatedPage:vi.fn() }));
const load = vi.mocked(getAgentSourcePassage);
const text = 'Frank believes the **western gate** is haunted. 🐐';
const hash = (s: string) => createHash('sha256').update(s).digest('hex');
const id = '11111111-1111-4111-8111-111111111111';
function completion(): WorldBuildGraphCompletionV2 {
  return { schema: 'dmb_build_graph_completion_v2', context_receipt_sha256: 'a'.repeat(64),
    answer_basis: 'opened_source_passages', answer_context_status: 'source_grounded',
    answer_segments: [{kind: 'source_passage_claim', text: 'Frank believes the gate is haunted.'}], citation_map: null,
    source_citations: [{ segment_index: 0, text_sha256: hash('Frank believes the gate is haunted.'),
      provider_attempt_id: id, envelope_sha256: 'c'.repeat(64), read_event_id: id,
      receipt: {source_read_id: 'read', anchor_id: 'anchor', evidence_ref_id: 'evidence',
        source_artifact_id: 'source', source_revision_id: 'source-revision', outcome: 'enough',
        content_sha256: hash(text), line_start: 1, line_end: 1, returned_chars: [...text].length,
        truncated: false, evidence_sufficiency_status: 'sufficient'} } ] };
}
function response(c: WorldBuildGraphCompletionV2, index = 0): AgentSourcePassageReadResponseV1 {
  return {schema: 'dmb_agent_source_passage_read_v1', target: {
    schema: 'dmb_agent_source_passage_open_target_v1', kind: 'source_passage',
    world_id: 'world', turn_id: id, citation_index: index}, citation: c.source_citations[index]!, content: text};
}
beforeEach(() => { vi.resetAllMocks(); vi.stubGlobal('crypto', webcrypto); });
describe('source-only evidence', () => {
  it('requires an explicit read and renders the exact inert Markdown passage', async () => {
    const c = completion(); load.mockResolvedValue(response(c));
    render(<BuildSourcePassageEvidence completion={c} worldId="world" turnId={id} />);
    expect(load).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', {name: 'Read passage 1'}));
    await screen.findByText('western gate');
    expect(load).toHaveBeenCalledWith('world', id, 0);
    expect(screen.getByText('western gate').tagName).toBe('STRONG');
    fireEvent.click(screen.getByRole('button', {name: 'Close passage'}));
    expect(screen.queryByLabelText('Opened source passage')).toBeNull();
  });
  it.each(['body', 'world', 'citation', 'index', 'error'])('refuses %s corruption without replacement', async failure => {
    const c = completion(), r = response(c);
    if (failure === 'body') r.content = 'x'.repeat([...text].length);
    if (failure === 'world') r.target.world_id = 'other';
    if (failure === 'citation') r.citation = {...r.citation, envelope_sha256: 'f'.repeat(64)};
    if (failure === 'index') r.target.citation_index = 1;
    if (failure === 'error') load.mockRejectedValue(new Error('missing')); else load.mockResolvedValue(r);
    render(<BuildSourcePassageEvidence completion={c} worldId="world" turnId={id} />);
    fireEvent.click(screen.getByRole('button', {name: 'Read passage 1'}));
    await screen.findByText(/No newer text has been substituted/);
    expect(screen.queryByText('western gate')).toBeNull();
  });
  it('deduplicates repeated receipts and exposes all unique passages', () => {
    const c = completion(), first = c.source_citations[0]!;
    c.source_citations = [first, ...Array.from({length: 10}, (_, i) => ({...first,
      read_event_id: `${String(i).padStart(8,'0')}-1111-4111-8111-111111111111`,
      receipt: {...first.receipt, source_artifact_id: `source-${i}`}})), {...first}];
    render(<BuildSourcePassageEvidence completion={c} worldId="world" turnId={id} />);
    expect(screen.getAllByRole('button', {name: /Read passage/})).toHaveLength(8);
    fireEvent.click(screen.getByRole('button', {name: 'Show more passages'}));
    expect(screen.getAllByRole('button', {name: /Read passage/})).toHaveLength(11);
  });
  it('discards a late read after the World or turn changes', async () => {
    const c = completion(); let resolve!: (r: AgentSourcePassageReadResponseV1) => void;
    load.mockImplementation(() => new Promise(r => {resolve = r;}));
    const {rerender} = render(<BuildSourcePassageEvidence completion={c} worldId="world" turnId={id} />);
    fireEvent.click(screen.getByRole('button', {name: 'Read passage 1'}));
    rerender(<BuildSourcePassageEvidence completion={c} worldId="other-world" turnId={id} />);
    await act(async () => resolve(response(c)));
    expect(screen.queryByLabelText('Opened source passage')).toBeNull();
  });
  it('keeps the existing separate Prompt tab', () => {
    render(<ResponseEvidenceTabs evidence={<BuildSourcePassageEvidence completion={completion()} worldId="world" turnId={id} />}
      prompt={<p>Exact saved request</p>} />);
    fireEvent.click(screen.getByRole('tab', {name: 'The Prompt'}));
    expect(screen.getByText('Exact saved request')).toBeInTheDocument();
    expect(load).not.toHaveBeenCalled();
  });
  it('strictly validates source attribution and rejects Graph masquerading', () => {
    const c = completion(), valid = (v: unknown) => isBuildSourceCompletion(v, 'a'.repeat(64), 'b'.repeat(64));
    expect(valid(c)).toBe(true);
    expect(valid({...c, citation_map: {entries: []}})).toBe(false);
    expect(valid({...c, source_citations: []})).toBe(false);
    expect(valid({...c, context_receipt_sha256: 'f'.repeat(64)})).toBe(false);
    expect(valid({...c, answer_segments: [{kind: 'graph_claim', text: 'invented'}]})).toBe(false);
    expect(valid({...c, answer_context_status: 'source_insufficient_evidence'})).toBe(false);
    expect(valid({...c, source_citations: [{...c.source_citations[0], extra: 'forged'}]})).toBe(false);
  });
});

it.each(['plan','play'] as const)('opens a named source citation for %s using the shared component',async surface=>{
  const c:SurfaceSourceCompletionV1={...completion(),schema:'dmb_surface_source_completion_v1',surface_id:surface,
    answer_basis:'opened_source_passages',answer_context_status:'source_grounded',
    answer_segments:[{kind:'source_passage_claim',text:'Frank believes the gate is haunted.'}],
    source_citations:completion().source_citations.map(c=>({...c,source_name:'Gatekeepers journal'}))};
  expect(isSurfaceSourceCompletion(c,'a'.repeat(64),surface)).toBe(true);
  expect(isSurfaceSourceCompletion(c,'a'.repeat(64),surface==='plan'?'play':'plan')).toBe(false);
  load.mockResolvedValue({schema:'dmb_agent_source_passage_read_v1',target:{schema:'dmb_agent_source_passage_open_target_v1',
    kind:'source_passage',world_id:'world',turn_id:id,citation_index:0},citation:c.source_citations[0]!,content:text});
  render(<BuildSourcePassageEvidence completion={c} worldId="world" turnId={id}/>);
  fireEvent.click(screen.getByRole('button',{name:'Read Gatekeepers journal · lines 1–1'}));
  await screen.findByText('western gate');expect(load).toHaveBeenCalledWith('world',id,0);
});


it('opens a verified named Build citation with the shared numbered control',async()=>{
  const c={...completion(),schema:'dmb_build_graph_completion_v3' as const,
    source_citations:completion().source_citations.map(c=>({...c,source_name:'River Watch — synthetic source'}))};
  expect(isBuildSourceCompletion(c,'a'.repeat(64),'b'.repeat(64),'world')).toBe(true);
  expect(isBuildSourceCompletion({...c,source_citations:c.source_citations.map(c=>({...c,source_name:' '}))},'a'.repeat(64),'b'.repeat(64))).toBe(false);
  expect(isBuildSourceCompletion({...c,schema:'dmb_build_graph_completion_v2'},'a'.repeat(64),'b'.repeat(64))).toBe(false);
  load.mockResolvedValue({...response(completion()),citation:c.source_citations[0]!});
  render(<BuildSourcePassageEvidence completion={c} worldId="world" turnId={id}/>);
  const control=screen.getByRole('button',{name:'Read River Watch — synthetic source · lines 1–1'});
  expect(control).toHaveTextContent('1');
  fireEvent.click(control);
  await screen.findByText('western gate');
  expect(screen.getByLabelText('Opened source passage')).toHaveTextContent('River Watch — synthetic source');
});

it('keeps working-draft references out of source citations and preserves mixed source indexes',()=>{
  const base=completion();
  const c:import('../../api/types').WorldBuildDraftContextCompletionV1={
    ...base,schema:'dmb_build_draft_context_completion_v1',answer_basis:'working_draft_context',
    answer_context_status:'authored_grounded',
    answer_segments:[{kind:'draft_reference_claim',text:'A complete working draft response. '+ 'x'.repeat(4200),draft_record_id:id}],
    source_citations:[],
  };
  expect(isBuildSourceCompletion(c,'a'.repeat(64),'b'.repeat(64),'world')).toBe(true);
  const view=render(<BuildSourcePassageEvidence completion={c} worldId="world" turnId={id}/>);
  expect(screen.queryByRole('button',{name:/Read/})).not.toBeInTheDocument();
  expect(load).not.toHaveBeenCalled();
  const mixed={...c,answer_segments:[...c.answer_segments,...base.answer_segments],source_citations:
    base.source_citations.map(cite=>({...cite,segment_index:1,source_name:'Gatekeepers journal'}))};
  expect(isBuildSourceCompletion(mixed,'a'.repeat(64),'b'.repeat(64))).toBe(true);
  view.rerender(<BuildSourcePassageEvidence completion={mixed} worldId="world" turnId={id}/>);
  expect(screen.getAllByRole('button',{name:/Read Gatekeepers journal/})).toHaveLength(1);
  expect(isBuildSourceCompletion({...mixed,source_citations:mixed.source_citations.map(cite=>({...cite,segment_index:0}))},'a'.repeat(64),'b'.repeat(64))).toBe(false);
  expect(isBuildSourceCompletion({...c,answer_segments:[{...c.answer_segments[0],draft_record_id:'forged'}]},'a'.repeat(64),'b'.repeat(64))).toBe(false);
});

describe('exact saved related page citations',()=>{
 const body='# Households\n\n| Household | Work |\n| --- | --- |\n| Copper | Lantern before dusk |';
 function related():import('../../api/types').WorldBuildRelatedPageCompletionV1 {
  return {schema:'dmb_build_related_page_completion_v1',context_receipt_sha256:'a'.repeat(64),answer_basis:'working_draft_context',answer_context_status:'authored_grounded',citation_map:null,source_citations:[],
   answer_segments:[{kind:'related_page_claim',text:'The saved table names Copper House.',read_id:id,
    page:{world_id:'world',document_id:id,registry_revision:9,title:'Households',visibility:'internal',content_sha256:hash(body)}}]};
 }
 it('opens the captured page by exact turn/read and verifies its identity and body',async()=>{
  const c=related(),segment=c.answer_segments[0];if(segment.kind!=='related_page_claim')throw new Error('fixture');
  vi.mocked(getAgentRelatedPage).mockResolvedValue({schema:'dmb_agent_related_page_read_v1',world_id:'world',turn_id:id,read_id:id,page:segment.page,markdown:body});
  expect(isBuildSourceCompletion(c,'a'.repeat(64),'b'.repeat(64),'world')).toBe(true);
  render(<BuildSourcePassageEvidence completion={c} worldId="world" turnId={id}/>);
  expect(getAgentRelatedPage).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Read Households · saved revision 9'}));
  await screen.findByText('Lantern before dusk');
  expect(getAgentRelatedPage).toHaveBeenCalledWith('world',id,id);
 });
 it.each(['world','read','body','page'])('refuses %s substitution without opening a newer page',async mode=>{
  const c=related(),segment=c.answer_segments[0];if(segment.kind!=='related_page_claim')throw new Error('fixture');
  const result={schema:'dmb_agent_related_page_read_v1',world_id:'world',turn_id:id,read_id:id,page:segment.page,markdown:body};
  if(mode==='world')result.world_id='other';if(mode==='read')result.read_id='other';if(mode==='body')result.markdown='Newer body';if(mode==='page')result.page={...segment.page,registry_revision:10};
  vi.mocked(getAgentRelatedPage).mockResolvedValue(result);
  render(<BuildSourcePassageEvidence completion={c} worldId="world" turnId={id}/>);
  fireEvent.click(screen.getByRole('button',{name:'Read Households · saved revision 9'}));
  await screen.findByText('The exact cited section is unavailable. No newer text has been substituted.');
 });
 it('does not admit a related claim under the historical draft completion schema',()=>{
  expect(isBuildSourceCompletion({...related(),schema:'dmb_build_draft_context_completion_v1'},'a'.repeat(64),'b'.repeat(64),'world')).toBe(false);
 });
});

it('requires the verified World when admitting related-page references',()=>{
 const c:import('../../api/types').WorldBuildRelatedPageCompletionV1={schema:'dmb_build_related_page_completion_v1',context_receipt_sha256:'a'.repeat(64),answer_basis:'working_draft_context',answer_context_status:'authored_grounded',citation_map:null,source_citations:[],answer_segments:[{kind:'related_page_claim',text:'Saved page text.',read_id:id,page:{world_id:'foreign',document_id:id,registry_revision:1,title:'Households',visibility:'internal',content_sha256:'b'.repeat(64)}}]};
 expect(isBuildSourceCompletion(c,'a'.repeat(64),'b'.repeat(64),'world')).toBe(false);
 expect(isBuildSourceCompletion(c,'a'.repeat(64),'b'.repeat(64))).toBe(false);
})

it('admits only closed typed collaboration objects and keeps historical shapes closed',()=>{
 const c={schema:'dmb_build_collaboration_completion_v1',context_receipt_sha256:'a'.repeat(64),answer_basis:'working_draft_context',answer_context_status:'creative_proposal',answer_segments:[{kind:'connective',text:'Let’s plan.'}],citation_map:null,source_citations:[],collaboration:{kind:'plan',steps:[{text:'Read the table.',kind:'discuss'},{text:'Prepare prose.',kind:'prepare_insertion'}]}};
 expect(isBuildSourceCompletion(c,'a'.repeat(64),'b'.repeat(64),'world')).toBe(true);
 for(const collaboration of [{kind:'plan',steps:[]},{kind:'plan',steps:[{text:'Write',kind:'create_page'}]},{kind:'questions',questions:[{text:'Which?',answer:'invented'}]}])expect(isBuildSourceCompletion({...c,collaboration},'a'.repeat(64),'b'.repeat(64),'world')).toBe(false);
 expect(isBuildSourceCompletion({...c,schema:'dmb_build_related_page_completion_v1'},'a'.repeat(64),'b'.repeat(64),'world')).toBe(false);
 expect(isBuildSourceCompletion({...c,collaboration:null},'a'.repeat(64),'b'.repeat(64),'world')).toBe(true);
});

it('accepts connected page review only in its new closed completion schema',()=>{
 const collaboration={kind:'connected_page',title:'Copper Forge',read_id:id,quote:'Copper',person_label:'Ada',relationships:['owns','operates'],instructions:'Proposed workshop'};
 const c={schema:'dmb_build_connected_page_review_completion_v1',context_receipt_sha256:'a'.repeat(64),answer_basis:'working_draft_context',answer_context_status:'creative_proposal',answer_segments:[{kind:'connective',text:'Ready for review.'}],citation_map:null,source_citations:[],collaboration};
 expect(isBuildSourceCompletion(c,'a'.repeat(64),'b'.repeat(64),'world')).toBe(true);
 expect(isBuildSourceCompletion({...c,schema:'dmb_build_collaboration_completion_v1'},'a'.repeat(64),'b'.repeat(64),'world')).toBe(false);
 for(const patch of [{read_id:'invented'},{relationships:['allies']},{node_id:'model-guessed-id'},{person_label:null}])expect(isBuildSourceCompletion({...c,collaboration:{...collaboration,...patch}},'a'.repeat(64),'b'.repeat(64),'world')).toBe(false);
});
it('accepts proposed relationships only in their new closed completion schema',()=>{
 const collaboration={kind:'relationship',read_id:id,quote:'Past temporary work.',source:{label:'Rowan',kind:'npc'},target:{label:'Mara',kind:'npc'},predicate:'works_with',label:'worked together',context:'Past temporary work only.'};
 const c={schema:'dmb_build_relationship_review_completion_v1',context_receipt_sha256:'a'.repeat(64),answer_basis:'working_draft_context',answer_context_status:'creative_proposal',answer_segments:[{kind:'connective',text:'Ready for review.'}],citation_map:null,source_citations:[],collaboration};
 expect(isBuildSourceCompletion(c,'a'.repeat(64),'b'.repeat(64),'world')).toBe(true);
 expect(isBuildSourceCompletion({...c,schema:'dmb_build_connected_page_review_completion_v1'},'a'.repeat(64),'b'.repeat(64),'world')).toBe(false);
 for(const patch of [{read_id:'invented'},{source:{...collaboration.source,node_id:'model-id'}},{context:'  '},{published:true}])expect(isBuildSourceCompletion({...c,collaboration:{...collaboration,...patch}},'a'.repeat(64),'b'.repeat(64),'world')).toBe(false);
});

it('decodes neutral and object-only intentional replies without widening historical formats',()=>{
 const value={schema:'dmb_build_intentional_response_completion_v1',context_receipt_sha256:'a'.repeat(64),answer_basis:'conversation',answer_context_status:'discussion',answer_segments:[],citation_map:null,source_citations:[],collaboration:{kind:'questions',questions:[{text:'Which shop?'}]}};
 expect(isBuildSourceCompletion(value,'a'.repeat(64),'b'.repeat(64),'world')).toBe(true);
 expect(isBuildSourceCompletion({...value,collaboration:null},'a'.repeat(64),'b'.repeat(64),'world')).toBe(false);
 expect(isBuildSourceCompletion({...value,schema:'dmb_build_collaboration_completion_v1'},'a'.repeat(64),'b'.repeat(64),'world')).toBe(false);
 expect(isBuildSourceCompletion({...value,answer_segments:[{kind:'saved_source_claim',text:'A fact.',content_sha256:'b'.repeat(64)}]},'a'.repeat(64),'b'.repeat(64),'world')).toBe(false);
 expect(isBuildSourceCompletion({...value,answer_segments:[{kind:'connective',text:'Ready.'}],collaboration:null},'a'.repeat(64),'b'.repeat(64),'world')).toBe(true);
});

it('requires explicit boolean choices in new completions without rewriting retained plans',()=>{
 const value={schema:'dmb_build_intentional_response_completion_v3',context_receipt_sha256:'a'.repeat(64),answer_basis:'conversation',answer_context_status:'discussion',answer_segments:[],citation_map:null,source_citations:[],collaboration:{kind:'plan',objective:'Discuss first; defer writing.',steps:[{text:'Discuss first.',kind:'discuss',selected:true},{text:'Write later.',kind:'prepare_insertion',selected:false}]}};
 const valid=(v:unknown)=>isBuildSourceCompletion(v,'a'.repeat(64),'b'.repeat(64),'world');
 expect(valid(value)).toBe(true);
 for(const selected of [undefined,null,'false',0,1])expect(valid({...value,collaboration:{...value.collaboration,steps:[{...value.collaboration.steps[1],selected}]}})).toBe(false);
 const historical={...value,schema:'dmb_build_intentional_response_completion_v2',collaboration:{...value.collaboration,steps:value.collaboration.steps.map(({selected,...row})=>row)}};
 const before=JSON.stringify(historical);expect(valid(historical)).toBe(true);expect(JSON.stringify(historical)).toBe(before);
 expect(valid({...value,schema:'dmb_build_intentional_response_completion_v2'})).toBe(false);
});
