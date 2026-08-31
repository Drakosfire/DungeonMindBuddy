import type {
  NativeRunbookBeatV2,
  NativeRunbookChoiceV2,
  NativeRunbookOptionV2,
  NativeRunbookReadyV2,
} from "../runbook/nativeRunbookProjection";
import type { AuthoredRelevance } from "../runbook/v2RuntimeProjection";

export type DecisionSelectionPlan =
  | { kind: "noop" }
  | { kind: "invalid" }
  | { kind: "write"; selections: Record<string, string> };

export type TouchedRelevance = {
  targetId: string;
  title: string;
  relevance: AuthoredRelevance;
};

export function operableDecisions(
  beat: NativeRunbookBeatV2,
  currentSceneId: string | null,
): NativeRunbookChoiceV2[] {
  if (currentSceneId == null) {
    return beat.choices.filter((choice) => choice.sceneId == null);
  }
  return beat.choices.filter(
    (choice) => choice.sceneId == null || choice.sceneId === currentSceneId,
  );
}

export function optionInChoice(
  choice: NativeRunbookChoiceV2,
  optionId: string,
): NativeRunbookOptionV2 | null {
  return choice.options.find((option) => option.id === optionId) ?? null;
}

export function selectedOptionForChoice(
  choice: NativeRunbookChoiceV2,
  selections: Readonly<Record<string, string>>,
): NativeRunbookOptionV2 | null {
  const selectedId = selections[choice.id];
  if (selectedId == null) return null;
  return optionInChoice(choice, selectedId);
}

export function planSelectOption(
  selections: Readonly<Record<string, string>>,
  choice: NativeRunbookChoiceV2,
  optionId: string,
): DecisionSelectionPlan {
  if (optionInChoice(choice, optionId) == null) return { kind: "invalid" };
  if (selections[choice.id] === optionId) return { kind: "noop" };
  return {
    kind: "write",
    selections: {
      ...selections,
      [choice.id]: optionId,
    },
  };
}

export function planClearSelection(
  selections: Readonly<Record<string, string>>,
  choice: NativeRunbookChoiceV2,
): DecisionSelectionPlan {
  if (selections[choice.id] == null) return { kind: "noop" };
  const next = { ...selections };
  delete next[choice.id];
  return { kind: "write", selections: next };
}

export function humanTitleForTarget(deck: NativeRunbookReadyV2, targetId: string): string {
  for (const beat of deck.beats) {
    if (beat.id === targetId) return beat.title;
    const scene = beat.scenes.find((entry) => entry.id === targetId);
    if (scene) return scene.title;
  }
  return targetId;
}

export function selectedOptionTouchedRelevance(
  deck: NativeRunbookReadyV2,
  option: NativeRunbookOptionV2,
): TouchedRelevance[] {
  const seen = new Set<string>();
  const rows: TouchedRelevance[] = [];
  for (const edge of deck.manifest.edges) {
    if (edge.option_id !== option.id) continue;
    if (seen.has(edge.target_id)) continue;
    seen.add(edge.target_id);
    rows.push({
      targetId: edge.target_id,
      title: humanTitleForTarget(deck, edge.target_id),
      relevance: deck.relevanceByTargetId[edge.target_id] ?? "default",
    });
  }
  return rows;
}
