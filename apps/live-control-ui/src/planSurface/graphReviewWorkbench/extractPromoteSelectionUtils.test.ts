import { describe, expect, it } from "vitest";

import type { ExtractPromotionReviewItem } from "../../api/types";
import {
  countSelectableSelected,
  initialPromoteSelection,
  selectedPromoteAssertionIds,
  togglePromoteSelection,
} from "./extractPromoteSelectionUtils";

function item(
  partial: Partial<ExtractPromotionReviewItem> &
    Pick<ExtractPromotionReviewItem, "assertionId" | "label" | "sliceQualifiedId">,
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
    dependsOnSliceQualifiedIds: [],
    ...partial,
  };
}

describe("extractPromoteSelectionUtils", () => {
  const hesta = item({
    assertionId: "a-hesta",
    sliceQualifiedId: "0:source_extraction::a-hesta",
    label: "Hesta",
  });
  const edge = item({
    assertionId: "a-edge",
    sliceQualifiedId: "0:source_extraction::a-edge",
    label: "Hesta —works_at→ Apothecary",
    kind: "relationship",
    dependsOnAssertionIds: ["a-hesta"],
    dependsOnSliceQualifiedIds: ["0:source_extraction::a-hesta"],
  });
  const other = item({
    assertionId: "a-other",
    sliceQualifiedId: "0:source_extraction::a-other",
    label: "Other",
  });
  const items = [hesta, edge, other];

  it("initializes selectable defaults", () => {
    const selected = initialPromoteSelection([
      hesta,
      edge,
      item({
        assertionId: "unresolved:x",
        sliceQualifiedId: "0:source_extraction::unresolved:x",
        label: "Ambiguous",
        selectable: false,
        selectedByDefault: false,
      }),
    ]);
    expect([...selected].sort()).toEqual([
      "0:source_extraction::a-edge",
      "0:source_extraction::a-hesta",
    ]);
  });

  it("deselecting a create node cascades off dependent relationships", () => {
    const selected = initialPromoteSelection(items);
    const next = togglePromoteSelection(items, selected, "0:source_extraction::a-hesta");
    expect(next.has("0:source_extraction::a-hesta")).toBe(false);
    expect(next.has("0:source_extraction::a-edge")).toBe(false);
    expect(next.has("0:source_extraction::a-other")).toBe(true);
  });

  it("selecting a relationship also selects its create-node dependencies", () => {
    const selected = new Set<string>(["0:source_extraction::a-other"]);
    const next = togglePromoteSelection(items, selected, "0:source_extraction::a-edge");
    expect(next.has("0:source_extraction::a-edge")).toBe(true);
    expect(next.has("0:source_extraction::a-hesta")).toBe(true);
  });

  it("deselecting a relationship alone leaves the endpoint node selected", () => {
    const selected = initialPromoteSelection(items);
    const next = togglePromoteSelection(items, selected, "0:source_extraction::a-edge");
    expect(next.has("0:source_extraction::a-edge")).toBe(false);
    expect(next.has("0:source_extraction::a-hesta")).toBe(true);
  });

  it("counts only selectable selected rows", () => {
    const selected = new Set(["0:source_extraction::a-hesta", "0:source_extraction::unresolved:x"]);
    expect(countSelectableSelected(items, selected)).toBe(1);
  });

  describe("cross-slice duplicate assertionId", () => {
    const sharedAssertionId = "assertion:shared";
    const sliceA = item({
      assertionId: sharedAssertionId,
      sliceQualifiedId: "0:standing_context::assertion:shared",
      contributionSliceId: "0:standing_context",
      label: "Heroes (standing)",
      provenance: "standing_context",
    });
    const sliceB = item({
      assertionId: sharedAssertionId,
      sliceQualifiedId: "0:source_extraction::assertion:shared",
      contributionSliceId: "0:source_extraction",
      label: "Heroes (recap)",
      provenance: "source_extraction",
    });
    const crossSliceItems = [sliceA, sliceB];

    it("selects only slice A independently", () => {
      const selected = initialPromoteSelection([
        { ...sliceA, selectedByDefault: false },
        { ...sliceB, selectedByDefault: false },
      ]);
      const next = togglePromoteSelection(crossSliceItems, selected, sliceA.sliceQualifiedId);
      expect([...next]).toEqual([sliceA.sliceQualifiedId]);
      expect(selectedPromoteAssertionIds(crossSliceItems, next)).toEqual([sliceA.sliceQualifiedId]);
    });

    it("selects only slice B independently", () => {
      const selected = initialPromoteSelection([
        { ...sliceA, selectedByDefault: false },
        { ...sliceB, selectedByDefault: false },
      ]);
      const next = togglePromoteSelection(crossSliceItems, selected, sliceB.sliceQualifiedId);
      expect([...next]).toEqual([sliceB.sliceQualifiedId]);
      expect(selectedPromoteAssertionIds(crossSliceItems, next)).toEqual([sliceB.sliceQualifiedId]);
    });

    it("selects both slices when toggled independently", () => {
      let selected = initialPromoteSelection([
        { ...sliceA, selectedByDefault: false },
        { ...sliceB, selectedByDefault: false },
      ]);
      selected = togglePromoteSelection(crossSliceItems, selected, sliceA.sliceQualifiedId);
      selected = togglePromoteSelection(crossSliceItems, selected, sliceB.sliceQualifiedId);
      expect([...selected].sort()).toEqual(
        [sliceA.sliceQualifiedId, sliceB.sliceQualifiedId].sort(),
      );
      expect(selectedPromoteAssertionIds(crossSliceItems, selected).sort()).toEqual(
        [sliceA.sliceQualifiedId, sliceB.sliceQualifiedId].sort(),
      );
    });
  });
});
