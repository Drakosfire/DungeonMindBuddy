import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { GuestReleasePage } from "./GuestReleasePage";

afterEach(() => vi.unstubAllGlobals());

it("follows a released relationship to its excerpt without loading private World APIs", async () => {
  const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => new Response(JSON.stringify({ release_id: "copy", manifest: {
    graph: { nodes: [
      { id: "a", label: "Sizzek", kind: "character", name_citations: ["s"], kind_citations: ["s"], name_basis: "inferred", kind_basis: "asserted" },
      { id: "b", label: "Funhouse", kind: "place", name_citations: ["s"], kind_citations: ["s"], name_basis: "asserted", kind_basis: "asserted" },
    ], edges: [{ id: "e", source: "a", target: "b", label: "visits", citations: ["s"], temporal: "unknown", basis: "inferred" }] },
    sources: [{ id: "s", text: "A saved excerpt.", evidence_role: "context" }], assets: [],
  } }), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  render(<GuestReleasePage publicId="public" />);
  await user.click(await screen.findByRole("button", { name: /Sizzek/ }));
  expect(screen.getByText("visits").parentElement).toHaveTextContent("Sizzek visits Funhouse");
  expect(screen.getByText(/inferred · When this happened is not specified/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Explore Funhouse" })).toBeInTheDocument();
  const citations = screen.getAllByRole("button", { name: "Read context 1" });
  await user.click(citations[citations.length - 1]);
  expect(screen.getByText("A saved excerpt.")).toBeInTheDocument();
  expect(screen.getByText("Context for this claim; not direct support.")).toBeInTheDocument();
  expect(screen.getByText(/read-only snapshot/i)).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock.mock.calls[0][0]).toBe("/api/live/guest-releases/public");
  expect(fetchMock.mock.calls[0][1]).toMatchObject({ credentials: "omit", cache: "no-store" });
});

it("shows an unavailable state when a release is withdrawn", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 404 })));
  render(<GuestReleasePage publicId="public" />);
  expect(await screen.findByRole("alert")).toHaveTextContent("This guest World is unavailable");
  expect(screen.getByRole("link", { name: "Return to Buddy" })).toHaveAttribute("href", "/");
});
