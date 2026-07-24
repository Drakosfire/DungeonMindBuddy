import { useState } from "react";
import type { AbilityName, StatblockDefinitionV1_Output } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import { ProtectedStructureBlock } from "./ProtectedStructureBlock";
import {
  createEditorStateFromOutput,
  formulaDisplayedAverage,
  getUiStatus,
  identityProtectedRemainder,
  resolveHitPointsEditTarget,
  setAbility,
  setHitPointsMax,
  setIdentityName,
  setPrimaryArmorClassValue,
  setRuleElementName,
  setRuleElementRulesText,
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

export type StatblockDefinitionEditorProps = {
  output: StatblockDefinitionV1_Output;
  editorState?: StatblockEditorState;
  onEditorStateChange?: (state: StatblockEditorState) => void;
};

function readPrimaryArmorClassValue(defenses: StatblockEditorState["workingCopy"]["defenses"]): number {
  return defenses.default_armor_class.value;
}

function readHitPointsEditorValue(vitality: StatblockEditorState["workingCopy"]["vitality"]): number {
  const hitPoints = vitality.hit_points;
  if (hitPoints.method === "fixed") {
    return hitPoints.fixed_value;
  }
  if (hitPoints.displayed_average !== null && hitPoints.displayed_average !== undefined) {
    return hitPoints.displayed_average;
  }
  return formulaDisplayedAverage(hitPoints.formula);
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

  const primaryAcLabel = "Primary AC value (default_armor_class)";
  const hpTarget = resolveHitPointsEditTarget(workingCopy.vitality.hit_points);

  return (
    <div className="statblock-definition-editor" data-testid="statblock-definition-editor">
      <p className="statblock-definition-editor__disclosure">
        Browser-local working copy for this candidate. Survives tab close; not a Server save.
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
        <ProtectedStructureBlock
          path="identity.protected"
          title="Identity (protected fields)"
          value={identityProtectedRemainder(workingCopy.identity)}
          editableFieldsAbove="name"
        />
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
        <ProtectedStructureBlock
          path="defenses"
          title="Defenses (full structure)"
          value={defensesDisclosureValue(workingCopy.defenses)}
          editableFieldsAbove="primary AC value"
        />
      </section>

      <section className="statblock-definition-editor__section" aria-label="Vitality">
        <h3>Hit points</h3>
        <label>
          Hit points (
          {hpTarget === "formula_average"
            ? "adjusts formula.modifier + displayed_average"
            : "mutates vitality.hit_points.fixed_value"}
          )
          <input
            type="number"
            min={1}
            step={1}
            aria-label="Hit points"
            title={
              hpTarget === "formula_average"
                ? "Steps by 1 HP via formula.modifier so displayed_average always matches the dice formula."
                : "Fixed hit point value."
            }
            value={readHitPointsEditorValue(workingCopy.vitality)}
            onChange={(event) => commit(setHitPointsMax(state, Number(event.target.value)))}
          />
        </label>
        <ProtectedStructureBlock
          path="vitality"
          title="Vitality (full structure)"
          value={vitalityDisclosureValue(workingCopy.vitality)}
          editableFieldsAbove={
            hpTarget === "formula_average"
              ? "hit_points.formula.modifier + displayed_average"
              : "hit_points.fixed_value"
          }
        />
      </section>

      <ProtectedStructureBlock path="ruleset" title="Ruleset" value={workingCopy.ruleset} />
      <ProtectedStructureBlock path="movement" title="Movement" value={workingCopy.movement} />
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

      <section className="statblock-definition-editor__section" aria-label="Rule elements">
        <h3>Rule elements</h3>
        {workingCopy.rule_elements.map((element, index) => (
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
            />
          </article>
        ))}
      </section>
    </div>
  );
}
