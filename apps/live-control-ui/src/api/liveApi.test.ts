import { afterEach, describe, expect, it, vi } from "vitest";

import { getArtifact, getCapabilities, getStatblockWorkbenchDraft, getStatblockWorkbenchSample, listStatblockWorkbenchDrafts, postCommand, postStatblockWorkbenchCommand, previewStatblockCorpusPromotion, storeStatblockWorkbenchDraft } from "./liveApi";
import type { ProjectionCommand, ProjectionWriteResult, StoreStatblockDraftRequest } from "./types";

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


  it("getStatblockWorkbenchSample calls expected sample endpoint", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({
        schema_version: "dmb_statblock_workbench_sample_v1",
        mode: "sample_mock",
        artifact: {},
        command_status: "ok",
        diagnostics: [],
        available_actions: [],
      }),
    );

    await getStatblockWorkbenchSample();

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/statblocks/workbench/sample");
  });


  it("postStatblockWorkbenchCommand posts command body to Workbench command endpoint", async () => {
    const request = {
      command_type: "statblock.draft.generate" as const,
      requested_by: "human" as const,
      as_artifact: true,
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({
        schema_version: "dmb_statblock_workbench_command_v1",
        mode: "mock_command",
        artifact: null,
        command_status: "ok",
        diagnostics: [],
        available_actions: [],
      }),
    );

    await postStatblockWorkbenchCommand(request);

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/statblocks/workbench/command");
    expect(init?.method).toBe("POST");
    expect(init?.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(String(init?.body))).toEqual(request);
  });


  it("storeStatblockWorkbenchDraft posts draft body to Workbench drafts endpoint", async () => {
    const request: StoreStatblockDraftRequest = {
      source: "workbench",
      artifact: {
        artifact_id: "statblock-draft-test",
        draft_id: "draft-test",
        title: "Test",
        markdown: "## Test",
        structured_statblock: {},
        combat_defaults: {},
        warnings: [],
        provenance: {},
        review_status: "needs_dm_review",
        lifecycle_state: "live_draft",
        storage_status: "not_stored",
        corpus_status: "not_promoted",
        source_refs: [],
        breadcrumbs: [],
        created_by: "agent",
        created_at: "2026-06-09T00:00:00Z",
        updated_at: "2026-06-09T00:00:00Z",
      },
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ schema_version: "dmb_statblock_draft_store_v1", record: {}, diagnostics: [] }),
    );

    await storeStatblockWorkbenchDraft(request);

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/statblocks/workbench/drafts");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual(request);
  });

  it("listStatblockWorkbenchDrafts calls expected drafts endpoint", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ schema_version: "dmb_statblock_draft_list_v1", drafts: [] }),
    );

    await listStatblockWorkbenchDrafts();

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/statblocks/workbench/drafts");
  });

  it("getStatblockWorkbenchDraft encodes artifact id in read endpoint", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ schema_version: "dmb_statblock_draft_read_v1", record: {} }),
    );

    await getStatblockWorkbenchDraft("statblock:draft test");

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/statblocks/workbench/drafts/statblock%3Adraft%20test");
  });

  it("previewStatblockCorpusPromotion posts encoded preview request", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({
        schema_version: "dmb_statblock_corpus_promotion_preview_v1",
        preview_token: "preview-token",
      }),
    );

    await previewStatblockCorpusPromotion("statblock:draft test", {
      include_writer_allowlist_check: false,
    });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/statblocks/workbench/drafts/statblock%3Adraft%20test/corpus-preview");
    expect(init?.method).toBe("POST");
    expect(init?.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(String(init?.body))).toEqual({ include_writer_allowlist_check: false });
  });

  it("postCommand posts command body unchanged to commands endpoint", async () => {
    const command: ProjectionCommand = {
      command_type: "append_observation",
      target: {
        target_type: "roll_table",
        target_id: "T-WX",
        label: "Storm weather",
        source_status: "authoritative",
        metadata: {},
      },
      lane: "observed_play",
      payload: {
        observation: "Remember this as wagon axle pressure.",
        session_clock: "live-control",
        visibility: "live_note",
      },
      evidence: [],
      requested_by: {
        requester_type: "human_ui",
        requester_id: "live-control-ui",
      },
      idempotency_key: "ui-append-observation:roll_table:T-WX:test-id",
    };
    const expected: ProjectionWriteResult = {
      write_id: "write-test-1",
      status: "accepted",
      events_appended: ["evt-observation-1"],
      jobs_queued: [],
      artifacts_changed: [],
      invalidations: [
        {
          projection_key: "live.events",
          target: null,
          reason: "append_observation appended live event",
        },
      ],
      conflicts: [],
      diagnostics: [],
      metadata: {},
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(mockJsonResponse(expected));

    const response = await postCommand(command);

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/commands");
    expect(init?.method).toBe("POST");
    const body = JSON.parse(String(init?.body));
    expect(body).toEqual(command);
    expect(JSON.stringify(body)).not.toContain("source_path");
    expect(JSON.stringify(body)).not.toContain("file_path");
    expect(JSON.stringify(body)).not.toContain("absolute_path");
    expect(JSON.stringify(body)).not.toContain("relative_path");
    expect(response).toEqual(expected);
  });
});
