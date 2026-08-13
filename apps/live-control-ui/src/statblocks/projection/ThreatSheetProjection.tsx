import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";

import { LiveApiError, postThreatQueryHydration, getStatblockWorkbenchDraft, addWorkbenchDraftToCombat } from "../../api/liveApi";
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
import { StatblockAdvancedLedger, StatblockRenderer } from "../render/StatblockRenderer";
import { ThreatCampaignGlance } from "./ThreatCampaignGlance";
import "./threatSheetProjection.css";
import {
  availableBindingCount,
  buildThreatQueryHydrationRequest,
  buildThreatSheetViewModel,
  mapHydrationResultLabelToLoadStatus,
  selectExactThreatHit,
  shouldRenderThreatCampaignSheet,
  threatSelectionTupleFromResolution,
  threatSelectionTupleKey,
  type ThreatSheetBindingViewModel,
  type ThreatSheetViewModel,
} from "./threatSheetViewModel";
import {
  playArtifactIdForThreatNode,
  summaryFromWorkbenchRecord,
  type OfConksPlayDraftSummary,
} from "./ofConksThreatPlayBridge";
import {
  mediaForOfConksNodeId,
  type OfConksNodeMedia,
} from "../../graphReference/ofConksNodeMedia";

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

function navigateToCombatPreservingCampaigns(): void {
  const params = new URLSearchParams(window.location.search);
  const campaigns = params.get("campaigns");
  const target = campaigns
    ? `/combat?campaigns=${encodeURIComponent(campaigns)}`
    : "/combat";
  window.location.assign(target);
}

function ThreatPlayDraftPanel({
  draft,
  media,
}: {
  draft: OfConksPlayDraftSummary;
  media?: OfConksNodeMedia | null;
}) {
  return (
    <section
      className="threat-sheet-projection__play-draft"
      aria-label={`${draft.title} workbench draft`}
      data-testid="threat-sheet-play-draft"
    >
      <h4>{draft.title}</h4>
      {media ? (
        <figure className="threat-sheet-projection__media" data-testid="threat-sheet-media">
          <img src={media.src} alt={media.alt} loading="lazy" />
          {media.caption ? <figcaption>{media.caption}</figcaption> : null}
        </figure>
      ) : null}
      <dl className="threat-sheet-projection__core-stats">
        <div>
          <dt>AC</dt>
          <dd>{draft.armorClass ?? "—"}</dd>
        </div>
        <div>
          <dt>HP</dt>
          <dd>{draft.hitPoints ?? "—"}</dd>
        </div>
        <div>
          <dt>Speed</dt>
          <dd>{draft.speed ?? "—"}</dd>
        </div>
        {draft.challengeRating ? (
          <div>
            <dt>CR</dt>
            <dd>{draft.challengeRating}</dd>
          </div>
        ) : null}
      </dl>
      {draft.tactics.length ? (
        <section aria-label="Suggested tactics">
          <h5>Tactics</h5>
          <ul>
            {draft.tactics.map((tactic) => (
              <li key={tactic}>{tactic}</li>
            ))}
          </ul>
        </section>
      ) : null}
      {draft.primaryActions.length ? (
        <section aria-label="Primary actions">
          <h5>Primary actions</h5>
          <ul>
            {draft.primaryActions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        </section>
      ) : null}
      <pre className="threat-sheet-projection__play-markdown">{draft.markdown}</pre>
    </section>
  );
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

function ThreatSheetAdvancedDetails({
  model,
  availableCount,
  graphObject,
  actions,
  rootRef,
  includeStatblockLedger,
}: {
  model: ThreatSheetViewModel;
  availableCount: number;
  graphObject: GraphObjectCardViewModel;
  actions: readonly GraphObjectActionViewModel[];
  rootRef: RefObject<HTMLElement | null>;
  /** Full Reference: fold validation/provenance into this same disclosure. */
  includeStatblockLedger: boolean;
}) {
  const evidenceCount = graphObject.details?.evidenceCount ?? graphObject.evidence?.length ?? 0;
  const sourceDomains = graphObject.details?.sourceDomains ?? graphObject.sourceDomains ?? [];
  const hasEvidence = evidenceCount > 0 || sourceDomains.length > 0
    || Boolean(graphObject.details?.sourceAnchorText);
  const ledgerBindings = includeStatblockLedger
    ? model.bindings.filter(
        (binding) => binding.hydrationStatus === "available" && binding.revision != null,
      )
    : [];

  return (
    <details className="threat-sheet-projection__inspect">
      <summary>Advanced Details</summary>

      {ledgerBindings.map((binding) => (
        <section
          key={`${binding.relationshipEdgeId}:${binding.bindingId ?? "none"}:ledger`}
          aria-label="Statblock validation and provenance"
        >
          {ledgerBindings.length > 1 ? (
            <h5>
              {binding.role ?? "Binding"}
              {binding.phaseKey ? ` · ${binding.phaseKey}` : ""}
              {binding.variantLabel ? ` · ${binding.variantLabel}` : ""}
            </h5>
          ) : null}
          {binding.revision ? (
            <StatblockAdvancedLedger revision={binding.revision} mode="full" />
          ) : null}
        </section>
      ))}

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
  playDraft,
  playDraftLoadStatus,
  onAddToCombat,
  isAddingToCombat,
  nodeMedia = null,
}: {
  model: ThreatSheetViewModel;
  glanceOnly: boolean;
  graphObject: GraphObjectCardViewModel;
  actions: readonly GraphObjectActionViewModel[];
  rootRef: RefObject<HTMLElement | null>;
  onSelectRelationship?: (relationship: GraphObjectRelationshipViewModel) => void;
  selectedRelationshipId?: string | null;
  relationshipsDisabled?: boolean;
  playDraft: OfConksPlayDraftSummary | null;
  playDraftLoadStatus: "idle" | "loading" | "ready" | "error";
  onAddToCombat?: () => void;
  isAddingToCombat?: boolean;
  nodeMedia?: OfConksNodeMedia | null;
}) {
  const availableCount = availableBindingCount(model.bindings);
  const compactBinding =
    availableCount === 1
      ? model.bindings.find((binding) => binding.hydrationStatus === "available") ?? null
      : null;
  const showPlayDraft = playDraftLoadStatus === "ready" && playDraft != null;
  const showLoadError =
    model.loadStatus !== "loading"
    && model.loadStatus !== "ready"
    && !showPlayDraft;

  return (
    <div
      className={`threat-sheet-projection${glanceOnly ? " threat-sheet-projection--glance" : " threat-sheet-projection--full"}`}
      data-testid="threat-sheet-projection"
      data-glance={glanceOnly ? "true" : "false"}
    >
      {!glanceOnly && showPlayDraft && onAddToCombat ? (
        <button
          type="button"
          className="threat-sheet-projection__add-to-combat"
          data-testid="threat-sheet-add-to-combat"
          disabled={isAddingToCombat}
          onClick={onAddToCombat}
        >
          {isAddingToCombat ? "Adding to combat…" : "Add to combat"}
        </button>
      ) : null}

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
          {model.loadStatus === "loading" ? (
            <p className="threat-sheet-projection__status threat-sheet-projection__status--loading" role="status">
              Loading exact mechanics…
            </p>
          ) : null}

          {model.loadStatus !== "loading" && showLoadError ? (
            <p
              className="threat-sheet-projection__status threat-sheet-projection__status--error"
              role="status"
              data-testid="threat-sheet-load-status"
              data-load-status={model.loadStatus}
            >
              {model.message ?? `Exact mechanics ${model.loadStatus.replace(/_/g, " ")}.`}
            </p>
          ) : null}

          {playDraftLoadStatus === "loading" ? (
            <p className="threat-sheet-projection__status threat-sheet-projection__status--loading" role="status">
              Loading workbench draft…
            </p>
          ) : null}

          {showPlayDraft && playDraft ? (
            <ThreatPlayDraftPanel draft={playDraft} media={nodeMedia} />
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

      {model.loadStatus !== "loading" && showLoadError && glanceOnly ? (
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

      <ThreatSheetAdvancedDetails
        model={model}
        availableCount={availableCount}
        graphObject={graphObject}
        actions={actions}
        rootRef={rootRef}
        includeStatblockLedger={!glanceOnly}
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

  const [playDraft, setPlayDraft] = useState<OfConksPlayDraftSummary | null>(null);
  const [playDraftLoadStatus, setPlayDraftLoadStatus] = useState<
    "idle" | "loading" | "ready" | "error"
  >("idle");
  const [isAddingToCombat, setIsAddingToCombat] = useState(false);

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

  const playArtifactId = useMemo(
    () => (selectionTuple ? playArtifactIdForThreatNode(selectionTuple.threatNodeId) : null),
    [selectionTuple],
  );

  const hasAvailableBinding = useMemo(
    () => model.bindings.some((binding) => binding.hydrationStatus === "available"),
    [model.bindings],
  );

  const shouldFetchPlayDraft =
    Boolean(playArtifactId) && loadStatus !== "loading" && !hasAvailableBinding;

  useEffect(() => {
    if (!shouldFetchPlayDraft || !playArtifactId) {
      setPlayDraft(null);
      setPlayDraftLoadStatus("idle");
      return;
    }

    let cancelled = false;
    setPlayDraftLoadStatus("loading");
    setPlayDraft(null);

    void getStatblockWorkbenchDraft(playArtifactId)
      .then((response) => {
        if (cancelled) return;
        setPlayDraft(summaryFromWorkbenchRecord(response.record));
        setPlayDraftLoadStatus("ready");
      })
      .catch(() => {
        if (cancelled) return;
        setPlayDraft(null);
        setPlayDraftLoadStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [playArtifactId, shouldFetchPlayDraft]);

  const handleAddToCombat = useCallback(async () => {
    if (!playDraft || isAddingToCombat) return;
    setIsAddingToCombat(true);
    try {
      await addWorkbenchDraftToCombat(playDraft.artifactId, { team: "enemy", count: 1 });
      navigateToCombatPreservingCampaigns();
    } finally {
      setIsAddingToCombat(false);
    }
  }, [isAddingToCombat, playDraft]);

  const cardModel = useMemo(() => {
    const baseActions = buildPlanGraphObjectActions({
      resolution,
      sessionDescriptor,
      onOpenStatblock,
    });
    const actions = [...baseActions];
    if (playDraft) {
      actions.push({
        id: "add-to-combat",
        label: "Add to combat",
        kind: "add-to-combat",
        disabled: isAddingToCombat,
        onClick: () => {
          void handleAddToCombat();
        },
      });
    }
    return {
      ...resolution.graphObject,
      actions,
    };
  }, [
    handleAddToCombat,
    isAddingToCombat,
    onOpenStatblock,
    playDraft,
    resolution,
    sessionDescriptor,
  ]);

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

  const usePlaySheetChrome = Boolean(playDraft) || shouldFetchPlayDraft;

  return (
    <article
      ref={articleRef}
      className={
        glanceOnly
          ? "plan-reference-object-card plan-reference-object-card--threat-sheet"
          : usePlaySheetChrome
            ? "plan-reference-object-card plan-reference-object-card--threat-sheet plan-reference-object-card--threat-sheet-play"
            : "plan-reference-object-card plan-reference-object-card--threat-sheet plan-reference-object-card--threat-sheet-full"
      }
      aria-label={`${model.label} threat sheet`}
      data-testid="plan-reference-threat-sheet"
      data-threat-sheet-chrome={glanceOnly ? "glance" : usePlaySheetChrome ? "play" : "full"}
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
        playDraft={playDraft}
        playDraftLoadStatus={playDraftLoadStatus}
        onAddToCombat={playDraft ? () => { void handleAddToCombat(); } : undefined}
        isAddingToCombat={isAddingToCombat}
        nodeMedia={mediaForOfConksNodeId(resolution.graphNodeId)}
      />
    </article>
  );
}

export function shouldRenderThreatSheetProjection(resolution: GraphReferenceResolution): boolean {
  return shouldRenderThreatCampaignSheet(resolution);
}
