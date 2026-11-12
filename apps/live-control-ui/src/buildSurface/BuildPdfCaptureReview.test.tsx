import {fireEvent, render, screen} from "@testing-library/react";
import {expect, it, vi} from "vitest";
import {authenticatedApiFetch} from "../api/liveApi";
import {CropOcr} from "./BuildPdfPreview";

vi.mock("../api/liveApi", () => ({authenticatedApiFetch: vi.fn()}));

const region = {
  source_revision_id: "srev:fixture", content_sha256: "fixture",
  page: 5, left: 0, top: 0, right: 0.48, bottom: 0.44,
};

it.each([true, false])("renders only a reply for the submitted crop (%s)", async matches => {
  vi.mocked(authenticatedApiFetch).mockResolvedValueOnce({
    response: Response.json({
      text: "Armor Class 16",
      region: {...region, page: matches ? 5 : 6},
    }),
  } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  render(<CropOcr worldId="elderwyld" region={region} hasPdfText />);
  fireEvent.change(screen.getByLabelText("Instructions for Buddy (optional)"), {
    target: {value: "Extract only AC."},
  });
  fireEvent.click(screen.getByRole("button", {name: "Ask Buddy about this capture"}));
  expect(authenticatedApiFetch).toHaveBeenCalledWith(
    "/api/live/agent/worlds/elderwyld/build-pdf-sources/review",
    {method: "POST", body: JSON.stringify({region, instruction: "Extract only AC."})},
  );
  if (matches) {
    const result = await screen.findByLabelText("Buddy’s review · Page 5") as HTMLTextAreaElement;
    expect(result.value).toBe("Armor Class 16");
  } else {
    expect((await screen.findByRole("alert")).textContent).toMatch(/did not match/);
    expect(screen.queryByLabelText("Buddy’s review · Page 5")).toBeNull();
  }
});

it("previews a statblock found by local OCR against the submitted source region", async () => {
  vi.mocked(authenticatedApiFetch).mockResolvedValueOnce({
    response: Response.json({
      text: "Grotesque Tree\nHuge plant, unaligned\nArmor Class 11 (natural armor)\nHit Points 39 (6d8+12)\nSTR DEX CON INT WIS CHA\n17 (+3) 9 (-1) 15 (+2) 7 (-2) 10 (0) 10 (0)",
    }),
  } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  render(<CropOcr worldId="elderwyld" region={region} hasPdfText />);
  fireEvent.click(screen.getByRole("button", {name: "Try OCR instead"}));
  fireEvent.click(await screen.findByRole("button", {name: "Preview statblock fields"}));
  expect(screen.getByText("Page 5 · srev:fixture")).toBeInTheDocument();
  expect(screen.getByText("11")).toBeInTheDocument();
  expect(screen.getByText("39 (6d8+12)")).toBeInTheDocument();
  expect(vi.mocked(authenticatedApiFetch)).toHaveBeenCalledWith(
    "/api/live/agent/worlds/elderwyld/build-pdf-sources/ocr",
    {method: "POST", body: JSON.stringify(region)},
  );
});

it("does not offer a statblock candidate for ordinary OCR prose", async () => {
  vi.mocked(authenticatedApiFetch).mockResolvedValueOnce({
    response: Response.json({text: "The Greenfields lie south-east of Baldur’s Gate."}),
  } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  render(<CropOcr worldId="elderwyld" region={region} hasPdfText />);
  fireEvent.click(screen.getByRole("button", {name: "Try OCR instead"}));
  expect(await screen.findByLabelText("OCR transcription")).toBeInTheDocument();
  expect(screen.queryByRole("button", {name: "Preview statblock fields"})).toBeNull();
});

it("does not associate isolated OCR armor and hit-point labels as one statblock", async () => {
  vi.mocked(authenticatedApiFetch).mockResolvedValueOnce({
    response: Response.json({text: "Workshop notes\nArmor Class 11\nThe creature had Hit Points 39 in an unrelated caption."}),
  } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  render(<CropOcr worldId="elderwyld" region={region} hasPdfText />);
  fireEvent.click(screen.getByRole("button", {name: "Try OCR instead"}));
  expect(await screen.findByLabelText("OCR transcription")).toBeInTheDocument();
  expect(screen.queryByRole("button", {name: "Preview statblock fields"})).toBeNull();
});

it("keeps image-only OCR as an image result without a statblock candidate", async () => {
  vi.mocked(authenticatedApiFetch).mockResolvedValueOnce({
    response: Response.json({text: "<|ref|>image<|/ref|><|det|>[[0,0,100,100]]<|/det|>"}),
  } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  render(<CropOcr worldId="elderwyld" region={region} hasPdfText={false} />);
  fireEvent.click(screen.getByRole("button", {name: "Read capture with OCR"}));
  expect(await screen.findByText("OCR found an image in this region without transcribing any text.")).toBeInTheDocument();
  expect(screen.queryByRole("button", {name: "Preview statblock fields"})).toBeNull();
});
