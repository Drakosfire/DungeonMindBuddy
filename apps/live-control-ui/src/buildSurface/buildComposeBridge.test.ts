import { Editor } from '@tiptap/core';
import { webcrypto } from 'node:crypto';
import { describe,it,expect,vi } from 'vitest';
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from '../tiptap/MarkdownEditorCore';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { createBuildComposeBridge,type BuildComposeEditorState } from './buildComposeBridge';
import { mediaMarkdown } from '../media/mediaReferences';
vi.stubGlobal('crypto',webcrypto);
const id='ac6c15cc-8c68-4732-8ae2-d9f3f051393a';
function setup(){
 const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:'<p>Edge</p>'});
 const state:BuildComposeEditorState={editor,worldId:'elderwyld',documentId:'edge',revision:1,contentSha256:'a'.repeat(64),visibility:'internal',draftGeneration:0,selectionGeneration:0,canEdit:true};
 const changed=vi.fn();return{editor,state,changed,bridge:createBuildComposeBridge(()=>state,changed)};
}
describe('Build image insertion boundary',()=>{
 it('inserts stable image once and keeps surrounding text',async()=>{
  const {editor,bridge,changed}=setup();try{
   const captured=await bridge.capture();bridge.insert(captured,mediaMarkdown(id,'Edge at dusk'));
   expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toContain(`![Edge at dusk](dmb-media:${id})`);
   expect(editor.getText()).toContain('Edge');expect(changed).toHaveBeenCalledTimes(1);
   expect(()=>bridge.insert(captured,mediaMarkdown(id,'Edge'))).toThrow('already');
  }finally{editor.destroy();}
 });
 it('refuses a changed document without modifying it',async()=>{
  const {editor,state,bridge}=setup();try{
   const captured=await bridge.capture();state.documentId='another';
   expect(()=>bridge.insert(captured,mediaMarkdown(id,'Edge'))).toThrow('changed');
   expect(editor.getJSON()).toEqual(JSON.parse(captured.editorJson));
  }finally{editor.destroy();}
 });
});
