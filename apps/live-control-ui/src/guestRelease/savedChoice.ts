export type SavedChoice = { version: "owner_saved_choice_v1"; prompt: string;
  options: [{ label: string; outcome: string }, { label: string; outcome: string }] };

function safeText(value: unknown, limit: number, multiline = false): value is string {
  if (typeof value !== "string" || !value.trim() || [...value].length > limit) return false;
  if (/[\[\]<>/\\@:]/.test(value) || /(?:[a-z0-9-]+\.)+[a-z]{2,}(?:\b|$)/.test(asciiFold(value))) return false;
  return ![...value].some(char => { const code = char.codePointAt(0)!; return (code < 32 && !(multiline && code === 10))
    || (code >= 0x7f && code <= 0x9f) || (code >= 0x202a && code <= 0x202e) || (code >= 0x2066 && code <= 0x2069)
    || (code >= 0xd800 && code <= 0xdfff); });
}

function asciiFold(value: string): string {
  return value.replace(/[A-Z]/g, char => String.fromCharCode(char.charCodeAt(0) + 32));
}

/** Old copies omit the field; a malformed present value is never approved. */
export function isSavedChoice(value: unknown): value is SavedChoice {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const item = value as Record<string, unknown>;
  if (Object.keys(item).sort().join(",") !== "options,prompt,version"
    || item.version !== "owner_saved_choice_v1" || !safeText(item.prompt, 240)
    || !Array.isArray(item.options) || item.options.length !== 2) return false;
  const valid = item.options.every((value: unknown) => {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const option = value as Record<string, unknown>;
    return Object.keys(option).sort().join(",") === "label,outcome"
      && safeText(option.label, 80) && safeText(option.outcome, 2000, true);
  });
  return valid && asciiFold(item.options[0].label.trim()) !== asciiFold(item.options[1].label.trim());
}
