import { expect, it, vi } from "vitest";
import { authenticatedApiFetch } from "./liveApi";
import { confirmNativeWorldbuilding } from "./nativeWorldbuildingPublicationApi";

vi.mock("./liveApi", async (importOriginal) => ({
  ...await importOriginal<typeof import("./liveApi")>(),
  authenticatedApiFetch: vi.fn(),
}));

it("replays the exact confirmation packet and rejects a different publication", async () => {
  const fetch = vi.mocked(authenticatedApiFetch);
  const packet = {
    envelope: {
      purpose: "dmb_native_worldbuilding_confirm_v1",
      prepared_change_id: "change:one",
      review: { expected_parent_revision_id: "rev:parent" },
    },
    prepared: { operations: [] },
    token: "signed-fixture",
  };
  const result = {
    prepared_change_id: "change:one",
    dungeonmind_publication_id: "change:one",
    expected_parent_revision_id: "rev:parent",
    child_revision_id: "rev:child",
  };
  fetch.mockImplementation(async () => ({
    response: Response.json({ status: "committed", recovered: true, result }),
  }) as Awaited<ReturnType<typeof authenticatedApiFetch>>);

  expect((await confirmNativeWorldbuilding(packet)).result).toEqual(result);
  expect((await confirmNativeWorldbuilding(packet)).recovered).toBe(true);
  expect(fetch.mock.calls.map(([, init]) => init?.body)).toEqual([
    JSON.stringify(packet), JSON.stringify(packet),
  ]);

  fetch.mockImplementationOnce(async () => ({
    response: Response.json({
      status: "committed", recovered: false,
      result: { ...result, dungeonmind_publication_id: "change:other" },
    }),
  }) as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  await expect(confirmNativeWorldbuilding(packet)).rejects.toThrow("Invalid native Worldbuilding receipt");
});
