import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type MouseEventHandler,
  type ReactNode,
  type Ref,
} from "react";
import type { Content, Editor, JSONContent } from "@tiptap/core";
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
import { tiptapJsonToSemanticMarkdown } from "../../tiptap/markdown/calloutMarkdown";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
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
import { useSelectedWorld } from "../../selectedWorld/SelectedWorldContext";
import {
  applyPlanEditProposal,
  capturePlanEditTarget,
  type PlanEditBridge,
  type PlanEditEditorState,
} from "../agentEdit/planAgentEditProposal";
import type { PlanDocumentDescriptor, PlanSessionDescriptor, SurfaceThemeConfig } from "../types";
import "../../tiptap/prepMarkdownThemes.css";
import "../../tiptap/tiptapSpike.css";
import "../../graphReference/graphReference.css";
import "../planSurface.css";

const TBD_PLAN_PATH = "TBD durable planning path";

/**
 * Shared visible Plan canvas frame for editors with a different persistence
 * owner. This keeps the World-owned writer independent without forking the
 * established canvas boundary and Markdown theme composition.
 */
export function PlanSurfaceCanvasFrame({
  identityLabel,
  themeId,
  className,
  testId,
  editorRef,
  onEditorClick,
  beforeEditor,
  afterEditor,
  children,
}: {
  identityLabel: string;
  themeId: string;
  className?: string;
  testId?: string;
  editorRef?: Ref<HTMLDivElement>;
  onEditorClick?: MouseEventHandler<HTMLDivElement>;
  beforeEditor?: ReactNode;
  afterEditor?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section
      className={`plan-surface-canvas${className ? ` ${className}` : ""}`}
      aria-label="Plan content"
      data-testid={testId ?? "plan-surface-canvas-frame"}
    >
      <p className="plan-surface-kicker" data-testid="plan-authoring-identity">
        {identityLabel}
      </p>
      {beforeEditor}
      <div
        ref={editorRef}
        className={`tiptap-spike-editor md-content md-theme-${themeId}`}
        data-md-theme={themeId}
        onClick={onEditorClick}
      >
        {children}
      </div>
      {afterEditor}
    </section>
  );
}

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
  onAgentEditBridgeChange?: (bridge: PlanEditBridge | null) => void;
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
  onAgentEditBridgeChange,
  shellState,
}: PlanSurfaceCanvasProps) {
  const canvasWorkTarget = useMemo(() => planShellWorkObject(shellState), [shellState]);
  const planningDocument = sessionDescriptor.planningDocument;
  const documentKind = planningDocument.kind as WorkspaceDocumentLocalKind;
  const authoringSurface: WorkspaceDocumentLocalSurface =
    documentKind === "runbook" ? "runbook" : "plan";
  const { isLocked, canEdit } = useEditCapability();
  const selectedWorld = useSelectedWorld();
  const { openGraphReference } = useProjection();
  const {
    resolvePlanReference,
    projection,
    projectionState,
  } = usePlanGraphReferenceResolver();
  const editorShellRef = useRef<HTMLDivElement | null>(null);

  const emptyMarkdownFallback = useMemo(
    () => documentKind === "plan"
      ? markdownToTiptapDoc("").doc
      : createStarterContentForPlanDocument(sessionDescriptor),
    [
      documentKind,
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

  const replaceBlankPlanContent = useCallback((target: Editor, content: JSONContent) => {
    target.commands.setContent(content, false);
    authoring.handleEditorUpdate(target.getJSON(), target, { programmatic: false });
    target.commands.focus("end");
  }, [authoring.handleEditorUpdate]);

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

  const agentEditState = useMemo<PlanEditEditorState>(() => ({
    editor,
    documentId: planningDocument.documentId,
    worldId: selectedWorld.kind === "managed" ? selectedWorld.worldId : null,
    session: sessionDescriptor.liveSession,
    baseRevision: authoring.snapshot?.loaded_revision ?? null,
    baseContentSha256: authoring.snapshot?.content_sha256 ?? null,
    sourceMarkdown: authoring.snapshot?.markdown ?? "",
    canEdit: canEdit && isEditorInteractive(authoring.phase)
      && !authoring.exportedMarkdownAuthoritative,
  }), [
    editor,
    planningDocument.documentId,
    selectedWorld,
    sessionDescriptor.liveSession,
    authoring.snapshot,
    authoring.phase,
    authoring.exportedMarkdownAuthoritative,
    canEdit,
  ]);

  const committedAgentEditState = useRef(agentEditState);
  useLayoutEffect(() => {
    committedAgentEditState.current = agentEditState;
    return () => {
      committedAgentEditState.current = { ...agentEditState, editor: null, canEdit: false };
    };
  }, [agentEditState]);

  const agentEditBridge = useMemo<PlanEditBridge>(() => ({
    capture: () => capturePlanEditTarget(agentEditState),
    apply: (captured, admitted) => applyPlanEditProposal({
      captured,
      admitted,
      current: agentEditState,
      getCurrent: () => committedAgentEditState.current,
    }),
  }), [agentEditState]);

  useEffect(() => {
    onAgentEditBridgeChange?.(agentEditBridge);
    return () => onAgentEditBridgeChange?.(null);
  }, [agentEditBridge, onAgentEditBridgeChange]);

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
    worldGraphObjectsPanel,
  ]);

  useEffect(() => {
    onEditorToolsChange?.(toAppChromeToolsGeneration(toolbarModel, canvasWorkTarget));
  }, [canvasWorkTarget, onEditorToolsChange, toolbarModel]);

  const showSavePanel = Boolean(
    authoring.lastCommitReceipt
    || (authoring.phase === "save_error" && authoring.error)
    || (authoring.phase === "committed_verification_pending" && authoring.error),
  );
  const showBlankPlanWelcome = documentKind === "plan"
    && authoring.snapshot != null
    && !authoring.exportedMarkdownAuthoritative
    && tiptapJsonToSemanticMarkdown(authoring.editorContent).trim().length === 0;

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
            <>
              {showBlankPlanWelcome ? (
                <PlanBlankPageWelcome
                  onStartWriting={() => ed.commands.focus("end")}
                  onUseOutline={() => replaceBlankPlanContent(ed, createStarterContentForPlanDocument(sessionDescriptor))}
                  onStartWithPrompt={(heading) => replaceBlankPlanContent(ed, createPlanPromptContent(heading))}
                  disabled={!canEdit}
                />
              ) : null}
              <EditorContent editor={ed} />
            </>
          </GraphNodeChipRuntimeProvider>
        )}
      </MarkdownEditorCore>
    );
  })();

  return (
    <PlanSurfaceCanvasFrame
      identityLabel={authoringIdentityLabel(planningDocument)}
      themeId={theme.themeId ?? "mireward-runbook"}
      editorRef={editorShellRef}
      onEditorClick={(event) => {
        void handleChipActivate(event.target);
      }}
      afterEditor={showSavePanel && (
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
    >
      {editorBody}
    </PlanSurfaceCanvasFrame>
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
  const { canEdit } = useEditCapability();
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
    saveActionDisabledReason,
  ]);

  const editorToolsGeneration = useMemo(
    () => toAppChromeToolsGeneration(toolbarModel, canvasWorkTarget),
    [canvasWorkTarget, toolbarModel],
  );

  useEffect(() => {
    onEditorToolsChange?.(editorToolsGeneration);
  }, [editorToolsGeneration, onEditorToolsChange]);

  return (
    <PlanSurfaceCanvasFrame
      identityLabel={authoringIdentityLabel(sessionDescriptor.planningDocument)}
      themeId={theme.themeId ?? "mireward-runbook"}
      testId="plan-blank-canvas"
      editorRef={editorShellRef}
      beforeEditor={inventoryUnavailable ? (
        <p className="plan-surface-list-warning" role="alert" data-testid="plan-selector-list-error">
          Active Plan inventory is unavailable; target session cannot be chosen safely.
        </p>
      ) : null}
      afterEditor={blankAuthoring.promotionError ? (
        <p className="plan-markdown-save-error" role="alert" data-testid="plan-markdown-save-error">
          {blankAuthoring.promotionError}
        </p>
      ) : null}
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
          {(ed) => (
            <>
              {blankAuthoring.isEmpty ? (
                <PlanBlankPageWelcome
                  onStartWriting={blankAuthoring.focusEditor}
                  onUseOutline={blankAuthoring.startWithSessionPrepTemplate}
                  onStartWithPrompt={blankAuthoring.startWithPrompt}
                  disabled={!canEdit || blankAuthoring.saveBusy}
                />
              ) : null}
              <EditorContent editor={ed} />
            </>
          )}
      </MarkdownEditorCore>
    </PlanSurfaceCanvasFrame>
  );
}

export function PlanBlankPageWelcome({
  onStartWriting,
  onUseOutline,
  onStartWithPrompt,
  disabled,
}: {
  onStartWriting: () => void;
  onUseOutline: () => void;
  onStartWithPrompt: (heading: string) => void;
  disabled: boolean;
}) {
  return (
    <section className="plan-blank-welcome" aria-labelledby="plan-blank-welcome-title" data-testid="plan-blank-welcome">
      <div className="plan-blank-welcome__copy">
        <p className="plan-blank-welcome__eyebrow">
          <span aria-hidden="true">✦</span> Your next session starts here
        </p>
        <h2 id="plan-blank-welcome-title">Give the table a reason to lean in.</h2>
        <p className="plan-blank-welcome__intro">
          Start with one bright idea. The scenes, choices, and surprises can grow from there.
        </p>
        <div className="plan-blank-welcome__actions">
          <button type="button" className="plan-blank-welcome__primary" onClick={onStartWriting} disabled={disabled}>
            Start writing
          </button>
          <button type="button" className="plan-blank-welcome__outline" onClick={onUseOutline} disabled={disabled}>
            Use session-prep outline
          </button>
        </div>
        <div className="plan-blank-welcome__sparks" aria-label="Optional starting points">
          <span>Need a first spark?</span>
          <button type="button" onClick={() => onStartWithPrompt("Session intent")} disabled={disabled}>
            Set an intention
          </button>
          <button type="button" onClick={() => onStartWithPrompt("Opening scene")} disabled={disabled}>
            Open on a scene
          </button>
          <button type="button" onClick={() => onStartWithPrompt("Loose threads")} disabled={disabled}>
            Follow a loose thread
          </button>
        </div>
      </div>
      <div className="plan-blank-welcome__art" aria-hidden="true">
        <svg viewBox="0 0 300 220" role="presentation">
          <path className="plan-blank-welcome__map-edge" d="M36 44c24-15 52-17 81-6 18 7 37 7 59-1 32-12 62-7 89 9v130c-27-16-57-20-89-8-22 8-41 8-59 1-29-11-57-9-81 6z" />
          <path className="plan-blank-welcome__map-line" d="M51 155c37-26 51-59 86-55 27 3 34 25 60 18 16-4 31-22 58-45" />
          <path className="plan-blank-welcome__map-line plan-blank-welcome__map-line--soft" d="M62 73c20 12 35 11 49 0m72 84c16-9 30-10 47-3" />
          <circle className="plan-blank-welcome__map-pin" cx="198" cy="118" r="8" />
          <circle className="plan-blank-welcome__map-pin-halo" cx="198" cy="118" r="16" />
          <path className="plan-blank-welcome__compass" d="m240 51 6 17 17 6-17 6-6 17-6-17-17-6 17-6z" />
          <path className="plan-blank-welcome__spark" d="m87 42 3 8 8 3-8 3-3 8-3-8-8-3 8-3z" />
          <path className="plan-blank-welcome__map-dash" d="M50 182h41m25 0h24m44 0h37" />
        </svg>
        <p><strong>Leave room for wonder.</strong><br />A plan is a compass, not a script.</p>
      </div>
    </section>
  );
}

function createPlanPromptContent(heading: string): JSONContent {
  return {
    type: "doc",
    content: [
      { type: "heading", attrs: { level: 2 }, content: [{ type: "text", text: heading }] },
      { type: "paragraph" },
    ],
  };
}

function PlanShellStatusSurfaceCanvas({
  sessionDescriptor,
  theme,
  shellState,
  loadErrorMessage = null,
  onEditorToolsChange,
}: PlanSurfaceCanvasProps) {
  const canvasWorkTarget = useMemo(() => planShellWorkObject(shellState), [shellState]);
  const disabledReason =
    loadErrorMessage != null
      ? "Document failed to load; retry or choose another document."
      : "Document is still loading.";

  const toolbarModel = useMemo<MarkdownEditorToolbarModel>(() => ({
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
  }), [disabledReason]);

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
    <section className="plan-surface-canvas" aria-label="Plan content">
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
