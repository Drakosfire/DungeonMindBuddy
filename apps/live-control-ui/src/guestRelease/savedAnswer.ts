export type SavedAnswer = { version: "owner_saved_answer_v1"; question: string;
  passages: { text: string; references: string[] }[] };

export function isSavedAnswerText(value: unknown, limit: number, multiline = false): value is string {
  return typeof value === "string" && !!value.trim() && Array.from(value).length <= limit
    && !/[\[\]<>/\\@:]/u.test(value) && !/(?:[a-z0-9-]+\.)+[a-z]{2,}(?:\b|$)/.test(value.replace(/[A-Z]/g, char => String.fromCharCode(char.charCodeAt(0) + 32)))
    && !Array.from(value).some(char => { const code = char.codePointAt(0)!;
      return (code < 32 && !(multiline && code === 10)) || (code >= 0x7f && code <= 0x9f)
        || (code >= 0x202a && code <= 0x202e) || (code >= 0x2066 && code <= 0x2069)
        || (code >= 0xd800 && code <= 0xdfff); });
}

/** A present answer is usable only when every passage references this copy. */
export function isSavedAnswer(value: unknown, sources: { id: string }[]): value is SavedAnswer {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const answer = value as Record<string, unknown>;
  if (Object.keys(answer).sort().join(",") !== "passages,question,version"
    || answer.version !== "owner_saved_answer_v1" || !isSavedAnswerText(answer.question, 240)
    || !Array.isArray(answer.passages) || answer.passages.length < 1 || answer.passages.length > 10) return false;
  return answer.passages.every(value => {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const passage = value as Record<string, unknown>;
    return Object.keys(passage).sort().join(",") === "references,text"
      && isSavedAnswerText(passage.text, 2000, true)
      && Array.isArray(passage.references) && passage.references.length >= 1 && passage.references.length <= 5
      && new Set(passage.references).size === passage.references.length
      && passage.references.every(id => typeof id === "string" && sources.some(source => source.id === id));
  });
}
