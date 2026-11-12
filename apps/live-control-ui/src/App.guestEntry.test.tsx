// @vitest-environment jsdom
import { App } from "./App";
import { StrictMode } from "react";
import { decodeLocalWorldPackageZipV1 } from "./localWorld/localWorldPackageZipV1";
import { LOCAL_WORLD_NOTES_DOCUMENT_PATH } from "./localWorld/localWorldDocumentAuthoring";
import { InMemoryLocalWorldRepository, InMemoryLocalWorldStore } from "./localWorld/inMemoryLocalWorldRepository";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Blob as NodeBlob } from "node:buffer";
import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const localRepositoryHarness = vi.hoisted(() => ({
  repository: null as InMemoryLocalWorldRepository | null,
}));

const managedClientHarness = vi.hoisted(() => ({
  created: [] as Array<{
    worldId: string;
    client: { api: { readGraph: () => Promise<unknown> }; invalidate: () => void };
  }>,
}));

vi.mock("./nativeGraphDemo/managedNativeGraphApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./nativeGraphDemo/managedNativeGraphApi")>();
  return {
    ...actual,
    createManagedNativeGraphApi: (worldId: string) => {
      const client = actual.createManagedNativeGraphApi(worldId);
      managedClientHarness.created.push({ worldId, client });
      return client;
    },
  };
});

vi.mock("./localWorld/indexedDbLocalWorldRepository", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./localWorld/indexedDbLocalWorldRepository")>();
  const { InMemoryLocalWorldRepository, InMemoryLocalWorldStore } = await import("./localWorld/inMemoryLocalWorldRepository");
  return {
    ...actual,
    openIndexedDbLocalWorldRepository: async () => ({
      status: "opened" as const,
      repository: localRepositoryHarness.repository!,
    }),
  };
});

vi.mock("./tiptap/MarkdownEditorCore", async () => {
  const React = await import("react");
  return {
    MarkdownEditorCore: ({ content, editable, onUpdate, dataTestId }: {
      content: { content?: readonly { content?: readonly { text?: string }[] }[] };
      editable?: boolean;
      onUpdate?: (json: unknown, editor: { getJSON: () => unknown }, meta: { programmatic: boolean }) => void;
      dataTestId?: string;
    }) => {
      const value = (content.content ?? []).flatMap((node) => node.content ?? []).map((node) => node.text ?? "").join("\n");
      return React.createElement("textarea", {
        "data-testid": dataTestId,
        "aria-label": "World notes editor",
        disabled: !editable,
        value,
        onChange: (event: React.ChangeEvent<HTMLTextAreaElement>) => {
          const json = { type: "doc", content: [{ type: "paragraph", content: [{ type: "text", text: event.target.value }] }] };
          onUpdate?.(json, { getJSON: () => json }, { programmatic: false });
        },
      });
    },
  };
});

vi.mock("./agentInteraction/IndexAgentConversation", () => ({
  IndexAgentConversation: () => <div data-testid="hosted-index-agent" />,
}));

function response(status: number, payload: unknown): Response {
  const make = (): Response => ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
    clone: make,
  } as Response);
  return make();
}

const guestGraph = {
  world_id: "private-space-guest",
  revision_id: "revision-guest-1",
  graph_sha256: "sha256:guest-graph-1",
  nodes: [
    { id: "entity:lina", name: "Lina", kind: "person" },
    { id: "entity:pike", name: "Pike", kind: "person" },
    { id: "entity:quay", name: "Amber Quay", kind: "location" },
  ],
  edges: [{ id: "assertion:lives", source_id: "entity:lina", target_id: "entity:quay", predicate: "lives_near" }],
  storage: "postgres",
  limitations: ["Event typing is not available in this native profile."],
  capabilities: { create: true, connect: true, rename: false, delete: false, object_kinds: ["person", "location"] },
};

function nativeIndexFetch(graph = guestGraph, authStatus: "local_operator" | "signed_out" = "local_operator") {
  return vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === "/api/auth/session") return authStatus === "signed_out"
      ? response(401, { status: "signed_out" })
      : response(200, { status: authStatus });
    if (path === "/api/live/index-graph/session") return response(200, { csrf_token: "guest-csrf" });
    if (path === "/api/live/index-graph/graph") return response(200, graph);
    return response(404, { error: "Not found.", code: "not_found" });
  });
}

function expectOnlyScopedIndexCalls(fetchMock: ReturnType<typeof nativeIndexFetch>): void {
  expect(fetchMock.mock.calls.map(([path]) => String(path))).toEqual(expect.arrayContaining([
    "/api/auth/session",
    "/api/live/index-graph/session",
    "/api/live/index-graph/graph",
  ]));
  expect(fetchMock.mock.calls.every(([path]) => String(path) === "/api/auth/session"
    || String(path).startsWith("/api/live/index-graph/"))).toBe(true);
}

async function graphMenuAction(name: string) {
  const direct = screen.queryByRole("button", { name, exact: true });
  if (direct) return direct;
  const trigger = ["Info", "Refresh", "Export snapshot"].includes(name) ? "More graph actions" : "Graph tools";
  fireEvent.click(await screen.findByRole("button", { name: trigger, exact: true }));
  return screen.getByRole("button", { name, exact: true });
}

// Exercise the connected-only default and its reveal control for isolated
// fixture objects, without changing their graph or bypassing the real UI.
async function revealIsolatedObject(user: ReturnType<typeof userEvent.setup>, name: string, hiddenCount = 1) {
  await user.click(await screen.findByRole("button", { name: "Graph view options" }));
  const reveal = await screen.findByRole("checkbox", { name: `Show objects without listed relationships (${hiddenCount} hidden)` });
  expect(reveal).not.toBeChecked();
  expect(screen.queryByRole("button", { name: `${name}, person` })).not.toBeInTheDocument();
  await user.click(reveal);
  expect(reveal).toBeChecked();
  return screen.findByRole("button", { name: `${name}, person` });
}

function managedWorldRecord(worldId: string, name: string) {
  return {
    schema_version: "dmb_world_container_record_v1",
    world_id: worldId,
    name,
    source_root_relpath: `corpus/${worldId}-markdown`,
    created_at: "2026-01-01T00:00:00Z",
  };
}

function managedGraphEnvelope(worldId: string, name: string) {
  const nativeWorldId = `native-${worldId}`;
  return {
    schema: "dmb_native_graph_explorer_v1",
    managed_world_id: worldId,
    native_world_id: nativeWorldId,
    binding_version: 1,
    graph: {
      ...guestGraph,
      world_id: nativeWorldId,
      revision_id: `revision-${worldId}`,
      nodes: [{ id: `entity:${worldId}`, name, kind: "person" }],
      edges: [],
      completeness: {
        status: "complete",
        listed_entities: 1,
        omitted_entities: 0,
        unexamined_entities: 0,
        listed_assertions: 0,
        omitted_assertions: 0,
        unexamined_assertions: 0,
        reasons: [],
      },
    },
  };
}

function managedServerFetch({
  authStatus = "local_operator",
  graphRead,
}: {
  authStatus?: "local_operator" | "authenticated";
  graphRead?: (worldId: string, readNumber: number) => Promise<Response> | Response;
} = {}) {
  const reads = new Map<string, number>();
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/auth/session") return Response.json({ status: authStatus, ...(authStatus === "authenticated" ? { subject: "owner-a" } : {}) });
    if (path === "/api/live/world-containers") return Response.json({
      schema_version: "dmb_world_container_registry_v1",
      records: [managedWorldRecord("world-a", "World A"), managedWorldRecord("world-b", "World B")],
    });
    if (path === "/api/live/agent/local-session") {
      return init?.method === "POST"
        ? Response.json({ status: "active", csrf_token: "managed-local-csrf" })
        : Response.json({ detail: { code: "graph_auth_required" } }, { status: 401 });
    }
    if (path === "/api/live/native-graph-explorer/graph") {
      const body = JSON.parse(String(init?.body)) as { managed_world_id: string };
      const number = (reads.get(body.managed_world_id) ?? 0) + 1;
      reads.set(body.managed_world_id, number);
      return graphRead
        ? graphRead(body.managed_world_id, number)
        : Response.json(managedGraphEnvelope(body.managed_world_id, body.managed_world_id === "world-a" ? "Aster" : "Bramble"));
    }
    return Response.json({ error: "Not found.", code: "not_found" }, { status: 404 });
  });
  return fetchMock;
}

const initialCreateObjectURL = Object.getOwnPropertyDescriptor(URL, "createObjectURL");
const initialRevokeObjectURL = Object.getOwnPropertyDescriptor(URL, "revokeObjectURL");

function restoreUrlObjectUrlMethods(): void {
  if (initialCreateObjectURL) Object.defineProperty(URL, "createObjectURL", initialCreateObjectURL);
  else Reflect.deleteProperty(URL, "createObjectURL");
  if (initialRevokeObjectURL) Object.defineProperty(URL, "revokeObjectURL", initialRevokeObjectURL);
  else Reflect.deleteProperty(URL, "revokeObjectURL");
}

describe("canonical local guest entry", () => {
  beforeEach(() => {
    vi.stubEnv("PROD", true);
    vi.stubGlobal("crypto", webcrypto as unknown as Crypto);
    vi.stubGlobal("Blob", NodeBlob);
    window.history.replaceState({}, "", "/graph");
    localStorage.clear();
    sessionStorage.clear();
    localRepositoryHarness.repository = new InMemoryLocalWorldRepository({ store: new InMemoryLocalWorldStore() });
    managedClientHarness.created = [];
  });

  afterEach(() => {
    restoreUrlObjectUrlMethods();
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/graph");
  });

  it("keeps older browser Worlds available as a secondary surface without hosted requests", async () => {
    const fetchMock = nativeIndexFetch();
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const mounted = render(<App />);

    expect(await screen.findByRole("button", { name: "Lina, person" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /buddy graph playground/i })).toBeInTheDocument();
    expect(screen.queryByTestId("hosted-index-agent")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Switch World: Choose" })).toBeInTheDocument();
    expectOnlyScopedIndexCalls(fetchMock);

    await user.click(await screen.findByText("Existing browser-only Worlds and notes"));
    expect(await screen.findByRole("button", { name: "Mara Venn, person" })).toBeInTheDocument();
    expect(screen.queryByTestId("hosted-index-agent")).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.every(([path]) => String(path) === "/api/auth/session"
      || String(path).startsWith("/api/live/index-graph/"))).toBe(true);

    await user.click(screen.getByRole("button", { name: "Edit World title" }));
    await user.clear(screen.getByLabelText("World title"));
    await user.type(screen.getByLabelText("World title"), "Guest Harbor");
    await user.click(screen.getByRole("button", { name: "Save title" }));
    expect(await screen.findByRole("heading", { name: "Guest Harbor" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Start writing" }));
    const notes = await screen.findByRole("textbox", { name: "World notes editor" });
    fireEvent.change(notes, { target: { value: "A local note written without an account." } });
    await user.click(screen.getByRole("button", { name: "Save in this browser" }));
    expect(await screen.findAllByText("Saved in this browser")).toHaveLength(2);
    expectOnlyScopedIndexCalls(fetchMock);

    const repository = localRepositoryHarness.repository;
    expect(repository).not.toBeNull();
    const records = await repository!.listWorlds();
    expect(records.status).toBe("found");
    if (records.status !== "found") return;
    expect(records.records).toHaveLength(1);
    const worldId = records.records[0].snapshot.worldId;
    const saved = await repository!.readWorldNotes(worldId);
    expect(saved.status).toBe("found");
    if (saved.status === "found") expect(saved.state.markdown).toBe("A local note written without an account.\n");

    mounted.unmount();
    render(<App />);
    await user.click(await screen.findByText("Existing browser-only Worlds and notes"));
    await user.click(await screen.findByRole("button", { name: /Guest Harbor/ }));
    expect(await screen.findByRole("textbox", { name: "World notes editor" })).toHaveValue("A local note written without an account.");
    expectOnlyScopedIndexCalls(fetchMock);

    let exported: Blob | null = null;
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn((blob: Blob) => { exported = blob; return "blob:guest-world-export"; }),
    });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    await user.click(screen.getByRole("button", { name: "Download World package" }));
    expect(await screen.findByText("Package downloaded. It includes the current local World and its stored attachments.")).toBeInTheDocument();
    expect(exported).toBeInstanceOf(NodeBlob);
    expect(exported!.size).toBeGreaterThan(22);
    const decoded = await decodeLocalWorldPackageZipV1(exported!);
    expect(decoded, decoded.status === "error" ? decoded.message : "").toMatchObject({ status: "staged" });
    if (decoded.status === "staged") {
      expect(decoded.parsed.candidate.record.snapshot.title).toBe("Guest Harbor");
      const noteRef = decoded.parsed.candidate.documents.find((reference) => reference.path === LOCAL_WORLD_NOTES_DOCUMENT_PATH);
      expect(noteRef?.status).toBe("bundled");
      const noteBytes = decoded.parsed.candidate.members.get(LOCAL_WORLD_NOTES_DOCUMENT_PATH);
      expect(noteBytes && new TextDecoder().decode(noteBytes)).toBe("A local note written without an account.\n");
    }
    expectOnlyScopedIndexCalls(fetchMock);
  });

  it("keeps older local graph editing and notes separate from the DungeonMind index graph", async () => {
    const fetchMock = nativeIndexFetch();
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const mounted = render(<App />);

    expect(await screen.findByRole("button", { name: "Lina, person" })).toBeInTheDocument();
    await user.click(await screen.findByText("Existing browser-only Worlds and notes"));
    expect(await screen.findByRole("button", { name: "Mara Venn, person" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Edit World title" }));
    await user.clear(screen.getByLabelText("World title"));
    await user.type(screen.getByLabelText("World title"), "Guest Graph");
    await user.click(screen.getByRole("button", { name: "Save title" }));
    expect(await screen.findByRole("heading", { name: "Guest Graph" })).toBeInTheDocument();

    const mara = await screen.findByRole("button", { name: "Mara Venn, person" });
    await user.click(mara);
    await user.click(screen.getByRole("button", { name: "Rename Mara Venn" }));
    await user.clear(screen.getByRole("textbox", { name: "New name" }));
    await user.type(screen.getByRole("textbox", { name: "New name" }), "Mara Vale");
    await user.click(screen.getByRole("button", { name: "Save name" }));
    await screen.findByRole("button", { name: "Mara Vale, person" });

    await user.click(within(screen.getByRole("main", { name: "Buddy Surface" })).getByRole("button", { name: "Add object" }));
    await user.type(screen.getByRole("textbox", { name: "Object name" }), "Tomas's Cartographer");
    await user.click(screen.getByRole("button", { name: "Create object" }));
    const addedNode = await screen.findByRole("button", { name: "Tomas's Cartographer, person" });
    await user.click(addedNode);
    await user.click(screen.getByRole("button", { name: "Connect selected objects" }));
    await user.type(screen.getByRole("textbox", { name: "Relationship label" }), "travels with");
    await user.click(screen.getByRole("button", { name: "Create relationship" }));
    expect(await screen.findByRole("img", { name: "Mara Vale travels with Tomas's Cartographer" })).toBeInTheDocument();

    const repository = localRepositoryHarness.repository;
    expect(repository).not.toBeNull();
    const listed = await repository!.listWorlds();
    expect(listed.status).toBe("found");
    if (listed.status !== "found") return;
    const worldId = listed.records[0].snapshot.worldId;
    const beforeMove = await repository!.readWorld(worldId);
    expect(beforeMove.status).toBe("found");
    if (beforeMove.status !== "found") return;
    const renamedObject = beforeMove.record.snapshot.objects.find((object) => object.name === "Mara Vale");
    expect(renamedObject).toBeDefined();
    const oldPosition = beforeMove.record.layout.positions[renamedObject!.id];
    fireEvent.keyDown(screen.getByRole("button", { name: "Mara Vale, person" }), { key: "ArrowRight" });
    await waitFor(async () => {
      const moved = await repository!.readWorld(worldId);
      expect(moved.status).toBe("found");
      if (moved.status === "found") expect(moved.record.layout.positions[renamedObject!.id]).not.toEqual(oldPosition);
    });

    mounted.unmount();
    render(<App />);
    await user.click(await screen.findByText("Existing browser-only Worlds and notes"));
    await user.click(await screen.findByRole("button", { name: /Guest Graph/ }));
    expect(await screen.findByRole("button", { name: "Mara Vale, person" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Mara Vale travels with Tomas's Cartographer" })).toBeInTheDocument();
    const reopened = await repository!.readWorld(worldId);
    expect(reopened.status).toBe("found");
    if (reopened.status !== "found") return;
    expect(reopened.record.snapshot.relationships).toHaveLength(5);
    expect(reopened.record.layout.positions[renamedObject!.id]).not.toEqual(oldPosition);

    let exported: Blob | null = null;
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn((blob: Blob) => { exported = blob; return "blob:guest-graph-export"; }) });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    await user.click(screen.getByRole("button", { name: "Download World package" }));
    expect(await screen.findByText("Package downloaded. It includes the current local World and its stored attachments.")).toBeInTheDocument();
    expect(exported).toBeInstanceOf(NodeBlob);
    const decoded = await decodeLocalWorldPackageZipV1(exported!);
    expect(decoded.status).toBe("staged");
    if (decoded.status === "staged") {
      expect(decoded.parsed.candidate.record.snapshot.objects.map((object) => object.name)).toContain("Mara Vale");
      expect(decoded.parsed.candidate.record.snapshot.relationships).toHaveLength(5);
      expect(decoded.parsed.candidate.record.layout.positions[renamedObject!.id]).not.toEqual(oldPosition);
    }
    expectOnlyScopedIndexCalls(fetchMock);
  });

  it("uses the scoped native graph at the guest index, preserves a draft, and reviews a single confirmed operation", async () => {
    let currentGraph = guestGraph;
    let resolvePrepare!: (value: Response) => void;
    const prepareResponse = new Promise<Response>((resolve) => { resolvePrepare = resolve; });
    const calls: Array<{ path: string; init?: RequestInit }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      calls.push({ path, init });
      if (path === "/api/auth/session") return response(200, { status: "local_operator" });
      if (path === "/api/live/index-graph/session") return response(200, { csrf_token: "guest-csrf" });
      if (path === "/api/live/index-graph/graph") return response(200, currentGraph);
      if (path === "/api/live/index-graph/prepare") return prepareResponse;
      if (path === "/api/live/index-graph/confirm") {
        const createdGraph = {
          ...currentGraph,
          revision_id: "revision-guest-2",
          graph_sha256: "sha256:guest-graph-2",
          nodes: [...currentGraph.nodes, { id: "entity:aster", name: "Aster", kind: "person" }],
        };
        currentGraph = createdGraph;
        return response(200, { status: "committed", graph: createdGraph });
      }
      return response(404, { error: "Not found.", code: "not_found" });
    });
    vi.stubGlobal("fetch", fetchMock);
    const operationId = "8e05e7e6-2ec8-43bd-bc4e-63a5b92eb84b";
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue(operationId);
    const user = userEvent.setup();
    const mounted = render(<App />, { reactStrictMode: true });

    expect(await screen.findByRole("button", { name: "Lina, person" })).toBeInTheDocument();
    expect(screen.getByText("Buddy playground · private graph")).toBeInTheDocument();
    await user.click(await graphMenuAction("Info"));
    expect(screen.getByText(/Event typing is not available in this native profile/)).toBeInTheDocument();
    expect(screen.getByText("Rename is unavailable")).toBeInTheDocument();
    expect(screen.getByText("Delete is unavailable")).toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([path]) => String(path) === "/api/live/index-graph/session")).toHaveLength(1);
    expect(fetchMock.mock.calls.some(([path]) => String(path) === "/api/live/index-graph/graph")).toBe(true);

    await user.click(await graphMenuAction("Add object"));
    const name = screen.getByLabelText("Name");
    await user.type(name, "Aster");
    mounted.unmount();
    render(<App />, { reactStrictMode: true });
    await user.click(await graphMenuAction("Add object"));
    expect(await screen.findByDisplayValue("Aster")).toBeInTheDocument();

    const prepareButton = screen.getByRole("button", { name: "Prepare object" });
    fireEvent.click(prepareButton);
    fireEvent.click(prepareButton);
    await waitFor(() => expect(calls.filter(({ path }) => path.endsWith("/prepare"))).toHaveLength(1));
    const prepareCall = calls.find(({ path }) => path.endsWith("/prepare"));
    expect(JSON.parse(String(prepareCall?.init?.body))).toEqual({
      operation_id: operationId,
      expected_revision_id: "revision-guest-1",
      kind: "create_object",
      name: "Aster",
      object_kind: "person",
    });
    expect(new Headers(prepareCall?.init?.headers).get("X-DMB-Index-Graph-CSRF")).toBe("guest-csrf");

    resolvePrepare(response(200, {
      status: "prepared",
      operation_id: operationId,
      parent_revision_id: "revision-guest-1",
      review: { summary: "Create Aster as a native person in this private graph." },
    }));
    expect(await screen.findByText("Create Aster as a native person in this private graph.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Confirm in DungeonMind" }));
    // This legacy response has no exact created-ID receipt. Reveal the saved
    // isolate explicitly rather than identifying or selecting it by its name.
    expect(await revealIsolatedObject(user, "Aster", 2)).toBeInTheDocument();
    expect(calls.filter(({ path }) => path.endsWith("/prepare"))).toHaveLength(1);
    expect(calls.filter(({ path }) => path.endsWith("/confirm"))).toHaveLength(1);
    expect(new Headers(calls.find(({ path }) => path.endsWith("/confirm"))?.init?.headers).get("X-DMB-Index-Graph-CSRF")).toBe("guest-csrf");
    expect(fetchMock.mock.calls.every(([path]) => String(path) === "/api/auth/session"
      || String(path).startsWith("/api/live/index-graph/"))).toBe(true);
    expect(screen.getByRole("button", { name: "Switch World: Choose" })).toBeInTheDocument();
  });

  it("shows recoverable session and malformed-graph errors instead of a browser-local fallback", async () => {
    let sessionAvailable = false;
    let graphMalformed = true;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/auth/session") return response(200, { status: "local_operator" });
      if (path === "/api/live/index-graph/session") {
        if (!sessionAvailable) throw new Error("connection refused");
        return response(200, { csrf_token: "guest-csrf" });
      }
      if (path === "/api/live/index-graph/graph") {
        return response(200, graphMalformed ? { ...guestGraph, capabilities: undefined } : guestGraph);
      }
      return response(404, { error: "Not found.", code: "not_found" });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByText(/connection refused/)).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path]) => String(path))).toEqual([
      "/api/auth/session",
      "/api/live/index-graph/session",
    ]);
    expect(screen.queryByRole("button", { name: "Lina, person" })).not.toBeInTheDocument();
    sessionAvailable = true;
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText(/incomplete or unsupported response/)).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([path]) => String(path) === "/api/live/index-graph/graph")).toBe(true);
    expect(screen.queryByRole("button", { name: "Lina, person" })).not.toBeInTheDocument();

    graphMalformed = false;
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("button", { name: "Lina, person" })).toBeInTheDocument();
    expect(fetchMock.mock.calls.every(([path]) => String(path) === "/api/auth/session"
      || String(path).startsWith("/api/live/index-graph/"))).toBe(true);
  });

  it("retains local-operator access when navigating to a protected route and returning to the index", async () => {
    const indexFetch = nativeIndexFetch();
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input) === "/api/auth/session") return response(200, { status: "local_operator" });
      if (String(input).startsWith("/api/live/index-graph/")) return indexFetch(input);
      return response(401, { status: "signed_out" });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByRole("button", { name: "Lina, person" })).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path]) => String(path))).toEqual([
      "/api/auth/session",
      "/api/live/index-graph/session",
      "/api/live/index-graph/graph",
    ]);

    await user.click(screen.getByRole("button", { name: "Open navigation" }));
    await user.click(screen.getByRole("link", { name: "Plan" }));
    await waitFor(() => expect(window.location.pathname).toBe("/plan"));
    expect(screen.queryByRole("link", { name: "Sign in with DungeonMind" })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([path]) => String(path) === "/api/auth/session")).toHaveLength(1);

    await act(async () => {
      window.history.back();
      await waitFor(() => expect(window.location.pathname).toBe("/graph"));
    });
    expect(await screen.findByRole("button", { name: "Lina, person" })).toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([path]) => String(path) === "/api/auth/session")).toHaveLength(1);
  });

  it("shows a distinct hosted signed-out playground and sign-in path without calling the local guest API", async () => {
    const fetchMock = nativeIndexFetch(guestGraph, "signed_out");
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/graph");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Buddy graph playground" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Plan" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in with DungeonMind" })).toHaveAttribute(
      "href", "/api/auth/login?return_to=%2Fgraph",
    );
    expect(screen.queryByRole("button", { name: "Lina, person" })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path]) => String(path))).toEqual(["/api/auth/session"]);
  });

  it("never treats an unavailable authentication check as signed out or as a playground", async () => {
    const fetchMock = vi.fn(async () => response(503, { status: "unavailable" }));
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/graph");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Sign-in status is unavailable" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Buddy graph playground" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Lina, person" })).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it.each(["authenticated", "local_operator"] as const)(
    "loads the real selected World graph and keeps its verified title paired in %s mode",
    async (authStatus) => {
      vi.stubEnv("PROD", true);
      window.history.replaceState({}, "", "/graph?world=world-a");
      const fetchMock = managedServerFetch({ authStatus });
      vi.stubGlobal("fetch", fetchMock);
      const user = userEvent.setup();

      render(<App />, { reactStrictMode: true });

      expect(await revealIsolatedObject(user, "Aster")).toBeInTheDocument();
      expect(screen.getByText("World · World A")).toBeInTheDocument();
      expect(fetchMock.mock.calls.some(([path]) => String(path) === "/api/live/native-graph-explorer/graph")).toBe(true);
      const graphCall = fetchMock.mock.calls.find(([path]) => String(path) === "/api/live/native-graph-explorer/graph");
      expect(JSON.parse(String(graphCall?.[1]?.body))).toEqual({ managed_world_id: "world-a" });
      expect(new Headers(graphCall?.[1]?.headers).get("X-DMB-Graph-CSRF")).toBe("managed-local-csrf");
      expect(fetchMock.mock.calls.some(([path]) => String(path).startsWith("/api/live/index-graph/"))).toBe(false);
    },
  );

  it("keeps an empty authenticated selection in an explicit playground with a World chooser", async () => {
    vi.stubEnv("PROD", true);
    window.history.replaceState({}, "", "/graph");
    const fetchMock = managedServerFetch({ authStatus: "authenticated" });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Buddy graph playground" })).toBeInTheDocument();
    expect(screen.getByText(/choose a World to browse its graph/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Switch World: Choose" })).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([path]) => String(path) === "/api/live/native-graph-explorer/graph"
      || String(path).startsWith("/api/live/index-graph/"))).toBe(false);
  });

  it("keeps the selected World title and error when its managed graph cannot be read", async () => {
    vi.stubEnv("PROD", true);
    window.history.replaceState({}, "", "/graph?world=world-a");
    const fetchMock = managedServerFetch({
      graphRead: () => Response.json({ error: "Native graph read is unavailable.", code: "graph_read_failed" }, { status: 503 }),
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByText(/Native graph read is unavailable/)).toBeInTheDocument();
    expect(screen.getByText("World · World A")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Aster, person" })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([path]) => String(path).startsWith("/api/live/index-graph/"))).toBe(false);
  });

  it("does not apply a late World A graph response after switching to World B", async () => {
    vi.stubEnv("PROD", true);
    window.history.replaceState({}, "", "/graph?world=world-a");
    let resolveSecondA!: (value: Response) => void;
    const secondA = new Promise<Response>((resolve) => { resolveSecondA = resolve; });
    const fetchMock = managedServerFetch({
      graphRead: (worldId, readNumber) => worldId === "world-a" && readNumber === 2
        ? secondA
        : Response.json(managedGraphEnvelope(worldId, worldId === "world-a" ? "Aster" : "Bramble")),
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<App />);
    expect(await revealIsolatedObject(user, "Aster")).toBeInTheDocument();
    await user.click(await graphMenuAction("Refresh"));
    await waitFor(() => expect(fetchMock.mock.calls.filter(([path, init]) => String(path) === "/api/live/native-graph-explorer/graph"
      && JSON.parse(String(init?.body)).managed_world_id === "world-a")).toHaveLength(2));

    await user.click(screen.getByRole("button", { name: "Switch World: World A" }));
    await user.click(await screen.findByRole("button", { name: "World B" }));
    expect(await revealIsolatedObject(user, "Bramble")).toBeInTheDocument();
    expect(screen.getByText("World · World B")).toBeInTheDocument();

    await act(async () => resolveSecondA(Response.json(managedGraphEnvelope("world-a", "Aster late"))));
    expect(screen.getByRole("button", { name: "Bramble, person" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Aster late, person" })).not.toBeInTheDocument();
  });

  it("owns a fresh managed client through StrictMode replay, World switching, and unmount", async () => {
    vi.stubEnv("PROD", true);
    window.history.replaceState({}, "", "/graph?world=world-a");
    const fetchMock = managedServerFetch();
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const mounted = render(<StrictMode><App /></StrictMode>);

    expect(await revealIsolatedObject(user, "Aster")).toBeInTheDocument();
    const clientsFor = (worldId: string) => managedClientHarness.created
      .filter((entry) => entry.worldId === worldId)
      .map((entry) => entry.client);
    const worldAClients = clientsFor("world-a");
    expect(worldAClients.length).toBeGreaterThanOrEqual(2);
    const replayRetiredA = worldAClients[0];
    const liveA = worldAClients[worldAClients.length - 1];

    const callsBeforeRetiredRead = fetchMock.mock.calls.length;
    await expect(replayRetiredA.api.readGraph()).rejects.toMatchObject({
      name: "NativeGraphDemoApiError",
      code: "invalid_managed_world_response",
    });
    expect(fetchMock).toHaveBeenCalledTimes(callsBeforeRetiredRead);
    await expect(liveA.api.readGraph()).resolves.toMatchObject({
      world_id: "native-world-a",
      revision_id: "revision-world-a",
    });

    await user.click(screen.getByRole("button", { name: "Switch World: World A" }));
    await user.click(await screen.findByRole("button", { name: "World B" }));
    expect(await revealIsolatedObject(user, "Bramble")).toBeInTheDocument();
    expect(screen.getByText("World · World B")).toBeInTheDocument();

    const worldBClients = clientsFor("world-b");
    expect(worldBClients.length).toBeGreaterThanOrEqual(2);
    const liveB = worldBClients[worldBClients.length - 1];
    for (const retiredA of worldAClients) {
      await expect(retiredA.api.readGraph()).rejects.toMatchObject({
        name: "NativeGraphDemoApiError",
        code: "invalid_managed_world_response",
      });
    }
    await expect(liveB.api.readGraph()).resolves.toMatchObject({
      world_id: "native-world-b",
      revision_id: "revision-world-b",
    });

    mounted.unmount();
    await expect(liveB.api.readGraph()).rejects.toMatchObject({
      name: "NativeGraphDemoApiError",
      code: "invalid_managed_world_response",
    });
  });

  it("retains existing local-operator managed drafts under their original storage key", async () => {
    window.history.replaceState({}, "", "/graph?world=world-a");
    sessionStorage.setItem("dungeonmind-native-demo:draft:managed%3Aworld-a:native-world-a", JSON.stringify({
      version: 1, world_id: "native-world-a", pending: null, pending_phase: "prepare",
      draft: { objectName: "Pre-existing local draft", objectKind: "person", sourceId: "", targetId: "", predicate: "" },
    }));
    vi.stubGlobal("fetch", managedServerFetch());
    const user = userEvent.setup();
    render(<App />);
    await revealIsolatedObject(user, "Aster");
    await user.click(await graphMenuAction("Add object"));
    expect(screen.getByLabelText("Name")).toHaveValue("Pre-existing local draft");
  });

  it("browses an assigned hosted World without exposing authoring", async () => {
    window.history.replaceState({}, "", "/graph?world=world-a");
    const fetchMock = managedServerFetch({ authStatus: "authenticated" });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    expect(await revealIsolatedObject(userEvent.setup(), "Aster")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add object" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Connect" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Plan" })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.every(([path]) => [
      "/api/auth/session", "/api/live/world-containers", "/api/live/native-graph-explorer/graph",
    ].includes(String(path)))).toBe(true);
  });

  it("posts sign-out to Buddy and reports a failed response", async () => {
    window.history.replaceState({}, "", "/");
    const fetchMock = vi.fn(async (url: RequestInfo | URL, _init?: RequestInit) => {
      if (url === "/api/auth/session") return Response.json({ status: "authenticated", subject: "owner" });
      if (url === "/api/auth/logout") return Response.json({}, { status: 503 });
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await userEvent.setup().click(await screen.findByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Sign-out failed");
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/logout", expect.objectContaining({
      method: "POST", credentials: "same-origin",
    }));
  });

  it.each(["/plan", "/play", "/build", "/ingest", "/combat", "/statblock", "/surface"])(
    "guards direct hosted entry to %s without mounting the workspace",
    async (path) => {
      window.history.replaceState({}, "", path);
      const fetchMock = managedServerFetch({ authStatus: "authenticated" });
      vi.stubGlobal("fetch", fetchMock);
      render(<App />);

      expect(await screen.findByRole("heading", { name: "This page is unavailable on hosted Buddy" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Open Graph" })).toHaveAttribute("href", "/graph");
      expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual(["/api/auth/session"]);
    },
  );

  it("inspects a hosted canvas point at the exact loaded pin without source or statblock requests", async () => {
    const dom = (globalThis as unknown as { jsdom: { reconfigure: (options: { url: string }) => void } }).jsdom;
    const originalUrl = window.location.href;
    dom.reconfigure({ url: "https://buddy.example/graph?world=world-a" });
    const envelope = managedGraphEnvelope("world-a", "Aster");
    const pin = { managed_world_id: "world-a", native_world_id: "native-world-a", binding_version: 1,
      revision_id: "revision-world-a", scope_mode: "world", campaign_id: null };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/api/auth/session") return Response.json({ status: "authenticated", subject: "hosted-owner" });
      if (path === "/api/live/world-containers") return Response.json({ schema_version: "dmb_world_container_registry_v1",
        records: [managedWorldRecord("world-a", "Owned World")] });
      if (path === "/api/live/native-graph-explorer/graph") return Response.json(envelope);
      if (path === "/api/live/native-graph-inspection/read") {
        expect(JSON.parse(String(init?.body))).toEqual({ scope: pin, selection: { kind: "entity", entity_id: "entity:world-a" } });
        return Response.json({ schema: "dmb_native_graph_entity_v1", scope: pin, entity: {
          found: true,
          assertions: [{ assertion_id: "assertion:description", subject_entity_id: "entity:world-a", predicate: "custom:description",
            value: { kind: "literal", value: "Keeps the observatory charts." }, metadata: {
              scope: [], visibility: { kind: "public" }, epistemic_basis: "reported", claim_mode: "dungeonbuddy.claim:belief",
              standing: "provisional", evidence_ref_ids: ["evidence:source"], temporal_scope: { kind: "unknown" }, domain_metadata: [],
            } }],
          evidence: [{ evidence_ref_id: "evidence:source", evidence_role: "support" }],
          completeness: { status: "complete", reason: null },
        } });
      }
      throw new Error(`Unexpected hosted request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const mounted = render(<App />, { reactStrictMode: true });
    try {
      const point = await revealIsolatedObject(user, "Aster");
      expect(fetchMock.mock.calls.some(([path]) => String(path) === "/api/live/native-graph-inspection/read")).toBe(false);
      await user.click(point);
      expect(await screen.findByText("Aster · description: Keeps the observatory charts.")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Object details" })).toBeInTheDocument();
      expect(screen.getByText("belief · reported · provisional")).toBeInTheDocument();
      expect(screen.getByText("Source excerpts and linked statblocks are not available in the hosted explorer yet.")).toBeInTheDocument();
      await user.click(screen.getByText("Record qualifications"));
      expect(screen.getByText(/"temporal_scope"/)).toHaveTextContent("unknown");
      expect(screen.queryByRole("button", { name: "Read supporting source" })).not.toBeInTheDocument();
      expect(screen.queryByRole("region", { name: "Linked statblocks" })).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Focus", exact: true }));
      await user.click(screen.getByRole("button", { name: "Close details" }));
      expect(screen.queryByText("Aster · description: Keeps the observatory charts.")).not.toBeInTheDocument();
      const reads = fetchMock.mock.calls.filter(([path]) => String(path) === "/api/live/native-graph-inspection/read");
      expect(reads).toHaveLength(1);
      expect(reads[0][1]).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
      expect(new Headers(reads[0][1]?.headers).has("Authorization")).toBe(false);
      expect(new Headers(reads[0][1]?.headers).has("X-DMB-Graph-CSRF")).toBe(false);
      expect(fetchMock.mock.calls.every(([path]) => ["/api/auth/session", "/api/live/world-containers",
        "/api/live/native-graph-explorer/graph", "/api/live/native-graph-inspection/read"].includes(String(path)))).toBe(true);
    } finally {
      mounted.unmount();
      dom.reconfigure({ url: originalUrl });
    }
  });

  it("rechecks World selection on account switch and isolates graph responses even for the same World ID", async () => {
    let subject = "owner-a";
    const backend = managedServerFetch();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/api/auth/session") return Response.json({ status: "authenticated", subject });
      if (path === "/api/live/native-graph-explorer/graph") {
        return Response.json(managedGraphEnvelope("world-a", subject === "owner-a" ? "Aster" : "Bramble"));
      }
      return backend(input, init);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/graph?world=world-a");
    const user = userEvent.setup();
    render(<App />);
    await revealIsolatedObject(user, "Aster");
    subject = "owner-b";
    fireEvent(window, new Event("focus"));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Aster, person" })).not.toBeInTheDocument());
    await revealIsolatedObject(user, "Bramble");
    expect(screen.queryByRole("button", { name: "Aster, person" })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([path]) => String(path) === "/api/live/world-containers")).toHaveLength(2);
    subject = "owner-a";
    fireEvent(window, new Event("focus"));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Bramble, person" })).not.toBeInTheDocument());
    await revealIsolatedObject(user, "Aster");
  });

  it.each(["signed_out", "unavailable"] as const)("removes the selected graph on %s and discards its pending response", async nextStatus => {
    let status = "authenticated";
    let resolveRead!: (response: Response) => void;
    const oldResponse = new Promise<Response>(resolve => { resolveRead = resolve; });
    const backend = managedServerFetch({ graphRead: (_worldId, readNumber) => readNumber === 1
      ? Response.json(managedGraphEnvelope("world-a", "Aster")) : oldResponse });
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) === "/api/auth/session") return Response.json(
        status === "authenticated" ? { status, subject: "owner-a" } : { status },
        { status: status === "signed_out" ? 401 : status === "unavailable" ? 503 : 200 });
      return backend(input, init);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/graph?world=world-a");
    const user = userEvent.setup();
    render(<App />);
    await revealIsolatedObject(user, "Aster");
    await user.click(await graphMenuAction("Refresh"));
    await waitFor(() => expect(fetchMock.mock.calls.filter(([path]) => String(path) === "/api/live/native-graph-explorer/graph")).toHaveLength(2));
    status = nextStatus;
    fireEvent(window, new Event("focus"));
    await screen.findByRole("heading", { name: nextStatus === "signed_out" ? "Sign in to DungeonMind" : "Sign-in status is unavailable" });
    expect(screen.queryByRole("button", { name: "Aster, person" })).not.toBeInTheDocument();
    await act(async () => resolveRead(Response.json(managedGraphEnvelope("world-a", "Old private graph"))));
    expect(screen.queryByRole("button", { name: "Old private graph, person" })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([path]) => String(path).startsWith("/api/live/index-graph/"))).toBe(false);
  });

  it("does not select a late old-owner World list after a new login", async () => {
    let subject = "owner-a";
    let resolveOld!: (response: Response) => void;
    const oldList = new Promise<Response>(resolve => { resolveOld = resolve; });
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input) === "/api/auth/session") return Response.json({ status: "authenticated", subject });
      if (String(input) === "/api/live/world-containers") return subject === "owner-a" ? oldList
        : Response.json({ schema_version: "dmb_world_container_registry_v1", records: [] });
      return Response.json({}, { status: 403 });
    });
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/graph?world=world-a");
    render(<App />);
    await screen.findByText("Verifying World selection…");
    await waitFor(() => expect(fetchMock.mock.calls.filter(([path]) => String(path) === "/api/live/world-containers")).toHaveLength(1));
    subject = "owner-b";
    fireEvent(window, new Event("focus"));
    await screen.findByText("World selection unavailable");
    await act(async () => resolveOld(Response.json({ schema_version: "dmb_world_container_registry_v1",
      records: [managedWorldRecord("world-a", "Owner A secret world")] })));
    expect(screen.queryByText("Owner A secret world")).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([path]) => String(path) === "/api/live/native-graph-explorer/graph")).toBe(false);
  });

  it.each(["/graph?world=hosted-world", "/graph?auth_error=cancelled", "/graph#section", "/unknown-path"]) (
    "does not expose a guest surface for %s",
    async (pathname) => {
      window.history.replaceState({}, "", pathname);
      const fetchMock = vi.fn(async () => response(401, { status: "signed_out" }));
      vi.stubGlobal("fetch", fetchMock);
      render(<App />);
      expect(await screen.findByRole("link", { name: "Sign in with DungeonMind" })).toBeInTheDocument();
      expect(screen.queryByLabelText("Buddy Surface")).not.toBeInTheDocument();
      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/auth/session");
    },
  );
});
