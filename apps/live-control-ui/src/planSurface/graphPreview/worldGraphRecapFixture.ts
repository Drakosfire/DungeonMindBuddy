import type {
  WorldGraphProjectionNodeView,
  WorldGraphProjectionSnapshot,
} from "../../api/types";

/** PR380A recap projection response shape (camelCase wire vocabulary). */
export interface WorldGraphRecapProjectionFixture {
  schema: "dmb_world_graph_recap_projection_v1";
  campaignId: string;
  sessionId: string;
  graphId: string;
  snapshot: WorldGraphProjectionSnapshot;
  markdown: string;
  focus: {
    focusSessionId: string | null;
    focusedEvidenceRefIds: string[];
    focusedEdgeIds: string[];
    focusedNodeIds: string[];
  };
  nodeViews: Record<string, WorldGraphProjectionNodeView>;
  mentions: Array<{
    mentionId: string;
    nodeId: string;
    label: string;
    startOffset: number | null;
    endOffset: number | null;
    evidenceRefIds: string[];
  }>;
  sourceSpans: [];
  diagnostics: Array<{ code: string; message: string; severity?: string | null }>;
  trustBoundary: {
    canTrust: string[];
    cannotTrust: string[];
  };
}

const REVISION_ID = "wg-rev-longmont-c2-session-23-recap-v1";

const focusAnchoredNode: WorldGraphProjectionNodeView = {
  nodeId: "pc_caelynn",
  label: "Caelynn",
  kind: "pc",
  role: "pc",
  aliases: ["Caelynn"],
  sourceDomains: ["recap"],
  summary: "Held the Mireward gate during Session 23.",
  anchoredToFocusSession: true,
  campaignScope: "longmont-c2",
  evidenceBadges: [
    {
      evidenceRefId: "evidence:session-23:caelynn:recap-mention",
      sourceArtifactId: "artifact:recap:longmont-c2:session-23",
      sourceDomain: "recap",
      evidenceRole: "focus_session_recap_mention",
      isFocusSessionEvidence: true,
      canOpenSource: true,
      canHighlightSpan: true,
      label: "Held the Mireward gate during the incident",
      sessionId: "session-23",
      sourceSpanRefId: "spref:session-23:p014",
    },
  ],
  adjacency: [
    {
      edgeId: "edge:pc_caelynn:connected_to:loc_mirathorn",
      nodeId: "loc_mirathorn",
      label: "Mirathorn",
      kind: "location",
      predicate: "connected_to",
      direction: "outgoing",
      anchoredToFocusSession: false,
      sourceDomains: ["worldbuilding"],
      evidenceRefIds: ["evidence:worldbuilding:mirathorn:prior-note"],
      sessionIds: [],
      campaignScope: "longmont-c2",
      relatedSummary: "Prior-campaign context location.",
      sourceExcerpt: null,
    },
  ],
  suggestedExpansions: [],
  evidenceRefIds: ["evidence:session-23:caelynn:recap-mention"],
  sourceArtifactIds: ["artifact:recap:longmont-c2:session-23"],
};

const priorContextNode: WorldGraphProjectionNodeView = {
  nodeId: "loc_mirathorn",
  label: "Mirathorn",
  kind: "location",
  role: "location",
  aliases: ["Mirathorn"],
  sourceDomains: ["worldbuilding"],
  summary: "Durable location referenced from earlier campaign context.",
  anchoredToFocusSession: false,
  campaignScope: "longmont-c2",
  evidenceBadges: [
    {
      evidenceRefId: "evidence:worldbuilding:mirathorn:prior-note",
      sourceArtifactId: "artifact:worldbuilding:longmont-c2:mirathorn-note",
      sourceDomain: "worldbuilding",
      evidenceRole: "character_context",
      isFocusSessionEvidence: false,
      canOpenSource: true,
      canHighlightSpan: false,
      label: "Referenced before Session 23 focus",
      sessionId: "session-21",
      sourceSpanRefId: null,
    },
  ],
  adjacency: [],
  suggestedExpansions: [],
  evidenceRefIds: ["evidence:worldbuilding:mirathorn:prior-note"],
  sourceArtifactIds: ["artifact:worldbuilding:longmont-c2:mirathorn-note"],
};

/** Real-shape World Graph recap fixture for PR380B tests (PR380A contract). */
export const session23WorldGraphRecapFixture: WorldGraphRecapProjectionFixture = {
  schema: "dmb_world_graph_recap_projection_v1",
  campaignId: "longmont-c2",
  sessionId: "session-23",
  graphId: REVISION_ID,
  snapshot: {
    worldId: "eldyrwild",
    campaignId: "longmont-c2",
    revisionId: REVISION_ID,
    headRevisionId: REVISION_ID,
    isHead: true,
    focus: { kind: "session", sessionId: "session-23", campaignId: "longmont-c2" },
    admissibility: "gm",
    scopeMode: "campaign",
  },
  markdown:
    "# Session 23 Sample\n\n[Caelynn](dmb-node:pc_caelynn) held the Mireward gate while the party tried to understand what had happened near [Mirathorn](dmb-node:loc_mirathorn).",
  focus: {
    focusSessionId: "session-23",
    focusedEvidenceRefIds: ["evidence:session-23:caelynn:recap-mention"],
    focusedEdgeIds: ["edge:pc_caelynn:connected_to:loc_mirathorn"],
    focusedNodeIds: ["pc_caelynn"],
  },
  nodeViews: {
    pc_caelynn: focusAnchoredNode,
    loc_mirathorn: priorContextNode,
  },
  mentions: [
    {
      mentionId: "mention:session-23:pc_caelynn:0",
      nodeId: "pc_caelynn",
      label: "Caelynn",
      startOffset: null,
      endOffset: null,
      evidenceRefIds: [],
    },
    {
      mentionId: "mention:session-23:loc_mirathorn:1",
      nodeId: "loc_mirathorn",
      label: "Mirathorn",
      startOffset: null,
      endOffset: null,
      evidenceRefIds: [],
    },
  ],
  sourceSpans: [],
  diagnostics: [],
  trustBoundary: {
    canTrust: [
      "snapshot identifies the exact graph read",
      "node_views and graph mention targets come from that snapshot",
      "markdown body comes from the requested canonical normalized recap",
      "graph_id equals snapshot.revision_id",
    ],
    cannotTrust: [
      "mention spans are evidence bindings",
      "source highlighting is available",
      "absent nodes were searched in other campaigns or world scope",
    ],
  },
};
