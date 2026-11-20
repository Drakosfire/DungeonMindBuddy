import {Editor} from '@tiptap/core';
import {expect,it} from 'vitest';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../../tiptap/MarkdownEditorCore';
import {markdownToTiptapDoc} from '../../tiptap/markdown/markdownToTiptap';
import {tiptapJsonToSemanticMarkdown} from '../../tiptap/markdown/calloutMarkdown';
import {semanticMarkdownSerializationDiagnostics} from '../../tiptap/markdown/semanticMarkdownSafety';
import {admitMarkdownInsertion} from '../../documentEditing/markdownInsertion';
import {workPlanFence,type WorkPlanReference} from './workPlanReference';
const ref:WorkPlanReference={schema:'dmb_surface_work_plan_ref_v1',world_id:'world',document_id:'page',conversation_id:'11111111-1111-4111-8111-111111111111',source_turn_id:'22222222-2222-4222-8222-222222222222',source_answer_sha256:'a'.repeat(64),title:'Workshop plan'};
it('survives the real editor and canonical Markdown without copying step state',()=>{
 const markdown='# Workshop\n\n'+workPlanFence(ref)+'\n\nAuthor text.';
 const parsed=markdownToTiptapDoc(markdown);expect(parsed.diagnostics).toEqual([]);
 const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:parsed.doc});
 try{
  expect(editor.getJSON().content?.[1]?.type).toBe('surfaceWorkPlan');
  expect(semanticMarkdownSerializationDiagnostics(editor.getJSON())).toEqual([]);
  expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toBe(markdown+'\n');
  expect(markdownToTiptapDoc(tiptapJsonToSemanticMarkdown(editor.getJSON())).diagnostics).toEqual([]);
 }finally{editor.destroy();}
});
it('refuses duplicate same-plan objects even if page titles differ',()=>{
 const parsed=markdownToTiptapDoc(workPlanFence(ref)+'\n\n'+workPlanFence({...ref,title:'Another title'}));
 expect(parsed.diagnostics.some(item=>item.level==='warning')).toBe(true);
 expect(semanticMarkdownSerializationDiagnostics(parsed.doc).length).toBeGreaterThan(0);
 expect(()=>tiptapJsonToSemanticMarkdown(parsed.doc)).toThrow(/Duplicate/);
});
it('does not admit HTML as an executable work-plan reference',()=>{
 const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:'<section data-surface-work-plan="'+ref.source_turn_id+'">Copied HTML</section>'});
 try{expect(JSON.stringify(editor.getJSON())).not.toContain('surfaceWorkPlan');}finally{editor.destroy();}
});
it('rejects model-generated reference fences at the inert insertion boundary',()=>{
 expect(()=>admitMarkdownInsertion(workPlanFence(ref))).toThrow();
});
