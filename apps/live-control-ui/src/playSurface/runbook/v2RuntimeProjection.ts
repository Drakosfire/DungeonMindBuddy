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

export function compareV2Membership(
  structure: PlayableStructureIndexV2,
  manifest: PlayRunReferenceManifestV2,
): string | null {
  const fromStructure = new Set<string>([
    ...structure.beats.map((beat) => v2MembershipKey("beat", beat.beatId)),
    ...structure.scenes.map((scene) => v2MembershipKey("scene", scene.sceneId, scene.beatId)),
    ...structure.choices.map((choice) => (
      v2MembershipKey("choice", choice.choiceId, choice.beatId, choice.sceneId ?? "")
    )),
    ...structure.options.map((option) => v2MembershipKey("option", option.optionId, option.choiceId)),
  ]);
  const fromManifest = new Set<string>([
    ...manifest.beats.map((beat) => v2MembershipKey("beat", beat.beat_id)),
    ...manifest.scenes.map((scene) => v2MembershipKey("scene", scene.scene_id, scene.beat_id)),
    ...manifest.choices.map((choice) => (
      v2MembershipKey("choice", choice.choice_id, choice.beat_id, choice.scene_id ?? "")
    )),
    ...manifest.options.map((option) => v2MembershipKey("option", option.option_id, option.choice_id)),
  ]);
  if (fromStructure.size !== fromManifest.size) {
    return "client v2 structure and sealed manifest disagree on Playable membership";
  }
  for (const key of fromStructure) {
    if (!fromManifest.has(key)) {
      return "client v2 structure and sealed manifest disagree on Playable membership";
    }
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
