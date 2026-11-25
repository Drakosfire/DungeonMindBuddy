import {Editor,type JSONContent} from '@tiptap/core';
import {describe,expect,it} from 'vitest';
import {createHash} from 'node:crypto';
import {writeFile} from 'node:fs/promises';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../../tiptap/MarkdownEditorCore';
import {PAGE_COMPOSER_EXTENSIONS,wrapPageRow} from '../../tiptap/pageComposer/PageRow';
import {compilePlanPlacementOptions,resolvePlanPlacementOption,planPlacementModelChoices,
 compilePlanParagraphPlacementOptions,resolvePlanParagraphPlacementOption,planParagraphPlacementModelChoices} from './planPlacementCatalog';
import {capturePlanParagraphPlacementCatalog,capturePlanPlacementCatalog} from './planPlacementCatalog';
import type {PlanOriginalAuthoringCapture} from '../../api/planAuthoringReviewApi';
const p=(text:string):JSONContent=>({type:'paragraph',content:[{type:'text',text}]});
const h=(level:number,text:string):JSONContent=>({type:'heading',attrs:{level},content:[{type:'text',text}]});
function withEditor(content:JSONContent[],run:(editor:Editor)=>void){
 const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:{type:'doc',content}});
 try{run(editor);}finally{editor.destroy();}
}
describe('versioned plain Plan paragraph placement',()=>{
 it('seals V2 from the actual editor without changing the legacy producer or exposing host fields',async()=>{
  const content=[h(2,'Preparation 🐑'),p('Bring the brass key.'),p('Check the lamp.')];
  const editor=new Editor({extensions:[...DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,...PAGE_COMPOSER_EXTENSIONS],content:{type:'doc',content}});
  try{
   const hash=(value:string)=>createHash('sha256').update(value).digest('hex');
   const markdown='## Preparation 🐑\n\nBring the brass key.\n\nCheck the lamp.';
   const editorJson=JSON.stringify(editor.getJSON()),selectionJson=JSON.stringify(editor.state.selection.toJSON());
   const original:PlanOriginalAuthoringCapture={schema:'dmb_plan_authoring_capture_v1',
    idempotency_key:'11111111-1111-4111-8111-111111111111',conversation_id:'22222222-2222-4222-8222-222222222222',
    expected_pointer_revision:1,world_id:'host-world',document_id:'host-document',base_revision:3,base_content_sha256:'a'.repeat(64),
    draft_markdown:markdown,draft_sha256:hash(markdown),editor_json:editorJson,editor_sha256:hash(editorJson),
    selection_json:selectionJson,selection_sha256:hash(selectionJson),from:editor.state.selection.from,to:editor.state.selection.to,
    draft_generation:1,selection_generation:1,target_kind:'insert_at_caret',selected_text:'',playable_target:null};
   const legacy=await capturePlanPlacementCatalog(editor,original);
   expect(legacy.schema).toBe('dmb_plan_placement_catalog_v1');
   const ordinary=await capturePlanPlacementCatalog(editor,original,true);
   expect(ordinary.schema).toBe('dmb_plan_placement_catalog_v2');
   const catalog=await capturePlanParagraphPlacementCatalog(editor,original);
   expect(ordinary).toEqual(catalog);
   expect(catalog.schema).toBe('dmb_plan_placement_catalog_v2');
   expect(catalog.entries.some(entry=>entry.kind==='after_paragraph')).toBe(true);
   expect(editor.getJSON()).toEqual(JSON.parse(editorJson));
   const projected=planParagraphPlacementModelChoices(catalog.entries);
   for(const field of ['host-world','host-document','source_root_index','root_boundary','target_capture_sha256'])
    expect(JSON.stringify(projected)).not.toContain(field);
   if(process.env.DMB_PLAN_CATALOG_EXPORT)
    await writeFile(process.env.DMB_PLAN_CATALOG_EXPORT,JSON.stringify({original_capture:original,catalog}),{flag:'wx'});
   const pending=capturePlanParagraphPlacementCatalog(editor,original);
   editor.commands.insertContentAt(editor.state.doc.content.size,p('Intervening edit.'));
   await expect(pending).rejects.toThrow(/page changed/);
   editor.commands.setTextSelection(1);
   expect(wrapPageRow(editor)).toBe(true);
   const composedJson=JSON.stringify(editor.getJSON()),composedSelection=JSON.stringify(editor.state.selection.toJSON());
   const composed={...original,editor_json:composedJson,editor_sha256:hash(composedJson),
    selection_json:composedSelection,selection_sha256:hash(composedSelection),
    from:editor.state.selection.from,to:editor.state.selection.to};
   const retained=await capturePlanPlacementCatalog(editor,composed,true);
   expect(retained.schema).toBe('dmb_plan_placement_catalog_v1');
   expect(retained.entries.some(entry=>entry.kind==='after_paragraph')).toBe(false);
   await expect(capturePlanParagraphPlacementCatalog(editor,composed)).rejects.toThrow(/plain Plan/);
  }finally{editor.destroy();}
 });
 it('uses exact root boundaries despite an unrelated caret and duplicate prose elsewhere, with Undo/Redo',()=>{
  withEditor([p('Unrelated opening.'),h(2,'Preparation'),p('Bring the brass key.'),
   p('Check the lamp.'),h(2,'Rumours'),p('Bring the brass key.')],editor=>{
   const before=editor.getJSON(),json=JSON.stringify(before),selection=editor.state.selection.toJSON();
   const options=compilePlanParagraphPlacementOptions(editor,json,'insert_at_caret');
   const entry=options.find(row=>row.kind==='after_paragraph'&&row.source_root_index===2)!;
   expect(entry.label).toBe('After paragraph in Preparation: Bring the brass key.');
   expect(options.filter(row=>row.kind==='after_paragraph'&&row.label.includes('Bring the brass key.'))).toHaveLength(2);
   expect(entry.root_boundary).toBe(3);expect(editor.state.doc.resolve(entry.position!).depth).toBe(0);
   expect(editor.state.selection.toJSON()).toEqual(selection);
   expect(resolvePlanParagraphPlacementOption(editor,json,'insert_at_caret',entry)).toEqual(entry);
   expect(editor.commands.insertContentAt(entry.position!,p('The gate locks at dusk.'))).toBe(true);
   const after=editor.getJSON();expect(after.content).toEqual([...before.content!.slice(0,3),p('The gate locks at dusk.'),...before.content!.slice(3)]);
   expect(editor.commands.undo()).toBe(true);expect(editor.getJSON()).toEqual(before);
   expect(editor.commands.redo()).toBe(true);expect(editor.getJSON()).toEqual(after);
  });
 });
 it('projects only opaque aliases and semantic labels while retaining legacy heading semantics',()=>{
  withEditor([h(2,'Preparation'),p('🗝️ Bring a key.'),h(3,'Details'),p('Leave quietly.'),h(2,'Next')],editor=>{
   const options=compilePlanParagraphPlacementOptions(editor,JSON.stringify(editor.getJSON()),'insert_at_caret');
   expect(options.find(row=>row.kind==='after_section'&&row.source_root_index===0)?.root_boundary).toBe(4);
   const choices=planParagraphPlacementModelChoices(options);
   expect(choices.every(row=>Object.keys(row).sort().join(',')==='label,selector')).toBe(true);
   expect(choices.every(row=>row.selector==='captured'||/^place[1-9][0-9]*$/.test(row.selector))).toBe(true);
   expect(new Set(choices.map(row=>row.selector)).size).toBe(choices.length);
   for(const kind of ['replace_selection','replace_playable_body'] as const)
    expect(compilePlanParagraphPlacementOptions(editor,JSON.stringify(editor.getJSON()),kind).map(row=>row.selector)).toEqual(['captured']);
  });
 });
 it('does not turn a named-table caption into a paragraph section',()=>{
  const table:JSONContent={type:'table',content:[{type:'tableRow',content:[{type:'tableCell',content:[p('Item')]}]}]};
  withEditor([h(2,'Preparation'),h(2,'Treasure'),table,p('Bring a key.')],editor=>{
   const options=compilePlanParagraphPlacementOptions(editor,JSON.stringify(editor.getJSON()),'insert_at_caret');
   expect(options.find(row=>row.kind==='after_paragraph')?.label).toBe('After paragraph in Preparation: Bring a key.');
   expect(options.some(row=>row.root_boundary===2)).toBe(false);
  });
 });
 it('refuses changed snapshots, substituted labels, roots and positions',()=>{
  withEditor([h(2,'Preparation'),p('Bring a key.'),p('Other prose.')],editor=>{
   const json=JSON.stringify(editor.getJSON());
   const entry=compilePlanParagraphPlacementOptions(editor,json,'insert_at_caret').find(row=>row.kind==='after_paragraph')!;
   for(const change of [{label:'Elsewhere'},{position:1},{source_root_index:2}])
    expect(()=>resolvePlanParagraphPlacementOption(editor,json,'insert_at_caret',{...entry,...change})).toThrow(/boundary/);
   editor.commands.insertContentAt(editor.state.doc.content.size,p('Intervening human edit.'));
   expect(()=>resolvePlanParagraphPlacementOption(editor,json,'insert_at_caret',entry)).toThrow(/page changed/);
  });
 });
});
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
   expect(entries.some(row=>row.selector==='before:2'||row.selector==='under:2'||row.selector==='after:2')).toBe(false);
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
   expect(entries).toHaveLength(212);
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

it.each([
 [h(2,'Preparation 🐑'),p('Existing body.'),h(3,'Nested notes'),p('Keep nested text.'),h(2,'Next')],
 [h(2,'Preparation'),h(3,'Nested notes'),p('Keep nested text.'),h(2,'Next')],
 [h(2,'Preparation')],
])('inserts directly below the heading before any existing body or nested section',(...content)=>{
 withEditor(content,editor=>{
  const before=editor.getJSON().content!,snapshot=JSON.stringify(editor.getJSON());
  const options=compilePlanPlacementOptions(editor,snapshot,'insert_at_caret');
  const under=options.find(row=>row.selector==='under:0')!;
  expect(under.root_boundary).toBe(1);
  expect(under.position).toBe(editor.state.doc.child(0).nodeSize);
  expect(editor.state.doc.resolve(under.position!).depth).toBe(0);
  expect(resolvePlanPlacementOption(editor,snapshot,'insert_at_caret',under)).toEqual(under);
  expect(editor.commands.insertContentAt(under.position!,p('New briefing.'))).toBe(true);
  expect(editor.getJSON().content).toEqual([before[0],p('New briefing.'),...before.slice(1)]);
 });
});
