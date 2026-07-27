import { useState } from "react";

import { GraphObjectCard } from "../../graphObjectCard";
import { GraphObjectProjectionCard } from "../../graphObjectCard/GraphObjectProjectionCard";
import { buildPlanIngestHref } from "../config/planSessionDescriptor";
import { useOptionalProjection } from "../projection/projectionContext";
import type { PlanSessionDescriptor } from "../types";
import { buildGraphObjectCardFromCorpusFallback } from "./buildGraphObjectCardFromCorpusFallback";
import { buildPlanGraphObjectActions } from "./buildPlanGraphObjectActions";
import type { PlanGraphProjectionState, PlanReferenceResolution } from "./graphAwareReferenceResolver";
import { usePlanGraphReferenceResolver } from "./usePlanGraphReferenceResolver";

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
    return "World Graph projection is still loading. Resolution may change once graph memory is available.";
  }
  if (projectionState === "unavailable") {
    return "World Graph projection is unavailable. Showing corpus fallback or unresolved state.";
  }
  if (projectionState === "error") {
    return "World Graph projection failed to load. Corpus fallback is disabled until the graph recovers.";
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
        <a href={ingestHref}>Fix memory in /ingest</a>
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
  const projection = useOptionalProjection();
  const { resolvePlanRelationship, projectionState: resolverProjectionState } =
    usePlanGraphReferenceResolver();
  const [navigatingRelationshipId, setNavigatingRelationshipId] = useState<string | null>(null);

  const effectiveProjectionState =
    projectionState ?? resolution.graphProjectionState ?? resolverProjectionState ?? null;
  const onOpenStatblock = projection ? () => projection.openTool("statblock") : undefined;
  // Compact chip open stays glance-only; Expand (or relationship navigation) unlocks provenance.
  const showRelationshipProvenance =
    projection?.active?.kind === "content" ? projection.active.glanceOnly !== true : true;

  const relationshipsDisabled =
    Boolean(navigatingRelationshipId)
    || resolverProjectionState === "loading"
    || resolverProjectionState === "error";

  if (resolution.kind === "graph-node" && resolution.graphObject) {
    const model = {
      ...resolution.graphObject,
      actions: buildPlanGraphObjectActions({
        resolution,
        sessionDescriptor,
        onOpenStatblock,
      }),
    };

    return (
      <GraphObjectProjectionCard
        model={model}
        mode="plan"
        aria-label={`${model.label} graph object`}
        showRelationshipProvenance={showRelationshipProvenance}
        onSelectRelationshipTarget={
          projection
            ? async (targetId) => {
                if (!projection?.openPlanReferenceResolution || navigatingRelationshipId) return;
                if (resolverProjectionState === "loading" || resolverProjectionState === "error") return;
                const relationship = (model.relationships ?? []).find((row) => row.targetId === targetId);
                if (!relationship) return;
                setNavigatingRelationshipId(relationship.id);
                try {
                  const nextResolution = await resolvePlanRelationship(relationship);
                  projection.openPlanReferenceResolution(
                    nextResolution,
                    nextResolution.graphProjectionState ?? effectiveProjectionState,
                  );
                } finally {
                  setNavigatingRelationshipId(null);
                }
              }
            : undefined
        }
        selectedRelationshipId={navigatingRelationshipId}
        disabled={relationshipsDisabled}
      />
    );
  }

  if (resolution.kind === "corpus-index") {
    const fallbackModel = buildGraphObjectCardFromCorpusFallback(resolution);
    if (fallbackModel) {
      const model = {
        ...fallbackModel,
        actions: buildPlanGraphObjectActions({
          resolution,
          sessionDescriptor,
          onOpenStatblock,
        }),
      };

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
            showRelationshipProvenance={showRelationshipProvenance}
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
