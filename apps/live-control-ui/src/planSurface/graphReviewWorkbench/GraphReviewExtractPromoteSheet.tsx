import { useCallback, useEffect, useMemo, useState } from "react";

import {
  confirmExtractPromote,
  ExtractPromoteApiError,
} from "../../api/extractPromoteApi";
import type {
  ExtractPromoteConfirmReceipt,
  ExtractPromotePrepareResponse,
  ExtractPromotionReviewItem,
  ExtractPromoteReviewSummary,
} from "../../api/types";
import {
  countSelectableSelected,
  initialPromoteSelection,
  selectedPromoteAssertionIds,
  togglePromoteSelection,
} from "./extractPromoteSelectionUtils";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";
import { GRAPH_REVIEW_RUNS_CHANGED_EVENT } from "./graphReviewWorkbenchUtils";

export interface GraphReviewExtractPromoteSheetProps {
  prepared: ExtractPromotePrepareResponse;
  onClose: () => void;
  onConfirmInFlightChange?: (inFlight: boolean) => void;
  onCatalogRefresh?: () => void | Promise<void>;
}

type ConfirmPhase = "idle" | "confirming" | "receipt" | "pre_commit_error" | "unknown_result";

function formatSummaryLines(summary: ExtractPromoteReviewSummary): string[] {
  const lines: string[] = [];
  if (summary.newObjectCount) {
    lines.push(
      `${summary.newObjectCount} new object${summary.newObjectCount === 1 ? "" : "s"}`,
    );
  }
  if (summary.connectExistingCount) {
    lines.push(
      `${summary.connectExistingCount} connection${summary.connectExistingCount === 1 ? "" : "s"} to existing objects`,
    );
  }
  if (summary.relationshipCount) {
    lines.push(
      `${summary.relationshipCount} relationship${summary.relationshipCount === 1 ? "" : "s"}`,
    );
  }
  if (summary.unresolvedMentionCount) {
    lines.push(
      `${summary.unresolvedMentionCount} unresolved mention${summary.unresolvedMentionCount === 1 ? "" : "s"}`,
    );
  }
  if (summary.rejectedAssertionCount) {
    lines.push(
      `${summary.rejectedAssertionCount} rejected assertion${summary.rejectedAssertionCount === 1 ? "" : "s"}`,
    );
  }
  return lines;
}

function actionLabel(action: ExtractPromotionReviewItem["action"]): string {
  switch (action) {
    case "create":
      return "Create new";
    case "connect_existing":
      return "Connect existing";
    default:
      return "Update";
  }
}

function outcomeHeadline(outcome: ExtractPromoteConfirmReceipt["outcome"]): string {
  switch (outcome) {
    case "committed":
      return "Merged into campaign memory";
    case "already_applied":
      return "Already in campaign memory";
    case "published_audit_degraded":
      return "Merged into campaign memory";
    default:
      return "Merge finished";
  }
}

function outcomeDetail(outcome: ExtractPromoteConfirmReceipt["outcome"]): string {
  switch (outcome) {
    case "committed":
      return "These selected changes are now part of the World Graph.";
    case "already_applied":
      return "This exact selection was already published; nothing new was written.";
    case "published_audit_degraded":
      return "Campaign memory advanced. Post-publish audit reported a warning — the merge itself succeeded.";
    default:
      return "Campaign memory update completed.";
  }
}

function confirmErrorMessage(error: unknown): string {
  if (error instanceof ExtractPromoteApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Failed to confirm promotion.";
}

async function defaultCatalogRefresh(): Promise<void> {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(GRAPH_REVIEW_RUNS_CHANGED_EVENT));
}

type ProjectionSyncPhase = "idle" | "syncing" | "ready" | "error";

/**
 * Game-facing promote review sheet (PR011A2 prepare + PR011A3 confirm).
 */
export function GraphReviewExtractPromoteSheet({
  prepared,
  onClose,
  onConfirmInFlightChange,
  onCatalogRefresh = defaultCatalogRefresh,
}: GraphReviewExtractPromoteSheetProps) {
  const { reloadCommittedWorldProjection, selectDurableObjectIds } =
    useGraphReviewLiveState();

  const [selectedIds, setSelectedIds] = useState<Set<string>>(() =>
    initialPromoteSelection(prepared.reviewItems),
  );
  const [confirmPhase, setConfirmPhase] = useState<ConfirmPhase>("idle");
  const [frozenIds, setFrozenIds] = useState<string[] | null>(null);
  const [receipt, setReceipt] = useState<ExtractPromoteConfirmReceipt | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [reloadError, setReloadError] = useState<string | null>(null);
  const [projectionSyncPhase, setProjectionSyncPhase] =
    useState<ProjectionSyncPhase>("idle");

  const confirming = confirmPhase === "confirming";
  const selectionLocked = confirming || confirmPhase === "receipt";
  const hasTerminalReceipt = receipt != null;
  const syncingProjection = projectionSyncPhase === "syncing";

  useEffect(() => {
    onConfirmInFlightChange?.(confirming);
  }, [confirming, onConfirmInFlightChange]);

  const effectiveSelectedIds = useMemo(() => {
    if (frozenIds == null) return selectedIds;
    return new Set(frozenIds);
  }, [frozenIds, selectedIds]);

  const selectedCount = useMemo(
    () => countSelectableSelected(prepared.reviewItems, effectiveSelectedIds),
    [prepared.reviewItems, effectiveSelectedIds],
  );

  const summaryLines = formatSummaryLines(prepared.reviewSummary);

  const toggle = (item: ExtractPromotionReviewItem) => {
    if (!item.selectable || selectionLocked) return;
    setSelectedIds((prev) =>
      togglePromoteSelection(prepared.reviewItems, prev, item.sliceQualifiedId),
    );
  };

  const applyCommittedRevision = useCallback(
    async (nextReceipt: ExtractPromoteConfirmReceipt): Promise<boolean> => {
      setReloadError(null);
      try {
        await reloadCommittedWorldProjection(
          nextReceipt.committedRevisionId,
          nextReceipt.worldId,
        );
        selectDurableObjectIds(nextReceipt.affectedObjectIds);
        return true;
      } catch (error) {
        setReloadError(
          error instanceof Error
            ? error.message
            : "Failed to reload committed World Graph revision.",
        );
        return false;
      }
    },
    [reloadCommittedWorldProjection, selectDurableObjectIds],
  );

  const startBackgroundProjectionSync = useCallback(
    (nextReceipt: ExtractPromoteConfirmReceipt) => {
      setProjectionSyncPhase("syncing");
      setReloadError(null);
      void (async () => {
        try {
          await onCatalogRefresh();
        } catch {
          // Catalog refresh failure must not erase receipt or block World Graph sync.
        }
        const ok = await applyCommittedRevision(nextReceipt);
        setProjectionSyncPhase(ok ? "ready" : "error");
      })();
    },
    [applyCommittedRevision, onCatalogRefresh],
  );

  const runConfirm = useCallback(
    async (assertionIds: string[]) => {
      setConfirmPhase("confirming");
      setConfirmError(null);
      setReloadError(null);
      setProjectionSyncPhase("idle");
      try {
        const nextReceipt = await confirmExtractPromote({
          reviewPackage: prepared.reviewPackage,
          assertionIds,
        });
        // Paint the success receipt immediately; World Graph reload continues in
        // the background so the GM can read confirmation while sync starts.
        setReceipt(nextReceipt);
        setConfirmPhase("receipt");
        startBackgroundProjectionSync(nextReceipt);
      } catch (error) {
        if (error instanceof ExtractPromoteApiError) {
          setConfirmPhase("pre_commit_error");
          setConfirmError(confirmErrorMessage(error));
          return;
        }
        setConfirmPhase("unknown_result");
        setConfirmError(
          error instanceof Error
            ? error.message
            : "Confirm result is unknown due to a network error.",
        );
      }
    },
    [prepared.reviewPackage, startBackgroundProjectionSync],
  );

  const onMergeClick = () => {
    if (confirming || hasTerminalReceipt || selectedCount === 0) return;
    const ids = selectedPromoteAssertionIds(prepared.reviewItems, selectedIds);
    if (!ids.length) return;
    setFrozenIds(ids);
    void runConfirm(ids);
  };

  const onRetryExactConfirm = () => {
    const ids = frozenIds ?? selectedPromoteAssertionIds(prepared.reviewItems, selectedIds);
    if (!ids.length) return;
    setFrozenIds(ids);
    void runConfirm(ids);
  };

  const onRetryProjectionSync = () => {
    if (!receipt || syncingProjection) return;
    startBackgroundProjectionSync(receipt);
  };

  const showMergeCta =
    !hasTerminalReceipt && confirmPhase !== "unknown_result" && confirmPhase !== "pre_commit_error";

  return (
    <section
      className="graph-review-extract-promote-sheet"
      data-testid="graph-review-extract-promote-sheet"
      data-proposal-digest={prepared.proposalDigest}
      aria-label="Review proposed campaign memory changes"
    >
      <header className="graph-review-extract-promote-sheet-header">
        <div>
          <h4>Review proposed changes</h4>
          <p className="graph-review-extract-promote-sheet-meta">
            Parent revision {prepared.parentRevisionId}
            {prepared.runId ? ` · ${prepared.runId}` : ""}
          </p>
        </div>
        <button type="button" className="secondary" disabled={confirming} onClick={onClose}>
          Close
        </button>
      </header>

      {summaryLines.length && !hasTerminalReceipt ? (
        <ul className="graph-review-extract-promote-summary">
          {summaryLines.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}

      {receipt ? (
        <div
          className={
            receipt.outcome === "published_audit_degraded"
              ? "graph-review-extract-promote-receipt is-degraded"
              : "graph-review-extract-promote-receipt is-success"
          }
          data-testid="graph-review-extract-promote-receipt"
          data-outcome={receipt.outcome}
          data-projection-sync={projectionSyncPhase}
          role="status"
          aria-live="polite"
        >
          <p
            className="graph-review-extract-promote-receipt-outcome"
            data-testid="graph-review-extract-promote-receipt-headline"
          >
            {outcomeHeadline(receipt.outcome)}
          </p>
          <p className="graph-review-extract-promote-receipt-detail">
            {outcomeDetail(receipt.outcome)}
          </p>
          <p className="graph-review-extract-promote-receipt-applied">
            Applied {receipt.appliedAssertionCount} change
            {receipt.appliedAssertionCount === 1 ? "" : "s"}
            {receipt.headAdvanced ? " · head advanced" : ""}.
          </p>
          <p className="graph-review-extract-promote-receipt-revision">
            {receipt.parentRevisionId} → {receipt.committedRevisionId}
          </p>
          <p
            className="graph-review-extract-promote-receipt-sync"
            data-testid="graph-review-extract-promote-projection-sync"
          >
            {projectionSyncPhase === "syncing"
              ? "Updating World Graph view in the background…"
              : projectionSyncPhase === "ready"
                ? "World Graph view updated."
                : projectionSyncPhase === "error"
                  ? "Merge succeeded, but the World Graph view did not refresh."
                  : null}
          </p>
          {receipt.warnings.length ? (
            <ul className="graph-review-extract-promote-receipt-warnings">
              {receipt.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {confirmError ? (
        <p
          className="graph-review-extract-promote-error"
          data-testid="graph-review-extract-promote-confirm-error"
          role="alert"
        >
          {confirmError}
        </p>
      ) : null}

      {reloadError ? (
        <p
          className="graph-review-extract-promote-error"
          data-testid="graph-review-extract-promote-reload-error"
          role="alert"
        >
          {reloadError}
        </p>
      ) : null}

      {!hasTerminalReceipt ? (
        <ul className="graph-review-extract-promote-items">
          {prepared.reviewItems.map((item) => {
            const checked = item.selectable && effectiveSelectedIds.has(item.sliceQualifiedId);
            return (
              <li
                key={item.sliceQualifiedId}
                className={
                  item.selectable
                    ? "graph-review-extract-promote-item"
                    : "graph-review-extract-promote-item is-blocked"
                }
              >
                <label>
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={!item.selectable || selectionLocked}
                    onChange={() => toggle(item)}
                    aria-label={`Select ${item.label}`}
                  />
                  <span className="graph-review-extract-promote-item-body">
                    <span className="graph-review-extract-promote-item-title">
                      {item.label}
                      <span className="graph-review-extract-promote-item-badge">
                        {actionLabel(item.action)} · {item.kind}
                      </span>
                    </span>
                    <span className="graph-review-extract-promote-item-summary">{item.summary}</span>
                    {item.evidenceSummary ? (
                      <span className="graph-review-extract-promote-item-evidence">
                        {item.evidenceSummary}
                      </span>
                    ) : null}
                    {item.warnings.length ? (
                      <span className="graph-review-extract-promote-item-warnings">
                        {item.warnings.join("; ")}
                      </span>
                    ) : null}
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
      ) : null}

      <footer className="graph-review-extract-promote-sheet-footer">
        <p
          className="graph-review-extract-promote-confirm-note"
          data-testid="graph-review-extract-promote-selection-status"
          data-selected-count={selectedCount}
          data-review-package-digest={prepared.proposalDigest}
        >
          {hasTerminalReceipt
            ? projectionSyncPhase === "syncing"
              ? "Merge succeeded. You can close this panel while the World Graph catches up."
              : "Merge succeeded."
            : selectedCount === 0
              ? "Select at least one accepted change to merge into campaign memory."
              : `${selectedCount} change${selectedCount === 1 ? "" : "s"} selected.`}
        </p>

        {showMergeCta ? (
          <button
            type="button"
            className="primary"
            data-testid="graph-review-extract-promote-merge-cta"
            disabled={selectedCount === 0 || confirming}
            onClick={onMergeClick}
          >
            {confirming
              ? "Merging…"
              : `Merge ${selectedCount} change${selectedCount === 1 ? "" : "s"} into campaign memory`}
          </button>
        ) : null}

        {confirmPhase === "pre_commit_error" ? (
          <button
            type="button"
            className="primary"
            data-testid="graph-review-extract-promote-retry-confirm"
            disabled={confirming}
            onClick={onRetryExactConfirm}
          >
            Retry merge
          </button>
        ) : null}

        {confirmPhase === "unknown_result" ? (
          <button
            type="button"
            className="primary"
            data-testid="graph-review-extract-promote-retry-exact-confirm"
            disabled={confirming}
            onClick={onRetryExactConfirm}
          >
            Retry exact confirm
          </button>
        ) : null}

        {receipt && projectionSyncPhase === "error" ? (
          <button
            type="button"
            className="secondary"
            data-testid="graph-review-extract-promote-reload-revision"
            disabled={syncingProjection}
            onClick={onRetryProjectionSync}
          >
            {syncingProjection ? "Updating view…" : "Retry World Graph refresh"}
          </button>
        ) : null}

        {receipt ? (
          <button
            type="button"
            className="primary"
            data-testid="graph-review-extract-promote-done"
            onClick={onClose}
          >
            {syncingProjection ? "Done — view still updating" : "Done"}
          </button>
        ) : null}
      </footer>
    </section>
  );
}
