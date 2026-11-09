import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import type { Editor } from '@tiptap/core';
import { useAgentInteraction } from '../../agentInteraction/AgentInteractionProvider';
import { usePublishSurfaceInteraction } from '../../agentInteraction/usePublishSurfaceInteraction';
import type { InspectionPin } from '../../api/nativeGraphInspection';
import {readCurrentNativeObjectReference} from '../../graphLens/readCurrentNativeObjectReference';
import type { AuthoredGraphReferenceV1 } from '../../api/types';
import { GraphNodeChipRuntimeProvider } from '../../graphReference/GraphNodeChipRuntime';
import { insertMarkdownReference } from '../../graphReference/insertMarkdownReference';
import { NativeGraphObjectPreview } from '../../graphLens/NativeGraphObjectPreview';
import { useOptionalMarkdownCanvasSession } from '../../markdownCanvas/MarkdownCanvasSession';
import { useSelectedWorldAdmission } from '../../selectedWorld/SelectedWorldContext';
import { useRulesLookupProjection } from '../../rulesLookup/rulesLookupProjection';
import { useStatblockWorkbenchProjection } from '../../statblocks/statblockWorkbenchProjection';
import { isEditorInteractive } from '../../workspaceDocument/workspaceDocumentAuthoringMachine';
import { buildBuildSurfaceInteractionPublication, type BuildReferenceContextBinding } from './buildBuildSurfaceInteractionPublication';
import { BUILD_REFERENCE_CONTEXT_BINDING_ID, BUILD_REFERENCE_SEARCH_PROJECTION_ID } from './buildReferenceIds';
import { BuildReferenceSearchProjection } from './BuildReferenceSearchProjection';
const unavailablePhases = new Set(['unloaded', 'loading', 'load_error', 'conflict']);
export interface BuildReferenceCapabilityProps {
    documentId: string | null;
    children?: ReactNode;
}
/** The admitted document owns World identity. Campaign labels are not Graph scopes. */
export function BuildReferenceCapability({ documentId, children }: BuildReferenceCapabilityProps) {
    const session = useOptionalMarkdownCanvasSession();
    const selection = useSelectedWorldAdmission();
    const { registerProjectionCatalog } = useAgentInteraction();
    const acceptedDocument = useMemo(() => {
        if (!documentId || session?.documentId !== documentId || !session.record || session.record.document_id !== documentId || unavailablePhases.has(session.phase))
            return null;
        return { documentId, worldId: session.record.world_id?.trim() || null };
    }, [documentId, session?.documentId, session?.record?.document_id, session?.record?.world_id, session?.phase]);
    const worldId = acceptedDocument?.worldId
        && selection.kind !== 'loading' && selection.kind !== 'error'
        && (selection.kind !== 'managed' || selection.worldId === acceptedDocument.worldId)
        ? acceptedDocument.worldId : null;
    const owner = useMemo(() => ({ documentId: acceptedDocument?.documentId ?? null, worldId, editor: session?.editor ?? null }), [acceptedDocument?.documentId, worldId, session?.editor]);
    const live = useRef<typeof owner | null>(null);
    const request = useRef<AbortController | null>(null);
    const [preview, setPreview] = useState<AuthoredGraphReferenceV1 | null>(null);
    const [opening, setOpening] = useState<{
        nodeId: string;
        error: string | null;
    } | null>(null);
    useLayoutEffect(() => {
        live.current = owner;
        setPreview(null);
        setOpening(null);
        return () => { live.current = null; request.current?.abort(); };
    }, [owner]);
    const insertionAllowed = Boolean(owner.editor && !owner.editor.isDestroyed && session && isEditorInteractive(session.phase) && worldId);
    const liveInsertionAllowed = useRef(false);
    useLayoutEffect(() => { liveInsertionAllowed.current = insertionAllowed; return () => { liveInsertionAllowed.current = false; }; }, [insertionAllowed]);
    const insertChip = useCallback((pin: InspectionPin, nodeId: string, label: string) => {
        if (live.current !== owner || !liveInsertionAllowed.current || !owner.editor || owner.editor.isDestroyed || pin.managed_world_id !== owner.worldId || pin.scope_mode !== 'world' || pin.campaign_id !== null)
            return;
        insertMarkdownReference(owner.editor, { kind: 'ref', refType: 'graph-node', refId: nodeId, label });
    }, [owner]);
    const openNode = useCallback(async (nodeId: string, sourceEditor?: Editor) => {
        // TipTap portals may use the module fallback runtime. Never use that fallback
        // to resolve another editor's link under this document's World authority.
        if (live.current !== owner || !owner.worldId || !owner.documentId || !sourceEditor || sourceEditor !== owner.editor || sourceEditor.isDestroyed)
            return;
        request.current?.abort();
        const abort = new AbortController();
        request.current = abort;
        setPreview(null);
        setOpening({ nodeId, error: null });
        try {
            const reference = await readCurrentNativeObjectReference(owner.worldId, nodeId, abort.signal);
            if (abort.signal.aborted || live.current !== owner)
                return;
            setOpening(null);
            setPreview(reference);
        }
        catch (error) {
            if (!abort.signal.aborted && live.current === owner)
                setOpening({ nodeId, error: error instanceof Error ? error.message : 'This object could not be opened.' });
        }
    }, [owner]);
    const referenceContext = useMemo<BuildReferenceContextBinding | null>(() => worldId && acceptedDocument ? {
        schema: 'dmb_build_reference_context_v3', documentId: acceptedDocument.documentId, worldId, insertChip, editorInsertDisabled: !insertionAllowed,
    } : null, [worldId, acceptedDocument, insertChip, insertionAllowed]);
    const mounted = useRef(false), liveDocument = useRef<string | null>(null);
    useEffect(() => { mounted.current = true; liveDocument.current = documentId; return () => { mounted.current = false; liveDocument.current = null; }; }, [documentId]);
    const saveDocument = useMemo(() => {
        const boundId = documentId, boundSession = session;
        return async () => {
            if (!mounted.current || liveDocument.current !== boundId || !boundId || !boundSession || boundSession.documentId !== boundId || unavailablePhases.has(boundSession.phase) || boundSession.record?.document_id !== boundId)
                return;
            await boundSession.saveMarkdown();
        };
    }, [documentId, session]);
    const publication = useMemo(() => buildBuildSurfaceInteractionPublication({ documentId, acceptedDocument, referenceContext,
        documentSave: acceptedDocument && session ? { saveDisabled: session.saveDisabled, disabledReason: session.saveDisabled ? session.statusLabel : undefined, save: saveDocument } : null,
    }), [documentId, acceptedDocument, referenceContext, session, saveDocument]);
    usePublishSurfaceInteraction(publication);
    useRulesLookupProjection('build', true);
    useStatblockWorkbenchProjection('build');
    useEffect(() => registerProjectionCatalog({ projectionId: BUILD_REFERENCE_SEARCH_PROJECTION_ID, surfaceId: 'build', kind: 'tool', preferredSize: 'wide', requiredBindingIds: [BUILD_REFERENCE_CONTEXT_BINDING_ID], render: ({ bindings }) => <BuildReferenceSearchProjection bindings={bindings}/> }), [registerProjectionCatalog]);
    const runtime = useMemo(() => ({ nodeViews: {}, activeNodeId: preview?.node_id ?? null, onSelectNode: () => undefined, onSelectEditorNode: (nodeId: string, editor: Editor) => { void openNode(nodeId, editor); }, exactGraphScope: null }), [preview?.node_id, openNode]);
    return <GraphNodeChipRuntimeProvider value={runtime}>
  {children ?? null}
  {opening && <section aria-label="Document object preview">{opening.error ? <><p role="alert">{opening.error}</p><button type="button" onClick={() => void openNode(opening.nodeId, owner.editor ?? undefined)}>Retry object</button></> : <p role="status">Opening object…</p>}<button type="button" onClick={() => { request.current?.abort(); setOpening(null); }}>Close object</button></section>}
  {preview && <NativeGraphObjectPreview reference={preview} onClose={() => setPreview(null)}/>}
 </GraphNodeChipRuntimeProvider>;
}
