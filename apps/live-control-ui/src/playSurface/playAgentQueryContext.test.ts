import { describe, expect, it } from "vitest";

import type { PlayRunRecord } from "../api/types";
import { buildPlayAgentWorldGraphQueryContextRequest } from "./playAgentQueryContext";

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

describe("buildPlayAgentWorldGraphQueryContextRequest", () => {
  it("builds campaign-scoped world-union focus for a mapped campaign", () => {
    expect(buildPlayAgentWorldGraphQueryContextRequest(playRun())).toEqual({
      schema: "dmb_agent_world_graph_query_context_request_v1",
      world_id: "eldyrwild",
      campaign_id: "longmont-c2",
      scope_mode: "campaign",
      focus: { kind: "none", session_id: null },
      admissibility: "gm",
      revision_pin: null,
    });
  });

  it("returns null when the campaign has no world mapping", () => {
    expect(
      buildPlayAgentWorldGraphQueryContextRequest(
        playRun({ campaign_id: "unknown-campaign" }),
      ),
    ).toBeNull();
  });
});
