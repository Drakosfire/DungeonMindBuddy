import { useSyncExternalStore } from "react";
import { HostedAuthGate, useHostedAuthStatus } from "./auth/HostedAuthGate";
import { getAppLocationSnapshot, subscribeAppLocation } from "./chrome/appNavigation";
import { SELECTED_WORLD_LOCATION_CHANGED_EVENT, GuestBuildWorldProvider, SelectedWorldProvider } from "./selectedWorld/SelectedWorldContext";
import { deferredComponent } from "./ui/deferredComponent";

const SharedBuddyApp = deferredComponent(
  () => import("./BuddyApp").then(module => ({ default: module.BuddyApp })),
  "Buddy",
);
const GuestReleasePage = deferredComponent(
  () => import("./guestRelease/GuestReleasePage").then(module => ({ default: module.GuestReleasePage })),
  "shared World",
);
const GuestProductGraph = deferredComponent(
  () => import("./guestRelease/GuestProductGraph").then(module => ({ default: module.GuestProductGraph })),
  "shared Graph",
);

function guestReleaseId(locationSnapshot: string): string | null {
  const match = /^\/visit\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:#.*)?$/.exec(locationSnapshot);
  return match?.[1] ?? null;
}

function guestHomeId(): string | null {
  const id = import.meta.env.VITE_GUEST_HOME_PUBLIC_ID;
  return import.meta.env.VITE_GUEST_RELEASE_PAGE === "1" && typeof id === "string"
    && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(id) ? id : null;
}

function isGuestHomeLocation(locationSnapshot: string): boolean {
  try {
    const url = new URL(locationSnapshot, "http://localhost");
    return url.pathname === "/" && url.search === "" &&
      (url.hash === "" || url.hash === "#copy" || url.hash.startsWith("#copy/"));
  } catch {
    return false;
  }
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
    const homeAnchor = url.pathname === "/" && (["", "#buddy-about", "#buddy-home-main"].includes(url.hash)
      || Boolean(guestHomeId()) && isGuestHomeLocation(locationSnapshot));
    const guestBuild = import.meta.env.VITE_HOSTED_GUEST_BUILD === "1" && url.pathname === "/build";
    const guestPlan = import.meta.env.VITE_HOSTED_GUEST_BUILD === "1" && import.meta.env.VITE_HOSTED_GUEST_PLAN === "1" && url.pathname === "/plan";
    return guestBuild || guestPlan || url.search === "" && (homeAnchor || url.pathname === "/graph" && url.hash === "");
  } catch {
    return false;
  }
}

function HomeOrWorld({ locationSnapshot }: { locationSnapshot: string }) {
  const auth = useHostedAuthStatus();
  const publicId = guestHomeId();
  const interactiveGuest = import.meta.env.VITE_HOSTED_GUEST_GRAPH === "1";
  if (!interactiveGuest && auth.status === "signed_out" && publicId && isGuestHomeLocation(locationSnapshot)) {
    return <GuestReleasePage publicId={publicId} home />;
  }
  if (!interactiveGuest && auth.status === "signed_out" && publicId && locationSnapshot === "/graph") {
    return <GuestProductGraph publicId={publicId} />;
  }
  const isGuestBuild = auth.status === "signed_out" && import.meta.env.VITE_HOSTED_GUEST_BUILD === "1"
    && (new URL(locationSnapshot, "http://localhost").pathname === "/build" ||
      import.meta.env.VITE_HOSTED_GUEST_PLAN === "1" && new URL(locationSnapshot, "http://localhost").pathname === "/plan");
  if (isGuestBuild) return <GuestBuildWorldProvider locationSnapshot={locationSnapshot}>
    <SharedBuddyApp locationSnapshot={locationSnapshot} />
  </GuestBuildWorldProvider>;
  return <SelectedWorldProvider locationSnapshot={locationSnapshot}>
    <SharedBuddyApp locationSnapshot={locationSnapshot} />
  </SelectedWorldProvider>;
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
      <HomeOrWorld locationSnapshot={locationSnapshot} />
    </HostedAuthGate>
  );
}
