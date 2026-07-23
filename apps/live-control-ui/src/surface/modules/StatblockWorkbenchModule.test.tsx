import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { ReadStatblockCandidateResponseV1 } from "../../api/types";
import type { GeneratedStatblockCandidateV1 } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import fixture from "../../../../../tests/fixtures/statblocks/v1/candidate-response.json";
import { StatblockWorkbenchModule } from "./StatblockWorkbenchModule";

const candidate = fixture as GeneratedStatblockCandidateV1;

const activeResponse: ReadStatblockCandidateResponseV1 = {
  schema: "dmb_statblock_candidate_read_v1",
  candidate_id: candidate.candidate_id,
  status: "active",
  candidate,
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("StatblockWorkbenchModule", () => {
  it("loads an exact candidate and renders structured mechanics", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);

    render(<StatblockWorkbenchModule />);
    await user.type(screen.getByPlaceholderText("cand_…"), "cand_fixture1");
    await user.click(screen.getByRole("button", { name: "Load candidate" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Ironhide Brute" })).toBeTruthy();
    });
    expect(liveApi.getStatblockCandidate).toHaveBeenCalledWith("cand_fixture1");
    expect(screen.getByText("Greatclub")).toBeTruthy();
    expect(screen.queryByText("Generate mock draft")).toBeNull();
    expect(screen.queryByText("Preview corpus promotion")).toBeNull();
  });

  it("shows expired state without mock fallback", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue({
      schema: "dmb_statblock_candidate_read_v1",
      candidate_id: "cand_expired1",
      status: "expired",
      failure_category: "downstream_expired",
      failure_message: "candidate expired",
    });

    render(<StatblockWorkbenchModule />);
    await user.type(screen.getByPlaceholderText("cand_…"), "cand_expired1");
    await user.click(screen.getByRole("button", { name: "Load candidate" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Candidate expired" })).toBeTruthy();
    });
    expect(screen.getByText(/cand_expired1/)).toBeTruthy();
    expect(screen.queryByText("Generate mock draft")).toBeNull();
  });

  it("generates from a ThreatDraft then loads the returned candidate", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "generateThreatDraftCandidate").mockResolvedValue({
      schema: "dmb_generate_threat_draft_candidate_response_v1",
      draft_id: "td_test",
      generated_from_draft_version: 1,
      request_id: "req_1",
      outcome: "success",
      candidate,
      cache_status: "stored",
      persistence_failures: [],
    });
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);

    render(<StatblockWorkbenchModule />);
    await user.type(screen.getByPlaceholderText("td_…"), "td_test");
    await user.click(screen.getByRole("button", { name: "Generate candidate" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Ironhide Brute" })).toBeTruthy();
    });
    expect(liveApi.generateThreatDraftCandidate).toHaveBeenCalledWith("td_test", {
      expected_draft_version: 1,
    });
    expect(liveApi.getStatblockCandidate).toHaveBeenCalledWith("cand_fixture1");
  });
});
