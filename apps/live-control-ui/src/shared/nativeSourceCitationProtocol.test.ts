import {afterEach,beforeEach,it,expect,vi} from 'vitest';
import {createElement} from 'react';
import {render,screen,fireEvent,cleanup} from '@testing-library/react';
import {createHash,webcrypto} from 'node:crypto';
import type {SurfaceEvidenceCompletionV3} from '../api/types';
import {isSurfaceEvidenceCompletion} from './surfaceEvidenceProtocol';
import {SurfaceEvidenceAnswer} from '../planSurface/components/SurfaceEvidenceAnswer';
import {getAgentNativeSourceSection,getAgentNativeBodyExcerpt} from '../api/liveApi';
vi.mock('../api/liveApi',()=>({getAgentNativeSourceSection:vi.fn(),getAgentNativeBodyExcerpt:vi.fn()}));
const id='11111111-1111-4111-8111-111111111111',content='Tree mechanics.\r\n';
function completion(surface:'plan'|'play'='plan'):SurfaceEvidenceCompletionV3 {
 return {schema:'dmb_surface_evidence_completion_v3',surface_id:surface,context_receipt_sha256:'a'.repeat(64),
 answer_basis:'mixed_evidence',answer_context_status:'source_grounded',citation_map:null,source_citations:[],
 answer_segments:[{kind:'source_passage_claim',text:'The appendix describes a tree.'}],native_source_citations:[{
 segment_index:0,text_sha256:'b'.repeat(64),provider_attempt_id:id,envelope_sha256:'c'.repeat(64),read_event_id:id,
 catalog_event_id:id,source_artifact_id:'source:synthetic',native_source_revision_id:'native:old',app_source_revision_id:id,
 content_sha256:'d'.repeat(64),excerpt_sha256:createHash('sha256').update(content).digest('hex'),section_id:'e'.repeat(64),
 selector_policy:'markdown_sections_v1',source_name:'Synthetic adventure',section_title:'Appendix A',line_start:3,line_end:4}]};
}
beforeEach(()=>{vi.stubGlobal('crypto',webcrypto);vi.mocked(getAgentNativeSourceSection).mockReset();});
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it.each(['plan','play'] as const)('admits named sections in %s',surface=>{
 expect(isSurfaceEvidenceCompletion(completion(surface),'a'.repeat(64),surface)).toBe(true);
});
it.each(['uncited','extra','name','range','duplicate','graph','old'])('rejects altered %s',change=>{
 const c=completion();
 if(change==='uncited')c.native_source_citations=[];
 if(change==='extra')Object.assign(c.native_source_citations[0]!,{anchor_id:'fake'});
 if(change==='name')c.native_source_citations[0]!.source_name=' ';
 if(change==='range')c.native_source_citations[0]!.line_end=1;
 if(change==='duplicate')c.native_source_citations.push(c.native_source_citations[0]!);
 if(change==='graph')Object.assign(c.answer_segments[0]!,{kind:'graph_claim'});
 if(change==='old')Object.assign(c,{schema:'dmb_surface_evidence_completion_v2'});
 expect(isSurfaceEvidenceCompletion(c,'a'.repeat(64),'plan')).toBe(false);
});
it.each(['exact','hash','name','world'])('opens only exact source bytes: %s',async change=>{
 const c=completion(),citation={...c.native_source_citations[0]!};
 if(change==='name')citation.source_name='Different';
 vi.mocked(getAgentNativeSourceSection).mockResolvedValue({schema:'dmb_agent_native_source_section_read_v1',
 world_id:change==='world'?'foreign':'world',turn_id:id,citation_index:0,citation,content:change==='hash'?'Changed bytes.':content});
 render(createElement(SurfaceEvidenceAnswer,{completion:c,worldId:'world',turnId:id}));
 fireEvent.click(screen.getByRole('button',{name:'Synthetic adventure · Appendix A'}));
 if(change==='exact')await screen.findByText('Tree mechanics.');
 else await screen.findByText(/exact cited section is unavailable/);
 expect(getAgentNativeSourceSection).toHaveBeenCalledWith('world',id,0);
 expect(screen.queryByText('Changed bytes.')).toBeNull();
});

function bodyCompletion():import('../api/types').SurfaceEvidenceCompletionV5 {
 const old=completion();
 const {catalog_event_id,app_source_revision_id,...citation}=old.native_source_citations[0]!;
 return {...old,schema:'dmb_surface_evidence_completion_v5',surface_id:'plan',native_source_citations:[],
   native_body_citations:[{...citation,catalog_sha256:'f'.repeat(64),selector_policy:'native_full_document_v1'}]};
}
it('admits the native body family only in Plan, without APP revision aliases',()=>{
 const c=bodyCompletion();expect(isSurfaceEvidenceCompletion(c,'a'.repeat(64),'plan')).toBe(true);
 expect(isSurfaceEvidenceCompletion({...c,surface_id:'play'},'a'.repeat(64),'play')).toBe(false);
 Object.assign(c.native_body_citations[0]!,{app_source_revision_id:id});
 expect(isSurfaceEvidenceCompletion(c,'a'.repeat(64),'plan')).toBe(false);
});
it.each(['exact','hash','citation','world','turn','index','family'])('native body citation uses the exact historical reader: %s',async change=>{
 const c=bodyCompletion(),citation={...c.native_body_citations[0]!};
 if(change==='citation')citation.native_source_revision_id='other';
 vi.mocked(getAgentNativeBodyExcerpt).mockResolvedValue({schema:change==='family'?'dmb_agent_native_source_section_read_v1':'dmb_agent_native_body_excerpt_read_v1',
   world_id:change==='world'?'foreign':'world',turn_id:change==='turn'?'other':id,citation_index:change==='index'?1:0,
   citation,content:change==='hash'?'Changed bytes.':content} as any);
 render(createElement(SurfaceEvidenceAnswer,{completion:c,worldId:'world',turnId:id}));
 fireEvent.click(screen.getByRole('button',{name:'Synthetic adventure · Appendix A'}));
 if(change==='exact')await screen.findByText('Tree mechanics.');
 else await screen.findByText(/exact cited section is unavailable/);
 expect(getAgentNativeBodyExcerpt).toHaveBeenLastCalledWith('world',id,0);
 expect(getAgentNativeSourceSection).not.toHaveBeenCalled();
 expect(screen.queryByText('Changed bytes.')).toBeNull();
});
