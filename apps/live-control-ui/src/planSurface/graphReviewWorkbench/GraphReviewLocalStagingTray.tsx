import type {
  GraphReviewLocalAuthoringProposal,
  GraphReviewLocalAuthoringProposalStatus,
} from "./graphReviewLocalAuthoringState";

function title(proposal: GraphReviewLocalAuthoringProposal): string {
  if (proposal.proposalType === "node_from_span")
    return `Node draft: ${proposal.suggestedLabel}`;
  if (proposal.proposalType === "node_assertion")
    return `Node assertion: ${proposal.label}`;
  if (proposal.proposalType === "relationship_assertion")
    return `${proposal.sourceNode.label} ${proposal.predicate} ${proposal.targetNode.label}`;
  return `Link intent: ${proposal.selectedNode.label} → ${proposal.candidate.label}`;
}
export function GraphReviewLocalStagingTray({
  proposals,
  onUpdateStatus,
  onReset,
}: {
  proposals: GraphReviewLocalAuthoringProposal[];
  onUpdateStatus: (
    proposalId: string,
    status: GraphReviewLocalAuthoringProposalStatus,
  ) => void;
  onReset: () => void;
}) {
  return (
    <aside
      className="graph-review-local-staging-tray"
      aria-label="Local staged proposals"
    >
      <header>
        <p className="plan-surface-kicker">Local staging</p>
        <h3>1. Local staged proposals</h3>
        <p>
          Draft only. No gold fixture, graph state, or corpus file has been
          changed.
        </p>
        <button type="button" onClick={onReset} disabled={!proposals.length}>
          Reset local draft
        </button>
      </header>
      {!proposals.length ? <p>No draft proposals staged yet.</p> : null}
      {proposals.map((proposal) => (
        <article
          key={proposal.proposalId}
          className="graph-review-local-proposal-card"
        >
          <span className="graph-review-local-only-badge">local only</span>
          <h4>{title(proposal)}</h4>
          <p>
            <strong>Draft proposal:</strong>{" "}
            {proposal.proposalType.replaceAll("_", " ")}
          </p>
          <p>
            <strong>Status:</strong> {proposal.status}
          </p>
          {"laneRole" in proposal ? (
            <p>
              <strong>Source lane:</strong> {proposal.laneRole}
            </p>
          ) : null}
          {proposal.proposalType === "node_from_span" ? (
            <p>
              {proposal.sourceOffsets
                ? `Offsets ${proposal.sourceOffsets.start}-${proposal.sourceOffsets.end}`
                : "Anchor precision: offset approximate/unanchored"}
            </p>
          ) : null}
          {proposal.proposalType === "relationship_assertion" &&
          proposal.laneRole === "mixed" ? (
            <p>
              Mixed-lane draft relationship. Resolver/linking review required
              before saving in a future PR.
            </p>
          ) : null}
          {proposal.proposalType === "existing_object_link_intent" ? (
            <p>
              This records a local draft intent to link later. No link has been
              written.
            </p>
          ) : null}
          <button
            type="button"
            onClick={() =>
              onUpdateStatus(proposal.proposalId, "accepted_local")
            }
          >
            Accept locally
          </button>{" "}
          <button
            type="button"
            onClick={() =>
              onUpdateStatus(proposal.proposalId, "rejected_local")
            }
          >
            Reject locally
          </button>
        </article>
      ))}
    </aside>
  );
}
