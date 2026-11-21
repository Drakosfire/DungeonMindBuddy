import { useSyncExternalStore } from "react";
import { HostedAuthGate } from "./auth/HostedAuthGate";
import { getAppLocationSnapshot, subscribeAppLocation } from "./chrome/appNavigation";
import { SELECTED_WORLD_LOCATION_CHANGED_EVENT, SelectedWorldProvider } from "./selectedWorld/SelectedWorldContext";
import { deferredComponent } from "./ui/deferredComponent";

const SharedBuddyApp = deferredComponent(
  () => import("./BuddyApp").then(module => ({ default: module.BuddyApp })),
  "Buddy",
);
const GuestReleasePage = deferredComponent(
  () => import("./guestRelease/GuestReleasePage").then(module => ({ default: module.GuestReleasePage })),
  "shared World",
);

function guestReleaseId(locationSnapshot: string): string | null {
  const match = /^\/visit\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:#.*)?$/.exec(locationSnapshot);
  return match?.[1] ?? null;
}

function subscribeSelectedWorldLocation(onChange: () => void): () => void {
  const unsubscribe = subscribeAppLocation(onChange);
  window.addEventListener(SELECTED_WORLD_LOCATION_CHANGED_EVENT, onChange);
  return () => {
    unsubscribe();
    window.removeEventListener(SELECTED_WORLD_LOCATION_CHANGED_EVENT, onChange);
  };
}

function isCanonicalLocalGuestEntry(locationSnapshot: string): boolean {
  try {
    const url = new URL(locationSnapshot, "http://localhost");
    const homeAnchor = url.pathname === "/" && ["", "#buddy-about", "#buddy-home-main"].includes(url.hash);
    return url.search === "" && (homeAnchor || url.pathname === "/graph" && url.hash === "");
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
  const guestId = guestReleaseId(locationSnapshot);
  if (guestId && import.meta.env.VITE_GUEST_RELEASE_PAGE === "1") return <GuestReleasePage publicId={guestId} />;
  return (
    <HostedAuthGate
      enabled={import.meta.env.PROD}
      allowSignedOutChildren={import.meta.env.PROD && isCanonicalLocalGuestEntry(locationSnapshot)}
    >
      <SelectedWorldProvider locationSnapshot={locationSnapshot}>
        <SharedBuddyApp locationSnapshot={locationSnapshot} />
      </SelectedWorldProvider>
    </HostedAuthGate>
  );
}
