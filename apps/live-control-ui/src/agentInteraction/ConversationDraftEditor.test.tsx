import { readSavedConversationVariantTarget } from "../statblocks/savedStatblockLocation";
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { confirmVariantReview, openConversationDraft, openVariantReview, saveConversationDraft } from "../api/conversationDraftApi";
import { ConversationDraftEditor } from "./ConversationDraftEditor";

vi.mock("../api/conversationDraftApi", () => ({
  openConversationDraft: vi.fn(),
  saveConversationDraft: vi.fn(),
  openVariantReview: vi.fn(),
  confirmVariantReview: vi.fn(),
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

vi.mock("../statblocks/render/StatblockRenderer", () => ({
  StatblockRenderer: () => <p>Reviewed mechanics</p>,
}));

it("requires explicit confirmation of the displayed review", async () => {
  const scope = { worldId: "world", conversationId: "conversation", turnId: "turn" };
  vi.mocked(openConversationDraft).mockResolvedValueOnce({
    revision: 2, markdown: "Draft", variant_review_ids: ["review"],
  });
  vi.mocked(openVariantReview).mockResolvedValueOnce({
    revision: 2, definition: {} as Awaited<ReturnType<typeof openVariantReview>>["definition"],
  });
  vi.mocked(confirmVariantReview).mockResolvedValueOnce({ revision_id: "saved" });
  render(<ConversationDraftEditor scope={scope} />);
  fireEvent.click(screen.getByRole("button", { name: "Open draft" }));
  fireEvent.click(await screen.findByRole("button", { name: "Review statblock variant" }));
  const confirm = { name: "Confirm and save as new statblock" };
  await screen.findByRole("button", confirm);
  expect(confirmVariantReview).not.toHaveBeenCalled();
  const editor = screen.getByRole("textbox", { name: "Draft Markdown" });
  fireEvent.change(editor, { target: { value: "Unsaved" } });
  expect(screen.queryByRole("button", confirm)).not.toBeInTheDocument();
  fireEvent.change(editor, { target: { value: "Draft" } });
  fireEvent.click(screen.getByRole("button", confirm));
  expect(await screen.findByRole("status")).toHaveTextContent("Statblock variant saved.");
  expect(confirmVariantReview).toHaveBeenCalledExactlyOnceWith(scope, "review");
  const href = screen.getByRole("link", { name: "Open saved variant" }).getAttribute("href");
  expect(readSavedConversationVariantTarget(href!)).toEqual({ ...scope, reviewId: "review" });
  expect(readSavedConversationVariantTarget(href + "&variantReview=other")).toBeNull();
});

it("reopens the link for a previously saved variant without confirming again", async () => {
  const scope = { worldId: "world", conversationId: "conversation", turnId: "turn" };
  vi.mocked(confirmVariantReview).mockClear();
  vi.mocked(openConversationDraft).mockResolvedValueOnce({
    revision: 2, markdown: "Draft", variant_review_ids: ["review"],
  });
  vi.mocked(openVariantReview).mockResolvedValueOnce({
    revision: 2, saved: true,
    definition: {} as Awaited<ReturnType<typeof openVariantReview>>["definition"],
  });

  render(<ConversationDraftEditor scope={scope} />);
  fireEvent.click(screen.getByRole("button", { name: "Open draft" }));
  fireEvent.click(await screen.findByRole("button", { name: "Review statblock variant" }));

  expect(await screen.findByRole("link", { name: "Open saved variant" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Confirm and save as new statblock" })).toBeDisabled();
  expect(confirmVariantReview).not.toHaveBeenCalled();
});
