import { describe, expect, it } from "vitest";

import {
  resolveGraphReviewWriteAuthority,
  resolvePublishedMemoryBrowseContext,
} from "./graphReviewAuthority";
import type { GraphReviewExactRunHandoff } from "./graphReviewRunSelection";

const exactHandoff: GraphReviewExactRunHandoff = {
  extractionRunId: "er_run_a",
  sourceArtifactId: "sa_1",
  documentId: null,
  revision: null,
  errors: [],
};

describe("graphReviewAuthority", () => {
  it("resolves ordinary ingest campaign/session browse without a run", () => {
    expect(
      resolvePublishedMemoryBrowseContext({
        fallbackCampaignId: "longmont-c2",
        fallbackSessionId: "session-23",
        search: "?campaign=longmont-c2&session=session-27",
      }),
    ).toEqual({
      worldId: null,
      campaignId: "longmont-c2",
      sessionId: "session-27",
      revisionPin: null,
      admissibility: "unknown",
    });
  });

  it("does not treat a leftover catalog run query as browse identity", () => {
    const browse = resolvePublishedMemoryBrowseContext({
      fallbackCampaignId: "longmont-c1",
      fallbackSessionId: "session-1",
      search: "?campaign=longmont-c2&session=session-27&run=er_stale",
    });
    expect(browse.campaignId).toBe("longmont-c2");
    expect(browse.sessionId).toBe("session-27");
  });

  it("grants write authority only for a ready exact-run handoff", () => {
    expect(
      resolveGraphReviewWriteAuthority({
        exactHandoff: null,
        exactHandoffErrors: [],
        exactRun: {
          run_id: "er_run_a",
          source_artifact_id: "sa_1",
          campaign_id: "longmont-c2",
          session_id: "session-23",
        },
        exactRunStatus: "ready",
      }),
    ).toBeNull();

    expect(
      resolveGraphReviewWriteAuthority({
        exactHandoff,
        exactHandoffErrors: [],
        exactRun: {
          run_id: "er_run_a",
          source_artifact_id: "sa_1",
          campaign_id: "longmont-c2",
          session_id: "session-23",
        },
        exactRunStatus: "ready",
      }),
    ).toEqual({
      kind: "exact_run",
      extractionRunId: "er_run_a",
      sourceArtifactId: "sa_1",
      campaignId: "longmont-c2",
      sessionId: "session-23",
    });
  });

  it("does not grant write authority for an invalid or unresolved exact-run handoff", () => {
    expect(
      resolveGraphReviewWriteAuthority({
        exactHandoff,
        exactHandoffErrors: ["handoff extractionRunId does not match the loaded run"],
        exactRun: {
          run_id: "er_other",
          source_artifact_id: "sa_1",
        },
        exactRunStatus: "error",
      }),
    ).toBeNull();
  });
});
