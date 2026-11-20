import { useSyncExternalStore } from "react";
import { HostedAuthGate } from "./auth/HostedAuthGate";
import { getAppLocationSnapshot, subscribeAppLocation } from "./chrome/appNavigation";
import { SELECTED_WORLD_LOCATION_CHANGED_EVENT, SelectedWorldProvider } from "./selectedWorld/SelectedWorldContext";
import { deferredComponent } from "./ui/deferredComponent";

const SharedBuddyApp = deferredComponent(
  () => import("./BuddyApp").then(module => ({ default: module.BuddyApp })),
  "Buddy",
);

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
