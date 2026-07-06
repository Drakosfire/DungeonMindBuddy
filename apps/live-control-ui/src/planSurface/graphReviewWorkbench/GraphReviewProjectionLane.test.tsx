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
  it("renders dmb-node links found directly in the markdown as graph tokens with delta state", () => {
    render(
      <GraphReviewProjectionLane
        laneRole="gold"
        title="Gold Fixture · read-only"
        markdown="The [Tripod Null-Calf](dmb-node:node:tripod-null-calf) threatened the North Gate."
        nodeViews={{ "node:tripod-null-calf": tripodNode }}
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
    expect(screen.queryByText("Matched")).not.toBeInTheDocument();
  });

  it("renders every dmb-node link present in the text, including ones with no matching mention entry", () => {
    render(
      <GraphReviewProjectionLane
        laneRole="gold"
        title="Gold Fixture · read-only"
        markdown="The [Tripod Null-Calf](dmb-node:node:tripod-null-calf) fled toward the [North Gate](dmb-node:loc_north_gate)."
        nodeViews={{ "node:tripod-null-calf": tripodNode }}
        mentionsCount={0}
        deltaIndex={deltaIndex}
        activeObject={null}
        onActiveObjectChange={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("button", { name: /Tripod Null-Calf/i }),
    ).toBeInTheDocument();
    const gateToken = screen.getByRole("button", { name: /North Gate/i });
    expect(gateToken).toHaveAttribute("data-graph-node-id", "loc_north_gate");
  });

  it("hides lane header metadata in reader mode", () => {
    render(
      <GraphReviewProjectionLane
        laneRole="gold"
        title="Gold Fixture · read-only"
        subtitle="evals/graph_memory_layer/examples/session_23.json"
        markdown="The [Tripod Null-Calf](dmb-node:node:tripod-null-calf) threatened the North Gate."
        nodeViews={{ "node:tripod-null-calf": tripodNode }}
        mentionsCount={1}
        deltaIndex={deltaIndex}
        activeObject={null}
        onActiveObjectChange={vi.fn()}
        readerMode
      />,
    );

    expect(screen.queryByText("Gold Fixture · read-only")).not.toBeInTheDocument();
    expect(
      screen.queryByText(/projected graph mention/i),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Tripod Null-Calf/i }),
    ).toBeInTheDocument();
  });

  it("shows delta badges only for mismatched pills", () => {
    const goldOnlyDeltaIndex: GraphReviewDeltaIndex = {
      ...deltaIndex,
      countsByStatus: {
        ...deltaIndex.countsByStatus,
        matched: 0,
        gold_only: 1,
      },
      deltas: [
        {
          deltaId: "gold-only:node:tripod",
          objectKind: "node",
          status: "gold_only",
          laneObjectRefs: [
            {
              laneId: "gold",
              laneRole: "gold",
              objectKind: "node",
              objectId: "node:tripod-null-calf",
              label: "Tripod Null-Calf",
            },
          ],
          label: "Tripod Null-Calf",
          summary: "Gold-only node: Tripod Null-Calf",
          sourceSpanRefIds: [],
          evidenceRefIds: [],
        },
      ],
    };

    render(
      <GraphReviewProjectionLane
        laneRole="gold"
        title="Gold Fixture · read-only"
        markdown="The [Tripod Null-Calf](dmb-node:node:tripod-null-calf) threatened the North Gate."
        nodeViews={{ "node:tripod-null-calf": tripodNode }}
        mentionsCount={1}
        deltaIndex={goldOnlyDeltaIndex}
        activeObject={null}
        onActiveObjectChange={vi.fn()}
      />,
    );

    const token = screen.getByRole("button", { name: /Tripod Null-Calf/i });
    expect(token).toHaveAttribute("data-delta-status", "gold_only");
    expect(screen.getByText("Gold-only")).toBeInTheDocument();
  });

  it("reports clicked node selection with lane role", () => {
    const onSelectObject = vi.fn();
    render(
      <GraphReviewProjectionLane
        laneRole="gold"
        title="Gold Fixture · read-only"
        markdown="The [Tripod Null-Calf](dmb-node:node:tripod-null-calf) threatened the North Gate."
        nodeViews={{ "node:tripod-null-calf": tripodNode }}
        mentionsCount={1}
        deltaIndex={deltaIndex}
        activeObject={null}
        onActiveObjectChange={vi.fn()}
        onSelectObject={onSelectObject}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Tripod Null-Calf/i }));
    expect(onSelectObject).toHaveBeenCalledWith({
      laneRole: "gold",
      nodeId: "node:tripod-null-calf",
    });
  });

  it("strips leading frontmatter while preserving mention tokens and body dividers", () => {
    const frontmatter =
      '---\ntitle: "Session 1"\ndocument_class: play\ncanon_layer: campaign\n---\n\n';
    const body =
      "The [Tripod Null-Calf](dmb-node:node:tripod-null-calf) threatened the North Gate.\n\n---\n\nThe gate held.";

    render(
      <GraphReviewProjectionLane
        laneRole="gold"
        title="Gold Fixture read-only"
        markdown={`${frontmatter}${body}`}
        nodeViews={{ "node:tripod-null-calf": tripodNode }}
        mentionsCount={1}
        deltaIndex={deltaIndex}
        activeObject={null}
        onActiveObjectChange={vi.fn()}
      />,
    );

    expect(screen.queryByText(/document_class/)).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Tripod Null-Calf/i }),
    ).toHaveAttribute("data-graph-node-id", "node:tripod-null-calf");
    expect(screen.getByText("---")).toBeInTheDocument();
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
            markdown="The [Tripod Null-Calf](dmb-node:node:tripod-null-calf) threatened the North Gate."
            nodeViews={{ "node:tripod-null-calf": tripodNode }}
            mentionsCount={1}
            deltaIndex={deltaIndex}
            activeObject={activeObject}
            onActiveObjectChange={setActiveObject}
          />
          <GraphReviewProjectionLane
            laneRole="live"
            title="Live Run · read-only"
            markdown="The [Tripod Null-Calf](dmb-node:live:tripod-null-calf) reached the North Gate."
            nodeViews={{ "live:tripod-null-calf": liveTripodNode }}
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

  it("reports selected prose text with the source lane role for gold and live lanes", () => {
    const onSelectGoldText = vi.fn();
    const onSelectLiveText = vi.fn();
    const selectionSpy = vi
      .spyOn(window, "getSelection")
      .mockReturnValue({ toString: () => "Tripod Null-Calf" } as Selection);

    render(
      <div>
        <GraphReviewProjectionLane
          laneRole="gold"
          title="Gold Fixture · read-only"
          markdown="The Tripod Null-Calf threatened the North Gate."
          nodeViews={{}}
          mentionsCount={0}
          deltaIndex={deltaIndex}
          activeObject={null}
          onActiveObjectChange={vi.fn()}
          onSelectText={onSelectGoldText}
        />
        <GraphReviewProjectionLane
          laneRole="live"
          title="Live Run · read-only"
          markdown="The Tripod Null-Calf reached the North Gate."
          nodeViews={{}}
          mentionsCount={0}
          deltaIndex={deltaIndex}
          activeObject={null}
          onActiveObjectChange={vi.fn()}
          onSelectText={onSelectLiveText}
        />
      </div>,
    );

    const documents = screen.getAllByText(/Tripod Null-Calf/);
    fireEvent.mouseUp(documents[0].closest("article")!);
    expect(onSelectGoldText).toHaveBeenCalledWith({
      laneRole: "gold",
      text: "Tripod Null-Calf",
      sourceOffsets: null,
    });

    fireEvent.mouseUp(documents[1].closest("article")!);
    expect(onSelectLiveText).toHaveBeenCalledWith({
      laneRole: "live",
      text: "Tripod Null-Calf",
      sourceOffsets: null,
    });

    selectionSpy.mockRestore();
  });
});
