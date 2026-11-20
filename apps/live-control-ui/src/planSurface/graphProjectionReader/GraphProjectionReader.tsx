import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Content } from "@tiptap/core";
import { EditorContent, useEditor } from "@tiptap/react";

import type { GraphProjectionNodeView, RecapProjectionSourceSpan } from "../../api/types";
import {
  GraphNodeChipRuntimeProvider,
  type GraphNodeChipDeltaPresentation,
} from "../../graphReference";
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from "../../tiptap/MarkdownEditorCore";
import { analyzeMarkdownBody } from "../../tiptap/markdown/markdownAdmission";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import { GraphNodeExplorer } from "../graphPreview/GraphNodePresentation";
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
  /** Preserve source whose normalization is already owned by its producer. */
  frontmatterPolicy?: "strip-leading" | "preserve";
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
  onInspectNode?: (nodeId: string) => void;
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
  frontmatterPolicy,
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
  frontmatterPolicy: "strip-leading" | "preserve";
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
    () => frontmatterPolicy === "preserve" ? markdown : stripLeadingYamlFrontmatter(markdown).markdown,
    [markdown, frontmatterPolicy],
  );
  const imported = useMemo(
    () => {
      if (frontmatterPolicy === "preserve") {
        // The orchestration helper strips YAML too. Use the same admission/parser
        // boundary directly when the producer already owns normalization.
        const result = analyzeMarkdownBody(projectionMarkdown.replace(/\r\n?/g, "\n"), { parseGraphNodeLinks: true });
        return { doc: { type: "doc", content: result.content }, diagnostics: result.diagnostics };
      }
      return markdownToTiptapDoc(projectionMarkdown, { parseGraphNodeLinks: true });
    },
    [projectionMarkdown, frontmatterPolicy],
  );
  const content = imported.doc as Content;
  const editor = useEditor({
    extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,
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
    let didScroll = false;
    const attach = () => {
      const highlighted = attachSourceSpanDataAttributes(root, sourceSpans, selectedEvidenceSpanId, sourceSpanDeltaOverlays ?? {});
      if (!didScroll && highlighted && typeof highlighted.scrollIntoView === "function") {
        highlighted.scrollIntoView({ block: "center", behavior: "smooth" });
        didScroll = true;
      }
    };
    // React node views mount their chip labels after the editor content effect.
    // Reattach when those children arrive so evidence can match the full prose.
    const observer = new MutationObserver(attach);
    observer.observe(root, { childList: true, subtree: true });
    attach();
    return () => observer.disconnect();
  }, [content, editor, sourceSpans, selectedEvidenceSpanId, sourceSpanDeltaOverlays]);

  return (
    <GraphNodeChipRuntimeProvider value={chipRuntime}>
      <div className="union-supergraph-tiptap-reader" ref={readerRef}>
        <EditorContent editor={editor} />
      </div>
      {imported.diagnostics.length > 0 ? (
        <details aria-label="Source formatting details">
          <summary>Source formatting</summary>
          <ul>{imported.diagnostics.map((diagnostic, index) => (
            <li key={`${diagnostic.message}:${index}`}>{diagnostic.message}</li>
          ))}</ul>
        </details>
      ) : null}
    </GraphNodeChipRuntimeProvider>
  );
}

export function GraphProjectionReader({
  markdown,
  frontmatterPolicy = "strip-leading",
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
  const [explorerTrail, setExplorerTrail] = useState<string[]>([]);
  const [pendingAuthoringSelection, setPendingAuthoringSelection] = useState<GraphAuthoringSelection | null>(null);
  const activeNodeId = explorerTrail.at(-1) ?? null;
  const activeNode = activeNodeId ? nodeViews[activeNodeId] : undefined;
  const [selectedEvidenceSpanId, setSelectedEvidenceSpanId] = useState<string | null>(null);
  const useExternalInspection = Boolean(onInspectNode);
  const pendingAuthoringSelectionRef = useRef<GraphAuthoringSelection | null>(null);

  const onGraphAuthoringSelectionRef = useRef(onGraphAuthoringSelection);
  onGraphAuthoringSelectionRef.current = onGraphAuthoringSelection;

  useEffect(() => {
    setExplorerTrail([]);
    setSelectedEvidenceSpanId(null);
    pendingAuthoringSelectionRef.current = null;
    setPendingAuthoringSelection(null);
    onActiveNodeChange?.(null);
    onGraphAuthoringSelectionRef.current?.(null);
  }, [markdown, graphId, resetKey, onActiveNodeChange]);

  const openExplorer = (nodeId: string) => {
    if (onInspectNode) {
      onInspectNode(nodeId);
      onActiveNodeChange?.(nodeId);
      return;
    }
    setExplorerTrail([nodeId]);
    onActiveNodeChange?.(nodeId);
  };

  const pushExplorer = (nodeId: string) => {
    setExplorerTrail((trail) => {
      if (trail.at(-1) === nodeId) {
        return trail;
      }
      return [...trail, nodeId];
    });
    onActiveNodeChange?.(nodeId);
  };

  const popExplorer = () => {
    setExplorerTrail((trail) => {
      if (trail.length <= 1) return trail;
      const nextTrail = trail.slice(0, -1);
      onActiveNodeChange?.(nextTrail.at(-1) ?? null);
      return nextTrail;
    });
  };

  const closeExplorer = () => {
    setExplorerTrail([]);
    onActiveNodeChange?.(null);
  };

  const handleAuthoringSelection = useCallback((selection: GraphAuthoringSelection | null) => {
    if (graphAuthoringSelectionsEqual(pendingAuthoringSelectionRef.current, selection)) {
      return;
    }
    pendingAuthoringSelectionRef.current = selection;
    setPendingAuthoringSelection(selection);
    onGraphAuthoringSelection?.(selection);
  }, [onGraphAuthoringSelection]);

  const explorerOpen = !useExternalInspection && explorerTrail.length > 0;
  const rootClassName = className ? `recap-reader-root ${className}` : "recap-reader-root";
  const effectiveSelectedSpanId = selectedSourceSpanId ?? selectedEvidenceSpanId;
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

      {typeof mentionsCount === "number" ? (
        <p className="recap-reader-hint union-supergraph-mentions-hint">
          Read-only TipTap projection of ingested recap Markdown. Editing and corpus writes are intentionally out of
          scope here. Graph chips are preview memory candidates; evidence highlights show the recap paragraph that supports the selected graph context. {mentionsCount} graph mention{mentionsCount === 1 ? "" : "s"} projected.
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

      <div className={`recap-reader-layout union-supergraph-layout${explorerOpen ? " graph-explorer-open" : ""}`}>
        <article
          className={`recap-reader-document union-supergraph-recap-document${
            documentScroll === "page" ? " recap-reader-document--page-scroll" : ""
          }`}
          aria-label={documentLabel}
        >
          <ReadOnlyTiptapRecap
            frontmatterPolicy={frontmatterPolicy}
            markdown={markdown}
            nodeViews={nodeViews}
            activeNodeId={activeNodeId}
            onSelectNode={openExplorer}
            sourceSpans={sourceSpans}
            selectedEvidenceSpanId={effectiveSelectedSpanId}
            nodeDeltaPresentations={nodeDeltaPresentations}
            sourceSpanDeltaOverlays={sourceSpanDeltaOverlays}
            authoringEnabled={authoringEnabled}
            authoringContext={authoringContext}
            onGraphAuthoringSelection={handleAuthoringSelection}
          />
        </article>
        {explorerOpen && activeNode ? (
          <GraphNodeExplorer
            key={activeNodeId}
            node={activeNode}
            nodeViews={nodeViews}
            trail={explorerTrail}
            onBack={popExplorer}
            onClose={closeExplorer}
            onExpand={pushExplorer}
            onEvidenceSelect={(badge) => setSelectedEvidenceSpanId(badge.source_span_ref_id ?? null)}
            selectedEvidenceSpanId={selectedEvidenceSpanId}
          />
        ) : null}
      </div>
    </div>
  );
}
