import type { PagePresentation } from "./presentation";
// Extend only the existing generic JSON transport's Page fields. No routing fork.
declare module "../../api/types" {
  interface WorkspaceDocumentSnapshot { page_presentation?: PagePresentation | null; page_presentation_sha256?: string | null; }
  interface TiptapMarkdownWritePrepareRequest { page_presentation?: PagePresentation | null; }
  interface TiptapMarkdownWriteCommitRequest { page_presentation?: PagePresentation | null; }
  interface TiptapMarkdownWritePrepareResponse { page_presentation_sha256?: string | null; }
  interface TiptapMarkdownWriteCommitResponse { page_presentation_sha256?: string | null; }
}
