import type { ReactNode } from "react";
import type {
  GraphProjectionNodeView,
  RecapProjectionSourceSpan,
} from "../../api/types";
import { presentationForNodeId } from "../graphPreview/GraphNodePresentation";
import type {
  GraphReviewDeltaIndex,
  GraphReviewDeltaStatus,
} from "./graphReviewDeltaTypes";

export type GraphReviewProjectionLaneRole = "gold" | "live";

interface GraphReviewProjectionLaneProps {
  laneRole: GraphReviewProjectionLaneRole;
  title: string;
  subtitle?: string;
  markdown: string;
  nodeViews: Record<string, GraphProjectionNodeView>;
  sourceSpans?: RecapProjectionSourceSpan[];
  mentionsCount: number;
  deltaIndex: GraphReviewDeltaIndex;
  activeObject: {
    laneRole: GraphReviewProjectionLaneRole;
    nodeId: string;
  } | null;
  onActiveObjectChange: (
    active: { laneRole: GraphReviewProjectionLaneRole; nodeId: string } | null,
  ) => void;
  onSelectNode?: (nodeId: string) => void;
}

interface NodeDecoration {
  status: GraphReviewDeltaStatus | "unknown";
  label: string;
  summary: string | null;
  counterpartNodeId: string | null;
}

const graphNodePattern = /\[([^\]]+)\]\(dmb-node:([^\)]+)\)/g;

function statusLabel(status: NodeDecoration["status"]): string {
  if (status === "gold_only") return "Gold-only";
  if (status === "live_only") return "Live-only";
  if (status === "comparator_uncertain") return "Uncertain";
  if (status === "matched") return "Matched";
  if (status.startsWith("changed_")) return "Changed";
  return "Unknown";
}

function buildNodeDecorations(
  deltaIndex: GraphReviewDeltaIndex,
  laneRole: GraphReviewProjectionLaneRole,
): Record<string, NodeDecoration> {
  const decorations: Record<string, NodeDecoration> = {};
  for (const delta of deltaIndex.deltas) {
    const laneRef = delta.laneObjectRefs.find(
      (ref) => ref.laneRole === laneRole && ref.objectKind === "node",
    );
    if (!laneRef) continue;
    const counterpartRole = laneRole === "gold" ? "live" : "gold";
    const counterpartRef = delta.laneObjectRefs.find(
      (ref) => ref.laneRole === counterpartRole && ref.objectKind === "node",
    );
    decorations[laneRef.objectId] = {
      status: delta.status,
      label: statusLabel(delta.status),
      summary: delta.summary,
      counterpartNodeId: counterpartRef?.objectId ?? null,
    };
  }
  return decorations;
}

function renderInline(
  text: string,
  laneRole: GraphReviewProjectionLaneRole,
  nodeViews: Record<string, GraphProjectionNodeView>,
  decorations: Record<string, NodeDecoration>,
  activeObject: GraphReviewProjectionLaneProps["activeObject"],
  onActiveObjectChange: GraphReviewProjectionLaneProps["onActiveObjectChange"],
  propsOnSelectNode?: (nodeId: string) => void,
) {
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  for (const match of text.matchAll(graphNodePattern)) {
    const index = match.index ?? 0;
    const [raw, label, nodeId] = match;
    if (index > lastIndex)
      parts.push(
        <span key={`t-${lastIndex}`}>{text.slice(lastIndex, index)}</span>,
      );
    const decoration = decorations[nodeId] ?? {
      status: "unknown",
      label: "Unknown",
      summary: null,
      counterpartNodeId: null,
    };
    const presentation = presentationForNodeId(nodeViews, nodeId, label);
    const counterpartHighlighted =
      activeObject?.laneRole !== laneRole && activeObject?.nodeId === nodeId;
    const activeHere =
      activeObject?.laneRole === laneRole && activeObject?.nodeId === nodeId;
    parts.push(
      <button
        key={`${nodeId}-${index}`}
        type="button"
        className={`recap-node-token graph-review-projection-token role-${presentation.role || presentation.kind || "node"} delta-${decoration.status}${activeHere ? " pinned" : ""}${counterpartHighlighted ? " counterpart-highlighted" : ""}`}
        data-graph-node-id={nodeId}
        data-delta-status={decoration.status}
        data-counterpart-highlighted={
          counterpartHighlighted ? "true" : undefined
        }
        onMouseEnter={() =>
          onActiveObjectChange({
            laneRole,
            nodeId: decoration.counterpartNodeId ?? nodeId,
          })
        }
        onMouseLeave={() => onActiveObjectChange(null)}
        onFocus={() =>
          onActiveObjectChange({
            laneRole,
            nodeId: decoration.counterpartNodeId ?? nodeId,
          })
        }
        onBlur={() => onActiveObjectChange(null)}
        onClick={() => propsOnSelectNode?.(nodeId)}
      >
        {label}
        {decoration.status !== "unknown" ? (
          <span className="graph-review-pill-delta-badge">
            {decoration.label}
          </span>
        ) : null}
      </button>,
    );
    lastIndex = index + raw.length;
  }
  if (lastIndex < text.length)
    parts.push(<span key={`t-${lastIndex}`}>{text.slice(lastIndex)}</span>);
  return parts;
}

function renderMarkdownBlocks(
  props: GraphReviewProjectionLaneProps,
  decorations: Record<string, NodeDecoration>,
) {
  return props.markdown.split(/\n{2,}/).map((block, index) => {
    const trimmed = block.trim();
    if (!trimmed) return null;
    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      const level = heading[1].length;
      const content = renderInline(
        heading[2],
        props.laneRole,
        props.nodeViews,
        decorations,
        props.activeObject,
        props.onActiveObjectChange,
        props.onSelectNode,
      );
      if (level === 1) return <h2 key={index}>{content}</h2>;
      if (level === 2) return <h3 key={index}>{content}</h3>;
      return <h4 key={index}>{content}</h4>;
    }
    return (
      <p key={index}>
        {renderInline(
          trimmed.replace(/\n/g, " "),
          props.laneRole,
          props.nodeViews,
          decorations,
          props.activeObject,
          props.onActiveObjectChange,
          props.onSelectNode,
        )}
      </p>
    );
  });
}

export function GraphReviewProjectionLane(
  props: GraphReviewProjectionLaneProps,
) {
  const decorations = buildNodeDecorations(props.deltaIndex, props.laneRole);
  const unanchoredCount = Math.max(
    0,
    props.mentionsCount - Object.keys(props.nodeViews).length,
  );
  return (
    <section
      className="graph-review-projection-lane"
      aria-label={props.title}
      data-lane-role={props.laneRole}
    >
      <header>
        <p className="plan-surface-kicker">
          {props.laneRole === "gold"
            ? "Gold Fixture · read-only"
            : "Live Run · read-only"}
        </p>
        <h3>{props.title}</h3>
        {props.subtitle ? <p>{props.subtitle}</p> : null}
        <span>
          {props.mentionsCount} projected graph mention
          {props.mentionsCount === 1 ? "" : "s"}
        </span>
      </header>
      {unanchoredCount ? (
        <p className="graph-review-projection-warning">
          {unanchoredCount} {props.laneRole} object
          {unanchoredCount === 1 ? " is" : "s are"} unanchored in this recap.
        </p>
      ) : null}
      <article
        className="graph-review-projection-document"
        data-testid={
          props.laneRole === "live" ? "graph-projection-reader" : undefined
        }
      >
        {renderMarkdownBlocks(props, decorations)}
      </article>
    </section>
  );
}
