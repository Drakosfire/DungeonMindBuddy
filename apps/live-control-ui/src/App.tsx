import { useCallback, useEffect, useMemo, useState } from "react";

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
import { AskPluginSlotProvider } from "./agentInteraction/AskPluginSlot";
import { AgentInteractionChrome } from "./agentInteraction/AgentInteractionChrome";
import { usePublishAgentSurfaceContext } from "./agentInteraction/usePublishAgentSurfaceContext";
import { usePublishSurfaceInteraction } from "./agentInteraction/usePublishSurfaceInteraction";
import {
  ROUTE_COMPATIBILITY_PUBLICATIONS,
} from "./agentInteraction/surfaceInteractionCompat";
import { LegacyProjectionHostAdapter } from "./planSurface/projection/LegacyProjectionHostAdapter";
import { ToolHost } from "./surfaceInteraction/toolHost/ToolHost";
import { SurfaceContextProvider } from "./surfaceInteraction/contextHost";
import { AppChrome, type AppChromeToolsGeneration } from "./chrome/AppChrome";
import { WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID } from "./chrome/appChromeConfig";
import {
  WorldGraphLensProvider,
  WorldGraphLensProjectionProvider,
} from "./graphLens";
import { MemoryIngestPage } from "./ingestSurface/MemoryIngestPage";
import { InspectorPane, type InspectorPaneState } from "./surface/InspectorPane";
import { SurfaceShell } from "./surface/SurfaceShell";
import type { PaneTarget } from "./surface/targetTypes";
import { PlanSurfacePage } from "./planSurface/PlanSurfacePage";
import { BuildSurfacePage } from "./buildSurface/BuildSurfacePage";
import { TiptapCalloutBridgeSpike } from "./tiptap/TiptapCalloutBridgeSpike";
import { PlaySurfacePage } from "./playSurface/PlaySurfacePage";
import { playPanelFromPath } from "./playSurface/playPanels";

type LoadStatus = "loading" | "ready" | "error";
type AppRoute =
  | "index"
  | "surface"
  | "tiptap-callout-spike"
  | "plan"
  | "ingest"
  | "build"
  | "play";

function currentRoute(): AppRoute {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  if (path === "/surface" || path === "/live-control") return "surface";
  if (path === "/tiptap-callout-spike") return "tiptap-callout-spike";
  if (path === "/plan") return "plan";
  if (path === "/ingest") return "ingest";
  if (path === "/build") return "build";
  if (playPanelFromPath(path)) return "play";
  return "index";
}

function IndexSurfacePublisher() {
  const context = useMemo(
    () => ({
      surfaceId: "index",
      label: "Command Board",
      campaignId: null,
      documentId: null,
      sessionNumber: null,
      ambientSummary: "Launcher · pick Plan, Ingest, Build, or Play",
      sourceEnvelope: null,
    }),
    [],
  );
  usePublishAgentSurfaceContext(context);
  usePublishSurfaceInteraction(ROUTE_COMPATIBILITY_PUBLICATIONS.index);
  return null;
}

function SurfaceRouteLeasePublisher() {
  usePublishSurfaceInteraction(ROUTE_COMPATIBILITY_PUBLICATIONS.surface);
  return null;
}

function TiptapSpikeRouteLeasePublisher() {
  usePublishSurfaceInteraction(ROUTE_COMPATIBILITY_PUBLICATIONS.tiptapCalloutSpike);
  return null;
}

function MirewardIndex() {
  return (
    <main className="launcher-root">
      <IndexSurfacePublisher />
      <header className="launcher-header">
        <h1>Command Board</h1>
        <p>Core surfaces for prep, memory review, worldbuilding, and table play.</p>
      </header>

      <section className="launcher-grid" aria-label="Main surfaces">
        <a className="launcher-card primary" href="/plan">
          <span className="launcher-kicker">Plan</span>
          <strong>Prep surface</strong>
          <span>Session prep canvas with reference chips and planning tools.</span>
        </a>
        <a className="launcher-card" href="/ingest">
          <span className="launcher-kicker">Ingest</span>
          <strong>Memory review</strong>
          <span>Graph Review workbench for reviewing and committing campaign memory.</span>
        </a>
        <a className="launcher-card" href="/build">
          <span className="launcher-kicker">Build</span>
          <strong>Worldbuilding source</strong>
          <span>Create and edit worldbuilding workspace documents.</span>
        </a>
        <a className="launcher-card" href="/play">
          <span className="launcher-kicker">Play</span>
          <strong>Table tools</strong>
          <span>Combat, roll tables, items, and statblocks under one World Graph scope.</span>
        </a>
      </section>
    </main>
  );
}

function TiptapSpikeRoute() {
  const [editorTools, setEditorTools] = useState<AppChromeToolsGeneration | null>(null);

  return (
    <AppChrome activeRoute="tiptap-callout-spike" editorTools={editorTools}>
      <TiptapSpikeRouteLeasePublisher />
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
        <SurfaceRouteLeasePublisher />
        <main className="app-status">
          <p>Loading live surface…</p>
        </main>
      </AppChrome>
    );
  }

  if (status === "error" || !layout || !state || !planView) {
    return (
      <AppChrome activeRoute="surface">
        <SurfaceRouteLeasePublisher />
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
      <SurfaceRouteLeasePublisher />
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
        <MirewardIndex />
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
  } else if (route === "play") {
    content = (
      <PlaySurfacePage
        initialPanel={playPanelFromPath(window.location.pathname) ?? "combat"}
      />
    );
  } else {
    content = <LiveControlApp />;
  }
  return (
    <AgentInteractionProvider>
      <AskPluginSlotProvider>
        <WorldGraphLensProvider planCampaignId={WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID}>
          <WorldGraphLensProjectionProvider defaultCampaignId={WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID}>
            <SurfaceContextProvider>
              {content}
              <ToolHost />
              <LegacyProjectionHostAdapter />
              <AgentInteractionChrome />
            </SurfaceContextProvider>
          </WorldGraphLensProjectionProvider>
        </WorldGraphLensProvider>
      </AskPluginSlotProvider>
    </AgentInteractionProvider>
  );
}
