import { describe, expect, it } from "vitest";

import {
  GRAPH_REVIEW_APPLIED_SELECTION_STORAGE_KEY,
  isInadmissibleRunIdentity,
  readAppliedSelectionFromStorage,
  readAppliedSelectionFromUrl,
  resolvePersistedAppliedSelection,
  writeAppliedSelectionToStorage,
  writeAppliedSelectionToUrl,
} from "./graphReviewAppliedSelection";

describe("graphReviewAppliedSelection", () => {
  it("reads campaign, session, and exact run_id from the URL", () => {
    expect(
      readAppliedSelectionFromUrl(
        "?campaign=longmont-c2&session=session-23&run=er_run_a",
      ),
    ).toEqual({
      campaignId: "longmont-c2",
      sessionId: "session-23",
      runId: "er_run_a",
    });
  });

  it("rejects legacy path-shaped run identity without file migration", () => {
    expect(isInadmissibleRunIdentity("artifacts/run-a/manifest.json")).toBe(true);
    expect(
      readAppliedSelectionFromUrl(
        "?campaign=longmont-c2&session=session-23&run=artifacts%2Frun-a%2Fmanifest.json",
      ),
    ).toEqual({
      campaignId: "longmont-c2",
      sessionId: "session-23",
      runId: null,
    });
  });

  it("requires both campaign and session in the URL", () => {
    expect(readAppliedSelectionFromUrl("?session=session-23")).toBeNull();
    expect(readAppliedSelectionFromUrl("?campaign=longmont-c2")).toBeNull();
  });

  it("writes run_id into the URL and round-trips through v2 sessionStorage", () => {
    window.history.replaceState({}, "", "/ingest?tool=graph-review-diagnostics");
    const selection = {
      campaignId: "longmont-c2",
      sessionId: "session-23",
      runId: "er_run_a",
    };
    writeAppliedSelectionToUrl(selection);
    expect(window.location.pathname).toBe("/ingest");
    expect(window.location.search).toContain("session=session-23");
    expect(window.location.search).toContain("campaign=longmont-c2");
    expect(window.location.search).toContain("run=er_run_a");
    expect(window.location.search).not.toContain("manifest");
    expect(window.location.search).toContain("tool=graph-review-diagnostics");

    const storage = window.sessionStorage;
    storage.clear();
    writeAppliedSelectionToStorage(selection, storage);
    expect(readAppliedSelectionFromStorage(storage)).toEqual(selection);
    expect(storage.getItem(GRAPH_REVIEW_APPLIED_SELECTION_STORAGE_KEY)).toContain("er_run_a");
    expect(storage.getItem("dmb.graph-review.applied-selection.v1")).toBeNull();
  });

  it("fills missing run from sessionStorage for the same URL session only", () => {
    const storage: Storage = {
      getItem: () =>
        JSON.stringify({
          campaignId: "longmont-c2",
          sessionId: "session-23",
          runId: "er_run_a",
        }),
      setItem: () => undefined,
      removeItem: () => undefined,
      clear: () => undefined,
      key: () => null,
      length: 0,
    };
    expect(
      resolvePersistedAppliedSelection({
        search: "?campaign=longmont-c2&session=session-23",
        storage,
      }),
    ).toEqual({
      campaignId: "longmont-c2",
      sessionId: "session-23",
      runId: "er_run_a",
    });
    expect(
      resolvePersistedAppliedSelection({
        search: "",
        storage,
      }),
    ).toBeNull();
  });
});
