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
import { AgentInteractionProvider } from "./agentInteraction/AgentInteractionProvider";
import { AppChrome, type AppChromeTools } from "./chrome/AppChrome";
import { appHref, stripAppBasePath } from "./chrome/appBasePath";
import { MemoryIngestPage } from "./ingestSurface/MemoryIngestPage";
import { InspectorPane, type InspectorPaneState } from "./surface/InspectorPane";
import { SurfaceShell } from "./surface/SurfaceShell";
import type { PaneTarget } from "./surface/targetTypes";
import { PlanSurfacePage } from "./planSurface/PlanSurfacePage";
import { BuildSurfacePage } from "./buildSurface/BuildSurfacePage";
import { TiptapCalloutBridgeSpike } from "./tiptap/TiptapCalloutBridgeSpike";

type LoadStatus = "loading" | "ready" | "error";
type AppRoute =
  | "index"
  | "surface"
  | "tiptap-callout-spike"
  | "plan"
  | "ingest"
  | "build"
  | "dev";

function currentRoute(): AppRoute {
  const path = stripAppBasePath(window.location.pathname);
  if (path === "/surface" || path === "/live-control") return "surface";
  if (path === "/tiptap-callout-spike") return "tiptap-callout-spike";
  if (path === "/plan") return "plan";
  if (path === "/ingest") return "ingest";
  if (path === "/build") return "build";
  if (path === "/dev") return "dev";
  return "index";
}

function DungeonBuddyHome() {
  return (
    <main className="launcher-root dungeonbuddy-home">
      <header className="launcher-header dungeonbuddy-home-hero">
        <p className="launcher-kicker">DungeonMind</p>
        <h1>DungeonBuddy</h1>
        <p>Campaign memory, prep, and live-table tools for the GM.</p>
        <div className="dungeonbuddy-home-cta-row">
          <a className="launcher-card primary dungeonbuddy-home-cta" href={appHref("/plan")}>
            <span className="launcher-kicker">Start</span>
            <strong>Open Plan</strong>
            <span>Session prep canvas with graph memory and Ask DungeonBuddy.</span>
          </a>
        </div>
      </header>

      <section className="launcher-grid dungeonbuddy-home-secondary" aria-label="DungeonBuddy surfaces">
        <a className="launcher-card" href={appHref("/ingest")}>
          <span className="launcher-kicker">Ingest</span>
          <strong>Memory Ingest</strong>
          <span>Review extracted graph runs and promote campaign memory.</span>
        </a>
        <a className="launcher-card" href={appHref("/build")}>
          <span className="launcher-kicker">Build</span>
          <strong>Worldbuilding</strong>
          <span>Create and edit worldbuilding workspace documents.</span>
        </a>
      </section>

      <p className="launcher-note dungeonbuddy-home-dev-link">
        <a href={appHref("/dev")}>Developer tools</a>
        {" · "}
        <a href="/">DungeonMind home</a>
      </p>
    </main>
  );
}

function DevToolsIndex() {
  return (
    <main className="launcher-root">
      <header className="launcher-header">
        <h1>Developer tools</h1>
        <p>Local spikes, eval boards, and legacy live-control surfaces.</p>
      </header>

      <section className="launcher-grid" aria-label="Developer surfaces">
        <a className="launcher-card" href={appHref("/")}>
          <span className="launcher-kicker">Home</span>
          <strong>DungeonBuddy</strong>
          <span>Back to the product entry.</span>
        </a>
        <a className="launcher-card" href="/evals/c2_live_prep/mireward-prep/live-play.html">
          <span className="launcher-kicker">Live Play</span>
          <strong>Command board</strong>
          <span>At-table launch surface for combat, notes, and bridge proof links.</span>
        </a>
        <a className="launcher-card" href="/evals/c2_live_prep/mireward-prep/retrieval.html">
          <span className="launcher-kicker">Retrieval</span>
          <strong>Dogfood surface</strong>
          <span>Source links, authority labels, and retrieval context checks.</span>
        </a>
        <a className="launcher-card" href={appHref("/surface")}>
          <span className="launcher-kicker">Live Control</span>
          <strong>React surface</strong>
          <span>Configurable live-control UI with combat roster and chat modules.</span>
        </a>
        <a className="launcher-card" href={appHref("/tiptap-callout-spike")}>
          <span className="launcher-kicker">Developer Spike</span>
          <strong>Tiptap callout bridge</strong>
          <span>Editable semantic callouts and Markdown export without canon writes.</span>
        </a>
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
  let content;
  if (route === "index") {
    content = (
      <AppChrome activeRoute="index">
        <DungeonBuddyHome />
      </AppChrome>
    );
  } else if (route === "dev") {
    content = (
      <AppChrome activeRoute="dev">
        <DevToolsIndex />
      </AppChrome>
    );
  } else if (route === "tiptap-callout-spike") {
    content = <TiptapSpikeRoute />;
  } else if (route === "plan") {
    content = <PlanSurfacePage />;
  } else if (route === "ingest") {
    content = <MemoryIngestPage />;
  } else if (route === "build") {
    content = <BuildSurfacePage />;
  } else {
    content = <LiveControlApp />;
  }
  return <AgentInteractionProvider>{content}</AgentInteractionProvider>;
}
