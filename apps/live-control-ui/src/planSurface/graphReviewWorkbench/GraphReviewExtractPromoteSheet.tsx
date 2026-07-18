import { useMemo, useState } from "react";

import type {
  ExtractPromotePrepareResponse,
  ExtractPromotionReviewItem,
  ExtractPromoteReviewSummary,
} from "../../api/types";

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

function initialSelection(items: ExtractPromotionReviewItem[]): Set<string> {
  return new Set(
    items.filter((item) => item.selectable && item.selectedByDefault).map((item) => item.assertionId),
  );
}

/**
 * Game-facing promote review sheet (PR011A2).
 *
 * Holds sealed reviewPackage + selected assertion ids for PR011A3 confirm.
 * Merge CTA does not POST confirm in this slice.
 */
export function GraphReviewExtractPromoteSheet({
  prepared,
  onClose,
}: GraphReviewExtractPromoteSheetProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() =>
    initialSelection(prepared.reviewItems),
  );

  const selectedCount = useMemo(() => {
    let count = 0;
    for (const item of prepared.reviewItems) {
      if (item.selectable && selectedIds.has(item.assertionId)) {
        count += 1;
      }
    }
    return count;
  }, [prepared.reviewItems, selectedIds]);

  const summaryLines = formatSummaryLines(prepared.reviewSummary);

  const toggle = (item: ExtractPromotionReviewItem) => {
    if (!item.selectable) return;
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(item.assertionId)) {
        next.delete(item.assertionId);
      } else {
        next.add(item.assertionId);
      }
      return next;
    });
  };

  return (
    <section
      className="graph-review-extract-promote-sheet"
      data-testid="graph-review-extract-promote-sheet"
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
        <p className="graph-review-extract-promote-confirm-note">
          Confirmation that advances the World Graph head lands in the next slice (PR011A3).
        </p>
        <button
          type="button"
          className="primary"
          disabled={selectedCount === 0}
          title={
            selectedCount === 0
              ? "Select at least one accepted change"
              : "Confirm merge arrives in PR011A3"
          }
          data-testid="graph-review-extract-promote-merge-cta"
          data-selected-count={selectedCount}
          data-review-package-digest={prepared.proposalDigest}
          // Sealed package + selection retained for A3; no confirm POST here.
          onClick={() => undefined}
        >
          {`Merge ${selectedCount} change${selectedCount === 1 ? "" : "s"} into campaign memory`}
        </button>
      </footer>
    </section>
  );
}
