import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { StrictMode } from "react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { InMemoryLocalWorldRepository } from "../inMemoryLocalWorldRepository";
import { createTestWorld, sequenceLocalIds } from "../localWorldContractFixtures";
import type { CommitSemanticResult, LocalWorldRecord, LocalWorldRelationship, WriteLayoutResult } from "../localWorldRepository";
import { createLocalWorldGraphAdapter } from "./localWorldGraphAdapter";
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
    vi.spyOn(graph, "getBoundingClientRect").mockReturnValue({ width: 1456, height: 1048, x: 0, y: 0, top: 0, right: 1456, bottom: 1048, left: 0, toJSON: () => ({}) });
    fireEvent(mara, new MouseEvent("pointerdown", { button: 0, clientX: 100, clientY: 100, bubbles: true }));
    fireEvent(graph, new MouseEvent("pointermove", { clientX: 140, clientY: 125, bubbles: true }));
    fireEvent(graph, new MouseEvent("pointerup", { clientX: 140, clientY: 125, bubbles: true }));
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
