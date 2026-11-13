import { useState, useSyncExternalStore } from "react";
import { dungeonMindLoginHref, HostedAuthGate, useHostedAuthStatus } from "./auth/HostedAuthGate";
import {
  getAppLocationSnapshot,
  interceptPrimaryNavigationClick,
  pathnameFromLocationSnapshot,
  subscribeAppLocation,
} from "./chrome/appNavigation";
import {
  SELECTED_WORLD_LOCATION_CHANGED_EVENT,
  SelectedWorldProvider,
  useSelectedWorld,
} from "./selectedWorld/SelectedWorldContext";
import { worldScopedSurfaceHref } from "./selectedWorld/worldSelectionNavigation";
import { WorldSelector } from "./selectedWorld/WorldSelector";
import { SurfaceContextHost } from "./surfaceInteraction/contextHost";
import { deferredComponent } from "./ui/deferredComponent";
import { IsolatedEntry, ManagedWorldGraph } from "./appEntryShared";

const LocalBuddyApp = import.meta.env.VITE_BUDDY_HOSTED_BUILD !== "1" ? deferredComponent(
  () => import("./LocalBuddyApp").then(module => ({ default: module.LocalBuddyApp })),
  "local Buddy",
) : null;

function SelectedWorldApp({ locationSnapshot }: { locationSnapshot: string }) {
  const auth = useHostedAuthStatus();
  return LocalBuddyApp && auth.status === "local_operator"
    ? <LocalBuddyApp locationSnapshot={locationSnapshot} />
    : <IsolatedEntry><HostedBuddy locationSnapshot={locationSnapshot} /></IsolatedEntry>;
}

function subscribeSelectedWorldLocation(onChange: () => void): () => void {
  const unsubscribe = subscribeAppLocation(onChange);
  window.addEventListener(SELECTED_WORLD_LOCATION_CHANGED_EVENT, onChange);
  return () => {
    unsubscribe();
    window.removeEventListener(SELECTED_WORLD_LOCATION_CHANGED_EVENT, onChange);
  };
}

function HostedBuddy({ locationSnapshot }: { readonly locationSnapshot: string }) {
  const auth = useHostedAuthStatus();
  const world = useSelectedWorld();
  const [signingOut, setSigningOut] = useState(false);
  const [signOutError, setSignOutError] = useState(false);
  const path = pathnameFromLocationSnapshot(locationSnapshot);
  const worldId = world.kind === "managed" ? world.worldId : null;
  const signedIn = auth.status === "authenticated";
  const graphHref = worldScopedSurfaceHref("/graph", worldId);

  async function signOut() {
    setSigningOut(true);
    setSignOutError(false);
    try {
      const response = await fetch("/api/auth/logout", {
        method: "POST", credentials: "same-origin", redirect: "error", cache: "no-store",
      });
      if (response.status !== 204) throw new Error("Sign-out failed");
      window.location.replace("/");
    } catch {
      setSignOutError(true);
      setSigningOut(false);
    }
  }

  return (
    <>
      <header className="app-status">
        <nav aria-label="Buddy navigation">
          <a href={worldScopedSurfaceHref("/", worldId)} onClick={interceptPrimaryNavigationClick}>Home</a>
          {" · "}
          <a href={graphHref} onClick={interceptPrimaryNavigationClick}>Graph</a>
        </nav>
        {signedIn && <>
          <WorldSelector compact />
          <details>
            <summary aria-label={`Account: ${auth.displayName ?? auth.subject}`}>
              {auth.displayName ?? auth.subject}
            </summary>
            <button type="button" disabled={signingOut} onClick={() => void signOut()}>
              {signingOut ? "Signing out…" : "Sign out"}
            </button>
            {signOutError && <p role="alert">Sign-out failed. Try again.</p>}
          </details>
        </>}
        <SurfaceContextHost />
      </header>
      {path !== "/" && path !== "/graph" ? (
        <main className="app-status">
          <h1>This page is unavailable on hosted Buddy</h1>
          <a href={graphHref} onClick={interceptPrimaryNavigationClick}>Open Graph</a>
        </main>
      ) : path === "/graph" && signedIn && world.kind === "managed" ? (
        <ManagedWorldGraph key={JSON.stringify([auth.subject, world.worldId])} worldId={world.worldId}
          worldTitle={world.name} stateScopeId={JSON.stringify(["hosted", auth.subject, world.worldId])} />
      ) : (
        <main className="app-status">
          <h1>{path === "/" ? "DungeonMind Buddy" : "Buddy graph playground"}</h1>
          {!signedIn ? (
            <a href={dungeonMindLoginHref(locationSnapshot)}>Sign in with DungeonMind</a>
          ) : world.kind === "loading" ? (
            <p role="status">Verifying World selection…</p>
          ) : world.kind === "error" ? (
            <p role="alert">World selection unavailable</p>
          ) : world.kind === "managed" ? (
            <a href={graphHref} onClick={interceptPrimaryNavigationClick}>Browse {world.name}’s graph</a>
          ) : (
            <p>Choose a World to browse its graph.</p>
          )}
        </main>
      )}
    </>
  );
}

function isCanonicalLocalGuestEntry(locationSnapshot: string): boolean {
  try {
    const url = new URL(locationSnapshot, "http://localhost");
    return (url.pathname === "/" || url.pathname === "/graph") && url.search === "" && url.hash === "";
  } catch {
    return false;
  }
}

export function App() {
  const locationSnapshot = useSyncExternalStore(
    subscribeSelectedWorldLocation,
    getAppLocationSnapshot,
    getAppLocationSnapshot,
  );
  return (
    <HostedAuthGate
      enabled={import.meta.env.PROD}
      allowSignedOutChildren={import.meta.env.PROD && isCanonicalLocalGuestEntry(locationSnapshot)}
    >
      <SelectedWorldProvider locationSnapshot={locationSnapshot}>
        <SelectedWorldApp locationSnapshot={locationSnapshot} />
      </SelectedWorldProvider>
    </HostedAuthGate>
  );
}
