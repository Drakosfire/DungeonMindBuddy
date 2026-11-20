import {Editor,type JSONContent} from '@tiptap/core';
import {webcrypto} from 'node:crypto';
import {describe,it,expect,vi} from 'vitest';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../../apps/live-control-ui/src/tiptap/MarkdownEditorCore';
import {createBuildComposeBridge,type BuildComposeEditorState} from '../../apps/live-control-ui/src/buildSurface/buildComposeBridge';
import {compilePlanPlacementOptions,resolvePlanPlacementOption} from '../../apps/live-control-ui/src/planSurface/agentEdit/planPlacementCatalog';
vi.stubGlobal('crypto',webcrypto);
const p=(text:string):JSONContent=>({type:'paragraph',content:[{type:'text',text}]});
const h=(text:string):JSONContent=>({type:'heading',attrs:{level:2},content:[{type:'text',text}]});
const opening='Opening image: three lantern flashes ripple across the eastern ridge.';
const scouts='The scouts have returned, but no one will explain why they were silent.';
function setup(){
 const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:{type:'doc',content:[h('Overview'),p('Unrelated opening; do not change.'),h('Preparation'),p(opening+' '+scouts),h('Opening Beat'),p('Keep the playable encounter unchanged.'),h('Rumours'),p(scouts)]}});
 editor.commands.setTextSelection(1);
 const state:BuildComposeEditorState={editor,worldId:'synthetic',documentId:'fixture',revision:1,contentSha256:'a'.repeat(64),visibility:'internal',draftGeneration:0,selectionGeneration:0,canEdit:true};
 return {editor,state,bridge:createBuildComposeBridge(()=>state,()=>{})};
}
describe('main host-capability baseline, NOT ordinary model routing',()=>{
 it('Build capture is incidental caret, not a named prose replacement',async()=>{
  const {editor,bridge}=setup();try{
   const before=editor.getJSON();const capture=await bridge.capture();
   expect(capture.basis.caret).toBe(1);expect(capture.basis.selection).toBeUndefined();
   expect(capture.pageBodyOffer).toBeDefined();expect(capture.pageEndOffer).toBeDefined();
   expect(editor.getJSON()).toEqual(before);
   console.log('BASELINE build-named-rewrite: no semantic replacement offer; ordinary routing unscored');
  }finally{editor.destroy();}
 });
 it('Plan already offers requested section boundary independent of caret',()=>{
  const {editor}=setup();try{
   const before=editor.getJSON(),snapshot=JSON.stringify(before);
   const entry=compilePlanPlacementOptions(editor,snapshot,'insert_at_caret').find(x=>x.selector==='after:2')!;
   expect(entry.root_boundary).toBe(4);expect(entry.position).not.toBe(1);
   expect(resolvePlanPlacementOption(editor,snapshot,'insert_at_caret',entry)).toEqual(entry);
   editor.commands.insertContentAt(entry.position!,p('Synthetic briefing.'));
   expect(editor.getJSON().content).toEqual([...before.content!.slice(0,4),p('Synthetic briefing.'),...before.content!.slice(4)]);
   editor.commands.undo();expect(editor.getJSON()).toEqual(before);
   console.log('BASELINE plan-after-objective: host boundary and native Undo pass; model choice unscored');
  }finally{editor.destroy();}
 });
 it('Plan does not offer an intra-paragraph after-sentence target without selection',()=>{
  const {editor}=setup();try{
   const snapshot=JSON.stringify(editor.getJSON());
   const options=compilePlanPlacementOptions(editor,snapshot,'insert_at_caret');
   let passageStart=0;editor.state.doc.forEach((node,pos)=>{if(node.textContent.startsWith(opening))passageStart=pos+1;});
   expect(options.some(x=>x.position===passageStart+opening.length)).toBe(false);
   expect(JSON.stringify(editor.getJSON())).toBe(snapshot);
   console.log('BASELINE plan-after-sentence: no host option; manual-caret precedent is not no-selection proof');
  }finally{editor.destroy();}
 });
 it('stale Plan boundary and read-only Build capture refuse without mutation',async()=>{
  const {editor,state,bridge}=setup();try{
   const snapshot=JSON.stringify(editor.getJSON());const entry=compilePlanPlacementOptions(editor,snapshot,'insert_at_caret')[1]!;
   editor.commands.insertContentAt(editor.state.doc.content.size,p('Human intervening edit.'));
   const after=editor.getJSON();expect(()=>resolvePlanPlacementOption(editor,snapshot,'insert_at_caret',entry)).toThrow();
   state.canEdit=false;await expect(bridge.capture()).rejects.toThrow();expect(editor.getJSON()).toEqual(after);
  }finally{editor.destroy();}
 });
});
