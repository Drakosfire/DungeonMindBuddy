import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useBuildExtraction } from "./useBuildExtraction";
import {useSelectedWorld} from "../selectedWorld/SelectedWorldContext";
import type {SessionEvidenceRef} from "../playSurface/review/sessionEvidenceApi";
import {BuildRecapConfiguration} from "./BuildRecapConfiguration";
import { useBuildNativeWorldSourceEvidence } from "./useBuildNativeWorldSourceEvidence";

const BuildRunReview = lazy(() => import("./BuildRunReview").then(module => ({default:module.BuildRunReview})));

interface BuildIngestToolbarProps {
  documentId: string;
  target?: HTMLElement | null;
  reviewTarget?: HTMLElement | null;
}

export function BuildIngestToolbar({ documentId, target, reviewTarget }: BuildIngestToolbarProps) {
  const menuRef=useRef<HTMLDetailsElement>(null);
  const selectedWorld=useSelectedWorld();
  const worldId=selectedWorld.kind==="managed"?selectedWorld.worldId:null;
  const [mode,setMode]=useState<"worldbuilding"|"recap">("worldbuilding");
  const [campaignId,setCampaignId]=useState("");
  const [session,setSession]=useState("");
  const [evidence,setEvidence]=useState<SessionEvidenceRef[]>([]);
  useEffect(()=>{setMode("worldbuilding");setCampaignId("");setSession("");setEvidence([]);},[documentId,worldId]);
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
    refresh, pendingRecap, recoverRecap, savedRecapRequests, setAsideRecap, restoreRecap,
  } = useBuildExtraction({ documentId, profile, worldId, recap:mode==="recap"?{worldId:worldId??"",campaignId,session:Number(session),evidence}:null });

  const content = (
    <section className="build-ingest-toolbar" data-testid="build-ingest-toolbar" aria-label="Build extraction">
      <label>Run mode<select aria-label="Run mode" value={mode} disabled={launching||reviewBusy}
        onChange={e=>setMode(e.target.value==="recap"?"recap":"worldbuilding")}>
        <option value="worldbuilding">Worldbuilding</option><option value="recap">Recap</option></select></label>
      <p>Configuration changes apply to the next extraction. The current run keeps its original source and mode.</p>
      {mode==="recap"?<BuildRecapConfiguration documentId={documentId} worldId={worldId} campaignId={campaignId} session={session} evidence={evidence}
        onCampaign={setCampaignId} onSession={setSession} onEvidence={setEvidence} disabled={launching||reviewBusy||pendingRecap}/>:<label>
        Extraction approach
        <select aria-label="Extraction approach" value={profile} disabled={launching}
          onChange={(event) => setSelection({ documentId, profile: event.target.value === "gazetteer" ? "gazetteer" : "pilot" })}>
          <option value="pilot">Focused lore</option>
          <option value="gazetteer">Gazetteer — places, people and setting details</option>
        </select>
      </label>}
      {pendingRecap&&<div role="status"><p>A saved Recap request needs recovery. Checking its status does not start another extraction.</p>
        <button disabled={launching||reviewBusy} onClick={()=>void recoverRecap()}>Check saved extraction</button>
        <button disabled={launching||reviewBusy} onClick={()=>void recoverRecap(true)}>Retry saved extraction request</button>
        <p>To correct settings or start separately, set this request aside. This does not cancel it; its original request stays saved in this browser.</p>
        <button disabled={launching||reviewBusy} onClick={setAsideRecap}>Set aside saved request</button></div>}
      {savedRecapRequests.length>0&&<details><summary>Saved extraction requests</summary>
        {savedRecapRequests.map(item=><button key={item.index} disabled={launching||reviewBusy||pendingRecap}
          onClick={()=>restoreRecap(item.index)}>Recover {item.label}</button>)}
      </details>}
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
            disabled={!canLaunch || reviewBusy || (mode==="recap"&&(!worldId||!campaignId.trim()||!Number.isInteger(Number(session))||Number(session)<1))}
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
              onClick={()=>{if(menuRef.current)menuRef.current.open=false;setReviewMounted(true);setReviewOpen(true);}}>Review extracted knowledge</button>
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
    <details ref={menuRef} className="build-extraction-menu"><summary>Extraction</summary>{content}</details>, target,
  ) : null;
  return <>{toolbar}{reviewMounted && reviewTarget && canOpenGraphReview && document && snapshot && handoff && run && sourceContentSha256
    ? createPortal(<div hidden={!reviewOpen}><Suspense fallback={<p role="status">Opening review…</p>}>
      <BuildRunReview document={document} currentRevision={snapshot.loaded_revision} run={run} handoff={handoff}
        sourceContentSha256={sourceContentSha256} onClose={()=>setReviewOpen(false)} onDerivedRun={adoptDerivedRun} onBusyChange={setReviewBusy} />
    </Suspense></div>, reviewTarget) : null}</>;
}
