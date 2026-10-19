import { createPlaySceneEditBridge } from "../agentEdit/playSceneEditBridge";
import { usePublishPlaySceneEditBridge } from "../../agentInteraction/WorldAgentConversation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Editor, JSONContent } from "@tiptap/core";
import { PLAYABLE_ELEMENT_ID_HTML_ATTR, PLAYABLE_ELEMENT_KIND_HTML_ATTR } from "../../tiptap/playable/playableElementIdentity";
import { MarkdownEditorCore } from "../../tiptap/MarkdownEditorCore";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import { preserveLeadingYamlFrontmatter, splitLeadingYamlFrontmatter } from "../../tiptap/markdown/stripLeadingYamlFrontmatter";
import { tiptapJsonToSemanticMarkdown } from "../../tiptap/markdown/calloutMarkdown";
import { semanticMarkdownSerializationDiagnostics } from "../../tiptap/markdown/semanticMarkdownSafety";
import { SurfaceContextAction, SurfaceContextStatus } from "../../surfaceInteraction/contextHost";
import { buildSurfaceInteractionIdentity } from "../../surfaceInteraction/surfaceIdentity";
import { PlaySurfaceContext } from "../components/PlaySurfaceContext";
import { usePlayRunContentController } from "./usePlayRunContentController";
import type { PlayRunContent } from "../playRunContentTypes";
import "./playSessionContentEditor.css";

export function PlaySessionContentEditor({
  content,
  currentSceneId,
  originLabel,
  onAcceptedContent,
  onUnsubmittedChange,
  runRevision,
  canPropose = false,
}: {
  content: PlayRunContent;
  runRevision?: number;
  canPropose?: boolean;
  currentSceneId: string | null;
  originLabel: string;
  onAcceptedContent: (content: PlayRunContent) => void;
  onUnsubmittedChange: (hasUnsubmitted: boolean) => void;
}) {
  const controller = usePlayRunContentController(content, onAcceptedContent, onUnsubmittedChange);
  const [open, setOpen] = useState(false);
  const [hasOpened, setHasOpened] = useState(false);
  const [mode, setMode] = useState<"visual" | "markdown">("visual");
  const [editorEpoch, setEditorEpoch] = useState(0);
  const [jumpCount, setJumpCount] = useState(0);
  const editorRef = useRef<Editor | null>(null);
  const split = useMemo(() => splitLeadingYamlFrontmatter(controller.state.draftMarkdown), [controller.state.draftMarkdown]);
  const imported = useMemo(() => markdownToTiptapDoc(controller.state.draftMarkdown), [controller.state.draftMarkdown]);
  const identityKey = `${content.world_id}:${content.run_id}:${content.origin.playable_work_revision_id}:${content.origin.playable_content_sha256}`;
  const sceneEditorState = useRef({ content: controller.state.accepted, runRevision: runRevision ?? content.observed_run_revision,
    sceneId: currentSceneId, clean: !controller.hasUnsubmittedContent, allowed: canPropose,
    draftMarkdown: controller.state.draftMarkdown, applyReviewed: controller.applyReviewed, remount: () => setEditorEpoch(value => value + 1) });
  sceneEditorState.current = { content: controller.state.accepted, runRevision: runRevision ?? content.observed_run_revision,
    sceneId: currentSceneId, clean: !controller.hasUnsubmittedContent, allowed: canPropose,
    draftMarkdown: controller.state.draftMarkdown, applyReviewed: controller.applyReviewed, remount: () => setEditorEpoch(value => value + 1) };
  const sceneEditBridge = useMemo(() => createPlaySceneEditBridge(() => sceneEditorState.current), [identityKey]);
  usePublishPlaySceneEditBridge(sceneEditBridge);
  const surfaceIdentity = buildSurfaceInteractionIdentity({ surfaceId: "play", instanceParts: ["play", content.world_id, content.run_id, content.origin.playable_artifact_id, String(content.origin.playable_revision), content.origin.playable_work_revision_id, content.origin.playable_content_sha256] });

  const diagnostics = useCallback((doc: unknown): string[] => {
    const semantic = semanticMarkdownSerializationDiagnostics(doc).map(item => item.message);
    try {
      const serialized = preserveLeadingYamlFrontmatter(
        controller.state.accepted.markdown,
        tiptapJsonToSemanticMarkdown(doc),
      );
      const importIssues = markdownToTiptapDoc(serialized).diagnostics.filter(item => item.level === "warning").map(item => item.message);
      return [...new Set([...semantic, ...importIssues])];
    } catch (error) {
      return [...new Set([...semantic, error instanceof Error ? error.message : "Markdown could not be serialized safely."])];
    }
  }, [controller.state.accepted.markdown]);

  const updateFromVisual = useCallback((json: JSONContent, _editor: Editor, meta: { programmatic: boolean }) => {
    if (meta.programmatic) return;
    try {
      const body = tiptapJsonToSemanticMarkdown(json);
      const markdown = preserveLeadingYamlFrontmatter(controller.state.accepted.markdown, body);
      controller.changeDraft(markdown, diagnostics(json));
    } catch (error) {
      controller.changeDraft(controller.state.draftMarkdown, [error instanceof Error ? error.message : "Markdown could not be serialized safely."]);
    }
  }, [controller.changeDraft, controller.state.accepted.markdown, controller.state.draftMarkdown, diagnostics]);

  useEffect(() => {
    if (!open || !hasOpened || jumpCount === 0 || !currentSceneId || !editorRef.current) return;
    const editor = editorRef.current;
    let selection: number | null = null;
    editor.state.doc.descendants((node, position) => {
      if (node.type.name === "heading" && node.attrs.playableElementKind === "scene" && node.attrs.playableElementId === currentSceneId) {
        selection = position + 1;
        return false;
      }
      return true;
    });
    if (selection === null) return;
    editor.commands.setTextSelection(selection);
    editor.commands.focus();
    const heading = Array.from(editor.view.dom.querySelectorAll(`[${PLAYABLE_ELEMENT_KIND_HTML_ATTR}="scene"]`))
      .find(element => element.getAttribute(PLAYABLE_ELEMENT_ID_HTML_ATTR) === currentSceneId);
    heading?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [currentSceneId, hasOpened, jumpCount, mode, open]);

  const openEditor = () => {
    setOpen(value => !value);
    setHasOpened(true);
  };
  const discardDraftForLatest = () => {
    controller.useLatestDiscardingDraft();
  };

  const savedLabel = controller.state.saveState === "saved"
    ? `Saved ${controller.state.savedAt ? new Date(controller.state.savedAt).toLocaleTimeString() : ""}`.trim()
    : controller.state.saveState === "dirty" ? "Unsaved changes · saving automatically"
      : controller.state.saveState === "saving" ? "Saving session copy…"
        : controller.state.saveState === "recovering" ? "Checking saved session…"
          : controller.state.saveState === "unknown" ? "Save outcome needs checking"
            : controller.state.saveState === "conflict" ? "Another saved version needs review"
              : controller.state.saveState === "invalid" ? "Fix this edit before it can save"
                : controller.state.saveState === "rejected" ? "This edit was rejected"
                : "Recovery storage needs attention";

  return (
    <>
    <PlaySurfaceContext id="play-editor-context" order={30} identity={surfaceIdentity}>
      <SurfaceContextAction type="button" aria-label={open ? "Close editor" : "Edit session"} title={open ? "Close editor" : "Edit session"} aria-expanded={open} onClick={openEditor}>{open ? "Close" : "Edit"}</SurfaceContextAction>
      <SurfaceContextStatus data-testid="play-canvas-save-status" tone={controller.state.saveState === "saved" ? "neutral" : "warning"}>{savedLabel}</SurfaceContextStatus>
    </PlaySurfaceContext>
    <section className="play-session-content" data-save-state={controller.state.saveState} aria-label="Play session copy">

      {controller.state.message ? <p className="play-session-content__message" role={controller.state.saveState === "invalid" || controller.state.saveState === "rejected" || controller.state.saveState === "storage-error" ? "alert" : "status"}>{controller.state.message}</p> : null}
      {controller.state.serializationIssues.length ? (
        <ul className="play-session-content__issues" aria-label="Markdown save issues">
          {controller.state.serializationIssues.map((issue, index) => <li key={`${issue}:${index}`}>{issue}</li>)}
        </ul>
      ) : null}

      {controller.state.saveState === "unknown" ? <button type="button" onClick={controller.retryRecovery}>Check this save</button> : null}
      {controller.state.saveState === "conflict" ? <button type="button" onClick={controller.reviewLatest}>Load latest for review</button> : null}
      {controller.state.latestRemote ? (
        <section className="play-session-content__review" aria-label="Session copy conflict review">
          <h2>Review the latest saved version</h2>
          <p>Your draft and the current saved copy are shown before you choose what to continue.</p>
          <details><summary>Your draft</summary><pre>{controller.state.draftMarkdown}</pre></details>
          <details><summary>Latest saved copy · revision {controller.state.latestRemote.edition_revision}</summary><pre>{controller.state.latestRemote.markdown}</pre></details>
          <div className="play-session-content__actions">
            <button type="button" onClick={discardDraftForLatest}>Use latest and discard my draft</button>
            <button type="button" onClick={controller.keepDraftOnLatest}>I reviewed it · keep my draft on latest</button>
          </div>
        </section>
      ) : null}

      {hasOpened ? (
        <div className="play-session-content__editor" hidden={!open} data-testid="play-session-copy-editor">
          <div className="play-session-content__toolbar">
            <div role="group" aria-label="Session editor mode">
              <button type="button" aria-pressed={mode === "visual"} onClick={() => setMode("visual")}>Visual</button>
              <button type="button" aria-pressed={mode === "markdown"} onClick={() => setMode("markdown")}>Markdown</button>
            </div>
            {mode === "visual" ? currentSceneId ? <button type="button" onClick={() => setJumpCount(value => value + 1)}>Go to current scene</button> : <span>No current scene selected</span> : null}
          </div>
          {split.frontmatter ? <details className="play-session-content__frontmatter"><summary>Preserved document metadata</summary><pre>{split.frontmatter}</pre></details> : null}
          {mode === "visual" ? (
            imported.diagnostics.some(item => item.level === "warning") ? (
              <div className="play-session-content__blocked" role="alert">
                <p>This session copy contains Markdown that the visual editor cannot preserve safely. Edit its body in Markdown mode.</p>
                <ul>{imported.diagnostics.filter(item => item.level === "warning").map((item, index) => <li key={`${item.message}:${index}`}>{item.message}</li>)}</ul>
              </div>
            ) : (
              <MarkdownEditorCore
                content={imported.doc}
                editable={controller.state.saveState !== "recovering"}
                documentKey={`${identityKey}:${controller.state.editorRevision}:${editorEpoch}:visual`}
                onUpdate={updateFromVisual}
                onEditorChange={editor => { editorRef.current = editor; }}
                className="play-session-content__visual"
                dataTestId="play-session-copy-visual"
              />
            )
          ) : (
            <textarea
              aria-label="Session copy Markdown"
              data-testid="play-session-copy-markdown"
              value={split.markdown}
              disabled={controller.state.saveState === "recovering"}
              onChange={event => {
                const markdown = preserveLeadingYamlFrontmatter(controller.state.accepted.markdown, event.target.value);
                const parsed = markdownToTiptapDoc(markdown);
                controller.changeDraft(markdown, parsed.diagnostics.filter(item => item.level === "warning").map(item => item.message));
              }}
              spellCheck={false}
            />
          )}
          <div className="play-session-content__footer">
            <span>Session copy · revision {controller.state.accepted.edition_revision} · {originLabel.replace(/^Created from saved /, "From ")}</span>
            {controller.state.saveState === "invalid" || controller.state.saveState === "rejected" ? <button type="button" onClick={() => { controller.resetDraftFromAccepted(); setEditorEpoch(value => value + 1); }}>Discard draft</button> : null}
          </div>
        </div>
      ) : null}
    </section>
    </>
  );
}
