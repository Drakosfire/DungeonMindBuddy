import { Editor, type JSONContent } from "@tiptap/core";
import { TextSelection } from "@tiptap/pm/state";
import { webcrypto } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from "../../tiptap/MarkdownEditorCore";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import { tiptapJsonToSemanticMarkdown } from "../../tiptap/markdown/calloutMarkdown";
import { resolvePlayableBodyTarget } from "./planPlayableBodyTarget";
import { preserveLeadingYamlFrontmatter } from "../../tiptap/markdown/stripLeadingYamlFrontmatter";
import {
  admitWorldPlanEditProposal,
  admitPlanEditProposal,
  applyWorldPlanEditProposal,
  applyPlanEditProposal,
  capturePlanEditTarget,
  captureWorldPlanEditTarget,
  captureWorldPlanAuthoringTarget,
  restorePlanAuthoringTarget,
  preparePlanAuthoringApplication,
  previewWorldPlanEditProposal,
  restoreWorldPlanSelection,
  type ExpectedWorldPlanEditAgentBinding,
  type PlanEditEditorState,
  type WorldPlanEditAgentBinding,
  type WorldPlanEditEditorState,
} from "./planAgentEditProposal";
import { planSectionTargets } from "./planSectionTarget";

const BASE_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
const editors: Editor[] = [];

beforeAll(() => {
  Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });
});

function mountedState(markdown = "# Plan\n\nOpening frame") {
  const element = document.createElement("div");
  document.body.appendChild(element);
  const editor = new Editor({
    element,
    extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,
    content: markdownToTiptapDoc(markdown).doc,
  });
  editors.push(editor);
  const state: PlanEditEditorState = {
    editor,
    documentId: "plan-1",
    worldId: "world-1",
    session: 1,
    baseRevision: 2,
    baseContentSha256: BASE_SHA,
    sourceMarkdown: markdown,
    canEdit: true,
  };
  return { editor, state };
}

it.each(["stale", "missing", "duplicate"])("rejects a %s current scene before capture", async (failure) => {
  const scene = "<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->\n## Arrival\nOriginal prose.\n";
  const { state } = mountedState(failure === "missing" ? "# Plan\n" : failure === "duplicate" ? scene + scene : scene);
  await expect(captureWorldPlanEditTarget({ ...worldState(state),
    currentSceneTarget: { kind: "scene", id: "scene:arrival" }, currentSceneTargetStale: failure === "stale",
  })).rejects.toThrow();
});

it.each(["basis", "scene", "mode", "stale"])("rejects %s change after capturing default scene and preserves editor bytes", async (change) => {
  const { editor, state } = mountedState("# Plan\n<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->\n## Arrival\nOriginal prose.\n<!-- dmb-playable-element:v1 kind=scene id=scene:next -->\n## Next\nNext prose.\n");
  let current: WorldPlanEditEditorState = { ...worldState(state), currentSceneTarget: { kind: "scene", id: "scene:arrival" } };
  const captured = await captureWorldPlanEditTarget(current, () => current);
  expect(captured.playableTargetSource).toBe("scene");
  expect(editor.state.doc.textBetween(captured.from, captured.to, "\n")).toBe("Original prose.");
  const key = "00000000-0000-4000-8000-000000000002";
  const admitted = await admitWorldPlanEditProposal(captured, await worldResponseFor(captured, "Revised prose.\n", key), key);
  const before = editor.getJSON();
  current = change === "basis" ? { ...current, baseRevision: 3 }
    : change === "scene" ? { ...current, currentSceneTarget: { kind: "scene", id: "scene:next" } }
      : change === "stale" ? { ...current, currentSceneTargetStale: true }
      : { ...current, playableTarget: { kind: "scene", id: "scene:arrival" } };
  await expect(applyWorldPlanEditProposal({ captured, admitted, getCurrent: () => current,
    expectedAgentBinding: expectedAgentBinding(), getAgentBinding: matchingAgentBinding,
  })).rejects.toThrow();
  expect(editor.getJSON()).toEqual(before);
});

function responseFor(
  captured: Awaited<ReturnType<typeof capturePlanEditTarget>>,
  replacement_markdown: string,
) {
  return {
    schema_version: "dmb_plan_document_edit_proposal_v1" as const,
    document_id: captured.request.document_id,
    world_id: captured.request.world_id,
    session: captured.request.session,
    base_revision: captured.request.base_revision,
    base_content_sha256: captured.request.base_content_sha256,
    draft_sha256: captured.request.draft_sha256,
    target_kind: captured.request.target_kind,
    selected_text_sha256: BASE_SHA,
    replacement_markdown,
    summary: "Opening scene",
    assumptions: [],
    model: "test-model",
    model_observed: true,
    model_latency_ms: 1,
    wall_latency_ms: 1,
    usage: null,
  };
}

function worldState(state: PlanEditEditorState): WorldPlanEditEditorState {
  return {
    editor: state.editor,
    documentId: state.documentId,
    worldId: state.worldId,
    baseRevision: state.baseRevision,
    baseContentSha256: state.baseContentSha256,
    sourceMarkdown: state.sourceMarkdown,
    draftGeneration: 0,
    selectionGeneration: 0,
    canEdit: state.canEdit,
  };
}

it("restores the second duplicate in a new editor and applies only that range", async () => {
  const markdown = "# Plan\n\nSame passage.\n\nOther prose.\n\nSame passage.\n";
  const first = mountedState(markdown);
  const positions: number[] = [];
  first.editor.state.doc.descendants((node, pos) => {
    if (node.isText && node.text === "Same passage.") positions.push(pos);
  });
  expect(positions).toHaveLength(2);
  const second = positions[1]!;
  first.editor.view.dispatch(first.editor.state.tr.setSelection(
    TextSelection.create(first.editor.state.doc, second + "Same passage.".length, second),
  ));
  const captured = await captureWorldPlanEditTarget(worldState(first.state));
  const anchor = captured.request.selection_anchor!;
  expect(anchor).toMatchObject({ from: second, to: second + "Same passage.".length,
    anchor: second + "Same passage.".length, head: second, section: null });
  first.editor.destroy();

  const remounted = mountedState(markdown);
  expect(remounted.editor.state.selection.empty).toBe(true);
  const current = worldState(remounted.state);
  const restored = await restoreWorldPlanSelection(anchor, captured.request.draft_sha256,
    await sha256Hex(captured.request.selected_text), {
      worldId: captured.request.world_id, documentId: captured.request.document_id,
      baseRevision: captured.request.base_revision, baseContentSha256: captured.request.base_content_sha256,
    }, () => true, () => current);
  expect(restored.request.selection_anchor).toEqual(anchor);
  const key = "00000000-0000-4000-8000-000000000002";
  const admitted = await admitWorldPlanEditProposal(restored,
    await worldResponseFor(restored, "Changed only here.", key), key);
  const preview = previewWorldPlanEditProposal(restored, admitted);
  expect(preview.before.markdown.match(/Same passage\./g)).toHaveLength(2);
  expect(preview.after.markdown).toContain("Same passage.");
  expect(preview.after.markdown).toContain("Changed only here.");
  await applyWorldPlanEditProposal({ captured: restored, admitted, getCurrent: () => current,
    expectedAgentBinding: expectedAgentBinding(), getAgentBinding: matchingAgentBinding });
  expect(remounted.editor.getText().match(/Same passage\./g)).toHaveLength(1);
  expect(remounted.editor.getText()).toContain("Changed only here.");
});

it("refuses a saved range after same-text editor JSON drift without moving the selection", async () => {
  const source = "# Plan\n\nSame passage.\n\nSame passage.\n";
  const first = mountedState(source);
  const positions: number[] = [];
  first.editor.state.doc.descendants((node, pos) => {
    if (node.isText && node.text === "Same passage.") positions.push(pos);
  });
  first.editor.commands.setTextSelection({ from: positions[1]!, to: positions[1]! + "Same passage.".length });
  const captured = await captureWorldPlanEditTarget(worldState(first.state));
  const remounted = mountedState("# Plan\n\nChanged prefix.\n\nSame passage.\n\nSame passage.\n");
  const before = remounted.editor.state.selection.toJSON();
  await expect(restoreWorldPlanSelection(captured.request.selection_anchor!,
    captured.request.draft_sha256, await sha256Hex(captured.request.selected_text), {
      worldId: captured.request.world_id, documentId: captured.request.document_id,
      baseRevision: captured.request.base_revision, baseContentSha256: captured.request.base_content_sha256,
    }, () => true,
    () => worldState(remounted.state))).rejects.toThrow(/Start a fresh edit/);
  expect(remounted.editor.state.selection.toJSON()).toEqual(before);
});

it.each(["World", "document", "revision", "digest"] as const)(
  "refuses a changed %s binding before restoring the saved selection", async (changed) => {
    const source = "# Plan\n\nSame passage.\n\nSame passage.\n";
    const first = mountedState(source);
    const positions: number[] = [];
    first.editor.state.doc.descendants((node, pos) => {
      if (node.isText && node.text === "Same passage.") positions.push(pos);
    });
    first.editor.commands.setTextSelection({ from: positions[1]!, to: positions[1]! + "Same passage.".length });
    const captured = await captureWorldPlanEditTarget(worldState(first.state));
    const remounted = mountedState(source);
    const before = remounted.editor.state.selection.toJSON();
    const beforeDocument = remounted.editor.getJSON();
    await expect(restoreWorldPlanSelection(captured.request.selection_anchor!,
      captured.request.draft_sha256, await sha256Hex(captured.request.selected_text), {
        worldId: changed === "World" ? "other-world" : captured.request.world_id,
        documentId: changed === "document" ? "other-plan" : captured.request.document_id,
        baseRevision: changed === "revision" ? captured.request.base_revision + 1 : captured.request.base_revision,
        baseContentSha256: changed === "digest" ? "f".repeat(64) : captured.request.base_content_sha256,
      }, () => true, () => worldState(remounted.state))).rejects.toThrow(/Start a fresh edit/);
    expect(remounted.editor.state.selection.toJSON()).toEqual(before);
    expect(remounted.editor.getJSON()).toEqual(beforeDocument);
});

it.each(["out-of-document range", "draft SHA", "selected-text SHA", "unknown anchor version", "unknown editor format", "extra anchor key"] as const)(
  "refuses %s before moving the saved selection", async (changed) => {
    const source = "# Plan\n\nSame passage.\n\nSame passage.\n";
    const first = mountedState(source);
    const positions: number[] = [];
    first.editor.state.doc.descendants((node, pos) => {
      if (node.isText && node.text === "Same passage.") positions.push(pos);
    });
    first.editor.commands.setTextSelection({ from: positions[1]!, to: positions[1]! + "Same passage.".length });
    const captured = await captureWorldPlanEditTarget(worldState(first.state));
    const remounted = mountedState(source);
    const beforeSelection = remounted.editor.state.selection.toJSON();
    const beforeDocument = remounted.editor.getJSON();
    const anchor = { ...captured.request.selection_anchor! };
    if (changed === "out-of-document range") {
      anchor.anchor = remounted.editor.state.doc.content.size + 10;
      anchor.head = anchor.anchor + 1;
      anchor.from = anchor.anchor;
      anchor.to = anchor.head;
    } else if (changed === "unknown anchor version") {
      Object.assign(anchor, { schema_version: "dmb_plan_selection_anchor_v2" });
    } else if (changed === "unknown editor format") {
      Object.assign(anchor, { editor_format: "unknown-editor-v1" });
    } else if (changed === "extra anchor key") {
      Object.assign(anchor, { unexpected: "forged" });
    }
    await expect(restoreWorldPlanSelection(anchor,
      changed === "draft SHA" ? "f".repeat(64) : captured.request.draft_sha256,
      changed === "selected-text SHA" ? "f".repeat(64) : await sha256Hex(captured.request.selected_text), {
        worldId: captured.request.world_id, documentId: captured.request.document_id,
        baseRevision: captured.request.base_revision, baseContentSha256: captured.request.base_content_sha256,
      }, () => true, () => worldState(remounted.state))).rejects.toThrow(/Start a fresh edit/);
    expect(remounted.editor.state.selection.toJSON()).toEqual(beforeSelection);
    expect(remounted.editor.getJSON()).toEqual(beforeDocument);
});

it("refuses a changed World conversation origin before restoring the saved selection", async () => {
  const source = "# Plan\n\nSame passage.\n\nSame passage.\n";
  const first = mountedState(source);
  const positions: number[] = [];
  first.editor.state.doc.descendants((node, pos) => {
    if (node.isText && node.text === "Same passage.") positions.push(pos);
  });
  first.editor.commands.setTextSelection({ from: positions[1]!, to: positions[1]! + "Same passage.".length });
  const captured = await captureWorldPlanEditTarget(worldState(first.state));
  const remounted = mountedState(source);
  const before = remounted.editor.state.selection.toJSON();
  await expect(restoreWorldPlanSelection(captured.request.selection_anchor!,
    captured.request.draft_sha256, await sha256Hex(captured.request.selected_text), {
      worldId: captured.request.world_id, documentId: captured.request.document_id,
      baseRevision: captured.request.base_revision, baseContentSha256: captured.request.base_content_sha256,
    }, () => false, () => worldState(remounted.state))).rejects.toThrow(/Start a fresh edit/);
  expect(remounted.editor.state.selection.toJSON()).toEqual(before);
});

it.each(["caret", "selection", "list", "card", "frontmatter"])("previews frozen %s context without mutation and matches actual Apply", async (kind) => {
  let source = kind === "card"
    ? "# Plan\n<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->\n## Arrival\nFirst sentence. Second sentence.\n<!-- dmb-playable-element:v1 kind=scene id=scene:next -->\n## Next\nOther prose.\n"
    : kind === "list" ? "# Opening\n\n- First item\n- Second item\n\n# Later\n\nOther prose.\n"
      : "# Opening\n\nFirst sentence. Second sentence.\n\n# Later\n\nOther prose.\n";
  if (kind === "frontmatter") source = "---\ntitle: Frozen Plan\n---\n" + source;
  const { editor, state } = mountedState(source);
  let textPosition = 0;
  editor.state.doc.descendants((node, position) => {
    if (node.isText && node.text?.startsWith(kind === "list" ? "First item" : "First sentence.")) textPosition = position;
  });
  editor.commands.setTextSelection(kind === "caret" || kind === "frontmatter" ? textPosition + "First sentence.".length
    : kind === "card" ? 1 : { from: textPosition, to: textPosition + (kind === "list" ? "First item".length : "First sentence.".length) });
  const current: WorldPlanEditEditorState = { ...worldState(state),
    ...(kind === "card" ? { currentSceneTarget: { kind: "scene", id: "scene:arrival" }, currentSceneTargetLabel: "Arrival" } : {}) };
  const captured = await captureWorldPlanEditTarget(current, () => current);
  const key = "00000000-0000-4000-8000-000000000002";
  const admitted = await admitWorldPlanEditProposal(captured, await worldResponseFor(captured, "New detail.", key), key);
  const beforeJson = editor.getJSON();
  const beforeSelection = editor.state.selection.toJSON();
  const admittedBytes = JSON.stringify(admitted);
  const storageWrite = vi.spyOn(Storage.prototype, "setItem");
  const preview = previewWorldPlanEditProposal(captured, admitted);
  expect(storageWrite).not.toHaveBeenCalled();
  expect(editor.getJSON()).toEqual(beforeJson);
  expect(editor.state.selection.toJSON()).toEqual(beforeSelection);
  expect(JSON.stringify(admitted)).toBe(admittedBytes);
  expect(preview.before.markdown).toBe(captured.request.draft_markdown);
  expect(preview.before.sourceLineTarget).toBeDefined();
  expect(preview.before.markdown.split("\n")[preview.before.sourceLineTarget!.startLine - 1]).toContain(kind === "list" ? "First item" : "First sentence.");
  expect(preview.after.markdown).toContain(kind === "card" ? "## Arrival" : "# Opening");
  expect(preview.after.markdown).toContain("Other prose.");
  expect(preview.after.markdown).toContain("New detail.");
  await applyWorldPlanEditProposal({ captured, admitted, getCurrent: () => current,
    expectedAgentBinding: expectedAgentBinding(), getAgentBinding: matchingAgentBinding });
  expect(preview.after.markdown).toBe(preserveLeadingYamlFrontmatter(captured.request.draft_markdown, tiptapJsonToSemanticMarkdown(editor.getJSON())));
  expect(previewWorldPlanEditProposal(captured, admitted)).toEqual(preview);
});

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function worldResponseFor(
  captured: Awaited<ReturnType<typeof captureWorldPlanEditTarget>>,
  replacement_markdown: string,
  idempotency_key = "00000000-0000-4000-8000-000000000002",
) {
  const bodyTarget = captured.playableBodyTarget;
  return {
    schema_version: bodyTarget
      ? "dmb_world_plan_document_edit_proposal_v2" as const
      : "dmb_world_plan_document_edit_proposal_v1" as const,
    action_id: "00000000-0000-4000-8000-000000000001",
    idempotency_key,
    document_id: captured.request.document_id,
    world_id: captured.request.world_id,
    base_revision: captured.request.base_revision,
    base_content_sha256: captured.request.base_content_sha256,
    draft_sha256: captured.request.draft_sha256,
    target_kind: captured.request.target_kind,
    selected_text_sha256: bodyTarget ? null : await sha256Hex(captured.request.selected_text),
    ...(bodyTarget ? {
      playable_target: bodyTarget.target,
      marker_grammar_version: bodyTarget.markerGrammarVersion,
      body_scope: bodyTarget.bodyScope,
      range_semantics_version: bodyTarget.rangeSemanticsVersion,
      body_serialization_version: bodyTarget.bodySerializationVersion,
      target_body_sha256: bodyTarget.targetBodySha256,
    } : {}),
    replacement_markdown,
    summary: "Opening scene",
    assumptions: [],
    model: "test-model",
    model_observed: true,
    model_latency_ms: 1,
    wall_latency_ms: 1,
    usage: null,
  };
}

function matchingAgentBinding(): WorldPlanEditAgentBinding {
  return {
    mounted: true,
    verifiedWorldId: "world-1",
    activeThreadId: "thread-1",
    scope: {
      campaignId: "world-plan-agent:world:world-1:document:plan-1",
      surfaceId: "plan",
      sessionNumber: null,
      documentId: "plan-1",
    },
  };
}

function expectedAgentBinding(): ExpectedWorldPlanEditAgentBinding {
  return {
    worldId: "world-1",
    documentId: "plan-1",
    threadId: "thread-1",
    namespace: "world-plan-agent:world:world-1:document:plan-1",
  };
}

const SECTION_MARKER = "<!-- dmb-playable-element:v2 kind=scene id=scene:town-breathes -->";
const SECTION_LINK = "[Lysandra Ironveil](dmb-node:node:captain-lysandra-ironveil)";
const SESSION_29_MARKDOWN = readFileSync(resolve(
  process.cwd(),
  "../..",
  "corpus",
  "eldyrwild-markdown",
  "Longmont Campaign",
  "Campaign 2",
  "Session Prep",
  "Session 29 - Buddy Plan.md",
), "utf8");
const WORLD_SECTION_MARKDOWN = [
  "# World Plan",
  "",
  "## Mireward",
  `${SECTION_MARKER}`,
  "### After the attack",
  "",
  `${SECTION_LINK} is present.`,
  "",
  "### Recovery",
  "The town regroups.",
  "",
  "## North Road",
  "A different route.",
].join("\n");

async function captureWorldSection(markdown = WORLD_SECTION_MARKDOWN, heading = "Mireward") {
  const { editor, state } = mountedState(markdown);
  const target = planSectionTargets(editor).find((candidate) => candidate.heading === heading);
  if (!target) throw new Error(`World Plan heading not found: ${heading}`);
  editor.commands.setTextSelection({ from: target.from, to: target.to });
  const current = worldState(state);
  const captured = await captureWorldPlanEditTarget(current, () => current);
  return { editor, current, captured };
}

afterEach(() => {
  vi.restoreAllMocks();
  for (const editor of editors.splice(0)) {
    const element = editor.options.element;
    editor.destroy();
    element?.remove();
  }
});

describe("reviewed Plan edit admission", () => {
  it("captures the mounted editor and applies registered prose/callout/decision components", async () => {
    const { editor, state } = mountedState();
    editor.commands.setTextSelection(1);
    const captured = await capturePlanEditTarget(state);
    const markdown = [
      "A quiet scene begins at the waystation.",
      "",
      "> [!READ-ALOUD]",
      "> The children wait beside the gate.",
      "",
      "> [!DECISION-CONSEQUENCE]",
      "> ### Decision",
      "> Invite the children inside.",
      ">",
      "> ### Consequence",
      "> Stacy remembers the kindness.",
    ].join("\n");
    const admitted = await admitPlanEditProposal(captured, responseFor(captured, markdown));
    await applyPlanEditProposal({ captured, admitted, current: state });
    const types = editor.getJSON().content?.map((item) => item.type);
    expect(types).toContain("callout");
    expect(types).toContain("decisionConsequence");
    expect(editor.getText()).toContain("Stacy remembers the kindness.");
  });

  it("validates the whole Plan when replacing a placeholder inside an existing list", async () => {
    const { editor, state } = mountedState(
      "# Plan\n\n## Session intent\n\nWhat should happen?\n\n## Scenes / beats\n\n- Opening frame\n- Decision forks\n- Exit ramps\n\n## Reference chips\n\nAdd references.",
    );
    let from = -1;
    let priorParagraphEnd = -1;
    editor.state.doc.descendants((node, position) => {
      if (node.isText && node.text === "Opening frame") from = position;
      if (node.isText && node.text === "Scenes / beats") priorParagraphEnd = position + node.nodeSize;
    });
    expect(from).toBeGreaterThan(0);
    expect(priorParagraphEnd).toBeGreaterThan(0);
    editor.commands.setTextSelection({ from: priorParagraphEnd, to: from + "Opening frame".length });
    const captured = await capturePlanEditTarget(state);
    expect(captured.request.selected_text.trim()).toBe("Opening frame");
    expect(captured.wholeBulletItem).toBeDefined();
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(captured.request.selected_text));
    const selectedSha = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
    const admitted = await admitPlanEditProposal(captured, {
      ...responseFor(captured, "Hempholm opens at dawn.\n\nStacy waits nearby.\n\n> [!READ-ALOUD]\n> Stacy waits.\n\n> [!DECISION-CONSEQUENCE]\n> ### Decision\n> Ask Stacy.\n>\n> ### Consequence\n> Stacy answers."),
      selected_text_sha256: selectedSha,
    });
    await applyPlanEditProposal({ captured, admitted, current: state });
    const exported = tiptapJsonToSemanticMarkdown(editor.getJSON());
    expect(exported).toContain("[!READ-ALOUD]");
    expect(exported).toContain("[!DECISION-CONSEQUENCE]");
    expect(exported).not.toMatch(/^\s*-\s*$/m);
    expect(markdownToTiptapDoc(exported).diagnostics).toEqual([]);
  });

  it("revises an inline phrase without splitting its paragraph or losing adjacent components", async () => {
    const { editor, state } = mountedState(
      "# Plan\n\nA half-sunk skiff waits.\n\n> [!READ-ALOUD]\n> The children watch.\n\n> [!DECISION-CONSEQUENCE]\n> ### Decision\n> Follow Stacy?\n>\n> ### Consequence\n> The tide turns.",
    );
    let phraseFrom = -1;
    editor.state.doc.descendants((node, position) => {
      if (node.isText && node.text?.includes("half-sunk")) phraseFrom = position + node.text.indexOf("half-sunk");
    });
    expect(phraseFrom).toBeGreaterThan(0);
    editor.commands.setTextSelection({ from: phraseFrom, to: phraseFrom + "half-sunk".length });
    const captured = await capturePlanEditTarget(state);
    const selectedDigest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("half-sunk"));
    const selectedSha = Array.from(new Uint8Array(selectedDigest), (byte) => byte.toString(16).padStart(2, "0")).join("");
    const admitted = await admitPlanEditProposal(captured, {
      ...responseFor(captured, "nearly submerged"),
      selected_text_sha256: selectedSha,
    });
    await applyPlanEditProposal({ captured, admitted, current: state });
    const exported = tiptapJsonToSemanticMarkdown(editor.getJSON());
    expect(exported).toContain("A nearly submerged skiff waits.");
    expect(exported).toContain("[!READ-ALOUD]");
    expect(exported).toContain("[!DECISION-CONSEQUENCE]");
    expect(markdownToTiptapDoc(exported).diagnostics).toEqual([]);
  });

  it("rejects a changed editor body, selection, document, or revision before mutation", async () => {
    const { editor, state } = mountedState();
    const captured = await capturePlanEditTarget(state);
    const admitted = await admitPlanEditProposal(captured, responseFor(captured, "New prose"));
    editor.commands.insertContentAt(2, "changed");
    const body = editor.getJSON();
    await expect(applyPlanEditProposal({ captured, admitted, current: state })).rejects.toThrow(/changed/);
    expect(editor.getJSON()).toEqual(body);
    await expect(applyPlanEditProposal({ captured, admitted, current: { ...state, documentId: "plan-2" } })).rejects.toThrow(/changed/);
    await expect(applyPlanEditProposal({ captured, admitted, current: { ...state, baseRevision: 3 } })).rejects.toThrow(/changed/);
  });

  it("does not capture a mixed target when an edit races the asynchronous draft digest", async () => {
    const { editor, state } = mountedState();
    editor.commands.setTextSelection({ from: 7, to: 14 });
    const originalDigest = crypto.subtle.digest.bind(crypto.subtle);
    let release!: () => void;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    vi.spyOn(crypto.subtle, "digest").mockImplementationOnce(async (...args) => {
      await gate;
      return originalDigest(...args);
    });
    const capture = capturePlanEditTarget(state);
    editor.commands.insertContentAt({ from: 7, to: 14 }, "Changed");
    editor.commands.setTextSelection({ from: 7, to: 14 });
    release();
    await expect(capture).rejects.toThrow(/changed/);
    expect(editor.getText()).toContain("Changed");
  });

  it("preserves an edit made during the asynchronous Apply recheck", async () => {
    const { editor, state } = mountedState();
    editor.commands.setTextSelection({ from: 7, to: 14 });
    const captured = await capturePlanEditTarget(state);
    const selectedDigest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("Opening"));
    const selectedSha = Array.from(new Uint8Array(selectedDigest), (byte) => byte.toString(16).padStart(2, "0")).join("");
    const admitted = await admitPlanEditProposal(captured, {
      ...responseFor(captured, "Agent text"), selected_text_sha256: selectedSha,
    });
    const originalDigest = crypto.subtle.digest.bind(crypto.subtle);
    let release!: () => void;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    vi.spyOn(crypto.subtle, "digest").mockImplementationOnce(async (...args) => {
      await gate;
      return originalDigest(...args);
    });
    const apply = applyPlanEditProposal({ captured, admitted, current: state });
    editor.commands.insertContentAt({ from: 7, to: 14 }, "Changed");
    editor.commands.setTextSelection({ from: 7, to: 14 });
    const localEdit = editor.getJSON();
    release();
    await expect(apply).rejects.toThrow(/changed/);
    expect(editor.getJSON()).toEqual(localEdit);
  });

  it.each([
    ["lock", { canEdit: false }],
    ["document", { documentId: "plan-2" }],
    ["World", { worldId: "world-2" }],
    ["revision", { baseRevision: 3 }],
    ["session", { session: 2 }],
  ] as const)("rechecks the live %s binding after hashing, without mutation", async (_label, change) => {
    const { editor, state } = mountedState();
    const captured = await capturePlanEditTarget(state);
    const admitted = await admitPlanEditProposal(captured, responseFor(captured, "Agent text"));
    const originalDigest = crypto.subtle.digest.bind(crypto.subtle);
    let release!: () => void;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    vi.spyOn(crypto.subtle, "digest").mockImplementationOnce(async (...args) => {
      await gate;
      return originalDigest(...args);
    });
    let live = state;
    const before = editor.getJSON();
    const apply = applyPlanEditProposal({ captured, admitted, current: state, getCurrent: () => live });
    live = { ...state, ...change };
    release();
    await expect(apply).rejects.toThrow();
    expect(editor.getJSON()).toEqual(before);
  });

  it.each([
    "<script>alert(1)</script>",
    "[Stacy](dmb-node:npc:made-up)",
    "> [!UNKNOWN]\n> A false component",
    "[file](/tmp/private.md)",
  ])("rejects unsupported fragment %s", async (markdown) => {
    const { state } = mountedState();
    const captured = await capturePlanEditTarget(state);
    await expect(admitPlanEditProposal(captured, responseFor(captured, markdown))).rejects.toThrow();
  });

  it("rejects a response bound to another draft", async () => {
    const { state } = mountedState();
    const captured = await capturePlanEditTarget(state);
    await expect(admitPlanEditProposal(captured, {
      ...responseFor(captured, "Valid prose"),
      draft_sha256: BASE_SHA,
    })).rejects.toThrow(/captured Plan target/);
  });
});

describe("reviewed World-only Plan edit admission and Apply", () => {
  it("restores a protected rich-text section with duplicate heading labels by exact range", async () => {
    const source = [
      "# World Plan", "", "## Mireward", "First heading remains untouched.", "",
      "## Mireward", SECTION_MARKER, "### After the attack", "",
      "- The **watcher** waits for *a signal*.", "- The town regroups.", "",
      `${SECTION_LINK} is present.`, "", "## North Road", "Elsewhere.",
    ].join("\n");
    const first = mountedState(source);
    const sections = planSectionTargets(first.editor).filter((candidate) => candidate.heading === "Mireward");
    expect(sections).toHaveLength(2);
    first.editor.commands.setTextSelection({ from: sections[1]!.from, to: sections[1]!.to });
    const captured = await captureWorldPlanEditTarget(worldState(first.state));
    const anchor = captured.request.selection_anchor!;
    expect(anchor.section?.id).toBe(sections[1]!.id);
    expect(captured.request.selected_text).toContain(SECTION_MARKER);
    expect(captured.request.selected_text).toContain("**watcher**");
    first.editor.destroy();
    const remounted = mountedState(source);
    const current = worldState(remounted.state);
    const restored = await restoreWorldPlanSelection(anchor, captured.request.draft_sha256,
      await sha256Hex(captured.request.selected_text), {
        worldId: captured.request.world_id, documentId: captured.request.document_id,
        baseRevision: captured.request.base_revision, baseContentSha256: captured.request.base_content_sha256,
      }, () => true, () => current);
    expect(restored.request.selection_anchor).toEqual(anchor);
    expect(restored.sectionTarget?.protectedInventory.map((entry) => entry.kind)).toEqual([
      "playable-marker", "graph-reference",
    ]);
    const replacement = captured.request.selected_text.replace("The town regroups.", "The town regroups under lantern light.");
    const admitted = await admitWorldPlanEditProposal(restored, await worldResponseFor(restored, replacement));
    const preview = previewWorldPlanEditProposal(restored, admitted);
    expect(preview.before.markdown).toContain("First heading remains untouched.");
    expect(preview.after.markdown).toContain("The town regroups under lantern light.");
    await applyWorldPlanEditProposal({ captured: restored, admitted, getCurrent: () => current,
      expectedAgentBinding: expectedAgentBinding(), getAgentBinding: matchingAgentBinding });
    const savedMarkdown = tiptapJsonToSemanticMarkdown(remounted.editor.getJSON());
    const reopened = markdownToTiptapDoc(savedMarkdown).doc;
    const reopenedMarkdown = tiptapJsonToSemanticMarkdown(reopened);
    expect(reopenedMarkdown).toContain("First heading remains untouched.");
    expect(reopenedMarkdown.match(/## Mireward/g)).toHaveLength(2);
    expect(reopenedMarkdown).toContain("The town regroups under lantern light.");
    expect(reopenedMarkdown).toContain(SECTION_MARKER);
    expect(reopenedMarkdown).toContain(SECTION_LINK);
    expect(reopenedMarkdown).not.toContain("The town regroups.\n");
  });

  it.each(["section locator", "section apply range"] as const)(
    "refuses an altered %s before changing the mounted editor", async (changed) => {
      const { captured } = await captureWorldSection();
      const anchor = structuredClone(captured.request.selection_anchor!);
      expect(anchor.section).not.toBeNull();
      if (changed === "section locator") {
        anchor.section!.id = anchor.section!.id.replace(/:[1-6]$/, ":6");
      } else {
        anchor.section!.apply_to += 1;
      }
      const remounted = mountedState(WORLD_SECTION_MARKDOWN);
      const current = worldState(remounted.state);
      const beforeSelection = remounted.editor.state.selection.toJSON();
      const beforeDocument = remounted.editor.getJSON();
      await expect(restoreWorldPlanSelection(anchor, captured.request.draft_sha256,
        await sha256Hex(captured.request.selected_text), {
          worldId: captured.request.world_id, documentId: captured.request.document_id,
          baseRevision: captured.request.base_revision, baseContentSha256: captured.request.base_content_sha256,
        }, () => true, () => current)).rejects.toThrow(/Start a fresh edit/);
      expect(remounted.editor.state.selection.toJSON()).toEqual(beforeSelection);
      expect(remounted.editor.getJSON()).toEqual(beforeDocument);
    });

  it("captures a whole heading section with an exact digest and typed protected identities", async () => {
    const { captured } = await captureWorldSection();
    expect(captured.sectionTarget).toBeDefined();
    expect(captured.request.selected_text).toContain(SECTION_MARKER);
    expect(captured.request.selected_text).toContain(SECTION_LINK);
    expect(captured.request.selected_text).toContain("### Recovery");
    expect(captured.request.selected_text).not.toContain("North Road");
    expect(captured.sectionTarget?.protectedInventory.map((entry) => entry.kind)).toEqual([
      "playable-marker",
      "graph-reference",
    ]);
    const response = await worldResponseFor(captured, captured.request.selected_text);
    expect(response.selected_text_sha256).toBe(await sha256Hex(captured.request.selected_text));
    await expect(admitWorldPlanEditProposal(captured, response)).resolves.toMatchObject({
      response,
      canonicalMarkdown: expect.stringContaining(SECTION_MARKER),
    });
  });

  it("preserves section prose marks and quotes after Markdown reload", async () => {
    const { editor, current, captured } = await captureWorldSection();
    const replacement = [
      "## Mireward",
      "",
      SECTION_MARKER,
      "### After the attack",
      "",
      "The **watcher** waits for *a signal*.",
      "",
      "> A voice carries over the water.",
      "",
      `${SECTION_LINK} is present.`,
      "",
      "### Recovery",
      "The town regroups.",
    ].join("\n");
    const admitted = await admitWorldPlanEditProposal(
      captured,
      await worldResponseFor(captured, replacement),
    );
    await applyWorldPlanEditProposal({
      captured,
      admitted,
      getCurrent: () => current,
      expectedAgentBinding: expectedAgentBinding(),
      getAgentBinding: matchingAgentBinding,
    });

    const savedMarkdown = tiptapJsonToSemanticMarkdown(editor.getJSON());
    const reloaded = markdownToTiptapDoc(savedMarkdown);
    const root = reloaded.doc.content ?? [];
    const headingText = (node: JSONContent) => (node.content ?? []).map((child) => child.text ?? "").join("");
    const start = root.findIndex((node) => node.type === "heading" && headingText(node) === "Mireward");
    const end = root.findIndex((node, index) => index > start && node.type === "heading" && headingText(node) === "North Road");
    expect(start).toBeGreaterThanOrEqual(0);
    expect(end).toBeGreaterThan(start);
    const reloadedSection = root.slice(start, end);
    expect(tiptapJsonToSemanticMarkdown({ type: "doc", content: reloadedSection })).toBe(admitted.canonicalMarkdown);

    let bold = false;
    let italic = false;
    let quote = false;
    const inspect = (node: JSONContent) => {
      bold ||= Boolean(node.marks?.some((mark) => mark.type === "bold"));
      italic ||= Boolean(node.marks?.some((mark) => mark.type === "italic"));
      quote ||= node.type === "blockquote";
      node.content?.forEach(inspect);
    };
    reloadedSection.forEach(inspect);
    expect(bold).toBe(true);
    expect(italic).toBe(true);
    expect(quote).toBe(true);
  });

  it("rejects selected-section semantic drift before mutating the mounted editor", async () => {
    const { editor, current, captured } = await captureWorldSection();
    const admitted = await admitWorldPlanEditProposal(
      captured,
      await worldResponseFor(captured, captured.request.selected_text),
    );
    admitted.content = [
      ...admitted.content,
      { type: "paragraph", content: [{ type: "text", text: "Unreviewed drift." }] },
    ];
    const before = editor.getJSON();

    await expect(applyWorldPlanEditProposal({
      captured,
      admitted,
      getCurrent: () => current,
      expectedAgentBinding: expectedAgentBinding(),
      getAgentBinding: matchingAgentBinding,
    })).rejects.toThrow(/reviewed World Plan edit changed after it was prepared/);
    expect(editor.getJSON()).toEqual(before);
  });

  it.each([
    ["changed marker", (selected: string) => selected.replace("scene:town-breathes", "scene:invented")],
    ["removed marker", (selected: string) => selected.replace(`${SECTION_MARKER}\n`, "")],
    ["duplicated reference", (selected: string) => `${selected}\n\n${SECTION_LINK}`],
    ["moved reference to another heading", (selected: string) => selected
      .replace(`${SECTION_LINK} is present.`, "Lysandra is present.")
      .replace("### Recovery\n", `### Recovery\n\n${SECTION_LINK} is present.\n`)],
    ["moved marker to another heading", (selected: string) => selected
      .replace(`${SECTION_MARKER}\n`, "")
      .replace("### Recovery", `${SECTION_MARKER}\n### Recovery`)],
  ] as const)("rejects a section proposal with a %s", async (_label, mutate) => {
    const { captured } = await captureWorldSection();
    const response = await worldResponseFor(captured, mutate(captured.request.selected_text));
    await expect(admitWorldPlanEditProposal(captured, response)).rejects.toThrow();
  });

  it("keeps protected markup strict for arbitrary World text selections", async () => {
    const { editor, state } = mountedState(WORLD_SECTION_MARKDOWN);
    let paragraphFrom = -1;
    let paragraphSize = 0;
    editor.state.doc.descendants((node, position) => {
      if (node.type.name === "paragraph" && node.textContent.includes("is present.")) {
        paragraphFrom = position;
        paragraphSize = node.nodeSize;
      }
    });
    expect(paragraphFrom).toBeGreaterThan(0);
    editor.commands.setTextSelection({ from: paragraphFrom + 1, to: paragraphFrom + paragraphSize - 1 });
    const current = worldState(state);
    const captured = await captureWorldPlanEditTarget(current, () => current);
    expect(captured.sectionTarget).toBeUndefined();
    const response = await worldResponseFor(captured, `Rewrite this: ${SECTION_LINK}`);
    await expect(admitWorldPlanEditProposal(captured, response)).rejects.toThrow(/unsupported markup/);
  });

  it("refuses duplicate ambiguous sections while retaining complete large sections", async () => {
    const duplicate = "# Plan\n\n## Repeated\n\nSame excerpt.\n\n## Repeated\n\nSame excerpt.\n";
    const { editor, state } = mountedState(duplicate);
    const repeatedTargets = planSectionTargets(editor).filter((target) => target.heading === "Repeated");
    expect(repeatedTargets).toHaveLength(2);
    editor.commands.setTextSelection({ from: repeatedTargets[1]!.from, to: repeatedTargets[1]!.to });
    await expect(captureWorldPlanEditTarget(worldState(state))).rejects.toThrow(/unique exact location/);

    const oversized = `# Plan\n\n## Large\n\n${"Long section prose. ".repeat(500)}\n\n## Small\n\nDone.`;
    const large = await captureWorldSection(oversized, "Large");
    expect(large.captured.request.selected_text.length).toBeGreaterThan(8_000);
  });

  it("captures a selected Session 29 parent Beat without changing its marked draft", async () => {
    const { editor, state } = mountedState(SESSION_29_MARKDOWN);
    const parentBeat = planSectionTargets(editor).find((target) => target.heading === "The Hours They Bought");
    expect(parentBeat).toBeDefined();
    editor.commands.setTextSelection({ from: parentBeat!.from, to: parentBeat!.to });

    const before = editor.getJSON();
    const captured = await captureWorldPlanEditTarget(worldState(state));
    expect(captured.request.target_kind).toBe("replace_selection");
    expect(captured.from).toBe(parentBeat!.from);
    expect(captured.to).toBe(parentBeat!.to);
    expect(captured.request.selected_text).toContain("Mireward After the Attack");
    expect(editor.getJSON()).toEqual(before);
  });

  it("captures a session-free World target and applies only to the same mounted editor", async () => {
    const { editor, state } = mountedState();
    editor.commands.setTextSelection(1);
    const current = worldState(state);
    const captured = await captureWorldPlanEditTarget(current, () => current);
    expect(captured.request).not.toHaveProperty("session");
    expect(captured.request).toMatchObject({
      world_id: "world-1",
      document_id: "plan-1",
      base_revision: 2,
      target_kind: "insert_at_caret",
    });
    const admitted = await admitWorldPlanEditProposal(
      captured,
      await worldResponseFor(captured, "A new World-owned opening."),
    );
    const binding = matchingAgentBinding();
    await applyWorldPlanEditProposal({
      captured,
      admitted,
      getCurrent: () => current,
      expectedAgentBinding: expectedAgentBinding(),
      getAgentBinding: () => binding,
    });
    expect(editor.getText()).toContain("A new World-owned opening.");
  });

  it.each([
    ["plain prose", "A lone watcher keeps vigil above the marsh."],
    [
      "canonical READ-ALOUD content",
      "> [!READ-ALOUD]\n> Three lantern flashes ripple across the eastern ridge. The scouts have returned, but no one will explain their silence. A cold wind threads through the camp, sharp against your skin.",
    ],
  ])("applies %s immediately after the first sentence in the live one-paragraph World Plan", async (_label, fragment) => {
    const source = "Opening image: three lantern flashes ripple across the eastern ridge. The scouts have returned, but no one will explain why they were silent.";
    const { editor, state } = mountedState(source);
    editor.commands.setTextSelection(1 + source.indexOf(".") + 1);
    const current = worldState(state);
    const captured = await captureWorldPlanEditTarget(current, () => current);
    const admitted = await admitWorldPlanEditProposal(
      captured,
      await worldResponseFor(captured, fragment),
    );
    await applyWorldPlanEditProposal({
      captured,
      admitted,
      getCurrent: () => current,
      expectedAgentBinding: expectedAgentBinding(),
      getAgentBinding: matchingAgentBinding,
    });

    const savedMarkdown = tiptapJsonToSemanticMarkdown(editor.getJSON());
    const reimported = markdownToTiptapDoc(savedMarkdown);
    expect(editor.getText()).toContain("Opening image: three lantern flashes ripple across the eastern ridge.");
    expect(editor.getText()).toContain("The scouts have returned, but no one will explain why they were silent.");
    expect(editor.getText()).toContain(fragment.includes("READ-ALOUD") ? "cold wind threads through the camp" : fragment);
    expect(reimported.diagnostics.filter((diagnostic) => diagnostic.level === "warning")).toEqual([]);
    expect(tiptapJsonToSemanticMarkdown(reimported.doc)).toBe(savedMarkdown);
  });

  it("rejects a thread switch during deferred Apply at the final synchronous guard", async () => {
    const { editor, state } = mountedState();
    editor.commands.setTextSelection({ from: 7, to: 14 });
    const current = worldState(state);
    const captured = await captureWorldPlanEditTarget(current, () => current);
    const admitted = await admitWorldPlanEditProposal(
      captured,
      await worldResponseFor(captured, "Agent text"),
    );
    const binding = matchingAgentBinding();
    const originalDigest = crypto.subtle.digest.bind(crypto.subtle);
    let release!: () => void;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    vi.spyOn(crypto.subtle, "digest").mockImplementationOnce(async (...args) => {
      await gate;
      return originalDigest(...args);
    });
    const before = editor.getJSON();
    const apply = applyWorldPlanEditProposal({
      captured,
      admitted,
      getCurrent: () => current,
      expectedAgentBinding: expectedAgentBinding(),
      getAgentBinding: () => binding,
    });
    binding.activeThreadId = "thread-2";
    release();
    await expect(apply).rejects.toThrow(/thread or scope changed/);
    expect(editor.getJSON()).toEqual(before);
  });

  it.each([
    ["null scope", (binding: WorldPlanEditAgentBinding) => { binding.scope = null; }],
    ["foreign scope", (binding: WorldPlanEditAgentBinding) => {
      binding.scope = { ...binding.scope!, campaignId: "foreign-world-plan" };
    }],
    ["null thread", (binding: WorldPlanEditAgentBinding) => { binding.activeThreadId = null; }],
    ["foreign World", (binding: WorldPlanEditAgentBinding) => { binding.verifiedWorldId = "world-2"; }],
  ] as const)("fails closed on %s after awaited Apply preparation", async (_label, replaceBinding) => {
    const { editor, state } = mountedState();
    editor.commands.setTextSelection({ from: 7, to: 14 });
    const current = worldState(state);
    const captured = await captureWorldPlanEditTarget(current, () => current);
    const admitted = await admitWorldPlanEditProposal(
      captured,
      await worldResponseFor(captured, "Agent text"),
    );
    const binding = matchingAgentBinding();
    const originalDigest = crypto.subtle.digest.bind(crypto.subtle);
    let release!: () => void;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    vi.spyOn(crypto.subtle, "digest").mockImplementationOnce(async (...args) => {
      await gate;
      return originalDigest(...args);
    });
    const before = editor.getJSON();
    const apply = applyWorldPlanEditProposal({
      captured,
      admitted,
      getCurrent: () => current,
      expectedAgentBinding: expectedAgentBinding(),
      getAgentBinding: () => binding,
    });
    replaceBinding(binding);
    release();
    await expect(apply).rejects.toThrow(/thread or scope changed/);
    expect(editor.getJSON()).toEqual(before);
  });

  it("rejects a response for another World Plan revision or draft", async () => {
    const { state } = mountedState();
    const current = worldState(state);
    const captured = await captureWorldPlanEditTarget(current, () => current);
    const response = await worldResponseFor(captured, "Valid prose");
    await expect(admitWorldPlanEditProposal(captured, { ...response, world_id: "world-2" })).rejects.toThrow(/captured World Plan/);
    await expect(admitWorldPlanEditProposal(captured, { ...response, base_revision: 3 })).rejects.toThrow(/captured World Plan/);
    await expect(admitWorldPlanEditProposal(captured, { ...response, draft_sha256: BASE_SHA })).rejects.toThrow(/captured World Plan/);
  });

  it.each([
    ["World identity", (current: WorldPlanEditEditorState) => { current.worldId = "world-2"; }],
    ["document identity", (current: WorldPlanEditEditorState) => { current.documentId = "plan-2"; }],
    ["saved revision", (current: WorldPlanEditEditorState) => { current.baseRevision = 3; }],
    ["saved digest", (current: WorldPlanEditEditorState) => { current.baseContentSha256 = "f".repeat(64); }],
    ["draft bytes", (current: WorldPlanEditEditorState) => { current.sourceMarkdown += "\nA new local sentence."; current.draftGeneration += 1; }],
    ["draft generation", (current: WorldPlanEditEditorState) => { current.draftGeneration += 1; }],
    ["selection generation", (current: WorldPlanEditEditorState) => { current.selectionGeneration += 1; }],
    ["save state", (current: WorldPlanEditEditorState) => { current.canEdit = false; }],
    ["editor selection", (_current: WorldPlanEditEditorState, editor: Editor) => { editor.commands.setTextSelection({ from: 8, to: 14 }); }],
    ["editor body", (current: WorldPlanEditEditorState, editor: Editor) => { editor.commands.insertContentAt(2, "Changed "); current.draftGeneration += 1; }],
  ] as const)("rejects stale %s without applying a proposal", async (_label, drift) => {
    const { editor, state } = mountedState();
    editor.commands.setTextSelection({ from: 7, to: 14 });
    const initial = worldState(state);
    const captured = await captureWorldPlanEditTarget(initial, () => initial);
    const admitted = await admitWorldPlanEditProposal(
      captured,
      await worldResponseFor(captured, "Agent text"),
    );
    const current = { ...initial };
    drift(current, editor);
    const before = editor.getJSON();
    await expect(applyWorldPlanEditProposal({
      captured,
      admitted,
      getCurrent: () => current,
      expectedAgentBinding: expectedAgentBinding(),
      getAgentBinding: matchingAgentBinding,
    })).rejects.toThrow();
    expect(editor.getJSON()).toEqual(before);
  });

  it("admits and applies a Scene body with an existing divider while rejecting frontmatter and changed references", async () => {
    const source = "# Plan\n\n<!-- dmb-playable-element:v2 kind=scene id=scene:recovery -->\n### Recovery\n\nAsk [the guide](dmb-node:node:guide) what needs doing.\n\n---\n\n<!-- dmb-playable-element:v2 kind=scene id=scene:later -->\n### Later\n\nUnchanged later scene.\n";
    const { editor, state } = mountedState(source);
    const current: WorldPlanEditEditorState = { ...worldState(state), playableTarget: { kind: "scene", id: "scene:recovery" }, playableTargetGeneration: 1 };
    const captured = await captureWorldPlanEditTarget(current, () => current);
    const key = "00000000-0000-4000-8000-000000000002";
    const replacement = captured.request.target_body_markdown! + "\nGM reminder: Invite a recovery priority.\n";
    const frontmatter = await worldResponseFor(captured, "---\ntitle: hidden\n---\n" + replacement, key);
    await expect(admitWorldPlanEditProposal(captured, frontmatter, key)).rejects.toThrow(/unsupported markup/);
    const changedReference = await worldResponseFor(captured, replacement.replace("node:guide", "node:other"), key);
    await expect(admitWorldPlanEditProposal(captured, changedReference, key)).rejects.toThrow(/protected card-body link/);
    const admitted = await admitWorldPlanEditProposal(captured, await worldResponseFor(captured, replacement, key), key);
    await applyWorldPlanEditProposal({ captured, admitted, getCurrent: () => current, expectedAgentBinding: expectedAgentBinding(), getAgentBinding: matchingAgentBinding });
    const saved = tiptapJsonToSemanticMarkdown(editor.getJSON());
    expect(saved).toContain("Ask [the guide](dmb-node:node:guide) what needs doing.\n\n---\n\nGM reminder: Invite a recovery priority.");
    expect(saved).toContain("id=scene:later");
    expect(saved).toContain("Unchanged later scene.");
    expect(state.sourceMarkdown).toBe(source);
    expect(tiptapJsonToSemanticMarkdown(markdownToTiptapDoc(saved).doc)).toBe(saved);
  });

  it("reviews and applies only one Option body, then saves and freshly reopens with its edges and references intact", async () => {
    const sourceMarkdown = [
      "# Plan",
      "",
      "<!-- dmb-playable-element:v2 kind=beat id=beat:approach beat_kind=spine -->",
      "## Approach",
      "The party reaches the gate.",
      "",
      "<!-- dmb-playable-element:v2 kind=choice id=choice:route -->",
      "### Route",
      "Choose a path.",
      "",
      "<!-- dmb-playable-element:v2 kind=option id=option:explore activates=beat:arrival -->",
      "- Explore [Aldric](dmb-node:node:captain-lysandra-ironveil) at dusk.",
      "",
      "<!-- dmb-playable-element:v2 kind=option id=option:wait suppresses=beat:arrival -->",
      "- Wait by the gate.",
      "",
      "<!-- dmb-playable-element:v2 kind=beat id=beat:arrival beat_kind=optional -->",
      "## Arrival",
      "A guide appears.",
      "",
    ].join("\n");
    const { editor, state } = mountedState(sourceMarkdown);
    const originalSavedMarkdown = state.sourceMarkdown;
    const current: WorldPlanEditEditorState = {
      ...worldState(state),
      playableTarget: { kind: "option", id: "option:explore" },
      playableTargetGeneration: 4,
    };
    const captured = await captureWorldPlanEditTarget(current, () => current);
    expect(captured.request).toMatchObject({
      target_kind: "replace_playable_body",
      selected_text: "",
      playable_target: { kind: "option", id: "option:explore" },
      target_body_markdown: "Explore [Aldric](dmb-node:node:captain-lysandra-ironveil) at dusk.\n",
    });
    const key = "00000000-0000-4000-8000-000000000002";
    const changedReference = await worldResponseFor(
      captured,
      "Explore [Someone else](dmb-node:node:different-person) quietly.",
      key,
    );
    await expect(admitWorldPlanEditProposal(captured, changedReference, key)).rejects.toThrow(/protected card-body link/);

    const replacement = "Quietly follow [Aldric](dmb-node:node:captain-lysandra-ironveil) through the gate.";
    const response = await worldResponseFor(captured, replacement, key);
    const admitted = await admitWorldPlanEditProposal(captured, response, key);
    let saveCalls = 0;
    let persistedMarkdown = originalSavedMarkdown;
    const ordinarySave = () => {
      saveCalls += 1;
      persistedMarkdown = tiptapJsonToSemanticMarkdown(editor.getJSON());
    };

    await applyWorldPlanEditProposal({
      captured,
      admitted,
      getCurrent: () => current,
      expectedAgentBinding: expectedAgentBinding(),
      getAgentBinding: matchingAgentBinding,
    });

    expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toContain(
      "- Quietly follow [Aldric](dmb-node:node:captain-lysandra-ironveil) through the gate.",
    );
    expect(state.sourceMarkdown).toBe(originalSavedMarkdown);
    expect(persistedMarkdown).toBe(originalSavedMarkdown);
    expect(saveCalls).toBe(0);

    ordinarySave();
    expect(saveCalls).toBe(1);
    expect(persistedMarkdown).toContain("option:explore activates=beat:arrival");
    expect(persistedMarkdown).toContain("option:wait suppresses=beat:arrival");
    expect(persistedMarkdown).toContain("- Wait by the gate.");
    expect(persistedMarkdown).toContain("[Aldric](dmb-node:node:captain-lysandra-ironveil)");
    expect(persistedMarkdown).toContain("- Quietly follow [Aldric](dmb-node:node:captain-lysandra-ironveil) through the gate.");
    const reopened = markdownToTiptapDoc(persistedMarkdown);
    expect(reopened.diagnostics.filter((diagnostic) => diagnostic.level === "warning")).toEqual([]);
    const reopenedElement = document.createElement("div");
    document.body.appendChild(reopenedElement);
    const reopenedEditor = new Editor({
      element: reopenedElement,
      extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,
      content: reopened.doc,
    });
    editors.push(reopenedEditor);
    const reopenedTarget = await resolvePlayableBodyTarget(reopenedEditor, { kind: "option", id: "option:explore" });
    expect(reopenedTarget.targetBodyMarkdown).toBe(`${admitted.canonicalMarkdown}`);
    expect(reopenedTarget.targetBodySha256).toBe(await sha256Hex(admitted.canonicalMarkdown));
    expect(reopenedTarget.targetBodySha256).not.toBe(captured.playableBodyTarget?.targetBodySha256);
  });
});


it("captures the full live Plan without old endpoint character caps",async()=>{
  const markdown="# Plan\n\n"+"A complete author paragraph. ".repeat(3500);
  const {editor,state}=mountedState(markdown);editor.commands.setTextSelection(5);
  const current=worldState(state);
  const {capture,target}=await captureWorldPlanAuthoringTarget(current,()=>current,{
    idempotencyKey:"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    conversationId:"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",pointerRevision:3,
  });
  expect(capture.draft_markdown.length).toBeGreaterThan(80_000);
  expect(capture.draft_markdown).toBe(target.request.draft_markdown);
  expect(capture.editor_json).toBe(JSON.stringify(editor.getJSON()));
  expect(capture.selection_json).toBe(JSON.stringify(editor.state.selection.toJSON()));
  expect(capture.from).toBe(editor.state.selection.from);expect(capture.to).toBe(editor.state.selection.to);
  expect(capture.expected_pointer_revision).toBe(3);expect(capture.draft_generation).toBe(current.draftGeneration);
});

it('refuses a generation change during the final authoring hashes without changing the editor',async()=>{
  const {editor,state}=mountedState();const current=worldState(state),before=editor.getJSON();let reads=0;
  await expect(captureWorldPlanAuthoringTarget(current,()=>++reads===1?current:{...current,draftGeneration:current.draftGeneration+1},{
    idempotencyKey:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',conversationId:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',pointerRevision:1,
  })).rejects.toThrow(/changed during capture/);
  expect(editor.getJSON()).toEqual(before);
});

it('captures the typed current scene body with its complete editor and directional selection',async()=>{
  const scene='<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->\n## Arrival\nOriginal prose.\n';
  const {editor,state}=mountedState(scene);
  const current={...worldState(state),currentSceneTarget:{kind:'scene' as const,id:'scene:arrival'}};
  const {capture}=await captureWorldPlanAuthoringTarget(current,()=>current,{
    idempotencyKey:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',conversationId:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',pointerRevision:1,
  });
  expect(capture.target_kind).toBe('replace_playable_body');
  expect(capture.playable_target).toMatchObject({kind:'scene',id:'scene:arrival',marker_grammar_version:'v1',body_markdown:'Original prose.\n'});
  expect(capture.selection_json).toBe(JSON.stringify(editor.state.selection.toJSON()));
});


const authoringIdentity={idempotencyKey:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  conversationId:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',pointerRevision:1};

it('restores a directional selection after reload without replacing document bytes',async()=>{
  const {editor,state}=mountedState('# Plan\n\nOpening frame');
  editor.view.dispatch(editor.state.tr.setSelection(TextSelection.create(editor.state.doc,15,10)));
  let current=worldState(state);
  const {capture}=await captureWorldPlanAuthoringTarget(current,()=>current,authoringIdentity);
  editor.commands.setTextSelection(1);
  current={...current,draftGeneration:12,selectionGeneration:18};
  const before=editor.getJSON();
  const restored=await restorePlanAuthoringTarget(capture,current,()=>current,authoringIdentity);
  expect(editor.getJSON()).toEqual(before);
  expect(editor.state.selection.anchor).toBe(15);expect(editor.state.selection.head).toBe(10);
  expect(restored.capture.draft_generation).toBe(12);expect(restored.capture.selection_generation).toBe(18);
  expect(restored.capture.draft_sha256).toBe(capture.draft_sha256);
});

it.each(['document','basis','draft'])('refuses restoring a changed %s without overwriting it',async change=>{
  const {editor,state}=mountedState();let current=worldState(state);
  const {capture}=await captureWorldPlanAuthoringTarget(current,()=>current,authoringIdentity);
  if(change==='document')current={...current,documentId:'another-plan'};
  if(change==='basis')current={...current,baseRevision:3};
  if(change==='draft')editor.commands.insertContent('Newer author typing');
  const before=editor.getJSON(),selection=editor.state.selection.toJSON();
  await expect(restorePlanAuthoringTarget(capture,current,()=>current,authoringIdentity)).rejects.toThrow(/page changed/);
  expect(editor.getJSON()).toEqual(before);expect(editor.state.selection.toJSON()).toEqual(selection);
});

it('seals the real apply result without changing the mounted draft, then applies identical bytes',async()=>{
  const {editor,state}=mountedState('---\ntitle: Plan\n---\n\n# Plan\n\nOpening frame');
  editor.commands.setTextSelection({from:10,to:15});const current=worldState(state);
  const {target}=await captureWorldPlanAuthoringTarget(current,()=>current,authoringIdentity);
  const before=editor.getJSON(),selection=editor.state.selection.toJSON();
  const prepared=await preparePlanAuthoringApplication(target,'A revised passage.', 'action-1',()=>current,
    expectedAgentBinding(),matchingAgentBinding);
  expect(editor.getJSON()).toEqual(before);expect(editor.state.selection.toJSON()).toEqual(selection);
  expect(prepared.afterMarkdown).toContain('title: Plan');
  expect(prepared.afterEditorSha256).toBe(await sha256Hex(prepared.afterEditorJson));
  expect(prepared.afterDraftSha256).toBe(await sha256Hex(prepared.afterMarkdown));
  await applyWorldPlanEditProposal({captured:target,admitted:prepared.admitted,getCurrent:()=>current,
    expectedAgentBinding:expectedAgentBinding(),getAgentBinding:matchingAgentBinding});
  expect(JSON.stringify(editor.getJSON())).toBe(prepared.afterEditorJson);
  expect(preserveLeadingYamlFrontmatter(state.sourceMarkdown,tiptapJsonToSemanticMarkdown(editor.getJSON())))
    .toBe(prepared.afterMarkdown);
});

it('preparation refuses retired conversation authority without changing the mounted draft',async()=>{
  const {editor,state}=mountedState();const current=worldState(state);
  const {target}=await captureWorldPlanAuthoringTarget(current,()=>current,authoringIdentity);
  const before=editor.getJSON();
  await expect(preparePlanAuthoringApplication(target,'Revised passage.','action-1',()=>current,
    expectedAgentBinding(),()=>({...matchingAgentBinding(),mounted:false}))).rejects.toThrow();
  expect(editor.getJSON()).toEqual(before);
});


it.each(["sibling", "body"])("captures, reviews, applies and reopens a Scene with an ordinary table in its %s", async (placement) => {
  const table = "| Lead | Next step |\n| --- | --- |\n| A repair | Ask the smith (optional). |";
  const source = [
    "# Preparation only", "",
    "<!-- dmb-playable-element:v2 kind=scene id=scene:arrival -->",
    "### Arrival", "", "Meet the residents.", "",
    ...(placement === "sibling" ? [table, ""] : []),
    "<!-- dmb-playable-element:v2 kind=scene id=scene:descent -->",
    "### Descent", "", "Ask [the guide](dmb-node:node:guide) about the guardian.", "",
    ...(placement === "body" ? [table, ""] : []),
    "<!-- dmb-playable-element:v2 kind=scene id=scene:later -->",
    "### Later", "", "**Unplayed** aftermath.", "",
  ].join("\n");
  const { editor, state } = mountedState(source);
  const current: WorldPlanEditEditorState = {
    ...worldState(state), playableTarget: { kind: "scene", id: "scene:descent" }, playableTargetGeneration: 1,
  };
  const before = editor.getJSON();
  const selection = editor.state.selection.toJSON();
  const captured = await captureWorldPlanEditTarget(current, () => current);
  expect(editor.getJSON()).toEqual(before);
  expect(editor.state.selection.toJSON()).toEqual(selection);
  const key = "00000000-0000-4000-8000-000000000002";
  const replacement = captured.request.target_body_markdown! + "\nProposed possibility: offer a peaceful departure.\n";
  const admitted = await admitWorldPlanEditProposal(captured, await worldResponseFor(captured, replacement, key), key);
  expect(editor.getJSON()).toEqual(before);
  await applyWorldPlanEditProposal({ captured, admitted, getCurrent: () => current,
    expectedAgentBinding: expectedAgentBinding(), getAgentBinding: matchingAgentBinding });
  expect(state.sourceMarkdown).toBe(source);
  const saved = tiptapJsonToSemanticMarkdown(editor.getJSON());
  expect(saved).toContain("| Lead | Next step |");
  expect(saved).toContain("**Unplayed** aftermath.");
  expect(saved).toContain("[the guide](dmb-node:node:guide)");
  expect(saved).toContain("id=scene:arrival");
  expect(saved).toContain("id=scene:later");
  const reopened = mountedState(saved).editor;
  expect(tiptapJsonToSemanticMarkdown(reopened.getJSON())).toBe(saved);
  const target = await resolvePlayableBodyTarget(reopened, { kind: "scene", id: "scene:descent" });
  expect(target.targetBodyMarkdown).toBe(admitted.canonicalMarkdown);
  expect(target.targetBodyMarkdown.includes("| Lead | Next step |")).toBe(placement === "body");
});
