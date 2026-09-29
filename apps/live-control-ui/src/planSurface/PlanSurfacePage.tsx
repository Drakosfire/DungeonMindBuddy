import { useEffect, useMemo, useRef, useState } from "react";
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
import type { PlanViewProjection, WorldOwnedPlanRecordV2 } from "../api/types";
import { MarkdownEditorCore } from "../tiptap/MarkdownEditorCore";
import { defaultMarkdownDocumentAdapter } from "../tiptap/MarkdownDocumentAdapter";
import { AppChrome, type AppChromeToolsGeneration } from "../chrome/AppChrome";
import { usePublishSurfaceInteraction } from "../agentInteraction/usePublishSurfaceInteraction";
import { buildSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import type { SurfaceInteractionPublication, SurfaceInteractionWorkObjectIdentity } from "../surfaceInteraction/types";
import { PlanSurfaceShell } from "./PlanSurfaceShell";
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { WorldPlanSurfaceContext } from "./components/PlanSurfaceContext";
import { PlanSurfaceCanvasFrame } from "./components/PlanSurfaceCanvas";
import { toAppChromeToolsGeneration, type MarkdownEditorToolbarModel } from "../tiptap/MarkdownEditorToolbar";
import { CALLOUT_KINDS, defaultCalloutLabel } from "../tiptap/markdown/calloutMarkdown";
import { SemanticMarkdownPaste } from "../tiptap/extensions/SemanticMarkdownPaste";
import "../tiptap/prepMarkdownThemes.css";
import "../tiptap/tiptapSpike.css";

type LoadStatus = "loading" | "ready" | "error";

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
  if (managedWorldId) return <WorldOwnedPlanPage key={managedWorldId} worldId={managedWorldId} worldName={selectedWorld.kind === "managed" ? selectedWorld.name : managedWorldId} />;

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
  title: string;
  markdown: string;
  revision: number | null;
  /** Browser-local identity only; never persisted to the server Plan record. */
  local_draft_id?: string | null;
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

function createWorldPlanLocalDraftId(): string {
  return globalThis.crypto.randomUUID();
}

function readWorldPlanLocalDraft(worldId: string): WorldPlanLocalDraftV2 | null {
  try {
    const raw = localStorage.getItem(worldPlanLocalDraftKey(worldId));
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<WorldPlanLocalDraftV2>;
    if (value.schema_version !== "dmb_plan_promotion_recovery_v2" || value.scope_mode !== "world"
      || value.world_id !== worldId || typeof value.title !== "string" || typeof value.markdown !== "string") return null;
    const localDraftId = typeof value.local_draft_id === "string" && value.local_draft_id.trim() !== ""
      ? value.local_draft_id
      : value.document_id == null
        ? createWorldPlanLocalDraftId()
        : null;
    const normalized: WorldPlanLocalDraftV2 = {
      schema_version: "dmb_plan_promotion_recovery_v2",
      scope_mode: "world",
      world_id: worldId,
      document_id: typeof value.document_id === "string" ? value.document_id : null,
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
    if (value.local_draft_id !== localDraftId && normalized.document_id === null) {
      // Additive in-place migration: retain every v2 content and recovery field.
      try {
        localStorage.setItem(worldPlanLocalDraftKey(worldId), JSON.stringify({ ...value, local_draft_id: localDraftId }));
      } catch {
        // Keep the readable legacy draft in memory if local storage is unavailable.
      }
    }
    return normalized;
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
      local_draft_id: Object.hasOwn(draft, "local_draft_id")
        ? draft.local_draft_id
        : draft.document_id === null
          ? previous?.local_draft_id ?? createWorldPlanLocalDraftId()
          : null,
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

function WorldOwnedPlanPage({ worldId, worldName }: { worldId: string; worldName: string }) {
  const [localDraft] = useState(() => readWorldPlanLocalDraft(worldId));
  const [initialDocumentId] = useState(() =>
    new URLSearchParams(window.location.search).get("documentId")?.trim() || localDraft?.document_id || null,
  );
  const [localDraftId, setLocalDraftId] = useState<string | null>(() =>
    initialDocumentId === null ? localDraft?.local_draft_id ?? createWorldPlanLocalDraftId() : null,
  );
  const [records, setRecords] = useState<WorldOwnedPlanRecordV2[]>([]);
  const [documentId, setDocumentId] = useState<string | null>(initialDocumentId);
  const [title, setTitle] = useState(localDraft?.title ?? "Plan");
  const [markdown, setMarkdown] = useState(localDraft?.markdown ?? "");
  const [createUncertain, setCreateUncertain] = useState(localDraft?.create_uncertain ?? false);
  const [uncertainCreateDraft, setUncertainCreateDraft] = useState(localDraft?.uncertain_create_draft ?? null);
  const [recoveryConflict, setRecoveryConflict] = useState(false);
  const [serverDraft, setServerDraft] = useState<{ title: string; markdown: string; revision: number } | null>(null);
  const [editorGeneration, setEditorGeneration] = useState(0);
  const [editor, setEditor] = useState<Editor | null>(null);
  const editorContent = useMemo(() => markdownToTiptapDoc(markdown).doc, [markdown]);
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(false);
  const statusRef = useRef(status);
  statusRef.current = status;
  const selectionEpochRef = useRef(0);
  const documentIdRef = useRef(initialDocumentId);
  const revisionRef = useRef<number | null>(localDraft?.revision ?? null);
  const titleRef = useRef(localDraft?.title ?? "Plan");
  const markdownRef = useRef(localDraft?.markdown ?? "");
  const editGenerationRef = useRef(localDraft?.edit_generation ?? 0);
  const pendingWriteRef = useRef(localDraft?.pending_write ?? null);
  const uncertainCreateDraftRef = useRef(localDraft?.uncertain_create_draft ?? null);
  const savingRef = useRef(false);
  const serverMarkdownRef = useRef("");
  const editorRef = useRef<Editor | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const selectedViewIsCurrent = (epoch: number, expectedDocumentId: string | null) =>
    mountedRef.current
    && selectionEpochRef.current === epoch
    && documentIdRef.current === expectedDocumentId;

  const workObject = useMemo<SurfaceInteractionWorkObjectIdentity>(() => documentId
    ? {
      kind: "world-plan-document",
      id: JSON.stringify(["world-plan-document", worldId, documentId]),
    }
    : {
      kind: "world-plan-local-draft",
      id: JSON.stringify(["world-plan-local-draft", worldId, localDraftId ?? "pending-local-draft"]),
    }, [documentId, localDraftId, worldId]);
  const workObjectKey = JSON.stringify([workObject.kind, workObject.id]);
  const workObjectRef = useRef(workObjectKey);
  workObjectRef.current = workObjectKey;
  const editorIdentity = `${workObjectKey}:${editorGeneration}`;
  const selectionEpoch = selectionEpochRef.current;
  const editorIdentityRef = useRef(editorIdentity);
  editorIdentityRef.current = editorIdentity;
  const surfaceIdentity = useMemo(() => buildSurfaceInteractionIdentity({
    surfaceId: "plan",
    instanceParts: ["world-plan", workObject.kind, workObject.id],
  }), [workObject.id, workObject.kind]);
  const surfacePublication = useMemo<SurfaceInteractionPublication>(() => ({
    surfaceId: "plan",
    label: "Plan",
    identity: surfaceIdentity,
    canvas: { canvasId: "world-plan-document", workObject },
    agentContext: {
      label: `${worldName} · ${documentId ? title || "Untitled Plan" : "Unsaved Plan draft"}`,
      campaignId: null,
      documentId,
      sessionNumber: null,
      ambientSummary: `World Plan · ${worldName}`,
      pointers: [{ kind: "world", value: worldId }],
    },
    tools: [],
    editCommands: [],
    projections: [],
    projectionBindings: [],
  }), [documentId, surfaceIdentity, title, workObject, worldId, worldName]);
  usePublishSurfaceInteraction(surfacePublication);
  const saveDisabledReason = status !== "ready"
    ? status === "loading" ? "Plan is still loading." : "Plan is unavailable until the load error is resolved."
    : saving ? "Plan is already saving."
      : createUncertain ? "Refresh Saved Plans and resolve the uncertain creation first."
        : recoveryConflict ? "Resolve the saved Plan conflict before saving."
          : uncertainCreateDraft && !documentId ? "Restore or discard the separately recovered draft first."
            : !markdown.trim() ? "Add Plan content before saving."
              : null;
  const saveDisabledReasonRef = useRef<string | null>(saveDisabledReason);
  saveDisabledReasonRef.current = saveDisabledReason;
  const setCurrentEditor = (next: Editor | null) => {
    editorRef.current = next;
    setEditor(next);
  };

  const toolbarModel = useMemo<MarkdownEditorToolbarModel>(() => {
    const action = (id: string, label: string, invoke: (active: Editor) => void, disabled = false) => ({
      id,
      label,
      onClick: () => {
        const active = editorRef.current;
        if (!mountedRef.current || workObjectRef.current !== workObjectKey
          || selectionEpochRef.current !== selectionEpoch
          || !active || editorIdentityRef.current !== editorIdentity || statusRef.current !== "ready"
          || savingRef.current || disabled) return;
        invoke(active);
      },
      disabled: !editor || status !== "ready" || saving || disabled,
    });
    return {
      pinnedActions: [{
        id: "world-plan-save",
        label: saving ? "Saving…" : "Save Plan",
        disabled: saveDisabledReason !== null,
        disabledReason: saveDisabledReason ?? undefined,
        onClick: () => {
          if (!mountedRef.current || workObjectRef.current !== workObjectKey
            || selectionEpochRef.current !== selectionEpoch
            || editorIdentityRef.current !== editorIdentity || statusRef.current !== "ready"
            || savingRef.current || saveDisabledReasonRef.current) return;
          void save();
        },
      }],
      sections: [
        {
          id: "world-plan-document",
          title: "Plan document",
          defaultOpen: true,
          actions: [],
          panel: (
            <label className="world-owned-plan__title-control">
              Plan title
              <input
                value={title}
                disabled={status !== "ready"}
                onChange={(event) => {
                  if (!mountedRef.current || workObjectRef.current !== workObjectKey
                    || selectionEpochRef.current !== selectionEpoch
                    || editorIdentityRef.current !== editorIdentity || statusRef.current !== "ready") return;
                  const next = event.target.value;
                  titleRef.current = next;
                  const generation = ++editGenerationRef.current;
                  setTitle(next);
                  persistEditorDraft(next, markdownRef.current, generation);
                }}
              />
            </label>
          ),
        },
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
  }, [createUncertain, documentId, editor, editorIdentity, markdown, recoveryConflict, saveDisabledReason, saving, status, title, uncertainCreateDraft, workObjectKey]);

  const appChromeTools = useMemo(
    () => toAppChromeToolsGeneration(toolbarModel, workObject),
    [toolbarModel, workObject],
  );

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
          serverMarkdownRef.current = snapshot.markdown;
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
            edit_generation: localDraft?.edit_generation ?? 0,
            pending_write: pendingWriteRef.current,
            create_uncertain: false,
          });
        }
        else if (localDraft?.document_id === null) {
          documentIdRef.current = null;
          revisionRef.current = null;
          persistWorldPlanLocalDraft(worldId, localDraft);
        }
        if (!cancelled) setStatus("ready");
      } catch (reason) {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "World Plan could not be loaded.");
          setStatus("error");
        }
      }
    })();
    return () => { cancelled = true; };
  }, [initialDocumentId, localDraft, worldId]);

  const openPlan = async (nextDocumentId: string) => {
    if (savingRef.current) return;
    const epoch = ++selectionEpochRef.current;
    const priorDocumentId = documentIdRef.current;
    editorIdentityRef.current = `${worldId}:${nextDocumentId}:${editorGeneration + 1}`;
    editorRef.current = null;
    setEditor(null);
    setStatus("loading");
    setError(null);
    try {
      const snapshot = await getWorldOwnedPlanSnapshot(nextDocumentId);
      if (snapshot.record.world_id !== worldId || snapshot.record.campaign_id !== null) {
        throw new Error("This Plan does not belong to the selected World.");
      }
      if (!selectedViewIsCurrent(epoch, priorDocumentId)) return;
      const preservedUncertainDraft = readWorldPlanLocalDraft(worldId)?.uncertain_create_draft
        ?? uncertainCreateDraftRef.current;
      const url = new URL(window.location.href);
      url.searchParams.set("world", worldId);
      url.searchParams.set("documentId", nextDocumentId);
      window.history.pushState({}, "", `${url.pathname}${url.search}`);
      documentIdRef.current = nextDocumentId;
      setLocalDraftId(null);
      revisionRef.current = snapshot.loaded_revision;
      titleRef.current = snapshot.record.title;
      markdownRef.current = snapshot.markdown;
      serverMarkdownRef.current = snapshot.markdown;
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
      setStatus("ready");
    } catch (reason) {
      if (!selectedViewIsCurrent(epoch, priorDocumentId)) return;
      setError(reason instanceof Error ? reason.message : "Plan could not be opened.");
      setStatus("error");
    }
  };

  const resetBlankPlan = () => {
    if (savingRef.current) return;
    ++selectionEpochRef.current;
    const nextLocalDraftId = createWorldPlanLocalDraftId();
    editorIdentityRef.current = `${worldId}:blank:${editorGeneration + 1}`;
    editorRef.current = null;
    setEditor(null);
    documentIdRef.current = null;
    revisionRef.current = null;
    titleRef.current = "Plan";
    markdownRef.current = "";
    pendingWriteRef.current = null;
    setRecoveryConflict(false);
    setServerDraft(null);
    setCreateUncertain(false);
    const url = new URL(window.location.href);
    url.searchParams.set("world", worldId);
    url.searchParams.delete("documentId");
    window.history.pushState({}, "", `${url.pathname}${url.search}`);
    setDocumentId(null);
    setLocalDraftId(nextLocalDraftId);
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
          setLocalDraftId(null);
          revisionRef.current = currentRevision;
          titleRef.current = submittedTitle;
          markdownRef.current = submittedMarkdown;
          serverMarkdownRef.current = "";
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
            });
            setError("The previous save outcome cannot be proven against the current World revision. Your local draft is preserved and saving is blocked until you choose a version.");
          }
          return;
        }
        currentRevision = snapshot.loaded_revision;
        revisionRef.current = currentRevision;
        serverMarkdownRef.current = committed ? committedMarkdown ?? snapshot.markdown : snapshot.markdown;
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
        local_draft_id: null,
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
      serverMarkdownRef.current = submittedMarkdown;
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
    if (!serverDraft) return;
    titleRef.current = serverDraft.title;
    markdownRef.current = serverDraft.markdown;
    revisionRef.current = serverDraft.revision;
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
      local_draft_id: documentIdRef.current ? null : localDraftId,
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
    if (!recovery || !selectedId || savingRef.current) return;
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
    if (!uncertainCreateDraftRef.current || savingRef.current) return;
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
      local_draft_id: documentIdRef.current ? null : localDraftId,
    });
  };

  return (
    <AppChrome activeRoute="plan" editorTools={appChromeTools} editToolboxLayout="dock">
      <WorldPlanSurfaceContext
        worldId={worldId}
        worldName={worldName}
        documentId={documentId}
        workObject={workObject}
        records={records}
        disabled={saving || status === "loading"}
        onSelect={(nextId) => { void openPlan(nextId); }}
        onNewPlan={resetBlankPlan}
      />
      <main className="app-status world-owned-plan" data-testid="world-owned-plan">
        <header className="world-owned-plan__heading">
          <div>
            <p className="plan-surface-kicker">WORLD PLAN</p>
            <h1>{documentId ? title || "Untitled Plan" : "New Plan"}</h1>
            <p className="world-owned-plan__intro">A working space for this World. Your draft is local until you save it.</p>
          </div>
        </header>
        {createUncertain ? (
          <section role="alert">
            <p>Plan creation may have succeeded, but its response was lost. Refresh Saved Plans and open a candidate if one appears. Its identity is not assumed; the recovered text stays separate until you explicitly restore it into a Plan or discard it. Automatic creation retry is blocked to avoid duplicates.</p>
            <button type="button" onClick={() => void refreshSavedPlans()} disabled={saving}>Refresh Saved Plans</button>
            <button type="button" onClick={discardUncertainDraft} disabled={saving}>Discard recovered draft</button>
          </section>
        ) : null}
        {uncertainCreateDraft && !createUncertain ? (
          <section role="status" aria-label="Recovered Plan draft">
            <p>An unsaved draft from an uncertain Plan creation is preserved separately. It has not been assumed to belong to the selected Plan.</p>
            {documentId ? <button type="button" onClick={restoreUncertainDraftIntoSelectedPlan} disabled={saving}>Restore recovered draft into this Plan</button> : null}
            <button type="button" onClick={discardUncertainDraft} disabled={saving}>Discard recovered draft</button>
          </section>
        ) : null}
        {recoveryConflict && serverDraft ? (
          <section role="alert">
            <p>The server Plan changed while a local draft was pending. Your local text is preserved, but cannot overwrite the newer server version silently.</p>
            <button type="button" onClick={useServerVersion}>Use saved Plan version</button>
          </section>
        ) : null}
        <PlanSurfaceCanvasFrame
          className="world-owned-plan__canvas"
          testId="world-owned-plan-editor"
          identityLabel={documentId ? `Editing Plan · ${title || "Untitled"}` : "Unsaved Plan draft"}
          themeId="world-plan"
        >
          <MarkdownEditorCore
            content={editorContent}
            documentKey={`${worldId}:${documentId ?? "local"}:${editorGeneration}`}
            editable
            extensions={[SemanticMarkdownPaste]}
            onEditorChange={setCurrentEditor}
            dataTestId="world-owned-plan-markdown-editor"
            onUpdate={(json: JSONContent, _editor: Editor, meta) => {
              if (!meta.programmatic) {
                const next = defaultMarkdownDocumentAdapter.exportMarkdown(json);
                markdownRef.current = next;
                const generation = ++editGenerationRef.current;
                setMarkdown(next);
                persistEditorDraft(titleRef.current, next, generation);
              }
            }}
          >
            {(editor) => <EditorContent editor={editor} aria-label="Markdown plan" />}
          </MarkdownEditorCore>
        </PlanSurfaceCanvasFrame>
        {status === "loading" ? <p role="status">Loading World Plan…</p> : null}
        {message ? <p role="status">{message}</p> : null}
        {error ? <p role="alert">{error}</p> : null}
      </main>
    </AppChrome>
  );
}
