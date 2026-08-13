import "./playObjectSheetProjection.css";

import {
  GraphObjectEvidenceRows,
  type GraphObjectCardViewModel,
  type GraphObjectEvidenceViewModel,
  type GraphObjectRelationshipViewModel,
} from "../graphObjectCard";
import {
  graphObjectTypeBadgeLabel,
  selectDefaultRelationshipRows,
} from "../graphObjectCard/graphObjectDisplay";
import type { PlayObjectBody, PlayObjectKind } from "./ofConksPlayObjectBridge";
import { playObjectBodyForNodeId } from "./ofConksPlayObjectBridge";
import type { GraphReferenceResolution } from "./types";

export type PlayObjectSheetProjectionProps = {
  resolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }>;
  model: GraphObjectCardViewModel;
  body?: PlayObjectBody | null;
  glanceOnly?: boolean;
  onSelectRelationship?: (relationship: GraphObjectRelationshipViewModel) => void;
  selectedRelationshipId?: string | null;
  relationshipsDisabled?: boolean;
  onReadSourceEvidence?: (evidence: GraphObjectEvidenceViewModel) => void;
  resolvingEvidenceId?: string | null;
  evidenceErrors?: Record<string, string>;
};

function sectionTitles(kind: PlayObjectKind): {
  atTable: string;
  attitude: string;
  offers: string;
} {
  switch (kind) {
    case "location":
      return {
        atTable: "Arrival",
        attitude: "What’s happening",
        offers: "Who’s here / what can happen",
      };
    case "item":
      return {
        atTable: "What it does",
        attitude: "Who wants it",
        offers: "Hooks",
      };
    case "faction":
      return {
        atTable: "At the table",
        attitude: "Pressure",
        offers: "Hooks",
      };
    case "npc":
    default:
      return {
        atTable: "At the table",
        attitude: "Attitude",
        offers: "Offers & hooks",
      };
  }
}

function connectedAsRelationship(
  chip: PlayObjectBody["connectedNow"][number],
): GraphObjectRelationshipViewModel {
  return {
    id: `play-connected:${chip.nodeId}`,
    label: chip.label,
    targetId: chip.nodeId,
    predicate: "related",
    direction: "related",
  };
}

/**
 * Table-first parchment sheet for Of Conks packet NPC/location/item (and faction) nodes.
 * Threats stay on ThreatSheetProjection.
 */
export function PlayObjectSheetProjection({
  resolution,
  model,
  body: bodyProp,
  glanceOnly = false,
  onSelectRelationship,
  selectedRelationshipId = null,
  relationshipsDisabled = false,
  onReadSourceEvidence,
  resolvingEvidenceId = null,
  evidenceErrors = {},
}: PlayObjectSheetProjectionProps) {
  const body = bodyProp ?? playObjectBodyForNodeId(resolution.graphNodeId);
  if (!body) {
    return null;
  }

  const titles = sectionTitles(body.kind);
  const typeBadge = graphObjectTypeBadgeLabel(model.kind, model.role);
  const aliases = model.aliases ?? [];
  const graphRelationships = model.relationships ?? [];
  const { rows: relatedRows, omittedCount } = selectDefaultRelationshipRows(graphRelationships);
  const evidence = model.evidence ?? [];
  const details = model.details;

  if (glanceOnly) {
    return (
      <article
        className="plan-reference-object-card plan-reference-object-card--play-object-sheet play-object-sheet play-object-sheet--glance"
        aria-label={`${model.label} play sheet`}
        data-testid="play-object-sheet"
        data-play-object-kind={body.kind}
      >
        <header className="play-object-sheet__header">
          <span className="play-object-sheet__type-badge">{typeBadge}</span>
          <h4 className="play-object-sheet__title">{model.label}</h4>
        </header>
        <p className="play-object-sheet__glance-line">{body.atTable}</p>
      </article>
    );
  }

  return (
    <article
      className="plan-reference-object-card plan-reference-object-card--play-object-sheet play-object-sheet"
      aria-label={`${model.label} play sheet`}
      data-testid="play-object-sheet"
      data-play-object-kind={body.kind}
    >
      <header className="play-object-sheet__header">
        <div className="play-object-sheet__title-row">
          <span className="play-object-sheet__type-badge" aria-label={`Object type: ${typeBadge}`}>
            {typeBadge}
          </span>
          <h4 className="play-object-sheet__title">{model.label}</h4>
          {model.campaignLabel ? (
            <span className="play-object-sheet__campaign-badge">{model.campaignLabel}</span>
          ) : null}
        </div>
        {aliases.length ? (
          <p className="play-object-sheet__aliases">Also known as: {aliases.join(", ")}</p>
        ) : null}
      </header>

      <section className="play-object-sheet__section" aria-label={titles.atTable}>
        <h5>{titles.atTable}</h5>
        <p>{body.atTable}</p>
      </section>

      {body.attitude?.trim() ? (
        <section className="play-object-sheet__section" aria-label={titles.attitude}>
          <h5>{titles.attitude}</h5>
          <p>{body.attitude}</p>
        </section>
      ) : null}

      {body.offersHooks?.length ? (
        <section className="play-object-sheet__section" aria-label={titles.offers}>
          <h5>{titles.offers}</h5>
          <ul>
            {body.offersHooks.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {body.connectedNow.length ? (
        <section
          className="play-object-sheet__section play-object-sheet__connected"
          aria-label="Connected now"
        >
          <h5>Connected now</h5>
          <ul className="play-object-sheet__chip-list">
            {body.connectedNow.map((chip) => {
              const relationship = connectedAsRelationship(chip);
              const selected = selectedRelationshipId === relationship.id;
              if (!onSelectRelationship) {
                return (
                  <li key={chip.nodeId}>
                    <span className="play-object-sheet__chip play-object-sheet__chip--static">
                      {chip.label}
                    </span>
                  </li>
                );
              }
              return (
                <li key={chip.nodeId}>
                  <button
                    type="button"
                    className={
                      selected
                        ? "play-object-sheet__chip play-object-sheet__chip--selected"
                        : "play-object-sheet__chip"
                    }
                    disabled={relationshipsDisabled}
                    aria-label={`Open ${chip.label}`}
                    onClick={() => onSelectRelationship(relationship)}
                  >
                    {chip.label}
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      <details className="play-object-sheet__advanced">
        <summary>Advanced</summary>
        {relatedRows.length ? (
          <section aria-label="Related objects from graph">
            <h6>Related objects</h6>
            <ul className="play-object-sheet__related-list">
              {relatedRows.map((relationship) => (
                <li key={relationship.id}>
                  {relationship.label}
                  {relationship.predicate ? ` · ${relationship.predicate}` : ""}
                </li>
              ))}
            </ul>
            {omittedCount > 0 ? (
              <p className="play-object-sheet__muted">+{omittedCount} more</p>
            ) : null}
          </section>
        ) : (
          <p className="play-object-sheet__muted">No graph adjacency on this node yet.</p>
        )}
        {details ? (
          <section aria-label="Memory and visibility">
            <h6>Memory and visibility</h6>
            {details.visibilityLabel ? (
              <p className="play-object-sheet__muted">Visibility: {details.visibilityLabel}</p>
            ) : null}
            {typeof details.evidenceCount === "number" ? (
              <p className="play-object-sheet__muted">Evidence: {details.evidenceCount}</p>
            ) : null}
            {details.sourceDomains?.length ? (
              <p className="play-object-sheet__muted">
                Domains: {details.sourceDomains.join(", ")}
              </p>
            ) : null}
            {details.nodeId ? (
              <p className="play-object-sheet__muted">Node: {details.nodeId}</p>
            ) : null}
          </section>
        ) : null}
        {evidence.length ? (
          <section aria-label="Evidence and source">
            <h6>Evidence and source</h6>
            <GraphObjectEvidenceRows
              evidence={evidence}
              onReadSourceEvidence={onReadSourceEvidence}
              resolvingEvidenceId={resolvingEvidenceId}
              evidenceErrors={evidenceErrors}
            />
          </section>
        ) : null}
      </details>
    </article>
  );
}

export function shouldRenderPlayObjectSheet(
  resolution: GraphReferenceResolution,
): boolean {
  if (resolution.kind !== "resolved_graph") return false;
  return playObjectBodyForNodeId(resolution.graphNodeId) !== null;
}
