import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";

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
import { PeekRegionProvider } from "./surfaceInteraction/peekHost";
import { SurfaceContextProvider } from "./surfaceInteraction/contextHost";
import { AppChrome, type AppChromeToolsGeneration } from "./chrome/AppChrome";
import {
  appRouteFromLocationSnapshot,
  getAppLocationSnapshot,
  interceptPrimaryNavigationClick,
  subscribeAppLocation,
} from "./chrome/appNavigation";
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
import { PlaySurfacePage } from "./playSurface/PlaySurfacePage";
import { BuildSurfacePage } from "./buildSurface/BuildSurfacePage";
import { TiptapCalloutBridgeSpike } from "./tiptap/TiptapCalloutBridgeSpike";
import {
  SELECTED_WORLD_LOCATION_CHANGED_EVENT,
  SelectedWorldProvider,
  useRetrySelectedWorld,
  useSelectedWorld,
} from "./selectedWorld/SelectedWorldContext";
import { WorldSelector } from "./selectedWorld/WorldSelector";
import { worldScopedSurfaceHref } from "./selectedWorld/worldSelectionNavigation";

type LoadStatus = "loading" | "ready" | "error";

function subscribeSelectedWorldLocation(onChange: () => void): () => void {
  const unsubscribe = subscribeAppLocation(onChange);
  window.addEventListener(SELECTED_WORLD_LOCATION_CHANGED_EVENT, onChange);
  return () => {
    unsubscribe();
    window.removeEventListener(SELECTED_WORLD_LOCATION_CHANGED_EVENT, onChange);
  };
}

function IndexSurfacePublisher() {
  const context = useMemo(
    () => ({
      surfaceId: "index",
      label: "Command Board",
      campaignId: null,
      documentId: null,
      sessionNumber: null,
      ambientSummary: "Launcher · pick Plan, Play, Ingest, Build, or Combat",
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
  const selectedWorld = useSelectedWorld();
  const worldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  return (
    <main className="launcher-root">
      <IndexSurfacePublisher />
      <header className="launcher-header">
        <h1>Command Board</h1>
        <p>Core surfaces for prep, live play, memory review, worldbuilding, and combat.</p>
      </header>

      <section className="launcher-grid" aria-label="Main surfaces">
        <a className="launcher-card primary" href={worldScopedSurfaceHref("/plan", worldId)} onClick={interceptPrimaryNavigationClick}>
          <span className="launcher-kicker">Plan</span>
          <strong>Prep surface</strong>
          <span>Session prep canvas with reference chips and planning tools.</span>
        </a>
        <a className="launcher-card" href={worldScopedSurfaceHref("/play", worldId)} onClick={interceptPrimaryNavigationClick}>
          <span className="launcher-kicker">Play</span>
          <strong>Runbook table deck</strong>
          <span>Open one exact durable Run and play its bound Runbook.</span>
        </a>
        <a className="launcher-card" href={worldScopedSurfaceHref("/ingest", worldId)} onClick={interceptPrimaryNavigationClick}>
          <span className="launcher-kicker">Ingest</span>
          <strong>Memory review</strong>
          <span>Graph Review workbench for reviewing and committing campaign memory.</span>
        </a>
        <a className="launcher-card" href={worldScopedSurfaceHref("/build", worldId)} onClick={interceptPrimaryNavigationClick}>
          <span className="launcher-kicker">Build</span>
          <strong>Worldbuilding source</strong>
          <span>Create and edit worldbuilding workspace documents.</span>
        </a>
        <a className="launcher-card" href="/combat">
          <span className="launcher-kicker">Combat Tracker</span>
          <strong>North Reach Gate tracker</strong>
          <span>
            Mature command-board combat: circular initiative, HP, statblock
            drilldown, import/export.
          </span>
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

function SelectedWorldApp({ locationSnapshot }: { locationSnapshot: string }) {
  const selectedWorld = useSelectedWorld();
  const retrySelectedWorld = useRetrySelectedWorld();
  if (selectedWorld.kind === "loading") {
    return <main className="app-status" role="status">Verifying World selection…</main>;
  }
  if (selectedWorld.kind === "error") {
    return (
      <main className="app-status app-error" role="alert">
        <h1>World selection unavailable</h1>
        <p>{selectedWorld.message}</p>
        <button type="button" onClick={retrySelectedWorld}>Retry selection</button>
        <WorldSelector />
      </main>
    );
  }
  const route = appRouteFromLocationSnapshot(locationSnapshot);
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
  } else if (route === "play") {
    content = <PlaySurfacePage />;
  } else if (route === "ingest") {
    // Graph Review reads its exact-run handoff at mount. Back/forward that
    // changes or clears that identity must replace the old review controller.
    const params = new URLSearchParams(new URL(locationSnapshot, "http://localhost").search);
    content = <MemoryIngestPage key={[
      params.get("extractionRunId") ?? "",
      params.get("sourceArtifactId") ?? "",
      params.get("documentId") ?? "",
      params.get("revision") ?? "",
    ].join("::")} />;
  } else if (route === "build") {
    content = <BuildSurfacePage />;
  } else {
    content = <LiveControlApp />;
  }
  return (
    <AgentInteractionProvider>
      <AskPluginSlotProvider>
        <WorldGraphLensProvider
          key={selectedWorld.kind === "managed" ? selectedWorld.worldId : "legacy"}
          planCampaignId={WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID}
          managedWorldId={selectedWorld.kind === "managed" ? selectedWorld.worldId : null}
        >
          <WorldGraphLensProjectionProvider defaultCampaignId={WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID}>
            <SurfaceContextProvider>
              <PeekRegionProvider key={selectedWorld.kind === "managed" ? selectedWorld.worldId : "legacy"}>
                {content}
                <ToolHost />
                <LegacyProjectionHostAdapter />
                <AgentInteractionChrome />
              </PeekRegionProvider>
            </SurfaceContextProvider>
          </WorldGraphLensProjectionProvider>
        </WorldGraphLensProvider>
      </AskPluginSlotProvider>
    </AgentInteractionProvider>
  );
}

export function App() {
  const locationSnapshot = useSyncExternalStore(
    subscribeSelectedWorldLocation,
    getAppLocationSnapshot,
    getAppLocationSnapshot,
  );
  return (
    <SelectedWorldProvider locationSnapshot={locationSnapshot}>
      <SelectedWorldApp locationSnapshot={locationSnapshot} />
    </SelectedWorldProvider>
  );
}
