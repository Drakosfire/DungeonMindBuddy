import {Editor} from '@tiptap/core';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../tiptap/MarkdownEditorCore';
import {markdownToTiptapDoc} from '../tiptap/markdown/markdownToTiptap';
import {tiptapJsonToSemanticMarkdown} from '../tiptap/markdown/calloutMarkdown';
import {semanticMarkdownSerializationDiagnostics} from '../tiptap/markdown/semanticMarkdownSafety';
import {SurfaceProposalReview} from '../surface/SurfacePageProposal';
import {render,screen,cleanup} from '@testing-library/react';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import {webcrypto,createHash} from 'node:crypto';
import type {SessionSummarySegment,SessionSummarySupport,SurfaceEvidenceCompletionV4} from '../api/types';
import type {SessionEvidence} from '../playSurface/review/sessionEvidenceApi';
import {readSessionEvidence} from '../playSurface/review/sessionEvidenceApi';
import {SessionEvidenceViewer} from '../playSurface/review/SessionEvidenceViewer';
import {SurfaceEvidenceAnswer} from '../planSurface/components/SurfaceEvidenceAnswer';
import {canonical} from './sourcePassageProtocol';
import {isSurfaceEvidenceCompletion} from './surfaceEvidenceProtocol';
import {sessionCitationTarget,sessionSummaryMarkdown,verifiedSessionEntryTargets} from './sessionEvidenceCitation';
vi.mock('../playSurface/review/sessionEvidenceApi',()=>({readSessionEvidence:vi.fn()}));
const sha=(text:string)=>createHash('sha256').update(text).digest('hex');
function fixture(){
 const body={schema_version:'dmb_session_evidence_v1' as const,world_id:'park / &',run_id:'11111111-1111-4111-8111-111111111111',
  review_revision:54,ended_at:'2026-10-19T00:00:00Z',checkpoint_run_revision:8,session_content_sha256:'c'.repeat(64),
  title:'Gate rehearsal',citation_url:'/play?world=park',sources:[
   {kind:'scene_note' as const,element_id:'scene:gate',text:'Technical rehearsal: the gate stayed closed. 🐸\r\n',citation_url:'/play'},
   {kind:'closing_reflections' as const,text:'Ask about the next route; no fight occurred.',citation_url:'/play'}]
   .map(source=>({...source,sha256:sha(source.text)}))};
 const packet:SessionEvidence={...body,sha256:sha(canonical(body))};
 const supports:SessionSummarySupport[]=packet.sources.map((source,ordinal)=>{
  const entry=sha(canonical({kind:source.kind,element_id:source.element_id??null,ordinal}));
  const sourceHandle='q'+sha(canonical({source_kind:'session',object_id:packet.run_id,revision:'54',body_sha256:source.sha256,owner_sha256:packet.sha256,entry_identity:entry}));
  const block={partition_version:'markdown_source_blocks_v1' as const,source_handle:sourceHandle,byte_start:0,
   byte_end:new TextEncoder().encode(source.text).length,block_sha256:source.sha256};
  return {kind:'authored_excerpt',text:source.text,source_kind:'session',source_name:'Gate rehearsal — notes and reflections',
   object_id:packet.run_id,revision:'54',body_sha256:source.sha256,owner_sha256:packet.sha256,entry_identity:entry,
   ...block,block_handle:'b'+sha(canonical(block)),source_ordinal:ordinal,entry_kind:source.kind,
   element_id:source.element_id??null,checkpoint_content_sha256:packet.session_content_sha256};
 });
 const summary:SessionSummarySegment={kind:'session_summary',text:'The rehearsal left the route unresolved.',supports};
 const completion:SurfaceEvidenceCompletionV4={schema:'dmb_surface_evidence_completion_v4',surface_id:'plan',context_receipt_sha256:'a'.repeat(64),
  answer_basis:'mixed_evidence',answer_context_status:'authored_grounded',answer_segments:[summary],citation_map:null,source_citations:[],native_source_citations:[]};
 return {packet,summary,completion};
}
beforeEach(()=>{vi.stubGlobal('crypto',webcrypto);vi.resetAllMocks();window.history.replaceState({},'','/play')});
afterEach(()=>{cleanup();vi.unstubAllGlobals();window.history.replaceState({},'','/play')});
it('derives compact separately inspectable references from exact pinned source entries',async()=>{
 const {packet,summary}=fixture();const targets=await verifiedSessionEntryTargets(packet);
 expect(targets).toEqual(summary.supports.map(s=>sessionCitationTarget(packet.world_id,s)));
 expect(targets[0]).not.toBe(targets[1]);
 const projection=sessionSummaryMarkdown(summary,packet.world_id,1);
 expect(projection.nextNumber).toBe(3);expect(projection.text).toContain('[1](/play?');expect(projection.text).toContain('[2](/play?');
 expect(projection.text).not.toContain(packet.sources[0]!.text);
 expect(sessionSummaryMarkdown({...summary,supports:[...summary.supports,summary.supports[0]!]},packet.world_id,1).targets).toHaveLength(2);
});
it.each(['body','kind','ordinal','owner','checkpoint'])('refuses a changed %s in the saved source',async change=>{
 const {packet}=fixture();
 if(change==='body')packet.sources[0]!.text+=' altered';
 if(change==='kind')packet.sources[0]!.kind='closing_reflections';
 if(change==='ordinal')packet.sources.reverse();
 if(change==='owner')packet.sha256='f'.repeat(64);
 if(change==='checkpoint')packet.session_content_sha256='e'.repeat(64);
 await expect(verifiedSessionEntryTargets(packet)).rejects.toThrow(/digest/);
});
it('renders synthesis with numbered links and source titles, without blockquoting it',()=>{
 const {completion,packet}=fixture();render(<SurfaceEvidenceAnswer completion={completion} worldId={packet.world_id}/>);
 expect(screen.getByLabelText('Saved session summary').textContent).toContain('route unresolved');
 expect(screen.getByRole('link',{name:'1'})).toHaveAttribute('title','Gate rehearsal — notes and reflections · Scene notes');
 expect(screen.getByRole('link',{name:'2'})).toHaveAttribute('title','Gate rehearsal — notes and reflections · Closing reflections');
 expect(document.querySelector('blockquote')).toBeNull();
});
it('validates the closed shape and rejects forged nested metadata',()=>{
 const {completion}=fixture();expect(isSurfaceEvidenceCompletion(completion,'a'.repeat(64),'plan')).toBe(true);
 const bad=structuredClone(completion),summary=bad.answer_segments[0]!;if(summary.kind!=='session_summary')throw Error('fixture');
 summary.supports[0]!.source_ordinal=-1;
 expect(isSurfaceEvidenceCompletion(bad,'a'.repeat(64),'plan')).toBe(false);
 expect(isSurfaceEvidenceCompletion(completion,'a'.repeat(64),'play')).toBe(false);
 expect(isSurfaceEvidenceCompletion({...completion,surface_id:'play'},'a'.repeat(64),'play')).toBe(true);
});
it('opens the immutable selected source with no editing controls',async()=>{
 const {packet,summary}=fixture();const target=sessionCitationTarget(packet.world_id,summary.supports[1]!);
 window.history.replaceState({},'',target);vi.mocked(readSessionEvidence).mockResolvedValue(packet);
 render(<SessionEvidenceViewer worldId={packet.world_id} runId={packet.run_id} revision={54}/>);
 expect(await screen.findByRole('region',{name:'Closing reflections'})).toHaveAttribute('id',target.split('#')[1]);
 expect(screen.queryByRole('textbox')).toBeNull();expect(screen.queryByRole('button',{name:/save/i})).toBeNull();
});
it('refuses a changed fragment rather than opening its neighboring source',async()=>{
 const {packet,summary}=fixture();const target=sessionCitationTarget(packet.world_id,summary.supports[0]!);
 window.history.replaceState({},'',target.replace('source-0-','source-1-'));
 vi.mocked(readSessionEvidence).mockResolvedValue(packet);
 render(<SessionEvidenceViewer worldId={packet.world_id} runId={packet.run_id} revision={54}/>);
 expect(await screen.findByRole('alert')).toHaveTextContent('No neighboring entry has been substituted');
 expect(screen.queryByText(packet.sources[0]!.text)).toBeNull();
});

it('preserves actual host-projected citations through the default editor, editing, Save/reload and activation',()=>{
 const {summary,packet}=fixture();
 summary.supports[0]!.source_name='Gate "rehearsal" \\ notes';
 const projection=sessionSummaryMarkdown(summary,packet.world_id,1);
 const source='Before — preserve.\n\n'+projection.text+'\n\nAfter — preserve.';
 const imported=markdownToTiptapDoc(source);expect(imported.diagnostics).toEqual([]);
 const element=document.createElement('div');document.body.append(element);
 const editor=new Editor({element,extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:imported.doc});
 const before=editor.getJSON().content!;const open=vi.spyOn(window,'open').mockReturnValue(null);
 try {
  const middle=editor.state.doc.child(0).nodeSize+1;
  editor.commands.insertContentAt(middle,'Author reminder: ');
  expect(editor.getJSON().content![0]).toEqual(before[0]);
  expect(editor.getJSON().content!.at(-1)).toEqual(before.at(-1));
  expect(semanticMarkdownSerializationDiagnostics(editor.getJSON())).toEqual([]);
  const saved=tiptapJsonToSemanticMarkdown(editor.getJSON());
  const reloaded=markdownToTiptapDoc(saved);expect(reloaded.diagnostics).toEqual([]);
  const reopened=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:reloaded.doc});
  try {
   expect(tiptapJsonToSemanticMarkdown(reopened.getJSON())).toBe(saved);
   const links=Array.from(reopened.view.dom.querySelectorAll('a'));
   expect(links.map(a=>a.getAttribute('href'))).toEqual(projection.targets);
   expect(links[0]!.getAttribute('title')).toBe(summary.supports[0]!.source_name+' · Scene notes');
   expect(links[1]!.getAttribute('title')).toBe(summary.supports[1]!.source_name+' · Closing reflections');
   const original=reopened.getJSON();
   links[1]!.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));
   expect(open).toHaveBeenCalledExactlyOnceWith(projection.targets[1],'_blank','noopener,noreferrer');
   expect(reopened.getJSON()).toEqual(original);
   const htmlReload=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:reopened.getHTML()});
   try {
    expect(Array.from(htmlReload.view.dom.querySelectorAll('a')).map(a=>[a.getAttribute('href'),a.getAttribute('title')]))
     .toEqual(links.map(a=>[a.getAttribute('href'),a.getAttribute('title')]));
   } finally {htmlReload.destroy();}
  } finally {reopened.destroy();}
  let savedReview='';
  render(<SurfaceProposalReview markdown={saved} onChange={()=>{}} busy={false} error={null} onSave={()=>{savedReview=saved}} onDiscard={()=>{}}/>);
  expect(screen.getByRole('textbox',{name:'Suggestion text'}).querySelectorAll('a')).toHaveLength(2);
  screen.getByRole('button',{name:'Save',exact:true}).click();expect(savedReview).toBe(saved);
 } finally {editor.destroy();element.remove();open.mockRestore();}
});
