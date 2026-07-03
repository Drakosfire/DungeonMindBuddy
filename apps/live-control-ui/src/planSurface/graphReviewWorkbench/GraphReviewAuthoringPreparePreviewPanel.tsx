import { useState } from "react";

import { prepareGraphGoldAuthoringPreview } from "../../api/liveApi";
import type { GraphGoldAuthoringPrepareResponse } from "../../api/types";
import { buildGraphGoldAuthoringPrepareRequest } from "./graphReviewAuthoringPrepareApi";
import type { GraphReviewLocalAuthoringProposal } from "./graphReviewLocalAuthoringState";

interface Props {
  campaignId: string;
  sessionId: string;
  proposals: GraphReviewLocalAuthoringProposal[];
}

function title(operationType: string): string {
  return operationType.split("_").map((part) => part[0]?.toUpperCase() + part.slice(1)).join(" ");
}

export function GraphReviewAuthoringPreparePreviewPanel({ campaignId, sessionId, proposals }: Props) {
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "blocked" | "error">("idle");
  const [response, setResponse] = useState<GraphGoldAuthoringPrepareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const prepare = async () => {
    setStatus("loading");
    setError(null);
    setResponse(null);
    try {
      const result = await prepareGraphGoldAuthoringPreview(
        buildGraphGoldAuthoringPrepareRequest({
          campaignId,
          sessionId,
          proposals: proposals.filter((proposal) => proposal.status !== "rejected_local"),
        }),
      );
      setResponse(result);
      setStatus(result.validation_status === "blocked" ? "blocked" : "ready");
    } catch (prepareError) {
      setStatus("error");
      setError(prepareError instanceof Error ? prepareError.message : "Could not prepare write preview.");
    }
  };

  return (
    <section className="graph-review-authoring-prepare-preview" aria-label="Prepare write preview panel">
      <header>
        <p className="plan-surface-kicker">Read-only authoring prepare</p>
        <h3>Prepare write preview</h3>
        <p>No files were changed.</p>
      </header>
      <button type="button" onClick={prepare} disabled={status === "loading"}>
        Prepare write preview
      </button>
      {status === "idle" ? <p>Accept local proposals, then prepare a read-only write preview.</p> : null}
      {status === "loading" ? <p role="status">Preparing read-only preview…</p> : null}
      {status === "ready" && response ? <p role="status">Preview prepared. No files were changed.</p> : null}
      {status === "blocked" && response ? <p role="status">Preview blocked. Resolve diagnostics before a future write step. No files were changed.</p> : null}
      {status === "error" ? <p role="alert">Could not prepare write preview. {error}</p> : null}

      {response ? (
        <div>
          <dl className="graph-review-lane-meta">
            <div><dt>Validation status</dt><dd>{response.validation_status}</dd></div>
            <div><dt>Accepted local</dt><dd>{response.proposal_counts.accepted_local}</dd></div>
            <div><dt>Staged</dt><dd>{response.proposal_counts.staged}</dd></div>
            <div><dt>Rejected local</dt><dd>{response.proposal_counts.rejected_local}</dd></div>
            <div><dt>Proposed operations</dt><dd>{response.proposal_counts.candidate_operations}</dd></div>
            <div><dt>write_performed</dt><dd>{String(response.write_performed)} — No files were changed.</dd></div>
          </dl>
          <p>{response.preview_summary}</p>
          {response.blocking_errors.length ? <div><h4>Blocking diagnostics</h4><ul>{response.blocking_errors.map((diagnostic) => <li key={`${diagnostic.code}-${diagnostic.source_proposal_id}`}>{diagnostic.message}</li>)}</ul></div> : null}
          {response.warnings.length ? <div><h4>Warnings</h4><ul>{response.warnings.map((diagnostic, index) => <li key={`${diagnostic.code}-${diagnostic.source_proposal_id}-${index}`}>{diagnostic.message}</li>)}</ul></div> : null}
          <div className="graph-review-authoring-operation-list">
            {response.proposed_operations.map((operation) => (
              <article key={operation.operation_id} className="graph-review-authoring-operation-card">
                <h4>{title(operation.operation_type)} — {operation.label}</h4>
                <p>{operation.summary}</p>
                <p>Source proposal: {operation.source_proposal_id}</p>
                <p>Manual review: {operation.requires_manual_review ? "yes" : "no"}</p>
                {operation.diagnostics.length ? <ul>{operation.diagnostics.map((diagnostic, index) => <li key={`${diagnostic.code}-${index}`}>{diagnostic.message}</li>)}</ul> : null}
                {operation.gold_shape_preview ? (
                  <details>
                    <summary>Gold-shaped preview payload</summary>
                    <pre>{JSON.stringify(operation.gold_shape_preview, null, 2)}</pre>
                  </details>
                ) : null}
              </article>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
