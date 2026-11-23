import { afterEach, expect, it, vi } from "vitest";

const id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const scope = { worldId: "world", conversationId: id, turnId: id };

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
  vi.resetModules();
});

it("saves and reopens a portrait by the same exact operation key", async () => {
  vi.stubEnv("VITE_LIVE_API_BASE_URL", "");
  const api = await import("./conversationDraftApi");
  const fetch = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(Response.json({ status: "active", csrf_token: "test-csrf" }))
    .mockImplementation(async () => Response.json({ revision_id: "saved" }));
  const command: import("./conversationDraftApi").VariantPortraitSave = {
    operation_id: id,
    portrait_asset_id: id,
    base: {
      provider: "dungeonmind", statblock_id: "creature", revision_id: "rev_original",
      contract: "statblock", contract_version: "1", definition_digest: "sha256:example",
    },
  };

  await api.openSavedConversationVariant(scope, id);
  await api.saveConversationVariantPortrait(scope, id, command);
  await api.openSavedConversationVariant(scope, id, command.operation_id);

  expect(String(fetch.mock.calls[2][0])).toContain(`/variant-reviews/${id}/saved/portrait`);
  expect(fetch.mock.calls[2][1]).toMatchObject({method: "POST", body: JSON.stringify(command)});
  expect(new Headers(fetch.mock.calls[2][1]?.headers).get("X-DMB-Graph-CSRF")).toBe("test-csrf");
  expect(String(fetch.mock.calls[3][0])).toContain(`/saved?portrait_operation_id=${id}`);
});

it("uses the local GM session for variant review and confirmation", async () => {
  vi.stubEnv("VITE_LIVE_API_BASE_URL", "");
  const api = await import("./conversationDraftApi");
  const fetch = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(Response.json({ status: "active", csrf_token: "test-csrf" }))
    .mockImplementation(async () => Response.json({ revision_id: "saved" }));

  await api.openVariantReview(scope, id);
  await api.confirmVariantReview(scope, id);

  await api.openSavedConversationVariant(scope, id);

  expect(fetch).toHaveBeenCalledTimes(4);
  expect(String(fetch.mock.calls[3][0])).toContain(`/variant-reviews/${id}/saved`);
  expect(fetch.mock.calls[3][1]).toMatchObject({ credentials: "same-origin" });
  expect(String(fetch.mock.calls[1][0])).toContain(`/variant-reviews/${id}`);
  expect(fetch.mock.calls[2][1]).toMatchObject({ method: "POST", credentials: "same-origin" });
  expect(new Headers(fetch.mock.calls[2][1]?.headers).get("X-DMB-Graph-CSRF")).toBe("test-csrf");
});
