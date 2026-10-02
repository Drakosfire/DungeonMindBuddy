import { useState } from "react";
import type {
  AbilityName,
  AttackMechanic_Input,
  CompositeMechanic_Input,
  MovementEffect_Input,
  MovementMode_Input,
  MovementModeKind,
  PassiveMechanic_Input,
  PhaseTransitionMechanic_Input,
  RuleElement_Input,
  SaveEffectMechanic_Input,
  StatblockDefinitionV1_Output,
} from "../../contracts/dungeonbuddy-statblocks-v1/client";
import { ProtectedStructureBlock } from "./ProtectedStructureBlock";
import {
  createEditorStateFromOutput,
  getUiStatus,
  identityProtectedRemainder,
  primaryArmorClassIndexForDisplay,
  resolveHitPointsEditTarget,
  setAbility,
  setHitPointsMax,
  setIdentityName,
  setPrimaryArmorClassValue,
  setRuleElementName,
  setRuleElementRulesText,
  updateWorkingCopy,
  type StatblockEditorState,
} from "./statblockEditorState";
import "./StatblockDefinitionEditor.css";

const ABILITY_NAMES: AbilityName[] = [
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
  "charisma",
];

const MOVEMENT_MODE_KINDS: MovementModeKind[] = [
  "walk",
  "fly",
  "swim",
  "climb",
  "burrow",
  "hover",
  "special",
];

type DirectEffectMechanic =
  | CompositeMechanic_Input
  | AttackMechanic_Input
  | PassiveMechanic_Input
  | PhaseTransitionMechanic_Input
  | SaveEffectMechanic_Input;
type DirectEffect = NonNullable<CompositeMechanic_Input["effects"]>[number];
type MovementEffectField =
  | "effects"
  | "hit_effects"
  | "miss_effects"
  | "success_effects"
  | "failure_effects";
type MovementEffectCollection = {
  field: MovementEffectField;
  label: string;
  effects: DirectEffect[];
};

function movementEffectCollections(
  mechanic: RuleElement_Input["mechanic"],
): MovementEffectCollection[] {
  switch (mechanic.kind) {
    case "composite":
    case "passive":
    case "phase_transition":
      return [{ field: "effects", label: "effects", effects: mechanic.effects ?? [] }];
    case "attack":
      return [
        { field: "hit_effects", label: "hit effects", effects: mechanic.hit_effects ?? [] },
        { field: "miss_effects", label: "miss effects", effects: mechanic.miss_effects ?? [] },
      ];
    case "save_effect":
      return [
        {
          field: "success_effects",
          label: "success effects",
          effects: mechanic.success_effects ?? [],
        },
        {
          field: "failure_effects",
          label: "failure effects",
          effects: mechanic.failure_effects ?? [],
        },
      ];
    default:
      return [];
  }
}

function isMovementEffect(effect: DirectEffect): effect is MovementEffect_Input {
  return effect.kind === "movement" || "movement_mode_key" in effect;
}

function hasDirectMovementEffect(mechanic: RuleElement_Input["mechanic"]): boolean {
  return movementEffectCollections(mechanic).some((collection) =>
    collection.effects.some(isMovementEffect),
  );
}

function updateMovementMode(
  state: StatblockEditorState,
  index: number,
  update: (mode: MovementMode_Input) => MovementMode_Input,
): StatblockEditorState {
  return updateWorkingCopy(state, (current) => ({
    ...current,
    movement: {
      ...current.movement,
      modes: current.movement.modes.map((mode, modeIndex) =>
        modeIndex === index ? update(mode) : mode,
      ),
    },
  }));
}

function addMovementMode(state: StatblockEditorState): StatblockEditorState {
  return updateWorkingCopy(state, (current) => ({
    ...current,
    movement: {
      ...current.movement,
      modes: [
        ...current.movement.modes,
        { key: "", mode: "walk", distance: { value: 0, unit: "feet" }, qualifiers: [] },
      ],
    },
  }));
}

function removeMovementMode(state: StatblockEditorState, index: number): StatblockEditorState {
  return updateWorkingCopy(state, (current) => ({
    ...current,
    movement: {
      ...current.movement,
      modes: current.movement.modes.filter((_mode, modeIndex) => modeIndex !== index),
    },
  }));
}

function updateMovementEffectReference(
  state: StatblockEditorState,
  elementKey: string,
  field: MovementEffectField,
  effectIndex: number,
  movementModeKey: string,
): StatblockEditorState {
  return updateWorkingCopy(state, (current) => ({
    ...current,
    rule_elements: current.rule_elements.map((element) => {
      if (element.key !== elementKey) return element;
      const updateEffects = (effects: DirectEffect[] | undefined): DirectEffect[] =>
        (effects ?? []).map((effect, index) =>
          index === effectIndex && isMovementEffect(effect)
            ? { ...effect, movement_mode_key: movementModeKey }
            : effect,
        );
      const mechanic = element.mechanic;
      let updatedMechanic: DirectEffectMechanic | null = null;
      switch (mechanic.kind) {
        case "composite":
        case "passive":
        case "phase_transition":
          if (field === "effects") {
            updatedMechanic = { ...mechanic, effects: updateEffects(mechanic.effects) };
          }
          break;
        case "attack":
          updatedMechanic = {
            ...mechanic,
            hit_effects:
              field === "hit_effects" ? updateEffects(mechanic.hit_effects) : mechanic.hit_effects,
            miss_effects:
              field === "miss_effects" ? updateEffects(mechanic.miss_effects) : mechanic.miss_effects,
          };
          break;
        case "save_effect":
          updatedMechanic = {
            ...mechanic,
            success_effects:
              field === "success_effects"
                ? updateEffects(mechanic.success_effects)
                : mechanic.success_effects,
            failure_effects:
              field === "failure_effects"
                ? updateEffects(mechanic.failure_effects)
                : mechanic.failure_effects,
          };
          break;
      }
      if (!updatedMechanic) return element;
      return {
        ...element,
        mechanic: updatedMechanic,
      };
    }),
  }));
}

function updateMovementQualifier(
  state: StatblockEditorState,
  modeIndex: number,
  qualifierIndex: number,
  value: string,
): StatblockEditorState {
  return updateMovementMode(state, modeIndex, (mode) => ({
    ...mode,
    qualifiers: (mode.qualifiers ?? []).map((qualifier, index) =>
      index === qualifierIndex ? value : qualifier,
    ),
  }));
}

function addMovementQualifier(state: StatblockEditorState, modeIndex: number): StatblockEditorState {
  return updateMovementMode(state, modeIndex, (mode) => ({
    ...mode,
    qualifiers: [...(mode.qualifiers ?? []), ""],
  }));
}

function removeMovementQualifier(
  state: StatblockEditorState,
  modeIndex: number,
  qualifierIndex: number,
): StatblockEditorState {
  return updateMovementMode(state, modeIndex, (mode) => ({
    ...mode,
    qualifiers: (mode.qualifiers ?? []).filter((_qualifier, index) => index !== qualifierIndex),
  }));
}

export type StatblockDefinitionEditorProps = {
  output: StatblockDefinitionV1_Output;
  editorState?: StatblockEditorState;
  onEditorStateChange?: (state: StatblockEditorState) => void;
};

function readPrimaryArmorClassValue(defenses: StatblockEditorState["workingCopy"]["defenses"]): number {
  const index = primaryArmorClassIndexForDisplay(defenses);
  return defenses.armor_classes[index]?.value ?? 0;
}

function readHitPointsEditorValue(vitality: StatblockEditorState["workingCopy"]["vitality"]): number {
  const hitPoints = vitality.hit_points;
  const target = resolveHitPointsEditTarget(hitPoints);
  if (target === "displayed_average") {
    return hitPoints.displayed_average ?? 0;
  }
  if (target === "fixed_value") {
    return hitPoints.fixed_value ?? 0;
  }
  return hitPoints.formula?.modifier ?? 0;
}

/** Full defenses JSON for disclosure; primary AC value is also editable above. */
function defensesDisclosureValue(defenses: StatblockEditorState["workingCopy"]["defenses"]) {
  return defenses;
}

/** Full vitality JSON for disclosure; one HP scalar is also editable above. */
function vitalityDisclosureValue(vitality: StatblockEditorState["workingCopy"]["vitality"]) {
  return vitality;
}

function ruleElementProtectedStructure(
  element: StatblockEditorState["workingCopy"]["rule_elements"][number],
  order: number,
): Record<string, unknown> {
  const structure: Record<string, unknown> = {
    key: element.key,
    section: element.section,
    order,
    automation_support: element.automation_support,
  };
  if (element.summary !== undefined) {
    structure.summary = element.summary;
  }
  if (element.tags !== undefined) {
    structure.tags = element.tags;
  }
  return structure;
}

export function StatblockDefinitionEditor({
  output,
  editorState: controlledState,
  onEditorStateChange,
}: StatblockDefinitionEditorProps) {
  const [uncontrolledState, setUncontrolledState] = useState(() => createEditorStateFromOutput(output));
  const state = controlledState ?? uncontrolledState;
  const workingCopy = state.workingCopy;
  const uiStatus = getUiStatus(state);

  const commit = (next: StatblockEditorState) => {
    if (controlledState !== undefined) {
      onEditorStateChange?.(next);
      return;
    }
    setUncontrolledState(next);
    onEditorStateChange?.(next);
  };

  const acIndex = primaryArmorClassIndexForDisplay(workingCopy.defenses);
  const primaryAcEntry = workingCopy.defenses.armor_classes[acIndex];
  const primaryAcLabel = primaryAcEntry?.default
    ? "Primary AC value (default armor_classes entry)"
    : "Primary AC value (armor_classes[0]; no default flagged)";
  const hpTarget = resolveHitPointsEditTarget(workingCopy.vitality.hit_points);

  return (
    <div className="statblock-definition-editor" data-testid="statblock-definition-editor">
      <p className="statblock-definition-editor__disclosure">
        Session-only working copy. Changes are unsaved and will be lost on refresh.
      </p>
      <p className="statblock-definition-editor__status" data-testid="editor-ui-status">
        Status: {uiStatus}
      </p>

      <section className="statblock-definition-editor__section" aria-label="Identity">
        <h3>Identity</h3>
        <label>
          Name
          <input
            aria-label="Creature name"
            value={workingCopy.identity.name}
            onChange={(event) => commit(setIdentityName(state, event.target.value))}
          />
        </label>
      </section>

      <section className="statblock-definition-editor__section" aria-label="Abilities">
        <h3>Ability scores</h3>
        <div className="statblock-definition-editor__grid">
          {ABILITY_NAMES.map((ability) => (
            <label key={ability}>
              {ability}
              <input
                type="number"
                aria-label={`${ability} score`}
                value={workingCopy.abilities[ability]}
                onChange={(event) => commit(setAbility(state, ability, Number(event.target.value)))}
              />
            </label>
          ))}
        </div>
      </section>

      <section className="statblock-definition-editor__section" aria-label="Defenses">
        <h3>Armor class</h3>
        <label>
          {primaryAcLabel}
          <input
            type="number"
            aria-label="Primary armor class"
            value={readPrimaryArmorClassValue(workingCopy.defenses)}
            onChange={(event) => commit(setPrimaryArmorClassValue(state, Number(event.target.value)))}
          />
        </label>
      </section>

      <section className="statblock-definition-editor__section" aria-label="Vitality">
        <h3>Hit points</h3>
        <label>
          Hit points (mutates vitality.hit_points.{hpTarget})
          <input
            type="number"
            aria-label="Hit points"
            value={readHitPointsEditorValue(workingCopy.vitality)}
            onChange={(event) => commit(setHitPointsMax(state, Number(event.target.value)))}
          />
        </label>
      </section>

      <section className="statblock-definition-editor__section" aria-label="Rule elements">
        <h3>Rule elements</h3>
        <p>
          Movement references use the exact key of a movement mode in this definition. Changing a
          mode kind never changes its key or rewrites a reference.
        </p>
        {workingCopy.rule_elements.map((element) => (
          <article key={element.key} className="statblock-definition-editor__rule-element">
            <label>
              Element name ({element.key})
              <input
                aria-label={`Rule element name ${element.key}`}
                value={element.name}
                onChange={(event) => commit(setRuleElementName(state, element.key, event.target.value))}
              />
            </label>
            <label>
              Rules text
              <textarea
                aria-label={`Rule element rules text ${element.key}`}
                value={element.rules_text}
                onChange={(event) => commit(setRuleElementRulesText(state, element.key, event.target.value))}
              />
            </label>
            {movementEffectCollections(element.mechanic).flatMap((collection) =>
              collection.effects.map((effect, effectIndex) =>
                isMovementEffect(effect) ? (
                  <label key={`movement-reference-${collection.field}-${effectIndex}`}>
                    Movement mode reference for {element.key} {collection.label} {effectIndex + 1}
                    <input
                      aria-label={`Movement mode reference ${element.key} ${collection.label} ${effectIndex}`}
                      value={effect.movement_mode_key ?? ""}
                      onChange={(event) =>
                        commit(
                          updateMovementEffectReference(
                            state,
                            element.key,
                            collection.field,
                            effectIndex,
                            event.currentTarget.value,
                          ),
                        )
                      }
                    />
                  </label>
                ) : null,
              ),
            )}
          </article>
        ))}
      </section>

      <section className="statblock-definition-editor__section" aria-label="Movement modes">
        <h3>Movement modes</h3>
        <p>Each key is local to this definition. Mode kind and key are separate values.</p>
        {workingCopy.movement.modes.map((mode, index) => (
          <fieldset key={index} className="statblock-definition-editor__rule-element">
            <legend>Movement mode {index + 1}</legend>
            <div className="statblock-definition-editor__grid">
              <label>
                Local key
                <input
                  aria-label={`Movement mode key ${index}`}
                  value={mode.key}
                  onChange={(event) =>
                    commit(updateMovementMode(state, index, (current) => ({
                      ...current,
                      key: event.currentTarget.value,
                    })))
                  }
                />
              </label>
              <label>
                Mode kind
                <select
                  aria-label={`Movement mode kind ${index}`}
                  value={mode.mode}
                  onChange={(event) => {
                    const nextMode = MOVEMENT_MODE_KINDS.find(
                      (kind) => kind === event.currentTarget.value,
                    );
                    if (nextMode) {
                      commit(updateMovementMode(state, index, (current) => ({
                        ...current,
                        mode: nextMode,
                      })));
                    }
                  }}
                >
                  {MOVEMENT_MODE_KINDS.map((kind) => (
                    <option key={kind} value={kind}>
                      {kind}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Distance (feet)
                <input
                  type="number"
                  aria-label={`Movement mode distance ${index}`}
                  value={mode.distance.value}
                  onChange={(event) =>
                    commit(updateMovementMode(state, index, (current) => ({
                      ...current,
                      distance: { ...current.distance, value: Number(event.currentTarget.value) },
                    })))
                  }
                />
              </label>
            </div>
            {(mode.qualifiers ?? []).map((qualifier, qualifierIndex) => (
              <div key={qualifierIndex} className="statblock-definition-editor__grid">
                <label>
                  Qualifier {qualifierIndex + 1}
                  <input
                    aria-label={`Movement mode qualifier ${index} ${qualifierIndex}`}
                    value={qualifier}
                    onChange={(event) =>
                      commit(
                        updateMovementQualifier(
                          state,
                          index,
                          qualifierIndex,
                          event.currentTarget.value,
                        ),
                      )
                    }
                  />
                </label>
                <button
                  type="button"
                  aria-label={`Remove qualifier ${qualifierIndex} from movement mode ${index}`}
                  onClick={() => commit(removeMovementQualifier(state, index, qualifierIndex))}
                >
                  Remove qualifier
                </button>
              </div>
            ))}
            <button
              type="button"
              aria-label={`Add qualifier to movement mode ${index}`}
              onClick={() => commit(addMovementQualifier(state, index))}
            >
              Add qualifier
            </button>
            <button
              type="button"
              aria-label={`Remove movement mode ${index}`}
              onClick={() => commit(removeMovementMode(state, index))}
            >
              Remove movement mode
            </button>
          </fieldset>
        ))}
        <button type="button" onClick={() => commit(addMovementMode(state))}>
          Add movement mode
        </button>
      </section>

      <details
        className="statblock-definition-editor__advanced"
        data-testid="editor-advanced-structure"
      >
        <summary>Advanced — full data structure</summary>
        <p className="statblock-definition-editor__disclosure">
          Protected contract fields. Dedicated controls above edit named targets; everything else is
          review-only here.
        </p>

        <ProtectedStructureBlock
          path="identity.protected"
          title="Identity (protected fields)"
          value={identityProtectedRemainder(workingCopy.identity)}
          editableFieldsAbove="name"
        />
        <ProtectedStructureBlock
          path="defenses"
          title="Defenses (full structure)"
          value={defensesDisclosureValue(workingCopy.defenses)}
          editableFieldsAbove="primary AC value"
        />
        <ProtectedStructureBlock
          path="vitality"
          title="Vitality (full structure)"
          value={vitalityDisclosureValue(workingCopy.vitality)}
          editableFieldsAbove={`hit_points.${hpTarget}`}
        />
        <ProtectedStructureBlock path="ruleset" title="Ruleset" value={workingCopy.ruleset} />
        <ProtectedStructureBlock path="proficiencies" title="Proficiencies" value={workingCopy.proficiencies} />
        <ProtectedStructureBlock path="senses" title="Senses" value={workingCopy.senses} />
        <ProtectedStructureBlock path="communication" title="Communication" value={workingCopy.communication} />
        <ProtectedStructureBlock path="challenge" title="Challenge" value={workingCopy.challenge} />

        {workingCopy.resources !== undefined ? (
          <ProtectedStructureBlock path="resources" title="Resources" value={workingCopy.resources} />
        ) : null}

        {workingCopy.phases !== undefined ? (
          <ProtectedStructureBlock path="phases" title="Phases" value={workingCopy.phases} />
        ) : null}

        {workingCopy.lair !== undefined ? (
          <ProtectedStructureBlock path="lair" title="Lair profile" value={workingCopy.lair} />
        ) : null}

        {workingCopy.flavor_text !== undefined ? (
          <ProtectedStructureBlock path="flavor_text" title="Flavor text" value={workingCopy.flavor_text} />
        ) : null}

        {workingCopy.rule_elements.map((element, index) => (
          <section
            key={`advanced-${element.key}`}
            className="statblock-definition-editor__rule-element"
            aria-label={`Protected structure for ${element.key}`}
          >
            <h4>{element.name || element.key}</h4>
            <ProtectedStructureBlock
              path={`rule_elements[${index}].structure`}
              title="Element structure (key, section, order, summary, tags, automation_support)"
              value={ruleElementProtectedStructure(element, index)}
              editableFieldsAbove="name and rules_text"
            />
            <ProtectedStructureBlock
              path={`rule_elements[${index}].summary`}
              title="Element summary"
              value={"summary" in element ? element.summary : "(property omitted)"}
              editableFieldsAbove="name and rules_text"
            />
            <ProtectedStructureBlock
              path={`rule_elements[${index}].activation`}
              title="Activation"
              value={element.activation}
            />
            <ProtectedStructureBlock
              path={`rule_elements[${index}].usage`}
              title="Usage"
              value={element.usage}
            />
            <ProtectedStructureBlock
              path={`rule_elements[${index}].costs`}
              title="Costs"
              value={"costs" in element ? element.costs : "(property omitted)"}
            />
            <ProtectedStructureBlock
              path={`rule_elements[${index}].mechanic`}
              title="Mechanic"
              value={element.mechanic}
              editableFieldsAbove={
                hasDirectMovementEffect(element.mechanic) ? "movement-mode reference" : undefined
              }
            />
          </section>
        ))}
      </details>
    </div>
  );
}
