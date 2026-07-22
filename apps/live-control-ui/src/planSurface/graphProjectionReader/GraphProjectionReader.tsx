import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Content } from "@tiptap/core";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

import type { GraphProjectionNodeView, RecapProjectionSourceSpan } from "../../api/types";
import {
  GraphNodeChipRuntimeProvider,
  type GraphNodeChipDeltaPresentation,
} from "../../graphReference";
import { GraphNodeReferenceNode } from "../../tiptap/extensions/GraphNodeReferenceNode";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import {
  graphAuthoringSelectionsEqual,
  type GraphAuthoringAction,
  type GraphAuthoringContext,
  type GraphAuthoringSelection,
} from "../graphReviewWorkbench/graphAuthoringSelection";
import { useGraphAuthoringSelection } from "../graphReviewWorkbench/useGraphAuthoringSelection";
import { stripLeadingYamlFrontmatter } from "./projectionMarkdownPreprocessing";
import { attachSourceSpanDataAttributes, type SourceSpanDomOverlay } from "./sourceSpanHighlight";

export type { GraphAuthoringAction, GraphAuthoringSelection };

export interface GraphProjectionReaderProps {
  markdown: string;
  nodeViews: Record<string, GraphProjectionNodeView>;
  sourceSpans: RecapProjectionSourceSpan[];
  mentionsCount?: number;
  graphId?: string | null;
  showGraphId?: boolean;
  title?: string;
  subtitle?: string;
  sourceNote?: string;
  className?: string;
  documentLabel?: string;
  documentScroll?: "contained" | "page";
  resetKey?: string | null;
  nodeDeltaPresentations?: Record<string, GraphNodeChipDeltaPresentation>;
  sourceSpanDeltaOverlays?: Record<string, SourceSpanDomOverlay>;
  selectedSourceSpanId?: string | null;
  onActiveNodeChange?: (nodeId: string | null) => void;
  /** Required for chip clicks — opens the shared Plan reference drawer host. */
  onInspectNode: (nodeId: string) => void;
  authoringEnabled?: boolean;
  authoringContext?: GraphAuthoringContext;
  onGraphAuthoringSelection?: (selection: GraphAuthoringSelection | null) => void;
  onGraphAuthoringAction?: (
    selection: GraphAuthoringSelection,
    action: GraphAuthoringAction,
  ) => void;
}

function ReadOnlyTiptapRecap({
  markdown,
  nodeViews,
  activeNodeId,
  onSelectNode,
  sourceSpans,
  selectedEvidenceSpanId,
  nodeDeltaPresentations,
  sourceSpanDeltaOverlays,
  authoringEnabled,
  authoringContext,
  onGraphAuthoringSelection,
}: {
  markdown: string;
  nodeViews: Record<string, GraphProjectionNodeView>;
  activeNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
  sourceSpans: RecapProjectionSourceSpan[];
  selectedEvidenceSpanId: string | null;
  nodeDeltaPresentations?: Record<string, GraphNodeChipDeltaPresentation>;
  sourceSpanDeltaOverlays?: Record<string, SourceSpanDomOverlay>;
  authoringEnabled?: boolean;
  authoringContext?: GraphAuthoringContext;
  onGraphAuthoringSelection?: (selection: GraphAuthoringSelection | null) => void;
}) {
  const readerRef = useRef<HTMLDivElement | null>(null);
  const projectionMarkdown = useMemo(
    () => stripLeadingYamlFrontmatter(markdown).markdown,
    [markdown],
  );
  const content = useMemo(
    () =>
      markdownToTiptapDoc(projectionMarkdown, { parseGraphNodeLinks: true })
        .doc as Content,
    [projectionMarkdown],
  );
  const editor = useEditor({
    extensions: [StarterKit, GraphNodeReferenceNode],
    content,
    editable: false,
    immediatelyRender: false,
  });

  useGraphAuthoringSelection({
    editor,
    authoringEnabled,
    authoringContext,
    onGraphAuthoringSelection,
  });

  useEffect(() => {
    editor?.commands.setContent(content, false);
  }, [content, editor]);

  const chipRuntime = useMemo(
    () => ({
      nodeViews,
      activeNodeId,
      onSelectNode,
      deltaByNodeId: nodeDeltaPresentations ?? {},
    }),
    [nodeViews, activeNodeId, onSelectNode, nodeDeltaPresentations],
  );

  useEffect(() => {
    const root = readerRef.current;
    if (!root) return;
    const highlighted = attachSourceSpanDataAttributes(root, sourceSpans, selectedEvidenceSpanId, sourceSpanDeltaOverlays ?? {});
    if (highlighted && typeof highlighted.scrollIntoView === "function") {
      highlighted.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [content, sourceSpans, selectedEvidenceSpanId, sourceSpanDeltaOverlays]);

  return (
    <GraphNodeChipRuntimeProvider value={chipRuntime}>
      <div className="union-supergraph-tiptap-reader" ref={readerRef}>
        <EditorContent editor={editor} />
      </div>
    </GraphNodeChipRuntimeProvider>
  );
}

export function GraphProjectionReader({
  markdown,
  nodeViews,
  sourceSpans,
  mentionsCount,
  graphId,
  showGraphId = false,
  title,
  subtitle,
  sourceNote,
  className,
  documentLabel = "Projected recap",
  documentScroll = "contained",
  resetKey,
  nodeDeltaPresentations,
  sourceSpanDeltaOverlays,
  selectedSourceSpanId,
  onActiveNodeChange,
  onInspectNode,
  authoringEnabled = false,
  authoringContext,
  onGraphAuthoringSelection,
  onGraphAuthoringAction,
}: GraphProjectionReaderProps) {
  const [activeNodeId, setActiveNodeId] = useState<string | null>(null);
  const [pendingAuthoringSelection, setPendingAuthoringSelection] = useState<GraphAuthoringSelection | null>(null);
  const pendingAuthoringSelectionRef = useRef<GraphAuthoringSelection | null>(null);

  const onGraphAuthoringSelectionRef = useRef(onGraphAuthoringSelection);
  onGraphAuthoringSelectionRef.current = onGraphAuthoringSelection;

  useEffect(() => {
    setActiveNodeId(null);
    pendingAuthoringSelectionRef.current = null;
    setPendingAuthoringSelection(null);
    onActiveNodeChange?.(null);
    onGraphAuthoringSelectionRef.current?.(null);
  }, [markdown, graphId, resetKey, onActiveNodeChange]);

  const handleSelectNode = useCallback(
    (nodeId: string) => {
      onInspectNode(nodeId);
      setActiveNodeId(nodeId);
      onActiveNodeChange?.(nodeId);
    },
    [onActiveNodeChange, onInspectNode],
  );

  const handleAuthoringSelection = useCallback((selection: GraphAuthoringSelection | null) => {
    if (graphAuthoringSelectionsEqual(pendingAuthoringSelectionRef.current, selection)) {
      return;
    }
    pendingAuthoringSelectionRef.current = selection;
    setPendingAuthoringSelection(selection);
    onGraphAuthoringSelection?.(selection);
  }, [onGraphAuthoringSelection]);

  const rootClassName = className ? `recap-reader-root ${className}` : "recap-reader-root";
  const effectiveSelectedSpanId = selectedSourceSpanId ?? null;
  const showAuthoringAction =
    authoringEnabled && pendingAuthoringSelection !== null && Boolean(onGraphAuthoringAction);

  return (
    <div className={rootClassName}>
      {title || subtitle || sourceNote || (showGraphId && graphId) ? (
        <header className="recap-reader-header">
          <div>
            {title ? <h2>{title}</h2> : null}
            {subtitle ? <p>{subtitle}</p> : null}
            {sourceNote ? <p className="union-supergraph-source-note">{sourceNote}</p> : null}
          </div>
          {showGraphId && graphId ? (
            <span className="union-supergraph-graph-id">{graphId}</span>
          ) : null}
        </header>
      ) : null}

      {typeof mentionsCount === "number" && mentionsCount > 0 ? (
        <p className="recap-reader-hint union-supergraph-mentions-hint">
          {mentionsCount} linked name{mentionsCount === 1 ? "" : "s"} in this recap.
        </p>
      ) : null}

      {showAuthoringAction ? (
        <div className="graph-authoring-selection-action-bar">
          <button
            type="button"
            className="graph-authoring-selection-action"
            data-testid="graph-authoring-action"
            onClick={() => {
              if (pendingAuthoringSelection) {
                onGraphAuthoringAction?.(pendingAuthoringSelection, "author_object");
              }
            }}
          >
            Author graph object
          </button>
        </div>
      ) : null}

      <div className="recap-reader-layout union-supergraph-layout">
        <article
          className={`recap-reader-document union-supergraph-recap-document${
            documentScroll === "page" ? " recap-reader-document--page-scroll" : ""
          }`}
          aria-label={documentLabel}
        >
          <ReadOnlyTiptapRecap
            markdown={markdown}
            nodeViews={nodeViews}
            activeNodeId={activeNodeId}
            onSelectNode={handleSelectNode}
            sourceSpans={sourceSpans}
            selectedEvidenceSpanId={effectiveSelectedSpanId}
            nodeDeltaPresentations={nodeDeltaPresentations}
            sourceSpanDeltaOverlays={sourceSpanDeltaOverlays}
            authoringEnabled={authoringEnabled}
            authoringContext={authoringContext}
            onGraphAuthoringSelection={handleAuthoringSelection}
          />
        </article>
      </div>
    </div>
  );
}
