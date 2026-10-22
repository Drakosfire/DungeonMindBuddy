import type {ExactRunReviewAssertion} from '../../api/types';
import {candidateSemanticDescription, hasReviewSemantics} from './candidateReviewSemantics';

export function CandidateReviewSemantics({assertion, assertions}: {
  assertion: ExactRunReviewAssertion; assertions: ExactRunReviewAssertion[];
}) {
  return <span className="graph-review-extract-promote-item-summary">
    <strong>{candidateSemanticDescription(assertion, assertions)}</strong>
    {!hasReviewSemantics(assertion, assertions) ? <span> · Structured meaning is unresolved; review cannot authorize this change.</span> : null}
  </span>;
}
