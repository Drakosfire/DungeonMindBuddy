import { describe, expect, it } from "vitest";

import { isPlanPrepSelectorDocument } from "./planPrepSelectorFilter";

describe("isPlanPrepSelectorDocument", () => {
  it("keeps run packets", () => {
    expect(isPlanPrepSelectorDocument({ title: "Hempholm — run packet" })).toBe(true);
  });

  it("hides roll tables, items, and mechanics moved to product tabs", () => {
    expect(isPlanPrepSelectorDocument({ title: "Hempholm names — roll table" })).toBe(false);
    expect(isPlanPrepSelectorDocument({ title: "Belly’s Mouthwash — item" })).toBe(false);
    expect(isPlanPrepSelectorDocument({ title: "Maglubiyet’s Statue — item" })).toBe(false);
    expect(isPlanPrepSelectorDocument({ title: "Grotesque Tree — mechanics" })).toBe(false);
    expect(isPlanPrepSelectorDocument({ title: "Guardian — mechanics" })).toBe(false);
    expect(
      isPlanPrepSelectorDocument({ title: "Caretakers — tactics (twig blight MM 32)" }),
    ).toBe(false);
  });
});