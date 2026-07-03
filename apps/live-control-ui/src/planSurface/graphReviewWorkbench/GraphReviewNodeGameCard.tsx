import { useState } from "react";
import type { GraphReviewGameNode } from "./graphReviewAuthoringMockData";

export function GraphReviewNodeGameCard({ node, onShowRelationships }: { node: GraphReviewGameNode; onShowRelationships: () => void }) {
  const [debugOpen, setDebugOpen] = useState(false);
  return (
    <article className="graph-review-node-game-card" aria-label={`${node.label} game card`}>
      <h4>{node.label}</h4>
      <p className="graph-review-game-kind">{node.gameKind}</p>
      <p>{node.summary}</p>
      <p><strong>Appears in:</strong> {node.appearsIn.join(", ")}</p>
      <section><h5>Available</h5>{node.availableSurfaces.map((surface) => <button key={surface.kind} type="button">{surface.label}</button>)}</section>
      <section><h5>Connected to</h5><ul>{node.relationships.map((rel) => <li key={`${rel.label}-${rel.target}`}>{rel.label} → {rel.target}</li>)}</ul></section>
      <div className="graph-review-card-actions"><button type="button" onClick={onShowRelationships}>Show relationships</button><button type="button">Link existing object</button><button type="button" onClick={() => setDebugOpen((open) => !open)}>Evidence / Debug</button></div>
      {debugOpen ? <p className="graph-review-debug-panel">Debug placeholder: source spans, extractor pass, scores, and raw IDs will live here.</p> : null}
    </article>
  );
}
