import type { GraphProjectionNodeView } from "../api/types";
import { presentationForNodeId, roleClass } from "./presentation";
import type { GraphNodeChipDeltaPresentation } from "./types";

const ROLE_CLASS_RE = /\brole-[a-z0-9_-]+\b/g;
const DELTA_CLASS_RE = /\bdelta-[a-z0-9_-]+\b/g;

export interface PaintGraphNodePillsOptions {
  nodeViews: Record<string, GraphProjectionNodeView>;
  activeNodeId: string | null;
  deltaByNodeId?: Record<string, GraphNodeChipDeltaPresentation>;
}

/**
 * Decorate native TipTap `button[data-graph-node-id]` pills with role / delta /
 * pinned classes. Avoids mounting a React NodeView per mention.
 */
export function paintGraphNodePills(
  root: ParentNode | null | undefined,
  options: PaintGraphNodePillsOptions,
): number {
  if (!root) {
    return 0;
  }

  const buttons = root.querySelectorAll<HTMLButtonElement>("button[data-graph-node-id]");
  for (const button of buttons) {
    const nodeId = button.dataset.graphNodeId?.trim();
    if (!nodeId) {
      continue;
    }

    const labelText = readPillLabel(button) || nodeId;
    const presentation = presentationForNodeId(options.nodeViews, nodeId, labelText);
    const role = presentation.role || presentation.kind || "node";
    const delta = options.deltaByNodeId?.[nodeId];
    const deltaStatus = delta?.status ?? "unclassified";
    const showDeltaBadge =
      deltaStatus !== "unknown"
      && deltaStatus !== "matched"
      && deltaStatus !== "unclassified";
    const focusSession = presentation.planningChips.some((chip) => chip.tone === "evidence");

    let className = button.className
      .replace(ROLE_CLASS_RE, "")
      .replace(DELTA_CLASS_RE, "")
      .replace(/\s+/g, " ")
      .trim();
    if (!/\brecap-node-token\b/.test(className)) {
      className = `${className} recap-node-token`.trim();
    }
    className = `${className} role-${roleClass(role)} delta-${deltaStatus}`.replace(/\s+/g, " ").trim();
    button.className = className;
    button.classList.toggle("pinned", options.activeNodeId === nodeId);
    button.classList.toggle("session-active", focusSession);
    button.dataset.deltaStatus = deltaStatus;

    ensureLabelText(button, labelText);
    ensureDeltaBadge(button, showDeltaBadge ? (delta?.label ?? deltaStatus) : null);
  }

  return buttons.length;
}

function readPillLabel(button: HTMLButtonElement): string {
  const badge = button.querySelector(".graph-review-pill-delta-badge");
  if (!badge) {
    return button.textContent?.trim() ?? "";
  }
  const clone = button.cloneNode(true) as HTMLElement;
  clone.querySelector(".graph-review-pill-delta-badge")?.remove();
  return clone.textContent?.trim() ?? "";
}

function ensureLabelText(button: HTMLButtonElement, label: string): void {
  const badge = button.querySelector(".graph-review-pill-delta-badge");
  const textNodes = Array.from(button.childNodes).filter(
    (node) => node.nodeType === Node.TEXT_NODE,
  );
  if (textNodes.length === 0) {
    button.insertBefore(document.createTextNode(label), badge);
    return;
  }
  textNodes[0]!.textContent = label;
  for (const extra of textNodes.slice(1)) {
    extra.remove();
  }
}

function ensureDeltaBadge(button: HTMLButtonElement, label: string | null): void {
  let badge = button.querySelector<HTMLSpanElement>(".graph-review-pill-delta-badge");
  if (!label) {
    badge?.remove();
    return;
  }
  if (!badge) {
    badge = document.createElement("span");
    badge.className = "graph-review-pill-delta-badge";
    button.appendChild(badge);
  }
  badge.textContent = label;
}
