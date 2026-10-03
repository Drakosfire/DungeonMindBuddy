import type { Editor } from "@tiptap/core";

export interface PlanSectionTarget {
  id: string;
  from: number;
  to: number;
  rootNodeStart: number;
  rootNodeEnd: number;
  level: number;
  heading: string;
  label: string;
}

interface RootHeading {
  from: number;
  rootIndex: number;
  level: number;
  text: string;
}

function headingKey(heading: Pick<RootHeading, "level" | "text">): string {
  return `${heading.level}\u001f${heading.text}`;
}

/**
 * Return one target for each nonempty top-level Markdown heading. A target
 * includes its own heading and following blocks up to the next heading at the
 * same or a higher level. Nested headings therefore remain inside their parent
 * section while still being independently selectable themselves.
 */
export function planSectionTargets(editor: Editor): PlanSectionTarget[] {
  const document = editor.state.doc;
  const headings: RootHeading[] = [];
  document.forEach((node, from, rootIndex) => {
    if (node.type.name !== "heading") return;
    const level = Number(node.attrs.level);
    const text = node.textContent.trim();
    if (Number.isInteger(level) && level >= 1 && level <= 6 && text) {
      headings.push({ from, rootIndex, level, text });
    }
  });

  const totalByHeading = new Map<string, number>();
  for (const heading of headings) {
    const key = headingKey(heading);
    totalByHeading.set(key, (totalByHeading.get(key) ?? 0) + 1);
  }

  const seenByHeading = new Map<string, number>();
  return headings.map((heading, index) => {
    const nextPeer = headings.slice(index + 1).find((candidate) => candidate.level <= heading.level);
    const boundary = nextPeer?.from ?? document.content.size;
    let to = boundary - 1;
    while (to > heading.from && !document.resolve(to).parent.inlineContent) to -= 1;
    const from = heading.from + 1;
    const key = headingKey(heading);
    const ordinal = (seenByHeading.get(key) ?? 0) + 1;
    seenByHeading.set(key, ordinal);
    const total = totalByHeading.get(key) ?? 1;
    const duplicateHint = total > 1 ? ` · ${ordinal} of ${total}` : "";
    return {
      id: `heading:${heading.from}:${heading.level}`,
      from,
      to,
      rootNodeStart: heading.rootIndex,
      rootNodeEnd: nextPeer?.rootIndex ?? document.childCount,
      level: heading.level,
      heading: heading.text,
      label: `${"#".repeat(heading.level)} ${heading.text}${duplicateHint}`,
    };
  }).filter((target) => target.to > target.from);
}

/** Return the heading target only when the mounted selection exactly matches it. */
export function planSectionTargetForSelection(
  editor: Editor,
  from: number,
  to: number,
): PlanSectionTarget | null {
  return planSectionTargets(editor).find((target) => target.from === from && target.to === to) ?? null;
}
