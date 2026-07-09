import { useState } from "react";
import type {
  GraphProjectionAdjacencyCandidate,
  GraphProjectionNodeView,
} from "../../api/types";
import {
  relatedSummaryForRelationship,
  relationshipMetaLine,
  relationshipPredicateLabel,
  relationshipSourceExcerpt,
} from "./graphReviewSelectionUtils";

export function GraphReviewRelationshipCard({
  sourceNode,
  relationship,
}: {
  sourceNode: GraphProjectionNodeView;
  relationship: GraphProjectionAdjacencyCandidate;
}) {
  const [debugOpen, setDebugOpen] = useState(false);
  const metaLine = relationshipMetaLine(relationship);
  const sourceExcerpt = relationshipSourceExcerpt(relationship);
  const relatedSummary = relatedSummaryForRelationship(relationship);

  return (
    <article
      className="graph-review-relationship-card"
      aria-label="Relationship card"
    >
      <p className="plan-surface-kicker">Selected relationship</p>
      <h4>{relationship.label}</h4>
      {metaLine ? <p className="graph-review-relationship-meta">{metaLine}</p> : null}
      {relatedSummary ? (
        <p>
          <strong>About {relationship.label}:</strong> {relatedSummary}
        </p>
      ) : null}
      {sourceExcerpt ? (
        <blockquote className="graph-review-relationship-source-excerpt">
          <p className="graph-review-muted">Source excerpt</p>
          <p>{sourceExcerpt}</p>
        </blockquote>
      ) : (
        <p className="graph-review-muted">
          Connected to {sourceNode.label} as a{" "}
          {relationshipPredicateLabel(relationship)} link
          {relationship.kind ? ` (${relationship.kind})` : ""}.
        </p>
      )}
      <dl className="graph-review-lane-meta">
        <div>
          <dt>Evidence</dt>
          <dd>
            {relationship.evidence_ref_ids.length} supporting ref
            {relationship.evidence_ref_ids.length === 1 ? "" : "s"} available
          </dd>
        </div>
        <div>
          <dt>Sources</dt>
          <dd>
            {relationship.source_domains.length
              ? relationship.source_domains.join(", ")
              : "—"}
          </dd>
        </div>
        <div>
          <dt>Sessions</dt>
          <dd>
            {relationship.session_ids?.length
              ? relationship.session_ids.join(", ")
              : "—"}
          </dd>
        </div>
      </dl>
      <div className="graph-review-card-actions">
        <button type="button" onClick={() => setDebugOpen((open) => !open)}>
          Evidence / Debug
        </button>
      </div>
      {debugOpen ? (
        <p className="graph-review-debug-panel">
          Edge {relationship.edge_id || "unavailable"}; direction{" "}
          {relationship.direction || "unknown"}.
        </p>
      ) : null}
    </article>
  );
}
