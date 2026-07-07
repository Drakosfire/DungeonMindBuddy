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

function formatAssertionSummary(summary: GraphObjectAuthoringPrepareResponse["overlay_summary"]): string[] {
  const lines: string[] = [];
  if (summary.object_count) {
    lines.push(`${summary.object_count} new object${summary.object_count === 1 ? "" : "s"}`);
  }
  if (summary.link_existing_count) {
    lines.push(
      `${summary.link_existing_count} linked alias${summary.link_existing_count === 1 ? "" : "es"}`,
    );
  }
  if (summary.relationship_count) {
    lines.push(
      `${summary.relationship_count} relationship${summary.relationship_count === 1 ? "" : "s"}`,
    );
  }
  if (summary.merge_objects_count) {
    lines.push(
      `${summary.merge_objects_count} identity merge${summary.merge_objects_count === 1 ? "" : "s"}`,
    );
  }
  return lines;
}

function PreparePreviewPrimary({
  prepared,
}: {
  prepared: GraphObjectAuthoringPrepareResponse;
}) {
  const assertionLines = formatAssertionSummary(prepared.overlay_summary);

  return (
    <div
      className="graph-object-authoring-prepare-preview"
      data-testid="graph-object-authoring-prepare-preview"
    >
      <h5>Prepared write preview</h5>
      {assertionLines.length ? (
        <ul className="graph-object-authoring-prepare-preview-summary">
          {assertionLines.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
      <p className="graph-object-authoring-prepare-preview-safety">
        Safe write preview generated. No source recap or extracted graph artifacts will be mutated.
      </p>
      <GraphObjectAuthoringOverlapWarnings
        warnings={toOverlapWarnings(prepared.diagnostics)}
        title="Prepare review warnings"
      />
      <details
        className="graph-object-authoring-write-safety-details-panel"
        data-testid="graph-object-authoring-write-safety-details"
      >
        <summary>Write safety details</summary>
        <ul className="graph-object-authoring-no-mutation-list">
          {prepared.no_mutation_guarantees.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </details>
      <details
        className="graph-object-authoring-technical-write-details-panel"
        data-testid="graph-object-authoring-technical-write-details"
      >
        <summary>Technical write details</summary>
        <dl className="graph-object-authoring-technical-write-fields">
          <div>
            <dt>Target overlay</dt>
            <dd>{prepared.overlay_path}</dd>
          </div>
          <div>
            <dt>Event log</dt>
            <dd>{prepared.event_log_path}</dd>
          </div>
          <div>
            <dt>Current overlay token</dt>
            <dd>{shortToken(prepared.current_overlay_token)}</dd>
          </div>
          <div>
            <dt>Proposed assertions digest</dt>
            <dd>{shortToken(prepared.proposed_assertions_digest)}</dd>
          </div>
        </dl>
      </details>
    </div>
  );
}

function CommitSuccessPrimary({
  committed,
  onRefreshProjection,
  refreshingProjection,
  refreshProjectionError,
  onRefresh,
  onDismiss,
}: {
  committed: GraphObjectAuthoringCommitResponse;
  onRefreshProjection?: () => Promise<unknown>;
  refreshingProjection: boolean;
  refreshProjectionError: string | null;
  onRefresh: () => void;
  onDismiss: () => void;
}) {
  return (
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
          onClick={onDismiss}
        >
          Dismiss
        </button>
      </div>
      <p className="graph-object-authoring-commit-success-lead">
        Authored graph memory was saved.
      </p>
      <p className="graph-object-authoring-commit-success-next">
        {onRefreshProjection
          ? "Next: refresh graph review to see the authored memory in the recap and graph cards."
          : "Reload graph review to see the authored memory."}
      </p>
      {onRefreshProjection ? (
        <div className="graph-object-authoring-commit-refresh-actions">
          <button
            type="button"
            data-testid="graph-object-authoring-refresh-projection"
            disabled={refreshingProjection}
            onClick={onRefresh}
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
      <details
        className="graph-object-authoring-write-details-panel"
        data-testid="graph-object-authoring-commit-write-details"
      >
        <summary>Write details</summary>
        <dl className="graph-object-authoring-technical-write-fields">
          <div>
            <dt>Overlay</dt>
            <dd>{committed.overlay_path}</dd>
          </div>
          <div>
            <dt>Event log</dt>
            <dd>{committed.event_log_path}</dd>
          </div>
          {committed.backup_path ? (
            <div>
              <dt>Backup</dt>
              <dd>{committed.backup_path}</dd>
            </div>
          ) : null}
          <div>
            <dt>New overlay token</dt>
            <dd>{shortToken(committed.new_overlay_token)}</dd>
          </div>
          <div>
            <dt>Assertion / event counts</dt>
            <dd>
              {committed.assertion_count} assertion(s), {committed.event_count} event record(s)
            </dd>
          </div>
        </dl>
        <ul className="graph-object-authoring-no-mutation-list">
          {committed.no_mutation_guarantees.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </details>
    </div>
  );
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

  function handleRefreshProjection() {
    if (!onRefreshProjection) {
      return;
    }
    setRefreshProjectionError(null);
    setRefreshingProjection(true);
    void onRefreshProjection()
      .catch((error) => {
        setRefreshProjectionError(parseApiError(error));
      })
      .finally(() => {
        setRefreshingProjection(false);
      });
  }

  if (proposals.length === 0 && !committed) {
    return null;
  }

  return (
    <div
      className="graph-object-authoring-prepare-commit-panel"
      aria-label="Prepare and commit authored graph memory"
      data-testid="graph-object-authoring-prepare-commit-panel"
    >
      {proposals.length > 0 ? (
        <div className="graph-object-authoring-prepare-commit-actions">
          <button
            type="button"
            data-testid="graph-object-authoring-prepare-button"
            disabled={!canPrepare}
            onClick={() => void handlePrepare()}
          >
            {preparing ? "Preparing…" : "Prepare staged memory"}
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
        <PreparePreviewPrimary prepared={prepared} />
      ) : null}

      {commitError ? (
        <p className="graph-object-authoring-prepare-commit-error" role="alert">
          {commitError}
        </p>
      ) : null}

      {committed ? (
        <CommitSuccessPrimary
          committed={committed}
          onRefreshProjection={onRefreshProjection}
          refreshingProjection={refreshingProjection}
          refreshProjectionError={refreshProjectionError}
          onRefresh={handleRefreshProjection}
          onDismiss={() => setCommitted(null)}
        />
      ) : null}
    </div>
  );
}
