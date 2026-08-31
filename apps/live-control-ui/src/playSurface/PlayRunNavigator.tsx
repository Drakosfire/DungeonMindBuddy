import { useMemo } from "react";

import { buildSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import {
  SurfaceContextAction,
  useOptionalSurfaceContext,
  useSurfaceContextContribution,
} from "../surfaceInteraction/contextHost";
import type {
  NativeRunbookBeatV2,
  NativeRunbookSceneV2,
} from "./runbook/nativeRunbookProjection";

export interface PlayRunNavigatorProps {
  instanceId: string;
  beats: readonly NativeRunbookBeatV2[];
  currentBeatId: string;
  scenes: readonly NativeRunbookSceneV2[];
  currentSceneId: string | null;
  inspectingSceneId: string | null;
  beatSelectionLocked: boolean;
  onSelectBeat: (beat: NativeRunbookBeatV2) => void;
  onInspectScene: (scene: NativeRunbookSceneV2) => void;
  onShowCurrent: () => void;
  onStartNewRun?: () => void;
}

function relevanceSuffix(relevance: NativeRunbookSceneV2["relevance"] | NativeRunbookBeatV2["relevance"]): string {
  if (relevance === "emphasized") return " · emphasized";
  if (relevance === "de-emphasized") return " · de-emphasized";
  return "";
}

function PlayRunNavigatorBound({
  instanceId,
  beats,
  currentBeatId,
  scenes,
  currentSceneId,
  inspectingSceneId,
  beatSelectionLocked,
  onSelectBeat,
  onInspectScene,
  onShowCurrent,
  onStartNewRun,
}: PlayRunNavigatorProps) {
  const surfaceIdentity = useMemo(
    () =>
      buildSurfaceInteractionIdentity({
        surfaceId: "play",
        instanceParts: ["play", instanceId, "navigator"],
      }),
    [instanceId],
  );

  const content = useMemo(
    () => (
      <div className="play-run-navigator" data-testid="play-run-navigator">
        <div className="play-run-navigator__rows">
          <div className="play-run-navigator__row">
            <span className="play-run-navigator__label">Beats</span>
            {beats.length === 0 ? (
              <span className="play-run-navigator__empty" data-testid="play-chrome-beats-empty">
                None in this Run
              </span>
            ) : (
              <div className="play-run-navigator__items" data-testid="play-chrome-beats">
                {beats.map((beat) => {
                  const isCurrent = beat.id === currentBeatId;
                  return (
                    <SurfaceContextAction
                      key={beat.id}
                      data-testid="play-chrome-beat"
                      data-beat-id={beat.id}
                      data-beat-kind={beat.beatKind ?? undefined}
                      title={beat.beatKind ? `${beat.title} (${beat.beatKind})` : beat.title}
                      data-current={isCurrent ? "true" : "false"}
                      aria-current={isCurrent ? "true" : undefined}
                      aria-label={isCurrent ? `${beat.title}, current Beat` : `Go to ${beat.title}`}
                      disabled={!isCurrent && beatSelectionLocked}
                      onClick={() => onSelectBeat(beat)}
                    >
                      {beat.title}
                      {relevanceSuffix(beat.relevance)}
                    </SurfaceContextAction>
                  );
                })}
              </div>
            )}
          </div>
          <div className="play-run-navigator__row">
            <span className="play-run-navigator__label">Scenes</span>
            {scenes.length === 0 ? (
              <span className="play-run-navigator__empty" data-testid="play-chrome-scenes-empty">
                None in this Beat
              </span>
            ) : (
              <div className="play-run-navigator__items" data-testid="play-chrome-scenes">
                {scenes.map((scene) => {
                  const isCurrent = scene.id === currentSceneId;
                  return (
                    <SurfaceContextAction
                      key={scene.id}
                      data-testid="play-chrome-scene"
                      data-scene-id={scene.id}
                      data-current={isCurrent ? "true" : "false"}
                      aria-current={isCurrent ? "true" : undefined}
                      aria-pressed={inspectingSceneId === scene.id}
                      aria-label={isCurrent ? `${scene.title}, current Scene` : `Inspect ${scene.title}`}
                      onClick={() => {
                        if (isCurrent) {
                          onShowCurrent();
                          return;
                        }
                        onInspectScene(scene);
                      }}
                    >
                      {scene.title}
                      {relevanceSuffix(scene.relevance)}
                    </SurfaceContextAction>
                  );
                })}
              </div>
            )}
          </div>
        </div>
        {onStartNewRun ? (
          <div className="play-run-navigator__session">
            <SurfaceContextAction data-testid="play-start-new-run" onClick={onStartNewRun}>
              Start New Run
            </SurfaceContextAction>
          </div>
        ) : null}
      </div>
    ),
    [
      beats,
      currentBeatId,
      scenes,
      currentSceneId,
      inspectingSceneId,
      beatSelectionLocked,
      onSelectBeat,
      onInspectScene,
      onShowCurrent,
      onStartNewRun,
    ],
  );

  useSurfaceContextContribution({
    id: "play-run",
    order: 10,
    surfaceIdentity,
    content,
  });

  return null;
}

export function PlayRunNavigator(props: PlayRunNavigatorProps) {
  const store = useOptionalSurfaceContext();
  if (store == null) return null;
  return <PlayRunNavigatorBound {...props} />;
}
