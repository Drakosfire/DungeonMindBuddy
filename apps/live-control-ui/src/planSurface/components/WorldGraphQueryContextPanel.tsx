import type {
  AgentWorldGraphQueryContext,
  PersistedWorldGraphContextSummary,
} from "../../api/types";

interface WorldGraphQueryContextPanelProps {
  context: AgentWorldGraphQueryContext | null;
  summary: PersistedWorldGraphContextSummary | null | undefined;
  persistedOnly?: boolean;
}

function nodeLabel(
  nodeId: string,
  nodes: AgentWorldGraphQueryContext["nodes"] | undefined,
): string {
  const node = nodes?.find((entry) => entry.node_id === nodeId);
  return node?.label ?? nodeId;
}

function focusLabel(focus: { kind: "none" | "session"; session_id?: string | null; sessionId?: string | null }): string {
  if (focus.kind === "none") return "none";
  return focus.session_id ?? focus.sessionId ?? "unknown session";
}

export function WorldGraphQueryContextPanel({
  context,
  summary,
  persistedOnly = false,
}: WorldGraphQueryContextPanelProps) {
  if (!context && !summary) return null;

  const status = context?.status ?? summary?.status ?? "unavailable";
  const revisionId = context?.revision_id ?? summary?.revisionId ?? null;
  const isHead = context?.is_head ?? summary?.isHead ?? null;
  const focus = context?.focus ?? (summary?.focus
    ? { kind: summary.focus.kind, session_id: summary.focus.sessionId }
    : { kind: "none" as const, session_id: null });
  const matchedNodeIds = context?.matched_node_ids ?? summary?.matchedNodeIds ?? [];
  const projectionTruncated = context?.projection_truncated ?? summary?.projectionTruncated ?? false;
  const warningCodes = context?.warning_codes ?? summary?.warningCodes ?? [];
  const relationships = context?.relationships ?? [];
  const attributes = context?.attributes ?? [];
  const diagnostics = context?.diagnostics ?? [];
  const nodes = context?.nodes ?? [];

  const connectedObjects = relationships.map((relationship) => {
    const peerId = matchedNodeIds.includes(relationship.source_node_id)
      ? relationship.target_node_id
      : relationship.source_node_id;
    return {
      edgeId: relationship.edge_id,
      peerId,
      peerLabel: nodeLabel(peerId, nodes),
      predicate: relationship.predicate,
      label: relationship.label,
      direction: relationship.direction,
    };
  });

  return (
    <section
      className="plan-agent-world-graph-context"
      data-status={status}
      aria-label="World graph query context"
    >
      <details className="plan-agent-metadata-drawer">
        <summary>
          World graph · {status} · {matchedNodeIds.length} matched
        </summary>
        <div>
          <p className="plan-surface-kicker">World graph</p>
          <h4>Graph context · {status}</h4>
          {persistedOnly ? (
            <p className="plan-agent-muted">
              Detailed graph projection was not retained for this turn. Summary only.
            </p>
          ) : null}
        </div>

        <dl className="plan-agent-world-graph-context-grid">
        <div>
          <dt>Revision</dt>
          <dd>{revisionId ?? "n/a"}</dd>
        </div>
        <div>
          <dt>Head</dt>
          <dd>{isHead == null ? "n/a" : isHead ? "yes" : "no"}</dd>
        </div>
        <div>
          <dt>Focus session</dt>
          <dd>{focusLabel(focus)}</dd>
        </div>
        <div>
          <dt>Projection truncated</dt>
          <dd>{projectionTruncated ? "yes" : "no"}</dd>
        </div>
      </dl>

      {matchedNodeIds.length ? (
        <div className="plan-agent-world-graph-matched">
          <h5>Matched durable IDs</h5>
          <ul>
            {matchedNodeIds.map((nodeId) => (
              <li key={nodeId}>
                <code>{nodeId}</code>
                {nodes.length ? (
                  <span className="plan-agent-muted"> · {nodeLabel(nodeId, nodes)}</span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {connectedObjects.length ? (
        <div className="plan-agent-world-graph-connected">
          <h5>Connected objects</h5>
          <ul>
            {connectedObjects.map((entry) => (
              <li key={entry.edgeId}>
                <strong>{entry.peerLabel}</strong>
                <span className="plan-agent-muted">
                  {" "}
                  · {entry.predicate}
                  {entry.direction ? ` (${entry.direction})` : ""}
                </span>
                {entry.label ? <p>{entry.label}</p> : null}
                <code>{entry.peerId}</code>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {attributes.length ? (
        <div className="plan-agent-world-graph-attributes">
          <h5>Graph attributes</h5>
          <p className="plan-agent-muted">Structured graph memory — not corpus citations.</p>
          <ul>
            {attributes.map((attribute) => (
              <li key={attribute.assertion_id}>
                <strong>{nodeLabel(attribute.subject_node_id, nodes)}</strong>
                {attribute.label ? <span> · {attribute.label}</span> : null}
                {attribute.predicate ? <span className="plan-agent-muted"> · {attribute.predicate}</span> : null}
                {attribute.text_value ? <p>{attribute.text_value}</p> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {warningCodes.length ? (
        <div className="plan-agent-world-graph-warnings">
          <h5>Warning codes</h5>
          <ul>
            {warningCodes.map((code) => <li key={code}><code>{code}</code></li>)}
          </ul>
        </div>
      ) : null}

      {diagnostics.length ? (
        <div className="plan-agent-world-graph-diagnostics">
          <h5>Diagnostics</h5>
          <ul>
            {diagnostics.map((diagnostic) => (
              <li key={`${diagnostic.code}-${diagnostic.message}`}>
                <code>{diagnostic.code}</code>
                <span className="plan-agent-muted"> · {diagnostic.severity}</span>
                <p>{diagnostic.message}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      </details>
    </section>
  );
}
