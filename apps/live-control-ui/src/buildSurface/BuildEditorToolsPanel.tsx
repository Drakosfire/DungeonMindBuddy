import {useEffect,useState} from 'react';
import type {Editor} from '@tiptap/core';

/** Editor state is observed inside the panel, without republishing its host generation. */
export function BuildEditorToolsPanel({editor}:{editor:Editor|null}) {
  const [,refresh]=useState(0);
  useEffect(()=>{
    if(!editor)return;
    const update=()=>refresh(value=>value+1);
    editor.on('transaction',update);
    return()=>{editor.off('transaction',update);};
  },[editor]);
  const headings: { position: number; level: number; text: string }[] = [];
  editor?.state.doc.descendants((node, position) => {
    if (node.type.name === "heading") headings.push({ position, level: node.attrs.level, text: node.textContent });
  });
  return <><div className="build-formatting" role="group" aria-label="Text formatting">
          <button type="button" disabled={!editor} aria-pressed={editor?.isActive("bold") ?? false}
            onClick={() => editor?.chain().focus().toggleBold().run()}>Bold</button>
          <button type="button" disabled={!editor} aria-pressed={editor?.isActive("italic") ?? false}
            onClick={() => editor?.chain().focus().toggleItalic().run()}>Italic</button>
          <button type="button" disabled={!editor} onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}>Heading</button>
          <button type="button" disabled={!editor?.can().undo()} onClick={() => editor?.chain().focus().undo().run()}>Undo</button>
          <button type="button" disabled={!editor?.can().redo()} onClick={() => editor?.chain().focus().redo().run()}>Redo</button>
        </div><nav className="markdown-document-outline" aria-label="On this page">
          {headings.length ? <ol>{headings.map(heading => <li key={heading.position}
            style={{ paddingInlineStart: `${Math.min(heading.level - 1, 2) * 0.75}rem` }}>
            <button type="button" onClick={() => editor?.chain().focus().setTextSelection(heading.position + 1).scrollIntoView().run()}>
              {heading.text || "Untitled section"}
            </button>
          </li>)}</ol> : <p>No headings in this document.</p>}
        </nav></>;
}
