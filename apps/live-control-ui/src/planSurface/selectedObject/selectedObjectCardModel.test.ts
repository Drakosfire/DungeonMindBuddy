import { describe, expect, it } from "vitest";

import type { ReferenceResolution } from "../reference/referenceResolver";
import { buildSelectedObjectActions } from "./selectedObjectActions";
import { buildSelectedObjectCardModel, hasSourcePreviewTarget } from "./selectedObjectCardModel";

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
    expect(model.metadata?.corpusDisplayPath).toContain("north_reach_gate.md");
    expect(model.metadata?.indexId).toBe("north-reach-gate");
    expect(model.actionIntents).toContain("source_preview");
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
        index_id: "tripod-null-calf",
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
    expect(model.actionIntents).toContain("statblock_tool");
    expect(model.actionIntents).toContain("source_preview");
    expect(model.metadata?.corpusDisplayPath).toContain("tripod_null_calf");
    expect(model.metadata?.indexId).toBe("tripod-null-calf");
  });

  it("uses generic statblock tool intent even when artifact id exists", () => {
    const model = buildSelectedObjectCardModel(
      resolvedResolution("statblock", {
        title: "Tripod Null-Calf",
        artifact_id: "artifact-tripod-null-calf",
      }),
    );

    expect(model.actionIntents).toContain("statblock_tool");
    expect(model.metadata?.artifactId).toBe("artifact-tripod-null-calf");
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

  it("maps roll-table resolution with dice metadata and roll intent", () => {
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
    expect(model.metadata?.dice).toBe("1d12");
    expect(model.actionIntents).toContain("roll");
    expect(model.primaryFields).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: "Table id", value: "gate-dilemma-d12" }),
        expect.objectContaining({ label: "Dice", value: "1d12" }),
      ]),
    );
    expect(model.summary).toBe("Pressure at North Reach Gate.");
  });

  it("omits roll intent when roll-table dice metadata is missing", () => {
    const model = buildSelectedObjectCardModel(
      resolvedResolution("roll-table", {
        table_id: "gate-dilemma",
        title: "Gate Dilemma",
      }),
    );

    expect(model.metadata?.dice).toBeUndefined();
    expect(model.actionIntents).not.toContain("roll");
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
    expect(model.actionIntents).toEqual(["ingest"]);
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
    expect(actionModel.actionIntents).toHaveLength(0);

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
    expect(citationModel.actionIntents).not.toContain("source_preview");
  });

  it("omits source_preview when no source path exists", () => {
    const model = buildSelectedObjectCardModel(
      resolvedResolution(
        "statblock",
        {
          title: "Tripod Null-Calf",
        },
        { sourcePath: "" },
      ),
    );

    expect(hasSourcePreviewTarget(model)).toBe(false);
    expect(model.actionIntents).not.toContain("source_preview");
  });
});

describe("buildSelectedObjectActions", () => {
  it("builds context-aware ingest href when supplied", () => {
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

    const actions = buildSelectedObjectActions(model, {
      ingestHref: "/ingest?campaign=longmont-c2&session=session-23",
    });

    expect(actions).toEqual([
      expect.objectContaining({
        id: "ingest",
        href: "/ingest?campaign=longmont-c2&session=session-23",
      }),
    ]);
  });

  it("labels statblock tool action honestly without object-specific wording", () => {
    const model = buildSelectedObjectCardModel(
      resolvedResolution("statblock", {
        title: "Tripod Null-Calf",
      }),
    );

    const actions = buildSelectedObjectActions(model);
    const statblockAction = actions.find((action) => action.id === "statblock");

    expect(statblockAction?.label).toBe("Open statblock tool");
    expect(statblockAction?.label).not.toMatch(/Tripod Null-Calf/i);
  });

  it("adds roll action for roll-table cards with dice metadata", () => {
    const model = buildSelectedObjectCardModel(
      resolvedResolution("roll-table", {
        table_id: "gate-dilemma-d12",
        title: "Gate Dilemma d12",
        dice: "d12",
      }),
    );

    const actions = buildSelectedObjectActions(model);
    expect(actions).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "roll",
          label: "Roll d12",
          payload: { dice: "d12" },
        }),
      ]),
    );
  });

  it("adds source preview action with payload when source path exists", () => {
    const model = buildSelectedObjectCardModel(
      resolvedResolution("location", {
        index_id: "north-reach-gate",
        title: "North Reach Gate",
        corpus_display_path: "corpus/locations/north_reach_gate.md",
      }),
    );

    const actions = buildSelectedObjectActions(model);
    expect(actions).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "source_preview",
          label: "Show source preview",
          payload: { sourcePath: "corpus/locations/north_reach_gate.md" },
        }),
      ]),
    );
  });

  it("prefers model.sourcePath over metadata corpus path for source preview payload", () => {
    const model = buildSelectedObjectCardModel(
      resolvedResolution(
        "statblock",
        {
          title: "Tripod Null-Calf",
          corpus_display_path: "corpus/bestiary/from-metadata.md",
        },
        { sourcePath: "corpus/bestiary/from-resolution.md" },
      ),
    );

    const actions = buildSelectedObjectActions(model);
    const sourceAction = actions.find((action) => action.id === "source_preview");

    expect(sourceAction?.payload?.sourcePath).toBe("corpus/bestiary/from-resolution.md");
  });
});
