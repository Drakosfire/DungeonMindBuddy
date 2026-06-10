import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type {
  ListStatblockDraftsResponse,
  ReadStatblockDraftResponse,
  StatblockWorkbenchCommandResponse,
  StatblockWorkbenchSampleResponse,
  StatblockCorpusPromotionPreviewResponse,
  StatblockCorpusWriteCommitResponse,
  StatblockCorpusWritePrepareResponse,
  StatblockRetrievalActivationResponse,
  StatblockRetrievalVerifyResponse,
  StoreStatblockDraftResponse,
} from "../../api/types";
import { StatblockWorkbenchModule } from "./StatblockWorkbenchModule";

const sampleResponse: StatblockWorkbenchSampleResponse = {
  schema_version: "dmb_statblock_workbench_sample_v1",
  mode: "sample_mock",
  command_status: "ok",
  diagnostics: ["sample endpoint uses MockStatBlockGeneratorProvider only"],
  available_actions: [
    {
      action_id: "store_draft",
      label: "Store draft",
      enabled: true,
      disabled_reason: null,
    },
    {
      action_id: "add_to_combat",
      label: "Add to combat",
      enabled: false,
      disabled_reason: "Disabled in PR3: future lifecycle PR will make this action durable.",
    },
  ],
  artifact: {
    artifact_id: "statblock-draft-test",
    draft_id: "mock-generated-draft",
    title: "Geomantic Drake Juvenile",
    markdown: "## Geomantic Drake Juvenile\nClaw. Bite. Shifting stone.",
    structured_statblock: { name: "Geomantic Drake Juvenile" },
    combat_defaults: {
      name: "Geomantic Drake Juvenile",
      armor_class: 15,
      hit_points: 68,
      initiative_bonus: 2,
      passive_perception: 13,
      speed_summary: "30 ft., burrow 10 ft.",
      senses_summary: "darkvision 60 ft.",
      primary_actions: ["Bite", "Stone Skitter"],
      suggested_tactics: ["Open from cover"],
      legendary_actions: null,
    },
    warnings: [
      {
        code: "needs_dm_review",
        message: "Review damage numbers before table use.",
        severity: "warning",
        path: "statblock.actions[0]",
      },
    ],
    provenance: { generator: "mock-statblock-generator", mode: "generate_from_prompt" },
    review_status: "needs_dm_review",
    lifecycle_state: "live_draft",
    storage_status: "not_stored",
    corpus_status: "not_promoted",
    source_refs: [{ label: "Geomantic drake seed", path: "corpus/example.md" }],
    breadcrumbs: [
      { label: "campaign:c2", source: "sample_fixture", metadata: {} },
      { label: "surface:statblock_workbench", source: "live_control", metadata: {} },
    ],
    created_by: "agent",
    created_at: "2026-06-09T00:00:00Z",
    updated_at: "2026-06-09T00:00:00Z",
  },
};

function commandResponseFor(
  title: string,
  markdown: string,
): StatblockWorkbenchCommandResponse {
  return {
    schema_version: "dmb_statblock_workbench_command_v1",
    mode: "mock_command",
    command_status: "ok",
    diagnostics: ["command endpoint uses MockStatBlockGeneratorProvider only"],
    available_actions: sampleResponse.available_actions,
    artifact: {
      ...sampleResponse.artifact,
      artifact_id: `statblock-draft-${title}`,
      draft_id: `draft-${title}`,
      title,
      markdown,
      structured_statblock: { name: title },
      combat_defaults: {
        ...sampleResponse.artifact.combat_defaults,
        name: title,
        primary_actions: title.includes("Clockwork")
          ? ["Gearhook Slam", "Bog Vent"]
          : ["Bite"],
      },
      provenance: {
        generator: "mock-statblock-generator",
        mode: title.includes("Clockwork") ? "render_existing" : "generate_from_prompt",
      },
    },
  };
}

const emptyDraftsResponse: ListStatblockDraftsResponse = {
  schema_version: "dmb_statblock_draft_list_v1",
  drafts: [],
};

function storedResponseFor(artifact = sampleResponse.artifact): StoreStatblockDraftResponse {
  const storedArtifact = {
    ...artifact,
    lifecycle_state: "stored_artifact",
    storage_status: "stored_draft",
    corpus_status: "not_promoted",
    updated_at: "2026-06-09T01:00:00Z",
  };
  return {
    schema_version: "dmb_statblock_draft_store_v1",
    diagnostics: ["stored as non-corpus draft artifact"],
    record: {
      schema_version: "dmb_statblock_draft_record_v1",
      artifact_id: storedArtifact.artifact_id,
      title: storedArtifact.title,
      campaign_id: "c2",
      session: 22,
      stored_at: "2026-06-09T01:00:00Z",
      updated_at: "2026-06-09T01:00:00Z",
      storage_path: `statblock_drafts/${storedArtifact.artifact_id}.json`,
      artifact: storedArtifact,
    },
  };
}

function readResponseFor(artifact = sampleResponse.artifact): ReadStatblockDraftResponse {
  return {
    schema_version: "dmb_statblock_draft_read_v1",
    record: storedResponseFor(artifact).record,
  };
}

function previewResponseFor(artifact = storedResponseFor().record.artifact): StatblockCorpusPromotionPreviewResponse {
  const frontmatter = "---\nschema_version: dmb_corpus_statblock_v1\ntitle: Geomantic Drake Juvenile\ncorpus_status: promotion_previewed\n---";
  return {
    schema_version: "dmb_statblock_corpus_promotion_preview_v1",
    preview_id: "preview-token-123",
    artifact_id: artifact.artifact_id,
    draft_id: artifact.draft_id,
    title: artifact.title,
    campaign_id: "longmont-c2",
    session: 22,
    source_record_path: `statblock_drafts/${artifact.artifact_id}.json`,
    corpus_root_display: "corpus/eldyrwild-markdown",
    proposed_corpus_relpath: "Longmont Campaign/Campaign 2/Statblocks/generated/geomantic_drake_juvenile.md",
    proposed_corpus_display_path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Statblocks/generated/geomantic_drake_juvenile.md",
    frontmatter: { schema_version: "dmb_corpus_statblock_v1", corpus_status: "promotion_previewed" },
    frontmatter_text: frontmatter,
    markdown_body: `# ${artifact.title}\n\n${artifact.markdown}`,
    full_markdown: `${frontmatter}\n\n# ${artifact.title}\n\n${artifact.markdown}`,
    breadcrumbs: artifact.breadcrumbs,
    source_refs: artifact.source_refs,
    combat_defaults: artifact.combat_defaults,
    warnings: [{ code: "writer_allowlist_pending", message: "Writer allowlist pending.", severity: "info" }],
    validation: { ok: true, proposed_path_safe: true, writer_allowed_now: false, writer_reason: "not allowed yet" },
    preview_token: "abc123previewtoken",
    diagnostics: ["preview only; no corpus write occurred"],
    available_actions: [
      { action_id: "confirm_corpus_write", label: "Confirm corpus write", enabled: false, disabled_reason: "Future PR will require an explicit confirmation token." },
      { action_id: "ingest_to_semantic_layer", label: "Ingest to Semantic Knowledge Layer", enabled: false, disabled_reason: "Disabled until corpus write exists." },
      { action_id: "add_to_combat", label: "Add to combat", enabled: false, disabled_reason: "Disabled until corpus-backed Statblock View/combat integration exists." },
    ],
  };
}


function writePrepareResponseFor(artifact = storedResponseFor().record.artifact): StatblockCorpusWritePrepareResponse {
  const preview = previewResponseFor(artifact);
  return {
    schema_version: "dmb_statblock_corpus_write_prepare_v1",
    artifact_id: preview.artifact_id,
    draft_id: preview.draft_id,
    title: preview.title,
    preview_token: preview.preview_token,
    proposed_corpus_relpath: preview.proposed_corpus_relpath,
    proposed_corpus_display_path: preview.proposed_corpus_display_path,
    writer_ok: true,
    writer_phase: "preview",
    writer_confirm_token: "writer-confirm-token",
    writer_diff: "--- /dev/null\n+++ b/Longmont Campaign/Campaign 2/Statblocks/generated/geomantic_drake_juvenile.md\n+# Geomantic Drake Juvenile\n",
    new_size_bytes: 512,
    warnings: preview.warnings,
    diagnostics: ["corpus writer dry-run only; no corpus file was written"],
    available_actions: [{ action_id: "confirm_corpus_write", label: "Confirm corpus write", enabled: true, disabled_reason: null }],
  };
}

function writeCommitResponseFor(artifact = storedResponseFor().record.artifact): StatblockCorpusWriteCommitResponse {
  const preview = previewResponseFor(artifact);
  const promotedArtifact = {
    ...artifact,
    lifecycle_state: "corpus_promoted" as const,
    corpus_status: "promotion_confirmed" as const,
  };
  return {
    schema_version: "dmb_statblock_corpus_write_commit_v1",
    artifact_id: preview.artifact_id,
    draft_id: preview.draft_id,
    title: preview.title,
    preview_token: preview.preview_token,
    proposed_corpus_relpath: preview.proposed_corpus_relpath,
    proposed_corpus_display_path: preview.proposed_corpus_display_path,
    writer_ok: true,
    writer_phase: "committed",
    bytes_written: 512,
    new_corpus_fingerprint: "fingerprint-123",
    stored_record: {
      ...storedResponseFor(promotedArtifact).record,
      corpus_relpath: preview.proposed_corpus_relpath,
      corpus_display_path: preview.proposed_corpus_display_path,
      corpus_written_at: "2026-06-09T02:00:00Z",
      corpus_preview_token: preview.preview_token,
      artifact: promotedArtifact,
    },
    diagnostics: ["corpus markdown file written with corpus writer confirm_token"],
    available_actions: [],
  };
}

function retrievalActivationResponseFor(
  commit = writeCommitResponseFor(),
): StatblockRetrievalActivationResponse {
  const route = `corpus/eldyrwild-markdown/${commit.proposed_corpus_relpath}`;
  return {
    schema_version: "dmb_statblock_retrieval_activation_v1",
    artifact_id: commit.artifact_id,
    draft_id: commit.draft_id,
    title: commit.title,
    corpus_relpath: commit.proposed_corpus_relpath,
    corpus_display_path: commit.proposed_corpus_display_path,
    manifest_overlay_path: "statblock_retrieval/generated_statblocks_manifest.json",
    manifest_entry: {
      source_id: `generated_statblock-${commit.artifact_id}`,
      source_role: "world_evidence",
      authority: "canon_play",
      route,
      route_exists: true,
      allowed_uses: ["planning_context", "statblock_lookup", "mechanical_reference"],
      forbidden_uses: ["play_facts"],
      lexical_terms: ["Geomantic Drake Juvenile", "statblock", "armor class", "hit points", "primary actions"],
    },
    stored_record: {
      ...commit.stored_record,
      retrieval_status: "manifest_activated",
      retrieval_manifest_path: "statblock_retrieval/generated_statblocks_manifest.json",
      retrieval_activated_at: "2026-06-09T02:05:00Z",
    },
    diagnostics: ["generated-statblock manifest overlay updated"],
    available_actions: [],
  };
}

function retrievalVerifyResponseFor(
  activation = retrievalActivationResponseFor(),
): StatblockRetrievalVerifyResponse {
  const path = String(activation.manifest_entry.route);
  return {
    schema_version: "dmb_statblock_retrieval_verify_v1",
    artifact_id: activation.artifact_id,
    draft_id: activation.draft_id,
    title: activation.title,
    query: 'What are the statblock details for "Geomantic Drake Juvenile"?',
    status: "verified",
    corpus_relpath: activation.corpus_relpath,
    manifest_overlay_path: activation.manifest_overlay_path,
    admitted_evidence: [{
      path,
      source_role: "world_evidence",
      authority: "canon_play",
      line_start: 12,
      line_end: 18,
      text_excerpt: "Geomantic Drake Juvenile Armor Class 15 Hit Points 68 Bite Stone Skitter",
      evidence_score: 42.5,
    }],
    rejected_evidence: [],
    retrieval_trace: { top_manifest_entries: [{ route: path }] },
    stored_record: {
      ...activation.stored_record,
      retrieval_status: "retrieval_verified",
      retrieval_verified_at: "2026-06-09T02:06:00Z",
      retrieval_query: 'What are the statblock details for "Geomantic Drake Juvenile"?',
      retrieval_evidence_path: path,
      retrieval_evidence_score: 42.5,
    },
    diagnostics: ["retrieval verification status: verified"],
    available_actions: [],
  };
}

describe("StatblockWorkbenchModule", () => {
  beforeEach(() => {
    vi.spyOn(liveApi, "listStatblockWorkbenchDrafts").mockResolvedValue(emptyDraftsResponse);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the read-only sample artifact lifecycle surface", async () => {
    vi.spyOn(liveApi, "getStatblockWorkbenchSample").mockResolvedValue(sampleResponse);

    render(<StatblockWorkbenchModule />);

    expect(screen.getByText(/Loading read-only sample artifact/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Mock / non-corpus draft lane")).toBeInTheDocument();
    });

    expect(screen.getByText(/Lifecycle preview for/i)).toBeInTheDocument();
    expect(screen.getAllByText("Geomantic Drake Juvenile").length).toBeGreaterThan(0);
    expect(screen.getByText(/Claw\. Bite\. Shifting stone\./)).toBeInTheDocument();
    expect(screen.getByText("Armor Class")).toBeInTheDocument();
    expect(screen.getByText("Bite, Stone Skitter")).toBeInTheDocument();
    expect(screen.getAllByText("needs_dm_review").length).toBeGreaterThan(0);
    expect(screen.getByText("not_stored")).toBeInTheDocument();
    expect(screen.getByText("not_promoted")).toBeInTheDocument();
    expect(screen.getByText("campaign:c2")).toBeInTheDocument();
    expect(screen.getByText(/Review damage numbers/)).toBeInTheDocument();
    expect(screen.getByText("Provenance")).toBeInTheDocument();
    expect(screen.getByText("Source refs")).toBeInTheDocument();

    const storeButton = screen.getByRole("button", { name: "Store draft" });
    const combatButton = screen.getByRole("button", { name: "Add to combat" });
    expect(storeButton).toBeEnabled();
    expect(combatButton).toBeDisabled();
    expect(screen.getByText("No stored statblock drafts yet.")).toBeInTheDocument();
  });

  it("renders the sample artifact even when stored drafts fail to load", async () => {
    vi.spyOn(liveApi, "getStatblockWorkbenchSample").mockResolvedValue(sampleResponse);
    vi.mocked(liveApi.listStatblockWorkbenchDrafts).mockRejectedValue(new Error("draft list unavailable"));

    render(<StatblockWorkbenchModule />);

    await screen.findByText("Mock / non-corpus draft lane");
    expect(screen.getAllByText("Geomantic Drake Juvenile").length).toBeGreaterThan(0);
    expect(screen.getByText(/Unable to load stored drafts: draft list unavailable/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Store draft" })).toBeEnabled();
  });

  it("runs generate command and replaces the displayed artifact", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "getStatblockWorkbenchSample").mockResolvedValue(sampleResponse);
    let resolveCommand!: (response: StatblockWorkbenchCommandResponse) => void;
    const commandPromise = new Promise<StatblockWorkbenchCommandResponse>((resolve) => {
      resolveCommand = resolve;
    });
    const commandSpy = vi
      .spyOn(liveApi, "postStatblockWorkbenchCommand")
      .mockReturnValue(commandPromise);

    render(<StatblockWorkbenchModule />);

    await screen.findByText("Mock / non-corpus draft lane");
    await user.click(screen.getByRole("button", { name: "Generate mock draft" }));

    expect(commandSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        command_type: "statblock.draft.generate",
        requested_by: "human",
        as_artifact: true,
      }),
    );
    expect(screen.getByText(/Running mock generate command/)).toBeInTheDocument();
    resolveCommand(
      commandResponseFor(
        "Generated Obsidian Thornling",
        "## Generated Obsidian Thornling\nA fresh mock generated draft.",
      ),
    );
    await screen.findByText(/A fresh mock generated draft/);
    expect(screen.getAllByText("Generated Obsidian Thornling").length).toBeGreaterThan(
      0,
    );
    expect(screen.queryByText(/Claw\. Bite\. Shifting stone\./)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Store draft" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Add to combat" })).toBeDisabled();
  });

  it("runs render command and replaces the displayed artifact", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "getStatblockWorkbenchSample").mockResolvedValue(sampleResponse);
    vi.spyOn(liveApi, "postStatblockWorkbenchCommand").mockResolvedValue(
      commandResponseFor(
        "Rendered Clockwork Mire Sentinel",
        "## Rendered Clockwork Mire Sentinel\nGearhook Slam. Bog Vent.",
      ),
    );

    render(<StatblockWorkbenchModule />);

    await screen.findByText("Mock / non-corpus draft lane");
    await user.click(screen.getByRole("button", { name: "Render mock draft" }));

    await screen.findByText(/Gearhook Slam\. Bog Vent\./);
    expect(liveApi.postStatblockWorkbenchCommand).toHaveBeenCalledWith(
      expect.objectContaining({ command_type: "statblock.draft.render" }),
    );
    expect(
      screen.getAllByText("Rendered Clockwork Mire Sentinel").length,
    ).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Store draft" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Add to combat" })).toBeDisabled();
  });

  it("keeps the existing artifact visible when a command fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "getStatblockWorkbenchSample").mockResolvedValue(sampleResponse);
    vi.spyOn(liveApi, "postStatblockWorkbenchCommand").mockRejectedValue(
      new Error("mock command failed safely"),
    );

    render(<StatblockWorkbenchModule />);

    await screen.findByText("Mock / non-corpus draft lane");
    await user.click(screen.getByRole("button", { name: "Generate mock draft" }));

    await screen.findByText(/Unable to run Workbench command: mock command failed safely/);
    expect(screen.getAllByText("Geomantic Drake Juvenile").length).toBeGreaterThan(0);
    expect(screen.getByText(/Claw\. Bite\. Shifting stone\./)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Store draft" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Add to combat" })).toBeDisabled();
  });

  it("stores the current draft and refreshes the stored draft list", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "getStatblockWorkbenchSample").mockResolvedValue(sampleResponse);
    const stored = storedResponseFor();
    vi.spyOn(liveApi, "storeStatblockWorkbenchDraft").mockResolvedValue(stored);
    vi.mocked(liveApi.listStatblockWorkbenchDrafts)
      .mockResolvedValueOnce(emptyDraftsResponse)
      .mockResolvedValueOnce({
        schema_version: "dmb_statblock_draft_list_v1",
        drafts: [{
          artifact_id: stored.record.artifact_id,
          title: stored.record.title,
          draft_id: stored.record.artifact.draft_id,
          review_status: stored.record.artifact.review_status,
          lifecycle_state: stored.record.artifact.lifecycle_state,
          storage_status: stored.record.artifact.storage_status,
          corpus_status: stored.record.artifact.corpus_status,
          stored_at: stored.record.stored_at,
          updated_at: stored.record.updated_at,
          storage_path: stored.record.storage_path,
        }],
      });

    render(<StatblockWorkbenchModule />);

    await screen.findByText("Mock / non-corpus draft lane");
    await user.click(screen.getByRole("button", { name: "Store draft" }));

    expect(liveApi.storeStatblockWorkbenchDraft).toHaveBeenCalledWith({
      artifact: sampleResponse.artifact,
      source: "workbench",
    });
    await screen.findByText("stored_artifact");
    expect(screen.getAllByText("stored_draft").length).toBeGreaterThan(0);
    expect(screen.getAllByText("not_promoted").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/statblock_drafts\/statblock-draft-test\.json/).length).toBeGreaterThan(0);
  });

  it("keeps the current artifact visible when storing fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "getStatblockWorkbenchSample").mockResolvedValue(sampleResponse);
    vi.spyOn(liveApi, "storeStatblockWorkbenchDraft").mockRejectedValue(new Error("unsafe id"));

    render(<StatblockWorkbenchModule />);

    await screen.findByText("Mock / non-corpus draft lane");
    await user.click(screen.getByRole("button", { name: "Store draft" }));

    await screen.findByText(/Unable to store draft: unsafe id/);
    expect(screen.getAllByText("Geomantic Drake Juvenile").length).toBeGreaterThan(0);
    expect(screen.getByText(/Claw\. Bite\. Shifting stone\./)).toBeInTheDocument();
  });

  it("clears a stale storage error when generating a new draft", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "getStatblockWorkbenchSample").mockResolvedValue(sampleResponse);
    vi.spyOn(liveApi, "storeStatblockWorkbenchDraft").mockRejectedValue(new Error("unsafe id"));
    vi.spyOn(liveApi, "postStatblockWorkbenchCommand").mockResolvedValue(
      commandResponseFor(
        "Generated Obsidian Thornling",
        "## Generated Obsidian Thornling\nSplinter Thorn.",
      ),
    );

    render(<StatblockWorkbenchModule />);

    await screen.findByText("Mock / non-corpus draft lane");
    await user.click(screen.getByRole("button", { name: "Store draft" }));
    await screen.findByText(/Unable to store draft: unsafe id/);

    await user.click(screen.getByRole("button", { name: "Generate mock draft" }));

    await screen.findByText(/Splinter Thorn\./);
    expect(screen.queryByText(/Unable to store draft: unsafe id/)).not.toBeInTheDocument();
  });

  it("loads a stored draft into the Workbench display", async () => {
    const user = userEvent.setup();
    const loadedArtifact = {
      ...sampleResponse.artifact,
      artifact_id: "statblock-draft-loaded",
      title: "Loaded Mire Adept",
      markdown: "## Loaded Mire Adept\nLoaded from storage.",
      lifecycle_state: "stored_artifact",
      storage_status: "stored_draft",
    };
    vi.spyOn(liveApi, "getStatblockWorkbenchSample").mockResolvedValue(sampleResponse);
    vi.mocked(liveApi.listStatblockWorkbenchDrafts).mockResolvedValue({
      schema_version: "dmb_statblock_draft_list_v1",
      drafts: [{
        artifact_id: "statblock-draft-loaded",
        title: "Loaded Mire Adept",
        draft_id: "draft-loaded",
        review_status: "needs_dm_review",
        lifecycle_state: "stored_artifact",
        storage_status: "stored_draft",
        corpus_status: "not_promoted",
        stored_at: "2026-06-09T01:00:00Z",
        updated_at: "2026-06-09T01:00:00Z",
        storage_path: "statblock_drafts/statblock-draft-loaded.json",
      }],
    });
    vi.spyOn(liveApi, "getStatblockWorkbenchDraft").mockResolvedValue(readResponseFor(loadedArtifact));

    render(<StatblockWorkbenchModule />);

    await screen.findByText("Loaded Mire Adept");
    await user.click(screen.getByRole("button", { name: "Load" }));

    expect(liveApi.getStatblockWorkbenchDraft).toHaveBeenCalledWith("statblock-draft-loaded");
    await screen.findByText(/Loaded from storage/);
    expect(screen.getAllByText("Loaded Mire Adept").length).toBeGreaterThan(0);
  });


  it("disables corpus promotion preview until the draft is stored", async () => {
    vi.spyOn(liveApi, "getStatblockWorkbenchSample").mockResolvedValue(sampleResponse);

    render(<StatblockWorkbenchModule />);

    await screen.findByText("Mock / non-corpus draft lane");
    expect(screen.getByRole("button", { name: "Preview corpus promotion" })).toBeDisabled();
    expect(screen.getByText("Store this draft before previewing corpus promotion.")).toBeInTheDocument();
  });

  it("previews corpus promotion for a stored draft and keeps future write actions disabled", async () => {
    const user = userEvent.setup();
    const stored = storedResponseFor();
    vi.spyOn(liveApi, "getStatblockWorkbenchSample").mockResolvedValue(sampleResponse);
    vi.spyOn(liveApi, "storeStatblockWorkbenchDraft").mockResolvedValue(stored);
    vi.spyOn(liveApi, "previewStatblockCorpusPromotion").mockResolvedValue(previewResponseFor(stored.record.artifact));
    vi.mocked(liveApi.listStatblockWorkbenchDrafts)
      .mockResolvedValueOnce(emptyDraftsResponse)
      .mockResolvedValueOnce({
        schema_version: "dmb_statblock_draft_list_v1",
        drafts: [{
          artifact_id: stored.record.artifact_id,
          title: stored.record.title,
          draft_id: stored.record.artifact.draft_id,
          review_status: stored.record.artifact.review_status,
          lifecycle_state: stored.record.artifact.lifecycle_state,
          storage_status: stored.record.artifact.storage_status,
          corpus_status: stored.record.artifact.corpus_status,
          stored_at: stored.record.stored_at,
          updated_at: stored.record.updated_at,
          storage_path: stored.record.storage_path,
        }],
      });

    render(<StatblockWorkbenchModule />);

    await screen.findByText("Mock / non-corpus draft lane");
    await user.click(screen.getByRole("button", { name: "Store draft" }));
    await screen.findByText("stored_artifact");
    expect(screen.getByRole("button", { name: "Preview corpus promotion" })).toBeEnabled();

    await user.click(screen.getByRole("button", { name: "Preview corpus promotion" }));

    expect(liveApi.previewStatblockCorpusPromotion).toHaveBeenCalledWith("statblock-draft-test", {
      include_writer_allowlist_check: true,
    });
    expect((await screen.findAllByText("Corpus promotion preview")).length).toBeGreaterThan(1);
    expect(screen.getAllByText(/Longmont Campaign\/Campaign 2\/Statblocks\/generated\/geomantic_drake_juvenile\.md/).length).toBeGreaterThan(0);
    expect(screen.getByText("abc123previewtoken")).toBeInTheDocument();
    expect(screen.getAllByText(/schema_version: dmb_corpus_statblock_v1/).length).toBeGreaterThan(0);
    expect(screen.getByText(/writer_allowlist_pending/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm corpus write" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Ingest to Semantic Knowledge Layer" })).toBeDisabled();
    expect(screen.getAllByRole("button", { name: "Add to combat" }).every((button) => button.hasAttribute("disabled"))).toBe(true);
  });

  it("prepares and confirms corpus write with writer confirm token", async () => {
    const user = userEvent.setup();
    const storedArtifact = storedResponseFor().record.artifact;
    const preview = previewResponseFor(storedArtifact);
    const prepare = writePrepareResponseFor(storedArtifact);
    const commit = writeCommitResponseFor(storedArtifact);
    vi.spyOn(liveApi, "getStatblockWorkbenchSample").mockResolvedValue({
      ...sampleResponse,
      artifact: storedArtifact,
      command_status: "loaded_stored_draft",
    });
    vi.spyOn(liveApi, "previewStatblockCorpusPromotion").mockResolvedValue(preview);
    vi.spyOn(liveApi, "prepareStatblockCorpusWrite").mockResolvedValue(prepare);
    vi.spyOn(liveApi, "commitStatblockCorpusWrite").mockResolvedValue(commit);
    vi.mocked(liveApi.listStatblockWorkbenchDrafts)
      .mockResolvedValueOnce(emptyDraftsResponse)
      .mockResolvedValueOnce({
        schema_version: "dmb_statblock_draft_list_v1",
        drafts: [{
          artifact_id: commit.stored_record.artifact_id,
          title: commit.stored_record.title,
          draft_id: commit.stored_record.artifact.draft_id,
          review_status: commit.stored_record.artifact.review_status,
          lifecycle_state: commit.stored_record.artifact.lifecycle_state,
          storage_status: commit.stored_record.artifact.storage_status,
          corpus_status: commit.stored_record.artifact.corpus_status,
          stored_at: commit.stored_record.stored_at,
          updated_at: commit.stored_record.updated_at,
          storage_path: commit.stored_record.storage_path,
          corpus_relpath: commit.stored_record.corpus_relpath,
        }],
      });

    render(<StatblockWorkbenchModule />);

    await screen.findByText("Mock / non-corpus draft lane");
    await user.click(screen.getByRole("button", { name: "Preview corpus promotion" }));
    await screen.findByText("abc123previewtoken");
    await user.click(screen.getByRole("button", { name: "Prepare corpus write" }));

    expect(liveApi.prepareStatblockCorpusWrite).toHaveBeenCalledWith("statblock-draft-test", {
      preview_token: "abc123previewtoken",
    });
    await screen.findByText("Corpus write preparation");
    expect(screen.getByText("writer-confirm-token")).toBeInTheDocument();
    expect(screen.getAllByText(/Geomantic Drake Juvenile/).length).toBeGreaterThan(0);
    expect(liveApi.commitStatblockCorpusWrite).not.toHaveBeenCalled();

    await user.click(screen.getAllByRole("button", { name: "Confirm corpus write" }).find((button) => !button.hasAttribute("disabled"))!);
    await user.click(screen.getByRole("button", { name: "Write corpus file" }));

    expect(liveApi.commitStatblockCorpusWrite).toHaveBeenCalledWith("statblock-draft-test", {
      preview_token: "abc123previewtoken",
      writer_confirm_token: "writer-confirm-token",
    });
    await screen.findByText("Corpus write result");
    expect(screen.getByText("fingerprint-123")).toBeInTheDocument();
    expect(screen.getAllByText("promotion_confirmed").length).toBeGreaterThan(0);
    expect(screen.queryByText("writer-confirm-token")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Write corpus file" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Confirm corpus write" }).every((button) => button.hasAttribute("disabled"))).toBe(true);
    expect(screen.getAllByRole("button", { name: "Add to combat" }).every((button) => button.hasAttribute("disabled"))).toBe(true);
  });


  it("activates and verifies retrieval from the Workbench panel", async () => {
    const user = userEvent.setup();
    const commit = writeCommitResponseFor(storedResponseFor().record.artifact);
    const activation = retrievalActivationResponseFor(commit);
    const verification = retrievalVerifyResponseFor(activation);
    vi.spyOn(liveApi, "getStatblockWorkbenchSample").mockResolvedValue({
      ...sampleResponse,
      artifact: commit.stored_record.artifact,
      command_status: "corpus_written",
    });
    vi.spyOn(liveApi, "activateStatblockRetrieval").mockResolvedValue(activation);
    vi.spyOn(liveApi, "verifyStatblockRetrieval").mockResolvedValue(verification);

    render(<StatblockWorkbenchModule />);

    await screen.findByText("Mock / non-corpus draft lane");
    const activateButton = screen.getByRole("button", { name: "Activate retrieval" });
    const verifyButton = screen.getByRole("button", { name: "Verify retrieval" });
    expect(activateButton).toBeEnabled();
    expect(verifyButton).toBeDisabled();

    await user.click(activateButton);

    expect(liveApi.activateStatblockRetrieval).toHaveBeenCalledWith("statblock-draft-test");
    await screen.findByText("statblock_retrieval/generated_statblocks_manifest.json");
    expect(screen.getByText(`generated_statblock-${commit.artifact_id}`)).toBeInTheDocument();
    expect(screen.getByText(`corpus/eldyrwild-markdown/${commit.proposed_corpus_relpath}`)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Activate retrieval" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Verify retrieval" })).toBeEnabled();

    await user.click(screen.getByRole("button", { name: "Verify retrieval" }));

    expect(liveApi.verifyStatblockRetrieval).toHaveBeenCalledWith("statblock-draft-test", {});
    await screen.findByText("Retrieval verified");
    expect(screen.getByText("verified")).toBeInTheDocument();
    expect(screen.getAllByText(`corpus/eldyrwild-markdown/${commit.proposed_corpus_relpath}`).length).toBeGreaterThan(0);
    expect(screen.getByText("12–18")).toBeInTheDocument();
    expect(screen.getByText(/Armor Class 15 Hit Points 68/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Activate retrieval" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Verify retrieval" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Add to combat" })).toBeDisabled();
  });


  it("keeps the artifact visible when corpus preview fails", async () => {
    const user = userEvent.setup();
    const storedArtifact = storedResponseFor().record.artifact;
    vi.spyOn(liveApi, "getStatblockWorkbenchSample").mockResolvedValue({
      ...sampleResponse,
      artifact: storedArtifact,
      command_status: "loaded_stored_draft",
    });
    vi.spyOn(liveApi, "previewStatblockCorpusPromotion").mockRejectedValue(new Error("preview failed safely"));

    render(<StatblockWorkbenchModule />);

    await screen.findByText("Mock / non-corpus draft lane");
    await user.click(screen.getByRole("button", { name: "Preview corpus promotion" }));

    await screen.findByText(/Unable to preview corpus promotion: preview failed safely/);
    expect(screen.getAllByText("Geomantic Drake Juvenile").length).toBeGreaterThan(0);
    expect(screen.getByText(/Claw\. Bite\. Shifting stone\./)).toBeInTheDocument();
  });

  it("clears an existing corpus preview when loading a different stored draft", async () => {
    const user = userEvent.setup();
    const storedArtifact = storedResponseFor().record.artifact;
    const loadedArtifact = {
      ...storedArtifact,
      artifact_id: "statblock-draft-loaded",
      title: "Loaded Mire Adept",
      markdown: "## Loaded Mire Adept\nLoaded from storage.",
    };
    vi.spyOn(liveApi, "getStatblockWorkbenchSample").mockResolvedValue({
      ...sampleResponse,
      artifact: storedArtifact,
      command_status: "loaded_stored_draft",
    });
    vi.mocked(liveApi.listStatblockWorkbenchDrafts).mockResolvedValue({
      schema_version: "dmb_statblock_draft_list_v1",
      drafts: [{
        artifact_id: "statblock-draft-loaded",
        title: "Loaded Mire Adept",
        draft_id: "draft-loaded",
        review_status: "needs_dm_review",
        lifecycle_state: "stored_artifact",
        storage_status: "stored_draft",
        corpus_status: "not_promoted",
        stored_at: "2026-06-09T01:00:00Z",
        updated_at: "2026-06-09T01:00:00Z",
        storage_path: "statblock_drafts/statblock-draft-loaded.json",
      }],
    });
    vi.spyOn(liveApi, "previewStatblockCorpusPromotion").mockResolvedValue(previewResponseFor(storedArtifact));
    vi.spyOn(liveApi, "getStatblockWorkbenchDraft").mockResolvedValue(readResponseFor(loadedArtifact));

    render(<StatblockWorkbenchModule />);

    await screen.findByText("Mock / non-corpus draft lane");
    await user.click(screen.getByRole("button", { name: "Preview corpus promotion" }));
    await screen.findByText("abc123previewtoken");
    await user.click(screen.getByRole("button", { name: "Load" }));

    await screen.findByText(/Loaded from storage/);
    expect(screen.queryByText("abc123previewtoken")).not.toBeInTheDocument();
  });

});
