import { afterEach, describe, expect, it, vi } from "vitest";

import { confirmExtractPromote, confirmFirstWorldGraph, prepareFirstWorldGraph } from "./extractPromoteApi";

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
