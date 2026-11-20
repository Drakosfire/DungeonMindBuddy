import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";

vi.mock("./auth/HostedAuthGate", () => ({ HostedAuthGate: () => { throw new Error("Guest route mounted auth gate"); } }));
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
