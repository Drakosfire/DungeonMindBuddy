import { describe, expect, it } from "vitest";

import {
  humanizeRelationshipPredicate,
  MAX_DEFAULT_RELATIONSHIP_ROWS,
  relationshipRowPrimaryCopy,
  relationshipSessionStamp,
  selectDefaultRelationshipRows,
} from "./graphObjectDisplay";
import type { GraphObjectRelationshipViewModel } from "./types";

function rel(
  partial: Partial<GraphObjectRelationshipViewModel> & Pick<GraphObjectRelationshipViewModel, "id" | "label">,
): GraphObjectRelationshipViewModel {
  return {
    predicate: null,
    summary: null,
    targetId: null,
    sessionIds: [],
    ...partial,
  };
}

describe("humanizeRelationshipPredicate", () => {
  it("replaces underscores with spaces", () => {
    expect(humanizeRelationshipPredicate("located_in")).toBe("located in");
    expect(humanizeRelationshipPredicate("travels_to")).toBe("travels to");
  });

  it("returns null for empty predicates", () => {
    expect(humanizeRelationshipPredicate(null)).toBeNull();
    expect(humanizeRelationshipPredicate("  ")).toBeNull();
  });
});

describe("relationshipSessionStamp", () => {
  it("formats the earliest numbered session", () => {
    expect(relationshipSessionStamp(["session-4", "session-2"])).toBe("S2");
  });
});

describe("relationshipRowPrimaryCopy", () => {
  it("includes session stamp and omits foreign-object summary", () => {
    expect(
      relationshipRowPrimaryCopy(
        rel({
          id: "e1",
          label: "Pippa",
          predicate: "owns",
          sessionIds: ["session-2"],
          summary: "Bright gnome who crafts beer.",
        }),
      ),
    ).toBe("S2 · Pippa · owns");
  });
});

describe("selectDefaultRelationshipRows", () => {
  it("orders chronologically and keeps distinct edges to the same target", () => {
    const { rows, omittedCount } = selectDefaultRelationshipRows([
      rel({
        id: "e1",
        label: "Pippa",
        predicate: "travels_to",
        targetId: "npc:pippa",
        sessionIds: ["session-4"],
      }),
      rel({
        id: "e2",
        label: "River",
        predicate: "located_in",
        targetId: "loc:river",
        sessionIds: ["session-2"],
      }),
      rel({
        id: "e3",
        label: "Pippa",
        predicate: "owns",
        targetId: "npc:pippa",
        sessionIds: ["session-2"],
      }),
    ]);

    expect(rows.map((row) => row.id)).toEqual(["e3", "e2", "e1"]);
    expect(omittedCount).toBe(0);
  });

  it("caps rows and reports omitted count", () => {
    const many = Array.from({ length: MAX_DEFAULT_RELATIONSHIP_ROWS + 3 }, (_, index) =>
      rel({
        id: `e${index}`,
        label: `Node ${index}`,
        targetId: `node:${index}`,
        predicate: "related_to",
        sessionIds: [`session-${index + 1}`],
      }),
    );
    const { rows, omittedCount } = selectDefaultRelationshipRows(many);
    expect(rows).toHaveLength(MAX_DEFAULT_RELATIONSHIP_ROWS);
    expect(omittedCount).toBe(3);
    expect(rows[0]?.sessionIds).toEqual(["session-1"]);
  });
});
