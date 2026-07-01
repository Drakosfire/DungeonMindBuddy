import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { RecapArtifactRecord } from "../../api/types";
import { RecapGraphModule } from "./RecapGraphModule";
import { session23UnionSupergraphFixture } from "./unionSupergraphFixture";

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
        sourceRecapPath: artifactRecord(24).source_recap_path,
        sourceRecapSha256: artifactRecord(24).source_sha256,
      });
    });
    expect(await screen.findByText(/Source: latest graph-ingest preview/i)).toBeInTheDocument();
  });

  it("defaults to the latest ingested recap artifact when no URL session is provided", async () => {
    window.history.replaceState({}, "", "/plan?tool=recap");
    vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({
      records: [artifactRecord(23), artifactRecord(24)],
    });
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
        sourceRecapPath: artifactRecord(24).source_recap_path,
        sourceRecapSha256: artifactRecord(24).source_sha256,
      });
    });
  });

  it("shows graph projection unavailable when recap exists but latest graph-ingest is missing", async () => {
    vi.spyOn(liveApi, "getUnionSupergraphProjection").mockRejectedValue(
      new liveApi.LiveApiError("latest missing", 404),
    );
    const fallback = vi.spyOn(liveApi, "getDefaultUnionSupergraphProjection").mockResolvedValue({} as never);

    render(<RecapGraphModule context={context} />);

    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open legacy recap preview" })).not.toBeInTheDocument();
    expect(fallback).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Graph projection is not ready for session-24 in longmont-c2. Recap memory exists, but no lineage-matched preview union projection was found.",
    );
  });

  it("does not fall back to the default fixture when no recap artifact exists", async () => {
    vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({ records: [] });
    vi.spyOn(liveApi, "getUnionSupergraphProjection").mockRejectedValue(
      new liveApi.LiveApiError("latest missing", 404),
    );
    const fallback = vi.spyOn(liveApi, "getDefaultUnionSupergraphProjection").mockResolvedValue({} as never);

    render(<RecapGraphModule context={context} />);

    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open legacy recap preview" })).not.toBeInTheDocument();
    expect(fallback).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "No ingested recap artifact or union-supergraph projection is available for session-22 in longmont-c2.",
    );
  });

  it("uses the campaign-specific recap record when session numbers collide across campaigns", async () => {
    window.history.replaceState({}, "", "/plan?tool=recap&session=session-1&campaign=longmont-c1");
    vi.spyOn(liveApi, "getRecapArtifacts").mockImplementation(async (campaignId) => {
      if (campaignId === "longmont-c1") {
        return {
          records: [
            {
              ...artifactRecord(1),
              artifact_id: "longmont-c1/session-1",
              campaign_id: "longmont-c1",
              session_id: "session-1",
              source_recap_path:
                "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Stonebridge.md",
              source_sha256: "sha256:c1-session-1",
              run_manifest_uri:
                "evals/graph_memory_layer/artifacts/graph_ingest_runs/session_1_vocabulary_ablation_projection_dogfood/graph_ingest_run_manifest.json",
            },
          ],
        };
      }
      return { records: [] };
    });
    const getUnion = vi.spyOn(liveApi, "getUnionSupergraphProjection").mockResolvedValue({
      ...session23UnionSupergraphFixture,
      campaign_id: "longmont-c1",
      session_id: "session-1",
      focus: { ...session23UnionSupergraphFixture.focus, focus_session_id: "session-1" },
    });

    render(<RecapGraphModule context={context} />);

    await waitFor(() => {
      expect(getUnion).toHaveBeenCalledWith({
        campaignId: "longmont-c1",
        sessionId: "session-1",
        useLatestGraphIngest: true,
        graphRunManifestPath:
          "evals/graph_memory_layer/artifacts/graph_ingest_runs/session_1_vocabulary_ablation_projection_dogfood/graph_ingest_run_manifest.json",
        sourceRecapPath:
          "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Stonebridge.md",
        sourceRecapSha256: "sha256:c1-session-1",
      });
    });
  });

  it("loads the selected campaign when the campaign picker changes", async () => {
    window.history.replaceState({}, "", "/plan?tool=recap&session=session-1&campaign=longmont-c2");
    const getArtifacts = vi.spyOn(liveApi, "getRecapArtifacts").mockImplementation(async (campaignId) => ({
      records:
        campaignId === "longmont-c2"
          ? [
              {
                ...artifactRecord(1),
                artifact_id: "longmont-c2/session-1",
                campaign_id: "longmont-c2",
                session_id: "session-1",
                source_recap_path:
                  "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 01 - Let the Games Begin.md",
                source_sha256: "sha256:c2-session-1",
              },
            ]
          : [],
    }));
    vi.spyOn(liveApi, "getUnionSupergraphProjection").mockResolvedValue({
      ...session23UnionSupergraphFixture,
      campaign_id: "longmont-c2",
      session_id: "session-1",
      focus: { ...session23UnionSupergraphFixture.focus, focus_session_id: "session-1" },
    });

    render(<RecapGraphModule context={context} />);

    await waitFor(() => {
      expect(getArtifacts).toHaveBeenCalledWith("longmont-c2");
    });
  });

  it("does not offer legacy recap preview when union projection is unavailable", async () => {
    vi.spyOn(liveApi, "getUnionSupergraphProjection").mockRejectedValue(
      new liveApi.LiveApiError("latest missing", 404),
    );
    vi.spyOn(liveApi, "getDefaultUnionSupergraphProjection").mockRejectedValue(
      new liveApi.LiveApiError("fixture missing", 404),
    );

    render(<RecapGraphModule context={context} />);

    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open legacy recap preview" })).not.toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Graph projection is not ready for session-24 in longmont-c2. Recap memory exists, but no lineage-matched preview union projection was found.",
    );
  });
});
