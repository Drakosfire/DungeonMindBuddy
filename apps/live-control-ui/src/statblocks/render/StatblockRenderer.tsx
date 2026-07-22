import "./StatblockRenderer.css";

import {
  abilityModifier,
  armorClassSummary,
  asRecord,
  hitPointsSummary,
  movementSummary,
  ruleElements,
  textOrNull,
  validationIssues,
  type JsonRecord,
} from "./statblockViewModel";

export interface StatblockRendererProps {
  candidate: JsonRecord;
  mode?: "review" | "summary" | "full" | "embed" | "combat-drilldown";
}

const ABILITY_ORDER = [
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
  "charisma",
] as const;

export function StatblockRenderer({ candidate, mode = "review" }: StatblockRendererProps) {
  const definition = asRecord(candidate.definition);
  if (!definition) {
    return (
      <div className="statblock-renderer" data-mode={mode} role="alert">
        Candidate is missing a structured definition.
      </div>
    );
  }

  const identity = asRecord(definition.identity) ?? {};
  const abilities = asRecord(definition.abilities) ?? {};
  const challenge = asRecord(definition.challenge) ?? {};
  const senses = asRecord(definition.senses) ?? {};
  const communication = asRecord(definition.communication) ?? {};
  const elements = ruleElements(definition);
  const issues = validationIssues(candidate);
  const errors = issues.filter((issue) => issue.severity === "error");
  const warnings = issues.filter((issue) => issue.severity === "warning");
  const generationReceipt = asRecord(candidate.generation_receipt);
  const unsupported = elements.filter((element) => element.humanAdjudicated);

  const size = textOrNull(identity.size);
  const creatureType = textOrNull(identity.creature_type);
  const alignment = textOrNull(identity.alignment);
  const identityLine = [size, creatureType, alignment].filter(Boolean).join(", ");

  return (
    <article className="statblock-renderer" data-mode={mode} aria-label="Statblock candidate">
      <header className="statblock-renderer__header">
        <h2>{textOrNull(identity.name) ?? "Unnamed candidate"}</h2>
        <p className="statblock-renderer__meta">{identityLine || "Identity incomplete"}</p>
        <p className="statblock-renderer__meta">
          Candidate <code>{textOrNull(candidate.candidate_id) ?? "unknown"}</code>
          {" · "}
          CR {textOrNull(challenge.rating) ?? "—"}
        </p>
      </header>

      <section aria-labelledby="statblock-defenses-heading">
        <h3 id="statblock-defenses-heading" className="statblock-renderer__section-title">
          Defenses and movement
        </h3>
        <dl className="statblock-renderer__grid">
          <div>
            <dt>Armor Class</dt>
            <dd>{armorClassSummary(definition)}</dd>
          </div>
          <div>
            <dt>Hit Points</dt>
            <dd>{hitPointsSummary(definition)}</dd>
          </div>
          <div>
            <dt>Speed</dt>
            <dd>{movementSummary(definition)}</dd>
          </div>
          <div>
            <dt>Passive Perception</dt>
            <dd>{typeof senses.passive_perception === "number" ? senses.passive_perception : "—"}</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="statblock-abilities-heading">
        <h3 id="statblock-abilities-heading" className="statblock-renderer__section-title">
          Abilities
        </h3>
        <ul className="statblock-renderer__abilities">
          {ABILITY_ORDER.map((ability) => {
            const score = abilities[ability];
            const modifier = abilityModifier(score);
            return (
              <li key={ability}>
                <strong>{ability.slice(0, 3).toUpperCase()}</strong>
                <span>{typeof score === "number" ? score : "—"}</span>
                <span>{modifier ?? "—"}</span>
              </li>
            );
          })}
        </ul>
      </section>

      <section aria-labelledby="statblock-communication-heading">
        <h3 id="statblock-communication-heading" className="statblock-renderer__section-title">
          Senses and languages
        </h3>
        <dl className="statblock-renderer__grid">
          <div>
            <dt>Languages</dt>
            <dd>
              {Array.isArray(communication.languages) && communication.languages.length
                ? communication.languages.map(String).join(", ")
                : "—"}
            </dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="statblock-elements-heading">
        <h3 id="statblock-elements-heading" className="statblock-renderer__section-title">
          Rule elements
        </h3>
        <div className="statblock-renderer__elements">
          {elements.length === 0 ? <p>No rule elements present.</p> : null}
          {elements.map((element) => (
            <article key={element.key} className="statblock-renderer__element">
              <h4>
                {element.name}
                <span className="statblock-renderer__badge">{element.section}</span>
                {element.humanAdjudicated ? (
                  <span className="statblock-renderer__badge">human-adjudicated</span>
                ) : null}
              </h4>
              {element.summary ? <p>{element.summary}</p> : null}
              {element.rulesText ? <p>{element.rulesText}</p> : null}
            </article>
          ))}
        </div>
      </section>

      {unsupported.length ? (
        <section className="statblock-renderer__unsupported" aria-label="Unsupported elements">
          <h3 className="statblock-renderer__section-title">Human-adjudicated elements</h3>
          <ul>
            {unsupported.map((element) => (
              <li key={`unsupported-${element.key}`}>{element.name}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-labelledby="statblock-validation-heading">
        <h3 id="statblock-validation-heading" className="statblock-renderer__section-title">
          Validation
        </h3>
        {errors.length === 0 && warnings.length === 0 ? (
          <p>No validation issues.</p>
        ) : (
          <>
            {errors.length ? (
              <ul className="statblock-renderer__issues statblock-renderer__issues--error" aria-label="Validation errors">
                {errors.map((issue) => (
                  <li key={`error-${issue.code}-${issue.fieldPath ?? "none"}`}>
                    <strong>{issue.code}</strong>: {issue.message}
                  </li>
                ))}
              </ul>
            ) : null}
            {warnings.length ? (
              <ul className="statblock-renderer__issues statblock-renderer__issues--warning" aria-label="Validation warnings">
                {warnings.map((issue) => (
                  <li key={`warning-${issue.code}-${issue.fieldPath ?? "none"}`}>
                    <strong>{issue.code}</strong>: {issue.message}
                  </li>
                ))}
              </ul>
            ) : null}
          </>
        )}
      </section>

      <details>
        <summary>Generation provenance</summary>
        <dl className="statblock-renderer__grid">
          <div>
            <dt>Request ID</dt>
            <dd>{textOrNull(generationReceipt?.request_id) ?? "—"}</dd>
          </div>
          <div>
            <dt>Provider</dt>
            <dd>{textOrNull(generationReceipt?.provider) ?? "—"}</dd>
          </div>
          <div>
            <dt>Model</dt>
            <dd>{textOrNull(generationReceipt?.model) ?? "—"}</dd>
          </div>
          <div>
            <dt>Contract</dt>
            <dd>
              {textOrNull(candidate.contract) ?? "—"} {textOrNull(candidate.contract_version) ?? ""}
            </dd>
          </div>
        </dl>
      </details>
    </article>
  );
}
