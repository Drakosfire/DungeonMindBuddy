import { act, render, waitFor } from "@testing-library/react";
import { Extension } from "@tiptap/core";
import type { Content } from "@tiptap/core";
import type { Editor } from "@tiptap/core";
import { describe, expect, it, vi } from "vitest";

import { MarkdownEditorCore } from "./MarkdownEditorCore";

const starterContent: Content = {
  type: "doc",
  content: [
    { type: "heading", attrs: { level: 1 }, content: [{ type: "text", text: "Starter" }] },
    { type: "paragraph", content: [{ type: "text", text: "Editable body." }] },
  ],
};

describe("MarkdownEditorCore", () => {
  it("mounts with content and exposes editor via onEditorChange", async () => {
    const handleEditorChange = vi.fn<(editor: Editor | null) => void>();

    render(
      <MarkdownEditorCore
        content={starterContent}
        onEditorChange={handleEditorChange}
        dataTestId="markdown-editor-core"
      />,
    );

    await waitFor(() => {
      expect(handleEditorChange).toHaveBeenCalledWith(expect.objectContaining({
        isEditable: true,
      }));
    });

    const editor = handleEditorChange.mock.calls.at(-1)?.[0];
    expect(editor?.getJSON()).toMatchObject({
      type: "doc",
      content: expect.arrayContaining([
        expect.objectContaining({ type: "heading" }),
      ]),
    });
  });

  it("fires onUpdate when content changes", async () => {
    const handleUpdate = vi.fn();
    let editor: Editor | null = null;

    render(
      <MarkdownEditorCore
        content={starterContent}
        onEditorChange={(nextEditor) => { editor = nextEditor; }}
        onUpdate={handleUpdate}
      />,
    );

    await waitFor(() => expect(editor).not.toBeNull());

    act(() => {
      editor?.commands.setContent(
        {
          type: "doc",
          content: [{ type: "paragraph", content: [{ type: "text", text: "Updated text." }] }],
        },
        true,
      );
    });

    await waitFor(() => {
      expect(handleUpdate).toHaveBeenCalled();
    });
    const [json] = handleUpdate.mock.calls.at(-1) ?? [];
    expect(JSON.stringify(json)).toContain("Updated text.");
  });

  it("toggles editor.isEditable when editable prop changes", async () => {
    let editor: Editor | null = null;
    const { rerender } = render(
      <MarkdownEditorCore
        content={starterContent}
        editable
        onEditorChange={(nextEditor) => { editor = nextEditor; }}
      />,
    );

    await waitFor(() => expect(editor?.isEditable).toBe(true));

    rerender(
      <MarkdownEditorCore
        content={starterContent}
        editable={false}
        onEditorChange={(nextEditor) => { editor = nextEditor; }}
      />,
    );

    await waitFor(() => expect(editor?.isEditable).toBe(false));
  });

  it("accepts additional extensions", async () => {
    const TestMarker = Extension.create({
      name: "testMarker",
    });
    let editor: Editor | null = null;

    render(
      <MarkdownEditorCore
        content={starterContent}
        extensions={[TestMarker]}
        onEditorChange={(nextEditor) => { editor = nextEditor; }}
      />,
    );

    await waitFor(() => expect(editor).not.toBeNull());
    expect(editor?.extensionManager.extensions.some((extension) => extension.name === "testMarker")).toBe(true);
  });

  it("reloads content when documentKey changes", async () => {
    let editor: Editor | null = null;
    const replacement: Content = {
      type: "doc",
      content: [{ type: "paragraph", content: [{ type: "text", text: "A plain imported plan." }] }],
    };

    const { rerender } = render(
      <MarkdownEditorCore
        content={starterContent}
        documentKey="doc:1"
        onEditorChange={(nextEditor) => { editor = nextEditor; }}
      />,
    );

    await waitFor(() => expect(editor).not.toBeNull());
    expect(editor?.getText()).toContain("Editable body.");

    rerender(
      <MarkdownEditorCore
        content={replacement}
        documentKey="doc:2"
        onEditorChange={(nextEditor) => { editor = nextEditor; }}
      />,
    );

    await waitFor(() => {
      expect(editor?.getText()).toContain("A plain imported plan.");
    });
  });
});
