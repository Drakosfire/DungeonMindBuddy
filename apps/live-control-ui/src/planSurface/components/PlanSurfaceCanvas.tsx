import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Content, Editor } from "@tiptap/core";
import { EditorContent } from "@tiptap/react";

import type { AppChromeToolsGeneration } from "../../chrome/AppChrome";
import {
  GraphNodeChipRuntimeProvider,
  GraphReferenceSearch,
  insertMarkdownReference,
  referenceFromGraphNode,
  type GraphNodeChipRuntimeValue,
  type GraphReferenceProjectionState,
  type GraphReferenceSearchItem,
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
import type { GraphProjectionNodeView, WorldGraphProjection } from "../../api/types";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import { extractExactGraphReferenceScope } from "../../graphReference/resolveGraphReference";
import { useProjection } from "../projection/projectionContext";
import { readReferenceFromElement } from "../reference/referenceResolver";
import { usePlanGraphReferenceResolver } from "../reference/usePlanGraphReferenceResolver";
import { adaptWorldGraphNodeForPlanCard } from "../reference/worldGraphProjectionAdapter";
import { useOptionalWorldGraphLensProjection } from "../../graphLens/useWorldGraphLensProjection";
import { formatReviewCampaignLabel } from "../sessionCampaignContext";
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

function nodeScopeLabel(node: GraphProjectionNodeView): string {
  const scope = node.campaign_scope?.trim();
  if (!scope) return "World";
  return formatReviewCampaignLabel(scope);
}

/**
 * World Graph objects tool panel.
 *
 * Edit-toolbox panels are published through a signature dedup that cannot see
 * ReactNode content changes: the first published panel element is kept as-is.
 * This component therefore reads the shared lens projection from context at
 * render time instead of trusting projection props captured at publish time.
 * The fallback props serve hosts without the lens projection provider (tests).
 */
function PlanGraphReferenceSearchTool({
  fallbackItems,
  fallbackProjection,
  fallbackState,
  fallbackError,
  insertDisabled,
  onInsert,
}: {
  fallbackItems: readonly GraphReferenceSearchItem[];
  fallbackProjection: WorldGraphProjection | null;
  fallbackState: GraphReferenceProjectionState;
  fallbackError: string | null;
  insertDisabled: boolean;
  onInsert: (item: GraphReferenceSearchItem) => void;
}) {
  const shared = useOptionalWorldGraphLensProjection();
  const { openGraphReference } = useProjection();
  const projection = shared?.projection ?? fallbackProjection;
  const projectionState = shared?.projectionState ?? fallbackState;
  const projectionError = shared?.projectionError ?? fallbackError;

  const items = useMemo<GraphReferenceSearchItem[]>(() => {
    if (!shared) return [...fallbackItems];
    return (projection?.nodes ?? []).map((node) => {
      const nodeView = adaptWorldGraphNodeForPlanCard(node);
      return {
        nodeId: nodeView.node_id,
        label: nodeView.label,
        kind: nodeView.kind,
        role: nodeView.role,
        summary: nodeView.summary ?? null,
        aliases: nodeView.aliases ?? [],
        scopeLabel: nodeScopeLabel(nodeView),
        reference: referenceFromGraphNode(nodeView),
        nodeView,
      };
    });
  }, [shared, projection, fallbackItems]);

  const handleView = useCallback(
    (item: GraphReferenceSearchItem) => {
      const graphScope = extractExactGraphReferenceScope(projection);
      if (!graphScope) {
        openGraphReference({
          resolution: {
            kind: "error",
            locator: `dmb-node:${item.nodeId}`,
            reference: item.reference,
            projectionState,
            message:
              "World Graph projection snapshot lacks exact world, campaign, or revision scope; graph search open blocked.",
          },
          projectionState,
        });
        return;
      }

      openGraphReference({
        resolution: {
          kind: "resolved_graph",
          locator: `dmb-node:${item.nodeId}`,
          reference: item.reference,
          graphObject: buildGraphObjectCardFromNodeView(item.nodeView),
          graphNodeId: item.nodeId,
          graphScope,
          projectionState,
          message: `Resolved graph node ${item.label}.`,
        },
        projectionState,
      });
    },
    [openGraphReference, projection, projectionState],
  );

  return (
    <GraphReferenceSearch
      items={items}
      projectionState={projectionState}
      projectionError={projectionError}
      insertDisabled={insertDisabled}
      onInsert={onInsert}
      onView={handleView}
    />
  );
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
    projectionError,
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

  const insertRunbookReference = useCallback(
    (attrs: RunbookReferenceAttrs) => {
      insertMarkdownReference(editor, attrs);
    },
    [editor],
  );

  const projectionNodes = useMemo(
    () => projection?.nodes.map((node) => adaptWorldGraphNodeForPlanCard(node)) ?? [],
    [projection],
  );

  const graphReferenceSearchItems = useMemo<GraphReferenceSearchItem[]>(
    () =>
      projectionNodes.map((node) => ({
        nodeId: node.node_id,
        label: node.label,
        kind: node.kind,
        role: node.role,
        summary: node.summary ?? null,
        aliases: node.aliases ?? [],
        scopeLabel: nodeScopeLabel(node),
        reference: referenceFromGraphNode(node),
        nodeView: node,
      })),
    [projectionNodes],
  );

  const graphRefSearchPanel = useMemo(
    () => (
      <PlanGraphReferenceSearchTool
        fallbackItems={graphReferenceSearchItems}
        fallbackProjection={projection}
        fallbackState={projectionState}
        fallbackError={projectionError}
        insertDisabled={!editor || isLocked || !editorInteractive}
        onInsert={(item) => insertRunbookReference(item.reference)}
      />
    ),
    [
      editor,
      editorInteractive,
      graphReferenceSearchItems,
      insertRunbookReference,
      isLocked,
      projection,
      projectionError,
      projectionState,
    ],
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
        panel: graphRefSearchPanel,
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
    graphRefSearchPanel,
    insertCallout,
    insertDecisionConsequence,
    isLocked,
    removeActiveBlock,
    toggleLock,
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
