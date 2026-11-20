import { expect, it, vi } from "vitest";
import { authenticatedApiFetch } from "./liveApi";
import { confirmNativeWorldbuilding, prepareNativeWorldbuilding } from "./nativeWorldbuildingPublicationApi";

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

it("keeps held preparations unconfirmable and rejects a changed candidate", async () => {
  const fetch = vi.mocked(authenticatedApiFetch);
  const input = {
    managed_world_id: "elderwyld", run_id: "run:one", expected_run_revision: 2,
    candidate_sha256: "a".repeat(64), expected_parent_revision_id: "rev:parent",
    expected_source_authority_epoch: 3, workspace_document_id: "doc:one",
    workspace_document_revision: 4, selections: [],
  };
  const held = {
    status: "held", publication: "not_performed", run_id: input.run_id,
    run_revision: input.expected_run_revision, candidate_sha256: input.candidate_sha256,
    expected_parent_revision_id: input.expected_parent_revision_id,
    expected_source_authority_epoch: input.expected_source_authority_epoch,
    records: [], envelope: null, prepared: null, token: null,
  };
  fetch.mockImplementationOnce(async () => ({
    response: Response.json(held),
  }) as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  expect(await prepareNativeWorldbuilding(input)).toEqual({ status: "held", records: [] });
  expect(fetch).toHaveBeenLastCalledWith("/api/live/extract-promote/native-prepare",
    expect.objectContaining({ body: JSON.stringify(input) }));

  fetch.mockImplementationOnce(async () => ({
    response: Response.json({ ...held, candidate_sha256: "b".repeat(64) }),
  }) as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  await expect(prepareNativeWorldbuilding(input)).rejects.toThrow("changed the selected review scope");
});

it("accepts server defaults but refuses changed evidence in the signed review", async () => {
  const fetch = vi.mocked(authenticatedApiFetch);
  const input = {
    managed_world_id: "elderwyld", run_id: "run:one", expected_run_revision: 2,
    candidate_sha256: "a".repeat(64), expected_parent_revision_id: "rev:parent",
    expected_source_authority_epoch: 3, workspace_document_id: "doc:one",
    workspace_document_revision: 4,
    selections: [{kind: "node", record_id: "node:one", action: "create",
      facts: [{field: "label", metadata: {evidence_ref_ids: ["support:one"]}}]}],
  };
  const respond = (evidenceId: string) => fetch.mockImplementationOnce(async () => ({
    response: Response.json({
      ...input, run_revision: input.expected_run_revision, status: "prepared",
      publication: "not_performed", records: [], prepared: {}, token: "signed-fixture",
      envelope: {purpose: "dmb_native_worldbuilding_confirm_v1",
        review: {...input, selections: [{...input.selections[0], entity_id: null,
          facts: [{field: "label", index: null, metadata: {evidence_ref_ids: [evidenceId]}}]}]}},
    }),
  }) as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  respond("support:one");
  await expect(prepareNativeWorldbuilding(input)).resolves.toMatchObject({status: "prepared"});
  respond("support:other");
  await expect(prepareNativeWorldbuilding(input)).rejects.toThrow("Invalid native Worldbuilding confirmation packet");
});
