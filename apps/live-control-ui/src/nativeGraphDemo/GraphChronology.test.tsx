import { fireEvent, render, screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import type { NativeAssertion, NativeGraphChronology } from "../api/nativeGraphInspection";
import { GraphChronology } from "./GraphChronology";
import type { NativeGraph } from "./nativeGraphDemoApi";

it("orders reviewed Campaign placements and opens the selected Event", async () => {
  const graph = {
    nodes: [
      { id: "campaign", name: "Elderwyld Campaign", kind: "object",
        presentation: { recorded_names: [], classification_terms: ["dungeonbuddy:campaign"] } },
      { id: "late", name: "Arrival", kind: "event" },
      { id: "early", name: "Departure", kind: "event" },
      { id: "conflict", name: "Disputed meeting", kind: "event" },
    ],
    edges: [],
  } as unknown as NativeGraph;
  function placement(id: string, session: number): NativeAssertion {
    return {
      assertion_id: id, subject_entity_id: id, predicate: "dungeonbuddy.custom:on_timeline",
      value: { kind: "entity_ref", entity_id: "campaign" },
      metadata: {
        scope: [], visibility: null, epistemic_basis: "", standing: "",
        claim_mode: "dungeonbuddy.claim:observed_event", evidence_ref_ids: [], domain_metadata: [],
        temporal_scope: { schema: "dungeonbuddy.time:fictional_anchor_v1", payload: { start: { session } } },
      },
    };
  }
  const catalogue = {
    assertions: [placement("late", 12), placement("early", 2), placement("conflict", 3), placement("conflict", 5)],
    completeness: { status: "complete" },
  } as NativeGraphChronology;
  const explore = vi.fn();
  render(<GraphChronology graph={graph} read={async () => catalogue} onExplore={explore} />);
  await screen.findByRole("option", { name: "Elderwyld Campaign" });
  fireEvent.change(screen.getByRole("combobox", { name: "Campaign" }), { target: { value: "campaign" } });
  const buttons = within(screen.getByRole("list")).getAllByRole("button");
  expect(buttons.map(button => button.textContent)).toEqual(["Departure", "Arrival", "Disputed meeting"]);
  const spiral = screen.getByText("Campaign session spiral").closest("details")!;
  spiral.open = true;
  expect(within(spiral).getAllByRole("button").map(marker => marker.getAttribute("aria-label")))
    .toEqual(["Go to Session 2", "Go to Session 12"]);
  fireEvent.keyDown(within(spiral).getByRole("button", { name: "Go to Session 2" }), { key: "Enter" });
  expect(document.activeElement).toBe(buttons[0]);
  expect(screen.getByText(/Conflicting placements/)).toHaveTextContent("Session 3, Session 5");
  fireEvent.click(buttons[0]!);
  expect(explore).toHaveBeenCalledWith("early");
});

it("shows both directions of a recorded ordering assertion", async () => {
  const graph = {
    nodes: [
      { id: "a", name: "Arrival", kind: "event" },
      { id: "b", name: "Departure", kind: "event" },
    ],
    edges: [],
  } as unknown as NativeGraph;
  const catalogue = {
    assertions: [{
      assertion_id: "order", subject_entity_id: "a", predicate: "dungeonbuddy.custom:precedes",
      value: { kind: "entity_ref", entity_id: "b" }, metadata: {},
    }],
    completeness: { status: "complete" },
  } as unknown as NativeGraphChronology;
  const explore = vi.fn();
  render(<GraphChronology graph={graph} read={async () => catalogue} onExplore={explore} />);
  const before = await screen.findByText("Recorded before");
  const after = screen.getByText("Recorded after");
  fireEvent.click(within(before).getByRole("button", { name: "Departure" }));
  fireEvent.click(within(after).getByRole("button", { name: "Arrival" }));
  expect(explore.mock.calls).toEqual([["b"], ["a"]]);
});

it("flags ordering cycles without discarding claims", async () => {
  const graph = { nodes: [
    { id: "a", name: "Arrival", kind: "event" },
    { id: "b", name: "Departure", kind: "event" },
    { id: "c", name: "Discussion", kind: "event" },
    { id: "d", name: "Unrelated", kind: "event" },
  ], edges: [] } as unknown as NativeGraph;
  const catalogue = {
    assertions: [["a", "b"], ["b", "c"], ["c", "a"], ["d", "a"]].map(([from, to]) => ({
      assertion_id: from, subject_entity_id: from, predicate: "dungeonbuddy.custom:precedes",
      value: { kind: "entity_ref", entity_id: to }, metadata: {},
    })),
    completeness: { status: "complete" },
  } as unknown as NativeGraphChronology;
  render(<GraphChronology graph={graph} read={async () => catalogue} onExplore={vi.fn()} />);
  expect(await screen.findAllByText("Conflicting recorded order")).toHaveLength(3);
  expect(screen.getAllByText("Recorded before")).toHaveLength(4);
  expect(screen.getAllByText("Recorded after")).toHaveLength(4);
});

it.each([{ambiguous: false, single: false}, {ambiguous: true, single: false}, {ambiguous: false, single: true}])("isolates ordering claims with Campaign mapping %j", async ({ ambiguous, single }) => {
  const campaigns = (single ? ["One"] : ["One", "Two"]).map(id => ({
    id, name: id, kind: "object",
    presentation: { recorded_names: [], classification_terms: ["dungeonbuddy:campaign"] },
  }));
  const graph = {
    nodes: [...campaigns, { id: "a", name: "Arrival", kind: "event" }, { id: "b", name: "Departure", kind: "event" }],
    edges: [],
  } as unknown as NativeGraph;
  function fact(from: string, to: string, campaign: string, predicate: string) {
    return {
      assertion_id: [from, to, campaign].join("/"), subject_entity_id: from,
      predicate: "dungeonbuddy.custom:" + predicate, value: { kind: "entity_ref", entity_id: to },
      metadata: { scope: [{ axis: "dungeonbuddy.scope:campaign", value: campaign }] },
    };
  }
  const catalogue = {
    assertions: [
      ...campaigns.flatMap(({ id }) => ["a", "b"].map(event => fact(event, id, "scope-" + id, "on_timeline"))),
      fact("a", "b", "scope-One", "precedes"), fact("b", "a", "scope-Two", "precedes"),
      ...(ambiguous ? [fact("a", "One", "scope-Two", "on_timeline")] : []),
    ],
    completeness: { status: "complete" },
  } as unknown as NativeGraphChronology;
  render(<GraphChronology graph={graph} read={async () => catalogue} onExplore={vi.fn()} strip={single} />);
  await screen.findByRole("option", { name: "One" });
  if (single) {
    fireEvent.change(screen.getByRole("combobox", { name: "Campaign" }), { target: { value: "One" } });
    expect(screen.getByText("Recorded before Departure")).toBeVisible();
    expect(screen.queryByText("Recorded before Arrival")).toBeNull();
    return;
  }
  expect(screen.queryByText("Conflicting recorded order")).toBeNull();
  const orderRows = screen.getAllByText("Recorded before");
  expect(orderRows.find(row => within(row).queryByRole("button", { name: "Departure" }))).toHaveTextContent("· One");
  expect(orderRows.find(row => within(row).queryByRole("button", { name: "Arrival" }))).toHaveTextContent(ambiguous ? "Campaign name unavailable" : "· Two");
  for (const [campaign, target] of [["One", "Departure"], ["Two", "Arrival"]]) {
    fireEvent.change(screen.getByRole("combobox", { name: "Campaign" }), { target: { value: campaign } });
    if (ambiguous) {
      expect(screen.queryByText("Recorded before")).toBeNull();
    } else {
      expect(within(screen.getByText("Recorded before")).getByRole("button", { name: target })).toBeVisible();
    }
    expect(screen.queryByText("Conflicting recorded order")).toBeNull();
  }
});

it("keeps connected Events selectable when their chronology cannot load", async () => {
  const graph = {
    nodes: [
      { id: "person", name: "Caelynn", kind: "character" },
      { id: "arrival", name: "Arrival", kind: "event" },
      { id: "unrelated", name: "Unrelated", kind: "event" },
    ],
    edges: [{ source_id: "person", target_id: "arrival" }],
  } as unknown as NativeGraph;
  const explore = vi.fn();
  render(<GraphChronology graph={graph} read={vi.fn().mockRejectedValue(new Error("Unavailable"))}
    relatedTo="person" strip selectedEvent="arrival" onExplore={explore} />);
  await screen.findByRole("alert");
  expect(screen.queryByRole("button", { name: "Unrelated" })).toBeNull();
  const event = screen.getByRole("button", { name: "Arrival", pressed: true });
  fireEvent.click(event);
  expect(explore).toHaveBeenCalledWith("arrival");
});
