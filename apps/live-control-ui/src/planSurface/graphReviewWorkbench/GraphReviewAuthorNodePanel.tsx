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

export function GraphReviewAuthorNodePanel({
  onRequestLoad,
}: {
  onRequestLoad?: () => void;
}) {
  const { projectionStatus, projection, liveRun, projectionError } =
    useGraphReviewLiveState();

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
        {projectionError ?? "Projection failed to load. Retry from Load recap."}
      </p>
    );
  }

  return (
    <div
      className="plan-projection-empty graph-review-author-node-empty"
      data-testid="graph-review-author-node-empty"
    >
      <p>Load an ingested session to author graph nodes from the projected recap.</p>
      {onRequestLoad ? (
        <button type="button" onClick={onRequestLoad}>
          Load recap
        </button>
      ) : null}
    </div>
  );
}
