import { afterEach, describe, expect, it, vi } from "vitest";

import {
  activateStatblockRetrieval,
  addGeneratedStatblockToCombat,
  advanceCombatTurn,
  applyCombatHpDelta,
  commitStatblockCorpusWrite,
  commitTiptapMarkdownWrite,
  getArtifact,
  getCapabilities,
  getGraphIngestRuns,
  getGoldGraphProjection,
  getLatestGraphIngestRun,
  getUnionSupergraphProjection,
  postWorldGraphProjection,
  getCurrentCombat,
  getGeneratedStatblock,
  getStatblockWorkbenchDraft,
  getStatblockWorkbenchSample,
  listGeneratedStatblocks,
  listStatblockWorkbenchDrafts,
  patchCombatEntity,
  postCommand,
  postCitationSource,
  postStatblockWorkbenchCommand,
  prepareStatblockCorpusWrite,
  prepareTiptapMarkdownWrite,
  previewStatblockCorpusPromotion,
  setCombatActiveTurn,
  sortCombatInitiative,
  storeStatblockWorkbenchDraft,
  verifyStatblockRetrieval,
} from "./liveApi";
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

  it("getGraphIngestRuns builds expected query string", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ schema_version: "dmb_graph_ingest_run_registry_v1", version: "1", runs: [] }),
    );

    await getGraphIngestRuns({
      campaignId: "c2",
      sessionId: "session-22",
      status: "preview_union_store_ready",
      requirePreviewUnionStore: true,
    });

    const [url] = fetchSpy.mock.calls[0];
    expect(String(url)).toContain("/api/live/graph-preview/graph-ingest/runs?");
    expect(String(url)).toContain("campaign_id=c2");
    expect(String(url)).toContain("session_id=session-22");
    expect(String(url)).toContain("status=preview_union_store_ready");
    expect(String(url)).toContain("require_preview_union_store=true");
  });

  it("getLatestGraphIngestRun calls expected endpoint", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ schema_version: "dmb_graph_ingest_run_registry_v1", version: "1", run: null }),
    );

    await getLatestGraphIngestRun("c2", "session-22", "corpus/recap.md", "sha256:abc");

    const [url] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe(
      "/api/live/graph-preview/graph-ingest/latest?campaign_id=c2&session_id=session-22&source_recap_path=corpus%2Frecap.md&source_recap_sha256=sha256%3Aabc",
    );
  });

  it("getUnionSupergraphProjection supports latest graph-ingest mode", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ campaign_id: "c2", session_id: "session-22", focus: {}, node_views: {}, mentions: [] }),
    );

    await getUnionSupergraphProjection({
      campaignId: "c2",
      sessionId: "session-22",
      useLatestGraphIngest: true,
      sourceRecapPath: "corpus/recap.md",
      sourceRecapSha256: "sha256:abc",
    });

    const [url] = fetchSpy.mock.calls[0];
    expect(String(url)).toContain("/api/live/graph-preview/union-supergraph/projection?");
    expect(String(url)).toContain("campaign_id=c2");
    expect(String(url)).toContain("session_id=session-22");
    expect(String(url)).toContain("use_latest_graph_ingest=true");
    expect(String(url)).toContain("source_recap_path=corpus%2Frecap.md");
    expect(String(url)).toContain("source_recap_sha256=sha256%3Aabc");
    expect(String(url)).not.toContain("preview_source=");
  });

  it("getUnionSupergraphProjection supports recap-only mode", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ campaign_id: "c2", session_id: "session-24", focus: {}, node_views: {}, mentions: [] }),
    );

    await getUnionSupergraphProjection({
      campaignId: "c2",
      sessionId: "session-24",
      allowRecapOnly: true,
    });

    const [url] = fetchSpy.mock.calls[0];
    expect(String(url)).toContain("/api/live/graph-preview/union-supergraph/projection?");
    expect(String(url)).toContain("campaign_id=c2");
    expect(String(url)).toContain("session_id=session-24");
    expect(String(url)).toContain("allow_recap_only=true");
  });

  it("getUnionSupergraphProjection preserves previewSource fallback", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ campaign_id: "c2", session_id: "session-23", focus: {}, node_views: {}, mentions: [] }),
    );

    await getUnionSupergraphProjection("session-23", "dogfood-preview");

    const [url] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe(
      "/api/live/graph-preview/union-supergraph/projection?session_id=session-23&preview_source=dogfood-preview",
    );
  });

  it("postWorldGraphProjection posts only the World Graph request contract", async () => {
    const request = {
      schema: "dmb_world_graph_projection_request_v1" as const,
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      focus: { kind: "session" as const, sessionId: "session-21" },
      admissibility: "gm" as const,
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({
        schema: "dmb_world_graph_projection_v1",
        snapshot: {},
        summary: {},
        nodes: [],
        relationships: [],
        attributes: [],
        evidence: [],
        sourceArtifacts: [],
        diagnostics: [],
      }),
    );

    await postWorldGraphProjection(request);

    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/world-graph/projection");
    expect(String(url)).not.toContain("?");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual(request);
    expect(Object.keys(JSON.parse(String(init?.body)))).toEqual([
      "schema",
      "worldId",
      "campaignId",
      "focus",
      "admissibility",
    ]);
  });

  it("getGoldGraphProjection calls gold projection endpoint with read-only query params", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({
        campaign_id: "longmont-c1",
        session_id: "session-1",
        source_kind: "gold_fixture",
        gold_fixture_id: "graph-memory:session-1-candidate-graph-gold:v0",
        gold_fixture_relpath: "evals/graph_memory_layer/examples/session_1_candidate_graph_gold/candidate_graph_gold.json",
        focus: {},
        node_views: {},
        mentions: [],
      }),
    );

    await getGoldGraphProjection({
      campaignId: "longmont-c1",
      sessionId: "session-1",
    });

    const [url] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe(
      "/api/live/graph-preview/gold-review/projection?campaign_id=longmont-c1&session_id=session-1",
    );
    expect(String(url)).not.toContain("/author");
    expect(String(url)).not.toContain("/write");
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

  it("listGeneratedStatblocks calls expected generated view endpoint", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ schema_version: "dmb_generated_statblock_list_v1", statblocks: [], diagnostics: [] }),
    );

    await listGeneratedStatblocks();

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/statblocks/view/generated");
  });

  it("getGeneratedStatblock encodes artifact id in generated view endpoint", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ schema_version: "dmb_generated_statblock_detail_v1" }),
    );

    await getGeneratedStatblock("statblock:draft test");

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/statblocks/view/generated/statblock%3Adraft%20test");
  });

  it("getCurrentCombat calls expected current combat endpoint", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ schema: "dmb_combat_encounter_state_v1", entities: [] }),
    );

    await getCurrentCombat();

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/combat/current");
  });

  it("combat roster mutation helpers call expected endpoints", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({
        schema_version: "dmb_combat_mutation_v1",
        encounter: { entities: [] },
        diagnostics: [],
      }),
    );

    await patchCombatEntity("entity:one", { notes: "bloodied" });
    await applyCombatHpDelta("entity:one", { action: "damage", amount: 7 });
    await sortCombatInitiative();
    await setCombatActiveTurn({ entity_id: "entity:one" });
    await advanceCombatTurn({ direction: "previous" });

    expect(fetchSpy).toHaveBeenCalledTimes(5);
    expect(String(fetchSpy.mock.calls[0][0])).toBe(
      "/api/live/combat/current/entities/entity%3Aone",
    );
    expect(fetchSpy.mock.calls[0][1]?.method).toBe("PATCH");
    expect(String(fetchSpy.mock.calls[1][0])).toBe(
      "/api/live/combat/current/entities/entity%3Aone/hp-delta",
    );
    expect(fetchSpy.mock.calls[1][1]?.method).toBe("POST");
    expect(String(fetchSpy.mock.calls[2][0])).toBe("/api/live/combat/current/sort-initiative");
    expect(String(fetchSpy.mock.calls[3][0])).toBe("/api/live/combat/current/active-turn");
    expect(String(fetchSpy.mock.calls[4][0])).toBe("/api/live/combat/current/turn");
  });

  it("addGeneratedStatblockToCombat posts encoded add request", async () => {
    const request = { team: "enemy" as const, count: 2, initiative: 17 };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ schema_version: "dmb_add_generated_statblock_to_combat_v1" }),
    );

    await addGeneratedStatblockToCombat("statblock:draft test", request);

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/statblocks/view/generated/statblock%3Adraft%20test/combat/add");
    expect(init?.method).toBe("POST");
    expect(init?.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(String(init?.body))).toEqual(request);
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

  it("prepareStatblockCorpusWrite posts encoded prepare request", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ schema_version: "dmb_statblock_corpus_write_prepare_v1" }),
    );

    await prepareStatblockCorpusWrite("statblock:draft test", {
      preview_token: "preview-token",
    });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/statblocks/workbench/drafts/statblock%3Adraft%20test/corpus-write/prepare");
    expect(init?.method).toBe("POST");
    expect(init?.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(String(init?.body))).toEqual({ preview_token: "preview-token" });
  });

  it("commitStatblockCorpusWrite posts encoded commit request", async () => {
    const request = { preview_token: "preview-token", writer_confirm_token: "writer-token" };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ schema_version: "dmb_statblock_corpus_write_commit_v1" }),
    );

    await commitStatblockCorpusWrite("statblock:draft test", request);

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/statblocks/workbench/drafts/statblock%3Adraft%20test/corpus-write/commit");
    expect(init?.method).toBe("POST");
    expect(init?.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(String(init?.body))).toEqual(request);
  });

  it("posts Tiptap Markdown prepare and commit requests", async () => {
    const request = {
      document_id: "doc",
      title: "Title",
      target_relpath: "evals/c2_live_prep/mireward-prep/content/tiptap/doc.md",
      markdown: "# Title",
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(mockJsonResponse({ schema_version: "dmb_tiptap_markdown_write_prepare_v1" }))
      .mockResolvedValueOnce(mockJsonResponse({ schema_version: "dmb_tiptap_markdown_write_commit_v1" }));

    await prepareTiptapMarkdownWrite(request);
    await commitTiptapMarkdownWrite({ ...request, writer_confirm_token: "token" });

    expect(String(fetchSpy.mock.calls[0][0])).toBe("/api/live/tiptap/markdown-write/prepare");
    expect(JSON.parse(String(fetchSpy.mock.calls[0][1]?.body))).toEqual(request);
    expect(String(fetchSpy.mock.calls[1][0])).toBe("/api/live/tiptap/markdown-write/commit");
    expect(JSON.parse(String(fetchSpy.mock.calls[1][1]?.body))).toEqual({
      ...request,
      writer_confirm_token: "token",
    });
  });

  it("activateStatblockRetrieval posts encoded activation request", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ schema_version: "dmb_statblock_retrieval_activation_v1" }),
    );

    await activateStatblockRetrieval("statblock:draft test");

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/statblocks/workbench/drafts/statblock%3Adraft%20test/retrieval/activate");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({});
  });

  it("verifyStatblockRetrieval posts encoded verification request", async () => {
    const request = { query: "Find generated statblock AC" };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ schema_version: "dmb_statblock_retrieval_verify_v1" }),
    );

    await verifyStatblockRetrieval("statblock:draft test", request);

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/statblocks/workbench/drafts/statblock%3Adraft%20test/retrieval/verify");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual(request);
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

describe("liveApi citation source helper", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("postCitationSource posts to /api/live/citation-source with path body", async () => {
    const expected = {
      schema_version: "dmb_citation_source_v1",
      path: "corpus/locations/north_reach_gate.md",
      content_type: "text/markdown",
      content: "# North Reach Gate",
      truncated: false,
      highlight: {
        line_start: null,
        line_end: null,
        text_excerpt: null,
        match_source: "none",
      },
      diagnostics: [],
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(mockJsonResponse(expected));

    const response = await postCitationSource({ path: "corpus/locations/north_reach_gate.md" });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/citation-source");
    expect(init?.method).toBe("POST");
    const body = JSON.parse(String(init?.body));
    expect(body).toEqual({ path: "corpus/locations/north_reach_gate.md" });
    expect(response).toEqual(expected);
  });
});
