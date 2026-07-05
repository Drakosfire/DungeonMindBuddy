import { useCallback, useEffect, useMemo, useState } from "react";

import { getPlanView } from "../api/liveApi";
import type { PlanViewProjection } from "../api/types";
import { AppChrome } from "../chrome/AppChrome";
import { buildPlanContextFromPlanView } from "../planSurface/config/planSurfaceConfig";
import { GraphReviewWorkbenchModule } from "../planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule";
import "../planSurface/planSurface.css";

type LoadStatus = "loading" | "ready" | "error";

function currentPathWithQuery(): string {
  if (typeof window === "undefined") return "/ingest";
  return `${window.location.pathname}${window.location.search}`;
}

export function MemoryIngestPage() {
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [planView, setPlanView] = useState<PlanViewProjection | null>(null);

  const refresh = useCallback(async () => {
    const response = await getPlanView();
    setPlanView(response);
  }, []);

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

  const context = useMemo(() => (planView ? buildPlanContextFromPlanView(planView) : null), [planView]);

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

  return (
    <AppChrome activeRoute="ingest">
      <main className="ingest-surface-root" aria-labelledby="memory-ingest-title">
        <header className="ingest-surface-header">
          <div>
            <p className="ingest-surface-kicker">Ingest</p>
            <h1 id="memory-ingest-title">Memory Ingest</h1>
            <p>Convert source artifacts into reviewed campaign memory.</p>
          </div>
          <details className="ingest-surface-advanced">
            <summary>Advanced</summary>
            <dl>
              <div>
                <dt>Campaign</dt>
                <dd>{context.campaignId}</dd>
              </div>
              <div>
                <dt>Ingest session</dt>
                <dd>Session {context.ingestSession}</dd>
              </div>
              <div>
                <dt>Route</dt>
                <dd>
                  <code>{currentPathWithQuery()}</code>
                </dd>
              </div>
              <div>
                <dt>Legacy Plan tools</dt>
                <dd>Graph and ingest review entries are archived from the Plan toolbox.</dd>
              </div>
            </dl>
          </details>
        </header>

        <GraphReviewWorkbenchModule context={context} />
      </main>
    </AppChrome>
  );
}
