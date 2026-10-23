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
  | "validated"
  | "validated_with_warnings"
  | "validated_with_errors"
  | "validation_unavailable";

/**
 * Receipt-bearing outcomes only — maps Server receipt status:
 * valid → validated, warnings → validated_with_warnings, invalid → validated_with_errors.
 * Pending/unavailable never get an associated revision.
 */
export type ValidationReceiptStatus =
  | "validated"
  | "validated_with_warnings"
  | "validated_with_errors";

export type ValidationAttempt = "none" | "validating" | "unavailable";

export type StatblockEditorState = {
  sourceOutput: StatblockDefinitionV1_Output;
  baselineFingerprint: string;
  workingCopy: StatblockDefinitionV1_Input;
  stateRevision: number;
  undoStack: StatblockDefinitionV1_Input[];
  redoStack: StatblockDefinitionV1_Input[];
  /**
   * Revision bound to an authoritative validation receipt.
   * Set only for validated | validated_with_warnings | validated_with_errors.
   * Never set for validating or validation_unavailable.
   */
  validatedRevision: number | null;
  /** In-flight or failed-transport attempt without a receipt association. */
  validationAttempt: ValidationAttempt;
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

function isReceiptBearingUiStatus(status: ValidationUiStatus): status is ValidationReceiptStatus {
  return (
    status === "validated" ||
    status === "validated_with_warnings" ||
    status === "validated_with_errors"
  );
}

function deriveUiStatus(state: StatblockEditorState): ValidationUiStatus {
  if (
    state.validatedRevision !== null &&
    state.stateRevision === state.validatedRevision &&
    isReceiptBearingUiStatus(state.validationUiStatus)
  ) {
    return state.validationUiStatus;
  }
  if (state.validationAttempt === "validating") {
    return "validating";
  }
  if (state.validationAttempt === "unavailable") {
    return "validation_unavailable";
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

function clearAttemptAndAssociation(): Pick<
  StatblockEditorState,
  "validatedRevision" | "validationAttempt" | "validationUiStatus"
> {
  return {
    validatedRevision: null,
    validationAttempt: "none",
    validationUiStatus: "dirty_unvalidated",
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
    ...clearAttemptAndAssociation(),
  };
  next.validationUiStatus = deriveUiStatus(next);
  return next;
}

export function clearValidationAssociation(state: StatblockEditorState): StatblockEditorState {
  const next: StatblockEditorState = {
    ...state,
    validatedRevision: null,
    validationAttempt: "none",
  };
  next.validationUiStatus = deriveUiStatus(next);
  return next;
}

/** @deprecated Use clearValidationAssociation */
export const clearValidationEligibility = clearValidationAssociation;

/** Pending validate call — no receipt, no associated revision. */
export function beginValidationAttempt(state: StatblockEditorState): StatblockEditorState {
  return {
    ...state,
    validatedRevision: null,
    validationAttempt: "validating",
    validationUiStatus: "validating",
  };
}

/** Transport/dependency failure — retain working copy, no receipt association. */
export function markValidationUnavailable(state: StatblockEditorState): StatblockEditorState {
  return {
    ...state,
    validatedRevision: null,
    validationAttempt: "unavailable",
    validationUiStatus: "validation_unavailable",
  };
}

/**
 * Associate an authoritative Server receipt with the current working-copy revision.
 * Accepts clean valid, warnings, or invalid receipt outcomes — never validating or unavailable.
 */
export function markValidationAssociated(
  state: StatblockEditorState,
  uiStatus: ValidationReceiptStatus,
): StatblockEditorState {
  return {
    ...state,
    validatedRevision: state.stateRevision,
    validationAttempt: "none",
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
    validationAttempt: "none",
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

/** Mutates `defenses.armor_classes[primaryArmorClassIndex(defenses)].value` only. */
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

/** Maximum HP uses the same rounded dice average as authoritative validation. */
export function readHitPointsMax(hitPoints: StatblockDefinitionV1_Input["vitality"]["hit_points"]): number {
  if (hitPoints.method === "fixed") return hitPoints.fixed_value ?? 0;
  const formula = hitPoints.formula;
  return formula ? Math.floor(formula.count * (formula.die + 1) / 2) + (formula.modifier ?? 0) : 0;
}

export function setHitPointsMax(state: StatblockEditorState, value: number): StatblockEditorState {
  if (!Number.isFinite(value) || !Number.isInteger(value)) return state;
  const original = state.workingCopy.vitality.hit_points;
  if (original.method === "formula" && !original.formula) return state;
  return updateWorkingCopy(state, (current) => {
    const hitPoints = { ...current.vitality.hit_points };
    if (hitPoints.method === "fixed") {
      hitPoints.fixed_value = value;
    } else if (hitPoints.formula) {
      const formula = hitPoints.formula;
      hitPoints.formula = { ...formula, modifier: value - Math.floor(formula.count * (formula.die + 1) / 2) };
    }
    if (hitPoints.displayed_average != null) hitPoints.displayed_average = value;
    return { ...current, vitality: { ...current.vitality, hit_points: hitPoints } };
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
    ...clearAttemptAndAssociation(),
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
    ...clearAttemptAndAssociation(),
  };
  next.validationUiStatus = deriveUiStatus(next);
  return next;
}

export function getUiStatus(state: StatblockEditorState): ValidationUiStatus {
  return deriveUiStatus(state);
}

/** Protected identity fields excluding the dedicated `name` control. */
export function identityProtectedRemainder(
  identity: StatblockDefinitionV1_Input["identity"],
): Omit<StatblockDefinitionV1_Input["identity"], "name"> {
  const { name: _name, ...remainder } = identity;
  return remainder;
}
