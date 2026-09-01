import { useEffect, useRef, useState } from "react";

import { LiveApiError, getPlayRun, putPlayRunProgress } from "../../api/liveApi";
import type { PlayRunProgress, PlayRunRecord } from "../../api/types";
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
  onAuthoritativeRun: (run: PlayRunRecord) => void;
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
  const mutationsOpen = mutationStatus === "idle" || mutationStatus === "saving";
  const [workspace, setWorkspace] = useState<PlayWorkspace>({ kind: "current" });
  const [beatCollapsed, setBeatCollapsed] = useState(false);
  const [glanceCollapsed, setGlanceCollapsed] = useState(false);
  const [progressRejection, setProgressRejection] = useState<string | null>(null);
  const [exactRereadSucceeded, setExactRereadSucceeded] = useState(false);
  const mountedRef = useRef(true);
  const liveRunIdRef = useRef(run.run_id);
  const requestSerialRef = useRef(0);
  const scenesLauncherRef = useRef<HTMLButtonElement | null>(null);
  const glanceToggleRef = useRef<HTMLButtonElement | null>(null);
  const inFlightRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;
    liveRunIdRef.current = run.run_id;
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
    setExactRereadSucceeded(false);
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
      setExactRereadSucceeded(reconciled != null);
      if (status === 409) {
        onMutationStatus(reconciled ? "conflict" : "unknown");
        return;
      }
      if (status === 422) {
        if (reconciled) {
          onMutationStatus("idle");
          setProgressRejection(
            "The Run rejected that change. Reloaded the exact Run. The write was not retried or treated as a conflict.",
          );
        } else {
          onMutationStatus("unknown");
        }
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
                  {currentBeat.bodyText ? <p className="play-body">{currentBeat.bodyText}</p> : null}
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
              {currentScene.bodyText ? <p className="play-body play-scene-board-body">{currentScene.bodyText}</p> : null}
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

          {workspaceKind === "current" && currentBeat && currentScene == null ? (
            <article data-testid="play-workspace-beat-only" aria-labelledby="play-workspace-heading">
              <p className="play-kicker">Current Beat</p>
              <h2 id="play-workspace-heading">{currentBeat.title}</h2>
              {currentBeat.bodyText ? <p className="play-body">{currentBeat.bodyText}</p> : null}
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
              {inspectedScene.bodyText ? <p className="play-body">{inspectedScene.bodyText}</p> : null}
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
