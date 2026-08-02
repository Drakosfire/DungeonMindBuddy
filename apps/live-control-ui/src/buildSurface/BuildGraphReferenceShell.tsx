import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Editor } from "@tiptap/core";
import { EditorContent } from "@tiptap/react";
import type { Content } from "@tiptap/react";

import type { AppChromeTools } from "../chrome/AppChrome";
import type { GraphProjectionNodeView } from "../api/types";
import { buildGraphObjectCardFromNodeView } from "../graphObjectCard";
import {
  GraphNodeChipRuntimeProvider,
  GraphReferenceSearch,
  insertMarkdownReference,
  referenceFromGraphNode,
  type GraphNodeChipRuntimeValue,
  type GraphReferenceSearchItem,
} from "../graphReference";
import { defaultMarkdownDocumentAdapter } from "../tiptap/MarkdownDocumentAdapter";
import { MarkdownEditorCore } from "../tiptap/MarkdownEditorCore";
import {
  toAppChromeTools,
  type MarkdownEditorToolbarModel,
} from "../tiptap/MarkdownEditorToolbar";
import {
  CALLOUT_KINDS,
  defaultCalloutLabel,
  type CalloutKind,
} from "../tiptap/markdown/calloutMarkdown";
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
import { useProjection } from "../planSurface/projection/projectionContext";
import { usePlanGraphReferenceResolver } from "../planSurface/reference/usePlanGraphReferenceResolver";
import { readReferenceFromElement } from "../planSurface/reference/referenceResolver";
import { adaptWorldGraphNodeForPlanCard } from "../planSurface/reference/worldGraphProjectionAdapter";
import { formatReviewCampaignLabel } from "../planSurface/sessionCampaignContext";

function buildEditorInteractive(sessionPhase: string): boolean {
  return sessionPhase !== "loading"
    && sessionPhase !== "unloaded"
    && sessionPhase !== "load_error"
    && sessionPhase !== "conflict";
}

function nodeScopeLabel(node: GraphProjectionNodeView): string {
  const scope = node.campaign_scope?.trim();
  if (!scope) return "world";
  return formatReviewCampaignLabel(scope);
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
  const { openGraphReference } = useProjection();
  const {
    resolvePlanReference,
    projection,
    projectionState,
    projectionError,
  } = usePlanGraphReferenceResolver();
  const editorShellRef = useRef<HTMLDivElement | null>(null);
  const editorRef = useRef<Editor | null>(null);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [isLocked, setIsLocked] = useState(true);
  const [graphRefSearchQuery, setGraphRefSearchQuery] = useState("");
  const saveMarkdownRef = useRef(session.saveMarkdown);
  saveMarkdownRef.current = session.saveMarkdown;
  const saveDisabled = session.saveDisabled;

  const toggleLock = useCallback(() => {
    setIsLocked((current) => !current);
  }, []);

  const editorInteractive = buildEditorInteractive(session.phase);
  const canEdit = !isLocked && editorInteractive;

  const handleEditorChange = useCallback(
    (nextEditor: Editor | null) => {
      editorRef.current = nextEditor;
      session.setEditor(nextEditor);
      setEditor(nextEditor);
    },
    [session.setEditor],
  );

  const handleInsertMarkdownReference = useCallback(
    (attrs: RunbookReferenceAttrs) => {
      insertMarkdownReference(editorRef.current, attrs);
    },
    [],
  );

  const insertCallout = useCallback(
    (kind: CalloutKind) => {
      editor?.chain().focus().insertCallout({ kind }).run();
    },
    [editor],
  );

  const removeActiveBlock = useCallback(() => {
    editor?.chain().focus().deleteActiveBlock().run();
  }, [editor]);

  const copyMarkdown = useCallback(async () => {
    if (!editor || !navigator.clipboard?.writeText) return;
    const markdown = defaultMarkdownDocumentAdapter.exportMarkdown(editor.getJSON());
    await navigator.clipboard.writeText(markdown);
  }, [editor]);

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

  const handleViewGraphReference = useCallback(
    (item: GraphReferenceSearchItem) => {
      openGraphReference({
        resolution: {
          kind: "resolved_graph",
          locator: `dmb-node:${item.nodeId}`,
          reference: item.reference,
          graphObject: buildGraphObjectCardFromNodeView(item.nodeView),
          graphNodeId: item.nodeId,
          projectionState,
          message: `Resolved graph node ${item.label}.`,
        },
        projectionState,
      });
    },
    [openGraphReference, projectionState],
  );

  const editorReady = Boolean(editor);

  const graphRefSearchPanel = useMemo(
    () => (
      <GraphReferenceSearch
        items={graphReferenceSearchItems}
        projectionState={projectionState}
        projectionError={projectionError}
        insertDisabled={!editorReady || isLocked || !editorInteractive}
        initialQuery={graphRefSearchQuery}
        onInsert={handleInsertMarkdownReference}
        onView={handleViewGraphReference}
      />
    ),
    [
      editorReady,
      editorInteractive,
      graphRefSearchQuery,
      graphReferenceSearchItems,
      handleInsertMarkdownReference,
      handleViewGraphReference,
      isLocked,
      projectionError,
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
      openGraphReference({
        reference: ref,
        resolution,
        projectionState,
        glanceOnly: true,
      });
    },
    [openGraphReference, projection, projectionState, resolvePlanReference],
  );

  const openGraphNodeFromChipRef = useRef(openGraphNodeFromChip);
  openGraphNodeFromChipRef.current = openGraphNodeFromChip;

  const chipRuntime = useMemo<GraphNodeChipRuntimeValue>(() => {
    const nodeViews: Record<string, GraphProjectionNodeView> = {};
    for (const node of projection?.nodes ?? []) {
      nodeViews[node.nodeId] = adaptWorldGraphNodeForPlanCard(node);
    }
    return {
      nodeViews,
      activeNodeId: null,
      onSelectNode: (nodeId) => {
        void openGraphNodeFromChipRef.current(nodeId);
      },
    };
  }, [projection?.nodes]);

  const handleChipActivate = useCallback(
    async (target: EventTarget | null) => {
      if (!(target instanceof HTMLElement) || !editorShellRef.current?.contains(target)) return;
      const chip = target.closest(".md-ref-chip");
      if (!(chip instanceof HTMLElement)) return;
      const ref = readReferenceFromElement(chip);
      if (!ref) return;
      const resolution = await resolvePlanReference(ref);
      openGraphReference({
        reference: ref,
        resolution,
        projectionState,
        glanceOnly: true,
      });
    },
    [openGraphReference, projectionState, resolvePlanReference],
  );

  const toolbarModel = useMemo<MarkdownEditorToolbarModel>(
    () => ({
      pinnedActions: [
        {
          id: "build-canvas-edit-lock",
          eyebrow: isLocked ? "Editing locked" : "Editing unlocked",
          label: isLocked ? "Unlock editing" : "Lock editing",
          onClick: toggleLock,
          pressed: isLocked,
        },
      ],
      sections: [
        {
          id: "build-world-graph-objects",
          title: "World Graph objects",
          defaultOpen: true,
          actions: [],
          panel: graphRefSearchPanel,
        },
        {
          id: "build-insert-blocks",
          title: "Insert blocks",
          defaultOpen: true,
          actions: CALLOUT_KINDS.map((kind) => ({
            id: `build-insert-${kind}`,
            eyebrow: "Insert",
            label: defaultCalloutLabel(kind),
            onClick: () => insertCallout(kind),
            disabled: !editor || isLocked || !editorInteractive,
          })),
        },
        {
          id: "build-edit-blocks",
          title: "Edit blocks",
          defaultOpen: true,
          actions: [
            {
              id: "build-remove-block",
              eyebrow: "Remove",
              label: "Remove block",
              onClick: removeActiveBlock,
              disabled: !editor || isLocked || !editorInteractive,
            },
          ],
        },
        {
          id: "build-markdown-export",
          title: "Markdown export",
          defaultOpen: true,
          actions: [
            {
              id: "build-copy-markdown",
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
          id: "build-markdown-save",
          title: "Markdown save",
          defaultOpen: true,
          actions: [
            {
              id: "build-save-markdown",
              label: "Save to Markdown",
              onClick: () => {
                void saveMarkdownRef.current();
              },
              disabled: saveDisabled,
            },
          ],
        },
      ],
    }),
    [
      copyMarkdown,
      editor,
      editorInteractive,
      graphRefSearchPanel,
      insertCallout,
      isLocked,
      removeActiveBlock,
      saveDisabled,
      toggleLock,
    ],
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
          editable={canEdit}
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
