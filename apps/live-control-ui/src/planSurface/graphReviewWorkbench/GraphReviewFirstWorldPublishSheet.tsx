import { useCallback, useEffect, useMemo, useState } from "react";

import {
  confirmFirstWorldGraph,
  ExtractPromoteApiError,
  prepareFirstWorldGraph,
} from "../../api/extractPromoteApi";
import type {
  ExactRunReviewAssertion,
  ExactRunReviewPackage,
  FirstWorldDecision,
  FirstWorldDisposition,
  FirstWorldGraphConfirmReceipt,
  FirstWorldGraphPlan,
} from "../../api/types";
import { GRAPH_REVIEW_RUNS_CHANGED_EVENT } from "./graphReviewWorkbenchUtils";

export interface GraphReviewFirstWorldPublishSheetProps {
  review: ExactRunReviewPackage;
  onConfirmInFlightChange?: (inFlight: boolean) => void;
  onCatalogRefresh?: () => void | Promise<void>;
}

type PublishPhase =
  | "idle"
  | "publishing"
  | "receipt"
  | "pre_commit_error"
  | "unknown_result";

function formatWorldDisplayName(worldId: string): string {
  return worldId
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function parseRelationshipEndpoints(summary: string): [string, string] | null {
  const parts = summary.split("→").map((part) => part.trim());
  if (parts.length !== 2 || !parts[0] || !parts[1]) {
    return null;
  }
  return [parts[0], parts[1]];
}

function isEvidenceBacked(assertion: ExactRunReviewAssertion): boolean {
  return assertion.evidence.length > 0;
}

function buildInitialKeepState(assertions: ExactRunReviewAssertion[]): Map<string, boolean> {
  const objectKeep = new Map<string, boolean>();
  for (const assertion of assertions) {
    if (assertion.kind === "object") {
      objectKeep.set(assertion.assertionId, isEvidenceBacked(assertion));
    }
  }

  const keep = new Map<string, boolean>();
  for (const assertion of assertions) {
    if (assertion.kind === "object") {
      keep.set(assertion.assertionId, objectKeep.get(assertion.assertionId) ?? false);
      continue;
    }
    const endpoints = parseRelationshipEndpoints(assertion.summary);
    const endpointsKept =
      endpoints != null
      && (objectKeep.get(endpoints[0]) ?? false)
      && (objectKeep.get(endpoints[1]) ?? false);
    keep.set(
      assertion.assertionId,
      isEvidenceBacked(assertion) && endpointsKept,
    );
  }
  return keep;
}

function relationshipEndpointIds(
  assertion: ExactRunReviewAssertion,
): [string, string] | null {
  if (assertion.kind !== "relationship") return null;
  return parseRelationshipEndpoints(assertion.summary);
}

function isRelationshipBlocked(
  assertion: ExactRunReviewAssertion,
  keepByAssertionId: Map<string, boolean>,
): boolean {
  const endpoints = relationshipEndpointIds(assertion);
  if (!endpoints) return false;
  return !keepByAssertionId.get(endpoints[0]) || !keepByAssertionId.get(endpoints[1]);
}

export function buildFirstWorldDecisions(
  assertions: ExactRunReviewAssertion[],
  keepByAssertionId: Map<string, boolean>,
): FirstWorldDisposition[] {
  return assertions.map((assertion) => {
    const keep = keepByAssertionId.get(assertion.assertionId) ?? false;
    let decision: FirstWorldDecision = "reject";
    if (keep) {
      decision = assertion.kind === "object" ? "create_new" : "accept";
    }
    return {
      assertionId: assertion.assertionId,
      decision,
    };
  });
}

function countKeptDecisions(
  assertions: ExactRunReviewAssertion[],
  keepByAssertionId: Map<string, boolean>,
): number {
  return assertions.filter((assertion) => keepByAssertionId.get(assertion.assertionId)).length;
}

function outcomeLabel(outcome: FirstWorldGraphConfirmReceipt["outcome"]): string {
  switch (outcome) {
    case "initialized":
      return "World Graph created";
    case "already_initialized":
      return "World Graph already exists";
    case "published_audit_degraded":
      return "World Graph created with degraded audit";
    default:
      return outcome;
  }
}

function publishErrorMessage(error: unknown): string {
  if (error instanceof ExtractPromoteApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Failed to create World Graph.";
}

async function defaultCatalogRefresh(): Promise<void> {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(GRAPH_REVIEW_RUNS_CHANGED_EVENT));
}

/**
 * First-world keep/reject review for exact worldbuilding runs (CR02A).
 */
export function GraphReviewFirstWorldPublishSheet({
  review,
  onConfirmInFlightChange,
  onCatalogRefresh = defaultCatalogRefresh,
}: GraphReviewFirstWorldPublishSheetProps) {
  if (review.firstWorldPublishEligible !== true) {
    return null;
  }

  const worldId = review.worldId?.trim() ?? "";
  const worldDisplayName = worldId ? formatWorldDisplayName(worldId) : "this world";

  const [keepByAssertionId, setKeepByAssertionId] = useState<Map<string, boolean>>(() =>
    buildInitialKeepState(review.assertions),
  );
  const [publishPhase, setPublishPhase] = useState<PublishPhase>("idle");
  const [sealedPlan, setSealedPlan] = useState<FirstWorldGraphPlan | null>(null);
  const [receipt, setReceipt] = useState<FirstWorldGraphConfirmReceipt | null>(null);
  const [publishError, setPublishError] = useState<string | null>(null);

  const publishing = publishPhase === "publishing";
  const hasTerminalReceipt = receipt != null;
  const selectionLocked = publishing || hasTerminalReceipt;
  const keptCount = useMemo(
    () => countKeptDecisions(review.assertions, keepByAssertionId),
    [keepByAssertionId, review.assertions],
  );

  useEffect(() => {
    onConfirmInFlightChange?.(publishing);
    return () => {
      onConfirmInFlightChange?.(false);
    };
  }, [onConfirmInFlightChange, publishing]);

  const toggleKeep = (assertion: ExactRunReviewAssertion) => {
    if (selectionLocked) return;
    setKeepByAssertionId((prev) => {
      const next = new Map(prev);
      const nextKeep = !(next.get(assertion.assertionId) ?? false);
      next.set(assertion.assertionId, nextKeep);

      if (assertion.kind === "object" && !nextKeep) {
        for (const candidate of review.assertions) {
          if (candidate.kind !== "relationship") continue;
          const endpoints = relationshipEndpointIds(candidate);
          if (!endpoints) continue;
          if (endpoints[0] === assertion.assertionId || endpoints[1] === assertion.assertionId) {
            next.set(candidate.assertionId, false);
          }
        }
      }
      return next;
    });
  };

  const runConfirmWithPlan = useCallback(
    async (plan: FirstWorldGraphPlan) => {
      setPublishPhase("publishing");
      setPublishError(null);

      let nextReceipt: FirstWorldGraphConfirmReceipt;
      try {
        nextReceipt = await confirmFirstWorldGraph({ plan });
      } catch (error) {
        if (error instanceof ExtractPromoteApiError) {
          setPublishPhase("pre_commit_error");
          setPublishError(publishErrorMessage(error));
          return;
        }
        setPublishPhase("unknown_result");
        setPublishError(
          error instanceof Error
            ? error.message
            : "Confirm result is unknown due to a network error.",
        );
        return;
      }

      setReceipt(nextReceipt);
      setPublishPhase("receipt");

      try {
        await onCatalogRefresh();
      } catch {
        // Catalog refresh failure must not erase receipt.
      }
    },
    [onCatalogRefresh],
  );

  const runPrepareAndConfirm = useCallback(async () => {
    if (publishing || hasTerminalReceipt || keptCount === 0) return;

    const decisions = buildFirstWorldDecisions(review.assertions, keepByAssertionId);
    setPublishPhase("publishing");
    setPublishError(null);

    let plan: FirstWorldGraphPlan;
    try {
      plan = await prepareFirstWorldGraph({
        runId: review.runId,
        decisions,
      });
    } catch (error) {
      setPublishPhase("pre_commit_error");
      setPublishError(publishErrorMessage(error));
      return;
    }

    setSealedPlan(plan);

    if (!plan.confirmable) {
      setPublishPhase("pre_commit_error");
      setPublishError("No kept changes are confirmable for this world.");
      return;
    }

    await runConfirmWithPlan(plan);
  }, [
    hasTerminalReceipt,
    keepByAssertionId,
    keptCount,
    publishing,
    review.assertions,
    review.runId,
    runConfirmWithPlan,
  ]);

  const onRetryExactConfirm = () => {
    if (!sealedPlan) return;
    void runConfirmWithPlan(sealedPlan);
  };

  const showCreateCta =
    !hasTerminalReceipt
    && publishPhase !== "unknown_result"
    && publishPhase !== "pre_commit_error";

  return (
    <section
      className="graph-review-extract-promote-sheet graph-review-first-world-publish-sheet"
      data-testid="graph-review-first-world-publish-sheet"
      data-world-id={worldId || undefined}
      aria-label={`Review first-world changes for ${worldDisplayName}`}
    >
      <header className="graph-review-extract-promote-sheet-header">
        <div>
          <h4>Review what DungeonBuddy found</h4>
          <p className="graph-review-extract-promote-sheet-meta">
            {worldDisplayName}
            {worldId ? (
              <>
                {" "}
                · <code>{worldId}</code>
              </>
            ) : null}
          </p>
        </div>
      </header>

      {receipt ? (
        <div
          className="graph-review-extract-promote-receipt"
          data-testid="graph-review-first-world-receipt"
          data-outcome={receipt.outcome}
        >
          <p className="graph-review-extract-promote-receipt-outcome">
            {outcomeLabel(receipt.outcome)}
          </p>
          <p className="graph-review-extract-promote-receipt-applied">
            {receipt.appliedAssertionCount} source-backed change
            {receipt.appliedAssertionCount === 1 ? "" : "s"} added to {worldDisplayName}.
          </p>
          {receipt.committedRevisionId ? (
            <p className="graph-review-extract-promote-receipt-revision">
              Committed revision <code>{receipt.committedRevisionId}</code>
            </p>
          ) : null}
          {receipt.warnings.length ? (
            <ul className="graph-review-extract-promote-receipt-warnings">
              {receipt.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {publishError ? (
        <p
          className="graph-review-extract-promote-error"
          data-testid="graph-review-first-world-publish-error"
          role="alert"
        >
          {publishError}
        </p>
      ) : null}

      {!hasTerminalReceipt ? (
        <ul className="graph-review-extract-promote-items">
          {review.assertions.map((assertion) => {
            const kept = keepByAssertionId.get(assertion.assertionId) ?? false;
            const blocked =
              assertion.kind === "relationship"
              && isRelationshipBlocked(assertion, keepByAssertionId);
            const disabled = selectionLocked || blocked;
            return (
              <li
                key={assertion.assertionId}
                className={
                  blocked
                    ? "graph-review-extract-promote-item is-blocked"
                    : "graph-review-extract-promote-item"
                }
              >
                <label>
                  <input
                    type="checkbox"
                    checked={kept}
                    disabled={disabled}
                    onChange={() => toggleKeep(assertion)}
                    aria-label={`Keep ${assertion.label}`}
                  />
                  <span className="graph-review-extract-promote-item-body">
                    <span className="graph-review-extract-promote-item-title">
                      {assertion.label}
                      <span className="graph-review-extract-promote-item-badge">
                        {assertion.kind}
                      </span>
                    </span>
                    <span className="graph-review-extract-promote-item-summary">
                      {assertion.summary}
                    </span>
                    {assertion.evidence[0]?.paragraphText ? (
                      <span className="graph-review-extract-promote-item-evidence">
                        {assertion.evidence[0].paragraphText}
                      </span>
                    ) : null}
                    {blocked ? (
                      <span
                        className="graph-review-extract-promote-item-warnings"
                        data-testid={`graph-review-first-world-relationship-blocked-${assertion.assertionId}`}
                      >
                        Ignored because a required endpoint object is ignored.
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
          data-testid="graph-review-first-world-selection-status"
          data-selected-count={keptCount}
        >
          {hasTerminalReceipt
            ? `World Graph is initialized for ${worldDisplayName}.`
            : keptCount === 0
              ? "Keep at least one object or relationship to create the World Graph."
              : `${keptCount} change${keptCount === 1 ? "" : "s"} kept.`}
        </p>

        {showCreateCta ? (
          <button
            type="button"
            className="primary"
            data-testid="graph-review-first-world-create-cta"
            disabled={keptCount === 0 || publishing}
            onClick={() => {
              void runPrepareAndConfirm();
            }}
          >
            {publishing
              ? "Creating World Graph…"
              : `Create World Graph with ${keptCount} change${keptCount === 1 ? "" : "s"}`}
          </button>
        ) : null}

        {publishPhase === "pre_commit_error" && !hasTerminalReceipt ? (
          <button
            type="button"
            className="primary"
            data-testid="graph-review-first-world-retry-prepare"
            disabled={publishing || keptCount === 0}
            onClick={() => {
              void runPrepareAndConfirm();
            }}
          >
            Retry create
          </button>
        ) : null}

        {publishPhase === "unknown_result" && !hasTerminalReceipt ? (
          <button
            type="button"
            className="primary"
            data-testid="graph-review-first-world-retry-exact-confirm"
            disabled={publishing || !sealedPlan}
            onClick={onRetryExactConfirm}
          >
            Retry exact confirm
          </button>
        ) : null}
      </footer>
    </section>
  );
}
