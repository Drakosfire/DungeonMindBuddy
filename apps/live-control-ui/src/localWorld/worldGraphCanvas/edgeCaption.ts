/** Display-only formatting. Never use this string as a predicate identifier. */
export function predicatePhrase(predicate: string): string {
  return predicate.replace(/_/g, " ");
}

export interface CaptionBounds { left: number; top: number; right: number; bottom: number }
export function overlaps(a: CaptionBounds, b: CaptionBounds): boolean {
  return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
}

/** The canvas owns these quadratic/cubic paths. Sample their middle, without DOM measurements. */
export function edgeCaption(path: string, predicate: string) {
  const v = path.match(/-?\d+(?:\.\d+)?(?:e[+-]?\d+)?/gi)?.map(Number) ?? [];
  const cubic = path.includes(" C ");
  if (v.length !== (cubic ? 8 : 6) || v.some(n => !Number.isFinite(n))) return null;
  const point = (t: number) => {
    const s = 1 - t;
    return cubic
      ? { x: s ** 3 * v[0] + 3 * s * s * t * v[2] + 3 * s * t * t * v[4] + t ** 3 * v[6], y: s ** 3 * v[1] + 3 * s * s * t * v[3] + 3 * s * t * t * v[5] + t ** 3 * v[7] }
      : { x: s * s * v[0] + 2 * s * t * v[2] + t * t * v[4], y: s * s * v[1] + 2 * s * t * v[3] + t * t * v[5] };
  };
  const center = point(.5), before = point(.49), after = point(.51);
  let angle = Math.atan2(after.y - before.y, after.x - before.x);
  // Only the text turns upright. The path and its target arrowhead never reverse.
  if (angle > Math.PI / 2) angle -= Math.PI;
  if (angle < -Math.PI / 2) angle += Math.PI;
  let length = 0, previous = point(0);
  for (let i = 1; i <= 32; i++) { const next = point(i / 32); length += Math.hypot(next.x - previous.x, next.y - previous.y); previous = next; }
  const phrase = predicatePhrase(predicate);
  // Conservative character estimate accommodates wide glyphs without measuring browser fonts.
  const capacity = Math.min(64, Math.floor((length - 24) / 12));
  if (capacity < 4 || !phrase.trim()) return null;
  const chars = Array.from(phrase);
  const text = chars.length > capacity ? `${chars.slice(0, capacity - 1).join("")}…` : phrase;
  const width = Array.from(text).length * 12 + 8;
  const height = 20;
  const x = center.x + Math.sin(angle) * 8, y = center.y - Math.cos(angle) * 8;
  const halfWidth = (Math.abs(Math.cos(angle)) * width + Math.abs(Math.sin(angle)) * height) / 2;
  const halfHeight = (Math.abs(Math.sin(angle)) * width + Math.abs(Math.cos(angle)) * height) / 2;
  return { text, x, y, angle: angle * 180 / Math.PI,
    bounds: { left: x - halfWidth, right: x + halfWidth, top: y - halfHeight, bottom: y + halfHeight } };
}
