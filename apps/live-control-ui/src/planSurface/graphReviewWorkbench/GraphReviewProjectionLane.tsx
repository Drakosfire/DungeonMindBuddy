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
import { stripLeadingYamlFrontmatter } from "../graphProjectionReader/projectionMarkdownPreprocessing";

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
  onSelectObject?: (selection: {
    laneRole: GraphReviewProjectionLaneRole;
    nodeId: string;
  }) => void;
  onSelectText?: (selection: {
    laneRole: GraphReviewProjectionLaneRole;
    text: string;
    sourceOffsets: { start: number; end: number } | null;
  }) => void;
  readerMode?: boolean;
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
  propsOnSelectObject?: (selection: {
    laneRole: GraphReviewProjectionLaneRole;
    nodeId: string;
  }) => void;
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
      {decoration.status !== "unknown" && decoration.status !== "matched" ? (
        <span className="graph-review-pill-delta-badge">
          {decoration.label}
        </span>
      ) : null}
    </button>
  );
}

// Matches parseRecapInlineSegments (graphPreview/recapMarkdown.ts) and
// markdownToTiptap.ts's graphNodeReferencePattern: find `[label](dmb-node:id)`
// links directly in the markdown text being rendered. This intentionally does
// NOT rely on server-computed mention offsets — those have to stay byte-perfect
// in sync with a markdown string that gets mutated in a different language, and
// they silently miss any link the corpus author wrote by hand (the backend's
// alias-matching pass skips text already wrapped in brackets, so no offset is
// ever produced for it). Parsing the text we actually have renders every link
// that's actually present, regardless of how it got there.
const NODE_LINK_PATTERN = /\[([^\]]+)\]\(dmb-node:([^)]+)\)/g;

function renderInlineText(
  text: string,
  laneRole: GraphReviewProjectionLaneRole,
  nodeViews: Record<string, GraphProjectionNodeView>,
  decorations: Record<string, NodeDecoration>,
  activeObject: GraphReviewProjectionLaneProps["activeObject"],
  onActiveObjectChange: GraphReviewProjectionLaneProps["onActiveObjectChange"],
  propsOnSelectObject?: (selection: {
    laneRole: GraphReviewProjectionLaneRole;
    nodeId: string;
  }) => void,
) {
  const parts: ReactNode[] = [];
  let cursor = 0;

  for (const match of text.matchAll(NODE_LINK_PATTERN)) {
    const start = match.index ?? 0;
    const end = start + match[0].length;
    if (start > cursor) {
      parts.push(<span key={`t-${cursor}`}>{text.slice(cursor, start)}</span>);
    }
    const label = match[1].replace(/\\]/g, "]").replace(/\\\\/g, "\\");
    const nodeId = match[2];
    parts.push(
      renderMentionToken({
        laneRole,
        nodeViews,
        decorations,
        activeObject,
        onActiveObjectChange,
        propsOnSelectObject,
        nodeId,
        label,
        key: `${nodeId}-${start}`,
      }),
    );
    cursor = end;
  }

  if (cursor < text.length) {
    parts.push(<span key={`t-${cursor}`}>{text.slice(cursor)}</span>);
  }
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
      const content = renderInlineText(
        markdown.slice(contentStart, end),
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
        {renderInlineText(
          markdown.slice(start, end),
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
  const laneProps = {
    ...props,
    markdown: stripLeadingYamlFrontmatter(props.markdown).markdown,
  };
  const readerMode = props.readerMode ?? false;
  const ariaLabel =
    props.laneRole === "gold" ? "Gold fixture prose" : "Live run prose";
  return (
    <section
      className="graph-review-projection-lane"
      aria-label={readerMode ? ariaLabel : props.title}
      data-lane-role={props.laneRole}
    >
      {!readerMode ? (
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
      ) : null}
      <article
        className="graph-review-projection-document"
        onMouseUp={() => {
          const selected = window.getSelection()?.toString().trim() ?? "";
          if (selected)
            props.onSelectText?.({
              laneRole: props.laneRole,
              text: selected,
              sourceOffsets: null,
            });
        }}
        data-testid={
          props.laneRole === "live" ? "graph-projection-reader" : undefined
        }
      >
        {renderMarkdownBlocks(laneProps, decorations)}
      </article>
    </section>
  );
}
