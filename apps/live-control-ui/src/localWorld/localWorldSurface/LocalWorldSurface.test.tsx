// @vitest-environment jsdom
import { AgentInteractionProvider } from "../../agentInteraction/AgentInteractionProvider";
import { InMemoryLocalWorldRepository, InMemoryLocalWorldStore } from "../inMemoryLocalWorldRepository";
import { createPackageTestRecord, packageFixtureAttachmentBytes } from "../localWorldPackageFixtures";
import type { LocalWorldPackageData } from "../localWorldRepository";
import { LocalWorldSurface } from "./LocalWorldSurface";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

function renderSurface(repository: InMemoryLocalWorldRepository) {
  return render(<AgentInteractionProvider><LocalWorldSurface openRepository={async () => ({ status: "opened", repository })} /></AgentInteractionProvider>);
}

function beforeUnloadIsPrevented(): boolean {
  const event = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(event);
  return event.defaultPrevented;
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("local World Surface", () => {
  it("does not create a World on entry and supports explicit create, rename, save and resume", async () => {
    const user = userEvent.setup();
    const repository = new InMemoryLocalWorldRepository();
    const { unmount } = renderSurface(repository);

    expect(await screen.findByText("No local Worlds yet. Create one when you’re ready.")).toBeTruthy();
    const emptyList = await repository.listWorlds();
    expect(emptyList.status).toBe("found");
    if (emptyList.status === "found") expect(emptyList.records).toHaveLength(0);
    await user.click(screen.getByText("Save menu"));
    expect(screen.getByRole("button", { name: "Save in this browser" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Download World package" })).toBeDisabled();

    await user.type(screen.getByLabelText("Create a World"), "The Lantern Coast");
    await user.click(screen.getByRole("button", { name: "Create World" }));
    expect(await screen.findByRole("heading", { name: "The Lantern Coast" })).toBeTruthy();
    expect(screen.getByText("Saved in this browser")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Edit World title" }));
    const title = screen.getByLabelText("World title");
    await user.clear(title);
    await user.type(title, "The Ember Coast");
    expect(screen.getByText("Unsaved title change")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Save title" }));
    expect(await screen.findByRole("heading", { name: "The Ember Coast" })).toBeTruthy();
    expect(screen.getByText("Saved in this browser")).toBeTruthy();
    const listed = await repository.listWorlds();
    expect(listed.status).toBe("found");
    if (listed.status === "found") expect(listed.records[0].localRevision).toBe(1);

    unmount();
    renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /The Ember Coast/ }));
    expect(await screen.findByRole("heading", { name: "The Ember Coast" })).toBeTruthy();
  });

  it("exports the current World and preserves bundled sidecar attachments after a title edit", async () => {
    const user = userEvent.setup();
    const sharedStore = new InMemoryLocalWorldStore();
    const store = new InMemoryLocalWorldRepository({ store: sharedStore });
    const restoredRecord = createPackageTestRecord();
    restoredRecord.snapshot.title = "Before Export";
    const path = "documents/story/source.txt";
    const data: LocalWorldPackageData = {
      localWorldId: restoredRecord.snapshot.worldId,
      documents: [{ id: "doc:source", status: "bundled", path, mediaType: "text/plain", locator: null }],
      assets: [],
      bundledMembers: { [path]: Array.from(packageFixtureAttachmentBytes.document) },
      fidelity: { localRecord: "preserved", sourceMetadata: "not-represented-by-local-record", profileMetadata: "not-represented-by-local-record" },
      creatorProfileAssumptions: { creator: "not-recorded", profile: "not-recorded" },
    };
    expect((await store.restorePackage(restoredRecord, data)).status).toBe("restored");
    // This instance reads the restored local record and its supplemental package data.
    const repo = new InMemoryLocalWorldRepository({ store: sharedStore });
    const createObjectURL = vi.fn(() => "blob:test");
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL, revokeObjectURL: vi.fn() }));
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    renderSurface(repo);
    await user.click(await screen.findByRole("button", { name: /Before Export/ }));
    await user.click(screen.getByRole("button", { name: "Edit World title" }));
    await user.clear(screen.getByLabelText("World title"));
    await user.type(screen.getByLabelText("World title"), "After Export");
    await user.click(screen.getByRole("button", { name: "Save title" }));
    await screen.findByRole("heading", { name: "After Export" });
    await user.click(screen.getByText("Save menu"));
    await user.click(screen.getByRole("button", { name: "Download World package" }));
    await waitFor(() => expect(createObjectURL).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("Package downloaded. It includes the current local World and its stored attachments.")).toBeTruthy();
    const sidecar = await repo.readPackageData(restoredRecord.snapshot.worldId);
    expect(sidecar.status).toBe("found");
    if (sidecar.status === "found") {
      expect(sidecar.data.documents).toEqual(data.documents);
      expect(Array.from(sidecar.data.bundledMembers[path])).toEqual(Array.from(packageFixtureAttachmentBytes.document));
    }
  });

  it("keeps a stale title as an explicit conflict candidate and offers a deliberate retry", async () => {
    const user = userEvent.setup();
    const repository = new InMemoryLocalWorldRepository();
    const created = await repository.createWorld({ title: "Conflict World" });
    expect(created.status).toBe("created");
    if (created.status !== "created") return;
    renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /Conflict World/ }));
    await user.click(screen.getByRole("button", { name: "Edit World title" }));
    await user.clear(screen.getByLabelText("World title"));
    await user.type(screen.getByLabelText("World title"), "My losing title");
    await repository.commitSemanticEdit({
      worldId: created.record.snapshot.worldId,
      expectedLocalRevision: created.record.localRevision,
      nextSnapshot: { ...created.record.snapshot, title: "Other tab title" },
      edit: { classification: "buddy-local-only", description: "Renamed in another tab" },
    });
    await user.click(screen.getByRole("button", { name: "Save title" }));
    expect(await screen.findByText("Conflict needs your choice")).toBeTruthy();
    expect(screen.getByText(/Your title is kept as a conflict candidate/)).toBeTruthy();
    expect((await repository.readConflictCandidates(created.record.snapshot.worldId)).status).toBe("found");
    await user.click(screen.getByRole("button", { name: "Save my title on the current version" }));
    expect(await screen.findByRole("heading", { name: "My losing title" })).toBeTruthy();
  });

  it("shows storage open and write failures without claiming a saved World", async () => {
    const openFailure = render(<AgentInteractionProvider><LocalWorldSurface openRepository={async () => ({ status: "error", message: "Browser storage is unavailable." })} /></AgentInteractionProvider>);
    expect(await screen.findByRole("alert")).toHaveTextContent("Browser storage is unavailable.");
    expect(screen.queryByText("Saved in this browser")).toBeNull();
    openFailure.unmount();

    const failed = new InMemoryLocalWorldRepository({ beforeCommit: (point) => { if (point === "create") throw new Error("Quota exceeded."); } });
    renderSurface(failed);
    await userEvent.setup().type(await screen.findByLabelText("Create a World"), "No false save");
    await userEvent.setup().click(screen.getByRole("button", { name: "Create World" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Quota exceeded.");
    expect(screen.queryByText("Saved in this browser")).toBeNull();
  });

  it("retains a failed title as an unsaved draft and only reports saved after an explicit retry commits", async () => {
    let failNextEdit = false;
    const repository = new InMemoryLocalWorldRepository({ beforeCommit: (point) => {
      if (point === "semantic-edit" && failNextEdit) {
        failNextEdit = false;
        throw new Error("Local transaction aborted.");
      }
    } });
    const created = await repository.createWorld({ title: "Committed title" });
    expect(created.status).toBe("created");
    if (created.status !== "created") return;

    const user = userEvent.setup();
    renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /Committed title/ }));
    await user.click(screen.getByRole("button", { name: "Edit World title" }));
    const input = screen.getByLabelText("World title");
    await user.clear(input);
    await user.type(input, "Proposed title");
    failNextEdit = true;
    await user.click(screen.getByRole("button", { name: "Save title" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Local transaction aborted.");
    expect(screen.getByText("Could not complete this local action")).toBeTruthy();
    expect(screen.getByLabelText("World title")).toHaveValue("Proposed title");
    expect(screen.queryByText("Saved in this browser")).toBeNull();
    const unchanged = await repository.readWorld(created.record.snapshot.worldId);
    expect(unchanged.status).toBe("found");
    if (unchanged.status === "found") expect(unchanged.record.snapshot.title).toBe("Committed title");

    await user.click(screen.getByRole("button", { name: "Save title" }));
    expect(await screen.findByRole("heading", { name: "Proposed title" })).toBeTruthy();
    expect(screen.getByText("Saved in this browser")).toBeTruthy();
  });

  it("keeps an unsaved title draft when creating or selecting another World and after a route-style remount", async () => {
    const repository = new InMemoryLocalWorldRepository();
    const first = await repository.createWorld({ title: "First World" });
    const second = await repository.createWorld({ title: "Second World" });
    expect(first.status).toBe("created");
    expect(second.status).toBe("created");
    if (first.status !== "created" || second.status !== "created") return;
    const user = userEvent.setup();
    const view = renderSurface(repository);

    await user.click(await screen.findByRole("button", { name: /First World/ }));
    await user.click(screen.getByRole("button", { name: "Edit World title" }));
    await user.clear(screen.getByLabelText("World title"));
    await user.type(screen.getByLabelText("World title"), "Uncommitted First World");
    expect(beforeUnloadIsPrevented()).toBe(true);

    await user.click(await screen.findByRole("button", { name: /Second World/ }));
    expect(await screen.findByRole("heading", { name: "Second World" })).toBeTruthy();
    expect(beforeUnloadIsPrevented()).toBe(true);
    await user.type(await screen.findByLabelText("Create a World"), "Third World");
    await user.click(screen.getByRole("button", { name: "Create World" }));
    expect(await screen.findByRole("heading", { name: "Third World" })).toBeTruthy();
    expect(beforeUnloadIsPrevented()).toBe(true);
    await user.click(screen.getByRole("button", { name: /First World/ }));
    expect(screen.getByLabelText("World title")).toHaveValue("Uncommitted First World");
    expect(screen.getByText("Unsaved title change")).toBeTruthy();

    view.unmount(); // Models an in-app route transition/Back remount in the same tab.
    expect(beforeUnloadIsPrevented()).toBe(true);
    renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /First World/ }));
    expect(screen.getByLabelText("World title")).toHaveValue("Uncommitted First World");
    expect(screen.getByText("Unsaved title change")).toBeTruthy();
    const unchanged = await repository.readWorld(first.record.snapshot.worldId);
    expect(unchanged.status).toBe("found");
    if (unchanged.status === "found") expect(unchanged.record.snapshot.title).toBe("First World");
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(beforeUnloadIsPrevented()).toBe(false);
  });

  it("keeps unload protection through an unmounted title write failure until the draft is resolved", async () => {
    let release!: () => void;
    let started!: () => void;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    const writeStarted = new Promise<void>((resolve) => { started = resolve; });
    let shouldFail = true;
    const repository = new InMemoryLocalWorldRepository({ beforeCommit: async (point) => {
      if (point !== "semantic-edit") return;
      started();
      await gate;
      if (shouldFail) throw new Error("Injected pending write failure.");
    } });
    const created = await repository.createWorld({ title: "Pending failure World" });
    expect(created.status).toBe("created");
    if (created.status !== "created") return;
    const user = userEvent.setup();
    const view = renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /Pending failure World/ }));
    await user.click(screen.getByRole("button", { name: "Edit World title" }));
    await user.clear(screen.getByLabelText("World title"));
    await user.type(screen.getByLabelText("World title"), "Kept after failure");
    await user.click(screen.getByRole("button", { name: "Save title" }));
    await writeStarted;
    view.unmount();
    expect(beforeUnloadIsPrevented()).toBe(true);

    await act(async () => {
      release();
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });
    expect(beforeUnloadIsPrevented()).toBe(true);
    shouldFail = false;
    renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /Pending failure World/ }));
    expect(screen.getByLabelText("World title")).toHaveValue("Kept after failure");
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(beforeUnloadIsPrevented()).toBe(false);
  });

  it("keeps unload protection until a pending title write commits after route unmount", async () => {
    let release!: () => void;
    let started!: () => void;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    const writeStarted = new Promise<void>((resolve) => { started = resolve; });
    const repository = new InMemoryLocalWorldRepository({ beforeCommit: async (point) => {
      if (point === "semantic-edit") { started(); await gate; }
    } });
    const created = await repository.createWorld({ title: "Pending success World" });
    expect(created.status).toBe("created");
    if (created.status !== "created") return;
    const user = userEvent.setup();
    const view = renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /Pending success World/ }));
    await user.click(screen.getByRole("button", { name: "Edit World title" }));
    await user.clear(screen.getByLabelText("World title"));
    await user.type(screen.getByLabelText("World title"), "Committed after unmount");
    await user.click(screen.getByRole("button", { name: "Save title" }));
    await writeStarted;
    view.unmount();
    expect(beforeUnloadIsPrevented()).toBe(true);

    await act(async () => {
      release();
      await waitFor(async () => {
        const result = await repository.readWorld(created.record.snapshot.worldId);
        expect(result.status === "found" && result.record.snapshot.title).toBe("Committed after unmount");
      });
    });
    await waitFor(() => expect(beforeUnloadIsPrevented()).toBe(false));
  });

  it("disables duplicate creates while the first durable operation is pending", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    const repository = new InMemoryLocalWorldRepository({ beforeCommit: async (point) => { if (point === "create") await gate; } });
    const user = userEvent.setup();
    renderSurface(repository);
    await user.type(await screen.findByLabelText("Create a World"), "One World");
    const create = screen.getByRole("button", { name: "Create World" });
    await user.click(create);
    expect(create).toBeDisabled();
    release();
    expect(await screen.findByRole("heading", { name: "One World" })).toBeTruthy();
    const worlds = await repository.listWorlds();
    expect(worlds.status === "found" && worlds.records).toHaveLength(1);
  });


  it("keeps same-name Worlds as distinct local identities", async () => {
    const user = userEvent.setup();
    const repository = new InMemoryLocalWorldRepository();
    renderSurface(repository);
    await user.type(await screen.findByLabelText("Create a World"), "Twin Lanterns");
    await user.click(screen.getByRole("button", { name: "Create World" }));
    await user.type(await screen.findByLabelText("Create a World"), "Twin Lanterns");
    await user.click(screen.getByRole("button", { name: "Create World" }));
    const listed = await repository.listWorlds();
    expect(listed.status).toBe("found");
    if (listed.status !== "found") return;
    expect(listed.records).toHaveLength(2);
    expect(new Set(listed.records.map((item) => item.snapshot.worldId)).size).toBe(2);
    expect(screen.getAllByRole("button", { name: /Twin Lanterns/ })).toHaveLength(2);
  });

  it("saves from the keyboard and lets Escape cancel the next title draft", async () => {
    const user = userEvent.setup();
    const repository = new InMemoryLocalWorldRepository();
    renderSurface(repository);
    await user.type(await screen.findByLabelText("Create a World"), "Keyboard World");
    await user.click(screen.getByRole("button", { name: "Create World" }));
    await user.click(await screen.findByRole("button", { name: "Edit World title" }));
    const input = screen.getByLabelText("World title");
    await user.clear(input);
    await user.type(input, "Keyboard Saved");
    await user.keyboard("{Enter}");
    expect(await screen.findByRole("heading", { name: "Keyboard Saved" })).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Edit World title" }));
    await user.clear(screen.getByLabelText("World title"));
    await user.type(screen.getByLabelText("World title"), "Abandoned draft");
    await user.keyboard("{Escape}");
    expect(await screen.findByRole("heading", { name: "Keyboard Saved" })).toBeTruthy();
    expect(screen.getByText("Saved in this browser")).toBeTruthy();
  });

  it("does not duplicate a pending rename, and a committed rename resumes after unmount", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    const repository = new InMemoryLocalWorldRepository({ beforeCommit: async (point) => { if (point === "semantic-edit") await gate; } });
    const created = await repository.createWorld({ title: "Before Navigation" });
    expect(created.status).toBe("created");
    if (created.status !== "created") return;
    const spy = vi.spyOn(repository, "commitSemanticEdit");
    const user = userEvent.setup();
    const view = renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /Before Navigation/ }));
    await user.click(screen.getByRole("button", { name: "Edit World title" }));
    await user.clear(screen.getByLabelText("World title"));
    await user.type(screen.getByLabelText("World title"), "After Navigation");
    await user.click(screen.getByRole("button", { name: "Save title" }));
    expect(await screen.findByText("Saving to this browser…")).toBeTruthy();
    expect(screen.getAllByRole("button", { name: "Saving…" }).every((button) => (button as HTMLButtonElement).disabled)).toBe(true);
    expect(spy).toHaveBeenCalledTimes(1);
    view.unmount(); // models route departure/reload while the captured write is pending
    release();
    await spy.mock.results[0].value;

    renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /After Navigation/ }));
    expect(await screen.findByRole("heading", { name: "After Navigation" })).toBeTruthy();
    expect(screen.getByText("Saved in this browser")).toBeTruthy();
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("leaves repository state unchanged when an opened World disappears before resume", async () => {
    const repository = new InMemoryLocalWorldRepository();
    const created = await repository.createWorld({ title: "Removed World" });
    expect(created.status).toBe("created");
    if (created.status !== "created") return;
    const wrapper = renderSurface(repository);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /Removed World/ }));
    expect(await screen.findByRole("heading", { name: "Removed World" })).toBeTruthy();
    wrapper.unmount();
    expect((await repository.listWorlds()).status).toBe("found");
  });
});
