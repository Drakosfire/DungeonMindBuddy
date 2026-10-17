import { act, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
import { beforeEach, expect, it, vi } from 'vitest';
import * as api from '../../api/buildDocumentProposalApi';
import * as live from '../../api/liveApi';
import type { WorldAgentConversationHistoryResponse } from '../../api/types';
import type { CapturedBuildInsertion, BuildComposeBridge } from '../../buildSurface/buildComposeBridge';
import { BuildComposeProposal, useBuildCompose } from './BuildComposeProposal';
vi.mock('../../api/buildDocumentProposalApi', () => ({ composeBuildProposal: vi.fn(), getBuildProposal: vi.fn(),
  getBuildProposalPrompt: vi.fn(), listBuildProposals: vi.fn(), reportBuildInsertion: vi.fn() }));
vi.mock('../../api/liveApi', () => ({ getWorldAgentConversationHistory: vi.fn(), postWorldAgentNewConversation: vi.fn(), getWorldAgentTurnPrompt: vi.fn() }));
const basis = { world_id: 'world', document_id: 'doc', registry_revision: 1, content_sha256: 'a'.repeat(64),
  draft_sha256: 'b'.repeat(64), visibility: 'internal' as const, caret: 1, draft_generation: 0, selection_generation: 0 };
const history: WorldAgentConversationHistoryResponse = { schema: 'dmb_agent_conversation_history_v1', world_id: 'world', conversation_state: 'active',
  conversation_id: 'conversation', active_conversation_id: 'conversation', pointer_revision: 1, turns: [], next_before_sequence: null };
const captured = { basis, draftMarkdown: '# Edge', editorJson: '{}', editor: {} } as CapturedBuildInsertion;
function receipt(request?: api.BuildProposalRequest): api.BuildProposalRecord {
  return { schema_version: 'dmb_build_document_proposal_v1', action_id: request?.idempotency_key ?? 'action',
    reservation: request ?? { idempotency_key: 'action', conversation_id: 'conversation', expected_pointer_revision: 1, basis, instruction: 'Create a table' },
    request_fingerprint: 'c'.repeat(64), after_turn_sequence: 0, revision: 5, state: 'proposed', created_at: '', updated_at: '', claim_expires_at: '',
    authorization: null, failure_code: null, inserted_in_draft: false,
    proposal: { replacement_markdown: '| NPC | Job |\n| --- | --- |\n| Nella | Baker |', summary: 'Proposed NPC', assumptions: ['Invented'] } };
}
let bridge: BuildComposeBridge;
beforeEach(() => {
  vi.resetAllMocks(); bridge = { capture: vi.fn().mockResolvedValue(captured), insert: vi.fn() };
  vi.mocked(api.listBuildProposals).mockResolvedValue([]);
  vi.mocked(api.composeBuildProposal).mockImplementation(async request => receipt(request));
  vi.mocked(api.reportBuildInsertion).mockImplementation(async (_world, record) => ({ ...record, inserted_in_draft: true }));
});
it('keeps one write request, reviews inline and inserts only once', async () => {
  const hook = renderHook(() => useBuildCompose({ worldId: 'world', history, bridge, enabled: true, onHistory: vi.fn() }));
  await act(async () => { await hook.result.current.submit('Create a table'); });
  expect(api.composeBuildProposal).toHaveBeenCalledTimes(1);
  const view = render(<>{hook.result.current.items.map(item => item.element)}</>);
  expect(screen.getByRole('table')).toHaveTextContent('Nella');
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Insert into page' })); });
  view.rerender(<>{hook.result.current.items.map(item => item.element)}</>);
  expect(bridge.insert).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole('button', { name: 'Insert into page' })).not.toBeInTheDocument();
});
it('recovers a stored proposal after remount without generation and inserts only on explicit approval', async () => {
  const record = receipt();
  record.proposal!.replacement_markdown = '| d20 | Name |\n|---:|---|\n| 1 | Mara |';
  vi.mocked(api.listBuildProposals).mockResolvedValue([record]);
  const hook = renderHook(() => useBuildCompose({ worldId: 'world', history, bridge, enabled: true, onHistory: vi.fn() }));
  await waitFor(() => expect(hook.result.current.items).toHaveLength(1));
  const view = render(<>{hook.result.current.items.map(item => item.element)}</>);
  expect(bridge.capture).not.toHaveBeenCalled();
  expect(bridge.insert).not.toHaveBeenCalled();
  expect(screen.getByRole('table')).toHaveTextContent('Mara');
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Insert at current caret' })); });
  expect(bridge.insert).toHaveBeenCalledWith(captured, '| d20 | Name |\n|---|---|\n| 1 | Mara |');
  expect(api.composeBuildProposal).not.toHaveBeenCalled();
  view.rerender(<>{hook.result.current.items.map(item => item.element)}</>);
  expect(screen.queryByRole('button', { name: /Insert/ })).not.toBeInTheDocument();
});
it.each(['world_id', 'document_id', 'registry_revision', 'content_sha256', 'visibility', 'draft_sha256'] as const)(
  'refuses recovered insertion when %s differs', async field => {
    vi.mocked(api.listBuildProposals).mockResolvedValue([receipt()]);
    vi.mocked(bridge.capture).mockResolvedValue({ ...captured, basis: { ...basis, [field]: field === 'registry_revision' ? 2 : 'different' } });
    const hook = renderHook(() => useBuildCompose({ worldId: 'world', history, bridge, enabled: true, onHistory: vi.fn() }));
    await waitFor(() => expect(hook.result.current.items).toHaveLength(1));
    render(<>{hook.result.current.items.map(item => item.element)}</>);
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Insert at current caret' })); });
    expect(bridge.insert).not.toHaveBeenCalled();
    expect(api.composeBuildProposal).not.toHaveBeenCalled();
    expect(hook.result.current.error).toContain('page has changed');
  });
it('drops a delayed recovered capture when the World changes and prevents double approval', async () => {
  vi.mocked(api.listBuildProposals).mockResolvedValue([receipt()]);
  let finish!: (value: CapturedBuildInsertion) => void;
  vi.mocked(bridge.capture).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  const hook = renderHook(({ world }) => useBuildCompose({ worldId: world, history: { ...history, world_id: world }, bridge, enabled: true, onHistory: vi.fn() }), { initialProps: { world: 'world' } });
  await waitFor(() => expect(hook.result.current.items).toHaveLength(1));
  render(<>{hook.result.current.items.map(item => item.element)}</>);
  fireEvent.click(screen.getByRole('button', { name: 'Insert at current caret' }));
  fireEvent.click(screen.getByRole('button', { name: 'Insert at current caret' }));
  expect(bridge.capture).toHaveBeenCalledTimes(1);
  hook.rerender({ world: 'foreign' });
  await act(async () => { finish(captured); });
  expect(bridge.insert).not.toHaveBeenCalled();
});
it('opens the first durable World conversation before composing', async () => {
  vi.mocked(live.postWorldAgentNewConversation).mockResolvedValue({ schema: 'dmb_agent_new_conversation_response_v1', world_id: 'world',
    conversation_id: 'conversation', active_conversation_id: 'conversation', pointer_revision: 1 });
  vi.mocked(live.getWorldAgentConversationHistory).mockResolvedValue(history);
  const hook = renderHook(() => {
    const [value, setValue] = useState<WorldAgentConversationHistoryResponse>({ ...history, conversation_id: null, active_conversation_id: null, pointer_revision: 0, conversation_state: 'absent' });
    return useBuildCompose({ worldId: 'world', history: value, bridge, enabled: true, onHistory: setValue });
  });
  await act(async () => { await hook.result.current.submit('Create a table'); });
  expect(live.postWorldAgentNewConversation).toHaveBeenCalledTimes(1);
  expect(api.composeBuildProposal).toHaveBeenCalledWith(expect.objectContaining({ conversation_id: 'conversation', expected_pointer_revision: 1 }));
  expect(hook.result.current.items).toHaveLength(1);
});
it('does not replay an uncertain provider operation', async () => {
  vi.mocked(api.composeBuildProposal).mockRejectedValue(new Error('Unknown outcome'));
  vi.mocked(api.getBuildProposal).mockResolvedValue({ ...receipt(), state: 'unknown', proposal: null });
  const hook = renderHook(() => useBuildCompose({ worldId: 'world', history, bridge, enabled: true, onHistory: vi.fn() }));
  await act(async () => { await hook.result.current.submit('Create a table'); });
  expect(api.composeBuildProposal).toHaveBeenCalledTimes(1);
  expect(api.getBuildProposal).toHaveBeenCalledTimes(1);
  expect(hook.result.current.error).toContain('Unknown outcome');
});
it('discards an old result after World A → B → A', async () => {
  let finish!: (value: api.BuildProposalRecord) => void;
  let request!: api.BuildProposalRequest;
  vi.mocked(api.composeBuildProposal).mockImplementation(value => { request = value; return new Promise(resolve => { finish = resolve; }); });
  const hook = renderHook(({ world }) => useBuildCompose({ worldId: world, history: { ...history, world_id: world }, bridge, enabled: true, onHistory: vi.fn() }), { initialProps: { world: 'world' } });
  let pending!: Promise<boolean>;
  act(() => { pending = hook.result.current.submit('Create a table'); });
  await waitFor(() => expect(api.composeBuildProposal).toHaveBeenCalledTimes(1));
  hook.rerender({ world: 'foreign' }); hook.rerender({ world: 'world' });
  await act(async () => { finish(receipt(request)); await pending; });
  expect(hook.result.current.items).toHaveLength(0);
});
it('keeps reopened proposals readable without executable editor authority', () => {
  render(<BuildComposeProposal record={receipt()} canInsert={false} onInsert={vi.fn()} />);
  expect(screen.getByRole('table')).toHaveTextContent('Nella');
  expect(screen.queryByRole('button', { name: 'Insert into page' })).not.toBeInTheDocument();
});
