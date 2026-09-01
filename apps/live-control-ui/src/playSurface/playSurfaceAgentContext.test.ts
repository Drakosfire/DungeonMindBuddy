import { describe, expect, it } from "vitest";

import type { PlayRunRecord } from "../api/types";
import { buildPlaySurfaceAgentContext } from "./playSurfaceAgentContext";

const RUN_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const DOC_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

function playRun(overrides: Partial<PlayRunRecord> = {}): PlayRunRecord {
  return {
    schema_version: "dmb_play_run_record_v1",
    run_id: RUN_ID,
    campaign_id: "longmont-c2",
    playable_artifact_id: DOC_ID,
    playable_revision: 5,
    playable_content_sha256: "c".repeat(64),
    run_revision: 1,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    progress: {
      current_beat_id: "beat:hold-the-breach",
      current_scene_id: "scene:north-gate",
      resolved_beat_ids: [],
      selections: {},
      notes_by_element_id: {},
    },
    rebased_from_run_revision: null,
    ...overrides,
  };
}

describe("buildPlaySurfaceAgentContext", () => {
  it("emits identity witnesses from an admitted Run with Beat and Scene", () => {
    const contribution = buildPlaySurfaceAgentContext(playRun());
    expect(contribution.campaignId).toBe("longmont-c2");
    expect(contribution.documentId).toBe(DOC_ID);
    expect(contribution.sessionNumber).toBeNull();
    expect(contribution.pointers).toEqual([
      { kind: "play_run", value: RUN_ID },
      { kind: "playable_revision", value: "5" },
      { kind: "current_beat", value: "beat:hold-the-breach" },
      { kind: "current_scene", value: "scene:north-gate" },
    ]);
  });

  it("omits current_scene when Beat-only current", () => {
    const contribution = buildPlaySurfaceAgentContext(
      playRun({
        progress: {
          current_beat_id: "beat:hold-the-breach",
          current_scene_id: null,
          resolved_beat_ids: [],
          selections: {},
          notes_by_element_id: {},
        },
      }),
    );
    expect(contribution.pointers).toEqual([
      { kind: "play_run", value: RUN_ID },
      { kind: "playable_revision", value: "5" },
      { kind: "current_beat", value: "beat:hold-the-breach" },
    ]);
  });

  it("publishes no current-moment pointers without an admitted Run Beat", () => {
    expect(buildPlaySurfaceAgentContext(null).pointers).toEqual([]);
    expect(
      buildPlaySurfaceAgentContext(
        playRun({
          progress: {
            current_beat_id: null,
            current_scene_id: null,
            resolved_beat_ids: [],
            selections: {},
            notes_by_element_id: {},
          },
        }),
      ).pointers,
    ).toEqual([]);
  });

  it("does not serialize authored titles, body, selections, or notes", () => {
    const contribution = buildPlaySurfaceAgentContext(
      playRun({
        progress: {
          current_beat_id: "beat:hold-the-breach",
          current_scene_id: "scene:north-gate",
          resolved_beat_ids: ["beat:hold-the-breach"],
          selections: { "choice:route": "option:fire" },
          notes_by_element_id: { "scene:north-gate": "SECRET NOTE" },
        },
      }),
    );
    const serialized = JSON.stringify(contribution);
    expect(serialized).not.toContain("Hold the Breach");
    expect(serialized).not.toContain("North Gate");
    expect(serialized).not.toContain("SECRET NOTE");
    expect(serialized).not.toContain("option:fire");
    expect(serialized).not.toContain(String(1));
  });

  it("reflects updated Run progress in a fresh snapshot", () => {
    const first = buildPlaySurfaceAgentContext(playRun());
    const second = buildPlaySurfaceAgentContext(
      playRun({
        progress: {
          current_beat_id: "beat:other",
          current_scene_id: "scene:other",
          resolved_beat_ids: [],
          selections: {},
          notes_by_element_id: {},
        },
      }),
    );
    expect(first.pointers).not.toEqual(second.pointers);
    expect(second.pointers[2]?.value).toBe("beat:other");
    expect(second.pointers[3]?.value).toBe("scene:other");
  });
});
