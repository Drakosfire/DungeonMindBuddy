/** Display-only formatting. Never use this string as a predicate identifier. */
export function predicatePhrase(predicate: string): string {
  return predicate.replace(/_/g, " ");
}

export interface CaptionBounds { left: number; top: number; right: number; bottom: number }
export function overlaps(a: CaptionBounds, b: CaptionBounds): boolean {
  return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
}

/** The canvas owns these quadratic/cubic paths. Sample their middle, without DOM measurements. */
export function edgeCaption(path: string, predicate: string, fraction = .5, scale = 1) {
  const v = path.match(/-?\d+(?:\.\d+)?(?:e[+-]?\d+)?/gi)?.map(Number) ?? [];
  const cubic = path.includes(" C ");
  if (v.length !== (cubic ? 8 : 6) || v.some(n => !Number.isFinite(n))) return null;
  const point = (t: number) => {
    const s = 1 - t;
    return cubic
      ? { x: s ** 3 * v[0] + 3 * s * s * t * v[2] + 3 * s * t * t * v[4] + t ** 3 * v[6], y: s ** 3 * v[1] + 3 * s * s * t * v[3] + 3 * s * t * t * v[5] + t ** 3 * v[7] }
      : { x: s * s * v[0] + 2 * s * t * v[2] + t * t * v[4], y: s * s * v[1] + 2 * s * t * v[3] + t * t * v[5] };
  };
  const center = point(fraction), before = point(fraction - .01), after = point(fraction + .01);
  let angle = Math.atan2(after.y - before.y, after.x - before.x);
  // Only the text turns upright. The path and its target arrowhead never reverse.
  if (angle > Math.PI / 2) angle -= Math.PI;
  if (angle < -Math.PI / 2) angle += Math.PI;
  let length = 0, previous = point(0);
  for (let i = 1; i <= 32; i++) { const next = point(i / 32); length += Math.hypot(next.x - previous.x, next.y - previous.y); previous = next; }
  const phrase = predicatePhrase(predicate);
  const glyphWidth = (character: string) => /[^\u0000-\u024f]/u.test(character) ? 12 : /[il .,:;]/.test(character) ? 4 : /[MW@]/.test(character) ? 11 : 7;
  const available = Math.max(0, length * 2 * Math.min(fraction, 1 - fraction) - 12) / scale;
  if (available < 28 || !phrase.trim()) return null;
  const chars = Array.from(phrase);
  let text = "", width = 0;
  for (const char of chars.slice(0, 64)) { if (width + glyphWidth(char) + 12 > available) break; text += char; width += glyphWidth(char); }
  if (Array.from(text).length < chars.length) { text = text.trimEnd() + "…"; width += 12; }
  width = (width + 8) * scale;
  const height = 20 * scale;
  const x = center.x + Math.sin(angle) * 8 * scale, y = center.y - Math.cos(angle) * 8 * scale;
  const halfWidth = (Math.abs(Math.cos(angle)) * width + Math.abs(Math.sin(angle)) * height) / 2;
  const halfHeight = (Math.abs(Math.sin(angle)) * width + Math.abs(Math.cos(angle)) * height) / 2;
  return { text, x, y, width, height, length, radians: angle, angle: angle * 180 / Math.PI,
    bounds: { left: x - halfWidth, right: x + halfWidth, top: y - halfHeight, bottom: y + halfHeight } };
}

/** Rectangle/circle intersection in caption-local coordinates avoids treating round bubbles as square obstacles. */
export function captionTouchesCircle(caption: NonNullable<ReturnType<typeof edgeCaption>>, circle: { x: number; y: number; radius: number }) {
  const dx = circle.x - caption.x, dy = circle.y - caption.y;
  const x = Math.cos(caption.radians) * dx + Math.sin(caption.radians) * dy;
  const y = -Math.sin(caption.radians) * dx + Math.cos(caption.radians) * dy;
  const outsideX = Math.max(0, Math.abs(x) - caption.width / 2);
  const outsideY = Math.max(0, Math.abs(y) - caption.height / 2);
  return outsideX ** 2 + outsideY ** 2 < (circle.radius + 2) ** 2;
}
