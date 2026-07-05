import { useEffect, type ReactNode } from "react";

import type { GraphProjectionAdjacencyCandidate } from "../../api/types";
import { GraphReviewNodeGameCard } from "./GraphReviewNodeGameCard";
import { GraphReviewRelationshipCard } from "./GraphReviewRelationshipCard";
import {
  GRAPH_REVIEW_RELATIONSHIP_PREDICATES,
  type GraphReviewRelationshipPredicate,
} from "./graphReviewLocalAuthoringState";
import {
  findSelectedAdjacency,
  type GraphReviewSelectedNode,
  type GraphReviewSelectedNodeViewModel,
  type GraphReviewSelectedRelationship,
} from "./graphReviewSelectionUtils";

export function GraphReviewProjectedInteractionSurface({
  open,
  selectedNode,
  selectedRelationship,
  authorMode,
  relationshipDraftSource,
  relationshipPredicate,
  resolver,
  onClose,
  onSelectRelationship,
  onSelectEvidenceDelta,
  onStageNodeAssertion,
  onUseAsRelationshipSource,
  onRelationshipPredicateChange,
  onStageRelationship,
}: {
  open: boolean;
  selectedNode: GraphReviewSelectedNodeViewModel | null;
  selectedRelationship: GraphReviewSelectedRelationship | null;
  authorMode: "review" | "author_draft";
  relationshipDraftSource: GraphReviewSelectedNode | null;
  relationshipPredicate: GraphReviewRelationshipPredicate;
  resolver?: ReactNode;
  onClose: () => void;
  onSelectRelationship: (
    relationship: GraphProjectionAdjacencyCandidate,
  ) => void;
  onSelectEvidenceDelta: (deltaId: string | null) => void;
  onStageNodeAssertion: () => void;
  onUseAsRelationshipSource: () => void;
  onRelationshipPredicateChange: (
    predicate: GraphReviewRelationshipPredicate,
  ) => void;
  onStageRelationship: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open || !selectedNode) return null;

  const relationship = findSelectedAdjacency(
    selectedNode.node,
    selectedRelationship,
  );
  const canStageRelationship =
    Boolean(relationshipDraftSource) &&
    (relationshipDraftSource?.laneRole !== selectedNode.laneRole ||
      relationshipDraftSource?.nodeId !== selectedNode.node.node_id);

  return (
    <div className="graph-review-projected-interaction-backdrop">
      <section
        className="graph-review-projected-interaction-surface"
        role="dialog"
        aria-modal="false"
        aria-labelledby="graph-review-projected-interaction-title"
      >
        <header className="graph-review-projected-interaction-header">
          <div>
            <p className="plan-surface-kicker">Selected object</p>
            <h3 id="graph-review-projected-interaction-title">
              {selectedNode.node.label}
            </h3>
            <p>
              <span className="graph-review-lane-badge">
                {selectedNode.laneRole === "gold"
                  ? "Gold Fixture · read-only"
                  : "Live Run · read-only"}
              </span>{" "}
              {[selectedNode.node.kind, selectedNode.node.role]
                .filter(Boolean)
                .join(" / ") || "Graph object"}
            </p>
          </div>
          <button
            type="button"
            aria-label="Close selected object"
            onClick={onClose}
          >
            Close
          </button>
        </header>

        <GraphReviewNodeGameCard
          viewModel={selectedNode}
          selectedEdgeId={relationship?.edge_id ?? null}
          onSelectRelationship={onSelectRelationship}
          onSelectEvidenceDelta={onSelectEvidenceDelta}
          showUsefulSurfaces={false}
        />
        {relationship ? (
          <GraphReviewRelationshipCard
            sourceNode={selectedNode.node}
            relationship={relationship}
          />
        ) : null}

        {authorMode === "author_draft" ? (
          <section
            className="graph-review-author-draft-actions graph-review-projected-author-actions"
            aria-label="Author Draft selected-object actions"
          >
            <h4>Author Draft actions</h4>
            <p>
              Author Draft lets you stage local corrections before anything is
              written.
            </p>
            <p>
              For a node, Stage node assertion records that this selected object
              should exist in reviewed gold memory. For a relationship: choose
              Use as relationship source on one object, click a second object as
              the target, choose the relationship type, then stage the
              relationship locally. Nothing is written until Prepare and Commit.
            </p>
            <p>
              Draft only. Staging is local; no gold fixture, graph state, or
              corpus file has changed.
            </p>
            <button type="button" onClick={onStageNodeAssertion}>
              {selectedNode.laneRole === "live"
                ? "Stage as possible gold node"
                : "Stage node assertion"}
            </button>
            <button type="button" onClick={onUseAsRelationshipSource}>
              Use as relationship source
            </button>
            <label>
              Relationship type{" "}
              <select
                value={relationshipPredicate}
                onChange={(event) =>
                  onRelationshipPredicateChange(
                    event.target.value as GraphReviewRelationshipPredicate,
                  )
                }
              >
                {GRAPH_REVIEW_RELATIONSHIP_PREDICATES.map((predicate) => (
                  <option key={predicate} value={predicate}>
                    {predicate}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={onStageRelationship}
              disabled={!canStageRelationship}
            >
              Stage relationship
            </button>
            {relationshipDraftSource ? (
              <p>
                Relationship source: {relationshipDraftSource.laneRole}:
                {relationshipDraftSource.nodeId}
              </p>
            ) : null}
          </section>
        ) : null}

        <section className="graph-review-projected-resolver-section">
          <h4>Find existing object</h4>
          <p>
            DungeonBuddy can check whether this selected object may already
            exist in the reviewed graph. Suggestions are read-only. In Author
            Draft, you can stage a link intent for later prepare/commit review.
            No link or merge is written here.
          </p>
          {resolver ?? null}
        </section>
      </section>
    </div>
  );
}
