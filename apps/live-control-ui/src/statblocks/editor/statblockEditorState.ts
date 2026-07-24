import type {
  AbilityName,
  StatblockDefinitionV1_Input,
  StatblockDefinitionV1_Output,
} from "../../contracts/dungeonbuddy-statblocks-v1/client";
import { definitionOutputToInput } from "./definitionOutputToInput";

export type ValidationUiStatus =
  | "clean_unvalidated"
  | "dirty_unvalidated"
  | "validating"
  | "validated_with_warnings"
  | "validated_with_errors"
  | "validation_unavailable";

export type StatblockEditorState = {
  sourceOutput: StatblockDefinitionV1_Output;
  baselineFingerprint: string;
  workingCopy: StatblockDefinitionV1_Input;
  stateRevision: number;
  undoStack: StatblockDefinitionV1_Input[];
  redoStack: StatblockDefinitionV1_Input[];
  /** Revision at which validation was last associated; session-only receipt. */
  validatedRevision: number | null;
  validationUiStatus: ValidationUiStatus;
};

function stableStringify(value: unknown): string {
  return JSON.stringify(value, (_key, current) => {
    if (current && typeof current === "object" && !Array.isArray(current)) {
      const sorted: Record<string, unknown> = {};
      for (const key of Object.keys(current as Record<string, unknown>).sort()) {
        sorted[key] = (current as Record<string, unknown>)[key];
      }
      return sorted;
    }
    return current;
  });
}

export function fingerprintDefinition(definition: StatblockDefinitionV1_Input): string {
  return stableStringify(definition);
}

export function getLocalFingerprint(state: StatblockEditorState): string {
  return fingerprintDefinition(state.workingCopy);
}

function isDirty(state: StatblockEditorState): boolean {
  return getLocalFingerprint(state) !== state.baselineFingerprint;
}

const PRESERVED_VALIDATION_UI: ValidationUiStatus[] = [
  "validating",
  "validated_with_warnings",
  "validated_with_errors",
  "validation_unavailable",
];

function deriveUiStatus(state: StatblockEditorState): ValidationUiStatus {
  if (
    state.validatedRevision !== null &&
    state.stateRevision === state.validatedRevision &&
    PRESERVED_VALIDATION_UI.includes(state.validationUiStatus)
  ) {
    return state.validationUiStatus;
  }
  return isDirty(state) ? "dirty_unvalidated" : "clean_unvalidated";
}

function cloneWorkingCopy(copy: StatblockDefinitionV1_Input): StatblockDefinitionV1_Input {
  return structuredClone(copy);
}

function pushUndo(state: StatblockEditorState, snapshot: StatblockDefinitionV1_Input): StatblockEditorState {
  return {
    ...state,
    undoStack: [...state.undoStack, cloneWorkingCopy(snapshot)],
    redoStack: [],
  };
}

function applyWorkingCopy(
  state: StatblockEditorState,
  nextWorkingCopy: StatblockDefinitionV1_Input,
  options?: { skipUndo?: boolean },
): StatblockEditorState {
  const withUndo = options?.skipUndo ? state : pushUndo(state, state.workingCopy);
  const next: StatblockEditorState = {
    ...withUndo,
    workingCopy: cloneWorkingCopy(nextWorkingCopy),
    stateRevision: state.stateRevision + 1,
    validatedRevision: null,
    validationUiStatus: "dirty_unvalidated",
  };
  next.validationUiStatus = deriveUiStatus(next);
  return next;
}

export function clearValidationAssociation(state: StatblockEditorState): StatblockEditorState {
  const next: StatblockEditorState = {
    ...state,
    validatedRevision: null,
    validationUiStatus: deriveUiStatus({ ...state, validatedRevision: null }),
  };
  return next;
}

/** @deprecated Use clearValidationAssociation */
export const clearValidationEligibility = clearValidationAssociation;

export function markValidationAssociated(
  state: StatblockEditorState,
  uiStatus: Exclude<ValidationUiStatus, "clean_unvalidated" | "dirty_unvalidated">,
): StatblockEditorState {
  return {
    ...state,
    validatedRevision: state.stateRevision,
    validationUiStatus: uiStatus,
  };
}

export function createEditorStateFromOutput(output: StatblockDefinitionV1_Output): StatblockEditorState {
  const workingCopy = definitionOutputToInput(output);
  const baselineFingerprint = fingerprintDefinition(workingCopy);
  return {
    sourceOutput: output,
    baselineFingerprint,
    workingCopy,
    stateRevision: 0,
    undoStack: [],
    redoStack: [],
    validatedRevision: null,
    validationUiStatus: "clean_unvalidated",
  };
}

export function updateWorkingCopy(
  state: StatblockEditorState,
  updater: (current: StatblockDefinitionV1_Input) => StatblockDefinitionV1_Input,
): StatblockEditorState {
  const draft = cloneWorkingCopy(state.workingCopy);
  const updated = updater(draft);
  return applyWorkingCopy(state, updated);
}

export function setIdentityName(state: StatblockEditorState, name: string): StatblockEditorState {
  return updateWorkingCopy(state, (current) => ({
    ...current,
    identity: {
      ...current.identity,
      name,
    },
  }));
}

export function setAbility(state: StatblockEditorState, ability: AbilityName, value: number): StatblockEditorState {
  return updateWorkingCopy(state, (current) => ({
    ...current,
    abilities: {
      ...current.abilities,
      [ability]: value,
    },
  }));
}

export function primaryArmorClassIndexForDisplay(defenses: StatblockDefinitionV1_Input["defenses"]): number {
  const defaultIndex = defenses.armor_classes.findIndex((entry) => entry.default);
  return defaultIndex >= 0 ? defaultIndex : 0;
}

function primaryArmorClassIndex(defenses: StatblockDefinitionV1_Input["defenses"]): number {
  return primaryArmorClassIndexForDisplay(defenses);
}

/** Mutates `defenses.armor_classes[primaryArmorClassIndex(defenses)]` (default entry, else index 0). */
export function setPrimaryArmorClassValue(state: StatblockEditorState, value: number): StatblockEditorState {
  return updateWorkingCopy(state, (current) => {
    const index = primaryArmorClassIndex(current.defenses);
    if (current.defenses.armor_classes.length === 0) {
      return current;
    }
    const armorClasses = current.defenses.armor_classes.map((entry, entryIndex) =>
      entryIndex === index ? { ...entry, value } : entry,
    );
    return {
      ...current,
      defenses: {
        ...current.defenses,
        armor_classes: armorClasses,
      },
    };
  });
}

export type HitPointsEditTarget = "displayed_average" | "fixed_value" | "formula_modifier";

export function resolveHitPointsEditTarget(hitPoints: StatblockDefinitionV1_Input["vitality"]["hit_points"]): HitPointsEditTarget {
  if (hitPoints.displayed_average !== null && hitPoints.displayed_average !== undefined) {
    return "displayed_average";
  }
  if (hitPoints.method === "fixed") {
    return "fixed_value";
  }
  return "formula_modifier";
}

export function setHitPointsMax(state: StatblockEditorState, value: number): StatblockEditorState {
  return updateWorkingCopy(state, (current) => {
    const hitPoints = { ...current.vitality.hit_points };
    const target = resolveHitPointsEditTarget(hitPoints);
    if (target === "displayed_average") {
      hitPoints.displayed_average = value;
    } else if (target === "fixed_value") {
      hitPoints.fixed_value = value;
    } else {
      const formula = hitPoints.formula ?? { count: 1, die: 6, modifier: 0 };
      hitPoints.formula = {
        ...formula,
        modifier: value,
      };
    }
    return {
      ...current,
      vitality: {
        hit_points: hitPoints,
      },
    };
  });
}

export function setRuleElementName(state: StatblockEditorState, elementKey: string, name: string): StatblockEditorState {
  return updateWorkingCopy(state, (current) => ({
    ...current,
    rule_elements: current.rule_elements.map((element) =>
      element.key === elementKey ? { ...element, name } : element,
    ),
  }));
}

export function setRuleElementRulesText(
  state: StatblockEditorState,
  elementKey: string,
  rulesText: string,
): StatblockEditorState {
  return updateWorkingCopy(state, (current) => ({
    ...current,
    rule_elements: current.rule_elements.map((element) =>
      element.key === elementKey ? { ...element, rules_text: rulesText } : element,
    ),
  }));
}

export function undo(state: StatblockEditorState): StatblockEditorState {
  if (state.undoStack.length === 0) {
    return state;
  }
  const previous = state.undoStack[state.undoStack.length - 1];
  const undoStack = state.undoStack.slice(0, -1);
  const next: StatblockEditorState = {
    ...state,
    workingCopy: cloneWorkingCopy(previous),
    undoStack,
    redoStack: [...state.redoStack, cloneWorkingCopy(state.workingCopy)],
    stateRevision: state.stateRevision + 1,
    validatedRevision: null,
    validationUiStatus: "dirty_unvalidated",
  };
  next.validationUiStatus = deriveUiStatus(next);
  return next;
}

export function redo(state: StatblockEditorState): StatblockEditorState {
  if (state.redoStack.length === 0) {
    return state;
  }
  const nextCopy = state.redoStack[state.redoStack.length - 1];
  const redoStack = state.redoStack.slice(0, -1);
  const next: StatblockEditorState = {
    ...state,
    workingCopy: cloneWorkingCopy(nextCopy),
    redoStack,
    undoStack: [...state.undoStack, cloneWorkingCopy(state.workingCopy)],
    stateRevision: state.stateRevision + 1,
    validatedRevision: null,
    validationUiStatus: "dirty_unvalidated",
  };
  next.validationUiStatus = deriveUiStatus(next);
  return next;
}

export function getUiStatus(state: StatblockEditorState): ValidationUiStatus {
  return deriveUiStatus(state);
}
