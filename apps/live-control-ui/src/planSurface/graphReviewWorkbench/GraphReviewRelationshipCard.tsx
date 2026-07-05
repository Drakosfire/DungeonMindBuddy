import { useState } from "react";
import type {
  GraphProjectionAdjacencyCandidate,
  GraphProjectionNodeView,
} from "../../api/types";
import { formatGraphReviewRelationshipStatement } from "./graphReviewSelectionUtils";

export function GraphReviewRelationshipCard({
  sourceNode,
  relationship,
}: {
  sourceNode: GraphProjectionNodeView;
  relationship: GraphProjectionAdjacencyCandidate;
}) {
  const [debugOpen, setDebugOpen] = useState(false);
  const statement = formatGraphReviewRelationshipStatement(
    sourceNode.label,
    relationship,
  );
  return (
    <article
      className="graph-review-relationship-card"
      aria-label="Relationship card"
    >
      <p className="plan-surface-kicker">Selected relationship</p>
      <h4>{statement}</h4>
      <p>
        Game meaning: {sourceNode.label} is connected to {relationship.label} as
        a projected campaign link
        {relationship.kind ? ` involving a ${relationship.kind}` : ""}.
      </p>
      <dl className="graph-review-lane-meta">
        <div>
          <dt>Adjacent object</dt>
          <dd>{relationship.label}</dd>
        </div>
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
