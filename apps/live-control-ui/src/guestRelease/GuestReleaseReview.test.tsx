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
    else if (url.endsWith("/published")) body = { releases: [] };
    else if (url.endsWith("/status")) body = { public_id: null, version: 0 };
    else body = { digest, source_visibility: { source: "internal" }, manifest: {
      nodes: [], graph: { nodes: [{ id: "n", label: "Sizzek", kind: "character", name_citations: ["source"],
        kind_citations: ["source"], name_temporal: "unknown", kind_temporal: "unknown", name_basis: "inferred", kind_basis: "inferred" }], edges: [] },
      sources: [{ id: "source", text: "<private text>", evidence_role: "context" }], assets: [] } };
    return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  render(<GuestReleaseReview worldId="world" />);
  await user.click(screen.getByRole("button", { name: "Load prepared copies" }));
  await user.click(await screen.findByRole("button", { name: /Review copy from/ }));
  expect(await screen.findByText(/Sizzek · character/)).toHaveTextContent("excerpt 1");
  expect(screen.getByText("<private text>")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Excerpt 1 · private source · context, not direct support" })).toBeInTheDocument();
  const publish = screen.getByRole("button", { name: "Publish this copy" });
  expect(publish).toBeDisabled();
  await user.click(screen.getByRole("checkbox", { name: /I reviewed this copy/ }));
  await user.click(publish);
  expect(await screen.findByRole("status")).toHaveTextContent("Guest page delivery is not yet available");
  const posted = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
  expect(JSON.parse(String(posted?.[1]?.body))).toMatchObject({ digest, expected_version: 0 });
});

it("does not permit approval until the selected image has loaded", async () => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const body = url.endsWith("/candidates") ? { candidates: [{ release_id: "copy", created_at: "2026-11-20T00:00:00Z" }] }
      : url.endsWith("/published") ? { releases: [] }
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

it("shows the saved choice and both outcomes and blocks malformed copies", async () => {
  let malformed: "example" | "choice" | null = null;
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const body = url.endsWith("/candidates") ? { candidates: [{ release_id: "copy", created_at: "2026-11-20T00:00:00Z" }] }
      : url.endsWith("/published") ? { releases: [] } : url.endsWith("/status") ? { version: 0 }
      : { digest: "a".repeat(64), source_visibility: { first: "internal", second: "player_safe" }, manifest: {
        graph: { nodes: [], edges: [] }, sources: [{ id: "first", text: "First", evidence_role: "support" }, { id: "second", text: "Second", evidence_role: "context" }], assets: [],
        saved_example: { version: "owner_saved_scene_v1", title: "Scene title", body: "Owner text", references: ["first", malformed === "example" ? "foreign" : "second"], image: null },
        saved_choice: { version: malformed === "choice" ? "unknown" : "owner_saved_choice_v1", prompt: "What next", options: [
          { label: "Enter", outcome: "A bell rings" }, { label: "Wait", outcome: "A lantern flickers" }] } } };
    return new Response(JSON.stringify(body), { status: 200 });
  }));
  const user = userEvent.setup();
  render(<GuestReleaseReview worldId="world" />);
  await user.click(screen.getByRole("button", { name: "Load prepared copies" }));
  await user.click(await screen.findByRole("button", { name: /Review copy from/ }));
  expect(await screen.findByText("Owner text")).toBeInTheDocument();
  expect(screen.getByText(/excerpt 1 \(support\), excerpt 2 \(context, not direct support\)/)).toBeInTheDocument();
  expect(screen.getByText("A bell rings")).toBeInTheDocument();
  expect(screen.getByText("A lantern flickers")).toBeInTheDocument();
  expect(screen.getByText(/Both outcomes are public/)).toBeInTheDocument();
  expect(screen.getByRole("checkbox", { name: /I reviewed this copy/ })).toBeEnabled();
  malformed = "choice";
  await user.click(screen.getByRole("button", { name: /Review copy from/ }));
  expect(await screen.findByRole("alert")).toHaveTextContent("saved choice is malformed");
  expect(screen.getByRole("checkbox", { name: /I reviewed this copy/ })).toBeDisabled();
  malformed = "example";
  await user.click(screen.getByRole("button", { name: /Review copy from/ }));
  expect((await screen.findAllByRole("alert")).some(node => node.textContent?.includes("saved example is malformed"))).toBe(true);
  expect(screen.getByRole("checkbox", { name: /I reviewed this copy/ })).toBeDisabled();
});

it("requires confirmation to revoke and uses the observed pointer version to restore", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/revoke")) return new Response(null, { status: 204 });
    const body = init?.method === "POST" ? { public_id: "public", version: 5 }
      : url.endsWith("/candidates") ? { candidates: [] }
      : url.endsWith("/published") ? { releases: [{ release_id: "earlier", published_at: "2026-11-20T00:00:00Z", current: false, reviewable: true }] }
      : url.endsWith("/status") ? { version: 4 }
      : { digest: "a".repeat(64), source_visibility: {}, manifest: { graph: { nodes: [], edges: [] }, sources: [], assets: [] } };
    return new Response(JSON.stringify(body), { status: 200 });
  });
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  render(<GuestReleaseReview worldId="world" />);
  await user.click(screen.getByRole("button", { name: "Load prepared copies" }));
  await user.click(await screen.findByRole("button", { name: "Review earlier copy" }));
  await user.click(await screen.findByRole("checkbox", { name: /I reviewed this copy/ }));
  await user.click(screen.getByRole("button", { name: "Restore this copy" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Copy restored");
  const restored = fetchMock.mock.calls.find(([url]) => String(url).endsWith("/restore"));
  expect(JSON.parse(String(restored?.[1]?.body))).toEqual({ expected_version: 4 });
  await user.click(screen.getByRole("button", { name: "Withdraw this copy" }));
  expect(screen.getByRole("button", { name: "Confirm withdrawal" })).toBeDisabled();
  await user.click(screen.getByRole("checkbox", { name: "I want to revoke this copy." }));
  await user.click(screen.getByRole("button", { name: "Confirm withdrawal" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Copy revoked");
});
