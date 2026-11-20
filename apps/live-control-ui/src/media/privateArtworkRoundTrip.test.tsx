import { createHash } from 'node:crypto';
import { Editor } from '@tiptap/core';
import { act, cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import * as api from '../api/liveApi';
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from '../tiptap/MarkdownEditorCore';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { markdownToTiptapDoc } from '../tiptap/markdown/markdownToTiptap';
import { createDocumentMediaBridge } from './documentMediaBridge';
import { DocumentImageStudio } from './DocumentImageStudio';
import { SavedMediaImage } from './SavedMediaImage';
const wizard=vi.hoisted(()=>({props:null as any}));
vi.mock('./DeferredMediaImageWizard',()=>({DeferredMediaImageWizard:(props:any)=>{wizard.props=props;return null;}}));
vi.mock('../guidedTour/ImageObservations',()=>({useTourImage:()=>null}));
const id='ac6c15cc-8c68-4732-8ae2-d9f3f051393a';
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals();});
it('inserts through the real document writer and reloads only the UUID as private artwork',async()=>{
 const original=Uint8Array.from(atob('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='),value=>value.charCodeAt(0));
 const metadata={asset_id:id,state:'staged',mime_type:'image/png',byte_length:original.length,content_sha256:createHash('sha256').update(original).digest('hex')};
 const fetcher=vi.spyOn(api,'authenticatedApiFetch').mockImplementation(async path=>{
  if(path!==`/api/live/media/images/${id}/metadata`&&path!==`/api/live/media/images/${id}/original`)throw new Error(`Unexpected media read: ${path}`);
  return {response:path.endsWith('/metadata')?Response.json(metadata):new Response(original,{headers:{'content-type':metadata.mime_type,'x-media-content-sha256':metadata.content_sha256}}),csrf:null,requestEpoch:api.getNativeGraphAccessGeneration()};
 });
 vi.stubGlobal('URL',class extends URL {
  static createObjectURL=vi.fn((_value:Blob|MediaSource)=>'blob:private-roundtrip');
  static revokeObjectURL=vi.fn();
 });
 const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:'<p>Before</p><p>After</p>'});
 const bridge=createDocumentMediaBridge(()=>({editor,identity:'world:plan',version:'saved:22:draft:0',canEdit:true}));
 vi.spyOn(editor.view,'posAtCoords').mockReturnValue({pos:9,inside:8});
 const studio=render(<DocumentImageStudio bridge={bridge} targetLabel="Plan" onClose={()=>{}}/>);
 try {
  const pending=wizard.props.onChoose(metadata,{}, {signal:new AbortController().signal,mode:'click'});
  await act(async()=>{editor.view.dom.dispatchEvent(new MouseEvent('pointerup',{bubbles:true,cancelable:true,clientX:10,clientY:10}));await pending;});
  const saved=tiptapJsonToSemanticMarkdown(editor.getJSON());
  expect(saved).toContain(`dmb-media:${id}`);
  expect(saved).not.toMatch(/data:|blob:|https:/);
  const reloaded=markdownToTiptapDoc(saved).doc;
  expect(JSON.stringify(reloaded)).toContain(id);
  expect(tiptapJsonToSemanticMarkdown(reloaded)).toBe(saved);
  expect(fetcher.mock.calls.map(([path])=>path)).toEqual([`/api/live/media/images/${id}/metadata`]);
  expect(URL.createObjectURL).not.toHaveBeenCalled();
  studio.unmount();const image=render(<SavedMediaImage assetId={id} alt="Saved artwork"/>);
  expect(await screen.findByRole('img',{name:'Saved artwork'})).toHaveAttribute('src','blob:private-roundtrip');
  expect(fetcher.mock.calls.map(([path])=>path)).toEqual([`/api/live/media/images/${id}/metadata`,`/api/live/media/images/${id}/metadata`,`/api/live/media/images/${id}/original`]);
  expect(fetcher.mock.calls.every(([,init])=>!init?.method&&init?.cache==='no-store'&&init.signal instanceof AbortSignal)).toBe(true);
  expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
  const blob=vi.mocked(URL.createObjectURL).mock.calls[0][0] as Blob;
  expect(blob.type).toBe(metadata.mime_type);expect(blob.size).toBe(original.length);
  expect(new Uint8Array(await blob.arrayBuffer())).toEqual(original);
  image.unmount();expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:private-roundtrip');
 } finally {editor.destroy();}
});
