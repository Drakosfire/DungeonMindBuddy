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
  GraphAuthoringOverlayDiagnostic,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
import { GraphObjectAuthoringOverlapWarnings } from "./GraphObjectAuthoringOverlapWarnings";
import type { GraphObjectAuthoringOverlapWarning } from "./graphObjectAuthoringOverlap";
import type { GraphObjectAuthoringProposal } from "./graphObjectAuthoringDraft";
import { serializeGraphObjectAuthoringProposalForApi } from "./graphObjectAuthoringDraft";
import { parseGraphObjectAuthoringApiError } from "./graphObjectAuthoringApiErrors";

function authoringErrorCode(error: unknown): string | null {
  if (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    typeof error.code === "string"
  ) {
    return error.code;
  }
  if (error instanceof Error) {
    try {
      const parsed = JSON.parse(error.message) as { code?: string };
      return typeof parsed.code === "string" ? parsed.code : null;
    } catch {
      return null;
    }
  }
  return null;
}

function toProposalPayload(proposal: GraphObjectAuthoringProposal): GraphObjectAuthoringProposalPayload {
  return serializeGraphObjectAuthoringProposalForApi(
    proposal,
  ) as unknown as GraphObjectAuthoringProposalPayload;
}

function proposalsFingerprint(proposals: GraphObjectAuthoringProposal[]): string {
  return JSON.stringify(proposals.map((proposal) => proposal.localProposalId));
}

function shortToken(token: string | null | undefined): string {
  if (!token) {
    return "not bound";
  }
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
      {prepared.expressibility === "INEXPRESSIBLE" ? (
        <p
          className="graph-object-authoring-prepare-inexpressible"
          data-testid="graph-object-authoring-prepare-inexpressible"
          role="status"
        >
          This Graph Review operation is not currently publishable through DungeonMind.
          Identity merges cannot be confirmed until a native merge primitive exists.
        </p>
      ) : null}
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
            <dt>Expected DungeonMind parent</dt>
            <dd>{prepared.expected_parent_revision_id ?? "not bound"}</dd>
          </div>
          <div>
            <dt>World</dt>
            <dd>{prepared.world_id ?? "unresolved"}</dd>
          </div>
          <div>
            <dt>Operation</dt>
            <dd>{prepared.authority_operation_id ?? "not bound"}</dd>
          </div>
          <div>
            <dt>Proposed assertions digest</dt>
            <dd>{shortToken(prepared.proposed_assertions_digest)}</dd>
          </div>
          <div>
            <dt>Prepared contribution digest</dt>
            <dd>{shortToken(prepared.contribution_digest)}</dd>
          </div>
        </dl>
      </details>
    </div>
  );
}

function formatPublicationOutcome(
  committed: GraphObjectAuthoringCommitResponse,
): string {
  if (committed.idempotency_status === "already_applied") {
    return "Recovered the already-published DungeonMind revision. No additional write.";
  }
  return "Published exactly one DungeonMind World Graph revision.";
}

function CommitSuccessPrimary({
  committed,
  onRefreshProjection,
  refreshingProjection,
  refreshProjectionError,
  projectionDiagnostics,
  onRefresh,
  onDismiss,
}: {
  committed: GraphObjectAuthoringCommitResponse;
  onRefreshProjection?: () => Promise<unknown>;
  refreshingProjection: boolean;
  refreshProjectionError: string | null;
  projectionDiagnostics: GraphAuthoringOverlayDiagnostic[];
  onRefresh: () => void;
  onDismiss: () => void;
}) {
  const publicationMessage = formatPublicationOutcome(committed);

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
        {publicationMessage}
      </p>
      <p
        className="graph-object-authoring-commit-revision-outcome"
        data-testid="graph-object-authoring-commit-revision-outcome"
      >
        Parent {committed.parent_revision_id ?? "unknown"} → published{" "}
        {committed.published_revision_id ?? "unknown"}.
      </p>
      <p className="graph-object-authoring-commit-success-next">
        {refreshingProjection
          ? "Refreshing graph review…"
          : onRefreshProjection
            ? "Graph review refreshed. New pills and authored memory should appear in the recap."
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
      {projectionDiagnostics.length ? (
        <div
          className="graph-object-authoring-projection-diagnostics"
          data-testid="graph-object-authoring-projection-diagnostics"
          role="status"
        >
          <p className="graph-object-authoring-projection-diagnostics-title">
            Recap pill projection notes
          </p>
          <ul>
            {projectionDiagnostics.map((diagnostic) => (
              <li key={`${diagnostic.code}:${diagnostic.message}`}>{diagnostic.message}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <details
        className="graph-object-authoring-write-details-panel"
        data-testid="graph-object-authoring-commit-write-details"
      >
        <summary>Write details</summary>
        <dl className="graph-object-authoring-technical-write-fields">
          <div>
            <dt>World</dt>
            <dd>{committed.world_id ?? "unresolved"}</dd>
          </div>
          <div>
            <dt>Parent revision</dt>
            <dd>{committed.parent_revision_id ?? "unknown"}</dd>
          </div>
          <div>
            <dt>Published revision</dt>
            <dd>{committed.published_revision_id ?? "unknown"}</dd>
          </div>
          <div>
            <dt>Operation</dt>
            <dd>{committed.operation_id ?? "unknown"}</dd>
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
  previewUnionStorePath?: string | null;
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
  previewUnionStorePath: _previewUnionStorePath,
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
  const [projectionDiagnostics, setProjectionDiagnostics] = useState<GraphAuthoringOverlayDiagnostic[]>([]);

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
  const canCommit =
    prepared !== null &&
    prepared.expressibility !== "INEXPRESSIBLE" &&
    !proposalsChangedSincePrepare &&
    !committing;

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
        worldId: campaignId,
        sourceRunId,
        sourceGraphId,
        proposals: proposals.map(toProposalPayload),
      });
      setPrepared(response);
      setPreparedForFingerprint(currentFingerprint);
    } catch (error) {
      setPrepared(null);
      setPrepareError(parseGraphObjectAuthoringApiError(error));
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
        worldId: campaignId,
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
      if (onRefreshProjection) {
        setRefreshProjectionError(null);
        setProjectionDiagnostics([]);
        setRefreshingProjection(true);
        try {
          const refreshed = (await onRefreshProjection()) as
            | UnionSupergraphProjectionResponse
            | undefined;
          const diagnostics =
            refreshed?.authored_overlay?.diagnostics?.filter(
              (item) => item.severity !== "info",
            ) ?? [];
          setProjectionDiagnostics(diagnostics);
        } catch (error) {
          setRefreshProjectionError(parseGraphObjectAuthoringApiError(error));
        } finally {
          setRefreshingProjection(false);
        }
      }
    } catch (error) {
      const code = authoringErrorCode(error);
      const message = parseGraphObjectAuthoringApiError(error);
      if (code === "stale_parent") {
        setCommitError(
          "The World Graph advanced since this preview was prepared. Prepare again against current truth.",
        );
      } else if (code === "confirmation_invalid" || code === "confirmation_expired") {
        setCommitError(
          "The prepared preview no longer matches these proposals. Prepare again before confirming.",
        );
      } else if (code === "governed_write_inexpressible") {
        setCommitError(
          "This Graph Review operation cannot be published through DungeonMind.",
        );
      } else if (
        code === "source_unresolved" ||
        code === "source_artifact_not_found" ||
        code === "source_inadmissible"
      ) {
        setCommitError("Graph Review source provenance could not be admitted. No write was published.");
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
        setRefreshProjectionError(parseGraphObjectAuthoringApiError(error));
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
        <p
          className="graph-object-authoring-prepare-commit-error"
          data-testid="graph-object-authoring-commit-error"
          role="alert"
        >
          {commitError}
        </p>
      ) : null}

      {committed ? (
        <CommitSuccessPrimary
          committed={committed}
          onRefreshProjection={onRefreshProjection}
          refreshingProjection={refreshingProjection}
          refreshProjectionError={refreshProjectionError}
          projectionDiagnostics={projectionDiagnostics}
          onRefresh={handleRefreshProjection}
          onDismiss={() => {
            setCommitted(null);
            setProjectionDiagnostics([]);
          }}
        />
      ) : null}
    </div>
  );
}
