import { StrictMode, useMemo } from "react";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "../App";
import { AppChrome } from "../chrome/AppChrome";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import { usePublishSurfaceInteraction } from "../agentInteraction/usePublishSurfaceInteraction";
import { validateSurfaceInteractionPublication } from "../surfaceInteraction/publication";
import { BlankSurface } from "./BlankSurface";
import { blankSurfacePublication, LANDING_SURFACE } from "./blankSurface";

vi.mock("../selectedWorld/SelectedWorldContext", async original => ({
  ...await original<typeof import("../selectedWorld/SelectedWorldContext")>(),
  SelectedWorldProvider: ({ children }: { children: React.ReactNode }) => children,
  useSelectedWorld: () => ({ kind: "legacy" }),
  useSelectedWorldAdmission: () => ({ kind: "ready" }),
}));
vi.mock("../agentInteraction/AgentInteractionChrome", async original => {
  const actual = await original<typeof import("../agentInteraction/AgentInteractionChrome")>();
  return { ...actual, AgentInteractionChrome: () => <><actual.AgentInteractionChrome /><Probe /></> };
});
vi.mock("../buildSurface/BuildSurfacePage", () => ({
  BuildSurfacePage: () => {
    const publication = useMemo(() => ({
      ...blankSurfacePublication({surfaceId: "build", label: "Build fixture", ambientSummary: "Build"}),
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
const second = { surfaceId: "inert-fixture", label: "Another blank", ambientSummary: "No work here" };

afterEach(() => {
  vi.restoreAllMocks();
  window.history.replaceState({}, "", "/");
  localStorage.clear();
});

it("constructs two neutral nonauthoring Surfaces with no fabricated work or capabilities", () => {
  for (const descriptor of [LANDING_SURFACE, second]) {
    const publication = blankSurfacePublication(descriptor);
    expect(validateSurfaceInteractionPublication(publication)).toMatchObject({ valid: true });
    expect(publication).toMatchObject({
      surfaceId: descriptor.surfaceId,
      canvas: null,
      agentContext: { campaignId: null, documentId: null, sessionNumber: null },
      tools: [], editCommands: [], projections: [], projectionBindings: [],
    });
  }
});

it("binds, replaces and releases either descriptor under StrictMode", () => {
  const tree = (descriptor: typeof second | null) => <StrictMode><AgentInteractionProvider>
    {descriptor && <BlankSurface descriptor={descriptor} />}
    <Probe />
  </AgentInteractionProvider></StrictMode>;
  const view = render(tree(LANDING_SURFACE));
  expect(JSON.parse(screen.getByTestId("publication").textContent!)).toMatchObject({ surfaceId: "index", tools: [] });
  view.rerender(tree(second));
  expect(screen.getByRole("heading", { name: second.label })).toBeInTheDocument();
  expect(JSON.parse(screen.getByTestId("publication").textContent!)).toMatchObject({ surfaceId: second.surfaceId });
  view.rerender(tree(null));
  expect(screen.getByTestId("publication")).toHaveTextContent("null");
  view.rerender(tree(LANDING_SURFACE));
  expect(JSON.parse(screen.getByTestId("publication").textContent!)).toMatchObject({ surfaceId: "index" });
});

it("opens the real blank App without HTTP, retains shared hosts, and replays Build and Back/Forward", async () => {
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Unexpected HTTP on inert entry"));
  window.history.replaceState({}, "", "/");
  render(<StrictMode><App /></StrictMode>);
  await screen.findByRole("heading", { name: "Buddy Surface" });
  expect(screen.getByRole("region", { name: "Blank workspace" })).toBeEmptyDOMElement();
  expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
  expect(fetchSpy).not.toHaveBeenCalled();
  expect(screen.getByTestId("agent-interaction-chrome")).toHaveAttribute("data-surface-id", "index");
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
  fireEvent.click(screen.getByRole("button", { name: "Open fixture projection" }));
  expect(screen.getByTestId("active-projection")).toHaveTextContent("fixture-projection");
  await act(async () => { window.history.back(); });
  await screen.findByRole("heading", { name: "Buddy Surface" });
  expect(screen.queryByRole("heading", { name: "Build fixture" })).not.toBeInTheDocument();
  expect(screen.getAllByTestId("agent-interaction-chrome")).toHaveLength(1);
  expect(screen.getByTestId("active-projection")).toHaveTextContent("null");
  expect(JSON.parse(screen.getByTestId("publication").textContent!)).toMatchObject({
    surfaceId: "index", canvas: null, tools: [], editCommands: [], projections: [],
  });
  expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
  await act(async () => { window.history.forward(); });
  await waitFor(() => expect(window.location.pathname).toBe("/build"));
  await screen.findByRole("heading", { name: "Build fixture" });
});
