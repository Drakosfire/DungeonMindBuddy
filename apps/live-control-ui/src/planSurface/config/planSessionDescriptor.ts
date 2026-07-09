import type { JSONContent } from "@tiptap/core";

import type { PlanViewProjection } from "../../api/types";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import {
  getTiptapRunbookDescriptor,
  isKnownTiptapRunbookDocumentId,
  TIPTAP_RUNBOOK_DESCRIPTORS,
  type TiptapRunbookDescriptor,
} from "../../tiptap/descriptors/tiptapRunbookDescriptors";
import { formatReviewCampaignLabel } from "../sessionCampaignContext";
import type { PlanContextDescriptor } from "../types";

export type PlanDocumentStatus = "local_draft" | "durable" | "missing" | "unknown";
export type PlanDocumentStarterKind = "blank" | "session_prep" | "legacy_north_gate";
export type PlanSourceStatusKind = "ready" | "missing" | "stale" | "unknown";

export interface PlanDocumentDescriptor {
  documentId: string;
  title: string;
  description?: string;
  targetRelpath?: string;
  storageKey: string;
  status: PlanDocumentStatus;
  starterKind: PlanDocumentStarterKind;
}

export interface PlanSessionDescriptor {
  surfaceId: "plan";
  campaignId: string;
  campaignLabel: string;
  prepSession: number;
  memorySession: number;
  liveSession: number;
  sourceStatusLabel: string;
  sourceStatusKind: PlanSourceStatusKind;
  planningDocument: PlanDocumentDescriptor;
}

export interface PlanDocumentOption {
  documentId: string;
  title: string;
  starterKind: PlanDocumentStarterKind;
}

const LEGACY_NORTH_GATE_DOCUMENT_IDS = new Set(
  TIPTAP_RUNBOOK_DESCRIPTORS.map((descriptor) => descriptor.documentId),
);

export function buildPlanContextFromPlanView(planView: PlanViewProjection): PlanContextDescriptor {
  const liveSession = planView.session;
  const prepSession = liveSession + 1;
  const ingestSession = Math.max(1, liveSession - 1);
  const campaignLabel = formatReviewCampaignLabel(planView.campaign_id);
  return {
    campaignId: planView.campaign_id,
    liveSession,
    prepSession,
    ingestSession,
    headerLabel: `Plan · ${campaignLabel} · preparing Session ${prepSession}`,
  };
}

export function createPlanCanvasStorageKey(args: {
  campaignId: string;
  prepSession: number;
  documentId: string;
}): string {
  return `dmb.planCanvas.${args.campaignId}.${args.prepSession}.${args.documentId}`;
}

export function defaultSessionPrepDocumentId(campaignId: string, prepSession: number): string {
  return `${campaignId}-session-${prepSession}-prep`;
}

export function defaultSessionPrepTitle(campaignLabel: string, prepSession: number): string {
  const shortLabel = campaignLabel.replace(/^Longmont /, "");
  return `${shortLabel} Session ${prepSession} Prep`;
}

export function defaultPlanTargetRelpath(campaignId: string, prepSession: number): string {
  const campaignNum = campaignId.match(/^longmont-c(\d+)$/i)?.[1];
  if (!campaignNum) {
    return "TBD durable planning path";
  }
  return `corpus/eldyrwild-markdown/Longmont Campaign/Campaign ${campaignNum}/planning/C${campaignNum}S${prepSession}-prep.md`;
}

export function resolveRequestedPlanDocumentId(
  searchParams: URLSearchParams | null = typeof window === "undefined"
    ? null
    : new URLSearchParams(window.location.search),
): string | null {
  const documentId = searchParams?.get("doc")?.trim();
  return documentId || null;
}

export function createPlanDocumentDescriptor(
  context: PlanContextDescriptor,
  requestedDocumentId?: string | null,
): PlanDocumentDescriptor {
  if (requestedDocumentId && isKnownTiptapRunbookDocumentId(requestedDocumentId)) {
    const legacy = getTiptapRunbookDescriptor(requestedDocumentId);
    return {
      documentId: legacy.documentId,
      title: legacy.title,
      description: legacy.description,
      targetRelpath: legacy.targetRelpath,
      storageKey: createPlanCanvasStorageKey({
        campaignId: context.campaignId,
        prepSession: context.prepSession,
        documentId: legacy.documentId,
      }),
      status: "local_draft",
      starterKind: "legacy_north_gate",
    };
  }

  const documentId = defaultSessionPrepDocumentId(context.campaignId, context.prepSession);
  const campaignLabel = formatReviewCampaignLabel(context.campaignId);
  return {
    documentId,
    title: defaultSessionPrepTitle(campaignLabel, context.prepSession),
    description: `Session ${context.prepSession} preparation board.`,
    targetRelpath: defaultPlanTargetRelpath(context.campaignId, context.prepSession),
    storageKey: createPlanCanvasStorageKey({
      campaignId: context.campaignId,
      prepSession: context.prepSession,
      documentId,
    }),
    status: "local_draft",
    starterKind: "session_prep",
  };
}

export function createPlanSessionDescriptor(
  planView: PlanViewProjection,
  requestedDocumentId?: string | null,
): PlanSessionDescriptor {
  const context = buildPlanContextFromPlanView(planView);
  const planningDocument = createPlanDocumentDescriptor(context, requestedDocumentId);
  return {
    surfaceId: "plan",
    campaignId: context.campaignId,
    campaignLabel: formatReviewCampaignLabel(context.campaignId),
    prepSession: context.prepSession,
    memorySession: context.ingestSession,
    liveSession: context.liveSession,
    sourceStatusLabel: `Session ${context.ingestSession} · open /ingest to review`,
    sourceStatusKind: "unknown",
    planningDocument,
  };
}

export function listSelectablePlanDocuments(
  sessionDescriptor: PlanSessionDescriptor,
): PlanDocumentOption[] {
  const options: PlanDocumentOption[] = [
    {
      documentId: sessionDescriptor.planningDocument.documentId,
      title: sessionDescriptor.planningDocument.title,
      starterKind: sessionDescriptor.planningDocument.starterKind,
    },
  ];

  for (const legacy of TIPTAP_RUNBOOK_DESCRIPTORS) {
    if (legacy.documentId === sessionDescriptor.planningDocument.documentId) continue;
    options.push({
      documentId: legacy.documentId,
      title: legacy.title,
      starterKind: "legacy_north_gate",
    });
  }

  return options;
}

export function buildPlanIngestHref(sessionDescriptor: PlanSessionDescriptor): string {
  const params = new URLSearchParams({
    campaign: sessionDescriptor.campaignId,
    session: `session-${sessionDescriptor.memorySession}`,
  });
  return `/ingest?${params.toString()}`;
}

function sessionPrepStarterMarkdown(
  sessionDescriptor: PlanSessionDescriptor,
): string {
  const { campaignLabel, prepSession, memorySession } = sessionDescriptor;
  return String.raw`# ${defaultSessionPrepTitle(campaignLabel, prepSession)}

## Session intent

What should this session accomplish at the table?

## Memory through Session ${memorySession}

Summarize what the party knows, unresolved threads, and likely pressure going into Session ${prepSession}.

## Scenes / beats

- Opening frame
- Decision forks
- Exit ramps

## Reference chips

Add corpus references as you identify the NPCs, locations, and tables you expect to need.`;
}

export function createStarterContentForPlanDocument(
  document: PlanDocumentDescriptor,
  sessionDescriptor: PlanSessionDescriptor,
): JSONContent {
  if (document.starterKind === "legacy_north_gate") {
    return getTiptapRunbookDescriptor(document.documentId).starterContent as JSONContent;
  }
  return markdownToTiptapDoc(sessionPrepStarterMarkdown(sessionDescriptor)).doc;
}

export function planDocumentToRunbookDescriptor(
  sessionDescriptor: PlanSessionDescriptor,
): TiptapRunbookDescriptor {
  const document = sessionDescriptor.planningDocument;
  if (document.starterKind === "legacy_north_gate") {
    const legacy = getTiptapRunbookDescriptor(document.documentId);
    return {
      ...legacy,
      storageKey: document.storageKey,
    };
  }

  return {
    documentId: document.documentId,
    title: document.title,
    campaignId: sessionDescriptor.campaignId,
    session: sessionDescriptor.prepSession,
    targetRelpath: document.targetRelpath ?? "TBD durable planning path",
    themeId: "command",
    description: document.description,
    starterContent: createStarterContentForPlanDocument(document, sessionDescriptor),
    storageKey: document.storageKey,
  };
}

export function isLegacyNorthGateDocumentId(documentId: string): boolean {
  return LEGACY_NORTH_GATE_DOCUMENT_IDS.has(documentId);
}
