import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { LiveApiError, postThreatQueryHydration } from "../../api/liveApi";
import type { ThreatQueryHydrationHitV1, ThreatQueryHydrationResponseV1 } from "../../api/types";
import { GraphObjectCard } from "../../graphObjectCard";
import type { GraphObjectRelationshipViewModel } from "../../graphObjectCard";
import {
  relationshipRowPrimaryCopy,
  selectDefaultRelationshipRows,
} from "../../graphObjectCard/graphObjectDisplay";
import type {
  GraphReferenceProjectionBinding,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
} from "../../graphReference/types";
import { buildPlanGraphObjectActions } from "../../planSurface/reference/buildPlanGraphObjectActions";
import type { PlanSessionDescriptor } from "../../planSurface/types";
import { StatblockRenderer } from "../render/StatblockRenderer";
import { buildStatblockViewModel } from "../render/statblockViewModel";
import "./threatSheetProjection.css";
import {
  availableBindingCount,
  buildThreatQueryHydrationRequest,
  buildThreatSheetViewModel,
  isExactResolvedThreat,
  mapHydrationResultLabelToLoadStatus,
  selectExactThreatHit,
  threatSelectionTupleFromResolution,
  threatSelectionTupleKey,
  type ThreatSheetBindingViewModel,
  type ThreatSheetViewModel,
} from "./threatSheetViewModel";

export interface ThreatSheetProjectionProps {
  resolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }>;
  sessionDescriptor?: PlanSessionDescriptor;
  projectionState?: GraphReferenceProjectionState | null;
  graphReferenceBinding?: GraphReferenceProjectionBinding | null;
  glanceOnly?: boolean;
}

function BindingStatusPanel({ binding }: { binding: ThreatSheetBindingViewModel }) {
  return (
    <section
      className="threat-sheet-projection__binding-panel"
      aria-label={`Binding status ${binding.bindingId ?? binding.relationshipEdgeId}`}
      data-testid="threat-sheet-binding-status"
      data-hydration-status={binding.hydrationStatus}
    >
      <h4>
        {binding.role ?? "Binding"}
        {binding.phaseKey ? ` · ${binding.phaseKey}` : ""}
        {binding.variantLabel ? ` · ${binding.variantLabel}` : ""}
      </h4>
      <p className="threat-sheet-projection__binding-locator">
        Status: <strong>{binding.hydrationStatus}</strong>
        {binding.statblockId ? (
          <>
            {" "}
            · statblock <code>{binding.statblockId}</code>
          </>
        ) : null}
        {binding.revisionId ? (
          <>
            {" "}
            · revision <code>{binding.revisionId}</code>
          </>
        ) : null}
        {binding.definitionDigest ? (
          <>
            {" "}
            · digest <code>{binding.definitionDigest}</code>
          </>
        ) : null}
      </p>
      {binding.message ? <p className="module-muted">{binding.message}</p> : null}
    </section>
  );
}

function CompactCoreStats({ binding }: { binding: ThreatSheetBindingViewModel }) {
  if (!binding.revision) return null;
  const view = buildStatblockViewModel(binding.revision, "summary");
  return (
    <dl className="threat-sheet-projection__core-stats" aria-label="Compact mechanics summary">
      <div>
        <dt>Armor Class</dt>
        <dd>{view.armorClassSummary}</dd>
      </div>
      <div>
        <dt>Hit Points</dt>
        <dd>{view.hitPointsSummary}</dd>
      </div>
      <div>
        <dt>Speed</dt>
        <dd>{view.speedSummary}</dd>
      </div>
      <div>
        <dt>Challenge</dt>
        <dd>{view.challengeSummary}</dd>
      </div>
    </dl>
  );
}

function ThreatRelationshipsSection({
  model,
  glanceOnly,
  onSelectRelationship,
  selectedRelationshipId,
  disabled,
}: {
  model: ThreatSheetViewModel;
  glanceOnly: boolean;
  onSelectRelationship?: (relationship: GraphObjectRelationshipViewModel) => void;
  selectedRelationshipId?: string | null;
  disabled?: boolean;
}) {
  const { rows, omittedCount } = selectDefaultRelationshipRows(
    [...model.relationships],
    glanceOnly ? 4 : model.relationships.length,
  );

  if (!rows.length) return null;

  return (
    <section aria-label="Connected graph objects">
      <h4>Connected objects</h4>
      <ul className="graph-object-card__relationship-list">
        {rows.map((relationship) => (
          <li key={relationship.id}>
            {onSelectRelationship ? (
              <button
                type="button"
                className="graph-object-card__relationship-button"
                aria-label={relationshipRowPrimaryCopy(relationship)}
                disabled={disabled || selectedRelationshipId === relationship.id}
                onClick={() => onSelectRelationship(relationship)}
              >
                {relationshipRowPrimaryCopy(relationship)}
              </button>
            ) : (
              <span>{relationshipRowPrimaryCopy(relationship)}</span>
            )}
          </li>
        ))}
      </ul>
      {omittedCount > 0 ? (
        <p className="module-muted" data-testid="threat-sheet-relationship-omitted">
          +{omittedCount} more relationship{omittedCount === 1 ? "" : "s"}
        </p>
      ) : null}
    </section>
  );
}

function ThreatSheetBody({
  model,
  glanceOnly,
  onSelectRelationship,
  selectedRelationshipId,
  relationshipsDisabled,
}: {
  model: ThreatSheetViewModel;
  glanceOnly: boolean;
  onSelectRelationship?: (relationship: GraphObjectRelationshipViewModel) => void;
  selectedRelationshipId?: string | null;
  relationshipsDisabled?: boolean;
}) {
  const availableCount = availableBindingCount(model.bindings);
  const compactBinding =
    availableCount === 1
      ? model.bindings.find((binding) => binding.hydrationStatus === "available") ?? null
      : null;

  return (
    <div className="threat-sheet-projection" data-testid="threat-sheet-projection">
      <header className="threat-sheet-projection__header">
        <p className="plan-surface-kicker">Threat sheet</p>
        <h3>{model.label}</h3>
        <p className="threat-sheet-projection__meta">
          {model.threatKind ?? "threat"}
          {model.intendedRole ? ` · ${model.intendedRole}` : ""}
        </p>
        {model.summary ? <p>{model.summary}</p> : null}
      </header>

      {model.loadStatus === "loading" ? (
        <p className="threat-sheet-projection__status threat-sheet-projection__status--loading" role="status">
          Loading exact mechanics…
        </p>
      ) : null}

      {model.loadStatus !== "loading" && model.loadStatus !== "ready" ? (
        <p
          className="threat-sheet-projection__status threat-sheet-projection__status--error"
          role="status"
          data-testid="threat-sheet-load-status"
          data-load-status={model.loadStatus}
        >
          {model.message ?? `Exact mechanics ${model.loadStatus.replace(/_/g, " ")}.`}
        </p>
      ) : null}

      <p className="threat-sheet-projection__binding-summary" data-testid="threat-sheet-binding-summary">
        Mechanics bindings: {model.bindings.length} total · {availableCount} available · disposition{" "}
        {model.mechanicsDisposition}
      </p>

      {glanceOnly && compactBinding ? <CompactCoreStats binding={compactBinding} /> : null}

      {glanceOnly && !compactBinding ? (
        <p className="module-muted">
          {availableCount === 0
            ? "No trusted mechanics binding for compact display."
            : `${availableCount} available bindings — expand to view each separately.`}
        </p>
      ) : null}

      {!glanceOnly ? (
        <div className="threat-sheet-projection__bindings">
          {model.bindings.map((binding) =>
            binding.hydrationStatus === "available" && binding.revision ? (
              <section key={`${binding.relationshipEdgeId}:${binding.bindingId ?? "none"}`}>
                <h4>
                  {binding.role ?? "Binding"}
                  {binding.phaseKey ? ` · ${binding.phaseKey}` : ""}
                  {binding.variantLabel ? ` · ${binding.variantLabel}` : ""}
                </h4>
                <StatblockRenderer revision={binding.revision} mode="full" />
              </section>
            ) : (
              <BindingStatusPanel
                key={`${binding.relationshipEdgeId}:${binding.bindingId ?? "none"}`}
                binding={binding}
              />
            ),
          )}
        </div>
      ) : null}

      <ThreatRelationshipsSection
        model={model}
        glanceOnly={glanceOnly}
        onSelectRelationship={onSelectRelationship}
        selectedRelationshipId={selectedRelationshipId}
        disabled={relationshipsDisabled}
      />

      {model.scope ? (
        <details className="threat-sheet-projection__technical-details">
          <summary>Exact scope and identifiers</summary>
          <dl>
            <div>
              <dt>World</dt>
              <dd>
                <code>{model.scope.worldId}</code>
              </dd>
            </div>
            <div>
              <dt>Campaign</dt>
              <dd>
                <code>{model.scope.campaignId}</code>
              </dd>
            </div>
            <div>
              <dt>Graph revision</dt>
              <dd>
                <code>{model.scope.revisionId}</code>
              </dd>
            </div>
            <div>
              <dt>Threat node</dt>
              <dd>
                <code>{model.threatNodeId}</code>
              </dd>
            </div>
          </dl>
        </details>
      ) : null}
    </div>
  );
}

export function ThreatSheetProjection({
  resolution,
  sessionDescriptor,
  projectionState,
  graphReferenceBinding = null,
  glanceOnly = false,
}: ThreatSheetProjectionProps) {
  const [navigatingRelationshipId, setNavigatingRelationshipId] = useState<string | null>(null);
  const graphReferenceBindingRef = useRef(graphReferenceBinding);
  graphReferenceBindingRef.current = graphReferenceBinding;

  const selectionTuple = useMemo(() => threatSelectionTupleFromResolution(resolution), [resolution]);
  const selectionKey = selectionTuple ? threatSelectionTupleKey(selectionTuple) : null;

  const [selectedHit, setSelectedHit] = useState<ThreatQueryHydrationHitV1 | null>(null);
  const [loadStatus, setLoadStatus] = useState<ThreatSheetViewModel["loadStatus"]>("loading");
  const [loadMessage, setLoadMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!selectionTuple || !selectionKey) {
      setLoadStatus("integrity_failure");
      setLoadMessage("Exact graph scope is required for Threat Sheet projection.");
      setSelectedHit(null);
      return;
    }

    let cancelled = false;
    setLoadStatus("loading");
    setLoadMessage(null);
    setSelectedHit(null);

    const request = buildThreatQueryHydrationRequest(
      {
        worldId: selectionTuple.worldId,
        campaignId: selectionTuple.campaignId,
        revisionId: selectionTuple.revisionId,
      },
      selectionTuple.threatNodeId,
    );

    void postThreatQueryHydration(request)
      .then((response: ThreatQueryHydrationResponseV1) => {
        if (cancelled) return;
        const selection = selectExactThreatHit(
          response,
          selectionTuple,
          selectionTuple.threatNodeId,
        );
        setLoadStatus(mapHydrationResultLabelToLoadStatus(response.resultLabel, selection));
        if (selection.status === "ready") {
          setSelectedHit(selection.hit);
          setLoadMessage(response.message);
          return;
        }
        setSelectedHit(null);
        if (selection.status === "not_found") {
          setLoadMessage(selection.message ?? "Exact Threat mechanics not found.");
          return;
        }
        setLoadMessage(selection.message);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setSelectedHit(null);
        if (error instanceof LiveApiError) {
          if (error.status === 404) {
            setLoadStatus("not_found");
            setLoadMessage(error.message);
            return;
          }
          if (error.status === 503) {
            setLoadStatus("unavailable");
            setLoadMessage(error.message);
            return;
          }
          if (error.status >= 500) {
            setLoadStatus("integrity_failure");
            setLoadMessage(error.message);
            return;
          }
        }
        setLoadStatus("unavailable");
        setLoadMessage(error instanceof Error ? error.message : "Threat mechanics unavailable.");
      });

    return () => {
      cancelled = true;
    };
  }, [selectionKey, selectionTuple]);

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

  const cardModel = useMemo(
    () => ({
      ...resolution.graphObject,
      actions: buildPlanGraphObjectActions({
        resolution,
        sessionDescriptor,
        onOpenStatblock,
      }),
    }),
    [onOpenStatblock, resolution, sessionDescriptor],
  );

  const onSelectRelationship = useCallback(
    async (relationship: GraphObjectRelationshipViewModel) => {
      const bindingAtStart = graphReferenceBinding;
      if (!bindingAtStart || navigatingRelationshipId) return;
      if (resolverProjectionState === "loading" || resolverProjectionState === "error") return;

      setNavigatingRelationshipId(relationship.id);
      try {
        const nextResolution = await bindingAtStart.resolveRelationship(relationship);
        const current = graphReferenceBindingRef.current;
        if (!current || current !== bindingAtStart) return;
        current.openResolvedReference(
          nextResolution,
          nextResolution.projectionState ?? effectiveProjectionState,
        );
      } finally {
        setNavigatingRelationshipId(null);
      }
    },
    [
      effectiveProjectionState,
      graphReferenceBinding,
      navigatingRelationshipId,
      resolverProjectionState,
    ],
  );

  const relationshipsDisabled =
    Boolean(navigatingRelationshipId)
    || resolverProjectionState === "loading"
    || resolverProjectionState === "error";

  const model = useMemo(
    () =>
      buildThreatSheetViewModel({
        resolution,
        hit: selectedHit,
        loadStatus,
        message: loadMessage,
      }),
    [loadMessage, loadStatus, resolution, selectedHit],
  );

  if (!selectionTuple) {
    return (
      <article
        className="plan-reference-object-card plan-reference-object-card--threat-sheet"
        aria-label={`${resolution.graphObject.label} threat sheet`}
        data-testid="plan-reference-threat-sheet"
      >
        <header className="threat-sheet-projection__header">
          <p className="plan-surface-kicker">Threat sheet</p>
          <h3>{resolution.graphObject.label}</h3>
          {resolution.graphObject.summary ? <p>{resolution.graphObject.summary}</p> : null}
        </header>
        <p
          className="threat-sheet-projection__status threat-sheet-projection__status--error"
          role="status"
          data-testid="threat-sheet-load-status"
          data-load-status="integrity_failure"
        >
          Exact graph scope is required for Threat Sheet projection.
        </p>
      </article>
    );
  }

  return (
    <article
      className="plan-reference-object-card plan-reference-object-card--threat-sheet"
      aria-label={`${model.label} threat sheet`}
      data-testid="plan-reference-threat-sheet"
    >
      <GraphObjectCard
        mode="plan"
        model={cardModel}
        aria-label={`${model.label} threat actions`}
        showRelationshipProvenance={false}
        relationshipsSlot={<></>}
        actionsSlot={<></>}
      />
      <ThreatSheetBody
        model={model}
        glanceOnly={glanceOnly}
        onSelectRelationship={graphReferenceBinding ? onSelectRelationship : undefined}
        selectedRelationshipId={navigatingRelationshipId}
        relationshipsDisabled={relationshipsDisabled}
      />
    </article>
  );
}

export function shouldRenderThreatSheetProjection(resolution: GraphReferenceResolution): boolean {
  return isExactResolvedThreat(resolution);
}
