import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { LiveControlApp } from "./LiveControlApp";
import { getSurface, getSurfaceSessionViews } from "./api/liveApi";
import type { LiveQueryResponse, ProjectionWriteResult, SurfaceLayout } from "./api/types";

vi.mock("./api/liveApi", () => ({
  getSurface: vi.fn(),
  getSurfaceSessionViews: vi.fn(),
}));
vi.mock("./agentInteraction/usePublishSurfaceInteraction", () => ({
  usePublishSurfaceInteraction: vi.fn(),
}));
vi.mock("./chrome/AppChrome", () => ({
  AppChrome: ({ children }: { children: React.ReactNode }) => children,
}));
vi.mock("./surface/InspectorPane", () => ({
  InspectorPane: ({ onCommandAccepted }: {
    onCommandAccepted: (result: ProjectionWriteResult) => Promise<void>;
  }) => <button onClick={() => void onCommandAccepted({} as ProjectionWriteResult)}>Accept command</button>,
}));
beforeEach(() => vi.resetAllMocks());
vi.mock("./surface/SurfaceShell", () => ({
  SurfaceShell: ({ layout, state, events, jobs, planView, onLayoutSaved, onQuerySuccess }: {
    layout: SurfaceLayout;
    state: { enabled_modules: string[] };
    events: { id: string }[];
    jobs: { id: string }[];
    planView: { timeline: string[] };
    onQuerySuccess: (response: LiveQueryResponse) => Promise<void>;
    onLayoutSaved: (saved: SurfaceLayout) => void;
  }) => (
    <>
      <button onClick={() => onLayoutSaved({ ...layout, saved: true } as SurfaceLayout)}>
        {"saved" in layout ? state.enabled_modules.join(", ") : "Save layout"}
      </button>
      <button onClick={() => void onQuerySuccess({} as LiveQueryResponse)}>Complete Chat</button>
      <output>{[events[0]?.id, jobs[0]?.id, ...planView.timeline].filter(Boolean).join(", ")}</output>
    </>
  ),
}));

it("refreshes enabled modules after saving without rereading events, jobs or Plan", async () => {
  const initial = { catalog: [], layout: {}, state: { enabled_modules: ["chat"] } };
  vi.mocked(getSurfaceSessionViews).mockResolvedValueOnce({
    ...initial, events: [], jobs: [], plan_view: { timeline: [] },
  } as Awaited<ReturnType<typeof getSurfaceSessionViews>>);
  vi.mocked(getSurface).mockResolvedValueOnce({
      ...initial,
      layout: { saved: true },
      state: { enabled_modules: ["chat", "record"] },
    } as Awaited<ReturnType<typeof getSurface>>);
  render(<LiveControlApp />);
  fireEvent.click(await screen.findByRole("button", { name: "Save layout" }));

  expect(await screen.findByRole("button", { name: "chat, record" })).toBeVisible();
  expect(getSurface).toHaveBeenCalledTimes(1);
  expect(getSurfaceSessionViews).toHaveBeenCalledTimes(1);
});

it.each(["Complete Chat", "Accept command"])("refreshes all session views after %s", async (action) => {
  const initial = {
    catalog: [], layout: {}, state: { enabled_modules: ["chat"] },
    events: [], jobs: [], plan_view: { timeline: [] },
  };
  type SessionViews = Awaited<ReturnType<typeof getSurfaceSessionViews>>;
  vi.mocked(getSurfaceSessionViews)
    .mockResolvedValueOnce(initial as SessionViews)
    .mockResolvedValueOnce({
      ...initial,
      events: [{ id: "new event" }],
      jobs: [{ id: "updated job" }],
      plan_view: { timeline: ["updated plan"] },
    } as unknown as SessionViews);

  render(<LiveControlApp />);
  fireEvent.click(await screen.findByRole("button", { name: action }));

  expect(await screen.findByText("new event, updated job, updated plan")).toBeVisible();
  expect(getSurfaceSessionViews).toHaveBeenCalledTimes(2);
  expect(getSurface).not.toHaveBeenCalled();
});
