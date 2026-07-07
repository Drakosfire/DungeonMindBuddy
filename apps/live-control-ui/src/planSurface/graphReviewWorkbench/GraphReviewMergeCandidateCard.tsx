import type { GraphProjectionNodeView } from "../../api/types";
import type { GraphObjectMergeCandidate } from "./graphObjectMergeCandidates";
import { formatGraphObjectType } from "./graphReviewSelectionUtils";

function MergeObjectPane({
  title,
  node,
}: {
  title: string;
  node: GraphProjectionNodeView | null;
}) {
  if (!node) {
    return (
      <div className="graph-review-merge-candidate-pane">
        <h4>{title}</h4>
        <p className="graph-review-muted">Object details unavailable.</p>
      </div>
    );
  }

  return (
    <div className="graph-review-merge-candidate-pane">
      <h4>{title}</h4>
      <dl className="graph-review-merge-candidate-details">
        <div>
          <dt>Label</dt>
          <dd>{node.label}</dd>
        </div>
        <div>
          <dt>Kind / role</dt>
          <dd>{formatGraphObjectType(node.kind, node.role)}</dd>
        </div>
        <div>
          <dt>Aliases</dt>
          <dd>{node.aliases.length ? node.aliases.join(", ") : "—"}</dd>
        </div>
        <div>
          <dt>Summary</dt>
          <dd>{node.summary?.trim() || "—"}</dd>
        </div>
        <div>
          <dt>Source scope</dt>
          <dd>{node.source_domains.join(", ") || "—"}</dd>
        </div>
        <div>
          <dt>Evidence</dt>
          <dd>{node.evidence_badges.length} badge(s)</dd>
        </div>
        <div>
          <dt>Connected objects</dt>
          <dd>
            {node.adjacency.length
              ? node.adjacency.map((item) => item.label).join(", ")
              : "—"}
          </dd>
        </div>
      </dl>
    </div>
  );
}

export function GraphReviewMergeCandidateCard({
  candidate,
  survivorNode,
  mergedNode,
  onAccept,
  onReject,
  onDefer,
  decision,
}: {
  candidate: GraphObjectMergeCandidate;
  survivorNode: GraphProjectionNodeView | null;
  mergedNode: GraphProjectionNodeView | null;
  onAccept: () => void;
  onReject: () => void;
  onDefer: () => void;
  decision: "pending" | "accepted" | "rejected" | "deferred";
}) {
  return (
    <article
      className="graph-review-merge-candidate-card"
      data-testid="graph-review-merge-candidate-card"
      data-confidence={candidate.confidence}
      data-decision={decision}
    >
      <header className="graph-review-merge-candidate-card-header">
        <p className="plan-surface-kicker">Merge candidate</p>
        <h4>
          {candidate.survivorObjectRef.label} ← {candidate.mergedObjectRef.label}
        </h4>
        <p className="graph-review-muted">
          Confidence: {candidate.confidence}
          {decision !== "pending" ? ` · ${decision}` : ""}
        </p>
      </header>

      <div className="graph-review-merge-candidate-comparison">
        <MergeObjectPane title="Keep / survivor" node={survivorNode} />
        <MergeObjectPane title="Merge away" node={mergedNode} />
      </div>

      <section className="graph-review-merge-candidate-rationale">
        <h5>Why this was suggested</h5>
        <ul>
          {candidate.matchedFeatures.map((feature) => (
            <li key={feature}>{feature}</li>
          ))}
        </ul>
      </section>

      {decision === "pending" ? (
        <div className="graph-review-merge-candidate-actions">
          <button type="button" onClick={onAccept}>
            Accept merge
          </button>
          <button type="button" onClick={onReject}>
            Reject
          </button>
          <button type="button" onClick={onDefer}>
            Defer
          </button>
        </div>
      ) : decision === "accepted" ? (
        <p role="status" className="graph-review-info">
          Merge staged locally. No objects have been deleted. Commit will write an
          identity merge assertion.
        </p>
      ) : decision === "rejected" ? (
        <p className="graph-review-muted">Rejected for this session. Nothing staged.</p>
      ) : (
        <p className="graph-review-muted">Deferred. Candidate remains visible but not staged.</p>
      )}
    </article>
  );
}
