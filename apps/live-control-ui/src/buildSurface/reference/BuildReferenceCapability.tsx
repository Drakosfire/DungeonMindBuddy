import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useSyncExternalStore,
  type ReactNode,
} from "react";

import type { Editor } from "@tiptap/core";
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
import { referenceFromGraphNode } from "../../graphReference/referenceFromGraphNode";
import { resolveGraphReference, extractExactGraphReferenceScope } from "../../graphReference/resolveGraphReference";
import type {
  ExactGraphReferenceScope,
  GraphNodeChipRuntimeValue,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
} from "../../graphReference/types";
import type { GraphProjectionNodeView, WorldGraphProjection } from "../../api/types";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import { adaptWorldGraphNodeView } from "../../worldGraph/worldGraphNodeViewAdapter";
import { useOptionalWorldGraphLens } from "../../graphLens/WorldGraphLensContext";
import {
  useOptionalWorldGraphLensInformationChannel,
  useOptionalWorldGraphLensProjection,
} from "../../graphLens/useWorldGraphLensProjection";
import { WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID } from "../../chrome/appChromeConfig";
import { usePublishSurfaceInteraction } from "../../agentInteraction/usePublishSurfaceInteraction";
import { insertMarkdownReference } from "../../graphReference/insertMarkdownReference";
import { useOptionalMarkdownCanvasSession } from "../../markdownCanvas/MarkdownCanvasSession";
import type { WorkspaceDocumentAuthoringPhase } from "../../workspaceDocument/workspaceDocumentAuthoringMachine";
import { isEditorInteractive } from "../../workspaceDocument/workspaceDocumentAuthoringMachine";
import { admitBuildObjectInsert } from "../../worldGraph/worldGraphSurfaceContext";
import { writeBuildLastCampaignId } from "../buildBareEntryCampaign";
import {
  buildBuildSurfaceInteractionPublication,
  type BuildReferenceContextBinding,
} from "./buildBuildSurfaceInteractionPublication";
import {
  BUILD_REFERENCE_CONTEXT_BINDING_ID,
  BUILD_REFERENCE_SEARCH_PROJECTION_ID,
  BUILD_WORLD_GRAPH_INFORMATION_CHANNEL_BINDING_ID,
} from "./buildReferenceIds";
import { BuildReferenceObjectProjection } from "./BuildReferenceObjectProjection";
import { BuildReferenceSearchProjection } from "./BuildReferenceSearchProjection";
import { resolveBuildFindGraphLens } from "./resolveBuildGraphLens";
import { useBuildWorldGraphProjection } from "./useBuildWorldGraphProjection";
import {
  BUILD_WORLD_GRAPH_FALLBACK_SNAPSHOT,
  searchItemsFromWorldGraphState,
} from "./buildWorldGraphSurfaceInformation";
import type {
  SurfaceInformationChannel,
  SurfaceInformationSnapshot,
  SurfaceInformationState,
} from "../../surfaceInformation";

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

type BuildEditorGate = {
  editor: Editor | null;
  documentId: string | null;
  documentCampaignId: string | null;
  editorInteractive: boolean;
};

const CLOSED_BUILD_EDITOR_GATE: BuildEditorGate = {
  editor: null,
  documentId: null,
  documentCampaignId: null,
  editorInteractive: false,
};

function isBuildEditorLive(gate: BuildEditorGate): boolean {
  return Boolean(gate.editor && gate.documentId && gate.editorInteractive);
}

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

function graphReferenceStateFromInformation(
  state: SurfaceInformationState<WorldGraphProjection>,
): GraphReferenceProjectionState {
  if (state.status === "loading") return "loading";
  if (state.status === "unavailable") return "unavailable";
  if (state.status === "integrity_error" || state.status === "stale") return "error";
  return "ready";
}

function liveWorldGraphState(
  channel: SurfaceInformationChannel<WorldGraphProjection> | null,
): SurfaceInformationState<WorldGraphProjection> | null {
  return channel?.getSnapshot().state ?? null;
}

async function resolveBuildRelationshipTarget(input: {
  relationship: GraphObjectRelationshipViewModel;
  channel: SurfaceInformationChannel<WorldGraphProjection> | null;
}): Promise<GraphReferenceResolution> {
  const label = String(input.relationship.label || "").trim() || "Related object";
  const targetId = String(input.relationship.targetId || "").trim() || null;
  const targetKind = String(input.relationship.targetKind || "").trim() || null;
  const locator = targetId ? `dmb-node:${targetId}` : label;
  const reference = targetKind && targetId
    ? { kind: "ref" as const, refType: targetKind, refId: targetId, label }
    : null;
  const information = liveWorldGraphState(input.channel);
  if (!information) {
    return {
      kind: "unresolved",
      locator,
      reference,
      projectionState: "unavailable",
      message: "World Graph information channel is not current; relationship resolution unavailable.",
    };
  }
  const projectionState = graphReferenceStateFromInformation(information);
  const projection = information.status === "ready" ? information.value : null;

  if (projectionState === "loading") {
    return {
      kind: "unresolved",
      locator,
      reference,
      projectionState,
      message: "World Graph projection is loading; relationship resolution deferred.",
    };
  }

  if (projectionState === "error") {
    return {
      kind: "error",
      locator,
      reference,
      projectionState,
      message: "World Graph projection failed; relationship resolution unavailable.",
    };
  }

  if (information.status === "empty") {
    return {
      kind: "unresolved",
      locator,
      reference,
      projectionState: "ready",
      message: `Could not resolve related object "${label}" from the loaded World Graph projection.`,
    };
  }

  if (projectionState === "ready" && !projection) {
    return {
      kind: "error",
      locator,
      reference,
      projectionState,
      message:
        "World Graph projection marked ready but no projection was supplied; relationship resolution unavailable.",
    };
  }

  if (projectionState === "unavailable") {
    return {
      kind: "unresolved",
      locator,
      reference,
      projectionState,
      message: "World Graph is unavailable; relationship resolution unavailable.",
    };
  }

  if (targetId && projection) {
    const exactNode = projection.nodes.find((node) => node.nodeId === targetId) ?? null;
    if (exactNode) {
      const graphScope = extractExactGraphReferenceScope(projection);
      if (!graphScope) {
        return {
          kind: "error",
          locator,
          reference,
          projectionState,
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
        projectionState,
        message: `Resolved graph node ${exactNode.label}.`,
      };
    }

    return {
      kind: "unresolved",
      locator,
      reference,
      projectionState,
      message: `Could not resolve related object "${label}" from the loaded World Graph projection.`,
    };
  }

  if (projection) {
    return resolveGraphReference({
      locator: label,
      label,
      refType: targetKind,
      projection,
      projectionState,
    });
  }

  return {
    kind: "unresolved",
    locator,
    reference,
    projectionState,
    message: `Could not resolve related object "${label}" from graph memory.`,
  };
}

function fallbackSubscribe(): () => void {
  return () => undefined;
}

function getFallbackSnapshot(): SurfaceInformationSnapshot<WorldGraphProjection> {
  return BUILD_WORLD_GRAPH_FALLBACK_SNAPSHOT;
}

function BuildWorldGraphChipRuntime({
  channel,
  onSelectNode,
  children,
}: {
  channel: SurfaceInformationChannel<WorldGraphProjection> | null;
  onSelectNode: (nodeId: string) => void;
  children: ReactNode;
}) {
  const snapshot = useSyncExternalStore(
    channel?.subscribe ?? fallbackSubscribe,
    channel?.getSnapshot ?? getFallbackSnapshot,
    channel?.getSnapshot ?? getFallbackSnapshot,
  ) as SurfaceInformationSnapshot<WorldGraphProjection>;
  const chipRuntime = useMemo<GraphNodeChipRuntimeValue>(() => {
    const items = searchItemsFromWorldGraphState(snapshot.state);
    const nodeViews: Record<string, GraphProjectionNodeView> = {};
    for (const item of items) {
      nodeViews[item.nodeId] = item.nodeView;
    }
    const projection =
      snapshot.state.status === "ready" || snapshot.state.status === "stale"
        ? snapshot.state.value
        : null;
    return {
      nodeViews,
      activeNodeId: null,
      onSelectNode,
      exactGraphScope: projection ? extractExactGraphReferenceScope(projection) : null,
    };
  }, [onSelectNode, snapshot]);
  return (
    <GraphNodeChipRuntimeProvider value={chipRuntime}>
      {children}
    </GraphNodeChipRuntimeProvider>
  );
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
  const sharedChannel = useOptionalWorldGraphLensInformationChannel();
  const sharedLensIdentityKey = useMemo(() => {
    if (!sharedGraphLens) return "";
    const { selectedCampaignIds, focus } = sharedGraphLens.lens;
    return JSON.stringify([
      selectedCampaignIds,
      focus?.campaignId ?? null,
      focus?.sessionNumber ?? null,
    ]);
  }, [sharedGraphLens]);

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

  const lens = useMemo(() => {
    if (!acceptedDocument) {
      return {
        status: "invalid" as const,
        reason: "Build graph lens requires an accepted document.",
      };
    }
    return resolveBuildFindGraphLens({
      documentId: acceptedDocument.documentId,
      documentCampaignId: acceptedDocument.campaignId,
      requestedCampaignId: lensParams.requestedCampaignId,
      requestedRevisionId: lensParams.requestedRevisionId,
      sharedLens: sharedGraphLens?.lens ?? null,
      sharedRequest: sharedProjection?.request ?? null,
      defaultCampaignId: WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional shared identity keys
  }, [
    acceptedDocument,
    lensParams.requestedCampaignId,
    lensParams.requestedRevisionId,
    sharedLensIdentityKey,
    sharedProjection?.requestKey,
  ]);

  const documentIdentity = useMemo(
    () => ({
      documentId: acceptedDocument?.documentId ?? "",
      campaignId: acceptedDocument?.campaignId ?? "",
    }),
    [acceptedDocument?.campaignId, acceptedDocument?.documentId],
  );

  const graphInformation = useBuildWorldGraphProjection({
    lens,
    documentIdentity,
    sharedProjection,
    sharedChannel,
  });

  const editorGateRef = useRef<BuildEditorGate>(CLOSED_BUILD_EDITOR_GATE);
  const liveChannelRef = useRef<SurfaceInformationChannel<WorldGraphProjection> | null>(null);

  useLayoutEffect(() => {
    editorGateRef.current = {
      editor: session?.editor ?? null,
      documentId: acceptedDocument?.documentId ?? null,
      documentCampaignId: acceptedDocument?.campaignId ?? null,
      editorInteractive: session ? isEditorInteractive(session.phase) : false,
    };
    return () => {
      editorGateRef.current = CLOSED_BUILD_EDITOR_GATE;
    };
  }, [
    acceptedDocument?.campaignId,
    acceptedDocument?.documentId,
    session,
    session?.editor,
    session?.phase,
  ]);

  useLayoutEffect(() => {
    liveChannelRef.current = graphInformation.channel;
    return () => {
      liveChannelRef.current = null;
    };
  }, [graphInformation.channel]);

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
    (nodeId: string) => {
      const channel = liveChannelRef.current;
      if (!channel) return;
      const state = channel.getSnapshot().state;
      if (state.status !== "ready") return;
      const trimmedNodeId = nodeId.trim();
      if (!trimmedNodeId) return;
      const exactNode = state.value.nodes.find((node) => node.nodeId === trimmedNodeId);
      if (!exactNode) return;
      const graphScope = extractExactGraphReferenceScope(state.value);
      if (!graphScope) return;
      const nodeView = adaptWorldGraphNodeView(exactNode);

      if (import.meta.env.VITEST) {
        buildViewExactTestSeam.lastGraphNodeId = exactNode.nodeId;
        buildViewExactTestSeam.lastGraphScope = graphScope;
      }

      const resolution: GraphReferenceResolution = {
        kind: "resolved_graph",
        locator: `dmb-node:${exactNode.nodeId}`,
        reference: referenceFromGraphNode(nodeView),
        graphNodeId: exactNode.nodeId,
        graphObject: buildGraphObjectCardFromNodeView(nodeView),
        graphScope,
        projectionState: "ready",
        message: `Resolved graph node ${nodeView.label}.`,
      };

      openGraphReference({
        resolution,
        projectionState: "ready",
        glanceOnly: glanceOnlyForGraphReference(resolution),
      });
    },
    [openGraphReference],
  );

  const insertChip = useCallback((nodeId: string) => {
    const gate = editorGateRef.current;
    if (!isBuildEditorLive(gate) || gate.editor == null) return;
    const channel = liveChannelRef.current;
    if (!channel) return;
    const state = channel.getSnapshot().state;
    if (state.status !== "ready") return;
    const trimmedNodeId = nodeId.trim();
    if (!trimmedNodeId) return;
    const exactNode = state.value.nodes.find((node) => node.nodeId === trimmedNodeId);
    if (!exactNode) return;
    const nodeView = adaptWorldGraphNodeView(exactNode);
    const admission = admitBuildObjectInsert({
      documentCampaignId: gate.documentCampaignId ?? undefined,
      objectCampaignScope: nodeView.campaign_scope,
    });
    if (!admission.ok) return;
    insertMarkdownReference(gate.editor, referenceFromGraphNode(nodeView));
  }, []);

  const editorInsertDisabled =
    !session?.editor
    || !isEditorInteractive(session.phase)
    || lens.status !== "ready";

  const referenceContext = useMemo<BuildReferenceContextBinding | null>(() => {
    if (!acceptedDocument) return null;
    return {
      schema: "dmb_build_reference_context_v2",
      documentId: acceptedDocument.documentId,
      documentCampaignId: acceptedDocument.campaignId,
      lens,
      selectCampaign,
      viewExact,
      insertChip,
      editorInsertDisabled,
    };
  }, [
    acceptedDocument,
    editorInsertDisabled,
    insertChip,
    lens,
    selectCampaign,
    viewExact,
  ]);

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
        worldGraphChannel: graphInformation.channel,
        documentSave,
      }),
    [acceptedDocument, documentId, documentSave, graphInformation.channel, referenceContext],
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
        requiredBindingIds: [
          BUILD_REFERENCE_CONTEXT_BINDING_ID,
          BUILD_WORLD_GRAPH_INFORMATION_CHANNEL_BINDING_ID,
        ],
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
      resolverState: graphInformation.channel ? "ready" : "unavailable",
      resolveRelationship: async (relationship) =>
        resolveBuildRelationshipTarget({
          relationship,
          channel: liveChannelRef.current,
        }),
      openResolvedReference: (resolution, state) => {
        const channel = liveChannelRef.current;
        if (!channel) return;
        const current = channel.getSnapshot().state;
        if (current.status !== "ready") return;
        openGraphReference({
          resolution,
          projectionState: state ?? graphReferenceStateFromInformation(current),
          glanceOnly: glanceOnlyForGraphReference(resolution),
        });
      },
      openTool,
    });
  }, [
    catalogActive,
    graphInformation.channel,
    openGraphReference,
    openTool,
    registerGraphReferenceBinding,
  ]);

  return (
    <BuildWorldGraphChipRuntime
      channel={graphInformation.channel}
      onSelectNode={viewExact}
    >
      {children ?? null}
    </BuildWorldGraphChipRuntime>
  );
}
