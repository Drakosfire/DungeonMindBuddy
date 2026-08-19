import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";

import {
  LiveApiError,
  getPlayRun,
  getPlayRunReferenceManifest,
  getWorkspaceDocumentSnapshot,
  listPlayRuns,
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
  overlayRuntimeOnDeck,
  type NativeRunbookAdmission,
  type NativeRunbookReadyDeck,
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

function playRunQuery(): string | null {
  const params = new URLSearchParams(window.location.search);
  if (!params.has("run")) return null;
  return params.get("run");
}

function navigateToRun(runId: string): void {
  window.history.pushState({}, "", `/play?run=${encodeURIComponent(runId)}`);
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

function PlayChooser() {
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
  const runQuery = useSyncExternalStore(subscribeLocation, playRunQuery, playRunQuery);
  const [loadStatus, setLoadStatus] = useState<PlayLoadStatus>(runQuery == null ? "chooser" : "loading");
  const [detail, setDetail] = useState<string | null>(null);
  const [admission, setAdmission] = useState<NativeRunbookAdmission | null>(null);
  const [mutationStatus, setMutationStatus] = useState<RunbookMutationStatus>("idle");
  const loadSerialRef = useRef(0);

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
      let snapshot;
      try {
        snapshot = await getWorkspaceDocumentSnapshot(loaded.playable_artifact_id);
      } catch (error) {
        if (loadSerialRef.current !== serial) return;
        const classified = classifyLoadError(error);
        setLoadStatus(classified === "integrity_failure" ? "unavailable" : classified);
        setDetail(error instanceof Error ? error.message : null);
        setAdmission(null);
        return;
      }
      if (loadSerialRef.current !== serial) return;
      const nextAdmission = admitNativeRunbook({ run: loaded, manifest, snapshot });
      if (loadSerialRef.current !== serial) return;
      setAdmission(nextAdmission);
      if (nextAdmission.status === "ready") {
        setLoadStatus("ready");
        setDetail(null);
        setMutationStatus("idle");
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
    if (runQuery == null) {
      loadSerialRef.current += 1;
      setLoadStatus("chooser");
      setAdmission(null);
      setMutationStatus("idle");
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
  }, [runQuery, loadExactRun]);

  const readyDeck: NativeRunbookReadyDeck | null =
    loadStatus === "ready" && admission?.status === "ready" ? admission : null;
  const admittedRun = readyDeck?.run ?? null;
  const publication = playPublicationAuthority({ admittedRun, runQuery });
  const blocked = readyDeck == null;

  return (
    <AppChrome activeRoute="play">
      <PlaySurfacePublisher admittedRun={admittedRun} runQuery={runQuery} />
      {loadStatus === "chooser" ? (
        <PlayChooser />
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
      {readyDeck ? (
        <main
          className="play-surface"
          data-testid="play-surface-ready"
          data-play-campaign-id={publication.campaignId ?? ""}
          data-play-document-id={publication.documentId ?? ""}
        >
          <RunbookTableDeck
            key={readyDeck.run.run_id}
            deck={readyDeck}
            mutationStatus={mutationStatus}
            onMutationStatus={setMutationStatus}
            onAuthoritativeRun={(nextRun) => {
              if (nextRun.run_id !== readyDeck.run.run_id) return;
              const overlaid = overlayRuntimeOnDeck(readyDeck, nextRun);
              if (!overlaid) {
                void loadExactRun(nextRun.run_id);
                return;
              }
              setAdmission(overlaid);
            }}
          />
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
