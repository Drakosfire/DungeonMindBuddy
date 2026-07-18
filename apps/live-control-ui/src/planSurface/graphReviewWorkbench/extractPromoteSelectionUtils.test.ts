import { describe, expect, it } from "vitest";

import type { ExtractPromotionReviewItem } from "../../api/types";
import {
  countSelectableSelected,
  initialPromoteSelection,
  togglePromoteSelection,
} from "./extractPromoteSelectionUtils";

function item(
  partial: Partial<ExtractPromotionReviewItem> &
    Pick<ExtractPromotionReviewItem, "assertionId" | "label">,
): ExtractPromotionReviewItem {
  return {
    kind: "object",
    action: "create",
    identityOutcome: "created_new",
    summary: partial.label,
    warnings: [],
    selectable: true,
    selectedByDefault: true,
    dependsOnAssertionIds: [],
    ...partial,
  };
}

describe("extractPromoteSelectionUtils", () => {
  const hesta = item({ assertionId: "a-hesta", label: "Hesta" });
  const edge = item({
    assertionId: "a-edge",
    label: "Hesta —works_at→ Apothecary",
    kind: "relationship",
    dependsOnAssertionIds: ["a-hesta"],
  });
  const other = item({ assertionId: "a-other", label: "Other" });
  const items = [hesta, edge, other];

  it("initializes selectable defaults", () => {
    const selected = initialPromoteSelection([
      hesta,
      edge,
      item({
        assertionId: "unresolved:x",
        label: "Ambiguous",
        selectable: false,
        selectedByDefault: false,
      }),
    ]);
    expect([...selected].sort()).toEqual(["a-edge", "a-hesta"]);
  });

  it("deselecting a create node cascades off dependent relationships", () => {
    const selected = initialPromoteSelection(items);
    const next = togglePromoteSelection(items, selected, "a-hesta");
    expect(next.has("a-hesta")).toBe(false);
    expect(next.has("a-edge")).toBe(false);
    expect(next.has("a-other")).toBe(true);
  });

  it("selecting a relationship also selects its create-node dependencies", () => {
    const selected = new Set<string>(["a-other"]);
    const next = togglePromoteSelection(items, selected, "a-edge");
    expect(next.has("a-edge")).toBe(true);
    expect(next.has("a-hesta")).toBe(true);
  });

  it("deselecting a relationship alone leaves the endpoint node selected", () => {
    const selected = initialPromoteSelection(items);
    const next = togglePromoteSelection(items, selected, "a-edge");
    expect(next.has("a-edge")).toBe(false);
    expect(next.has("a-hesta")).toBe(true);
  });

  it("counts only selectable selected rows", () => {
    const selected = new Set(["a-hesta", "unresolved:x"]);
    expect(countSelectableSelected(items, selected)).toBe(1);
  });
});
