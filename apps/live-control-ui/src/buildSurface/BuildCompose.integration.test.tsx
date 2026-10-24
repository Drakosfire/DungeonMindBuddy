import {proposalReview,type BuildProposalReview} from '../api/buildProposalReviewApi';
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
vi.mock('../api/buildProposalReviewApi',()=>({proposalReview:vi.fn()}));
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
  const compose = useBuildCompose({ worldId: 'elderwyld', pageDocumentId:session.documentId, history,
    bridge: registry.build?.value.composeBridge ?? null, enabled: true, onHistory: () => undefined });
  return <><button onClick={() => { void compose.submit('Create NPCs and jobs as a table and add them to the page.'); }}>Request table</button>
    <button disabled={session.saveDisabled} onClick={() => { void session.saveMarkdown(); }}>Save test page</button>
    <span data-testid="dirty">{String(session.dirty)}</span>{compose.pageElement}{compose.items.map(item => item.element)}{compose.error && <p role="alert">{compose.error}</p>}</>;
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
  const reviews=new Map<string,BuildProposalReview>();
  vi.mocked(proposalReview).mockImplementation(async(world,action,command)=>{
    let saved=reviews.get(action);
    if(!saved){
      saved={schema:'dmb_build_proposal_review_v1',world_id:world,action_id:action,reservation_sha256:'b'.repeat(64),revision:1,state:'editing',markdown:'| NPC | Job |\n| --- | --- |\n| Nella | Ferrier |',markdown_sha256:'d'.repeat(64),apply:null,updated_at:''};
    }
    if(command?.operation==='save')saved={...saved,revision:saved.revision+1,markdown:command.markdown!};
    if(command?.operation==='prepare')saved={...saved,revision:saved.revision+1,state:'applying',apply:{apply_id:command.apply_id!,before_editor_sha256:'e'.repeat(64),before_draft_sha256:'f'.repeat(64),after_editor_sha256:command.after_editor_sha256!,after_draft_sha256:command.after_draft_sha256!,reviewed_sha256:saved.markdown_sha256}};
    if(command?.operation==='confirm')saved={...saved,revision:saved.revision+1,state:'applied'};
    reviews.set(action,saved);return saved;
  });
  vi.mocked(proposals.composeBuildProposal).mockImplementation(async request => ({ schema_version: 'dmb_build_document_proposal_v1',
    action_id: request.idempotency_key, reservation: { idempotency_key: request.idempotency_key, conversation_id: request.conversation_id,
      expected_pointer_revision: request.expected_pointer_revision, basis: request.basis, instruction: request.instruction, origin: request.origin },
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
  await screen.findByRole('button', { name: 'Keep on page' });
  expect(session.editor!.state.doc.textContent).not.toContain('Nella');
  fireEvent.click(screen.getByRole('button', { name: 'Keep on page' }));
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
  await screen.findByRole('button', { name: 'Keep on page' });
  act(() => { session.editor!.commands.insertContent('My new idea.'); });
  const before = session.editor!.getJSON();
  await screen.findByRole('status');
  expect(session.editor!.getJSON()).toEqual(before);
  expect(proposals.reportBuildInsertion).not.toHaveBeenCalled();
});

function OpenConversation() {
  session = useMarkdownCanvasSession();
  const agent = useAgentInteraction();
  return <button onClick={() => agent.setPaneOpen(true)}>Open conversation</button>;
}
it('uses the Harness for a discussion follow-up and exposes its durable preview even if the reply is lost', async () => {
  vi.mocked(api.getWorldAgentConversationHistory).mockResolvedValue(history);
  let saved: proposals.BuildProposalRecord[] = [];
  vi.mocked(proposals.listBuildProposals).mockImplementation(async () => saved);
  vi.mocked(api.postWorldBuildAgentTurn).mockImplementation(async request => {
    const cap = request.build_write_capability!;
    expect(cap.basis.document_id).toBe(DOC);
    expect(cap.draft_markdown).toContain('A fort town.');
    const generate = vi.mocked(proposals.composeBuildProposal).getMockImplementation()!;
    saved = [await generate({ ...cap, instruction: 'Prepare the discussed Nella, a ferrier, as a table.',
      origin: { client_turn_id: request.turn_id, durable_turn_id: '55555555-5555-4555-8555-555555555555', turn_attempt: 1,
        broker_operation_id: 'host:g1', arguments_sha256: 'd'.repeat(64) } })];
    throw new Error('Synthetic connection lost after the Harness tool prepared its preview');
  });
  render(<AgentInteractionProvider><AskPluginSlotProvider><WorldAgentConversationProvider worldId="elderwyld">
    <BuildCanvasTestProvider documentId={DOC}><BuildSurfaceShell /><OpenConversation /></BuildCanvasTestProvider>
    <WorldAgentConversation surface="build" worldId="elderwyld" worldName="Elderwyld" />
  </WorldAgentConversationProvider></AskPluginSlotProvider></AgentInteractionProvider>);
  await waitFor(() => expect(session.phase).toBe('ready_clean'));
  fireEvent.click(screen.getByRole('button', { name: 'Open conversation' }));
  const composer = await screen.findByLabelText('Message DungeonBuddy');
  fireEvent.change(composer, { target: { value: 'Sounds good; please put that on the page as a table.' } });
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send message' })).not.toBeDisabled());
  fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
  const insert = await screen.findByRole('button', { name: 'Keep on page' });
  expect(api.postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);
  expect(proposals.composeBuildProposal).not.toHaveBeenCalled();
  expect(session.dirty).toBe(false);
  expect(session.editor!.state.doc.textContent).not.toContain('Nella');
  fireEvent.click(insert);
  await waitFor(() => expect(session.dirty).toBe(true));
  expect(session.editor!.state.doc.textContent).toContain('Nella');
  expect(api.commitTiptapMarkdownWrite).not.toHaveBeenCalled();
});

it.each(['click', 'enter'])('holds a new Harness request by %s while preserving an uncertain earlier turn', async method => {
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
  expect(screen.getByRole('button', { name: 'Send message' })).toBeDisabled();
  if (method === 'enter') fireEvent.keyDown(composer, { key: 'Enter' });
  else fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
  expect(proposals.composeBuildProposal).not.toHaveBeenCalled();
  expect(api.postWorldBuildAgentTurn).not.toHaveBeenCalled();
  expect(localStorage.getItem(key)).toBe(pending);
  expect(session.dirty).toBe(false);
  fireEvent.change(composer, { target: { value: 'What do you know about Edge?' } });
  expect(screen.getByRole('button', { name: 'Send message' })).toBeDisabled();
});

it('reloads a proposal and inserts at its original position after the author moves the caret', async () => {
  let saved: proposals.BuildProposalRecord[] = [];
  const generate = vi.mocked(proposals.composeBuildProposal).getMockImplementation()!;
  vi.mocked(proposals.composeBuildProposal).mockImplementation(async request => {
    const result = await generate(request); saved = [result]; return result;
  });
  vi.mocked(proposals.listBuildProposals).mockImplementation(async () => saved);
  const view=render(<Harness />);
  await waitFor(() => expect(session.phase).toBe('ready_clean'));
  act(() => {session.editor!.commands.setTextSelection(session.editor!.state.doc.content.size-1);});
  fireEvent.click(screen.getByRole('button',{name:'Request table'}));
  await screen.findByRole('button',{name:'Keep on page'});
  expect(saved[0].reservation.basis.editor_sha256).toMatch(/^[a-f0-9]{64}$/);
  view.unmount(); render(<Harness />);
  await waitFor(() => expect(session.phase).toBe('ready_clean'));
  act(() => {session.editor!.commands.setTextSelection(1);});
  const before=session.editor!.getJSON();
  fireEvent.click(await screen.findByRole('button',{name:'Keep on page'}));
  await waitFor(() => expect(session.dirty).toBe(true));
  const markdown=tiptapJsonToSemanticMarkdown(session.editor!.getJSON());
  expect(markdown.indexOf('A fort town.')).toBeLessThan(markdown.indexOf('Nella'));
  expect(proposals.composeBuildProposal).toHaveBeenCalledTimes(1);
  expect(api.commitTiptapMarkdownWrite).not.toHaveBeenCalled();
  act(() => {session.editor!.commands.undo();});
  expect(session.editor!.getJSON()).toEqual(before);
});

let exposedBridge: import('./buildComposeBridge').BuildComposeBridge|null=null;
function ExposeBuildBridge(){const registry=useWorldAgentConversationState();exposedBridge=registry?.build?.value.composeBridge??null;return null;}
function ClosedPageHarness(){return <AgentInteractionProvider><AskPluginSlotProvider><WorldAgentConversationProvider worldId="elderwyld">
 <BuildCanvasTestProvider documentId={DOC}><BuildSurfaceShell/><OpenConversation/><ExposeBuildBridge/></BuildCanvasTestProvider>
 <WorldAgentConversation surface="build" worldId="elderwyld" worldName="Elderwyld"/>
 </WorldAgentConversationProvider></AskPluginSlotProvider></AgentInteractionProvider>;}
it('restores a saved on-page review with chat closed and does not reread history when chat opens',async()=>{
 vi.mocked(api.getWorldAgentConversationHistory).mockResolvedValue(history);
 let finish!:(records:proposals.BuildProposalRecord[])=>void;
 vi.mocked(proposals.listBuildProposals).mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
 const view=render(<ClosedPageHarness/>);
 await waitFor(()=>expect(session.phase).toBe('ready_clean'));
 await waitFor(()=>expect(finish).toBeTypeOf('function'));
 expect(screen.queryByRole('textbox',{name:'Message DungeonBuddy',exact:true})).not.toBeInTheDocument();
 const cap=await exposedBridge!.capture();
 const record=await vi.mocked(proposals.composeBuildProposal).getMockImplementation()!({idempotency_key:'closed-page-review',conversation_id:history.conversation_id!,expected_pointer_revision:1,basis:cap.basis,draft_markdown:cap.draftMarkdown,instruction:'A table'});
 await act(async()=>{finish([record]);});
 await screen.findByRole('region',{name:'Proposed page change'});
 expect(session.dirty).toBe(false);expect(api.getWorldAgentConversationHistory).toHaveBeenCalledTimes(1);
 fireEvent.click(screen.getByRole('button',{name:'Open conversation'}));
 await screen.findByLabelText('Message DungeonBuddy');
 expect(api.getWorldAgentConversationHistory).toHaveBeenCalledTimes(1);
 view.unmount();
 vi.mocked(proposals.listBuildProposals).mockResolvedValue([record]);
 render(<ClosedPageHarness/>);
 await screen.findByRole('region',{name:'Proposed page change'});
 expect(screen.queryByRole('textbox',{name:'Message DungeonBuddy',exact:true})).not.toBeInTheDocument();
 expect(session.dirty).toBe(false);expect(api.postWorldBuildAgentTurn).not.toHaveBeenCalled();
});
