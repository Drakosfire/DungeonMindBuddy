import { act, renderHook, waitFor } from '@testing-library/react';
import type { Editor, JSONContent } from '@tiptap/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { commitTiptapMarkdownWrite, getWorkspaceDocumentSnapshot, prepareTiptapMarkdownWrite } from '../api/liveApi';
import type { WorkspaceDocumentSnapshot } from '../api/types';
import { fixtureWorkspaceDocumentRecord } from '../planSurface/config/planSessionDescriptor';
import { markdownToTiptapDoc } from '../tiptap/markdown/markdownToTiptap';
import { projectPresentation, presentationFingerprint } from '../tiptap/pageComposer/presentation';
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

});
