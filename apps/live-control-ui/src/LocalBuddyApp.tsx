import "./statblocks/render/statblockCampaignTheme.css";
import { useMemo, useState, type ReactNode } from "react";

import { createBuddyIndexGraphApi } from "./nativeGraphDemo/buddyIndexGraphApi";
import { AppChrome } from "./chrome/AppChrome";
import {
  appRouteFromLocationSnapshot,
  interceptPrimaryNavigationClick,
} from "./chrome/appNavigation";
import { worldScopedSurfaceHref } from "./selectedWorld/worldSelectionNavigation";
import { APP_NAV_ITEMS } from "./chrome/appChromeConfig";
import { deferredComponent } from "./ui/deferredComponent";
import { dungeonMindLoginHref, useHostedAuthStatus } from "./auth/HostedAuthGate";

import {
  useRetrySelectedWorld,
  useSelectedWorldAdmission,
  useSelectedWorld,
} from "./selectedWorld/SelectedWorldContext";
import { WorldSelector } from "./selectedWorld/WorldSelector";

import { IsolatedEntry, ManagedWorldGraph, NativeGraphDemo } from "./appEntryShared";

const LocalWorkspace = deferredComponent(
  () => import("./LocalWorkspace").then(module => ({ default: module.LocalWorkspace })),
  "World workspace",
);
const LiveControlApp = deferredComponent(
  () => import("./LiveControlApp").then(module => ({ default: module.LiveControlApp })),
  "Live Control",
);
const LocalWorldSurface = deferredComponent(
  () => import("./localWorld/localWorldSurface/LocalWorldSurface").then(module => ({ default: module.LocalWorldSurface })),
  "local World",
);
const PlanSurfacePage = deferredComponent(() => import("./planSurface/PlanSurfacePage").then(module => ({ default: module.PlanSurfacePage })), "Plan");
const PlaySurfacePage = deferredComponent(() => import("./playSurface/PlaySurfacePage").then(module => ({ default: module.PlaySurfacePage })), "Play");
const BuildSurfacePage = deferredComponent(() => import("./buildSurface/BuildSurfacePage").then(module => ({ default: module.BuildSurfacePage })), "Build");
const StatblockPage = deferredComponent(() => import("./statblocks/StatblockPage").then(module => ({ default: module.StatblockPage })), "Statblock");
const CombatSurfacePage = deferredComponent(() => import("./combat/CombatSurfacePage").then(module => ({ default: module.CombatSurfacePage })), "Combat");
const MemoryIngestPage = deferredComponent(() => import("./ingestSurface/MemoryIngestPage").then(module => ({ default: module.MemoryIngestPage })), "Ingest");
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
  return <LocalWorkspace route={route} pageAdmitted={pageAdmitted}>{content}</LocalWorkspace>;
}
