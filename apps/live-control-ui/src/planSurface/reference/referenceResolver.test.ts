import { describe, expect, it, vi, beforeEach } from "vitest";

import {
  findIndexItem,
  isValidReferenceLocator,
  normalizeReferenceKey,
  resetReferenceIndexCache,
  resolveReference,
} from "./referenceResolver";

describe("referenceResolver", () => {
  beforeEach(() => {
    resetReferenceIndexCache();
  });

  it("validates opaque locators", () => {
    expect(isValidReferenceLocator("lysandro-ironveil")).toBe(true);
    expect(isValidReferenceLocator("../escape")).toBe(false);
    expect(isValidReferenceLocator("")).toBe(false);
  });

  it("normalizes keys like prep.js", () => {
    expect(normalizeReferenceKey("Sewer Meat Creature")).toBe("sewer-meat-creature");
  });

  it("finds npc index items by slug", () => {
    const item = findIndexItem("npc", "lysandro-ironveil", {
      npcs: [{ slug: "lysandro-ironveil", title: "Lysandro Ironveil" }],
    });
    expect(item?.title).toBe("Lysandro Ironveil");
  });

  it("resolves statblock references from path stems", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        statblocks: [{
          title: "Sewer Meat Creature",
          corpus_display_path: "corpus/bestiary/sewer_meat_creature_statblock_cr3.md",
        }],
      }),
    });

    const result = await resolveReference(
      {
        kind: "ref",
        refType: "statblock",
        refId: "sewer-meat-creature",
        label: "Sewer Meat Creature",
      },
      fetchImpl as typeof fetch,
    );

    expect(result.status).toBe("resolved");
    expect(result.sourcePath).toContain("sewer_meat_creature_statblock");
    expect(fetchImpl).toHaveBeenCalledWith("/api/live/statblocks/index");
  });

  it("returns unresolved for missing index hits", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ npcs: [] }),
    });

    const result = await resolveReference(
      {
        kind: "ref",
        refType: "npc",
        refId: "missing-person",
        label: "Missing Person",
      },
      fetchImpl as typeof fetch,
    );

    expect(result.status).toBe("unresolved");
  });
});
