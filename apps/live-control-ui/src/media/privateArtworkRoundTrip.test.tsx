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
vi.mock('./MediaImageWizard',()=>({MediaImageWizard:(props:any)=>{wizard.props=props;return null;}}));
vi.mock('../guidedTour/ImageObservations',()=>({useTourImage:()=>null}));
const id='ac6c15cc-8c68-4732-8ae2-d9f3f051393a';
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('inserts through the real document writer and reloads only the UUID as private artwork',async()=>{
 const metadata={asset_id:id,state:'staged',mime_type:'image/png',byte_length:1,content_sha256:'a'.repeat(64)};
 const fetcher=vi.spyOn(api,'authenticatedApiFetch').mockImplementation(async path=>({response:Response.json(path.endsWith('/metadata')?metadata:{...metadata,data_url:'data:image/png;base64,AA=='}),csrf:null,requestEpoch:api.getNativeGraphAccessGeneration()}));
 Object.defineProperty(URL,'createObjectURL',{configurable:true,value:vi.fn(()=>'blob:private-roundtrip')});
 Object.defineProperty(URL,'revokeObjectURL',{configurable:true,value:vi.fn()});
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
  studio.unmount();render(<SavedMediaImage assetId={id} alt="Saved artwork"/>);
  expect(await screen.findByRole('img',{name:'Saved artwork'})).toHaveAttribute('src','blob:private-roundtrip');
  expect(fetcher.mock.calls.every(([path,init])=>path.startsWith('/api/live/media/images/') && !init?.method)).toBe(true);
 } finally {editor.destroy();}
});
