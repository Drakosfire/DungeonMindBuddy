import { GuestReleaseReview } from "./GuestReleaseReview";

/** Owner review overlays the graph instead of taking its bounded workspace. */
export function GuestReleaseDrawer({ worldId }: { worldId: string }) {
  return <details className="guest-release-drawer">
    <summary><span className="guest-release-drawer-open">Review guest copy</span><span className="guest-release-drawer-close">Close guest review</span></summary>
    <GuestReleaseReview worldId={worldId} />
  </details>;
}
