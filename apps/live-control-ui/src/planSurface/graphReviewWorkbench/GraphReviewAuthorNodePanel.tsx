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

export function GraphReviewAuthorNodePanel(_props: {
  onRequestLoad?: () => void;
} = {}) {
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
