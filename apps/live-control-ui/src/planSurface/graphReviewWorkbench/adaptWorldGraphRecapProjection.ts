import type {
  UnionSupergraphProjectionResponse,
  WorldGraphRecapProjection,
} from "../../api/types";
import { adaptWorldGraphNodeViewMap } from "../../worldGraph/worldGraphNodeViewAdapter";

/** Adapt World Graph recap projection into the Graph Review live-lane snake_case shape. */
export function adaptWorldGraphRecapToUnionProjection(
  payload: WorldGraphRecapProjection,
): UnionSupergraphProjectionResponse {
  return {
    campaign_id: payload.campaignId,
    session_id: payload.sessionId,
    graph_id: payload.graphId,
    markdown: payload.markdown,
    focus: {
      focus_session_id: payload.focus.focusSessionId,
      focused_evidence_ref_ids: payload.focus.focusedEvidenceRefIds,
      focused_edge_ids: payload.focus.focusedEdgeIds,
      focused_node_ids: payload.focus.focusedNodeIds,
    },
    node_views: adaptWorldGraphNodeViewMap(payload.nodeViews),
    source_spans: (payload.sourceSpans ?? []).map((span, index) => ({
      span_id: span.spanId,
      kind: "paragraph",
      ordinal: index + 1,
      text_excerpt: span.textExcerpt,
    })),
    mentions: (payload.mentions ?? []).map((mention) => ({
      mention_id: mention.mentionId,
      node_id: mention.nodeId,
      label: mention.label,
      start_offset: mention.startOffset,
      end_offset: mention.endOffset,
      evidence_ref_ids: mention.evidenceRefIds,
    })),
  };
}
