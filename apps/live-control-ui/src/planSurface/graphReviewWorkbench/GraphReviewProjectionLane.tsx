import type { ReactNode } from "react";
import type {
  GraphProjectionNodeView,
  RecapProjectionSourceSpan,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
import { presentationForNodeId } from "../graphPreview/GraphNodePresentation";
import type {
  GraphReviewDeltaIndex,
  GraphReviewDeltaStatus,
} from "./graphReviewDeltaTypes";

export type GraphReviewProjectionLaneRole = "gold" | "live";

type ProjectionMention =
  UnionSupergraphProjectionResponse["mentions"][number] & {
    anchor_status?: string | null;
  };

interface GraphReviewProjectionLaneProps {
  laneRole: GraphReviewProjectionLaneRole;
  title: string;
  subtitle?: string;
  markdown: string;
  nodeViews: Record<string, GraphProjectionNodeView>;
  sourceSpans?: RecapProjectionSourceSpan[];
  mentions: ProjectionMention[];
  mentionsCount: number;
  deltaIndex: GraphReviewDeltaIndex;
  activeObject: {
    laneRole: GraphReviewProjectionLaneRole;
    nodeId: string;
  } | null;
  onActiveObjectChange: (
    active: { laneRole: GraphReviewProjectionLaneRole; nodeId: string } | null,
  ) => void;
  onSelectObject?: (selection: { laneRole: GraphReviewProjectionLaneRole; nodeId: string }) => void;
}

interface NodeDecoration {
  status: GraphReviewDeltaStatus | "unknown";
  label: string;
  summary: string | null;
  counterpartNodeId: string | null;
}

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

function isAnchoredMention(mention: ProjectionMention): boolean {
  if (mention.anchor_status && mention.anchor_status !== "anchored")
    return false;
  return (
    typeof mention.start_offset === "number" &&
    typeof mention.end_offset === "number" &&
    mention.end_offset > mention.start_offset
  );
}

function renderMentionToken({
  laneRole,
  nodeViews,
  decorations,
  activeObject,
  onActiveObjectChange,
  propsOnSelectObject,
  nodeId,
  label,
  key,
}: {
  laneRole: GraphReviewProjectionLaneRole;
  nodeViews: Record<string, GraphProjectionNodeView>;
  decorations: Record<string, NodeDecoration>;
  activeObject: GraphReviewProjectionLaneProps["activeObject"];
  onActiveObjectChange: GraphReviewProjectionLaneProps["onActiveObjectChange"];
  propsOnSelectObject?: (selection: { laneRole: GraphReviewProjectionLaneRole; nodeId: string }) => void;
  nodeId: string;
  label: string;
  key: string;
}) {
  const decoration = decorations[nodeId] ?? {
    status: "unknown" as const,
    label: "Unknown",
    summary: null,
    counterpartNodeId: null,
  };
  const presentation = presentationForNodeId(nodeViews, nodeId, label);
  const counterpartHighlighted =
    activeObject?.laneRole !== laneRole && activeObject?.nodeId === nodeId;
  const activeHere =
    activeObject?.laneRole === laneRole && activeObject?.nodeId === nodeId;
  return (
    <button
      key={key}
      type="button"
      className={`recap-node-token graph-review-projection-token role-${presentation.role || presentation.kind || "node"} delta-${decoration.status}${activeHere ? " pinned" : ""}${counterpartHighlighted ? " counterpart-highlighted" : ""}`}
      data-graph-node-id={nodeId}
      data-delta-status={decoration.status}
      data-counterpart-highlighted={counterpartHighlighted ? "true" : undefined}
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
      onClick={() => propsOnSelectObject?.({ laneRole, nodeId })}
    >
      {label}
      {decoration.status !== "unknown" ? (
        <span className="graph-review-pill-delta-badge">
          {decoration.label}
        </span>
      ) : null}
    </button>
  );
}

function renderInlineRange(
  text: string,
  rangeStart: number,
  rangeEnd: number,
  mentions: ProjectionMention[],
  laneRole: GraphReviewProjectionLaneRole,
  nodeViews: Record<string, GraphProjectionNodeView>,
  decorations: Record<string, NodeDecoration>,
  activeObject: GraphReviewProjectionLaneProps["activeObject"],
  onActiveObjectChange: GraphReviewProjectionLaneProps["onActiveObjectChange"],
  propsOnSelectObject?: (selection: { laneRole: GraphReviewProjectionLaneRole; nodeId: string }) => void,
) {
  const parts: ReactNode[] = [];
  const anchoredMentions = mentions
    .filter((mention) => isAnchoredMention(mention))
    .filter(
      (mention) =>
        mention.start_offset! >= rangeStart && mention.end_offset! <= rangeEnd,
    )
    .sort(
      (left, right) =>
        left.start_offset! - right.start_offset! ||
        left.end_offset! - right.end_offset!,
    );

  let cursor = rangeStart;
  for (const mention of anchoredMentions) {
    const start = mention.start_offset!;
    const end = mention.end_offset!;
    if (start < cursor) continue;
    if (start > cursor)
      parts.push(
        <span key={`t-${cursor}`}>
          {text.slice(cursor - rangeStart, start - rangeStart)}
        </span>,
      );
    const fallbackLabel = text.slice(start - rangeStart, end - rangeStart);
    parts.push(
      renderMentionToken({
        laneRole,
        nodeViews,
        decorations,
        activeObject,
        onActiveObjectChange,
        propsOnSelectObject,
        nodeId: mention.node_id,
        label: mention.label || fallbackLabel,
        key: mention.mention_id || `${mention.node_id}-${start}`,
      }),
    );
    cursor = end;
  }

  if (cursor < rangeEnd)
    parts.push(
      <span key={`t-${cursor}`}>
        {text.slice(cursor - rangeStart, rangeEnd - rangeStart)}
      </span>,
    );
  return parts;
}

function renderMarkdownBlocks(
  props: GraphReviewProjectionLaneProps,
  decorations: Record<string, NodeDecoration>,
) {
  const markdown = props.markdown;
  const blocks: ReactNode[] = [];
  const blockPattern = /\S[\s\S]*?(?=\n{2,}|$)/g;
  for (const match of markdown.matchAll(blockPattern)) {
    const rawBlock = match[0];
    const blockStart = match.index ?? 0;
    const leadingWhitespace = rawBlock.match(/^\s*/)?.[0].length ?? 0;
    const trailingWhitespace = rawBlock.match(/\s*$/)?.[0].length ?? 0;
    const start = blockStart + leadingWhitespace;
    const end = blockStart + rawBlock.length - trailingWhitespace;
    const trimmed = markdown.slice(start, end);
    if (!trimmed) continue;
    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      const level = heading[1].length;
      const contentStart = start + heading[1].length + 1;
      const content = renderInlineRange(
        markdown.slice(contentStart, end),
        contentStart,
        end,
        props.mentions,
        props.laneRole,
        props.nodeViews,
        decorations,
        props.activeObject,
        props.onActiveObjectChange,
        props.onSelectObject,
      );
      if (level === 1) blocks.push(<h2 key={start}>{content}</h2>);
      else if (level === 2) blocks.push(<h3 key={start}>{content}</h3>);
      else blocks.push(<h4 key={start}>{content}</h4>);
      continue;
    }
    blocks.push(
      <p key={start}>
        {renderInlineRange(
          markdown.slice(start, end),
          start,
          end,
          props.mentions,
          props.laneRole,
          props.nodeViews,
          decorations,
          props.activeObject,
          props.onActiveObjectChange,
          props.onSelectObject,
        )}
      </p>,
    );
  }
  return blocks;
}

export function GraphReviewProjectionLane(
  props: GraphReviewProjectionLaneProps,
) {
  const decorations = buildNodeDecorations(props.deltaIndex, props.laneRole);
  const unanchoredCount = props.mentions.filter(
    (mention) => !isAnchoredMention(mention),
  ).length;
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
