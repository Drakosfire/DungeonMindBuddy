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
const HEIGHT = 600;
const NODE_WIDTH = 168;
const NODE_HEIGHT = 76;

export interface WorldGraphCanvasProps {
  readonly record: LocalWorldRecord;
  readonly projectionOptions?: GraphProjectionOptions;
  readonly onRenameObject?: (record: LocalWorldRecord, objectId: LocalObjectId, name: string) => Promise<CommitSemanticResult>;
  readonly onCreateObject?: (record: LocalWorldRecord, input: NewLocalGraphObject) => Promise<CommitSemanticResult>;
  readonly onCreateRelationship?: (record: LocalWorldRecord, input: NewLocalGraphRelationship) => Promise<CommitSemanticResult>;
  readonly onMoveObjects?: (record: LocalWorldRecord, positions: Readonly<Record<string, { readonly x: number; readonly y: number }>>) => Promise<WriteLayoutResult>;
  readonly onSemanticResult?: (result: CommitSemanticResult) => void;
  readonly onLayoutResult?: (result: WriteLayoutResult) => void;
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
): EdgeGeometry {
  const from = positions.get(edge.fromObjectId)!;
  const to = positions.get(edge.toObjectId)!;
  if (edge.fromObjectId === edge.toObjectId) {
    const spread = (parallelIndex - (parallelCount - 1) / 2) * 24;
    const start = { x: from.x + NODE_WIDTH * 0.62, y: from.y + 8 };
    const end = { x: from.x + NODE_WIDTH * 0.62, y: from.y + NODE_HEIGHT - 8 };
    const controlOne = { x: from.x + NODE_WIDTH + 76 + Math.abs(spread), y: from.y - 42 + spread };
    const controlTwo = { x: from.x + NODE_WIDTH + 76 + Math.abs(spread), y: from.y + NODE_HEIGHT + 42 + spread };
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
  const offset = (parallelIndex - (parallelCount - 1) / 2) * 30;
  const control = {
    x: (start.x + end.x) / 2 - (dy / length) * offset,
    y: (start.y + end.y) / 2 + (dx / length) * offset,
  };
  return {
    path: `M ${start.x} ${start.y} Q ${control.x} ${control.y} ${end.x} ${end.y}`,
    labelX: (start.x + 2 * control.x + end.x) / 4,
    labelY: (start.y + 2 * control.y + end.y) / 4,
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
  const [selectedIds, setSelectedIds] = useState<LocalObjectId[]>([]);
  const [renameId, setRenameId] = useState<LocalObjectId | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [showObjectForm, setShowObjectForm] = useState(false);
  const [showRelationshipForm, setShowRelationshipForm] = useState(false);
  const [objectName, setObjectName] = useState("");
  const [objectKind, setObjectKind] = useState("person");
  const [relationshipKind, setRelationshipKind] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [drag, setDrag] = useState<{ id: LocalObjectId; pointerX: number; pointerY: number; x: number; y: number } | null>(null);
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
    setSelectedIds([]);
    setRenameId(null);
    setRenameValue("");
    setShowObjectForm(false);
    setShowRelationshipForm(false);
    setObjectName("");
    setRelationshipKind("");
    setBusy(false);
    setStatus("");
    setDrag(null);
  }
  const dragMoved = useRef(false);

  useEffect(() => {
    instanceGenerationRef.current += 1;
    instanceActiveRef.current = true;
    return () => {
      instanceActiveRef.current = false;
      instanceGenerationRef.current += 1;
    };
  }, []);

  const selectedObject = projection.nodes.find((node) => node.id === selectedIds.at(-1));
  const canvasWidth = Math.max(WIDTH, ...projection.nodes.map((node) => node.x + NODE_WIDTH + 88));
  const canvasHeight = Math.max(HEIGHT, ...projection.nodes.map((node) => node.y + NODE_HEIGHT + 72));
  const positions = new Map(projection.nodes.map((node) => [node.id, { x: node.x, y: node.y }]));
  const nodeNames = new Map(projection.nodes.map((node) => [node.id, node.name]));
  const edgeGroupCounts = new Map<string, number>();
  for (const edge of projection.edges) {
    const key = [edge.fromObjectId, edge.toObjectId].sort().join("\u0000");
    edgeGroupCounts.set(key, (edgeGroupCounts.get(key) ?? 0) + 1);
  }
  const edgeGroupIndexes = new Map<string, number>();
  const renderedEdges = projection.edges.map((edge) => {
    const key = [edge.fromObjectId, edge.toObjectId].sort().join("\u0000");
    const index = edgeGroupIndexes.get(key) ?? 0;
    edgeGroupIndexes.set(key, index + 1);
    return { edge, geometry: edgeGeometry(edge, positions, index, edgeGroupCounts.get(key) ?? 1) };
  });

  function selectNode(id: LocalObjectId) {
    if (showRelationshipForm) relationshipKindVersionRef.current += 1;
    setSelectedIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }

  async function runSemantic(action: () => Promise<CommitSemanticResult>): Promise<CommitSemanticResult | null> {
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
          worldGenerationRef.current === submittedGeneration) setBusy(false);
    }
  }

  function finishDrag(event: PointerEvent<SVGSVGElement>) {
    if (!drag) return;
    if (dragMoved.current && onMoveObjects) {
      const rect = event.currentTarget.getBoundingClientRect();
      const scaleX = rect.width ? canvasWidth / rect.width : 1;
      const scaleY = rect.height ? canvasHeight / rect.height : 1;
      const x = Math.max(0, Math.min(canvasWidth - NODE_WIDTH, drag.x + (event.clientX - drag.pointerX) * scaleX));
      const y = Math.max(0, Math.min(canvasHeight - NODE_HEIGHT, drag.y + (event.clientY - drag.pointerY) * scaleY));
      void runLayout({ [drag.id]: { x, y } });
    }
    setDrag(null);
    dragMoved.current = false;
  }

  function moveSelected(id: LocalObjectId, dx: number, dy: number) {
    if (!onMoveObjects || busy) return;
    const node = projection.nodes.find((candidate) => candidate.id === id);
    if (!node) return;
    const x = Math.max(0, Math.min(canvasWidth - NODE_WIDTH, node.x + dx));
    const y = Math.max(0, Math.min(canvasHeight - NODE_HEIGHT, node.y + dy));
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
    const submittedGeneration = worldGenerationRef.current;
    const result = await runSemantic(() => onRenameObject(record, submittedId, submittedValue));
    if (result?.status === "committed" && currentWorldIdRef.current === record.snapshot.worldId && worldGenerationRef.current === submittedGeneration && renameVersionRef.current === submittedVersion && renameId === submittedId) {
      setRenameId(null);
      setRenameValue("");
    }
  }

  async function submitObject(event: FormEvent) {
    event.preventDefault();
    if (!onCreateObject) return;
    const input = { name: objectName, kind: objectKind };
    const submittedVersion = objectNameVersionRef.current;
    const submittedGeneration = worldGenerationRef.current;
    const result = await runSemantic(() => onCreateObject(record, input));
    if (result?.status === "committed" && currentWorldIdRef.current === record.snapshot.worldId && worldGenerationRef.current === submittedGeneration && objectNameVersionRef.current === submittedVersion) {
      setObjectName("");
      setShowObjectForm(false);
    }
  }

  async function submitRelationship(event: FormEvent) {
    event.preventDefault();
    if (!onCreateRelationship || selectedIds.length !== 2) return;
    const input = { fromObjectId: selectedIds[0], toObjectId: selectedIds[1], kind: relationshipKind };
    const submittedVersion = relationshipKindVersionRef.current;
    const submittedGeneration = worldGenerationRef.current;
    const result = await runSemantic(() => onCreateRelationship(record, input));
    if (result?.status === "committed" && currentWorldIdRef.current === record.snapshot.worldId && worldGenerationRef.current === submittedGeneration && relationshipKindVersionRef.current === submittedVersion) {
      setRelationshipKind("");
      setShowRelationshipForm(false);
    }
  }

  return (
    <section className="world-graph-canvas" aria-label="Local World graph canvas" aria-busy={busy}>
      <div className="world-graph-canvas__toolbar" aria-label="Graph editing tools">
        {onCreateObject ? <button type="button" disabled={busy} onClick={() => setShowObjectForm((value) => !value)}>Add object</button> : null}
        {onCreateRelationship && selectedIds.length === 2 ? <button type="button" disabled={busy} onClick={() => setShowRelationshipForm((value) => !value)}>Connect selected objects</button> : null}
        {onRenameObject && selectedObject ? <button type="button" disabled={busy} onClick={() => { renameVersionRef.current += 1; setRenameId(selectedObject.id); setRenameValue(selectedObject.name); }}>Rename {selectedObject.name}</button> : null}
      </div>

      {showObjectForm && onCreateObject ? (
        <form className="world-graph-canvas__form" onSubmit={submitObject}>
          <label>Object name<input autoFocus value={objectName} onChange={(event) => { objectNameVersionRef.current += 1; setObjectName(event.target.value); }} /></label>
          <label>Type<select value={objectKind} onChange={(event) => { objectNameVersionRef.current += 1; setObjectKind(event.target.value); }}><option value="person">Person</option><option value="location">Location</option><option value="event">Event</option><option value="faction">Faction</option></select></label>
          <button type="submit" disabled={busy || !objectName.trim()}>Create object</button>
          <button type="button" onClick={() => setShowObjectForm(false)}>Cancel</button>
        </form>
      ) : null}
      {showRelationshipForm && onCreateRelationship && selectedIds.length === 2 ? (
        <form className="world-graph-canvas__form" onSubmit={submitRelationship}>
          <label>Relationship label<input autoFocus value={relationshipKind} onChange={(event) => { relationshipKindVersionRef.current += 1; setRelationshipKind(event.target.value); }} /></label>
          <button type="submit" disabled={busy || !relationshipKind.trim()}>Create relationship</button>
          <button type="button" onClick={() => setShowRelationshipForm(false)}>Cancel</button>
        </form>
      ) : null}
      {renameId && onRenameObject ? (
        <form className="world-graph-canvas__form" onSubmit={submitRename}>
          <label>New name<input autoFocus value={renameValue} onChange={(event) => { renameVersionRef.current += 1; setRenameValue(event.target.value); }} /></label>
          <button type="submit" disabled={busy || !renameValue.trim()}>Save name</button>
          <button type="button" onClick={() => setRenameId(null)}>Cancel</button>
        </form>
      ) : null}

      <div className="world-graph-canvas__viewport">
        <svg
          className="world-graph-canvas__svg"
          viewBox={`0 0 ${canvasWidth} ${canvasHeight}`}
          style={{ width: `${canvasWidth}px`, height: `${canvasHeight}px` }}
          role="group"
          aria-label={`${record.snapshot.title} world graph`}
          onPointerMove={(event) => {
            if (!drag) return;
            if (Math.abs(event.clientX - drag.pointerX) + Math.abs(event.clientY - drag.pointerY) > 4) dragMoved.current = true;
          }}
          onPointerUp={finishDrag}
          onPointerCancel={() => { setDrag(null); dragMoved.current = false; }}
        >
          <defs><marker id={markerId} markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><path d="M0,0 L9,3.5 L0,7 z" /></marker></defs>
          <g className="world-graph-canvas__edges" aria-label="Relationships">
            {renderedEdges.map(({ edge, geometry }) => {
              const label = accessibleRelationshipLabel(edge, nodeNames);
              return (
              <g className="world-graph-canvas__edge" key={edge.id} data-edge-id={edge.id} role="img" aria-label={label}>
                <path d={geometry.path} markerEnd={`url(#${markerId})`} />
                <text x={geometry.labelX} y={geometry.labelY - 7}>{edge.kind}</text>
                <title>{label}</title>
              </g>
            );})}
          </g>
          <g className="world-graph-canvas__nodes" aria-label="World objects">
            {projection.nodes.map((node) => {
              const selected = selectedIds.includes(node.id);
              return (
                <g
                  key={node.id}
                  className={`world-graph-canvas__node${selected ? " is-selected" : ""}`}
                  transform={`translate(${node.x} ${node.y})`}
                  role="button"
                  tabIndex={0}
                  aria-pressed={selected}
                  aria-label={`${node.name}, ${node.kind}`}
                  data-node-id={node.id}
                  onClick={() => { if (!dragMoved.current) selectNode(node.id); }}
                  onKeyDown={(event) => onNodeKeyDown(event, node.id)}
                  onPointerDown={(event) => {
                    if ((event.button ?? 0) !== 0 || !onMoveObjects) return;
                    dragMoved.current = false;
                    setDrag({ id: node.id, pointerX: event.clientX, pointerY: event.clientY, x: node.x, y: node.y });
                    if ("setPointerCapture" in event.currentTarget) {
                      try { event.currentTarget.setPointerCapture(event.pointerId); } catch { /* Pointer capture is optional in test DOMs. */ }
                    }
                  }}
                >
                  <rect width={NODE_WIDTH} height={NODE_HEIGHT} rx="12" />
                  <text className="world-graph-canvas__node-kind" x="14" y="22">{node.kind}</text>
                  <text className="world-graph-canvas__node-name" x="14" y="49">{node.name.length > 22 ? `${node.name.slice(0, 21)}…` : node.name}</text>
                </g>
              );
            })}
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
