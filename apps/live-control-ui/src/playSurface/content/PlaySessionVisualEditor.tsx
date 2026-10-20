import type { Editor, JSONContent } from "@tiptap/core";
import { MarkdownEditorCore } from "../../tiptap/MarkdownEditorCore";

export function PlaySessionVisualEditor({
  content,
  editable,
  documentKey,
  onUpdate,
  onEditorChange,
}: {
  content: JSONContent;
  editable: boolean;
  documentKey: string;
  onUpdate: (json: JSONContent, editor: Editor, meta: { programmatic: boolean }) => void;
  onEditorChange: (editor: Editor | null) => void;
}) {
  return (
    <MarkdownEditorCore
      content={content}
      editable={editable}
      documentKey={documentKey}
      onUpdate={onUpdate}
      onEditorChange={onEditorChange}
      className="play-session-content__visual"
      dataTestId="play-session-copy-visual"
    />
  );
}
