import { useCallback, useEffect, useRef, useState } from "react";

import { LiveApiError, getPlayRun, putPlayRunProgress } from "../../api/liveApi";
import type { PlayRunProgress, PlayRunRecord } from "../../api/types";
import { PlayRunNavigator } from "../PlayRunNavigator";
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
  sceneInCurrentBeat,
  type PlayWorkspace,
} from "./currentMomentModel";
import {
  operableDecisions,
  planClearSelection,
  planSelectOption,
  selectedOptionForChoice,
  selectedOptionTouchedRelevance,
} from "./decisionInteractionModel";

export interface PlayCurrentMomentCockpitProps {
  deck: NativeRunbookReadyV2;
  mutationStatus: RunbookMutationStatus;
  onMutationStatus: (status: RunbookMutationStatus) => void;
  onAuthoritativeRun: (run: PlayRunRecord) => void;
  onStartNewRun?: () => void;
}

function relevanceLabel(relevance: NativeRunbookSceneV2["relevance"]): string | null {
  if (relevance === "emphasized") return "emphasized";
  if (relevance === "de-emphasized") return "de-emphasized";
  return null;
}

function isSeparatorOnlyContext(text: string): boolean {
  return text.replace(/[·.•….\-\s]/g, "").length === 0;
}

function BeatContextCopy({ text }: { text: string }) {
  const parts = text
    .split(/\n\n+/)
    .map((part) => part.trim())
    .filter((part) => part.length > 0 && !isSeparatorOnlyContext(part));
  if (parts.length === 0) return null;
  return (
    <div className="play-beat-bar-context-copy">
      {parts.map((part, index) => (
        <p key={index} className="play-body">{part}</p>
      ))}
    </div>
  );
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
        const touched = selected == null ? [] : selectedOptionTouchedRelevance(deck, selected);
        const groupId = `play-decision-${choice.id}`;
        return (
          <section
            key={choice.id}
            className={`play-decision${selected ? " is-resolved" : ""}`}
            data-testid="play-decision"
            data-choice-id={choice.id}
          >
            <header className="play-decision-header">
              <p className="play-kicker">Decision</p>
              <h3 id={groupId} data-testid="play-decision-prompt">
                {choice.title}
              </h3>
              {choice.bodyText ? <p className="play-decision-framing">{choice.bodyText}</p> : null}
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
                {selected.bodyText ? (
                  <p className="play-decision-consequence" data-testid="play-decision-consequence">
                    {selected.bodyText}
                  </p>
                ) : null}
                {touched.length > 0 ? (
                  <>
                    <p className="play-decision-relevance-kicker">What this makes more / less relevant</p>
                    <ul className="play-decision-relevance" data-testid="play-decision-relevance">
                      {touched.map((row) => (
                        <li key={row.targetId} data-target-id={row.targetId} data-relevance={row.relevance}>
                          {row.title} — {row.relevance}
                        </li>
                      ))}
                    </ul>
                  </>
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
  onStartNewRun,
}: PlayCurrentMomentCockpitProps) {
  const run = deck.run;
  const mutationsOpen = mutationStatus === "idle" || mutationStatus === "saving";
  const [workspace, setWorkspace] = useState<PlayWorkspace>({ kind: "current" });
  const [beatCollapsed, setBeatCollapsed] = useState(false);
  const [progressRejection, setProgressRejection] = useState<string | null>(null);
  const mountedRef = useRef(true);
  const liveRunIdRef = useRef(run.run_id);
  const requestSerialRef = useRef(0);
  const lastInspectedSceneIdRef = useRef<string | null>(null);
  const inFlightRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;
    liveRunIdRef.current = run.run_id;
    setWorkspace({ kind: "current" });
    setBeatCollapsed(false);
    setProgressRejection(null);
    lastInspectedSceneIdRef.current = null;
    inFlightRef.current = false;
    return () => {
      mountedRef.current = false;
      requestSerialRef.current += 1;
    };
  }, [run.run_id]);

  const moment = resolveCurrentMoment(deck);
  const currentBeat = moment.status === "ok" ? moment.beat : null;
  const currentScene = moment.status === "ok" ? moment.scene : null;
  const inspectedScene = workspace.kind === "scene-inspect"
    ? sceneInCurrentBeat(deck, workspace.sceneId)
    : null;

  const replaceProgress = async (next: PlayRunProgress) => {
    if (!mutationsOpen || mutationStatus === "saving" || inFlightRef.current) return;
    const boundRunId = run.run_id;
    const expected = run.run_revision;
    const serial = requestSerialRef.current + 1;
    requestSerialRef.current = serial;
    inFlightRef.current = true;
    setProgressRejection(null);
    onMutationStatus("saving");
    try {
      const updated = await putPlayRunProgress(boundRunId, {
        expected_run_revision: expected,
        progress: canonicalizePlayRunProgress(next),
      });
      if (!mountedRef.current || liveRunIdRef.current !== boundRunId || requestSerialRef.current !== serial) {
        return;
      }
      onAuthoritativeRun(updated);
      onMutationStatus("idle");
      setWorkspace({ kind: "current" });
    } catch (error) {
      if (!mountedRef.current || liveRunIdRef.current !== boundRunId || requestSerialRef.current !== serial) {
        return;
      }
      const status = error instanceof LiveApiError ? error.status : 0;
      let reconciled: PlayRunRecord | null = null;
      try {
        reconciled = await getPlayRun(boundRunId);
      } catch {
        reconciled = null;
      }
      if (!mountedRef.current || liveRunIdRef.current !== boundRunId || requestSerialRef.current !== serial) {
        return;
      }
      if (reconciled) onAuthoritativeRun(reconciled);
      if (status === 409) {
        onMutationStatus("conflict");
        return;
      }
      if (status === 422) {
        onMutationStatus("idle");
        setProgressRejection(
          "The Run rejected that change. Reloaded the exact Run. The write was not retried or treated as a conflict.",
        );
        return;
      }
      onMutationStatus("unknown");
    } finally {
      if (requestSerialRef.current === serial) {
        inFlightRef.current = false;
      }
    }
  };

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

  const restoreWorkspaceFocus = useCallback(() => {
    queueMicrotask(() => {
      const sceneId = lastInspectedSceneIdRef.current;
      const selector = sceneId
        ? `[data-testid="play-chrome-scene"][data-scene-id="${CSS.escape(sceneId)}"]`
        : '[data-testid="play-chrome-scene"][data-current="true"]';
      const target = document.querySelector<HTMLButtonElement>(selector);
      target?.focus();
    });
  }, []);

  const closeToCurrent = useCallback(() => {
    setWorkspace({ kind: "current" });
    restoreWorkspaceFocus();
  }, [restoreWorkspaceFocus]);

  const openInspect = useCallback((scene: NativeRunbookSceneV2) => {
    lastInspectedSceneIdRef.current = scene.id;
    setWorkspace({ kind: "scene-inspect", sceneId: scene.id });
  }, []);

  const selectBeat = (beat: NativeRunbookBeatV2) => {
    if (beat.id === deck.currentBeatId) {
      closeToCurrent();
      return;
    }
    const sceneStays = currentScene?.beatId === beat.id ? currentScene.id : null;
    lastInspectedSceneIdRef.current = null;
    void replaceProgress({
      ...run.progress,
      current_beat_id: beat.id,
      current_scene_id: sceneStays,
    });
  };

  const saving = mutationStatus === "saving";
  const workspaceKind = workspace.kind === "scene-inspect" && inspectedScene == null
    ? "current"
    : workspace.kind;
  const decisions = currentBeat
    ? operableDecisions(currentBeat, currentScene?.id ?? null)
    : [];
  const showSceneIdentityInBar = workspaceKind !== "current" || currentScene == null;

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
          The progress write did not return a known result. Reloaded the exact Run before further mutation.
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

      {deck.beats.length > 0 ? (
        <PlayRunNavigator
          instanceId={run.run_id}
          beats={deck.beats}
          currentBeatId={deck.currentBeatId}
          scenes={currentBeat?.scenes ?? []}
          currentSceneId={currentScene?.id ?? null}
          inspectingSceneId={workspaceKind === "scene-inspect" ? inspectedScene?.id ?? null : null}
          beatSelectionLocked={saving || !mutationsOpen}
          onSelectBeat={selectBeat}
          onInspectScene={openInspect}
          onShowCurrent={closeToCurrent}
          onStartNewRun={onStartNewRun}
        />
      ) : null}

      {currentBeat ? (
        <article className="play-beat-wrap" data-testid="play-beat-wrap">
          <header className="play-beat-bar">
            <div className="play-beat-bar-identity">
              <p className="play-kicker">Beat</p>
              <h2 data-testid="play-current-beat">{currentBeat.title}</h2>
              {currentBeat.beatKind ? (
                <span className="play-beat-kind-pill" data-testid="play-beat-kind-pill">
                  {currentBeat.beatKind}
                </span>
              ) : null}
              {showSceneIdentityInBar ? (
                <p className="play-beat-bar-scene" data-testid="play-current-scene">
                  {currentScene ? currentScene.title : "No Scene is current"}
                </p>
              ) : null}
              <button
                type="button"
                className="play-beat-context-toggle"
                data-testid="play-beat-context-toggle"
                aria-expanded={!beatCollapsed}
                aria-controls="play-beat-context-body"
                aria-label={beatCollapsed ? "Expand Beat context" : "Collapse Beat context"}
                onClick={() => setBeatCollapsed((current) => !current)}
              >
                {beatCollapsed ? "Show context" : "Hide context"}
              </button>
            </div>
            <div
              className={`play-beat-context${beatCollapsed ? " is-collapsed" : ""}`}
              data-testid="play-beat-context"
            >
              {beatCollapsed ? null : (
                <div id="play-beat-context-body" className="play-beat-bar-context">
                  {currentBeat.bodyText ? <BeatContextCopy text={currentBeat.bodyText} /> : null}
                </div>
              )}
            </div>
          </header>

          <div
            className="play-cockpit-shell"
            data-testid="play-cockpit-shell"
            data-beat-collapsed={beatCollapsed ? "true" : "false"}
            data-center-expanded={beatCollapsed ? "true" : "false"}
          >
            <div
              className="play-cockpit-center"
              data-testid="play-central-workspace"
              data-workspace={workspaceKind}
            >
              {workspaceKind === "current" && currentScene ? (
                <article
                  className="play-workspace-board"
                  data-testid="play-workspace-current"
                  aria-labelledby="play-workspace-heading"
                >
                  <h2 id="play-workspace-heading" data-testid="play-current-scene">
                    {currentScene.title}
                  </h2>
                  {relevanceLabel(currentScene.relevance) ? (
                    <span className="play-relevance-pill">
                      {relevanceLabel(currentScene.relevance)}
                    </span>
                  ) : null}
                  {currentScene.bodyText ? <p className="play-body">{currentScene.bodyText}</p> : null}
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

              {workspaceKind === "current" && currentScene == null ? (
                <article
                  className="play-workspace-board"
                  data-testid="play-workspace-beat-only"
                  aria-labelledby="play-workspace-heading"
                >
                  <h2 id="play-workspace-heading">Scenes</h2>
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
              {inspectedScene.bodyText ? <p className="play-body">{inspectedScene.bodyText}</p> : null}
            </article>
          ) : null}
            </div>
          </div>
        </article>
      ) : null}
    </section>
  );
}
