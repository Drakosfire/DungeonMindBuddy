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
    const [json, , meta] = handleUpdate.mock.calls.at(-1) ?? [];
    expect(JSON.stringify(json)).toContain("Updated text.");
    expect(meta).toEqual({ programmatic: false });
  });

  it("tags the first mount update as programmatic and the first user edit as non-programmatic", async () => {
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

    await waitFor(() => {
      expect(handleUpdate.mock.calls.some(([, , meta]) => meta?.programmatic === true)).toBe(true);
    });

    handleUpdate.mockClear();

    act(() => {
      editor?.commands.insertContent("User edit.");
    });

    await waitFor(() => {
      expect(handleUpdate).toHaveBeenCalledTimes(1);
    });
    expect(handleUpdate.mock.calls[0]?.[2]).toEqual({ programmatic: false });
  });

  it("marks the first real user transaction as non-programmatic after idle mount", async () => {
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
    // Allow the hydration microtask to clear before the user edit.
    await act(async () => {
      await Promise.resolve();
    });
    const callsBeforeEdit = handleUpdate.mock.calls.length;

    act(() => {
      editor?.commands.insertContent(" pasted");
    });

    await waitFor(() => {
      expect(handleUpdate.mock.calls.length).toBeGreaterThan(callsBeforeEdit);
    });
    const userCalls = handleUpdate.mock.calls.slice(callsBeforeEdit);
    expect(userCalls).toHaveLength(1);
    expect(userCalls[0]?.[2]).toEqual({ programmatic: false });
    expect(JSON.stringify(userCalls[0]?.[0])).toContain("pasted");
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
