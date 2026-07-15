import { describe, expect, it } from "vitest";

import type { RecapArtifactRecord } from "../api/types";
import {
  formatReviewCampaignLabel,
  requestedPrepSessionFromLocation,
  requestedSessionNumberFromLocation,
  resolveInitialReviewCampaignId,
  resolveSessionRecapContext,
  sessionsForReviewCampaign,
} from "./sessionCampaignContext";

function recapRecord(campaignId: string, sessionId: string): RecapArtifactRecord {
  return {
    schema_version: "dmb_recap_artifact_record_v1",
    artifact_id: `${campaignId}/${sessionId}`,
    campaign_id: campaignId,
    session_id: sessionId,
    source_artifact_id: null,
    source_recap_path: "corpus/example.md",
    breadcrumb_seed_path: null,
    session_memory_records_path: null,
    run_bundle_uri: "",
    run_manifest_uri: "",
    source_span_index_uri: "",
    provenance_index_uri: null,
    graph_run_refs: [],
    default_graph_run_uri: null,
    default_projection_mode: "recap_graph",
    source_sha256: "sha256:example",
    registered_at: "2026-06-28T00:00:00Z",
    updated_at: "2026-06-28T00:00:00Z",
    registry_source: "scan",
  };
}

describe("sessionCampaignContext", () => {
  it("formats longmont campaign labels", () => {
    expect(formatReviewCampaignLabel("longmont-c1")).toBe("Longmont C1");
    expect(formatReviewCampaignLabel("elderwyld")).toBe("elderwyld");
  });

  it("parses bare and prefixed session query params", () => {
    expect(requestedSessionNumberFromLocation("?session=24")).toBe(24);
    expect(requestedSessionNumberFromLocation("?session=session-23")).toBe(23);
    expect(requestedSessionNumberFromLocation("?prepSession=25")).toBeNull();
    expect(requestedPrepSessionFromLocation("?prepSession=25")).toBe(25);
    expect(requestedPrepSessionFromLocation("?session=24")).toBeNull();
  });

  it("prefers the URL campaign over plan context", () => {
    expect(resolveInitialReviewCampaignId("longmont-c2", "longmont-c1")).toBe("longmont-c1");
    expect(resolveInitialReviewCampaignId("longmont-c2", null)).toBe("longmont-c2");
    expect(resolveInitialReviewCampaignId("longmont-c2", "unknown")).toBe("longmont-c2");
  });

  it("resolves recap records strictly by selected campaign", () => {
    const records = [recapRecord("longmont-c1", "session-1"), recapRecord("longmont-c2", "session-1")];
    expect(resolveSessionRecapContext("session-1", "longmont-c1", records).record?.campaign_id).toBe(
      "longmont-c1",
    );
    expect(resolveSessionRecapContext("session-1", "longmont-c2", records).record?.campaign_id).toBe(
      "longmont-c2",
    );
  });

  it("keeps campaign-scoped gold sessions plus worldbuilding fixtures", () => {
    const sessions = [
      { session_id: "session-1", campaign_id: "longmont-c1" },
      { session_id: "session-23", campaign_id: "longmont-c2" },
      { session_id: "mirathorn-city", campaign_id: null },
    ];
    expect(sessionsForReviewCampaign(sessions, "longmont-c1").map((item) => item.session_id)).toEqual([
      "session-1",
      "mirathorn-city",
    ]);
  });
});
