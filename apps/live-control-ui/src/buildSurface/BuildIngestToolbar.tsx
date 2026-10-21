import { lazy, Suspense, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useBuildExtraction } from "./useBuildExtraction";
import { useBuildNativeWorldSourceEvidence } from "./useBuildNativeWorldSourceEvidence";

const BuildRunReview = lazy(() => import("./BuildRunReview").then(module => ({default:module.BuildRunReview})));

interface BuildIngestToolbarProps {
  documentId: string;
  target?: HTMLElement | null;
  reviewTarget?: HTMLElement | null;
}

export function BuildIngestToolbar({ documentId, target, reviewTarget }: BuildIngestToolbarProps) {
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewMounted, setReviewMounted] = useState(false);
  const [reviewBusy, setReviewBusy] = useState(false);
  useEffect(() => {
    if (reviewOpen) reviewTarget?.scrollIntoView?.({block:"start"});
  }, [reviewOpen, reviewTarget]);
  const [selection, setSelection] = useState<{ documentId: string; profile: "pilot" | "gazetteer" }>({ documentId, profile: "pilot" });
  if (selection.documentId !== documentId) setSelection({ documentId, profile: "pilot" });
  const profile = selection.documentId === documentId ? selection.profile : "pilot";
  const nativeSource = useBuildNativeWorldSourceEvidence(documentId);
  const {
    document, snapshot, sourceContentSha256, adoptDerivedRun,
    statusLabel,
    error,
    canLaunch,
    canRefresh,
    canOpenGraphReview,
    launching,
    handoff,
    run,
    launch,
    refresh,
  } = useBuildExtraction({ documentId, profile });

  const content = (
    <section className="build-ingest-toolbar" data-testid="build-ingest-toolbar" aria-label="Build extraction">
      <label>
        Extraction approach
        <select aria-label="Extraction approach" value={profile} disabled={launching}
          onChange={(event) => setSelection({ documentId, profile: event.target.value === "gazetteer" ? "gazetteer" : "pilot" })}>
          <option value="pilot">Focused lore</option>
          <option value="gazetteer">Gazetteer — places, people and setting details</option>
        </select>
      </label>
      <div className="build-ingest-toolbar-row">
        <p data-testid="build-native-source-status" aria-live="polite">
          {nativeSource.loading
            ? "Native World source: checking…"
            : nativeSource.status?.state === "admitted"
              ? "Native World source: admitted"
              : nativeSource.status?.state === "pending"
                ? "Source saved; native World admission pending"
                : "Native World source status unavailable"}
        </p>
        <div className="build-ingest-toolbar-actions">
          {nativeSource.status?.state === "pending" ? (
            <button
              type="button"
              data-testid="build-native-source-retry"
              onClick={() => void nativeSource.retry()}
              disabled={nativeSource.retrying || nativeSource.loading}
            >
              {nativeSource.retrying ? "Admitting…" : "Retry World admission"}
            </button>
          ) : null}
          <button
            type="button"
            data-testid="build-native-source-refresh"
            onClick={() => void nativeSource.reload()}
            disabled={nativeSource.loading || nativeSource.retrying}
          >
            Refresh World status
          </button>
        </div>
      </div>
      {nativeSource.status?.state === "admitted" ? (
        <p data-testid="build-native-source-evidence">
          World <code>{nativeSource.status.world_id}</code> · exact source revision {nativeSource.status.loaded_revision} · whole-document evidence
        </p>
      ) : null}
      {nativeSource.error ? (
        <p role="alert" data-testid="build-native-source-error">{nativeSource.error}</p>
      ) : null}
      <div className="build-ingest-toolbar-row">
        <p data-testid="build-extraction-status">{statusLabel}</p>
        <div className="build-ingest-toolbar-actions">
          <button
            type="button"
            data-testid="build-extract-button"
            onClick={() => {
              void launch();
            }}
            disabled={!canLaunch || reviewBusy}
          >
            {launching ? "Extracting…" : "Extract"}
          </button>
          <button
            type="button"
            data-testid="build-extraction-refresh"
            onClick={() => {
              void refresh();
            }}
            disabled={!canRefresh || reviewBusy}
          >
            Refresh run
          </button>
          {canOpenGraphReview && handoff ? (
            <button type="button" data-testid="build-open-graph-review" disabled={!reviewTarget || reviewBusy}
              onClick={()=>{setReviewMounted(true);setReviewOpen(true);}}>Review extracted knowledge</button>
          ) : (
            <span data-testid="build-open-graph-review-disabled">Review extracted knowledge</span>
          )}
        </div>
      </div>
      {run ? (
        <p data-testid="build-extraction-run-id">
          Exact run: <code>{run.run_id}</code>
        </p>
      ) : null}
      {error ? (
        <p role="alert" data-testid="build-extraction-error">{error}</p>
      ) : null}
    </section>
  );

  // Portal only presentation; hooks keep the owning document session/context.
  // Keeping content mounted while collapsed also preserves the selected profile.
  const toolbar = target === undefined ? content : target ? createPortal(
    <details className="build-extraction-menu"><summary>Extraction</summary>{content}</details>, target,
  ) : null;
  return <>{toolbar}{reviewMounted && reviewTarget && canOpenGraphReview && document && snapshot && handoff && run && sourceContentSha256
    ? createPortal(<div hidden={!reviewOpen}><Suspense fallback={<p role="status">Opening review…</p>}>
      <BuildRunReview document={document} currentRevision={snapshot.loaded_revision} run={run} handoff={handoff}
        sourceContentSha256={sourceContentSha256} onClose={()=>setReviewOpen(false)} onDerivedRun={adoptDerivedRun} onBusyChange={setReviewBusy} />
    </Suspense></div>, reviewTarget) : null}</>;
}
