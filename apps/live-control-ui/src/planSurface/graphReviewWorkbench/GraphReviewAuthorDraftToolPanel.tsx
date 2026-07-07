import { useEffect } from "react";

import { GraphReviewAuthorDraftWorkspace } from "./GraphReviewAuthorDraftWorkspace";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";

export function GraphReviewAuthorDraftToolPanel() {
  const { projectionStatus, authorDraft } = useGraphReviewLiveState();

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
      <GraphReviewAuthorDraftWorkspace />
    </section>
  );
}
