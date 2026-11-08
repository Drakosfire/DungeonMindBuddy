import { StrictMode, useEffect, type ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
function Harness({ enabled, generation = "legacy", worldId = null, children }: {
  enabled: boolean; generation?: string; worldId?: string | null; children?: ReactNode;
}) {
  return <WorldGraphLensProvider key={generation} planCampaignId="longmont-c2"
    managedWorldId={worldId} loadFocusOptions={enabled}><Observer />{children}</WorldGraphLensProvider>;
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

// An effect consumer can initiate graph/Ask work before an eventual DOM assertion.
// Observe every committed effect, including the first re-enabled render.
it.each([false, true])("gates effect consumers throughout fresh demand (StrictMode=%s)", async strict => {
  const fresh = deferred<IngestionSourceBundle>();
  const effects: string[] = [];
  const request = vi.fn();
  function Consumer({ generation }: { generation: number }) {
    const { focusValidationStatus } = useWorldGraphLens();
    useEffect(() => {
      effects.push(focusValidationStatus);
      if (focusValidationStatus === "valid") request();
    }, [focusValidationStatus, generation]);
    return null;
  }
  let freshDemand = false;
  vi.spyOn(api, "getSourceBundle").mockImplementation(() => freshDemand
    ? fresh.promise : Promise.resolve(bundleWithSessions(20)));
  const tree = (enabled: boolean, generation: number) => {
    const content = <Harness enabled={enabled}><Consumer generation={generation} /></Harness>;
    return strict ? <StrictMode>{content}</StrictMode> : content;
  };
  const view = render(tree(true, 0));
  await waitFor(() => expect(observation().status).toBe("valid"));
  expect(request).toHaveBeenCalledTimes(1);
  view.rerender(tree(false, 1));
  effects.length = 0; request.mockClear(); freshDemand = true;
  view.rerender(tree(true, 2));
  expect(effects.length).toBeGreaterThan(0);
  expect(effects).toEqual(["pending"]);
  expect(request).not.toHaveBeenCalled();
  await act(async () => fresh.resolve(bundleWithSessions(20)));
  await waitFor(() => expect(observation().status).toBe("valid"));
  expect(effects).toEqual(["pending", "valid"]);
  expect(request).toHaveBeenCalledTimes(1);
});

it("keeps exact-lens overrides explicit while fresh re-entry waits for its own result", async () => {
  const fresh = deferred<IngestionSourceBundle>();
  vi.spyOn(api, "getSourceBundle")
    .mockRejectedValueOnce(new Error("bundle unavailable"))
    .mockReturnValueOnce(fresh.promise);
  const effects: string[] = [];
  function Override({ generation }: { generation: number }) {
    const { acceptUnverifiedFocus, focusValidationStatus } = useWorldGraphLens();
    useEffect(() => { effects.push(focusValidationStatus); }, [focusValidationStatus, generation]);
    return <button onClick={acceptUnverifiedFocus}>Accept this focus</button>;
  }
  const tree = (enabled: boolean, generation: number) => <Harness enabled={enabled}>
    <Override generation={generation} />
  </Harness>;
  const view = render(tree(true, 0));
  await waitFor(() => expect(observation().status).toBe("unavailable"));
  fireEvent.click(screen.getByRole("button", { name: "Accept this focus" }));
  expect(observation().status).toBe("valid");
  view.rerender(tree(false, 1));
  effects.length = 0;
  view.rerender(tree(true, 2));
  expect(effects).toEqual(["pending"]);
  expect(observation().lens.focus).toEqual(focus);
  await act(async () => fresh.reject(new Error("fresh bundle unavailable")));
  await waitFor(() => expect(observation().status).toBe("valid"));
  expect(effects).toEqual(["pending", "valid"]);
  expect(observation().lens.focus).toEqual(focus);
});
