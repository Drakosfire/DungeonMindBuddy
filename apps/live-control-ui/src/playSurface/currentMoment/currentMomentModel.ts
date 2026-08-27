import type {
  NativeRunbookBeatV2,
  NativeRunbookReadyV2,
  NativeRunbookSceneV2,
} from "../runbook/nativeRunbookProjection";

export type PlayWorkspace =
  | { kind: "current" }
  | { kind: "scenes" }
  | { kind: "scene-inspect"; sceneId: string };

export type CurrentMoment =
  | {
    status: "ok";
    beat: NativeRunbookBeatV2;
    scene: NativeRunbookSceneV2 | null;
  }
  | {
    status: "incoherent";
    reason: string;
  };

export function resolveCurrentMoment(deck: NativeRunbookReadyV2): CurrentMoment {
  const beat = deck.beats.find((entry) => entry.id === deck.currentBeatId);
  if (beat == null) {
    return {
      status: "incoherent",
      reason: "current Beat is not in the admitted v2 projection",
    };
  }
  if (deck.currentSceneId == null) {
    return { status: "ok", beat, scene: null };
  }
  const scene = beat.scenes.find((entry) => entry.id === deck.currentSceneId);
  if (scene == null || scene.beatId !== beat.id) {
    return {
      status: "incoherent",
      reason: "current Scene is not a member of the current Beat",
    };
  }
  return { status: "ok", beat, scene };
}

export function sceneInCurrentBeat(
  deck: NativeRunbookReadyV2,
  sceneId: string,
): NativeRunbookSceneV2 | null {
  const moment = resolveCurrentMoment(deck);
  if (moment.status !== "ok") return null;
  const scene = moment.beat.scenes.find((entry) => entry.id === sceneId);
  if (scene == null || scene.beatId !== moment.beat.id) return null;
  return scene;
}
