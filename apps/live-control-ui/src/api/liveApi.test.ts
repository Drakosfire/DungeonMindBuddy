import { afterEach, describe, expect, it, vi } from "vitest";

import { getArtifact, getCapabilities } from "./liveApi";

function mockJsonResponse(payload: unknown): Response {
  return {
    ok: true,
    status: 200,
    statusText: "OK",
    text: async () => JSON.stringify(payload),
  } as Response;
}

describe("liveApi artifact/capability helpers", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("getArtifact calls expected endpoint with target query params only", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(mockJsonResponse({ schema_version: "0.1.0" }));

    await getArtifact({ target_type: "roll_table", target_id: "T-WX" });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url] = fetchSpy.mock.calls[0];
    expect(String(url)).toContain("/api/live/artifact?");
    expect(String(url)).toContain("target_type=roll_table");
    expect(String(url)).toContain("target_id=T-WX");
    expect(String(url)).not.toContain("source_path");
    expect(String(url)).not.toContain("file_path");
    expect(String(url)).not.toContain("absolute_path");
    expect(String(url)).not.toContain("relative_path");
  });

  it("getCapabilities calls expected endpoint with target query params only", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(mockJsonResponse({ schema_version: "0.1.0", capabilities: [] }));

    await getCapabilities({ target_type: "event", target_id: "evt-1" });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url] = fetchSpy.mock.calls[0];
    expect(String(url)).toContain("/api/live/capabilities?");
    expect(String(url)).toContain("target_type=event");
    expect(String(url)).toContain("target_id=evt-1");
    expect(String(url)).not.toContain("source_path");
    expect(String(url)).not.toContain("file_path");
    expect(String(url)).not.toContain("absolute_path");
    expect(String(url)).not.toContain("relative_path");
  });
});
