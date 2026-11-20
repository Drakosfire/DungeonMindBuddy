/** Navigation syntax only; the immutable evidence viewer owns target verification. */
export function admittedSessionEvidenceHref(value: unknown): value is string {
  if (typeof value !== 'string' || !value.startsWith('/play?') || /[\s\u0000-\u001f\u007f\\]/u.test(value)) return false;
  let url: URL;
  try { url = new URL(value, 'https://surface.invalid'); } catch { return false; }
  if (url.pathname !== '/play' || value.split(/[?#]/)[0] !== '/play') return false;
  const keys = new Set(['world', 'run', 'evidence_revision']);
  for (const key of url.searchParams.keys()) if (!keys.has(key) || url.searchParams.getAll(key).length !== 1) return false;
  const world = url.searchParams.get('world'), run = url.searchParams.get('run'), revision = url.searchParams.get('evidence_revision');
  if (!world || world.trim() !== world || /[\u0000-\u001f\u007f]/u.test(world)
      || !run || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(run)
      || !revision || !/^[1-9][0-9]*$/.test(revision) || !Number.isSafeInteger(Number(revision))) return false;
  if (!url.hash) return true;
  const match = /^#source-(0|[1-9][0-9]*)-([a-f0-9]{64})-([a-f0-9]{64})-([a-f0-9]{64})-([a-f0-9]{64})$/.exec(url.hash);
  return !!match && Number.isSafeInteger(Number(match[1]));
}
