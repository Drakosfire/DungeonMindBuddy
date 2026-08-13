import { describe, expect, it } from "vitest";

import type { StoredStatblockDraftRecord } from "../../api/types";
import {
  playArtifactIdForThreatNode,
  summaryFromWorkbenchRecord,
} from "./ofConksThreatPlayBridge";

function sampleRecord(overrides: Partial<StoredStatblockDraftRecord> = {}): StoredStatblockDraftRecord {
  return {
    schema_version: "dmb_statblock_draft_record_v1",
    artifact_id: "of-conks-grotesque-tree",
    title: "Grotesque Tree",
    campaign_id: "longmont-c2",
    session: 22,
    stored_at: "2026-08-13T13:31:41.552554Z",
    updated_at: "2026-08-13T14:50:54.361814Z",
    storage_path: "statblock_drafts/of-conks-grotesque-tree.json",
    artifact: {
      artifact_id: "of-conks-grotesque-tree",
      draft_id: "draft-of-conks-grotesque-tree",
      title: "Grotesque Tree",
      markdown: "# Grotesque Tree\n\nArmor Class 11",
      structured_statblock: {
        challenge_rating: "1",
      },
      combat_defaults: {
        name: "Grotesque Tree",
        armor_class: 11,
        hit_points: 39,
        speed: "—",
        primary_actions: ["Branch", "Rock"],
        suggested_tactics: ["Attack anyone within 30 ft."],
      },
      warnings: [],
      provenance: {},
      review_status: "draft",
      lifecycle_state: "workbench_stored",
      storage_status: "stored",
      corpus_status: "not_promoted",
      source_refs: [],
      breadcrumbs: [],
      created_by: "seed",
      created_at: "2026-08-13T13:31:41.552554Z",
      updated_at: "2026-08-13T14:50:54.361814Z",
    },
    ...overrides,
  };
}

describe("playArtifactIdForThreatNode", () => {
  it("maps Of Conks threat node ids with or without threat: prefix", () => {
    expect(playArtifactIdForThreatNode("threat:grotesque-tree")).toBe("of-conks-grotesque-tree");
    expect(playArtifactIdForThreatNode("grotesque-tree")).toBe("of-conks-grotesque-tree");
    expect(playArtifactIdForThreatNode("threat:guardian")).toBe("of-conks-guardian");
    expect(playArtifactIdForThreatNode("threat:caretakers")).toBe("of-conks-caretakers-twig-blight");
  });

  it("returns null for unmapped threats", () => {
    expect(playArtifactIdForThreatNode("threat:tripod-null-calf")).toBeNull();
    expect(playArtifactIdForThreatNode("unknown")).toBeNull();
  });
});

describe("summaryFromWorkbenchRecord", () => {
  it("extracts combat defaults and structured challenge rating", () => {
    const summary = summaryFromWorkbenchRecord(sampleRecord());

    expect(summary).toEqual({
      artifactId: "of-conks-grotesque-tree",
      title: "Grotesque Tree",
      markdown: "# Grotesque Tree\n\nArmor Class 11",
      armorClass: 11,
      hitPoints: 39,
      speed: "—",
      challengeRating: "1",
      tactics: ["Attack anyone within 30 ft."],
      primaryActions: ["Branch", "Rock"],
    });
  });

  it("falls back to speed_summary when speed is absent", () => {
    const summary = summaryFromWorkbenchRecord(
      sampleRecord({
        artifact: {
          ...sampleRecord().artifact,
          combat_defaults: {
            ...sampleRecord().artifact.combat_defaults,
            speed: null,
            speed_summary: "30 ft.",
          },
        },
      }),
    );

    expect(summary.speed).toBe("30 ft.");
  });
});
