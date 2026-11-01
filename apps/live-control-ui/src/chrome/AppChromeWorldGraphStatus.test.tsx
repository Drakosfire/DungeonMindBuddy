import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, expect, it, vi } from "vitest";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { AskPluginSlotProvider } from "../agentInteraction/AskPluginSlot";
import { SurfaceContextProvider } from "../surfaceInteraction/contextHost";
import { PeekRegionProvider } from "../surfaceInteraction/peekHost";
import { AppChrome } from "./AppChrome";
import { AppChromeWorldGraphStatus } from "./AppChromeWorldGraphStatus";
import { getNativeGraphCatalog, postManagedWorldGraphProjection, postWorldGraphProjection } from "../api/liveApi";
import type { SelectedWorldState } from "../selectedWorld/SelectedWorldContext";

const selected = vi.hoisted(() => ({ world: { kind: "managed", worldId: "elderwyld", name: "Elderwyld", documentId: null } as SelectedWorldState }));
vi.mock("../selectedWorld/SelectedWorldContext", async () => ({ ...await vi.importActual("../selectedWorld/SelectedWorldContext"), useSelectedWorld: () => selected.world }));
vi.mock("../api/liveApi", async () => ({ ...await vi.importActual("../api/liveApi"), getNativeGraphCatalog: vi.fn(), postManagedWorldGraphProjection: vi.fn(), postWorldGraphProjection: vi.fn() }));
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
});
beforeEach(() => {
  vi.clearAllMocks();
  selected.world = { kind: "managed", worldId: "elderwyld", name: "Elderwyld", documentId: null };
  vi.mocked(getNativeGraphCatalog).mockResolvedValue({ schema: "dmb_native_graph_catalog_v1", scope: { managed_world_id: "elderwyld", native_world_id: "native", binding_version: 3, revision_id: "published", scope_mode: "world", campaign_id: null },
    catalogue: { identity: { space_id: "native", revision_id: "published" }, entities: [{ entity_id: "e1" }], admitted_assertion_ids: [], completeness: { status: "complete", reason: null }, request_sha256: "hash", result_digest: "digest" }, assertions: [] });
});
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it.each(["index", "plan", "build", "ingest"] as const)("offers the same published Graph on %s without a readiness claim or prefetch", route => {
  render(<AgentInteractionProvider><AskPluginSlotProvider><SurfaceContextProvider><PeekRegionProvider><AppChrome activeRoute={route}><main>page</main></AppChrome></PeekRegionProvider></SurfaceContextProvider></AskPluginSlotProvider></AgentInteractionProvider>);
  const launcher = screen.getByRole("button", { name: "Explore Elderwyld World graph" });
  expect(launcher).toHaveTextContent("Graph");
  expect(launcher).not.toHaveTextContent(/Ready|0 nodes/);
  expect(getNativeGraphCatalog).not.toHaveBeenCalled();
  expect(postManagedWorldGraphProjection).not.toHaveBeenCalled();
  expect(postWorldGraphProjection).not.toHaveBeenCalled();
});

it("opens the existing native inspector directly from chrome", async () => {
  render(<AppChromeWorldGraphStatus />);
  fireEvent.click(screen.getByRole("button", { name: "Explore Elderwyld World graph" }));
  expect(await screen.findByText(/1 objects.*Complete for this view/)).toBeInTheDocument();
  expect(screen.getByRole("dialog", { name: "Elderwyld World graph" })).toBeVisible();
  expect(getNativeGraphCatalog).toHaveBeenCalledWith({ managed_world_id: "elderwyld", scope_mode: "world", campaign_id: null }, expect.any(AbortSignal));
  expect(screen.queryByRole("group", { name: "Graph material" })).not.toBeInTheDocument();
  expect(postManagedWorldGraphProjection).not.toHaveBeenCalled();
  expect(postWorldGraphProjection).not.toHaveBeenCalled();
});

it("reports unavailable native authority without showing classic counts or falling back", async () => {
  vi.mocked(getNativeGraphCatalog).mockRejectedValue(new Error("Native authority unavailable"));
  render(<AppChromeWorldGraphStatus />);
  fireEvent.click(screen.getByRole("button", { name: "Explore Elderwyld World graph" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Native authority unavailable");
  expect(screen.queryByText(/0 objects|0 nodes|Ready/)).not.toBeInTheDocument();
  expect(postManagedWorldGraphProjection).not.toHaveBeenCalled();
  expect(postWorldGraphProjection).not.toHaveBeenCalled();
});

it("does not invent a World when none is verified", () => {
  selected.world = { kind: "legacy" };
  render(<AppChromeWorldGraphStatus />);
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  expect(getNativeGraphCatalog).not.toHaveBeenCalled();
});
