import type {
  ExtractPromoteConfirmReceipt,
  ExtractPromotePrepareResponse,
  WorldGraphProjection,
  WorldGraphProjectionRequest,
} from "../../api/types";

export type GraphReviewCommittedPhase =
  | "candidate"
  | "loading"
  | "ready"
  | "error";

export type GraphReviewCommittedBinding =
  | {
      kind: "catalog_run";
      key: string;
      runId: string;
      campaignId: string;
      sessionId: string;
    }
  | {
      kind: "exact_run";
      key: string;
      runId: string;
      sourceArtifactId: string;
      campaignId: string | null;
      sessionId: string | null;
    };

export function catalogRunBindingKey(input: {
  runId: string;
  campaignId: string;
  sessionId: string;
}): string {
  return `catalog_run:${input.runId}:${input.campaignId}:${input.sessionId}`;
}

export function exactRunBindingKey(input: {
  runId: string;
  sourceArtifactId: string;
  campaignId: string | null;
  sessionId: string | null;
}): string {
  return `exact_run:${input.runId}:${input.sourceArtifactId}:${input.campaignId ?? ""}:${input.sessionId ?? ""}`;
}

function nullNormalizedScope(value: string | null | undefined): string {
  return value?.trim() ?? "";
}

export const TERMINAL_CONFIRM_OUTCOMES = [
  "committed",
  "already_applied",
  "published_audit_degraded",
] as const;

export type TerminalConfirmOutcome = (typeof TERMINAL_CONFIRM_OUTCOMES)[number];

export type CommittedAuthorityErrorKind =
  | "scope_unavailable"
  | "request_failed"
  | "integrity_mismatch";

export function isTerminalConfirmOutcome(
  outcome: string,
): outcome is TerminalConfirmOutcome {
  return (TERMINAL_CONFIRM_OUTCOMES as readonly string[]).includes(outcome);
}

export function committedBindingsEqual(
  left: GraphReviewCommittedBinding | null | undefined,
  right: GraphReviewCommittedBinding | null | undefined,
): boolean {
  if (!left || !right) return left === right;
  return left.key === right.key && left.kind === right.kind;
}

export function normalizeAffectedObjectIds(objectIds: readonly string[]): string[] {
  const seen = new Set<string>();
  const normalized: string[] = [];
  for (const raw of objectIds) {
    const id = raw.trim();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    normalized.push(id);
  }
  return normalized;
}

export type ReceiptAdoptionResult =
  | { ok: true; receipt: ExtractPromoteConfirmReceipt; affectedObjectIds: string[] }
  | { ok: false; reason: string; errorKind: CommittedAuthorityErrorKind };

export function validateCommittedReceiptAdoption(
  receipt: ExtractPromoteConfirmReceipt | null | undefined,
  prepared?: Pick<
    ExtractPromotePrepareResponse,
    "proposalId" | "proposalDigest" | "parentRevisionId" | "worldId" | "runId" | "campaignId" | "sessionId"
  > | null,
  binding?: GraphReviewCommittedBinding | null,
): ReceiptAdoptionResult {
  if (!receipt) {
    return {
      ok: false,
      reason: "Confirm receipt is required to adopt committed authority.",
      errorKind: "integrity_mismatch",
    };
  }
  if (!isTerminalConfirmOutcome(receipt.outcome)) {
    return {
      ok: false,
      reason: `Receipt outcome ${receipt.outcome} is not a terminal confirm outcome.`,
      errorKind: "integrity_mismatch",
    };
  }
  const worldId = receipt.worldId?.trim() ?? "";
  const parentRevisionId = receipt.parentRevisionId?.trim() ?? "";
  const committedRevisionId = receipt.committedRevisionId?.trim() ?? "";
  if (!worldId) {
    return {
      ok: false,
      reason: "Confirm receipt is missing worldId.",
      errorKind: "integrity_mismatch",
    };
  }
  if (!parentRevisionId) {
    return {
      ok: false,
      reason: "Confirm receipt is missing parentRevisionId.",
      errorKind: "integrity_mismatch",
    };
  }
  if (!committedRevisionId) {
    return {
      ok: false,
      reason: "Confirm receipt is missing committedRevisionId.",
      errorKind: "integrity_mismatch",
    };
  }

  if (prepared) {
    if ((prepared.proposalId ?? "").trim() !== (receipt.proposalId ?? "").trim()) {
      return {
        ok: false,
        reason: "Confirm receipt proposalId does not match the prepared proposal.",
        errorKind: "integrity_mismatch",
      };
    }
    if ((prepared.proposalDigest ?? "").trim() !== (receipt.proposalDigest ?? "").trim()) {
      return {
        ok: false,
        reason: "Confirm receipt proposalDigest does not match the prepared proposal.",
        errorKind: "integrity_mismatch",
      };
    }
    if ((prepared.parentRevisionId ?? "").trim() !== parentRevisionId) {
      return {
        ok: false,
        reason: "Confirm receipt parentRevisionId does not match the prepared proposal.",
        errorKind: "integrity_mismatch",
      };
    }
    if ((prepared.worldId ?? "").trim() !== worldId) {
      return {
        ok: false,
        reason: "Confirm receipt worldId does not match the prepared proposal.",
        errorKind: "integrity_mismatch",
      };
    }
    if (binding) {
      const preparedRunId = prepared.runId?.trim() || "";
      if (preparedRunId && preparedRunId !== binding.runId) {
        return {
          ok: false,
          reason: "Prepared runId does not match the current review binding.",
          errorKind: "integrity_mismatch",
        };
      }
      if (
        nullNormalizedScope(prepared.campaignId)
        !== nullNormalizedScope(binding.campaignId)
      ) {
        return {
          ok: false,
          reason: "Prepared campaignId does not match the current review binding.",
          errorKind: "integrity_mismatch",
        };
      }
      if (
        nullNormalizedScope(prepared.sessionId)
        !== nullNormalizedScope(binding.sessionId)
      ) {
        return {
          ok: false,
          reason: "Prepared sessionId does not match the current review binding.",
          errorKind: "integrity_mismatch",
        };
      }
    }
  }

  return {
    ok: true,
    receipt: {
      ...receipt,
      worldId,
      parentRevisionId,
      committedRevisionId,
      affectedObjectIds: normalizeAffectedObjectIds(receipt.affectedObjectIds ?? []),
    },
    affectedObjectIds: normalizeAffectedObjectIds(receipt.affectedObjectIds ?? []),
  };
}

export type CommittedProjectionValidationResult =
  | { ok: true }
  | { ok: false; reason: string; errorKind: CommittedAuthorityErrorKind };

export function validateCommittedProjectionResponse(input: {
  projection: WorldGraphProjection;
  receipt: Pick<ExtractPromoteConfirmReceipt, "worldId" | "committedRevisionId">;
  request: WorldGraphProjectionRequest;
}): CommittedProjectionValidationResult {
  const expectedWorld = input.receipt.worldId.trim();
  const expectedRevision = input.receipt.committedRevisionId.trim();
  const snapshot = input.projection.snapshot;
  const actualWorld = snapshot.worldId?.trim() ?? "";
  const actualRevision = snapshot.revisionId?.trim() ?? "";
  const actualCampaign = snapshot.campaignId?.trim() ?? "";
  const expectedCampaign = input.request.campaignId.trim();

  if (input.projection.schema !== "dmb_world_graph_projection_v1") {
    return {
      ok: false,
      reason: `Unexpected World Graph projection schema: ${String(input.projection.schema)}.`,
      errorKind: "integrity_mismatch",
    };
  }
  if (!actualWorld || actualWorld !== expectedWorld) {
    return {
      ok: false,
      reason: `World Graph projection world mismatch: expected ${expectedWorld}, got ${actualWorld || "(empty)"}.`,
      errorKind: "integrity_mismatch",
    };
  }
  if (!actualCampaign || actualCampaign !== expectedCampaign) {
    return {
      ok: false,
      reason: `World Graph projection campaign mismatch: expected ${expectedCampaign}, got ${actualCampaign || "(empty)"}.`,
      errorKind: "integrity_mismatch",
    };
  }
  if (!actualRevision || actualRevision !== expectedRevision) {
    return {
      ok: false,
      reason: `World Graph projection revision mismatch: expected ${expectedRevision}, got ${actualRevision || "(empty)"}.`,
      errorKind: "integrity_mismatch",
    };
  }
  if (snapshot.admissibility !== "gm" || input.request.admissibility !== "gm") {
    return {
      ok: false,
      reason: `World Graph projection admissibility mismatch: expected gm, got ${snapshot.admissibility}.`,
      errorKind: "integrity_mismatch",
    };
  }
  if (
    snapshot.scopeMode != null
    && input.request.scopeMode != null
    && snapshot.scopeMode !== input.request.scopeMode
  ) {
    return {
      ok: false,
      reason: `World Graph projection scopeMode mismatch: expected ${input.request.scopeMode}, got ${snapshot.scopeMode}.`,
      errorKind: "integrity_mismatch",
    };
  }
  const expectedFocus = input.request.focus;
  const actualFocus = snapshot.focus;
  if (actualFocus.kind !== expectedFocus.kind) {
    return {
      ok: false,
      reason: `World Graph projection focus kind mismatch: expected ${expectedFocus.kind}, got ${actualFocus.kind}.`,
      errorKind: "integrity_mismatch",
    };
  }
  if ((actualFocus.sessionId ?? null) !== (expectedFocus.sessionId ?? null)) {
    return {
      ok: false,
      reason: `World Graph projection focus session mismatch: expected ${expectedFocus.sessionId ?? "null"}, got ${actualFocus.sessionId ?? "null"}.`,
      errorKind: "integrity_mismatch",
    };
  }
  return { ok: true };
}

export function selectFirstPresentCommittedObjectId(input: {
  affectedObjectIds: readonly string[];
  projection: WorldGraphProjection;
}): string | null {
  const present = new Set(input.projection.nodes.map((node) => node.nodeId));
  for (const id of normalizeAffectedObjectIds(input.affectedObjectIds)) {
    if (present.has(id)) return id;
  }
  return null;
}
