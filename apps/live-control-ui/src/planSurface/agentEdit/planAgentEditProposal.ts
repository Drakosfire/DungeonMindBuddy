import { Editor, type JSONContent } from "@tiptap/core";

import type {
  PlanDocumentEditProposalRequest,
  PlanDocumentEditProposalResponse,
  WorldPlanDocumentEditProposalRequest,
  WorldPlanDocumentEditProposalResponse,
} from "../../api/types";
import { tiptapJsonToSemanticMarkdown } from "../../tiptap/markdown/calloutMarkdown";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import { semanticMarkdownSerializationDiagnostics } from "../../tiptap/markdown/semanticMarkdownSafety";
import { preserveLeadingYamlFrontmatter } from "../../tiptap/markdown/stripLeadingYamlFrontmatter";
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from "../../tiptap/MarkdownEditorCore";

export interface PlanEditEditorState {
  editor: Editor | null;
  documentId: string;
  worldId: string | null;
  session: number;
  baseRevision: number | null;
  baseContentSha256: string | null;
  sourceMarkdown: string;
  canEdit: boolean;
}

export interface CapturedPlanEditTarget {
  editor: Editor;
  request: Omit<PlanDocumentEditProposalRequest, "instruction" | "conversation_history">;
  from: number;
  to: number;
  editorJson: string;
  selectionJson: string;
  wholeBulletItem?: {
    listFrom: number;
    listTo: number;
    precedingItems: JSONContent[];
    followingItems: JSONContent[];
  };
}

export interface AdmittedPlanEditProposal {
  response: PlanDocumentEditProposalResponse;
  content: JSONContent[];
  canonicalMarkdown: string;
}

export interface PlanEditBridge {
  capture: () => Promise<CapturedPlanEditTarget>;
  apply: (captured: CapturedPlanEditTarget, admitted: AdmittedPlanEditProposal) => Promise<void>;
}

export interface WorldPlanEditEditorState {
  editor: Editor | null;
  documentId: string | null;
  worldId: string | null;
  baseRevision: number | null;
  baseContentSha256: string | null;
  sourceMarkdown: string;
  draftGeneration: number;
  selectionGeneration: number;
  canEdit: boolean;
}

export interface CapturedWorldPlanEditTarget {
  editor: Editor;
  request: Omit<WorldPlanDocumentEditProposalRequest, "instruction" | "conversation_history">;
  from: number;
  to: number;
  editorJson: string;
  selectionJson: string;
  draftGeneration: number;
  selectionGeneration: number;
  wholeBulletItem?: CapturedPlanEditTarget["wholeBulletItem"];
}

export interface AdmittedWorldPlanEditProposal {
  response: WorldPlanDocumentEditProposalResponse;
  content: JSONContent[];
  canonicalMarkdown: string;
}

export interface WorldPlanEditAgentBinding {
  mounted: boolean;
  verifiedWorldId: string | null;
  activeThreadId: string | null;
  scope: {
    campaignId: string;
    surfaceId: string | null;
    sessionNumber: number | null;
    documentId: string | null;
  } | null;
}

export interface ExpectedWorldPlanEditAgentBinding {
  worldId: string;
  documentId: string;
  threadId: string;
  namespace: string;
}

export interface WorldPlanEditBridge {
  capture: () => Promise<CapturedWorldPlanEditTarget>;
  apply: (
    captured: CapturedWorldPlanEditTarget,
    admitted: AdmittedWorldPlanEditProposal,
    expectedAgentBinding: ExpectedWorldPlanEditAgentBinding,
    getAgentBinding: () => WorldPlanEditAgentBinding,
  ) => Promise<void>;
}

export class PlanEditGuardError extends Error {}

async function sha256(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function currentEditor(input: PlanEditEditorState): Editor {
  if (!input.canEdit || !input.editor || input.editor.isDestroyed) {
    throw new PlanEditGuardError("Unlock the mounted Plan editor before composing an edit.");
  }
  if (!input.worldId || !input.documentId || input.baseRevision == null || !input.baseContentSha256) {
    throw new PlanEditGuardError("Load an exact managed-World Plan before composing an edit.");
  }
  return input.editor;
}

function currentWorldEditor(input: WorldPlanEditEditorState): Editor {
  if (!input.canEdit || !input.editor || input.editor.isDestroyed) {
    throw new PlanEditGuardError("Unlock the mounted World Plan editor before composing an edit.");
  }
  if (!input.worldId || !input.documentId || input.baseRevision == null || !input.baseContentSha256) {
    throw new PlanEditGuardError("Load an exact saved World Plan before composing an edit.");
  }
  return input.editor;
}

function sameWorldPlanEditorBinding(
  captured: WorldPlanEditEditorState,
  current: WorldPlanEditEditorState,
): boolean {
  return currentWorldEditor(current) === captured.editor
    && current.documentId === captured.documentId
    && current.worldId === captured.worldId
    && current.baseRevision === captured.baseRevision
    && current.baseContentSha256 === captured.baseContentSha256
    && current.sourceMarkdown === captured.sourceMarkdown
    && current.draftGeneration === captured.draftGeneration
    && current.selectionGeneration === captured.selectionGeneration;
}

function assertWorldPlanAgentBinding(
  actual: WorldPlanEditAgentBinding,
  expected: ExpectedWorldPlanEditAgentBinding,
): void {
  if (!actual.mounted
    || actual.verifiedWorldId !== expected.worldId
    || actual.activeThreadId !== expected.threadId
    || !actual.scope
    || actual.scope.campaignId !== expected.namespace
    || actual.scope.surfaceId !== "plan"
    || actual.scope.sessionNumber !== null
    || actual.scope.documentId !== expected.documentId) {
    throw new PlanEditGuardError("World Plan Agent thread or scope changed. Compose again in the current Plan.");
  }
}

function wholeBulletItemSelection(editor: Editor, from: number, to: number, selectedText: string):
  CapturedPlanEditTarget["wholeBulletItem"] {
  if (from === to) return undefined;
  const end = editor.state.doc.resolve(to);
  for (let depth = end.depth; depth >= 2; depth -= 1) {
    if (end.node(depth).type.name !== "listItem" || end.node(depth - 1).type.name !== "bulletList") continue;
    // Browser text selection can include only the separator before an item
    // plus its text. It is still the same whole-item target; preserving the
    // old list shell would leave a blank bullet after block replacement.
    if (end.node(depth).textContent.trim() !== selectedText.trim()) return undefined;
    const listDepth = depth - 1;
    const list = end.node(listDepth);
    const selectedIndex = end.index(listDepth);
    const items = list.content.content;
    return {
      listFrom: end.before(listDepth),
      listTo: end.after(listDepth),
      precedingItems: items.slice(0, selectedIndex).map((item) => item.toJSON()),
      followingItems: items.slice(selectedIndex + 1).map((item) => item.toJSON()),
    };
  }
  return undefined;
}

export async function capturePlanEditTarget(input: PlanEditEditorState): Promise<CapturedPlanEditTarget> {
  const editor = currentEditor(input);
  const { from, to } = editor.state.selection;
  const selectedText = editor.state.doc.textBetween(from, to, "\n");
  const targetKind = from === to ? "insert_at_caret" : "replace_selection";
  if (targetKind === "replace_selection" && !selectedText.trim()) {
    throw new PlanEditGuardError("Select text or place a caret in the Plan editor.");
  }
  const json = editor.getJSON();
  const editorJson = JSON.stringify(json);
  const selectionJson = JSON.stringify(editor.state.selection.toJSON());
  const wholeBulletItem = wholeBulletItemSelection(editor, from, to, selectedText);
  if (markdownToTiptapDoc(input.sourceMarkdown).diagnostics.some((diagnostic) => diagnostic.level === "warning")) {
    throw new PlanEditGuardError("This Plan source cannot round-trip safely; resolve its Markdown warnings first.");
  }
  if (semanticMarkdownSerializationDiagnostics(json).length) {
    throw new PlanEditGuardError("This Plan draft contains content that cannot round-trip safely as Markdown.");
  }
  const draftMarkdown = preserveLeadingYamlFrontmatter(
    input.sourceMarkdown,
    tiptapJsonToSemanticMarkdown(json),
  );
  if (draftMarkdown.length > 80_000 || selectedText.length > 8_000) {
    throw new PlanEditGuardError("The selected Plan material is too large for one proposal.");
  }
  const draftSha256 = await sha256(draftMarkdown);
  // Hashing yields to local edits and navigation. Never combine a pre-hash
  // body with a post-hash selection, or return an already-stale target.
  if (
    editor.isDestroyed
    || JSON.stringify(editor.getJSON()) !== editorJson
    || JSON.stringify(editor.state.selection.toJSON()) !== selectionJson
  ) {
    throw new PlanEditGuardError("Plan or selection changed while capturing the target. Capture again.");
  }
  return {
    editor,
    request: {
      document_id: input.documentId,
      world_id: input.worldId!,
      session: input.session,
      base_revision: input.baseRevision!,
      base_content_sha256: input.baseContentSha256!,
      draft_markdown: draftMarkdown,
      draft_sha256: draftSha256,
      target_kind: targetKind,
      selected_text: selectedText,
    },
    from,
    to,
    editorJson,
    selectionJson,
    wholeBulletItem,
  };
}

export async function captureWorldPlanEditTarget(
  input: WorldPlanEditEditorState,
  getCurrent: () => WorldPlanEditEditorState = () => input,
): Promise<CapturedWorldPlanEditTarget> {
  const editor = currentWorldEditor(input);
  const { from, to } = editor.state.selection;
  const selectedText = editor.state.doc.textBetween(from, to, "\n");
  const targetKind = from === to ? "insert_at_caret" : "replace_selection";
  if (targetKind === "replace_selection" && !selectedText.trim()) {
    throw new PlanEditGuardError("Select text or place a caret in the Plan editor.");
  }
  const json = editor.getJSON();
  const editorJson = JSON.stringify(json);
  const selectionJson = JSON.stringify(editor.state.selection.toJSON());
  const wholeBulletItem = wholeBulletItemSelection(editor, from, to, selectedText);
  if (markdownToTiptapDoc(input.sourceMarkdown).diagnostics.some((diagnostic) => diagnostic.level === "warning")) {
    throw new PlanEditGuardError("This Plan source cannot round-trip safely; resolve its Markdown warnings first.");
  }
  if (semanticMarkdownSerializationDiagnostics(json).length) {
    throw new PlanEditGuardError("This Plan draft contains content that cannot round-trip safely as Markdown.");
  }
  const draftMarkdown = preserveLeadingYamlFrontmatter(
    input.sourceMarkdown,
    tiptapJsonToSemanticMarkdown(json),
  );
  if (draftMarkdown.length > 80_000 || selectedText.length > 8_000) {
    throw new PlanEditGuardError("The selected Plan material is too large for one proposal.");
  }
  const draftSha256 = await sha256(draftMarkdown);
  const live = getCurrent();
  if (!sameWorldPlanEditorBinding(input, live)
    || JSON.stringify(editor.getJSON()) !== editorJson
    || JSON.stringify(editor.state.selection.toJSON()) !== selectionJson) {
    throw new PlanEditGuardError("World Plan or selection changed while capturing the target. Capture again.");
  }
  return {
    editor,
    request: {
      document_id: input.documentId!,
      world_id: input.worldId!,
      base_revision: input.baseRevision!,
      base_content_sha256: input.baseContentSha256!,
      draft_markdown: draftMarkdown,
      draft_sha256: draftSha256,
      target_kind: targetKind,
      selected_text: selectedText,
    },
    from,
    to,
    editorJson,
    selectionJson,
    draftGeneration: input.draftGeneration,
    selectionGeneration: input.selectionGeneration,
    wholeBulletItem,
  };
}

function insertionForTarget(
  captured: Pick<CapturedPlanEditTarget, "editor" | "from" | "to" | "wholeBulletItem">,
  content: JSONContent[],
): {
  range: { from: number; to: number };
  content: JSONContent[];
} {
  const item = captured.wholeBulletItem;
  if (!item) {
    const start = captured.editor.state.doc.resolve(captured.from);
    const end = captured.editor.state.doc.resolve(captured.to);
    const paragraph = content.length === 1 && content[0]?.type === "paragraph" ? content[0] : null;
    if (
      paragraph
      && start.sameParent(end)
      && start.parent.type.name === "paragraph"
      && captured.from !== captured.to
    ) {
      return {
        range: { from: captured.from, to: captured.to },
        content: paragraph.content ?? [],
      };
    }
    if (captured.from === captured.to && start.parent.type.name === "paragraph") {
      // Inserting block content splits the current paragraph. Whitespace that
      // sat at the caret becomes leading/trailing whitespace on the new edge
      // paragraphs, which Markdown import normalizes away. Consume only that
      // adjacent whitespace so the simulated and mounted results are already
      // canonical before the loss-prevention round-trip check.
      const trailingWhitespace = start.nodeBefore?.isText
        ? start.nodeBefore.text?.match(/\s+$/u)?.[0] ?? ""
        : "";
      const leadingWhitespace = start.nodeAfter?.isText
        ? start.nodeAfter.text?.match(/^\s+/u)?.[0] ?? ""
        : "";
      return {
        range: {
          from: captured.from - trailingWhitespace.length,
          to: captured.to + leadingWhitespace.length,
        },
        content,
      };
    }
    return { range: { from: captured.from, to: captured.to }, content };
  }
  const preceding = item.precedingItems.length
    ? [{ type: "bulletList", content: item.precedingItems }]
    : [];
  const following = item.followingItems.length
    ? [{ type: "bulletList", content: item.followingItems }]
    : [];
  return {
    range: { from: item.listFrom, to: item.listTo },
    content: [...preceding, ...content, ...following],
  };
}

function validateFragment(markdown: string): { content: JSONContent[]; canonicalMarkdown: string } {
  if (!markdown.trim() || markdown.length > 12_000) {
    throw new PlanEditGuardError("Agent returned an empty or oversized edit.");
  }
  if (
    /^---\s*$/m.test(markdown)
    || /<\/?[A-Za-z][^>]*>/.test(markdown)
    || /(?:dmb-node:|graphNodeReference|\bnode:[a-z0-9_-]+)/i.test(markdown)
    || /\[[^\]]+\]\((?:file:|\.{1,2}\/|\/)/i.test(markdown)
    || /(?:^|\n)\s*>\s*\[!(?!READ-ALOUD\]|GM-NOTE\]|DECISION-CONSEQUENCE\])[^\]]+\]/i.test(markdown)
  ) {
    throw new PlanEditGuardError("Agent proposed unsupported markup, a path, or a graph identity.");
  }
  const parsed = markdownToTiptapDoc(markdown);
  const importWarning = parsed.diagnostics.find((diagnostic) => diagnostic.level === "warning");
  if (importWarning) {
    throw new PlanEditGuardError(`Agent proposed Markdown the Plan editor cannot import safely: ${importWarning.message}`);
  }
  if (semanticMarkdownSerializationDiagnostics(parsed.doc).length) {
    throw new PlanEditGuardError("Agent proposed a component the Plan editor cannot serialize safely.");
  }
  const canonicalMarkdown = tiptapJsonToSemanticMarkdown(parsed.doc);
  const reparsed = markdownToTiptapDoc(canonicalMarkdown);
  if (
    reparsed.diagnostics.some((diagnostic) => diagnostic.level === "warning")
    || JSON.stringify(reparsed.doc) !== JSON.stringify(parsed.doc)
  ) {
    throw new PlanEditGuardError("Agent proposal does not round-trip through Plan Markdown.");
  }
  return { content: parsed.doc.content ?? [], canonicalMarkdown };
}

export async function admitPlanEditProposal(
  captured: CapturedPlanEditTarget,
  response: PlanDocumentEditProposalResponse,
): Promise<AdmittedPlanEditProposal> {
  const request = captured.request;
  if (
    response.schema_version !== "dmb_plan_document_edit_proposal_v1"
    || response.document_id !== request.document_id
    || response.world_id !== request.world_id
    || response.session !== request.session
    || response.base_revision !== request.base_revision
    || response.base_content_sha256 !== request.base_content_sha256
    || response.draft_sha256 !== request.draft_sha256
    || response.target_kind !== request.target_kind
    || response.selected_text_sha256 !== await sha256(request.selected_text)
  ) {
    throw new PlanEditGuardError("Agent proposal does not match the captured Plan target.");
  }
  const fragment = validateFragment(response.replacement_markdown);
  return { response, ...fragment };
}

export async function admitWorldPlanEditProposal(
  captured: CapturedWorldPlanEditTarget,
  response: WorldPlanDocumentEditProposalResponse,
): Promise<AdmittedWorldPlanEditProposal> {
  const request = captured.request;
  if (
    response.schema_version !== "dmb_world_plan_document_edit_proposal_v1"
    || response.document_id !== request.document_id
    || response.world_id !== request.world_id
    || response.base_revision !== request.base_revision
    || response.base_content_sha256 !== request.base_content_sha256
    || response.draft_sha256 !== request.draft_sha256
    || response.target_kind !== request.target_kind
    || response.selected_text_sha256 !== await sha256(request.selected_text)
  ) {
    throw new PlanEditGuardError("Agent proposal does not match the captured World Plan target.");
  }
  const fragment = validateFragment(response.replacement_markdown);
  return { response, ...fragment };
}

export async function applyPlanEditProposal(args: {
  captured: CapturedPlanEditTarget;
  admitted: AdmittedPlanEditProposal;
  current: PlanEditEditorState;
  getCurrent?: () => PlanEditEditorState;
}): Promise<void> {
  const { captured, admitted } = args;
  const editor = currentEditor(args.current);
  const now = await capturePlanEditTarget(args.current);
  const live = args.getCurrent?.() ?? args.current;
  if (
    currentEditor(live) !== editor
    || editor !== captured.editor
    || live.documentId !== captured.request.document_id
    || live.worldId !== captured.request.world_id
    || live.session !== captured.request.session
    || live.baseRevision !== captured.request.base_revision
    || live.baseContentSha256 !== captured.request.base_content_sha256
    || live.sourceMarkdown !== args.current.sourceMarkdown
    || now.request.document_id !== captured.request.document_id
    || now.request.world_id !== captured.request.world_id
    || now.request.session !== captured.request.session
    || now.request.base_revision !== captured.request.base_revision
    || now.request.base_content_sha256 !== captured.request.base_content_sha256
    || now.request.draft_sha256 !== captured.request.draft_sha256
    || now.from !== captured.from
    || now.to !== captured.to
    || now.editorJson !== captured.editorJson
    || now.selectionJson !== captured.selectionJson
    || admitted.response.draft_sha256 !== captured.request.draft_sha256
  ) {
    throw new PlanEditGuardError("Plan or selection changed after the Agent proposal. Compose again.");
  }
  // Check the full resulting document, not only the fragment. Inserting a
  // component inside an existing list or pane can change its parent grammar.
  const simulated = new Editor({
    extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,
    content: editor.getJSON(),
  });
  const insertion = insertionForTarget(captured, admitted.content);
  try {
    if (!simulated.commands.insertContentAt(insertion.range, insertion.content)) {
      throw new PlanEditGuardError("Agent proposal cannot be inserted at this Plan target.");
    }
    const result = simulated.getJSON();
    if (semanticMarkdownSerializationDiagnostics(result).length) {
      throw new PlanEditGuardError("Agent proposal would make the Plan unsafe to save as Markdown.");
    }
    const serialized = tiptapJsonToSemanticMarkdown(result);
    const reimported = markdownToTiptapDoc(serialized);
    if (
      reimported.diagnostics.some((diagnostic) => diagnostic.level === "warning")
      || tiptapJsonToSemanticMarkdown(reimported.doc) !== serialized
    ) {
      throw new PlanEditGuardError("Agent proposal would not round-trip in this Plan location.");
    }
  } finally {
    simulated.destroy();
  }
  // No await separates this final live-state guard from the single mutation.
  if (
    currentEditor(args.getCurrent?.() ?? live) !== editor
    || JSON.stringify(editor.getJSON()) !== captured.editorJson
    || JSON.stringify(editor.state.selection.toJSON()) !== captured.selectionJson
  ) {
    throw new PlanEditGuardError("Plan or selection changed after the Agent proposal. Compose again.");
  }
  if (!editor.commands.insertContentAt(insertion.range, insertion.content)) {
    throw new PlanEditGuardError("The mounted Plan editor could not apply this proposal.");
  }
}

export async function applyWorldPlanEditProposal(args: {
  captured: CapturedWorldPlanEditTarget;
  admitted: AdmittedWorldPlanEditProposal;
  getCurrent: () => WorldPlanEditEditorState;
  expectedAgentBinding: ExpectedWorldPlanEditAgentBinding;
  getAgentBinding: () => WorldPlanEditAgentBinding;
}): Promise<void> {
  const { captured, admitted } = args;
  const initial = args.getCurrent();
  const editor = currentWorldEditor(initial);
  if (editor !== captured.editor) {
    throw new PlanEditGuardError("World Plan changed after the Agent proposal. Compose again.");
  }
  const now = await captureWorldPlanEditTarget(initial, args.getCurrent);
  const live = args.getCurrent();
  if (
    currentWorldEditor(live) !== editor
    || live.documentId !== captured.request.document_id
    || live.worldId !== captured.request.world_id
    || live.baseRevision !== captured.request.base_revision
    || live.baseContentSha256 !== captured.request.base_content_sha256
    || live.sourceMarkdown !== initial.sourceMarkdown
    || live.draftGeneration !== captured.draftGeneration
    || live.selectionGeneration !== captured.selectionGeneration
    || now.request.document_id !== captured.request.document_id
    || now.request.world_id !== captured.request.world_id
    || now.request.base_revision !== captured.request.base_revision
    || now.request.base_content_sha256 !== captured.request.base_content_sha256
    || now.request.draft_sha256 !== captured.request.draft_sha256
    || now.from !== captured.from
    || now.to !== captured.to
    || now.editorJson !== captured.editorJson
    || now.selectionJson !== captured.selectionJson
    || admitted.response.document_id !== captured.request.document_id
    || admitted.response.world_id !== captured.request.world_id
    || admitted.response.draft_sha256 !== captured.request.draft_sha256
  ) {
    throw new PlanEditGuardError("World Plan or selection changed after the Agent proposal. Compose again.");
  }
  const simulated = new Editor({
    extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,
    content: editor.getJSON(),
  });
  const insertion = insertionForTarget(captured, admitted.content);
  try {
    if (!simulated.commands.insertContentAt(insertion.range, insertion.content)) {
      throw new PlanEditGuardError("Agent proposal cannot be inserted at this World Plan target.");
    }
    const result = simulated.getJSON();
    if (semanticMarkdownSerializationDiagnostics(result).length) {
      throw new PlanEditGuardError("Agent proposal would make the Plan unsafe to save as Markdown.");
    }
    const serialized = tiptapJsonToSemanticMarkdown(result);
    const reimported = markdownToTiptapDoc(serialized);
    if (
      reimported.diagnostics.some((diagnostic) => diagnostic.level === "warning")
      || tiptapJsonToSemanticMarkdown(reimported.doc) !== serialized
    ) {
      throw new PlanEditGuardError("Agent proposal would not round-trip in this Plan location.");
    }
  } finally {
    simulated.destroy();
  }

  const finalState = args.getCurrent();
  if (
    currentWorldEditor(finalState) !== editor
    || finalState.documentId !== captured.request.document_id
    || finalState.worldId !== captured.request.world_id
    || finalState.baseRevision !== captured.request.base_revision
    || finalState.baseContentSha256 !== captured.request.base_content_sha256
    || finalState.draftGeneration !== captured.draftGeneration
    || finalState.selectionGeneration !== captured.selectionGeneration
    || JSON.stringify(editor.getJSON()) !== captured.editorJson
    || JSON.stringify(editor.state.selection.toJSON()) !== captured.selectionJson
  ) {
    throw new PlanEditGuardError("World Plan or selection changed after the Agent proposal. Compose again.");
  }
  // This getter reads the current provider scope/thread. Never fall back to the
  // captured binding when the provider reports null or a different scope.
  assertWorldPlanAgentBinding(args.getAgentBinding(), args.expectedAgentBinding);
  if (!editor.commands.insertContentAt(insertion.range, insertion.content)) {
    throw new PlanEditGuardError("The mounted World Plan editor could not apply this proposal.");
  }
}
