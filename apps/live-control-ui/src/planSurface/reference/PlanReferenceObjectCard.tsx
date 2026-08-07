import { useCallback, useEffect, useRef, useState } from "react";

import { GraphObjectCard } from "../../graphObjectCard";
import type { GraphObjectRelationshipViewModel } from "../../graphObjectCard";
import { ResolvedGraphObjectProjection } from "../../graphReference/ResolvedGraphObjectProjection";
import type {
  GraphReferenceProjectionBinding,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
} from "../../graphReference/types";
import { buildPlanIngestHref } from "../config/planSessionDescriptor";
import type { PlanSessionDescriptor } from "../types";
import { buildGraphObjectCardFromCorpusFallback } from "./buildGraphObjectCardFromCorpusFallback";
import { buildPlanGraphObjectActions } from "./buildPlanGraphObjectActions";

export interface PlanReferenceObjectCardProps {
  resolution: GraphReferenceResolution;
  sessionDescriptor?: PlanSessionDescriptor;
  projectionState?: GraphReferenceProjectionState | null;
  /** Explicit registered graph projection binding; absent → content only, actions fail closed. */
  graphReferenceBinding?: GraphReferenceProjectionBinding | null;
  /** Compact chip open stays glance-only; Expand unlocks relationship provenance. */
  glanceOnly?: boolean;
}

function projectionStateNote(
  projectionState: GraphReferenceProjectionState | null | undefined,
  resolution: GraphReferenceResolution,
): string | null {
  if (resolution.kind === "resolved_graph") return null;

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
  resolution: Extract<GraphReferenceResolution, { kind: "resolved_corpus_fallback" }>;
  projectionState?: GraphReferenceProjectionState | null;
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
        <strong>{resolution.fallback.ref.label ?? resolution.locator}</strong>.
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
  const ambiguousIds = resolution.kind === "ambiguous" ? resolution.matchingGraphNodeIds : [];
  const projectionNote = projectionStateNote(projectionState, resolution);
  const title = resolution.reference?.label ?? resolution.locator;

  return (
    <article
      className="plan-reference-object-card plan-reference-object-card--unresolved"
      aria-label={`${title} unresolved reference`}
      data-testid="plan-reference-unresolved-card"
    >
      <header className="plan-reference-object-card__header">
        <p className="plan-surface-kicker">Graph memory</p>
        <h3>{title}</h3>
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
 * Consumes explicit props/binding only — no route-local resolver or projection hooks.
 * Graph-native rendering goes through the shared GraphObjectProjectionCard.
 */
export function PlanReferenceObjectCard({
  resolution,
  sessionDescriptor,
  projectionState,
  graphReferenceBinding = null,
  glanceOnly = false,
}: PlanReferenceObjectCardProps) {
  const [navigatingRelationshipId, setNavigatingRelationshipId] = useState<string | null>(null);
  const graphReferenceBindingRef = useRef(graphReferenceBinding);
  graphReferenceBindingRef.current = graphReferenceBinding;
  const selectedObjectKey = resolution.kind === "resolved_graph"
    ? [
        resolution.kind,
        resolution.graphNodeId,
        resolution.graphScope?.worldId ?? "",
        resolution.graphScope?.campaignId ?? "",
        resolution.graphScope?.scopeMode ?? "",
        resolution.graphScope?.revisionId ?? "",
      ].join("\0")
    : [resolution.kind, resolution.locator].join("\0");
  const selectedObjectKeyRef = useRef<string | null>(null);
  const navigationGenerationRef = useRef(0);
  const mountedRef = useRef(false);
  if (selectedObjectKeyRef.current !== selectedObjectKey) {
    selectedObjectKeyRef.current = selectedObjectKey;
    navigationGenerationRef.current += 1;
  }

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      navigationGenerationRef.current += 1;
    };
  }, []);
  useEffect(() => {
    setNavigatingRelationshipId(null);
  }, [selectedObjectKey]);

  const resolverProjectionState = graphReferenceBinding?.resolverState ?? null;
  const effectiveProjectionState =
    projectionState ?? resolution.projectionState ?? resolverProjectionState ?? null;
  const onOpenStatblock = graphReferenceBinding
    ? () => {
        const current = graphReferenceBindingRef.current;
        if (!current) return;
        current.openTool("statblock");
      }
    : undefined;
  const showRelationshipProvenance = glanceOnly !== true;

  const onSelectRelationship = useCallback(
    async (relationship: GraphObjectRelationshipViewModel) => {
      const bindingAtStart = graphReferenceBinding;
      if (!bindingAtStart || navigatingRelationshipId) return;
      if (resolverProjectionState === "loading" || resolverProjectionState === "error") return;

      const generationAtStart = navigationGenerationRef.current;
      const selectedObjectKeyAtStart = selectedObjectKey;
      setNavigatingRelationshipId(relationship.id);
      try {
        const nextResolution = await bindingAtStart.resolveRelationship(
          relationship,
          resolution.kind === "resolved_graph" ? resolution.graphScope : undefined,
        );
        // Stale-operation rule: binding and selected-object identity must both survive.
        const current = graphReferenceBindingRef.current;
        if (
          !mountedRef.current
          || !current
          || current !== bindingAtStart
          || navigationGenerationRef.current !== generationAtStart
          || selectedObjectKeyRef.current !== selectedObjectKeyAtStart
        ) return;
        current.openResolvedReference(
          nextResolution,
          nextResolution.projectionState ?? effectiveProjectionState,
        );
      } finally {
        if (
          mountedRef.current
          && navigationGenerationRef.current === generationAtStart
        ) {
          setNavigatingRelationshipId(null);
        }
      }
    },
    [
      effectiveProjectionState,
      navigatingRelationshipId,
      graphReferenceBinding,
      resolverProjectionState,
      resolution,
      selectedObjectKey,
    ],
  );

  const relationshipsDisabled =
    Boolean(navigatingRelationshipId)
    || resolverProjectionState === "loading"
    || resolverProjectionState === "error";

  if (resolution.kind === "resolved_graph") {
    const model = {
      ...resolution.graphObject,
      actions: buildPlanGraphObjectActions({
        resolution,
        sessionDescriptor,
        onOpenStatblock,
      }),
    };

    return (
      <ResolvedGraphObjectProjection
        resolution={resolution}
        glanceOnly={glanceOnly}
        graphReferenceBinding={graphReferenceBinding}
        projectionState={effectiveProjectionState}
        sessionDescriptor={sessionDescriptor}
        model={model}
        mode="plan"
        showRelationshipProvenance={showRelationshipProvenance}
        onSelectRelationship={graphReferenceBinding ? onSelectRelationship : undefined}
        selectedRelationshipId={navigatingRelationshipId}
        relationshipsDisabled={relationshipsDisabled}
        aria-label={`${model.label} graph object`}
      />
    );
  }

  if (resolution.kind === "resolved_corpus_fallback") {
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
