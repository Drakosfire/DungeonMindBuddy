import { useEffect, useRef, useState } from "react";

import {
  LiveApiError,
  getPlayRun,
  getWorldPlayRun,
  putPlayRunProgress,
  putWorldPlayRunProgress,
} from "../../api/liveApi";
import type { AnyPlayRunRecord, PlayRunProgress, WorldPlayRunRecordV2 } from "../../api/types";
import { ReadOnlyBodyContent } from "../../markdownReader/ReadOnlyBodyContent";
import {
  canonicalizePlayRunProgress,
  type NativeRunbookChoiceV2,
  type NativeRunbookReadyV2,
  type NativeRunbookSceneV2,
} from "../runbook/nativeRunbookProjection";
import type { RunbookMutationStatus } from "../runbook/RunbookTableDeck";
import {
  resolveCurrentMoment,
  sceneInCurrentBeat,
  type PlayWorkspace,
} from "./currentMomentModel";
import {
  choiceBranchRelevance,
  operableDecisions,
  planClearSelection,
  planSelectOption,
  selectedOptionForChoice,
} from "./decisionInteractionModel";

export interface PlayCurrentMomentCockpitProps {
  deck: NativeRunbookReadyV2;
  mutationStatus: RunbookMutationStatus;
  onMutationStatus: (status: RunbookMutationStatus) => void;
  onAuthoritativeRun: (run: AnyPlayRunRecord) => void;
}

type SceneNoteFailure = "conflict" | "unknown" | "rejected" | "unconfirmed" | "recovered";

interface SceneNoteDraft {
  scopeKey: string;
  worldId: string;
  runId: string;
  sceneId: string;
  noteElementId: string;
  playableArtifactId: string;
  playableRevision: number;
  playableWorkRevisionId: string;
  playableContentSha256: string;
  text: string;
  basisText: string;
  basisPresent: boolean;
  basisRevision: number;
  state: "editing" | "saving" | "failed";
  sentText?: string;
  sentRevision?: number;
  sentRequestId?: string;
  failure?: SceneNoteFailure;
  recovered?: boolean;
}

interface SceneNoteDraftCacheV1 extends SceneNoteDraft {
  schema_version: "dmb_play_scene_note_draft_v1";
}

interface ProgressReplacementOptions {
  allowExplicitRetry?: boolean;
  onSaved?: (updated: AnyPlayRunRecord, expectedRevision: number) => void;
  onFailure?: (failure: SceneNoteFailure, reloaded: AnyPlayRunRecord | null) => void;
}

function sceneNoteScopeKey(run: WorldPlayRunRecordV2, sceneId: string): string {
  return JSON.stringify([
    "dmb_play_scene_note_draft_v1",
    run.world_id,
    run.run_id,
    sceneId,
    run.playable_artifact_id,
    run.playable_revision,
    run.playable_work_revision_id,
    run.playable_content_sha256,
  ]);
}

function sceneNoteStorageKey(scopeKey: string): string {
  return `dmb.play.scene-note-draft.v1:${encodeURIComponent(scopeKey)}`;
}

function isSceneNoteFailure(value: unknown): value is SceneNoteFailure {
  return value === "conflict" || value === "unknown" || value === "rejected"
    || value === "unconfirmed" || value === "recovered";
}

function readSceneNoteDraftCache(
  scopeKey: string,
  run: WorldPlayRunRecordV2,
  sceneId: string,
): { draft?: SceneNoteDraft; issue?: string } {
  let raw: string | null;
  try {
    raw = window.localStorage.getItem(sceneNoteStorageKey(scopeKey));
  } catch {
    return { issue: "Browser recovery storage is unavailable. This tab's note draft remains editable." };
  }
  if (raw == null) return {};
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    return { issue: "A browser note draft could not be read. This tab's note draft remains editable." };
  }
  if (typeof value !== "object" || value == null) {
    return { issue: "A browser note draft could not be read. This tab's note draft remains editable." };
  }
  const cache = value as Partial<SceneNoteDraftCacheV1>;
  const validState = cache.state === "editing" || cache.state === "saving" || cache.state === "failed";
  const validSent = cache.sentText === undefined && cache.sentRevision === undefined && cache.sentRequestId === undefined
    || typeof cache.sentText === "string" && typeof cache.sentRevision === "number"
      && Number.isFinite(cache.sentRevision) && typeof cache.sentRequestId === "string";
  const exactBinding = cache.schema_version === "dmb_play_scene_note_draft_v1"
    && cache.scopeKey === scopeKey
    && cache.worldId === run.world_id
    && cache.runId === run.run_id
    && cache.sceneId === sceneId
    && cache.noteElementId === sceneId
    && cache.playableArtifactId === run.playable_artifact_id
    && cache.playableRevision === run.playable_revision
    && cache.playableWorkRevisionId === run.playable_work_revision_id
    && cache.playableContentSha256 === run.playable_content_sha256;
  const validDraft = typeof cache.text === "string"
    && typeof cache.basisText === "string"
    && typeof cache.basisPresent === "boolean"
    && typeof cache.basisRevision === "number" && Number.isFinite(cache.basisRevision)
    && validState && validSent
    && (cache.state !== "saving" || typeof cache.sentRequestId === "string")
    && (cache.failure === undefined || isSceneNoteFailure(cache.failure));
  if (!exactBinding || !validDraft) {
    return { issue: "A browser note draft belongs to a different or unreadable Run version and was not restored." };
  }
  return {
    draft: {
      ...(cache as SceneNoteDraftCacheV1),
      state: "failed",
      failure: cache.failure ?? (cache.sentRequestId ? "unknown" : "recovered"),
      recovered: true,
    },
  };
}

function writeSceneNoteDraftCache(draft: SceneNoteDraft): void {
  const cache: SceneNoteDraftCacheV1 = {
    schema_version: "dmb_play_scene_note_draft_v1",
    ...draft,
  };
  window.localStorage.setItem(sceneNoteStorageKey(draft.scopeKey), JSON.stringify(cache));
}

function removeSceneNoteDraftCache(scopeKey: string): void {
  window.localStorage.removeItem(sceneNoteStorageKey(scopeKey));
}

function sameWorldRunBinding(original: AnyPlayRunRecord, candidate: AnyPlayRunRecord): boolean {
  return original.schema_version === "dmb_world_play_run_record_v2"
    && candidate.schema_version === "dmb_world_play_run_record_v2"
    && candidate.world_id === original.world_id
    && candidate.run_id === original.run_id
    && candidate.playable_artifact_id === original.playable_artifact_id
    && candidate.playable_revision === original.playable_revision
    && candidate.playable_work_revision_id === original.playable_work_revision_id
    && candidate.playable_content_sha256 === original.playable_content_sha256;
}

function isExactSceneNoteAcknowledgement(
  original: AnyPlayRunRecord,
  updated: AnyPlayRunRecord,
  sceneId: string,
  submittedText: string,
  expectedRevision: number,
): boolean {
  return sameWorldRunBinding(original, updated)
    && updated.run_revision > expectedRevision
    && updated.progress.notes_by_element_id[sceneId] === submittedText;
}

function relevanceLabel(relevance: NativeRunbookSceneV2["relevance"]): string | null {
  if (relevance === "emphasized") return "emphasized";
  if (relevance === "de-emphasized") return "de-emphasized";
  return null;
}

function DecisionBlock({
  deck,
  decisions,
  saving,
  mutationsOpen,
  onSelect,
  onClear,
}: {
  deck: NativeRunbookReadyV2;
  decisions: NativeRunbookChoiceV2[];
  saving: boolean;
  mutationsOpen: boolean;
  onSelect: (choice: NativeRunbookChoiceV2, optionId: string) => void;
  onClear: (choice: NativeRunbookChoiceV2) => void;
}) {
  if (decisions.length === 0) return null;
  const selections = deck.run.progress.selections;
  const locked = saving || !mutationsOpen;
  return (
    <div className="play-decisions" data-testid="play-decisions">
      {decisions.map((choice) => {
        const selected = selectedOptionForChoice(choice, selections);
        const branch = selected == null ? [] : choiceBranchRelevance(deck, choice);
        const groupId = `play-decision-${choice.id}`;
        return (
          <section
            key={choice.id}
            className={`play-decision${selected ? " is-resolved" : ""}`}
            data-testid="play-decision"
            data-choice-id={choice.id}
          >
            <header className="play-decision-header">
              <p className="play-decision-kicker">Decision</p>
              <h3 id={groupId} data-testid="play-decision-prompt">
                {choice.title}
              </h3>
              <ReadOnlyBodyContent
                content={choice.bodyContent}
                fallbackText={choice.bodyText}
                className="play-body play-decision-framing"
              />
            </header>
            <div className="play-decision-options" role="radiogroup" aria-labelledby={groupId}>
              {choice.options.map((option) => {
                const isSelected = selected?.id === option.id;
                return (
                  <button
                    key={option.id}
                    type="button"
                    role="radio"
                    className={`play-decision-option${isSelected ? " is-selected" : ""}`}
                    name={groupId}
                    value={option.id}
                    aria-checked={isSelected}
                    disabled={locked}
                    onClick={() => onSelect(choice, option.id)}
                  >
                    {option.title}
                  </button>
                );
              })}
            </div>
            {selected ? (
              <div className="play-decision-result">
                <ReadOnlyBodyContent
                  content={selected.bodyContent}
                  fallbackText={selected.bodyText}
                  className="play-body play-decision-consequence"
                  testId="play-decision-consequence"
                />
                {branch.length > 0 ? (
                  <ul className="play-decision-relevance" data-testid="play-decision-relevance">
                    {branch.map((row) => (
                      <li key={row.targetId} data-target-id={row.targetId} data-relevance={row.relevance}>
                        {row.title} — {row.relevance}
                      </li>
                    ))}
                  </ul>
                ) : null}
                {mutationsOpen ? (
                  <button
                    type="button"
                    className="play-decision-clear"
                    data-testid="play-decision-clear"
                    disabled={saving}
                    aria-label={`Clear selection for ${choice.title}`}
                    onClick={() => onClear(choice)}
                  >
                    Clear
                  </button>
                ) : null}
              </div>
            ) : null}
          </section>
        );
      })}
    </div>
  );
}

export function PlayCurrentMomentCockpit({
  deck,
  mutationStatus,
  onMutationStatus,
  onAuthoritativeRun,
}: PlayCurrentMomentCockpitProps) {
  const run = deck.run;
  const runIdentity = run.schema_version === "dmb_world_play_run_record_v2"
    ? JSON.stringify([
      run.schema_version,
      run.world_id,
      run.run_id,
      run.playable_artifact_id,
      run.playable_revision,
      run.playable_work_revision_id,
      run.playable_content_sha256,
    ])
    : JSON.stringify([run.schema_version, run.run_id]);
  const mutationsOpen = mutationStatus === "idle" || mutationStatus === "saving";
  const [workspace, setWorkspace] = useState<PlayWorkspace>({ kind: "current" });
  const [beatCollapsed, setBeatCollapsed] = useState(false);
  const [glanceCollapsed, setGlanceCollapsed] = useState(false);
  const [progressRejection, setProgressRejection] = useState<string | null>(null);
  const [exactRereadSucceeded, setExactRereadSucceeded] = useState(false);
  const [sceneNoteDrafts, setSceneNoteDrafts] = useState<Record<string, SceneNoteDraft>>({});
  const [sceneNoteStorageWarnings, setSceneNoteStorageWarnings] = useState<Record<string, string>>({});
  const mountedRef = useRef(true);
  const liveRunIdRef = useRef(run.run_id);
  const liveRunIdentityRef = useRef(runIdentity);
  const requestSerialRef = useRef(0);
  const scenesLauncherRef = useRef<HTMLButtonElement | null>(null);
  const glanceToggleRef = useRef<HTMLButtonElement | null>(null);
  const inFlightRef = useRef(false);
  const saveSceneNoteRef = useRef<(scope: string) => void>(() => undefined);
  const sceneNoteDraftsRef = useRef(sceneNoteDrafts);
  const sceneNoteRequestCounterRef = useRef(0);
  sceneNoteDraftsRef.current = sceneNoteDrafts;

  useEffect(() => {
    mountedRef.current = true;
    liveRunIdRef.current = run.run_id;
    liveRunIdentityRef.current = runIdentity;
    setWorkspace({ kind: "current" });
    setBeatCollapsed(false);
    setGlanceCollapsed(false);
    setProgressRejection(null);
    setExactRereadSucceeded(false);
    inFlightRef.current = false;
    return () => {
      mountedRef.current = false;
      requestSerialRef.current += 1;
    };
  }, [runIdentity]);

  const moment = resolveCurrentMoment(deck);
  const currentBeat = moment.status === "ok" ? moment.beat : null;
  const currentScene = moment.status === "ok" ? moment.scene : null;
  const inspectedScene = workspace.kind === "scene-inspect"
    ? sceneInCurrentBeat(deck, workspace.sceneId)
    : null;
  const worldOwnedRun = run.schema_version === "dmb_world_play_run_record_v2";
  const sceneNoteId = worldOwnedRun ? currentScene?.id ?? null : null;
  const sceneNoteScope = sceneNoteId && worldOwnedRun
    ? sceneNoteScopeKey(run, sceneNoteId)
    : null;
  const activeSceneNoteDraft = sceneNoteScope ? sceneNoteDrafts[sceneNoteScope] : undefined;
  const activeSceneNoteStorageWarning = sceneNoteScope ? sceneNoteStorageWarnings[sceneNoteScope] : undefined;
  const serverSceneNote = sceneNoteId ? run.progress.notes_by_element_id[sceneNoteId] ?? "" : "";
  const sceneNoteValue = activeSceneNoteDraft?.text ?? serverSceneNote;
  const sceneNoteSaved = sceneNoteId != null
    && Object.prototype.hasOwnProperty.call(run.progress.notes_by_element_id, sceneNoteId);
  const sceneNoteChangedOnServer = activeSceneNoteDraft != null
    && (activeSceneNoteDraft.basisPresent !== sceneNoteSaved
      || activeSceneNoteDraft.basisText !== serverSceneNote);

  const replaceProgress = async (next: PlayRunProgress, options?: ProgressReplacementOptions) => {
    const explicitRetryIsCurrent = options?.allowExplicitRetry === true
      && (mutationStatus === "idle" || exactRereadSucceeded);
    if ((!mutationsOpen && !explicitRetryIsCurrent) || mutationStatus === "saving" || inFlightRef.current) return;
    const boundRunId = run.run_id;
    const boundRunIdentity = runIdentity;
    const expected = run.run_revision;
    const serial = requestSerialRef.current + 1;
    requestSerialRef.current = serial;
    inFlightRef.current = true;
    setProgressRejection(null);
    setExactRereadSucceeded(false);
    onMutationStatus("saving");
    try {
      const request = {
        expected_run_revision: expected,
        progress: canonicalizePlayRunProgress(next),
      };
      const updated = run.schema_version === "dmb_world_play_run_record_v2"
        ? await putWorldPlayRunProgress(boundRunId, run.world_id, request)
        : await putPlayRunProgress(boundRunId, request);
      if (!mountedRef.current || liveRunIdRef.current !== boundRunId
        || liveRunIdentityRef.current !== boundRunIdentity || requestSerialRef.current !== serial) {
        return;
      }
      options?.onSaved?.(updated, expected);
      onAuthoritativeRun(updated);
      onMutationStatus("idle");
      setWorkspace({ kind: "current" });
    } catch (error) {
      if (!mountedRef.current || liveRunIdRef.current !== boundRunId
        || liveRunIdentityRef.current !== boundRunIdentity || requestSerialRef.current !== serial) {
        return;
      }
      const status = error instanceof LiveApiError ? error.status : 0;
      let reconciled: AnyPlayRunRecord | null = null;
      try {
        reconciled = run.schema_version === "dmb_world_play_run_record_v2"
          ? await getWorldPlayRun(boundRunId, run.world_id)
          : await getPlayRun(boundRunId);
      } catch {
        reconciled = null;
      }
      if (!mountedRef.current || liveRunIdRef.current !== boundRunId
        || liveRunIdentityRef.current !== boundRunIdentity || requestSerialRef.current !== serial) {
        return;
      }
      if (reconciled) onAuthoritativeRun(reconciled);
      setExactRereadSucceeded(reconciled != null);
      if (status === 409) {
        onMutationStatus(reconciled ? "conflict" : "unknown");
        options?.onFailure?.(reconciled ? "conflict" : "unknown", reconciled);
        return;
      }
      if (status === 422) {
        if (reconciled) {
          onMutationStatus("idle");
          setProgressRejection(
            "The Run rejected that change. Reloaded the exact Run. The write was not retried or treated as a conflict.",
          );
          options?.onFailure?.("rejected", reconciled);
        } else {
          onMutationStatus("unknown");
          options?.onFailure?.("unknown", null);
        }
        return;
      }
      onMutationStatus("unknown");
      options?.onFailure?.("unknown", reconciled);
    } finally {
      if (requestSerialRef.current === serial) {
        inFlightRef.current = false;
      }
    }
  };

  const updateSceneNoteDraft = (
    scope: string,
    update: (current: SceneNoteDraft | undefined) => SceneNoteDraft | null,
  ) => {
    const current = sceneNoteDraftsRef.current;
    const next = update(current[scope]);
    let updated: Record<string, SceneNoteDraft>;
    if (next == null) {
      if (!Object.prototype.hasOwnProperty.call(current, scope)) {
        updated = current;
      } else {
        updated = { ...current };
        delete updated[scope];
      }
    } else {
      updated = { ...current, [scope]: next };
    }
    sceneNoteDraftsRef.current = updated;
    setSceneNoteDrafts(updated);
    try {
      if (next == null) removeSceneNoteDraftCache(scope);
      else writeSceneNoteDraftCache(next);
      setSceneNoteStorageWarnings((warnings) => {
        if (!Object.prototype.hasOwnProperty.call(warnings, scope)) return warnings;
        const copy = { ...warnings };
        delete copy[scope];
        return copy;
      });
    } catch {
      setSceneNoteStorageWarnings((warnings) => ({
        ...warnings,
        [scope]: "Browser recovery storage is unavailable. This tab's note draft remains editable.",
      }));
    }
  };

  useEffect(() => {
    if (!sceneNoteScope || !sceneNoteId || run.schema_version !== "dmb_world_play_run_record_v2") return;
    const result = readSceneNoteDraftCache(sceneNoteScope, run, sceneNoteId);
    if (result.issue) {
      setSceneNoteStorageWarnings((warnings) => ({ ...warnings, [sceneNoteScope]: result.issue! }));
      return;
    }
    if (result.draft) {
      updateSceneNoteDraft(sceneNoteScope, (current) => current ?? result.draft!);
    }
  }, [sceneNoteScope]);

  const saveSceneNote = (scope: string, allowExplicitRetry = false) => {
    if (run.schema_version !== "dmb_world_play_run_record_v2" || !sceneNoteId || scope !== sceneNoteScope) return;
    const draft = sceneNoteDrafts[scope];
    if (!draft || draft.state === "saving" || (draft.state === "failed" && !allowExplicitRetry)) return;
    const submittedText = draft.text;
    const expectedRevision = run.run_revision;
    const sentRequestId = `${Date.now()}:${sceneNoteRequestCounterRef.current + 1}`;
    sceneNoteRequestCounterRef.current += 1;
    updateSceneNoteDraft(scope, (current) => current ? {
      ...current,
      state: "saving",
      sentText: submittedText,
      sentRevision: expectedRevision,
      sentRequestId,
      failure: undefined,
    } : null);
    void replaceProgress({
      ...run.progress,
      notes_by_element_id: {
        ...run.progress.notes_by_element_id,
        [sceneNoteId]: submittedText,
      },
    }, {
      allowExplicitRetry,
      onSaved: (updated, sentRevision) => {
        if (!isExactSceneNoteAcknowledgement(run, updated, sceneNoteId, submittedText, sentRevision)) {
          updateSceneNoteDraft(scope, (current) => current ? {
            ...current,
            state: "failed",
            sentText: submittedText,
            sentRevision,
            failure: "unconfirmed",
          } : null);
          return;
        }
        updateSceneNoteDraft(scope, (current) => {
          if (!current) return null;
          const exactSentDraft = current.sentText === submittedText
            && current.sentRevision === sentRevision;
          if (exactSentDraft && current.text === submittedText) return null;
          return {
            ...current,
            basisText: submittedText,
            basisPresent: true,
            basisRevision: updated.run_revision,
            state: "editing",
            sentText: undefined,
            sentRevision: undefined,
            sentRequestId: undefined,
            failure: undefined,
          };
        });
      },
      onFailure: (failure, reloaded) => {
        updateSceneNoteDraft(scope, (current) => {
          if (!current) return null;
          const exactReload = reloaded != null && sameWorldRunBinding(run, reloaded);
          const reloadedHasNote = exactReload
            && Object.prototype.hasOwnProperty.call(reloaded.progress.notes_by_element_id, sceneNoteId);
          return {
            ...current,
            basisText: exactReload ? reloaded.progress.notes_by_element_id[sceneNoteId] ?? "" : current.basisText,
            basisPresent: exactReload ? reloadedHasNote : current.basisPresent,
            basisRevision: exactReload ? reloaded.run_revision : current.basisRevision,
            state: "failed",
            sentText: submittedText,
            sentRevision: expectedRevision,
            sentRequestId,
            failure,
          };
        });
      },
    });
  };

  const changeSceneNote = (text: string) => {
    if (!worldOwnedRun || !sceneNoteId || !sceneNoteScope) return;
    updateSceneNoteDraft(sceneNoteScope, (current) => {
      const draft = current ?? {
        scopeKey: sceneNoteScope,
        worldId: run.world_id,
        runId: run.run_id,
        sceneId: sceneNoteId,
        noteElementId: sceneNoteId,
        playableArtifactId: run.playable_artifact_id,
        playableRevision: run.playable_revision,
        playableWorkRevisionId: run.playable_work_revision_id,
        playableContentSha256: run.playable_content_sha256,
        text: serverSceneNote,
        basisText: serverSceneNote,
        basisPresent: sceneNoteSaved,
        basisRevision: run.run_revision,
        state: "editing" as const,
      };
      return {
        ...draft,
        text,
        state: draft.state === "failed" ? "failed" : "editing",
      };
    });
  };

  saveSceneNoteRef.current = (scope) => saveSceneNote(scope);

  useEffect(() => {
    if (!sceneNoteScope || activeSceneNoteDraft?.state !== "editing"
      || sceneNoteChangedOnServer || mutationStatus !== "idle") return;
    const scope = sceneNoteScope;
    const timer = window.setTimeout(() => saveSceneNoteRef.current(scope), 450);
    return () => window.clearTimeout(timer);
  }, [sceneNoteScope, activeSceneNoteDraft?.state, activeSceneNoteDraft?.text,
    sceneNoteChangedOnServer, mutationStatus, run.run_revision]);

  const makeSceneCurrent = (scene: NativeRunbookSceneV2) => {
    if (scene.beatId !== deck.currentBeatId) return;
    void replaceProgress({
      ...run.progress,
      current_beat_id: scene.beatId,
      current_scene_id: scene.id,
    });
  };

  const selectOption = (choice: NativeRunbookChoiceV2, optionId: string) => {
    const planned = planSelectOption(run.progress.selections, choice, optionId);
    if (planned.kind !== "write") return;
    void replaceProgress({
      ...run.progress,
      selections: planned.selections,
    });
  };

  const clearSelection = (choice: NativeRunbookChoiceV2) => {
    const planned = planClearSelection(run.progress.selections, choice);
    if (planned.kind !== "write") return;
    void replaceProgress({
      ...run.progress,
      selections: planned.selections,
    });
  };

  const restoreWorkspaceFocus = () => {
    queueMicrotask(() => {
      const scenes = scenesLauncherRef.current;
      if (scenes?.isConnected) {
        scenes.focus();
        return;
      }
      glanceToggleRef.current?.focus();
    });
  };

  const closeToCurrent = () => {
    setWorkspace({ kind: "current" });
    restoreWorkspaceFocus();
  };

  const openInspect = (scene: NativeRunbookSceneV2) => {
    setWorkspace({ kind: "scene-inspect", sceneId: scene.id });
  };

  const sceneCount = currentBeat?.scenes.length ?? 0;
  const saving = mutationStatus === "saving";
  const workspaceKind = workspace.kind === "scene-inspect" && inspectedScene == null
    ? "current"
    : workspace.kind;
  const decisions = currentBeat
    ? operableDecisions(currentBeat, currentScene?.id ?? null)
    : [];

  return (
    <section
      className="play-cockpit"
      data-testid="play-current-moment-cockpit"
      data-play-run-id={run.run_id}
      data-current-beat-id={deck.currentBeatId}
      data-current-scene-id={deck.currentSceneId ?? ""}
      aria-label="Current moment"
    >
      {moment.status === "incoherent" ? (
        <p role="alert" className="play-banner" data-testid="play-current-moment-incoherent">
          {moment.reason}
        </p>
      ) : null}

      {mutationStatus === "conflict" ? (
        <p className="play-banner" role="alert" data-testid="play-cas-conflict">
          Another writer updated this Run. Reloaded the exact Run. Progress was not retried or merged.
        </p>
      ) : null}
      {mutationStatus === "unknown" ? (
        <p className="play-banner" role="alert" data-testid="play-unknown-outcome">
          {exactRereadSucceeded
            ? "The progress write did not return a known result. Reloaded the exact Run before further mutation."
            : "The progress write did not return a known result. The exact Run could not be reloaded."}
        </p>
      ) : null}
      {progressRejection ? (
        <p className="play-banner" role="alert" data-testid="play-progress-rejected">
          {progressRejection}
        </p>
      ) : null}
      {saving ? (
        <p className="play-muted" role="status" data-testid="play-saving">
          Saving…
        </p>
      ) : null}

      {currentBeat ? (
        <div className="play-cockpit-orientation" data-testid="play-current-orientation">
          <p data-testid="play-current-beat">Current Beat: {currentBeat.title}</p>
          <p data-testid="play-current-scene">
            {currentScene ? `Current Scene: ${currentScene.title}` : "No Scene is current"}
          </p>
        </div>
      ) : null}

      <div
        className="play-cockpit-shell"
        data-testid="play-cockpit-shell"
        data-beat-collapsed={beatCollapsed ? "true" : "false"}
        data-glance-collapsed={glanceCollapsed ? "true" : "false"}
      >
        <aside
          className={`play-cockpit-rail play-beat-context${beatCollapsed ? " is-collapsed" : ""}`}
          data-testid="play-beat-context"
        >
          <button
            type="button"
            className="play-rail-toggle"
            data-testid="play-beat-context-toggle"
            aria-expanded={!beatCollapsed}
            aria-controls="play-beat-context-body"
            aria-label={
              currentBeat
                ? `${beatCollapsed ? "Expand" : "Collapse"} Beat Context: ${currentBeat.title}`
                : undefined
            }
            onClick={() => setBeatCollapsed((current) => !current)}
          >
            Beat Context
            {!beatCollapsed && currentBeat ? `: ${currentBeat.title}` : ""}
          </button>
          {beatCollapsed ? null : (
            <div id="play-beat-context-body" className="play-rail-body">
              {currentBeat ? (
                <>
                  <h2 data-testid="play-beat-context-title">{currentBeat.title}</h2>
                  {currentBeat.beatKind ? (
                    <p className="play-muted">{currentBeat.beatKind}</p>
                  ) : null}
                  {run.progress.resolved_beat_ids.includes(currentBeat.id) ? (
                    <p className="play-muted">resolved</p>
                  ) : null}
                  <ReadOnlyBodyContent
                    content={currentBeat.bodyContent}
                    fallbackText={currentBeat.bodyText}
                    className="play-body"
                  />
                </>
              ) : (
                <p className="play-muted">Current Beat is unavailable.</p>
              )}
            </div>
          )}
        </aside>

        <div
          className="play-cockpit-center"
          data-testid="play-central-workspace"
          data-workspace={workspaceKind}
        >
          {workspaceKind === "current" && currentBeat && currentScene ? (
            <article
              className="play-scene-board"
              data-testid="play-workspace-current"
              aria-labelledby="play-workspace-heading"
            >
              <p className="play-kicker">Current Scene</p>
              <h2 id="play-workspace-heading">{currentScene.title}</h2>
              <ReadOnlyBodyContent
                content={currentScene.bodyContent}
                fallbackText={currentScene.bodyText}
                className="play-body play-scene-board-body"
              />
              <DecisionBlock
                deck={deck}
                decisions={decisions}
                saving={saving}
                mutationsOpen={mutationsOpen}
                onSelect={selectOption}
                onClear={clearSelection}
              />
              {worldOwnedRun && sceneNoteScope && sceneNoteId ? (
                <section className="play-notes" data-testid="play-scene-note">
                  <label htmlFor={`play-scene-note-${run.run_id}-${sceneNoteId}`}>Scene note</label>
                  <textarea
                    id={`play-scene-note-${run.run_id}-${sceneNoteId}`}
                    value={sceneNoteValue}
                    aria-describedby="play-scene-note-status"
                    onChange={(event) => changeSceneNote(event.target.value)}
                  />
                  <p
                    className="play-muted"
                    role="status"
                    aria-live="polite"
                    data-testid="play-scene-note-status"
                  >
                    {activeSceneNoteDraft?.state === "saving"
                      ? "Saving note to this Run…"
                      : sceneNoteChangedOnServer || activeSceneNoteDraft?.failure === "conflict"
                        ? "Not saved. Another update changed this Run; your draft is kept. Review before retrying."
                        : activeSceneNoteDraft?.failure === "unknown"
                          ? "Not saved. The previous save result is unknown; your draft is kept and was not resent."
                          : activeSceneNoteDraft?.failure === "rejected"
                            ? "Not saved. The Run rejected this note; your draft is kept. Retry is manual."
                            : activeSceneNoteDraft?.failure === "unconfirmed"
                              ? "Not saved. The Run did not confirm this note; your draft is kept. Retry is manual."
                              : activeSceneNoteDraft?.recovered
                                ? "Recovered browser draft; unsaved in this Run. Save it when ready."
                                : activeSceneNoteDraft
                                  ? "Unsaved draft; autosave starts after a pause."
                                  : sceneNoteSaved
                                    ? "Saved in this Run."
                                    : "No saved note."}
                  </p>
                  {activeSceneNoteDraft ? (
                    <button
                      type="button"
                      disabled={saving || (mutationStatus !== "idle" && !exactRereadSucceeded)}
                      onClick={() => saveSceneNote(sceneNoteScope, true)}
                    >
                      {activeSceneNoteDraft.state === "saving"
                        ? "Saving note…"
                        : sceneNoteChangedOnServer
                          ? "Save note after review"
                          : activeSceneNoteDraft.state === "failed"
                          ? activeSceneNoteDraft.recovered && activeSceneNoteDraft.failure === "recovered"
                            ? "Save recovered note"
                            : "Retry note save"
                            : "Save note now"}
                    </button>
                  ) : null}
                  {activeSceneNoteStorageWarning ? (
                    <p
                      className="play-banner"
                      role="alert"
                      data-testid="play-scene-note-storage-warning"
                    >
                      {activeSceneNoteStorageWarning}
                    </p>
                  ) : null}
                </section>
              ) : null}
            </article>
          ) : null}

          {workspaceKind === "current" && currentBeat && currentScene == null ? (
            <article data-testid="play-workspace-beat-only" aria-labelledby="play-workspace-heading">
              <p className="play-kicker">Current Beat</p>
              <h2 id="play-workspace-heading">{currentBeat.title}</h2>
              <ReadOnlyBodyContent
                content={currentBeat.bodyContent}
                fallbackText={currentBeat.bodyText}
                className="play-body"
              />
              <h3>Scenes in this Beat</h3>
              {currentBeat.scenes.length === 0 ? (
                <p className="play-muted" data-testid="play-scenes-empty">
                  No authored Scenes in this Beat.
                </p>
              ) : (
                <ul className="play-scene-actions">
                  {currentBeat.scenes.map((scene) => (
                    <li key={scene.id}>
                      <span>{scene.title}</span>
                      {mutationsOpen ? (
                        <button
                          type="button"
                          disabled={saving}
                          aria-label={`Make ${scene.title} current`}
                          onClick={() => makeSceneCurrent(scene)}
                        >
                          Make Current
                        </button>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
              <DecisionBlock
                deck={deck}
                decisions={decisions}
                saving={saving}
                mutationsOpen={mutationsOpen}
                onSelect={selectOption}
                onClear={clearSelection}
              />
            </article>
          ) : null}

          {workspaceKind === "scenes" && currentBeat ? (
            <article data-testid="play-workspace-scenes" aria-labelledby="play-workspace-heading">
              <p className="play-kicker">Scenes</p>
              <h2 id="play-workspace-heading">Scenes</h2>
              <button type="button" data-testid="play-workspace-back" onClick={closeToCurrent}>
                Back
              </button>
              {currentBeat.scenes.length === 0 ? (
                <p className="play-muted" data-testid="play-scenes-empty">
                  No authored Scenes in this Beat.
                </p>
              ) : (
                <ul className="play-scene-inventory" data-testid="play-scene-inventory">
                  {currentBeat.scenes.map((scene) => {
                    const isCurrent = currentScene?.id === scene.id;
                    const extra = relevanceLabel(scene.relevance);
                    return (
                      <li
                        key={scene.id}
                        data-scene-id={scene.id}
                        data-current={isCurrent ? "true" : "false"}
                        aria-current={isCurrent ? "true" : undefined}
                      >
                        <span>
                          {scene.title}
                          {isCurrent ? " · current" : " · not current"}
                          {extra ? ` · ${extra}` : ""}
                        </span>
                        <button
                          type="button"
                          aria-label={`Inspect ${scene.title}`}
                          onClick={() => openInspect(scene)}
                        >
                          Inspect
                        </button>
                        {mutationsOpen && !isCurrent ? (
                          <button
                            type="button"
                            disabled={saving}
                            aria-label={`Make ${scene.title} current`}
                            onClick={() => makeSceneCurrent(scene)}
                          >
                            Make Current
                          </button>
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              )}
            </article>
          ) : null}

          {workspaceKind === "scene-inspect" && inspectedScene && currentBeat ? (
            <article
              data-testid="play-workspace-inspect"
              data-inspecting-current={inspectedScene.id === currentScene?.id ? "true" : "false"}
              aria-labelledby="play-workspace-heading"
            >
              <p className="play-kicker">
                {inspectedScene.id === currentScene?.id ? "Current Scene" : "Inspecting Scene"}
              </p>
              <h2 id="play-workspace-heading">
                {inspectedScene.id === currentScene?.id
                  ? inspectedScene.title
                  : `Inspecting ${inspectedScene.title}`}
              </h2>
              <p data-testid="play-inspect-current">
                Current: {currentScene ? currentScene.title : currentBeat.title}
              </p>
              <p data-testid="play-inspect-scene">Inspecting: {inspectedScene.title}</p>
              <div className="play-controls">
                <button type="button" data-testid="play-workspace-back" onClick={closeToCurrent}>
                  Back
                </button>
                {mutationsOpen && inspectedScene.id !== currentScene?.id ? (
                  <button
                    type="button"
                    data-testid="play-make-current"
                    disabled={saving}
                    aria-label={`Make ${inspectedScene.title} current`}
                    onClick={() => makeSceneCurrent(inspectedScene)}
                  >
                    Make Current
                  </button>
                ) : null}
              </div>
              <ReadOnlyBodyContent
                content={inspectedScene.bodyContent}
                fallbackText={inspectedScene.bodyText}
                className="play-body"
              />
            </article>
          ) : null}
        </div>

        <aside
          className={`play-cockpit-rail play-at-a-glance${glanceCollapsed ? " is-collapsed" : ""}`}
          data-testid="play-at-a-glance"
        >
          <button
            type="button"
            className="play-rail-toggle"
            data-testid="play-at-a-glance-toggle"
            ref={glanceToggleRef}
            aria-expanded={!glanceCollapsed}
            aria-controls="play-at-a-glance-body"
            onClick={() => setGlanceCollapsed((current) => !current)}
          >
            At a Glance
          </button>
          {glanceCollapsed ? null : (
            <div id="play-at-a-glance-body" className="play-rail-body">
              <p className="play-glance-caption">Around this moment</p>
              <button
                type="button"
                className="play-glance-category"
                data-testid="play-at-a-glance-scenes"
                ref={scenesLauncherRef}
                aria-pressed={workspaceKind === "scenes"}
                onClick={() => setWorkspace({ kind: "scenes" })}
              >
                Scenes {sceneCount}
              </button>
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}
