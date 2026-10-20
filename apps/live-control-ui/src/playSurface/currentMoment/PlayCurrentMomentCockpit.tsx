import { ContentsToggle } from "../../shared/Contents";
import { CardSceneNavigation } from "../../shared/CardSceneNavigation";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import {
  LiveApiError,
  getPlayRun,
  getWorldPlayRun,
  putPlayRunProgress,
  putWorldPlayRunProgress,
} from "../../api/liveApi";
import type { AnyPlayRunRecord, PlayRunProgress, WorldPlayRunRecordV2 } from "../../api/types";
import { ReadOnlyBodyContent } from "../../markdownReader/ReadOnlyBodyContent";
import { FloatingSceneNotes } from "./FloatingSceneNotes";
import { SceneCard, type SceneCardChoice, type SceneCardChoiceActions, type SceneCardIdentity } from "../../shared/SceneCard";
import {
  canonicalizePlayRunProgress,
  type NativeRunbookBeatV2,
  type NativeRunbookChoiceV2,
  type NativeRunbookReadyV2,
  type NativeRunbookSceneV2,
} from "../runbook/nativeRunbookProjection";
import type { RunbookMutationStatus } from "../runbook/RunbookTableDeck";
import {
  resolveCurrentMoment,
  type PlayWorkspace,
} from "./currentMomentModel";
import { beatForScene, PlayRecordedOutcomes, PlaySceneOutline, sceneInAnyBeat } from "./PlayCockpitPanels";
import {
  choiceBranchRelevance,
  operableDecisions,
  planClearSelection,
  planSelectOption,
  selectedOptionForChoice,
} from "./decisionInteractionModel";
import { SurfaceContextAction, SurfaceContextPopover, SurfaceContextSelect } from "../../surfaceInteraction/contextHost";
import { PlaySurfaceContext, playSurfaceContextIdentity } from "../components/PlaySurfaceContext";

export interface PlayCurrentMomentCockpitProps {
  deck: NativeRunbookReadyV2;
  mutationStatus: RunbookMutationStatus;
  onMutationStatus: (status: RunbookMutationStatus) => void;
  onAuthoritativeRun: (run: AnyPlayRunRecord) => void;
  onNoteUnsubmittedChange?: (hasUnsubmitted: boolean) => void;
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

function narrowPlayViewport(): boolean {
  return typeof window !== "undefined"
    && typeof window.matchMedia === "function"
    && window.matchMedia("(max-width: 60rem)").matches;
}

function playSceneCardChoices(decisions: readonly NativeRunbookChoiceV2[], selections: Readonly<Record<string, string>>): SceneCardChoice[] {
  return decisions.map((choice) => ({
    id: choice.id,
    title: choice.title,
    bodyText: choice.bodyText,
    bodyContent: choice.bodyContent,
    associatedSceneId: choice.sceneId,
    selectedOptionId: selections[choice.id] ?? null,
    options: choice.options.map((option) => ({
      id: option.id,
      title: option.title,
      bodyText: option.bodyText,
      bodyContent: option.bodyContent,
    })),
  }));
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

function BeatContext({
  beat,
  resolved,
  relation,
}: {
  beat: NativeRunbookBeatV2;
  resolved: boolean;
  relation: "Current Beat" | "Viewing Beat";
}) {
  return (
    <details
      className="play-beat-context"
      data-testid="play-beat-context-disclosure"
      data-beat-id={beat.id}
      data-beat-resolved={resolved ? "true" : "false"}
    >
      <summary>
        <span>{relation}</span>
        <strong>{beat.title}</strong>
        <span className="play-beat-context-state">
          {beat.beatKind ? `${beat.beatKind} · ` : ""}{resolved ? "Resolved" : "Not marked resolved"}
        </span>
      </summary>
      <ReadOnlyBodyContent
        content={beat.bodyContent}
        fallbackText={beat.bodyText}
        className="play-body play-beat-context-body"
      />
    </details>
  );
}

export function PlayCurrentMomentCockpit({
  deck,
  mutationStatus,
  onMutationStatus,
  onAuthoritativeRun,
  onNoteUnsubmittedChange,
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
  const [beatCollapsed, setBeatCollapsed] = useState(narrowPlayViewport);
  const [glanceCollapsed, setGlanceCollapsed] = useState(true);
  const [moreOpen, setMoreOpen] = useState(false);
  const [notesOpen, setNotesOpen] = useState(false);
  const [progressRejection, setProgressRejection] = useState<string | null>(null);
  const [exactRereadSucceeded, setExactRereadSucceeded] = useState(false);
  const [hydratedNoteScope, setHydratedNoteScope] = useState<string | null>(null);
  const [sceneNoteDrafts, setSceneNoteDrafts] = useState<Record<string, SceneNoteDraft>>({});
  const [sceneNoteStorageWarnings, setSceneNoteStorageWarnings] = useState<Record<string, string>>({});
  const cockpitRef = useRef<HTMLElement | null>(null);
  const compactLayoutRef = useRef(narrowPlayViewport());
  const mountedRef = useRef(true);
  const liveRunIdRef = useRef(run.run_id);
  const liveRunIdentityRef = useRef(runIdentity);
  const requestSerialRef = useRef(0);
  const outlineToggleRef = useRef<HTMLButtonElement | null>(null);
  const inFlightRef = useRef(false);
  const saveSceneNoteRef = useRef<(scope: string) => void>(() => undefined);
  const sceneNoteDraftsRef = useRef(sceneNoteDrafts);
  const sceneNoteRequestCounterRef = useRef(0);
  const compactOutlineToggleRef = useRef<HTMLButtonElement | null>(null);
  const compactOutcomesToggleRef = useRef<HTMLButtonElement | null>(null);
  const notesNavbarToggleRef = useRef<HTMLButtonElement | null>(null);
  const scenesNavbarToggleRef = useRef<HTMLButtonElement | null>(null);
  const moreNavbarToggleRef = useRef<HTMLButtonElement | null>(null);
  const compactPanelFocusRef = useRef<"scenes" | "outcomes">("scenes");
  const workspaceHeadingRef = useRef<HTMLHeadingElement | null>(null);
  const returnInspectionToMoreRef = useRef(false);
  sceneNoteDraftsRef.current = sceneNoteDrafts;

  useEffect(() => {
    mountedRef.current = true;
    liveRunIdRef.current = run.run_id;
    liveRunIdentityRef.current = runIdentity;
    setWorkspace({ kind: "current" });
    setNotesOpen(false);
    setMoreOpen(false);
    const compactPanels = compactLayoutRef.current;
    setBeatCollapsed(compactPanels);
    setGlanceCollapsed(true);
    setProgressRejection(null);
    setExactRereadSucceeded(false);
    inFlightRef.current = false;
    return () => {
      mountedRef.current = false;
      requestSerialRef.current += 1;
    };
  }, [runIdentity]);

  useEffect(() => {
    const cockpit = cockpitRef.current;
    if (cockpit && typeof ResizeObserver !== "undefined") {
      let previousCompact: boolean | null = null;
      const observer = new ResizeObserver((entries) => {
        const width = entries[0]?.contentRect.width ?? cockpit.getBoundingClientRect().width;
        const compact = width <= 960;
        compactLayoutRef.current = compact;
        if (previousCompact === compact) return;
        previousCompact = compact;
        setBeatCollapsed(compact);
        setGlanceCollapsed(true);
      });
      observer.observe(cockpit);
      return () => observer.disconnect();
    }

    if (typeof window.matchMedia !== "function") return;
    const query = window.matchMedia("(max-width: 60rem)");
    const sync = () => {
      compactLayoutRef.current = query.matches;
      setBeatCollapsed(query.matches);
      setGlanceCollapsed(true);
    };
    sync();
    query.addEventListener?.("change", sync);
    return () => query.removeEventListener?.("change", sync);
  }, []);

  useEffect(() => {
    if (returnInspectionToMoreRef.current) {
      returnInspectionToMoreRef.current = false;
      queueMicrotask(() => moreNavbarToggleRef.current?.focus());
    } else if (workspace.kind === "scene-inspect") {
      queueMicrotask(() => workspaceHeadingRef.current?.focus());
    }
  }, [workspace]);

  const moment = resolveCurrentMoment(deck);
  const currentBeat = moment.status === "ok" ? moment.beat : null;
  const currentScene = moment.status === "ok" ? moment.scene : null;
  const surfaceIdentity = playSurfaceContextIdentity(run, run.run_id);
  const inspectedScene = workspace.kind === "scene-inspect"
    ? sceneInAnyBeat(deck, workspace.sceneId)
    : null;
  const inspectedBeat = workspace.kind === "scene-inspect"
    ? beatForScene(deck, workspace.sceneId)
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
  useEffect(() => {
    onNoteUnsubmittedChange?.(sceneNoteScope != null && (sceneNoteScope !== hydratedNoteScope || activeSceneNoteDraft != null));
    return () => onNoteUnsubmittedChange?.(false);
  }, [activeSceneNoteDraft, sceneNoteScope, hydratedNoteScope, run.run_revision, onNoteUnsubmittedChange]);
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
    setHydratedNoteScope(sceneNoteScope);
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
      const outline = compactLayoutRef.current
        ? scenesNavbarToggleRef.current
        : outlineToggleRef.current;
      if (outline?.isConnected) {
        outline.focus();
      }
    });
  };

  const closeToCurrent = () => {
    setMoreOpen(false);
    setWorkspace({ kind: "current" });
    restoreWorkspaceFocus();
  };

  const toggleOutline = () => {
    const nextCollapsed = !beatCollapsed;
    if (compactLayoutRef.current && !nextCollapsed) {
      compactPanelFocusRef.current = "scenes";
      setGlanceCollapsed(true);
    }
    setBeatCollapsed(nextCollapsed);
    if (!nextCollapsed) queueMicrotask(() => compactOutlineToggleRef.current?.focus());
  };

  const toggleOutcomes = () => {
    const nextCollapsed = !glanceCollapsed;
    if (compactLayoutRef.current && !nextCollapsed) {
      compactPanelFocusRef.current = "outcomes";
      setBeatCollapsed(true);
    }
    setGlanceCollapsed(nextCollapsed);
    if (!nextCollapsed) queueMicrotask(() => compactOutcomesToggleRef.current?.focus());
  };

  const dismissSurfacePanelOnEscape = (event: KeyboardEvent<HTMLButtonElement>, panel: "scenes" | "outcomes") => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    event.stopPropagation();
    if (panel === "scenes") setBeatCollapsed(true);
    else setGlanceCollapsed(true);
    queueMicrotask(() => (panel === "scenes" ? scenesNavbarToggleRef.current : moreNavbarToggleRef.current)?.focus());
  };

  const openInspect = (scene: NativeRunbookSceneV2) => {
    if (compactLayoutRef.current) {
      setBeatCollapsed(true);
      setGlanceCollapsed(true);
    }
    setMoreOpen(false);
    setWorkspace(scene.id === currentScene?.id ? { kind: "current" } : { kind: "scene-inspect", sceneId: scene.id });
  };

  const browseAdjacentScene = (direction: -1 | 1) => {
    const scenes = deck.beats.flatMap(beat => beat.scenes);
    const index = scenes.findIndex(scene => scene.id === (inspectedScene?.id ?? currentScene?.id));
    const scene = scenes[Math.max(0, Math.min(scenes.length - 1, index + direction))];
    if (scene) openInspect(scene);
  };

  const saving = mutationStatus === "saving";
  const workspaceKind = workspace.kind === "scene-inspect" && inspectedScene == null
    ? "current"
    : workspace.kind;
  const compactOverlayOpen = compactLayoutRef.current && (!beatCollapsed || !glanceCollapsed);
  const decisions = currentBeat
    ? operableDecisions(currentBeat, currentScene?.id ?? null)
    : [];
  const inspectedDecisions = inspectedBeat && inspectedScene
    ? operableDecisions(inspectedBeat, inspectedScene.id)
    : [];
  const originKind = "kind" in deck.snapshot
    ? deck.snapshot.kind
    : "record" in deck.snapshot ? deck.snapshot.record.kind : null;
  const editionOriginLabel = originKind === "plan"
    ? `From Plan version ${run.playable_revision}`
    : originKind === "runbook"
      ? `From Runbook version ${run.playable_revision}`
      : `From saved source version ${run.playable_revision}`;
  const sceneCardIdentity = (sceneId: string): SceneCardIdentity => ({
    worldId: worldOwnedRun ? run.world_id : null,
    campaignId: worldOwnedRun ? null : run.campaign_id,
    documentId: run.playable_artifact_id,
    sceneId,
    revision: run.playable_revision,
    workRevisionId: worldOwnedRun ? run.playable_work_revision_id : null,
    contentSha256: run.playable_content_sha256,
    sourceState: deck.effectiveContent?.source === "edition" ? "run-edition" : "run-pin",
    ...(deck.effectiveContent?.source === "edition" ? {
      edition: { revision: deck.effectiveContent.edition_revision, revisionId: deck.effectiveContent.edition_revision_id!, contentSha256: deck.effectiveContent.content_sha256 },
      originLabel: editionOriginLabel,
    } : {}),
  });
  const choiceActions = (source: readonly NativeRunbookChoiceV2[], writable: boolean): SceneCardChoiceActions => ({
    writable,
    busy: saving || !mutationsOpen,
    onSelectOption: writable ? (choiceId, optionId) => {
      const choice = source.find((entry) => entry.id === choiceId);
      if (choice) selectOption(choice, optionId);
    } : undefined,
    onClearSelection: writable ? (choiceId) => {
      const choice = source.find((entry) => entry.id === choiceId);
      if (choice) clearSelection(choice);
    } : undefined,
    renderSelectedContext: ({ id }) => {
      const choice = source.find((entry) => entry.id === id);
      if (!choice) return null;
      const branch = choiceBranchRelevance(deck, choice);
      return branch.length ? (
        <ul className="play-decision-relevance" data-testid="play-decision-relevance">
          {branch.map((row) => (
            <li key={row.targetId} data-target-id={row.targetId} data-relevance={row.relevance}>
              {row.title} — {row.relevance}
            </li>
          ))}
        </ul>
      ) : null;
    },
  });

  return (
    <section
      className="play-cockpit"
      ref={cockpitRef}
      data-testid="play-current-moment-cockpit"
      data-play-run-id={run.run_id}
      data-current-beat-id={deck.currentBeatId}
      data-current-scene-id={deck.currentSceneId ?? ""}
      aria-label="Current moment"
      onKeyDown={(event) => {
        if (event.key !== "Escape") return;
        event.preventDefault();
        if (compactOverlayOpen) {
          const focusTarget = compactPanelFocusRef.current === "scenes"
            ? scenesNavbarToggleRef
            : moreNavbarToggleRef;
          setBeatCollapsed(true);
          setGlanceCollapsed(true);
          queueMicrotask(() => focusTarget.current?.focus());
        } else if (workspaceKind === "scene-inspect") {
          closeToCurrent();
        }
      }}
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

      <PlaySurfaceContext id="play-cockpit-context" order={20} identity={surfaceIdentity}>
        <ContentsToggle buttonRef={scenesNavbarToggleRef} className="surface-context-action play-surface-context__outline" label="Contents" controls="play-outline-body" onKeyDown={event => dismissSurfacePanelOnEscape(event, "scenes")} onToggle={toggleOutline} expanded={!beatCollapsed} />
        <SurfaceContextSelect className="play-surface-context__scene" aria-label="Inspect scene" value={inspectedScene?.id ?? currentScene?.id ?? ""}
          onChange={event => { const scene = sceneInAnyBeat(deck, event.target.value); if (scene) openInspect(scene); }}>
          {!currentScene ? <option value="">Choose scene</option> : null}
          {deck.beats.map(beat => <optgroup key={beat.id} label={beat.title}>{beat.scenes.map(scene => <option key={scene.id} value={scene.id}>{scene.id === currentScene?.id ? "Current: " : ""}{scene.title}</option>)}</optgroup>)}
        </SurfaceContextSelect>
        {workspace.kind === "scene-inspect" ? <SurfaceContextAction className="play-surface-context__return" type="button" aria-label="Return to current" title={`Return to current scene: ${currentScene?.title ?? "none"}`} onClick={closeToCurrent}>Current</SurfaceContextAction> : null}
        <button ref={notesNavbarToggleRef} className="surface-context-action play-surface-context__notes" type="button" aria-expanded={notesOpen} aria-label={`Notes · ${workspace.kind === "scene-inspect" ? "current scene " : ""}${currentScene?.title ?? "no current scene"}`} title={`Notes for current scene: ${currentScene?.title ?? "none"}`} onClick={() => setNotesOpen(value => !value)} disabled={!worldOwnedRun || !currentScene}>
          Notes{workspace.kind === "scene-inspect" ? " (current)" : ""}
        </button>
        <div className="play-surface-context__more" onKeyDownCapture={event => {
          if (event.key !== "Escape" || !moreOpen) return;
          event.preventDefault(); event.stopPropagation(); setMoreOpen(false);
          queueMicrotask(() => moreNavbarToggleRef.current?.focus());
        }}>
        <SurfaceContextPopover open={moreOpen} onOpenChange={setMoreOpen} title="More" align="end" trigger={<button ref={moreNavbarToggleRef} className="surface-context-action" type="button" aria-expanded={moreOpen} aria-label="More Play controls" onKeyDown={event => {
          if (event.key !== "Escape") return;
          event.preventDefault(); event.stopPropagation();
          setBeatCollapsed(true); setGlanceCollapsed(true);
          queueMicrotask(() => moreNavbarToggleRef.current?.focus());
        }} onClick={() => setMoreOpen(value => !value)}>More</button>}>
          <SurfaceContextAction type="button" onClick={() => { toggleOutcomes(); setMoreOpen(false); queueMicrotask(() => moreNavbarToggleRef.current?.focus()); }} aria-expanded={!glanceCollapsed}>Run record</SurfaceContextAction>
          <div className="play-surface-context__compact-navigation" role="group" aria-label="Scene navigation">
            <SurfaceContextAction type="button" onClick={() => { toggleOutline(); setMoreOpen(false); queueMicrotask(() => moreNavbarToggleRef.current?.focus()); }}>Browse Contents</SurfaceContextAction>
            <SurfaceContextAction type="button" disabled={!currentScene} onClick={() => { returnInspectionToMoreRef.current = true; browseAdjacentScene(-1); }}>Previous</SurfaceContextAction>
            <SurfaceContextAction type="button" disabled={!currentScene} onClick={() => { returnInspectionToMoreRef.current = true; browseAdjacentScene(1); }}>Next</SurfaceContextAction>
            {workspace.kind === "scene-inspect" ? <SurfaceContextAction type="button" onClick={() => { closeToCurrent(); queueMicrotask(() => moreNavbarToggleRef.current?.focus()); }}>Show current scene</SurfaceContextAction> : null}
          </div>
          <p className="play-muted" data-testid="play-source-cue">
            {deck.effectiveContent?.source === "edition" ? `Session copy · revision ${deck.effectiveContent.edition_revision} · ` : ""}
            Created from saved {originKind === "plan" ? "Plan" : originKind === "runbook" ? "Runbook" : originKind === "worldbuilding_source" ? "Worldbuilding source" : "source"} version {run.playable_revision}
          </p>
          {currentBeat && inspectedScene ? <>
            <p className="play-inspect-position" data-testid="play-inspect-current">Run position: {currentBeat.title} · {currentScene?.title ?? "No current Scene"}</p>
            <p className="play-inspect-position" data-testid="play-inspect-scene">Viewing: {inspectedBeat?.title ?? "Unknown Beat"} · {inspectedScene.title}</p>
          </> : null}
          {(inspectedBeat ?? currentBeat) ? <BeatContext beat={(inspectedBeat ?? currentBeat)!}
            resolved={run.progress.resolved_beat_ids.includes((inspectedBeat ?? currentBeat)!.id)}
            relation={inspectedBeat ? "Viewing Beat" : "Current Beat"} /> : null}
        </SurfaceContextPopover>
        </div>
      </PlaySurfaceContext>

      <div
        className="play-cockpit-shell"
        data-testid="play-cockpit-shell"
        data-beat-collapsed={beatCollapsed ? "true" : "false"}
        data-glance-collapsed={glanceCollapsed ? "true" : "false"}
      >
        <div
          className="play-cockpit-center"
          data-testid="play-central-workspace"
          data-workspace={workspaceKind}
          inert={compactOverlayOpen}
          aria-hidden={compactOverlayOpen ? true : undefined}
        >
          <CardSceneNavigation scenes={deck.beats.flatMap(beat => beat.scenes)} sceneId={inspectedScene?.id ?? currentScene?.id ?? null}
            hidden={workspaceKind !== "current" && workspaceKind !== "scene-inspect"}
            onSelect={id => { const scene = sceneInAnyBeat(deck, id); if (scene) openInspect(scene); }} />
          {workspaceKind === "current" && currentBeat && currentScene ? (
            <article
              className="play-scene-board"
              data-testid="play-workspace-current"
              aria-labelledby="play-workspace-heading"
            >
              <SceneCard
                identity={sceneCardIdentity(currentScene.id)}
                scene={currentScene}
                choices={playSceneCardChoices(decisions, run.progress.selections)}
                variant="play-current"
                kicker=""
                headingId="play-workspace-heading"
                headingRef={workspaceHeadingRef}

                choiceActions={choiceActions(decisions, true)}

              />
            </article>
          ) : null}

          {workspaceKind === "current" && currentBeat && currentScene == null ? (
            <article data-testid="play-workspace-beat-only" aria-labelledby="play-workspace-heading">
              <p className="play-kicker">Current Beat</p>
              <h2 id="play-workspace-heading" ref={workspaceHeadingRef} tabIndex={-1}>{currentBeat.title}</h2>
              <p className="play-muted" data-testid="play-current-scene">No Scene is current.</p>
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

          {workspaceKind === "scene-inspect" && inspectedScene && currentBeat ? (
            <article
              data-testid="play-workspace-inspect"
              data-inspecting-current={inspectedScene.id === currentScene?.id ? "true" : "false"}
              aria-labelledby="play-workspace-heading"
            >
              <SceneCard
                identity={sceneCardIdentity(inspectedScene.id)}
                scene={inspectedScene}
                choices={playSceneCardChoices(inspectedDecisions, run.progress.selections)}
                variant="play-inspection"
                kicker=""
                headingId="play-workspace-heading"
                headingRef={workspaceHeadingRef}

                sceneActions={<div className="play-controls">
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
                </div>}
                choiceActions={choiceActions(inspectedDecisions, false)}
                footer={worldOwnedRun ? (
                  <section className="play-notes play-notes--readonly" data-testid="play-inspected-scene-note">
                    <h3>Scene note</h3>
                    <p>{Object.prototype.hasOwnProperty.call(run.progress.notes_by_element_id, inspectedScene.id)
                      ? run.progress.notes_by_element_id[inspectedScene.id]
                      : "No saved note."}</p>
                  </section>
                ) : null}
              />
            </article>
          ) : null}
        </div>

        <PlaySceneOutline
          deck={deck}
          currentSceneId={currentScene?.id ?? null}
          inspectedSceneId={workspaceKind === "scene-inspect" ? inspectedScene?.id ?? null : null}
          collapsed={beatCollapsed}
          compact={compactLayoutRef.current}
          returnFocusRef={scenesNavbarToggleRef}
          onToggle={toggleOutline}
          onInspect={openInspect}
          toggleRef={outlineToggleRef}
        />
        <PlayRecordedOutcomes
          deck={deck}
          collapsed={glanceCollapsed}
          onToggle={toggleOutcomes}
          onInspect={openInspect}
        />
      </div>

      {worldOwnedRun ? (
        <FloatingSceneNotes sceneTitle={currentScene?.title ?? null} open={notesOpen} onOpenChange={setNotesOpen} returnFocusRef={notesNavbarToggleRef} hideToggle
          available={Boolean(sceneNoteScope && sceneNoteId)} suspended={compactOverlayOpen}
          status={activeSceneNoteStorageWarning || activeSceneNoteDraft?.failure || sceneNoteChangedOnServer
            ? "Needs attention" : activeSceneNoteDraft?.state === "saving" ? "Saving…"
              : activeSceneNoteDraft ? "Unsaved" : sceneNoteSaved ? "Saved" : "No note yet"}>
          {sceneNoteScope && sceneNoteId ? (
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
                    id="play-scene-note-status"
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
        </FloatingSceneNotes>
      ) : null}
    </section>
  );
}
