import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useEffect } from "react";
import { webcrypto } from "node:crypto";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import type {
  AgentInteractionThread,
  AgentInteractionTurn,
  WorldAgentConversationHistoryResponse,
  WorldAgentConversationHistoryResponseV1,
  WorldAgentConversationHistoryResponseV2,
  WorldAgentConversationHistoryTurnV1,
  WorldAgentConversationHistoryTurnV2,
  WorldAgentConversationHistoryPlanTurnV3,
  WorldPlanAgentPlanContextV1,
  WorldPlanAgentTurnResponseV2,
  WorldPlanAgentTurnRequestV1,
  WorldPlanGraphAnswerContextStatusV1,
  WorldPlanGraphExecutionProjectionV1,
} from "../api/types";

const harness = vi.hoisted(() => ({
  worldId: "",
  documentId: "",
  host: null as HTMLElement | null,
  agent: null as any,
}));

vi.mock("../selectedWorld/SelectedWorldContext", () => ({
  useSelectedWorld: () => ({ kind: "managed", worldId: harness.worldId }),
}));
vi.mock("../agentInteraction/AskPluginSlot", () => ({
  useAskPluginSlotOptional: () => ({ hostElement: harness.host }),
  useRegisterAskPluginPresence: () => undefined,
}));
vi.mock("../agentInteraction/useAgentInteraction", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../agentInteraction/useAgentInteraction")>();
  return {
    useAgentInteraction: () => harness.agent ?? actual.useAgentInteraction(),
  };
});
vi.mock("../agentInteraction/usePublishAgentSurfaceContext", () => ({
  usePublishAgentSurfaceContext: () => undefined,
}));

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { activeThreadStorageKey, persistAgentThread } from "../agentInteraction/agentInteractionStorage";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import { classifyPlanComposerIntent, WorldPlanAgentConversation } from "./components/WorldPlanAgentConversation";
import { AGENT_TURN_HISTORY_CAP, threadStorageKey } from "./components/agentInteractionHistory";

const worldId = "world-conversation-test";
const documentId = "saved-plan-test";
const surfaceInstanceId = "plan-surface-test";
const namespace = `world-plan-agent:world:${encodeURIComponent(worldId)}:document:${encodeURIComponent(documentId)}`;
const workRevisionId = "00000000-0000-4000-8000-000000000011";
const contentSha256 = "a".repeat(64);
const legacyThreadId = "legacy-thread-test";
const pendingAskClearedEventName = "dmb:world-plan-pending-ask-cleared:v1";
const pendingAskAcceptedEventName = "dmb:world-plan-ask-accepted:v1";
const pendingAskEventListeners: { eventName: string; listener: EventListener }[] = [];

function getGraphContextToggle() {
  return screen.queryByRole("button", { name: "Plan + World" })
    ?? screen.getByRole("button", { name: "Plan only" });
}

function ensureWorldGraphAskEnabled() {
  const toggle = getGraphContextToggle();
  if (toggle.getAttribute("aria-pressed") !== "true") fireEvent.click(toggle);
}

function ensureWorldGraphAskDisabled() {
  const toggle = getGraphContextToggle();
  if (toggle.getAttribute("aria-pressed") === "true") fireEvent.click(toggle);
}

function openLatestTurnDetails() {
  const transcript = screen.getByRole("region", { name: "World conversation transcript" });
  const latestTurn = transcript.querySelector("article[data-sequence]");
  const details = latestTurn?.querySelector(".world-plan-agent-conversation__turn-details");
  if (details && !details.hasAttribute("open")) fireEvent.click(details.querySelector("summary")!);
}

function makeTurn(
  sequence: number,
  turnId: string,
  userText: string,
  assistantText: string | null,
  surfaceId = "plan",
): WorldAgentConversationHistoryTurnV1 {
  return {
    turn_id: turnId,
    sequence,
    lifecycle_status: "completed",
    user_text: userText,
    assistant_text: assistantText,
    provenance: {
      world_id: worldId,
      surface_resolution: "resolved",
      surface_id: surfaceId,
      surface_instance_id: `${surfaceId}-instance`,
      primary_work: {
        resolution: "resolved",
        kind: surfaceId === "plan" ? "plan" : "build",
        object_id: surfaceId === "plan" ? documentId : "other-work",
        revision: null,
        content_sha256: null,
        object_revision: surfaceId === "plan" ? 7 : null,
        work_revision_id: surfaceId === "plan" ? workRevisionId : null,
        revision_n: surfaceId === "plan" ? 1 : null,
      },
      supporting_work: [],
      selected_object: {
        resolution: "absent",
        kind: null,
        object_id: null,
        revision: null,
        content_sha256: null,
        object_revision: null,
        work_revision_id: null,
        revision_n: null,
      },
    },
  };
}

function history(
  conversationId: string | null,
  pointerRevision: number,
  turns: WorldAgentConversationHistoryTurnV1[],
  nextBeforeSequence: number | null = null,
): WorldAgentConversationHistoryResponseV1 {
  const absent = conversationId === null;
  return {
    schema: "dmb_agent_conversation_history_v1",
    world_id: worldId,
    conversation_state: absent ? "absent" : "active",
    conversation_id: conversationId,
    active_conversation_id: conversationId,
    pointer_revision: pointerRevision,
    turns,
    next_before_sequence: nextBeforeSequence,
  };
}

// Captured from SERVER #926 head 746711815577e022e6961b32c135395e00d36531 with the
// APP-STATE execution types from 7a8365a5a354e9d3c85e788112f7904f1e517cce:
// get_world_conversation_history -> project_plan_turn_context -> FastAPI response serializer.
// Mount this v2 wire body unchanged to join the accepted producer projection to the consumer.
const serverHistoryProjection: WorldAgentConversationHistoryResponseV2 = {
  "active_conversation_id": "00000000-0000-4000-8000-000000000031",
  "conversation_id": "00000000-0000-4000-8000-000000000031",
  "conversation_state": "active",
  "next_before_sequence": null,
  "pointer_revision": 4,
  "schema": "dmb_agent_conversation_history_v2",
  "turns": [
    {
      "assistant_text": "The western gate is watched.",
      "lifecycle_status": "completed",
      "plan_context": {
        "completion": {
          "answer_basis": "committed_plan_plus_world_graph",
          "answer_context_status": "graph_grounded",
          "answer_segments": [
            {
              "claim_id": "claim-internal-test",
              "evidence_ref_ids": [
                "evidence-internal-test"
              ],
              "graph_revision": "graph-revision-test",
              "kind": "graph_claim",
              "target_id": "assertion-internal-test",
              "target_kind": "assertion",
              "text": "The western gate is watched."
            }
          ],
          "citation_map": {
            "context_receipt_sha256": "c67e5dc4a2ef13672c0373330c8fd560dea3be9906045fcdce3ee30a7e791fec",
            "entries": [
              {
                "claim_id": "claim-internal-test",
                "evidence_ref_ids": [
                  "evidence-internal-test"
                ],
                "graph_revision": "graph-revision-test",
                "source_opened": false,
                "target_id": "assertion-internal-test",
                "target_kind": "assertion"
              }
            ],
            "schema": "dmb_graph_citation_map_v1"
          },
          "context_receipt_sha256": "c67e5dc4a2ef13672c0373330c8fd560dea3be9906045fcdce3ee30a7e791fec",
          "schema": "dmb_plan_world_graph_completion_v1"
        },
        "delivery_replay": false,
        "execution": {
          "authorization_state": "response_received",
          "automatic_redispatch": false,
          "claimability": "completed",
          "schema": "dmb_agent_plan_world_graph_execution_projection_v1"
        },
        "receipt": {
          "assembled_input": {
            "assembled_input_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
            "assembler_version": "assembler-v1",
            "budget_policy_version": "budget-v1",
            "context_window_limit": 100,
            "dispatched_assertion_ids": [
              "assertion-internal-test"
            ],
            "dispatched_evidence_ref_ids": [
              "evidence-internal-test"
            ],
            "dispatched_packet_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
            "dispatched_relationship_ids": [],
            "included_history": [],
            "output_token_reserve": 10,
            "packet_disposition": "included",
            "packet_disposition_reason": null,
            "provider_envelope_input_tokens": 10,
            "provider_model_name": "synthetic-model",
            "provider_model_version": "1",
            "source_token_accounting": [],
            "tokenizer_name": "utf8_json_bytes_plus_64_per_node_v1",
            "tokenizer_version": "v1"
          },
          "context_receipt_sha256": "c67e5dc4a2ef13672c0373330c8fd560dea3be9906045fcdce3ee30a7e791fec",
          "evidence_mode": "metadata_only",
          "graph_authority": {
            "admissibility_version": "gm-v1",
            "binding_version": 2,
            "campaign_id": null,
            "graph_revision": "graph-revision-test",
            "managed_world_id": "world-conversation-test",
            "native_world_id": "native-world-internal-test",
            "scope_mode": "world"
          },
          "graph_packet": {
            "candidate_assertion_ids": [
              "assertion-internal-test"
            ],
            "candidate_evidence_ref_ids": [
              "evidence-internal-test"
            ],
            "candidate_relationship_ids": [],
            "coverage_status": "complete",
            "evidence_sufficiency_policy_version": "sufficiency-v1",
            "evidence_sufficiency_status": "sufficient",
            "omission_reasons": [],
            "packet_serializer_version": "canonical-json-utf8-v1",
            "result_limit": 32,
            "retrieval_packet_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
            "retrieval_status": "complete",
            "schema": "dmb_plan_world_graph_packet_v1",
            "selection_policy_version": "selection-v1",
            "truncated": false
          },
          "plan_basis": {
            "content_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "document_id": "saved-plan-test",
            "object_revision": 7,
            "revision_n": 1,
            "work_revision_id": "00000000-0000-4000-8000-000000000011",
            "world_id": "world-conversation-test"
          },
          "plan_context_policy": {
            "policy": "auto_plan_world",
            "schema": "dmb_plan_context_policy_v1"
          },
          "playable_target": null,
          "receipt_serializer_version": "canonical-json-utf8-v1",
          "schema": "dmb_agent_plan_world_graph_context_receipt_v1",
          "source_opened": false
        },
        "schema": "dmb_agent_plan_world_graph_context_response_v1"
      },
      "provenance": {
        "primary_work": {
          "content_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "kind": "plan",
          "object_id": "saved-plan-test",
          "object_revision": 7,
          "resolution": "resolved",
          "revision": "7",
          "revision_n": 1,
          "work_revision_id": "00000000-0000-4000-8000-000000000011"
        },
        "selected_object": {
          "content_sha256": null,
          "kind": null,
          "object_id": null,
          "object_revision": null,
          "resolution": "absent",
          "revision": null,
          "revision_n": null,
          "work_revision_id": null
        },
        "supporting_work": [],
        "surface_id": "plan",
        "surface_instance_id": "plan-main",
        "surface_resolution": "resolved",
        "world_id": "world-conversation-test"
      },
      "sequence": 1,
      "turn_id": "00000000-0000-4000-8000-000000000021",
      "user_text": "Who watches the western gate?"
    }
  ],
  "world_id": "world-conversation-test"
};

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value !== null && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(record[key])}`).join(",")}}`;
  }
  const encoded = JSON.stringify(value);
  if (encoded === undefined) throw new Error("Unsupported value in canonical JSON payload.");
  return encoded;
}

// Exact SERVER #930 response body emitted by get_world_conversation_history ->
// project_plan_turn_context -> FastAPI serialization; SHA-256: 9bcefddc6b4bd9854f8842f280a6c30d01e0eec5d493836f12685021c5682b46.
// The separate serverHistoryProjection above retains the non-null execution witness.
const serverCardTargetHistoryProjection: WorldAgentConversationHistoryResponseV2 = {
    "active_conversation_id": "00000000-0000-4000-8000-000000000031",
    "conversation_id": "00000000-0000-4000-8000-000000000031",
    "conversation_state": "active",
    "next_before_sequence": null,
    "pointer_revision": 4,
    "schema": "dmb_agent_conversation_history_v2",
    "turns": [
      {
        "assistant_text": "The western gate is watched.",
        "lifecycle_status": "completed",
        "plan_context": {
          "completion": {
            "answer_basis": "committed_plan_plus_world_graph",
            "answer_context_status": "graph_grounded",
            "answer_segments": [
              {
                "claim_id": "claim-internal-test",
                "evidence_ref_ids": [
                  "evidence-internal-test"
                ],
                "graph_revision": "graph-revision-3",
                "kind": "graph_claim",
                "target_id": "assertion-internal-test",
                "target_kind": "assertion",
                "text": "The western gate is watched."
              }
            ],
            "citation_map": {
              "context_receipt_sha256": "63043187af13a39b0f4792b664e905e1e52354b4a9a00c208e65474de40512b2",
              "entries": [
                {
                  "claim_id": "claim-internal-test",
                  "evidence_ref_ids": [
                    "evidence-internal-test"
                  ],
                  "graph_revision": "graph-revision-3",
                  "source_opened": false,
                  "target_id": "assertion-internal-test",
                  "target_kind": "assertion"
                }
              ],
              "schema": "dmb_graph_citation_map_v1"
            },
            "context_receipt_sha256": "63043187af13a39b0f4792b664e905e1e52354b4a9a00c208e65474de40512b2",
            "schema": "dmb_plan_world_graph_completion_v1"
          },
          "delivery_replay": false,
          "execution": null,
          "receipt": {
            "assembled_input": {
              "assembled_input_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
              "assembler_version": "assembler-v1",
              "budget_policy_version": "budget-v1",
              "context_window_limit": 100,
              "dispatched_assertion_ids": [
                "assertion-internal-test"
              ],
              "dispatched_evidence_ref_ids": [
                "evidence-internal-test"
              ],
              "dispatched_packet_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
              "dispatched_relationship_ids": [],
              "included_history": [],
              "output_token_reserve": 10,
              "packet_disposition": "included",
              "packet_disposition_reason": null,
              "provider_envelope_input_tokens": 10,
              "provider_model_name": "synthetic-model",
              "provider_model_version": "1",
              "source_token_accounting": [],
              "tokenizer_name": "utf8_json_bytes_plus_64_per_node_v1",
              "tokenizer_version": "v1"
            },
            "context_receipt_sha256": "63043187af13a39b0f4792b664e905e1e52354b4a9a00c208e65474de40512b2",
            "evidence_mode": "metadata_only",
            "graph_authority": {
              "admissibility_version": "gm-v1",
              "binding_version": 2,
              "campaign_id": null,
              "graph_revision": "graph-revision-3",
              "managed_world_id": "world-conversation-test",
              "native_world_id": "native:one",
              "scope_mode": "world"
            },
            "graph_packet": {
              "candidate_assertion_ids": [
                "assertion-internal-test"
              ],
              "candidate_evidence_ref_ids": [
                "evidence-internal-test"
              ],
              "candidate_relationship_ids": [],
              "coverage_status": "complete",
              "evidence_sufficiency_policy_version": "sufficiency-v1",
              "evidence_sufficiency_status": "sufficient",
              "omission_reasons": [],
              "packet_serializer_version": "canonical-json-utf8-v1",
              "result_limit": 32,
              "retrieval_packet_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
              "retrieval_status": "complete",
              "schema": "dmb_plan_world_graph_packet_v1",
              "selection_policy_version": "selection-v1",
              "truncated": false
            },
            "plan_basis": {
              "content_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
              "document_id": "saved-plan-test",
              "object_revision": 7,
              "revision_n": 1,
              "work_revision_id": "00000000-0000-4000-8000-000000000011",
              "world_id": "world-conversation-test"
            },
            "plan_context_policy": {
              "policy": "auto_plan_world",
              "schema": "dmb_plan_context_policy_v1"
            },
            "playable_target": {
              "id": "scene:opening",
              "kind": "scene",
              "marker_grammar_version": "v1",
              "schema": "dmb_plan_playable_target_receipt_v1"
            },
            "receipt_serializer_version": "canonical-json-utf8-v1",
            "schema": "dmb_agent_plan_world_graph_context_receipt_v1",
            "source_opened": false
          },
          "schema": "dmb_agent_plan_world_graph_context_response_v1"
        },
        "provenance": {
          "primary_work": {
            "content_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "kind": "plan",
            "object_id": "saved-plan-test",
            "object_revision": 7,
            "resolution": "resolved",
            "revision": "7",
            "revision_n": 1,
            "work_revision_id": "00000000-0000-4000-8000-000000000011"
          },
          "selected_object": {
            "content_sha256": null,
            "kind": null,
            "object_id": null,
            "object_revision": null,
            "resolution": "absent",
            "revision": null,
            "revision_n": null,
            "work_revision_id": null
          },
          "supporting_work": [
            {
              "content_sha256": null,
              "kind": "dmb_plan_playable_target_v1",
              "object_id": "scene:opening",
              "object_revision": null,
              "resolution": "resolved",
              "revision": "v1",
              "revision_n": null,
              "work_revision_id": null
            }
          ],
          "surface_id": "plan",
          "surface_instance_id": "plan-main",
          "surface_resolution": "resolved",
          "world_id": "world-conversation-test"
        },
        "sequence": 2,
        "turn_id": "00000000-0000-4000-8000-000000000032",
        "user_text": "Who watches the western gate?"
      },
      {
        "assistant_text": "A legacy answer",
        "lifecycle_status": "completed",
        "provenance": {
          "primary_work": {
            "content_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "kind": "plan",
            "object_id": "saved-plan-test",
            "object_revision": 7,
            "resolution": "resolved",
            "revision": "7",
            "revision_n": 1,
            "work_revision_id": "00000000-0000-4000-8000-000000000011"
          },
          "selected_object": {
            "content_sha256": null,
            "kind": null,
            "object_id": null,
            "object_revision": null,
            "resolution": "absent",
            "revision": null,
            "revision_n": null,
            "work_revision_id": null
          },
          "supporting_work": [
            {
              "content_sha256": null,
              "kind": "dmb_plan_playable_target_v1",
              "object_id": "scene:opening",
              "object_revision": null,
              "resolution": "resolved",
              "revision": "v1",
              "revision_n": null,
              "work_revision_id": null
            }
          ],
          "surface_id": "plan",
          "surface_instance_id": "plan-main",
          "surface_resolution": "resolved",
          "world_id": "world-conversation-test"
        },
        "sequence": 1,
        "turn_id": "00000000-0000-4000-8000-000000000033",
        "user_text": "A legacy question"
      }
    ],
    "world_id": "world-conversation-test"
  };

async function planGraphContext(
  status: WorldPlanGraphAnswerContextStatusV1,
  options: {
    request?: WorldPlanAgentTurnRequestV1;
    execution?: WorldPlanGraphExecutionProjectionV1 | null;
    completion?: boolean;
  } = {},
): Promise<WorldPlanAgentPlanContextV1> {
  const graphClaimed = status === "graph_grounded" || status === "graph_grounded_partial";
  const sufficient = status !== "plan_only_insufficient_evidence";
  const graphRevision = "graph-revision-test";
  const assertionIds = sufficient ? ["assertion-internal-test"] : [];
  const evidenceIds = sufficient ? ["evidence-internal-test"] : [];
  const receiptPayload = {
    schema: "dmb_agent_plan_world_graph_context_receipt_v1" as const,
    receipt_serializer_version: "canonical-json-utf8-v1" as const,
    context_receipt_sha256: "0".repeat(64),
    plan_context_policy: { schema: "dmb_plan_context_policy_v1" as const, policy: "auto_plan_world" as const },
    plan_basis: {
      world_id: worldId,
      document_id: documentId,
      object_revision: options.request?.primary_work.expected_revision ?? 7,
      work_revision_id: workRevisionId,
      revision_n: options.request?.primary_work.expected_revision_n ?? 1,
      content_sha256: options.request?.primary_work.expected_content_sha256 ?? contentSha256,
    },
    playable_target: options.request?.playable_target ? {
      schema: "dmb_plan_playable_target_receipt_v1" as const,
      kind: options.request.playable_target.kind,
      id: options.request.playable_target.id,
      marker_grammar_version: "v1" as const,
    } : null,
    graph_authority: {
      managed_world_id: worldId,
      native_world_id: "native-world-internal-test",
      binding_version: 3,
      scope_mode: "world" as const,
      campaign_id: null,
      admissibility_version: "admissibility-test-v1",
      graph_revision: graphRevision,
    },
    graph_packet: {
      schema: "dmb_plan_world_graph_packet_v1" as const,
      packet_serializer_version: "canonical-json-utf8-v1" as const,
      selection_policy_version: "selection-test-v1",
      evidence_sufficiency_policy_version: "evidence-test-v1",
      retrieval_packet_sha256: "b".repeat(64),
      candidate_assertion_ids: assertionIds,
      candidate_relationship_ids: [],
      candidate_evidence_ref_ids: evidenceIds,
      retrieval_status: sufficient ? "complete" as const : "empty" as const,
      evidence_sufficiency_status: sufficient ? "sufficient" as const : "insufficient" as const,
      result_limit: 10,
      coverage_status: status === "graph_grounded_partial" ? "incomplete" as const : "complete" as const,
      truncated: status === "graph_grounded_partial",
      omission_reasons: sufficient ? [] : ["no_claim_ready_evidence"],
    },
    assembled_input: {
      assembler_version: "assembler-test-v1",
      budget_policy_version: "budget-test-v1",
      provider_model_name: "test-model",
      provider_model_version: "test-model-v1",
      tokenizer_name: "test-tokenizer",
      tokenizer_version: "test-tokenizer-v1",
      provider_envelope_input_tokens: 400,
      output_token_reserve: 100,
      context_window_limit: 1000,
      packet_disposition: sufficient ? "included" as const : "omitted_insufficient" as const,
      packet_disposition_reason: sufficient ? null : "insufficient_evidence" as const,
      dispatched_packet_sha256: sufficient ? "c".repeat(64) : null,
      dispatched_assertion_ids: assertionIds,
      dispatched_relationship_ids: [],
      dispatched_evidence_ref_ids: evidenceIds,
      source_token_accounting: [{ source_kind: "plan" as const, source_id: documentId, input_tokens: 200 }],
      included_history: [],
      assembled_input_sha256: "d".repeat(64),
    },
    evidence_mode: "metadata_only" as const,
    source_opened: false as const,
  };
  const { context_receipt_sha256: _ignored, ...receiptForHash } = receiptPayload;
  const receiptDigest = await sha256Hex(canonicalJson(receiptForHash));
  const receipt = { ...receiptPayload, context_receipt_sha256: receiptDigest };
  const segments = graphClaimed
    ? [{
      kind: "graph_claim" as const,
      claim_id: "claim-internal-test",
      text: "The western gate is watched.",
      target_kind: "assertion" as const,
      target_id: assertionIds[0]!,
      graph_revision: graphRevision,
      evidence_ref_ids: evidenceIds,
    }]
    : [{ kind: "connective" as const, text: "The saved Plan has one opening scene." }];
  const citationEntries = graphClaimed ? [{
    claim_id: "claim-internal-test",
    target_kind: "assertion" as const,
    target_id: assertionIds[0]!,
    graph_revision: graphRevision,
    evidence_ref_ids: evidenceIds,
    source_opened: false as const,
  }] : [];
  return {
    schema: "dmb_agent_plan_world_graph_context_response_v1",
    receipt,
    completion: options.completion === false ? null : {
      schema: "dmb_plan_world_graph_completion_v1",
      context_receipt_sha256: receiptDigest,
      answer_basis: graphClaimed ? "committed_plan_plus_world_graph" : "committed_plan",
      answer_context_status: status,
      answer_segments: segments,
      citation_map: graphClaimed ? {
        schema: "dmb_graph_citation_map_v1",
        context_receipt_sha256: receiptDigest,
        entries: citationEntries,
      } : null,
    },
    execution: options.execution === undefined ? {
      schema: "dmb_agent_plan_world_graph_execution_projection_v1",
      claimability: "completed",
      authorization_state: "response_received",
      automatic_redispatch: false,
    } : options.execution,
    delivery_replay: false,
  };
}

async function resealPlanGraphContext(context: WorldPlanAgentPlanContextV1): Promise<WorldPlanAgentPlanContextV1> {
  const { context_receipt_sha256: _ignored, ...receiptPayload } = context.receipt;
  const digest = await sha256Hex(canonicalJson(receiptPayload));
  context.receipt.context_receipt_sha256 = digest;
  if (context.completion) {
    context.completion.context_receipt_sha256 = digest;
    if (context.completion.citation_map) context.completion.citation_map.context_receipt_sha256 = digest;
  }
  return context;
}

async function historyV2(
  conversationId: string | null,
  pointerRevision: number,
  turns: WorldAgentConversationHistoryTurnV2[],
  nextBeforeSequence: number | null = null,
): Promise<WorldAgentConversationHistoryResponseV2> {
  const absent = conversationId === null;
  return {
    schema: "dmb_agent_conversation_history_v2",
    world_id: worldId,
    conversation_state: absent ? "absent" : "active",
    conversation_id: conversationId,
    active_conversation_id: conversationId,
    pointer_revision: pointerRevision,
    turns,
    next_before_sequence: nextBeforeSequence,
  };
}

async function expectedHistoryCorrelationKey(frozenWorldId: string, clientTurnId: string): Promise<string> {
  const namespace = Uint8Array.from("6ba7b8119dad11d180b400c04fd430c8".match(/.{2}/g)!, (pair) => Number.parseInt(pair, 16));
  const name = new TextEncoder().encode(`dmb-agent-turn:${frozenWorldId}:${clientTurnId}`);
  const input = new Uint8Array(namespace.length + name.length);
  input.set(namespace);
  input.set(name, namespace.length);
  const hash = new Uint8Array(await crypto.subtle.digest("SHA-1", input));
  hash[6] = (hash[6]! & 0x0f) | 0x50;
  hash[8] = (hash[8]! & 0x3f) | 0x80;
  const hex = Array.from(hash.slice(0, 16), (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

async function historyV3(
  conversationId: string | null,
  pointerRevision: number,
  turns: WorldAgentConversationHistoryPlanTurnV3[],
): Promise<WorldAgentConversationHistoryResponse> {
  const absent = conversationId === null;
  return {
    schema: "dmb_agent_conversation_history_v3",
    world_id: worldId,
    conversation_state: absent ? "absent" : "active",
    conversation_id: conversationId,
    active_conversation_id: conversationId,
    pointer_revision: pointerRevision,
    turns,
    next_before_sequence: null,
  };
}

function withPersistedCorrelation(
  turn: WorldAgentConversationHistoryTurnV2,
  idempotencyKey: string,
  durableTurnId = "00000000-0000-4000-8000-000000000090",
): WorldAgentConversationHistoryPlanTurnV3 {
  if (!turn.plan_context) throw new Error("The synthetic v3 history row must include the producer's Plan receipt/completion projection.");
  return { ...turn, turn_id: durableTurnId, idempotency_key: idempotencyKey };
}

async function policyResponse(
  request: WorldPlanAgentTurnRequestV1,
  conversationId: string,
  answer: string,
  status: WorldPlanGraphAnswerContextStatusV1 = "graph_grounded",
): Promise<WorldPlanAgentTurnResponseV2> {
  const legacy = agentResponse(request, conversationId, answer);
  const graphGrounded = status === "graph_grounded" || status === "graph_grounded_partial";
  return {
    ...legacy,
    schema: "dmb_agent_turn_response_v2",
    answer: { ...legacy.answer, graph_grounded: graphGrounded },
    plan_context: await planGraphContext(status, { request }),
  };
}

function agentResponse(request: WorldPlanAgentTurnRequestV1, conversationId: string, answer: string) {
  return {
    schema: "dmb_agent_turn_response_v1",
    client_thread_id: request.client_thread_id,
    turn_id: request.turn_id,
    surface: {
      surface_id: "plan",
      instance_id: request.surface.instance_id,
      status: "resolved",
    },
    owner_scope: {
      status: "resolved",
      kind: "world",
      owner_id: worldId,
      name: "Test World",
    },
    primary_work: {
      status: "resolved",
      kind: "plan",
      object_id: documentId,
      revision_used: request.primary_work.expected_revision,
      expected_revision: request.primary_work.expected_revision,
      content_basis: {
        world_id: worldId,
        document_id: documentId,
        object_revision: request.primary_work.expected_revision,
        work_revision_id: workRevisionId,
        revision_n: request.primary_work.expected_revision_n,
        content_sha256: request.primary_work.expected_content_sha256,
        committed_status: "committed",
        has_divergent_working_copy: false,
      },
    },
    client_work_state_reported: request.client_work_state,
    graph: {
      status: "not_requested",
      world_id: null,
      campaign_id: null,
      scope_mode: null,
      revision_id: null,
      focus: null,
      selection_node_id: null,
      selection_found: null,
      head_revision_id: null,
      is_head: null,
    },
    conversation: {
      client_thread_id: request.client_thread_id,
      turn_id: request.turn_id,
      pointer_status: "accepted",
      pointer_id: null,
      conversation_id: conversationId,
    },
    answer: {
      status: "ok",
      text: answer,
      code: null,
      message: null,
      graph_grounded: false,
      trace: {},
    },
  };
}

function durableReplayResponse(request: WorldPlanAgentTurnRequestV1, conversationId: string, answer: string) {
  const accepted = agentResponse(request, conversationId, answer);
  return {
    ...accepted,
    primary_work: { ...accepted.primary_work, content_basis: null },
    conversation: { ...accepted.conversation, pointer_status: "reused" },
    answer: {
      ...accepted.answer,
      trace: {
        schema: "dmb_agent_turn_trace_v1",
        trace_id: "00000000-0000-4000-8000-000000000099",
        agent_thread_id: request.client_thread_id,
        turn_id: request.turn_id,
        runtime: "durable_receipt",
        backend: "application_state",
        mode: "replay",
        status: "ok",
        usage: {},
        model_calls: [],
        spans: [],
        steps: [],
        context_summary: {},
        artifact_refs: [],
        warnings: ["durable_turn_replay_no_provider_dispatch"],
        conversation_context: "durable_replay",
      },
    },
  };
}

function fullLegacyThread(): AgentInteractionThread {
  const thread = legacyThread();
  const first = thread.turns[0]!;
  return {
    ...thread,
    turns: Array.from({ length: AGENT_TURN_HISTORY_CAP }, (_, index) => ({
      ...first,
      turnId: `legacy-turn-${index + 1}`,
      askedAt: `2026-01-01T00:${String(index).padStart(2, "0")}:00.000Z`,
      completedAt: `2026-01-01T00:${String(index).padStart(2, "0")}:30.000Z`,
      question: `Legacy question ${index + 1}`,
      answer: `Legacy answer ${index + 1}`,
    })),
  };
}

function ActualProviderScopeInitializer() {
  const agent = useAgentInteraction();
  useEffect(() => {
    agent.rehydrateScope({
      campaignId: namespace,
      sessionNumber: null,
      surfaceId: "plan",
      documentId,
    });
    agent.setPaneOpen(true);
  }, []);
  return null;
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function readBlob(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error("Could not read exported history."));
    reader.readAsText(blob);
  });
}

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

interface ConversationTestProps {
  documentId?: string;
  revision?: number;
  editBridge?: any;
  playableTarget?: { kind: "scene" | "beat" | "choice" | "option"; id: string } | null;
  playableEditTarget?: { kind: "scene" | "beat" | "choice" | "option"; id: string; generation: number } | null;
  playableEditTargetGeneration?: number;
  playableEditTargetDirty?: boolean;
  playableEditTargetStale?: boolean;
  playableTargetBasis?: { revision: number; contentSha256: string } | null;
  playableTargetStale?: boolean;
  selectionGeneration?: number;
  draftGeneration?: number;
  savedDirty?: boolean;
}

function conversationElement(props: ConversationTestProps = {}) {
  const revision = props.revision ?? 7;
  const playableTarget = props.playableTarget ?? null;
  const hasExplicitTargetBasis = Object.prototype.hasOwnProperty.call(props, "playableTargetBasis");
  const playableTargetBasis = hasExplicitTargetBasis
    ? props.playableTargetBasis ?? null
    : playableTarget ? { revision: 7, contentSha256 } : null;
  return (
    <WorldPlanAgentConversation
      worldId={worldId}
      worldName="Test World"
      documentId={props.documentId ?? documentId}
      surfaceInstanceId={surfaceInstanceId}
      revision={revision}
      editBridge={props.editBridge ?? null}
      draftGeneration={props.draftGeneration ?? 0}
      selectionGeneration={props.selectionGeneration ?? 0}
      savedDirty={props.savedDirty ?? false}
      pageReady
      saveInFlight={false}
      playableTarget={playableTarget}
      playableEditTarget={props.playableEditTarget}
      playableEditTargetGeneration={props.playableEditTargetGeneration}
      playableEditTargetDirty={props.playableEditTargetDirty ?? false}
      playableEditTargetStale={props.playableEditTargetStale ?? false}
      playableTargetBasis={playableTargetBasis}
      playableTargetStale={props.playableTargetStale ?? false}
    />
  );
}

function historyTurnForAsk(
  request: WorldPlanAgentTurnRequestV1,
  answer: string,
): WorldAgentConversationHistoryTurnV1 {
  const turn = makeTurn(1, request.turn_id, request.message, answer);
  turn.provenance.primary_work = {
    ...turn.provenance.primary_work,
    revision: String(request.primary_work.expected_revision),
    content_sha256: request.primary_work.expected_content_sha256,
    object_revision: request.primary_work.expected_revision,
    work_revision_id: workRevisionId,
    revision_n: request.primary_work.expected_revision_n,
  };
  turn.provenance.supporting_work = request.playable_target ? [{
    resolution: "resolved",
    kind: "dmb_plan_playable_target_v1",
    object_id: request.playable_target.id,
    revision: "v1",
    content_sha256: null,
    object_revision: null,
    work_revision_id: null,
    revision_n: null,
  }] : [];
  return turn;
}

function policyHistoryTurn(
  sequence: number,
  turnId: string,
  question: string,
  answer: string | null,
  context: WorldPlanAgentPlanContextV1,
  lifecycle: WorldAgentConversationHistoryTurnV2["lifecycle_status"] = "completed",
  request?: WorldPlanAgentTurnRequestV1,
): WorldAgentConversationHistoryTurnV2 {
  const turn = makeTurn(sequence, turnId, question, answer);
  const basis = context.receipt.plan_basis;
  if (request) {
    turn.provenance.surface_id = request.surface.surface_id;
    turn.provenance.surface_instance_id = request.surface.instance_id;
  }
  turn.provenance.primary_work = {
    resolution: "resolved",
    kind: "plan",
    object_id: basis.document_id,
    revision: String(basis.object_revision),
    content_sha256: basis.content_sha256,
    object_revision: basis.object_revision,
    work_revision_id: basis.work_revision_id,
    revision_n: basis.revision_n,
  };
  const target = context.receipt.playable_target;
  turn.provenance.supporting_work = target ? [{
    resolution: "resolved",
    kind: "dmb_plan_playable_target_v1",
    object_id: target.id,
    revision: target.marker_grammar_version,
    content_sha256: null,
    object_revision: null,
    work_revision_id: null,
    revision_n: null,
  }] : [];
  return { ...turn, lifecycle_status: lifecycle, plan_context: context };
}

async function failedV3HistoryTurn(
  correlatedRequest: WorldPlanAgentTurnRequestV1,
  options: {
    rowRequest?: WorldPlanAgentTurnRequestV1;
    durableTurnId?: string;
    execution?: WorldPlanGraphExecutionProjectionV1;
  } = {},
): Promise<WorldAgentConversationHistoryPlanTurnV3> {
  const rowRequest = options.rowRequest ?? correlatedRequest;
  const context = await planGraphContext("plan_only_graph_unused", {
    request: rowRequest,
    completion: false,
    execution: options.execution ?? {
      schema: "dmb_agent_plan_world_graph_execution_projection_v1",
      claimability: "blocked_unknown_or_sent",
      authorization_state: "response_received",
      automatic_redispatch: false,
    },
  });
  const turn = policyHistoryTurn(
    1,
    correlatedRequest.turn_id,
    correlatedRequest.message,
    null,
    context,
    "failed",
    rowRequest,
  );
  return withPersistedCorrelation(
    turn,
    await expectedHistoryCorrelationKey(worldId, correlatedRequest.turn_id),
    options.durableTurnId ?? "ce97be5a-18b5-4fb5-a820-8161716fe516",
  );
}

function legacyThread(): AgentInteractionThread {
  const turn: AgentInteractionTurn = {
    turnId: "legacy-turn-1",
    askedAt: "2026-01-01T00:00:00.000Z",
    completedAt: "2026-01-01T00:01:00.000Z",
    question: "Legacy question",
    answer: "Legacy only fact",
    backend: "hermes",
    status: "ok",
  };
  return {
    threadId: legacyThreadId,
    title: "Old local thread",
    createdAt: "2026-01-01T00:00:00.000Z",
    updatedAt: "2026-01-01T00:01:00.000Z",
    campaignId: namespace,
    session: null,
    documentId,
    surfaceId: "plan",
    activeBackend: "hermes",
    hermesSession: { sessionId: "legacy-provider-session", pointerId: "legacy-pointer" },
    turns: [turn],
  };
}

function setHarness() {
  harness.worldId = worldId;
  harness.documentId = documentId;
  harness.host = document.createElement("div");
  document.body.appendChild(harness.host);
  const thread = legacyThread();
  harness.agent = {
    activeThread: thread,
    scope: {
      campaignId: namespace,
      surfaceId: "plan",
      sessionNumber: null,
      documentId,
    },
    paneState: { isOpen: true },
    updateThread: vi.fn((nextThread: AgentInteractionThread) => { harness.agent.activeThread = nextThread; }),
    createThread: vi.fn(),
  };
  return thread;
}

function mountComponent(
  revision = 7,
  editBridge: any = null,
  playableTarget: { kind: "scene" | "beat" | "choice" | "option"; id: string } | null = null,
  playableTargetStale = false,
) {
  return render(conversationElement({
    revision,
    editBridge,
    playableTarget,
    playableTargetStale,
  }));
}

function committedRevision(selectedDocumentId = documentId) {
  return {
    schema_version: "dmb_workspace_committed_revision_v2",
    scope_mode: "world",
    world_id: worldId,
    campaign_id: null,
    document_id: selectedDocumentId,
    kind: "plan",
    status: "active",
    object_revision: 7,
    work_revision_id: workRevisionId,
    revision_n: 1,
    content_sha256: contentSha256,
    markdown: "# Saved Plan",
    has_divergent_working_copy: false,
  };
}

async function capturedCardBodyEdit(targetBodyMarkdown: string) {
  const target = { kind: "scene" as const, id: "scene:arrival" };
  const targetBodySha256 = await sha256Hex(targetBodyMarkdown);
  const bodyTarget = {
    target,
    markerGrammarVersion: "v2" as const,
    bodyScope: "heading_body" as const,
    rangeSemanticsVersion: "plan-playable-ranges-v1" as const,
    bodySerializationVersion: "plan-playable-body-markdown-v1" as const,
    targetBodyMarkdown,
    targetBodySha256,
    from: 10,
    to: 30,
    rootStartIndex: 0,
    rootEndIndex: 2,
    protectedReferences: [],
  };
  return {
    editor: { isDestroyed: false },
    request: {
      document_id: documentId,
      world_id: worldId,
      session: 1,
      base_revision: 7,
      base_content_sha256: contentSha256,
      draft_markdown: "# Draft Plan\n\nScene content.",
      draft_sha256: "d".repeat(64),
      target_kind: "replace_playable_body" as const,
      selected_text: "",
      playable_target: target,
      body_serialization_version: bodyTarget.bodySerializationVersion,
      target_body_markdown: targetBodyMarkdown,
      target_body_sha256: targetBodySha256,
    },
    from: bodyTarget.from,
    to: bodyTarget.to,
    editorJson: "{}",
    selectionJson: "[]",
    draftGeneration: 0,
    selectionGeneration: 0,
    playableTargetGeneration: 2,
    playableBodyTarget: bodyTarget,
  };
}

function mockCardBodyProposal(replacementMarkdown = "The revised scene opens.") {
  return vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockImplementation(async (request) => ({
    schema_version: "dmb_world_plan_document_edit_proposal_v2",
    action_id: "00000000-0000-4000-8000-000000000099",
    idempotency_key: request.idempotency_key,
    document_id: request.document_id,
    world_id: request.world_id,
    base_revision: request.base_revision,
    base_content_sha256: request.base_content_sha256,
    draft_sha256: request.draft_sha256,
    target_kind: request.target_kind,
    selected_text_sha256: null,
    playable_target: request.playable_target,
    marker_grammar_version: "v2",
    body_scope: "heading_body",
    range_semantics_version: "plan-playable-ranges-v1",
    body_serialization_version: "plan-playable-body-markdown-v1",
    target_body_sha256: request.target_body_sha256,
    replacement_markdown: replacementMarkdown,
    summary: "Revise the arrival scene.",
    assumptions: [],
    model: "test-model",
    model_observed: false,
    model_latency_ms: 0,
    wall_latency_ms: 0,
    usage: null,
  }) as any);
}

function setupApi(initialHistory: WorldAgentConversationHistoryResponse) {
  let currentHistory = initialHistory;
  let currentBasis = committedRevision();
  let olderPage: WorldAgentConversationHistoryResponse | null = null;
  let olderHandler: (() => Promise<WorldAgentConversationHistoryResponse>) | null = null;
  const historyCalls: Array<{ limit?: number; beforeSequence?: number }> = [];
  const getHistory = vi.spyOn(liveApi, "getWorldAgentConversationHistory").mockImplementation(async (_world, options = {}) => {
    historyCalls.push(options);
    if (options.beforeSequence !== undefined) {
      if (olderHandler) return olderHandler();
      if (olderPage) return olderPage;
    }
    return currentHistory;
  });
  const getPlanBasis = vi.spyOn(liveApi, "getWorldOwnedPlanCommittedRevision")
    .mockImplementation(async () => currentBasis as any);
  vi.spyOn(liveApi, "getWorldPlanDocumentEditActions").mockResolvedValue({
    schema_version: "dmb_world_plan_action_projection_v1",
    basis: {
      world_id: worldId,
      document_id: documentId,
      object_revision: 7,
      work_revision_id: workRevisionId,
      revision_n: 1,
      content_sha256: contentSha256,
    },
    actions: [],
  });
  return {
    getHistory,
    getPlanBasis,
    historyCalls,
    setCurrent(value: WorldAgentConversationHistoryResponse) { currentHistory = value; },
    setPlanBasis(value: ReturnType<typeof committedRevision>) { currentBasis = value; },
    setOlder(value: WorldAgentConversationHistoryResponse) { olderPage = value; },
    setOlderHandler(value: () => Promise<WorldAgentConversationHistoryResponse>) { olderHandler = value; },
  };
}

function pendingAskKeys(): string[] {
  return Object.keys(localStorage).filter((key) =>
    key.startsWith(`dmb:world-plan-pending-ask:v1:${encodeURIComponent(worldId)}:${encodeURIComponent(documentId)}:`));
}

async function leavePendingGraphAsk(
  playableTarget: { kind: "scene" | "beat" | "choice" | "option"; id: string },
  initialHistory: WorldAgentConversationHistoryResponseV1 = history("conversation-a", 10, []),
  revisionN = 1,
  requestIds?: { clientThreadId: string; turnId: string },
) {
  const api = setupApi(initialHistory);
  if (revisionN !== 1) api.setPlanBasis({ ...committedRevision(), revision_n: revisionN });
  const sent: WorldPlanAgentTurnRequestV1[] = [];
  const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
    sent.push(request);
    throw new Error("connection reset after dispatch");
  });
  const mounted = render(conversationElement({ playableTarget, selectionGeneration: 0 }));

  await screen.findByText(/No messages yet/i);
  ensureWorldGraphAskEnabled();
  fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
    target: { value: "Who watches the western gate?" },
  });
  if (requestIds) {
    vi.spyOn(crypto, "randomUUID")
      .mockReturnValueOnce(requestIds.clientThreadId)
      .mockReturnValueOnce(requestIds.turnId);
  }
  fireEvent.click(screen.getByRole("button", { name: "Send message" }));
  expect(await screen.findByText(/outcome of this Graph-context Ask is uncertain/)).toBeInTheDocument();
  expect(await screen.findByText(/Saved Graph Asks stay in browser storage/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Refresh World history" })).toBeEnabled();
  expect(postAsk).toHaveBeenCalledTimes(1);
  expect(pendingAskKeys()).toHaveLength(1);
  return { api, mounted, postAsk, request: sent[0]! };
}

function capturePendingAskEvents(eventName: string): CustomEvent<unknown>[] {
  const events: CustomEvent<unknown>[] = [];
  const listener: EventListener = (event) => events.push(event as CustomEvent<unknown>);
  pendingAskEventListeners.push({ eventName, listener });
  window.addEventListener(eventName, listener);
  return events;
}

function pendingCommandKeys(): string[] {
  return Object.keys(localStorage).filter((key) =>
    key.startsWith(`dmb:world-agent-new-conversation:v1:${encodeURIComponent(worldId)}:`));
}

beforeAll(() => {
  Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });
});

beforeEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  setHarness();
});

afterEach(() => {
  vi.restoreAllMocks();
  for (const { eventName, listener } of pendingAskEventListeners.splice(0)) {
    window.removeEventListener(eventName, listener);
  }
  localStorage.clear();
  document.body.innerHTML = "";
  harness.host = null;
});

describe("World Plan conversation consumer", () => {
  it.each([
    ["What changes after the rescue?", "discuss"],
    ["Tell me about Lysandra.", "discuss"],
    ["Could we talk about making this scene shorter?", "discuss"],
    ["Add a lantern to the warehouse scene.", "propose"],
    ["Please rewrite the scene opening.", "propose"],
    ["Can you make the card more concise?", "propose"],
    ["Could you rewrite the scene opening?", "propose"],
    ["I want you to add a sensory detail.", "propose"],
    ["I want to add a sensory detail.", "propose"],
    ["Could we add a choice here?", "propose"],
    ["Why did the scene move to the warehouse?", "discuss"],
  ] as const)("routes a single composer message by its intent: %s", (message, intent) => {
    expect(classifyPlanComposerIntent(message)).toBe(intent);
  });

  it("keeps Plan scope, edit intent, and Graph source explicit in the conversation controls", async () => {
    setupApi(history("conversation-a", 1, []));
    render(conversationElement({
      playableTarget: { kind: "scene", id: "scene:arrival" },
      playableEditTarget: { kind: "choice", id: "choice:retreat", generation: 2 },
      editBridge: {},
    }));
    await screen.findByText(/No messages yet/i);

    const context = screen.getByRole("group", { name: "Current Plan context" });
    expect(context).toHaveTextContent("Question · scene:arrival");
    expect(context).toHaveTextContent("Change · choice:retreat");
    expect(within(context).getByRole("button", { name: "Clear Ask target" })).toBeInTheDocument();
    expect(within(context).getByRole("button", { name: "Clear edit target" })).toBeInTheDocument();

    const composer = screen.getByRole("region", { name: "Conversation composer" });
    expect(within(composer).getByRole("textbox", { name: "Message DungeonBuddy" })).toBeInTheDocument();
    expect(within(composer).queryByRole("radio")).not.toBeInTheDocument();
    expect(within(context).getByRole("button", { name: "Plan + World" })).toHaveAttribute("aria-pressed", "true");
  });

  it("defaults a fresh Plan conversation to its saved Plan and World context", async () => {
    setupApi(history("conversation-a", 1, []));
    render(conversationElement());
    await screen.findByText(/No messages yet/i);
    expect(screen.getByRole("button", { name: "Plan + World" })).toHaveAttribute("aria-pressed", "true");
  });

  it("keeps only the newest saved exchange in the reading path and folds prior turns", async () => {
    setupApi(history("conversation-a", 2, [
      makeTurn(1, "turn-1", "Earlier question", "Earlier answer"),
      makeTurn(2, "turn-2", "Latest question", "Latest answer"),
    ]));
    render(conversationElement());

    const transcript = await screen.findByRole("region", { name: "World conversation transcript" });
    expect(within(transcript).getByText("Latest question")).toBeInTheDocument();
    expect(within(transcript).getByText("Latest answer")).toBeInTheDocument();
    const earlier = within(transcript).getByText("Earlier conversation · 1").closest("details")!;
    expect(earlier).not.toHaveAttribute("open");
    expect(within(earlier).getByText("Earlier question")).toBeInTheDocument();
    expect(within(earlier).getByText("Earlier answer")).toBeInTheDocument();
  });

  it("uses the selected card as the Propose target without showing overridden section controls", async () => {
    setupApi(history("conversation-a", 1, []));
    render(conversationElement({
      playableEditTarget: { kind: "scene", id: "scene:recovery", generation: 2 },
      editBridge: {},
    }));
    await screen.findByText(/No messages yet/i);

    const context = screen.getByRole("group", { name: "Current Plan context" });
    expect(within(context).getByText("Change · scene:recovery")).toBeInTheDocument();
    expect(within(context).getByRole("button", { name: "Clear edit target" })).toBeInTheDocument();

    const composer = screen.getByRole("region", { name: "Conversation composer" });
    expect(within(composer).queryByRole("combobox", { name: "Plan section (optional)" })).not.toBeInTheDocument();
    expect(within(composer).queryByRole("button", { name: "Refresh sections" })).not.toBeInTheDocument();
    expect(within(composer).queryByText(/Use selection; otherwise insert at cursor/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Talk through the saved Plan, or choose Propose edit/)).not.toBeInTheDocument();
    expect(within(composer).getByRole("textbox", { name: "Message DungeonBuddy" })).toBeInTheDocument();
  });

  it("shows the verified content version and keeps Ask and Edit targets distinct", async () => {
    setupApi(history("conversation-a", 1, []));
    render(conversationElement({
      playableTarget: { kind: "scene", id: "scene:arrival" },
      playableEditTarget: { kind: "choice", id: "choice:retreat", generation: 2 },
      playableEditTargetDirty: true,
    }));

    const header = document.querySelector(".world-plan-agent-conversation__header")!;
    expect(await within(header).findByText(/Saved Plan · version 1/)).toBeInTheDocument();
    expect(header).not.toHaveTextContent("version 7");
    expect(within(header).getByText("Question · scene:arrival")).toBeInTheDocument();
    expect(within(header).getByText("Change · choice:retreat")).toBeInTheDocument();
    expect(within(header).getByRole("button", { name: "Clear Ask target" })).toBeInTheDocument();
    expect(within(header).getByRole("button", { name: "Clear edit target" })).toBeInTheDocument();

    fireEvent.click(screen.getByText("Advanced details"));
    expect(screen.getByRole("region", { name: "Ask target details" })).toHaveTextContent(
      "Ask uses the committed Plan. Unsaved editor changes are excluded",
    );
    expect(screen.getByRole("region", { name: "Edit target details" })).toHaveTextContent(
      "This proposal uses the unsaved Plan draft. Apply changes only the mounted draft; Save keeps the changes.",
    );
  });

  it("submits on plain Enter, preserves newline and IME keys, and blocks a duplicate while busy", async () => {
    const api = setupApi(history("conversation-a", 4, []));
    let releaseResponse: ((response: any) => void) | null = null;
    const response = new Promise<any>((resolve) => { releaseResponse = resolve; });
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockReturnValue(response);
    render(conversationElement());
    await screen.findByText(/No messages yet/i);
    const textarea = screen.getByLabelText("Message DungeonBuddy");
    fireEvent.change(textarea, { target: { value: "What happens at the opening?" } });

    expect(fireEvent.keyDown(textarea, { key: "Enter", code: "Enter", shiftKey: true })).toBe(true);
    expect(fireEvent.keyDown(textarea, { key: "Enter", code: "Enter", isComposing: true })).toBe(true);
    expect(fireEvent.keyDown(textarea, { key: "Enter", code: "Enter", ctrlKey: true })).toBe(true);
    expect(postAsk).not.toHaveBeenCalled();

    expect(fireEvent.keyDown(textarea, { key: "Enter", code: "Enter" })).toBe(false);
    await waitFor(() => expect(postAsk).toHaveBeenCalledTimes(1));
    expect(fireEvent.keyDown(textarea, { key: "Enter", code: "Enter" })).toBe(true);
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(postAsk.mock.calls[0]![0].message).toBe("What happens at the opening?");

    const request = postAsk.mock.calls[0]![0];
    api.setCurrent(history("conversation-a", 5, [historyTurnForAsk(request, "The path opens quietly.")]));
    await act(async () => {
      releaseResponse?.(agentResponse(request, "conversation-a", "The path opens quietly."));
      await response;
    });
    expect(await screen.findByText("The path opens quietly.")).toBeInTheDocument();
  });

  it("mounts the exact SERVER history projection and renders its validated citation", async () => {
    const api = setupApi(serverHistoryProjection);

    render(conversationElement());

    expect(await screen.findAllByText("The western gate is watched.")).toHaveLength(2);
    expect(screen.getByText("Grounded in World Graph evidence.")).toBeInTheDocument();
    expect(screen.getByText("graph-revision-test")).toBeInTheDocument();
    expect(screen.getByText(
      "The server recorded this Ask as complete. Its structured outcome is shown above; this turn will not be automatically resent.",
    )).toBeInTheDocument();
    const evidenceSummary = screen.getByText("1 evidence reference");
    const evidenceDetails = evidenceSummary.closest("details")!;
    fireEvent.click(evidenceSummary);
    expect(within(evidenceDetails).getByText("evidence-internal-test")).toBeInTheDocument();
    expect(api.getHistory).toHaveBeenCalledWith(worldId, { limit: 50, includeTurnCorrelation: true });
  });

  it("renders SERVER answer prose as readable rich text while preserving its evidence details", async () => {
    const segments = [
      "**Saved Plan:** The western gate is watched.",
      "**Evidence:** One graph reference.",
      "**Next:** Keep A sealed gate and a watchful guard on duty.",
    ];
    const answer = segments.join("\n");
    const projection = {
      ...serverHistoryProjection,
      turns: serverHistoryProjection.turns.map((turn, index) => index === 0
        ? {
          ...turn,
          assistant_text: answer,
          plan_context: {
            ...turn.plan_context,
            completion: {
              ...turn.plan_context.completion!,
              answer_segments: [
                { ...turn.plan_context.completion!.answer_segments[0]!, text: segments[0]! },
                {
                  kind: "plan_claim" as const,
                  text: segments[1]!,
                  plan_content_sha256: turn.plan_context.receipt.plan_basis.content_sha256,
                },
                { kind: "connective" as const, text: segments[2]! },
              ],
            },
          },
        }
        : turn),
    } satisfies WorldAgentConversationHistoryResponseV2;
    setupApi(projection);

    render(conversationElement());

    const transcript = await screen.findByRole("region", { name: "World conversation transcript" });
    expect(await within(transcript).findByText("Saved Plan:", { selector: "strong" })).toBeInTheDocument();
    expect(within(transcript).getByText("Evidence:", { selector: "strong" })).toBeInTheDocument();
    expect(within(transcript).getByText("Next:", { selector: "strong" })).toBeInTheDocument();
    expect(within(transcript).getByText("Keep A sealed gate and a watchful guard on duty.")).toBeInTheDocument();
    const renderedAnswer = transcript.querySelector(".world-plan-agent-answer")!;
    expect(renderedAnswer).not.toHaveTextContent("**Saved Plan:**");
    expect(renderedAnswer.querySelectorAll(":scope > div")).toHaveLength(3);
    expect(screen.getByText("Grounded in World Graph evidence.")).toBeInTheDocument();
    const evidenceSummary = screen.getByText("1 evidence reference");
    fireEvent.click(evidenceSummary);
    expect(within(evidenceSummary.closest("details")!).getByText("evidence-internal-test")).toBeInTheDocument();
  });

  it("keeps SERVER's card-A receipt and provenance after selection changes and history reloads", async () => {
    const api = setupApi(serverCardTargetHistoryProjection);
    const cardA = { kind: "scene" as const, id: "scene:opening" };
    const cardB = { kind: "scene" as const, id: "scene:ending" };
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn");
    const mounted = render(conversationElement({ playableTarget: cardA, selectionGeneration: 0 }));

    expect(await screen.findAllByText("The western gate is watched.")).toHaveLength(2);
    expect(screen.getByText("Grounded in World Graph evidence.")).toBeInTheDocument();
    expect(screen.getAllByText(/Playable target: scene scene:opening/)).toHaveLength(2);
    expect(screen.getByText("graph-revision-3")).toBeInTheDocument();
    const evidenceSummary = screen.getByText("1 evidence reference");
    fireEvent.click(evidenceSummary);
    expect(screen.getByText("evidence-internal-test")).toBeInTheDocument();
    expect(Array.from(screen.getByRole("region", { name: "World conversation transcript" }).querySelectorAll("article"))
      .map((article) => article.getAttribute("data-sequence"))).toEqual(["1", "2"]);

    mounted.rerender(conversationElement({ playableTarget: cardB, selectionGeneration: 1 }));
    expect(screen.getByRole("group", { name: "Selected Playable card for Ask" })).toHaveTextContent("scene:ending");
    expect(screen.getAllByText(/Playable target: scene scene:opening/)).toHaveLength(2);
    expect(screen.queryByText(/Playable target: scene scene:ending/)).not.toBeInTheDocument();

    const callsBeforeReload = api.historyCalls.length;
    mounted.unmount();
    render(conversationElement({ playableTarget: cardB, selectionGeneration: 1 }));

    expect(await screen.findAllByText("The western gate is watched.")).toHaveLength(2);
    expect(screen.getByText("Grounded in World Graph evidence.")).toBeInTheDocument();
    expect(screen.getAllByText(/Playable target: scene scene:opening/)).toHaveLength(2);
    expect(screen.getByText("evidence-internal-test")).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Selected Playable card for Ask" })).toHaveTextContent("scene:ending");
    expect(api.historyCalls).toHaveLength(callsBeforeReload + 1);
    expect(postAsk).not.toHaveBeenCalled();
  });

  it.each(["omitted", "mismatched"] as const)(
    "rejects the SERVER Graph history projection when card provenance is %s",
    async (failure) => {
      const projection = JSON.parse(JSON.stringify(serverCardTargetHistoryProjection)) as WorldAgentConversationHistoryResponseV2;
      const graphTurn = projection.turns[0]! as WorldAgentConversationHistoryTurnV2;
      if (failure === "omitted") {
        graphTurn.provenance.supporting_work = [];
      } else {
        graphTurn.provenance.supporting_work[0]!.object_id = "scene:ending";
      }
      setupApi(projection);

      render(conversationElement({ playableTarget: { kind: "scene", id: "scene:ending" } }));

      expect(await screen.findByText(/invalid Graph-context receipt/)).toBeInTheDocument();
      expect(screen.queryByText("The western gate is watched.")).not.toBeInTheDocument();
      expect(screen.queryByText(/Playable target: scene scene:ending/)).not.toBeInTheDocument();
    },
  );

  it.each(["duplicate", "mixed"] as const)(
    "rejects SERVER history with %s sequence order",
    async (failure) => {
      const projection = JSON.parse(JSON.stringify(serverCardTargetHistoryProjection)) as WorldAgentConversationHistoryResponseV2;
      if (failure === "duplicate") {
        projection.turns[1]!.sequence = projection.turns[0]!.sequence;
      } else {
        projection.turns.push({
          ...projection.turns[1]!,
          sequence: 3,
          turn_id: "00000000-0000-4000-8000-000000000034",
        });
      }
      setupApi(projection);

      render(conversationElement());

      expect(await screen.findByText(/invalid Graph-context receipt/)).toBeInTheDocument();
      expect(screen.queryByText("The western gate is watched.")).not.toBeInTheDocument();
    },
  );

  it("sends the explicit additive Graph policy with the committed Plan and card pins, then reads v2 history citations", async () => {
    const api = setupApi(history("conversation-a", 4, []));
    const card = { kind: "scene" as const, id: "scene:opening" };
    let captured: WorldPlanAgentTurnRequestV1 | null = null;
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      captured = request;
      const response = await policyResponse(request, "conversation-a", "The western gate is watched.");
      const turn = {
        ...historyTurnForAsk(request, "The western gate is watched."),
        plan_context: response.plan_context,
      };
      api.setCurrent(await historyV2("conversation-a", 5, [turn]));
      return response;
    });

    render(conversationElement({ playableTarget: card, savedDirty: true }));
    await screen.findByText(/No messages yet/i);
    const graphToggle = getGraphContextToggle();
    expect(graphToggle).toHaveAttribute("aria-pressed", "true");
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "Who watches the western gate?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText("Grounded in World Graph evidence.")).toBeInTheDocument();
    expect(await screen.findByText("graph-revision-test")).toBeInTheDocument();
    const evidenceSummary = screen.getByText("1 evidence reference");
    const evidenceDetails = evidenceSummary.closest("details")!;
    expect(evidenceDetails).not.toHaveAttribute("open");
    fireEvent.click(evidenceSummary);
    expect(within(evidenceDetails).getByText("evidence-internal-test")).toBeInTheDocument();
    expect(screen.getByText(/Playable target: scene scene:opening · marker grammar v1/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Advanced details"));
    expect(screen.getByRole("region", { name: "Ask target details" })).toHaveTextContent(
      "Ask uses the committed Plan. Unsaved editor changes are excluded",
    );
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(captured).toMatchObject({
      schema: "dmb_agent_turn_request_v1",
      plan_context_policy: { schema: "dmb_plan_context_policy_v1", policy: "auto_plan_world" },
      primary_work: {
        kind: "plan",
        object_id: documentId,
        expected_revision: 7,
        expected_revision_n: 1,
        expected_content_sha256: contentSha256,
      },
      playable_target: { schema: "dmb_plan_playable_target_v1", ...card },
      client_work_state: "saved_dirty",
      graph_request: { mode: "none" },
      graph_selection: null,
    });
    expect(Object.keys(captured ?? {}).sort()).toEqual([
      "client_thread_id", "client_work_state", "graph_request", "graph_selection", "message", "owner_scope",
      "plan_context_policy", "playable_target", "primary_work", "schema", "surface", "turn_id",
    ]);
    expect(JSON.stringify(captured)).not.toContain("unsaved editor bytes");
    expect(JSON.stringify(captured)).not.toContain("native_world_id");
    expect(JSON.stringify(captured)).not.toContain("graph_revision");
    expect(getGraphContextToggle()).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByText(/assertion-internal-test|native-world-internal-test/)).not.toBeInTheDocument();
  });

  it("renders each validated v2 completion outcome and safe execution recovery guidance", async () => {
    const outcomes: Array<[WorldPlanGraphAnswerContextStatusV1, WorldPlanGraphExecutionProjectionV1, string]> = [
      ["graph_grounded", {
        schema: "dmb_agent_plan_world_graph_execution_projection_v1",
        claimability: "completed", authorization_state: "response_received", automatic_redispatch: false,
      }, "Grounded in World Graph evidence."],
      ["graph_grounded_partial", {
        schema: "dmb_agent_plan_world_graph_execution_projection_v1",
        claimability: "blocked_unknown_or_sent", authorization_state: "outcome_unknown", automatic_redispatch: false,
      }, "Partially grounded in World Graph evidence; coverage was incomplete."],
      ["plan_only_insufficient_evidence", {
        schema: "dmb_agent_plan_world_graph_execution_projection_v1",
        claimability: "safe_to_reclaim_without_dispatch", authorization_state: "none", automatic_redispatch: false,
      }, "No sufficient World Graph evidence was available; this answer uses the saved Plan context only."],
      ["plan_only_graph_unused", {
        schema: "dmb_agent_plan_world_graph_execution_projection_v1",
        claimability: "explicit_new_attempt_required", authorization_state: "known_not_sent", automatic_redispatch: false,
      }, "Graph context was available; no Graph claims were cited or used in the structured answer."],
    ];
    const turns: WorldAgentConversationHistoryTurnV2[] = [];
    for (const [status, execution] of outcomes) {
      const context = await planGraphContext(status, { execution });
      turns.push(policyHistoryTurn(
        turns.length + 1,
        `status-turn-${turns.length + 1}`,
        `Question ${status}`,
        `Answer ${status}`,
        context,
      ));
    }
    setupApi(await historyV2("conversation-a", 8, turns));

    render(conversationElement());

    for (const [, , label] of outcomes) expect(await screen.findByText(label)).toBeInTheDocument();
    expect(screen.getByText(/provider dispatch did not begin\. Submit a new Ask if you want another attempt/)).toBeInTheDocument();
    expect(screen.getByText(/attempt outcome is unknown\. Refresh World history before taking another action/)).toBeInTheDocument();
    expect(screen.getByText(/A new attempt requires a new Ask/)).toBeInTheDocument();
    expect(screen.queryByText(/assertion-internal-test|context_receipt_sha256/)).not.toBeInTheDocument();
    expect(screen.getAllByText("graph-revision-test")).toHaveLength(2);
  });

  it("accepts parent-validated tool evidence when the initial Graph receipt was insufficient", async () => {
    const api = setupApi(history("conversation-a", 4, []));
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      const response = await policyResponse(request, "conversation-a", "The tool found a watched gate.", "graph_grounded");
      const context = response.plan_context;
      context.receipt.graph_packet.candidate_assertion_ids = [];
      context.receipt.graph_packet.candidate_relationship_ids = [];
      context.receipt.graph_packet.candidate_evidence_ref_ids = [];
      context.receipt.graph_packet.retrieval_status = "empty";
      context.receipt.graph_packet.evidence_sufficiency_status = "insufficient";
      context.receipt.graph_packet.omission_reasons = ["no_claim_ready_evidence"];
      context.receipt.assembled_input.packet_disposition = "omitted_insufficient";
      context.receipt.assembled_input.packet_disposition_reason = "insufficient_evidence";
      context.receipt.assembled_input.dispatched_packet_sha256 = null;
      context.receipt.assembled_input.dispatched_assertion_ids = [];
      context.receipt.assembled_input.dispatched_relationship_ids = [];
      context.receipt.assembled_input.dispatched_evidence_ref_ids = [];
      const claim = context.completion!.answer_segments[0]!;
      expect(claim.kind).toBe("graph_claim");
      if (claim.kind !== "graph_claim") throw new Error("Fixture expected one Graph claim.");
      claim.target_id = "tool-assertion-test";
      claim.evidence_ref_ids = ["tool-evidence-test"];
      const citation = context.completion!.citation_map!.entries[0]!;
      citation.target_id = claim.target_id;
      citation.evidence_ref_ids = claim.evidence_ref_ids;
      await resealPlanGraphContext(context);
      api.setCurrent(await historyV2("conversation-a", 5, [policyHistoryTurn(
        1, request.turn_id, request.message, "The tool found a watched gate.", context,
      )]));
      return response;
    });

    render(conversationElement());
    await screen.findByText(/No messages yet/i);
    ensureWorldGraphAskEnabled();
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Check the northern gate." } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText("Grounded in World Graph evidence.")).toBeInTheDocument();
    expect(await screen.findByText("The tool found a watched gate.")).toBeInTheDocument();
    expect(screen.getByText(/source text not opened\./)).toBeInTheDocument();
    const details = screen.getByText("1 evidence reference").closest("details")!;
    fireEvent.click(screen.getByText("1 evidence reference"));
    expect(within(details).getByText("tool-evidence-test")).toBeInTheDocument();
    expect(postAsk).toHaveBeenCalledTimes(1);
  });

  it("accepts a V2 source-opened citation in ordinary saved history", async () => {
    const context = await planGraphContext("graph_grounded");
    const completion = context.completion! as unknown as Record<string, unknown>;
    const citationMap = completion.citation_map as Record<string, unknown>;
    const entries = citationMap.entries as Array<Record<string, unknown>>;
    completion.schema = "dmb_plan_world_graph_completion_v2";
    citationMap.schema = "dmb_graph_citation_map_v2";
    entries[0]!.source_opened = true;
    entries[0]!.source_read_ids = ["source-read:one"];
    setupApi(await historyV2("conversation-a", 5, [policyHistoryTurn(
      1, "v2-read-turn", "What does the source say?", "The western gate is watched.", context,
    )]));

    render(conversationElement());
    expect((await screen.findAllByText("The western gate is watched.")).length).toBeGreaterThan(0);
    expect(screen.getByText(/source passage read\./)).toBeInTheDocument();
    expect(screen.queryByText(/source text not opened\./)).not.toBeInTheDocument();
    expect(screen.queryByText(/invalid Graph-context receipt/)).not.toBeInTheDocument();
  });

  it("accepts mixed initial and tool citations for a partial completion with truncated retrieval", async () => {
    const api = setupApi(history("conversation-a", 4, []));
    vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      const response = await policyResponse(request, "conversation-a", "The gate is watched, and a patrol circles it.", "graph_grounded_partial");
      const context = response.plan_context;
      context.completion!.answer_segments.push(
        { kind: "connective", text: " A patrol also circles it." },
        {
          kind: "graph_claim",
          claim_id: "tool-claim-test",
          text: "A patrol circles it.",
          target_kind: "relationship",
          target_id: "tool-relationship-test",
          graph_revision: "graph-revision-test",
          evidence_ref_ids: ["tool-evidence-test"],
        },
      );
      context.completion!.citation_map!.entries.push({
        claim_id: "tool-claim-test",
        target_kind: "relationship",
        target_id: "tool-relationship-test",
        graph_revision: "graph-revision-test",
        evidence_ref_ids: ["tool-evidence-test"],
        source_opened: false,
      });
      await resealPlanGraphContext(context);
      api.setCurrent(await historyV2("conversation-a", 5, [policyHistoryTurn(
        1, request.turn_id, request.message, "The gate is watched, and a patrol circles it.", context,
      )]));
      return response;
    });

    render(conversationElement());
    await screen.findByText(/No messages yet/i);
    ensureWorldGraphAskEnabled();
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Describe the gate patrol." } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText("Partially grounded in World Graph evidence; coverage was incomplete.")).toBeInTheDocument();
    const evidenceSummaries = screen.getAllByText("1 evidence reference");
    expect(evidenceSummaries).toHaveLength(2);
    for (const summary of evidenceSummaries) fireEvent.click(summary);
    expect(screen.getByText("evidence-internal-test")).toBeInTheDocument();
    expect(screen.getByText("tool-evidence-test")).toBeInTheDocument();
  });

  it("keeps pending, interrupted, and failed policy turns without inventing a completion", async () => {
    const turns: WorldAgentConversationHistoryTurnV2[] = [];
    for (const lifecycle of ["accepted", "interrupted", "failed"] as const) {
      const context = await planGraphContext("plan_only_graph_unused", { completion: false, execution: null });
      turns.push(policyHistoryTurn(
        turns.length + 1,
        `incomplete-${lifecycle}`,
        `Question ${lifecycle}`,
        null,
        context,
        lifecycle,
      ));
    }
    setupApi(await historyV2("conversation-a", 9, turns));

    render(conversationElement());

    expect(await screen.findByText("Question failed")).toBeInTheDocument();
    const earlier = screen.getByText(/Earlier conversation/).closest("details")!;
    fireEvent.click(earlier.querySelector("summary")!);
    const failed = within(earlier).getByText("Question failed").closest("article")!;
    fireEvent.click(failed.querySelector("details > summary")!);
    expect(within(failed).getByText("This World history turn failed; no final Graph-context completion was recorded.")).toBeInTheDocument();
    expect(within(failed).getByText("World history records this turn as failed. The execution disposition was not recorded. The saved turn is not automatically reposted; this view offers no retry.")).toBeInTheDocument();
    expect(within(earlier).queryByText("No final Graph-context completion has been recorded for this turn yet.")).not.toBeInTheDocument();
    expect(screen.queryByText(/Graph context was available; no Graph claims/)).not.toBeInTheDocument();
  });

  it("rejects a v2 history citation that does not map to its validated graph claim", async () => {
    const context = await planGraphContext("graph_grounded");
    context.completion!.citation_map!.entries[0]!.target_id = "unsupported-claim-target";
    const turn = policyHistoryTurn(1, "bad-citation-turn", "Question", "Should not display", context);
    setupApi(await historyV2("conversation-a", 10, [turn]));

    render(conversationElement());

    expect(await screen.findByText(/invalid Graph-context receipt/)).toBeInTheDocument();
    expect(screen.queryByText("Should not display")).not.toBeInTheDocument();
  });

  it("accepts a valid receipt for a different historical Plan when that turn provenance matches", async () => {
    const context = await planGraphContext("graph_grounded");
    context.receipt.plan_basis.document_id = "older-plan-test";
    context.receipt.plan_basis.object_revision = 3;
    context.receipt.plan_basis.work_revision_id = "00000000-0000-4000-8000-000000000099";
    context.receipt.plan_basis.revision_n = 2;
    context.receipt.plan_basis.content_sha256 = "b".repeat(64);
    await resealPlanGraphContext(context);
    const turn = policyHistoryTurn(1, "older-plan-turn", "What did the north gate reveal?", "A watch patrol circles the gate.", context);
    setupApi(await historyV2("conversation-a", 11, [turn]));

    render(conversationElement());

    expect(await screen.findByText("A watch patrol circles the gate.")).toBeInTheDocument();
    expect(screen.getByText("Grounded in World Graph evidence.")).toBeInTheDocument();
  });

  it("rejects internally valid history receipts for a foreign World or mismatched Plan revision", async () => {
    const foreignContext = await planGraphContext("graph_grounded");
    foreignContext.receipt.plan_basis.world_id = "foreign-world-test";
    foreignContext.receipt.graph_authority.managed_world_id = "foreign-world-test";
    await resealPlanGraphContext(foreignContext);
    setupApi(await historyV2("conversation-a", 12, [policyHistoryTurn(
      1, "foreign-world-turn", "Foreign?", "Must not display", foreignContext,
    )]));
    const foreignView = render(conversationElement());
    expect(await screen.findByText(/invalid Graph-context receipt/)).toBeInTheDocument();
    expect(screen.queryByText("Must not display")).not.toBeInTheDocument();
    foreignView.unmount();

    vi.restoreAllMocks();
    localStorage.clear();
    const wrongRevisionContext = await planGraphContext("graph_grounded");
    wrongRevisionContext.receipt.plan_basis.object_revision = 8;
    await resealPlanGraphContext(wrongRevisionContext);
    const wrongRevisionTurn = policyHistoryTurn(
      1, "wrong-plan-revision-turn", "Wrong revision?", "Must also not display", wrongRevisionContext,
    );
    wrongRevisionTurn.provenance.primary_work.revision = "7";
    wrongRevisionTurn.provenance.primary_work.object_revision = 7;
    setupApi(await historyV2("conversation-a", 13, [wrongRevisionTurn]));
    render(conversationElement());

    expect(await screen.findByText(/invalid Graph-context receipt/)).toBeInTheDocument();
    expect(screen.queryByText("Must also not display")).not.toBeInTheDocument();
  });

  it("rejects completed policy history without completion and in-progress history with final completion", async () => {
    const missingCompletion = await planGraphContext("plan_only_graph_unused", { completion: false });
    setupApi(await historyV2("conversation-a", 14, [policyHistoryTurn(
      1, "completed-without-completion", "Missing completion?", "Must not display", missingCompletion,
    )]));
    const missingView = render(conversationElement());
    expect(await screen.findByText(/invalid Graph-context receipt/)).toBeInTheDocument();
    expect(screen.queryByText("Must not display")).not.toBeInTheDocument();
    missingView.unmount();

    vi.restoreAllMocks();
    localStorage.clear();
    const finalCompletion = await planGraphContext("plan_only_graph_unused");
    setupApi(await historyV2("conversation-a", 15, [policyHistoryTurn(
      1, "running-with-completion", "Premature completion?", "Also must not display", finalCompletion, "running",
    )]));
    render(conversationElement());

    expect(await screen.findByText(/invalid Graph-context receipt/)).toBeInTheDocument();
    expect(screen.queryByText("Also must not display")).not.toBeInTheDocument();
  });

  it("keeps a malformed policy response pending instead of accepting its prose", async () => {
    setupApi(history("conversation-a", 4, []));
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      const response = await policyResponse(request, "conversation-a", "Unsupported answer.");
      response.plan_context.completion!.citation_map!.entries[0]!.target_id = "unsupported-target";
      return response;
    });
    render(conversationElement());
    await screen.findByText(/No messages yet/i);
    ensureWorldGraphAskEnabled();
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Ask for a grounded answer." } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText(/outcome of this Graph-context Ask is uncertain/)).toBeInTheDocument();
    expect(screen.queryByText("Unsupported answer.")).not.toBeInTheDocument();
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(pendingAskKeys()).toHaveLength(1);
  });

  it("rejects a completion citation map that is not one-to-one with graph claims", async () => {
    setupApi(history("conversation-a", 4, []));
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      const response = await policyResponse(request, "conversation-a", "Structurally unsupported answer.");
      response.plan_context.completion!.citation_map!.entries = [];
      return response;
    });
    render(conversationElement());
    await screen.findByText(/No messages yet/i);
    ensureWorldGraphAskEnabled();
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Ask with a malformed map." } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText(/outcome of this Graph-context Ask is uncertain/)).toBeInTheDocument();
    expect(screen.queryByText("Structurally unsupported answer.")).not.toBeInTheDocument();
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(pendingAskKeys()).toHaveLength(1);
  });

  it("clears a definitive pre-dispatch failure from pending recovery", async () => {
    setupApi(history("conversation-a", 4, []));
    liveApi.setNativeGraphAccessToken("test-only-local-operator-credential-value");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 413,
      statusText: "Payload Too Large",
      text: async () => JSON.stringify({
        detail: {
          code: "provider_envelope_over_budget",
          message: "The selected model context cannot contain this request.",
          plan_context_failure: {
            schema: "dmb_plan_world_graph_context_failure_v1",
            status: "pre_dispatch_failed",
            failure_code: "provider_envelope_over_budget",
            provider_dispatched: false,
            automatic_downgrade: false,
          },
        },
      }),
    } as Response);
    render(conversationElement());
    await screen.findByText(/No messages yet/i);
    ensureWorldGraphAskEnabled();
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Check the north gate." } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText(/server confirmed provider dispatch did not begin/)).toBeInTheDocument();
    expect(screen.getByText(/provider_envelope_over_budget/)).toBeInTheDocument();
    expect(screen.getByText(/no answer was saved/)).toBeInTheDocument();
    expect(screen.queryByText(/outcome of this Graph-context Ask is uncertain/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry saved Ask" })).not.toBeInTheDocument();
    const turnCall = fetchSpy.mock.calls.find(([url]) => String(url) === "/api/live/agent/turn");
    expect(turnCall).toBeDefined();
    expect(JSON.parse(String(turnCall?.[1]?.body))).toHaveProperty(
      "plan_context_policy",
      { schema: "dmb_plan_context_policy_v1", policy: "auto_plan_world" },
    );
    expect(pendingAskKeys()).toEqual([]);
    expect(screen.queryByRole("region", { name: "Pending Ask recovery" })).not.toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("allows a fresh Graph Ask after clearing a definitive pre-dispatch failure", async () => {
    const api = setupApi(history("conversation-a", 4, []));
    const failure = new liveApi.LiveApiError("The selected model context cannot contain this request.", 413, {
      code: "provider_envelope_over_budget",
      planContextFailure: {
        schema: "dmb_plan_world_graph_context_failure_v1",
        status: "pre_dispatch_failed",
        failure_code: "provider_envelope_over_budget",
        provider_dispatched: false,
        automatic_downgrade: false,
      },
    });
    const requests: WorldPlanAgentTurnRequestV1[] = [];
    const answer = "The fresh Graph Ask was answered.";
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      requests.push(request);
      if (requests.length === 1) throw failure;
      const response = await policyResponse(request, "conversation-a", answer);
      const completedTurn = {
        ...historyTurnForAsk(request, answer),
        plan_context: response.plan_context,
      };
      api.setCurrent(await historyV2("conversation-a", 4, [completedTurn]));
      return response;
    });
    render(conversationElement());
    await screen.findByText(/No messages yet/i);
    ensureWorldGraphAskEnabled();
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "Ask once before fixing the budget." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText(/no answer was saved/)).toBeInTheDocument();
    expect(pendingAskKeys()).toEqual([]);
    expect(postAsk).toHaveBeenCalledTimes(1);

    ensureWorldGraphAskEnabled();
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "Ask again after fixing the request budget." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText(answer)).toBeInTheDocument();
    expect(postAsk).toHaveBeenCalledTimes(2);
    expect(requests[1]!.turn_id).not.toBe(requests[0]!.turn_id);
    expect(pendingAskKeys()).toEqual([]);
  });

  it("does not repost an uncertain Graph-context Ask from browser recovery", async () => {
    setupApi(history("conversation-a", 4, []));
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockRejectedValue(new Error("connection reset after dispatch"));
    render(conversationElement());
    await screen.findByText(/No messages yet/i);
    ensureWorldGraphAskEnabled();
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Check the north gate." } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText(/outcome of this Graph-context Ask is uncertain/)).toBeInTheDocument();
    expect(await screen.findByText(/Saved Graph Asks stay in browser storage/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry saved Ask" })).not.toBeInTheDocument();
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(pendingAskKeys()).toHaveLength(1);
  });

  it("keeps Hermes initialization 503 unresolved without a dispatch receipt", async () => {
    setupApi(history("conversation-a", 4, []));
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockRejectedValue(
      new liveApi.LiveApiError("Hermes runtime initialization failed.", 503, {
        code: "hermes_agent_init_error",
      }),
    );
    render(conversationElement());
    await screen.findByText(/No messages yet/i);
    ensureWorldGraphAskEnabled();
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "Ask about the northern gate." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText(/outcome of this Graph-context Ask is uncertain/)).toBeInTheDocument();
    expect(screen.getByText(/Hermes runtime initialization failed\./)).toBeInTheDocument();
    expect(screen.queryByText(/provider dispatch did not begin/)).not.toBeInTheDocument();
    expect(screen.queryByText(/no answer was saved/)).not.toBeInTheDocument();
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(pendingAskKeys()).toHaveLength(1);
  });

  it.each([
    {
      label: "provider dispatch is reported",
      status: 503,
      code: "provider_outcome_unknown",
      failureCode: "provider_outcome_unknown",
      providerDispatched: true,
      extraFailureField: false,
    },
    {
      label: "the failure code is unrecognized",
      status: 413,
      code: "unknown_pre_dispatch_failure",
      failureCode: "unknown_pre_dispatch_failure",
      providerDispatched: false,
      extraFailureField: false,
    },
    {
      label: "the response and failure codes contradict each other",
      status: 413,
      code: "provider_envelope_over_budget",
      failureCode: "native_binding_invalid",
      providerDispatched: false,
      extraFailureField: false,
    },
    {
      label: "the HTTP status contradicts the failure code",
      status: 413,
      code: "native_binding_invalid",
      failureCode: "native_binding_invalid",
      providerDispatched: false,
      extraFailureField: false,
    },
    {
      label: "the top-level response code is missing",
      status: 413,
      code: null,
      failureCode: "provider_envelope_over_budget",
      providerDispatched: false,
      extraFailureField: false,
    },
    {
      label: "the failure contains unrecognized fields",
      status: 413,
      code: "provider_envelope_over_budget",
      failureCode: "provider_envelope_over_budget",
      providerDispatched: false,
      extraFailureField: true,
    },
  ] as const)("keeps a Graph Ask pending when $label", async ({
    status,
    code,
    failureCode,
    providerDispatched,
    extraFailureField,
  }) => {
    setupApi(history("conversation-a", 4, []));
    liveApi.setNativeGraphAccessToken("test-only-local-operator-credential-value");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status,
      statusText: "Injected failure",
      text: async () => JSON.stringify({
        detail: {
          ...(code === null ? {} : { code }),
          message: `The injected failure is ${code}.`,
          plan_context_failure: {
            schema: "dmb_plan_world_graph_context_failure_v1",
            status: "pre_dispatch_failed",
            failure_code: failureCode,
            provider_dispatched: providerDispatched,
            automatic_downgrade: false,
            ...(extraFailureField ? { retryable: true } : {}),
          },
        },
      }),
    } as Response);
    render(conversationElement());
    await screen.findByText(/No messages yet/i);
    ensureWorldGraphAskEnabled();
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Check the north gate." } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText(/outcome of this Graph-context Ask is uncertain/)).toBeInTheDocument();
    expect(screen.queryByText(/server confirmed provider dispatch did not begin/)).not.toBeInTheDocument();
    expect(pendingAskKeys()).toHaveLength(1);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("reconciles a lost Graph Ask from its exact completed history after remount without using the new card selection", async () => {
    const cardA = { kind: "scene" as const, id: "scene:opening" };
    const cardB = { kind: "scene" as const, id: "scene:ending" };
    const { api, mounted, postAsk, request } = await leavePendingGraphAsk(cardA, history("conversation-a", 10, []), 3);
    const storageKey = pendingAskKeys()[0]!;
    const originalEnvelope = localStorage.getItem(storageKey);
    mounted.unmount();

    const context = await planGraphContext("graph_grounded", { request, execution: null });
    const answer = "The western gate is watched.";
    const correlationKey = await expectedHistoryCorrelationKey(worldId, request.turn_id);
    const completedTurn = withPersistedCorrelation(policyHistoryTurn(
      1, request.turn_id, request.message, answer, context, "completed", request,
    ), correlationKey, "00000000-0000-4000-8000-000000000091");
    expect(completedTurn.turn_id).not.toBe(request.turn_id);
    expect(completedTurn.plan_context.receipt.plan_basis).toMatchObject({ object_revision: 7, revision_n: 3 });
    api.setCurrent(await historyV3("conversation-a", 10, [completedTurn]));

    render(conversationElement({ playableTarget: cardB, selectionGeneration: 1 }));

    expect(await screen.findAllByText(answer)).toHaveLength(2);
    expect(await screen.findByText("Grounded in World Graph evidence.")).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Selected Playable card for Ask" })).toHaveTextContent(cardB.id);
    const transcript = screen.getByRole("region", { name: "World conversation transcript" });
    const answerTurn = transcript.querySelector("article");
    expect(answerTurn).toHaveTextContent(cardA.id);
    expect(answerTurn).not.toHaveTextContent(cardB.id);
    await waitFor(() => expect(pendingAskKeys()).toEqual([]));
    expect(localStorage.getItem(storageKey)).toBeNull();
    expect(screen.queryByRole("region", { name: "Pending Ask recovery" })).not.toBeInTheDocument();
    expect(JSON.parse(originalEnvelope ?? "{}").request.playable_target.id).toBe(cardA.id);
    expect(postAsk).toHaveBeenCalledTimes(1);
  });

  it("reconciles the first Ask when its completed turn opened the World conversation", async () => {
    const cardA = { kind: "scene" as const, id: "scene:opening" };
    const { api, mounted, postAsk, request } = await leavePendingGraphAsk(cardA, history(null, 0, []), 3);
    const storageKey = pendingAskKeys()[0]!;
    expect(JSON.parse(localStorage.getItem(storageKey) ?? "{}").origin).toMatchObject({
      pointerRevision: 0,
      conversationId: null,
    });
    mounted.unmount();

    const context = await planGraphContext("graph_grounded", { request, execution: null });
    const answer = "The western gate is watched.";
    const correlationKey = await expectedHistoryCorrelationKey(worldId, request.turn_id);
    const completedTurn = withPersistedCorrelation(policyHistoryTurn(
      1, request.turn_id, request.message, answer, context, "completed", request,
    ), correlationKey, "00000000-0000-4000-8000-000000000092");
    api.setCurrent(await historyV3("first-conversation", 1, [completedTurn]));

    render(conversationElement({ playableTarget: cardA, selectionGeneration: 1 }));

    expect(await screen.findAllByText(answer)).toHaveLength(2);
    await waitFor(() => expect(pendingAskKeys()).toEqual([]));
    expect(screen.queryByRole("region", { name: "Pending Ask recovery" })).not.toBeInTheDocument();
    expect(postAsk).toHaveBeenCalledTimes(1);
  });

  it("classifies an exact v3 failed turn while preserving the failed and unmatched local Ask records", async () => {
    const playableTarget = { kind: "scene" as const, id: "scene:opening" };
    const clientTurnId = "55e38574-2d69-429e-9f91-e593e96b7830";
    const durableTurnId = "ce97be5a-18b5-4fb5-a820-8161716fe516";
    const { api, mounted, postAsk, request } = await leavePendingGraphAsk(
      playableTarget,
      history("conversation-a", 10, []),
      1,
      { clientThreadId: "2d7c2e17-5525-43a8-824c-adc54d4b0470", turnId: clientTurnId },
    );
    expect(request.turn_id).toBe(clientTurnId);
    const failedStorageKey = pendingAskKeys()[0]!;
    const failedBytes = localStorage.getItem(failedStorageKey)!;
    const failedEnvelope = JSON.parse(failedBytes);
    const unknownIds = [
      "9e316000-0000-4000-8000-000000000001",
      "5f700000-0000-4000-8000-000000000002",
      "b1f59500-0000-4000-8000-000000000003",
    ];
    const unknownRecords = unknownIds.map((turnId, index) => {
      const envelope = {
        ...failedEnvelope,
        request: {
          ...failedEnvelope.request,
          client_thread_id: `2d7c2e17-5525-43a8-824c-adc54d4b000${index + 1}`,
          turn_id: turnId,
          message: `Unmatched saved question ${index + 1}`,
        },
      };
      const origin = envelope.origin;
      const basis = [origin.objectRevision, origin.workRevisionId, origin.revisionN, origin.contentSha256, turnId].join("|");
      const storageKey = `dmb:world-plan-pending-ask:v1:${encodeURIComponent(worldId)}:${encodeURIComponent(documentId)}:${encodeURIComponent(basis)}`;
      const serialized = JSON.stringify(envelope);
      localStorage.setItem(storageKey, serialized);
      return { storageKey, serialized, turnId };
    });
    mounted.unmount();

    const failedTurn = await failedV3HistoryTurn(request, { durableTurnId });
    expect(failedTurn.turn_id).toBe(durableTurnId);
    api.setCurrent(await historyV3("conversation-a", 10, [failedTurn]));
    render(conversationElement({ playableTarget, editBridge: {} }));

    expect(await screen.findByText("Buddy couldn’t finish this reply. Your Plan was not changed.")).toBeInTheDocument();
    openLatestTurnDetails();
    const graphRecovery = await screen.findByRole("region", { name: "World Graph evidence and recovery" });
    expect(graphRecovery).toHaveTextContent("Exact V3 World history records this turn as failed.");
    expect(graphRecovery).toHaveTextContent("This World history turn failed; no final Graph-context completion was recorded.");
    expect(graphRecovery).toHaveTextContent("The provider returned a response; no final Graph-context completion was recorded.");
    expect(graphRecovery).toHaveTextContent("The saved turn is not automatically reposted; this view offers no retry.");
    expect(graphRecovery).not.toHaveTextContent("No final Graph-context completion has been recorded for this turn yet.");
    expect(graphRecovery).not.toHaveTextContent("Refresh World history before taking another action");
    expect(graphRecovery).not.toHaveTextContent("This saved turn will not be automatically reposted");
    expect(screen.getByText("This World history turn failed; no final Graph-context completion was recorded.")).toBeInTheDocument();
    expect(screen.queryByText(/awaiting exact completed history match/)).not.toBeInTheDocument();
    const failedSummary = screen.getByText(`Graph Ask · ${clientTurnId} · failure confirmed`);
    fireEvent.click(failedSummary);
    expect(screen.getByText("Status · terminal failure confirmed in exact V3 World history")).toBeInTheDocument();
    for (const record of unknownRecords) fireEvent.click(screen.getByText(`Graph Ask · ${record.turnId}`));
    expect(screen.getAllByText("Status · outcome not confirmed in exact V3 World history")).toHaveLength(3);

    fireEvent.click(screen.getByText(/Needs attention/));
    const pending = screen.getByRole("region", { name: "Saved Ask recovery records" });
    expect(pending).toHaveTextContent("Ask recovery · 3 Graph outcomes unconfirmed · 1 recorded failure · 4 saved");
    expect(pending).toHaveTextContent("3 Graph Ask outcomes remain unconfirmed in exact V3 World history; 1 failed turn is already recorded. All 4 Graph Ask records remain saved. Refresh never reposts them.");
    const body = screen.getByRole("region", { name: "Saved World Plan conversation" })
      .querySelector(".world-plan-agent-conversation__body");
    const composer = screen.getByRole("region", { name: "Conversation composer" });
    expect(body).not.toContainElement(composer);
    expect(composer).toContainElement(screen.getByLabelText("Message DungeonBuddy"));
    expect(composer).toContainElement(screen.getByRole("textbox", { name: "Message DungeonBuddy" }));
    expect(within(composer).queryByRole("radio")).not.toBeInTheDocument();
    expect(localStorage.getItem(failedStorageKey)).toBe(failedBytes);
    for (const record of unknownRecords) expect(localStorage.getItem(record.storageKey)).toBe(record.serialized);
    expect(pendingAskKeys()).toHaveLength(4);
    expect(postAsk).toHaveBeenCalledTimes(1);

    const historyCallCount = api.historyCalls.length;
    fireEvent.click(screen.getByRole("button", { name: "Refresh World history" }));
    await waitFor(() => expect(api.historyCalls.length).toBeGreaterThan(historyCallCount));
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem(failedStorageKey)).toBe(failedBytes);
    for (const record of unknownRecords) expect(localStorage.getItem(record.storageKey)).toBe(record.serialized);
    expect(pendingAskKeys()).toHaveLength(4);
  });

  it("shows a recorded World-history failure after switching Plans without a local envelope", async () => {
    const otherPlanId = "62a91472";
    const playableTarget = { kind: "scene" as const, id: "scene:opening" };
    const { api, mounted, postAsk, request } = await leavePendingGraphAsk(playableTarget);
    const failedStorageKey = pendingAskKeys()[0]!;
    const failedBytes = localStorage.getItem(failedStorageKey)!;
    expect(JSON.parse(failedBytes).origin.documentId).toBe(documentId);
    mounted.unmount();

    const failedTurn = await failedV3HistoryTurn(request);
    api.setCurrent(await historyV3("conversation-a", 10, [failedTurn]));
    api.setPlanBasis(committedRevision(otherPlanId));
    harness.agent.scope = {
      campaignId: `world-plan-agent:world:${encodeURIComponent(worldId)}:document:${encodeURIComponent(otherPlanId)}`,
      surfaceId: "plan",
      sessionNumber: null,
      documentId: otherPlanId,
    };
    harness.agent.activeThread = null;

    render(conversationElement({ documentId: otherPlanId }));

    expect(await screen.findByText("Buddy couldn’t finish this reply. Your Plan was not changed.")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Why this reply stopped"));
    const graphRecovery = await screen.findByRole("region", { name: "World Graph evidence and recovery" });
    expect(graphRecovery).toHaveTextContent("World history records this turn as failed.");
    expect(graphRecovery).toHaveTextContent("World history records this turn as failed.");
    expect(graphRecovery).not.toHaveTextContent("Exact V3 World history records this turn as failed.");
    expect(graphRecovery).toHaveTextContent("This World history turn failed; no final Graph-context completion was recorded.");
    expect(graphRecovery).toHaveTextContent("The provider returned a response; no final Graph-context completion was recorded.");
    expect(graphRecovery).toHaveTextContent("The saved turn is not automatically reposted; this view offers no retry.");
    expect(graphRecovery).not.toHaveTextContent("No final Graph-context completion has been recorded for this turn yet.");
    expect(graphRecovery).not.toHaveTextContent("Refresh World history before taking another action");
    expect(screen.queryByRole("button", { name: "Retry saved Ask" })).not.toBeInTheDocument();
    expect(localStorage.getItem(failedStorageKey)).toBe(failedBytes);
    expect(Object.keys(localStorage).some((key) => key.startsWith(
      `dmb:world-plan-pending-ask:v1:${encodeURIComponent(worldId)}:${encodeURIComponent(otherPlanId)}:`,
    ))).toBe(false);
    expect(postAsk).toHaveBeenCalledTimes(1);
  });

  it("preserves the explicit-new-attempt disposition alongside an exact failed V3 turn", async () => {
    const playableTarget = { kind: "scene" as const, id: "scene:opening" };
    const { api, mounted, postAsk, request } = await leavePendingGraphAsk(playableTarget);
    const storageKey = pendingAskKeys()[0]!;
    const originalBytes = localStorage.getItem(storageKey);
    mounted.unmount();

    const failedTurn = await failedV3HistoryTurn(request, {
      execution: {
        schema: "dmb_agent_plan_world_graph_execution_projection_v1",
        claimability: "explicit_new_attempt_required",
        authorization_state: "known_not_sent",
        automatic_redispatch: false,
      },
    });
    api.setCurrent(await historyV3("conversation-a", 10, [failedTurn]));
    render(conversationElement({ playableTarget, editBridge: {} }));

    expect(await screen.findByText("Buddy couldn’t finish this reply. Your Plan was not changed.")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Why this reply stopped"));
    const graphRecovery = await screen.findByRole("region", { name: "World Graph evidence and recovery" });
    expect(graphRecovery).toHaveTextContent("Exact V3 World history records this turn as failed.");
    expect(graphRecovery).toHaveTextContent("Execution disposition requires a separate new Ask for any new attempt.");
    expect(graphRecovery).toHaveTextContent("The saved turn is not automatically reposted; this view offers no retry.");
    expect(graphRecovery).not.toHaveTextContent("Refresh World history before taking another action");
    expect(screen.queryByRole("button", { name: "Retry saved Ask" })).not.toBeInTheDocument();
    expect(screen.getByText(`Graph Ask · ${request.turn_id} · failure confirmed`)).toBeInTheDocument();
    expect(localStorage.getItem(storageKey)).toBe(originalBytes);
    expect(pendingAskKeys()).toEqual([storageKey]);
    expect(postAsk).toHaveBeenCalledTimes(1);
  });

  it.each([
    ["none", "Execution disposition: provider dispatch did not begin.", false],
    ["known_not_sent", "Execution disposition: provider dispatch did not begin.", false],
    ["response_received", "Execution projection conflicts: claimability is safe to reclaim without dispatch while authorization state is provider response received.", true],
    ["sdk_entered", "Execution projection conflicts: claimability is safe to reclaim without dispatch while authorization state is provider call entered.", true],
  ] as const)("gates a safe-to-reclaim execution statement on %s authorization", async (authorizationState, expectedDisposition, isConflict) => {
    const playableTarget = { kind: "scene" as const, id: "scene:opening" };
    const { api, mounted, postAsk, request } = await leavePendingGraphAsk(playableTarget);
    const storageKey = pendingAskKeys()[0]!;
    const originalBytes = localStorage.getItem(storageKey);
    mounted.unmount();

    const failedTurn = await failedV3HistoryTurn(request, {
      execution: {
        schema: "dmb_agent_plan_world_graph_execution_projection_v1",
        claimability: "safe_to_reclaim_without_dispatch",
        authorization_state: authorizationState,
        automatic_redispatch: false,
      },
    });
    api.setCurrent(await historyV3("conversation-a", 10, [failedTurn]));
    render(conversationElement({ playableTarget, editBridge: {} }));

    expect(await screen.findByText(`Graph Ask · ${request.turn_id} · failure confirmed`)).toBeInTheDocument();
    openLatestTurnDetails();
    const graphRecovery = screen.getByRole("region", { name: "World Graph evidence and recovery" });
    expect(graphRecovery).toHaveTextContent(expectedDisposition);
    if (isConflict) expect(graphRecovery).not.toHaveTextContent("provider dispatch did not begin");
    expect(graphRecovery).toHaveTextContent("Exact V3 World history records this turn as failed.");
    expect(graphRecovery).toHaveTextContent("The saved turn is not automatically reposted; this view offers no retry.");
    expect(graphRecovery).not.toHaveTextContent("Refresh World history before taking another action");
    expect(screen.queryByRole("button", { name: "Retry saved Ask" })).not.toBeInTheDocument();
    expect(localStorage.getItem(storageKey)).toBe(originalBytes);
    expect(pendingAskKeys()).toEqual([storageKey]);
    expect(postAsk).toHaveBeenCalledTimes(1);

    const historyCallCount = api.historyCalls.length;
    fireEvent.click(screen.getByRole("button", { name: "Refresh World history" }));
    await waitFor(() => expect(api.historyCalls.length).toBeGreaterThan(historyCallCount));
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem(storageKey)).toBe(originalBytes);
    expect(pendingAskKeys()).toEqual([storageKey]);
  });

  it.each([
    "ambiguous",
    "target-mismatch",
    "conversation-mismatch",
    "surface-mismatch",
    "plan-basis-mismatch",
    "receipt-digest-mismatch",
    "completed-without-completion",
    "legacy-v2",
  ] as const)("leaves a failed Ask unclassified when history is %s", async (historyCase) => {
    const playableTarget = { kind: "scene" as const, id: "scene:opening" };
    const { api, mounted, postAsk, request } = await leavePendingGraphAsk(playableTarget);
    const storageKey = pendingAskKeys()[0]!;
    const originalBytes = localStorage.getItem(storageKey);
    mounted.unmount();

    let rowRequest = request;
    if (historyCase === "target-mismatch") {
      rowRequest = { ...request, playable_target: { schema: "dmb_plan_playable_target_v1", kind: "scene", id: "scene:ending" } };
    } else if (historyCase === "surface-mismatch") {
      rowRequest = { ...request, surface: { surface_id: "build", instance_id: "build-instance" } };
    } else if (historyCase === "plan-basis-mismatch") {
      rowRequest = {
        ...request,
        primary_work: {
          ...request.primary_work,
          expected_revision_n: request.primary_work.expected_revision_n + 1,
          expected_content_sha256: "b".repeat(64),
        },
      };
    }

    if (historyCase === "legacy-v2") {
      const context = await planGraphContext("plan_only_graph_unused", {
        request: rowRequest,
        completion: false,
        execution: {
          schema: "dmb_agent_plan_world_graph_execution_projection_v1",
          claimability: "blocked_unknown_or_sent",
          authorization_state: "response_received",
          automatic_redispatch: false,
        },
      });
      api.setCurrent(await historyV2("conversation-a", 10, [policyHistoryTurn(
        1, request.turn_id, request.message, null, context, "failed", rowRequest,
      )]));
    } else {
      const failedTurn = await failedV3HistoryTurn(request, {
        rowRequest,
        durableTurnId: "ce97be5a-18b5-4fb5-a820-8161716fe517",
        execution: historyCase === "completed-without-completion" ? {
          schema: "dmb_agent_plan_world_graph_execution_projection_v1",
          claimability: "completed",
          authorization_state: "response_received",
          automatic_redispatch: false,
        } : undefined,
      });
      if (historyCase === "receipt-digest-mismatch") {
        failedTurn.plan_context.receipt.context_receipt_sha256 = "f".repeat(64);
      }
      if (historyCase === "ambiguous") {
        const duplicate = { ...failedTurn, sequence: 2, turn_id: "ce97be5a-18b5-4fb5-a820-8161716fe518" };
        api.setCurrent(await historyV3("conversation-a", 10, [failedTurn, duplicate]));
      } else {
        const conversationId = historyCase === "conversation-mismatch" ? "conversation-b" : "conversation-a";
        const pointerRevision = historyCase === "conversation-mismatch" ? 11 : 10;
        api.setCurrent(await historyV3(conversationId, pointerRevision, [failedTurn]));
      }
    }

    render(conversationElement({ playableTarget, editBridge: {} }));
    expect(await screen.findByText("Needs attention · 1 outcome unconfirmed")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Needs attention"));
    if (historyCase !== "receipt-digest-mismatch") {
      openLatestTurnDetails();
      const graphRecovery = await screen.findByRole("region", { name: "World Graph evidence and recovery" });
      expect(graphRecovery).not.toHaveTextContent("Exact V3 World history records this turn as failed.");
      expect(graphRecovery).toHaveTextContent("This World history turn failed; no final Graph-context completion was recorded.");
      expect(graphRecovery).toHaveTextContent("World history records this turn as failed.");
      expect(graphRecovery).not.toHaveTextContent("Refresh World history before taking another action");
      if (historyCase === "completed-without-completion") {
        expect(graphRecovery).toHaveTextContent("Execution projection conflicts: claimability is completed while authorization state is provider response received.");
      }
    }
    expect(screen.queryByText(`Graph Ask · ${request.turn_id} · failure confirmed`)).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Needs attention"));
    fireEvent.click(screen.getByText(`Graph Ask · ${request.turn_id}`));
    expect(screen.getByText("Status · outcome not confirmed in exact V3 World history")).toBeInTheDocument();
    expect(localStorage.getItem(storageKey)).toBe(originalBytes);
    expect(pendingAskKeys()).toEqual([storageKey]);
    expect(postAsk).toHaveBeenCalledTimes(1);
  });

  it("refreshes World history without reposting or clearing an unmatched Graph Ask", async () => {
    const playableTarget = { kind: "scene" as const, id: "scene:opening" };
    const { api, mounted, postAsk } = await leavePendingGraphAsk(playableTarget);
    mounted.rerender(conversationElement({ playableTarget, selectionGeneration: 0, editBridge: {} }));
    const beforeRefresh = api.historyCalls.length;

    fireEvent.click(screen.getByRole("button", { name: "Refresh World history" }));

    await waitFor(() => expect(api.historyCalls.length).toBeGreaterThan(beforeRefresh));
    expect(api.historyCalls.at(-1)).toMatchObject({ includeTurnCorrelation: true });
    expect(pendingAskKeys()).toHaveLength(1);
    expect(postAsk).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByText("Needs attention"));
    const conversation = screen.getByRole("region", { name: "Saved World Plan conversation" });
    const body = conversation.querySelector(".world-plan-agent-conversation__body");
    const transcript = screen.getByRole("region", { name: "World conversation transcript" });
    const recovery = screen.getByRole("region", { name: "Pending Ask recovery" });
    const composer = screen.getByRole("region", { name: "Conversation composer" });
    expect(recovery).toHaveTextContent("Pending recovery · 1");
    expect(body).not.toBeNull();
    expect(body).toContainElement(transcript);
    expect(body).toContainElement(recovery);
    expect(body).not.toContainElement(composer);
    expect(composer?.parentElement).toBe(conversation);
    expect(composer).toContainElement(screen.getByRole("textbox", { name: "Message DungeonBuddy" }));
    expect(within(composer).queryByRole("radio")).not.toBeInTheDocument();
  });

  it("does not heuristically clear a text-matching v2 history row without persisted correlation", async () => {
    const cardA = { kind: "scene" as const, id: "scene:opening" };
    const { api, mounted, postAsk, request } = await leavePendingGraphAsk(cardA);
    const storageKey = pendingAskKeys()[0]!;
    mounted.unmount();
    const context = await planGraphContext("graph_grounded", { request, execution: null });
    const answer = "The western gate is watched.";
    // This deliberately resembles the legacy heuristic fields, including a coincident turn UUID.
    const matchingTextOnlyRow = policyHistoryTurn(
      1, request.turn_id, request.message, answer, context, "completed", request,
    );
    api.setCurrent(await historyV2("conversation-a", 10, [matchingTextOnlyRow]));

    render(conversationElement({ playableTarget: cardA }));

    await screen.findAllByText(answer);
    await waitFor(() => expect(pendingAskKeys()).toEqual([storageKey]));
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Refresh World history" })).toBeInTheDocument();
  });

  it("keeps a pending Graph Ask when more than one v3 row has its persisted key", async () => {
    const cardA = { kind: "scene" as const, id: "scene:opening" };
    const { api, mounted, postAsk, request } = await leavePendingGraphAsk(cardA);
    const storageKey = pendingAskKeys()[0]!;
    mounted.unmount();
    const context = await planGraphContext("graph_grounded", { request, execution: null });
    const answer = "The western gate is watched.";
    const correlationKey = await expectedHistoryCorrelationKey(worldId, request.turn_id);
    const first = withPersistedCorrelation(
      policyHistoryTurn(1, request.turn_id, request.message, answer, context, "completed", request),
      correlationKey,
      "00000000-0000-4000-8000-000000000093",
    );
    const duplicate = { ...first, sequence: 2, turn_id: "00000000-0000-4000-8000-000000000094" };
    api.setCurrent(await historyV3("conversation-a", 10, [first, duplicate]));

    render(conversationElement({ playableTarget: cardA }));

    await screen.findAllByText(answer);
    await waitFor(() => expect(pendingAskKeys()).toEqual([storageKey]));
    expect(postAsk).toHaveBeenCalledTimes(1);
  });

  it.each(["target-mismatch", "conversation-mismatch", "unfinished", "execution-not-completed", "ambiguous", "replacement-bytes"] as const)(
    "keeps the Graph Ask pending when history is %s",
    async (historyCase) => {
      const cardA = { kind: "scene" as const, id: "scene:opening" };
      const cardB = { kind: "scene" as const, id: "scene:ending" };
      const { api, mounted, postAsk, request } = await leavePendingGraphAsk(cardA);
      const storageKey = pendingAskKeys()[0]!;
      const originalEnvelope = localStorage.getItem(storageKey);
      mounted.unmount();
      let expectedEnvelope = originalEnvelope;
      if (historyCase === "replacement-bytes") {
        const replacement = JSON.parse(originalEnvelope ?? "{}") as { createdAt?: string };
        replacement.createdAt = "replacement-after-history-read";
        expectedEnvelope = JSON.stringify(replacement);
        const originalGetItem = Storage.prototype.getItem;
        let matchingReads = 0;
        vi.spyOn(Storage.prototype, "getItem").mockImplementation(function (this: Storage, key: string) {
          if (key === storageKey && ++matchingReads === 3) {
            this.setItem(key, expectedEnvelope!);
            return expectedEnvelope!;
          }
          return originalGetItem.call(this, key);
        });
      }

      let receiptRequest = request;
      let context: WorldPlanAgentPlanContextV1;
      let lifecycle: WorldAgentConversationHistoryTurnV2["lifecycle_status"] = "completed";
      let answer: string | null = "The western gate is watched.";
      if (historyCase === "target-mismatch") {
        receiptRequest = {
          ...request,
          playable_target: { schema: "dmb_plan_playable_target_v1", ...cardB },
        };
        context = await planGraphContext("graph_grounded", { request: receiptRequest, execution: null });
      } else if (historyCase === "conversation-mismatch") {
        context = await planGraphContext("graph_grounded", { request, execution: null });
      } else if (historyCase === "unfinished") {
        lifecycle = "running";
        answer = null;
        context = await planGraphContext("graph_grounded", { request, completion: false, execution: null });
      } else if (historyCase === "execution-not-completed") {
        context = await planGraphContext("graph_grounded", {
          request,
          execution: {
            schema: "dmb_agent_plan_world_graph_execution_projection_v1",
            claimability: "blocked_unknown_or_sent",
            authorization_state: "outcome_unknown",
            automatic_redispatch: false,
          },
        });
      } else {
        context = await planGraphContext("graph_grounded", { request, execution: null });
      }

      const correlationKey = await expectedHistoryCorrelationKey(worldId, request.turn_id);
      const completedTurn = withPersistedCorrelation(policyHistoryTurn(
        1, request.turn_id, request.message, answer, context, lifecycle, receiptRequest,
      ), correlationKey, "00000000-0000-4000-8000-000000000095");
      const turns = historyCase === "ambiguous"
        ? [completedTurn, { ...completedTurn, sequence: 2, turn_id: "00000000-0000-4000-8000-000000000096" }]
        : [completedTurn];
      const conversationId = historyCase === "conversation-mismatch" ? "conversation-b" : "conversation-a";
      const pointerRevision = historyCase === "conversation-mismatch" ? 11 : 10;
      api.setCurrent(await historyV3(conversationId, pointerRevision, turns));

      render(conversationElement({ playableTarget: cardB, selectionGeneration: 1 }));

      if (historyCase === "ambiguous") {
        expect(await screen.findAllByText(answer!)).toHaveLength(4);
      } else if (historyCase === "unfinished") {
        expect(await screen.findByText("No final Graph-context completion has been recorded for this turn yet.")).toBeInTheDocument();
      } else {
        expect(await screen.findAllByText(answer!)).toHaveLength(2);
      }
      await waitFor(() => expect(pendingAskKeys()).toEqual([storageKey]));
      expect(localStorage.getItem(storageKey)).toBe(expectedEnvelope);
      fireEvent.click(screen.getByText("Needs attention"));
      expect(screen.getByRole("region", { name: "Pending Ask recovery" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Retry saved Ask" })).not.toBeInTheDocument();
      expect(postAsk).toHaveBeenCalledTimes(1);
    },
  );

  it("directs an authorization-rejected Graph Ask to refresh history before another action", async () => {
    setupApi(history("conversation-a", 4, []));
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockRejectedValue(new liveApi.LiveApiError("Unauthorized", 401));
    render(conversationElement());
    await screen.findByText(/No messages yet/i);
    ensureWorldGraphAskEnabled();
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Check the north gate." } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText(/Reconnect in Settings, then refresh World history before taking another action/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry saved Ask" })).not.toBeInTheDocument();
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(pendingAskKeys()).toHaveLength(1);
  });

  it("keeps an explicitly Plan-only Ask on the byte-compatible v1 request shape", async () => {
    const api = setupApi(history("conversation-a", 4, []));
    let captured: WorldPlanAgentTurnRequestV1 | null = null;
    vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      captured = request;
      api.setCurrent(history("conversation-a", 5, [historyTurnForAsk(request, "A saved-Plan answer.")]));
      return agentResponse(request, "conversation-a", "A saved-Plan answer.") as any;
    });
    render(conversationElement());
    await screen.findByText(/No messages yet/i);
    ensureWorldGraphAskDisabled();
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Ask without Graph context" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    expect(await screen.findByText("A saved-Plan answer.")).toBeInTheDocument();
    expect(captured?.schema).toBe("dmb_agent_turn_request_v1");
    expect(captured).not.toHaveProperty("plan_context_policy");
    expect(Object.keys(captured ?? {}).sort()).toEqual([
      "client_thread_id", "client_work_state", "graph_request", "graph_selection", "message", "owner_scope",
      "primary_work", "schema", "surface", "turn_id",
    ]);
  });

  it("renders the immutable target, grammar, and exact WorkRevision from history", async () => {
    const turn = makeTurn(1, "target-turn", "What happens at arrival?", "The arrival is guarded.");
    turn.provenance.primary_work = {
      ...turn.provenance.primary_work,
      revision: "7",
      content_sha256: contentSha256,
      object_revision: 7,
      work_revision_id: workRevisionId,
      revision_n: 4,
    };
    turn.provenance.supporting_work = [{
      resolution: "resolved",
      kind: "dmb_plan_playable_target_v1",
      object_id: "scene:arrival",
      revision: "v1",
      content_sha256: null,
      object_revision: null,
      work_revision_id: null,
      revision_n: null,
    }];
    setupApi(history("conversation-a", 1, [turn]));

    mountComponent();

    expect(await screen.findByText(/Playable target: scene scene:arrival · marker grammar v1 · committed Plan saved-plan-test, object revision 7/)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`WorkRevision ${workRevisionId}, revision 4, SHA-256 ${contentSha256}`))).toBeInTheDocument();
  });

  it("settles a successful late Ask as history for its original card after selection changes", async () => {
    const api = setupApi(history("conversation-a", 10, []));
    const response = deferred<ReturnType<typeof agentResponse>>();
    const sent: WorldPlanAgentTurnRequestV1[] = [];
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      sent.push(request);
      return response.promise as any;
    });
    const cardA = { kind: "scene" as const, id: "scene:opening" };
    const cardB = { kind: "scene" as const, id: "scene:ending" };
    const mounted = render(conversationElement({ playableTarget: cardA, selectionGeneration: 0 }));

    await screen.findByText(/No messages yet/i);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "What happens at the opening?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(postAsk).toHaveBeenCalledTimes(1));
    const originalRequest = sent[0]!;
    expect(originalRequest).toMatchObject({
      message: "What happens at the opening?",
      playable_target: { schema: "dmb_plan_playable_target_v1", ...cardA },
      primary_work: {
        object_id: documentId,
        expected_revision: 7,
        expected_content_sha256: contentSha256,
      },
    });
    expect(pendingAskKeys()).toHaveLength(1);

    mounted.rerender(conversationElement({ playableTarget: cardB, selectionGeneration: 1 }));
    const selectedCardForB = screen.getByRole("group", { name: "Selected Playable card for Ask" });
    const selectedCardForBBeforeSettlement = selectedCardForB.textContent;

    const answer = "The opening is guarded by two sentries.";
    const acceptedTurn = historyTurnForAsk(originalRequest, answer);
    await act(async () => {
      api.setCurrent(history("conversation-a", 11, [acceptedTurn]));
      response.resolve(agentResponse(originalRequest, "conversation-a", answer));
      await response.promise;
    });

    expect(await screen.findByText(answer)).toBeInTheDocument();
    expect(await screen.findByText(/original selected card scene:opening at committed Plan object revision 7/)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`Playable target: scene scene:opening · marker grammar v1 · committed Plan ${documentId}, object revision 7, WorkRevision ${workRevisionId}, revision 1, SHA-256 ${contentSha256}`))).toBeInTheDocument();
    expect(selectedCardForB.textContent).toBe(selectedCardForBBeforeSettlement);
    expect(screen.getByRole("region", { name: "World conversation transcript" }).querySelector("article"))
      .toHaveTextContent("scene:opening");
    expect(screen.getByRole("region", { name: "World conversation transcript" }).querySelector("article"))
      .not.toHaveTextContent("scene:ending");
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(sent).toEqual([originalRequest]);
    expect(pendingAskKeys()).toHaveLength(0);

    mounted.unmount();
    render(conversationElement({ playableTarget: cardA, selectionGeneration: 2 }));
    expect(await screen.findByText(answer)).toBeInTheDocument();
    expect(screen.getByText(/Playable target: scene scene:opening · marker grammar v1/)).toBeInTheDocument();
  });

  it("settles an accepted Ask across SPA unmount and remount", async () => {
    const api = setupApi(history("conversation-a", 10, []));
    const response = deferred<ReturnType<typeof agentResponse>>();
    const sent: WorldPlanAgentTurnRequestV1[] = [];
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      sent.push(request);
      return response.promise as any;
    });
    const mounted = render(conversationElement());

    await screen.findByText(/No messages yet/i);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "What is the saved Plan's opening?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(postAsk).toHaveBeenCalledTimes(1));

    const originalRequest = sent[0]!;
    const storageKey = pendingAskKeys()[0]!;
    const originalBytes = localStorage.getItem(storageKey)!;
    expect(originalBytes).toContain(originalRequest.turn_id);

    mounted.unmount();
    render(conversationElement());
    await screen.findByRole("button", { name: "Retry saved Ask" });
    expect(pendingAskKeys()).toEqual([storageKey]);
    expect(postAsk).toHaveBeenCalledTimes(1);

    const historyCallsBeforeSettlement = api.historyCalls.length;
    const canonicalConversationId = "00000000-0000-4000-8000-000000000222";
    const answer = "The saved Plan opens at the north gate.";
    const acceptedTurn = historyTurnForAsk(originalRequest, answer);
    const clearEvents = capturePendingAskEvents(pendingAskClearedEventName);
    const acceptedEvents = capturePendingAskEvents(pendingAskAcceptedEventName);

    await act(async () => {
      api.setCurrent(history(canonicalConversationId, 11, [acceptedTurn]));
      response.resolve(agentResponse(originalRequest, canonicalConversationId, answer));
      await response.promise;
    });

    expect(originalRequest.turn_id).not.toBe(canonicalConversationId);
    expect(await screen.findByText(answer)).toBeInTheDocument();
    expect(api.historyCalls).toHaveLength(historyCallsBeforeSettlement + 1);
    expect(pendingAskKeys()).toEqual([]);
    expect(localStorage.getItem(storageKey)).toBeNull();
    expect(screen.queryByRole("button", { name: "Retry saved Ask" })).not.toBeInTheDocument();
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(sent).toEqual([originalRequest]);
    expect(screen.getByRole("region", { name: "World conversation transcript" }).querySelector("article"))
      .toHaveTextContent(answer);

    expect(clearEvents).toHaveLength(1);
    expect(acceptedEvents).toHaveLength(0);
    const detail = clearEvents[0]!.detail as Record<string, unknown>;
    expect(Object.keys(detail).sort()).toEqual(["key", "origin", "version"]);
    expect(detail).toEqual({
      version: 1,
      key: storageKey,
      origin: {
        worldId,
        documentId,
        objectRevision: 7,
        workRevisionId,
        revisionN: 1,
        contentSha256,
      },
    });
    expect(JSON.stringify(detail)).not.toContain(answer);
    expect(JSON.stringify(detail)).not.toContain(originalRequest.message);
  });

  it("ignores pending Ask cleared events for another scope or with malformed origin", async () => {
    const api = setupApi(history("conversation-a", 10, []));
    render(conversationElement());

    await screen.findByText(/No messages yet/i);
    const initialHistoryCalls = api.historyCalls.length;
    const otherWorldId = "another-world";
    const otherScopeKey = "dmb:world-plan-pending-ask:v1:"
      + encodeURIComponent(otherWorldId) + ":" + encodeURIComponent(documentId) + ":test";
    const malformedOriginKey = "dmb:world-plan-pending-ask:v1:"
      + encodeURIComponent(worldId) + ":" + encodeURIComponent(documentId) + ":test";

    await act(async () => {
      window.dispatchEvent(new CustomEvent(pendingAskClearedEventName, {
        detail: {
          version: 1,
          key: otherScopeKey,
          origin: {
            worldId: otherWorldId,
            documentId,
            objectRevision: 7,
            workRevisionId,
            revisionN: 1,
            contentSha256,
          },
        },
      }));
      window.dispatchEvent(new CustomEvent(pendingAskClearedEventName, {
        detail: {
          version: 1,
          key: malformedOriginKey,
          origin: {
            worldId,
            documentId,
            objectRevision: 7,
            workRevisionId,
            revisionN: 1,
            contentSha256,
            unexpected: "must be ignored",
          },
        },
      }));
    });

    expect(api.historyCalls).toHaveLength(initialHistoryCalls);
    expect(pendingAskKeys()).toEqual([]);
  });

  it("preserves replacement recovery bytes when a captured Ask succeeds after unmount", async () => {
    const api = setupApi(history("conversation-a", 10, []));
    const response = deferred<ReturnType<typeof agentResponse>>();
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async () => {
      return response.promise as any;
    });
    const mounted = render(conversationElement());

    await screen.findByText(/No messages yet/i);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "Original captured request" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(postAsk).toHaveBeenCalledTimes(1));

    const originalRequest = postAsk.mock.calls[0]![0];
    const storageKey = pendingAskKeys()[0]!;
    const originalBytes = localStorage.getItem(storageKey)!;
    const replacement = JSON.parse(originalBytes);
    replacement.request.message = "Replacement recovery must remain";
    const replacementBytes = JSON.stringify(replacement);
    localStorage.setItem(storageKey, replacementBytes);

    mounted.unmount();
    render(conversationElement());
    await screen.findByRole("button", { name: "Retry saved Ask" });
    const clearEvents = capturePendingAskEvents(pendingAskClearedEventName);
    const acceptedEvents = capturePendingAskEvents(pendingAskAcceptedEventName);
    const canonicalConversationId = "00000000-0000-4000-8000-000000000223";
    const answer = "The original request completed on the server.";
    const historyCallsBeforeSettlement = api.historyCalls.length;

    await act(async () => {
      api.setCurrent(history(canonicalConversationId, 11, [
        historyTurnForAsk(originalRequest, answer),
      ]));
      response.resolve(agentResponse(originalRequest, canonicalConversationId, answer));
      await response.promise;
    });

    expect(localStorage.getItem(storageKey)).toBe(replacementBytes);
    expect(pendingAskKeys()).toEqual([storageKey]);
    expect(screen.getByRole("button", { name: "Retry saved Ask" })).toBeInTheDocument();
    expect(await screen.findByText(answer)).toBeInTheDocument();
    expect(api.historyCalls).toHaveLength(historyCallsBeforeSettlement + 1);
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(clearEvents).toHaveLength(0);
    expect(acceptedEvents).toHaveLength(1);
    const detail = acceptedEvents[0]!.detail as Record<string, unknown>;
    expect(Object.keys(detail).sort()).toEqual(["key", "origin", "version"]);
    expect(JSON.stringify(detail)).not.toContain(answer);
  });

  it.each(["network rejection", "malformed response"])(
    "keeps exact recovery after an unmounted %s and explicit retry",
    async (firstOutcome) => {
      const api = setupApi(history("conversation-a", 10, []));
      const firstResponse = deferred<unknown>();
      const requests: WorldPlanAgentTurnRequestV1[] = [];
      const canonicalConversationId = "00000000-0000-4000-8000-000000000224";
      const answer = "The exact recovered Plan answer.";
      const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
        requests.push(request);
        if (requests.length === 1) return firstResponse.promise as any;
        api.setCurrent(history(canonicalConversationId, 11, [
          historyTurnForAsk(request, answer),
        ]));
        return agentResponse(request, canonicalConversationId, answer) as any;
      });
      const mounted = render(conversationElement());

      await screen.findByText(/No messages yet/i);
      fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
        target: { value: "Keep this exact request recoverable" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Send message" }));
      await waitFor(() => expect(postAsk).toHaveBeenCalledTimes(1));

      const storageKey = pendingAskKeys()[0]!;
      const originalBytes = localStorage.getItem(storageKey)!;
      const originalRequest = requests[0]!;
      mounted.unmount();
      render(conversationElement());
      await screen.findByRole("button", { name: "Retry saved Ask" });
      const clearEvents = capturePendingAskEvents(pendingAskClearedEventName);
      const acceptedEvents = capturePendingAskEvents(pendingAskAcceptedEventName);

      await act(async () => {
        if (firstOutcome === "network rejection") {
          firstResponse.reject(new Error("connection lost"));
          await firstResponse.promise.catch(() => undefined);
        } else {
          firstResponse.resolve({});
          await firstResponse.promise;
        }
      });

      expect(localStorage.getItem(storageKey)).toBe(originalBytes);
      expect(pendingAskKeys()).toEqual([storageKey]);
      expect(postAsk).toHaveBeenCalledTimes(1);
      expect(clearEvents).toHaveLength(0);
      expect(acceptedEvents).toHaveLength(0);
      expect(screen.getByRole("button", { name: "Retry saved Ask" })).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: "Retry saved Ask" }));
      expect(await screen.findByText(answer)).toBeInTheDocument();
      expect(postAsk).toHaveBeenCalledTimes(2);
      expect(requests[1]).toEqual(originalRequest);
      expect(pendingAskKeys()).toEqual([]);
      expect(localStorage.getItem(storageKey)).toBeNull();
      expect(clearEvents).toHaveLength(1);
      expect(acceptedEvents).toHaveLength(0);
    },
  );

  it("keeps a late same-card Ask attributed to its old committed basis after the basis changes", async () => {
    const api = setupApi(history("conversation-a", 10, []));
    const response = deferred<ReturnType<typeof agentResponse>>();
    const sent: WorldPlanAgentTurnRequestV1[] = [];
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      sent.push(request);
      return response.promise as any;
    });
    const sameCard = { kind: "scene" as const, id: "scene:arrival" };
    const mounted = render(conversationElement({ playableTarget: sameCard, selectionGeneration: 0 }));

    await screen.findByText(/No messages yet/i);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "What changes at arrival?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(postAsk).toHaveBeenCalledTimes(1));
    const originalRequest = sent[0]!;
    const newDigest = "b".repeat(64);

    mounted.rerender(conversationElement({
      revision: 8,
      playableTarget: sameCard,
      playableTargetBasis: { revision: 8, contentSha256: newDigest },
      selectionGeneration: 1,
      draftGeneration: 1,
      savedDirty: true,
    }));
    const selectedCardAfterBasisChange = screen.getByRole("group", { name: "Selected Playable card for Ask" });
    expect(selectedCardAfterBasisChange).toHaveTextContent("Question · scene:arrival");
    fireEvent.click(screen.getByText("Advanced details"));
    const askTargetDetails = screen.getByRole("region", { name: "Ask target details" });
    expect(await within(askTargetDetails).findByText(/Card basis · object revision 8/)).toBeInTheDocument();
    expect(askTargetDetails).toHaveTextContent(newDigest);

    const answer = "The arrival now has a verified historical answer.";
    const acceptedTurn = historyTurnForAsk(originalRequest, answer);
    await act(async () => {
      api.setCurrent(history("conversation-a", 11, [acceptedTurn]));
      response.resolve(agentResponse(originalRequest, "conversation-a", answer));
      await response.promise;
    });

    expect(await screen.findByText(answer)).toBeInTheDocument();
    expect(await screen.findByText(/original selected card scene:arrival at committed Plan object revision 7/)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`Playable target: scene scene:arrival · marker grammar v1 · committed Plan ${documentId}, object revision 7, WorkRevision ${workRevisionId}, revision 1, SHA-256 ${contentSha256}`))).toBeInTheDocument();
    expect(selectedCardAfterBasisChange).toHaveTextContent("Question · scene:arrival");
    expect(selectedCardAfterBasisChange).not.toHaveTextContent(contentSha256);
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(sent[0]).toEqual(originalRequest);
    expect(originalRequest.primary_work.expected_revision).toBe(7);
    expect(originalRequest.primary_work.expected_content_sha256).toBe(contentSha256);
  });

  it("keeps a late Ask with a malformed target receipt generic after selection changes and reopen", async () => {
    const api = setupApi(history("conversation-a", 10, []));
    const response = deferred<ReturnType<typeof agentResponse>>();
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async () => {
      return response.promise as any;
    });
    const cardA = { kind: "scene" as const, id: "scene:opening" };
    const cardB = { kind: "scene" as const, id: "scene:ending" };
    const mounted = render(conversationElement({ playableTarget: cardA, selectionGeneration: 0 }));

    await screen.findByText(/No messages yet/i);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "What happens at the opening?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(postAsk).toHaveBeenCalledTimes(1));
    const originalRequest = postAsk.mock.calls[0]![0];
    const acceptedTurn = historyTurnForAsk(originalRequest, "The opening has a safe generic historical answer.");
    acceptedTurn.provenance.supporting_work = [{
      resolution: "resolved",
      kind: "dmb_plan_playable_target_v1",
      object_id: "scene:invalid/id",
      revision: "v1",
      content_sha256: null,
      object_revision: null,
      work_revision_id: null,
      revision_n: null,
    }];

    mounted.rerender(conversationElement({ playableTarget: cardB, selectionGeneration: 1 }));
    await act(async () => {
      api.setCurrent(history("conversation-a", 11, [acceptedTurn]));
      response.resolve(agentResponse(originalRequest, "conversation-a", "The opening has a safe generic historical answer."));
      await response.promise;
    });

    const answer = "The opening has a safe generic historical answer.";
    expect(await screen.findByText(answer)).toBeInTheDocument();
    const transcript = screen.getByRole("region", { name: "World conversation transcript" });
    const row = transcript.querySelector("article")!;
    expect(within(row).getByRole("alert")).toHaveTextContent("Target receipt unavailable");
    expect(row).not.toHaveTextContent("Playable target:");
    expect(row).not.toHaveTextContent(cardA.id);
    expect(row).not.toHaveTextContent(cardB.id);

    mounted.unmount();
    render(conversationElement({ playableTarget: cardA, selectionGeneration: 2 }));
    expect(await screen.findByText(answer)).toBeInTheDocument();
    const reopenedTranscript = screen.getByRole("region", { name: "World conversation transcript" });
    const reopenedRow = reopenedTranscript.querySelector("article")!;
    expect(within(reopenedRow).getByRole("alert")).toHaveTextContent("Target receipt unavailable");
    expect(reopenedRow).not.toHaveTextContent("Playable target:");
    expect(reopenedRow).not.toHaveTextContent(cardA.id);
  });

  it("blocks a stale targeted Ask before browser persistence or API dispatch", async () => {
    setupApi(history("conversation-a", 1, []));
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn");

    mountComponent(7, null, { kind: "scene", id: "scene:arrival" }, true);
    await screen.findByText(/No messages yet/i);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "Ask about the deleted card." },
    });
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
    fireEvent.submit(screen.getByLabelText("Message DungeonBuddy").closest("form")!);

    expect(postAsk).not.toHaveBeenCalled();
    expect(pendingAskKeys()).toHaveLength(0);
  });

  it("loads the latest page, merges older turns by durable ID, and preserves server ordering", async () => {
    const api = setupApi(history("conversation-a", 5, [
      makeTurn(2, "turn-2", "Middle question", "Middle answer"),
      makeTurn(3, "turn-3", "Newest question", "Newest answer", "build"),
    ], 2));
    api.setOlder(history("conversation-a", 5, [
      makeTurn(1, "turn-1", "Oldest question", "Oldest answer"),
      makeTurn(2, "turn-2", "Middle question", "Middle answer"),
    ]));

    mountComponent();
    expect(await screen.findByText("Newest question")).toBeInTheDocument();
    const earlier = screen.getByText(/Earlier conversation/).closest("details")!;
    fireEvent.click(earlier.querySelector("summary")!);
    expect(screen.getByText(/Historical surface: build/)).toBeInTheDocument();

    fireEvent.click(within(earlier).getByRole("button", { name: "Load earlier messages" }));
    expect(await screen.findByText("Oldest question")).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText("Middle question")).toHaveLength(1));
    expect(api.historyCalls).toEqual([
      { limit: 50, includeTurnCorrelation: true },
      { limit: 50, beforeSequence: 2, includeTurnCorrelation: true },
    ]);
    const transcript = screen.getByRole("region", { name: "World conversation transcript" });
    const renderedTurns = Array.from(transcript.querySelectorAll("article"))
      .map((article) => article.getAttribute("data-sequence"));
    expect(renderedTurns).toEqual(["1", "2", "3"]);
  });

  it("keeps the newer v2 receipt and execution sidecar when an older page repeats the same turn", async () => {
    const latestContext = await planGraphContext("graph_grounded", {
      execution: {
        schema: "dmb_agent_plan_world_graph_execution_projection_v1",
        claimability: "completed", authorization_state: "response_received", automatic_redispatch: false,
      },
    });
    const staleContext = await planGraphContext("plan_only_insufficient_evidence", {
      execution: {
        schema: "dmb_agent_plan_world_graph_execution_projection_v1",
        claimability: "safe_to_reclaim_without_dispatch", authorization_state: "none", automatic_redispatch: false,
      },
    });
    const latestTurn = policyHistoryTurn(2, "shared-policy-turn", "Was the gate watched?", "The western gate is watched.", latestContext);
    const staleDuplicate: WorldAgentConversationHistoryTurnV2 = {
      ...latestTurn,
      plan_context: staleContext,
    };
    const api = setupApi(await historyV2("conversation-a", 5, [latestTurn], 2));
    api.setOlder(await historyV2("conversation-a", 5, [
      makeTurn(1, "legacy-before-policy", "What is the opening?", "A saved-plan opening."),
      staleDuplicate,
    ]));

    render(conversationElement());
    expect(await screen.findByText("Grounded in World Graph evidence.")).toBeInTheDocument();
    const earlier = screen.getByText(/Earlier conversation/).closest("details")!;
    fireEvent.click(earlier.querySelector("summary")!);
    fireEvent.click(within(earlier).getByRole("button", { name: "Load earlier messages" }));
    expect(await screen.findByText("A saved-plan opening.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText("The western gate is watched.")).toHaveLength(2));
    expect(screen.getByText("Grounded in World Graph evidence.")).toBeInTheDocument();
    expect(screen.queryByText(/No sufficient World Graph evidence was available/)).not.toBeInTheDocument();
    const transcript = screen.getByRole("region", { name: "World conversation transcript" });
    expect(transcript.querySelectorAll('[data-sequence="2"]')).toHaveLength(1);
  });

  it("unlocks older paging after navigation invalidates a pending page and discards its stale response", async () => {
    const oldLatest = history("conversation-a", 5, [
      makeTurn(3, "turn-3", "Current A turn", "A answer"),
    ], 3);
    const movedPointer = history("conversation-b", 6, [
      makeTurn(2, "turn-b2", "Fresh B turn", "Fresh answer"),
    ], 2);
    const api = setupApi(oldLatest);
    let releaseStalePage!: (value: WorldAgentConversationHistoryResponseV1) => void;
    const stalePage = new Promise<WorldAgentConversationHistoryResponseV1>((resolve) => { releaseStalePage = resolve; });
    api.setOlderHandler(() => stalePage);
    vi.spyOn(liveApi, "postWorldAgentNewConversation").mockImplementation(async (_world, request) => {
      api.setCurrent(movedPointer);
      return {
        schema: "dmb_agent_new_conversation_response_v1",
        world_id: worldId,
        conversation_id: "conversation-b",
        active_conversation_id: "conversation-b",
        pointer_revision: request.expected_pointer_revision + 1,
      } as any;
    });

    mountComponent();
    expect(await screen.findByText("Current A turn")).toBeInTheDocument();
    const earlier = screen.getByText(/Earlier conversation/).closest("details")!;
    fireEvent.click(earlier.querySelector("summary")!);
    fireEvent.click(within(earlier).getByRole("button", { name: "Load earlier messages" }));
    await waitFor(() => expect(api.historyCalls.some((call) => call.beforeSequence === 3)).toBe(true));

    fireEvent.click(screen.getByRole("button", { name: "New conversation" }));
    expect(await screen.findByText("Fresh B turn")).toBeInTheDocument();
    expect(api.historyCalls).toContainEqual({ limit: 50, includeTurnCorrelation: true });

    await act(async () => {
      releaseStalePage(history("conversation-a", 5, [
        makeTurn(1, "stale-a-page", "Stale older page", "Must be discarded"),
      ], null));
    });
    expect(screen.queryByText("Stale older page")).not.toBeInTheDocument();
    const earlierAfterNavigation = screen.getByText(/Earlier conversation/).closest("details")!;
    fireEvent.click(earlierAfterNavigation.querySelector("summary")!);
    const olderButton = within(earlierAfterNavigation).getByRole("button", { name: "Load earlier messages" });
    await waitFor(() => expect(olderButton).toBeEnabled());

    api.setOlderHandler(async () => history("conversation-b", 6, [
      makeTurn(1, "turn-b1", "Fresh older B turn", "Older B answer"),
    ], null));
    fireEvent.click(olderButton);
    expect(await screen.findByText("Fresh older B turn")).toBeInTheDocument();
    expect(api.historyCalls).toContainEqual({ limit: 50, beforeSequence: 2, includeTurnCorrelation: true });
  });

  it("replays the exact Ask receipt across Plan and conversation changes without injecting it into the active transcript", async () => {
    const api = setupApi(history("conversation-a", 4, []));
    const thread = legacyThread();
    const localKey = threadStorageKey(namespace, legacyThreadId);
    const legacyBytes = JSON.stringify(thread);
    localStorage.setItem(localKey, legacyBytes);
    harness.agent.activeThread = thread;

    const createObjectUrl = vi.fn(() => "blob:legacy-export");
    const revokeObjectUrl = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    const oldCreate = Object.getOwnPropertyDescriptor(URL, "createObjectURL");
    const oldRevoke = Object.getOwnPropertyDescriptor(URL, "revokeObjectURL");
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectUrl });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectUrl });

    const sent: WorldPlanAgentTurnRequestV1[] = [];
    let replayReceipt: ReturnType<typeof durableReplayResponse> | null = null;
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      expect(pendingAskKeys()).toHaveLength(1);
      sent.push(request);
      if (sent.length === 1) {
        replayReceipt = durableReplayResponse(request, "conversation-b", "Recovered answer");
        api.setCurrent(history("conversation-c", 6, [
          makeTurn(1, "turn-c1", "Current C question", "Current C answer"),
        ]));
        throw new Error("connection reset after dispatch");
      }
      return replayReceipt as any;
    });

    const first = mountComponent();
    fireEvent.click(screen.getByText("Advanced details"));
    expect(await screen.findByRole("region", { name: "Local-only legacy Plan history" })).toBeInTheDocument();
    expect(screen.getByText("Legacy only fact")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Export local history JSON" }));
    expect(createObjectUrl).toHaveBeenCalledWith(expect.objectContaining({ type: "application/json" }));
    expect(revokeObjectUrl).toHaveBeenCalledWith("blob:legacy-export");
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "What is the plan?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    expect(await screen.findByText(/Ask outcome is uncertain/)).toBeInTheDocument();

    const storedKey = pendingAskKeys()[0]!;
    const storedRaw = localStorage.getItem(storedKey)!;
    const storedEnvelope = JSON.parse(storedRaw);
    expect(storedEnvelope.request).toEqual(sent[0]);
    expect(storedEnvelope.origin).toMatchObject({
      worldId,
      documentId,
      objectRevision: 7,
      workRevisionId,
      revisionN: 1,
      contentSha256,
      pointerRevision: 4,
      conversationId: "conversation-a",
    });
    expect(storedEnvelope.request).not.toHaveProperty("work_revision_id");
    expect(JSON.stringify(storedEnvelope.request)).not.toContain(workRevisionId);
    expect(localStorage.getItem(localKey)).toBe(legacyBytes);
    expect(harness.agent.updateThread).not.toHaveBeenCalled();

    first.unmount();
    api.setPlanBasis({
      ...committedRevision(),
      object_revision: 8,
      work_revision_id: "00000000-0000-4000-8000-000000000012",
      revision_n: 2,
      content_sha256: "b".repeat(64),
      markdown: "# Changed Plan",
    });
    harness.host = document.createElement("div");
    document.body.appendChild(harness.host);
    mountComponent(8);
    fireEvent.click(await screen.findByRole("button", { name: "Retry saved Ask" }));
    await waitFor(() => expect(postAsk).toHaveBeenCalledTimes(2));
    expect(sent[1]).toEqual(sent[0]);
    expect(replayReceipt?.conversation.conversation_id).toBe("conversation-b");
    expect(replayReceipt?.answer.trace.model_calls).toEqual([]);
    expect(replayReceipt?.answer.trace.conversation_context).toBe("durable_replay");
    // Header verification on both mounts plus the exact replay basis check.
    expect(api.getPlanBasis).toHaveBeenCalledTimes(3);
    expect(pendingAskKeys()).toHaveLength(0);
    expect(await screen.findByText(/confirmed this Ask under conversation conversation-b\. It was not inserted into the currently active conversation/)).toBeInTheDocument();
    expect(await screen.findByText("Current C question")).toBeInTheDocument();
    expect(screen.getByText("Current C answer")).toBeInTheDocument();
    expect(screen.queryByText("Recovered answer")).not.toBeInTheDocument();
    expect(localStorage.getItem(localKey)).toBe(legacyBytes);
    expect(harness.agent.updateThread).not.toHaveBeenCalled();

    if (oldCreate) Object.defineProperty(URL, "createObjectURL", oldCreate);
    else delete (URL as any).createObjectURL;
    if (oldRevoke) Object.defineProperty(URL, "revokeObjectURL", oldRevoke);
    else delete (URL as any).revokeObjectURL;
  });

  it("does not dispatch Ask when browser storage cannot save the exact recovery envelope", async () => {
    setupApi(history("conversation-a", 4, []));
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn");
    const originalSetItem = Storage.prototype.setItem;
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(function (key, value) {
      if (key.startsWith("dmb:world-plan-pending-ask:v1:")) throw new Error("quota exceeded");
      return originalSetItem.call(this, key, value);
    });

    mountComponent();
    await screen.findByText(/No messages yet/i);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Do not lose this request" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText(/Ask was not sent because its recovery envelope could not be saved/)).toBeInTheDocument();
    expect(postAsk).not.toHaveBeenCalled();
  });

  it("uses one message field for discussion and inline Plan proposals", async () => {
    const api = setupApi(history("conversation-a", 4, []));
    const askRequests: WorldPlanAgentTurnRequestV1[] = [];
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      askRequests.push(request);
      const answer = askRequests.length === 1
        ? "The saved Plan currently has one opening scene."
        : "The saved Plan discussion continues after the proposals.";
      const currentTurn = makeTurn(
        askRequests.length,
        request.turn_id,
        request.message,
        answer,
      );
      if (askRequests.length === 2) {
        api.setOlder(history("conversation-a", 6, [
          makeTurn(1, askRequests[0]!.turn_id, askRequests[0]!.message, "The saved Plan currently has one opening scene."),
        ]));
      }
      api.setCurrent(history(
        "conversation-a",
        4 + askRequests.length,
        [currentTurn],
        askRequests.length === 1 ? null : 2,
      ));
      return agentResponse(request, "conversation-a", answer) as any;
    });
    let proposalCount = 0;
    const proposalRequest = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockImplementation(async (request) => ({
      schema_version: "dmb_world_plan_document_edit_proposal_v1",
      action_id: `00000000-0000-4000-8000-${String(++proposalCount).padStart(12, "0")}`,
      idempotency_key: request.idempotency_key,
      document_id: request.document_id,
      world_id: request.world_id,
      base_revision: request.base_revision,
      base_content_sha256: request.base_content_sha256,
      draft_sha256: request.draft_sha256,
      target_kind: request.target_kind,
      selected_text_sha256: await sha256Hex(request.selected_text),
      replacement_markdown: "A lantern shines at the arch.",
      summary: "Add a lantern to the opening.",
      assumptions: [],
      model: "test-model",
      model_observed: false,
      model_latency_ms: 0,
      wall_latency_ms: 0,
      usage: null,
    }) as any);
    vi.spyOn(liveApi, "postWorldAgentNewConversation").mockImplementation(async (_world, request) => {
      api.setCurrent(history("conversation-b", request.expected_pointer_revision + 1, [
        makeTurn(1, "conversation-b-turn-1", "A fresh conversation question", "A fresh conversation answer"),
      ]));
      return {
        schema: "dmb_agent_new_conversation_response_v1",
        world_id: worldId,
        conversation_id: "conversation-b",
        active_conversation_id: "conversation-b",
        pointer_revision: request.expected_pointer_revision + 1,
      } as any;
    });
    const captured = {
      editor: { isDestroyed: false },
      request: {
        document_id: documentId,
        world_id: worldId,
        session: 1,
        base_revision: 7,
        base_content_sha256: contentSha256,
        draft_markdown: "# Draft Plan",
        draft_sha256: "d".repeat(64),
        target_kind: "insert_at_caret" as const,
        selected_text: "",
      },
      from: 1,
      to: 1,
      editorJson: "{}",
      selectionJson: "[]",
      draftGeneration: 0,
      selectionGeneration: 0,
    };
    const bridge = {
      capture: vi.fn(async () => captured),
      apply: vi.fn(async () => undefined),
    };

    const mounted = mountComponent(7, bridge);
    await screen.findByText(/No messages yet/i);
    expect(screen.getAllByRole("textbox")).toHaveLength(1);
    const messageBox = screen.getByLabelText("Message DungeonBuddy");
    expect(screen.getByRole("button", { name: "Settings" })).toBeInTheDocument();
    fireEvent.change(messageBox, { target: { value: "What is in the opening?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    expect(await screen.findByText("The saved Plan currently has one opening scene.")).toBeInTheDocument();
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(askRequests[0]).toMatchObject({
      message: "What is in the opening?",
      graph_request: { mode: "none" },
      graph_selection: null,
      primary_work: { object_id: documentId, expected_revision: 7 },
    });

        expect(screen.getByLabelText("Message DungeonBuddy")).toBe(messageBox);
    fireEvent.change(messageBox, { target: { value: "Add a lantern to the opening." } });
    fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
    const review = await screen.findByRole("region", { name: "Review proposed Plan edit" });
    expect(review.querySelectorAll("pre")[0]?.textContent)
      .toBe("Nothing selected · text will be inserted at the captured caret.");
    expect(screen.getAllByRole("textbox")).toHaveLength(1);
    expect(proposalRequest).toHaveBeenCalledTimes(1);
    expect(proposalRequest.mock.calls[0]![0]).toMatchObject({
      instruction: "Add a lantern to the opening.",
      base_revision: 7,
      target_kind: "insert_at_caret",
    });
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("region", { name: "World conversation transcript" })).toContainElement(review);
    expect(review).toHaveTextContent("A lantern shines at the arch.");
    expect(bridge.apply).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Apply changes" }));
    await waitFor(() => expect(bridge.apply).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("region", { name: "Review proposed Plan edit" })).not.toBeInTheDocument();
    expect(screen.getByText("Apply changes your draft. Save keeps the changes.")).toBeInTheDocument();
    expect(postAsk).toHaveBeenCalledTimes(1);

        fireEvent.change(messageBox, { target: { value: "Add a second detail to the opening." } });
    fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
    await screen.findByRole("region", { name: "Review proposed Plan edit" });
    fireEvent.click(screen.getByRole("button", { name: "Discard proposal" }));
    fireEvent.change(messageBox, { target: { value: "What follows the opening now?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    expect(await screen.findByText("The saved Plan discussion continues after the proposals.")).toBeInTheDocument();
    const earlier = screen.getByText(/Earlier conversation/).closest("details")!;
    fireEvent.click(earlier.querySelector("summary")!);
    fireEvent.click(within(earlier).getByRole("button", { name: "Load earlier messages" }));
    expect(await screen.findByText("What is in the opening?")).toBeInTheDocument();

    const transcriptArticles = Array.from(screen.getByRole("region", { name: "World conversation transcript" }).querySelectorAll("article"));
    expect(transcriptArticles.map((article) => article.hasAttribute("data-sequence")
      ? `world:${article.getAttribute("data-sequence")}`
      : `proposal:${article.querySelector("strong")?.parentElement?.textContent?.replace("You:", "").trim()}`)).toEqual([
      "world:1",
      "proposal:Add a lantern to the opening.",
      "proposal:Add a second detail to the opening.",
      "world:2",
    ]);
    expect(transcriptArticles.filter((article) => article.hasAttribute("data-proposal-turn-id"))
      .map((article) => article.getAttribute("data-after-sequence"))).toEqual(["1", "1"]);

    mounted.unmount();
    mountComponent(7, bridge);
    expect(await screen.findByText("The saved Plan discussion continues after the proposals.")).toBeInTheDocument();
    const earlierAfterReload = screen.getByText(/Earlier conversation/).closest("details")!;
    fireEvent.click(earlierAfterReload.querySelector("summary")!);
    fireEvent.click(within(earlierAfterReload).getByRole("button", { name: "Load earlier messages" }));
    expect(await screen.findByText("What is in the opening?")).toBeInTheDocument();
    const reloadedArticles = Array.from(screen.getByRole("region", { name: "World conversation transcript" }).querySelectorAll("article"));
    expect(reloadedArticles.map((article) => article.hasAttribute("data-sequence")
      ? `world:${article.getAttribute("data-sequence")}`
      : `proposal:${article.querySelector("strong")?.parentElement?.textContent?.replace("You:", "").trim()}`)).toEqual([
      "world:1",
      "proposal:Add a lantern to the opening.",
      "proposal:Add a second detail to the opening.",
      "world:2",
    ]);

    fireEvent.click(screen.getByRole("button", { name: "New conversation" }));
    expect(await screen.findByText("A fresh conversation question")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "World conversation transcript" })
      .querySelectorAll("[data-proposal-turn-id]")).toHaveLength(0);
    expect(screen.getByRole("region", { name: "Local Plan proposal activity" })).toHaveTextContent(
      "different World conversation",
    );
  });

  it.each([
    ["non-empty", "The old arrival prose.\n", "The old arrival prose.\n"],
    ["empty", "", "Empty card body"],
  ] as const)("reviews a card-body replacement against its captured %s Before", async (_label, targetBodyMarkdown, expectedBefore) => {
    setupApi(history("conversation-a", 4, []));
    const captured = await capturedCardBodyEdit(targetBodyMarkdown);
    const bridge = {
      capture: vi.fn(async () => captured),
      apply: vi.fn(async () => undefined),
    };
    const proposalRequest = mockCardBodyProposal();

    mountComponent(7, bridge);
    await screen.findByText(/No messages yet/i);
        fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "Revise the arrival scene." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));

    const review = await screen.findByRole("region", { name: "Review proposed Plan edit" });
    expect(review.querySelectorAll("pre")[0]?.textContent).toBe(expectedBefore);
    expect(review).toHaveTextContent("Card target · scene scene:arrival");
    expect(review.querySelectorAll("pre")[1]?.textContent).toBe("The revised scene opens.\n");
    expect(review).not.toHaveTextContent("Nothing selected · text will be inserted at the captured caret.");
    expect(proposalRequest).toHaveBeenCalledTimes(1);
    expect(proposalRequest.mock.calls[0]![0]).toMatchObject({
      target_kind: "replace_playable_body",
      selected_text: "",
      target_body_markdown: targetBodyMarkdown,
      target_body_sha256: captured.request.target_body_sha256,
    });
    expect(bridge.apply).not.toHaveBeenCalled();
  });

  it.each(["missing", "request-mismatch"] as const)(
    "fails closed before proposal dispatch when the captured card Before is %s",
    async (invalidCapture) => {
      setupApi(history("conversation-a", 4, []));
      const captured = await capturedCardBodyEdit("The old arrival prose.\n") as any;
      if (invalidCapture === "missing") captured.playableBodyTarget = undefined;
      else captured.request.target_body_markdown = "A different body.";
      const bridge = {
        capture: vi.fn(async () => captured),
        apply: vi.fn(async () => undefined),
      };
      const proposalRequest = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockResolvedValue({} as any);

      mountComponent(7, bridge);
      await screen.findByText(/No messages yet/i);
            fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
        target: { value: "Revise the arrival scene." },
      });
      fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));

      expect(await screen.findByRole("alert")).toHaveTextContent("no valid Before snapshot");
      expect(screen.queryByRole("region", { name: "Review proposed Plan edit" })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Apply changes" })).not.toBeInTheDocument();
      expect(proposalRequest).not.toHaveBeenCalled();
      expect(bridge.apply).not.toHaveBeenCalled();
    },
  );

  it("retires a card review when its captured target goes stale", async () => {
    setupApi(history("conversation-a", 4, []));
    const captured = await capturedCardBodyEdit("The old arrival prose.\n");
    const bridge = {
      capture: vi.fn(async () => captured),
      apply: vi.fn(async () => undefined),
    };
    mockCardBodyProposal();
    const arrivalTarget = { kind: "scene" as const, id: "scene:arrival", generation: 2 };
    const mounted = render(conversationElement({
      editBridge: bridge,
      playableEditTarget: arrivalTarget,
      playableEditTargetGeneration: 2,
    }));

    await screen.findByText(/No messages yet/i);
        fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "Revise the arrival scene." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
    await screen.findByRole("region", { name: "Review proposed Plan edit" });

    mounted.rerender(conversationElement({
      editBridge: bridge,
      playableEditTarget: { kind: "scene", id: "scene:warehouse", generation: 3 },
      playableEditTargetGeneration: 3,
    }));
    await waitFor(() => {
      expect(screen.queryByRole("region", { name: "Review proposed Plan edit" })).not.toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: "Apply changes" })).not.toBeInTheDocument();
    expect(bridge.apply).not.toHaveBeenCalled();
  });

  it("keeps an auth-rejected Ask pending until the operator reconnects and explicitly retries", async () => {
    const api = setupApi(history("conversation-a", 4, []));
    const requests: WorldPlanAgentTurnRequestV1[] = [];
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      requests.push(request);
      if (requests.length === 1) throw new liveApi.LiveApiError("Unauthorized", 401);
      api.setCurrent(history("conversation-a", 4, [
        makeTurn(1, request.turn_id, request.message, "Authorized retry answer"),
      ]));
      return agentResponse(request, "conversation-a", "Authorized retry answer") as any;
    });

    mountComponent();
    await screen.findByText(/No messages yet/i);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Keep this exact ask" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText(/Local authorization was rejected/)).toBeInTheDocument();
    expect(pendingAskKeys()).toHaveLength(1);
    expect(postAsk).toHaveBeenCalledTimes(1);
    const savedRequest = JSON.parse(localStorage.getItem(pendingAskKeys()[0]!)!).request;

    expect(screen.getByRole("button", { name: "Open Settings" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Connect local session", hidden: true })).not.toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Open Settings" }));
    expect(screen.getByRole("button", { name: "Connect local session" })).toBeVisible();
    vi.spyOn(liveApi, "connectNativeGraphSession").mockResolvedValue("test-csrf");
    fireEvent.click(screen.getByRole("button", { name: "Connect local session" }));
    expect(await screen.findByText(/Local Agent and Graph session active/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry saved Ask" }));

    expect(await screen.findByText("Authorized retry answer")).toBeInTheDocument();
    expect(postAsk).toHaveBeenCalledTimes(2);
    expect(requests[1]).toEqual(savedRequest);
    expect(pendingAskKeys()).toHaveLength(0);
  });

  it("retries New Conversation with the same CAS command and hydrates the confirmed server state", async () => {
    const api = setupApi(history("conversation-a", 10, [
      makeTurn(1, "turn-a", "Earlier question", "Earlier answer"),
    ]));
    const requests: any[] = [];
    const postNew = vi.spyOn(liveApi, "postWorldAgentNewConversation").mockImplementation(async (_world, request) => {
      expect(pendingCommandKeys()).toHaveLength(1);
      requests.push(request);
      if (requests.length === 1) throw new Error("connection lost after command");
      api.setCurrent(history("conversation-b", 11, []));
      return {
        schema: "dmb_agent_new_conversation_response_v1",
        world_id: worldId,
        conversation_id: "conversation-b",
        active_conversation_id: "conversation-b",
        pointer_revision: 11,
      } as any;
    });

    mountComponent();
    expect(await screen.findByText("Earlier question")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "New conversation" }));
    expect(await screen.findByText(/command outcome is uncertain/)).toBeInTheDocument();
    const storedCommand = JSON.parse(localStorage.getItem(pendingCommandKeys()[0]!)!);
    expect(storedCommand.request).toEqual(requests[0]);
    expect(requests[0]).toMatchObject({
      schema: "dmb_agent_new_conversation_v1",
      expected_pointer_revision: 10,
      expected_active_conversation_id: "conversation-a",
    });

    fireEvent.click(screen.getByRole("button", { name: "Retry saved New Conversation command" }));
    expect(await screen.findByText(/No messages yet/i)).toBeInTheDocument();
    expect(requests[1]).toEqual(requests[0]);
    expect(postNew).toHaveBeenCalledTimes(2);
    expect(pendingCommandKeys()).toHaveLength(0);
    expect(harness.agent.updateThread).not.toHaveBeenCalled();
    expect(harness.agent.createThread).not.toHaveBeenCalled();
  });

  it("keeps a delayed old Ask result out of a newly active World conversation", async () => {
    const api = setupApi(history("conversation-a", 10, []));
    const sent: WorldPlanAgentTurnRequestV1[] = [];
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      sent.push(request);
      if (sent.length === 1) throw new Error("temporary network failure");
      return agentResponse(request, "conversation-a", "Old conversation answer") as any;
    });
    vi.spyOn(liveApi, "postWorldAgentNewConversation").mockImplementation(async (_world, request) => {
      api.setCurrent(history("conversation-b", 11, []));
      return {
        schema: "dmb_agent_new_conversation_response_v1",
        world_id: worldId,
        conversation_id: "conversation-b",
        active_conversation_id: "conversation-b",
        pointer_revision: 11,
      } as any;
    });

    mountComponent();
    await screen.findByText(/No messages yet/i);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Keep this in conversation A" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    expect(await screen.findByText(/Ask outcome is uncertain/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "New conversation" }));
    await waitFor(() => expect(screen.getByText(/New World conversation confirmed/)).toBeInTheDocument());
    await screen.findByText(/No messages yet/i);
    fireEvent.click(screen.getByRole("button", { name: "Retry saved Ask" }));

    expect(await screen.findByText(/not inserted into the currently active conversation/)).toBeInTheDocument();
    expect(sent[1]).toEqual(sent[0]);
    expect(postAsk).toHaveBeenCalledTimes(2);
    expect(screen.queryByText("Old conversation answer")).not.toBeInTheDocument();
    expect(screen.queryByText("Keep this in conversation A")).not.toBeInTheDocument();
    expect(harness.agent.updateThread).not.toHaveBeenCalled();
  });

  it("keeps a null-basis Ask response pending unless it carries the durable receipt replay trace", async () => {
    setupApi(history("conversation-a", 4, []));
    const requests: WorldPlanAgentTurnRequestV1[] = [];
    vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      requests.push(request);
      const response = agentResponse(request, "conversation-a", "Unverified response");
      response.primary_work.content_basis = null as any;
      response.conversation.pointer_status = "reused";
      return response as any;
    });

    mountComponent();
    await screen.findByText(/No messages yet/i);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Do not accept this result" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/did not match this saved Plan|could not be verified/i);
    expect(requests).toHaveLength(1);
    expect(requests[0]?.message).toBe("Do not accept this result");
    expect(pendingAskKeys()).toHaveLength(1);
  });

  it("keeps a full-cap legacy thread byte-for-byte exportable while real provider storage persists Compose and Apply separately", async () => {
    const api = setupApi(history("conversation-a", 4, []));
    harness.agent = null;
    const legacy = fullLegacyThread();
    persistAgentThread(legacy);
    const legacyKey = threadStorageKey(namespace, legacy.threadId);
    const legacyBytes = localStorage.getItem(legacyKey);
    expect(legacyBytes).toBeTruthy();
    expect(JSON.parse(legacyBytes!).turns).toHaveLength(AGENT_TURN_HISTORY_CAP);

    const createdBlobs: Blob[] = [];
    const oldCreate = Object.getOwnPropertyDescriptor(URL, "createObjectURL");
    const oldRevoke = Object.getOwnPropertyDescriptor(URL, "revokeObjectURL");
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn((blob: Blob) => {
        createdBlobs.push(blob);
        return "blob:legacy-export";
      }),
    });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    try {
      const captured = {
        editor: { isDestroyed: false },
        request: {
          document_id: documentId,
          world_id: worldId,
          session: 1,
          base_revision: 7,
          base_content_sha256: contentSha256,
          draft_markdown: "# Draft\n\nDraft excerpt.",
          draft_sha256: "d".repeat(64),
          target_kind: "replace_selection" as const,
          selected_text: "Draft excerpt",
        },
        from: 1,
        to: 2,
        editorJson: "{}",
        selectionJson: "[]",
        draftGeneration: 0,
        selectionGeneration: 0,
      };
      const bridge = {
        capture: vi.fn(async () => captured),
        apply: vi.fn(async () => undefined),
      };
      vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockImplementation(async (request) => ({
        schema_version: "dmb_world_plan_document_edit_proposal_v1",
        action_id: "00000000-0000-4000-8000-000000000088",
        idempotency_key: request.idempotency_key,
        document_id: request.document_id,
        world_id: request.world_id,
        base_revision: request.base_revision,
        base_content_sha256: request.base_content_sha256,
        draft_sha256: request.draft_sha256,
        target_kind: request.target_kind,
        selected_text_sha256: await sha256Hex(request.selected_text),
        replacement_markdown: "A distant bell rings.",
        summary: "**Saved Plan:** Add a distant bell.\n\n**Evidence:** Draft excerpt.\n\n- The opening scene gains a bell",
        assumptions: [],
        model: "test-model",
        model_observed: false,
        model_latency_ms: 0,
        wall_latency_ms: 0,
        usage: null,
      }) as any);

      const renderRealProvider = () => render(
        <AgentInteractionProvider>
          <ActualProviderScopeInitializer />
          <WorldPlanAgentConversation
            worldId={worldId}
            worldName="Test World"
            documentId={documentId}
            surfaceInstanceId={surfaceInstanceId}
            revision={7}
            editBridge={bridge}
            draftGeneration={0}
            selectionGeneration={0}
            savedDirty={false}
            pageReady
            saveInFlight={false}
          />
        </AgentInteractionProvider>,
      );

      let view = renderRealProvider();
      expect(await screen.findByText("Legacy question 20")).toBeInTheDocument();
      fireEvent.click(screen.getByText("Advanced details"));
      expect(screen.getByRole("region", { name: "Local-only legacy Plan history" })).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Export local history JSON" }));
      expect(await readBlob(createdBlobs[0]!)).toBe(legacyBytes);

            fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
        target: { value: "Add a distant bell." },
      });
      fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
      const review = await screen.findByRole("region", { name: "Review proposed Plan edit" });
      expect(review.querySelectorAll("pre")[0]?.textContent).toBe("Draft excerpt");
      expect(review).not.toHaveTextContent("Nothing selected · text will be inserted at the captured caret.");
      fireEvent.click(screen.getByRole("button", { name: "Apply changes" }));
      await waitFor(() => expect(bridge.apply).toHaveBeenCalledTimes(1));

      const proposalEvent = document.querySelector(".world-plan-agent-conversation__proposal-event")!;
      expect(within(proposalEvent).getByText("Saved Plan:", { selector: "strong" })).toBeInTheDocument();
      expect(within(proposalEvent).getByText("Evidence:", { selector: "strong" })).toBeInTheDocument();
      expect(within(proposalEvent).getByText("The opening scene gains a bell")).toBeInTheDocument();
      expect(proposalEvent).not.toHaveTextContent("**Saved Plan:**");

      const activeThreadId = localStorage.getItem(activeThreadStorageKey(namespace, "plan", documentId));
      expect(activeThreadId).toBeTruthy();
      expect(activeThreadId).not.toBe(legacy.threadId);
      const proposalKey = threadStorageKey(namespace, activeThreadId!);
      const proposalThread = JSON.parse(localStorage.getItem(proposalKey) ?? "null");
      expect(proposalThread).toMatchObject({
        worldPlanProposalHistory: "world_plan_proposals_v1",
        turns: [{ backend: "plan_edit", planEdit: { applied: true } }],
      });
      expect(proposalThread.turns).toHaveLength(1);
      expect(localStorage.getItem(legacyKey)).toBe(legacyBytes);
      expect(JSON.parse(legacyBytes!).turns).toHaveLength(AGENT_TURN_HISTORY_CAP);
      expect(await screen.findByRole("region", { name: "World conversation transcript" })).toBeInTheDocument();
      expect(screen.getByRole("region", { name: "Local-only legacy Plan history" })).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: "Export local history JSON" }));
      expect(await readBlob(createdBlobs[1]!)).toBe(legacyBytes);
      view.unmount();
      api.setPlanBasis(committedRevision());

      harness.host = document.createElement("div");
      document.body.appendChild(harness.host);
      view = renderRealProvider();
      expect(await screen.findByRole("region", { name: "World conversation transcript" })).toBeInTheDocument();
      fireEvent.click(screen.getByText("Advanced details"));
      expect(await screen.findByRole("region", { name: "Local-only legacy Plan history" })).toBeInTheDocument();
      expect(localStorage.getItem(legacyKey)).toBe(legacyBytes);
      expect(JSON.parse(localStorage.getItem(proposalKey) ?? "null").turns[0].planEdit.applied).toBe(true);
      view.unmount();
    } finally {
      if (oldCreate) Object.defineProperty(URL, "createObjectURL", oldCreate);
      else delete (URL as any).createObjectURL;
      if (oldRevoke) Object.defineProperty(URL, "revokeObjectURL", oldRevoke);
      else delete (URL as any).revokeObjectURL;
    }
  });

  it("sends empty proposal history and preserves an in-flight PlanAction body across a conversation change", async () => {
    const api = setupApi(history("conversation-a", 10, []));
    let releaseProposal: ((value: any) => void) | null = null;
    const pendingProposal = new Promise<any>((resolve) => { releaseProposal = resolve; });
    const proposalSpy = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockReturnValue(pendingProposal);
    vi.spyOn(liveApi, "postWorldAgentNewConversation").mockImplementation(async (_world, _request) => {
      api.setCurrent(history("conversation-b", 11, []));
      return {
        schema: "dmb_agent_new_conversation_response_v1",
        world_id: worldId,
        conversation_id: "conversation-b",
        active_conversation_id: "conversation-b",
        pointer_revision: 11,
      } as any;
    });
    const captured = {
      editor: { isDestroyed: false },
      request: {
        document_id: documentId,
        world_id: worldId,
        session: 1,
        base_revision: 7,
        base_content_sha256: contentSha256,
        draft_markdown: "# Draft",
        draft_sha256: "d".repeat(64),
        target_kind: "replace_selection" as const,
        selected_text: "Draft excerpt",
      },
      from: 1,
      to: 2,
      editorJson: "{}",
      selectionJson: "[]",
      draftGeneration: 0,
      selectionGeneration: 0,
    };
    const bridge = {
      capture: vi.fn(async () => captured),
      apply: vi.fn(async () => undefined),
    };

    const view = mountComponent(7, bridge);
    await screen.findByText(/No messages yet/i);
        fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "Revise this excerpt" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
    await waitFor(() => expect(proposalSpy).toHaveBeenCalledTimes(1));
    const originalRequest = proposalSpy.mock.calls[0]![0];
    expect(originalRequest.conversation_history).toEqual([]);
    expect(JSON.stringify(originalRequest)).not.toContain("Legacy only fact");

    view.rerender(
      <WorldPlanAgentConversation
        worldId={worldId}
        worldName="Test World"
        documentId={documentId}
        surfaceInstanceId={surfaceInstanceId}
        revision={8}
        editBridge={bridge}
        draftGeneration={0}
        selectionGeneration={0}
        savedDirty={false}
        pageReady
        saveInFlight={false}
      />,
    );
    await waitFor(() => expect(screen.getByRole("button", { name: "New conversation" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "New conversation" }));
    await screen.findByText(/No messages yet/i);

    expect(proposalSpy).toHaveBeenCalledTimes(1);
    expect(proposalSpy.mock.calls[0]![0]).toEqual(originalRequest);
    expect(originalRequest.idempotency_key).toBeTruthy();
    expect(harness.agent.updateThread).not.toHaveBeenCalled();
    await act(async () => {
      releaseProposal?.({ idempotency_key: originalRequest.idempotency_key, action_id: "action-1" });
    });
  });
});
