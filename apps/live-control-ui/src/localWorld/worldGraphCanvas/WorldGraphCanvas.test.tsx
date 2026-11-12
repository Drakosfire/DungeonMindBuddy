import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { StrictMode } from "react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { InMemoryLocalWorldRepository } from "../inMemoryLocalWorldRepository";
import { createTestWorld, sequenceLocalIds } from "../localWorldContractFixtures";
import type { CommitSemanticResult, LocalWorldRecord, LocalWorldRelationship, WriteLayoutResult } from "../localWorldRepository";
import { createLocalWorldGraphAdapter } from "./localWorldGraphAdapter";
import { projectLocalWorldGraph } from "./graphProjection";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as projectionModule from "./graphProjection";
import { WorldGraphCanvas, type WorldGraphEditorDraft } from "./WorldGraphCanvas";

async function graphRecord(): Promise<{ repository: InMemoryLocalWorldRepository; record: LocalWorldRecord }> {
  const repository = new InMemoryLocalWorldRepository({ idFactory: sequenceLocalIds() });
  const empty = await createTestWorld(repository, "The Ember Coast");
  const worldId = empty.snapshot.worldId;
  const people = ["Mara Venn", "Tomas Reed"].map((name) => ({
    id: repository.allocateObjectId(worldId), name, kind: "person", properties: {},
  }));
  const location = { id: repository.allocateObjectId(worldId), name: "The Glass Orchard", kind: "location", properties: {} };
  const event = { id: repository.allocateObjectId(worldId), name: "The Winter Accord", kind: "event", properties: {} };
  const objects = [...people, location, event];
  const relationships = [
    [people[0].id, people[1].id, "allies"],
    [people[0].id, event.id, "negotiated"],
    [people[1].id, event.id, "signed"],
    [location.id, event.id, "hosted"],
  ].map(([fromObjectId, toObjectId, kind]) => ({
    id: repository.allocateRelationshipId(worldId), fromObjectId, toObjectId, kind, properties: {},
  })) as LocalWorldRelationship[];
  const result = await repository.commitSemanticEdit({
    worldId, expectedLocalRevision: empty.localRevision,
    nextSnapshot: { worldId, title: empty.snapshot.title, objects, relationships },
    edit: { classification: "buddy-local-only", description: "Test fixture graph" },
  });
  if (result.status !== "committed") throw new Error("Unable to seed canvas test graph.");
  return { repository, record: result.record };
}

type DraftKind = "object" | "relationship" | "rename";
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}

function cameraFromScene(scene: Element): { readonly x: number; readonly y: number; readonly zoom: number } {
  const match = scene.getAttribute("transform")?.match(/translate\(([-.\d]+) ([-.\d]+)\) scale\(([-.\d]+)\)/);
  if (!match) throw new Error("Graph scene transform is missing.");
  return { x: Number(match[1]), y: Number(match[2]), zoom: Number(match[3]) };
}

function screenPoint(camera: { readonly x: number; readonly y: number; readonly zoom: number }, point: { readonly x: number; readonly y: number }) {
  return { x: camera.x + point.x * camera.zoom, y: camera.y + point.y * camera.zoom };
}

function captureRect(element: Element, width = 960, height = 520) {
  return vi.spyOn(element, "getBoundingClientRect").mockReturnValue({ width, height, x: 0, y: 0,
    top: 0, right: width, bottom: height, left: 0, toJSON: () => ({}) });
}

function dispatchPointer(element: Element, type: "pointerdown" | "pointermove" | "pointerup" | "pointercancel", init: MouseEventInit & { readonly pointerId: number }) {
  const event = new MouseEvent(type, { bubbles: true, cancelable: true, ...init });
  Object.defineProperty(event, "pointerId", { configurable: true, value: init.pointerId });
  fireEvent(element, event);
}

async function enterDraft(user: ReturnType<typeof userEvent.setup>, kind: DraftKind, record: LocalWorldRecord) {
  let input: HTMLInputElement;
  let submitName: string;
  let draft: string;
  if (kind === "object") {
    await user.click(screen.getByRole("button", { name: "Add object" }));
    input = screen.getByLabelText("Object name") as HTMLInputElement;
    draft = "Ashen Courier";
    submitName = "Create object";
  } else if (kind === "relationship") {
    const graph = screen.getByRole("group", { name: `${record.snapshot.title} world graph` });
    await user.click(within(graph).getByRole("button", { name: `${record.snapshot.objects[0].name}, person` }));
    await user.click(within(graph).getByRole("button", { name: `${record.snapshot.objects[1].name}, person` }));
    await user.click(screen.getByRole("button", { name: "Connect selected objects" }));
    input = screen.getByLabelText("Relationship label") as HTMLInputElement;
    draft = "trusts";
    submitName = "Create relationship";
  } else {
    const first = record.snapshot.objects[0];
    const graph = screen.getByRole("group", { name: `${record.snapshot.title} world graph` });
    await user.click(within(graph).getByRole("button", { name: `${first.name}, ${first.kind}` }));
    await user.click(screen.getByRole("button", { name: `Rename ${first.name}` }));
    input = screen.getByLabelText("New name") as HTMLInputElement;
    draft = "Mara Candidate";
    submitName = "Save name";
  }
  if (kind === "rename") await user.clear(input);
  await user.type(input, draft);
  await user.click(screen.getByRole("button", { name: submitName }));
  return { inputLabel: kind === "object" ? "Object name" : kind === "relationship" ? "Relationship label" : "New name", submitName, draft };
}

async function conflictFor(kind: DraftKind, repository: InMemoryLocalWorldRepository, record: LocalWorldRecord, draft: string): Promise<CommitSemanticResult> {
  const adapter = createLocalWorldGraphAdapter(repository);
  const firstId = record.snapshot.objects[0].id;
  const secondId = record.snapshot.objects[1].id;
  const winner = await adapter.renameObject(record, firstId, "Winning edit");
  if (winner.status !== "committed") throw new Error("Unable to prepare stale conflict fixture.");
  if (kind === "object") return adapter.createObject(record, { name: draft, kind: "person" });
  if (kind === "relationship") return adapter.createRelationship(record, { fromObjectId: firstId, toObjectId: secondId, kind: draft });
  return adapter.renameObject(record, firstId, draft);
}

describe("WorldGraphCanvas", () => {
  it("renders an accessible controlled cyclic-capable graph with parallel edges keyed by assertion identity", async () => {
    const { record } = await graphRecord();
    const original = record.snapshot.relationships[0];
    const parallel: LocalWorldRelationship = {
      ...original,
      id: `${record.snapshot.worldId}:relationship:parallel` as LocalWorldRelationship["id"],
    };
    const reciprocal: LocalWorldRelationship = {
      ...original,
      id: `${record.snapshot.worldId}:relationship:reciprocal` as LocalWorldRelationship["id"],
      fromObjectId: original.toObjectId,
      toObjectId: original.fromObjectId,
      kind: "reciprocates",
    };
    const loop: LocalWorldRelationship = {
      ...original,
      id: `${record.snapshot.worldId}:relationship:loop` as LocalWorldRelationship["id"],
      toObjectId: original.fromObjectId,
      kind: "remembers",
    };
    const snapshot = { ...record.snapshot, relationships: [...record.snapshot.relationships, reciprocal, parallel, loop] };
    render(<WorldGraphCanvas record={{ ...record, snapshot }} />);

    const graph = screen.getByRole("group", { name: "The Ember Coast world graph" });
    expect(within(graph).getByRole("button", { name: "Mara Venn, person" })).toBeVisible();
    expect(within(graph).getByRole("button", { name: "Tomas Reed, person" })).toBeVisible();
    expect(within(graph).getByRole("button", { name: "The Glass Orchard, location" })).toBeVisible();
    expect(within(graph).getByRole("button", { name: "The Winter Accord, event" })).toBeVisible();
    expect(graph.querySelectorAll("[data-edge-id]")).toHaveLength(7);
    const firstEdge = graph.querySelector(`[data-edge-id="${original.id}"]`);
    const parallelEdge = graph.querySelector(`[data-edge-id="${parallel.id}"]`);
    expect(firstEdge?.querySelector("path")?.getAttribute("d"))
      .not.toBe(parallelEdge?.querySelector("path")?.getAttribute("d"));
    expect(firstEdge?.querySelector("text")?.getAttribute("y"))
      .not.toBe(parallelEdge?.querySelector("text")?.getAttribute("y"));
    const reciprocalEdge = graph.querySelector(`[data-edge-id="${reciprocal.id}"]`);
    expect(new Set([firstEdge, reciprocalEdge, parallelEdge].map((edge) => edge?.querySelector("path")?.getAttribute("d"))).size).toBe(3);
    expect(new Set([firstEdge, reciprocalEdge, parallelEdge].map((edge) => edge?.querySelector("text")?.getAttribute("y"))).size).toBe(3);
    expect(firstEdge).toHaveAccessibleName("Mara Venn allies Tomas Reed");
    expect(graph.querySelector(`[data-edge-id="${loop.id}"] path`)?.getAttribute("d")).toContain(" C ");
    expect(screen.queryByRole("button", { name: /world, world/i })).not.toBeInTheDocument();
  });

  it("uses true circles, clips curved edges to their radii, fits the initial graph and retains a manually moved camera", async () => {
    const { record } = await graphRecord();
    const first = record.snapshot.objects[0];
    const loop: LocalWorldRelationship = {
      ...record.snapshot.relationships[0],
      id: `${record.snapshot.worldId}:relationship:circle-loop` as LocalWorldRelationship["id"],
      fromObjectId: first.id,
      toObjectId: first.id,
      kind: "remembers",
    };
    const expanded = { ...record, snapshot: { ...record.snapshot, relationships: [...record.snapshot.relationships, loop] } };
    const layout = vi.fn();
    const view = render(<WorldGraphCanvas record={expanded} nodeShape="circle" onMoveObjects={layout} />);
    const graph = screen.getByRole("group", { name: "The Ember Coast world graph" });
    const firstNode = graph.querySelector(`[data-node-id="${first.id}"]`)!;
    expect(firstNode.querySelector(".world-graph-canvas__node-circle")).toHaveAttribute("r", "56");
    expect(firstNode.querySelector("rect")).toBeNull();
    expect(graph.querySelectorAll(".world-graph-canvas__node-circle")).toHaveLength(4);

    const camera = cameraFromScene(screen.getByTestId("graph-scene"));
    for (const node of projectLocalWorldGraph(expanded).nodes) {
      expect((node.x * camera.zoom + camera.x)).toBeGreaterThanOrEqual(-1);
      expect(((node.x + 112) * camera.zoom + camera.x)).toBeLessThanOrEqual(961);
      expect((node.y * camera.zoom + camera.y)).toBeGreaterThanOrEqual(-1);
      expect(((node.y + 112) * camera.zoom + camera.y)).toBeLessThanOrEqual(521);
    }

    const sourcePosition = projectLocalWorldGraph(expanded).nodes[0];
    for (const edgeId of [record.snapshot.relationships[0].id, loop.id]) {
      const path = graph.querySelector(`[data-edge-id="${edgeId}"] path`)!;
      const match = path.getAttribute("d")?.match(/^M\s+([-\d.]+)\s+([-\d.]+)/);
      expect(match).not.toBeNull();
      const startX = Number(match?.[1]);
      const startY = Number(match?.[2]);
      const distance = Math.hypot(startX - (sourcePosition.x + 56), startY - (sourcePosition.y + 56));
      expect(distance).toBeCloseTo(61, 4);
    }
    expect(graph.querySelector(`[data-edge-id="${loop.id}"] path`)?.getAttribute("d")).toContain(" C ");

    const svg = graph;
    captureRect(svg);
    const beforePan = screen.getByTestId("graph-scene").getAttribute("transform");
    dispatchPointer(svg, "pointerdown", { button: 0, pointerId: 20, clientX: 100, clientY: 100 });
    dispatchPointer(svg, "pointermove", { pointerId: 20, clientX: 180, clientY: 140 });
    dispatchPointer(svg, "pointerup", { pointerId: 20, clientX: 180, clientY: 140 });
    const afterPan = screen.getByTestId("graph-scene").getAttribute("transform");
    expect(afterPan).not.toBe(beforePan);
    view.rerender(<WorldGraphCanvas record={{ ...expanded, localRevision: expanded.localRevision + 1 }} nodeShape="circle" onMoveObjects={layout} />);
    expect(screen.getByTestId("graph-scene").getAttribute("transform")).toBe(afterPan);
    expect(layout).not.toHaveBeenCalled();
  });

  it("opens an accessible palette at the clicked graph coordinate after pan and zoom, and only emits the chosen draft intent", async () => {
    const user = userEvent.setup();
    const { record } = await graphRecord();
    const onCanvasCreateRequest = vi.fn();
    render(<WorldGraphCanvas record={record} nodeShape="circle"
      creationKinds={[{ kind: "person", label: "Person" }, { kind: "location", label: "Location" }]}
      onCanvasCreateRequest={onCanvasCreateRequest} />);
    const svg = screen.getByRole("group", { name: "The Ember Coast world graph" });
    captureRect(svg);
    dispatchPointer(svg, "pointerdown", { button: 0, pointerId: 21, clientX: 40, clientY: 40 });
    dispatchPointer(svg, "pointermove", { pointerId: 21, clientX: 130, clientY: 90 });
    dispatchPointer(svg, "pointerup", { pointerId: 21, clientX: 130, clientY: 90 });
    await user.click(screen.getByRole("button", { name: "Zoom in" }));
    const camera = cameraFromScene(screen.getByTestId("graph-scene"));
    const pointer = { x: 720, y: 420 };
    const expected = {
      x: Math.max(0, Math.min(6000, (pointer.x - camera.x) / camera.zoom)),
      y: Math.max(0, Math.min(6000, (pointer.y - camera.y) / camera.zoom)),
    };
    dispatchPointer(svg, "pointerdown", { button: 0, pointerId: 22, clientX: pointer.x, clientY: pointer.y });
    dispatchPointer(svg, "pointerup", { pointerId: 22, clientX: pointer.x, clientY: pointer.y });
    const palette = screen.getByTestId("node-palette");
    expect(palette).toHaveAccessibleName("Choose node type");
    expect(Number(palette.getAttribute("data-position-x"))).toBeCloseTo(expected.x, 4);
    expect(Number(palette.getAttribute("data-position-y"))).toBeCloseTo(expected.y, 4);
    expect(onCanvasCreateRequest).not.toHaveBeenCalled();
    await user.click(within(palette).getByRole("button", { name: "Person" }));
    expect(onCanvasCreateRequest).toHaveBeenCalledExactlyOnceWith({ kind: "person", position: expected });

    const trigger = screen.getByRole("button", { name: "Place node" });
    await user.click(trigger);
    const nextPalette = screen.getByTestId("node-palette");
    expect(nextPalette).toBeVisible();
    const cancel = within(nextPalette).getByRole("button", { name: "Cancel placement" });
    expect(cancel).toHaveAttribute("aria-keyshortcuts", "Escape");
    await user.click(cancel);
    expect(screen.queryByTestId("node-palette")).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(onCanvasCreateRequest).toHaveBeenCalledTimes(1);

    await user.click(trigger);
    await user.keyboard("{Escape}");
    expect(screen.queryByTestId("node-palette")).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(onCanvasCreateRequest).toHaveBeenCalledTimes(1);
  });

  it("keeps the exit visible and reachable in a short viewport after a blank-canvas click", async () => {
    const user = userEvent.setup();
    const { record } = await graphRecord();
    let resize!: ResizeObserverCallback;
    class TestResizeObserver {
      constructor(callback: ResizeObserverCallback) { resize = callback; }
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    vi.stubGlobal("ResizeObserver", TestResizeObserver);
    const oldVisualViewport = Object.getOwnPropertyDescriptor(window, "visualViewport");
    const visibleWindow = new EventTarget() as VisualViewport;
    Object.defineProperties(visibleWindow, {
      offsetLeft: { configurable: true, value: 0 },
      offsetTop: { configurable: true, value: 12 },
      width: { configurable: true, writable: true, value: 390 },
      height: { configurable: true, writable: true, value: 320 },
    });
    Object.defineProperty(window, "visualViewport", { configurable: true, value: visibleWindow });
    const originalGetRect = HTMLDivElement.prototype.getBoundingClientRect;
    vi.spyOn(HTMLDivElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLDivElement) {
      if (this.classList.contains("world-graph-canvas__palette")) {
        return { x: 0, y: 0, top: 0, left: 0, right: 160, bottom: 158, width: 160, height: 158, toJSON: () => ({}) };
      }
      return originalGetRect.call(this);
    });
    const onCanvasCreateRequest = vi.fn();
    let svgTop = 180;
    try {
      render(<>
        <button type="button">Outside canvas control</button>
        <WorldGraphCanvas record={record} nodeShape="circle"
          creationKinds={[{ kind: "person", label: "Person" }, { kind: "location", label: "Location" }]}
          onCanvasCreateRequest={onCanvasCreateRequest} />
      </>);

      const svg = screen.getByRole("group", { name: "The Ember Coast world graph" });
      vi.spyOn(svg, "getBoundingClientRect").mockImplementation(() => ({ width: 390, height: 120, x: 0, y: svgTop,
        top: svgTop, right: 390, bottom: svgTop + 120, left: 0, toJSON: () => ({}) }));
      act(() => resize([{ contentRect: { width: 390, height: 120 } } as ResizeObserverEntry], {} as ResizeObserver));
      dispatchPointer(svg, "pointerdown", { button: 0, pointerId: 50, clientX: 380, clientY: 295 });
      dispatchPointer(svg, "pointerup", { pointerId: 50, clientX: 380, clientY: 295 });

      const palette = screen.getByTestId("node-palette");
      const choices = palette.querySelector(".world-graph-canvas__palette-choices")!;
      const cancel = within(palette).getByRole("button", { name: "Cancel placement" });
      expect(palette.parentElement).toBe(document.body);
      expect(palette).toHaveStyle({ position: "fixed" });
      expect(Number(palette.style.left.replace("px", ""))).toBeGreaterThanOrEqual(8);
      const initialTop = Number(palette.style.top.replace("px", ""));
      expect(initialTop).toBeGreaterThanOrEqual(20);
      expect(initialTop + 158).toBeLessThanOrEqual(324);
      const originalGraphY = palette.getAttribute("data-position-y");
      expect(cancel).toBeVisible();
      expect(choices).not.toContainElement(cancel);
      expect(screen.getByRole("button", { name: "Person" })).toHaveFocus();

      await user.tab();
      await user.tab();
      expect(cancel).toHaveFocus();
      svgTop = 120;
      act(() => window.dispatchEvent(new Event("scroll")));
      expect(Number(palette.style.top.replace("px", ""))).not.toBe(initialTop);
      expect(palette.getAttribute("data-position-y")).toBe(originalGraphY);
      Object.defineProperty(visibleWindow, "height", { configurable: true, writable: true, value: 270 });
      act(() => visibleWindow.dispatchEvent(new Event("resize")));
      expect(Number(palette.style.top.replace("px", "")) + 158).toBeLessThanOrEqual(274);
      expect(cancel).toHaveFocus();
      await user.keyboard("{Enter}");
      expect(screen.queryByTestId("node-palette")).not.toBeInTheDocument();
      await waitFor(() => expect(svg).toHaveFocus());
      expect(onCanvasCreateRequest).not.toHaveBeenCalled();

      dispatchPointer(svg, "pointerdown", { button: 0, pointerId: 51, clientX: 380, clientY: 235 });
      dispatchPointer(svg, "pointerup", { pointerId: 51, clientX: 380, clientY: 235 });
      expect(screen.getByTestId("node-palette")).toBeVisible();
      screen.getByRole("button", { name: "Outside canvas control" }).focus();
      await user.keyboard("{Escape}");
      expect(screen.queryByTestId("node-palette")).not.toBeInTheDocument();
      await waitFor(() => expect(svg).toHaveFocus());
      expect(onCanvasCreateRequest).not.toHaveBeenCalled();
    } finally {
      vi.unstubAllGlobals();
      vi.restoreAllMocks();
      if (oldVisualViewport) Object.defineProperty(window, "visualViewport", oldVisualViewport);
      else Reflect.deleteProperty(window, "visualViewport");
    }
  });

  it("keeps empty-state and interaction feedback when neutral graph counts are hidden", async () => {
    const user = userEvent.setup();
    const { record } = await graphRecord();
    const onConnectRequest = vi.fn();
    const { rerender } = render(<WorldGraphCanvas record={record} onConnectRequest={onConnectRequest} />);
    const feedback = document.querySelector(".world-graph-canvas__feedback")!;
    expect(feedback).toHaveTextContent("4 objects · 4 relationships");
    rerender(<WorldGraphCanvas record={record} onConnectRequest={onConnectRequest} showSummaryCounts={false} />);
    expect(feedback).toBeEmptyDOMElement();

    await user.click(screen.getByRole("button", { name: "Mara Venn, person" }));
    await user.click(screen.getByRole("button", { name: "Tomas Reed, person" }));
    await user.click(screen.getByRole("button", { name: "Connect selected nodes" }));
    expect(feedback).toHaveTextContent("Connection draft opened.");
    expect(onConnectRequest).toHaveBeenCalledExactlyOnceWith({ sourceId: record.snapshot.objects[0].id, targetId: record.snapshot.objects[1].id });

    const emptyRecord = { ...record, snapshot: { ...record.snapshot, objects: [], relationships: [] } };
    const emptyView = render(<WorldGraphCanvas record={emptyRecord} showSummaryCounts={false} />);
    expect(emptyView.container.querySelector(".world-graph-canvas__feedback")).toHaveTextContent("This World has no objects yet. Add an object to begin.");
  });

  it("captures connector-dot drags, previews a curve and emits only real-node drops", async () => {
    const { record } = await graphRecord();
    const onConnectRequest = vi.fn();
    const view = render(<WorldGraphCanvas record={record} nodeShape="circle" onConnectRequest={onConnectRequest} />);
    const svg = screen.getByRole("group", { name: "The Ember Coast world graph" });
    captureRect(svg);
    const scene = screen.getByTestId("graph-scene");
    const originalTransform = scene.getAttribute("transform");
    const camera = cameraFromScene(scene);
    const projected = projectLocalWorldGraph(record).nodes;
    const [source, target] = projected;
    const sourceNode = svg.querySelector(`[data-node-id="${source.id}"]`)!;
    const port = screen.getByTestId(`connect-port-${source.id}`);
    const capture = vi.fn();
    const release = vi.fn();
    Object.defineProperty(port, "setPointerCapture", { configurable: true, value: capture });
    Object.defineProperty(port, "releasePointerCapture", { configurable: true, value: release });
    const start = screenPoint(camera, { x: source.x + 110, y: source.y + 56 });
    const end = screenPoint(camera, { x: target.x + 56, y: target.y + 56 });

    dispatchPointer(port, "pointerdown", { button: 0, pointerId: 31, clientX: start.x, clientY: start.y });
    expect(capture).toHaveBeenCalledExactlyOnceWith(31);
    dispatchPointer(svg, "pointermove", { pointerId: 31, clientX: end.x, clientY: end.y });
    expect(screen.getByTestId("connect-preview")).toBeVisible();
    expect(sourceNode).toHaveAttribute("transform", `translate(${source.x} ${source.y})`);
    expect(svg).not.toHaveClass("is-panning");
    expect(scene.getAttribute("transform")).toBe(originalTransform);
    dispatchPointer(svg, "pointerup", { pointerId: 31, clientX: end.x, clientY: end.y });
    expect(onConnectRequest).toHaveBeenCalledExactlyOnceWith({ sourceId: source.id, targetId: target.id });
    expect(release).toHaveBeenCalledExactlyOnceWith(31);
    expect(screen.queryByTestId("connect-preview")).not.toBeInTheDocument();
    expect(svg.querySelector(`[data-node-id="${source.id}"]`)).toHaveAttribute("aria-pressed", "false");

    dispatchPointer(port, "pointerdown", { button: 0, pointerId: 32, clientX: start.x, clientY: start.y });
    dispatchPointer(svg, "pointermove", { pointerId: 32, clientX: end.x, clientY: end.y });
    dispatchPointer(svg, "pointercancel", { pointerId: 32 });
    dispatchPointer(svg, "pointerup", { pointerId: 32, clientX: end.x, clientY: end.y });
    dispatchPointer(port, "pointerdown", { button: 0, pointerId: 34, clientX: start.x, clientY: start.y });
    dispatchPointer(svg, "pointermove", { pointerId: 34, clientX: end.x, clientY: end.y });
    fireEvent.keyDown(svg, { key: "Escape" });
    dispatchPointer(svg, "pointerup", { pointerId: 34, clientX: end.x, clientY: end.y });
    dispatchPointer(port, "pointerdown", { button: 0, pointerId: 33, clientX: start.x, clientY: start.y });
    dispatchPointer(svg, "pointermove", { pointerId: 33, clientX: -1000, clientY: -1000 });
    dispatchPointer(svg, "pointerup", { pointerId: 33, clientX: -1000, clientY: -1000 });
    dispatchPointer(port, "pointerdown", { button: 0, pointerId: 35, clientX: start.x, clientY: start.y });
    dispatchPointer(svg, "pointermove", { pointerId: 35, clientX: end.x, clientY: end.y });
    const otherWorld = { ...record, snapshot: { ...record.snapshot, worldId: `${record.snapshot.worldId}:other` as typeof record.snapshot.worldId } };
    view.rerender(<WorldGraphCanvas record={otherWorld} nodeShape="circle" onConnectRequest={onConnectRequest} />);
    dispatchPointer(svg, "pointerup", { pointerId: 35, clientX: end.x, clientY: end.y });
    expect(onConnectRequest).toHaveBeenCalledTimes(1);
  });

  it("keeps the default card geometry and legacy local editor behavior", async () => {
    const user = userEvent.setup();
    const { record } = await graphRecord();
    const onCreateObject = vi.fn(async () => ({ status: "error", message: "keep draft" }) as CommitSemanticResult);
    render(<WorldGraphCanvas record={record} onCreateObject={onCreateObject} />);
    const graph = screen.getByRole("group", { name: "The Ember Coast world graph" });
    const node = graph.querySelector(`[data-node-id="${record.snapshot.objects[0].id}"]`)!;
    expect(node.querySelector("rect")).toBeInTheDocument();
    expect(node.querySelector(".world-graph-canvas__node-circle")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Add object" }));
    await user.type(screen.getByLabelText("Object name"), "Ashen Courier");
    await user.click(screen.getByRole("button", { name: "Create object" }));
    expect(onCreateObject).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("keep draft")).toBeVisible();
    expect(screen.getByLabelText("Object name")).toHaveValue("Ashen Courier");
  });

  it.each(["object", "relationship", "rename"] as const)("retains a %s draft after callback rejection, error result and semantic conflict", async (kind) => {
    for (const outcome of ["rejection", "failure", "conflict"] as const) {
      const user = userEvent.setup();
      const { repository, record } = await graphRecord();
      const pending = deferred<CommitSemanticResult>();
      const callback = vi.fn(() => pending.promise);
      const props = kind === "object" ? { onCreateObject: callback }
        : kind === "relationship" ? { onCreateRelationship: callback }
          : { onRenameObject: callback };
      const { unmount } = render(<WorldGraphCanvas record={record} {...props} />);
      const { draft, inputLabel } = await enterDraft(user, kind, record);
      if (outcome === "rejection") pending.reject(new Error("callback rejected"));
      else pending.resolve(outcome === "failure"
          ? { status: "error", message: "write interrupted" }
          : await conflictFor(kind, repository, record, draft));
      expect(await screen.findByText(outcome === "rejection" ? "callback rejected" : outcome === "failure" ? "write interrupted" : /conflict candidate/)).toBeVisible();
      expect(screen.getByLabelText(inputLabel)).toHaveValue(draft);
      expect(screen.getByRole("button", { name: kind === "object" ? "Create object" : kind === "relationship" ? "Create relationship" : "Save name" })).toBeVisible();
      // Unmount between matrix cases so each row owns a clean canvas instance.
      unmount();
    }
  });

  it.each(["object", "relationship", "rename"] as const)("restores a failed %s draft from the route-owned versioned snapshot", async (kind) => {
    const user = userEvent.setup();
    const { record } = await graphRecord();
    const error = { status: "error", message: "write interrupted" } as const;
    const callbacks = kind === "object" ? { onCreateObject: async () => error }
      : kind === "relationship" ? { onCreateRelationship: async () => error }
        : { onRenameObject: async () => error };
    let saved: { version: number; draft: WorldGraphEditorDraft | null } = { version: 0, draft: null };
    const onDraftChange = (draft: WorldGraphEditorDraft | null, version: number, expectedVersion?: number) => {
      if (expectedVersion !== undefined && saved.version !== expectedVersion) return;
      if (version >= saved.version) saved = { version, draft };
    };
    const renderCanvas = () => render(<WorldGraphCanvas record={record} editorDraftState={saved}
      onEditorDraftChange={onDraftChange} {...callbacks} />);

    const first = renderCanvas();
    const { draft, inputLabel } = await enterDraft(user, kind, record);
    expect(await screen.findByText("write interrupted")).toBeVisible();
    expect(saved.draft).not.toBeNull();
    first.unmount();

    renderCanvas();
    expect(screen.getByLabelText(inputLabel)).toHaveValue(draft);
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(saved.draft).toBeNull();
  });

  it.each(["object", "relationship", "rename"] as const)("does not clear a newer %s draft when an older submission succeeds", async (kind) => {
    const user = userEvent.setup();
    const { record } = await graphRecord();
    const pending = deferred<CommitSemanticResult>();
    const callback = vi.fn(() => pending.promise);
    const props = kind === "object" ? { onCreateObject: callback }
      : kind === "relationship" ? { onCreateRelationship: callback }
        : { onRenameObject: callback };
    const { unmount } = render(<WorldGraphCanvas record={record} {...props} />);
    const { draft, inputLabel } = await enterDraft(user, kind, record);
    await user.type(screen.getByLabelText(inputLabel), " newer");
    pending.resolve({ status: "committed", record });
    expect(await screen.findByText("Edit recorded.")).toBeVisible();
    expect(screen.getByLabelText(inputLabel)).toHaveValue(`${draft} newer`);
    unmount();
  });

  it.each(["object", "relationship", "rename"] as const)("keeps a %s draft when edited away and back during submission", async (kind) => {
    const user = userEvent.setup();
    const { record } = await graphRecord();
    const pending = deferred<CommitSemanticResult>();
    const callback = vi.fn(() => pending.promise);
    const props = kind === "object" ? { onCreateObject: callback }
      : kind === "relationship" ? { onCreateRelationship: callback }
        : { onRenameObject: callback };
    const { unmount } = render(<WorldGraphCanvas record={record} {...props} />);
    const { draft, inputLabel } = await enterDraft(user, kind, record);
    const input = screen.getByLabelText(inputLabel);
    await user.clear(input);
    await user.type(input, draft);
    pending.resolve({ status: "committed", record });
    expect(await screen.findByText("Edit recorded.")).toBeVisible();
    expect(screen.getByLabelText(inputLabel)).toHaveValue(draft);
    unmount();
  });

  it("retains a changed object type when an older create submission succeeds", async () => {
    const user = userEvent.setup();
    const { record } = await graphRecord();
    const pending = deferred<CommitSemanticResult>();
    render(<WorldGraphCanvas record={record} onCreateObject={() => pending.promise} />);
    await user.click(screen.getByRole("button", { name: "Add object" }));
    await user.type(screen.getByLabelText("Object name"), "Ashen Courier");
    await user.click(screen.getByRole("button", { name: "Create object" }));
    await user.selectOptions(screen.getByLabelText("Type"), "event");
    pending.resolve({ status: "committed", record });
    expect(await screen.findByText("Edit recorded.")).toBeVisible();
    expect(screen.getByLabelText("Object name")).toHaveValue("Ashen Courier");
    expect(screen.getByLabelText("Type")).toHaveValue("event");
  });

  it("retains a changed relationship endpoint selection when an older create succeeds", async () => {
    const user = userEvent.setup();
    const { record } = await graphRecord();
    const pending = deferred<CommitSemanticResult>();
    render(<WorldGraphCanvas record={record} onCreateRelationship={() => pending.promise} />);
    const graph = screen.getByRole("group", { name: `${record.snapshot.title} world graph` });
    const mara = within(graph).getByRole("button", { name: "Mara Venn, person" });
    const tomas = within(graph).getByRole("button", { name: "Tomas Reed, person" });
    const orchard = within(graph).getByRole("button", { name: "The Glass Orchard, location" });
    await user.click(mara);
    await user.click(tomas);
    await user.click(screen.getByRole("button", { name: "Connect selected objects" }));
    await user.type(screen.getByLabelText("Relationship label"), "trusts");
    await user.click(screen.getByRole("button", { name: "Create relationship" }));
    await user.click(mara);
    await user.click(orchard);
    pending.resolve({ status: "committed", record });
    expect(await screen.findByText("Edit recorded.")).toBeVisible();
    expect(screen.getByLabelText("Relationship label")).toHaveValue("trusts");
  });

  it("ignores a pending semantic completion after the controlled World changes", async () => {
    const user = userEvent.setup();
    const { record } = await graphRecord();
    const nextWorld = {
      ...record,
      snapshot: { ...record.snapshot, worldId: `${record.snapshot.worldId}:other` as typeof record.snapshot.worldId, title: "Other World" },
    };
    const pending = deferred<CommitSemanticResult>();
    const callback = vi.fn(() => pending.promise);
    const onSemanticResult = vi.fn();
    const { rerender } = render(<WorldGraphCanvas record={record} onCreateObject={callback} onSemanticResult={onSemanticResult} />);
    await user.click(screen.getByRole("button", { name: "Add object" }));
    const input = screen.getByLabelText("Object name");
    await user.type(input, "Draft for first World");
    await user.click(screen.getByRole("button", { name: "Create object" }));
    rerender(<WorldGraphCanvas record={nextWorld} onCreateObject={callback} onSemanticResult={onSemanticResult} />);
    await user.click(screen.getByRole("button", { name: "Add object" }));
    await user.type(screen.getByLabelText("Object name"), "Draft for second World");
    pending.resolve({ status: "committed", record });
    expect(await screen.findByLabelText("Object name")).toHaveValue("Draft for second World");
    expect(onSemanticResult).not.toHaveBeenCalled();
    expect(screen.getByRole("group", { name: `${nextWorld.snapshot.title} world graph` })).toBeVisible();
  });

  it("suppresses semantic and layout delivery from unmounted canvas instances", async () => {
    const user = userEvent.setup();
    const { repository, record } = await graphRecord();
    const adapter = createLocalWorldGraphAdapter(repository);
    const semanticGate = deferred<void>();
    let semanticOperation: Promise<CommitSemanticResult> | undefined;
    const staleSemanticResult = vi.fn();
    const firstMount = render(<WorldGraphCanvas record={record}
      onCreateObject={(current, input) => {
        semanticOperation = semanticGate.promise.then(() => adapter.createObject(current, input));
        return semanticOperation;
      }} onSemanticResult={staleSemanticResult} />);
    await user.click(screen.getByRole("button", { name: "Add object" }));
    await user.type(screen.getByLabelText("Object name"), "Ashen Courier");
    await user.click(screen.getByRole("button", { name: "Create object" }));
    firstMount.unmount();

    const currentSemanticResult = vi.fn();
    render(<WorldGraphCanvas record={record} onSemanticResult={currentSemanticResult} />);
    semanticGate.resolve(undefined);
    const semanticResult = await semanticOperation;
    expect(semanticResult?.status).toBe("committed");
    const persisted = await repository.readWorld(record.snapshot.worldId);
    expect(persisted.status).toBe("found");
    if (persisted.status === "found") expect(persisted.record.snapshot.objects.some((object) => object.name === "Ashen Courier")).toBe(true);
    expect(staleSemanticResult).not.toHaveBeenCalled();
    expect(currentSemanticResult).not.toHaveBeenCalled();
    expect(screen.getByRole("group", { name: `${record.snapshot.title} world graph` })).toBeVisible();

    const layoutGate = deferred<void>();
    let layoutOperation: Promise<WriteLayoutResult> | undefined;
    const staleLayoutResult = vi.fn();
    const secondMount = render(<WorldGraphCanvas record={record}
      onMoveObjects={(current, positions) => {
        layoutOperation = layoutGate.promise.then(() => adapter.moveObjects(current, positions));
        return layoutOperation;
      }} onLayoutResult={staleLayoutResult} />);
    const node = screen.getAllByRole("button", { name: "Mara Venn, person" }).at(-1)!;
    fireEvent.keyDown(node, { key: "ArrowRight" });
    secondMount.unmount();
    const currentLayoutResult = vi.fn();
    render(<WorldGraphCanvas record={record} onLayoutResult={currentLayoutResult} />);
    layoutGate.resolve(undefined);
    const layoutResult = await layoutOperation;
    expect(layoutResult?.status).toBe("written");
    const savedLayout = await repository.readWorld(record.snapshot.worldId);
    expect(savedLayout.status).toBe("found");
    if (savedLayout.status === "found") expect(savedLayout.record.layoutRevision).toBe(record.layoutRevision + 1);
    expect(staleLayoutResult).not.toHaveBeenCalled();
    expect(currentLayoutResult).not.toHaveBeenCalled();
  });

  it("delivers mounted semantic and layout results after StrictMode effect replay", async () => {
    const user = userEvent.setup();
    const { record } = await graphRecord();
    const semanticPending = deferred<CommitSemanticResult>();
    const layoutPending = deferred<WriteLayoutResult>();
    const onSemanticResult = vi.fn();
    const onLayoutResult = vi.fn();
    render(<StrictMode><WorldGraphCanvas record={record}
      onCreateObject={() => semanticPending.promise}
      onMoveObjects={() => layoutPending.promise}
      onSemanticResult={onSemanticResult}
      onLayoutResult={onLayoutResult} /></StrictMode>);
    await user.click(screen.getByRole("button", { name: "Add object" }));
    await user.type(screen.getByLabelText("Object name"), "Ashen Courier");
    await user.click(screen.getByRole("button", { name: "Create object" }));
    await act(async () => { semanticPending.resolve({ status: "committed", record }); });
    expect(onSemanticResult).toHaveBeenCalledWith({ status: "committed", record });

    fireEvent.keyDown(screen.getByRole("button", { name: "Mara Venn, person" }), { key: "ArrowRight" });
    await act(async () => { layoutPending.resolve({ status: "written", record }); });
    expect(onLayoutResult).toHaveBeenCalledWith({ status: "written", record });
  });

  it("creates a relationship between two selected objects through the local CAS adapter", async () => {
    const user = userEvent.setup();
    const { repository, record } = await graphRecord();
    const adapter = createLocalWorldGraphAdapter(repository);
    render(<WorldGraphCanvas record={record}
      onCreateRelationship={(current, input) => adapter.createRelationship(current, input)} />);
    const graph = screen.getByRole("group", { name: "The Ember Coast world graph" });
    const mara = within(graph).getByRole("button", { name: "Mara Venn, person" });
    const tomas = within(graph).getByRole("button", { name: "Tomas Reed, person" });
    await user.click(mara);
    await user.click(tomas);
    await user.click(screen.getByRole("button", { name: "Connect selected objects" }));
    await user.type(screen.getByLabelText("Relationship label"), "trusts");
    await user.click(screen.getByRole("button", { name: "Create relationship" }));

    expect(await screen.findByText("Edit recorded.")).toBeVisible();
    const persisted = await repository.readWorld(record.snapshot.worldId);
    expect(persisted.status).toBe("found");
    if (persisted.status === "found") {
      expect(persisted.record.localRevision).toBe(record.localRevision + 1);
      expect(persisted.record.snapshot.relationships.at(-1)).toMatchObject({
        fromObjectId: record.snapshot.objects[0].id,
        toObjectId: record.snapshot.objects[1].id,
        kind: "trusts",
      });
    }
  });

  it("exposes rename and layout as separate callbacks, including arrow-key node movement", async () => {
    const user = userEvent.setup();
    const { repository, record } = await graphRecord();
    const adapter = createLocalWorldGraphAdapter(repository);
    const layoutCallback = vi.fn((current: LocalWorldRecord, positions: Readonly<Record<string, { x: number; y: number }>>) => adapter.moveObjects(current, positions));
    render(<WorldGraphCanvas record={record}
      onRenameObject={(current, id, name) => adapter.renameObject(current, id, name)}
      onMoveObjects={layoutCallback} />);

    const mara = screen.getByRole("button", { name: "Mara Venn, person" });
    mara.focus();
    fireEvent.keyDown(mara, { key: "Enter" });
    expect(mara).toHaveAttribute("aria-pressed", "true");
    fireEvent.keyDown(mara, { key: "ArrowRight" });
    expect(await screen.findByText("Canvas layout updated.")).toBeVisible();
    expect(layoutCallback).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole("button", { name: "Rename Mara Venn" }));
    const nameInput = screen.getByLabelText("New name");
    await user.clear(nameInput);
    await user.type(nameInput, "Mara of the Reach");
    await user.click(screen.getByRole("button", { name: "Save name" }));
    expect(await screen.findByText("Edit recorded.")).toBeVisible();

    const persisted = await repository.readWorld(record.snapshot.worldId);
    expect(persisted.status).toBe("found");
    if (persisted.status === "found") {
      expect(persisted.record.localRevision).toBe(record.localRevision + 1);
      expect(persisted.record.layoutRevision).toBe(record.layoutRevision + 1);
      expect(persisted.record.snapshot.objects[0].name).toBe("Mara of the Reach");
    }
  });

  it("prevents duplicate object submissions while an edit callback is pending", async () => {
    const user = userEvent.setup();
    const { repository, record } = await graphRecord();
    let finish!: (result: CommitSemanticResult) => void;
    const commit = vi.fn(() => new Promise<CommitSemanticResult>((resolve) => { finish = resolve; }));
    render(<WorldGraphCanvas record={record} onCreateObject={commit} />);
    await user.click(screen.getByRole("button", { name: "Add object" }));
    await user.type(screen.getByLabelText("Object name"), "Ashen Courier");
    await user.click(screen.getByRole("button", { name: "Create object" }));
    expect(commit).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Add object" })).toBeDisabled();
    finish({ status: "error", message: "write interrupted" });
    expect(await screen.findByText("write interrupted")).toBeVisible();
  });

  it("supports pointer drag while writing only the separate layout revision", async () => {
    const { repository, record } = await graphRecord();
    const adapter = createLocalWorldGraphAdapter(repository);
    const layout = vi.fn((current: LocalWorldRecord, positions: Readonly<Record<string, { x: number; y: number }>>) => adapter.moveObjects(current, positions));
    const firstObjectId = record.snapshot.objects[0].id;
    const expandedRecord = { ...record, layout: { ...record.layout, positions: { [firstObjectId]: { x: 1200, y: 900 } } } };
    render(<WorldGraphCanvas record={expandedRecord} onMoveObjects={layout} />);
    const graph = screen.getByRole("group", { name: "The Ember Coast world graph" });
    const mara = screen.getByRole("button", { name: "Mara Venn, person" });
    fireEvent.click(screen.getByRole("button", { name: "100%" }));
    // The CSS-rendered viewport is twice its SVG viewBox dimensions.
    vi.spyOn(graph, "getBoundingClientRect").mockReturnValue({ width: 1920, height: 1040, x: 0, y: 0, top: 0, right: 1920, bottom: 1040, left: 0, toJSON: () => ({}) });
    fireEvent(mara, new MouseEvent("pointerdown", { button: 0, clientX: 100, clientY: 100, bubbles: true }));
    fireEvent(graph, new MouseEvent("pointermove", { clientX: 180, clientY: 150, bubbles: true }));
    fireEvent(graph, new MouseEvent("pointerup", { clientX: 180, clientY: 150, bubbles: true }));
    expect(await screen.findByText("Canvas layout updated.")).toBeVisible();
    expect(layout).toHaveBeenCalledTimes(1);
    const saved = await repository.readWorld(record.snapshot.worldId);
    expect(saved.status).toBe("found");
    if (saved.status === "found") {
      expect(saved.record.localRevision).toBe(record.localRevision);
      expect(saved.record.layoutRevision).toBe(record.layoutRevision + 1);
      expect(saved.record.layout.positions[record.snapshot.objects[0].id]).toEqual({ x: 1240, y: 925 });
    }
  });

  it("pans the background and supports zoom/fit without writing graph state", async () => {
    const { record } = await graphRecord();
    const layout = vi.fn();
    render(<WorldGraphCanvas record={record} onMoveObjects={layout} />);
    const graph = screen.getByRole("group", { name: "The Ember Coast world graph" });
    const scene = screen.getByTestId("graph-scene");
    const initial = scene.getAttribute("transform");
    fireEvent(graph, new MouseEvent("pointerdown", { button: 0, clientX: 20, clientY: 20, bubbles: true }));
    fireEvent(graph, new MouseEvent("pointermove", { clientX: 120, clientY: 70, bubbles: true }));
    expect(scene.getAttribute("transform")).not.toBe(initial);
    fireEvent(graph, new MouseEvent("pointerup", { clientX: 120, clientY: 70, bubbles: true }));
    const panned = scene.getAttribute("transform");
    fireEvent.keyDown(graph, { key: "ArrowRight" });
    expect(scene.getAttribute("transform")).not.toBe(panned);
    fireEvent.click(screen.getByRole("button", { name: "Zoom in" }));
    const zoomed = scene.getAttribute("transform");
    fireEvent.keyDown(graph, { key: "-" });
    expect(scene.getAttribute("transform")).not.toBe(zoomed);
    fireEvent.click(screen.getByRole("button", { name: "Fit graph" }));
    expect(scene.getAttribute("transform")).toBe(initial);
    expect(layout).not.toHaveBeenCalled();
    expect(graph).toHaveAttribute("tabindex", "0");
  });

  it("previews node movement and edges at zoom, saves once on release and does not select after drag", async () => {
    const { record } = await graphRecord();
    const pending = deferred<WriteLayoutResult>();
    const layout = vi.fn(() => pending.promise);
    render(<WorldGraphCanvas record={record} onMoveObjects={layout} />);
    const graph = screen.getByRole("group", { name: "The Ember Coast world graph" });
    const mara = screen.getByRole("button", { name: "Mara Venn, person" });
    const edge = graph.querySelector("[data-edge-id] path")!;
    const initialEdge = edge.getAttribute("d");
    fireEvent.click(screen.getByRole("button", { name: "100%" }));
    fireEvent.click(screen.getByRole("button", { name: "Zoom in" }));
    fireEvent(mara, new MouseEvent("pointerdown", { button: 0, clientX: 100, clientY: 100, bubbles: true }));
    fireEvent(graph, new MouseEvent("pointermove", { clientX: 150, clientY: 125, bubbles: true }));
    expect(mara).toHaveAttribute("transform", "translate(120 100)");
    expect(edge.getAttribute("d")).not.toBe(initialEdge);
    expect(layout).not.toHaveBeenCalled();
    fireEvent(graph, new MouseEvent("pointerup", { clientX: 150, clientY: 125, bubbles: true }));
    fireEvent.lostPointerCapture(graph);
    expect(mara).toHaveAttribute("transform", "translate(120 100)");
    fireEvent.click(mara);
    expect(mara).toHaveAttribute("aria-pressed", "false");
    expect(layout).toHaveBeenCalledExactlyOnceWith(record, { [record.snapshot.objects[0].id]: { x: 120, y: 100 } });
    pending.resolve({ status: "error", message: "Layout could not be saved" });
    expect(await screen.findByText("Layout could not be saved")).toBeVisible();
    expect(mara).toHaveAttribute("transform", "translate(80 80)");
    fireEvent.click(mara);
    expect(mara).toHaveAttribute("aria-pressed", "true");
  });

  it.each(["pointercancel", "lostpointercapture", "Escape"])("cancels transient movement on %s without saving", async (reason) => {
    const { record } = await graphRecord();
    const layout = vi.fn();
    render(<WorldGraphCanvas record={record} onMoveObjects={layout} />);
    const graph = screen.getByRole("group", { name: "The Ember Coast world graph" });
    const mara = screen.getByRole("button", { name: "Mara Venn, person" });
    fireEvent(mara, new MouseEvent("pointerdown", { button: 0, clientX: 100, clientY: 100, bubbles: true }));
    fireEvent(graph, new MouseEvent("pointermove", { clientX: 160, clientY: 140, bubbles: true }));
    expect(mara.getAttribute("transform")).not.toBe("translate(80 80)");
    if (reason === "Escape") fireEvent.keyDown(graph, { key: "Escape" });
    else fireEvent(graph, new MouseEvent(reason, { bubbles: true }));
    fireEvent(graph, new MouseEvent("pointerup", { clientX: 160, clientY: 140, bubbles: true }));
    expect(mara).toHaveAttribute("transform", "translate(80 80)");
    expect(layout).not.toHaveBeenCalled();
  });

  it("invalidates an active drag on a newer controlled revision and preserves the latest saved positions", async () => {
    const { record } = await graphRecord();
    const layout = vi.fn();
    const view = render(<WorldGraphCanvas record={record} onMoveObjects={layout} />);
    const graph = screen.getByRole("group", { name: "The Ember Coast world graph" });
    const mara = screen.getByRole("button", { name: "Mara Venn, person" });
    fireEvent(mara, new MouseEvent("pointerdown", { button: 0, clientX: 100, clientY: 100, bubbles: true }));
    fireEvent(graph, new MouseEvent("pointermove", { clientX: 160, clientY: 140, bubbles: true }));
    const updated = { ...record, layoutRevision: record.layoutRevision + 1, layout: { ...record.layout, positions: { [record.snapshot.objects[0].id]: { x: 900, y: 500 } } } };
    view.rerender(<WorldGraphCanvas record={updated} onMoveObjects={layout} />);
    fireEvent(graph, new MouseEvent("pointerup", { clientX: 160, clientY: 140, bubbles: true }));
    expect(mara).toHaveAttribute("transform", "translate(900 500)");
    expect(layout).not.toHaveBeenCalled();
  });

  it("wraps long predicate labels on opaque plates and preserves full accessible text", async () => {
    const { record } = await graphRecord();
    const predicate = "has promised to protect during the winter gathering and beyond";
    const relationship = { ...record.snapshot.relationships[0], kind: predicate };
    render(<WorldGraphCanvas record={{ ...record, snapshot: { ...record.snapshot, relationships: [relationship] } }} />);
    const edge = screen.getByRole("img", { name: `Mara Venn ${predicate} Tomas Reed` });
    expect(edge.querySelector("rect")).toHaveClass("world-graph-canvas__edge-label");
    expect(edge.querySelectorAll("tspan").length).toBeGreaterThan(1);
    expect(edge.querySelector("title")?.textContent).toContain(predicate);
    expect(edge.querySelector("path")?.getAttribute("d")).not.toContain("M 164 118 ");
  });

  it.each(["vertical reciprocal", "horizontal multiline", "self loops", "coincident endpoints"])("keeps %s predicate plates disjoint", async (shape) => {
    const { record } = await graphRecord();
    const [first, second] = record.snapshot.objects;
    const relationships = [0, 1, 2].map((index) => ({ ...record.snapshot.relationships[0],
      id: `${record.snapshot.worldId}:relationship:lane-${index}` as LocalWorldRelationship["id"],
      fromObjectId: shape === "vertical reciprocal" && index === 1 ? second.id : first.id,
      toObjectId: shape === "self loops" || (shape === "vertical reciprocal" && index === 1) ? first.id : second.id,
      kind: shape === "horizontal multiline" ? "has promised to protect during the winter gathering and beyond" : "attends",
    }));
    const positions = { [first.id]: { x: 100, y: 100 }, [second.id]: shape === "vertical reciprocal" ? { x: 100, y: 500 } : shape === "coincident endpoints" ? { x: 100, y: 100 } : { x: 700, y: 100 } };
    render(<WorldGraphCanvas record={{ ...record, snapshot: { ...record.snapshot, relationships }, layout: { ...record.layout, positions } }} />);
    const plates = [...document.querySelectorAll(".world-graph-canvas__edge-label")].map((element) => ({
      x: Number(element.getAttribute("x")), y: Number(element.getAttribute("y")),
      width: Number(element.getAttribute("width")), height: Number(element.getAttribute("height")),
    }));
    expect(plates).toHaveLength(3);
    for (let i = 0; i < plates.length; i += 1) {
      for (let j = i + 1; j < plates.length; j += 1) {
        const a = plates[i]; const b = plates[j];
        expect(a.x + a.width < b.x || b.x + b.width < a.x || a.y + a.height < b.y || b.y + b.height < a.y).toBe(true);
      }
    }
  });

  it("fits all multiline parallel and reciprocal predicate plates into a narrow viewport", async () => {
    const { record } = await graphRecord();
    const [first, second] = record.snapshot.objects;
    let resize!: ResizeObserverCallback;
    class TestResizeObserver {
      constructor(callback: ResizeObserverCallback) { resize = callback; }
      observe() {} unobserve() {} disconnect() {}
    }
    vi.stubGlobal("ResizeObserver", TestResizeObserver);
    try {
      const relationships = Array.from({ length: 7 }, (_, index) => ({ ...record.snapshot.relationships[0],
        id: `${record.snapshot.worldId}:relationship:fit-${index}` as LocalWorldRelationship["id"],
        fromObjectId: index % 2 ? second.id : first.id, toObjectId: index % 2 ? first.id : second.id,
        kind: "abcdefghijklmnopqrstuvwx protects the winter gathering and beyond",
      }));
      const positions = { [first.id]: { x: 100, y: 100 }, [second.id]: { x: 100, y: 500 } };
      render(<WorldGraphCanvas record={{ ...record, snapshot: { ...record.snapshot, objects: [first, second], relationships }, layout: { ...record.layout, positions } }} />);
      act(() => resize([{ contentRect: { width: 600, height: 520 } } as ResizeObserverEntry], {} as ResizeObserver));
      fireEvent.click(screen.getByRole("button", { name: "Zoom in" }));
      fireEvent.click(screen.getByRole("button", { name: "Fit graph" }));
      const transform = screen.getByTestId("graph-scene").getAttribute("transform")!;
      const [, x, y, zoom] = transform.match(/translate\(([-.\d]+) ([-.\d]+)\) scale\(([-.\d]+)\)/)!.map(Number);
      for (const plate of document.querySelectorAll(".world-graph-canvas__edge-label")) {
        const left = Number(plate.getAttribute("x")); const top = Number(plate.getAttribute("y"));
        const right = left + Number(plate.getAttribute("width")); const bottom = top + Number(plate.getAttribute("height"));
        expect(left * zoom + x).toBeGreaterThanOrEqual(0);
        expect(top * zoom + y).toBeGreaterThanOrEqual(0);
        expect(right * zoom + x).toBeLessThanOrEqual(600);
        expect(bottom * zoom + y).toBeLessThanOrEqual(520);
      }
    } finally { vi.unstubAllGlobals(); }
  });

  it("keeps stale conflict candidates and reports them without replacing the controlled graph", async () => {
    const user = userEvent.setup();
    const { repository, record } = await graphRecord();
    const adapter = createLocalWorldGraphAdapter(repository);
    const winner = await adapter.renameObject(record, record.snapshot.objects[0].id, "Mara Winner");
    expect(winner.status).toBe("committed");
    let delivered: CommitSemanticResult | undefined;
    render(<WorldGraphCanvas record={record}
      onRenameObject={(current, id, name) => adapter.renameObject(current, id, name)}
      onSemanticResult={(result) => { delivered = result; }} />);
    await user.click(screen.getByRole("button", { name: "Mara Venn, person" }));
    await user.click(screen.getByRole("button", { name: "Rename Mara Venn" }));
    const input = screen.getByLabelText("New name");
    await user.clear(input);
    await user.type(input, "Mara Candidate");
    await user.click(screen.getByRole("button", { name: "Save name" }));

    expect(await screen.findByText(/conflict candidate/)).toBeVisible();
    expect(delivered?.status).toBe("conflict");
    if (delivered?.status === "conflict") expect(delivered.candidate.proposedSnapshot.objects[0].name).toBe("Mara Candidate");
    expect(screen.getByRole("button", { name: "Mara Venn, person" })).toBeVisible();
  });
});


it("does not rebuild the full corpus index or projection when only the camera changes", async () => {
  const { record } = await graphRecord();
  const index = vi.spyOn(projectionModule, "indexLocalWorldGraph");
  const project = vi.spyOn(projectionModule, "projectLocalWorldGraph");
  render(<WorldGraphCanvas record={record} />);
  const indexed = index.mock.calls.length;
  const projected = project.mock.calls.length;
  fireEvent.click(screen.getByRole("button", {name: "Zoom in"}));
  fireEvent.click(screen.getByRole("button", {name: "Zoom out"}));
  fireEvent.click(screen.getByRole("button", {name: "Fit graph"}));
  expect(index).toHaveBeenCalledTimes(indexed);
  expect(project).toHaveBeenCalledTimes(projected);
  index.mockRestore(); project.mockRestore();
});

describe("full loaded SVG overview", () => {
  it("pans from a bubble by default without moving, selecting, or creating anything", async () => {
    const { record } = await graphRecord();
    const save = vi.fn(), select = vi.fn(), create = vi.fn();
    render(<WorldGraphCanvas record={record} nodeShape="circle" projectionOptions={{ fullCorpus: true }}
      onMoveObjects={save} onSelectionChange={select} onCanvasCreateRequest={create} creationKinds={[{ kind: "person", label: "Person" }]} />);
    const svg = screen.getByRole("group", { name: "The Ember Coast world graph" });
    captureRect(svg);
    const scene = screen.getByTestId("graph-scene"), before = cameraFromScene(scene);
    const node = screen.getByRole("button", { name: "Mara Venn, person" }), position = node.getAttribute("transform");
    expect(select).toHaveBeenCalledExactlyOnceWith(null); select.mockClear();
    expect(screen.getByRole("button", { name: "Pan graph" })).toHaveAttribute("aria-pressed", "true");
    dispatchPointer(node, "pointerdown", { pointerId: 91, button: 0, clientX: 100, clientY: 100 });
    dispatchPointer(svg, "pointermove", { pointerId: 91, clientX: 160, clientY: 140 });
    dispatchPointer(svg, "pointerup", { pointerId: 91, clientX: 160, clientY: 140 });
    fireEvent.click(node); // Browser click following a completed drag must not select.
    expect(cameraFromScene(scene)).toEqual({ ...before, x: before.x + 60, y: before.y + 40 });
    expect(node).toHaveAttribute("transform", position!);
    expect(node).toHaveAttribute("aria-pressed", "false");
    expect(save).not.toHaveBeenCalled(); expect(select).not.toHaveBeenCalled(); expect(create).not.toHaveBeenCalled();
    expect(screen.queryByText("Place a node here")).not.toBeInTheDocument();
    dispatchPointer(node, "pointerdown", { pointerId: 92, button: 0, clientX: 160, clientY: 140 });
    dispatchPointer(svg, "pointerup", { pointerId: 92, clientX: 160, clientY: 140 });
    fireEvent.click(node);
    expect(node).toHaveAttribute("aria-pressed", "true");
    expect(select).toHaveBeenLastCalledWith(record.snapshot.objects[0].id);
    expect(screen.queryByText("Place a node here")).not.toBeInTheDocument();
  });

  it("requires Move nodes for pointer edits, then returns to safe keyboard panning", async () => {
    const { repository, record } = await graphRecord();
    const adapter = createLocalWorldGraphAdapter(repository);
    const save = vi.fn((current: LocalWorldRecord, positions: Readonly<Record<string, { x: number; y: number }>>) => adapter.moveObjects(current, positions));
    render(<WorldGraphCanvas record={record} nodeShape="circle" projectionOptions={{ fullCorpus: true }} onMoveObjects={save} />);
    const svg = screen.getByRole("group", { name: "The Ember Coast world graph" }); captureRect(svg);
    const node = screen.getByRole("button", { name: "Mara Venn, person" }), scene = screen.getByTestId("graph-scene");
    const initial = cameraFromScene(scene), position = node.getAttribute("transform");
    fireEvent.keyDown(node, { key: "ArrowRight" });
    expect(cameraFromScene(scene)).toEqual({ ...initial, x: initial.x - 32 });
    expect(save).not.toHaveBeenCalled(); expect(node).toHaveAttribute("transform", position!);
    fireEvent.click(screen.getByRole("button", { name: "Move nodes" }));
    expect(screen.getByRole("button", { name: "Move nodes" })).toHaveAttribute("aria-pressed", "true");
    const camera = scene.getAttribute("transform");
    dispatchPointer(node, "pointerdown", { pointerId: 93, button: 0, clientX: 100, clientY: 100 });
    dispatchPointer(svg, "pointermove", { pointerId: 93, clientX: 130, clientY: 120 });
    expect(node.getAttribute("transform")).not.toBe(position);
    dispatchPointer(svg, "pointerup", { pointerId: 93, clientX: 130, clientY: 120 });
    await screen.findByText("Canvas layout updated.");
    expect(save).toHaveBeenCalledTimes(1); expect(scene).toHaveAttribute("transform", camera!);
    fireEvent.click(screen.getByRole("button", { name: "Pan graph" }));
    fireEvent.keyDown(node, { key: "ArrowLeft" });
    expect(save).toHaveBeenCalledTimes(1);
    expect(cameraFromScene(scene).x).toBe(initial.x);
  });

  it("keeps intentional keyboard node movement in Move nodes mode", async () => {
    const { repository, record } = await graphRecord();
    const adapter = createLocalWorldGraphAdapter(repository);
    const save = vi.fn((current: LocalWorldRecord, positions: Readonly<Record<string, { x: number; y: number }>>) => adapter.moveObjects(current, positions));
    render(<WorldGraphCanvas record={record} nodeShape="circle" projectionOptions={{ fullCorpus: true }} onMoveObjects={save} />);
    const node = screen.getByRole("button", { name: "Mara Venn, person" }), scene = screen.getByTestId("graph-scene");
    const before = scene.getAttribute("transform");
    const position = node.getAttribute("transform")!.match(/translate\(([-.\d]+) ([-.\d]+)\)/)!;
    fireEvent.click(screen.getByRole("button", { name: "Move nodes" }));
    fireEvent.keyDown(node, { key: "ArrowRight", shiftKey: true });
    await screen.findByText("Canvas layout updated.");
    expect(save).toHaveBeenCalledExactlyOnceWith(record, { [record.snapshot.objects[0].id]: { x: Number(position[1]) + 24, y: Number(position[2]) } });
    expect(scene).toHaveAttribute("transform", before!);
  });

  it.each(["Escape", "pointercancel", "mode change"])("cancels an unfinished node-origin pan on %s without a layout write", async (interruption) => {
    const { record } = await graphRecord(); const save = vi.fn();
    render(<WorldGraphCanvas record={record} nodeShape="circle" projectionOptions={{ fullCorpus: true }} onMoveObjects={save} />);
    const svg = screen.getByRole("group", { name: "The Ember Coast world graph" }); captureRect(svg);
    const node = screen.getByRole("button", { name: "Mara Venn, person" });
    const initial = screen.getByTestId("graph-scene").getAttribute("transform");
    dispatchPointer(node, "pointerdown", { pointerId: 94, button: 0, clientX: 100, clientY: 100 });
    dispatchPointer(svg, "pointermove", { pointerId: 94, clientX: 170, clientY: 140 });
    if (interruption === "Escape") fireEvent.keyDown(node, { key: "Escape" });
    else if (interruption === "pointercancel") dispatchPointer(svg, "pointercancel", { pointerId: 94 });
    else fireEvent.click(screen.getByRole("button", { name: "Move nodes" }));
    dispatchPointer(svg, "pointerup", { pointerId: 94, clientX: 170, clientY: 140 });
    expect(screen.getByTestId("graph-scene")).toHaveAttribute("transform", initial!);
    expect(save).not.toHaveBeenCalled(); expect(node).toHaveAttribute("aria-pressed", "false");
  });

  it("cancels a node move when switching to Pan and resets to Pan for another World", async () => {
    const { record } = await graphRecord(); const save = vi.fn();
    const view = render(<WorldGraphCanvas record={record} nodeShape="circle" projectionOptions={{ fullCorpus: true }} onMoveObjects={save} />);
    const svg = screen.getByRole("group", { name: "The Ember Coast world graph" }); captureRect(svg);
    const node = screen.getByRole("button", { name: "Mara Venn, person" }), position = node.getAttribute("transform");
    fireEvent.click(screen.getByRole("button", { name: "Move nodes" }));
    dispatchPointer(node, "pointerdown", { pointerId: 95, button: 0, clientX: 100, clientY: 100 });
    dispatchPointer(svg, "pointermove", { pointerId: 95, clientX: 170, clientY: 140 });
    fireEvent.click(screen.getByRole("button", { name: "Pan graph" }));
    dispatchPointer(svg, "pointerup", { pointerId: 95, clientX: 170, clientY: 140 });
    expect(node).toHaveAttribute("transform", position!); expect(save).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Move nodes" }));
    view.rerender(<WorldGraphCanvas record={{ ...record, snapshot: { ...record.snapshot, worldId: "other-world" as typeof record.snapshot.worldId } }} nodeShape="circle" projectionOptions={{ fullCorpus: true }} onMoveObjects={save} />);
    expect(screen.getByRole("button", { name: "Pan graph" })).toHaveAttribute("aria-pressed", "true");
  });

  it("allows node-origin navigation when layout edits are unavailable", async () => {
    const { record } = await graphRecord();
    render(<WorldGraphCanvas record={record} nodeShape="circle" projectionOptions={{ fullCorpus: true }} interactionDisabled />);
    const svg = screen.getByRole("group", { name: "The Ember Coast world graph" }); captureRect(svg);
    const node = screen.getByRole("button", { name: "Mara Venn, person" }), scene = screen.getByTestId("graph-scene");
    const before = scene.getAttribute("transform");
    expect(screen.getByRole("button", { name: "Move nodes" })).toBeDisabled();
    dispatchPointer(node, "pointerdown", { pointerId: 96, button: 0, clientX: 100, clientY: 100 });
    dispatchPointer(svg, "pointerup", { pointerId: 96, clientX: 160, clientY: 140 });
    expect(scene.getAttribute("transform")).not.toBe(before);
    fireEvent.keyDown(node, { key: "0" });
    expect(scene).toHaveAttribute("transform", before!);
  });

  it.each(["local revision", "layout revision", "World"])("releases node-origin pan capture and suppresses its trailing click across %s changes", async (change) => {
    const { record } = await graphRecord(); const save = vi.fn();
    const props = { nodeShape: "circle" as const, projectionOptions: { fullCorpus: true }, onMoveObjects: save };
    const view = render(<WorldGraphCanvas record={record} {...props} />);
    const svg = screen.getByRole("group", { name: "The Ember Coast world graph" }); captureRect(svg);
    const node = screen.getByRole("button", { name: "Mara Venn, person" });
    const release = vi.fn(); Object.defineProperty(node, "releasePointerCapture", { configurable: true, value: release });
    dispatchPointer(node, "pointerdown", { pointerId: 97, button: 0, clientX: 100, clientY: 100 });
    dispatchPointer(svg, "pointermove", { pointerId: 97, clientX: 170, clientY: 140 });
    const next = change === "local revision" ? { ...record, localRevision: record.localRevision + 1 }
      : change === "layout revision" ? { ...record, layoutRevision: record.layoutRevision + 1 }
      : { ...record, snapshot: { ...record.snapshot, worldId: "reused-node-ids" as typeof record.snapshot.worldId } };
    view.rerender(<WorldGraphCanvas record={next} {...props} />);
    expect(release).toHaveBeenCalledExactlyOnceWith(97);
    dispatchPointer(svg, "pointerup", { pointerId: 97, clientX: 170, clientY: 140 });
    fireEvent.click(screen.getByRole("button", { name: "Mara Venn, person" }));
    expect(screen.getByRole("button", { name: "Mara Venn, person" })).toHaveAttribute("aria-pressed", "false");
    expect(save).not.toHaveBeenCalled();
  });

  it("cannot finish a stale node move after editing is disabled and enabled again", async () => {
    const { record } = await graphRecord(); const save = vi.fn();
    const props = { record, nodeShape: "circle" as const, projectionOptions: { fullCorpus: true }, onMoveObjects: save };
    const view = render(<WorldGraphCanvas {...props} />);
    const svg = screen.getByRole("group", { name: "The Ember Coast world graph" }); captureRect(svg);
    const node = screen.getByRole("button", { name: "Mara Venn, person" }), position = node.getAttribute("transform");
    const release = vi.fn(); Object.defineProperty(node, "releasePointerCapture", { configurable: true, value: release });
    fireEvent.click(screen.getByRole("button", { name: "Move nodes" }));
    dispatchPointer(node, "pointerdown", { pointerId: 98, button: 0, clientX: 100, clientY: 100 });
    dispatchPointer(svg, "pointermove", { pointerId: 98, clientX: 170, clientY: 140 });
    view.rerender(<WorldGraphCanvas {...props} interactionDisabled />);
    expect(release).toHaveBeenCalledExactlyOnceWith(98);
    expect(node).toHaveAttribute("transform", position!);
    view.rerender(<WorldGraphCanvas {...props} />);
    dispatchPointer(svg, "pointerup", { pointerId: 98, clientX: 170, clientY: 140 });
    fireEvent.click(node);
    expect(save).not.toHaveBeenCalled(); expect(node).toHaveAttribute("aria-pressed", "false");
  });

  it("fits persisted geometry when keyboard Fit interrupts a connected-node drag", async () => {
    const { record } = await graphRecord();
    const save = vi.fn();
    render(<WorldGraphCanvas record={record} nodeShape="circle" projectionOptions={{ fullCorpus: true }} onMoveObjects={save} />);
    const svg = screen.getByRole("group", { name: "The Ember Coast world graph" });
    captureRect(svg);
    fireEvent.click(screen.getByRole("button", { name: "Move nodes" }));
    fireEvent.click(screen.getByRole("button", { name: "Fit graph" }));
    const camera = screen.getByTestId("graph-scene").getAttribute("transform")!;
    const first = document.querySelector(`[data-node-id="${record.snapshot.objects[0].id}"]`)!;
    const position = first.getAttribute("transform")!;
    dispatchPointer(first, "pointerdown", { pointerId: 14, clientX: 100, clientY: 100, button: 0 });
    dispatchPointer(svg, "pointermove", { pointerId: 14, clientX: 1100, clientY: 800, buttons: 1 });
    expect(first.getAttribute("transform")).not.toBe(position);
    fireEvent.keyDown(svg, { key: "0" });
    expect(first).toHaveAttribute("transform", position);
    expect(screen.getByTestId("graph-scene")).toHaveAttribute("transform", camera);
    expect(save).not.toHaveBeenCalled();
  });

  it("keeps revealed kind labels at readable contrast on each bubble palette color", async () => {
    const { record } = await graphRecord();
    const kinds = ["npc", "pc", "item", "event", "person", "location", "faction", "item", "creature", "source", "entity", "constructor", "__proto__"];
    const objects = kinds.map((kind, i) => ({ ...record.snapshot.objects[0], id: `${record.snapshot.worldId}:contrast:${i}` as LocalWorldRecord["snapshot"]["objects"][number]["id"], name: kind, kind }));
    render(<WorldGraphCanvas record={{ ...record, snapshot: { ...record.snapshot, objects, relationships: [] } }} nodeShape="circle" projectionOptions={{ fullCorpus: true, showUnconnected: true }} />);
    const graphStyles = readFileSync(fileURLToPath(import.meta.url).replace(/WorldGraphCanvas\.test\.tsx$/, "worldGraphCanvas.css"), "utf8");
    expect(graphStyles).toContain(".world-graph-canvas--full .world-graph-canvas__node-kind { fill: var(--graph-ink); }");
    // More specific than the generic button:hover:not(:disabled) rule, including its text color.
    expect(graphStyles).toContain('.world-graph-canvas .world-graph-canvas__drag-mode button[aria-pressed="true"]:hover,');
    expect(graphStyles).toContain('.world-graph-canvas .world-graph-canvas__drag-mode button[aria-pressed="true"]:focus-visible { background: var(--graph-ink); color: #fffdf7; border-color: var(--graph-ink); }');
    const ink = graphStyles.match(/--graph-ink: (#[0-9a-f]{6})/)![1];
    function luminance(hex: string) {
      const channels = [1, 3, 5].map((offset) => parseInt(hex.slice(offset, offset + 2), 16) / 255).map((value) => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
      return channels[0] * .2126 + channels[1] * .7152 + channels[2] * .0722;
    }
    const colors = [...document.querySelectorAll<SVGElement>("[data-node-id]")].map((node) => node.style.getPropertyValue("--node-color"));
    expect(new Set(colors.slice(0, 4)).size).toBe(4);
    for (const color of colors) expect((luminance(color) + .05) / (luminance(ink) + .05)).toBeGreaterThanOrEqual(4.5);
  });

  it("zooms a compact full graph below Fit until the enabled control reaches its floor", async () => {
    const { record } = await graphRecord();
    render(<WorldGraphCanvas record={record} nodeShape="circle" projectionOptions={{ fullCorpus: true }} />);
    fireEvent.click(screen.getByRole("button", { name: "100%" }));
    fireEvent.click(screen.getByRole("button", { name: "Zoom out" }));
    expect(screen.getByLabelText("Graph zoom")).toHaveTextContent("80%");
    const button = screen.getByRole("button", { name: "Zoom out" });
    for (let i = 0; i < 20 && !button.hasAttribute("disabled"); i += 1) {
      const before = cameraFromScene(screen.getByTestId("graph-scene")).zoom;
      fireEvent.click(button);
      expect(cameraFromScene(screen.getByTestId("graph-scene")).zoom).toBeLessThan(before);
    }
    expect(button).toBeDisabled();
    expect(screen.getByLabelText("Graph zoom")).toHaveTextContent("15%");
  });

  it("keeps camera motion out of projection and edge geometry while preserving selection", async () => {
    const { record } = await graphRecord();
    const indexSpy = vi.spyOn(projectionModule, "indexLocalWorldGraph");
    const layoutSpy = vi.spyOn(projectionModule, "createGraphFallbackPositions");
    const projectionSpy = vi.spyOn(projectionModule, "projectLocalWorldGraph");
    const geometrySpy = vi.spyOn(Math, "hypot");
    const view = render(<WorldGraphCanvas record={record} nodeShape="circle" projectionOptions={{ fullCorpus: true }} />);
    const first = document.querySelector(`[data-node-id="${record.snapshot.objects[0].id}"]`)!;
    fireEvent.click(first);
    const scene = screen.getByTestId("graph-scene");
    const edges = [...document.querySelectorAll("[data-edge-id] path")];
    const paths = edges.map((edge) => edge.getAttribute("d"));
    const counts = [indexSpy.mock.calls.length, layoutSpy.mock.calls.length, projectionSpy.mock.calls.length, geometrySpy.mock.calls.length];
    fireEvent.click(screen.getByRole("button", { name: "Zoom in" }));
    fireEvent.keyDown(screen.getByRole("group", { name: "The Ember Coast world graph" }), { key: "ArrowLeft" });
    expect(first).toHaveAttribute("aria-pressed", "true");
    expect(document.querySelector(`[data-node-id="${record.snapshot.objects[0].id}"]`)).toBe(first);
    expect([...document.querySelectorAll("[data-edge-id] path")]).toEqual(edges);
    expect(edges.map((edge) => edge.getAttribute("d"))).toEqual(paths);
    expect([indexSpy.mock.calls.length, layoutSpy.mock.calls.length, projectionSpy.mock.calls.length, geometrySpy.mock.calls.length]).toEqual(counts);
    fireEvent.click(screen.getByRole("button", { name: "100%" }));
    expect(scene).toHaveAttribute("data-detail", "relationships");
    expect(first.getAttribute("style")).toContain("--node-color");
    expect(screen.getByLabelText("Object type colors")).toHaveTextContent("person");
    view.unmount();
    vi.restoreAllMocks();
  });

  it("retains fallback positions and camera on a revision addition without saving layout", async () => {
    const { record } = await graphRecord();
    const save = vi.fn();
    const options = { fullCorpus: true };
    const view = render(<WorldGraphCanvas record={record} nodeShape="circle" projectionOptions={options} onMoveObjects={save} />);
    const before = new Map([...document.querySelectorAll("[data-node-id]")].map((node) => [node.getAttribute("data-node-id"), node.getAttribute("transform")]));
    fireEvent.keyDown(screen.getByRole("group", { name: "The Ember Coast world graph" }), { key: "ArrowRight" });
    const camera = screen.getByTestId("graph-scene").getAttribute("transform");
    const added = { ...record.snapshot.objects[0], id: `${record.snapshot.worldId}:object:new` as LocalWorldRecord["snapshot"]["objects"][number]["id"], name: "A new arrival" };
    const next = { ...record, localRevision: record.localRevision + 1, snapshot: { ...record.snapshot, objects: [added, ...record.snapshot.objects].reverse() } };
    view.rerender(<WorldGraphCanvas record={next} revealObjectId={added.id} nodeShape="circle" projectionOptions={options} onMoveObjects={save} />);
    for (const [id, transform] of before) expect(document.querySelector(`[data-node-id="${id}"]`)).toHaveAttribute("transform", transform!);
    expect(screen.getByTestId("graph-scene")).toHaveAttribute("transform", camera!);
    expect(document.querySelectorAll("[data-node-id]")).toHaveLength(5);
    expect(save).not.toHaveBeenCalled();
  });
});

describe("loaded relationship density", () => {
  it("hides isolates by default, reveals exact focus and selection, and offers an all-isolate escape", async () => {
    const { record } = await graphRecord();
    const isolated = { ...record, snapshot: { ...record.snapshot, relationships: [] } };
    const props = { record: isolated, nodeShape: "circle" as const, projectionOptions: { fullCorpus: true } };
    const view = render(<WorldGraphCanvas {...props} />);
    expect(document.querySelectorAll("[data-node-id]")).toHaveLength(0);
    expect(screen.getByText(/No connected objects in the loaded snapshot/)).toBeVisible();
    expect(screen.queryByText("This World has no objects yet. Add an object to begin.")).not.toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /Show objects without listed relationships \(4 hidden\)/ })).not.toBeChecked();
    fireEvent.click(screen.getByRole("checkbox", { name: /Show objects without listed relationships/ }));
    expect(document.querySelectorAll("[data-node-id]")).toHaveLength(4);
    fireEvent.click(screen.getByRole("button", { name: "Mara Venn, person" }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Show objects without listed relationships/ }));
    expect(document.querySelectorAll("[data-node-id]")).toHaveLength(1);
    view.rerender(<WorldGraphCanvas {...props} cameraFocusRequest={{ nodeId: record.snapshot.objects[1].id, requestId: 1, selectNode: true }} />);
    expect(screen.getByRole("button", { name: "Tomas Reed, person" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("checkbox", { name: /3 hidden/ })).not.toBeChecked();
    view.rerender(<WorldGraphCanvas {...props} revealObjectId={record.snapshot.objects[2].id} />);
    expect(screen.getByRole("button", { name: "The Glass Orchard, location" })).toBeInTheDocument();
    expect(document.querySelectorAll("[data-node-id]")).toHaveLength(2);
  });

  it("uses bounded loaded degree area with stable centers, full names and unequal edge endpoints", async () => {
    const { record } = await graphRecord();
    const objects = record.snapshot.objects.slice(0, 3).map((object, i) => ({ ...object,
      kind: ["npc", "pc", "item"][i], properties: { recordedNames: [object.name, `Full alternative ${i}`] } }));
    // One connection plus 30 / 100 distinct self-loop IDs gives degrees 1, 31, 100.
    const relationships = [{ ...record.snapshot.relationships[0], fromObjectId: objects[0].id, toObjectId: objects[1].id },
      ...[30, 100].flatMap((count, i) => Array.from({ length: count }, (_, j) => ({ ...record.snapshot.relationships[0],
        id: `density-${i}-${j}` as LocalWorldRelationship["id"], fromObjectId: objects[i + 1].id, toObjectId: objects[i + 1].id })))];
    const dense = { ...record, snapshot: { ...record.snapshot, objects, relationships },
      layout: { ...record.layout, positions: Object.fromEntries(objects.map((object, i) => [object.id, { x: i * 500, y: 0 }])) } };
    const view = render(<WorldGraphCanvas record={dense} nodeShape="circle" projectionOptions={{ fullCorpus: true }} onConnectRequest={vi.fn()} />);
    const nodes = objects.map((object) => document.querySelector(`[data-node-id="${object.id}"]`)!);
    const radii = nodes.map((node) => Number(node.querySelector(".world-graph-canvas__node-circle")!.getAttribute("r")));
    expect(radii[0]).toBeGreaterThanOrEqual(22);
    expect(radii[1] - radii[0]).toBeGreaterThan(10);
    expect(radii[2] - radii[1]).toBeGreaterThan(4);
    expect(radii[2]).toBeCloseTo(24 * Math.sqrt(40));
    nodes.forEach((node, i) => {
      expect(node.querySelector("circle")).toHaveAttribute("cx", "56");
      expect(node.querySelector("title")).toHaveTextContent(`Full alternative ${i}`);
      expect(node).toHaveAttribute("aria-description", expect.stringContaining(`${[1, 31, 100][i]} relationships in loaded snapshot`));
      expect(Number(node.querySelector(".world-graph-canvas__node-port")!.getAttribute("cx"))).toBeCloseTo(56 + radii[i] - 2);
    });
    const path = document.querySelector(`[data-edge-id="${relationships[0].id}"] path`)!.getAttribute("d")!;
    const values = path.match(/-?\d+(?:\.\d+)?/g)!.map(Number);
    expect(values[0]).toBeCloseTo(56 + radii[0] + 5);
    expect(values[4]).toBeCloseTo(556 - radii[1] - 5);
    expect(document.querySelectorAll("[data-edge-id]")).toHaveLength(131);
    const loopPath = document.querySelector('[data-edge-id="density-0-0"] path')!.getAttribute("d")!;
    const loop = loopPath.match(/-?\d+(?:\.\d+)?/g)!.map(Number);
    expect(Math.hypot(loop[0] - 556, loop[1] - 56)).toBeCloseTo(radii[1] + 5);
    expect(Math.hypot(loop[6] - 556, loop[7] - 56)).toBeCloseTo(radii[1] + 5);
    const coincident = { ...dense, layout: { ...dense.layout, positions: { ...dense.layout.positions, [objects[1].id]: { x: 0, y: 0 } } } };
    view.rerender(<WorldGraphCanvas record={coincident} nodeShape="circle" projectionOptions={{ fullCorpus: true }} />);
    const coincidentPath = document.querySelector(`[data-edge-id="${relationships[0].id}"] path`)!.getAttribute("d")!;
    const endpoints = coincidentPath.match(/-?\d+(?:\.\d+)?/g)!.map(Number);
    expect(Math.hypot(endpoints[0] - 56, endpoints[1] - 56)).toBeCloseTo(radii[0] + 5);
    expect(Math.hypot(endpoints[6] - 56, endpoints[7] - 56)).toBeCloseTo(radii[1] + 5);
    fireEvent.click(screen.getByRole("button", { name: "Zoom in" }));
    view.rerender(<WorldGraphCanvas record={dense} nodeShape="circle" projectionOptions={{ fullCorpus: true, focusObjectId: objects[0].id, neighborhoodDepth: 0 }} />);
    expect(Number(document.querySelector(".world-graph-canvas__node-circle")!.getAttribute("r"))).toBe(radii[0]);
  });
});

it("hit-tests the weighted radius rather than the old maximum footprint", async () => {
  const { record } = await graphRecord();
  const [source, target] = record.snapshot.objects;
  const placed = { ...record, layout: { ...record.layout, positions: {
    [source.id]: { x: 0, y: 0 }, [target.id]: { x: 500, y: 0 },
  } } };
  const onConnectRequest = vi.fn();
  render(<WorldGraphCanvas record={placed} nodeShape="circle" projectionOptions={{ fullCorpus: true }} onConnectRequest={onConnectRequest} />);
  const svg = screen.getByRole("group", { name: "The Ember Coast world graph" });
  captureRect(svg);
  const camera = cameraFromScene(screen.getByTestId("graph-scene"));
  const radius = Number(document.querySelector(`[data-node-id="${target.id}"] .world-graph-canvas__node-circle`)!.getAttribute("r"));
  const port = screen.getByTestId(`connect-port-${source.id}`);
  const start = screenPoint(camera, { x: 90, y: 56 });
  const outside = screenPoint(camera, { x: 556 + radius + 4, y: 56 });
  dispatchPointer(port, "pointerdown", { button: 0, pointerId: 81, clientX: start.x, clientY: start.y });
  dispatchPointer(svg, "pointermove", { pointerId: 81, clientX: outside.x, clientY: outside.y });
  dispatchPointer(svg, "pointerup", { pointerId: 81, clientX: outside.x, clientY: outside.y });
  expect(onConnectRequest).not.toHaveBeenCalled();
  const inside = screenPoint(camera, { x: 556 + radius - 2, y: 56 });
  dispatchPointer(port, "pointerdown", { button: 0, pointerId: 82, clientX: start.x, clientY: start.y });
  dispatchPointer(svg, "pointermove", { pointerId: 82, clientX: inside.x, clientY: inside.y });
  dispatchPointer(svg, "pointerup", { pointerId: 82, clientX: inside.x, clientY: inside.y });
  expect(onConnectRequest).toHaveBeenCalledExactlyOnceWith({ sourceId: source.id, targetId: target.id });
});

it("applies revision resets before a simultaneous exact-object reveal and focus", async () => {
  const { record } = await graphRecord();
  const [old, target] = record.snapshot.objects;
  const onCameraFocusChange = vi.fn();
  const view = render(<WorldGraphCanvas record={record} nodeShape="circle"
    projectionOptions={{ fullCorpus: true, focusObjectId: old.id, neighborhoodDepth: 0 }}
    cameraFocusRequest={{ nodeId: old.id, requestId: 1, selectNode: true }} onCameraFocusChange={onCameraFocusChange} />);
  expect(screen.getByRole("button", { name: "Mara Venn, person" })).toHaveAttribute("aria-pressed", "true");
  onCameraFocusChange.mockClear();
  const next = { ...record, localRevision: record.localRevision + 1, snapshot: { ...record.snapshot, relationships: [] } };
  view.rerender(<WorldGraphCanvas record={next} nodeShape="circle" projectionOptions={{ fullCorpus: true }}
    revealObjectId={target.id} clearCameraFocusRequest={{ requestId: 1, fitView: true }} clearSelectionRequest={1}
    cameraFocusRequest={{ nodeId: target.id, requestId: 2, selectNode: true }} onCameraFocusChange={onCameraFocusChange} />);
  expect(screen.getByRole("button", { name: "Tomas Reed, person" })).toHaveAttribute("aria-pressed", "true");
  expect(onCameraFocusChange).toHaveBeenLastCalledWith(target.id);
  const node = document.querySelector(`[data-node-id="${target.id}"]`)!;
  const [x, y] = node.getAttribute("transform")!.match(/-?\d+(?:\.\d+)?/g)!.map(Number);
  const camera = cameraFromScene(screen.getByTestId("graph-scene"));
  expect(camera.x + (x + 56) * camera.zoom).toBeCloseTo(480);
  expect(camera.y + (y + 56) * camera.zoom).toBeCloseTo(260);
  // A one-node reset overview fits at 100%, not the old focused 135% camera.
  view.rerender(<WorldGraphCanvas record={next} nodeShape="circle" projectionOptions={{ fullCorpus: true }}
    revealObjectId={target.id} clearCameraFocusRequest={{ requestId: 1, fitView: true }} clearSelectionRequest={1}
    cameraFocusRequest={{ nodeId: null, requestId: 3 }} onCameraFocusChange={onCameraFocusChange} />);
  const restored = cameraFromScene(screen.getByTestId("graph-scene"));
  expect(restored.zoom).toBe(1);
  expect(restored.x + (x + 56) * restored.zoom).toBeCloseTo(480);
  expect(restored.y + (y + 56) * restored.zoom).toBeCloseTo(260);
});

it("fits post-reset visibility without a previously selected distant isolate", async () => {
  const { record } = await graphRecord();
  const isolate = { ...record.snapshot.objects[0], id: `${record.snapshot.worldId}:distant-isolate` as LocalWorldRecord["snapshot"]["objects"][number]["id"], name: "Distant isolate" };
  const placed = { ...record, snapshot: { ...record.snapshot, objects: [...record.snapshot.objects, isolate] },
    layout: { ...record.layout, positions: { ...record.layout.positions, [isolate.id]: { x: 5800, y: 5800 } } } };
  const props = { nodeShape: "circle" as const, projectionOptions: { fullCorpus: true } };
  const view = render(<WorldGraphCanvas {...props} record={placed} />);
  const overviewCamera = screen.getByTestId("graph-scene").getAttribute("transform");
  view.rerender(<WorldGraphCanvas {...props} record={placed}
    cameraFocusRequest={{ nodeId: isolate.id, requestId: 1, selectNode: true }} />);
  expect(screen.getByRole("button", { name: "Distant isolate, person" })).toHaveAttribute("aria-pressed", "true");
  view.rerender(<WorldGraphCanvas {...props} record={{ ...placed, localRevision: placed.localRevision + 1 }}
    clearSelectionRequest={1} clearCameraFocusRequest={{ requestId: 1, fitView: true }} />);
  expect(screen.queryByRole("button", { name: "Distant isolate, person" })).not.toBeInTheDocument();
  expect(screen.getByTestId("graph-scene")).toHaveAttribute("transform", overviewCamera!);
});

describe("packed readable overview", () => {
  it("keeps every relationship while quieting crossings and retaining readable hub captions", async () => {
    const { record } = await graphRecord();
    let bubbleRenderReads = 0;
    const objects = Array.from({ length: 513 }, (_, i) => ({ ...record.snapshot.objects[0],
      id: `readable-${i}` as LocalWorldRecord["snapshot"]["objects"][number]["id"], name: `Recorded object ${i}`,
      properties: { get recordedNames() { bubbleRenderReads += 1; return [`Recorded object ${i}`]; } } }));
    const relationships = Array.from({ length: 559 }, (_, i) => ({ ...record.snapshot.relationships[0],
      id: `real-edge-${i}` as LocalWorldRelationship["id"], fromObjectId: objects[i % 513].id, toObjectId: objects[(i + 1) % 513].id }));
    const populated = { ...record, snapshot: { ...record.snapshot, objects, relationships } };
    render(<WorldGraphCanvas record={populated} nodeShape="circle" projectionOptions={{ fullCorpus: true }} />);
    const scene = screen.getByTestId("graph-scene");
    expect(scene).toHaveAttribute("data-detail", "overview");
    expect(scene).toHaveAttribute("data-all-relationships", "false");
    expect(document.querySelectorAll("[data-node-id]")).toHaveLength(513);
    const paths = [...document.querySelectorAll("[data-edge-id] path")];
    expect(paths).toHaveLength(559);
    expect(document.querySelector(".world-graph-canvas__overview-note")).toHaveTextContent("513 loaded objects · 559 real relationships");
    const labels = [...document.querySelectorAll<SVGTextElement>(".world-graph-canvas__overview-label")];
    expect(labels.length).toBeGreaterThan(0);
    expect(labels.length).toBeLessThanOrEqual(8);
    const camera = cameraFromScene(scene);
    for (const label of labels) expect(parseFloat(label.style.fontSize) * camera.zoom).toBeCloseTo(12);
    bubbleRenderReads = 0;
    fireEvent.click(screen.getByRole("button", { name: "Zoom in" }));
    expect(bubbleRenderReads).toBeLessThanOrEqual(16); // Only bounded hub captions, not all 513 memoized bubbles.
    expect([...document.querySelectorAll("[data-edge-id] path")]).toEqual(paths);
    fireEvent.click(screen.getByRole("checkbox", { name: "All relationships" }));
    expect(scene).toHaveAttribute("data-all-relationships", "true");
    expect([...document.querySelectorAll("[data-edge-id] path")]).toEqual(paths);
    fireEvent.click(screen.getByRole("button", { name: "Recorded object 0, person" }));
    expect(scene).toHaveAttribute("data-has-selection", "true");
    const selected = [...document.querySelectorAll(".world-graph-canvas__edge.is-selected")].map((edge) => edge.getAttribute("data-edge-id"));
    expect(selected.sort()).toEqual(relationships.filter((edge) => edge.fromObjectId === objects[0].id || edge.toObjectId === objects[0].id).map((edge) => edge.id).sort());
    expect(document.querySelectorAll("[data-edge-id]")).toHaveLength(559);
    const small = screen.getByRole("button", { name: "Recorded object 512, person" });
    expect(small.querySelector(".world-graph-canvas__overview-label")).toBeNull();
    fireEvent.click(small);
    const smallCaption = small.querySelector<SVGTextElement>(".world-graph-canvas__overview-label")!;
    expect(smallCaption).not.toBeNull();
    expect(small).toHaveAttribute("data-important", "true");
    expect(parseFloat(smallCaption.style.fontSize) * cameraFromScene(scene).zoom).toBeCloseTo(12);
    expect(document.querySelectorAll(".world-graph-canvas__overview-label").length).toBeLessThanOrEqual(10);
    expect([...document.querySelectorAll("[data-edge-id] path")]).toEqual(paths);
    const css = readFileSync(fileURLToPath(import.meta.url).replace(/WorldGraphCanvas\.test\.tsx$/, "worldGraphCanvas.css"), "utf8");
    expect(css).toContain('.world-graph-canvas--full .world-graph-canvas__edge { opacity: .12; }');
    expect(css).toContain('[data-has-selection="true"] .world-graph-canvas__edge:not(.is-selected) { opacity: .04; }');
    expect(css).toContain('.world-graph-canvas__scene .world-graph-canvas__edge.is-selected { opacity: 1; }');
  });

  it("settles only on geometry changes, preserving pins while allowing unpinned adaptation", async () => {
    const { record } = await graphRecord();
    const solve = vi.spyOn(projectionModule, "createGraphFallbackPositions");
    const props = { nodeShape: "circle" as const, projectionOptions: { fullCorpus: true } };
    const view = render(<WorldGraphCanvas {...props} record={record} />);
    const count = solve.mock.calls.length;
    const before = new Map([...document.querySelectorAll("[data-node-id]")].map((node) => [node.getAttribute("data-node-id"), node.getAttribute("transform")]));
    const revised = { ...record, localRevision: record.localRevision + 1,
      snapshot: { ...record.snapshot, objects: [...record.snapshot.objects].reverse().map((object) => ({ ...object, name: `${object.name} renamed` })), relationships: [...record.snapshot.relationships].reverse() },
      layout: { ...record.layout, positions: { ...record.layout.positions } } };
    view.rerender(<WorldGraphCanvas {...props} record={revised} />);
    expect(solve).toHaveBeenCalledTimes(count);
    for (const [id, position] of before) expect(document.querySelector(`[data-node-id="${id}"]`)).toHaveAttribute("transform", position!);
    fireEvent.click(screen.getByRole("checkbox", { name: "All relationships" }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Show objects without listed relationships/ }));
    fireEvent.click(screen.getByRole("button", { name: "Zoom in" }));
    expect(solve).toHaveBeenCalledTimes(count);
    const pinnedId = record.snapshot.objects[0].id;
    const pinned = { ...revised, layoutRevision: revised.layoutRevision + 1,
      layout: { ...revised.layout, positions: { [pinnedId]: { x: 1500, y: 1700 } } } };
    view.rerender(<WorldGraphCanvas {...props} record={pinned} />);
    expect(solve).toHaveBeenCalledTimes(count + 1);
    expect(document.querySelector(`[data-node-id="${pinnedId}"]`)).toHaveAttribute("transform", "translate(1500 1700)");
    expect(record.snapshot.objects.some((object) => object.id !== pinnedId && document.querySelector(`[data-node-id="${object.id}"]`)!.getAttribute("transform") !== before.get(object.id))).toBe(true);
    view.rerender(<WorldGraphCanvas {...props} record={{ ...revised, layoutRevision: pinned.layoutRevision + 1 }} />);
    expect(solve).toHaveBeenCalledTimes(count + 2);
    for (const [id, position] of before) expect(document.querySelector(`[data-node-id="${id}"]`)).toHaveAttribute("transform", position!);
    view.unmount();
    solve.mockRestore();
  });
});

it.each([4, 0])("keeps unequal-radius packed connector tangents directed into targets with gap %s", async (gap) => {
  const { record } = await graphRecord();
  const objects = record.snapshot.objects.slice(0, 2);
  // Degree1 vs degree31 yields radius24 vs ~134; test both directions separately.
  for (const reverse of [false, true]) {
    const [small, large] = objects;
    const direct = { ...record.snapshot.relationships[0], fromObjectId: reverse ? large.id : small.id, toObjectId: reverse ? small.id : large.id };
    const loops = Array.from({ length: 30 }, (_, i) => ({ ...direct, id: `packed-loop-${i}` as LocalWorldRelationship["id"], fromObjectId: large.id, toObjectId: large.id }));
    const rSmall = projectionModule.graphBubbleRadius(1), rLarge = projectionModule.graphBubbleRadius(31);
    const distance = rSmall + rLarge + gap;
    const packed = { ...record, snapshot: { ...record.snapshot, objects, relationships: [direct, ...loops] },
      layout: { ...record.layout, positions: { [small.id]: { x: 0, y: 0 }, [large.id]: { x: distance, y: 0 } } } };
    const view = render(<WorldGraphCanvas record={packed} nodeShape="circle" projectionOptions={{ fullCorpus: true }} />);
    const path = document.querySelector(`[data-edge-id="${direct.id}"] path`)!.getAttribute("d")!;
    const [sx, sy, cx, cy, ex, ey] = path.match(/-?\d+(?:\.\d+)?/g)!.map(Number);
    const fromCenter = { x: 56 + (reverse ? distance : 0), y: 56 };
    const toCenter = { x: 56 + (reverse ? 0 : distance), y: 56 };
    const fromRadius = reverse ? rLarge : rSmall, toRadius = reverse ? rSmall : rLarge;
    const padding = gap / 4;
    expect(Math.hypot(sx - fromCenter.x, sy - fromCenter.y)).toBeCloseTo(fromRadius + padding);
    expect(Math.hypot(ex - toCenter.x, ey - toCenter.y)).toBeCloseTo(toRadius + padding);
    expect((ex - cx) * (toCenter.x - ex) + (ey - cy) * (toCenter.y - ey)).toBeGreaterThan(0);
    expect((cx - sx) * (sx - fromCenter.x) + (cy - sy) * (sy - fromCenter.y)).toBeGreaterThan(0);
    expect(Math.hypot(ex - sx, ey - sy)).toBeGreaterThan(0);
    view.unmount();
  }
});
