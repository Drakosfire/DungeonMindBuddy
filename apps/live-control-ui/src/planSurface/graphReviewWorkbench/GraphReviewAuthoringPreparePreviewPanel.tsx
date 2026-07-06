import { GraphReviewCommitSummaryPanel } from "./GraphReviewCommitSummaryPanel";
import { GraphReviewCommitVerificationPanel } from "./GraphReviewCommitVerificationPanel";
import type { GraphReviewAuthorDraftWorkflow } from "./useGraphReviewAuthorDraftWorkflow";
import type { GraphGoldAuthoringCommitResponse, GraphGoldAuthoringVerifyCommitResponse } from "../../api/types";

interface Props {
  campaignId: string;
  sessionId: string;
  hasGold?: boolean;
  workflow: GraphReviewAuthorDraftWorkflow;
  onReloadAndVerifyCommit?: (commitResponse: GraphGoldAuthoringCommitResponse) => Promise<GraphGoldAuthoringVerifyCommitResponse>;
  onShowCommittedObject?: (targetId: string) => void;
  canShowCommittedObject?: (targetId: string) => boolean;
}

function title(operationType: string): string {
  return operationType.split("_").map((part) => part[0]?.toUpperCase() + part.slice(1)).join(" ");
}

export function GraphReviewAuthoringPreparePreviewPanel({
  hasGold = false,
  workflow: draft,
  onReloadAndVerifyCommit,
  onShowCommittedObject,
  canShowCommittedObject,
}: Props) {
  if (!hasGold) {
    return (
      <section
        className="graph-review-authoring-prepare-preview"
        aria-label="Prepare write preview panel"
      >
        <header>
          <p className="plan-surface-kicker">Author Draft workflow</p>
          <h3>2. Prepare preview</h3>
        </header>
        <p className="plan-projection-empty">
          Gold fixture required to commit authoring changes. Local staging above
          is ephemeral until a gold fixture exists for this session.
        </p>
      </section>
    );
  }

  return (
    <section className="graph-review-authoring-prepare-preview" aria-label="Prepare write preview panel">
      <header>
        <p className="plan-surface-kicker">Author Draft workflow</p>
        <h3>2. Prepare preview</h3>
        <p>Prepare write preview. No files were changed.</p>
      </header>
      <button type="button" onClick={draft.preparePreview} disabled={draft.prepareStatus === "loading"}>
        Prepare write preview
      </button>
      {draft.prepareStatus === "idle" ? <p>Accept local proposals, then prepare a read-only write preview.</p> : null}
      {draft.prepareStatus === "loading" ? <p role="status">Preparing read-only preview…</p> : null}
      {draft.prepareStatus === "ready" && draft.prepareResponse ? <p role="status">Preview prepared. No files were changed.</p> : null}
      {draft.prepareStatus === "blocked" && draft.prepareResponse ? <p role="status">Preview blocked. Resolve diagnostics before a future write step. No files were changed.</p> : null}
      {draft.prepareStatus === "error" ? <p role="alert">Could not prepare write preview. {draft.prepareError}</p> : null}

      {draft.prepareResponse ? (
        <div>
          <dl className="graph-review-lane-meta">
            <div><dt>Validation status</dt><dd>{draft.prepareResponse.validation_status}</dd></div>
            <div><dt>Accepted local</dt><dd>{draft.prepareResponse.proposal_counts.accepted_local}</dd></div>
            <div><dt>Staged</dt><dd>{draft.prepareResponse.proposal_counts.staged}</dd></div>
            <div><dt>Rejected local</dt><dd>{draft.prepareResponse.proposal_counts.rejected_local}</dd></div>
            <div><dt>Proposed operations</dt><dd>{draft.prepareResponse.proposal_counts.candidate_operations}</dd></div>
            <div><dt>write_performed</dt><dd>{String(draft.prepareResponse.write_performed)} — No files were changed.</dd></div>
          </dl>
          <p>{draft.prepareResponse.preview_summary}</p>
          {draft.prepareResponse.blocking_errors.length ? <div><h4>Blocking diagnostics</h4><ul>{draft.prepareResponse.blocking_errors.map((diagnostic) => <li key={`${diagnostic.code}-${diagnostic.source_proposal_id}`}>{diagnostic.message}</li>)}</ul></div> : null}
          {draft.prepareResponse.warnings.length ? <div><h4>Warnings</h4><ul>{draft.prepareResponse.warnings.map((diagnostic, index) => <li key={`${diagnostic.code}-${diagnostic.source_proposal_id}-${index}`}>{diagnostic.message}</li>)}</ul></div> : null}
          {draft.prepareResponse.validation_status !== "blocked" ? (
            <section className="graph-review-authoring-commit" aria-label="Commit prepared preview">
              <h4>3. Commit prepared preview</h4>
              <p>This preview is ready to commit. Committing will write the gold fixture and create a backup.</p>
              <p><strong>This will write the gold fixture and create a backup.</strong></p>
              <label>
                <input type="checkbox" checked={draft.commitConfirmed} onChange={(event) => draft.setCommitConfirmed(event.target.checked)} />
                I understand this will write to the gold fixture and create a backup.
              </label>
              <button type="button" onClick={draft.commitPreparedPreview} disabled={!draft.preparedRequest || !draft.commitConfirmed || draft.commitStatus === "loading" || draft.commitStatus === "success"}>Commit prepared preview</button>
              {draft.commitStatus === "loading" ? <p role="status">Committing prepared preview…</p> : null}
              {draft.commitStatus === "success" && draft.commitResponse ? <p role="status">Committed. Gold fixture updated and backup created.</p> : null}
              {draft.commitStatus === "blocked" ? <p role="status">Commit blocked. No files were changed.</p> : null}
              {draft.commitStatus === "error" ? <p role="alert">Could not commit prepared preview. {draft.commitError}</p> : null}
              {draft.commitResponse ? (
                <>
                  <GraphReviewCommitSummaryPanel commitResponse={draft.commitResponse} />
                  {draft.commitResponse.commit_status !== "blocked" && onReloadAndVerifyCommit ? (
                    <section aria-label="Reload and verify committed changes">
                      <h4>4. Verify committed changes</h4>
                      <button type="button" onClick={draft.reloadAndVerifyCommit} disabled={draft.verificationStatus === "loading"}>Reload gold projection</button>
                    </section>
                  ) : null}
                  {draft.verificationStatus === "loading" ? <p role="status">Reloading gold projection…</p> : null}
                  {draft.verificationStatus === "error" ? <p role="alert">Could not verify committed changes. {draft.verificationError}</p> : null}
                  {draft.verificationResponse ? <GraphReviewCommitVerificationPanel verificationResponse={draft.verificationResponse} onShowCommittedObject={onShowCommittedObject} canShowCommittedObject={canShowCommittedObject} /> : null}
                </>
              ) : null}
            </section>
          ) : null}
          <div className="graph-review-authoring-operation-list">
            {draft.prepareResponse.proposed_operations.map((operation) => (
              <article key={operation.operation_id} className="graph-review-authoring-operation-card">
                <h4>{title(operation.operation_type)} — {operation.label}</h4>
                <p>{operation.summary}</p>
                <p>Source proposal: {operation.source_proposal_id}</p>
                <p>Manual review: {operation.requires_manual_review ? "yes" : "no"}</p>
                {operation.diagnostics.length ? <ul>{operation.diagnostics.map((diagnostic, index) => <li key={`${diagnostic.code}-${index}`}>{diagnostic.message}</li>)}</ul> : null}
                {operation.gold_shape_preview ? (<details><summary>Gold-shaped preview payload</summary><pre>{JSON.stringify(operation.gold_shape_preview, null, 2)}</pre></details>) : null}
              </article>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
