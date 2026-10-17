import { AskPluginSlotProvider } from "../agentInteraction/AskPluginSlot";
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { webcrypto } from 'node:crypto';
import { useAgentInteraction } from '../agentInteraction/useAgentInteraction';
import { AgentInteractionProvider } from '../agentInteraction/AgentInteractionProvider';
import { WorldAgentConversation, WorldAgentConversationProvider, useWorldAgentConversationState } from '../agentInteraction/WorldAgentConversation';
import { useMarkdownCanvasSession } from '../markdownCanvas/MarkdownCanvasSession';
import { BuildCanvasTestProvider } from './buildCanvasTestProvider';
import { BuildSurfaceShell } from './BuildSurfaceShell';
import { useBuildCompose } from '../planSurface/components/BuildComposeProposal';
import * as api from '../api/liveApi';
import * as proposals from '../api/buildDocumentProposalApi';
import type { WorkspaceDocumentSnapshot, WorldAgentConversationHistoryResponse } from '../api/types';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
vi.mock('../selectedWorld/SelectedWorldContext', () => ({ useSelectedWorld: () => ({ kind: 'managed', worldId: 'elderwyld' }) }));
vi.mock('../api/liveApi', async original => ({ ...await original<typeof api>(), getWorkspaceDocumentSnapshot: vi.fn(),
  prepareTiptapMarkdownWrite: vi.fn(), commitTiptapMarkdownWrite: vi.fn(), getBuildSourceNavigation: vi.fn(), getWorldAgentConversationHistory: vi.fn(), postWorldBuildAgentTurn: vi.fn() }));
vi.mock('../api/buildDocumentProposalApi', async original => ({ ...await original<typeof proposals>(),
  composeBuildProposal: vi.fn(), listBuildProposals: vi.fn(), reportBuildInsertion: vi.fn(), getBuildProposal: vi.fn() }));
const DOC = '11111111-1111-4111-8111-111111111111';
const history: WorldAgentConversationHistoryResponse = { schema: 'dmb_agent_conversation_history_v1', world_id: 'elderwyld',
  conversation_id: '22222222-2222-4222-8222-222222222222', active_conversation_id: '22222222-2222-4222-8222-222222222222',
  pointer_revision: 1, conversation_state: 'active', turns: [], next_before_sequence: null };
let session: ReturnType<typeof useMarkdownCanvasSession>;
function Controls() {
  session = useMarkdownCanvasSession();
  const registry = useWorldAgentConversationState()!;
  const compose = useBuildCompose({ worldId: 'elderwyld', history,
    bridge: registry.build?.value.composeBridge ?? null, enabled: true, onHistory: () => undefined });
  return <><button onClick={() => { void compose.submit('Create NPCs and jobs as a table and add them to the page.'); }}>Request table</button>
    <button disabled={session.saveDisabled} onClick={() => { void session.saveMarkdown(); }}>Save test page</button>
    <span data-testid="dirty">{String(session.dirty)}</span>{compose.items.map(item => item.element)}{compose.error && <p role="alert">{compose.error}</p>}</>;
}
function Harness() { return <AgentInteractionProvider><WorldAgentConversationProvider worldId="elderwyld">
  <BuildCanvasTestProvider documentId={DOC}><BuildSurfaceShell /><Controls /></BuildCanvasTestProvider>
</WorldAgentConversationProvider></AgentInteractionProvider>; }
let stored: WorkspaceDocumentSnapshot;
beforeEach(() => {
  Object.defineProperty(globalThis, 'crypto', { configurable: true, value: webcrypto });
  vi.clearAllMocks(); localStorage.clear(); sessionStorage.clear(); window.history.replaceState({}, '', `/build?world=elderwyld&documentId=${DOC}`);
  stored = { schema_version: 'dmb_workspace_document_snapshot_v1', record: { schema_version: 'dmb_workspace_document_record_v1',
    document_id: DOC, title: 'Edge', campaign_id: 'elderwyld', world_id: 'elderwyld', target_session: null, kind: 'worldbuilding_source',
    target_relpath: `out/workspace/worldbuilding/${DOC}.md`, status: 'active', content_status: 'committed', revision: 1,
    created_at: '', updated_at: '', source_domain: 'worldbuilding', document_class: 'lore', authority_state: 'draft', visibility_state: 'internal' },
    markdown: '# Edge\n\nA fort town.\n', content_sha256: 'a'.repeat(64), file_fingerprint: 'fp1', file_exists: true, loaded_revision: 1 };
  vi.mocked(api.getWorkspaceDocumentSnapshot).mockImplementation(async () => structuredClone(stored));
  vi.mocked(proposals.listBuildProposals).mockResolvedValue([]);
  vi.mocked(proposals.composeBuildProposal).mockImplementation(async request => ({ schema_version: 'dmb_build_document_proposal_v1',
    action_id: request.idempotency_key, reservation: { idempotency_key: request.idempotency_key, conversation_id: request.conversation_id,
      expected_pointer_revision: request.expected_pointer_revision, basis: request.basis, instruction: request.instruction },
    request_fingerprint: 'b'.repeat(64), after_turn_sequence: 0, revision: 5, state: 'proposed', created_at: '2026-10-16T00:00:00Z', updated_at: '', claim_expires_at: '',
    authorization: null, proposal: { replacement_markdown: '| NPC | Job |\n| --- | --- |\n| Nella | Ferrier |', summary: 'A proposed NPC.', assumptions: ['Nella is invented.'] },
    failure_code: null, inserted_in_draft: false }));
  vi.mocked(proposals.reportBuildInsertion).mockImplementation(async (_world, record) => ({ ...record, revision: record.revision + 1, inserted_in_draft: true }));
  vi.mocked(api.prepareTiptapMarkdownWrite).mockImplementation(async request => ({ schema_version: 'dmb_tiptap_markdown_write_prepare_v1', document_id: DOC,
    title: 'Edge', target_relpath: stored.record.target_relpath, target_display_path: 'Edge', registry_revision: 1, file_exists: true,
    writer_ok: true, writer_phase: 'prepare', writer_confirm_token: 'synthetic', writer_diff: request.markdown, warnings: [], diagnostics: [] }));
  vi.mocked(api.commitTiptapMarkdownWrite).mockImplementation(async () => {
    stored = { ...stored, record: { ...stored.record, revision: 2 }, loaded_revision: 2, markdown: tiptapJsonToSemanticMarkdown(session.editor!.getJSON()),
      content_sha256: 'c'.repeat(64), file_fingerprint: 'fp2' };
    return { schema_version: 'dmb_tiptap_markdown_write_commit_v1', document_id: DOC, title: 'Edge', target_relpath: stored.record.target_relpath,
      target_display_path: 'Edge', registry_revision: 2, committed_revision: 2, committed_record: stored.record,
      normalized_content_sha256: stored.content_sha256, writer_ok: true, bytes_written: stored.markdown.length, file_fingerprint: 'fp2', diagnostics: [] };
  });
});
it('proposes a table, inserts into mounted Build, manually edits, explicitly saves and reopens', async () => {
  const view = render(<Harness />);
  await waitFor(() => expect(session.editor).not.toBeNull());
  await waitFor(() => expect(session.phase).toBe('ready_clean'));
  act(() => { session.editor!.commands.setTextSelection(session.editor!.state.doc.content.size - 1); });
  fireEvent.click(screen.getByRole('button', { name: 'Request table' }));
  await screen.findByRole('button', { name: 'Insert into page' });
  expect(session.editor!.state.doc.textContent).not.toContain('Nella');
  fireEvent.click(screen.getByRole('button', { name: 'Insert into page' }));
  await waitFor(() => expect(session.dirty).toBe(true));
  expect(session.editor!.getJSON().content?.some(node => node.type === 'table')).toBe(true);
  expect(api.commitTiptapMarkdownWrite).not.toHaveBeenCalled();
  act(() => {
    const editor = session.editor!;
    let position = 0;
    editor.state.doc.descendants((node, at) => { if (node.isText && node.text === 'Ferrier') position = at; });
    editor.commands.insertContentAt({ from: position, to: position + 7 }, 'Boatwright');
    session.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
  });
  fireEvent.click(screen.getByRole('button', { name: 'Save test page' }));
  await waitFor(() => expect(session.dirty).toBe(false));
  expect(stored.markdown).toContain('Boatwright');
  expect(api.commitTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
  view.unmount(); localStorage.clear(); render(<Harness />);
  await waitFor(() => expect(session.phase).toBe('ready_clean'));
  expect(session.editor!.state.doc.textContent).toContain('Boatwright');
  expect(session.editor!.state.doc.textContent).toContain('A fort town.');
});
it('refuses insertion after an intervening edit and keeps the new writing', async () => {
  render(<Harness />); await waitFor(() => expect(session.phase).toBe('ready_clean'));
  fireEvent.click(screen.getByRole('button', { name: 'Request table' }));
  await screen.findByRole('button', { name: 'Insert into page' });
  act(() => { session.editor!.commands.insertContent('My new idea.'); });
  const before = session.editor!.getJSON();
  fireEvent.click(screen.getByRole('button', { name: 'Insert into page' }));
  await screen.findByRole('alert');
  expect(session.editor!.getJSON()).toEqual(before);
  expect(proposals.reportBuildInsertion).not.toHaveBeenCalled();
});

function OpenConversation() {
  session = useMarkdownCanvasSession();
  const agent = useAgentInteraction();
  return <button onClick={() => agent.setPaneOpen(true)}>Open conversation</button>;
}
it('routes the ordinary Build composer to a reviewed page insertion using the published bridge', async () => {
  vi.mocked(api.getWorldAgentConversationHistory).mockResolvedValue(history);
  render(<AgentInteractionProvider><AskPluginSlotProvider><WorldAgentConversationProvider worldId="elderwyld">
    <BuildCanvasTestProvider documentId={DOC}><BuildSurfaceShell /><OpenConversation /></BuildCanvasTestProvider>
    <WorldAgentConversation surface="build" worldId="elderwyld" worldName="Elderwyld" />
  </WorldAgentConversationProvider></AskPluginSlotProvider></AgentInteractionProvider>);
  await waitFor(() => expect(session.phase).toBe('ready_clean'));
  fireEvent.click(screen.getByRole('button', { name: 'Open conversation' }));
  const composer = await screen.findByLabelText('Message DungeonBuddy');
  fireEvent.change(composer, { target: { value: 'Create six NPCs with jobs and add them as a table.' } });
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send message' })).not.toBeDisabled());
  fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
  const insert = await screen.findByRole('button', { name: 'Insert into page' });
  expect(api.postWorldBuildAgentTurn).not.toHaveBeenCalled();
  expect(proposals.composeBuildProposal).toHaveBeenCalledTimes(1);
  fireEvent.click(insert);
  await waitFor(() => expect(session.dirty).toBe(true));
  expect(session.editor!.state.doc.textContent).toContain('Nella');
});

it.each(['click', 'enter'])('previews a natural table request by %s while preserving an uncertain read-only Ask', async method => {
  vi.mocked(api.getWorldAgentConversationHistory).mockResolvedValue(history);
  const key = 'dmb:world-play-pending-turn:v1:elderwyld';
  const pending = JSON.stringify({ schema: 'dmb_world_play_pending_turn_v1', request: {
    schema: 'dmb_agent_turn_request_v1', client_thread_id: '33333333-3333-4333-8333-333333333333',
    turn_id: '44444444-4444-4444-8444-444444444444', surface: { surface_id: 'build', instance_id: `build:${DOC}` },
    owner_scope: { kind: 'world', world_id: 'elderwyld' },
    primary_work: { kind: 'build', object_id: DOC, expected_revision: 1, expected_content_sha256: 'a'.repeat(64) },
    client_work_state: 'saved_clean', graph_request: { mode: 'none' }, graph_selection: null,
    message: 'Do you have write tools? Can you see the page?',
  } });
  localStorage.setItem(key, pending);
  render(<AgentInteractionProvider><AskPluginSlotProvider><WorldAgentConversationProvider worldId="elderwyld">
    <BuildCanvasTestProvider documentId={DOC}><BuildSurfaceShell /><OpenConversation /></BuildCanvasTestProvider>
    <WorldAgentConversation surface="build" worldId="elderwyld" worldName="Elderwyld" />
  </WorldAgentConversationProvider></AskPluginSlotProvider></AgentInteractionProvider>);
  await waitFor(() => expect(session.phase).toBe('ready_clean'));
  fireEvent.click(screen.getByRole('button', { name: 'Open conversation' }));
  const composer = await screen.findByLabelText('Message DungeonBuddy');
  fireEvent.change(composer, { target: { value: 'What do you know about Edge?' } });
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send message' })).toBeDisabled());
  fireEvent.change(composer, { target: { value: 'I want a table of 20 soldiers names on a d20 table.' } });
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send message' })).toBeEnabled());
  if (method === 'enter') fireEvent.keyDown(composer, { key: 'Enter' });
  else fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
  await screen.findByRole('button', { name: 'Insert into page' });
  expect(proposals.composeBuildProposal).toHaveBeenCalledTimes(1);
  expect(api.postWorldBuildAgentTurn).not.toHaveBeenCalled();
  expect(localStorage.getItem(key)).toBe(pending);
  expect(session.dirty).toBe(false);
  fireEvent.change(composer, { target: { value: 'What do you know about Edge?' } });
  expect(screen.getByRole('button', { name: 'Send message' })).toBeDisabled();
});
