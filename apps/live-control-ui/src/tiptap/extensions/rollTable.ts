import type { Node } from '@tiptap/pm/model';

export function readRollTable(node: Node) {
  const header = node.firstChild;
  const match = /^d([1-9]\d{0,3})$/i.exec(header?.firstChild?.textContent.trim() ?? '');
  if (!match || Number(match[1]) > 1000) return null;
  const sides = Number(match[1]);
  const entries: { from: number; to: number; text: string }[] = [];
  const covered = new Set<number>();
  for (let index = 1; index < node.childCount; index++) {
    const row = node.child(index);
    const range = /^(\d+)(?:\s*[-–]\s*(\d+))?$/.exec(row.firstChild?.textContent.trim() ?? '');
    if (!range || row.childCount < 2) return null;
    const from = Number(range[1]); const to = Number(range[2] ?? range[1]);
    if (from < 1 || to > sides || to < from) return null;
    const cells: string[] = [];
    for (let cell = 1; cell < row.childCount; cell++) cells.push(row.child(cell).textContent);
    const text = cells.filter(Boolean).join(' · ');
    if (!text.trim()) return null;
    for (let face = from; face <= to; face++) {
      if (covered.has(face)) return null;
      covered.add(face);
    }
    entries.push({ from, to, text });
  }
  return covered.size === sides ? { sides, entries } : null;
}

export function rollFace(sides: number, draw = () => crypto.getRandomValues(new Uint32Array(1))[0]!) {
  if (!Number.isInteger(sides) || sides < 1 || sides > 1000) throw new Error('Invalid die');
  const limit = 0x100000000 - (0x100000000 % sides);
  let value: number;
  do { value = draw(); } while (value >= limit);
  return (value % sides) + 1;
}
