import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Editor } from "@tiptap/core";
import { EditorContent } from "@tiptap/react";
import type { Content } from "@tiptap/react";

import type { AppChromeTools } from "../chrome/AppChrome";
import type { GraphProjectionNodeView } from "../api/types";
import { buildGraphObjectCardFromNodeView } from "../graphObjectCard";
import {
  GraphNodeChipRuntimeProvider,
  type GraphNodeChipRuntimeValue,
  GraphReferenceSearch,
  insertMarkdownReference,
  useOpenGraphReference,
} from "../graphReference";
import { MarkdownEditorCore } from "../tiptap/MarkdownEditorCore";
import {
  toAppChromeTools,
  type MarkdownEditorToolbarModel,
} from "../tiptap/MarkdownEditorToolbar";
import {
  GRAPH_NODE_REF_TYPE,
  type RunbookReferenceAttrs,
} from "../tiptap/references/runbookReferences";
import { useMarkdownCanvasSession } from "../markdownCanvas/MarkdownCanvasSession";
import type { MarkdownCanvasSlots } from "../markdownCanvas/MarkdownCanvas";
import {
  BUILD_FIND_EXISTING_EVENT,
  type BuildFindExistingDetail,
} from "./buildFindExisting";
import { usePlanGraphReferenceResolver } from "../planSurface/reference/usePlanGraphReferenceResolver";
import { readReferenceFromElement } from "../planSurface/reference/referenceResolver";
import { adaptWorldGraphNodeForPlanCard } from "../planSurface/reference/worldGraphProjectionAdapter";

function buildEditorInteractive(sessionPhase: string): boolean {
  return sessionPhase !== "loading"
    && sessionPhase !== "unloaded"
    && sessionPhase !== "load_error"
    && sessionPhase !== "conflict";
}

export interface BuildGraphReferenceShellProps {
  slots: MarkdownCanvasSlots;
  onEditorToolsChange?: (tools: AppChromeTools | null) => void;
}

export function BuildGraphReferenceShell({
  slots,
  onEditorToolsChange,
}: BuildGraphReferenceShellProps) {
  const session = useMarkdownCanvasSession();
  const openGraphReference = useOpenGraphReference();
  const {
    resolvePlanReference,
    projection,
    projectionState,
    projectionError,
  } = usePlanGraphReferenceResolver();
  const editorShellRef = useRef<HTMLDivElement | null>(null);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [graphRefSearchQuery, setGraphRefSearchQuery] = useState("");

  const editorInteractive = buildEditorInteractive(session.phase);

  const handleEditorChange = useCallback(
    (nextEditor: Editor | null) => {
      session.setEditor(nextEditor);
      setEditor(nextEditor);
    },
    [session.setEditor],
  );

  const handleInsertMarkdownReference = useCallback(
    (attrs: RunbookReferenceAttrs) => {
      insertMarkdownReference(editor, attrs);
    },
    [editor],
  );

  const projectionNodes = useMemo(
    () => projection?.nodes.map((node) => adaptWorldGraphNodeForPlanCard(node)) ?? [],
    [projection],
  );

  const handleViewGraphNode = useCallback(
    (node: GraphProjectionNodeView) => {
      openGraphReference(
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
    [openGraphReference, projectionState],
  );

  const graphRefSearchPanel = useMemo(
    () => (
      <GraphReferenceSearch
        nodes={projectionNodes}
        projectionState={projectionState}
        projectionError={projectionError}
        insertDisabled={!editor || !editorInteractive}
        initialQuery={graphRefSearchQuery}
        onInsert={handleInsertMarkdownReference}
        onView={handleViewGraphNode}
      />
    ),
    [
      editor,
      editorInteractive,
      graphRefSearchQuery,
      handleInsertMarkdownReference,
      handleViewGraphNode,
      projectionError,
      projectionNodes,
      projectionState,
    ],
  );

  useEffect(() => {
    function onFindExisting(event: Event) {
      const detail = (event as CustomEvent<BuildFindExistingDetail>).detail;
      if (!detail?.query?.trim()) return;
      setGraphRefSearchQuery(detail.query.trim());
    }
    window.addEventListener(BUILD_FIND_EXISTING_EVENT, onFindExisting);
    return () => window.removeEventListener(BUILD_FIND_EXISTING_EVENT, onFindExisting);
  }, []);

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
      openGraphReference(resolution, projectionState, ref);
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
    };
  }, [openGraphNodeFromChip, projection?.nodes]);

  const handleChipActivate = useCallback(
    async (target: EventTarget | null) => {
      if (!(target instanceof HTMLElement) || !editorShellRef.current?.contains(target)) return;
      const chip = target.closest(".md-ref-chip");
      if (!(chip instanceof HTMLElement)) return;
      const ref = readReferenceFromElement(chip);
      if (!ref) return;
      const resolution = await resolvePlanReference(ref);
      openGraphReference(resolution, projectionState, ref);
    },
    [openGraphReference, projectionState, resolvePlanReference],
  );

  const toolbarModel = useMemo<MarkdownEditorToolbarModel>(
    () => ({
      sections: [
        {
          id: "build-world-graph-objects",
          title: "World Graph objects",
          defaultOpen: true,
          actions: [],
          panel: graphRefSearchPanel,
        },
      ],
    }),
    [graphRefSearchPanel],
  );

  useEffect(() => {
    onEditorToolsChange?.(toAppChromeTools(toolbarModel));
    return () => onEditorToolsChange?.(null);
  }, [onEditorToolsChange, toolbarModel]);

  const {
    title,
    statusExtra,
    hideDefaultStatus = false,
    actions,
    tools,
    loadingMessage = "Loading document…",
    errorHeading = "Document",
    conflictHeading = "Document",
    className = "markdown-canvas",
    editorClassName = "markdown-canvas-editor",
    dataTestId = "markdown-canvas",
    editorDataTestId = "markdown-canvas-editor",
    loadingTestId,
    errorTestId,
    authorityErrorTestId,
    conflictTestId,
    statusTestId,
    saveErrorTestId,
    editorMdTheme,
  } = slots;

  if (session.phase === "loading" || session.phase === "unloaded") {
    return (
      <main className="app-status" data-testid={loadingTestId ?? `${dataTestId}-loading`}>
        <p>{loadingMessage}</p>
      </main>
    );
  }

  if (session.phase === "load_error") {
    return (
      <main className="app-status app-error" data-testid={errorTestId ?? `${dataTestId}-error`}>
        <h1>{errorHeading}</h1>
        <p data-testid={authorityErrorTestId ?? `${dataTestId}-authority-error`}>
          {session.error ?? "Unable to load document."}
        </p>
      </main>
    );
  }

  if (session.phase === "conflict") {
    return (
      <main className="app-status app-error" data-testid={conflictTestId ?? `${dataTestId}-conflict`}>
        <h1>{conflictHeading}</h1>
        <p>{session.statusLabel}</p>
        <button type="button" onClick={() => void session.reloadFromSnapshot()}>
          Reload from server
        </button>
        <button type="button" onClick={() => void session.discardLocalDraft()}>
          Discard local draft
        </button>
      </main>
    );
  }

  return (
    <main className={className} data-testid={dataTestId}>
      {tools}
      <header className="markdown-canvas-header">
        <h1>{title ?? session.record?.title ?? errorHeading}</h1>
        {hideDefaultStatus ? null : (
          <p data-testid={statusTestId ?? `${dataTestId}-status`}>{session.statusLabel}</p>
        )}
        {session.error ? (
          <p role="alert" data-testid={saveErrorTestId ?? `${dataTestId}-save-error`}>
            {session.error}
          </p>
        ) : null}
        {statusExtra}
      </header>

      <div
        ref={editorShellRef}
        className={editorClassName}
        {...(editorMdTheme ? { "data-md-theme": editorMdTheme } : {})}
        onClick={(event) => {
          void handleChipActivate(event.target);
        }}
      >
        <MarkdownEditorCore
          documentKey={session.documentKey}
          content={session.editorContent as Content}
          onEditorChange={handleEditorChange}
          onUpdate={session.handleEditorUpdate}
          dataTestId={editorDataTestId}
        >
          {(ed) => (
            <GraphNodeChipRuntimeProvider value={chipRuntime}>
              <EditorContent editor={ed} />
            </GraphNodeChipRuntimeProvider>
          )}
        </MarkdownEditorCore>
      </div>

      {actions ? <footer className="markdown-canvas-actions">{actions}</footer> : null}
    </main>
  );
}
