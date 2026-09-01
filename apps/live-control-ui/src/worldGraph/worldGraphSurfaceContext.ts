import type { WorldGraphProjectionRequest } from "../api/types";

export const WORLD_ID_BY_CAMPAIGN: Record<string, string> = {
  "longmont-c1": "eldyrwild",
  "longmont-c2": "eldyrwild",
  // Dogfood (of-conks end-to-end): module world initialized on the local
  // DungeonMind authority; campaign id == world id by gold-package design.
  "of-conks-cons": "of-conks-cons",
};

/**
 * Campaign→world registry. Seeded from the shipped constant so the UI works
 * before/offline; replaced by the authority read (`GET world-graph/campaigns`)
 * once the lens provider fetches it. Module-level so pure resolvers
 * (`resolvePlanGraphLens`, `classifyBuildDocumentScope`) stay synchronous.
 */
export interface WorldGraphCampaignRegistryEntry {
  campaignId: string;
  worldId: string;
}

const DEFAULT_CAMPAIGN_REGISTRY: readonly WorldGraphCampaignRegistryEntry[] = [
  { campaignId: "longmont-c1", worldId: "eldyrwild" },
  { campaignId: "longmont-c2", worldId: "eldyrwild" },
];

let campaignRegistry: readonly WorldGraphCampaignRegistryEntry[] = DEFAULT_CAMPAIGN_REGISTRY;
const registryListeners = new Set<() => void>();

function sameRegistry(
  a: readonly WorldGraphCampaignRegistryEntry[],
  b: readonly WorldGraphCampaignRegistryEntry[],
): boolean {
  return (
    a.length === b.length
    && a.every((entry, index) => (
      entry.campaignId === b[index]?.campaignId && entry.worldId === b[index]?.worldId
    ))
  );
}

export function getCampaignRegistry(): readonly WorldGraphCampaignRegistryEntry[] {
  return campaignRegistry;
}

/** Replace the registry from the authority read; invalid entries are dropped. */
export function setCampaignRegistry(
  entries: readonly WorldGraphCampaignRegistryEntry[],
): void {
  const seen = new Set<string>();
  const cleaned: WorldGraphCampaignRegistryEntry[] = [];
  for (const entry of entries) {
    const campaignId = typeof entry?.campaignId === "string" ? entry.campaignId.trim() : "";
    const worldId = typeof entry?.worldId === "string" ? entry.worldId.trim() : "";
    if (!campaignId || !worldId || seen.has(campaignId)) continue;
    seen.add(campaignId);
    cleaned.push({ campaignId, worldId });
  }
  if (cleaned.length === 0 || sameRegistry(cleaned, campaignRegistry)) return;
  campaignRegistry = cleaned;
  for (const listener of registryListeners) listener();
}

export function subscribeCampaignRegistry(listener: () => void): () => void {
  registryListeners.add(listener);
  return () => {
    registryListeners.delete(listener);
  };
}

export function getWorldIdForCampaign(campaignId: string): string | null {
  const fromRegistry = campaignRegistry.find(
    (entry) => entry.campaignId === campaignId,
  )?.worldId;
  return fromRegistry ?? WORLD_ID_BY_CAMPAIGN[campaignId] ?? null;
}

export function getCampaignIdsForWorld(worldId: string): readonly string[] {
  const ids = new Set<string>(
    campaignRegistry
      .filter((entry) => entry.worldId === worldId)
      .map((entry) => entry.campaignId),
  );
  for (const [campaignId, mappedWorldId] of Object.entries(WORLD_ID_BY_CAMPAIGN)) {
    if (mappedWorldId === worldId) ids.add(campaignId);
  }
  return [...ids].sort();
}

export type BuildDocumentScopeClassification =
  | { kind: "campaign"; campaignId: string; worldId: string }
  | { kind: "world"; worldId: string }
  | { kind: "unknown" };

export function classifyBuildDocumentScope(
  documentCampaignId: string,
): BuildDocumentScopeClassification {
  const trimmed = documentCampaignId.trim();
  const mappedWorldId = WORLD_ID_BY_CAMPAIGN[trimmed];
  if (mappedWorldId) {
    return { kind: "campaign", campaignId: trimmed, worldId: mappedWorldId };
  }

  const campaignIdsForWorld = getCampaignIdsForWorld(trimmed);
  if (campaignIdsForWorld.length > 0) {
    return { kind: "world", worldId: trimmed };
  }

  return { kind: "unknown" };
}

export function buildWorldGraphRecapProjectionRequest(input: {
  campaignId: string;
  sessionId: string;
}): WorldGraphProjectionRequest | null {
  const worldId = getWorldIdForCampaign(input.campaignId);
  if (!worldId) return null;

  return {
    schema: "dmb_world_graph_projection_request_v1",
    worldId,
    campaignId: input.campaignId,
    scopeMode: "campaign",
    focus: {
      kind: "session",
      sessionId: input.sessionId,
      campaignId: input.campaignId,
    },
    admissibility: "gm",
  };
}

export function buildBuildWorldGraphProjectionRequest(input: {
  campaignId: string;
  revisionPin?: string | null;
  scopeMode?: "campaign" | "world";
  focus?:
    | { kind: "none"; sessionId: null }
    | { kind: "session"; sessionId: string; focusCampaignId: string };
}): WorldGraphProjectionRequest | null {
  const worldId = getWorldIdForCampaign(input.campaignId);
  if (!worldId) return null;

  const focus: WorldGraphProjectionRequest["focus"] =
    input.focus?.kind === "session"
      ? {
          kind: "session",
          sessionId: input.focus.sessionId,
          campaignId: input.focus.focusCampaignId,
        }
      : { kind: "none", sessionId: null };

  return {
    schema: "dmb_world_graph_projection_request_v1",
    worldId,
    campaignId: input.campaignId,
    scopeMode: input.scopeMode ?? "campaign",
    focus,
    admissibility: "gm",
    revisionPin: input.revisionPin ?? null,
  };
}

/**
 * Post-confirm Graph Review exact read.
 * Uses receipt.worldId (no remapping). Fail closed when campaign map is missing
 * or disagrees with the receipt world.
 */
export function buildGraphReviewCommittedProjectionRequest(input: {
  campaignId: string;
  sessionId?: string | null;
  receipt: { worldId: string; committedRevisionId: string };
}): WorldGraphProjectionRequest | null {
  const campaignId = input.campaignId.trim();
  const receiptWorldId = input.receipt.worldId.trim();
  const committedRevisionId = input.receipt.committedRevisionId.trim();
  if (!campaignId || !receiptWorldId || !committedRevisionId) return null;

  const mappedWorldId = getWorldIdForCampaign(campaignId);
  if (!mappedWorldId || mappedWorldId !== receiptWorldId) return null;

  const sessionId = input.sessionId?.trim() || "";
  return {
    schema: "dmb_world_graph_projection_request_v1",
    worldId: receiptWorldId,
    campaignId,
    scopeMode: "campaign",
    focus: sessionId
      ? { kind: "session", sessionId, campaignId }
      : { kind: "none", sessionId: null },
    admissibility: "gm",
    revisionPin: committedRevisionId,
  };
}

export function admitBuildDocumentScope(input: {
  documentCampaignId: string | null | undefined;
  incomingCampaignId: string;
}):
  | { ok: true }
  | { ok: false; reason: string } {
  const documentCampaignId = input.documentCampaignId?.trim() ?? "";
  if (!documentCampaignId) {
    return {
      ok: false,
      reason: "Select a Build source with a known campaign or world scope before opening graph context.",
    };
  }

  const worldId = getWorldIdForCampaign(input.incomingCampaignId);
  if (!worldId) {
    return {
      ok: false,
      reason: `Unknown campaign mapping for ${input.incomingCampaignId}. Graph context cannot load.`,
    };
  }

  if (
    documentCampaignId === input.incomingCampaignId
    || documentCampaignId === worldId
  ) {
    return { ok: true };
  }

  return {
    ok: false,
    reason: `Build source scope (${documentCampaignId}) does not admit graph context for campaign ${input.incomingCampaignId} (world ${worldId}).`,
  };
}

/**
 * Browse admission: shared World Graph Find may cross campaigns within the
 * document's admitted world. Unknown document scopes fail closed.
 * Write/insert is object-level via {@link admitBuildObjectInsert} — projection
 * campaignId is a narrative/anchor, not write authority for every node.
 */
export function admitBuildWorldGraphBrowse(input: {
  documentCampaignId: string | null | undefined;
  projectionWorldId: string;
}):
  | { ok: true; documentWorldId: string }
  | { ok: false; reason: string } {
  const documentCampaignId = input.documentCampaignId?.trim() ?? "";
  if (!documentCampaignId) {
    return {
      ok: false,
      reason: "Select a Build source with a known campaign or world scope before opening graph context.",
    };
  }

  const scope = classifyBuildDocumentScope(documentCampaignId);
  if (scope.kind === "unknown") {
    return {
      ok: false,
      reason: `Unknown Build document scope: ${documentCampaignId}.`,
    };
  }

  const projectionWorldId = input.projectionWorldId.trim();
  if (!projectionWorldId || scope.worldId !== projectionWorldId) {
    return {
      ok: false,
      reason:
        `Build source scope (${documentCampaignId}) does not admit World Graph browse for world ${projectionWorldId || "∅"} `
        + `(document world ${scope.worldId}).`,
    };
  }

  return { ok: true, documentWorldId: scope.worldId };
}

/** Compact campaign stamp for insert-denial copy (`longmont-c1` → `C1`). */
function compactCampaignStamp(campaignId: string): string {
  const trimmed = campaignId.trim();
  const longmont = trimmed.match(/^longmont-c(\d+)$/i);
  if (longmont) return `C${longmont[1]}`;
  const bare = trimmed.match(/^c(\d+)$/i);
  if (bare) return `C${bare[1]}`;
  return trimmed;
}

/**
 * Object-level insert admission for Build Find.
 * Campaign-scoped documents admit matching campaign objects plus null/world-universal
 * objects; other campaign-scoped objects are denied. World-scoped documents admit
 * all objects already present in the admitted world projection.
 */
export function admitBuildObjectInsert(input: {
  documentCampaignId: string | null | undefined;
  objectCampaignScope: string | null | undefined;
}):
  | { ok: true }
  | { ok: false; reason: string } {
  const documentCampaignId = input.documentCampaignId?.trim() ?? "";
  if (!documentCampaignId) {
    return {
      ok: false,
      reason: "Select a Build source with a known campaign or world scope before inserting chips.",
    };
  }

  const documentScope = classifyBuildDocumentScope(documentCampaignId);
  if (documentScope.kind === "unknown") {
    return {
      ok: false,
      reason: `Unknown Build document scope: ${documentCampaignId}.`,
    };
  }

  const rawObjectScope = input.objectCampaignScope;
  let objectCampaignScope: string | null;
  if (rawObjectScope == null) {
    objectCampaignScope = null;
  } else {
    const trimmed = rawObjectScope.trim();
    if (!trimmed) {
      // Backend projection integrity rejects blank campaign scopes; do not treat
      // malformed blank tenancy as world-universal.
      return {
        ok: false,
        reason: "Object campaign scope is blank; world-universal requires null.",
      };
    }
    objectCampaignScope = trimmed;
  }

  if (documentScope.kind === "world") {
    if (objectCampaignScope) {
      const objectWorldId = getWorldIdForCampaign(objectCampaignScope);
      if (!objectWorldId) {
        return {
          ok: false,
          reason: `Unknown campaign scope on object (${objectCampaignScope}).`,
        };
      }
      if (objectWorldId !== documentScope.worldId) {
        return {
          ok: false,
          reason:
            `${compactCampaignStamp(objectCampaignScope)} object · `
            + `${documentScope.worldId} document`,
        };
      }
    }
    return { ok: true };
  }

  // Campaign-scoped document: matching campaign + world-universal (null) only.
  if (!objectCampaignScope) {
    return { ok: true };
  }
  if (objectCampaignScope === documentScope.campaignId) {
    return { ok: true };
  }

  return {
    ok: false,
    reason:
      `${compactCampaignStamp(objectCampaignScope)} object · `
      + `${compactCampaignStamp(documentScope.campaignId)} document`,
  };
}
