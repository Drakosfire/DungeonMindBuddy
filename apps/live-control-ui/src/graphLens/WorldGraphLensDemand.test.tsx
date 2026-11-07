import { StrictMode } from "react";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api/liveApi";
import type { IngestionSourceBundle, SourceUnit } from "../api/types";
import { WorldGraphLensProvider, useWorldGraphLens } from "./WorldGraphLensContext";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
function bundleWithSessions(...sessions: number[]): IngestionSourceBundle {
  return {
    schema_version: "dmb_ingestion_source_bundle_v1", bundle_id: "demand-fixture",
    scope: "campaign-ingested", corpus_root: "corpus", artifacts: [], anchors: [],
    units: sessions.map((sessionNumber): SourceUnit => ({
      unitId: `unit-${sessionNumber}`, artifactId: `artifact-${sessionNumber}`,
      anchorId: `anchor-${sessionNumber}`, unitKind: "normalized_recap",
      label: `Session ${sessionNumber}`, fields: { sessionNumber },
      sourceAnchor: {
        anchorId: `anchor-${sessionNumber}`, artifactId: `artifact-${sessionNumber}`,
        label: `Session ${sessionNumber}`, anchorKind: "document",
        locator: { locatorId: `loc-${sessionNumber}`, scheme: "corpus_path", value: `session-${sessionNumber}.md` },
        relatedLocators: [], displaySummary: null, metadata: {},
      },
      canonState: "played_canon", lifecycleState: "ingested", evidenceRole: "source_evidence",
      authorityState: "played_truth", visibilityState: "gm_private", provenance: [], diagnostics: {},
    })), coverage: {}, diagnostics: [],
  };
}
function Observer() {
  const value = useWorldGraphLens();
  return <output data-testid="lens-state">{JSON.stringify({
    lens: value.lens, focusOptions: value.focusOptions,
    status: value.focusValidationStatus, derived: value.derived,
  })}</output>;
}
function Harness({ enabled, generation = "legacy", worldId = null }: {
  enabled: boolean; generation?: string; worldId?: string | null;
}) {
  return <WorldGraphLensProvider key={generation} planCampaignId="longmont-c2"
    managedWorldId={worldId} loadFocusOptions={enabled}><Observer /></WorldGraphLensProvider>;
}
function observation() { return JSON.parse(screen.getByTestId("lens-state").textContent!); }
const focus = { campaignId: "longmont-c2", sessionNumber: 20 };
beforeEach(() => window.history.replaceState({}, "", "/?session=longmont-c2:20"));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("legacy focus bundle demand", () => {
  it("does no HTTP under inert StrictMode entry and loads only when enabled", async () => {
    const load = vi.spyOn(api, "getSourceBundle").mockResolvedValue(bundleWithSessions(20));
    const fetch = vi.spyOn(globalThis, "fetch");
    const view = render(<StrictMode><Harness enabled={false} /></StrictMode>);
    expect(observation()).toMatchObject({ lens: { focus }, focusOptions: [], status: "pending" });
    expect(load).not.toHaveBeenCalled(); expect(fetch).not.toHaveBeenCalled();
    view.rerender(<StrictMode><Harness enabled /></StrictMode>);
    await waitFor(() => expect(observation().status).toBe("valid"));
    expect(load).toHaveBeenCalledTimes(1);
    expect(load).toHaveBeenCalledWith("campaign-ingested", "longmont-c2");
    expect(observation().focusOptions).toEqual([
      { campaignId: "longmont-c2", sessionNumber: 20, label: "C2 · Session 20" },
    ]);
  });
  it.each(["resolve", "reject"] as const)("retires pending %s while disabled and re-enables a fresh request", async settlement => {
    const old = deferred<IngestionSourceBundle>(), fresh = deferred<IngestionSourceBundle>();
    const load = vi.spyOn(api, "getSourceBundle")
      .mockReturnValueOnce(old.promise).mockReturnValueOnce(fresh.promise);
    const view = render(<Harness enabled />);
    expect(load).toHaveBeenCalledTimes(1);
    view.rerender(<Harness enabled={false} />);
    const inert = observation();
    expect(inert).toMatchObject({ lens: { focus }, focusOptions: [], status: "pending" });
    await act(async () => {
      if (settlement === "resolve") old.resolve(bundleWithSessions(99));
      else old.reject(new Error("retired request failed"));
    });
    expect(observation()).toEqual(inert);
    expect(new URLSearchParams(window.location.search).get("session")).toBe("longmont-c2:20");
    view.rerender(<Harness enabled />);
    expect(load).toHaveBeenCalledTimes(2); expect(observation().status).toBe("pending");
    await act(async () => fresh.resolve(bundleWithSessions(20)));
    await waitFor(() => expect(observation().status).toBe("valid"));
    expect(observation().lens.focus).toEqual(focus);
    expect(observation().focusOptions.map((option: {sessionNumber: number}) => option.sessionNumber)).toEqual([20]);
  });
  it("drops loaded options when disabled without clearing retained URL focus", async () => {
    const load = vi.spyOn(api, "getSourceBundle").mockResolvedValue(bundleWithSessions(20));
    const view = render(<Harness enabled />);
    await waitFor(() => expect(observation().status).toBe("valid"));
    view.rerender(<Harness enabled={false} />);
    expect(observation()).toMatchObject({ lens: { focus }, focusOptions: [], status: "pending" });
    expect(new URLSearchParams(window.location.search).get("session")).toBe("longmont-c2:20");
    expect(load).toHaveBeenCalledTimes(1);
  });
  it("ignores a legacy completion after replacement by another World provider", async () => {
    const old = deferred<IngestionSourceBundle>();
    const load = vi.spyOn(api, "getSourceBundle").mockReturnValue(old.promise);
    const view = render(<Harness enabled />);
    expect(load).toHaveBeenCalledTimes(1);
    view.rerender(<Harness enabled generation="world-b" worldId="world-b" />);
    const current = observation();
    expect(current).toMatchObject({ lens: { selectedCampaignIds: [], focus: null },
      focusOptions: [], status: "none", derived: null });
    await act(async () => old.resolve(bundleWithSessions(99)));
    expect(observation()).toEqual(current); expect(load).toHaveBeenCalledTimes(1);
  });
});
