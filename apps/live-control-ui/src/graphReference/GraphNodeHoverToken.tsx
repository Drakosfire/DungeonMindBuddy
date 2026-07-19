import type { ReactNode } from "react";

import { presentationForNodeId, roleClass } from "./presentation";
import type { GraphNodeGlancePresentation } from "./types";
import "./graphReference.css";

/** Tiny CSS glance: keep thread list short so hover stays scannable. */
const MAX_GLANCE_THREADS = 2;
const MAX_THREAD_LABEL_CHARS = 72;

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

function typeLabel(role: string, kind: string): string | null {
  const normalizedRole = role.trim();
  const normalizedKind = kind.trim();
  if (!normalizedRole && !normalizedKind) {
    return null;
  }
  if (!normalizedRole) {
    return normalizedKind;
  }
  if (!normalizedKind || normalizedRole.toLowerCase() === normalizedKind.toLowerCase()) {
    return normalizedRole;
  }
  return `${normalizedRole} · ${normalizedKind}`;
}

function truncateThreadLabel(label: string): string {
  const trimmed = label.trim();
  if (trimmed.length <= MAX_THREAD_LABEL_CHARS) {
    return trimmed;
  }
  return `${trimmed.slice(0, MAX_THREAD_LABEL_CHARS - 1).trimEnd()}…`;
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
  const glanceType = typeLabel(presentation.role, presentation.kind);
  const glanceThreads = presentation.threadHints.slice(0, MAX_GLANCE_THREADS);

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
        {glanceType ? <span className="recap-node-kind">{glanceType}</span> : null}
        {presentation.summary ? (
          <small className="recap-planning-summary">{presentation.summary}</small>
        ) : null}
        {presentation.whyNow ? (
          <PlanningScanSection title="Why now">
            <small>{presentation.whyNow}</small>
          </PlanningScanSection>
        ) : null}
        {deltaStatus && showDeltaBadge ? (
          <PlanningScanSection title="Graph review delta">
            <small>{deltaSummary ?? deltaLabel ?? deltaStatus}</small>
          </PlanningScanSection>
        ) : null}
        {glanceThreads.length ? (
          <PlanningScanSection title="Threads">
            <ul className="recap-planning-thread-list">
              {glanceThreads.map((hint) => (
                <li key={`${presentation.nodeId}:${hint.nodeId}`}>
                  {truncateThreadLabel(hint.edgeLabel)}
                </li>
              ))}
            </ul>
          </PlanningScanSection>
        ) : null}
      </span>
    </span>
  );
}

export { presentationForNodeId };
