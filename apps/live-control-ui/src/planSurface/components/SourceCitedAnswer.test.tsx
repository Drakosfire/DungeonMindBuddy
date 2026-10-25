import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {beforeEach,it,expect,vi} from 'vitest';
import {createHash,webcrypto} from 'node:crypto';
import {SourceCitedAnswer} from './SourceCitedAnswer';
import {getAgentSavedSection,getAgentRelatedPage,getAgentSourcePassage} from '../../api/liveApi';
import type {WorldBuildConnectedPageReviewCompletionV1,SavedBuildSectionTargetV1} from '../../api/types';
vi.mock('../../api/liveApi',()=>({getAgentSavedSection:vi.fn(),getAgentRelatedPage:vi.fn(),getAgentSourcePassage:vi.fn()}));
const id='11111111-1111-4111-8111-111111111111',read='22222222-2222-4222-8222-222222222222';
const hash=(s:string)=>createHash('sha256').update(s).digest('hex');
const current='Current page **orchids**.',related='Workshop practice bells.',world='Mara owns the workshop.';
const basis={world_id:'world',document_id:'current',registry_revision:2,content_sha256:'a'.repeat(64),visibility:'internal' as const};
function fixture(){
 const segments=[{kind:'saved_source_claim' as const,text:'The current page describes orchids.',content_sha256:basis.content_sha256},
  {kind:'related_page_claim' as const,text:'The other page describes bells.',read_id:read,page:{...basis,document_id:read,title:'Workshop',registry_revision:3,content_sha256:hash(related)}},
  {kind:'source_passage_claim' as const,text:'Mara owns the shop.'}];
 const citation={segment_index:2,text_sha256:hash(segments[2]!.text),provider_attempt_id:id,envelope_sha256:'c'.repeat(64),read_event_id:id,source_name:'World record',receipt:{source_read_id:'read',anchor_id:'anchor',evidence_ref_id:'ev',source_artifact_id:'source',source_revision_id:'revision',outcome:'enough' as const,content_sha256:hash(world),line_start:1,line_end:1,returned_chars:world.length,truncated:false,evidence_sufficiency_status:'sufficient' as const}};
 const completion:WorldBuildConnectedPageReviewCompletionV1={schema:'dmb_build_connected_page_review_completion_v1',context_receipt_sha256:'b'.repeat(64),answer_basis:'working_draft_context',answer_context_status:'authored_grounded',citation_map:null,collaboration:null,source_citations:[citation],answer_segments:segments};
 const target:SavedBuildSectionTargetV1={schema:'dmb_saved_build_section_target_v1',kind:'saved_build_section',world_id:'world',turn_id:id,segment_index:0,section_event_id:id,section_read_id:id,source_basis:basis,source_class:'saved_authored_source_not_played_truth',line_start:1,line_end:1,excerpt_sha256:hash(current),text_sha256:hash(segments[0]!.text)};
 return {completion,target,props:{answer:segments.map(s=>s.text).join('\n'),completion,worldId:'world',turnId:id,saved:{targets:[target],basis,sourceName:'Current page'}}};
}
beforeEach(()=>{vi.clearAllMocks();vi.stubGlobal('crypto',webcrypto);const {completion,target}=fixture();
 vi.mocked(getAgentSavedSection).mockResolvedValue({schema:'dmb_saved_build_section_read_v1',target,content:current});
 const s=completion.answer_segments[1]!;if(s.kind!=='related_page_claim')throw new Error('fixture');
 vi.mocked(getAgentRelatedPage).mockResolvedValue({schema:'dmb_agent_related_page_read_v1',world_id:'world',turn_id:id,read_id:read,page:s.page,markdown:related});
 vi.mocked(getAgentSourcePassage).mockResolvedValue({schema:'dmb_agent_source_passage_read_v1',target:{schema:'dmb_agent_source_passage_open_target_v1',kind:'source_passage',world_id:'world',turn_id:id,citation_index:0},citation:completion.source_citations[0]!,content:world});
});
it('renders each statement once and numbers all source families in reply order without passive reads',async()=>{
 const {props}=fixture();render(<SourceCitedAnswer {...props}/>);
 const buttons=screen.getAllByRole('button');expect(buttons.map(b=>b.textContent)).toEqual(['1','2','3']);
 for(const segment of props.completion.answer_segments)expect(document.querySelector('.world-plan-agent-answer')!.textContent!.split(segment.text)).toHaveLength(2);
 fireEvent.mouseEnter(buttons[0]!);fireEvent.focus(buttons[0]!);expect(getAgentSavedSection).not.toHaveBeenCalled();expect(getAgentRelatedPage).not.toHaveBeenCalled();expect(getAgentSourcePassage).not.toHaveBeenCalled();
 expect(buttons[0]).toHaveAttribute('title','Current page · saved revision 2 · lines 1–1');
 fireEvent.click(buttons[0]!);await screen.findByText('orchids');expect(getAgentSavedSection).toHaveBeenCalledTimes(1);
 fireEvent.click(screen.getByRole('button',{name:'Read Workshop · saved revision 3'}));await screen.findByText(related);expect(screen.queryByText('orchids')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Read World record · lines 1–1'}));await screen.findByText(world);expect(screen.queryByText(related)).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Close passage'}));expect(screen.queryByLabelText('Opened source passage')).toBeNull();
});
it.each(['saved','related','passage'])('refuses changed %s bytes without newer-source replacement',async(kind)=>{
 if(kind==='saved')vi.mocked(getAgentSavedSection).mockImplementation(async target=>({schema:'dmb_saved_build_section_read_v1',target,content:'changed'}));
 if(kind==='related')vi.mocked(getAgentRelatedPage).mockImplementation(async()=>{throw new Error('unavailable')});
 if(kind==='passage')vi.mocked(getAgentSourcePassage).mockImplementation(async()=>{throw new Error('unavailable')});
 render(<SourceCitedAnswer {...fixture().props}/>);
 fireEvent.click(screen.getAllByRole('button')[kind==='saved'?0:kind==='related'?1:2]!);
 await screen.findByText(/No newer text has been substituted/);
 expect(screen.queryByText('changed')).toBeNull();
});
it('retires late reads across a World and turn round trip',async()=>{
 const result=await vi.mocked(getAgentRelatedPage)('world',id,read);vi.mocked(getAgentRelatedPage).mockClear();
 let resolve!:(value:typeof result)=>void;vi.mocked(getAgentRelatedPage).mockImplementation(()=>new Promise(r=>{resolve=r}));
 const {props}=fixture(),view=render(<SourceCitedAnswer {...props}/>);fireEvent.click(screen.getByRole('button',{name:'Read Workshop · saved revision 3'}));
 await waitFor(()=>expect(getAgentRelatedPage).toHaveBeenCalledTimes(1));view.rerender(<SourceCitedAnswer {...props} worldId='other' turnId={read}/>);view.rerender(<SourceCitedAnswer {...props}/>);
 await act(async()=>resolve(result));expect(screen.queryByText(related)).toBeNull();expect(screen.queryByLabelText('Opened source section')).toBeNull();
});
it('preserves an unaligned historical reply and exposes sources without false inline placement',()=>{
 const {props}=fixture();render(<SourceCitedAnswer {...props} answer='A differently formatted retained reply.'/>);
 expect(screen.getByText('A differently formatted retained reply.')).toBeInTheDocument();expect(screen.getByLabelText('Sources for this reply').querySelectorAll('button')).toHaveLength(3);
 expect(screen.queryByText(props.completion.answer_segments[0]!.text)).toBeNull();
});
