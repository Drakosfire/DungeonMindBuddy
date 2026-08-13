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

export interface PlayReferenceObjectProjectionProps {
  bindings: Readonly<Record<string, unknown>>;
  glanceOnly?: boolean;
}

function PlayReferenceUnresolvedCard({ resolution }: { resolution: GraphReferenceResolution }) {
  const title = resolution.reference?.label ?? resolution.locator;
  return (
    <article
      className="play-reference-object-projection play-reference-object-projection--unresolved"
      aria-label={`${title} unresolved reference`}
      data-testid="play-reference-unresolved-card"
    >
      <header>
        <p>Play reference</p>
        <h3>{title}</h3>
      </header>
      <p>{resolution.message ?? "Could not resolve this object."}</p>
    </article>
  );
}

export function PlayReferenceObjectProjection({
  bindings,
  glanceOnly = false,
}: PlayReferenceObjectProjectionProps) {
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

  return <PlayReferenceUnresolvedCard resolution={resolution} />;
}
