import { useEffect, useMemo, useState } from "react";

import {
  ExtractPromoteApiError,
  getExactRunReviewPackage,
} from "../api/extractPromoteApi";
import type {
  ExactRunReviewAssertion,
  ExactRunReviewPackage,
  ExtractPromoteErrorBody,
} from "../api/types";
import { getExtractionRunStatus } from "../api/liveApi";
import { useMarkdownCanvasSession } from "../markdownCanvas/MarkdownCanvasSession";
import type { PlanContextDescriptor } from "../planSurface/types";
import { dispatchBuildFindExisting } from "./buildFindExisting";
import { readBuildExtractionRunId } from "./useBuildExtraction";

type ReviewLoadState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; review: ExactRunReviewPackage }
  | {
      status: "error";
      message: string;
      inspectionStatus?: ExtractPromoteErrorBody["inspectionStatus"];
      runStatus?: string;
      diagnostics?: NonNullable<ExtractPromoteErrorBody["diagnostics"]>;
    };

function documentIdFromLocation(): string | null {
  const value = new URLSearchParams(window.location.search).get("documentId");
  return value?.trim() || null;
}

function pinnedSourceHref(documentId: string, runId: string): string {
  const url = new URL(window.location.href);
  url.pathname = "/build";
  url.search = "";
  url.searchParams.set("documentId", documentId);
  url.searchParams.set("extractionRunId", runId);
  return `${url.pathname}${url.search}`;
}

function sourceMatchesCanvas(args: {
  canvasRevision: number | null;
  canvasDigest: string | null;
  pinnedRevision: number | null;
  pinnedDigest: string | null;
}): boolean {
  const { canvasRevision, canvasDigest, pinnedRevision, pinnedDigest } = args;
  if (pinnedRevision == null || !pinnedDigest?.trim()) return false;
  if (canvasRevision == null || !canvasDigest?.trim()) return false;
  return canvasRevision === pinnedRevision && canvasDigest === pinnedDigest;
}

function reviewFailureFromError(error: unknown): Extract<ReviewLoadState, { status: "error" }> {
  if (error instanceof ExtractPromoteApiError) {
    return {
      status: "error",
      message: error.message,
      inspectionStatus: error.body?.inspectionStatus,
      runStatus: error.body?.runStatus,
      diagnostics: error.body?.diagnostics,
    };
  }
  return {
    status: "error",
    message: error instanceof Error ? error.message : "Failed to load extraction run review package.",
  };
}

function InspectorCandidateRow({ assertion }: { assertion: ExactRunReviewAssertion }) {
  return (
    <li
      className="build-extraction-run-inspector-candidate"
      data-testid={`build-extraction-run-candidate-${assertion.assertionId}`}
    >
      <div>
        <strong>{assertion.label}</strong>
        <span>
          {" "}
          · {assertion.kind}
          {assertion.summary ? ` · ${assertion.summary}` : ""}
        </span>
      </div>
      <button
        type="button"
        data-testid={`build-extraction-run-find-existing-${assertion.assertionId}`}
        onClick={() => {
          dispatchBuildFindExisting({
            query: assertion.label,
            kindHint: assertion.kind === "object" ? assertion.summary || null : assertion.kind,
          });
        }}
      >
        Find existing object
      </button>
      {assertion.evidence.length > 0 ? (
        <ul className="build-extraction-run-inspector-evidence">
          {assertion.evidence.map((item) => (
            <li
              key={`${item.sourceSpanRefId}:${item.startLine ?? 0}`}
              data-testid="build-extraction-run-evidence-item"
            >
              <p>
                Span <code>{item.sourceSpanRefId}</code>
                {item.startLine != null
                  ? ` · lines ${item.startLine}${item.endLine != null && item.endLine !== item.startLine ? `–${item.endLine}` : ""}`
                  : ""}
              </p>
              {item.anchorQuotes.length > 0 ? (
                <p data-testid="build-extraction-run-evidence-quote">
                  Quote: “{item.anchorQuotes.join(" · ")}”
                </p>
              ) : null}
              <blockquote>{item.paragraphText || "(span paragraph unavailable)"}</blockquote>
            </li>
          ))}
        </ul>
      ) : (
        <p className="plan-projection-empty">No source evidence bound to this candidate.</p>
      )}
    </li>
  );
}

export interface BuildExtractionRunInspectorProps {
  context: PlanContextDescriptor;
}

export function BuildExtractionRunInspector({ context: _context }: BuildExtractionRunInspectorProps) {
  const canvas = useMarkdownCanvasSession();
  const documentId = documentIdFromLocation();
  const runId = documentId ? readBuildExtractionRunId(documentId) : null;

  const [pinnedRevision, setPinnedRevision] = useState<number | null>(null);
  const [pinnedDigest, setPinnedDigest] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [reviewState, setReviewState] = useState<ReviewLoadState>({ status: "idle" });

  const canvasRevision = canvas.documentId === documentId
    ? (canvas.snapshot?.loaded_revision ?? canvas.record?.revision ?? null)
    : null;
  const canvasDigest = canvas.documentId === documentId
    ? (canvas.snapshot?.content_sha256 ?? null)
    : null;

  const highlightsAvailable = useMemo(
    () => sourceMatchesCanvas({
      canvasRevision,
      canvasDigest,
      pinnedRevision,
      pinnedDigest,
    }),
    [canvasDigest, canvasRevision, pinnedDigest, pinnedRevision],
  );

  useEffect(() => {
    if (!runId) {
      setPinnedRevision(null);
      setPinnedDigest(null);
      setRunStatus(null);
      setStatusError(null);
      setReviewState({ status: "idle" });
      return;
    }

    let cancelled = false;
    setStatusError(null);
    setReviewState({ status: "loading" });

    void (async () => {
      try {
        const status = await getExtractionRunStatus(runId);
        if (cancelled) return;
        setPinnedRevision(status.document_revision);
        setPinnedDigest(status.source_content_sha256);
        setRunStatus(status.run.status);
      } catch (error) {
        if (cancelled) return;
        setStatusError(error instanceof Error ? error.message : "Failed to load extraction run status.");
      }

      try {
        const review = await getExactRunReviewPackage(runId);
        if (cancelled) return;
        if (review.runId !== runId) {
          setReviewState({
            status: "error",
            message: "Review package run ID does not match the selected exact run.",
          });
          return;
        }
        setReviewState({ status: "ready", review });
      } catch (error) {
        if (cancelled) return;
        setReviewState(reviewFailureFromError(error));
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [runId]);

  if (!documentId) {
    return (
      <p className="plan-projection-empty" data-testid="build-extraction-run-inspector-empty">
        Open a Build document to inspect an extraction run.
      </p>
    );
  }

  if (!runId) {
    return (
      <p className="plan-projection-empty" data-testid="build-extraction-run-inspector-empty">
        No exact extraction run is selected for this document.
      </p>
    );
  }

  return (
    <div
      className="build-extraction-run-inspector"
      data-testid="build-extraction-run-inspector"
    >
      <p data-testid="build-extraction-run-inspector-run">
        Run <code>{runId}</code>
        {runStatus ? (
          <>
            {" "}
            · <span data-testid="build-extraction-run-inspector-run-status">{runStatus}</span>
          </>
        ) : null}
      </p>
      {pinnedRevision != null ? (
        <p data-testid="build-extraction-run-inspector-pinned-revision">
          Pinned revision: <code>{pinnedRevision}</code>
        </p>
      ) : null}
      {pinnedDigest ? (
        <p data-testid="build-extraction-run-inspector-pinned-digest">
          Pinned digest: <code>{pinnedDigest}</code>
        </p>
      ) : null}
      {statusError ? (
        <p role="alert" className="graph-review-error" data-testid="build-extraction-run-inspector-status-error">
          {statusError}
        </p>
      ) : null}

      {!highlightsAvailable && pinnedRevision != null && pinnedDigest ? (
        <p
          className="build-extraction-run-inspector-draft-mismatch"
          data-testid="build-extraction-run-inspector-draft-mismatch"
        >
          Highlights unavailable on current draft.{" "}
          <a href={pinnedSourceHref(documentId, runId)}>Open pinned source</a>
        </p>
      ) : null}

      {reviewState.status === "loading" ? (
        <p className="plan-projection-empty">Loading extraction run review package…</p>
      ) : null}

      {reviewState.status === "error" ? (
        <div className="graph-review-error" data-testid="build-extraction-run-inspector-review-error">
          <p>{reviewState.message}</p>
          {reviewState.inspectionStatus ? (
            <p data-testid="build-extraction-run-inspector-inspection-status">
              Inspection status: <code>{reviewState.inspectionStatus}</code>
              {reviewState.runStatus ? (
                <>
                  {" "}
                  (run lifecycle: <code>{reviewState.runStatus}</code>)
                </>
              ) : null}
            </p>
          ) : null}
          {reviewState.diagnostics?.length ? (
            <ul data-testid="build-extraction-run-inspector-review-diagnostics">
              {reviewState.diagnostics.map((item, index) => (
                <li key={`${item.code}-${index}`}>
                  <code>{item.code}</code>: {item.message}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {reviewState.status === "ready" ? (
        <>
          {reviewState.review.diagnostics.length > 0 ? (
            <ul data-testid="build-extraction-run-inspector-package-diagnostics">
              {reviewState.review.diagnostics.map((message) => (
                <li key={message}>{message}</li>
              ))}
            </ul>
          ) : null}
          <section aria-label="Extraction candidates">
            <h3>Candidates ({reviewState.review.assertions.length})</h3>
            <ul className="build-extraction-run-inspector-candidates">
              {reviewState.review.assertions.map((assertion) => (
                <InspectorCandidateRow key={assertion.assertionId} assertion={assertion} />
              ))}
            </ul>
          </section>
          {highlightsAvailable && reviewState.review.sourceProse ? (
            <section aria-label="Pinned source prose">
              <h3>Pinned source</h3>
              <pre data-testid="build-extraction-run-inspector-source-prose">
                {reviewState.review.sourceProse}
              </pre>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
