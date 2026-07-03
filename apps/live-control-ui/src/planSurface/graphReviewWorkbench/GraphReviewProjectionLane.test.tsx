import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import type { GraphReviewDeltaIndex } from "./graphReviewDeltaTypes";
import { GraphReviewProjectionLane } from "./GraphReviewProjectionLane";

const tripodNode: GraphProjectionNodeView = {
  node_id: "node:tripod-null-calf",
  label: "Tripod Null-Calf",
  kind: "npc",
  role: "npc",
  aliases: [],
  source_domains: [],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
  summary: null,
};

const liveTripodNode: GraphProjectionNodeView = {
  ...tripodNode,
  node_id: "live:tripod-null-calf",
};

const deltaIndex: GraphReviewDeltaIndex = {
  schemaVersion: "dmb_graph_review_contextual_delta_index_v1",
  campaignId: "longmont-c1",
  sessionId: "session-1",
  goldLaneId: "gold",
  liveLaneId: "live",
  liveRunManifestPath: "manifest.json",
  countsByObjectKind: {
    node: 1,
    edge: 0,
    mention: 0,
    source_span: 0,
    beat: 0,
    write: 0,
    ignored_item: 0,
    deferred_item: 0,
    unknown: 0,
  },
  countsByStatus: {
    matched: 1,
    gold_only: 0,
    live_only: 0,
    changed_type: 0,
    changed_label: 0,
    changed_evidence: 0,
    changed_edges: 0,
    comparator_uncertain: 0,
  },
  warnings: [],
  deltas: [
    {
      deltaId: "matched:node:tripod",
      objectKind: "node",
      status: "matched",
      laneObjectRefs: [
        {
          laneId: "gold",
          laneRole: "gold",
          objectKind: "node",
          objectId: "node:tripod-null-calf",
          label: "Tripod Null-Calf",
        },
        {
          laneId: "live",
          laneRole: "live",
          objectKind: "node",
          objectId: "live:tripod-null-calf",
          label: "Tripod Null-Calf",
        },
      ],
      label: "Tripod Null-Calf",
      summary: "Matched node: Tripod Null-Calf",
      sourceSpanRefIds: [],
      evidenceRefIds: [],
    },
  ],
};

describe("GraphReviewProjectionLane", () => {
  it("renders structured anchored mentions as graph tokens with delta state", () => {
    render(
      <GraphReviewProjectionLane
        laneRole="gold"
        title="Gold Fixture · read-only"
        markdown="The Tripod Null-Calf threatened the North Gate."
        nodeViews={{ "node:tripod-null-calf": tripodNode }}
        mentions={[
          {
            mention_id: "m1",
            node_id: "node:tripod-null-calf",
            label: "Tripod Null-Calf",
            start_offset: 4,
            end_offset: 21,
            evidence_ref_ids: [],
            anchor_status: "anchored",
          },
        ]}
        mentionsCount={1}
        deltaIndex={deltaIndex}
        activeObject={null}
        onActiveObjectChange={vi.fn()}
      />,
    );

    const token = screen.getByRole("button", { name: /Tripod Null-Calf/i });
    expect(token).toHaveAttribute(
      "data-graph-node-id",
      "node:tripod-null-calf",
    );
    expect(token).toHaveAttribute("data-delta-status", "matched");
  });

  it("highlights a matched live counterpart when the gold token is hovered", () => {
    function Harness() {
      const [activeObject, setActiveObject] = useState<{
        laneRole: "gold" | "live";
        nodeId: string;
      } | null>(null);
      return (
        <div>
          <GraphReviewProjectionLane
            laneRole="gold"
            title="Gold Fixture · read-only"
            markdown="The Tripod Null-Calf threatened the North Gate."
            nodeViews={{ "node:tripod-null-calf": tripodNode }}
            mentions={[
              {
                mention_id: "m1",
                node_id: "node:tripod-null-calf",
                label: "Tripod Null-Calf",
                start_offset: 4,
                end_offset: 21,
                evidence_ref_ids: [],
                anchor_status: "anchored",
              },
            ]}
            mentionsCount={1}
            deltaIndex={deltaIndex}
            activeObject={activeObject}
            onActiveObjectChange={setActiveObject}
          />
          <GraphReviewProjectionLane
            laneRole="live"
            title="Live Run · read-only"
            markdown="The Tripod Null-Calf reached the North Gate."
            nodeViews={{ "live:tripod-null-calf": liveTripodNode }}
            mentions={[
              {
                mention_id: "m2",
                node_id: "live:tripod-null-calf",
                label: "Tripod Null-Calf",
                start_offset: 4,
                end_offset: 21,
                evidence_ref_ids: [],
                anchor_status: "anchored",
              },
            ]}
            mentionsCount={1}
            deltaIndex={deltaIndex}
            activeObject={activeObject}
            onActiveObjectChange={setActiveObject}
          />
        </div>
      );
    }

    render(<Harness />);
    const tokens = screen.getAllByRole("button", { name: /Tripod Null-Calf/i });
    fireEvent.mouseEnter(tokens[0]);
    expect(tokens[1]).toHaveAttribute("data-counterpart-highlighted", "true");
  });
});
