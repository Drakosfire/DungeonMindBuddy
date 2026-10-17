import Table from "@tiptap/extension-table";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import TableRow from "@tiptap/extension-table-row";
import { EmbeddedTableView } from './EmbeddedTableView';

/** GFM-style tables for Plan Board / MarkdownEditor (non-resizable). */
export const PLAN_TABLE_EXTENSIONS = [
  Table.extend({ addNodeView() { return ({ node, view, getPos }) => new EmbeddedTableView(node, view, getPos); } }).configure({
    resizable: false,
    HTMLAttributes: {
      class: "md-table",
    },
  }),
  TableRow,
  TableHeader,
  TableCell,
];
