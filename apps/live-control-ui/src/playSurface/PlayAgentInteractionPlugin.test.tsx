import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createElement, useEffect, type ReactNode } from "react";

import { AgentInteractionProvider, useAgentInteraction } from "../agentInteraction/AgentInteractionProvider";
import { AskPluginSlotProvider } from "../agentInteraction/AskPluginSlot";
import { AgentInteractionChrome } from "../agentInteraction/AgentInteractionChrome";
import { buildSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import type { PlayRunRecord, LiveQueryResponse } from "../api/types";
import * as liveApi from "../api/liveApi";
import { PlayAgentInteractionPlugin } from "./PlayAgentInteractionPlugin";
import { buildPlaySurfaceAgentContext } from "./playSurfaceAgentContext";

const RUN_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const DOC_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

function playRun(overrides: Partial<PlayRunRecord> = {}): PlayRunRecord {
  return {
    schema_version: "dmb_play_run_record_v1",
    run_id: RUN_ID,
    campaign_id: "longmont-c2",
    playable_artifact_id: DOC_ID,
    playable_revision: 5,
    playable_content_sha256: "c".repeat(64),
    run_revision: 1,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    progress: {
      current_beat_id: "beat:hold-the-breach",
      current_scene_id: "scene:north-gate",
      resolved_beat_ids: [],
      selections: {},
      notes_by_element_id: {},
    },
    rebased_from_run_revision: null,
    ...overrides,
  };
}

function PlayLeasePublisher({ run, children }: { run: PlayRunRecord; children: ReactNode }) {
  const { publishSurfaceInteractionPublication } = useAgentInteraction();
  useEffect(() => {
    const agentContext = buildPlaySurfaceAgentContext(run);
    return publishSurfaceInteractionPublication({
      surfaceId: "play",
      label: "Play",
      identity: buildSurfaceInteractionIdentity({
        surfaceId: "play",
        instanceParts: ["play", run.run_id],
      }),
      canvas: null,
      agentContext: {
        ...agentContext,
        ambientSummary: `Play · run ${run.run_id}`,
      },
      tools: [],
      editCommands: [],
      projections: [],
      projectionBindings: [],
    });
  }, [publishSurfaceInteractionPublication, run]);
  return createElement("div", null, children);
}

function wrapper(run: PlayRunRecord) {
  return ({ children }: { children: ReactNode }) => createElement(
    AgentInteractionProvider,
    null,
    createElement(
      AskPluginSlotProvider,
      null,
      createElement(AgentInteractionChrome),
      createElement(PlayLeasePublisher, { run }, children),
    ),
  );
}

const mockQueryResponse: LiveQueryResponse = {
  answer: "The gate holds.",
  mode: "hermes_graph_agent",
  status: "ok",
  classification: {},
  events_written: [],
  jobs_queued: [],
  next_suggestions: [],
  diagnostics: {},
  provenance: {},
  agent_thread_id: "agent-thread-play-1",
};

describe("PlayAgentInteractionPlugin", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("registers Ask presence and renders when the pane is open", async () => {
    const user = userEvent.setup();
    render(<PlayAgentInteractionPlugin run={playRun()} />, { wrapper: wrapper(playRun()) });

    expect(screen.getByTestId("agent-interaction-chrome")).toHaveAttribute(
      "data-ask-available",
      "true",
    );

    await user.click(screen.getByTestId("agent-interaction-open"));
    expect(screen.getByTestId("play-agent-interaction-pane")).toBeInTheDocument();
  });

  it("submits via postAgentQuery without top-level campaign or session", async () => {
    const user = userEvent.setup();
    const askSpy = vi.spyOn(liveApi, "postAgentQuery").mockResolvedValue(mockQueryResponse);

    render(<PlayAgentInteractionPlugin run={playRun()} />, { wrapper: wrapper(playRun()) });
    await user.click(screen.getByTestId("agent-interaction-open"));

    await user.type(screen.getByTestId("play-agent-question-input"), "What is happening at the gate?");
    await user.click(screen.getByTestId("play-agent-submit"));

    await waitFor(() => expect(askSpy).toHaveBeenCalledTimes(1));
    const [text, options] = askSpy.mock.calls[0];
    expect(text).toBe("What is happening at the gate?");
    expect(options.surfaceContext?.surface_id).toBe("play");
    expect(options.worldGraphContext).toMatchObject({
      campaign_id: "longmont-c2",
      focus: { kind: "none", session_id: null },
    });
    expect(options).not.toHaveProperty("campaignId");
    expect(options).not.toHaveProperty("session");
  });

  it("disables submit when the campaign has no world mapping", async () => {
    const user = userEvent.setup();
    const askSpy = vi.spyOn(liveApi, "postAgentQuery").mockResolvedValue(mockQueryResponse);
    const unmappedRun = playRun({ campaign_id: "unknown-campaign" });

    render(<PlayAgentInteractionPlugin run={unmappedRun} />, { wrapper: wrapper(unmappedRun) });
    await user.click(screen.getByTestId("agent-interaction-open"));

    expect(screen.getByTestId("play-agent-no-world-mapping")).toBeInTheDocument();
    expect(screen.getByTestId("play-agent-submit")).toBeDisabled();

    await user.type(screen.getByTestId("play-agent-question-input"), "Should not send");
    await user.click(screen.getByTestId("play-agent-submit"));
    expect(askSpy).not.toHaveBeenCalled();
  });
});
