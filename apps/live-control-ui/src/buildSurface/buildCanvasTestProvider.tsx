import type { ReactNode } from "react";

import { MarkdownCanvasSessionProvider } from "../markdownCanvas/MarkdownCanvasSession";
import { BUILD_MARKDOWN_CANVAS } from "./buildMarkdownCanvasAdapter";

/** Shared test wrapper: one canvas session owns document authority for Build plugins. */
export function BuildCanvasTestProvider(props: {
  documentId: string;
  children: ReactNode;
}) {
  return (
    <MarkdownCanvasSessionProvider
      key={props.documentId}
      documentId={props.documentId}
      surface={BUILD_MARKDOWN_CANVAS.surface}
      kind={BUILD_MARKDOWN_CANVAS.kind}
    >
      {props.children}
    </MarkdownCanvasSessionProvider>
  );
}
