import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Editor } from '@tiptap/core';
import { EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { afterEach, beforeAll, beforeEach, expect, it, vi } from 'vitest';
import { AgentInteractionProvider, useAgentInteraction } from '../../agentInteraction/AgentInteractionProvider';
import * as api from '../../api/liveApi';
import type { NativeGraphCatalog } from '../../api/nativeGraphInspection';
import type { MarkdownCanvasSessionValue } from '../../markdownCanvas/MarkdownCanvasSession';
import type { SurfaceInteractionPublication } from '../../surfaceInteraction/types';
import { RunbookReferenceNode } from '../../tiptap/extensions/RunbookReferenceNode';
import { GraphNodeReferenceNode } from '../../tiptap/extensions/GraphNodeReferenceNode';
import { exportMarkdownWithAdapter, importMarkdownWithAdapter } from '../../tiptap/MarkdownDocumentAdapter';
import { useGraphNodeChipRuntime, __resetGraphNodeChipRuntimeForTests } from '../../graphReference/GraphNodeChipRuntime';
import { BuildReferenceCapability } from './BuildReferenceCapability';
import type { BuildReferenceContextBinding } from './buildBuildSurfaceInteractionPublication';
import { BuildReferenceSearchProjection } from './BuildReferenceSearchProjection';
import { BUILD_REFERENCE_CONTEXT_BINDING_ID } from './buildReferenceIds';
let selection: {
    kind: "legacy" | "loading" | "managed";
    worldId?: string;
} = { kind: "legacy" };
let current: MarkdownCanvasSessionValue;
let publication: SurfaceInteractionPublication | null;
let runtime: ReturnType<typeof useGraphNodeChipRuntime>;
const editors: Editor[] = [];
vi.mock('../../markdownCanvas/MarkdownCanvasSession', () => ({ useOptionalMarkdownCanvasSession: () => current }));
vi.mock('../../selectedWorld/SelectedWorldContext', () => ({ useSelectedWorldAdmission: () => selection }));
vi.mock('../../rulesLookup/rulesLookupProjection', async (original) => ({ ...await original<typeof import('../../rulesLookup/rulesLookupProjection')>(), useRulesLookupProjection: () => undefined }));
vi.mock('../../statblocks/statblockWorkbenchProjection', async (original) => ({ ...await original<typeof import('../../statblocks/statblockWorkbenchProjection')>(), useStatblockWorkbenchProjection: () => undefined }));
vi.mock('../../api/liveApi', async (original) => ({ ...await original<typeof import('../../api/liveApi')>(), getNativeGraphCatalog: vi.fn(), inspectNativeGraph: vi.fn(), listWorldMechanicsAssociations: vi.fn().mockResolvedValue([]), postManagedWorldGraphProjection: vi.fn(), postWorldGraphProjection: vi.fn() }));
const pin = { managed_world_id: 'w', native_world_id: 'native-w', binding_version: 3, revision_id: 'rev-native', scope_mode: 'world' as const, campaign_id: null };
const catalog: NativeGraphCatalog = { schema: 'dmb_native_graph_catalog_v1', scope: pin, catalogue: { identity: { space_id: 'native-w', revision_id: 'rev-native' }, entities: [{ entity_id: 'ent:fellinor' }], admitted_assertion_ids: [], completeness: { status: 'complete', reason: null }, request_sha256: 'request', result_digest: 'digest' }, assertions: [] };
function makeEditor(content: unknown = { type: 'doc', content: [{ type: 'paragraph' }] }) {
    const editor = new Editor({ extensions: [StarterKit, RunbookReferenceNode, GraphNodeReferenceNode], content: content as never });
    editors.push(editor);
    return editor;
}
function session(documentId = 'doc-a', worldId: string | null = 'w', editor = makeEditor()) {
    return { documentId, phase: 'ready_clean', record: { document_id: documentId, world_id: worldId, campaign_id: null }, editor, saveDisabled: false, statusLabel: 'Ready', saveMarkdown: vi.fn() } as unknown as MarkdownCanvasSessionValue;
}
function Probe() { publication = useAgentInteraction().surfaceInteractionPublication; runtime = useGraphNodeChipRuntime(); return null; }
function Harness() { return <AgentInteractionProvider><BuildReferenceCapability documentId={current.documentId}><EditorContent editor={current.editor}/><Probe /></BuildReferenceCapability></AgentInteractionProvider>; }
function binding() { return publication!.projectionBindings.find(b => b.id === BUILD_REFERENCE_CONTEXT_BINDING_ID)!.value as BuildReferenceContextBinding; }
beforeAll(() => { HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); }; HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); }; });
beforeEach(() => { vi.clearAllMocks(); selection = { kind: "legacy" }; current = session(); publication = null; vi.mocked(api.getNativeGraphCatalog).mockResolvedValue(catalog); vi.mocked(api.inspectNativeGraph).mockResolvedValue({ schema: 'dmb_native_graph_entity_v1', scope: pin, entity: { found: true, assertions: [], evidence: [], completeness: { status: 'complete', reason: null } } }); });
afterEach(() => { cleanup(); for (const editor of editors.splice(0))
    editor.destroy(); __resetGraphNodeChipRuntimeForTests(); });
it('keeps null-campaign World pages, Save and tools available without eagerly loading either Graph', async () => {
    render(<Harness />);
    await waitFor(() => expect(binding().worldId).toBe('w'));
    expect(binding().editorInsertDisabled).toBe(false);
    expect(api.getNativeGraphCatalog).not.toHaveBeenCalled();
    expect(api.postWorldGraphProjection).not.toHaveBeenCalled();
    expect(api.postManagedWorldGraphProjection).not.toHaveBeenCalled();
    await act(async () => { await publication!.editCommands[0]!.invoke(); });
    expect(current.saveMarkdown).toHaveBeenCalledOnce();
});
it('inserts an existing reference, roundtrips Markdown and opens the same native entity through the actual NodeView', async () => {
    const view = render(<Harness />);
    const editor = current.editor!;
    act(() => binding().insertChip(pin, 'ent:fellinor', 'Fellinor'));
    const markdown = exportMarkdownWithAdapter(editor.getJSON());
    expect(markdown).toContain('#dmb-ref:graph-node:ent:fellinor');
    fireEvent.click(await screen.findByRole('button', { name: 'Fellinor', exact: true }));
    expect(await screen.findByRole('dialog', { name: 'Object · ent:fellinor' })).toBeInTheDocument();
    await waitFor(() => expect(api.inspectNativeGraph).toHaveBeenCalledWith(pin, { kind: 'entity', entity_id: 'ent:fellinor' }, expect.any(AbortSignal)));
    expect(api.postManagedWorldGraphProjection).not.toHaveBeenCalled();
    view.unmount();
    current = session('doc-a', 'w', makeEditor(importMarkdownWithAdapter(markdown).doc));
    render(<Harness />);
    fireEvent.click(await screen.findByRole('button', { name: 'Fellinor', exact: true }));
    expect(await screen.findByRole('dialog', { name: 'Object · ent:fellinor' })).toBeInTheDocument();
});
it('refuses stale insertion and Save callbacks after document replacement, even when World is unchanged', async () => {
    const view = render(<Harness />);
    const old = binding(), save = publication!.editCommands[0]!.invoke, oldEditor = current.editor!, oldSave = current.saveMarkdown;
    current = session('doc-b');
    view.rerender(<Harness />);
    act(() => old.insertChip(pin, 'ent:fellinor', 'Wrong page'));
    await act(async () => { await save(); });
    expect(oldEditor.getText()).toBe('');
    expect(current.editor!.getText()).toBe('');
    expect(oldSave).not.toHaveBeenCalled();
});
it('does not insert a cross-World pin or route another editor through the portal fallback', async () => {
    render(<Harness />);
    act(() => binding().insertChip({ ...pin, managed_world_id: 'other' }, 'ent:fellinor', 'Wrong World'));
    expect(current.editor!.getText()).toBe('');
    act(() => runtime.onSelectEditorNode?.('ent:fellinor', makeEditor()));
    expect(api.getNativeGraphCatalog).not.toHaveBeenCalled();
});
it('discards a delayed object read after document replacement', async () => {
    let resolve!: (value: NativeGraphCatalog) => void;
    vi.mocked(api.getNativeGraphCatalog).mockReturnValueOnce(new Promise(r => { resolve = r; }));
    const view = render(<Harness />);
    act(() => runtime.onSelectEditorNode?.('ent:fellinor', current.editor!));
    expect(screen.getByText('Opening object…')).toBeInTheDocument();
    current = session('doc-b', 'other');
    view.rerender(<Harness />);
    await act(async () => { resolve(catalog); });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(api.inspectNativeGraph).not.toHaveBeenCalled();
});
it('reports unavailable links accurately and supports explicit retry without mutation', async () => {
    vi.mocked(api.getNativeGraphCatalog).mockRejectedValueOnce(new Error('Read unavailable'));
    render(<Harness />);
    act(() => runtime.onSelectEditorNode?.('ent:fellinor', current.editor!));
    expect(await screen.findByRole('alert')).toHaveTextContent('Read unavailable');
    fireEvent.click(screen.getByRole('button', { name: 'Retry object' }));
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(current.editor!.getText()).toBe('');
});
it('disables insertion in conflict and invalidates retained callbacks on unmount', () => {
    const view = render(<Harness />), retained = binding();
    current = { ...current, phase: 'conflict' };
    view.rerender(<Harness />);
    act(() => retained.insertChip(pin, 'ent:fellinor', 'Conflict'));
    expect(current.editor!.getText()).toBe('');
    view.unmount();
    act(() => retained.insertChip(pin, 'ent:fellinor', 'Unmounted'));
    expect(current.editor!.getText()).toBe('');
});
it('search projection adopts native inspection and labels insertion rather than context selection', async () => {
    render(<Harness />);
    const context = binding();
    render(<BuildReferenceSearchProjection bindings={{ [BUILD_REFERENCE_CONTEXT_BINDING_ID]: context }}/>);
    fireEvent.click(await screen.findByRole('button', { name: 'Insert link to ent:fellinor' }));
    expect(exportMarkdownWithAdapter(current.editor!.getJSON())).toContain('#dmb-ref:graph-node:ent:fellinor');
    expect(api.getNativeGraphCatalog).toHaveBeenCalledWith({ managed_world_id: 'w', scope_mode: 'world', campaign_id: null }, expect.any(AbortSignal));
    expect(screen.queryByText('Use as context')).not.toBeInTheDocument();
});
it('blocks retained selection while a different World is being admitted', () => {
    const view = render(<Harness />), retained = binding();
    selection = { kind: 'loading' };
    view.rerender(<Harness />);
    act(() => retained.insertChip(pin, 'ent:fellinor', 'Pending World'));
    expect(current.editor!.getText()).toBe('');
    selection = { kind: 'managed', worldId: 'other' };
    view.rerender(<Harness />);
    expect(publication!.tools.find(t => t.id === 'build-find-existing-object')?.availability.status).toBe('disabled');
});
it('rejects a catalogue whose identity does not match its native pin', async () => {
    vi.mocked(api.getNativeGraphCatalog).mockResolvedValue({ ...catalog, catalogue: { ...catalog.catalogue, identity: { space_id: 'native-w', revision_id: 'another-revision' } } });
    render(<Harness />);
    act(() => runtime.onSelectEditorNode?.('ent:fellinor', current.editor!));
    expect(await screen.findByRole('alert')).toHaveTextContent('did not match this World');
    expect(api.inspectNativeGraph).not.toHaveBeenCalled();
});
it('opens existing dmb-node links without changing their persisted identity', async () => {
    current = session('doc-a', 'w', makeEditor(importMarkdownWithAdapter('[Fellinor](dmb-node:ent:fellinor)').doc));
    render(<Harness />);
    fireEvent.click(await screen.findByRole('button', { name: 'Fellinor', exact: true }));
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(exportMarkdownWithAdapter(current.editor!.getJSON())).toContain('dmb-node:ent:fellinor');
});
