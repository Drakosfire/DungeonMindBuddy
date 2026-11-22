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


export async function openConversationVariantApproval(scope: ConversationDraftScope) {
  const world = encodeURIComponent(scope.worldId);
  const conversation = encodeURIComponent(scope.conversationId);
  const turn = encodeURIComponent(scope.turnId);
  const path = `/api/live/agent/worlds/${world}/conversations/${conversation}/turns/${turn}/variant-approval`;
  const { response } = await authenticatedApiFetch(path, { cache: "no-store" });
  if (!response.ok) throw new LiveApiError("Could not find the reviewed variant.", response.status);
  const body = await response.json();
  if (body?.status !== "ready") {
    throw new Error(body?.status === "ambiguous"
      ? "More than one reviewed variant is available. Open the intended draft to choose it."
      : "No current review is available. Reopen the intended draft before saving.");
  }
  if (typeof body.turn_id !== "string" || typeof body.review_id !== "string"
    || !Number.isSafeInteger(body.revision) || body.revision < 1) {
    throw new Error("Invalid reviewed variant.");
  }
  return { scope: { ...scope, turnId: body.turn_id }, reviewId: body.review_id, revision: body.revision };
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

export type VariantRuleField = "rules_text" | "timing_text" | "condition_text";

export type VariantTextReplacement = ({
  rule_key: string;
  field: VariantRuleField;
} | {
  field: "name";
}) & {
  replace_exact: string;
  with_text: string;
};

export async function correctVariantReview(
  scope: ConversationDraftScope, reviewId: string, revision: number, replacements: VariantTextReplacement[],
): Promise<{ review_id: string; revision: number }> {
  const body = await requestDraftResource(scope, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ expected_revision: revision, replacements }),
  }, `/variant-reviews/${encodeURIComponent(reviewId)}`);
  if (typeof body?.review_id !== "string" || body.revision !== revision + 1) {
    throw new Error("The corrected review could not be verified. Reopen the draft.");
  }
  return body;
}

export async function confirmVariantReview(scope: ConversationDraftScope, reviewId: string): Promise<{ revision_id: string }> {
  return requestDraftResource(scope, { method: "POST" }, `/variant-reviews/${encodeURIComponent(reviewId)}/confirm`);
}

export function openSavedConversationVariant(scope: ConversationDraftScope, reviewId: string): Promise<{ revision: StatblockRevisionResourceV1 }> {
  return requestDraftResource(scope, undefined, `/variant-reviews/${encodeURIComponent(reviewId)}/saved`);
}
