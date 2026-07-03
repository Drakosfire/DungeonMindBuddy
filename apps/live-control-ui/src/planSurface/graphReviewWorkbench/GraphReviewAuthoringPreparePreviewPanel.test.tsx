import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { commitGraphGoldAuthoringPreview, prepareGraphGoldAuthoringPreview } from "../../api/liveApi";
import { GraphReviewAuthoringPreparePreviewPanel } from "./GraphReviewAuthoringPreparePreviewPanel";
import type { GraphReviewLocalAuthoringProposal } from "./graphReviewLocalAuthoringState";

vi.mock("../../api/liveApi", async () => {
  const actual = await vi.importActual<typeof import("../../api/liveApi")>("../../api/liveApi");
  return { ...actual, prepareGraphGoldAuthoringPreview: vi.fn(), commitGraphGoldAuthoringPreview: vi.fn() };

  it("shows reload after commit and renders verification results", async () => {
    vi.mocked(prepareGraphGoldAuthoringPreview).mockResolvedValue(readyResponse);
    vi.mocked(commitGraphGoldAuthoringPreview).mockResolvedValue(commitResponse);
    const onReloadAndVerifyCommit = vi.fn().mockResolvedValue({
      schema: "dmb_graph_gold_authoring_verify_commit_response_v1",
      campaign_id: "longmont-c1",
      session_id: "session-1",
      commit_id: "graph-gold-authoring-test",
      verification_status: "verified",
      checked_operations: [{ operation_id: "preview:node:local-1", operation_type: "add_node", source_proposal_id: "local-1", target_id: "authored:node:local-1", verification_status: "found_in_gold_projection", summary: "Committed node found in gold projection." }],
      diagnostics: [],
    });
    render(<GraphReviewAuthoringPreparePreviewPanel campaignId="longmont-c1" sessionId="session-1" proposals={[acceptedProposal]} onReloadAndVerifyCommit={onReloadAndVerifyCommit} />);
    expect(screen.queryByRole("button", { name: "Reload gold projection" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Prepare write preview" }));
    await userEvent.click(await screen.findByLabelText("I understand this will write to the gold fixture and create a backup."));
    await userEvent.click(screen.getByRole("button", { name: "Commit prepared preview" }));
    const reloadButton = await screen.findByRole("button", { name: "Reload gold projection" });
    await userEvent.click(reloadButton);
    await waitFor(() => expect(onReloadAndVerifyCommit).toHaveBeenCalledWith(commitResponse));
    expect(await screen.findByText("Gold projection reloaded. Committed changes verified.")).toBeInTheDocument();
    expect(screen.getByText(/Status: found in gold projection/)).toBeInTheDocument();
    expect(screen.queryByText(/LLM|Identity resolved|Canon merged/)).not.toBeInTheDocument();
  });

  it("renders fixture-only, event-only, and missing verification honestly", async () => {
    vi.mocked(prepareGraphGoldAuthoringPreview).mockResolvedValue(readyResponse);
    vi.mocked(commitGraphGoldAuthoringPreview).mockResolvedValue(commitResponse);
    const onReloadAndVerifyCommit = vi.fn().mockResolvedValue({
      schema: "dmb_graph_gold_authoring_verify_commit_response_v1",
      campaign_id: "longmont-c1",
      session_id: "session-1",
      commit_id: "graph-gold-authoring-test",
      verification_status: "partial",
      checked_operations: [
        { operation_id: "a", operation_type: "add_node", source_proposal_id: "local-1", target_id: "authored:node:local-1", verification_status: "found_in_fixture_only", summary: "Committed node found in gold fixture, but not anchored in projection." },
        { operation_id: "b", operation_type: "link_existing_intent", source_proposal_id: "local-2", target_id: null, verification_status: "recorded_event_only", summary: "Recorded in authoring event log only; no identity link was written." },
        { operation_id: "c", operation_type: "add_edge", source_proposal_id: "local-3", target_id: "authored:edge:missing", verification_status: "missing", summary: "Committed edge was not found in the gold fixture or projection." },
      ],
      diagnostics: [{ code: "operation_missing", message: "Missing edge", operation_id: "c", severity: "error" }],
    });
    render(<GraphReviewAuthoringPreparePreviewPanel campaignId="longmont-c1" sessionId="session-1" proposals={[acceptedProposal]} onReloadAndVerifyCommit={onReloadAndVerifyCommit} />);
    await userEvent.click(screen.getByRole("button", { name: "Prepare write preview" }));
    await userEvent.click(await screen.findByLabelText("I understand this will write to the gold fixture and create a backup."));
    await userEvent.click(screen.getByRole("button", { name: "Commit prepared preview" }));
    await userEvent.click(await screen.findByRole("button", { name: "Reload gold projection" }));
    expect(await screen.findByText("Gold projection reloaded. Some committed changes are fixture-only or event-only.")).toBeInTheDocument();
    expect(screen.getByText(/Status: found in fixture only/)).toBeInTheDocument();
    expect(screen.getByText("No identity link was written.")).toBeInTheDocument();
    expect(screen.getByText(/Status: missing/)).toBeInTheDocument();
    expect(screen.getByText("Missing edge")).toBeInTheDocument();
  });

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
  prepare_fingerprint: "prepared-fingerprint-1",
  write_performed: false as const,
};

const commitResponse = {
  schema: "dmb_graph_gold_authoring_commit_response_v1" as const,
  campaign_id: "longmont-c1",
  session_id: "session-1",
  fixture_relpath: "gold/candidate_graph_gold.json",
  backup_relpath: "gold/backups/candidate_graph_gold.backup.json",
  event_log_relpath: "gold/authoring_events.jsonl",
  commit_id: "graph-gold-authoring-test",
  committed_at_iso: "2026-07-03T00:00:00Z",
  commit_status: "committed" as const,
  prepare_fingerprint: "abc",
  applied_operations: [{ operation_id: "preview:node:local-1", operation_type: "add_node", source_proposal_id: "local-1", status: "applied" as const, target_id: "authored:node:local-1", summary: "Added authored node Tripod Null-Calf." }],
  skipped_operations: [],
  diagnostics: [],
  changed_counts: { nodes_added: 1, nodes_asserted: 0, edges_added: 0, link_intents_recorded: 0, operations_skipped: 0 },
};

describe("GraphReviewAuthoringPreparePreviewPanel", () => {
  beforeEach(() => {
    vi.mocked(prepareGraphGoldAuthoringPreview).mockReset();
    vi.mocked(commitGraphGoldAuthoringPreview).mockReset();
  });

  it("sends accepted-local proposals and renders operation cards with collapsed payload", async () => {
    vi.mocked(prepareGraphGoldAuthoringPreview).mockResolvedValue(readyResponse);
    render(<GraphReviewAuthoringPreparePreviewPanel campaignId="longmont-c1" sessionId="session-1" proposals={[acceptedProposal]} />);

    expect(screen.queryByText(/Save|Apply|Merge/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Prepare write preview" }));

    await waitFor(() => expect(prepareGraphGoldAuthoringPreview).toHaveBeenCalled());
    expect(prepareGraphGoldAuthoringPreview).toHaveBeenCalledWith(expect.objectContaining({ proposals: [expect.objectContaining({ proposal_id: "local-1", status: "accepted_local" })] }));
    expect(await screen.findByText("Preview prepared. No files were changed.")).toBeInTheDocument();
    expect(screen.getByText("Add Node — Tripod Null-Calf")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Commit prepared preview" })).toBeDisabled();
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

  it("requires explicit confirmation before committing and renders commit summary", async () => {
    vi.mocked(prepareGraphGoldAuthoringPreview).mockResolvedValue(readyResponse);
    vi.mocked(commitGraphGoldAuthoringPreview).mockResolvedValue(commitResponse);
    render(<GraphReviewAuthoringPreparePreviewPanel campaignId="longmont-c1" sessionId="session-1" proposals={[acceptedProposal]} />);
    await userEvent.click(screen.getByRole("button", { name: "Prepare write preview" }));
    const commitButton = await screen.findByRole("button", { name: "Commit prepared preview" });
    expect(commitButton).toBeDisabled();
    await userEvent.click(screen.getByLabelText("I understand this will write to the gold fixture and create a backup."));
    await userEvent.click(commitButton);
    await waitFor(() => expect(commitGraphGoldAuthoringPreview).toHaveBeenCalled());
    expect(commitGraphGoldAuthoringPreview).toHaveBeenCalledWith(expect.objectContaining({ campaign_id: "longmont-c1", session_id: "session-1", expected_prepare_fingerprint: "prepared-fingerprint-1", proposals: [expect.objectContaining({ proposal_id: "local-1" })] }));
    expect(await screen.findByText("Committed. Gold fixture updated and backup created.")).toBeInTheDocument();
    expect(screen.getByText("graph-gold-authoring-test")).toBeInTheDocument();
    expect(screen.getByText("gold/backups/candidate_graph_gold.backup.json")).toBeInTheDocument();
    expect(screen.getAllByText("1").length).toBeGreaterThan(0);
  });

  it("does not show commit controls when prepare is blocked", async () => {
    vi.mocked(prepareGraphGoldAuthoringPreview).mockResolvedValue({ ...readyResponse, validation_status: "blocked", proposed_operations: [], proposal_counts: { ...readyResponse.proposal_counts, candidate_operations: 0, blocked: 1 }, blocking_errors: [{ code: "empty_proposals", message: "No local proposals were provided.", severity: "error", source_proposal_id: null }], preview_summary: "Preview blocked. Resolve diagnostics before a future write step." });
    render(<GraphReviewAuthoringPreparePreviewPanel campaignId="longmont-c1" sessionId="session-1" proposals={[]} />);
    await userEvent.click(screen.getByRole("button", { name: "Prepare write preview" }));
    await screen.findByText("No local proposals were provided.");
    expect(screen.queryByRole("button", { name: "Commit prepared preview" })).not.toBeInTheDocument();
  });

  it("clears the prepared commit controls when local proposals change after prepare", async () => {
    vi.mocked(prepareGraphGoldAuthoringPreview).mockResolvedValue(readyResponse);
    const { rerender } = render(<GraphReviewAuthoringPreparePreviewPanel campaignId="longmont-c1" sessionId="session-1" proposals={[acceptedProposal]} />);
    await userEvent.click(screen.getByRole("button", { name: "Prepare write preview" }));
    expect(await screen.findByRole("button", { name: "Commit prepared preview" })).toBeDisabled();
    rerender(<GraphReviewAuthoringPreparePreviewPanel campaignId="longmont-c1" sessionId="session-1" proposals={[{ ...acceptedProposal, proposalId: "local-2", suggestedLabel: "Changed Preview" }]} />);
    await waitFor(() => expect(screen.queryByRole("button", { name: "Commit prepared preview" })).not.toBeInTheDocument());
    expect(screen.getByText("Accept local proposals, then prepare a read-only write preview.")).toBeInTheDocument();
  });


  it("shows reload after commit and renders verification results", async () => {
    vi.mocked(prepareGraphGoldAuthoringPreview).mockResolvedValue(readyResponse);
    vi.mocked(commitGraphGoldAuthoringPreview).mockResolvedValue(commitResponse);
    const onReloadAndVerifyCommit = vi.fn().mockResolvedValue({
      schema: "dmb_graph_gold_authoring_verify_commit_response_v1",
      campaign_id: "longmont-c1",
      session_id: "session-1",
      commit_id: "graph-gold-authoring-test",
      verification_status: "verified",
      checked_operations: [{ operation_id: "preview:node:local-1", operation_type: "add_node", source_proposal_id: "local-1", target_id: "authored:node:local-1", verification_status: "found_in_gold_projection", summary: "Committed node found in gold projection." }],
      diagnostics: [],
    });
    render(<GraphReviewAuthoringPreparePreviewPanel campaignId="longmont-c1" sessionId="session-1" proposals={[acceptedProposal]} onReloadAndVerifyCommit={onReloadAndVerifyCommit} />);
    expect(screen.queryByRole("button", { name: "Reload gold projection" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Prepare write preview" }));
    await userEvent.click(await screen.findByLabelText("I understand this will write to the gold fixture and create a backup."));
    await userEvent.click(screen.getByRole("button", { name: "Commit prepared preview" }));
    const reloadButton = await screen.findByRole("button", { name: "Reload gold projection" });
    await userEvent.click(reloadButton);
    await waitFor(() => expect(onReloadAndVerifyCommit).toHaveBeenCalledWith(commitResponse));
    expect(await screen.findByText("Gold projection reloaded. Committed changes verified.")).toBeInTheDocument();
    expect(screen.getByText(/Status: found in gold projection/)).toBeInTheDocument();
    expect(screen.queryByText(/LLM|Identity resolved|Canon merged/)).not.toBeInTheDocument();
  });

  it("renders fixture-only, event-only, and missing verification honestly", async () => {
    vi.mocked(prepareGraphGoldAuthoringPreview).mockResolvedValue(readyResponse);
    vi.mocked(commitGraphGoldAuthoringPreview).mockResolvedValue(commitResponse);
    const onReloadAndVerifyCommit = vi.fn().mockResolvedValue({
      schema: "dmb_graph_gold_authoring_verify_commit_response_v1",
      campaign_id: "longmont-c1",
      session_id: "session-1",
      commit_id: "graph-gold-authoring-test",
      verification_status: "partial",
      checked_operations: [
        { operation_id: "a", operation_type: "add_node", source_proposal_id: "local-1", target_id: "authored:node:local-1", verification_status: "found_in_fixture_only", summary: "Committed node found in gold fixture, but not anchored in projection." },
        { operation_id: "b", operation_type: "link_existing_intent", source_proposal_id: "local-2", target_id: null, verification_status: "recorded_event_only", summary: "Recorded in authoring event log only; no identity link was written." },
        { operation_id: "c", operation_type: "add_edge", source_proposal_id: "local-3", target_id: "authored:edge:missing", verification_status: "missing", summary: "Committed edge was not found in the gold fixture or projection." },
      ],
      diagnostics: [{ code: "operation_missing", message: "Missing edge", operation_id: "c", severity: "error" }],
    });
    render(<GraphReviewAuthoringPreparePreviewPanel campaignId="longmont-c1" sessionId="session-1" proposals={[acceptedProposal]} onReloadAndVerifyCommit={onReloadAndVerifyCommit} />);
    await userEvent.click(screen.getByRole("button", { name: "Prepare write preview" }));
    await userEvent.click(await screen.findByLabelText("I understand this will write to the gold fixture and create a backup."));
    await userEvent.click(screen.getByRole("button", { name: "Commit prepared preview" }));
    await userEvent.click(await screen.findByRole("button", { name: "Reload gold projection" }));
    expect(await screen.findByText("Gold projection reloaded. Some committed changes are fixture-only or event-only.")).toBeInTheDocument();
    expect(screen.getByText(/Status: found in fixture only/)).toBeInTheDocument();
    expect(screen.getByText("No identity link was written.")).toBeInTheDocument();
    expect(screen.getByText(/Status: missing/)).toBeInTheDocument();
    expect(screen.getByText("Missing edge")).toBeInTheDocument();
  });

});
