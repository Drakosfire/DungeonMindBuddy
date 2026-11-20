import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { GuestReleaseReview } from "./GuestReleaseReview";

afterEach(() => vi.unstubAllGlobals());

it("shows the exact staged copy and requires explicit approval before publication", async () => {
  const digest = "a".repeat(64);
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    let body: unknown;
    if (init?.method === "POST") body = { public_id: "public", version: 1 };
    else if (url.endsWith("/candidates")) body = { candidates: [{ release_id: "copy", created_at: "2026-11-20T00:00:00Z" }] };
    else if (url.endsWith("/status")) body = { public_id: null, version: 0 };
    else body = { digest, source_visibility: { source: "internal" }, manifest: {
      nodes: [], graph: { nodes: [{ id: "n", label: "Sizzek", kind: "character", name_citations: ["source"],
        kind_citations: ["source"], name_temporal: "unknown", kind_temporal: "unknown" }], edges: [] },
      sources: [{ id: "source", text: "<private text>" }], assets: [] } };
    return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  render(<GuestReleaseReview worldId="world" />);
  await user.click(screen.getByRole("button", { name: "Load prepared copies" }));
  await user.click(await screen.findByRole("button", { name: /Review copy from/ }));
  expect(await screen.findByText(/Sizzek · character/)).toHaveTextContent("excerpt 1");
  expect(screen.getByText("<private text>")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Excerpt 1 · private source" })).toBeInTheDocument();
  const publish = screen.getByRole("button", { name: "Publish this copy" });
  expect(publish).toBeDisabled();
  await user.click(screen.getByRole("checkbox", { name: /I reviewed this copy/ }));
  await user.click(publish);
  expect(await screen.findByRole("status")).toHaveTextContent("Guest delivery is not yet available");
  const posted = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
  expect(JSON.parse(String(posted?.[1]?.body))).toMatchObject({ digest, expected_version: 0 });
});

it("does not permit approval until the selected image has loaded", async () => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const body = url.endsWith("/candidates") ? { candidates: [{ release_id: "copy", created_at: "2026-11-20T00:00:00Z" }] }
      : url.endsWith("/status") ? { version: 0 }
      : { digest: "a".repeat(64), source_visibility: {}, manifest: { graph: { nodes: [], edges: [] }, sources: [], assets: [{ id: "image" }] } };
    return new Response(JSON.stringify(body), { status: 200 });
  }));
  const user = userEvent.setup();
  render(<GuestReleaseReview worldId="world" />);
  await user.click(screen.getByRole("button", { name: "Load prepared copies" }));
  await user.click(await screen.findByRole("button", { name: /Review copy from/ }));
  const image = await screen.findByRole("img", { name: "Selected release image 1" });
  const approval = screen.getByRole("checkbox", { name: /I reviewed this copy/ });
  expect(approval).toBeDisabled();
  fireEvent.load(image);
  expect(approval).toBeEnabled();
  fireEvent.error(image);
  expect(approval).toBeDisabled();
});
