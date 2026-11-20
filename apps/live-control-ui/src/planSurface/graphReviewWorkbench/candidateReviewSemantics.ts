import type {ExactRunReviewAssertion} from '../../api/types';

const text = (value: unknown): value is string => typeof value === 'string' && !!value.trim();
/** Exact IDs only: candidate wording and summaries are never an authority join. */
export function relationshipEndpoints(a: ExactRunReviewAssertion): [string, string] | null {
  return a.kind === 'relationship' && text(a.relationshipType)
    && text(a.fromCandidateNodeId) && text(a.toCandidateNodeId)
    ? [a.fromCandidateNodeId, a.toCandidateNodeId] : null;
}
export function hasReviewSemantics(a: ExactRunReviewAssertion, assertions: ExactRunReviewAssertion[]): boolean {
  if (assertions.filter(row => row.assertionId === a.assertionId).length !== 1) return false;
  if (a.kind === 'object') return text(a.nodeType) && text(a.contributionKind);
  const ids = relationshipEndpoints(a);
  return !!ids && ids.every(id => {
    const nodes = assertions.filter(row => row.assertionId === id);
    return nodes.length === 1 && nodes[0].kind === 'object'
      && text(nodes[0].label) && text(nodes[0].nodeType) && text(nodes[0].contributionKind);
  });
}
/** Disambiguate only collisions; exact candidate identity stays consistent across rows. */
export function candidateIdentity(a: ExactRunReviewAssertion, assertions: ExactRunReviewAssertion[]): string {
  const ambiguous = assertions.filter(row => row.kind === 'object'
    && row.label.trim().toLocaleLowerCase() === a.label.trim().toLocaleLowerCase()
    && row.nodeType === a.nodeType).length > 1;
  return ambiguous ? `${a.label} [${a.assertionId}]` : a.label;
}
export function candidateSemanticDescription(a: ExactRunReviewAssertion, assertions: ExactRunReviewAssertion[]): string {
  if (a.kind === 'object') return `Structured type: ${a.nodeType || 'unresolved'}; stored kind: ${a.contributionKind || 'unresolved'}${candidateIdentity(a, assertions) !== a.label ? `; candidate: ${a.assertionId}` : ''}`;
  const ids = relationshipEndpoints(a);
  const endpoint = (id: string) => {
    const nodes = assertions.filter(row => row.assertionId === id && row.kind === 'object');
    return nodes.length === 1 ? `${candidateIdentity(nodes[0], assertions)} (${nodes[0].nodeType || 'unresolved'})` : 'Unresolved endpoint';
  };
  return `Structured relation: ${ids ? endpoint(ids[0]) : 'Unresolved endpoint'} → ${a.relationshipType || 'unresolved'} → ${ids ? endpoint(ids[1]) : 'Unresolved endpoint'}`;
}
