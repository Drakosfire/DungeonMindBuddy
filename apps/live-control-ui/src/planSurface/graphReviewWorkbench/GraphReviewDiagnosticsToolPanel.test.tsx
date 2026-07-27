import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import { buildEvidenceSelectionForDelta } from "./graphReviewEvidenceSelectionUtils";
import { buildGraphReviewDeltaIndex } from "./graphReviewDeltaUtils";
import { buildSourceSpanDeltaIndex } from "./graphReviewSourceSpanOverlayUtils";
import { buildVariantLiveInventoryIndex } from "./graphReviewVariantReferenceUtils";
import type { GraphReviewDiagnosticsProjectionPayload } from "../projection/projectionBindings";
import { GraphReviewDiagnosticsToolPanel } from "./GraphReviewDiagnosticsToolPanel";

function emptyPayload(
  overrides: Partial<GraphReviewDiagnosticsProjectionPayload> = {},
): GraphReviewDiagnosticsProjectionPayload {
  return {
    campaignId: "longmont-c2",
    sessionId: "session-21",
    liveRun: null,
    projection: null,
    projectionStatus: "idle",
    compareStatus: "idle",
    compare: null,
    compareError: null,
    selection: null,
    onSelectSelection: vi.fn(),
    deltaIndex: buildGraphReviewDeltaIndex({
      compare: null,
      liveProjection: null,
      goldLane: null,
      liveLane: null,
    }),
    sourceSpanDeltaIndex: buildSourceSpanDeltaIndex({
      sourceSpans: [],
      deltas: [],
    }),
    selectedDeltaNodeId: null,
    setSelectedEvidenceDeltaId: vi.fn(),
    selectedEvidenceDeltaId: null,
    selectedSourceSpanId: null,
    setSelectedSourceSpanId: vi.fn(),
    evidenceSelection: buildEvidenceSelectionForDelta(null),
    evidenceDiff: null,
    evidenceStatus: "idle",
    evidenceError: null,
    manualBeds: [],
    manualBedsStatus: "idle",
    manualBedsError: null,
    selectedManualBed: null,
    selectedVariantLaneView: null,
    selectedManualVariant: null,
    onSelectManualBedId: vi.fn(),
    onSelectManualVariantName: vi.fn(),
    variantInventoryIndex: buildVariantLiveInventoryIndex({
      variant: null,
      compare: null,
    }),
    selectedVariantInventoryRowId: null,
    setSelectedVariantInventoryRowId: vi.fn(),
    selectedVariantInventoryRow: null,
    ...overrides,
  };
}

describe("GraphReviewDiagnosticsToolPanel", () => {
  it("renders an explicit unavailable state when payload is absent", () => {
    render(<GraphReviewDiagnosticsToolPanel payload={null} />);
    expect(screen.getByTestId("graph-review-diagnostics-unavailable")).toHaveTextContent(
      /Graph Review diagnostics are unavailable/i,
    );
  });

  it("renders the select-a-live-run empty state from a supplied idle payload", () => {
    render(<GraphReviewDiagnosticsToolPanel payload={emptyPayload()} />);
    expect(
      screen.getByText(/Select a live run with a projection to inspect diagnostics/i),
    ).toBeInTheDocument();
  });

  it("renders diagnostics sections from a ready payload without live-state ancestry", () => {
    const setSelectedEvidenceDeltaId = vi.fn();
    const node: GraphProjectionNodeView = {
      node_id: "npc-glowkindle",
      label: "Glowkindle",
      kind: "npc",
      role: "merchant",
      aliases: [],
      source_domains: ["recap"],
      evidence_badges: [],
      adjacency: [],
      anchored_to_focus_session: true,
      summary: "A friendly merchant.",
    };

    render(
      <GraphReviewDiagnosticsToolPanel
        payload={emptyPayload({
          liveRun: {
            manifest_path: "manifest.json",
            run_dir: "runs/run-1",
            campaign_id: "longmont-c2",
            session_id: "session-21",
            status: "preview_ready",
            node_count: 1,
            edge_count: 0,
            evidence_ref_count: 0,
            next_actions: [],
            run_id: "run-1",
            run_label: "Run 1",
            vocabulary_mode: "played_canon",
            runner_options_summary: {},
            diagnostics_summary: {},
            preview_union_available: true,
          },
          projection: {
            campaign_id: "longmont-c2",
            session_id: "session-21",
            node_views: { "npc-glowkindle": node },
            focus: {
              focused_evidence_ref_ids: [],
              focused_edge_ids: [],
              focused_node_ids: [],
            },
            mentions: [],
          },
          projectionStatus: "ready",
          selectedDeltaNodeId: "npc-glowkindle",
          setSelectedEvidenceDeltaId,
        })}
      />,
    );

    expect(screen.getByLabelText("Graph review diagnostics")).toBeInTheDocument();
    expect(screen.queryByTestId("graph-review-diagnostics-unavailable")).not.toBeInTheDocument();
  });
});
