import { authenticatedApiFetch } from "./liveApi";
import { ExtractPromoteApiError } from "./extractPromoteApi";

export interface WorldbuildingDecision {
  assertionId: string;
  decision: "create_new" | "bind_existing" | "accept" | "reject" | "defer";
  targetNodeId?: string;
}
export interface WorldbuildingCapabilities {
  schema: "dmb_worldbuilding_publication_capabilities_v1";
  confirmationSupported: true;
  configured: boolean;
  unavailabilityReasons: string[];
}
/** Preserve the complete server-sealed plan for the exact confirm round trip. */
export interface WorldbuildingPlan {
  schema: "dmb_worldbuilding_write_plan_v2";
  version: 2;
  planId: string;
  planDigest: string;
  decisionDigest: string;
  worldId: string;
  parentRevisionId: string;
  runId: string;
  sourceArtifactId: string;
  sourceRevisionId: string;
  prepareBinding: string | null;
  publicationBinding: {
    managedWorldId: string;
    nativeWorldId: string;
    bindingVersion: number;
    sourceArtifactId: string;
    documentId: string;
    documentRevision: number;
    sourceSha256: string;
  } | null;
  effect: {
    decisionSnapshot: Array<WorldbuildingDecision & { candidateKind: string }>;
    acceptedProposals: unknown[];
    [key: string]: unknown;
  };
  summary: {
    createNewNodeCount: number;
    bindExistingNodeCount: number;
    acceptedEdgeCount: number;
    rejectedCandidateCount: number;
    deferredCandidateCount: number;
    acceptedAssertionCount: number;
  };
  diagnostics: string[];
  [key: string]: unknown;
}
export interface WorldbuildingReceipt {
  schema: "dmb_worldbuilding_write_plan_confirm_v1";
  outcome: "committed" | "already_applied" | "published_audit_degraded";
  worldId: string;
  planId: string;
  planDigest: string;
  decisionDigest: string;
  parentRevisionId: string;
  committedRevisionId: string;
  appliedAssertionCount: number;
  auditStatus: "ok" | "degraded";
  warnings: string[];
}
async function request<T>(path: string, body?: unknown): Promise<T> {
  const { response } = await authenticatedApiFetch(`/api/live/extract-promote/worldbuilding/${path}`,
    body === undefined ? undefined : { method: "POST", body: JSON.stringify(body) });
  let parsed: unknown;
  try { parsed = JSON.parse(await response.text()); }
  catch { throw new ExtractPromoteApiError(`Publication response was not JSON (HTTP ${response.status}).`, response.status); }
  if (!response.ok) {
    const error = parsed as {message?: string; code?: string};
    throw new ExtractPromoteApiError(error?.message || `Publication failed (HTTP ${response.status}).`, response.status, error?.code ?? null);
  }
  return parsed as T;
}
export function getWorldbuildingCapabilities() {
  return request<WorldbuildingCapabilities>("capabilities");
}
export function prepareWorldbuilding(input: {runId: string; expectedParentRevisionId: string; dispositions: WorldbuildingDecision[]}) {
  return request<WorldbuildingPlan>("prepare", {schema: "dmb_worldbuilding_write_plan_prepare_request_v1", ...input});
}
export function confirmWorldbuilding(plan: WorldbuildingPlan) {
  return request<WorldbuildingReceipt>("confirm", {schema: "dmb_worldbuilding_write_plan_confirm_request_v1", plan});
}
