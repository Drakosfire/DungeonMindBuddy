import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import type { WorldOwnedPlanRecordV2 } from "../api/types";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { SelectedWorldProvider } from "../selectedWorld/SelectedWorldContext";
import { SurfaceContextProvider } from "../surfaceInteraction/contextHost";
import { PeekRegionProvider } from "../surfaceInteraction/peekHost";
import { PlanSurfacePage } from "./PlanSurfacePage";

vi.mock("./components/WorldPlanAgentConversation", () => ({
  WorldPlanAgentConversation: () => null,
}));

const worldId = "card-projection-world";
const secondWorldId = "card-projection-world-b";
const documentId = "saved-card-plan";
const secondDocumentId = "saved-card-plan-b";
const thirdDocumentId = "saved-card-plan-c";
const initialMarkdown = [
  "<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->",
  "## Arrival",
  "Scene overview.",
  "<!-- dmb-playable-element:v1 kind=beat id=beat:gate -->",
  "### The gate",
  "The guard is waiting.",
  "<!-- dmb-playable-element:v1 kind=choice id=choice:route -->",
  "### Choose a route",
  "Two paths are open.",
  "<!-- dmb-playable-element:v1 kind=option id=option:run -->",
  "#### Run through the gate",
  "Move quickly.",
].join("\n") + "\n";
const initialDigest = "a".repeat(64);
const committedDigest = "b".repeat(64);

const record: WorldOwnedPlanRecordV2 = {
  schema_version: "dmb_world_owned_plan_record_v2",
  scope_mode: "world",
  document_id: documentId,
  title: "Arrival Plan",
  campaign_id: null,
  world_id: worldId,
  target_session: null,
  kind: "plan",
  target_relpath: `out/workspace/plan/${documentId}.md`,
  status: "active",
  content_status: "committed",
  revision: 4,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderPlan(selectedWorldId = worldId) {
  return render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${selectedWorldId}`}>
      <AgentInteractionProvider>
        <SurfaceContextProvider>
          <PeekRegionProvider><PlanSurfacePage /></PeekRegionProvider>
        </SurfaceContextProvider>
      </AgentInteractionProvider>
    </SelectedWorldProvider>,
  );
}

function installApiMocks() {
  let savedMarkdown = initialMarkdown;
  let savedRevision = 4;
  let savedDigest = initialDigest;
  const listWorlds = vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [{
      schema_version: "dmb_world_container_record_v1",
      world_id: worldId,
      name: "Card Projection World",
      source_root_relpath: "corpus/card-projection-world",
      created_at: "2026-01-01T00:00:00Z",
    }],
  });
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockResolvedValue({
    schema_version: "dmb_managed_world_plan_context_v2",
    scope_mode: "world",
    world_id: worldId,
    campaign_id: null,
    session: null,
    authoritative: false,
    generated_at: "2026-01-01T00:00:00Z",
    derived_from: ["managed_world_container"],
    timeline: [],
  });
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockImplementation(async () => ({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [{ ...record, revision: savedRevision }],
  }));
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockImplementation(async () => ({
    schema_version: "dmb_workspace_document_snapshot_v2",
    record: { ...record, revision: savedRevision },
    markdown: savedMarkdown,
    content_sha256: savedDigest,
    file_fingerprint: "postgres",
    file_exists: true,
    loaded_revision: savedRevision,
  }));
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockImplementation(async (request) => ({
    schema_version: "dmb_tiptap_markdown_write_prepare_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: documentId,
    title: request.title,
    target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!,
    registry_revision: savedRevision + 1,
    file_exists: true,
    writer_ok: true,
    writer_confirm_token: "card-projection-prepared",
    warnings: [],
    diagnostics: [],
  }));
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockImplementation(async (request) => {
    savedMarkdown = request.markdown;
    savedRevision = request.expected_revision + 1;
    savedDigest = committedDigest;
    return {
      schema_version: "dmb_tiptap_markdown_write_commit_v2",
      scope_mode: "world",
      world_id: worldId,
      document_id: documentId,
      title: record.title,
      target_relpath: record.target_relpath!,
      target_display_path: record.target_relpath!,
      registry_revision: savedRevision,
      committed_revision: savedRevision,
      committed_record: { ...record, revision: savedRevision },
      normalized_content_sha256: committedDigest,
      writer_ok: true,
      writer_phase: "commit",
      diagnostics: [],
    };
  });
  return { listWorlds, prepare, commit, readServer: () => ({ savedMarkdown, savedRevision, savedDigest }) };
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  window.history.replaceState({}, "", "/");
});

it("keeps one editor draft through Cards, ordinary Save, and fresh reopen at the exact committed revision", async () => {
  const apis = installApiMocks();
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  const mounted = renderPlan();

  const page = await screen.findByTestId("world-owned-plan");
  const cardsButton = await within(page).findByRole("button", { name: "Cards" });
  await waitFor(() => expect(cardsButton).toBeEnabled());
  expect(apis.listWorlds).toHaveBeenCalled();
  expect(apis.prepare).not.toHaveBeenCalled();
  expect(apis.commit).not.toHaveBeenCalled();

  const editorElement = screen.getByTestId("world-owned-plan-markdown-editor").querySelector(".ProseMirror");
  expect(editorElement).not.toBeNull();
  fireEvent.click(cardsButton);
  expect(screen.getByTestId("world-plan-cards")).toBeInTheDocument();
  expect(within(screen.getByTestId("world-plan-cards")).getByText("Scene overview.")).toBeInTheDocument();
  expect(screen.getByTestId("world-owned-plan-markdown-editor").querySelector(".ProseMirror")).toBe(editorElement);
  // Return through the explicit Document view control while retaining the same editor node.
  fireEvent.click(within(page).getByRole("button", { name: "Document" }));
  const sceneBody = within(screen.getByTestId("world-owned-plan-markdown-editor")).getByText("Scene overview.");
  sceneBody.textContent = "Scene overview revised.";
  fireEvent.input(sceneBody);
  await waitFor(() => expect(within(screen.getByTestId("world-plan-document-view")).getByText("Scene overview revised.")).toBeInTheDocument());
  expect(apis.prepare).not.toHaveBeenCalled();
  expect(apis.commit).not.toHaveBeenCalled();

  fireEvent.click(within(page).getByRole("button", { name: "Cards" }));
  expect(screen.getByText("Draft / unsaved")).toBeInTheDocument();
  expect(within(screen.getByTestId("world-plan-cards")).getByText("Scene overview revised.")).toBeInTheDocument();
  expect(screen.getByTestId("world-owned-plan-markdown-editor").querySelector(".ProseMirror")).toBe(editorElement);
  expect(apis.prepare).not.toHaveBeenCalled();
  expect(apis.commit).not.toHaveBeenCalled();

  const editedProse = within(screen.getByTestId("world-plan-document-view")).getByText("Scene overview revised.");
  const selectionTextNode = editedProse.firstChild!;
  const selection = window.getSelection()!;
  const range = document.createRange();
  range.setStart(selectionTextNode, 5);
  range.collapse(true);
  selection.removeAllRanges();
  selection.addRange(range);
  fireEvent.click(within(page).getByRole("button", { name: "Cards" }));
  fireEvent.click(within(page).getByRole("button", { name: "Document" }));
  expect(selection.anchorNode).toBe(selectionTextNode);
  expect(selection.anchorOffset).toBe(5);
  expect(screen.getByTestId("world-owned-plan-markdown-editor").querySelector(".ProseMirror")).toBe(editorElement);
  const editHost = await screen.findByTestId("surface-edit-host");
  const saveButton = await within(editHost).findByRole("button", { name: "Save Plan" });
  await waitFor(() => expect(saveButton).toBeEnabled());
  fireEvent.click(saveButton);
  await screen.findByText("Saved to this World.");

  expect(apis.prepare).toHaveBeenCalledTimes(1);
  expect(apis.prepare.mock.calls[0]?.[0]).toMatchObject({
    world_id: worldId,
    document_id: documentId,
    expected_revision: 4,
  });
  expect(apis.commit).toHaveBeenCalledTimes(1);
  const committedMarkdown = apis.commit.mock.calls[0]?.[0].markdown ?? "";
  expect(committedMarkdown).toContain("Scene overview revised.");
  expect(committedMarkdown).toContain("<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->");
  expect(committedMarkdown).toContain("<!-- dmb-playable-element:v1 kind=option id=option:run -->");
  const markerIds = [...committedMarkdown.matchAll(/dmb-playable-element:v1 kind=[a-z]+ id=([a-z]+:[a-z0-9._-]+)/g)]
    .map((match) => match[1]);
  expect(markerIds).toEqual(["scene:arrival", "beat:gate", "choice:route", "option:run"]);
  expect(apis.readServer()).toMatchObject({ savedRevision: 6, savedDigest: committedDigest });

  mounted.unmount();
  localStorage.removeItem(`dmb:world-plan-local-draft:v2:${worldId}`);
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  renderPlan();
  const reopenedPage = await screen.findByTestId("world-owned-plan");
  const reopenedCardsButton = within(reopenedPage).getByRole("button", { name: "Cards" });
  await waitFor(() => expect(reopenedCardsButton).toBeEnabled());
  fireEvent.click(reopenedCardsButton);
  expect(screen.getByText("Saved Plan")).toBeInTheDocument();
  fireEvent.click(screen.getByText("Saved revision details"));
  expect(screen.getByText("6", { selector: "dd" })).toBeInTheDocument();
  expect(screen.getByText(committedDigest)).toBeInTheDocument();
  expect(within(screen.getByTestId("world-plan-cards")).getByText("Scene overview revised.")).toBeInTheDocument();
  expect(screen.getByTestId("world-owned-plan-markdown-editor").querySelector(".ProseMirror")).not.toBe(editorElement);
  expect(apis.commit).toHaveBeenCalledTimes(1);
});


it("invalidates the selected card projection when the saved document or World changes", async () => {
  const secondRecord: WorldOwnedPlanRecordV2 = {
    ...record,
    document_id: secondDocumentId,
    world_id: worldId,
    title: "Second Plan",
    revision: 12,
    target_relpath: `out/workspace/plan/${secondDocumentId}.md`,
  };
  const thirdRecord: WorldOwnedPlanRecordV2 = {
    ...record,
    document_id: thirdDocumentId,
    world_id: secondWorldId,
    title: "Other World Plan",
    revision: 21,
    target_relpath: `out/workspace/plan/${thirdDocumentId}.md`,
  };
  const records = [record, secondRecord, thirdRecord];
  const markdownByDocument = new Map([
    [documentId, initialMarkdown],
    [secondDocumentId, "<!-- dmb-playable-element:v1 kind=scene id=scene:second -->\n## Second scene\nSecond document prose.\n"],
    [thirdDocumentId, "<!-- dmb-playable-element:v1 kind=scene id=scene:other-world -->\n## Other World scene\nOther World prose.\n"],
  ]);
  const revisionByDocument = new Map([[documentId, 4], [secondDocumentId, 12], [thirdDocumentId, 21]]);
  const digestByDocument = new Map([[documentId, initialDigest], [secondDocumentId, "c".repeat(64)], [thirdDocumentId, "d".repeat(64)]]);

  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [worldId, secondWorldId].map((id) => ({
      schema_version: "dmb_world_container_record_v1" as const,
      world_id: id,
      name: id,
      source_root_relpath: `corpus/${id}`,
      created_at: "2026-01-01T00:00:00Z",
    })),
  });
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockImplementation(async (requestedWorldId) => ({
    schema_version: "dmb_managed_world_plan_context_v2",
    scope_mode: "world",
    world_id: requestedWorldId,
    campaign_id: null,
    session: null,
    authoritative: false,
    generated_at: "2026-01-01T00:00:00Z",
    derived_from: ["managed_world_container"],
    timeline: [],
  }));
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockImplementation(async (requestedWorldId) => ({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: requestedWorldId,
    records: records.filter((candidate) => candidate.world_id === requestedWorldId),
  }));
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockImplementation(async (requestedDocumentId) => {
    const selectedRecord = records.find((candidate) => candidate.document_id === requestedDocumentId)!;
    return {
      schema_version: "dmb_workspace_document_snapshot_v2",
      record: selectedRecord,
      markdown: markdownByDocument.get(requestedDocumentId)!,
      content_sha256: digestByDocument.get(requestedDocumentId)!,
      file_fingerprint: "postgres",
      file_exists: true,
      loaded_revision: revisionByDocument.get(requestedDocumentId)!,
    };
  });

  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  const mounted = renderPlan(worldId);
  const page = await screen.findByTestId("world-owned-plan");
  const cardsButton = within(page).getByRole("button", { name: "Cards" });
  await waitFor(() => expect(cardsButton).toBeEnabled());
  fireEvent.click(cardsButton);
  expect(within(screen.getByTestId("world-plan-cards")).getByText("Scene overview.")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: secondDocumentId } });
  await waitFor(() => expect(screen.getByLabelText("Plan document")).toHaveValue(secondDocumentId));
  await waitFor(() => expect(screen.queryByTestId("world-plan-cards")).not.toBeInTheDocument());
  expect(within(screen.getByTestId("world-plan-document-view")).getByText("Second document prose.")).toBeInTheDocument();
  fireEvent.click(within(page).getByRole("button", { name: "Cards" }));
  expect(within(screen.getByTestId("world-plan-cards")).getByText("Second document prose.")).toBeInTheDocument();
  expect(within(screen.getByTestId("world-plan-cards")).queryByText("Scene overview.")).not.toBeInTheDocument();

  mounted.unmount();
  window.history.replaceState({}, "", `/plan?world=${secondWorldId}&documentId=${thirdDocumentId}`);
  renderPlan(secondWorldId);
  const otherWorldPage = await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(within(otherWorldPage).getByRole("button", { name: "Cards" })).toBeEnabled());
  expect(screen.queryByTestId("world-plan-cards")).not.toBeInTheDocument();
  expect(within(screen.getByTestId("world-plan-document-view")).getByText("Other World prose.")).toBeInTheDocument();
  fireEvent.click(within(otherWorldPage).getByRole("button", { name: "Cards" }));
  const otherWorldCards = screen.getByTestId("world-plan-cards");
  expect(within(otherWorldCards).getByText("Other World prose.")).toBeInTheDocument();
  fireEvent.click(within(otherWorldCards).getByText("Saved revision details"));
  expect(within(otherWorldCards).getByText(secondWorldId)).toBeInTheDocument();
  expect(within(otherWorldCards).getByText(thirdDocumentId)).toBeInTheDocument();
  expect(within(otherWorldCards).getByText("21", { selector: "dd" })).toBeInTheDocument();
});
