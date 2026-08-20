import { useEffect, useRef, useState } from "react";
import type { JSONContent } from "@tiptap/core";

import { LiveApiError, putPlayRunProgress, getPlayRun } from "../../api/liveApi";
import type { PlayRunProgress, PlayRunRecord } from "../../api/types";
import { MarkdownEditorCore } from "../../tiptap/MarkdownEditorCore";
import {
  canonicalizePlayRunProgress,
  extractSceneListingsFromBody,
  omitHoistedSceneListings,
  type NativeRunbookBeat,
  type NativeRunbookReadyDeck,
  type NativeRunbookScene,
} from "./nativeRunbookProjection";

export type RunbookMutationStatus = "idle" | "saving" | "conflict" | "unknown";

export interface RunbookTableDeckProps {
  deck: NativeRunbookReadyDeck;
  onAuthoritativeRun: (run: PlayRunRecord) => void;
  mutationStatus: RunbookMutationStatus;
  onMutationStatus: (status: RunbookMutationStatus) => void;
}

type FlattenedBeat = {
  scene: NativeRunbookScene;
  beat: NativeRunbookBeat;
};

function flattenBeats(deck: NativeRunbookReadyDeck): FlattenedBeat[] {
  return deck.scenes.flatMap((scene) => scene.beats.map((beat) => ({ scene, beat })));
}

function hasRichBody(doc: JSONContent | undefined): boolean {
  return Array.isArray(doc?.content) && doc.content.length > 0;
}

function ReadOnlyPlayDoc({
  content,
  documentKey,
  className,
  dataTestId,
}: {
  content: JSONContent;
  documentKey: string;
  className: string;
  dataTestId: string;
}) {
  return (
    <MarkdownEditorCore
      content={content}
      editable={false}
      documentKey={documentKey}
      className={className}
      dataTestId={dataTestId}
    />
  );
}

function listingDescriptorId(beatId: string, index: number): string {
  return `play-scene-listing-${beatId.replace(/[^a-zA-Z0-9:_-]/g, "-")}-${index}`;
}

export function RunbookTableDeck({
  deck,
  onAuthoritativeRun,
  mutationStatus,
  onMutationStatus,
}: RunbookTableDeckProps) {
  const run = deck.run;
  const mutationsOpen = mutationStatus === "idle" || mutationStatus === "saving";
  const beats = flattenBeats(deck);
  const [viewSceneId, setViewSceneId] = useState<string | null>(deck.displayedSceneId);
  const [viewBeatId, setViewBeatId] = useState<string | null>(deck.displayedBeatId);
  const [viewSceneListing, setViewSceneListing] = useState(0);
  const [viewMode, setViewMode] = useState<"table" | "runbook">("table");
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
    setViewSceneListing(0);
  }, [run.run_id, run.progress.current_scene_id, run.progress.current_beat_id, deck.displayedSceneId, deck.displayedBeatId]);

  useEffect(() => {
    setViewMode("table");
  }, [run.run_id]);

  const matchedBeatIndex = beats.findIndex(
    (entry) => entry.scene.id === viewSceneId && entry.beat.id === viewBeatId,
  );
  const viewBeatIndex = matchedBeatIndex >= 0 ? matchedBeatIndex : beats.length > 0 ? 0 : -1;
  const viewEntry = viewBeatIndex >= 0 ? beats[viewBeatIndex] : null;
  const viewScene = viewEntry?.scene ?? null;
  const viewBeat = viewEntry?.beat ?? null;
  const beatOrdinal = viewBeatIndex >= 0 ? viewBeatIndex + 1 : 0;
  const noteElementId = viewBeat?.id ?? viewScene?.id ?? null;
  const runtimeSceneId = run.progress.current_scene_id;
  const runtimeBeatId = run.progress.current_beat_id;
  const sceneListings = extractSceneListingsFromBody(viewBeat?.bodyDoc);
  const stageBodyDoc = omitHoistedSceneListings(viewBeat?.bodyDoc);
  const focusedListingIndex = sceneListings.length === 0
    ? -1
    : Math.min(viewSceneListing, sceneListings.length - 1);

  useEffect(() => {
    setViewSceneListing(0);
  }, [viewBeat?.id]);

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

  const focusBeat = (entry: FlattenedBeat) => {
    setViewSceneId(entry.scene.id);
    setViewBeatId(entry.beat.id);
    setViewSceneListing(0);
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

  const canPreviousMoment = viewBeatIndex > 0;
  const canNextMoment = viewBeatIndex >= 0 && viewBeatIndex < beats.length - 1;

  const focusPreviousMoment = () => {
    if (viewBeatIndex > 0) focusBeat(beats[viewBeatIndex - 1]);
  };

  const focusNextMoment = () => {
    if (viewBeatIndex >= 0 && viewBeatIndex < beats.length - 1) {
      focusBeat(beats[viewBeatIndex + 1]);
    }
  };

  const bindingKey = `${run.run_id}:${run.playable_revision}:${run.playable_content_sha256}`;

  return (
    <section
      className="play-deck"
      data-testid="runbook-table-deck"
      data-run-id={run.run_id}
      data-playable-revision={String(run.playable_revision)}
      aria-label="Runbook table deck"
    >
      <header className="play-run-bar">
        <div className="play-run-identity">
          <h1>{deck.snapshot.record.title}</h1>
        </div>
        <div className="play-mode-toggle" role="group" aria-label="View mode">
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
          <ReadOnlyPlayDoc
            content={deck.importedDoc}
            documentKey={bindingKey}
            className="play-runbook-editor"
            dataTestId="play-runbook-editor"
          />
        </div>
      ) : (
      <div className="play-moment" data-testid="play-moment">
        <nav className="play-scene-deck" aria-label="Beats" data-testid="play-beat-deck">
          <button
            type="button"
            className="play-scene-step"
            aria-label="Previous beat"
            disabled={!canPreviousMoment}
            onClick={focusPreviousMoment}
          >
            Previous
          </button>
          {viewBeat ? (
            <div className="play-scene-position">
              <p className="play-scene-ordinal">
                Beat {beatOrdinal} / {beats.length}
              </p>
              <h2
                className="play-scene-heading"
                data-runtime-current={runtimeBeatId === viewBeat.id && runtimeSceneId === viewScene?.id ? "true" : "false"}
              >
                {viewBeat.title}
              </h2>
              {mutationsOpen ? (
                <label className="play-resolved">
                  <input
                    type="checkbox"
                    checked={run.progress.resolved_beat_ids.includes(viewBeat.id)}
                    disabled={mutationStatus === "saving"}
                    onChange={(event) => toggleResolved(viewBeat.id, event.target.checked)}
                  />
                  Resolved
                </label>
              ) : null}
            </div>
          ) : (
            <p className="play-muted">This Runbook has no authored Beats.</p>
          )}
          <button
            type="button"
            className="play-scene-step"
            aria-label="Next beat"
            disabled={!canNextMoment}
            onClick={focusNextMoment}
          >
            Next
          </button>
          {beats.length > 1 ? (
            <label className="play-scene-picker">
              Jump to beat
              <select
                aria-label="Jump to beat"
                value={viewBeat?.id ?? ""}
                onChange={(event) => {
                  const entry = beats.find((item) => item.beat.id === event.target.value);
                  if (entry) focusBeat(entry);
                }}
              >
                {beats.map((entry, index) => (
                  <option key={entry.beat.id} value={entry.beat.id}>
                    Beat {index + 1} / {beats.length} · {entry.beat.title}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </nav>

        {viewBeat ? (
          <>
            {sceneListings.length > 0 ? (
              <nav className="play-beat-strip play-scene-strip" aria-label="Scenes" data-testid="play-scene-strip">
                <p className="play-strip-label">Scenes</p>
                <ul className="play-beat-chips">
                  {sceneListings.map((title, index) => {
                    const isFocused = focusedListingIndex === index;
                    const describedBy = listingDescriptorId(viewBeat.id, index);
                    return (
                      <li key={`${viewBeat.id}:${index}`}>
                        <button
                          type="button"
                          className="play-beat-chip"
                          aria-current={isFocused ? "true" : undefined}
                          aria-describedby={describedBy}
                          onClick={() => setViewSceneListing(index)}
                        >
                          {title}
                        </button>
                        <span id={describedBy} className="play-visually-hidden">
                          {isFocused ? "Focused." : ""}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </nav>
            ) : null}

            <article
              className="play-beat-stage"
              data-testid="focused-beat"
              aria-label="Focused Beat stage"
            >
              {hasRichBody(stageBodyDoc) ? (
                <ReadOnlyPlayDoc
                  content={stageBodyDoc}
                  documentKey={`${bindingKey}:beat:${viewBeat.id}`}
                  className="play-runbook-editor play-beat-body"
                  dataTestId="play-beat-editor"
                />
              ) : null}

              {(viewScene?.choices ?? []).map((choice) => (
                <div key={choice.id} className="play-choice">
                  <h4>{choice.title}</h4>
                  {hasRichBody(choice.bodyDoc) ? (
                    <ReadOnlyPlayDoc
                      content={choice.bodyDoc}
                      documentKey={`${bindingKey}:choice:${choice.id}`}
                      className="play-runbook-editor play-choice-body"
                      dataTestId={`play-choice-body-${choice.id}`}
                    />
                  ) : null}
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
                        {hasRichBody(option.bodyDoc) ? (
                          <ReadOnlyPlayDoc
                            content={option.bodyDoc}
                            documentKey={`${bindingKey}:option:${option.id}`}
                            className="play-runbook-editor play-option-body"
                            dataTestId={`play-option-body-${option.id}`}
                          />
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}

              {noteElementId && mutationsOpen ? (
                <details className="play-notes">
                  <summary>Notes</summary>
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
                </details>
              ) : null}
            </article>
          </>
        ) : null}
      </div>
      )}
    </section>
  );
}
