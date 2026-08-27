import { useEffect, useRef, useState } from "react";

import { LiveApiError, getPlayRun, putPlayRunProgress } from "../../api/liveApi";
import type { PlayRunProgress, PlayRunRecord } from "../../api/types";
import {
  canonicalizePlayRunProgress,
  type NativeRunbookReadyV2,
  type NativeRunbookSceneV2,
} from "../runbook/nativeRunbookProjection";
import type { RunbookMutationStatus } from "../runbook/RunbookTableDeck";
import {
  resolveCurrentMoment,
  sceneInCurrentBeat,
  type PlayWorkspace,
} from "./currentMomentModel";

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
      onMutationStatus(status === 409 ? "conflict" : "unknown");
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
            <article data-testid="play-workspace-current" aria-labelledby="play-workspace-heading">
              <p className="play-kicker">Current Scene</p>
              <h2 id="play-workspace-heading">{currentScene.title}</h2>
              {currentScene.bodyText ? <p className="play-body">{currentScene.bodyText}</p> : null}
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
