import { useCallback, useEffect, useRef, useState } from "react";

import {
  getPlayRun,
  getPlayRunReferenceManifest,
  getCommittedWorkspaceRevision,
  listWorkspaceDocuments,
  putPlayRun,
  putPlayRunReferenceManifest,
} from "../api/liveApi";
import type { WorkspaceDocumentRecord } from "../api/types";
import {
  executeStartRunAttempt,
  type StartRunBinding,
  type StartRunDeps,
  type StartRunPhase,
} from "./startRunAttempt";

const liveStartRunDeps: StartRunDeps = {
  generateRunId: () => crypto.randomUUID(),
  getCommittedRevision: getCommittedWorkspaceRevision,
  putRun: putPlayRun,
  getRun: getPlayRun,
  putManifest: putPlayRunReferenceManifest,
  getManifest: getPlayRunReferenceManifest,
};

type ListStatus = "loading" | "ready" | "empty" | "unavailable";
type AttemptStatus = "idle" | "starting" | "incomplete" | "blocked" | "replay_create";

export function StartRunPanel({
  onStarted,
}: {
  onStarted: (runId: string) => void;
}) {
  const [listStatus, setListStatus] = useState<ListStatus>("loading");
  const [listDetail, setListDetail] = useState<string | null>(null);
  const [runbooks, setRunbooks] = useState<WorkspaceDocumentRecord[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [attemptStatus, setAttemptStatus] = useState<AttemptStatus>("idle");
  const [attemptDetail, setAttemptDetail] = useState<string | null>(null);
  const [attempt, setAttempt] = useState<StartRunBinding | null>(null);
  const startedRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setListStatus("loading");
      setListDetail(null);
      try {
        const listed = await listWorkspaceDocuments({ kind: "runbook", status: "active" });
        if (cancelled) return;
        const records = listed.records;
        setRunbooks(records);
        setListStatus(records.length === 0 ? "empty" : "ready");
      } catch (error) {
        if (cancelled) return;
        setRunbooks([]);
        setListStatus("unavailable");
        setListDetail(error instanceof Error ? error.message : "Runbooks are unavailable.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const runAttempt = useCallback(async (phase: StartRunPhase, currentAttempt: StartRunBinding | null) => {
    if (selectedDocumentId == null) return;
    setAttemptStatus("starting");
    setAttemptDetail(null);
    const result = await executeStartRunAttempt({
      selectedDocumentId,
      attempt: currentAttempt,
      phase,
      deps: liveStartRunDeps,
    });
    if (result.outcome === "ready") {
      if (startedRef.current === result.binding.runId) return;
      startedRef.current = result.binding.runId;
      setAttempt(result.binding);
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
  }, [onStarted, selectedDocumentId]);

  return (
    <section className="play-start-run" data-testid="play-start-run">
      <h2>Start a Run</h2>
      <p className="play-muted">Choose one active Runbook, then start an exact Run from its current committed revision.</p>
      {listStatus === "loading" ? <p>Loading Runbooks…</p> : null}
      {listStatus === "unavailable" ? (
        <p role="alert" data-testid="play-start-run-unavailable">
          {listDetail ?? "Runbooks are unavailable."}
        </p>
      ) : null}
      {listStatus === "empty" ? (
        <p className="play-muted" data-testid="play-start-run-empty">No active Runbooks are available.</p>
      ) : null}
      {listStatus === "ready" ? (
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
                    setSelectedDocumentId(runbook.document_id);
                    setAttempt(null);
                    setAttemptStatus("idle");
                    setAttemptDetail(null);
                    startedRef.current = null;
                  }}
                >
                  <strong>{runbook.title || runbook.document_id}</strong>
                  <span className="play-muted"> · {runbook.document_id}</span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
      <div className="play-controls">
        <button
          type="button"
          data-testid="play-start-run-submit"
          disabled={selectedDocumentId == null || attemptStatus === "starting"}
          onClick={() => {
            void runAttempt("fresh", null);
          }}
        >
          Start exact Run
        </button>
        {attemptStatus === "replay_create" && attempt ? (
          <button
            type="button"
            data-testid="play-start-run-replay"
            onClick={() => {
              void runAttempt("replay_create", attempt);
            }}
          >
            Retry same UUID
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
      {attemptStatus === "starting" ? <p>Starting exact Run…</p> : null}
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
