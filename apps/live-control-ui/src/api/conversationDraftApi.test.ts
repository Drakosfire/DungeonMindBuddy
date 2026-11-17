import { afterEach, expect, it, vi } from "vitest";

const id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const scope = { worldId: "world", conversationId: id, turnId: id };

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
  vi.resetModules();
});

it("uses the local GM session for variant review and confirmation", async () => {
  vi.stubEnv("VITE_LIVE_API_BASE_URL", "");
  const api = await import("./conversationDraftApi");
  const fetch = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(Response.json({ status: "active", csrf_token: "test-csrf" }))
    .mockImplementation(async () => Response.json({ revision_id: "saved" }));

  await api.openVariantReview(scope, id);
  await api.confirmVariantReview(scope, id);

  expect(fetch).toHaveBeenCalledTimes(3);
  expect(String(fetch.mock.calls[1][0])).toContain(`/variant-reviews/${id}`);
  expect(fetch.mock.calls[2][1]).toMatchObject({ method: "POST", credentials: "same-origin" });
  expect(new Headers(fetch.mock.calls[2][1]?.headers).get("X-DMB-Graph-CSRF")).toBe("test-csrf");
});
