import { useMemo, useState } from "react";

import type {
  ExtractPromotePrepareResponse,
  ExtractPromotionReviewItem,
  ExtractPromoteReviewSummary,
} from "../../api/types";
import {
  countSelectableSelected,
  initialPromoteSelection,
  togglePromoteSelection,
} from "./extractPromoteSelectionUtils";

export interface GraphReviewExtractPromoteSheetProps {
  prepared: ExtractPromotePrepareResponse;
  onClose: () => void;
}

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

/**
 * Game-facing promote review sheet (PR011A2).
 *
 * Holds sealed reviewPackage + selected assertion ids for PR011A3 confirm.
 * Confirm CTA is intentionally omitted until A3 — selection count stays visible.
 */
export function GraphReviewExtractPromoteSheet({
  prepared,
  onClose,
}: GraphReviewExtractPromoteSheetProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() =>
    initialPromoteSelection(prepared.reviewItems),
  );

  const selectedCount = useMemo(
    () => countSelectableSelected(prepared.reviewItems, selectedIds),
    [prepared.reviewItems, selectedIds],
  );

  const summaryLines = formatSummaryLines(prepared.reviewSummary);

  const toggle = (item: ExtractPromotionReviewItem) => {
    if (!item.selectable) return;
    setSelectedIds((prev) =>
      togglePromoteSelection(prepared.reviewItems, prev, item.assertionId),
    );
  };

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
        <button type="button" className="secondary" onClick={onClose}>
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

      <ul className="graph-review-extract-promote-items">
        {prepared.reviewItems.map((item) => {
          const checked = item.selectable && selectedIds.has(item.assertionId);
          return (
            <li
              key={item.assertionId}
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
                  disabled={!item.selectable}
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

      <footer className="graph-review-extract-promote-sheet-footer">
        <p
          className="graph-review-extract-promote-confirm-note"
          data-testid="graph-review-extract-promote-selection-status"
          data-selected-count={selectedCount}
          data-review-package-digest={prepared.proposalDigest}
        >
          {selectedCount === 0
            ? "Select at least one accepted change to enable confirmation in PR011A3."
            : `${selectedCount} change${selectedCount === 1 ? "" : "s"} selected. Confirmation that advances the World Graph head lands in PR011A3.`}
        </p>
      </footer>
    </section>
  );
}
