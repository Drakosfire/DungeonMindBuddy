import { useCallback, useEffect, useState } from "react";
import type { Content } from "@tiptap/core";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

import type { AppChromeTools } from "../chrome/AppChrome";
import { CalloutNode } from "./extensions/CalloutNode";
import {
  CALLOUT_KINDS,
  defaultCalloutLabel,
  tiptapJsonToSemanticMarkdown,
  type CalloutKind,
} from "./markdown/calloutMarkdown";
import {
  buildInitialWorkingBoardState,
  initialCalloutContent,
  readTiptapWorkingBoardState,
  writeTiptapWorkingBoardState,
  type TiptapWorkingBoardState,
} from "./state/tiptapLocalState";
import "../../../../evals/c2_live_prep/mireward-prep/assets/prep-markdown-themes.css";
import "./tiptapSpike.css";

export { initialCalloutContent };

type LocalStateStatus = "Loaded starter content" | "Loaded local draft" | "Saved locally" | "Reset to starter";

interface TiptapCalloutBridgeSpikeProps {
  onEditorToolsChange?: (tools: AppChromeTools | null) => void;
}

export function TiptapCalloutBridgeSpike({ onEditorToolsChange }: TiptapCalloutBridgeSpikeProps) {
  const [workingState, setWorkingState] = useState<TiptapWorkingBoardState>(() => (
    readTiptapWorkingBoardState(window.localStorage) ?? buildInitialWorkingBoardState()
  ));
  const [localStateStatus, setLocalStateStatus] = useState<LocalStateStatus>(() => (
    readTiptapWorkingBoardState(window.localStorage) ? "Loaded local draft" : "Loaded starter content"
  ));
  const [copyMessage, setCopyMessage] = useState("");
  const [isEditorLocked, setIsEditorLocked] = useState(false);
  const editor = useEditor({
    extensions: [StarterKit, CalloutNode],
    content: workingState.tiptap_json as Content,
    editable: !isEditorLocked,
    onUpdate: ({ editor: nextEditor }) => {
      const tiptapJson = nextEditor.getJSON();
      const now = new Date().toISOString();
      setWorkingState((current) => {
        const nextState = {
          ...current,
          tiptap_json: tiptapJson,
          exported_markdown: tiptapJsonToSemanticMarkdown(tiptapJson),
          dirty: false,
          updated_at: now,
          last_local_save_at: now,
        };
        writeTiptapWorkingBoardState(window.localStorage, nextState);
        return nextState;
      });
      setLocalStateStatus("Saved locally");
    },
  });

  const insertCallout = useCallback((kind: CalloutKind) => {
    editor?.chain().focus().insertCallout({ kind }).run();
  }, [editor]);

  const toggleEditorLock = useCallback(() => {
    const nextLocked = !isEditorLocked;
    setIsEditorLocked(nextLocked);
    editor?.setEditable(!nextLocked);
  }, [editor, isEditorLocked]);

  const resetLocalDraft = useCallback(() => {
    if (!editor) return;
    const now = new Date().toISOString();
    const resetState = buildInitialWorkingBoardState(now);
    editor.commands.setContent(initialCalloutContent, false);
    writeTiptapWorkingBoardState(window.localStorage, resetState);
    setWorkingState(resetState);
    setLocalStateStatus("Reset to starter");
    setCopyMessage("");
  }, [editor]);

  const copyMarkdown = useCallback(async () => {
    if (!navigator.clipboard?.writeText) {
      setCopyMessage("Copy unavailable in this browser; select the Markdown export manually.");
      return;
    }

    try {
      await navigator.clipboard.writeText(workingState.exported_markdown);
      setCopyMessage("Markdown copied.");
    } catch {
      setCopyMessage("Copy unavailable in this browser; select the Markdown export manually.");
    }
  }, [workingState.exported_markdown]);

  useEffect(() => {
    onEditorToolsChange?.({
      pinnedActions: [
        {
          id: "tiptap-edit-lock",
          eyebrow: isEditorLocked ? "Editing locked" : "Editing unlocked",
          label: isEditorLocked ? "Unlock editing" : "Lock editing",
          onClick: toggleEditorLock,
          disabled: !editor,
          pressed: isEditorLocked,
        },
      ],
      sections: [
        {
          id: "tiptap-local-state",
          title: "Local working state",
          defaultOpen: true,
          actions: [
            {
              id: "tiptap-reset-local-draft",
              eyebrow: "Browser storage",
              label: "Reset local draft",
              onClick: resetLocalDraft,
              disabled: !editor,
            },
            {
              id: "tiptap-copy-markdown",
              eyebrow: "Export",
              label: "Copy Markdown",
              onClick: copyMarkdown,
            },
          ],
        },
        {
          id: "tiptap-insert-blocks",
          title: "Insert blocks",
          defaultOpen: true,
          actions: CALLOUT_KINDS.map((kind) => ({
            id: `insert-${kind}`,
            eyebrow: "Insert",
            label: defaultCalloutLabel(kind),
            onClick: () => insertCallout(kind),
            disabled: !editor || isEditorLocked,
          })),
        },
      ],
    });

    return () => onEditorToolsChange?.(null);
  }, [copyMarkdown, editor, insertCallout, isEditorLocked, onEditorToolsChange, resetLocalDraft, toggleEditorLock]);

  const updatedAt = new Date(workingState.updated_at).toLocaleString();

  return (
    <main className="tiptap-spike-page">
      <header className="tiptap-spike-header">
        <div>
          <p className="tiptap-spike-kicker">Developer proof of concept</p>
          <h1>Tiptap Semantic Callout Bridge Spike</h1>
          <p>Editable Tiptap nodes sharing the established semantic Markdown callout contract.</p>
        </div>
        <a href="/">Back to launcher</a>
      </header>

      <section className="tiptap-spike-panel" aria-labelledby="editor-heading">
        <div className="tiptap-spike-section-heading">
          <div>
            <p className="tiptap-spike-kicker">Working board state</p>
            <h2 id="editor-heading">Editor</h2>
          </div>
          <div className="tiptap-local-actions">
            <button type="button" onClick={resetLocalDraft} disabled={!editor}>Reset local draft</button>
            <button type="button" onClick={copyMarkdown}>Copy Markdown</button>
          </div>
        </div>

        <div className="tiptap-local-state" aria-live="polite">
          <p>Working board state is saved locally in this browser. No backend or corpus write happens here.</p>
          <dl>
            <div><dt>Document</dt><dd>{workingState.title}</dd></div>
            <div><dt>State</dt><dd>{localStateStatus}</dd></div>
            <div><dt>Updated</dt><dd>{updatedAt}</dd></div>
          </dl>
          {copyMessage && <p className="tiptap-copy-message">{copyMessage}</p>}
        </div>

        <div className="tiptap-spike-editor md-content md-theme-command" data-md-theme="command" data-testid="tiptap-editor">
          <EditorContent editor={editor} />
        </div>
      </section>

      <div className="tiptap-spike-grid">
        <section className="tiptap-spike-panel" aria-labelledby="json-heading">
          <h2 id="json-heading">Editor JSON</h2>
          <pre data-testid="editor-json">{JSON.stringify(workingState.tiptap_json, null, 2)}</pre>
        </section>
        <section className="tiptap-spike-panel" aria-labelledby="markdown-heading">
          <h2 id="markdown-heading">Exported Markdown</h2>
          <pre data-testid="markdown-export">{workingState.exported_markdown}</pre>
        </section>
      </div>

      <aside className="tiptap-spike-note" aria-labelledby="bridge-notes-heading">
        <h2 id="bridge-notes-heading">Bridge notes</h2>
        <p>
          This is working board state only. Exported Markdown is for review/corpus handoff. No canon writes happen here.
        </p>
      </aside>
    </main>
  );
}
