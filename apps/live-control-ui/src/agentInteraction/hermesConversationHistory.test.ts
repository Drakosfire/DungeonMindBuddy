import { describe, expect, it } from "vitest";

import {
  buildHermesConversationHistory,
  HERMES_HISTORY_MAX_MESSAGE_CHARS,
  HERMES_HISTORY_MAX_PAIRS,
  HERMES_HISTORY_MAX_TOTAL_CHARS,
  normalizeHermesOutboundConversationHistory,
} from "./hermesConversationHistory";

const POISON_FIELDS = {
  trace: "RAW_TRACE_SECRET",
  citations: "RAW_CITATION_SECRET",
  grounding: "FOREIGN_REVISION_A",
  worldGraphContext: "FOREIGN_THREAD_A",
  hermes_session_id: "RAW_HERMES_TRANSCRIPT_SECRET",
  manifest_path: "/foreign/absolute/path.md",
  tool_arguments: "RAW_TOOL_ARGUMENT_SECRET",
  source_body: "RAW_SOURCE_BODY_SECRET",
  system: "RAW_SYSTEM_MESSAGE_SECRET",
} as const;

describe("buildHermesConversationHistory", () => {
  it("returns empty output for non-array input", () => {
    expect(buildHermesConversationHistory(null)).toEqual([]);
    expect(buildHermesConversationHistory("bad")).toEqual([]);
  });

  it("converts newest-first turns into chronological user/assistant pairs", () => {
    const history = buildHermesConversationHistory([
      { question: "Turn 3?", answer: "Answer 3." },
      { question: "Turn 2?", answer: "Answer 2." },
      { question: "Turn 1?", answer: "Answer 1." },
    ]);
    expect(history).toEqual([
      { role: "user", content: "Turn 1?" },
      { role: "assistant", content: "Answer 1." },
      { role: "user", content: "Turn 2?" },
      { role: "assistant", content: "Answer 2." },
      { role: "user", content: "Turn 3?" },
      { role: "assistant", content: "Answer 3." },
    ]);
  });

  it("drops malformed and oversized pairs while preserving valid siblings", () => {
    const oversized = "x".repeat(HERMES_HISTORY_MAX_MESSAGE_CHARS + 1);
    const history = buildHermesConversationHistory([
      { question: "Valid 2?", answer: "Valid 2." },
      { question: oversized, answer: "Too big." },
      { question: "", answer: "Missing question." },
      { question: "Valid 1?", answer: "Valid 1." },
    ]);
    expect(history).toEqual([
      { role: "user", content: "Valid 1?" },
      { role: "assistant", content: "Valid 1." },
      { role: "user", content: "Valid 2?" },
      { role: "assistant", content: "Valid 2." },
    ]);
  });

  it("enforces pair, message, and total character caps deterministically", () => {
    const pairs = Array.from({ length: HERMES_HISTORY_MAX_PAIRS + 2 }, (_, index) => ({
      question: `Q${index}?`,
      answer: `A${index}.`,
    })).reverse();
    const history = buildHermesConversationHistory(pairs);
    expect(history).toHaveLength(HERMES_HISTORY_MAX_PAIRS * 2);

    const largePair = {
      question: "a".repeat(HERMES_HISTORY_MAX_MESSAGE_CHARS),
      answer: "b".repeat(HERMES_HISTORY_MAX_MESSAGE_CHARS),
    };
    const secondLargePair = {
      question: "c".repeat(HERMES_HISTORY_MAX_MESSAGE_CHARS),
      answer: "d".repeat(HERMES_HISTORY_MAX_MESSAGE_CHARS),
    };
    const smallPair = { question: "Small?", answer: "Small." };
    const budgeted = buildHermesConversationHistory([smallPair, secondLargePair, largePair]);
    expect(budgeted).toEqual([
      { role: "user", content: secondLargePair.question },
      { role: "assistant", content: secondLargePair.answer },
      { role: "user", content: "Small?" },
      { role: "assistant", content: "Small." },
    ]);
    const totalChars = budgeted.reduce((sum, message) => sum + message.content.length, 0);
    expect(totalChars).toBeLessThanOrEqual(HERMES_HISTORY_MAX_TOTAL_CHARS);
  });

  it("ignores poison metadata and never mutates source turns", () => {
    const turns = [
      {
        question: "What is it?",
        answer: "Tripod Null-Calf.",
        ...POISON_FIELDS,
      },
    ];
    const copy = structuredClone(turns);
    const history = buildHermesConversationHistory(turns);
    expect(history).toEqual([
      { role: "user", content: "What is it?" },
      { role: "assistant", content: "Tripod Null-Calf." },
    ]);
    expect(turns).toEqual(copy);
    expect(JSON.stringify(history)).not.toContain("RAW_TRACE_SECRET");
    expect(JSON.stringify(history)).not.toContain("/foreign/absolute/path.md");
  });
});

describe("normalizeHermesOutboundConversationHistory", () => {
  it("re-normalizes adversarial wire values independently", () => {
    const normalized = normalizeHermesOutboundConversationHistory([
      { role: "user", content: "  First?  ", trace: "RAW_TRACE_SECRET" },
      { role: "assistant", content: "First.", citations: ["RAW_CITATION_SECRET"] },
      { role: "tool", content: "must drop" },
      { role: "assistant", content: "orphan" },
      { role: "user", content: "Second?" },
      { role: "assistant", content: "Second." },
    ]);
    expect(normalized).toEqual([
      { role: "user", content: "First?" },
      { role: "assistant", content: "First." },
      { role: "user", content: "Second?" },
      { role: "assistant", content: "Second." },
    ]);
    expect(JSON.stringify(normalized)).not.toContain("RAW_TRACE_SECRET");
    expect(JSON.stringify(normalized)).not.toContain("RAW_CITATION_SECRET");
  });

  it("preserves later valid siblings when a mid-stream child is malformed", () => {
    const normalized = normalizeHermesOutboundConversationHistory([
      { role: "user", content: "First?" },
      null,
      { role: "assistant", content: "First answer." },
      { role: "user", content: "Second?" },
      { role: "assistant", content: "Second answer." },
    ]);
    expect(normalized).toEqual([
      { role: "user", content: "First?" },
      { role: "assistant", content: "First answer." },
      { role: "user", content: "Second?" },
      { role: "assistant", content: "Second answer." },
    ]);
  });
});
