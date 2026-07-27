import type { WorkspaceDocumentRecord } from "../api/types";
import {
  PLAN_SURFACE_SPIKE_THEME_ID,
  PLAN_SURFACE_THEME_TOKENS,
} from "../planSurface/config/planSurfaceConfig";
import { formatReviewCampaignLabel } from "../planSurface/sessionCampaignContext";
import type { PlanSessionDescriptor, SurfaceConfig } from "../planSurface/types";
import { BUILD_SURFACE_LABEL } from "./buildSurfaceConfig";

function workspaceRecordToResolverPlanningDocument(
  record: WorkspaceDocumentRecord,
): PlanSessionDescriptor["planningDocument"] {
  return {
    documentId: record.document_id,
    title: record.title,
    campaignId: record.campaign_id,
    targetSession: record.target_session,
    targetRelpath: record.target_relpath,
    storageKey: `dmb.workspaceDocument.${record.document_id}`,
    status: record.status,
    contentStatus: record.content_status,
    revision: record.revision,
    kind: "plan",
  };
}

/** Minimal Plan-shaped session descriptor for shared world-graph resolver (no prep-session lens). */
export function buildGraphReferenceSessionDescriptor(
  record: WorkspaceDocumentRecord,
): PlanSessionDescriptor {
  return {
    surfaceId: "plan",
    campaignId: record.campaign_id,
    campaignLabel: formatReviewCampaignLabel(record.campaign_id),
    memorySession: null,
    liveSession: 0,
    sourceStatusLabel: "Build world graph",
    sourceStatusKind: "unknown",
    planningDocument: workspaceRecordToResolverPlanningDocument(record),
  };
}

export function createBuildSurfaceConfig(record: WorkspaceDocumentRecord): SurfaceConfig {
  const sessionDescriptor = buildGraphReferenceSessionDescriptor(record);
  return {
    id: "build",
    label: BUILD_SURFACE_LABEL,
    context: {
      campaignId: record.campaign_id,
      liveSession: 0,
      ingestSession: 0,
      headerLabel: `${BUILD_SURFACE_LABEL} · ${record.title}`,
    },
    sessionDescriptor,
    tools: [
      {
        id: "build-extraction-run-inspector",
        label: "Extraction Run",
        size: "wide",
      },
    ],
    canvas: {
      documentId: record.document_id,
    },
    theme: {
      themeId: PLAN_SURFACE_SPIKE_THEME_ID,
      tokens: PLAN_SURFACE_THEME_TOKENS,
    },
  };
}
