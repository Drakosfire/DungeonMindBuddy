import { useRef, type ReactNode, type RefObject } from "react";

import type {
  GraphObjectActionViewModel,
  GraphObjectCardMode,
  GraphObjectCardViewModel,
  GraphObjectRelationshipViewModel,
} from "./types";

export interface GraphObjectCardProps {
  model: GraphObjectCardViewModel;
  mode?: GraphObjectCardMode;
  /** When true, plan-mode details may show raw node identifiers. */
  showDebugIdentifiers?: boolean;
  /** When provided, related objects render as buttons and invoke this callback. */
  onSelectRelationship?: (relationship: GraphObjectRelationshipViewModel) => void;
  /** Optional highlight for the active relationship row. */
  selectedRelationshipId?: string | null;
  /** Disables relationship buttons (e.g. while navigating). */
  relationshipsDisabled?: boolean;
  /** Optional override for related-objects body (e.g. Graph Review chips). */
  relationshipsSlot?: ReactNode;
  /** Optional override for actions body (e.g. review staging / evidence). */
  actionsSlot?: ReactNode;
  /** Optional override for collapsed details (e.g. review status / merge provenance). */
  detailsSlot?: ReactNode;
  className?: string;
  "aria-label"?: string;
}

function relationshipPrimaryCopy(relationship: GraphObjectRelationshipViewModel): string {
  const parts = [relationship.label];
  if (relationship.predicate) parts.push(relationship.predicate);
  if (relationship.summary) parts.push(relationship.summary);
  return parts.join(" · ");
}

function DefaultRelationships({
  model,
  onSelectRelationship,
  selectedRelationshipId,
  relationshipsDisabled,
}: {
  model: GraphObjectCardViewModel;
  onSelectRelationship?: (relationship: GraphObjectRelationshipViewModel) => void;
  selectedRelationshipId?: string | null;
  relationshipsDisabled?: boolean;
}) {
  const relationships = model.relationships ?? [];
  if (!relationships.length) return null;

  return (
    <section
      className="graph-object-card__relationships"
      aria-label="Connected objects and relationships"
    >
      <h5>Related objects</h5>
      <ul className="graph-object-card__relationship-list">
        {relationships.map((relationship) => {
          const copy = (
            <>
              <strong>{relationship.label}</strong>
              {relationship.predicate ? ` · ${relationship.predicate}` : ""}
              {relationship.summary ? ` — ${relationship.summary}` : ""}
            </>
          );

          if (!onSelectRelationship) {
            return <li key={relationship.id}>{copy}</li>;
          }

          const selected = selectedRelationshipId === relationship.id;
          return (
            <li key={relationship.id}>
              <button
                type="button"
                className={
                  selected
                    ? "graph-object-card__relationship-button graph-object-card__relationship-button--selected"
                    : "graph-object-card__relationship-button"
                }
                disabled={relationshipsDisabled}
                aria-label={`Open related object ${relationshipPrimaryCopy(relationship)}`}
                onClick={() => onSelectRelationship(relationship)}
              >
                {copy}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function GraphObjectIdentityHeader({ model }: { model: GraphObjectCardViewModel }) {
  const aliases = model.aliases ?? [];

  return (
    <header className="graph-object-card__identity-header">
      <div className="graph-object-card__title-row">
        <span
          className="graph-object-card__type-badge"
          aria-label={`Object type: ${model.typeBadgeLabel}`}
        >
          {model.typeBadgeLabel}
        </span>
        <h4>{model.label}</h4>
      </div>
      {model.secondaryRoleLabel ? (
        <p className="graph-object-card__role-subtitle">{model.secondaryRoleLabel}</p>
      ) : null}
      {aliases.length ? (
        <p className="graph-object-card__aliases">Also known as: {aliases.join(", ")}</p>
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
        <p className="graph-object-card__why-now">{model.whyItMattersNow}</p>
      ) : null}
    </section>
  );
}

function resolveActionHandler(
  action: GraphObjectActionViewModel,
  rootRef: RefObject<HTMLElement | null>,
): (() => void) | undefined {
  if (action.onClick) return action.onClick;
  if (action.kind === "open-source") {
    return () => {
      const details = rootRef.current?.querySelector(".graph-object-card__details");
      if (!(details instanceof HTMLDetailsElement)) return;
      details.open = true;
      if (typeof details.scrollIntoView === "function") {
        details.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    };
  }
  return undefined;
}

function DefaultActions({
  model,
  rootRef,
}: {
  model: GraphObjectCardViewModel;
  rootRef: RefObject<HTMLElement | null>;
}) {
  const actions = model.actions ?? [];
  if (!actions.length) return null;

  return (
    <section aria-label="Actions">
      <h5>Actions</h5>
      <div className="graph-object-card__actions">
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
              onClick={resolveActionHandler(action, rootRef)}
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
  showDebugIdentifiers,
}: {
  model: GraphObjectCardViewModel;
  mode: GraphObjectCardMode;
  showDebugIdentifiers: boolean;
}) {
  const details = model.details;
  const evidence = model.evidence ?? [];
  const sourceDomains = details?.sourceDomains ?? model.sourceDomains ?? [];
  const evidenceCount = details?.evidenceCount ?? evidence.length;
  const showIdentifiers =
    mode === "plan" && showDebugIdentifiers && Boolean(details?.nodeId);
  const hasBody =
    Boolean(details?.visibilityLabel || model.visibilityLabel) ||
    Boolean(details?.sourceAnchorText) ||
    showIdentifiers ||
    evidenceCount > 0 ||
    sourceDomains.length > 0 ||
    Boolean(details?.lines?.length) ||
    Boolean(model.freshnessLabel);

  if (!hasBody) return null;

  return (
    <details className="graph-object-card__details">
      <summary>Details</summary>
      {(details?.visibilityLabel || model.visibilityLabel || model.freshnessLabel) ? (
        <section className="graph-object-card__details-section" aria-label="Memory and visibility">
          {details?.visibilityLabel || model.visibilityLabel ? (
            <p className="graph-object-card__muted">
              Visibility: {details?.visibilityLabel ?? model.visibilityLabel}
            </p>
          ) : null}
          {model.freshnessLabel ? (
            <p className="graph-object-card__muted">Freshness: {model.freshnessLabel}</p>
          ) : null}
        </section>
      ) : null}
      <section className="graph-object-card__details-section" aria-label="Evidence and source">
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
          <p key={item.id} className="graph-object-card__muted">
            {item.label ?? item.id}
            {item.sourceDomain ? ` · ${item.sourceDomain}` : ""}
          </p>
        ))}
      </section>
      {details?.lines?.length ? (
        <section className="graph-object-card__details-section" aria-label="Additional details">
          {details.lines.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </section>
      ) : null}
      {showIdentifiers ? (
        <section className="graph-object-card__details-section" aria-label="Identifiers">
          <h6>Identifiers</h6>
          <p>
            <strong>Node ID:</strong> {details?.nodeId}
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
  showDebugIdentifiers = false,
  onSelectRelationship,
  selectedRelationshipId = null,
  relationshipsDisabled = false,
  relationshipsSlot,
  actionsSlot,
  detailsSlot,
  className = "graph-object-card",
  "aria-label": ariaLabel,
}: GraphObjectCardProps) {
  const rootRef = useRef<HTMLElement>(null);

  return (
    <article
      ref={rootRef}
      className={className}
      data-graph-object-card-mode={mode}
      aria-label={ariaLabel ?? `${model.label} game card`}
    >
      <GraphObjectIdentityHeader model={model} />
      {relationshipsSlot ?? (
        <DefaultRelationships
          model={model}
          onSelectRelationship={onSelectRelationship}
          selectedRelationshipId={selectedRelationshipId}
          relationshipsDisabled={relationshipsDisabled}
        />
      )}
      <GraphObjectSummary model={model} />
      {actionsSlot ?? <DefaultActions model={model} rootRef={rootRef} />}
      {detailsSlot ?? (
        <DefaultDetails
          model={model}
          mode={mode}
          showDebugIdentifiers={showDebugIdentifiers}
        />
      )}
    </article>
  );
}
