import {Editor,type JSONContent} from '@tiptap/core';
import {describe,it,expect} from 'vitest';
import {PAGE_COMPOSER_EXTENSIONS} from '../../apps/live-control-ui/src/tiptap/pageComposer/PageRow';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../../apps/live-control-ui/src/tiptap/MarkdownEditorCore';
import {captureProseTargetCatalog,resolveProseTarget,type ProseTargetState} from '../../apps/live-control-ui/src/documentEditing/proseTargetCatalog';
import {insertReviewedMarkdownAtAnchor} from '../../apps/live-control-ui/src/documentEditing/markdownInsertion';
const p=(text:string):JSONContent=>({type:'paragraph',content:[{type:'text',text}]});
const h=(text:string):JSONContent=>({type:'heading',attrs:{level:2},content:[{type:'text',text}]});
function setup(){
 const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:{type:'doc',content:[h('Overview'),p('Do not change.'),h('Preparation'),p('The scouts returned silently.'),h('Opening Beat'),p('The scouts returned silently.')]}});
 editor.commands.setTextSelection(1);
 const state:ProseTargetState={editor,scopeKey:'synthetic:page:revision1',draftGeneration:0,canEdit:true};
 return {editor,state,get:()=>state};
}
describe('prose target host catalog (no model selector or Save integration)',()=>{
 it('offers distinct occurrences with section context, without using or changing caret',()=>{
  const {editor,get}=setup();try{
   const before=editor.getJSON(),catalog=captureProseTargetCatalog(get);
   const matches=catalog.choices.filter(x=>x.operation==='replace_paragraph'&&x.passage==='The scouts returned silently.');
   expect(matches.map(x=>x.section)).toEqual(['Preparation','Opening Beat']);
   expect(matches[0]!.selector).not.toBe(matches[1]!.selector);
   expect(editor.state.selection.from).toBe(1);expect(editor.getJSON()).toEqual(before);
   expect(JSON.stringify(catalog)).not.toMatch(/scopeKey|revision1|editorJson|draftGeneration|"from"|"to"/);
   expect(Object.isFrozen(catalog.choices)).toBe(true);expect(Object.isFrozen(matches[0])).toBe(true);
  }finally{editor.destroy();}
 });
 it('resolves a nominated paragraph into existing reviewed insertion helper; preserves all other nodes and Undo',()=>{
  const {editor,get}=setup();try{
   const before=editor.getJSON(),catalog=captureProseTargetCatalog(get);
   const option=catalog.choices.find(x=>x.section==='Preparation'&&x.operation==='replace_paragraph')!;
   const target=resolveProseTarget(catalog,option.selector,get);
   editor.commands.setTextSelection(editor.state.doc.content.size-1);
   expect(resolveProseTarget(catalog,option.selector,get)).toEqual(target);
   insertReviewedMarkdownAtAnchor(editor,{from:target.from,to:target.to},[p('The scouts returned without speaking.')],target.editorJson);
   expect(editor.getJSON().content).toEqual([...before.content!.slice(0,3),p('The scouts returned without speaking.'),...before.content!.slice(4)]);
   expect(()=>resolveProseTarget(catalog,option.selector,get)).toThrow();
   editor.commands.undo();expect(editor.getJSON()).toEqual(before);
  }finally{editor.destroy();}
 });
 it('adds only at an offered root boundary, not incidental caret',()=>{
  const {editor,get}=setup();try{
   const before=editor.getJSON(),catalog=captureProseTargetCatalog(get);
   const option=catalog.choices.find(x=>x.section==='Preparation'&&x.operation==='insert_after')!;
   const target=resolveProseTarget(catalog,option.selector,get);
   insertReviewedMarkdownAtAnchor(editor,target.from,[p('A lone watcher keeps vigil.')],target.editorJson);
   expect(editor.getJSON().content).toEqual([...before.content!.slice(0,4),p('A lone watcher keeps vigil.'),...before.content!.slice(4)]);
  }finally{editor.destroy();}
 });
 it.each(['scope','generation','permission','silent-readonly','edit','forged','unknown'] as const)('refuses %s without mutation',kind=>{
  const {editor,state,get}=setup();try{
   const catalog=captureProseTargetCatalog(get),selector=catalog.choices[0]!.selector;
   if(kind==='scope')state.scopeKey='other';
   if(kind==='generation')state.draftGeneration++;
   if(kind==='permission')state.canEdit=false;
   if(kind==='silent-readonly')editor.setEditable(false,false);
   if(kind==='edit')editor.commands.insertContentAt(editor.state.doc.content.size,p('Human edit.'));
   const before=editor.getJSON();
   expect(()=>resolveProseTarget(kind==='forged'?{choices:catalog.choices}:catalog,kind==='unknown'?'offset:17':selector,get)).toThrow();
   expect(editor.getJSON()).toEqual(before);
  }finally{editor.destroy();}
 });
 it('resolves text extent inside the real composer paragraph without replacing its identity',()=>{
  const editor=new Editor({extensions:[...DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,...PAGE_COMPOSER_EXTENSIONS],content:{type:'doc',content:[{...p('Original text.'),attrs:{pageBlockId:'original-occurrence'}}]}});
  const state:ProseTargetState={editor,scopeKey:'synthetic',draftGeneration:0,canEdit:true};
  try{
   const before=editor.getJSON(),catalog=captureProseTargetCatalog(()=>state);
   const option=catalog.choices.find(x=>x.operation==='replace_paragraph')!;
   const target=resolveProseTarget(catalog,option.selector,()=>state);
   expect(target.from).toBe(1);expect(target.to).toBe(editor.state.doc.child(0).nodeSize-1);
   editor.view.dispatch(editor.state.tr.insertText('Revised text.',target.from,target.to));
   expect(editor.getJSON().content![0]!.attrs).toEqual(before.content![0]!.attrs);
   editor.commands.undo();expect(editor.getJSON()).toEqual(before);
  }finally{editor.destroy();}
 });
 it('does not mistake a table caption for the containing section',()=>{
  const {editor,get}=setup();try{
   editor.commands.setContent({type:'doc',content:[h('Preparation'),h('Named table'),{type:'table',content:[{type:'tableRow',content:[{type:'tableCell',content:[p('Cue')]}]}]},p('Trailing preparation prose.')]});
   const options=captureProseTargetCatalog(get).choices;
   expect(options).toHaveLength(3);expect(options.every(x=>x.section==='Preparation')).toBe(true);
  }finally{editor.destroy();}
 });
 it('does not offer nested list paragraphs, marked links or table-adjacent caption paragraphs',()=>{
  const {editor,get}=setup();try{
   editor.commands.setContent({type:'doc',content:[{type:'paragraph',content:[{type:'text',text:'Cited',marks:[{type:'link',attrs:{href:'https://example.test/source'}}]}]},{type:'bulletList',content:[{type:'listItem',content:[p('Nested.')]}]},p('Caption'),{type:'table',content:[{type:'tableRow',content:[{type:'tableCell',content:[p('Cell')]}]}]}]});
   expect(captureProseTargetCatalog(get).choices).toEqual([]);
  }finally{editor.destroy();}
 });
});
