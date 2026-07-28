import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";

import { getRecapArtifacts } from "../../api/liveApi";
import { useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import {
  sameProjectionSurfaceIdentity,
  type ProjectionSurfaceIdentity,
} from "../../agentInteraction/projectionSurfacePublication";
import { useProjection, projectionContainerClass } from "./projectionContext";
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

export function AdaptiveProjectionContainer() {
  const { projectionSurface } = useAgentInteraction();
  const {
    active,
    activePlanReference,
    close,
    expandContent,
    openTool,
    planProjectionState,
    planReferenceBinding,
    graphReviewDiagnosticsPayload,
  } = useProjection();

  const config = projectionSurface?.publication.config ?? null;
  const projectionsEnabled = projectionSurface?.projectionsEnabled ?? false;

  if (!config || !projectionsEnabled || config.tools.length === 0 || !config.context) {
    return null;
  }

  return (
    <AdaptiveProjectionContainerInner
      surfaceIdentity={projectionSurface!.publication.identity}
      config={config}
      active={active}
      activePlanReference={activePlanReference}
      close={close}
      expandContent={expandContent}
      openTool={openTool}
      planProjectionState={planProjectionState}
      planReferenceBinding={planReferenceBinding}
      graphReviewDiagnosticsPayload={graphReviewDiagnosticsPayload}
    />
  );
}

interface AdaptiveProjectionContainerInnerProps {
  surfaceIdentity: ProjectionSurfaceIdentity;
  config: NonNullable<ReturnType<typeof useAgentInteraction>["projectionSurface"]>["publication"]["config"];
  active: ReturnType<typeof useProjection>["active"];
  activePlanReference: ReturnType<typeof useProjection>["activePlanReference"];
  close: () => void;
  expandContent: () => void;
  openTool: (toolId: string) => void;
  planProjectionState: ReturnType<typeof useProjection>["planProjectionState"];
  planReferenceBinding: ReturnType<typeof useProjection>["planReferenceBinding"];
  graphReviewDiagnosticsPayload: ReturnType<typeof useProjection>["graphReviewDiagnosticsPayload"];
}

function AdaptiveProjectionContainerInner({
  surfaceIdentity,
  config,
  active,
  activePlanReference,
  close,
  expandContent,
  openTool,
  planProjectionState,
  planReferenceBinding,
  graphReviewDiagnosticsPayload,
}: AdaptiveProjectionContainerInnerProps) {
  const isOpen = Boolean(active);
  // Latest rendered surface identity for async re-validation. Cleared on
  // unmount so completions from an unmounted surface can never act.
  const surfaceIdentityRef = useRef<ProjectionSurfaceIdentity | null>(surfaceIdentity);
  surfaceIdentityRef.current = surfaceIdentity;
  useEffect(() => {
    return () => {
      surfaceIdentityRef.current = null;
    };
  }, []);
  const activeToolId = active?.kind === "tool" ? active.key : null;
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
      // Capture the exact surface identity at invocation; an async session
      // lookup may complete after the host has moved to another surface.
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
        // Stale lookup result: it must never touch another surface's URL or
        // projection state.
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

  useEffect(() => {
    document.body.classList.toggle("plan-toolbox-open", isOpen);
    return () => document.body.classList.remove("plan-toolbox-open");
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") close();
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [close, isOpen]);

  const containerClass = projectionContainerClass(active?.size);
  const showModalBackdrop = isOpen && active?.kind === "tool";
  const rootClass = [
    "plan-toolbox",
    isOpen ? "open" : "",
    active?.kind === "tool" ? `tool-${active.key}` : "",
    active?.kind === "content" ? "tool-reference" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const themeStyle = (config.theme.tokens ?? {}) as CSSProperties;

  return (
    <div
      className={rootClass}
      style={themeStyle}
      data-md-theme={config.theme.themeId}
    >
      <button
        type="button"
        className="plan-toolbox-toggle"
        aria-expanded={isOpen}
        aria-controls="plan-toolbox-drawer"
        title="Plan toolbox"
        onClick={() => (isOpen ? close() : firstToolId ? void openToolFromNav(firstToolId) : undefined)}
      >
        Tools
      </button>
      <div
        className="plan-toolbox-backdrop"
        hidden={!showModalBackdrop}
        onClick={close}
        aria-hidden="true"
      />
      <aside
        id="plan-toolbox-drawer"
        className={containerClass}
        aria-label={active ? `${active.title} projection` : "Plan toolbox"}
      >
        <header className="plan-projection-header">
          <div>
            <p className="plan-surface-kicker">{active?.kind === "content" ? "Reference" : "Command Board"}</p>
            <h2>{active?.kind === "content" ? "Reference" : "Toolbox"}</h2>
          </div>
          <div className="plan-projection-header-actions">
            {active?.kind === "content" && active.glanceOnly ? (
              <button type="button" onClick={expandContent}>
                Expand
              </button>
            ) : null}
            <button type="button" onClick={close} aria-label="Close toolbox">
              ×
            </button>
          </div>
        </header>
        <nav
          className="plan-toolbox-nav"
          aria-label="Toolbox tools"
          hidden={active?.kind === "content"}
        >
          {config.tools.map((tool) => (
            <button
              key={tool.id}
              type="button"
              className={activeToolId === tool.id ? "active" : undefined}
              aria-pressed={activeToolId === tool.id}
              onClick={() => void openToolFromNav(tool.id)}
            >
              {tool.label}
            </button>
          ))}
        </nav>
        <div className="plan-projection-body">
          {!active ? null : active.kind === "tool" ? (
            renderToolProjection(active.key, config.context!, {
              graphReviewDiagnosticsPayload,
            })
          ) : activePlanReference ? (
            renderContentProjection(activePlanReference, config, planProjectionState, {
              planReferenceBinding,
              glanceOnly: active.glanceOnly === true,
            })
          ) : (
            <p className="plan-projection-empty">Loading reference…</p>
          )}
        </div>
      </aside>
    </div>
  );
}
