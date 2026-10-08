import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { Editor, JSONContent } from "@tiptap/core";
import { EditorContent } from "@tiptap/react";

import {
  commitWorldOwnedPlanMarkdownWrite,
  createWorldOwnedPlan,
  getManagedWorldPlanContext,
  LiveApiError,
  getPlanView,
  getWorldOwnedPlanCommittedRevision,
  getWorldOwnedPlanSnapshot,
  listWorldOwnedPlans,
  prepareTiptapMarkdownWrite,
} from "../api/liveApi";
import type { PlanViewProjection, WorldOwnedPlanRecordV2, WorldOwnedPlanSnapshotV2 } from "../api/types";
import { MarkdownEditorCore } from "../tiptap/MarkdownEditorCore";
import { defaultMarkdownDocumentAdapter } from "../tiptap/MarkdownDocumentAdapter";
import { AppChrome, type AppChromeToolsGeneration } from "../chrome/AppChrome";
import { PlanSurfaceShell } from "./PlanSurfaceShell";
import { markdownToTiptapDoc, type MarkdownImportDiagnostic } from "../tiptap/markdown/markdownToTiptap";
import { semanticMarkdownSerializationDiagnostics } from "../tiptap/markdown/semanticMarkdownSafety";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { isCanonicalUuid, CANONICAL_SHA256_RE } from "../playSurface/runbook/nativeRunbookProjection";
import { WorldPlanSurfaceContext } from "./components/PlanSurfaceContext";
import {
  useWorldPlanGraphReferenceActivation,
  WorldPlanGraphReferenceActivationProvider,
} from "./components/WorldPlanGraphReferenceActivation";
import { PlanSurfaceCanvasFrame } from "./components/PlanSurfaceCanvas";
import { PlanConversationDockAdapter } from "./components/PlanConversationDockAdapter";
import { WorldPlanAgentConversation } from "./components/WorldPlanAgentConversation";
import {
  buildWorldPlanCardProjectionModel,
  WorldPlanCardProjection,
  worldPlanCardTargetKey,
  worldPlanCardTargetKeys,
  type WorldPlanCardBasis,
  type WorldPlanCardTarget,
  type WorldPlanCardNode,
} from "./components/WorldPlanCardProjection";
import "./components/WorldPlanCardProjection.css";
import {
  applyWorldPlanEditProposal,
  captureWorldPlanEditTarget,
  previewWorldPlanEditProposal,
  type WorldPlanEditBridge,
  type WorldPlanEditEditorState,
} from "./agentEdit/planAgentEditProposal";
import { toAppChromeToolsGeneration, type MarkdownEditorToolbarModel } from "../tiptap/MarkdownEditorToolbar";
import { CALLOUT_KINDS, defaultCalloutLabel } from "../tiptap/markdown/calloutMarkdown";
import { SemanticMarkdownPaste } from "../tiptap/extensions/SemanticMarkdownPaste";
import { usePublishSurfaceInteraction } from "../agentInteraction/usePublishSurfaceInteraction";
import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";
import { buildWorldPlanSurfaceIdentity, createWorldPlanLocalDraftId, worldPlanWorkObject } from "./worldPlanIdentity";
import "../tiptap/prepMarkdownThemes.css";
import "../tiptap/tiptapSpike.css";

type LoadStatus = "loading" | "ready" | "error";

type SelectedWorldPlanPlayableTarget = {
  target: WorldPlanCardTarget;
  worldId: string;
  documentId: string;
  revision: number;
  contentSha256: string;
  stale: boolean;
};

type SelectedWorldPlanPlayableEditTarget = {
  target: WorldPlanCardTarget;
  worldId: string;
  documentId: string;
  revision: number;
  contentSha256: string;
  generation: number;
  stale: boolean;
};

function markdownFidelityWarnings(
  importDiagnostics: readonly MarkdownImportDiagnostic[],
  editorDocument: JSONContent,
): string[] {
  const importWarnings = importDiagnostics
    .filter((diagnostic) => diagnostic.level === "warning")
    .map((diagnostic) => `${diagnostic.line != null ? `Line ${diagnostic.line}: ` : ""}${diagnostic.message}`);
  let serializationWarnings: string[];
  try {
    serializationWarnings = semanticMarkdownSerializationDiagnostics(editorDocument)
      .map((diagnostic) => diagnostic.message);
  } catch {
    serializationWarnings = ["The editor could not verify this document's Markdown serialization safely."];
  }
  return [...new Set([...importWarnings, ...serializationWarnings])];
}

function markdownFidelityDetails(warnings: readonly string[]): string {
  const details = warnings.slice(0, 4).map((warning) => `• ${warning}`).join(" ");
  const remainder = warnings.length > 4 ? ` ${warnings.length - 4} more issue(s) are not shown.` : "";
  return `${details}${remainder}`;
}

function markdownFidelityWarningText(warnings: readonly string[]): string {
  return `This Plan contains Markdown the editor cannot safely preserve. Editing and Save are disabled to protect the saved text; the original and local recovery copy remain unchanged. Resolve these constructs in the source and reopen the Plan. ${markdownFidelityDetails(warnings)}`;
}

function markdownFidelityRejectionText(warnings: readonly string[]): string {
  return `This edit was reverted to protect the saved Plan. The editor was restored from the last safe Markdown, and the saved text and local recovery copy are unchanged. ${markdownFidelityDetails(warnings)}`;
}

export function PlanSurfacePage() {
  const selectedWorld = useSelectedWorld();
  const managedWorldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [planView, setPlanView] = useState<PlanViewProjection | null>(null);
  const [editorTools, setEditorTools] = useState<AppChromeToolsGeneration | null>(null);

  useEffect(() => {
    if (selectedWorld.kind === "loading" || selectedWorld.kind === "error" || managedWorldId) return;
    let cancelled = false;
    (async () => {
      setStatus("loading");
      setError(null);
      setPlanView(null);
      try {
        const response = await getPlanView(managedWorldId);
        if (!cancelled) {
          if (managedWorldId && (
            response.world_id !== managedWorldId
            || response.campaign_id !== managedWorldId
          )) {
            throw new Error(`Plan context does not match selected World ${managedWorldId}.`);
          }
          setPlanView(response);
          setStatus("ready");
        }
      } catch (loadError) {
        if (!cancelled) {
          setStatus("error");
          setError(loadError instanceof Error ? loadError.message : "Failed to load plan context");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [managedWorldId, selectedWorld.kind]);

  if (selectedWorld.kind === "loading") {
    return <AppChrome activeRoute="plan"><main className="app-status"><p>Resolving selected World…</p></main></AppChrome>;
  }
  if (selectedWorld.kind === "error") {
    return <AppChrome activeRoute="plan"><main className="app-status app-error"><h1>Plan</h1><p>{selectedWorld.message}</p></main></AppChrome>;
  }
  if (managedWorldId) return (
    <WorldPlanGraphReferenceActivationProvider worldId={managedWorldId}>
      <WorldOwnedPlanPage key={managedWorldId} worldId={managedWorldId} worldName={selectedWorld.kind === "managed" ? selectedWorld.name : managedWorldId} />
    </WorldPlanGraphReferenceActivationProvider>
  );

  if (status === "loading") {
    return (
      <AppChrome activeRoute="plan">
        <main className="app-status">
          <p>Loading plan surface…</p>
        </main>
      </AppChrome>
    );
  }

  if (status === "error" || !planView) {
    return (
      <AppChrome activeRoute="plan">
        <main className="app-status app-error">
          <h1>Plan</h1>
          <p>{error ?? "Unable to load plan context."}</p>
        </main>
      </AppChrome>
    );
  }

  return (
    <AppChrome activeRoute="plan" editorTools={editorTools} editToolboxLayout="dock">
      <PlanSurfaceShell planView={planView} onEditorToolsChange={setEditorTools} />
    </AppChrome>
  );
}

interface WorldPlanLocalDraftV2 {
  schema_version: "dmb_plan_promotion_recovery_v2";
  scope_mode: "world";
  world_id: string;
  document_id: string | null;
  local_draft_id?: string | null;
  title: string;
  markdown: string;
  revision: number | null;
  edit_generation?: number;
  create_uncertain?: boolean;
  uncertain_create_draft?: {
    title: string;
    markdown: string;
    edit_generation: number;
    bound_document_id?: string | null;
  } | null;
  pending_write?: {
    phase: "prepare" | "commit";
    base_revision: number;
    prepared_revision: number | null;
    base_markdown: string;
    markdown: string;
    edit_generation: number;
  } | null;
}

function worldPlanLocalDraftKey(worldId: string): string {
  return `dmb:world-plan-local-draft:v2:${worldId}`;
}

function readWorldPlanLocalDraft(worldId: string): WorldPlanLocalDraftV2 | null {
  try {
    const raw = localStorage.getItem(worldPlanLocalDraftKey(worldId));
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<WorldPlanLocalDraftV2>;
    if (value.schema_version !== "dmb_plan_promotion_recovery_v2" || value.scope_mode !== "world"
      || value.world_id !== worldId || typeof value.title !== "string" || typeof value.markdown !== "string") return null;
    const documentId = typeof value.document_id === "string" ? value.document_id : null;
    const existingLocalId = typeof value.local_draft_id === "string"
      && value.local_draft_id.startsWith(`local-plan:${worldId}:`)
      ? value.local_draft_id : null;
    const localDraftId = existingLocalId ?? (documentId === null ? createWorldPlanLocalDraftId(worldId) : null);
    const draft: WorldPlanLocalDraftV2 = {
      schema_version: "dmb_plan_promotion_recovery_v2",
      scope_mode: "world",
      world_id: worldId,
      document_id: documentId,
      local_draft_id: localDraftId,
      title: value.title,
      markdown: value.markdown,
      revision: typeof value.revision === "number" ? value.revision : null,
      edit_generation: typeof value.edit_generation === "number" ? value.edit_generation : 0,
      create_uncertain: value.create_uncertain === true,
      uncertain_create_draft: value.uncertain_create_draft
        && typeof value.uncertain_create_draft === "object"
        && typeof value.uncertain_create_draft.title === "string"
        && typeof value.uncertain_create_draft.markdown === "string"
        && typeof value.uncertain_create_draft.edit_generation === "number"
        ? {
          title: value.uncertain_create_draft.title,
          markdown: value.uncertain_create_draft.markdown,
          edit_generation: value.uncertain_create_draft.edit_generation,
          bound_document_id: typeof value.uncertain_create_draft.bound_document_id === "string"
            ? value.uncertain_create_draft.bound_document_id
            : null,
        }
        : null,
      pending_write: value.pending_write && typeof value.pending_write === "object"
        && (value.pending_write.phase === "prepare" || value.pending_write.phase === "commit")
        && typeof value.pending_write.base_revision === "number"
        && typeof value.pending_write.base_markdown === "string"
        && typeof value.pending_write.markdown === "string"
        && typeof value.pending_write.edit_generation === "number"
        ? {
          phase: value.pending_write.phase,
          base_revision: value.pending_write.base_revision,
          prepared_revision: typeof value.pending_write.prepared_revision === "number"
            ? value.pending_write.prepared_revision
            : null,
          base_markdown: value.pending_write.base_markdown,
          markdown: value.pending_write.markdown,
          edit_generation: value.pending_write.edit_generation,
        }
        : null,
    };
    return draft;
  } catch {
    return null;
  }
}

function persistWorldPlanLocalDraft(
  worldId: string,
  draft: Pick<WorldPlanLocalDraftV2, "document_id" | "title" | "markdown" | "revision">
    & Partial<Pick<WorldPlanLocalDraftV2, "local_draft_id" | "edit_generation" | "create_uncertain" | "uncertain_create_draft" | "pending_write">>,
): void {
  try {
    const previous = readWorldPlanLocalDraft(worldId);
    const uncertainCreateDraft = Object.hasOwn(draft, "uncertain_create_draft")
      ? draft.uncertain_create_draft ?? null
      : previous?.uncertain_create_draft ?? null;
    localStorage.setItem(worldPlanLocalDraftKey(worldId), JSON.stringify({
      schema_version: "dmb_plan_promotion_recovery_v2",
      scope_mode: "world",
      world_id: worldId,
      local_draft_id: previous?.local_draft_id ?? null,
      edit_generation: 0,
      create_uncertain: false,
      pending_write: null,
      uncertain_create_draft: uncertainCreateDraft,
      ...draft,
    } satisfies WorldPlanLocalDraftV2));
  } catch {
    // Browser-local recovery is best effort; durable Save remains server-owned.
  }
}

function worldPlanCardBasisFromSnapshot(
  snapshot: WorldOwnedPlanSnapshotV2,
  hasPendingWrite = false,
): WorldPlanCardBasis {
  if (hasPendingWrite) return { status: "unavailable" };
  if (snapshot.record.content_status === "committed") {
    return {
      status: "verified",
      revision: snapshot.loaded_revision,
      contentSha256: snapshot.content_sha256,
    };
  }
  if (snapshot.record.content_status === "draft") return { status: "server-draft" };
  return { status: "unavailable" };
}

function WorldOwnedPlanPage({ worldId, worldName }: { worldId: string; worldName: string }) {
  const { activateNode } = useWorldPlanGraphReferenceActivation();
  const [localDraft] = useState(() => {
    const existing = readWorldPlanLocalDraft(worldId);
    const requestedDocumentId = new URLSearchParams(window.location.search).get("documentId")?.trim();
    if (existing || requestedDocumentId) return existing;
    const fresh: WorldPlanLocalDraftV2 = {
      schema_version: "dmb_plan_promotion_recovery_v2",
      scope_mode: "world",
      world_id: worldId,
      document_id: null,
      local_draft_id: createWorldPlanLocalDraftId(worldId),
      title: "Plan",
      markdown: "",
      revision: null,
    };
    persistWorldPlanLocalDraft(worldId, fresh);
    return fresh;
  });
  const [initialDocumentId] = useState(() =>
    new URLSearchParams(window.location.search).get("documentId")?.trim() || localDraft?.document_id || null,
  );
  const initialLocalDraft = localDraft?.document_id === initialDocumentId ? localDraft : null;
  const [records, setRecords] = useState<WorldOwnedPlanRecordV2[]>([]);
  const [documentId, setDocumentId] = useState<string | null>(initialDocumentId);
  const [localDraftId, setLocalDraftId] = useState(() => initialLocalDraft?.local_draft_id ?? createWorldPlanLocalDraftId(worldId));
  const [title, setTitle] = useState(initialLocalDraft?.title ?? "Plan");
  const [markdown, setMarkdown] = useState(initialLocalDraft?.markdown ?? "");
  const [savedBasis, setSavedBasis] = useState<WorldPlanCardBasis>({ status: "unavailable" });
  const [createUncertain, setCreateUncertain] = useState(initialLocalDraft?.create_uncertain ?? false);
  const [uncertainCreateDraft, setUncertainCreateDraft] = useState(localDraft?.uncertain_create_draft ?? null);
  const [recoveryConflict, setRecoveryConflict] = useState(false);
  const [serverDraft, setServerDraft] = useState<{
    title: string;
    markdown: string;
    revision: number;
    contentSha256: string;
    contentStatus: WorldOwnedPlanRecordV2["content_status"];
  } | null>(null);
  const [editorGeneration, setEditorGeneration] = useState(0);
  const [selectionGeneration, setSelectionGeneration] = useState(0);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [routeCardsViewRequested, setRouteCardsViewRequested] = useState(
    () => new URLSearchParams(window.location.search).get("view") === "cards",
  );
  const [selectedCardViewIdentity, setSelectedCardViewIdentity] = useState<string | null>(null);
  const [selectedPlayableTarget, setSelectedPlayableTarget] = useState<SelectedWorldPlanPlayableTarget | null>(null);
  const [selectedPlayableEditTarget, setSelectedPlayableEditTarget] = useState<SelectedWorldPlanPlayableEditTarget | null>(null);
  const [playableEditTargetGeneration, setPlayableEditTargetGeneration] = useState(0);
  const importedMarkdown = useMemo(() => markdownToTiptapDoc(markdown), [markdown]);
  const editorContent = importedMarkdown.doc;
  const fidelityWarnings = useMemo(
    () => markdownFidelityWarnings(importedMarkdown.diagnostics, editorContent),
    [importedMarkdown, editorContent],
  );
  const fidelityBlocked = fidelityWarnings.length > 0;
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [initialLoadAttempt, setInitialLoadAttempt] = useState(0);
  const [retryTarget, setRetryTarget] = useState<
    { kind: "initial" } | { kind: "document"; documentId: string } | null
  >(null);
  const [saving, setSaving] = useState(false);
  const [startingPlay, setStartingPlay] = useState(false);
  const [startPlayError, setStartPlayError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(false);
  const selectionEpochRef = useRef(0);
  const documentIdRef = useRef(initialDocumentId);
  const localDraftIdRef = useRef(localDraftId);
  const revisionRef = useRef<number | null>(initialLocalDraft?.revision ?? null);
  const titleRef = useRef(initialLocalDraft?.title ?? "Plan");
  const markdownRef = useRef(initialLocalDraft?.markdown ?? "");
  const serverDigestRef = useRef<string | null>(null);
  const editGenerationRef = useRef(initialLocalDraft?.edit_generation ?? 0);
  const selectionGenerationRef = useRef(0);
  const selectedPlayableEditTargetRef = useRef<SelectedWorldPlanPlayableEditTarget | null>(null);
  const playableEditTargetGenerationRef = useRef(0);
  const playableEditTargetStaleRef = useRef(false);
  selectedPlayableEditTargetRef.current = selectedPlayableEditTarget;
  const pendingWriteRef = useRef(initialLocalDraft?.pending_write ?? null);
  const uncertainCreateDraftRef = useRef(localDraft?.uncertain_create_draft ?? null);
  const savingRef = useRef(false);
  const startPlayRequestRef = useRef(0);
  const statusRef = useRef(status);
  statusRef.current = status;
  const switchingDocumentRef = useRef(false);
  const serverTitleRef = useRef("");
  const serverMarkdownRef = useRef("");
  const editorRef = useRef<Editor | null>(null);
  const getLiveFidelityWarnings = useCallback((editorDocument?: JSONContent) => {
    const currentMarkdown = markdownRef.current;
    const currentImport = currentMarkdown === markdown
      ? importedMarkdown
      : markdownToTiptapDoc(currentMarkdown);
    return markdownFidelityWarnings(
      currentImport.diagnostics,
      editorDocument ?? editorRef.current?.getJSON() ?? currentImport.doc,
    );
  }, [importedMarkdown, markdown]);
  const workObject = useMemo(() => worldPlanWorkObject({ worldId, documentId, localDraftId }), [worldId, documentId, localDraftId]);
  const surfaceIdentity = useMemo(() => buildWorldPlanSurfaceIdentity({ worldId, documentId, localDraftId }), [worldId, documentId, localDraftId]);
  const activePublication = useMemo<SurfaceInteractionPublication | null>(() => status === "ready" ? {
    surfaceId: "plan",
    label: "World Plan",
    identity: surfaceIdentity,
    canvas: {
      canvasId: "markdown-canvas",
      workObject,
    },
    agentContext: null,
    tools: [],
    editCommands: [],
    projections: [],
    projectionBindings: [],
  } : null, [status, surfaceIdentity, workObject]);
  usePublishSurfaceInteraction(activePublication);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const selectedViewIsCurrent = (epoch: number, expectedDocumentId: string | null) =>
    mountedRef.current
    && selectionEpochRef.current === epoch
    && documentIdRef.current === expectedDocumentId;

  const editorIdentity = `${worldId}:${documentId ?? localDraftId}:${editorGeneration}`;
  const editorIdentityRef = useRef(editorIdentity);
  editorIdentityRef.current = editorIdentity;
  const isCurrentEditTarget = useMemo(() => {
    const epoch = selectionEpochRef.current;
    return (allowDuringSave = false) => mountedRef.current
      && !switchingDocumentRef.current
      && selectionEpochRef.current === epoch
      && documentIdRef.current === documentId
      && localDraftIdRef.current === localDraftId
      && editorIdentityRef.current === editorIdentity
      && statusRef.current === "ready"
      && (allowDuringSave || !savingRef.current);
  }, [documentId, localDraftId, editorIdentity]);
  const setCurrentEditor = (next: Editor | null) => {
    editorRef.current = next;
    setEditor(next);
  };

  useLayoutEffect(() => {
    if (!editor) return;
    const onSelectionUpdate = () => {
      selectionGenerationRef.current += 1;
      setSelectionGeneration(selectionGenerationRef.current);
    };
    editor.on("selectionUpdate", onSelectionUpdate);
    return () => { editor.off("selectionUpdate", onSelectionUpdate); };
  }, [editor]);

  const worldEditStateGetterRef = useRef<() => WorldPlanEditEditorState>(() => ({
    editor: null,
    documentId: null,
    worldId,
    baseRevision: null,
    baseContentSha256: null,
    sourceMarkdown: "",
    draftGeneration: 0,
    selectionGeneration: 0,
    playableTarget: null,
    playableTargetGeneration: 0,
    playableTargetStale: false,
    canEdit: false,
  }));
  worldEditStateGetterRef.current = () => ({
    editor: editorRef.current,
    documentId: documentIdRef.current,
    worldId,
    baseRevision: revisionRef.current,
    baseContentSha256: serverDigestRef.current,
    sourceMarkdown: markdownRef.current,
    draftGeneration: editGenerationRef.current,
    selectionGeneration: selectionGenerationRef.current,
    playableTarget: selectedPlayableEditTargetRef.current?.target ?? null,
    playableTargetGeneration: playableEditTargetGenerationRef.current,
    playableTargetStale: playableEditTargetStaleRef.current,
    currentSceneTarget: selectedPlayableTarget?.target.kind === "scene" ? selectedPlayableTarget.target : null,
    currentSceneTargetStale: selectedPlayableTargetStale,
    currentSceneTargetLabel: cardTargetLabel(selectedPlayableTarget?.target ?? null),
    playableTargetLabel: cardTargetLabel(selectedPlayableEditTargetRef.current?.target ?? null),
    canEdit: Boolean(
      documentIdRef.current
      && serverDigestRef.current
      && isCurrentEditTarget()
      && !savingRef.current
      && !createUncertain
      && !recoveryConflict
      && pendingWriteRef.current === null
      && getLiveFidelityWarnings(editorRef.current?.getJSON()).length === 0
    ),
  });
  const worldPlanEditBridge = useMemo<WorldPlanEditBridge>(() => ({
    preview: previewWorldPlanEditProposal,
    capture: () => captureWorldPlanEditTarget(
      worldEditStateGetterRef.current(),
      () => worldEditStateGetterRef.current(),
    ),
    apply: (captured, admitted, expectedAgentBinding, getAgentBinding) => applyWorldPlanEditProposal({
      captured,
      admitted,
      getCurrent: () => worldEditStateGetterRef.current(),
      expectedAgentBinding,
      getAgentBinding,
    }),
  }), []);

  const toolbarModel = useMemo<MarkdownEditorToolbarModel>(() => {
    const action = (id: string, label: string, invoke: (active: Editor) => void, disabled = false) => ({
      id,
      label,
      onClick: () => {
        const active = editorRef.current;
        if (!active || !isCurrentEditTarget() || disabled) return;
        const fidelityIssues = getLiveFidelityWarnings(active.getJSON());
        if (fidelityIssues.length) {
          setError(markdownFidelityWarningText(fidelityIssues));
          return;
        }
        invoke(active);
      },
      disabled: !editor || status !== "ready" || saving || fidelityBlocked || disabled,
    });
    return {
      sections: [
        {
          id: "world-plan-format",
          title: "Text",
          defaultOpen: true,
          actions: [
            action("world-plan-bold", "Bold", (active) => { active.chain().focus().toggleBold().run(); }),
            action("world-plan-italic", "Italic", (active) => { active.chain().focus().toggleItalic().run(); }),
            action("world-plan-heading", "Heading", (active) => { active.chain().focus().toggleHeading({ level: 2 }).run(); }),
          ],
        },
        {
          id: "world-plan-blocks",
          title: "Insert blocks",
          defaultOpen: true,
          actions: CALLOUT_KINDS.map((kind) => action(
            `world-plan-insert-${kind}`,
            defaultCalloutLabel(kind),
            (active) => { active.chain().focus().insertCallout({ kind }).run(); },
          )),
        },
      ],
    };
  }, [editor, fidelityBlocked, getLiveFidelityWarnings, isCurrentEditTarget, saving, status]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const context = await getManagedWorldPlanContext(worldId);
        if (context.schema_version !== "dmb_managed_world_plan_context_v2"
          || context.scope_mode !== "world" || context.world_id !== worldId
          || context.campaign_id !== null || context.session !== null) {
          throw new Error("Managed Plan context does not match the selected World.");
        }
        const inventory = await listWorldOwnedPlans(worldId);
        if (inventory.world_id !== worldId) throw new Error("World Plan inventory does not match the selected World.");
        if (cancelled) return;
        setRecords(inventory.records);
        if (initialDocumentId) {
          const snapshot = await getWorldOwnedPlanSnapshot(initialDocumentId);
          if (snapshot.record.world_id !== worldId || snapshot.record.campaign_id !== null || snapshot.record.kind !== "plan") {
            throw new Error("This Plan does not belong to the selected World.");
          }
          if (cancelled) return;
          const recoverLocal = localDraft?.document_id === initialDocumentId;
          const revisionChangedUnderDraft = recoverLocal
            && localDraft.revision !== snapshot.loaded_revision
            && !localDraft.pending_write;
          const nextTitle = recoverLocal ? localDraft.title : snapshot.record.title;
          const nextMarkdown = recoverLocal ? localDraft.markdown : snapshot.markdown;
          documentIdRef.current = initialDocumentId;
          revisionRef.current = snapshot.loaded_revision;
          titleRef.current = nextTitle;
          markdownRef.current = nextMarkdown;
          serverTitleRef.current = snapshot.record.title;
          serverMarkdownRef.current = snapshot.markdown;
          serverDigestRef.current = snapshot.content_sha256;
          setSavedBasis(worldPlanCardBasisFromSnapshot(snapshot, recoverLocal && Boolean(localDraft.pending_write)));
          pendingWriteRef.current = recoverLocal ? localDraft.pending_write ?? null : null;
          setTitle(nextTitle);
          setMarkdown(nextMarkdown);
          setEditorGeneration((value) => value + 1);
          if (revisionChangedUnderDraft) {
            setRecoveryConflict(true);
            setServerDraft({
              title: snapshot.record.title,
              markdown: snapshot.markdown,
              revision: snapshot.loaded_revision,
              contentSha256: snapshot.content_sha256,
              contentStatus: snapshot.record.content_status,
            });
            setError("The saved Plan changed since this local draft. Your draft is preserved; choose which version to keep before saving.");
          }
          if (!new URLSearchParams(window.location.search).has("documentId")) {
            const url = new URL(window.location.href);
            url.searchParams.set("world", worldId);
            url.searchParams.set("documentId", initialDocumentId);
            window.history.replaceState({}, "", `${url.pathname}${url.search}`);
          }
          persistWorldPlanLocalDraft(worldId, {
            document_id: initialDocumentId,
            title: nextTitle,
            markdown: nextMarkdown,
            revision: snapshot.loaded_revision,
            edit_generation: initialLocalDraft?.edit_generation ?? 0,
            pending_write: pendingWriteRef.current,
            create_uncertain: false,
          });
        }
        else if (localDraft?.document_id === null) {
          documentIdRef.current = null;
          revisionRef.current = null;
          serverDigestRef.current = null;
          setSavedBasis({ status: "unavailable" });
          persistWorldPlanLocalDraft(worldId, localDraft);
        }
        if (!cancelled) {
          setRetryTarget(null);
          setStatus("ready");
        }
      } catch (reason) {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "World Plan could not be loaded.");
          setRetryTarget({ kind: "initial" });
          setStatus("error");
        }
      }
    })();
    return () => { cancelled = true; };
  }, [initialDocumentId, initialLoadAttempt, localDraft, worldId]);

  const openPlan = async (nextDocumentId: string, allowRetry = false) => {
    if (savingRef.current || (statusRef.current !== "ready" && !allowRetry)) return;
    const epoch = ++selectionEpochRef.current;
    const priorDocumentId = documentIdRef.current;
    startPlayRequestRef.current += 1;
    setStartingPlay(false);
    setStartPlayError(null);
    // Close the outgoing edit lease before React paints the loading state.
    switchingDocumentRef.current = true;
    setSavedBasis({ status: "unavailable" });
    editorRef.current?.setEditable(false);
    editorIdentityRef.current = `${worldId}:${nextDocumentId}:${editorGeneration + 1}`;
    editorRef.current = null;
    setEditor(null);
    setStatus("loading");
    setRetryTarget({ kind: "document", documentId: nextDocumentId });
    setError(null);
    try {
      const snapshot = await getWorldOwnedPlanSnapshot(nextDocumentId);
      if (snapshot.record.world_id !== worldId || snapshot.record.campaign_id !== null || snapshot.record.kind !== "plan") {
        throw new Error("This Plan does not belong to the selected World.");
      }
      if (!selectedViewIsCurrent(epoch, priorDocumentId)) return;
      const preservedUncertainDraft = readWorldPlanLocalDraft(worldId)?.uncertain_create_draft
        ?? uncertainCreateDraftRef.current;
      const url = new URL(window.location.href);
      url.searchParams.set("world", worldId);
      url.searchParams.set("documentId", nextDocumentId);
      url.searchParams.delete("view");
      window.history.pushState({}, "", `${url.pathname}${url.search}`);
      setRouteCardsViewRequested(false);
      setSelectedCardViewIdentity(null);
      documentIdRef.current = nextDocumentId;
      revisionRef.current = snapshot.loaded_revision;
      titleRef.current = snapshot.record.title;
      markdownRef.current = snapshot.markdown;
      serverTitleRef.current = snapshot.record.title;
      serverMarkdownRef.current = snapshot.markdown;
      serverDigestRef.current = snapshot.content_sha256;
      setSavedBasis(worldPlanCardBasisFromSnapshot(snapshot));
      pendingWriteRef.current = null;
      uncertainCreateDraftRef.current = preservedUncertainDraft;
      setUncertainCreateDraft(preservedUncertainDraft);
      setDocumentId(nextDocumentId);
      setTitle(snapshot.record.title);
      setMarkdown(snapshot.markdown);
      setEditorGeneration((value) => value + 1);
      setRecoveryConflict(false);
      setServerDraft(null);
      setCreateUncertain(false);
      persistWorldPlanLocalDraft(worldId, {
        document_id: nextDocumentId,
        title: snapshot.record.title,
        markdown: snapshot.markdown,
        revision: snapshot.loaded_revision,
        edit_generation: editGenerationRef.current,
        pending_write: null,
        create_uncertain: false,
      });
      setMessage(null);
      switchingDocumentRef.current = false;
      setRetryTarget(null);
      setStatus("ready");
    } catch (reason) {
      if (!selectedViewIsCurrent(epoch, priorDocumentId)) return;
      setError(reason instanceof Error ? reason.message : "Plan could not be opened.");
      setStatus("error");
    }
  };

  const retryPlanLoad = () => {
    if (statusRef.current !== "error" || !retryTarget) return;
    if (retryTarget.kind === "document") {
      void openPlan(retryTarget.documentId, true);
      return;
    }
    setStatus("loading");
    setError(null);
    setInitialLoadAttempt((attempt) => attempt + 1);
  };

  const resetBlankPlan = () => {
    if (statusRef.current !== "ready" || savingRef.current) return;
    ++selectionEpochRef.current;
    startPlayRequestRef.current += 1;
    setStartingPlay(false);
    setStartPlayError(null);
    switchingDocumentRef.current = false;
    editorIdentityRef.current = `${worldId}:blank:${editorGeneration + 1}`;
    editorRef.current = null;
    setEditor(null);
    documentIdRef.current = null;
    const nextLocalDraftId = createWorldPlanLocalDraftId(worldId);
    localDraftIdRef.current = nextLocalDraftId;
    setLocalDraftId(nextLocalDraftId);
    revisionRef.current = null;
    titleRef.current = "Plan";
    markdownRef.current = "";
    serverTitleRef.current = "";
    serverMarkdownRef.current = "";
    serverDigestRef.current = null;
    setSavedBasis({ status: "unavailable" });
    pendingWriteRef.current = null;
    setRecoveryConflict(false);
    setServerDraft(null);
    setCreateUncertain(false);
    const url = new URL(window.location.href);
    url.searchParams.set("world", worldId);
    url.searchParams.delete("documentId");
    url.searchParams.delete("view");
    window.history.pushState({}, "", `${url.pathname}${url.search}`);
    setRouteCardsViewRequested(false);
    setSelectedCardViewIdentity(null);
    setDocumentId(null);
    setTitle("Plan");
    setMarkdown("");
    setEditorGeneration((value) => value + 1);
    persistWorldPlanLocalDraft(worldId, {
      document_id: null,
      local_draft_id: nextLocalDraftId,
      title: "Plan",
      markdown: "",
      revision: null,
      edit_generation: ++editGenerationRef.current,
      pending_write: null,
      create_uncertain: false,
    });
    setMessage(null);
    setError(null);
    setStatus("ready");
  };

  const save = async () => {
    if (statusRef.current !== "ready") return;
    const fidelityIssues = getLiveFidelityWarnings(editorRef.current?.getJSON());
    if (fidelityIssues.length) {
      if (!fidelityBlocked) setError(markdownFidelityWarningText(fidelityIssues));
      return;
    }
    if (savingRef.current || createUncertain || recoveryConflict
      || (uncertainCreateDraftRef.current && !documentIdRef.current)
      || !markdownRef.current.trim()) return;
    const epoch = selectionEpochRef.current;
    const initialId = documentIdRef.current;
    let uiDocumentId = initialId;
    const isCurrent = () => selectedViewIsCurrent(epoch, uiDocumentId);
    let exactId = initialId;
    let currentRevision = revisionRef.current;
    let submittedTitle = titleRef.current.trim() || "Plan";
    let submittedMarkdown = markdownRef.current;
    let submittedGeneration = editGenerationRef.current;
    savingRef.current = true;
    setSaving(true);
    if (isCurrent()) setSavedBasis({ status: "unavailable" });
    setError(null);
    setMessage(null);
    try {
      if (!exactId) {
        const blankDraft = readWorldPlanLocalDraft(worldId);
        submittedTitle = blankDraft?.title ?? submittedTitle;
        submittedMarkdown = blankDraft?.markdown ?? submittedMarkdown;
        submittedGeneration = blankDraft?.edit_generation ?? submittedGeneration;
        const quarantinedDraft = {
          title: submittedTitle,
          markdown: submittedMarkdown,
          edit_generation: submittedGeneration,
          bound_document_id: null,
        };
        uncertainCreateDraftRef.current = quarantinedDraft;
        if (isCurrent()) setUncertainCreateDraft(quarantinedDraft);
        persistWorldPlanLocalDraft(worldId, {
          document_id: null,
          title: submittedTitle,
          markdown: submittedMarkdown,
          revision: null,
          edit_generation: submittedGeneration,
          create_uncertain: true,
          uncertain_create_draft: quarantinedDraft,
          pending_write: null,
        });
        if (isCurrent()) setCreateUncertain(true);
        let created: WorldOwnedPlanRecordV2;
        try {
          created = await createWorldOwnedPlan({
            schema_version: "dmb_workspace_document_create_v2",
            scope_mode: "world",
            world_id: worldId,
            title: submittedTitle,
          });
        } catch (reason) {
          const latest = readWorldPlanLocalDraft(worldId);
          persistWorldPlanLocalDraft(worldId, {
            document_id: null,
            title: latest?.title ?? submittedTitle,
            markdown: latest?.markdown ?? submittedMarkdown,
            revision: null,
            edit_generation: latest?.edit_generation ?? submittedGeneration,
            create_uncertain: true,
            uncertain_create_draft: {
              title: latest?.title ?? submittedTitle,
              markdown: latest?.markdown ?? submittedMarkdown,
              edit_generation: latest?.edit_generation ?? submittedGeneration,
              bound_document_id: null,
            },
            pending_write: null,
          });
          if (isCurrent()) {
            setError(`World Plan creation response was uncertain. Refresh Saved Plans and select the Plan if it appears; automatic retry is disabled to prevent a duplicate. ${reason instanceof Error ? reason.message : ""}`.trim());
          }
          return;
        }
        if (created.world_id !== worldId || created.campaign_id !== null || created.kind !== "plan") {
          const latest = readWorldPlanLocalDraft(worldId);
          persistWorldPlanLocalDraft(worldId, {
            document_id: null,
            title: latest?.title ?? submittedTitle,
            markdown: latest?.markdown ?? submittedMarkdown,
            revision: null,
            edit_generation: latest?.edit_generation ?? submittedGeneration,
            create_uncertain: true,
            uncertain_create_draft: {
              title: latest?.title ?? submittedTitle,
              markdown: latest?.markdown ?? submittedMarkdown,
              edit_generation: latest?.edit_generation ?? submittedGeneration,
              bound_document_id: null,
            },
            pending_write: null,
          });
          throw new Error("Server returned a Plan outside the selected World; creation outcome is quarantined.");
        }
        exactId = created.document_id;
        currentRevision = created.revision;
        const latest = readWorldPlanLocalDraft(worldId);
        submittedTitle = latest?.document_id === null ? latest.title : submittedTitle;
        submittedMarkdown = latest?.document_id === null ? latest.markdown : submittedMarkdown;
        submittedGeneration = latest?.edit_generation ?? submittedGeneration;
        persistWorldPlanLocalDraft(worldId, {
          document_id: exactId,
          title: submittedTitle,
          markdown: submittedMarkdown,
          revision: currentRevision,
          edit_generation: submittedGeneration,
          create_uncertain: false,
          uncertain_create_draft: null,
          pending_write: null,
        });
        uncertainCreateDraftRef.current = null;
        if (isCurrent() && documentIdRef.current === null) {
          uiDocumentId = exactId;
          documentIdRef.current = exactId;
          revisionRef.current = currentRevision;
          titleRef.current = submittedTitle;
          markdownRef.current = submittedMarkdown;
          serverTitleRef.current = created.title;
          serverMarkdownRef.current = "";
          serverDigestRef.current = null;
          setSavedBasis({ status: "unavailable" });
          setCreateUncertain(false);
          setUncertainCreateDraft(null);
          setDocumentId(exactId);
          setRecords((current) => [created, ...current]);
          const url = new URL(window.location.href);
          url.searchParams.set("world", worldId);
          url.searchParams.set("documentId", exactId);
          window.history.replaceState({}, "", `${url.pathname}${url.search}`);
        }
      }

      if (!exactId || currentRevision == null) {
        throw new Error("The exact World Plan identity or revision is unavailable.");
      }

      let savedLocal = readWorldPlanLocalDraft(worldId);
      if (savedLocal?.document_id === exactId) {
        submittedTitle = isCurrent() ? titleRef.current.trim() || "Plan" : savedLocal.title;
        submittedMarkdown = isCurrent() ? markdownRef.current : savedLocal.markdown;
        submittedGeneration = isCurrent() ? editGenerationRef.current : (savedLocal.edit_generation ?? 0);
      }

      const previousPending = savedLocal?.document_id === exactId
        ? savedLocal.pending_write ?? null
        : pendingWriteRef.current;
      if (previousPending) {
        const snapshot = await getWorldOwnedPlanSnapshot(exactId);
        if (snapshot.record.world_id !== worldId || snapshot.record.campaign_id !== null) {
          throw new Error("Pending write recovery resolved outside the selected World.");
        }
        let committedMarkdown: string | null = null;
        try {
          const committedRevision = await getWorldOwnedPlanCommittedRevision(exactId);
          if (committedRevision.world_id !== worldId || committedRevision.campaign_id !== null) {
            throw new Error("Committed revision recovery resolved outside the selected World.");
          }
          committedMarkdown = committedRevision.markdown;
        } catch (reason) {
          if (!(reason instanceof LiveApiError && (reason.status === 404 || reason.status === 409))) {
            throw reason;
          }
        }

        const committed = committedMarkdown === previousPending.markdown;
        const preparedCopy = previousPending.prepared_revision !== null
          && snapshot.loaded_revision === previousPending.prepared_revision
          && snapshot.markdown === previousPending.markdown;
        const prepareApplied = previousPending.phase === "prepare"
          && snapshot.loaded_revision === previousPending.base_revision + 1
          && snapshot.markdown === previousPending.markdown;
        const prepareDidNotApply = previousPending.phase === "prepare"
          && snapshot.loaded_revision === previousPending.base_revision
          && snapshot.markdown === previousPending.base_markdown;
        if (!committed && !preparedCopy && !prepareApplied && !prepareDidNotApply) {
          if (isCurrent()) {
            setRecoveryConflict(true);
            setServerDraft({
              title: snapshot.record.title,
              markdown: snapshot.markdown,
              revision: snapshot.loaded_revision,
              contentSha256: snapshot.content_sha256,
              contentStatus: snapshot.record.content_status,
            });
            setError("The previous save outcome cannot be proven against the current World revision. Your local draft is preserved and saving is blocked until you choose a version.");
          }
          return;
        }
        currentRevision = snapshot.loaded_revision;
        revisionRef.current = currentRevision;
        serverTitleRef.current = snapshot.record.title;
        serverMarkdownRef.current = committed ? committedMarkdown ?? snapshot.markdown : snapshot.markdown;
        serverDigestRef.current = snapshot.content_sha256;
        if (isCurrent()) {
          setSavedBasis(committed && snapshot.record.content_status === "committed"
            ? worldPlanCardBasisFromSnapshot(snapshot)
            : { status: "unavailable" });
        }
        pendingWriteRef.current = null;
        const latest = readWorldPlanLocalDraft(worldId);
        const preserveLatest = latest?.document_id === exactId
          && (latest.edit_generation ?? 0) > previousPending.edit_generation;
        persistWorldPlanLocalDraft(worldId, {
          document_id: exactId,
          title: preserveLatest ? latest.title : submittedTitle,
          markdown: preserveLatest ? latest.markdown : submittedMarkdown,
          revision: currentRevision,
          edit_generation: preserveLatest ? latest.edit_generation ?? submittedGeneration : submittedGeneration,
          create_uncertain: false,
          pending_write: null,
        });
        if (committed && !preserveLatest) {
          const currentRecovery = readWorldPlanLocalDraft(worldId)?.uncertain_create_draft
            ?? uncertainCreateDraftRef.current;
          const recoveryWasSubmitted = currentRecovery?.bound_document_id === exactId
            && currentRecovery.edit_generation <= previousPending.edit_generation
            && currentRecovery.markdown === previousPending.markdown;
          const remainingRecovery = recoveryWasSubmitted ? null : currentRecovery;
          uncertainCreateDraftRef.current = remainingRecovery;
          if (isCurrent()) setUncertainCreateDraft(remainingRecovery);
          persistWorldPlanLocalDraft(worldId, {
            document_id: exactId,
            title: submittedTitle,
            markdown: submittedMarkdown,
            revision: currentRevision,
            edit_generation: submittedGeneration,
            create_uncertain: false,
            uncertain_create_draft: remainingRecovery,
            pending_write: null,
          });
          if (isCurrent()) {
            setMessage("Saved to this World.");
            setSaving(false);
          }
          return;
        }
        savedLocal = readWorldPlanLocalDraft(worldId);
        if (savedLocal?.document_id === exactId) {
          submittedTitle = isCurrent() ? titleRef.current.trim() || "Plan" : savedLocal.title;
          submittedMarkdown = isCurrent() ? markdownRef.current : savedLocal.markdown;
          submittedGeneration = isCurrent() ? editGenerationRef.current : (savedLocal.edit_generation ?? 0);
        }
      }

      const baseRevision = currentRevision;
      const baseMarkdown = serverMarkdownRef.current;
      const preparing = {
        phase: "prepare" as const,
        base_revision: baseRevision,
        prepared_revision: null,
        base_markdown: baseMarkdown,
        markdown: submittedMarkdown,
        edit_generation: submittedGeneration,
      };
      pendingWriteRef.current = preparing;
      const beforePrepare = readWorldPlanLocalDraft(worldId);
      persistWorldPlanLocalDraft(worldId, {
        document_id: exactId,
        title: beforePrepare?.title ?? submittedTitle,
        markdown: beforePrepare?.markdown ?? submittedMarkdown,
        revision: baseRevision,
        edit_generation: beforePrepare?.edit_generation ?? submittedGeneration,
        create_uncertain: false,
        pending_write: preparing,
      });
      const scope = {
        schema_version: "dmb_tiptap_markdown_write_prepare_v2" as const,
        scope_mode: "world" as const,
        world_id: worldId,
      };
      const prepared = await prepareTiptapMarkdownWrite({
        ...scope,
        document_id: exactId,
        markdown: submittedMarkdown,
        expected_revision: baseRevision,
      });
      if (!prepared.writer_ok || !prepared.writer_confirm_token || prepared.world_id !== worldId) {
        throw new Error(prepared.warnings.join(" ") || "Plan write could not be prepared.");
      }
      currentRevision = prepared.registry_revision;
      revisionRef.current = currentRevision;
      const preparedWrite = {
        ...preparing,
        phase: "commit" as const,
        prepared_revision: prepared.registry_revision,
      };
      pendingWriteRef.current = preparedWrite;
      const afterPrepare = readWorldPlanLocalDraft(worldId);
      persistWorldPlanLocalDraft(worldId, {
        document_id: exactId,
        title: afterPrepare?.title ?? submittedTitle,
        markdown: afterPrepare?.markdown ?? submittedMarkdown,
        revision: prepared.registry_revision,
        edit_generation: afterPrepare?.edit_generation ?? submittedGeneration,
        create_uncertain: false,
        pending_write: preparedWrite,
      });

      const committed = await commitWorldOwnedPlanMarkdownWrite({
        schema_version: "dmb_tiptap_markdown_write_commit_v2",
        scope_mode: "world",
        world_id: worldId,
        document_id: exactId,
        markdown: submittedMarkdown,
        expected_revision: prepared.registry_revision,
        writer_confirm_token: prepared.writer_confirm_token,
      });
      if (committed.world_id !== worldId || committed.committed_record.schema_version !== "dmb_world_owned_plan_record_v2") {
        throw new Error("Commit receipt did not preserve World-owned Plan scope.");
      }
      currentRevision = committed.registry_revision;
      revisionRef.current = currentRevision;
      serverTitleRef.current = committed.title;
      serverMarkdownRef.current = submittedMarkdown;
      serverDigestRef.current = committed.normalized_content_sha256;
      if (isCurrent()) {
        setSavedBasis({
          status: "verified",
          revision: committed.registry_revision,
          contentSha256: committed.normalized_content_sha256,
        });
      }
      pendingWriteRef.current = null;
      const latest = readWorldPlanLocalDraft(worldId);
      const preserveLatest = latest?.document_id === exactId
        && (latest.edit_generation ?? 0) > submittedGeneration;
      const finalTitle = preserveLatest ? latest.title : committed.title;
      const finalMarkdown = preserveLatest ? latest.markdown : submittedMarkdown;
      const finalGeneration = preserveLatest ? latest.edit_generation ?? submittedGeneration : submittedGeneration;
      const currentRecovery = readWorldPlanLocalDraft(worldId)?.uncertain_create_draft
        ?? uncertainCreateDraftRef.current;
      const recoveryWasSubmitted = currentRecovery?.bound_document_id === exactId
        && currentRecovery.edit_generation <= submittedGeneration
        && currentRecovery.markdown === submittedMarkdown;
      const remainingRecovery = recoveryWasSubmitted ? null : currentRecovery;
      persistWorldPlanLocalDraft(worldId, {
        document_id: exactId,
        title: finalTitle,
        markdown: finalMarkdown,
        revision: currentRevision,
        edit_generation: finalGeneration,
        create_uncertain: false,
        uncertain_create_draft: remainingRecovery,
        pending_write: null,
      });
      uncertainCreateDraftRef.current = remainingRecovery;
      if (isCurrent()) {
        setUncertainCreateDraft(remainingRecovery);
        if (!preserveLatest) {
          titleRef.current = committed.title;
          markdownRef.current = submittedMarkdown;
          setTitle(committed.title);
          setMarkdown(submittedMarkdown);
          setEditorGeneration((value) => value + 1);
        }
        setRecords((current) => current.map((record) => record.document_id === exactId ? committed.committed_record : record));
        setCreateUncertain(false);
        setRecoveryConflict(false);
        setServerDraft(null);
        setMessage("Saved to this World.");
      }
    } catch (reason) {
      if (isCurrent()) {
        setError(reason instanceof Error ? reason.message : "Plan could not be saved.");
      }
    } finally {
      savingRef.current = false;
      if (isCurrent()) setSaving(false);
    }
  };

  const refreshSavedPlans = async () => {
    const epoch = selectionEpochRef.current;
    const selectedId = documentIdRef.current;
    try {
      const inventory = await listWorldOwnedPlans(worldId);
      if (!selectedViewIsCurrent(epoch, selectedId) || inventory.world_id !== worldId) return;
      setRecords(inventory.records);
      setMessage("Saved Plans refreshed. Opening a candidate will not bind the recovered draft; you can choose that explicitly afterward.");
      setError(null);
    } catch (reason) {
      if (selectedViewIsCurrent(epoch, selectedId)) {
        setError(reason instanceof Error ? reason.message : "Saved Plans could not be refreshed.");
      }
    }
  };

  const useServerVersion = () => {
    if (statusRef.current !== "ready" || !serverDraft) return;
    titleRef.current = serverDraft.title;
    markdownRef.current = serverDraft.markdown;
    serverTitleRef.current = serverDraft.title;
    serverMarkdownRef.current = serverDraft.markdown;
    serverDigestRef.current = serverDraft.contentSha256;
    revisionRef.current = serverDraft.revision;
    setSavedBasis(serverDraft.contentStatus === "committed"
      ? { status: "verified", revision: serverDraft.revision, contentSha256: serverDraft.contentSha256 }
      : serverDraft.contentStatus === "draft"
        ? { status: "server-draft" }
        : { status: "unavailable" });
    pendingWriteRef.current = null;
    const generation = ++editGenerationRef.current;
    setTitle(serverDraft.title);
    setMarkdown(serverDraft.markdown);
    setEditorGeneration((value) => value + 1);
    setRecoveryConflict(false);
    setServerDraft(null);
    setError(null);
    persistWorldPlanLocalDraft(worldId, {
      document_id: documentIdRef.current,
      title: serverDraft.title,
      markdown: serverDraft.markdown,
      revision: serverDraft.revision,
      edit_generation: generation,
      create_uncertain: false,
      pending_write: null,
    });
  };

  const restoreUncertainDraftIntoSelectedPlan = () => {
    const recovery = uncertainCreateDraftRef.current;
    const selectedId = documentIdRef.current;
    if (statusRef.current !== "ready" || !recovery || !selectedId || savingRef.current) return;
    const generation = Math.max(editGenerationRef.current, recovery.edit_generation) + 1;
    const boundRecovery = { ...recovery, edit_generation: generation, bound_document_id: selectedId };
    uncertainCreateDraftRef.current = boundRecovery;
    editGenerationRef.current = generation;
    titleRef.current = recovery.title;
    markdownRef.current = recovery.markdown;
    setUncertainCreateDraft(boundRecovery);
    setTitle(recovery.title);
    setMarkdown(recovery.markdown);
    setEditorGeneration((value) => value + 1);
    persistWorldPlanLocalDraft(worldId, {
      document_id: selectedId,
      title: recovery.title,
      markdown: recovery.markdown,
      revision: revisionRef.current,
      edit_generation: generation,
      create_uncertain: false,
      uncertain_create_draft: boundRecovery,
      pending_write: null,
    });
    setMessage("Recovered draft is now explicitly associated with this Plan. Save to write it to the World.");
    setError(null);
  };

  const discardUncertainDraft = () => {
    if (statusRef.current !== "ready" || !uncertainCreateDraftRef.current || savingRef.current) return;
    uncertainCreateDraftRef.current = null;
    setUncertainCreateDraft(null);
    setCreateUncertain(false);
    const current = readWorldPlanLocalDraft(worldId);
    const discardActiveDraft = documentIdRef.current === null;
    const nextTitle = discardActiveDraft ? "Plan" : titleRef.current;
    const nextMarkdown = discardActiveDraft ? "" : markdownRef.current;
    const nextGeneration = discardActiveDraft ? ++editGenerationRef.current : editGenerationRef.current;
    if (discardActiveDraft) {
      titleRef.current = nextTitle;
      markdownRef.current = nextMarkdown;
      setTitle(nextTitle);
      setMarkdown(nextMarkdown);
      setEditorGeneration((value) => value + 1);
    }
    persistWorldPlanLocalDraft(worldId, {
      document_id: documentIdRef.current,
      title: nextTitle,
      markdown: nextMarkdown,
      revision: discardActiveDraft ? null : revisionRef.current,
      edit_generation: nextGeneration,
      create_uncertain: false,
      uncertain_create_draft: null,
      pending_write: current?.pending_write ?? pendingWriteRef.current,
    });
    setMessage("Recovered draft discarded.");
    setError(null);
  };

  const persistEditorDraft = (nextTitle: string, nextMarkdown: string, generation: number) => {
    if (statusRef.current !== "ready") return;
    const saved = readWorldPlanLocalDraft(worldId);
    const existingRecovery = saved?.uncertain_create_draft ?? uncertainCreateDraftRef.current;
    const isPendingCreate = createUncertain || saved?.create_uncertain === true;
    const recoveryIsBoundHere = Boolean(documentIdRef.current)
      && existingRecovery?.bound_document_id === documentIdRef.current;
    const nextRecovery = isPendingCreate || recoveryIsBoundHere
      ? {
        title: nextTitle,
        markdown: nextMarkdown,
        edit_generation: generation,
        bound_document_id: existingRecovery?.bound_document_id ?? null,
      }
      : existingRecovery;
    uncertainCreateDraftRef.current = nextRecovery ?? null;
    setUncertainCreateDraft(nextRecovery ?? null);
    persistWorldPlanLocalDraft(worldId, {
      document_id: documentIdRef.current,
      title: nextTitle,
      markdown: nextMarkdown,
      revision: revisionRef.current,
      edit_generation: generation,
      create_uncertain: isPendingCreate,
      uncertain_create_draft: nextRecovery ?? null,
      pending_write: saved?.pending_write ?? pendingWriteRef.current,
    });
  };

  const saveRef = useRef(save);
  saveRef.current = save;
  const persistEditorDraftRef = useRef(persistEditorDraft);
  persistEditorDraftRef.current = persistEditorDraft;
  const documentActions = useMemo(() => ({
    onTitleChange: (next: string) => {
      if (!isCurrentEditTarget(true) || getLiveFidelityWarnings(editorRef.current?.getJSON()).length > 0) return;
      titleRef.current = next;
      const generation = ++editGenerationRef.current;
      setTitle(next);
      persistEditorDraftRef.current(next, markdownRef.current, generation);
    },
    onSave: () => {
      if (isCurrentEditTarget()) void saveRef.current();
    },
  }), [getLiveFidelityWarnings, isCurrentEditTarget]);
  const editorToolsGeneration = useMemo(() => status === "ready" ? toAppChromeToolsGeneration({
    sections: [
      {
        id: "world-plan-document",
        title: "Document",
        defaultOpen: true,
        actions: [{
          id: "world-plan-save",
          label: saving ? "Saving…" : "Save Plan",
          onClick: documentActions.onSave,
          disabled: saving || fidelityBlocked || createUncertain || recoveryConflict
            || Boolean(uncertainCreateDraft && !documentId) || !markdown.trim(),
        }],
        panel: <label className="world-plan-edit-panel">Plan title
          <input value={title} disabled={fidelityBlocked} onChange={(event) => documentActions.onTitleChange(event.target.value)} />
        </label>,
      },
      ...(toolbarModel.sections ?? []),
    ],
  }, workObject) : null, [status, saving, fidelityBlocked, createUncertain, recoveryConflict, uncertainCreateDraft,
    documentId, markdown, title, documentActions, toolbarModel, workObject]);
  const cardsViewActive = Boolean(documentId) && status === "ready"
    && (selectedCardViewIdentity === editorIdentity
      || (routeCardsViewRequested && documentId === initialDocumentId));
  const selectPlanView = (view: "cards" | "document") => {
    const url = new URL(window.location.href);
    if (view === "cards") url.searchParams.set("view", "cards");
    else url.searchParams.delete("view");
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
    setRouteCardsViewRequested(false);
    setSelectedCardViewIdentity(view === "cards" ? editorIdentity : null);
  };
  const cardProjectionDocument = editor?.getJSON() ?? editorContent;
  const cardProjectionDirty = documentId !== null
    && (markdown !== serverMarkdownRef.current || title !== serverTitleRef.current);
  const canStartPlayFromSavedPlan = Boolean(
    documentId
    && documentIdRef.current === documentId
    && status === "ready"
    && savedBasis.status === "verified"
    && !cardProjectionDirty
    && !saving
    && !savingRef.current
    && pendingWriteRef.current === null
    && !createUncertain
    && !recoveryConflict
    && !fidelityBlocked
    && !startingPlay
  );
  const startPlayFromSavedPlan = async () => {
    if (!canStartPlayFromSavedPlan || !documentId || savedBasis.status !== "verified") return;
    const selectedDocumentId = documentId;
    const selectedBasis = savedBasis;
    const selectionEpoch = selectionEpochRef.current;
    const editGeneration = editGenerationRef.current;
    const request = startPlayRequestRef.current + 1;
    startPlayRequestRef.current = request;
    setStartingPlay(true);
    setStartPlayError(null);
    try {
      const committed = await getWorldOwnedPlanCommittedRevision(selectedDocumentId);
      if (
        startPlayRequestRef.current !== request
        || !selectedViewIsCurrent(selectionEpoch, selectedDocumentId)
      ) return;
      if (
        committed.schema_version !== "dmb_workspace_committed_revision_v2"
        || committed.scope_mode !== "world"
        || committed.world_id !== worldId
        || committed.document_id !== selectedDocumentId
        || committed.kind !== "plan"
        || committed.campaign_id !== null
        || committed.status !== "active"
        || committed.has_divergent_working_copy
        || committed.object_revision !== selectedBasis.revision
        || committed.content_sha256 !== selectedBasis.contentSha256
        || committed.markdown !== serverMarkdownRef.current
        || revisionRef.current !== selectedBasis.revision
        || serverDigestRef.current !== selectedBasis.contentSha256
        || !isCanonicalUuid(committed.work_revision_id)
        || !CANONICAL_SHA256_RE.test(committed.content_sha256)
        || editGenerationRef.current !== editGeneration
        || markdownRef.current !== serverMarkdownRef.current
        || titleRef.current !== serverTitleRef.current
        || pendingWriteRef.current !== null
        || savingRef.current
      ) {
        throw new Error("The selected Plan no longer matches its verified saved revision. Save and reopen the Plan before starting Play.");
      }
      const location = new URLSearchParams(window.location.search);
      if (
        location.get("world") !== worldId
        || location.get("documentId") !== selectedDocumentId
        || documentIdRef.current !== selectedDocumentId
      ) {
        throw new Error("The selected Plan or World changed before Play could start. Reopen the Plan and try again.");
      }
      const params = new URLSearchParams({
        world: worldId,
        plan: selectedDocumentId,
        plan_revision: String(committed.revision_n),
        plan_work_revision_id: committed.work_revision_id,
        plan_sha256: committed.content_sha256,
      });
      window.history.pushState({}, "", `/play?${params.toString()}`);
      window.dispatchEvent(new PopStateEvent("popstate"));
    } catch (reason) {
      if (
        startPlayRequestRef.current === request
        && selectedViewIsCurrent(selectionEpoch, selectedDocumentId)
      ) {
        setStartPlayError(reason instanceof Error ? reason.message : "The saved Plan could not be verified for Play.");
      }
    } finally {
      if (
        startPlayRequestRef.current === request
        && selectedViewIsCurrent(selectionEpoch, selectedDocumentId)
      ) setStartingPlay(false);
    }
  };
  const currentCardProjection = useMemo(
    () => buildWorldPlanCardProjectionModel({
      document: cardProjectionDocument,
      markdown,
      sourceWarnings: fidelityWarnings,
    }),
    [cardProjectionDocument, markdown, fidelityWarnings],
  );
  const savedCardProjection = useMemo(() => {
    if (savedBasis.status !== "verified" || !documentId) return null;
    const imported = markdownToTiptapDoc(serverMarkdownRef.current);
    return buildWorldPlanCardProjectionModel({
      document: imported.doc,
      markdown: serverMarkdownRef.current,
      sourceWarnings: markdownFidelityWarnings(imported.diagnostics, imported.doc),
    });
  }, [documentId, savedBasis]);
  function cardTargetLabel(target: WorldPlanCardTarget | null): string | undefined {
    if (!target || currentCardProjection.status !== "ready") return undefined;
    const pending = [...currentCardProjection.roots];
    while (pending.length) {
      const node = pending.pop()!;
      if (node.kind === target.kind && node.id === target.id) return node.title;
      pending.push(...node.children);
    }
    return undefined;
  }
  const selectableTargetKeys = useMemo(() => {
    if (savedBasis.status !== "verified" || !savedCardProjection) return new Set<string>();
    const currentKeys = worldPlanCardTargetKeys(currentCardProjection);
    const savedKeys = worldPlanCardTargetKeys(savedCardProjection);
    return new Set([...currentKeys].filter((key) => savedKeys.has(key)));
  }, [currentCardProjection, savedBasis, savedCardProjection]);
  const editableTargetKeys = useMemo(() => {
    if (savedBasis.status !== "verified") return new Set<string>();
    return worldPlanCardTargetKeys(currentCardProjection);
  }, [currentCardProjection, savedBasis]);
  const selectedTargetBasisMatches = Boolean(selectedPlayableTarget
    && selectedPlayableTarget.worldId === worldId
    && selectedPlayableTarget.documentId === documentId
    && savedBasis.status === "verified"
    && selectedPlayableTarget.revision === savedBasis.revision
    && selectedPlayableTarget.contentSha256 === savedBasis.contentSha256);
  const selectedPlayableTargetStale = Boolean(selectedPlayableTarget
    && (!selectedTargetBasisMatches
      || selectedPlayableTarget.stale
      || !selectableTargetKeys.has(worldPlanCardTargetKey(selectedPlayableTarget.target))));
  const selectedEditTargetBasisMatches = Boolean(selectedPlayableEditTarget
    && selectedPlayableEditTarget.worldId === worldId
    && selectedPlayableEditTarget.documentId === documentId
    && savedBasis.status === "verified"
    && selectedPlayableEditTarget.revision === savedBasis.revision
    && selectedPlayableEditTarget.contentSha256 === savedBasis.contentSha256);
  const selectedPlayableEditTargetStale = Boolean(selectedPlayableEditTarget
    && (!selectedEditTargetBasisMatches
      || selectedPlayableEditTarget.stale
      || !editableTargetKeys.has(worldPlanCardTargetKey(selectedPlayableEditTarget.target))));
  playableEditTargetStaleRef.current = selectedPlayableEditTargetStale;

  useEffect(() => {
    if (!selectedPlayableTarget) return;
    if (selectedPlayableTarget.worldId !== worldId || selectedPlayableTarget.documentId !== documentId) {
      setSelectedPlayableTarget(null);
      return;
    }
    if (savedBasis.status === "verified"
      && (selectedPlayableTarget.revision !== savedBasis.revision
        || selectedPlayableTarget.contentSha256 !== savedBasis.contentSha256)) {
      if (!selectedPlayableTarget.stale) setSelectedPlayableTarget({ ...selectedPlayableTarget, stale: true });
      return;
    }
    if ((!selectedTargetBasisMatches || !selectableTargetKeys.has(worldPlanCardTargetKey(selectedPlayableTarget.target)))
      && !selectedPlayableTarget.stale) {
      setSelectedPlayableTarget({ ...selectedPlayableTarget, stale: true });
    }
  }, [documentId, savedBasis, selectableTargetKeys, selectedPlayableTarget, selectedTargetBasisMatches, worldId]);

  useEffect(() => {
    if (!selectedPlayableEditTarget) return;
    if (selectedPlayableEditTarget.worldId !== worldId || selectedPlayableEditTarget.documentId !== documentId) {
      setSelectedPlayableEditTarget(null);
      selectedPlayableEditTargetRef.current = null;
      playableEditTargetGenerationRef.current += 1;
      setPlayableEditTargetGeneration(playableEditTargetGenerationRef.current);
      return;
    }
    if (savedBasis.status === "verified"
      && (selectedPlayableEditTarget.revision !== savedBasis.revision
        || selectedPlayableEditTarget.contentSha256 !== savedBasis.contentSha256)) {
      setSelectedPlayableEditTarget(null);
      selectedPlayableEditTargetRef.current = null;
      playableEditTargetGenerationRef.current += 1;
      setPlayableEditTargetGeneration(playableEditTargetGenerationRef.current);
      return;
    }
    if ((!selectedEditTargetBasisMatches
      || !editableTargetKeys.has(worldPlanCardTargetKey(selectedPlayableEditTarget.target)))
      && !selectedPlayableEditTarget.stale) {
      setSelectedPlayableEditTarget({ ...selectedPlayableEditTarget, stale: true });
    }
  }, [documentId, editableTargetKeys, savedBasis, selectedEditTargetBasisMatches, selectedPlayableEditTarget, worldId]);

  const selectPlayableTarget = useCallback((target: WorldPlanCardTarget | null) => {
    if (target === null) {
      setSelectedPlayableTarget(null);
      return;
    }
    if (savedBasis.status !== "verified" || !documentId
      || !selectableTargetKeys.has(worldPlanCardTargetKey(target))) return;
    setSelectedPlayableTarget({
      target,
      worldId,
      documentId,
      revision: savedBasis.revision,
      contentSha256: savedBasis.contentSha256,
      stale: false,
    });
  }, [documentId, savedBasis, selectableTargetKeys, worldId]);

  const selectPlayableEditTarget = useCallback((target: WorldPlanCardTarget) => {
    if (savedBasis.status !== "verified" || !documentId
      || !editableTargetKeys.has(worldPlanCardTargetKey(target))) return;
    const generation = playableEditTargetGenerationRef.current + 1;
    playableEditTargetGenerationRef.current = generation;
    setPlayableEditTargetGeneration(generation);
    const selected = {
      target,
      worldId,
      documentId,
      revision: savedBasis.revision,
      contentSha256: savedBasis.contentSha256,
      generation,
      stale: false,
    };
    selectedPlayableEditTargetRef.current = selected;
    playableEditTargetStaleRef.current = false;
    setSelectedPlayableEditTarget(selected);
  }, [documentId, editableTargetKeys, savedBasis, worldId]);

  const clearPlayableEditTarget = useCallback(() => {
    playableEditTargetGenerationRef.current += 1;
    setPlayableEditTargetGeneration(playableEditTargetGenerationRef.current);
    selectedPlayableEditTargetRef.current = null;
    playableEditTargetStaleRef.current = false;
    setSelectedPlayableEditTarget(null);
  }, []);

  const focusTitle = (() => {
    if (!selectedPlayableTarget || savedCardProjection?.status !== "ready") return null;
    const find = (nodes: WorldPlanCardNode[]): string | null => {
      for (const node of nodes) {
        if (node.id === selectedPlayableTarget.target.id && node.kind === selectedPlayableTarget.target.kind) return node.title;
        const child = find(node.children); if (child) return child;
      }
      return null;
    };
    return find(savedCardProjection.roots);
  })();
  return (
    <AppChrome activeRoute="plan" editorTools={editorToolsGeneration} editToolboxLayout="dock" workspaceLayout="bounded">
      <WorldPlanSurfaceContext
        worldId={worldId}
        worldName={worldName}
        documentId={documentId}
        localDraftId={localDraftId}
        records={records}
        disabled={saving || status !== "ready"}
        onSelect={(nextId) => { void openPlan(nextId); }}
        onNewPlan={resetBlankPlan}
      />
      <PlanConversationDockAdapter contextLabel={focusTitle ? `${focusTitle} · Full saved Plan` : `${worldName} · Full saved Plan`} reader={(
      <main
        className="app-status world-owned-plan"
        data-testid="world-owned-plan"
        data-plan-surface-identity={editorIdentity}
        aria-labelledby="world-owned-plan-title"
      >
        <h1 id="world-owned-plan-title" className="sr-only">
          {documentId ? title || "Untitled Plan" : "New Plan"}
        </h1>
        <p className="world-owned-plan__intro">
          Plan changes stay local until you choose Save Plan.
        </p>
        <div className="world-plan-start-play">
          <button
            type="button"
            data-testid="world-plan-start-play"
            disabled={!canStartPlayFromSavedPlan}
            onClick={() => { void startPlayFromSavedPlan(); }}
          >
            {startingPlay ? "Verifying saved Plan…" : "Start Play from this Plan"}
          </button>
          {startPlayError ? <p role="alert" data-testid="world-plan-start-play-error">{startPlayError}</p> : null}
          {status === "ready" && documentId && !canStartPlayFromSavedPlan && !startingPlay ? (
            <p role="status" data-testid="world-plan-start-play-disabled">
              Save and reopen a clean, committed Plan before starting Play.
            </p>
          ) : null}
        </div>
        {createUncertain ? (
          <section role="alert">
            <p>Plan creation may have succeeded, but its response was lost. Refresh Saved Plans and open a candidate if one appears. Its identity is not assumed; the recovered text stays separate until you explicitly restore it into a Plan or discard it. Automatic creation retry is blocked to avoid duplicates.</p>
            <button type="button" onClick={() => void refreshSavedPlans()} disabled={saving || status !== "ready"}>Refresh Saved Plans</button>
            <button type="button" onClick={discardUncertainDraft} disabled={saving || status !== "ready"}>Discard recovered draft</button>
          </section>
        ) : null}
        {uncertainCreateDraft && !createUncertain ? (
          <section role="status" aria-label="Recovered Plan draft">
            <p>An unsaved draft from an uncertain Plan creation is preserved separately. It has not been assumed to belong to the selected Plan.</p>
            {documentId ? <button type="button" onClick={restoreUncertainDraftIntoSelectedPlan} disabled={saving || status !== "ready"}>Restore recovered draft into this Plan</button> : null}
            <button type="button" onClick={discardUncertainDraft} disabled={saving || status !== "ready"}>Discard recovered draft</button>
          </section>
        ) : null}
        {recoveryConflict && serverDraft ? (
          <section role="alert">
            <p>The server Plan changed while a local draft was pending. Your local text is preserved, but cannot overwrite the newer server version silently.</p>
            <button type="button" onClick={useServerVersion}>Use saved Plan version</button>
          </section>
        ) : null}
        {fidelityWarnings.length ? (
          <section role="alert" aria-label="Markdown preservation warning">
            <p>This Plan contains Markdown the editor cannot safely preserve. Editing and Save are disabled to protect the saved text; the original and local recovery copy remain unchanged. Resolve these constructs in the source and reopen the Plan.</p>
            <ul>{fidelityWarnings.map((warning, index) => <li key={`${index}:${warning}`}>{warning}</li>)}</ul>
          </section>
        ) : null}
        <nav className="world-plan-view-switch" role="group" aria-label="Plan view" data-testid="world-plan-view-switch">
          <button
            type="button"
            aria-pressed={!cardsViewActive}
            onClick={() => selectPlanView("document")}
          >Document</button>
          <button
            type="button"
            aria-pressed={cardsViewActive}
            disabled={!documentId || status !== "ready" || !editor}
            onClick={() => selectPlanView("cards")}
          >Cards</button>
        </nav>
        <div
          className="world-plan-document-view"
          data-testid="world-plan-document-view"
          hidden={cardsViewActive}
          aria-hidden={cardsViewActive}
        >
          <PlanSurfaceCanvasFrame
            className="world-owned-plan__canvas"
            testId="world-owned-plan-editor"
            identityLabel={documentId ? "Plan editor" : "Unsaved Plan draft"}
            themeId="mireward-runbook"
          >
            <MarkdownEditorCore
              content={editorContent}
              documentKey={editorIdentity}
              editable={status === "ready" && !fidelityBlocked}
              extensions={[SemanticMarkdownPaste]}
              onEditorChange={setCurrentEditor}
              dataTestId="world-owned-plan-markdown-editor"
              onUpdate={(json: JSONContent, updatedEditor: Editor, meta) => {
                if (!meta.programmatic && !switchingDocumentRef.current && status === "ready" && updatedEditor === editorRef.current) {
                  const currentFidelityIssues = getLiveFidelityWarnings(json);
                  if (currentFidelityIssues.length) {
                    if (!fidelityBlocked) {
                      setError(markdownFidelityRejectionText(currentFidelityIssues));
                    }
                    setEditorGeneration((value) => value + 1);
                    return;
                  }
                  const next = defaultMarkdownDocumentAdapter.exportMarkdown(json);
                  const nextImport = markdownToTiptapDoc(next);
                  const nextFidelityIssues = markdownFidelityWarnings(nextImport.diagnostics, json);
                  if (nextFidelityIssues.length) {
                    setError(markdownFidelityRejectionText(nextFidelityIssues));
                    setEditorGeneration((value) => value + 1);
                    return;
                  }
                  if (next === markdownRef.current) return;
                  markdownRef.current = next;
                  const generation = ++editGenerationRef.current;
                  setMarkdown(next);
                  persistEditorDraft(titleRef.current, next, generation);
                  setError(null);
                }
              }}
            >
              {(editor) => <EditorContent editor={editor} aria-label="Markdown plan" />}
            </MarkdownEditorCore>
          </PlanSurfaceCanvasFrame>
        </div>
        {cardsViewActive && documentId ? (
          <WorldPlanCardProjection
            key={editorIdentity}
            worldId={worldId}
            documentId={documentId}
            document={cardProjectionDocument}
            markdown={markdown}
            sourceWarnings={fidelityWarnings}
            basis={savedBasis}
            isDirty={cardProjectionDirty}
            onReturnToDocument={() => selectPlanView("document")}
            selectableTargetKeys={selectableTargetKeys}
            editableTargetKeys={editableTargetKeys}
            selectedTarget={selectedPlayableTarget?.target ?? null}
            selectedEditTarget={selectedPlayableEditTarget?.target ?? null}
            onSelectTarget={selectPlayableTarget}
            onSelectEditTarget={selectPlayableEditTarget}
            selectionStale={selectedPlayableTargetStale}
            onActivateGraphNode={activateNode}
          />
        ) : null}
        {status === "loading" ? <p role="status">Loading World Plan…</p> : null}
        {message ? <p role="status">{message}</p> : null}
        {error ? <p role="alert">{error}</p> : null}
        {status === "error" ? <button type="button" onClick={retryPlanLoad}>Retry Plan load</button> : null}
      </main>
      )}>
      {(presentationHosts) => <WorldPlanAgentConversation
        presentationHosts={presentationHosts}
        worldId={worldId}
        worldName={worldName}
        documentId={documentId}
        surfaceInstanceId={surfaceIdentity.instanceKey}
        revision={revisionRef.current}
        editBridge={documentId ? worldPlanEditBridge : null}
        draftGeneration={editGenerationRef.current}
        selectionGeneration={selectionGeneration}
        savedDirty={Boolean(documentId && (title !== serverTitleRef.current || markdown !== serverMarkdownRef.current))}
        pageReady={status === "ready"}
        saveInFlight={saving || pendingWriteRef.current !== null}
        playableTarget={selectedPlayableTarget?.target ?? null}
        playableTargetBasis={selectedPlayableTarget ? {
          revision: selectedPlayableTarget.revision,
          contentSha256: selectedPlayableTarget.contentSha256,
        } : null}
        playableTargetStale={selectedPlayableTargetStale}
        onClearPlayableTarget={() => setSelectedPlayableTarget(null)}
        playableEditTarget={selectedPlayableEditTarget ? {
          ...selectedPlayableEditTarget.target,
          generation: selectedPlayableEditTarget.generation,
        } : null}
        playableEditTargetGeneration={playableEditTargetGeneration}
        playableEditTargetStale={selectedPlayableEditTargetStale}
        playableEditTargetDirty={cardProjectionDirty}
        editorSelectionActive={Boolean(editor && !editor.state.selection.empty)}
        playableTargetLabel={cardTargetLabel(selectedPlayableTarget?.target ?? null)}
        playableEditTargetLabel={cardTargetLabel(selectedPlayableEditTarget?.target ?? null)}
        onClearPlayableEditTarget={clearPlayableEditTarget}
      />}
      </PlanConversationDockAdapter>
    </AppChrome>
  );
}
