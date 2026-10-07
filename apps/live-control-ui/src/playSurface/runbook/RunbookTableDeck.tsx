import { useEffect, useRef, useState } from "react";

import {
  LiveApiError,
  getPlayRun,
  getWorldPlayRun,
  putPlayRunProgress,
  putWorldPlayRunProgress,
} from "../../api/liveApi";
import type { AnyPlayRunRecord, PlayRunProgress } from "../../api/types";
import { MarkdownEditorCore } from "../../tiptap/MarkdownEditorCore";
import {
  canonicalizePlayRunProgress,
  type NativeRunbookReadyDeck,
} from "./nativeRunbookProjection";

export type RunbookMutationStatus = "idle" | "saving" | "conflict" | "unknown";

export interface RunbookTableDeckProps {
  deck: NativeRunbookReadyDeck;
  onAuthoritativeRun: (run: AnyPlayRunRecord) => void;
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
  const [viewMode, setViewMode] = useState<"table" | "runbook">("table");
  const [noteDrafts, setNoteDrafts] = useState<{ runId: string; values: Record<string, string> }>({
    runId: run.run_id,
    values: {},
  });
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

  useEffect(() => {
    setViewMode("table");
    setNoteDrafts({ runId: run.run_id, values: {} });
  }, [run.run_id]);

  const viewScene = sceneById(deck, viewSceneId);
  const viewBeat = viewScene?.beats.find((beat) => beat.id === viewBeatId) ?? viewScene?.beats[0] ?? null;
  const noteElementId = viewBeat?.id ?? viewScene?.id ?? null;

  const noteIsDraft = noteElementId != null
    && noteDrafts.runId === run.run_id
    && Object.prototype.hasOwnProperty.call(noteDrafts.values, noteElementId);
  const noteDraft = noteElementId == null ? "" : noteIsDraft
    ? noteDrafts.values[noteElementId]
    : run.progress.notes_by_element_id[noteElementId] ?? "";

  const replaceProgress = async (
    next: PlayRunProgress,
    onAcknowledged?: (updated: AnyPlayRunRecord) => void,
  ) => {
    if (!mutationsOpen) return;
    const boundRunId = run.run_id;
    const expected = run.run_revision;
    const serial = requestSerialRef.current + 1;
    requestSerialRef.current = serial;
    onMutationStatus("saving");
    try {
      const request = {
        expected_run_revision: expected,
        progress: canonicalizePlayRunProgress(next),
      };
      const updated = run.schema_version === "dmb_world_play_run_record_v2"
        ? await putWorldPlayRunProgress(boundRunId, run.world_id, request)
        : await putPlayRunProgress(boundRunId, request);
      if (!mountedRef.current || liveRunIdRef.current !== boundRunId || requestSerialRef.current !== serial) {
        return;
      }
      onAcknowledged?.(updated);
      onAuthoritativeRun(updated);
      onMutationStatus("idle");
    } catch (error) {
      if (!mountedRef.current || liveRunIdRef.current !== boundRunId || requestSerialRef.current !== serial) {
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
    const boundRunId = run.run_id;
    const boundElementId = noteElementId;
    const submittedText = noteDraft;
    void replaceProgress({
      ...run.progress,
      notes_by_element_id: {
        ...run.progress.notes_by_element_id,
        [boundElementId]: submittedText,
      },
    }, (updated) => {
      if (updated.run_id !== boundRunId || updated.schema_version !== run.schema_version
        || updated.playable_artifact_id !== run.playable_artifact_id
        || updated.playable_revision !== run.playable_revision
        || updated.playable_content_sha256 !== run.playable_content_sha256
        || updated.run_revision <= run.run_revision) return;
      if (run.schema_version === "dmb_world_play_run_record_v2"
        && (updated.schema_version !== "dmb_world_play_run_record_v2" || updated.world_id !== run.world_id
          || updated.playable_work_revision_id !== run.playable_work_revision_id)) return;
      if (updated.progress.notes_by_element_id[boundElementId] !== submittedText) return;
      setNoteDrafts((current) => {
        if (current.runId !== boundRunId || current.values[boundElementId] !== submittedText) return current;
        const values = { ...current.values };
        delete values[boundElementId];
        return { runId: current.runId, values };
      });
    });
  };

  const runtimeSceneId = run.progress.current_scene_id;
  const runtimeBeatId = run.progress.current_beat_id;

  return (
    <section className="play-deck" data-testid="runbook-table-deck" aria-label="Runbook table deck">
      <header className="play-surface-header">
        <p className="play-kicker">Play</p>
        <h1>{"record" in deck.snapshot ? deck.snapshot.record.title : deck.snapshot.title}</h1>
        <div className="play-deck-meta">
          <span>Run {run.run_id}</span>
          {run.schema_version === "dmb_world_play_run_record_v2"
            ? <span>World {run.world_id}</span>
            : <span>Campaign {run.campaign_id}</span>}
          <span>
            Runbook revision {run.playable_revision} · run revision {run.run_revision}
          </span>
        </div>
        <div className="play-mode-toggle" role="group" aria-label="Play projection">
          <button
            type="button"
            data-testid="play-mode-table"
            aria-pressed={viewMode === "table"}
            onClick={() => setViewMode("table")}
          >
            Table
          </button>
          <button
            type="button"
            data-testid="play-mode-runbook"
            aria-pressed={viewMode === "runbook"}
            onClick={() => setViewMode("runbook")}
          >
            Runbook
          </button>
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

      {viewMode === "runbook" ? (
        <div className="play-runbook-document" data-testid="play-runbook-document">
          <MarkdownEditorCore
            content={deck.importedDoc}
            editable={false}
            documentKey={`${run.run_id}:${run.playable_revision}:${run.playable_content_sha256}`}
            className="play-runbook-editor"
            dataTestId="play-runbook-editor"
          />
        </div>
      ) : (
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

              {noteElementId ? (
                <div className="play-notes">
                  <label htmlFor={`play-note-${noteElementId}`}>Note</label>
                  <textarea
                    id={`play-note-${noteElementId}`}
                    value={noteDraft}
                    disabled={mutationStatus === "saving"}
                    readOnly={!mutationsOpen}
                    onChange={(event) => {
                      const text = event.target.value;
                      setNoteDrafts((current) => ({
                        runId: run.run_id,
                        values: {
                          ...(current.runId === run.run_id ? current.values : {}),
                          [noteElementId]: text,
                        },
                      }));
                    }}
                  />
                  <p className="play-muted" role="status">
                    {noteIsDraft ? "Unsaved note" : Object.prototype.hasOwnProperty.call(run.progress.notes_by_element_id, noteElementId)
                      ? "Saved in this Run" : "No saved note"}
                  </p>
                  <button type="button" disabled={!mutationsOpen || mutationStatus === "saving"} onClick={saveNote}>
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
      )}
    </section>
  );
}
