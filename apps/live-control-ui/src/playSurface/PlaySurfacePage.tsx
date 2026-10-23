import {useAgentInteraction} from '../agentInteraction/useAgentInteraction';
import {SceneEncounterLauncher} from '../combat/SceneEncounterLauncher';
import {TABLE_TOOL,TABLE_PROJECTION,TABLE_BINDING_ID,pendingTableKey,usePreparedTablesProjection,type PreparedTablesBinding} from "../preparedTables/preparedTablesProjection";
import {COMBAT_TOOL, COMBAT_PROJECTION, useCombatProjection} from "../combat/combatProjection";
import { RULES_LOOKUP_TOOL, RULES_LOOKUP_PROJECTION, useRulesLookupProjection } from "../rulesLookup/rulesLookupProjection";
import { useWorkspaceInventoryVersion } from "../workspaceLifecycle/workspaceInventoryChange";
import { WorkspaceTrashControl } from "../workspaceLifecycle/WorkspaceTrashControl";
import { getWorldPlayRunContent } from "../api/playRunContentApi";
import { admitEffectivePlayRunContent } from "./playRunEffectiveContent";
import { PlaySessionContentEditor } from "./content/PlaySessionContentEditor";
import { hasUnsubmittedPlayRunContent } from "./content/usePlayRunContentController";
import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";

import {
  LiveApiError,
  getWorldOwnedPlanCommittedRevision,
  getWorldOwnedRunbookCommittedRevision,
  getWorldPlayRun,
  getWorldPlayActiveRun,
  getWorldPlayRunReferenceManifest,
  getPlayActiveRun,
  getPlayRun,
  getPlayRunReferenceManifest,
  getCommittedWorkspaceRevision,
  listWorldPlayRuns,
  listWorldOwnedPlans,
  listWorldOwnedRunbooks,
  listWorkspaceDocuments,
  listPlayRuns,
  putWorldPlayRunRebase,
  putPlayActiveRun,
  putWorldPlayActiveRun,
} from "../api/liveApi";
import type {
  AnyPlayRunRecord,
  WorldOwnedCommittedRevisionV2,
  WorldOwnedRunbookCommittedRevisionV2,
  WorldPlayRunRecordV2,
  WorldPlayActiveRunStateV2,
} from "../api/types";
import type { PlayRunContent } from "./playRunContentTypes";
import { usePublishAgentSurfaceContext } from "../agentInteraction/usePublishAgentSurfaceContext";
import { usePublishWorldPlayConversation } from "../agentInteraction/WorldAgentConversation";
import { usePublishSurfaceInteraction } from "../agentInteraction/usePublishSurfaceInteraction";
import { AppChrome } from "../chrome/AppChrome";
import { buildSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";
import type { RunbookMutationStatus } from "./currentMoment/playRunMutation";
import { PlayCurrentMomentCockpit } from "./currentMoment/PlayCurrentMomentCockpit";
import { useOptionalWorldGraphLens } from "../graphLens";
import { campaignIdFromProductContext } from "./blankRunbook";
import { buildPlaySurfaceAgentContext } from "./playSurfaceAgentContext";
import {SessionEvidenceViewer} from "./review/SessionEvidenceViewer";
import { SessionReviewPanel } from "./review/SessionReviewPanel";
import {readSessionReview} from "./review/sessionReviewApi";
import { SurfaceWorldPicker } from "../shared/SurfaceWorldPicker";
import { StartRunPanel } from "./StartRunPanel";
import { SurfaceContextAction } from "../surfaceInteraction/contextHost";
import { PlaySurfaceContext, playSurfaceContextIdentity } from "./components/PlaySurfaceContext";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import {
  admitNativeRunbook,
  isCanonicalUuid,
  isNativeRunbookReadyV2,
  overlayRuntimeOnV2Ready,
  type NativeRunbookAdmission,
  type NativeRunbookReadyV2,
} from "./runbook/nativeRunbookProjection";
import "./playSurface.css";

type PlayLoadStatus =
  | "chooser"
  | "loading"
  | "ready"
  | "miss"
  | "trashed"
  | "unavailable"
  | "recovery_pending"
  | "rebase_required"
  | "integrity_failure"
  | "unsupported_playable";

function subscribeLocation(onStoreChange: () => void): () => void {
  window.addEventListener("popstate", onStoreChange);
  return () => window.removeEventListener("popstate", onStoreChange);
}

function playLocationSearch(): string {
  return window.location.search;
}

function playRunQuery(search: string): string | null {
  const params = new URLSearchParams(search);
  if (!params.has("run")) return null;
  return params.get("run");
}

function playPlanQuery(search: string): string | null {
  const params = new URLSearchParams(search);
  return params.has("run") ? null : params.get("plan");
}

function playPlanRevisionPin(search: string): {
  revisionN: number;
  workRevisionId: string;
  contentSha256: string;
} | null {
  const params = new URLSearchParams(search);
  const revisionN = Number(params.get("plan_revision"));
  const workRevisionId = params.get("plan_work_revision_id") ?? "";
  const contentSha256 = params.get("plan_sha256") ?? "";
  if (
    !Number.isInteger(revisionN)
    || revisionN <= 0
    || !isCanonicalUuid(workRevisionId)
    || !/^[0-9a-f]{64}$/.test(contentSha256)
  ) return null;
  return { revisionN, workRevisionId, contentSha256 };
}

function playChooserQuery(search: string): boolean {
  const params = new URLSearchParams(search);
  return !params.has("run") && (params.get("choose") === "1" || params.has("plan"));
}

async function getWorldOwnedPinnedPlayableRevision(
  documentId: string,
  worldId: string,
  revisionN: number,
  expectedSha256: string,
): Promise<WorldOwnedCommittedRevisionV2 | WorldOwnedRunbookCommittedRevisionV2> {
  try {
    const committed = await getWorldOwnedPlanCommittedRevision(documentId, revisionN);
    if (
      committed.schema_version !== "dmb_workspace_committed_revision_v2"
      || committed.scope_mode !== "world"
      || committed.world_id !== worldId
      || committed.document_id !== documentId
      || committed.kind !== "plan"
    ) {
      throw new TypeError("Exact committed World Plan does not match the selected Run source.");
    }
    if (committed.revision_n !== revisionN || committed.content_sha256 !== expectedSha256) {
      throw new TypeError("Exact committed World Plan does not match the Run's revision and digest.");
    }
    return committed;
  } catch (error) {
    if (!(error instanceof LiveApiError && error.status === 404)) throw error;
  }
  return getWorldOwnedRunbookCommittedRevision(
    documentId,
    worldId,
    revisionN,
    expectedSha256,
  );
}

function playHref(query: Record<string, string>): string {
  const params = new URLSearchParams();
  const worldId = new URLSearchParams(window.location.search).get("world");
  if (worldId) params.set("world", worldId);
  for (const [key, value] of Object.entries(query)) params.set(key, value);
  return `/play?${params.toString()}`;
}

function navigateToRun(runId: string): void {
  window.history.pushState({}, "", playHref({ run: runId }));
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function isApplicationStateUnavailableMessage(message: string | null | undefined): boolean {
  if (!message) return false;
  return /DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL|application state is unavailable/i.test(
    message,
  );
}

function LocalPlaySetupHint({ message }: { message: string | null | undefined }) {
  if (!import.meta.env.DEV || !isApplicationStateUnavailableMessage(message)) {
    return null;
  }
  return (
    <p role="note" className="play-muted" data-testid="play-local-setup-hint">
      Local Play setup is incomplete.
      <br />
      Run:
      <br />
      uv run python scripts/bootstrap_local_play.py check
    </p>
  );
}

function replaceToRun(runId: string): void {
  window.history.replaceState({}, "", playHref({ run: runId }));
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function navigateToChooser(): void {
  window.history.pushState({}, "", playHref({ choose: "1" }));
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function classifyLoadError(error: unknown): Extract<PlayLoadStatus, "miss" | "unavailable" | "recovery_pending" | "integrity_failure"> {
  if (error instanceof LiveApiError) {
    if (error.status === 404) return "miss";
    if (error.status === 503) return "recovery_pending";
    if (error.status === 422 || error.status === 409) return "integrity_failure";
  }
  return "unavailable";
}

function isWorldPlayActiveRunState(value: unknown, worldId: string): value is WorldPlayActiveRunStateV2 {
  if (typeof value !== "object" || value === null) return false;
  const state = value as Partial<WorldPlayActiveRunStateV2>;
  if (
    state.schema_version !== "dmb_world_play_active_run_v2"
    || state.world_id !== worldId
    || !(state.run_id === null || (typeof state.run_id === "string" && isCanonicalUuid(state.run_id)))
    || !(state.selected_at === null || (
      typeof state.selected_at === "string"
      && state.selected_at.trim() !== ""
      && Number.isFinite(Date.parse(state.selected_at))
    ))
  ) return false;
  return (state.run_id === null) === (state.selected_at === null);
}

type PlayPublicationAuthority = {
  campaignId: string | null;
  documentId: string | null;
  ambientSummary: string;
  instanceId: string;
};

type PlayRouteIdentity = {
  worldId: string | null;
  runId: string | null;
  chooser: boolean;
  search: string;
  generation: number;
};

function playPublicationAuthority(input: {
  admittedRun: AnyPlayRunRecord | null;
  runQuery: string | null;
}): PlayPublicationAuthority {
  const admittedRun = input.admittedRun;
  const campaignRun = admittedRun?.schema_version === "dmb_play_run_record_v1" ? admittedRun : null;
  return {
    campaignId: campaignRun?.campaign_id ?? null,
    documentId: campaignRun?.playable_artifact_id ?? null,
    ambientSummary: campaignRun
      ? `Play · run ${campaignRun.run_id}`
      : input.runQuery
        ? `Play · run ${input.runQuery}`
        : "Play · choose a Run",
    instanceId: admittedRun?.run_id ?? input.runQuery ?? "chooser",
  };
}

function pinnedSourceCue(
  run: AnyPlayRunRecord,
  snapshot: NativeRunbookReadyV2["snapshot"],
): string {
  const sourceKind = "kind" in snapshot ? snapshot.kind : "record" in snapshot ? snapshot.record.kind : null;
  const version = run.playable_revision;
  if (sourceKind === "plan") return `Created from saved Plan version ${version}`;
  if (sourceKind === "runbook") return `Created from saved Runbook version ${version}`;
  if (sourceKind === "worldbuilding_source") return `Created from saved Worldbuilding source version ${version}`;
  return `Created from saved source version ${version}`;
}

function PlaySurfacePublisher({
  admittedRun,
  runQuery,
  currentMoment,
  sessionCopy = false,
  contentBasis = null,
  preparedTables = null,
}: {
  preparedTables?: PreparedTablesBinding | null;
  sessionCopy?: boolean;
  contentBasis?: import("../api/types").WorldPlayContentBasis | null;
  admittedRun: AnyPlayRunRecord | null;
  runQuery: string | null;
  currentMoment: { beatId: string; beatTitle: string; sceneId: string | null; sceneTitle: string | null } | null;
}) {
  const authority = useMemo(
    () => playPublicationAuthority({ admittedRun, runQuery }),
    [admittedRun, runQuery],
  );
  const agentContextContribution = useMemo(
    () => buildPlaySurfaceAgentContext(
      sessionCopy ? null : admittedRun,
    ),
    [admittedRun, sessionCopy],
  );

  const publication = useMemo<SurfaceInteractionPublication>(() => ({
    surfaceId: "play",
    label: "Play",
    identity: buildSurfaceInteractionIdentity({
      surfaceId: "play",
      instanceParts: ["play", authority.instanceId],
    }),
    canvas: null,
    agentContext: {
      ...agentContextContribution,
      ambientSummary: sessionCopy ? "Play session copy · Agent context unavailable" : authority.ambientSummary,
    },
    tools: [RULES_LOOKUP_TOOL, COMBAT_TOOL, ...(preparedTables ? [TABLE_TOOL] : [])],
    editCommands: [],
    projections: [RULES_LOOKUP_PROJECTION, COMBAT_PROJECTION, ...(preparedTables ? [TABLE_PROJECTION] : [])],
    projectionBindings: preparedTables ? [{id:TABLE_BINDING_ID,value:preparedTables}] : [],
  }), [authority, agentContextContribution, sessionCopy, preparedTables]);

  usePublishWorldPlayConversation(!sessionCopy && contentBasis != null && admittedRun?.schema_version === "dmb_world_play_run_record_v2"
    ? {
      worldId: admittedRun.world_id,
      runId: admittedRun.run_id,
      runRevision: admittedRun.run_revision,
      ...(contentBasis ? { contentBasis } : {}),
      surfaceInstanceId: publication.identity.instanceKey,
      beatTitle: currentMoment?.beatTitle ?? null,
      sceneTitle: currentMoment?.sceneTitle ?? null,
      beatId: currentMoment?.beatId ?? null,
      sceneId: currentMoment?.sceneId ?? null,
    } : null, sessionCopy ? "Save your session changes before asking Buddy. Buddy will use the saved session copy and current-scene notes." : null);

  const agentContext = useMemo(
    () => ({
      surfaceId: "play" as const,
      label: agentContextContribution.label,
      campaignId: agentContextContribution.campaignId,
      documentId: agentContextContribution.documentId,
      sessionNumber: agentContextContribution.sessionNumber,
      ambientSummary: sessionCopy ? "Play session copy · Agent context unavailable" : authority.ambientSummary,
      sourceEnvelope: null,
    }),
    [agentContextContribution, authority.ambientSummary, sessionCopy],
  );

  usePublishSurfaceInteraction(publication);
  useRulesLookupProjection("play", true);
  const runEncounterContext=useMemo(()=>admittedRun?.schema_version==='dmb_world_play_run_record_v2'&&currentMoment?.sceneId?{
    worldId:admittedRun.world_id,runId:admittedRun.run_id,sceneId:currentMoment.sceneId,sceneTitle:currentMoment.sceneTitle??'Scene',
  }:null,[admittedRun?.run_id,admittedRun?.schema_version,currentMoment?.sceneId,currentMoment?.sceneTitle]);
  useCombatProjection("play", true,runEncounterContext);
  usePreparedTablesProjection();
  usePublishAgentSurfaceContext(agentContext);
  const {activateProjectionTool}=useAgentInteraction();
  return runEncounterContext?<PlaySurfaceContext id="play-scene-encounter" order={20} identity={publication.identity}><SceneEncounterLauncher onOpen={()=>void activateProjectionTool('combat')}/></PlaySurfaceContext>:null;
}

function PlayChooser({
  continuityWarning,
  initialPlanId,
  initialPlanRevisionPin,
}: {
  continuityWarning?: string | null;
  initialPlanId: string | null;
  initialPlanRevisionPin: ReturnType<typeof playPlanRevisionPin>;
}) {
  const selectedWorld = useSelectedWorld();
  const selectedWorldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const trashInventoryVersion = useWorkspaceInventoryVersion(selectedWorldId);
  const world = useOptionalWorldGraphLens();
  const productCampaignId = selectedWorldId ? null : campaignIdFromProductContext(world);
  const [status, setStatus] = useState<"loading" | "ready" | "unavailable" | "recovery_pending">("loading");
  const [detail, setDetail] = useState<string | null>(null);
  const [records, setRecords] = useState<AnyPlayRunRecord[]>([]);
  const [titles, setTitles] = useState<Record<string, string>>({});
  const [activeId, setActiveId] = useState<string | null>(null);
  const [endedIds,setEndedIds]=useState<string[]>([]);
  useEffect(()=>{
    let cancelled=false;setEndedIds([]);
    if(selectedWorldId){
      const queue=[...records],ended:string[]=[];
      const worker=async()=>{while(!cancelled&&queue.length){const record=queue.shift()!;try{if((await readSessionReview(record.run_id,selectedWorldId)).review?.status==="ended")ended.push(record.run_id)}catch{/* Session itself remains openable if review metadata is unavailable. */}}};
      void Promise.all(Array.from({length:Math.min(3,records.length)},worker)).then(()=>{if(!cancelled)setEndedIds(ended)});
    }
    return()=>{cancelled=true};
  },[records,selectedWorldId]);

  useEffect(() => {
    let cancelled = false;
    setTitles({});
    setActiveId(null);
    const sources = selectedWorldId
      ? [listWorldOwnedPlans(selectedWorldId), listWorldOwnedRunbooks(selectedWorldId)]
      : [listWorkspaceDocuments()];
    void Promise.allSettled(sources).then(results => {
      if (cancelled) return;
      const next: Record<string, string> = {};
      for (const result of results) {
        if (result.status !== "fulfilled" || !result.value) continue;
        for (const record of result.value.records) {
          if (selectedWorldId && (!("world_id" in record) || record.world_id !== selectedWorldId)) continue;
          if (record.title.trim()) next[record.document_id] = record.title;
        }
      }
      setTitles(next);
    });
    void Promise.resolve(continuityWarning ? null : selectedWorldId ? getWorldPlayActiveRun(selectedWorldId) : getPlayActiveRun())
      .then(active => {
        if (cancelled || !active) return;
        if (selectedWorldId && !isWorldPlayActiveRunState(active, selectedWorldId)) return;
        setActiveId(active.run_id);
      }).catch(() => { /* The list remains usable without Resume metadata. */ });
    return () => { cancelled = true; };
  }, [selectedWorldId, continuityWarning, trashInventoryVersion]);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    (async () => {
      setStatus("loading");
      setRecords([]);
      try {
        const listed = selectedWorldId
          ? await listWorldPlayRuns(selectedWorldId, controller.signal)
          : await listPlayRuns({}, controller.signal);
        if (cancelled) return;
        setRecords(listed.records.filter(record => selectedWorldId
          ? record.schema_version === "dmb_world_play_run_record_v2" && record.world_id === selectedWorldId
          : record.schema_version === "dmb_play_run_record_v1"));
        setStatus("ready");
      } catch (error) {
        if (cancelled) return;
        if (error instanceof LiveApiError && error.status === 503) {
          if (isApplicationStateUnavailableMessage(error.message)) {
            setStatus("unavailable");
            setDetail(error.message);
            return;
          }
          setStatus("recovery_pending");
          setDetail(error.message);
          return;
        }
        setStatus("unavailable");
        setDetail(error instanceof Error ? error.message : "Play Runs are unavailable.");
      }
    })();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [selectedWorldId, trashInventoryVersion]);

  const ordered = [...records].sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  const matching = initialPlanId ? ordered.filter(record => record.playable_artifact_id === initialPlanId) : ordered;
  const other = initialPlanId ? ordered.filter(record => record.playable_artifact_id !== initialPlanId) : [];
  const recommended = matching.find(record => record.run_id === activeId) ?? matching[0];
  const remaining = matching.filter(record => record.run_id !== recommended?.run_id);
  const dateLabel = (value: string) => {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "Date unavailable" : date.toLocaleString(undefined, {
      month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit",
    });
  };
  const title = (record: AnyPlayRunRecord) => titles[record.playable_artifact_id] || "Saved session";
  const sessionLink = (record: AnyPlayRunRecord, primary = false) => {
    const noteCount = Object.values(record.progress.notes_by_element_id).filter(note => note.trim()).length;
    return <li key={record.run_id}>
      <a className={primary ? "play-session-resume" : undefined}
        data-testid={`play-session-${record.run_id}`} href={playHref({ run: record.run_id }) + (endedIds.includes(record.run_id)?"&review=1":"")}
        onClick={event => { if(!endedIds.includes(record.run_id)){event.preventDefault(); navigateToRun(record.run_id);} }}>
        <strong>{endedIds.includes(record.run_id)?"Session reflections":primary ? "Resume session" : "Open session"} · {title(record)}</strong>
        <span className="play-muted">Last played {dateLabel(record.updated_at)} · {noteCount} saved {noteCount === 1 ? "note" : "notes"}</span>
      </a>
      <details className="play-session-details"><summary>Session details</summary>
        <p>Started {dateLabel(record.created_at)} · Source version {record.playable_revision}</p>
        <code>{record.run_id}</code>
      </details>
    </li>;
  };

  return (
    <main className="play-surface play-chooser" data-testid="play-run-chooser">
      <header>
        <p className="play-kicker">At the table</p>
        <h1>{initialPlanId && titles[initialPlanId] ? titles[initialPlanId] : "Bring your next session to life"}</h1>
        <p className="play-welcome-intro">Run your game with scenes, read-alouds, images and Buddy beside you.</p>
        <p className="play-muted">Take scene notes and edit as you improvise. Your changes save to this session’s copy, keeping the Plan intact.</p>
        {selectedWorldId ? <p className="play-welcome-plan"><a href={`/plan?world=${encodeURIComponent(selectedWorldId)}`}>Open a Plan →</a><span>Prepare scenes, then press Play to begin a session.</span></p> : null}
        {continuityWarning ? <p role="alert" className="play-continuity-warning" data-testid="play-active-run-warning">{continuityWarning}</p> : null}
        <LocalPlaySetupHint message={continuityWarning ?? detail} />
      </header>
      {!selectedWorldId ? <SurfaceWorldPicker surface="play" /> : null}
      <section data-testid="play-existing-runs" aria-label="Saved sessions">
        {selectedWorldId || records.length > 0 ? <h2>{selectedWorldId ? "Your sessions" : "Earlier campaign sessions"}</h2> : null}
        {status === "loading" ? <p>Loading sessions…</p> : null}
        {status === "recovery_pending" ? <p role="alert">Your sessions are being recovered. Please try again when recovery finishes.</p> : null}
        {status === "unavailable" ? <p role="alert">{detail ?? "Saved sessions are unavailable."}</p> : null}
        {selectedWorldId && status === "ready" && matching.length === 0 ? <p className="play-muted">
          {initialPlanId ? "You haven’t played this Plan yet. Start a session below." : "No sessions in this World yet. Open a Plan and press Play to start one."}
        </p> : null}
        {status === "ready" && recommended ? <ul className="play-run-list">{sessionLink(recommended, true)}</ul> : null}
        {status === "ready" && remaining.length > 0 ? <details className="play-session-group">
          <summary>Other sessions ({remaining.length})</summary>
          <ul className="play-run-list">{remaining.map(record => sessionLink(record))}</ul>
        </details> : null}
        {status === "ready" && other.length > 0 ? <details className="play-session-group">
          <summary>Sessions from other Plans ({other.length})</summary>
          <ul className="play-run-list">{other.map(record => sessionLink(record))}</ul>
        </details> : null}
      </section>
      {selectedWorldId ? <details className="play-session-group" open={Boolean(initialPlanId) && status === "ready" && matching.length === 0}>
        <summary>{initialPlanId ? "Start a new session from this Plan" : "Start from an existing Runbook"}</summary>
        <StartRunPanel
          key={`${selectedWorldId ?? "campaign"}:${initialPlanId ?? "runbook-chooser"}`}
          onStarted={navigateToRun} productCampaignId={productCampaignId} verifiedWorldId={selectedWorldId}
          initialPlanId={selectedWorldId ? initialPlanId : null}
          initialPlanRevisionPin={selectedWorldId ? initialPlanRevisionPin : null}
        />
      </details> : null}
    </main>
  );
}

function statusCopy(status: PlayLoadStatus, detail: string | null): { title: string; body: string } {
  switch (status) {
    case "trashed":
      return {title:"Session in Trash",body:"Open Trash in the toolbar to restore this session, including its notes and saved content."};
    case "miss":
      return { title: "Run not found", body: detail ?? "That Run UUID does not exist." };
    case "unavailable":
      return { title: "Play is unavailable", body: detail ?? "The Run could not be loaded." };
    case "recovery_pending":
      return {
        title: "Run recovery pending",
        body: detail ?? "This Run is blocked until rebase recovery finishes. Progress cannot be mutated.",
      };
    case "rebase_required":
      return {
        title: "Rebase required",
        body: detail ?? "The committed Runbook no longer matches this Run binding. Play will not overlay the old Runtime on newer prose.",
      };
    case "unsupported_playable":
      return { title: "Unsupported Playable format", body: detail ?? "Play requires v2 Playable markers. Open the source in Plan to author current cards." };
    case "integrity_failure":
      return {
        title: "Playable integrity failure",
        body: detail ?? "The Run, sealed manifest, and Runbook do not form one coherent authority set.",
      };
    default:
      return { title: "Play", body: detail ?? "" };
  }
}

export function PlaySurfacePage() {
  const search=useSyncExternalStore(subscribeLocation,playLocationSearch,()=>"");
  const world=useSelectedWorld();const params=new URLSearchParams(search);const revision=params.get("evidence_revision");const run=params.get("run");
  if(revision!==null&&run&&world.kind==="managed")return <AppChrome activeRoute="play"><SessionEvidenceViewer worldId={world.worldId} runId={run} revision={Number(revision)}/></AppChrome>;
  return <PlayRuntimePage/>;
}
function PlayRuntimePage() {
  const selectedWorld = useSelectedWorld();
  const selectedWorldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const locationSearch = useSyncExternalStore(subscribeLocation, playLocationSearch, () => "");
  const runQuery = playRunQuery(locationSearch);
  const initialPlanId = playPlanQuery(locationSearch);
  const initialPlanRevisionPin = playPlanRevisionPin(locationSearch);
  const chooserQuery = playChooserQuery(locationSearch);
  const routeIdentityRef = useRef<PlayRouteIdentity>({
    worldId: selectedWorldId,
    runId: runQuery,
    chooser: chooserQuery,
    search: locationSearch,
    generation: 0,
  });
  if (
    routeIdentityRef.current.worldId !== selectedWorldId
    || routeIdentityRef.current.runId !== runQuery
    || routeIdentityRef.current.chooser !== chooserQuery
    || routeIdentityRef.current.search !== locationSearch
  ) {
    routeIdentityRef.current = {
      worldId: selectedWorldId,
      runId: runQuery,
      chooser: chooserQuery,
      search: locationSearch,
      generation: routeIdentityRef.current.generation + 1,
    };
  }
  const renderedRoute = routeIdentityRef.current;
  const [loadStatus, setLoadStatus] = useState<PlayLoadStatus>(() => (
    playChooserQuery(window.location.search) ? "chooser" : "loading"
  ));
  const [detail, setDetail] = useState<string | null>(null);
  const [admission, setAdmission] = useState<NativeRunbookAdmission | null>(null);
  const admissionRef = useRef<NativeRunbookAdmission | null>(null);
  admissionRef.current = admission;
  const [sessionDraftState, setSessionDraftState] = useState<{ identity: string; hasUnsubmitted: boolean } | null>(null);
  const [noteDraftState, setNoteDraftState] = useState<{ identity: string; hasUnsubmitted: boolean } | null>(null);
  const [pendingWorldRebase, setPendingWorldRebase] = useState<{
    run: WorldPlayRunRecordV2;
    current: WorldOwnedRunbookCommittedRevisionV2;
  } | null>(null);
  const [mutationStatus, setMutationStatus] = useState<RunbookMutationStatus>("idle");
  const loadSerialRef = useRef(0);
  const rebaseRequestRef = useRef(0);
  const activeWriteRunRef = useRef<string | null>(null);
  const activeWorldWriteFenceRef = useRef<{ key: string } | null>(null);
  const settledWorldWriteIntentRef = useRef<{ key: string; status: "succeeded" | "failed" } | null>(null);
  const skipWorldActiveWriteRunRef = useRef<string | null>(null);
  const activeWriteQueueRef = useRef<Promise<void>>(Promise.resolve());
  const isCurrentRoute = useCallback((route: PlayRouteIdentity) => (
    routeIdentityRef.current.generation === route.generation
  ), []);

  const loadExactRun = useCallback(async (runId: string) => {
    const skipWorldActiveWrite = Boolean(
      selectedWorldId && skipWorldActiveWriteRunRef.current === runId,
    );
    if (skipWorldActiveWrite) skipWorldActiveWriteRunRef.current = null;
    const serial = loadSerialRef.current + 1;
    loadSerialRef.current = serial;
    setLoadStatus("loading");
    setDetail(null);
    setAdmission(null);
    setPendingWorldRebase(null);
    setMutationStatus("idle");
    try {
      const loaded = selectedWorldId
        ? await getWorldPlayRun(runId, selectedWorldId)
        : await getPlayRun(runId, { ensureNativeReady: true });
      if (loadSerialRef.current !== serial) return;
      if (
        selectedWorldId
        && (loaded.schema_version !== "dmb_world_play_run_record_v2" || loaded.world_id !== selectedWorldId)
      ) {
        setLoadStatus("integrity_failure");
        setDetail(`Run ${runId} does not belong to World ${selectedWorldId}.`);
        return;
      }
      if (loaded.schema_version === "dmb_world_play_run_record_v2" && loaded.lifecycle_status === "trashed") {
        setLoadStatus("trashed");
        return;
      }
      let manifest;
      try {
        manifest = selectedWorldId && loaded.schema_version === "dmb_world_play_run_record_v2"
          ? await getWorldPlayRunReferenceManifest(loaded.run_id, selectedWorldId)
          : loaded.schema_version === "dmb_play_run_record_v1"
            ? await getPlayRunReferenceManifest(loaded.run_id)
            : null;
        if (manifest == null) throw new TypeError("Run schema does not match the selected Play scope.");
      } catch (error) {
        if (loadSerialRef.current !== serial) return;
        const classified = error instanceof LiveApiError && error.status === 404
          ? "integrity_failure"
          : classifyLoadError(error);
        setLoadStatus(classified);
        setDetail(
          classified === "integrity_failure"
            ? "sealed Playable reference manifest is missing or unreadable"
            : error instanceof Error ? error.message : null,
        );
        setAdmission(null);
        return;
      }
      let committed;
      try {
        committed = selectedWorldId && loaded.schema_version === "dmb_world_play_run_record_v2"
          ? await getWorldOwnedPinnedPlayableRevision(
            loaded.playable_artifact_id,
            selectedWorldId,
            loaded.playable_revision,
            loaded.playable_content_sha256,
          )
          : loaded.schema_version === "dmb_play_run_record_v1"
            ? await getCommittedWorkspaceRevision(loaded.playable_artifact_id, loaded.playable_revision)
            : null;
        if (committed == null) throw new TypeError("Run schema does not match the selected committed-revision scope.");
      } catch (error) {
        if (loadSerialRef.current !== serial) return;
        if (error instanceof LiveApiError && (error.status === 404 || error.status === 409)) {
          setLoadStatus("integrity_failure");
          setDetail(error instanceof Error ? error.message : "bound Playable revision could not be loaded");
          setAdmission(null);
          return;
        }
        const classified = classifyLoadError(error);
        setLoadStatus(classified === "integrity_failure" ? "unavailable" : classified);
        setDetail(error instanceof Error ? error.message : null);
        setAdmission(null);
        return;
      }
      if (loadSerialRef.current !== serial) return;
      if (manifest.schema_version === "dmb_play_run_reference_manifest_v1") {
        setLoadStatus("unsupported_playable");
        setDetail("This session uses an unsupported Playable format. Play requires v2 markers; open its source in Plan to author current cards. The saved session and notes have not been changed.");
        setAdmission(null);
        setMutationStatus("idle");
        return;
      }
      let nextAdmission = admitNativeRunbook({ run: loaded, manifest, committed });
      if (selectedWorldId && loaded.schema_version === "dmb_world_play_run_record_v2"
        && isNativeRunbookReadyV2(nextAdmission)) {
        try {
          const content = await getWorldPlayRunContent(loaded.run_id, selectedWorldId);
          if (loadSerialRef.current !== serial) return;
          nextAdmission = await admitEffectivePlayRunContent(nextAdmission, content);
          if (loadSerialRef.current !== serial) return;
        } catch (error) {
          if (loadSerialRef.current !== serial) return;
          setLoadStatus(error instanceof TypeError || error instanceof LiveApiError && [0, 404, 409, 422].includes(error.status)
            ? "integrity_failure" : classifyLoadError(error));
          setDetail(error instanceof Error ? error.message : "Effective session content could not be admitted.");
          return;
        }
      }
      if (
        selectedWorldId
        && loaded.schema_version === "dmb_world_play_run_record_v2"
        && committed?.kind === "runbook"
        && isNativeRunbookReadyV2(nextAdmission)
        && nextAdmission.effectiveContent?.source !== "edition"
      ) {
        const current = await getWorldOwnedRunbookCommittedRevision(
          loaded.playable_artifact_id,
          selectedWorldId,
        );
        if (loadSerialRef.current !== serial) return;
        if (current.status !== "active") {
          setLoadStatus("integrity_failure");
          setDetail("The bound World Runbook is discarded; Play will not rebase to it.");
          return;
        }
        if (current.revision_n > loaded.playable_revision) {
          setPendingWorldRebase({ run: loaded, current });
          setLoadStatus("rebase_required");
          setDetail(
            `World Runbook ${loaded.playable_artifact_id} has committed revision ${current.revision_n}; Run ${loaded.run_id} is pinned to revision ${loaded.playable_revision}. Rebase only if you choose to apply the newer revision.`,
          );
          return;
        }
        if (
          current.revision_n !== loaded.playable_revision
          || current.content_sha256 !== loaded.playable_content_sha256
          || current.work_revision_id !== loaded.playable_work_revision_id
        ) {
          setLoadStatus("integrity_failure");
          setDetail("Current World Runbook authority conflicts with the Run's exact revision pin.");
          return;
        }
      }
      if (loadSerialRef.current !== serial) return;

      if (loadSerialRef.current !== serial) return;
      setAdmission(nextAdmission);
      if (nextAdmission.status === "ready") {
        setLoadStatus("ready");
        setDetail(null);
        setMutationStatus("idle");
        if (selectedWorldId) {
          const intentKey = JSON.stringify([
            routeIdentityRef.current.generation,
            selectedWorldId,
            loaded.run_id,
          ]);
          const sameIntentInFlight = activeWorldWriteFenceRef.current?.key === intentKey;
          const sameIntentSettled = settledWorldWriteIntentRef.current?.key === intentKey;
          if (!skipWorldActiveWrite && !sameIntentInFlight && !sameIntentSettled) {
            activeWorldWriteFenceRef.current = { key: intentKey };
            activeWriteQueueRef.current = activeWriteQueueRef.current
              .catch(() => undefined)
              .then(async () => {
                if (loadSerialRef.current !== serial) {
                  if (activeWorldWriteFenceRef.current?.key === intentKey) {
                    activeWorldWriteFenceRef.current = null;
                  }
                  return;
                }
                try {
                  await putWorldPlayActiveRun(selectedWorldId, loaded.run_id);
                  if (activeWorldWriteFenceRef.current?.key === intentKey) {
                    activeWorldWriteFenceRef.current = null;
                    settledWorldWriteIntentRef.current = { key: intentKey, status: "succeeded" };
                  }
                } catch (error) {
                  if (activeWorldWriteFenceRef.current?.key === intentKey) {
                    activeWorldWriteFenceRef.current = null;
                    settledWorldWriteIntentRef.current = { key: intentKey, status: "failed" };
                  }
                  if (loadSerialRef.current !== serial) return;
                  setDetail(
                    error instanceof Error
                      ? `Run is open, but Resume state could not be saved: ${error.message}`
                      : "Run is open, but Resume state could not be saved.",
                  );
                }
              });
        }
      } else if (!skipWorldActiveWrite && activeWriteRunRef.current !== loaded.run_id) {
        activeWriteRunRef.current = loaded.run_id;
        activeWriteQueueRef.current = activeWriteQueueRef.current
          .catch(() => undefined)
          .then(async () => {
            if (loadSerialRef.current !== serial) return;
            try {
              await putPlayActiveRun(loaded.run_id);
            } catch (error) {
              if (loadSerialRef.current !== serial) return;
              setDetail(
                error instanceof Error
                  ? `Run is open, but Resume state could not be saved: ${error.message}`
                  : "Run is open, but Resume state could not be saved.",
              );
            }
          });
        }
      } else {
        setLoadStatus(nextAdmission.status);
        setDetail(nextAdmission.reason);
        setMutationStatus("idle");
      }
    } catch (error) {
      if (loadSerialRef.current !== serial) return;
      const classified = classifyLoadError(error);
      setLoadStatus(classified);
      setDetail(error instanceof Error ? error.message : null);
      setAdmission(null);
    }
  }, [selectedWorldId]);

  const rebaseWorldRun = useCallback(async () => {
    const route = renderedRoute;
    const request = rebaseRequestRef.current + 1;
    rebaseRequestRef.current = request;
    const isCurrentRequest = () => (
      isCurrentRoute(route) && rebaseRequestRef.current === request
    );
    const pending = pendingWorldRebase;
    const worldId = route.worldId;
    if (
      !pending
      || !worldId
      || route.runId !== pending.run.run_id
      || pending.run.world_id !== worldId
      || !isCurrentRequest()
    ) return;
    let target: WorldOwnedRunbookCommittedRevisionV2 | null = null;
    setMutationStatus("saving");
    setDetail(null);
    try {
      target = await getWorldOwnedRunbookCommittedRevision(
        pending.run.playable_artifact_id,
        worldId,
      );
      if (!isCurrentRequest()) return;
      if (target.status !== "active") throw new Error("The selected World's Runbook is discarded.");
      if (target.revision_n <= pending.run.playable_revision) {
        await loadExactRun(pending.run.run_id);
        return;
      }
      const rebased = await putWorldPlayRunRebase(pending.run.run_id, worldId, {
        expected_run_revision: pending.run.run_revision,
        target_playable_revision: target.revision_n,
        target_playable_content_sha256: target.content_sha256,
      });
      if (
        rebased.world_id !== worldId
        || rebased.playable_artifact_id !== pending.run.playable_artifact_id
        || rebased.playable_revision !== target.revision_n
        || rebased.playable_work_revision_id !== target.work_revision_id
        || rebased.playable_content_sha256 !== target.content_sha256
        || rebased.rebased_from_run_revision !== pending.run.run_revision
      ) {
        throw new TypeError("World rebase response does not match the requested Runbook revision and Run revision.");
      }
      if (!isCurrentRequest()) return;
      setPendingWorldRebase(null);
      await loadExactRun(rebased.run_id);
    } catch (error) {
      let observed: WorldPlayRunRecordV2 | null = null;
      try {
        observed = await getWorldPlayRun(pending.run.run_id, worldId);
      } catch {
        observed = null;
      }
      if (!isCurrentRequest()) return;
      if (
        observed
        && target
        && observed.run_revision > pending.run.run_revision
        && observed.world_id === worldId
        && observed.playable_artifact_id === pending.run.playable_artifact_id
        && observed.playable_revision === target.revision_n
        && observed.playable_work_revision_id === target.work_revision_id
        && observed.playable_content_sha256 === target.content_sha256
        && observed.rebased_from_run_revision === pending.run.run_revision
      ) {
        setPendingWorldRebase(null);
        await loadExactRun(observed.run_id);
        return;
      }
      setMutationStatus("idle");
      setLoadStatus("rebase_required");
      setDetail(
        `${error instanceof Error ? error.message : "World Run rebase failed."} The exact Run was reread; no progress retry was made. Choose again or reload the Run.`,
      );
    }
  }, [isCurrentRoute, loadExactRun, pendingWorldRebase, renderedRoute]);

  useEffect(() => {
    if (chooserQuery) {
      loadSerialRef.current += 1;
      setLoadStatus("chooser");
      setDetail(null);
      setAdmission(null);
      setPendingWorldRebase(null);
      setMutationStatus("idle");
      return;
    }
    if (runQuery == null) {
      const serial = loadSerialRef.current + 1;
      loadSerialRef.current = serial;
      setLoadStatus("loading");
      setDetail(null);
      setAdmission(null);
      setPendingWorldRebase(null);
      setMutationStatus("idle");
      void (async () => {
        try {
          const active = selectedWorldId
            ? await getWorldPlayActiveRun(selectedWorldId)
            : await getPlayActiveRun();
          if (loadSerialRef.current !== serial) return;
          if (selectedWorldId) {
            if (!isWorldPlayActiveRunState(active, selectedWorldId)) {
              setLoadStatus("chooser");
              setDetail("World Resume state is malformed or belongs to another World. Choose a Run explicitly.");
              return;
            }
            if (active.run_id === null) {
              setLoadStatus("chooser");
              return;
            }
            const activeRun = await getWorldPlayRun(active.run_id, selectedWorldId);
            if (loadSerialRef.current !== serial) return;
            if (
              activeRun.schema_version !== "dmb_world_play_run_record_v2"
              || activeRun.run_id !== active.run_id
              || activeRun.world_id !== selectedWorldId
            ) {
              setLoadStatus("chooser");
              setDetail("Resume state points to another World. Choose a Run explicitly.");
              return;
            }
            skipWorldActiveWriteRunRef.current = activeRun.run_id;
            replaceToRun(activeRun.run_id);
            return;
          }
          if (active.run_id == null) {
            setLoadStatus("chooser");
            return;
          }
          if (!isCanonicalUuid(active.run_id)) {
            setLoadStatus("chooser");
            setDetail("Resume state is malformed. Choose a Run explicitly.");
            return;
          }
          replaceToRun(active.run_id);
        } catch (error) {
          if (loadSerialRef.current !== serial) return;
          setLoadStatus("chooser");
          setDetail(
            error instanceof Error
              ? `Resume state is unavailable. Choose a Run explicitly. (${error.message})`
              : "Resume state is unavailable. Choose a Run explicitly.",
          );
        }
      })();
      return () => { loadSerialRef.current += 1; };
    }
    if (!isCanonicalUuid(runQuery)) {
      loadSerialRef.current += 1;
      setLoadStatus("miss");
      setDetail("Run identity must be the exact canonical UUID.");
      setAdmission(null);
      return;
    }
    void loadExactRun(runQuery);
    return () => {
      loadSerialRef.current += 1;
    };
  }, [chooserQuery, locationSearch, runQuery, loadExactRun, selectedWorldId]);

  const v2Deck: NativeRunbookReadyV2 | null =
    loadStatus === "ready" && admission != null && isNativeRunbookReadyV2(admission)
      ? admission
      : null;
  const admittedRun = v2Deck?.run ?? null;
  const sessionCopyIdentity = v2Deck?.effectiveContent
    ? JSON.stringify([v2Deck.effectiveContent.world_id, v2Deck.effectiveContent.run_id, v2Deck.effectiveContent.origin])
    : null;
  const noteDraftIdentity = JSON.stringify([sessionCopyIdentity, admittedRun?.run_revision, v2Deck?.currentSceneId ?? null]);
  const sessionCopyBlocked = Boolean(v2Deck?.effectiveContent && (
    hasUnsubmittedPlayRunContent(v2Deck.effectiveContent)
    || sessionDraftState?.identity === sessionCopyIdentity && sessionDraftState.hasUnsubmitted
    || noteDraftState?.identity !== noteDraftIdentity || noteDraftState.hasUnsubmitted
  ));
  const onAcceptedSessionContent = useCallback((content: PlayRunContent) => {
    const routeGeneration = routeIdentityRef.current.generation;
    void (async () => {
      let source = admissionRef.current;
      while (source && routeIdentityRef.current.generation === routeGeneration) {
        if (!isNativeRunbookReadyV2(source) || source.run.schema_version !== "dmb_world_play_run_record_v2"
          || source.run.run_id !== content.run_id || source.run.world_id !== content.world_id) return;
        const currentContent = source.effectiveContent;
        if (currentContent && currentContent.edition_revision > content.edition_revision) return;
        if (currentContent && currentContent.edition_revision === content.edition_revision
          && currentContent.content_sha256 !== content.content_sha256) {
          throw new TypeError("The same session-copy revision was returned with different content.");
        }
        const projected = await admitEffectivePlayRunContent(source, content);
        if (routeIdentityRef.current.generation !== routeGeneration) return;
        const latest = admissionRef.current;
        if (latest !== source) {
          source = latest;
          continue;
        }
        admissionRef.current = projected;
        setAdmission(projected);
        return;
      }
    })().catch(error => {
      if (routeIdentityRef.current.generation !== routeGeneration) return;
      setLoadStatus("integrity_failure");
      setDetail(error instanceof Error ? error.message : "The saved session copy could not be projected.");
    });
  }, []);
  const onNoteDraftStateChange = useCallback((hasUnsubmitted: boolean) => {
    if (sessionCopyIdentity) setNoteDraftState({ identity: noteDraftIdentity, hasUnsubmitted });
  }, [sessionCopyIdentity, noteDraftIdentity]);
  const onSessionDraftStateChange = useCallback((hasUnsubmitted: boolean) => {
    if (sessionCopyIdentity) setSessionDraftState({ identity: sessionCopyIdentity, hasUnsubmitted });
  }, [sessionCopyIdentity]);
  const [tableHold,setTableHold]=useState<{scope:string;held:boolean}|null>(null);
  const tableScope=admittedRun?.schema_version === 'dmb_world_play_run_record_v2'
    ? pendingTableKey(admittedRun.world_id,admittedRun.run_id) : null;
  const recoveredTableHold=useMemo(()=>{
    if(!tableScope)return false;
    try{return localStorage.getItem(tableScope)!==null;}catch{return true;}
  },[tableScope]);
  const tableHeld=tableHold?.scope===tableScope ? tableHold.held : recoveredTableHold;
  const preparedTables=useMemo<PreparedTablesBinding|null>(()=>{
    if(admittedRun?.schema_version !== 'dmb_world_play_run_record_v2'||!tableScope)return null;
    const world=admittedRun.world_id,id=admittedRun.run_id;
    const current=()=>{const latest=admissionRef.current;return latest&&isNativeRunbookReadyV2(latest)&&latest.run.schema_version==='dmb_world_play_run_record_v2'&&latest.run.world_id===world&&latest.run.run_id===id?latest:null;};
    return {run:admittedRun,blocked:sessionCopyBlocked||mutationStatus!=='idle',
      onHeld:(held)=>{if(current())setTableHold({scope:tableScope,held});},
      onRun:(next)=>{
        const latest=current();if(!latest)throw new Error('Play session changed during the command');
        if(next.run_revision<latest.run.run_revision)return;
        const overlaid=overlayRuntimeOnV2Ready(latest,next);
        if(!overlaid)throw new Error('Refresh this session to inspect the saved roll');
        admissionRef.current=overlaid;setAdmission(overlaid);
      }};
  },[admittedRun,tableScope,sessionCopyBlocked,mutationStatus]);
  const currentWorldBeat = v2Deck?.beats.find((beat) => beat.id === v2Deck.currentBeatId) ?? null;
  const currentWorldScene = currentWorldBeat?.scenes.find((scene) => scene.id === v2Deck?.currentSceneId) ?? null;
  const publication = playPublicationAuthority({ admittedRun, runQuery });
  const blocked = v2Deck == null;

  return (
    <AppChrome activeRoute="play">
      {loadStatus !== "chooser" ? <PlaySurfaceContext id="play-page-context" order={10} identity={playSurfaceContextIdentity(admittedRun, runQuery)}>
        <SurfaceContextAction type="button" data-testid="play-load-run" onClick={navigateToChooser}>Load</SurfaceContextAction>
        {selectedWorldId ? <WorkspaceTrashControl showTrash={false} worldId={selectedWorldId}
          current={v2Deck?.effectiveContent && admittedRun ? {kind:"session", id:admittedRun.run_id,
            title:`${("record" in v2Deck.snapshot ? v2Deck.snapshot.record.title : v2Deck.snapshot.title)} — ${currentWorldScene?.title ?? "Play session"}`,
            surface:"play", revision:admittedRun.run_revision, content_revision:v2Deck.effectiveContent.edition_revision} : null}
          blocked={sessionCopyBlocked || tableHeld || mutationStatus !== "idle" || loadStatus !== "ready"}
          onTrashed={() => window.location.assign(`/play?world=${encodeURIComponent(selectedWorldId)}&choose=1`)}
          /> : null}
      </PlaySurfaceContext> : null}
      <PlaySurfacePublisher admittedRun={admittedRun} runQuery={runQuery} preparedTables={preparedTables}
        sessionCopy={sessionCopyBlocked}
        contentBasis={v2Deck?.effectiveContent ? { edition_revision: v2Deck.effectiveContent.edition_revision, edition_revision_id: v2Deck.effectiveContent.edition_revision_id, content_sha256: v2Deck.effectiveContent.content_sha256 } : null}
        currentMoment={currentWorldBeat ? { beatId: currentWorldBeat.id, beatTitle: currentWorldBeat.title,
          sceneId: currentWorldScene?.id ?? null, sceneTitle: currentWorldScene?.title ?? null } : null} />
      {loadStatus === "chooser" ? (
        <PlayChooser
          key={`${selectedWorldId ?? "campaign"}:${initialPlanId ?? "all"}`}
          continuityWarning={detail}
          initialPlanId={initialPlanId}
          initialPlanRevisionPin={initialPlanRevisionPin}
        />
      ) : null}
      {loadStatus === "loading" ? (
        <main
          className="play-status"
          data-testid="play-status-loading"
          data-play-campaign-id=""
          data-play-document-id=""
        >
          <p>Loading exact Run…</p>
        </main>
      ) : null}
      {v2Deck ? (
        <main
          className="play-surface"
          data-testid="play-surface-ready"
          data-play-grammar="v2"
          data-play-campaign-id={publication.campaignId ?? ""}
          data-play-document-id={publication.documentId ?? ""}
        >

          {selectedWorldId && v2Deck.run.schema_version === "dmb_world_play_run_record_v2" && v2Deck.effectiveContent ? <SessionReviewPanel key={`review:${v2Deck.run.run_id}`} runId={v2Deck.run.run_id} worldId={selectedWorldId} runRevision={v2Deck.run.run_revision} content={v2Deck.effectiveContent} blocked={sessionCopyBlocked||tableHeld||mutationStatus!=="idle"} sceneTitles={Object.fromEntries(v2Deck.beats.flatMap(beat=>[[beat.id,beat.title],...beat.scenes.map(scene=>[scene.id,scene.title])]))}/> : null}
          {v2Deck.effectiveContent ? <PlaySessionContentEditor
            key={sessionCopyIdentity}
            content={v2Deck.effectiveContent}
            currentSceneId={v2Deck.currentSceneId}
            originLabel={pinnedSourceCue(v2Deck.run, v2Deck.snapshot)}
            onAcceptedContent={onAcceptedSessionContent}
            onUnsubmittedChange={onSessionDraftStateChange}
            runRevision={v2Deck.run.run_revision}
            externalMutationBlocked={tableHeld}
            canPropose={!sessionCopyBlocked&&!tableHeld}
          /> : null}
          {sessionCopyBlocked ? (
            <p role="status" aria-label="Session copy Agent availability" className="play-muted"
              data-testid="play-session-copy-agent-notice">{"Save your session changes before asking Buddy. Buddy will use the saved session copy and current-scene notes."}</p>
          ) : null}
          <PlayCurrentMomentCockpit
            key={v2Deck.run.run_id}
            deck={v2Deck}
            externalMutationBlocked={tableHeld}
            mutationStatus={mutationStatus}
            onMutationStatus={setMutationStatus}
            onNoteUnsubmittedChange={onNoteDraftStateChange}
            onAuthoritativeRun={(nextRun) => {
              if (nextRun.run_id !== v2Deck.run.run_id) return;
              const overlaid = overlayRuntimeOnV2Ready(v2Deck, nextRun);
              if (!overlaid) {
                void loadExactRun(nextRun.run_id);
                return;
              }
              setAdmission(overlaid);
            }}
          />
          {detail ? (
            <p role="alert" className="play-continuity-warning" data-testid="play-active-run-save-warning">
              {detail}
            </p>
          ) : null}
        </main>
      ) : null}
      {blocked && loadStatus !== "chooser" && loadStatus !== "loading" && loadStatus !== "ready" ? (
        <main
          className="play-status"
          role="alert"
          data-testid={`play-status-${loadStatus}`}
          data-play-campaign-id=""
          data-play-document-id=""
        >
          <h1>{statusCopy(loadStatus, detail).title}</h1>
          <p>{statusCopy(loadStatus, detail).body}</p>
          {loadStatus === "rebase_required" && pendingWorldRebase ? (
            <button
              type="button"
              data-testid="play-world-run-rebase"
              disabled={mutationStatus === "saving"}
              onClick={() => { void rebaseWorldRun(); }}
            >
              Rebase this Run to the current World Runbook revision
            </button>
          ) : null}
        </main>
      ) : null}
    </AppChrome>
  );
}
