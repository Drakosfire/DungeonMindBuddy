/** Navigation href only. Typed Buddy identities are admitted by their own nodes. */
export function webSourceHref(value: unknown): string | null {
  if (typeof value !== 'string' || /[\s\u0000-\u001f\u007f\\]/u.test(value) || !/^https?:\/\//i.test(value)) return null;
  try {
    const url = new URL(value);
    return url.hostname && !url.username && !url.password ? value : null;
  } catch { return null; }
}
