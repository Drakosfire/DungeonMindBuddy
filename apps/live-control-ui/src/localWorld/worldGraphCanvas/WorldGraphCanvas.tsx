import { useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent, type PointerEvent } from "react";
import type {
  CommitSemanticResult,
  LocalObjectId,
  LocalWorldRecord,
  WriteLayoutResult,
} from "../localWorldRepository";
import { projectLocalWorldGraph, type GraphProjectionOptions, type ProjectedGraphEdge } from "./graphProjection";
import type { NewLocalGraphObject, NewLocalGraphRelationship } from "./localWorldGraphAdapter";
import "./worldGraphCanvas.css";

const WIDTH = 960;
const HEIGHT = 520;
const MIN_ZOOM = 0.15;
const MAX_ZOOM = 2.5;
const MAX_NODE_COORDINATE = 6000;
const NODE_WIDTH = 168;
const NODE_HEIGHT = 76;

export interface WorldGraphCanvasProps {
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
  readonly kind: "node" | "pan";
  readonly captureTarget: Element;
  readonly pointerId: number;
  readonly pointerX: number;
  readonly pointerY: number;
  readonly camera: Camera;
  readonly scaleX: number;
  readonly scaleY: number;
  readonly node?: { readonly id: LocalObjectId; readonly x: number; readonly y: number };
  moved: boolean;
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
}

function edgeGeometry(
  edge: ProjectedGraphEdge,
  positions: ReadonlyMap<string, { x: number; y: number }>,
  parallelIndex: number,
  parallelCount: number,
  labelWidth: number,
  labelHeight: number,
): EdgeGeometry {
  const from = positions.get(edge.fromObjectId)!;
  const to = positions.get(edge.toObjectId)!;
  if (edge.fromObjectId === edge.toObjectId) {
    // Concentric loops put their plates side by side, with no shared label band.
    const spread = parallelIndex * (labelWidth + 12) * 4 / 3;
    const start = { x: from.x + NODE_WIDTH + 5, y: from.y + 15 };
    const end = { x: from.x + NODE_WIDTH + 5, y: from.y + NODE_HEIGHT - 15 };
    const controlOne = { x: from.x + NODE_WIDTH + 76 + Math.abs(spread), y: from.y - 42 };
    const controlTwo = { x: from.x + NODE_WIDTH + 76 + Math.abs(spread), y: from.y + NODE_HEIGHT + 42 };
    return {
      path: `M ${start.x} ${start.y} C ${controlOne.x} ${controlOne.y} ${controlTwo.x} ${controlTwo.y} ${end.x} ${end.y}`,
      labelX: (start.x + 3 * controlOne.x + 3 * controlTwo.x + end.x) / 8 + 4,
      labelY: (start.y + 3 * controlOne.y + 3 * controlTwo.y + end.y) / 8,
    };
  }
  const start = { x: from.x + NODE_WIDTH / 2, y: from.y + NODE_HEIGHT / 2 };
  const end = { x: to.x + NODE_WIDTH / 2, y: to.y + NODE_HEIGHT / 2 };
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
  function boundary(center: { x: number; y: number }, toward: { x: number; y: number }) {
    const vx = toward.x - center.x;
    const vy = toward.y - center.y;
    const extent = Math.max(Math.abs(vx) / (NODE_WIDTH / 2 + 5), Math.abs(vy) / (NODE_HEIGHT / 2 + 5));
    return extent > 0 ? { x: center.x + vx / extent, y: center.y + vy / extent } : center;
  }
  const pathStart = boundary(start, control);
  const pathEnd = boundary(end, control);
  // Tight, user-arranged nodes need a label outside their overlap rather than hidden under a card.
  const tight = Math.abs(dx) < NODE_WIDTH + 160 && Math.abs(dy) < NODE_HEIGHT + 70;
  return {
    path: `M ${pathStart.x} ${pathStart.y} Q ${control.x} ${control.y} ${pathEnd.x} ${pathEnd.y}`,
    labelX: (start.x + 2 * control.x + end.x) / 4,
    labelY: (start.y + 2 * control.y + end.y) / 4 - (tight ? NODE_HEIGHT + 30 : 0),
  };
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
}: WorldGraphCanvasProps) {
  const projection = projectLocalWorldGraph(record, projectionOptions);
  const markerId = `world-graph-arrow-${useId().replace(/:/g, "")}`;
  const initialDraft = editorDraftState?.draft ?? emptyEditorDraft(editorDraftState?.version ?? 0);
  const [selectedIds, setSelectedIds] = useState<LocalObjectId[]>([...initialDraft.selectedIds]);
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
  const [camera, setCamera] = useState<Camera>({ x: 0, y: 0, zoom: 1 });
  const [dragPreview, setDragPreview] = useState<{ id: LocalObjectId; x: number; y: number } | null>(null);
  const [isPanning, setIsPanning] = useState(false);
  const gestureRef = useRef<CanvasGesture | null>(null);
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
    gestureRef.current = null;
    suppressClickRef.current = null;
    manualCameraRef.current = false;
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
  const positions = new Map(projection.nodes.map((node) => [node.id,
    dragPreview?.id === node.id ? { x: dragPreview.x, y: dragPreview.y } : { x: node.x, y: node.y }]));

  function fittedCamera(): Camera {
    if (!projection.nodes.length) return { x: 0, y: 0, zoom: 1 };
    const xs = projection.nodes.map((node) => node.x);
    const ys = projection.nodes.map((node) => node.y);
    const left = Math.min(...xs) - 72;
    const top = Math.min(...ys) - 80;
    const loopGroups = new Map<string, { count: number; width: number }>();
    for (const edge of projection.edges) {
      if (edge.fromObjectId !== edge.toObjectId) continue;
      const previous = loopGroups.get(edge.fromObjectId) ?? { count: 0, width: 0 };
      loopGroups.set(edge.fromObjectId, { count: previous.count + 1, width: Math.max(previous.width, labelBox(edge.kind).width) });
    }
    const rightPadding = Math.max(120, ...[...loopGroups.values()].map(({ count, width }) => 70 + count * (width + 12)));
    const width = Math.max(...xs) + NODE_WIDTH + rightPadding - left;
    const height = Math.max(...ys) + NODE_HEIGHT + 80 - top;
    const zoom = Math.max(MIN_ZOOM, Math.min(1, viewport.width / width, viewport.height / height));
    return { x: (viewport.width - width * zoom) / 2 - left * zoom,
      y: (viewport.height - height * zoom) / 2 - top * zoom, zoom };
  }

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(([entry]) => {
      if (entry.contentRect.width > 0 && entry.contentRect.height > 0) {
        setViewport({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    observer.observe(svg);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!manualCameraRef.current) setCamera(fittedCamera());
    // Fit initial visibility and responsive size, never re-fit after user pan/zoom or node edits.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewport.width, viewport.height, record.snapshot.worldId]);

  useEffect(() => {
    // A new controlled revision invalidates an unfinished drag, rather than saving it over newer layout.
    gestureRef.current = null;
    setDragPreview(null);
    setIsPanning(false);
  }, [record.snapshot.worldId, record.localRevision, record.layoutRevision]);

  function zoomBy(factor: number) {
    cancelGesture();
    manualCameraRef.current = true;
    setCamera((current) => {
      const zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, current.zoom * factor));
      const ratio = zoom / current.zoom;
      return { zoom, x: viewport.width / 2 - (viewport.width / 2 - current.x) * ratio,
        y: viewport.height / 2 - (viewport.height / 2 - current.y) * ratio };
    });
  }
  const nodeNames = new Map(projection.nodes.map((node) => [node.id, node.name]));
  const edgeGroups = new Map<string, { count: number; width: number; height: number }>();
  for (const edge of projection.edges) {
    const key = [edge.fromObjectId, edge.toObjectId].sort().join("\u0000");
    const previous = edgeGroups.get(key) ?? { count: 0, width: 0, height: 0 };
    const box = labelBox(edge.kind);
    edgeGroups.set(key, { count: previous.count + 1, width: Math.max(previous.width, box.width), height: Math.max(previous.height, box.height) });
  }
  const edgeGroupIndexes = new Map<string, number>();
  const renderedEdges = projection.edges.map((edge) => {
    const key = [edge.fromObjectId, edge.toObjectId].sort().join("\u0000");
    const index = edgeGroupIndexes.get(key) ?? 0;
    edgeGroupIndexes.set(key, index + 1);
    const group = edgeGroups.get(key)!;
    return { edge, box: labelBox(edge.kind), geometry: edgeGeometry(edge, positions, index, group.count, group.width, group.height) };
  });

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
    if (!onMoveObjects || busy) return;
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
    if ((event.button ?? 0) !== 0 || gestureRef.current || (node && (busy || !onMoveObjects))) return;
    event.preventDefault();
    event.stopPropagation();
    suppressClickRef.current = null;
    const svg = svgRef.current;
    const rect = svg?.getBoundingClientRect();
    gestureRef.current = { kind: node ? "node" : "pan", captureTarget: event.currentTarget, pointerId: event.pointerId,
      pointerX: event.clientX, pointerY: event.clientY, camera,
      scaleX: rect?.width ? viewport.width / rect.width : 1,
      scaleY: rect?.height ? viewport.height / rect.height : 1, node, moved: false };
    try { event.currentTarget.setPointerCapture(event.pointerId); } catch { /* Optional in test DOMs. */ }
  }

  function updateGesture(event: PointerEvent<SVGSVGElement>) {
    const gesture = gestureRef.current;
    if (!gesture || gesture.pointerId !== event.pointerId) return;
    const dx = (event.clientX - gesture.pointerX) * gesture.scaleX;
    const dy = (event.clientY - gesture.pointerY) * gesture.scaleY;
    if (Math.abs(event.clientX - gesture.pointerX) + Math.abs(event.clientY - gesture.pointerY) > 4) gesture.moved = true;
    if (!gesture.moved) return;
    if (gesture.node) {
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
    if (gesture.node && gesture.moved) suppressClickRef.current = gesture.node.id;
    if (gesture?.kind === "pan") setCamera(gesture.camera);
    setDragPreview(null);
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
    if (gesture.moved && gesture.node && onMoveObjects) {
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
      event.preventDefault();
      const amount = event.shiftKey ? 24 : 8;
      moveSelected(id, event.key === "ArrowLeft" ? -amount : event.key === "ArrowRight" ? amount : 0,
        event.key === "ArrowUp" ? -amount : event.key === "ArrowDown" ? amount : 0);
    }
  }

  async function submitRename(event: FormEvent) {
    event.preventDefault();
    if (!renameId || !onRenameObject) return;
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
    if (!onCreateObject) return;
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
    if (!onCreateRelationship || selectedIds.length !== 2) return;
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

  return (
    <section className="world-graph-canvas" aria-label="Local World graph canvas" aria-busy={busy}>
      <div className="world-graph-canvas__toolbar" aria-label="Graph editing tools">
        {onCreateObject ? <button type="button" disabled={busy} onClick={() => {
          const show = !showObjectForm;
          if (!show) setObjectName("");
          setShowObjectForm(show);
          publishEditorDraft({ showObjectForm: show, objectName: show ? objectName : "" });
        }}>Add object</button> : null}
        {onCreateRelationship && selectedIds.length === 2 ? <button type="button" disabled={busy} onClick={() => {
          const show = !showRelationshipForm;
          if (!show) setRelationshipKind("");
          setShowRelationshipForm(show);
          publishEditorDraft({ selectedIds, showRelationshipForm: show, relationshipKind: show ? relationshipKind : "" });
        }}>Connect selected objects</button> : null}
        {onRenameObject && selectedObject ? <button type="button" disabled={busy} onClick={() => {
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
          <button type="submit" disabled={busy || !objectName.trim()}>Create object</button>
          <button type="button" onClick={() => { setObjectName(""); setShowObjectForm(false); publishEditorDraft({ objectName: "", showObjectForm: false }); }}>Cancel</button>
        </form>
      ) : null}
      {showRelationshipForm && onCreateRelationship && selectedIds.length === 2 ? (
        <form className="world-graph-canvas__form" onSubmit={submitRelationship}>
          <label>Relationship label<input autoFocus value={relationshipKind} onChange={(event) => { relationshipKindVersionRef.current += 1; setRelationshipKind(event.target.value); publishEditorDraft({ selectedIds, showRelationshipForm: true, relationshipKind: event.target.value }); }} /></label>
          <button type="submit" disabled={busy || !relationshipKind.trim()}>Create relationship</button>
          <button type="button" onClick={() => { setRelationshipKind(""); setShowRelationshipForm(false); publishEditorDraft({ showRelationshipForm: false, relationshipKind: "" }); }}>Cancel</button>
        </form>
      ) : null}
      {renameId && onRenameObject ? (
        <form className="world-graph-canvas__form" onSubmit={submitRename}>
          <label>New name<input autoFocus value={renameValue} onChange={(event) => { renameVersionRef.current += 1; setRenameValue(event.target.value); publishEditorDraft({ renameValue: event.target.value }); }} /></label>
          <button type="submit" disabled={busy || !renameValue.trim()}>Save name</button>
          <button type="button" onClick={() => { setRenameId(null); setRenameValue(""); publishEditorDraft({ renameId: null, renameValue: "" }); }}>Cancel</button>
        </form>
      ) : null}

      <div className="world-graph-canvas__view-tools" aria-label="Graph view controls">
        <button type="button" aria-label="Zoom out" disabled={camera.zoom <= MIN_ZOOM} onClick={() => zoomBy(1 / 1.25)}>−</button>
        <span aria-label="Graph zoom">{Math.round(camera.zoom * 100)}%</span>
        <button type="button" aria-label="Zoom in" disabled={camera.zoom >= MAX_ZOOM} onClick={() => zoomBy(1.25)}>+</button>
        <button type="button" onClick={() => { cancelGesture(); manualCameraRef.current = true; setCamera(fittedCamera()); }}>Fit graph</button>
        <button type="button" onClick={() => zoomBy(1 / camera.zoom)}>100%</button>
      </div>
      <p className="world-graph-canvas__hint" id={`${markerId}-help`}>Drag the background to pan. Drag an object to move it. Select two objects to connect them. Focus the canvas and use arrow keys to pan, +/− to zoom, or 0 to fit.</p>
      <div className="world-graph-canvas__viewport">
        <svg
          ref={svgRef}
          className={`world-graph-canvas__svg${isPanning ? " is-panning" : ""}`}
          viewBox={`0 0 ${viewport.width} ${viewport.height}`}
          tabIndex={0}
          aria-describedby={`${markerId}-help`}
          role="group"
          aria-label={`${record.snapshot.title} world graph`}
          onPointerDown={(event) => { if (event.target === event.currentTarget) beginGesture(event); }}
          onPointerMove={updateGesture}
          onPointerUp={finishDrag}
          onPointerCancel={cancelGesture}
          onLostPointerCapture={cancelGesture}
          onKeyDown={(event) => {
            if (event.key === "Escape") { cancelGesture(); return; }
            if (event.target !== event.currentTarget) return;
            if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) {
              event.preventDefault();
              manualCameraRef.current = true;
              const amount = event.shiftKey ? 96 : 32;
              setCamera((current) => ({ ...current,
                x: current.x + (event.key === "ArrowLeft" ? amount : event.key === "ArrowRight" ? -amount : 0),
                y: current.y + (event.key === "ArrowUp" ? amount : event.key === "ArrowDown" ? -amount : 0) }));
            } else if (["+", "=", "-", "0"].includes(event.key)) {
              event.preventDefault();
              if (event.key === "0") { cancelGesture(); manualCameraRef.current = true; setCamera(fittedCamera()); }
              else zoomBy(event.key === "-" ? 1 / 1.25 : 1.25);
            }
          }}
        >
          <defs><marker id={markerId} markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><path d="M0,0 L9,3.5 L0,7 z" /></marker></defs>
          <g className="world-graph-canvas__scene" data-testid="graph-scene" transform={`translate(${camera.x} ${camera.y}) scale(${camera.zoom})`}>
          <g className="world-graph-canvas__nodes" aria-label="World objects">
            {projection.nodes.map((node) => {
              const selected = selectedIds.includes(node.id);
              const position = positions.get(node.id)!;
              return (
                <g
                  key={node.id}
                  className={`world-graph-canvas__node${selected ? " is-selected" : ""}`}
                  transform={`translate(${position.x} ${position.y})`}
                  role="button"
                  tabIndex={0}
                  aria-pressed={selected}
                  aria-label={`${node.name}, ${node.kind}`}
                  data-node-id={node.id}
                  onClick={() => {
                    if (suppressClickRef.current === node.id) { suppressClickRef.current = null; return; }
                    selectNode(node.id);
                  }}
                  onKeyDown={(event) => onNodeKeyDown(event, node.id)}
                  onPointerDown={(event) => { event.stopPropagation(); beginGesture(event, node); }}
                >
                  <rect width={NODE_WIDTH} height={NODE_HEIGHT} rx="12" />
                  <text className="world-graph-canvas__node-kind" x="14" y="22">{node.kind}</text>
                  <text className="world-graph-canvas__node-name" x="14" y="49">{node.name.length > 22 ? `${node.name.slice(0, 21)}…` : node.name}</text>
                </g>
              );
            })}
          </g>
          <g className="world-graph-canvas__edges" aria-label="Relationships">
            {renderedEdges.map(({ edge, geometry, box }) => {
              const label = accessibleRelationshipLabel(edge, nodeNames);
              return (
              <g className="world-graph-canvas__edge" key={edge.id} data-edge-id={edge.id} role="img" aria-label={label}>
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
            );})}
          </g>
          </g>
        </svg>
      </div>

      <div className="world-graph-canvas__feedback" role="status" aria-live="polite">
        {status || (projection.nodes.length ? `${projection.nodes.length} objects · ${projection.edges.length} relationships` : "This World has no objects yet. Add an object to begin.")}
      </div>
      {projection.omittedNodes || projection.omittedEdges ? <p className="world-graph-canvas__diagnostic">Showing a bounded view. {projection.omittedNodes} objects and {projection.omittedEdges} relationships omitted.</p> : null}
      {projection.diagnostics.length ? <ul className="world-graph-canvas__diagnostics" role="status" aria-label="Graph projection diagnostics">{projection.diagnostics.map((message) => <li key={message}>{message}</li>)}</ul> : null}
      {projection.omittedDiagnostics || projection.unexaminedRelationships ? (
        <p className="world-graph-canvas__diagnostic">Relationship inspection was bounded: {projection.omittedDiagnostics} additional integrity warnings were not listed and {projection.unexaminedRelationships} relationships were not checked.</p>
      ) : null}
    </section>
  );
}
