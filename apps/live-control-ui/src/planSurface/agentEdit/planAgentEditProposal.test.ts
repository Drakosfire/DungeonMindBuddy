import { Editor } from "@tiptap/core";
import { webcrypto } from "node:crypto";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from "../../tiptap/MarkdownEditorCore";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import { tiptapJsonToSemanticMarkdown } from "../../tiptap/markdown/calloutMarkdown";
import {
  admitWorldPlanEditProposal,
  admitPlanEditProposal,
  applyWorldPlanEditProposal,
  applyPlanEditProposal,
  capturePlanEditTarget,
  captureWorldPlanEditTarget,
  type ExpectedWorldPlanEditAgentBinding,
  type PlanEditEditorState,
  type WorldPlanEditAgentBinding,
  type WorldPlanEditEditorState,
} from "./planAgentEditProposal";

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

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function worldResponseFor(
  captured: Awaited<ReturnType<typeof captureWorldPlanEditTarget>>,
  replacement_markdown: string,
) {
  return {
    schema_version: "dmb_world_plan_document_edit_proposal_v1" as const,
    document_id: captured.request.document_id,
    world_id: captured.request.world_id,
    base_revision: captured.request.base_revision,
    base_content_sha256: captured.request.base_content_sha256,
    draft_sha256: captured.request.draft_sha256,
    target_kind: captured.request.target_kind,
    selected_text_sha256: await sha256Hex(captured.request.selected_text),
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
});
