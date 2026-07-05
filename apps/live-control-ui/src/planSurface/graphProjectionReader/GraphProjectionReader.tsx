import { useEffect, useMemo, useRef, useState } from "react";
import type { Content } from "@tiptap/core";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

import type { GraphProjectionNodeView, RecapProjectionSourceSpan } from "../../api/types";
import { GraphNodeReferenceNode } from "../../tiptap/extensions/GraphNodeReferenceNode";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import { GraphNodeExplorer } from "../graphPreview/GraphNodePresentation";
import { setRecapGraphNodeRuntimeState, type RecapGraphNodeDeltaPresentation } from "../graphPreview/recapGraphNodeRuntime";
import { stripLeadingYamlFrontmatter } from "./projectionMarkdownPreprocessing";
import { attachSourceSpanDataAttributes, type SourceSpanDomOverlay } from "./sourceSpanHighlight";

export interface GraphProjectionReaderProps {
  markdown: string;
  nodeViews: Record<string, GraphProjectionNodeView>;
  sourceSpans: RecapProjectionSourceSpan[];
  mentionsCount?: number;
  graphId?: string | null;
  title?: string;
  subtitle?: string;
  sourceNote?: string;
  className?: string;
  documentLabel?: string;
  resetKey?: string | null;
  nodeDeltaPresentations?: Record<string, RecapGraphNodeDeltaPresentation>;
  sourceSpanDeltaOverlays?: Record<string, SourceSpanDomOverlay>;
  selectedSourceSpanId?: string | null;
  onActiveNodeChange?: (nodeId: string | null) => void;
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
}: {
  markdown: string;
  nodeViews: Record<string, GraphProjectionNodeView>;
  activeNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
  sourceSpans: RecapProjectionSourceSpan[];
  selectedEvidenceSpanId: string | null;
  nodeDeltaPresentations?: Record<string, RecapGraphNodeDeltaPresentation>;
  sourceSpanDeltaOverlays?: Record<string, SourceSpanDomOverlay>;
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

  useEffect(() => {
    editor?.commands.setContent(content, false);
  }, [content, editor]);

  useEffect(() => {
    setRecapGraphNodeRuntimeState({ nodeViews, activeNodeId, onSelectNode, deltaByNodeId: nodeDeltaPresentations ?? {} });
  }, [nodeViews, activeNodeId, onSelectNode, nodeDeltaPresentations]);

  useEffect(() => {
    const root = readerRef.current;
    if (!root) return;
    const highlighted = attachSourceSpanDataAttributes(root, sourceSpans, selectedEvidenceSpanId, sourceSpanDeltaOverlays ?? {});
    if (highlighted && typeof highlighted.scrollIntoView === "function") {
      highlighted.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [content, sourceSpans, selectedEvidenceSpanId, sourceSpanDeltaOverlays]);

  return (
    <div className="union-supergraph-tiptap-reader" ref={readerRef}>
      <EditorContent editor={editor} />
    </div>
  );
}

export function GraphProjectionReader({
  markdown,
  nodeViews,
  sourceSpans,
  mentionsCount,
  graphId,
  title,
  subtitle,
  sourceNote,
  className,
  documentLabel = "Projected recap",
  resetKey,
  nodeDeltaPresentations,
  sourceSpanDeltaOverlays,
  selectedSourceSpanId,
  onActiveNodeChange,
}: GraphProjectionReaderProps) {
  const [explorerTrail, setExplorerTrail] = useState<string[]>([]);
  const activeNodeId = explorerTrail.at(-1) ?? null;
  const activeNode = activeNodeId ? nodeViews[activeNodeId] : undefined;
  const [selectedEvidenceSpanId, setSelectedEvidenceSpanId] = useState<string | null>(null);

  useEffect(() => {
    setExplorerTrail([]);
    setSelectedEvidenceSpanId(null);
    onActiveNodeChange?.(null);
  }, [markdown, graphId, resetKey, onActiveNodeChange]);

  const openExplorer = (nodeId: string) => {
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

  const explorerOpen = explorerTrail.length > 0;
  const rootClassName = className ? `recap-reader-root ${className}` : "recap-reader-root";
  const effectiveSelectedSpanId = selectedSourceSpanId ?? selectedEvidenceSpanId;

  return (
    <div className={rootClassName}>
      {title || subtitle || sourceNote || graphId ? (
        <header className="recap-reader-header">
          <div>
            {title ? <h2>{title}</h2> : null}
            {subtitle ? <p>{subtitle}</p> : null}
            {sourceNote ? <p className="union-supergraph-source-note">{sourceNote}</p> : null}
          </div>
          {graphId ? <span className="union-supergraph-graph-id">{graphId}</span> : null}
        </header>
      ) : null}

      {typeof mentionsCount === "number" ? (
        <p className="recap-reader-hint union-supergraph-mentions-hint">
          Read-only TipTap projection of ingested recap Markdown. Editing and corpus writes are intentionally out of
          scope here. Graph chips are preview memory candidates; evidence highlights show the recap paragraph that supports the selected graph context. {mentionsCount} graph mention{mentionsCount === 1 ? "" : "s"} projected.
        </p>
      ) : null}

      <div className={`recap-reader-layout union-supergraph-layout${explorerOpen ? " graph-explorer-open" : ""}`}>
        <article className="recap-reader-document union-supergraph-recap-document" aria-label={documentLabel}>
          <ReadOnlyTiptapRecap
            markdown={markdown}
            nodeViews={nodeViews}
            activeNodeId={activeNodeId}
            onSelectNode={openExplorer}
            sourceSpans={sourceSpans}
            selectedEvidenceSpanId={effectiveSelectedSpanId}
            nodeDeltaPresentations={nodeDeltaPresentations}
            sourceSpanDeltaOverlays={sourceSpanDeltaOverlays}
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
