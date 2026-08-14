import "./beats.css";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { getPlayRunState, putPlayRunState } from "../../api/liveApi";
import type { PlayRunStateDocument } from "../../api/types";
import { useAgentInteraction } from "../../agentInteraction/useAgentInteraction";
import { appendLensQueryToHref } from "../../graphLens/sessionCampaignContext";
import {
  playBeatsFocusFromSearch,
  playPanelHref,
  type PlayPanelId,
} from "../playPanels";
import { buildPlayLocalGraphReferenceResolution } from "../reference/buildPlayLocalGraphReference";
import {
  OF_CONKS_HEMPHOLM_RUN_ID,
  OF_CONKS_HEMPHOLM_SPINE,
  beatById,
  sceneById,
  visibleScenesForBranch,
  type AdventureBeat,
  type AdventureScene,
  type BeatChip,
} from "./ofConksHempholmBeats";

const SAVE_DEBOUNCE_MS = 400;

function emptyRunState(runId: string): PlayRunStateDocument {
  return {
    schema_version: "dmb_play_run_state_v1",
    run_id: runId,
    campaign_id: "of-conks-cons",
    adventure_id: "hempholm",
    updated_at: "",
    current_scene_id: "hook",
    branch: { hook: "hill", aftermath: null },
    resolved_beat_ids: [],
    scene_notes: {},
  };
}

function SceneDeckNav({
  scenes,
  currentSceneId,
  onSelect,
}: {
  scenes: AdventureScene[];
  currentSceneId: string;
  onSelect: (sceneId: string) => void;
}) {
  const index = scenes.findIndex((s) => s.id === currentSceneId);
  const prev = index > 0 ? scenes[index - 1] : null;
  const next = index >= 0 && index < scenes.length - 1 ? scenes[index + 1] : null;

  return (
    <nav className="beats-deck-nav" aria-label="Scene deck">
      <div className="beats-deck-nav__stepper">
        <button
          type="button"
          className="beats-deck-nav__step"
          disabled={!prev}
          onClick={() => prev && onSelect(prev.id)}
        >
          ← Prev
        </button>
        <span className="beats-deck-nav__position">
          Scene {Math.max(index + 1, 1)} / {scenes.length}
        </span>
        <button
          type="button"
          className="beats-deck-nav__step"
          disabled={!next}
          onClick={() => next && onSelect(next.id)}
        >
          Next →
        </button>
      </div>
      <ol className="beats-deck-nav__list">
        {scenes.map((scene) => {
          const active = scene.id === currentSceneId;
          return (
            <li key={scene.id}>
              <button
                type="button"
                className={
                  active
                    ? "beats-deck-nav__scene beats-deck-nav__scene--active"
                    : "beats-deck-nav__scene"
                }
                aria-current={active ? "step" : undefined}
                onClick={() => onSelect(scene.id)}
              >
                {scene.title}
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function BeatTopStrip({
  beats,
  resolvedIds,
  selectedBeatId,
  onSelectBeat,
  onToggleResolved,
}: {
  beats: AdventureBeat[];
  resolvedIds: ReadonlySet<string>;
  selectedBeatId: string | null;
  onSelectBeat: (beatId: string) => void;
  onToggleResolved: (beatId: string, resolved: boolean) => void;
}) {
  return (
    <nav className="beats-strip" aria-label="Beats">
      <span className="beats-strip__label">Beats</span>
      <ul className="beats-strip__list">
        {beats.map((beat) => {
          const resolved = resolvedIds.has(beat.id);
          const selected = selectedBeatId === beat.id;
          return (
            <li
              key={beat.id}
              className={
                selected
                  ? "beats-strip__item beats-strip__item--selected"
                  : "beats-strip__item"
              }
            >
              <label className="beats-strip__resolve">
                <input
                  type="checkbox"
                  checked={resolved}
                  aria-label={`Resolved: ${beat.title}`}
                  onChange={(event) => onToggleResolved(beat.id, event.target.checked)}
                />
              </label>
              <button
                type="button"
                className="beats-strip__beat"
                data-beat-kind={beat.kind}
                onClick={() => onSelectBeat(beat.id)}
              >
                <span className="beats-strip__kind">{beat.kind}</span>
                <span className="beats-strip__title">{beat.title}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

function ChipButtons({
  chips,
  onOpen,
}: {
  chips: BeatChip[];
  onOpen: (chip: BeatChip) => void;
}) {
  if (!chips.length) return null;
  return (
    <ul className="beats-chip-list">
      {chips.map((chip) => (
        <li key={chip.nodeId}>
          <button
            type="button"
            className="beats-chip"
            onClick={() => onOpen(chip)}
          >
            {chip.label}
          </button>
        </li>
      ))}
    </ul>
  );
}

/**
 * Play → Beats: Of Conks Hempholm scene deck with top beat strip and wide detail stage.
 */
export function BeatsPanel({
  search = typeof window !== "undefined" ? window.location.search : null,
}: {
  search?: string | null;
} = {}) {
  const spine = OF_CONKS_HEMPHOLM_SPINE;
  const runId = OF_CONKS_HEMPHOLM_RUN_ID;
  const { openGraphReference } = useAgentInteraction();

  const [runState, setRunState] = useState<PlayRunStateDocument>(() => emptyRunState(runId));
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [selectedBeatId, setSelectedBeatId] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const saveTimer = useRef<number | null>(null);
  const latestRef = useRef(runState);
  const focusAppliedRef = useRef(false);
  latestRef.current = runState;

  useEffect(() => {
    let cancelled = false;
    getPlayRunState(runId)
      .then((doc) => {
        if (cancelled) return;
        setRunState(doc);
        setHydrated(true);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoadError(err instanceof Error ? err.message : "Failed to load run state");
        setHydrated(true);
      });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  const scheduleSave = useCallback((next: PlayRunStateDocument) => {
    setRunState(next);
    latestRef.current = next;
    if (saveTimer.current != null) window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(() => {
      putPlayRunState(runId, latestRef.current)
        .then((saved) => {
          setSaveError(null);
          setRunState(saved);
          latestRef.current = saved;
        })
        .catch((err: unknown) => {
          setSaveError(err instanceof Error ? err.message : "Failed to save run state");
        });
    }, SAVE_DEBOUNCE_MS);
  }, [runId]);

  useEffect(() => {
    return () => {
      if (saveTimer.current != null) window.clearTimeout(saveTimer.current);
    };
  }, []);

  useEffect(() => {
    if (!hydrated || focusAppliedRef.current) return;
    const { beatId, nodeId } = playBeatsFocusFromSearch(search);
    if (!beatId && !nodeId) {
      focusAppliedRef.current = true;
      return;
    }
    focusAppliedRef.current = true;

    if (beatId) {
      const found = beatById(spine, beatId);
      if (found) {
        const next = { ...latestRef.current };
        if (found.scene.requiresAftermath) {
          next.branch = { ...next.branch, aftermath: found.scene.requiresAftermath };
        }
        next.current_scene_id = found.scene.id;
        scheduleSave(next);
        setSelectedBeatId(found.beat.id);
      }
    }

    if (nodeId) {
      const resolution = buildPlayLocalGraphReferenceResolution(nodeId);
      if (resolution) {
        openGraphReference({
          resolution,
          projectionState: "ready",
          glanceOnly: false,
        });
      }
    }
  }, [hydrated, openGraphReference, scheduleSave, search, spine]);

  const visibleScenes = useMemo(
    () => visibleScenesForBranch(spine, runState.branch),
    [spine, runState.branch],
  );

  const currentScene =
    visibleScenes.find((s) => s.id === runState.current_scene_id)
    ?? visibleScenes[0]
    ?? sceneById(spine, "hook");

  useEffect(() => {
    if (!hydrated || !currentScene) return;
    if (runState.current_scene_id !== currentScene.id) {
      scheduleSave({ ...runState, current_scene_id: currentScene.id });
    }
    // Only realign when branch hides the current scene.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hydrated, currentScene?.id, visibleScenes.map((s) => s.id).join(",")]);

  const resolvedSet = useMemo(
    () => new Set(runState.resolved_beat_ids),
    [runState.resolved_beat_ids],
  );

  const selectedBeat =
    currentScene?.beats.find((b) => b.id === selectedBeatId)
    ?? null;

  const openChip = useCallback(
    (chip: BeatChip) => {
      const resolution = buildPlayLocalGraphReferenceResolution(chip.nodeId, chip.label);
      if (!resolution) return;
      openGraphReference({
        resolution,
        projectionState: "ready",
        glanceOnly: false,
      });
    },
    [openGraphReference],
  );

  function selectScene(sceneId: string) {
    setSelectedBeatId(null);
    scheduleSave({ ...runState, current_scene_id: sceneId });
  }

  function toggleResolved(beatId: string, resolved: boolean) {
    const next = new Set(runState.resolved_beat_ids);
    if (resolved) next.add(beatId);
    else next.delete(beatId);
    scheduleSave({ ...runState, resolved_beat_ids: [...next] });
  }

  function setNotes(value: string) {
    if (!currentScene) return;
    scheduleSave({
      ...runState,
      scene_notes: { ...runState.scene_notes, [currentScene.id]: value },
    });
  }

  function setAftermath(aftermath: "celebration" | "fire") {
    const nextScene =
      aftermath === "celebration" ? "aftermath-celebration" : "aftermath-fire";
    setSelectedBeatId(null);
    scheduleSave({
      ...runState,
      branch: { ...runState.branch, aftermath },
      current_scene_id: nextScene,
    });
  }

  function setHook(hook: "hill" | "alchemist" | "guild") {
    scheduleSave({
      ...runState,
      branch: { ...runState.branch, hook },
    });
  }

  if (!currentScene) {
    return (
      <div className="beats-panel" data-testid="beats-panel">
        <p className="beats-panel__status">No scenes available.</p>
      </div>
    );
  }

  const notes = runState.scene_notes[currentScene.id] ?? "";

  return (
    <div className="beats-panel" data-testid="beats-panel">
      <header className="beats-panel__header">
        <div>
          <p className="beats-panel__eyebrow">{spine.title}</p>
          <h2 className="beats-panel__title">{currentScene.title}</h2>
        </div>
        <div className="beats-panel__status-row">
          {!hydrated ? <span>Loading…</span> : null}
          {loadError ? <span role="alert">Load: {loadError}</span> : null}
          {saveError ? <span role="alert">Save: {saveError}</span> : null}
          {hydrated && !saveError ? (
            <span className="beats-panel__saved" data-testid="beats-save-ok">
              Notes persist to workspace
            </span>
          ) : null}
        </div>
      </header>

      <SceneDeckNav
        scenes={visibleScenes}
        currentSceneId={currentScene.id}
        onSelect={selectScene}
      />

      <section className="beats-scene beats-scene--context" aria-label="Scene">
        <p className="beats-scene__intent">{currentScene.intent}</p>
        {currentScene.clocks?.length ? (
          <ul className="beats-scene__clocks" aria-label="Clocks">
            {currentScene.clocks.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        ) : null}
        {currentScene.readAloud ? (
          <blockquote className="beats-scene__ra">{currentScene.readAloud}</blockquote>
        ) : null}
        {currentScene.gmNote ? (
          <p className="beats-scene__gm">
            <strong>GM:</strong> {currentScene.gmNote}
          </p>
        ) : null}
        {currentScene.chips?.length ? (
          <ChipButtons chips={currentScene.chips} onOpen={openChip} />
        ) : null}

        {currentScene.branchKind === "hook-pick" ? (
          <div className="beats-branch" aria-label="Hook choice">
            <span>Active hook:</span>
            {(["hill", "alchemist", "guild"] as const).map((hook) => (
              <button
                key={hook}
                type="button"
                className={
                  runState.branch.hook === hook
                    ? "beats-branch__btn beats-branch__btn--active"
                    : "beats-branch__btn"
                }
                onClick={() => setHook(hook)}
              >
                {hook}
              </button>
            ))}
          </div>
        ) : null}

        {currentScene.branchKind === "aftermath-pick" ? (
          <div className="beats-branch" aria-label="Aftermath choice">
            <span>After the surface tree:</span>
            <button
              type="button"
              className="beats-branch__btn"
              onClick={() => setAftermath("celebration")}
            >
              Celebration
            </button>
            <button
              type="button"
              className="beats-branch__btn"
              onClick={() => setAftermath("fire")}
            >
              Firefighting
            </button>
          </div>
        ) : null}

        <label className="beats-notes">
          <span className="beats-notes__label">Scene notes</span>
          <textarea
            className="beats-notes__input"
            data-testid="beats-scene-notes"
            rows={3}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Scratch notes for this scene (persisted)…"
          />
        </label>
      </section>

      <BeatTopStrip
        beats={currentScene.beats}
        resolvedIds={resolvedSet}
        selectedBeatId={selectedBeatId}
        onSelectBeat={setSelectedBeatId}
        onToggleResolved={toggleResolved}
      />

      <div className="beats-panel__stage">
        {selectedBeat ? (
          <section
            className="beats-detail beats-detail--stage"
            aria-label="Beat detail"
            data-testid="beats-detail"
          >
            <header className="beats-detail__header">
              <div>
                <p className="beats-detail__kind" data-beat-kind={selectedBeat.kind}>
                  {selectedBeat.kind}
                </p>
                <h3>{selectedBeat.title}</h3>
              </div>
              <button
                type="button"
                className="beats-detail__close"
                onClick={() => setSelectedBeatId(null)}
              >
                Close
              </button>
            </header>
            <div className="beats-detail__body">
              <p className="beats-detail__summary" data-testid="beats-detail-summary">
                {selectedBeat.summary}
              </p>

              <section className="beats-detail__section" aria-label="At the table">
                <h4 className="beats-detail__section-title">At the table</h4>
                <p className="beats-detail__at-table" data-testid="beats-detail-at-table">
                  {selectedBeat.atTable?.trim() || selectedBeat.summary}
                </p>
              </section>

              {selectedBeat.readAlouds?.length ? (
                <section className="beats-detail__section" aria-label="Read-aloud">
                  <h4 className="beats-detail__section-title">Read-aloud</h4>
                  {selectedBeat.readAlouds.map((ra) => (
                    <blockquote
                      key={`${ra.label ?? ""}:${ra.text.slice(0, 48)}`}
                      className="beats-scene__ra"
                      data-testid="beats-detail-read-aloud"
                    >
                      {ra.label?.trim() ? (
                        <p className="beats-detail__ra-label">{ra.label}</p>
                      ) : null}
                      {ra.text}
                    </blockquote>
                  ))}
                </section>
              ) : null}

              {selectedBeat.gmNote?.trim() ? (
                <section className="beats-detail__section" aria-label="GM note">
                  <h4 className="beats-detail__section-title">GM note</h4>
                  <p className="beats-scene__gm" data-testid="beats-detail-gm">
                    {selectedBeat.gmNote}
                  </p>
                </section>
              ) : null}

              {selectedBeat.rulesNow?.length ? (
                <section className="beats-detail__section" aria-label="Rules now">
                  <h4 className="beats-detail__section-title">Rules now</h4>
                  <ul className="beats-detail__rules" data-testid="beats-detail-rules">
                    {selectedBeat.rulesNow.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {selectedBeat.ifTheyWait?.length ? (
                <section className="beats-detail__section" aria-label="If they wait">
                  <h4 className="beats-detail__section-title">If they wait</h4>
                  <ul className="beats-detail__list">
                    {selectedBeat.ifTheyWait.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {selectedBeat.ifTheySucceed?.length ? (
                <section className="beats-detail__section" aria-label="If they succeed">
                  <h4 className="beats-detail__section-title">If they succeed</h4>
                  <ul className="beats-detail__list">
                    {selectedBeat.ifTheySucceed.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {selectedBeat.ifTheyFail?.length ? (
                <section className="beats-detail__section" aria-label="If they fail">
                  <h4 className="beats-detail__section-title">If they fail</h4>
                  <ul className="beats-detail__list">
                    {selectedBeat.ifTheyFail.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {selectedBeat.warnings?.length ? (
                <section
                  className="beats-detail__section beats-detail__section--warn"
                  aria-label="Warnings"
                >
                  <h4 className="beats-detail__section-title">Warnings</h4>
                  <ul className="beats-detail__warnings" data-testid="beats-detail-warnings">
                    {selectedBeat.warnings.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {selectedBeat.treasure?.length ? (
                <section className="beats-detail__section" aria-label="Treasure">
                  <h4 className="beats-detail__section-title">Treasure</h4>
                  <ul className="beats-detail__list" data-testid="beats-detail-treasure">
                    {selectedBeat.treasure.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {selectedBeat.chips?.length ? (
                <section className="beats-detail__section" aria-label="Open now">
                  <h4 className="beats-detail__section-title">Open now</h4>
                  <ChipButtons chips={selectedBeat.chips} onOpen={openChip} />
                </section>
              ) : null}

              {selectedBeat.toolLinks?.length ? (
                <section className="beats-detail__section" aria-label="Tools">
                  <h4 className="beats-detail__section-title">Tools</h4>
                  <ul className="beats-tool-list">
                    {selectedBeat.toolLinks.map((link) => (
                      <li key={`${link.panel}:${link.label}`}>
                        <a
                          className="beats-tool-link"
                          href={appendLensQueryToHref(playPanelHref(link.panel as PlayPanelId))}
                        >
                          {link.label}
                        </a>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </div>
          </section>
        ) : (
          <p className="beats-detail beats-detail--empty beats-detail--stage">
            Select a beat above for full details.
          </p>
        )}
      </div>
    </div>
  );
}
