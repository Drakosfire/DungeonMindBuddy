import * as liveApi from "./liveApi";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  correctRecapRunEvidence,
  confirmExtractPromote,
  confirmFirstWorldGraph,
  prepareExtractPromote,
  prepareFirstWorldGraph,
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
  beforeEach(() => {
    vi.spyOn(liveApi, "authenticatedApiFetch").mockImplementation(async (path, init) => ({
      response: await fetch(path, init), csrf: null, requestEpoch: 1,
    }));
  });
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
        schema: "dmb_first_world_graph_plan_v3", sourceEvidenceSha256: "sha256:"+"d".repeat(64),
      nativeTarget: {nativeWorldId: "world:"+"1".repeat(32), provisioningId: "provision:"+"2".repeat(32), bindingVersion: 1},
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
      schema: "dmb_first_world_graph_plan_v3", sourceEvidenceSha256: "sha256:"+"d".repeat(64),
      nativeTarget: {nativeWorldId: "world:"+"1".repeat(32), provisioningId: "provision:"+"2".repeat(32), bindingVersion: 1},
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


describe("recap correction adapter", () => {
  afterEach(() => vi.restoreAllMocks());
  const request = { parentRunId: "parent/run", parentCandidateSha256: "a".repeat(64), corrections: [{
    assertionId: "node", evidenceIndex: 0, sourceSpanRefId: "span:39", quoteIndex: 0,
    originalQuote: "invented", replacementQuote: "literal",
  }] };
  const receipt = { schema: "dmb_recap_evidence_correction_response_v1", runId: "child", parentRunId: request.parentRunId,
    parentCandidateSha256: request.parentCandidateSha256, candidateSha256: "b".repeat(64), correctionDigest: "c".repeat(64),
    status: "reviewable", semanticState: "held", semanticBasisSha256: "d".repeat(64) };
  it("uses authenticated transport and the exact pinned payload", async () => {
    const fetch = vi.spyOn(liveApi, "authenticatedApiFetch").mockResolvedValue({ url: "unused", response: Response.json(receipt) });
    await expect(correctRecapRunEvidence(request)).resolves.toEqual(receipt);
    expect(fetch).toHaveBeenCalledTimes(1);
    const [path, init] = fetch.mock.calls[0];
    expect(path).toBe("/api/live/extract-promote/runs/parent%2Frun/recap-evidence-corrections");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({ schema: "dmb_exact_run_evidence_correction_request_v1", ...request });
  });
  it.each([
    { parentRunId: "another" }, { parentCandidateSha256: "e".repeat(64) }, { runId: "parent/run" },
    { candidateSha256: "bad" }, { semanticState: "published" }, { semanticBasisSha256: null },
    { schema: "other" }, { status: "failed" },
  ])("rejects a mismatched receipt %j", async patch => {
    vi.spyOn(liveApi, "authenticatedApiFetch").mockResolvedValue({ url: "unused", response: Response.json({ ...receipt, ...patch }) });
    await expect(correctRecapRunEvidence(request)).rejects.toMatchObject({ status: 0 });
  });
  it("preserves a rejected HTTP outcome without replay", async () => {
    const fetch = vi.spyOn(liveApi, "authenticatedApiFetch").mockResolvedValue({ url: "unused", response: Response.json({ code: "quote_not_literal", message: "Choose literal source words" }, { status: 409 }) });
    await expect(correctRecapRunEvidence(request)).rejects.toMatchObject({ status: 409, code: "quote_not_literal" });
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});


it('sends the current worldbuilding partition wire directly without a quote-only fallback',async()=>{
  const {correctExactRunEvidence,getWorldbuildingFrozenSpans}=await import('./extractPromoteApi');
  const request={schema:'dmb_worldbuilding_evidence_correction_request_v2',parentRunId:'run/a',expectedParentRevision:7,
    expectedParentStatus:'reviewable',worldId:'world',sourceArtifactId:'source',sourceSha256:'a'.repeat(64),spanIndexSha256:'b'.repeat(64),
    parentCandidateSha256:'c'.repeat(64),corrections:[]} as import('./types').WorldbuildingEvidenceCorrectionRequest;
  const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(mockJsonResponse({status:'reviewable'}));
  await correctExactRunEvidence(request);
  expect(String(fetch.mock.calls[0][0])).toContain('/runs/run%2Fa/evidence-corrections');
  expect(JSON.parse(String(fetch.mock.calls[0][1]?.body))).toEqual(request);
  await getWorldbuildingFrozenSpans('run/a');
  expect(String(fetch.mock.calls[1][0])).toContain('/runs/run%2Fa/frozen-source-spans');
  expect(fetch).toHaveBeenCalledTimes(2);fetch.mockRestore();
});
