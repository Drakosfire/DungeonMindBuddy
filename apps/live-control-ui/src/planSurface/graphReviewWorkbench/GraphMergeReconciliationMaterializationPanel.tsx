// PR003_LEGACY_GRAPH_PREVIEW_EXEMPTION:
// Retained until PR007/PR008 removes preview/latest-ingest selectors from surface APIs.
import { useState } from "react";

import {
  applyGraphMergeReconciliationMaterialization,
  prepareGraphMergeReconciliationMaterialization,
} from "../../api/liveApi";
import type {
  GraphMergeReconciliationApplyResponse,
  GraphMergeReconciliationPrepareResponse,
  UnionSupergraphProjectionResponse,
} from "../../api/types";

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

function shortToken(token: string): string {
  if (token.length <= 16) {
    return token;
  }
  return `${token.slice(0, 8)}…${token.slice(-8)}`;
}

function formatPlanSummary(summary: GraphMergeReconciliationPrepareResponse["summary"]): string[] {
  const lines: string[] = [];
  if (summary.merge_assertion_count) {
    lines.push(
      `${summary.merge_assertion_count} committed identity merge${summary.merge_assertion_count === 1 ? "" : "s"} found`,
    );
  }
  if (summary.applicable_assertion_count) {
    lines.push(
      `${summary.applicable_assertion_count} would apply now (${summary.redirect_count} redirect${summary.redirect_count === 1 ? "" : "s"}, ${summary.edge_rewire_count} edge rewire${summary.edge_rewire_count === 1 ? "" : "s"})`,
    );
  }
  if (summary.already_materialized_assertion_count) {
    lines.push(
      `${summary.already_materialized_assertion_count} already materialized in the union store`,
    );
  }
  if (summary.skipped_assertion_count) {
    lines.push(
      `${summary.skipped_assertion_count} not applicable from current overlay/store state`,
    );
  }
  return lines;
}

function formatApplySummary(summary: GraphMergeReconciliationApplyResponse["summary"]): string {
  const parts = [
    `${summary.redirects_added} redirect${summary.redirects_added === 1 ? "" : "s"} added`,
    `${summary.merge_records_added} merge record${summary.merge_records_added === 1 ? "" : "s"} added`,
    `${summary.edges_rewired} edge${summary.edges_rewired === 1 ? "" : "s"} rewired`,
  ];
  if (summary.edges_deduped) {
    parts.push(`${summary.edges_deduped} duplicate edge${summary.edges_deduped === 1 ? "" : "s"} removed`);
  }
  return parts.join("; ");
}

export interface GraphMergeReconciliationMaterializationPanelProps {
  campaignId: string;
  sessionId: string;
  campaignRel?: string | null;
  previewUnionStorePath?: string | null;
  onRefreshProjection?: () => Promise<UnionSupergraphProjectionResponse>;
}

export function GraphMergeReconciliationMaterializationPanel({
  campaignId,
  sessionId,
  campaignRel,
  previewUnionStorePath,
  onRefreshProjection,
}: GraphMergeReconciliationMaterializationPanelProps) {
  const [prepared, setPrepared] = useState<GraphMergeReconciliationPrepareResponse | null>(null);
  const [applied, setApplied] = useState<GraphMergeReconciliationApplyResponse | null>(null);
  const [prepareError, setPrepareError] = useState<string | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [preparing, setPreparing] = useState(false);
  const [applying, setApplying] = useState(false);
  const [refreshingProjection, setRefreshingProjection] = useState(false);
  const [refreshProjectionError, setRefreshProjectionError] = useState<string | null>(null);

  const canPrepare = Boolean(previewUnionStorePath) && !preparing;
  const canApply =
    prepared !== null &&
    prepared.summary.applicable_assertion_count > 0 &&
    !applying;

  async function handlePrepare() {
    if (!previewUnionStorePath) {
      return;
    }
    setPrepareError(null);
    setApplyError(null);
    setApplied(null);
    setPreparing(true);
    try {
      const response = await prepareGraphMergeReconciliationMaterialization({
        campaignId,
        campaignRel,
        sessionId,
        previewUnionStorePath,
      });
      setPrepared(response);
    } catch (error) {
      setPrepared(null);
      setPrepareError(parseApiError(error));
    } finally {
      setPreparing(false);
    }
  }

  async function handleApply() {
    if (!prepared || !previewUnionStorePath) {
      return;
    }
    setApplyError(null);
    setApplying(true);
    try {
      const response = await applyGraphMergeReconciliationMaterialization({
        campaignId,
        campaignRel,
        sessionId,
        previewUnionStorePath,
        materializationPassId: prepared.materialization_pass_id,
        confirmToken: prepared.confirm_token,
        overlayToken: prepared.overlay_token,
        unionStoreToken: prepared.union_store_token,
      });
      setApplied(response);
      if (onRefreshProjection) {
        setRefreshingProjection(true);
        setRefreshProjectionError(null);
        try {
          await onRefreshProjection();
        } catch (error) {
          setRefreshProjectionError(parseApiError(error));
        } finally {
          setRefreshingProjection(false);
        }
      }
    } catch (error) {
      const message = parseApiError(error);
      let errorCode: string | null = null;
      if (error instanceof Error) {
        try {
          const parsed = JSON.parse(error.message) as { code?: string };
          errorCode = parsed.code ?? null;
        } catch {
          // ignore
        }
      }
      if (
        errorCode === "stale_overlay" ||
        errorCode === "stale_union_store" ||
        message.includes("stale_overlay") ||
        message.includes("stale_union_store") ||
        message.includes("changed since")
      ) {
        setApplyError(
          "The overlay or union store changed since this preview was prepared. Prepare again before applying.",
        );
      } else if (message.includes("confirm_token") || errorCode === "confirm_token_mismatch") {
        setApplyError(
          "The prepared preview no longer matches the current state. Prepare again before applying.",
        );
      } else {
        setApplyError(message);
      }
    } finally {
      setApplying(false);
    }
  }

  if (!previewUnionStorePath) {
    return (
      <div
        className="graph-merge-reconciliation-materialization-panel graph-merge-reconciliation-materialization-panel--unavailable"
        data-testid="graph-merge-reconciliation-materialization-panel"
      >
        <h5>Durable identity materialization</h5>
        <p className="graph-merge-reconciliation-materialization-lead">
          Select a live ingest run with a preview union graph store to materialize committed identity merges.
        </p>
      </div>
    );
  }

  return (
    <div
      className="graph-merge-reconciliation-materialization-panel"
      aria-label="Durable identity materialization"
      data-testid="graph-merge-reconciliation-materialization-panel"
    >
      <h5>Durable identity materialization</h5>
      <p className="graph-merge-reconciliation-materialization-lead">
        Committed identity merges are saved in authored graph memory. This step makes those reviewed merge
        decisions durable in the selected union graph store.
      </p>
      <p className="graph-merge-reconciliation-materialization-safety">
        This writes identity redirects to the selected union graph store. It does not mutate source recap
        markdown, extracted run artifacts, or candidate graph gold.
      </p>

      <div className="graph-merge-reconciliation-materialization-actions">
        <button
          type="button"
          data-testid="graph-merge-reconciliation-prepare-button"
          disabled={!canPrepare}
          onClick={() => void handlePrepare()}
        >
          {preparing ? "Preparing…" : "Prepare identity materialization"}
        </button>
        {prepared && prepared.summary.applicable_assertion_count > 0 ? (
          <button
            type="button"
            data-testid="graph-merge-reconciliation-apply-button"
            disabled={!canApply}
            onClick={() => void handleApply()}
          >
            {applying ? "Applying…" : "Apply durable identity merge"}
          </button>
        ) : null}
      </div>

      {prepareError ? (
        <p className="graph-merge-reconciliation-materialization-error" role="alert">
          {prepareError}
        </p>
      ) : null}

      {prepared && !applied ? (
        <div
          className="graph-merge-reconciliation-prepare-preview"
          data-testid="graph-merge-reconciliation-prepare-preview"
        >
          {formatPlanSummary(prepared.summary).length ? (
            <ul className="graph-merge-reconciliation-prepare-summary">
              {formatPlanSummary(prepared.summary).map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          ) : null}
          {prepared.summary.applicable_assertion_count > 0 ? (
            <p className="graph-merge-reconciliation-prepare-safety">
              Safe preview generated. No union store writes occurred during prepare.
            </p>
          ) : (
            <p
              className="graph-merge-reconciliation-no-plans"
              data-testid="graph-merge-reconciliation-no-plans"
            >
              No committed identity merges need materialization for this overlay and union store.
            </p>
          )}
          <details className="graph-merge-reconciliation-technical-details">
            <summary>Technical materialization details</summary>
            <dl className="graph-merge-reconciliation-technical-fields">
              <div>
                <dt>Union store</dt>
                <dd>{prepared.union_store_path}</dd>
              </div>
              <div>
                <dt>Overlay</dt>
                <dd>{prepared.overlay_path}</dd>
              </div>
              <div>
                <dt>Materialization pass</dt>
                <dd>{prepared.materialization_pass_id}</dd>
              </div>
              <div>
                <dt>Plan digest</dt>
                <dd>{shortToken(prepared.plan_digest)}</dd>
              </div>
            </dl>
          </details>
        </div>
      ) : null}

      {applyError ? (
        <p className="graph-merge-reconciliation-materialization-error" role="alert">
          {applyError}
        </p>
      ) : null}

      {applied ? (
        <div
          className="graph-merge-reconciliation-apply-summary"
          data-testid="graph-merge-reconciliation-apply-summary"
          role="status"
        >
          <p className="graph-merge-reconciliation-apply-success-lead">
            Durable identity merge applied. Refresh Graph Review to inspect the survivor identity.
          </p>
          <p className="graph-merge-reconciliation-apply-success-counts">
            {formatApplySummary(applied.summary)}
          </p>
          {onRefreshProjection ? (
            <p className="graph-merge-reconciliation-refresh-status">
              {refreshingProjection
                ? "Refreshing graph review…"
                : refreshProjectionError
                  ? refreshProjectionError
                  : "Graph review refreshed."}
            </p>
          ) : null}
          <details className="graph-merge-reconciliation-technical-details">
            <summary>Technical apply details</summary>
            <dl className="graph-merge-reconciliation-technical-fields">
              <div>
                <dt>Backup path</dt>
                <dd>{applied.backup_path ?? "—"}</dd>
              </div>
              <div>
                <dt>Union store</dt>
                <dd>{applied.union_store_path}</dd>
              </div>
              {applied.applied_assertion_ids.length ? (
                <div>
                  <dt>Applied assertion ids</dt>
                  <dd>{applied.applied_assertion_ids.join(", ")}</dd>
                </div>
              ) : null}
              {applied.skipped_assertion_ids.length ? (
                <div>
                  <dt>Skipped assertion ids</dt>
                  <dd>{applied.skipped_assertion_ids.join(", ")}</dd>
                </div>
              ) : null}
            </dl>
          </details>
        </div>
      ) : null}
    </div>
  );
}
