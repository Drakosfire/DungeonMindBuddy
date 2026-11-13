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
    assertions: [placement("late", 12), placement("early", 2)],
    completeness: { status: "complete" },
  } as NativeGraphChronology;
  const explore = vi.fn();
  render(<GraphChronology graph={graph} read={async () => catalogue} onExplore={explore} />);
  await screen.findByRole("option", { name: "Elderwyld Campaign" });
  fireEvent.change(screen.getByRole("combobox", { name: "Campaign" }), { target: { value: "campaign" } });
  const buttons = within(screen.getByRole("list")).getAllByRole("button");
  expect(buttons.map(button => button.textContent)).toEqual(["Departure", "Arrival"]);
  fireEvent.click(buttons[0]!);
  expect(explore).toHaveBeenCalledWith("early");
});
