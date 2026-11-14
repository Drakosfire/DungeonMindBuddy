import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { authenticatedApiFetch } from "../api/liveApi";
import { StartPdfStatblockReview } from "./StartPdfStatblockReview";

vi.mock("../api/liveApi", () => ({ authenticatedApiFetch: vi.fn() }));
afterEach(() => {
  cleanup();
  window.history.replaceState(null, "", "/");
});

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
  expect(await screen.findByRole("alert")).toHaveTextContent("Hit Points; ability scores. (pdf_statblock_extraction_incomplete)");
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});

it("explains an invalid structured response without offering a saved review", async () => {
  const fetch = vi.mocked(authenticatedApiFetch);
  fetch.mockResolvedValue({ response: Response.json({ detail: {
    code: "pdf_statblock_output_invalid",
  } }, { status: 502 }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  render(<StartPdfStatblockReview worldId="elderwyld" regions={[first]} onRemoveRegion={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Create statblock review" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("pdf_statblock_output_invalid");
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});

it("surfaces the generation failure code with an actionable explanation", async () => {
  const fetch = vi.mocked(authenticatedApiFetch);
  fetch.mockResolvedValue({ response: Response.json({ detail: {
    code: "pdf_statblock_generation_unavailable",
  } }, { status: 503 }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  render(<StartPdfStatblockReview worldId="elderwyld" regions={[first]} onRemoveRegion={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Create statblock review" }));
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("could not generate a structured statblock");
  expect(alert).toHaveTextContent("pdf_statblock_generation_unavailable");
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});

it("shows a safe unknown error code without exposing server detail", async () => {
  const fetch = vi.mocked(authenticatedApiFetch);
  fetch.mockResolvedValue({ response: Response.json({ detail: {
    code: "pdf_statblock_internal_error", message: "private server details",
  } }, { status: 500 }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  render(<StartPdfStatblockReview worldId="elderwyld" regions={[first]} onRemoveRegion={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Create statblock review" }));
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("pdf_statblock_internal_error");
  expect(alert).not.toHaveTextContent("private server details");
});

it("offers an existing review after a conflict", async () => {
  const fetch = vi.mocked(authenticatedApiFetch);
  fetch.mockResolvedValue({ response: new Response(null, { status: 409 }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  render(<StartPdfStatblockReview worldId="elderwyld" regions={[first]} onRemoveRegion={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Create statblock review" }));
  expect(await screen.findByRole("link", { name: "Open existing statblock review" })).toBeInTheDocument();
});

it("prepares the current crop and routes directly to the saved editor", async () => {
  const fetch = vi.mocked(authenticatedApiFetch);
  fetch.mockClear();
  fetch.mockResolvedValue({ response: Response.json({ revision: 1 }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  const prepareRegions = vi.fn(async () => {
    expect(fetch).not.toHaveBeenCalled();
    return [first];
  });
  render(<StartPdfStatblockReview worldId="elderwyld" regions={[]} onRemoveRegion={vi.fn()}
    prepareRegions={prepareRegions} />);
  fireEvent.click(screen.getByRole("button", { name: "Extract statblock" }));
  const savedLink = await screen.findByRole("link", { name: "Open statblock review" });
  const restored = new URL(window.location.href);
  expect(restored.searchParams.get("world")).toBe("elderwyld");
  expect(restored.searchParams.get("pdfReview")).toBe(
    new URL(savedLink.getAttribute("href")!, restored).searchParams.get("pdfReview"),
  );
  expect(prepareRegions).toHaveBeenCalledOnce();
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/from-regions"), {
    method: "POST", body: JSON.stringify({ regions: [first], instruction: "" }),
  });
});

it("does not rewrite the destination URL when extraction completes after navigation", async () => {
  const fetch = vi.mocked(authenticatedApiFetch);
  let finish!: (result: Awaited<ReturnType<typeof authenticatedApiFetch>>) => void;
  fetch.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  window.history.replaceState(null, "", "/build?world=elderwyld");
  render(<StartPdfStatblockReview worldId="elderwyld" regions={[]} onRemoveRegion={vi.fn()}
    prepareRegions={async () => [first]} />);
  fireEvent.click(screen.getByRole("button", { name: "Extract statblock" }));
  await Promise.resolve();
  window.history.replaceState(null, "", "/plan?world=another");
  finish({ response: Response.json({ revision: 1 }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  await screen.findByRole("link", { name: "Open statblock review" });
  expect(window.location.pathname + window.location.search).toBe("/plan?world=another");
});

it("extracts both full pages without a crop and opens the editor", async () => {
  const fetch = vi.mocked(authenticatedApiFetch);
  fetch.mockClear();
  fetch.mockResolvedValue({ response: Response.json({ revision: 1 }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  const pages = [1, 2].map(page => ({ ...first, page, left: 0, top: 0, right: 1, bottom: 1 }));
  render(<StartPdfStatblockReview worldId="elderwyld" regions={[]} onRemoveRegion={vi.fn()}
    prepareWholePdf={async () => pages} />);
  fireEvent.click(screen.getByRole("button", { name: "Extract whole PDF" }));
  await screen.findByRole("link", { name: "Open statblock review" });
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/from-regions"), {
    method: "POST", body: JSON.stringify({ regions: pages, instruction: "" }),
  });
  expect(new URL(window.location.href).searchParams.get("pdfReview")).toBeTruthy();
});
