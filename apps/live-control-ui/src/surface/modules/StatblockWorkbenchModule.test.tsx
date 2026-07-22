import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import { LiveApiError } from "../../api/liveApi";
import type { ReadStatblockCandidateResponseV1 } from "../../api/types";
import { StatblockWorkbenchModule } from "./StatblockWorkbenchModule";

const here = dirname(fileURLToPath(import.meta.url));
const fixturePath = resolve(
  here,
  "../../../../../tests/fixtures/statblocks/v1/candidate-response.json",
);
const candidateFixture = JSON.parse(readFileSync(fixturePath, "utf8")) as Record<string, unknown>;

function activeResponse(
  overrides: Partial<ReadStatblockCandidateResponseV1> = {},
): ReadStatblockCandidateResponseV1 {
  return {
    schema: "dmb_statblock_candidate_read_v1",
    candidate_id: "cand_fixture1",
    status: "active",
    candidate: candidateFixture,
    ...overrides,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("StatblockWorkbenchModule", () => {
  it("loads and renders an exact typed candidate", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse());

    render(<StatblockWorkbenchModule />);

    await user.type(screen.getByLabelText("Candidate ID"), "cand_fixture1");
    await user.click(screen.getByRole("button", { name: "Load candidate" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Ironhide Brute" })).toBeInTheDocument();
    });
    expect(liveApi.getStatblockCandidate).toHaveBeenCalledWith("cand_fixture1");
    expect(screen.getByText(/Greatclub/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Activate retrieval/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Preview corpus promotion/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /mock generate/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Generate mock/i })).not.toBeInTheDocument();
  });

  it("shows honest not-found state without mock fallback", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "getStatblockCandidate").mockRejectedValue(
      new LiveApiError("missing", 404),
    );

    render(<StatblockWorkbenchModule />);
    await user.type(screen.getByLabelText("Candidate ID"), "cand_missing");
    await user.click(screen.getByRole("button", { name: "Load candidate" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("cand_missing was not found");
    });
    expect(screen.queryByRole("heading", { name: "Ironhide Brute" })).not.toBeInTheDocument();
  });

  it("shows expired state and retains locator", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(
      activeResponse({ status: "expired" }),
    );

    render(<StatblockWorkbenchModule />);
    await user.type(screen.getByLabelText("Candidate ID"), "cand_fixture1");
    await user.click(screen.getByRole("button", { name: "Load candidate" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("expired");
    });
    expect(screen.getByText(/Exact locator/i)).toHaveTextContent("cand_fixture1");
  });

  it("shows unavailable state without mock fallback", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue({
      schema: "dmb_statblock_candidate_read_v1",
      candidate_id: "cand_fixture1",
      status: "unavailable",
      failure_category: "downstream_unavailable",
      failure_message: "DungeonMind statblock service unavailable",
    });

    render(<StatblockWorkbenchModule />);
    await user.type(screen.getByLabelText("Candidate ID"), "cand_fixture1");
    await user.click(screen.getByRole("button", { name: "Load candidate" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("unavailable");
    });
    expect(screen.queryByText(/Geomantic Drake/i)).not.toBeInTheDocument();
  });

  it("reloads the same candidate id", async () => {
    const user = userEvent.setup();
    const spy = vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse());

    render(<StatblockWorkbenchModule />);
    await user.type(screen.getByLabelText("Candidate ID"), "cand_fixture1");
    await user.click(screen.getByRole("button", { name: "Load candidate" }));
    await screen.findByRole("heading", { name: "Ironhide Brute" });
    await user.click(screen.getByRole("button", { name: "Reload" }));

    await waitFor(() => {
      expect(spy).toHaveBeenCalledTimes(2);
    });
    expect(spy).toHaveBeenNthCalledWith(2, "cand_fixture1");
  });
});
