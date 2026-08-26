import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";

import {
  LiveApiError,
  getPlayActiveRun,
  getPlayRun,
  getPlayRunReferenceManifest,
  getCommittedWorkspaceRevision,
  listPlayRuns,
  putPlayActiveRun,
  putPlayRunProgress,
} from "../api/liveApi";
import type { PlayRunRecord } from "../api/types";
import { usePublishAgentSurfaceContext } from "../agentInteraction/usePublishAgentSurfaceContext";
import { usePublishSurfaceInteraction } from "../agentInteraction/usePublishSurfaceInteraction";
import { AppChrome } from "../chrome/AppChrome";
import { buildSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";
import {
  RunbookTableDeck,
  type RunbookMutationStatus,
} from "./runbook/RunbookTableDeck";
import { StartRunPanel } from "./StartRunPanel";
import {
  admitNativeRunbook,
  isCanonicalUuid,
  isNativeRunbookReadyV1,
  isNativeRunbookReadyV2,
  overlayRuntimeOnDeck,
  type NativeRunbookAdmission,
  type NativeRunbookReadyDeck,
  type NativeRunbookReadyV2,
} from "./runbook/nativeRunbookProjection";
import {
  deriveV2OpeningBeatIdFromMarkdown,
  playRunProgressIsEmpty,
  v2SeedProgress,
} from "./runbook/v2RuntimeProjection";
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

function playChooserQuery(search: string): boolean {
  const params = new URLSearchParams(search);
  return params.get("choose") === "1" && !params.has("run");
}

function navigateToRun(runId: string): void {
  window.history.pushState({}, "", `/play?run=${encodeURIComponent(runId)}`);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function replaceToRun(runId: string): void {
  window.history.replaceState({}, "", `/play?run=${encodeURIComponent(runId)}`);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function navigateToChooser(): void {
  window.history.pushState({}, "", "/play?choose=1");
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

type PlayPublicationAuthority = {
  campaignId: string | null;
  documentId: string | null;
  ambientSummary: string;
  instanceId: string;
};

function playPublicationAuthority(input: {
  admittedRun: PlayRunRecord | null;
  runQuery: string | null;
}): PlayPublicationAuthority {
  const admittedRun = input.admittedRun;
  return {
    campaignId: admittedRun?.campaign_id ?? null,
    documentId: admittedRun?.playable_artifact_id ?? null,
    ambientSummary: admittedRun
      ? `Play · run ${admittedRun.run_id}`
      : input.runQuery
        ? `Play · run ${input.runQuery}`
        : "Play · choose a Run",
    instanceId: admittedRun?.run_id ?? input.runQuery ?? "chooser",
  };
}

function PlaySurfacePublisher({
  admittedRun,
  runQuery,
}: {
  admittedRun: PlayRunRecord | null;
  runQuery: string | null;
}) {
  const authority = useMemo(
    () => playPublicationAuthority({ admittedRun, runQuery }),
    [admittedRun, runQuery],
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
      label: "Play",
      campaignId: authority.campaignId,
      documentId: authority.documentId,
      sessionNumber: null,
      ambientSummary: authority.ambientSummary,
      pointers: [],
    },
    tools: [],
    editCommands: [],
    projections: [],
    projectionBindings: [],
  }), [authority]);

  const agentContext = useMemo(
    () => ({
      surfaceId: "play" as const,
      label: "Play",
      campaignId: authority.campaignId,
      documentId: authority.documentId,
      sessionNumber: null,
      ambientSummary: authority.ambientSummary,
      sourceEnvelope: null,
    }),
    [authority],
  );

  usePublishSurfaceInteraction(publication);
  usePublishAgentSurfaceContext(agentContext);
  return null;
}

function PlayChooser({ continuityWarning }: { continuityWarning?: string | null }) {
  const [status, setStatus] = useState<"loading" | "ready" | "unavailable" | "recovery_pending">("loading");
  const [detail, setDetail] = useState<string | null>(null);
  const [records, setRecords] = useState<PlayRunRecord[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setStatus("loading");
      try {
        const listed = await listPlayRuns();
        if (cancelled) return;
        setRecords(listed.records);
        setStatus("ready");
      } catch (error) {
        if (cancelled) return;
        if (error instanceof LiveApiError && error.status === 503) {
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
  }, []);

  return (
    <main className="play-surface play-chooser" data-testid="play-run-chooser">
      <header>
        <p className="play-kicker">Play</p>
        <h1>Choose a Run</h1>
        <p className="play-muted">Open one exact durable Run, or start a new exact Run from a committed Runbook. Nothing is selected until you choose it.</p>
        {continuityWarning ? (
          <p role="alert" className="play-continuity-warning" data-testid="play-active-run-warning">
            {continuityWarning}
          </p>
        ) : null}
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
                  href={`/play?run=${encodeURIComponent(record.run_id)}`}
                  onClick={(event) => {
                    event.preventDefault();
                    navigateToRun(record.run_id);
                  }}
                >
                  <strong>{record.run_id}</strong>
                  <span className="play-muted">
                    {" "}
                    · campaign {record.campaign_id} · revision {record.playable_revision}
                  </span>
                </a>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
      <StartRunPanel onStarted={navigateToRun} />
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
  const locationSearch = useSyncExternalStore(subscribeLocation, playLocationSearch, () => "");
  const runQuery = playRunQuery(locationSearch);
  const chooserQuery = playChooserQuery(locationSearch);
  const [loadStatus, setLoadStatus] = useState<PlayLoadStatus>(() => (
    playChooserQuery(window.location.search) ? "chooser" : "loading"
  ));
  const [detail, setDetail] = useState<string | null>(null);
  const [admission, setAdmission] = useState<NativeRunbookAdmission | null>(null);
  const [mutationStatus, setMutationStatus] = useState<RunbookMutationStatus>("idle");
  const loadSerialRef = useRef(0);
  const activeWriteRunRef = useRef<string | null>(null);
  const activeWriteQueueRef = useRef<Promise<void>>(Promise.resolve());

  const loadExactRun = useCallback(async (runId: string) => {
    const serial = loadSerialRef.current + 1;
    loadSerialRef.current = serial;
    setLoadStatus("loading");
    setDetail(null);
    setAdmission(null);
    setMutationStatus("idle");
    try {
      const loaded = await getPlayRun(runId);
      if (loadSerialRef.current !== serial) return;
      let manifest;
      try {
        manifest = await getPlayRunReferenceManifest(loaded.run_id);
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
        committed = await getCommittedWorkspaceRevision(
          loaded.playable_artifact_id,
          loaded.playable_revision,
        );
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
      let runForAdmission = loaded;
      if (manifest.schema_version === "dmb_play_run_reference_manifest_v2") {
        const openingBeatId = deriveV2OpeningBeatIdFromMarkdown(committed.markdown);
        if (openingBeatId == null) {
          setLoadStatus("integrity_failure");
          setDetail("v2 Playable has no Beat; native READY is fail-closed");
          setAdmission(null);
          return;
        }
        if (playRunProgressIsEmpty(runForAdmission.progress)) {
          try {
            runForAdmission = await putPlayRunProgress(runForAdmission.run_id, {
              expected_run_revision: runForAdmission.run_revision,
              progress: v2SeedProgress(openingBeatId),
            });
          } catch (error) {
            if (loadSerialRef.current !== serial) return;
            if (error instanceof LiveApiError && error.status === 409) {
              try {
                runForAdmission = await getPlayRun(runForAdmission.run_id);
              } catch (rereadError) {
                if (loadSerialRef.current !== serial) return;
                const classified = classifyLoadError(rereadError);
                setLoadStatus(classified);
                setDetail(rereadError instanceof Error ? rereadError.message : null);
                setAdmission(null);
                return;
              }
            } else {
              const classified = classifyLoadError(error);
              setLoadStatus(classified === "integrity_failure" ? classified : "unavailable");
              setDetail(error instanceof Error ? error.message : null);
              setAdmission(null);
              return;
            }
          }
          if (loadSerialRef.current !== serial) return;
        }
      }
      const nextAdmission = admitNativeRunbook({
        run: runForAdmission,
        manifest,
        committed,
      });
      if (loadSerialRef.current !== serial) return;
      setAdmission(nextAdmission);
      if (nextAdmission.status === "ready") {
        setLoadStatus("ready");
        setDetail(null);
        setMutationStatus("idle");
        if (activeWriteRunRef.current !== runForAdmission.run_id) {
          activeWriteRunRef.current = runForAdmission.run_id;
          activeWriteQueueRef.current = activeWriteQueueRef.current
            .catch(() => undefined)
            .then(async () => {
              try {
                await putPlayActiveRun(runForAdmission.run_id);
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
  }, []);

  useEffect(() => {
    if (chooserQuery) {
      loadSerialRef.current += 1;
      setLoadStatus("chooser");
      setDetail(null);
      setAdmission(null);
      setMutationStatus("idle");
      return;
    }
    if (runQuery == null) {
      const serial = loadSerialRef.current + 1;
      loadSerialRef.current = serial;
      setLoadStatus("loading");
      setDetail(null);
      setAdmission(null);
      setMutationStatus("idle");
      void (async () => {
        try {
          const active = await getPlayActiveRun();
          if (loadSerialRef.current !== serial) return;
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
      return;
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
  }, [chooserQuery, locationSearch, runQuery, loadExactRun]);

  const v1Deck: NativeRunbookReadyDeck | null =
    loadStatus === "ready" && admission != null && isNativeRunbookReadyV1(admission)
      ? admission
      : null;
  const v2Deck: NativeRunbookReadyV2 | null =
    loadStatus === "ready" && admission != null && isNativeRunbookReadyV2(admission)
      ? admission
      : null;
  const admittedRun = v1Deck?.run ?? v2Deck?.run ?? null;
  const publication = playPublicationAuthority({ admittedRun, runQuery });
  const blocked = v1Deck == null && v2Deck == null;

  return (
    <AppChrome activeRoute="play">
      <PlaySurfacePublisher admittedRun={admittedRun} runQuery={runQuery} />
      {loadStatus === "chooser" ? (
        <PlayChooser continuityWarning={detail} />
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
          <section data-testid="play-v2-runtime">
            <p className="play-kicker">Play</p>
            <h1>v2 Run READY</h1>
            <p data-testid="play-v2-current-beat">current Beat {v2Deck.currentBeatId}</p>
            <p data-testid="play-v2-current-scene">
              current Scene {v2Deck.currentSceneId ?? "none"}
            </p>
            <p className="play-muted" data-testid="play-v2-binding">
              revision {v2Deck.run.playable_revision} · {v2Deck.run.playable_content_sha256}
            </p>
          </section>
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
        </main>
      ) : null}
    </AppChrome>
  );
}
