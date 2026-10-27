import { admittedSessionEvidenceHref } from '../../playSurface/review/sessionEvidenceHref';
import { admittedDocumentHref } from '../../documentReference/documentReference';
/** Navigation href only. Typed Buddy identities are admitted by their own nodes. */
export function webSourceHref(value: unknown): string | null {
  if (typeof value === 'string' && (admittedDocumentHref(value) || admittedSessionEvidenceHref(value))) return value;
  if (typeof value !== 'string' || /[\s\u0000-\u001f\u007f\\]/u.test(value) || !/^https?:\/\//i.test(value)) return null;
  try {
    const url = new URL(value);
    return url.hostname && !url.username && !url.password ? value : null;
  } catch { return null; }
}

/** Inert optional display text; never URL or evidence authority. */
export function validWebSourceTitle(value: unknown): value is string | null | undefined {
  return value == null || (typeof value === 'string' && !/[\u0000-\u001f\u007f-\u009f]/u.test(value));
}
