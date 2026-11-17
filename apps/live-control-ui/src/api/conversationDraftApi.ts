import { authenticatedApiFetch, LiveApiError } from "./liveApi";

export interface ConversationDraftScope {
  worldId: string;
  conversationId: string;
  turnId: string;
}

export interface ConversationDraft {
  revision: number;
  markdown: string;
}

async function requestDraft(scope: ConversationDraftScope, init?: RequestInit): Promise<ConversationDraft> {
  const world = encodeURIComponent(scope.worldId);
  const conversation = encodeURIComponent(scope.conversationId);
  const turn = encodeURIComponent(scope.turnId);
  const path = `/api/live/agent/worlds/${world}/conversations/${conversation}/drafts/${turn}`;
  const { response } = await authenticatedApiFetch(path, { cache: "no-store", ...init });
  const body = await response.json();
  if (!response.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : "Conversation draft unavailable.";
    throw new LiveApiError(detail, response.status);
  }
  if (!Number.isSafeInteger(body?.revision) || body.revision < 1 || typeof body.markdown !== "string") {
    throw new Error("Invalid conversation draft.");
  }
  return { revision: body.revision, markdown: body.markdown };
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
