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
