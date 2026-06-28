import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import { RecapGraphModule } from "./RecapGraphModule";
import { session23UnionSupergraphFixture } from "./unionSupergraphFixture";

const context = {
  campaignId: "longmont-c2",
  ingestSession: 22,
  liveSession: 22,
  target: { target_type: "session", target_id: "session-22" },
} as const;

function mockArtifacts() {
  vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({
    records: [
      {
        campaign_id: "longmont-c2",
        session: 24,
        session_id: "session-24",
        title: "Session 24",
        canonical_path: "Session 24.md",
        normalized_path: "_normalized/Session 24.md",
        updated_at: "2026-06-28T00:00:00Z",
      },
    ],
  });
}

describe("RecapGraphModule", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/plan?tool=recap&session=session-24");
    mockArtifacts();
    vi.spyOn(liveApi, "getGraphPreviewRuns").mockResolvedValue({ runs: [] });
    vi.spyOn(liveApi, "getRecapGraphPresentation").mockResolvedValue({} as never);
  });

  it("requests the latest graph-ingest projection for the URL session", async () => {
    const getUnion = vi.spyOn(liveApi, "getUnionSupergraphProjection").mockResolvedValue({
      ...session23UnionSupergraphFixture,
      session_id: "session-24",
      focus: { ...session23UnionSupergraphFixture.focus, focus_session_id: "session-24" },
    });

    render(<RecapGraphModule context={context} />);

    await waitFor(() => {
      expect(getUnion).toHaveBeenCalledWith({
        campaignId: "longmont-c2",
        sessionId: "session-24",
        useLatestGraphIngest: true,
      });
    });
    expect(await screen.findByText(/Source: latest graph-ingest preview/i)).toBeInTheDocument();
  });

  it("falls back to the default union projection when latest graph-ingest is missing", async () => {
    vi.spyOn(liveApi, "getUnionSupergraphProjection").mockRejectedValue(
      new liveApi.LiveApiError("latest missing", 404),
    );
    const fallback = vi.spyOn(liveApi, "getDefaultUnionSupergraphProjection").mockResolvedValue({
      ...session23UnionSupergraphFixture,
      session_id: "session-24",
      focus: { ...session23UnionSupergraphFixture.focus, focus_session_id: "session-24" },
    });

    render(<RecapGraphModule context={context} />);

    await waitFor(() => expect(fallback).toHaveBeenCalledWith("session-24"));
    expect(await screen.findByText(/Source: default preview fixture/i)).toBeInTheDocument();
  });

  it("offers legacy recap preview when union projection is unavailable", async () => {
    vi.spyOn(liveApi, "getUnionSupergraphProjection").mockRejectedValue(
      new liveApi.LiveApiError("latest missing", 404),
    );
    vi.spyOn(liveApi, "getDefaultUnionSupergraphProjection").mockRejectedValue(
      new liveApi.LiveApiError("fixture missing", 404),
    );

    render(<RecapGraphModule context={context} />);

    expect(await screen.findByRole("button", { name: "Open legacy recap preview" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("No union-supergraph projection is available for session-24");
  });
});
