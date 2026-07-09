import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../api/liveApi", () => ({
  prepareGraphObjectAuthoringWrite: vi.fn(),
  commitGraphObjectAuthoringWrite: vi.fn(),
}));

import {
  commitGraphObjectAuthoringWrite,
  prepareGraphObjectAuthoringWrite,
} from "../../api/liveApi";
import { buildManualGraphAuthoringSelection } from "./graphAuthoringSelection";
import {
  buildGraphObjectAuthoringProposal,
  createDefaultGraphObjectAuthoringFormState,
} from "./graphObjectAuthoringDraft";
import { useGraphObjectAuthoringQuickCommit } from "./useGraphObjectAuthoringQuickCommit";

describe("useGraphObjectAuthoringQuickCommit", () => {
  beforeEach(() => {
    vi.mocked(prepareGraphObjectAuthoringWrite).mockReset();
    vi.mocked(commitGraphObjectAuthoringWrite).mockReset();
  });

  it("prepares and commits a single object proposal, returning the created node id", async () => {
    vi.mocked(prepareGraphObjectAuthoringWrite).mockResolvedValue({
      prepared: true,
      campaign_id: "longmont-c1",
      overlay_path: "/tmp/overlay.json",
      event_log_path: "/tmp/events.jsonl",
      current_overlay_token: "token-before",
      proposed_assertions_digest: "digest",
      confirm_token: "confirm-token",
      assertion_count: 1,
      event_count: 1,
      assertions_preview: [],
      overlay_summary: {
        existing_assertion_count: 0,
        proposed_assertion_count: 1,
        total_assertion_count: 1,
        object_count: 1,
        link_existing_count: 0,
        relationship_count: 0,
        merge_objects_count: 0,
      },
      diagnostics: [],
      no_mutation_guarantees: [],
    });
    vi.mocked(commitGraphObjectAuthoringWrite).mockResolvedValue({
      committed: true,
      campaign_id: "longmont-c1",
      overlay_path: "/tmp/overlay.json",
      event_log_path: "/tmp/events.jsonl",
      assertion_count: 1,
      event_count: 1,
      new_overlay_token: "token-after",
      diagnostics: [],
      no_mutation_guarantees: [],
      created_node_ids: { "local-1": "authored:assert-abc" },
    });

    const selection = buildManualGraphAuthoringSelection({
      campaignId: "longmont-c1",
      sessionId: "session-2",
    });
    const proposal = buildGraphObjectAuthoringProposal(
      selection,
      {
        ...createDefaultGraphObjectAuthoringFormState(selection),
        label: "Questionable Company",
      },
      "local-1",
    );

    const { result } = renderHook(() =>
      useGraphObjectAuthoringQuickCommit({
        campaignId: "longmont-c1",
        sessionId: "session-2",
      }),
    );

    let commitResult: Awaited<ReturnType<typeof result.current.commitObjectProposal>> | undefined;
    await act(async () => {
      commitResult = await result.current.commitObjectProposal(proposal);
    });

    await waitFor(() => {
      expect(result.current.committing).toBe(false);
    });

    expect(commitResult).toEqual({
      committed: true,
      nodeId: "authored:assert-abc",
    });
    expect(prepareGraphObjectAuthoringWrite).toHaveBeenCalledTimes(1);
    expect(commitGraphObjectAuthoringWrite).toHaveBeenCalledTimes(1);
  });

  it("surfaces commit failure without throwing", async () => {
    vi.mocked(prepareGraphObjectAuthoringWrite).mockResolvedValue({
      prepared: true,
      campaign_id: "longmont-c1",
      overlay_path: "/tmp/overlay.json",
      event_log_path: "/tmp/events.jsonl",
      current_overlay_token: "token-before",
      proposed_assertions_digest: "digest",
      confirm_token: "confirm-token",
      assertion_count: 1,
      event_count: 1,
      assertions_preview: [],
      overlay_summary: {
        existing_assertion_count: 0,
        proposed_assertion_count: 1,
        total_assertion_count: 1,
        object_count: 1,
        link_existing_count: 0,
        relationship_count: 0,
        merge_objects_count: 0,
      },
      diagnostics: [],
      no_mutation_guarantees: [],
    });
    vi.mocked(commitGraphObjectAuthoringWrite).mockResolvedValue({
      committed: false,
      campaign_id: "longmont-c1",
      overlay_path: "/tmp/overlay.json",
      event_log_path: "/tmp/events.jsonl",
      assertion_count: 1,
      event_count: 0,
      new_overlay_token: "token-after",
      diagnostics: [{ code: "event_log_write_failed", message: "Event log failed.", severity: "error" }],
      no_mutation_guarantees: [],
    });

    const selection = buildManualGraphAuthoringSelection({
      campaignId: "longmont-c1",
      sessionId: "session-2",
    });
    const proposal = buildGraphObjectAuthoringProposal(
      selection,
      {
        ...createDefaultGraphObjectAuthoringFormState(selection),
        label: "Questionable Company",
      },
      "local-1",
    );

    const { result } = renderHook(() =>
      useGraphObjectAuthoringQuickCommit({
        campaignId: "longmont-c1",
        sessionId: "session-2",
      }),
    );

    let commitResult: Awaited<ReturnType<typeof result.current.commitObjectProposal>> | undefined;
    await act(async () => {
      commitResult = await result.current.commitObjectProposal(proposal);
    });

    expect(commitResult).toEqual({ committed: false, nodeId: null });
    expect(result.current.error).toBe("Event log failed.");
  });
});
