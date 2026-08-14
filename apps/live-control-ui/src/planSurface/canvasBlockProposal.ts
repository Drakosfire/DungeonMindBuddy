/**
 * Typed canvas callout proposals from Hermes (`dmb_canvas_block_proposal_v1`).
 * Approve applies through TipTap; durable save stays prepare/commit.
 */

import type { Editor } from "@tiptap/core";
import type { CalloutKind } from "../tiptap/markdown/calloutMarkdown";
import { normalizeCalloutKind } from "../tiptap/markdown/calloutMarkdown";

export const CANVAS_BLOCK_PROPOSAL_SCHEMA = "dmb_canvas_block_proposal_v1" as const;

export type CanvasBlockOp = "insert_callout" | "replace_callout";

export interface CanvasBlockLocator {
  afterHeading?: string;
  oldText?: string;
}

export interface CanvasBlockProposal {
  schema: typeof CANVAS_BLOCK_PROPOSAL_SCHEMA;
  documentId: string;
  surfaceId: string;
  op: CanvasBlockOp;
  kind: CalloutKind;
  body: string;
  locator: CanvasBlockLocator;
  previewMarkdown: string;
  expectedContentSha256?: string | null;
  provenanceRefs?: string[];
}

export interface CanvasWorkObjectRequest {
  documentId: string;
  surfaceId: string;
  expectedContentSha256?: string | null;
}

export type ApplyCanvasBlockResult =
  | { ok: true }
  | { ok: false; reason: string };

function bodyParagraphs(body: string): Array<{ type: "paragraph"; content?: Array<{ type: "text"; text: string }> }> {
  const chunks = body.split(/\n\n+/).map((part) => part.trim()).filter(Boolean);
  if (!chunks.length) {
    return [{ type: "paragraph" }];
  }
  return chunks.map((text) => ({
    type: "paragraph" as const,
    content: [{ type: "text" as const, text }],
  }));
}

export function isCanvasBlockProposal(value: unknown): value is CanvasBlockProposal {
  if (!value || typeof value !== "object") return false;
  const row = value as Record<string, unknown>;
  return (
    row.schema === CANVAS_BLOCK_PROPOSAL_SCHEMA
    && typeof row.documentId === "string"
    && typeof row.op === "string"
    && typeof row.kind === "string"
    && typeof row.body === "string"
    && typeof row.previewMarkdown === "string"
    && row.locator != null
    && typeof row.locator === "object"
  );
}

export function canvasBlockProposalsFromMutations(
  mutations: unknown[] | null | undefined,
): CanvasBlockProposal[] {
  if (!Array.isArray(mutations)) return [];
  return mutations.filter(isCanvasBlockProposal);
}

export function applyCanvasBlockProposal(
  editor: Editor,
  proposal: CanvasBlockProposal,
  options: {
    documentId: string;
    currentContentSha256?: string | null;
    /** True when TipTap local state diverges from the admission snapshot Hermes saw. */
    isDirty?: boolean;
  },
): ApplyCanvasBlockResult {
  if (proposal.documentId !== options.documentId) {
    return { ok: false, reason: "Proposal targets a different document." };
  }

  const expected = proposal.expectedContentSha256?.trim() || null;
  if (expected) {
    const current = options.currentContentSha256?.trim() || null;
    // Admission CAS: base content sha of last loaded/saved snapshot.
    if (current && current !== expected) {
      return {
        ok: false,
        reason: "Document changed since Hermes read it. Re-ask after Save or Reload.",
      };
    }
    // Concurrent local edits keep the same base sha — refuse dirty so Approve
    // does not apply against content Hermes did not see.
    if (options.isDirty) {
      return {
        ok: false,
        reason: "Document has unsaved local edits. Save or Reload, then re-ask Hermes.",
      };
    }
  }

  const kind = normalizeCalloutKind(proposal.kind);
  const content = {
    type: "callout",
    attrs: { kind, label: null },
    content: bodyParagraphs(proposal.body),
  };

  if (proposal.op === "replace_callout") {
    const oldText = proposal.locator.oldText?.trim();
    if (!oldText) {
      return { ok: false, reason: "replace_callout requires locator.oldText." };
    }
    const { doc } = editor.state;
    let foundFrom: number | null = null;
    let foundTo: number | null = null;
    doc.descendants((node, pos) => {
      if (foundFrom != null) return false;
      if (node.type.name !== "callout") return;
      const text = node.textContent;
      if (text.includes(oldText) || oldText.includes(text.slice(0, 80))) {
        foundFrom = pos;
        foundTo = pos + node.nodeSize;
        return false;
      }
    });
    if (foundFrom == null || foundTo == null) {
      return { ok: false, reason: "Could not find the callout to replace." };
    }
    const ok = editor
      .chain()
      .focus()
      .command(({ tr, dispatch }) => {
        if (dispatch) {
          tr.replaceWith(foundFrom!, foundTo!, editor.schema.nodeFromJSON(content));
        }
        return true;
      })
      .run();
    return ok ? { ok: true } : { ok: false, reason: "TipTap replace failed." };
  }

  const afterHeading = proposal.locator.afterHeading?.trim();
  if (afterHeading) {
    const { doc } = editor.state;
    let insertPos: number | null = null;
    doc.descendants((node, pos) => {
      if (insertPos != null) return false;
      if (!node.type.name.startsWith("heading")) return;
      if (node.textContent.trim() === afterHeading || node.textContent.includes(afterHeading)) {
        insertPos = pos + node.nodeSize;
        return false;
      }
    });
    if (insertPos == null) {
      // Fall through: insert at cursor / end.
      const ok = editor.chain().focus("end").insertContent(content).run();
      return ok
        ? { ok: true }
        : { ok: false, reason: "Could not find heading; insert at end failed." };
    }
    const ok = editor
      .chain()
      .focus()
      .insertContentAt(insertPos, content)
      .run();
    return ok ? { ok: true } : { ok: false, reason: "TipTap insert after heading failed." };
  }

  const ok = editor.chain().focus("end").insertContent(content).run();
  return ok ? { ok: true } : { ok: false, reason: "TipTap insert failed." };
}

/** Bridge so Ask panel can apply into the live Plan canvas editor. */
export type CanvasBlockApplyBridge = {
  documentId: string;
  getEditor: () => Editor | null;
  getBaseContentSha256: () => string | null;
  isDirty: () => boolean;
  /** Persist local dirty state after a programmatic insert. */
  afterApply?: () => void;
};

let bridge: CanvasBlockApplyBridge | null = null;

export function registerCanvasBlockApplyBridge(next: CanvasBlockApplyBridge | null): void {
  bridge = next;
}

export function getCanvasBlockApplyBridge(): CanvasBlockApplyBridge | null {
  return bridge;
}

export function approveCanvasBlockProposal(proposal: CanvasBlockProposal): ApplyCanvasBlockResult {
  const active = getCanvasBlockApplyBridge();
  if (!active) {
    return { ok: false, reason: "No open Plan canvas editor." };
  }
  if (active.documentId !== proposal.documentId) {
    return { ok: false, reason: "Open a matching Plan document first." };
  }
  const editor = active.getEditor();
  if (!editor) {
    return { ok: false, reason: "Editor is not ready." };
  }
  const result = applyCanvasBlockProposal(editor, proposal, {
    documentId: active.documentId,
    currentContentSha256: active.getBaseContentSha256(),
    isDirty: active.isDirty(),
  });
  if (result.ok) {
    active.afterApply?.();
  }
  return result;
}
