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

function response(status: number, payload: Record<string, string>): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => payload } as Response;
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
    localRepositoryHarness.repository = new InMemoryLocalWorldRepository({ store: new InMemoryLocalWorldStore() });
  });

  afterEach(() => {
    restoreUrlObjectUrlMethods();
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/");
  });

  it("creates, saves, reopens and exports a World without hosted requests", async () => {
    const fetchMock = vi.fn(async () => response(401, { status: "signed_out" }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const mounted = render(<App />);

    expect(await screen.findByText("No local Worlds yet. Create one when you’re ready.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.queryByTestId("hosted-index-agent")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Switch World: Choose" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("app-chrome-world-graph-status")).not.toBeInTheDocument();

    await user.type(screen.getByLabelText("Create a World"), "Guest Harbor");
    await user.click(screen.getByRole("button", { name: "Create World" }));
    expect(await screen.findByRole("heading", { name: "Guest Harbor" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Start writing" }));
    const notes = await screen.findByRole("textbox", { name: "World notes editor" });
    fireEvent.change(notes, { target: { value: "A local note written without an account." } });
    await user.click(screen.getByRole("button", { name: "Save in this browser" }));
    expect(await screen.findAllByText("Saved in this browser")).toHaveLength(2);
    expect(fetchMock).not.toHaveBeenCalled();

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
    await user.click(await screen.findByRole("button", { name: /Guest Harbor/ }));
    expect(await screen.findByRole("textbox", { name: "World notes editor" })).toHaveValue("A local note written without an account.");
    expect(fetchMock).not.toHaveBeenCalled();

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
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("keeps protected navigation behind sign-in and returns to the local root on Back", async () => {
    const fetchMock = vi.fn(async () => response(401, { status: "signed_out" }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByText("No local Worlds yet. Create one when you’re ready.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Open navigation" }));
    await user.click(screen.getByRole("link", { name: "Plan" }));
    const signIn = await screen.findByRole("link", { name: "Sign in with DungeonMind" });
    expect(signIn.getAttribute("href")).toBe("/api/auth/login?return_to=%2Fplan");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/auth/session");

    await act(async () => {
      window.history.back();
      await waitFor(() => expect(window.location.pathname).toBe("/"));
    });
    expect(await screen.findByText("No local Worlds yet. Create one when you’re ready.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
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
