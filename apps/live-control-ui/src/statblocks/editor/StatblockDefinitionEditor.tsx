import { useState } from "react";
import type { AbilityName, RuleElement_Input, StatblockDefinitionV1_Output } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import { ProtectedStructureBlock } from "./ProtectedStructureBlock";
import {
  createEditorStateFromOutput,
  getUiStatus,
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

function primaryArmorClassIndex(defenses: StatblockDefinitionV1_Output["defenses"]): number {
  const defaultIndex = defenses.armor_classes.findIndex((entry) => entry.default);
  return defaultIndex >= 0 ? defaultIndex : 0;
}

function readPrimaryArmorClassValue(defenses: StatblockEditorState["workingCopy"]["defenses"]): number {
  const index = primaryArmorClassIndex(defenses);
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

function mechanicSummary(element: RuleElement_Input): Record<string, unknown> {
  const mechanic = element.mechanic;
  const kind = mechanic.kind ?? "unknown";
  const summary: Record<string, unknown> = { kind };
  if (kind === "spellcasting" && "groups" in mechanic) {
    summary.casting_mode = mechanic.casting_mode;
    summary.group_count = mechanic.groups.length;
  }
  if (kind === "human_adjudicated" && "adjudication_tags" in mechanic) {
    summary.adjudication_tags = mechanic.adjudication_tags ?? [];
  }
  if (kind === "phase_transition" && "destination_phase_key" in mechanic) {
    summary.destination_phase_key = mechanic.destination_phase_key;
  }
  if (kind === "attack" && "hit_effects" in mechanic) {
    summary.hit_effects = mechanic.hit_effects ?? [];
  }
  return summary;
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

  const identityProtected = {
    size: workingCopy.identity.size,
    creature_type: workingCopy.identity.creature_type,
    subtypes: workingCopy.identity.subtypes ?? [],
    alignment: workingCopy.identity.alignment ?? null,
  };

  const acIndex = primaryArmorClassIndex(workingCopy.defenses);
  const otherArmorClasses = workingCopy.defenses.armor_classes.filter((_entry, index) => index !== acIndex);

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
        <ProtectedStructureBlock path="identity" title="Identity structure" summary={identityProtected} />
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
          Primary AC value
          <input
            type="number"
            aria-label="Primary armor class"
            value={readPrimaryArmorClassValue(workingCopy.defenses)}
            onChange={(event) => commit(setPrimaryArmorClassValue(state, Number(event.target.value)))}
          />
        </label>
        {otherArmorClasses.length > 0 ? (
          <ProtectedStructureBlock
            path="defenses.armor_classes.additional"
            title="Additional armor classes"
            summary={{ entries: otherArmorClasses }}
          />
        ) : null}
        <ProtectedStructureBlock
          path="defenses.damage_interactions"
          title="Damage interactions"
          summary={{ entries: workingCopy.defenses.damage_interactions ?? [] }}
        />
        <ProtectedStructureBlock
          path="defenses.condition_immunities"
          title="Condition immunities"
          summary={{ entries: workingCopy.defenses.condition_immunities ?? [] }}
        />
      </section>

      <section className="statblock-definition-editor__section" aria-label="Vitality">
        <h3>Hit points</h3>
        <label>
          Hit points ({resolveHitPointsEditTarget(workingCopy.vitality.hit_points)})
          <input
            type="number"
            aria-label="Hit points"
            value={readHitPointsEditorValue(workingCopy.vitality)}
            onChange={(event) => commit(setHitPointsMax(state, Number(event.target.value)))}
          />
        </label>
        <ProtectedStructureBlock
          path="vitality.hit_points.profile"
          title="Hit point profile"
          summary={workingCopy.vitality.hit_points}
        />
      </section>

      <ProtectedStructureBlock path="ruleset" title="Ruleset" summary={workingCopy.ruleset} />
      <ProtectedStructureBlock path="movement" title="Movement" summary={workingCopy.movement} />
      <ProtectedStructureBlock path="proficiencies" title="Proficiencies" summary={workingCopy.proficiencies} />
      <ProtectedStructureBlock path="senses" title="Senses" summary={workingCopy.senses} />
      <ProtectedStructureBlock path="communication" title="Communication" summary={workingCopy.communication} />
      <ProtectedStructureBlock path="challenge" title="Challenge" summary={workingCopy.challenge} />

      {workingCopy.resources && workingCopy.resources.length > 0 ? (
        <ProtectedStructureBlock path="resources" title="Resources" summary={{ entries: workingCopy.resources }} />
      ) : null}

      {workingCopy.phases && workingCopy.phases.length > 0 ? (
        <ProtectedStructureBlock path="phases" title="Phases" summary={{ entries: workingCopy.phases }} />
      ) : null}

      {workingCopy.lair ? (
        <ProtectedStructureBlock path="lair" title="Lair profile" summary={workingCopy.lair} />
      ) : null}

      {workingCopy.flavor_text ? (
        <ProtectedStructureBlock path="flavor_text" title="Flavor text" summary={workingCopy.flavor_text} />
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
              path={`rule_elements[${index}].meta`}
              title="Element identity and order"
              summary={{
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
              summary={element.activation}
            />
            <ProtectedStructureBlock
              path={`rule_elements[${index}].usage`}
              title="Usage"
              summary={element.usage}
            />
            <ProtectedStructureBlock
              path={`rule_elements[${index}].costs`}
              title="Costs"
              summary={{ entries: element.costs ?? [] }}
            />
            <ProtectedStructureBlock
              path={`rule_elements[${index}].mechanic`}
              title="Mechanic (protected)"
              summary={mechanicSummary(element)}
            />
          </article>
        ))}
      </section>
    </div>
  );
}
