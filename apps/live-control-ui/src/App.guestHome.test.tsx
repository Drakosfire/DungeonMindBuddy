import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useEffect, type ReactNode } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";

const lifecycle = vi.hoisted(() => ({ mounted: 0, unmounted: 0 }));
vi.mock("./api/liveApi", () => ({ invalidateHostedGraphAccess: vi.fn() }));
vi.mock("./selectedWorld/SelectedWorldContext", () => ({
  SELECTED_WORLD_LOCATION_CHANGED_EVENT: "world-location-changed",
  SelectedWorldProvider: ({ children }: { children: ReactNode }) => {
    useEffect(() => { lifecycle.mounted++; return () => { lifecycle.unmounted++; }; }, []);
    return <div data-testid="private-world-provider">{children}</div>;
  },
}));
vi.mock("./BuddyApp", () => ({ BuddyApp: () => <div>Personal welcome</div> }));

const publicId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const manifest = { release_id: "copy", manifest: {
  graph: { nodes: [{ id: "a", label: "Demo point", kind: "character", name_citations: ["s"], kind_citations: ["s"], name_basis: "asserted", kind_basis: "asserted" }], edges: [] },
  sources: [{ id: "s", text: "Demo excerpt", evidence_role: "support" }], assets: [],
} };
const reply = (status: number, body?: unknown) => new Response(body === undefined ? null : JSON.stringify(body), { status });
beforeEach(() => {
  lifecycle.mounted = 0; lifecycle.unmounted = 0;
  vi.stubEnv("PROD", true);
  vi.stubEnv("VITE_GUEST_RELEASE_PAGE", "1");
  vi.stubEnv("VITE_GUEST_HOME_PUBLIC_ID", publicId);
  window.history.replaceState({}, "", "/");
});
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); window.history.replaceState({}, "", "/"); });

it("opens the configured demo at signed-out Home without a private World provider", async () => {
  window.history.replaceState({}, "", "/#copy/copy/point/a/source/s");
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => String(input) === "/api/auth/session"
    ? reply(401) : reply(200, manifest));
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  expect(await screen.findByText("Demo excerpt")).toBeInTheDocument();
  expect(screen.queryByTestId("private-world-provider")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Sign in to create your World/ })).toHaveAttribute("href", "/api/auth/login?return_to=%2F");
  expect(fetchMock.mock.calls.map(call => String(call[0])).sort()).toEqual(["/api/auth/session", `/api/live/guest-releases/${publicId}`].sort());
  act(() => { window.history.pushState({}, "", "#copy/old/point/a/source/s"); window.dispatchEvent(new PopStateEvent("popstate")); });
  expect(screen.getByText("Every story has a trail.")).toBeInTheDocument();
});

it("unmounts a pending guest fetch on sign-in and returns on sign-out", async () => {
  let session = "signed_out";
  let releaseRequests = 0;
  let finishRelease!: (value: Response) => void;
  const pending = new Promise<Response>(resolve => { finishRelease = resolve; });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => String(input) === "/api/auth/session"
    ? session === "signed_out" ? reply(401) : reply(200, { status: "authenticated", subject: session })
    : releaseRequests++ === 0 ? pending : reply(200, manifest)));
  render(<App />);
  expect(await screen.findByText("Opening this guest World…")).toBeInTheDocument();
  expect(screen.queryByTestId("private-world-provider")).not.toBeInTheDocument();
  session = "owner-a";
  fireEvent.focus(window);
  expect(await screen.findByText("Personal welcome")).toBeInTheDocument();
  await act(async () => { finishRelease(reply(200, manifest)); await pending; });
  expect(screen.queryByText("Demo excerpt")).not.toBeInTheDocument();
  session = "signed_out";
  fireEvent.focus(window);
  expect(await screen.findByText("Follow the threads.")).toBeInTheDocument();
  expect(screen.queryByTestId("private-world-provider")).not.toBeInTheDocument();
});

it("does not fall back to private state when the configured copy is withdrawn", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => String(input) === "/api/auth/session" ? reply(401) : reply(404));
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent("This guest World is unavailable");
  expect(screen.queryByTestId("private-world-provider")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Sign in to Buddy" })).toHaveAttribute("href", "/api/auth/login?return_to=%2F");
  expect(fetchMock.mock.calls.map(call => String(call[0])).sort()).toEqual(["/api/auth/session", `/api/live/guest-releases/${publicId}`].sort());
});

it("keeps the ordinary welcome when configuration is malformed", async () => {
  vi.stubEnv("VITE_GUEST_HOME_PUBLIC_ID", "not-a-public-id");
  const fetchMock = vi.fn(async () => reply(401));
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  expect(await screen.findByText("Personal welcome")).toBeInTheDocument();
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  expect(fetchMock.mock.calls[0][0]).toBe("/api/auth/session");
});

it("does not show a guest or personal World while auth is unavailable", async () => {
  let unavailable = false;
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => String(input) === "/api/auth/session"
    ? unavailable ? reply(503) : reply(401) : reply(200, manifest)));
  render(<App />);
  expect(await screen.findByText("Follow the threads.")).toBeInTheDocument();
  unavailable = true;
  fireEvent.focus(window);
  expect(await screen.findByRole("heading", { name: "Sign-in status is unavailable" })).toBeInTheDocument();
  expect(screen.queryByTestId("private-world-provider")).not.toBeInTheDocument();
  expect(screen.queryByText("Follow the threads.")).not.toBeInTheDocument();
});

it("does not use the root demo as a query-bearing sign-in bypass", async () => {
  window.history.replaceState({}, "", "/?auth_error=cancelled");
  const fetchMock = vi.fn(async () => reply(401));
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  expect(await screen.findByText("Sign-in was cancelled. You can try again when you are ready.")).toBeInTheDocument();
  expect(fetchMock.mock.calls.map(call => String(call[0]))).toEqual(["/api/auth/session"]);
  expect(screen.queryByTestId("private-world-provider")).not.toBeInTheDocument();
});

it("keeps local-operator Home on its existing path", async () => {
  vi.stubEnv("PROD", false);
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  expect(await screen.findByText("Personal welcome")).toBeInTheDocument();
  expect(screen.getByTestId("private-world-provider")).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();
});

it("keeps legacy Home anchors on the ordinary welcome", async () => {
  window.history.replaceState({}, "", "/#buddy-about");
  const fetchMock = vi.fn(async () => reply(401));
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  expect(await screen.findByText("Personal welcome")).toBeInTheDocument();
  expect(fetchMock.mock.calls.map(call => String(call[0]))).toEqual(["/api/auth/session"]);
});

it("keeps malformed release fragments inside the configured demo without private reads", async () => {
  window.history.replaceState({}, "", "/#copy/copy/point/%E0%A4%A");
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => String(input) === "/api/auth/session" ? reply(401) : reply(200, manifest));
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  expect(await screen.findByText("Every story has a trail.")).toBeInTheDocument();
  expect(screen.queryByTestId("private-world-provider")).not.toBeInTheDocument();
  expect(fetchMock.mock.calls.map(call => String(call[0])).sort()).toEqual(["/api/auth/session", `/api/live/guest-releases/${publicId}`].sort());
});

it("remounts personal Home when the authenticated account changes", async () => {
  let subject = "owner-a";
  vi.stubGlobal("fetch", vi.fn(async () => reply(200, { status: "authenticated", subject })));
  render(<App />);
  expect(await screen.findByText("Personal welcome")).toBeInTheDocument();
  expect(lifecycle.mounted).toBe(1);
  subject = "owner-b";
  fireEvent.focus(window);
  await waitFor(() => expect(lifecycle.mounted).toBe(2));
  expect(lifecycle.unmounted).toBe(1);
  expect(screen.queryByText("Follow the threads.")).not.toBeInTheDocument();
});
