import type { GraphReviewExistingObjectCandidate } from "../../api/types";
import {
  candidateScopeLabel,
  formatResolverCandidateLabel,
} from "./graphObjectCandidateScope";

const MAX_BIND_CANDIDATES = 5;

export function GraphObjectAuthoringBindExistingPanel({
  selectedText,
  status,
  error = null,
  candidates,
  onBindAsAlias,
  binding = false,
}: {
  selectedText: string;
  status: "idle" | "loading" | "ready" | "error";
  error?: string | null;
  candidates: GraphReviewExistingObjectCandidate[];
  onBindAsAlias: (candidate: GraphReviewExistingObjectCandidate) => void;
  binding?: boolean;
}) {
  const phrase = selectedText.trim();
  if (!phrase) {
    return null;
  }

  const topCandidates = candidates.slice(0, MAX_BIND_CANDIDATES);

  return (
    <section
      className="graph-object-authoring-bind-existing"
      aria-label="Bind highlighted text to an existing object"
      data-testid="graph-object-authoring-bind-existing"
    >
      <header className="graph-object-authoring-bind-existing-header">
        <p className="plan-surface-kicker">Bind or create</p>
        <h4>Is “{phrase}” already in the campaign?</h4>
        <p className="graph-object-authoring-surface-hint">
          Most of the time this is an alias of an existing node. Bind it below, or
          keep scrolling to create a new object.
        </p>
      </header>

      {status === "loading" ? (
        <p role="status" data-testid="graph-object-authoring-bind-existing-loading">
          Searching campaign sources…
        </p>
      ) : null}

      {status === "error" ? (
        <p role="alert" data-testid="graph-object-authoring-bind-existing-error">
          {error ?? "Could not search existing objects."}
        </p>
      ) : null}

      {status === "ready" && topCandidates.length === 0 ? (
        <p data-testid="graph-object-authoring-bind-existing-empty">
          No likely existing objects matched. Create a new object below if this
          phrase should become its own node.
        </p>
      ) : null}

      {topCandidates.length > 0 ? (
        <ul
          className="graph-object-authoring-bind-existing-list"
          data-testid="graph-object-authoring-bind-existing-list"
        >
          {topCandidates.map((candidate) => (
            <li
              key={`${candidate.graph_scope ?? candidate.source}:${candidate.candidate_id}`}
              className="graph-object-authoring-bind-existing-item"
            >
              <div className="graph-object-authoring-bind-existing-meta">
                <p className="graph-object-authoring-bind-existing-label">
                  {formatResolverCandidateLabel(candidate)}
                </p>
                <p className="graph-object-authoring-bind-existing-subline">
                  {candidateScopeLabel(candidate)}
                  {candidate.confidence ? ` · ${candidate.confidence}` : ""}
                  {candidate.reason ? ` · ${candidate.reason}` : ""}
                </p>
              </div>
              <button
                type="button"
                data-testid="graph-object-authoring-bind-as-alias-button"
                disabled={binding}
                onClick={() => onBindAsAlias(candidate)}
              >
                Add as alias
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
