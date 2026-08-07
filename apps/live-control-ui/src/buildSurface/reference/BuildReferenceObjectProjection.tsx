import { useCallback, useEffect, useRef, useState } from "react";

import type { GraphObjectRelationshipViewModel } from "../../graphObjectCard";
import {
  readGraphReferenceBinding,
  readGraphReferenceResolutionBinding,
} from "../../graphReference/projectionBindings";
import { ResolvedGraphObjectProjection } from "../../graphReference/ResolvedGraphObjectProjection";
import type {
  GraphReferenceProjectionBinding,
  GraphReferenceResolution,
} from "../../graphReference/types";

export interface BuildReferenceObjectProjectionProps {
  bindings: Readonly<Record<string, unknown>>;
  glanceOnly?: boolean;
}

function BuildReferenceUnresolvedCard({ resolution }: { resolution: GraphReferenceResolution }) {
  const title = resolution.reference?.label ?? resolution.locator;
  const ambiguousIds = resolution.kind === "ambiguous" ? resolution.matchingGraphNodeIds : [];

  return (
    <article
      className="build-reference-object-projection build-reference-object-projection--unresolved"
      aria-label={`${title} unresolved reference`}
      data-testid="build-reference-unresolved-card"
    >
      <header className="build-reference-object-projection__header">
        <p className="build-reference-object-projection__kicker">World Graph</p>
        <h3>{title}</h3>
      </header>
      <p className="build-reference-object-projection__message">
        {resolution.message ?? "Could not resolve this object from graph memory."}
      </p>
      {ambiguousIds.length ? (
        <ul className="build-reference-object-projection__candidates" data-testid="build-reference-ambiguous-ids">
          {ambiguousIds.map((nodeId) => (
            <li key={nodeId}>
              <code>{nodeId}</code>
            </li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}

function BuildReferenceCorpusFallbackBlocked({
  resolution,
}: {
  resolution: Extract<GraphReferenceResolution, { kind: "resolved_corpus_fallback" }>;
}) {
  const title = resolution.reference?.label ?? resolution.fallback.ref.label ?? resolution.locator;
  return (
    <article
      className="build-reference-object-projection build-reference-object-projection--corpus-blocked"
      aria-label={`${title} corpus fallback blocked`}
      data-testid="build-reference-corpus-fallback-blocked"
    >
      <header className="build-reference-object-projection__header">
        <p className="build-reference-object-projection__kicker">World Graph</p>
        <h3>{title}</h3>
      </header>
      <p className="build-reference-object-projection__message" role="alert">
        World Graph inspection only — corpus fallback is not available on Build.
      </p>
    </article>
  );
}

export function BuildReferenceObjectProjection({
  bindings,
  glanceOnly = false,
}: BuildReferenceObjectProjectionProps) {
  const resolution = readGraphReferenceResolutionBinding(bindings);
  const graphReferenceBinding = readGraphReferenceBinding(bindings) ?? null;
  const [navigatingRelationshipId, setNavigatingRelationshipId] = useState<string | null>(null);
  const graphReferenceBindingRef = useRef<GraphReferenceProjectionBinding | null>(graphReferenceBinding);
  graphReferenceBindingRef.current = graphReferenceBinding;
  const mountedRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const resolverProjectionState = graphReferenceBinding?.resolverState ?? null;
  const showRelationshipProvenance = glanceOnly !== true;

  const onSelectRelationship = useCallback(
    async (relationship: GraphObjectRelationshipViewModel) => {
      const bindingAtStart = graphReferenceBinding;
      if (!bindingAtStart || navigatingRelationshipId) return;
      if (resolverProjectionState === "loading" || resolverProjectionState === "error") return;

      setNavigatingRelationshipId(relationship.id);
      try {
        const nextResolution = await bindingAtStart.resolveRelationship(relationship);
        const current = graphReferenceBindingRef.current;
        if (!mountedRef.current || !current || current !== bindingAtStart) return;
        current.openResolvedReference(
          nextResolution,
          nextResolution.projectionState ?? resolverProjectionState,
        );
      } finally {
        if (mountedRef.current) {
          setNavigatingRelationshipId(null);
        }
      }
    },
    [graphReferenceBinding, navigatingRelationshipId, resolverProjectionState],
  );

  const relationshipsDisabled =
    Boolean(navigatingRelationshipId)
    || resolverProjectionState === "loading"
    || resolverProjectionState === "error";

  if (resolution.kind === "resolved_graph") {
    return (
      <ResolvedGraphObjectProjection
        resolution={resolution}
        glanceOnly={glanceOnly}
        graphReferenceBinding={graphReferenceBinding}
        projectionState={resolverProjectionState}
        showRelationshipProvenance={showRelationshipProvenance}
        onSelectRelationship={graphReferenceBinding ? onSelectRelationship : undefined}
        selectedRelationshipId={navigatingRelationshipId}
        relationshipsDisabled={relationshipsDisabled}
        aria-label={`${resolution.graphObject.label} graph object`}
      />
    );
  }

  if (resolution.kind === "resolved_corpus_fallback") {
    return <BuildReferenceCorpusFallbackBlocked resolution={resolution} />;
  }

  if (resolution.kind === "ambiguous" || resolution.kind === "unresolved" || resolution.kind === "error") {
    return <BuildReferenceUnresolvedCard resolution={resolution} />;
  }

  return <BuildReferenceUnresolvedCard resolution={resolution} />;
}
