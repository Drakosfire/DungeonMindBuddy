import type { RefObject } from "react";

import type {
  NativeRunbookReadyV2,
  NativeRunbookSceneV2,
} from "../runbook/nativeRunbookProjection";
import { selectedOptionForChoice } from "./decisionInteractionModel";

export function sceneInAnyBeat(deck: NativeRunbookReadyV2, sceneId: string): NativeRunbookSceneV2 | null {
  for (const beat of deck.beats) {
    const scene = beat.scenes.find((entry) => entry.id === sceneId);
    if (scene) return scene;
  }
  return null;
}

export function PlaySceneOutline({
  deck,
  currentSceneId,
  inspectedSceneId,
  collapsed,
  onToggle,
  onInspect,
  toggleRef,
}: {
  deck: NativeRunbookReadyV2;
  currentSceneId: string | null;
  inspectedSceneId: string | null;
  collapsed: boolean;
  onToggle: () => void;
  onInspect: (scene: NativeRunbookSceneV2) => void;
  toggleRef: RefObject<HTMLButtonElement | null>;
}) {
  const currentBeat = deck.beats.find((beat) => beat.id === deck.currentBeatId);

  return (
    <aside
      className={`play-cockpit-rail play-outline${collapsed ? " is-collapsed" : ""}`}
      data-testid="play-beat-context"
    >
      <button
        type="button"
        className="play-rail-toggle"
        data-testid="play-beat-context-toggle"
        ref={toggleRef}
        aria-expanded={!collapsed}
        aria-controls="play-outline-body"
        aria-label={`${collapsed ? "Expand" : "Collapse"} Scene outline`}
        onClick={onToggle}
      >
        Outline
      </button>
      {collapsed ? null : (
        <div id="play-outline-body" className="play-rail-body" data-testid="play-outline-body">
          {currentBeat ? (
            <p className="play-outline-current-beat">
              <span>Current Beat</span>
              <strong>{currentBeat.title}</strong>
            </p>
          ) : null}
          <nav aria-label="Scenes in this Run" className="play-outline-groups">
            {deck.beats.map((beat) => (
              <section className="play-outline-group" key={beat.id} data-beat-id={beat.id}>
                <h2 data-testid={beat.id === deck.currentBeatId ? "play-beat-context-title" : undefined}>
                  {beat.title}
                </h2>
                {beat.scenes.length === 0 ? (
                  <p className="play-muted">No scenes</p>
                ) : (
                  <ul className="play-outline-scenes">
                    {beat.scenes.map((scene) => {
                      const isCurrent = scene.id === currentSceneId;
                      const isInspected = scene.id === inspectedSceneId && !isCurrent;
                      return (
                        <li
                          key={scene.id}
                          data-testid={isCurrent ? "play-current-scene" : undefined}
                          data-current={isCurrent ? "true" : "false"}
                        >
                          <button
                            type="button"
                            className="play-outline-scene"
                            data-testid="play-outline-scene"
                            data-scene-id={scene.id}
                            data-current={isCurrent ? "true" : "false"}
                            data-inspecting={isInspected ? "true" : "false"}
                            aria-current={isCurrent ? "location" : undefined}
                            aria-pressed={isInspected}
                            onClick={() => onInspect(scene)}
                          >
                            <span className="play-outline-scene-title">{scene.title}</span>
                            <span className="play-outline-scene-state">
                              {isCurrent ? "Current" : isInspected ? "Viewing" : ""}
                            </span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </section>
            ))}
          </nav>
        </div>
      )}
    </aside>
  );
}

export function PlayRecordedOutcomes({
  deck,
  collapsed,
  onToggle,
  onInspect,
}: {
  deck: NativeRunbookReadyV2;
  collapsed: boolean;
  onToggle: () => void;
  onInspect: (scene: NativeRunbookSceneV2) => void;
}) {
  const selections = deck.run.progress.selections;
  const decisions = deck.beats.flatMap((beat) => beat.choices.flatMap((choice) => {
    const option = selectedOptionForChoice(choice, selections);
    return option ? [{ beat, choice, option }] : [];
  }));
  const sceneNotes = deck.beats.flatMap((beat) => beat.scenes.flatMap((scene) => {
    const note = deck.run.progress.notes_by_element_id[scene.id]?.trim();
    return note ? [{ beat, scene, note }] : [];
  }));

  return (
    <aside
      className={`play-cockpit-rail play-recorded-outcomes${collapsed ? " is-collapsed" : ""}`}
      data-testid="play-at-a-glance"
    >
      <button
        type="button"
        className="play-rail-toggle"
        data-testid="play-at-a-glance-toggle"
        aria-expanded={!collapsed}
        aria-controls="play-recorded-outcomes-body"
        aria-label={`${collapsed ? "Expand" : "Collapse"} Recorded outcomes`}
        onClick={onToggle}
      >
        {collapsed ? "Outcomes" : "Recorded outcomes"}
      </button>
      {collapsed ? null : (
        <div id="play-recorded-outcomes-body" className="play-rail-body" data-testid="play-recorded-outcomes-body">
          <p className="play-outcomes-caveat">Saved direction in this Run</p>
          <section aria-labelledby="play-recorded-decisions-heading">
            <h2 id="play-recorded-decisions-heading">Player choices</h2>
            {decisions.length === 0 ? (
              <p className="play-muted" data-testid="play-recorded-choices-empty">No choices recorded yet.</p>
            ) : (
              <ol className="play-outcome-list" data-testid="play-recorded-choices">
                {decisions.map(({ beat, choice, option }) => {
                  const scene = choice.sceneId ? sceneInAnyBeat(deck, choice.sceneId) : null;
                  return (
                    <li key={choice.id} data-choice-id={choice.id}>
                      <span className="play-outcome-label">{choice.title}</span>
                      <strong>{option.title}</strong>
                      <span className="play-outcome-context">{scene?.title ?? beat.title}</span>
                      {scene ? (
                        <button type="button" onClick={() => onInspect(scene)}>
                          Open scene
                        </button>
                      ) : null}
                    </li>
                  );
                })}
              </ol>
            )}
          </section>
          <section aria-labelledby="play-recorded-notes-heading">
            <h2 id="play-recorded-notes-heading">Scene notes</h2>
            {sceneNotes.length === 0 ? (
              <p className="play-muted" data-testid="play-recorded-notes-empty">No scene notes saved yet.</p>
            ) : (
              <ul className="play-outcome-list" data-testid="play-recorded-notes">
                {sceneNotes.map(({ beat, scene, note }) => (
                  <li key={scene.id} data-scene-id={scene.id}>
                    <span className="play-outcome-context">{beat.title}</span>
                    <button type="button" className="play-outcome-scene" onClick={() => onInspect(scene)}>
                      {scene.title}
                    </button>
                    <p>{note}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </aside>
  );
}
