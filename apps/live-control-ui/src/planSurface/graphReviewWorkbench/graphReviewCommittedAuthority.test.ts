import { describe, expect, it } from "vitest";

import type {
  ExtractPromoteConfirmReceipt,
  WorldGraphProjection,
  WorldGraphProjectionRequest,
} from "../../api/types";
import {
  catalogRunBindingKey,
  committedBindingsEqual,
  exactRunBindingKey,
  isTerminalConfirmOutcome,
  normalizeAffectedObjectIds,
  selectFirstPresentCommittedObjectId,
  validateCommittedProjectionResponse,
  validateCommittedReceiptAdoption,
} from "./graphReviewCommittedAuthority";

function receipt(
  overrides: Partial<ExtractPromoteConfirmReceipt> = {},
): ExtractPromoteConfirmReceipt {
  return {
    schema: "dmb_extract_promote_confirm_v2",
    outcome: "committed",
    worldId: "eldyrwild",
    proposalId: "prop-1",
    proposalDigest: "digest-a",
    parentRevisionId: "rev:parent",
    committedRevisionId: "rev:committed",
    headAdvanced: true,
    selectedAssertionIds: [],
    acceptedAssertionIds: [],
    affectedObjectIds: [" object-1 ", "object-1", "object-2"],
    appliedAssertionCount: 1,
    auditStatus: "ok",
    warnings: [],
    ...overrides,
  };
}

function request(
  overrides: Partial<WorldGraphProjectionRequest> = {},
): WorldGraphProjectionRequest {
  return {
    schema: "dmb_world_graph_projection_request_v1",
    worldId: "eldyrwild",
    campaignId: "longmont-c2",
    scopeMode: "campaign",
    focus: { kind: "none", sessionId: null },
    admissibility: "gm",
    revisionPin: "rev:committed",
    ...overrides,
  };
}

function projection(
  overrides: Partial<WorldGraphProjection> = {},
): WorldGraphProjection {
  return {
    schema: "dmb_world_graph_projection_v1",
    snapshot: {
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      revisionId: "rev:committed",
      headRevisionId: "rev:committed",
      isHead: true,
      focus: { kind: "none", sessionId: null },
      admissibility: "gm",
      scopeMode: "campaign",
    },
    summary: {
      nodeCount: 1,
      relationshipCount: 0,
      attributeCount: 0,
      evidenceCount: 0,
      sourceArtifactCount: 0,
      projectionTruncated: false,
    },
    nodes: [
      {
        nodeId: "object-1",
        label: "Hesta Ironroot",
        kind: "npc",
        role: "character",
        aliases: [],
        sourceDomains: [],
        anchoredToFocusSession: false,
        evidenceBadges: [],
        adjacency: [],
        suggestedExpansions: [],
        evidenceRefIds: [],
        sourceArtifactIds: [],
      },
    ],
    relationships: [],
    attributes: [],
    evidence: [],
    sourceArtifacts: [],
    diagnostics: [],
    ...overrides,
  };
}

describe("graphReviewCommittedAuthority", () => {
  it("recognizes terminal confirm outcomes", () => {
    expect(isTerminalConfirmOutcome("committed")).toBe(true);
    expect(isTerminalConfirmOutcome("already_applied")).toBe(true);
    expect(isTerminalConfirmOutcome("published_audit_degraded")).toBe(true);
    expect(isTerminalConfirmOutcome("prepared")).toBe(false);
  });

  it("normalizes affected object ids with trim and order-preserving dedupe", () => {
    expect(normalizeAffectedObjectIds([" object-1 ", "object-1", "", "object-2"])).toEqual([
      "object-1",
      "object-2",
    ]);
  });

  it("validates receipt adoption for terminal outcomes and prepared identity", () => {
    expect(validateCommittedReceiptAdoption(receipt()).ok).toBe(true);
    expect(
      validateCommittedReceiptAdoption({
        ...receipt(),
        outcome: "prepared" as ExtractPromoteConfirmReceipt["outcome"],
      }).ok,
    ).toBe(false);
    expect(validateCommittedReceiptAdoption(receipt({ worldId: "  " })).ok).toBe(false);
    expect(
      validateCommittedReceiptAdoption(receipt(), {
        proposalId: "prop-other",
        proposalDigest: "digest-a",
        parentRevisionId: "rev:parent",
        worldId: "eldyrwild",
        runId: "run-a",
        campaignId: "longmont-c2",
        sessionId: "session-25",
      }).ok,
    ).toBe(false);
  });

  it("validates committed projection against frozen request identity", () => {
    expect(
      validateCommittedProjectionResponse({
        projection: projection(),
        receipt: receipt(),
        request: request(),
      }),
    ).toEqual({ ok: true });
    expect(
      validateCommittedProjectionResponse({
        projection: projection({
          snapshot: {
            ...projection().snapshot,
            revisionId: "rev:other",
          },
        }),
        receipt: receipt(),
        request: request(),
      }).ok,
    ).toBe(false);
    expect(
      validateCommittedProjectionResponse({
        projection: projection({
          snapshot: {
            ...projection().snapshot,
            campaignId: "longmont-c1",
          },
        }),
        receipt: receipt(),
        request: request(),
      }).ok,
    ).toBe(false);
    expect(
      validateCommittedProjectionResponse({
        projection: projection({
          snapshot: {
            ...projection().snapshot,
            isHead: false,
            headRevisionId: "rev:head-moved",
          },
        }),
        receipt: receipt(),
        request: request(),
      }),
    ).toEqual({ ok: true });
  });

  it("selects the first affected id present in the committed projection", () => {
    expect(
      selectFirstPresentCommittedObjectId({
        affectedObjectIds: ["missing", "object-1"],
        projection: projection(),
      }),
    ).toBe("object-1");
    expect(
      selectFirstPresentCommittedObjectId({
        affectedObjectIds: ["missing"],
        projection: projection(),
      }),
    ).toBeNull();
  });

  it("compares catalog and exact bindings by stable key identity", () => {
    const catalogA = {
      kind: "catalog_run" as const,
      key: catalogRunBindingKey({
        runId: "run-a",
        campaignId: "c2",
        sessionId: "s25",
      }),
      runId: "run-a",
      campaignId: "c2",
      sessionId: "s25",
    };
    expect(committedBindingsEqual(catalogA, { ...catalogA })).toBe(true);
    expect(
      committedBindingsEqual(catalogA, {
        ...catalogA,
        key: catalogRunBindingKey({
          runId: "run-b",
          campaignId: "c2",
          sessionId: "s25",
        }),
        runId: "run-b",
      }),
    ).toBe(false);
    expect(
      committedBindingsEqual(
        {
          kind: "exact_run",
          key: exactRunBindingKey({
            runId: "er-1",
            sourceArtifactId: "art-1",
            campaignId: "c2",
            sessionId: null,
          }),
          runId: "er-1",
          sourceArtifactId: "art-1",
          campaignId: "c2",
          sessionId: null,
        },
        {
          kind: "exact_run",
          key: exactRunBindingKey({
            runId: "er-1",
            sourceArtifactId: "art-2",
            campaignId: "c2",
            sessionId: null,
          }),
          runId: "er-1",
          sourceArtifactId: "art-2",
          campaignId: "c2",
          sessionId: null,
        },
      ),
    ).toBe(false);
  });

  it("includes campaign and session scope in exact-run binding keys", () => {
    const base = {
      runId: "er-1",
      sourceArtifactId: "art-1",
      campaignId: "c2",
      sessionId: "s25",
    };
    expect(exactRunBindingKey(base)).toBe("exact_run:er-1:art-1:c2:s25");
    expect(
      exactRunBindingKey({ ...base, sessionId: "s26" }),
    ).not.toBe(exactRunBindingKey(base));
    expect(
      exactRunBindingKey({ ...base, campaignId: "c3" }),
    ).not.toBe(exactRunBindingKey(base));
    expect(
      exactRunBindingKey({ ...base, campaignId: null, sessionId: null }),
    ).toBe("exact_run:er-1:art-1::");
  });

  it("rejects prepared campaign/session mismatch against the review binding", () => {
    const prepared = {
      proposalId: "prop-1",
      proposalDigest: "digest-a",
      parentRevisionId: "rev:parent",
      worldId: "eldyrwild",
      runId: "er-1",
      campaignId: "longmont-c2",
      sessionId: "session-25",
    };
    const binding = {
      kind: "exact_run" as const,
      key: exactRunBindingKey({
        runId: "er-1",
        sourceArtifactId: "art-1",
        campaignId: "longmont-c2",
        sessionId: "session-25",
      }),
      runId: "er-1",
      sourceArtifactId: "art-1",
      campaignId: "longmont-c2",
      sessionId: "session-25",
    };
    expect(validateCommittedReceiptAdoption(receipt(), prepared, binding).ok).toBe(true);
    expect(
      validateCommittedReceiptAdoption(
        receipt(),
        { ...prepared, campaignId: "other-campaign" },
        binding,
      ),
    ).toMatchObject({ ok: false, errorKind: "integrity_mismatch" });
    expect(
      validateCommittedReceiptAdoption(
        receipt(),
        { ...prepared, sessionId: "session-other" },
        binding,
      ),
    ).toMatchObject({ ok: false, errorKind: "integrity_mismatch" });
    expect(
      validateCommittedReceiptAdoption(
        receipt(),
        { ...prepared, campaignId: "  longmont-c2  ", sessionId: " session-25 " },
        binding,
      ).ok,
    ).toBe(true);
    expect(
      validateCommittedReceiptAdoption(
        receipt(),
        { ...prepared, campaignId: null, sessionId: null },
        {
          ...binding,
          key: exactRunBindingKey({
            runId: "er-1",
            sourceArtifactId: "art-1",
            campaignId: null,
            sessionId: null,
          }),
          campaignId: null,
          sessionId: null,
        },
      ).ok,
    ).toBe(true);
  });
});
