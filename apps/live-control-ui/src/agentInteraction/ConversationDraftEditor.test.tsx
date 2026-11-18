import { readSavedConversationVariantTarget } from "../statblocks/savedStatblockLocation";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { confirmVariantReview, correctVariantReview, openConversationDraft, openConversationVariantApproval, openVariantReview, saveConversationDraft } from "../api/conversationDraftApi";
import { ConversationDraftEditor, ConversationVariantApproval } from "./ConversationDraftEditor";

vi.mock("../api/conversationDraftApi", () => ({
  openConversationDraft: vi.fn(),
  openConversationVariantApproval: vi.fn(),
  saveConversationDraft: vi.fn(),
  openVariantReview: vi.fn(),
  confirmVariantReview: vi.fn(),
  correctVariantReview: vi.fn(),
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

it("retries saving a variant link without applying the insertion again", async () => {
  const scope = { worldId: "world", conversationId: "conversation", turnId: "turn" };
  vi.mocked(openConversationDraft).mockResolvedValueOnce({
    revision: 2, markdown: "Draft", variant_review_ids: ["review"],
  });
  vi.mocked(openVariantReview).mockResolvedValueOnce({
    revision: 2, saved: true,
    definition: {} as Awaited<ReturnType<typeof openVariantReview>>["definition"],
  });
  const captured = { basis: { document_id: "edge", world_id: "world", visibility: "internal" }, draftMarkdown: "Existing page" };
  const bridge = {
    capture: vi.fn().mockResolvedValue(captured),
    placeSavedVariantLink: vi.fn().mockResolvedValue({ captured, afterEditorSha256: "editor", afterDraftSha256: "draft" }),
    saveProposal: vi.fn().mockRejectedValueOnce(new Error("Save interrupted")).mockResolvedValueOnce(undefined),
  };
  type Placement = NonNullable<Parameters<typeof ConversationDraftEditor>[0]["placement"]>;
  render(<ConversationDraftEditor scope={scope} placement={{ documentId: "edge", bridge: bridge as unknown as Placement["bridge"] }}/>);
  fireEvent.click(screen.getByRole("button", { name: "Open draft" }));
  fireEvent.click(await screen.findByRole("button", { name: "Review statblock variant" }));
  const insert = await screen.findByRole("button", { name: "Insert at cursor and save page" });
  fireEvent.click(insert);
  expect(await screen.findByRole("alert")).toHaveTextContent("Save interrupted");
  fireEvent.click(insert);
  expect(await screen.findByText("Variant link verified on the saved page.")).toBeInTheDocument();
  expect(bridge.placeSavedVariantLink).toHaveBeenCalledExactlyOnceWith(captured, { ...scope, reviewId: "review" });
  expect(bridge.saveProposal).toHaveBeenCalledTimes(2);
});

it("opens the producing review from the approval turn and waits for confirmation", async () => {
  const scope = { worldId: "world", conversationId: "conversation", turnId: "approval" };
  const producer = { ...scope, turnId: "producer" };
  vi.mocked(confirmVariantReview).mockClear();
  vi.mocked(openConversationVariantApproval).mockResolvedValueOnce({ scope: producer, reviewId: "review", revision: 2 });
  vi.mocked(openConversationDraft).mockResolvedValueOnce({
    revision: 2, markdown: "Reviewed draft", variant_review_ids: ["review"],
  });
  vi.mocked(openVariantReview).mockResolvedValueOnce({
    revision: 2, definition: {} as Awaited<ReturnType<typeof openVariantReview>>["definition"],
  });

  render(<ConversationVariantApproval scope={scope} />);
  fireEvent.click(screen.getByRole("button", { name: "Find reviewed statblock" }));
  expect(await screen.findByRole("button", { name: "Confirm and save as new statblock" })).toBeEnabled();
  expect(openConversationVariantApproval).toHaveBeenCalledWith(scope);
  expect(openVariantReview).toHaveBeenCalledWith(producer, "review");
  expect(confirmVariantReview).not.toHaveBeenCalled();
});

it("rejects a draft edited after the approval lookup", async () => {
  const scope = { worldId: "world", conversationId: "conversation", turnId: "approval" };
  vi.mocked(openConversationVariantApproval).mockResolvedValueOnce({
    scope: { ...scope, turnId: "producer" }, reviewId: "review", revision: 2,
  });
  vi.mocked(openConversationDraft).mockResolvedValueOnce({ revision: 3, markdown: "Newer draft" });
  render(<ConversationVariantApproval scope={scope} />);
  fireEvent.click(screen.getByRole("button", { name: "Find reviewed statblock" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("The reviewed draft changed.");
  expect(screen.queryByRole("button", { name: "Confirm and save as new statblock" })).not.toBeInTheDocument();
});

it("stages a bounded rule correction and confirms only the successor review", async () => {
  const scope = { worldId: "world", conversationId: "conversation", turnId: "producer" };
  vi.mocked(confirmVariantReview).mockClear().mockResolvedValueOnce({ revision_id: "saved" });
  vi.mocked(openConversationDraft)
    .mockResolvedValueOnce({ revision: 1, markdown: "Original", variant_review_ids: ["old"] })
    .mockResolvedValueOnce({ revision: 2, markdown: "Updated", variant_review_ids: ["new"] });
  const definition = { rule_elements: [{
    key: "rain", name: "Rain", rules_text: "Any hostile action starts the rain.", activation: {},
  }] } as Awaited<ReturnType<typeof openVariantReview>>["definition"];
  vi.mocked(openVariantReview)
    .mockResolvedValueOnce({ revision: 1, definition })
    .mockResolvedValueOnce({ revision: 2, definition });
  vi.mocked(correctVariantReview).mockResolvedValueOnce({ revision: 2, review_id: "new" });

  render(<ConversationDraftEditor scope={scope} />);
  fireEvent.click(screen.getByRole("button", { name: "Open draft" }));
  fireEvent.click(await screen.findByRole("button", { name: "Review statblock variant" }));
  fireEvent.click(await screen.findByText("Correct reviewed rules"));
  fireEvent.change(screen.getByRole("textbox", { name: "Rule text" }), {
    target: { value: "Qualifying violence starts the rain." },
  });
  expect(screen.getByRole("button", { name: "Confirm and save as new statblock" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Stage corrected review" }));
  expect(await screen.findByDisplayValue("Updated")).toBeInTheDocument();
  expect(correctVariantReview).toHaveBeenCalledWith(scope, "old", 1, [{
    rule_key: "rain", field: "rules_text",
    replace_exact: "Any hostile action starts the rain.", with_text: "Qualifying violence starts the rain.",
  }]);
  expect(confirmVariantReview).not.toHaveBeenCalled();
  const confirm = await screen.findByRole("button", { name: "Confirm and save as new statblock" });
  await waitFor(() => expect(confirm).toBeEnabled());
  fireEvent.click(confirm);
  expect(await screen.findByRole("status")).toHaveTextContent("Statblock variant saved.");
  expect(confirmVariantReview).toHaveBeenCalledExactlyOnceWith(scope, "new");
});

it("recovers from a lost correction response without carrying approval to the new review", async () => {
  const scope = { worldId: "world", conversationId: "conversation", turnId: "approval" };
  const producer = { ...scope, turnId: "producer" };
  const definition = { rule_elements: [{
    key: "rain", name: "Rain", rules_text: "Any hostile action starts rain.", activation: {},
  }] } as Awaited<ReturnType<typeof openVariantReview>>["definition"];
  vi.mocked(confirmVariantReview).mockClear();
  vi.mocked(openConversationVariantApproval).mockResolvedValueOnce({ scope: producer, reviewId: "old", revision: 1 });
  vi.mocked(openConversationDraft)
    .mockResolvedValueOnce({ revision: 1, markdown: "Old", variant_review_ids: ["old"] })
    .mockResolvedValueOnce({ revision: 2, markdown: "Corrected", variant_review_ids: ["new"] });
  vi.mocked(openVariantReview).mockResolvedValueOnce({ revision: 1, definition });
  vi.mocked(correctVariantReview).mockRejectedValueOnce(new Error("Response lost."));

  render(<ConversationVariantApproval scope={scope} />);
  fireEvent.click(screen.getByRole("button", { name: "Find reviewed statblock" }));
  fireEvent.click(await screen.findByText("Correct reviewed rules"));
  fireEvent.change(screen.getByRole("textbox", { name: "Rule text" }), { target: { value: "Qualifying violence starts rain." } });
  fireEvent.click(screen.getByRole("button", { name: "Stage corrected review" }));
  fireEvent.click(await screen.findByRole("button", { name: "Open latest draft for review" }));
  expect(await screen.findByDisplayValue("Corrected")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Review statblock variant" })).toBeVisible();
  expect(screen.queryByRole("button", { name: "Confirm and save as new statblock" })).not.toBeInTheDocument();
  expect(confirmVariantReview).not.toHaveBeenCalled();
});
