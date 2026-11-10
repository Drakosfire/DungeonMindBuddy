import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
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
  type NativeGraphDemoApi,
  type NativeObjectKind,
  type NativePrepareRequest,
  type OperationLookupResult,
  type PrepareResult,
} from "./nativeGraphDemoApi";
import "./nativeGraphDemo.css";

const STORAGE_VERSION = 1;
const MAX_COORDINATE = 6000;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const PREDICATE_PATTERN = /^[a-z0-9][a-z0-9._-]*$/;
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
}

interface LayoutState {
  readonly worldId: string;
  readonly positions: Readonly<Record<string, { readonly x: number; readonly y: number }>>;
  readonly revision: number;
}

type PendingStatus = "none" | "not_sent" | "checking" | "not_found" | "rejected" | "unknown" | "prepared";
type NoticeKind = "success" | "info" | "warning" | "error";
interface Notice { readonly kind: NoticeKind; readonly text: string }

const EMPTY_DRAFT: DemoFormDraft = {
  objectName: "",
  objectKind: "person",
  sourceId: "",
  targetId: "",
  predicate: "",
};

function storageKey(kind: "layout" | "draft", worldId: string): string {
  return `dungeonmind-native-demo:${kind}:${encodeURIComponent(worldId)}`;
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
  };
}

function safeReadDraft(worldId: string): StoredDraftEnvelope | null {
  try {
    // sessionStorage is isolated per tab and survives reload/navigation in that tab.
    // A second tab cannot overwrite this tab's operation ID or recovery form.
    const raw = window.sessionStorage.getItem(storageKey("draft", worldId));
    return raw ? parseStoredDraft(JSON.parse(raw), worldId) : null;
  } catch {
    return null;
  }
}

function safeWriteDraft(worldId: string, draft: DemoFormDraft, pending: PendingNativeOperation | null, phase: "prepare" | "confirm" = "prepare"): boolean {
  try {
    const envelope: StoredDraftEnvelope = { version: STORAGE_VERSION, world_id: worldId, draft, pending, pending_phase: phase };
    window.sessionStorage.setItem(storageKey("draft", worldId), JSON.stringify(envelope));
    return true;
  } catch {
    return false;
  }
}

function safeClearDraft(worldId: string, draft: DemoFormDraft): boolean {
  return safeWriteDraft(worldId, draft, null);
}

function readLayout(worldId: string, allowedIds: ReadonlySet<string>): Readonly<Record<string, { readonly x: number; readonly y: number }>> {
  try {
    const raw = window.localStorage.getItem(storageKey("layout", worldId));
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    const positions: Record<string, { x: number; y: number }> = {};
    for (const [id, value] of Object.entries(parsed)) {
      if (!allowedIds.has(id) || !value || typeof value !== "object") continue;
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

function writeLayout(worldId: string, positions: Readonly<Record<string, { readonly x: number; readonly y: number }>>): boolean {
  try {
    window.localStorage.setItem(storageKey("layout", worldId), JSON.stringify(positions));
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
function toCanvasRecord(graph: NativeGraph, layout: LayoutState): LocalWorldRecord {
  const worldId = graph.world_id as LocalWorldId;
  return {
    snapshot: {
      worldId,
      title: "DungeonMind native graph",
      objects: graph.nodes.map((node) => ({
        id: node.id as LocalObjectId,
        name: node.name,
        kind: node.kind,
        properties: {},
      })),
      relationships: graph.edges.map((edge) => ({
        id: edge.id as LocalRelationshipId,
        fromObjectId: edge.source_id as LocalObjectId,
        toObjectId: edge.target_id as LocalObjectId,
        kind: edge.predicate,
        properties: {},
      })),
    },
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

function operationName(operation: PendingNativeOperation): string {
  return operation.kind === "create_object" ? `Create ${operation.object_kind}` : "Connect objects";
}

export interface NativeGraphDemoProps {
  readonly api?: NativeGraphDemoApi;
}

export function NativeGraphDemo({ api: providedApi }: NativeGraphDemoProps) {
  const api = useMemo(() => providedApi ?? createNativeGraphDemoApi(), [providedApi]);
  const [graph, setGraph] = useState<NativeGraph | null>(null);
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
  const [reviewSummary, setReviewSummary] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [layout, setLayout] = useState<LayoutState>({ worldId: "", positions: {}, revision: 0 });
  const [storageWarning, setStorageWarning] = useState(false);
  const generationRef = useRef(0);
  const graphRequestGenerationRef = useRef(0);
  const mountedOwnerRef = useRef<number | null>(null);
  const pendingActionRef = useRef<"confirm" | "edit" | null>(null);

  function ownsMount(owner: number | null): owner is number {
    return owner !== null && mountedOwnerRef.current === owner;
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
    setStorageWarning(!safeWriteDraft(worldId, next, pendingRef.current));
  }, [draftReadyWorldId, graph?.world_id]);

  const setPendingOperation = useCallback((operation: PendingNativeOperation | null, phase: "prepare" | "confirm" = "prepare") => {
    pendingRef.current = operation;
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
    if (!ownsMount(owner)) return;
    setPendingStatus("checking");
    try {
      const lookup = await api.readOperation(operation.operation_id);
      if (!ownsMount(owner)) return;
      await applyOperationLookup(lookup, operation, priorErrorCode, owner);
    } catch (error) {
      if (!ownsMount(owner)) return;
      setPendingStatus("unknown");
      setPendingErrorCode(priorErrorCode ?? asApiError(error)?.code ?? null);
      setNotice({ kind: "warning", text: `The operation status could not be verified. Keep this draft and use the same operation ID: ${describeError(error)}` });
    }
  // Function declarations below are hoisted so the single recovery path can be shared by mount and buttons.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api]);

  async function clearRecoveredOperation(message: string, owner: number | null = mountedOwnerRef.current, completedOperation?: PendingNativeOperation) {
    if (!ownsMount(owner)) return;
    const currentGraph = graphRef.current;
    let currentDraft = draftRef.current;
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
      const cleared = safeClearDraft(currentGraph.world_id, currentDraft);
      setStorageWarning(!cleared);
    }
    draftRef.current = currentDraft;
    setDraft(currentDraft);
    setPendingOperation(null);
    setPendingStatus("none");
    setPendingErrorCode(null);
    setReviewSummary(null);
    setNotice({ kind: "success", text: message });
  }

  async function applyOperationLookup(lookup: OperationLookupResult, operation: PendingNativeOperation, priorErrorCode: string | null = null, owner: number | null = mountedOwnerRef.current) {
    if (!ownsMount(owner)) return;
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
        : { kind: "warning", text: "DungeonMind has no operation record for this request. The exact draft and operation ID are preserved; an explicit retry may use this same ID and input." });
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
        if (!ownsMount(owner)) return;
        if (graphRequest !== graphRequestGenerationRef.current) {
          setPendingStatus("unknown");
          setNotice({ kind: "warning", text: "DungeonMind reports this operation committed, but the graph readback was superseded. Check the exact operation again before continuing." });
          return;
        }
      }
      if (!ownsMount(owner)) return;
      installServerGraph(committedGraph);
      await clearRecoveredOperation(`${operationName(operation)} is committed in DungeonMind. The current graph has been read back from the server.`, owner, operation);
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
    api.readGraph().then(async (loadedGraph) => {
      if (!installReadGraph(loadedGraph, graphRequest, owner)) return;
      const saved = safeReadDraft(loadedGraph.world_id);
      const restoredDraft = saved?.draft ?? EMPTY_DRAFT;
      draftRef.current = restoredDraft;
      setDraft(restoredDraft);
      setDraftReadyWorldId(loadedGraph.world_id);
      setPendingOperation(saved?.pending ?? null);
      pendingPhaseRef.current = saved?.pending_phase ?? "prepare";
      setPendingPhaseState(saved?.pending_phase ?? "prepare");
      pendingRef.current = saved?.pending ?? null;
      setLayout({
        worldId: loadedGraph.world_id,
        positions: readLayout(loadedGraph.world_id, new Set(loadedGraph.nodes.map((node) => node.id))),
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
  }, [api, recoverOperation]);

  async function refreshGraph() {
    const owner = mountedOwnerRef.current;
    if (!ownsMount(owner) || refreshing) return;
    const graphRequest = ++graphRequestGenerationRef.current;
    setRefreshing(true);
    try {
      const nextGraph = await api.readGraph();
      if (!installReadGraph(nextGraph, graphRequest, owner)) return;
      if (nextGraph.world_id !== layout.worldId) {
        const positions = readLayout(nextGraph.world_id, new Set(nextGraph.nodes.map((node) => node.id)));
        setLayout({ worldId: nextGraph.world_id, positions, revision: 0 });
        setDraftReadyWorldId(nextGraph.world_id);
        const saved = safeReadDraft(nextGraph.world_id);
        const nextDraft = saved?.draft ?? EMPTY_DRAFT;
        draftRef.current = nextDraft;
        setDraft(nextDraft);
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
  }

  function updateDraft(patch: Partial<DemoFormDraft>) {
    setDraftAndPersist({ ...draftRef.current, ...patch });
  }

  async function dispatchPrepare(operation: PendingNativeOperation) {
    const owner = mountedOwnerRef.current;
    if (!ownsMount(owner) || pendingRef.current) return;
    setPendingOperation(operation, "prepare");
    setReviewSummary(null);
    setPendingErrorCode(null);
    if (!graph || !safeWriteDraft(graph.world_id, draftRef.current, operation, "prepare")) {
      setPendingStatus("not_sent");
      setStorageWarning(true);
      setNotice({ kind: "error", text: "This browser could not save the recovery draft, so the request was not sent. Keep the page open and try again after browser storage is available." });
      return;
    }
    setStorageWarning(false);
    setPendingStatus("unknown");
    setNotice({ kind: "info", text: "Preparing a review in DungeonMind. Objects and relationships are not published until you confirm; source evidence may be saved for recovery." });
    try {
      const result = await api.prepare(operation);
      if (!ownsMount(owner)) return;
      await applyPrepareResult(result, operation, owner);
    } catch (error) {
      if (!ownsMount(owner)) return;
      const apiError = asApiError(error);
      setPendingErrorCode(apiError?.code ?? null);
      setPendingStatus("unknown");
      setNotice({ kind: "warning", text: `The prepare response was not verified. The same operation ID is retained; checking its server record now. ${describeError(error)}` });
      await recoverOperation(operation, apiError?.code ?? null, owner);
    }
  }

  async function applyPrepareResult(result: PrepareResult, operation: PendingNativeOperation, owner: number | null = mountedOwnerRef.current) {
    if (!ownsMount(owner)) return;
    if (result.status === "already_exists") {
      installServerGraph(result.graph);
      await clearRecoveredOperation(`${result.message} The latest graph was read from DungeonMind.`, owner);
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
    if (!graph || pendingRef.current || !graph.capabilities.connect) return;
    if (!graph.nodes.some((node) => node.id === draft.sourceId) || !graph.nodes.some((node) => node.id === draft.targetId)) return;
    const predicate = draft.predicate.trim();
    if (!predicate || !PREDICATE_PATTERN.test(predicate)) return;
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
    if (!operation || pendingPhase !== "prepare" || (pendingStatus !== "not_found" && pendingStatus !== "not_sent")) return;
    // The existing ID is already pending, so retry its exact request without allocating or replacing it.
    const owner = mountedOwnerRef.current;
    if (!ownsMount(owner)) return;
    setReviewSummary(null);
    if (!graph || !safeWriteDraft(graph.world_id, draftRef.current, operation, "prepare")) {
      setPendingStatus("not_sent");
      setStorageWarning(true);
      setNotice({ kind: "error", text: "This browser still cannot save the recovery draft, so the request was not sent." });
      return;
    }
    setStorageWarning(false);
    setPendingStatus("unknown");
    setNotice({ kind: "info", text: "Retrying the exact prepared input with the same operation ID. No replacement ID was created." });
    try {
      const result = await api.prepare(operation);
      if (ownsMount(owner)) await applyPrepareResult(result, operation, owner);
    } catch (error) {
      if (!ownsMount(owner)) return;
      const code = asApiError(error)?.code ?? null;
      setPendingErrorCode(code);
      setPendingStatus("unknown");
      setNotice({ kind: "warning", text: `The retry response was not verified. The same operation ID remains saved. ${describeError(error)}` });
      await recoverOperation(operation, code, owner);
    }
  }

  async function checkPendingStatus() {
    const operation = pendingRef.current;
    const owner = mountedOwnerRef.current;
    if (!operation || pendingStatus === "checking" || !ownsMount(owner)) return;
    await recoverOperation(operation, pendingErrorCode, owner);
  }

  async function confirmPrepared() {
    const operation = pendingRef.current;
    const owner = mountedOwnerRef.current;
    if (!operation || pendingStatus !== "prepared" || !reviewSummary || !ownsMount(owner) || pendingActionRef.current !== null) return;
    pendingActionRef.current = "confirm";
    const currentGraph = graphRef.current;
    if (!currentGraph || !safeWriteDraft(currentGraph.world_id, draftRef.current, operation, "confirm")) {
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
      if (!ownsMount(owner)) return;
      if (result.status === "committed") {
        installServerGraph(result.graph);
        await clearRecoveredOperation(`${operationName(operation)} is committed. The graph below is the server readback.`, owner, operation);
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
      if (!ownsMount(owner)) return;
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
      || !ownsMount(owner) || pendingActionRef.current !== null) return;
    pendingActionRef.current = "edit";
    setPendingStatus("checking");
    setNotice({ kind: "info", text: "Refreshing the latest graph before releasing this tab's prepared review…" });
    try {
      const before = await api.readOperation(operation.operation_id);
      if (!ownsMount(owner)) return;
      if (before.status !== "prepared") {
        await applyOperationLookup(before, operation, null, owner);
        return;
      }
      const graphRequest = ++graphRequestGenerationRef.current;
      const latestGraph = await api.readGraph();
      if (!ownsMount(owner)) return;
      if (graphRequest !== graphRequestGenerationRef.current) {
        setPendingStatus("prepared");
        setNotice({ kind: "warning", text: "A newer graph read is in progress. This prepared review remains attached; try Edit draft again." });
        return;
      }
      if (!installReadGraph(latestGraph, graphRequest, owner)) return;
      const after = await api.readOperation(operation.operation_id);
      if (!ownsMount(owner)) return;
      if (after.status !== "prepared") {
        await applyOperationLookup(after, operation, null, owner);
        return;
      }
      if (!safeClearDraft(latestGraph.world_id, draftRef.current)) {
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
      if (!ownsMount(owner)) return;
      setPendingStatus("prepared");
      setNotice({ kind: "error", text: `Could not safely release the draft. The prepared review remains available: ${describeError(error)}` });
    } finally {
      if (pendingActionRef.current === "edit") pendingActionRef.current = null;
    }
  }

  async function startFreshAfterStaleReview() {
    const operation = pendingRef.current;
    const owner = mountedOwnerRef.current;
    const canStartFresh = pendingStatus === "rejected" && pendingErrorCode === "stale_revision"
      || pendingStatus === "not_found" && pendingPhase === "prepare";
    if (!operation || !canStartFresh || !ownsMount(owner)) return;
    setPendingStatus("checking");
    setNotice({ kind: "info", text: "Verifying that the old operation is safe to leave before refreshing the graph…" });
    try {
      const lookup = await api.readOperation(operation.operation_id);
      if (!ownsMount(owner)) return;
      const stillSafeToStartFresh = lookup.status === "rejected" && lookup.code === "stale_revision"
        || lookup.status === "not_found" && pendingPhaseRef.current === "prepare";
      if (!stillSafeToStartFresh) {
        await applyOperationLookup(lookup, operation, pendingErrorCode, owner);
        return;
      }
      const graphRequest = ++graphRequestGenerationRef.current;
      const freshGraph = await api.readGraph();
      if (!ownsMount(owner)) return;
      if (graphRequest !== graphRequestGenerationRef.current) {
        setPendingStatus("unknown");
        setNotice({ kind: "warning", text: "A newer graph read is already in progress. The stale review ID is still preserved; check it again before starting a fresh review." });
        return;
      }
      if (!installReadGraph(freshGraph, graphRequest, owner)) return;
      if (freshGraph.world_id !== layout.worldId) {
        setLayout({ worldId: freshGraph.world_id, positions: readLayout(freshGraph.world_id, new Set(freshGraph.nodes.map((node) => node.id))), revision: 0 });
      }
      const cleared = safeClearDraft(freshGraph.world_id, draftRef.current);
      setStorageWarning(!cleared);
      setPendingOperation(null);
      setPendingStatus("none");
      setPendingErrorCode(null);
      setReviewSummary(null);
      setNotice({ kind: "success", text: "The old review has a definitive safe outcome and the latest DungeonMind graph is loaded. Your form draft remains; prepare again to create a new review ID." });
    } catch (error) {
      if (!ownsMount(owner)) return;
      setPendingStatus("unknown");
      setNotice({ kind: "error", text: `Could not safely start a fresh review. The original ID and form draft remain: ${describeError(error)}` });
    }
  }

  const record = graph ? toCanvasRecord(graph, layout) : null;
  const limitations = graph ? detailLimitations(graph) : [];

  const saveLayout = useCallback(async (_record: LocalWorldRecord, changedPositions: Readonly<Record<string, { readonly x: number; readonly y: number }>>): Promise<WriteLayoutResult> => {
    if (!graph) return { status: "missing" };
    const current = layout.worldId === graph.world_id ? layout : { worldId: graph.world_id, positions: {}, revision: 0 };
    const mergedPositions: Record<string, { x: number; y: number }> = { ...current.positions };
    const allowedIds = new Set(graph.nodes.map((node) => node.id));
    for (const [id, position] of Object.entries(changedPositions)) {
      if (!allowedIds.has(id) || !Number.isFinite(position.x) || !Number.isFinite(position.y)) continue;
      mergedPositions[id] = {
        x: Math.max(0, Math.min(MAX_COORDINATE, position.x)),
        y: Math.max(0, Math.min(MAX_COORDINATE, position.y)),
      };
    }
    const nextLayout: LayoutState = { worldId: graph.world_id, positions: mergedPositions, revision: current.revision + 1 };
    setLayout(nextLayout);
    const nextRecord = toCanvasRecord(graph, nextLayout);
    if (!writeLayout(graph.world_id, mergedPositions)) {
      return { status: "error", message: "This arrangement is visible for now, but the browser could not save its presentation-only layout." };
    }
    return { status: "written", record: nextRecord };
  }, [graph, layout]);

  if (loading && !graph) {
    return <main className="native-demo-shell"><div className="native-demo-loading" role="status">Opening the DungeonMind graph…</div></main>;
  }

  if (!graph) {
    return (
      <main className="native-demo-shell">
        <section className="native-demo-error-card" aria-labelledby="native-demo-title">
          <p className="native-demo-kicker">DUNGEONMIND · NATIVE GRAPH</p>
          <h1 id="native-demo-title">The graph is not available yet</h1>
          <p role="alert">{notice?.text ?? "The isolated DungeonMind service has not returned a graph."}</p>
          <button className="native-demo-button native-demo-button--light" type="button" onClick={() => void refreshGraph()} disabled={refreshing}>
            {refreshing ? "Checking…" : "Try again"}
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="native-demo-shell">
      <div className="native-demo-layout">
        <header className="native-demo-header">
          <div className="native-demo-brand-mark" aria-hidden="true"><span>DM</span></div>
          <div className="native-demo-heading">
            <p className="native-demo-kicker">A SMALL, REAL GRAPH WORKSPACE</p>
            <h1>DungeonMind <span>native graph</span></h1>
            <p>Explore the published World graph, then prepare and review a native change before confirming it.</p>
          </div>
          <div className="native-demo-storage-pill"><span aria-hidden="true" /> PostgreSQL · server-backed</div>
        </header>

        {notice ? <div className={`native-demo-notice native-demo-notice--${notice.kind}`} role={notice.kind === "error" ? "alert" : "status"}>{notice.text}</div> : null}
        {storageWarning ? <div className="native-demo-storage-note" role="status">Browser storage is unavailable. Form drafts may not survive a page reload, and new requests will wait until a recovery draft can be saved.</div> : null}

        <div className="native-demo-workspace">
          <section className="native-demo-graph-card" aria-labelledby="native-demo-graph-heading">
            <div className="native-demo-card-heading">
              <div>
                <p className="native-demo-eyebrow">PUBLISHED WORLD</p>
                <h2 id="native-demo-graph-heading">The living graph</h2>
              </div>
              <button className="native-demo-button native-demo-button--quiet" type="button" onClick={() => void refreshGraph()} disabled={refreshing}>
                <span aria-hidden="true">↻</span> {refreshing ? "Refreshing…" : "Refresh"}
              </button>
            </div>
            <div className="native-demo-canvas-note">Pan the canvas by dragging its background. Move a node to arrange this view. Those positions stay in this browser only. Semantic edits always come from DungeonMind.</div>
            {record ? <WorldGraphCanvas key={`${graph.world_id}:${graph.revision_id}`} record={record} onMoveObjects={saveLayout} /> : null}
            <div className="native-demo-graph-meta">
              <span><strong>{graph.nodes.length}</strong> objects</span>
              <span><strong>{graph.edges.length}</strong> relationships</span>
              <span className="native-demo-meta-ellipsis" title={graph.revision_id}>Revision <code>{graph.revision_id}</code></span>
            </div>
          </section>

          <aside className="native-demo-side-panel" aria-label="Native graph actions">
            <section className="native-demo-action-card" aria-labelledby="native-demo-create-title">
              <p className="native-demo-eyebrow">AUTHOR A NODE</p>
              <h2 id="native-demo-create-title">Add an object</h2>
              <p className="native-demo-copy">Create a typed DungeonMind object. It stays a draft until you review and confirm.</p>
              <form className="native-demo-form" onSubmit={(event) => void submitCreate(event)}>
                <label htmlFor="native-demo-name">Name</label>
                <input id="native-demo-name" name="name" autoComplete="off" maxLength={120} required value={draft.objectName}
                  onChange={(event) => updateDraft({ objectName: event.target.value })} disabled={Boolean(pendingOperation)} placeholder="e.g. Mara" />
                <label htmlFor="native-demo-kind">Type</label>
                <select id="native-demo-kind" name="kind" value={draft.objectKind}
                  onChange={(event) => updateDraft({ objectKind: event.target.value as NativeObjectKind })} disabled={Boolean(pendingOperation)}>
                  <option value="person">Person</option>
                  <option value="location">Location</option>
                  <option value="event" disabled={!isNativeKindSupported(graph, "event")}>Event{!isNativeKindSupported(graph, "event") ? " · unavailable" : ""}</option>
                </select>
                {!isNativeKindSupported(graph, "event") ? <p className="native-demo-limitation">Event typing is not supported by this DungeonMind profile yet. This demo is incomplete until the native profile accepts it.</p> : null}
                <button className="native-demo-button native-demo-button--gold" type="submit" disabled={!graph.capabilities.create || !isNativeKindSupported(graph, draft.objectKind) || Boolean(pendingOperation) || pendingStatus === "not_sent"}>
                  {pendingOperation?.kind === "create_object" ? "Review is in progress" : "Prepare object"}
                </button>
              </form>
            </section>

            <section className="native-demo-action-card" aria-labelledby="native-demo-connect-title">
              <p className="native-demo-eyebrow">AUTHOR A DIRECTED EDGE</p>
              <h2 id="native-demo-connect-title">Connect two objects</h2>
              <p className="native-demo-copy">Choose the source, destination, and predicate. DungeonMind checks the current graph revision.</p>
              <form className="native-demo-form" onSubmit={(event) => void submitConnect(event)}>
                <label htmlFor="native-demo-source">From</label>
                <select id="native-demo-source" value={draft.sourceId} required disabled={Boolean(pendingOperation)}
                  onChange={(event) => updateDraft({ sourceId: event.target.value })}>
                  <option value="">Choose an object</option>
                  {graph.nodes.map((node) => <option key={node.id} value={node.id}>{node.name} · {node.kind}</option>)}
                </select>
                <label htmlFor="native-demo-target">To</label>
                <select id="native-demo-target" value={draft.targetId} required disabled={Boolean(pendingOperation)}
                  onChange={(event) => updateDraft({ targetId: event.target.value })}>
                  <option value="">Choose an object</option>
                  {graph.nodes.map((node) => <option key={node.id} value={node.id}>{node.name} · {node.kind}</option>)}
                </select>
                <label htmlFor="native-demo-predicate">Relationship</label>
                <input id="native-demo-predicate" name="predicate" autoComplete="off" maxLength={64} required pattern="[a-z0-9][a-z0-9._-]*" title="Use lowercase letters, numbers, dots, underscores, or hyphens only. Example: works_at."
                  onChange={(event) => updateDraft({ predicate: event.target.value })} value={draft.predicate} disabled={Boolean(pendingOperation)} placeholder="e.g. works_at" />
                <p className="native-demo-predicate-help">Use lowercase letters, numbers, dots, underscores, and hyphens only.</p>
                <button className="native-demo-button native-demo-button--gold" type="submit" disabled={!graph.capabilities.connect || graph.nodes.length < 1 || Boolean(pendingOperation) || pendingStatus === "not_sent"}>
                  {pendingOperation?.kind === "connect" ? "Review is in progress" : "Prepare connection"}
                </button>
              </form>
            </section>

            {pendingOperation ? (
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
                {pendingStatus === "unknown" || pendingStatus === "not_sent" || pendingStatus === "not_found" || pendingStatus === "rejected" ? (
                  <div className="native-demo-recovery-actions">
                    {pendingStatus !== "not_sent" ? <button className="native-demo-button native-demo-button--light" type="button" onClick={() => void checkPendingStatus()}>Check status</button> : null}
                    {(pendingStatus === "not_found" && pendingPhase === "prepare" || pendingStatus === "not_sent") ? <button className="native-demo-button native-demo-button--quiet" type="button" onClick={() => void retrySamePrepare()}>Retry same operation ID</button> : null}
                    {(pendingStatus === "rejected" && pendingErrorCode === "stale_revision" || pendingStatus === "not_found" && pendingPhase === "prepare")
                      ? <button className="native-demo-button native-demo-button--quiet" type="button" onClick={() => void startFreshAfterStaleReview()}>Refresh and start a fresh review</button> : null}
                    {pendingStatus === "rejected" && pendingErrorCode !== "stale_revision" ? <button className="native-demo-button native-demo-button--quiet" type="button" onClick={() => void clearRecoveredOperation("The rejected operation is dismissed. Your form draft is still here; edit it and prepare a new review.")}>Dismiss rejected operation</button> : null}
                  </div>
                ) : null}
                {pendingStatus === "checking" ? <p className="native-demo-checking" role="status">Checking the exact operation ID…</p> : null}
                <p className="native-demo-no-cancel">If the response was lost, this panel keeps the same ID. It will never create a replacement operation automatically. Setting aside a prepared review only releases this tab's pointer; it does not delete server-side source or review records.</p>
              </section>
            ) : null}

            <section className="native-demo-limits-card" aria-labelledby="native-demo-limits-title">
              <p className="native-demo-eyebrow">CURRENT PROFILE</p>
              <h2 id="native-demo-limits-title">What this demo can do</h2>
              <ul>
                <li className={graph.capabilities.create ? "is-available" : "is-unavailable"}>Create supported native objects</li>
                <li className={graph.capabilities.connect ? "is-available" : "is-unavailable"}>Connect objects with a predicate</li>
                <li className="is-unavailable">Rename is unavailable</li>
                <li className="is-unavailable">Delete is unavailable</li>
              </ul>
              <p className="native-demo-limit-detail">Rename and delete are not implemented by the native operation contract, so this demo does not imitate them with other assertions.</p>
              {limitations.map((limitation) => <p className="native-demo-limit-detail" key={limitation}>{limitation}</p>)}
            </section>
          </aside>
        </div>

        <footer className="native-demo-footer">
          <span>DungeonMind is the semantic authority for this graph.</span>
          <span>Graph digest <code>{graph.graph_sha256.slice(0, 16)}…</code></span>
          <span>Browser storage holds only view layout and tab-scoped recoverable drafts.</span>
        </footer>
      </div>
    </main>
  );
}
