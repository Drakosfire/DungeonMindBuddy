import { useRef, type ReactNode, type RefObject } from "react";

import {
  humanizeRelationshipPredicate,
  relationshipRowPrimaryCopy,
  relationshipSessionStamp,
  selectDefaultRelationshipRows,
} from "./graphObjectDisplay";
import type {
  GraphObjectActionViewModel,
  GraphObjectCardMode,
  GraphObjectCardViewModel,
  GraphObjectEvidenceViewModel,
  GraphObjectRelationshipViewModel,
} from "./types";

export interface GraphObjectCardProps {
  model: GraphObjectCardViewModel;
  mode?: GraphObjectCardMode;
  /** When true, plan-mode details may show raw node identifiers. */
  showDebugIdentifiers?: boolean;
  /**
   * When true (Plan reference Expand), related rows show origin prose under each
   * chronological pill. Compact click keeps pills scan-only.
   */
  showRelationshipProvenance?: boolean;
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
  /** Invoked when the GM chooses Read source on one explicit evidence row. */
  onReadSourceEvidence?: (evidence: GraphObjectEvidenceViewModel) => void;
  /** Disables the clicked evidence row while source navigation resolves. */
  resolvingEvidenceId?: string | null;
  /** Row-local resolver errors keyed by evidence id. */
  evidenceErrors?: Record<string, string>;
  className?: string;
  "aria-label"?: string;
}

function evidenceRowCanReadSource(item: GraphObjectEvidenceViewModel): boolean {
  return Boolean(
    item.canOpenSource && item.sourceArtifactId && item.sourceSpanRefId,
  );
}

export function GraphObjectEvidenceRows({
  evidence,
  onReadSourceEvidence,
  resolvingEvidenceId = null,
  evidenceErrors = {},
}: {
  evidence: GraphObjectEvidenceViewModel[];
  onReadSourceEvidence?: (evidence: GraphObjectEvidenceViewModel) => void;
  resolvingEvidenceId?: string | null;
  evidenceErrors?: Record<string, string>;
}) {
  return (
    <>
      {evidence.map((item) => {
        const canRead = evidenceRowCanReadSource(item);
        const isResolving = resolvingEvidenceId === item.id;
        const error = evidenceErrors[item.id];

        return (
          <div key={item.id} className="graph-object-card__evidence-row">
            <p className="graph-object-card__muted">
              {item.label ?? item.id}
              {item.sourceDomain ? ` · ${item.sourceDomain}` : ""}
            </p>
            {canRead && onReadSourceEvidence ? (
              <>
                <button
                  type="button"
                  className="graph-object-card__read-source-button"
                  disabled={isResolving}
                  onClick={() => onReadSourceEvidence(item)}
                >
                  {isResolving ? "Opening source…" : "Read source"}
                </button>
                {error ? (
                  <p className="graph-object-card__evidence-error" role="alert">
                    {error}
                  </p>
                ) : null}
              </>
            ) : null}
          </div>
        );
      })}
    </>
  );
}

function RelationshipRowBody({
  relationship,
  showProvenance,
}: {
  relationship: GraphObjectRelationshipViewModel;
  showProvenance: boolean;
}) {
  const predicate = humanizeRelationshipPredicate(relationship.predicate);
  const session = relationshipSessionStamp(relationship.sessionIds, relationship.campaignScope);
  const excerpt = relationship.sourceExcerpt?.trim() || null;
  const domain = relationship.sourceDomains?.[0]?.trim() || null;

  return (
    <>
      <span className="graph-object-card__relationship-pill-line">
        {session ? (
          <span className="graph-object-card__relationship-session">{session}</span>
        ) : null}
        <strong>{relationship.label}</strong>
        {predicate ? ` · ${predicate}` : ""}
      </span>
      {showProvenance ? (
        excerpt ? (
          <p className="graph-object-card__relationship-provenance">
            <span className="graph-object-card__relationship-excerpt">“{excerpt}”</span>
            {domain ? (
              <span className="graph-object-card__muted"> · {domain}</span>
            ) : null}
          </p>
        ) : (
          <p className="graph-object-card__muted graph-object-card__relationship-provenance">
            No origin prose in graph memory yet.
          </p>
        )
      ) : null}
    </>
  );
}

function DefaultRelationships({
  model,
  onSelectRelationship,
  selectedRelationshipId,
  relationshipsDisabled,
  showProvenance,
}: {
  model: GraphObjectCardViewModel;
  onSelectRelationship?: (relationship: GraphObjectRelationshipViewModel) => void;
  selectedRelationshipId?: string | null;
  relationshipsDisabled?: boolean;
  showProvenance: boolean;
}) {
  const source = model.relationships ?? [];
  if (!source.length) return null;

  const { rows, omittedCount } = selectDefaultRelationshipRows(source);

  return (
    <section
      className="graph-object-card__relationships"
      aria-label="Connected objects and relationships"
      data-provenance={showProvenance ? "expanded" : "compact"}
    >
      <h5>Related objects</h5>
      <ul className="graph-object-card__relationship-list">
        {rows.map((relationship) => {
          const body = (
            <RelationshipRowBody
              relationship={relationship}
              showProvenance={showProvenance}
            />
          );

          if (!onSelectRelationship) {
            return (
              <li
                key={relationship.id}
                className={
                  showProvenance
                    ? "graph-object-card__relationship-item graph-object-card__relationship-item--provenance"
                    : "graph-object-card__relationship-item"
                }
              >
                {body}
              </li>
            );
          }

          const selected = selectedRelationshipId === relationship.id;
          return (
            <li
              key={relationship.id}
              className={
                showProvenance
                  ? "graph-object-card__relationship-item graph-object-card__relationship-item--provenance"
                  : "graph-object-card__relationship-item"
              }
            >
              <button
                type="button"
                className={
                  selected
                    ? "graph-object-card__relationship-button graph-object-card__relationship-button--selected"
                    : "graph-object-card__relationship-button"
                }
                disabled={relationshipsDisabled}
                aria-label={`Open related object ${relationshipRowPrimaryCopy(relationship)}`}
                onClick={() => onSelectRelationship(relationship)}
              >
                {body}
              </button>
            </li>
          );
        })}
      </ul>
      {omittedCount > 0 ? (
        <p className="graph-object-card__muted">+{omittedCount} more</p>
      ) : null}
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
        {model.campaignLabel ? (
          <span
            className="graph-object-card__campaign-badge"
            aria-label={`Campaign: ${model.campaignLabel}`}
          >
            {model.campaignLabel}
          </span>
        ) : null}
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

function ActionLinks({
  actions,
  rootRef,
}: {
  actions: GraphObjectActionViewModel[];
  rootRef: RefObject<HTMLElement | null>;
}) {
  if (!actions.length) return null;

  return (
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
  );
}

/** Plan-mode: curator links stay available but out of the primary scan path. */
function PlanMemoryTools({
  model,
  rootRef,
}: {
  model: GraphObjectCardViewModel;
  rootRef: RefObject<HTMLElement | null>;
}) {
  const actions = model.actions ?? [];
  if (!actions.length) return null;

  return (
    <details className="graph-object-card__memory-tools">
      <summary>Memory tools</summary>
      <ActionLinks actions={actions} rootRef={rootRef} />
    </details>
  );
}

function DefaultDetails({
  model,
  mode,
  showDebugIdentifiers,
  onReadSourceEvidence,
  resolvingEvidenceId,
  evidenceErrors,
}: {
  model: GraphObjectCardViewModel;
  mode: GraphObjectCardMode;
  showDebugIdentifiers: boolean;
  onReadSourceEvidence?: (evidence: GraphObjectEvidenceViewModel) => void;
  resolvingEvidenceId?: string | null;
  evidenceErrors?: Record<string, string>;
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
        <GraphObjectEvidenceRows
          evidence={evidence}
          onReadSourceEvidence={onReadSourceEvidence}
          resolvingEvidenceId={resolvingEvidenceId}
          evidenceErrors={evidenceErrors}
        />
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
  showRelationshipProvenance = false,
  onSelectRelationship,
  selectedRelationshipId = null,
  relationshipsDisabled = false,
  relationshipsSlot,
  actionsSlot,
  detailsSlot,
  onReadSourceEvidence,
  resolvingEvidenceId = null,
  evidenceErrors = {},
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
      <GraphObjectSummary model={model} />
      {relationshipsSlot ?? (
        <DefaultRelationships
          model={model}
          onSelectRelationship={onSelectRelationship}
          selectedRelationshipId={selectedRelationshipId}
          relationshipsDisabled={relationshipsDisabled}
          showProvenance={showRelationshipProvenance}
        />
      )}
      {detailsSlot ?? (
        <DefaultDetails
          model={model}
          mode={mode}
          showDebugIdentifiers={showDebugIdentifiers}
          onReadSourceEvidence={onReadSourceEvidence}
          resolvingEvidenceId={resolvingEvidenceId}
          evidenceErrors={evidenceErrors}
        />
      )}
      {actionsSlot ?? (mode === "plan" ? <PlanMemoryTools model={model} rootRef={rootRef} /> : null)}
    </article>
  );
}
