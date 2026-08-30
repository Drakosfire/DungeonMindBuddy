/**
 * A6: build identity-only SurfaceContext request from lease-guarded publication.
 *
 * Source: SurfaceInteractionPublication.agentContext — never activeSurfaceContext,
 * URL, DOM, thread metadata, label, or ambientSummary.
 */

import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";

export const AGENT_SURFACE_CONTEXT_REQUEST_SCHEMA =
  "dmb_agent_surface_context_request_v1" as const;

export interface AgentSurfacePointerRequestV1 {
  kind: string;
  value: string;
}

export interface AgentSurfaceContextRequestV1 {
  schema: typeof AGENT_SURFACE_CONTEXT_REQUEST_SCHEMA;
  surface_id: string;
  campaign_id: string | null;
  document_id: string | null;
  session_number: number | null;
  pointers: AgentSurfacePointerRequestV1[];
}

const MAX_SURFACE_ID = 64;
const MAX_CAMPAIGN_ID = 128;
const MAX_DOCUMENT_ID = 128;
const MAX_POINTERS = 16;
const MAX_POINTER_KIND = 64;
const MAX_POINTER_VALUE = 256;

function boundedNonEmpty(value: string, max: number): string | null {
  const trimmed = value.trim();
  if (!trimmed || trimmed.length > max) return null;
  return trimmed;
}

/**
 * Snapshot identity-only fields from the active lease-guarded publication.
 * Returns null when publication/agentContext is absent or identity is unsafe.
 */
export function buildAgentSurfaceContextRequest(
  publication: SurfaceInteractionPublication | null | undefined,
): AgentSurfaceContextRequestV1 | null {
  if (!publication?.agentContext) {
    return null;
  }
  const surfaceId = boundedNonEmpty(publication.surfaceId, MAX_SURFACE_ID);
  if (!surfaceId) {
    return null;
  }
  // Prefer publication.surfaceId; do not rewrite mismatched surfaces into Plan.
  const ctx = publication.agentContext;
  let campaignId: string | null = null;
  if (ctx.campaignId != null) {
    campaignId = boundedNonEmpty(ctx.campaignId, MAX_CAMPAIGN_ID);
    if (campaignId == null) return null;
  }
  let documentId: string | null = null;
  if (ctx.documentId != null) {
    // Never serialize local-plan:* as durable server identity.
    if (ctx.documentId.startsWith("local-plan:")) {
      documentId = null;
    } else {
      documentId = boundedNonEmpty(ctx.documentId, MAX_DOCUMENT_ID);
      if (documentId == null) return null;
    }
  }
  const sessionNumber =
    ctx.sessionNumber == null
      ? null
      : Number.isInteger(ctx.sessionNumber) && ctx.sessionNumber >= 1
        ? ctx.sessionNumber
        : null;
  if (ctx.sessionNumber != null && sessionNumber == null) {
    return null;
  }

  const pointers: AgentSurfacePointerRequestV1[] = [];
  if (ctx.pointers.length > MAX_POINTERS) {
    return null;
  }
  for (const pointer of ctx.pointers) {
    const kind = boundedNonEmpty(pointer.kind, MAX_POINTER_KIND);
    const value = boundedNonEmpty(pointer.value, MAX_POINTER_VALUE);
    if (kind == null || value == null) {
      return null;
    }
    pointers.push({ kind, value });
  }

  return {
    schema: AGENT_SURFACE_CONTEXT_REQUEST_SCHEMA,
    surface_id: surfaceId,
    campaign_id: campaignId,
    document_id: documentId,
    session_number: sessionNumber,
    pointers,
  };
}

/**
 * Plan proving-path builder: fail closed to absence when the active lease is not Plan.
 * Does not rewrite foreign surfaces into Plan identity.
 */
export function buildPlanAgentSurfaceContextRequest(
  publication: SurfaceInteractionPublication | null | undefined,
): AgentSurfaceContextRequestV1 | null {
  const request = buildAgentSurfaceContextRequest(publication);
  if (request == null || request.surface_id !== "plan") {
    return null;
  }
  return request;
}
