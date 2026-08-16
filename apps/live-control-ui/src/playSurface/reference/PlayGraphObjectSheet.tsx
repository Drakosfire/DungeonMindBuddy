import { useCallback, useEffect, useRef, useState } from "react";

import type {
  GraphObjectEvidenceViewModel,
  GraphObjectRelationshipViewModel,
} from "../../graphObjectCard";
import { relationshipRowPrimaryCopy } from "../../graphObjectCard/graphObjectDisplay";
import type {
  GraphReferenceProjectionBinding,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
} from "../../graphReference/types";
import { shouldRenderThreatCampaignSheet } from "../../statblocks/projection/threatSheetViewModel";
import { PlayThreatMechanicsSection } from "./PlayThreatMechanicsSection";

export interface PlayGraphReferenceOccurrence {
  graphNodeId: string;
  sourceNodeType: "graphNodeReference" | "runbookReference";
  sceneId?: string | null;
  beatId?: string | null;
  choiceId?: string | null;
  optionId?: string | null;
}

export interface PlayGraphObjectSheetProps {
  resolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }>;
  occurrences?: readonly PlayGraphReferenceOccurrence[];
  graphReferenceBinding?: GraphReferenceProjectionBinding | null;
  projectionState?: GraphReferenceProjectionState | null;
  onReadSourceEvidence?: (evidence: GraphObjectEvidenceViewModel) => void;
}

function occurrenceContextLabel(occurrence: PlayGraphReferenceOccurrence): string {
  const parts = [
    occurrence.sceneId ? `Scene ${occurrence.sceneId}` : null,
    occurrence.beatId ? `Beat ${occurrence.beatId}` : null,
    occurrence.choiceId ? `Choice ${occurrence.choiceId}` : null,
    occurrence.optionId ? `Option ${occurrence.optionId}` : null,
  ].filter((part): part is string => Boolean(part));
  const context = parts.length ? parts.join(" · ") : "Runbook";
  return `${context} (${occurrence.sourceNodeType})`;
}

/**
 * Play object sheet: World identity + Source + optional Runbook occurrence context
 * + exact Threat mechanics. P3B click/open/occurrence derivation is not owned here.
 */
export function PlayGraphObjectSheet({
  resolution,
  occurrences = [],
  graphReferenceBinding = null,
  projectionState = null,
  onReadSourceEvidence,
}: PlayGraphObjectSheetProps) {
  const graphObject = resolution.graphObject;
  const [navigatingRelationshipId, setNavigatingRelationshipId] = useState<string | null>(null);
  const graphReferenceBindingRef = useRef(graphReferenceBinding);
  graphReferenceBindingRef.current = graphReferenceBinding;
  const selectedObjectKey = [
    resolution.graphNodeId,
    resolution.graphScope.worldId,
    resolution.graphScope.campaignId,
    resolution.graphScope.scopeMode,
    resolution.graphScope.revisionId,
  ].join("\0");
  const selectedObjectKeyRef = useRef(selectedObjectKey);
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
  const relationshipsDisabled =
    Boolean(navigatingRelationshipId)
    || resolverProjectionState === "loading"
    || resolverProjectionState === "error";

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
          resolution.graphScope,
        );
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
        if (mountedRef.current && navigationGenerationRef.current === generationAtStart) {
          setNavigatingRelationshipId(null);
        }
      }
    },
    [
      effectiveProjectionState,
      graphReferenceBinding,
      navigatingRelationshipId,
      resolution.graphScope,
      resolverProjectionState,
      selectedObjectKey,
    ],
  );

  const evidence = graphObject.evidence ?? [];
  const sourceDomains = graphObject.details?.sourceDomains ?? graphObject.sourceDomains ?? [];
  const evidenceCount = graphObject.details?.evidenceCount ?? evidence.length;
  const hasSource = evidenceCount > 0 || sourceDomains.length > 0
    || Boolean(graphObject.details?.sourceAnchorText);
  const objectOccurrences = occurrences.filter(
    (occurrence) => occurrence.graphNodeId === resolution.graphNodeId,
  );
  const isThreat = shouldRenderThreatCampaignSheet(resolution);

  return (
    <article
      className="play-graph-object-sheet"
      aria-label={`${graphObject.label} object sheet`}
      data-testid="play-graph-object-sheet"
      data-node-id={resolution.graphNodeId}
      data-revision-id={resolution.graphScope.revisionId}
    >
      <header data-testid="play-graph-object-sheet-world">
        <h2>{graphObject.label}</h2>
        {graphObject.summary ? <p>{graphObject.summary}</p> : null}
        <p className="module-muted">
          {graphObject.kind ?? "object"}
          {graphObject.role ? ` · ${graphObject.role}` : ""}
          {" · "}
          <code>{resolution.graphNodeId}</code>
          {" @ "}
          <code>{resolution.graphScope.revisionId}</code>
        </p>
      </header>

      {(graphObject.relationships ?? []).length ? (
        <section aria-label="Connected graph objects">
          <h3>Connected objects</h3>
          <ul>
            {(graphObject.relationships ?? []).map((relationship) => (
              <li key={relationship.id}>
                {graphReferenceBinding ? (
                  <button
                    type="button"
                    aria-label={relationshipRowPrimaryCopy(relationship)}
                    disabled={relationshipsDisabled || selectedRelationshipIdMatches(
                      navigatingRelationshipId,
                      relationship.id,
                    )}
                    onClick={() => void onSelectRelationship(relationship)}
                  >
                    {relationshipRowPrimaryCopy(relationship)}
                  </button>
                ) : (
                  <span>{relationshipRowPrimaryCopy(relationship)}</span>
                )}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-label="Source evidence" data-testid="play-graph-object-sheet-source">
        <h3>Source</h3>
        {hasSource ? (
          <>
            <p className="module-muted">
              {evidenceCount} evidence badge{evidenceCount === 1 ? "" : "s"}
              {sourceDomains.length
                ? `; source domains: ${sourceDomains.join(", ")}`
                : "; no source domains"}
              .
            </p>
            {graphObject.details?.sourceAnchorText ? (
              <p>
                <strong>Source phrase:</strong> {graphObject.details.sourceAnchorText}
              </p>
            ) : null}
            {evidence.map((item) => (
              <p key={item.id}>
                {onReadSourceEvidence && item.canOpenSource ? (
                  <button type="button" onClick={() => onReadSourceEvidence(item)}>
                    {item.label ?? item.id}
                  </button>
                ) : (
                  <span>{item.label ?? item.id}</span>
                )}
              </p>
            ))}
          </>
        ) : (
          <p className="module-muted" data-testid="play-graph-object-sheet-source-missing">
            No Source evidence is attached to this object in the pinned graph revision.
          </p>
        )}
      </section>

      <section aria-label="In this Runbook" data-testid="play-graph-object-sheet-runbook">
        <h3>In this Runbook</h3>
        {objectOccurrences.length ? (
          <ul>
            {objectOccurrences.map((occurrence, index) => (
              <li
                key={`${occurrence.graphNodeId}:${occurrence.sourceNodeType}:${occurrence.sceneId ?? ""}:${occurrence.beatId ?? ""}:${occurrence.choiceId ?? ""}:${occurrence.optionId ?? ""}:${index}`}
                data-testid="play-graph-object-occurrence"
                data-beat-id={occurrence.beatId ?? ""}
                data-choice-id={occurrence.choiceId ?? ""}
                data-option-id={occurrence.optionId ?? ""}
                data-source-node-type={occurrence.sourceNodeType}
              >
                {occurrenceContextLabel(occurrence)}
              </li>
            ))}
          </ul>
        ) : (
          <p className="module-muted" data-testid="play-graph-object-sheet-runbook-missing">
            No Runbook occurrence context is available for this object yet.
          </p>
        )}
      </section>

      {isThreat ? <PlayThreatMechanicsSection resolution={resolution} /> : null}
    </article>
  );
}

function selectedRelationshipIdMatches(
  navigatingRelationshipId: string | null,
  relationshipId: string,
): boolean {
  return navigatingRelationshipId === relationshipId;
}
