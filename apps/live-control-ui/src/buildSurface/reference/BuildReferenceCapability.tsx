import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";

import { useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphObjectRelationshipViewModel } from "../../graphObjectCard";
import {
  GraphNodeChipRuntimeProvider,
} from "../../graphReference/GraphNodeChipRuntime";
import type { GraphNodeChipRuntimeValue } from "../../graphReference/types";
import {
  GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
} from "../../graphReference/projectionBindings";
import { resolveGraphReference, extractExactGraphReferenceScope } from "../../graphReference/resolveGraphReference";
import {
  exactScopeFromReferenceAttrs,
  exactScopesEqual,
} from "../../graphReference/scopedGraphReference";
import type {
  ExactGraphReferenceScope,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
  GraphReferenceSearchItem,
} from "../../graphReference/types";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import {
  GRAPH_NODE_REF_TYPE,
  graphScopePresence,
  isSupportedRunbookReference,
  normalizeRunbookReferenceAttrs,
  type RunbookReferenceAttrs,
} from "../../tiptap/references/runbookReferences";
import type { GraphProjectionNodeView } from "../../api/types";
import { adaptWorldGraphNodeView } from "../../worldGraph/worldGraphNodeViewAdapter";
import { usePublishSurfaceInteraction } from "../../agentInteraction/usePublishSurfaceInteraction";
import { useOptionalMarkdownCanvasSession } from "../../markdownCanvas/MarkdownCanvasSession";
import type { WorkspaceDocumentAuthoringPhase } from "../../workspaceDocument/workspaceDocumentAuthoringMachine";
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
import { resolveBuildGraphLens } from "./resolveBuildGraphLens";
import { useBuildWorldGraphProjection } from "./useBuildWorldGraphProjection";

const EMPTY_PUBLICATION_PHASES: ReadonlySet<WorkspaceDocumentAuthoringPhase> = new Set([
  "unloaded",
  "loading",
  "load_error",
  "conflict",
]);

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

type PendingActivation = {
  documentId: string;
  attrs: RunbookReferenceAttrs;
  scope: ExactGraphReferenceScope;
  generation: number;
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
}

export function BuildReferenceCapability({ documentId }: BuildReferenceCapabilityProps) {
  const session = useOptionalMarkdownCanvasSession();
  const [insertionError, setInsertionError] = useState<string | null>(null);
  const [pendingActivation, setPendingActivation] = useState<PendingActivation | null>(null);
  const {
    openGraphReference,
    openTool,
    registerGraphReferenceBinding,
    registerProjectionCatalog,
    graphReferenceBinding,
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

  const acceptedDocument = useMemo(() => {
    if (!documentId || !session || session.documentId !== documentId) return null;
    if (EMPTY_PUBLICATION_PHASES.has(session.phase)) return null;
    if (!session.record) return null;
    return {
      documentId: session.record.document_id,
      campaignId: session.record.campaign_id,
    };
  }, [documentId, session]);

  const lens = useMemo(() => {
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

  const projection = useBuildWorldGraphProjection({
    lens,
    documentIdentity: {
      documentId: acceptedDocument?.documentId ?? "",
      campaignId: acceptedDocument?.campaignId ?? "",
    },
  });

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
  const pendingGenerationRef = useRef(0);

  const saveMountedRef = useRef(false);
  const liveDocumentIdRef = useRef<string | null>(null);
  useEffect(() => {
    saveMountedRef.current = true;
    liveDocumentIdRef.current = documentId;
    setPendingActivation(null);
    pendingGenerationRef.current += 1;
    setInsertionError(null);
    return () => {
      saveMountedRef.current = false;
      liveDocumentIdRef.current = null;
      setPendingActivation(null);
      pendingGenerationRef.current += 1;
    };
  }, [documentId]);

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

      openGraphReference({
        resolution: {
          kind: "resolved_graph",
          locator: `dmb-node:${canonical.nodeId}`,
          reference: canonical.reference,
          graphNodeId: canonical.nodeId,
          graphObject: buildGraphObjectCardFromNodeView(canonical.nodeView),
          graphScope,
          projectionState: projection.state,
          message: `Resolved graph node ${canonical.label}.`,
        },
        projectionState: projection.state,
      });
    },
    [openGraphReference, projection.items, projection.loadKey, projection.projection, projection.state],
  );

  const openResolvedGraphNode = useCallback(
    (input: {
      nodeId: string;
      reference: RunbookReferenceAttrs;
      graphScope: ExactGraphReferenceScope;
    }) => {
      const authorizedKey = authorizedLoadKeyRef.current;
      const liveKey = liveLoadKeyRef.current;
      if (!authorizedKey || authorizedKey !== liveKey) return;
      if (projection.state !== "ready") return;
      const canonical = projection.items.find((entry) => entry.nodeId === input.nodeId);
      if (!canonical) return;

      openGraphReference({
        resolution: {
          kind: "resolved_graph",
          locator: `dmb-node:${input.nodeId}`,
          reference: input.reference,
          graphNodeId: input.nodeId,
          graphObject: buildGraphObjectCardFromNodeView(canonical.nodeView),
          graphScope: input.graphScope,
          projectionState: projection.state,
          message: `Resolved graph node ${canonical.label}.`,
        },
        projectionState: projection.state,
      });
    },
    [openGraphReference, projection.items, projection.state],
  );

  const insertExact = useCallback(
    async (item: GraphReferenceSearchItem) => {
      if (!saveMountedRef.current) return;
      if (liveDocumentIdRef.current !== documentId) return;

      const authorizedKey = authorizedLoadKeyRef.current;
      const liveKey = liveLoadKeyRef.current;
      if (!authorizedKey || authorizedKey !== liveKey) {
        setInsertionError("Graph projection is stale; refresh search and try again.");
        return;
      }
      if (projection.state !== "ready") return;

      const canonical = projection.items.find((entry) => entry.nodeId === item.nodeId);
      if (!canonical) {
        setInsertionError("Selected node is no longer in the current projection.");
        return;
      }

      const projectionScope = extractExactGraphReferenceScope(projection.projection);
      const itemScope = exactScopeFromReferenceAttrs(canonical.reference);
      if (!projectionScope || !itemScope || !exactScopesEqual(itemScope, projectionScope)) {
        setInsertionError("Reference scope does not match the current projection.");
        return;
      }

      if (!session || session.documentId !== documentId) return;
      const admission = session.lookupAdmission("editable");
      if (!admission.ok) {
        setInsertionError(
          admission.detail?.trim() || "Unlock editing to insert chips into the board.",
        );
        return;
      }

      const result = await session.insertReference(canonical.reference);
      if (!saveMountedRef.current || liveDocumentIdRef.current !== documentId) return;
      if (!result.ok) {
        setInsertionError(result.reason?.trim() || "Could not insert reference.");
        return;
      }
      setInsertionError(null);
    },
    [documentId, projection.items, projection.projection, projection.state, session],
  );

  const activateChip = useCallback(
    (rawAttrs: RunbookReferenceAttrs) => {
      if (!saveMountedRef.current) return;
      if (!acceptedDocument || liveDocumentIdRef.current !== acceptedDocument.documentId) return;

      const normalized = normalizeRunbookReferenceAttrs(rawAttrs);
      if (!isSupportedRunbookReference(normalized)) return;
      if (normalized.refType !== GRAPH_NODE_REF_TYPE) return;

      const scopePresence = graphScopePresence(normalized);
      if (scopePresence === "partial") return;

      const storedScope = exactScopeFromReferenceAttrs(normalized);
      const nodeId = normalized.refId;

      if (scopePresence === "none") {
        const authorizedKey = authorizedLoadKeyRef.current;
        const liveKey = liveLoadKeyRef.current;
        if (!authorizedKey || authorizedKey !== liveKey || projection.state !== "ready") return;

        const currentScope = extractExactGraphReferenceScope(projection.projection);
        if (!currentScope) return;

        const canonical = projection.items.find((entry) => entry.nodeId === nodeId);
        if (!canonical) {
          openGraphReference({
            resolution: {
              kind: "unresolved",
              locator: `dmb-node:${nodeId}`,
              reference: normalized,
              projectionState: projection.state,
              message: `Graph node "${nodeId}" was not found in the loaded World Graph projection.`,
            },
            projectionState: projection.state,
          });
          return;
        }

        openResolvedGraphNode({
          nodeId,
          reference: normalized,
          graphScope: currentScope,
        });
        return;
      }

      if (!storedScope) return;

      const currentScope = extractExactGraphReferenceScope(projection.projection);
      const authorizedKey = authorizedLoadKeyRef.current;
      const liveKey = liveLoadKeyRef.current;

      if (
        projection.state === "ready"
        && authorizedKey === liveKey
        && currentScope
        && exactScopesEqual(storedScope, currentScope)
      ) {
        const canonical = projection.items.find((entry) => entry.nodeId === nodeId);
        if (!canonical) {
          openGraphReference({
            resolution: {
              kind: "unresolved",
              locator: `dmb-node:${nodeId}`,
              reference: normalized,
              projectionState: projection.state,
              message: `Graph node "${nodeId}" was not found in the loaded World Graph projection.`,
            },
            projectionState: projection.state,
          });
          return;
        }

        openResolvedGraphNode({
          nodeId,
          reference: normalized,
          graphScope: storedScope,
        });
        return;
      }

      const pinLens = resolveBuildGraphLens({
        documentId: acceptedDocument.documentId,
        documentCampaignId: acceptedDocument.campaignId,
        requestedCampaignId: storedScope.campaignId,
        requestedRevisionId: storedScope.revisionId,
      });
      if (pinLens.status === "invalid") return;

      if (typeof window === "undefined") return;
      const url = new URL(window.location.href);
      url.searchParams.set("campaign", storedScope.campaignId);
      url.searchParams.set("graphRevision", storedScope.revisionId);
      window.history.replaceState({}, "", url.toString());
      window.dispatchEvent(new PopStateEvent("popstate"));

      pendingGenerationRef.current += 1;
      setPendingActivation({
        documentId: acceptedDocument.documentId,
        attrs: normalized,
        scope: storedScope,
        generation: pendingGenerationRef.current,
      });
    },
    [
      acceptedDocument,
      openGraphReference,
      openResolvedGraphNode,
      projection.items,
      projection.projection,
      projection.state,
    ],
  );

  useEffect(() => {
    const pending = pendingActivation;
    if (!pending) return;
    if (!graphReferenceBinding) return;
    if (liveDocumentIdRef.current !== pending.documentId) {
      setPendingActivation(null);
      return;
    }

    if (projection.state === "error" || projection.state === "unavailable") {
      setPendingActivation(null);
      return;
    }

    if (projection.state !== "ready") return;

    const loadedScope = extractExactGraphReferenceScope(projection.projection);
    const lensMatchesPending =
      lens.status === "ready"
      && lens.campaignId === pending.scope.campaignId
      && (
        lens.revision.kind === "pinned"
          ? lens.revision.revisionId === pending.scope.revisionId
          : pending.scope.revisionId === projection.loadedRevisionId
      );

    if (!loadedScope || !exactScopesEqual(loadedScope, pending.scope)) {
      if (
        lensMatchesPending
        && projection.loadedRevisionId === pending.scope.revisionId
      ) {
        setPendingActivation(null);
      }
      return;
    }

    const nodeId = pending.attrs.refId;
    const canonical = projection.items.find((entry) => entry.nodeId === nodeId);
    if (!canonical) {
      setPendingActivation(null);
      openGraphReference({
        resolution: {
          kind: "unresolved",
          locator: `dmb-node:${nodeId}`,
          reference: pending.attrs,
          projectionState: projection.state,
          message: `Graph node "${nodeId}" was not found in the loaded World Graph projection.`,
        },
        projectionState: projection.state,
      });
      return;
    }

    const pendingSnapshot = pending;
    queueMicrotask(() => {
      if (liveDocumentIdRef.current !== pendingSnapshot.documentId) return;
      openGraphReference({
        resolution: {
          kind: "resolved_graph",
          locator: `dmb-node:${nodeId}`,
          reference: pendingSnapshot.attrs,
          graphNodeId: nodeId,
          graphObject: buildGraphObjectCardFromNodeView(canonical.nodeView),
          graphScope: pendingSnapshot.scope,
          projectionState: projection.state,
          message: `Resolved graph node ${canonical.label}.`,
        },
        projectionState: projection.state,
      });
      setPendingActivation((current) => (
        current?.generation === pendingSnapshot.generation ? null : current
      ));
    });
  }, [
    graphReferenceBinding,
    lens,
    openGraphReference,
    pendingActivation,
    projection.items,
    projection.loadedRevisionId,
    projection.projection,
    projection.state,
  ]);

  const insertAvailable = useMemo(() => {
    if (!acceptedDocument || !session) return false;
    if (session.documentId !== acceptedDocument.documentId) return false;
    if (EMPTY_PUBLICATION_PHASES.has(session.phase)) return false;
    const admission = session.lookupAdmission("editable");
    if (!admission.ok) return false;
    if (projection.state !== "ready") return false;
    if (!extractExactGraphReferenceScope(projection.projection)) return false;
    return authorizedLoadKeyRef.current === liveLoadKeyRef.current;
  }, [acceptedDocument, projection.projection, projection.state, session]);

  const insertDisabledReason = useMemo(() => {
    if (insertAvailable) return undefined;
    if (!acceptedDocument || !session) return "Insert is unavailable for this document.";
    const admission = session.lookupAdmission("editable");
    if (!admission.ok) {
      return admission.detail?.trim() || "Unlock editing to insert chips into the board.";
    }
    if (projection.state !== "ready") return "World Graph projection is not ready.";
    if (!extractExactGraphReferenceScope(projection.projection)) {
      return "World Graph projection lacks exact scope.";
    }
    return "Insert is unavailable for the current graph lens.";
  }, [acceptedDocument, insertAvailable, projection.projection, projection.state, session]);

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
      insertAvailable,
      insertDisabledReason,
      insertExact,
      insertionError,
    };
  }, [
    acceptedDocument,
    insertAvailable,
    insertDisabledReason,
    insertExact,
    insertionError,
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

  const chipRuntime = useMemo<GraphNodeChipRuntimeValue>(() => {
    if (!catalogActive || !acceptedDocument) {
      return {
        nodeViews: {},
        activeNodeId: null,
        onSelectNode: () => undefined,
      };
    }

    const nodeViews: Record<string, GraphProjectionNodeView> = {};
    if (projection.state === "ready" && projection.projection) {
      for (const node of projection.projection.nodes) {
        nodeViews[node.nodeId] = adaptWorldGraphNodeView(node);
      }
    }

    return {
      nodeViews,
      activeNodeId: null,
      onSelectNode: (nodeId: string) => {
        activateChip({
          kind: "ref",
          refType: GRAPH_NODE_REF_TYPE,
          refId: nodeId,
          label: nodeViews[nodeId]?.label ?? nodeId,
        });
      },
      onSelectReference: (attrs: RunbookReferenceAttrs) => {
        activateChip(attrs);
      },
    };
  }, [acceptedDocument, activateChip, catalogActive, projection.projection, projection.state]);

  if (!catalogActive) {
    return null;
  }

  return (
    <GraphNodeChipRuntimeProvider value={chipRuntime}>
      {null}
    </GraphNodeChipRuntimeProvider>
  );
}
