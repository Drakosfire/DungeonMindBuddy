import { fromMarkdown } from "mdast-util-from-markdown";
import { gfmStrikethrough } from "micromark-extension-gfm-strikethrough";
import { gfmStrikethroughFromMarkdown } from "mdast-util-gfm-strikethrough";
import { gfmTable } from "micromark-extension-gfm-table";
import { gfmTableFromMarkdown } from "mdast-util-gfm-table";
import { gfmTaskListItem } from "micromark-extension-gfm-task-list-item";
import { gfmTaskListItemFromMarkdown } from "mdast-util-gfm-task-list-item";
import type { Root } from "mdast";

/**
 * The single parser-backed structural interpretation of a Markdown body.
 *
 * Handoff: Docs/Plans/HANDOFF-BUILD-unify-markdown-structural-analysis.md
 *
 * This module is the ONLY place the micromark/mdast stack is configured.
 * Admission and TipTap projection both derive from the AST returned here;
 * no other module may re-derive Markdown structure from raw lines.
 *
 * Extension policy (handoff §6 compatibility gate):
 *
 * - GFM tables: enabled. The editor already supports a safe flat table
 *   subset; the parser now owns row/cell/alignment recognition.
 * - GFM strikethrough with `singleTilde: false`: enabled only in the
 *   canonical `~~strike~~` spelling the serializer emits. `~single~` stays
 *   literal text, matching pre-rescue behavior.
 * - GFM task-list items: enabled so admission can REJECT them structurally
 *   (`checked !== null`) instead of pattern-matching `[ ]` in raw text.
 * - NO autolink-literal: bare `https://…` / `www.…` / email text must remain
 *   plain paragraph text, exactly as before. Enabling it would smuggle
 *   ordinary-link support into the admitted language.
 * - NO footnotes, NO frontmatter plugin: `[^1]` stays literal text, and
 *   leading YAML frontmatter is owned byte-for-byte by
 *   `stripLeadingYamlFrontmatter` upstream of this parser.
 */
export function parseMarkdownAst(markdownBody: string): Root {
  return fromMarkdown(markdownBody, {
    extensions: [
      gfmTable(),
      gfmStrikethrough({ singleTilde: false }),
      gfmTaskListItem(),
    ],
    mdastExtensions: [
      gfmTableFromMarkdown(),
      gfmStrikethroughFromMarkdown(),
      gfmTaskListItemFromMarkdown(),
    ],
  });
}
