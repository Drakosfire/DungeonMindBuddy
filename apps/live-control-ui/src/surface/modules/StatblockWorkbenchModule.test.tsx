import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { ReadStatblockCandidateResponseV1 } from "../../api/types";
import type { GeneratedStatblockCandidateV1 } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import fixture from "../../../../../tests/fixtures/statblocks/v1/candidate-response.json";
import { presentCandidateStatus, StatblockWorkbenchModule } from "./StatblockWorkbenchModule";

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

async function loadId(id: string) {
  const user = userEvent.setup();
  render(<StatblockWorkbenchModule />);
  await user.type(screen.getByPlaceholderText("cand_…"), id);
  await user.click(screen.getByRole("button", { name: "Load candidate" }));
  return user;
}

describe("presentCandidateStatus", () => {
  it("distinguishes integrity failure from dependency unavailable", () => {
    expect(presentCandidateStatus("unavailable", "integrity_failure").stateKind).toBe(
      "integrity_failure",
    );
    expect(presentCandidateStatus("unavailable", "downstream_unavailable").stateKind).toBe(
      "dependency_unavailable",
    );
    expect(presentCandidateStatus("missing", null).stateKind).toBe("missing");
    expect(presentCandidateStatus("expired", "downstream_expired").stateKind).toBe("expired");
  });
});

describe("StatblockWorkbenchModule", () => {
  it("loads an exact candidate and renders structured mechanics", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);

    await loadId("cand_fixture1");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Ironhide Brute" })).toBeTruthy();
    });
    expect(liveApi.getStatblockCandidate).toHaveBeenCalledWith("cand_fixture1");
    expect(screen.getByText("Greatclub")).toBeTruthy();
    expect(screen.queryByText("Generate mock draft")).toBeNull();
    expect(screen.queryByText("Preview corpus promotion")).toBeNull();
  });

  it("shows expired state without mock fallback", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue({
      schema: "dmb_statblock_candidate_read_v1",
      candidate_id: "cand_expired1",
      status: "expired",
      failure_category: "downstream_expired",
      failure_message: "candidate expired",
    });

    await loadId("cand_expired1");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Candidate expired" })).toBeTruthy();
    });
    expect(screen.getByText(/cand_expired1/)).toBeTruthy();
    expect(document.querySelector('[data-candidate-status="expired"]')).toBeTruthy();
    expect(screen.queryByText("Generate mock draft")).toBeNull();
  });

  it("shows missing state without mock fallback", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue({
      schema: "dmb_statblock_candidate_read_v1",
      candidate_id: "cand_missing1",
      status: "missing",
    });

    await loadId("cand_missing1");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Candidate missing" })).toBeTruthy();
    });
    expect(screen.getByText(/cand_missing1/)).toBeTruthy();
    expect(document.querySelector('[data-candidate-status="missing"]')).toBeTruthy();
    expect(screen.queryByText(/DungeonMindServer outage/i)).toBeNull();
    expect(screen.queryByText("Generate mock draft")).toBeNull();
  });

  it("shows integrity failure distinctly from dependency unavailable", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue({
      schema: "dmb_statblock_candidate_read_v1",
      candidate_id: "cand_integrity1",
      status: "unavailable",
      failure_category: "integrity_failure",
      failure_message: "candidate cache digest mismatch",
    });

    await loadId("cand_integrity1");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Candidate integrity failure" })).toBeTruthy();
    });
    expect(screen.getByText(/not a DungeonMindServer outage/i)).toBeTruthy();
    expect(screen.getByText(/cand_integrity1/)).toBeTruthy();
    expect(document.querySelector('[data-candidate-status="integrity_failure"]')).toBeTruthy();
    expect(screen.queryByText("Candidate service unavailable")).toBeNull();
    expect(screen.queryByText("Generate mock draft")).toBeNull();
  });

  it("shows dependency unavailable for non-integrity unavailable categories", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue({
      schema: "dmb_statblock_candidate_read_v1",
      candidate_id: "cand_down1",
      status: "unavailable",
      failure_category: "downstream_unavailable",
      failure_message: "upstream timeout",
    });

    await loadId("cand_down1");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Candidate service unavailable" })).toBeTruthy();
    });
    expect(document.querySelector('[data-candidate-status="dependency_unavailable"]')).toBeTruthy();
    expect(screen.queryByText(/integrity failure/i)).toBeNull();
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
