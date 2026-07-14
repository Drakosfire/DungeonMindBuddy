export type HermesConversationHistoryRole = "user" | "assistant";

export interface HermesConversationHistoryMessage {
  role: HermesConversationHistoryRole;
  content: string;
}

export const HERMES_HISTORY_MAX_PAIRS = 6;
export const HERMES_HISTORY_MAX_MESSAGES = 12;
export const HERMES_HISTORY_MAX_MESSAGE_CHARS = 4000;
export const HERMES_HISTORY_MAX_TOTAL_CHARS = 16000;

interface ValidTurnPair {
  question: string;
  answer: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function nonEmptyTrimmedString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function validTurnPair(entry: unknown): ValidTurnPair | null {
  if (!isRecord(entry)) return null;
  const question = nonEmptyTrimmedString(entry.question);
  const answer = nonEmptyTrimmedString(entry.answer);
  if (!question || !answer) return null;
  if (question.length > HERMES_HISTORY_MAX_MESSAGE_CHARS) return null;
  if (answer.length > HERMES_HISTORY_MAX_MESSAGE_CHARS) return null;
  return { question, answer };
}

function pairCharTotal(pair: ValidTurnPair): number {
  return pair.question.length + pair.answer.length;
}

function selectBoundedPairs(pairs: ValidTurnPair[]): ValidTurnPair[] {
  const selected: ValidTurnPair[] = [];
  let totalChars = 0;
  for (const pair of pairs) {
    if (selected.length >= HERMES_HISTORY_MAX_PAIRS) break;
    const nextTotal = totalChars + pairCharTotal(pair);
    if (nextTotal > HERMES_HISTORY_MAX_TOTAL_CHARS) continue;
    selected.push(pair);
    totalChars = nextTotal;
  }
  return selected;
}

function flattenPairs(pairs: ValidTurnPair[]): HermesConversationHistoryMessage[] {
  const messages: HermesConversationHistoryMessage[] = [];
  for (const pair of pairs) {
    messages.push({ role: "user", content: pair.question });
    messages.push({ role: "assistant", content: pair.answer });
  }
  return messages;
}

export function buildHermesConversationHistory(turns: unknown): HermesConversationHistoryMessage[] {
  if (!Array.isArray(turns)) return [];
  const validPairs: ValidTurnPair[] = [];
  for (const entry of turns) {
    const pair = validTurnPair(entry);
    if (pair) validPairs.push(pair);
  }
  const bounded = selectBoundedPairs(validPairs);
  const chronological = [...bounded].reverse();
  return flattenPairs(chronological);
}

function validMessagePair(
  user: unknown,
  assistant: unknown,
): HermesConversationHistoryMessage[] | null {
  if (!isRecord(user) || !isRecord(assistant)) return null;
  const userContent = nonEmptyTrimmedString(user.content);
  const assistantContent = nonEmptyTrimmedString(assistant.content);
  if (!userContent || !assistantContent) return null;
  if (user.role !== "user" || assistant.role !== "assistant") return null;
  if (userContent.length > HERMES_HISTORY_MAX_MESSAGE_CHARS) return null;
  if (assistantContent.length > HERMES_HISTORY_MAX_MESSAGE_CHARS) return null;
  return [
    { role: "user", content: userContent },
    { role: "assistant", content: assistantContent },
  ];
}

function selectBoundedMessages(
  messages: HermesConversationHistoryMessage[],
): HermesConversationHistoryMessage[] {
  const pairs: ValidTurnPair[] = [];
  for (let index = 0; index + 1 < messages.length; index += 2) {
    const user = messages[index];
    const assistant = messages[index + 1];
    if (user?.role !== "user" || assistant?.role !== "assistant") continue;
    pairs.push({ question: user.content, answer: assistant.content });
  }
  return flattenPairs(selectBoundedPairs(pairs));
}

export function normalizeHermesOutboundConversationHistory(
  value: unknown,
): HermesConversationHistoryMessage[] {
  if (!Array.isArray(value)) return [];
  const pairs: HermesConversationHistoryMessage[] = [];
  for (let index = 0; index + 1 < value.length; index += 2) {
    const built = validMessagePair(value[index], value[index + 1]);
    if (built) pairs.push(...built);
  }
  return selectBoundedMessages(pairs);
}
