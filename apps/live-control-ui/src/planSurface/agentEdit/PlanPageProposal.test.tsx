import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeAll,expect,it,vi} from 'vitest';
import {Editor} from '@tiptap/core';
import {webcrypto} from 'node:crypto';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../../tiptap/MarkdownEditorCore';
import {markdownToTiptapDoc} from '../../tiptap/markdown/markdownToTiptap';
import * as api from '../../api/planAuthoringReviewApi';
import {captureWorldPlanEditTarget,sealWorldPlanAuthoringTarget,type WorldPlanEditEditorState} from './planAgentEditProposal';
import {PlanPageProposal} from './PlanPageProposal';

const editors:Editor[]=[];
beforeAll(()=>Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto}));
afterEach(()=>{cleanup();for(const editor of editors.splice(0))editor.destroy();sessionStorage.clear();vi.restoreAllMocks();document.body.innerHTML='';});
async function setup(){
  const host=document.createElement('div');document.body.append(host);
  const markdown='# Plan\n\nExisting body.';
  const editor=new Editor({element:host,extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:markdownToTiptapDoc(markdown).doc});editors.push(editor);
  const world='world-a',documentId='plan-a',action='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
  const identity={idempotencyKey:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',conversationId:'cccccccc-cccc-4ccc-8ccc-cccccccccccc',pointerRevision:1};
  const state:WorldPlanEditEditorState={editor,worldId:world,documentId,baseRevision:2,baseContentSha256:'a'.repeat(64),sourceMarkdown:markdown,draftGeneration:0,selectionGeneration:0,canEdit:true};
  const target=await captureWorldPlanEditTarget(state,()=>state);
  const capture=await sealWorldPlanAuthoringTarget(target,identity);
  const proposal={schema:'dmb_plan_authored_proposal_v1',capture,replacement_markdown:'A proposed cue.',
    origin:{action_id:action,conversation_id:identity.conversationId,idempotency_key:identity.idempotencyKey}} as api.PlanAuthoredProposal;
  let saved:api.PlanAuthoringReview={schema:'dmb_plan_authoring_review_v1',world_id:world,action_id:action,origin_sha256:'b'.repeat(64),revision:1,state:'editing',markdown:proposal.replacement_markdown,markdown_sha256:'c'.repeat(64),capture,applications:[],last_command_id:identity.idempotencyKey,last_command_sha256:'d'.repeat(64),updated_at:'2026-11-05T00:00:00Z'};
  const read=vi.spyOn(api,'readPlanAuthoringReview').mockImplementation(async()=>({schema:'dmb_plan_authoring_review_snapshot_v1',world_id:world,action_id:action,origin_sha256:saved.origin_sha256,review:saved}));
  const command=vi.spyOn(api,'commandPlanAuthoringReview').mockImplementation(async(_world,_action,request)=>{
    saved={...saved,revision:saved.revision+1,last_command_id:request.command_id};
    if(request.operation==='save')saved={...saved,markdown:request.markdown};
    if(request.operation==='discard')saved={...saved,state:'discarded'};
    if(request.operation==='prepare')saved={...saved,state:'applying',applications:[{...request,capture,markdown:saved.markdown} as unknown as api.PlanReviewApplication]};
    if(request.operation==='confirm')saved={...saved,state:'applied'};
    return saved;
  });
  const bridge={capture:vi.fn(async()=>target),apply:vi.fn(),captureAuthoring:vi.fn(async()=>({capture,target})),
    restoreAuthoring:vi.fn(async()=>({capture,target})),authoringTitle:()=> 'Plan',
    prepareAuthoring:vi.fn(async()=>({admitted:{canonicalMarkdown:'A proposed cue.'},afterEditorJson:JSON.stringify(editor.getJSON()),afterEditorSha256:'e'.repeat(64),afterMarkdown:markdown,afterDraftSha256:'f'.repeat(64)})),
    saveAuthoring:vi.fn(async(...args:any[])=>args.at(-1)())};
  const props={proposal,bridge:bridge as any,identity,expectedBinding:{worldId:world,documentId,threadId:identity.conversationId,namespace:'test'},getBinding:()=>({} as any),disabled:false,onVisible:vi.fn()};
  return {editor,props,bridge,command,read,world,action,proposal,getSaved:()=>saved,setSaved:(value:api.PlanAuthoringReview)=>{saved=value;}};
}

it('shows a retained native suggestion and calls the Save owner only after explicit Save',async()=>{
  const h=await setup();render(<PlanPageProposal {...h.props}/>);
  await screen.findByRole('textbox',{name:'Suggestion text'});
  expect(h.bridge.saveAuthoring).not.toHaveBeenCalled();expect(h.command).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Save'}));
  await screen.findByText('Suggestion saved on the Plan.');
  expect(h.bridge.prepareAuthoring).toHaveBeenCalledTimes(1);expect(h.bridge.saveAuthoring).toHaveBeenCalledTimes(1);
  expect(h.command.mock.calls.map(call=>call[2].operation)).toEqual(['move','prepare','confirm']);
  expect(h.bridge.apply).not.toHaveBeenCalled();
});

it('retires the visual placement when the page changes and preserves the suggestion for recovery',async()=>{
  const h=await setup();const view=render(<PlanPageProposal {...h.props}/>);
  await screen.findByRole('textbox',{name:'Suggestion text'});
  await act(async()=>h.editor.commands.insertContent('New author draft.'));
  await waitFor(()=>expect(screen.queryByRole('textbox',{name:'Suggestion text'})).not.toBeInTheDocument());
  expect(h.bridge.saveAuthoring).not.toHaveBeenCalled();expect(h.getSaved().state).toBe('editing');
  view.unmount();render(<PlanPageProposal {...h.props}/>);
  await screen.findByText(/The page changed/);
  expect(h.command).not.toHaveBeenCalled();expect(h.editor.getText()).toContain('New author draft.');
});

it('retains an uncertain command and retries its exact identity without automatically repeating Save',async()=>{
  const h=await setup();h.command.mockRejectedValueOnce(new Error('Synthetic response lost'));
  const view=render(<PlanPageProposal {...h.props}/>);await screen.findByRole('textbox',{name:'Suggestion text'});
  fireEvent.click(screen.getByRole('button',{name:'Save'}));await screen.findByText('Synthetic response lost');
  const original=h.command.mock.calls[0]![2];expect(h.bridge.saveAuthoring).not.toHaveBeenCalled();
  view.unmount();render(<PlanPageProposal {...h.props}/>);
  const retry=await screen.findByRole('button',{name:'Retry exact move operation'});
  expect(h.command).toHaveBeenCalledTimes(1);fireEvent.click(retry);
  await waitFor(()=>expect(h.command).toHaveBeenCalledTimes(2));
  expect(h.command.mock.calls[1]![2]).toEqual(original);expect(h.bridge.saveAuthoring).not.toHaveBeenCalled();
});

it('keeps a discarded suggestion terminal after reload without recreating placement',async()=>{
  const h=await setup();let view=render(<PlanPageProposal {...h.props}/>);
  await screen.findByRole('textbox',{name:'Suggestion text'});fireEvent.click(screen.getByRole('button',{name:'Dismiss suggestion'}));
  await screen.findByText('Suggestion discarded.');view.unmount();view=render(<PlanPageProposal {...h.props}/>);
  await screen.findByText('Suggestion discarded.');expect(screen.queryByRole('button',{name:'Save'})).not.toBeInTheDocument();
  expect(h.command.mock.calls.map(call=>call[2].operation)).toEqual(['discard']);expect(h.bridge.saveAuthoring).not.toHaveBeenCalled();
});


it('refuses Save when the current target cannot restore its committed basis',async()=>{
  const h=await setup();render(<PlanPageProposal {...h.props}/>);await screen.findByRole('textbox',{name:'Suggestion text'});
  h.bridge.restoreAuthoring.mockRejectedValueOnce(new Error('The committed Plan changed.'));
  fireEvent.click(screen.getByRole('button',{name:'Save'}));await screen.findByText('The committed Plan changed.');
  expect(h.bridge.prepareAuthoring).not.toHaveBeenCalled();expect(h.bridge.saveAuthoring).not.toHaveBeenCalled();expect(h.command).not.toHaveBeenCalled();
  expect(h.getSaved().state).toBe('editing');
});
