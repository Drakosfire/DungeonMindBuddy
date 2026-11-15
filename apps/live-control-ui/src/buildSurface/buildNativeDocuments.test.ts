import { beforeEach, expect, it, vi } from "vitest";
import { readBuildNativeDocument } from "./buildNativeDocuments";

const api = vi.hoisted(() => ({ getNativeSourceCatalog: vi.fn(), readNativeSource: vi.fn() }));
vi.mock("../api/liveApi", () => api);

const scope = {
  managed_world_id: "elderwyld", native_world_id: "space", scope_mode: "world",
  campaign_id: null, binding_version: 1, revision_id: "graph-revision",
};

beforeEach(() => {
  api.getNativeSourceCatalog.mockResolvedValue({
    schema: "dmb_native_source_catalog_v1", scope,
    catalogue: { space_id: "space", revision_id: "graph-revision", sources: [{
      source_artifact: { source_artifact_id: "recap" },
      source_revision: { source_revision_id: "saved", content_sha256: "digest" },
      evidence_ref_ids: ["evidence"], navigation: { label: "Session recap" },
    }] },
  });
});

it.each(["saved", "different"])("only renders the exact requested source revision (%s)", async revision => {
  api.readNativeSource.mockResolvedValue({
    schema: "dmb_native_source_body_v1", scope,
    source: { status: "available", source_artifact_id: "recap", source_revision_id: revision,
      evidence_ref_id: "evidence", body_sha256: "digest", body_text: "# Session notes" },
  });
  const result = readBuildNativeDocument("elderwyld", "saved", new AbortController().signal);
  if (revision === "saved") {
    await expect(result).resolves.toEqual({ title: "Session recap", markdown: "# Session notes" });
  } else {
    await expect(result).rejects.toThrow("The exact document revision is unavailable.");
  }
});
