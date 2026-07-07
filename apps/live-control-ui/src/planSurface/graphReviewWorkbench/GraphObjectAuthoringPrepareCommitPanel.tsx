import { useEffect, useMemo, useState } from "react";

import {
  commitGraphObjectAuthoringWrite,
  prepareGraphObjectAuthoringWrite,
} from "../../api/liveApi";
import type {
  GraphObjectAuthoringCommitResponse,
  GraphObjectAuthoringPrepareResponse,
  GraphObjectAuthoringProposalPayload,
  GraphAuthoringDiagnostic,
} from "../../api/types";
import { GraphObjectAuthoringOverlapWarnings } from "./GraphObjectAuthoringOverlapWarnings";
import type { GraphObjectAuthoringOverlapWarning } from "./graphObjectAuthoringOverlap";
import type { GraphObjectAuthoringProposal } from "./graphObjectAuthoringDraft";
import { serializeGraphObjectAuthoringProposalForApi } from "./graphObjectAuthoringDraft";

function toProposalPayload(proposal: GraphObjectAuthoringProposal): GraphObjectAuthoringProposalPayload {
  return serializeGraphObjectAuthoringProposalForApi(
    proposal,
  ) as unknown as GraphObjectAuthoringProposalPayload;
}

function proposalsFingerprint(proposals: GraphObjectAuthoringProposal[]): string {
  return JSON.stringify(proposals.map((proposal) => proposal.localProposalId));
}

function shortToken(token: string): string {
  if (token.length <= 16) {
    return token;
  }
  return `${token.slice(0, 8)}…${token.slice(-8)}`;
}

function toOverlapWarnings(diagnostics: GraphAuthoringDiagnostic[]) {
  return diagnostics
    .filter((item) => item.severity === "warning" || item.severity === "info")
    .map((item) => ({
      code: item.code as GraphObjectAuthoringOverlapWarning["code"],
      message: item.message,
      localProposalId: item.local_proposal_id ?? undefined,
    }));
}

function parseApiError(error: unknown): string {
  if (error instanceof Error) {
    const message = error.message;
    try {
      const parsed = JSON.parse(message) as { code?: string; message?: string };
      if (parsed.message) {
        return parsed.message;
      }
    } catch {
      // keep raw message
    }
    return message;
  }
  return "Request failed.";
}

export interface GraphObjectAuthoringPrepareCommitPanelProps {
  campaignId: string;
  sessionId: string;
  campaignRel?: string | null;
  sourceRunId?: string | null;
  sourceGraphId?: string | null;
  proposals: GraphObjectAuthoringProposal[];
  onCommitted: (localProposalIds: string[]) => void;
  onRefreshProjection?: () => Promise<unknown>;
}

export function GraphObjectAuthoringPrepareCommitPanel({
  campaignId,
  sessionId,
  campaignRel,
  sourceRunId,
  sourceGraphId,
  proposals,
  onCommitted,
  onRefreshProjection,
}: GraphObjectAuthoringPrepareCommitPanelProps) {
  const [prepared, setPrepared] = useState<GraphObjectAuthoringPrepareResponse | null>(null);
  const [committed, setCommitted] = useState<GraphObjectAuthoringCommitResponse | null>(null);
  const [preparedForFingerprint, setPreparedForFingerprint] = useState<string>("");
  const [prepareError, setPrepareError] = useState<string | null>(null);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [preparing, setPreparing] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [refreshingProjection, setRefreshingProjection] = useState(false);
  const [refreshProjectionError, setRefreshProjectionError] = useState<string | null>(null);

  const currentFingerprint = useMemo(() => proposalsFingerprint(proposals), [proposals]);
  const proposalsChangedSincePrepare =
    prepared !== null && preparedForFingerprint !== currentFingerprint;

  useEffect(() => {
    if (proposalsChangedSincePrepare) {
      setPrepared(null);
      setPreparedForFingerprint("");
      setCommitError(null);
    }
  }, [proposalsChangedSincePrepare]);

  const canPrepare = proposals.length > 0 && !preparing;
  const canCommit = prepared !== null && !proposalsChangedSincePrepare && !committing;

  async function handlePrepare() {
    setPrepareError(null);
    setCommitError(null);
    setCommitted(null);
    setPreparing(true);
    try {
      const response = await prepareGraphObjectAuthoringWrite({
        campaignId,
        campaignRel,
        sessionId,
        sourceRunId,
        sourceGraphId,
        proposals: proposals.map(toProposalPayload),
      });
      setPrepared(response);
      setPreparedForFingerprint(currentFingerprint);
    } catch (error) {
      setPrepared(null);
      setPrepareError(parseApiError(error));
    } finally {
      setPreparing(false);
    }
  }

  async function handleCommit() {
    if (!prepared) {
      return;
    }
    setCommitError(null);
    setCommitting(true);
    try {
      const response = await commitGraphObjectAuthoringWrite({
        campaignId,
        campaignRel,
        sessionId,
        sourceRunId,
        sourceGraphId,
        proposals: proposals.map(toProposalPayload),
        confirmToken: prepared.confirm_token,
        currentOverlayToken: prepared.current_overlay_token,
      });
      if (!response.committed) {
        setCommitError(
          response.diagnostics[0]?.message ??
            "Commit did not complete. Review diagnostics and prepare again.",
        );
        return;
      }
      setCommitted(response);
      setPrepared(null);
      setPreparedForFingerprint("");
      onCommitted(proposals.map((proposal) => proposal.localProposalId));
    } catch (error) {
      const message = parseApiError(error);
      if (message.includes("stale_overlay") || message.includes("changed since")) {
        setCommitError(
          "The authored graph changed since this preview was prepared. Prepare again before committing.",
        );
      } else if (message.includes("confirm_token")) {
        setCommitError(
          "The prepared preview no longer matches these proposals. Prepare again before committing.",
        );
      } else {
        setCommitError(message);
      }
    } finally {
      setCommitting(false);
    }
  }

  if (proposals.length === 0 && !committed) {
    return null;
  }

  return (
    <section
      className="graph-object-authoring-prepare-commit-panel"
      aria-label="Prepare and commit authored graph memory"
      data-testid="graph-object-authoring-prepare-commit-panel"
    >
      <header>
        <h4>Write authored graph memory</h4>
        <p className="graph-object-authoring-prepare-commit-hint">
          Prepare a safe preview, then commit into authored campaign graph memory. Staged proposals
          persist for this browser tab until you commit or remove them. After commit, refresh graph
          review to see authored objects in the picker.
        </p>
      </header>

      {proposals.length > 0 ? (
        <div className="graph-object-authoring-prepare-commit-actions">
          <button
            type="button"
            data-testid="graph-object-authoring-prepare-button"
            disabled={!canPrepare}
            onClick={() => void handlePrepare()}
          >
            {preparing ? "Preparing…" : "Prepare write"}
          </button>
          {prepared ? (
            <button
              type="button"
              data-testid="graph-object-authoring-commit-button"
              disabled={!canCommit}
              onClick={() => void handleCommit()}
            >
              {committing ? "Committing…" : "Commit authored graph memory"}
            </button>
          ) : null}
        </div>
      ) : null}

      {prepareError ? (
        <p className="graph-object-authoring-prepare-commit-error" role="alert">
          {prepareError}
        </p>
      ) : null}

      {prepared && !proposalsChangedSincePrepare ? (
        <div
          className="graph-object-authoring-prepare-preview"
          data-testid="graph-object-authoring-prepare-preview"
        >
          <h5>Prepared write preview</h5>
          <ul>
            {prepared.overlay_summary.object_count ? (
              <li>{prepared.overlay_summary.object_count} object assertion(s)</li>
            ) : null}
            {prepared.overlay_summary.link_existing_count ? (
              <li>{prepared.overlay_summary.link_existing_count} link-existing assertion(s)</li>
            ) : null}
            {prepared.overlay_summary.relationship_count ? (
              <li>{prepared.overlay_summary.relationship_count} relationship assertion(s)</li>
            ) : null}
          </ul>
          <p>Target overlay: {prepared.overlay_path}</p>
          <p>Event log: {prepared.event_log_path}</p>
          <p>Current overlay token: {shortToken(prepared.current_overlay_token)}</p>
          <p>Proposed assertions digest: {shortToken(prepared.proposed_assertions_digest)}</p>
          <ul className="graph-object-authoring-no-mutation-list">
            {prepared.no_mutation_guarantees.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <GraphObjectAuthoringOverlapWarnings
            warnings={toOverlapWarnings(prepared.diagnostics)}
            title="Prepare overlap warnings"
          />
        </div>
      ) : null}

      {commitError ? (
        <p className="graph-object-authoring-prepare-commit-error" role="alert">
          {commitError}
        </p>
      ) : null}

      {committed ? (
        <div
          className="graph-object-authoring-commit-summary graph-object-authoring-commit-summary--success"
          data-testid="graph-object-authoring-commit-summary"
          role="status"
        >
          <div className="graph-object-authoring-commit-summary-header">
            <h5>Write succeeded</h5>
            <button
              type="button"
              className="graph-object-authoring-commit-summary-dismiss"
              data-testid="graph-object-authoring-commit-summary-dismiss"
              onClick={() => setCommitted(null)}
            >
              Dismiss
            </button>
          </div>
          <p className="graph-object-authoring-commit-success-lead">
            Authored graph memory was written to disk. Reload graph review or refresh authored
            overlay data to see it in the graph.
          </p>
          {onRefreshProjection ? (
            <div className="graph-object-authoring-commit-refresh-actions">
              <button
                type="button"
                data-testid="graph-object-authoring-refresh-projection"
                disabled={refreshingProjection}
                onClick={() => {
                  setRefreshProjectionError(null);
                  setRefreshingProjection(true);
                  void onRefreshProjection()
                    .catch((error) => {
                      setRefreshProjectionError(parseApiError(error));
                    })
                    .finally(() => {
                      setRefreshingProjection(false);
                    });
                }}
              >
                {refreshingProjection ? "Refreshing graph review…" : "Refresh graph review"}
              </button>
            </div>
          ) : null}
          {refreshProjectionError ? (
            <p className="graph-object-authoring-error" role="alert">
              {refreshProjectionError}
            </p>
          ) : null}
          <p>Overlay: {committed.overlay_path}</p>
          <p>Event log: {committed.event_log_path}</p>
          {committed.backup_path ? <p>Backup: {committed.backup_path}</p> : null}
          <p>New overlay token: {shortToken(committed.new_overlay_token)}</p>
          <p>
            {committed.assertion_count} assertion(s), {committed.event_count} event record(s)
          </p>
          <ul className="graph-object-authoring-no-mutation-list">
            {committed.no_mutation_guarantees.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
