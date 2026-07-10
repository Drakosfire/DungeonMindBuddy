import type { ReactNode } from "react";

import type { GraphObjectCardMode, GraphObjectCardViewModel } from "./types";

export interface GraphObjectCardProps {
  model: GraphObjectCardViewModel;
  mode?: GraphObjectCardMode;
  /** Optional override for related-objects body (e.g. Graph Review chips). */
  relationshipsSlot?: ReactNode;
  /** Optional override for actions body (e.g. review staging / evidence). */
  actionsSlot?: ReactNode;
  /** Optional override for collapsed details (e.g. review status / merge provenance). */
  detailsSlot?: ReactNode;
  className?: string;
  "aria-label"?: string;
}

function GraphObjectIdentityHeader({ model }: { model: GraphObjectCardViewModel }) {
  const aliases = model.aliases ?? [];

  return (
    <header className="graph-review-node-identity-header">
      <div className="graph-review-node-identity-title-row">
        <span
          className="graph-review-object-type-badge"
          aria-label={`Object type: ${model.typeBadgeLabel}`}
        >
          {model.typeBadgeLabel}
        </span>
        <h4>{model.label}</h4>
      </div>
      {model.secondaryRoleLabel ? (
        <p className="graph-review-node-role-subtitle">{model.secondaryRoleLabel}</p>
      ) : null}
      {aliases.length ? (
        <p className="graph-review-node-aliases">
          Also known as: {aliases.join(", ")}
        </p>
      ) : null}
    </header>
  );
}

function GraphObjectSummary({ model }: { model: GraphObjectCardViewModel }) {
  const summary = model.gameSummary ?? model.summary;
  if (!summary && !model.whyItMattersNow) return null;

  return (
    <section aria-label="Campaign summary">
      {summary ? <p>{summary}</p> : null}
      {model.whyItMattersNow ? (
        <p className="graph-object-card-why-now">{model.whyItMattersNow}</p>
      ) : null}
    </section>
  );
}

function DefaultRelationships({ model }: { model: GraphObjectCardViewModel }) {
  const relationships = model.relationships ?? [];
  if (!relationships.length) return null;

  return (
    <section
      className="graph-review-node-relationships-primary"
      aria-label="Connected objects and relationships"
    >
      <h5>Related objects</h5>
      <ul className="graph-object-card-relationship-list">
        {relationships.map((relationship) => (
          <li key={relationship.id}>
            <strong>{relationship.label}</strong>
            {relationship.predicate ? ` · ${relationship.predicate}` : ""}
            {relationship.summary ? ` — ${relationship.summary}` : ""}
          </li>
        ))}
      </ul>
    </section>
  );
}

function DefaultActions({ model }: { model: GraphObjectCardViewModel }) {
  const actions = model.actions ?? [];
  if (!actions.length) return null;

  return (
    <section aria-label="Actions">
      <h5>Actions</h5>
      <div className="graph-review-card-actions">
        {actions.map((action) =>
          action.href ? (
            <a key={action.id} href={action.href} title={action.helpText}>
              {action.label}
            </a>
          ) : (
            <button
              key={action.id}
              type="button"
              disabled={action.disabled}
              title={action.helpText}
              onClick={action.onClick}
            >
              {action.label}
            </button>
          ),
        )}
      </div>
    </section>
  );
}

function DefaultDetails({
  model,
  mode,
}: {
  model: GraphObjectCardViewModel;
  mode: GraphObjectCardMode;
}) {
  const details = model.details;
  const evidence = model.evidence ?? [];
  const sourceDomains = details?.sourceDomains ?? model.sourceDomains ?? [];
  const evidenceCount = details?.evidenceCount ?? evidence.length;
  const hasBody =
    Boolean(details?.visibilityLabel || model.visibilityLabel) ||
    Boolean(details?.sourceAnchorText) ||
    Boolean(details?.nodeId) ||
    evidenceCount > 0 ||
    sourceDomains.length > 0 ||
    Boolean(details?.lines?.length) ||
    Boolean(model.freshnessLabel);

  if (!hasBody) return null;

  return (
    <details className="graph-review-details-panel">
      <summary>Details</summary>
      {(details?.visibilityLabel || model.visibilityLabel || model.freshnessLabel) ? (
        <section className="graph-review-details-section" aria-label="Memory and visibility">
          {details?.visibilityLabel || model.visibilityLabel ? (
            <p className="graph-review-muted">
              Visibility: {details?.visibilityLabel ?? model.visibilityLabel}
            </p>
          ) : null}
          {model.freshnessLabel ? (
            <p className="graph-review-muted">Freshness: {model.freshnessLabel}</p>
          ) : null}
        </section>
      ) : null}
      <section className="graph-review-details-section" aria-label="Evidence and source">
        <h6>Evidence and source</h6>
        <p>
          {evidenceCount} evidence badge
          {evidenceCount === 1 ? "" : "s"}
          {sourceDomains.length
            ? `; source domains: ${sourceDomains.join(", ")}`
            : "; no source domains"}
          .
        </p>
        {details?.sourceAnchorText ? (
          <p>
            <strong>Source phrase:</strong> {details.sourceAnchorText}
          </p>
        ) : null}
        {evidence.map((item) => (
          <p key={item.id} className="graph-review-muted">
            {item.label ?? item.id}
            {item.sourceDomain ? ` · ${item.sourceDomain}` : ""}
          </p>
        ))}
      </section>
      {details?.lines?.length ? (
        <section className="graph-review-details-section" aria-label="Additional details">
          {details.lines.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </section>
      ) : null}
      {details?.nodeId && mode === "plan" ? (
        <section className="graph-review-details-section" aria-label="Identifiers">
          <h6>Identifiers</h6>
          <p>
            <strong>Node ID:</strong> {details.nodeId}
          </p>
        </section>
      ) : null}
    </details>
  );
}

/**
 * Neutral graph-object card for Plan and Graph Review.
 *
 * Review-only machinery (lane labels, delta IDs, merge internals, authoring,
 * comparison status) must be injected via slots from Graph Review — never baked
 * into plan mode defaults.
 */
export function GraphObjectCard({
  model,
  mode = "plan",
  relationshipsSlot,
  actionsSlot,
  detailsSlot,
  className = "graph-review-node-game-card",
  "aria-label": ariaLabel,
}: GraphObjectCardProps) {
  return (
    <article
      className={className}
      data-graph-object-card-mode={mode}
      aria-label={ariaLabel ?? `${model.label} game card`}
    >
      <GraphObjectIdentityHeader model={model} />
      {relationshipsSlot ?? <DefaultRelationships model={model} />}
      <GraphObjectSummary model={model} />
      {actionsSlot ?? <DefaultActions model={model} />}
      {detailsSlot ?? <DefaultDetails model={model} mode={mode} />}
    </article>
  );
}
