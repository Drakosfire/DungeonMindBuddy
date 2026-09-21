import { useEffect, useState, type ReactNode } from "react";

import {
  GraphReviewAuthorNodeDrawer,
  consumeLegacyAuthorDraftToolQuery,
} from "./GraphReviewAuthorNodeDrawer";
import {
  authorNodeProjectionReady,
  type GraphReviewAuthorNodeMode,
} from "./GraphReviewAuthorNodePanel";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";

interface GraphReviewAuthorNodeHostProps {
  /** Always visible chrome (empty states, session toolbar). */
  chrome?: ReactNode;
  /** Read-only main projection; hidden while Author Node shows TipTap workspace. */
  projection?: ReactNode;
  /** Published recap mode keeps the source projection visible beside local staging. */
  mode?: GraphReviewAuthorNodeMode;
  /** Controlled open state is useful when source selection launches Author Node. */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  publishedLocalPanel?: ReactNode;
  publishedLocalPreview?: ReactNode;
}

/**
 * Owns Author Node drawer open state and hides the read-only main projection
 * while the authorable TipTap workspace is showing.
 */
export function GraphReviewAuthorNodeHost({
  chrome = null,
  projection = null,
  mode = "exact-run",
  open: controlledOpen,
  onOpenChange: controlledOnOpenChange,
  publishedLocalPanel,
  publishedLocalPreview,
}: GraphReviewAuthorNodeHostProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const open = controlledOpen ?? internalOpen;
  const setOpen = controlledOnOpenChange ?? setInternalOpen;

  useEffect(() => {
    if (consumeLegacyAuthorDraftToolQuery()) {
      setOpen(true);
    }
  }, []);

  if (mode === "published-local") {
    return (
      <GraphReviewPublishedAuthorNodeHostContent
        chrome={chrome}
        projection={projection}
        open={open}
        onOpenChange={setOpen}
        publishedLocalPanel={publishedLocalPanel}
        publishedLocalPreview={publishedLocalPreview}
      />
    );
  }

  return (
    <GraphReviewExactAuthorNodeHostContent
      chrome={chrome}
      projection={projection}
      open={open}
      onOpenChange={setOpen}
      publishedLocalPanel={publishedLocalPanel}
    />
  );
}

function GraphReviewPublishedAuthorNodeHostContent({
  chrome,
  projection,
  open,
  onOpenChange,
  publishedLocalPanel,
  publishedLocalPreview,
}: Omit<GraphReviewAuthorNodeHostProps, "mode" | "open" | "onOpenChange"> & {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <>
      {chrome}
      {projection}
      <GraphReviewAuthorNodeDrawer
        open={open}
        onOpenChange={onOpenChange}
        mode="published-local"
        publishedLocalPanel={publishedLocalPanel}
        publishedLocalPreview={publishedLocalPreview}
      />
    </>
  );
}

function GraphReviewExactAuthorNodeHostContent({
  chrome,
  projection,
  open,
  onOpenChange,
  publishedLocalPanel,
}: Omit<GraphReviewAuthorNodeHostProps, "mode" | "open" | "onOpenChange"> & {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { projectionStatus, projection: liveProjection, liveRun } =
    useGraphReviewLiveState();
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
        onOpenChange={onOpenChange}
        mode="exact-run"
        publishedLocalPanel={publishedLocalPanel}
      />
    </>
  );
}
