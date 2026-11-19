import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "./api/liveApi";
import { makeWriteResult, mockCatalog, mockLayout, mockPlanView, mockRollEvent, mockState } from "./test/fixtures";
import { App } from "./App";

type SessionViews = Awaited<ReturnType<typeof liveApi.getSurfaceSessionViews>>;
const initialViews: SessionViews = {
  catalog: mockCatalog, layout: mockLayout, state: mockState,
  events: [], jobs: [], plan_view: mockPlanView,
};
const refreshedViews: SessionViews = {
  ...initialViews,
  state: { ...mockState, now: { ...mockState.now, day_label: "After accepted command" }, recent_event_count: 1, queued_job_count: 1 },
  events: [mockRollEvent],
  jobs: [{ schema_version: "0.1.0", id: "job-after-accept", created_at: "2026-05-28T00:01:00Z",
    campaign_id: mockState.campaign_id, session: mockState.session,
    job_type: "refresh_projection", status: "queued", source_event_id: mockRollEvent.id }],
  plan_view: { ...mockPlanView, generated_at: "2026-05-28T00:01:00Z" },
};

vi.mock("./api/liveApi");
vi.mock("./surface/SurfaceShell", () => ({
  SurfaceShell: ({ state, events, jobs, planView }: {
    state: SessionViews["state"]; events: SessionViews["events"];
    jobs: SessionViews["jobs"]; planView: SessionViews["plan_view"];
  }) => <output data-testid="surface-shell-mock">{JSON.stringify({ state, events, jobs, plan_view: planView })}</output>,
}));
vi.mock("./surface/InspectorPane", () => ({
  InspectorPane: ({
    onCommandAccepted,
  }: {
    onCommandAccepted?: (result: ReturnType<typeof makeWriteResult>) => Promise<void> | void;
  }) => (
    <button
      type="button"
      onClick={() => {
        void onCommandAccepted?.(makeWriteResult({ events_appended: [mockRollEvent.id], jobs_queued: ["job-after-accept"] }));
      }}
    >
      Trigger command accepted
    </button>
  ),
}));

describe("App command accepted callback", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    window.history.replaceState({}, "", "/surface");
    vi.mocked(liveApi.getSurfaceSessionViews)
      .mockResolvedValueOnce(initialViews)
      .mockResolvedValue(refreshedViews);
  });

  afterEach(() => { window.history.replaceState({}, "", "/"); });

  it("refreshes app data after accepted command callback", async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Trigger command accepted" })).toBeInTheDocument();
    });
    const renderedViews = () => JSON.parse(screen.getByTestId("surface-shell-mock").textContent!);
    expect(vi.mocked(liveApi.getSurfaceSessionViews)).toHaveBeenCalledTimes(1);
    expect(renderedViews()).toEqual({
      state: initialViews.state, events: initialViews.events,
      jobs: initialViews.jobs, plan_view: initialViews.plan_view,
    });

    await user.click(screen.getByRole("button", { name: "Trigger command accepted" }));

    await waitFor(() => {
      expect(vi.mocked(liveApi.getSurfaceSessionViews)).toHaveBeenCalledTimes(2);
      expect(renderedViews()).toEqual({
        state: refreshedViews.state, events: refreshedViews.events,
        jobs: refreshedViews.jobs, plan_view: refreshedViews.plan_view,
      });
    });
    expect(liveApi.getSurface).not.toHaveBeenCalled();
    expect(liveApi.getEvents).not.toHaveBeenCalled();
    expect(liveApi.getJobs).not.toHaveBeenCalled();
    expect(liveApi.getPlanView).not.toHaveBeenCalled();
  });
});
