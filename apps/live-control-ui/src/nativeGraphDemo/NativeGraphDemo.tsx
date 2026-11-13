import { useCallback, useEffect, useId, useLayoutEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import type {
  LocalObjectId,
  LocalRelationshipId,
  LocalWorldId,
  LocalWorldRecord,
  PublishedRevisionId,
  WriteLayoutResult,
} from "../localWorld/localWorldRepository";
import { WorldGraphCanvas } from "../localWorld/worldGraphCanvas/WorldGraphCanvas";
import {
  createNativeGraphDemoApi,
  NativeGraphDemoApiError,
  type NativeGraph,
  type NativeGraphCompleteness,
  type NativeGraphDemoApi,
  type NativeObjectKind,
  type NativePrepareRequest,
  type OperationLookupResult,
  type PrepareResult,
} from "./nativeGraphDemoApi";
import type { NativeGraphEntity } from "../api/nativeGraphInspection";
import { nativeGraphPresentation } from "./nativeGraphPresentation";
import { NativeGraphNodeExplorer } from "./GraphNodeExplorer";
import { compactNodeLabel } from "./graphNodeExplorerModel";
import { buildSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import {
  SurfaceContextAction,
  SurfaceContextBadge,
  SurfaceContextModule,
  SurfaceContextPopover,
  SurfaceContextStatus,
  SurfaceContextValue,
  useSurfaceContextContribution,
} from "../surfaceInteraction/contextHost";
import "./nativeGraphDemo.css";

const STORAGE_VERSION = 1;
const MAX_COORDINATE = 6000;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const PREDICATE_PATTERN = /^[a-z0-9]+(?:[._-][a-z0-9]+)*$/;
const PREDICATE_PATTERN_HTML = "[a-z0-9]+([._-][a-z0-9]+)*";
const MAX_NATIVE_NAME_UTF8_BYTES = 128;

function exceedsNativeNameByteLimit(name: string): boolean {
  return new TextEncoder().encode(name.trim()).length > MAX_NATIVE_NAME_UTF8_BYTES;
}
const CUSTOM_PREDICATE_OPTION = "__custom_predicate__";
const OBJECT_KINDS: readonly NativeObjectKind[] = ["person", "location", "event"];

interface DemoFormDraft {
  readonly objectName: string;
  readonly objectKind: NativeObjectKind;
  readonly sourceId: string;
  readonly targetId: string;
  readonly predicate: string;
}

type PendingNativeOperation = NativePrepareRequest;

interface StoredDraftEnvelope {
  readonly version: 1;
  readonly world_id: string;
  readonly draft: DemoFormDraft;
  readonly pending: PendingNativeOperation | null;
  readonly pending_phase: "prepare" | "confirm";
  readonly placement?: StoredPlacementIntent | null;
}

interface StoredPlacementIntent {
  readonly kind: NativeObjectKind;
  readonly position: { readonly x: number; readonly y: number };
  readonly operation_id: string | null;
  readonly base_revision_id: string | null;
  readonly created_node_id: string | null;
}

interface LayoutState {
  readonly worldId: string;
  readonly positions: Readonly<Record<string, { readonly x: number; readonly y: number }>>;
  readonly revision: number;
}

type PendingStatus = "none" | "prepare_retry" | "not_sent" | "preparing" | "checking" | "not_found" | "rejected" | "unknown" | "prepared";
type NoticeKind = "success" | "info" | "warning" | "error";
interface Notice { readonly kind: NoticeKind; readonly text: string }

const EMPTY_DRAFT: DemoFormDraft = {
  objectName: "",
  objectKind: "person",
  sourceId: "",
  targetId: "",
  predicate: "",
};

const MISSING_MANAGED_API: NativeGraphDemoApi = {
  readGraph: () => Promise.reject(new Error("This managed World graph needs its verified API binding.")),
  prepare: () => Promise.reject(new Error("This managed World graph needs its verified API binding.")),
  confirm: () => Promise.reject(new Error("This managed World graph needs its verified API binding.")),
  readOperation: () => Promise.reject(new Error("This managed World graph needs its verified API binding.")),
};

function storageKey(kind: "layout" | "draft", worldId: string, stateScopeId?: string): string {
  const scope = stateScopeId === undefined ? "" : `${encodeURIComponent(stateScopeId)}:`;
  return `dungeonmind-native-demo:${kind}:${scope}${encodeURIComponent(worldId)}`;
}

function parseKind(value: unknown): value is NativeObjectKind {
  return typeof value === "string" && OBJECT_KINDS.includes(value as NativeObjectKind);
}

function parsePending(value: unknown): PendingNativeOperation | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as Record<string, unknown>;
  if (typeof candidate.operation_id !== "string" || !UUID_PATTERN.test(candidate.operation_id)
    || typeof candidate.expected_revision_id !== "string" || !candidate.expected_revision_id) return null;
  if (candidate.kind === "create_object" && typeof candidate.name === "string" && parseKind(candidate.object_kind)) {
    return candidate as unknown as PendingNativeOperation;
  }
  if (candidate.kind === "connect" && typeof candidate.source_id === "string" && typeof candidate.target_id === "string"
    && typeof candidate.predicate === "string") return candidate as unknown as PendingNativeOperation;
  return null;
}

function parseStoredDraft(value: unknown, worldId: string): StoredDraftEnvelope | null {
  if (!value || typeof value !== "object") return null;
  const envelope = value as Record<string, unknown>;
  if (envelope.version !== STORAGE_VERSION || envelope.world_id !== worldId || !envelope.draft || typeof envelope.draft !== "object") return null;
  const draft = envelope.draft as Record<string, unknown>;
  if (typeof draft.objectName !== "string" || !parseKind(draft.objectKind)
    || typeof draft.sourceId !== "string" || typeof draft.targetId !== "string" || typeof draft.predicate !== "string") return null;
  const pending = envelope.pending === null ? null : parsePending(envelope.pending);
  if (envelope.pending !== null && pending === null) return null;
  if (envelope.pending_phase !== undefined && envelope.pending_phase !== "prepare" && envelope.pending_phase !== "confirm") return null;
  let placement: StoredPlacementIntent | null = null;
  if (envelope.placement && typeof envelope.placement === "object") {
    const candidate = envelope.placement as Record<string, unknown>;
    const position = candidate.position && typeof candidate.position === "object" ? candidate.position as Record<string, unknown> : null;
    if (parseKind(candidate.kind) && position && typeof position.x === "number" && Number.isFinite(position.x)
      && typeof position.y === "number" && Number.isFinite(position.y)
      && (candidate.operation_id === null || typeof candidate.operation_id === "string")
      && (candidate.base_revision_id === null || typeof candidate.base_revision_id === "string")
      && (candidate.created_node_id === undefined || candidate.created_node_id === null || typeof candidate.created_node_id === "string")) {
      placement = {
        kind: candidate.kind,
        position: { x: Math.max(0, Math.min(MAX_COORDINATE, position.x)), y: Math.max(0, Math.min(MAX_COORDINATE, position.y)) },
        operation_id: candidate.operation_id as string | null,
        base_revision_id: candidate.base_revision_id as string | null,
        created_node_id: typeof candidate.created_node_id === "string" ? candidate.created_node_id : null,
      };
    }
  }
  return {
    version: STORAGE_VERSION,
    world_id: worldId,
    draft: {
      objectName: draft.objectName.slice(0, 120),
      objectKind: draft.objectKind,
      sourceId: draft.sourceId,
      targetId: draft.targetId,
      predicate: draft.predicate.slice(0, 120),
    },
    pending,
    pending_phase: envelope.pending_phase === "confirm" ? "confirm" : "prepare",
    placement,
  };
}

function safeReadDraft(worldId: string, stateScopeId?: string): StoredDraftEnvelope | null {
  try {
    // sessionStorage is isolated per tab and survives reload/navigation in that tab.
    // A second tab cannot overwrite this tab's operation ID or recovery form.
    const raw = window.sessionStorage.getItem(storageKey("draft", worldId, stateScopeId));
    return raw ? parseStoredDraft(JSON.parse(raw), worldId) : null;
  } catch {
    return null;
  }
}

function safeWriteDraft(worldId: string, draft: DemoFormDraft, pending: PendingNativeOperation | null, phase: "prepare" | "confirm" = "prepare", placement: StoredPlacementIntent | null | undefined = undefined, stateScopeId?: string): boolean {
  try {
    const retainedPlacement = placement === undefined ? safeReadDraft(worldId, stateScopeId)?.placement ?? null : placement;
    const envelope: StoredDraftEnvelope = { version: STORAGE_VERSION, world_id: worldId, draft, pending, pending_phase: phase, placement: retainedPlacement };
    window.sessionStorage.setItem(storageKey("draft", worldId, stateScopeId), JSON.stringify(envelope));
    return true;
  } catch {
    return false;
  }
}

function safeClearDraft(worldId: string, draft: DemoFormDraft, stateScopeId?: string): boolean {
  return safeWriteDraft(worldId, draft, null, "prepare", undefined, stateScopeId);
}

function readLayout(worldId: string, stateScopeId?: string): Readonly<Record<string, { readonly x: number; readonly y: number }>> {
  try {
    const raw = window.localStorage.getItem(storageKey("layout", worldId, stateScopeId));
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    const positions: Record<string, { x: number; y: number }> = Object.create(null) as Record<string, { x: number; y: number }>;
    // Keep presentation coordinates for temporarily omitted native nodes in partial reads.
    // They remain inert unless a matching node ID appears in a later server readback.
    for (const [id, value] of Object.entries(parsed).slice(0, 4096)) {
      if (!id || id.length > 512 || id === "__proto__" || id === "constructor" || id === "prototype" || !value || typeof value !== "object") continue;
      const candidate = value as Record<string, unknown>;
      if (typeof candidate.x !== "number" || !Number.isFinite(candidate.x) || typeof candidate.y !== "number" || !Number.isFinite(candidate.y)) continue;
      positions[id] = {
        x: Math.max(0, Math.min(MAX_COORDINATE, candidate.x)),
        y: Math.max(0, Math.min(MAX_COORDINATE, candidate.y)),
      };
    }
    return positions;
  } catch {
    return {};
  }
}

function writeLayout(worldId: string, positions: Readonly<Record<string, { readonly x: number; readonly y: number }>>, stateScopeId?: string): boolean {
  try {
    window.localStorage.setItem(storageKey("layout", worldId, stateScopeId), JSON.stringify(positions));
    return true;
  } catch {
    return false;
  }
}

/**
 * The legacy canvas accepts a LocalWorldRecord shape. This is only a view model:
 * native IDs are copied verbatim, the published revision comes from the server,
 * and browser state is limited to presentation layout and recoverable form drafts.
 */
function toCanvasSnapshot(graph: NativeGraph): LocalWorldRecord["snapshot"] {
  const worldId = graph.world_id as LocalWorldId;
  return {
  worldId,
  title: "DungeonMind native graph",
  objects: graph.nodes.map((node) => {
    const presentation = nativeGraphPresentation(node);
    return {
      id: node.id as LocalObjectId,
      name: presentation.displayName,
      kind: presentation.displayKind,
      properties: {
        recordedNames: [...presentation.recordedNames],
        recordedClassifications: [...presentation.classificationTerms],
      },
    };
  }),
  relationships: graph.edges.map((edge) => ({
    id: edge.id as LocalRelationshipId,
    fromObjectId: edge.source_id as LocalObjectId,
    toObjectId: edge.target_id as LocalObjectId,
    kind: edge.predicate,
    properties: {},
  })),
  };
}

function toCanvasRecord(
  graph: NativeGraph,
  snapshot: LocalWorldRecord["snapshot"],
  layout: LayoutState,
): LocalWorldRecord {
  return {
    snapshot,
    // This field exists only for the legacy canvas contract; it is not a native or local semantic revision.
    localRevision: 0,
    publishedRevisionId: graph.revision_id as PublishedRevisionId,
    layout: {
      positions: layout.worldId === graph.world_id ? layout.positions : {},
      viewport: { x: 0, y: 0, zoom: 1 },
      layoutVersion: layout.worldId === graph.world_id ? layout.revision : 0,
    },
    layoutRevision: layout.worldId === graph.world_id ? layout.revision : 0,
    history: [],
  };
}

function describeError(error: unknown): string {
  return error instanceof Error ? error.message : "The native graph service could not complete that request.";
}

function asApiError(error: unknown): NativeGraphDemoApiError | null {
  return error instanceof NativeGraphDemoApiError ? error : null;
}

function detailLimitations(graph: NativeGraph): string[] {
  return graph.limitations.filter((value) => typeof value === "string" && Boolean(value.trim()));
}

function isNativeKindSupported(graph: NativeGraph, kind: NativeObjectKind): boolean {
  const kinds = graph.capabilities.object_kinds;
  return Array.isArray(kinds) && kinds.includes(kind);
}

function canConnectGraph(graph: NativeGraph | null): boolean {
  if (!graph || !graph.capabilities.connect) return false;
  const { allowed_predicates: allowedPredicates, allows_custom_predicates: allowsCustom } = graph.capabilities;
  return (allowedPredicates === undefined && allowsCustom === undefined)
    || allowsCustom === true
    || Boolean(allowedPredicates?.length);
}

function usesFinitePredicateOptions(graph: NativeGraph): boolean {
  return (graph.capabilities.allowed_predicates !== undefined && graph.capabilities.allows_custom_predicates !== true)
    || (graph.capabilities.allowed_predicates === undefined && graph.capabilities.allows_custom_predicates === false);
}

function isPredicateAllowed(graph: NativeGraph, predicate: string): boolean {
  const { allowed_predicates: allowedPredicates, allows_custom_predicates: allowsCustom } = graph.capabilities;
  if (allowedPredicates?.includes(predicate)) return true;
  if (allowsCustom === true) return PREDICATE_PATTERN.test(predicate);
  if (allowedPredicates !== undefined || allowsCustom === false) return false;
  // Older playground profiles predate predicate descriptors and keep their existing syntax.
  return PREDICATE_PATTERN.test(predicate);
}

function operationName(operation: PendingNativeOperation): string {
  return operation.kind === "create_object" ? `Create ${operation.object_kind}` : "Connect objects";
}

function graphCompleteness(graph: NativeGraph): NativeGraphCompleteness | null {
  return graph.completeness ?? null;
}

function completenessReasonLabel(reason: string): string {
  switch (reason) {
    case "non_graph_assertions": return "Some assertions could not be represented as graph edges";
    case "entity_name_missing": return "Some entities have no usable name";
    case "entity_name_conflict": return "Some entity names conflict";
    case "entity_classification_ambiguous": return "Some entity types are ambiguous";
    default: return reason.replace(/[_-]+/g, " ");
  }
}

function createdNodeIdFromResult(value: unknown): string | null {
  if (!value || typeof value !== "object") return null;
  const id = (value as Record<string, unknown>).created_node_id;
  return typeof id === "string" && id.length > 0 ? id : null;
}

type EmbeddedPanel = "create" | "connect" | "info" | "details" | null;

interface NativeGraphDemoContextProps {
  readonly graph: NativeGraph | null;
  readonly activePanel: EmbeddedPanel;
  readonly mode: "playground" | "managed";
  readonly worldTitle?: string;
  readonly loading: boolean;
  readonly refreshing: boolean;
  readonly hasPendingOperation: boolean;
  readonly pendingStatus: PendingStatus;
  readonly hasPlacementIntent: boolean;
  readonly onPanelChange: (panel: EmbeddedPanel) => void;
  readonly onRefresh: () => void;
  readonly onExport: () => void;
  readonly canRefresh: boolean;
  readonly searchContent: ReactNode;
  readonly neighborhoodContent: ReactNode;
  readonly onControlsHost: (host: HTMLDivElement | null) => void;
}

function NativeGraphDemoContext({
  graph,
  activePanel,
  mode,
  worldTitle,
  loading,
  refreshing,
  hasPendingOperation,
  pendingStatus,
  hasPlacementIntent,
  onPanelChange,
  onRefresh,
  onExport,
  canRefresh,
  searchContent,
  neighborhoodContent,
  onControlsHost,
}: NativeGraphDemoContextProps) {
  const controlsRowRef = useRef<HTMLDivElement>(null);
  const [menu, setMenu] = useState<"find" | "more" | "focus" | null>(null);
  const dismissMenu = useCallback(() => {
    if (menu) controlsRowRef.current?.querySelector<HTMLButtonElement>(`[data-graph-menu="${menu}"]`)?.focus();
    setMenu(null);
  }, [menu]);
  useLayoutEffect(() => {
    if (menu === "focus" && !neighborhoodContent) {
      setMenu(null);
      controlsRowRef.current?.querySelector<HTMLButtonElement>('[data-graph-menu="find"]')?.focus();
    }
  }, [menu, neighborhoodContent]);
  const surfaceIdentity = useMemo(() => buildSurfaceInteractionIdentity({
    surfaceId: "index",
    instanceParts: ["buddy-native-graph-playground"],
  }), []);
  const completeness = graph ? graphCompleteness(graph) : null;
  const status = loading && !graph ? "Opening graph…"
    : !graph ? "Graph unavailable"
      : hasPendingOperation ? pendingStatus === "prepared" ? "Review ready" : pendingStatus === "preparing" ? "Preparing review" : pendingStatus === "checking" ? "Checking review" : "Review needs attention"
        : completeness?.status === "partial" ? "Partial native read" : "Saved to DungeonMind";
  const identity = mode === "managed"
    ? `World · ${worldTitle?.trim() || "Selected World"}`
    : "Buddy playground · private graph";
  const content = useMemo(() => (
    <SurfaceContextModule className="native-demo-context">
      <div className="native-demo-context__row" ref={controlsRowRef} onKeyDown={(event) => {
        if (event.key === "Escape" && menu) {
          controlsRowRef.current?.querySelector<HTMLButtonElement>(`[data-graph-menu="${menu}"]`)?.focus();
          setMenu(null);
          event.preventDefault();
          event.stopPropagation();
        }
      }}>
        <SurfaceContextValue className="native-demo-context__identity" title={identity}>{identity}</SurfaceContextValue>
        <SurfaceContextAction className="native-demo-context__status-action" disabled={!graph} aria-pressed={activePanel === "info"}
          title={graph ? `${graph.nodes.length} loaded objects · ${graph.edges.length} listed relationships. Open graph information.` : status}
          onClick={() => onPanelChange(activePanel === "info" ? null : "info")}>
          <SurfaceContextStatus tone={!graph && !loading ? "error" : hasPendingOperation || completeness?.status === "partial" ? "warning" : "neutral"}>
            {refreshing ? "Refreshing…" : status}{completeness?.status === "partial" && (refreshing || status !== "Partial native read") ? " · partial read" : ""}
          </SurfaceContextStatus>
        </SurfaceContextAction>
        {hasPlacementIntent ? <SurfaceContextBadge className="native-demo-context__placement">Placement ready</SurfaceContextBadge> : null}
        <SurfaceContextPopover open={menu === "find"} onOpenChange={(open) => setMenu(open ? "find" : null)} title="Find an object"
          trigger={<SurfaceContextAction disabled={!graph} aria-haspopup="dialog" data-graph-menu="find" aria-label={`Find an object${graph ? ` · ${graph.nodes.length} loaded` : ""}`} aria-expanded={menu === "find"} onClick={() => setMenu(menu === "find" ? null : "find")}>Find</SurfaceContextAction>}>
          <div onClick={(event) => { if ((event.target as HTMLElement).closest("[data-graph-search-result]")) dismissMenu(); }}>{searchContent}</div>
        </SurfaceContextPopover>
        <div className="native-demo-context__canvas-controls" ref={onControlsHost} />
        {neighborhoodContent ? <SurfaceContextPopover open={menu === "focus"} onOpenChange={(open) => setMenu(open ? "focus" : null)} title="Focused neighborhood"
          trigger={<SurfaceContextAction aria-haspopup="dialog" data-graph-menu="focus" aria-label="Focused neighborhood" aria-expanded={menu === "focus"} onClick={() => setMenu(menu === "focus" ? null : "focus")}>Focus</SurfaceContextAction>}>
          {neighborhoodContent}
        </SurfaceContextPopover> : null}
        <SurfaceContextPopover open={menu === "more"} onOpenChange={(open) => setMenu(open ? "more" : null)} title="Graph actions" align="end"
          trigger={<SurfaceContextAction aria-haspopup="dialog" data-graph-menu="more" aria-label="More graph actions" aria-expanded={menu === "more"} onClick={() => setMenu(menu === "more" ? null : "more")}>More</SurfaceContextAction>}>
          <div className="native-demo-context__menu-actions">
            <SurfaceContextAction disabled={!canRefresh || loading || refreshing || hasPendingOperation} onClick={() => { dismissMenu(); onRefresh(); }}>Refresh</SurfaceContextAction>
            <SurfaceContextAction disabled={!graph || hasPendingOperation} onClick={() => { dismissMenu(); onPanelChange(activePanel === "info" ? null : "info"); }}>Info</SurfaceContextAction>
            <SurfaceContextAction disabled={!graph} onClick={() => { dismissMenu(); onExport(); }}>Export snapshot</SurfaceContextAction>
          </div>
        </SurfaceContextPopover>
      </div>
    </SurfaceContextModule>
  ), [activePanel, canRefresh, completeness, dismissMenu, graph, hasPendingOperation, hasPlacementIntent, identity, loading, menu, neighborhoodContent, onControlsHost, onExport, onPanelChange, onRefresh, refreshing, searchContent, status]);

  useSurfaceContextContribution({
    id: "buddy-native-graph-playground",
    order: 10,
    surfaceIdentity,
    content,
  });
  return null;
}

export interface NativeGraphDemoProps {
  readonly api?: NativeGraphDemoApi;
  /** Render inside Buddy's existing AppChrome frame instead of a standalone page. */
  readonly embedded?: boolean;
  /** The playground is a private synthetic graph; managed mode is supplied only by a verified route composition. */
  readonly mode?: "playground" | "managed";
  readonly worldTitle?: string;
  /** Stable managed-world identity used only to isolate browser draft and layout storage. */
  readonly stateScopeId?: string;
  /** Presentation limit only; does not authorize entity or source access. */
  readonly entityOnlyDetails?: boolean;
  readonly readOnly?: boolean;
}

export function NativeGraphDemo({ api: providedApi, embedded = false, mode = "playground", worldTitle, stateScopeId, entityOnlyDetails = false, readOnly = false }: NativeGraphDemoProps) {
  const api = useMemo(() => providedApi ?? (mode === "managed" ? MISSING_MANAGED_API : createNativeGraphDemoApi()), [mode, providedApi]);
  const [graph, setGraph] = useState<NativeGraph | null>(null);
  const graphNodes = graph?.nodes;
  const nodesById = useMemo(() => new Map(graphNodes?.map((node) => [node.id, node])), [graphNodes]);
  const graphRef = useRef<NativeGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [draft, setDraft] = useState<DemoFormDraft>(EMPTY_DRAFT);
  const draftRef = useRef(draft);
  const [draftReadyWorldId, setDraftReadyWorldId] = useState<string | null>(null);
  const [pendingOperation, setPendingOperationState] = useState<PendingNativeOperation | null>(null);
  const pendingRef = useRef<PendingNativeOperation | null>(null);
  const [pendingPhase, setPendingPhaseState] = useState<"prepare" | "confirm">("prepare");
  const pendingPhaseRef = useRef<"prepare" | "confirm">("prepare");
  const [pendingStatus, setPendingStatus] = useState<PendingStatus>("none");
  const [pendingErrorCode, setPendingErrorCode] = useState<string | null>(null);
  const stalePrepareRejectionRef = useRef(false);
  const [customPredicateMode, setCustomPredicateMode] = useState(false);
  const [reviewSummary, setReviewSummary] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [layout, setLayout] = useState<LayoutState>({ worldId: "", positions: {}, revision: 0 });
  const layoutRef = useRef(layout);
  layoutRef.current = layout;
  const [storageWarning, setStorageWarning] = useState(false);
  const [activePanel, setActivePanel] = useState<EmbeddedPanel>(null);
  const [placementIntent, setPlacementIntent] = useState<StoredPlacementIntent | null>(null);
  const placementIntentRef = useRef<StoredPlacementIntent | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const selectedNodeIdRef = useRef<string | null>(null);
  const [inspectionHistory, setInspectionHistory] = useState<string[]>([]);
  const inspectorHeadingRef = useRef<HTMLHeadingElement | null>(null);
  const focusInspectorRef = useRef(false);
  useLayoutEffect(() => {
    if (focusInspectorRef.current) { inspectorHeadingRef.current?.focus(); focusInspectorRef.current = false; }
  }, [selectedNodeId]);
  const [selectedNodeDetail, setSelectedNodeDetail] = useState<NativeGraphEntity | null>(null);
  const [selectedNodeDetailStatus, setSelectedNodeDetailStatus] = useState<"idle" | "loading" | "ready" | "unavailable" | "error">("idle");
  const [selectedNodeDetailError, setSelectedNodeDetailError] = useState<string | null>(null);
  const detailRequestGenerationRef = useRef(0);
  const detailAbortRef = useRef<AbortController | null>(null);
  const detailGraphRef = useRef<NativeGraph | null>(null);
  const searchId = useId();
  const [objectQuery, setObjectQuery] = useState("");
  const [objectPage, setObjectPage] = useState(0);
  const [viewFocusId, setViewFocusId] = useState<LocalObjectId | null>(null);
  const [neighborhoodDepth, setNeighborhoodDepth] = useState(1);
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);
  const [createdNodeReveal, setCreatedNodeReveal] = useState<{ readonly nodeId: string; readonly worldId: string } | null>(null);
  const pendingCreatedFocusRef = useRef<{ readonly nodeId: string; readonly graph: NativeGraph } | null>(null);
  const [cameraFocusRequest, setCameraFocusRequest] = useState<{ readonly nodeId: LocalObjectId | null; readonly requestId: number; readonly worldId: string; readonly selectNode?: boolean } | undefined>(undefined);
  const cameraFocusRequestIdRef = useRef(0);
  const [cameraFocusResetRequest, setCameraFocusResetRequest] = useState<{readonly requestId: number; readonly fitView: boolean} | undefined>(undefined);
  const [clearSelectionRequest, setClearSelectionRequest] = useState<number | undefined>(undefined);
  const selectionClearRequestIdRef = useRef(0);
  const [canvasControlsHost, setCanvasControlsHost] = useState<HTMLDivElement | null>(null);
  const createNameInputRef = useRef<HTMLInputElement | null>(null);
  const focusCreateInputAfterPlacementRef = useRef(false);
  const connectPredicateInputRef = useRef<HTMLInputElement | null>(null);
  const connectPredicateSelectRef = useRef<HTMLSelectElement | null>(null);
  const generationRef = useRef(0);
  const graphRequestGenerationRef = useRef(0);
  const mountedOwnerRef = useRef<number | null>(null);
  const pendingActionRef = useRef<"confirm" | "edit" | null>(null);
  const componentScope = `${mode}:${stateScopeId ?? "default"}`;
  const componentScopeRef = useRef(componentScope);
  const stateScopeIdRef = useRef(stateScopeId);
  stateScopeIdRef.current = stateScopeId;

  useLayoutEffect(() => {
    if (componentScopeRef.current === componentScope) return;
    componentScopeRef.current = componentScope;
    mountedOwnerRef.current = null;
    generationRef.current += 1;
    graphRequestGenerationRef.current += 1;
    graphRef.current = null;
    setGraph(null);
    setLoading(true);
    setRefreshing(false);
    draftRef.current = EMPTY_DRAFT;
    setDraft(EMPTY_DRAFT);
    setDraftReadyWorldId(null);
    pendingRef.current = null;
    setPendingOperationState(null);
    pendingPhaseRef.current = "prepare";
    setPendingPhaseState("prepare");
    setPendingStatus("none");
    setPendingErrorCode(null);
    stalePrepareRejectionRef.current = false;
    setCustomPredicateMode(false);
    pendingActionRef.current = null;
    setReviewSummary(null);
    placementIntentRef.current = null;
    setPlacementIntent(null);
    setLayout({ worldId: "", positions: {}, revision: 0 });
    setCreatedNodeReveal(null);
    pendingCreatedFocusRef.current = null;
    setSelectedNodeId(null);
    setInspectionHistory([]);
    setActivePanel(null);
    setStorageWarning(false);
    setNotice(null);
  }, [componentScope]);

  useLayoutEffect(() => {
    if (detailGraphRef.current === graph) return;
    detailGraphRef.current = graph;
    detailAbortRef.current?.abort();
    detailAbortRef.current = null;
    detailRequestGenerationRef.current += 1;
    selectedNodeIdRef.current = null;
    setSelectedNodeId(null);
    setInspectionHistory([]);
    setSelectedNodeDetail(null);
    setSelectedNodeDetailStatus("idle");
    setSelectedNodeDetailError(null);
    setFocusedNodeId(null);
    setViewFocusId(null);
    setNeighborhoodDepth(1);
    setObjectQuery("");
    setObjectPage(0);
    setCameraFocusRequest(undefined);
    cameraFocusRequestIdRef.current += 1;
    setCameraFocusResetRequest({requestId: cameraFocusRequestIdRef.current, fitView: viewFocusId !== null});
    selectionClearRequestIdRef.current += 1;
    setClearSelectionRequest(selectionClearRequestIdRef.current);
    setActivePanel((current) => current === "details" ? null : current);
    setCreatedNodeReveal((current) => current && graph?.world_id === current.worldId
      && nodesById.has(current.nodeId) ? current : null);
    const createdFocus = pendingCreatedFocusRef.current;
    pendingCreatedFocusRef.current = null;
    if (embedded && graph && createdFocus?.graph === graph) {
      setCreatedNodeReveal({ nodeId: createdFocus.nodeId, worldId: graph.world_id });
      cameraFocusRequestIdRef.current += 1;
      setCameraFocusRequest({ nodeId: createdFocus.nodeId as LocalObjectId, requestId: cameraFocusRequestIdRef.current, worldId: graph.world_id, selectNode: true });
    }
  }, [graph, embedded, nodesById]);

  const handleCanvasSelectionChange = useCallback((nodeId: LocalObjectId | null) => {
    const previous = selectedNodeIdRef.current;
    if (nodeId && previous && previous !== nodeId) setInspectionHistory((history) => [...history, previous].slice(-30));
    selectedNodeIdRef.current = nodeId;
    setSelectedNodeId(nodeId);
    setActivePanel((current) => nodeId ? "details" : current === "details" ? null : current);
  }, []);

  const handleCanvasFocusChange = useCallback((nodeId: LocalObjectId | null) => {
    setFocusedNodeId(nodeId);
    if (nodeId === null) setCameraFocusRequest(undefined);
  }, []);

  const requestCameraFocus = useCallback((nodeId: string | null) => {
    if (!graph) return;
    setViewFocusId(nodeId as LocalObjectId | null);
    setNeighborhoodDepth(1);
    cameraFocusRequestIdRef.current += 1;
    setCameraFocusRequest({ nodeId: nodeId as LocalObjectId | null, requestId: cameraFocusRequestIdRef.current, worldId: graph.world_id, selectNode: true });
  }, [graph]);

  const closeSelectedDetails = useCallback(() => {
    if (focusedNodeId || cameraFocusRequest?.nodeId) requestCameraFocus(null);
    const previousSelection = selectedNodeIdRef.current;
    selectedNodeIdRef.current = null;
    setSelectedNodeId(null);
    setInspectionHistory([]);
    setSelectedNodeDetail(null);
    setSelectedNodeDetailStatus("idle");
    setSelectedNodeDetailError(null);
    setActivePanel((current) => current === "details" ? null : current);
    selectionClearRequestIdRef.current += 1;
    setClearSelectionRequest(selectionClearRequestIdRef.current);
    queueMicrotask(() => {
      const canvas = document.getElementById("loaded-native-graph-canvas");
      const nodes = canvas?.querySelectorAll<HTMLElement>("[data-node-id]");
      const selected = previousSelection && nodes
        ? [...nodes].find((node) => node.dataset.nodeId === previousSelection)
        : null;
      (selected ?? canvas)?.focus();
    });
  }, [cameraFocusRequest?.nodeId, focusedNodeId, requestCameraFocus]);

  useEffect(() => {
    if (!embedded || activePanel !== "details" || pendingOperation || !selectedNodeId) return;
    const closeDetailsOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape" || event.defaultPrevented) return;
      const current = placementIntentRef.current;
      if (current && current.operation_id === null && !pendingRef.current) {
        event.preventDefault();
        event.stopPropagation();
        cancelCanvasPlacement();
      } else if (!pendingRef.current && selectedNodeIdRef.current) {
        event.preventDefault();
        event.stopPropagation();
        closeSelectedDetails();
      }
    };
    window.addEventListener("keydown", closeDetailsOnEscape);
    return () => window.removeEventListener("keydown", closeDetailsOnEscape);
  }, [activePanel, closeSelectedDetails, embedded, pendingOperation, selectedNodeId]);

  const handleEmbeddedPanelChange = useCallback((panel: EmbeddedPanel) => {
    if (panel !== "details" && (focusedNodeId || cameraFocusRequest?.nodeId)) requestCameraFocus(null);
    setActivePanel(panel);
  }, [cameraFocusRequest?.nodeId, focusedNodeId, requestCameraFocus]);

  useEffect(() => {
    detailAbortRef.current?.abort();
    detailAbortRef.current = null;
    detailRequestGenerationRef.current += 1;
    setSelectedNodeDetail(null);
    setSelectedNodeDetailError(null);
    if (!embedded || mode !== "managed" || !graph || !selectedNodeId
      || selectedNodeIdRef.current !== selectedNodeId || graphRef.current !== graph) {
      setSelectedNodeDetailStatus("idle");
      return;
    }
    if (!api.inspectNode) {
      setSelectedNodeDetailStatus("unavailable");
      setSelectedNodeDetailError("Native record inspection is not available for this graph connection.");
      return;
    }
    const snapshot = graph;
    const selectedId = selectedNodeId;
    const controller = new AbortController();
    const requestGeneration = detailRequestGenerationRef.current;
    detailAbortRef.current = controller;
    setSelectedNodeDetailStatus("loading");
    void api.inspectNode(snapshot, selectedId, controller.signal).then((detail) => {
      if (controller.signal.aborted || requestGeneration !== detailRequestGenerationRef.current
        || selectedNodeIdRef.current !== selectedId || graphRef.current !== snapshot
        || graphRef.current.world_id !== snapshot.world_id || graphRef.current.revision_id !== snapshot.revision_id) return;
      if (detail.schema !== "dmb_native_graph_entity_v1" || detail.scope.revision_id !== snapshot.revision_id
        || detail.scope.native_world_id !== snapshot.world_id
        || detail.scope.scope_mode !== "world" || detail.scope.campaign_id !== null
        || !detail.scope.managed_world_id || !Number.isSafeInteger(detail.scope.binding_version) || detail.scope.binding_version < 1
        || !snapshot.nodes.some((node) => node.id === selectedId)) {
        throw new Error("The detail response did not match the selected object in this loaded World revision.");
      }
      setSelectedNodeDetail(detail);
      setSelectedNodeDetailStatus("ready");
    }).catch((error: unknown) => {
      if (controller.signal.aborted || requestGeneration !== detailRequestGenerationRef.current
        || selectedNodeIdRef.current !== selectedId || graphRef.current !== snapshot) return;
      setSelectedNodeDetailStatus("error");
      setSelectedNodeDetailError(describeError(error));
    });
    return () => {
      controller.abort();
      if (detailAbortRef.current === controller) detailAbortRef.current = null;
    };
  }, [api, embedded, graph, mode, selectedNodeId]);

  useEffect(() => {
    if (!embedded || pendingOperation) return;
    if (activePanel === "create") createNameInputRef.current?.focus();
    else if (activePanel === "connect") (connectPredicateInputRef.current ?? connectPredicateSelectRef.current)?.focus();
  }, [activePanel, customPredicateMode, embedded, pendingOperation]);

  useEffect(() => {
    if (!focusCreateInputAfterPlacementRef.current || !embedded || pendingOperation || !placementIntent) return;
    focusCreateInputAfterPlacementRef.current = false;
    createNameInputRef.current?.focus();
  }, [activePanel, embedded, pendingOperation, placementIntent]);

  function ownsMount(owner: number | null): owner is number {
    return owner !== null && mountedOwnerRef.current === owner;
  }

  function ownsOperation(owner: number | null, operationId: string): boolean {
    return ownsMount(owner) && pendingRef.current?.operation_id === operationId;
  }

  function installReadGraph(nextGraph: NativeGraph, requestGeneration: number, owner: number | null): boolean {
    if (!ownsMount(owner) || requestGeneration !== graphRequestGenerationRef.current) return false;
    graphRef.current = nextGraph;
    setGraph(nextGraph);
    setNotice(null);
    return true;
  }

  const setDraftAndPersist = useCallback((next: DemoFormDraft, worldId = graph?.world_id) => {
    draftRef.current = next;
    setDraft(next);
    if (!worldId || draftReadyWorldId !== worldId) return;
    setStorageWarning(!safeWriteDraft(worldId, next, pendingRef.current, "prepare", undefined, stateScopeId));
  }, [draftReadyWorldId, graph?.world_id, stateScopeId]);

  const setPendingOperation = useCallback((operation: PendingNativeOperation | null, phase: "prepare" | "confirm" = "prepare") => {
    pendingRef.current = operation;
    stalePrepareRejectionRef.current = false;
    pendingPhaseRef.current = phase;
    setPendingPhaseState(phase);
    setPendingOperationState(operation);
  }, []);

  const setPendingPhase = useCallback((phase: "prepare" | "confirm") => {
    pendingPhaseRef.current = phase;
    setPendingPhaseState(phase);
  }, []);

  const installServerGraph = useCallback((nextGraph: NativeGraph) => {
    // A confirmed server readback is newer authority than any earlier GET still in flight.
    graphRequestGenerationRef.current += 1;
    graphRef.current = nextGraph;
    setGraph(nextGraph);
    setNotice(null);
  }, []);

  const recoverOperation = useCallback(async (operation: PendingNativeOperation, priorErrorCode: string | null = null, owner: number | null = mountedOwnerRef.current) => {
    if (!ownsOperation(owner, operation.operation_id)) return;
    setPendingStatus("checking");
    try {
      const lookup = await api.readOperation(operation.operation_id);
      if (!ownsOperation(owner, operation.operation_id)) return;
      await applyOperationLookup(lookup, operation, priorErrorCode, owner);
    } catch (error) {
      if (!ownsOperation(owner, operation.operation_id)) return;
      setPendingStatus("unknown");
      setPendingErrorCode(priorErrorCode ?? asApiError(error)?.code ?? null);
      setNotice({ kind: "warning", text: `The operation status could not be verified. Keep this draft and use the same operation ID: ${describeError(error)}` });
    }
  // Function declarations below are hoisted so the single recovery path can be shared by mount and buttons.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api]);

  function applyCreatedNodePlacement(operation: PendingNativeOperation, committedGraph: NativeGraph, placement: StoredPlacementIntent | null, createdNodeId: string | null): string | null {
    if (operation.kind !== "create_object" || !placement || placement.operation_id !== operation.operation_id) return null;
    if (placement.kind !== operation.object_kind) return "The object was saved, but its type no longer matches the requested canvas placement. Its position was left unchanged.";
    if (placement.base_revision_id !== operation.expected_revision_id) return "The object was saved, but the placement belongs to a different graph revision. Its position was left unchanged.";
    if (committedGraph.world_id !== graphRef.current?.world_id) return "The object was saved, but the verified readback is for a different graph. Its requested canvas position was not applied.";
    if (!createdNodeId) return "DungeonMind confirmed the object, but did not return its exact new node ID. The requested canvas position was not applied.";
    const created = committedGraph.nodes.find((node) => node.id === createdNodeId);
    if (!created) return "DungeonMind returned the new node ID, but this readback does not include it. The requested position was discarded; refresh the graph and arrange the node manually if it appears.";
    if (created.kind !== operation.object_kind) return `DungeonMind returned the exact new node ID, but its graph type is ${created.kind}, not ${operation.object_kind}. Its requested position was not applied.`;
    const currentScopeId = stateScopeIdRef.current;
    const positions = readLayout(committedGraph.world_id, currentScopeId);
    const nextPositions = { ...positions, [createdNodeId]: placement.position };
    const nextLayout: LayoutState = {
      worldId: committedGraph.world_id,
      positions: nextPositions,
      revision: layoutRef.current.worldId === committedGraph.world_id ? layoutRef.current.revision + 1 : 1,
    };
    setLayout(nextLayout);
    if (!writeLayout(committedGraph.world_id, nextPositions, currentScopeId)) {
      setStorageWarning(true);
      return "DungeonMind saved the object. This browser could not save its requested canvas position, so drag it into place manually.";
    }
    setStorageWarning(false);
    return null;
  }

  async function clearRecoveredOperation(message: string, owner: number | null = mountedOwnerRef.current, completedOperation?: PendingNativeOperation, committedGraph?: NativeGraph, applyPlacement = true, createdNodeId: string | null = null) {
    if (!ownsMount(owner) || completedOperation && pendingRef.current?.operation_id !== completedOperation.operation_id) return;
    const currentGraph = graphRef.current;
    if (embedded && applyPlacement && completedOperation?.kind === "create_object" && committedGraph
      && committedGraph === currentGraph && createdNodeId
      && committedGraph.nodes.some((node) => node.id === createdNodeId && node.kind === completedOperation.object_kind)) {
      pendingCreatedFocusRef.current = { nodeId: createdNodeId, graph: committedGraph };
    }
    let currentDraft = draftRef.current;
    const currentScopeId = stateScopeIdRef.current;
    const savedPlacement = placementIntentRef.current
      ?? (currentGraph ? safeReadDraft(currentGraph.world_id, currentScopeId)?.placement ?? null : null);
    const placementBelongsToOperation = Boolean(completedOperation && savedPlacement?.operation_id === completedOperation.operation_id);
    const placementNotice = completedOperation && placementBelongsToOperation && !applyPlacement
      ? "The existing object is shown in DungeonMind; its canvas position was left unchanged."
      : completedOperation && committedGraph && placementBelongsToOperation
      ? applyCreatedNodePlacement(completedOperation, committedGraph, savedPlacement, createdNodeId)
      : null;
    if (completedOperation?.kind === "create_object"
      && currentDraft.objectName.trim() === completedOperation.name
      && currentDraft.objectKind === completedOperation.object_kind) {
      currentDraft = { ...currentDraft, objectName: "" };
    } else if (completedOperation?.kind === "connect"
      && currentDraft.sourceId === completedOperation.source_id
      && currentDraft.targetId === completedOperation.target_id
      && currentDraft.predicate.trim() === completedOperation.predicate) {
      currentDraft = { ...currentDraft, sourceId: "", targetId: "", predicate: "" };
    }
    if (currentGraph) {
      const cleared = safeWriteDraft(currentGraph.world_id, currentDraft, null, "prepare", placementBelongsToOperation ? null : savedPlacement, currentScopeId);
      setStorageWarning(!cleared || Boolean(placementNotice?.includes("could not save its requested canvas position")));
    }
    if (placementBelongsToOperation) {
      placementIntentRef.current = null;
      setPlacementIntent(null);
    }
    draftRef.current = currentDraft;
    setDraft(currentDraft);
    setPendingOperation(null);
    setPendingStatus("none");
    setPendingErrorCode(null);
    setReviewSummary(null);
    setNotice(placementNotice ? { kind: "warning", text: `${message} ${placementNotice}` } : { kind: "success", text: message });
  }

  async function applyOperationLookup(lookup: OperationLookupResult, operation: PendingNativeOperation, priorErrorCode: string | null = null, owner: number | null = mountedOwnerRef.current) {
    if (!ownsOperation(owner, operation.operation_id)) return;
    if (lookup.status === "prepared") {
      setPendingStatus("prepared");
      setPendingErrorCode(null);
      setReviewSummary(lookup.review?.summary ?? null);
      setNotice(lookup.review?.summary
        ? { kind: "info", text: "A prepared review was recovered. Objects and relationships are not published until you confirm; source evidence may already be saved for recovery." }
        : { kind: "warning", text: "DungeonMind reports a prepared operation, but its review details are unavailable. Retry the same preparation to recover the review before confirming." });
      return;
    }
    if (lookup.status === "not_found") {
      setPendingStatus("not_found");
      setPendingErrorCode(priorErrorCode);
      setReviewSummary(null);
      setNotice(pendingPhaseRef.current === "confirm"
        ? { kind: "error", text: "DungeonMind has no operation record after the confirmation attempt. Recovery is unavailable; keep this ID and draft, and check for an exact outcome later. Do not replay prepare or start a new review." }
        : priorErrorCode === "stale_revision" && stalePrepareRejectionRef.current
          ? { kind: "warning", text: "DungeonMind rejected this prepare as stale_revision, and the exact operation ID has no record. Refreshing and starting a new review is now safe." }
          : { kind: "warning", text: "DungeonMind has no operation record yet. The exact draft and operation ID are preserved; a missing record alone does not prove the request cannot still arrive. Check status or retry the same ID; do not start a new review." });
      return;
    }
    if (lookup.status === "rejected") {
      setPendingStatus("rejected");
      setPendingErrorCode(lookup.code);
      setReviewSummary(null);
      setNotice({ kind: "error", text: `${lookup.error} Your form draft is preserved.` });
      return;
    }
    if (lookup.status === "committed") {
      let committedGraph = lookup.graph;
      if (!committedGraph) {
        const graphRequest = ++graphRequestGenerationRef.current;
        committedGraph = await api.readGraph();
        if (!ownsOperation(owner, operation.operation_id)) return;
        if (graphRequest !== graphRequestGenerationRef.current) {
          setPendingStatus("unknown");
          setNotice({ kind: "warning", text: "DungeonMind reports this operation committed, but the graph readback was superseded. Check the exact operation again before continuing." });
          return;
        }
      }
      if (!ownsOperation(owner, operation.operation_id)) return;
      installServerGraph(committedGraph);
      await clearRecoveredOperation(`${operationName(operation)} is committed in DungeonMind. The current graph has been read back from the server.`, owner, operation, committedGraph, true, createdNodeIdFromResult(lookup));
      return;
    }
    if (lookup.recovery_action === "retry_prepare" && pendingPhaseRef.current === "prepare") {
      setPendingStatus("prepare_retry");
      setPendingErrorCode(null);
      setReviewSummary(null);
      setNotice({ kind: "warning", text: "DungeonMind verified that review preparation was interrupted before a complete review was saved. Retry the exact draft with the same operation ID. You will still review and confirm before publishing the graph change." });
      return;
    }
    setPendingStatus("unknown");
    setPendingErrorCode(priorErrorCode);
    setReviewSummary(null);
    setNotice({ kind: "warning", text: "DungeonMind recorded an uncertain outcome. Do not retry or replace this operation ID. Check its status again when the service is available." });
  }

  useEffect(() => {
    const owner = ++generationRef.current;
    mountedOwnerRef.current = owner;
    const graphRequest = ++graphRequestGenerationRef.current;
    setLoading(true);
      if (mode === "managed" && !stateScopeId) {
        setLoading(false);
        setNotice({ kind: "error", text: "This managed graph is missing its verified World scope. Reselect the World to continue safely." });
        return () => {
          if (mountedOwnerRef.current === owner) mountedOwnerRef.current = null;
        };
      }
    api.readGraph().then(async (loadedGraph) => {
      if (!installReadGraph(loadedGraph, graphRequest, owner)) return;
      const saved = readOnly ? null : safeReadDraft(loadedGraph.world_id, stateScopeId);
      const restoredDraft = saved?.draft ?? EMPTY_DRAFT;
      draftRef.current = restoredDraft;
      setDraft(restoredDraft);
      setCustomPredicateMode(Boolean(loadedGraph.capabilities.allows_custom_predicates && restoredDraft.predicate
        && !loadedGraph.capabilities.allowed_predicates?.includes(restoredDraft.predicate)));
      setDraftReadyWorldId(readOnly ? null : loadedGraph.world_id);
      placementIntentRef.current = saved?.placement ?? null;
      setPlacementIntent(saved?.placement ?? null);
      setPendingOperation(saved?.pending ?? null);
      pendingPhaseRef.current = saved?.pending_phase ?? "prepare";
      setPendingPhaseState(saved?.pending_phase ?? "prepare");
      pendingRef.current = saved?.pending ?? null;
      setLayout({
        worldId: loadedGraph.world_id,
        positions: readLayout(loadedGraph.world_id, stateScopeId),
        revision: 0,
      });
      setLoading(false);
      setStorageWarning(false);
      if (saved?.pending) await recoverOperation(saved.pending, null, owner);
    }).catch((error: unknown) => {
      if (!ownsMount(owner) || graphRequest !== graphRequestGenerationRef.current) return;
      setLoading(false);
      setNotice({ kind: "error", text: describeError(error) });
    });
    return () => {
      if (mountedOwnerRef.current === owner) mountedOwnerRef.current = null;
    };
  }, [api, componentScope, readOnly, recoverOperation, stateScopeId]);

  const refreshGraph = useCallback(async () => {
    const owner = mountedOwnerRef.current;
    if (!ownsMount(owner) || refreshing || pendingRef.current) return;
    const graphRequest = ++graphRequestGenerationRef.current;
    setRefreshing(true);
    try {
      const nextGraph = await api.readGraph();
      if (!ownsMount(owner) || pendingRef.current) return;
      if (!installReadGraph(nextGraph, graphRequest, owner)) return;
      if (nextGraph.world_id !== layout.worldId) {
        const positions = readLayout(nextGraph.world_id, stateScopeId);
        setLayout({ worldId: nextGraph.world_id, positions, revision: 0 });
        setDraftReadyWorldId(readOnly ? null : nextGraph.world_id);
        const saved = readOnly ? null : safeReadDraft(nextGraph.world_id, stateScopeId);
        const nextDraft = saved?.draft ?? EMPTY_DRAFT;
        draftRef.current = nextDraft;
        setDraft(nextDraft);
        setCustomPredicateMode(Boolean(nextGraph.capabilities.allows_custom_predicates && nextDraft.predicate
          && !nextGraph.capabilities.allowed_predicates?.includes(nextDraft.predicate)));
        placementIntentRef.current = saved?.placement ?? null;
        setPlacementIntent(saved?.placement ?? null);
        setPendingOperation(saved?.pending ?? null);
        pendingPhaseRef.current = saved?.pending_phase ?? "prepare";
        setPendingPhaseState(saved?.pending_phase ?? "prepare");
        pendingRef.current = saved?.pending ?? null;
        setPendingStatus(saved?.pending ? "checking" : "none");
        if (saved?.pending) await recoverOperation(saved.pending, null, owner);
      }
      if (!ownsMount(owner)) return;
      setNotice({ kind: "success", text: "Latest graph revision loaded from DungeonMind. Your current form draft is preserved." });
    } catch (error) {
      if (!ownsMount(owner) || graphRequest !== graphRequestGenerationRef.current) return;
      setNotice({ kind: "error", text: `The latest graph could not be loaded. Your draft is unchanged: ${describeError(error)}` });
    } finally {
      if (ownsMount(owner)) setRefreshing(false);
    }
  }, [api, installServerGraph, layout, readOnly, recoverOperation, refreshing, setPendingOperation, setPendingPhase, stateScopeId]);

  function updateDraft(patch: Partial<DemoFormDraft>) {
    setDraftAndPersist({ ...draftRef.current, ...patch });
  }

  function updateCreateKind(kind: NativeObjectKind) {
    const currentPlacement = placementIntentRef.current;
    if (!currentPlacement) {
      updateDraft({ objectKind: kind });
      return;
    }
    const nextDraft = { ...draftRef.current, objectKind: kind };
    const nextPlacement = { ...currentPlacement, kind };
    draftRef.current = nextDraft;
    setDraft(nextDraft);
    placementIntentRef.current = nextPlacement;
    setPlacementIntent(nextPlacement);
    if (!graph || draftReadyWorldId !== graph.world_id) return;
    setStorageWarning(!safeWriteDraft(graph.world_id, nextDraft, pendingRef.current, pendingPhaseRef.current, nextPlacement, stateScopeId));
  }

  async function dispatchPrepare(operation: PendingNativeOperation) {
    const owner = mountedOwnerRef.current;
    if (!ownsMount(owner) || pendingRef.current) return;
    setPendingOperation(operation, "prepare");
    setReviewSummary(null);
    setPendingErrorCode(null);
    const currentPlacement = placementIntentRef.current;
    const operationPlacement = operation.kind === "create_object"
      ? graph && currentPlacement?.kind === operation.object_kind ? {
          ...currentPlacement,
          operation_id: operation.operation_id,
          base_revision_id: operation.expected_revision_id,
          created_node_id: null,
        } : null
      : currentPlacement;
    placementIntentRef.current = operationPlacement;
    setPlacementIntent(operationPlacement);
    if (!graph || !safeWriteDraft(graph.world_id, draftRef.current, operation, "prepare", operationPlacement, stateScopeId)) {
      setPendingStatus("not_sent");
      setStorageWarning(true);
      setNotice({ kind: "error", text: "This browser could not save the recovery draft, so the request was not sent. Keep the page open and try again after browser storage is available." });
      return;
    }
    setStorageWarning(false);
    setPendingStatus("preparing");
    setNotice({ kind: "info", text: "Preparing a review in DungeonMind. Objects and relationships are not published until you confirm; source evidence may be saved for recovery." });
    try {
      const result = await api.prepare(operation);
      if (!ownsOperation(owner, operation.operation_id)) return;
      await applyPrepareResult(result, operation, owner);
    } catch (error) {
      if (!ownsOperation(owner, operation.operation_id)) return;
      const apiError = asApiError(error);
      setPendingErrorCode(apiError?.code ?? null);
      setPendingStatus("unknown");
      stalePrepareRejectionRef.current = apiError?.status === 409 && apiError.code === "stale_revision";
      setNotice({ kind: "warning", text: `The prepare response was not verified. The same operation ID is retained; checking its server record now. ${describeError(error)}` });
      await recoverOperation(operation, apiError?.code ?? null, owner);
    }
  }

  async function applyPrepareResult(result: PrepareResult, operation: PendingNativeOperation, owner: number | null = mountedOwnerRef.current) {
    if (!ownsOperation(owner, operation.operation_id)) return;
    if (result.status === "already_exists") {
      installServerGraph(result.graph);
      await clearRecoveredOperation(`${result.message} The latest graph was read from DungeonMind.`, owner, operation, result.graph, false);
      return;
    }
    setPendingStatus("prepared");
    setPendingErrorCode(null);
    setReviewSummary(result.review.summary);
    setNotice({ kind: "info", text: `${operationName(operation)} is prepared. Review the server summary, then confirm to publish it.` });
  }

  async function submitCreate(event: FormEvent) {
    event.preventDefault();
    if (!graph || pendingRef.current || !graph.capabilities.create || !isNativeKindSupported(graph, draft.objectKind)) return;
    const name = draft.objectName.trim();
    if (!name) return;
    if (exceedsNativeNameByteLimit(name)) {
      setNotice({ kind: "warning", text: `Names must use ${MAX_NATIVE_NAME_UTF8_BYTES} UTF-8 bytes or fewer. Your draft is still editable.` });
      return;
    }
    if (embedded) setActivePanel(null);
    await dispatchPrepare({
      operation_id: crypto.randomUUID(),
      expected_revision_id: graph.revision_id,
      kind: "create_object",
      name,
      object_kind: draft.objectKind,
    });
  }

  async function submitConnect(event: FormEvent) {
    event.preventDefault();
    if (!graph || pendingRef.current || !canConnectGraph(graph)) return;
    if (!nodesById.has(draft.sourceId) || !nodesById.has(draft.targetId)) return;
    const predicate = draft.predicate.trim();
    if (!predicate || !isPredicateAllowed(graph, predicate)) return;
    if (embedded) setActivePanel(null);
    await dispatchPrepare({
      operation_id: crypto.randomUUID(),
      expected_revision_id: graph.revision_id,
      kind: "connect",
      source_id: draft.sourceId,
      target_id: draft.targetId,
      predicate,
    });
  }

  async function retrySamePrepare() {
    const operation = pendingRef.current;
    if (!operation || pendingPhase !== "prepare" || (pendingStatus !== "not_found" && pendingStatus !== "not_sent" && pendingStatus !== "prepare_retry")
      || pendingStatus === "not_found" && stalePrepareRejectionRef.current) return;
    // The existing ID is already pending, so retry its exact request without allocating or replacing it.
    const owner = mountedOwnerRef.current;
    if (!ownsOperation(owner, operation.operation_id)) return;
    setReviewSummary(null);
    if (!graph || !safeWriteDraft(graph.world_id, draftRef.current, operation, "prepare", undefined, stateScopeId)) {
      setPendingStatus("not_sent");
      setStorageWarning(true);
      setNotice({ kind: "error", text: "This browser still cannot save the recovery draft, so the request was not sent." });
      return;
    }
    setStorageWarning(false);
    stalePrepareRejectionRef.current = false;
    setPendingStatus("preparing");
    setNotice({ kind: "info", text: "Retrying the exact prepared input with the same operation ID. No replacement ID was created." });
    try {
      const result = await api.prepare(operation);
      if (ownsOperation(owner, operation.operation_id)) await applyPrepareResult(result, operation, owner);
    } catch (error) {
      if (!ownsOperation(owner, operation.operation_id)) return;
      const code = asApiError(error)?.code ?? null;
      setPendingErrorCode(code);
      setPendingStatus("unknown");
      const apiError = asApiError(error);
      stalePrepareRejectionRef.current = apiError?.status === 409 && apiError.code === "stale_revision";
      setNotice({ kind: "warning", text: `The retry response was not verified. The same operation ID remains saved. ${describeError(error)}` });
      await recoverOperation(operation, code, owner);
    }
  }

  async function checkPendingStatus() {
    const operation = pendingRef.current;
    const owner = mountedOwnerRef.current;
    if (!operation || pendingStatus === "checking" || pendingStatus === "preparing" || !ownsOperation(owner, operation.operation_id)) return;
    await recoverOperation(operation, pendingErrorCode, owner);
  }

  async function confirmPrepared() {
    const operation = pendingRef.current;
    const owner = mountedOwnerRef.current;
    if (!operation || pendingStatus !== "prepared" || !reviewSummary || !ownsOperation(owner, operation.operation_id) || pendingActionRef.current !== null) return;
    pendingActionRef.current = "confirm";
    const currentGraph = graphRef.current;
    if (!currentGraph || !safeWriteDraft(currentGraph.world_id, draftRef.current, operation, "confirm", undefined, stateScopeId)) {
      setStorageWarning(true);
      setNotice({ kind: "error", text: "This browser could not save the confirmation recovery step, so confirmation was not sent." });
      pendingActionRef.current = null;
      return;
    }
    setStorageWarning(false);
    setPendingPhase("confirm");
    setPendingStatus("checking");
    setNotice({ kind: "info", text: "Confirming the reviewed operation in DungeonMind…" });
    try {
      const result = await api.confirm(operation.operation_id);
      if (!ownsOperation(owner, operation.operation_id)) return;
      if (result.status === "committed") {
        installServerGraph(result.graph);
        await clearRecoveredOperation(`${operationName(operation)} is committed. The graph below is the server readback.`, owner, operation, result.graph, true, createdNodeIdFromResult(result));
      } else if (result.status === "rejected") {
        setPendingStatus("rejected");
        setPendingErrorCode(result.code);
        setReviewSummary(null);
        setNotice({ kind: "error", text: `${result.error} Your form draft is preserved.` });
      } else {
        setPendingStatus("unknown");
        setPendingErrorCode(null);
        setReviewSummary(null);
        setNotice({ kind: "warning", text: `${result.message} The outcome is recorded as uncertain. Do not retry or replace this operation ID; check its status again.` });
      }
    } catch (error) {
      if (!ownsOperation(owner, operation.operation_id)) return;
      const code = asApiError(error)?.code ?? null;
      setPendingErrorCode(code);
      setNotice({ kind: "warning", text: `The confirmation response was not verified. The operation stays attached to the same ID; checking its server record now. ${describeError(error)}` });
      await recoverOperation(operation, code, owner);
    } finally {
      if (pendingActionRef.current === "confirm") pendingActionRef.current = null;
    }
  }

  async function setAsidePreparedForEditing() {
    const operation = pendingRef.current;
    const owner = mountedOwnerRef.current;
    if (!operation || pendingStatus !== "prepared" || pendingPhase !== "prepare" || pendingPhaseRef.current !== "prepare"
      || !ownsOperation(owner, operation.operation_id) || pendingActionRef.current !== null) return;
    pendingActionRef.current = "edit";
    setPendingStatus("checking");
    setNotice({ kind: "info", text: "Refreshing the latest graph before releasing this tab's prepared review…" });
    try {
      const before = await api.readOperation(operation.operation_id);
      if (!ownsOperation(owner, operation.operation_id)) return;
      if (before.status !== "prepared") {
        await applyOperationLookup(before, operation, null, owner);
        return;
      }
      const graphRequest = ++graphRequestGenerationRef.current;
      const latestGraph = await api.readGraph();
      if (!ownsOperation(owner, operation.operation_id)) return;
      if (graphRequest !== graphRequestGenerationRef.current) {
        setPendingStatus("prepared");
        setNotice({ kind: "warning", text: "A newer graph read is in progress. This prepared review remains attached; try Edit draft again." });
        return;
      }
      if (!installReadGraph(latestGraph, graphRequest, owner)) return;
      const after = await api.readOperation(operation.operation_id);
      if (!ownsOperation(owner, operation.operation_id)) return;
      if (after.status !== "prepared") {
        await applyOperationLookup(after, operation, null, owner);
        return;
      }
      if (!safeClearDraft(latestGraph.world_id, draftRef.current, stateScopeId)) {
        setPendingStatus("prepared");
        setStorageWarning(true);
        setReviewSummary(after.review?.summary ?? reviewSummary);
        setNotice({ kind: "error", text: "The latest graph was refreshed, but this browser could not release the local review pointer. Nothing was deleted on the server; the prepared review stays attached." });
        return;
      }
      setStorageWarning(false);
      setPendingOperation(null);
      setPendingStatus("none");
      setPendingErrorCode(null);
      setReviewSummary(null);
      setNotice({ kind: "success", text: `Draft unlocked after refreshing the latest graph. Server review and source evidence remain; this only set aside the local pointer and did not delete or cancel them. Retained operation ID: ${operation.operation_id}` });
    } catch (error) {
      if (!ownsOperation(owner, operation.operation_id)) return;
      setPendingStatus("prepared");
      setNotice({ kind: "error", text: `Could not safely release the draft. The prepared review remains available: ${describeError(error)}` });
    } finally {
      if (pendingActionRef.current === "edit") pendingActionRef.current = null;
    }
  }

  async function startFreshAfterStaleReview() {
    const operation = pendingRef.current;
    const owner = mountedOwnerRef.current;
    const definitiveStalePrepare = pendingPhaseRef.current === "prepare" && pendingErrorCode === "stale_revision"
      && (stalePrepareRejectionRef.current || pendingStatus === "rejected");
    const canStartFresh = pendingStatus === "rejected" && pendingErrorCode === "stale_revision"
      || pendingStatus === "not_found" && definitiveStalePrepare;
    if (!operation || !canStartFresh || !ownsOperation(owner, operation.operation_id)) return;
    setPendingStatus("checking");
    setNotice({ kind: "info", text: "Verifying that the old operation is safe to leave before refreshing the graph…" });
    try {
      const lookup = await api.readOperation(operation.operation_id);
      if (!ownsOperation(owner, operation.operation_id)) return;
      const stillSafeToStartFresh = lookup.status === "rejected" && lookup.code === "stale_revision"
        || lookup.status === "not_found" && definitiveStalePrepare;
      if (!stillSafeToStartFresh) {
        await applyOperationLookup(lookup, operation, pendingErrorCode, owner);
        return;
      }
      const graphRequest = ++graphRequestGenerationRef.current;
      const freshGraph = await api.readGraph();
      if (!ownsOperation(owner, operation.operation_id)) return;
      if (graphRequest !== graphRequestGenerationRef.current) {
        setPendingStatus("unknown");
        setNotice({ kind: "warning", text: "A newer graph read is already in progress. The stale review ID is still preserved; check it again before starting a fresh review." });
        return;
      }
      if (!installReadGraph(freshGraph, graphRequest, owner)) return;
      if (freshGraph.world_id !== layout.worldId) {
        setLayout({ worldId: freshGraph.world_id, positions: readLayout(freshGraph.world_id, stateScopeId), revision: 0 });
      }
      const cleared = safeClearDraft(freshGraph.world_id, draftRef.current, stateScopeId);
      setStorageWarning(!cleared);
      setPendingOperation(null);
      setPendingStatus("none");
      setPendingErrorCode(null);
      setReviewSummary(null);
      setNotice({ kind: "success", text: "The old review has a definitive safe outcome and the latest DungeonMind graph is loaded. Your form draft remains; prepare again to create a new review ID." });
    } catch (error) {
      if (!ownsOperation(owner, operation.operation_id)) return;
      setPendingStatus("unknown");
      setNotice({ kind: "error", text: `Could not safely start a fresh review. The original ID and form draft remain: ${describeError(error)}` });
    }
  }

  const canvasSnapshot = useMemo(() => graph ? toCanvasSnapshot(graph) : null, [graph]);
  const record = useMemo(
    () => graph && canvasSnapshot ? toCanvasRecord(graph, canvasSnapshot, layout) : null,
    [graph, canvasSnapshot, layout],
  );
  const connectionOptions = useMemo(() => graph?.nodes.map((node) => {
    const { displayName, displayKind } = nativeGraphPresentation(node);
    return { id: node.id, label: `${displayName} · ${displayKind}` };
  }) ?? [], [graph?.nodes]);
  const searchNodes = graph?.nodes;
  const objectSearchIndex = useMemo(() => searchNodes?.map((node) => {
    const presentation = nativeGraphPresentation(node);
    return {
      node,
      text: `${node.name} ${node.kind} ${node.id} ${presentation.displayName} ${presentation.displayKind} ${presentation.recordedNames.join(" ")}`.toLocaleLowerCase(),
    };
  }) ?? [], [searchNodes]);
  const matchingObjects = useMemo(() => {
    const query = objectQuery.trim().toLocaleLowerCase();
    if (!query) return searchNodes ?? [];
    return objectSearchIndex.filter(({ text }) => text.includes(query)).map(({ node }) => node);
  }, [objectQuery, objectSearchIndex, searchNodes]);
  const searchPageSize = 20;
  const lastObjectPage = Math.max(0, Math.ceil(matchingObjects.length / searchPageSize) - 1);
  const currentObjectPage = Math.min(objectPage, lastObjectPage);
  const visibleSearchObjects = matchingObjects.slice(currentObjectPage * searchPageSize, (currentObjectPage + 1) * searchPageSize);
  const limitations = graph ? detailLimitations(graph) : [];

  const saveLayout = useCallback(async (_record: LocalWorldRecord, changedPositions: Readonly<Record<string, { readonly x: number; readonly y: number }>>): Promise<WriteLayoutResult> => {
    if (!graph || !canvasSnapshot) return { status: "missing" };
    const current = layout.worldId === graph.world_id ? layout : { worldId: graph.world_id, positions: {}, revision: 0 };
    const mergedPositions: Record<string, { x: number; y: number }> = { ...current.positions };
    for (const [id, position] of Object.entries(changedPositions)) {
      if (!nodesById.has(id) || !Number.isFinite(position.x) || !Number.isFinite(position.y)) continue;
      mergedPositions[id] = {
        x: Math.max(0, Math.min(MAX_COORDINATE, position.x)),
        y: Math.max(0, Math.min(MAX_COORDINATE, position.y)),
      };
    }
    const nextLayout: LayoutState = { worldId: graph.world_id, positions: mergedPositions, revision: current.revision + 1 };
    setLayout(nextLayout);
    const nextRecord = toCanvasRecord(graph, canvasSnapshot, nextLayout);
    if (!writeLayout(graph.world_id, mergedPositions, stateScopeId)) {
      return { status: "error", message: "This arrangement is visible for now, but the browser could not save its presentation-only layout." };
    }
    return { status: "written", record: nextRecord };
  }, [graph, canvasSnapshot, nodesById, layout, stateScopeId]);

  const creationKinds = graph?.capabilities.create
    ? graph.capabilities.object_kinds.map((kind) => ({ kind, label: kind.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()) }))
    : [];

  function handleCanvasCreateRequest(intent: { readonly kind: string; readonly position: { readonly x: number; readonly y: number } }) {
    if (!graph || pendingRef.current || !graph.capabilities.create || !isNativeKindSupported(graph, intent.kind as NativeObjectKind)
      || !Number.isFinite(intent.position.x) || !Number.isFinite(intent.position.y)) return;
    const kind = intent.kind as NativeObjectKind;
    const nextDraft = { ...draftRef.current, objectKind: kind };
    setDraftAndPersist(nextDraft);
    const nextIntent: StoredPlacementIntent = {
      kind,
      position: { x: Math.max(0, Math.min(MAX_COORDINATE, intent.position.x)), y: Math.max(0, Math.min(MAX_COORDINATE, intent.position.y)) },
      operation_id: null,
      base_revision_id: graph.revision_id,
      created_node_id: null,
    };
    placementIntentRef.current = nextIntent;
    setPlacementIntent(nextIntent);
    focusCreateInputAfterPlacementRef.current = true;
    setStorageWarning(!safeWriteDraft(graph.world_id, nextDraft, pendingRef.current, pendingPhaseRef.current, nextIntent, stateScopeId));
    setActivePanel("create");
    setNotice({ kind: "info", text: `Choose a name for the ${kind}. Its requested spot is saved locally and will be applied only after DungeonMind confirms the new node.` });
  }

  function cancelCanvasPlacement(): boolean {
    const current = placementIntentRef.current;
    if (!graph || pendingRef.current || !current || current.operation_id !== null) return false;
    if (!safeWriteDraft(graph.world_id, draftRef.current, null, "prepare", null, stateScopeId)) {
      setStorageWarning(true);
      setNotice({ kind: "error", text: "This browser could not save the placement cancellation. The placement and object draft remain available in this tab." });
      return true;
    }
    placementIntentRef.current = null;
    setPlacementIntent(null);
    setStorageWarning(false);
    setNotice({ kind: "info", text: "Placement canceled. Your name and type draft are still saved, and nothing was sent to DungeonMind." });
    createNameInputRef.current?.focus();
    return true;
  }

  function handleConnectRequest(intent: { readonly sourceId: string; readonly targetId: string }) {
    if (!graph || pendingRef.current || !canConnectGraph(graph)
      || !nodesById.has(intent.sourceId)
      || !nodesById.has(intent.targetId)) return;
    updateDraft({ sourceId: intent.sourceId, targetId: intent.targetId });
    setActivePanel("connect");
    setNotice({ kind: "info", text: "Add a relationship label, then review it with DungeonMind before confirming." });
  }

  const exportSnapshot = useCallback(() => {
    if (!graph) return;
    const positions = readLayout(graph.world_id, stateScopeId);
    const snapshot = {
      format: "dungeonmind-index-graph-snapshot-v1",
      kind: "read-only-revision-pinned-snapshot",
      note: "This is a read-only graph snapshot with browser presentation layout. It is not a restorable World backup.",
      exported_at: new Date().toISOString(),
      world_id: graph.world_id,
      revision_id: graph.revision_id,
      graph_sha256: graph.graph_sha256,
      graph,
      presentation: { layout_revision: layout.worldId === graph.world_id ? layout.revision : 0, positions },
      ...(mode === "managed" ? { selected_world_title: worldTitle ?? null } : {}),
    };
    try {
      const url = URL.createObjectURL(new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json" }));
      const anchor = document.createElement("a");
      const slug = (mode === "managed" ? worldTitle ?? "world" : "playground").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "graph";
      anchor.href = url;
      anchor.download = `dungeonmind-${slug}-${graph.revision_id}.json`;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
      setNotice({ kind: "success", text: `Read-only snapshot of revision ${graph.revision_id} downloaded with this browser's canvas layout. It is not a restorable World backup.` });
    } catch (error) {
      setNotice({ kind: "error", text: `The snapshot could not be downloaded: ${describeError(error)}` });
    }
  }, [graph, layout, mode, stateScopeId, worldTitle]);
  const refreshFromContext = useCallback(() => { void refreshGraph(); }, [refreshGraph]);

  const searchContent = <div className="native-demo-context__search">
              <label htmlFor={searchId}>Search loaded objects</label>
              <input autoFocus id={searchId} type="search" value={objectQuery} placeholder="Name, type or ID"
                disabled={Boolean(pendingOperation)} onChange={(event) => { setObjectQuery(event.target.value); setObjectPage(0); }} />
              <p>{matchingObjects.length} matching objects. Search includes every loaded object.</p>
              <ul aria-label="Matching graph objects">{visibleSearchObjects.map((node) => <li key={node.id}>
                <button type="button" data-graph-search-result disabled={Boolean(pendingOperation)} aria-label={`Explore ${nativeGraphPresentation(node).displayName} (${node.id})`}
                  onClick={() => { handleCanvasSelectionChange(node.id as LocalObjectId); requestCameraFocus(node.id); }}>
                  {nativeGraphPresentation(node).displayName} <small>{nativeGraphPresentation(node).displayKind} · {node.id}</small>
                </button>
              </li>)}</ul>
              {!matchingObjects.length ? <p>No loaded objects match this search.</p> : null}
              {lastObjectPage > 0 ? <div role="group" aria-label="Object search pages">
                <button type="button" disabled={currentObjectPage === 0 || Boolean(pendingOperation)} onClick={() => setObjectPage(currentObjectPage - 1)}>Previous objects</button>
                <span>Page {currentObjectPage + 1} of {lastObjectPage + 1}</span>
                <button type="button" disabled={currentObjectPage === lastObjectPage || Boolean(pendingOperation)} onClick={() => setObjectPage(currentObjectPage + 1)}>Next objects</button>
              </div> : null}
  </div>;
  const neighborhoodContent = viewFocusId && graph ? <div className="world-graph-canvas__neighborhood" role="group" aria-label="Neighborhood controls">
              <span>Neighborhood: {neighborhoodDepth} {neighborhoodDepth === 1 ? "step" : "steps"} from {nodesById.get(viewFocusId)?.name}. Focused view limit: 512 objects. The overview shows connected objects; objects without listed connections remain available in search or with the reveal control.</span>
              <button type="button" disabled={neighborhoodDepth >= graph.nodes.length || Boolean(pendingOperation)} onClick={() => setNeighborhoodDepth((depth) => depth + 1)}>Expand neighborhood</button>
              <button type="button" disabled={Boolean(pendingOperation)} onClick={() => requestCameraFocus(null)}>Show overview</button>
            </div> : null;

  const embeddedContext = embedded ? (
    <NativeGraphDemoContext
      graph={graph}
      activePanel={activePanel}
      mode={mode}
      worldTitle={worldTitle}
      loading={loading}
      refreshing={refreshing}
      hasPendingOperation={Boolean(pendingOperation)}
      pendingStatus={pendingStatus}
      hasPlacementIntent={Boolean(placementIntent)}
      onPanelChange={handleEmbeddedPanelChange}
      onRefresh={refreshFromContext}
      onExport={exportSnapshot}
      canRefresh={mode !== "managed" || Boolean(stateScopeId)}
      searchContent={searchContent}
      neighborhoodContent={neighborhoodContent}
      onControlsHost={setCanvasControlsHost}
    />
  ) : null;


  if (loading && !graph) {
    return <main className={`native-demo-shell${embedded ? " native-demo-shell--embedded" : ""}`}>
      {embeddedContext}
      <h1 className={embedded ? "native-demo-sr-only" : undefined}>{embedded ? mode === "managed" ? `${worldTitle?.trim() || "Selected World"} graph` : "Buddy graph playground" : ""}</h1>
      <div className="native-demo-loading" role="status">Opening the DungeonMind graph…</div>
    </main>;
  }

  if (!graph) {
    return (
      <main className={`native-demo-shell${embedded ? " native-demo-shell--embedded" : ""}`}>
        {embeddedContext}
        <section className="native-demo-error-card" aria-labelledby="native-demo-title">
          <p className="native-demo-kicker">{embedded ? mode === "managed" ? `BUDDY · ${worldTitle?.trim() || "SELECTED WORLD"}` : "BUDDY · GRAPH PLAYGROUND" : "DUNGEONMIND · NATIVE GRAPH"}</p>
          <h1 id="native-demo-title">The graph is not available yet</h1>
          <p role="alert">{notice?.text ?? (embedded ? mode === "managed" ? `Buddy could not open ${worldTitle?.trim() || "the selected World"} right now.` : "Buddy could not open the private playground right now." : "The isolated DungeonMind service has not returned a graph.")}</p>
          {mode !== "managed" || stateScopeId ? <button className="native-demo-button native-demo-button--light" type="button" onClick={() => void refreshGraph()} disabled={refreshing}>
            {refreshing ? "Checking…" : "Try again"}
          </button> : null}
        </section>
      </main>
    );
  }

  const completeness = graphCompleteness(graph);
  const partialReadSummary = completeness?.status === "partial"
    ? `Partial native graph read: ${completeness.omitted_entities} entities omitted, ${completeness.unexamined_entities} unexamined; ${completeness.omitted_assertions} assertions omitted, ${completeness.unexamined_assertions} unexamined.`
    : null;
  const graphNavigationHelp = embedded
    ? "Drag anywhere to pan. Choose Move nodes to fix a bubble in place; unpinned bubbles settle around it."
    : "Drag the background to pan and nodes to arrange them.";
  const graphZoomHelp = "Use the graph controls to zoom or fit. With the graph focused, +/− zoom and 0 fits; hold Ctrl and scroll over the graph to zoom around the pointer.";
  const graphHelpText = pendingOperation
    ? "The graph is paused while this review is resolved. Use the review controls above."
    : graph.capabilities.create && canConnectGraph(graph)
      ? `${graphNavigationHelp} Use Place node to choose where a new node should go, or drag a connector dot to another node to draft a relationship. ${graphZoomHelp}`
      : graph.capabilities.create
        ? `${graphNavigationHelp} Use Place node to choose where a new node should go. ${graphZoomHelp}`
        : canConnectGraph(graph)
          ? `${graphNavigationHelp} Drag a connector dot to another node to draft a relationship. ${graphZoomHelp}`
          : `${graphNavigationHelp} ${graphZoomHelp}`;

  const nameExceedsByteLimit = exceedsNativeNameByteLimit(draft.objectName);
  const createPanel = (
    <section className="native-demo-action-card" aria-labelledby="native-demo-create-title">
      <p className="native-demo-eyebrow">AUTHOR A NODE</p>
      <h2 id="native-demo-create-title">Add an object</h2>
      <p className="native-demo-copy">{placementIntent
        ? `This ${placementIntent.kind} will be placed where you clicked after DungeonMind confirms the new node.`
        : "Create a typed object. Review every change before it is saved by DungeonMind."}</p>
      {embedded && placementIntent?.operation_id === null && !pendingOperation ? (
        <button className="native-demo-button native-demo-button--quiet" type="button" aria-keyshortcuts="Escape" onClick={cancelCanvasPlacement}>Cancel placement</button>
      ) : null}
      <form className="native-demo-form" onSubmit={(event) => void submitCreate(event)}>
        <label htmlFor="native-demo-name">Name</label>
        <input ref={createNameInputRef} id="native-demo-name" name="name" autoComplete="off" maxLength={120} required value={draft.objectName}
          onChange={(event) => updateDraft({ objectName: event.target.value })} disabled={Boolean(pendingOperation)} placeholder="e.g. Mara" />
        {nameExceedsByteLimit
          ? <p className="native-demo-limitation" role="alert">Names must use {MAX_NATIVE_NAME_UTF8_BYTES} UTF-8 bytes or fewer. Shorten this draft to prepare a review.</p>
          : null}
        <label htmlFor="native-demo-kind">Type</label>
        <select id="native-demo-kind" name="kind" value={draft.objectKind}
          onChange={(event) => updateCreateKind(event.target.value as NativeObjectKind)} disabled={Boolean(pendingOperation)}>
          {graph.capabilities.object_kinds.map((kind) => <option value={kind} key={kind}>{kind.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase())}</option>)}
          {!isNativeKindSupported(graph, "event") ? <option value="event" disabled>Event · unavailable</option> : null}
        </select>
        {graph.capabilities.create && !graph.capabilities.object_kinds.length ? <p className="native-demo-limitation">This graph profile has no supported object types to create.</p> : null}
        {!isNativeKindSupported(graph, "event") ? <p className="native-demo-limitation">{embedded ? "Event typing is not supported by this DungeonMind profile." : "Event typing is not supported by this DungeonMind profile yet. This demo is incomplete until the native profile accepts it."}</p> : null}
        <button className="native-demo-button native-demo-button--gold" type="submit" disabled={!graph.capabilities.create || !isNativeKindSupported(graph, draft.objectKind) || nameExceedsByteLimit || Boolean(pendingOperation) || pendingStatus === "not_sent"}>
          {pendingOperation?.kind === "create_object" ? "Review is in progress" : "Prepare object"}
        </button>
      </form>
    </section>
  );

  const finitePredicateOptions = usesFinitePredicateOptions(graph);
  const allowedPredicates = graph.capabilities.allowed_predicates ?? [];
  const allowsCustomPredicates = graph.capabilities.allows_custom_predicates === true;
  const showPredicateOptions = finitePredicateOptions || allowsCustomPredicates && allowedPredicates.length > 0;
  const showCustomPredicateInput = allowsCustomPredicates
    ? allowedPredicates.length === 0 || customPredicateMode
    : !finitePredicateOptions;
  const predicateInputPattern = PREDICATE_PATTERN_HTML;
  const connectPanel = (
    <section className="native-demo-action-card" aria-labelledby="native-demo-connect-title">
      <p className="native-demo-eyebrow">AUTHOR A DIRECTED EDGE</p>
      <h2 id="native-demo-connect-title">Connect two objects</h2>
      <p className="native-demo-copy">{finitePredicateOptions
        ? "Choose the source, destination, and an approved relationship label. DungeonMind checks the current graph revision."
        : allowsCustomPredicates
          ? "Choose a registered label or enter a plain custom label. DungeonMind checks the current graph revision."
          : "Choose the source, destination, and predicate. DungeonMind checks the current graph revision."}</p>
      <form className="native-demo-form" onSubmit={(event) => void submitConnect(event)}>
        <label htmlFor="native-demo-source">From</label>
        <select id="native-demo-source" value={draft.sourceId} required disabled={Boolean(pendingOperation)}
          onChange={(event) => updateDraft({ sourceId: event.target.value })}>
          <option value="">Choose an object</option>
          {connectionOptions.map(({ id, label }) => <option key={id} value={id}>{label}</option>)}
        </select>
        <label htmlFor="native-demo-target">To</label>
        <select id="native-demo-target" value={draft.targetId} required disabled={Boolean(pendingOperation)}
          onChange={(event) => updateDraft({ targetId: event.target.value })}>
          <option value="">Choose an object</option>
          {connectionOptions.map(({ id, label }) => <option key={id} value={id}>{label}</option>)}
        </select>
        <label htmlFor={showPredicateOptions ? "native-demo-predicate-choice" : "native-demo-predicate"}>Relationship</label>
        {showPredicateOptions ? (
          <select ref={connectPredicateSelectRef} id="native-demo-predicate-choice" name="predicate_choice" required
            value={customPredicateMode && allowsCustomPredicates ? CUSTOM_PREDICATE_OPTION : draft.predicate}
            disabled={Boolean(pendingOperation)}
            onChange={(event) => {
              if (event.target.value === CUSTOM_PREDICATE_OPTION) {
                setCustomPredicateMode(true);
                if (allowedPredicates.includes(draft.predicate)) updateDraft({ predicate: "" });
              } else {
                setCustomPredicateMode(false);
                updateDraft({ predicate: event.target.value });
              }
            }}>
            <option value="">Choose an approved label</option>
            {allowedPredicates.map((predicate) => <option value={predicate} key={predicate}>{predicate}</option>)}
            {allowsCustomPredicates ? <option value={CUSTOM_PREDICATE_OPTION}>Enter a custom label…</option> : null}
          </select>
        ) : null}
        {showCustomPredicateInput ? (
          <>
            {showPredicateOptions ? <label htmlFor="native-demo-predicate">Custom label</label> : null}
            <input ref={connectPredicateInputRef} id="native-demo-predicate" name="predicate" autoComplete="off" maxLength={64} required pattern={predicateInputPattern}
              title="Use lowercase letters, numbers, dots, underscores, or hyphens only. Example: works_at."
              onChange={(event) => { setCustomPredicateMode(true); updateDraft({ predicate: event.target.value }); }}
              value={draft.predicate} disabled={Boolean(pendingOperation)} placeholder="e.g. works_at" />
          </>
        ) : null}
        <p className="native-demo-predicate-help">{finitePredicateOptions
          ? allowedPredicates.length ? "Only labels approved by the selected World can be used." : "No approved relationship labels are available for this World."
          : allowsCustomPredicates ? "Choose a registered label or enter a plain lowercase custom label; DungeonMind stores custom labels in the approved namespace."
            : "Use lowercase letters, numbers, dots, underscores, and hyphens only."}</p>
        <button className="native-demo-button native-demo-button--gold" type="submit" disabled={!canConnectGraph(graph) || graph.nodes.length < 1 || Boolean(pendingOperation) || pendingStatus === "not_sent"}>
          {pendingOperation?.kind === "connect" ? "Review is in progress" : "Prepare connection"}
        </button>
      </form>
    </section>
  );

  const reviewPanel = pendingOperation ? (
    <section className="native-demo-review-card" aria-labelledby="native-demo-review-title">
      <p className="native-demo-eyebrow">EXPLICIT REVIEW</p>
      <h2 id="native-demo-review-title">{operationName(pendingOperation)}</h2>
      {reviewSummary ? <p className="native-demo-review-summary">{reviewSummary}</p> : <p className="native-demo-copy">The saved form draft and stable operation ID are being reconciled with DungeonMind.</p>}
      <p className="native-demo-operation-id">Operation <code>{pendingOperation.operation_id}</code></p>
      {pendingStatus === "prepared" && reviewSummary ? (
        <>
          <button className="native-demo-button native-demo-button--confirm" type="button" onClick={() => void confirmPrepared()}>Confirm in DungeonMind</button>
          {pendingPhase === "prepare" ? <button className="native-demo-button native-demo-button--quiet" type="button" onClick={() => void setAsidePreparedForEditing()}>Edit draft (keep review record)</button> : null}
        </>
      ) : null}
      {pendingStatus === "unknown" || pendingStatus === "prepare_retry" || pendingStatus === "not_sent" || pendingStatus === "not_found" || pendingStatus === "rejected" ? (
        <div className="native-demo-recovery-actions">
          {pendingStatus !== "not_sent" ? <button className="native-demo-button native-demo-button--light" type="button" onClick={() => void checkPendingStatus()}>Check status</button> : null}
          {(pendingStatus === "not_found" && pendingPhase === "prepare" && !stalePrepareRejectionRef.current || pendingStatus === "prepare_retry" && pendingPhase === "prepare" || pendingStatus === "not_sent") ? <button className="native-demo-button native-demo-button--quiet" type="button" onClick={() => void retrySamePrepare()}>Retry same operation ID</button> : null}
          {(pendingStatus === "rejected" && pendingErrorCode === "stale_revision" || pendingStatus === "not_found" && pendingPhase === "prepare" && pendingErrorCode === "stale_revision" && stalePrepareRejectionRef.current)
            ? <button className="native-demo-button native-demo-button--quiet" type="button" onClick={() => void startFreshAfterStaleReview()}>Refresh and start a fresh review</button> : null}
          {pendingStatus === "rejected" && pendingErrorCode !== "stale_revision" ? <button className="native-demo-button native-demo-button--quiet" type="button" onClick={() => void clearRecoveredOperation("The rejected operation is dismissed. Your form draft is still here; edit it and prepare a new review.")}>Dismiss rejected operation</button> : null}
        </div>
      ) : null}
      {pendingStatus === "checking" ? <p className="native-demo-checking" role="status">Checking the exact operation ID…</p> : null}
      {pendingStatus === "preparing" ? <p className="native-demo-checking" role="status">Waiting for DungeonMind to accept this exact request. Status checks stay unavailable until the response settles.</p> : null}
      <p className="native-demo-no-cancel">If the response was lost, this panel keeps the same ID. It will never create a replacement operation automatically. Setting aside a prepared review only releases this tab's pointer; it does not delete server-side source or review records.</p>
    </section>
  ) : null;

  const infoPanel = (
    <section className="native-demo-limits-card" aria-labelledby="native-demo-limits-title">
      <p className="native-demo-eyebrow">ABOUT THIS GRAPH</p>
      <h2 id="native-demo-limits-title">{mode === "managed" ? worldTitle?.trim() || "Selected World" : "A small, scoped playground"}</h2>
      <p className="native-demo-copy">{mode === "managed"
        ? "This is the selected World graph from DungeonMind. Semantic edits stay behind the native review and confirmation flow."
        : "This private synthetic graph is backed by DungeonMind. It does not edit or publish your account Worlds."}</p>
      <p className="native-demo-limit-detail">The arrangement is saved in this browser only.</p>
      <ul>
        <li className={graph.capabilities.create ? "is-available" : "is-unavailable"}>{graph.capabilities.create ? `Create ${graph.capabilities.object_kinds.map((kind) => kind.replace(/[_-]+/g, " ")).join(", ") || "supported native objects"}` : "Object creation is read-only here"}</li>
        <li className={canConnectGraph(graph) ? "is-available" : "is-unavailable"}>{!graph.capabilities.connect ? "Connections are read-only here" : !canConnectGraph(graph) ? "No approved relationship labels are available" : finitePredicateOptions ? `Connect using ${allowedPredicates.length} approved relationship label${allowedPredicates.length === 1 ? "" : "s"}` : allowsCustomPredicates ? "Use registered relationship labels or plain labels in DungeonMind’s approved custom namespace" : "Connect objects with a predicate"}</li>
        <li className="is-unavailable">Rename is unavailable</li>
        <li className="is-unavailable">Delete is unavailable</li>
      </ul>
      <p className="native-demo-copy">{graphHelpText}</p>
      <p className="native-demo-limit-detail">Rename and delete are not part of the native operation contract.</p>
      {completeness?.status === "partial" ? (
        <div className="native-demo-completeness native-demo-completeness--info" role="status">
          <strong>Partial native graph read</strong>
          <p>{partialReadSummary}</p>
          {completeness.reasons.length ? <ul>{completeness.reasons.map((reason) => <li key={reason}>{completenessReasonLabel(reason)}</li>)}</ul> : null}
        </div>
      ) : null}
      {limitations.map((limitation) => <p className="native-demo-limit-detail" key={limitation}>{limitation}</p>)}
      <p className="native-demo-limit-detail">Revision <code>{graph.revision_id}</code> · digest <code>{graph.graph_sha256.slice(0, 16)}…</code></p>
      {mode === "playground" ? <p className="native-demo-limit-detail">Saved for this browser session. Clearing cookies or session expiry loses the link to this graph.</p> : null}
      <p className="native-demo-limit-detail">Browser storage holds presentation layout and a tab-scoped recovery draft only; DungeonMind remains the semantic authority.</p>
    </section>
  );

  const selectedNode = selectedNodeId ? nodesById.get(selectedNodeId) ?? null : null;
  const selectedLabels = new Map(graph.nodes.map((node) => [node.id, compactNodeLabel(node)]));
  const selectedConnections = selectedNode ? graph.edges.filter((edge) => edge.source_id === selectedNode.id || edge.target_id === selectedNode.id) : [];
  const detailsPanel = selectedNode ? <NativeGraphNodeExplorer
    key={`${graph.world_id}:${graph.revision_id}:${selectedNode.id}`}
    node={selectedNode} revision={graph.revision_id} detail={selectedNodeDetail} labels={selectedLabels}
    mode={mode} status={selectedNodeDetailStatus} error={selectedNodeDetailError} connections={selectedConnections}
    entityOnly={entityOnlyDetails} partial={completeness?.status === "partial"} navigationDisabled={Boolean(pendingOperation)}
    headingRef={inspectorHeadingRef} onFocus={() => requestCameraFocus(selectedNode.id)}
    onExitFocus={focusedNodeId ? () => requestCameraFocus(null) : undefined} onClose={closeSelectedDetails}
    previousLabel={selectedLabels.get(inspectionHistory[inspectionHistory.length - 1]!)}
    onBack={inspectionHistory.length ? () => {
      const previous = inspectionHistory[inspectionHistory.length - 1];
      if (!previous || pendingOperation || !nodesById.has(previous)) return;
      focusInspectorRef.current = true;
      setInspectionHistory((history) => history.slice(0, -1));
      selectedNodeIdRef.current = previous;
      setSelectedNodeId(previous);
      requestCameraFocus(previous);
    } : undefined}
    onExplore={(nodeId) => {
      if (pendingOperation || !nodesById.has(nodeId)) return;
      focusInspectorRef.current = true;
      handleCanvasSelectionChange(nodeId as LocalObjectId);
      requestCameraFocus(nodeId);
    }}
  /> : null;


  return (
    <main className={`native-demo-shell${embedded ? " native-demo-shell--embedded" : ""}`}
      onKeyDown={(event) => {
        if (event.key !== "Escape") return;
        const current = placementIntentRef.current;
        if (current && current.operation_id === null && !pendingRef.current) {
          event.preventDefault();
          event.stopPropagation();
          cancelCanvasPlacement();
          return;
        }
        if (activePanel === "details" && selectedNodeIdRef.current && !pendingRef.current) {
          event.preventDefault();
          event.stopPropagation();
          closeSelectedDetails();
        }
      }}>
      {embeddedContext}
      {embedded ? <h1 className="native-demo-sr-only">{mode === "managed" ? `${worldTitle?.trim() || "Selected World"} graph` : "Buddy graph playground"}</h1> : null}
      <div className={`native-demo-layout${embedded ? " native-demo-layout--embedded" : ""}`}>
        {!embedded ? <header className="native-demo-header">
          <div className="native-demo-brand-mark" aria-hidden="true"><span>{embedded ? "B" : "DM"}</span></div>
          <div className="native-demo-heading">
            <p className="native-demo-kicker">{embedded ? "BUDDY · GRAPH PLAYGROUND" : "A SMALL, REAL GRAPH WORKSPACE"}</p>
            <h1>{embedded ? <>Buddy <span>graph playground</span></> : <>DungeonMind <span>native graph</span></>}</h1>
            <p>{embedded
              ? "Explore a private synthetic graph backed by DungeonMind. Review each change before it is confirmed."
              : "Explore the published World graph, then prepare and review a native change before confirming it."}</p>
          </div>
          <div className="native-demo-storage-pill"><span aria-hidden="true" /> {embedded ? "Private · DungeonMind" : "PostgreSQL · server-backed"}</div>
        </header> : null}

        {notice ? <div className={`native-demo-notice native-demo-notice--${notice.kind}`} role={notice.kind === "error" ? "alert" : "status"}>{notice.text}</div> : null}
        {storageWarning ? <div className="native-demo-storage-note" role="status">Browser storage is unavailable. Form drafts may not survive a page reload, and new requests will wait until a recovery draft can be saved.</div> : null}

        <div className={`native-demo-workspace${embedded ? ` native-demo-workspace--embedded${pendingOperation || activePanel ? " has-panel" : ""}` : ""}`}>
          <section className={`native-demo-graph-card${embedded ? " native-demo-graph-card--embedded" : ""}`} aria-labelledby="native-demo-graph-heading">
            {embedded ? (
              <h2 id="native-demo-graph-heading" className="native-demo-sr-only">DungeonMind graph</h2>
            ) : (
              <div className="native-demo-card-heading">
                <div>
                  <p className="native-demo-eyebrow">PUBLISHED WORLD</p>
                  <h2 id="native-demo-graph-heading">The living graph</h2>
                </div>
                <button className="native-demo-button native-demo-button--quiet" type="button" onClick={() => void refreshGraph()} disabled={refreshing || Boolean(pendingOperation)}>
                  <span aria-hidden="true">↻</span> {refreshing ? "Refreshing…" : "Refresh"}
                </button>
              </div>
            )}
            {record ? (
              <WorldGraphCanvas
                key={graph.world_id}
                canvasId={embedded ? "loaded-native-graph-canvas" : undefined}
                record={record}
                onMoveObjects={saveLayout}
                {...(embedded ? {
                  nodeShape: "circle" as const,
                  externalControls: true,
                  controlsHost: canvasControlsHost,
                  toolActions: !readOnly ? <>
                    <SurfaceContextAction disabled={!graph.capabilities.create || !graph.capabilities.object_kinds.length || Boolean(pendingOperation)} onClick={() => handleEmbeddedPanelChange(activePanel === "create" ? null : "create")}>Add object</SurfaceContextAction>
                    <SurfaceContextAction disabled={!canConnectGraph(graph) || Boolean(pendingOperation)} onClick={() => handleEmbeddedPanelChange(activePanel === "connect" ? null : "connect")}>Connect</SurfaceContextAction>
                  </> : undefined,
                  projectionOptions: { fullCorpus: true, maxNodes: 512, maxEdges: 1024, focusObjectId: viewFocusId, neighborhoodDepth },
                  creationKinds,
                  onCanvasCreateRequest: !readOnly && graph.capabilities.create ? handleCanvasCreateRequest : undefined,
                  onConnectRequest: !readOnly && canConnectGraph(graph) ? handleConnectRequest : undefined,
                  onSelectionChange: handleCanvasSelectionChange,
                  revealObjectId: createdNodeReveal?.worldId === graph.world_id ? createdNodeReveal.nodeId as LocalObjectId : null,
                  cameraFocusRequest: cameraFocusRequest?.worldId === graph.world_id ? cameraFocusRequest : undefined,
                  clearCameraFocusRequest: cameraFocusResetRequest,
                  clearSelectionRequest,
                  onCameraFocusChange: handleCanvasFocusChange,
                  interactionDisabled: Boolean(pendingOperation),
                  showSummaryCounts: false,
                  preserveCameraOnResize: true,
                } : {})}
              />
            ) : null}
            {!embedded ? <div className="native-demo-graph-meta">
              <span><strong>{graph.nodes.length}</strong> {completeness?.status === "partial" ? "listed objects" : "objects"}</span>
              <span><strong>{graph.edges.length}</strong> {completeness?.status === "partial" ? "listed relationships" : "relationships"}</span>
              {!embedded ? <span className="native-demo-meta-ellipsis" title={graph.revision_id}>Revision <code>{graph.revision_id}</code></span> : null}
            </div> : null}
            {!embedded && partialReadSummary ? <div className="native-demo-completeness" role="status"><strong>Partial native graph read</strong><span>{partialReadSummary}</span>{completeness?.reasons.map((reason) => <span key={reason}>{completenessReasonLabel(reason)}</span>)}</div> : null}
          </section>

          {embedded ? (
            pendingOperation ? (
              <aside className="native-demo-side-panel native-demo-side-panel--embedded" aria-label="Pending graph review">
                {reviewPanel}
              </aside>
            ) : activePanel && (activePanel !== "details" || selectedNode) ? (
              <aside className="native-demo-side-panel native-demo-side-panel--embedded" aria-label={activePanel === "info" ? "Graph information" : activePanel === "details" ? "Selected object details" : "Graph actions"}>
                {activePanel === "create" ? createPanel : activePanel === "connect" ? connectPanel : activePanel === "details" ? detailsPanel : infoPanel}
              </aside>
            ) : null
          ) : (
            <aside className="native-demo-side-panel" aria-label="Native graph actions">
              {createPanel}
              {connectPanel}
              {reviewPanel}
              <section className="native-demo-limits-card" aria-labelledby="native-demo-limits-title">
                <p className="native-demo-eyebrow">CURRENT PROFILE</p>
                <h2 id="native-demo-limits-title">What this demo can do</h2>
                <ul>
                  <li className={graph.capabilities.create ? "is-available" : "is-unavailable"}>Create supported native objects</li>
                  <li className={canConnectGraph(graph) ? "is-available" : "is-unavailable"}>{canConnectGraph(graph) ? "Connect objects with an approved relationship label" : "Connections are read-only here"}</li>
                  <li className="is-unavailable">Rename is unavailable</li>
                  <li className="is-unavailable">Delete is unavailable</li>
                </ul>
                <p className="native-demo-limit-detail">Rename and delete are not implemented by the native operation contract, so this demo does not imitate them with other assertions.</p>
                {limitations.map((limitation) => <p className="native-demo-limit-detail" key={limitation}>{limitation}</p>)}
              </section>
            </aside>
          )}
        </div>

        {!embedded ? <footer className="native-demo-footer">
          <span>{embedded ? "This private demo graph is separate from your existing Worlds." : "DungeonMind is the semantic authority for this graph."}</span>
          {embedded ? <span>This graph is saved by DungeonMind for this browser session. If the session expires or its cookie is cleared, this browser may lose its link to the graph.</span> : null}
          <span>Graph digest <code>{graph.graph_sha256.slice(0, 16)}…</code></span>
          <span>Browser storage holds only view layout and tab-scoped recoverable drafts.</span>
        </footer> : null}
      </div>
    </main>
  );
}
