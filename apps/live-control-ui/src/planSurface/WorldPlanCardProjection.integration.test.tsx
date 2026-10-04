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
import { PlanSurfacePage } from "./PlanSurfacePage";
import {
  buildWorldPlanCardProjectionModel,
  WorldPlanCardProjection,
  worldPlanCardTargetKeys,
} from "./components/WorldPlanCardProjection";

type GenerateHtml = typeof import("@tiptap/core").generateHTML;
const { generateHtmlMock, originalGenerateHtml } = vi.hoisted(() => ({
  generateHtmlMock: vi.fn<GenerateHtml>(),
  originalGenerateHtml: { current: null as GenerateHtml | null },
}));
vi.mock("@tiptap/core", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tiptap/core")>();
  originalGenerateHtml.current = actual.generateHTML;
  generateHtmlMock.mockImplementation((...args) => originalGenerateHtml.current!(...args));
  return { ...actual, generateHTML: generateHtmlMock };
});

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
const initialDigest = "a".repeat(64);
const committedDigest = "b".repeat(64);

function visitJsonNodes(node: JSONContent, visitor: (node: JSONContent) => void) {
  visitor(node);
  for (const child of node.content ?? []) visitJsonNodes(child, visitor);
}

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
  vi.restoreAllMocks();
  generateHtmlMock.mockImplementation((...args) => originalGenerateHtml.current!(...args));
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

  const cards = screen.getByTestId("world-plan-cards");
  const scene = cards.querySelector('[data-element-id="scene:arrival"]');
  expect(scene).not.toBeNull();
  const askButton = scene!.querySelector<HTMLButtonElement>('button[data-target-id="scene:arrival"]');
  const editButton = scene!.querySelector<HTMLButtonElement>('button[data-edit-target-id="scene:arrival"]');
  expect(askButton).not.toBeNull();
  expect(editButton).not.toBeNull();
  expect(askButton).toBeEnabled();
  expect(editButton).toBeEnabled();
  fireEvent.click(editButton!);
  expect(selectForEdit).toHaveBeenCalledWith({ kind: "scene", id: "scene:arrival" });
  expect(selectForAsk).not.toHaveBeenCalled();
  fireEvent.click(askButton!);
  expect(selectForAsk).toHaveBeenCalledWith({ kind: "scene", id: "scene:arrival" });
  expect(selectForEdit).toHaveBeenCalledTimes(1);
});

it("serializes authored Plan content inertly, escapes reference labels, and fails closed on media", () => {
  const markdown = [
    "<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->",
    "## Arrival [Warehouse](dmb-node:node:warehouse)",
    "First paragraph with **bold** and _emphasis_, plus [Captain](#dmb-ref:npc:captain).",
    "",
    "Second paragraph.",
    "",
    "- First item",
    "  - Nested item",
    "",
    "> [!GM-NOTE]",
    "> Keep the gate pressure visible.",
    "",
    "[Warehouse](dmb-node:node:warehouse)",
  ].join("\n");
  const imported = markdownToTiptapDoc(markdown);
  expect(imported.diagnostics).toEqual([]);
  const documentWithMarkupLikeLabel = JSON.parse(JSON.stringify(imported.doc)) as JSONContent;
  visitJsonNodes(documentWithMarkupLikeLabel, (node) => {
    if (node.type === "graphNodeReference" && node.attrs?.nodeId === "node:warehouse") {
      node.attrs = { ...node.attrs, label: '<img src=x onerror="alert(1)">' };
    }
  });
  const originalDocument = JSON.stringify(documentWithMarkupLikeLabel);
  const fetchSpy = vi.spyOn(globalThis, "fetch");
  const importedModel = buildWorldPlanCardProjectionModel({
    document: documentWithMarkupLikeLabel,
    markdown,
    sourceWarnings: [],
  });
  expect(importedModel.status).toBe("ready");
  if (importedModel.status !== "ready") return;
  const scene = importedModel.roots[0]!;
  const mounted = render(
    <WorldPlanCardProjection
      worldId={worldId}
      documentId={documentId}
      document={documentWithMarkupLikeLabel}
      markdown={markdown}
      sourceWarnings={[]}
      basis={{ status: "verified", revision: 4, contentSha256: committedDigest }}
      isDirty={false}
      onReturnToDocument={vi.fn()}
    />,
  );

  const card = screen.getByTestId(`world-plan-card-content-scene-${scene.id}`);
  const article = screen.getByTestId(`world-plan-card-title-scene-${scene.id}`).closest("article")!;
  expect(screen.getByTestId(`world-plan-card-title-scene-${scene.id}`).querySelector("h3"))
    .toHaveTextContent('<img src=x onerror="alert(1)">');
  expect(card.querySelectorAll("p").length).toBeGreaterThanOrEqual(3);
  expect(card.querySelector("strong")).toHaveTextContent("bold");
  expect(card.querySelector("em")).toHaveTextContent("emphasis");
  expect(card.querySelector("ul ul")).toHaveTextContent("Nested item");
  expect(card.querySelector('[data-md-callout="gm-note"]')).toHaveTextContent("Keep the gate pressure visible.");
  expect(article.querySelectorAll('[data-graph-node-id="node:warehouse"]')).toHaveLength(2);
  expect(card.querySelector('[data-md-ref-id="captain"]')).toHaveTextContent("Captain");
  expect(article.querySelector("img")).toBeNull();
  expect(article.querySelector(".ProseMirror, [contenteditable='true'], [data-node-view-wrapper]")).toBeNull();
  const graphReference = article.querySelector<HTMLElement>('[data-plan-card-reference="graph"]')!;
  expect(graphReference.tagName).toBe("SPAN");
  expect(graphReference.closest("a, button")).toBeNull();
  fireEvent.mouseEnter(graphReference);
  fireEvent.click(graphReference);
  expect(fetchSpy).not.toHaveBeenCalled();
  expect(JSON.stringify(documentWithMarkupLikeLabel)).toBe(originalDocument);

  mounted.unmount();

  const mediaDocument = JSON.parse(JSON.stringify(imported.doc)) as JSONContent;
  let insertedMedia = false;
  visitJsonNodes(mediaDocument, (node) => {
    if (!insertedMedia && node.type === "paragraph") {
      node.content = [
        ...(node.content ?? []),
        { type: "image", attrs: { src: "javascript:alert(1)", alt: "unsafe" } },
      ];
      insertedMedia = true;
    }
  });
  const mediaRender = render(
    <WorldPlanCardProjection
      worldId={worldId}
      documentId={documentId}
      document={mediaDocument}
      markdown={markdown}
      sourceWarnings={[]}
      basis={{ status: "verified", revision: 4, contentSha256: committedDigest }}
      isDirty={false}
      onReturnToDocument={vi.fn()}
    />,
  );
  expect(screen.getByTestId("world-plan-card-content-unavailable-scene-scene:arrival")).toHaveTextContent(
    "This card contains content Cards cannot display safely.",
  );
  expect(screen.queryByRole("img")).toBeNull();
  expect(fetchSpy).not.toHaveBeenCalled();
  mediaRender.unmount();

  const unsafeLinkDocument = JSON.parse(JSON.stringify(imported.doc)) as JSONContent;
  let markedUnsafeLink = false;
  visitJsonNodes(unsafeLinkDocument, (node) => {
    if (!markedUnsafeLink && node.type === "text" && node.text === "First paragraph with ") {
      node.marks = [...(node.marks ?? []), { type: "link", attrs: { href: "javascript:alert(1)" } }];
      markedUnsafeLink = true;
    }
  });
  expect(markedUnsafeLink).toBe(true);
  const unsafeLinkRender = render(
    <WorldPlanCardProjection
      worldId={worldId}
      documentId={documentId}
      document={unsafeLinkDocument}
      markdown={markdown}
      sourceWarnings={[]}
      basis={{ status: "verified", revision: 4, contentSha256: committedDigest }}
      isDirty={false}
      onReturnToDocument={vi.fn()}
    />,
  );
  expect(screen.getByTestId("world-plan-card-content-unavailable-scene-scene:arrival")).toBeInTheDocument();
  expect(document.querySelector('a[href^="javascript:"]')).toBeNull();
  expect(fetchSpy).not.toHaveBeenCalled();
  unsafeLinkRender.unmount();
});

it("reuses static card HTML for equivalent documents and unrelated selection renders", () => {
  const markdown = [
    "<!-- dmb-playable-element:v1 kind=scene id=scene:stable -->",
    "## Stable scene",
    "Original body.",
  ].join("\n");
  const imported = markdownToTiptapDoc(markdown);
  expect(imported.diagnostics).toEqual([]);
  generateHtmlMock.mockClear();
  const props = {
    worldId,
    documentId,
    markdown,
    sourceWarnings: [] as string[],
    basis: { status: "verified" as const, revision: 4, contentSha256: committedDigest },
    isDirty: false,
    onReturnToDocument: vi.fn(),
  };
  const mounted = render(<WorldPlanCardProjection {...props} document={imported.doc} />);
  expect(generateHtmlMock).toHaveBeenCalledTimes(2);

  const equivalentDocument = JSON.parse(JSON.stringify(imported.doc)) as JSONContent;
  mounted.rerender(
    <WorldPlanCardProjection
      {...props}
      document={equivalentDocument}
      selectedTarget={{ kind: "scene", id: "scene:stable" }}
    />,
  );
  expect(generateHtmlMock).toHaveBeenCalledTimes(2);

  const changedMarkdown = markdown.replace("Original body.", "Updated body.");
  const changedDocument = JSON.parse(JSON.stringify(equivalentDocument)) as JSONContent;
  visitJsonNodes(changedDocument, (node) => {
    if (node.type === "text" && node.text === "Original body.") node.text = "Updated body.";
  });
  mounted.rerender(
    <WorldPlanCardProjection
      {...props}
      markdown={changedMarkdown}
      document={changedDocument}
      selectedTarget={{ kind: "scene", id: "scene:stable" }}
    />,
  );
  expect(generateHtmlMock).toHaveBeenCalledTimes(4);
  expect(screen.getByText("Updated body.")).toBeInTheDocument();
});

it("renders a representative 20-card synthetic Plan projection", () => {
  const markdown = Array.from({ length: 20 }, (_, index) => [
    `<!-- dmb-playable-element:v1 kind=scene id=scene:synthetic-${index + 1} -->`,
    `## Synthetic scene ${index + 1}`,
    `A representative paragraph for scene ${index + 1}.`,
  ].join("\n")).join("\n");
  const imported = markdownToTiptapDoc(markdown);
  expect(imported.diagnostics).toEqual([]);
  const startedAt = performance.now();
  const mounted = render(
    <WorldPlanCardProjection
      worldId={worldId}
      documentId={documentId}
      document={imported.doc}
      markdown={markdown}
      sourceWarnings={[]}
      basis={{ status: "verified", revision: 4, contentSha256: committedDigest }}
      isDirty={false}
      onReturnToDocument={vi.fn()}
    />,
  );
  const elapsedMs = performance.now() - startedAt;
  expect(screen.getAllByTestId(/^world-plan-card-content-scene-scene:synthetic-/)).toHaveLength(20);
  expect(document.querySelectorAll(".ProseMirror, [data-node-view-wrapper]")).toHaveLength(0);
  console.info(`Synthetic Plan projection: 20 cards mounted in ${elapsedMs.toFixed(1)} ms (jsdom).`);
  mounted.unmount();
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
  expect(screen.getByTestId("world-plan-cards")).toBeInTheDocument();
  expect(within(screen.getByTestId("world-plan-cards")).getByText("Scene overview.")).toBeInTheDocument();
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
  expect(screen.getByText("Draft / unsaved")).toBeInTheDocument();
  expect(within(screen.getByTestId("world-plan-cards")).getByText("Scene overview revised.")).toBeInTheDocument();
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
  const editHost = await screen.findByTestId("surface-edit-host");
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
  expect(screen.getByText("Saved Plan")).toBeInTheDocument();
  fireEvent.click(screen.getByText("Plan basis details"));
  expect(screen.getByText("6", { selector: "dd" })).toBeInTheDocument();
  expect(screen.getByText(committedDigest)).toBeInTheDocument();
  expect(within(screen.getByTestId("world-plan-cards")).getByText("Scene overview revised.")).toBeInTheDocument();
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
  const cards = screen.getByTestId("world-plan-cards");
  expect(within(cards).getByText("Server draft / uncommitted")).toBeInTheDocument();
  expect(cards).toHaveTextContent("Uncommitted server draft");
  expect(within(cards).getAllByText("Unavailable")).toHaveLength(2);
  expect(within(cards).getByText("Persisted server draft prose.")).toBeInTheDocument();
  expect(within(cards).queryByText("Saved Plan")).not.toBeInTheDocument();

  const editHost = await screen.findByTestId("surface-edit-host");
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
  const reopenedCards = screen.getByTestId("world-plan-cards");
  expect(within(reopenedCards).getByText("Saved Plan")).toBeInTheDocument();
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
  expect(within(cards).queryByText("Saved Plan")).not.toBeInTheDocument();
  fireEvent.click(within(cards).getByText("Plan basis details"));
  expect(within(cards).getByText("Basis", { selector: "dt" }).nextElementSibling).toHaveTextContent("Unavailable");
  expect(within(cards).getByText("Revision", { selector: "dt" }).nextElementSibling).toHaveTextContent("Unavailable");
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
  const cards = screen.getByTestId("world-plan-cards");
  expect(within(cards).getByText("Draft / unsaved")).toBeInTheDocument();
  expect(within(cards).getByText("The queue is moving.")).toBeInTheDocument();
  expect(cards).toHaveTextContent("Associated scene: scene:gate-line");
  expect(cards).toHaveTextContent("Authored activates: scene:gate-line");
  expect(cards).toHaveTextContent("Authored suppresses: beat:panic-breaks");
  expect(apis.prepare).not.toHaveBeenCalled();
  expect(apis.commit).not.toHaveBeenCalled();

  const editHost = await screen.findByTestId("surface-edit-host");
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
  const reopenedCards = screen.getByTestId("world-plan-cards");
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
  const cards = screen.getByTestId("world-plan-cards");
  const detailsSummary = within(cards).getByText("Plan basis details");
  fireEvent.click(detailsSummary);
  expect(within(cards).getByText(initialDigest)).toBeInTheDocument();

  const editHost = await screen.findByTestId("surface-edit-host");
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
  expect(within(screen.getByTestId("world-plan-cards")).getByText("Scene overview.")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: secondDocumentId } });
  await waitFor(() => expect(screen.getByLabelText("Plan document")).toHaveValue(secondDocumentId));
  await waitFor(() => expect(screen.queryByTestId("world-plan-cards")).not.toBeInTheDocument());
  expect(within(screen.getByTestId("world-plan-document-view")).getByText("Second document prose.")).toBeInTheDocument();
  fireEvent.click(within(page).getByRole("button", { name: "Cards" }));
  expect(within(screen.getByTestId("world-plan-cards")).getByText("Second document prose.")).toBeInTheDocument();
  expect(within(screen.getByTestId("world-plan-cards")).queryByText("Scene overview.")).not.toBeInTheDocument();

  mounted.unmount();
  window.history.replaceState({}, "", `/plan?world=${secondWorldId}&documentId=${thirdDocumentId}`);
  renderPlan(secondWorldId);
  const otherWorldPage = await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(within(otherWorldPage).getByRole("button", { name: "Cards" })).toBeEnabled());
  expect(screen.queryByTestId("world-plan-cards")).not.toBeInTheDocument();
  expect(within(screen.getByTestId("world-plan-document-view")).getByText("Other World prose.")).toBeInTheDocument();
  fireEvent.click(within(otherWorldPage).getByRole("button", { name: "Cards" }));
  const otherWorldCards = screen.getByTestId("world-plan-cards");
  expect(within(otherWorldCards).getByText("Other World prose.")).toBeInTheDocument();
  fireEvent.click(within(otherWorldCards).getByText("Plan basis details"));
  expect(within(otherWorldCards).getByText(secondWorldId)).toBeInTheDocument();
  expect(within(otherWorldCards).getByText(thirdDocumentId)).toBeInTheDocument();
  expect(within(otherWorldCards).getByText("21", { selector: "dd" })).toBeInTheDocument();
});
