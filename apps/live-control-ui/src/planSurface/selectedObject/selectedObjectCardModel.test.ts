import { describe, expect, it } from "vitest";

import type { ReferenceResolution } from "../reference/referenceResolver";
import { buildSelectedObjectCardModel } from "./selectedObjectCardModel";

function resolvedResolution(
  refType: string,
  item: Record<string, unknown>,
  overrides: Partial<ReferenceResolution> = {},
): ReferenceResolution {
  return {
    status: "resolved",
    ref: {
      kind: "ref",
      refType,
      refId: String(item.slug ?? item.index_id ?? item.table_id ?? "test-id"),
      label: String(item.title ?? "Test"),
    },
    message: `Resolved from live ${refType} index.`,
    sourcePath: String(item.corpus_display_path ?? item.primary_doc_path ?? ""),
    item,
    ...overrides,
  };
}

describe("buildSelectedObjectCardModel", () => {
  it("maps location resolution to a game-facing card", () => {
    const model = buildSelectedObjectCardModel(
      resolvedResolution("location", {
        index_id: "north-reach-gate",
        title: "North Reach Gate",
        table_note: "Crowded checkpoint.",
        district: "North Reach",
        corpus_display_path: "corpus/locations/north_reach_gate.md",
      }),
    );

    expect(model.status).toBe("resolved");
    expect(model.kind).toBe("location");
    expect(model.title).toBe("North Reach Gate");
    expect(model.subtitle).toBe("Location");
    expect(model.summary).toBe("Crowded checkpoint.");
    expect(model.summary).not.toBe("Resolved from live location index.");
    expect(model.sourcePath).toContain("north_reach_gate.md");
    expect(model.primaryFields.some((field) => field.label === "District")).toBe(true);
  });

  it("maps statblock resolution with CR / HP / AC when present", () => {
    const model = buildSelectedObjectCardModel(
      resolvedResolution("statblock", {
        title: "Tripod Null-Calf",
        challenge_rating: "5",
        armor_class: "16",
        hit_points: "82",
        creature_type: "construct",
        role_tag: "Siege scout",
        corpus_display_path: "corpus/bestiary/tripod_null_calf_statblock_cr5.md",
      }),
    );

    expect(model.kind).toBe("statblock");
    expect(model.primaryFields).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: "CR", value: "5" }),
        expect.objectContaining({ label: "AC", value: "16" }),
        expect.objectContaining({ label: "HP", value: "82" }),
        expect.objectContaining({ label: "Creature type", value: "construct" }),
      ]),
    );
    expect(model.actions.some((action) => action.id === "statblock")).toBe(true);
  });

  it("maps npc resolution with role, faction, and location when present", () => {
    const model = buildSelectedObjectCardModel(
      resolvedResolution("npc", {
        title: "Lysandro Ironveil",
        role: "Gate contact",
        faction: "Ironveil traders",
        location: "North Reach Gate",
        primary_doc_path: "corpus/npcs/lysandro/README.md",
      }),
    );

    expect(model.kind).toBe("npc");
    expect(model.primaryFields).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: "Role", value: "Gate contact" }),
        expect.objectContaining({ label: "Faction", value: "Ironveil traders" }),
        expect.objectContaining({ label: "Location", value: "North Reach Gate" }),
      ]),
    );
  });

  it("maps roll-table resolution with table metadata when present", () => {
    const model = buildSelectedObjectCardModel(
      resolvedResolution("roll-table", {
        table_id: "gate-dilemma-d12",
        title: "Gate Dilemma d12",
        category: "pressure",
        dice: "1d12",
        row_count: "12",
        table_note: "Pressure at North Reach Gate.",
        corpus_display_path: "corpus/tables/gate_dilemma_d12.md",
      }),
    );

    expect(model.kind).toBe("roll-table");
    expect(model.primaryFields).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: "Table id", value: "gate-dilemma-d12" }),
        expect.objectContaining({ label: "Category", value: "pressure" }),
        expect.objectContaining({ label: "Dice", value: "1d12" }),
        expect.objectContaining({ label: "Row count", value: "12" }),
      ]),
    );
    expect(model.summary).toBe("Pressure at North Reach Gate.");
  });

  it("maps unresolved resolution with helpful fallback copy", () => {
    const model = buildSelectedObjectCardModel({
      status: "unresolved",
      ref: {
        kind: "ref",
        refType: "location",
        refId: "north-reach-gate",
        label: "North Reach Gate",
      },
      message: "Could not resolve this reference.",
    });

    expect(model.status).toBe("unresolved");
    expect(model.title).toBe("North Reach Gate");
    expect(model.summary).toMatch(/Could not resolve this reference/i);
    expect(model.primaryFields).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: "Type", value: "location" }),
        expect.objectContaining({ label: "Id", value: "north-reach-gate" }),
      ]),
    );
  });

  it("maps action and citation placeholders without inventing fields", () => {
    const actionModel = buildSelectedObjectCardModel({
      status: "unresolved",
      ref: {
        kind: "action",
        refType: "combat",
        refId: "north-gate-combat",
        label: "North Gate Combat",
      },
      source: "action-placeholder",
      message: "Combat action placeholder. Launch behavior is intentionally disabled.",
    });

    expect(actionModel.title).toBe("Action placeholder");
    expect(actionModel.summary).toMatch(/intentionally disabled/i);
    expect(actionModel.primaryFields).toHaveLength(0);

    const citationModel = buildSelectedObjectCardModel({
      status: "unresolved",
      ref: {
        kind: "ref",
        refType: "citation",
        refId: "c2s22-ending",
        label: "Session 22 ending",
      },
      source: "citation-placeholder",
      message: "Citation resolver pending.",
    });

    expect(citationModel.summary).toBe("Citation resolver pending.");
  });
});
