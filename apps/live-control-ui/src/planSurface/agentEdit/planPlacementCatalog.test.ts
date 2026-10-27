import {Editor,type JSONContent} from '@tiptap/core';
import {describe,expect,it} from 'vitest';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../../tiptap/MarkdownEditorCore';
import {compilePlanPlacementOptions,resolvePlanPlacementOption,planPlacementModelChoices} from './planPlacementCatalog';
const p=(text:string):JSONContent=>({type:'paragraph',content:[{type:'text',text}]});
const h=(level:number,text:string):JSONContent=>({type:'heading',attrs:{level},content:[{type:'text',text}]});
function withEditor(content:JSONContent[],run:(editor:Editor)=>void){
 const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:{type:'doc',content}});
 try{run(editor);}finally{editor.destroy();}
}
describe('captured Plan placement catalog',()=>{
 it('inserts at the true boundary after an objective and before its next Beat, preserving all outside nodes',()=>{
  withEditor([h(1,'Rehearsal'),h(2,'Preparation objective'),p('Keep every alternative open.'),
    h(2,'Opening Beat'),h(3,'Scene'),p('Existing scene body.')],editor=>{
   const snapshot=JSON.stringify(editor.getJSON()),before=editor.getJSON().content!;
   const entry=compilePlanPlacementOptions(editor,snapshot,'insert_at_caret').find(row=>row.selector==='after:1')!;
   expect(entry.root_boundary).toBe(3);
   expect(editor.state.doc.resolve(entry.position!).depth).toBe(0);
   expect(editor.commands.insertContentAt(entry.position!,p('Proposed briefing.'))).toBe(true);
   expect(editor.getJSON().content).toEqual([...before.slice(0,3),p('Proposed briefing.'),...before.slice(3)]);
  });
 });
 it('uses ProseMirror UTF-16 positions and keeps nested headings inside the section',()=>{
  withEditor([h(2,'Objective 🐑'),p('🦋 nectar'),h(3,'Details'),p('é / 🐝'),h(2,'Beat')],editor=>{
   const snapshot=JSON.stringify(editor.getJSON()),entries=compilePlanPlacementOptions(editor,snapshot,'insert_at_caret');
   const after=entries.find(row=>row.selector==='after:0')!;
   expect(after.root_boundary).toBe(4);
   expect(after.position).toBe(editor.state.doc.child(0).nodeSize+editor.state.doc.child(1).nodeSize
    +editor.state.doc.child(2).nodeSize+editor.state.doc.child(3).nodeSize);
   expect(resolvePlanPlacementOption(editor,snapshot,'insert_at_caret',after)).toEqual(after);
  });
 });
 it('keeps a caption and table indivisible, including when the section ends with a table',()=>{
  const table:JSONContent={type:'table',content:[{type:'tableRow',content:[{type:'tableCell',content:[p('Cue')]}]}]};
  withEditor([h(2,'Objective'),p('Text'),h(2,'Named table'),table,h(2,'Beat')],editor=>{
   const snapshot=JSON.stringify(editor.getJSON()),before=editor.getJSON().content!;
   const entries=compilePlanPlacementOptions(editor,snapshot,'insert_at_caret');
   expect(entries.some(row=>row.selector==='before:2'||row.selector==='after:2')).toBe(false);
   expect(entries.some(row=>row.root_boundary===3)).toBe(false);
   const after=entries.find(row=>row.selector==='after:0')!;
   expect(after.root_boundary).toBe(4);
   expect(editor.commands.insertContentAt(after.position!,p('After table, outside its cells.'))).toBe(true);
   expect(editor.getJSON().content).toEqual([...before.slice(0,4),p('After table, outside its cells.'),...before.slice(4)]);
  });
 });
 it('distinguishes duplicate headings and preserves every offered location without a cap',()=>{
  withEditor(Array.from({length:70},()=>h(2,'Repeated')),editor=>{
   const entries=compilePlanPlacementOptions(editor,JSON.stringify(editor.getJSON()),'insert_at_caret');
   expect(entries).toHaveLength(142);
   expect(new Set(entries.map(row=>row.selector)).size).toBe(entries.length);
   expect(entries.find(row=>row.selector==='before:0')?.label).toContain('1 of 70');
   expect(entries.find(row=>row.selector==='before:69')?.label).toContain('70 of 70');
  });
 });
 it('does not broaden replacement authority or expose host positions to the provider',()=>{
  withEditor([h(2,'Objective'),p('Do not broaden this.')],editor=>{
   const json=JSON.stringify(editor.getJSON());
   for(const kind of ['replace_selection','replace_playable_body'] as const)
    expect(compilePlanPlacementOptions(editor,json,kind).map(row=>row.selector)).toEqual(['captured']);
   const projected=planPlacementModelChoices(compilePlanPlacementOptions(editor,json,'insert_at_caret'));
   expect(projected.every(row=>Object.keys(row).sort().join(',')==='label,selector')).toBe(true);
  });
 });
 it('refuses changed snapshots and forged or stale host boundaries',()=>{
  withEditor([h(2,'Objective'),p('Original')],editor=>{
   const json=JSON.stringify(editor.getJSON());
   const entry=compilePlanPlacementOptions(editor,json,'insert_at_caret').find(row=>row.selector==='after:0')!;
   expect(()=>resolvePlanPlacementOption(editor,json,'insert_at_caret',{...entry,position:1})).toThrow(/boundary/);
   expect(()=>resolvePlanPlacementOption(editor,json,'insert_at_caret',{...entry,label:'Elsewhere'})).toThrow(/boundary/);
   editor.commands.insertContentAt(editor.state.doc.content.size,p('Newer draft'));
   expect(()=>resolvePlanPlacementOption(editor,json,'insert_at_caret',entry)).toThrow(/page changed/);
  });
 });
});
