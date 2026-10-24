import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {webcrypto} from 'node:crypto';
import {Editor} from '@tiptap/core';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../tiptap/MarkdownEditorCore';
import {tiptapJsonToSemanticMarkdown} from '../tiptap/markdown/calloutMarkdown';
import {createBuildComposeBridge,type BuildComposeEditorState} from './buildComposeBridge';
import {BuildPageProposal} from './BuildPageProposal';
import {proposalReview,type BuildProposalReview} from '../api/buildProposalReviewApi';
import type {BuildProposalRecord} from '../api/buildDocumentProposalApi';
vi.mock('../api/buildProposalReviewApi',()=>({proposalReview:vi.fn()}));
let editor:Editor;let state:BuildComposeEditorState;let bridge:ReturnType<typeof createBuildComposeBridge>;
let record:BuildProposalRecord;let saved:BuildProposalReview;let lostAck=false;let lostPrepare=false;
const status=vi.fn();const complete=vi.fn();
async function digest(text:string){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text))),value=>value.toString(16).padStart(2,'0')).join('');}
beforeEach(async()=>{
 vi.clearAllMocks();sessionStorage.clear();lostAck=false;lostPrepare=false;Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true});
 editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:'<p>Before</p><p>After</p>'});
 document.body.append(editor.view.dom);editor.commands.setTextSelection(7);
 state={editor,worldId:'world',documentId:'doc',revision:1,contentSha256:'a'.repeat(64),visibility:'internal',draftGeneration:0,selectionGeneration:0,canEdit:true};
 bridge=createBuildComposeBridge(()=>state,()=>undefined);const captured=await bridge.capture();
 record={schema_version:'dmb_build_document_proposal_v1',action_id:'action',reservation:{idempotency_key:'action',conversation_id:'conversation',expected_pointer_revision:1,basis:captured.basis,instruction:'Add culture'},
 request_fingerprint:'b'.repeat(64),after_turn_sequence:1,revision:5,state:'proposed',created_at:'',updated_at:'',claim_expires_at:'',authorization:null,failure_code:null,inserted_in_draft:false,
 proposal:{replacement_markdown:'## Culture\n\nA proposed custom.',summary:'Culture',assumptions:[]}};
 saved={schema:'dmb_build_proposal_review_v1',world_id:'world',action_id:'action',reservation_sha256:record.request_fingerprint,revision:1,state:'editing',markdown:record.proposal!.replacement_markdown,
 markdown_sha256:await digest(record.proposal!.replacement_markdown),apply:null,updated_at:''};
 vi.mocked(proposalReview).mockImplementation(async(_world,_action,command)=>{
  if(!command||command.operation==='open')return structuredClone(saved);
  if(command.expected_revision!==saved.revision)throw new Error('Saved suggestion changed');
  if(command.operation==='save')saved={...saved,revision:saved.revision+1,markdown:command.markdown!,markdown_sha256:await digest(command.markdown!)};
  if(command.operation==='discard')saved={...saved,revision:saved.revision+1,state:'discarded'};
  if(command.operation==='prepare')saved={...saved,revision:saved.revision+1,state:'applying',apply:{apply_id:command.apply_id!,before_editor_sha256:record.reservation.basis.editor_sha256!,before_draft_sha256:record.reservation.basis.draft_sha256,
   after_editor_sha256:command.after_editor_sha256!,after_draft_sha256:command.after_draft_sha256!,reviewed_sha256:saved.markdown_sha256}};
  if(command.operation==='prepare'&&lostPrepare)throw new Error('Prepared outcome unavailable');
  if(command.operation==='confirm'){if(lostAck)throw new Error('Acknowledgment unavailable');saved={...saved,revision:saved.revision+1,state:'applied'};}
  return structuredClone(saved);
 });
});
afterEach(()=>{cleanup();editor.destroy();editor.view.dom.remove();});
function Review({source='doc:1',request=0}:{source?:string;request?:number}){return <BuildPageProposal record={record} bridge={bridge} sourceKey={source} requestKey={request} onStatus={status} onComplete={complete} inspector={<p>Exact captured prompt</p>}/>;}
it('stages outside editor JSON, edits and keeps once at its original position with one Undo',async()=>{
 const before=editor.getJSON();render(<Review/>);
 await screen.findByRole('region',{name:'Proposed page change'});
 expect(editor.getJSON()).toEqual(before);expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).not.toContain('Culture');
 fireEvent.click(screen.getByRole('button',{name:'Edit suggestion'}));
 fireEvent.change(screen.getByRole('textbox',{name:'Suggestion Markdown'}),{target:{value:'## Culture\n\nAn authored revision.'}});
 expect(editor.getJSON()).toEqual(before);
 act(()=>editor.commands.setTextSelection(1));
 fireEvent.click(screen.getByRole('button',{name:'Keep on page'}));
 await waitFor(()=>expect(saved.state).toBe('applied'));
 const md=tiptapJsonToSemanticMarkdown(editor.getJSON());expect(md.indexOf('Before')).toBeLessThan(md.indexOf('An authored revision.'));expect(md.indexOf('An authored revision.')).toBeLessThan(md.indexOf('After'));
 expect(saved.markdown).toContain('An authored revision.');expect(complete).toHaveBeenCalledTimes(1);
 act(()=>editor.commands.undo());expect(editor.getJSON()).toEqual(before);
});
it('retains unsaved suggestion typing through remount without entering page content',async()=>{
 const before=editor.getJSON();const view=render(<Review/>);await screen.findByRole('button',{name:'Edit suggestion'});
 fireEvent.click(screen.getByRole('button',{name:'Edit suggestion'}));
 fireEvent.change(screen.getByRole('textbox',{name:'Suggestion Markdown'}),{target:{value:'My unfinished local copy'}});
 view.unmount();render(<Review/>);await screen.findByRole('button',{name:'Edit suggestion'});
 fireEvent.click(screen.getByRole('button',{name:'Edit suggestion'}));
 expect(screen.getByRole('textbox',{name:'Suggestion Markdown'})).toHaveValue('My unfinished local copy');expect(editor.getJSON()).toEqual(before);
 fireEvent.click(screen.getByRole('button',{name:'Save suggestion'}));
 await waitFor(()=>expect(saved.markdown).toBe('My unfinished local copy'));expect(editor.getJSON()).toEqual(before);
});
it('discards durably without changing page JSON or undo history',async()=>{
 const before=editor.getJSON();const view=render(<Review/>);await screen.findByRole('button',{name:'Discard suggestion'});
 fireEvent.click(screen.getByRole('button',{name:'Discard suggestion'}));await waitFor(()=>expect(saved.state).toBe('discarded'));
 expect(editor.getJSON()).toEqual(before);view.unmount();render(<Review/>);
 await waitFor(()=>expect(status).toHaveBeenLastCalledWith('Suggestion discarded'));
 expect(screen.queryByRole('region',{name:'Proposed page change'})).not.toBeInTheDocument();expect(editor.getJSON()).toEqual(before);
});
it('recovers lost acknowledgment by recognizing the result without a second insertion',async()=>{
 lostAck=true;const apply=vi.spyOn(bridge,'applyPrepared');const view=render(<Review/>);await screen.findByRole('button',{name:'Keep on page'});
 fireEvent.click(screen.getByRole('button',{name:'Keep on page'}));
 await screen.findByRole('button',{name:'Check insertion'});await screen.findByRole('alert');
 const after=editor.getJSON();expect(apply).toHaveBeenCalledTimes(1);expect(saved.state).toBe('applying');
 view.unmount();lostAck=false;render(<Review/>);
 fireEvent.click(await screen.findByRole('button',{name:'Check insertion'}));
 await waitFor(()=>expect(saved.state).toBe('applied'));expect(apply).toHaveBeenCalledTimes(1);expect(editor.getJSON()).toEqual(after);
});
it('rejects intervening page changes and removes stale placement without erasing writing',async()=>{
 render(<Review/>);await screen.findByRole('button',{name:'Keep on page'});
 act(()=>editor.commands.insertContent('My new page text.'));
 await screen.findByRole('status');expect(screen.queryByRole('button',{name:'Keep on page'})).not.toBeInTheDocument();
 expect(editor.getText()).toContain('My new page text.');expect(saved.state).toBe('editing');
});
it('leaves invalid Markdown editable without inserting it',async()=>{
 const before=editor.getJSON();render(<Review/>);await screen.findByRole('button',{name:'Edit suggestion'});
 fireEvent.click(screen.getByRole('button',{name:'Edit suggestion'}));fireEvent.change(screen.getByRole('textbox',{name:'Suggestion Markdown'}),{target:{value:'<script>bad</script>'}});
 fireEvent.click(screen.getByRole('button',{name:'Keep on page'}));await screen.findByRole('alert');expect(editor.getJSON()).toEqual(before);expect(saved.state).toBe('editing');
});

it('recovers a lost prepare response before any insertion, without reserving another apply',async()=>{
 lostPrepare=true;const apply=vi.spyOn(bridge,'applyPrepared');render(<Review/>);
 fireEvent.click(await screen.findByRole('button',{name:'Keep on page'}));
 await screen.findByRole('button',{name:'Check insertion'});expect(apply).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Check insertion'}));
 await waitFor(()=>expect(saved.state).toBe('applied'));expect(apply).toHaveBeenCalledTimes(1);
 expect(vi.mocked(proposalReview).mock.calls.filter(([, ,command])=>command?.operation==='prepare')).toHaveLength(1);
});
it('drops a late prepared response after a page switch without applying it to either page',async()=>{
 const send=vi.mocked(proposalReview).getMockImplementation()!;
 let finish!:(value:BuildProposalReview)=>void;
 vi.mocked(proposalReview).mockImplementation(async(world,action,command)=>{
  const result=await send(world,action,command);
  if(command?.operation==='prepare')return new Promise(resolve=>{finish=resolve;});
  return result;
 });
 const apply=vi.spyOn(bridge,'applyPrepared');const before=editor.getJSON();const view=render(<Review/>);
 fireEvent.click(await screen.findByRole('button',{name:'Keep on page'}));
 await waitFor(()=>expect(finish).toBeTypeOf('function'));
 state.documentId='other';view.rerender(<Review source="other:1"/>);
 await act(async()=>{finish(structuredClone(saved));});
 expect(apply).not.toHaveBeenCalled();expect(editor.getJSON()).toEqual(before);
 expect(await screen.findByRole('button',{name:'Check insertion'})).not.toBeDisabled();
});
it('retains conflicting local review text and requires a deliberate copy choice',async()=>{
 const view=render(<Review/>);fireEvent.click(await screen.findByRole('button',{name:'Edit suggestion'}));
 fireEvent.change(screen.getByRole('textbox',{name:'Suggestion Markdown'}),{target:{value:'My local copy'}});
 view.unmount();saved={...saved,revision:saved.revision+1,markdown:'A saved edit from elsewhere'};
 render(<Review/>);await screen.findByRole('button',{name:'Use saved suggestion'});
 expect(screen.getByRole('button',{name:'Keep on page'})).toBeDisabled();
 fireEvent.click(screen.getByRole('button',{name:'Review my local copy'}));
 fireEvent.click(screen.getByRole('button',{name:'Edit suggestion'}));
 expect(screen.getByRole('textbox',{name:'Suggestion Markdown'})).toHaveValue('My local copy');
 expect(saved.markdown).toBe('A saved edit from elsewhere');
});
