import type {
  GraphProjectionAdjacencyCandidate,
  GraphProjectionEvidenceBadge,
  GraphProjectionNodeView,
} from "../../api/types";
import {
  buildRecapNodePresentation,
  fallbackRecapNodePresentation,
  roleClass,
  type RecapNodePresentation,
} from "./recapNodePresentation";

function EvidenceBadgeRow({ badge }: { badge: GraphProjectionEvidenceBadge }) {
  const tone = badge.is_focus_session_evidence ? "focus" : "worldbuilding";
  return (
    <li className="union-supergraph-evidence-badge" data-tone={tone}>
      <span className="union-supergraph-evidence-domain">{badge.source_domain}</span>
      <span>{badge.label ?? badge.evidence_role}</span>
      {badge.is_focus_session_evidence ? (
        <em className="union-supergraph-focus-tag">focus session</em>
      ) : (
        <em className="union-supergraph-context-tag">broader context</em>
      )}
    </li>
  );
}

export function GraphNodeToken({
  presentation,
  label,
  pinned,
  onSelect,
}: {
  presentation: RecapNodePresentation;
  label: string;
  pinned: boolean;
  onSelect: () => void;
}) {
  const role = presentation.role || presentation.kind || "node";
  return (
    <span className="recap-node-token-wrap">
      <button
        type="button"
        className={`recap-node-token role-${roleClass(role)}${pinned ? " pinned" : ""}`}
        data-graph-node-id={presentation.nodeId}
        onClick={onSelect}
      >
        {label}
      </button>
      <span className="recap-node-hover-card" role="tooltip">
        <strong>{presentation.label}</strong>
        <span>{presentation.kind}</span>
        {presentation.description ? <small>{presentation.description}</small> : null}
        {presentation.chips.length ? (
          <span className="recap-node-chip-row">
            {presentation.chips.map((chip) => (
              <em key={`${presentation.nodeId}:${chip.label}`}>{chip.label}</em>
            ))}
          </span>
        ) : null}
      </span>
    </span>
  );
}

export function GraphNodeAdjacencyRow({
  candidate,
  onSelect,
  selected,
}: {
  candidate: GraphProjectionAdjacencyCandidate;
  onSelect: (nodeId: string) => void;
  selected: boolean;
}) {
  return (
    <li className="union-supergraph-adjacency-item" data-focus={candidate.anchored_to_focus_session}>
      <button
        type="button"
        className={`union-supergraph-adjacency-button${selected ? " selected" : ""}`}
        onClick={() => onSelect(candidate.node_id)}
      >
        <strong>{candidate.label}</strong>
        <span>{candidate.predicate}</span>
        <span>{candidate.source_domains.join(", ")}</span>
        {candidate.anchored_to_focus_session ? (
          <em className="union-supergraph-focus-tag">focus session</em>
        ) : (
          <em className="union-supergraph-context-tag">worldbuilding</em>
        )}
      </button>
    </li>
  );
}

export function GraphNodeDetailPanel({ node }: { node?: GraphProjectionNodeView }) {
  if (!node) {
    return (
      <aside className="recap-node-panel union-supergraph-node-panel">
        <p className="plan-projection-empty">
          Hover a pill for context, or click one to pin its node here.
        </p>
      </aside>
    );
  }

  const presentation = buildRecapNodePresentation(node);
  const focusEvidence = node.evidence_badges.filter((badge) => badge.is_focus_session_evidence);
  const contextEvidence = node.evidence_badges.filter((badge) => !badge.is_focus_session_evidence);
  const focusAdjacency = node.adjacency.filter((candidate) => candidate.anchored_to_focus_session);
  const contextAdjacency = node.adjacency.filter((candidate) => !candidate.anchored_to_focus_session);

  return (
    <aside className="recap-node-panel union-supergraph-node-panel" aria-label="Global node detail">
      <p className="plan-surface-kicker">Pinned node</p>
      <h3>{node.label}</h3>
      <p className="union-supergraph-node-id">
        <code>{node.node_id}</code>
      </p>
      <p className="recap-node-kind">
        {node.role} · {node.kind}
        {node.anchored_to_focus_session ? " · anchored to focus session" : ""}
      </p>
      {presentation.description ? (
        <p className="recap-node-description">{presentation.description}</p>
      ) : null}
      {presentation.chips.length ? (
        <ul className="recap-node-chips" aria-label="Context chips">
          {presentation.chips.map((chip) => (
            <li key={`${node.node_id}:${chip.label}`} data-tone={chip.tone}>
              {chip.label}
            </li>
          ))}
        </ul>
      ) : null}

      {focusEvidence.length ? (
        <section className="union-supergraph-evidence-group" aria-label="Focus session evidence">
          <h4>Focus session evidence</h4>
          <ul>
            {focusEvidence.map((badge) => (
              <EvidenceBadgeRow key={badge.evidence_ref_id} badge={badge} />
            ))}
          </ul>
        </section>
      ) : null}

      {contextEvidence.length ? (
        <section className="union-supergraph-evidence-group" aria-label="Broader context evidence">
          <h4>Broader context evidence</h4>
          <ul>
            {contextEvidence.map((badge) => (
              <EvidenceBadgeRow key={badge.evidence_ref_id} badge={badge} />
            ))}
          </ul>
        </section>
      ) : null}

      {focusAdjacency.length ? (
        <section className="union-supergraph-adjacency-group" aria-label="Focus session adjacency">
          <h4>Focus session adjacency</h4>
          <ul>
            {focusAdjacency.map((candidate) => (
              <li key={candidate.edge_id}>
                <span className="union-supergraph-adjacency-label">{candidate.label}</span>
                <span className="union-supergraph-adjacency-meta">{candidate.predicate}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {contextAdjacency.length ? (
        <section className="union-supergraph-adjacency-group" aria-label="Worldbuilding adjacency">
          <h4>Worldbuilding adjacency</h4>
          <ul>
            {contextAdjacency.map((candidate) => (
              <li key={candidate.edge_id}>
                <span className="union-supergraph-adjacency-label">{candidate.label}</span>
                <span className="union-supergraph-adjacency-meta">{candidate.predicate}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </aside>
  );
}

export function presentationForNodeId(
  nodeViews: Record<string, GraphProjectionNodeView>,
  nodeId: string,
  label: string,
): RecapNodePresentation {
  const node = nodeViews[nodeId];
  return node ? buildRecapNodePresentation(node) : fallbackRecapNodePresentation(nodeId, label);
}
