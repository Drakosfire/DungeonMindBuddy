import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Editor, JSONContent } from "@tiptap/core";

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

vi.mock("./components/WorldPlanAgentConversation", () => ({
  WorldPlanAgentConversation: (props: Record<string, unknown>) => <output data-testid="agent-state">{JSON.stringify({
    worldId: props.worldId, documentId: props.documentId, revision: props.revision,
    target: props.playableTarget, basis: props.playableTargetBasis, stale: props.playableTargetStale,
    editTarget: props.playableEditTarget, dirty: props.savedDirty, saveInFlight: props.saveInFlight,
  })}</output>,
}));

const worldId = "card-projection-world";
const secondWorldId = "card-projection-world-b";
const documentId = "saved-card-plan";
const secondDocumentId = "saved-card-plan-b";
const thirdDocumentId = "saved-card-plan-c";
const initialMarkdown = [
  "<!-- dmb-playable-element:v2 kind=beat id=beat:gate beat_kind=spine -->",
  "## The gate",
  "The guard is waiting.",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:arrival -->",
  "### Arrival",
  "Scene overview.",
  "<!-- dmb-playable-element:v2 kind=choice id=choice:route scene=scene:arrival -->",
  "### Choose a route",
  "Two paths are open.",
  "<!-- dmb-playable-element:v2 kind=option id=option:run -->",
  "- Run through the gate",
  "Move quickly.",
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

const navigationMarkdown = [
  "<!-- dmb-playable-element:v2 kind=beat id=beat:road beat_kind=spine -->",
  "## North road",
  "Keep the lantern lit.",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:lantern -->",
  "### Lantern Gate",
  "> [!READ-ALOUD]",
  "> The lantern shines through the mist.",
  "",
  "Original lantern cue.",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:regent -->",
  "### Glass Regent",
  "Boss mechanics remain in full: " + "Legendary action; lair action. ".repeat(100),
  "<!-- dmb-playable-element:v2 kind=beat id=beat:harbor beat_kind=optional -->",
  "## Harbor arrival",
  "Watch the tide.",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:census -->",
  "### Harbor Census",
  "![Harbor map](dmb-media:ac6c15cc-8c68-4732-8ae2-d9f3f051393a \"dmb-image:v1 width=55 collapsed=true\")",
  "",
  "| Name | Duty |",
  "| --- | --- |",
  ...Array.from({ length: 18 }, (_, i) => `| Citizen ${i + 1} | Gate watch |`),
  "<!-- dmb-playable-element:v2 kind=choice id=choice:crossing scene=scene:census -->",
  "### Choose the crossing",
  "<!-- dmb-playable-element:v2 kind=option id=option:wait -->",
  "- Wait",
  "<!-- dmb-playable-element:v2 kind=option id=option:boat -->",
  "- Take the boat",
  "<!-- dmb-playable-element:v2 kind=option id=option:walk -->",
  "- Walk the boardwalk",
].join("\n") + "\n";


function agentState() { return JSON.parse(screen.getByTestId("agent-state").textContent ?? "{}"); }
function liveEditor() { return (screen.getByTestId("world-owned-plan-markdown-editor").querySelector(".ProseMirror") as HTMLElement & { editor: Editor }).editor; }
async function openCards() {
  const button = within(screen.getByRole("group", { name: "Plan view" })).getByRole("button", { name: "Cards", exact: true });
  await waitFor(() => expect(button).toBeEnabled()); fireEvent.click(button);
}
function documentView() { fireEvent.click(within(screen.getByRole("group", { name: "Plan view" })).getByRole("button", { name: "Document", exact: true })); }
async function savePlan() {
  const host = await openPlanEditHost(); const save = await within(host).findByRole("button", { name: "Save Plan" });
  await waitFor(() => expect(save).toBeEnabled()); fireEvent.click(save);
  await screen.findByText("Saved to this World.");
}
async function mountOwner(source = initialMarkdown, contentStatus: FixtureContentStatus = "committed") {
  const apis = installApiMocks(source, contentStatus);
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  const mounted = renderPlan(); await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(liveEditor()).toBeDefined());
  return { apis, mounted };
}
function renderReadonly(markdown = readerFidelityV2Markdown, sceneId = "scene:gate-call", extra: Partial<React.ComponentProps<typeof WorldPlanCardProjection>> = {}) {
  const imported = markdownToTiptapDoc(markdown);
  return render(<WorldPlanCardProjection worldId={worldId} documentId={documentId}
    document={imported.doc} markdown={markdown} sourceWarnings={[]} sceneId={sceneId}
    basis={{ status: "verified", revision: 4, contentSha256: initialDigest }} isDirty={false}
    onReturnToDocument={vi.fn()} {...extra} />);
}

it("makes duplicate current marker identities unavailable to card and Agent targets", () => {
  const source = initialMarkdown + "\n<!-- dmb-playable-element:v2 kind=scene id=scene:arrival -->\n### Duplicate\nBody.\n";
  const model = buildWorldPlanCardProjectionModel({ document: markdownToTiptapDoc(source).doc, markdown: source });
  expect(model.status).toBe("blocked"); expect(worldPlanCardTargetKeys(model).size).toBe(0);
  renderReadonly(source, "scene:arrival");
  expect(screen.getByRole("alert")).toBeInTheDocument(); expect(screen.queryByTestId("world-plan-scene-reader")).toBeNull();
});

it("preserves authored blocks and inert references with a compact Beat disclosure in the current readonly card", () => {
  renderReadonly(); const reader = screen.getByTestId("world-plan-scene-reader");
  const body = reader.querySelector(".shared-scene-card__body")!;
  expect([...body.children].map(e => e.tagName)).toEqual(["P", "P", "P", "UL", "OL"]);
  expect(body.querySelector("strong")).toHaveTextContent("brass");
  expect(body.querySelector("ul > li > ul")).not.toBeNull(); expect(body.querySelector("ol > li > ul")).not.toBeNull();
  expect(body.querySelector('[data-graph-node-id="pc_caelynn"]')).toHaveTextContent("Caelynn");
  expect(body.querySelector('[data-md-ref-id="gate-procedure"]')).toHaveTextContent("Gate procedure");
  expect(body.querySelector("script")).toBeNull(); expect(reader.querySelectorAll(".ProseMirror, [data-node-view-wrapper]")).toHaveLength(0);
  expect(reader).not.toHaveTextContent("Do not show this ordinary section");
  const context = within(reader).getByRole("region", { name: "Authored Beat context" });
  expect(context).toHaveAttribute("data-beat-id", "beat:gate-call");
  expect(context.querySelector(".world-plan-scene-reader__objective")).toHaveTextContent("keep the gate open");
  const details = context.querySelector("details")!; expect(details).not.toHaveAttribute("open");
  fireEvent.click(within(context).getByText("Beat details")); expect(details).toHaveAttribute("open");
  expect(details).toHaveTextContent("Pressure: rain"); expect(details).toHaveTextContent("Role: the scout");
  expect(details).toHaveTextContent("The bell rings twice");
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
      sceneId="scene:gate-call"
      onReturnToDocument={vi.fn()}
      onActivateGraphNode={onActivateGraphNode}
    />,
  );

  const cards = screen.getByTestId("world-plan-scene-reader");
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
      sceneId="scene:gate-call"
      onReturnToDocument={vi.fn()}
    />,
  );

  const cards = screen.getByTestId("world-plan-scene-reader");
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
      sceneId="scene:gate-call"
      onReturnToDocument={vi.fn()}
    />,
  );

  const cards = screen.getByTestId("world-plan-scene-reader");
  const sceneCard = cards.querySelector('[data-element-id="scene:gate-call"]');
  expect(sceneCard).toHaveTextContent("cannot be displayed safely in Cards");
  expect(sceneCard?.querySelector('a[href^="javascript:"]')).toBeNull();
});


it("keeps the surface-selected scene while a newer verified basis replaces its source provenance", () => {
  const imported = markdownToTiptapDoc(initialMarkdown);
  const props = { worldId, documentId, document: imported.doc, markdown: initialMarkdown, sourceWarnings: [], sceneId: "scene:arrival", isDirty: false, onReturnToDocument: vi.fn() };
  const view = render(<WorldPlanCardProjection {...props} basis={{ status: "verified", revision: 4, contentSha256: initialDigest }} />);
  expect(screen.getByTestId("world-plan-scene-reader").querySelector("[data-scene-card]")).toHaveAttribute("data-source-revision", "4");
  view.rerender(<WorldPlanCardProjection {...props} basis={{ status: "verified", revision: 5, contentSha256: committedDigest }} />);
  const card = screen.getByTestId("world-plan-scene-reader").querySelector("[data-scene-card]");
  expect(card).toHaveAttribute("data-scene-id", "scene:arrival"); expect(card).toHaveAttribute("data-source-revision", "5");
  expect(card).toHaveAttribute("data-content-sha256", committedDigest); expect(screen.queryByText("Back to outline")).toBeNull();
});

it("keeps current draft Agent Edit targeting separate from committed Ask authority", async () => {
  const { apis } = await mountOwner(); await openCards();
  fireEvent.click(screen.getByRole("button", { name: "Show scene: Arrival" }));
  expect(agentState()).toMatchObject({ target: { kind: "scene", id: "scene:arrival" }, basis: { revision: 4, contentSha256: initialDigest } });
  const editor = liveEditor(); documentView();
  act(() => { editor.commands.insertContentAt(2, "Unsaved draft "); });
  await openCards(); fireEvent.click(screen.getByRole("button", { name: "Show scene: Arrival" }));
  expect(agentState()).toMatchObject({ dirty: true, basis: { revision: 4, contentSha256: initialDigest } });
  const edit = vi.fn(); const keys = worldPlanCardTargetKeys(buildWorldPlanCardProjectionModel({document: editor.getJSON(), markdown: initialMarkdown}));
  renderReadonly(initialMarkdown, "scene:arrival", { isDirty: true, editableTargetKeys: keys, onSelectEditTarget: edit });
  fireEvent.click(screen.getByRole("button", { name: "Use scene for Agent edit" }));
  expect(edit).toHaveBeenCalledExactlyOnceWith({ kind: "scene", id: "scene:arrival" });
  expect(agentState().basis).toEqual({ revision: 4, contentSha256: initialDigest });
  expect(apis.prepare).not.toHaveBeenCalled(); expect(apis.commit).not.toHaveBeenCalled();
});

it("uses surface-owned card arrows and scrolls the selected scene into Document", async () => {
  const { apis } = await mountOwner(navigationMarkdown); const scrolled: HTMLElement[] = [];
  originalScrollIntoViewDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollIntoView"); scrollIntoViewWasPatched = true;
  HTMLElement.prototype.scrollIntoView = function () { scrolled.push(this); };
  await openCards(); const arrows = screen.getByRole("navigation", { name: "Card navigation" });
  expect(within(arrows).getByRole("button", { name: "Previous scene" })).toBeDisabled();
  fireEvent.click(within(arrows).getByRole("button", { name: "Next scene" }));
  expect(screen.getByRole("button", { name: "Show scene: Glass Regent" })).toHaveAttribute("aria-current", "true");
  documentView(); expect(scrolled.at(-1)).toHaveAttribute("data-dmb-playable-id", "scene:regent");
  expect(apis.commit).not.toHaveBeenCalled();
});

it("clears the committed Ask target when a new draft scene is not in the saved Plan", async () => {
  const { apis } = await mountOwner(); await openCards(); fireEvent.click(screen.getByRole("button", { name: "Show scene: Arrival" }));
  expect(agentState().target).toEqual({kind:"scene", id:"scene:arrival"});
  documentView(); const source = initialMarkdown + "\n<!-- dmb-playable-element:v2 kind=scene id=scene:new -->\n### New draft scene\nDraft only.\n";
  act(() => { liveEditor().commands.setContent(markdownToTiptapDoc(source).doc); });
  await openCards(); fireEvent.click(screen.getByRole("button", { name: "Show scene: New draft scene" }));
  expect(agentState().target).toBeNull(); expect(agentState().basis).toBeNull(); expect(apis.commit).not.toHaveBeenCalled();
});

it("keeps one draft through Cards, ordinary Save and fresh reopen at the exact committed revision", async () => {
  const { apis, mounted } = await mountOwner(); const editor = liveEditor();
  act(() => { editor.commands.insertContentAt(2, "Saved revision witness "); });
  const draft = editor.getJSON(); await openCards(); await savePlan();
  expect(liveEditor()).toBe(editor); expect(editor.getJSON()).toEqual(draft);
  expect(apis.prepare).toHaveBeenCalledTimes(1); expect(apis.commit).toHaveBeenCalledTimes(1);
  expect(apis.commit.mock.calls[0][0]).toMatchObject({expected_revision:5,world_id:worldId,document_id:documentId});
  expect(apis.readServer()).toMatchObject({savedRevision:6,savedDigest:committedDigest});
  expect(apis.readServer().savedMarkdown).toContain("dmb-playable-element:v2");
  mounted.unmount(); localStorage.clear(); renderPlan(); await screen.findByTestId("world-owned-plan"); await openCards();
  expect(liveEditor()).not.toBe(editor); expect(liveEditor().getJSON()).toEqual(draft); expect(agentState().revision).toBe(6);
  expect(apis.commit).toHaveBeenCalledTimes(1);
});

it("keeps a server draft uncommitted until Save then reopens the committed current card", async () => {
  const { apis, mounted } = await mountOwner(initialMarkdown.replace("Scene overview.", "Server draft witness."), "draft");
  await openCards(); fireEvent.click(screen.getByRole("button", {name:"Show scene: Arrival"}));
  expect(agentState().basis).toBeNull(); expect(apis.prepare).not.toHaveBeenCalled();
  expect(liveEditor().getText()).toContain("Server draft witness."); await savePlan();
  mounted.unmount(); localStorage.clear(); renderPlan(); await screen.findByTestId("world-owned-plan"); await openCards();
  fireEvent.click(screen.getByRole("button", {name:"Show scene: Arrival"}));
  expect(agentState()).toMatchObject({basis:{revision:6,contentSha256:committedDigest}});
  expect(liveEditor().getText()).toContain("Server draft witness."); expect(apis.commit).toHaveBeenCalledTimes(1);
});

it("keeps unknown saved authority unavailable while still allowing the current draft to be read", async () => {
  const { apis } = await mountOwner(initialMarkdown, "unknown"); await openCards();
  fireEvent.click(screen.getByRole("button", {name:"Show scene: Arrival"}));
  expect(agentState().basis).toBeNull(); expect(agentState().target).toBeNull();
  expect(liveEditor().getText()).toContain("Scene overview."); expect(apis.commit).not.toHaveBeenCalled();
});

it("round-trips current v2 references, callouts, tables and media through Cards Save and reopen", async () => {
  const { apis, mounted } = await mountOwner(navigationMarkdown + "\nParagraph [Caelynn](#dmb-ref:npc:caelynn).\n\n> [!RULES] Travel\n> Rules witness.\n");
  const editor = liveEditor(); act(() => { editor.commands.insertContentAt(2, "V2 writer witness "); });
  const draft = editor.getJSON(); await openCards(); fireEvent.click(screen.getByRole("button",{name:"Show scene: Harbor Census"}));
  expect(liveEditor()).toBe(editor); await savePlan();
  expect(apis.readServer().savedMarkdown).toContain("width=55 collapsed=true");
  expect(apis.readServer().savedMarkdown).toContain("[Caelynn](#dmb-ref:npc:caelynn)");
  expect(apis.readServer().savedMarkdown).toContain("| Name | Duty |"); expect(apis.readServer().savedMarkdown).toContain("[!RULES]");
  mounted.unmount(); localStorage.clear(); renderPlan(); await screen.findByTestId("world-owned-plan"); await openCards();
  expect(liveEditor().getJSON()).toEqual(draft); expect(apis.commit).toHaveBeenCalledTimes(1);
});

it("preserves an uncertain commit draft and fences Agent authority without retrying on view changes", async () => {
  const { apis } = await mountOwner(); let reject!: (error:Error)=>void;
  apis.commit.mockImplementationOnce(() => new Promise((_, rejection) => { reject = rejection; }));
  const editor = liveEditor(); act(() => { editor.commands.insertContentAt(2,"Pending witness "); }); const draft=editor.getJSON();
  await openCards(); const host=await openPlanEditHost(); fireEvent.click(await within(host).findByRole("button",{name:"Save Plan"}));
  await waitFor(()=>expect(apis.commit).toHaveBeenCalledTimes(1));
  expect(agentState().saveInFlight).toBe(true); documentView(); await openCards();
  expect(editor.getJSON()).toEqual(draft); expect(apis.prepare).toHaveBeenCalledTimes(1);
  const local=JSON.parse(localStorage.getItem(`dmb:world-plan-local-draft:v2:${worldId}`)??"null");
  expect(local.pending_write).toMatchObject({phase:"commit",base_revision:4,prepared_revision:5});
  await act(async()=>{reject(new Error("commit response failed"));});
  expect(await screen.findByText("commit response failed")).toBeInTheDocument();
  expect(editor.getJSON()).toEqual(draft); expect(apis.commit).toHaveBeenCalledTimes(1);
});

it("invalidates scene and Agent identity when the document or World changes", async () => {
  const { apis, mounted } = await mountOwner(); await openCards(); fireEvent.click(screen.getByRole("button",{name:"Show scene: Arrival"}));
  const second={...record,document_id:secondDocumentId,title:"Second Plan",revision:12};
  vi.mocked(liveApi.listWorldOwnedPlans).mockResolvedValue({schema_version:"dmb_workspace_document_registry_v2",scope_mode:"world",world_id:worldId,records:[record,second]});
  // A fresh owner mount reads the new document catalog; the picker then performs the identity transition.
  mounted.unmount(); localStorage.clear(); const next=renderPlan(); await screen.findByTestId("world-owned-plan");
  const nextSource=initialMarkdown.replaceAll("scene:arrival","scene:second").replaceAll("Arrival","Second scene");
  vi.mocked(liveApi.getWorldOwnedPlanSnapshot).mockResolvedValue({schema_version:"dmb_workspace_document_snapshot_v2",record:second,markdown:nextSource,content_sha256:"c".repeat(64),file_fingerprint:"postgres",file_exists:true,loaded_revision:12});
  fireEvent.change(screen.getByRole("combobox",{name:"Plan document"}),{target:{value:secondDocumentId}});
  await waitFor(()=>expect(agentState().documentId).toBe(secondDocumentId)); await openCards();
  expect(screen.queryByRole("button",{name:"Show scene: Arrival"})).toBeNull(); expect(agentState().basis?.contentSha256).not.toBe(initialDigest);
  next.unmount(); localStorage.clear();
  const other={...second,document_id:thirdDocumentId,world_id:secondWorldId,title:"Other World Plan",revision:21};
  vi.mocked(liveApi.listWorldContainers).mockResolvedValue({schema_version:"dmb_world_container_registry_v1",records:[{schema_version:"dmb_world_container_record_v1",world_id:secondWorldId,name:"Other World",source_root_relpath:"corpus/other",created_at:record.created_at}]});
  vi.mocked(liveApi.listWorldOwnedPlans).mockResolvedValue({schema_version:"dmb_workspace_document_registry_v2",scope_mode:"world",world_id:secondWorldId,records:[other]});
  vi.mocked(liveApi.getManagedWorldPlanContext).mockResolvedValue({schema_version:"dmb_managed_world_plan_context_v2",scope_mode:"world",world_id:secondWorldId,campaign_id:null,session:null,authoritative:false,generated_at:record.created_at,derived_from:[],timeline:[]});
  vi.mocked(liveApi.getWorldOwnedPlanSnapshot).mockResolvedValue({schema_version:"dmb_workspace_document_snapshot_v2",record:other,markdown:nextSource,content_sha256:"d".repeat(64),file_fingerprint:"postgres",file_exists:true,loaded_revision:21});
  window.history.replaceState({},"",`/plan?world=${secondWorldId}&documentId=${thirdDocumentId}`); renderPlan(secondWorldId);
  await waitFor(()=>expect(agentState()).toMatchObject({worldId:secondWorldId,documentId:thirdDocumentId,revision:21}));
  expect(apis.commit).not.toHaveBeenCalled();
});

it("navigates the thumbnail deck across Beats and retains scene and deck scroll through Document/Cards without writes", async () => {
  const {apis}=await mountOwner(navigationMarkdown); await openCards(); const deck=screen.getByRole("navigation",{name:"Contents"});
  const list=within(deck).getByRole("list"); list.scrollTop=80;
  fireEvent.click(within(deck).getByRole("button",{name:"Show scene: Harbor Census"}));
  documentView(); await openCards(); expect(screen.getByRole("navigation",{name:"Contents"})).toBe(deck);
  expect(list.scrollTop).toBe(80); expect(within(deck).getByRole("button",{name:"Show scene: Harbor Census"})).toHaveAttribute("aria-current","true");
  expect(apis.prepare).not.toHaveBeenCalled(); expect(apis.commit).not.toHaveBeenCalled();
});

it("retains the same editor, draft media, caret and undo history while browsing scenes and switching views", async () => {
  const {apis}=await mountOwner(navigationMarkdown); const editor=liveEditor(); const accepted=editor.getJSON();
  act(()=>{editor.commands.setTextSelection(2); editor.commands.insertContent("Draft lantern ");
    let media=-1; editor.state.doc.descendants((node,pos)=>{if(node.type.name==="mediaImage")media=pos;});
    editor.commands.command(({tr})=>{tr.setNodeMarkup(media,undefined,{...tr.doc.nodeAt(media)!.attrs,width:70,collapsed:false});return true;});});
  const draft=editor.getJSON(); await openCards(); fireEvent.click(screen.getByRole("button",{name:"Show scene: Harbor Census"})); const caret=editor.state.selection.toJSON();
  documentView(); await openCards(); expect(liveEditor()).toBe(editor); expect(editor.getJSON()).toEqual(draft); expect(editor.state.selection.toJSON()).toEqual(caret);
  documentView();
  act(()=>{for(let remaining=20;remaining>0 && editor.commands.undo();remaining--){/* original user history */}}); expect(editor.getJSON()).toEqual(accepted); expect(apis.commit).not.toHaveBeenCalled();
});

it("opens an initial Cards deep link at the same canonical scene in Document", async () => {
  installApiMocks(navigationMarkdown); window.history.replaceState({},"",`/plan?world=${worldId}&documentId=${documentId}&view=cards`);renderPlan();
  const first=await screen.findByRole("button",{name:"Show scene: Lantern Gate"}); await waitFor(()=>expect(first).toHaveAttribute("aria-current","true"));
  documentView(); await openCards(); expect(first).toHaveAttribute("aria-current","true"); expect(screen.queryByText("Back to outline")).toBeNull();
});
it("opens Cards directly at a scene with no outline destination and retains its editor across disclosure and views", async () => {
  const apis = installApiMocks(navigationMarkdown);
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}&view=cards`);
  renderPlan();
  await screen.findByTestId("world-owned-plan");
  const first = await screen.findByRole("button", { name: "Show scene: Lantern Gate" });
  await waitFor(() => expect(first).toHaveAttribute("aria-current", "true"));
  expect(screen.queryByRole("button", { name: "Scene outline", exact: true })).toBeNull();
  expect(screen.queryByRole("heading", { name: "Plan cards", exact: true })).toBeNull();
  const dom = screen.getByTestId("world-owned-plan-markdown-editor").querySelector(".ProseMirror") as HTMLElement & { editor: Editor };
  const editor = dom.editor;
  const accepted = editor.getJSON();
  act(() => {
    editor.commands.setTextSelection(2);
    editor.commands.insertContent("Draft continuity ");
    let mediaPos = -1;
    editor.state.doc.descendants((node, pos) => { if (node.type.name === "mediaImage") mediaPos = pos; });
    expect(mediaPos).toBeGreaterThanOrEqual(0);
    editor.commands.command(({ tr }) => { tr.setNodeMarkup(mediaPos, undefined,
      { ...tr.doc.nodeAt(mediaPos)!.attrs, width: 70, collapsed: false }); return true; });
  });
  const draft = editor.getJSON();
  const initialCaret = editor.state.selection.toJSON();
  fireEvent.click(screen.getByRole("button", { name: "Collapse Contents", exact: true }));
  fireEvent.click(screen.getByRole("button", { name: "Expand Contents", exact: true }));
  expect(editor.state.selection.toJSON()).toEqual(initialCaret);
  fireEvent.click(screen.getByRole("button", { name: "Show scene: Glass Regent" }));
  const caret = editor.state.selection.toJSON();
  expect(screen.getByRole("button", { name: "Show scene: Glass Regent" })).toHaveAttribute("aria-current", "true");
  const views = screen.getByRole("group", { name: "Plan view" });
  fireEvent.click(within(views).getByRole("button", { name: "Document", exact: true }));
  fireEvent.click(within(views).getByRole("button", { name: "Cards", exact: true }));
  expect(screen.getByRole("button", { name: "Show scene: Glass Regent" })).toHaveAttribute("aria-current", "true");
  expect(screen.queryByRole("heading", { name: "Plan cards", exact: true })).toBeNull();
  expect(dom.editor).toBe(editor);
  expect(editor.getJSON()).toEqual(draft);
  expect(editor.state.selection.toJSON()).toEqual(caret);
  documentView();
  act(() => { for (let remaining=20; remaining>0 && editor.commands.undo(); remaining--) { /* retained user history */ } });
  expect(editor.getJSON()).toEqual(accepted);
  expect(apis.prepare).not.toHaveBeenCalled();
  expect(apis.commit).not.toHaveBeenCalled();
});

it("opens Cards directly at the first remaining scene when the selected marker disappears", async () => {
  const apis = installApiMocks(navigationMarkdown);
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}&view=cards`);
  renderPlan();
  const selected = await screen.findByRole("button", { name: "Show scene: Glass Regent" });
  fireEvent.click(selected);
  expect(selected).toHaveAttribute("aria-current", "true");
  const dom = screen.getByTestId("world-owned-plan-markdown-editor").querySelector(".ProseMirror") as HTMLElement & { editor: Editor };
  const views = screen.getByRole("group", { name: "Plan view" });
  fireEvent.click(within(views).getByRole("button", { name: "Document", exact: true }));
  act(() => { dom.editor.commands.setContent(markdownToTiptapDoc(navigationMarkdown.replace("id=scene:regent", "id=scene:renamed-regent")).doc); });
  fireEvent.click(within(views).getByRole("button", { name: "Cards", exact: true }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Show scene: Lantern Gate" })).toHaveAttribute("aria-current", "true"));
  expect(screen.queryByRole("heading", { name: "Plan cards", exact: true })).toBeNull();
  expect(screen.queryByRole("button", { name: "Scene outline", exact: true })).toBeNull();
  expect(apis.commit).not.toHaveBeenCalled();
});
