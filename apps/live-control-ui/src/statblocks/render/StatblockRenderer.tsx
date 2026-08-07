import type { ReactNode } from "react";

import type {
  GeneratedStatblockCandidateV1,
  StatblockRevisionResourceV1,
} from "../../contracts/dungeonbuddy-statblocks-v1/client";

import "./StatblockRenderer.css";
import "./statblockCampaignTheme.css";
import {
  buildStatblockViewModel,
  formatModifier,
  groupRuleElementsBySection,
  type FormattedRuleElement,
  type StatblockRenderMode,
  type StatblockViewModel,
} from "./statblockViewModel";

export type StatblockRendererChrome = "default" | "campaign";

/** Same Cloudflare placeholder as Statblock Generator PortraitPanel until CDN portraits are bound. */
export const STATBLOCK_PORTRAIT_PLACEHOLDER_URL =
  "https://imagedelivery.net/SahcvrNe_-ej4lTB6vsAZA/1778cee9-f500-4476-7f30-ac7fd991f700/public";

export type StatblockRendererProps =
  | {
      candidate: GeneratedStatblockCandidateV1;
      revision?: never;
      mode?: StatblockRenderMode;
      /** campaign = Threat expand / GM prep; hides revision-id + ledger chrome. */
      chrome?: StatblockRendererChrome;
    }
  | {
      candidate?: never;
      revision: StatblockRevisionResourceV1;
      mode?: StatblockRenderMode;
      chrome?: StatblockRendererChrome;
    };

function ValidationReceiptSection({ view }: { view: StatblockViewModel }) {
  if (!view.validation) return null;
  return (
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
  );
}

function ProvenanceReceiptBody({ view }: { view: StatblockViewModel }) {
  return (
    <dl className="statblock-renderer-core" aria-label="Provenance and receipts">
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
  );
}

/** Ledger blocks for Threat Advanced Details (validation + provenance). */
export function StatblockAdvancedLedger({
  revision,
  mode = "full",
}: {
  revision: StatblockRevisionResourceV1;
  mode?: StatblockRenderMode;
}) {
  const view = buildStatblockViewModel(revision, mode);
  return (
    <div className="statblock-advanced-ledger" data-testid="statblock-advanced-ledger">
      <ValidationReceiptSection view={view} />
      <section className="statblock-renderer-section" aria-label="Provenance and receipts">
        <h4>Provenance and receipts</h4>
        <ProvenanceReceiptBody view={view} />
      </section>
    </div>
  );
}

function RuleElementBlock({ element }: { element: FormattedRuleElement }) {
  return (
    <div className="statblock-rule-element" data-element-key={element.key} data-mechanic-kind={element.mechanicKind}>
      <div>
        <span className="statblock-rule-element-name">{element.name}</span>
        {element.humanAdjudicated ? <span className="statblock-badge">Human adjudicated</span> : null}
        {element.unsupportedMechanic ? <span className="statblock-badge">Unsupported mechanic</span> : null}
      </div>
      {element.summary ? <p className="module-muted">{element.summary}</p> : null}
      <dl className="statblock-rule-meta" aria-label={`${element.name} activation and usage`}>
        <div>
          <dt>Activation</dt>
          <dd>
            {element.activation.kind}
            {element.activation.trigger ? ` · trigger ${element.activation.trigger}` : ""}
            {element.activation.timingText ? ` · ${element.activation.timingText}` : ""}
          </dd>
        </div>
        <div>
          <dt>Usage</dt>
          <dd>{element.usage.summary}</dd>
        </div>
        {element.costs.length ? (
          <div>
            <dt>Costs</dt>
            <dd>{element.costs.map((cost) => `${cost.amount}× ${cost.resourceKey}`).join(", ")}</dd>
          </div>
        ) : null}
      </dl>
      <ul className="statblock-mechanic-details" aria-label={`${element.name} mechanic details`}>
        {element.mechanicDetails.lines.map((line) => (
          <li key={`${element.key}-${line}`}>{line}</li>
        ))}
      </ul>
      <p className="statblock-rule-element-text">{element.rulesText}</p>
    </div>
  );
}

function DefensesExtras({ view }: { view: StatblockViewModel }) {
  if (!view.damageInteractions.length && !view.conditionImmunities.length) return null;
  return (
    <section className="statblock-renderer-section" aria-label="Damage interactions and condition immunities">
      <h4>Defenses</h4>
      {view.damageInteractions.length ? (
        <ul className="statblock-structured-list" data-region="damage-interactions">
          {view.damageInteractions.map((entry) => (
            <li key={entry.key}>
              <strong>{entry.kind}</strong>: {entry.damageTypes}
              {entry.qualifiers ? ` (${entry.qualifiers})` : ""}
              {entry.bypasses ? `; bypasses ${entry.bypasses}` : ""}
            </li>
          ))}
        </ul>
      ) : null}
      {view.conditionImmunities.length ? (
        <p data-region="condition-immunities">
          Condition immunities: {view.conditionImmunities.join(", ")}
        </p>
      ) : null}
    </section>
  );
}

function ResourcesSection({ view }: { view: StatblockViewModel }) {
  if (!view.resources.length) return null;
  return (
    <section className="statblock-renderer-section" aria-label="Resources">
      <h4>Resources</h4>
      <ul className="statblock-structured-list" data-region="resources">
        {view.resources.map((resource) => (
          <li key={resource.key}>
            <strong>{resource.name}</strong> · max {resource.maximum} · refresh {resource.refresh}
            {resource.rulesText ? ` — ${resource.rulesText}` : ""}
          </li>
        ))}
      </ul>
    </section>
  );
}

function PhasesSection({ view }: { view: StatblockViewModel }) {
  if (!view.phases.length) return null;
  return (
    <section className="statblock-renderer-section" aria-label="Phases">
      <h4>Phases</h4>
      <ul className="statblock-structured-list" data-region="phases">
        {view.phases.map((phase) => (
          <li key={phase.key}>
            <strong>{phase.name}</strong>
            {phase.isDefault ? " (default)" : ""}
            {phase.enabledElementKeys.length
              ? ` · enables ${phase.enabledElementKeys.join(", ")}`
              : ""}
            {phase.disabledElementKeys.length
              ? ` · disables ${phase.disabledElementKeys.join(", ")}`
              : ""}
            {phase.entryRulesText ? ` — ${phase.entryRulesText}` : ""}
          </li>
        ))}
      </ul>
    </section>
  );
}

function formatDamageKindLabel(kind: string): string {
  const normalized = kind.replace(/_/g, " ").trim();
  if (!normalized) return "Damage";
  return `Damage ${normalized.replace(/\b\w/g, (ch) => ch.toUpperCase())}`;
}

function CampaignRuleElement({ element }: { element: FormattedRuleElement }) {
  const metaBits = [
    element.usage.summary && element.usage.summary !== "at will" ? element.usage.summary : null,
    ...element.mechanicDetails.lines.slice(0, 2),
  ].filter(Boolean);

  return (
    <div
      className="statblock-campaign-rule"
      data-element-key={element.key}
      data-mechanic-kind={element.mechanicKind}
    >
      <span className="statblock-campaign-rule__name">{element.name}</span>
      {metaBits.length ? (
        <p className="statblock-campaign-rule__meta">{metaBits.join(" · ")}</p>
      ) : null}
      {element.rulesText ? (
        <p className="statblock-campaign-rule__text">{element.rulesText}</p>
      ) : element.summary ? (
        <p className="statblock-campaign-rule__text">{element.summary}</p>
      ) : null}
    </div>
  );
}

function CampaignSectionCard({
  heading,
  children,
}: {
  heading: string;
  children: ReactNode;
}) {
  return (
    <section className="statblock-campaign-card" aria-label={heading}>
      <h4 className="statblock-campaign-card__heading">{heading}</h4>
      {children}
    </section>
  );
}

function CampaignStatblockBody({ view }: { view: StatblockViewModel }) {
  const sections = groupRuleElementsBySection(view.ruleElements);
  const damageRows = view.damageInteractions.map((entry) => ({
    label: formatDamageKindLabel(entry.kind),
    value: [
      entry.damageTypes,
      entry.qualifiers ? `(${entry.qualifiers})` : null,
      entry.bypasses ? `bypasses ${entry.bypasses}` : null,
    ]
      .filter(Boolean)
      .join(" "),
  }));

  return (
    <>
      <header className="statblock-campaign-header">
        <h3>{view.name}</h3>
        <p className="statblock-campaign-identity">{view.identityLine}</p>
      </header>

      <div className="statblock-campaign-grid">
        <div className="statblock-campaign-col">
          <figure className="statblock-campaign-portrait" data-testid="statblock-campaign-portrait">
            <div className="statblock-campaign-portrait__frame">
              <img
                className="statblock-campaign-portrait__image"
                src={STATBLOCK_PORTRAIT_PLACEHOLDER_URL}
                alt="Portrait placeholder"
              />
            </div>
          </figure>

          {view.flavorSummary ? (
            <p className="statblock-campaign-flavor" data-testid="statblock-campaign-flavor">
              {view.flavorSummary}
            </p>
          ) : null}

          <dl className="statblock-campaign-vitals" aria-label="Core combat statistics">
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

          <table className="statblock-campaign-ability-table" aria-label="Ability scores">
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
                  <td key={`${row.ability}-score`}>
                    {row.score}
                    <span className="statblock-campaign-ability-mod">
                      ({formatModifier(row.modifier)})
                    </span>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>

        <div className="statblock-campaign-col">
          <dl className="statblock-campaign-quickfacts" aria-label="Proficiencies defenses and challenge">
            <div>
              <dt>Saving Throws</dt>
              <dd>{view.savingThrows}</dd>
            </div>
            <div>
              <dt>Skills</dt>
              <dd>{view.skills}</dd>
            </div>
            {damageRows.map((row) => (
              <div key={`${row.label}-${row.value}`}>
                <dt>{row.label}</dt>
                <dd>{row.value}</dd>
              </div>
            ))}
            {view.conditionImmunities.length ? (
              <div>
                <dt>Condition Immunities</dt>
                <dd>{view.conditionImmunities.join(", ")}</dd>
              </div>
            ) : null}
            <div>
              <dt>Senses</dt>
              <dd>{view.sensesSummary}</dd>
            </div>
            <div>
              <dt>Languages</dt>
              <dd>{view.languagesSummary}</dd>
            </div>
            <div>
              <dt>Challenge</dt>
              <dd>{view.challengeSummary}</dd>
            </div>
          </dl>

          {view.resources.length ? (
            <CampaignSectionCard heading="Resources">
              {view.resources.map((resource) => (
                <div key={resource.key} className="statblock-campaign-rule">
                  <span className="statblock-campaign-rule__name">{resource.name}</span>
                  <p className="statblock-campaign-rule__text">
                    Max {resource.maximum} · refresh {resource.refresh}
                    {resource.rulesText ? ` — ${resource.rulesText}` : ""}
                  </p>
                </div>
              ))}
            </CampaignSectionCard>
          ) : null}

          {sections.map(({ section, elements }) => (
            <CampaignSectionCard key={section} heading={section.replace(/_/g, " ")}>
              {elements.map((element) => (
                <CampaignRuleElement key={element.key} element={element} />
              ))}
            </CampaignSectionCard>
          ))}

          {view.phases.length ? (
            <CampaignSectionCard heading="Phases">
              {view.phases.map((phase) => (
                <div key={phase.key} className="statblock-campaign-rule">
                  <span className="statblock-campaign-rule__name">{phase.name}</span>
                  <p className="statblock-campaign-rule__text">
                    {phase.isDefault ? "Default phase. " : ""}
                    {phase.entryRulesText ?? ""}
                    {phase.enabledElementKeys.length
                      ? ` Enables ${phase.enabledElementKeys.join(", ")}.`
                      : ""}
                  </p>
                </div>
              ))}
            </CampaignSectionCard>
          ) : null}

          {view.lair ? (
            <CampaignSectionCard heading="Lair">
              <div className="statblock-campaign-rule">
                <span className="statblock-campaign-rule__name">
                  {view.lair.name ?? "Lair"}
                </span>
                {view.lair.description ? (
                  <p className="statblock-campaign-rule__text">{view.lair.description}</p>
                ) : null}
                {view.lair.regionalRulesText ? (
                  <p className="statblock-campaign-rule__text">{view.lair.regionalRulesText}</p>
                ) : null}
              </div>
            </CampaignSectionCard>
          ) : null}
        </div>
      </div>
    </>
  );
}

function LairSection({ view }: { view: StatblockViewModel }) {
  if (!view.lair) return null;
  const lair = view.lair;
  return (
    <section className="statblock-renderer-section" aria-label="Lair">
      <h4>Lair</h4>
      <dl className="statblock-renderer-core" data-region="lair">
        {lair.name ? (
          <div>
            <dt>Name</dt>
            <dd>{lair.name}</dd>
          </div>
        ) : null}
        {lair.description ? (
          <div>
            <dt>Description</dt>
            <dd>{lair.description}</dd>
          </div>
        ) : null}
        {lair.initiativeCount != null ? (
          <div>
            <dt>Initiative count</dt>
            <dd>{lair.initiativeCount}</dd>
          </div>
        ) : null}
        {lair.initiativeTiebreak != null ? (
          <div>
            <dt>Initiative tiebreak</dt>
            <dd>{lair.initiativeTiebreak}</dd>
          </div>
        ) : null}
        {lair.regionalRulesText ? (
          <div>
            <dt>Regional rules</dt>
            <dd>{lair.regionalRulesText}</dd>
          </div>
        ) : null}
      </dl>
    </section>
  );
}

export function StatblockRenderer({
  candidate,
  revision,
  mode = "review",
  chrome = "default",
}: StatblockRendererProps) {
  const source = candidate ?? revision;
  if (!source) {
    throw new Error("StatblockRenderer requires candidate or revision");
  }
  if (candidate && revision) {
    throw new Error("StatblockRenderer accepts candidate or revision, not both");
  }

  const view = buildStatblockViewModel(source, mode);
  const sections = groupRuleElementsBySection(view.ruleElements);
  const campaignChrome = chrome === "campaign";

  return (
    <article
      className={`statblock-renderer${campaignChrome ? " statblock-renderer--campaign" : ""}`}
      data-statblock-renderer
      data-render-mode={mode}
      data-chrome={chrome}
      data-candidate-id={view.candidateId}
      data-resource-kind={view.recordKind}
      aria-label={`Statblock ${view.recordKind} ${view.name}`}
    >
      {campaignChrome ? (
        <CampaignStatblockBody view={view} />
      ) : (
        <>
          <header className="statblock-renderer-header">
            <h3>{view.name}</h3>
            <p className="statblock-renderer-identity">{view.identityLine}</p>
            <p className="statblock-renderer-meta">
              {view.recordKind === "revision" ? "Revision" : "Candidate"}{" "}
              <code>{view.candidateId}</code> · {view.challengeSummary}
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

          <DefensesExtras view={view} />
          <ResourcesSection view={view} />

          {sections.map(({ section, elements }) => (
            <section key={section} className="statblock-renderer-section" aria-label={`${section} rule elements`}>
              <h4>{section.replace(/_/g, " ")}</h4>
              {elements.map((element) => (
                <RuleElementBlock key={element.key} element={element} />
              ))}
            </section>
          ))}

          <PhasesSection view={view} />
          <LairSection view={view} />

          <ValidationReceiptSection view={view} />
          <details className="statblock-renderer-receipts">
            <summary>Provenance and receipts</summary>
            <ProvenanceReceiptBody view={view} />
          </details>
        </>
      )}
    </article>
  );
}
