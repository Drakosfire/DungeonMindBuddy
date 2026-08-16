import { act, render, waitFor } from "@testing-library/react";
import type { Editor } from "@tiptap/core";
import { DOMParser } from "@tiptap/pm/model";
import { describe, expect, it } from "vitest";

import { MarkdownEditorCore } from "../MarkdownEditorCore";
import {
  PLAYABLE_ELEMENT_ID_HTML_ATTR,
  PLAYABLE_ELEMENT_KIND_HTML_ATTR,
} from "./playableElementIdentity";

describe("P1C Choice/Option clipboard re-key", () => {
  it("re-keys a Choice duplicated through the clipboard HTML serialize/parse path", async () => {
    let editor: Editor | null = null;
    render(
      <MarkdownEditorCore
        content={{
          type: "doc",
          content: [
            {
              type: "heading",
              attrs: { level: 2, playableElementKind: "scene", playableElementId: "scene:gate" },
              content: [{ type: "text", text: "The Gate" }],
            },
            {
              type: "heading",
              attrs: { level: 3, playableElementKind: "choice", playableElementId: "choice:route" },
              content: [{ type: "text", text: "Which route?" }],
            },
            {
              type: "heading",
              attrs: { level: 4, playableElementKind: "option", playableElementId: "option:fire" },
              content: [{ type: "text", text: "Burn" }],
            },
          ],
        }}
        onEditorChange={(nextEditor) => { editor = nextEditor; }}
      />,
    );
    await waitFor(() => expect(editor).not.toBeNull());

    const choicePos = (() => {
      let pos: number | null = null;
      editor!.state.doc.descendants((node, nodePos) => {
        if (node.type.name === "heading" && node.attrs.playableElementId === "choice:route") {
          pos = nodePos;
        }
      });
      return pos;
    })();
    expect(choicePos).not.toBeNull();
    const choiceNode = editor!.state.doc.nodeAt(choicePos!);
    expect(choiceNode).not.toBeNull();

    const clipboard = editor!.view.serializeForClipboard(
      editor!.state.doc.slice(choicePos!, choicePos! + choiceNode!.nodeSize),
    );
    const html = clipboard.dom.innerHTML;
    expect(html).toContain(`${PLAYABLE_ELEMENT_KIND_HTML_ATTR}="choice"`);
    expect(html).toContain(`${PLAYABLE_ELEMENT_ID_HTML_ATTR}="choice:route"`);

    const wrapper = document.createElement("div");
    wrapper.innerHTML = html;
    const parsed = DOMParser.fromSchema(editor!.schema).parseSlice(wrapper);
    act(() => {
      editor!.view.dispatch(editor!.state.tr.insert(editor!.state.doc.content.size, parsed.content));
    });

    const ids: string[] = [];
    editor!.state.doc.descendants((node) => {
      if (node.type.name === "heading" && typeof node.attrs.playableElementId === "string") {
        ids.push(node.attrs.playableElementId);
      }
    });
    expect(ids.filter((id) => id === "choice:route")).toHaveLength(1);
    expect(ids.filter((id) => id.startsWith("choice:") && id !== "choice:route")).toHaveLength(1);
    expect(ids).toContain("option:fire");
    expect(ids).toContain("scene:gate");
  });

  it("re-keys an Option duplicated through the clipboard HTML serialize/parse path", async () => {
    let editor: Editor | null = null;
    render(
      <MarkdownEditorCore
        content={{
          type: "doc",
          content: [
            {
              type: "heading",
              attrs: { level: 3, playableElementKind: "choice", playableElementId: "choice:route" },
              content: [{ type: "text", text: "Which route?" }],
            },
            {
              type: "heading",
              attrs: { level: 4, playableElementKind: "option", playableElementId: "option:fire" },
              content: [{ type: "text", text: "Burn" }],
            },
          ],
        }}
        onEditorChange={(nextEditor) => { editor = nextEditor; }}
      />,
    );
    await waitFor(() => expect(editor).not.toBeNull());

    const optionPos = (() => {
      let pos: number | null = null;
      editor!.state.doc.descendants((node, nodePos) => {
        if (node.type.name === "heading" && node.attrs.playableElementId === "option:fire") {
          pos = nodePos;
        }
      });
      return pos;
    })();
    expect(optionPos).not.toBeNull();
    const optionNode = editor!.state.doc.nodeAt(optionPos!);
    expect(optionNode).not.toBeNull();

    const clipboard = editor!.view.serializeForClipboard(
      editor!.state.doc.slice(optionPos!, optionPos! + optionNode!.nodeSize),
    );
    const html = clipboard.dom.innerHTML;
    expect(html).toContain(`${PLAYABLE_ELEMENT_KIND_HTML_ATTR}="option"`);
    expect(html).toContain(`${PLAYABLE_ELEMENT_ID_HTML_ATTR}="option:fire"`);

    const wrapper = document.createElement("div");
    wrapper.innerHTML = html;
    const parsed = DOMParser.fromSchema(editor!.schema).parseSlice(wrapper);
    act(() => {
      editor!.view.dispatch(editor!.state.tr.insert(editor!.state.doc.content.size, parsed.content));
    });

    const ids: string[] = [];
    editor!.state.doc.descendants((node) => {
      if (node.type.name === "heading" && typeof node.attrs.playableElementId === "string") {
        ids.push(node.attrs.playableElementId);
      }
    });
    expect(ids.filter((id) => id === "option:fire")).toHaveLength(1);
    expect(ids.filter((id) => id.startsWith("option:") && id !== "option:fire")).toHaveLength(1);
    expect(ids).toContain("choice:route");
  });
});
