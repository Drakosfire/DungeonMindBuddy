import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { RecapArtifactRecord } from "../../api/types";
import { RecapGraphModule } from "./RecapGraphModule";
import { session23WorldGraphRecapFixture } from "./worldGraphRecapFixture";

const context = {
  campaignId: "longmont-c2",
  ingestSession: 22,
  liveSession: 22,
  target: { target_type: "session", target_id: "session-22" },
} as const;

function artifactRecord(session: number): RecapArtifactRecord {
  return {
    schema_version: "dmb_recap_artifact_record_v1",
    artifact_id: `longmont-c2/session-${session}`,
    campaign_id: "longmont-c2",
    session_id: `session-${session}`,
    source_artifact_id: null,
    source_recap_path: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session ${session} - Dogfood.md`,
    breadcrumb_seed_path: null,
    session_memory_records_path: null,
    run_bundle_uri: "",
    run_manifest_uri: "",
    source_span_index_uri: "",
    provenance_index_uri: null,
    graph_run_refs: [],
    default_graph_run_uri: null,
    default_projection_mode: "recap_graph",
    source_sha256: `sha256:session-${session}`,
    registered_at: "2026-06-28T00:00:00Z",
    updated_at: "2026-06-28T00:00:00Z",
    registry_source: "scan",
  };
}

function mockArtifacts() {
  vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({
    records: [artifactRecord(24)],
  });
}

function mockCompleteObject() {
  vi.spyOn(liveApi, "postWorldGraphCompleteObject").mockImplementation(async (request) => {
    const node = session23WorldGraphRecapFixture.nodeViews[request.nodeId] ?? null;
    const withOriginProse = node
      ? {
          ...node,
          adjacency: node.adjacency.map((edge, index) =>
            index === 0
              ? { ...edge, sourceExcerpt: "Held the Mireward gate during the incident." }
              : edge,
          ),
        }
      : null;
    return {
      schema: "dmb_world_graph_object_projection_v1",
      found: Boolean(withOriginProse),
      completeness: { status: "complete", truncatedFields: [] },
      snapshot: session23WorldGraphRecapFixture.snapshot,
      requestedNodeId: request.nodeId,
      resolvedNodeId: withOriginProse ? request.nodeId : null,
      node: withOriginProse,
      relatedNodes: [],
      semanticFingerprint: "fp-test",
    };
  });
}

function mockAuthoringWrites() {
  vi.spyOn(liveApi, "prepareGraphObjectAuthoringWrite");
  vi.spyOn(liveApi, "commitGraphObjectAuthoringWrite");
  vi.spyOn(liveApi, "resolveGraphReviewExistingObjectCandidates").mockResolvedValue({
    schema: "dmb_graph_review_existing_object_resolver_response_v1",
    campaign_id: "longmont-c2",
    session_id: "session-24",
    selected_node_id: "selection",
    selected_label: "selection",
    candidates: [],
    warnings: [],
    diagnostics: [],
    scopes_searched: [],
  });
}

async function findRecapPill(name: RegExp | string) {
  return waitFor(() => {
    const pill = screen
      .getAllByRole("button", { name })
      .find((button) => button.classList.contains("recap-node-token"));
    expect(pill).toBeTruthy();
    return pill as HTMLButtonElement;
  }, { timeout: 8000 });
}

describe("RecapGraphModule", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/plan?tool=recap&session=session-24");
    mockArtifacts();
    mockCompleteObject();
    mockAuthoringWrites();
  });

  it("requests World Graph recap projection for the URL session", async () => {
    const postRecap = vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue({
      ...session23WorldGraphRecapFixture,
      sessionId: "session-24",
    });

    render(<RecapGraphModule context={context} />);

    await waitFor(() => {
      expect(postRecap).toHaveBeenCalledWith({
        schema: "dmb_world_graph_projection_request_v1",
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        scopeMode: "campaign",
        focus: { kind: "session", sessionId: "session-24", campaignId: "longmont-c2" },
        admissibility: "gm",
      });
    });
    expect(await screen.findByLabelText("Published recap")).toBeInTheDocument();
  });

  it("defaults to the latest ingested recap artifact when no URL session is provided", async () => {
    window.history.replaceState({}, "", "/plan?tool=recap");
    vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({
      records: [artifactRecord(23), artifactRecord(24)],
    });
    const postRecap = vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue({
      ...session23WorldGraphRecapFixture,
      sessionId: "session-24",
    });

    render(<RecapGraphModule context={context} />);

    await waitFor(() => {
      expect(postRecap).toHaveBeenCalledWith(
        expect.objectContaining({ focus: expect.objectContaining({ sessionId: "session-24" }) }),
      );
    });
  });

  it("succeeds when recap memory exists but preview union is absent", async () => {
    vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue(session23WorldGraphRecapFixture);

    render(<RecapGraphModule context={context} />);

    expect(await screen.findByLabelText("Published recap")).toBeInTheDocument();
    expect(await findRecapPill(/Caelynn/i)).toBeInTheDocument();
  }, 15000);

  it("shows unavailable message for recap_markdown_unavailable without preview fallback", async () => {
    vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockRejectedValue(
      new liveApi.LiveApiError("recap missing", 404, { code: "recap_markdown_unavailable" }),
    );

    render(<RecapGraphModule context={context} />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Canonical normalized recap is unavailable for session-24 in longmont-c2.",
    );
  });

  it("uses campaign-specific session selection without manifest fields in graph request", async () => {
    window.history.replaceState({}, "", "/plan?tool=recap&session=session-1&campaign=longmont-c1");
    vi.spyOn(liveApi, "getRecapArtifacts").mockImplementation(async (campaignId) => {
      if (campaignId === "longmont-c1") {
        return { records: [{ ...artifactRecord(1), campaign_id: "longmont-c1", session_id: "session-1" }] };
      }
      return { records: [] };
    });
    const postRecap = vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue({
      ...session23WorldGraphRecapFixture,
      campaignId: "longmont-c1",
      sessionId: "session-1",
    });

    render(<RecapGraphModule context={context} />);

    await waitFor(() => {
      expect(postRecap).toHaveBeenCalledWith(
        expect.objectContaining({ campaignId: "longmont-c1", focus: expect.objectContaining({ sessionId: "session-1" }) }),
      );
    });
    const body = postRecap.mock.calls[0]?.[0];
    expect(body).not.toHaveProperty("revisionPin");
  });

  it("passes the selected recap record source identity into local authoring without synthesizing a span", async () => {
    vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue({
      ...session23WorldGraphRecapFixture,
      sessionId: "session-24",
    });

    render(<RecapGraphModule context={context} />);

    const host = await screen.findByTestId("published-recap-local-authoring");
    expect(host).toHaveAttribute("data-write-authority", "none");
    expect(host).toHaveAttribute("data-source-artifact-id", "null");
    expect(host).toHaveAttribute("data-source-artifact-path", artifactRecord(24).source_recap_path);
    expect(host).toHaveAttribute("data-source-artifact-sha256", "sha256:session-24");
    expect(host).toHaveAttribute("data-source-span-ref-id", "null");
    expect(liveApi.prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
    expect(liveApi.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
  });
});

describe("RecapGraphModule PR380B World Graph authority", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/plan?tool=recap&session=session-24");
    mockArtifacts();
    mockCompleteObject();
    mockAuthoringWrites();
  });

  it("does not call Union/latest-ingest selectors", async () => {
    const getUnion = vi.spyOn(liveApi, "getUnionSupergraphProjection");
    vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue(session23WorldGraphRecapFixture);

    render(<RecapGraphModule context={context} />);
    await screen.findByLabelText("Published recap");
    expect(getUnion).not.toHaveBeenCalled();
  });

  it("does not put Continue in Build on the ordinary recap Peek", async () => {
    vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue(session23WorldGraphRecapFixture);
    render(<RecapGraphModule context={context} />);
    await screen.findByLabelText("Published recap");
    fireEvent.click(await findRecapPill(/Caelynn/i));
    await waitFor(() => {
      expect(liveApi.postWorldGraphCompleteObject).toHaveBeenCalledWith(
        expect.objectContaining({ nodeId: "pc_caelynn", campaignId: "longmont-c2" }),
      );
    });
    expect(screen.queryByRole("link", { name: /Continue in Build/i })).not.toBeInTheDocument();
    expect(screen.queryByText("World object")).not.toBeInTheDocument();
    expect(screen.queryByText("Why it matters here")).not.toBeInTheDocument();
    const card = screen.getByTestId("graph-object-projection-card");
    expect(card).toHaveAttribute("data-testid", "graph-object-projection-card");
    expect(card.textContent).not.toContain("Held the Mireward gate during the incident.");
    expect(card.textContent).not.toMatch(/session_recap/i);
    expect(screen.getByTestId("published-recap-local-authoring")).toHaveAttribute(
      "data-existing-node-id",
      "pc_caelynn",
    );
    expect(screen.getByTestId("graph-object-projection-card")).toBeInTheDocument();
    expect(liveApi.prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
    expect(liveApi.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
  }, 15000);

  it("does not render preview-candidate or recap-lens metadata copy", async () => {
    vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue(session23WorldGraphRecapFixture);
    render(<RecapGraphModule context={context} />);
    expect(await screen.findByLabelText("Published recap")).toBeInTheDocument();
    expect(screen.queryByText(/Session focus lens/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Published World Graph · session recap/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/graph mentions projected/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/preview memory candidates/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/evidence highlights/i)).not.toBeInTheDocument();
  });

  it("preserves an explicit URL session even when it is absent from the artifact listing", async () => {
    window.history.replaceState({}, "", "/plan?tool=recap&session=session-99");
    vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({
      records: [artifactRecord(24)],
    });
    const postRecap = vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockRejectedValue(
      new liveApi.LiveApiError("recap missing", 404, { code: "recap_markdown_unavailable" }),
    );

    render(<RecapGraphModule context={context} />);

    await waitFor(() => {
      expect(postRecap).toHaveBeenCalledWith(
        expect.objectContaining({
          focus: expect.objectContaining({ sessionId: "session-99" }),
        }),
      );
    });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Canonical normalized recap is unavailable for session-99 in longmont-c2.",
    );
  });

  it("keeps Ingest recap session-27 identity instead of Plan-qualified lens syntax", async () => {
    window.history.replaceState({}, "", "/ingest?campaign=longmont-c2&session=session-27");
    vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({
      records: [artifactRecord(26), artifactRecord(27)],
    });
    const postRecap = vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue({
      ...session23WorldGraphRecapFixture,
      sessionId: "session-27",
    });

    render(<RecapGraphModule context={context} />);

    await waitFor(() => {
      expect(postRecap).toHaveBeenCalledWith(
        expect.objectContaining({
          campaignId: "longmont-c2",
          focus: expect.objectContaining({ sessionId: "session-27" }),
        }),
      );
    });
    expect(window.location.pathname).toBe("/ingest");
    expect(window.location.search).toContain("session=session-27");
    expect(window.location.search).not.toMatch(/longmont-c2:27/);
  });

  it("recovers Ingest recap identity if the URL was already rewritten to qualified lens syntax", async () => {
    window.history.replaceState({}, "", "/ingest?campaign=longmont-c2&session=longmont-c2:27");
    vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({
      records: [artifactRecord(27)],
    });
    const postRecap = vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue({
      ...session23WorldGraphRecapFixture,
      sessionId: "session-27",
    });

    render(<RecapGraphModule context={context} />);

    await waitFor(() => {
      expect(postRecap).toHaveBeenCalledWith(
        expect.objectContaining({
          focus: expect.objectContaining({ sessionId: "session-27" }),
        }),
      );
    });
    expect(window.location.search).toContain("session=session-27");
    expect(window.location.search).not.toMatch(/longmont-c2:27/);
  });

  it("chooses a valid C1 recap session when switching from C2 session-26", async () => {
    window.history.replaceState({}, "", "/ingest?campaign=longmont-c2&session=session-26");
    vi.spyOn(liveApi, "getRecapArtifacts").mockImplementation(async (campaignId) => {
      if (campaignId === "longmont-c1") {
        return {
          records: [
            { ...artifactRecord(15), campaign_id: "longmont-c1", session_id: "session-15" },
            { ...artifactRecord(16), campaign_id: "longmont-c1", session_id: "session-16" },
          ],
        };
      }
      return { records: [artifactRecord(26)] };
    });
    const postRecap = vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockImplementation(async (request) => ({
      ...session23WorldGraphRecapFixture,
      campaignId: request.campaignId,
      sessionId: request.focus.kind === "session" ? request.focus.sessionId : "session-26",
    }));

    render(<RecapGraphModule context={context} />);
    await waitFor(() => {
      expect(postRecap).toHaveBeenCalledWith(
        expect.objectContaining({
          campaignId: "longmont-c2",
          focus: expect.objectContaining({ sessionId: "session-26" }),
        }),
      );
    });

    fireEvent.change(screen.getByLabelText("Campaign"), { target: { value: "longmont-c1" } });

    await waitFor(() => {
      expect(postRecap).toHaveBeenCalledWith(
        expect.objectContaining({
          campaignId: "longmont-c1",
          focus: expect.objectContaining({ sessionId: "session-16" }),
        }),
      );
    });
    expect(
      postRecap.mock.calls.some(
        (call) =>
          call[0]?.campaignId === "longmont-c1"
          && call[0]?.focus?.kind === "session"
          && call[0]?.focus?.sessionId === "session-26",
      ),
    ).toBe(false);
    expect(window.location.search).toContain("campaign=longmont-c1");
    expect(window.location.search).toContain("session=session-16");
    expect(screen.getByLabelText("Focus session")).toHaveValue("session-16");
  });

  it("makes the previous recap non-authorable as soon as campaign changes", async () => {
    window.history.replaceState({}, "", "/ingest?campaign=longmont-c2&session=session-26");
    vi.spyOn(liveApi, "getRecapArtifacts").mockImplementation(async (campaignId) => {
      if (campaignId === "longmont-c1") {
        return {
          records: [
            { ...artifactRecord(16), campaign_id: "longmont-c1", session_id: "session-16" },
          ],
        };
      }
      return { records: [artifactRecord(26)] };
    });
    const postRecap = vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockImplementation(async (request) => ({
      ...session23WorldGraphRecapFixture,
      campaignId: request.campaignId,
      sessionId: request.focus.kind === "session" ? request.focus.sessionId : "session-26",
    }));

    render(<RecapGraphModule context={context} />);
    await waitFor(() => {
      expect(screen.getByTestId("published-recap-local-authoring")).toHaveAttribute(
        "data-campaign-id",
        "longmont-c2",
      );
    });
    expect(postRecap).toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Campaign"), { target: { value: "longmont-c1" } });

    expect(screen.queryByTestId("published-recap-local-authoring")).not.toBeInTheDocument();
    expect(screen.getByText(/Loading published World Graph recap/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("published-recap-local-authoring")).toHaveAttribute(
        "data-campaign-id",
        "longmont-c1",
      );
    });
    expect(screen.getByTestId("published-recap-local-authoring")).toHaveAttribute(
      "data-session-id",
      "session-16",
    );
  });

  it("rejects a slower previous projection after session switch", async () => {
    window.history.replaceState({}, "", "/ingest?campaign=longmont-c2&session=session-26");
    vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({
      records: [artifactRecord(26), artifactRecord(27)],
    });
    let resolveFirst: ((value: typeof session23WorldGraphRecapFixture) => void) | undefined;
    const firstProjection = new Promise<typeof session23WorldGraphRecapFixture>((resolve) => {
      resolveFirst = resolve;
    });
    let calls = 0;
    vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockImplementation(async (request) => {
      const sessionId = request.focus.kind === "session" ? request.focus.sessionId : "session-26";
      const payload = {
        ...session23WorldGraphRecapFixture,
        campaignId: request.campaignId,
        sessionId,
      };
      calls += 1;
      if (calls === 1) {
        return firstProjection;
      }
      return payload;
    });

    render(<RecapGraphModule context={context} />);
    await waitFor(() => {
      expect(liveApi.postWorldGraphRecapProjection).toHaveBeenCalledTimes(1);
    });

    fireEvent.change(screen.getByLabelText("Focus session"), { target: { value: "session-27" } });
    expect(screen.queryByTestId("published-recap-local-authoring")).not.toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("published-recap-local-authoring")).toHaveAttribute(
        "data-session-id",
        "session-27",
      );
    });

    resolveFirst?.({
      ...session23WorldGraphRecapFixture,
      campaignId: "longmont-c2",
      sessionId: "session-26",
    });

    await waitFor(() => {
      expect(screen.getByTestId("published-recap-local-authoring")).toHaveAttribute(
        "data-session-id",
        "session-27",
      );
    });
    expect(screen.queryByText(/Loading published World Graph recap/i)).not.toBeInTheDocument();
    expect(screen.getByTestId("published-recap-local-authoring")).not.toHaveAttribute(
      "data-session-id",
      "session-26",
    );
  });
});
