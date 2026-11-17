import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { openConversationDraft, saveConversationDraft } from "../api/conversationDraftApi";
import { ConversationDraftEditor } from "./ConversationDraftEditor";

vi.mock("../api/conversationDraftApi", () => ({
  openConversationDraft: vi.fn(),
  saveConversationDraft: vi.fn(),
}));

it("keeps unsaved Markdown visible when the revision changes", async () => {
  const scope = { worldId: "world", conversationId: "conversation", turnId: "turn" };
  vi.mocked(openConversationDraft)
    .mockResolvedValueOnce({ revision: 1, markdown: "Original" })
    .mockResolvedValueOnce({ revision: 2, markdown: "Saved elsewhere" });
  vi.mocked(saveConversationDraft).mockRejectedValueOnce(new Error("Conversation draft changed."));

  render(<ConversationDraftEditor scope={scope} />);
  fireEvent.click(screen.getByRole("button", { name: "Open draft" }));
  const editor = await screen.findByRole("textbox", { name: "Draft Markdown" });
  fireEvent.change(editor, { target: { value: "My edits" } });
  fireEvent.click(screen.getByRole("button", { name: "Save draft" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Conversation draft changed.");
  expect(editor).toHaveValue("My edits");
  expect(saveConversationDraft).toHaveBeenCalledWith(scope, 1, "My edits");
  fireEvent.click(screen.getByRole("button", { name: "Discard local edits and reopen" }));
  expect(await screen.findByDisplayValue("Saved elsewhere")).toBe(editor);
});
