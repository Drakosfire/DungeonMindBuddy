import {proposalReview} from '../../api/buildProposalReviewApi';
import { act, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
import { beforeEach, expect, it, vi } from 'vitest';
import * as api from '../../api/buildDocumentProposalApi';
import * as live from '../../api/liveApi';
import * as media from '../../media/PreparedBuildImage';
import type { WorldAgentConversationHistoryResponse } from '../../api/types';
import type { CapturedBuildInsertion, BuildComposeBridge } from '../../buildSurface/buildComposeBridge';
import { BuildComposeProposal, useBuildCompose } from './BuildComposeProposal';
vi.mock('../../api/buildProposalReviewApi',()=>({proposalReview:vi.fn()}));
vi.mock('../../api/buildDocumentProposalApi', () => ({ composeBuildProposal: vi.fn(), getBuildProposal: vi.fn(),
  getBuildProposalPrompt: vi.fn(), listBuildProposals: vi.fn(), reportBuildInsertion: vi.fn() }));
vi.mock('../../api/liveApi', () => ({ getWorldAgentConversationHistory: vi.fn(), postWorldAgentNewConversation: vi.fn(), getWorldAgentNewConversationStatus:vi.fn(), getWorldAgentTurnPrompt: vi.fn() }));
const basis = { world_id: 'world', document_id: 'doc', registry_revision: 1, content_sha256: 'a'.repeat(64),
  draft_sha256: 'b'.repeat(64), editor_sha256: 'e'.repeat(64), visibility: 'internal' as const, caret: 1, draft_generation: 0, selection_generation: 0 };
const history: WorldAgentConversationHistoryResponse = { schema: 'dmb_agent_conversation_history_v1', world_id: 'world', conversation_state: 'active',
  conversation_id: 'conversation', active_conversation_id: 'conversation', pointer_revision: 1, turns: [], next_before_sequence: null };
const captured = { basis, draftMarkdown: '# Edge', editorJson: '{}', editor: {} } as CapturedBuildInsertion;
function receipt(request?: api.BuildProposalRequest): api.BuildProposalRecord {
  return { schema_version: 'dmb_build_document_proposal_v1', action_id: request?.idempotency_key ?? 'action',
    reservation: request ?? { idempotency_key: 'action', conversation_id: 'conversation', expected_pointer_revision: 1, basis: {...basis}, instruction: 'Create a table' },
    request_fingerprint: 'c'.repeat(64), after_turn_sequence: 0, revision: 5, state: 'proposed', created_at: '', updated_at: '', claim_expires_at: '',
    authorization: null, failure_code: null, inserted_in_draft: false,
    proposal: { replacement_markdown: '| NPC | Job |\n| --- | --- |\n| Nella | Baker |', summary: 'Proposed NPC', assumptions: ['Invented'] } };
}
let bridge: BuildComposeBridge;
beforeEach(() => {
  vi.resetAllMocks();window.localStorage.clear(); bridge = { captureContext:vi.fn(async()=>({schema:'dmb_build_draft_snapshot_v1' as const,
    world_id:basis.world_id,document_id:basis.document_id,registry_revision:basis.registry_revision,
    content_sha256:basis.content_sha256,visibility:basis.visibility,draft_markdown:captured.draftMarkdown,
    draft_sha256:basis.draft_sha256,editor_sha256:basis.editor_sha256,draft_generation:basis.draft_generation})), capture: vi.fn().mockResolvedValue(captured), restore: vi.fn().mockResolvedValue(captured), insert: vi.fn(), insertProposal: vi.fn(), prepareProposal:vi.fn(), applyPrepared:vi.fn(), inspectProposal:vi.fn(), saveProposal:vi.fn() };
  vi.mocked(api.listBuildProposals).mockResolvedValue([]);
  vi.spyOn(media, 'listPreparedImages').mockResolvedValue([]);
  vi.mocked(api.composeBuildProposal).mockImplementation(async request => receipt(request));
  vi.mocked(api.reportBuildInsertion).mockImplementation(async (_world, record) => ({ ...record, inserted_in_draft: true }));
});
it('does not refetch conversation sidecars for turn lifecycle changes, but refreshes on explicit request or conversation change', async () => {
  const firstHistory = { ...history, turns: [{ turn_id: 'turn-1', sequence: 1, lifecycle_status: 'running' }] } as WorldAgentConversationHistoryResponse;
  const hook = renderHook(({ snapshot }) => useBuildCompose({ worldId: 'world', pageDocumentId:'doc', history: snapshot, bridge, enabled: true, onHistory: vi.fn() }),
    { initialProps: { snapshot: firstHistory } });
  await waitFor(() => {
    expect(api.listBuildProposals).toHaveBeenCalledTimes(1);
    expect(media.listPreparedImages).toHaveBeenCalledTimes(1);
  });

  act(() => hook.rerender({ snapshot: { ...firstHistory, turns: [{ ...firstHistory.turns[0], lifecycle_status: 'completed' }] } }));
  expect(api.listBuildProposals).toHaveBeenCalledTimes(1);
  expect(media.listPreparedImages).toHaveBeenCalledTimes(1);

  act(() => hook.result.current.refresh());
  await waitFor(() => {
    expect(api.listBuildProposals).toHaveBeenCalledTimes(2);
    expect(media.listPreparedImages).toHaveBeenCalledTimes(2);
  });

  act(() => hook.rerender({ snapshot: { ...firstHistory, conversation_id: 'conversation-next', active_conversation_id: 'conversation-next' } }));
  await waitFor(() => {
    expect(api.listBuildProposals).toHaveBeenCalledTimes(3);
    expect(media.listPreparedImages).toHaveBeenCalledTimes(3);
  });
});
it('keeps generated prose out of conversation and exposes the page-owned review', async () => {
  const hook = renderHook(() => useBuildCompose({worldId:'world',pageDocumentId:'doc',history,bridge,enabled:true,onHistory:vi.fn()}));
  await act(async()=>{await hook.result.current.submit('Create a table');});
  render(<>{hook.result.current.items.map(item=>item.element)}</>);
  expect(screen.getByRole('button',{name:'Review suggestion on page'})).toBeInTheDocument();
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
  expect(hook.result.current.pageElement).not.toBeNull();
  expect(api.composeBuildProposal).toHaveBeenCalledTimes(1);
});
it('opens the first durable World conversation before composing', async () => {
  vi.mocked(live.postWorldAgentNewConversation).mockResolvedValue({ schema: 'dmb_agent_new_conversation_response_v1', world_id: 'world',
    conversation_id: 'conversation', active_conversation_id: 'conversation', pointer_revision: 1 });
  vi.mocked(live.getWorldAgentConversationHistory).mockResolvedValue(history);
  const hook = renderHook(() => {
    const [value, setValue] = useState<WorldAgentConversationHistoryResponse>({ ...history, conversation_id: null, active_conversation_id: null, pointer_revision: 0, conversation_state: 'absent' });
    return useBuildCompose({ worldId: 'world', pageDocumentId:'doc', history: value, bridge, enabled: true, onHistory: setValue });
  });
  await act(async () => { await hook.result.current.submit('Create a table'); });
  expect(live.postWorldAgentNewConversation).toHaveBeenCalledTimes(1);
  expect(api.composeBuildProposal).toHaveBeenCalledWith(expect.objectContaining({ conversation_id: 'conversation', expected_pointer_revision: 1 }));
  expect(hook.result.current.items).toHaveLength(1);
});
it('does not replay an uncertain provider operation', async () => {
  vi.mocked(api.composeBuildProposal).mockRejectedValue(new Error('Unknown outcome'));
  vi.mocked(api.getBuildProposal).mockResolvedValue({ ...receipt(), state: 'unknown', proposal: null });
  const hook = renderHook(() => useBuildCompose({ worldId: 'world', pageDocumentId:'doc', history, bridge, enabled: true, onHistory: vi.fn() }));
  await act(async () => { await hook.result.current.submit('Create a table'); });
  expect(api.composeBuildProposal).toHaveBeenCalledTimes(1);
  expect(api.getBuildProposal).toHaveBeenCalledTimes(1);
  expect(hook.result.current.error).toContain('Unknown outcome');
});
it('discards an old result after World A → B → A', async () => {
  let finish!: (value: api.BuildProposalRecord) => void;
  let request!: api.BuildProposalRequest;
  vi.mocked(api.composeBuildProposal).mockImplementation(value => { request = value; return new Promise(resolve => { finish = resolve; }); });
  const hook = renderHook(({ world }) => useBuildCompose({ worldId: world, pageDocumentId:'doc', history: { ...history, world_id: world }, bridge, enabled: true, onHistory: vi.fn() }), { initialProps: { world: 'world' } });
  let pending!: Promise<boolean>;
  act(() => { pending = hook.result.current.submit('Create a table'); });
  await waitFor(() => expect(api.composeBuildProposal).toHaveBeenCalledTimes(1));
  hook.rerender({ world: 'foreign' }); hook.rerender({ world: 'world' });
  await act(async () => { finish(receipt(request)); await pending; });
  expect(hook.result.current.items).toHaveLength(0);
});
it('keeps reopened proposals readable without executable editor authority', () => {
  render(<BuildComposeProposal record={receipt()} />);
  expect(screen.getByRole('table')).toHaveTextContent('Nella');
  expect(screen.queryByRole('button', { name: 'Insert into page' })).not.toBeInTheDocument();
});

it.each([true, false])('places a Harness proposal after its requesting turn when loaded: %s', async matching => {
  const record = receipt();
  record.after_turn_sequence = 4;
  record.reservation.origin = {client_turn_id: 'client', durable_turn_id: 'requesting-turn', turn_attempt: 1,
    broker_operation_id: 'operation', arguments_sha256: 'a'.repeat(64)};
  vi.mocked(api.listBuildProposals).mockResolvedValue([record]);
  const loaded = {...history, turns: [{turn_id: matching ? 'requesting-turn' : 'unrelated-turn', sequence: 5}]} as WorldAgentConversationHistoryResponse;
  const hook = renderHook(() => useBuildCompose({worldId: 'world', pageDocumentId:'doc', history: loaded, bridge, enabled: true, onHistory: vi.fn()}));
  await waitFor(() => expect(hook.result.current.items).toHaveLength(1));
  expect(hook.result.current.items[0].afterSequence).toBe(matching ? 5 : 4);
  render(<>{hook.result.current.items[0].element}</>);
  expect(screen.queryByText('Writing details')).not.toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Review suggestion on page'})).toBeInTheDocument();
});

it('keeps a historical proposal readable without manufacturing an original anchor', async () => {
  const old = receipt(); delete old.reservation.basis.editor_sha256;
  vi.mocked(api.listBuildProposals).mockResolvedValue([old]);
  const hook = renderHook(() => useBuildCompose({ worldId: 'world', pageDocumentId:'doc', history, bridge, enabled: true, onHistory: vi.fn() }));
  await waitFor(() => expect(hook.result.current.items).toHaveLength(1));
  render(<>{hook.result.current.items.map(item => item.element)}</>);
  const details=screen.getByText('Earlier page suggestion').closest('details')!;
  details.open=true;fireEvent(details,new Event('toggle'));
  expect(screen.getByRole('table')).toHaveTextContent('Nella');
  expect(screen.queryByRole('button', {name: /Insert/})).not.toBeInTheDocument();
  expect(bridge.restore).not.toHaveBeenCalled();
});

it('reopens the author-reviewed text separately from original generated prose',async()=>{
 const record=receipt();record.inserted_in_draft=true;
 vi.mocked(api.listBuildProposals).mockResolvedValue([record]);
 vi.mocked(proposalReview).mockResolvedValue({schema:'dmb_build_proposal_review_v2',world_id:'world',action_id:'action',reservation_sha256:record.request_fingerprint,
  placement_caret:1,revision:4,state:'applied',markdown:'The author’s retained review edit.',markdown_sha256:'a'.repeat(64),apply:null,updated_at:''});
 const hook=renderHook(()=>useBuildCompose({worldId:'world',pageDocumentId:'doc',history,bridge,enabled:true,onHistory:vi.fn()}));
 await waitFor(()=>expect(hook.result.current.items).toHaveLength(1));
 render(<>{hook.result.current.items.map(item=>item.element)}</>);
 expect(hook.result.current.pageElement).toBeNull();expect(proposalReview).not.toHaveBeenCalled();
 const details=screen.getByText('Kept page suggestion').closest('details')!;details.open=true;fireEvent(details,new Event('toggle'));
 expect(await screen.findByText('The author’s retained review edit.')).toBeInTheDocument();
 expect(screen.queryByText('Authored suggestion for your page')).not.toBeInTheDocument();
});

it('stages only the current page and reuses the same World proposal read across page navigation',async()=>{
 const first=receipt();first.action_id='first';first.created_at='2026-10-23T00:00:00Z';
 const second=receipt();second.action_id='second';second.created_at='2026-10-23T00:01:00Z';second.reservation={...second.reservation,basis:{...second.reservation.basis,document_id:'other'}};
 vi.mocked(api.listBuildProposals).mockResolvedValue([first,second]);
 const hook=renderHook(({doc})=>useBuildCompose({worldId:'world',pageDocumentId:doc,history,bridge,enabled:true,onHistory:vi.fn()}),{initialProps:{doc:'doc' as string|null}});
 await waitFor(()=>expect(hook.result.current.items).toHaveLength(2));
 expect((hook.result.current.pageElement as React.ReactElement<{record:api.BuildProposalRecord}>).props.record.action_id).toBe('first');
 const view=render(<>{hook.result.current.items.map(item=>item.element)}</>);
 fireEvent.click(screen.getByRole('button',{name:'Review suggestion on page'}));
 hook.rerender({doc:'other'});
 expect((hook.result.current.pageElement as React.ReactElement<{record:api.BuildProposalRecord}>).props.record.action_id).toBe('second');
 expect(api.listBuildProposals).toHaveBeenCalledTimes(1);
 hook.rerender({doc:null});expect(hook.result.current.pageElement).toBeNull();view.unmount();
});

it('hands explicit review to the page and requests conversation collapse',async()=>{
 vi.mocked(api.listBuildProposals).mockResolvedValue([receipt()]);const collapse=vi.fn();
 const hook=renderHook(()=>useBuildCompose({worldId:'world',pageDocumentId:'doc',history,bridge,enabled:true,onHistory:vi.fn(),onReviewOnPage:collapse}));
 await waitFor(()=>expect(hook.result.current.items).toHaveLength(1));render(<>{hook.result.current.items.map(item=>item.element)}</>);
 fireEvent.click(screen.getByRole('button',{name:'Review suggestion on page'}));expect(collapse).toHaveBeenCalledTimes(1);
 expect((hook.result.current.pageElement as React.ReactElement<{requestKey:number}>).props.requestKey).toBe(1);
});


it('initializes the first conversation once and retains read context independently of write placement',async()=>{
 const active={...history,conversation_id:'11111111-1111-4111-8111-111111111111',active_conversation_id:'11111111-1111-4111-8111-111111111111'};
 const empty={...history,conversation_state:'absent' as const,conversation_id:null,active_conversation_id:null,pointer_revision:0};
 const onHistory=vi.fn();
 vi.mocked(live.postWorldAgentNewConversation).mockResolvedValue({schema:'dmb_agent_new_conversation_response_v1',world_id:'world',
  conversation_id:active.conversation_id,active_conversation_id:active.conversation_id,pointer_revision:active.pointer_revision});
 vi.mocked(live.getWorldAgentConversationHistory).mockResolvedValue(active);
 vi.mocked(bridge.capture).mockRejectedValue(new Error('Page is read-only'));
 const hook=renderHook(()=>useBuildCompose({worldId:'world',pageDocumentId:'doc',history:empty,bridge,enabled:true,onHistory}));
 let prepared:Awaited<ReturnType<typeof hook.result.current.prepareHarnessTurn>>|undefined;
 await act(async()=>{prepared=await hook.result.current.prepareHarnessTurn('22222222-2222-4222-8222-222222222222',true);});
 expect(bridge.capture).not.toHaveBeenCalled();
 expect(prepared?.draftContext?.snapshot.draft_markdown).toBe('# Edge');
 expect(prepared?.capability).toBeUndefined();
 expect(prepared?.draftContext?.conversation_id).toBe(active.conversation_id);
 expect(onHistory).toHaveBeenCalledWith(active);
 expect(live.postWorldAgentNewConversation).toHaveBeenCalledTimes(1);
 expect(localStorage.getItem('dmb:build-initial-conversation:world')).toBeNull();
});

it('recovers an uncertain first-conversation command using its original identity',async()=>{
 const empty={...history,conversation_state:'absent' as const,conversation_id:null,active_conversation_id:null,pointer_revision:0};
 const active={...history,conversation_id:'11111111-1111-4111-8111-111111111111',active_conversation_id:'11111111-1111-4111-8111-111111111111'};
 vi.mocked(live.postWorldAgentNewConversation).mockRejectedValueOnce(new Error('Acknowledgment lost')).mockResolvedValueOnce({schema:'dmb_agent_new_conversation_response_v1',world_id:'world',
  conversation_id:active.conversation_id,active_conversation_id:active.conversation_id,pointer_revision:active.pointer_revision});
 vi.mocked(live.getWorldAgentConversationHistory).mockResolvedValue(active);
 const hook=renderHook(()=>useBuildCompose({worldId:'world',pageDocumentId:'doc',history:empty,bridge,enabled:true,onHistory:vi.fn()}));
 const first='22222222-2222-4222-8222-222222222222',second='33333333-3333-4333-8333-333333333333';
 vi.mocked(live.getWorldAgentNewConversationStatus).mockResolvedValue({schema:'dmb_agent_new_conversation_status_v1',world_id:'world',
  command_id:first,command_kind:'new',expected_pointer_revision:0,expected_active_conversation_id:null,request_fingerprint:'a'.repeat(64),status:'confirmed',
  receipt:{schema:'dmb_agent_new_conversation_receipt_v1',conversation_id:active.conversation_id,active_conversation_id:active.conversation_id,pointer_revision:active.pointer_revision,recorded_at:'now'}});
 await act(async()=>{await expect(hook.result.current.prepareHarnessTurn(first,true)).rejects.toThrow('Acknowledgment lost');});
 expect(JSON.parse(localStorage.getItem('dmb:build-initial-conversation:world')!).command_id).toBe(first);
 await act(async()=>{await hook.result.current.prepareHarnessTurn(second,true);});
 expect(vi.mocked(live.postWorldAgentNewConversation).mock.calls.map(call=>call[1].command_id)).toEqual([first]);
 expect(live.getWorldAgentNewConversationStatus).toHaveBeenCalledWith('world',expect.objectContaining({command_id:first}));
 expect(localStorage.getItem('dmb:build-initial-conversation:world')).toBeNull();
});


it('retires an absent old initializer after the World pointer advances instead of locking Send',async()=>{
 const empty={...history,conversation_state:'absent' as const,conversation_id:null,active_conversation_id:null,pointer_revision:4};
 const command={schema:'dmb_agent_new_conversation_v1',command_id:'22222222-2222-4222-8222-222222222222',expected_pointer_revision:0,expected_active_conversation_id:null};
 localStorage.setItem('dmb:build-initial-conversation:world',JSON.stringify(command));
 vi.mocked(live.getWorldAgentNewConversationStatus).mockResolvedValue({schema:'dmb_agent_new_conversation_status_v1',world_id:'world',
  command_id:command.command_id,command_kind:'new',expected_pointer_revision:0,expected_active_conversation_id:null,request_fingerprint:'a'.repeat(64),status:'absent',receipt:null});
 vi.mocked(live.getWorldAgentConversationHistory).mockResolvedValue(empty);
 const onHistory=vi.fn();
 const hook=renderHook(()=>useBuildCompose({worldId:'world',pageDocumentId:'doc',history:empty,bridge,enabled:true,onHistory}));
 await act(async()=>{await expect(hook.result.current.prepareHarnessTurn('33333333-3333-4333-8333-333333333333',true)).rejects.toThrow('active conversation changed');});
 expect(localStorage.getItem('dmb:build-initial-conversation:world')).toBeNull();
 expect(onHistory).toHaveBeenCalledWith(empty);
 expect(live.postWorldAgentNewConversation).not.toHaveBeenCalled();
});


it('retires live construction across navigation and marks lost delivery incomplete without replay',async()=>{
 const progress={schema:'dmb_build_construction_v1' as const,action_id:'action',reservation_sha256:'c'.repeat(64),conversation_id:'conversation',basis,
  origin:{client_turn_id:'client',durable_turn_id:'durable',turn_attempt:1,broker_operation_id:'op:1',arguments_sha256:'d'.repeat(64)},provider_attempt_id:'provider',sequence:1,status:'building' as const,markdown:'| Name |\n| --- |\n| Nia |\n'};
 const hook=renderHook(({doc})=>useBuildCompose({worldId:'world',pageDocumentId:doc,sourceKey:doc,history,bridge,enabled:true,onHistory:vi.fn()}),{initialProps:{doc:'doc'}});
 await act(async()=>{hook.result.current.observeConstruction({...progress,basis:{...basis,document_id:'foreign'}});});
 expect(hook.result.current.pageElement).toBeNull();
 act(()=>hook.result.current.observeConstruction(progress));
 expect(hook.result.current.pageElement?.props.progress.status).toBe('building');
 act(()=>hook.result.current.finishConstruction('action'));
 expect(hook.result.current.pageElement?.props.progress.status).toBe('incomplete');
 expect(api.composeBuildProposal).not.toHaveBeenCalled();
 hook.rerender({doc:'other'});expect(hook.result.current.pageElement).toBeNull();
 hook.rerender({doc:'doc'});expect(hook.result.current.pageElement).toBeNull();
});


it('does not resurrect a live preview after leaving and returning to its conversation',async()=>{
 const progress={schema:'dmb_build_construction_v1' as const,action_id:'action',reservation_sha256:'c'.repeat(64),conversation_id:'conversation',basis,
  origin:{client_turn_id:'client',durable_turn_id:'durable',turn_attempt:1,broker_operation_id:'op:1',arguments_sha256:'d'.repeat(64)},provider_attempt_id:'provider',sequence:1,status:'building' as const,markdown:'| Name |\n| --- |\n| Nia |\n'};
 const hook=renderHook(({snapshot})=>useBuildCompose({worldId:'world',pageDocumentId:'doc',history:snapshot,bridge,enabled:true,onHistory:vi.fn()}),{initialProps:{snapshot:history}});
 act(()=>hook.result.current.observeConstruction(progress));expect(hook.result.current.pageElement).not.toBeNull();
 hook.rerender({snapshot:{...history,conversation_id:'older'}});expect(hook.result.current.pageElement).toBeNull();
 hook.rerender({snapshot:history});expect(hook.result.current.pageElement).toBeNull();
});

it('keeps durable review identity through its own committed revision while retiring a foreign page',async()=>{
 vi.mocked(api.listBuildProposals).mockResolvedValue([receipt()]);
 const hook=renderHook(({sourceKey,pageDocumentId})=>useBuildCompose({worldId:'world',pageDocumentId,sourceKey,history,bridge,enabled:true,onHistory:vi.fn()}),{initialProps:{sourceKey:'doc:revision1',pageDocumentId:'doc'}});
 await waitFor(()=>expect(hook.result.current.pageElement).not.toBeNull());
 const first=hook.result.current.pageElement as React.ReactElement<{sourceKey:string}>;
 hook.rerender({sourceKey:'doc:revision2:committed-hash',pageDocumentId:'doc'});
 const after=hook.result.current.pageElement as React.ReactElement<{sourceKey:string}>;
 expect(after.key).toBe(first.key);expect(after.props.sourceKey).toBe(first.props.sourceKey);
 hook.rerender({sourceKey:'foreign:revision1',pageDocumentId:'foreign'});expect(hook.result.current.pageElement).toBeNull();
});
