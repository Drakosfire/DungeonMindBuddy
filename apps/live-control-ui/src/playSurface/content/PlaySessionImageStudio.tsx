import { useMemo, useRef } from "react";
import type { Editor } from "@tiptap/core";
import { DocumentImageStudio } from "../../media/DocumentImageStudio";
import { createDocumentMediaBridge, type DocumentMediaState } from "../../media/documentMediaBridge";

export function PlaySessionImageStudio({
  editor,
  identity,
  version,
  canEdit,
  worldId,
  onClose,
}: {
  editor: Editor;
  identity: string;
  version: string;
  canEdit: boolean;
  worldId?: string;
  onClose: () => void;
}) {
  const current = useRef<DocumentMediaState | null>(null);
  current.current = { editor, identity, version, canEdit };
  const bridge = useMemo(() => createDocumentMediaBridge(() => current.current), [identity]);
  return <DocumentImageStudio worldId={worldId} bridge={bridge} targetLabel="session copy" onClose={onClose} />;
}
