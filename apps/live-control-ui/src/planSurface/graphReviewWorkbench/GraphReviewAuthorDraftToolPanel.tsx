import { useEffect } from "react";

import { useProjection } from "../projection/projectionContext";
import { GraphReviewAuthoringPreparePreviewPanel } from "./GraphReviewAuthoringPreparePreviewPanel";
import { GraphReviewLocalStagingTray } from "./GraphReviewLocalStagingTray";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";

export function GraphReviewAuthorDraftToolPanel() {
  const { close } = useProjection();
  const {
    campaignId,
    sessionId,
    hasGold,
    projectionStatus,
    goldProjection,
    authorDraft,
    stageNodeFromSelection,
    reloadGoldProjectionAndVerifyCommit,
    selectGoldNodeCard,
  } = useGraphReviewLiveState();

  const { authorMode } = authorDraft;

  useEffect(() => {
    authorDraft.setAuthorMode("author_draft");
    return () => {
      authorDraft.setAuthorMode("review");
    };
  }, [authorDraft.setAuthorMode]);

  if (projectionStatus !== "ready") {
    return (
      <p className="plan-projection-empty">
        Select a live run with a projection before authoring draft corrections.
      </p>
    );
  }

  return (
    <section
      className="graph-review-author-draft-tool-panel"
      aria-label="Author Draft workflow"
    >
      <div
        className="graph-review-author-draft-mode-bar"
        aria-label="Author Draft mode"
      >
        <p className="graph-review-author-draft-mode-note">
          Author Draft lives in the toolbox for now. Staged proposals stay local
          until prepare and commit.
        </p>
        <button
          type="button"
          onClick={() => {
            authorDraft.setAuthorMode("review");
            close();
          }}
        >
          Return to review
        </button>
        {authorMode === "author_draft" ? (
          <strong>
            Draft only. No gold fixture, graph state, or corpus file has been
            changed.
          </strong>
        ) : null}
      </div>

      <section
        className="graph-review-author-draft-actions"
        aria-label="Author Draft text-selection actions"
      >
        <h3>Author Draft text-selection actions</h3>
        <p>Local staging is ephemeral and not saved.</p>
        <button
          type="button"
          onClick={stageNodeFromSelection}
          disabled={!authorDraft.selectedText?.text.trim()}
        >
          Stage node from selection
        </button>
        {authorDraft.selectedText?.text ? (
          <p>
            Selected {authorDraft.selectedText.laneRole} text: “
            {authorDraft.selectedText.text}” (offset approximate/unanchored)
          </p>
        ) : null}
      </section>

      <GraphReviewLocalStagingTray
        proposals={authorDraft.localProposals}
        onUpdateStatus={authorDraft.updateProposalStatus}
        onReset={authorDraft.resetLocalDraft}
      />
      <GraphReviewAuthoringPreparePreviewPanel
        campaignId={campaignId}
        sessionId={sessionId}
        hasGold={hasGold}
        workflow={authorDraft}
        onReloadAndVerifyCommit={reloadGoldProjectionAndVerifyCommit}
        onShowCommittedObject={(targetId) => {
          selectGoldNodeCard(targetId);
        }}
        canShowCommittedObject={(targetId) =>
          Boolean(goldProjection?.node_views[targetId])
        }
      />
    </section>
  );
}
