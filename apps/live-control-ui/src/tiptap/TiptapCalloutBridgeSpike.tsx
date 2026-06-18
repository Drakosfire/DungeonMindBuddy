import { useCallback, useEffect, useState } from "react";
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
import "../../../../evals/c2_live_prep/mireward-prep/assets/prep-markdown-themes.css";
import "./tiptapSpike.css";

export const initialCalloutContent = {
  type: "doc",
  content: [
    {
      type: "heading",
      attrs: { level: 2 },
      content: [{ type: "text", text: "North-gate opening spike" }],
    },
    {
      type: "callout",
      attrs: { kind: "read-aloud" },
      content: [{ type: "paragraph", content: [{ type: "text", text: "The southern road gives way to the dark wall of Mireward." }] }],
    },
    {
      type: "callout",
      attrs: { kind: "gm-note" },
      content: [{ type: "paragraph", content: [{ type: "text", text: "Lysandro is the human accelerant." }] }],
    },
    {
      type: "callout",
      attrs: { kind: "rules" },
      content: [{ type: "paragraph", content: [{ type: "text", text: "Track Gate, Civilians, and Cure Line as visible pressures." }] }],
    },
    {
      type: "callout",
      attrs: { kind: "warning" },
      content: [{ type: "paragraph", content: [{ type: "text", text: "The meat flank is 3–8 minutes behind the refugees." }] }],
    },
  ],
};

interface TiptapCalloutBridgeSpikeProps {
  onEditorToolsChange?: (tools: AppChromeTools | null) => void;
}

export function TiptapCalloutBridgeSpike({ onEditorToolsChange }: TiptapCalloutBridgeSpikeProps) {
  const [json, setJson] = useState<unknown>(initialCalloutContent);
  const [isEditorLocked, setIsEditorLocked] = useState(false);
  const editor = useEditor({
    extensions: [StarterKit, CalloutNode],
    content: initialCalloutContent,
    editable: !isEditorLocked,
    onUpdate: ({ editor: nextEditor }) => setJson(nextEditor.getJSON()),
  });

  const insertCallout = useCallback((kind: CalloutKind) => {
    editor?.chain().focus().insertCallout({ kind }).run();
  }, [editor]);

  const toggleEditorLock = useCallback(() => {
    const nextLocked = !isEditorLocked;
    setIsEditorLocked(nextLocked);
    editor?.setEditable(!nextLocked);
  }, [editor, isEditorLocked]);

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
  }, [editor, insertCallout, isEditorLocked, onEditorToolsChange, toggleEditorLock]);

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
        </div>

        <div className="tiptap-spike-editor md-content md-theme-command" data-md-theme="command" data-testid="tiptap-editor">
          <EditorContent editor={editor} />
        </div>
      </section>

      <div className="tiptap-spike-grid">
        <section className="tiptap-spike-panel" aria-labelledby="json-heading">
          <h2 id="json-heading">Editor JSON</h2>
          <pre data-testid="editor-json">{JSON.stringify(json, null, 2)}</pre>
        </section>
        <section className="tiptap-spike-panel" aria-labelledby="markdown-heading">
          <h2 id="markdown-heading">Exported Markdown</h2>
          <pre data-testid="markdown-export">{tiptapJsonToSemanticMarkdown(json)}</pre>
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
