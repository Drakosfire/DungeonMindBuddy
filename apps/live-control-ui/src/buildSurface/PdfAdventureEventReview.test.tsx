import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { authenticatedApiFetch } from "../api/liveApi";
import { PdfAdventureEventReview } from "./PdfAdventureEventReview";

vi.mock("../api/liveApi", () => ({ authenticatedApiFetch: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

it("reviews editable OCR and retries the exact publication after a lost response", async () => {
  const request = vi.mocked(authenticatedApiFetch);
  request.mockImplementationOnce(async (_url, init) => ({
    response: Response.json({
      draft: JSON.parse(String(init?.body)),
      prepared: { revision: "parent" },
      token: "review-token",
    }),
    csrf: null,
    requestEpoch: 0,
  }));
  request.mockRejectedValueOnce(new TypeError("Connection closed"));
  request.mockResolvedValueOnce({
    response: Response.json({ node_id: "event:one", published_revision_id: "revision:one" }),
    csrf: null,
    requestEpoch: 0,
  });

  const locator = {
    source_revision_id: "source:one", content_sha256: "a".repeat(64),
    page: 2, left: 0, top: 0, right: 1, bottom: 1,
  };
  render(<PdfAdventureEventReview worldId="rehearsal" locator={locator}
    text={"<|ref|>text<|/ref|><|det|>[[0,0,900,900]]<|/det|>\nThe bell sounds."} />);
  fireEvent.click(screen.getByText("Save as adventure Event"));
  expect(screen.getByLabelText("Event text")).toHaveValue("The bell sounds.");
  fireEvent.change(screen.getByLabelText("Event name"), { target: { value: "The alarm" } });
  fireEvent.change(screen.getByLabelText("Event text"), { target: { value: "The bell warns the villagers." } });
  fireEvent.click(screen.getByRole("button", { name: "Review Event" }));
  const publish = await screen.findByRole("button", { name: "Publish Event" });
  expect(request).toHaveBeenCalledTimes(1);
  expect(request.mock.calls[0][0]).toMatch(/\/prepare$/);
  expect(JSON.parse(String(request.mock.calls[0][1]?.body))).toMatchObject({
    name: "The alarm", description: "The bell warns the villagers.", region: locator,
  });

  fireEvent.click(publish);
  fireEvent.click(await screen.findByRole("button", { name: "Retry confirmation" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Published as prep");
  expect(request.mock.calls[1][0]).toMatch(/\/confirm$/);
  expect(request.mock.calls[2]).toEqual(request.mock.calls[1]);
});
