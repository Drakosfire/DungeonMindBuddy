import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { authenticatedApiFetch } from "../api/liveApi";
import { StartPdfStatblockReview } from "./StartPdfStatblockReview";

vi.mock("../api/liveApi", () => ({ authenticatedApiFetch: vi.fn() }));
afterEach(cleanup);

it("starts a review with the imported definition and exact capture", async () => {
  const region = { source_revision_id: "srev:test", content_sha256: "a".repeat(64),
    page: 2, left: 0, top: 0, right: 0.5, bottom: 1 };
  const definition = { identity: { name: "Creature" } };
  const fetch = vi.mocked(authenticatedApiFetch);
  fetch.mockResolvedValue({ response: Response.json({ revision: 1 }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  render(<StartPdfStatblockReview worldId="elderwyld" region={region} />);
  fireEvent.click(screen.getByText("Import a statblock definition"));
  fireEvent.change(screen.getByLabelText("Statblock definition JSON"), {
    target: { files: [{ text: async () => JSON.stringify(definition) }] },
  });
  const link = await screen.findByRole("link", { name: "Open statblock review" });
  const id = new URL(link.getAttribute("href")!, "http://localhost").searchParams.get("pdfReview");
  expect(fetch).toHaveBeenCalledWith(
    `/api/live/agent/worlds/elderwyld/build-pdf-sources/statblock-reviews/${id}`,
    { method: "PUT", body: JSON.stringify({ definition, regions: [region], expected_revision: 0 }) },
  );
});
