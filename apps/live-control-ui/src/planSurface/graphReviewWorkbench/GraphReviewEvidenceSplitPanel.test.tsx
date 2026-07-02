import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { GoldReviewEvidenceDiffResponse } from "../../api/types";
import type { GraphReviewContextualDelta } from "./graphReviewDeltaTypes";
import { buildEvidenceSelectionForDelta } from "./graphReviewEvidenceSelectionUtils";
import { GraphReviewEvidenceSplitPanel } from "./GraphReviewEvidenceSplitPanel";

function delta(overrides: Partial<GraphReviewContextualDelta> = {}): GraphReviewContextualDelta {
  return {
    deltaId: "delta-1",
    objectKind: "node",
    status: "matched",
    laneObjectRefs: [{ laneId: "gold", laneRole: "gold", objectKind: "node", objectId: "gold-node", label: "Gold node" }],
    summary: "Matched node delta.",
    sourceSpanRefIds: [],
    evidenceRefIds: [],
    ...overrides,
  };
}

const evidence: GoldReviewEvidenceDiffResponse = {
  schema_version: "dmb_graph_gold_review_evidence_v1",
  version: "1",
  session_id: "session-23",
  campaign_id: "longmont-c2",
  object_kind: "nodes",
  object_id: "gold-node",
  matched: true,
  match_score: 0.88,
  gold: {
    object_id: "gold-node",
    object_kind: "nodes",
    label: "Gold Node",
    summary: "Expected node summary.",
    payload: { node_kind: "actor" },
    evidence: [{ source_anchor_id: "anchor-1", source_span_ref_id: "span-1", preview_snippet: "Gold preview", paragraph_text: "Gold paragraph", line_start: 4, line_end: 6 }],
  },
  live: {
    object_id: "live-node",
    object_kind: "nodes",
    label: "Live Node",
    summary: "Produced node summary.",
    payload: { node_kind: "actor" },
    evidence: [{ source_anchor_id: "anchor-2", source_span_ref_id: "span-2", preview_snippet: "Live preview", paragraph_text: "Live paragraph", line_start: 7, line_end: 7 }],
  },
};

describe("GraphReviewEvidenceSplitPanel", () => {
  it("renders idle guidance with no selection", () => {
    render(<GraphReviewEvidenceSplitPanel selection={buildEvidenceSelectionForDelta(null)} evidence={null} status="idle" />);
    expect(screen.getByText("Select a delta, graph pill, or source-span attached delta to inspect gold/live evidence.")).toBeInTheDocument();
  });

  it("renders live-only unavailable messaging", () => {
    const selection = buildEvidenceSelectionForDelta(delta({
      status: "live_only",
      laneObjectRefs: [{ laneId: "live", laneRole: "live", objectKind: "node", objectId: "live-node" }],
    }));
    render(<GraphReviewEvidenceSplitPanel selection={selection} evidence={null} status="unavailable" />);
    expect(screen.getByText("This live-only delta has no gold object reference, so there is no gold evidence side to fetch in this PR.")).toBeInTheDocument();
    expect(screen.getByText(/live-node/)).toBeInTheDocument();
  });

  it("renders loading state", () => {
    render(<GraphReviewEvidenceSplitPanel selection={buildEvidenceSelectionForDelta(delta())} evidence={null} status="loading" />);
    expect(screen.getByText("Loading gold/live evidence…")).toBeInTheDocument();
  });

  it("renders error state", () => {
    render(<GraphReviewEvidenceSplitPanel selection={buildEvidenceSelectionForDelta(delta())} evidence={null} status="error" errorMessage="Evidence missing" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Evidence missing");
    expect(screen.getByRole("alert")).toHaveTextContent("nodes · gold-node");
  });

  it("renders gold and live columns when ready", () => {
    render(<GraphReviewEvidenceSplitPanel selection={buildEvidenceSelectionForDelta(delta())} evidence={evidence} status="ready" />);
    expect(screen.getByText("Gold expected evidence")).toBeInTheDocument();
    expect(screen.getByText("Live produced evidence")).toBeInTheDocument();
    expect(screen.getAllByText("Gold Node").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Live Node").length).toBeGreaterThan(0);
  });

  it("handles missing live evidence side", () => {
    render(<GraphReviewEvidenceSplitPanel selection={buildEvidenceSelectionForDelta(delta())} evidence={{ ...evidence, live: null }} status="ready" />);
    expect(screen.getAllByText("Gold Node").length).toBeGreaterThan(0);
    expect(screen.getAllByText("No live evidence side.").length).toBeGreaterThan(0);
  });

  it("renders source span refs and preview snippets", () => {
    render(<GraphReviewEvidenceSplitPanel selection={buildEvidenceSelectionForDelta(delta())} evidence={evidence} status="ready" />);
    expect(screen.getByText("span-1")).toBeInTheDocument();
    expect(screen.getByText("Gold preview")).toBeInTheDocument();
    expect(screen.getByText("Gold paragraph")).toBeInTheDocument();
  });

  it("calls the clear handler", () => {
    const onClear = vi.fn();
    render(<GraphReviewEvidenceSplitPanel selection={buildEvidenceSelectionForDelta(delta())} evidence={null} status="loading" onClearSelection={onClear} />);
    fireEvent.click(screen.getByRole("button", { name: "Clear selection" }));
    expect(onClear).toHaveBeenCalledTimes(1);
  });
});
