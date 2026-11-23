import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { GuestReleasePage } from "./GuestReleasePage";
import { isSavedChoice } from "./savedChoice";
import choiceParity from "./savedChoiceParity.json";

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); window.history.replaceState({}, "", "/"); });

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
