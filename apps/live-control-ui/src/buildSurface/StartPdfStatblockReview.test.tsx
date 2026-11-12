import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { authenticatedApiFetch } from "../api/liveApi";
import { StartPdfStatblockReview } from "./StartPdfStatblockReview";

vi.mock("../api/liveApi", () => ({ authenticatedApiFetch: vi.fn() }));
afterEach(cleanup);

const first = { source_revision_id: "srev:test", content_sha256: "a".repeat(64),
  page: 1, left: 0, top: 0, right: 0.5, bottom: 1 };
const second = { ...first, page: 2, left: 0.5, right: 1 };

it("creates a review from multiple selected source regions and guidance", async () => {
  const fetch = vi.mocked(authenticatedApiFetch);
  fetch.mockResolvedValue({ response: Response.json({ revision: 1 }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  render(<StartPdfStatblockReview worldId="elderwyld" regions={[first, second]} onRemoveRegion={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Guidance for Buddy (optional)"), {
    target: { value: "Preserve the printed action names." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create statblock review" }));
  const link = await screen.findByRole("link", { name: "Open statblock review" });
  const id = new URL(link.getAttribute("href")!, "http://localhost").searchParams.get("pdfReview");
  expect(fetch).toHaveBeenCalledWith(
    `/api/live/agent/worlds/elderwyld/build-pdf-sources/statblock-reviews/${id}/from-regions`,
    { method: "POST", body: JSON.stringify({
      regions: [first, second], instruction: "Preserve the printed action names.",
    }) },
  );
});

it("lets the author remove a selected region before extraction", () => {
  const onRemoveRegion = vi.fn();
  render(<StartPdfStatblockReview worldId="elderwyld" regions={[first, second]} onRemoveRegion={onRemoveRegion} />);
  fireEvent.click(screen.getAllByRole("button", { name: "Remove" })[0]);
  expect(onRemoveRegion).toHaveBeenCalledWith(first);
});

it("shows incomplete extraction details without opening or saving a review", async () => {
  const fetch = vi.mocked(authenticatedApiFetch);
  fetch.mockResolvedValue({ response: Response.json({ detail: {
    code: "pdf_statblock_extraction_incomplete", missing_details: ["Hit Points", "ability scores"],
  } }, { status: 422 }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  render(<StartPdfStatblockReview worldId="elderwyld" regions={[first]} onRemoveRegion={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Create statblock review" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Hit Points; ability scores");
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});

it("explains an invalid structured response without offering a saved review", async () => {
  const fetch = vi.mocked(authenticatedApiFetch);
  fetch.mockResolvedValue({ response: Response.json({ detail: {
    code: "pdf_statblock_output_invalid",
  } }, { status: 502 }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  render(<StartPdfStatblockReview worldId="elderwyld" regions={[first]} onRemoveRegion={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Create statblock review" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("No review was saved");
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});

it("offers an existing review after a conflict", async () => {
  const fetch = vi.mocked(authenticatedApiFetch);
  fetch.mockResolvedValue({ response: new Response(null, { status: 409 }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  render(<StartPdfStatblockReview worldId="elderwyld" regions={[first]} onRemoveRegion={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Create statblock review" }));
  expect(await screen.findByRole("link", { name: "Open existing statblock review" })).toBeInTheDocument();
});
