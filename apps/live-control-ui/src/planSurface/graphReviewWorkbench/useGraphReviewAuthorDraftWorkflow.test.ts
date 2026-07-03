import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { commitGraphGoldAuthoringPreview, prepareGraphGoldAuthoringPreview } from "../../api/liveApi";
import { createGraphReviewLocalAuthoringIdFactory } from "./graphReviewLocalAuthoringState";
import { useGraphReviewAuthorDraftWorkflow } from "./useGraphReviewAuthorDraftWorkflow";

vi.mock("../../api/liveApi", async () => {
  const actual = await vi.importActual<typeof import("../../api/liveApi")>("../../api/liveApi");
  return { ...actual, prepareGraphGoldAuthoringPreview: vi.fn(), commitGraphGoldAuthoringPreview: vi.fn() };
});

const prepareResponse = {
  schema: "dmb_graph_gold_authoring_prepare_response_v1" as const,
  campaign_id: "longmont-c1",
  session_id: "session-1",
  fixture_relpath: "gold/candidate_graph_gold.json",
  validation_status: "ready" as const,
  proposal_counts: { total: 1, accepted_local: 1, staged: 0, rejected_local: 0, candidate_operations: 1, ignored: 0, blocked: 0 },
  normalized_proposals: [],
  proposed_operations: [],
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
  prepare_fingerprint: "prepared-fingerprint-1",
  applied_operations: [],
  skipped_operations: [],
  diagnostics: [],
  changed_counts: { nodes_added: 1, nodes_asserted: 0, edges_added: 0, link_intents_recorded: 0, operations_skipped: 0 },
};

function renderWorkflow(onReloadAndVerifyCommit = vi.fn()) {
  return renderHook(() => useGraphReviewAuthorDraftWorkflow({
    campaignId: "longmont-c1",
    sessionId: "session-1",
    idFactory: createGraphReviewLocalAuthoringIdFactory(() => "2026-07-03T00:00:00Z"),
    onReloadAndVerifyCommit,
  }));
}

describe("useGraphReviewAuthorDraftWorkflow", () => {
  beforeEach(() => {
    vi.mocked(prepareGraphGoldAuthoringPreview).mockReset();
    vi.mocked(commitGraphGoldAuthoringPreview).mockReset();
  });

  it("starts in safe Review mode", () => {
    const { result } = renderWorkflow();
    expect(result.current.authorMode).toBe("review");
    expect(result.current.localProposals).toEqual([]);
    expect(result.current.prepareStatus).toBe("idle");
    expect(result.current.commitStatus).toBe("idle");
    expect(result.current.verificationStatus).toBe("idle");
  });

  it("stages and accepts a local proposal, then prepares a snapshot", async () => {
    vi.mocked(prepareGraphGoldAuthoringPreview).mockResolvedValue(prepareResponse);
    const { result } = renderWorkflow();
    act(() => result.current.setSelectedText({ laneRole: "live", text: "Tripod Null-Calf", sourceOffsets: null }));
    act(() => result.current.stageNodeFromSpan());
    expect(result.current.localProposals).toHaveLength(1);
    act(() => result.current.updateProposalStatus("local-1", "accepted_local"));
    await act(async () => result.current.preparePreview());
    expect(result.current.prepareStatus).toBe("ready");
    expect(result.current.preparedRequest?.proposals[0]).toEqual(expect.objectContaining({ proposal_id: "local-1", status: "accepted_local" }));
  });

  it("clears prepared, commit, and verification state when proposals change after prepare", async () => {
    vi.mocked(prepareGraphGoldAuthoringPreview).mockResolvedValue(prepareResponse);
    const { result } = renderWorkflow();
    act(() => result.current.stageNodeAssertion({ laneRole: "live", nodeId: "node-1", label: "Node One", kind: null, role: null }));
    await act(async () => result.current.preparePreview());
    expect(result.current.prepareResponse).not.toBeNull();
    act(() => result.current.updateProposalStatus("local-1", "accepted_local"));
    await waitFor(() => expect(result.current.prepareResponse).toBeNull());
    expect(result.current.commitResponse).toBeNull();
    expect(result.current.verificationResponse).toBeNull();
  });

  it("commits the prepared request snapshot with expected fingerprint and stores verification", async () => {
    vi.mocked(prepareGraphGoldAuthoringPreview).mockResolvedValue(prepareResponse);
    vi.mocked(commitGraphGoldAuthoringPreview).mockResolvedValue(commitResponse);
    const verificationResponse = { schema: "dmb_graph_gold_authoring_verify_commit_response_v1" as const, campaign_id: "longmont-c1", session_id: "session-1", commit_id: "graph-gold-authoring-test", verification_status: "verified" as const, checked_operations: [], diagnostics: [] };
    const onReloadAndVerifyCommit = vi.fn().mockResolvedValue(verificationResponse);
    const { result } = renderWorkflow(onReloadAndVerifyCommit);
    act(() => result.current.stageNodeAssertion({ laneRole: "live", nodeId: "node-1", label: "Node One", kind: null, role: null }));
    await act(async () => result.current.preparePreview());
    act(() => result.current.setCommitConfirmed(true));
    await act(async () => result.current.commitPreparedPreview());
    expect(commitGraphGoldAuthoringPreview).toHaveBeenCalledWith(expect.objectContaining({ expected_prepare_fingerprint: "prepared-fingerprint-1", proposals: result.current.preparedRequest?.proposals }));
    await act(async () => result.current.reloadAndVerifyCommit());
    expect(onReloadAndVerifyCommit).toHaveBeenCalledWith(commitResponse);
    expect(result.current.verificationResponse).toEqual(verificationResponse);
  });

  it("preparing again clears old commit and verification state", async () => {
    vi.mocked(prepareGraphGoldAuthoringPreview).mockResolvedValue(prepareResponse);
    vi.mocked(commitGraphGoldAuthoringPreview).mockResolvedValue(commitResponse);
    const verificationResponse = { schema: "dmb_graph_gold_authoring_verify_commit_response_v1" as const, campaign_id: "longmont-c1", session_id: "session-1", commit_id: "graph-gold-authoring-test", verification_status: "verified" as const, checked_operations: [], diagnostics: [] };
    const { result } = renderWorkflow(vi.fn().mockResolvedValue(verificationResponse));
    act(() => result.current.stageNodeAssertion({ laneRole: "live", nodeId: "node-1", label: "Node One", kind: null, role: null }));
    await act(async () => result.current.preparePreview());
    act(() => result.current.setCommitConfirmed(true));
    await act(async () => result.current.commitPreparedPreview());
    await act(async () => result.current.reloadAndVerifyCommit());
    expect(result.current.commitResponse).not.toBeNull();
    expect(result.current.verificationResponse).not.toBeNull();
    await act(async () => result.current.preparePreview());
    expect(result.current.commitResponse).toBeNull();
    expect(result.current.verificationResponse).toBeNull();
    expect(result.current.commitConfirmed).toBe(false);
  });

  it("reset clears the complete local draft and prepared workflow", async () => {
    vi.mocked(prepareGraphGoldAuthoringPreview).mockResolvedValue(prepareResponse);
    const { result } = renderWorkflow();
    act(() => result.current.setSelectedText({ laneRole: "live", text: "Tripod Null-Calf", sourceOffsets: null }));
    act(() => result.current.setRelationshipDraftSource({ laneRole: "live", nodeId: "node-source" }));
    act(() => result.current.stageNodeAssertion({ laneRole: "live", nodeId: "node-1", label: "Node One", kind: null, role: null }));
    await act(async () => result.current.preparePreview());
    act(() => result.current.setCommitConfirmed(true));
    expect(result.current.localProposals).toHaveLength(1);
    act(() => result.current.resetLocalDraft());
    expect(result.current.localProposals).toEqual([]);
    expect(result.current.selectedText).toBeNull();
    expect(result.current.relationshipDraftSource).toBeNull();
    expect(result.current.prepareResponse).toBeNull();
    expect(result.current.commitResponse).toBeNull();
    expect(result.current.verificationResponse).toBeNull();
    expect(result.current.commitConfirmed).toBe(false);
  });
});
