import { afterEach, expect, it, vi } from "vitest";
import { confirmNativeWorldbuilding } from "../../api/nativeWorldbuildingPublicationApi";
import type { ExactRunReviewPackage } from "../../api/types";
import {
  submitNativeWorldbuildingConfirmation,
  retryNativeWorldbuildingConfirmation,
} from "./worldbuildingPublicationRecovery";

vi.mock("../../api/nativeWorldbuildingPublicationApi", () => ({
  confirmNativeWorldbuilding: vi.fn(),
}));

afterEach(() => {
  localStorage.clear();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

it("retains the submitted packet across response loss and refuses a replacement", async () => {
  vi.stubGlobal("navigator", {
    locks: { request: async (_key: string, action: () => unknown) => action() },
  });
  const review: ExactRunReviewPackage = {
    schema: "dmb_extract_promote_exact_run_review_v1",
    runId: "run:one", worldId: "elderwyld", sourceDomain: "worldbuilding",
    sourceArtifactId: "source:one", sourceRevisionId: "rev:source",
    sourceProse: "", assertions: [], diagnostics: [],
  };
  const packet = {
    envelope: {
      purpose: "dmb_native_worldbuilding_confirm_v1",
      prepared_change_id: "change:one",
      review: { managed_world_id: "elderwyld", run_id: "run:one" },
    },
    prepared: { operations: [] },
    token: "signed-fixture",
  };
  const confirm = vi.mocked(confirmNativeWorldbuilding);
  confirm.mockRejectedValueOnce(new Error("response lost"));
  await expect(submitNativeWorldbuildingConfirmation(review, "elderwyld", packet))
    .rejects.toThrow("response lost");
  await expect(submitNativeWorldbuildingConfirmation(review, "elderwyld", { ...packet, token: "replacement" }))
    .rejects.toThrow("Recover the original");
  confirm.mockResolvedValueOnce({ recovered: true, result: { child_revision_id: "rev:child" } });
  await expect(retryNativeWorldbuildingConfirmation(review, "elderwyld"))
    .resolves.toMatchObject({ recovered: true });
  expect(confirm.mock.calls).toEqual([[packet], [packet]]);
});
