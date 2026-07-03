import { useState } from "react";
import type { GraphReviewGameRelationship } from "./graphReviewAuthoringMockData";

export function GraphReviewRelationshipCard({ relationship }: { relationship: GraphReviewGameRelationship }) {
  const [debugOpen, setDebugOpen] = useState(false);
  return (
    <article className="graph-review-relationship-card" aria-label="Relationship card">
      <h4>{relationship.source} {relationship.predicate} {relationship.target}</h4>
      <p>{relationship.meaning}</p>
      <div className="graph-review-card-actions">
        <button type="button">Highlight endpoints</button>
        <button type="button">Open {relationship.target}</button>
        <button type="button">Open encounter</button>
        <button type="button" onClick={() => setDebugOpen((open) => !open)}>Evidence / Debug</button>
      </div>
      {debugOpen ? <p className="graph-review-debug-panel">Evidence/debug placeholder: anchors, confidence, and raw relation payload stay secondary.</p> : null}
    </article>
  );
}
