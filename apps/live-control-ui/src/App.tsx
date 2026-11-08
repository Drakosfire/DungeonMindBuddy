import {SavedStatblockProvider} from './statblocks/SavedStatblockSession';
import {WorldGuidedTour} from './guidedTour/WorldGuidedTour';
import { DocumentReferenceSurfaceHost } from './documentReference/DocumentReferenceSurfaceHost';
import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

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
import { WorldAgentConversation, WorldAgentConversationProvider } from "./agentInteraction/WorldAgentConversation";
import { AskPluginSlotProvider } from "./agentInteraction/AskPluginSlot";
import { AgentInteractionChrome } from "./agentInteraction/AgentInteractionChrome";
import { IndexAgentConversation } from "./agentInteraction/IndexAgentConversation";
import { LocalWorldSurface } from "./localWorld/localWorldSurface/LocalWorldSurface";
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
  subscribeAppLocation,
} from "./chrome/appNavigation";
import { WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID } from "./chrome/appChromeConfig";
import {
  WorldGraphLensProvider,
  WorldGraphLensProjectionProvider,
} from "./graphLens";

import type { InspectorPaneState } from "./surface/InspectorPane";
import { deferredComponent } from "./ui/deferredComponent";
import { HostedAuthGate } from "./auth/HostedAuthGate";

import type { PaneTarget } from "./surface/targetTypes";

import {
  SELECTED_WORLD_LOCATION_CHANGED_EVENT,
  SelectedWorldProvider,
  useRetrySelectedWorld,
  useSelectedWorldAdmission,
  useSelectedWorld,
} from "./selectedWorld/SelectedWorldContext";
import { WorldSelector } from "./selectedWorld/WorldSelector";

const SurfaceShell = deferredComponent(() => import("./surface/SurfaceShell").then(module => ({ default: module.SurfaceShell })), "surface");
const PlanSurfacePage = deferredComponent(() => import("./planSurface/PlanSurfacePage").then(module => ({ default: module.PlanSurfacePage })), "Plan");
const PlaySurfacePage = deferredComponent(() => import("./playSurface/PlaySurfacePage").then(module => ({ default: module.PlaySurfacePage })), "Play");
const BuildSurfacePage = deferredComponent(() => import("./buildSurface/BuildSurfacePage").then(module => ({ default: module.BuildSurfacePage })), "Build");
const StatblockPage = deferredComponent(() => import("./statblocks/StatblockPage").then(module => ({ default: module.StatblockPage })), "Statblock");
const CombatSurfacePage = deferredComponent(() => import("./combat/CombatSurfacePage").then(module => ({ default: module.CombatSurfacePage })), "Combat");
const MemoryIngestPage = deferredComponent(() => import("./ingestSurface/MemoryIngestPage").then(module => ({ default: module.MemoryIngestPage })), "Ingest");
const TiptapCalloutBridgeSpike = deferredComponent(() => import("./tiptap/TiptapCalloutBridgeSpike").then(module => ({ default: module.TiptapCalloutBridgeSpike })), "editor");
const InspectorPane = deferredComponent(() => import("./surface/InspectorPane").then(module => ({ default: module.InspectorPane })), "inspector");

type LoadStatus = "loading" | "ready" | "error";

function subscribeSelectedWorldLocation(onChange: () => void): () => void {
  const unsubscribe = subscribeAppLocation(onChange);
  window.addEventListener(SELECTED_WORLD_LOCATION_CHANGED_EVENT, onChange);
  return () => {
    unsubscribe();
    window.removeEventListener(SELECTED_WORLD_LOCATION_CHANGED_EVENT, onChange);
  };
}

function SurfaceRouteLeasePublisher() {
  usePublishSurfaceInteraction(ROUTE_COMPATIBILITY_PUBLICATIONS.surface);
  return null;
}

function TiptapSpikeRouteLeasePublisher() {
  usePublishSurfaceInteraction(ROUTE_COMPATIBILITY_PUBLICATIONS.tiptapCalloutSpike);
  return null;
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
            For local development only, start L3 with explicit loopback-bound operator mode:{" "}
            <code>
              DMB_DEPLOYMENT_ENVIRONMENT=local DMB_AUTH_MODE=local_operator uv run uvicorn{" "}
              apps.live_control_server.main:app --reload --host 127.0.0.1
            </code>{" "}
            and ensure session files are available.
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
  const admission = useSelectedWorldAdmission();
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
  const pageAdmitted = admission.kind !== "loading";
  let content;
  if (!pageAdmitted) {
    content = <main className="app-status" role="status">Verifying page selection…</main>;
  } else if (route === "index") {
    content = (
      <AppChrome activeRoute="index">
        <LocalWorldSurface>
          <IndexAgentConversation />
        </LocalWorldSurface>
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
  } else if (route === "combat") {
    content = <CombatSurfacePage />;
  } else if (route === "statblock") {
    content = <StatblockPage />;
  } else if (route === "build") {
    content = <BuildSurfacePage />;
  } else {
    content = <LiveControlApp />;
  }
  return (
    <AgentInteractionProvider>
      <AskPluginSlotProvider>
        <WorldAgentConversationProvider key={selectedWorld.kind === "managed" ? selectedWorld.worldId : "legacy"}
          worldId={selectedWorld.kind === "managed" ? selectedWorld.worldId : null}>
          <WorldGuidedTour worldId={selectedWorld.kind === "managed" ? selectedWorld.worldId : null} worldName={selectedWorld.kind === "managed" ? selectedWorld.name : undefined}>
          <WorldGraphLensProvider
            key={selectedWorld.kind === "managed" ? selectedWorld.worldId : "legacy"}
            loadFocusOptions={pageAdmitted && route !== "index"}
            planCampaignId={WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID}
            managedWorldId={selectedWorld.kind === "managed" ? selectedWorld.worldId : null}
          >
            <WorldGraphLensProjectionProvider defaultCampaignId={WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID}>
              <SavedStatblockProvider worldId={selectedWorld.kind === 'managed' ? selectedWorld.worldId : null}>
              <SurfaceContextProvider>
                <PeekRegionProvider key={selectedWorld.kind === "managed" ? selectedWorld.worldId : "legacy"}>
                  <DocumentReferenceSurfaceHost worldId={selectedWorld.kind === "managed" ? selectedWorld.worldId : null} surface={pageAdmitted ? route : "pending"}>
                  {content}
                  {pageAdmitted ? <>
                    <ToolHost />
                    <LegacyProjectionHostAdapter />
                    <AgentInteractionChrome />
                  </> : null}
                  <WorldAgentConversation surface={pageAdmitted && (route === "plan" || route === "play" || route === "build") ? route : "other"}
                    worldId={selectedWorld.kind === "managed" ? selectedWorld.worldId : null}
                    worldName={selectedWorld.kind === "managed" ? selectedWorld.name : undefined} />
                  </DocumentReferenceSurfaceHost>
                </PeekRegionProvider>
              </SurfaceContextProvider>
              </SavedStatblockProvider>
            </WorldGraphLensProjectionProvider>
          </WorldGraphLensProvider>
          </WorldGuidedTour>
        </WorldAgentConversationProvider>
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
    <HostedAuthGate enabled={import.meta.env.PROD}>
      <SelectedWorldProvider locationSnapshot={locationSnapshot}>
        <SelectedWorldApp locationSnapshot={locationSnapshot} />
      </SelectedWorldProvider>
    </HostedAuthGate>
  );
}
