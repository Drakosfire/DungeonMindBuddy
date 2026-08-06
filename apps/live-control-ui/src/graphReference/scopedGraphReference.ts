import {
  graphScopePresence,
  normalizeRunbookReferenceAttrs,
  type RunbookReferenceAttrs,
} from "../tiptap/references/runbookReferences";
import type { ExactGraphReferenceScope } from "./types";

export function exactScopeFromReferenceAttrs(
  attrs: RunbookReferenceAttrs,
): ExactGraphReferenceScope | null {
  const normalized = normalizeRunbookReferenceAttrs(attrs);
  if (graphScopePresence(normalized) !== "complete") return null;
  return {
    worldId: normalized.graphWorldId as string,
    campaignId: normalized.graphCampaignId as string,
    scopeMode: normalized.graphScopeMode as "campaign" | "world",
    revisionId: normalized.graphRevisionId as string,
  };
}

export function referenceAttrsWithExactScope(
  baseAttrs: Partial<RunbookReferenceAttrs>,
  scope: ExactGraphReferenceScope,
): RunbookReferenceAttrs {
  return normalizeRunbookReferenceAttrs({
    ...baseAttrs,
    graphWorldId: scope.worldId,
    graphCampaignId: scope.campaignId,
    graphScopeMode: scope.scopeMode,
    graphRevisionId: scope.revisionId,
  });
}

export function exactScopesEqual(
  left: ExactGraphReferenceScope,
  right: ExactGraphReferenceScope,
): boolean {
  return left.worldId === right.worldId
    && left.campaignId === right.campaignId
    && left.scopeMode === right.scopeMode
    && left.revisionId === right.revisionId;
}

export { graphScopePresence };
