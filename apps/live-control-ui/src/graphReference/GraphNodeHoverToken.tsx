import { useId, useLayoutEffect, useRef, useState } from "react";

import { ThreatCampaignGlance } from "../statblocks/projection/ThreatCampaignGlance";
import { useThreatHoverMechanics } from "../statblocks/projection/ThreatHoverMechanics";
import { isThreatHoverPresentation } from "../statblocks/projection/threatSheetViewModel";
import {
  readBottomObstacleTop,
  resolveGlancePlacement,
  type GlancePlacement,
} from "./glancePlacement";
import { useGraphNodeChipRuntime } from "./GraphNodeChipRuntime";
import { presentationForNodeId, roleClass } from "./presentation";
import type { GraphNodeGlancePresentation } from "./types";
import "./graphReference.css";
import "../statblocks/projection/threatSheetProjection.css";

function typeLabel(role: string, kind: string): string | null {
  const displayType = (value: string) => {
    const normalized = value.trim().toLowerCase();
    if (normalized === "pc" || normalized === "player_character") {
      return "PC";
    }
    if (normalized === "npc" || normalized === "non_player_character") {
      return "NPC";
    }
    return value.replace(/_/g, " ").trim();
  };
  const normalizedRole = displayType(role);
  const normalizedKind = displayType(kind);
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

function measureGlancePlacement(
  wrap: HTMLElement,
  card: HTMLElement,
): GlancePlacement {
  card.dataset.measuring = "true";
  const tokenRect = wrap.getBoundingClientRect();
  const cardHeight = card.getBoundingClientRect().height;
  delete card.dataset.measuring;

  return resolveGlancePlacement({
    tokenTop: tokenRect.top,
    tokenBottom: tokenRect.bottom,
    cardHeight,
    viewportHeight: window.innerHeight,
    obstacleTop: readBottomObstacleTop(),
  });
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
  tokenClassName,
  counterpartHighlighted = false,
  buttonProps,
  onMouseEnter,
  onMouseLeave,
  onFocus,
  onBlur,
}: GraphNodeHoverTokenProps) {
  const glanceId = useId();
  const wrapRef = useRef<HTMLSpanElement>(null);
  const cardRef = useRef<HTMLSpanElement>(null);
  const [glance, setGlance] = useState<{ open: boolean; placement: GlancePlacement }>({
    open: false,
    placement: "below",
  });
  const { open, placement } = glance;

  const role = presentation.role || presentation.kind || "node";
  const focusSession = presentation.planningChips.some((chip) => chip.tone === "evidence");
  const normalizedDeltaStatus = deltaStatus ?? "unclassified";
  const showDeltaBadge =
    normalizedDeltaStatus !== "unknown"
    && normalizedDeltaStatus !== "matched"
    && normalizedDeltaStatus !== "unclassified";
  const glanceType = typeLabel(presentation.role, presentation.kind);
  const threatHover = isThreatHoverPresentation(presentation);
  const { exactGraphScope } = useGraphNodeChipRuntime();
  const threatMechanics = useThreatHoverMechanics(
    open && threatHover,
    presentation.nodeId,
    exactGraphScope,
  );

  const activate = () => {
    const wrap = wrapRef.current;
    const card = cardRef.current;
    // Measure while hidden, then open already on the correct side — no below→above flash.
    const nextPlacement =
      wrap && card ? measureGlancePlacement(wrap, card) : "below";
    setGlance({ open: true, placement: nextPlacement });
  };

  const deactivate = () => {
    setGlance({ open: false, placement: "below" });
  };

  useLayoutEffect(() => {
    if (!open) {
      return;
    }
    const wrap = wrapRef.current;
    const card = cardRef.current;
    if (!wrap || !card) {
      return;
    }

    const recompute = () => {
      setGlance((current) => ({
        ...current,
        placement: measureGlancePlacement(wrap, card),
      }));
    };

    window.addEventListener("resize", recompute);
    window.addEventListener("scroll", recompute, true);
    return () => {
      window.removeEventListener("resize", recompute);
      window.removeEventListener("scroll", recompute, true);
    };
  }, [open]);

  return (
    <span
      ref={wrapRef}
      className={`recap-node-token-wrap recap-node-glance${
        placement === "above" ? " recap-node-glance--above" : ""
      }`}
      data-open={open ? "true" : "false"}
      onMouseEnter={() => {
        activate();
        onMouseEnter?.();
      }}
      onMouseLeave={() => {
        deactivate();
        onMouseLeave?.();
      }}
      onFocus={() => {
        activate();
        onFocus?.();
      }}
      onBlur={() => {
        deactivate();
        onBlur?.();
      }}
    >
      <button
        type="button"
        className={`recap-node-token role-${roleClass(role)} delta-${normalizedDeltaStatus}${pinned ? " pinned" : ""}${focusSession ? " session-active" : ""}${counterpartHighlighted ? " counterpart-highlighted" : ""}${tokenClassName ? ` ${tokenClassName}` : ""}`}
        data-graph-node-id={presentation.nodeId}
        data-delta-status={normalizedDeltaStatus}
        data-counterpart-highlighted={counterpartHighlighted ? "true" : undefined}
        aria-describedby={open ? glanceId : undefined}
        {...buttonProps}
        contentEditable={false}
        onClick={(event) => {
          event.stopPropagation();
          deactivate();
          onSelect();
        }}
      >
        {label}
        {showDeltaBadge ? (
          <span className="graph-review-pill-delta-badge">{deltaLabel ?? normalizedDeltaStatus}</span>
        ) : null}
      </button>
      <span
        ref={cardRef}
        id={glanceId}
        className={`recap-node-hover-card recap-planning-card${
          threatHover ? " recap-node-hover-card--threat" : ""
        }`}
        role="tooltip"
        data-placement={placement}
        data-threat-hover={threatHover ? "true" : "false"}
      >
        {threatHover ? (
          <div className="plan-reference-object-card plan-reference-object-card--threat-sheet threat-sheet-hover-shell">
            <ThreatCampaignGlance
              label={presentation.label || label}
              threatKind={presentation.kind}
              intendedRole={presentation.role}
              summary={presentation.summary}
              loadStatus={threatMechanics.loadStatus}
              compactBinding={threatMechanics.compactBinding}
              availableCount={threatMechanics.availableCount}
              bindingCount={threatMechanics.bindingCount}
              variant="hover"
            />
          </div>
        ) : (
          <>
            <strong className="recap-node-glance-title">{presentation.label || label}</strong>
            {glanceType ? <span className="recap-node-kind">{glanceType}</span> : null}
            {presentation.summary ? (
              <small className="recap-planning-summary">{presentation.summary}</small>
            ) : null}
            {presentation.whyNow ? (
              <div className="recap-node-glance-context">
                <span>Why it matters here</span>
                <small>{presentation.whyNow}</small>
              </div>
            ) : null}
          </>
        )}
      </span>
    </span>
  );
}

export { presentationForNodeId };
