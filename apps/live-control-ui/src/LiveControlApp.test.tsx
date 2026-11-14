import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { LiveControlApp } from "./LiveControlApp";
import { getEvents, getJobs, getPlanView, getSurface } from "./api/liveApi";
import type { LiveQueryResponse, SurfaceLayout } from "./api/types";

const { chatResponse } = vi.hoisted(() => ({ chatResponse: { current: {} as Partial<LiveQueryResponse> } }));
beforeEach(() => vi.clearAllMocks());

vi.mock("./api/liveApi", () => ({
  getSurface: vi.fn(),
  getEvents: vi.fn(async () => ({ events: [] })),
  getJobs: vi.fn(async () => ({ jobs: [] })),
  getPlanView: vi.fn(async () => ({})),
}));
vi.mock("./agentInteraction/usePublishSurfaceInteraction", () => ({
  usePublishSurfaceInteraction: vi.fn(),
}));
vi.mock("./chrome/AppChrome", () => ({
  AppChrome: ({ children }: { children: React.ReactNode }) => children,
}));
vi.mock("./surface/InspectorPane", () => ({ InspectorPane: () => null }));
vi.mock("./surface/SurfaceShell", () => ({
  SurfaceShell: ({ layout, state, onLayoutSaved, onQuerySuccess }: {
    layout: SurfaceLayout;
    state: { enabled_modules: string[] };
    onQuerySuccess: (response: LiveQueryResponse) => void;
    onLayoutSaved: (saved: SurfaceLayout) => void;
  }) => (
    <>
    <button onClick={() => onLayoutSaved({ ...layout, saved: true } as SurfaceLayout)}>
      {"saved" in layout ? state.enabled_modules.join(", ") : "Save layout"}
    </button>
    <button onClick={() => onQuerySuccess(chatResponse.current as LiveQueryResponse)}>Complete Chat</button>
    <output>{state.enabled_modules.join(", ")}</output>
    </>
  ),
}));

it("refreshes enabled modules after saving without rereading events, jobs or Plan", async () => {
  const initial = { catalog: [], layout: {}, state: { enabled_modules: ["chat"] } };
  vi.mocked(getSurface)
    .mockResolvedValueOnce(initial as Awaited<ReturnType<typeof getSurface>>)
    .mockResolvedValueOnce({
      ...initial,
      layout: { saved: true },
      state: { enabled_modules: ["chat", "record"] },
    } as Awaited<ReturnType<typeof getSurface>>);
  render(<LiveControlApp />);
  fireEvent.click(await screen.findByRole("button", { name: "Save layout" }));

  expect(await screen.findByRole("button", { name: "chat, record" })).toBeVisible();
  expect(getSurface).toHaveBeenCalledTimes(2);
  for (const read of [getEvents, getJobs, getPlanView]) {
    expect(read).toHaveBeenCalledTimes(1);
  }
});

it.each([
  ["zero writes", {}, 1],
  ["an event", { events_written: ["event"] }, 2],
  ["a job", { jobs_queued: ["job"] }, 2],
  ["a mutation", { mutations: [{}] }, 2],
  ["an unknown mode", { mode: "other" }, 2],
  ["missing write information", { jobs_queued: undefined }, 2],
] as const)("refreshes Chat with %s", async (_label, override, expectedReads) => {
  chatResponse.current = {
    schema: "dmb_live_query_response_v1",
    mode: "live_turn",
    status: "ok",
    events_written: [],
    jobs_queued: [],
    mutations: [],
    ...override,
  };
  const initial = { catalog: [], layout: {}, state: { enabled_modules: ["chat"] } };
  vi.mocked(getSurface)
    .mockResolvedValueOnce(initial as Awaited<ReturnType<typeof getSurface>>)
    .mockResolvedValueOnce({
      ...initial,
      state: { enabled_modules: ["record"] },
    } as Awaited<ReturnType<typeof getSurface>>);
  render(<LiveControlApp />);
  fireEvent.click(await screen.findByRole("button", { name: "Complete Chat" }));

  expect(await screen.findByText("record")).toBeVisible();
  expect(getSurface).toHaveBeenCalledTimes(2);
  for (const read of [getEvents, getJobs, getPlanView]) {
    expect(read).toHaveBeenCalledTimes(expectedReads);
  }
});
