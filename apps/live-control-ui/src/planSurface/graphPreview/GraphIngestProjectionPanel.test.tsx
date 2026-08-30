import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import { GraphIngestProjectionPanel } from "./GraphIngestProjectionPanel";

vi.mock("../../api/liveApi", async () => {
  const actual = await vi.importActual<typeof import("../../api/liveApi")>("../../api/liveApi");
  return {
    ...actual,
    getLatestGraphIngestRun: vi.fn(),
    getUnionSupergraphProjection: vi.fn(),
  };
});

const context = {
  campaignId: "longmont-c2",
  ingestSession: 23,
} as const;

describe("GraphIngestProjectionPanel", () => {
  beforeEach(() => {
    vi.mocked(liveApi.getLatestGraphIngestRun).mockReset();
    vi.mocked(liveApi.getUnionSupergraphProjection).mockReset();
    vi.mocked(liveApi.getLatestGraphIngestRun).mockResolvedValue({
      run: {
        status: "ready",
        run_label: "Run A",
        run_id: "run-a",
        generated_at: "2026-01-01T00:00:00Z",
        model_id: "model",
        model_provider: "provider",
        extraction_profile: "profile",
        extraction_mode: "mode",
        vocabulary_mode: "vocab",
        preview_union_available: true,
        preview_union_store_path: "artifacts/run-a/preview-union.json",
        manifest_path: "artifacts/run-a/manifest.json",
        node_count: 3,
        edge_count: 2,
        evidence_ref_count: 1,
        next_actions: [],
      },
    } as never);
  });

  it("does not offer Open Union Graph and never calls the retired projection API", async () => {
    render(<GraphIngestProjectionPanel context={context as never} />);

    await waitFor(() =>
      expect(
        screen.getByTestId("union-supergraph-preview-retired"),
      ).toBeInTheDocument(),
    );
    expect(screen.queryByRole("button", { name: /Open Union Graph/i })).not.toBeInTheDocument();
    expect(liveApi.getUnionSupergraphProjection).not.toHaveBeenCalled();
    expect(liveApi.getLatestGraphIngestRun).toHaveBeenCalled();
  });
});
