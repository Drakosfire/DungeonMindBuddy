import type {
  PlayRunManifestV2Edge,
  PlayRunProgress,
  PlayRunReferenceManifestV2,
} from "../../api/types";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import {
  indexPlayableStructureV2,
  type PlayableStructureIndexV2,
} from "../../tiptap/playable/playableStructureIndex";

export type AuthoredRelevance = "emphasized" | "de-emphasized" | "default";

export function playRunProgressIsEmpty(progress: PlayRunProgress): boolean {
  return (
    progress.current_scene_id == null
    && progress.current_beat_id == null
    && progress.resolved_beat_ids.length === 0
    && Object.keys(progress.selections).length === 0
    && Object.keys(progress.notes_by_element_id).length === 0
  );
}

/**
 * First spine Beat in pinned document order, else first Beat, else null.
 * Uses the structure index walk, never sealed manifest array order.
 */
export function deriveV2OpeningBeatId(structure: PlayableStructureIndexV2): string | null {
  const spine = structure.beats.find((beat) => beat.beatKind === "spine");
  if (spine) return spine.beatId;
  return structure.beatOrder[0] ?? null;
}

export function deriveV2OpeningBeatIdFromMarkdown(markdown: string): string | null {
  const imported = markdownToTiptapDoc(markdown);
  const indexed = indexPlayableStructureV2(imported.doc);
  if (indexed.status !== "ready") return null;
  return deriveV2OpeningBeatId(indexed.index);
}

export function v2SeedProgress(openingBeatId: string): PlayRunProgress {
  return {
    current_beat_id: openingBeatId,
    current_scene_id: null,
    resolved_beat_ids: [],
    selections: {},
    notes_by_element_id: {},
  };
}

function v2MembershipKey(kind: string, id: string, parentA = "", parentB = ""): string {
  return [kind, id, parentA, parentB].join("\0");
}

function targetKindFromId(targetId: string): string {
  const idx = targetId.indexOf(":");
  return idx === -1 ? "" : targetId.slice(0, idx);
}

function sameKeySet(left: Set<string>, right: Set<string>): boolean {
  if (left.size !== right.size) return false;
  for (const key of left) {
    if (!right.has(key)) return false;
  }
  return true;
}

export function compareV2Membership(
  structure: PlayableStructureIndexV2,
  manifest: PlayRunReferenceManifestV2,
): string | null {
  const structureBeats = new Set(
    structure.beats.map((beat) => v2MembershipKey("beat", beat.beatId, beat.beatKind ?? "")),
  );
  const manifestBeats = new Set(
    manifest.beats.map((beat) => v2MembershipKey("beat", beat.beat_id, beat.beat_kind ?? "")),
  );
  if (!sameKeySet(structureBeats, manifestBeats)) {
    return "client v2 structure and sealed manifest disagree on Beat kind or membership";
  }

  const structureScenes = new Set(
    structure.scenes.map((scene) => v2MembershipKey("scene", scene.sceneId, scene.beatId)),
  );
  const manifestScenes = new Set(
    manifest.scenes.map((scene) => v2MembershipKey("scene", scene.scene_id, scene.beat_id)),
  );
  if (!sameKeySet(structureScenes, manifestScenes)) {
    return "client v2 structure and sealed manifest disagree on Playable membership";
  }

  const structureChoices = new Set(
    structure.choices.map((choice) => (
      v2MembershipKey("choice", choice.choiceId, choice.beatId, choice.sceneId ?? "")
    )),
  );
  const manifestChoices = new Set(
    manifest.choices.map((choice) => (
      v2MembershipKey("choice", choice.choice_id, choice.beat_id, choice.scene_id ?? "")
    )),
  );
  if (!sameKeySet(structureChoices, manifestChoices)) {
    return "client v2 structure and sealed manifest disagree on Playable membership";
  }

  const structureOptions = new Set(
    structure.options.map((option) => v2MembershipKey("option", option.optionId, option.choiceId)),
  );
  const manifestOptions = new Set(
    manifest.options.map((option) => v2MembershipKey("option", option.option_id, option.choice_id)),
  );
  if (!sameKeySet(structureOptions, manifestOptions)) {
    return "client v2 structure and sealed manifest disagree on Playable membership";
  }

  const structureEdges = new Set<string>();
  for (const option of structure.options) {
    for (const target of option.activates) {
      structureEdges.add(["edge", "activate", option.optionId, targetKindFromId(target), target].join("\0"));
    }
    for (const target of option.suppresses) {
      structureEdges.add(["edge", "suppress", option.optionId, targetKindFromId(target), target].join("\0"));
    }
  }
  const manifestEdges = new Set(
    manifest.edges.map((edge) => (
      ["edge", edge.effect, edge.option_id, edge.target_kind, edge.target_id].join("\0")
    )),
  );
  if (!sameKeySet(structureEdges, manifestEdges)) {
    return "client v2 structure and sealed manifest disagree on authored transition edges";
  }
  return null;
}

/**
 * Derived projection state. Never persisted. Activation wins suppression.
 * Targets with neither edge remain default. Membership is not removed.
 */
export function deriveAuthoredRelevance(
  edges: readonly PlayRunManifestV2Edge[],
  selections: Readonly<Record<string, string>>,
  targetIds: readonly string[],
): Record<string, AuthoredRelevance> {
  const selectedOptions = new Set(Object.values(selections));
  const activated = new Set<string>();
  const suppressed = new Set<string>();
  for (const edge of edges) {
    if (!selectedOptions.has(edge.option_id)) continue;
    if (edge.effect === "activate") activated.add(edge.target_id);
    else suppressed.add(edge.target_id);
  }
  const relevance: Record<string, AuthoredRelevance> = {};
  for (const targetId of targetIds) {
    if (activated.has(targetId)) relevance[targetId] = "emphasized";
    else if (suppressed.has(targetId)) relevance[targetId] = "de-emphasized";
    else relevance[targetId] = "default";
  }
  return relevance;
}

export function v2RelevanceTargetIds(manifest: PlayRunReferenceManifestV2): string[] {
  return [
    ...manifest.beats.map((beat) => beat.beat_id),
    ...manifest.scenes.map((scene) => scene.scene_id),
  ];
}
