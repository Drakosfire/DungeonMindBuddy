import { useEffect } from "react";

import type { GoldReviewSessionSummary } from "../../api/types";
import { GraphReviewLanePicker } from "./GraphReviewLanePicker";
import { GraphReviewLoadLaneSummary } from "./GraphReviewLoadLaneSummary";
import { hasReviewableProjection } from "./graphReviewWorkbenchUtils";

interface GraphReviewLoadSurfaceProps {
  open: boolean;
  sessions: GoldReviewSessionSummary[];
  draftCampaignId: string;
  draftSessionId: string;
  draftManifestPath: string | null;
  draftSession: GoldReviewSessionSummary | null;
  draftLiveRun: GoldReviewSessionSummary["available_runs"][number] | null;
  onClose: () => void;
  onLoad: () => void;
  onCampaignSelect: (campaignId: string) => void;
  onSessionSelect: (sessionId: string) => void;
  onManifestSelect: (manifestPath: string | null) => void;
}

export function GraphReviewLoadSurface({
  open,
  sessions,
  draftCampaignId,
  draftSessionId,
  draftManifestPath,
  draftSession,
  draftLiveRun,
  onClose,
  onLoad,
  onCampaignSelect,
  onSessionSelect,
  onManifestSelect,
}: GraphReviewLoadSurfaceProps) {
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const canLoad =
    Boolean(draftSession) &&
    hasReviewableProjection(draftSession!) &&
    Boolean(draftLiveRun?.preview_union_available);

  return (
    <div
      className="graph-review-projected-interaction-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="graph-review-projected-interaction-surface graph-review-load-surface"
        role="dialog"
        aria-modal="true"
        aria-labelledby="graph-review-load-surface-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="graph-review-projected-interaction-header">
          <div>
            <p className="plan-surface-kicker">Load comparison</p>
            <h3 id="graph-review-load-surface-title">Choose session and live run</h3>
          </div>
          <button type="button" aria-label="Close load dialog" onClick={onClose}>
            Close
          </button>
        </header>

        <GraphReviewLanePicker
          sessions={sessions}
          selectedCampaignId={draftCampaignId}
          selectedSessionId={draftSessionId}
          selectedManifestPath={draftManifestPath}
          onCampaignSelect={onCampaignSelect}
          onSessionSelect={onSessionSelect}
          onManifestSelect={onManifestSelect}
        />

        <GraphReviewLoadLaneSummary session={draftSession} liveRun={draftLiveRun} />

        <div className="graph-review-load-surface-actions">
          <button type="button" onClick={onClose}>
            Cancel
          </button>
          <button type="button" onClick={onLoad} disabled={!canLoad}>
            Load
          </button>
        </div>
      </section>
    </div>
  );
}
