import { useCallback, useEffect, useState } from "react";

import { getRecapArtifacts } from "../../api/liveApi";
import { useProjection, projectionContainerClass } from "./projectionContext";
import { renderContentProjection, renderToolProjection } from "./projectionRegistry";
import type { SurfaceConfig } from "../types";
import {
  filterNumericRecapArtifactRecords,
  sortRecapArtifactRecords,
} from "../graphPreview/recapSessionLabels";

interface AdaptiveProjectionContainerProps {
  config: SurfaceConfig;
}

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

export function AdaptiveProjectionContainer({ config }: AdaptiveProjectionContainerProps) {
  const { active, activePlanReference, close, expandContent, openTool, planProjectionState } = useProjection();
  const isOpen = Boolean(active);
  const activeToolId = active?.kind === "tool" ? active.key : null;
  const firstToolId = config.tools[0]?.id;
  const [latestIngestedSessionId, setLatestIngestedSessionId] = useState<string | null>(null);

  const resolveLatestIngestedSessionId = useCallback(async () => {
    if (latestIngestedSessionId) return latestIngestedSessionId;
    try {
      const response = await getRecapArtifacts(config.context.campaignId);
      const records = sortRecapArtifactRecords(filterNumericRecapArtifactRecords(response.records));
      const sessionId = records.at(-1)?.session_id ?? null;
      setLatestIngestedSessionId(sessionId);
      return sessionId;
    } catch {
      setLatestIngestedSessionId(null);
      return null;
    }
  }, [config.context.campaignId, latestIngestedSessionId]);

  const openToolFromNav = useCallback(
    async (toolId: string) => {
      const inferredSessionId =
        SESSION_AWARE_TOOLS.has(toolId) && !requestedSessionFromLocation()
          ? await resolveLatestIngestedSessionId()
          : null;
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
  // Reference glances must leave the canvas interactive so chips stay clickable
  // while a card is open. Modal backdrop stays for tool projections only.
  const showModalBackdrop = isOpen && active?.kind === "tool";
  const rootClass = [
    "plan-toolbox",
    isOpen ? "open" : "",
    active?.kind === "tool" ? `tool-${active.key}` : "",
    active?.kind === "content" ? "tool-reference" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={rootClass}>
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
        <nav className="plan-toolbox-nav" aria-label="Toolbox tools">
          {active?.kind === "content" ? (
            active.glanceOnly ? (
              <button type="button" onClick={expandContent}>
                Expand
              </button>
            ) : null
          ) : (
            config.tools.map((tool) => (
              <button
                key={tool.id}
                type="button"
                className={activeToolId === tool.id ? "active" : undefined}
                aria-pressed={activeToolId === tool.id}
                onClick={() => void openToolFromNav(tool.id)}
              >
                {tool.label}
              </button>
            ))
          )}
          <button
            type="button"
            className="plan-toolbox-nav-close"
            onClick={close}
            aria-label="Close toolbox"
          >
            ×
          </button>
        </nav>
        <div className="plan-projection-body">
          {!active ? null : active.kind === "tool" ? (
            renderToolProjection(active.key, config.context)
          ) : activePlanReference ? (
            renderContentProjection(activePlanReference, config, planProjectionState)
          ) : (
            <p className="plan-projection-empty">Loading reference…</p>
          )}
        </div>
      </aside>
    </div>
  );
}
