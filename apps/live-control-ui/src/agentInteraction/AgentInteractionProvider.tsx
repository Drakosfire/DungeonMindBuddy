import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import type { AgentInteractionThread, LiveQueryBackend } from "../api/types";
import type {
  GraphReferenceProjectionBinding,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
} from "../graphReference/types";
import type {
  GraphReviewDiagnosticsProjectionPayload,
  RegisterableToolProjectionId,
  ToolProjectionPayloadMap,
} from "../planSurface/projection/projectionBindings";
import { GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID } from "../planSurface/projection/projectionBindings";
import type { ActiveProjection, ProjectionSize } from "../surfaceInteraction/projection/types";
import {
  GRAPH_REFERENCE_PROJECTION_ID,
  normalizeProjectionCatalogRegistration,
  resolveProjectionCatalog as resolveProjectionCatalogPure,
  type ProjectionCatalogLiveEntry,
  type ProjectionCatalogRegistration,
} from "../surfaceInteraction/projection/projectionCatalog";
import {
  AGENT_TURN_HISTORY_CAP,
  clearAgentThread,
  createAgentInteractionThread,
  deleteAgentThread as deleteStoredAgentThread,
  listAgentThreads,
  loadAgentThread,
  loadAgentThreadById,
  persistAgentThread,
  renameAgentThread,
  setActiveAgentThread,
  threadTitleFromQuestion,
  turnFromResponse,
} from "./agentInteractionStorage";
import type {
  AgentInteractionContextValue,
  AgentInteractionPaneState,
  AgentInteractionScope,
  AgentInteractionSelectedSource,
  AgentInteractionSurfaceContext,
} from "./agentInteractionTypes";
import type { OpenGraphReferenceArgs } from "../graphReference/types";
import {
  adaptProjectionSurfaceToNeutralBase,
} from "./surfaceInteractionCompat";
import {
  bindSurfaceInteractionLease,
  createLeaseCallbackGate,
  registerChromeCompatibilityFragment,
  unregisterChromeCompatibilityFragment,
  updateSurfaceInteractionLease,
  type SurfaceInteractionChromeFragment,
  type SurfaceInteractionLeaseSnapshot,
} from "./surfaceInteractionLease";
import {
  sameProjectionSurfaceIdentity,
  validateProjectionSurfacePublication,
  type ProjectionSurfacePublication,
  type ValidatedProjectionSurface,
} from "./projectionSurfacePublication";
import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";

const AgentInteractionContext = createContext<AgentInteractionContextValue | null>(null);

function sameScope(left: AgentInteractionScope | null, right: AgentInteractionScope): boolean {
  return Boolean(
    left &&
      left.campaignId === right.campaignId &&
      left.sessionNumber === right.sessionNumber &&
      (left.surfaceId ?? "plan") === (right.surfaceId ?? "plan") &&
      (left.documentId ?? null) === (right.documentId ?? null) &&
      (left.surfaceInstanceId ?? null) === (right.surfaceInstanceId ?? null),
  );
}

interface LegacyProjectionAttachment {
  validated: ValidatedProjectionSurface | null;
}

interface ProviderLeaseBundle {
  snapshot: SurfaceInteractionLeaseSnapshot;
  legacyProjection: LegacyProjectionAttachment | null;
  authorizationEpoch: number;
  appChromePublisherEpoch: number;
}

interface BindingRegistration<T> {
  surfaceToken: symbol;
  token: symbol;
  value: T;
}

interface LeasedActiveProjection {
  surfaceToken: symbol;
  projection: ActiveProjection;
  /**
   * Tool contribution id that launched this projection (tool kind only).
   * Distinct from `projection.key`, which is the Projection descriptor id.
   */
  launchingToolId?: string;
}

interface LeasedGraphReference {
  surfaceToken: symbol;
  resolution: GraphReferenceResolution;
}

interface LeasedGraphProjectionState {
  surfaceToken: symbol;
  state: GraphReferenceProjectionState | null;
}

interface CatalogRegistrationAttachment {
  surfaceToken: symbol;
  registrationToken: symbol;
  registration: ProjectionCatalogRegistration;
}

interface ProjectionToolActivatorAttachment {
  leaseToken: symbol;
  fn: (toolId: string) => boolean | void | Promise<boolean | void>;
}

function isThenable<T>(value: T | PromiseLike<T>): value is PromiseLike<T> {
  return typeof value === "object" && value !== null && "then" in value;
}

function contentSize(resolution: GraphReferenceResolution): ProjectionSize {
  if (resolution.kind === "resolved_graph" || resolution.kind === "resolved_corpus_fallback") return "wide";
  return "compact";
}

/**
 * Revalidate an open tool Projection against the *neutral* effective publication.
 * Active key is the Projection descriptor id; launchingToolId (when present) must
 * still authorize that descriptor via activation.projectionId.
 */
function revalidateLeasedToolProjection(
  publication: SurfaceInteractionPublication,
  leased: LeasedActiveProjection,
): LeasedActiveProjection | null {
  const projectionId = leased.projection.key;
  const launchingToolId = leased.launchingToolId;

  const tool = launchingToolId
    ? publication.tools.find((entry) => entry.id === launchingToolId)
    : publication.tools.find(
        (entry) =>
          entry.activation.kind === "projection"
          && entry.activation.projectionId === projectionId,
      );

  if (!tool || tool.availability.status !== "enabled") return null;
  if (tool.activation.kind !== "projection" || tool.activation.projectionId !== projectionId) {
    return null;
  }

  const descriptor = publication.projections.find(
    (entry) => entry.id === projectionId && entry.kind === "tool",
  );
  if (!descriptor) return null;

  return {
    surfaceToken: leased.surfaceToken,
    launchingToolId: tool.id,
    projection: {
      kind: "tool",
      key: projectionId,
      size: descriptor.preferredSize,
      title: tool.label,
    },
  };
}

function revalidateLeasedProjection(
  validated: ValidatedProjectionSurface,
  leased: LeasedActiveProjection | null,
  publication: SurfaceInteractionPublication | null,
): LeasedActiveProjection | null {
  if (!leased) return null;
  // Canonical disabled state clears every active projection, including tools
  // whose IDs still appear in a contradictory or otherwise invalid config.
  if (!validated.projectionsEnabled) return null;
  if (leased.projection.kind === "tool") {
    if (!publication) return null;
    return revalidateLeasedToolProjection(publication, leased);
  }
  return leased;
}

/**
 * Declaration gate: effective publication exposes exactly one graph-reference
 * content descriptor. Any surface (Plan, Build, …) may qualify via publication
 * shape — never via surfaceId alone.
 */
function publicationDeclaresGraphReferenceCapability(
  publication: SurfaceInteractionPublication | null | undefined,
): boolean {
  if (!publication) return false;
  let matches = 0;
  for (const entry of publication.projections) {
    if (entry.id === GRAPH_REFERENCE_PROJECTION_ID && entry.kind === "content") {
      matches += 1;
    }
  }
  return matches === 1;
}

/**
 * Lease-aware declaration: legacy Plan loses graph-reference authority when
 * projectionsEnabled is false (context loss), even if the neutral adapter still
 * emits the content descriptor.
 */
function leaseDeclaresGraphReferenceCapability(bundle: ProviderLeaseBundle | null): boolean {
  if (!bundle?.snapshot.effectivePublication) return false;
  const legacy = bundle.legacyProjection?.validated;
  if (
    legacy
    && legacy.publication.identity.surfaceId === "plan"
    && !legacy.projectionsEnabled
  ) {
    return false;
  }
  return publicationDeclaresGraphReferenceCapability(bundle.snapshot.effectivePublication);
}

function graphReferenceBindingRegisteredOnLease(
  registration: BindingRegistration<GraphReferenceProjectionBinding> | null,
  surfaceToken: symbol | null,
): boolean {
  return Boolean(registration && surfaceToken && registration.surfaceToken === surfaceToken);
}

/** Operational gate: declaration plus a live binding on the current lease. */
function canOperateGraphReferenceCapability(
  bundle: ProviderLeaseBundle | null,
  registration: BindingRegistration<GraphReferenceProjectionBinding> | null,
): boolean {
  if (!leaseDeclaresGraphReferenceCapability(bundle)) {
    return false;
  }
  return graphReferenceBindingRegisteredOnLease(registration, bundle!.snapshot.token);
}

function isAuthorizedDiagnosticsPublication(bundle: ProviderLeaseBundle | null): boolean {
  if (!bundle?.snapshot.effectivePublication) return false;
  const validated = bundle?.legacyProjection?.validated;
  if (!validated?.projectionsEnabled) return false;
  const { identity, config } = validated.publication;
  if (identity.surfaceId !== "ingest" || config.id !== "ingest") return false;
  return config.tools.some((entry) => entry.id === GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID);
}

function computeAuthorizationEpoch(bundle: ProviderLeaseBundle): number {
  const graphReference = leaseDeclaresGraphReferenceCapability(bundle)
    ? 1
    : 0;
  const diagnostics = isAuthorizedDiagnosticsPublication(bundle) ? 1 : 0;
  const effective = bundle.snapshot.effectivePublication ? 1 : 0;
  return (graphReference << 2) | (diagnostics << 1) | effective;
}

export function AgentInteractionProvider({ children }: { children: ReactNode }) {
  const [scope, setScope] = useState<AgentInteractionScope | null>(null);
  const [activeThread, setActiveThread] = useState<AgentInteractionThread | null>(null);
  const [threadSummaries, setThreadSummaries] = useState<AgentInteractionContextValue["threadSummaries"]>([]);
  const [paneState, setPaneState] = useState<AgentInteractionPaneState>({ isOpen: false, mode: "bar" });
  const [activeSurfaceContext, setActiveSurfaceContext] = useState<AgentInteractionSurfaceContext | null>(null);
  const [selectedSource, setSelectedSource] = useState<AgentInteractionSelectedSource | null>(null);

  const leaseBundleRef = useRef<ProviderLeaseBundle | null>(null);
  const [leaseBundle, setLeaseBundle] = useState<ProviderLeaseBundle | null>(null);
  const leaseCallbackGateRef = useRef(createLeaseCallbackGate(() => leaseBundleRef.current?.snapshot ?? null));

  const applyLeaseBundle = useCallback((next: ProviderLeaseBundle) => {
    const nextEpoch = computeAuthorizationEpoch(next);
    const priorEpoch = leaseBundleRef.current ? computeAuthorizationEpoch(leaseBundleRef.current) : -1;
    const bundle: ProviderLeaseBundle = {
      ...next,
      authorizationEpoch: nextEpoch,
      appChromePublisherEpoch: priorEpoch !== nextEpoch
        ? (leaseBundleRef.current?.appChromePublisherEpoch ?? 0) + 1
        : (next.appChromePublisherEpoch ?? leaseBundleRef.current?.appChromePublisherEpoch ?? 0),
    };
    leaseBundleRef.current = bundle;
    setLeaseBundle(bundle);
  }, []);

  const clearLeaseBundle = useCallback(() => {
    leaseBundleRef.current = null;
    setLeaseBundle(null);
  }, []);

  const [leasedActive, setLeasedActive] = useState<LeasedActiveProjection | null>(null);
  const leasedActiveRef = useRef<LeasedActiveProjection | null>(null);
  const [leasedGraphReference, setLeasedGraphReference] = useState<LeasedGraphReference | null>(null);
  const [leasedGraphProjectionState, setLeasedGraphProjectionState] = useState<LeasedGraphProjectionState | null>(
    null,
  );

  const graphReferenceRegistrationRef = useRef<BindingRegistration<GraphReferenceProjectionBinding> | null>(null);
  const [graphReferenceRegistration, setGraphReferenceRegistration] = useState<
    BindingRegistration<GraphReferenceProjectionBinding> | null
  >(null);
  const diagnosticsRegistrationRef = useRef<BindingRegistration<GraphReviewDiagnosticsProjectionPayload> | null>(
    null,
  );
  const [diagnosticsRegistration, setDiagnosticsRegistration] = useState<
    BindingRegistration<GraphReviewDiagnosticsProjectionPayload> | null
  >(null);

  const catalogEntriesRef = useRef<CatalogRegistrationAttachment[]>([]);
  const [catalogEntries, setCatalogEntries] = useState<CatalogRegistrationAttachment[]>([]);
  const projectionActivatorRef = useRef<ProjectionToolActivatorAttachment | null>(null);

  const clearCatalogEntries = useCallback(() => {
    catalogEntriesRef.current = [];
    setCatalogEntries([]);
  }, []);

  /**
   * Same-identity publication updates change descriptor preferredSize synchronously.
   * Patch live catalog preferredSize in place so resolve stays atomic with the
   * publication and open renderers are not temporarily preferred_size_mismatch /
   * unmounted. Kind stays registration-owned so a descriptor kind rewrite still
   * fails closed as kind_mismatch.
   */
  const syncCatalogMetadataFromPublication = useCallback(() => {
    const bundle = leaseBundleRef.current;
    const publication = bundle?.snapshot.effectivePublication;
    const token = bundle?.snapshot.token;
    if (!publication || !token) return;
    let changed = false;
    const next = catalogEntriesRef.current.map((entry) => {
      if (entry.surfaceToken !== token) return entry;
      const descriptor = publication.projections.find(
        (candidate) => candidate.id === entry.registration.projectionId,
      );
      if (!descriptor) return entry;
      if (entry.registration.preferredSize === descriptor.preferredSize) {
        return entry;
      }
      changed = true;
      return {
        ...entry,
        registration: {
          ...entry.registration,
          preferredSize: descriptor.preferredSize,
        },
      };
    });
    if (!changed) return;
    catalogEntriesRef.current = next;
    setCatalogEntries([...next]);
  }, []);

  const clearSelectedProjection = useCallback(() => {
    leasedActiveRef.current = null;
    setLeasedActive(null);
    setLeasedGraphReference(null);
    setLeasedGraphProjectionState(null);
  }, []);

  /** Clear leased object/content attachments without touching an open Tool projection. */
  const clearLeasedGraphReferenceContent = useCallback(() => {
    setLeasedGraphReference(null);
    setLeasedGraphProjectionState(null);
    if (leasedActiveRef.current?.projection.kind === "content") {
      leasedActiveRef.current = null;
      setLeasedActive(null);
    }
  }, []);

  const revalidateLeasedAttachmentsAfterSnapshot = useCallback(() => {
    const bundle = leaseBundleRef.current;
    if (!bundle?.snapshot.effectivePublication) {
      clearSelectedProjection();
      graphReferenceRegistrationRef.current = null;
      setGraphReferenceRegistration(null);
      diagnosticsRegistrationRef.current = null;
      setDiagnosticsRegistration(null);
      clearCatalogEntries();
      return;
    }
    const publication = bundle.snapshot.effectivePublication;
    const legacyValidated = bundle.legacyProjection?.validated;
    let nextLeased = leasedActiveRef.current;

    if (legacyValidated) {
      nextLeased = revalidateLeasedProjection(legacyValidated, nextLeased, publication);
    } else if (nextLeased?.projection.kind === "tool") {
      // Native publications must clear leasedActive when the launching tool or
      // target descriptor disappears under the same identity (no resurrection).
      nextLeased = revalidateLeasedToolProjection(publication, nextLeased);
    } else if (nextLeased?.projection.kind === "content") {
      // Native content survives only while the lease still declares capability.
      if (!leaseDeclaresGraphReferenceCapability(bundle)) {
        nextLeased = null;
      }
    }

    leasedActiveRef.current = nextLeased;
    setLeasedActive(nextLeased);
    if (!nextLeased || nextLeased.projection.kind !== "content") {
      setLeasedGraphReference(null);
      setLeasedGraphProjectionState(null);
    }
    if (!leaseDeclaresGraphReferenceCapability(bundle)) {
      graphReferenceRegistrationRef.current = null;
      setGraphReferenceRegistration(null);
    }
    if (!isAuthorizedDiagnosticsPublication(bundle)) {
      diagnosticsRegistrationRef.current = null;
      setDiagnosticsRegistration(null);
    }
  }, [clearCatalogEntries, clearSelectedProjection]);

  const applySameIdentityConfigUpdate = useCallback(
    (validated: ValidatedProjectionSurface): boolean => {
      const current = leaseBundleRef.current;
      if (!current?.legacyProjection?.validated) return false;
      if (
        !sameProjectionSurfaceIdentity(
          current.legacyProjection.validated.publication.identity,
          validated.publication.identity,
        )
      ) {
        return false;
      }
      const neutralBase = adaptProjectionSurfaceToNeutralBase(validated);
      const updated = updateSurfaceInteractionLease(
        current.snapshot,
        current.snapshot.token,
        neutralBase,
        leaseCallbackGateRef.current,
      );
      if (!updated) return false;
      applyLeaseBundle({
        snapshot: updated,
        legacyProjection: { validated },
        authorizationEpoch: current.authorizationEpoch,
        appChromePublisherEpoch: current.appChromePublisherEpoch,
      });
      syncCatalogMetadataFromPublication();
      revalidateLeasedAttachmentsAfterSnapshot();
      return true;
    },
    [applyLeaseBundle, revalidateLeasedAttachmentsAfterSnapshot, syncCatalogMetadataFromPublication],
  );

  const publishSurfaceInteractionPublication = useCallback(
    (publication: unknown | null) => {
      const snapshot = bindSurfaceInteractionLease(
        publication,
        "legacy_route",
        leaseCallbackGateRef.current,
      );
      clearSelectedProjection();
      clearCatalogEntries();
      applyLeaseBundle({
        snapshot,
        legacyProjection: null,
        authorizationEpoch: 0,
        appChromePublisherEpoch: leaseBundleRef.current?.appChromePublisherEpoch ?? 0,
      });
      const token = snapshot.token;
      return () => {
        if (leaseBundleRef.current?.snapshot.token !== token) return;
        clearSelectedProjection();
        clearCatalogEntries();
        clearLeaseBundle();
      };
    },
    [applyLeaseBundle, clearCatalogEntries, clearLeaseBundle, clearSelectedProjection],
  );

  const updateSurfaceInteractionPublication = useCallback((publication: unknown) => {
    const current = leaseBundleRef.current;
    if (!current?.snapshot.boundIdentity) return;
    const updated = updateSurfaceInteractionLease(
      current.snapshot,
      current.snapshot.token,
      publication,
      leaseCallbackGateRef.current,
    );
    if (!updated) return;
    applyLeaseBundle({
      ...current,
      snapshot: updated,
    });
    syncCatalogMetadataFromPublication();
    revalidateLeasedAttachmentsAfterSnapshot();
  }, [applyLeaseBundle, revalidateLeasedAttachmentsAfterSnapshot, syncCatalogMetadataFromPublication]);

  const publishAppChromeCompatibility = useCallback((fragment: SurfaceInteractionChromeFragment) => {
    const current = leaseBundleRef.current;
    const capturedToken = current?.snapshot.token ?? null;
    const capturedPublisherEpoch = current?.appChromePublisherEpoch ?? 0;
    if (!capturedToken || !current) return () => undefined;
    const fragmentToken = Symbol("app-chrome-fragment");
    const next = registerChromeCompatibilityFragment(
      current.snapshot,
      capturedToken,
      fragmentToken,
      fragment,
      leaseCallbackGateRef.current,
    );
    if (!next) return () => undefined;
    applyLeaseBundle({ ...current, snapshot: next });
    revalidateLeasedAttachmentsAfterSnapshot();
    return () => {
      const live = leaseBundleRef.current;
      if (!live || live.snapshot.token !== capturedToken) return;
      if (live.appChromePublisherEpoch !== capturedPublisherEpoch) return;
      const updated = unregisterChromeCompatibilityFragment(
        live.snapshot,
        capturedToken,
        fragmentToken,
        leaseCallbackGateRef.current,
      );
      if (!updated) return;
      applyLeaseBundle({ ...live, snapshot: updated });
      revalidateLeasedAttachmentsAfterSnapshot();
    };
  }, [applyLeaseBundle, leaseBundle?.appChromePublisherEpoch, leaseBundle?.authorizationEpoch, revalidateLeasedAttachmentsAfterSnapshot]);

  const publishProjectionSurface = useCallback(
    (publication: ProjectionSurfacePublication | null) => {
      if (publication !== null) {
        const validated = validateProjectionSurfacePublication(publication);
        if (applySameIdentityConfigUpdate(validated)) {
          return () => undefined;
        }
        const neutralBase = adaptProjectionSurfaceToNeutralBase(validated);
        const snapshot = bindSurfaceInteractionLease(
          neutralBase,
          "legacy_projection",
          leaseCallbackGateRef.current,
        );
        clearSelectedProjection();
        clearCatalogEntries();
        applyLeaseBundle({
          snapshot,
          legacyProjection: { validated },
          authorizationEpoch: 0,
          appChromePublisherEpoch: leaseBundleRef.current?.appChromePublisherEpoch ?? 0,
        });
        const token = snapshot.token;
        return () => {
          if (leaseBundleRef.current?.snapshot.token !== token) return;
          clearSelectedProjection();
          clearCatalogEntries();
          clearLeaseBundle();
        };
      }

      const snapshot = bindSurfaceInteractionLease(
        null,
        "legacy_projection",
        leaseCallbackGateRef.current,
      );
      clearSelectedProjection();
      clearCatalogEntries();
      applyLeaseBundle({
        snapshot,
        legacyProjection: { validated: null },
        authorizationEpoch: 0,
        appChromePublisherEpoch: leaseBundleRef.current?.appChromePublisherEpoch ?? 0,
      });
      const token = snapshot.token;
      return () => {
        if (leaseBundleRef.current?.snapshot.token !== token) return;
        clearSelectedProjection();
        clearCatalogEntries();
        clearLeaseBundle();
      };
    },
    [applyLeaseBundle, applySameIdentityConfigUpdate, clearCatalogEntries, clearLeaseBundle, clearSelectedProjection],
  );

  const updateProjectionSurfaceConfig = useCallback(
    (publication: ProjectionSurfacePublication) => {
      applySameIdentityConfigUpdate(validateProjectionSurfacePublication(publication));
    },
    [applySameIdentityConfigUpdate],
  );

  // Exact lease authorization: a callback captured without a current surface
  // lease (null token) must stay a no-op permanently, never a wildcard.
  const surfaceTokenGuard = (capturedToken: symbol | null, bundle: ProviderLeaseBundle | null) => {
    if (capturedToken === null || !bundle) return false;
    return bundle.snapshot.token === capturedToken;
  };

  const currentSurfaceToken = leaseBundle?.snapshot.token ?? null;

  const close = useCallback(() => {
    const capturedToken = currentSurfaceToken;
    const bundle = leaseBundleRef.current;
    if (!surfaceTokenGuard(capturedToken, bundle)) return;
    clearSelectedProjection();
  }, [clearSelectedProjection, currentSurfaceToken]);

  const openToolFromEffectivePublication = useCallback(
    (toolId: string): boolean => {
      const capturedToken = currentSurfaceToken;
      const bundle = leaseBundleRef.current;
      if (!surfaceTokenGuard(capturedToken, bundle)) return false;
      const publication = bundle!.snapshot.effectivePublication;
      if (!publication) return false;

      const tool = publication.tools.find((entry) => entry.id === toolId);
      if (!tool || tool.availability.status !== "enabled") return false;
      if (tool.activation.kind !== "projection") return false;

      const projectionId = tool.activation.projectionId;
      const descriptor = publication.projections.find(
        (entry) => entry.id === projectionId && entry.kind === "tool",
      );
      if (!descriptor) return false;

      const activeToken = bundle!.snapshot.token;
      const next: LeasedActiveProjection = {
        surfaceToken: activeToken,
        launchingToolId: toolId,
        projection: {
          kind: "tool",
          key: projectionId,
          size: descriptor.preferredSize,
          title: tool.label,
        },
      };
      leasedActiveRef.current = next;
      setLeasedActive(next);
      setLeasedGraphReference(null);
      setLeasedGraphProjectionState(null);
      return true;
    },
    [currentSurfaceToken],
  );

  const openTool = useCallback(
    (toolId: string): boolean => openToolFromEffectivePublication(toolId),
    [openToolFromEffectivePublication],
  );

  const activateProjectionTool = useCallback(
    (toolId: string): boolean | Promise<boolean> => {
      const activator = projectionActivatorRef.current;
      const liveToken = leaseBundleRef.current?.snapshot.token ?? null;
      if (activator && liveToken && activator.leaseToken === liveToken) {
        const result = activator.fn(toolId);
        if (isThenable(result)) {
          return Promise.resolve(result).then((value) => value !== false);
        }
        return result !== false;
      }
      return openToolFromEffectivePublication(toolId);
    },
    [openToolFromEffectivePublication],
  );

  const registerProjectionToolActivator = useCallback(
    (activator: (toolId: string) => boolean | void | Promise<boolean | void>) => {
      const capturedToken = currentSurfaceToken;
      const bundle = leaseBundleRef.current;
      if (
        !capturedToken
        || bundle?.snapshot.token !== capturedToken
        || !bundle.snapshot.effectivePublication
      ) {
        return () => undefined;
      }
      const attachment: ProjectionToolActivatorAttachment = {
        leaseToken: capturedToken,
        fn: activator,
      };
      projectionActivatorRef.current = attachment;
      return () => {
        if (projectionActivatorRef.current?.leaseToken === capturedToken) {
          projectionActivatorRef.current = null;
        }
      };
    },
    [currentSurfaceToken],
  );

  const openGraphReference = useCallback(
    (args: OpenGraphReferenceArgs) => {
      const {
        resolution,
        projectionState = resolution.projectionState ?? null,
        glanceOnly = false,
        reference = resolution.reference,
      } = args;
      const capturedToken = currentSurfaceToken;
      const bundle = leaseBundleRef.current;
      if (
        !surfaceTokenGuard(capturedToken, bundle)
        || !canOperateGraphReferenceCapability(bundle, graphReferenceRegistrationRef.current)
      ) {
        return;
      }
      const activeToken = bundle!.snapshot.token;
      const title =
        (resolution.kind === "resolved_graph" ? resolution.graphObject?.label : null)
        ?? (resolution.kind === "resolved_corpus_fallback" ? resolution.fallback.ref.label : null)
        ?? reference?.label
        ?? resolution.locator
        ?? "Related object";
      const next: LeasedActiveProjection = {
        surfaceToken: activeToken,
        projection: {
          kind: "content",
          key: reference?.refType ?? (resolution.kind === "resolved_graph" ? resolution.graphNodeId : resolution.locator) ?? "graph-reference",
          size: glanceOnly ? "compact" : contentSize(resolution),
          title,
          glanceOnly,
        },
      };
      leasedActiveRef.current = next;
      setLeasedActive(next);
      setLeasedGraphReference({ surfaceToken: activeToken, resolution });
      setLeasedGraphProjectionState({ surfaceToken: activeToken, state: projectionState });
    },
    [currentSurfaceToken],
  );

  const expandContent = useCallback(() => {
    const capturedToken = currentSurfaceToken;
    const bundle = leaseBundleRef.current;
    if (
      !surfaceTokenGuard(capturedToken, bundle)
      || !canOperateGraphReferenceCapability(bundle, graphReferenceRegistrationRef.current)
    ) {
      return;
    }
    const activeToken = bundle!.snapshot.token;
    setLeasedActive((current) => {
      if (!current || current.surfaceToken !== activeToken || current.projection.kind !== "content") {
        return current;
      }
      const next: LeasedActiveProjection = {
        surfaceToken: activeToken,
        projection: { ...current.projection, size: "wide", glanceOnly: false },
      };
      leasedActiveRef.current = next;
      return next;
    });
  }, [currentSurfaceToken]);

  // Registrars capture the surface lease they were supplied under AND require
  // an authorized capability on that lease. Token/surfaceId alone is not enough.
  const registerGraphReferenceBinding = useCallback(
    (binding: GraphReferenceProjectionBinding) => {
      const capturedToken = currentSurfaceToken;
      const capturedEpoch = leaseBundleRef.current?.authorizationEpoch ?? -1;
      const bundle = leaseBundleRef.current;
      if (
        !capturedToken
        || bundle?.snapshot.token !== capturedToken
        || !leaseDeclaresGraphReferenceCapability(bundle)
      ) {
        return () => undefined;
      }
      const token = Symbol("graph-reference-binding");
      const registration: BindingRegistration<GraphReferenceProjectionBinding> = {
        surfaceToken: capturedToken,
        token,
        value: binding,
      };
      graphReferenceRegistrationRef.current = registration;
      setGraphReferenceRegistration(registration);
      return () => {
        if (graphReferenceRegistrationRef.current?.token === token) {
          graphReferenceRegistrationRef.current = null;
          // Unregister must revoke leased object content so a replacement binding
          // cannot resurrect the prior resolution under a new lens/context.
          clearLeasedGraphReferenceContent();
        }
        if (leaseBundleRef.current?.authorizationEpoch !== capturedEpoch) return;
        setGraphReferenceRegistration((current) => (current?.token === token ? null : current));
      };
    },
    [clearLeasedGraphReferenceContent, currentSurfaceToken, leaseBundle?.authorizationEpoch],
  );

  const registerToolProjectionPayload = useCallback(
    <K extends RegisterableToolProjectionId>(toolId: K, payload: ToolProjectionPayloadMap[K]) => {
      if (toolId !== GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID) {
        return () => undefined;
      }
      const capturedToken = currentSurfaceToken;
      const capturedEpoch = leaseBundleRef.current?.authorizationEpoch ?? -1;
      const bundle = leaseBundleRef.current;
      if (
        !capturedToken
        || bundle?.snapshot.token !== capturedToken
        || !isAuthorizedDiagnosticsPublication(bundle)
      ) {
        return () => undefined;
      }
      const token = Symbol(`tool-payload:${toolId}`);
      const typedPayload = payload as GraphReviewDiagnosticsProjectionPayload;
      const registration: BindingRegistration<GraphReviewDiagnosticsProjectionPayload> = {
        surfaceToken: capturedToken,
        token,
        value: typedPayload,
      };
      diagnosticsRegistrationRef.current = registration;
      setDiagnosticsRegistration(registration);
      return () => {
        if (diagnosticsRegistrationRef.current?.token === token) {
          diagnosticsRegistrationRef.current = null;
        }
        if (leaseBundleRef.current?.authorizationEpoch !== capturedEpoch) return;
        setDiagnosticsRegistration((current) => (current?.token === token ? null : current));
      };
    },
    [currentSurfaceToken, leaseBundle?.authorizationEpoch],
  );

  const registerProjectionCatalog = useCallback(
    (registration: ProjectionCatalogRegistration) => {
      const capturedToken = currentSurfaceToken;
      const bundle = leaseBundleRef.current;
      // Exact current-lease gate (same pattern as graph-reference / diagnostics):
      // a callback captured under lease A must not mutate state after lease B binds.
      if (
        !capturedToken
        || bundle?.snapshot.token !== capturedToken
        || !bundle.snapshot.effectivePublication
      ) {
        return () => undefined;
      }
      const normalized = normalizeProjectionCatalogRegistration(registration);
      if (!normalized) {
        return () => undefined;
      }
      const registrationToken = Symbol("projection-catalog-registration");
      const attachment: CatalogRegistrationAttachment = {
        surfaceToken: capturedToken,
        registrationToken,
        registration: normalized,
      };
      catalogEntriesRef.current = [...catalogEntriesRef.current, attachment];
      setCatalogEntries([...catalogEntriesRef.current]);
      return () => {
        const live = leaseBundleRef.current;
        if (!live || live.snapshot.token !== capturedToken) return;
        catalogEntriesRef.current = catalogEntriesRef.current.filter(
          (entry) => entry.registrationToken !== registrationToken,
        );
        setCatalogEntries([...catalogEntriesRef.current]);
      };
    },
    [currentSurfaceToken],
  );

  const resolveProjectionCatalog = useCallback(
    (args: {
      projectionId: string;
      active: ActiveProjection;
      bindings: Readonly<Record<string, unknown>>;
    }) => {
      const bundle = leaseBundleRef.current;
      const leaseToken = bundle?.snapshot.token ?? null;
      const publication = bundle?.snapshot.effectivePublication ?? null;
      const liveEntries: ProjectionCatalogLiveEntry[] = catalogEntriesRef.current
        .filter((entry) => entry.surfaceToken === leaseToken)
        .map((entry) => ({
          registrationToken: entry.registrationToken,
          leaseToken: entry.surfaceToken,
          registration: entry.registration,
        }));
      return resolveProjectionCatalogPure({
        leaseToken,
        entries: liveEntries,
        publication,
        projectionId: args.projectionId,
        active: args.active,
        bindings: args.bindings,
      });
    },
    [],
  );

  const graphReferenceBinding = useMemo((): GraphReferenceProjectionBinding | null => {
    const registration = graphReferenceRegistration;
    const bundle = leaseBundle;
    const surfaceToken = bundle?.snapshot.token;
    if (!registration || !surfaceToken || registration.surfaceToken !== surfaceToken) return null;
    if (!canOperateGraphReferenceCapability(bundle, registration)) return null;
    const { token, value: binding } = registration;
    return {
      resolverState: binding.resolverState,
      resolveRelationship: (relationship, originatingScope) =>
        binding.resolveRelationship(relationship, originatingScope),
      openResolvedReference: (resolution, projectionState) => {
        const current = graphReferenceRegistrationRef.current;
        const live = leaseBundleRef.current;
        if (!current || current.token !== token || current.surfaceToken !== surfaceToken) return;
        if (!canOperateGraphReferenceCapability(live, current) || live?.snapshot.token !== surfaceToken) {
          return;
        }
        current.value.openResolvedReference(resolution, projectionState);
      },
      openTool: (toolId) => {
        const current = graphReferenceRegistrationRef.current;
        const live = leaseBundleRef.current;
        if (!current || current.token !== token || current.surfaceToken !== surfaceToken) return;
        if (!canOperateGraphReferenceCapability(live, current) || live?.snapshot.token !== surfaceToken) {
          return;
        }
        current.value.openTool(toolId);
      },
    };
  }, [graphReferenceRegistration, leaseBundle]);

  const projectionSurface = leaseBundle?.legacyProjection?.validated ?? null;
  const surfaceInteractionPublication = leaseBundle?.snapshot.effectivePublication ?? null;
  const surfaceInteractionBasePublication = leaseBundle?.snapshot.rawBasePublication ?? null;

  const active = useMemo(() => {
    if (!leasedActive || !currentSurfaceToken || leasedActive.surfaceToken !== currentSurfaceToken) return null;
    if (
      leasedActive.projection.kind === "content"
      && !canOperateGraphReferenceCapability(leaseBundle, graphReferenceRegistration)
    ) {
      return null;
    }
    const publication = leaseBundle?.snapshot.effectivePublication;
    if (!publication) return null;
    if (leasedActive.projection.kind === "tool") {
      const projectionId = leasedActive.projection.key;
      const launchingToolId = leasedActive.launchingToolId;
      const tool = launchingToolId
        ? publication.tools.find((entry) => entry.id === launchingToolId)
        : publication.tools.find(
            (entry) =>
              entry.activation.kind === "projection"
              && entry.activation.projectionId === projectionId,
          );
      if (!tool || tool.availability.status !== "enabled") return null;
      if (tool.activation.kind !== "projection" || tool.activation.projectionId !== projectionId) {
        return null;
      }
      const descriptor = publication.projections.find(
        (entry) => entry.id === projectionId && entry.kind === "tool",
      );
      if (!descriptor) return null;
    }
    return leasedActive.projection;
  }, [currentSurfaceToken, graphReferenceRegistration, leasedActive, leaseBundle]);

  const activeGraphReference = useMemo(() => {
    if (!leasedGraphReference || !currentSurfaceToken || leasedGraphReference.surfaceToken !== currentSurfaceToken) {
      return null;
    }
    if (!canOperateGraphReferenceCapability(leaseBundle, graphReferenceRegistration)) return null;
    return leasedGraphReference.resolution;
  }, [currentSurfaceToken, graphReferenceRegistration, leasedGraphReference, leaseBundle]);

  const graphReferenceProjectionState = useMemo(() => {
    if (
      !leasedGraphProjectionState
      || !currentSurfaceToken
      || leasedGraphProjectionState.surfaceToken !== currentSurfaceToken
    ) {
      return null;
    }
    if (!canOperateGraphReferenceCapability(leaseBundle, graphReferenceRegistration)) return null;
    return leasedGraphProjectionState.state;
  }, [currentSurfaceToken, graphReferenceRegistration, leasedGraphProjectionState, leaseBundle]);

  const graphReviewDiagnosticsPayload = useMemo(() => {
    const registration = diagnosticsRegistration;
    const bundle = leaseBundle;
    const surfaceToken = bundle?.snapshot.token;
    if (!registration || !surfaceToken || registration.surfaceToken !== surfaceToken) return null;
    if (!isAuthorizedDiagnosticsPublication(bundle)) return null;
    return registration.value;
  }, [diagnosticsRegistration, leaseBundle]);

  const refreshSummaries = useCallback((nextScope: AgentInteractionScope | null = scope) => {
    if (!nextScope) {
      setThreadSummaries([]);
      return;
    }
    setThreadSummaries(listAgentThreads(
      nextScope.campaignId,
      nextScope.surfaceId ?? "plan",
      nextScope.documentId,
      nextScope.surfaceInstanceId,
    ));
  }, [scope]);

  const rehydrateScope = useCallback((nextScope: AgentInteractionScope) => {
    if (sameScope(scope, nextScope)) return;
    const surfaceId = nextScope.surfaceId ?? "plan";
    const storedThread = loadAgentThread(
      nextScope.campaignId,
      surfaceId,
      nextScope.documentId,
      nextScope.surfaceInstanceId,
    );
    setScope(nextScope);
    setActiveThread(storedThread);
    setSelectedSource(null);
    setThreadSummaries(listAgentThreads(
      nextScope.campaignId,
      surfaceId,
      nextScope.documentId,
      nextScope.surfaceInstanceId,
    ));
  }, [scope]);

  const updateThread = useCallback((thread: AgentInteractionThread) => {
    persistAgentThread(thread);
    setActiveThread(thread);
    refreshSummaries({
      campaignId: thread.campaignId,
      sessionNumber: thread.session ?? null,
      surfaceId: thread.surfaceId,
      documentId: thread.documentId,
      surfaceInstanceId: thread.surfaceInstanceId,
    });
    return thread;
  }, [refreshSummaries]);

  const ensureThread = useCallback((title = "New prep thread", backend: LiveQueryBackend = "hermes") => {
    if (activeThread) return activeThread;
    if (!scope) throw new Error("Agent Interaction scope has not been published");
    const nextThread = createAgentInteractionThread(
      scope.campaignId,
      scope.sessionNumber,
      scope.surfaceId ?? "plan",
      backend,
      title,
      scope.documentId,
      scope.surfaceInstanceId,
    );
    return updateThread(nextThread);
  }, [activeThread, scope, updateThread]);

  const createThread = useCallback((title = "New prep thread") => {
    if (!scope) throw new Error("Agent Interaction scope has not been published");
    const nextThread = createAgentInteractionThread(
      scope.campaignId,
      scope.sessionNumber,
      scope.surfaceId ?? "plan",
      "hermes",
      title,
      scope.documentId,
      scope.surfaceInstanceId,
    );
    setActiveAgentThread(
      scope.campaignId,
      scope.surfaceId ?? "plan",
      nextThread.threadId,
      scope.documentId,
      scope.surfaceInstanceId,
    );
    setSelectedSource(null);
    return updateThread(nextThread);
  }, [scope, updateThread]);

  const switchThread = useCallback((threadId: string) => {
    if (!scope) return null;
    const nextThread = loadAgentThreadById(scope.campaignId, threadId);
    if (!nextThread) return null;
    setActiveAgentThread(
      scope.campaignId,
      scope.surfaceId ?? "plan",
      threadId,
      scope.documentId,
      scope.surfaceInstanceId,
    );
    setSelectedSource(null);
    setActiveThread(nextThread);
    refreshSummaries(scope);
    return nextThread;
  }, [refreshSummaries, scope]);

  const deleteThread = useCallback((threadId: string) => {
    if (!scope) return;
    const doomed = loadAgentThreadById(scope.campaignId, threadId);
    if (!doomed) return;
    deleteStoredAgentThread(doomed);
    const nextThread = loadAgentThread(
      scope.campaignId,
      scope.surfaceId ?? "plan",
      scope.documentId,
      scope.surfaceInstanceId,
    );
    setActiveThread(nextThread);
    setSelectedSource(null);
    refreshSummaries(scope);
  }, [refreshSummaries, scope]);

  const renameThread = useCallback((title: string) => {
    const baseThread = activeThread ?? ensureThread(title);
    return updateThread(renameAgentThread(baseThread, title));
  }, [activeThread, ensureThread, updateThread]);

  const clearThread = useCallback(() => {
    if (!activeThread) return null;
    clearAgentThread(activeThread);
    const nextThread = { ...activeThread, updatedAt: new Date().toISOString(), turns: [], uiState: { traceVisible: activeThread.uiState?.traceVisible ?? false, scrollAnchorTurnId: null, newThreadSuggestionDismissed: false } };
    setSelectedSource(null);
    return updateThread(nextThread);
  }, [activeThread, updateThread]);

  const updateActiveTurn = useCallback((turnId: string) => {
    if (!activeThread) return;
    updateThread({ ...activeThread, uiState: { traceVisible: activeThread.uiState?.traceVisible ?? false, ...activeThread.uiState, scrollAnchorTurnId: turnId } });
    setSelectedSource(null);
  }, [activeThread, updateThread]);

  const appendResponseTurn = useCallback((question: string, response: Parameters<typeof turnFromResponse>[1]) => {
    const backend = activeThread?.activeBackend ?? "hermes";
    const currentThread = activeThread ?? ensureThread(threadTitleFromQuestion(question), backend);
    const nextTurn = turnFromResponse(question, response, backend);
    const nextTurns = [nextTurn, ...currentThread.turns].slice(0, AGENT_TURN_HISTORY_CAP);
    const nextThread: AgentInteractionThread = {
      ...currentThread,
      threadId: response.agent_thread_id ?? currentThread.threadId,
      title: currentThread.turns.length ? currentThread.title : threadTitleFromQuestion(question),
      updatedAt: new Date().toISOString(),
      activeBackend: backend,
      hermesSession: response.mode === "hermes_graph_agent"
        ? (response.hermes_session ?? currentThread.hermesSession ?? null)
        : (response.hermes_session ?? currentThread.hermesSession ?? null),
      turns: nextTurns,
      uiState: {
        traceVisible: currentThread.uiState?.traceVisible ?? false,
        scrollAnchorTurnId: nextTurn.turnId,
        newThreadSuggestionDismissed: currentThread.uiState?.newThreadSuggestionDismissed ?? false,
      },
    };
    setSelectedSource(null);
    return updateThread(nextThread);
  }, [activeThread, ensureThread, updateThread]);

  const updateTurnFreshness: AgentInteractionContextValue["updateTurnFreshness"] = useCallback((turnId, freshness) => {
    if (!activeThread) return null;
    return updateThread({
      ...activeThread,
      updatedAt: new Date().toISOString(),
      turns: activeThread.turns.map((turn) => (turn.turnId === turnId ? { ...turn, corpusFreshness: freshness } : turn)),
    });
  }, [activeThread, updateThread]);

  const value = useMemo<AgentInteractionContextValue>(() => ({
    scope,
    activeThread,
    activeThreadId: activeThread?.threadId ?? null,
    threads: activeThread ? [activeThread] : [],
    threadSummaries,
    turns: activeThread?.turns ?? [],
    traceVisible: activeThread?.uiState?.traceVisible ?? false,
    paneState,
    activeSurfaceContext,
    selectedSource,
    projectionSurface,
    surfaceInteractionPublication,
    surfaceInteractionBasePublication,
    active,
    activeGraphReference,
    graphReferenceProjectionState,
    graphReferenceBinding,
    graphReviewDiagnosticsPayload,
    publishProjectionSurface,
    updateProjectionSurfaceConfig,
    publishSurfaceInteractionPublication,
    updateSurfaceInteractionPublication,
    publishAppChromeCompatibility,
    openTool,
    activateProjectionTool,
    registerProjectionToolActivator,
    openGraphReference,
    expandContent,
    close,
    registerGraphReferenceBinding,
    registerToolProjectionPayload,
    registerProjectionCatalog,
    resolveProjectionCatalog,
    publishSurfaceContext: setActiveSurfaceContext,
    setPaneOpen: (isOpen) => setPaneState((current) => ({ ...current, isOpen, mode: isOpen ? "pane" : "bar" })),
    setPaneMode: (mode) => setPaneState((current) => ({ ...current, mode })),
    setSelectedSource,
    rehydrateScope,
    ensureThread,
    createThread,
    switchThread,
    deleteThread,
    renameThread,
    clearThread,
    updateThread,
    updateActiveTurn,
    appendResponseTurn,
    updateTurnFreshness,
  }), [
    active,
    activeGraphReference,
    activeSurfaceContext,
    activeThread,
    appendResponseTurn,
    clearThread,
    close,
    createThread,
    deleteThread,
    ensureThread,
    expandContent,
    graphReferenceBinding,
    graphReferenceProjectionState,
    graphReviewDiagnosticsPayload,
    openGraphReference,
    openTool,
    activateProjectionTool,
    registerProjectionToolActivator,
    paneState,
    projectionSurface,
    surfaceInteractionPublication,
    surfaceInteractionBasePublication,
    publishProjectionSurface,
    publishSurfaceInteractionPublication,
    publishAppChromeCompatibility,
    rehydrateScope,
    registerGraphReferenceBinding,
    registerToolProjectionPayload,
    registerProjectionCatalog,
    resolveProjectionCatalog,
    renameThread,
    scope,
    selectedSource,
    switchThread,
    threadSummaries,
    updateActiveTurn,
    updateProjectionSurfaceConfig,
    updateSurfaceInteractionPublication,
    updateThread,
    updateTurnFreshness,
    catalogEntries,
  ]);

  return <AgentInteractionContext.Provider value={value}>{children}</AgentInteractionContext.Provider>;
}

export function useAgentInteraction(): AgentInteractionContextValue {
  const context = useContext(AgentInteractionContext);
  if (!context) throw new Error("useAgentInteraction must be used within AgentInteractionProvider");
  return context;
}

export function useOptionalAgentInteraction(): AgentInteractionContextValue | null {
  return useContext(AgentInteractionContext);
}
