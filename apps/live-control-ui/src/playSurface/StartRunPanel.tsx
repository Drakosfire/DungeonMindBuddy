import { useCallback, useEffect, useRef, useState } from "react";

import {
  getWorldOwnedRunbookCommittedRevision,
  getWorldPlayRun,
  getWorldPlayRunReferenceManifest,
  getPlayRun,
  getPlayRunReferenceManifest,
  getCommittedWorkspaceRevision,
  listWorldOwnedRunbooks,
  listWorkspaceDocuments,
  putWorldPlayRun,
  putWorldPlayRunReferenceManifest,
  putPlayRun,
  putPlayRunReferenceManifest,
} from "../api/liveApi";
import type { WorldOwnedRunbookRecordV2, WorkspaceDocumentRecord } from "../api/types";
import {
  executeStartWorldRunAttempt,
  executeStartRunAttempt,
  type StartRunBinding,
  type StartRunDeps,
  type StartRunPhase,
  type WorldStartRunBinding,
  type WorldStartRunDeps,
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
  getRun: getWorldPlayRun,
  putManifest: putWorldPlayRunReferenceManifest,
  getManifest: getWorldPlayRunReferenceManifest,
};

type StartRunbookRecord = WorkspaceDocumentRecord | WorldOwnedRunbookRecordV2;
type StartRunAttemptBinding = StartRunBinding | WorldStartRunBinding;

type ListStatus = "loading" | "ready" | "empty" | "unavailable";
type AttemptStatus = "idle" | "starting" | "incomplete" | "blocked" | "replay_create";

export function StartRunPanel({
  onStarted,
  productCampaignId = null,
  verifiedWorldId = null,
}: {
  onStarted: (runId: string) => void;
  productCampaignId?: string | null;
  verifiedWorldId?: string | null;
}) {
  const [listStatus, setListStatus] = useState<ListStatus>("loading");
  const [listDetail, setListDetail] = useState<string | null>(null);
  const [runbooks, setRunbooks] = useState<StartRunbookRecord[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [attemptStatus, setAttemptStatus] = useState<AttemptStatus>("idle");
  const [attemptDetail, setAttemptDetail] = useState<string | null>(null);
  const [attempt, setAttempt] = useState<StartRunAttemptBinding | null>(null);
  const [campaignDraft, setCampaignDraft] = useState("");
  const [creatingBlank, setCreatingBlank] = useState(false);
  const [createBlankError, setCreateBlankError] = useState<string | null>(null);
  const [listRefreshWarning, setListRefreshWarning] = useState<string | null>(null);
  const [blankAttempt, setBlankAttempt] = useState<BlankRunbookAttempt | null>(null);
  const [worldBlankAttempt, setWorldBlankAttempt] = useState<WorldBlankRunbookAttempt | null>(null);
  const startedRef = useRef<string | null>(null);

  const refreshRunbooks = useCallback(async () => {
    setListStatus("loading");
    setListDetail(null);
    const records = verifiedWorldId
      ? (await listWorldOwnedRunbooks(verifiedWorldId)).records
      : (await listWorkspaceDocuments({ kind: "runbook", status: "active" })).records;
    setRunbooks(records);
    setListStatus(records.length === 0 ? "empty" : "ready");
    return records;
  }, [verifiedWorldId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const records = await refreshRunbooks();
        if (cancelled) return;
        void records;
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
  }, [refreshRunbooks]);

  useEffect(() => {
    setSelectedDocumentId(null);
    setAttempt(null);
    setAttemptStatus("idle");
    setAttemptDetail(null);
    setBlankAttempt(null);
    setWorldBlankAttempt(null);
    startedRef.current = null;
  }, [verifiedWorldId]);

  const runAttempt = useCallback(async (phase: StartRunPhase, currentAttempt: StartRunAttemptBinding | null) => {
    if (selectedDocumentId == null) return;
    const selected = runbooks.find((record) => record.document_id === selectedDocumentId);
    if (verifiedWorldId && (
      selected == null
      || selected.schema_version !== "dmb_world_owned_runbook_record_v2"
      || selected.world_id !== verifiedWorldId
      || selected.campaign_id !== null
    )) {
      setAttemptStatus("blocked");
      setAttemptDetail("Runbook does not belong to the selected World.");
      return;
    }
    if (!verifiedWorldId && selected?.schema_version === "dmb_world_owned_runbook_record_v2") {
      setAttemptStatus("blocked");
      setAttemptDetail("World-owned Runbooks require their selected managed World.");
      return;
    }
    if (verifiedWorldId && currentAttempt != null && !("worldId" in currentAttempt)) {
      setAttemptStatus("blocked");
      setAttemptDetail("This Start Run attempt belongs to Campaign scope, not the selected World.");
      return;
    }
    if (!verifiedWorldId && currentAttempt != null && "worldId" in currentAttempt) {
      setAttemptStatus("blocked");
      setAttemptDetail("This Start Run attempt belongs to another World scope.");
      return;
    }
    setAttemptStatus("starting");
    setAttemptDetail(null);
    const result = verifiedWorldId
      ? await executeStartWorldRunAttempt({
        selectedDocumentId,
        worldId: verifiedWorldId,
        attempt: currentAttempt as WorldStartRunBinding | null,
        phase,
        deps: liveWorldStartRunDeps,
      })
      : await executeStartRunAttempt({
        selectedDocumentId,
        attempt: currentAttempt as StartRunBinding | null,
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
  }, [onStarted, runbooks, selectedDocumentId, verifiedWorldId]);

  const resolvedCampaignId = resolveBlankRunbookCampaignId(productCampaignId, campaignDraft);
  const showCreate = listStatus === "empty" || listStatus === "ready";
  const canCreateBlank = blankAttempt != null
    || worldBlankAttempt != null
    || verifiedWorldId != null
    || resolvedCampaignId != null;
  const selectedRunbook = selectedDocumentId == null
    ? null
    : runbooks.find((record) => record.document_id === selectedDocumentId) ?? null;
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
    if (!canCreateBlank || creatingBlank) return;
    if (verifiedWorldId == null && (blankAttempt?.campaignId ?? resolvedCampaignId) == null) return;
    setCreatingBlank(true);
    setCreateBlankError(null);
    setListRefreshWarning(null);
    try {
      const createdRecord: StartRunbookRecord = verifiedWorldId
        ? (await createBlankWorldRunbook(verifiedWorldId, {
          attempt: worldBlankAttempt,
          onAttemptRetained: setWorldBlankAttempt,
        })).record
        : (await createBlankRunbook(blankAttempt?.campaignId ?? resolvedCampaignId ?? "", {
          attempt: blankAttempt,
          onAttemptRetained: setBlankAttempt,
        })).record;
      setBlankAttempt(null);
      setWorldBlankAttempt(null);
      setSelectedDocumentId(createdRecord.document_id);
      setAttempt(null);
      setAttemptStatus("idle");
      setAttemptDetail(null);
      startedRef.current = null;
      try {
        const records = await refreshRunbooks();
        const selected = records.find((record) => record.document_id === createdRecord.document_id)
          ?? createdRecord;
        setSelectedDocumentId(selected.document_id);
        if (!records.some((record) => record.document_id === createdRecord.document_id)) {
          setRunbooks((current) => (
            current.some((record) => record.document_id === createdRecord.document_id)
              ? current
              : [...current, createdRecord]
          ));
          setListStatus("ready");
        }
      } catch (refreshError) {
        setRunbooks((current) => (
          current.some((record) => record.document_id === createdRecord.document_id)
            ? current
            : [...current, createdRecord]
        ));
        setListStatus("ready");
        setListRefreshWarning(
          refreshError instanceof Error
            ? refreshError.message
            : "Blank Runbook is committed; the Runbook list could not be refreshed.",
        );
      }
    } catch (error) {
      if (error instanceof BlankRunbookCreateError && error.attempt) {
        if ("worldId" in error.attempt) setWorldBlankAttempt(error.attempt);
        else setBlankAttempt(error.attempt);
      }
      setCreateBlankError(
        error instanceof Error ? error.message : "Failed to create a blank Runbook.",
      );
    } finally {
      setCreatingBlank(false);
    }
  }, [blankAttempt, canCreateBlank, creatingBlank, refreshRunbooks, resolvedCampaignId, verifiedWorldId, worldBlankAttempt]);

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
                  <span className="play-muted">
                    {runbook.schema_version === "dmb_world_owned_runbook_record_v2"
                      ? ` · World ${runbook.world_id} · ${runbook.document_id}`
                      : ` · ${runbook.document_id}`}
                  </span>
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
        <div className="play-edit-runbook-control">
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
        </div>
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
