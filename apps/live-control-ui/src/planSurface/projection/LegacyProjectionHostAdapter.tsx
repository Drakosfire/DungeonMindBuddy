import { useCallback, useEffect, useRef, useState } from "react";

import { getRecapArtifacts } from "../../api/liveApi";
import { useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import {
  sameProjectionSurfaceIdentity,
  type ProjectionSurfaceIdentity,
} from "../../agentInteraction/projectionSurfacePublication";
import { ProjectionHost } from "../../surfaceInteraction/projection/ProjectionHost";
import { useProjection } from "./projectionContext";
import { renderContentProjection, renderToolProjection } from "./projectionRegistry";
import {
  filterNumericRecapArtifactRecords,
  sortRecapArtifactRecords,
} from "../graphPreview/recapSessionLabels";

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
 * Temporary Plan-owned projection host policy adapter (BLD-SIH-03a).
 * Owns URL/session inference, stale identity checks, and renderer dispatch.
 * Delete when BLD-SIH-03b / Plan recomposition lands a native publication path.
 */
export function LegacyProjectionHostAdapter() {
  const { projectionSurface } = useAgentInteraction();
  const {
    active,
    activeGraphReference,
    close,
    expandContent,
    openTool,
    graphReferenceProjectionState,
    graphReferenceBinding,
    graphReviewDiagnosticsPayload,
  } = useProjection();

  const config = projectionSurface?.publication.config ?? null;
  const projectionsEnabled = projectionSurface?.projectionsEnabled ?? false;

  if (!config || !projectionsEnabled || config.tools.length === 0 || !config.context) {
    return null;
  }

  return (
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
    />
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

  const body = !active ? null : active.kind === "tool" ? (
    renderToolProjection(active.key, config.context!, {
      graphReviewDiagnosticsPayload,
    })
  ) : activeGraphReference ? (
    renderContentProjection(activeGraphReference, config, graphReferenceProjectionState, {
      graphReferenceBinding,
      glanceOnly: active.glanceOnly === true,
    })
  ) : (
    <p className="surface-projection-empty">Loading reference…</p>
  );

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
