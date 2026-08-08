import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { getRecapArtifacts } from "../../api/liveApi";
import { useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import {
  sameProjectionSurfaceIdentity,
  type ProjectionSurfaceIdentity,
} from "../../agentInteraction/projectionSurfacePublication";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import { ProjectionHost } from "../../surfaceInteraction/projection/ProjectionHost";
import type { SurfaceInteractionPublication } from "../../surfaceInteraction/types";
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
import type { SurfaceConfig } from "../types";
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

/** Drop sticky ?tool= (and #tool=) so close does not fight the URL restore effect. */
export function clearToolQueryParamFromLocation(): void {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams(window.location.search);
  const hadQueryTool = params.has("tool");
  if (hadQueryTool) params.delete("tool");
  const hash = window.location.hash.replace(/^#/, "");
  const hadHashTool = hash.startsWith("tool=");
  if (!hadQueryTool && !hadHashTool) return;
  const query = params.toString();
  const path = window.location.pathname;
  const nextPath = query ? `${path}?${query}` : path;
  const keepHash = hash && !hash.startsWith("tool=") ? `#${hash}` : "";
  window.history.replaceState({}, "", `${nextPath}${keepHash}`);
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

type ProjectionHostPolicy =
  | {
      kind: "legacy-plan-or-ingest";
      surfaceIdentity: ProjectionSurfaceIdentity;
      config: SurfaceConfig;
      toolDescriptors: NonNullable<SurfaceInteractionPublication["projections"]>;
    }
  | {
      kind: "native-build";
      publication: SurfaceInteractionPublication;
    }
  | { kind: "none" };

function resolveProjectionHostPolicy(
  projectionSurface: ReturnType<typeof useAgentInteraction>["projectionSurface"],
  surfaceInteractionPublication: SurfaceInteractionPublication | null,
): ProjectionHostPolicy {
  const config = projectionSurface?.publication.config ?? null;
  const projectionsEnabled = projectionSurface?.projectionsEnabled ?? false;

  if (config && projectionsEnabled && config.tools.length > 0 && config.context) {
    return {
      kind: "legacy-plan-or-ingest",
      surfaceIdentity: projectionSurface!.publication.identity,
      config,
      toolDescriptors: (surfaceInteractionPublication?.projections ?? []).filter(
        (entry) => entry.kind === "tool",
      ),
    };
  }

  const publication = surfaceInteractionPublication;
  if (
    publication
    && publication.surfaceId === "build"
    && publication.tools.some((tool) => tool.activation.kind === "projection")
  ) {
    return { kind: "native-build", publication };
  }

  return { kind: "none" };
}

function mapPublicationBindings(
  publication: SurfaceInteractionPublication,
): Record<string, unknown> {
  const bindings: Record<string, unknown> = {};
  for (const entry of publication.projectionBindings) {
    bindings[entry.id] = entry.value;
  }
  return bindings;
}

/**
 * Temporary Plan-owned projection host policy adapter (BLD-SIH-03a/03b).
 * Owns URL/session inference and stale identity checks for legacy Plan/Ingest;
 * native Build uses publication-scoped bindings without legacy URL writes.
 * Delete when Plan recomposition lands a native publication path after BLD-SIH-06.
 */
export function LegacyProjectionHostAdapter() {
  const { projectionSurface, surfaceInteractionPublication, registerProjectionToolActivator } =
    useAgentInteraction();
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

  const policy = useMemo(
    () => resolveProjectionHostPolicy(projectionSurface, surfaceInteractionPublication),
    [projectionSurface, surfaceInteractionPublication],
  );

  const surfaceIdentityRef = useRef<ProjectionSurfaceIdentity | null>(
    policy.kind === "legacy-plan-or-ingest" ? policy.surfaceIdentity : null,
  );
  surfaceIdentityRef.current = policy.kind === "legacy-plan-or-ingest" ? policy.surfaceIdentity : null;

  useEffect(() => {
    return () => {
      surfaceIdentityRef.current = null;
    };
  }, []);

  const legacyConfig = policy.kind === "legacy-plan-or-ingest" ? policy.config : null;
  const campaignKey = legacyConfig?.context?.campaignId ?? null;

  const [latestIngestedSessionByCampaign, setLatestIngestedSessionByCampaign] = useState<
    Record<string, string | null>
  >({});

  useEffect(() => {
    if (!campaignKey) return;
    setLatestIngestedSessionByCampaign((current) => {
      if (campaignKey in current) return current;
      return { ...current, [campaignKey]: null };
    });
  }, [campaignKey]);

  const latestIngestedSessionId = campaignKey
    ? (latestIngestedSessionByCampaign[campaignKey] ?? null)
    : null;

  const resolveLatestIngestedSessionId = useCallback(async () => {
    if (!legacyConfig?.context || !campaignKey) return null;
    if (latestIngestedSessionId) return latestIngestedSessionId;
    try {
      const response = await getRecapArtifacts(legacyConfig.context.campaignId);
      const records = sortRecapArtifactRecords(filterNumericRecapArtifactRecords(response.records));
      const sessionId = records.at(-1)?.session_id ?? null;
      setLatestIngestedSessionByCampaign((current) => ({ ...current, [campaignKey]: sessionId }));
      return sessionId;
    } catch {
      setLatestIngestedSessionByCampaign((current) => ({ ...current, [campaignKey]: null }));
      return null;
    }
  }, [campaignKey, legacyConfig, latestIngestedSessionId]);

  const openToolFromNav = useCallback(
    async (toolId: string): Promise<boolean> => {
      const identityAtStart = surfaceIdentityRef.current;
      const inferredSessionId =
        SESSION_AWARE_TOOLS.has(toolId) && !requestedSessionFromLocation()
          ? await resolveLatestIngestedSessionId()
          : null;
      const identityNow = surfaceIdentityRef.current;
      if (
        !identityAtStart
        || !identityNow
        || !sameProjectionSurfaceIdentity(identityAtStart, identityNow)
      ) {
        return false;
      }
      const opened = openTool(toolId);
      if (!opened) {
        return false;
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
      return true;
    },
    [openTool, resolveLatestIngestedSessionId],
  );

  useEffect(() => {
    if (policy.kind !== "legacy-plan-or-ingest") return;
    return registerProjectionToolActivator(openToolFromNav);
  }, [openToolFromNav, policy.kind, registerProjectionToolActivator]);

  useEffect(() => {
    if (policy.kind === "native-build") {
      return registerProjectionToolActivator((toolId) => openTool(toolId));
    }
    return undefined;
  }, [openTool, policy.kind, registerProjectionToolActivator]);

  // Deep-link / refresh restore only. Do not re-open on every openTool/policy
  // identity churn while ?tool= is still sticky after the operator closed.
  useEffect(() => {
    if (policy.kind !== "legacy-plan-or-ingest") return;
    const requestedTool = requestedToolFromLocation();
    if (!requestedTool) return;
    if (!policy.config.tools.some((tool) => tool.id === requestedTool)) return;
    // Plan tool ids match projection keys (recap, statblock, …).
    if (active?.kind === "tool" && active.key === requestedTool) return;
    openTool(requestedTool);
  }, [active, openTool, policy]);

  const handleClose = useCallback(() => {
    if (policy.kind === "legacy-plan-or-ingest") {
      clearToolQueryParamFromLocation();
    }
    close();
  }, [close, policy.kind]);

  const runtimeBindings = useMemo(() => {
    const bindings: Record<string, unknown> = policy.kind === "native-build"
      ? mapPublicationBindings(policy.publication)
      : policy.kind === "legacy-plan-or-ingest"
        ? {
            [PLAN_CONTEXT_BINDING_ID]: policy.config.context,
            [PLAN_SURFACE_CONFIG_BINDING_ID]: policy.config,
          }
        : {};
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
    graphReferenceBinding,
    graphReferenceProjectionState,
    graphReviewDiagnosticsPayload,
    policy,
  ]);

  const navigationItems = useMemo(() => {
    if (policy.kind === "legacy-plan-or-ingest") {
      return policy.config.tools.map((tool) => ({ id: tool.id, label: tool.label }));
    }
    if (policy.kind === "native-build") {
      // Nav id = projection descriptor id so ProjectionHost can match active.key
      // without host/type changes (tool id ≠ projection id for Build Find existing).
      return policy.publication.tools
        .filter(
          (tool) => tool.availability.status === "enabled" && tool.activation.kind === "projection",
        )
        .map((tool) => ({
          id: tool.activation.kind === "projection" ? tool.activation.projectionId : tool.id,
          label: tool.label,
        }));
    }
    return [];
  }, [policy]);

  const hostLabels = useMemo(() => {
    if (policy.kind === "native-build") {
      const surfaceLabel = policy.publication.label;
      return {
        toggleTitle: `${surfaceLabel} toolbox`,
        closedDrawerLabel: `${surfaceLabel} toolbox`,
        navigationLabel: "Toolbox tools",
        closeLabel: "Close toolbox",
        toolKicker: surfaceLabel,
        contentKicker: "Reference",
        toolTitle: "Toolbox",
        contentTitle: "Reference",
      };
    }
    return {
      toggleTitle: "Plan toolbox",
      closedDrawerLabel: "Plan toolbox",
      navigationLabel: "Toolbox tools",
      closeLabel: "Close toolbox",
      toolKicker: "Command Board",
      contentKicker: "Reference",
      toolTitle: "Toolbox",
      contentTitle: "Reference",
    };
  }, [policy]);

  const hostTheme = useMemo(() => {
    if (policy.kind === "legacy-plan-or-ingest") return policy.config.theme;
    return {};
  }, [policy]);

  const onNavigate = useCallback(
    (itemId: string) => {
      if (policy.kind === "legacy-plan-or-ingest") {
        void openToolFromNav(itemId);
        return;
      }
      if (policy.kind === "native-build") {
        const tool = policy.publication.tools.find(
          (entry) =>
            entry.id === itemId
            || (entry.activation.kind === "projection" && entry.activation.projectionId === itemId),
        );
        if (tool) openTool(tool.id);
        return;
      }
      openTool(itemId);
    },
    [openTool, openToolFromNav, policy],
  );

  if (policy.kind === "none") {
    return null;
  }

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
    <>
      {policy.kind === "legacy-plan-or-ingest" && policy.config.id === "plan" ? (
        <PlanProjectionCatalogRegistration
          surfaceId={policy.config.id}
          toolDescriptors={policy.toolDescriptors}
        />
      ) : null}
      {policy.kind === "legacy-plan-or-ingest" && policy.config.id === "ingest" ? (
        <IngestProjectionCatalogRegistration
          surfaceId={policy.config.id}
          toolDescriptors={policy.toolDescriptors}
        />
      ) : null}
      <ProjectionHost
        active={active}
        navigationItems={navigationItems}
        labels={hostLabels}
        theme={hostTheme}
        body={body}
        onNavigate={onNavigate}
        onClose={handleClose}
        onExpand={expandContent}
      />
    </>
  );
}
