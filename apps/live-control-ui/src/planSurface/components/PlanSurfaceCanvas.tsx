import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { Content, Editor } from "@tiptap/core";
import { EditorContent } from "@tiptap/react";

import type { AppChromeToolsGeneration } from "../../chrome/AppChrome";
import {
  GraphNodeChipRuntimeProvider,
  insertMarkdownReference,
  type GraphNodeChipRuntimeValue,
} from "../../graphReference";
import { defaultMarkdownDocumentAdapter } from "../../tiptap/MarkdownDocumentAdapter";
import { MarkdownEditorCore } from "../../tiptap/MarkdownEditorCore";
import { SemanticMarkdownPaste } from "../../tiptap/extensions/SemanticMarkdownPaste";
import {
  toAppChromeToolsGeneration,
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
import type {
  WorkspaceDocumentLocalKind,
  WorkspaceDocumentLocalSurface,
} from "../../tiptap/state/tiptapLocalState";
import { isEditorInteractive } from "../../workspaceDocument/workspaceDocumentAuthoringMachine";
import { useWorkspaceDocumentAuthoring } from "../../workspaceDocument/useWorkspaceDocumentAuthoring";
import type { WorkspaceDocumentCreationController } from "../../workspaceDocument/workspaceDocumentCreation";
import { useEditCapability } from "../edit/editCapability";
import {
  planShellWorkObject,
  type PlanAuthoringShellState,
} from "../planBlankAuthoringState";
import { usePlanBlankAuthoring } from "../usePlanBlankAuthoring";
import type { GraphProjectionNodeView } from "../../api/types";
import { extractExactGraphReferenceScope } from "../../graphReference/resolveGraphReference";
import { useProjection } from "../projection/projectionContext";
import { readReferenceFromElement } from "../reference/referenceResolver";
import { usePlanGraphReferenceResolver } from "../reference/usePlanGraphReferenceResolver";
import { adaptWorldGraphNodeForPlanCard } from "../reference/worldGraphProjectionAdapter";
import { PlanWorldGraphObjectsPanel } from "./PlanWorldGraphObjectsPanel";
import { glanceOnlyForGraphReference } from "../../graphReference/openGraphReferencePolicy";
import type { PlanDocumentDescriptor, PlanSessionDescriptor, SurfaceThemeConfig } from "../types";
import "../../tiptap/prepMarkdownThemes.css";
import "../../tiptap/tiptapSpike.css";
import "../../graphReference/graphReference.css";

const TBD_PLAN_PATH = "TBD durable planning path";

export function canSavePlanningDocument(document: {
  kind: string;
  targetRelpath: string | null;
}): boolean {
  if (document.kind === "runbook") return true;
  return document.targetRelpath != null && document.targetRelpath !== TBD_PLAN_PATH;
}

export interface PlanGraphInsertEditorGate {
  editor: Editor | null;
  isLocked: boolean;
  editorInteractive: boolean;
}

export function isPlanGraphInsertEditorLive(input: PlanGraphInsertEditorGate): boolean {
  return Boolean(input.editor) && !input.isLocked && input.editorInteractive;
}

export function insertPlanGraphReferenceIfLive(input: {
  getGate: () => PlanGraphInsertEditorGate;
  reference: RunbookReferenceAttrs;
  insert: (editor: Editor, reference: RunbookReferenceAttrs) => void;
}): void {
  const gate = input.getGate();
  if (!isPlanGraphInsertEditorLive(gate) || gate.editor == null) return;
  input.insert(gate.editor, input.reference);
}

const CLOSED_PLAN_GRAPH_INSERT_GATE: PlanGraphInsertEditorGate = {
  editor: null,
  isLocked: true,
  editorInteractive: false,
};

/**
 * Visible insertEnabled follows the current render. Retained Insert callbacks
 * read the last committed gate so a speculative unlock cannot leak into the
 * still-locked committed UI. Unmount cleanup closes the gate so AppChrome-retained
 * editorTools cannot insert through a removed editor.
 */
export function useCommittedPlanGraphInsertGate(input: PlanGraphInsertEditorGate): {
  insertEnabled: boolean;
  isInsertCurrentlyEnabled: () => boolean;
  getCommittedGate: () => PlanGraphInsertEditorGate;
} {
  const gateRef = useRef<PlanGraphInsertEditorGate>(CLOSED_PLAN_GRAPH_INSERT_GATE);

  useLayoutEffect(() => {
    gateRef.current = {
      editor: input.editor,
      isLocked: input.isLocked,
      editorInteractive: input.editorInteractive,
    };
    return () => {
      gateRef.current = CLOSED_PLAN_GRAPH_INSERT_GATE;
    };
  }, [input.editor, input.editorInteractive, input.isLocked]);

  const insertEnabled = isPlanGraphInsertEditorLive(input);

  const isInsertCurrentlyEnabled = useCallback(
    () => isPlanGraphInsertEditorLive(gateRef.current),
    [],
  );

  const getCommittedGate = useCallback(() => gateRef.current, []);

  return { insertEnabled, isInsertCurrentlyEnabled, getCommittedGate };
}

function authoringIdentityLabel(document: PlanDocumentDescriptor): string {
  const title = document.title.trim() || "Untitled";
  if (document.kind === "runbook") return `Editing Runbook · ${title}`;
  return `Editing Plan · ${title}`;
}

interface PlanSurfaceCanvasProps {
  sessionDescriptor: PlanSessionDescriptor;
  theme: SurfaceThemeConfig;
  shellState: PlanAuthoringShellState;
  loadErrorMessage?: string | null;
  selectorListAvailable: boolean;
  createController: WorkspaceDocumentCreationController;
  onEditorToolsChange?: (tools: AppChromeToolsGeneration | null) => void;
  onSaveStatusChange?: (statusLabel: string) => void;
  onPlanningDocumentCommitted?: (document: PlanDocumentDescriptor) => void;
  onBlankPromoted?: (document: PlanDocumentDescriptor) => void;
  onBlankPromotionStateChange?: (args: {
    promoting: boolean;
    retainedCreateId: string | null;
    error: string | null;
  }) => void;
}

export function PlanSurfaceCanvas(props: PlanSurfaceCanvasProps) {
  if (
    props.shellState.kind === "load_error"
    && props.shellState.localDraft
    && props.shellState.inventoryUnavailable
  ) {
    return (
      <PlanLocalBlankSurfaceCanvas
        {...props}
        draft={props.shellState.localDraft}
        retainedCreateId={null}
        selectorListAvailable={false}
        inventoryUnavailable
      />
    );
  }
  if (props.shellState.kind === "blank_ready" || props.shellState.kind === "promoting") {
    return (
      <PlanLocalBlankSurfaceCanvas
        {...props}
        draft={props.shellState.draft}
        retainedCreateId={
          props.shellState.kind === "promoting" ? props.shellState.retainedCreateId : null
        }
        selectorListAvailable={props.shellState.selectorListAvailable}
      />
    );
  }
  if (props.shellState.kind === "durable_ready") {
    return <PlanDurableSurfaceCanvas {...props} />;
  }
  return <PlanShellStatusSurfaceCanvas {...props} />;
}

function PlanDurableSurfaceCanvas({
  sessionDescriptor,
  theme,
  onEditorToolsChange,
  onSaveStatusChange,
  onPlanningDocumentCommitted,
  shellState,
}: PlanSurfaceCanvasProps) {
  const canvasWorkTarget = useMemo(() => planShellWorkObject(shellState), [shellState]);
  const planningDocument = sessionDescriptor.planningDocument;
  const documentKind = planningDocument.kind as WorkspaceDocumentLocalKind;
  const authoringSurface: WorkspaceDocumentLocalSurface =
    documentKind === "runbook" ? "runbook" : "plan";
  const { isLocked, canEdit, toggleLock } = useEditCapability();
  const { openGraphReference } = useProjection();
  const {
    resolvePlanReference,
    projection,
    projectionState,
  } = usePlanGraphReferenceResolver();
  const editorShellRef = useRef<HTMLDivElement | null>(null);

  const emptyMarkdownFallback = useMemo(
    () => createStarterContentForPlanDocument(sessionDescriptor),
    [
      sessionDescriptor.campaignId,
      sessionDescriptor.planningDocument.documentId,
      sessionDescriptor.planningDocument.targetSession,
    ],
  );

  const authoring = useWorkspaceDocumentAuthoring({
    documentId: planningDocument.documentId,
    surface: authoringSurface,
    kind: documentKind,
    emptyMarkdownFallback,
    requireDirtyToSave: false,
    canSave: () => canSavePlanningDocument(planningDocument),
  });

  const editorInteractive = isEditorInteractive(authoring.phase);
  const showEditor = authoring.phase !== "loading"
    && authoring.phase !== "unloaded"
    && authoring.phase !== "conflict"
    && authoring.phase !== "load_error";

  const deliveredHandbackKeysRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    deliveredHandbackKeysRef.current.clear();
  }, [planningDocument.documentId]);

  useEffect(() => {
    const receipt = authoring.lastCommitReceipt;
    const record = authoring.record;
    if (!receipt || !record) return;
    const loadedRevision = authoring.snapshot?.loaded_revision ?? record.revision;
    if (receipt.document_id !== record.document_id) return;
    if (receipt.committed_revision !== loadedRevision) return;
    const key = `${receipt.document_id}:${receipt.committed_revision}:${receipt.normalized_content_sha256}`;
    if (deliveredHandbackKeysRef.current.has(key)) return;
    deliveredHandbackKeysRef.current.add(key);
    onPlanningDocumentCommitted?.({
      ...planningDocument,
      title: record.title,
      targetRelpath: record.target_relpath,
      revision: record.revision,
      contentStatus: record.content_status,
    });
  }, [
    authoring.lastCommitReceipt,
    authoring.record,
    authoring.snapshot?.loaded_revision,
    onPlanningDocumentCommitted,
    planningDocument,
  ]);

  useEffect(() => {
    onSaveStatusChange?.(authoring.statusLabel);
  }, [onSaveStatusChange, authoring.statusLabel]);

  const [editor, setEditor] = useState<Editor | null>(null);

  const handleEditorChange = useCallback((nextEditor: Editor | null) => {
    authoring.setEditor(nextEditor);
    setEditor(nextEditor);
  }, [authoring.setEditor]);

  const insertCallout = useCallback(
    (kind: CalloutKind) => {
      editor?.chain().focus().insertCallout({ kind }).run();
    },
    [editor],
  );

  const insertDecisionConsequence = useCallback(() => {
    editor?.chain().focus().insertDecisionConsequence().run();
  }, [editor]);

  const planPasteExtensions = useMemo(() => [SemanticMarkdownPaste], []);

  const {
    insertEnabled: insertGraphReferenceEnabled,
    isInsertCurrentlyEnabled,
    getCommittedGate,
  } = useCommittedPlanGraphInsertGate({
    editor,
    isLocked,
    editorInteractive,
  });

  const handleInsertGraphReference = useCallback(
    (reference: RunbookReferenceAttrs) => {
      insertPlanGraphReferenceIfLive({
        getGate: getCommittedGate,
        reference,
        insert: insertMarkdownReference,
      });
    },
    [getCommittedGate],
  );

  const worldGraphObjectsPanel = useMemo(
    () => (
      <PlanWorldGraphObjectsPanel
        insertEnabled={insertGraphReferenceEnabled}
        isInsertCurrentlyEnabled={isInsertCurrentlyEnabled}
        onInsertReference={handleInsertGraphReference}
      />
    ),
    [handleInsertGraphReference, insertGraphReferenceEnabled, isInsertCurrentlyEnabled],
  );

  const copyMarkdown = useCallback(async () => {
    if (!editor || !navigator.clipboard?.writeText) return;
    const markdown = defaultMarkdownDocumentAdapter.exportMarkdown(editor.getJSON());
    await navigator.clipboard.writeText(markdown);
  }, [editor]);

  const removeActiveBlock = useCallback(() => {
    if (!editor) return;
    const removedPair = editor.chain().focus().deleteParentDecisionConsequence().run();
    if (!removedPair) {
      editor.chain().focus().deleteActiveBlock().run();
    }
  }, [editor]);

  const handleChipActivate = useCallback(
    async (target: EventTarget | null) => {
      if (!(target instanceof HTMLElement) || !editorShellRef.current?.contains(target)) return;
      const chip = target.closest(".md-ref-chip");
      if (!(chip instanceof HTMLElement)) return;
      const ref = readReferenceFromElement(chip);
      if (!ref) return;
      const resolution = await resolvePlanReference(ref);
      // Hover owns the parchment glance; Threat Reference opens as full StatblockRenderer.
      openGraphReference({
        reference: ref,
        resolution,
        projectionState,
        glanceOnly: glanceOnlyForGraphReference(resolution),
      });
    },
    [openGraphReference, projectionState, resolvePlanReference],
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
      openGraphReference({
        reference: ref,
        resolution,
        projectionState,
        glanceOnly: glanceOnlyForGraphReference(resolution),
      });
    },
    [openGraphReference, projection, projectionState, resolvePlanReference],
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
      exactGraphScope: extractExactGraphReferenceScope(projection),
    };
  }, [openGraphNodeFromChip, projection]);

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
        panel: worldGraphObjectsPanel,
      },
      {
        id: "plan-insert-blocks",
        title: "Insert blocks",
        defaultOpen: true,
        actions: [
          ...CALLOUT_KINDS.map((kind) => ({
            id: `plan-insert-${kind}`,
            eyebrow: "Insert",
            label: defaultCalloutLabel(kind),
            onClick: () => insertCallout(kind),
            disabled: !editor || isLocked || !editorInteractive,
          })),
          {
            id: "plan-insert-decision-consequence",
            eyebrow: "Insert",
            label: "Decision / Consequence",
            onClick: insertDecisionConsequence,
            disabled: !editor || isLocked || !editorInteractive,
          },
        ],
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
            disabled: !editor || isLocked || !editorInteractive,
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
              void authoring.saveMarkdown();
            },
            disabled: authoring.saveDisabled,
          },
        ],
      },
    ],
  }), [
    authoring.saveDisabled,
    authoring.saveMarkdown,
    copyMarkdown,
    editor,
    editorInteractive,
    insertCallout,
    insertDecisionConsequence,
    isLocked,
    removeActiveBlock,
    toggleLock,
    worldGraphObjectsPanel,
  ]);

  useEffect(() => {
    onEditorToolsChange?.(toAppChromeToolsGeneration(toolbarModel, canvasWorkTarget));
  }, [canvasWorkTarget, onEditorToolsChange, toolbarModel]);

  const editorThemeClass = `md-theme-${theme.themeId ?? "mireward-runbook"}`;

  const showSavePanel = Boolean(
    authoring.lastCommitReceipt
    || (authoring.phase === "save_error" && authoring.error)
    || (authoring.phase === "committed_verification_pending" && authoring.error),
  );

  const editorBody = (() => {
    if (authoring.phase === "loading" || authoring.phase === "unloaded") {
      return (
        <p data-testid="plan-canvas-authoring-loading">Loading plan document…</p>
      );
    }
    if (authoring.phase === "conflict") {
      return (
        <div data-testid="plan-canvas-authoring-conflict">
          <p>
            {authoring.reconciliation?.conflictReason
              ?? "Local draft conflicts with server content."}
          </p>
          <button type="button" onClick={() => void authoring.reloadFromSnapshot()}>
            Reload from server
          </button>
          <button type="button" onClick={() => void authoring.discardLocalDraft()}>
            Discard local draft
          </button>
        </div>
      );
    }
    if (authoring.phase === "load_error") {
      return (
        <p role="alert" data-testid="plan-canvas-authoring-error">
          {authoring.error ?? "Unable to load plan document."}
        </p>
      );
    }
    if (!showEditor) {
      return null;
    }
    return (
      <MarkdownEditorCore
        content={authoring.editorContent as Content}
        documentKey={authoring.documentKey}
        editable={canEdit}
        extensions={planPasteExtensions}
        onEditorChange={handleEditorChange}
        onUpdate={authoring.handleEditorUpdate}
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
      <p className="plan-surface-kicker" data-testid="plan-authoring-identity">
        {authoringIdentityLabel(planningDocument)}
      </p>
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

      {showSavePanel && (
        <section
          className="plan-markdown-save-panel"
          aria-label="Markdown save status"
          data-testid="plan-markdown-save-panel"
        >
          <p className="plan-surface-kicker">Durable save</p>
          <p className="plan-markdown-save-target" data-testid="plan-markdown-save-target">
            Target:{" "}
            {planningDocument.targetRelpath
              ?? (documentKind === "runbook" ? "native Runbook WorkObject" : "unset")}
          </p>
          {authoring.lastCommitReceipt?.diagnostics?.map((diagnostic) => (
            <p className="plan-markdown-save-diagnostic" key={diagnostic}>
              {diagnostic}
            </p>
          ))}
          {authoring.error && (authoring.phase === "save_error" || authoring.phase === "committed_verification_pending") && (
            <p className="plan-markdown-save-error" role="alert" data-testid="plan-markdown-save-error">
              {authoring.error}
            </p>
          )}
          {authoring.lastCommitReceipt && (
            <dl className="plan-markdown-save-success" data-testid="plan-markdown-save-success">
              <div>
                <dt>Path</dt>
                <dd>{authoring.lastCommitReceipt.target_display_path}</dd>
              </div>
              <div>
                <dt>Bytes written</dt>
                <dd>{authoring.lastCommitReceipt.bytes_written}</dd>
              </div>
              {authoring.lastCommitReceipt.backup_relpath && (
                <div>
                  <dt>Backup</dt>
                  <dd>{authoring.lastCommitReceipt.backup_relpath}</dd>
                </div>
              )}
            </dl>
          )}
        </section>
      )}
    </section>
  );
}

type PlanLocalBlankSurfaceCanvasProps = PlanSurfaceCanvasProps & {
  draft: import("../planBlankAuthoringState").PlanLocalDraft;
  retainedCreateId: string | null;
  selectorListAvailable: boolean;
  inventoryUnavailable?: boolean;
};

function PlanLocalBlankSurfaceCanvas({
  sessionDescriptor,
  theme,
  draft,
  retainedCreateId,
  selectorListAvailable,
  inventoryUnavailable = false,
  createController,
  shellState,
  onEditorToolsChange,
  onSaveStatusChange,
  onBlankPromoted,
  onBlankPromotionStateChange,
}: PlanLocalBlankSurfaceCanvasProps) {
  const canvasWorkTarget = useMemo(() => planShellWorkObject(shellState), [shellState]);
  const { isLocked, canEdit, toggleLock } = useEditCapability();
  const editorShellRef = useRef<HTMLDivElement | null>(null);
  const planPasteExtensions = useMemo(() => [SemanticMarkdownPaste], []);

  const blankAuthoring = usePlanBlankAuthoring({
    draft,
    sessionDescriptor,
    selectorListAvailable,
    retainedCreateId,
    createController,
    onPromoted: (document) => onBlankPromoted?.(document),
    onPromotionStateChange: onBlankPromotionStateChange,
  });

  useEffect(() => {
    onSaveStatusChange?.(blankAuthoring.statusLabel);
  }, [blankAuthoring.statusLabel, onSaveStatusChange]);

  const handleEditorChange = useCallback(
    (nextEditor: Editor | null) => {
      blankAuthoring.setEditor(nextEditor);
    },
    [blankAuthoring.setEditor],
  );

  const saveActionDisabledReason =
    blankAuthoring.saveDisabledReason
    ?? (blankAuthoring.saveBusy ? "Saving Plan…" : null);

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
        id: "plan-markdown-save",
        title: "Markdown save",
        defaultOpen: true,
        actions: [
          {
            id: "plan-save-markdown",
            label: "Save to Markdown",
            onClick: () => {
              void blankAuthoring.saveMarkdown();
            },
            disabled: blankAuthoring.saveDisabled,
            disabledReason: saveActionDisabledReason ?? undefined,
          },
        ],
      },
    ],
  }), [
    blankAuthoring.saveDisabled,
    blankAuthoring.saveMarkdown,
    isLocked,
    saveActionDisabledReason,
    toggleLock,
  ]);

  const editorToolsGeneration = useMemo(
    () => toAppChromeToolsGeneration(toolbarModel, canvasWorkTarget),
    [canvasWorkTarget, toolbarModel],
  );

  useEffect(() => {
    onEditorToolsChange?.(editorToolsGeneration);
  }, [editorToolsGeneration, onEditorToolsChange]);

  const editorThemeClass = `md-theme-${theme.themeId ?? "mireward-runbook"}`;

  return (
    <section className="plan-surface-canvas" aria-label="Plan canvas" data-testid="plan-blank-canvas">
      {inventoryUnavailable ? (
        <p className="plan-surface-list-warning" role="alert" data-testid="plan-selector-list-error">
          Active Plan inventory is unavailable; target session cannot be chosen safely.
        </p>
      ) : null}
      <div
        ref={editorShellRef}
        className={`tiptap-spike-editor md-content ${editorThemeClass}`}
        data-md-theme={theme.themeId}
      >
        <MarkdownEditorCore
          content={blankAuthoring.editorContent as Content}
          documentKey={blankAuthoring.documentKey}
          editable={canEdit && !blankAuthoring.saveBusy}
          extensions={planPasteExtensions}
          onEditorChange={handleEditorChange}
          onUpdate={blankAuthoring.handleEditorUpdate}
          dataTestId="plan-surface-canvas-editor"
        >
          {(ed) => <EditorContent editor={ed} />}
        </MarkdownEditorCore>
      </div>
      {blankAuthoring.promotionError ? (
        <p className="plan-markdown-save-error" role="alert" data-testid="plan-markdown-save-error">
          {blankAuthoring.promotionError}
        </p>
      ) : null}
    </section>
  );
}

function PlanShellStatusSurfaceCanvas({
  sessionDescriptor,
  theme,
  shellState,
  loadErrorMessage = null,
  onEditorToolsChange,
}: PlanSurfaceCanvasProps) {
  const canvasWorkTarget = useMemo(() => planShellWorkObject(shellState), [shellState]);
  const { isLocked, toggleLock } = useEditCapability();
  const disabledReason =
    loadErrorMessage != null
      ? "Document failed to load; retry or choose another document."
      : "Document is still loading.";

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
        id: "plan-markdown-save",
        title: "Markdown save",
        defaultOpen: true,
        actions: [
          {
            id: "plan-save-markdown",
            label: "Save to Markdown",
            onClick: () => undefined,
            disabled: true,
            disabledReason,
          },
        ],
      },
    ],
  }), [disabledReason, isLocked, toggleLock]);

  useEffect(() => {
    onEditorToolsChange?.(toAppChromeToolsGeneration(toolbarModel, canvasWorkTarget));
  }, [canvasWorkTarget, onEditorToolsChange, toolbarModel]);

  const editorThemeClass = `md-theme-${theme.themeId ?? "mireward-runbook"}`;
  const body =
    loadErrorMessage != null ? (
      <p role="alert" data-testid="plan-canvas-authoring-error">
        {loadErrorMessage}
      </p>
    ) : (
      <p data-testid="plan-canvas-authoring-loading">Loading plan document…</p>
    );

  return (
    <section className="plan-surface-canvas" aria-label="Plan canvas">
      <div
        className={`tiptap-spike-editor md-content ${editorThemeClass}`}
        data-md-theme={theme.themeId}
      >
        {body}
      </div>
      <p className="plan-surface-kicker" data-testid="plan-canvas-title">
        {sessionDescriptor.planningDocument.title}
      </p>
    </section>
  );
}
