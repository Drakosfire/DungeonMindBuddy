import type { JSONContent } from "@tiptap/core";

import {
  getWorkspaceDocument,
  listWorkspaceDocuments,
} from "../../api/liveApi";
import type { PlanViewProjection, WorkspaceDocumentRecord } from "../../api/types";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import { workspaceDocumentSelectionSearch } from "../../workspaceDocument/workspaceDocumentNavigation";
import { formatReviewCampaignLabel, requestedDocumentIdFromLocation } from "../sessionCampaignContext";
import type {
  PlanContextDescriptor,
  PlanDocumentDescriptor,
  PlanSessionDescriptor,
} from "../types";

export type {
  PlanDocumentDescriptor,
  PlanDocumentContentStatus,
  PlanDocumentStatus,
  PlanSessionDescriptor,
  PlanSourceStatusKind,
} from "../types";

export const FIXTURE_DOC_ID = "11111111-1111-4111-8111-111111111111";

export interface PlanSessionLocationOverrides {
  /** Explicit graph/memory focus from `?session=`. Null/absent → no invented default. */
  memorySession?: number | null;
}

export function workspaceDocumentStorageKey(documentId: string): string {
  return `dmb.workspaceDocument.${documentId}`;
}

/**
 * Plan-facing alias for exact opaque `documentId` URL selection.
 * Owned implementation: `workspaceDocumentSelectionSearch`.
 */
export function planDocumentSelectionSearch(
  currentSearch: string | null | undefined,
  documentId: string,
): string {
  return workspaceDocumentSelectionSearch(currentSearch, documentId);
}

/**
 * Human-facing selector option label. The document title is primary; target
 * session is presentation metadata appended only when the title does not
 * already name it. Identity stays in the option value (`document_id`).
 */
export function planDocumentOptionLabel(record: WorkspaceDocumentRecord): string {
  const title = record.title.trim() || "Untitled prep document";
  const session = record.target_session;
  if (session != null && !title.toLowerCase().includes(`session ${session}`)) {
    return `${title} · Session ${session}`;
  }
  return title;
}

export function workspaceRecordToPlanDocumentDescriptor(
  record: WorkspaceDocumentRecord,
): PlanDocumentDescriptor {
  return {
    documentId: record.document_id,
    title: record.title,
    campaignId: record.campaign_id,
    targetSession: record.target_session,
    targetRelpath: record.target_relpath,
    storageKey: workspaceDocumentStorageKey(record.document_id),
    status: record.status,
    contentStatus: record.content_status,
    revision: record.revision,
    kind: record.kind === "runbook" ? "runbook" : "plan",
    description: record.target_session != null
      ? `Session ${record.target_session} preparation board.`
      : undefined,
  };
}

export function fixtureWorkspaceDocumentRecord(
  overrides: Partial<WorkspaceDocumentRecord> = {},
): WorkspaceDocumentRecord {
  return {
    schema_version: "dmb_workspace_document_record_v1",
    document_id: FIXTURE_DOC_ID,
    title: "C2 Session 23 Prep",
    campaign_id: "longmont-c2",
    target_session: 23,
    kind: "plan",
    target_relpath: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 23 Prep.md",
    status: "active",
    content_status: "draft",
    revision: 1,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function fixturePlanDocumentDescriptor(
  overrides: Partial<PlanDocumentDescriptor> = {},
): PlanDocumentDescriptor {
  return workspaceRecordToPlanDocumentDescriptor(fixtureWorkspaceDocumentRecord({
    document_id: overrides.documentId ?? FIXTURE_DOC_ID,
    title: overrides.title ?? "C2 Session 23 Prep",
    campaign_id: overrides.campaignId ?? "longmont-c2",
    target_session: overrides.targetSession ?? 23,
    target_relpath: overrides.targetRelpath
      ?? "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 23 Prep.md",
    status: overrides.status ?? "active",
    content_status: overrides.contentStatus ?? "draft",
    revision: overrides.revision ?? 1,
    kind: overrides.kind ?? "plan",
  }));
}

export function fixturePlanSessionDescriptor(
  overrides: Partial<PlanSessionDescriptor> = {},
): PlanSessionDescriptor {
  const planningDocument = overrides.planningDocument ?? fixturePlanDocumentDescriptor();
  const { planningDocument: _pd, ...rest } = overrides;
  return {
    surfaceId: "plan",
    campaignId: "longmont-c2",
    campaignLabel: "Longmont C2",
    memorySession: null,
    liveSession: 22,
    sourceStatusLabel: "World graph (all sessions) · set ?session=N to focus",
    sourceStatusKind: "unknown",
    planningDocument,
    ...rest,
  };
}

export function buildPlanContextFromPlanView(
  planView: PlanViewProjection,
  planningDocument: PlanDocumentDescriptor,
  overrides: PlanSessionLocationOverrides = {},
): PlanContextDescriptor {
  const liveSession = planView.session;
  const ingestSession = overrides.memorySession ?? liveSession;
  return {
    campaignId: planView.campaign_id,
    liveSession,
    ingestSession,
    headerLabel: `Plan · ${planningDocument.title}`,
  };
}

export function defaultSessionPrepTitle(campaignLabel: string, targetSession: number): string {
  const shortLabel = campaignLabel.replace(/^Longmont /, "");
  return `${shortLabel} Session ${targetSession} Prep`;
}

/** Matches existing Longmont corpus layout under `Session Prep/`. */
export function defaultPlanTargetRelpath(campaignId: string, targetSession: number): string {
  const campaignNum = campaignId.match(/^longmont-c(\d+)$/i)?.[1];
  if (!campaignNum) {
    return "TBD durable planning path";
  }
  return `corpus/eldyrwild-markdown/Longmont Campaign/Campaign ${campaignNum}/Session Prep/Session ${targetSession} Prep.md`;
}

export function suggestedPlanCreatePayload(campaignId: string, liveSession: number): {
  title: string;
  target_session: number;
  target_relpath: string;
} {
  const targetSession = liveSession + 1;
  const campaignLabel = formatReviewCampaignLabel(campaignId);
  return {
    title: defaultSessionPrepTitle(campaignLabel, targetSession),
    target_session: targetSession,
    target_relpath: defaultPlanTargetRelpath(campaignId, targetSession),
  };
}

/** Next unused target session at or above liveSession + 1. */
export function suggestNextPlanTargetSession(
  liveSession: number,
  occupiedSessions: Array<number | null | undefined>,
): number {
  const occupied = new Set(
    occupiedSessions.filter((session): session is number => session != null),
  );
  let candidate = liveSession + 1;
  while (occupied.has(candidate)) {
    candidate += 1;
  }
  return candidate;
}

/** Durable corpus path when known; null when the campaign layout is not derivable. */
export function durablePlanTargetRelpath(
  campaignId: string,
  targetSession: number,
): string | null {
  const relpath = defaultPlanTargetRelpath(campaignId, targetSession);
  return relpath === "TBD durable planning path" ? null : relpath;
}

export class NoActivePlanningDocumentsError extends Error {
  constructor(campaignId: string) {
    super(`No active planning documents for campaign ${campaignId}`);
    this.name = "NoActivePlanningDocumentsError";
  }
}

export async function resolvePlanningDocument(args: {
  planView: PlanViewProjection;
  locationSearch?: string | null;
}): Promise<PlanDocumentDescriptor> {
  const { planView, locationSearch } = args;
  const campaignId = planView.campaign_id;
  const requestedId = requestedDocumentIdFromLocation(locationSearch);

  if (requestedId) {
    const record = await getWorkspaceDocument(requestedId);
    return workspaceRecordToPlanDocumentDescriptor(record);
  }

  const list = await listWorkspaceDocuments({
    campaign_id: campaignId,
    kind: "plan",
    status: "active",
  });
  if (list.records.length > 0) {
    return workspaceRecordToPlanDocumentDescriptor(list.records[0]);
  }

  throw new NoActivePlanningDocumentsError(campaignId);
}

export function createPlanSessionDescriptor(
  planView: PlanViewProjection,
  planningDocument: PlanDocumentDescriptor,
  overrides: PlanSessionLocationOverrides = {},
): PlanSessionDescriptor {
  const memorySession =
    overrides.memorySession === undefined ? null : overrides.memorySession;
  const sourceStatusLabel =
    memorySession == null
      ? "World graph (all sessions) · set ?session=N to focus"
      : `Session ${memorySession} · open /ingest to review`;
  return {
    surfaceId: "plan",
    campaignId: planView.campaign_id,
    campaignLabel: formatReviewCampaignLabel(planView.campaign_id),
    memorySession,
    liveSession: planView.session,
    sourceStatusLabel,
    sourceStatusKind: "unknown",
    planningDocument,
  };
}

export function buildPlanIngestHref(sessionDescriptor: PlanSessionDescriptor): string {
  const params = new URLSearchParams({
    campaign: sessionDescriptor.campaignId,
  });
  if (sessionDescriptor.memorySession != null) {
    params.set("session", `session-${sessionDescriptor.memorySession}`);
  }
  return `/ingest?${params.toString()}`;
}

function sessionPrepStarterMarkdown(sessionDescriptor: PlanSessionDescriptor): string {
  const { planningDocument, memorySession } = sessionDescriptor;
  const targetSession = planningDocument.targetSession;
  const memoryHeading =
    memorySession == null
      ? "## Memory (world graph)"
      : `## Memory through Session ${memorySession}`;
  const targetLine = targetSession != null
    ? `Summarize what the party knows, unresolved threads, and likely pressure going into Session ${targetSession}.`
    : "Summarize what the party knows, unresolved threads, and likely pressure for this session.";
  return String.raw`# ${planningDocument.title}

## Session intent

What should this session accomplish at the table?

${memoryHeading}

${targetLine}

## Scenes / beats

- Opening frame
- Decision forks
- Exit ramps

## Reference chips

Add corpus references as you identify the NPCs, locations, and tables you expect to need. Example: [North Reach Gate](#dmb-ref:location:north-reach-gate).`;
}

export function createStarterContentForPlanDocument(
  sessionDescriptor: PlanSessionDescriptor,
): JSONContent {
  return markdownToTiptapDoc(sessionPrepStarterMarkdown(sessionDescriptor)).doc;
}
