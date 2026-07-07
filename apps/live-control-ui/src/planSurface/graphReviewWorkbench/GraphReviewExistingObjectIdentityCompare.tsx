import type { GraphReviewExistingObjectCandidate } from "../../api/types";
import { candidateScopeLabel } from "./graphObjectCandidateScope";
import { formatGraphObjectType } from "./graphReviewSelectionUtils";

function IdentityCompareCard({
  title,
  subtitle,
  candidate,
}: {
  title: string;
  subtitle: string;
  candidate: GraphReviewExistingObjectCandidate;
}) {
  return (
    <div className="graph-review-existing-object-identity-compare-card">
      <p className="graph-review-existing-object-identity-compare-kicker">{subtitle}</p>
      <h5>{title}</h5>
      <dl className="graph-review-existing-object-identity-compare-details">
        <div>
          <dt>Label</dt>
          <dd>{candidate.label}</dd>
        </div>
        <div>
          <dt>Candidate id</dt>
          <dd className="graph-review-existing-object-candidate-id">
            <code>{candidate.candidate_id}</code>
            <button
              type="button"
              className="graph-review-copy-id-button"
              aria-label={`Copy ${candidate.candidate_id}`}
              onClick={() => {
                void navigator.clipboard?.writeText(candidate.candidate_id);
              }}
            >
              Copy id
            </button>
          </dd>
        </div>
        <div>
          <dt>Scope / source</dt>
          <dd>{candidateScopeLabel(candidate)}</dd>
        </div>
        <div>
          <dt>Kind / role</dt>
          <dd>{formatGraphObjectType(candidate.kind, candidate.role)}</dd>
        </div>
        <div>
          <dt>Aliases</dt>
          <dd>
            {candidate.aliases && candidate.aliases.length
              ? candidate.aliases.join(", ")
              : "—"}
          </dd>
        </div>
        <div>
          <dt>Matched features</dt>
          <dd>
            {candidate.matched_features.length
              ? candidate.matched_features.join(", ")
              : "—"}
          </dd>
        </div>
        {candidate.visibility ? (
          <div>
            <dt>Visibility</dt>
            <dd>{candidate.visibility}</dd>
          </div>
        ) : null}
        {candidate.authored ? (
          <div>
            <dt>Authored</dt>
            <dd>Yes</dd>
          </div>
        ) : null}
      </dl>
    </div>
  );
}

export function GraphReviewExistingObjectIdentityCompare({
  canonical,
  duplicate,
}: {
  canonical: GraphReviewExistingObjectCandidate;
  duplicate: GraphReviewExistingObjectCandidate;
}) {
  return (
    <section
      className="graph-review-existing-object-identity-compare"
      aria-label="Compare canonical and duplicate search results"
    >
      <h4>Compare before staging</h4>
      <p className="graph-review-muted">
        Review the hub you want to keep versus the duplicate record that should
        merge away. This stages an object identity merge, not a recap text alias
        link.
      </p>
      <div className="graph-review-existing-object-identity-compare-grid">
        <IdentityCompareCard
          title={canonical.label}
          subtitle="Keep this / Survivor"
          candidate={canonical}
        />
        <IdentityCompareCard
          title={duplicate.label}
          subtitle="Merge this away / Duplicate"
          candidate={duplicate}
        />
      </div>
    </section>
  );
}
