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
vi.mock('../../api/liveApi', () => ({ getWorldAgentConversationHistory: vi.fn(), postWorldAgentNewConversation: vi.fn(), getWorldAgentTurnPrompt: vi.fn() }));
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
  vi.resetAllMocks(); bridge = { capture: vi.fn().mockResolvedValue(captured), restore: vi.fn().mockResolvedValue(captured), insert: vi.fn(), insertProposal: vi.fn(), prepareProposal:vi.fn(), applyPrepared:vi.fn(), inspectProposal:vi.fn() };
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
 vi.mocked(proposalReview).mockResolvedValue({schema:'dmb_build_proposal_review_v1',world_id:'world',action_id:'action',reservation_sha256:record.request_fingerprint,
  revision:4,state:'applied',markdown:'The author’s retained review edit.',markdown_sha256:'a'.repeat(64),apply:null,updated_at:''});
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
