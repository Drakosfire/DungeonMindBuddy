import type { ConversationDraftScope } from "../api/conversationDraftApi";

export interface SavedStatblockTarget {worldId:string;draftId:string;revisionId:string;sourceReviewId?:string}

/** Explicit navigation identity only. The existing server reader owns admission. */
export function savedStatblockHref(target:SavedStatblockTarget):string {
 return '/statblock?'+new URLSearchParams({world:target.worldId,draft:target.draftId,revision:target.revisionId,...(target.sourceReviewId?{sourceReview:target.sourceReviewId}:{})});
}
export function readSavedStatblockTarget(snapshot:string):SavedStatblockTarget|null {
 const params=new URL(snapshot,'http://localhost').searchParams;
 const values=['world','draft','revision'].map(key=>params.getAll(key));
 if(values.some(items=>items.length!==1||!items[0]!.trim()))return null;
 const source = params.getAll('sourceReview');
 if(source.length>1||(source.length===1&&!source[0]?.trim()))return null;
 return {worldId:values[0]![0]!,draftId:values[1]![0]!,revisionId:values[2]![0]!,
  ...(source[0]?{sourceReviewId:source[0]}:{})};
}

export function buildSavedStatblockHref(target: SavedStatblockTarget): string {
 return "/build?" + new URLSearchParams({world: target.worldId, draft: target.draftId, revision: target.revisionId, ...(target.sourceReviewId ? {sourceReview: target.sourceReviewId} : {})});
}

export interface SavedConversationVariantTarget extends ConversationDraftScope {
 reviewId: string;
 portraitOperationId?: string;
}

const uuid = /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i;

export function savedConversationVariantHref(target: SavedConversationVariantTarget): string {
 return "/statblock?" + new URLSearchParams({
  world: target.worldId, conversation: target.conversationId, turn: target.turnId, variantReview: target.reviewId,
  ...(target.portraitOperationId ? { variantPortrait: target.portraitOperationId } : {}),
 });
}

export function readSavedConversationVariantTarget(snapshot: string): SavedConversationVariantTarget | null {
 const params = new URL(snapshot, "http://localhost").searchParams;
 if (params.has("draft") || params.has("revision") || params.has("sourceReview")) return null;
 const values = ["world", "conversation", "turn", "variantReview"].map(key => params.getAll(key));
 if (values.some(items => items.length !== 1 || !items[0]?.trim())) return null;
 const [worldId, conversationId, turnId, reviewId] = values.map(items => items[0]!);
 const portraits = params.getAll("variantPortrait");
 if (portraits.length > 1 || portraits.length === 1 && !uuid.test(portraits[0]!)) return null;
 return { worldId, conversationId, turnId, reviewId, ...(portraits[0] ? { portraitOperationId: portraits[0] } : {}) };
}


/** Inert first-party page link. The server still authorizes the saved receipt. */
export function admittedSavedConversationVariantHref(value: string): boolean {
 if (!value.startsWith("/statblock?") || /[\\#\s]/u.test(value)) return false;
 const target = readSavedConversationVariantTarget(value);
 if (!target) return false;
 const params = new URL(value, "http://localhost").searchParams;
 return [...params].length === (target.portraitOperationId ? 5 : 4) && /^[A-Za-z0-9._:-]+$/.test(target.worldId)
  && [target.conversationId, target.turnId, target.reviewId].every(part => uuid.test(part));
}
