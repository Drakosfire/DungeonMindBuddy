import { useEffect, useMemo, useRef, useState } from "react";
import type { Content } from "@tiptap/core";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

import type { GraphProjectionNodeView, RecapProjectionSourceSpan, UnionSupergraphProjectionResponse } from "../../api/types";
import { GraphNodeReferenceNode } from "../../tiptap/extensions/GraphNodeReferenceNode";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import { GraphNodeExplorer } from "./GraphNodePresentation";
import { setRecapGraphNodeRuntimeState } from "./recapGraphNodeRuntime";
import type { RecapProjectionSource } from "./RecapGraphModule";

interface UnionSupergraphRecapProjectionProps {
  payload: UnionSupergraphProjectionResponse;
  selectedSessionId: string;
  onSelectSession: (sessionId: string) => void;
  sessionOptions: string[];
  onOpenLegacy?: () => void;
  projectionSource?: RecapProjectionSource;
}

function ReadOnlyTiptapRecap({
  markdown,
  nodeViews,
  activeNodeId,
  onSelectNode,
  sourceSpans,
  selectedEvidenceSpanId,
}: {
  markdown: string;
  nodeViews: Record<string, GraphProjectionNodeView>;
  activeNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
  sourceSpans: RecapProjectionSourceSpan[];
  selectedEvidenceSpanId: string | null;
}) {
  const readerRef = useRef<HTMLDivElement | null>(null);
  const content = useMemo(
    () => markdownToTiptapDoc(markdown, { parseGraphNodeLinks: true }).doc as Content,
    [markdown],
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
    setRecapGraphNodeRuntimeState({ nodeViews, activeNodeId, onSelectNode });
  }, [nodeViews, activeNodeId, onSelectNode]);

  useEffect(() => {
    const root = readerRef.current;
    if (!root) return;
    const highlighted = attachSourceSpanDataAttributes(root, sourceSpans, selectedEvidenceSpanId);
    if (highlighted && typeof highlighted.scrollIntoView === "function") {
      highlighted.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [content, sourceSpans, selectedEvidenceSpanId]);

  return (
    <div className="union-supergraph-tiptap-reader" ref={readerRef}>
      <EditorContent editor={editor} />
    </div>
  );
}

function normalizeEvidenceText(value: string): string {
  return value.replace(/\s+/g, " ").trim().toLowerCase();
}

function readableNodeText(node: HTMLElement): string {
  const clone = node.cloneNode(true) as HTMLElement;
  clone.querySelectorAll(".recap-node-hover-card").forEach((hiddenContext) => hiddenContext.remove());
  return clone.textContent ?? "";
}

function attachSourceSpanDataAttributes(
  root: HTMLElement,
  sourceSpans: RecapProjectionSourceSpan[],
  selectedEvidenceSpanId: string | null,
): HTMLElement | null {
  const candidates = Array.from(
    root.querySelectorAll<HTMLElement>(".ProseMirror p, .ProseMirror li, .ProseMirror blockquote p"),
  );
  candidates.forEach((candidate) => {
    delete candidate.dataset.sourceSpanId;
    candidate.classList.remove("recap-source-span-highlight");
  });

  const unused = new Set(candidates);
  const claimed = new Map<string, HTMLElement>();

  for (const span of sourceSpans) {
    const excerpt = normalizeEvidenceText(span.text_excerpt ?? "");
    if (!excerpt) continue;
    const matches = Array.from(unused).filter((node) => {
      const nodeText = normalizeEvidenceText(readableNodeText(node));
      return nodeText === excerpt || nodeText.includes(excerpt);
    });
    if (matches.length === 1) {
      claimed.set(span.span_id, matches[0]);
      unused.delete(matches[0]);
    }
  }

  for (const span of sourceSpans) {
    if (claimed.has(span.span_id)) continue;
    const ordinal = span.ordinal ?? 0;
    const ordinalCandidate = ordinal > 0 ? candidates[ordinal - 1] : undefined;
    if (ordinalCandidate && unused.has(ordinalCandidate)) {
      claimed.set(span.span_id, ordinalCandidate);
      unused.delete(ordinalCandidate);
    }
  }

  let highlighted: HTMLElement | null = null;
  for (const [spanId, node] of claimed.entries()) {
    node.dataset.sourceSpanId = spanId;
    const isHighlighted = spanId === selectedEvidenceSpanId;
    node.classList.toggle("recap-source-span-highlight", isHighlighted);
    if (isHighlighted) highlighted = node;
  }
  return highlighted;
}

export function UnionSupergraphRecapProjection({
  payload,
  selectedSessionId,
  onSelectSession,
  sessionOptions,
  onOpenLegacy,
  projectionSource = "default-preview-source",
}: UnionSupergraphRecapProjectionProps) {
  const [explorerTrail, setExplorerTrail] = useState<string[]>([]);
  const activeNodeId = explorerTrail.at(-1) ?? null;
  const activeNode = activeNodeId ? payload.node_views[activeNodeId] : undefined;
  const [selectedEvidenceSpanId, setSelectedEvidenceSpanId] = useState<string | null>(null);
  const paragraphSourceSpans = useMemo(
    () => (payload.source_spans ?? [])
      .filter((span) => span.kind === "paragraph")
      .sort((a, b) => (a.ordinal ?? 0) - (b.ordinal ?? 0)),
    [payload.source_spans],
  );
  const sourceCopy = {
    "latest-graph-ingest": {
      label: "latest graph-ingest preview",
      description: "This recap is projected from the latest preview union supergraph for this campaign/session.",
    },
    "recap-only": {
      label: "recap memory only",
      description: "This session has ingested recap memory, but no graph projection is ready yet, so graph chips are unavailable.",
    },
    "default-preview-source": {
      label: "default preview fixture",
      description: "No latest graph-ingest preview store was available for this session, so this is using the default preview source.",
    },
    legacy: {
      label: "legacy recap preview",
      description: "This recap is using the legacy recap preview projection.",
    },
    unavailable: {
      label: "no graph projection available",
      description: "No graph projection is available for this session yet. Generate Recap Memory first, then retry.",
    },
  }[projectionSource];
  const projectedMarkdown = payload.markdown
    ?? "# Session recap projection unavailable\n\nThe union-supergraph payload did not include projected recap Markdown.";

  useEffect(() => {
    setExplorerTrail([]);
    setSelectedEvidenceSpanId(null);
  }, [payload.session_id]);

  const openExplorer = (nodeId: string) => {
    setExplorerTrail([nodeId]);
  };

  const pushExplorer = (nodeId: string) => {
    setExplorerTrail((trail) => {
      if (trail.at(-1) === nodeId) {
        return trail;
      }
      return [...trail, nodeId];
    });
  };

  const popExplorer = () => {
    setExplorerTrail((trail) => (trail.length > 1 ? trail.slice(0, -1) : trail));
  };

  const closeExplorer = () => {
    setExplorerTrail([]);
  };

  const explorerOpen = explorerTrail.length > 0;

  return (
    <div className="recap-reader-root union-supergraph-recap-root">
      <header className="recap-reader-header">
        <div>
          <p className="plan-surface-kicker">Union supergraph · dogfood</p>
          <h2>Session focus lens</h2>
          <p>
            Global campaign graph with a Session {payload.focus.focus_session_id?.replace("session-", "") ?? "?"}{" "}
            focus overlay. Hover recap chips for a quick scan; click to expand and crawl suggested connections.
          </p>
          <p className="union-supergraph-source-note">
            Source: {sourceCopy.label}. {sourceCopy.description}
          </p>
        </div>
        <span className="union-supergraph-graph-id">{payload.graph_id ?? "union-supergraph"}</span>
      </header>

      <div className="recap-reader-toolbar">
        <label className="graph-preview-run-picker">
          <span>Focus session</span>
          <select
            value={selectedSessionId}
            onChange={(event) => onSelectSession(event.target.value)}
          >
            {sessionOptions.map((sessionId) => (
              <option key={sessionId} value={sessionId}>
                {sessionId.replace("session-", "Session ")}
              </option>
            ))}
          </select>
        </label>
        {onOpenLegacy ? (
          <button type="button" className="union-supergraph-legacy-button" onClick={onOpenLegacy}>
            Legacy recap preview
          </button>
        ) : null}
      </div>

      <p className="recap-reader-hint union-supergraph-mentions-hint">
        Read-only TipTap projection of ingested recap Markdown. Editing and corpus writes are intentionally out of
        scope here. Graph chips are preview memory candidates; evidence highlights show the recap paragraph that supports the selected graph context. {payload.mentions.length} graph mention{payload.mentions.length === 1 ? "" : "s"} projected.
      </p>

      <div
        className={`recap-reader-layout union-supergraph-layout${explorerOpen ? " graph-explorer-open" : ""}`}
      >
        <article className="recap-reader-document union-supergraph-recap-document" aria-label="Projected recap">
          <ReadOnlyTiptapRecap
            markdown={projectedMarkdown}
            nodeViews={payload.node_views}
            activeNodeId={activeNodeId}
            onSelectNode={openExplorer}
            sourceSpans={paragraphSourceSpans}
            selectedEvidenceSpanId={selectedEvidenceSpanId}
          />
        </article>
        {explorerOpen && activeNode ? (
          <GraphNodeExplorer
            key={activeNodeId}
            node={activeNode}
            nodeViews={payload.node_views}
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
