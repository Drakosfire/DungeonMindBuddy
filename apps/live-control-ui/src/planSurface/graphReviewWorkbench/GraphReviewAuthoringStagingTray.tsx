import type { GraphReviewAuthoringProposal, GraphReviewProposalStatus } from "./graphReviewAuthoringState";

export function GraphReviewAuthoringStagingTray({ proposals, onStatusChange }: { proposals: GraphReviewAuthoringProposal[]; onStatusChange: (id: string, status: GraphReviewProposalStatus) => void }) {
  return (
    <aside className="graph-review-authoring-staging-tray" aria-label="Authoring staging tray">
      <div><p className="plan-surface-kicker">Staging tray</p><h3>LLM and authoring proposals are staged, not canon.</h3></div>
      {proposals.map((proposal) => (
        <article key={proposal.id} className="graph-review-authoring-proposal" data-status={proposal.status}>
          <p className="plan-surface-kicker">Proposal: {proposal.kind.replace(/_/g, " ")} · {proposal.status}</p>
          <h4>{proposal.title}</h4><p>{proposal.subtitle}</p><p><strong>Reason:</strong> {proposal.reason}</p>
          <div className="graph-review-card-actions"><button type="button" onClick={() => onStatusChange(proposal.id, "accepted")}>Accept</button><button type="button" onClick={() => onStatusChange(proposal.id, "edited")}>Edit</button><button type="button" onClick={() => onStatusChange(proposal.id, "rejected")}>Reject</button></div>
        </article>
      ))}
    </aside>
  );
}
