import { useEffect, useState, type ReactNode } from "react";

import {
  GraphReviewAuthorNodeDrawer,
  consumeLegacyAuthorDraftToolQuery,
} from "./GraphReviewAuthorNodeDrawer";
import { authorNodeProjectionReady } from "./GraphReviewAuthorNodePanel";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";

interface GraphReviewAuthorNodeHostProps {
  onRequestLoad: () => void;
  /** Always visible chrome (empty states, session toolbar). */
  chrome: ReactNode;
  /** Read-only main projection; hidden while Author Node shows TipTap workspace. */
  projection?: ReactNode;
}

/**
 * Owns Author Node drawer open state and hides the read-only main projection
 * while the authorable TipTap workspace is showing.
 */
export function GraphReviewAuthorNodeHost({
  onRequestLoad,
  chrome,
  projection = null,
}: GraphReviewAuthorNodeHostProps) {
  const [open, setOpen] = useState(false);
  const { projectionStatus, projection: liveProjection, liveRun } =
    useGraphReviewLiveState();

  useEffect(() => {
    if (consumeLegacyAuthorDraftToolQuery()) {
      setOpen(true);
    }
  }, []);

  const hideMain =
    open &&
    authorNodeProjectionReady({
      projectionStatus,
      projection: liveProjection,
      liveRun,
    });

  return (
    <>
      {chrome}
      {hideMain ? null : projection}
      <GraphReviewAuthorNodeDrawer
        open={open}
        onOpenChange={setOpen}
        onRequestLoad={onRequestLoad}
      />
    </>
  );
}
