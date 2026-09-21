import type { ReactNode } from "react";

import { GraphReviewAuthorDraftWorkspace } from "./GraphReviewAuthorDraftWorkspace";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";

export function authorNodeProjectionReady(args: {
  projectionStatus: string;
  projection: unknown;
  liveRun: unknown;
}): boolean {
  return (
    args.projectionStatus === "ready" &&
    Boolean(args.projection) &&
    Boolean(args.liveRun)
  );
}

export type GraphReviewAuthorNodeMode = "exact-run" | "published-local";

export function GraphReviewAuthorNodePanel(props: {
  onRequestLoad?: () => void;
  mode?: GraphReviewAuthorNodeMode;
  publishedLocalPanel?: ReactNode;
} = {}) {
  if (props.mode === "published-local") {
    return (
      <section
        className="graph-review-author-node-panel graph-review-author-node-panel--published-local"
        aria-label="Published recap local authoring"
        data-testid="graph-review-published-local-author-node-panel"
      >
        {props.publishedLocalPanel ?? (
          <div className="plan-projection-empty" data-testid="graph-review-author-node-empty">
            Published recap authoring is unavailable for this source.
          </div>
        )}
      </section>
    );
  }

  const { projectionStatus, projection, liveRun, projectionError } =
    useGraphReviewLiveState();

  if (!liveRun) {
    return (
      <div
        className="plan-projection-empty graph-review-author-node-empty"
        data-testid="graph-review-author-node-empty"
      >
        <p data-testid="graph-review-author-node-missing-authority">
          Authoring requires an explicit source/run context.
        </p>
      </div>
    );
  }

  if (authorNodeProjectionReady({ projectionStatus, projection, liveRun })) {
    return (
      <section
        className="graph-review-author-node-panel"
        aria-label="Author Node workflow"
        data-testid="graph-review-author-node-panel"
      >
        <GraphReviewAuthorDraftWorkspace />
      </section>
    );
  }

  if (projectionStatus === "loading") {
    return (
      <p className="plan-projection-empty" data-testid="graph-review-author-node-empty">
        Loading projection…
      </p>
    );
  }

  if (projectionStatus === "error") {
    return (
      <p className="plan-projection-empty" data-testid="graph-review-author-node-empty">
        {projectionError ?? "Projection failed to load."}
      </p>
    );
  }

  return (
    <div
      className="plan-projection-empty graph-review-author-node-empty"
      data-testid="graph-review-author-node-empty"
    >
      <p data-testid="graph-review-author-node-missing-authority">
        Authoring requires an explicit source/run context.
      </p>
    </div>
  );
}
