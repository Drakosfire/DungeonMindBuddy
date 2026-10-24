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


it('recovers the original position after editor recreation and ignores a later caret', async () => {
 const first=setup();
 first.editor.commands.setContent('<p>Before</p><p>After</p>');
 first.editor.commands.setTextSelection(7);
 const captured=await first.bridge.capture(); const original=first.editor.getJSON(); first.editor.destroy();
 const next=setup();
 try {
  next.editor.commands.setContent(original); next.editor.commands.setTextSelection(1);
  next.state.draftGeneration=12; next.state.selectionGeneration=20;
  const restored=await next.bridge.restore(captured.basis);
  expect(restored.basis.caret).toBe(7); expect(next.editor.state.selection.from).toBe(1);
  next.bridge.insertProposal(restored, 'A proposed culture.');
  expect(next.editor.getText()).toContain('A proposed culture.');
  const markdown=tiptapJsonToSemanticMarkdown(next.editor.getJSON());
  expect(markdown.indexOf('Before')).toBeLessThan(markdown.indexOf('A proposed culture.'));
  expect(markdown.indexOf('A proposed culture.')).toBeLessThan(markdown.indexOf('After'));
  expect(next.changed).toHaveBeenCalledTimes(1);
  next.editor.commands.undo(); expect(next.editor.getJSON()).toEqual(original);
  expect(()=>next.bridge.insertProposal(restored,'Again')).toThrow('already');
 } finally {next.editor.destroy();}
});
it('preserves strict media placement but lets the captured proposal use its own target', async () => {
 const {editor,state,bridge}=setup();
 try {
  const captured=await bridge.capture(); editor.commands.setTextSelection(3); state.selectionGeneration++;
  expect(()=>bridge.insert(captured,'Media placement')).toThrow('changed');
  bridge.insertProposal(captured,'Proposed text');
  expect(editor.getText()).toContain('Proposed text');
 } finally {editor.destroy();}
});
it.each(['worldId','documentId','revision','contentSha256','visibility','canEdit'] as const)(
 'refuses original-anchor recovery after %s drift',async field=>{
 const {editor,state,bridge}=setup();
 try {
  const captured=await bridge.capture();
  Object.assign(state,{[field]:field==='revision'?2:field==='canEdit'?false:'different'});
  const before=editor.getJSON(); await expect(bridge.restore(captured.basis)).rejects.toThrow();
  expect(editor.getJSON()).toEqual(before);
 } finally {editor.destroy();}
});
it.each(['document','digest','draft','position','missing'] as const)('rejects %s anchor drift without mutation',async scenario=>{
 const {editor,bridge}=setup();
 try {
  const captured=await bridge.capture(); const basis={...captured.basis};
  if(scenario==='document')editor.commands.insertContent('My new writing');
  if(scenario==='digest')basis.editor_sha256='f'.repeat(64);
  if(scenario==='draft')basis.draft_sha256='f'.repeat(64);
  if(scenario==='position')basis.caret=editor.state.doc.content.size+1;
  if(scenario==='missing')delete basis.editor_sha256;
  const before=editor.getJSON();await expect(bridge.restore(basis)).rejects.toThrow();expect(editor.getJSON()).toEqual(before);
 } finally {editor.destroy();}
});
it('rejects an editor replacement during asynchronous original-anchor recovery',async()=>{
 const {editor,state,bridge}=setup();let replacement:Editor|undefined;
 try {
  const captured=await bridge.capture();const pending=bridge.restore(captured.basis);
  replacement=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:editor.getJSON()});
  state.editor=replacement;
  await expect(pending).rejects.toThrow('changed');expect(replacement.getJSON()).toEqual(editor.getJSON());
 } finally {editor.destroy();replacement?.destroy();}
});


it.each(['inline','block'])('stages an exact %s selection replacement and restores it after editor recreation',async kind=>{
 const first=setup();
 first.editor.commands.setContent(kind==='inline'?'<p>Before old text after.</p>':'<p>Before</p><p>Old text</p><p>After</p>');
 const from=kind==='inline'?8:9,to=from+8;
 first.editor.commands.setTextSelection({from,to});
 const captured=await first.bridge.capture(), before=first.editor.getJSON();
 expect(captured.basis.selection).toEqual({end:to,text:kind==='inline'?'old text':'Old text'});
 const prepared=await first.bridge.prepareProposal(captured,'New wording');
 expect(first.editor.getJSON()).toEqual(before);
 first.editor.destroy();
 const next=setup();next.editor.commands.setContent(before);next.editor.commands.setTextSelection(1);
 try{
  const restored=await next.bridge.restore(captured.basis);
  const reopened=await next.bridge.prepareProposal(restored,'New wording');
  expect(reopened.afterEditorSha256).toBe(prepared.afterEditorSha256);
  next.bridge.applyPrepared(reopened);
  expect(next.editor.getText()).toContain('Before');
  expect(next.editor.getText()).toContain(kind==='inline'?'after.':'After');
  expect(next.editor.getText()).not.toContain(kind==='inline'?'old text':'Old text');
  expect(next.editor.getText()).toContain('New wording');
  if(kind==='inline')expect(next.editor.state.doc.childCount).toBe(1);
  expect(()=>next.bridge.applyPrepared(reopened)).toThrow('already');
  next.editor.commands.undo();expect(next.editor.getJSON()).toEqual(before);
 }finally{next.editor.destroy();}
});


it('refuses stale or forged replacement targets and never uses a selection for image placement',async()=>{
 const {editor,bridge,state}=setup();
 try{
  editor.commands.setContent('<p>Old text</p><p>Keep this</p>');editor.commands.setTextSelection({from:1,to:9});
  const captured=await bridge.capture(),before=editor.getJSON();
  expect(()=>bridge.insert(captured,mediaMarkdown(id,'Image'))).toThrow('requires a caret');
  await expect(bridge.restore({...captured.basis,selection:{end:9,text:'Forged'}})).rejects.toThrow('selected passage changed');
  await expect(bridge.restore({...captured.basis,selection:{end:999,text:'Old text'}})).rejects.toThrow();
  expect(editor.getJSON()).toEqual(before);
  state.documentId='another';await expect(bridge.prepareProposal(captured,'Revision')).rejects.toThrow('changed');
  state.documentId='edge';editor.commands.insertContent('New local work');state.draftGeneration++;
  const changed=editor.getJSON();await expect(bridge.restore(captured.basis)).rejects.toThrow('changed');
  expect(editor.getJSON()).toEqual(changed);
 }finally{editor.destroy();}
});


it('replaces a selection spanning paragraphs and refuses a prepared change after new local writing',async()=>{
 const {editor,bridge,state}=setup();
 try{
  editor.commands.setContent('<p>Before</p><p>Old first</p><p>Old second</p><p>After</p>');
  const from=editor.state.doc.child(0).nodeSize+1;
  const to=from+editor.state.doc.child(1).nodeSize+editor.state.doc.child(2).content.size;
  editor.commands.setTextSelection({from,to});
  const captured=await bridge.capture(),before=editor.getJSON();
  expect(captured.basis.selection?.text).toBe('Old first\nOld second');
  const prepared=await bridge.prepareProposal(captured,'New first\n\nNew second');
  expect(editor.getJSON()).toEqual(before);
  bridge.applyPrepared(prepared);
  expect(editor.getText()).toContain('Before');expect(editor.getText()).toContain('After');
  expect(editor.getText()).not.toContain('Old');expect(editor.getText()).toContain('New second');
  editor.commands.undo();expect(editor.getJSON()).toEqual(before);
  const restored=await bridge.restore(captured.basis);
  const pending=await bridge.prepareProposal(restored,'Another version');
  editor.commands.setTextSelection(1);editor.commands.insertContent('My newer writing.');state.draftGeneration++;
  const newer=editor.getJSON();expect(()=>bridge.applyPrepared(pending)).toThrow('changed');
  expect(editor.getJSON()).toEqual(newer);
 }finally{editor.destroy();}
});
