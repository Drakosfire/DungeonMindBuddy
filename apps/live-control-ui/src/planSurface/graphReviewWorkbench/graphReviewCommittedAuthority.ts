import type {
  ExtractPromoteConfirmReceipt,
  WorldGraphProjection,
} from "../../api/types";

export type GraphReviewCommittedPhase =
  | "candidate"
  | "loading"
  | "ready"
  | "error";

export type GraphReviewCommittedBinding =
  | {
      kind: "catalog";
      campaignId: string;
      sessionId: string;
      liveRunId: string;
    }
  | {
      kind: "exact";
      extractionRunId: string;
      campaignId: string;
      sessionId: string;
    };

export const TERMINAL_CONFIRM_OUTCOMES = [
  "committed",
  "already_applied",
  "published_audit_degraded",
] as const;

export type TerminalConfirmOutcome = (typeof TERMINAL_CONFIRM_OUTCOMES)[number];

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
  if (left.kind !== right.kind) return false;
  if (left.kind === "catalog" && right.kind === "catalog") {
    return (
      left.campaignId === right.campaignId &&
      left.sessionId === right.sessionId &&
      left.liveRunId === right.liveRunId
    );
  }
  if (left.kind === "exact" && right.kind === "exact") {
    return left.extractionRunId === right.extractionRunId;
  }
  return false;
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
  | { ok: false; reason: string };

export function validateCommittedReceiptAdoption(
  receipt: ExtractPromoteConfirmReceipt | null | undefined,
): ReceiptAdoptionResult {
  if (!receipt) {
    return { ok: false, reason: "Confirm receipt is required to adopt committed authority." };
  }
  if (!isTerminalConfirmOutcome(receipt.outcome)) {
    return {
      ok: false,
      reason: `Receipt outcome ${receipt.outcome} is not a terminal confirm outcome.`,
    };
  }
  const worldId = receipt.worldId?.trim() ?? "";
  const parentRevisionId = receipt.parentRevisionId?.trim() ?? "";
  const committedRevisionId = receipt.committedRevisionId?.trim() ?? "";
  if (!worldId) {
    return { ok: false, reason: "Confirm receipt is missing worldId." };
  }
  if (!parentRevisionId) {
    return { ok: false, reason: "Confirm receipt is missing parentRevisionId." };
  }
  if (!committedRevisionId) {
    return { ok: false, reason: "Confirm receipt is missing committedRevisionId." };
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
  | { ok: false; reason: string };

export function validateCommittedProjectionResponse(input: {
  projection: WorldGraphProjection;
  receipt: Pick<ExtractPromoteConfirmReceipt, "worldId" | "committedRevisionId">;
}): CommittedProjectionValidationResult {
  const expectedWorld = input.receipt.worldId.trim();
  const expectedRevision = input.receipt.committedRevisionId.trim();
  const actualWorld = input.projection.snapshot.worldId?.trim() ?? "";
  const actualRevision = input.projection.snapshot.revisionId?.trim() ?? "";
  if (!actualWorld || actualWorld !== expectedWorld) {
    return {
      ok: false,
      reason: `World Graph projection world mismatch: expected ${expectedWorld}, got ${actualWorld || "(empty)"}.`,
    };
  }
  if (!actualRevision || actualRevision !== expectedRevision) {
    return {
      ok: false,
      reason: `World Graph projection revision mismatch: expected ${expectedRevision}, got ${actualRevision || "(empty)"}.`,
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
