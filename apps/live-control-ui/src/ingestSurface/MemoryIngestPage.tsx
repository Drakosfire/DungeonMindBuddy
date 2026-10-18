import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { getExtractionRun, getPlanView } from "../api/liveApi";
import type { ExtractionRunRecord, PlanViewProjection } from "../api/types";
import { usePublishAgentSurfaceContext } from "../agentInteraction/usePublishAgentSurfaceContext";
import { IngestionModule } from "../modules/IngestionModule";
import { AppChrome } from "../chrome/AppChrome";
import { buildIngestContextFromPlanView } from "../planSurface/config/ingestSurfaceConfig";
import { GraphReviewWorkbenchModule } from "../planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule";
import { parseGraphReviewRunHandoff } from "../planSurface/graphReviewWorkbench/graphReviewRunSelection";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { worldScopedSurfaceHref } from "../selectedWorld/worldSelectionNavigation";
import { useIngestRunCatalogInformation } from "./useIngestRunCatalogInformation";
import "../planSurface/planSurface.css";
import "./MemoryIngestPage.css";

type LoadStatus = "loading" | "ready" | "error";

export function MemoryIngestPage() {
  const selectedWorld = useSelectedWorld();
  const selectionError = selectedWorld.kind === "error" ? selectedWorld.message : null;
  const blockedContext = useMemo(() => selectedWorld.kind === "managed" ? null : {
    surfaceId: "ingest",
    label: "Memory Ingest",
    campaignId: null,
    documentId: null,
    sessionNumber: null,
    ambientSummary: selectedWorld.kind === "loading"
      ? "Loading World selection…"
      : selectedWorld.kind === "error" ? selectedWorld.message : "Select a World to use Ingest.",
    sourceEnvelope: null,
  }, [selectedWorld.kind, selectionError]);
  usePublishAgentSurfaceContext(blockedContext);
  if (selectedWorld.kind === "managed") return <SelectedWorldMemoryIngestPage key={selectedWorld.worldId} managedWorldId={selectedWorld.worldId} />;
  return (
    <AppChrome activeRoute="ingest">
      <main className="ingest-first-use">
        {selectedWorld.kind === "loading" ? (
          <section className="ingest-welcome-card" aria-labelledby="ingest-loading-title">
            <p className="ingest-welcome-kicker">A place for your sources</p>
            <h1 id="ingest-loading-title">Getting your World ready…</h1>
            <p role="status">Loading World selection…</p>
          </section>
        ) : selectedWorld.kind === "error" ? (
          <section className="ingest-welcome-card ingest-welcome-card--error" aria-labelledby="ingest-error-title">
            <p className="ingest-welcome-kicker">World selection</p>
            <h1 id="ingest-error-title">We couldn’t open that World.</h1>
            <div role="alert">
              <p>{selectedWorld.message}</p>
              <p>Choose a different World from the navigation to continue.</p>
            </div>
          </section>
        ) : (
          <section className="ingest-welcome-card" aria-labelledby="ingest-welcome-title">
            <p className="ingest-welcome-kicker">A place for your sources</p>
            <h1 id="ingest-welcome-title">Give your World a little more to remember.</h1>
            <p className="ingest-welcome-intro">
              Ingest turns your notes and session recaps into evidence you can inspect before it becomes part of a World.
              Choose a World in the navigation to begin.
            </p>
            <ol className="ingest-welcome-steps" aria-label="How Ingest works">
              <li><span>01</span><div><strong>Choose a World</strong><p>Pick the setting you want to grow.</p></div></li>
              <li><span>02</span><div><strong>Bring in a source</strong><p>Open Build to add a document or recap.</p></div></li>
              <li><span>03</span><div><strong>Review what it found</strong><p>Inspect the evidence before accepting it.</p></div></li>
            </ol>
          </section>
        )}
      </main>
    </AppChrome>
  );
}

function SelectedWorldMemoryIngestPage({ managedWorldId: selectedManagedWorldId }: { managedWorldId: string }) {
  const selectedWorld = useSelectedWorld();
  const managedWorldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const catalog = useIngestRunCatalogInformation();
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [planView, setPlanView] = useState<PlanViewProjection | null>(null);
  const [locationSearch, setLocationSearch] = useState(() => window.location.search);
  const locationSearchRef = useRef(locationSearch);
  locationSearchRef.current = locationSearch;
  const [sourceReview, setSourceReview] = useState<Pick<
    ExtractionRunRecord,
    "run_id" | "source_artifact_id" | "campaign_id" | "session_id"
  > | null>(null);

  const refresh = useCallback(async (searchSnapshot: string) => {
    const params = new URLSearchParams(searchSnapshot);
    const claimedCampaign = params.get("campaign")?.trim();
    const handoff = parseGraphReviewRunHandoff(searchSnapshot);
    const isExistingRecapCampaign = !handoff && managedWorldId === "elderwyld" &&
      (claimedCampaign === "longmont-c1" || claimedCampaign === "longmont-c2");
    if (
      managedWorldId
      && claimedCampaign
      && claimedCampaign !== managedWorldId
      && !isExistingRecapCampaign
      && !handoff
    ) {
      throw new Error(`Ingest campaign ${claimedCampaign} does not match selected World ${managedWorldId}.`);
    }
    let nextSourceReview: typeof sourceReview = null;
    if (managedWorldId && handoff?.extractionRunId && handoff.errors.length === 0) {
      const run = await getExtractionRun(handoff.extractionRunId);
      if (run.run_id !== handoff.extractionRunId) {
        throw new Error("handoff extractionRunId does not match the loaded run");
      }
      if (run.source_domain === "recap") {
        // A recap's campaign identifies its source. The selected managed World
        // is a destination intent; it does not establish recap ownership.
        nextSourceReview = {
          run_id: run.run_id,
          source_artifact_id: run.source_artifact_id,
          campaign_id: run.campaign_id,
          session_id: run.session_id,
        };
      } else {
        if (
          claimedCampaign
          && claimedCampaign !== managedWorldId
          && !isExistingRecapCampaign
        ) {
          throw new Error(`Ingest campaign ${claimedCampaign} does not match selected World ${managedWorldId}.`);
        }
        if (run.campaign_id !== managedWorldId) {
          throw new Error(`Extraction Run does not belong to World ${managedWorldId}.`);
        }
      }
    }
    const response = await getPlanView(managedWorldId);
    // The server-resolved World ID pins this view to the selected managed
    // World. Campaign scope is separate context and is not a World identity.
    if (managedWorldId && response.world_id !== managedWorldId) {
      throw new Error(`Ingest context does not match selected World ${managedWorldId}.`);
    }
    return { planView: response, sourceReview: nextSourceReview };
  }, [managedWorldId]);

  useEffect(() => {
    let cancelled = false;
    const searchSnapshot = locationSearch;
    (async () => {
      setStatus("loading");
      setError(null);
      setSourceReview(null);
      setPlanView(null);
      try {
        const loaded = await refresh(searchSnapshot);
        if (cancelled || locationSearchRef.current !== searchSnapshot) return;
        setPlanView(loaded.planView);
        setSourceReview(loaded.sourceReview);
        setStatus("ready");
      } catch (loadError) {
        if (!cancelled && locationSearchRef.current === searchSnapshot) {
          setStatus("error");
          setError(loadError instanceof Error ? loadError.message : "Failed to load ingest context");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [locationSearch, refresh]);

  useEffect(() => {
    const syncLocationSearch = () => setLocationSearch(window.location.search);
    window.addEventListener("popstate", syncLocationSearch);
    return () => window.removeEventListener("popstate", syncLocationSearch);
  }, []);

  const onLocationSearchChange = useCallback((search: string) => {
    setLocationSearch(search);
  }, []);

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

  // The established recap pipeline owns the Longmont corpus in Elderwyld.
  // Keep it separate from exact managed extraction-run review; never infer
  // a Longmont campaign for another World.
  if (managedWorldId && !parseGraphReviewRunHandoff(window.location.search)) {
    return (
      <AppChrome activeRoute="ingest">
        <main className="ingest-surface-root" aria-label="Memory Ingest">
          {managedWorldId === "elderwyld" ? (
            <IngestionModule campaignId="longmont-c2" session={29} managedWorldId={selectedManagedWorldId} initialSourceSession={29} />
          ) : (
            <section className="ingest-welcome-card ingest-welcome-card--world" aria-labelledby="ingest-world-welcome-title">
              <p className="ingest-welcome-kicker">{selectedWorld.kind === "managed" ? selectedWorld.name : "Your World"}</p>
              <h2 id="ingest-world-welcome-title">Bring a source into the story.</h2>
              <p className="ingest-welcome-intro">
                Add a document in Build, then start an extraction to turn its details into reviewable World evidence.
                Ingest will bring you back to the exact run so you can inspect what Buddy found.
              </p>
              <a className="ingest-welcome-action" href={worldScopedSurfaceHref("/build", managedWorldId)}>
                Open Build <span aria-hidden="true">→</span>
              </a>
              <p className="ingest-welcome-footnote">Nothing enters the World Graph until you review and accept it.</p>
            </section>
          )}
        </main>
      </AppChrome>
    );
  }

  return (
    <AppChrome activeRoute="ingest">
      <main className="ingest-surface-root" aria-label="Memory Ingest">
        {sourceReview ? (
          <section
            className="ingest-source-review"
            aria-label="Read-only source review"
            data-testid="source-review-scope"
          >
            <h1>Read-only source review</h1>
            <dl className="ingest-source-review-metadata">
              <dt>Source artifact</dt>
              <dd>
                <details>
                  <summary>Show exact artifact ID</summary>
                  <code>{sourceReview.source_artifact_id}</code>
                </details>
              </dd>
              <dt>Source campaign</dt><dd>{sourceReview.campaign_id ?? "Not declared"}</dd>
              <dt>Source session</dt><dd>{sourceReview.session_id ?? "Not declared"}</dd>
              <dt>Selected target World</dt><dd>{managedWorldId}</dd>
            </dl>
            <p className="ingest-source-review-notice">
              Source text is read-only. Quote corrections create a separate candidate; reviewing or correcting it does not import it or associate it with the selected World.
            </p>
          </section>
        ) : null}
        <GraphReviewWorkbenchModule
          context={context}
          catalogChannel={catalog.channel}
          onCatalogRefresh={catalog.refresh}
          sourceReviewOnly={sourceReview !== null}
          sourceReviewRunId={sourceReview?.run_id ?? null}
          locationSearch={locationSearch}
          onLocationSearchChange={onLocationSearchChange}
        />
      </main>
    </AppChrome>
  );
}
