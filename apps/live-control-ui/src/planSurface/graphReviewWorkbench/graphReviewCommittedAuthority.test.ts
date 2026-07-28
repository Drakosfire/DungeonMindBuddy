import { describe, expect, it } from "vitest";

import type { ExtractPromoteConfirmReceipt, WorldGraphProjection } from "../../api/types";
import {
  committedBindingsEqual,
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

  it("validates receipt adoption for terminal outcomes only", () => {
    expect(validateCommittedReceiptAdoption(receipt()).ok).toBe(true);
    expect(
      validateCommittedReceiptAdoption({
        ...receipt(),
        outcome: "prepared" as ExtractPromoteConfirmReceipt["outcome"],
      }).ok,
    ).toBe(false);
    expect(validateCommittedReceiptAdoption(receipt({ worldId: "  " })).ok).toBe(false);
  });

  it("validates committed projection world and revision identity", () => {
    expect(
      validateCommittedProjectionResponse({
        projection: projection(),
        receipt: receipt(),
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
      }).ok,
    ).toBe(false);
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

  it("compares catalog and exact bindings by identity", () => {
    expect(
      committedBindingsEqual(
        { kind: "catalog", campaignId: "c2", sessionId: "s25", liveRunId: "run-a" },
        { kind: "catalog", campaignId: "c2", sessionId: "s25", liveRunId: "run-a" },
      ),
    ).toBe(true);
    expect(
      committedBindingsEqual(
        { kind: "exact", extractionRunId: "er-1", campaignId: "c2", sessionId: "" },
        { kind: "exact", extractionRunId: "er-2", campaignId: "c2", sessionId: "" },
      ),
    ).toBe(false);
  });
});
