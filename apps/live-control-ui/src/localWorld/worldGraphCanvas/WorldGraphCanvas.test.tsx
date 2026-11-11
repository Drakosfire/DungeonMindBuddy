import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { StrictMode } from "react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { InMemoryLocalWorldRepository } from "../inMemoryLocalWorldRepository";
import { createTestWorld, sequenceLocalIds } from "../localWorldContractFixtures";
import type { CommitSemanticResult, LocalWorldRecord, LocalWorldRelationship, WriteLayoutResult } from "../localWorldRepository";
import { createLocalWorldGraphAdapter } from "./localWorldGraphAdapter";
import { projectLocalWorldGraph } from "./graphProjection";
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
