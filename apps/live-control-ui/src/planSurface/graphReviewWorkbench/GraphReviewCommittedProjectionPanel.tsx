import { useCallback, useMemo, useState } from "react";

import type { ExtractPromoteConfirmReceipt, WorldGraphProjection } from "../../api/types";
import {
  GraphObjectProjectionCard,
  resolveExactProjectedNode,
} from "../../graphObjectCard/GraphObjectProjectionCard";
import { adaptWorldGraphNodeView } from "../../worldGraph/worldGraphNodeViewAdapter";
import type { GraphReviewCommittedPhase } from "./graphReviewCommittedAuthority";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";

function adaptProjectionNodeMap(projection: WorldGraphProjection) {
  return Object.fromEntries(
    projection.nodes.map((node) => [node.nodeId, adaptWorldGraphNodeView(node)]),
  );
}

function outcomeLabel(outcome: ExtractPromoteConfirmReceipt["outcome"]): string {
  switch (outcome) {
    case "committed":
      return "Committed";
    case "already_applied":
      return "Already applied";
    case "published_audit_degraded":
      return "Committed with degraded audit";
    default:
      return outcome;
  }
}

export interface GraphReviewCommittedProjectionPanelProps {
  /** Optional controlled overrides for isolated unit tests. */
  phase?: GraphReviewCommittedPhase;
  receipt?: ExtractPromoteConfirmReceipt | null;
  projection?: WorldGraphProjection | null;
  selectedObjectId?: string | null;
  affectedObjectIds?: string[];
  error?: string | null;
  onRetry?: () => void | Promise<void>;
  onSelectObjectId?: (objectId: string) => void;
}

export function GraphReviewCommittedProjectionPanel(
  props: GraphReviewCommittedProjectionPanelProps = {},
) {
  const live = useGraphReviewLiveState();
  const phase = props.phase ?? live.committedPhase;
  const receipt = props.receipt ?? live.committedReceipt;
  const projection = props.projection ?? live.committedProjection;
  const selectedObjectId =
    props.selectedObjectId ?? live.committedSelectedObjectId;
  const affectedObjectIds =
    props.affectedObjectIds ?? live.committedAffectedObjectIds;
  const error = props.error ?? live.committedError;
  const onRetry = props.onRetry ?? live.reloadCommittedAuthority;
  const onSelectObjectId =
    props.onSelectObjectId ?? live.setCommittedSelectedObjectId;

  const [selectedRelationshipId, setSelectedRelationshipId] = useState<
    string | null
  >(null);
  const [retrying, setRetrying] = useState(false);

  const nodeViews = useMemo(
    () => (projection ? adaptProjectionNodeMap(projection) : {}),
    [projection],
  );
  const activeNodeView = selectedObjectId
    ? resolveExactProjectedNode(nodeViews, selectedObjectId)
    : null;

  const handleSelectRelationshipTarget = useCallback(
    (targetId: string) => {
      const trimmed = targetId.trim();
      setSelectedRelationshipId(trimmed || null);
      if (trimmed && resolveExactProjectedNode(nodeViews, trimmed)) {
        onSelectObjectId(trimmed);
      }
    },
    [nodeViews, onSelectObjectId],
  );

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await onRetry();
    } finally {
      setRetrying(false);
    }
  };

  if (phase === "candidate") {
    return null;
  }

  return (
    <section
      className="graph-review-committed-projection-panel"
      data-testid="graph-review-committed-projection-panel"
      data-phase={phase}
      aria-label="Committed World Graph projection"
    >
      <header className="graph-review-committed-projection-header">
        <p className="plan-surface-kicker">Committed World Graph</p>
        <h3>
          Exact revision{" "}
          {receipt?.committedRevisionId ??
            projection?.snapshot.revisionId ??
            "—"}
        </h3>
        {receipt ? (
          <dl className="graph-review-lane-meta" data-testid="graph-review-committed-receipt-meta">
            <div>
              <dt>Outcome</dt>
              <dd>{outcomeLabel(receipt.outcome)}</dd>
            </div>
            <div>
              <dt>World</dt>
              <dd>{receipt.worldId}</dd>
            </div>
            <div>
              <dt>Parent → committed</dt>
              <dd>
                {receipt.parentRevisionId} → {receipt.committedRevisionId}
              </dd>
            </div>
            <div>
              <dt>Affected objects</dt>
              <dd>{affectedObjectIds.length ? affectedObjectIds.join(", ") : "—"}</dd>
            </div>
          </dl>
        ) : null}
      </header>

      {phase === "loading" ? (
        <p className="graph-review-live-projection-status" role="status">
          Loading committed World Graph revision…
        </p>
      ) : null}

      {phase === "error" || error ? (
        <div className="graph-review-error" role="alert">
          <p data-testid="graph-review-committed-projection-error">
            {error ?? "Failed to load committed World Graph revision."}
          </p>
          <button
            type="button"
            className="secondary"
            data-testid="graph-review-committed-projection-retry"
            disabled={retrying}
            onClick={() => void handleRetry()}
          >
            {retrying ? "Retrying…" : "Retry committed load"}
          </button>
        </div>
      ) : null}

      {phase === "ready" && projection ? (
        <div className="graph-review-committed-projection-body">
          {affectedObjectIds.length ? (
            <ul
              className="graph-review-committed-object-list"
              data-testid="graph-review-committed-object-list"
            >
              {affectedObjectIds.map((objectId) => {
                const present = Boolean(nodeViews[objectId]);
                return (
                  <li key={objectId}>
                    <button
                      type="button"
                      className={
                        objectId === selectedObjectId
                          ? "graph-review-committed-object-button is-active"
                          : "graph-review-committed-object-button"
                      }
                      data-testid={`graph-review-committed-object-${objectId}`}
                      data-present={present ? "true" : "false"}
                      disabled={!present}
                      onClick={() => {
                        if (present) onSelectObjectId(objectId);
                      }}
                    >
                      {present
                        ? nodeViews[objectId].label
                        : `${objectId} (missing from committed revision)`}
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="module-muted">
              Committed revision loaded with no affected object ids.
            </p>
          )}

          {activeNodeView ? (
            <GraphObjectProjectionCard
              mode="plan"
              nodeView={activeNodeView}
              onSelectRelationshipTarget={handleSelectRelationshipTarget}
              selectedRelationshipId={selectedRelationshipId}
              aria-label={`Committed object ${activeNodeView.label}`}
            />
          ) : selectedObjectId ? (
            <p className="graph-preview-error" role="status">
              Exact object {selectedObjectId} is not present in the pinned World
              Graph revision.
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
