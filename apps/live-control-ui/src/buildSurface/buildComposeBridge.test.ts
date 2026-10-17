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


it('inserts a saved image into a draft with Shift+Enter and blank-line runs',async()=>{
 const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:'<h1>Edge</h1><p>Before<br>Next line<br><br>After</p><p>End</p>'});
 const state:BuildComposeEditorState={editor,worldId:'elderwyld',documentId:'edge',revision:1,contentSha256:'a'.repeat(64),visibility:'internal',draftGeneration:0,selectionGeneration:0,canEdit:true};
 const bridge=createBuildComposeBridge(()=>state,()=>{});
 try{
  editor.commands.setTextSelection(editor.state.doc.content.size-1);
  const before=editor.getJSON();const capture=await bridge.capture();bridge.insert(capture,mediaMarkdown(id,'Edge map'));
  const markdown=tiptapJsonToSemanticMarkdown(editor.getJSON());
  expect(markdown).toContain('Before'+String.fromCharCode(92,10)+'Next line'+String.fromCharCode(92,10).repeat(2)+'After');
  expect(markdown).toContain(`![Edge map](dmb-media:${id})`);
  const {markdownToTiptapDoc}=await import('../tiptap/markdown/markdownToTiptap');
  const reopened=markdownToTiptapDoc(markdown);expect(reopened.diagnostics).toEqual([]);
  expect(tiptapJsonToSemanticMarkdown(reopened.doc)).toBe(markdown);
  editor.commands.undo();expect(editor.getJSON()).toEqual(before);
 }finally{editor.destroy();}
});

it('preserves leading, single, repeated paragraph breaks without changing enclosing structure',async()=>{
 const {markdownToTiptapDoc}=await import('../tiptap/markdown/markdownToTiptap');
 const {semanticMarkdownSerializationDiagnostics}=await import('../tiptap/markdown/semanticMarkdownSafety');
 for(const n of [1,2,3]){
  for(const lead of [false,true]){
   const content=[...(lead?[]:[{type:'text',text:'Before',marks:[{type:'bold'}]}]),...Array.from({length:n},()=>({type:'hardBreak'})),{type:'text',text:'After'}];
   const doc={type:'doc',content:[{type:'paragraph',content}]};
   expect(semanticMarkdownSerializationDiagnostics(doc)).toEqual([]);
   const md=tiptapJsonToSemanticMarkdown(doc);const reopened=markdownToTiptapDoc(md);
   expect(reopened.diagnostics).toEqual([]);expect(reopened.doc).toEqual(doc);
  }
 }
 const trailing={type:'doc',content:[{type:'paragraph',content:[{type:'text',text:'Before'},{type:'hardBreak'}]}]};
 expect(semanticMarkdownSerializationDiagnostics(trailing).length).toBeGreaterThan(0);
});

it('places a closure-bound saved image at an explicit drop and supports one Undo',async()=>{
 const {editor,bridge,state,changed}=setup();
 document.body.appendChild(editor.view.dom);
 const controller=new AbortController();
 try{
  editor.commands.setContent('<p>Before</p><p>After</p>');editor.commands.setTextSelection(1);
  const before=editor.getJSON();
  vi.spyOn(editor.view,'posAtCoords').mockReturnValue({pos:9,inside:8});
  const pending=bridge.pickInsertion!({signal:controller.signal,mode:'drag',assetId:id});
  const event=new MouseEvent('drop',{bubbles:true,cancelable:true,clientX:10,clientY:20});
  Object.defineProperty(event,'dataTransfer',{value:{getData:(key:string)=>key==='application/x-dmb-media'?id:''}});
  editor.view.dom.dispatchEvent(event);
  const target=await pending;bridge.insert(target,mediaMarkdown(id,'Edge map'));
  expect(event.defaultPrevented).toBe(true);expect(changed).toHaveBeenCalledTimes(1);
  let count=0;editor.state.doc.descendants(node=>{if(node.type.name==='mediaImage')count++;});expect(count).toBe(1);
  const md=tiptapJsonToSemanticMarkdown(editor.getJSON());expect(md.indexOf('Before')).toBeLessThan(md.indexOf('![Edge map]'));expect(md.indexOf('![Edge map]')).toBeLessThan(md.indexOf('After'));
  editor.commands.undo();expect(editor.getJSON()).toEqual(before);
  state.documentId='other';
 }finally{controller.abort();editor.view.dom.remove();editor.destroy();}
});

it('rejects foreign drops, outside positions, selection replacement and cancellation without mutation',async()=>{
 for(const scenario of ['foreign','outside','selection','abort']){
  const {editor,bridge,changed}=setup();const controller=new AbortController();const before=editor.getJSON();
  try{
   vi.spyOn(editor.view,'posAtCoords').mockReturnValue(scenario==='outside'?null:{pos:1,inside:0});
   if(scenario==='selection')editor.commands.setTextSelection({from:1,to:3});
   const pending=bridge.pickInsertion!({signal:controller.signal,mode:'drag',assetId:id});
   const observed=expect(pending).rejects.toThrow();
   if(scenario==='abort')controller.abort();
   else{const event=new MouseEvent('drop',{bubbles:true,cancelable:true});Object.defineProperty(event,'dataTransfer',{value:{getData:()=>scenario==='foreign'?'different':id}});editor.view.dom.dispatchEvent(event);expect(event.defaultPrevented).toBe(true);}
   await observed;expect(editor.getJSON()).toEqual(before);expect(changed).not.toHaveBeenCalled();
  }finally{controller.abort();editor.destroy();}
 }
});
