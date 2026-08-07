import { useEffect, useMemo, useRef, useState } from "react";

import { LiveApiError, postWorldGraphProjection } from "../../api/liveApi";
import type {
  WorldGraphProjection,
  WorldGraphProjectionRequest,
} from "../../api/types";
import { referenceFromGraphNode } from "../../graphReference/referenceFromGraphNode";
import type {
  GraphReferenceProjectionState,
  GraphReferenceSearchItem,
} from "../../graphReference/types";
import type { WorldGraphLensProjectionValue } from "../../graphLens/useWorldGraphLensProjection";
import { adaptWorldGraphNodeView } from "../../worldGraph/worldGraphNodeViewAdapter";
import { buildBuildWorldGraphProjectionRequest } from "../../worldGraph/worldGraphSurfaceContext";
import { worldGraphProjectionRequestKey } from "../../worldGraph/worldGraphProjectionRequestKey";
import { verifyWorldGraphProjectionResponse } from "../../worldGraph/verifyWorldGraphProjectionResponse";
import type { BuildGraphLensResolution } from "./resolveBuildGraphLens";

export { verifyWorldGraphProjectionResponse } from "../../worldGraph/verifyWorldGraphProjectionResponse";

export interface UseBuildWorldGraphProjectionInput {
  lens: BuildGraphLensResolution;
  documentIdentity: { documentId: string; campaignId: string };
  /** App-level shared projection — reused only when exact request keys match. */
  sharedProjection?: WorldGraphLensProjectionValue | null;
}

export interface UseBuildWorldGraphProjectionResult {
  projection: WorldGraphProjection | null;
  state: GraphReferenceProjectionState;
  error: string | null;
  requestedRevisionId: string | null;
  loadedRevisionId: string | null;
  revisionMode: "head" | "pinned";
  /** True only when a head request was verified against snapshot.isHead. */
  loadedIsHead: boolean;
  generation: number;
  /** Current lens/document load key — use for synchronous auth (not generation alone). */
  loadKey: string;
  items: readonly GraphReferenceSearchItem[];
  /** Exact request for the current Build Find lens (null when lens cannot form a request). */
  request: WorldGraphProjectionRequest | null;
  requestKey: string | null;
  /** True when bytes came from the shared app projection (no secondary POST). */
  reusedSharedProjection: boolean;
}

type StoredProjectionLoad = {
  loadKey: string;
  projection: WorldGraphProjection | null;
  state: GraphReferenceProjectionState;
  error: string | null;
  loadedRevisionId: string | null;
  loadedIsHead: boolean;
  reusedSharedProjection: boolean;
};

function resolveRevisionFields(lens: BuildGraphLensResolution): {
  revisionMode: "head" | "pinned";
  requestedRevisionId: string | null;
} {
  if (lens.status === "invalid") {
    return { revisionMode: "head", requestedRevisionId: null };
  }
  if (lens.revision.kind === "pinned") {
    return { revisionMode: "pinned", requestedRevisionId: lens.revision.revisionId };
  }
  return { revisionMode: "head", requestedRevisionId: null };
}

function adaptProjectionSearchItems(
  projection: WorldGraphProjection,
  scopeCampaignId: string,
): GraphReferenceSearchItem[] {
  return projection.nodes.map((node) => {
    const nodeView = adaptWorldGraphNodeView(node);
    return {
      nodeId: nodeView.node_id,
      label: nodeView.label,
      kind: nodeView.kind,
      role: nodeView.role,
      summary: nodeView.summary ?? null,
      aliases: nodeView.aliases ?? [],
      scopeLabel: nodeView.campaign_scope ?? scopeCampaignId,
      reference: referenceFromGraphNode(nodeView),
      nodeView,
    };
  });
}

function formatProjectionLoadError(error: unknown): string {
  if (error instanceof LiveApiError) {
    return error.code ? `${error.message} (${error.code})` : error.message;
  }
  return error instanceof Error ? error.message : "Failed to load World Graph projection.";
}

function pendingLoadForKey(loadKey: string): StoredProjectionLoad {
  return {
    loadKey,
    projection: null,
    state: "loading",
    error: null,
    loadedRevisionId: null,
    loadedIsHead: false,
    reusedSharedProjection: false,
  };
}

const EMPTY_SEARCH_ITEMS: readonly GraphReferenceSearchItem[] = [];

export function buildBuildWorldGraphRequestFromLens(
  lens: Extract<BuildGraphLensResolution, { status: "ready" }>,
): WorldGraphProjectionRequest | null {
  const revisionPin =
    lens.revision.kind === "pinned" ? lens.revision.revisionId : null;
  return buildBuildWorldGraphProjectionRequest({
    campaignId: lens.campaignId,
    revisionPin,
    scopeMode: lens.scopeMode,
    focus: lens.focus,
  });
}

/**
 * Structured load identity. Includes scope/focus so Find auth cannot cross lenses.
 * Revision mode and opaque revision id are separate fields so current-head mode
 * never collides with a pinned revision whose id is literally "head".
 */
export function buildBuildGraphProjectionLoadKey(input: {
  documentIdentity: { documentId: string; campaignId: string };
  lens: BuildGraphLensResolution;
}): string {
  const { documentIdentity, lens } = input;
  if (lens.status === "invalid") {
    return JSON.stringify([
      "dmb_build_graph_load_v1",
      documentIdentity.documentId,
      documentIdentity.campaignId,
      "invalid",
      null,
      null,
      null,
      null,
      null,
      lens.reason,
    ]);
  }
  if (lens.status === "selection_required") {
    return JSON.stringify([
      "dmb_build_graph_load_v1",
      lens.documentId,
      lens.documentCampaignId,
      "selection_required",
      null,
      lens.revision.kind,
      lens.revision.kind === "pinned" ? lens.revision.revisionId : null,
      lens.scopeMode,
      lens.focus.kind === "session" ? lens.focus.sessionId : null,
      lens.reason,
    ]);
  }
  return JSON.stringify([
    "dmb_build_graph_load_v1",
    lens.documentId,
    lens.documentCampaignId,
    "ready",
    lens.campaignId,
    lens.revision.kind,
    lens.revision.kind === "pinned" ? lens.revision.revisionId : null,
    lens.scopeMode,
    lens.focus.kind === "session"
      ? `${lens.focus.sessionId}@${lens.focus.focusCampaignId}`
      : null,
  ]);
}

export function useBuildWorldGraphProjection(
  input: UseBuildWorldGraphProjectionInput,
): UseBuildWorldGraphProjectionResult {
  const { lens, documentIdentity, sharedProjection = null } = input;
  const revisionFields = useMemo(() => resolveRevisionFields(lens), [lens]);

  const [stored, setStored] = useState<StoredProjectionLoad>(() =>
    pendingLoadForKey("__init__"),
  );
  const [generation, setGeneration] = useState(0);
  const requestGenerationRef = useRef(0);

  const loadKey = useMemo(
    () => buildBuildGraphProjectionLoadKey({ documentIdentity, lens }),
    [documentIdentity, lens],
  );

  const request = useMemo(() => {
    if (lens.status !== "ready") return null;
    return buildBuildWorldGraphRequestFromLens(lens);
  }, [lens]);

  const requestKey = useMemo(
    () => (request ? worldGraphProjectionRequestKey(request) : null),
    [request],
  );

  const sharedMatches =
    Boolean(requestKey)
    && sharedProjection?.requestKey != null
    && sharedProjection.requestKey === requestKey;

  const sharedState = sharedProjection?.projectionState ?? null;
  const sharedProjectionRef = sharedProjection?.projection ?? null;
  const sharedError = sharedProjection?.projectionError ?? null;

  // Depend on loadKey + shared exact-match signals (not lens object identity).
  useEffect(() => {
    const currentGeneration = ++requestGenerationRef.current;
    setGeneration(currentGeneration);
    const isCurrent = () => currentGeneration === requestGenerationRef.current;

    if (lens.status === "selection_required") {
      setStored({
        loadKey,
        projection: null,
        state: "unavailable",
        error: lens.reason,
        loadedRevisionId: null,
        loadedIsHead: false,
        reusedSharedProjection: false,
      });
      return () => {
        requestGenerationRef.current += 1;
      };
    }

    if (lens.status === "invalid") {
      setStored({
        loadKey,
        projection: null,
        state: "error",
        error: lens.reason,
        loadedRevisionId: null,
        loadedIsHead: false,
        reusedSharedProjection: false,
      });
      return () => {
        requestGenerationRef.current += 1;
      };
    }

    if (!request) {
      setStored({
        loadKey,
        projection: null,
        state: "error",
        error: `Unknown campaign mapping for ${lens.campaignId}.`,
        loadedRevisionId: null,
        loadedIsHead: false,
        reusedSharedProjection: false,
      });
      return () => {
        requestGenerationRef.current += 1;
      };
    }

    const revisionPin =
      lens.revision.kind === "pinned" ? lens.revision.revisionId : null;
    const revisionKind = lens.revision.kind === "pinned" ? "pinned" : "head";

    // Exact match: wait on / adopt the shared provider — no duplicate POST.
    if (sharedMatches && sharedProjection) {
      if (sharedState === "loading") {
        setStored(pendingLoadForKey(loadKey));
        return () => {
          requestGenerationRef.current += 1;
        };
      }

      if (sharedState === "ready" && sharedProjectionRef) {
        const mismatch = verifyWorldGraphProjectionResponse({
          request,
          response: sharedProjectionRef,
          revisionKind,
          pinnedRevisionId: revisionPin,
        });
        if (mismatch) {
          setStored({
            loadKey,
            projection: null,
            state: "error",
            error: mismatch,
            loadedRevisionId: null,
            loadedIsHead: false,
            reusedSharedProjection: false,
          });
          return () => {
            requestGenerationRef.current += 1;
          };
        }
        setStored({
          loadKey,
          projection: sharedProjectionRef,
          state: "ready",
          error: null,
          loadedRevisionId: sharedProjectionRef.snapshot.revisionId,
          loadedIsHead: revisionKind === "head"
            ? sharedProjectionRef.snapshot.isHead === true
            : false,
          reusedSharedProjection: true,
        });
        return () => {
          requestGenerationRef.current += 1;
        };
      }

      if (sharedState === "unavailable") {
        setStored({
          loadKey,
          projection: null,
          state: "unavailable",
          error: null,
          loadedRevisionId: null,
          loadedIsHead: false,
          reusedSharedProjection: true,
        });
        return () => {
          requestGenerationRef.current += 1;
        };
      }

      if (sharedState === "error") {
        setStored({
          loadKey,
          projection: null,
          state: "error",
          error: sharedError ?? "Shared World Graph projection failed.",
          loadedRevisionId: null,
          loadedIsHead: false,
          reusedSharedProjection: true,
        });
        return () => {
          requestGenerationRef.current += 1;
        };
      }
    }

    // Secondary exact load — pinned revision or lens that differs from shared nav.
    setStored(pendingLoadForKey(loadKey));

    void (async () => {
      try {
        const response = await postWorldGraphProjection(request);
        if (!isCurrent()) return;

        const mismatch = verifyWorldGraphProjectionResponse({
          request,
          response,
          revisionKind,
          pinnedRevisionId: revisionPin,
        });
        if (mismatch) {
          setStored({
            loadKey,
            projection: null,
            state: "error",
            error: mismatch,
            loadedRevisionId: null,
            loadedIsHead: false,
            reusedSharedProjection: false,
          });
          return;
        }

        setStored({
          loadKey,
          projection: response,
          state: "ready",
          error: null,
          loadedRevisionId: response.snapshot.revisionId,
          loadedIsHead: revisionKind === "head" ? response.snapshot.isHead === true : false,
          reusedSharedProjection: false,
        });
      } catch (loadError) {
        if (!isCurrent()) return;
        setStored({
          loadKey,
          projection: null,
          state: "error",
          error: formatProjectionLoadError(loadError),
          loadedRevisionId: null,
          loadedIsHead: false,
          reusedSharedProjection: false,
        });
      }
    })();

    return () => {
      requestGenerationRef.current += 1;
    };
    // loadKey encodes document + lens; shared* gates exact-match reuse.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional: avoid lens-identity loops
  }, [
    loadKey,
    requestKey,
    sharedMatches,
    sharedState,
    sharedProjectionRef,
    sharedError,
  ]);

  // Fail closed across the transition render: never expose lens B with projection A.
  const coherent =
    stored.loadKey === loadKey
      ? stored
      : lens.status === "selection_required"
        ? {
            loadKey,
            projection: null,
            state: "unavailable" as const,
            error: lens.reason,
            loadedRevisionId: null,
            loadedIsHead: false,
            reusedSharedProjection: false,
          }
        : lens.status === "invalid"
          ? {
              loadKey,
              projection: null,
              state: "error" as const,
              error: lens.reason,
              loadedRevisionId: null,
              loadedIsHead: false,
              reusedSharedProjection: false,
            }
          : pendingLoadForKey(loadKey);

  const items = useMemo(() => {
    if (coherent.state !== "ready" || !coherent.projection || lens.status !== "ready") {
      return EMPTY_SEARCH_ITEMS;
    }
    return adaptProjectionSearchItems(coherent.projection, lens.campaignId);
  }, [coherent.projection, coherent.state, lens]);

  return useMemo(
    () => ({
      projection: coherent.projection,
      state: coherent.state,
      error: coherent.error,
      requestedRevisionId: revisionFields.requestedRevisionId,
      loadedRevisionId: coherent.loadedRevisionId,
      revisionMode: revisionFields.revisionMode,
      loadedIsHead: coherent.loadedIsHead,
      generation,
      loadKey,
      items,
      request,
      requestKey,
      reusedSharedProjection: coherent.reusedSharedProjection,
    }),
    [
      coherent.error,
      coherent.loadedIsHead,
      coherent.loadedRevisionId,
      coherent.projection,
      coherent.reusedSharedProjection,
      coherent.state,
      generation,
      items,
      loadKey,
      request,
      requestKey,
      revisionFields.requestedRevisionId,
      revisionFields.revisionMode,
    ],
  );
}
