import type { ReactNode } from "react";
import type {
  GraphProjectionAdjacencyCandidate,
  GraphProjectionEvidenceBadge,
  GraphProjectionNodeView,
} from "../../api/types";
import {
  adjacencyThreadLabel,
  buildRecapNodePresentation,
  evidencePlanningText,
  fallbackRecapNodePresentation,
  roleClass,
  type RecapNodePresentation,
} from "./recapNodePresentation";

function EvidenceBadgeRow({ badge }: { badge: GraphProjectionEvidenceBadge }) {
  const tone = badge.is_focus_session_evidence ? "focus" : "worldbuilding";
  return (
    <li className="union-supergraph-evidence-badge" data-tone={tone}>
      <span className="union-supergraph-evidence-domain">{badge.source_domain}</span>
      <span>{evidencePlanningText(badge)}</span>
      {badge.is_focus_session_evidence ? (
        <em className="union-supergraph-focus-tag">current session</em>
      ) : (
        <em className="union-supergraph-context-tag">prior context</em>
      )}
    </li>
  );
}

function PlanningScanSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="recap-planning-scan-section">
      <span className="recap-planning-scan-kicker">{title}</span>
      {children}
    </div>
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
  const focusSession = presentation.planningChips.some((chip) => chip.tone === "evidence");
  return (
    <span className="recap-node-token-wrap">
      <button
        type="button"
        className={`recap-node-token role-${roleClass(role)}${pinned ? " pinned" : ""}${focusSession ? " session-active" : ""}`}
        data-graph-node-id={presentation.nodeId}
        onClick={onSelect}
      >
        {label}
      </button>
      <span className="recap-node-hover-card recap-planning-card" role="tooltip">
        <strong>{presentation.label}</strong>
        <span className="recap-node-kind">
          {presentation.role} · {presentation.kind}
        </span>
        {presentation.summary ? (
          <small className="recap-planning-summary">{presentation.summary}</small>
        ) : null}
        {presentation.whyNow ? (
          <PlanningScanSection title="Why now">
            <small>{presentation.whyNow}</small>
          </PlanningScanSection>
        ) : null}
        {presentation.knownBefore ? (
          <PlanningScanSection title="Known before">
            <small>{presentation.knownBefore}</small>
          </PlanningScanSection>
        ) : null}
        {presentation.threadHints.length ? (
          <PlanningScanSection title="Threads">
            <ul className="recap-planning-thread-list">
              {presentation.threadHints.map((hint) => (
                <li key={`${presentation.nodeId}:${hint.nodeId}`}>{hint.edgeLabel}</li>
              ))}
            </ul>
          </PlanningScanSection>
        ) : null}
        {presentation.planningChips.length ? (
          <span className="recap-node-chip-row">
            {presentation.planningChips.map((chip) => (
              <em key={`${presentation.nodeId}:${chip.label}`} data-tone={chip.tone}>
                {chip.label}
              </em>
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
        <span>{adjacencyThreadLabel(candidate)}</span>
        {candidate.anchored_to_focus_session ? (
          <em className="union-supergraph-focus-tag">current session</em>
        ) : (
          <em className="union-supergraph-context-tag">prior context</em>
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
      <p className="recap-node-kind">
        {node.role} · {node.kind}
        {node.anchored_to_focus_session ? " · in this session" : ""}
      </p>
      {presentation.summary ? (
        <p className="recap-node-description">{presentation.summary}</p>
      ) : null}
      {presentation.whyNow ? (
        <PlanningScanSection title="Why now">
          <p className="recap-planning-scan-line">{presentation.whyNow}</p>
        </PlanningScanSection>
      ) : null}
      {presentation.knownBefore ? (
        <PlanningScanSection title="Known before">
          <p className="recap-planning-scan-line">{presentation.knownBefore}</p>
        </PlanningScanSection>
      ) : null}
      {presentation.planningChips.length ? (
        <ul className="recap-node-chips" aria-label="Planning posture">
          {presentation.planningChips.map((chip) => (
            <li key={`${node.node_id}:${chip.label}`} data-tone={chip.tone}>
              {chip.label}
            </li>
          ))}
        </ul>
      ) : null}

      {focusEvidence.length ? (
        <section className="union-supergraph-evidence-group" aria-label="Current session evidence">
          <h4>Current session</h4>
          <ul>
            {focusEvidence.map((badge) => (
              <EvidenceBadgeRow key={badge.evidence_ref_id} badge={badge} />
            ))}
          </ul>
        </section>
      ) : null}

      {contextEvidence.length ? (
        <section className="union-supergraph-evidence-group" aria-label="Prior context evidence">
          <h4>Prior context</h4>
          <ul>
            {contextEvidence.map((badge) => (
              <EvidenceBadgeRow key={badge.evidence_ref_id} badge={badge} />
            ))}
          </ul>
        </section>
      ) : null}

      {focusAdjacency.length ? (
        <section className="union-supergraph-adjacency-group" aria-label="Current session threads">
          <h4>Connected threads · this session</h4>
          <ul>
            {focusAdjacency.map((candidate) => (
              <li key={candidate.edge_id}>
                <span className="union-supergraph-adjacency-label">{adjacencyThreadLabel(candidate)}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {contextAdjacency.length ? (
        <section className="union-supergraph-adjacency-group" aria-label="Broader context threads">
          <h4>Connected threads · prior context</h4>
          <ul>
            {contextAdjacency.map((candidate) => (
              <li key={candidate.edge_id}>
                <span className="union-supergraph-adjacency-label">{adjacencyThreadLabel(candidate)}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <p className="recap-planning-debug-id">
        <code>{node.node_id}</code>
      </p>
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
