import { useCallback, useEffect, useMemo, useRef, useSyncExternalStore } from "react";

import { useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphObjectRelationshipViewModel } from "../../graphObjectCard";
import {
  GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
} from "../../graphReference/projectionBindings";
import { resolveGraphReference, extractExactGraphReferenceScope } from "../../graphReference/resolveGraphReference";
import type {
  GraphReferenceProjectionState,
  GraphReferenceResolution,
  GraphReferenceSearchItem,
} from "../../graphReference/types";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import { adaptWorldGraphNodeView } from "../../worldGraph/worldGraphNodeViewAdapter";
import { usePublishSurfaceInteraction } from "../../agentInteraction/usePublishSurfaceInteraction";
import { useOptionalMarkdownCanvasSession } from "../../markdownCanvas/MarkdownCanvasSession";
import type { WorkspaceDocumentAuthoringPhase } from "../../workspaceDocument/workspaceDocumentAuthoringMachine";
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

  const selectCampaign = useCallback((campaignId: string) => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    url.searchParams.set("campaign", campaignId.trim());
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
    };
  }, [
    acceptedDocument,
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

  const saveDocument = useCallback(async () => {
    if (!documentId || !session || session.documentId !== documentId) return;
    if (EMPTY_PUBLICATION_PHASES.has(session.phase)) return;
    if (!session.record || session.record.document_id !== documentId) return;
    await session.saveMarkdown();
  }, [documentId, session]);

  const documentSave = useMemo(() => {
    if (!acceptedDocument || !session) return null;
    return {
      saveDisabled: session.saveDisabled,
      disabledReason: session.saveDisabled
        ? (session.statusLabel || "Save is unavailable for this document.")
        : undefined,
      save: () => {
        void saveDocument();
      },
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

  return null;
}
