import { afterEach, describe, expect, it, vi } from "vitest";

import {
  activateStatblockRetrieval,
  addGeneratedStatblockToCombat,
  advanceCombatTurn,
  applyCombatHpDelta,
  commitStatblockCorpusWrite,
  commitTiptapMarkdownWrite,
  createWorkspaceDocument,
  DEFAULT_PLANNING_MANIFEST_PATH,
  getArtifact,
  getCapabilities,
  getGraphIngestRuns,
  getGoldGraphProjection,
  getLatestGraphIngestRun,
  getUnionSupergraphProjection,
  LiveApiError,
  listWorkspaceDocuments,
  postLiveQuery,
  postWorldGraphProjection,
  postWorldGraphSourceAnchorRead,
  getCurrentCombat,
  getGeneratedStatblock,
  getStatblockWorkbenchDraft,
  getStatblockWorkbenchSample,
  getStatblockCandidate,
  createThreatDraft,
  generateThreatDraftCandidate,
  validateStatblockDefinition,
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
import type {
  CreateWorkspaceDocumentRequest,
  ProjectionCommand,
  ProjectionWriteResult,
  StoreStatblockDraftRequest,
  TiptapMarkdownWritePrepareResponse,
  WorkspaceDocumentRecord,
} from "./types";

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

  it("generateThreatDraftCandidate posts to exact draft generate route", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({
        schema: "dmb_generate_threat_draft_candidate_response_v1",
        draft_id: "draft-1",
        generated_from_draft_version: 1,
        request_id: "req-1",
        outcome: "success",
        candidate_ref: {
          candidate_id: "cand-1",
          generated_from_draft_version: 1,
          request_id: "req-1",
          created_at: "2026-01-01T00:00:00Z",
          status: "active",
        },
        candidate: { candidate_id: "cand-1" },
        cache_status: "stored",
      }),
    );

    await generateThreatDraftCandidate("draft-1", { expected_draft_version: 1 });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/threat-drafts/draft-1/candidates:generate");
    expect(init?.method).toBe("POST");
  });

  it("createThreatDraft posts to threat-drafts collection", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({
        schema: "dmb_threat_draft_v1",
        draft_id: "11111111-1111-1111-1111-111111111111",
        version: 1,
        world_id: "world_eldyrwild",
        campaign_id: "campaign_longmont_c2",
        name: "Gate Warden",
        description: "Guards the gate.",
        threat_kind: "creature",
        workflow_state: "drafting",
        created_by: "gm-workbench",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      }),
    );

    await createThreatDraft({
      world_id: "world_eldyrwild",
      campaign_id: "campaign_longmont_c2",
      name: "Gate Warden",
      description: "Guards the gate.",
      threat_kind: "creature",
      generation_intent: { ruleset: { system: "dnd5e", edition: "2024" } },
      graph_context_snapshot: {
        graph_revision_id: "rev_workbench_quick_create",
        selected_node_ids: ["node_workbench_placeholder"],
        admitted_source_anchor_ids: ["anchor_workbench_placeholder"],
      },
      created_by: "gm-workbench",
    });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/threat-drafts");
    expect(init?.method).toBe("POST");
  });

  it("getStatblockCandidate reads exact candidate id", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({
        schema: "dmb_statblock_candidate_read_v1",
        candidate_id: "cand-1",
        status: "active",
        candidate: { candidate_id: "cand-1" },
      }),
    );

    await getStatblockCandidate("cand-1");

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/statblock-candidates/cand-1");
  });

  it("validateStatblockDefinition posts exact working-copy definition", async () => {
    const definition = { identity: { name: "Test" } };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({
        schema: "dmb_statblock_definition_validation_v1",
        outcome: "success",
        definition_digest: "sha256:abc",
        validation_receipt: {
          status: "valid",
          mode: "editor_preview",
          validator_version: "1",
          canonicalizer_version: "1",
          definition_digest: "sha256:abc",
          issues: [],
        },
      }),
    );

    await validateStatblockDefinition({ definition: definition as never });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/statblock-definitions:validate");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({ definition });
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
      document_id: "11111111-1111-4111-8111-111111111111",
      markdown: "# Title",
      expected_revision: 2,
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

describe("liveApi World Graph error preservation", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("preserves World Graph error code and diagnostics on LiveApiError", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 409,
      statusText: "Conflict",
      text: async () =>
        JSON.stringify({
          schema: "dmb_world_graph_projection_error_v1",
          code: "projection_integrity_error",
          message: "Projection integrity check failed.",
          statusCode: 409,
          diagnostics: [
            {
              code: "missing_node",
              message: "Node npc-glowkindle is missing.",
              severity: "error",
            },
          ],
        }),
    } as Response);

    await expect(
      postWorldGraphProjection({
        schema: "dmb_world_graph_projection_request_v1",
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        focus: { kind: "session", sessionId: "session-21" },
        admissibility: "gm",
      }),
    ).rejects.toMatchObject({
      name: "LiveApiError",
      status: 409,
      message: "Projection integrity check failed.",
      code: "projection_integrity_error",
      diagnostics: [
        {
          code: "missing_node",
          message: "Node npc-glowkindle is missing.",
          severity: "error",
        },
      ],
    });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });
});

describe("liveApi postLiveQuery Hermes serializer", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("omits manifest_path and hermes_session_id for Hermes requests", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ answer: "ok", classification: {} }),
    );

    await postLiveQuery("Who is Glowkindle?", "longmont-c2", 22, "hermes", {
      hermesSessionId: "hermes-session-should-not-send",
      hermesSessionPointer: "hptr-should-send",
      agentThreadId: "thread-1",
      traceRequested: true,
    });

    const [, init] = fetchSpy.mock.calls[0];
    const body = JSON.parse(String(init?.body)) as Record<string, unknown>;
    expect(body).not.toHaveProperty("manifest_path");
    expect(body).not.toHaveProperty("hermes_session_id");
    expect(body).toMatchObject({
      campaign_id: "longmont-c2",
      session: 22,
      mode: "live",
      query_backend: "hermes",
      text: "Who is Glowkindle?",
      agent_thread_id: "thread-1",
      trace_requested: true,
      hermes_session_pointer: "hptr-should-send",
    });
  });

  it("includes manifest_path and hermes_session_id for live requests", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ answer: "ok", classification: {} }),
    );

    await postLiveQuery("Who is Glowkindle?", "longmont-c2", 22, "live", {
      hermesSessionId: "hermes-session-live",
      agentThreadId: "thread-2",
      traceRequested: false,
    });

    const [, init] = fetchSpy.mock.calls[0];
    const body = JSON.parse(String(init?.body)) as Record<string, unknown>;
    expect(body).toHaveProperty("manifest_path", DEFAULT_PLANNING_MANIFEST_PATH);
    expect(body).toHaveProperty("hermes_session_id", "hermes-session-live");
    expect(body).toMatchObject({
      campaign_id: "longmont-c2",
      session: 22,
      mode: "live",
      query_backend: "live",
      text: "Who is Glowkindle?",
      agent_thread_id: "thread-2",
      trace_requested: false,
    });
  });

  it("includes world_graph_context for Hermes when provided and omits prior-turn fields", async () => {
    const worldGraphContext = {
      schema: "dmb_agent_world_graph_query_context_request_v1" as const,
      world_id: "eldyrwild",
      campaign_id: "longmont-c2",
      focus: { kind: "session" as const, session_id: "session-22" },
      admissibility: "gm" as const,
      revision_pin: null,
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ answer: "ok", classification: {} }),
    );

    await postLiveQuery("Tripod threat?", "longmont-c2", 22, "hermes", {
      worldGraphContext,
    });

    const [, init] = fetchSpy.mock.calls[0];
    const body = JSON.parse(String(init?.body)) as Record<string, unknown>;
    expect(body.world_graph_context).toEqual(worldGraphContext);
    expect(body).not.toHaveProperty("prior_turns");
    expect(body).not.toHaveProperty("history");
    expect(body).not.toHaveProperty("capability_policy");
    expect(body).not.toHaveProperty("graph_root");
  });

  it("omits conversation_history on first Hermes turn and includes normalized pairs on follow-up", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ answer: "ok", classification: {} }),
    );

    await postLiveQuery("First question?", "longmont-c2", 22, "hermes");
    let body = JSON.parse(String(fetchSpy.mock.calls[0][1]?.body)) as Record<string, unknown>;
    expect(body).not.toHaveProperty("conversation_history");

    await postLiveQuery("Follow-up?", "longmont-c2", 22, "hermes", {
      conversationHistory: [
        { role: "user", content: "First question?" },
        { role: "assistant", content: "First answer." },
      ],
    });
    body = JSON.parse(String(fetchSpy.mock.calls[1][1]?.body)) as Record<string, unknown>;
    expect(body.conversation_history).toEqual([
      { role: "user", content: "First question?" },
      { role: "assistant", content: "First answer." },
    ]);
    expect(body.text).toBe("Follow-up?");
    expect(JSON.stringify(body)).not.toContain("RAW_TRACE_SECRET");
  });

  it("never serializes conversation_history for Live requests", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({ answer: "ok", classification: {} }),
    );

    await postLiveQuery("Live question?", "longmont-c2", 22, "live", {
      conversationHistory: [
        { role: "user", content: "prior" },
        { role: "assistant", content: "answer" },
      ],
    });

    const body = JSON.parse(String(fetchSpy.mock.calls[0][1]?.body)) as Record<string, unknown>;
    expect(body).not.toHaveProperty("conversation_history");
  });
});

describe("liveApi postWorldGraphSourceAnchorRead", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("posts camelCase body to source-anchor read endpoint", async () => {
    const request = {
      schema: "dmb_world_graph_source_anchor_read_request_v1" as const,
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      focus: { kind: "session" as const, sessionId: "session-22" },
      admissibility: "gm" as const,
      revisionPin: "rev:031c50b108af3c2523ee04accbf6ea4d",
      anchorId: "source-anchor:v1:05beab431e789dc9577e0b0b3472071c89682454944bc08a7d7ba8e76257d63e",
      maxChars: 4000,
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({
        schema: "dmb_world_graph_source_anchor_read_v1",
        outcome: "enough",
        anchorId: request.anchorId,
        truncated: false,
        diagnostics: [],
      }),
    );

    await postWorldGraphSourceAnchorRead(request);

    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe("/api/live/world-graph/retrieval/source-anchor/read");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual(request);
    expect(Object.keys(JSON.parse(String(init?.body)))).toEqual([
      "schema",
      "worldId",
      "campaignId",
      "focus",
      "admissibility",
      "revisionPin",
      "anchorId",
      "maxChars",
    ]);
    expect(JSON.parse(String(init?.body)).focus).toEqual({
      kind: "session",
      sessionId: "session-22",
    });
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

function worldbuildingRecord(overrides: Partial<WorkspaceDocumentRecord> = {}): WorkspaceDocumentRecord {
  const documentId = overrides.document_id ?? "11111111-1111-4111-8111-111111111111";
  return {
    schema_version: "dmb_workspace_document_record_v1",
    document_id: documentId,
    title: "World Lore",
    campaign_id: "eldyrwild",
    target_session: null,
    kind: "worldbuilding_source",
    target_relpath: `out/workspace/worldbuilding/${documentId}.md`,
    status: "active",
    content_status: "draft",
    revision: 1,
    created_at: "2026-07-22T00:00:00Z",
    updated_at: "2026-07-22T00:00:00Z",
    source_domain: "worldbuilding",
    document_class: "lore",
    authority_state: "draft",
    visibility_state: "internal",
    ...overrides,
  };
}

describe("liveApi workspace worldbuilding contracts", () => {
  it("posts worldbuilding create payloads and returns registry-owned targets", async () => {
    const record = worldbuildingRecord();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(mockJsonResponse(record));

    const request: CreateWorkspaceDocumentRequest = {
      title: "World Lore",
      campaign_id: "eldyrwild",
      kind: "worldbuilding_source",
      source_domain: "worldbuilding",
      document_class: "lore",
      authority_state: "draft",
      visibility_state: "internal",
    };
    const created = await createWorkspaceDocument(request);

    expect(created.target_relpath).toBe(`out/workspace/worldbuilding/${record.document_id}.md`);
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/api/live/workspace-documents"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(request),
      }),
    );
  });

  it("lists worldbuilding_source documents by kind", async () => {
    const record = worldbuildingRecord();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({
        schema_version: "dmb_workspace_document_registry_v1",
        records: [record],
      }),
    );

    const listed = await listWorkspaceDocuments({ kind: "worldbuilding_source" });
    expect(listed.records).toHaveLength(1);
    expect(listed.records[0]?.kind).toBe("worldbuilding_source");
    expect(String(fetchSpy.mock.calls[0]?.[0])).toContain("kind=worldbuilding_source");
  });

  it("surfaces prepare diagnostics when writer_ok is false", async () => {
    const prepare = {
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: "11111111-1111-4111-8111-111111111111",
      title: "World Lore",
      target_relpath: "out/workspace/worldbuilding/11111111-1111-4111-8111-111111111111.md",
      target_display_path: "out/workspace/worldbuilding/11111111-1111-4111-8111-111111111111.md",
      registry_revision: 1,
      file_exists: false,
      writer_ok: false,
      writer_phase: "prepare",
      writer_confirm_token: null,
      writer_diff: "",
      warnings: ["Commit blocked: unsupported Markdown would be lossy."],
      diagnostics: ["line 2: unsupported Markdown block would be lossy on commit"],
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(mockJsonResponse(prepare));

    const response = await prepareTiptapMarkdownWrite({
      document_id: prepare.document_id,
      markdown: "| a | b |\n",
      expected_revision: 1,
    });
    expect(response.writer_ok).toBe(false);
    expect(response.writer_confirm_token).toBeNull();
    expect(response.diagnostics.some((item) => item.includes("lossy"))).toBe(true);
  });

  it("fetches workspace document snapshots", async () => {
    const record = worldbuildingRecord({ revision: 2, content_status: "committed" });
    const snapshotPayload = {
      schema_version: "dmb_workspace_document_snapshot_v1",
      record,
      markdown: "# Committed\n",
      content_sha256: "sha-committed",
      file_fingerprint: "present",
      file_exists: true,
      loaded_revision: 2,
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(mockJsonResponse(snapshotPayload));

    const { getWorkspaceDocumentSnapshot } = await import("./liveApi");
    const snapshot = await getWorkspaceDocumentSnapshot(record.document_id);

    expect(snapshot.markdown).toBe("# Committed\n");
    expect(snapshot.loaded_revision).toBe(2);
    expect(String(fetchSpy.mock.calls[0]?.[0])).toContain(`/workspace-documents/${record.document_id}/snapshot`);
  });
});
