import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { JSONContent } from "@tiptap/core";

import * as liveApi from "../api/liveApi";
import type { WorldOwnedPlanRecordV2 } from "../api/types";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { SelectedWorldProvider } from "../selectedWorld/SelectedWorldContext";
import { SurfaceContextProvider } from "../surfaceInteraction/contextHost";
import { PeekRegionProvider } from "../surfaceInteraction/peekHost";
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import { slicePlayableBodies } from "../playSurface/runbook/nativeRunbookProjection";
import { PlanSurfacePage } from "./PlanSurfacePage";
import {
  buildWorldPlanCardProjectionModel,
  WorldPlanCardProjection,
  worldPlanCardTargetKeys,
} from "./components/WorldPlanCardProjection";

vi.mock("./components/WorldPlanAgentConversation", () => ({
  WorldPlanAgentConversation: () => null,
}));

const worldId = "card-projection-world";
const secondWorldId = "card-projection-world-b";
const documentId = "saved-card-plan";
const secondDocumentId = "saved-card-plan-b";
const thirdDocumentId = "saved-card-plan-c";
const initialMarkdown = [
  "<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->",
  "## Arrival",
  "Scene overview.",
  "<!-- dmb-playable-element:v1 kind=beat id=beat:gate -->",
  "### The gate",
  "The guard is waiting.",
  "<!-- dmb-playable-element:v1 kind=choice id=choice:route -->",
  "### Choose a route",
  "Two paths are open.",
  "<!-- dmb-playable-element:v1 kind=option id=option:run -->",
  "#### Run through the gate",
  "Move quickly.",
].join("\n") + "\n";
const initialV2Markdown = [
  "<!-- dmb-playable-element:v2 kind=beat id=beat:hold-the-gate beat_kind=spine -->",
  "## Hold the gate",
  "Beat overview.",
  "",
  "Talk to [Caelynn](#dmb-ref:npc:caelynn).",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:gate-line -->",
  "### Gate line",
  "The queue is waiting.",
  "<!-- dmb-playable-element:v2 kind=choice id=choice:gate-response scene=scene:gate-line -->",
  "### What do you do?",
  "The guard asks for a decision.",
  "<!-- dmb-playable-element:v2 kind=option id=option:open-gate activates=scene:gate-line suppresses=beat:panic-breaks -->",
  "- Open the gate",
  "  Consult [Gate procedure](#dmb-ref:citation:gate-procedure).",
  "<!-- dmb-playable-element:v2 kind=beat id=beat:panic-breaks beat_kind=optional -->",
  "## Panic breaks",
  "The line starts to move.",
].join("\n") + "\n";
const readerFidelityV2Markdown = [
  "<!-- dmb-playable-element:v2 kind=beat id=beat:gate-call beat_kind=spine -->",
  "## Hold the gate",
  "The objective is to keep the gate open.",
  "",
  "Pressure: rain is filling the lower street.",
  "",
  "Role: the scout handles the signal.",
  "",
  "The bell rings twice before the courier arrives.",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:gate-call -->",
  "### Arrival at [North Gate](dmb-node:loc_north_gate)",
  "The wet stones shine beneath the wall.",
  "",
  "A **brass** bell hangs beside the gate.",
  "",
  "Speak with [Caelynn](dmb-node:pc_caelynn) and review [Gate procedure](#dmb-ref:citation:gate-procedure).",
  "",
  "- Inspect the north hinge",
  "  - Ask the keeper for the iron key",
  "",
  "1. Sound the bell",
  "2. Raise the lantern",
  "   - Keep the shutter closed",
  "",
  "## General Runbook direction",
  "Do not show this ordinary section in Cards.",
].join("\n") + "\n";
const initialDigest = "a".repeat(64);

function returnToCardOutline() {
  const reader = screen.queryByTestId("world-plan-scene-reader");
  if (reader) fireEvent.click(within(reader).getByRole("button", { name: "Back to outline" }));
  return screen.getByTestId("world-plan-cards");
}
const committedDigest = "b".repeat(64);
let originalScrollIntoViewDescriptor: PropertyDescriptor | undefined;
let scrollIntoViewWasPatched = false;

const record: WorldOwnedPlanRecordV2 = {
  schema_version: "dmb_world_owned_plan_record_v2",
  scope_mode: "world",
  document_id: documentId,
  title: "Arrival Plan",
  campaign_id: null,
  world_id: worldId,
  target_session: null,
  kind: "plan",
  target_relpath: `out/workspace/plan/${documentId}.md`,
  status: "active",
  content_status: "committed",
  revision: 4,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderPlan(selectedWorldId = worldId) {
  return render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${selectedWorldId}`}>
      <AgentInteractionProvider>
        <SurfaceContextProvider>
          <PeekRegionProvider><PlanSurfacePage /></PeekRegionProvider>
        </SurfaceContextProvider>
      </AgentInteractionProvider>
    </SelectedWorldProvider>,
  );
}

async function openPlanEditHost() {
  const editHost = await screen.findByTestId("surface-edit-host");
  const editToggle = within(editHost).queryByRole("button", { name: "Edit" });
  if (editToggle) fireEvent.click(editToggle);
  return editHost;
}

type FixtureContentStatus = WorldOwnedPlanRecordV2["content_status"] | "unknown";

function installApiMocks(
  initialSource = initialMarkdown,
  initialContentStatus: FixtureContentStatus = "committed",
) {
  let savedMarkdown = initialSource;
  let savedRevision = 4;
  let savedDigest = initialDigest;
  let savedContentStatus = initialContentStatus;
  const listWorlds = vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [{
      schema_version: "dmb_world_container_record_v1",
      world_id: worldId,
      name: "Card Projection World",
      source_root_relpath: "corpus/card-projection-world",
      created_at: "2026-01-01T00:00:00Z",
    }],
  });
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockResolvedValue({
    schema_version: "dmb_managed_world_plan_context_v2",
    scope_mode: "world",
    world_id: worldId,
    campaign_id: null,
    session: null,
    authoritative: false,
    generated_at: "2026-01-01T00:00:00Z",
    derived_from: ["managed_world_container"],
    timeline: [],
  });
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockImplementation(async () => ({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [{ ...record, content_status: savedContentStatus as WorldOwnedPlanRecordV2["content_status"], revision: savedRevision }],
  }));
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockImplementation(async () => ({
    schema_version: "dmb_workspace_document_snapshot_v2",
    record: { ...record, content_status: savedContentStatus as WorldOwnedPlanRecordV2["content_status"], revision: savedRevision },
    markdown: savedMarkdown,
    content_sha256: savedDigest,
    file_fingerprint: "postgres",
    file_exists: true,
    loaded_revision: savedRevision,
  }));
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockImplementation(async (request) => ({
    schema_version: "dmb_tiptap_markdown_write_prepare_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: documentId,
    title: request.title,
    target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!,
    registry_revision: savedRevision + 1,
    file_exists: true,
    writer_ok: true,
    writer_confirm_token: "card-projection-prepared",
    warnings: [],
    diagnostics: [],
  }));
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockImplementation(async (request) => {
    savedMarkdown = request.markdown;
    savedRevision = request.expected_revision + 1;
    savedDigest = committedDigest;
    savedContentStatus = "committed";
    return {
      schema_version: "dmb_tiptap_markdown_write_commit_v2",
      scope_mode: "world",
      world_id: worldId,
      document_id: documentId,
      title: record.title,
      target_relpath: record.target_relpath!,
      target_display_path: record.target_relpath!,
      registry_revision: savedRevision,
      committed_revision: savedRevision,
      committed_record: { ...record, content_status: "committed", revision: savedRevision },
      normalized_content_sha256: committedDigest,
      writer_ok: true,
      writer_phase: "commit",
      diagnostics: [],
    };
  });
  return { listWorlds, prepare, commit, readServer: () => ({ savedMarkdown, savedRevision, savedDigest }) };
}

afterEach(() => {
  if (scrollIntoViewWasPatched) {
    if (originalScrollIntoViewDescriptor) {
      Object.defineProperty(HTMLElement.prototype, "scrollIntoView", originalScrollIntoViewDescriptor);
    } else {
      Reflect.deleteProperty(HTMLElement.prototype, "scrollIntoView");
    }
    originalScrollIntoViewDescriptor = undefined;
    scrollIntoViewWasPatched = false;
  }
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  localStorage.clear();
  window.history.replaceState({}, "", "/");
});

it("makes duplicate marker identities unavailable to target selection", () => {
  const duplicateMarkdown = `${initialMarkdown}\n<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->\n## Arrival again\nA duplicate scene.\n`;
  const imported = markdownToTiptapDoc(duplicateMarkdown);
  const model = buildWorldPlanCardProjectionModel({
    document: imported.doc,
    markdown: duplicateMarkdown,
    sourceWarnings: [],
  });

  expect(model.status).toBe("blocked");
  expect(worldPlanCardTargetKeys(model)).toEqual(new Set());
});

it("preserves authored blocks and renders inert references with a compact Beat disclosure", async () => {
  const imported = markdownToTiptapDoc(readerFidelityV2Markdown);
  expect(imported.diagnostics).toEqual([]);
  const slices = slicePlayableBodies(imported.doc);
  const beat = slices.get("beat:gate-call");
  const scene = slices.get("scene:gate-call");
  expect(beat).toBeDefined();
  expect(scene).toBeDefined();
  expect(scene?.titleContent).toContainEqual({
    type: "graphNodeReference",
    attrs: { nodeId: "loc_north_gate", label: "North Gate" },
  });
  expect(scene?.bodyContent.map((node) => node.type)).toEqual([
    "paragraph",
    "paragraph",
    "paragraph",
    "bulletList",
    "orderedList",
  ]);
  expect(scene?.bodyContent[2]?.content).toContainEqual({
    type: "graphNodeReference",
    attrs: { nodeId: "pc_caelynn", label: "Caelynn" },
  });
  expect(scene?.bodyContent[2]?.content).toContainEqual({
    type: "runbookReference",
    attrs: { kind: "ref", refType: "citation", refId: "gate-procedure", label: "Gate procedure" },
  });
  expect(JSON.stringify(scene?.bodyContent)).not.toContain("Do not show this ordinary section");

  const apis = installApiMocks(readerFidelityV2Markdown);
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  renderPlan();
  const page = await screen.findByTestId("world-owned-plan");
  const cardsButton = within(page).getByRole("button", { name: "Cards" });
  await waitFor(() => expect(cardsButton).toBeEnabled());
  fireEvent.click(cardsButton);

  const cards = returnToCardOutline();
  const sceneCard = cards.querySelector<HTMLElement>('[data-element-id="scene:gate-call"]');
  expect(sceneCard).not.toBeNull();
  const title = sceneCard?.querySelector(".world-plan-card__title");
  expect(title?.querySelector("h3")).toHaveTextContent("Arrival at North Gate");
  expect(title?.querySelector('[data-plan-card-reference="graph"][data-graph-node-id="loc_north_gate"]')?.tagName).toBe("BUTTON");

  const body = sceneCard?.querySelector<HTMLElement>(".world-plan-card__content");
  expect(body).not.toBeNull();
  expect(Array.from(body!.children).map((element) => element.tagName)).toEqual([
    "P",
    "P",
    "P",
    "UL",
    "OL",
  ]);
  expect(body?.querySelector("strong")).toHaveTextContent("brass");
  expect(body?.querySelector("ul > li > ul")).not.toBeNull();
  expect(body?.querySelector("ol > li > ul")).not.toBeNull();
  const graphPill = body?.querySelector('[data-plan-card-reference="graph"][data-graph-node-id="pc_caelynn"]');
  expect(graphPill?.tagName).toBe("BUTTON");
  expect(graphPill).toHaveAttribute("data-graph-node-activation", "enabled");
  expect(graphPill).toHaveTextContent("Caelynn");
  expect(body?.querySelector('[data-md-ref-id="gate-procedure"]')).toHaveTextContent("Gate procedure");
  expect(body?.querySelector("script")).toBeNull();
  expect(cards).not.toHaveTextContent("Do not show this ordinary section in Cards.");

  fireEvent.click(within(sceneCard!).getByRole("button", { name: /Read scene:/ }));
  const reader = screen.getByTestId("world-plan-scene-reader");
  expect(reader.querySelector(".world-plan-scene-reader__title h2")).toHaveTextContent("Arrival at North Gate");
  const context = reader.querySelector<HTMLElement>('[aria-label="Authored Beat context"]');
  expect(context).not.toBeNull();
  expect(context?.querySelector(".world-plan-scene-reader__context-title h3")).toHaveTextContent("Hold the gate");
  const objective = context?.querySelector(".world-plan-scene-reader__objective");
  expect(objective).toHaveTextContent("The objective is to keep the gate open.");
  expect(objective).not.toHaveTextContent("Pressure:");
  const details = context?.querySelector("details");
  expect(details).not.toHaveAttribute("open");
  const summary = context?.querySelector("summary");
  expect(summary?.tagName).toBe("SUMMARY");
  expect(summary).toHaveTextContent("Beat details");
  fireEvent.click(summary!);
  expect(details).toHaveAttribute("open");
  expect(details).toHaveTextContent("Pressure: rain is filling the lower street.");
  expect(details).toHaveTextContent("Role: the scout handles the signal.");
  expect(details).toHaveTextContent("The bell rings twice before the courier arrives.");
  expect(apis.prepare).not.toHaveBeenCalled();
  expect(apis.commit).not.toHaveBeenCalled();
});

it("opts into exact Graph reference activation in Cards without changing authored content", () => {
  const onActivateGraphNode = vi.fn();
  const imported = markdownToTiptapDoc(readerFidelityV2Markdown);
  render(
    <WorldPlanCardProjection
      worldId={worldId}
      documentId={documentId}
      document={imported.doc}
      markdown={readerFidelityV2Markdown}
      sourceWarnings={[]}
      basis={{ status: "verified", revision: 4, contentSha256: initialDigest }}
      isDirty={false}
      onReturnToDocument={vi.fn()}
      onActivateGraphNode={onActivateGraphNode}
    />,
  );

  const cards = screen.getByTestId("world-plan-cards");
  const reference = within(cards).getByRole("button", { name: "Caelynn" });
  expect(reference).toHaveAttribute("data-graph-node-id", "pc_caelynn");
  fireEvent.click(reference);

  expect(onActivateGraphNode).toHaveBeenCalledTimes(1);
  expect(onActivateGraphNode).toHaveBeenCalledWith("pc_caelynn", reference);
  expect(cards).toHaveTextContent("Speak with Caelynn and review Gate procedure.");
});

it("escapes markup-like reference labels and mounts no editor or reference NodeView in Cards", () => {
  const imported = markdownToTiptapDoc(readerFidelityV2Markdown);
  const escapedDoc = JSON.parse(JSON.stringify(imported.doc)) as JSONContent;
  const markupLabel = "<img src=x onerror=alert(1)>";
  const replaceReferenceLabels = (node: JSONContent) => {
    if (node.type === "graphNodeReference") {
      node.attrs = { ...node.attrs, label: markupLabel };
    }
    node.content?.forEach(replaceReferenceLabels);
  };
  escapedDoc.content?.forEach(replaceReferenceLabels);

  render(
    <WorldPlanCardProjection
      worldId={worldId}
      documentId={documentId}
      document={escapedDoc}
      markdown={readerFidelityV2Markdown}
      sourceWarnings={[]}
      basis={{ status: "verified", revision: 4, contentSha256: initialDigest }}
      isDirty={false}
      onReturnToDocument={vi.fn()}
    />,
  );

  const cards = screen.getByTestId("world-plan-cards");
  const graphPills = cards.querySelectorAll<HTMLElement>('[data-plan-card-reference="graph"]');
  expect(graphPills.length).toBe(2);
  for (const pill of graphPills) {
    expect(pill.textContent).toBe(markupLabel);
    expect(pill.innerHTML).toContain("&lt;img");
    expect(pill.querySelector("img")).toBeNull();
  }
  expect(cards.querySelectorAll(".ProseMirror, [data-node-view-wrapper], .react-renderer")).toHaveLength(0);
  expect(cards.querySelectorAll("button[data-graph-node-id]")).toHaveLength(0);
});

it("shows unsafe authored links as unavailable instead of serializing them", () => {
  const imported = markdownToTiptapDoc(readerFidelityV2Markdown);
  const unsafeDoc = JSON.parse(JSON.stringify(imported.doc)) as JSONContent;
  let changed = false;
  const injectUnsafeLink = (node: JSONContent) => {
    if (!changed && node.type === "text" && node.text === "The wet stones shine beneath the wall.") {
      node.marks = [{ type: "link", attrs: { href: "javascript:alert(1)" } }];
      changed = true;
    }
    node.content?.forEach(injectUnsafeLink);
  };
  unsafeDoc.content?.forEach(injectUnsafeLink);
  expect(changed).toBe(true);

  render(
    <WorldPlanCardProjection
      worldId={worldId}
      documentId={documentId}
      document={unsafeDoc}
      markdown={readerFidelityV2Markdown}
      sourceWarnings={[]}
      basis={{ status: "verified", revision: 4, contentSha256: initialDigest }}
      isDirty={false}
      onReturnToDocument={vi.fn()}
    />,
  );

  const cards = screen.getByTestId("world-plan-cards");
  const sceneCard = cards.querySelector('[data-element-id="scene:gate-call"]');
  expect(sceneCard).toHaveTextContent("cannot be displayed safely in Cards");
  expect(sceneCard?.querySelector('a[href^="javascript:"]')).toBeNull();
});

it("clears focused Scene and Ask context when the verified Plan basis changes", async () => {
  const imported = markdownToTiptapDoc(initialMarkdown);
  const model = buildWorldPlanCardProjectionModel({ document: imported.doc, markdown: initialMarkdown, sourceWarnings: [] });
  expect(model.status).toBe("ready");
  const targetKeys = worldPlanCardTargetKeys(model);
  const onSelectTarget = vi.fn();
  const props = {
    worldId,
    document: imported.doc,
    markdown: initialMarkdown,
    sourceWarnings: [] as string[],
    isDirty: false,
    onReturnToDocument: vi.fn(),
    selectableTargetKeys: targetKeys,
    editableTargetKeys: targetKeys,
    selectedTarget: { kind: "scene" as const, id: "scene:arrival" },
    onSelectTarget,
  };
  const mounted = render(
    <WorldPlanCardProjection {...props} documentId={documentId} basis={{ status: "verified", revision: 4, contentSha256: initialDigest }} />,
  );

  expect(screen.getByTestId("world-plan-scene-reader")).toBeInTheDocument();
  expect(onSelectTarget).toHaveBeenLastCalledWith({ kind: "scene", id: "scene:arrival" });

  mounted.rerender(
    <WorldPlanCardProjection {...props} documentId={documentId} basis={{ status: "verified", revision: 5, contentSha256: committedDigest }} />,
  );
  await waitFor(() => expect(screen.queryByTestId("world-plan-scene-reader")).not.toBeInTheDocument());
  expect(onSelectTarget).toHaveBeenLastCalledWith(null);
});

it("keeps current-draft Edit selection separate from committed-Plan Ask selection", () => {
  const imported = markdownToTiptapDoc(initialMarkdown);
  const model = buildWorldPlanCardProjectionModel({
    document: imported.doc,
    markdown: initialMarkdown,
    sourceWarnings: [],
  });
  expect(model.status).toBe("ready");
  const targetKeys = worldPlanCardTargetKeys(model);
  const selectForAsk = vi.fn();
  const selectForEdit = vi.fn();
  const scrollTo = vi.fn();
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));
  vi.stubGlobal("scrollY", 100);
  vi.stubGlobal("scrollTo", scrollTo);
  render(
    <WorldPlanCardProjection
      worldId={worldId}
      documentId={documentId}
      document={imported.doc}
      markdown={initialMarkdown}
      sourceWarnings={[]}
      basis={{ status: "verified", revision: 4, contentSha256: committedDigest }}
      isDirty
      onReturnToDocument={vi.fn()}
      selectableTargetKeys={targetKeys}
      editableTargetKeys={targetKeys}
      onSelectTarget={selectForAsk}
      onSelectEditTarget={selectForEdit}
    />,
  );

  expect(screen.getByTestId("world-plan-scene-reader")).toBeInTheDocument();
  expect(selectForAsk).toHaveBeenLastCalledWith({ kind: "scene", id: "scene:arrival" });
  fireEvent.click(within(screen.getByTestId("world-plan-scene-reader")).getByRole("button", { name: "Back to outline" }));
  selectForAsk.mockClear();

  const cards = screen.getByTestId("world-plan-cards");
  const scene = cards.querySelector('[data-element-id="scene:arrival"]');
  expect(scene).not.toBeNull();
  const askButton = scene!.querySelector<HTMLButtonElement>('button[data-target-id="scene:arrival"]');
  const editButton = scene!.querySelector<HTMLButtonElement>('button[data-edit-target-id="scene:arrival"]');
  const editCard = scene!.querySelector<HTMLElement>(".world-plan-card");
  expect(askButton).not.toBeNull();
  expect(editButton).not.toBeNull();
  expect(editCard).not.toBeNull();
  expect(askButton).toBeEnabled();
  expect(editButton).toBeEnabled();
  vi.spyOn(editCard!, "getBoundingClientRect").mockReturnValue({ top: 260 } as DOMRect);
  fireEvent.click(editButton!);
  expect(selectForEdit).toHaveBeenCalledWith({ kind: "scene", id: "scene:arrival" });
  expect(scrollTo).toHaveBeenCalledWith({ top: 348, behavior: "auto" });
  expect(selectForAsk).not.toHaveBeenCalled();
  fireEvent.click(askButton!);
  expect(selectForAsk).toHaveBeenCalledWith({ kind: "scene", id: "scene:arrival" });
  expect(selectForEdit).toHaveBeenCalledTimes(1);
});

it("scrolls the focused Scene heading into view on open and Plan-order navigation", () => {
  const markdown = [
    "<!-- dmb-playable-element:v2 kind=beat id=beat:main beat_kind=spine -->",
    "## Main beat",
    "Beat overview and location notes.",
    "<!-- dmb-playable-element:v2 kind=scene id=scene:gate -->",
    "### The gate",
    "The guard waits beside the north gate.",
    "<!-- dmb-playable-element:v2 kind=choice id=choice:gate scene=scene:gate -->",
    "### How do you enter?",
    "The guard asks for a response.",
    "<!-- dmb-playable-element:v2 kind=option id=option:talk -->",
    "- Talk to the guard",
    "  Explain your reason for entering.",
    "<!-- dmb-playable-element:v2 kind=scene id=scene:warehouse -->",
    "### The warehouse",
    "A lantern moves behind the loading door.",
  ].join("\n") + "\n";
  const imported = markdownToTiptapDoc(markdown);
  const model = buildWorldPlanCardProjectionModel({ document: imported.doc, markdown, sourceWarnings: [] });
  expect(model.status).toBe("ready");
  const scrollIntoView = vi.fn();
  originalScrollIntoViewDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollIntoView");
  scrollIntoViewWasPatched = true;
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
    configurable: true,
    value: scrollIntoView,
  });
  const targetKeys = worldPlanCardTargetKeys(model);
  const onSelectTarget = vi.fn();
  render(
    <WorldPlanCardProjection
      worldId={worldId}
      documentId={documentId}
      document={imported.doc}
      markdown={markdown}
      sourceWarnings={[]}
      basis={{ status: "verified", revision: 9, contentSha256: committedDigest }}
      isDirty={false}
      onReturnToDocument={vi.fn()}
      selectableTargetKeys={targetKeys}
      editableTargetKeys={targetKeys}
      onSelectTarget={onSelectTarget}
    />,
  );

  const reader = screen.getByTestId("world-plan-scene-reader");
  expect(reader.querySelector(".world-plan-scene-reader__title h2")).toHaveTextContent("The gate");
  const readerHeading = reader.querySelector(".world-plan-scene-reader__heading");
  expect(scrollIntoView).toHaveBeenCalledWith({ block: "start" });
  expect(scrollIntoView.mock.contexts[0]).toBe(readerHeading);
  expect(reader).toHaveTextContent("The guard waits beside the north gate.");
  expect(reader).toHaveTextContent("Beat overview and location notes.");
  expect(reader).toHaveTextContent("How do you enter?");
  expect(reader).toHaveTextContent("Talk to the guard");
  expect(reader).toHaveTextContent("Explain your reason for entering.");
  expect(reader.querySelector('[data-element-id="scene:warehouse"]')).toBeNull();
  expect(onSelectTarget).toHaveBeenLastCalledWith({ kind: "scene", id: "scene:gate" });

  fireEvent.click(within(reader).getByRole("button", { name: "Next scene" }));
  const warehouseReader = screen.getByTestId("world-plan-scene-reader");
  expect(scrollIntoView.mock.contexts[1]).toBe(warehouseReader.querySelector(".world-plan-scene-reader__heading"));
  expect(warehouseReader).toHaveTextContent("A lantern moves behind the loading door.");
  expect(warehouseReader.querySelector('[data-element-id="scene:gate"]')).toBeNull();
  expect(onSelectTarget).toHaveBeenLastCalledWith({ kind: "scene", id: "scene:warehouse" });

  fireEvent.click(within(warehouseReader).getByRole("button", { name: "Previous scene" }));
  const gateReader = screen.getByTestId("world-plan-scene-reader");
  expect(gateReader.querySelector(".world-plan-scene-reader__title h2")).toHaveTextContent("The gate");
  expect(scrollIntoView.mock.contexts[2]).toBe(gateReader.querySelector(".world-plan-scene-reader__heading"));
  fireEvent.click(within(screen.getByTestId("world-plan-scene-reader")).getByRole("button", { name: "Back to outline" }));
  expect(screen.queryByTestId("world-plan-scene-reader")).not.toBeInTheDocument();
  expect(screen.getByTestId("world-plan-cards")).toBeInTheDocument();
});

it("clears an earlier Ask target when a focused Scene is outside the verified saved selection", () => {
  const imported = markdownToTiptapDoc(initialMarkdown);
  const model = buildWorldPlanCardProjectionModel({ document: imported.doc, markdown: initialMarkdown, sourceWarnings: [] });
  expect(model.status).toBe("ready");
  const onSelectTarget = vi.fn();
  render(
    <WorldPlanCardProjection
      worldId={worldId}
      documentId={documentId}
      document={imported.doc}
      markdown={initialMarkdown}
      sourceWarnings={[]}
      basis={{ status: "verified", revision: 4, contentSha256: committedDigest }}
      isDirty
      onReturnToDocument={vi.fn()}
      selectableTargetKeys={new Set()}
      onSelectTarget={onSelectTarget}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Open scene: Arrival" }));
  expect(onSelectTarget).toHaveBeenLastCalledWith(null);
  expect(screen.getByTestId("world-plan-scene-reader")).toHaveTextContent("default Ask card target is cleared");
});

it("keeps one editor draft through Cards, ordinary Save, and fresh reopen at the exact committed revision", async () => {
  const apis = installApiMocks();
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  const mounted = renderPlan();

  const page = await screen.findByTestId("world-owned-plan");
  const cardsButton = await within(page).findByRole("button", { name: "Cards" });
  await waitFor(() => expect(cardsButton).toBeEnabled());
  expect(apis.listWorlds).toHaveBeenCalled();
  expect(apis.prepare).not.toHaveBeenCalled();
  expect(apis.commit).not.toHaveBeenCalled();

  const editorElement = screen.getByTestId("world-owned-plan-markdown-editor").querySelector(".ProseMirror");
  expect(editorElement).not.toBeNull();
  fireEvent.click(cardsButton);
  const cards = returnToCardOutline();
  expect(cards).toBeInTheDocument();
  expect(within(cards).getByText("Scene overview.")).toBeInTheDocument();
  expect(screen.getByTestId("world-owned-plan-markdown-editor").querySelector(".ProseMirror")).toBe(editorElement);
  // Return through the explicit Document view control while retaining the same editor node.
  fireEvent.click(within(page).getByRole("button", { name: "Document" }));
  const sceneBody = within(screen.getByTestId("world-owned-plan-markdown-editor")).getByText("Scene overview.");
  sceneBody.textContent = "Scene overview revised.";
  fireEvent.input(sceneBody);
  await waitFor(() => expect(within(screen.getByTestId("world-plan-document-view")).getByText("Scene overview revised.")).toBeInTheDocument());
  expect(apis.prepare).not.toHaveBeenCalled();
  expect(apis.commit).not.toHaveBeenCalled();

  fireEvent.click(within(page).getByRole("button", { name: "Cards" }));
  const editedCards = returnToCardOutline();
  expect(screen.getByText("Draft / unsaved")).toBeInTheDocument();
  expect(within(editedCards).getByText("Scene overview revised.")).toBeInTheDocument();
  expect(screen.getByTestId("world-owned-plan-markdown-editor").querySelector(".ProseMirror")).toBe(editorElement);
  expect(apis.prepare).not.toHaveBeenCalled();
  expect(apis.commit).not.toHaveBeenCalled();

  const editedProse = within(screen.getByTestId("world-plan-document-view")).getByText("Scene overview revised.");
  const selectionTextNode = editedProse.firstChild!;
  const selection = window.getSelection()!;
  const range = document.createRange();
  range.setStart(selectionTextNode, 5);
  range.collapse(true);
  selection.removeAllRanges();
  selection.addRange(range);
  fireEvent.click(within(page).getByRole("button", { name: "Cards" }));
  fireEvent.click(within(page).getByRole("button", { name: "Document" }));
  expect(selection.anchorNode).toBe(selectionTextNode);
  expect(selection.anchorOffset).toBe(5);
  expect(screen.getByTestId("world-owned-plan-markdown-editor").querySelector(".ProseMirror")).toBe(editorElement);
  const editHost = await openPlanEditHost();
  const saveButton = await within(editHost).findByRole("button", { name: "Save Plan" });
  await waitFor(() => expect(saveButton).toBeEnabled());
  fireEvent.click(saveButton);
  await screen.findByText("Saved to this World.");

  expect(apis.prepare).toHaveBeenCalledTimes(1);
  expect(apis.prepare.mock.calls[0]?.[0]).toMatchObject({
    world_id: worldId,
    document_id: documentId,
    expected_revision: 4,
  });
  expect(apis.commit).toHaveBeenCalledTimes(1);
  const committedMarkdown = apis.commit.mock.calls[0]?.[0].markdown ?? "";
  expect(committedMarkdown).toContain("Scene overview revised.");
  expect(committedMarkdown).toContain("<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->");
  expect(committedMarkdown).toContain("<!-- dmb-playable-element:v1 kind=option id=option:run -->");
  const markerIds = [...committedMarkdown.matchAll(/dmb-playable-element:v1 kind=[a-z]+ id=([a-z]+:[a-z0-9._-]+)/g)]
    .map((match) => match[1]);
  expect(markerIds).toEqual(["scene:arrival", "beat:gate", "choice:route", "option:run"]);
  expect(apis.readServer()).toMatchObject({ savedRevision: 6, savedDigest: committedDigest });

  mounted.unmount();
  localStorage.removeItem(`dmb:world-plan-local-draft:v2:${worldId}`);
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  renderPlan();
  const reopenedPage = await screen.findByTestId("world-owned-plan");
  const reopenedCardsButton = within(reopenedPage).getByRole("button", { name: "Cards" });
  await waitFor(() => expect(reopenedCardsButton).toBeEnabled());
  fireEvent.click(reopenedCardsButton);
  const reopenedOutline = returnToCardOutline();
  expect(screen.getByText("Saved snapshot verified")).toBeInTheDocument();
  fireEvent.click(within(reopenedOutline).getByText("Plan basis details"));
  expect(screen.getByText("6", { selector: "dd" })).toBeInTheDocument();
  expect(screen.getByText(committedDigest)).toBeInTheDocument();
  expect(within(reopenedOutline).getByText("Scene overview revised.")).toBeInTheDocument();
  expect(screen.getByTestId("world-owned-plan-markdown-editor").querySelector(".ProseMirror")).not.toBe(editorElement);
  expect(apis.commit).toHaveBeenCalledTimes(1);
});

it("keeps a persisted server draft uncommitted until ordinary Save and fresh reopen", async () => {
  const serverDraftMarkdown = initialMarkdown.replace("Scene overview.", "Persisted server draft prose.");
  const apis = installApiMocks(serverDraftMarkdown, "draft");
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  const mounted = renderPlan();
  const page = await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(within(page).getByRole("button", { name: "Cards" })).toBeEnabled());
  expect(within(screen.getByTestId("world-plan-document-view")).getByText("Persisted server draft prose.")).toBeInTheDocument();
  expect(apis.prepare).not.toHaveBeenCalled();
  expect(apis.commit).not.toHaveBeenCalled();

  fireEvent.click(within(page).getByRole("button", { name: "Cards" }));
  const cards = returnToCardOutline();
  expect(within(cards).getByText("Server draft / uncommitted")).toBeInTheDocument();
  expect(cards).toHaveTextContent("Uncommitted server draft");
  expect(within(cards).getAllByText("Unavailable")).toHaveLength(2);
  expect(within(cards).getByText("Persisted server draft prose.")).toBeInTheDocument();
  expect(within(cards).queryByText("Saved snapshot verified")).not.toBeInTheDocument();

  const editHost = await openPlanEditHost();
  const saveButton = await within(editHost).findByRole("button", { name: "Save Plan" });
  await waitFor(() => expect(saveButton).toBeEnabled());
  fireEvent.click(saveButton);
  await screen.findByText("Saved to this World.");
  expect(apis.prepare).toHaveBeenCalledTimes(1);
  expect(apis.commit).toHaveBeenCalledTimes(1);
  expect(apis.commit.mock.calls[0]?.[0].markdown).toContain("Persisted server draft prose.");

  mounted.unmount();
  localStorage.removeItem(`dmb:world-plan-local-draft:v2:${worldId}`);
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  renderPlan();
  const reopenedPage = await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(within(reopenedPage).getByRole("button", { name: "Cards" })).toBeEnabled());
  fireEvent.click(within(reopenedPage).getByRole("button", { name: "Cards" }));
  const reopenedCards = returnToCardOutline();
  expect(within(reopenedCards).getByText("Saved snapshot verified")).toBeInTheDocument();
  fireEvent.click(within(reopenedCards).getByText("Plan basis details"));
  expect(within(reopenedCards).getByText("Committed snapshot")).toBeInTheDocument();
  expect(within(reopenedCards).getByText("6", { selector: "dd" })).toBeInTheDocument();
  expect(within(reopenedCards).getByText(committedDigest)).toBeInTheDocument();
  expect(apis.commit).toHaveBeenCalledTimes(1);
});

it("keeps the card basis unavailable when the loaded snapshot status is unknown", async () => {
  const apis = installApiMocks(initialMarkdown, "unknown");
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  renderPlan();
  const page = await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(within(page).getByRole("button", { name: "Cards" })).toBeEnabled());
  fireEvent.click(within(page).getByRole("button", { name: "Cards" }));

  const cards = screen.getByTestId("world-plan-cards");
  expect(within(cards).getByText("Saved basis unavailable")).toBeInTheDocument();
  expect(within(cards).queryByText("Saved snapshot verified")).not.toBeInTheDocument();
  fireEvent.click(within(cards).getByText("Plan basis details"));
  expect(within(cards).getByText("Basis", { selector: "dt" }).nextElementSibling).toHaveTextContent("Unavailable");
  expect(within(cards).getByText("Object revision", { selector: "dt" }).nextElementSibling).toHaveTextContent("Unavailable");
  expect(within(cards).getByText("Content SHA-256", { selector: "dt" }).nextElementSibling).toHaveTextContent("Unavailable");
  expect(apis.prepare).not.toHaveBeenCalled();
  expect(apis.commit).not.toHaveBeenCalled();
});

it("round-trips the mounted v2 writer boundary from Document edit through Cards, Save, and fresh reopen", async () => {
  const apis = installApiMocks(initialV2Markdown);
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  const mounted = renderPlan();
  const page = await screen.findByTestId("world-owned-plan");
  const cardsButton = within(page).getByRole("button", { name: "Cards" });
  await waitFor(() => expect(cardsButton).toBeEnabled());

  const sceneBody = within(screen.getByTestId("world-owned-plan-markdown-editor")).getByText("The queue is waiting.");
  sceneBody.textContent = "The queue is moving.";
  fireEvent.input(sceneBody);
  await waitFor(() => expect(within(screen.getByTestId("world-plan-document-view")).getByText("The queue is moving.")).toBeInTheDocument());
  expect(apis.prepare).not.toHaveBeenCalled();
  expect(apis.commit).not.toHaveBeenCalled();

  fireEvent.click(cardsButton);
  const cards = returnToCardOutline();
  expect(within(cards).getByText("Draft / unsaved")).toBeInTheDocument();
  expect(within(cards).getByText("The queue is moving.")).toBeInTheDocument();
  expect(cards).toHaveTextContent("Associated scene: scene:gate-line");
  expect(cards).toHaveTextContent("Authored activates: scene:gate-line");
  expect(cards).toHaveTextContent("Authored suppresses: beat:panic-breaks");
  expect(apis.prepare).not.toHaveBeenCalled();
  expect(apis.commit).not.toHaveBeenCalled();

  const editHost = await openPlanEditHost();
  const saveButton = await within(editHost).findByRole("button", { name: "Save Plan" });
  await waitFor(() => expect(saveButton).toBeEnabled());
  fireEvent.click(saveButton);
  await screen.findByText("Saved to this World.");

  expect(apis.prepare).toHaveBeenCalledTimes(1);
  expect(apis.commit).toHaveBeenCalledTimes(1);
  expect(apis.prepare.mock.calls[0]?.[0]).toMatchObject({
    world_id: worldId,
    document_id: documentId,
    expected_revision: 4,
  });
  const committedMarkdown = apis.commit.mock.calls[0]?.[0].markdown ?? "";
  expect(committedMarkdown).toContain("The queue is moving.");
  expect(committedMarkdown).toContain("[Caelynn](#dmb-ref:npc:caelynn)");
  expect(committedMarkdown).toContain("[Gate procedure](#dmb-ref:citation:gate-procedure)");
  const markerIdentityOrder = [...committedMarkdown.matchAll(/<!-- dmb-playable-element:v2 kind=([a-z]+) id=([a-z0-9._:-]+)/g)]
    .map((match) => `${match[1]}:${match[2]}`);
  expect(markerIdentityOrder).toEqual([
    "beat:beat:hold-the-gate",
    "scene:scene:gate-line",
    "choice:choice:gate-response",
    "option:option:open-gate",
    "beat:beat:panic-breaks",
  ]);
  expect(committedMarkdown).toContain("kind=choice id=choice:gate-response scene=scene:gate-line");
  expect(committedMarkdown).toContain("kind=option id=option:open-gate activates=scene:gate-line suppresses=beat:panic-breaks");
  expect(apis.readServer()).toMatchObject({ savedRevision: 6, savedDigest: committedDigest });

  mounted.unmount();
  localStorage.removeItem(`dmb:world-plan-local-draft:v2:${worldId}`);
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  renderPlan();
  const reopenedPage = await screen.findByTestId("world-owned-plan");
  const reopenedCardsButton = within(reopenedPage).getByRole("button", { name: "Cards" });
  await waitFor(() => expect(reopenedCardsButton).toBeEnabled());
  fireEvent.click(reopenedCardsButton);
  const reopenedCards = returnToCardOutline();
  const reopenedRoots = reopenedCards.querySelector(":scope > .world-plan-card-roots")!;
  expect([...reopenedRoots.querySelectorAll(":scope > li")].map((node) => node.getAttribute("data-element-id")))
    .toEqual(["beat:hold-the-gate", "beat:panic-breaks"]);
  const childCardIds = (node: Element) => {
    const childList = [...node.children].find((child) => child.tagName === "OL");
    return childList ? [...childList.children].map((child) => child.getAttribute("data-element-id")) : [];
  };
  const holdTheGate = reopenedCards.querySelector('[data-element-id="beat:hold-the-gate"]')!;
  expect(childCardIds(holdTheGate)).toEqual(["scene:gate-line", "choice:gate-response"]);
  const reopenedChoice = reopenedCards.querySelector('[data-element-id="choice:gate-response"]')!;
  expect(reopenedChoice).toHaveTextContent("Associated scene: scene:gate-line");
  expect(childCardIds(reopenedChoice)).toEqual(["option:open-gate"]);
  const reopenedOption = reopenedCards.querySelector('[data-element-id="option:open-gate"]')!;
  expect(reopenedOption).toHaveTextContent("Authored activates: scene:gate-line");
  expect(reopenedOption).toHaveTextContent("Authored suppresses: beat:panic-breaks");
  expect(reopenedCards).toHaveTextContent("The queue is moving.");
  fireEvent.click(within(reopenedCards).getByText("Plan basis details"));
  expect(within(reopenedCards).getByText("6", { selector: "dd" })).toBeInTheDocument();
  expect(within(reopenedCards).getByText(committedDigest)).toBeInTheDocument();
  expect(apis.commit).toHaveBeenCalledTimes(1);
});

it("hides the saved basis while a commit is uncertain and preserves the draft without retrying", async () => {
  const apis = installApiMocks();
  let rejectCommit!: (reason: Error) => void;
  apis.commit.mockImplementationOnce(() => new Promise((_, reject) => { rejectCommit = reject; }));
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  renderPlan();
  const page = await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(within(page).getByRole("button", { name: "Cards" })).toBeEnabled());
  const editor = within(screen.getByTestId("world-owned-plan-markdown-editor"));
  const sceneBody = editor.getByText("Scene overview.");
  sceneBody.textContent = "Scene overview pending.";
  fireEvent.input(sceneBody);
  await waitFor(() => expect(within(screen.getByTestId("world-plan-document-view")).getByText("Scene overview pending.")).toBeInTheDocument());
  fireEvent.click(within(page).getByRole("button", { name: "Cards" }));
  const cards = returnToCardOutline();
  const detailsSummary = within(cards).getByText("Plan basis details");
  fireEvent.click(detailsSummary);
  expect(within(cards).getByText(initialDigest)).toBeInTheDocument();

  const editHost = await openPlanEditHost();
  fireEvent.click(within(editHost).getByRole("button", { name: "Save Plan" }));
  await waitFor(() => expect(apis.commit).toHaveBeenCalledTimes(1));
  expect(apis.prepare).toHaveBeenCalledTimes(1);
  expect(within(cards).getByText("Draft / unsaved")).toBeInTheDocument();
  expect(within(cards).getAllByText("Unavailable")).toHaveLength(3);

  fireEvent.click(within(page).getByRole("button", { name: "Document" }));
  fireEvent.click(within(page).getByRole("button", { name: "Cards" }));
  const pendingCards = screen.getByTestId("world-plan-cards");
  fireEvent.click(within(pendingCards).getByText("Plan basis details"));
  expect(within(pendingCards).getAllByText("Unavailable")).toHaveLength(3);
  expect(within(pendingCards).getByText("Scene overview pending.")).toBeInTheDocument();
  const localDraft = JSON.parse(localStorage.getItem(`dmb:world-plan-local-draft:v2:${worldId}`) ?? "null");
  expect(localDraft).toMatchObject({ pending_write: { phase: "commit", base_revision: 4, prepared_revision: 5 } });
  expect(localDraft.pending_write.markdown).toContain("Scene overview pending.");

  await act(async () => { rejectCommit(new Error("commit response failed")); });
  expect(await screen.findByText("commit response failed")).toBeInTheDocument();
  expect(within(screen.getByTestId("world-plan-cards")).getByText("Draft / unsaved")).toBeInTheDocument();
  expect(apis.prepare).toHaveBeenCalledTimes(1);
  expect(apis.commit).toHaveBeenCalledTimes(1);
});


it("invalidates the selected card projection when the saved document or World changes", async () => {
  const secondRecord: WorldOwnedPlanRecordV2 = {
    ...record,
    document_id: secondDocumentId,
    world_id: worldId,
    title: "Second Plan",
    revision: 12,
    target_relpath: `out/workspace/plan/${secondDocumentId}.md`,
  };
  const thirdRecord: WorldOwnedPlanRecordV2 = {
    ...record,
    document_id: thirdDocumentId,
    world_id: secondWorldId,
    title: "Other World Plan",
    revision: 21,
    target_relpath: `out/workspace/plan/${thirdDocumentId}.md`,
  };
  const records = [record, secondRecord, thirdRecord];
  const markdownByDocument = new Map([
    [documentId, initialMarkdown],
    [secondDocumentId, "<!-- dmb-playable-element:v1 kind=scene id=scene:second -->\n## Second scene\nSecond document prose.\n"],
    [thirdDocumentId, "<!-- dmb-playable-element:v1 kind=scene id=scene:other-world -->\n## Other World scene\nOther World prose.\n"],
  ]);
  const revisionByDocument = new Map([[documentId, 4], [secondDocumentId, 12], [thirdDocumentId, 21]]);
  const digestByDocument = new Map([[documentId, initialDigest], [secondDocumentId, "c".repeat(64)], [thirdDocumentId, "d".repeat(64)]]);

  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [worldId, secondWorldId].map((id) => ({
      schema_version: "dmb_world_container_record_v1" as const,
      world_id: id,
      name: id,
      source_root_relpath: `corpus/${id}`,
      created_at: "2026-01-01T00:00:00Z",
    })),
  });
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockImplementation(async (requestedWorldId) => ({
    schema_version: "dmb_managed_world_plan_context_v2",
    scope_mode: "world",
    world_id: requestedWorldId,
    campaign_id: null,
    session: null,
    authoritative: false,
    generated_at: "2026-01-01T00:00:00Z",
    derived_from: ["managed_world_container"],
    timeline: [],
  }));
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockImplementation(async (requestedWorldId) => ({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: requestedWorldId,
    records: records.filter((candidate) => candidate.world_id === requestedWorldId),
  }));
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockImplementation(async (requestedDocumentId) => {
    const selectedRecord = records.find((candidate) => candidate.document_id === requestedDocumentId)!;
    return {
      schema_version: "dmb_workspace_document_snapshot_v2",
      record: selectedRecord,
      markdown: markdownByDocument.get(requestedDocumentId)!,
      content_sha256: digestByDocument.get(requestedDocumentId)!,
      file_fingerprint: "postgres",
      file_exists: true,
      loaded_revision: revisionByDocument.get(requestedDocumentId)!,
    };
  });

  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  const mounted = renderPlan(worldId);
  const page = await screen.findByTestId("world-owned-plan");
  const cardsButton = within(page).getByRole("button", { name: "Cards" });
  await waitFor(() => expect(cardsButton).toBeEnabled());
  fireEvent.click(cardsButton);
  const initialCards = returnToCardOutline();
  expect(within(initialCards).getByText("Scene overview.")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: secondDocumentId } });
  await waitFor(() => expect(screen.getByLabelText("Plan document")).toHaveValue(secondDocumentId));
  await waitFor(() => expect(screen.queryByTestId("world-plan-cards")).not.toBeInTheDocument());
  expect(within(screen.getByTestId("world-plan-document-view")).getByText("Second document prose.")).toBeInTheDocument();
  fireEvent.click(within(page).getByRole("button", { name: "Cards" }));
  const secondReader = await screen.findByTestId("world-plan-scene-reader");
  expect(secondReader).toHaveTextContent("Second document prose.");
  expect(secondReader).not.toHaveTextContent("Scene overview.");
  expect(secondReader.querySelector('[data-element-id="scene:arrival"]')).toBeNull();

  mounted.unmount();
  window.history.replaceState({}, "", `/plan?world=${secondWorldId}&documentId=${thirdDocumentId}`);
  renderPlan(secondWorldId);
  const otherWorldPage = await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(within(otherWorldPage).getByRole("button", { name: "Cards" })).toBeEnabled());
  expect(screen.queryByTestId("world-plan-cards")).not.toBeInTheDocument();
  expect(within(screen.getByTestId("world-plan-document-view")).getByText("Other World prose.")).toBeInTheDocument();
  fireEvent.click(within(otherWorldPage).getByRole("button", { name: "Cards" }));
  expect(await screen.findByTestId("world-plan-scene-reader")).toHaveTextContent("Other World prose.");
  const otherWorldCards = returnToCardOutline();
  fireEvent.click(within(otherWorldCards).getByText("Plan basis details"));
  expect(within(otherWorldCards).getByText(secondWorldId)).toBeInTheDocument();
  expect(within(otherWorldCards).getByText(thirdDocumentId)).toBeInTheDocument();
  expect(within(otherWorldCards).getByText("21", { selector: "dd" })).toBeInTheDocument();
});
