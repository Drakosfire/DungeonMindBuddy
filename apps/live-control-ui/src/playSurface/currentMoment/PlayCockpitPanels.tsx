import { Contents } from "../../shared/Contents";
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

export function beatForScene(deck: NativeRunbookReadyV2, sceneId: string): NativeRunbookReadyV2["beats"][number] | null {
  return deck.beats.find((beat) => beat.scenes.some((scene) => scene.id === sceneId)) ?? null;
}

export function PlaySceneOutline({
  deck,
  currentSceneId,
  inspectedSceneId,
  collapsed,
  onToggle,
  onInspect,
  toggleRef,
  compact,
  returnFocusRef,
  fallbackFocusRef,
}: {
  deck: NativeRunbookReadyV2;
  currentSceneId: string | null;
  inspectedSceneId: string | null;
  collapsed: boolean;
  onToggle: () => void;
  onInspect: (scene: NativeRunbookSceneV2) => void;
  toggleRef: RefObject<HTMLButtonElement | null>;
  compact: boolean;
  returnFocusRef: RefObject<HTMLButtonElement | null>;
  fallbackFocusRef: RefObject<HTMLButtonElement | null>;
}) {
  const entries = deck.beats.flatMap(beat => beat.scenes.map(scene => ({
    ...scene, groupTitle: beat.title, current: scene.id === currentSceneId,
  })));
  return <aside className={`play-cockpit-rail play-outline${collapsed ? " is-collapsed" : ""}`}
    data-testid="play-beat-context">
    <Contents entries={entries} selectedId={inspectedSceneId ?? currentSceneId}
      visible={!collapsed} expanded={!collapsed} onExpandedChange={() => onToggle()}
      toggleRef={toggleRef} toggleTestId="play-beat-context-toggle"
      bodyId="play-outline-body" bodyTestId="play-outline-body" compact={compact}
      dismissFocusRef={compact ? returnFocusRef : toggleRef}
      fallbackDismissFocusRef={compact ? fallbackFocusRef : undefined}
      onSelect={id => { const scene = sceneInAnyBeat(deck, id); if (scene) onInspect(scene); }} />
  </aside>;
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
        aria-label={`${collapsed ? "Expand" : "Collapse"} saved choices and notes`}
        onClick={onToggle}
      >
        Saved choices &amp; notes
      </button>
      {collapsed ? null : (
        <div id="play-recorded-outcomes-body" className="play-rail-body" data-testid="play-recorded-outcomes-body">
          <p className="play-outcomes-caveat">Current Run state</p>
          <section aria-labelledby="play-recorded-decisions-heading">
            <h2 id="play-recorded-decisions-heading">Saved choices</h2>
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
