import {Editor} from '@tiptap/core';
import {expect,it} from 'vitest';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../../tiptap/MarkdownEditorCore';
import {markdownToTiptapDoc} from '../../tiptap/markdown/markdownToTiptap';
import {tiptapJsonToSemanticMarkdown} from '../../tiptap/markdown/calloutMarkdown';
import {moveWorkPlan} from './workPlanObjectMove';
import {workPlanFence,type WorkPlanReference} from './workPlanReference';
const ref:WorkPlanReference={schema:'dmb_surface_work_plan_ref_v1',world_id:'world',document_id:'page',conversation_id:'11111111-1111-4111-8111-111111111111',source_turn_id:'22222222-2222-4222-8222-222222222222',source_answer_sha256:'a'.repeat(64),title:'Plan'};
it('moves the exact atomic reference and undo restores its old position',()=>{
 const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:markdownToTiptapDoc('Before.\n\n'+workPlanFence(ref)+'\n\nAfter.').doc});
 try{
  const before=tiptapJsonToSemanticMarkdown(editor.getJSON()),from=editor.state.doc.firstChild!.nodeSize;
  expect(moveWorkPlan(editor.view,from,editor.state.doc.content.size)).toBe(true);
  expect(editor.getJSON().content?.at(-1)?.type).toBe('surfaceWorkPlan');
  expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toContain(workPlanFence(ref));
  editor.commands.undo();expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toBe(before);
 }finally{editor.destroy();}
});
it('refuses movement in a read-only editor or into an inline position',()=>{
 const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:markdownToTiptapDoc(workPlanFence(ref)+'\n\nAfter.').doc});
 try{const original=JSON.stringify(editor.getJSON());expect(moveWorkPlan(editor.view,0,2)).toBe(false);editor.setEditable(false);expect(moveWorkPlan(editor.view,0,editor.state.doc.content.size)).toBe(false);expect(JSON.stringify(editor.getJSON())).toBe(original);}finally{editor.destroy();}
});
