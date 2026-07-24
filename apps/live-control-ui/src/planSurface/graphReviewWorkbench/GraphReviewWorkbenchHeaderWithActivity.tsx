import { useEffect, useMemo, useRef, type ReactNode } from "react";

import { formatReviewCampaignLabel } from "../sessionCampaignContext";
import {
  formatGraphReviewActivityTarget,
  resolveGraphReviewActivity,
  type WarmupStatus,
} from "./graphReviewActivity";
import { GraphReviewWorkbenchHeader } from "./GraphReviewWorkbenchHeader";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";

interface GraphReviewWorkbenchHeaderWithActivityProps {
  loaded: boolean;
  sessionLabel: string | null;
  onOpenLoad: () => void;
  sessionsLoaded: boolean;
  hasAppliedLoad: boolean;
  warmupStatus: WarmupStatus;
  draftCampaignId: string;
  draftSessionId: string;
  /** When set, publish header into AppChrome surface slot and render nothing in-page. */
  onSurfaceChromeChange?: (chrome: ReactNode) => void;
}

/**
 * Header + activity strip. Lives inside GraphReviewLiveStateProvider so applied
 * session projection loading can surface without prop-drilling projectionStatus.
 *
 * Surface-chrome publish must not list callback props in the effect deps: parent
 * setState from onSurfaceChromeChange re-renders the workbench, which often
 * recreates onOpenLoad and would otherwise infinite-loop (max update depth).
 */
export function GraphReviewWorkbenchHeaderWithActivity({
  loaded,
  sessionLabel,
  onOpenLoad,
  sessionsLoaded,
  hasAppliedLoad,
  warmupStatus,
  draftCampaignId,
  draftSessionId,
  onSurfaceChromeChange,
}: GraphReviewWorkbenchHeaderWithActivityProps) {
  const { projectionStatus, campaignId, sessionId, projectionAuthority } =
    useGraphReviewLiveState();

  const onSurfaceChromeChangeRef = useRef(onSurfaceChromeChange);
  onSurfaceChromeChangeRef.current = onSurfaceChromeChange;
  const onOpenLoadRef = useRef(onOpenLoad);
  onOpenLoadRef.current = onOpenLoad;

  const activity = useMemo(() => {
    const warmupTargetLabel = formatGraphReviewActivityTarget(
      formatReviewCampaignLabel(draftCampaignId),
      draftSessionId,
    );
    const appliedTargetLabel = formatGraphReviewActivityTarget(
      formatReviewCampaignLabel(campaignId),
      sessionId,
    );
    return resolveGraphReviewActivity({
      sessionsLoaded,
      hasAppliedLoad,
      warmupStatus,
      warmupTargetLabel,
      projectionStatus: hasAppliedLoad ? projectionStatus : null,
      appliedTargetLabel,
    });
  }, [
    campaignId,
    draftCampaignId,
    draftSessionId,
    hasAppliedLoad,
    projectionStatus,
    sessionId,
    sessionsLoaded,
    warmupStatus,
  ]);

  const inMemory = hasAppliedLoad && projectionAuthority === "world_graph";

  useEffect(() => {
    const publish = onSurfaceChromeChangeRef.current;
    if (!publish) return;
    publish(
      <GraphReviewWorkbenchHeader
        loaded={loaded}
        sessionLabel={sessionLabel}
        onOpenLoad={() => onOpenLoadRef.current()}
        activity={activity}
        inMemory={inMemory}
      />,
    );
    return () => {
      onSurfaceChromeChangeRef.current?.(null);
    };
  }, [activity, inMemory, loaded, sessionLabel]);

  if (onSurfaceChromeChange) {
    return null;
  }

  return (
    <GraphReviewWorkbenchHeader
      loaded={loaded}
      sessionLabel={sessionLabel}
      onOpenLoad={onOpenLoad}
      activity={activity}
      inMemory={inMemory}
    />
  );
}
