import { useEffect, useMemo, useState } from "react";
import type { Content } from "@tiptap/core";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

import type { GraphProjectionNodeView, UnionSupergraphProjectionResponse } from "../../api/types";
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
}: {
  markdown: string;
  nodeViews: Record<string, GraphProjectionNodeView>;
  activeNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
}) {
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

  return (
    <div className="union-supergraph-tiptap-reader">
      <EditorContent editor={editor} />
    </div>
  );
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
  const sourceCopy = {
    "latest-graph-ingest": {
      label: "latest graph-ingest preview",
      description: "This recap is projected from the latest preview union supergraph for this campaign/session.",
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
        scope here. {payload.mentions.length} graph mention{payload.mentions.length === 1 ? "" : "s"} projected.
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
          />
        ) : null}
      </div>
    </div>
  );
}
