import userEvent from '@testing-library/user-event';
import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {webcrypto} from 'node:crypto';
import {Editor} from '@tiptap/core';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../tiptap/MarkdownEditorCore';
import {tiptapJsonToSemanticMarkdown} from '../tiptap/markdown/calloutMarkdown';
import {markdownToTiptapDoc} from '../tiptap/markdown/markdownToTiptap';
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
 vi.clearAllMocks();sessionStorage.clear();
 let pending=Promise.resolve();
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:vi.fn((_name:string,work:()=>Promise<unknown>)=>{
   const result=pending.then(work);pending=result.then(()=>undefined,()=>undefined);return result;
 })}});
 Object.defineProperty(Range.prototype,'getClientRects',{configurable:true,value:()=>[]});
 Object.defineProperty(Range.prototype,'getBoundingClientRect',{configurable:true,value:()=>({top:0,left:0,right:0,bottom:0,width:0,height:0})});
 Object.defineProperty(document,'elementFromPoint',{configurable:true,value:()=>screen.queryByRole('textbox',{name:'Suggestion text'})});lostAck=false;lostPrepare=false;Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true});
 editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:'<p>Before</p><p>After</p>'});
 document.body.append(editor.view.dom);editor.commands.setTextSelection(7);
 state={editor,worldId:'world',documentId:'doc',revision:1,contentSha256:'a'.repeat(64),visibility:'internal',draftGeneration:0,selectionGeneration:0,canEdit:true};
 bridge=createBuildComposeBridge(()=>state,()=>undefined,vi.fn(async()=>undefined));const captured=await bridge.capture();
 record={schema_version:'dmb_build_document_proposal_v1',action_id:'action',reservation:{idempotency_key:'action',conversation_id:'conversation',expected_pointer_revision:1,basis:captured.basis,instruction:'Add culture'},
 request_fingerprint:'b'.repeat(64),after_turn_sequence:1,revision:5,state:'proposed',created_at:'',updated_at:'',claim_expires_at:'',authorization:null,failure_code:null,inserted_in_draft:false,
 proposal:{replacement_markdown:'## Culture\n\nA proposed custom.',summary:'Culture',assumptions:[]}};
 saved={schema:'dmb_build_proposal_review_v2',world_id:'world',action_id:'action',reservation_sha256:record.request_fingerprint,placement_caret:7,revision:1,state:'editing',markdown:record.proposal!.replacement_markdown,
 markdown_sha256:await digest(record.proposal!.replacement_markdown),apply:null,updated_at:''};
 vi.mocked(proposalReview).mockImplementation(async(_world,_action,command)=>{
  if(!command||command.operation==='open')return structuredClone(saved);
  if(command.expected_revision!==saved.revision)throw new Error('Saved suggestion changed');
  if(command.operation==='save')saved={...saved,revision:saved.revision+1,markdown:command.markdown!,markdown_sha256:await digest(command.markdown!)};
  if(command.operation==='move')saved={...saved,revision:saved.revision+1,placement_caret:command.placement_caret!};
  if(command.operation==='discard')saved={...saved,revision:saved.revision+1,state:'discarded'};
  if(command.operation==='replace_placement')saved={...saved,schema:'dmb_build_proposal_review_v3',revision:saved.revision+1,
    placement:command.placement!,state:'editing',apply:null,placement_caret:command.placement!.basis.caret,
    retired_placements:[...(saved.retired_placements??[]),{basis:{...(saved.placement?.basis??record.reservation.basis),caret:saved.placement_caret},markdown:saved.markdown,
      markdown_sha256:saved.markdown_sha256,apply:saved.apply,command_id:saved.placement?.command_id??null,
      disposition:saved.apply?'superseded_unresolved':'superseded_unapplied'}]};
  if(command.operation==='prepare')saved={...saved,revision:saved.revision+1,state:'applying',apply:{...(saved.page_body_target?{page_body_target:saved.page_body_target}:{}),placement_caret:saved.placement_caret,apply_id:command.apply_id!,before_editor_sha256:(saved.placement?.basis??record.reservation.basis).editor_sha256!,before_draft_sha256:(saved.placement?.basis??record.reservation.basis).draft_sha256,
   after_editor_sha256:command.after_editor_sha256!,after_draft_sha256:command.after_draft_sha256!,reviewed_sha256:saved.markdown_sha256}};
  if(command.operation==='prepare'&&lostPrepare)throw new Error('Prepared outcome unavailable');
  if(command.operation==='confirm'){if(lostAck)throw new Error('Acknowledgment unavailable');saved={...saved,revision:saved.revision+1,state:'applied'};}
  return structuredClone(saved);
 });
});
afterEach(()=>{cleanup();editor.destroy();editor.view.dom.remove();Reflect.deleteProperty(Range.prototype,'getClientRects');Reflect.deleteProperty(Range.prototype,'getBoundingClientRect');Reflect.deleteProperty(document,'elementFromPoint');});
async function writeSuggestion(value:string){const box=await screen.findByRole('textbox',{name:'Suggestion text'});await userEvent.clear(box);await userEvent.type(box,value);}
function Review({source='doc:1',request=0}:{source?:string;request?:number}){return <BuildPageProposal record={record} bridge={bridge} sourceKey={source} requestKey={request} onStatus={status} onComplete={complete} inspector={<p>Exact captured prompt</p>}/>;}
it('stages outside editor JSON, edits and keeps once at its original position with one Undo',async()=>{
 const before=editor.getJSON();render(<Review/>);
 await screen.findByRole('region',{name:'Proposed page change'});
 expect(editor.getJSON()).toEqual(before);expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).not.toContain('Culture');

 await writeSuggestion('An authored revision.');
 expect(editor.getJSON()).toEqual(before);
 act(()=>editor.commands.setTextSelection(1));
 fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));
 await waitFor(()=>expect(saved.state).toBe('applied'));
 const md=tiptapJsonToSemanticMarkdown(editor.getJSON());expect(md.indexOf('Before')).toBeLessThan(md.indexOf('An authored revision.'));expect(md.indexOf('An authored revision.')).toBeLessThan(md.indexOf('After'));
 expect(saved.markdown).toContain('An authored revision.');expect(complete).toHaveBeenCalledTimes(1);
 act(()=>editor.commands.undo());expect(editor.getJSON()).toEqual(before);
});
it('retains unsaved suggestion typing through remount without entering page content',async()=>{
 const before=editor.getJSON();const view=render(<Review/>);await screen.findByRole('textbox',{name:'Suggestion text'});

 await writeSuggestion('My unfinished local copy');
 view.unmount();render(<Review/>);await screen.findByRole('textbox',{name:'Suggestion text'});

 expect(screen.getByRole('textbox',{name:'Suggestion text'})).toHaveTextContent('My unfinished local copy');expect(editor.getJSON()).toEqual(before);
 fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));
 await waitFor(()=>expect(saved.state).toBe('applied'));
 expect(saved.markdown.trim()).toBe('My unfinished local copy');
 expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toContain('My unfinished local copy');
});
it('discards durably without changing page JSON or undo history',async()=>{
 const before=editor.getJSON();const view=render(<Review/>);await screen.findByRole('button',{name:'Dismiss suggestion'});
 fireEvent.click(screen.getByRole('button',{name:'Dismiss suggestion'}));await waitFor(()=>expect(saved.state).toBe('discarded'));
 expect(editor.getJSON()).toEqual(before);view.unmount();render(<Review/>);
 await waitFor(()=>expect(status).toHaveBeenLastCalledWith('Suggestion discarded'));
 expect(screen.queryByRole('region',{name:'Proposed page change'})).not.toBeInTheDocument();expect(editor.getJSON()).toEqual(before);
});
it('recovers lost acknowledgment by recognizing the result without a second insertion',async()=>{
 lostAck=true;const apply=vi.spyOn(bridge,'applyPrepared');const view=render(<Review/>);await screen.findByRole('button',{name:'Save',exact:true});
 fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));
 await screen.findByRole('button',{name:'Check insertion'});await screen.findByRole('alert');
 const after=editor.getJSON();expect(apply).toHaveBeenCalledTimes(1);expect(saved.state).toBe('applying');
 view.unmount();lostAck=false;render(<Review/>);
 fireEvent.click(await screen.findByRole('button',{name:'Check insertion'}));
 await waitFor(()=>expect(saved.state).toBe('applied'));expect(apply).toHaveBeenCalledTimes(1);expect(editor.getJSON()).toEqual(after);
});
it('rejects intervening page changes and removes stale placement without erasing writing',async()=>{
 render(<Review/>);await screen.findByRole('button',{name:'Save',exact:true});
 act(()=>editor.commands.insertContent('My new page text.'));
 await screen.findByRole('status');expect(screen.queryByRole('button',{name:'Save',exact:true})).not.toBeInTheDocument();
 expect(editor.getText()).toContain('My new page text.');expect(saved.state).toBe('editing');
});
it('leaves invalid Markdown editable without inserting it',async()=>{
 const before=editor.getJSON();render(<Review/>);await screen.findByRole('textbox',{name:'Suggestion text'});
await writeSuggestion('<script>bad</script>');
 fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));await screen.findByRole('alert');expect(editor.getJSON()).toEqual(before);expect(saved.state).toBe('editing');
});

it('recovers a lost prepare response before any insertion, without reserving another apply',async()=>{
 lostPrepare=true;const apply=vi.spyOn(bridge,'applyPrepared');render(<Review/>);
 fireEvent.click(await screen.findByRole('button',{name:'Save',exact:true}));
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
 fireEvent.click(await screen.findByRole('button',{name:'Save',exact:true}));
 await waitFor(()=>expect(finish).toBeTypeOf('function'));
 state.documentId='other';view.rerender(<Review source="other:1"/>);
 await act(async()=>{finish(structuredClone(saved));});
 expect(apply).not.toHaveBeenCalled();expect(editor.getJSON()).toEqual(before);
 expect(await screen.findByRole('button',{name:'Check insertion'})).not.toBeDisabled();
});
it('retains conflicting local review text and requires a deliberate copy choice',async()=>{
 const view=render(<Review/>);fireEvent.click(await screen.findByRole('textbox',{name:'Suggestion text'}));
 await writeSuggestion('My local copy');
 view.unmount();saved={...saved,revision:saved.revision+1,markdown:'A saved edit from elsewhere'};
 render(<Review/>);await screen.findByRole('button',{name:'Use saved suggestion'});
 expect(screen.getByRole('button',{name:'Save',exact:true})).toBeDisabled();
 fireEvent.click(screen.getByRole('button',{name:'Review my local copy'}));

 expect(screen.getByRole('textbox',{name:'Suggestion text'})).toHaveTextContent('My local copy');
 expect(saved.markdown).toBe('A saved edit from elsewhere');
});

it('moves a directly edited suggestion without changing page bytes and retains its chosen position through reload',async()=>{
 const before=editor.getJSON();const view=render(<Review/>);await writeSuggestion('Authored custom.');
 const input=screen.getByRole('textbox',{name:'Suggestion text'});
 act(()=>editor.commands.setTextSelection(1));
 fireEvent.click(screen.getByRole('button',{name:'Move',exact:true}));
 vi.spyOn(editor.view,'posAtCoords').mockReturnValue({pos:editor.state.selection.from,inside:0});
 fireEvent.click(editor.view.dom,{clientX:10,clientY:10});
 await waitFor(()=>expect(saved.placement_caret).toBe(1));
 expect(editor.getJSON()).toEqual(before);
 expect(screen.getByRole('textbox',{name:'Suggestion text'})).toBe(input);
 expect(input).toHaveTextContent('Authored custom.');
 view.unmount();render(<Review/>);await screen.findByRole('button',{name:'Save',exact:true});
 fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));
 await waitFor(()=>expect(saved.state).toBe('applied'));
 const md=tiptapJsonToSemanticMarkdown(editor.getJSON());
 expect(md.indexOf('Authored custom.')).toBeLessThan(md.indexOf('Before'));
 expect(saved.apply?.placement_caret).toBe(1);
 act(()=>editor.commands.undo());expect(editor.getJSON()).toEqual(before);
});
it('recovers a lost move response by reading the saved placement, never repeating the move',async()=>{
 const send=vi.mocked(proposalReview).getMockImplementation()!;
 vi.mocked(proposalReview).mockImplementation(async(world,action,command)=>{const result=await send(world,action,command);if(command?.operation==='move')throw new Error('Move response unavailable');return result;});
 render(<Review/>);await screen.findByRole('textbox',{name:'Suggestion text'});
 act(()=>editor.commands.setTextSelection(0));fireEvent.click(screen.getByRole('button',{name:'Move',exact:true}));
 vi.spyOn(editor.view,'posAtCoords').mockReturnValue({pos:editor.state.selection.from,inside:0});
 fireEvent.click(editor.view.dom,{clientX:10,clientY:10});
 await screen.findByRole('alert');await waitFor(()=>expect(screen.getByRole('button',{name:'Save',exact:true})).toBeEnabled());
 fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));await waitFor(()=>expect(saved.state).toBe('applied'));
 expect(saved.apply?.placement_caret).toBe(1);
 expect(vi.mocked(proposalReview).mock.calls.filter(([, ,command])=>command?.operation==='move')).toHaveLength(1);
});
it('accepts only this suggestion drag on the unchanged page without inserting drag DOM',async()=>{
 const before=editor.getJSON();render(<Review/>);await screen.findByRole('textbox',{name:'Suggestion text'});
 vi.spyOn(editor.view,'posAtCoords').mockReturnValue({pos:0,inside:-1});
 const transfer=(id:string)=>({types:['application/x-dmb-page-proposal'],getData:()=>id});
 fireEvent.drop(editor.view.dom,{dataTransfer:transfer('another-action'),clientX:10,clientY:10});
 expect(vi.mocked(proposalReview).mock.calls.some(([, ,command])=>command?.operation==='move')).toBe(false);
 fireEvent.drop(editor.view.dom,{dataTransfer:transfer(record.action_id),clientX:10,clientY:10});
 await waitFor(()=>expect(saved.placement_caret).toBe(0));expect(editor.getJSON()).toEqual(before);
});
it('reveals and focuses the requested proposal region in context',async()=>{
 const scroll=vi.fn();Object.defineProperty(HTMLElement.prototype,'scrollIntoView',{configurable:true,value:scroll});
 try{render(<Review request={1}/>);const host=await screen.findByRole('region',{name:'Proposed page change'});
 await waitFor(()=>expect(document.activeElement).toBe(host));expect(scroll).toHaveBeenCalledWith({block:'center',behavior:'auto'});
 }finally{Reflect.deleteProperty(HTMLElement.prototype,'scrollIntoView');}
});

it.each([{key:'End',ctrlKey:true},{key:'ArrowDown',metaKey:true}])('keeps document navigation and subsequent typing inside the suggestion: %j',async keys=>{
 const before=editor.getJSON();const selection=editor.state.selection.toJSON();render(<Review/>);
 const input=await screen.findByRole('textbox',{name:'Suggestion text'});input.focus();
 fireEvent.keyDown(input,keys);
 expect(document.activeElement).toBe(input);
 expect(input.contains(window.getSelection()?.anchorNode??null)).toBe(true);
 await userEvent.keyboard(' Authored ending.');
 expect(input).toHaveTextContent('Authored ending.');
 expect(editor.getJSON()).toEqual(before);expect(editor.state.selection.toJSON()).toEqual(selection);
});
it.each([{key:'Home',ctrlKey:true},{key:'ArrowUp',metaKey:true}])('owns extended document selection inside the suggestion: %j',async keys=>{
 const before=editor.getJSON();render(<Review/>);const input=await screen.findByRole('textbox',{name:'Suggestion text'});input.focus();
 fireEvent.keyDown(input,{key:'End',ctrlKey:true});fireEvent.keyDown(input,{...keys,shiftKey:true});
 expect(document.activeElement).toBe(input);expect(input.contains(window.getSelection()?.anchorNode??null)).toBe(true);
 expect(window.getSelection()?.toString()).toContain('Culture');expect(window.getSelection()?.toString()).toContain('A proposed custom.');
 expect(editor.getJSON()).toEqual(before);
});


it.each([false,true])('keeps an explicitly labelled selected-passage revision and recovers acknowledgment: %s',async lose=>{
 editor.commands.setTextSelection({from:1,to:7});
 const captured=await bridge.capture();record.reservation.basis=captured.basis;saved.placement_caret=captured.basis.caret;
 const before=editor.getJSON();lostAck=lose;
 const view=render(<Review/>);
 await screen.findByText('Replaces your selected passage when you Save.');
 expect(screen.queryByRole('button',{name:'Drag suggestion'})).not.toBeInTheDocument();
 expect(editor.getJSON()).toEqual(before);
 await writeSuggestion('Revised passage');
 fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));
 if(lose){
  await screen.findByRole('button',{name:'Check insertion'});await screen.findByRole('alert');
  const after=editor.getJSON();view.unmount();lostAck=false;render(<Review/>);
  fireEvent.click(await screen.findByRole('button',{name:'Check insertion'}));
  await waitFor(()=>expect(saved.state).toBe('applied'));expect(editor.getJSON()).toEqual(after);
 }else await waitFor(()=>expect(saved.state).toBe('applied'));
 expect(editor.getText()).not.toContain('Before');expect(editor.getText()).toContain('After');
 expect(editor.getText().match(/Revised passage/g)).toHaveLength(1);
 act(()=>editor.commands.undo());expect(editor.getJSON()).toEqual(before);
});


it('keeps a staged proposal after its exact captured draft is saved and the review reopens',async()=>{
 const before=editor.getJSON();const view=render(<Review/>);
 await screen.findByRole('button',{name:'Save',exact:true});
 view.unmount();state.revision+=1;state.contentSha256=record.reservation.basis.draft_sha256;
 render(<Review source="doc:2"/>);
 fireEvent.click(await screen.findByRole('button',{name:'Save',exact:true}));
 await waitFor(()=>expect(saved.state).toBe('applied'));
 expect(editor.getText()).toContain('A proposed custom.');
 expect(editor.getText()).toContain('Before');expect(editor.getText()).toContain('After');
 expect(vi.mocked(proposalReview).mock.calls.filter(([, ,command])=>command?.operation==='prepare')).toHaveLength(1);
 act(()=>editor.commands.undo());expect(editor.getJSON()).toEqual(before);
});


it('recovers a lost prepare after the unchanged draft saves without preparing or inserting twice',async()=>{
 lostPrepare=true;const apply=vi.spyOn(bridge,'applyPrepared');const view=render(<Review/>);
 fireEvent.click(await screen.findByRole('button',{name:'Save',exact:true}));
 await screen.findByRole('button',{name:'Check insertion'});expect(apply).not.toHaveBeenCalled();
 view.unmount();state.revision+=1;state.contentSha256=record.reservation.basis.draft_sha256;
 render(<Review source="doc:2"/>);
 fireEvent.click(await screen.findByRole('button',{name:'Check insertion'}));
 await waitFor(()=>expect(saved.state).toBe('applied'));expect(apply).toHaveBeenCalledTimes(1);
 expect(vi.mocked(proposalReview).mock.calls.filter(([, ,command])=>command?.operation==='prepare')).toHaveLength(1);
});


it('offers only Save, with details under Debug and a small dismiss control',async()=>{
 record.proposal!.assumptions=['A proposed custom'];render(<Review/>);
 await screen.findByRole('button',{name:'Save',exact:true});
 expect(screen.queryByRole('button',{name:'Keep on page'})).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Save suggestion'})).not.toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Dismiss suggestion'})).toHaveTextContent('×');
 expect(screen.queryByText('A proposed custom')).not.toBeInTheDocument();
 fireEvent.click(screen.getByText('Debug',{exact:true}));
 await screen.findByText('A proposed custom');
});
it('cancels click placement without moving or changing text and removes its listeners',async()=>{
 const before=editor.getJSON();const view=render(<Review/>);await writeSuggestion('My suggestion');
 const point=vi.spyOn(editor.view,'posAtCoords').mockReturnValue({pos:1,inside:0});
 fireEvent.click(screen.getByRole('button',{name:'Move',exact:true}));
 expect(editor.view.dom).toHaveClass('is-suggestion-placement-target');
 fireEvent.keyDown(document,{key:'Escape'});
 expect(editor.view.dom).not.toHaveClass('is-suggestion-placement-target');
 fireEvent.click(editor.view.dom,{clientX:10,clientY:10});
 expect(saved.placement_caret).toBe(7);expect(editor.getJSON()).toEqual(before);
 fireEvent.click(screen.getByRole('button',{name:'Move',exact:true}));
 view.unmount();point.mockClear();fireEvent.click(editor.view.dom,{clientX:10,clientY:10});
 expect(point).not.toHaveBeenCalled();expect(editor.view.dom).not.toHaveClass('is-suggestion-placement-target');
});


it('does not let a queued reveal steal focus after suggestion typing begins',async()=>{
 const frames:FrameRequestCallback[]=[];
 const raf=vi.spyOn(window,'requestAnimationFrame').mockImplementation(callback=>{frames.push(callback);return frames.length;});
 try{
  render(<Review request={1}/>);
  const box=await screen.findByRole('textbox',{name:'Suggestion text'});
  box.focus();expect(document.activeElement).toBe(box);
  act(()=>{for(const callback of frames.splice(0))callback(0);});
  expect(document.activeElement).toBe(box);
  await userEvent.type(box,' Still writing.');
  expect(box).toHaveTextContent('Still writing.');
 }finally{raf.mockRestore();}
});

it('waits for verified page persistence before confirming and recovers a failed save without reinserting',async()=>{
 let rejectSave:(reason:Error)=>void=()=>{};
 const persist=vi.spyOn(bridge,'saveProposal').mockImplementationOnce(()=>new Promise((_resolve,reject)=>{rejectSave=reject;}));
 const apply=vi.spyOn(bridge,'applyPrepared');render(<Review/>);
 fireEvent.click(await screen.findByRole('button',{name:'Save',exact:true}));
 await waitFor(()=>expect(persist).toHaveBeenCalledTimes(1));
 expect(saved.state).toBe('applying');expect(complete).not.toHaveBeenCalled();
 expect(vi.mocked(proposalReview).mock.calls.some(([, ,command])=>command?.operation==='confirm')).toBe(false);
 await act(async()=>rejectSave(new Error('The page save was not verified.')));
 await screen.findByRole('button',{name:'Check insertion'});expect(saved.state).toBe('applying');
 fireEvent.click(screen.getByRole('button',{name:'Check insertion'}));
 await waitFor(()=>expect(saved.state).toBe('applied'));expect(apply).toHaveBeenCalledTimes(1);expect(persist).toHaveBeenCalledTimes(2);
 expect(status).toHaveBeenCalledWith('Saved to page');
});


it('explicitly places retained edited text on a newer page while keeping the uncertain receipt',async()=>{
 lostAck=true;
 const view=render(<Review/>);await writeSuggestion('My retained cedar-box sentence.');
 fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));
 await screen.findByRole('button',{name:'Check insertion'});await screen.findByRole('alert');
 const uncertain=structuredClone(saved.apply);
 act(()=>{editor.commands.setContent('<p>Newer author writing.</p>');state.revision=2;state.contentSha256='d'.repeat(64);state.draftGeneration++;});
 view.rerender(<Review source="doc:2"/>);await screen.findByRole('button',{name:'Choose a new position'});
 vi.spyOn(bridge,'pickInsertion').mockImplementation(async()=>bridge.capture());
 const before=editor.getJSON();
 fireEvent.click(screen.getByRole('button',{name:'Choose a new position'}));
 await screen.findByRole('textbox',{name:'Suggestion text'});
 expect(editor.getJSON()).toEqual(before);
 expect(saved.retired_placements?.[0].apply).toEqual(uncertain);
 const debug=screen.getByText('Debug').closest('details')!;debug.open=true;fireEvent(debug,new Event('toggle'));
 expect(await screen.findByText('Earlier insertion attempts · 1')).toBeInTheDocument();
 expect(screen.getByText(/Superseded · outcome unresolved/)).toBeInTheDocument();
 expect(screen.getByRole('textbox',{name:'Suggestion text'})).toHaveTextContent('My retained cedar-box sentence.');
 lostAck=false;
 fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));
 await waitFor(()=>expect(saved.state).toBe('applied'));
 expect(editor.getText()).toContain('Newer author writing.');
 expect(editor.getText().match(/My retained cedar-box sentence/g)).toHaveLength(1);
 expect(saved.apply?.apply_id).not.toBe(uncertain?.apply_id);
 expect(saved.apply?.before_editor_sha256).toBe(saved.placement?.basis.editor_sha256);
 expect(bridge.pickInsertion).toHaveBeenCalledTimes(1);
});

it('holds the tab lock through delayed prepare, then refuses an old callback on newer writing',async()=>{
 const send=vi.mocked(proposalReview).getMockImplementation()!;
 let finish!:(value:BuildProposalReview)=>void;
 vi.mocked(proposalReview).mockImplementation(async(world,action,command)=>{
   const result=await send(world,action,command);
   if(command?.operation==='prepare')return new Promise(resolve=>{finish=resolve;});
   return result;
 });
 const first=render(<Review/>);
 fireEvent.click(await screen.findByRole('button',{name:'Save',exact:true}));
 await waitFor(()=>expect(finish).toBeTypeOf('function'));
 act(()=>{editor.commands.setContent('<p>Newer tab writing.</p>');state.revision=2;state.contentSha256='d'.repeat(64);state.draftGeneration++;});
 const newer=editor.getJSON();
 let secondEntered=false;
 const queued=navigator.locks.request('dmb:proposal-review:world:action',async()=>{secondEntered=true;});
 await act(async()=>{await Promise.resolve();});
 expect(secondEntered).toBe(false);
 await act(async()=>{finish(structuredClone(saved));await queued;});
 expect(secondEntered).toBe(true);
 expect(editor.getJSON()).toEqual(newer);
 expect(saved.state).toBe('applying');
 expect(complete).not.toHaveBeenCalled();
 first.unmount();
});

it('refuses a stale recovery callback after another placement superseded its receipt',async()=>{
 lostAck=true;const view=render(<Review/>);
 fireEvent.click(await screen.findByRole('button',{name:'Save',exact:true}));
 await screen.findByRole('button',{name:'Check insertion'});await screen.findByRole('alert');
 const original=editor.getJSON();const apply=vi.spyOn(bridge,'applyPrepared');apply.mockClear();
 // Simulate another tab publishing a newer placement while this panel remains open.
 saved={...saved,revision:saved.revision+1,state:'editing',apply:null};
 fireEvent.click(screen.getByRole('button',{name:'Check insertion'}));
 await screen.findByRole('status',{name:'Suggestion placement unavailable'});
 expect(screen.getByRole('status',{name:'Suggestion placement unavailable'})).toHaveTextContent('retained');
 expect(apply).not.toHaveBeenCalled();expect(editor.getJSON()).toEqual(original);
 view.unmount();
});


it('shows a proposal outside a hidden table-title heading without changing its saved insertion point',async()=>{
 editor.commands.setContent(markdownToTiptapDoc('## Quarry Households\n\n| Household | Task |\n| --- | --- |\n| Copper House | Repair the hook. |').doc);
 editor.commands.setTextSelection(1);
 const captured=await bridge.capture();record.reservation.basis=captured.basis;saved.placement_caret=captured.basis.caret;
 const before=editor.getJSON();render(<Review/>);
 const proposal=await screen.findByRole('region',{name:'Proposed page change'});
 // Named-table presentation hides the source heading. Its review must be a sibling,
 // not a descendant that inherits that hidden state.
 expect(proposal.parentElement).toBe(editor.view.dom);
 expect(editor.view.dom.querySelector(':scope > h2')).toHaveTextContent('Quarry Households');
 expect(editor.getJSON()).toEqual(before);
 fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));
 await waitFor(()=>expect(saved.state).toBe('applied'));
 expect(saved.apply?.placement_caret).toBe(1);
 const markdown=tiptapJsonToSemanticMarkdown(editor.getJSON());
 expect(markdown).toContain('Quarry Households');expect(markdown).toContain('Repair the hook.');
 expect(markdown.match(/A proposed custom\./g)).toHaveLength(1);
 act(()=>editor.commands.undo());expect(editor.getJSON()).toEqual(before);
});

it('acknowledges the same saved result after spacer recovery without another insertion or Save',async()=>{
 editor.commands.setContent('<p></p><p>Before</p><p>After</p>');editor.commands.setTextSelection(editor.state.doc.content.size-1);
 state.draftGeneration++;
 const captured=await bridge.capture();record.reservation.basis=captured.basis;saved.placement_caret=captured.basis.caret;
 const apply=vi.spyOn(bridge,'applyPrepared');
 const persist=vi.spyOn(bridge,'saveProposal').mockRejectedValueOnce(new Error('Source is protected; review current page.'));
 render(<Review/>);fireEvent.click(await screen.findByRole('button',{name:'Save',exact:true}));
 await screen.findByRole('button',{name:'Check insertion'});await screen.findByRole('alert');
 const originalReceipt=structuredClone(saved.apply);
 const body=tiptapJsonToSemanticMarkdown(editor.getJSON());expect(await digest(body)).toBe(originalReceipt!.after_draft_sha256);
 act(()=>{editor.commands.setContent(markdownToTiptapDoc(body).doc);state.draftGeneration++;state.revision=2;state.contentSha256=originalReceipt!.after_draft_sha256;});
 const {saveBuildProposal}=await import('./saveBuildProposal');
 const api=await import('../api/liveApi');
 const {fixtureWorkspaceDocumentRecord}=await import('../planSurface/config/planSessionDescriptor');
 const sourceRecord=fixtureWorkspaceDocumentRecord({document_id:'doc',world_id:'world',kind:'worldbuilding_source',revision:2,content_status:'committed'});
 const snapshot={schema_version:'dmb_workspace_document_snapshot_v1' as const,record:sourceRecord,markdown:body,content_sha256:await digest(body),file_fingerprint:'saved-file',file_exists:true,loaded_revision:2};
 const saveMarkdown=vi.fn();const owner={documentId:'doc',editor,snapshot,saveMarkdown};
 const sourceRead=vi.spyOn(api,'getWorkspaceDocumentSnapshot').mockResolvedValue(snapshot);
 persist.mockImplementation((basis,afterEditor,afterDraft,projection)=>saveBuildProposal(()=>owner,basis,afterEditor,afterDraft,projection));
 const currentJson=editor.getJSON(),docChanges=vi.fn();editor.on('transaction',({transaction})=>{if(transaction.docChanged)docChanges();});
 fireEvent.click(screen.getByRole('button',{name:'Check insertion'}));
 await waitFor(()=>expect(saved.state).toBe('applied'));
 expect(saveMarkdown).not.toHaveBeenCalled();expect(apply).toHaveBeenCalledTimes(1);expect(sourceRead).toHaveBeenCalledTimes(1);
 expect(docChanges).not.toHaveBeenCalled();expect(editor.getJSON()).toEqual(currentJson);expect(saved.apply).toEqual(originalReceipt);
 expect(editor.getText().match(/A proposed custom/g)).toHaveLength(1);expect(complete).toHaveBeenCalledWith('applied');
 sourceRead.mockRestore();
});


it('reviews the whole body explicitly and recovers a lost save acknowledgment without appending',async()=>{
 const captured=await bridge.capture();
 record.reservation.page_body_offer=captured.pageBodyOffer;
 record.proposal!.target='page_body';
 record.proposal!.replacement_markdown='Preparation only.\n\nOffer communication first.';
 saved={...saved,page_body_target:captured.pageBodyOffer,markdown:record.proposal!.replacement_markdown,
   markdown_sha256:await digest(record.proposal!.replacement_markdown)};
 lostAck=true;
 const view=render(<Review/>);await screen.findByText('Replaces the entire page body when you Save.');
 fireEvent.click(screen.getByText('Original page body'));
 expect(screen.getByText(/Before\s+After/)).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));
 await waitFor(()=>expect(saved.state).toBe('applying'));
 await screen.findByRole('button',{name:'Check insertion'});
 expect(screen.queryByRole('button',{name:'Choose a new position'})).not.toBeInTheDocument();
 expect(editor.getJSON().content).toHaveLength(2);
 expect(editor.getText()).toBe('Preparation only.\n\nOffer communication first.');
 const after=editor.getJSON();view.unmount();lostAck=false;render(<Review/>);
 fireEvent.click(await screen.findByRole('button',{name:'Check insertion'}));
 await waitFor(()=>expect(saved.state).toBe('applied'));
 expect(editor.getJSON()).toEqual(after);
 expect(vi.mocked(proposalReview).mock.calls.filter(([, ,cmd])=>cmd?.operation==='prepare')).toHaveLength(1);
});
