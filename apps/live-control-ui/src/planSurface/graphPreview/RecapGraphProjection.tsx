import type {
  GraphPreviewRunSummary,
  RecapArtifactRecord,
  RecapGraphNode,
  RecapGraphPresentationResponse,
} from "../../api/types";
import { parseRecapInlineSegments, splitRecapBlocks } from "./recapMarkdown";
import { recapArtifactSessionLabel } from "./recapSessionLabels";

interface RecapGraphProjectionProps {
  payload: RecapGraphPresentationResponse;
  runs: GraphPreviewRunSummary[];
  sessionRecords: RecapArtifactRecord[];
  selectedSessionId: string;
  onSelectSession: (sessionId: string) => void;
  selectedRunDir: string;
  onSelectRun: (runDir: string) => void;
  pinnedNodeId: string | null;
  onPinNode: (objectId: string) => void;
}

function roleClass(role: string): string {
  return role.toLowerCase().replace(/[^a-z0-9_-]+/g, "-") || "node";
}

function NodeToken({
  node,
  label,
  objectId,
  pinned,
  onPinNode,
}: {
  node?: RecapGraphNode;
  label: string;
  objectId: string;
  pinned: boolean;
  onPinNode: (objectId: string) => void;
}) {
  const role = node?.role ?? node?.kind ?? "node";
  return (
    <span className="recap-node-token-wrap">
      <button
        type="button"
        className={`recap-node-token role-${roleClass(role)}${pinned ? " pinned" : ""}`}
        onClick={() => onPinNode(objectId)}
      >
        {label}
      </button>
      {node ? (
        <span className="recap-node-hover-card" role="tooltip">
          <strong>{node.label}</strong>
          <span>{node.kind}</span>
          {node.description ? <small>{node.description}</small> : null}
          {node.chips.length ? (
            <span className="recap-node-chip-row">
              {node.chips.map((chip) => (
                <em key={`${node.object_id}:${chip.label}`}>{chip.label}</em>
              ))}
            </span>
          ) : null}
        </span>
      ) : null}
    </span>
  );
}

function RecapBlock({
  block,
  nodes,
  pinnedNodeId,
  onPinNode,
}: {
  block: string;
  nodes: Record<string, RecapGraphNode>;
  pinnedNodeId: string | null;
  onPinNode: (objectId: string) => void;
}) {
  const heading = block.match(/^(#{1,4})\s+(.+)$/);
  const body = heading ? heading[2] : block;
  const content = parseRecapInlineSegments(body).map((segment, index) => {
    if (segment.type === "text") {
      return <span key={index}>{segment.text}</span>;
    }
    return (
      <NodeToken
        key={`${segment.objectId}:${index}`}
        node={nodes[segment.objectId]}
        label={segment.text}
        objectId={segment.objectId}
        pinned={pinnedNodeId === segment.objectId}
        onPinNode={onPinNode}
      />
    );
  });

  if (heading) {
    return <h3 className="recap-reader-heading">{content}</h3>;
  }
  return <p className="recap-reader-paragraph">{content}</p>;
}

function PinnedNodePanel({ node }: { node?: RecapGraphNode }) {
  if (!node) {
    return (
      <aside className="recap-node-panel">
        <p className="plan-projection-empty">Hover a pill for context, or click one to pin its node here.</p>
      </aside>
    );
  }
  return (
    <aside className="recap-node-panel">
      <p className="plan-surface-kicker">Pinned node</p>
      <h3>{node.label}</h3>
      <p className="recap-node-kind">{node.kind}</p>
      {node.description ? <p className="recap-node-description">{node.description}</p> : null}
      {node.chips.length ? (
        <ul className="recap-node-chips" aria-label="Context chips">
          {node.chips.map((chip) => (
            <li key={`${node.object_id}:${chip.label}`} data-tone={chip.tone}>{chip.label}</li>
          ))}
        </ul>
      ) : null}
    </aside>
  );
}

export function RecapGraphProjection({
  payload,
  runs,
  sessionRecords,
  selectedSessionId,
  onSelectSession,
  selectedRunDir,
  onSelectRun,
  pinnedNodeId,
  onPinNode,
}: RecapGraphProjectionProps) {
  const blocks = splitRecapBlocks(payload.markdown);
  const pinnedNode = pinnedNodeId ? payload.nodes[pinnedNodeId] : undefined;

  return (
    <div className="recap-reader-root">
      <header className="recap-reader-header">
        <div>
          <p className="plan-surface-kicker">Recap</p>
          <h2>Session graph reader</h2>
          <p>Generated Markdown links render as graph-aware entity pills; canon recap files stay untouched.</p>
        </div>
        <span>{payload.links.length} linked mentions</span>
      </header>

      <div className="recap-reader-toolbar">
        {sessionRecords.length > 0 ? (
          <label className="graph-preview-run-picker">
            <span>Session</span>
            <select
              value={selectedSessionId}
              onChange={(event) => onSelectSession(event.target.value)}
            >
              {sessionRecords.map((record) => (
                <option key={record.artifact_id} value={record.session_id}>
                  {recapArtifactSessionLabel(record)}
                  {record.graph_run_refs.length === 0 ? " · recap only" : ""}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        {runs.length > 1 ? (
          <label className="graph-preview-run-picker">
            <span>Graph run</span>
            <select value={selectedRunDir} onChange={(event) => onSelectRun(event.target.value)}>
              {runs.map((run) => (
                <option key={run.run_dir} value={run.run_dir}>
                  {run.model_id ?? "model"} · {run.run_dir.split("/").slice(-1)[0]}
                  {run.canonical_ir_valid ? " · valid" : ""}
                </option>
              ))}
            </select>
          </label>
        ) : runs.length === 0 ? (
          <p className="recap-reader-hint">No graph extraction runs for this session — showing recap text only.</p>
        ) : null}
      </div>

      <div className="recap-reader-layout">
        <article className="recap-reader-document" aria-label="Graph-linked recap">
          {blocks.map((block, index) => (
            <RecapBlock
              key={`${index}:${block.slice(0, 24)}`}
              block={block}
              nodes={payload.nodes}
              pinnedNodeId={pinnedNodeId}
              onPinNode={onPinNode}
            />
          ))}
        </article>
        <PinnedNodePanel node={pinnedNode} />
      </div>
    </div>
  );
}
