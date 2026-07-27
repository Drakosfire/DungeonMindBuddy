import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { RecapArtifactRecord } from "../../api/types";
import { RecapGraphModule } from "./RecapGraphModule";
import { session23WorldGraphRecapFixture } from "./worldGraphRecapFixture";

const context = {
  campaignId: "longmont-c2",
  ingestSession: 22,
  liveSession: 22,
  target: { target_type: "session", target_id: "session-22" },
} as const;

function artifactRecord(session: number): RecapArtifactRecord {
  return {
    schema_version: "dmb_recap_artifact_record_v1",
    artifact_id: `longmont-c2/session-${session}`,
    campaign_id: "longmont-c2",
    session_id: `session-${session}`,
    source_artifact_id: null,
    source_recap_path: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session ${session} - Dogfood.md`,
    breadcrumb_seed_path: null,
    session_memory_records_path: null,
    run_bundle_uri: "",
    run_manifest_uri: "",
    source_span_index_uri: "",
    provenance_index_uri: null,
    graph_run_refs: [],
    default_graph_run_uri: null,
    default_projection_mode: "recap_graph",
    source_sha256: `sha256:session-${session}`,
    registered_at: "2026-06-28T00:00:00Z",
    updated_at: "2026-06-28T00:00:00Z",
    registry_source: "scan",
  };
}

function mockArtifacts() {
  vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({
    records: [artifactRecord(24)],
  });
}

describe("RecapGraphModule", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/plan?tool=recap&session=session-24");
    mockArtifacts();
  });

  it("requests World Graph recap projection for the URL session", async () => {
    const postRecap = vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue({
      ...session23WorldGraphRecapFixture,
      sessionId: "session-24",
    });

    render(<RecapGraphModule context={context} />);

    await waitFor(() => {
      expect(postRecap).toHaveBeenCalledWith({
        schema: "dmb_world_graph_projection_request_v1",
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        scopeMode: "campaign",
        focus: { kind: "session", sessionId: "session-24", campaignId: "longmont-c2" },
        admissibility: "gm",
      });
    });
    expect((await screen.findAllByText(/Published World Graph/i)).length).toBeGreaterThan(0);
  });

  it("defaults to the latest ingested recap artifact when no URL session is provided", async () => {
    window.history.replaceState({}, "", "/plan?tool=recap");
    vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({
      records: [artifactRecord(23), artifactRecord(24)],
    });
    const postRecap = vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue({
      ...session23WorldGraphRecapFixture,
      sessionId: "session-24",
    });

    render(<RecapGraphModule context={context} />);

    await waitFor(() => {
      expect(postRecap).toHaveBeenCalledWith(
        expect.objectContaining({ focus: expect.objectContaining({ sessionId: "session-24" }) }),
      );
    });
  });

  it("succeeds when recap memory exists but preview union is absent", async () => {
    vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue(session23WorldGraphRecapFixture);

    render(<RecapGraphModule context={context} />);

    expect((await screen.findAllByText(/Published World Graph/i)).length).toBeGreaterThan(0);
    expect(await screen.findByRole("button", { name: /Caelynn/i })).toBeInTheDocument();
  });

  it("shows unavailable message for recap_markdown_unavailable without preview fallback", async () => {
    vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockRejectedValue(
      new liveApi.LiveApiError("recap missing", 404, { code: "recap_markdown_unavailable" }),
    );

    render(<RecapGraphModule context={context} />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Canonical normalized recap is unavailable for session-24 in longmont-c2.",
    );
  });

  it("uses campaign-specific session selection without manifest fields in graph request", async () => {
    window.history.replaceState({}, "", "/plan?tool=recap&session=session-1&campaign=longmont-c1");
    vi.spyOn(liveApi, "getRecapArtifacts").mockImplementation(async (campaignId) => {
      if (campaignId === "longmont-c1") {
        return { records: [{ ...artifactRecord(1), campaign_id: "longmont-c1", session_id: "session-1" }] };
      }
      return { records: [] };
    });
    const postRecap = vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue({
      ...session23WorldGraphRecapFixture,
      campaignId: "longmont-c1",
      sessionId: "session-1",
    });

    render(<RecapGraphModule context={context} />);

    await waitFor(() => {
      expect(postRecap).toHaveBeenCalledWith(
        expect.objectContaining({ campaignId: "longmont-c1", focus: expect.objectContaining({ sessionId: "session-1" }) }),
      );
    });
    const body = postRecap.mock.calls[0]?.[0];
    expect(body).not.toHaveProperty("revisionPin");
  });
});

describe("RecapGraphModule PR380B World Graph authority", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/plan?tool=recap&session=session-24");
    mockArtifacts();
  });

  it("does not call Union/latest-ingest selectors", async () => {
    const getUnion = vi.spyOn(liveApi, "getUnionSupergraphProjection");
    vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue(session23WorldGraphRecapFixture);

    render(<RecapGraphModule context={context} />);
    await screen.findByText(/Published World Graph/i);
    expect(getUnion).not.toHaveBeenCalled();
  });

  it("exposes Continue in Build with pointer-only URL fields", async () => {
    vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue(session23WorldGraphRecapFixture);
    render(<RecapGraphModule context={context} />);
    const chip = await screen.findByRole("button", { name: /Caelynn/i });
    fireEvent.click(chip);
    const continueLink = await screen.findByRole("link", { name: /Continue in Build/i });
    expect(continueLink.getAttribute("href")).toContain("campaign=longmont-c2");
    expect(continueLink.getAttribute("href")).toContain("graphNodeId=pc_caelynn");
    expect(continueLink.getAttribute("href")).toContain(`graphRevision=${session23WorldGraphRecapFixture.snapshot.revisionId}`);
  });
});
