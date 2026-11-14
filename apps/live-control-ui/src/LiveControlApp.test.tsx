import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { LiveControlApp } from "./LiveControlApp";
import { getEvents, getJobs, getPlanView, getSurface } from "./api/liveApi";
import type { SurfaceLayout } from "./api/types";

vi.mock("./api/liveApi", () => ({
  getSurface: vi.fn(async () => ({ catalog: [], layout: {}, state: {} })),
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
  SurfaceShell: ({ layout, onLayoutSaved }: {
    layout: SurfaceLayout;
    onLayoutSaved: (saved: SurfaceLayout) => void;
  }) => (
    <button onClick={() => onLayoutSaved({ ...layout, saved: true } as SurfaceLayout)}>
      {"saved" in layout ? "Saved layout" : "Save layout"}
    </button>
  ),
}));

it("uses the saved layout without rereading surface, events, jobs or Plan", async () => {
  render(<LiveControlApp />);
  fireEvent.click(await screen.findByRole("button", { name: "Save layout" }));

  expect(await screen.findByRole("button", { name: "Saved layout" })).toBeVisible();
  for (const read of [getSurface, getEvents, getJobs, getPlanView]) {
    expect(read).toHaveBeenCalledTimes(1);
  }
});
