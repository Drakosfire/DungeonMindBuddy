import type { JSONContent } from "@tiptap/core";

import type { PlanViewProjection } from "../../api/types";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import type { TiptapRunbookDescriptor } from "../../tiptap/descriptors/tiptapRunbookDescriptors";
import { formatReviewCampaignLabel } from "../sessionCampaignContext";
import type {
  PlanContextDescriptor,
  PlanDocumentDescriptor,
  PlanSessionDescriptor,
} from "../types";

export type {
  PlanDocumentDescriptor,
  PlanDocumentStatus,
  PlanSessionDescriptor,
  PlanSourceStatusKind,
} from "../types";

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

/** Matches existing Longmont corpus layout under `Session Prep/`. */
export function defaultPlanTargetRelpath(campaignId: string, prepSession: number): string {
  const campaignNum = campaignId.match(/^longmont-c(\d+)$/i)?.[1];
  if (!campaignNum) {
    return "TBD durable planning path";
  }
  return `corpus/eldyrwild-markdown/Longmont Campaign/Campaign ${campaignNum}/Session Prep/Session ${prepSession} Prep.md`;
}

export function createPlanDocumentDescriptor(context: PlanContextDescriptor): PlanDocumentDescriptor {
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
  };
}

export function createPlanSessionDescriptor(planView: PlanViewProjection): PlanSessionDescriptor {
  const context = buildPlanContextFromPlanView(planView);
  const planningDocument = createPlanDocumentDescriptor(context);
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

export function buildPlanIngestHref(sessionDescriptor: PlanSessionDescriptor): string {
  const params = new URLSearchParams({
    campaign: sessionDescriptor.campaignId,
    session: `session-${sessionDescriptor.memorySession}`,
  });
  return `/ingest?${params.toString()}`;
}

function sessionPrepStarterMarkdown(sessionDescriptor: PlanSessionDescriptor): string {
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

Add corpus references as you identify the NPCs, locations, and tables you expect to need. Example: [North Reach Gate](#dmb-ref:location:north-reach-gate).`;
}

export function createStarterContentForPlanDocument(
  sessionDescriptor: PlanSessionDescriptor,
): JSONContent {
  return markdownToTiptapDoc(sessionPrepStarterMarkdown(sessionDescriptor)).doc;
}

export function planDocumentToRunbookDescriptor(
  sessionDescriptor: PlanSessionDescriptor,
): TiptapRunbookDescriptor {
  const document = sessionDescriptor.planningDocument;
  return {
    documentId: document.documentId,
    title: document.title,
    campaignId: sessionDescriptor.campaignId,
    session: sessionDescriptor.prepSession,
    targetRelpath: document.targetRelpath,
    themeId: "command",
    description: document.description,
    starterContent: createStarterContentForPlanDocument(sessionDescriptor),
    storageKey: document.storageKey,
  };
}
