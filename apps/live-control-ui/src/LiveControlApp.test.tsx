import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { LiveControlApp } from "./LiveControlApp";
import { getEvents, getJobs, getPlanView, getSurface } from "./api/liveApi";
import type { SurfaceLayout } from "./api/types";

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
  SurfaceShell: ({ layout, state, onLayoutSaved }: {
    layout: SurfaceLayout;
    state: { enabled_modules: string[] };
    onLayoutSaved: (saved: SurfaceLayout) => void;
  }) => (
    <button onClick={() => onLayoutSaved({ ...layout, saved: true } as SurfaceLayout)}>
      {"saved" in layout ? state.enabled_modules.join(", ") : "Save layout"}
    </button>
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
