import { useCallback, useEffect, useState } from "react";

import { getEvents, getJobs, getPlanView, getSurface } from "./api/liveApi";
import type {
  LiveEvent,
  LiveJob,
  PlanViewProjection,
  ProjectionWriteResult,
  LiveQueryResponse,
  LiveState,
  SurfaceLayout,
  SurfaceModuleDefinition,
} from "./api/types";
import { AppChrome, type AppChromeTools } from "./chrome/AppChrome";
import { InspectorPane, type InspectorPaneState } from "./surface/InspectorPane";
import { SurfaceShell } from "./surface/SurfaceShell";
import type { PaneTarget } from "./surface/targetTypes";
import { PlanSurfacePage } from "./planSurface/PlanSurfacePage";
import { TiptapCalloutBridgeSpike } from "./tiptap/TiptapCalloutBridgeSpike";

type LoadStatus = "loading" | "ready" | "error";
type AppRoute = "index" | "surface" | "tiptap-callout-spike" | "plan";

function currentRoute(): AppRoute {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  if (path === "/surface" || path === "/live-control") return "surface";
  if (path === "/tiptap-callout-spike") return "tiptap-callout-spike";
  if (path === "/plan") return "plan";
  return "index";
}

function MirewardIndex() {
  return (
    <main className="launcher-root">
      <header className="launcher-header">
        <h1>Mireward local tools</h1>
        <p>C2 Session 23 launcher. Choose the surface you actually want to use.</p>
      </header>

      <section className="launcher-grid" aria-label="Main surfaces">
        <a className="launcher-card primary" href="/plan">
          <span className="launcher-kicker">Plan</span>
          <strong>Prep surface</strong>
          <span>Intentional planning canvas with ingestion, statblock tools, and reference-chip navigation.</span>
        </a>
        <a className="launcher-card" href="/evals/c2_live_prep/mireward-prep/live-play.html">
          <span className="launcher-kicker">Live Play</span>
          <strong>Command board</strong>
          <span>At-table launch surface for combat, notes, statblocks, roll tables, and bridge proof links.</span>
        </a>
        <a className="launcher-card" href="/evals/c2_live_prep/mireward-prep/retrieval.html">
          <span className="launcher-kicker">Retrieval</span>
          <strong>Dogfood surface</strong>
          <span>Source links, authority labels, planning packets, and retrieval context checks.</span>
        </a>
        <a className="launcher-card" href="/surface">
          <span className="launcher-kicker">Live Control</span>
          <strong>React surface</strong>
          <span>The configurable live-control UI with combat roster, statblock workbench, chat, and record modules.</span>
        </a>
        <a className="launcher-card" href="/tiptap-callout-spike">
          <span className="launcher-kicker">Developer Spike</span>
          <strong>Tiptap callout bridge</strong>
          <span>Editable semantic callouts, live editor JSON, and Markdown export without canon writes.</span>
        </a>
      </section>

      <section className="launcher-note">
        <p>
          This Vite app serves all UI on <code>5173</code>. The FastAPI backend remains API-only on{" "}
          <code>8000</code>, and the React live-control surface lives at <code>/surface</code>.
        </p>
      </section>
    </main>
  );
}

function TiptapSpikeRoute() {
  const [editorTools, setEditorTools] = useState<AppChromeTools | null>(null);

  return (
    <AppChrome activeRoute="tiptap-callout-spike" editorTools={editorTools}>
      <TiptapCalloutBridgeSpike onEditorToolsChange={setEditorTools} />
    </AppChrome>
  );
}

function LiveControlApp() {
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [catalog, setCatalog] = useState<SurfaceModuleDefinition[]>([]);
  const [layout, setLayout] = useState<SurfaceLayout | null>(null);
  const [state, setState] = useState<LiveState | null>(null);
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [jobs, setJobs] = useState<LiveJob[]>([]);
  const [planView, setPlanView] = useState<PlanViewProjection | null>(null);
  const [inspectorPane, setInspectorPane] = useState<InspectorPaneState>({ status: "closed" });

  const refreshAll = useCallback(async () => {
    const surface = await getSurface();
    const [eventsResponse, jobsResponse, planViewResponse] = await Promise.all([
      getEvents(),
      getJobs(),
      getPlanView(),
    ]);
    setCatalog(surface.catalog);
    setLayout(surface.layout);
    setState(surface.state);
    setEvents(eventsResponse.events);
    setJobs(jobsResponse.jobs);
    setPlanView(planViewResponse);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setStatus("loading");
      setError(null);
      try {
        await refreshAll();
        if (!cancelled) {
          setStatus("ready");
        }
      } catch (loadError) {
        if (!cancelled) {
          setStatus("error");
          setError(loadError instanceof Error ? loadError.message : "Failed to load live surface");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshAll]);

  const handleQuerySuccess = useCallback(
    async (_response: LiveQueryResponse) => {
      await refreshAll();
    },
    [refreshAll],
  );

  const handleLayoutSaved = useCallback(
    async (savedLayout: SurfaceLayout) => {
      setLayout(savedLayout);
      await refreshAll();
    },
    [refreshAll],
  );

  const handleSelectTarget = useCallback((target: PaneTarget) => {
    setInspectorPane({ status: "open", target });
  }, []);

  const handleOpenInspector = useCallback(() => {
    setInspectorPane({ status: "open", target: null });
  }, []);

  const handleCloseInspector = useCallback(() => {
    setInspectorPane({ status: "closed" });
  }, []);

  const handleCommandAccepted = useCallback(
    async (_result: ProjectionWriteResult) => {
      await refreshAll();
    },
    [refreshAll],
  );

  if (status === "loading") {
    return (
      <AppChrome activeRoute="surface">
        <main className="app-status">
          <p>Loading live surface…</p>
        </main>
      </AppChrome>
    );
  }

  if (status === "error" || !layout || !state || !planView) {
    return (
      <AppChrome activeRoute="surface">
        <main className="app-status app-error">
          <h1>Live Control</h1>
          <p>{error ?? "Unable to load session surface."}</p>
          <p className="module-muted">
            Start the L3 server with{" "}
            <code>uv run uvicorn apps.live_control_server.main:app --reload</code> and ensure
            session files are available.
          </p>
        </main>
      </AppChrome>
    );
  }

  return (
    <AppChrome
      activeRoute="surface"
      pageActions={[
        {
          id: "surface-inspector",
          label: "Inspector",
          onClick: handleOpenInspector,
        },
      ]}
    >
      <SurfaceShell
        catalog={catalog}
        layout={layout}
        state={state}
        events={events}
        jobs={jobs}
        planView={planView}
        onQuerySuccess={handleQuerySuccess}
        onLayoutSaved={handleLayoutSaved}
        onSelectTarget={handleSelectTarget}
      />
      <InspectorPane
        state={inspectorPane}
        onClose={handleCloseInspector}
        onCommandAccepted={handleCommandAccepted}
      />
    </AppChrome>
  );
}

export function App() {
  const route = currentRoute();
  if (route === "index") {
    return (
      <AppChrome activeRoute="index">
        <MirewardIndex />
      </AppChrome>
    );
  }
  if (route === "tiptap-callout-spike") return <TiptapSpikeRoute />;
  if (route === "plan") return <PlanSurfacePage />;
  return <LiveControlApp />;
}
