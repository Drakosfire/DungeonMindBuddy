import { useEffect, useState } from "react";
import type { Editor } from "@tiptap/core";

import {
  buildGraphAuthoringSelectionFromEditor,
  type GraphAuthoringContext,
  type GraphAuthoringSelection,
} from "./graphAuthoringSelection";

interface UseGraphAuthoringSelectionOptions {
  editor: Editor | null;
  authoringEnabled?: boolean;
  authoringContext?: GraphAuthoringContext | null;
  onGraphAuthoringSelection?: (selection: GraphAuthoringSelection | null) => void;
}

export function useGraphAuthoringSelection({
  editor,
  authoringEnabled = false,
  authoringContext,
  onGraphAuthoringSelection,
}: UseGraphAuthoringSelectionOptions): GraphAuthoringSelection | null {
  const [pendingSelection, setPendingSelection] = useState<GraphAuthoringSelection | null>(null);

  useEffect(() => {
    if (!editor || !authoringEnabled || !authoringContext) {
      setPendingSelection(null);
      onGraphAuthoringSelection?.(null);
      return;
    }

    const syncSelection = () => {
      const nextSelection = buildGraphAuthoringSelectionFromEditor(editor, authoringContext);
      setPendingSelection(nextSelection);
      onGraphAuthoringSelection?.(nextSelection);
    };

    syncSelection();
    editor.on("selectionUpdate", syncSelection);
    return () => {
      editor.off("selectionUpdate", syncSelection);
    };
  }, [authoringContext, authoringEnabled, editor, onGraphAuthoringSelection]);

  return pendingSelection;
}
