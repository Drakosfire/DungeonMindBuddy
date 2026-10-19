import type { PlaySceneEditRecord, PlaySceneEditRequest } from "../../api/playSceneEditApi";
import type { PlayRunContent } from "../playRunContentTypes";
import { samePlayRunContentOrigin } from "../content/playRunContentProtocol";
import { contentSha256 } from "../playRunEffectiveContent";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";

export interface PlaySceneEditCapture { worldId: string; runId: string; request: Omit<PlaySceneEditRequest, "instruction">; markdown: string }
export interface PlaySceneEditBridge {
  capture: () => PlaySceneEditCapture;
  matches: (record: PlaySceneEditRecord) => boolean;
  apply: (record: PlaySceneEditRecord) => Promise<void>;
}
export interface PlaySceneEditorState {
  content: PlayRunContent; runRevision: number; sceneId: string | null; clean: boolean; allowed: boolean;
  draftMarkdown: string; applyReviewed: (markdown: string, revision: number) => void; remount: () => void;
}
export function createPlaySceneEditBridge(getCurrent: () => PlaySceneEditorState): PlaySceneEditBridge {
  const capture = (): PlaySceneEditCapture => {
    const s = getCurrent();
    if (!s.allowed || !s.clean || !s.sceneId || s.draftMarkdown !== s.content.markdown) throw new Error("Save this scene and its notes before asking Buddy to edit it.");
    return { worldId: s.content.world_id, runId: s.content.run_id, markdown: s.content.markdown,
      request: { schema_version: "dmb_play_scene_edit_request_v1", run_revision: s.runRevision, scene_id: s.sceneId,
        content_basis: { edition_revision: s.content.edition_revision, edition_revision_id: s.content.edition_revision_id, content_sha256: s.content.content_sha256 } } };
  };
  const matches = (record: PlaySceneEditRecord) => {
    try {
      const now = capture(); const basis = record.basis;
      return record.status === "ready" && record.world_id === now.worldId && record.run_id === now.runId
        && basis.scene_id === now.request.scene_id && basis.run_revision === now.request.run_revision
        && basis.content_basis.edition_revision === now.request.content_basis.edition_revision
        && basis.content_basis.edition_revision_id === now.request.content_basis.edition_revision_id
        && basis.content_basis.content_sha256 === now.request.content_basis.content_sha256
        && samePlayRunContentOrigin(basis.origin, getCurrent().content.origin);
    } catch { return false; }
  };
  return { capture, matches, async apply(record) {
    if (!matches(record) || !record.result) throw new Error("This scene, its notes or saved copy changed. Ask Buddy for a fresh proposal.");
    const start = capture(); const r = record.result; const bytes = new TextEncoder().encode(start.markdown);
    if (r.body_end_utf8 > bytes.length) throw new Error("The proposed scene range is invalid.");
    const decode = (value: Uint8Array) => new TextDecoder("utf-8", { fatal: true }).decode(value);
    const before = decode(bytes.slice(r.body_start_utf8, r.body_end_utf8));
    const candidate = decode(bytes.slice(0, r.body_start_utf8)) + r.replacement_markdown + decode(bytes.slice(r.body_end_utf8));
    if (before !== r.before_markdown || candidate !== r.candidate_markdown || await contentSha256(candidate) !== r.candidate_sha256) throw new Error("The proposed scene does not match its exact Before/After review.");
    const diagnostics = markdownToTiptapDoc(candidate).diagnostics.filter(item => item.level === "warning");
    if (diagnostics.length) throw new Error("The shared editor cannot preserve this proposal safely. Ask for supported Markdown.");
    if (!matches(record) || capture().markdown !== start.markdown) throw new Error("The session changed while checking this proposal.");
    getCurrent().applyReviewed(candidate, start.request.run_revision);
    getCurrent().remount();
  } };
}
