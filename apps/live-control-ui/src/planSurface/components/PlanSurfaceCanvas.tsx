import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Content, Editor } from "@tiptap/core";
import { EditorContent } from "@tiptap/react";

import { getWorkspaceDocumentSnapshot } from "../../api/liveApi";
import type { AppChromeTools } from "../../chrome/AppChrome";
import {
  GraphNodeChipRuntimeProvider,
  type GraphNodeChipRuntimeValue,
} from "../../graphReference";
import { defaultMarkdownDocumentAdapter } from "../../tiptap/MarkdownDocumentAdapter";
import { MarkdownEditorCore } from "../../tiptap/MarkdownEditorCore";
import {
  toAppChromeTools,
  type MarkdownEditorToolbarModel,
} from "../../tiptap/MarkdownEditorToolbar";
import {
  CALLOUT_KINDS,
  defaultCalloutLabel,
  type CalloutKind,
} from "../../tiptap/markdown/calloutMarkdown";
import {
  GRAPH_NODE_REF_TYPE,
  type RunbookReferenceAttrs,
} from "../../tiptap/references/runbookReferences";
import { createStarterContentForPlanDocument } from "../config/planSessionDescriptor";
import {
  readWorkspaceDocumentLocalState,
  writeWorkspaceDocumentLocalState,
  workspaceDocumentStorageKey,
  type WorkspaceDocumentLocalKind,
  type WorkspaceDocumentLocalState,
} from "../../tiptap/state/tiptapLocalState";
import { openWorkspaceDocumentAuthoringState } from "../../workspaceDocument/openWorkspaceDocumentAuthoringState";
import { useEditCapability } from "../edit/editCapability";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphProjectionNodeView } from "../../api/types";
import { useProjection } from "../projection/projectionContext";
import { readReferenceFromElement } from "../reference/referenceResolver";
import { usePlanGraphReferenceResolver } from "../reference/usePlanGraphReferenceResolver";
import { adaptWorldGraphNodeForPlanCard } from "../reference/worldGraphProjectionAdapter";
import { usePlanMarkdownSave } from "../save/usePlanMarkdownSave";
import type { PlanDocumentDescriptor, PlanSessionDescriptor, SurfaceThemeConfig } from "../types";
import { PlanGraphLoadPanel } from "./PlanGraphLoadPanel";
import { PlanGraphRefSearch } from "./PlanGraphRefSearch";
import "../../../../../evals/c2_live_prep/mireward-prep/assets/prep-markdown-themes.css";
import "../../tiptap/tiptapSpike.css";

type AuthoringLoadStatus = "loading" | "ready" | "conflict" | "error";

interface PlanSurfaceCanvasProps {
  sessionDescriptor: PlanSessionDescriptor;
  theme: SurfaceThemeConfig;
  onEditorToolsChange?: (tools: AppChromeTools | null) => void;
  onSaveStatusChange?: (statusLabel: string) => void;
  onPlanningDocumentCommitted?: (document: PlanDocumentDescriptor) => void;
}

export function PlanSurfaceCanvas({
  sessionDescriptor,
  theme,
  onEditorToolsChange,
  onSaveStatusChange,
  onPlanningDocumentCommitted,
}: PlanSurfaceCanvasProps) {
  const planningDocument = sessionDescriptor.planningDocument;
  const documentKind = planningDocument.kind as WorkspaceDocumentLocalKind;
  const { isLocked, canEdit, toggleLock } = useEditCapability();
  const { openContentFromChip, openPlanReferenceResolution } = useProjection();
  const {
    resolvePlanReference,
    projection,
    projectionState,
    projectionError,
  } = usePlanGraphReferenceResolver();
  const editorShellRef = useRef<HTMLDivElement | null>(null);
  const markDirtyRef = useRef<() => void>(() => {});
  const skipNextDirtyRef = useRef(true);
  const workingStateRef = useRef<WorkspaceDocumentLocalState | null>(null);

  const [authoringStatus, setAuthoringStatus] = useState<AuthoringLoadStatus>("loading");
  const [authoringError, setAuthoringError] = useState<string | null>(null);
  const [conflictReason, setConflictReason] = useState<string | null>(null);
  const [workingState, setWorkingState] = useState<WorkspaceDocumentLocalState | null>(null);
  const [documentKey, setDocumentKey] = useState(planningDocument.documentId);

  useEffect(() => {
    workingStateRef.current = workingState;
  }, [workingState]);

  const loadAuthoringState = useCallback(async () => {
    setAuthoringStatus("loading");
    setAuthoringError(null);
    setConflictReason(null);
    try {
      const snapshot = await getWorkspaceDocumentSnapshot(planningDocument.documentId);
      const stored = readWorkspaceDocumentLocalState(window.localStorage, planningDocument.documentId);
      const opened = openWorkspaceDocumentAuthoringState({
        snapshot,
        stored,
        surface: "plan",
        kind: documentKind,
        emptyMarkdownFallback: createStarterContentForPlanDocument(sessionDescriptor),
      });

      if (opened.status === "conflict") {
        setWorkingState(stored);
        setConflictReason(
          opened.reconciliation.conflictReason ?? "Local draft conflicts with server content.",
        );
        setDocumentKey(`${planningDocument.documentId}:conflict:${snapshot.loaded_revision}`);
        setAuthoringStatus("conflict");
        return;
      }
      if (opened.status === "reject" || !opened.localState) {
        setWorkingState(null);
        setAuthoringError(opened.reconciliation.rejectReason ?? "Local draft was rejected.");
        setAuthoringStatus("error");
        return;
      }

      writeWorkspaceDocumentLocalState(window.localStorage, opened.localState);
      setWorkingState(opened.localState);
      setDocumentKey(
        `${planningDocument.documentId}:${snapshot.loaded_revision}:${opened.localState.dirty ? "dirty" : "clean"}`,
      );
      skipNextDirtyRef.current = true;
      setAuthoringStatus("ready");
    } catch (loadError) {
      setWorkingState(null);
      setAuthoringError(
        loadError instanceof Error ? loadError.message : "Unable to load workspace document.",
      );
      setAuthoringStatus("error");
    }
  }, [documentKind, planningDocument.documentId, sessionDescriptor]);

  useEffect(() => {
    void loadAuthoringState();
  }, [loadAuthoringState]);

  const handleDiscardLocalDraft = useCallback(() => {
    window.localStorage.removeItem(workspaceDocumentStorageKey(planningDocument.documentId));
    void loadAuthoringState();
  }, [loadAuthoringState, planningDocument.documentId]);

  const handlePlanningDocumentCommitted = useCallback(
    async (document: PlanDocumentDescriptor) => {
      onPlanningDocumentCommitted?.(document);
      try {
        const snapshot = await getWorkspaceDocumentSnapshot(document.documentId);
        const opened = openWorkspaceDocumentAuthoringState({
          snapshot,
          stored: null,
          surface: "plan",
          kind: documentKind,
          emptyMarkdownFallback: createStarterContentForPlanDocument(sessionDescriptor),
        });
        if (!opened.localState) return;
        const nextLocalState: WorkspaceDocumentLocalState = {
          ...opened.localState,
          title: document.title,
          dirty: false,
        };
        writeWorkspaceDocumentLocalState(window.localStorage, nextLocalState);
        setWorkingState(nextLocalState);
        setDocumentKey(`${document.documentId}:${snapshot.loaded_revision}:committed`);
      } catch {
        // Snapshot refresh after save is best-effort; local dirty flag was already cleared by save flow.
      }
    },
    [documentKind, onPlanningDocumentCommitted, sessionDescriptor],
  );

  const effectivePlanningDocument = useMemo(
    () => ({
      ...planningDocument,
      revision: workingState?.base_revision ?? planningDocument.revision,
    }),
    [planningDocument, workingState?.base_revision],
  );

  const [editor, setEditor] = useState<Editor | null>(null);

  const {
    state: saveState,
    statusLabel,
    saveDisabled,
    markDirty,
    saveMarkdown,
  } = usePlanMarkdownSave({
    editor,
    planningDocument: effectivePlanningDocument,
    onPlanningDocumentCommitted: (document) => {
      void handlePlanningDocumentCommitted(document);
    },
  });

  useEffect(() => {
    markDirtyRef.current = markDirty;
  }, [markDirty]);

  useEffect(() => {
    onSaveStatusChange?.(statusLabel);
  }, [onSaveStatusChange, statusLabel]);

  const insertCallout = useCallback(
    (kind: CalloutKind) => {
      editor?.chain().focus().insertCallout({ kind }).run();
    },
    [editor],
  );

  const insertRunbookReference = useCallback(
    (attrs: RunbookReferenceAttrs) => {
      editor?.chain().focus().insertRunbookReference(attrs).run();
    },
    [editor],
  );

  const projectionNodes = useMemo(
    () => projection?.nodes.map((node) => adaptWorldGraphNodeForPlanCard(node)) ?? [],
    [projection],
  );

  const handleViewGraphNode = useCallback(
    (node: GraphProjectionNodeView) => {
      openPlanReferenceResolution(
        {
          kind: "graph-node",
          locator: `dmb-node:${node.node_id}`,
          refType: node.kind,
          refId: node.node_id,
          graphObject: buildGraphObjectCardFromNodeView(node),
          graphNodeId: node.node_id,
          fallback: null,
          source: "world-graph",
          message: `Resolved graph node ${node.label}.`,
          graphProjectionState: projectionState,
        },
        projectionState,
      );
    },
    [openPlanReferenceResolution, projectionState],
  );

  const graphRefSearchPanel = useMemo(
    () => (
      <PlanGraphRefSearch
        nodes={projectionNodes}
        projectionState={projectionState}
        projectionError={projectionError}
        insertDisabled={!editor || isLocked || authoringStatus !== "ready"}
        onInsert={insertRunbookReference}
        onView={handleViewGraphNode}
      />
    ),
    [
      authoringStatus,
      editor,
      handleViewGraphNode,
      insertRunbookReference,
      isLocked,
      projectionError,
      projectionNodes,
      projectionState,
    ],
  );

  const copyMarkdown = useCallback(async () => {
    if (!editor || !navigator.clipboard?.writeText) return;
    const markdown = defaultMarkdownDocumentAdapter.exportMarkdown(editor.getJSON());
    await navigator.clipboard.writeText(markdown);
  }, [editor]);

  const removeActiveBlock = useCallback(() => {
    editor?.chain().focus().deleteActiveBlock().run();
  }, [editor]);

  const handleChipActivate = useCallback(
    async (target: EventTarget | null) => {
      if (!(target instanceof HTMLElement) || !editorShellRef.current?.contains(target)) return;
      const chip = target.closest(".md-ref-chip");
      if (!(chip instanceof HTMLElement)) return;
      const ref = readReferenceFromElement(chip);
      if (!ref) return;
      const resolution = await resolvePlanReference(ref);
      openContentFromChip(ref, resolution, true, projectionState);
    },
    [openContentFromChip, projectionState, resolvePlanReference],
  );

  const openGraphNodeFromChip = useCallback(
    async (nodeId: string) => {
      const node = projection?.nodes.find((entry) => entry.nodeId === nodeId);
      const ref: RunbookReferenceAttrs = {
        kind: "ref",
        refType: GRAPH_NODE_REF_TYPE,
        refId: nodeId,
        label: node?.label ?? nodeId,
      };
      const resolution = await resolvePlanReference(ref);
      openContentFromChip(ref, resolution, true, projectionState);
    },
    [openContentFromChip, projection, projectionState, resolvePlanReference],
  );

  const chipRuntime = useMemo<GraphNodeChipRuntimeValue>(() => {
    const nodeViews: Record<string, GraphProjectionNodeView> = {};
    for (const node of projection?.nodes ?? []) {
      nodeViews[node.nodeId] = adaptWorldGraphNodeForPlanCard(node);
    }
    return {
      nodeViews,
      activeNodeId: null,
      onSelectNode: (nodeId) => {
        void openGraphNodeFromChip(nodeId);
      },
    };
  }, [openGraphNodeFromChip, projection?.nodes]);

  const toolbarModel = useMemo<MarkdownEditorToolbarModel>(() => ({
    pinnedActions: [
      {
        id: "plan-canvas-edit-lock",
        eyebrow: isLocked ? "Editing locked" : "Editing unlocked",
        label: isLocked ? "Unlock editing" : "Lock editing",
        onClick: toggleLock,
        pressed: isLocked,
      },
    ],
    sections: [
      {
        id: "plan-world-graph-objects",
        title: "World Graph objects",
        defaultOpen: true,
        actions: [],
        panel: graphRefSearchPanel,
      },
      {
        id: "plan-insert-blocks",
        title: "Insert blocks",
        defaultOpen: true,
        actions: CALLOUT_KINDS.map((kind) => ({
          id: `plan-insert-${kind}`,
          eyebrow: "Insert",
          label: defaultCalloutLabel(kind),
          onClick: () => insertCallout(kind),
          disabled: !editor || isLocked || authoringStatus !== "ready",
        })),
      },
      {
        id: "plan-edit-blocks",
        title: "Edit blocks",
        defaultOpen: true,
        actions: [
          {
            id: "plan-remove-block",
            eyebrow: "Remove",
            label: "Remove block",
            onClick: removeActiveBlock,
            disabled: !editor || isLocked || authoringStatus !== "ready",
          },
        ],
      },
      {
        id: "plan-markdown-export",
        title: "Markdown export",
        defaultOpen: true,
        actions: [
          {
            id: "plan-copy-markdown",
            eyebrow: "Export",
            label: "Copy Markdown",
            onClick: () => {
              void copyMarkdown();
            },
            disabled: !editor,
          },
        ],
      },
      {
        id: "plan-markdown-save",
        title: "Markdown save",
        defaultOpen: true,
        actions: [
          {
            id: "plan-save-markdown",
            label: "Save to Markdown",
            onClick: () => {
              void saveMarkdown();
            },
            disabled: saveDisabled || authoringStatus !== "ready",
          },
        ],
      },
    ],
  }), [
    authoringStatus,
    copyMarkdown,
    editor,
    graphRefSearchPanel,
    insertCallout,
    isLocked,
    removeActiveBlock,
    saveDisabled,
    saveMarkdown,
    toggleLock,
  ]);

  useEffect(() => {
    onEditorToolsChange?.(toAppChromeTools(toolbarModel));
    return () => onEditorToolsChange?.(null);
  }, [onEditorToolsChange, toolbarModel]);

  const editorThemeClass = `md-theme-${theme.themeId ?? "mireward-runbook"}`;

  const editorBody = (() => {
    if (authoringStatus === "loading") {
      return (
        <p data-testid="plan-canvas-authoring-loading">Loading plan document…</p>
      );
    }
    if (authoringStatus === "conflict") {
      return (
        <div data-testid="plan-canvas-authoring-conflict">
          <p>{conflictReason ?? "Local draft conflicts with server content."}</p>
          <button type="button" onClick={() => void loadAuthoringState()}>
            Reload from server
          </button>
          <button type="button" onClick={handleDiscardLocalDraft}>
            Discard local draft
          </button>
        </div>
      );
    }
    if (authoringStatus === "error") {
      return (
        <p role="alert" data-testid="plan-canvas-authoring-error">
          {authoringError ?? "Unable to load plan document."}
        </p>
      );
    }
    if (!workingState) {
      return null;
    }
    return (
      <MarkdownEditorCore
        content={workingState.tiptap_json as Content}
        documentKey={documentKey}
        editable={canEdit}
        onEditorChange={setEditor}
        onUpdate={(tiptapJson) => {
          const current = workingStateRef.current;
          if (!current) return;
          const now = new Date().toISOString();
          const next: WorkspaceDocumentLocalState = {
            ...current,
            tiptap_json: tiptapJson,
            updated_at: now,
            last_local_save_at: now,
            dirty: true,
          };
          writeWorkspaceDocumentLocalState(window.localStorage, next);
          setWorkingState(next);
          if (skipNextDirtyRef.current) {
            skipNextDirtyRef.current = false;
            return;
          }
          markDirtyRef.current();
        }}
        dataTestId="plan-surface-canvas-editor"
      >
        {(ed) => (
          <GraphNodeChipRuntimeProvider value={chipRuntime}>
            <EditorContent editor={ed} />
          </GraphNodeChipRuntimeProvider>
        )}
      </MarkdownEditorCore>
    );
  })();

  return (
    <section className="plan-surface-canvas" aria-label="Plan canvas">
      <header className="plan-canvas-heading" aria-label="Plan Board">
        <div className="plan-canvas-heading__identity">
          <p className="plan-surface-kicker">Plan Board</p>
          <h2 data-testid="plan-canvas-title">{planningDocument.title}</h2>
          <p className="plan-canvas-meta" data-testid="plan-canvas-save-status">
            {statusLabel}
          </p>
        </div>
        <div className="plan-canvas-heading__graph">
          <PlanGraphLoadPanel
            projectionState={projectionState}
            projectionError={projectionError}
            nodeCount={projectionNodes.length}
          />
        </div>
      </header>

      <div
        ref={editorShellRef}
        className={`tiptap-spike-editor md-content ${editorThemeClass}`}
        data-md-theme={theme.themeId}
        onClick={(event) => {
          void handleChipActivate(event.target);
        }}
      >
        {editorBody}
      </div>

      {(saveState.status === "committed" || saveState.error || saveState.warnings?.length || saveState.diagnostics?.length) && (
        <section
          className="plan-markdown-save-panel"
          aria-label="Markdown save status"
          data-testid="plan-markdown-save-panel"
        >
          <p className="plan-surface-kicker">Durable save</p>
          <p className="plan-markdown-save-target" data-testid="plan-markdown-save-target">
            Target: {planningDocument.targetRelpath}
          </p>
          {saveState.warnings?.map((warning) => (
            <p className="plan-markdown-save-warning" key={warning}>
              {warning}
            </p>
          ))}
          {saveState.diagnostics?.map((diagnostic) => (
            <p className="plan-markdown-save-diagnostic" key={diagnostic}>
              {diagnostic}
            </p>
          ))}
          {saveState.error && (
            <p className="plan-markdown-save-error" role="alert" data-testid="plan-markdown-save-error">
              {saveState.error}
            </p>
          )}
          {saveState.committed && (
            <dl className="plan-markdown-save-success" data-testid="plan-markdown-save-success">
              <div>
                <dt>Path</dt>
                <dd>{saveState.committed.target_display_path}</dd>
              </div>
              <div>
                <dt>Bytes written</dt>
                <dd>{saveState.committed.bytes_written}</dd>
              </div>
              {saveState.committed.backup_relpath && (
                <div>
                  <dt>Backup</dt>
                  <dd>{saveState.committed.backup_relpath}</dd>
                </div>
              )}
            </dl>
          )}
        </section>
      )}
    </section>
  );
}
