import { useEffect, useRef, useState } from "react";

import { LiveApiError, putPlayRunProgress, getPlayRun } from "../../api/liveApi";
import type { PlayRunProgress, PlayRunRecord } from "../../api/types";
import {
  canonicalizePlayRunProgress,
  type NativeRunbookReadyDeck,
} from "./nativeRunbookProjection";

export type RunbookMutationStatus = "idle" | "saving" | "conflict" | "unknown";

export interface RunbookTableDeckProps {
  deck: NativeRunbookReadyDeck;
  onAuthoritativeRun: (run: PlayRunRecord) => void;
  mutationStatus: RunbookMutationStatus;
  onMutationStatus: (status: RunbookMutationStatus) => void;
}

function sceneById(deck: NativeRunbookReadyDeck, sceneId: string | null) {
  return deck.scenes.find((scene) => scene.id === sceneId) ?? null;
}

export function RunbookTableDeck({
  deck,
  onAuthoritativeRun,
  mutationStatus,
  onMutationStatus,
}: RunbookTableDeckProps) {
  const run = deck.run;
  const mutationsOpen = mutationStatus === "idle" || mutationStatus === "saving";
  const [viewSceneId, setViewSceneId] = useState<string | null>(deck.displayedSceneId);
  const [viewBeatId, setViewBeatId] = useState<string | null>(deck.displayedBeatId);
  const [noteDraft, setNoteDraft] = useState("");
  const mountedRef = useRef(true);
  const liveRunIdRef = useRef(run.run_id);
  const requestSerialRef = useRef(0);

  useEffect(() => {
    mountedRef.current = true;
    liveRunIdRef.current = run.run_id;
    return () => {
      mountedRef.current = false;
      requestSerialRef.current += 1;
    };
  }, [run.run_id]);

  useEffect(() => {
    setViewSceneId(deck.displayedSceneId);
    setViewBeatId(deck.displayedBeatId);
  }, [run.run_id, run.progress.current_scene_id, run.progress.current_beat_id, deck.displayedSceneId, deck.displayedBeatId]);

  const viewScene = sceneById(deck, viewSceneId);
  const viewBeat = viewScene?.beats.find((beat) => beat.id === viewBeatId) ?? viewScene?.beats[0] ?? null;
  const noteElementId = viewBeat?.id ?? viewScene?.id ?? null;

  useEffect(() => {
    if (!noteElementId) {
      setNoteDraft("");
      return;
    }
    setNoteDraft(run.progress.notes_by_element_id[noteElementId] ?? "");
  }, [noteElementId, run.progress.notes_by_element_id, run.run_revision]);

  const replaceProgress = async (next: PlayRunProgress) => {
    if (!mutationsOpen) return;
    const boundRunId = run.run_id;
    const expected = run.run_revision;
    const serial = requestSerialRef.current + 1;
    requestSerialRef.current = serial;
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
    }
  };

  const setCurrentScene = (sceneId: string) => {
    const scene = sceneById(deck, sceneId);
    const beatId = scene?.beats[0]?.id ?? null;
    void replaceProgress({
      ...run.progress,
      current_scene_id: sceneId,
      current_beat_id: beatId,
    });
  };

  const setCurrentBeat = (beatId: string) => {
    const sceneId = viewScene?.id;
    if (!sceneId) return;
    void replaceProgress({
      ...run.progress,
      current_scene_id: sceneId,
      current_beat_id: beatId,
    });
  };

  const toggleResolved = (beatId: string, resolved: boolean) => {
    const next = new Set(run.progress.resolved_beat_ids);
    if (resolved) next.add(beatId);
    else next.delete(beatId);
    void replaceProgress({
      ...run.progress,
      resolved_beat_ids: [...next],
    });
  };

  const selectOption = (choiceId: string, optionId: string) => {
    void replaceProgress({
      ...run.progress,
      selections: {
        ...run.progress.selections,
        [choiceId]: optionId,
      },
    });
  };

  const saveNote = () => {
    if (!noteElementId) return;
    void replaceProgress({
      ...run.progress,
      notes_by_element_id: {
        ...run.progress.notes_by_element_id,
        [noteElementId]: noteDraft,
      },
    });
  };

  const runtimeSceneId = run.progress.current_scene_id;
  const runtimeBeatId = run.progress.current_beat_id;

  return (
    <section className="play-deck" data-testid="runbook-table-deck" aria-label="Runbook table deck">
      <header className="play-surface-header">
        <p className="play-kicker">Play</p>
        <h1>{deck.snapshot.record.title}</h1>
        <div className="play-deck-meta">
          <span>Run {run.run_id}</span>
          <span>Campaign {run.campaign_id}</span>
          <span>
            Runbook revision {run.playable_revision} · run revision {run.run_revision}
          </span>
        </div>
      </header>

      {deck.currentIsPreview ? (
        <p className="play-preview-flag" data-testid="play-preview-flag">
          Previewing the first authored Scene. Current Scene is unset until you set it.
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

      <div className="play-deck-columns">
        <nav aria-label="Scenes">
          <h2>Scenes</h2>
          <ul className="play-nav-list">
            {deck.scenes.map((scene) => (
              <li key={scene.id}>
                <button
                  type="button"
                  aria-current={viewScene?.id === scene.id}
                  className={runtimeSceneId === scene.id ? "current" : undefined}
                  onClick={() => {
                    setViewSceneId(scene.id);
                    setViewBeatId(scene.beats[0]?.id ?? null);
                  }}
                >
                  {scene.title}
                  {runtimeSceneId === scene.id ? " · current" : ""}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <nav aria-label="Beats">
          <h2>Beats</h2>
          <ul className="play-nav-list">
            {(viewScene?.beats ?? []).map((beat) => (
              <li key={beat.id}>
                <button
                  type="button"
                  aria-current={viewBeat?.id === beat.id}
                  className={runtimeBeatId === beat.id ? "current" : undefined}
                  onClick={() => setViewBeatId(beat.id)}
                >
                  {beat.title}
                  {run.progress.resolved_beat_ids.includes(beat.id) ? " · resolved" : ""}
                  {runtimeBeatId === beat.id ? " · current" : ""}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <article className="play-authored" aria-label="Focused runbook content">
          {viewScene ? (
            <>
              <div>
                <h2>{viewScene.title}</h2>
                {viewScene.bodyText ? <p className="play-body">{viewScene.bodyText}</p> : null}
                {mutationsOpen ? (
                  <div className="play-controls">
                    <button
                      type="button"
                      disabled={mutationStatus === "saving"}
                      onClick={() => setCurrentScene(viewScene.id)}
                    >
                      Set current Scene
                    </button>
                  </div>
                ) : null}
              </div>
              {viewBeat ? (
                <div data-testid="focused-beat">
                  <h3>{viewBeat.title}</h3>
                  {viewBeat.bodyText ? <p className="play-body">{viewBeat.bodyText}</p> : null}
                  {mutationsOpen ? (
                    <div className="play-controls">
                      <button
                        type="button"
                        disabled={mutationStatus === "saving"}
                        onClick={() => setCurrentBeat(viewBeat.id)}
                      >
                        Set current Beat
                      </button>
                      <label>
                        <input
                          type="checkbox"
                          checked={run.progress.resolved_beat_ids.includes(viewBeat.id)}
                          disabled={mutationStatus === "saving"}
                          onChange={(event) => toggleResolved(viewBeat.id, event.target.checked)}
                        />
                        Resolved
                      </label>
                    </div>
                  ) : null}
                </div>
              ) : null}

              {(viewScene.choices ?? []).map((choice) => (
                <div key={choice.id} className="play-choice">
                  <h3>{choice.title}</h3>
                  {choice.bodyText ? <p className="play-body">{choice.bodyText}</p> : null}
                  <ul className="play-option-list">
                    {choice.options.map((option) => (
                      <li key={option.id}>
                        <label>
                          <input
                            type="radio"
                            name={`choice-${choice.id}`}
                            checked={run.progress.selections[choice.id] === option.id}
                            disabled={!mutationsOpen || mutationStatus === "saving"}
                            onChange={() => selectOption(choice.id, option.id)}
                          />
                          {option.title}
                        </label>
                        {option.bodyText ? <p className="play-body">{option.bodyText}</p> : null}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}

              {noteElementId && mutationsOpen ? (
                <div className="play-notes">
                  <label htmlFor={`play-note-${noteElementId}`}>Note</label>
                  <textarea
                    id={`play-note-${noteElementId}`}
                    value={noteDraft}
                    disabled={mutationStatus === "saving"}
                    onChange={(event) => setNoteDraft(event.target.value)}
                  />
                  <button type="button" disabled={mutationStatus === "saving"} onClick={saveNote}>
                    Save note
                  </button>
                </div>
              ) : null}
            </>
          ) : (
            <p className="play-muted">This Runbook has no authored Scenes.</p>
          )}
        </article>
      </div>
    </section>
  );
}
