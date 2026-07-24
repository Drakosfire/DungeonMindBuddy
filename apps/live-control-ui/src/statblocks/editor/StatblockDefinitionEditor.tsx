import { useState } from "react";
import type { AbilityName, StatblockDefinitionV1_Output } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import { ProtectedStructureBlock } from "./ProtectedStructureBlock";
import {
  createEditorStateFromOutput,
  getUiStatus,
  primaryArmorClassIndexForDisplay,
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
    ? "Primary AC (default armor_classes entry)"
    : "Primary AC (armor_classes[0]; no default flagged)";

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
        <ProtectedStructureBlock path="identity" title="Identity structure" value={workingCopy.identity} />
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
        <ProtectedStructureBlock path="defenses" title="Defenses" value={workingCopy.defenses} />
      </section>

      <section className="statblock-definition-editor__section" aria-label="Vitality">
        <h3>Hit points</h3>
        <label>
          Hit points (mutates vitality.hit_points.{resolveHitPointsEditTarget(workingCopy.vitality.hit_points)})
          <input
            type="number"
            aria-label="Hit points"
            value={readHitPointsEditorValue(workingCopy.vitality)}
            onChange={(event) => commit(setHitPointsMax(state, Number(event.target.value)))}
          />
        </label>
        <ProtectedStructureBlock path="vitality" title="Vitality" value={workingCopy.vitality} />
      </section>

      <ProtectedStructureBlock path="ruleset" title="Ruleset" value={workingCopy.ruleset} />
      <ProtectedStructureBlock path="movement" title="Movement" value={workingCopy.movement} />
      <ProtectedStructureBlock path="proficiencies" title="Proficiencies" value={workingCopy.proficiencies} />
      <ProtectedStructureBlock path="senses" title="Senses" value={workingCopy.senses} />
      <ProtectedStructureBlock path="communication" title="Communication" value={workingCopy.communication} />
      <ProtectedStructureBlock path="challenge" title="Challenge" value={workingCopy.challenge} />

      {workingCopy.resources && workingCopy.resources.length > 0 ? (
        <ProtectedStructureBlock path="resources" title="Resources" value={workingCopy.resources} />
      ) : null}

      {workingCopy.phases && workingCopy.phases.length > 0 ? (
        <ProtectedStructureBlock path="phases" title="Phases" value={workingCopy.phases} />
      ) : null}

      {workingCopy.lair !== undefined && workingCopy.lair !== null ? (
        <ProtectedStructureBlock path="lair" title="Lair profile" value={workingCopy.lair} />
      ) : null}

      {workingCopy.flavor_text ? (
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
              title="Element structure (key, section, order, tags, automation_support)"
              value={{
                key: element.key,
                section: element.section,
                order: index,
                automation_support: element.automation_support,
                tags: element.tags ?? [],
              }}
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
              value={element.costs ?? []}
            />
            <ProtectedStructureBlock
              path={`rule_elements[${index}].mechanic`}
              title="Mechanic (protected)"
              value={element.mechanic}
            />
          </article>
        ))}
      </section>
    </div>
  );
}
