import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
} from "react";

import { useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import { usePublishSurfaceInteraction } from "../../agentInteraction/usePublishSurfaceInteraction";
import {
  GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
  readGraphReferenceBinding,
  readGraphReferenceResolutionBinding,
} from "../../graphReference/projectionBindings";
import { validateExactGraphReferenceScope } from "../../graphReference/resolveGraphReference";
import type {
  ExactGraphReferenceScope,
  GraphReferenceProjectionBinding,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
} from "../../graphReference/types";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import { buildSurfaceInteractionIdentity } from "../../surfaceInteraction/surfaceIdentity";
import type { SurfaceInteractionPublication } from "../../surfaceInteraction/types";
import { PlayGraphObjectSheet } from "./PlayGraphObjectSheet";

export const PLAY_EXACT_GRAPH_REFERENCE_SURFACE_ID = "play" as const;

/** Loose Play graph context so incomplete/mismatched callers can fail closed. */
export type PlayGraphContextInput = {
  worldId?: string | null;
  campaignId?: string | null;
  scopeMode?: string | null;
  revisionId?: string | null;
};

export type PlayExactGraphAdmissionReason =
  | "admitted"
  | "incomplete_context"
  | "loading"
  | "error_state"
  | "not_resolved_graph"
  | "corpus_fallback"
  | "ambiguous"
  | "unresolved"
  | "error"
  | "node_id_mismatch"
  | "world_mismatch"
  | "campaign_mismatch"
  | "scope_mode_mismatch"
  | "revision_mismatch";

export type PlayExactGraphAdmission =
  | {
      admitted: true;
      reason: "admitted";
      resolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }>;
    }
  | { admitted: false; reason: Exclude<PlayExactGraphAdmissionReason, "admitted"> };

export interface PlayExactGraphResolveInput {
  requestedNodeId: string;
  activeContext: ExactGraphReferenceScope;
}

export interface PlayExactGraphReferenceHandle {
  openExactGraphReference(requestedNodeId: string): Promise<void>;
}

export interface PlayExactGraphReferenceProps {
  activeContext: PlayGraphContextInput | ExactGraphReferenceScope | null;
  resolve: (input: PlayExactGraphResolveInput) => Promise<GraphReferenceResolution>;
  resolverState?: GraphReferenceProjectionState | null;
  publication?: SurfaceInteractionPublication;
}

export function playExactGraphContextKey(context: ExactGraphReferenceScope): string {
  return [context.worldId, context.campaignId, context.scopeMode, context.revisionId].join("\0");
}

export function asExactPlayGraphContext(
  context: PlayGraphContextInput | ExactGraphReferenceScope | null | undefined,
): ExactGraphReferenceScope | null {
  if (!context) return null;
  const candidate: ExactGraphReferenceScope = {
    worldId: String(context.worldId ?? "").trim(),
    campaignId: String(context.campaignId ?? "").trim(),
    scopeMode: context.scopeMode === "world" ? "world" : "campaign",
    revisionId: String(context.revisionId ?? "").trim(),
  };
  if (context.scopeMode !== "campaign" && context.scopeMode !== "world") {
    return null;
  }
  return validateExactGraphReferenceScope(candidate) ? candidate : null;
}

function scopesEqual(
  left: ExactGraphReferenceScope,
  right: ExactGraphReferenceScope,
): boolean {
  return playExactGraphContextKey(left) === playExactGraphContextKey(right);
}

/**
 * Play-only exact World Graph admission. Shared corpus fallback stays available
 * to other surfaces; Play never opens it.
 */
export function admitPlayExactGraphReference(args: {
  requestedNodeId: string;
  activeContext: PlayGraphContextInput | ExactGraphReferenceScope | null;
  resolution: GraphReferenceResolution;
  resolverState?: GraphReferenceProjectionState | null;
}): PlayExactGraphAdmission {
  const activeContext = asExactPlayGraphContext(args.activeContext);
  if (!activeContext) {
    return { admitted: false, reason: "incomplete_context" };
  }

  if (args.resolverState === "loading") {
    return { admitted: false, reason: "loading" };
  }
  if (args.resolverState === "error") {
    return { admitted: false, reason: "error_state" };
  }

  const requestedNodeId = String(args.requestedNodeId ?? "").trim();
  if (!requestedNodeId) {
    return { admitted: false, reason: "node_id_mismatch" };
  }

  const { resolution } = args;
  if (resolution.projectionState === "loading") {
    return { admitted: false, reason: "loading" };
  }
  if (resolution.kind === "resolved_corpus_fallback") {
    return { admitted: false, reason: "corpus_fallback" };
  }
  if (resolution.kind === "ambiguous") {
    return { admitted: false, reason: "ambiguous" };
  }
  if (resolution.kind === "unresolved") {
    return { admitted: false, reason: "unresolved" };
  }
  if (resolution.kind === "error") {
    return { admitted: false, reason: "error" };
  }
  if (resolution.kind !== "resolved_graph") {
    return { admitted: false, reason: "not_resolved_graph" };
  }

  if (resolution.graphNodeId !== requestedNodeId) {
    return { admitted: false, reason: "node_id_mismatch" };
  }
  if (!validateExactGraphReferenceScope(resolution.graphScope)) {
    return { admitted: false, reason: "revision_mismatch" };
  }
  if (resolution.graphScope.worldId !== activeContext.worldId) {
    return { admitted: false, reason: "world_mismatch" };
  }
  if (resolution.graphScope.campaignId !== activeContext.campaignId) {
    return { admitted: false, reason: "campaign_mismatch" };
  }
  if (resolution.graphScope.scopeMode !== activeContext.scopeMode) {
    return { admitted: false, reason: "scope_mode_mismatch" };
  }
  if (resolution.graphScope.revisionId !== activeContext.revisionId) {
    return { admitted: false, reason: "revision_mismatch" };
  }

  return { admitted: true, reason: "admitted", resolution };
}

const EMPTY_GRAPH_REFERENCE_RESOLUTION: GraphReferenceResolution = {
  kind: "unresolved",
  locator: "",
  reference: null,
  projectionState: null,
  message: "No object selected.",
};

export function buildPlayExactGraphReferencePublication(
  instancePart: string = "exact-graph-reference",
): SurfaceInteractionPublication {
  return {
    surfaceId: PLAY_EXACT_GRAPH_REFERENCE_SURFACE_ID,
    label: "Play",
    identity: buildSurfaceInteractionIdentity({
      surfaceId: PLAY_EXACT_GRAPH_REFERENCE_SURFACE_ID,
      instanceParts: [PLAY_EXACT_GRAPH_REFERENCE_SURFACE_ID, instancePart],
    }),
    canvas: null,
    agentContext: null,
    tools: [],
    editCommands: [],
    projections: [
      {
        id: GRAPH_REFERENCE_PROJECTION_ID,
        kind: "content",
        preferredSize: "wide",
        bindingIds: [GRAPH_REFERENCE_RESOLUTION_BINDING_ID],
      },
    ],
    projectionBindings: [
      {
        id: GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
        value: EMPTY_GRAPH_REFERENCE_RESOLUTION,
      },
    ],
  };
}

function PlayExactGraphCatalogBody({
  bindings,
}: {
  bindings: Readonly<Record<string, unknown>>;
}) {
  const resolution = readGraphReferenceResolutionBinding(bindings);
  if (resolution.kind !== "resolved_graph") return null;
  const graphReferenceBinding = readGraphReferenceBinding(bindings) ?? null;
  return (
    <PlayGraphObjectSheet
      resolution={resolution}
      graphReferenceBinding={graphReferenceBinding}
    />
  );
}

/**
 * Play-owned exact graph admission into the existing shared Projection host.
 * Does not create a /play route or a second host.
 */
export const PlayExactGraphReference = forwardRef<
  PlayExactGraphReferenceHandle,
  PlayExactGraphReferenceProps
>(function PlayExactGraphReference(
  {
    activeContext,
    resolve,
    resolverState = null,
    publication,
  },
  ref,
) {
  const livePublication = useMemo(
    () => publication ?? buildPlayExactGraphReferencePublication(),
    [publication],
  );
  usePublishSurfaceInteraction(livePublication);

  const {
    registerProjectionCatalog,
    registerGraphReferenceBinding,
    openGraphReference,
    openTool,
  } = useAgentInteraction();

  const exactContext = asExactPlayGraphContext(activeContext);
  const admissionKey = [
    livePublication.identity.surfaceId,
    livePublication.identity.instanceKey,
    exactContext ? playExactGraphContextKey(exactContext) : "",
  ].join("\0");
  const admissionKeyRef = useRef(admissionKey);
  const generationRef = useRef(0);
  const mountedRef = useRef(false);
  const exactContextRef = useRef(exactContext);
  const resolveRef = useRef(resolve);
  const resolverStateRef = useRef(resolverState);
  const openGraphReferenceRef = useRef(openGraphReference);
  const pendingRequestedNodeIdRef = useRef<string | null>(null);

  exactContextRef.current = exactContext;
  resolveRef.current = resolve;
  resolverStateRef.current = resolverState;
  openGraphReferenceRef.current = openGraphReference;

  if (admissionKeyRef.current !== admissionKey) {
    admissionKeyRef.current = admissionKey;
    generationRef.current += 1;
  }

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      generationRef.current += 1;
    };
  }, []);

  useEffect(() => {
    return registerProjectionCatalog({
      projectionId: GRAPH_REFERENCE_PROJECTION_ID,
      surfaceId: PLAY_EXACT_GRAPH_REFERENCE_SURFACE_ID,
      kind: "content",
      preferredSize: "wide",
      requiredBindingIds: [GRAPH_REFERENCE_RESOLUTION_BINDING_ID],
      render: ({ bindings }) => <PlayExactGraphCatalogBody bindings={bindings} />,
    });
  }, [registerProjectionCatalog]);

  const openAdmitted = useCallback(
    (
      requestedNodeId: string,
      resolution: GraphReferenceResolution,
      projectionState?: GraphReferenceProjectionState | null,
    ) => {
      const decision = admitPlayExactGraphReference({
        requestedNodeId,
        activeContext: exactContextRef.current,
        resolution,
        resolverState: resolverStateRef.current,
      });
      if (!decision.admitted) return;
      openGraphReferenceRef.current({
        resolution: decision.resolution,
        projectionState: projectionState ?? decision.resolution.projectionState ?? "ready",
        glanceOnly: false,
      });
    },
    [],
  );

  const playBinding = useMemo((): GraphReferenceProjectionBinding => {
    return {
      resolverState,
      resolveRelationship: async (relationship, originatingScope) => {
        const requestedNodeId = String(relationship.targetId ?? "").trim();
        pendingRequestedNodeIdRef.current = requestedNodeId || null;
        const context = originatingScope ?? exactContextRef.current;
        if (!context || !validateExactGraphReferenceScope(context)) {
          pendingRequestedNodeIdRef.current = null;
          return {
            kind: "error",
            locator: requestedNodeId,
            reference: null,
            projectionState: resolverStateRef.current,
            message: "Play graph context is incomplete; relationship resolution blocked.",
          };
        }
        return resolveRef.current({
          requestedNodeId,
          activeContext: context,
        });
      },
      openResolvedReference: (resolution, projectionState) => {
        const requestedNodeId = pendingRequestedNodeIdRef.current
          ?? (resolution.kind === "resolved_graph" ? resolution.graphNodeId : "");
        pendingRequestedNodeIdRef.current = null;
        openAdmitted(requestedNodeId, resolution, projectionState);
      },
      openTool,
    };
  }, [openAdmitted, openTool, resolverState]);

  useEffect(() => {
    return registerGraphReferenceBinding(playBinding);
  }, [playBinding, registerGraphReferenceBinding]);

  const openExactGraphReference = useCallback(async (requestedNodeId: string) => {
    const generationAtStart = generationRef.current;
    const admissionKeyAtStart = admissionKeyRef.current;
    const contextAtStart = exactContextRef.current;
    if (!contextAtStart) return;
    if (resolverStateRef.current === "loading" || resolverStateRef.current === "error") {
      return;
    }

    let resolution: GraphReferenceResolution;
    try {
      resolution = await resolveRef.current({
        requestedNodeId: String(requestedNodeId ?? "").trim(),
        activeContext: contextAtStart,
      });
    } catch {
      return;
    }

    if (
      !mountedRef.current
      || generationRef.current !== generationAtStart
      || admissionKeyRef.current !== admissionKeyAtStart
    ) {
      return;
    }
    const contextNow = exactContextRef.current;
    if (!contextNow || !scopesEqual(contextAtStart, contextNow)) return;

    openAdmitted(requestedNodeId, resolution, resolution.projectionState);
  }, [openAdmitted]);

  useImperativeHandle(ref, () => ({ openExactGraphReference }), [openExactGraphReference]);

  return null;
});
