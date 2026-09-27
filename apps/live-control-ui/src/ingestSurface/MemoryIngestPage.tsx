import { useCallback, useEffect, useMemo, useState } from "react";

import { getExtractionRun, getPlanView } from "../api/liveApi";
import type { PlanViewProjection } from "../api/types";
import { usePublishAgentSurfaceContext } from "../agentInteraction/usePublishAgentSurfaceContext";
import { AppChrome } from "../chrome/AppChrome";
import { buildIngestContextFromPlanView } from "../planSurface/config/ingestSurfaceConfig";
import { GraphReviewWorkbenchModule } from "../planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule";
import { parseGraphReviewRunHandoff } from "../planSurface/graphReviewWorkbench/graphReviewRunSelection";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { useIngestRunCatalogInformation } from "./useIngestRunCatalogInformation";
import "../planSurface/planSurface.css";

type LoadStatus = "loading" | "ready" | "error";

export function MemoryIngestPage() {
  const selectedWorld = useSelectedWorld();
  const managedWorldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const catalog = useIngestRunCatalogInformation();
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [planView, setPlanView] = useState<PlanViewProjection | null>(null);

  const refresh = useCallback(async () => {
    const params = new URLSearchParams(window.location.search);
    const claimedCampaign = params.get("campaign")?.trim();
    if (managedWorldId && claimedCampaign && claimedCampaign !== managedWorldId) {
      throw new Error(`Ingest campaign ${claimedCampaign} does not match selected World ${managedWorldId}.`);
    }
    const handoff = parseGraphReviewRunHandoff(window.location.search);
    if (managedWorldId && handoff?.extractionRunId && handoff.errors.length === 0) {
      const run = await getExtractionRun(handoff.extractionRunId);
      if (run.campaign_id !== managedWorldId) {
        throw new Error(`Extraction Run does not belong to World ${managedWorldId}.`);
      }
    }
    const response = await getPlanView(managedWorldId);
    if (managedWorldId && (
      response.world_id !== managedWorldId || response.campaign_id !== managedWorldId
    )) {
      throw new Error(`Ingest context does not match selected World ${managedWorldId}.`);
    }
    setPlanView(response);
  }, [managedWorldId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setStatus("loading");
      setError(null);
      try {
        await refresh();
        if (!cancelled) setStatus("ready");
      } catch (loadError) {
        if (!cancelled) {
          setStatus("error");
          setError(loadError instanceof Error ? loadError.message : "Failed to load ingest context");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const context = useMemo(
    () => (planView ? buildIngestContextFromPlanView(planView) : null),
    [planView],
  );

  const agentSurfaceContext = useMemo(() => {
    if (status === "loading") {
      return {
        surfaceId: "ingest",
        label: "Memory Ingest",
        campaignId: null,
        documentId: null,
        sessionNumber: null,
        ambientSummary: "Loading memory review…",
        sourceEnvelope: null,
      };
    }
    if (status === "error" || !context) {
      return {
        surfaceId: "ingest",
        label: "Memory Ingest",
        campaignId: null,
        documentId: null,
        sessionNumber: null,
        ambientSummary: error ?? "Unable to load ingest context",
        sourceEnvelope: null,
      };
    }
    return {
      surfaceId: "ingest",
      label: "Memory Ingest",
      campaignId: context.campaignId,
      documentId: null,
      sessionNumber: context.ingestSession,
      ambientSummary: `Graph Review · ${context.campaignId} · session ${context.ingestSession}`,
      sourceEnvelope: null,
    };
  }, [context, error, status]);

  usePublishAgentSurfaceContext(agentSurfaceContext);

  if (status === "loading") {
    return (
      <AppChrome activeRoute="ingest">
        <main className="app-status">
          <p>Loading memory ingest...</p>
        </main>
      </AppChrome>
    );
  }

  if (status === "error" || !context) {
    return (
      <AppChrome activeRoute="ingest">
        <main className="app-status app-error">
          <h1>Memory Ingest</h1>
          <p>{error ?? "Unable to load ingest context."}</p>
        </main>
      </AppChrome>
    );
  }

  // The existing published-recap browser is specifically the C1/C2 review
  // vocabulary. A managed World must not display that legacy catalog as if it
  // were its own memory. Exact, server-verified managed run links still use
  // the existing Graph Review projection below.
  if (managedWorldId && !parseGraphReviewRunHandoff(window.location.search)) {
    return (
      <AppChrome activeRoute="ingest">
        <main className="ingest-surface-root" aria-label="Memory Ingest">
          <h1>Memory review · {selectedWorld.kind === "managed" ? selectedWorld.name : managedWorldId}</h1>
          <p>No exact extraction run is selected for this World.</p>
          <p>Open a source in Build and follow its exact extraction-run link to review it here.</p>
        </main>
      </AppChrome>
    );
  }

  return (
    <AppChrome activeRoute="ingest">
      <main className="ingest-surface-root" aria-label="Memory Ingest">
        <GraphReviewWorkbenchModule
          context={context}
          catalogChannel={catalog.channel}
          onCatalogRefresh={catalog.refresh}
        />
      </main>
    </AppChrome>
  );
}
