import type { ReactNode } from "react";
import { useState } from "react";
import type {
  GraphProjectionAdjacencyCandidate,
  GraphProjectionEvidenceBadge,
  GraphProjectionNodeView,
  GraphProjectionSuggestedExpansion,
} from "../../api/types";
import {
  adjacencyThreadLabel,
  buildRecapNodePresentation,
  DEFAULT_SUGGESTED_EXPANSION_DISPLAY_CAP,
  expansionPresentationLabel,
  expansionRankReasonLabel,
  evidencePlanningText,
  fallbackRecapNodePresentation,
  roleClass,
  type RecapNodePresentation,
} from "./recapNodePresentation";

function EvidenceBadgeRow({
  badge,
  onSelect,
  selected,
}: {
  badge: GraphProjectionEvidenceBadge;
  onSelect?: (badge: GraphProjectionEvidenceBadge) => void;
  selected?: boolean;
}) {
  const tone = badge.is_focus_session_evidence ? "focus" : "worldbuilding";
  const label = evidencePlanningText(badge);
  const content = (
    <>
      <span className="union-supergraph-evidence-domain">{badge.source_domain}</span>
      <span>{label}</span>
      {badge.source_span_ref_id ? <small>{badge.source_span_ref_id}</small> : null}
      {badge.is_focus_session_evidence ? (
        <em className="union-supergraph-focus-tag">current session</em>
      ) : (
        <em className="union-supergraph-context-tag">prior context</em>
      )}
    </>
  );
  return (
    <li className="union-supergraph-evidence-badge" data-tone={tone} data-selected={selected ? "true" : "false"}>
      {badge.source_span_ref_id ? (
        <button
          type="button"
          className="union-supergraph-evidence-button"
          onClick={() => onSelect?.(badge)}
        >
          {content}
        </button>
      ) : (
        <div className="union-supergraph-evidence-button">{content}</div>
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
  deltaStatus,
  deltaLabel,
  deltaSummary,
  tokenClassName,
  counterpartHighlighted = false,
  onMouseEnter,
  onMouseLeave,
  onFocus,
  onBlur,
}: {
  presentation: RecapNodePresentation;
  label: string;
  pinned: boolean;
  onSelect: () => void;
  deltaStatus?: string;
  deltaLabel?: string;
  deltaSummary?: string | null;
  tokenClassName?: string;
  counterpartHighlighted?: boolean;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
  onFocus?: () => void;
  onBlur?: () => void;
}) {
  const role = presentation.role || presentation.kind || "node";
  const focusSession = presentation.planningChips.some((chip) => chip.tone === "evidence");
  const normalizedDeltaStatus = deltaStatus ?? "unclassified";
  const showDeltaBadge =
    normalizedDeltaStatus !== "unknown" &&
    normalizedDeltaStatus !== "matched" &&
    normalizedDeltaStatus !== "unclassified";
  return (
    <span
      className="recap-node-token-wrap"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      onFocus={onFocus}
      onBlur={onBlur}
    >
      <button
        type="button"
        className={`recap-node-token role-${roleClass(role)} delta-${normalizedDeltaStatus}${pinned ? " pinned" : ""}${focusSession ? " session-active" : ""}${counterpartHighlighted ? " counterpart-highlighted" : ""}${tokenClassName ? ` ${tokenClassName}` : ""}`}
        data-graph-node-id={presentation.nodeId}
        data-delta-status={normalizedDeltaStatus}
        data-counterpart-highlighted={counterpartHighlighted ? "true" : undefined}
        onClick={onSelect}
      >
        {label}
        {showDeltaBadge ? (
          <span className="graph-review-pill-delta-badge">{deltaLabel ?? normalizedDeltaStatus}</span>
        ) : null}
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
        {deltaStatus && showDeltaBadge ? (
          <PlanningScanSection title="Graph review delta">
            <small>{deltaSummary ?? deltaLabel ?? deltaStatus}</small>
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

function SuggestedExpansionChip({
  expansion,
  targetNode,
  onSelect,
}: {
  expansion: GraphProjectionSuggestedExpansion;
  targetNode?: GraphProjectionNodeView;
  onSelect: (nodeId: string) => void;
}) {
  const targetPresentation = targetNode ? buildRecapNodePresentation(targetNode) : null;
  const role = targetNode?.role || targetNode?.kind || "node";
  return (
    <li className="graph-explorer-expansion-item" data-focus={expansion.anchored_to_focus_session}>
      <button
        type="button"
        className={`graph-explorer-expansion-chip role-${roleClass(role)}`}
        onClick={() => onSelect(expansion.node_id)}
      >
        <span className="graph-explorer-expansion-rank">{expansion.rank}</span>
        <span className="graph-explorer-expansion-body">
          <strong>{expansion.label}</strong>
          <span>{expansionPresentationLabel(expansion)}</span>
          <em className="graph-explorer-expansion-reason">
            {expansionRankReasonLabel(expansion.rank_reason)}
          </em>
        </span>
        {targetPresentation?.whyNow ? (
          <small className="graph-explorer-expansion-why">{targetPresentation.whyNow}</small>
        ) : null}
      </button>
    </li>
  );
}

export function GraphNodeExplorer({
  node,
  nodeViews,
  trail,
  onBack,
  onClose,
  onExpand,
  onEvidenceSelect,
  selectedEvidenceSpanId,
}: {
  node: GraphProjectionNodeView;
  nodeViews: Record<string, GraphProjectionNodeView>;
  trail: string[];
  onBack: () => void;
  onClose: () => void;
  onExpand: (nodeId: string) => void;
  onEvidenceSelect?: (badge: GraphProjectionEvidenceBadge) => void;
  selectedEvidenceSpanId?: string | null;
}) {
  const [showAllExpansions, setShowAllExpansions] = useState(false);
  const presentation = buildRecapNodePresentation(node);
  const focusEvidence = node.evidence_badges.filter((badge) => badge.is_focus_session_evidence);
  const contextEvidence = node.evidence_badges.filter((badge) => !badge.is_focus_session_evidence);
  const expansions =
    node.suggested_expansions?.length
      ? node.suggested_expansions
      : node.adjacency.map((candidate, index) => ({
          ...candidate,
          rank: index + 1,
          rank_reason: candidate.anchored_to_focus_session ? "current session" : "connected thread",
        }));
  const visibleExpansions = showAllExpansions
    ? expansions
    : expansions.slice(0, DEFAULT_SUGGESTED_EXPANSION_DISPLAY_CAP);
  const hiddenCount = expansions.length - DEFAULT_SUGGESTED_EXPANSION_DISPLAY_CAP;

  return (
    <aside
      className="graph-node-explorer union-supergraph-node-panel"
      aria-label="Graph node explorer"
    >
      <header className="graph-explorer-header">
        <div className="graph-explorer-nav">
          {trail.length > 1 ? (
            <button type="button" className="graph-explorer-back" onClick={onBack}>
              Back
            </button>
          ) : null}
          <button type="button" className="graph-explorer-close" onClick={onClose}>
            Close
          </button>
        </div>
        {trail.length > 1 ? (
          <nav className="graph-explorer-breadcrumb" aria-label="Explorer trail">
            {trail.map((nodeId, index) => {
              const trailNode = nodeViews[nodeId];
              const trailLabel = trailNode?.label ?? nodeId;
              return (
                <span key={nodeId}>
                  {index > 0 ? <span className="graph-explorer-breadcrumb-sep">→</span> : null}
                  <span
                    className={
                      index === trail.length - 1 ? "graph-explorer-breadcrumb-current" : ""
                    }
                  >
                    {trailLabel}
                  </span>
                </span>
              );
            })}
          </nav>
        ) : null}
      </header>

      <article
        className={`graph-explorer-expanded-chip role-${roleClass(node.role || node.kind)}`}
      >
        <p className="plan-surface-kicker">Expanded chip</p>
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
      </article>

      {focusEvidence.length ? (
        <section className="union-supergraph-evidence-group" aria-label="Current session evidence">
          <h4>Current session</h4>
          <ul>
            {focusEvidence.map((badge) => (
              <EvidenceBadgeRow key={badge.evidence_ref_id} badge={badge} onSelect={onEvidenceSelect} selected={badge.source_span_ref_id === selectedEvidenceSpanId} />
            ))}
          </ul>
        </section>
      ) : null}

      {contextEvidence.length ? (
        <section className="union-supergraph-evidence-group" aria-label="Prior context evidence">
          <h4>Prior context</h4>
          <ul>
            {contextEvidence.map((badge) => (
              <EvidenceBadgeRow key={badge.evidence_ref_id} badge={badge} onSelect={onEvidenceSelect} selected={badge.source_span_ref_id === selectedEvidenceSpanId} />
            ))}
          </ul>
        </section>
      ) : null}

      {expansions.length ? (
        <section className="graph-explorer-expansions" aria-label="Suggested expansions">
          <h4>Suggested expansions</h4>
          <ul className="graph-explorer-expansion-list">
            {visibleExpansions.map((expansion) => (
              <SuggestedExpansionChip
                key={expansion.edge_id}
                expansion={expansion}
                targetNode={nodeViews[expansion.node_id]}
                onSelect={onExpand}
              />
            ))}
          </ul>
          {!showAllExpansions && hiddenCount > 0 ? (
            <button
              type="button"
              className="graph-explorer-show-all"
              onClick={() => setShowAllExpansions(true)}
            >
              Show all {expansions.length} connections
            </button>
          ) : null}
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
