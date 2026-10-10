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
import { usePublishAgentSurfaceContext } from "../agentInteraction/usePublishAgentSurfaceContext";
import { usePublishWorldPlayConversation } from "../agentInteraction/WorldAgentConversation";
import { usePublishSurfaceInteraction } from "../agentInteraction/usePublishSurfaceInteraction";
import { AppChrome } from "../chrome/AppChrome";
import { buildSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";
import {
  RunbookTableDeck,
  type RunbookMutationStatus,
} from "./runbook/RunbookTableDeck";
import { PlayCurrentMomentCockpit } from "./currentMoment/PlayCurrentMomentCockpit";
import { useOptionalWorldGraphLens } from "../graphLens";
import { campaignIdFromProductContext } from "./blankRunbook";
import { buildPlaySurfaceAgentContext } from "./playSurfaceAgentContext";
import { StartRunPanel } from "./StartRunPanel";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import {
  admitNativeRunbook,
  isCanonicalUuid,
  isNativeRunbookReadyV1,
  isNativeRunbookReadyV2,
  overlayRuntimeOnDeck,
  overlayRuntimeOnV2Ready,
  type NativeRunbookAdmission,
  type NativeRunbookReadyDeck,
  type NativeRunbookReadyV2,
} from "./runbook/nativeRunbookProjection";
import "./playSurface.css";

type PlayLoadStatus =
  | "chooser"
  | "loading"
  | "ready"
  | "miss"
  | "unavailable"
  | "recovery_pending"
  | "rebase_required"
  | "integrity_failure";

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
  snapshot: NativeRunbookReadyDeck["snapshot"] | NativeRunbookReadyV2["snapshot"],
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
}: {
  admittedRun: AnyPlayRunRecord | null;
  runQuery: string | null;
  currentMoment: { beatTitle: string; sceneTitle: string | null } | null;
}) {
  const authority = useMemo(
    () => playPublicationAuthority({ admittedRun, runQuery }),
    [admittedRun, runQuery],
  );
  const agentContextContribution = useMemo(
    () => buildPlaySurfaceAgentContext(
      admittedRun,
    ),
    [admittedRun],
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
      ambientSummary: authority.ambientSummary,
    },
    tools: [],
    editCommands: [],
    projections: [],
    projectionBindings: [],
  }), [authority, agentContextContribution]);

  usePublishWorldPlayConversation(admittedRun?.schema_version === "dmb_world_play_run_record_v2"
    ? {
      worldId: admittedRun.world_id,
      runId: admittedRun.run_id,
      runRevision: admittedRun.run_revision,
      surfaceInstanceId: publication.identity.instanceKey,
      beatTitle: currentMoment?.beatTitle ?? null,
      sceneTitle: currentMoment?.sceneTitle ?? null,
    } : null);

  const agentContext = useMemo(
    () => ({
      surfaceId: "play" as const,
      label: agentContextContribution.label,
      campaignId: agentContextContribution.campaignId,
      documentId: agentContextContribution.documentId,
      sessionNumber: agentContextContribution.sessionNumber,
      ambientSummary: authority.ambientSummary,
      sourceEnvelope: null,
    }),
    [agentContextContribution, authority.ambientSummary],
  );

  usePublishSurfaceInteraction(publication);
  usePublishAgentSurfaceContext(agentContext);
  return null;
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
  const world = useOptionalWorldGraphLens();
  const productCampaignId = selectedWorldId ? null : campaignIdFromProductContext(world);
  const [status, setStatus] = useState<"loading" | "ready" | "unavailable" | "recovery_pending">("loading");
  const [detail, setDetail] = useState<string | null>(null);
  const [records, setRecords] = useState<AnyPlayRunRecord[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setStatus("loading");
      try {
        const listed = selectedWorldId
          ? await listWorldPlayRuns(selectedWorldId)
          : await listPlayRuns();
        if (cancelled) return;
        setRecords(listed.records);
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
    };
  }, [selectedWorldId]);

  return (
    <main className="play-surface play-chooser" data-testid="play-run-chooser">
      <header>
        <p className="play-kicker">Play</p>
        <h1>Choose a Run</h1>
        <p className="play-muted">
          {initialPlanId
            ? "Open one exact durable Run, or start a new exact Run from the selected Plan."
            : "Open one exact durable Run, or start a new exact Run from a committed Runbook. Nothing is selected until you choose it."}
        </p>
        {continuityWarning ? (
          <p role="alert" className="play-continuity-warning" data-testid="play-active-run-warning">
            {continuityWarning}
          </p>
        ) : null}
        <LocalPlaySetupHint message={continuityWarning ?? detail} />
      </header>
      <section data-testid="play-existing-runs">
        <h2>Existing Runs</h2>
        {status === "loading" ? <p>Loading Runs…</p> : null}
        {status === "recovery_pending" ? (
          <p role="alert">Run recovery is pending. Play cannot list or mutate Runs until that recovery finishes.</p>
        ) : null}
        {status === "unavailable" ? (
          <p role="alert">{detail ?? "Play Runs are unavailable."}</p>
        ) : null}
        {status === "ready" && records.length === 0 ? (
          <p className="play-muted">No durable Runs are available.</p>
        ) : null}
        {status === "ready" && records.length > 0 ? (
          <ul className="play-run-list">
            {records.map((record) => (
              <li key={record.run_id}>
                <a
                  href={playHref({ run: record.run_id })}
                  onClick={(event) => {
                    event.preventDefault();
                    navigateToRun(record.run_id);
                  }}
                >
                  <strong>{record.run_id}</strong>
                  <span className="play-muted">
                    {" "}
                    · {record.schema_version === "dmb_world_play_run_record_v2"
                      ? `World ${record.world_id}`
                      : `campaign ${record.campaign_id}`} · revision {record.playable_revision}
                  </span>
                </a>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
      <StartRunPanel
        key={`${selectedWorldId ?? "campaign"}:${initialPlanId ?? "runbook-chooser"}`}
        onStarted={navigateToRun}
        productCampaignId={productCampaignId}
        verifiedWorldId={selectedWorldId}
        initialPlanId={selectedWorldId ? initialPlanId : null}
        initialPlanRevisionPin={selectedWorldId ? initialPlanRevisionPin : null}
      />
    </main>
  );
}

function statusCopy(status: PlayLoadStatus, detail: string | null): { title: string; body: string } {
  switch (status) {
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
      if (
        selectedWorldId
        && loaded.schema_version === "dmb_world_play_run_record_v2"
        && committed?.kind === "runbook"
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
      const nextAdmission = admitNativeRunbook({
        run: loaded,
        manifest,
        committed,
      });
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

  const v1Deck: NativeRunbookReadyDeck | null =
    loadStatus === "ready" && admission != null && isNativeRunbookReadyV1(admission)
      ? admission
      : null;
  const v2Deck: NativeRunbookReadyV2 | null =
    loadStatus === "ready" && admission != null && isNativeRunbookReadyV2(admission)
      ? admission
      : null;
  const admittedRun = v1Deck?.run ?? v2Deck?.run ?? null;
  const currentWorldBeat = v2Deck?.beats.find((beat) => beat.id === v2Deck.currentBeatId) ?? null;
  const currentWorldScene = currentWorldBeat?.scenes.find((scene) => scene.id === v2Deck?.currentSceneId) ?? null;
  const publication = playPublicationAuthority({ admittedRun, runQuery });
  const blocked = v1Deck == null && v2Deck == null;

  return (
    <AppChrome activeRoute="play">
      <PlaySurfacePublisher admittedRun={admittedRun} runQuery={runQuery}
        currentMoment={currentWorldBeat ? { beatTitle: currentWorldBeat.title, sceneTitle: currentWorldScene?.title ?? null } : null} />
      {loadStatus === "chooser" ? (
        <PlayChooser
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
      {v1Deck ? (
        <main
          className="play-surface"
          data-testid="play-surface-ready"
          data-play-campaign-id={publication.campaignId ?? ""}
          data-play-document-id={publication.documentId ?? ""}
        >
          <div className="play-continuity-actions">
            <button type="button" data-testid="play-start-new-run" onClick={navigateToChooser}>
              Start New Run
            </button>
          </div>
          <p className="play-source-cue" data-testid="play-source-cue" aria-label="Run source">
            {pinnedSourceCue(v1Deck.run, v1Deck.snapshot)}
          </p>
          <RunbookTableDeck
            key={v1Deck.run.run_id}
            deck={v1Deck}
            mutationStatus={mutationStatus}
            onMutationStatus={setMutationStatus}
            onAuthoritativeRun={(nextRun) => {
              if (nextRun.run_id !== v1Deck.run.run_id) return;
              const overlaid = overlayRuntimeOnDeck(v1Deck, nextRun);
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
      {v2Deck ? (
        <main
          className="play-surface"
          data-testid="play-surface-ready"
          data-play-grammar="v2"
          data-play-campaign-id={publication.campaignId ?? ""}
          data-play-document-id={publication.documentId ?? ""}
        >
          <div className="play-continuity-actions">
            <button type="button" data-testid="play-start-new-run" onClick={navigateToChooser}>
              Start New Run
            </button>
          </div>
          <p className="play-source-cue" data-testid="play-source-cue" aria-label="Run source">
            {pinnedSourceCue(v2Deck.run, v2Deck.snapshot)}
          </p>
          <PlayCurrentMomentCockpit
            key={v2Deck.run.run_id}
            deck={v2Deck}
            mutationStatus={mutationStatus}
            onMutationStatus={setMutationStatus}
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
