import { memo, useEffect, useId, useLayoutEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent, type PointerEvent, type CSSProperties, type RefObject } from "react";
import { createPortal } from "react-dom";
import type {
  CommitSemanticResult,
  LocalObjectId,
  LocalWorldRecord,
  WriteLayoutResult,
} from "../localWorldRepository";
import { createGraphFallbackPositions, indexLocalWorldGraph, projectLocalWorldGraph, type GraphProjectionOptions, type ProjectedGraphEdge, type ProjectedGraphNode } from "./graphProjection";
import type { NewLocalGraphObject, NewLocalGraphRelationship } from "./localWorldGraphAdapter";
import "./worldGraphCanvas.css";

const WIDTH = 960;
const HEIGHT = 520;
const MIN_ZOOM = 0.15;
const MAX_ZOOM = 2.5;
const MAX_NODE_COORDINATE = 6000;
const NODE_WIDTH = 168;
const NODE_HEIGHT = 76;
const CIRCLE_RADIUS = 56;
const CIRCLE_DIAMETER = CIRCLE_RADIUS * 2;
// Area grows logarithmically with loaded degree, saturating at 100 relationships.
function bubbleRadius(count: number): number {
  return Math.sqrt(32 ** 2 + (56 ** 2 - 32 ** 2) * Math.min(1, Math.log1p(Math.max(0, count)) / Math.log1p(100)));
}
function kindColor(kind: string): string {
  const colors: Record<string, string> = {
    npc: "#77b5d9", pc: "#d68f9f", item: "#d8a17d", event: "#dbb65c",
    location: "#a4bd78", place: "#a4bd78", character: "#a8b4be",
    "character (role unspecified)": "#a8b4be", person: "#a8b4be",
    "session beat": "#b397d0", session_beat: "#b397d0",
    faction: "#b397d0", group: "#b397d0", organization: "#b397d0",
  };
  const key = kind.toLowerCase();
  return Object.hasOwn(colors, key) ? colors[key] : "#bac0c4";
}
function recordedNames(node: ProjectedGraphNode): string[] {
  const names = node.object.properties.recordedNames;
  return Array.isArray(names) ? names.filter((name): name is string => typeof name === "string" && name.trim().length > 0) : [];
}
function shortLabel(value: string, limit: number): string {
  return value.length > limit ? `${value.slice(0, limit - 1)}…` : value;
}
interface NodePosition { readonly x: number; readonly y: number; readonly radius?: number }

export interface CanvasCreationKind {
  readonly kind: string;
  readonly label: string;
}

export interface CanvasCreateIntent {
  readonly kind: string;
  readonly position: { readonly x: number; readonly y: number };
}

export interface CanvasConnectIntent {
  readonly sourceId: LocalObjectId;
  readonly targetId: LocalObjectId;
}

type NodeShape = "card" | "circle";

interface NodeInteractionHandlers {
  selectNode(id: LocalObjectId): void;
  onNodeKeyDown(event: KeyboardEvent<SVGGElement>, id: LocalObjectId): void;
  beginGesture(event: PointerEvent, node?: { id: LocalObjectId; x: number; y: number }): void;
  beginConnectGesture(event: PointerEvent, id: LocalObjectId): void;
}

// A selection changes only the affected bubbles, not all loaded SVG labels.
const GraphBubble = memo(function GraphBubble({ node, position, selected, isConnectTarget, nodeShape, fullCorpus, canConnect, handlersRef, suppressClickRef }: {
  node: ProjectedGraphNode;
  position: { x: number; y: number };
  selected: boolean;
  isConnectTarget: boolean;
  nodeShape: NodeShape;
  fullCorpus: boolean;
  canConnect: boolean;
  handlersRef: RefObject<NodeInteractionHandlers>;
  suppressClickRef: RefObject<LocalObjectId | null>;
}) {
  const radius = fullCorpus ? bubbleRadius(node.relationshipCount) : CIRCLE_RADIUS;
  const names = recordedNames(node);
  const description = `${node.name}, ${node.kind}${fullCorpus ? `, ${node.relationshipCount} relationships in loaded snapshot` : ""}${names.length ? `. Recorded names: ${names.join("; ")}` : ""}`;
  return (
    <g
      key={node.id}
      className={`world-graph-canvas__node${selected ? " is-selected" : ""}${isConnectTarget ? " is-connect-target" : ""}${nodeShape === "circle" ? " is-circle" : ""}`}
      style={fullCorpus ? { "--node-color": kindColor(node.kind) } as CSSProperties : undefined}
      transform={`translate(${position.x} ${position.y})`}
      role="button"
      tabIndex={0}
      aria-pressed={selected}
      aria-label={`${node.name}, ${node.kind}`}
      aria-description={description}
      data-node-id={node.id}
      onClick={() => {
        if (suppressClickRef.current === node.id) { suppressClickRef.current = null; return; }
        handlersRef.current.selectNode(node.id);
      }}
      onKeyDown={(event) => handlersRef.current.onNodeKeyDown(event, node.id)}
      onPointerDown={(event) => { event.stopPropagation(); handlersRef.current.beginGesture(event, node); }}
    >
      <title>{description}</title>
      {nodeShape === "circle" ? <>
        <circle className="world-graph-canvas__node-circle" cx={CIRCLE_RADIUS} cy={CIRCLE_RADIUS} r={radius} />
        <text className="world-graph-canvas__node-kind" x={CIRCLE_RADIUS} y={CIRCLE_RADIUS - 5} textAnchor="middle">{shortLabel(node.kind, Math.max(7, Math.floor(radius / 3.4)))}</text>
        <text className="world-graph-canvas__node-name" x={CIRCLE_RADIUS} y={CIRCLE_RADIUS + 17} textAnchor="middle">
          {shortLabel(node.name, Math.max(7, Math.floor(radius / 4)))}
        </text>
      </> : <>
        <rect width={NODE_WIDTH} height={NODE_HEIGHT} rx="12" />
        <text className="world-graph-canvas__node-kind" x="14" y="22">{node.kind}</text>
        <text className="world-graph-canvas__node-name" x="14" y="49">{node.name.length > 22 ? `${node.name.slice(0, 21)}…` : node.name}</text>
      </>}
      {canConnect ? <circle className="world-graph-canvas__node-port" data-testid={`connect-port-${node.id}`}
        aria-hidden="true" cx={nodeShape === "circle" ? CIRCLE_RADIUS + radius - 2 : NODE_WIDTH - 3}
        cy={nodeShape === "circle" ? CIRCLE_RADIUS : NODE_HEIGHT / 2} r="7"
        onPointerDown={(event) => handlersRef.current.beginConnectGesture(event, node.id)}
        onClick={(event) => { event.preventDefault(); event.stopPropagation(); }} /> : null}
    </g>
  );
});

export interface WorldGraphCanvasProps {
  readonly canvasId?: string;
  readonly record: LocalWorldRecord;
  readonly editorDraftState?: { readonly version: number; readonly draft: WorldGraphEditorDraft | null };
  readonly onEditorDraftChange?: (draft: WorldGraphEditorDraft | null, version: number, expectedVersion?: number) => void;
  readonly onEditorDraftCommit?: (field: WorldGraphEditorDraftField, submittedToken: number) => void;
  readonly projectionOptions?: GraphProjectionOptions;
  readonly onRenameObject?: (record: LocalWorldRecord, objectId: LocalObjectId, name: string) => Promise<CommitSemanticResult>;
  readonly onCreateObject?: (record: LocalWorldRecord, input: NewLocalGraphObject) => Promise<CommitSemanticResult>;
  readonly onCreateRelationship?: (record: LocalWorldRecord, input: NewLocalGraphRelationship) => Promise<CommitSemanticResult>;
  readonly onMoveObjects?: (record: LocalWorldRecord, positions: Readonly<Record<string, { readonly x: number; readonly y: number }>>) => Promise<WriteLayoutResult>;
  readonly onSemanticResult?: (result: CommitSemanticResult) => void;
  readonly onLayoutResult?: (result: WriteLayoutResult) => void;
  readonly nodeShape?: NodeShape;
  readonly creationKinds?: readonly CanvasCreationKind[];
  readonly onCanvasCreateRequest?: (intent: CanvasCreateIntent) => void;
  readonly onConnectRequest?: (intent: CanvasConnectIntent) => void;
  readonly onSelectionChange?: (id: LocalObjectId | null) => void;
  /** Keep an exact created/recovered object visible without moving the camera. */
  readonly revealObjectId?: LocalObjectId | null;
  readonly cameraFocusRequest?: { readonly nodeId: LocalObjectId | null; readonly requestId: number; readonly selectNode?: boolean };
  readonly clearCameraFocusRequest?: number | { readonly requestId: number; readonly fitView: boolean };
  readonly clearSelectionRequest?: number;
  readonly onCameraFocusChange?: (nodeId: LocalObjectId | null) => void;
  readonly interactionDisabled?: boolean;
  readonly showSummaryCounts?: boolean;
  /** Preserve the current camera on viewport changes after the first measured fit. */
  readonly preserveCameraOnResize?: boolean;
}

export interface WorldGraphEditorDraft {
  readonly version: number;
  readonly renameToken: number;
  readonly objectToken: number;
  readonly relationshipToken: number;
  readonly selectedIds: readonly LocalObjectId[];
  readonly renameId: LocalObjectId | null;
  readonly renameValue: string;
  readonly showObjectForm: boolean;
  readonly objectName: string;
  readonly objectKind: string;
  readonly showRelationshipForm: boolean;
  readonly relationshipKind: string;
}

export type WorldGraphEditorDraftField = "rename" | "object" | "relationship";

function emptyEditorDraft(version = 0): WorldGraphEditorDraft {
  return { version, renameToken: version, objectToken: version, relationshipToken: version, selectedIds: [], renameId: null, renameValue: "", showObjectForm: false, objectName: "", objectKind: "person", showRelationshipForm: false, relationshipKind: "" };
}

function hasEditorDraft(draft: WorldGraphEditorDraft): boolean {
  return draft.renameId !== null || draft.showObjectForm || draft.objectName.length > 0 || draft.showRelationshipForm || draft.relationshipKind.length > 0;
}

interface Camera { readonly x: number; readonly y: number; readonly zoom: number }
interface CanvasGesture {
  readonly worldId: string;
  readonly kind: "node" | "pan" | "connect";
  readonly captureTarget: Element;
  readonly pointerId: number;
  readonly pointerX: number;
  readonly pointerY: number;
  readonly camera: Camera;
  readonly scaleX: number;
  readonly scaleY: number;
  readonly node?: { readonly id: LocalObjectId; readonly x: number; readonly y: number };
  readonly originNodeId?: LocalObjectId;
  readonly sourceId?: LocalObjectId;
  moved: boolean;
}

interface GraphPoint { readonly x: number; readonly y: number }

interface CanvasPalette {
  readonly point: GraphPoint;
}

interface PaletteScreenPosition {
  readonly x: number;
  readonly y: number;
  readonly maxWidth: number;
  readonly maxHeight: number;
}

interface VisibleViewportBounds {
  readonly left: number;
  readonly top: number;
  readonly right: number;
  readonly bottom: number;
  readonly width: number;
  readonly height: number;
}

function visibleViewportBounds(): VisibleViewportBounds {
  const visualViewport = typeof window === "undefined" ? null : window.visualViewport;
  const left = visualViewport?.offsetLeft ?? 0;
  const top = visualViewport?.offsetTop ?? 0;
  const width = Math.max(0, visualViewport?.width ?? (typeof window === "undefined" ? WIDTH : window.innerWidth));
  const height = Math.max(0, visualViewport?.height ?? (typeof window === "undefined" ? HEIGHT : window.innerHeight));
  return { left, top, right: left + width, bottom: top + height, width, height };
}

function nodeDimensions(shape: NodeShape) {
  return shape === "circle"
    ? { width: CIRCLE_DIAMETER, height: CIRCLE_DIAMETER }
    : { width: NODE_WIDTH, height: NODE_HEIGHT };
}

function labelLines(value: string): string[] {
  // Bound visual labels, but retain the full predicate in the accessible name/title.
  const bounded = value.length > 96 ? `${value.slice(0, 95)}…` : value;
  return bounded.match(/.{1,24}(?:\s|$)|.{1,24}/g)?.map((line) => line.trim()) ?? [""];
}

function labelBox(value: string) {
  const lines = labelLines(value);
  // One em per UTF-16 unit is conservative for the 12px label font, including wide glyphs.
  return { lines, width: Math.max(...lines.map((line) => line.length)) * 12 + 20, height: lines.length * 16 + 10 };
}

interface EdgeGeometry {
  readonly path: string;
  readonly labelX: number;
  readonly labelY: number;
  readonly bounds: { readonly left: number; readonly top: number; readonly right: number; readonly bottom: number };
}

function edgeGeometry(
  edge: ProjectedGraphEdge,
  positions: ReadonlyMap<string, NodePosition>,
  parallelIndex: number,
  parallelCount: number,
  labelWidth: number,
  labelHeight: number,
  shape: NodeShape,
): EdgeGeometry {
  const from = positions.get(edge.fromObjectId)!;
  const to = positions.get(edge.toObjectId)!;
  const dimensions = nodeDimensions(shape);
  const radius = shape === "circle" ? (from.radius ?? CIRCLE_RADIUS) : undefined;
  const fromCenter = { x: from.x + dimensions.width / 2, y: from.y + dimensions.height / 2 };
  const toCenter = { x: to.x + dimensions.width / 2, y: to.y + dimensions.height / 2 };
  if (edge.fromObjectId === edge.toObjectId || (from.x === to.x && from.y === to.y)) {
    const endRadius = to.radius ?? CIRCLE_RADIUS;
    const clearanceRadius = Math.max(radius ?? 0, endRadius);
    // Concentric loops put their plates side by side, with no shared label band.
    const spread = parallelIndex * (labelWidth + 12) * 4 / 3;
    const start = radius === undefined
      ? { x: from.x + NODE_WIDTH + 5, y: from.y + 15 }
      : { x: fromCenter.x + (radius + 5) * Math.cos(-0.72), y: fromCenter.y + (radius + 5) * Math.sin(-0.72) };
    const end = radius === undefined
      ? { x: from.x + NODE_WIDTH + 5, y: from.y + NODE_HEIGHT - 15 }
      : { x: fromCenter.x + (endRadius + 5) * Math.cos(0.72), y: fromCenter.y + (endRadius + 5) * Math.sin(0.72) };
    const controlOne = radius === undefined
      ? { x: from.x + NODE_WIDTH + 76 + Math.abs(spread), y: from.y - 42 }
      : { x: fromCenter.x + clearanceRadius + 64 + Math.abs(spread), y: fromCenter.y - clearanceRadius - 28 };
    const controlTwo = radius === undefined
      ? { x: from.x + NODE_WIDTH + 76 + Math.abs(spread), y: from.y + NODE_HEIGHT + 42 }
      : { x: fromCenter.x + clearanceRadius + 64 + Math.abs(spread), y: fromCenter.y + clearanceRadius + 28 };
    return {
      path: `M ${start.x} ${start.y} C ${controlOne.x} ${controlOne.y} ${controlTwo.x} ${controlTwo.y} ${end.x} ${end.y}`,
      labelX: (start.x + 3 * controlOne.x + 3 * controlTwo.x + end.x) / 8 + 4,
      labelY: (start.y + 3 * controlOne.y + 3 * controlTwo.y + end.y) / 8,
      bounds: { left: Math.min(start.x, end.x, controlOne.x, controlTwo.x), top: Math.min(start.y, end.y, controlOne.y, controlTwo.y),
        right: Math.max(start.x, end.x, controlOne.x, controlTwo.x), bottom: Math.max(start.y, end.y, controlOne.y, controlTwo.y) },
    };
  }
  const start = fromCenter;
  const end = toCenter;
  const canonicalForward = edge.fromObjectId.localeCompare(edge.toObjectId) < 0;
  const laneStart = canonicalForward ? start : end;
  const laneEnd = canonicalForward ? end : start;
  const dx = laneEnd.x - laneStart.x;
  const dy = laneEnd.y - laneStart.y;
  const length = Math.hypot(dx, dy) || 1;
  // Quadratic midpoints travel half the control-point offset. Space plate projections
  // along the lane normal, so vertical, diagonal and wrapped horizontal labels stay disjoint.
  const plateExtent = labelWidth * Math.abs(dy) / length + labelHeight * Math.abs(dx) / length;
  const offset = (parallelIndex - (parallelCount - 1) / 2) * 2 * (plateExtent + 12);
  const control = {
    x: (start.x + end.x) / 2 - (dy / length) * offset,
    y: (start.y + end.y) / 2 + (dx / length) * offset,
  };
  function boundary(center: { x: number; y: number }, toward: { x: number; y: number }, endpointRadius: number | undefined) {
    const vx = toward.x - center.x;
    const vy = toward.y - center.y;
    if (endpointRadius !== undefined) {
      const length = Math.hypot(vx, vy) || 1;
      const extent = endpointRadius + 5;
      return { x: center.x + (vx / length) * extent, y: center.y + (vy / length) * extent };
    }
    const extent = Math.max(Math.abs(vx) / (NODE_WIDTH / 2 + 5), Math.abs(vy) / (NODE_HEIGHT / 2 + 5));
    return extent > 0 ? { x: center.x + vx / extent, y: center.y + vy / extent } : center;
  }
  const pathStart = boundary(start, control, radius);
  const pathEnd = boundary(end, control, shape === "circle" ? (to.radius ?? CIRCLE_RADIUS) : undefined);
  // Tight, user-arranged nodes need a label outside their overlap rather than hidden under a card.
  const tight = Math.abs(dx) < dimensions.width + 160 && Math.abs(dy) < dimensions.height + 70;
  return {
    path: `M ${pathStart.x} ${pathStart.y} Q ${control.x} ${control.y} ${pathEnd.x} ${pathEnd.y}`,
    labelX: (start.x + 2 * control.x + end.x) / 4,
    labelY: (start.y + 2 * control.y + end.y) / 4 - (tight ? dimensions.height + 30 : 0),
    bounds: { left: Math.min(pathStart.x, pathEnd.x, control.x), top: Math.min(pathStart.y, pathEnd.y, control.y),
      right: Math.max(pathStart.x, pathEnd.x, control.x), bottom: Math.max(pathStart.y, pathEnd.y, control.y) },
  };
}

function renderEdges(edges: readonly ProjectedGraphEdge[], positions: ReadonlyMap<string, NodePosition>, shape: NodeShape) {
  const edgeGroups = new Map<string, { count: number; width: number; height: number }>();
  for (const edge of edges) {
    const key = [edge.fromObjectId, edge.toObjectId].sort().join("\u0000");
    const previous = edgeGroups.get(key) ?? { count: 0, width: 0, height: 0 };
    const box = labelBox(edge.kind);
    edgeGroups.set(key, { count: previous.count + 1, width: Math.max(previous.width, box.width), height: Math.max(previous.height, box.height) });
  }
  const edgeGroupIndexes = new Map<string, number>();
  return edges.map((edge) => {
    const key = [edge.fromObjectId, edge.toObjectId].sort().join("\u0000");
    const index = edgeGroupIndexes.get(key) ?? 0;
    edgeGroupIndexes.set(key, index + 1);
    const group = edgeGroups.get(key)!;
    return { edge, box: labelBox(edge.kind), geometry: edgeGeometry(edge, positions, index, group.count, group.width, group.height, shape) };
  });
}

function graphNodeContains(point: GraphPoint, node: NodePosition, shape: NodeShape): boolean {
  if (shape === "circle") {
    const dx = point.x - (node.x + CIRCLE_RADIUS);
    const dy = point.y - (node.y + CIRCLE_RADIUS);
    return dx * dx + dy * dy <= (node.radius ?? CIRCLE_RADIUS) ** 2;
  }
  return point.x >= node.x && point.x <= node.x + NODE_WIDTH && point.y >= node.y && point.y <= node.y + NODE_HEIGHT;
}

function accessibleRelationshipLabel(
  edge: ProjectedGraphEdge,
  names: ReadonlyMap<string, string>,
): string {
  const from = names.get(edge.fromObjectId) ?? "Unknown object";
  const to = names.get(edge.toObjectId) ?? "Unknown object";
  return `${from} ${edge.kind} ${to}`;
}

function messageForSemanticResult(result: CommitSemanticResult): string {
  switch (result.status) {
    case "committed": return "Edit recorded.";
    case "conflict": return "This World changed elsewhere. Your proposed edit is kept as a conflict candidate.";
    case "missing": return "This World is no longer available.";
    case "error": return result.message;
  }
}

function messageForLayoutResult(result: WriteLayoutResult): string {
  switch (result.status) {
    case "written": return "Canvas layout updated.";
    case "conflict": return "The canvas layout changed elsewhere. Reload its latest layout before moving nodes again.";
    case "missing": return "This World is no longer available.";
    case "error": return result.message;
  }
}

export function WorldGraphCanvas({
  canvasId,
  record,
  editorDraftState,
  onEditorDraftChange,
  onEditorDraftCommit,
  projectionOptions,
  onRenameObject,
  onCreateObject,
  onCreateRelationship,
  onMoveObjects,
  onSemanticResult,
  onLayoutResult,
  nodeShape = "card",
  creationKinds,
  onCanvasCreateRequest,
  onConnectRequest,
  onSelectionChange,
  cameraFocusRequest,
  revealObjectId,
  clearCameraFocusRequest,
  clearSelectionRequest,
  onCameraFocusChange,
  interactionDisabled = false,
  showSummaryCounts = true,
  preserveCameraOnResize = false,
}: WorldGraphCanvasProps) {
  const index = useMemo(() => indexLocalWorldGraph(record.snapshot), [record.snapshot]);
  const fullCorpus = projectionOptions?.fullCorpus === true;
  const initialDraft = editorDraftState?.draft ?? emptyEditorDraft(editorDraftState?.version ?? 0);
  const [selectedIds, setSelectedIds] = useState<LocalObjectId[]>([...initialDraft.selectedIds]);
  const lastSelectionClearRequestRef = useRef<number | null>(null);
  // Fit in the reset commit must already see the post-reset visibility.
  const clearingSelection = clearSelectionRequest !== undefined && lastSelectionClearRequestRef.current !== clearSelectionRequest;
  const [unconnectedVisibility, setUnconnectedVisibility] = useState<{ worldId: string; show: boolean } | null>(null);
  const showUnconnected = unconnectedVisibility?.worldId === record.snapshot.worldId
    ? unconnectedVisibility.show : (projectionOptions?.showUnconnected ?? !fullCorpus);
  const revealObjectIds = useMemo(() => [...new Set([...(clearingSelection ? [] : selectedIds), ...(projectionOptions?.revealObjectIds ?? []),
    ...(cameraFocusRequest?.nodeId ? [cameraFocusRequest.nodeId] : []), ...(revealObjectId ? [revealObjectId] : [])])],
    [selectedIds, clearingSelection, projectionOptions?.revealObjectIds, cameraFocusRequest?.nodeId, revealObjectId]);
  const fallbackRef = useRef<{ worldId: string; positions: ReturnType<typeof createGraphFallbackPositions> } | null>(null);
  const fallbackPositions = useMemo(() => {
    if (!fullCorpus) return undefined;
    const previous = fallbackRef.current?.worldId === record.snapshot.worldId ? fallbackRef.current.positions : undefined;
    const positions = createGraphFallbackPositions(index, previous);
    fallbackRef.current = { worldId: record.snapshot.worldId, positions };
    return positions;
  }, [fullCorpus, index, record.snapshot.worldId]);
  const projection = useMemo(() => projectLocalWorldGraph(record, { ...projectionOptions, fallbackPositions, showUnconnected, revealObjectIds }, index),
    [record.snapshot, record.layout, index, fullCorpus, fallbackPositions, projectionOptions?.maxNodes, projectionOptions?.maxEdges,
      projectionOptions?.focusObjectId, projectionOptions?.neighborhoodDepth, showUnconnected, revealObjectIds]);
  const legend = useMemo(() => [...new Set(record.snapshot.objects.map((object) => object.kind))].sort(), [record.snapshot]);
  const isolatedCount = useMemo(() => record.snapshot.objects.filter((object) => !index.relationshipCounts.get(object.id)).length, [index, record.snapshot]);
  const markerId = `world-graph-arrow-${useId().replace(/:/g, "")}`;
  const [renameId, setRenameId] = useState<LocalObjectId | null>(initialDraft.renameId);
  const [renameValue, setRenameValue] = useState(initialDraft.renameValue);
  const [showObjectForm, setShowObjectForm] = useState(initialDraft.showObjectForm);
  const [showRelationshipForm, setShowRelationshipForm] = useState(initialDraft.showRelationshipForm);
  const [objectName, setObjectName] = useState(initialDraft.objectName);
  const [objectKind, setObjectKind] = useState(initialDraft.objectKind);
  const [relationshipKind, setRelationshipKind] = useState(initialDraft.relationshipKind);
  const editorDraftRef = useRef<WorldGraphEditorDraft>(initialDraft);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const svgRef = useRef<SVGSVGElement>(null);
  const [viewport, setViewport] = useState({ width: WIDTH, height: HEIGHT });
  const [viewportMeasured, setViewportMeasured] = useState(false);
  const [camera, setCamera] = useState<Camera>({ x: 0, y: 0, zoom: 1 });
  const [dragPreview, setDragPreview] = useState<{ id: LocalObjectId; x: number; y: number } | null>(null);
  const [isPanning, setIsPanning] = useState(false);
  const [moveNodesMode, setMoveNodesMode] = useState(false);
  const [palette, setPalette] = useState<CanvasPalette | null>(null);
  const [paletteScreen, setPaletteScreen] = useState<PaletteScreenPosition | null>(null);
  const [connectPreview, setConnectPreview] = useState<{ sourceId: LocalObjectId; point: GraphPoint } | null>(null);
  const gestureRef = useRef<CanvasGesture | null>(null);
  const paletteRef = useRef<HTMLDivElement>(null);
  const paletteFirstActionRef = useRef<HTMLButtonElement>(null);
  const paletteFocusPendingRef = useRef(false);
  const paletteTriggerRef = useRef<HTMLElement | SVGSVGElement | null>(null);
  const originalCameraBeforeFocusRef = useRef<Camera | null>(null);
  const lastCameraFocusRequestRef = useRef<number | null>(null);
  const lastCameraFocusClearRequestRef = useRef<number | null>(null);
  const initialFitWorldRef = useRef<string | null>(null);
  const suppressClickRef = useRef<LocalObjectId | null>(null);
  const manualCameraRef = useRef(false);
  const renameVersionRef = useRef(0);
  const objectNameVersionRef = useRef(0);
  const relationshipKindVersionRef = useRef(0);
  const currentWorldIdRef = useRef(record.snapshot.worldId);
  const worldGenerationRef = useRef(0);
  const instanceGenerationRef = useRef(0);
  const instanceActiveRef = useRef(false);
  if (currentWorldIdRef.current !== record.snapshot.worldId) {
    currentWorldIdRef.current = record.snapshot.worldId;
    worldGenerationRef.current += 1;
    renameVersionRef.current += 1;
    objectNameVersionRef.current += 1;
    relationshipKindVersionRef.current += 1;
    const nextDraft = editorDraftState?.draft ?? emptyEditorDraft(editorDraftState?.version ?? 0);
    editorDraftRef.current = nextDraft;
    setSelectedIds([...nextDraft.selectedIds]);
    setRenameId(nextDraft.renameId);
    setRenameValue(nextDraft.renameValue);
    setShowObjectForm(nextDraft.showObjectForm);
    setShowRelationshipForm(nextDraft.showRelationshipForm);
    setObjectName(nextDraft.objectName);
    setObjectKind(nextDraft.objectKind);
    setRelationshipKind(nextDraft.relationshipKind);
    setBusy(false);
    setStatus("");
    setDragPreview(null);
    setIsPanning(false);
    setMoveNodesMode(false);
    setPalette(null);
    setConnectPreview(null);
    suppressClickRef.current = null;
    manualCameraRef.current = false;
    originalCameraBeforeFocusRef.current = null;
    setCamera({ x: 0, y: 0, zoom: 1 });
  }

  function publishEditorDraft(patch: Partial<Omit<WorldGraphEditorDraft, "version">>) {
    const current = editorDraftRef.current;
    const touchesRename = "renameId" in patch || "renameValue" in patch;
    const touchesObject = "showObjectForm" in patch || "objectName" in patch || "objectKind" in patch;
    const touchesRelationship = "showRelationshipForm" in patch || "relationshipKind" in patch || "selectedIds" in patch;
    const next = {
      ...current,
      ...patch,
      version: current.version + 1,
      renameToken: current.renameToken + Number(touchesRename),
      objectToken: current.objectToken + Number(touchesObject),
      relationshipToken: current.relationshipToken + Number(touchesRelationship),
    };
    editorDraftRef.current = next;
    if (hasEditorDraft(next)) onEditorDraftChange?.(next, next.version);
    else onEditorDraftChange?.(null, next.version, current.version);
  }

  useEffect(() => {
    if (!editorDraftState || editorDraftState.version <= editorDraftRef.current.version) return;
    const next = editorDraftState.draft ?? emptyEditorDraft(editorDraftState.version);
    editorDraftRef.current = next;
    setSelectedIds([...next.selectedIds]);
    setRenameId(next.renameId);
    setRenameValue(next.renameValue);
    setShowObjectForm(next.showObjectForm);
    setObjectName(next.objectName);
    setObjectKind(next.objectKind);
    setShowRelationshipForm(next.showRelationshipForm);
    setRelationshipKind(next.relationshipKind);
  }, [editorDraftState]);

  useEffect(() => {
    instanceGenerationRef.current += 1;
    instanceActiveRef.current = true;
    return () => {
      instanceActiveRef.current = false;
      instanceGenerationRef.current += 1;
    };
  }, []);

  const selectedObject = projection.nodes.find((node) => node.id === selectedIds.at(-1));
  const persistedPositions = useMemo(() => new Map(projection.nodes.map((node) => [node.id, { ...node, radius: fullCorpus ? bubbleRadius(node.relationshipCount) : CIRCLE_RADIUS }])), [projection.nodes, fullCorpus]);
  const positions = useMemo(() => {
    if (!dragPreview) return persistedPositions;
    const preview = new Map<LocalObjectId, NodePosition>(persistedPositions);
    preview.set(dragPreview.id, { ...persistedPositions.get(dragPreview.id), ...dragPreview });
    return preview;
  }, [persistedPositions, dragPreview]);
  const dimensions = nodeDimensions(nodeShape);
  const nodeNames = useMemo(() => new Map(projection.nodes.map((node) => [node.id, node.name])), [projection.nodes]);
  // Geometry has no camera dependency: pan/zoom only changes the scene transform and detail level.
  const persistedEdges = useMemo(() => renderEdges(projection.edges, persistedPositions, nodeShape), [projection.edges, persistedPositions, nodeShape]);
  const renderedEdges = useMemo(() => dragPreview ? renderEdges(projection.edges, positions, nodeShape) : persistedEdges,
    [projection.edges, positions, nodeShape, dragPreview, persistedEdges]);
  const graphBounds = useMemo(() => {
    let left = Infinity, top = Infinity, right = -Infinity, bottom = -Infinity;
    for (const node of projection.nodes) {
      const radius = persistedPositions.get(node.id)!.radius;
      const inset = nodeShape === "circle" ? CIRCLE_RADIUS - radius : 0;
      left = Math.min(left, node.x + inset); top = Math.min(top, node.y + inset);
      right = Math.max(right, node.x + dimensions.width - inset); bottom = Math.max(bottom, node.y + dimensions.height - inset);
    }
    for (const { geometry, box } of persistedEdges) {
      left = Math.min(left, geometry.bounds.left, geometry.labelX - box.width / 2);
      top = Math.min(top, geometry.bounds.top, geometry.labelY - box.height / 2);
      right = Math.max(right, geometry.bounds.right, geometry.labelX + box.width / 2);
      bottom = Math.max(bottom, geometry.bounds.bottom, geometry.labelY + box.height / 2);
    }
    return { left: left - 56, top: top - 56, width: right - left + 112, height: bottom - top + 112 };
  }, [projection.nodes, persistedPositions, persistedEdges, nodeShape, dimensions.width, dimensions.height]);

  function fittedCamera(): Camera {
    if (!projection.nodes.length) return { x: 0, y: 0, zoom: 1 };
    const { left, top, width, height } = graphBounds;
    // Fit includes every visible edge/plate even when the bounded graph needs a scale below manual zoom-out.
    const zoom = Math.min(1, viewport.width / width, viewport.height / height);
    return { x: (viewport.width - width * zoom) / 2 - left * zoom,
      y: (viewport.height - height * zoom) / 2 - top * zoom, zoom };
  }

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg || typeof ResizeObserver === "undefined") {
      setViewportMeasured(true);
      return;
    }
    const observer = new ResizeObserver(([entry]) => {
      if (entry.contentRect.width > 0 && entry.contentRect.height > 0) {
        setViewport({ width: entry.contentRect.width, height: entry.contentRect.height });
        setViewportMeasured(true);
      }
    });
    observer.observe(svg);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!manualCameraRef.current && (!preserveCameraOnResize || viewportMeasured && initialFitWorldRef.current !== record.snapshot.worldId)) {
      setCamera(fittedCamera());
      if (preserveCameraOnResize && viewportMeasured) initialFitWorldRef.current = record.snapshot.worldId;
    }
    // Fit initial visibility and responsive size, never re-fit after user pan/zoom or node edits.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewport.width, viewport.height, viewportMeasured, record.snapshot.worldId, preserveCameraOnResize]);

  // Both effects share the intended reset baseline; setCamera does not update
  // the following effect's render-time camera closure in the same commit.
  const resetFitCamera = typeof clearCameraFocusRequest === "object" && clearCameraFocusRequest.fitView
    && lastCameraFocusClearRequestRef.current !== clearCameraFocusRequest.requestId ? fittedCamera() : null;
  // Revision resets precede a new explicit focus in the same commit.
  useLayoutEffect(() => {
    const requestId = typeof clearCameraFocusRequest === "object" ? clearCameraFocusRequest.requestId : clearCameraFocusRequest;
    if (requestId === undefined || lastCameraFocusClearRequestRef.current === requestId) return;
    lastCameraFocusClearRequestRef.current = requestId;
    originalCameraBeforeFocusRef.current = null;
    if (typeof clearCameraFocusRequest === "object" && clearCameraFocusRequest.fitView) {
      manualCameraRef.current = true;
      setCamera(resetFitCamera ?? fittedCamera());
    }
    onCameraFocusChange?.(null);
  }, [clearCameraFocusRequest, onCameraFocusChange, resetFitCamera]);

  useLayoutEffect(() => {
    if (clearSelectionRequest === undefined || lastSelectionClearRequestRef.current === clearSelectionRequest) return;
    lastSelectionClearRequestRef.current = clearSelectionRequest;
    setSelectedIds([]);
    onSelectionChange?.(null);
  }, [clearSelectionRequest, onSelectionChange]);

  useLayoutEffect(() => {
    if (!cameraFocusRequest || lastCameraFocusRequestRef.current === cameraFocusRequest.requestId) return;
    lastCameraFocusRequestRef.current = cameraFocusRequest.requestId;
    if (cameraFocusRequest.nodeId === null) {
      const previousCamera = originalCameraBeforeFocusRef.current;
      originalCameraBeforeFocusRef.current = null;
      manualCameraRef.current = true;
      // Fit can end camera focus while a neighborhood is still displayed. In
      // that case returning to the overview must frame the new projection.
      setCamera(previousCamera ?? fittedCamera());
      onCameraFocusChange?.(null);
      return;
    }
    const node = projection.nodes.find((candidate) => candidate.id === cameraFocusRequest.nodeId);
    if (!node) {
      originalCameraBeforeFocusRef.current = null;
      onCameraFocusChange?.(null);
      return;
    }
    const rect = svgRef.current?.getBoundingClientRect();
    const measuredViewport = {
      width: rect?.width && rect.width > 0 ? rect.width : viewport.width,
      height: rect?.height && rect.height > 0 ? rect.height : viewport.height,
    };
    if (measuredViewport.width !== viewport.width || measuredViewport.height !== viewport.height) {
      setViewport(measuredViewport);
    }
    if (cameraFocusRequest.selectNode) setSelectedIds([node.id]);
    const focusBaseline = resetFitCamera ?? camera;
    if (!originalCameraBeforeFocusRef.current) originalCameraBeforeFocusRef.current = focusBaseline;
    const zoom = Math.max(focusBaseline.zoom, 1.35);
    const centerX = node.x + dimensions.width / 2;
    const centerY = node.y + dimensions.height / 2;
    manualCameraRef.current = true;
    setCamera({ zoom, x: measuredViewport.width / 2 - centerX * zoom,
      y: measuredViewport.height / 2 - centerY * zoom });
    onCameraFocusChange?.(node.id);
  }, [camera, resetFitCamera, cameraFocusRequest, dimensions.height, dimensions.width, onCameraFocusChange, projection.nodes, viewport.height, viewport.width]);

  useLayoutEffect(() => {
    // Release capture and suppress the trailing click before a new revision/authority becomes interactive.
    cancelGesture();
    setDragPreview(null);
    setIsPanning(false);
    setConnectPreview(null);
    setPalette(null);
  }, [record.snapshot.worldId, record.localRevision, record.layoutRevision, interactionDisabled]);

  const creationSignature = creationKinds?.map((item) => `${item.kind}:${item.label}`).join("|") ?? "";

  useLayoutEffect(() => {
    if (!palette) return;
    if (paletteFocusPendingRef.current) {
      paletteFocusPendingRef.current = false;
      paletteFirstActionRef.current?.focus();
    }
    const updatePalettePosition = () => {
      const menuRect = paletteRef.current?.getBoundingClientRect();
      if (!menuRect || menuRect.width <= 0 || menuRect.height <= 0) return;
      const bounds = visibleViewportBounds();
      const svgRect = svgRef.current?.getBoundingClientRect();
      const scaleX = svgRect?.width && viewport.width ? svgRect.width / viewport.width : 1;
      const scaleY = svgRect?.height && viewport.height ? svgRect.height / viewport.height : 1;
      const graphScreenX = camera.x + palette.point.x * camera.zoom;
      const graphScreenY = camera.y + palette.point.y * camera.zoom;
      const anchorX = (svgRect?.left ?? 0) + graphScreenX * scaleX;
      const anchorY = (svgRect?.top ?? 0) + graphScreenY * scaleY;
      const maxWidth = Math.max(0, bounds.width - 16);
      const maxHeight = Math.max(0, bounds.height - 16);
      const menuWidth = Math.min(menuRect.width, maxWidth);
      const menuHeight = Math.min(menuRect.height, maxHeight);
      let x = anchorX;
      let y = anchorY;
      if (x + menuWidth > bounds.right - 8) {
        const leftOfAnchor = anchorX - menuWidth;
        if (leftOfAnchor >= bounds.left + 8) x = leftOfAnchor;
      }
      if (y + menuHeight > bounds.bottom - 8) {
        const aboveAnchor = anchorY - menuHeight;
        if (aboveAnchor >= bounds.top + 8) y = aboveAnchor;
      }
      x = Math.max(bounds.left + 8, Math.min(bounds.right - menuWidth - 8, x));
      y = Math.max(bounds.top + 8, Math.min(bounds.bottom - menuHeight - 8, y));
      setPaletteScreen((current) => current
        && Math.abs(current.x - x) < 0.1 && Math.abs(current.y - y) < 0.1
        && Math.abs(current.maxWidth - maxWidth) < 0.1 && Math.abs(current.maxHeight - maxHeight) < 0.1
        ? current : { x, y, maxWidth, maxHeight });
    };
    updatePalettePosition();
    window.addEventListener("resize", updatePalettePosition);
    // A page or nested scroll can move the clicked canvas anchor under a fixed popover.
    window.addEventListener("scroll", updatePalettePosition, true);
    const visualViewport = window.visualViewport;
    visualViewport?.addEventListener("resize", updatePalettePosition);
    visualViewport?.addEventListener("scroll", updatePalettePosition);
    return () => {
      window.removeEventListener("resize", updatePalettePosition);
      window.removeEventListener("scroll", updatePalettePosition, true);
      visualViewport?.removeEventListener("resize", updatePalettePosition);
      visualViewport?.removeEventListener("scroll", updatePalettePosition);
    };
  }, [camera.x, camera.y, camera.zoom, creationSignature, palette, paletteScreen, viewport.height, viewport.width]);

  useLayoutEffect(() => {
    if (!palette) return;
    const onGlobalKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setPalette(null);
      setPaletteScreen(null);
      paletteFocusPendingRef.current = false;
      queueMicrotask(() => paletteTriggerRef.current?.focus());
      event.preventDefault();
      event.stopPropagation();
    };
    window.addEventListener("keydown", onGlobalKeyDown, true);
    return () => window.removeEventListener("keydown", onGlobalKeyDown, true);
  }, [palette]);

  useEffect(() => {
    onSelectionChange?.(selectedIds.at(-1) ?? null);
  }, [selectedIds, onSelectionChange]);

  function graphPointAt(clientX: number, clientY: number, baseCamera: Camera = camera): GraphPoint {
    const rect = svgRef.current?.getBoundingClientRect();
    const screenX = rect?.width ? (clientX - rect.left) * viewport.width / rect.width : clientX;
    const screenY = rect?.height ? (clientY - rect.top) * viewport.height / rect.height : clientY;
    return {
      x: Math.max(0, Math.min(MAX_NODE_COORDINATE, (screenX - baseCamera.x) / baseCamera.zoom)),
      y: Math.max(0, Math.min(MAX_NODE_COORDINATE, (screenY - baseCamera.y) / baseCamera.zoom)),
    };
  }

  function openPalette(point: GraphPoint, trigger?: HTMLElement | SVGSVGElement | null) {
    if (interactionDisabled || !onCanvasCreateRequest || !creationKinds?.length) return;
    paletteTriggerRef.current = trigger
      ?? (document.activeElement instanceof HTMLElement ? document.activeElement : null);
    paletteFocusPendingRef.current = true;
    const bounds = visibleViewportBounds();
    setPaletteScreen({ x: bounds.left + 8, y: bounds.top + 8,
      maxWidth: Math.max(0, bounds.width - 16), maxHeight: Math.max(0, bounds.height - 16) });
    setPalette({ point });
  }

  function openPaletteAtCanvasCenter() {
    openPalette({
      x: Math.max(0, Math.min(MAX_NODE_COORDINATE, (viewport.width / 2 - camera.x) / camera.zoom)),
      y: Math.max(0, Math.min(MAX_NODE_COORDINATE, (viewport.height / 2 - camera.y) / camera.zoom)),
    }, document.activeElement instanceof HTMLElement ? document.activeElement : null);
  }

  function closePalette(restoreFocus = false) {
    setPalette(null);
    setPaletteScreen(null);
    paletteFocusPendingRef.current = false;
    if (restoreFocus) queueMicrotask(() => paletteTriggerRef.current?.focus());
  }

  function nodeAt(point: GraphPoint): LocalObjectId | null {
    for (let index = projection.nodes.length - 1; index >= 0; index -= 1) {
      const node = projection.nodes[index];
      const position = positions.get(node.id);
      if (position && graphNodeContains(point, position, nodeShape)) return node.id;
    }
    return null;
  }

  function emitConnectRequest(sourceId: LocalObjectId, targetId: LocalObjectId) {
    if (interactionDisabled || !onConnectRequest) return;
    onConnectRequest({ sourceId, targetId });
    setStatus("Connection draft opened.");
  }

  function zoomBy(factor: number) {
    cancelGesture();
    manualCameraRef.current = true;
    setCamera((current) => {
      const zoom = Math.max(Math.min(MIN_ZOOM, fullCorpus ? fittedCamera().zoom : MIN_ZOOM, current.zoom), Math.min(MAX_ZOOM, current.zoom * factor));
      const ratio = zoom / current.zoom;
      return { zoom, x: viewport.width / 2 - (viewport.width / 2 - current.x) * ratio,
        y: viewport.height / 2 - (viewport.height / 2 - current.y) * ratio };
    });
  }
  function fitGraph() {
    cancelGesture();
    manualCameraRef.current = true;
    originalCameraBeforeFocusRef.current = null;
    setCamera(fittedCamera());
    onCameraFocusChange?.(null);
  }
  const connectTargetId = connectPreview ? nodeAt(connectPreview.point) : null;

  function selectNode(id: LocalObjectId) {
    if (showRelationshipForm) relationshipKindVersionRef.current += 1;
    const next = selectedIds.includes(id) ? selectedIds.filter((item) => item !== id) : [...selectedIds, id];
    setSelectedIds(next);
    publishEditorDraft({ selectedIds: showRelationshipForm ? next : [], showRelationshipForm, relationshipKind });
  }

  async function runSemantic(action: () => Promise<CommitSemanticResult>, submittedDraft?: { readonly field: WorldGraphEditorDraftField; readonly token: number }): Promise<CommitSemanticResult | null> {
    if (busy) return null;
    const submittedWorldId = record.snapshot.worldId;
    const submittedGeneration = worldGenerationRef.current;
    const submittedInstanceGeneration = instanceGenerationRef.current;
    setBusy(true);
    setStatus("Saving edit…");
    try {
      const result = await action();
      const isCurrent = instanceActiveRef.current && instanceGenerationRef.current === submittedInstanceGeneration &&
        currentWorldIdRef.current === submittedWorldId && worldGenerationRef.current === submittedGeneration;
      if (!isCurrent && result.status === "committed" && submittedDraft !== undefined) {
        onEditorDraftCommit?.(submittedDraft.field, submittedDraft.token);
      }
      if (isCurrent) {
        onSemanticResult?.(result);
        setStatus(messageForSemanticResult(result));
      }
      return isCurrent ? result : null;
    } catch (error) {
      if (instanceActiveRef.current && instanceGenerationRef.current === submittedInstanceGeneration &&
          currentWorldIdRef.current === submittedWorldId && worldGenerationRef.current === submittedGeneration) {
        setStatus(error instanceof Error ? error.message : "The edit could not be saved.");
      }
      return null;
    } finally {
      if (instanceActiveRef.current && instanceGenerationRef.current === submittedInstanceGeneration &&
          worldGenerationRef.current === submittedGeneration) setBusy(false);
    }
  }

  async function runLayout(positionsToWrite: Readonly<Record<string, { readonly x: number; readonly y: number }>>) {
    if (!onMoveObjects || busy || interactionDisabled) return;
    const submittedWorldId = record.snapshot.worldId;
    const submittedGeneration = worldGenerationRef.current;
    const submittedInstanceGeneration = instanceGenerationRef.current;
    setBusy(true);
    setStatus("Saving canvas layout…");
    try {
      const result = await onMoveObjects(record, positionsToWrite);
      if (instanceActiveRef.current && instanceGenerationRef.current === submittedInstanceGeneration &&
          currentWorldIdRef.current === submittedWorldId && worldGenerationRef.current === submittedGeneration) {
        onLayoutResult?.(result);
        setStatus(messageForLayoutResult(result));
      }
    } catch (error) {
      if (instanceActiveRef.current && instanceGenerationRef.current === submittedInstanceGeneration &&
          currentWorldIdRef.current === submittedWorldId && worldGenerationRef.current === submittedGeneration) {
        setStatus(error instanceof Error ? error.message : "The canvas layout could not be saved.");
      }
    } finally {
      if (instanceActiveRef.current && instanceGenerationRef.current === submittedInstanceGeneration &&
          worldGenerationRef.current === submittedGeneration) {
        setBusy(false);
        setDragPreview(null);
      }
    }
  }

  function beginGesture(event: PointerEvent, node?: { id: LocalObjectId; x: number; y: number }) {
    const movesNode = Boolean(node && (!fullCorpus || moveNodesMode));
    if ((event.button ?? 0) !== 0 || gestureRef.current || (movesNode && (busy || !onMoveObjects || interactionDisabled))) return;
    event.preventDefault();
    event.stopPropagation();
    suppressClickRef.current = null;
    const svg = svgRef.current;
    const rect = svg?.getBoundingClientRect();
    gestureRef.current = { worldId: record.snapshot.worldId, kind: movesNode ? "node" : "pan", captureTarget: event.currentTarget, pointerId: event.pointerId,
      pointerX: event.clientX, pointerY: event.clientY, camera,
      scaleX: rect?.width ? viewport.width / rect.width : 1,
      scaleY: rect?.height ? viewport.height / rect.height : 1,
      node: movesNode ? node : undefined, originNodeId: node?.id, moved: false };
    try { event.currentTarget.setPointerCapture(event.pointerId); } catch { /* Optional in test DOMs. */ }
  }

  function beginConnectGesture(event: PointerEvent, sourceId: LocalObjectId) {
    if ((event.button ?? 0) !== 0 || gestureRef.current || interactionDisabled || busy || !onConnectRequest) return;
    event.preventDefault();
    event.stopPropagation();
    const svg = svgRef.current;
    const rect = svg?.getBoundingClientRect();
    const source = positions.get(sourceId);
    if (!source) return;
    const portPoint = nodeShape === "circle"
      ? { x: source.x + CIRCLE_RADIUS + (source.radius ?? CIRCLE_RADIUS) - 2, y: source.y + CIRCLE_RADIUS }
      : { x: source.x + NODE_WIDTH - 3, y: source.y + NODE_HEIGHT / 2 };
    gestureRef.current = {
      worldId: record.snapshot.worldId, kind: "connect", sourceId, captureTarget: event.currentTarget, pointerId: event.pointerId,
      pointerX: event.clientX, pointerY: event.clientY, camera,
      scaleX: rect?.width ? viewport.width / rect.width : 1,
      scaleY: rect?.height ? viewport.height / rect.height : 1,
      moved: false,
    };
    setConnectPreview({ sourceId, point: portPoint });
    try { event.currentTarget.setPointerCapture(event.pointerId); } catch { /* Optional in test DOMs. */ }
  }

  function updateGesture(event: PointerEvent<SVGSVGElement>) {
    const gesture = gestureRef.current;
    if (!gesture || gesture.pointerId !== event.pointerId) return;
    const dx = (event.clientX - gesture.pointerX) * gesture.scaleX;
    const dy = (event.clientY - gesture.pointerY) * gesture.scaleY;
    if (Math.abs(event.clientX - gesture.pointerX) + Math.abs(event.clientY - gesture.pointerY) > 4) gesture.moved = true;
    if (!gesture.moved) return;
    if (gesture.kind === "connect" && gesture.sourceId) {
      setConnectPreview({ sourceId: gesture.sourceId, point: graphPointAt(event.clientX, event.clientY, gesture.camera) });
    } else if (gesture.node) {
      setDragPreview({ id: gesture.node.id,
        x: Math.max(0, Math.min(MAX_NODE_COORDINATE, gesture.node.x + dx / gesture.camera.zoom)),
        y: Math.max(0, Math.min(MAX_NODE_COORDINATE, gesture.node.y + dy / gesture.camera.zoom)) });
    } else {
      manualCameraRef.current = true;
      setIsPanning(true);
      setCamera({ ...gesture.camera, x: gesture.camera.x + dx, y: gesture.camera.y + dy });
    }
  }

  function cancelGesture() {
    const gesture = gestureRef.current;
    if (!gesture) return;
    gestureRef.current = null;
    if (gesture.originNodeId && gesture.moved) suppressClickRef.current = gesture.originNodeId;
    if (gesture.kind === "pan" && gesture.worldId === currentWorldIdRef.current) setCamera(gesture.camera);
    setDragPreview(null);
    setConnectPreview(null);
    setIsPanning(false);
    if (gesture) {
      try { gesture.captureTarget.releasePointerCapture(gesture.pointerId); } catch { /* Optional in test DOMs. */ }
    }
  }

  function finishDrag(event: PointerEvent<SVGSVGElement>) {
    const gesture = gestureRef.current;
    if (!gesture || gesture.pointerId !== event.pointerId) return;
    updateGesture(event);
    gestureRef.current = null;
    setIsPanning(false);
    setConnectPreview(null);
    if (gesture.moved && gesture.originNodeId) suppressClickRef.current = gesture.originNodeId;
    if (gesture.moved && gesture.kind === "connect" && gesture.sourceId) {
      const targetId = nodeAt(graphPointAt(event.clientX, event.clientY, gesture.camera));
      if (targetId) emitConnectRequest(gesture.sourceId, targetId);
    } else if (!gesture.moved && gesture.kind === "pan" && !gesture.originNodeId) {
      openPalette(graphPointAt(event.clientX, event.clientY, gesture.camera), svgRef.current);
    } else if (gesture.moved && gesture.node && onMoveObjects && !interactionDisabled) {
      suppressClickRef.current = gesture.node.id;
      const x = Math.max(0, Math.min(MAX_NODE_COORDINATE, gesture.node.x + (event.clientX - gesture.pointerX) * gesture.scaleX / gesture.camera.zoom));
      const y = Math.max(0, Math.min(MAX_NODE_COORDINATE, gesture.node.y + (event.clientY - gesture.pointerY) * gesture.scaleY / gesture.camera.zoom));
      void runLayout({ [gesture.node.id]: { x, y } });
    } else setDragPreview(null);
    try { gesture.captureTarget.releasePointerCapture(event.pointerId); } catch { /* Optional in test DOMs. */ }
  }

  function moveSelected(id: LocalObjectId, dx: number, dy: number) {
    if (!onMoveObjects || busy) return;
    const node = projection.nodes.find((candidate) => candidate.id === id);
    if (!node) return;
    const x = Math.max(0, Math.min(MAX_NODE_COORDINATE, node.x + dx));
    const y = Math.max(0, Math.min(MAX_NODE_COORDINATE, node.y + dy));
    void runLayout({ [id]: { x, y } });
  }

  function onNodeKeyDown(event: KeyboardEvent<SVGGElement>, id: LocalObjectId) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      selectNode(id);
    } else if (event.key === "ArrowLeft" || event.key === "ArrowRight" || event.key === "ArrowUp" || event.key === "ArrowDown") {
      if (fullCorpus && !moveNodesMode) return; // Let the canvas pan, without a layout write.
      event.preventDefault();
      event.stopPropagation();
      const amount = event.shiftKey ? 24 : 8;
      moveSelected(id, event.key === "ArrowLeft" ? -amount : event.key === "ArrowRight" ? amount : 0,
        event.key === "ArrowUp" ? -amount : event.key === "ArrowDown" ? amount : 0);
    }
  }

  async function submitRename(event: FormEvent) {
    event.preventDefault();
    if (!renameId || !onRenameObject || interactionDisabled) return;
    const submittedId = renameId;
    const submittedValue = renameValue;
    const submittedVersion = renameVersionRef.current;
    const submittedDraft = { field: "rename" as const, token: editorDraftRef.current.renameToken };
    const submittedGeneration = worldGenerationRef.current;
    const result = await runSemantic(() => onRenameObject(record, submittedId, submittedValue), submittedDraft);
    if (result?.status === "committed" && currentWorldIdRef.current === record.snapshot.worldId && worldGenerationRef.current === submittedGeneration && renameVersionRef.current === submittedVersion && renameId === submittedId) {
      setRenameId(null);
      setRenameValue("");
      publishEditorDraft({ renameId: null, renameValue: "" });
    }
  }

  async function submitObject(event: FormEvent) {
    event.preventDefault();
    if (!onCreateObject || interactionDisabled) return;
    const input = { name: objectName, kind: objectKind };
    const submittedVersion = objectNameVersionRef.current;
    const submittedDraft = { field: "object" as const, token: editorDraftRef.current.objectToken };
    const submittedGeneration = worldGenerationRef.current;
    const result = await runSemantic(() => onCreateObject(record, input), submittedDraft);
    if (result?.status === "committed" && currentWorldIdRef.current === record.snapshot.worldId && worldGenerationRef.current === submittedGeneration && objectNameVersionRef.current === submittedVersion) {
      setObjectName("");
      setShowObjectForm(false);
      publishEditorDraft({ objectName: "", showObjectForm: false });
    }
  }

  async function submitRelationship(event: FormEvent) {
    event.preventDefault();
    if (!onCreateRelationship || selectedIds.length !== 2 || interactionDisabled) return;
    const input = { fromObjectId: selectedIds[0], toObjectId: selectedIds[1], kind: relationshipKind };
    const submittedVersion = relationshipKindVersionRef.current;
    const submittedDraft = { field: "relationship" as const, token: editorDraftRef.current.relationshipToken };
    const submittedGeneration = worldGenerationRef.current;
    const result = await runSemantic(() => onCreateRelationship(record, input), submittedDraft);
    if (result?.status === "committed" && currentWorldIdRef.current === record.snapshot.worldId && worldGenerationRef.current === submittedGeneration && relationshipKindVersionRef.current === submittedVersion) {
      setRelationshipKind("");
      setShowRelationshipForm(false);
      publishEditorDraft({ relationshipKind: "", showRelationshipForm: false });
    }
  }

  const handlersRef = useRef({ selectNode, onNodeKeyDown, beginGesture, beginConnectGesture });
  handlersRef.current = { selectNode, onNodeKeyDown, beginGesture, beginConnectGesture };
  const nodeLayer = useMemo(() => projection.nodes.map((node) => <GraphBubble
    key={node.id} node={node} position={positions.get(node.id)!} selected={selectedIds.includes(node.id)}
    isConnectTarget={connectPreview !== null && connectTargetId === node.id} nodeShape={nodeShape}
    fullCorpus={fullCorpus} canConnect={Boolean(onConnectRequest)} handlersRef={handlersRef} suppressClickRef={suppressClickRef} />),
    [projection.nodes, selectedIds, positions, connectPreview !== null, connectTargetId, nodeShape, fullCorpus, Boolean(onConnectRequest)]);
  const edgeLayer = useMemo(() => renderedEdges.map(({ edge, geometry, box }) => {
              const label = accessibleRelationshipLabel(edge, nodeNames);
              return (
              <g className={`world-graph-canvas__edge${selectedIds.includes(edge.fromObjectId) || selectedIds.includes(edge.toObjectId) ? " is-selected" : ""}`} key={edge.id} data-edge-id={edge.id} role="img" aria-label={label}>
                <path d={geometry.path} markerEnd={`url(#${markerId})`} />
                <rect className="world-graph-canvas__edge-label" x={geometry.labelX - box.width / 2}
                  y={geometry.labelY - box.height / 2}
                  width={box.width}
                  height={box.height} rx="6" />
                <text x={geometry.labelX} y={geometry.labelY}>
                  {box.lines.map((line, index, lines) => <tspan key={index} x={geometry.labelX} y={geometry.labelY + (index - (lines.length - 1) / 2) * 16 + 4}>{line}</tspan>)}
                </text>
                <title>{label}</title>
              </g>
            );}), [renderedEdges, nodeNames, markerId, selectedIds]);

  return (
    <section id={canvasId} tabIndex={canvasId ? -1 : undefined} className={`world-graph-canvas${fullCorpus ? " world-graph-canvas--full" : ""}`} aria-label="Local World graph canvas" aria-busy={busy}
      onKeyDown={(event) => {
        if (event.key !== "Escape") return;
        if (!palette && !gestureRef.current) return;
        cancelGesture();
        if (palette) closePalette(true);
        event.preventDefault();
        event.stopPropagation();
      }}>
      <div className="world-graph-canvas__toolbar" aria-label="Graph editing tools">
        {onCanvasCreateRequest && creationKinds?.length ? <button type="button" disabled={busy || interactionDisabled} onClick={openPaletteAtCanvasCenter}>Place node</button> : null}
        {onConnectRequest && selectedIds.length === 2 ? <button type="button" disabled={busy || interactionDisabled}
          onClick={() => emitConnectRequest(selectedIds[0], selectedIds[1])}>Connect selected nodes</button> : null}
        {onCreateObject ? <button type="button" disabled={busy || interactionDisabled} onClick={() => {
          const show = !showObjectForm;
          if (!show) setObjectName("");
          setShowObjectForm(show);
          publishEditorDraft({ showObjectForm: show, objectName: show ? objectName : "" });
        }}>Add object</button> : null}
        {onCreateRelationship && selectedIds.length === 2 ? <button type="button" disabled={busy || interactionDisabled} onClick={() => {
          const show = !showRelationshipForm;
          if (!show) setRelationshipKind("");
          setShowRelationshipForm(show);
          publishEditorDraft({ selectedIds, showRelationshipForm: show, relationshipKind: show ? relationshipKind : "" });
        }}>Connect selected objects</button> : null}
        {onRenameObject && selectedObject ? <button type="button" disabled={busy || interactionDisabled} onClick={() => {
          renameVersionRef.current += 1;
          setRenameId(selectedObject.id);
          setRenameValue(selectedObject.name);
          publishEditorDraft({ renameId: selectedObject.id, renameValue: selectedObject.name });
        }}>Rename {selectedObject.name}</button> : null}
      </div>

      {showObjectForm && onCreateObject ? (
        <form className="world-graph-canvas__form" onSubmit={submitObject}>
          <label>Object name<input autoFocus value={objectName} onChange={(event) => { objectNameVersionRef.current += 1; setObjectName(event.target.value); publishEditorDraft({ objectName: event.target.value, objectKind }); }} /></label>
          <label>Type<select value={objectKind} onChange={(event) => { objectNameVersionRef.current += 1; setObjectKind(event.target.value); publishEditorDraft({ objectName, objectKind: event.target.value }); }}><option value="person">Person</option><option value="location">Location</option><option value="event">Event</option><option value="faction">Faction</option></select></label>
          <button type="submit" disabled={busy || interactionDisabled || !objectName.trim()}>Create object</button>
          <button type="button" onClick={() => { setObjectName(""); setShowObjectForm(false); publishEditorDraft({ objectName: "", showObjectForm: false }); }}>Cancel</button>
        </form>
      ) : null}
      {showRelationshipForm && onCreateRelationship && selectedIds.length === 2 ? (
        <form className="world-graph-canvas__form" onSubmit={submitRelationship}>
          <label>Relationship label<input autoFocus value={relationshipKind} onChange={(event) => { relationshipKindVersionRef.current += 1; setRelationshipKind(event.target.value); publishEditorDraft({ selectedIds, showRelationshipForm: true, relationshipKind: event.target.value }); }} /></label>
          <button type="submit" disabled={busy || interactionDisabled || !relationshipKind.trim()}>Create relationship</button>
          <button type="button" onClick={() => { setRelationshipKind(""); setShowRelationshipForm(false); publishEditorDraft({ showRelationshipForm: false, relationshipKind: "" }); }}>Cancel</button>
        </form>
      ) : null}
      {renameId && onRenameObject ? (
        <form className="world-graph-canvas__form" onSubmit={submitRename}>
          <label>New name<input autoFocus value={renameValue} onChange={(event) => { renameVersionRef.current += 1; setRenameValue(event.target.value); publishEditorDraft({ renameValue: event.target.value }); }} /></label>
          <button type="submit" disabled={busy || interactionDisabled || !renameValue.trim()}>Save name</button>
          <button type="button" onClick={() => { setRenameId(null); setRenameValue(""); publishEditorDraft({ renameId: null, renameValue: "" }); }}>Cancel</button>
        </form>
      ) : null}

      <div className="world-graph-canvas__view-tools" aria-label="Graph view controls">
        <button type="button" aria-label="Zoom out" disabled={camera.zoom <= (fullCorpus ? Math.min(MIN_ZOOM, fittedCamera().zoom) : MIN_ZOOM)} onClick={() => zoomBy(1 / 1.25)}>−</button>
        <span aria-label="Graph zoom">{Math.round(camera.zoom * 100)}%</span>
        <button type="button" aria-label="Zoom in" disabled={camera.zoom >= MAX_ZOOM} onClick={() => zoomBy(1.25)}>+</button>
        <button type="button" onClick={fitGraph}>Fit graph</button>
        <button type="button" onClick={() => zoomBy(1 / camera.zoom)}>100%</button>
        {fullCorpus ? <div className="world-graph-canvas__drag-mode" role="group" aria-label="Graph drag mode">
          <button type="button" aria-pressed={!moveNodesMode} onClick={() => { cancelGesture(); setMoveNodesMode(false); }}>Pan graph</button>
          <button type="button" aria-pressed={moveNodesMode} disabled={!onMoveObjects || busy || interactionDisabled}
            onClick={() => { cancelGesture(); setMoveNodesMode(true); }}>Move nodes</button>
        </div> : null}
      </div>
      {fullCorpus ? <>
        <label className="world-graph-canvas__visibility"><input type="checkbox" checked={showUnconnected}
          onChange={(event) => { cancelGesture(); setUnconnectedVisibility({ worldId: record.snapshot.worldId, show: event.target.checked }); }} />
          Show objects without listed relationships ({projection.hiddenUnconnectedNodes} hidden)
        </label>
        {!projection.nodes.length && isolatedCount > 0 ? <p role="status">No connected objects in the loaded snapshot. Show objects without listed relationships to explore them, or find an object with search.</p> : null}
        <div className="world-graph-canvas__legend" aria-label="Object type colors">{legend.map((kind) => <span key={kind}><i aria-hidden="true" style={{ backgroundColor: kindColor(kind) }} />{kind}</span>)}</div>
        <p className="world-graph-canvas__overview-note">{projection.nodes.length} loaded objects · {projection.edges.length} real relationships shown. {isolatedCount} loaded objects have no listed connections. Zoom in for names, relationship labels and connectors. Color shows explicit object type. Bubble area grows logarithmically with relationships in loaded snapshot (radius 32–56, capped at 100 relationships); position is only an arrangement.</p>
      </> : null}
      <p className="world-graph-canvas__hint" id={`${markerId}-help`}>
        {fullCorpus ? moveNodesMode
          ? "Drag an object to move it, or empty canvas to pan. Choose Pan graph to navigate without moving objects. "
          : "Drag anywhere to pan. Click an object to select it. Choose Move nodes to rearrange objects. "
          : "Drag the background to pan. Drag an object to move it. "}
        {onCanvasCreateRequest ? "Click blank canvas to place a node, or use Place node with a keyboard." : "Select two objects to connect them."}
        {onConnectRequest ? " Drag a node's gold connector dot to another node, or select two nodes and use Connect selected nodes." : ""}
        {" Focus the canvas and use arrow keys to pan, +/− to zoom, or 0 to fit."}
        {fullCorpus ? " A focused object's arrow keys pan in Pan graph mode, and move that object in Move nodes mode." : ""}
      </p>
      <div className="world-graph-canvas__viewport">
        <svg
          ref={svgRef}
          className={`world-graph-canvas__svg${isPanning ? " is-panning" : ""}`}
          data-drag-mode={fullCorpus && !moveNodesMode ? "pan" : "move"}
          viewBox={`0 0 ${viewport.width} ${viewport.height}`}
          tabIndex={0}
          aria-describedby={`${markerId}-help`}
          role="group"
          aria-label={`${record.snapshot.title} world graph`}
          onPointerDown={(event) => { if (fullCorpus || event.target === event.currentTarget) beginGesture(event); }}
          onPointerMove={updateGesture}
          onPointerUp={finishDrag}
          onPointerCancel={cancelGesture}
          onLostPointerCapture={cancelGesture}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              if (gestureRef.current) {
                event.preventDefault();
                event.stopPropagation();
                cancelGesture();
              }
              return;
            }
            const focusedNode = fullCorpus && event.target instanceof Element && event.target.closest("[data-node-id]");
            if (event.target !== event.currentTarget && !focusedNode) return;
            if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) {
              event.preventDefault();
              manualCameraRef.current = true;
              const amount = event.shiftKey ? 96 : 32;
              setCamera((current) => ({ ...current,
                x: current.x + (event.key === "ArrowLeft" ? amount : event.key === "ArrowRight" ? -amount : 0),
                y: current.y + (event.key === "ArrowUp" ? amount : event.key === "ArrowDown" ? -amount : 0) }));
            } else if (["+", "=", "-", "0"].includes(event.key)) {
              event.preventDefault();
              if (event.key === "0") fitGraph();
              else zoomBy(event.key === "-" ? 1 / 1.25 : 1.25);
            }
          }}
        >
          <defs><marker id={markerId} markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><path d="M0,0 L9,3.5 L0,7 z" /></marker></defs>
          <g className="world-graph-canvas__scene" data-testid="graph-scene" data-detail={camera.zoom >= 0.9 ? "relationships" : camera.zoom >= 0.45 ? "names" : "overview"} transform={`translate(${camera.x} ${camera.y}) scale(${camera.zoom})`}>
          <g className="world-graph-canvas__nodes" aria-label="World objects">
            {nodeLayer}
          </g>
          <g className="world-graph-canvas__edges" aria-label="Relationships">
            {edgeLayer}
            {connectPreview ? (() => {
              const source = positions.get(connectPreview.sourceId);
              if (!source) return null;
              const start = nodeShape === "circle"
                ? { x: source.x + CIRCLE_RADIUS + (source.radius ?? CIRCLE_RADIUS) - 2, y: source.y + CIRCLE_RADIUS }
                : { x: source.x + NODE_WIDTH - 3, y: source.y + NODE_HEIGHT / 2 };
              const end = connectPreview.point;
              const bend = Math.max(36, Math.abs(end.x - start.x) * 0.42) * Math.sign(end.x - start.x || 1);
              return <path className="world-graph-canvas__connect-preview" data-testid="connect-preview"
                d={`M ${start.x} ${start.y} C ${start.x + bend} ${start.y} ${end.x - bend} ${end.y} ${end.x} ${end.y}`}
                markerEnd={`url(#${markerId})`} />;
            })() : null}
          </g>
          </g>
        </svg>
        {palette && paletteScreen && creationKinds?.length && typeof document !== "undefined" ? createPortal(
          <div ref={paletteRef} className="world-graph-canvas__palette" role="group" aria-label="Choose node type"
            style={{ position: "fixed", left: paletteScreen.x, top: paletteScreen.y, maxWidth: paletteScreen.maxWidth, maxHeight: paletteScreen.maxHeight }} data-testid="node-palette"
            data-position-x={palette.point.x} data-position-y={palette.point.y}>
          <div className="world-graph-canvas__palette-header">
            <span className="world-graph-canvas__palette-title">Place a node here</span>
          </div>
          <div className="world-graph-canvas__palette-choices" aria-label="Node types">
            {creationKinds.map((item, index) => <button type="button" key={item.kind} ref={index === 0 ? paletteFirstActionRef : undefined}
              onClick={() => {
                onCanvasCreateRequest?.({ kind: item.kind, position: palette.point });
                closePalette();
                setStatus(`${item.label} draft opened.`);
              }}>{item.label}</button>)}
          </div>
          <div className="world-graph-canvas__palette-actions">
            <button type="button" className="world-graph-canvas__palette-cancel" aria-keyshortcuts="Escape" onClick={() => closePalette(true)}>Cancel placement</button>
          </div>
          </div>, document.body) : null}
      </div>

      <div className="world-graph-canvas__feedback" role="status" aria-live="polite">
        {status || (projection.nodes.length || projection.omittedNodes
          ? showSummaryCounts ? `${projection.nodes.length}${projection.omittedNodes ? " displayed" : ""} objects · ${projection.edges.length}${projection.omittedEdges ? " displayed" : ""} relationships` : ""
          : projection.hiddenUnconnectedNodes ? `${projection.hiddenUnconnectedNodes} loaded objects without listed relationships are hidden.`
          : "This World has no objects yet. Add an object to begin.")}
      </div>
      {projection.omittedNodes || projection.hiddenRelationships ? <p className="world-graph-canvas__diagnostic">Bounded canvas: {projection.nodes.length} of {record.snapshot.objects.length} loaded objects and {projection.edges.length} of {record.snapshot.relationships.length} loaded relationships shown. {projection.omittedNodes} objects and {projection.hiddenRelationships} valid relationships are outside this view.</p> : null}
      {projection.invalidRelationships ? <p className="world-graph-canvas__diagnostic">{projection.invalidRelationships} relationships reference objects absent from the loaded graph.</p> : null}
      {projection.diagnostics.length ? <ul className="world-graph-canvas__diagnostics" role="status" aria-label="Graph projection diagnostics">{projection.diagnostics.map((message) => <li key={message}>{message}</li>)}</ul> : null}
      {projection.omittedDiagnostics ? <p className="world-graph-canvas__diagnostic">{projection.omittedDiagnostics} additional missing-endpoint details are not listed.</p> : null}
    </section>
  );
}
