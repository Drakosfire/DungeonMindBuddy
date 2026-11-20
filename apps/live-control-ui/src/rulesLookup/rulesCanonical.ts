const record = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === 'object' && !Array.isArray(value);
export function rulesCanonical(value: unknown): string {
  if (Array.isArray(value)) return '[' + value.map(rulesCanonical).join(',') + ']';
  if (record(value)) return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + rulesCanonical(value[key])).join(',') + '}';
  return JSON.stringify(value);
}
export async function rulesDigest(value: string): Promise<string> {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))), byte => byte.toString(16).padStart(2, '0')).join('');
}
