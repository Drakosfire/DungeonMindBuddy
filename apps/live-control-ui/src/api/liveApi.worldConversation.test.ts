import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getWorldAgentConversationHistory,
  postWorldAgentNewConversation,
  setNativeGraphAccessToken,
} from "./liveApi";

function jsonResponse(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.restoreAllMocks();
  setNativeGraphAccessToken(null);
});

describe("World Agent conversation transport", () => {
  it("reads the exact bounded World history route and preserves the accepted response", async () => {
    const response = {
      schema: "dmb_agent_conversation_history_v1",
      world_id: "world/a",
      conversation_state: "active",
      conversation_id: "conversation-1",
      active_conversation_id: "conversation-1",
      pointer_revision: 12,
      turns: [],
      next_before_sequence: 50,
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(response));

    await expect(getWorldAgentConversationHistory("world/a", {
      limit: 50,
      beforeSequence: 51,
    })).resolves.toEqual(response);

    expect(String(fetchSpy.mock.calls[0]?.[0])).toBe(
      "/api/live/agent/worlds/world%2Fa/conversation?limit=50&before_sequence=51",
    );
    expect(fetchSpy.mock.calls[0]?.[1]?.method).toBeUndefined();
    expect(fetchSpy.mock.calls[0]?.[1]?.body).toBeUndefined();
  });

  it("posts the exact New Conversation CAS envelope", async () => {
    const request = {
      schema: "dmb_agent_new_conversation_v1" as const,
      command_id: "00000000-0000-4000-8000-000000000001",
      expected_pointer_revision: 12,
      expected_active_conversation_id: "conversation-1",
    };
    const response = {
      schema: "dmb_agent_new_conversation_response_v1",
      world_id: "world-1",
      conversation_id: "conversation-2",
      active_conversation_id: "conversation-2",
      pointer_revision: 13,
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(response));

    await expect(postWorldAgentNewConversation("world-1", request)).resolves.toEqual(response);

    expect(String(fetchSpy.mock.calls[0]?.[0])).toBe(
      "/api/live/agent/worlds/world-1/conversation/new",
    );
    expect(fetchSpy.mock.calls[0]?.[1]?.method).toBe("POST");
    expect(JSON.parse(String(fetchSpy.mock.calls[0]?.[1]?.body))).toEqual(request);
  });
});
