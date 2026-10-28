import {useGuidedTour,type TourDispatchScope} from '../guidedTour/GuidedTour';
import {runPins} from '../guidedTour/ownerPins';
import type {WorldPlayRunRecordV2} from '../api/types';
import {WorldSessionPreparation} from '../combat/WorldSessionPreparation';
import {inspectSession,cancelSession,type WorldSessionRequest,type SessionSource} from '../combat/runEncountersApi';
import {exactIntent,withIntentLock} from '../combat/exactIntent';
import { useCallback, useEffect, useRef, useState } from "react";

import {
  getWorldOwnedPlanCommittedRevision,
  getWorldOwnedRunbookCommittedRevision,
  getPlayRun,
  getPlayRunReferenceManifest,
  getCommittedWorkspaceRevision,
  listWorldOwnedPlans,
  listWorldOwnedRunbooks,
  listWorkspaceDocuments,
  putWorldPlayRun,
  putPlayRun,
  putPlayRunReferenceManifest,
} from "../api/liveApi";
import type {
  WorldOwnedPlanRecordV2,
  WorldOwnedRunbookRecordV2,
  WorkspaceDocumentRecord,
} from "../api/types";
import {
  executeStartWorldRunAttempt,
  executeStartRunAttempt,
  type StartRunBinding,
  type StartRunDeps,
  type StartRunPhase,
  type WorldStartRunBinding,
  type WorldStartRunDeps,
  type WorldStartRunExpectedSourcePin,
} from "./startRunAttempt";
import {
  BlankRunbookCreateError,
  createBlankWorldRunbook,
  createBlankRunbook,
  resolveBlankRunbookCampaignId,
  type BlankRunbookAttempt,
  type WorldBlankRunbookAttempt,
} from "./blankRunbook";
import {
  playRunbookAuthoringCampaignMismatch,
  playRunbookAuthoringHref,
} from "./playRunbookAuthoringHref";

const liveStartRunDeps: StartRunDeps = {
  generateRunId: () => crypto.randomUUID(),
  getCommittedRevision: getCommittedWorkspaceRevision,
  putRun: putPlayRun,
  getRun: getPlayRun,
  putManifest: putPlayRunReferenceManifest,
  getManifest: getPlayRunReferenceManifest,
};

const liveWorldStartRunDeps: WorldStartRunDeps = {
  generateRunId: () => crypto.randomUUID(),
  getCommittedRevision: getWorldOwnedRunbookCommittedRevision,
  putRun: putWorldPlayRun,
  inspectCreation: (id,world)=>inspectSession(world,id),
};

type StartRunbookRecord = WorkspaceDocumentRecord | WorldOwnedRunbookRecordV2;
type StartRunAttemptBinding = StartRunBinding | WorldStartRunBinding;

type ListStatus = "loading" | "ready" | "empty" | "unavailable";
type AttemptStatus = "idle" | "starting" | "incomplete" | "blocked" | "replay_create";
type StartRunPanelScope = {
  worldId: string | null;
  campaignId: string | null;
  generation: number;
};

export function StartRunPanel({
  onStarted,
  productCampaignId = null,
  verifiedWorldId = null,
  initialPlanId = null,
  initialPlanRevisionPin = null,
  initialSceneId = null,
}: {
  onStarted: (runId: string) => void;
  productCampaignId?: string | null;
  verifiedWorldId?: string | null;
  initialPlanId?: string | null;
  initialPlanRevisionPin?: WorldStartRunExpectedSourcePin | null;
  initialSceneId?:string|null;
}) {
  const tour=useGuidedTour();
  const recordTourCreation=useCallback((run:WorldPlayRunRecordV2,request:WorldSessionRequest,scope:TourDispatchScope|null)=>{const pins=runPins(run);tour?.recordRunCreation({step:'play',target:pins.target,parent:pins.parent,origin:'acknowledged',observedAt:run.created_at,receiptId:`session-create:${run.run_id}:${run.playable_work_revision_id}`,proof:{kind:'run-creation',entrySceneId:request.entry_scene_id,preparedSceneIds:request.encounters.map(item=>item.scene_id)}},scope);},[tour?.recordRunCreation]);
  const [listStatus, setListStatus] = useState<ListStatus>("loading");
  const [listDetail, setListDetail] = useState<string | null>(null);
  const [runbooks, setRunbooks] = useState<StartRunbookRecord[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<WorldOwnedPlanRecordV2 | null>(null);
  const [planStatus, setPlanStatus] = useState<ListStatus>(initialPlanId ? "loading" : "empty");
  const [planDetail, setPlanDetail] = useState<string | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [attemptStatus, setAttemptStatus] = useState<AttemptStatus>("idle");
  const [attemptDetail, setAttemptDetail] = useState<string | null>(null);
  const [attempt, setAttempt] = useState<StartRunAttemptBinding | null>(null);
  const [confirmedRequest,setConfirmedRequest]=useState<WorldSessionRequest|null>(null);
  const [sessionSource,setSessionSource]=useState<SessionSource|null>(null);
  const [retainedWorldAttempt,setRetainedWorldAttempt]=useState<WorldStartRunBinding|null>(null);
  const [storageError,setStorageError]=useState<string|null>(null);
  const sessionKey=verifiedWorldId?`dmb.session.creation:${verifiedWorldId}`:null;
  useEffect(()=>{
    setRetainedWorldAttempt(null);setStorageError(null);
    if(!sessionKey)return;
    try{const raw=localStorage.getItem(sessionKey);if(raw){const saved=JSON.parse(raw) as WorldStartRunBinding;
      if(saved.worldId!==verifiedWorldId||saved.request?.schema_version!=='dmb_world_session_create_v1'||saved.playableArtifactId!==saved.request.playable_artifact_id)throw new Error('Stored session intent is invalid; it has been retained.');
      setRetainedWorldAttempt(saved);}}
    catch(error){setStorageError(String(error));}
  },[sessionKey,verifiedWorldId]);
  useEffect(()=>{
    let current=true;setSessionSource(null);setConfirmedRequest(null);
    if(!verifiedWorldId||!selectedDocumentId||retainedWorldAttempt)return;
    const request=initialPlanId===selectedDocumentId?getWorldOwnedPlanCommittedRevision(selectedDocumentId):getWorldOwnedRunbookCommittedRevision(selectedDocumentId,verifiedWorldId);
    request.then(source=>{if(current&&source.world_id===verifiedWorldId)setSessionSource({playable_artifact_id:source.document_id,expected_playable_revision:source.revision_n,expected_playable_work_revision_id:source.work_revision_id,expected_playable_content_sha256:source.content_sha256});}).catch(error=>{if(current)setAttemptDetail(String(error));});
    return()=>{current=false;};
  },[verifiedWorldId,selectedDocumentId,initialPlanId,retainedWorldAttempt]);
  async function retainSession(binding:WorldStartRunBinding){
    if(!sessionKey||binding.worldId!==verifiedWorldId)throw new Error('Session World changed before retention');
    await withIntentLock(sessionKey,()=>{
      if(!mountedRef.current||scopeRef.current.worldId!==binding.worldId)throw new Error('Session World changed before retention');
      const raw=localStorage.getItem(sessionKey);
      if(raw&&exactIntent(JSON.parse(raw))!==exactIntent(binding))throw new Error('Resolve the existing retained session creation first.');
      localStorage.setItem(sessionKey,JSON.stringify(binding));setRetainedWorldAttempt(binding);setAttempt(binding);
    });
  }
  async function clearRetainedSession(binding:WorldStartRunBinding){
    if(!sessionKey)return;
    await withIntentLock(sessionKey,()=>{
      if(!isCurrentScope(renderedScope))return;
      const raw=localStorage.getItem(sessionKey);
      if(raw&&exactIntent(JSON.parse(raw))!==exactIntent(binding))throw new Error('Retained session changed; recovery is preserved.');
      localStorage.removeItem(sessionKey);setRetainedWorldAttempt(null);
    });
  }
  const [campaignDraft, setCampaignDraft] = useState("");
  const [creatingBlank, setCreatingBlank] = useState(false);
  const [createBlankError, setCreateBlankError] = useState<string | null>(null);
  const [listRefreshWarning, setListRefreshWarning] = useState<string | null>(null);
  const [blankAttempt, setBlankAttempt] = useState<BlankRunbookAttempt | null>(null);
  const [worldBlankAttempt, setWorldBlankAttempt] = useState<WorldBlankRunbookAttempt | null>(null);
  const startedRef = useRef<string | null>(null);
  const mountedRef = useRef(true);
  const scopeRef = useRef<StartRunPanelScope>({
    worldId: verifiedWorldId,
    campaignId: productCampaignId,
    generation: 0,
  });
  const selectedDocumentRef = useRef(selectedDocumentId);
  const selectedDocumentScopeGenerationRef = useRef(scopeRef.current.generation);
  const selectionGenerationRef = useRef(0);
  if (
    scopeRef.current.worldId !== verifiedWorldId
    || scopeRef.current.campaignId !== productCampaignId
  ) {
    scopeRef.current = {
      worldId: verifiedWorldId,
      campaignId: productCampaignId,
      generation: scopeRef.current.generation + 1,
    };
    selectionGenerationRef.current += 1;
  }
  const renderedScope = scopeRef.current;
  if (selectedDocumentScopeGenerationRef.current === renderedScope.generation) {
    selectedDocumentRef.current = selectedDocumentId;
  }
  const selectDocument = useCallback((documentId: string | null) => {
    if (
      selectedDocumentScopeGenerationRef.current !== scopeRef.current.generation
      || selectedDocumentRef.current !== documentId
    ) {
      selectionGenerationRef.current += 1;
    }
    selectedDocumentRef.current = documentId;
    selectedDocumentScopeGenerationRef.current = scopeRef.current.generation;
    setSelectedDocumentId(documentId);
  }, []);
  const runbookListRequestRef = useRef(0);
  const planListRequestRef = useRef(0);
  const worldBlankAttemptsRef = useRef(new Map<string, WorldBlankRunbookAttempt>());
  const isCurrentScope = useCallback((scope: StartRunPanelScope) => (
    mountedRef.current
    && scopeRef.current.generation === scope.generation
    && scopeRef.current.worldId === scope.worldId
    && scopeRef.current.campaignId === scope.campaignId
  ), []);
  const isCurrentSelection = useCallback((
    scope: StartRunPanelScope,
    documentId: string | null,
    selectionGeneration: number,
  ) => (
    isCurrentScope(scope)
    && selectedDocumentScopeGenerationRef.current === scope.generation
    && selectionGenerationRef.current === selectionGeneration
    && selectedDocumentRef.current === documentId
  ), [isCurrentScope]);

  const refreshRunbooks = useCallback(async (scope: StartRunPanelScope = renderedScope) => {
    if (!isCurrentScope(scope)) return [];
    const request = runbookListRequestRef.current + 1;
    runbookListRequestRef.current = request;
    setListStatus("loading");
    setListDetail(null);
    let records: StartRunbookRecord[];
    try {
      records = scope.worldId
        ? (await listWorldOwnedRunbooks(scope.worldId)).records
        : (await listWorkspaceDocuments({ kind: "runbook", status: "active" })).records;
    } catch (error) {
      if (isCurrentScope(scope) && runbookListRequestRef.current === request) {
        setRunbooks([]);
        setListStatus("unavailable");
        setListDetail(error instanceof Error ? error.message : "Runbooks are unavailable.");
      }
      throw error;
    }
    if (isCurrentScope(scope) && runbookListRequestRef.current === request) {
      setRunbooks(records);
      setListStatus(records.length === 0 ? "empty" : "ready");
      setListDetail(null);
    }
    return records;
  }, [isCurrentScope, renderedScope]);

  useEffect(() => {
    if (initialPlanId != null) {
      setListStatus("empty");
      setRunbooks([]);
      return;
    }
    void refreshRunbooks(renderedScope).catch(() => undefined);
  }, [initialPlanId, refreshRunbooks, renderedScope]);

  useEffect(() => {
    selectionGenerationRef.current += 1;
    selectedDocumentRef.current = null;
    selectedDocumentScopeGenerationRef.current = renderedScope.generation;
    setSelectedDocumentId(null);
    setSelectedPlan(null);
    setPlanStatus(initialPlanId ? "loading" : "empty");
    setPlanDetail(null);
    setAttempt(null);
    setAttemptStatus("idle");
    setAttemptDetail(null);
    setBlankAttempt(null);
    setWorldBlankAttempt(
      renderedScope.worldId == null
        ? null
        : worldBlankAttemptsRef.current.get(renderedScope.worldId) ?? null,
    );
    setCreatingBlank(false);
    setCreateBlankError(null);
    setListRefreshWarning(null);
    startedRef.current = null;
  }, [initialPlanId, renderedScope]);

  useEffect(() => {
    if (initialPlanId == null) {
      setSelectedPlan(null);
      setPlanStatus("empty");
      setPlanDetail(null);
      return;
    }
    const scope = renderedScope;
    if (scope.worldId == null) {
      setSelectedPlan(null);
      setPlanStatus("unavailable");
      setPlanDetail("A saved Plan can only start Play from its selected managed World.");
      return;
    }
    const request = planListRequestRef.current + 1;
    planListRequestRef.current = request;
    setPlanStatus("loading");
    setPlanDetail(null);
    void listWorldOwnedPlans(scope.worldId).then((inventory) => {
      if (!isCurrentScope(scope) || planListRequestRef.current !== request) return;
      if (
        inventory.schema_version !== "dmb_workspace_document_registry_v2"
        || inventory.scope_mode !== "world"
        || inventory.world_id !== scope.worldId
      ) {
        throw new TypeError("World Plan inventory does not match the selected World.");
      }
      const record = inventory.records.find((candidate) => candidate.document_id === initialPlanId);
      if (
        record == null
        || record.schema_version !== "dmb_world_owned_plan_record_v2"
        || record.world_id !== scope.worldId
        || record.campaign_id !== null
        || record.kind !== "plan"
      ) {
        throw new TypeError("Selected Plan does not belong to the selected World.");
      }
      if (record.status !== "active") {
        throw new TypeError("Selected World Plan is discarded.");
      }
      setSelectedPlan(record);
      setPlanStatus("ready");
      setSelectedDocumentId(record.document_id);
      selectedDocumentRef.current = record.document_id;
      selectedDocumentScopeGenerationRef.current = scope.generation;
      selectionGenerationRef.current += 1;
    }).catch((error: unknown) => {
      if (!isCurrentScope(scope) || planListRequestRef.current !== request) return;
      setSelectedPlan(null);
      setPlanStatus("unavailable");
      setPlanDetail(error instanceof Error ? error.message : "Selected World Plan is unavailable.");
    });
    return () => {
      if (planListRequestRef.current === request) planListRequestRef.current += 1;
    };
  }, [initialPlanId, isCurrentScope, renderedScope]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      selectionGenerationRef.current += 1;
    };
  }, []);

  const runAttempt = useCallback(async (phase: StartRunPhase, currentAttempt: StartRunAttemptBinding | null) => {
    const tourScope=tour?.captureScope()??null;
    const scope = renderedScope;
    const documentId = currentAttempt && "worldId" in currentAttempt ? currentAttempt.playableArtifactId : selectedDocumentId;
    const selectionGeneration = selectionGenerationRef.current;
    if (documentId == null || (phase === "fresh" && !isCurrentSelection(scope, documentId, selectionGeneration))) return;
    const selected = runbooks.find((record) => record.document_id === documentId);
    const plan = selectedPlan?.document_id === documentId ? selectedPlan : null;
    const expectedKind = currentAttempt && "worldId" in currentAttempt ? currentAttempt.playableKind : initialPlanId != null ? "plan" : "runbook";
    if (phase === "fresh" && expectedKind === "plan" && (
      scope.worldId == null
      || plan == null
      || plan.document_id !== initialPlanId
      || plan.world_id !== scope.worldId
      || plan.campaign_id !== null
      || plan.kind !== "plan"
      || plan.status !== "active"
    )) {
      setAttemptStatus("blocked");
      setAttemptDetail("Selected Plan does not belong to the selected World.");
      return;
    }
    if (expectedKind === "runbook" && scope.worldId && (
      selected == null
      || selected.schema_version !== "dmb_world_owned_runbook_record_v2"
      || selected.world_id !== scope.worldId
      || selected.campaign_id !== null
    )) {
      setAttemptStatus("blocked");
      setAttemptDetail("Runbook does not belong to the selected World.");
      return;
    }
    if (!scope.worldId && selected?.schema_version === "dmb_world_owned_runbook_record_v2") {
      setAttemptStatus("blocked");
      setAttemptDetail("World-owned Runbooks require their selected managed World.");
      return;
    }
    if (scope.worldId && currentAttempt != null && !("worldId" in currentAttempt)) {
      setAttemptStatus("blocked");
      setAttemptDetail("This Start Run attempt belongs to Campaign scope, not the selected World.");
      return;
    }
    if (!scope.worldId && currentAttempt != null && "worldId" in currentAttempt) {
      setAttemptStatus("blocked");
      setAttemptDetail("This Start Run attempt belongs to another World scope.");
      return;
    }
    setAttemptStatus("starting");
    setAttemptDetail(null);
    const worldDeps: WorldStartRunDeps = expectedKind === "plan"
      ? {
        ...liveWorldStartRunDeps,
        getCommittedRevision: async (requestedDocumentId, requestedWorldId) => {
          const committed = await getWorldOwnedPlanCommittedRevision(requestedDocumentId);
          if (
            committed.world_id !== requestedWorldId
            || committed.document_id !== requestedDocumentId
            || committed.kind !== "plan"
          ) {
            throw new TypeError("Committed Plan does not belong to the selected World.");
          }
          return committed;
        },
      }
      : liveWorldStartRunDeps;
    const result = scope.worldId
      ? await executeStartWorldRunAttempt({
        selectedDocumentId: documentId,
        worldId: scope.worldId,
        expectedKind,
        expectedSourcePin: expectedKind === "plan" ? initialPlanRevisionPin : null,
        attempt: currentAttempt as WorldStartRunBinding | null,
        phase,
        confirmedRequest,
        retainAttempt: retainSession,
        deps: worldDeps,
      })
      : await executeStartRunAttempt({
        selectedDocumentId: documentId,
        attempt: currentAttempt as StartRunBinding | null,
        phase,
        deps: liveStartRunDeps,
      });
    if (phase === "fresh" ? !isCurrentSelection(scope, documentId, selectionGeneration) : !isCurrentScope(scope)) return;
    if (result.outcome === "ready") {
      if (startedRef.current === result.binding.runId) return;
      if("worldId" in result.binding)await clearRetainedSession(result.binding);
      if(!isCurrentScope(scope))return;
      startedRef.current = result.binding.runId;
      setAttempt(result.binding);
      if(result.run.schema_version==='dmb_world_play_run_record_v2'&&'worldId' in result.binding&&result.binding.playableKind==='plan')recordTourCreation(result.run,result.binding.request,tourScope);
      onStarted(result.binding.runId);
      return;
    }
    if (result.outcome === "incomplete") {
      setAttempt(result.binding);
      setAttemptStatus("incomplete");
      setAttemptDetail(result.detail);
      return;
    }
    if (result.outcome === "replay_create") {
      setAttempt(result.binding);
      setAttemptStatus("replay_create");
      setAttemptDetail(result.detail);
      return;
    }
    setAttempt(result.binding ?? currentAttempt);
    setAttemptStatus("blocked");
    setAttemptDetail(result.detail);
  }, [initialPlanId, initialPlanRevisionPin, isCurrentScope, isCurrentSelection, onStarted, recordTourCreation, tour?.captureScope, renderedScope, runbooks, selectedDocumentId, selectedPlan, confirmedRequest, sessionKey]);

  const resolvedCampaignId = resolveBlankRunbookCampaignId(productCampaignId, campaignDraft);
  const currentWorldBlankAttempt = renderedScope.worldId != null
    && worldBlankAttempt?.worldId === renderedScope.worldId
    ? worldBlankAttempt
    : null;
  const showCreate = initialPlanId == null && (listStatus === "empty" || listStatus === "ready");
  const canCreateBlank = initialPlanId == null && (blankAttempt != null
    || currentWorldBlankAttempt != null
    || verifiedWorldId != null
    || resolvedCampaignId != null);
  const selectedRunbook = selectedDocumentId == null
    ? null
    : runbooks.find((record) => record.document_id === selectedDocumentId) ?? null;
  const planMode = initialPlanId != null;
  const selectedPlanReady = planMode
    && planStatus === "ready"
    && selectedPlan?.document_id === initialPlanId
    && selectedDocumentId === initialPlanId
    && selectedPlan.world_id === verifiedWorldId
    && initialPlanRevisionPin != null;
  const blockedPlanAttempt = attemptStatus === "blocked"
    && attempt != null
    && "playableKind" in attempt
    && attempt.playableKind === "plan";
  const campaignMismatchReason = selectedRunbook == null
    ? null
    : verifiedWorldId
      ? selectedRunbook.schema_version !== "dmb_world_owned_runbook_record_v2"
        || selectedRunbook.world_id !== verifiedWorldId
        || selectedRunbook.campaign_id !== null
        ? "Runbook does not belong to the selected World."
        : null
      : selectedRunbook.schema_version === "dmb_world_owned_runbook_record_v2"
        ? "World-owned Runbooks require their selected managed World."
        : playRunbookAuthoringCampaignMismatch(productCampaignId, selectedRunbook.campaign_id);
  const canOpenRunbookAuthoring = selectedDocumentId != null && campaignMismatchReason == null;

  const onCreateBlank = useCallback(async () => {
    const scope = renderedScope;
    if (!isCurrentScope(scope) || !canCreateBlank || creatingBlank) return;
    const selectedAtStart = selectedDocumentRef.current;
    const selectionGeneration = selectionGenerationRef.current;
    if (scope.worldId == null && (blankAttempt?.campaignId ?? resolvedCampaignId) == null) return;
    setCreatingBlank(true);
    setCreateBlankError(null);
    setListRefreshWarning(null);
    try {
      const createdRecord: StartRunbookRecord = scope.worldId
        ? (await createBlankWorldRunbook(scope.worldId, {
          attempt: currentWorldBlankAttempt,
          onAttemptRetained: (retained) => {
            worldBlankAttemptsRef.current.set(retained.worldId, retained);
            if (isCurrentScope(scope)) setWorldBlankAttempt(retained);
          },
        })).record
        : (await createBlankRunbook(blankAttempt?.campaignId ?? resolvedCampaignId ?? "", {
          attempt: blankAttempt,
          onAttemptRetained: (retained) => {
            if (isCurrentScope(scope)) setBlankAttempt(retained);
          },
        })).record;
      if (scope.worldId) worldBlankAttemptsRef.current.delete(scope.worldId);
      if (!isCurrentScope(scope)) return;
      setBlankAttempt(null);
      setWorldBlankAttempt(null);
      if (isCurrentSelection(scope, selectedAtStart, selectionGeneration)) {
        setAttempt(null);
        setAttemptStatus("idle");
        setAttemptDetail(null);
        startedRef.current = null;
      }
      try {
        const records = await refreshRunbooks(scope);
        if (!isCurrentScope(scope)) return;
        const selected = records.find((record) => record.document_id === createdRecord.document_id)
          ?? createdRecord;
        if (isCurrentSelection(scope, selectedAtStart, selectionGeneration)) {
          selectDocument(selected.document_id);
        }
        if (!records.some((record) => record.document_id === createdRecord.document_id)) {
          setRunbooks((current) => (
            current.some((record) => record.document_id === createdRecord.document_id)
              ? current
              : [...current, createdRecord]
          ));
          setListStatus("ready");
        }
      } catch (refreshError) {
        if (!isCurrentScope(scope)) return;
        setRunbooks((current) => (
          current.some((record) => record.document_id === createdRecord.document_id)
            ? current
            : [...current, createdRecord]
        ));
        setListStatus("ready");
        if (isCurrentSelection(scope, selectedAtStart, selectionGeneration)) {
          selectDocument(createdRecord.document_id);
        }
        setListRefreshWarning(
          refreshError instanceof Error
            ? refreshError.message
            : "Blank Runbook is committed; the Runbook list could not be refreshed.",
        );
      }
    } catch (error) {
      if (!isCurrentScope(scope)) return;
      if (error instanceof BlankRunbookCreateError && error.attempt) {
        if ("worldId" in error.attempt) {
          worldBlankAttemptsRef.current.set(error.attempt.worldId, error.attempt);
          setWorldBlankAttempt(error.attempt);
        } else setBlankAttempt(error.attempt);
      }
      setCreateBlankError(
        error instanceof Error ? error.message : "Failed to create a blank Runbook.",
      );
    } finally {
      if (isCurrentScope(scope)) setCreatingBlank(false);
    }
  }, [blankAttempt, canCreateBlank, creatingBlank, currentWorldBlankAttempt, isCurrentScope, isCurrentSelection, refreshRunbooks, renderedScope, resolvedCampaignId, selectDocument]);

  return (
    <section className="play-start-run" data-testid="play-start-run">
      <h2>{planMode ? "Play this Plan" : "Choose your material"}</h2>
      {storageError&&<p role="alert">{storageError}</p>}
      {verifiedWorldId&&sessionSource&&!retainedWorldAttempt&&<WorldSessionPreparation worldId={verifiedWorldId} source={sessionSource} entrySceneId={initialSceneId} onChange={setConfirmedRequest} disabled={attemptStatus==='starting'}/>}
      {retainedWorldAttempt&&<section aria-label="Retained session creation"><p>A session creation is retained. Check, retry or cancel it before starting another.</p>
      <button disabled={attemptStatus==='starting'} onClick={()=>{selectDocument(retainedWorldAttempt.playableArtifactId);void runAttempt('replay_create',retainedWorldAttempt);}}>Retry retained session</button>
      <button disabled={attemptStatus==='starting'} onClick={async()=>{const tourScope=tour?.captureScope()??null;setAttemptStatus('starting');try{const result=await inspectSession(retainedWorldAttempt.worldId,retainedWorldAttempt.runId);if(!isCurrentScope(renderedScope))return;if(result?.state==='applied'){const {assertSessionOutcome}=await import('../combat/runEncountersApi');assertSessionOutcome(result,retainedWorldAttempt.worldId,retainedWorldAttempt.runId,retainedWorldAttempt.request);await clearRetainedSession(retainedWorldAttempt);if(!isCurrentScope(renderedScope))return;if(retainedWorldAttempt.playableKind==='plan')recordTourCreation(result.run,retainedWorldAttempt.request,tourScope);onStarted(result.run.run_id);}else if(result?.state==='canceled'){const {assertSessionOutcome}=await import('../combat/runEncountersApi');assertSessionOutcome(result,retainedWorldAttempt.worldId,retainedWorldAttempt.runId,retainedWorldAttempt.request);await clearRetainedSession(retainedWorldAttempt);if(!isCurrentScope(renderedScope))return;setAttemptStatus('idle');}else{setAttemptStatus('replay_create');setAttemptDetail('No terminal result yet. The exact creation intent remains retained.');}}catch(error){if(!isCurrentScope(renderedScope))return;setAttemptStatus('replay_create');setAttemptDetail(String(error));}}}>Check session creation</button>
      <button disabled={attemptStatus==='starting'} onClick={async()=>{const tourScope=tour?.captureScope()??null;setAttemptStatus('starting');try{const result=await cancelSession(retainedWorldAttempt.worldId,retainedWorldAttempt.runId,retainedWorldAttempt.request);if(!isCurrentScope(renderedScope))return;const {assertSessionOutcome}=await import('../combat/runEncountersApi');assertSessionOutcome(result,retainedWorldAttempt.worldId,retainedWorldAttempt.runId,retainedWorldAttempt.request);await clearRetainedSession(retainedWorldAttempt);if(!isCurrentScope(renderedScope))return;setAttemptStatus('idle');if(result.state==='applied'){if(retainedWorldAttempt.playableKind==='plan')recordTourCreation(result.run,retainedWorldAttempt.request,tourScope);onStarted(result.run.run_id);}}catch(error){if(!isCurrentScope(renderedScope))return;setAttemptStatus('replay_create');setAttemptDetail(String(error));}}}>Cancel session creation</button>
      </section>}

      <p className="play-muted">
        {planMode
          ? "Start a fresh session from this saved Plan. Your previous sessions and notes are kept."
          : "Choose a saved Runbook to begin a fresh session."}
      </p>
      {planMode ? (
        <>
          {planStatus === "loading" ? <p>Loading selected World Plan…</p> : null}
          {planStatus === "unavailable" ? (
            <p role="alert" data-testid="play-start-plan-unavailable">
              {planDetail ?? "Selected World Plan is unavailable."}
            </p>
          ) : null}
          {planStatus === "ready" && selectedPlan ? (
            <div data-testid="play-start-selected-plan">
              <strong>{selectedPlan.title || "Untitled Plan"}</strong>
            </div>
          ) : null}
          {planStatus === "ready" && initialPlanRevisionPin == null ? (
            <p role="alert" data-testid="play-start-plan-pin-unavailable">
              The exact saved Plan revision is missing from the handoff. Reopen the Plan before starting.
            </p>
          ) : null}
        </>
      ) : (
        <>
          {listStatus === "loading" ? <p>Loading Runbooks…</p> : null}
          {listStatus === "unavailable" ? (
            <p role="alert" data-testid="play-start-run-unavailable">
              {listDetail ?? "Runbooks are unavailable."}
            </p>
          ) : null}
          {listStatus === "empty" ? (
            <p className="play-muted" data-testid="play-start-run-empty">No active Runbooks are available.</p>
          ) : null}
        </>
      )}
      {!planMode && listStatus === "ready" ? (
        <ul className="play-run-list">
          {runbooks.map((runbook) => {
            const selected = selectedDocumentId === runbook.document_id;
            return (
              <li key={runbook.document_id}>
                <button
                  type="button"
                  aria-pressed={selected}
                  data-testid={`play-start-runbook-${runbook.document_id}`}
                  onClick={() => {
                    selectDocument(runbook.document_id);
                    setAttempt(null);
                    setAttemptStatus("idle");
                    setAttemptDetail(null);
                    startedRef.current = null;
                  }}
                >
                  <strong>{runbook.title || "Untitled Runbook"}</strong>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
      {showCreate ? (
        <div className="play-blank-runbook" data-testid="play-create-blank-runbook">
          {verifiedWorldId ? (
            <p className="play-muted" data-testid="play-create-blank-runbook-world-context">
              World {verifiedWorldId}
            </p>
          ) : productCampaignId?.trim() ? (
            <p className="play-muted" data-testid="play-create-blank-runbook-campaign-context">
              Campaign {productCampaignId.trim()}
            </p>
          ) : (
            <label>
              Campaign
              <input
                type="text"
                autoComplete="off"
                spellCheck={false}
                value={campaignDraft}
                data-testid="play-create-blank-runbook-campaign"
                onChange={(event) => setCampaignDraft(event.target.value)}
              />
            </label>
          )}
          <button
            type="button"
            data-testid="play-create-blank-runbook-submit"
            disabled={!canCreateBlank || creatingBlank}
            onClick={() => {
              void onCreateBlank();
            }}
          >
            Create blank Runbook
          </button>
          {creatingBlank ? <p>Creating blank Runbook…</p> : null}
          {createBlankError ? (
            <p role="alert" data-testid="play-create-blank-runbook-error">
              {createBlankError}
            </p>
          ) : null}
          {listRefreshWarning ? (
            <p className="play-muted" data-testid="play-create-blank-runbook-list-warning">
              Blank Runbook is committed. {listRefreshWarning}
            </p>
          ) : null}
        </div>
      ) : null}
      <div className="play-controls">
        {!planMode ? <div className="play-edit-runbook-control">
          {canOpenRunbookAuthoring && selectedDocumentId ? (
            <a
              className="play-edit-runbook"
              data-testid="play-edit-runbook"
              href={playRunbookAuthoringHref(
                selectedDocumentId,
                typeof window !== "undefined" ? window.location.search : "",
              )}
            >
              Edit Runbook
            </a>
          ) : (
            <button
              type="button"
              className="play-edit-runbook"
              data-testid="play-edit-runbook"
              disabled
              aria-describedby={campaignMismatchReason ? "play-edit-runbook-campaign-mismatch" : undefined}
            >
              Edit Runbook
            </button>
          )}
          {campaignMismatchReason ? (
            <p
              id="play-edit-runbook-campaign-mismatch"
              role="status"
              className="play-edit-runbook-campaign-mismatch"
              data-testid="play-edit-runbook-campaign-mismatch"
            >
              {campaignMismatchReason}
            </p>
          ) : null}
        </div> : null}
        <button
          type="button"
          data-testid="play-start-run-submit"
          disabled={!!storageError || (!!verifiedWorldId && (!confirmedRequest || !!retainedWorldAttempt)) || selectedDocumentId == null || attemptStatus === "starting" || blockedPlanAttempt || (planMode && !selectedPlanReady)}
          onClick={() => {
            void runAttempt("fresh", null);
          }}
        >
          {planMode ? "Start session from Plan" : "Start session"}
        </button>
        {attemptStatus === "replay_create" && attempt ? (
          <button
            type="button"
            data-testid="play-start-run-replay"
            onClick={() => {
              void runAttempt("replay_create", attempt);
            }}
          >
            Retry starting this session
          </button>
        ) : null}
        {attemptStatus === "incomplete" && attempt ? (
          <button
            type="button"
            data-testid="play-start-run-retry-seal"
            onClick={() => {
              void runAttempt("retry_seal", attempt);
            }}
          >
            Retry setup
          </button>
        ) : null}
      </div>
      {attemptStatus === "starting" ? <p>Starting session…</p> : null}
      {attemptStatus === "blocked" ? (
        <p role="alert" data-testid="play-start-run-blocked">{attemptDetail}</p>
      ) : null}
      {attemptStatus === "incomplete" ? (
        <p role="alert" data-testid="play-start-run-incomplete">{attemptDetail}</p>
      ) : null}
        {attemptStatus === "replay_create" ? (
        <p role="alert" data-testid="play-start-run-replay-needed">{attemptDetail}</p>
      ) : null}
    </section>
  );
}
