import React from 'react';
import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {webcrypto} from 'node:crypto';
import {Editor,type JSONContent} from '@tiptap/core';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../../apps/live-control-ui/src/tiptap/MarkdownEditorCore';
import {PAGE_COMPOSER_EXTENSIONS} from '../../apps/live-control-ui/src/tiptap/pageComposer/PageRow';
import {projectPresentation,hydratePresentation} from '../../apps/live-control-ui/src/tiptap/pageComposer/presentation';
import {tiptapJsonToSemanticMarkdown} from '../../apps/live-control-ui/src/tiptap/markdown/calloutMarkdown';
import {createBuildComposeBridge,type BuildComposeEditorState} from '../../apps/live-control-ui/src/buildSurface/buildComposeBridge';
import {BuildPageProposal} from '../../apps/live-control-ui/src/buildSurface/BuildPageProposal';
import type {BuildProposalRecord} from '../../apps/live-control-ui/src/api/buildDocumentProposalApi';
const transport=vi.hoisted(()=>({fetch:globalThis.fetch,base:'http://127.0.0.1:15567',holdPrepare:null as null|(()=>Promise<void>),prepareArrived:false}));
vi.mock('../../apps/live-control-ui/src/api/liveApi',async importOriginal=>{
 const actual=await importOriginal<typeof import('../../apps/live-control-ui/src/api/liveApi')>();
 return {...actual,authenticatedApiFetch:async(url:string,init?:RequestInit)=>{
  const match=url.match(/^\/api\/live\/agent\/worlds\/[^/]+\/build-proposals\/([^/]+)\/review$/);
  if(!match)throw new Error('Proof adapter refuses non-review route: '+url);
  const response=await transport.fetch(transport.base+'/review/'+match[1],{...init,headers:{'Content-Type':'application/json'}});
  if(init?.body&&JSON.parse(String(init.body)).operation==='prepare'&&transport.holdPrepare){transport.prepareArrived=true;await transport.holdPrepare();}
  return {response};
 }};
});
async function request(path:string,body?:unknown){
 const response=await transport.fetch(transport.base+path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});
 const value=await response.json();if(!response.ok)throw new Error(JSON.stringify(value));return value;
}
const p=(text:string,id:string):JSONContent=>({type:'paragraph',attrs:{pageBlockId:id},content:[{type:'text',text,...(id==='opening'?{marks:[{type:'link',attrs:{href:'https://example.test/synthetic-source'}}]}:{})}]});
const h=(text:string,id:string):JSONContent=>({type:'heading',attrs:{level:2,pageBlockId:id},content:[{type:'text',text}]});
const editors:Editor[]=[];
afterEach(()=>{cleanup();for(const editor of editors){editor.destroy();editor.view.dom.remove();}editors.length=0;sessionStorage.clear();});
it('scripted paragraph-boundary alias -> native insertion review -> explicit Save -> cold editor reopen',async()=>{
 vi.stubGlobal('crypto',webcrypto);
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_name:string,work:()=>unknown)=>work()}});
 Object.defineProperty(Range.prototype,'getClientRects',{configurable:true,value:()=>[]});
 Object.defineProperty(Range.prototype,'getBoundingClientRect',{configurable:true,value:()=>({top:0,left:0,right:0,bottom:0,width:0,height:0})});
 Object.defineProperty(document,'elementFromPoint',{configurable:true,value:()=>screen.queryByRole('textbox',{name:'Suggestion text'})});
 const editor=new Editor({extensions:[...DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,...PAGE_COMPOSER_EXTENSIONS],content:{type:'doc',content:[
  h('Overview','overview'),p('Untouched opening.','opening'),h('Preparation','preparation'),p('The scouts returned silently.','intended'),
  h('Opening Beat','beat'),p('The scouts returned silently.','duplicate'),{type:'pageRow',attrs:{id:'untouched-row',min_height:0,line_mode:'clean'},content:[{type:'pageSlot',attrs:{id:'untouched-slot',width:12},content:[p('Untouched playable row.','row-text')]}]}
 ]}});editors.push(editor);document.body.append(editor.view.dom);editor.commands.setTextSelection(1);
 const before=editor.getJSON();const initialMd=tiptapJsonToSemanticMarkdown(before);
 const initial=projectPresentation(before,initialMd,before);
 const source=await request('/bootstrap',{markdown:initial.markdown,page_presentation:initial.presentation});
 const state:BuildComposeEditorState={editor,worldId:source.world_id,documentId:source.document_id,revision:source.registry_revision,contentSha256:source.content_sha256,visibility:'internal',draftGeneration:0,selectionGeneration:0,canEdit:true};
 editor.on('transaction',({transaction})=>{if(transaction.docChanged)state.draftGeneration++;});
 let saves=0;
 const bridge=createBuildComposeBridge(()=>state,()=>{},async(basis,afterEditor,afterDraft)=>{
  const digest=async(text:string)=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text))),n=>n.toString(16).padStart(2,'0')).join('');
  expect(await digest(JSON.stringify(editor.getJSON()))).toBe(afterEditor);
  expect(await digest(tiptapJsonToSemanticMarkdown(editor.getJSON()))).toBe(afterDraft);
  const projected=projectPresentation(editor.getJSON(),source.markdown,before);
  const saved=await request('/save',{basis,markdown:projected.markdown,page_presentation:projected.presentation});
  state.revision=saved.registry_revision;state.contentSha256=saved.content_sha256;saves++;
 },{allowProseBoundaries:true});
 let catalog=await bridge.captureProseTargets!();
 const selected=catalog.choices.find(x=>x.section==='Preparation'&&x.operation==='insert_after')!;
 expect(catalog.choices.filter(x=>x.passage==='The scouts returned silently.'&&x.operation==='insert_after')).toHaveLength(2);
 // Scripted alias is a deterministic host control, not ordinary model routing.
 let captured=await bridge.captureProseInsertion!(catalog,selected.selector);
 expect(captured.basis.caret).toBe(1);expect(captured.basis.selection).toBeUndefined();
 // Native draft transaction/Undo before any proposal or source Save.
 const trial=await bridge.prepareProposal(captured,'A lone watcher keeps vigil.');
 bridge.applyPrepared(trial);expect(saves).toBe(0);
 expect((await request('/page')).markdown).toBe(source.markdown);
 editor.commands.undo();expect(editor.getJSON()).toEqual(before);
 expect(()=>bridge.applyPrepared(trial)).toThrow();
 editor.commands.setTextSelection(1);
 catalog=await bridge.captureProseTargets!();captured=await bridge.captureProseInsertion!(catalog,selected.selector);
 const record=await request('/fixture',{basis:captured.basis,draft_markdown:captured.draftMarkdown,editor_json:captured.editorJson,
  prose_target:captured.proseTarget,catalog_choices:catalog.choices,replacement_markdown:'A lone watcher keeps vigil.'}) as BuildProposalRecord;
 expect(record.schema_version).toBe('dmb_build_document_proposal_v3');
 expect((await request('/page')).markdown).toBe(source.markdown);
 const status=vi.fn(),complete=vi.fn();
 const component=(enabled:boolean)=><BuildPageProposal record={record} bridge={bridge} sourceKey="synthetic" requestKey={1} inspector={null} onStatus={status} onComplete={complete} allowProseBoundaries={enabled}/>;
 const view=render(component(false));
 await screen.findByText(/requires an enabled proof reader/);expect(editor.getJSON()).toEqual(before);expect(saves).toBe(0);
 view.rerender(component(true));
 await screen.findByRole('textbox',{name:'Suggestion text'});
 expect(editor.getJSON()).toEqual(before);expect(saves).toBe(0);
 let release!:()=>void;const held=new Promise<void>(resolve=>{release=resolve;});
 transport.holdPrepare=()=>held;transport.prepareArrived=false;
 fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));
 await waitFor(()=>expect(transport.prepareArrived).toBe(true));
 view.rerender(component(false));await screen.findByText(/requires an enabled proof reader/);
 await act(async()=>{release();await held;});transport.holdPrepare=null;
 expect(editor.getJSON()).toEqual(before);expect(saves).toBe(0);expect(complete).not.toHaveBeenCalled();
 expect((await request('/page')).markdown).toBe(source.markdown);
 view.rerender(component(true));
 fireEvent.click(await screen.findByRole('button',{name:'Check insertion',exact:true}));
 await waitFor(()=>expect(complete).toHaveBeenCalledWith('applied'),{timeout:10000});
 const after=editor.getJSON();expect(saves).toBe(1);
 expect(after.content!.filter((_,i)=>i!==4)).toEqual(before.content);
 expect(editor.state.doc.child(3).textContent).toBe('The scouts returned silently.');
 expect(editor.state.doc.child(4).textContent).toBe('A lone watcher keeps vigil.');
 expect(editor.state.doc.child(5).textContent).toBe('Opening Beat');
 expect(after.content![4]!.attrs!.pageBlockId).toMatch(/^page-prose-/);
 const review=await request('/review/'+record.action_id);
 expect(review.schema).toBe('dmb_build_proposal_review_v5');expect(review.prose_target).toEqual(record.reservation.prose_target);
 expect(review.placement_caret).toBe(1);expect(review.placement).toBeUndefined();
 expect(review.apply.placement_caret).toBe(1);expect(review.apply.prose_target).toEqual(review.prose_target);expect(review.state).toBe('applied');
 const durable=await request('/page');expect(durable.registry_revision).toBeGreaterThan(source.registry_revision);
 expect((await request('/page')).markdown).toBe(durable.markdown);
 view.unmount();editor.destroy();editor.view.dom.remove();editors.splice(editors.indexOf(editor),1);
 const reopened=new Editor({extensions:[...DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,...PAGE_COMPOSER_EXTENSIONS],content:hydratePresentation(durable.markdown,durable.page_presentation)});editors.push(reopened);
 expect(reopened.getJSON()).toEqual(after);
 expect((await request('/record/'+record.action_id)).inserted_in_draft).toBe(true);
 const again=await request('/review/'+record.action_id,{operation:'confirm',expected_revision:review.revision,apply_id:review.apply.apply_id});
 expect(again.revision).toBe(review.revision);expect((await request('/page')).registry_revision).toBe(durable.registry_revision);
},30000);
