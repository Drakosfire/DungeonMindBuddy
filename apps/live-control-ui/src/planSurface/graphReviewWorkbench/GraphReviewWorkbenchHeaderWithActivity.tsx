import { useMemo } from "react";

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
}

/**
 * Header + activity strip. Lives inside GraphReviewLiveStateProvider so applied
 * session projection loading can surface without prop-drilling projectionStatus.
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
}: GraphReviewWorkbenchHeaderWithActivityProps) {
  const { projectionStatus, campaignId, sessionId, projectionAuthority } =
    useGraphReviewLiveState();

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

  return (
    <GraphReviewWorkbenchHeader
      loaded={loaded}
      sessionLabel={sessionLabel}
      onOpenLoad={onOpenLoad}
      activity={activity}
      inMemory={hasAppliedLoad && projectionAuthority === "world_graph"}
    />
  );
}
