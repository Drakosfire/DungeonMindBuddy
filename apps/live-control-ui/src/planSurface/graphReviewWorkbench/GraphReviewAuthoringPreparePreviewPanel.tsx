import { useEffect, useMemo, useState } from "react";

import { commitGraphGoldAuthoringPreview, prepareGraphGoldAuthoringPreview } from "../../api/liveApi";
import type { GraphGoldAuthoringCommitResponse, GraphGoldAuthoringPrepareRequest, GraphGoldAuthoringPrepareResponse, GraphGoldAuthoringVerifyCommitResponse } from "../../api/types";
import { buildGraphGoldAuthoringPrepareRequest } from "./graphReviewAuthoringPrepareApi";
import type { GraphReviewLocalAuthoringProposal } from "./graphReviewLocalAuthoringState";

interface Props {
  campaignId: string;
  sessionId: string;
  proposals: GraphReviewLocalAuthoringProposal[];
  onReloadAndVerifyCommit?: (commitResponse: GraphGoldAuthoringCommitResponse) => Promise<GraphGoldAuthoringVerifyCommitResponse>;
  onShowCommittedObject?: (targetId: string) => void;
}

function title(operationType: string): string {
  return operationType.split("_").map((part) => part[0]?.toUpperCase() + part.slice(1)).join(" ");
}

export function GraphReviewAuthoringPreparePreviewPanel({ campaignId, sessionId, proposals, onReloadAndVerifyCommit, onShowCommittedObject }: Props) {
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "blocked" | "error">("idle");
  const [response, setResponse] = useState<GraphGoldAuthoringPrepareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [commitConfirmed, setCommitConfirmed] = useState(false);
  const [commitStatus, setCommitStatus] = useState<"idle" | "loading" | "success" | "blocked" | "error">("idle");
  const [commitResponse, setCommitResponse] = useState<GraphGoldAuthoringCommitResponse | null>(null);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [preparedRequest, setPreparedRequest] = useState<GraphGoldAuthoringPrepareRequest | null>(null);
  const [verificationStatus, setVerificationStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [verificationResponse, setVerificationResponse] = useState<GraphGoldAuthoringVerifyCommitResponse | null>(null);
  const [verificationError, setVerificationError] = useState<string | null>(null);
  const proposalSignature = useMemo(() => JSON.stringify({ campaignId, sessionId, proposals }), [campaignId, sessionId, proposals]);

  useEffect(() => {
    if (!response) return;
    setStatus("idle");
    setResponse(null);
    setPreparedRequest(null);
    setCommitConfirmed(false);
    setCommitStatus("idle");
    setCommitResponse(null);
    setCommitError(null);
    setVerificationStatus("idle");
    setVerificationResponse(null);
    setVerificationError(null);
  }, [proposalSignature]);

  const prepare = async () => {
    setStatus("loading");
    setError(null);
    setResponse(null);
    try {
      const request = buildGraphGoldAuthoringPrepareRequest({
        campaignId,
        sessionId,
        proposals: proposals.filter((proposal) => proposal.status !== "rejected_local"),
      });
      const result = await prepareGraphGoldAuthoringPreview(request);
      setResponse(result);
      setPreparedRequest(request);
      setStatus(result.validation_status === "blocked" ? "blocked" : "ready");
      setCommitConfirmed(false);
      setCommitStatus("idle");
      setCommitResponse(null);
      setCommitError(null);
      setVerificationStatus("idle");
      setVerificationResponse(null);
      setVerificationError(null);
    } catch (prepareError) {
      setStatus("error");
      setError(prepareError instanceof Error ? prepareError.message : "Could not prepare write preview.");
    }
  };

  const commit = async () => {
    if (!response || !preparedRequest || response.validation_status === "blocked" || !commitConfirmed) return;
    setCommitStatus("loading");
    setCommitError(null);
    setCommitResponse(null);
    try {
      const result = await commitGraphGoldAuthoringPreview({
        schema: "dmb_graph_gold_authoring_commit_request_v1",
        campaign_id: campaignId,
        session_id: sessionId,
        fixture_version: preparedRequest.fixture_version,
        proposals: preparedRequest.proposals,
        expected_prepare_fingerprint: response.prepare_fingerprint,
      });
      setCommitResponse(result);
      setCommitStatus(result.commit_status === "blocked" ? "blocked" : "success");
      setVerificationStatus("idle");
      setVerificationResponse(null);
      setVerificationError(null);
    } catch (commitErrorValue) {
      setCommitStatus("error");
      setCommitError(commitErrorValue instanceof Error ? commitErrorValue.message : "Could not commit prepared preview.");
    }
  };


  const reloadAndVerify = async () => {
    if (!commitResponse || !onReloadAndVerifyCommit) return;
    setVerificationStatus("loading");
    setVerificationError(null);
    try {
      const result = await onReloadAndVerifyCommit(commitResponse);
      setVerificationResponse(result);
      setVerificationStatus("ready");
    } catch (verifyErrorValue) {
      setVerificationStatus("error");
      setVerificationError(verifyErrorValue instanceof Error ? verifyErrorValue.message : "Could not reload and verify gold projection.");
    }
  };

  const verificationCopy = verificationResponse?.verification_status === "verified"
    ? "Gold projection reloaded. Committed changes verified."
    : verificationResponse?.verification_status === "missing"
      ? "Gold projection reloaded, but expected committed changes were not found."
      : verificationResponse
        ? "Gold projection reloaded. Some committed changes are fixture-only or event-only."
        : null;

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
          {response.validation_status !== "blocked" ? (
            <section className="graph-review-authoring-commit" aria-label="Commit prepared preview">
              <h4>Commit prepared preview</h4>
              <p>This preview is ready to commit. Committing will write the gold fixture and create a backup.</p>
              <p><strong>This will write the gold fixture and create a backup.</strong></p>
              <label>
                <input type="checkbox" checked={commitConfirmed} onChange={(event) => setCommitConfirmed(event.target.checked)} />
                I understand this will write to the gold fixture and create a backup.
              </label>
              <button type="button" onClick={commit} disabled={!preparedRequest || !commitConfirmed || commitStatus === "loading"}>Commit prepared preview</button>
              {commitStatus === "loading" ? <p role="status">Committing prepared preview…</p> : null}
              {commitStatus === "success" && commitResponse ? <p role="status">Committed. Gold fixture updated and backup created.</p> : null}
              {commitStatus === "blocked" ? <p role="status">Commit blocked. No files were changed.</p> : null}
              {commitStatus === "error" ? <p role="alert">Could not commit prepared preview. {commitError}</p> : null}
              {commitResponse ? (
                <div>
                  <dl className="graph-review-lane-meta">
                    <div><dt>Commit id</dt><dd>{commitResponse.commit_id}</dd></div>
                    <div><dt>Fixture relpath</dt><dd>{commitResponse.fixture_relpath}</dd></div>
                    <div><dt>Backup relpath</dt><dd>{commitResponse.backup_relpath ?? "No backup written"}</dd></div>
                    <div><dt>Event log relpath</dt><dd>{commitResponse.event_log_relpath ?? "No event written"}</dd></div>
                    <div><dt>Nodes added</dt><dd>{commitResponse.changed_counts.nodes_added}</dd></div>
                    <div><dt>Nodes asserted</dt><dd>{commitResponse.changed_counts.nodes_asserted}</dd></div>
                    <div><dt>Edges added</dt><dd>{commitResponse.changed_counts.edges_added}</dd></div>
                    <div><dt>Link intents recorded</dt><dd>{commitResponse.changed_counts.link_intents_recorded}</dd></div>
                    <div><dt>Operations skipped</dt><dd>{commitResponse.changed_counts.operations_skipped}</dd></div>
                  </dl>
                  <h5>Applied operations</h5>
                  <ul>{commitResponse.applied_operations.map((operation) => <li key={operation.operation_id}>{operation.summary}</li>)}</ul>
                  <h5>Skipped operations</h5>
                  <ul>{commitResponse.skipped_operations.map((operation) => <li key={operation.operation_id}>{operation.reason}</li>)}</ul>
                  {commitResponse.diagnostics.length ? <ul>{commitResponse.diagnostics.map((diagnostic, index) => <li key={`${diagnostic.code}-${index}`}>{diagnostic.message}</li>)}</ul> : null}
                  {commitResponse.commit_status !== "blocked" && onReloadAndVerifyCommit ? (
                    <button type="button" onClick={reloadAndVerify} disabled={verificationStatus === "loading"}>Reload gold projection</button>
                  ) : null}
                  {verificationStatus === "loading" ? <p role="status">Reloading gold projection…</p> : null}
                  {verificationStatus === "error" ? <p role="alert">Could not verify committed changes. {verificationError}</p> : null}
                  {verificationResponse ? (
                    <section aria-label="Verified committed changes">
                      <h5>Verified committed changes</h5>
                      {verificationCopy ? <p role="status">{verificationCopy}</p> : null}
                      <ul>
                        {verificationResponse.checked_operations.map((operation) => (
                          <li key={operation.operation_id}>
                            <strong>{title(operation.operation_type)}</strong> — Status: {operation.verification_status.replaceAll("_", " ")}
                            {operation.target_id ? <> Target: {operation.target_id}</> : null}
                            <p>{operation.summary}</p>
                            {operation.verification_status === "recorded_event_only" && operation.operation_type === "link_existing_intent" ? <p>No identity link was written.</p> : null}
                            {operation.target_id && operation.verification_status === "found_in_gold_projection" && onShowCommittedObject ? <button type="button" onClick={() => onShowCommittedObject(operation.target_id!)}>Show {operation.target_id}</button> : null}
                          </li>
                        ))}
                      </ul>
                      {verificationResponse.diagnostics.length ? <ul>{verificationResponse.diagnostics.map((diagnostic, index) => <li key={`${diagnostic.code}-${index}`}>{diagnostic.message}</li>)}</ul> : null}
                    </section>
                  ) : null}
                </div>
              ) : null}
            </section>
          ) : null}
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
