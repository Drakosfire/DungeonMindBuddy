import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GRAPH_REVIEW_RUNS_CHANGED_EVENT } from "../planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils";
import {
  INGEST_RUN_CATALOG_UNAVAILABLE,
  IngestRunCatalogApiError,
  type ExtractionRunCatalogResponse,
} from "./ingestRunCatalogApi";
import { useIngestRunCatalogInformation } from "./useIngestRunCatalogInformation";

vi.mock("./ingestRunCatalogApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./ingestRunCatalogApi")>();
  return {
    ...actual,
    getExtractionRunCatalog: vi.fn(),
  };
});

import { getExtractionRunCatalog } from "./ingestRunCatalogApi";

const getCatalog = vi.mocked(getExtractionRunCatalog);

function catalog(runIds: string[]): ExtractionRunCatalogResponse {
  return {
    schema_version: "dmb_extraction_run_catalog_v1",
    runs: runIds.map((run_id) => ({
      schema_version: "dmb_extraction_run_v1" as const,
      version: "1.0",
      run_id,
      source_artifact_id: "sa_1",
      source_domain: "recap",
      status: "reviewable" as const,
      campaign_id: "longmont-c2",
      session_id: "session-23",
    })),
  };
}

describe("useIngestRunCatalogInformation", () => {
  beforeEach(() => {
    getCatalog.mockReset();
  });

  it("reuses one channel across refresh and rejects a late older completion", async () => {
    let resolveA: ((value: ExtractionRunCatalogResponse) => void) | undefined;
    let resolveB: ((value: ExtractionRunCatalogResponse) => void) | undefined;
    getCatalog
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveA = resolve;
          }),
      )
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveB = resolve;
          }),
      );

    const { result } = renderHook(() => useIngestRunCatalogInformation());
    const channel = result.current.channel;
    expect(channel.descriptor.channelId).toBe("ingest-extraction-run-catalog:v1");

    await waitFor(() => expect(getCatalog).toHaveBeenCalledTimes(1));
    act(() => {
      result.current.refresh();
    });
    await waitFor(() => expect(getCatalog).toHaveBeenCalledTimes(2));

    await act(async () => {
      resolveB?.(catalog(["er_b"]));
    });
    await waitFor(() => {
      const state = channel.getSnapshot().state;
      expect(state.status).toBe("ready");
      if (state.status === "ready") {
        expect(state.value.runs.map((run) => run.run_id)).toEqual(["er_b"]);
      }
    });
    const generationAfterB = channel.getSnapshot().generation;

    await act(async () => {
      resolveA?.(catalog(["er_a"]));
    });
    expect(channel.getSnapshot().generation).toBe(generationAfterB);
    const state = channel.getSnapshot().state;
    expect(state.status).toBe("ready");
    if (state.status === "ready") {
      expect(state.value.runs.map((run) => run.run_id)).toEqual(["er_b"]);
    }
  });

  it("disposes the channel on unmount so later completion is inert", async () => {
    let resolveCatalog: ((value: ExtractionRunCatalogResponse) => void) | undefined;
    getCatalog.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveCatalog = resolve;
        }),
    );
    const { result, unmount } = renderHook(() => useIngestRunCatalogInformation());
    const channel = result.current.channel;
    unmount();
    await act(async () => {
      resolveCatalog?.(catalog(["er_late"]));
    });
    expect(channel.getSnapshot().state.status).toBe("loading");
  });

  it("refresh via runs-changed event uses the same channel", async () => {
    getCatalog
      .mockResolvedValueOnce(catalog(["er_a"]))
      .mockResolvedValueOnce(catalog(["er_b"]));
    const { result } = renderHook(() => useIngestRunCatalogInformation());
    const channel = result.current.channel;
    await waitFor(() => expect(channel.getSnapshot().state.status).toBe("ready"));
    act(() => {
      window.dispatchEvent(new Event(GRAPH_REVIEW_RUNS_CHANGED_EVENT));
    });
    await waitFor(() => {
      const state = channel.getSnapshot().state;
      expect(state.status).toBe("ready");
      if (state.status === "ready") {
        expect(state.value.runs[0]?.run_id).toBe("er_b");
      }
    });
    expect(result.current.channel).toBe(channel);
  });

  it("maps fetch failure without inventing rows", async () => {
    getCatalog.mockRejectedValueOnce(
      new IngestRunCatalogApiError("dsn missing", 503, INGEST_RUN_CATALOG_UNAVAILABLE),
    );
    const { result } = renderHook(() => useIngestRunCatalogInformation());
    await waitFor(() => expect(result.current.channel.getSnapshot().state.status).toBe("unavailable"));
  });
});
