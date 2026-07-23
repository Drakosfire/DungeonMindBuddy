import type { GeneratedStatblockCandidateV1 } from "../../contracts/dungeonbuddy-statblocks-v1/client";

import "./StatblockRenderer.css";
import {
  buildStatblockViewModel,
  formatModifier,
  groupRuleElementsBySection,
  type StatblockRenderMode,
} from "./statblockViewModel";

export type StatblockRendererProps = {
  candidate: GeneratedStatblockCandidateV1;
  mode?: StatblockRenderMode;
};

export function StatblockRenderer({ candidate, mode = "review" }: StatblockRendererProps) {
  const view = buildStatblockViewModel(candidate, mode);
  const sections = groupRuleElementsBySection(view.ruleElements);

  return (
    <article
      className="statblock-renderer"
      data-statblock-renderer
      data-render-mode={mode}
      data-candidate-id={view.candidateId}
      aria-label={`Statblock candidate ${view.name}`}
    >
      <header className="statblock-renderer-header">
        <h3>{view.name}</h3>
        <p className="statblock-renderer-identity">{view.identityLine}</p>
        <p className="statblock-renderer-meta">
          Candidate <code>{view.candidateId}</code> · {view.challengeSummary}
        </p>
        {view.flavorSummary ? <p className="statblock-renderer-flavor">{view.flavorSummary}</p> : null}
      </header>

      <dl className="statblock-renderer-core" aria-label="Core combat statistics">
        <div>
          <dt>Armor Class</dt>
          <dd>{view.armorClassSummary}</dd>
        </div>
        <div>
          <dt>Hit Points</dt>
          <dd>{view.hitPointsSummary}</dd>
        </div>
        <div>
          <dt>Speed</dt>
          <dd>{view.speedSummary}</dd>
        </div>
      </dl>

      <section className="statblock-renderer-section" aria-label="Ability scores">
        <h4>Abilities</h4>
        <table className="statblock-ability-table">
          <thead>
            <tr>
              {view.abilities.map((row) => (
                <th key={row.ability} scope="col">
                  {row.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {view.abilities.map((row) => (
                <td key={`${row.ability}-score`}>{row.score}</td>
              ))}
            </tr>
            <tr>
              {view.abilities.map((row) => (
                <td key={`${row.ability}-mod`}>{formatModifier(row.modifier)}</td>
              ))}
            </tr>
          </tbody>
        </table>
      </section>

      <dl className="statblock-renderer-core" aria-label="Proficiencies and senses">
        <div>
          <dt>Saving Throws</dt>
          <dd>{view.savingThrows}</dd>
        </div>
        <div>
          <dt>Skills</dt>
          <dd>{view.skills}</dd>
        </div>
        <div>
          <dt>Senses</dt>
          <dd>{view.sensesSummary}</dd>
        </div>
        <div>
          <dt>Languages</dt>
          <dd>{view.languagesSummary}</dd>
        </div>
      </dl>

      {sections.map(({ section, elements }) => (
        <section key={section} className="statblock-renderer-section" aria-label={`${section} rule elements`}>
          <h4>{section.replace(/_/g, " ")}</h4>
          {elements.map((element) => (
            <div key={element.key} className="statblock-rule-element" data-element-key={element.key}>
              <div>
                <span className="statblock-rule-element-name">{element.name}</span>
                {element.humanAdjudicated ? (
                  <span className="statblock-badge">Human adjudicated</span>
                ) : null}
                {element.unsupportedMechanic ? (
                  <span className="statblock-badge">Unsupported mechanic</span>
                ) : null}
              </div>
              {element.summary ? <p className="module-muted">{element.summary}</p> : null}
              <p className="statblock-rule-element-text">{element.rulesText}</p>
            </div>
          ))}
        </section>
      ))}

      {view.validation ? (
        <section className="statblock-renderer-section" aria-label="Validation receipt">
          <h4>
            Validation
            {view.validation.errors.length ? (
              <span className="statblock-badge statblock-badge-error">Errors</span>
            ) : null}
            {view.validation.warnings.length ? (
              <span className="statblock-badge statblock-badge-warning">Warnings</span>
            ) : null}
          </h4>
          <p className="module-muted">
            Status <strong>{view.validation.status}</strong> · digest <code>{view.validation.digest}</code>
          </p>
          {view.validation.errors.length ? (
            <ul className="statblock-issue-list" data-severity="error">
              {view.validation.errors.map((issue, index) => (
                <li key={`error-${issue.code}-${index}`}>
                  {issue.field_path ? <code>{issue.field_path}</code> : null} {issue.message}
                </li>
              ))}
            </ul>
          ) : null}
          {view.validation.warnings.length ? (
            <ul className="statblock-issue-list" data-severity="warning">
              {view.validation.warnings.map((issue, index) => (
                <li key={`warning-${issue.code}-${index}`}>
                  {issue.field_path ? <code>{issue.field_path}</code> : null} {issue.message}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}

      <details className="statblock-renderer-receipts">
        <summary>Provenance and receipts</summary>
        <dl className="statblock-renderer-core">
          <div>
            <dt>Contract</dt>
            <dd>
              {view.contract}@{view.contractVersion}
            </dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{view.createdAt}</dd>
          </div>
          <div>
            <dt>Expires</dt>
            <dd>{view.expiresAt}</dd>
          </div>
          {view.generation ? (
            <>
              <div>
                <dt>Generation request</dt>
                <dd>
                  <code>{view.generation.requestId}</code>
                </dd>
              </div>
              <div>
                <dt>Provider / model</dt>
                <dd>
                  {view.generation.provider} / {view.generation.model}
                </dd>
              </div>
            </>
          ) : null}
        </dl>
      </details>
    </article>
  );
}
