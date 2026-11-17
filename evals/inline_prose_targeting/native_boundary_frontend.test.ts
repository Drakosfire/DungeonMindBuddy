import {Editor,type JSONContent} from '@tiptap/core';
import {webcrypto} from 'node:crypto';
import {describe,it,expect,vi} from 'vitest';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../../apps/live-control-ui/src/tiptap/MarkdownEditorCore';
import {PAGE_COMPOSER_EXTENSIONS} from '../../apps/live-control-ui/src/tiptap/pageComposer/PageRow';
import {createBuildComposeBridge,type BuildComposeEditorState} from '../../apps/live-control-ui/src/buildSurface/buildComposeBridge';
vi.stubGlobal('crypto',webcrypto);
const p=(text:string,id?:string):JSONContent=>({type:'paragraph',attrs:{pageBlockId:id??null},content:[{type:'text',text}]});
const h=(text:string,id:string):JSONContent=>({type:'heading',attrs:{level:2,pageBlockId:id},content:[{type:'text',text}]});
function setup(enabled=true,missing=false,presented=true,replacement=false){
 const editor=new Editor({extensions:[...DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,...PAGE_COMPOSER_EXTENSIONS],content:{type:'doc',content:[h('Overview','overview'),p('Keep opening.',missing?undefined:'opening'),h('Preparation','preparation'),p('The scouts returned silently.','target'),h('Rumours','rumours'),p('The scouts returned silently.','duplicate'),...(presented?[{type:'pageRow',attrs:{id:'row',min_height:0,line_mode:'clean'},content:[{type:'pageSlot',attrs:{id:'slot',width:12},content:[p('Untouched row.','row-text')]}]}]:[])]}});
 editor.commands.setTextSelection(1);
 const state:BuildComposeEditorState={editor,worldId:'synthetic',documentId:'boundary-proof',revision:1,contentSha256:'a'.repeat(64),visibility:'internal',draftGeneration:0,selectionGeneration:0,canEdit:true};
 editor.on('transaction',({transaction})=>{if(transaction.docChanged)state.draftGeneration++;});
 const changed=vi.fn(),save=vi.fn();
 const bridge=createBuildComposeBridge(()=>state,changed,save,{allowProseTargets:replacement,allowProseBoundaries:enabled});
 return {editor,state,bridge,changed,save};
}
async function capture(bridge:ReturnType<typeof createBuildComposeBridge>,operation:'insert_before'|'insert_after'){
 const catalog=await bridge.captureProseTargets!();
 const choice=catalog.choices.find(row=>row.operation===operation&&row.section==='Preparation')!;
 return bridge.captureProseInsertion!(catalog,choice.selector);
}
describe('host-bound native paragraph boundary, no model',()=>{
 it.each(['insert_before','insert_after'] as const)('adds exactly one paragraph at %s and one Undo restores all old nodes',async operation=>{
  const {editor,bridge,changed,save}=setup();try{
   const before=editor.getJSON();const captured=await capture(bridge,operation);
   expect(captured.basis.caret).toBe(1);expect(captured.basis.selection).toBeUndefined();
   expect(captured.proseTarget!.schema).toBe('dmb_build_prose_boundary_target_v1');expect(captured.proseTarget!.from).toBe(captured.proseTarget!.to);
   const prepared=await bridge.prepareProposal(captured,'A lone watcher keeps vigil.');
   expect(editor.getJSON()).toEqual(before);bridge.applyPrepared(prepared);
   const index=operation==='insert_before'?3:4;const after=editor.getJSON();
   expect(after.content!.filter((_,i)=>i!==index)).toEqual(before.content);
   expect(editor.state.doc.child(index).textContent).toBe('A lone watcher keeps vigil.');
   expect(after.content![index]!.attrs!.pageBlockId).toMatch(/^page-prose-/);
   expect(changed).toHaveBeenCalledTimes(1);expect(save).not.toHaveBeenCalled();
   editor.commands.undo();expect(editor.getJSON()).toEqual(before);
   expect(()=>bridge.applyPrepared(prepared)).toThrow();
  }finally{editor.destroy();}
 });
 it('boundary-only opt-in refuses a replacement nomination',async()=>{
  const {editor,bridge}=setup();try{
   const before=editor.getJSON();const catalog=await bridge.captureProseTargets!();
   const choice=catalog.choices.find(row=>row.operation==='replace_paragraph'&&row.section==='Preparation')!;
   await expect(bridge.captureProseInsertion!(catalog,choice.selector)).rejects.toThrow();
   expect(editor.getJSON()).toEqual(before);
  }finally{editor.destroy();}
 });
 it('replacement-only opt-in refuses boundary capture and restored bytes',async()=>{
  const {editor,bridge}=setup(false,false,true,true);try{
   const before=editor.getJSON();await expect(capture(bridge,'insert_after')).rejects.toThrow();expect(editor.getJSON()).toEqual(before);
  }finally{editor.destroy();}
 });
 it.each(['edit','readonly','scope','normalization'] as const)('refuses %s with zero side effects',async kind=>{
  const {editor,state,bridge,save,changed}=setup(true,kind==='normalization');try{
   const captured=await capture(bridge,'insert_after');
   if(kind==='edit')editor.commands.insertContentAt(editor.state.doc.content.size,p('Human edit.','human'));
   if(kind==='readonly')editor.setEditable(false,false);
   if(kind==='scope')state.documentId='other';
   const before=editor.getJSON();await expect(bridge.prepareProposal(captured,'One addition.')).rejects.toThrow();
   expect(editor.getJSON()).toEqual(before);expect(save).not.toHaveBeenCalled();expect(changed).not.toHaveBeenCalled();
  }finally{editor.destroy();}
 });
 it('refuses a plain page instead of adding layout or losing identities at Save',async()=>{
  const {editor,bridge,save,changed}=setup(true,false,false);try{
   const captured=await capture(bridge,'insert_after');const before=editor.getJSON();
   await expect(bridge.prepareProposal(captured,'One addition.')).rejects.toThrow('existing saved page composition');
   expect(editor.getJSON()).toEqual(before);expect(save).not.toHaveBeenCalled();expect(changed).not.toHaveBeenCalled();
  }finally{editor.destroy();}
 });
 it('refuses pre-existing invalid IDs that the Save projection would rename',async()=>{
  const {editor,bridge,save,changed}=setup();try{
   editor.commands.setNodeSelection(0);editor.commands.updateAttributes('heading',{pageBlockId:'x'.repeat(81)});
   editor.commands.setTextSelection(1);const captured=await capture(bridge,'insert_after');const before=editor.getJSON();
   await expect(bridge.prepareProposal(captured,'One addition.')).rejects.toThrow();
   expect(editor.getJSON()).toEqual(before);expect(save).not.toHaveBeenCalled();expect(changed).not.toHaveBeenCalled();
  }finally{editor.destroy();}
 });
 it('rejects forged boundary, unknown alias and multiple paragraphs',async()=>{
  const {editor,bridge}=setup();try{
   const before=editor.getJSON();const captured=await capture(bridge,'insert_after');
   await expect(bridge.restore(captured.basis,undefined,undefined,{...captured.proseTarget!,from:1,to:1})).rejects.toThrow();
   const catalog=await bridge.captureProseTargets!();await expect(bridge.captureProseInsertion!(catalog,'first matching scouts')).rejects.toThrow();
   await expect(bridge.prepareProposal(captured,'One.\n\nTwo.')).rejects.toThrow();expect(editor.getJSON()).toEqual(before);
  }finally{editor.destroy();}
 });
});
