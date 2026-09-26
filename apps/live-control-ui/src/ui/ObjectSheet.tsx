import { useState } from "react";

import {
  friendlyVisibilityCopy,
  MAX_DEFAULT_RELATIONSHIP_ROWS,
  relationshipRowPrimaryCopy,
  selectDefaultRelationshipRows,
} from "../graphObjectCard/graphObjectDisplay";
import type { GraphObjectCardViewModel } from "../graphObjectCard/types";
import { Badge, Button, Surface } from "./primitives";

import "./ObjectSheet.css";

export interface ObjectSheetProps {
  model: GraphObjectCardViewModel;
}

/** A static presentation study over the existing World-object view model. */
export function ObjectSheet({ model }: ObjectSheetProps) {
  const [expandedObjectId, setExpandedObjectId] = useState<string | null>(null);
  const expanded = expandedObjectId === model.id;
  const relationships = model.relationships ?? [];
  const { rows, omittedCount } = selectDefaultRelationshipRows(
    relationships,
    expanded ? relationships.length : MAX_DEFAULT_RELATIONSHIP_ROWS,
  );
  const summary = model.gameSummary ?? model.summary;
  const aliases = model.aliases?.filter((alias) => alias.trim()) ?? [];
  const evidence = model.evidence ?? [];
  const sourceDomains = model.details?.sourceDomains ?? model.sourceDomains ?? [];
  const evidenceCount = model.details?.evidenceCount ?? evidence.length;
  const visibility = model.details?.visibilityLabel ?? model.visibilityLabel;
  const hasSource = Boolean(
    visibility || model.freshnessLabel || evidenceCount || sourceDomains.length
      || model.details?.sourceAnchorText || model.details?.lines?.length,
  );

  return (
    <Surface tone="paper" className="object-sheet" aria-label={`${model.label} object sheet`}>
      <header className="object-sheet__header">
        <div className="object-sheet__identity">
          <h2>{model.label}</h2>
          <div className="object-sheet__identity-meta">
            <Badge>{model.typeBadgeLabel}</Badge>
            {model.secondaryRoleLabel ? <span>{model.secondaryRoleLabel}</span> : null}
            {model.campaignLabel ? <Badge>{model.campaignLabel}</Badge> : null}
          </div>
        </div>
        {aliases.length ? <p className="object-sheet__aliases">Also known as {aliases.join(", ")}</p> : null}
      </header>

      {summary || model.whyItMattersNow ? (
        <section className="object-sheet__at-table" aria-label="At the table">
          <h3>At the table</h3>
          {summary ? <p className="object-sheet__summary">{summary}</p> : null}
          {model.whyItMattersNow ? (
            <p className="object-sheet__why-now">
              <strong>Why it matters now</strong> {model.whyItMattersNow}
            </p>
          ) : null}
        </section>
      ) : null}

      {relationships.length ? (
        <section className="object-sheet__connections" aria-label="Connected objects">
          <h3>Connected objects</h3>
          <ul>
            {rows.map((relationship) => (
              <li key={relationship.id}>{relationshipRowPrimaryCopy(relationship)}</li>
            ))}
          </ul>
          {relationships.length > MAX_DEFAULT_RELATIONSHIP_ROWS ? (
            <Button
              className="object-sheet__disclosure"
              aria-expanded={expanded}
              onClick={() => setExpandedObjectId(expanded ? null : model.id)}
            >
              {expanded
                ? "Show fewer"
                : `Show all ${relationships.length} relationships (${omittedCount} more)`}
            </Button>
          ) : null}
        </section>
      ) : null}

      {hasSource ? (
        <details className="object-sheet__source">
          <summary>Source and provenance</summary>
          {visibility ? <p>Visibility: {friendlyVisibilityCopy(visibility)}</p> : null}
          {model.freshnessLabel ? <p>Freshness: {model.freshnessLabel}</p> : null}
          {sourceDomains.length ? <p>Sources: {sourceDomains.join(", ")}</p> : null}
          {evidenceCount ? <p>{evidenceCount} evidence {evidenceCount === 1 ? "item" : "items"}</p> : null}
          {model.details?.sourceAnchorText ? (
            <p>Source phrase: {model.details.sourceAnchorText}</p>
          ) : null}
          {evidence.some((item) => item.label) ? (
            <ul>
              {evidence.filter((item) => item.label).map((item) => <li key={item.id}>{item.label}</li>)}
            </ul>
          ) : null}
          {model.details?.lines?.map((line) => <p key={line}>{line}</p>)}
        </details>
      ) : null}
    </Surface>
  );
}
