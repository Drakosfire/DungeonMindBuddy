import { act, renderHook, waitFor } from '@testing-library/react';
import type { Editor, JSONContent } from '@tiptap/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { commitTiptapMarkdownWrite, getWorkspaceDocumentSnapshot, prepareTiptapMarkdownWrite } from '../api/liveApi';
import type { WorkspaceDocumentSnapshot } from '../api/types';
import { fixtureWorkspaceDocumentRecord } from '../planSurface/config/planSessionDescriptor';
import { markdownToTiptapDoc } from '../tiptap/markdown/markdownToTiptap';
import { admittedPresentationBlocks, hydratePresentation, projectPresentation, presentationFingerprint, presentationSha256, type PagePresentation } from '../tiptap/pageComposer/presentation';
import { readWorkspaceDocumentLocalState } from '../tiptap/state/tiptapLocalState';
import { useWorkspaceDocumentAuthoring } from './useWorkspaceDocumentAuthoring';
vi.mock('../api/liveApi', () => ({
 NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT:'dmb:native-graph-access-token-changed', getNativeGraphAccessGeneration:vi.fn(()=>0),
 getWorkspaceDocumentSnapshot:vi.fn(), prepareTiptapMarkdownWrite:vi.fn(), commitTiptapMarkdownWrite:vi.fn(),
}));
const id='11111111-1111-4111-8111-111111111111';
const source='Café 🌲\n\nSecond paragraph.\n';
const plain=markdownToTiptapDoc(source).doc;
function composed(width=6):JSONContent {return {type:'doc',content:[{type:'pageRow',attrs:{id:'row-1',min_height:0,line_mode:'guide'},content:[{type:'pageSlot',attrs:{id:'left',width},content:[plain.content![0]]},{type:'pageSlot',attrs:{id:'right',width:12-width},content:[plain.content![1]]}]}]};}
function snap(width=6,revision=1):WorkspaceDocumentSnapshot {
 const layout=projectPresentation(composed(width),source,plain).presentation;
 return {schema_version:'dmb_workspace_document_snapshot_v1',record:fixtureWorkspaceDocumentRecord({document_id:id,kind:'worldbuilding_source',campaign_id:null,world_id:'smoke',revision,content_status:'committed'}),markdown:source,content_sha256:'same-source',file_fingerprint:'postgres',file_exists:false,loaded_revision:revision,page_presentation:layout,page_presentation_sha256:presentationFingerprint(layout)};
}
function mount(){return renderHook(()=>useWorkspaceDocumentAuthoring({documentId:id,kind:'worldbuilding_source',surface:'build'}));}
beforeEach(()=>{vi.clearAllMocks();localStorage.clear();});
describe('Page layout authoring boundary',()=>{
 it('does not enroll a legacy plain page during ordinary Save',async()=>{
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue({...snap(),page_presentation:null,page_presentation_sha256:null});
  vi.mocked(prepareTiptapMarkdownWrite).mockResolvedValue({writer_ok:false,warnings:[],diagnostics:[]} as never);
  const h=mount();await waitFor(()=>expect(h.result.current.phase).toBe('ready_clean'));
  const edited=structuredClone(plain);edited.content![0].content=[{type:'text',text:'Ordinary edit.'}];
  const editor={getJSON:()=>edited} as Editor;
  act(()=>{h.result.current.setEditor(editor);h.result.current.handleEditorUpdate(edited,editor,{programmatic:false});});
  await waitFor(()=>expect(h.result.current.saveDisabled).toBe(false));await act(()=>h.result.current.saveMarkdown());
  expect(prepareTiptapMarkdownWrite).toHaveBeenCalled();
  expect(vi.mocked(prepareTiptapMarkdownWrite).mock.calls[0][0].page_presentation ?? null).toBeNull();
  h.unmount();
 });
 it('retains existing plain identities through draft reopen, both Save phases and a fresh server reopen',async()=>{
  const layout:PagePresentation={schema_version:'dmb_page_presentation_v1',markdown_sha256:presentationSha256(source),
   items:admittedPresentationBlocks(source).map((b,i)=>({kind:'block',id:`retained-${i}`,byte_start:b.byte_start,byte_end:b.byte_end,sha256:b.sha256}))};
  const initial={...snap(),page_presentation:layout,page_presentation_sha256:presentationFingerprint(layout)};
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(initial);
  const h=mount();await waitFor(()=>expect(h.result.current.phase).toBe('ready_clean'));
  const original=hydratePresentation(source,layout),edited=structuredClone(original);
  edited.content![0].content=[{type:'text',text:'Updated paragraph.'}];
  act(()=>h.result.current.handleEditorUpdate(edited,{} as Editor,{programmatic:false}));
  await waitFor(()=>expect(h.result.current.dirty).toBe(true));
  const retained=readWorkspaceDocumentLocalState(localStorage,id)!;
  expect(retained.page_presentation!.items.map(item=>item.id)).toEqual(['retained-0','retained-1']);
  h.unmount();const r=mount();await waitFor(()=>expect(r.result.current.dirty).toBe(true));
  expect(r.result.current.editorContent).toEqual(edited);
  const saved={...initial,markdown:retained.exported_markdown,content_sha256:presentationSha256(retained.exported_markdown),
   loaded_revision:2,record:{...initial.record,revision:2},page_presentation:retained.page_presentation,
   page_presentation_sha256:presentationFingerprint(retained.page_presentation)};
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(saved);
  vi.mocked(prepareTiptapMarkdownWrite).mockResolvedValue({writer_ok:true,writer_confirm_token:'token'} as never);
  vi.mocked(commitTiptapMarkdownWrite).mockResolvedValue({document_id:id,committed_revision:2,committed_record:saved.record,
   normalized_content_sha256:saved.content_sha256,file_fingerprint:'postgres',writer_ok:true,page_presentation_sha256:saved.page_presentation_sha256} as never);
  act(()=>r.result.current.setEditor({getJSON:()=>edited} as Editor));
  await waitFor(()=>expect(r.result.current.saveDisabled).toBe(false));await act(()=>r.result.current.saveMarkdown());
  for(const write of [prepareTiptapMarkdownWrite,commitTiptapMarkdownWrite])
   expect(write).toHaveBeenCalledWith(expect.objectContaining({markdown:saved.markdown,page_presentation:saved.page_presentation}));
  await waitFor(()=>expect(r.result.current.dirty).toBe(false));r.unmount();localStorage.clear();
  const cold=mount();await waitFor(()=>expect(cold.result.current.phase).toBe('ready_clean'));
  expect(cold.result.current.editorContent).toEqual(edited);cold.unmount();
 });
 it('retains resize-only draft across unmount and reopens it dirty without changing source bytes',async()=>{
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snap());
  const h=mount();await waitFor(()=>expect(h.result.current.phase).toBe('ready_clean'));
  act(()=>h.result.current.handleEditorUpdate(composed(4),{} as Editor,{programmatic:false}));
  await waitFor(()=>expect(readWorkspaceDocumentLocalState(localStorage,id)?.dirty).toBe(true));
  expect(readWorkspaceDocumentLocalState(localStorage,id)?.exported_markdown).toBe(source);
  h.unmount();const r=mount();await waitFor(()=>expect(r.result.current.dirty).toBe(true));
  expect((r.result.current.editorContent as JSONContent).content![0].content![0].attrs!.width).toBe(4);
 });
 it('fails closed on stale server layout while retaining the browser copy',async()=>{
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snap());const h=mount();await waitFor(()=>expect(h.result.current.phase).toBe('ready_clean'));
  act(()=>h.result.current.handleEditorUpdate(composed(4),{} as Editor,{programmatic:false}));
  await waitFor(()=>expect(readWorkspaceDocumentLocalState(localStorage,id)?.dirty).toBe(true));h.unmount();
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snap(8,2));const r=mount();await waitFor(()=>expect(r.result.current.phase).toBe('conflict'));
  expect(readWorkspaceDocumentLocalState(localStorage,id)?.page_presentation).not.toEqual(snap(8,2).page_presentation);
 });
 it('sends layout and unchanged Markdown through both write phases and verifies the saved fingerprint',async()=>{
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValueOnce(snap()).mockResolvedValue(snap(4,2));
  vi.mocked(prepareTiptapMarkdownWrite).mockResolvedValue({writer_ok:true,writer_confirm_token:'token'} as never);
  const saved=snap(4,2);
  vi.mocked(commitTiptapMarkdownWrite).mockResolvedValue({document_id:id,committed_revision:2,committed_record:saved.record,normalized_content_sha256:'same-source',file_fingerprint:'postgres',writer_ok:true,page_presentation_sha256:saved.page_presentation_sha256} as never);
  const h=mount();await waitFor(()=>expect(h.result.current.phase).toBe('ready_clean'));
  const editor={getJSON:()=>composed(4)} as Editor;
  act(()=>{h.result.current.setEditor(editor);h.result.current.handleEditorUpdate(composed(4),editor,{programmatic:false});});
  await waitFor(()=>expect(h.result.current.saveDisabled).toBe(false));await act(()=>h.result.current.saveMarkdown());
  expect(prepareTiptapMarkdownWrite).toHaveBeenCalledWith(expect.objectContaining({markdown:source,page_presentation:expect.any(Object)}));
  expect(commitTiptapMarkdownWrite).toHaveBeenCalledWith(expect.objectContaining({markdown:source,page_presentation:expect.any(Object)}));
  await waitFor(()=>expect(h.result.current.dirty).toBe(false));
 });
 it('keeps a newer resize dirty when an earlier save completes',async()=>{
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValueOnce(snap()).mockResolvedValue(snap(4,2));
  let finish!: (v: never)=>void;
  vi.mocked(prepareTiptapMarkdownWrite).mockResolvedValue({writer_ok:true,writer_confirm_token:'token'} as never);
  vi.mocked(commitTiptapMarkdownWrite).mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
  const h=mount();await waitFor(()=>expect(h.result.current.phase).toBe('ready_clean'));
  let json=composed(4);const editor={getJSON:()=>json} as Editor;
  act(()=>{h.result.current.setEditor(editor);h.result.current.handleEditorUpdate(json,editor,{programmatic:false});});
  await waitFor(()=>expect(h.result.current.saveDisabled).toBe(false));let saving!:Promise<void>;
  act(()=>{saving=h.result.current.saveMarkdown();});await waitFor(()=>expect(commitTiptapMarkdownWrite).toHaveBeenCalled());
  json=composed(8);act(()=>h.result.current.handleEditorUpdate(json,editor,{programmatic:false}));
  const saved=snap(4,2);
  await act(async()=>{finish({document_id:id,committed_revision:2,committed_record:saved.record,normalized_content_sha256:'same-source',file_fingerprint:'postgres',writer_ok:true,page_presentation_sha256:saved.page_presentation_sha256} as never);await saving;});
  expect(h.result.current.dirty).toBe(true);
  const local=readWorkspaceDocumentLocalState(localStorage,id)!;
  expect(local.base_revision).toBe(2);expect(local.base_page_presentation_sha256).toBe(saved.page_presentation_sha256);
  expect(local.page_presentation).toEqual(snap(8).page_presentation);
 });
 it('sends explicit null only on intentional unwrap',async()=>{
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snap());
  vi.mocked(prepareTiptapMarkdownWrite).mockResolvedValue({writer_ok:false,warnings:[],diagnostics:[]} as never);
  const h=mount();await waitFor(()=>expect(h.result.current.phase).toBe('ready_clean'));
  const editor={getJSON:()=>plain} as Editor;
  act(()=>{h.result.current.setEditor(editor);h.result.current.handleEditorUpdate(plain,editor,{programmatic:false});});
  await waitFor(()=>expect(h.result.current.saveDisabled).toBe(false));await act(()=>h.result.current.saveMarkdown());
  expect(prepareTiptapMarkdownWrite).toHaveBeenCalledWith(expect.objectContaining({markdown:source,page_presentation:null}));
 });

 it('preserves unsupported dirty composed editor JSON on cold reopen instead of hydrating stale layout over it',async()=>{
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snap());const h=mount();await waitFor(()=>expect(h.result.current.phase).toBe('ready_clean'));
  const broken=composed(4);broken.content![0].content![0].content!.push({type:'unknownUnsupported',attrs:{precious:'unsaved'}});
  act(()=>h.result.current.handleEditorUpdate(broken,{} as Editor,{programmatic:false}));
  await waitFor(()=>expect(readWorkspaceDocumentLocalState(localStorage,id)?.exported_markdown_authoritative).toBe(true));h.unmount();
  const r=mount();await waitFor(()=>expect(r.result.current.dirty).toBe(true));
  expect(r.result.current.editorContent).toEqual(broken);expect(r.result.current.saveDisabled).toBe(true);
  expect(readWorkspaceDocumentLocalState(localStorage,id)?.tiptap_json).toEqual(broken);
 });

 it('protected source recovery restores the preserved composition and keeps the unsupported original copy',async()=>{
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snap());const h=mount();await waitFor(()=>expect(h.result.current.phase).toBe('ready_clean'));
  const broken=composed(4);broken.content![0].content![0].content!.push({type:'unknownUnsupported',attrs:{precious:'unsaved'}});
  const editor={getJSON:()=>broken,getText:()=>"Protected unsaved content"} as Editor;
  act(()=>{h.result.current.setEditor(editor);h.result.current.handleEditorUpdate(broken,editor,{programmatic:false});});
  await waitFor(()=>expect(readWorkspaceDocumentLocalState(localStorage,id)?.exported_markdown_authoritative).toBe(true));
  await waitFor(()=>expect(h.result.current.statusLabel).not.toBe('Saving local copy…'));
  const review=h.result.current.prepareDraftRecovery();await act(()=>h.result.current.confirmDraftRecovery(review,'source'));
  const restored=readWorkspaceDocumentLocalState(localStorage,id)!;
  expect(restored.exported_markdown).toBe(source);expect(restored.page_presentation).toEqual(snap().page_presentation);
  expect((restored.tiptap_json as JSONContent).content![0].type).toBe('pageRow');expect(restored.dirty).toBe(false);
  expect(localStorage.getItem(`dmb.workspaceDocument.${id}.recovery.v2`)).toContain('precious');
 });

 it('retains an unfinished new paragraph through reload and resumes saving when typed',async()=>{
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snap());const h=mount();await waitFor(()=>expect(h.result.current.phase).toBe('ready_clean'));
  const unfinished=composed(6);unfinished.content![0].content![0].content!.push({type:'paragraph'});
  act(()=>h.result.current.handleEditorUpdate(unfinished,{} as Editor,{programmatic:false}));
  await waitFor(()=>expect(readWorkspaceDocumentLocalState(localStorage,id)?.page_presentation_pending).toBe(true));
  expect(h.result.current.exportedMarkdownAuthoritative).toBe(false);h.unmount();
  const r=mount();await waitFor(()=>expect(r.result.current.dirty).toBe(true));expect(r.result.current.editorContent).toEqual(unfinished);
  const finished=structuredClone(unfinished);finished.content![0].content![0].content![1].content=[{type:'text',text:'New text'}];
  act(()=>r.result.current.handleEditorUpdate(finished,{} as Editor,{programmatic:false}));
  await waitFor(()=>expect(readWorkspaceDocumentLocalState(localStorage,id)?.page_presentation_pending).toBe(false));
  expect(r.result.current.exportedMarkdownAuthoritative).toBe(false);expect(readWorkspaceDocumentLocalState(localStorage,id)?.exported_markdown).toContain('New text');
 });

 it('anchors pending completion to last valid Markdown, not a newer lossy projection',async()=>{
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snap());const h=mount();await waitFor(()=>expect(h.result.current.phase).toBe('ready_clean'));
  const pending=composed(6);pending.content![0].content![0].content![0].content=[{type:'text',text:'NEW WORDS'}];pending.content![0].content![0].content!.push({type:'paragraph'});
  act(()=>h.result.current.handleEditorUpdate(pending,{} as Editor,{programmatic:false}));
  await waitFor(()=>expect(readWorkspaceDocumentLocalState(localStorage,id)?.page_presentation_pending).toBe(true));
  const completed=structuredClone(pending);completed.content![0].content![0].content!.pop();
  act(()=>h.result.current.handleEditorUpdate(completed,{} as Editor,{programmatic:false}));
  await waitFor(()=>expect(readWorkspaceDocumentLocalState(localStorage,id)?.page_presentation_pending).toBe(false));
  expect(readWorkspaceDocumentLocalState(localStorage,id)?.exported_markdown).toContain('NEW WORDS');h.unmount();
  const r=mount();await waitFor(()=>expect(r.result.current.dirty).toBe(true));expect(JSON.stringify(r.result.current.editorContent)).toContain('NEW WORDS');
 });

 it.each(['guide','border','clean'])('recovers three-slot %s height-only edits and saves unchanged source',async(lineMode)=>{
  const threeSource='Left table context.\n\nMiddle artwork context.\n\nRight table context.\n';
  const threePlain=markdownToTiptapDoc(threeSource).doc;
  const doc:JSONContent={type:'doc',content:[{type:'pageRow',attrs:{id:'three',min_height:0,line_mode:'guide'},content:threePlain.content!.map((block,i)=>({type:'pageSlot',attrs:{id:`slot-${i}`,width:4},content:[block]}))}]};
  const layout=projectPresentation(doc,threeSource,threePlain).presentation;
  const initial={...snap(),markdown:threeSource,page_presentation:layout,page_presentation_sha256:presentationFingerprint(layout)};
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(initial);
  const h=mount();await waitFor(()=>expect(h.result.current.phase).toBe('ready_clean'));
  const edited=structuredClone(doc);edited.content![0].attrs={...edited.content![0].attrs,min_height:256,line_mode:lineMode};
  act(()=>h.result.current.handleEditorUpdate(edited,{} as Editor,{programmatic:false}));
  await waitFor(()=>expect(readWorkspaceDocumentLocalState(localStorage,id)?.dirty).toBe(true));h.unmount();
  const r=mount();await waitFor(()=>expect(r.result.current.dirty).toBe(true));
  expect((r.result.current.editorContent as JSONContent).content![0].attrs).toEqual(expect.objectContaining({min_height:256,line_mode:lineMode}));
  expect(readWorkspaceDocumentLocalState(localStorage,id)?.exported_markdown).toBe(threeSource);
  const updatedLayout=projectPresentation(edited,threeSource,threePlain).presentation;
  const saved={...initial,loaded_revision:2,record:{...initial.record,revision:2},page_presentation:updatedLayout,page_presentation_sha256:presentationFingerprint(updatedLayout)};
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(saved);
  vi.mocked(prepareTiptapMarkdownWrite).mockResolvedValue({writer_ok:true,writer_confirm_token:'token'} as never);
  vi.mocked(commitTiptapMarkdownWrite).mockResolvedValue({document_id:id,committed_revision:2,committed_record:saved.record,normalized_content_sha256:'same-source',file_fingerprint:'postgres',writer_ok:true,page_presentation_sha256:saved.page_presentation_sha256} as never);
  act(()=>r.result.current.setEditor({getJSON:()=>edited} as Editor));await waitFor(()=>expect(r.result.current.saveDisabled).toBe(false));await act(()=>r.result.current.saveMarkdown());
  expect(commitTiptapMarkdownWrite).toHaveBeenCalledWith(expect.objectContaining({markdown:threeSource,page_presentation:updatedLayout}));
  await waitFor(()=>expect(r.result.current.dirty).toBe(false));
 });

 const stackSource='![Art](dmb-media:11111111-1111-4111-8111-111111111111)\n\n# Café title\n';
 const stackPlain=markdownToTiptapDoc(stackSource).doc;
 const stackDoc=(anchor='middle-center'):JSONContent=>({type:'doc',content:[{type:'pageImageText',attrs:{id:'stack',anchor,inset:'small',backing:'contrast'},content:stackPlain.content}]});
 const stackSnap=(anchor='middle-center',revision=1):WorkspaceDocumentSnapshot=>{
  const layout=projectPresentation(stackDoc(anchor),stackSource,stackPlain).presentation;
  return {...snap(6,revision),markdown:stackSource,page_presentation:layout,page_presentation_sha256:presentationFingerprint(layout)};
 };
 it('recovers anchor-only stack draft and saves the same source and new layout fingerprint',async()=>{
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(stackSnap());const h=mount();await waitFor(()=>expect(h.result.current.phase).toBe('ready_clean'));
  const doc=stackDoc('bottom-right');act(()=>h.result.current.handleEditorUpdate(doc,{} as Editor,{programmatic:false}));await waitFor(()=>expect(h.result.current.dirty).toBe(true));h.unmount();
  const r=mount();await waitFor(()=>expect(r.result.current.dirty).toBe(true));expect((r.result.current.editorContent as JSONContent).content![0].attrs!.anchor).toBe('bottom-right');expect(readWorkspaceDocumentLocalState(localStorage,id)?.exported_markdown).toBe(stackSource);
  const saved=stackSnap('bottom-right',2);vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(saved);vi.mocked(prepareTiptapMarkdownWrite).mockResolvedValue({writer_ok:true,writer_confirm_token:'token'} as never);vi.mocked(commitTiptapMarkdownWrite).mockResolvedValue({document_id:id,committed_revision:2,committed_record:saved.record,normalized_content_sha256:'same-source',file_fingerprint:'postgres',writer_ok:true,page_presentation_sha256:saved.page_presentation_sha256} as never);
  act(()=>r.result.current.setEditor({getJSON:()=>doc} as Editor));await waitFor(()=>expect(r.result.current.saveDisabled).toBe(false));await act(()=>r.result.current.saveMarkdown());expect(commitTiptapMarkdownWrite).toHaveBeenCalledWith(expect.objectContaining({markdown:stackSource,page_presentation:saved.page_presentation}));await waitFor(()=>expect(r.result.current.dirty).toBe(false));
 });
 it('retains an empty live stack title across cold draft reopen and resumes on completion',async()=>{
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(stackSnap());const h=mount();await waitFor(()=>expect(h.result.current.phase).toBe('ready_clean'));
  const pending=stackDoc();pending.content![0].content=structuredClone(stackPlain.content);pending.content![0].content![1].content=[];
  act(()=>h.result.current.handleEditorUpdate(pending,{} as Editor,{programmatic:false}));await waitFor(()=>expect(readWorkspaceDocumentLocalState(localStorage,id)?.page_presentation_pending).toBe(true));h.unmount();
  const r=mount();await waitFor(()=>expect(r.result.current.dirty).toBe(true));expect(r.result.current.editorContent).toEqual(pending);
  const completed=structuredClone(pending);completed.content![0].content![1].content=[{type:'text',text:'New title'}];act(()=>r.result.current.handleEditorUpdate(completed,{} as Editor,{programmatic:false}));await waitFor(()=>expect(readWorkspaceDocumentLocalState(localStorage,id)?.page_presentation_pending).toBe(false));expect(readWorkspaceDocumentLocalState(localStorage,id)?.exported_markdown).toContain('New title');
 });
 it('retains anchor-only draft when the server stack revision has changed',async()=>{
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(stackSnap());const h=mount();await waitFor(()=>expect(h.result.current.phase).toBe('ready_clean'));act(()=>h.result.current.handleEditorUpdate(stackDoc('bottom-right'),{} as Editor,{programmatic:false}));await waitFor(()=>expect(h.result.current.dirty).toBe(true));h.unmount();
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(stackSnap('top-left',2));const r=mount();await waitFor(()=>expect(r.result.current.phase).toBe('conflict'));expect(JSON.stringify(readWorkspaceDocumentLocalState(localStorage,id)?.tiptap_json)).toContain('bottom-right');
 });

});
