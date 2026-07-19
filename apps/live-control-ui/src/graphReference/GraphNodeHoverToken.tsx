import type { ReactNode } from "react";

import { presentationForNodeId, roleClass } from "./presentation";
import type { GraphNodeGlancePresentation } from "./types";
import "./graphReference.css";

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

export interface GraphNodeHoverTokenProps {
  presentation: GraphNodeGlancePresentation;
  label: string;
  pinned: boolean;
  onSelect: () => void;
  deltaStatus?: string;
  deltaLabel?: string;
  deltaSummary?: string | null;
  tokenClassName?: string;
  counterpartHighlighted?: boolean;
  /** Extra button attrs (e.g. Plan md-ref-chip data attributes). */
  buttonProps?: Record<string, string | undefined>;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
  onFocus?: () => void;
  onBlur?: () => void;
}

export function GraphNodeHoverToken({
  presentation,
  label,
  pinned,
  onSelect,
  deltaStatus,
  deltaLabel,
  deltaSummary,
  tokenClassName,
  counterpartHighlighted = false,
  buttonProps,
  onMouseEnter,
  onMouseLeave,
  onFocus,
  onBlur,
}: GraphNodeHoverTokenProps) {
  const role = presentation.role || presentation.kind || "node";
  const focusSession = presentation.planningChips.some((chip) => chip.tone === "evidence");
  const normalizedDeltaStatus = deltaStatus ?? "unclassified";
  const showDeltaBadge =
    normalizedDeltaStatus !== "unknown"
    && normalizedDeltaStatus !== "matched"
    && normalizedDeltaStatus !== "unclassified";

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
        {...buttonProps}
        contentEditable={false}
        onClick={(event) => {
          event.stopPropagation();
          onSelect();
        }}
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

export { presentationForNodeId };
