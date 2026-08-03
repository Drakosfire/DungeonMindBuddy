import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { getRecapArtifacts } from "../../api/liveApi";
import { useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import {
  sameProjectionSurfaceIdentity,
  type ProjectionSurfaceIdentity,
} from "../../agentInteraction/projectionSurfacePublication";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import { ProjectionHost } from "../../surfaceInteraction/projection/ProjectionHost";
import { useProjection } from "./projectionContext";
import {
  filterNumericRecapArtifactRecords,
  sortRecapArtifactRecords,
} from "../graphPreview/recapSessionLabels";
import {
  GRAPH_REFERENCE_BINDING_ID,
  GRAPH_REFERENCE_PROJECTION_STATE_BINDING_ID,
  GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
  GRAPH_REVIEW_DIAGNOSTICS_BINDING_ID,
  PLAN_CONTEXT_BINDING_ID,
  PLAN_SURFACE_CONFIG_BINDING_ID,
} from "./projectionBindings";
import { IngestProjectionCatalogRegistration } from "./IngestProjectionCatalogRegistration";
import { PlanProjectionCatalogRegistration } from "./PlanProjectionCatalogRegistration";

function requestedToolFromLocation(): string | null {
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("tool");
  if (fromQuery) return fromQuery;
  const hash = window.location.hash.replace(/^#/, "");
  return hash.startsWith("tool=") ? hash.slice("tool=".length) : hash || null;
}

function requestedSessionFromLocation(): string | null {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get("session")?.trim() || null;
}

const SESSION_AWARE_TOOLS = new Set([
  "ingest-recap",
  "recap",
  "graph-preview",
  "graph-gold-review",
  "party-registry",
]);

/**
 * Temporary Plan-owned projection host policy adapter (BLD-SIH-03a/03b).
 * Owns URL/session inference and stale identity checks; renderer selection
 * is explicit via lease-scoped catalog registrations. Delete when Plan
 * recomposition lands a native publication path after BLD-SIH-06.
 */
export function LegacyProjectionHostAdapter() {
  const { projectionSurface, surfaceInteractionPublication } = useAgentInteraction();
  const {
    active,
    activeGraphReference,
    close,
    expandContent,
    openTool,
    graphReferenceProjectionState,
    graphReferenceBinding,
    graphReviewDiagnosticsPayload,
    resolveProjectionCatalog,
  } = useProjection();

  const config = projectionSurface?.publication.config ?? null;
  const projectionsEnabled = projectionSurface?.projectionsEnabled ?? false;

  const toolDescriptors = useMemo(
    () => (surfaceInteractionPublication?.projections ?? []).filter((entry) => entry.kind === "tool"),
    [surfaceInteractionPublication?.projections],
  );

  if (!config || !projectionsEnabled || config.tools.length === 0 || !config.context) {
    return null;
  }

  return (
    <>
      {config.id === "plan" ? (
        <PlanProjectionCatalogRegistration
          surfaceId={config.id}
          toolDescriptors={toolDescriptors}
        />
      ) : null}
      {config.id === "ingest" ? (
        <IngestProjectionCatalogRegistration
          surfaceId={config.id}
          toolDescriptors={toolDescriptors}
        />
      ) : null}
      <LegacyProjectionHostAdapterInner
        surfaceIdentity={projectionSurface!.publication.identity}
        config={config}
        active={active}
        activeGraphReference={activeGraphReference}
        close={close}
        expandContent={expandContent}
        openTool={openTool}
        graphReferenceProjectionState={graphReferenceProjectionState}
        graphReferenceBinding={graphReferenceBinding}
        graphReviewDiagnosticsPayload={graphReviewDiagnosticsPayload}
        resolveProjectionCatalog={resolveProjectionCatalog}
      />
    </>
  );
}

interface LegacyProjectionHostAdapterInnerProps {
  surfaceIdentity: ProjectionSurfaceIdentity;
  config: NonNullable<ReturnType<typeof useAgentInteraction>["projectionSurface"]>["publication"]["config"];
  active: ReturnType<typeof useProjection>["active"];
  activeGraphReference: ReturnType<typeof useProjection>["activeGraphReference"];
  close: () => void;
  expandContent: () => void;
  openTool: (toolId: string) => void;
  graphReferenceProjectionState: ReturnType<typeof useProjection>["graphReferenceProjectionState"];
  graphReferenceBinding: ReturnType<typeof useProjection>["graphReferenceBinding"];
  graphReviewDiagnosticsPayload: ReturnType<typeof useProjection>["graphReviewDiagnosticsPayload"];
  resolveProjectionCatalog: ReturnType<typeof useProjection>["resolveProjectionCatalog"];
}

function LegacyProjectionHostAdapterInner({
  surfaceIdentity,
  config,
  active,
  activeGraphReference,
  close,
  expandContent,
  openTool,
  graphReferenceProjectionState,
  graphReferenceBinding,
  graphReviewDiagnosticsPayload,
  resolveProjectionCatalog,
}: LegacyProjectionHostAdapterInnerProps) {
  const surfaceIdentityRef = useRef<ProjectionSurfaceIdentity | null>(surfaceIdentity);
  surfaceIdentityRef.current = surfaceIdentity;
  useEffect(() => {
    return () => {
      surfaceIdentityRef.current = null;
    };
  }, []);
  const firstToolId = config.tools[0]?.id;
  const campaignKey = config.context!.campaignId;
  const [latestIngestedSessionByCampaign, setLatestIngestedSessionByCampaign] = useState<
    Record<string, string | null>
  >({});

  useEffect(() => {
    setLatestIngestedSessionByCampaign((current) => {
      if (campaignKey in current) return current;
      return { ...current, [campaignKey]: null };
    });
  }, [campaignKey]);

  const latestIngestedSessionId = latestIngestedSessionByCampaign[campaignKey] ?? null;

  const resolveLatestIngestedSessionId = useCallback(async () => {
    if (latestIngestedSessionId) return latestIngestedSessionId;
    try {
      const response = await getRecapArtifacts(config.context!.campaignId);
      const records = sortRecapArtifactRecords(filterNumericRecapArtifactRecords(response.records));
      const sessionId = records.at(-1)?.session_id ?? null;
      setLatestIngestedSessionByCampaign((current) => ({ ...current, [campaignKey]: sessionId }));
      return sessionId;
    } catch {
      setLatestIngestedSessionByCampaign((current) => ({ ...current, [campaignKey]: null }));
      return null;
    }
  }, [campaignKey, config.context, latestIngestedSessionId]);

  const openToolFromNav = useCallback(
    async (toolId: string) => {
      const identityAtStart = surfaceIdentityRef.current;
      const inferredSessionId =
        SESSION_AWARE_TOOLS.has(toolId) && !requestedSessionFromLocation()
          ? await resolveLatestIngestedSessionId()
          : null;
      const identityNow = surfaceIdentityRef.current;
      if (
        !identityAtStart ||
        !identityNow ||
        !sameProjectionSurfaceIdentity(identityAtStart, identityNow)
      ) {
        return;
      }
      if (typeof window !== "undefined") {
        const params = new URLSearchParams(window.location.search);
        params.set("tool", toolId);
        if (inferredSessionId) {
          params.set("session", inferredSessionId);
        }
        window.history.pushState(
          {},
          "",
          `${window.location.pathname}?${params.toString()}`,
        );
      }
      openTool(toolId);
    },
    [openTool, resolveLatestIngestedSessionId],
  );

  useEffect(() => {
    const requestedTool = requestedToolFromLocation();
    if (requestedTool && config.tools.some((tool) => tool.id === requestedTool)) {
      openTool(requestedTool);
    }
  }, [config.tools, openTool]);

  const runtimeBindings = useMemo(() => {
    const bindings: Record<string, unknown> = {
      [PLAN_CONTEXT_BINDING_ID]: config.context,
      [PLAN_SURFACE_CONFIG_BINDING_ID]: config,
    };
    if (activeGraphReference) {
      bindings[GRAPH_REFERENCE_RESOLUTION_BINDING_ID] = activeGraphReference;
    }
    if (graphReferenceProjectionState !== null && graphReferenceProjectionState !== undefined) {
      bindings[GRAPH_REFERENCE_PROJECTION_STATE_BINDING_ID] = graphReferenceProjectionState;
    }
    if (graphReferenceBinding) {
      bindings[GRAPH_REFERENCE_BINDING_ID] = graphReferenceBinding;
    }
    if (graphReviewDiagnosticsPayload) {
      bindings[GRAPH_REVIEW_DIAGNOSTICS_BINDING_ID] = graphReviewDiagnosticsPayload;
    }
    return bindings;
  }, [
    activeGraphReference,
    config,
    graphReferenceBinding,
    graphReferenceProjectionState,
    graphReviewDiagnosticsPayload,
  ]);

  const body = !active ? null : active.kind === "content" && !activeGraphReference ? (
    <p className="surface-projection-empty">Loading reference…</p>
  ) : (() => {
    const catalogId = active.kind === "tool" ? active.key : GRAPH_REFERENCE_PROJECTION_ID;
    const resolution = resolveProjectionCatalog({
      projectionId: catalogId,
      active,
      bindings: runtimeBindings,
    });
    if (resolution.status === "ready") {
      return resolution.body;
    }
    if (active.kind === "tool" && resolution.status === "unregistered") {
      return <p className="plan-projection-empty">Unknown tool: {active.key}</p>;
    }
    return <p className="surface-projection-empty">Projection unavailable.</p>;
  })();

  return (
    <ProjectionHost
      active={active}
      navigationItems={config.tools.map((tool) => ({ id: tool.id, label: tool.label }))}
      labels={{
        toggleTitle: "Plan toolbox",
        closedDrawerLabel: "Plan toolbox",
        navigationLabel: "Toolbox tools",
        closeLabel: "Close toolbox",
        toolKicker: "Command Board",
        contentKicker: "Reference",
        toolTitle: "Toolbox",
        contentTitle: "Reference",
      }}
      theme={config.theme}
      body={body}
      onNavigate={(itemId) => void openToolFromNav(itemId)}
      onToggle={() => {
        if (firstToolId) void openToolFromNav(firstToolId);
      }}
      onClose={close}
      onExpand={expandContent}
    />
  );
}
