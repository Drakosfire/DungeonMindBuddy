import {SavedStatblockProvider} from './statblocks/SavedStatblockSession';
import {WorldGuidedTour} from './guidedTour/WorldGuidedTour';
import { DocumentReferenceSurfaceHost } from './documentReference/DocumentReferenceSurfaceHost';
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

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
import { createBuddyIndexGraphApi } from "./nativeGraphDemo/buddyIndexGraphApi";
import { usePublishSurfaceInteraction } from "./agentInteraction/usePublishSurfaceInteraction";
import {
  ROUTE_COMPATIBILITY_PUBLICATIONS,
} from "./agentInteraction/surfaceInteractionCompat";
import { LegacyProjectionHostAdapter } from "./planSurface/projection/LegacyProjectionHostAdapter";
import { ToolHost } from "./surfaceInteraction/toolHost/ToolHost";
import { PeekRegionProvider } from "./surfaceInteraction/peekHost";
import { SurfaceContextProvider } from "./surfaceInteraction/contextHost";
import { AppChrome } from "./chrome/AppChrome";
import {
  appRouteFromLocationSnapshot,
  interceptPrimaryNavigationClick,
} from "./chrome/appNavigation";
import { worldScopedSurfaceHref } from "./selectedWorld/worldSelectionNavigation";
import { APP_NAV_ITEMS, WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID } from "./chrome/appChromeConfig";
import {
  WorldGraphLensProvider,
  WorldGraphLensProjectionProvider,
} from "./graphLens";

import type { InspectorPaneState } from "./surface/InspectorPane";
import { deferredComponent } from "./ui/deferredComponent";
import { dungeonMindLoginHref, useHostedAuthStatus } from "./auth/HostedAuthGate";

import type { PaneTarget } from "./surface/targetTypes";

import {
  useRetrySelectedWorld,
  useSelectedWorldAdmission,
  useSelectedWorld,
} from "./selectedWorld/SelectedWorldContext";
import { WorldSelector } from "./selectedWorld/WorldSelector";

import { IsolatedEntry, ManagedWorldGraph, NativeGraphDemo } from "./appEntryShared";

const LocalWorldSurface = deferredComponent(
  () => import("./localWorld/localWorldSurface/LocalWorldSurface").then(module => ({ default: module.LocalWorldSurface })),
  "local World",
);
const SurfaceShell = deferredComponent(() => import("./surface/SurfaceShell").then(module => ({ default: module.SurfaceShell })), "surface");
const PlanSurfacePage = deferredComponent(() => import("./planSurface/PlanSurfacePage").then(module => ({ default: module.PlanSurfacePage })), "Plan");
const PlaySurfacePage = deferredComponent(() => import("./playSurface/PlaySurfacePage").then(module => ({ default: module.PlaySurfacePage })), "Play");
const BuildSurfacePage = deferredComponent(() => import("./buildSurface/BuildSurfacePage").then(module => ({ default: module.BuildSurfacePage })), "Build");
const StatblockPage = deferredComponent(() => import("./statblocks/StatblockPage").then(module => ({ default: module.StatblockPage })), "Statblock");
const CombatSurfacePage = deferredComponent(() => import("./combat/CombatSurfacePage").then(module => ({ default: module.CombatSurfacePage })), "Combat");
const MemoryIngestPage = deferredComponent(() => import("./ingestSurface/MemoryIngestPage").then(module => ({ default: module.MemoryIngestPage })), "Ingest");
const InspectorPane = deferredComponent(() => import("./surface/InspectorPane").then(module => ({ default: module.InspectorPane })), "inspector");

type LoadStatus = "loading" | "ready" | "error";

function SurfaceRouteLeasePublisher() {
  usePublishSurfaceInteraction(ROUTE_COMPATIBILITY_PUBLICATIONS.surface);
  return null;
}

function BuddyLandingPage() {
  const world = useSelectedWorld();
  const auth = useHostedAuthStatus();
  return (
    <AppChrome activeRoute="index" localOnlyNavigation={auth.status === "signed_out"} workspaceLayout="bounded">
      <main className="app-status">
        <h1>DungeonMind Buddy</h1>
        {auth.status === "signed_out" && <a href={dungeonMindLoginHref("/")}>Sign in with DungeonMind</a>}
        <ul>
          {APP_NAV_ITEMS.filter((item) => item.route !== "index").map((item) => (
            <li key={item.href}>
              <a href={world.kind === "managed" ? worldScopedSurfaceHref(item.href, world.worldId) : item.href}
                onClick={interceptPrimaryNavigationClick}>{item.label}</a>
            </li>
          ))}
        </ul>
      </main>
    </AppChrome>
  );
}

function BuddyGraphPage({
  localOnlyNavigation = false,
  locationSnapshot,
}: {
  readonly localOnlyNavigation?: boolean;
  readonly locationSnapshot: string;
}) {
  const auth = useHostedAuthStatus();
  const selectedWorld = useSelectedWorld();
  const admitted = auth.status === "local_operator" || auth.status === "authenticated" && auth.subject !== null;
  const managedWorldId = admitted && selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const stateScopeId = auth.status === "authenticated"
    ? JSON.stringify(["hosted", auth.subject, managedWorldId])
    : `managed:${managedWorldId}`;
  const playgroundApi = useMemo(() => createBuddyIndexGraphApi(), []);
  const [legacyWorldsOpen, setLegacyWorldsOpen] = useState(false);

  let explorer: ReactNode;
  if (managedWorldId && selectedWorld.kind === "managed") {
    explorer = <ManagedWorldGraph key={stateScopeId} worldId={managedWorldId}
      worldTitle={selectedWorld.name} stateScopeId={stateScopeId} />;
  } else if (auth.status === "local_operator") {
    explorer = <NativeGraphDemo api={playgroundApi} embedded mode="playground" />;
  } else if (auth.status === "signed_out") {
    explorer = <main className="app-status" aria-labelledby="buddy-playground-title">
      <p className="module-muted">BUDDY · PLAYGROUND</p>
      <h1 id="buddy-playground-title">Buddy graph playground</h1>
      <p>The hosted service does not expose the local-only playground graph. Sign in to load a managed World’s native graph.</p>
      <a href={dungeonMindLoginHref(locationSnapshot)}>Sign in with DungeonMind</a>
    </main>;
  } else {
    explorer = <main className="app-status" aria-labelledby="buddy-playground-title">
      <p className="module-muted">BUDDY · PLAYGROUND</p>
      <h1 id="buddy-playground-title">Buddy graph playground</h1>
      <p>Choose a managed World in the navigation above to load its native graph. The synthetic playground is available on local Buddy deployments only.</p>
    </main>;
  }

  return (
    <AppChrome activeRoute="graph" localOnlyNavigation={localOnlyNavigation} workspaceLayout="bounded">
      {explorer}
      <details className="buddy-index-legacy" onToggle={(event) => setLegacyWorldsOpen(event.currentTarget.open)}>
        <summary>Existing browser-only Worlds and notes</summary>
        <p>These older Worlds stay in this browser and remain separate from the private DungeonMind graph above. Opening them does not migrate or publish them.</p>
        {legacyWorldsOpen
          ? <LocalWorldSurface />
          : null}
      </details>
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

export function LocalBuddyApp({ locationSnapshot }: { locationSnapshot: string }) {
  const selectedWorld = useSelectedWorld();
  const retrySelectedWorld = useRetrySelectedWorld();
  const admission = useSelectedWorldAdmission();
  const route = appRouteFromLocationSnapshot(locationSnapshot);
  if (route === "index") return <IsolatedEntry><BuddyLandingPage /></IsolatedEntry>;
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
  if (route === "graph" && selectedWorld.kind === "legacy") {
    return <IsolatedEntry>
      <BuddyGraphPage locationSnapshot={locationSnapshot} />
    </IsolatedEntry>;
  }
  const pageAdmitted = admission.kind !== "loading";
  let content;
  if (!pageAdmitted) {
    content = <main className="app-status" role="status">Verifying page selection…</main>;
  } else if (route === "graph") {
    content = <BuddyGraphPage locationSnapshot={locationSnapshot} />;
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
            loadFocusOptions={pageAdmitted && route !== "graph"}
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
