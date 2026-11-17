import type { StatblockDefinitionV1_Output, StatblockRevisionResourceV1 } from "../contracts/dungeonbuddy-statblocks-v1/client";
import { authenticatedApiFetch, LiveApiError } from "./liveApi";

export interface ConversationDraftScope {
  worldId: string;
  conversationId: string;
  turnId: string;
}

export interface ConversationDraft {
  revision: number;
  markdown: string;
  variant_review_ids?: string[];
}

async function requestDraftResource(scope: ConversationDraftScope, init?: RequestInit, suffix = "") {
  const world = encodeURIComponent(scope.worldId);
  const conversation = encodeURIComponent(scope.conversationId);
  const turn = encodeURIComponent(scope.turnId);
  const path = `/api/live/agent/worlds/${world}/conversations/${conversation}/drafts/${turn}${suffix}`;
  const { response } = await authenticatedApiFetch(path, { cache: "no-store", ...init });
  const body = await response.json();
  if (!response.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : "Conversation draft unavailable.";
    throw new LiveApiError(detail, response.status);
  }
  return body;
}

async function requestDraft(scope: ConversationDraftScope, init?: RequestInit): Promise<ConversationDraft> {
  const body = await requestDraftResource(scope, init);
  if (!Number.isSafeInteger(body?.revision) || body.revision < 1 || typeof body.markdown !== "string") {
    throw new Error("Invalid conversation draft.");
  }
  return { revision: body.revision, markdown: body.markdown, variant_review_ids: body.variant_review_ids };
}

export function openConversationDraft(scope: ConversationDraftScope) {
  return requestDraft(scope);
}

export function saveConversationDraft(scope: ConversationDraftScope, expectedRevision: number, markdown: string) {
  return requestDraft(scope, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ expected_revision: expectedRevision, markdown }),
  });
}

export interface ConversationVariantReview {
  revision: number;
  definition: StatblockDefinitionV1_Output;
  saved?: boolean;
}

export async function openVariantReview(scope: ConversationDraftScope, reviewId: string): Promise<ConversationVariantReview> {
  return requestDraftResource(scope, undefined, `/variant-reviews/${encodeURIComponent(reviewId)}`);
}

export async function confirmVariantReview(scope: ConversationDraftScope, reviewId: string): Promise<{ revision_id: string }> {
  return requestDraftResource(scope, { method: "POST" }, `/variant-reviews/${encodeURIComponent(reviewId)}/confirm`);
}

export function openSavedConversationVariant(scope: ConversationDraftScope, reviewId: string): Promise<{ revision: StatblockRevisionResourceV1 }> {
  return requestDraftResource(scope, undefined, `/variant-reviews/${encodeURIComponent(reviewId)}/saved`);
}
