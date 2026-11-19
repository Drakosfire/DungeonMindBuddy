// Registered path retained until the active CI classification lease permits relocation.
import { StrictMode, useMemo, type ReactNode } from "react";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "../App";
import { AppChrome } from "../chrome/AppChrome";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import { usePublishSurfaceInteraction } from "../agentInteraction/usePublishSurfaceInteraction";
import { buildSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";

vi.mock("../selectedWorld/SelectedWorldContext", async original => ({
  ...await original<typeof import("../selectedWorld/SelectedWorldContext")>(),
  SelectedWorldProvider: ({ children }: { children: React.ReactNode }) => children,
  useSelectedWorld: () => ({ kind: "legacy" }),
  useSelectedWorldAdmission: () => ({ kind: "ready" }),
}));
vi.mock("../appEntryShared", async original => {
  const actual = await original<typeof import("../appEntryShared")>();
  return { ...actual, IsolatedEntry: ({ children }: { children: ReactNode }) =>
    <actual.IsolatedEntry>{children}<Probe /></actual.IsolatedEntry> };
});
vi.mock("../agentInteraction/AgentInteractionChrome", async original => {
  const actual = await original<typeof import("../agentInteraction/AgentInteractionChrome")>();
  return { ...actual, AgentInteractionChrome: () => <div data-testid="authoring-host-probe" style={{ display: "contents" }}><actual.AgentInteractionChrome /><Probe /></div> };
});
vi.mock("../buildSurface/BuildSurfacePage", () => ({
  BuildSurfacePage: () => {
    const publication = useMemo<SurfaceInteractionPublication>(() => ({
      surfaceId: "build", label: "Build fixture",
      identity: buildSurfaceInteractionIdentity({ surfaceId: "build", instanceParts: ["landing-navigation-fixture"] }),
      canvas: null, agentContext: null, editCommands: [], projectionBindings: [],
      tools: [{ id: "fixture-tool", label: "Fixture tool",
        placement: { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0 },
        availability: { status: "enabled" as const },
        activation: { kind: "projection" as const, projectionId: "fixture-projection" } }],
      projections: [{ id: "fixture-projection", kind: "tool" as const,
        preferredSize: "wide" as const, bindingIds: [] }],
    }), []);
    const { activateProjectionTool } = useAgentInteraction();
    usePublishSurfaceInteraction(publication);
    return <AppChrome activeRoute="build"><h1>Build fixture</h1><button onClick={() => activateProjectionTool("fixture-tool")}>Open fixture projection</button></AppChrome>;
  },
}));

function Probe() {
  const { surfaceInteractionPublication: publication, active } = useAgentInteraction();
  return <><output data-testid="publication">{JSON.stringify(publication)}</output>
    <output data-testid="active-projection">{JSON.stringify(active)}</output></>;
}

afterEach(() => {
  vi.restoreAllMocks();
  window.history.replaceState({}, "", "/");
  localStorage.clear();
});

it("navigates the current landing through Build and Back/Forward with isolated capabilities", async () => {
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Unexpected HTTP on inert entry"));
  window.history.replaceState({}, "", "/");
  render(<StrictMode><App /></StrictMode>);
  await screen.findByRole("heading", { name: /Your world,\s*ready for the table\./i });
  expect(JSON.parse(screen.getByTestId("publication").textContent!)).toBeNull();
  expect(JSON.parse(screen.getByTestId("active-projection").textContent!)).toBeNull();
  expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
  expect(fetchSpy).not.toHaveBeenCalled();
  expect(screen.queryByTestId("agent-interaction-chrome")).not.toBeInTheDocument();
  expect(screen.queryByTestId("authoring-host-probe")).not.toBeInTheDocument();
  const nav = screen.getByRole("navigation", { name: "Command board navigation" });
  fireEvent.click(within(nav).getByRole("button", { name: "Open navigation" }));
  const build = within(nav).getByRole("link", { name: "Build" });
  const modified = new MouseEvent("click", { bubbles: true, cancelable: true, ctrlKey: true });
  const push = vi.spyOn(window.history, "pushState");
  // React's delegated handler has already run when the event reaches document.
  // Capture its decision, then suppress jsdom's unsupported new-tab navigation.
  let preventedByReact: boolean | undefined;
  document.addEventListener("click", event => {
    preventedByReact = event.defaultPrevented;
    event.preventDefault();
  }, { once: true });
  fireEvent(build, modified);
  expect(preventedByReact).toBe(false);
  expect(push).not.toHaveBeenCalled();
  fireEvent.click(build);
  await screen.findByRole("heading", { name: "Build fixture" });
  expect(screen.getByRole("button", { name: "Tools" })).toBeInTheDocument();
  expect(screen.getAllByTestId("authoring-host-probe")).toHaveLength(1);
  fireEvent.click(screen.getByRole("button", { name: "Open fixture projection" }));
  expect(JSON.parse(screen.getByTestId("active-projection").textContent!)).toMatchObject({ kind: "tool", key: "fixture-projection" });
  await act(async () => { window.history.back(); });
  await screen.findByRole("heading", { name: /Your world,\s*ready for the table\./i });
  expect(screen.queryByRole("heading", { name: "Build fixture" })).not.toBeInTheDocument();
  expect(screen.queryByTestId("agent-interaction-chrome")).not.toBeInTheDocument();
  expect(screen.queryByTestId("authoring-host-probe")).not.toBeInTheDocument();
  expect(JSON.parse(screen.getByTestId("active-projection").textContent!)).toBeNull();
  expect(JSON.parse(screen.getByTestId("publication").textContent!)).toBeNull();
  expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
  await act(async () => { window.history.forward(); });
  await waitFor(() => expect(window.location.pathname).toBe("/build"));
  await screen.findByRole("heading", { name: "Build fixture" });
  expect(screen.getAllByTestId("authoring-host-probe")).toHaveLength(1);
  // This fixture publishes tools, not an Ask plugin; the real dock stays gated.
  expect(screen.queryByTestId("agent-interaction-chrome")).not.toBeInTheDocument();
  expect(JSON.parse(screen.getByTestId("active-projection").textContent!)).toBeNull();
  expect(screen.getByRole("button", { name: "Tools" })).toBeInTheDocument();
});
