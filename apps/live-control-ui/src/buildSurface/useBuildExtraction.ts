import { useCallback, useEffect, useRef, useState } from "react";

import {
  getExtractionRunStatus,
  launchExtractionRun,
} from "../api/liveApi";
import type {
  ExtractionRunLaunchResponse,
  ExtractionRunRecord,
  ExtractionRunStatusResponse,
  GraphReviewHandoffPayload,
  WorkspaceDocumentRecord,
  WorkspaceDocumentSnapshot,
} from "../api/types";
import {assertRecapQuoteChild, type BuildCorrectionReceipt, quoteDigest, RECAP_QUOTE_DERIVATION} from './buildRecapCorrection';
import type {RecapSemanticDecisionReceipt} from '../api/recapSemanticReviewApi';
import { useMarkdownCanvasSession } from "../markdownCanvas/MarkdownCanvasSession";
import { DOCUMENT_SAVE_COMMAND_ID } from "../markdownCanvas/markdownCanvasTypes";
import { translateBuildDocumentCommandFailure } from "./buildAdmissionCopy";
import {
  BUILD_EXTRACT_COMMAND_ID,
} from "./buildDocumentCommands";

import {assertRecapLaunchBinding, launchBuildRecap, recoverBuildRecap, recapRecoveryKey, recapHistoryKey, validRecapRequest,
  type BuildRecapLaunchRequest, type BuildRecapSettings} from "../api/buildRecapApi";

const RUN_STORAGE_PREFIX = "dmb.buildExtractionRun.";

/** Bounded BLD-08 worldbuilding profile (Build product default). */
export const BUILD_WORLDBUILDING_PROFILE_ID = "worldbuilding_shepherds_flock_v0";
export const BUILD_WORLDBUILDING_PROFILE_VERSION = "0.1";
export const BUILD_GAZETTEER_PROFILE_ID = "worldbuilding_gazetteer_v1";
export const BUILD_GAZETTEER_PROFILE_VERSION = "1.10";

function runIdFromLocation(): string | null {
  const value = new URLSearchParams(window.location.search).get("extractionRunId");
  return value?.trim() || null;
}

function documentIdFromLocation(): string | null {
  const value = new URLSearchParams(window.location.search).get("documentId");
  return value?.trim() || null;
}

/** Mutate URL only while the selected document still owns the page. */
function setRunIdInLocationForDocument(documentId: string, runId: string): void {
  if (documentIdFromLocation() !== documentId) return;
  const url = new URL(window.location.href);
  url.searchParams.set("extractionRunId", runId);
  window.history.replaceState({}, "", `${url.pathname}${url.search}`);
}

function readStoredRunId(documentId: string): string | null {
  try {
    return window.localStorage.getItem(`${RUN_STORAGE_PREFIX}${documentId}`);
  } catch {
    return null;
  }
}

function writeStoredRunId(documentId: string, runId: string): void {
  try {
    window.localStorage.setItem(`${RUN_STORAGE_PREFIX}${documentId}`, runId);
  } catch {
    // ignore quota
  }
}

function diagnosticRun(runId: string, sourceArtifactId = ""): ExtractionRunRecord {
  return {
    schema_version: "dmb_extraction_run_v1",
    version: "1.0",
    run_id: runId,
    source_artifact_id: sourceArtifactId,
    source_domain: "worldbuilding",
    status: "failed",
  };
}

export type ExactRunIdentityValidation =
  | { ok: true; handoff: GraphReviewHandoffPayload }
  | { ok: false; reason: string };

function singleQueryValue(params: URLSearchParams, key: string): string | null {
  const values = params.getAll(key);
  if (values.length !== 1) return null;
  const value = values[0]?.trim() ?? "";
  return value || null;
}

/** Require handoff.href query identities to equal the handoff payload fields. */
export function validateHandoffHref(handoff: GraphReviewHandoffPayload): ExactRunIdentityValidation {
  if (!handoff.href?.trim()) {
    return { ok: false, reason: "Handoff href is missing." };
  }
  if (/\blatest\b/i.test(handoff.href)) {
    return { ok: false, reason: "Handoff href substitutes latest." };
  }
  let url: URL;
  try {
    url = new URL(handoff.href, "https://dmb.invalid");
  } catch {
    return { ok: false, reason: "Handoff href is malformed." };
  }
  const params = url.searchParams;
  const extractionRunId = singleQueryValue(params, "extractionRunId");
  const sourceArtifactId = singleQueryValue(params, "sourceArtifactId");
  const documentId = singleQueryValue(params, "documentId");
  const revision = singleQueryValue(params, "revision");
  if (
    extractionRunId !== handoff.extraction_run_id
    || sourceArtifactId !== handoff.source_artifact_id
    || documentId !== handoff.document_id
    || revision !== String(handoff.document_revision)
  ) {
    return {
      ok: false,
      reason: "Handoff href query identities do not match the handoff payload fields.",
    };
  }
  return { ok: true, handoff };
}

/** Shared identity matrix for launch and status envelopes. */
export function validateExactRunIdentity(args: {
  selectedDocumentId: string;
  requestedRunId: string;
  response: Pick<
    ExtractionRunStatusResponse,
    | "run"
    | "source_artifact_id"
    | "document_id"
    | "document_revision"
    | "source_content_sha256"
    | "graph_review_handoff"
  >;
  /** When set (launch path), response must equal the snapshot submitted with the request. */
  expectedDocumentRevision?: number;
  expectedContentSha256?: string;
}): ExactRunIdentityValidation {
  const {
    selectedDocumentId,
    requestedRunId,
    response,
    expectedDocumentRevision,
    expectedContentSha256,
  } = args;
  const handoff = response.graph_review_handoff;
  if (!handoff) {
    return { ok: false, reason: "Exact-run response is missing graph_review_handoff." };
  }
  if (response.run.run_id !== requestedRunId) {
    return { ok: false, reason: "Response run ID does not match the requested exact run." };
  }
  if (response.run.source_artifact_id !== response.source_artifact_id) {
    return { ok: false, reason: "Run source artifact does not match response source artifact." };
  }
  if (response.source_artifact_id !== handoff.source_artifact_id) {
    return { ok: false, reason: "Handoff source artifact does not match response source artifact." };
  }
  if (handoff.extraction_run_id !== response.run.run_id) {
    return { ok: false, reason: "Handoff run ID does not match response run." };
  }
  if (response.document_id !== selectedDocumentId || handoff.document_id !== selectedDocumentId) {
    return {
      ok: false,
      reason: "Exact run belongs to a different workspace document than the selected Build source.",
    };
  }
  if (handoff.document_revision !== response.document_revision) {
    return { ok: false, reason: "Handoff revision does not match server-resolved source revision." };
  }
  if (!response.source_content_sha256?.trim()) {
    return { ok: false, reason: "Exact-run response is missing source_content_sha256." };
  }
  if (
    expectedDocumentRevision !== undefined
    && response.document_revision !== expectedDocumentRevision
  ) {
    return {
      ok: false,
      reason: "Launch response revision does not match the requested snapshot revision.",
    };
  }
  if (
    expectedContentSha256 !== undefined
    && response.source_content_sha256 !== expectedContentSha256
  ) {
    return {
      ok: false,
      reason: "Launch response digest does not match the requested snapshot digest.",
    };
  }
  return validateHandoffHref(handoff);
}

export interface UseBuildExtractionArgs {
  documentId: string;
  profile?: "pilot" | "gazetteer";
  recap?: BuildRecapSettings | null;
  worldId?: string | null;
}

export interface BuildExtractionState {
  document: WorkspaceDocumentRecord | null;
  snapshot: WorkspaceDocumentSnapshot | null;
  run: ExtractionRunRecord | null;
  handoff: GraphReviewHandoffPayload | null;
  sourceContentSha256: string | null;
  adoptDerivedRun: (receipt: BuildCorrectionReceipt, expectedDigest: string, isCurrent: () => boolean) => Promise<() => void>;
  adoptSemanticDecision: (receipt: RecapSemanticDecisionReceipt, isCurrent: () => boolean) => Promise<() => void>;
  statusLabel: string;
  error: string | null;
  launching: boolean;
  canLaunch: boolean;
  canRefresh: boolean;
  canOpenGraphReview: boolean;
  refresh: () => Promise<void>;
  launch: () => Promise<void>;
  savedRecapRequests: {index: number; label: string}[];
  setAsideRecap: () => void;
  restoreRecap: (index: number) => void;
  pendingRecap: boolean;
  recoverRecap: (retry?: boolean) => Promise<void>;
}

export function useBuildExtraction(args: UseBuildExtractionArgs): BuildExtractionState {
  const { documentId, profile = "pilot" } = args;
  const canvas = useMarkdownCanvasSession();
  const worldId=args.worldId??null, recap=args.recap??null;
  const operationScope=JSON.stringify([documentId,worldId]);
  const scopeRef=useRef(operationScope);scopeRef.current=operationScope;
  const pendingKey=recapRecoveryKey(worldId??"",documentId);
  const [pendingState,setPendingState]=useState<{key:string;value:unknown}>(()=>{
    try{return {key:pendingKey,value:JSON.parse(localStorage.getItem(pendingKey)??"null")};}
    catch{return {key:pendingKey,value:{unavailable:true}};}
  });
  const pending=pendingState.key===pendingKey?pendingState.value:null;
  const historyKey=recapHistoryKey(worldId??"",documentId);
  const readHistory=useCallback(():unknown[]=>{
    const stored=JSON.parse(localStorage.getItem(historyKey)??"[]");
    if(!Array.isArray(stored))throw new Error("Saved extraction history is unavailable.");
    return stored;
  },[historyKey]);
  const [historyState,setHistoryState]=useState<{key:string;values:unknown[]}>(()=>{
    try{return {key:historyKey,values:readHistory()};}catch{return {key:historyKey,values:[]};}
  });
  useEffect(()=>{try{setHistoryState({key:historyKey,values:readHistory()});}
    catch{setHistoryState({key:historyKey,values:[]});}},[historyKey,readHistory]);
  const savedRecapRequests=(historyState.key===historyKey?historyState.values:[]).map((value,index)=>({index,
    label:validRecapRequest(value)?`${value.campaign_id} · Session ${value.session}`:"Unavailable saved request"}));
  useEffect(()=>{
    try{setPendingState({key:pendingKey,value:JSON.parse(localStorage.getItem(pendingKey)??"null")});}
    catch{setPendingState({key:pendingKey,value:{unavailable:true}});}
  },[pendingKey]);
  const [run, setRun] = useState<ExtractionRunRecord | null>(null);
  const [handoff, setHandoff] = useState<GraphReviewHandoffPayload | null>(null);
  const [sourceContentSha256, setSourceContentSha256] = useState<string | null>(null);
  const currentRunRef = useRef(run);
  currentRunRef.current = run;
  const [error, setError] = useState<string | null>(null);
  const [launching, setLaunching] = useState(false);

  // Separate generations so Refresh cannot cancel an in-flight Extract adoption.
  const launchGenerationRef = useRef(0);
  const refreshGenerationRef = useRef(0);
  // Synchronous mirror of launching so refresh can no-op before any await.
  const launchingRef = useRef(false);

  const committedClean = canvas.documentId === documentId
    ? canvas.getAdmittedDocument("committed_clean")
    : null;
  const document = canvas.documentId === documentId ? canvas.record : null;
  const snapshot = canvas.documentId === documentId ? canvas.snapshot : null;
  const localCleanMatch = committedClean != null;

  const clearAdoptedRunState = useCallback(() => {
    setRun(null);
    setHandoff(null);
    setSourceContentSha256(null);
    setError(null);
    launchingRef.current = false;
    setLaunching(false);
  }, []);

  const refresh = useCallback(async () => {
    // Refresh must not supersede an active launch generation or clear a pending
    // Extract before its exact run ID is known.
    if (launchingRef.current) return;

    const generation = ++refreshGenerationRef.current;
    const selectedDocumentId = documentId;
    setError(null);
    setHandoff(null);

    if (!selectedDocumentId) {
      clearAdoptedRunState();
      return;
    }

    const exactRunId = runIdFromLocation() ?? readStoredRunId(selectedDocumentId);

    try {
      if (generation !== refreshGenerationRef.current) return;
      if (launchingRef.current) return;
      if (documentIdFromLocation() !== selectedDocumentId || scopeRef.current!==operationScope) return;

      if (!exactRunId) {
        setRun(null);
        setHandoff(null);
        return;
      }

      const status: ExtractionRunStatusResponse = await getExtractionRunStatus(exactRunId);
      if (generation !== refreshGenerationRef.current) return;
      if (launchingRef.current) return;
      if (documentIdFromLocation() !== selectedDocumentId || scopeRef.current!==operationScope) return;

      if(status.run.source_domain==="recap" && (status.run.lineage?.world_campaign_ingest_context as Record<string,unknown>|undefined)?.managed_world_id!==worldId){
        throw new Error("This Recap extraction belongs to another selected World.");
      }
      const validation = validateExactRunIdentity({
        selectedDocumentId,
        requestedRunId: exactRunId,
        response: status,
      });
      setRun(status.run);
      if (!validation.ok) {
        setHandoff(null);
        setError(validation.reason);
        return;
      }
      writeStoredRunId(selectedDocumentId, status.run.run_id);
      setHandoff(validation.handoff);
      setSourceContentSha256(status.source_content_sha256);
      setError(null);
    } catch (loadError) {
      if (generation !== refreshGenerationRef.current) return;
      if (launchingRef.current) return;
      if (documentIdFromLocation() !== selectedDocumentId || scopeRef.current!==operationScope) return;
      setHandoff(null);
      setError(loadError instanceof Error ? loadError.message : "Failed to load extraction state");
      setRun((current) => {
        if (current) return current;
        return exactRunId ? diagnosticRun(exactRunId) : null;
      });
    }
  }, [clearAdoptedRunState, documentId, worldId, operationScope]);

  useEffect(() => {
    // Invalidate any in-flight refresh/launch belonging to a prior selection.
    launchGenerationRef.current += 1;
    refreshGenerationRef.current += 1;
    clearAdoptedRunState();
    void refresh();
    return () => {
      launchGenerationRef.current += 1;
      refreshGenerationRef.current += 1;
      launchingRef.current = false;
    };
    // refresh is recreated when documentId changes; keying the effect on documentId is enough.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId,worldId]);

  const launch = useCallback(async () => {
    const selectedDocumentId = documentId;
    // Reject synchronous re-entry before React re-renders the disabled button.
    if (launchingRef.current || pending !== null) return;

    // Invalidate every pre-existing refresh before the first await so a stale
    // refresh cannot adopt R1 after this launch adopts R2.
    refreshGenerationRef.current += 1;
    const generation = ++launchGenerationRef.current;
    launchingRef.current = true;
    setLaunching(true);
    setError(null);
    setHandoff(null);

    try {
      const commandResult = await canvas.runDocumentCommand(
        {
          id: BUILD_EXTRACT_COMMAND_ID,
          conflictsWith: [DOCUMENT_SAVE_COMMAND_ID],
          admission: "committed_clean",
          invalidateOnDocumentChange: true,
        },
        async ({ envelope, signal, documentId: commandDocumentId }) => {
          if (!envelope) {
            throw new Error("Extraction requires a committed-clean document envelope.");
          }
          if (envelope.documentId !== selectedDocumentId || commandDocumentId !== selectedDocumentId) {
            throw new Error("Admitted envelope does not match the selected Build document.");
          }
          // Plugins may not manufacture envelopes; use only the command-host capture.
          let savedRecapRequest: BuildRecapLaunchRequest|null=null;
          let response: ExtractionRunLaunchResponse;
          if(recap){
            savedRecapRequest={request_id:crypto.randomUUID(),document_id:selectedDocumentId,
              expected_revision:envelope.revision,expected_content_sha256:envelope.contentSha256.replace(/^sha256:/,""),
              managed_world_id:recap.worldId,campaign_id:recap.campaignId,session:recap.session,
              session_evidence:structuredClone(recap.evidence)};
            if(recap.worldId!==worldId||!validRecapRequest(savedRecapRequest))throw new Error("Choose a verified World, source campaign and session for this Recap.");
            localStorage.setItem(pendingKey,JSON.stringify(savedRecapRequest));
            setPendingState({key:pendingKey,value:savedRecapRequest});
            const status=await launchBuildRecap(savedRecapRequest);
            assertRecapLaunchBinding(savedRecapRequest,status);
            response={...status,schema_version:"dmb_extraction_run_launch_v1",failure_kind:status.run.status==="failed"?"extraction":null,diagnostics:status.run.diagnostics?.messages??[]};
          }else response = await launchExtractionRun({
            document_id: selectedDocumentId,
            expected_revision: envelope.revision,
            expected_content_sha256: envelope.contentSha256,
            profile_id: profile === "gazetteer" ? BUILD_GAZETTEER_PROFILE_ID : BUILD_WORLDBUILDING_PROFILE_ID,
            profile_version: profile === "gazetteer" ? BUILD_GAZETTEER_PROFILE_VERSION : BUILD_WORLDBUILDING_PROFILE_VERSION,
          });
          if (signal.aborted) {
            throw new Error("Extraction launch aborted.");
          }
          return { response, envelope, savedRecapRequest };
        },
      );

      if (generation !== launchGenerationRef.current) return;
      if (documentIdFromLocation() !== selectedDocumentId || scopeRef.current!==operationScope) return;

      if (!commandResult.ok) {
        if (commandResult.code === "duplicate_command") return;
        setError(translateBuildDocumentCommandFailure(commandResult));
        return;
      }

      const { response, envelope, savedRecapRequest } = commandResult.value;
      const expectedProfile = recap ? "recap_category_v2@2.0" : profile === "gazetteer" ? `${BUILD_GAZETTEER_PROFILE_ID}@${BUILD_GAZETTEER_PROFILE_VERSION}` : `${BUILD_WORLDBUILDING_PROFILE_ID}@${BUILD_WORLDBUILDING_PROFILE_VERSION}`;
      if (response.run.profile_id !== expectedProfile) {
        setHandoff(null);
        setError("Extraction returned a different or missing profile. Review is unavailable; refresh server configuration before trying again.");
        return;
      }
      const validation = validateExactRunIdentity({
        selectedDocumentId,
        requestedRunId: response.run.run_id,
        response,
        expectedDocumentRevision: envelope.revision,
        expectedContentSha256: envelope.contentSha256,
      });
      if (!validation.ok) {
        setRun(response.run);
        setHandoff(null);
        setError(validation.reason);
        return;
      }

      if(savedRecapRequest && ["reviewable","failed","rejected","promoted"].includes(response.run.status)){
        localStorage.removeItem(pendingKey);setPendingState({key:pendingKey,value:null});
      }
      setRun(response.run);
      setHandoff(validation.handoff);
      setSourceContentSha256(response.source_content_sha256);
      setRunIdInLocationForDocument(selectedDocumentId, response.run.run_id);
      writeStoredRunId(selectedDocumentId, response.run.run_id);
      if (response.failure_kind) {
        setError(response.diagnostics.join("; ") || `Extraction ${response.failure_kind}`);
      }
    } catch (launchError) {
      if (generation !== launchGenerationRef.current) return;
      if (documentIdFromLocation() !== selectedDocumentId || scopeRef.current!==operationScope) return;
      setHandoff(null);
      setError(launchError instanceof Error ? launchError.message : "Extraction launch failed");
    } finally {
      if (generation === launchGenerationRef.current) {
        launchingRef.current = false;
        setLaunching(false);
      }
    }
  }, [canvas, documentId, profile, recap, worldId, pending, pendingKey, operationScope]);

  const recoverRecap = useCallback(async(retry=false)=>{
    if(launchingRef.current)return;
    if(!validRecapRequest(pending)||pending.document_id!==documentId||pending.managed_world_id!==worldId){
      setError("The saved Recap request is unavailable or belongs to another document/World.");return;
    }
    launchingRef.current=true;setLaunching(true);setError(null);
    const generation=++launchGenerationRef.current;refreshGenerationRef.current+=1;
    try{
      const status=await (retry?launchBuildRecap(pending):recoverBuildRecap(pending));
      if(scopeRef.current!==operationScope||generation!==launchGenerationRef.current||documentIdFromLocation()!==documentId)return;
      assertRecapLaunchBinding(pending,status);
      const validation=validateExactRunIdentity({selectedDocumentId:documentId,requestedRunId:status.run.run_id,response:status,
        expectedDocumentRevision:pending.expected_revision,expectedContentSha256:pending.expected_content_sha256});
      if(!validation.ok)throw new Error(validation.reason);
      setRun(status.run);setHandoff(validation.handoff);setSourceContentSha256(status.source_content_sha256);
      writeStoredRunId(documentId,status.run.run_id);setRunIdInLocationForDocument(documentId,status.run.run_id);
      if(["reviewable","failed","rejected","promoted"].includes(status.run.status)){
        localStorage.removeItem(pendingKey);setPendingState({key:pendingKey,value:null});
      }
    }catch(reason){if(scopeRef.current===operationScope)setError(reason instanceof Error?reason.message:"Recap recovery unavailable");}
    finally{if(generation===launchGenerationRef.current){launchingRef.current=false;setLaunching(false);}}
  },[documentId,worldId,pending,pendingKey,operationScope]);

  // GET404 is not cancellation: an earlier POST may still be validating.
  // Retain its exact body before permitting a separate extraction.
  const setAsideRecap=useCallback(()=>{
    if(launchingRef.current||pending===null)return;
    try{
      const values=readHistory();
      const raw=localStorage.getItem(pendingKey);
      if(raw===null)throw new Error("The saved request changed. Reload before continuing.");
      let retained:unknown;try{retained=JSON.parse(raw);}catch{retained={unavailable:true,raw};}
      if(!values.some(value=>JSON.stringify(value)===JSON.stringify(retained)))values.push(retained);
      localStorage.setItem(historyKey,JSON.stringify(values));
      localStorage.removeItem(pendingKey);
      setHistoryState({key:historyKey,values});setPendingState({key:pendingKey,value:null});setError(null);
    }catch(reason){setError(reason instanceof Error?reason.message:"Could not retain the saved request.");}
  },[pending,pendingKey,historyKey,readHistory]);
  const restoreRecap=useCallback((index:number)=>{
    if(launchingRef.current||pending!==null)return;
    try{
      const value=readHistory()[index];
      if(!validRecapRequest(value)||value.document_id!==documentId||value.managed_world_id!==worldId)
        throw new Error("The saved Recap request is unavailable or belongs to another document/World.");
      localStorage.setItem(pendingKey,JSON.stringify(value));
      setPendingState({key:pendingKey,value});setError(null);
    }catch(reason){setError(reason instanceof Error?reason.message:"Could not restore the saved request.");}
  },[pending,pendingKey,readHistory,documentId,worldId]);

  const adoptDerivedRun = useCallback(async (receipt: BuildCorrectionReceipt, expectedDigest: string, isCurrent: () => boolean) => {
    const parent = run;
    const digest = (value: unknown) => typeof value === "string" && /^(?:sha256:)?[a-f0-9]{64}$/.test(value) ? value.replace(/^sha256:/, "") : null;
    if (!isCurrent() || !parent || !handoff || !sourceContentSha256 || receipt.schema !== (parent.source_domain==='recap'?'dmb_recap_evidence_correction_response_v1':'dmb_exact_run_evidence_correction_response_v1')
      || receipt.parentRunId !== parent.run_id || receipt.status !== "reviewable" || typeof receipt.runId !== "string" || !receipt.runId.trim() || receipt.runId === parent.run_id
      || !digest(expectedDigest) || digest(receipt.correctionDigest) !== digest(expectedDigest)
      || !digest(receipt.parentCandidateSha256) || !digest(receipt.candidateSha256) || !digest(receipt.correctionDigest)
      || digest(receipt.parentCandidateSha256) !== digest(parent.components?.candidate_graph?.sha256)) {
      throw new Error("The correction receipt does not match the selected source run.");
    }
    const status = await getExtractionRunStatus(receipt.runId);
    if (!isCurrent() || documentIdFromLocation() !== documentId || currentRunRef.current?.run_id !== parent.run_id) {
      throw new Error("The selected document or run changed. Reopen the original correction to recover it.");
    }
    const validation = validateExactRunIdentity({ selectedDocumentId: documentId, requestedRunId: receipt.runId,
      response: status, expectedDocumentRevision: handoff.document_revision, expectedContentSha256: sourceContentSha256 });
    if (!validation.ok || status.run.status !== "reviewable" || status.run.source_domain !== parent.source_domain || status.source_artifact_id !== parent.source_artifact_id
      || status.run.profile_id !== parent.profile_id || status.run.lineage?.parent_run_id !== parent.run_id
      || digest(String(status.run.lineage?.parent_candidate_sha256)) !== digest(receipt.parentCandidateSha256)
      || digest(status.run.components?.candidate_graph?.sha256) !== digest(receipt.candidateSha256)
      || digest(String(status.run.lineage?.correction_digest)) !== digest(receipt.correctionDigest)) {
      throw new Error("The corrected child run does not preserve this source and parent lineage.");
    }
    if(parent.source_domain==='recap'){
      if(quoteDigest(sourceContentSha256)!==quoteDigest(parent.components?.source_artifact?.sha256))throw new Error('The Recap source differs from its committed Build document.');
      assertRecapQuoteChild(parent,receipt as import('../api/types').RecapEvidenceCorrectionResponse,status.run);
    }
    return ()=>{
      if(!isCurrent()||documentIdFromLocation()!==documentId||currentRunRef.current?.run_id!==parent.run_id)throw new Error('The selected correction changed before adoption.');
      window.localStorage.setItem(`${RUN_STORAGE_PREFIX}${documentId}`,status.run.run_id);
      setRunIdInLocationForDocument(documentId,status.run.run_id);
      setRun(status.run);setHandoff(validation.handoff);setSourceContentSha256(status.source_content_sha256);setError(null);
    };
  }, [documentId, handoff, run, sourceContentSha256]);

  const adoptSemanticDecision = useCallback(async(receipt: RecapSemanticDecisionReceipt, isCurrent:()=>boolean)=>{
    const parent=run;
    if(!isCurrent()||!parent||!handoff||!sourceContentSha256||parent.run_id!==receipt.runId
      ||parent.source_domain!=='recap'||parent.lineage?.derivation!==RECAP_QUOTE_DERIVATION
      ||quoteDigest(parent.components?.candidate_graph?.sha256)!==receipt.candidateSha256
      ||quoteDigest((parent.lineage?.semantic_disposition as Record<string,unknown>|undefined)?.basis_sha256)!==receipt.basisSha256)throw new Error('The selected Recap changed before decision adoption.');
    const status=await getExtractionRunStatus(receipt.runId);
    if(!isCurrent()||documentIdFromLocation()!==documentId||currentRunRef.current?.run_id!==parent.run_id)throw new Error('The selected document or run changed. Recover the original review decision.');
    const validation=validateExactRunIdentity({selectedDocumentId:documentId,requestedRunId:receipt.runId,response:status,
      expectedDocumentRevision:handoff.document_revision,expectedContentSha256:sourceContentSha256});
    const decision=status.run.lineage?.semantic_disposition as Record<string,unknown>|undefined;
    if(!validation.ok||status.run.source_domain!=='recap'||status.run.status!=='reviewable'
      ||status.run.source_artifact_id!==parent.source_artifact_id||status.run.profile_id!==parent.profile_id
      ||status.run.campaign_id!==parent.campaign_id||status.run.session_id!==parent.session_id
      ||(status.run as ExtractionRunRecord & {revision?:unknown}).revision!==receipt.revision
      ||status.run.lineage?.derivation!==RECAP_QUOTE_DERIVATION
      ||quoteDigest(status.run.components?.candidate_graph?.sha256)!==receipt.candidateSha256
      ||!decision||decision.state!==receipt.state||decision.basis_sha256!==receipt.basisSha256
      ||decision.review_decision_ref!==receipt.reviewDecisionRef||decision.reviewer_id!==receipt.reviewerId||decision.decided_at!==receipt.decidedAt
      ||JSON.stringify(status.run.lineage?.world_campaign_ingest_context)!==JSON.stringify(parent.lineage?.world_campaign_ingest_context)
      ||['source_artifact','source_span_index'].some(key=>status.run.components?.[key]?.uri!==parent.components?.[key]?.uri
        ||quoteDigest(status.run.components?.[key]?.sha256)!==quoteDigest(parent.components?.[key]?.sha256)))throw new Error('The exact Recap decision could not be verified from its current run.');
    return ()=>{
      if(!isCurrent()||documentIdFromLocation()!==documentId||currentRunRef.current?.run_id!==parent.run_id)throw new Error('The selected Recap changed before adopting its decision.');
      setRun(status.run);setHandoff(validation.handoff);setSourceContentSha256(status.source_content_sha256);setError(null);
    };
  },[documentId,handoff,run,sourceContentSha256]);

  const canLaunch = Boolean(committedClean && !launching && pending===null);
  const canRefresh = !launching;
  const canOpenGraphReview = Boolean(
    !launching
    && run
    && handoff
    && run.status === "reviewable",
  );

  let statusLabel = "No extraction run";
  if (launching) statusLabel = "Launching extraction…";
  else if (run && !handoff && error) statusLabel = `Run ${run.run_id} · identity unresolved`;
  else if (run) statusLabel = `Run ${run.run_id} · ${run.status}`;
  else if (!localCleanMatch) statusLabel = "Commit a clean matching source to enable extraction";
  else if (document?.content_status !== "committed") statusLabel = "Commit source to enable extraction";

  return {
    document,
    snapshot,
    run,
    handoff,
    sourceContentSha256,
    adoptDerivedRun, adoptSemanticDecision,
    statusLabel,
    error,
    launching,
    pendingRecap:pending!==null, recoverRecap, savedRecapRequests, setAsideRecap, restoreRecap,
    canLaunch,
    canRefresh,
    canOpenGraphReview,
    refresh,
    launch,
  };
}
