import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { prepareGraphGoldAuthoringPreview } from "../../api/liveApi";
import { GraphReviewAuthoringPreparePreviewPanel } from "./GraphReviewAuthoringPreparePreviewPanel";
import type { GraphReviewLocalAuthoringProposal } from "./graphReviewLocalAuthoringState";

vi.mock("../../api/liveApi", async () => {
  const actual = await vi.importActual<typeof import("../../api/liveApi")>("../../api/liveApi");
  return { ...actual, prepareGraphGoldAuthoringPreview: vi.fn() };
});

const acceptedProposal: GraphReviewLocalAuthoringProposal = {
  proposalId: "local-1",
  proposalType: "node_from_span",
  createdAtIso: "2026-07-03T00:00:00Z",
  status: "accepted_local",
  laneRole: "live",
  sourceText: "Tripod Null-Calf",
  sourceOffsets: null,
  suggestedLabel: "Tripod Null-Calf",
  suggestedKind: null,
};

const readyResponse = {
  schema: "dmb_graph_gold_authoring_prepare_response_v1" as const,
  campaign_id: "longmont-c1",
  session_id: "session-1",
  fixture_relpath: "gold/candidate_graph_gold.json",
  validation_status: "ready" as const,
  proposal_counts: { total: 1, accepted_local: 1, staged: 0, rejected_local: 0, candidate_operations: 1, ignored: 0, blocked: 0 },
  normalized_proposals: [],
  proposed_operations: [{ operation_id: "preview:node:local-1", operation_type: "add_node" as const, source_proposal_id: "local-1", label: "Tripod Null-Calf", summary: "Would add a new gold-shaped draft node from selected prose.", gold_shape_preview: { node: { label: "Tripod Null-Calf" } }, requires_manual_review: false, diagnostics: [] }],
  blocking_errors: [],
  warnings: [],
  preview_summary: "Preview prepared with 1 proposed operation(s). No files were changed.",
  write_performed: false as const,
};

describe("GraphReviewAuthoringPreparePreviewPanel", () => {
  beforeEach(() => vi.mocked(prepareGraphGoldAuthoringPreview).mockReset());

  it("sends accepted-local proposals and renders operation cards with collapsed payload", async () => {
    vi.mocked(prepareGraphGoldAuthoringPreview).mockResolvedValue(readyResponse);
    render(<GraphReviewAuthoringPreparePreviewPanel campaignId="longmont-c1" sessionId="session-1" proposals={[acceptedProposal]} />);

    expect(screen.queryByText(/Save|Commit|Apply|Merge/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Prepare write preview" }));

    await waitFor(() => expect(prepareGraphGoldAuthoringPreview).toHaveBeenCalled());
    expect(prepareGraphGoldAuthoringPreview).toHaveBeenCalledWith(expect.objectContaining({ proposals: [expect.objectContaining({ proposal_id: "local-1", status: "accepted_local" })] }));
    expect(await screen.findByText("Preview prepared. No files were changed.")).toBeInTheDocument();
    expect(screen.getByText("Add Node — Tripod Null-Calf")).toBeInTheDocument();
    const details = screen.getByText("Gold-shaped preview payload").closest("details");
    expect(details).not.toHaveAttribute("open");
  });

  it("renders blocking diagnostics and no-files-changed copy", async () => {
    vi.mocked(prepareGraphGoldAuthoringPreview).mockResolvedValue({ ...readyResponse, validation_status: "blocked", proposed_operations: [], proposal_counts: { ...readyResponse.proposal_counts, candidate_operations: 0, blocked: 1 }, blocking_errors: [{ code: "empty_proposals", message: "No local proposals were provided.", severity: "error", source_proposal_id: null }], preview_summary: "Preview blocked. Resolve diagnostics before a future write step." });
    render(<GraphReviewAuthoringPreparePreviewPanel campaignId="longmont-c1" sessionId="session-1" proposals={[]} />);
    await userEvent.click(screen.getByRole("button", { name: "Prepare write preview" }));
    expect((await screen.findAllByText(/Preview blocked/)).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/No files were changed/).length).toBeGreaterThan(0);
    expect(screen.getByText("No local proposals were provided.")).toBeInTheDocument();
  });
});
