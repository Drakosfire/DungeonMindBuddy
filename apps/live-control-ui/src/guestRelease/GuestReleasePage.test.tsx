import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { webcrypto } from "node:crypto";
import { createGuestGraphApi, parseGuestGraphRelease } from "./guestGraphModel";
import { GuestReleasePage } from "./GuestReleasePage";
import { isSavedChoice } from "./savedChoice";
import choiceParity from "./savedChoiceParity.json";

afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); vi.restoreAllMocks(); window.history.replaceState({}, "", "/"); });

it("opens mobile point details and returns to the graph without losing selection", async () => {
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ release_id: "copy", manifest: {
    graph: { nodes: [{ id: "a", label: "Sizzek", kind: "npc", name_citations: ["s"], kind_citations: ["s"], name_basis: "asserted", kind_basis: "asserted" }], edges: [] },
    sources: [{ id: "s", text: "A source", evidence_role: "support" }], assets: [],
  } }), { status: 200 })));
  const user = userEvent.setup();
  render(<GuestReleasePage publicId="public" />);
  await user.click(await screen.findByRole("button", { name: "Sizzek npc" }));
  expect(screen.getByRole("complementary")).toHaveFocus();
  expect(window.location.hash).toBe("#copy/copy/point/a");
  await user.click(screen.getByRole("button", { name: "← Back to graph" }));
  expect(screen.getByRole("region", { name: "A web of connections" })).toHaveFocus();
  expect(window.location.hash).toBe("#copy/copy/point/a");
  await user.click(screen.getByRole("button", { name: "Read source: A source" }));
  expect(screen.getByText("A source")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "← Back to graph" }));
  expect(window.location.hash).toBe("#copy/copy/point/a/source/s");
  await user.type(screen.getByRole("textbox", { name: "Point name" }), "A new clue");
  await user.selectOptions(screen.getByRole("combobox", { name: "Connect to a shared point" }), "a");
  await user.click(screen.getByRole("button", { name: "Add temporary point" }));
  expect(screen.getByRole("complementary")).toHaveFocus();
  expect(screen.getByRole("heading", { name: "A new clue" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "← Back to graph" }));
  await user.click(screen.getByRole("button", { name: "Reset my additions" }));
  expect(screen.queryByRole("button", { name: "A new clue Your addition" })).not.toBeInTheDocument();
});

it("keeps desktop focus on the selected point", async () => {
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false })));
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ release_id: "copy", manifest: {
    graph: { nodes: [{ id: "a", label: "Sizzek", kind: "npc", name_citations: [], kind_citations: [], name_basis: "asserted", kind_basis: "asserted" }], edges: [] }, sources: [], assets: [],
  } }), { status: 200 })));
  const user = userEvent.setup();
  render(<GuestReleasePage publicId="public" />);
  const point = await screen.findByRole("button", { name: "Sizzek npc" });
  await user.click(point);
  expect(point).toHaveFocus();
});

it("keeps mobile connection endpoints aligned when points are added and reset", async () => {
  const nodes = ["Sizzek", "Festival of Light and Gifts", "Izmati", "The Funhouse", "The Guild"].map((label, index) => ({
    id: String(index), label, kind: "place", name_citations: [], kind_citations: [], name_basis: "asserted", kind_basis: "asserted",
  }));
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ release_id: "copy", manifest: {
    graph: { nodes, edges: [{ id: "e", source: "0", target: "4", label: "knows", citations: [], temporal: "unknown", basis: "asserted" }] }, sources: [], assets: [],
  } }), { status: 200 })));
  const user = userEvent.setup();
  render(<GuestReleasePage publicId="public" />);
  const first = await screen.findByRole("button", { name: "Sizzek place" });
  const last = screen.getByRole("button", { name: "The Guild place" });
  const mobileLine = document.querySelector(".guest-world__lines--mobile line")!;
  expect(first.style.getPropertyValue("--point-mobile-x")).toBe("25%");
  expect(last.style.getPropertyValue("--point-mobile-x")).toBe("25%");
  expect(mobileLine).toHaveAttribute("x1", "25");
  expect(mobileLine).toHaveAttribute("x2", "25");
  expect(mobileLine).toHaveAttribute("y2", String(250 / 3));

  await user.type(screen.getByRole("textbox", { name: "Point name" }), "A very long visitor-created point");
  await user.selectOptions(screen.getByRole("combobox", { name: "Connect to a shared point" }), "0");
  await user.click(screen.getByRole("button", { name: "Add temporary point" }));
  expect(screen.getByRole("button", { name: "A very long visitor-created point Your addition" })).toHaveStyle({ "--point-mobile-x": "75%" });
  expect(document.querySelectorAll(".guest-world__lines--mobile line")).toHaveLength(2);
  await user.click(screen.getByRole("button", { name: "Reset my additions" }));
  expect(document.querySelectorAll(".guest-world__lines--mobile line")).toHaveLength(1);
  expect(screen.queryByRole("button", { name: "A very long visitor-created point Your addition" })).not.toBeInTheDocument();
});

it.each(choiceParity)("uses the shared Unicode choice contract: $name", ({ labels, repeat, valid }) => {
  const choice = { version: "owner_saved_choice_v1", prompt: "What next", options: [
    { label: labels[0].repeat(repeat ?? 1), outcome: "One" }, { label: labels[1], outcome: "Two" }] };
  expect(isSavedChoice(choice)).toBe(valid);
});

it("presents known graph terms without changing evidence or visitor-authored text", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ release_id: "copy", manifest: {
    graph: { nodes: [
      { id: "a", label: "Sizzek", kind: "dnd5e · npc", name_citations: ["s"], kind_citations: ["s"], name_basis: "asserted", kind_basis: "inferred" },
      { id: "b", label: "Izmati", kind: "other · creature", name_citations: ["s"], kind_citations: ["s"], name_basis: "asserted", kind_basis: "asserted" },
    ], edges: [{ id: "e", source: "a", target: "b", label: "dnd5e · associated with", citations: ["s"], temporal: "unknown", basis: "inferred" }] },
    sources: [{ id: "s", text: "A source excerpt.", evidence_role: "support" }], assets: [],
  } }), { status: 200 })));
  const user = userEvent.setup();
  render(<GuestReleasePage publicId="public" />);
  await user.click(await screen.findByRole("button", { name: "Sizzek npc" }));
  expect(screen.getByRole("button", { name: "Izmati other · creature" })).toBeInTheDocument();
  expect(screen.getByRole("option", { name: "Sizzek · npc" })).toHaveValue("a");
  expect(screen.getByText("associated with").parentElement).toHaveTextContent("Sizzek associated with Izmati");
  expect(screen.getByText("Name: asserted · Classification: inferred")).toBeInTheDocument();
  expect(screen.getByText(/inferred · When this happened is not specified/)).toBeInTheDocument();
  expect(screen.getAllByRole("button", { name: "Read source: A source excerpt." }).length).toBeGreaterThan(0);

  await user.type(screen.getByRole("textbox", { name: "Point name" }), "Visitor point");
  await user.clear(screen.getByRole("textbox", { name: "Connection" }));
  await user.type(screen.getByRole("textbox", { name: "Connection" }), "dnd5e · custom wording");
  await user.selectOptions(screen.getByRole("combobox", { name: "Connect to a shared point" }), "a");
  await user.click(screen.getByRole("button", { name: "Add temporary point" }));
  expect(screen.getByText("dnd5e · custom wording")).toBeInTheDocument();
  expect(screen.getByText("Your temporary connection · not sourced from the shared World")).toBeInTheDocument();
});

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
  const citations = screen.getAllByRole("button", { name: "Read context: A saved excerpt." });
  await user.click(citations[citations.length - 1]);
  expect(screen.getByText("A saved excerpt.")).toBeInTheDocument();
  expect(screen.getByText("Evidence role: context, not direct support.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Link to this excerpt" })).toHaveAttribute("href", "#copy/copy/point/a/source/s");
  expect(screen.getByText(/shared World stays unchanged/i)).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock.mock.calls[0][0]).toBe("/api/live/guest-releases/public");
  expect(fetchMock.mock.calls[0][1]).toMatchObject({ credentials: "omit", cache: "no-store" });
});

it("opens only release-local deep links and ignores stale or invalid fragments", async () => {
  const data = { release_id: "copy", manifest: { graph: { nodes: [
    { id: "a", label: "Sizzek", kind: "character", name_citations: ["s"], kind_citations: ["s"], name_basis: "asserted", kind_basis: "asserted" },
  ], edges: [] }, sources: [{ id: "s", text: "Safe excerpt", evidence_role: "support" }], assets: [] } };
  const fetchMock = vi.fn(async () => new Response(JSON.stringify(data), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  window.history.replaceState({}, "", "/visit/public#copy/copy/point/a/source/s");
  render(<GuestReleasePage publicId="public" />);
  expect(await screen.findByText("Safe excerpt")).toBeInTheDocument();
  expect(screen.getByText("Evidence role: support.")).toBeInTheDocument();
  act(() => { window.history.pushState({}, "", "#copy/older-copy/point/a/source/s"); window.dispatchEvent(new PopStateEvent("popstate")); });
  expect(await screen.findByText("Every story has a trail.")).toBeInTheDocument();
  act(() => { window.history.pushState({}, "", "#copy/copy/point/a/source/s"); window.dispatchEvent(new PopStateEvent("popstate")); });
  expect(screen.getByText("Safe excerpt")).toBeInTheDocument();
  act(() => { window.history.pushState({}, "", "#copy/copy/point/a/source/private-id"); window.dispatchEvent(new PopStateEvent("popstate")); });
  expect(screen.queryByText("Safe excerpt")).not.toBeInTheDocument();
  act(() => { window.history.pushState({}, "", "#copy/copy/point/%E0%A4%A"); window.dispatchEvent(new PopStateEvent("popstate")); });
  expect(screen.getByText("Every story has a trail.")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(1);
});


it("navigates the guest copy without changing its selected source or fragment", async () => {
  const copy = { release_id: "copy", manifest: { graph: { nodes: [
    { id: "a", label: "Sizzek", kind: "character", name_citations: ["s1"], kind_citations: ["s1"], name_basis: "asserted", kind_basis: "asserted" },
  ], edges: [] }, sources: [{ id: "s1", text: "Safe excerpt", evidence_role: "support" }, { id: "s2", text: "Another excerpt", evidence_role: "context" }], assets: [],
    saved_example: { version: "owner_saved_scene_v1", title: "A saved scene", body: "A scene", references: ["s1", "s2"], image: null } } };
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(copy), { status: 200 })));
  window.history.replaceState({}, "", "/#copy/copy/point/a/source/s1");
  const user = userEvent.setup();
  render(<GuestReleasePage publicId="public" home />);
  expect(await screen.findByText("Safe excerpt")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Explore this World in Graph →" })).toHaveAttribute("href", "/graph");
  const navigation = screen.getByRole("navigation", { name: "Guest navigation" });
  await user.click(within(navigation).getByRole("button", { name: "Saved scene" }));
  expect(screen.getByRole("region", { name: "A saved scene" })).toHaveFocus();
  expect(window.location.hash).toBe("#copy/copy/point/a/source/s1");
  expect(screen.getByText("Safe excerpt")).toBeInTheDocument();
  await user.click(within(navigation).getByRole("button", { name: "Explore graph" }));
  expect(screen.getByRole("region", { name: "A web of connections" })).toHaveFocus();
  expect(window.location.hash).toBe("#copy/copy/point/a/source/s1");
});

it("shows an unavailable state when a release is withdrawn", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 404 })));
  render(<GuestReleasePage publicId="public" />);
  expect(await screen.findByRole("alert")).toHaveTextContent("This guest World is unavailable");
  expect(screen.getByRole("link", { name: "Return to Buddy" })).toHaveAttribute("href", "/");
  expect(screen.queryByRole("button", { name: "Explore graph" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Saved scene" })).not.toBeInTheDocument();
});

it("shows an unchanged saved example with release-only references and inline image", async () => {
  const copy = { release_id: "copy", manifest: { graph: { nodes: [{ id: "a", label: "Shared", kind: "place", name_citations: [], kind_citations: [], name_basis: "asserted", kind_basis: "asserted" }], edges: [] },
    sources: [{ id: "s1", text: "First clue", evidence_role: "support" }, { id: "s2", text: "Second clue", evidence_role: "context" }],
    assets: [{ id: "image" }], saved_example: { version: "owner_saved_scene_v1", title: "A saved scene", body: "A line\nAnother line", references: ["s1", "s2"], image: { id: "image", description: "A red tent" } },
    saved_choice: { version: "owner_saved_choice_v1", prompt: "What next", options: [
      { label: "Enter", outcome: "A bell rings" }, { label: "Wait", outcome: "A lantern flickers" }] } } };
  const fetchMock = vi.fn(async () => new Response(JSON.stringify(copy), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  render(<GuestReleasePage publicId="public" home />);
  expect(await screen.findByRole("heading", { name: "A saved scene" })).toBeInTheDocument();
  expect(screen.getByText(/Your temporary additions were not used/)).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "A red tent" })).toHaveAttribute("src", "/api/live/guest-releases/public/releases/copy/assets/image");
  expect(screen.getByRole("group", { name: "What next" })).toBeInTheDocument();
  expect(screen.queryByText("A bell rings")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Enter" }));
  expect(screen.getByText("A bell rings")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Enter" })).toHaveAttribute("aria-pressed", "true");
  await user.click(screen.getByRole("button", { name: "Explore graph" }));
  await user.click(screen.getByRole("button", { name: "Saved scene" }));
  expect(screen.getByText("A bell rings")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Enter" })).toHaveAttribute("aria-pressed", "true");
  expect(window.location.href).not.toContain("Enter");
  await user.click(screen.getByRole("button", { name: "Wait" }));
  expect(screen.getByText("A lantern flickers")).toBeInTheDocument();
  expect(screen.queryByText("A bell rings")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Reset choice" }));
  expect(screen.queryByText("A lantern flickers")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Reset choice" })).toHaveFocus();
  await user.click(screen.getByRole("button", { name: "Enter" }));
  await user.type(screen.getByLabelText("Point name"), "A visitor point");
  await user.selectOptions(screen.getByLabelText("Connect to a shared point"), "a");
  await user.click(screen.getByRole("button", { name: "Add temporary point" }));
  expect(screen.getByText("A line Another line")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Reset my additions" }));
  expect(screen.queryByText("A bell rings")).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "A saved scene" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Read context: Second clue" }));
  expect(screen.getByText("Second clue")).toBeInTheDocument();
  expect(screen.getByText("Second clue").closest("aside")).toHaveFocus();
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("keeps choices in each mounted copy, clears them on copy change and never persists them", async () => {
  const manifest = { graph: { nodes: [], edges: [] }, sources: [{ id: "s1", text: "One", evidence_role: "support" }, { id: "s2", text: "Two", evidence_role: "context" }], assets: [],
    saved_example: { version: "owner_saved_scene_v1", title: "Scene", body: "Saved scene", references: ["s1", "s2"], image: null },
    saved_choice: { version: "owner_saved_choice_v1", prompt: "What next", options: [{ label: "Enter", outcome: "Bell" }, { label: "Wait", outcome: "Lantern" }] } };
  const fetchMock = vi.fn(async (url: RequestInfo | URL) => new Response(JSON.stringify({ release_id: String(url).endsWith("/third") ? "other-copy" : "copy", manifest }), { status: 200 }));
  const storage = vi.spyOn(Storage.prototype, "setItem");
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  const first = render(<GuestReleasePage publicId="first" />), second = render(<GuestReleasePage publicId="second" />);
  const one = within(first.container), two = within(second.container);
  await one.findByRole("group", { name: "What next" }); await two.findByRole("group", { name: "What next" });
  await user.click(one.getByRole("button", { name: "Enter" }));
  expect(one.getByText("Bell")).toBeInTheDocument();
  expect(two.queryByText("Bell")).not.toBeInTheDocument();
  expect(window.location.href).not.toContain("Enter");
  act(() => { window.history.pushState({}, "", "#copy/copy/source/s1"); window.dispatchEvent(new PopStateEvent("popstate")); });
  expect(one.getByText("Bell")).toBeInTheDocument();
  expect(window.location.hash).not.toContain("Enter");
  expect(storage).not.toHaveBeenCalled();
  first.rerender(<GuestReleasePage publicId="third" />);
  expect(one.queryByText("Bell")).not.toBeInTheDocument();
  await one.findByRole("group", { name: "What next" });
  expect(one.queryByText("Bell")).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(3);
  expect(storage).not.toHaveBeenCalled();
  storage.mockRestore();
});

it("does not render an unrecognized saved choice", async () => {
  const manifest = { graph: { nodes: [], edges: [] }, sources: [{ id: "s1", text: "One", evidence_role: "support" }, { id: "s2", text: "Two", evidence_role: "context" }], assets: [],
    saved_example: { version: "owner_saved_scene_v1", title: "Scene", body: "Saved scene", references: ["s1", "s2"], image: null },
    saved_choice: { version: "future", prompt: "What next", options: [] } };
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ release_id: "copy", manifest }), { status: 200 })));
  render(<GuestReleasePage publicId="public" />);
  expect(await screen.findByRole("alert")).toHaveTextContent("saved choice is unavailable");
  expect(screen.queryByRole("group", { name: "What next" })).not.toBeInTheDocument();
});

it("renders a saved answer with passage-specific released citations", async () => {
  const copy = { release_id: "copy", manifest: { graph: { nodes: [], edges: [] }, assets: [],
    sources: [{ id: "s1", text: "Plan excerpt", evidence_role: "support" }, { id: "s2", text: "Recap excerpt", evidence_role: "context" }],
    saved_answer: { version: "owner_saved_answer_v1", question: "What do the notes say", passages: [
      { text: "A plan", references: ["s1"] }, { text: "A recap", references: ["s2"] }] } } };
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(copy), { status: 200 })));
  const user = userEvent.setup();
  render(<GuestReleasePage publicId="public" />);
  const answer = await screen.findByRole("region", { name: "What do the notes say" });
  expect(within(answer).getByText(/not a live Buddy response/)).toBeInTheDocument();
  await user.click(within(answer).getByRole("button", { name: "Read context: Recap excerpt" }));
  expect(screen.getByText("Recap excerpt")).toBeInTheDocument();
  expect(screen.getByText("Evidence role: context, not direct support.")).toBeInTheDocument();
});


it("previews released excerpts without breaking Unicode and opens their full text", async () => {
  const excerpt = `  ${"🐉".repeat(70)}\n  The full source continues.  `;
  const copy = { release_id: "copy", manifest: { graph: { nodes: [], edges: [] }, assets: [],
    sources: [{ id: "s", text: excerpt, evidence_role: "context" }],
    saved_answer: { version: "owner_saved_answer_v1", question: "A question", passages: [{ text: "An answer", references: ["s"] }] } } };
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(copy), { status: 200 })));
  const user = userEvent.setup();
  render(<GuestReleasePage publicId="public" />);
  const answer = await screen.findByRole("region", { name: "A question" });
  const citation = within(answer).getByRole("button", { name: `Read context: ${"🐉".repeat(64)}…` });
  await user.click(citation);
  expect(screen.getByText(excerpt, { normalizer: text => text })).toBeInTheDocument();
  expect(screen.getByText("Evidence role: context, not direct support.")).toBeInTheDocument();
});

const release = () => ({ release_id: "copy-1", manifest: { graph: { nodes: [
  { id: "a", label: "Sizzek", kind: "dnd5e · npc", name_basis: "asserted", kind_basis: "inferred", name_citations: ["s"], kind_citations: ["s"] },
  { id: "b", label: "Carnival", kind: "location", name_basis: "asserted", kind_basis: "asserted", name_citations: [], kind_citations: [] },
], edges: [{ id: "e", source: "a", target: "b", label: "dnd5e · owns", basis: "asserted", temporal: "unknown", citations: ["s"] }] },
  sources: [{ id: "s", text: "A released excerpt", evidence_role: "support" }] } });

it("adapts only released records into a memory-only read-only graph", async () => {
  vi.stubGlobal("crypto", webcrypto);
  const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
  const api = await createGuestGraphApi("public", parseGuestGraphRelease(release()));
  const graph = await api.readGraph();
  expect(graph.storage).toBe("memory");
  expect(graph.world_id).toBe("guest:public:copy-1");
  expect(graph.nodes.map((node) => [node.name, node.kind])).toEqual([["Sizzek", "npc"], ["Carnival", "location"]]);
  expect(graph.edges[0]).toMatchObject({ source_id: "a", target_id: "b", predicate: "owns" });
  expect(graph.capabilities).toMatchObject({ create: false, connect: false });
  await expect(api.prepare({ operation_id: "x", expected_revision_id: "copy-1", kind: "create_object", name: "x", object_kind: "person" })).rejects.toThrow("read-only");
  expect(fetchMock).not.toHaveBeenCalled();
});

it("rejects dangling or duplicated release-local identities and source references", () => {
  const missing = release(); missing.manifest.graph.edges[0].citations = ["private-source"];
  expect(() => parseGuestGraphRelease(missing)).toThrow("Incomplete shared graph");
  const duplicate = release(); duplicate.manifest.graph.nodes.push({ ...duplicate.manifest.graph.nodes[0] });
  expect(() => parseGuestGraphRelease(duplicate)).toThrow("Incomplete shared graph");
  const foreign = release(); foreign.manifest.graph.edges[0].target = "private-node";
  expect(() => parseGuestGraphRelease(foreign)).toThrow("Incomplete shared graph");
});


describe("signed-out product Graph", () => {
const publicId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const copy = { release_id: "copy", manifest: { graph: { nodes: [
  { id: "a", label: "Sizzek", kind: "npc", name_basis: "asserted", kind_basis: "asserted", name_citations: ["s"], kind_citations: ["s"] },
  { id: "b", label: "Carnival", kind: "location", name_basis: "asserted", kind_basis: "asserted", name_citations: [], kind_citations: [] },
], edges: [{ id: "e", source: "a", target: "b", label: "owns", basis: "asserted", temporal: "unknown", citations: ["s"] }] },
  sources: [{ id: "s", text: "The released excerpt.", evidence_role: "context" }], assets: [] } };
beforeEach(() => { vi.stubEnv("PROD", true); vi.stubEnv("VITE_GUEST_RELEASE_PAGE", "1"); vi.stubEnv("VITE_GUEST_HOME_PUBLIC_ID", publicId); vi.stubGlobal("crypto", webcrypto); window.history.replaceState({}, "", "/graph"); });
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); vi.restoreAllMocks(); window.history.replaceState({}, "", "/"); });

it("opens the actual Graph workspace from the public copy without private or playground requests", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => String(input) === "/api/auth/session"
    ? new Response(null, { status: 401 }) : String(input) === `/api/live/guest-releases/${publicId}`
      ? new Response(JSON.stringify(copy), { status: 200 }) : new Response(null, { status: 500 }));
  vi.stubGlobal("fetch", fetchMock);
  const storage = vi.spyOn(Storage.prototype, "setItem");
  const { App } = await import("../App");
  const user = userEvent.setup(); const view = render(<App />);
  expect(await screen.findByText("Shared World · demo")).toBeInTheDocument();
  expect(await screen.findByTestId("graph-scene")).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "Command board navigation" })).toBeInTheDocument();
  const point = screen.getByText("Sizzek", { selector: "svg text" });
  await user.click(point);
  expect(await screen.findByRole("region", { name: "Shared source evidence" })).toHaveTextContent("Name: asserted");
  await user.click(screen.getAllByText("Read context: The released excerpt.")[0]);
  expect(screen.getAllByText("The released excerpt.").length).toBeGreaterThan(0);
  expect(screen.getByText("When this happened is not specified", { exact: false })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Explore Carnival" }));
  expect(await screen.findByRole("heading", { name: "Carnival" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Back to Sizzek" }));
  expect(await screen.findByRole("heading", { name: "Sizzek" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Graph tools" }));
  await user.click(screen.getByRole("button", { name: "Move nodes" }));
  const node = screen.getByRole("button", { name: "Sizzek, npc" });
  const position = node.getAttribute("transform");
  fireEvent.keyDown(node, { key: "ArrowRight" });
  await waitFor(() => expect(node.getAttribute("transform")).not.toBe(position));
  const movedPosition = node.getAttribute("transform");
  view.unmount();
  render(<App />);
  const reopened = await screen.findByRole("button", { name: "Sizzek, npc" });
  expect(reopened.getAttribute("transform")).not.toBe(movedPosition);
  expect(storage).not.toHaveBeenCalled();
  expect(fetchMock.mock.calls.map((call) => String(call[0])).sort()).toEqual(["/api/auth/session", "/api/auth/session", `/api/live/guest-releases/${publicId}`, `/api/live/guest-releases/${publicId}`].sort());
});

it("adds and connects temporary points in the real Graph, then resets without storage or private writes", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => String(input) === "/api/auth/session"
    ? new Response(null, { status: 401 }) : new Response(JSON.stringify(copy), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  const storage = vi.spyOn(Storage.prototype, "setItem");
  const { App } = await import("../App");
  const user = userEvent.setup(); const view = render(<App />);
  await screen.findByTestId("graph-scene");
  await user.click(screen.getByRole("button", { name: "Graph tools" }));
  await user.click(screen.getByRole("button", { name: "Move nodes" }));
  const original = screen.getByRole("button", { name: "Sizzek, npc" });
  const originalPosition = original.getAttribute("transform");
  fireEvent.keyDown(original, { key: "ArrowRight" });
  await waitFor(() => expect(original.getAttribute("transform")).not.toBe(originalPosition));
  const movedPosition = original.getAttribute("transform");
  await user.click(screen.getByText("Add to this graph"));
  await user.type(screen.getByRole("textbox", { name: "New point" }), "A visitor clue");
  await user.click(screen.getByRole("button", { name: "Add point" }));
  const added = await screen.findByRole("button", { name: "A visitor clue, temporary" });
  expect(screen.getByRole("button", { name: "Sizzek, npc" })).toHaveAttribute("transform", movedPosition);
  await user.click(added);
  expect(await screen.findByText("Your temporary point · not sourced from the shared World.")).toBeInTheDocument();
  await user.selectOptions(screen.getByRole("combobox", { name: "To" }), "a");
  await user.type(screen.getByRole("textbox", { name: "Connection" }), "points to");
  await user.click(screen.getByRole("button", { name: "Connect points" }));
  await user.click(await screen.findByRole("button", { name: "A visitor clue, temporary" }));
  expect(screen.getByRole("button", { name: "Sizzek, npc" })).toHaveAttribute("transform", movedPosition);
  expect(await screen.findByText("Your temporary connection · not sourced from the shared World.")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Explore Sizzek" }));
  expect(await screen.findByText("Name: asserted")).toBeInTheDocument();
  const reset = screen.getByRole("button", { name: "Reset my additions" });
  await user.click(reset);
  expect(reset).toHaveFocus();
  await screen.findByRole("button", { name: "Sizzek, npc" });
  await user.click(screen.getByRole("button", { name: "Done" }));
  expect(screen.getByText("Add to this graph")).toHaveFocus();
  await user.click(screen.getByText("Add to this graph"));
  screen.getByRole("textbox", { name: "New point" }).focus();
  await user.keyboard("{Escape}");
  expect(screen.getByText("Add to this graph")).toHaveFocus();
  expect(screen.getByText("Add to this graph").closest("details")).not.toHaveAttribute("open");
  await screen.findByRole("button", { name: "Sizzek, npc" });
  expect(screen.queryByRole("button", { name: "A visitor clue, temporary" })).not.toBeInTheDocument();
  expect(screen.queryByText("Your temporary connection · not sourced from the shared World.")).not.toBeInTheDocument();
  view.unmount(); render(<App />);
  await screen.findByRole("button", { name: "Sizzek, npc" });
  expect(screen.queryByRole("button", { name: "A visitor clue, temporary" })).not.toBeInTheDocument();
  expect(storage).not.toHaveBeenCalled();
  expect(fetchMock.mock.calls.map((call) => String(call[0])).sort()).toEqual(["/api/auth/session", "/api/auth/session", `/api/live/guest-releases/${publicId}`, `/api/live/guest-releases/${publicId}`].sort());
});

it("does not restore an older delayed edit after reset", async () => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => String(input) === "/api/auth/session" ? new Response(null, { status: 401 }) : new Response(JSON.stringify(copy), { status: 200 })));
  const { App } = await import("../App");
  const user = userEvent.setup(); render(<App />);
  await screen.findByRole("button", { name: "Sizzek, npc" });
  const realDigest = webcrypto.subtle.digest.bind(webcrypto.subtle);
  let releaseDigest: (() => void) | undefined;
  vi.spyOn(webcrypto.subtle, "digest").mockImplementationOnce((algorithm, data) => new Promise((resolve, reject) => {
    releaseDigest = () => { void realDigest(algorithm, data).then(resolve, reject); };
  }));
  await user.click(screen.getByText("Add to this graph"));
  await user.type(screen.getByRole("textbox", { name: "New point" }), "Delayed clue");
  await user.click(screen.getByRole("button", { name: "Add point" }));
  await waitFor(() => expect(releaseDigest).toBeDefined());
  await user.click(screen.getByRole("button", { name: "Reset my additions" }));
  await screen.findByRole("button", { name: "Sizzek, npc" });
  await act(async () => { releaseDigest?.(); await new Promise((resolve) => setTimeout(resolve, 0)); });
  expect(screen.queryByRole("button", { name: "Delayed clue, temporary" })).not.toBeInTheDocument();
});

it("fails closed when the released copy is unavailable", async () => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => new Response(null, { status: String(input) === "/api/auth/session" ? 401 : 404 })));
  const { App } = await import("../App");
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent("This shared World is unavailable");
  await waitFor(() => expect(screen.queryByTestId("graph-scene")).not.toBeInTheDocument());
});

it("shows a released point even when it has no relationships", async () => {
  const isolated = { ...copy, manifest: { ...copy.manifest, graph: { nodes: [copy.manifest.graph.nodes[0]], edges: [] } } };
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => String(input) === "/api/auth/session"
    ? new Response(null, { status: 401 }) : new Response(JSON.stringify(isolated), { status: 200 })));
  const { App } = await import("../App");
  render(<App />);
  expect(await screen.findByRole("button", { name: "Sizzek, npc" })).toBeInTheDocument();
});

it("unmounts the guest Graph when the visitor signs in", async () => {
  let signedIn = false;
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => String(input) === "/api/auth/session"
    ? signedIn ? new Response(JSON.stringify({ status: "authenticated", subject: "owner" }), { status: 200 }) : new Response(null, { status: 401 })
    : String(input) === `/api/live/guest-releases/${publicId}` ? new Response(JSON.stringify(copy), { status: 200 }) : new Response(null, { status: 404 })));
  const { App } = await import("../App");
  render(<App />);
  expect(await screen.findByText("Shared World · demo")).toBeInTheDocument();
  await screen.findByTestId("graph-scene");
  signedIn = true;
  fireEvent.focus(window);
  await waitFor(() => expect(screen.queryByText("Shared World · demo")).not.toBeInTheDocument());
});

it("discards an older pending copy when the public identity changes", async () => {
  let finishOld!: (response: Response) => void;
  const pending = new Promise<Response>((resolve) => { finishOld = resolve; });
  const otherId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
  const other = { ...copy, release_id: "new-copy", manifest: { ...copy.manifest, graph: { ...copy.manifest.graph, nodes: [{ ...copy.manifest.graph.nodes[0], label: "New point" }, copy.manifest.graph.nodes[1]] } } };
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => String(input).endsWith(publicId) ? pending : new Response(JSON.stringify(other), { status: 200 })));
  const { GuestProductGraph } = await import("./GuestProductGraph");
  const view = render(<GuestProductGraph publicId={publicId} />);
  view.rerender(<GuestProductGraph publicId={otherId} />);
  await waitFor(() => expect(screen.getByText("Shared World · demo")).toBeInTheDocument());
  await waitFor(() => expect(screen.getByTestId("graph-scene")).toBeInTheDocument());
  expect(screen.getByRole("button", { name: /New point/ })).toBeInTheDocument();
  await act(async () => { finishOld(new Response(JSON.stringify(copy), { status: 200 })); await pending; });
  expect(screen.queryByRole("button", { name: "Sizzek, npc" })).not.toBeInTheDocument();
});

});
