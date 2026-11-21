import { act, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";

vi.mock("./auth/HostedAuthGate", () => ({
  HostedAuthGate: () => { throw new Error("Guest route mounted auth gate"); },
  dungeonMindLoginHref: () => "/api/auth/login?return_to=%2F",
}));
vi.mock("./selectedWorld/SelectedWorldContext", () => ({
  SELECTED_WORLD_LOCATION_CHANGED_EVENT: "world-location-changed",
  SelectedWorldProvider: () => { throw new Error("Guest route mounted private World provider"); },
}));
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); window.history.replaceState({}, "", "/"); });

it("opens an exact guest path without loading the private World provider", async () => {
  vi.stubEnv("VITE_GUEST_RELEASE_PAGE", "1");
  const publicId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
  window.history.replaceState({}, "", `/visit/${publicId}`);
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ release_id: "copy", manifest: {
    graph: { nodes: [], edges: [] }, sources: [], assets: [],
  } }), { status: 200 })));
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Follow the threads." })).toBeInTheDocument();
});

it("opens a guest excerpt fragment and keeps the guest route on history navigation", async () => {
  vi.stubEnv("VITE_GUEST_RELEASE_PAGE", "1");
  const publicId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
  window.history.replaceState({}, "", `/visit/${publicId}#copy/copy/point/a/source/s`);
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ release_id: "copy", manifest: {
    graph: { nodes: [{ id: "a", label: "Sizzek", kind: "character", name_citations: ["s"], kind_citations: ["s"], name_basis: "asserted", kind_basis: "asserted" }], edges: [] },
    sources: [{ id: "s", text: "Shared excerpt", evidence_role: "support" }], assets: [],
  } }), { status: 200 })));
  render(<App />);
  expect(await screen.findByText("Shared excerpt")).toBeInTheDocument();
  act(() => { window.history.pushState({}, "", "#copy/copy/point/a"); window.dispatchEvent(new PopStateEvent("popstate")); });
  expect(screen.getByRole("heading", { name: "Sizzek" })).toBeInTheDocument();
  act(() => { window.history.pushState({}, "", "#copy/copy/point/a/source/s"); window.dispatchEvent(new PopStateEvent("popstate")); });
  expect(screen.getByText("Shared excerpt")).toBeInTheDocument();
});
