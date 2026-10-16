import { afterEach, describe, expect, it, vi } from "vitest";

import {
  confirmExtractPromote,
  confirmFirstWorldGraph,
  prepareExtractPromote,
  prepareFirstWorldGraph,
  prepareWorldbuildingWritePlan,
} from "./extractPromoteApi";

function mockJsonResponse(payload: unknown): Response {
  return {
    ok: true,
    status: 200,
    statusText: "OK",
    text: async () => JSON.stringify(payload),
  } as Response;
}

describe("extractPromoteApi confirm", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("confirmExtractPromote posts only schema, reviewPackage, and assertionIds", async () => {
    const reviewPackage = {
      schema: "dmb_extract_promote_proposal_v1",
      proposalId: "prop-1",
    };
    const assertionIds = ["a-hesta", "a-edge"];
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({
        schema: "dmb_extract_promote_confirm_v2",
        outcome: "committed",
        worldId: "eldyrwild",
        proposalId: "prop-1",
        proposalDigest: "digest-a",
        parentRevisionId: "rev:parent",
        committedRevisionId: "rev:committed",
        headAdvanced: true,
        selectedAssertionIds: assertionIds,
        acceptedAssertionIds: assertionIds,
        affectedObjectIds: ["obj-hesta"],
        appliedAssertionCount: 2,
        auditStatus: "ok",
        warnings: [],
      }),
    );

    await confirmExtractPromote({ reviewPackage, assertionIds });

    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toContain("/api/live/extract-promote/confirm");
    expect(init?.method).toBe("POST");
    const body = JSON.parse(String(init?.body));
    expect(body).toEqual({
      schema: "dmb_extract_promote_confirm_request_v2",
      reviewPackage,
      assertionIds,
    });
    expect(Object.keys(body)).toEqual(["schema", "reviewPackage", "assertionIds"]);
  });

  it("prepareFirstWorldGraph posts schema, runId, and decisions", async () => {
    const decisions = [
      { assertionId: "obj_session22_vial", decision: "create_new" as const },
      { assertionId: "e33", decision: "accept" as const },
    ];
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({
        schema: "dmb_first_world_graph_plan_v1",
        planId: "first-world-graph-plan:abc",
        planDigest: "sha256:plan",
        decisionDigest: "sha256:decisions",
        worldId: "the-glass-orchard",
        runId: "run-glass",
        sourceArtifactId: "artifact:worldbuilding:glass",
        sourceRevisionId: "sha256:rev",
        workspaceDocumentId: "doc-1",
        workspaceDocumentRevision: "1",
        extractionProfile: "worldbuilding_shepherds_flock_v0@0.1",
        acceptedAssertionIds: ["obj_session22_vial", "e33"],
        rejectedAssertionIds: [],
        contributionId: "contribution:glass",
        contributionPayloadSha256: "sha256:payload",
        reviewedEffect: {},
        summary: {
          createNewNodeCount: 1,
          acceptedEdgeCount: 1,
          rejectedCandidateCount: 0,
          acceptedAssertionCount: 2,
        },
        confirmable: true,
        diagnostics: [],
      }),
    );

    await prepareFirstWorldGraph({ runId: "run-glass", decisions });

    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toContain(
      "/api/live/extract-promote/worldbuilding/first-world/prepare",
    );
    expect(init?.method).toBe("POST");
    const body = JSON.parse(String(init?.body));
    expect(body).toEqual({
      schema: "dmb_first_world_graph_prepare_request_v1",
      runId: "run-glass",
      decisions,
    });
  });

  it("prepareWorldbuildingWritePlan posts the exact run, parent revision, and dispositions", async () => {
    const dispositions = [
      { assertionId: "place:coast", decision: "create_new" as const },
      { assertionId: "obs:coast:flock", decision: "accept" as const },
    ];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({
        schema: "dmb_worldbuilding_write_plan_v2",
        version: 2,
        planId: "plan-1",
        planDigest: "sha256:plan",
        decisionDigest: "sha256:decisions",
        worldId: "elderwyld",
        parentRevisionId: "rev:parent",
        runId: "run-gazetteer-1",
        sourceDomain: "worldbuilding",
        sourceArtifactId: "artifact:worldbuilding:elderwyld",
        sourceRevisionId: "rev:source",
        extractionProfile: "worldbuilding_gazetteer_v1@1.11",
        candidatePreviewId: "preview-1",
        candidateSchema: "dmb_candidate_graph_v1",
        candidateVersion: "0.2",
        effect: {
          acceptedProposals: [],
          rejectedAssertions: [],
          unresolvedMentions: [],
          deferredCandidateIds: [],
          nodeIdMap: {},
          decisionSnapshot: [],
        },
        summary: {
          createNewNodeCount: 1,
          bindExistingNodeCount: 0,
          acceptedEdgeCount: 0,
          rejectedCandidateCount: 0,
          deferredCandidateCount: 0,
          acceptedAssertionCount: 2,
        },
        diagnostics: [],
        confirmable: false,
        confirmableReason: "Prepared plan is inert.",
      }),
    );

    await prepareWorldbuildingWritePlan({
      runId: "run-gazetteer-1",
      expectedParentRevisionId: "rev:parent",
      dispositions,
    });

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(String(url)).toContain("/api/live/extract-promote/worldbuilding/prepare");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({
      schema: "dmb_worldbuilding_write_plan_prepare_request_v1",
      runId: "run-gazetteer-1",
      expectedParentRevisionId: "rev:parent",
      dispositions,
    });
  });

  it("confirmFirstWorldGraph posts only schema and sealed plan", async () => {
    const plan = {
      schema: "dmb_first_world_graph_plan_v1",
      planId: "first-world-graph-plan:abc",
      planDigest: "sha256:plan",
      decisionDigest: "sha256:decisions",
      worldId: "the-glass-orchard",
      runId: "run-glass",
      sourceArtifactId: "artifact:worldbuilding:glass",
      sourceRevisionId: "sha256:rev",
      workspaceDocumentId: "doc-1",
      workspaceDocumentRevision: "1",
      extractionProfile: "worldbuilding_shepherds_flock_v0@0.1",
      acceptedAssertionIds: [],
      rejectedAssertionIds: [],
      contributionId: "contribution:glass",
      contributionPayloadSha256: "sha256:payload",
      reviewedEffect: {},
      summary: {
        createNewNodeCount: 0,
        acceptedEdgeCount: 0,
        rejectedCandidateCount: 0,
        acceptedAssertionCount: 0,
      },
      confirmable: false,
      diagnostics: [],
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({
        schema: "dmb_first_world_graph_confirm_v1",
        outcome: "initialized",
        worldId: "the-glass-orchard",
        planId: plan.planId,
        planDigest: plan.planDigest,
        decisionDigest: plan.decisionDigest,
        sourceArtifactId: plan.sourceArtifactId,
        sourceRevisionId: plan.sourceRevisionId,
        contributionId: plan.contributionId,
        appliedAssertionCount: 0,
        acceptedAssertionIds: [],
        rejectedAssertionIds: [],
        auditStatus: "ok",
        warnings: [],
      }),
    );

    await confirmFirstWorldGraph({ plan });

    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toContain(
      "/api/live/extract-promote/worldbuilding/first-world/confirm",
    );
    expect(init?.method).toBe("POST");
    const body = JSON.parse(String(init?.body));
    expect(body).toEqual({
      schema: "dmb_first_world_graph_confirm_request_v1",
      plan,
    });
    expect(Object.keys(body)).toEqual(["schema", "plan"]);
  });
});

describe("extractPromoteApi prepare", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("posts the explicit managed World with the exact run and optional node selection", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({}),
    );

    await prepareExtractPromote({
      runId: "run-recap-1",
      managedWorldId: "managed-world-a",
      nodeIds: ["node-a", "node-b"],
    });

    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toContain("/api/live/extract-promote/prepare");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({
      schema: "dmb_extract_promote_prepare_request_v2",
      runId: "run-recap-1",
      managedWorldId: "managed-world-a",
      nodeIds: ["node-a", "node-b"],
    });
  });
});
