import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { authenticatedApiFetch } from "../api/liveApi";
import { baseCandidateDefinition } from "../statblocks/editor/editorFixtures";
import { BuildPdfStatblockReview } from "./BuildPdfStatblockReview";

vi.mock("../api/liveApi", () => ({ authenticatedApiFetch: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("reopens a draft and saves edits against the exact retained regions", async () => {
  const definition = baseCandidateDefinition();
  const regions = [{ source_revision_id: "srev:test", content_sha256: "a".repeat(64),
    page: 2, left: 0, top: 0, right: 1, bottom: 1 }];
  const fetch = vi.mocked(authenticatedApiFetch);
  fetch.mockImplementation(async (path, init) => {
    if (init?.method === "PUT") {
      const payload = JSON.parse(String(init.body));
      expect(payload.expected_revision).toBe(4);
      expect(payload.regions).toEqual(regions);
      expect(payload.definition.identity.name).toBe("Revised creature");
      return { response: Response.json({ revision: 5, definition: payload.definition, regions }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>;
    }
    expect(path).toContain("/elderwyld/build-pdf-sources/statblock-reviews/review");
    return { response: Response.json({ revision: 4, definition, regions }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>;
  });

  render(<BuildPdfStatblockReview worldId="elderwyld" reviewId="review" />);
  const name = await screen.findByRole("textbox", { name: "Creature name" });
  fireEvent.change(name, { target: { value: "Revised creature" } });
  fireEvent.click(screen.getByRole("button", { name: "Save review draft" }));
  await waitFor(() => expect(screen.getByText("Draft saved")).toBeInTheDocument());
  expect(screen.getByRole("button", { name: "Open source region 1 · Page 2" })).toBeInTheDocument();
});
