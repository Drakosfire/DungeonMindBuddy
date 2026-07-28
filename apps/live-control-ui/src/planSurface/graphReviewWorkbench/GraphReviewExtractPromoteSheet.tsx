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

function outcomeLabel(outcome: ExtractPromoteConfirmReceipt["outcome"]): string {
  switch (outcome) {
    case "committed":
      return "Committed";
    case "already_applied":
      return "Already applied";
    case "published_audit_degraded":
      return "Committed with degraded audit";
    default:
      return outcome;
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

/**
 * Game-facing promote review sheet (PR011A2 prepare + PR011A3 confirm).
 */
export function GraphReviewExtractPromoteSheet({
  prepared,
  onClose,
  onConfirmInFlightChange,
  onCatalogRefresh = defaultCatalogRefresh,
}: GraphReviewExtractPromoteSheetProps) {
  const { adoptCommittedReceipt, reloadCommittedAuthority } =
    useGraphReviewLiveState();

  const [selectedIds, setSelectedIds] = useState<Set<string>>(() =>
    initialPromoteSelection(prepared.reviewItems),
  );
  const [confirmPhase, setConfirmPhase] = useState<ConfirmPhase>("idle");
  const [frozenIds, setFrozenIds] = useState<string[] | null>(null);
  const [receipt, setReceipt] = useState<ExtractPromoteConfirmReceipt | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [reloadError, setReloadError] = useState<string | null>(null);
  const [reloadingRevision, setReloadingRevision] = useState(false);

  const confirming = confirmPhase === "confirming";
  const selectionLocked = confirming || confirmPhase === "receipt";
  const hasTerminalReceipt = receipt != null;

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

  const adoptTerminalReceipt = useCallback(
    async (nextReceipt: ExtractPromoteConfirmReceipt) => {
      setReloadError(null);
      try {
        // Provider owns receipt adoption, including campaignless fail-closed reads.
        await adoptCommittedReceipt(nextReceipt, prepared);
      } catch (error) {
        setReloadError(
          error instanceof Error
            ? error.message
            : "Failed to reload committed World Graph revision.",
        );
      }
    },
    [adoptCommittedReceipt, prepared],
  );

  const runConfirm = useCallback(
    async (assertionIds: string[]) => {
      setConfirmPhase("confirming");
      setConfirmError(null);
      setReloadError(null);

      let nextReceipt: ExtractPromoteConfirmReceipt;
      try {
        nextReceipt = await confirmExtractPromote({
          reviewPackage: prepared.reviewPackage,
          assertionIds,
        });
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
        return;
      }

      // Terminal receipt is authoritative immediately — never leave this phase.
      setReceipt(nextReceipt);
      setConfirmPhase("receipt");

      // Adopt before catalog refresh so a refresh-driven binding change cannot
      // race ahead of freezing committed authority for the current binding.
      try {
        await adoptTerminalReceipt(nextReceipt);
      } catch (error) {
        // adoptTerminalReceipt already catches; never flip phase away from receipt.
        setReloadError(
          error instanceof Error
            ? error.message
            : "Failed to reload committed World Graph revision.",
        );
      }

      try {
        await onCatalogRefresh();
      } catch {
        // Catalog refresh failure must not erase receipt.
      }
    },
    [adoptTerminalReceipt, onCatalogRefresh, prepared.reviewPackage],
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

  const onReloadCommittedRevision = async () => {
    if (!receipt) return;
    setReloadingRevision(true);
    setReloadError(null);
    try {
      // Retry loads committed authority only — never re-confirm.
      await reloadCommittedAuthority();
    } catch (error) {
      setReloadError(
        error instanceof Error
          ? error.message
          : "Failed to reload committed World Graph revision.",
      );
    } finally {
      setReloadingRevision(false);
    }
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

      {summaryLines.length ? (
        <ul className="graph-review-extract-promote-summary">
          {summaryLines.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}

      {receipt ? (
        <div
          className="graph-review-extract-promote-receipt"
          data-testid="graph-review-extract-promote-receipt"
          data-outcome={receipt.outcome}
        >
          <p className="graph-review-extract-promote-receipt-outcome">
            {outcomeLabel(receipt.outcome)}
          </p>
          <p className="graph-review-extract-promote-receipt-revision">
            {receipt.parentRevisionId} → {receipt.committedRevisionId}
          </p>
          <p className="graph-review-extract-promote-receipt-applied">
            Applied {receipt.appliedAssertionCount} change
            {receipt.appliedAssertionCount === 1 ? "" : "s"} to campaign memory.
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
            ? "These changes are committed to campaign memory."
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

        {confirmPhase === "unknown_result" && !hasTerminalReceipt ? (
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

        {receipt ? (
          <button
            type="button"
            className="secondary"
            data-testid="graph-review-extract-promote-reload-revision"
            disabled={reloadingRevision}
            onClick={() => void onReloadCommittedRevision()}
          >
            {reloadingRevision ? "Reloading…" : "Reload committed revision"}
          </button>
        ) : null}
      </footer>
    </section>
  );
}
