import { GraphObjectCard } from "../../graphObjectCard";
import { buildPlanIngestHref } from "../config/planSessionDescriptor";
import type { PlanSessionDescriptor } from "../types";
import { buildGraphObjectCardFromCorpusFallback } from "./buildGraphObjectCardFromCorpusFallback";
import type { PlanGraphProjectionState, PlanReferenceResolution } from "./graphAwareReferenceResolver";

export interface PlanReferenceObjectCardProps {
  resolution: PlanReferenceResolution;
  sessionDescriptor?: PlanSessionDescriptor;
  projectionState?: PlanGraphProjectionState | null;
}

function projectionStateNote(
  projectionState: PlanGraphProjectionState | null | undefined,
  resolution: PlanReferenceResolution,
): string | null {
  if (resolution.kind === "graph-node") return null;

  if (projectionState === "loading") {
    return "Union Supergraph projection is still loading. Resolution may change once graph memory is available.";
  }
  if (projectionState === "unavailable") {
    return "Union Supergraph projection is unavailable. Showing corpus fallback or unresolved state.";
  }
  if (projectionState === "error") {
    return "Union Supergraph projection failed to load. Showing corpus fallback or unresolved state.";
  }
  if (projectionState === "ready") {
    return "Graph memory did not resolve this reference.";
  }
  return null;
}

function PlanReferenceFallbackBanner({
  resolution,
  projectionState,
}: {
  resolution: PlanReferenceResolution;
  projectionState?: PlanGraphProjectionState | null;
}) {
  const projectionNote = projectionStateNote(projectionState, resolution);

  return (
    <div
      className="plan-reference-object-card__banner plan-reference-object-card__banner--fallback"
      role="status"
      data-testid="plan-reference-fallback-banner"
    >
      <p>
        Graph memory did not resolve this yet. Corpus index fallback found{" "}
        <strong>{resolution.fallback?.ref.label ?? resolution.locator}</strong>.
      </p>
      {projectionNote ? <p className="plan-reference-object-card__muted">{projectionNote}</p> : null}
    </div>
  );
}

function PlanReferenceUnresolvedCard({
  resolution,
  sessionDescriptor,
  projectionState,
}: PlanReferenceObjectCardProps) {
  const ingestHref = sessionDescriptor ? buildPlanIngestHref(sessionDescriptor) : "/ingest";
  const ambiguousIds = resolution.ambiguousNodeIds ?? [];
  const projectionNote = projectionStateNote(projectionState, resolution);

  return (
    <article
      className="plan-reference-object-card plan-reference-object-card--unresolved"
      aria-label={`${resolution.fallback?.ref.label ?? resolution.locator} unresolved reference`}
      data-testid="plan-reference-unresolved-card"
    >
      <header className="plan-reference-object-card__header">
        <p className="plan-surface-kicker">Graph memory</p>
        <h3>{resolution.fallback?.ref.label ?? resolution.locator}</h3>
      </header>
      <p className="plan-reference-object-card__message">
        {resolution.message
          ?? "Could not uniquely resolve this object from graph memory. Use /ingest to review aliases or identity."}
      </p>
      {projectionNote ? <p className="plan-reference-object-card__muted">{projectionNote}</p> : null}
      <p>
        <a href={ingestHref}>Open /ingest to review memory</a>
      </p>
      {ambiguousIds.length ? (
        <details className="plan-reference-object-card__technical-details">
          <summary>Matching graph node ids</summary>
          <ul>
            {ambiguousIds.map((nodeId) => (
              <li key={nodeId}>
                <code>{nodeId}</code>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </article>
  );
}

/**
 * Forward Plan selected-object renderer for graph-aware reference resolution.
 */
export function PlanReferenceObjectCard({
  resolution,
  sessionDescriptor,
  projectionState,
}: PlanReferenceObjectCardProps) {
  const effectiveProjectionState = projectionState ?? resolution.graphProjectionState ?? null;

  if (resolution.kind === "graph-node" && resolution.graphObject) {
    return (
      <GraphObjectCard
        mode="plan"
        model={resolution.graphObject}
        aria-label={`${resolution.graphObject.label} graph object`}
      />
    );
  }

  if (resolution.kind === "corpus-index") {
    const model = buildGraphObjectCardFromCorpusFallback(resolution);
    if (model) {
      return (
        <div className="plan-reference-object-card plan-reference-object-card--corpus-fallback">
          <PlanReferenceFallbackBanner
            resolution={resolution}
            projectionState={effectiveProjectionState}
          />
          <GraphObjectCard
            mode="plan"
            model={model}
            aria-label={`${model.label} corpus fallback object`}
          />
        </div>
      );
    }
  }

  return (
    <PlanReferenceUnresolvedCard
      resolution={resolution}
      sessionDescriptor={sessionDescriptor}
      projectionState={effectiveProjectionState}
    />
  );
}
