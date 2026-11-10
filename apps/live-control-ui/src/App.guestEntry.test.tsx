// @vitest-environment jsdom
import { App } from "./App";
import { decodeLocalWorldPackageZipV1 } from "./localWorld/localWorldPackageZipV1";
import { LOCAL_WORLD_NOTES_DOCUMENT_PATH } from "./localWorld/localWorldDocumentAuthoring";
import { InMemoryLocalWorldRepository, InMemoryLocalWorldStore } from "./localWorld/inMemoryLocalWorldRepository";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Blob as NodeBlob } from "node:buffer";
import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const localRepositoryHarness = vi.hoisted(() => ({
  repository: null as InMemoryLocalWorldRepository | null,
}));

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

function nativeIndexFetch(graph = guestGraph) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === "/api/live/index-graph/session") return response(200, { csrf_token: "guest-csrf" });
    if (path === "/api/live/index-graph/graph") return response(200, graph);
    return response(404, { error: "Not found.", code: "not_found" });
  });
}

function expectOnlyScopedIndexCalls(fetchMock: ReturnType<typeof nativeIndexFetch>): void {
  expect(fetchMock.mock.calls.map(([path]) => String(path))).toEqual(expect.arrayContaining([
    "/api/live/index-graph/session",
    "/api/live/index-graph/graph",
  ]));
  expect(fetchMock.mock.calls.every(([path]) => String(path).startsWith("/api/live/index-graph/"))).toBe(true);
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
    window.history.replaceState({}, "", "/");
    localStorage.clear();
    sessionStorage.clear();
    localRepositoryHarness.repository = new InMemoryLocalWorldRepository({ store: new InMemoryLocalWorldStore() });
  });

  afterEach(() => {
    restoreUrlObjectUrlMethods();
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/");
  });

  it("keeps older browser Worlds available as a secondary surface without hosted requests", async () => {
    const fetchMock = nativeIndexFetch();
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const mounted = render(<App />);

    expect(await screen.findByRole("button", { name: "Lina, person" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /buddy graph playground/i })).toBeInTheDocument();
    expect(screen.queryByTestId("hosted-index-agent")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Switch World: Choose" })).not.toBeInTheDocument();
    expectOnlyScopedIndexCalls(fetchMock);

    await user.click(screen.getByText("Existing browser-only Worlds and notes"));
    expect(await screen.findByRole("button", { name: "Mara Venn, person" })).toBeInTheDocument();
    expect(screen.queryByTestId("hosted-index-agent")).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.every(([path]) => String(path).startsWith("/api/live/index-graph/"))).toBe(true);

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
    await user.click(screen.getByText("Existing browser-only Worlds and notes"));
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
    await user.click(screen.getByText("Existing browser-only Worlds and notes"));
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

    await user.click(screen.getByRole("button", { name: "Add object" }));
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
    await user.click(screen.getByText("Existing browser-only Worlds and notes"));
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
    expect(screen.getByText(/private demo graph is separate from your existing Worlds/i)).toBeInTheDocument();
    expect(screen.getByText(/Event typing is not supported by this DungeonMind profile yet/)).toBeInTheDocument();
    expect(screen.getByText("Rename is unavailable")).toBeInTheDocument();
    expect(screen.getByText("Delete is unavailable")).toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([path]) => String(path) === "/api/live/index-graph/session")).toHaveLength(1);
    expect(fetchMock.mock.calls.some(([path]) => String(path) === "/api/live/index-graph/graph")).toBe(true);

    const name = screen.getByLabelText("Name");
    await user.type(name, "Aster");
    mounted.unmount();
    render(<App />, { reactStrictMode: true });
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
    expect(await screen.findByRole("button", { name: "Aster, person" })).toBeInTheDocument();
    expect(calls.filter(({ path }) => path.endsWith("/prepare"))).toHaveLength(1);
    expect(calls.filter(({ path }) => path.endsWith("/confirm"))).toHaveLength(1);
    expect(new Headers(calls.find(({ path }) => path.endsWith("/confirm"))?.init?.headers).get("X-DMB-Index-Graph-CSRF")).toBe("guest-csrf");
    expect(fetchMock.mock.calls.every(([path]) => String(path).startsWith("/api/live/index-graph/"))).toBe(true);
    expect(screen.queryByRole("button", { name: "Switch World: Choose" })).not.toBeInTheDocument();
  });

  it("shows recoverable session and malformed-graph errors instead of a browser-local fallback", async () => {
    let sessionAvailable = false;
    let graphMalformed = true;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
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
    expect(fetchMock.mock.calls.map(([path]) => String(path))).toEqual(["/api/live/index-graph/session"]);
    expect(screen.queryByRole("button", { name: "Lina, person" })).not.toBeInTheDocument();
    sessionAvailable = true;
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText(/incomplete or unsupported response/)).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([path]) => String(path) === "/api/live/index-graph/graph")).toBe(true);
    expect(screen.queryByRole("button", { name: "Lina, person" })).not.toBeInTheDocument();

    graphMalformed = false;
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("button", { name: "Lina, person" })).toBeInTheDocument();
    expect(fetchMock.mock.calls.every(([path]) => String(path).startsWith("/api/live/index-graph/"))).toBe(true);
  });

  it("keeps protected navigation behind sign-in and returns to the local root on Back", async () => {
    const indexFetch = nativeIndexFetch();
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).startsWith("/api/live/index-graph/")) return indexFetch(input);
      return response(401, { status: "signed_out" });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByRole("button", { name: "Lina, person" })).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path]) => String(path))).toEqual([
      "/api/live/index-graph/session",
      "/api/live/index-graph/graph",
    ]);

    await user.click(screen.getByRole("button", { name: "Open navigation" }));
    await user.click(screen.getByRole("link", { name: "Plan" }));
    const signIn = await screen.findByRole("link", { name: "Sign in with DungeonMind" });
    expect(signIn.getAttribute("href")).toBe("/api/auth/login?return_to=%2Fplan");
    expect(fetchMock.mock.calls.filter(([path]) => String(path) === "/api/auth/session")).toHaveLength(1);

    await act(async () => {
      window.history.back();
      await waitFor(() => expect(window.location.pathname).toBe("/"));
    });
    expect(await screen.findByRole("button", { name: "Lina, person" })).toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([path]) => String(path) === "/api/auth/session")).toHaveLength(1);
  });

  it.each(["/?world=hosted-world", "/?auth_error=cancelled", "/#section", "/unknown-path"]) (
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
