import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Blob as NodeBlob } from "node:buffer";
import { readFileSync } from "node:fs";
import { URL as NodeURL } from "node:url";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NativeGraphDemo, type NativeGraphDemoProps } from "./NativeGraphDemo";
import { NativeGraphDemoApiError, type NativeGraph, type NativeGraphDemoApi, type OperationLookupResult, type PrepareResult } from "./nativeGraphDemoApi";
import { SurfaceContextHost, SurfaceContextProvider } from "../surfaceInteraction/contextHost";

const graph: NativeGraph = {
  world_id: "space:native-demo",
  revision_id: "revision-001",
  graph_sha256: "sha256:graph-001",
  nodes: [
    { id: "entity:mara", name: "Mara", kind: "npc" },
    { id: "entity:tomas", name: "Tomas", kind: "npc" },
    { id: "entity:inn", name: "Lantern Inn", kind: "location" },
  ],
  edges: [{ id: "assertion:stays", source_id: "entity:mara", target_id: "entity:inn", predicate: "stays_at" }],
  storage: "postgres",
  limitations: ["Event typing is not available in this native profile."],
  capabilities: { create: true, connect: true, rename: false, delete: false, object_kinds: ["person", "location"] },
};

const createdGraph: NativeGraph = {
  ...graph,
  revision_id: "revision-002",
  graph_sha256: "sha256:graph-002",
  nodes: [...graph.nodes, { id: "entity:mira", name: "Mira", kind: "person" }],
};

const initialCreateObjectURL = Object.getOwnPropertyDescriptor(URL, "createObjectURL");
const initialRevokeObjectURL = Object.getOwnPropertyDescriptor(URL, "revokeObjectURL");

function restoreUrlObjectUrlMethods(): void {
  if (initialCreateObjectURL) Object.defineProperty(URL, "createObjectURL", initialCreateObjectURL);
  else Reflect.deleteProperty(URL, "createObjectURL");
  if (initialRevokeObjectURL) Object.defineProperty(URL, "revokeObjectURL", initialRevokeObjectURL);
  else Reflect.deleteProperty(URL, "revokeObjectURL");
}

function makeApi(overrides: Partial<NativeGraphDemoApi> = {}): NativeGraphDemoApi {
  return {
    readGraph: vi.fn().mockResolvedValue(graph),
    prepare: vi.fn().mockResolvedValue({
      status: "prepared",
      operation_id: "bb9c10ac-c94a-4693-b7bc-4d001c398770",
      parent_revision_id: graph.revision_id,
      review: { summary: "Create Mira as a native person in the current World." },
    }),
    confirm: vi.fn().mockResolvedValue({ status: "committed", created_node_id: "entity:mira", graph: createdGraph }),
    readOperation: vi.fn().mockResolvedValue({ status: "unknown", operation_id: "bb9c10ac-c94a-4693-b7bc-4d001c398770" }),
    ...overrides,
  };
}

function renderEmbeddedDemo(props: Omit<NativeGraphDemoProps, "embedded"> = {}) {
  return render(<SurfaceContextProvider>
    <header className="app-chrome-header"><SurfaceContextHost /></header>
    <NativeGraphDemo {...props} embedded />
  </SurfaceContextProvider>);
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((accept, fail) => { resolve = accept; reject = fail; });
  return { promise, resolve, reject };
}

describe("NativeGraphDemo", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    document.head.innerHTML = '<meta name="native-demo-capability" content="demo-test">';
  });

  afterEach(() => {
    cleanup();
    restoreUrlObjectUrlMethods();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("lets the embedded bounded index graph use the available page width", () => {
    const css = readFileSync(new NodeURL("./nativeGraphDemo.css", import.meta.url), "utf8");
    expect(css).toMatch(/\.app-wrap\[data-workspace-layout="bounded"\]:has\(\.native-demo-shell--embedded\)\s*\{\s*max-width:\s*none;\s*\}/);
    const embeddedLayout = css.match(/\.native-demo-shell--embedded > \.native-demo-layout--embedded\s*\{([^}]+)\}/)?.[1] ?? "";
    expect(embeddedLayout).toMatch(/width:\s*100%;/);
    expect(embeddedLayout).not.toMatch(/max-width|1600px/);
    expect(css).toMatch(/\.native-demo-layout\s*\{\s*width:\s*min\(1500px,\s*100%\);/);
  });

  it("uses the server graph and makes create a prepare-review-confirm sequence", async () => {
    const user = userEvent.setup();
    const api = makeApi();
    const uuid = vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue("bb9c10ac-c94a-4693-b7bc-4d001c398770");
    render(<NativeGraphDemo api={api} />);

    expect(await screen.findByRole("heading", { name: "The living graph" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "DungeonMind native graph" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Mara, npc/i })).toHaveAttribute("data-node-id", "entity:mara");
    expect(screen.getByText(/Event typing is not supported by this DungeonMind profile yet/)).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Event · unavailable/ })).toBeDisabled();
    expect(screen.getByText(/Rename is unavailable/)).toBeInTheDocument();
    expect(screen.getByText(/Delete is unavailable/)).toBeInTheDocument();

    await user.type(screen.getByLabelText("Name"), "Mira");
    await user.click(screen.getByRole("button", { name: "Prepare object" }));

    await screen.findByText("Create Mira as a native person in the current World.");
    expect(api.prepare).toHaveBeenCalledWith({
      operation_id: "bb9c10ac-c94a-4693-b7bc-4d001c398770",
      expected_revision_id: "revision-001",
      kind: "create_object",
      name: "Mira",
      object_kind: "person",
    });
    expect(api.confirm).not.toHaveBeenCalled();
    expect(screen.getByDisplayValue("Mira")).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Confirm in DungeonMind" }));

    expect(await screen.findByText(/is committed\. The graph below is the server readback/)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /Mira, person/i })).toHaveAttribute("data-node-id", "entity:mira");
    expect(api.confirm).toHaveBeenCalledWith("bb9c10ac-c94a-4693-b7bc-4d001c398770");
    expect(uuid).toHaveBeenCalledOnce();
  });

  it("puts the embedded explorer in Surface context and keeps only one compact panel open", async () => {
    const user = userEvent.setup();
    const api = makeApi();
    renderEmbeddedDemo({ api });

    expect(await screen.findByRole("button", { name: /Mara, npc/i })).toBeInTheDocument();
    const navbar = within(screen.getByTestId("surface-context-host"));
    expect(navbar.getByText("Buddy playground · private graph")).toBeInTheDocument();
    expect(navbar.getByText("Saved to DungeonMind")).toBeInTheDocument();
    expect(navbar.getByRole("button", { name: "Add object" })).toBeEnabled();
    expect(navbar.getByRole("button", { name: "Connect" })).toBeEnabled();
    expect(navbar.getByRole("button", { name: "Refresh" })).toBeEnabled();
    expect(navbar.getByRole("button", { name: "Info" })).toBeEnabled();
    expect(navbar.getByRole("button", { name: "Export snapshot" })).toBeEnabled();
    expect(screen.queryByRole("heading", { name: "The graph so far" })).not.toBeInTheDocument();
    expect(screen.getByTestId("graph-scene").querySelector(".world-graph-canvas__node circle")).not.toBeNull();
    expect(document.querySelector(".native-demo-shell--embedded .world-graph-canvas__viewport")).toBeInTheDocument();

    await user.click(navbar.getByRole("button", { name: "Add object" }));
    await user.type(screen.getByLabelText("Name"), "Aster");
    await user.click(navbar.getByRole("button", { name: "Connect" }));
    expect(screen.queryByLabelText("Name")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Relationship")).toBeInTheDocument();
    await user.click(navbar.getByRole("button", { name: "Add object" }));
    expect(screen.getByLabelText("Name")).toHaveValue("Aster");
    expect(screen.queryByLabelText("Relationship")).not.toBeInTheDocument();

    await user.click(navbar.getByRole("button", { name: "Info" }));
    expect(screen.queryByLabelText("Name")).not.toBeInTheDocument();
    expect(screen.getByText(/This private synthetic graph is backed by DungeonMind/)).toBeInTheDocument();
    expect(screen.getByText("Rename is unavailable")).toBeInTheDocument();
    expect(screen.getByText("Delete is unavailable")).toBeInTheDocument();
    expect(screen.getByText(/Clearing cookies or session expiry loses the link to this graph/)).toBeInTheDocument();
  });

  it("shows a partial native read separately from canvas projection limits", async () => {
    const partialGraph = {
      ...graph,
      completeness: {
        status: "partial" as const,
        listed_entities: 3,
        omitted_entities: 2,
        unexamined_entities: 0,
        listed_assertions: 1,
        omitted_assertions: 1,
        unexamined_assertions: 0,
        reasons: ["entity_name_missing", "non_graph_assertions"],
      },
    } as NativeGraph;
    const api = makeApi({ readGraph: vi.fn().mockResolvedValue(partialGraph) });
    const user = userEvent.setup();
    renderEmbeddedDemo({ api, mode: "managed", worldTitle: "Elderwyld", stateScopeId: "managed:world-17" });

    expect(await screen.findByRole("button", { name: /Mara, npc/i })).toBeInTheDocument();
    expect(within(screen.getByTestId("surface-context-host")).getByText("Partial native read")).toBeInTheDocument();
    expect(screen.getByText(/2 entities omitted, 0 unexamined; 1 assertions omitted, 0 unexamined/)).toBeInTheDocument();
    await user.click(within(screen.getByTestId("surface-context-host")).getByRole("button", { name: "Info" }));
    expect(screen.getAllByText("Some entities have no usable name").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Some assertions could not be represented as graph edges").length).toBeGreaterThan(0);
  });

  it("keeps authoring controls disabled when the selected graph is read-only", async () => {
    const user = userEvent.setup();
    const readOnlyGraph = {
      ...graph,
      capabilities: { ...graph.capabilities, create: false, connect: false, object_kinds: [] },
    };
    const api = makeApi({ readGraph: vi.fn().mockResolvedValue(readOnlyGraph) });
    renderEmbeddedDemo({ api, mode: "managed", worldTitle: "Elderwyld", stateScopeId: "managed:world-17" });

    expect(await screen.findByRole("button", { name: /Mara, npc/i })).toBeInTheDocument();
    const navbar = within(screen.getByTestId("surface-context-host"));
    expect(navbar.getByRole("button", { name: "Add object" })).toBeDisabled();
    expect(navbar.getByRole("button", { name: "Connect" })).toBeDisabled();
    await user.click(navbar.getByRole("button", { name: "Info" }));
    expect(screen.getByText("Object creation is read-only here")).toBeInTheDocument();
    expect(screen.getByText("Connections are read-only here")).toBeInTheDocument();
  });

  it("fails closed instead of showing the playground graph when managed mode has no verified API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    renderEmbeddedDemo({ mode: "managed", worldTitle: "Elderwyld", stateScopeId: "managed:world-17" });

    expect(await screen.findByRole("alert")).toHaveTextContent("This managed World graph needs its verified API binding.");
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: /Mara, npc/i })).not.toBeInTheDocument();
  });

  it("limits managed connections to descriptor-approved predicate labels", async () => {
    const user = userEvent.setup();
    const managedGraph: NativeGraph = {
      ...graph,
      capabilities: {
        ...graph.capabilities,
        allowed_predicates: ["located_in", "allied_with"],
        allows_custom_predicates: false,
      },
    };
    const api = makeApi({ readGraph: vi.fn().mockResolvedValue(managedGraph) });
    renderEmbeddedDemo({ api, mode: "managed", worldTitle: "Elderwyld", stateScopeId: "managed:world-17" });
    await screen.findByRole("button", { name: /Mara, npc/i });
    await user.click(within(screen.getByTestId("surface-context-host")).getByRole("button", { name: "Connect" }));

    const relationship = screen.getByLabelText("Relationship");
    expect(relationship.tagName).toBe("SELECT");
    expect(within(relationship).getByRole("option", { name: "located_in" })).toBeInTheDocument();
    expect(within(relationship).getByRole("option", { name: "allied_with" })).toBeInTheDocument();
    fireEvent.change(relationship, { target: { value: "custom:unsupported" } });
    fireEvent.submit(relationship.closest("form")!);
    expect(api.prepare).not.toHaveBeenCalled();

    await user.selectOptions(relationship, "allied_with");
    await user.selectOptions(screen.getByLabelText("From"), "entity:mara");
    await user.selectOptions(screen.getByLabelText("To"), "entity:tomas");
    fireEvent.submit(relationship.closest("form")!);
    await waitFor(() => expect(api.prepare).toHaveBeenCalledWith(expect.objectContaining({ predicate: "allied_with" })));
  });

  it("offers registered labels and accepts only valid plain custom labels when the descriptor allows them", async () => {
    const user = userEvent.setup();
    const managedGraph: NativeGraph = {
      ...graph,
      capabilities: { ...graph.capabilities, allowed_predicates: ["located_in", "allied_with"], allows_custom_predicates: true },
    };
    const api = makeApi({ readGraph: vi.fn().mockResolvedValue(managedGraph) });
    renderEmbeddedDemo({ api, mode: "managed", worldTitle: "Elderwyld", stateScopeId: "managed:world-17" });
    await screen.findByRole("button", { name: /Mara, npc/i });
    await user.click(within(screen.getByTestId("surface-context-host")).getByRole("button", { name: "Connect" }));

    const relationship = screen.getByLabelText("Relationship");
    expect(relationship.tagName).toBe("SELECT");
    expect(within(relationship).getByRole("option", { name: "located_in" })).toBeInTheDocument();
    expect(within(relationship).getByRole("option", { name: "allied_with" })).toBeInTheDocument();
    await user.selectOptions(relationship, "__custom_predicate__");
    const customLabel = screen.getByLabelText("Custom label");
    expect(customLabel).toHaveAttribute("pattern", "[a-z0-9]+([._-][a-z0-9]+)*");
    await user.selectOptions(screen.getByLabelText("From"), "entity:mara");
    await user.selectOptions(screen.getByLabelText("To"), "entity:tomas");
    fireEvent.change(customLabel, { target: { value: "story:knows" } });
    fireEvent.submit(customLabel.closest("form")!);
    expect(api.prepare).not.toHaveBeenCalled();

    await user.clear(customLabel);
    await user.type(customLabel, "works__at");
    fireEvent.submit(customLabel.closest("form")!);
    expect(api.prepare).not.toHaveBeenCalled();

    await user.clear(customLabel);
    await user.type(customLabel, "works_at");
    fireEvent.submit(customLabel.closest("form")!);
    await waitFor(() => expect(api.prepare).toHaveBeenCalledWith(expect.objectContaining({ predicate: "works_at" })));
  });

  it("keeps pending drafts isolated by the managed World scope", async () => {
    const user = userEvent.setup();
    const guestKey = `dungeonmind-native-demo:draft:${encodeURIComponent(graph.world_id)}`;
    const managedKey = `dungeonmind-native-demo:draft:${encodeURIComponent("managed:world-17")}:${encodeURIComponent(graph.world_id)}`;
    const pending = {
      operation_id: "c965d040-2d72-49eb-b417-31ccba7c7510",
      expected_revision_id: graph.revision_id,
      kind: "create_object",
      name: "Guest-only draft",
      object_kind: "person",
    };
    const envelope = (name: string, operation: typeof pending | null) => ({
      version: 1,
      world_id: graph.world_id,
      draft: { objectName: name, objectKind: "person", sourceId: "", targetId: "", predicate: "" },
      pending: operation,
      pending_phase: "prepare",
    });
    sessionStorage.setItem(guestKey, JSON.stringify(envelope("Guest-only draft", pending)));
    sessionStorage.setItem(managedKey, JSON.stringify(envelope("Managed draft", null)));
    const api = makeApi();
    renderEmbeddedDemo({ api, mode: "managed", worldTitle: "Elderwyld", stateScopeId: "managed:world-17" });

    expect(await screen.findByRole("button", { name: /Mara, npc/i })).toBeInTheDocument();
    await user.click(within(screen.getByTestId("surface-context-host")).getByRole("button", { name: "Add object" }));
    expect(screen.getByLabelText("Name")).toHaveValue("Managed draft");
    expect(api.readOperation).not.toHaveBeenCalled();
    expect(sessionStorage.getItem(guestKey)).toContain("Guest-only draft");
  });

  it("recovers the new managed scope with the same API without writing the prior scope", async () => {
    const operationA = "c965d040-2d72-49eb-b417-31ccba7c7510";
    const operationB = "4a4a77ef-4182-4050-86cf-e9c7e06935f8";
    const keyFor = (scope: string) => `dungeonmind-native-demo:draft:${encodeURIComponent(scope)}:${encodeURIComponent(graph.world_id)}`;
    const layoutKeyFor = (scope: string) => `dungeonmind-native-demo:layout:${encodeURIComponent(scope)}:${encodeURIComponent(graph.world_id)}`;
    const makeEnvelope = (name: string, operationId: string, position: { x: number; y: number }) => ({
      version: 1,
      world_id: graph.world_id,
      draft: { objectName: name, objectKind: "person", sourceId: "", targetId: "", predicate: "" },
      pending: { operation_id: operationId, expected_revision_id: graph.revision_id, kind: "create_object", name, object_kind: "person" },
      pending_phase: "confirm",
      placement: { kind: "person", position, operation_id: operationId, base_revision_id: graph.revision_id, created_node_id: null },
    });
    sessionStorage.setItem(keyFor("managed:world-a"), JSON.stringify(makeEnvelope("Draft A", operationA, { x: 100, y: 120 })));
    sessionStorage.setItem(keyFor("managed:world-b"), JSON.stringify(makeEnvelope("Draft B", operationB, { x: 340, y: 420 })));
    const oldLookup = deferred<OperationLookupResult>();
    const api = makeApi({
      readOperation: vi.fn((operationId: string) => operationId === operationA
        ? oldLookup.promise
        : Promise.resolve({ status: "committed", operation_id: operationId, graph: createdGraph, created_node_id: "entity:mira" })),
    });
    const view = render(<NativeGraphDemo api={api} mode="managed" worldTitle="World A" stateScopeId="managed:world-a" />);
    await waitFor(() => expect(api.readOperation).toHaveBeenCalledWith(operationA));

    view.rerender(<NativeGraphDemo api={api} mode="managed" worldTitle="World B" stateScopeId="managed:world-b" />);
    await waitFor(() => expect(api.readOperation).toHaveBeenCalledWith(operationB));
    await waitFor(() => {
      expect(JSON.parse(sessionStorage.getItem(keyFor("managed:world-b")) ?? "null").pending).toBeNull();
      expect(JSON.parse(sessionStorage.getItem(keyFor("managed:world-a")) ?? "null").pending.operation_id).toBe(operationA);
      expect(JSON.parse(localStorage.getItem(layoutKeyFor("managed:world-b")) ?? "null")["entity:mira"]).toEqual({ x: 340, y: 420 });
      expect(localStorage.getItem(layoutKeyFor("managed:world-a"))).toBeNull();
    });

    oldLookup.resolve({ status: "prepared", operation_id: operationA, review: { summary: "Old scope review" } });
    await waitFor(() => expect(JSON.parse(sessionStorage.getItem(keyFor("managed:world-a")) ?? "null").pending.operation_id).toBe(operationA));
  });

  it("retains a canvas placement with its exact operation and applies it only after server readback", async () => {
    const user = userEvent.setup();
    const api = makeApi();
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue("bb9c10ac-c94a-4693-b7bc-4d001c398770");
    renderEmbeddedDemo({ api });

    await screen.findByRole("button", { name: /Mara, npc/i });
    await user.click(screen.getByRole("button", { name: "Place node" }));
    const palette = screen.getByTestId("node-palette");
    expect(palette).toBeVisible();
    await user.click(within(palette).getByRole("button", { name: "Person" }));
    await user.type(screen.getByLabelText("Name"), "Mira");

    const draftKey = `dungeonmind-native-demo:draft:${encodeURIComponent(graph.world_id)}`;
    const beforePrepare = JSON.parse(sessionStorage.getItem(draftKey) ?? "null");
    expect(beforePrepare.placement).toMatchObject({ kind: "person", operation_id: null, base_revision_id: graph.revision_id });
    const placement = beforePrepare.placement.position;
    expect(api.prepare).not.toHaveBeenCalled();
    expect(localStorage.getItem(`dungeonmind-native-demo:layout:${encodeURIComponent(graph.world_id)}`)).toBeNull();

    await user.click(screen.getByRole("button", { name: "Prepare object" }));
    expect(await screen.findByText("Create Mira as a native person in the current World.")).toBeInTheDocument();
    const prepared = JSON.parse(sessionStorage.getItem(draftKey) ?? "null");
    expect(prepared.pending.operation_id).toBe("bb9c10ac-c94a-4693-b7bc-4d001c398770");
    expect(prepared.placement).toMatchObject({ operation_id: prepared.pending.operation_id, base_revision_id: graph.revision_id, created_node_id: null });
    expect(localStorage.getItem(`dungeonmind-native-demo:layout:${encodeURIComponent(graph.world_id)}`)).toBeNull();

    await user.click(screen.getByRole("button", { name: "Confirm in DungeonMind" }));
    expect(await screen.findByRole("button", { name: "Mira, person" })).toBeInTheDocument();
    await waitFor(() => {
      const saved = JSON.parse(localStorage.getItem(`dungeonmind-native-demo:layout:${encodeURIComponent(graph.world_id)}`) ?? "null");
      expect(saved?.["entity:mira"]).toEqual(placement);
    });
    expect(JSON.parse(sessionStorage.getItem(draftKey) ?? "null").placement).toBeNull();
  });

  it("turns connector-dot drags into a relationship draft without preparing automatically", async () => {
    const api = makeApi();
    renderEmbeddedDemo({ api });
    await screen.findByRole("button", { name: /Mara, npc/i });

    const svg = screen.getByRole("group", { name: "DungeonMind native graph world graph" });
    vi.spyOn(svg, "getBoundingClientRect").mockReturnValue({ width: 960, height: 520, x: 0, y: 0, top: 0, right: 960, bottom: 520, left: 0, toJSON: () => ({}) });
    const scene = screen.getByTestId("graph-scene");
    const transform = scene.getAttribute("transform")?.match(/translate\(([-.\d]+) ([-.\d]+)\) scale\(([-.\d]+)\)/);
    expect(transform).not.toBeNull();
    const camera = { x: Number(transform?.[1]), y: Number(transform?.[2]), zoom: Number(transform?.[3]) };
    const sourceTransform = svg.querySelector('[data-node-id="entity:mara"]')?.getAttribute("transform")?.match(/translate\(([-.\d]+) ([-.\d]+)\)/);
    const targetTransform = svg.querySelector('[data-node-id="entity:tomas"]')?.getAttribute("transform")?.match(/translate\(([-.\d]+) ([-.\d]+)\)/);
    expect(sourceTransform).not.toBeNull();
    expect(targetTransform).not.toBeNull();
    const start = { x: camera.x + (Number(sourceTransform?.[1]) + 110) * camera.zoom, y: camera.y + (Number(sourceTransform?.[2]) + 56) * camera.zoom };
    const end = { x: camera.x + (Number(targetTransform?.[1]) + 56) * camera.zoom, y: camera.y + (Number(targetTransform?.[2]) + 56) * camera.zoom };
    const port = screen.getByTestId("connect-port-entity:mara");
    const pointer = (target: Element, type: "pointerdown" | "pointermove" | "pointerup", pointerId: number, point: { readonly x: number; readonly y: number }) => {
      const event = new MouseEvent(type, { bubbles: true, cancelable: true, button: 0, clientX: point.x, clientY: point.y });
      Object.defineProperty(event, "pointerId", { configurable: true, value: pointerId });
      fireEvent(target, event);
    };
    pointer(port, "pointerdown", 71, start);
    pointer(svg, "pointermove", 71, end);
    expect(screen.getByTestId("connect-preview")).toBeVisible();
    pointer(svg, "pointerup", 71, end);

    expect(await screen.findByLabelText("Relationship")).toBeInTheDocument();
    expect(screen.getByLabelText("From")).toHaveValue("entity:mara");
    expect(screen.getByLabelText("To")).toHaveValue("entity:tomas");
    expect(api.prepare).not.toHaveBeenCalled();
  });

  it("exports a pinned read-only snapshot with browser layout, not a restorable World backup", async () => {
    const user = userEvent.setup();
    const worldKey = encodeURIComponent(graph.world_id);
    localStorage.setItem(`dungeonmind-native-demo:layout:${encodeURIComponent("managed:world-17")}:${worldKey}`, JSON.stringify({ "entity:mara": { x: 120, y: 240 } }));
    vi.stubGlobal("Blob", NodeBlob);
    let exported: NodeBlob | null = null;
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn((blob: Blob) => { exported = blob as NodeBlob; return "blob:native-graph-snapshot"; }) });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    const api = makeApi();
    renderEmbeddedDemo({ api, mode: "managed", worldTitle: "Elderwyld", stateScopeId: "managed:world-17" });

    await screen.findByRole("button", { name: /Mara, npc/i });
    const navbar = within(screen.getByTestId("surface-context-host"));
    expect(navbar.getByText("World · Elderwyld")).toBeInTheDocument();
    expect(navbar.queryByText(/private graph/i)).not.toBeInTheDocument();
    await user.click(navbar.getByRole("button", { name: "Export snapshot" }));
    expect(await screen.findByText(/not a restorable World backup/)).toBeInTheDocument();
    expect(exported).not.toBeNull();
    const payload = JSON.parse(await exported!.text());
    expect(payload).toMatchObject({
      format: "dungeonmind-index-graph-snapshot-v1",
      kind: "read-only-revision-pinned-snapshot",
      world_id: graph.world_id,
      revision_id: graph.revision_id,
      presentation: { positions: { "entity:mara": { x: 120, y: 240 } } },
    });
    expect(payload.note).toMatch(/not a restorable World backup/);
    expect(api.prepare).not.toHaveBeenCalled();
  });

  it("keeps the exact operation ID and form draft after an uncertain prepare response", async () => {
    const user = userEvent.setup();
    const uncertain = Object.assign(new Error("connection dropped"), { code: "network_error", status: 0 });
    const api = makeApi({
      prepare: vi.fn()
        .mockRejectedValueOnce(uncertain)
        .mockResolvedValueOnce({
          status: "prepared",
          operation_id: "4a4a77ef-4182-4050-86cf-e9c7e06935f8",
          parent_revision_id: graph.revision_id,
          review: { summary: "Create Mira as a native person in the current World." },
        }),
      readOperation: vi.fn().mockResolvedValue({ status: "not_found", operation_id: "4a4a77ef-4182-4050-86cf-e9c7e06935f8" }),
    });
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue("4a4a77ef-4182-4050-86cf-e9c7e06935f8");
    render(<NativeGraphDemo api={api} />);

    await screen.findByRole("heading", { name: "The living graph" });
    await user.type(screen.getByLabelText("Name"), "Mira");
    await user.click(screen.getByRole("button", { name: "Prepare object" }));

    expect(await screen.findByText(/operation ID are preserved/)).toBeInTheDocument();
    expect(api.readOperation).toHaveBeenCalledWith("4a4a77ef-4182-4050-86cf-e9c7e06935f8");
    expect(screen.getByDisplayValue("Mira")).toBeDisabled();
    const stored = JSON.parse(sessionStorage.getItem("dungeonmind-native-demo:draft:space%3Anative-demo") ?? "null");
    expect(stored.pending.operation_id).toBe("4a4a77ef-4182-4050-86cf-e9c7e06935f8");

    await user.click(screen.getByRole("button", { name: "Retry same operation ID" }));

    await screen.findByText("Create Mira as a native person in the current World.");
    expect(api.prepare).toHaveBeenCalledTimes(2);
    expect(api.prepare.mock.calls[0]?.[0]).toEqual(api.prepare.mock.calls[1]?.[0]);
  });

  it("keeps recovery controls unavailable while prepare is pending and reuses its ID after not_found", async () => {
    const user = userEvent.setup();
    const preparing = deferred<PrepareResult>();
    const operationId = "4a4a77ef-4182-4050-86cf-e9c7e06935f8";
    const api = makeApi({
      prepare: vi.fn().mockReturnValueOnce(preparing.promise).mockResolvedValueOnce({
        status: "prepared",
        operation_id: operationId,
        parent_revision_id: graph.revision_id,
        review: { summary: "Create Mira as a native person in the current World." },
      }),
      readOperation: vi.fn().mockResolvedValue({ status: "not_found", operation_id: operationId }),
    });
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue(operationId);
    render(<NativeGraphDemo api={api} />);

    await screen.findByRole("heading", { name: "The living graph" });
    await user.type(screen.getByLabelText("Name"), "Mira");
    await user.click(screen.getByRole("button", { name: "Prepare object" }));
    expect(await screen.findByText(/Status checks stay unavailable until the response settles/)).toBeInTheDocument();
    expect(api.prepare).toHaveBeenCalledTimes(1);
    expect(api.readOperation).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Check status" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry same operation ID" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Refresh and start a fresh review" })).not.toBeInTheDocument();

    await act(async () => { preparing.reject(new Error("connection dropped")); });
    expect(await screen.findByText(/missing record alone does not prove the request cannot still arrive/)).toBeInTheDocument();
    expect(api.readOperation).toHaveBeenCalledWith(operationId);
    expect(screen.queryByRole("button", { name: "Refresh and start a fresh review" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry same operation ID" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry same operation ID" }));
    expect(await screen.findByText("Create Mira as a native person in the current World.")).toBeInTheDocument();
    expect(api.prepare).toHaveBeenCalledTimes(2);
    expect(api.prepare.mock.calls[0]?.[0]).toEqual(api.prepare.mock.calls[1]?.[0]);
  });

  it("allows a fresh review only after prepare is definitively rejected stale and its exact ID is not found", async () => {
    const user = userEvent.setup();
    const firstId = "4a4a77ef-4182-4050-86cf-e9c7e06935f8";
    const secondId = "b121ad7a-c50a-4a58-9e62-91eea9e3972d";
    const latestGraph = { ...graph, revision_id: "revision-latest", graph_sha256: "sha256-latest" };
    const api = makeApi({
      readGraph: vi.fn().mockResolvedValueOnce(graph).mockResolvedValueOnce(latestGraph),
      prepare: vi.fn()
        .mockRejectedValueOnce(new NativeGraphDemoApiError("stale", "stale_revision", 409))
        .mockResolvedValueOnce({ status: "prepared", operation_id: secondId, parent_revision_id: latestGraph.revision_id, review: { summary: "Fresh review." } }),
      readOperation: vi.fn().mockResolvedValue({ status: "not_found", operation_id: firstId }),
    });
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValueOnce(firstId).mockReturnValueOnce(secondId);
    render(<NativeGraphDemo api={api} />);

    await screen.findByRole("heading", { name: "The living graph" });
    await user.type(screen.getByLabelText("Name"), "Mira");
    await user.click(screen.getByRole("button", { name: "Prepare object" }));
    expect(await screen.findByText(/rejected this prepare as stale_revision, and the exact operation ID has no record/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Refresh and start a fresh review" }));
    expect(await screen.findByText(/definitive safe outcome and the latest DungeonMind graph is loaded/)).toBeInTheDocument();
    expect(api.prepare).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "Prepare object" }));
    expect(await screen.findByText("Fresh review.")).toBeInTheDocument();
    expect(api.prepare).toHaveBeenCalledTimes(2);
    expect(api.prepare.mock.calls[0]?.[0].operation_id).toBe(firstId);
    expect(api.prepare.mock.calls[1]?.[0].operation_id).toBe(secondId);
  });

  it("blocks names over DungeonMind's UTF-8 byte limit before allocating an operation", async () => {
    const api = makeApi();
    const uuid = vi.spyOn(globalThis.crypto, "randomUUID");
    render(<NativeGraphDemo api={api} />);

    await screen.findByRole("heading", { name: "The living graph" });
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "é".repeat(80) } });
    expect(screen.getByRole("alert")).toHaveTextContent("Names must use 128 UTF-8 bytes or fewer");
    expect(screen.getByRole("button", { name: "Prepare object" })).toBeDisabled();
    expect(uuid).not.toHaveBeenCalled();
    expect(api.prepare).not.toHaveBeenCalled();
  });

  it("preserves a form draft across navigation and constrains directed relationship predicates", async () => {
    const user = userEvent.setup();
    const api = makeApi();
    const view = render(<NativeGraphDemo api={api} />);

    await screen.findByRole("heading", { name: "The living graph" });
    await user.type(screen.getByLabelText("Name"), "Aster");
    view.unmount();
    render(<NativeGraphDemo api={api} />);
    expect(await screen.findByDisplayValue("Aster")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("From"), "entity:mara");
    await user.selectOptions(screen.getByLabelText("To"), "entity:tomas");
    const predicate = screen.getByLabelText("Relationship");
    await user.type(predicate, "Knows people");
    expect(predicate).toHaveAttribute("pattern", "[a-z0-9]+([._-][a-z0-9]+)*");
    expect(screen.getByText(/lowercase letters, numbers, dots, underscores, and hyphens only/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Prepare connection" }));
    expect(api.prepare).not.toHaveBeenCalled();

    fireEvent.change(predicate, { target: { value: "knows_people" } });
    await user.click(screen.getByRole("button", { name: "Prepare connection" }));
    await waitFor(() => expect(api.prepare).toHaveBeenCalledWith(expect.objectContaining({
      kind: "connect",
      expected_revision_id: "revision-001",
      source_id: "entity:mara",
      target_id: "entity:tomas",
      predicate: "knows_people",
    })));
  });

  it("recovers a prepared operation by its saved ID without preparing or confirming automatically", async () => {
    sessionStorage.setItem("dungeonmind-native-demo:draft:space%3Anative-demo", JSON.stringify({
      version: 1,
      world_id: graph.world_id,
      draft: { objectName: "Recovered", objectKind: "person", sourceId: "", targetId: "", predicate: "" },
      pending: {
        operation_id: "c965d040-2d72-49eb-b417-31ccba7c7510",
        expected_revision_id: graph.revision_id,
        kind: "create_object",
        name: "Recovered",
        object_kind: "person",
      },
    }));
    const api = makeApi({
      readOperation: vi.fn().mockResolvedValue({
        status: "prepared",
        operation_id: "c965d040-2d72-49eb-b417-31ccba7c7510",
        parent_revision_id: graph.revision_id,
        review: { summary: "Recovered prepared change." },
      }),
    });
    render(<NativeGraphDemo api={api} />);

    expect(await screen.findByText("Recovered prepared change.")).toBeInTheDocument();
    expect(api.readOperation).toHaveBeenCalledWith("c965d040-2d72-49eb-b417-31ccba7c7510");
    expect(api.prepare).not.toHaveBeenCalled();
    expect(api.confirm).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Confirm in DungeonMind" })).toBeInTheDocument();
  });

  it("refreshes before editing a prepared draft and creates a new review without publishing the old one", async () => {
    const user = userEvent.setup();
    const latestGraph = { ...graph, revision_id: "revision-source-advanced", graph_sha256: "sha256-source-advanced" };
    const firstId = "4a4a77ef-4182-4050-86cf-e9c7e06935f8";
    const secondId = "b121ad7a-c50a-4a58-9e62-91eea9e3972d";
    const api = makeApi({
      readGraph: vi.fn().mockResolvedValueOnce(graph).mockResolvedValueOnce(latestGraph),
      readOperation: vi.fn().mockImplementation(async (operationId: string) => ({ status: "prepared", operation_id: operationId, review: { summary: "Prepared review remains on the server." } })),
      prepare: vi.fn()
        .mockResolvedValueOnce({ status: "prepared", operation_id: firstId, parent_revision_id: graph.revision_id, review: { summary: "First review." } })
        .mockResolvedValueOnce({ status: "prepared", operation_id: secondId, parent_revision_id: latestGraph.revision_id, review: { summary: "Edited review." } }),
    });
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValueOnce(firstId).mockReturnValueOnce(secondId);
    render(<NativeGraphDemo api={api} />);

    await screen.findByRole("heading", { name: "The living graph" });
    await user.type(screen.getByLabelText("Name"), "Mira");
    await user.click(screen.getByRole("button", { name: "Prepare object" }));
    expect(await screen.findByText("First review.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Edit draft (keep review record)" }));

    expect(await screen.findByText(new RegExp(`Retained operation ID: ${firstId}`))).toBeInTheDocument();
    expect(screen.getByDisplayValue("Mira")).toBeEnabled();
    expect(api.confirm).not.toHaveBeenCalled();
    expect(api.readOperation).toHaveBeenCalledTimes(2);
    expect(api.readGraph).toHaveBeenCalledTimes(2);

    await user.type(screen.getByLabelText("Name"), " Gray");
    await user.click(screen.getByRole("button", { name: "Prepare object" }));
    expect(await screen.findByText("Edited review.")).toBeInTheDocument();
    expect(api.prepare).toHaveBeenNthCalledWith(1, expect.objectContaining({ operation_id: firstId, name: "Mira", expected_revision_id: graph.revision_id }));
    expect(api.prepare).toHaveBeenNthCalledWith(2, expect.objectContaining({ operation_id: secondId, name: "Mira Gray", expected_revision_id: latestGraph.revision_id }));
    expect(api.confirm).not.toHaveBeenCalled();
  });

  it("keeps an HTTP 200 unknown confirm outcome locked to status checks", async () => {
    const user = userEvent.setup();
    const api = makeApi({
      confirm: vi.fn().mockResolvedValue({ status: "unknown", message: "Publication receipt is still being reconciled." }),
    });
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue("bb9c10ac-c94a-4693-b7bc-4d001c398770");
    render(<NativeGraphDemo api={api} />);

    await screen.findByRole("heading", { name: "The living graph" });
    await user.type(screen.getByLabelText("Name"), "Mira");
    await user.click(screen.getByRole("button", { name: "Prepare object" }));
    await screen.findByText("Create Mira as a native person in the current World.");
    await user.click(screen.getByRole("button", { name: "Confirm in DungeonMind" }));

    expect(await screen.findByText(/Publication receipt is still being reconciled/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Check status" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry same operation ID" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Refresh and start a fresh review" })).not.toBeInTheDocument();
    const stored = JSON.parse(sessionStorage.getItem("dungeonmind-native-demo:draft:space%3Anative-demo") ?? "null");
    expect(stored.pending_phase).toBe("confirm");
    expect(stored.pending.operation_id).toBe("bb9c10ac-c94a-4693-b7bc-4d001c398770");
  });

  it("does not let a late confirmation from an unmounted instance overwrite a newer tab draft", async () => {
    const user = userEvent.setup();
    const commit = deferred<Awaited<ReturnType<NativeGraphDemoApi["confirm"]>>>();
    const api = makeApi({ confirm: vi.fn(() => commit.promise) });
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue("bb9c10ac-c94a-4693-b7bc-4d001c398770");
    const first = render(<NativeGraphDemo api={api} />);

    await screen.findByRole("heading", { name: "The living graph" });
    await user.type(screen.getByLabelText("Name"), "Mira");
    await user.click(screen.getByRole("button", { name: "Prepare object" }));
    await screen.findByText("Create Mira as a native person in the current World.");
    await user.click(screen.getByRole("button", { name: "Confirm in DungeonMind" }));
    expect(api.confirm).toHaveBeenCalledOnce();
    first.unmount();

    // Model a newer page state that owns the same tab-scoped storage key.
    sessionStorage.setItem("dungeonmind-native-demo:draft:space%3Anative-demo", JSON.stringify({
      version: 1,
      world_id: graph.world_id,
      draft: { objectName: "Aster", objectKind: "person", sourceId: "", targetId: "", predicate: "" },
      pending: null,
    }));
    render(<NativeGraphDemo api={api} />);
    const nameField = await screen.findByDisplayValue("Aster");
    await user.type(nameField, " Vale");
    expect(JSON.parse(sessionStorage.getItem("dungeonmind-native-demo:draft:space%3Anative-demo") ?? "null").draft.objectName).toBe("Aster Vale");

    commit.resolve({ status: "committed", graph: createdGraph });
    await waitFor(() => expect(JSON.parse(sessionStorage.getItem("dungeonmind-native-demo:draft:space%3Anative-demo") ?? "null").draft.objectName).toBe("Aster Vale"));
    expect(screen.getByDisplayValue("Aster Vale")).toBeInTheDocument();
  });

  it("ignores an older graph GET that returns after a newer confirmed graph readback", async () => {
    const user = userEvent.setup();
    const staleGraphRead = deferred<NativeGraph>();
    let graphReads = 0;
    const api = makeApi({
      readGraph: vi.fn(() => {
        graphReads += 1;
        return graphReads === 1 ? Promise.resolve(graph) : staleGraphRead.promise;
      }),
    });
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue("bb9c10ac-c94a-4693-b7bc-4d001c398770");
    render(<NativeGraphDemo api={api} />);
    await screen.findByRole("heading", { name: "The living graph" });

    await user.click(screen.getByRole("button", { name: /Refresh/ }));
    await waitFor(() => expect(api.readGraph).toHaveBeenCalledTimes(2));
    await user.type(screen.getByLabelText("Name"), "Mira");
    await user.click(screen.getByRole("button", { name: "Prepare object" }));
    await screen.findByText("Create Mira as a native person in the current World.");
    await user.click(screen.getByRole("button", { name: "Confirm in DungeonMind" }));

    expect(await screen.findByText("revision-002")).toBeInTheDocument();
    staleGraphRead.resolve(graph);
    await waitFor(() => expect(screen.getByText("revision-002")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /Mira, person/i })).toHaveAttribute("data-node-id", "entity:mira");
  });
});
