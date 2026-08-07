import { useCallback, useEffect, useMemo, useRef, useSyncExternalStore, type ReactNode } from "react";

import { useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphObjectRelationshipViewModel } from "../../graphObjectCard";
import {
  GraphNodeChipRuntimeProvider,
} from "../../graphReference/GraphNodeChipRuntime";
import { glanceOnlyForGraphReference } from "../../graphReference/openGraphReferencePolicy";
import {
  GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
} from "../../graphReference/projectionBindings";
import { resolveGraphReference, extractExactGraphReferenceScope } from "../../graphReference/resolveGraphReference";
import type {
  ExactGraphReferenceScope,
  GraphNodeChipRuntimeValue,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
  GraphReferenceSearchItem,
} from "../../graphReference/types";
import type { GraphProjectionNodeView } from "../../api/types";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import { adaptWorldGraphNodeView } from "../../worldGraph/worldGraphNodeViewAdapter";
import { referenceFromGraphNode } from "../../graphReference/referenceFromGraphNode";
import { deriveApiLens } from "../../graphLens/sessionCampaignContext";
import { useOptionalWorldGraphLens } from "../../graphLens/WorldGraphLensContext";
import { useOptionalWorldGraphLensProjection } from "../../graphLens/useWorldGraphLensProjection";
import type { WorldGraphProjection } from "../../api/types";
import { usePublishSurfaceInteraction } from "../../agentInteraction/usePublishSurfaceInteraction";
import { insertMarkdownReference } from "../../graphReference/insertMarkdownReference";
import { useOptionalMarkdownCanvasSession } from "../../markdownCanvas/MarkdownCanvasSession";
import type { RunbookReferenceAttrs } from "../../tiptap/references/runbookReferences";
import type { WorkspaceDocumentAuthoringPhase } from "../../workspaceDocument/workspaceDocumentAuthoringMachine";
import { isEditorInteractive } from "../../workspaceDocument/workspaceDocumentAuthoringMachine";
import { writeBuildLastCampaignId } from "../buildBareEntryCampaign";
import {
  buildBuildSurfaceInteractionPublication,
  type BuildReferenceContextBinding,
} from "./buildBuildSurfaceInteractionPublication";
import {
  BUILD_REFERENCE_CONTEXT_BINDING_ID,
  BUILD_REFERENCE_SEARCH_PROJECTION_ID,
} from "./buildReferenceIds";
import { BuildReferenceObjectProjection } from "./BuildReferenceObjectProjection";
import { BuildReferenceSearchProjection } from "./BuildReferenceSearchProjection";
import { resolveBuildGraphLens, type BuildGraphLensResolution } from "./resolveBuildGraphLens";
import { useBuildWorldGraphProjection } from "./useBuildWorldGraphProjection";

const EMPTY_PUBLICATION_PHASES: ReadonlySet<WorkspaceDocumentAuthoringPhase> = new Set([
  "unloaded",
  "loading",
  "load_error",
  "conflict",
]);

const EMPTY_SEARCH_ITEMS: readonly GraphReferenceSearchItem[] = [];

/** Stable stub so shared-nav projection does not recreate lens identity every render. */
const SHARED_NAV_PROJECTION_DISABLED_LENS: BuildGraphLensResolution = {
  status: "invalid",
  reason: "Using shared nav World Graph projection.",
};

/**
 * Vitest-only seam: last successful viewExact identity/scope for App-route E5 proof.
 * Idle outside Vitest; never read by production UI.
 */
export const buildViewExactTestSeam = {
  lastGraphNodeId: null as string | null,
  lastGraphScope: null as ExactGraphReferenceScope | null,
  reset() {
    this.lastGraphNodeId = null;
    this.lastGraphScope = null;
  },
};

function subscribeToLocationSearch(onStoreChange: () => void): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }
  window.addEventListener("popstate", onStoreChange);
  return () => window.removeEventListener("popstate", onStoreChange);
}

function getLocationSearchSnapshot(): string {
  if (typeof window === "undefined") return "";
  return window.location.search;
}

function readBuildGraphLensParams(search: string): {
  requestedCampaignId: string | null;
  requestedRevisionId: string | null;
} {
  const params = new URLSearchParams(search);
  return {
    requestedCampaignId: params.get("campaign")?.trim() || null,
    requestedRevisionId: params.get("graphRevision")?.trim() || null,
  };
}

function adaptSharedProjectionSearchItems(
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

function resolveEffectiveBuildGraphLens(
  lens: ReturnType<typeof resolveBuildGraphLens>,
  sharedGraphLens: ReturnType<typeof useOptionalWorldGraphLens>,
  defaultCampaignId: string | null,
): ReturnType<typeof resolveBuildGraphLens> {
  if (lens.status !== "selection_required" || !sharedGraphLens) {
    return lens;
  }
  if (sharedGraphLens.lens.selectedCampaignIds.length === 0) {
    return lens;
  }
  const derived = deriveApiLens(
    sharedGraphLens.lens,
    defaultCampaignId ?? sharedGraphLens.lens.selectedCampaignIds[0],
  );
  if (!derived) {
    return lens;
  }
  return {
    status: "ready",
    documentId: lens.documentId,
    documentCampaignId: lens.documentCampaignId,
    campaignId: derived.campaignId,
    worldId: lens.worldId,
    availableCampaignIds: lens.availableCampaignIds,
    revision: lens.revision,
  };
}

async function resolveBuildRelationshipTarget(input: {
  relationship: GraphObjectRelationshipViewModel;
  projection: ReturnType<typeof useBuildWorldGraphProjection>["projection"];
  projectionState: GraphReferenceProjectionState;
}): Promise<GraphReferenceResolution> {
  const label = String(input.relationship.label || "").trim() || "Related object";
  const targetId = String(input.relationship.targetId || "").trim() || null;
  const targetKind = String(input.relationship.targetKind || "").trim() || null;
  const locator = targetId ? `dmb-node:${targetId}` : label;
  const reference = targetKind && targetId
    ? { kind: "ref" as const, refType: targetKind, refId: targetId, label }
    : null;

  if (input.projectionState === "loading") {
    return {
      kind: "unresolved",
      locator,
      reference,
      projectionState: input.projectionState,
      message: "World Graph projection is loading; relationship resolution deferred.",
    };
  }

  if (input.projectionState === "error") {
    return {
      kind: "error",
      locator,
      reference,
      projectionState: input.projectionState,
      message: "World Graph projection failed; relationship resolution unavailable.",
    };
  }

  if (input.projectionState === "ready" && !input.projection) {
    return {
      kind: "error",
      locator,
      reference,
      projectionState: input.projectionState,
      message:
        "World Graph projection marked ready but no projection was supplied; relationship resolution unavailable.",
    };
  }

  if (input.projectionState === "unavailable") {
    return {
      kind: "unresolved",
      locator,
      reference,
      projectionState: input.projectionState,
      message: "World Graph is unavailable; relationship resolution unavailable.",
    };
  }

  if (targetId && input.projection) {
    const exactNode = input.projection.nodes.find((node) => node.nodeId === targetId) ?? null;
    if (exactNode) {
      const graphScope = extractExactGraphReferenceScope(input.projection);
      if (!graphScope) {
        return {
          kind: "error",
          locator,
          reference,
          projectionState: input.projectionState,
          message:
            "World Graph projection is missing an exact scope; relationship resolution unavailable.",
        };
      }
      const nodeView = adaptWorldGraphNodeView(exactNode);
      return {
        kind: "resolved_graph",
        locator,
        reference,
        graphNodeId: exactNode.nodeId,
        graphObject: buildGraphObjectCardFromNodeView(nodeView),
        graphScope,
        projectionState: input.projectionState,
        message: `Resolved graph node ${exactNode.label}.`,
      };
    }

    return {
      kind: "unresolved",
      locator,
      reference,
      projectionState: input.projectionState,
      message: `Could not resolve related object "${label}" from the loaded World Graph projection.`,
    };
  }

  if (input.projection) {
    return resolveGraphReference({
      locator: label,
      label,
      refType: targetKind,
      projection: input.projection,
      projectionState: input.projectionState,
    });
  }

  return {
    kind: "unresolved",
    locator,
    reference,
    projectionState: input.projectionState,
    message: `Could not resolve related object "${label}" from graph memory.`,
  };
}

export interface BuildReferenceCapabilityProps {
  documentId: string | null;
  children?: ReactNode;
}

export function BuildReferenceCapability({ documentId, children }: BuildReferenceCapabilityProps) {
  const session = useOptionalMarkdownCanvasSession();
  const {
    openGraphReference,
    openTool,
    registerGraphReferenceBinding,
    registerProjectionCatalog,
  } = useAgentInteraction();
  const locationSearch = useSyncExternalStore(
    subscribeToLocationSearch,
    getLocationSearchSnapshot,
    () => "",
  );
  const lensParams = useMemo(
    () => readBuildGraphLensParams(locationSearch),
    [locationSearch],
  );
  const sharedGraphLens = useOptionalWorldGraphLens();
  const sharedProjection = useOptionalWorldGraphLensProjection();
  const sharedCampaignSelectionKey =
    sharedGraphLens?.lens.selectedCampaignIds.join(",") ?? "";

  const acceptedDocument = useMemo(() => {
    if (!documentId || !session || session.documentId !== documentId) return null;
    if (EMPTY_PUBLICATION_PHASES.has(session.phase)) return null;
    if (!session.record) return null;
    return {
      documentId: session.record.document_id,
      campaignId: session.record.campaign_id,
    };
  }, [
    documentId,
    session?.documentId,
    session?.phase,
    session?.record?.campaign_id,
    session?.record?.document_id,
  ]);

  const rawLens = useMemo(() => {
    if (!acceptedDocument) {
      return {
        status: "invalid" as const,
        reason: "Build graph lens requires an accepted document.",
      };
    }
    return resolveBuildGraphLens({
      documentId: acceptedDocument.documentId,
      documentCampaignId: acceptedDocument.campaignId,
      requestedCampaignId: lensParams.requestedCampaignId,
      requestedRevisionId: lensParams.requestedRevisionId,
    });
  }, [acceptedDocument, lensParams.requestedCampaignId, lensParams.requestedRevisionId]);

  const lens = useMemo(
    () =>
      resolveEffectiveBuildGraphLens(
        rawLens,
        sharedGraphLens,
        lensParams.requestedCampaignId ?? sharedGraphLens?.lens.selectedCampaignIds[0] ?? null,
      ),
    // sharedGraphLens context value churns on unrelated validation ticks; selection key is enough.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional sharedCampaignSelectionKey
    [lensParams.requestedCampaignId, rawLens, sharedCampaignSelectionKey],
  );

  const useSharedProjection = Boolean(
    sharedProjection
    && sharedGraphLens
    && sharedGraphLens.lens.selectedCampaignIds.length > 0
    && lens.status === "ready",
  );

  const documentIdentity = useMemo(
    () => ({
      documentId: acceptedDocument?.documentId ?? "",
      campaignId: acceptedDocument?.campaignId ?? "",
    }),
    [acceptedDocument?.campaignId, acceptedDocument?.documentId],
  );

  const localProjection = useBuildWorldGraphProjection({
    lens: useSharedProjection ? SHARED_NAV_PROJECTION_DISABLED_LENS : lens,
    documentIdentity,
  });

  const projection = useMemo(() => {
    if (!useSharedProjection || !sharedProjection) {
      return localProjection;
    }
    const derived = deriveApiLens(
      sharedGraphLens!.lens,
      lensParams.requestedCampaignId ?? sharedGraphLens!.lens.selectedCampaignIds[0],
    );
    const scopeCampaignId = derived?.campaignId ?? sharedGraphLens!.lens.selectedCampaignIds[0];
    const snapshot = sharedProjection.projection?.snapshot;
    const revisionMode = lens.status === "ready" && lens.revision.kind === "pinned" ? "pinned" : "head";
    const requestedRevisionId =
      lens.status === "ready" && lens.revision.kind === "pinned" ? lens.revision.revisionId : null;
    return {
      projection: sharedProjection.projection,
      state: sharedProjection.projectionState,
      error: sharedProjection.projectionError,
      requestedRevisionId,
      loadedRevisionId: snapshot?.revisionId ?? null,
      revisionMode,
      loadedIsHead: snapshot?.isHead === true,
      generation: localProjection.generation,
      loadKey: `shared:${scopeCampaignId}:${snapshot?.revisionId ?? "none"}`,
      items:
        sharedProjection.projectionState === "ready" && sharedProjection.projection
          ? adaptSharedProjectionSearchItems(sharedProjection.projection, scopeCampaignId)
          : EMPTY_SEARCH_ITEMS,
    };
  }, [
    lens,
    lensParams.requestedCampaignId,
    localProjection,
    sharedGraphLens,
    sharedProjection,
    useSharedProjection,
  ]);

  /** Live load key — updated every render so retained callbacks fail closed across lens transitions. */
  const liveLoadKeyRef = useRef(projection.loadKey);
  liveLoadKeyRef.current = projection.loadKey;
  /** Authorized only while coherent state is ready for the current load key. */
  const authorizedLoadKeyRef = useRef<string | null>(null);
  authorizedLoadKeyRef.current =
    projection.state === "ready" ? projection.loadKey : null;
  const projectionGenerationRef = useRef(projection.generation);
  projectionGenerationRef.current = projection.generation;
  const relationshipResolveGenerationRef = useRef<number | null>(null);
  const relationshipResolveLoadKeyRef = useRef<string | null>(null);

  const selectCampaign = useCallback((campaignId: string) => {
    if (typeof window === "undefined") return;
    const trimmed = campaignId.trim();
    const url = new URL(window.location.href);
    url.searchParams.set("campaign", trimmed);
    writeBuildLastCampaignId(trimmed);
    window.history.pushState({}, "", url.toString());
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, []);

  const viewExact = useCallback(
    (item: GraphReferenceSearchItem) => {
      const authorizedKey = authorizedLoadKeyRef.current;
      const liveKey = liveLoadKeyRef.current;
      if (!authorizedKey || authorizedKey !== liveKey) return;
      if (projection.state !== "ready") return;
      if (projection.loadKey !== liveKey) return;
      const canonical = projection.items.find((entry) => entry.nodeId === item.nodeId);
      if (!canonical) return;
      const graphScope = extractExactGraphReferenceScope(projection.projection);
      if (!graphScope) return;

      if (import.meta.env.VITEST) {
        buildViewExactTestSeam.lastGraphNodeId = canonical.nodeId;
        buildViewExactTestSeam.lastGraphScope = graphScope;
      }

      const resolution: GraphReferenceResolution = {
        kind: "resolved_graph",
        locator: `dmb-node:${canonical.nodeId}`,
        reference: canonical.reference,
        graphNodeId: canonical.nodeId,
        graphObject: buildGraphObjectCardFromNodeView(canonical.nodeView),
        graphScope,
        projectionState: projection.state,
        message: `Resolved graph node ${canonical.label}.`,
      };

      openGraphReference({
        resolution,
        projectionState: projection.state,
        glanceOnly: glanceOnlyForGraphReference(resolution),
      });
    },
    [openGraphReference, projection.items, projection.loadKey, projection.projection, projection.state],
  );

  const openGraphNodeFromChip = useCallback(
    (nodeId: string) => {
      const item = projection.items.find((entry) => entry.nodeId === nodeId);
      if (!item) return;
      viewExact(item);
    },
    [projection.items, viewExact],
  );

  const insertChip = useCallback(
    (attrs: RunbookReferenceAttrs) => {
      if (!session) return;
      if (!isEditorInteractive(session.phase)) return;
      insertMarkdownReference(session.editor, attrs);
    },
    [session],
  );

  const insertDisabled = !session?.editor || !isEditorInteractive(session.phase);

  const chipRuntime = useMemo<GraphNodeChipRuntimeValue>(() => {
    const nodeViews: Record<string, GraphProjectionNodeView> = {};
    for (const item of projection.items) {
      nodeViews[item.nodeId] = item.nodeView;
    }
    return {
      nodeViews,
      activeNodeId: null,
      onSelectNode: openGraphNodeFromChip,
      exactGraphScope: extractExactGraphReferenceScope(projection.projection),
    };
  }, [openGraphNodeFromChip, projection.items, projection.projection]);

  const referenceContext = useMemo<BuildReferenceContextBinding | null>(() => {
    if (!acceptedDocument) return null;
    return {
      schema: "dmb_build_reference_context_v1",
      documentId: acceptedDocument.documentId,
      documentCampaignId: acceptedDocument.campaignId,
      lens,
      projectionState: projection.state,
      projectionError: projection.error,
      requestedRevisionId: projection.requestedRevisionId,
      loadedRevisionId: projection.loadedRevisionId,
      loadedIsHead: projection.loadedIsHead,
      items: projection.items,
      selectCampaign,
      viewExact,
      insertChip,
      insertDisabled,
    };
  }, [
    acceptedDocument,
    insertChip,
    insertDisabled,
    lens,
    projection.error,
    projection.items,
    projection.loadedIsHead,
    projection.loadedRevisionId,
    projection.requestedRevisionId,
    projection.state,
    selectCampaign,
    viewExact,
  ]);

  /**
   * Build-local Save live lease. Effect cleanup marks the capability inactive;
   * the next effect setup restores liveness (StrictMode rehearsal cleanup must
   * not permanently kill Save). liveDocumentIdRef is committed only in the
   * effect so document replacement is event-safe — never mutated during render.
   * Retained document-A invokes no-op when unmounted or when the live document
   * no longer matches the bound identity (Canvas mountedRef alone is checked
   * only after prepare/commit begins).
   */
  const saveMountedRef = useRef(false);
  const liveDocumentIdRef = useRef<string | null>(null);
  useEffect(() => {
    saveMountedRef.current = true;
    liveDocumentIdRef.current = documentId;
    return () => {
      saveMountedRef.current = false;
      liveDocumentIdRef.current = null;
    };
  }, [documentId]);

  const saveDocument = useMemo(() => {
    const boundDocumentId = documentId;
    const boundSession = session;
    return async () => {
      if (!saveMountedRef.current) return;
      if (liveDocumentIdRef.current !== boundDocumentId) return;
      if (!boundDocumentId || !boundSession || boundSession.documentId !== boundDocumentId) return;
      if (EMPTY_PUBLICATION_PHASES.has(boundSession.phase)) return;
      if (!boundSession.record || boundSession.record.document_id !== boundDocumentId) return;
      if (!saveMountedRef.current) return;
      if (liveDocumentIdRef.current !== boundDocumentId) return;
      await boundSession.saveMarkdown();
    };
  }, [documentId, session]);

  const documentSave = useMemo(() => {
    if (!acceptedDocument || !session) return null;
    return {
      saveDisabled: session.saveDisabled,
      disabledReason: session.saveDisabled
        ? (session.statusLabel || "Save is unavailable for this document.")
        : undefined,
      save: () => saveDocument(),
    };
  }, [acceptedDocument, saveDocument, session]);

  const publication = useMemo(
    () =>
      buildBuildSurfaceInteractionPublication({
        documentId,
        acceptedDocument,
        referenceContext,
        documentSave,
      }),
    [acceptedDocument, documentId, documentSave, referenceContext],
  );

  usePublishSurfaceInteraction(publication);

  const catalogActive = Boolean(referenceContext && publication.tools.length > 0);

  useEffect(() => {
    if (!catalogActive) return undefined;

    const cleanups = [
      registerProjectionCatalog({
        projectionId: BUILD_REFERENCE_SEARCH_PROJECTION_ID,
        surfaceId: "build",
        kind: "tool",
        preferredSize: "wide",
        requiredBindingIds: [BUILD_REFERENCE_CONTEXT_BINDING_ID],
        render: ({ bindings }) => <BuildReferenceSearchProjection bindings={bindings} />,
      }),
      registerProjectionCatalog({
        projectionId: GRAPH_REFERENCE_PROJECTION_ID,
        surfaceId: "build",
        kind: "content",
        preferredSize: "wide",
        requiredBindingIds: [GRAPH_REFERENCE_RESOLUTION_BINDING_ID],
        render: ({ bindings, active }) => (
          <BuildReferenceObjectProjection
            bindings={bindings}
            glanceOnly={active.glanceOnly === true}
          />
        ),
      }),
    ];

    return () => {
      for (const cleanup of cleanups) {
        cleanup();
      }
    };
  }, [catalogActive, registerProjectionCatalog]);

  useEffect(() => {
    if (!catalogActive) return undefined;

    return registerGraphReferenceBinding({
      resolverState: projection.state,
      resolveRelationship: async (relationship) => {
        relationshipResolveGenerationRef.current = projectionGenerationRef.current;
        relationshipResolveLoadKeyRef.current = liveLoadKeyRef.current;
        return resolveBuildRelationshipTarget({
          relationship,
          projection: projection.projection,
          projectionState: projection.state,
        });
      },
      openResolvedReference: (resolution, state) => {
        const resolveKey = relationshipResolveLoadKeyRef.current;
        relationshipResolveLoadKeyRef.current = null;
        if (
          relationshipResolveGenerationRef.current !== projectionGenerationRef.current
          || !resolveKey
          || resolveKey !== liveLoadKeyRef.current
          || authorizedLoadKeyRef.current !== liveLoadKeyRef.current
        ) {
          relationshipResolveGenerationRef.current = null;
          return;
        }
        relationshipResolveGenerationRef.current = null;
        openGraphReference({
          resolution,
          projectionState: state ?? projection.state,
          glanceOnly: glanceOnlyForGraphReference(resolution),
        });
      },
      openTool,
    });
  }, [
    catalogActive,
    openGraphReference,
    openTool,
    projection.projection,
    projection.state,
    registerGraphReferenceBinding,
  ]);

  return (
    <GraphNodeChipRuntimeProvider value={chipRuntime}>
      {children ?? null}
    </GraphNodeChipRuntimeProvider>
  );
}
