import type { PhrasingContent } from "mdast";

export type HeadingIdRegistry = {
  allocate: (children: PhrasingContent[]) => string;
};

function extractPlainTextFromPhrasingNode(node: PhrasingContent): string {
  switch (node.type) {
    case "text":
      return node.value;
    case "inlineCode":
      return node.value;
    case "break":
      return " ";
    case "emphasis":
    case "strong":
    case "delete":
      return extractPlainTextFromPhrasing(node.children);
    case "link":
      return extractPlainTextFromPhrasing(node.children);
    case "image":
      return node.alt ?? "";
    default:
      return "";
  }
}

/** Extract visible plain text from heading phrasing children (no markup). */
export function extractPlainTextFromPhrasing(nodes: PhrasingContent[] | undefined): string {
  if (!nodes?.length) return "";
  return nodes.map(extractPlainTextFromPhrasingNode).join("");
}

/** GitHub-style heading slug: lowercase, punctuation stripped, spaces → hyphens. */
export function slugifyHeading(text: string): string {
  return text
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s-]/gu, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "");
}

/** Allocate unique heading ids within one document (`-1`, `-2`, … on duplicates). */
export function createHeadingIdRegistry(): HeadingIdRegistry {
  const used = new Map<string, number>();

  return {
    allocate(children) {
      const base = slugifyHeading(extractPlainTextFromPhrasing(children)) || "heading";
      const count = used.get(base) ?? 0;
      used.set(base, count + 1);
      return count === 0 ? base : `${base}-${count}`;
    },
  };
}
