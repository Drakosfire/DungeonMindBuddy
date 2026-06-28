import { useEffect, useMemo, useState } from "react";
import type { Content } from "@tiptap/core";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

import type { GraphProjectionNodeView, UnionSupergraphProjectionResponse } from "../../api/types";
import { GraphNodeReferenceNode } from "../../tiptap/extensions/GraphNodeReferenceNode";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import {
  GraphNodeAdjacencyRow,
  GraphNodeDetailPanel,
} from "./GraphNodePresentation";
import { defaultPinnedNodeId } from "./recapNodePresentation";
import { setRecapGraphNodeRuntimeState } from "./recapGraphNodeRuntime";

interface UnionSupergraphRecapProjectionProps {
  payload: UnionSupergraphProjectionResponse;
  selectedSessionId: string;
  onSelectSession: (sessionId: string) => void;
  sessionOptions: string[];
  onOpenLegacy?: () => void;
}

function ReadOnlyTiptapRecap({
  markdown,
  nodeViews,
  pinnedNodeId,
  onSelectNode,
}: {
  markdown: string;
  nodeViews: Record<string, GraphProjectionNodeView>;
  pinnedNodeId: string | null;
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
    setRecapGraphNodeRuntimeState({ nodeViews, pinnedNodeId, onSelectNode });
  }, [nodeViews, pinnedNodeId, onSelectNode]);

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
}: UnionSupergraphRecapProjectionProps) {
  const initialPinnedNodeId = useMemo(() => defaultPinnedNodeId(payload), [payload]);
  const [pinnedNodeId, setPinnedNodeId] = useState<string | null>(initialPinnedNodeId);
  const pinnedNode = pinnedNodeId ? payload.node_views[pinnedNodeId] : undefined;
  const projectedMarkdown = payload.markdown
    ?? "# Session recap projection unavailable\n\nThe union-supergraph payload did not include projected recap Markdown.";

  useEffect(() => {
    setPinnedNodeId(defaultPinnedNodeId(payload));
  }, [payload.session_id]);

  return (
    <div className="recap-reader-root union-supergraph-recap-root">
      <header className="recap-reader-header">
        <div>
          <p className="plan-surface-kicker">Union supergraph · dogfood</p>
          <h2>Session focus lens</h2>
          <p>
            Global campaign graph with a Session {payload.focus.focus_session_id?.replace("session-", "") ?? "?"}{" "}
            focus overlay. Hover recap pills for context; click to pin and navigate adjacency.
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

      <div className="recap-reader-layout union-supergraph-layout">
        <article className="recap-reader-document union-supergraph-recap-document" aria-label="Projected recap">
          <ReadOnlyTiptapRecap
            markdown={projectedMarkdown}
            nodeViews={payload.node_views}
            pinnedNodeId={pinnedNodeId}
            onSelectNode={setPinnedNodeId}
          />
          {pinnedNode && pinnedNode.adjacency.length ? (
            <section
              className="union-supergraph-adjacency-group"
              aria-label={`Adjacency from ${pinnedNode.label}`}
            >
              <h4>Adjacency from {pinnedNode.label}</h4>
              <ul className="union-supergraph-adjacency-list">
                {pinnedNode.adjacency.map((candidate) => (
                  <GraphNodeAdjacencyRow
                    key={candidate.edge_id}
                    candidate={candidate}
                    onSelect={setPinnedNodeId}
                    selected={pinnedNodeId === candidate.node_id}
                  />
                ))}
              </ul>
            </section>
          ) : null}
        </article>
        <GraphNodeDetailPanel node={pinnedNode} />
      </div>
    </div>
  );
}
