import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";

import { LiveApiError, postThreatQueryHydration } from "../../api/liveApi";
import type { ThreatQueryHydrationHitV1, ThreatQueryHydrationResponseV1 } from "../../api/types";
import type {
  GraphObjectActionViewModel,
  GraphObjectCardViewModel,
  GraphObjectRelationshipViewModel,
} from "../../graphObjectCard";
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
import { ThreatCampaignGlance } from "./ThreatCampaignGlance";
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

function resolveThreatActionHandler(
  action: GraphObjectActionViewModel,
  rootRef: RefObject<HTMLElement | null>,
): (() => void) | undefined {
  if (action.onClick) return action.onClick;
  if (action.kind === "open-source") {
    return () => {
      const details = rootRef.current?.querySelector(".threat-sheet-projection__inspect");
      if (!(details instanceof HTMLDetailsElement)) return;
      details.open = true;
      if (typeof details.scrollIntoView === "function") {
        details.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    };
  }
  return undefined;
}

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
    <section
      className="threat-sheet-projection__relationships"
      aria-label="Connected graph objects"
    >
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

function ThreatSheetInspectDetails({
  model,
  availableCount,
  graphObject,
  actions,
  rootRef,
}: {
  model: ThreatSheetViewModel;
  availableCount: number;
  graphObject: GraphObjectCardViewModel;
  actions: readonly GraphObjectActionViewModel[];
  rootRef: RefObject<HTMLElement | null>;
}) {
  const evidenceCount = graphObject.details?.evidenceCount ?? graphObject.evidence?.length ?? 0;
  const sourceDomains = graphObject.details?.sourceDomains ?? graphObject.sourceDomains ?? [];
  const hasEvidence = evidenceCount > 0 || sourceDomains.length > 0
    || Boolean(graphObject.details?.sourceAnchorText);

  return (
    <details className="threat-sheet-projection__inspect">
      <summary>Inspect proof and tools</summary>

      <p
        className="threat-sheet-projection__binding-summary"
        data-testid="threat-sheet-binding-summary"
      >
        Mechanics bindings: {model.bindings.length} total · {availableCount} available · disposition{" "}
        {model.mechanicsDisposition}
      </p>

      {hasEvidence ? (
        <section aria-label="Evidence and source">
          <h5>Evidence and source</h5>
          <p className="threat-sheet-projection__muted">
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
        </section>
      ) : null}

      {model.scope ? (
        <section aria-label="Exact scope and identifiers">
          <h5>Exact scope and identifiers</h5>
          <dl className="threat-sheet-projection__id-grid">
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
        </section>
      ) : null}

      {actions.length ? (
        <div className="threat-sheet-projection__actions">
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
                onClick={resolveThreatActionHandler(action, rootRef)}
              >
                {action.label}
              </button>
            ),
          )}
        </div>
      ) : null}
    </details>
  );
}

function ThreatSheetBody({
  model,
  glanceOnly,
  graphObject,
  actions,
  rootRef,
  onSelectRelationship,
  selectedRelationshipId,
  relationshipsDisabled,
}: {
  model: ThreatSheetViewModel;
  glanceOnly: boolean;
  graphObject: GraphObjectCardViewModel;
  actions: readonly GraphObjectActionViewModel[];
  rootRef: RefObject<HTMLElement | null>;
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
    <div
      className={`threat-sheet-projection${glanceOnly ? " threat-sheet-projection--glance" : " threat-sheet-projection--full"}`}
      data-testid="threat-sheet-projection"
      data-glance={glanceOnly ? "true" : "false"}
    >
      {glanceOnly ? (
        <ThreatCampaignGlance
          label={model.label}
          threatKind={model.threatKind}
          intendedRole={model.intendedRole}
          summary={model.summary}
          loadStatus={model.loadStatus}
          compactBinding={compactBinding}
          availableCount={availableCount}
          bindingCount={model.bindings.length}
          variant="sheet"
        />
      ) : (
        <>
          <header className="threat-sheet-projection__header threat-sheet-projection__header--full">
            <p className="threat-sheet-projection__kicker">Threat · full statblock</p>
            {model.summary ? (
              <p className="threat-sheet-projection__summary">{model.summary}</p>
            ) : null}
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

          <div className="threat-sheet-projection__bindings">
            {model.bindings.map((binding) =>
              binding.hydrationStatus === "available" && binding.revision ? (
                <section
                  key={`${binding.relationshipEdgeId}:${binding.bindingId ?? "none"}`}
                  className="threat-sheet-projection__full-statblock"
                >
                  {model.bindings.length > 1 ? (
                    <h4>
                      {binding.role ?? "Binding"}
                      {binding.phaseKey ? ` · ${binding.phaseKey}` : ""}
                      {binding.variantLabel ? ` · ${binding.variantLabel}` : ""}
                    </h4>
                  ) : null}
                  <StatblockRenderer revision={binding.revision} mode="full" chrome="campaign" />
                </section>
              ) : (
                <BindingStatusPanel
                  key={`${binding.relationshipEdgeId}:${binding.bindingId ?? "none"}`}
                  binding={binding}
                />
              ),
            )}
          </div>
        </>
      )}

      {model.loadStatus !== "loading" && model.loadStatus !== "ready" && glanceOnly ? (
        <p
          className="threat-sheet-projection__status threat-sheet-projection__status--error"
          role="status"
          data-testid="threat-sheet-load-status"
          data-load-status={model.loadStatus}
        >
          {model.message ?? `Exact mechanics ${model.loadStatus.replace(/_/g, " ")}.`}
        </p>
      ) : null}

      <ThreatRelationshipsSection
        model={model}
        glanceOnly={glanceOnly}
        onSelectRelationship={onSelectRelationship}
        selectedRelationshipId={selectedRelationshipId}
        disabled={relationshipsDisabled}
      />

      <ThreatSheetInspectDetails
        model={model}
        availableCount={availableCount}
        graphObject={graphObject}
        actions={actions}
        rootRef={rootRef}
      />
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
  const articleRef = useRef<HTMLElement | null>(null);
  const [navigatingRelationshipId, setNavigatingRelationshipId] = useState<string | null>(null);
  const graphReferenceBindingRef = useRef(graphReferenceBinding);
  graphReferenceBindingRef.current = graphReferenceBinding;

  const selectionTuple = useMemo(() => threatSelectionTupleFromResolution(resolution), [resolution]);
  const selectionKey = selectionTuple ? threatSelectionTupleKey(selectionTuple) : null;
  const selectedObjectKey = selectionKey ?? `${resolution.kind}\0${resolution.locator}`;

  const [selectedHit, setSelectedHit] = useState<ThreatQueryHydrationHitV1 | null>(null);
  const [loadStatus, setLoadStatus] = useState<ThreatSheetViewModel["loadStatus"]>("loading");
  const [loadMessage, setLoadMessage] = useState<string | null>(null);
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
        scopeMode: selectionTuple.scopeMode,
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
      graphReferenceBinding,
      navigatingRelationshipId,
      resolverProjectionState,
      resolution,
      selectedObjectKey,
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
        ref={articleRef}
        className="plan-reference-object-card plan-reference-object-card--threat-sheet"
        aria-label={`${resolution.graphObject.label} threat sheet`}
        data-testid="plan-reference-threat-sheet"
      >
        <div className="threat-sheet-projection threat-sheet-projection--glance">
          <header className="threat-sheet-projection__header">
            <h3 className="threat-sheet-projection__title">{resolution.graphObject.label}</h3>
            {resolution.graphObject.summary ? (
              <p className="threat-sheet-projection__summary">{resolution.graphObject.summary}</p>
            ) : null}
          </header>
          <p
            className="threat-sheet-projection__status threat-sheet-projection__status--error"
            role="status"
            data-testid="threat-sheet-load-status"
            data-load-status="integrity_failure"
          >
            Exact graph scope is required for Threat Sheet projection.
          </p>
        </div>
      </article>
    );
  }

  return (
    <article
      ref={articleRef}
      className="plan-reference-object-card plan-reference-object-card--threat-sheet"
      aria-label={`${model.label} threat sheet`}
      data-testid="plan-reference-threat-sheet"
    >
      <ThreatSheetBody
        model={model}
        glanceOnly={glanceOnly}
        graphObject={cardModel}
        actions={cardModel.actions ?? []}
        rootRef={articleRef}
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
