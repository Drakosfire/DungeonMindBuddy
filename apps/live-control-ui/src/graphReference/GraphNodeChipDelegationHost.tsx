import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import { createPortal } from "react-dom";

import type { GraphProjectionNodeView } from "../api/types";
import {
  readBottomObstacleTop,
  resolveGlancePlacement,
  type GlancePlacement,
} from "./glancePlacement";
import { paintGraphNodePills } from "./paintGraphNodePills";
import { presentationForNodeId } from "./presentation";
import type { GraphNodeChipDeltaPresentation, GraphNodeGlancePresentation } from "./types";
import "./graphReference.css";

const MAX_GLANCE_THREADS = 2;
const MAX_THREAD_LABEL_CHARS = 72;

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

interface ActiveGlance {
  nodeId: string;
  label: string;
  presentation: GraphNodeGlancePresentation;
  placement: GlancePlacement;
  left: number;
  top: number;
  width: number;
  deltaStatus?: string;
  deltaLabel?: string;
  deltaSummary?: string | null;
}

export interface GraphNodeChipDelegationHostProps {
  rootRef: RefObject<HTMLElement | null>;
  /** Re-paint when TipTap content / source-span overlays change. */
  contentEpoch?: string | number | null;
  nodeViews: Record<string, GraphProjectionNodeView>;
  activeNodeId: string | null;
  deltaByNodeId?: Record<string, GraphNodeChipDeltaPresentation>;
  onSelectNode: (nodeId: string) => void;
  children: ReactNode;
}

/**
 * One event-delegation host for all recap graph pills: click + shared hover glance.
 * Pair with TipTap `GraphNodeReferenceNode` that uses native `renderHTML` (no React NodeViews).
 */
export function GraphNodeChipDelegationHost({
  rootRef,
  contentEpoch,
  nodeViews,
  activeNodeId,
  deltaByNodeId,
  onSelectNode,
  children,
}: GraphNodeChipDelegationHostProps) {
  const [glance, setGlance] = useState<ActiveGlance | null>(null);
  const cardRef = useRef<HTMLSpanElement>(null);
  const activeTokenRef = useRef<HTMLButtonElement | null>(null);
  const nodeViewsRef = useRef(nodeViews);
  nodeViewsRef.current = nodeViews;
  const deltaRef = useRef(deltaByNodeId);
  deltaRef.current = deltaByNodeId;
  const onSelectNodeRef = useRef(onSelectNode);
  onSelectNodeRef.current = onSelectNode;

  useEffect(() => {
    paintGraphNodePills(rootRef.current, {
      nodeViews,
      activeNodeId,
      deltaByNodeId,
    });
  }, [rootRef, nodeViews, activeNodeId, deltaByNodeId, contentEpoch]);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) {
      return;
    }

    const resolveButton = (target: EventTarget | null): HTMLButtonElement | null => {
      if (!(target instanceof Element)) {
        return null;
      }
      const button = target.closest("button[data-graph-node-id]");
      if (!(button instanceof HTMLButtonElement) || !root.contains(button)) {
        return null;
      }
      return button;
    };

    const openGlanceFor = (button: HTMLButtonElement) => {
      const nodeId = button.dataset.graphNodeId?.trim();
      if (!nodeId) {
        return;
      }
      activeTokenRef.current = button;
      const label = button.textContent?.replace(/\s+/g, " ").trim() || nodeId;
      // Strip delta badge text from label if present.
      const badge = button.querySelector(".graph-review-pill-delta-badge");
      const cleanLabel = badge
        ? Array.from(button.childNodes)
            .filter((node) => node.nodeType === Node.TEXT_NODE)
            .map((node) => node.textContent ?? "")
            .join("")
            .trim() || nodeId
        : label;
      const presentation = presentationForNodeId(nodeViewsRef.current, nodeId, cleanLabel);
      const delta = deltaRef.current?.[nodeId];
      const rect = button.getBoundingClientRect();
      setGlance({
        nodeId,
        label: cleanLabel,
        presentation,
        placement: "below",
        left: rect.left,
        top: rect.bottom,
        width: rect.width,
        deltaStatus: delta?.status,
        deltaLabel: delta?.label,
        deltaSummary: delta?.summary,
      });
    };

    const closeGlance = () => {
      activeTokenRef.current = null;
      setGlance(null);
    };

    const onClick = (event: MouseEvent) => {
      const button = resolveButton(event.target);
      if (!button) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      const nodeId = button.dataset.graphNodeId?.trim();
      if (nodeId) {
        onSelectNodeRef.current(nodeId);
      }
    };

    const onPointerOver = (event: PointerEvent) => {
      const button = resolveButton(event.target);
      if (!button) {
        return;
      }
      if (activeTokenRef.current === button) {
        return;
      }
      openGlanceFor(button);
    };

    const onPointerOut = (event: PointerEvent) => {
      const button = resolveButton(event.target);
      if (!button || activeTokenRef.current !== button) {
        return;
      }
      const related = event.relatedTarget;
      if (related instanceof Node && (button.contains(related) || cardRef.current?.contains(related))) {
        return;
      }
      closeGlance();
    };

    const onFocusIn = (event: FocusEvent) => {
      const button = resolveButton(event.target);
      if (button) {
        openGlanceFor(button);
      }
    };

    const onFocusOut = (event: FocusEvent) => {
      const button = resolveButton(event.target);
      if (!button || activeTokenRef.current !== button) {
        return;
      }
      const related = event.relatedTarget;
      if (related instanceof Node && (button.contains(related) || cardRef.current?.contains(related))) {
        return;
      }
      closeGlance();
    };

    root.addEventListener("click", onClick);
    root.addEventListener("pointerover", onPointerOver);
    root.addEventListener("pointerout", onPointerOut);
    root.addEventListener("focusin", onFocusIn);
    root.addEventListener("focusout", onFocusOut);
    return () => {
      root.removeEventListener("click", onClick);
      root.removeEventListener("pointerover", onPointerOver);
      root.removeEventListener("pointerout", onPointerOut);
      root.removeEventListener("focusin", onFocusIn);
      root.removeEventListener("focusout", onFocusOut);
    };
  }, [rootRef]);

  useLayoutEffect(() => {
    if (!glance || !cardRef.current || !activeTokenRef.current) {
      return;
    }
    const token = activeTokenRef.current;
    const card = cardRef.current;
    card.dataset.measuring = "true";
    const tokenRect = token.getBoundingClientRect();
    const cardHeight = card.getBoundingClientRect().height;
    delete card.dataset.measuring;
    const placement = resolveGlancePlacement({
      tokenTop: tokenRect.top,
      tokenBottom: tokenRect.bottom,
      cardHeight,
      viewportHeight: window.innerHeight,
      obstacleTop: readBottomObstacleTop(),
    });
    const nextTop = placement === "above" ? tokenRect.top : tokenRect.bottom;
    setGlance((current) => {
      if (!current || current.nodeId !== glance.nodeId) {
        return current;
      }
      if (
        current.placement === placement
        && current.left === tokenRect.left
        && current.top === nextTop
        && current.width === tokenRect.width
      ) {
        return current;
      }
      return {
        ...current,
        placement,
        left: tokenRect.left,
        top: nextTop,
        width: tokenRect.width,
      };
    });
  }, [glance?.nodeId, glance?.presentation.nodeId]);

  const glancePortal =
    glance && typeof document !== "undefined"
      ? createPortal(
          <span
            className={`recap-node-token-wrap recap-node-glance graph-node-chip-shared-glance${
              glance.placement === "above" ? " recap-node-glance--above" : ""
            }`}
            data-open="true"
            data-testid="graph-node-chip-shared-glance"
            style={{
              position: "fixed",
              left: glance.left,
              top: glance.placement === "above" ? undefined : glance.top,
              bottom:
                glance.placement === "above"
                  ? `${window.innerHeight - glance.top}px`
                  : undefined,
              width: Math.max(glance.width, 1),
              zIndex: 60,
              pointerEvents: "none",
            }}
          >
            <span
              ref={cardRef}
              className="recap-node-hover-card recap-planning-card"
              role="tooltip"
              data-placement={glance.placement}
            >
              {(() => {
                const glanceType = typeLabel(
                  glance.presentation.role,
                  glance.presentation.kind,
                );
                const threads = glance.presentation.threadHints.slice(0, MAX_GLANCE_THREADS);
                const normalizedDeltaStatus = glance.deltaStatus ?? "unclassified";
                const showDeltaBadge =
                  normalizedDeltaStatus !== "unknown"
                  && normalizedDeltaStatus !== "matched"
                  && normalizedDeltaStatus !== "unclassified";
                return (
                  <>
                    {glanceType ? (
                      <span className="recap-node-kind">{glanceType}</span>
                    ) : null}
                    {glance.presentation.summary ? (
                      <small className="recap-planning-summary">
                        {glance.presentation.summary}
                      </small>
                    ) : null}
                    {glance.presentation.whyNow ? (
                      <PlanningScanSection title="Why now">
                        <small>{glance.presentation.whyNow}</small>
                      </PlanningScanSection>
                    ) : null}
                    {glance.deltaStatus && showDeltaBadge ? (
                      <PlanningScanSection title="Graph review delta">
                        <small>
                          {glance.deltaSummary ?? glance.deltaLabel ?? glance.deltaStatus}
                        </small>
                      </PlanningScanSection>
                    ) : null}
                    {threads.length ? (
                      <PlanningScanSection title="Threads">
                        <ul className="recap-planning-thread-list">
                          {threads.map((hint) => (
                            <li key={`${glance.nodeId}:${hint.nodeId}`}>
                              {truncateThreadLabel(hint.edgeLabel)}
                            </li>
                          ))}
                        </ul>
                      </PlanningScanSection>
                    ) : null}
                  </>
                );
              })()}
            </span>
          </span>,
          document.body,
        )
      : null;

  return (
    <>
      {children}
      {glancePortal}
    </>
  );
}
