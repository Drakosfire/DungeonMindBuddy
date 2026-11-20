import {Editor,type JSONContent} from '@tiptap/core';
import {webcrypto} from 'node:crypto';
import {describe,it,expect,vi} from 'vitest';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../../apps/live-control-ui/src/tiptap/MarkdownEditorCore';
import {PAGE_COMPOSER_EXTENSIONS} from '../../apps/live-control-ui/src/tiptap/pageComposer/PageRow';
import {createBuildComposeBridge,type BuildComposeEditorState} from '../../apps/live-control-ui/src/buildSurface/buildComposeBridge';
vi.stubGlobal('crypto',webcrypto);
const p=(text:string,id:string):JSONContent=>({type:'paragraph',attrs:{pageBlockId:id},content:[{type:'text',text}]});
const h=(text:string):JSONContent=>({type:'heading',attrs:{level:2,pageBlockId:'heading-'+text},content:[{type:'text',text}]});
function setup(enabled=true,stableIds=true){
 const editor=new Editor({extensions:[...DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,...PAGE_COMPOSER_EXTENSIONS],content:{type:'doc',content:[h('Overview'),p('Untouched opening.','opening'),h('Preparation'),p('The scouts returned silently.','intended'),h('Opening Beat'),p('The scouts returned silently.','duplicate')].map(node=>stableIds?node:{...node,attrs:{...node.attrs,pageBlockId:null}})}});
 editor.commands.setTextSelection(1);
 const state:BuildComposeEditorState={editor,worldId:'synthetic',documentId:'page',revision:1,contentSha256:'a'.repeat(64),visibility:'internal',draftGeneration:0,selectionGeneration:0,canEdit:true};
 editor.on('transaction',({transaction})=>{if(transaction.docChanged)state.draftGeneration++;});
 const changed=vi.fn(),save=vi.fn().mockResolvedValue(undefined);
 const bridge=createBuildComposeBridge(()=>state,changed,save,{allowProseTargets:enabled});
 return {editor,state,bridge,changed,save};
}
async function nominate(bridge:ReturnType<typeof createBuildComposeBridge>){
 const catalog=await bridge.captureProseTargets!();
 const option=catalog.choices.find(x=>x.section==='Preparation'&&x.operation==='replace_paragraph')!;
 return bridge.captureProseInsertion!(catalog,option.selector);
}
describe('isolated opt-in native prose editor transaction, not model routing',()=>{
 it('replaces the chosen duplicate only; retains node identity, one Undo/Redo and no implicit Save',async()=>{
  const {editor,bridge,changed,save}=setup();try{
   const before=editor.getJSON(),captured=await nominate(bridge);
   expect(captured.basis.caret).toBe(1);expect(captured.basis.selection).toBeUndefined();
   const prepared=await bridge.prepareProposal(captured,'The scouts returned without speaking.');
   expect(editor.getJSON()).toEqual(before);expect(changed).not.toHaveBeenCalled();
   bridge.applyPrepared(prepared);
   const after=editor.getJSON();expect(after.content!.filter((_,i)=>i!==3)).toEqual(before.content!.filter((_,i)=>i!==3));
   expect(after.content![3]!.attrs).toEqual(before.content![3]!.attrs);
   expect(editor.state.doc.child(3).textContent).toBe('The scouts returned without speaking.');
   expect(changed).toHaveBeenCalledTimes(1);expect(save).not.toHaveBeenCalled();
   editor.commands.undo();expect(editor.getJSON()).toEqual(before);
   expect(()=>bridge.applyPrepared(prepared)).toThrow();
   editor.commands.redo();expect(editor.getJSON()).toEqual(after);
   await bridge.saveProposal(captured.basis,prepared.afterEditorSha256,prepared.afterDraftSha256);
   expect(save).toHaveBeenCalledTimes(1);
  }finally{editor.destroy();}
 });
 it('refuses when existing normalization would stamp unrelated block IDs',async()=>{
  const {editor,bridge,changed,save}=setup(true,false);try{
   const before=editor.getJSON(),captured=await nominate(bridge);
   await expect(bridge.prepareProposal(captured,'The scouts returned without speaking.')).rejects.toThrow('unrelated page structure');
   expect(editor.getJSON()).toEqual(before);expect(changed).not.toHaveBeenCalled();expect(save).not.toHaveBeenCalled();
  }finally{editor.destroy();}
 });
 it('restores an immutable nomination on a fresh editor without faking author selection',async()=>{
  const first=setup(),second=setup();try{
   const captured=await nominate(first.bridge);
   const restored=await second.bridge.restore(captured.basis,undefined,undefined,captured.proseTarget);
   expect(restored.proseTarget).toEqual(captured.proseTarget);expect(restored.basis.selection).toBeUndefined();
   const prepared=await second.bridge.prepareProposal(restored,'The scouts returned without speaking.');
   second.bridge.applyPrepared(prepared);expect(second.editor.state.doc.child(5).textContent).toBe('The scouts returned silently.');
  }finally{first.editor.destroy();second.editor.destroy();}
 });
 it('defaults off and refuses unissued/forged extents and multi-paragraph output',async()=>{
  const enabled=setup(),disabled=setup(false);try{
   await expect(nominate(disabled.bridge)).rejects.toThrow('not enabled');
   const captured=await nominate(enabled.bridge),before=enabled.editor.getJSON();
   await expect(enabled.bridge.restore(captured.basis,undefined,undefined,{...captured.proseTarget!,from:1})).rejects.toThrow();
   await expect(enabled.bridge.prepareProposal({...captured},'Unsafe')).rejects.toThrow('not admitted');
   await expect(enabled.bridge.prepareProposal(captured,'One paragraph.\n\nAnother paragraph.')).rejects.toThrow('one paragraph');
   expect(enabled.editor.getJSON()).toEqual(before);expect(enabled.changed).not.toHaveBeenCalled();expect(enabled.save).not.toHaveBeenCalled();
  }finally{enabled.editor.destroy();disabled.editor.destroy();}
 });
 it.each(['edit','readonly','scope'] as const)('refuses intervening %s without replacing anything',async kind=>{
  const {editor,state,bridge,save,changed}=setup();try{
   const captured=await nominate(bridge);
   if(kind==='edit')editor.commands.insertContentAt(editor.state.doc.content.size,p('Human addition.','human'));
   if(kind==='readonly')editor.setEditable(false,false);
   if(kind==='scope')state.documentId='other';
   const before=editor.getJSON();
   await expect(bridge.prepareProposal(captured,'No mutation.')).rejects.toThrow();
   expect(editor.getJSON()).toEqual(before);expect(changed).not.toHaveBeenCalled();expect(save).not.toHaveBeenCalled();
  }finally{editor.destroy();}
 });
});
