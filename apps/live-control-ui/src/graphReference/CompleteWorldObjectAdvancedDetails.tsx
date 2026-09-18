import type { WorldGraphObjectProjectionResult } from "../api/types";

export function CompleteWorldObjectAdvancedDetails({
  result,
  originSurface,
  bare = false,
}: {
  result: WorldGraphObjectProjectionResult;
  originSurface?: string;
  /** Recap campaign-memory Peek inlines this body into the single Source disclosure. */
  bare?: boolean;
}) {
  const relationshipCount = result.relationships?.length
    ?? result.telemetry?.relationshipCount
    ?? result.node?.adjacency.length
    ?? 0;
  const assertionCount = result.assertions?.length ?? result.telemetry?.assertionCount ?? 0;
  const sourceBindingCount = result.sourceBindings?.length ?? 0;

  const body = (
    <dl>
      <dt>World ID</dt><dd>{result.snapshot?.worldId ?? "Unknown"}</dd>
      <dt>Node ID</dt><dd>{result.resolvedNodeId ?? result.requestedNodeId}</dd>
      <dt>World revision</dt><dd>{result.snapshot?.revisionId ?? "Unknown"}</dd>
      <dt>Semantic fingerprint</dt><dd>{result.semanticFingerprint ?? "Unavailable"}</dd>
      <dt>Completeness</dt><dd>{result.completeness.status}</dd>
      <dt>Relationships</dt><dd>{relationshipCount}</dd>
      <dt>Assertions</dt><dd>{assertionCount}</dd>
      <dt>Source bindings</dt><dd>{sourceBindingCount}</dd>
      {originSurface ? <><dt>Origin surface</dt><dd>{originSurface}</dd></> : null}
    </dl>
  );

  if (bare) {
    return body;
  }

  return (
    <details className="graph-object-card__advanced">
      <summary>Advanced</summary>
      {body}
    </details>
  );
}
